"""C: named no-expansion timer replay; engine evidence in work/re/c_lastexp_report.md."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')


def test_last_expansion_retail_times_named_replay():
    """Compare the measured three home counters, not precise activation frames.

    TimeSinceLastExpansionHeuristic.Time covers retail 60s and 240s with no
    expansion. Reset after expansion, Past=false and frame equality remain gaps.
    """
    w = simai.run('ailastexp', 'a', 286, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = {second: dict(zip(labels, values)) for second, values in w.sim.series}
    for start, expected in ((40, (4, 4, 0)), (100, (0, 4, 0)),
                            (220, (0, 4, 0)), (275, (0, 0, 0))):
        for second in range(start, start + 10):
            assert tuple(rows[second][label] for label in ('六十在家', '二四零家', '常量在家')) == expected, second
