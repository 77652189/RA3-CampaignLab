"""E146: replay the three treatments from engine_objectbatch:a."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('objectbatch_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


@pytest.mark.parametrize('check_id,family', [
    ('a', 'money'), ('a', 'heal'), ('a', 'drain'),
    ('b', 'money'), ('b', 'gates'), ('b', 'heal'), ('b', 'drain')])
def test_objectbatch_named_bench_readings(check_id, family):
    import build
    import sim
    m, t, _ = build.resolve('engine_objectbatch', check_id)
    # Fixed actual plateaus, independent of the recipe's initial predictions.
    observed = {
        'money': [('money on', 20, '==', 60, 25), ('money off', 2, '==', 0, 25)],
        'heal': [('heal', 3, '==', 50050, 25)],
        'drain': [('drain', 3, '==', 100100, 25)],
        'gates': [('gates', 20, '==', 111111, 25)],
    }
    t.expect = observed[family]
    if check_id == 'b' and family == 'money':
        t.expect = t.expect[:1]  # b replaces the second HUD line with gates.
    engine = sim.Sim(m, t).run(26)
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts
