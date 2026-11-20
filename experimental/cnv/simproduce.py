"""Production's read side (sim.Sim.production; S7b session 1): what the ports and the host ask of the factories'
queues, by the factory's serial -- the AI whether one is idle, the UI its jobs, the proxy what the player still owes.
The queues stay the host's for now (Sim.queues: order_build queues, produce_due runs them; S7b session 2 moves them
here), read through the loan at every ask -- a snapshot restore replaces the dict. Rows come out read only
(readonly.view): a write goes through Sim.order_build, never past it."""
from engine.ports.readonly import view

PEERS = frozenset({'queues', 'banned', 'unit_construction_disabled'})


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
    __slots__ = ('peers',)

    def __init__(self, peers):
        self.peers = peers

    def jobs(self, serial):
        """The factory's jobs in order, read only ({'template', 'owner', 'cost', 'secs', 'progress' (per cent,
        float32), 'paid', 'full' (the frame it filled or None)}, an upgrade's also 'upgrade', 'kind'); () for none."""
        return view(self.peers.queues.get(serial, ()))

    def busy(self, serial):
        """Whether the factory has a job queued."""
        return bool(self.peers.queues.get(serial))

    def owed(self, player):
        """What the player's queued jobs will still take (produce_due pays frame by frame)."""
        return sum(j['cost'] - j['paid'] for q in self.peers.queues.values() for j in q if j['owner'] == player)

    def buying(self, player, upgrade):
        """Whether an upgrade (lower case) is queued for the player anywhere."""
        return any(j.get('upgrade', '').lower() == upgrade for q in self.peers.queues.values() for j in q
                   if j['owner'] == player)

    def held(self, job):
        """A unit job not full that stands for a ban: its unit off the owner's menu (ALLOW_DISALLOW_ONE_BUILDING 0) or
        the owner's unit construction disabled -- paid so far kept, the queue behind it too; an upgrade's never.
        The global gate was measured with AlliedEngineer only (bench 2026-11-09 engine_production g): applying it to
        other unit templates is INFERRED; upgrade queues and UI request eligibility are not measured."""
        return job['full'] is None and 'upgrade' not in job and (
            (job['owner'], job['template'].lower()) in self.peers.banned
            or job['owner'] in self.peers.unit_construction_disabled)
