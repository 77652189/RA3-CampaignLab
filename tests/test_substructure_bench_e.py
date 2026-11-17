"""E189 standalone substructure control; not parent/child effect coverage."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('substructure_simbench', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_substructure_standalone_named_bench():
    import build
    import sim

    mission, check, _ = build.resolve('engine_substructure_e', 'a')
    result = sim.Sim(mission, check).run(17)
    assert [result.eng.value(counter) for counter in
            ('E189Frame', 'E189On', 'E189Off', 'E189Yard')] == [240, 80, 80, 0]
