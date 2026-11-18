"""L2 ore mining (ADR 0029, docs/engine/sim-layers.md; docs/engine/mining.md): the harvesters' collector loop.

`Mining` keeps the ore nodes' state and the last frame mined, and moves every player's miner a frame at a time over
the world it is given (simworld.WORLD_API only). Money goes out through `pay(owner, amount)`, handed in by the caller
(simmoney.Money.collect, L4): this module never imports the money. Fields it owns: its own `nodes` and `mined_to`. A
miner is a thing with an OreMinerBehavior module (engine/modules/oreminer.py, step M9), which keeps its trip (the
body's `mine`, a read-only forward); this loop sets it through the module.
"""
import math

import simunits
from engine.kernel import interfaces
from simworld import CIV

# HOOKS 7, ore mining (docs/engine/mining.md, bench 2026-11-05 engine_mining a-e): a load 250 (retail miners'
# DeliveryCapacity), loaded at the node in 30 frames starting the frame after the miner docks, unloaded at the refinery
# in 30 frames from its arrival, 8 a frame and the rest on the last; past MaximumGatheredValue (30000) a load is 60.
# The node then plays MINE_REST frames before it takes the next miner, a load every 30 + 121 = 151 frames: what
# bounds retail's facing (mineturn0 p / mineniag p trip 151, the drive alone 133; round 179 below). The data's 60 +
# 30 + 60 (move to extract, extract, move to deliver) + 1 is 151 when they start with the loading (INFERRED: that
# overlap, not read)
MINE_LOAD, MINE_DOCK, MINE_REST, MINE_FULL, MINE_EMPTY = 250, 30, 121, 30000, 60
MINE_RETRY = 15                # no node / refinery found: the miner idles 1 s and looks again
# A leg (node <-> refinery) takes straight distance / speed + MINE_TURN_EXTRA frames, by how far the node is turned off
# facing the leg's other end (degrees, either way alike): the miner docks at the node's front, so a node turned away
# is driven round. Retail stands every node facing its refinery (node angle = refinery's + 180: heidelberg,
# gibraltar, north sea). Bench 2026-11-12 checks/engine_mining.py mineturn<k> p (probe_range's pad, refinery 180 from
# its node, an Allied miner at 50 = 54 frames straight): trips 151 / 186-187 / 241 / 323 at 0 / 45 / 90 / 180, and
# engine_mining a 269 at 135 (its node at angle 0); a trip = 2 legs + 30 + 30 + 1. Between readings linear (INFERRED);
# niagara's east pad (45 off) trips 185 on the bench (aitowerinc5 f, an AI's miner): the same rule, 45's 8 set to it.
# Round 179 (checks/engine_mining.py mineturn0 q, minefar p): at 0 the trip is the node's (151, MINE_REST), not the
# drive's -- the first visit, at a node that waits, is in c's node square 73 frames (2 x 36 + 1), the later ones 91;
# so the leg there is 36 (-18), not the 45 (-9) a drive-bound 151 gave.
MINE_TURN_EXTRA = ((0.0, -18.0), (45.0, 8.0), (90.0, 36.0), (135.0, 50.0), (180.0, 77.0))
# A refinery's own collector's first leg, from where it fades in (the refinery's spot, INFERRED) rather than from the
# refinery's dock: mineturn0 q has it in the node square at 23, the later legs at 15 from the dock (+8; its first
# money 111 = +7); from 45 on the first money is the period's - 29 within 2 (0). Between linear (INFERRED).
MINE_SPAWN_EXTRA = ((0.0, 7.0), (45.0, 0.0))


def _turned_off(node, far):
    """How far (degrees, 0 .. 180) `node`'s facing is turned off the direction to `far`."""
    want = math.degrees(math.atan2(far[1] - node.y, far[0] - node.x))
    return abs((math.degrees(node.angle) - want + 180.0) % 360.0 - 180.0)


def _by_turn(table, turn):
    for (k0, v0), (k1, v1) in zip(table, table[1:]):
        if turn <= k1:
            return v0 + (v1 - v0) * (turn - k0) / (k1 - k0)
    return table[-1][1]


def mine_extra(node, far):
    """Frames (float) a miner's leg to or from `node` takes beyond straight distance / speed: by how far the node's
    facing is turned off the direction to the leg's other end `far` (MINE_TURN_EXTRA)."""
    return _by_turn(MINE_TURN_EXTRA, _turned_off(node, far))


