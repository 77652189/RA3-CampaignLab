"""E153 named Athena activation, observed bits and expiration, not forced states."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('activate_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_activate_athena_named_observations():
    import build
    import sim
    from parts import Script
    m, t, _ = build.resolve('engine_activate', 'a')
    # Two actual same-frame HUD observations, independent of the latch predicate.
    for frame, value in [(152, 111), (379, 100)]:
        t.scripts.append(Script('Test - E153 measured ' + str(frame), [
            ('COUNTER', 'E153Frame', 2, frame), ('COUNTER', 'E153on', 2, value),
            ('COUNTER', 'E153off', 2, 100)], [('SET_COUNTER', 'E153Match' + str(frame), 1)]))
    engine = sim.Sim(m, t).run(32)
    assert engine.eng.value('E153Evidence') == 7, {
        name: engine.eng.value(name) for name in ('E153Frame', 'E153on', 'E153off', 'E153Evidence')}
    assert engine.eng.value('E153Match152') == engine.eng.value('E153Match379') == 1
