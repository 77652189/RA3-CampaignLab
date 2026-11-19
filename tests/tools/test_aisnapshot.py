"""A run's snapshot with the skirmish AI (experimental/cnv/simaisnap.py; step S 11b-4, docs/engine/sim-modules.md
9.2): a SimAI with no brain taken at heal_a's half, through JSON and back equal, written onto a SimAI made anew,
taken again equal (4.2) and run on to the end as the one never stopped; with brains (guard 7's ai_open, the engine
model here) every field of the SimAI, its brains and their Units sorted (4.3) and the snapshot refused naming the plugin
object without the snapshot port."""
import json

import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import build  # noqa: E402
import sim  # noqa: E402
import simai  # noqa: E402
import simaisnap  # noqa: E402
import simrecord  # noqa: E402
import simsnap  # noqa: E402

FPS = 15
_, _WHERE, END = simrecord.TASKS['heal_a']
HALF = int(END / 2 * FPS)


def _simai(m, t):
    return simai.SimAI(sim.Sim(m, t, model=False))


@pytest.fixture(scope='module')
def heal():
    m, t, _ = build.resolve(*_WHERE)
    run = _simai(m, t).advance(HALF)
    taken = simaisnap.snapshot(run)
    restored = _simai(m, t)
    simaisnap.restore(restored, json.loads(json.dumps(taken)))
    return m, t, run, taken, restored


def test_a_simai_with_no_brain_taken_and_written_back_equal(heal):
    m, t, run, taken, restored = heal
    assert not run.brains and run.done_to is not None
    assert json.loads(json.dumps(taken)) == taken
    assert simaisnap.snapshot(restored) == taken
    assert restored.done_to == run.done_to


def test_a_simai_written_back_runs_on_as_the_one_never_stopped(heal):
    m, t, run, taken, restored = heal
    run.advance(int(END * FPS) - HALF)
    restored.advance(int(END * FPS) - HALF)
    assert simsnap.snapshot(restored.sim) == simsnap.snapshot(run.sim)
    assert restored.done_to == run.done_to


def test_a_snapshot_of_another_shape_is_refused():
    m, t, _ = build.resolve(*_WHERE)
    with pytest.raises(ValueError, match='shape'):
        simaisnap.restore(_simai(m, t), {'version': simaisnap.VERSION, 'sim': {}})
    with pytest.raises(ValueError, match='not a field'):
        simaisnap.restore(_simai(m, t), {'version': simaisnap.VERSION, 'sim': {}, 'brains': [],
                                         'ai': [['brains', {}]]})


@pytest.fixture(scope='module')
def skirm():
    if not simai.available():
        pytest.skip('the engine model (ra3model.ai) is not on this computer')
    m, t, _ = build.resolve(*simrecord.TASKS['ai_open'][1])     # guard 7's fixed mission with the AI
    return _simai(m, t).advance(int(simrecord.TASKS['ai_open'][2] * FPS))     # to its end: units out


def test_every_field_of_the_simai_its_brains_and_units_is_sorted(skirm):
    assert skirm.brains and any(b.wrappers for b in skirm.brains.values())
    assert simaisnap.unclassified(skirm) == []


def test_a_new_field_or_a_broken_alias_is_named(skirm):
    b = next(iter(skirm.brains.values()))
    u = next(iter(b.wrappers.values()))
    garrison = skirm.garrison
    try:
        b.fresh_field, u.fresh_field, skirm.garrison = 1, 2, object()
        assert simaisnap.unclassified(skirm) == ['Brain.fresh_field', 'Unit.fresh_field',
                                                 'simai.garrison (not the object it names)']
    finally:
        del b.fresh_field, u.fresh_field
        skirm.garrison = garrison


def test_a_brain_whose_plugin_has_no_snapshot_port_is_refused_by_name(skirm, monkeypatch):
    monkeypatch.delattr(simai.model()['player'].AIPlayer, 'snapshot', raising=False)    # the stand-in's, below
    with pytest.raises(NotImplementedError, match=r'ra3model\.ai\.player\.AIPlayer \(at .*\.ai\).*snapshot port'):
        simaisnap.snapshot(skirm)


