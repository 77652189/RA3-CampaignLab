"""A run's snapshot with the skirmish AI (experimental/cnv/simaisnap.py; step S 11b-4, docs/engine/sim-modules.md
9.2): a SimAI with no brain taken at heal_a's half, through JSON and back equal, written onto a SimAI made anew,
taken again equal (4.2) and run on to the end as the one never stopped; with brains (guard 7's ai_open, the engine
model here) every field of the SimAI, its brains and their Units sorted (4.3); the brains through the plugin's own
port (11b-4c), the two AI tasks of guard 7 written back at half and run on as the ones never stopped."""
import io
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


# ---- 11b-4c: the brains through the plugin's own port (the engine model's ra3model/ai/snapshot.py, a session a
# brain): guard 7's two AI tasks taken at half, through JSON, written onto a SimAI made anew, taken again equal, run
# on to the end as the one never stopped (the Sim's snapshot and the AI's equal at the end).
def _half(task):
    if not simai.available():
        pytest.skip('the engine model (ra3model.ai) is not on this computer')
    _, where, end = simrecord.TASKS[task]
    m, t, _ = build.resolve(*where)
    half = int(end * FPS / 2)
    run = _simai(m, t).advance(half)
    taken = simaisnap.snapshot(run)
    restored = _simai(m, t)
    simaisnap.restore(restored, json.loads(json.dumps(taken)))
    return run, taken, restored, int(end * FPS) - half


@pytest.fixture(scope='module')
def half():
    return _half('ai_open')


def test_the_brains_taken_and_written_back_equal(half):
    run, taken, restored, _ = half
    assert taken['brains'] and json.loads(json.dumps(taken)) == taken
    assert any(b._protos for b in run.brains.values()) and any(b.wrappers for b in run.brains.values())
    assert simaisnap.snapshot(restored) == taken
    for player, b in run.brains.items():
        nb = restored.brains[player]
        assert nb is not b and nb.made_as == b.made_as
        assert {n: u.body.serial for n, u in nb.wrappers.items()} == {n: u.body.serial for n, u in b.wrappers.items()}
        assert all(u.body is restored.sim.world.numbered[u.body.serial] for u in nb.wrappers.values())
        assert [(n, p.serial) for n, p in nb._protos.items()] == [(n, p.serial) for n, p in b._protos.items()]
        assert all(p.name not in restored.sim.bodies for p in nb._protos.values())


def test_one_object_of_the_plugin_held_at_two_places_comes_back_as_one(half):
    run, taken, restored, _ = half
    for player, b in run.brains.items():
        nb = restored.brains[player]
        assert nb.ai is not b.ai and nb.tactics in nb.ai.blocks and nb.targets is nb.tactics.targets
        teams = list(nb.ai.teams.teams.values())
        assert teams and all(r.team in teams for r in nb.tactics.runs.values())
        assert all(nb.tactics.run_of(r.team) is r for r in nb.tactics.runs.values())
        units = {id(u) for u in nb.wrappers.values()}
        assert all(id(u) in units for t in teams for u in t.members)
        assert all(u.team is None or u.team in teams for u in nb.wrappers.values())


@pytest.mark.parametrize('task', ['ai_open', 'ai_crush1'])
def test_an_ai_run_written_back_runs_on_as_the_one_never_stopped(task, half):
    run, taken, restored, rest = half if task == 'ai_open' else _half(task)
    run.advance(rest)
    restored.advance(rest)
    assert simsnap.snapshot(restored.sim) == simsnap.snapshot(run.sim)
    assert simaisnap.snapshot(restored) == simaisnap.snapshot(run)


def test_a_brain_without_the_plugin_port_is_refused(half, monkeypatch):
    run, *_ = half
    monkeypatch.setattr(simaisnap, '_port', lambda w: None)
    with pytest.raises(NotImplementedError, match=r'snapshot \(Taker / Putter\)'):
        simaisnap.snapshot(run)


