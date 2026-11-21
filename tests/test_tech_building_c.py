"""TechBuilding registered-set contrast; work/re/c_techkind_report.md."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)

FIXTURES = ROOT / 'tests/fixtures'


def native_picks(build):
    import teamlog
    return teamlog.target_picks(str(FIXTURES / f'{build}_target_picks.txt'))


@pytest.mark.parametrize('build, tech', [('aitechkind', True), ('aitechnon', False)])
def test_tech_building_same_frame_native_qualification(build, tech):
    """Game candidate filter, selected slot and original counts are independent evidence."""
    import teamlog
    rows = native_picks(build)
    assert rows
    assert all(r['state_id'] == teamlog.state_hash('CNVStateTP') and r['index'] == 0
               and r['more'] == 0 for r in rows)
    first = rows[0]
    assert first['frame'] == 16 and first['slot'] == 0
    assert all(r['found'] for r in rows)
    assert all(r['count'] == len(r['candidates']) == (2 if tech else 1) for r in rows)
    for row in rows:
        # The inherited map also has an oil far outside SearchRange=1200.
        far = next(c for c in row['candidates'] if c['point'] == (700., 3200.))
        assert far['ok'] and far['why'] == []
        near = [c for c in row['candidates'] if c['point'] == (3150., 3300.)]
        if tech:
            assert len(near) == 1 and near[0]['ok'] and near[0]['why'] == []
            assert row['target'] == near[0]['id'] and row['point'] == near[0]['point']
        else:
            assert near == []
            assert row['target'] == far['id'] and row['point'] == far['point']


@pytest.mark.parametrize('build', ['aitechkind', pytest.param('aitechnon',
    marks=pytest.mark.xfail(strict=True,
        reason='Native selects the inherited far oil; model excludes it by search range. '
               'Do not infer live base/range semantics; see work/re/handoff-c.md '
               'and work/re/c_techkind_report.md.'))])
def test_tech_building_named_selection_replays_native_picks(build):
    import ast
    if not simai.available():
        pytest.skip('no private AI model')
    w = simai_run.run(build, 'a', until=3)
    brain = w.brains['Soviet_1']
    picks = [text for _, kind, text in brain.ai.log
             if kind == 'target' and text.startswith('CNVStateTP: ')]
    native = native_picks(build)
    assert native
    if native[0]['found']:
        assert picks
        things = {t.id: t for t in brain.view.things}
        for text in picks:
            ids = ast.literal_eval(text.split(' -> ')[1])
            assert len(ids) == 1
            target = things[ids[0]]
            assert (target.x, target.y) == native[0]['point']
    else:
        assert picks == []


@pytest.mark.parametrize('build, expected', [
    ('aitechkind', [4, 0, 0, 0]), ('aitechnon', [0, 0, 0, 0]),
])
def test_tech_building_original_readings(build, expected):
    path = Path(simai.labpaths.WORK) / 're/c_techkind_measured.json'
    if not path.exists():
        pytest.skip('private original archive unavailable')
    measured = json.loads(path.read_text(encoding='utf-8'))[build]
    assert measured['verdict'] == ('PASS' if build == 'aitechkind' else 'FAIL')
    rows = [r for r in measured['rows'] if 39 <= r[0] <= 42]
    assert rows and all(r[1] is not None and r[2] == expected for r in rows)
    public = native_picks(build)
    original = measured['picks']
    for row in original:
        for key in ('brain', 'state', 'heuristic'):
            row[key] = 'redacted'
    assert json.loads(json.dumps(public)) == original
