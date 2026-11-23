"""L2 ore mining (ADR 0029, docs/engine/sim-layers.md; docs/engine/mining.md): the harvesters' collector loop.

`Mining` keeps the ore nodes' state and the last frame mined, and moves every player's miner a frame at a time over
the world it is given (simworld.WORLD_API only). Money goes out through `pay(owner, amount)`, handed in by the caller
(simmoney.Money.collect, L4): this module never imports the money. Fields it owns: its own `nodes` and `mined_to`. A
miner is a thing with an OreMinerBehavior module (engine/modules/oreminer.py, step M9), which keeps its trip (the
body's `mine`, a read-only forward); this loop sets it through the module.
"""
import math

import engine.data.units as simunits
from engine.kernel import interfaces
from engine.world.handle import CIV, held

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
# A placed miner's first leg (from where it stands, not a refinery's dock): MINE_TURN_EXTRA's leg is dock to dock, the
# refinery's end MINE_PLACED_EXTRA of its -18; E207 dockqueue a (miners half-way to their nodes) reach them f19 / f48,
# the simulator without it f10 / f41 (INFERRED: one end's share, the other end's not read)
MINE_PLACED_EXTRA = 9.0
# A refinery's pads (E207 dockqueue a, work/re/e207_dockqueue.md; D187 work/re/d187_cangodirect.md): a miner holds them
# from its unload to MINE_PAD2 frames after (the bench's from pad 0, MINE_PAD1 before: not kept, the side node's leg is
# ~10 frames short). Off its node (MINE_PAD2 after loading, inside the leg) a miner finding them held queues, and once
# free drives in by pad 0 and pad 1 (MINE_PAD0 + MINE_PAD1). Pads free, one whose spot (MINE_LEAVE ahead of the node) is
# within 40 of the refinery's point DIRECT_AT ahead (or past it, within 63.2) goes direct and unloads beside one on the
# pads; another waits at pad 0 for them. 40 / 63.2 read (D187); MINE_LEAVE and DIRECT_AT fitted to E207's front (yes)
# and side (no) nodes and D165's turned node (no) (INFERRED)
MINE_PAD0, MINE_PAD1, MINE_PAD2, MINE_LEAVE, DIRECT_AT = 18, 22, 14, 60.0, 120.0


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
        self.nodes = {}                     # ore node serial -> {'free': frame it takes a miner from, 'gathered', 'at',
                                            # 'claim'}: the miners themselves (11-19 same-name sweep: a node or miner
                                            # made under the name since has none of the old one's)
        self.mined_to = None                # the last frame mine_due ran
        self.docks = {}                     # refinery serial -> the frame its pads are free from

    def mine_due(self, world, frame, pay):
        """Every player's miner (an OreMinerBehavior, not the neutral side's) up to `frame`, a frame at a time, the
        collector's loop of docs/engine/mining.md: locate a node -> drive -> dock (the node loads it MINE_DOCK frames,
        from the frame after it docked, once the node waits for a miner) -> the nearest unpacked refinery of its
        owner's -> drive -> unload MINE_DOCK frames into the owner's money, load // MINE_DOCK a frame and the rest on the
        last -> again. The node: its last one first (sticky), else the nearest (INFERRED: 'the first one found', the
        search order not read). A miner coming to a node where another is docked waits there for good (the retail node
        has no queue place: bench engine_mining b / e); one coming while the node plays its MINE_REST frames docks and
        waits for it. A refinery's pads take one miner at a time, the next queued; one that can go direct unloads
        beside it (MINE_PAD0 .. DIRECT_AT).
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
        node = held(world, b.find(interfaces.OreMiner).node)
        far =(b.x, b.y) if state == 'to node' else to          # the leg's end away from the node
        extra = mine_extra(node, far) if node else 0.0
        first = b.mine.pop('first', None)
        if first and node and state == 'to node':  # from where it faded in, or was placed
            extra += _by_turn(MINE_SPAWN_EXTRA, _turned_off(node, far)) if first == 'spawned' else MINE_PLACED_EXTRA
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
                 'first': 'spawned' if b.unpack_parent is not None and (b.x, b.y) == (b.unpack_parent.x,
                                                                             b.unpack_parent.y) else 'placed'}
            b.find(interfaces.OreMiner).set_trip(m)
        if m['leg']:                                # drawn along its drive
            (x0, y0), (x1, y1), f0, f1 = m['leg']
            k = min(1.0, (fr - f0) / max(1, f1 - f0))
            b.x, b.y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        if fr < m['due']:
            return
        st = m['state']
        om = b.find(interfaces.OreMiner)
        if st == 'locate':
            node = held(world, om.node)
            if node is None or not node.alive:
                node = min(nodes, key=lambda n: math.hypot(n.x - b.x, n.y - b.y), default=None)
            if node is None:
                m['due'] = fr + MINE_RETRY
                return
            om.head_for(node=node)
            n = self.nodes.setdefault(node.serial, {'free': 0, 'gathered': 0, 'at': None})
            if not self._claimed(world, n, b, node):
                n['claim'] = b                      # the first to look for it holds it (round 189)
            self._leg(world, b, fr, (node.x, node.y), 'to node')
        elif st == 'to node':
            m['leg'] = None
            if held(world, om.node) is None or not om.node.alive:  # the node picked has left the world (one made
                m['state'] = 'locate'               # under its name since is another) or died: it looks again
                                                    # (INFERRED; review 1119u P2 #4: a dead one is still in bodies)
                return
            n = self.nodes.setdefault(om.node.serial, {'free': 0, 'gathered': 0, 'at': None})
            if (n['at'] is not None and n['at'] is not b and self._docked(world, n['at'], om.node)) \
                    or self._claimed(world, n, b, om.node):
                m['state'], m['due'] = 'stuck', 10 ** 9     # no queue place: it never gets in
                return
            n['at'] = b
            m['state'], m['due'] = 'docked', max(fr + 1, n['free'])
        elif st == 'docked':                        # the node's first loading frame
            if held(world, om.node) is None or not om.node.alive:  # the node has left the world or died before
                                                    # its batch was reserved (review 1119u P2 #4):
                self._undock(b)                     # it looks again, as on its way there (review 1119p #4;
                m['state'] = 'locate'               # INFERRED)
                return
            n = self.nodes[om.node.serial]
            # E180 / D165: reserve the batch here, but cargo becomes visible
            # only when loading finishes. See work/re/e180_queuedock_load.md.
            m['pending_load'] = MINE_LOAD if n['gathered'] < MINE_FULL else MINE_EMPTY
            if n['gathered'] < MINE_FULL:
                n['gathered'] += MINE_LOAD
            m['state'], m['due'] = 'loading', fr + MINE_DOCK - 1
        elif st == 'loading':                       # full on its last loading frame: off the frame after (the trip
            n = self.nodes[om.node.serial]          # 2 x 104 + 61 = 269 of engine_mining a)
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
            om.head_for(refinery=r)
            # E164 / D165: selection still finds a refinery lacking QueueDock, but
            # native delivery faults immediately, before moving or paying. Reject
            # this configuration rather than simulating a successful delivery.
            # See work/re/e164_queuedock.md; absolute path timing remains a gap.
            if not simunits.queue_dock(r.template, world.own):
                raise ValueError(f'QueueDock missing on refinery {r.name!r} selected by miner {b.name!r}')
            m['direct'] = self._direct(world, b, r)
            self._leg(world, b, fr, (r.x, r.y), 'to refinery')
            # off the node by its pad 2 (the leg holds it), then it asks the refinery: direct or by pad 0
            m['state'], m['due'] = 'off node', min(fr + MINE_PAD2, m['due'])
        elif st in ('off node', 'to pad'):
            r = held(world, om.refinery)
            if r is None or not r.alive:
                m['state'], m['leg'] = 'find refinery', None
                return
            free = self.docks.get(r.serial, 0)
            if st == 'off node':
                if fr < free:                       # held: to the queue, in by pad 0 and pad 1 once free
                    m['state'], m['wait'], m['due'] = 'to pad', MINE_PAD0 + MINE_PAD1, free
                elif m['direct']:                   # straight to the action pad, beside one on the pads
                    m['state'], m['due'] = 'to refinery', m['leg'][3]
                else:                               # by pad 0 at the end of its drive (the pads it then holds
                    m['state'], m['wait'], m['due'] = 'to pad', 0, m['leg'][3]   # from its unload: INFERRED)
                del m['direct']
            elif fr < free:                         # held: it waits (at pad 0, pad 1 still to drive: INFERRED)
                m['due'], m['wait'] = free, m['wait'] or MINE_PAD1
                return
            else:
                m['state'], m['due'] = 'to refinery', max(fr + m.pop('wait'), m['leg'][3])
                self.docks[r.serial] = m['due'] + MINE_DOCK + MINE_PAD2
            if m['due'] <= fr:
                self._mine(world, b, fr, nodes, pay)
        elif st == 'to refinery':
            m['leg'] = None
            r = held(world, om.refinery)            # the one picked, not one made under its name since
            if r is None or not r.alive:
                m['state'] = 'find refinery'
                return
            self.docks[r.serial] = max(self.docks.get(r.serial, 0), fr + MINE_DOCK + MINE_PAD2)
            m['state'], m['n'] = 'unloading', 0
            self._mine(world, b, fr, nodes, pay)
        elif st == 'unloading':                     # money on the arrival frame and the next MINE_DOCK - 1
            r = held(world, om.refinery)
            if r is None or not r.alive:            # cut off mid-unload: it carries on with what is left, not the
                m['load'] -= m['load'] // MINE_DOCK * m['n']    # whole load again (review 1119p #1; INFERRED)
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

    @staticmethod
    def _direct(world, b, r):
        """Whether `b`, setting off for refinery `r`, can go direct to its action pad (MINE_PAD0 .. DIRECT_AT)."""
        node = held(world, b.find(interfaces.OreMiner).node)
        x, y = b.x, b.y
        if node is not None and math.hypot(node.x - x, node.y - y) < 1.0:     # its spot ahead of the node
            x, y = x + MINE_LEAVE * math.cos(node.angle), y + MINE_LEAVE * math.sin(node.angle)
        dx, dy = r.x + DIRECT_AT * math.cos(r.angle) - x, r.y + DIRECT_AT * math.sin(r.angle) - y
        d2 = dx * dx + dy * dy
        return d2 <= 1600.0 or (dx * (r.x - x) + dy * (r.y - y) < 0 and d2 <= 4000.0)

    def _claimed(self, world, n, b, node):
        """Whether another miner than `b` holds node `n` (the thing `node`): it looked for it first and is on its way
        there, docked or loading (bench round 189, checks/engine_mining.py g / mineaway g: the placed collector works,
        the refinery's own waits for good, whether or not their drives meet). The claim is the miner itself: one
        made under its name since holds nothing."""
        o = held(world, n.get('claim')) if n.get('claim') is not b else None
        return self._at(o, node, ('to node', 'docked', 'loading'))

    def _docked(self, world, miner, node):
        """Whether `miner` (the thing) stands docked at (or is being loaded by) `node`, the world still holding it."""
        return self._at(held(world, miner), node, ('docked', 'loading'))

    @staticmethod
    def _at(o, node, states):
        return o is not None and o.alive and o.mine is not None and o.find(interfaces.OreMiner).node is node \
            and o.mine['state'] in states

    def _undock(self, b):
        node = b.find(interfaces.OreMiner).node if b.mine else None
        n = self.nodes.get(node.serial) if node is not None else None
        if n and n['at'] is b:
            n['at'] = None