def test_a_run_on_record_written_back_goes_on_with_the_trail_the_one_never_stopped_writes():
    """11b-4e: SimAI(record=True) (HOOKS 9) cut at ai_crush1's half, a micro update just run and its runs numbered:
    through JSON onto a SimAI made anew with record=True, taken again equal; run on, each brain's trail (frames with
    their run numbers and `updated`, orders, deaths) is the uninterrupted run's, and so are both snapshots."""
    if not simai.available():
        pytest.skip('the engine model (ra3model.ai) is not on this computer')
    _, where, end = simrecord.TASKS['ai_crush1']
    m, t, _ = build.resolve(*where)

    def made():
        return simai.SimAI(sim.Sim(m, t, model=False), record=True)
    half, rest = int(end * FPS / 2), int(end * FPS) - int(end * FPS / 2)
    run = made().advance(half)
    recs = [b for b in run.brains.values() if b._rec_runs]
    assert recs and any(b._rec_mem for b in recs)
    taken = simaisnap.snapshot(run)
    assert json.loads(json.dumps(taken)) == taken
    restored = made()
    simaisnap.restore(restored, json.loads(json.dumps(taken)))
    assert simaisnap.snapshot(restored) == taken
    for player, b in run.brains.items():
        nb = restored.brains[player]
        assert len(nb._rec_runs) == len(b._rec_runs) and not set(map(id, nb._rec_runs)) & set(map(id, b._rec_runs))
        live = list(nb.tactics.runs.values())       # a run the tactics still hold is the very one the trail numbers
        assert all(any(x is r for x in nb._rec_runs) for r in live)
    run.advance(rest)
    restored.advance(rest)
    for player, b in run.brains.items():
        assert len(b.rec['frames']) > 0 and restored.brains[player].rec == b.rec
    assert any(f['updated'] for b in run.brains.values() for f in b.rec['frames'] if f['frame'] > half)
    assert simsnap.snapshot(restored.sim) == simsnap.snapshot(run.sim)
    assert simaisnap.snapshot(restored) == simaisnap.snapshot(run)


def test_a_closure_the_plugin_holds_is_named_not_dropped(half, monkeypatch):
    run, *_ = half
    b = next(iter(run.brains.values()))
    monkeypatch.setattr(b.tactics, 'held_note', [lambda: 0], raising=False)     # a closure in a list: no new object
    taken = simaisnap.snapshot(run)                                             # can get it back
    with pytest.raises(ValueError, match='held_note.*closure'):
        simaisnap.restore(_simai(*build.resolve(*simrecord.TASKS['ai_open'][1])[:2]), json.loads(json.dumps(taken)))


# ---- review 1119k (P3, with 11b-4c)
def test_a_returner_comes_back_with_its_facility_and_the_path_it_walks():
    m, t, _ = build.resolve(*_WHERE)
    run = _simai(m, t).advance(HALF)
    u, g = [b for b in run.sim.bodies.values() if b.alive][:2]
    u.path = [(1.0, 2.0)]
    run.pullback.returning[u.name] = (g, u.move_to, u.owner, u.path)
    restored = _simai(m, t)
    simaisnap.restore(restored, json.loads(json.dumps(simaisnap.snapshot(run))))
    ng, dest, owner, path = restored.pullback.returning[u.name]
    assert ng is restored.sim.world.numbered[g.serial] and path is restored.sim.bodies[u.name].path


def test_a_returner_a_later_order_cancelled_stays_cancelled():
    """1119p #2: a later order gave the unit a new path equal to the one send saw; busy (by identity) has it
    cancelled -- written back it stays so, not tied again to the unit's path by its points."""
    m, t, _ = build.resolve(*_WHERE)
    run = _simai(m, t).advance(HALF)
    u, g = [b for b in run.sim.bodies.values() if b.alive][:2]
    seen = [(1.0, 2.0), (3.0, 4.0)]
    run.pullback.returning[u.name] = (g, u.move_to, u.owner, seen)
    u.path = list(seen)                 # the later order's: the same points, another path
    restored = _simai(m, t)
    taken = simaisnap.snapshot(run)
    simaisnap.restore(restored, json.loads(json.dumps(taken)))
    path = restored.pullback.returning[u.name][3]
    assert path == seen and path is not restored.sim.bodies[u.name].path
    assert simaisnap.snapshot(restored) == taken


def test_a_private_slot_is_scanned_under_its_mangled_name():
    class Slotted:
        __slots__ = ('plain', '__hidden')

    x = Slotted()
    x.plain, x._Slotted__hidden = 8, 9
    assert simsnap._fields(x) == {'plain': 8, '_Slotted__hidden': 9}


def test_a_snapshot_missing_a_kernel_field_is_refused_before_anything_is_written(heal):
    m, t, run, taken, _ = heal
    s = json.loads(json.dumps(taken['sim']))
    del s['kernel']['late']
    fresh = sim.Sim(m, t, model=False)
    before = simsnap.snapshot(fresh)
    with pytest.raises(ValueError, match="kernel.*late"):
        simsnap.restore(fresh, s)
    assert simsnap.snapshot(fresh) == before


# ---- review 1119m (with 11b-4c's push)
class _DerivedAI(simai.SimAI):
    """A host's SimAI subclass declared in a module with no Brain or Unit (1119m #3: restore read them from here)."""


def test_a_simai_subclass_declared_where_no_brain_is_is_restored(heal, half):
    """1119m #3: written onto a SimAI subclass from another module: with no brain (none looked for), and with
    brains (Brain and Unit found along the subclass's classes, simai's)."""
    m, t, run, taken, _ = heal
    w = _DerivedAI(sim.Sim(m, t, model=False))
    simaisnap.restore(w, json.loads(json.dumps(taken)))
    assert simaisnap.snapshot(w) == taken
    _, taken, _, _ = half
    w = _DerivedAI(sim.Sim(*build.resolve(*simrecord.TASKS['ai_open'][1])[:2], model=False))
    simaisnap.restore(w, json.loads(json.dumps(taken)))
    assert all(type(b) is simai.Brain for b in w.brains.values())
    assert simaisnap.snapshot(w) == taken


def test_an_older_sim_part_is_refused_before_a_brain_is_made(half):
    """1119m #1: the Sim's part of another version (a v5 one's spy on its way broke the first tick) is refused before
    restore makes the brains (making one multiplies its player's income): nothing written."""
    _, taken, _, _ = half
    old = json.loads(json.dumps(taken))
    old['sim']['version'] = simsnap.VERSION - 1
    w = _simai(*build.resolve(*simrecord.TASKS['ai_open'][1])[:2])
    before = simsnap.snapshot(w.sim)
    with pytest.raises(ValueError, match=f'version {simsnap.VERSION - 1}'):
        simaisnap.restore(w, old)
    assert not w.brains and simsnap.snapshot(w.sim) == before


def test_guard_7_takes_an_ai_task_cut_and_its_record_goes_on_as_the_whole_one():
    """11b-4d: `simrecord snap` on an AI task (run_task through simaisnap): the record of the run taken at half,
    written back onto a SimAI made anew and run on is the whole run's line for line, the ends (the AI's snapshot with
    its brains, the report) the same."""
    if not simai.available():
        pytest.skip('the engine model (ra3model.ai) is not on this computer')
    assert 'ai_crush1' in simrecord.SNAP_TASKS and 'ai_open' in simrecord.SNAP_TASKS
    outs, ends = [], []
    for snap in ('whole', '0.5'):
        out = io.StringIO()
        s, rec = simrecord.run_task('ai_crush1', out, snap=snap)
        outs.append(out.getvalue())
        ends.append(json.loads(json.dumps(rec.end)))
    assert rec.snap['at'] > 0 and 'brains' in ends[1]['snapshot'] and ends[1]['snapshot']['brains']
    assert outs[0].count(chr(10)) > 10 and outs[0] == outs[1]
    assert simrecord.differences(ends[0]['snapshot'], ends[1]['snapshot']) == []
    assert ends[0]['report'] == ends[1]['report']
