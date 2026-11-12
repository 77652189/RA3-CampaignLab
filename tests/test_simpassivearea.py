"""Independent engineer area healing: replay the named E70 bench."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('area_simbench', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_engineer_area_healing_matches_named_bench():
    import build
    import sim
    m, t, _ = build.resolve('engine_passivearea', 'a')
    engine = sim.Sim(m, t).run(40)
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts


@pytest.mark.xfail(strict=True, reason=(
    'E71 engine_passivearea:f reads 11/11/11/71 frames; continuous integration '
    'reads 2/8/15/75. Survey/heal scheduling unresolved; see work/re/e_passive_e71.md '
    'and work/re/handoff-e.md.'))
def test_engineer_area_frame_thresholds_match_named_bench():
    """E71 engine_passivearea:f: simultaneous early thresholds, then full HP.

    These are latched game-script frames, not screenshot seconds. See
    work/re/e_passive_e71.md for the original readings and timing gap.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_passivearea', 'f')
    engine = sim.Sim(m, t).run(25)
    assert tuple(engine.series[-1][1]) == (11, 11, 11, 71)
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts
