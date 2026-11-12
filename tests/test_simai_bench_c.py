"""C-line replays of named AI bench counters; evidence: work/re/c_release_report.md."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)

pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')


@pytest.mark.xfail(strict=True, reason='aiskirm:m replay has no populated Cleanup counter through 170s; '
                  'retail transfers defense 8 -> Cleanup 8. Named-team observation or release consumer '
                  'needs B investigation; no model change or inventory promotion. '
                  'See work/re/handoff-c.md and work/re/c_release_report.md.')
def test_release_to_priority_transfers_defense_without_a_pool_round_trip():
    """aiskirm:m: defense 8 -> 0, Cleanup 99 -> 8, pool peak 1 at transfer.

    This observes the stock DEFENSE -> STANDARD release path only. Other release
    modes and recruitment distance ordering remain gaps; no exact-second fit.
    """
    lib = simai.model()['xmldata'].Library()
    w = simai.run('aiskirm', 'm', until=170, lib=lib)
    labels = [label for _, label in w.sim.test.counters]
    rows = [(t, dict(zip(labels, values))) for t, values in w.sim.series]
    first = next((i for i, (_, row) in enumerate(rows) if row['清扫'] not in (0, 99)), None)
    observed = {label: sorted({row[label] for _, row in rows}) for label in labels}
    (brain,) = w.brains.values()
    assert first is not None, (observed, [e for e in brain.ai.teams.log if e[1] == 'go'])
    before, after = rows[first - 1][1], rows[first][1]
    assert (before['防御型'], before['清扫']) == (8, 99), rows[max(0, first - 2):first + 2]
    assert (after['防御型'], after['清扫']) == (0, 8), rows[max(0, first - 2):first + 2]
    assert after['池峰'] == 1
    assert any(row['池峰'] == 2 for _, row in rows[first:])
