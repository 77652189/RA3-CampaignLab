"""Production (sim.Sim.production; S7b): the factories' queues by the factory's serial, run a frame at a time (due),
and what the ports and the host ask of them -- the AI whether one is idle, the UI its jobs, the proxy what the player
still owes; and the builders' structures (at_site, pack, put_down: an MCV, an engineer's core, a yard packing).
Sim.order_build picks the factory and queues (queue), the exchange file's simbattlefield sets a factory's queue (put);
the host lends the money, the build frames (its power), what a done job makes (a unit out of the door, an upgrade),
the removal of a replaced builder and the EMP book. Rows come out read only (readonly.view)."""
import math

import numpy as np

import engine.world.handle as simworld
from engine.data import units as simunits
from engine.kernel import interfaces
from engine.ports.readonly import view

REPLACE_FRAMES = 6             # a ReplaceSelfSpecialAbility at its point: the replacement 6 frames on (engine_build a)

PEERS = frozenset({'wallet', 'build_frames', 'upgrade_done', 'produce_out', 'banned', 'unit_construction_disabled',
                   '_life', 'emp_book'})


def f32(x):
    return float(np.float32(x))


class Peers:
    """What production may reach on its host (the Sim): the names in PEERS, read when used."""
    __slots__ = ('host',)

    def __init__(self, host):
        object.__setattr__(self, 'host', host)

    def __getattr__(self, name):
        if name not in PEERS:
            raise AttributeError(f'simproduce.Peers: {name} is not lent (PEERS)')
        return getattr(self.host, name)


class Production:
    def __init__(self, world, peers):
        self.world, self.peers = world, peers
        self.queues = {}                # factory serial -> [job] (Sim.order_build's), in the order first queued
        self.produced_to = None         # the last frame due ran
        self.placing = []               # (frame, structure, owner, team, x, y, by): a builder's, to put down (R5)
        self.pack_hold = {}             # a yard packing's frames held after, by serial (review 1119p #3: unsorted)

    def queue(self, serial, job):
        """Sim.order_build's job at the end of the factory's queue."""
        self.queues.setdefault(serial, []).append(job)

    def put(self, serial, jobs):
        """The factory's queue set to `jobs` (simbattlefield's file), last in the order; none: no queue."""
        self.queues.pop(serial, None)
        if jobs:
            self.queues[serial] = jobs

    def due(self, frame):
        """Each factory's queue up to `frame`, a frame at a time: the first job not yet full goes on 100 / frames
        (single float, so a 150-frame build fills at the 151st), paying up to ceil(cost x progress / 100) -- a frame
        the owner cannot pay the difference stands still; the next job starts the frame after one fills; a full one
        comes out DoorOpeningTime later at the factory's UnitCreatePoint (turned with it), on the factory's team,
        and walks to its NaturalRallyPoint (bench 2026-11-05 engine_production a-d: 150 / 151 frames, 54 paid at
        the 16th, a 250 budget stalls at 3 left, out 10 frames after full). A banned unit's job
        (ALLOW_DISALLOW_ONE_BUILDING 0) stands, keeps what it paid and goes on when let go -- not cancelled, not
        refunded (bench 2026-11-09 engine_production g). A factory gone takes its queue (keyed by serial: O31)."""
        world, peers = self.world, self.peers
        start = frame if self.produced_to is None else self.produced_to + 1
        self.produced_to = frame
        if not self.queues:
            return
        for fr in range(start, frame + 1):
            for serial in list(self.queues):
                f, q = simworld.held(world, world.world.numbered.get(serial)), self.queues[serial]
                if f is None or not f.alive or not q:
                    del self.queues[serial]
                    continue
                create, rally, door = simunits.exit_of(f.template, world.own)
                for job in [j for j in q if j['full'] is not None and fr >= j['full'] + (0 if 'upgrade' in j else door)]:
                    if not peers.wallet.instal(job['owner'], job, 100.0):
                        continue            # a file's full job not paid up (simbattlefield) waits for its rest
                    q.remove(job)
                    if 'upgrade' in job:
                        peers.upgrade_done(f, job)
                    else:
                        peers.produce_out(f, job, create, rally)
                job = next((j for j in q if j['full'] is None), None)
                if job is None or self.held(job):
                    continue                # banned: the first job stands, paid so far kept, the queue behind it too
                step = f32(100.0 / peers.build_frames(job['secs'], job['owner']))
                nxt = f32(job['progress'] + step)
                if not peers.wallet.instal(job['owner'], job, nxt):
                    continue
                job['progress'] = nxt
                if nxt >= 100.0:
                    job['full'] = fr

    def jobs(self, serial):
        """The factory's jobs in order, read only ({'template', 'owner', 'cost', 'secs', 'progress' (per cent,
        float32), 'paid', 'full' (the frame it filled or None)}, an upgrade's also 'upgrade', 'kind'); () for none."""
        return view(self.queues.get(serial, ()))

    def busy(self, serial):
        """Whether the factory has a job queued."""
        return bool(self.queues.get(serial))

    def owed(self, player):
        """What the player's queued jobs will still take (due pays frame by frame)."""
        return sum(j['cost'] - j['paid'] for q in self.queues.values() for j in q if j['owner'] == player)

    def buying(self, player, upgrade):
        """Whether an upgrade (lower case) is queued for the player anywhere."""
        return any(j.get('upgrade', '').lower() == upgrade for q in self.queues.values() for j in q
                   if j['owner'] == player)

    def admits(self, f, template):
        """Whether factory f takes an order for `template` (Sim.order_build): a LIMITED_PRODUCTION_AIRCRAFT only while
        f's ParkingPlaceBehavior spots (engine/modules/parking.py; none: 0) outnumber the planes of that kind it made
        still alive and those in its queue (bench engine_parking: 4 of 5 presses made, none without the module)."""
        kind = 'LIMITED_PRODUCTION_AIRCRAFT'
        if kind not in simunits.stats(template, self.world.own)['kinds']:
            return True
        kept = sum(1 for b in self.world.bodies.values() if b.alive and b.made_by == f.name and kind in b.kinds) + sum(
            1 for j in self.queues.get(f.serial, ()) if kind in simunits.stats(j['template'], self.world.own)['kinds'])
        return kept < sum(p.spots for p in f.find(interfaces.Parking))

    def held(self, job):
        """A unit job not full that stands for a ban: its unit off the owner's menu (ALLOW_DISALLOW_ONE_BUILDING 0) or
        the owner's unit construction disabled -- paid so far kept, the queue behind it too; an upgrade's never.
        The global gate was measured with AlliedEngineer only (bench 2026-11-09 engine_production g): applying it to
        other unit templates is INFERRED; upgrade queues and UI request eligibility are not measured."""
        return job['full'] is None and 'upgrade' not in job and (
            (job['owner'], job['template'].lower()) in self.peers.banned
            or job['owner'] in self.peers.unit_construction_disabled)

    def at_site(self, b, walked):
        """R5: a builder within his stand of the spot he was told to build at stops; the structure is made there the
        frame after he got there (`walked` this tick before that: bench 2026-11-07 engine_life, the ice core one frame
        after an order given within range). False while he is still short of it."""
        structure, (x, y), stand = b.building
        if math.hypot(b.x - x, b.y - y) > stand + 1e-6:
            return False
        if getattr(b, 'unpack_here', False):    # order_unpack here=True: the structure where b stands (D157)
            x, y = b.x, b.y
        world = self.world
        got = world.frame_now() + (math.ceil(round(walked / b.speed * simunits.LIFE_FPS, 6)) if walked else 0)
        self.placing.append((got + (REPLACE_FRAMES if b.replace else 1), structure, b.owner, b.team, x, y, b))
        b.building, b.path, b.dest = None, [], None
        world.note('技能', f'{world.label(b)} 到位，造 {structure}')
        return True

    def pack(self, b, into, frames, hold):
        """A yard packing (a script's button): b turns into `into` `frames` on, standing still `hold` frames after."""
        self.pack_hold[b.serial] = hold
        self.placing.append((self.world.frame_now() + frames, into, b.owner, b.team, b.x, b.y, b))   # by the thing

    def put_down(self, frame):
        """The structures builders (the things that got there) put down by `frame` (at_site, pack); a replaced one
        gone. Its own frame phase (simloop's build), apart from the factories' due."""
        world = self.world
        for d in [d for d in self.placing if d[0] <= frame]:
            del self.placing[next(i for i, e in enumerate(self.placing) if e is d)]
            _, structure, owner, team, x, y, was = d
            by = was.name
            if was.replace:                         # engine_unpack: the replacement takes its name and health share
                if not was.alive or world.bodies.get(by) is not was:
                    continue
                share = was.hp / was.max_hp if was.max_hp else 1.0
                self.peers._life().delete(world, was, f'展开成 {structure}')
                world.bodies[simworld.free_name(world, '#packed', by)] = world.bodies.pop(by)
                n = world.add(by, structure, owner, was.x, was.y, by=by, at=world.t)
                n.set_hp(n.max_hp * share, tell=False)
                hold = self.pack_hold.pop(was.serial, 0)
                if hold:                    # DISABLE_NEW_OBJECT_DURING_UNPACK: stands still (engine_pack), as EMP'd
                    self.peers.emp_book()[n.serial] = world.frame_now() + hold
            else:
                n = world.add(simworld.free_name(world, '#built', f'by {by}'), structure, owner, x, y, by=by, at=world.t)
            n.team = team
            if world.blocks(n):
                world.reblock()
