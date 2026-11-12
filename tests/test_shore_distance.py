"""Named shore-distance replay; original evidence: work/re/c_shore_report.md."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)


@pytest.mark.skipif(not simai.available(), reason='no private AI model')
@pytest.mark.parametrize('build, expected_home', [
    ('aishorehi', 0),
    pytest.param('aishorelo', 4, marks=pytest.mark.xfail(strict=True, reason=
        'World bridge supplies default zero shore distance; see work/re/c_shore_report.md')),
    ('aishorectl', 0),
])
def test_shore_distance_named_bench_replay(build, expected_home):
    w = simai.run(build, 'a', until=61)
    rows = [values[0] for second, values in w.sim.series if 60 <= second <= 61]
    assert rows and all(value == expected_home for value in rows), rows


@pytest.mark.parametrize('build, expected_home', [
    ('aishorehi', 0), ('aishorelo', 4), ('aishorectl', 0),
])
def test_shore_distance_original_readings(build, expected_home):
    path = Path(simai.labpaths.WORK) / 're/c_shore_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    rows = json.loads(path.read_text(encoding='utf-8'))[build]['rows']
    goal = 0 if build == 'aishorelo' else 4
    early_before = max((row for row in rows if row[0] <= 20), key=lambda row: row[0])
    early_after = min((row for row in rows if row[0] >= 20), key=lambda row: row[0])
    assert all(row[2][1] == goal for row in (early_before, early_after))
    before = max((row for row in rows if row[0] <= 60), key=lambda row: row[0])
    after = min((row for row in rows if row[0] >= 60), key=lambda row: row[0])
    assert all(row[2][0] == expected_home for row in (before, after))
