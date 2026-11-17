"""E163: replay the measured cross-player Friend snapshot; enemy is unmeasured."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('areaally_simbench', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_areaally_named_bench_friend_snapshot():
    """Bench b f240: own/foreign full, inactive half, source full => 15.

    b ended at f448, before the f450 enemy/position snapshots. Neither those
    missing snapshots nor the failed capture-second expectations are asserted.
    See work/re/e163_areaally.md.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_areaally', 'b')
    engine = sim.Sim(m, t).run(17)
    assert engine.eng.value('E163Friend') == 15
    assert engine.eng.value('E163Enemy') == 0
    assert engine.eng.value('E163Position') == 0
