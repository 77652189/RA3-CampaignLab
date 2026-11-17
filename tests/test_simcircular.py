"""E143 negative diagnostic, not CircularDamageUpdate effect acceptance.

engine_circular a/b/c/d: marker hit at frame 2, radial rows never damaged.
See work/re/e143_circular_gate.md; no consumer is inferred from these readings.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench_circular', ROOT / 'experimental/cnv/simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)


@pytest.mark.parametrize('check', ['a', 'b', 'c', 'd'])
def test_circular_negative_diagnostic_keeps_radial_rows_healthy_and_marker_fires(check):
    import build
    import sim
    m, t, _ = build.resolve('engine_circular', check)
    engine = sim.Sim(m, t)
    engine.shot_clock = True
    result = engine.run(15.0)
    # Bench: all three radial counters continue together; marker freezes at 2.
    # Their absolute unbounded counters are not aligned to bench wall seconds.
    assert result.series[-1][1][3] == 2
    assert len(set(result.series[-1][1][:3])) == 1
    bodies = {b.name: b for b in engine.living()}
    assert [bodies[f'UNIT - Circle Target {k}'].hp for k in range(3)] == [10000.0] * 3