# ---- 11b-4b: the brains' public fields, through a stand-in for the plugin's port (the real one is 11b-4c, in the
# engine model's repository): each plugin object gives its class name and the keys of the Units / things it would
# hold (the tactics: its runs' members), restore checks each key comes back as the new run's object; a Team's key
# is a number given here, the new AI player's team(key) a Team made for that key.
class _Port:
    def __init__(self, mod):
        self.keys, self.back, self.stand = {}, [], {}
        self.teams = mod['teams']

    def snapshot(self, x, key):
        if '_stand_in' in vars(x):          # one written back: its keys again (the stand-in keeps no other state)
            return {'class': type(x).__name__, 'held': [key(u) for u in x._stand_in]}
        runs = getattr(x, 'runs', None) or {}
        return {'class': type(x).__name__,
                'held': [key(u) for r in runs.values() for u in r.team.members]}

    def restore(self, x, data, obj):
        assert data['class'] == type(x).__name__
        x._stand_in = [obj(k) for k in data['held']]
        self.back += list(zip(data['held'], x._stand_in))

    def key(self, team):
        return self.keys.setdefault(id(team), [len(self.keys), team])[0]

    def team(self, k):
        if k not in self.stand:
            t = self.stand[k] = self.teams.Team('restored', 'tactic', None)
            self.keys[id(t)] = [k, t]
        return self.stand[k]


@pytest.fixture(scope='module')
def ported():
    if not simai.available():
        pytest.skip('the engine model (ra3model.ai) is not on this computer')
    mod = simai.model()
    port = _Port(mod)
    mp = pytest.MonkeyPatch()
    classes = [mod['player'].AIPlayer, mod['tactics'].TacticsBlock, mod['targets'].TargetsBlock,
               mod['targets'].View, mod['defense'].DefenseBlock, mod['defense'].Base, mod['micro'].MicroBlock,
               mod['micro'].HuntGoal, mod['specials'].PlayerPowers]
    for c in classes:
        mp.setattr(c, 'snapshot', lambda self, key: port.snapshot(self, key), raising=False)
        mp.setattr(c, 'restore', lambda self, data, obj: port.restore(self, data, obj), raising=False)
    mp.setattr(mod['teams'].Team, 'snapshot_key', lambda self: port.key(self), raising=False)
    mp.setattr(mod['player'].AIPlayer, 'team', lambda self, k: port.team(k), raising=False)
    yield port
    mp.undo()


@pytest.fixture(scope='module')
def half(ported):
    m, t, _ = build.resolve(*simrecord.TASKS['ai_open'][1])
    run = _simai(m, t).advance(int(simrecord.TASKS['ai_open'][2] * FPS / 2))
    b = next(iter(run.brains.values()))
    team = next(iter(b.ai.teams.teams.values()), None) or mod_team(ported)
    b._exp_teams = [(team, (1.0, 2.0))]     # a SimpleExpansion's split (none in this mission)
    taken = simaisnap.snapshot(run)
    restored = _simai(m, t)
    simaisnap.restore(restored, json.loads(json.dumps(taken)))
    return run, taken, restored


def mod_team(port):
    return port.teams.Team('made here', 'tactic', None)


def test_the_brains_taken_and_written_back_equal(half, ported):
    run, taken, restored = half
    assert taken['brains'] and json.loads(json.dumps(taken)) == taken
    assert any(b._protos for b in run.brains.values()) and any(b.wrappers for b in run.brains.values())
    assert simaisnap.snapshot(restored) == taken
    for player, b in run.brains.items():
        nb = restored.brains[player]
        assert nb is not b and nb.made_as == b.made_as
        assert {n: u.body.serial for n, u in nb.wrappers.items()} == {n: u.body.serial for n, u in b.wrappers.items()}
        assert all(u.body is restored.sim.world.numbered[u.body.serial] for u in nb.wrappers.values())
        assert nb.path_rng.random() == b.path_rng.random() and nb.place_rng.getstate() == b.place_rng.getstate()
        assert [(n, p.serial) for n, p in nb._protos.items()] == [(n, p.serial) for n, p in b._protos.items()]
        assert all(p.name not in restored.sim.bodies for p in nb._protos.values())
        (t, p), = nb._exp_teams
        assert p == (1.0, 2.0) and ported.key(t) == ported.key(b._exp_teams[0][0])


def test_the_plugin_gets_the_units_back_as_the_new_brain_wraps_them(half, ported):
    run, taken, restored = half
    units = {id(u) for b in restored.brains.values() for u in b.wrappers.values()}
    assert ported.back and all(id(u) in units for k, u in ported.back if '$unit' in k)


def test_a_brain_kept_on_record_or_without_a_team_lookup_is_refused(half, ported, monkeypatch):
    run, *_ = half
    b = next(iter(run.brains.values()))
    monkeypatch.setattr(b, '_rec_runs', {1: (1, object())})
    with pytest.raises(NotImplementedError, match='record=True'):
        simaisnap.snapshot(run)
    monkeypatch.setattr(b, '_rec_runs', {})
    monkeypatch.delattr(type(b.ai), 'team')
    with pytest.raises(NotImplementedError, match=r'team\(key\)'):
        simaisnap.snapshot(run)
