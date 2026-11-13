"""EnemyFilter named-host replay; original evidence: work/re/c_enemyfilter_report.md."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)


@pytest.mark.skipif(not simai.available(), reason='no private AI model')
@pytest.mark.parametrize('build, expected_home', [('aiefharv', 0), ('aiefeng', 4), ('aiefself', 4)])
# the model reads EnemyNearby's EnemyFilter (Relationship picks the owners, the filter the templates): B round 155
def test_enemyfilter_named_bench_replay(build, expected_home):
    w = simai.run(build, 'a', until=61)
    rows = [values[0] for second, values in w.sim.series if 60 <= second <= 61]
    assert rows and all(value == expected_home for value in rows), rows


@pytest.mark.parametrize('build, expected_home', [('aiefharv', 0), ('aiefeng', 4), ('aiefself', 4)])
def test_enemyfilter_original_readings(build, expected_home):
    path = Path(simai.labpaths.WORK) / 're/c_enemyfilter_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    rows = json.loads(path.read_text(encoding='utf-8'))[build]['rows']
    for second, expected in [(20, [expected_home, 4 if build == 'aiefharv' else 0]),
                             (60, [expected_home, 0])]:
        before = max((row for row in rows if row[0] <= second), key=lambda row: row[0])
        after = min((row for row in rows if row[0] >= second), key=lambda row: row[0])
        assert all(row[2] == expected for row in (before, after))
