"""Independent engineer area healing: replay the named E70 bench."""
import importlib.util
from pathlib import Path

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
