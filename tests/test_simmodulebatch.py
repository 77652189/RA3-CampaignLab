"""E145: independent readbacks from the single engine_modulebatch:a plate."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('modulebatch_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


@pytest.mark.parametrize('family', [
    pytest.param('products', marks=pytest.mark.xfail(strict=True, raises=AssertionError,
        reason='E145: factories() checks the base menu without held upgrades; an empty-base factory stays excluded '
               'after CommandSetUpgrade. B production gate; see work/re/e145_modulebatch.md and work/re/handoff-e.md')),
    pytest.param('ready', marks=pytest.mark.xfail(strict=True, raises=AssertionError,
        reason='E145: countdown script action and MonitorSpecialPowerTimerUpdate ready-condition output are missing. '
               'A countdown interface required; see work/re/e145_modulebatch.md and work/re/handoff-e.md')),
    'healed', 'enemy'])
def test_modulebatch_named_bench_readings(family):
    import build
    import sim
    m, t, _ = build.resolve('engine_modulebatch', 'a')
    t.expect = [row for row in t.expect if row[0] == family]
    engine = sim.Sim(m, t).run(35)
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts
