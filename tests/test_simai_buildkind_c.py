"""Named replays of C's active-construction KindOf comparison."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')


@pytest.mark.parametrize('build,target,home', [
    ('aibkindyes', 4, 0), ('aibkindno', 0, 4),
    ('aibkindoryes', 4, 0), ('aibkindorno', 0, 4)])
def test_building_kind_active(build, target, home):
    """engine_aibuildkind a measured s40: 4/0/4/1 and 0/4/4/1.

    The pre-run >=2-plant control checks production participation; exact
    production timing is outside this KindOf comparison. The multi-token
    controls measured the same rows: only the second token matches in the
    positive case; neither matches in the negative. Original thresholds and
    model are unchanged. See work/re/c_buildkind_or_report.md and
    work/re/c_buildkind_report.md. Queue cancellation/suspension remain gaps.
    """
    w = simai.run(build, 'a', 41, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = [dict(zip(labels, values)) for t, values in w.sim.series if t == 40]
    assert len(rows) == 1
    row, = rows
    assert (row['到陆厂'], row['在家']) == (target, home), row
    assert row['电厂数'] >= 2, row
    assert row['基地数'] == 1, row
