"""E175: named turbine bench replay; exact power bits, not presence of a name."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('powerupgrade_simbench', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E175: original advanced plant has campaign power 500, simulator 350; '
    'turbine upgrade possession was never observed. See work/re/e175_powerupgrade.md '
    'and work/re/handoff-e.md; no inferred turbine effect implemented.'))
def test_powerupgrade_named_bench():
    import build
    import sim
    m, t, _ = build.resolve('engine_powerupgrade_e', 'a')
    engine = sim.Sim(m, t).run(23)
    assert [engine.eng.value(c) for c in
            ('E175Frame', 'E175Base', 'E175Grant', 'E175Remove')] == [330, 11, 10, 11]


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E175: bench grant interval holds no turbine upgrade; simulator grants an '
    'unresolved upgrade and misses advanced plant campaign power 500. '
    'See work/re/e175_powerupgrade.md and work/re/handoff-e.md.'))
def test_powerupgrade_diagnostic_named_bench():
    import build
    import sim
    from model import Script
    m, t, _ = build.resolve('engine_powerupgrade_e', 'b')
    # At frame 182 all four exact candidate values were observed, none held UP.
    # 330 is the frozen endpoint. Clock arithmetic equals the captured unrolled stamps.
    observed = {182: [18200100, 18200100, 18200500, 18200350],
                330: [33000100, 33000100, 33000500, 33000350]}
    for frame in observed:
        t.scripts.append(Script(f'Test - replay snapshot {frame}',
            [('COUNTER', 'E175Frame', 2, frame)],
            [('SET_COUNTER_TO_COUNTER', f'Replay{frame}_{i}', f'E175Read{i}') for i in range(4)]))
    engine = sim.Sim(m, t).run(23)
    for frame, expected in observed.items():
        assert [engine.eng.value(f'Replay{frame}_{i}') for i in range(4)] == expected
