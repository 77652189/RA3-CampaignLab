"""E176: named retail pack-status removal control, observed on the bench."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('specialability_simbench', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_specialability_named_bench():
    import build
    import sim
    m, t, _ = build.resolve('engine_specialability_e', 'a')
    engine = sim.Sim(m, t).run(17)
    assert [engine.eng.value(c) for c in
            ('E176Frame', 'E176Ever', 'E176On', 'E176Off')] == [240, 13, 4, 4]
