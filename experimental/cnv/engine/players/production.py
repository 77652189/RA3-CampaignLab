"""Production (sim.Sim.production; S7b): the factories' queues by the factory's serial, run a frame at a time (due),
and what the ports and the host ask of them -- the AI whether one is idle, the UI its jobs, the proxy what the player
still owes. Sim.order_build picks the factory and queues (Sim.queues is this one's dict under a second name; the
exchange file's simbattlefield sets a factory's queue there too); the host lends the money, the build frames (its
power) and what a done job makes (a unit out of the door, an upgrade). Rows come out read only (readonly.view)."""
import numpy as np

import engine.world.handle as simworld
from engine.data import units as simunits
from engine.ports.readonly import view

PEERS = frozenset({'wallet', 'build_frames', 'upgrade_done', 'produce_out', 'banned', 'unit_construction_disabled'})


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

    def held(self, job):
        """A unit job not full that stands for a ban: its unit off the owner's menu (ALLOW_DISALLOW_ONE_BUILDING 0) or
        the owner's unit construction disabled -- paid so far kept, the queue behind it too; an upgrade's never.
        The global gate was measured with AlliedEngineer only (bench 2026-11-09 engine_production g): applying it to
        other unit templates is INFERRED; upgrade queues and UI request eligibility are not measured."""
        return job['full'] is None and 'upgrade' not in job and (
            (job['owner'], job['template'].lower()) in self.peers.banned
            or job['owner'] in self.peers.unit_construction_disabled)
