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
    'E72 engine_passivearea:f reads 11/31/51/71 frames (20/20/20 gaps); '
    'continuous integration reads 2/21/42/62. Initial survey phase unresolved; '
    'see work/re/e_passive_e72.md and work/re/handoff-e.md.'))
def test_engineer_area_frame_thresholds_match_named_bench():
    """E72 engine_passivearea:f: intermediate heal crossings.

    Bench readings: 51/64/78/91 cross at 11/31/51/71 script frames,
    matching the pre-run 20/20/20 gap prediction. First phase remains a gap.
    See work/re/e_passive_e72.md.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_passivearea', 'f')
    engine = sim.Sim(m, t).run(25)
    counts = tuple(engine.series[-1][1])
    assert counts == (11, 31, 51, 71)
    assert tuple(b - a for a, b in zip(counts, counts[1:])) == (20, 20, 20), counts
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts
