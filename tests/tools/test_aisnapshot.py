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


def test_a_brain_whose_plugin_has_no_snapshot_port_is_refused_by_name(skirm):
    with pytest.raises(NotImplementedError, match=r'ra3model\.ai\.player\.AIPlayer \(at .*\.ai\).*snapshot port'):
        simaisnap.snapshot(skirm)
