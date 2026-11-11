"""Full PullbackInjuredHealthPct replay; no injected facility or orders."""
from test_simai_bench_b import lib, _probe_run, pytestmark  # noqa: F401
import pytest


def test_pullback_threshold_low_reaches_the_fight(lib):
    """checks/engine_aipullpct.py: 30% is above threshold 0.2 initially."""
    _, rows = _probe_run('aipullpctlo', lib, 40.0)
    assert any(r['血量'] == 30 for r in rows[8:13])
    assert any(r['到远厂'] >= 3 for r in rows)
    # Bench reaches the plant s15-17, then one survivor returns at s34 after
    # further injury. This is an initial non-trigger control, never "no return".
    assert all(r['回家'] == 0 for r in rows[14:30])


@pytest.mark.xfail(strict=True, reason='Full replay has no pullback facility hook: high 0.5 reaches the '
                   'far plant with four tanks and never returns in 40s; Soviet Crane return/recycling '
                   'consumer is missing. See work/re/handoff-c.md, Pullback threshold interface gap.')
def test_pullback_threshold_high_returns_before_recycling(lib):
    """checks/engine_aipullpct.py: threshold 0.5 sends the same 30% tanks home."""
    _, rows = _probe_run('aipullpcthi', lib, 40.0)
    assert any(r['血量'] == 30 for r in rows[8:13])
    home = next((i for i, r in enumerate(rows[14:], 14) if r['回家'] >= 1), None)
    assert home is not None
    assert any(r['回家'] == 4 for r in rows[home:])
    assert all(r['到远厂'] == 0 for r in rows)
    assert any(r['坦克数'] == 0 for r in rows[home + 1:])
