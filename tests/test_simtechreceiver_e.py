"""E167: named retail receiver / Level2-removal bench replay."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('techreceiver_simbench', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


@pytest.mark.parametrize('name', ['engine_techrecvon', 'engine_techrecvoff'])
def test_techreceiver_named_bench_holder_counts(name):
    """f60 baseline, f180 source/receiver counts, f300 source deletion."""
    import build
    import sim
    m, t, _ = build.resolve(name, 'a')
    engine = sim.Sim(m, t).run(23)
    assert [engine.eng.value(c) for c in ('E167Frame', 'E167Base', 'E167Grant', 'E167Gone')] == [330, 15, 15, 15]
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts
    for tag in ('near', 'far'):
        assert engine.bodies[m.role(tag + 'factory').name].alive
        assert not engine.bodies[m.role(tag + 'yard').name].alive
