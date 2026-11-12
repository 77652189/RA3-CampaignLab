"""E66 automatic controls and E67 isolated explicit-target healing."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('assign_simbench', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


@pytest.mark.parametrize('mission', ['engine_assignon', 'engine_assignoff'])
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E66: retail drone auto-acquisition/repair not modeled; both controls heal '
    '20->100 with status 10->110->0, cast event on/off=1/0. Explicit assignment '
    'is not isolated: see work/re/handoff-e.md and work/re/e_assign_e66.md'))
def test_repair_bay_assignment_controls_match_named_bench(mission):
    """Replay actual health/status/cast readings, without crediting auto-repair to dispatch."""
    import build
    import sim
    m, t, _ = build.resolve(mission, 'a')
    engine = sim.Sim(m, t).run(28)
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E67: explicit command changes fourth-target healing with three repair '
    'statuses still set. Occupancy/status cleanup and capture-time alignment '
    'remain unresolved. See work/re/e_assign_e68.md '
    'and work/re/handoff-e.md'))
def test_repair_assignment_competition_occupancy_and_timing_match_named_bench():
    """Both lanes occupied three targets; only the commanded fourth healed."""
    import build
    import sim
    m, t, _ = build.resolve('engine_assignrace', 'a')
    engine = sim.Sim(m, t).run(28)
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E68: E67 capture endpoint is 92/20, but capture indexes cannot yet be '
    'aligned with mission time at SDK 480 HP / 20 HP per second. Do not fit '
    'the rate or duration to the endpoint. See work/re/e_assign_e68.md '
    'and work/re/handoff-e.md'))
def test_repair_assignment_competition_explicit_healing_matches_named_bench():
    """Retain every original HP observation, with occupancy tested separately."""
    import build
    import sim
    m, t, _ = build.resolve('engine_assignrace', 'a')
    t.expect = [expect for expect in t.expect if 'HP' in expect[0]]
    engine = sim.Sim(m, t).run(28)
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts


def test_repair_assignment_competition_only_explicit_target_heals():
    """E67 direction and control: commanded target heals; control stays at 20%."""
    import build
    import sim
    m, t, _ = build.resolve('engine_assignrace', 'a')
    engine = sim.Sim(m, t).run(25)
    on = engine.body(m.role('on3').name)
    off = engine.body(m.role('off3').name)
    assert on.hp > on.max_hp * .2
    assert int(off.hp * 100 / off.max_hp) == 20
    assert any('AssignSlaves' in str(g) for g in engine.unmodeled)
