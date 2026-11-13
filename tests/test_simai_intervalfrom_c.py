"""C: named CountFrom controls; work/re/c_intervalfrom_report.md."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')


@pytest.mark.parametrize('build,home32', [('aiintmap', 0), ('aiintai', 4)])
def test_interval_countfrom_named_replay(build, home32):
    """Replay the engine home/total readings before and after both origins."""
    w = simai.run(build, 'a', 43, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = {t: dict(zip(labels, values)) for t, values in w.sim.series}
    for second, home in ((24, 4), (32, home32), (42, 0)):
        row = rows[second]
        assert (row['坦克在家'], row['坦克总数']) == (home, 4), (second, row)
