"""E66 measured repair-bay controls; explicit assignment remains unisolated."""
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
