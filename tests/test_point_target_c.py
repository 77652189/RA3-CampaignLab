"""Native Point selection and named model replay; work/re/c_point_report.md."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
FIXTURES = ROOT / 'tests/fixtures'


def native_picks(build):
    import teamlog
    return teamlog.target_picks(str(FIXTURES / f'{build}_target_picks.txt'))


@pytest.mark.parametrize('build', ['aipointwater', 'aipointtiny'])
def test_point_native_water_search_finds_a_non_object_target(build):
    import teamlog
    rows = native_picks(build)
    assert rows and rows[0]['frame'] == 16
    for row in rows:
        assert row['state_id'] == teamlog.state_hash('CNVStateTP')
        assert row['slot'] == row['index'] == 0
        assert row['found'] and row['target'] == 0
        assert row['sort'] == 'ThreatToWater'
        assert row['count'] == row['more'] == 0 and row['candidates'] == []
    # This observer resolves coordinates through object IDs. A Point has no
    # object: its recorded (0, 0) is not evidence for the chosen location.


@pytest.mark.parametrize('build', [
    pytest.param('aipointwater', marks=pytest.mark.xfail(strict=True,
        reason='Native Point finds a location; model has no Point candidate provider. '
               'Actual point coordinates/search inputs are unavailable; '
               'see work/re/handoff-c.md and work/re/c_point_report.md.')),
    pytest.param('aipointtiny', marks=pytest.mark.xfail(strict=True,
        reason='Native range-1 Point also succeeds; model selects nothing. '
               'Search origin/candidate generation unresolved; '
               'see work/re/handoff-c.md and work/re/c_point_report.md.')),
])
def test_point_named_selection_matches_native(build):
    if not simai.available():
        pytest.skip('no private AI model')
    native = native_picks(build)
    assert native
    w = simai.run(build, 'a', until=3)
    brain = w.brains['Soviet_1']
    picks = [text for _, kind, text in brain.ai.log
             if kind == 'target' and text.startswith('CNVStateTP: ')]
    if native[0]['found']:
        assert picks
    else:
        assert picks == []


@pytest.mark.parametrize('build', ['aipointwater', 'aipointtiny'])
def test_point_original_controls_and_public_records(build):
    path = Path(simai.labpaths.WORK) / 're/c_point_measured.json'
    if not path.exists():
        pytest.skip('private original archive unavailable')
    measured = json.loads(path.read_text(encoding='utf-8'))[build]
    assert measured['verdict'] == 'PASS'
    rows = [r for r in measured['rows'] if 25 <= r[0] <= 26]
    assert rows and all(r[1] is not None and r[2] == [4, 0] for r in rows)
    original = measured['picks']
    for row in original:
        for key in ('brain', 'state', 'heuristic'):
            row[key] = 'redacted'
    assert json.loads(json.dumps(native_picks(build))) == original


@pytest.mark.xfail(strict=True, reason='Pre-run range-1 no-point prediction failed: '
    'native found=1 at frame 16; real search origin and point not observed. '
    'See work/re/handoff-c.md and work/re/c_point_report.md.')
def test_point_original_tiny_range_negative_prediction():
    rows = native_picks('aipointtiny')
    assert rows
    assert all(not row['found'] for row in rows)
