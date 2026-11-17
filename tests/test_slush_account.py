"""Named SLUSH_FUND bench replay; evidence in work/re/c_slush_report.md."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')


@pytest.mark.parametrize('build, expected', [('aislush100', 2), ('aislush0', 2)])
def test_slush_named_bench_replay(build, expected):
    w = simai.run(build, 'a', until=41)
    rows = [values[0] for second, values in w.sim.series if 40 <= second <= 41]
    assert rows and all(value == expected for value in rows), rows


@pytest.mark.parametrize('build, slush', [('aislsdef', True), ('aislddef', False)])
def test_slush_defense_named_bench_replay(build, slush):
    w = simai.run(build, 'd', until=61)
    rows = [values[0] for second, values in w.sim.series if 60 <= second <= 61]
    assert rows
    assert all(value == (0 if slush else 2) for value in rows), rows


@pytest.mark.parametrize('build, second, expected', [
    ('aislush100', 40, 2), ('aislush0', 40, 2),
    ('aislsdef', 60, 0), ('aislddef', 60, 2),
])
def test_slush_original_readings(build, second, expected):
    path = Path(simai.labpaths.WORK) / 're/c_slush_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    rows = json.loads(path.read_text(encoding='utf-8'))[build]['rows']
    # Image captures can straddle the requested second. Check the nearest
    # original sample on EACH side instead of pretending an exact frame exists.
    before = max((row for row in rows if row[0] <= second), key=lambda row: row[0])
    after = min((row for row in rows if row[0] >= second), key=lambda row: row[0])
    window = [row[2][0] for row in (before, after)]
    assert all(value == expected for value in window)
