"""Named ForbiddenObjectStatus replay; work/re/c_forbid_report.md."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
CASES = [('aiforbidnone', (1, 4, 0, 0)), ('aiforbidset', (1, 0, 4, 0)),
         ('aiforbidclear', (0, 4, 0, 0))]
MASK_CASES = [('aifmasknone', (1, 4, 0, 0)), ('aifmaskiron', (1, 0, 4, 0)),
              ('aifmaskboth', (1, 0, 4, 0))]


@pytest.mark.skipif(not simai.available(), reason='no private AI model')
@pytest.mark.parametrize('build,expected', CASES)
def test_forbidden_status_named_bench_replay(build, expected):
    w = simai.run(build, 'a', until=41)
    rows = [tuple(v) for second, v in w.sim.series if 40 <= second <= 41]
    assert rows and all(row == expected for row in rows), rows


@pytest.mark.parametrize('build,expected', CASES)
def test_forbidden_status_original_readings(build, expected):
    path = Path(simai.labpaths.WORK) / 're/c_forbid_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))[build]
    rows = [r for r in evidence['rows'] if 40 <= r[0] <= 41]
    assert rows and all(tuple(r[2]) == expected for r in rows), rows
    status_rows = [r for r in evidence['rows'] if 5 <= r[0] <= 41]
    assert status_rows and all(r[2][0] == expected[0] for r in status_rows)
    assert evidence['verdict'] == 'PASS', evidence['result']['expectations']


@pytest.mark.skipif(not simai.available(), reason='no private AI model')
@pytest.mark.parametrize('build,expected', MASK_CASES)
def test_forbidden_mask_named_bench_replay(build, expected):
    """Only IRON is set: the original two-bit mask excludes on ANY overlap."""
    w = simai.run(build, 'a', until=41)
    rows = [tuple(v) for second, v in w.sim.series if 40 <= second <= 41]
    assert rows and all(row == expected for row in rows), rows


@pytest.mark.parametrize('build,expected', MASK_CASES)
def test_forbidden_mask_original_readings(build, expected):
    path = Path(simai.labpaths.WORK) / 're/c_forbidmask_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))[build]
    rows = [r for r in evidence['rows'] if 40 <= r[0] <= 41]
    assert rows and all(tuple(r[2]) == expected for r in rows), rows
    # The status counter is IRON + 2*UNATTACKABLE, not a model target.
    status_rows = [r for r in evidence['rows'] if 5 <= r[0] <= 41]
    assert status_rows and all(r[2][0] == 1 for r in status_rows)
    assert evidence['verdict'] == 'PASS', evidence['result']['expectations']
