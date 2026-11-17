"""E166: named dual-source plate, with a single-source and inactive control."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('areaoverlap_simbench', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_areaoverlap_named_bench_two_sources():
    """Native a: f61=31/f100=29/f210=31; additive prediction rejected."""
    import build
    import sim
    m, t, _ = build.resolve('engine_areaoverlap', 'a')
    engine = sim.Sim(m, t).run(17)
    assert [engine.eng.value(c) for c in
            ('E166Frame', 'E166Base', 'E166Mid', 'E166Late')] == [240, 31, 29, 31]
    assert [engine.bodies[m.role(r).name].hp / engine.bodies[m.role(r).name].max_hp * 100
            for r in ('single', 'double', 'off')] == [100, 100, 50]
    assert ('物体模块', 'PassiveAreaEffectBehavior overlap') not in engine.unmodeled


def test_areaoverlap_named_bench_nonstack_band():
    """b discriminates single-rate from additive healing at f100."""
    import build
    import sim
    m, t, _ = build.resolve('engine_areaoverlap', 'b')
    engine = sim.Sim(m, t).run(17)
    assert [engine.eng.value(c) for c in
            ('E166Frame', 'E166Base', 'E166Mid', 'E166Late')] == [240, 31, 31, 31]
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts
    assert ('物体模块', 'PassiveAreaEffectBehavior overlap') not in engine.unmodeled