class Mining:
    def __init__(self):
        self.nodes = {}                     # ore node name -> {'free': frame it takes a miner from, 'gathered', 'at'}
        self.mined_to = None                # the last frame mine_due ran

    def mine_due(self, world, frame, pay):
        """Every player's miner (an OreMinerBehavior, not the neutral side's) up to `frame`, a frame at a time, the
        collector's loop of docs/engine/mining.md: locate a node -> drive -> dock (the node loads it MINE_DOCK frames,
        from the frame after it docked, once the node waits for a miner) -> the nearest unpacked refinery of its
        owner's -> drive -> unload MINE_DOCK frames into the owner's money, load // MINE_DOCK a frame and the rest on the
        last -> again. The node: its last one first (sticky), else the nearest (INFERRED: 'the first one found', the
        search order not read). A miner coming to a node where another is docked waits there for good (the retail node
        has no queue place: bench engine_mining b / e); one coming while the node plays its MINE_REST frames docks and
        waits for it. A refinery unloads one miner at a time, the next waiting (INFERRED: its queue places not read).
        A leg is straight distance at the miner's speed + mine_extra (by the node's facing, no path finding); the miner is
        drawn along it. A harvester given a path (a script's move) drops its trip and starts over once it stands."""
        start = frame if self.mined_to is None else self.mined_to + 1
        self.mined_to = frame
        miners = [b for b in world.living() if b.modules and b.find(interfaces.OreMiner) is not None
                  and b.owner != CIV and b.speed > 0]
        if not miners:
            return
        nodes = [b for b in world.living() if 'orenode' in b.template.lower()]
        # a refinery's own collector, not yet started, looks for its node after the miners already there (it fades
        # in after the map's objects are made; round 189: the placed one claims the node first)
        miners.sort(key=lambda b: b.mine is None and b.unpack_parent is not None)
        for fr in range(start, frame + 1):
            for b in miners:
                if b.alive:
                    self._mine(world, b, fr, nodes, pay)

    def _leg(self, world, b, fr, to, state):
        """Off to `to`: there mine_extra + distance / speed frames on, in `state` meanwhile."""
        d = math.hypot(to[0] - b.x, to[1] - b.y)
        node = world.bodies.get(b.mine['node']) if b.mine.get('node') else None
        far = (b.x, b.y) if state == 'to node' else to          # the leg's end away from the node
        extra = mine_extra(node, far) if node else 0.0
        if b.mine.pop('spawned', False) and node and state == 'to node':     # from where it faded in
            extra += _by_turn(MINE_SPAWN_EXTRA, _turned_off(node, far))
        frames = int(round(d / b.speed * simunits.LIFE_FPS + extra))
        b.mine.update(state=state, due=fr + frames, leg=((b.x, b.y), to, fr, fr + frames))

    def _mine(self, world, b, fr, nodes, pay):
        """One frame of a harvester's trip (mine_due)."""
        m = b.mine
        if b.path:                                  # moved by someone else: start over once it stands
            if m is not None:
                self._undock(b)
                b.find(interfaces.OreMiner).set_trip(None)
            return
        if m is None and b.building is not None:
            # told to unpack (order_unpack; the SimpleExpansion miner armed to unpack within Distance): it does not
            # set off for ore while that order stands. aiexpb50 (D169): the miner standing at its slot 67 behind the
            # node was drawn onto the node by a new trip and unpacked 38 from it; the bench miner stands 98 away
            # idle to s130 (D156). INFERRED: the game's reason (the order's state, the team's hold) not read
            return
        if m is None:
            m = {'state': 'locate', 'node': None, 'ref': None, 'due': fr, 'load': 0, 'n': 0, 'leg': None,
                 'spawned': b.unpack_parent is not None and (b.x, b.y) == (b.unpack_parent.x, b.unpack_parent.y)}
            b.find(interfaces.OreMiner).set_trip(m)
        if m['leg']:                                # drawn along its drive
            (x0, y0), (x1, y1), f0, f1 = m['leg']
            k = min(1.0, (fr - f0) / max(1, f1 - f0))
            b.x, b.y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        if fr < m['due']:
            return
        st = m['state']
        if st == 'locate':
            node = world.bodies.get(m['node']) if m['node'] else None
            if node is None or not node.alive:
                node = min(nodes, key=lambda n: math.hypot(n.x - b.x, n.y - b.y), default=None)
            if node is None:
                m['due'] = fr + MINE_RETRY
                return
            m['node'] = node.name
            n = self.nodes.setdefault(node.name, {'free': 0, 'gathered': 0, 'at': None})
            if not self._claimed(world, n, b, node.name):
                n['claim'] = b.name                 # the first to look for it holds it (round 189)
            self._leg(world, b, fr, (node.x, node.y), 'to node')
        elif st == 'to node':
            m['leg'] = None
            n = self.nodes.setdefault(m['node'], {'free': 0, 'gathered': 0, 'at': None})
            if (n['at'] is not None and n['at'] != b.name and self._docked(world, n['at'], m['node'])) \
                    or self._claimed(world, n, b, m['node']):
                m['state'], m['due'] = 'stuck', 10 ** 9     # no queue place: it never gets in
                return
            n['at'] = b.name
            m['state'], m['due'] = 'docked', max(fr + 1, n['free'])
        elif st == 'docked':                        # the node's first loading frame
            n = self.nodes[m['node']]
            # E180 / D165: reserve the batch here, but cargo becomes visible
            # only when loading finishes. See work/re/e180_queuedock_load.md.
            m['pending_load'] = MINE_LOAD if n['gathered'] < MINE_FULL else MINE_EMPTY
            if n['gathered'] < MINE_FULL:
                n['gathered'] += MINE_LOAD
            m['state'], m['due'] = 'loading', fr + MINE_DOCK - 1
        elif st == 'loading':                       # full on its last loading frame: off the frame after (the trip
            n = self.nodes[m['node']]               # 2 x 104 + 61 = 269 of engine_mining a)
            m['load'] = m.pop('pending_load')
            n['at'], n['free'], n['claim'] = None, fr + MINE_REST + 1, None
            m['state'], m['due'] = 'find refinery', fr + 1
        elif st == 'find refinery':
            now = world.frame_now()
            refs = [r for r in world.living() if r.owner == b.owner and 'REFINERY' in r.kinds
                    and not (r.unpack_end is not None and now < r.unpack_end)]
            r = min(refs, key=lambda r: math.hypot(r.x - b.x, r.y - b.y), default=None)
            if r is None:
                m['due'] = fr + MINE_RETRY
                return
            m['ref'] = r.name
            # E164 / D165: selection still finds a refinery lacking QueueDock, but
            # native delivery faults immediately, before moving or paying. Reject
            # this configuration rather than simulating a successful delivery.
            # See work/re/e164_queuedock.md; absolute path timing remains a gap.
            if not simunits.queue_dock(r.template, world.own):
                raise ValueError(f'QueueDock missing on refinery {r.name!r} selected by miner {b.name!r}')
            self._leg(world, b, fr, (r.x, r.y), 'to refinery')
        elif st == 'to refinery':
            m['leg'] = None
            r = world.bodies.get(m['ref'])
            if r is None or not r.alive:
                m['state'] = 'find refinery'
                return
            busy = next((o for o in world.living() if o is not b and o.mine and o.mine['state'] == 'unloading'
                         and o.mine['ref'] == r.name), None)
            if busy is not None:                    # one at a time: wait for it to finish
                m['due'] = busy.mine['due'] + MINE_DOCK - busy.mine['n']
                return
            m['state'], m['n'] = 'unloading', 0
            self._mine(world, b, fr, nodes, pay)
        elif st == 'unloading':                     # money on the arrival frame and the next MINE_DOCK - 1
            r = world.bodies.get(m['ref'])
            if r is None or not r.alive:
                m['state'] = 'find refinery'
                return
            m['n'] += 1
            step = m['load'] // MINE_DOCK
            give = step if m['n'] < MINE_DOCK else m['load'] - step * (MINE_DOCK - 1)
            pay(b.owner, give)                  # simmoney.Money.collect (L4), handed in
            m['due'] = fr + 1
            if m['n'] >= MINE_DOCK:
                # D165 / E164: native cargo clears when Unload finishes, not
                # when the next ore node begins loading.
                m['load'] = 0
                m['state'] = 'locate'

    def _claimed(self, world, n, b, node):
        """Whether another miner than `b` holds node `n` (named `node`): it looked for it first and is on its way
        there, docked or loading (bench round 189, checks/engine_mining.py g / mineaway g: the placed collector works,
        the refinery's own waits for good, whether or not their drives meet)."""
        o = world.bodies.get(n.get('claim')) if n.get('claim') not in (None, b.name) else None
        return o is not None and o.alive and o.mine is not None and o.mine['node'] == node \
            and o.mine['state'] in ('to node', 'docked', 'loading')

    def _docked(self, world, miner, node):
        """Whether `miner` stands docked at (or is being loaded by) `node`."""
        o = world.bodies.get(miner)
        return o is not None and o.alive and o.mine is not None and o.mine['node'] == node \
            and o.mine['state'] in ('docked', 'loading')

    def _undock(self, b):
        n = self.nodes.get(b.mine['node']) if b.mine and b.mine['node'] else None
        if n and n['at'] == b.name:
            n['at'] = None
