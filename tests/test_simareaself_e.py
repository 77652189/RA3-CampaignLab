"""E165: replay the measured self-full rejection, preserving the failed prediction."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('areaself_simbench', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_areaself_named_bench_self_not_full():
    """Native a f61=7/f210=6, alive=7; the source-full prediction failed."""
    import build
    import sim
    m, t, _ = build.resolve('engine_areaself', 'a')
    engine = sim.Sim(m, t).run(17)
    assert engine.eng.value('E165Frame') == 240
    assert engine.eng.value('E165Baseline') == 7
    assert engine.eng.value('E165Final') == 6
    assert engine.eng.value('E165Alive') == 7
    bodies = [engine.bodies[m.role(r).name] for r in ('source', 'off', 'ally')]
    # a only established 'source not full', not its exact final HP.
    assert bodies[0].hp < bodies[0].max_hp
    assert [b.hp / b.max_hp * 100 for b in bodies[1:]] == [50, 100]


def test_areaself_named_bench_peer_engineer():
    """Native peer f61=15/f210=15, alive=15: exact HP 50/50/100/100."""
    import build
    import sim
    m, t, _ = build.resolve('engine_areaselfpeer', 'a')
    engine = sim.Sim(m, t).run(17)
    assert [engine.eng.value(c) for c in
            ('E165Frame', 'E165Baseline', 'E165Final', 'E165Alive')] == [240, 15, 15, 15]
    bodies = [engine.bodies[m.role(r).name] for r in ('source', 'off', 'ally', 'peer')]
    assert [b.hp / b.max_hp * 100 for b in bodies] == [50, 50, 100, 100]
    assert all(b.alive for b in bodies)
    assert ('物体模块', 'PassiveAreaEffectBehavior overlap/self') not in engine.unmodeled
    assert ('物体模块', 'PassiveAreaEffectBehavior overlap') not in engine.unmodeled
