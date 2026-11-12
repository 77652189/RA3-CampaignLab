"""Named minimum enemy distance replay; work/re/c_mindist_report.md."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)

CASES = [('aimind0', (4, 0, 0, 0)), ('aimindhi', (0, 0, 0, 4)),
         ('aimindctl', (4, 0, 0, 0))]


@pytest.mark.skipif(not simai.available(), reason='no private AI model')
@pytest.mark.parametrize('build, expected', CASES)
def test_min_enemy_distance_named_bench_replay(build, expected):
    w = simai.run(build, 'a', until=41)
    rows = [tuple(values) for second, values in w.sim.series if 40 <= second <= 41]
    assert rows and all(row == expected for row in rows), rows


@pytest.mark.parametrize('build, expected', CASES)
def test_min_enemy_distance_original_readings(build, expected):
    path = Path(simai.labpaths.WORK) / 're/c_mindist_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))[build]
    assert evidence['verdict'] == 'PASS'
    rows = evidence['rows']
    before = max((row for row in rows if row[0] <= 40), key=lambda row: row[0])
    after = min((row for row in rows if row[0] >= 40), key=lambda row: row[0])
    assert all(tuple(row[2]) == expected for row in (before, after))
