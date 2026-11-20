"""Named ForbiddenObjectStatus replay; work/re/c_forbid_report.md."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)
CASES = [('aiforbidnone', (1, 4, 0, 0)), ('aiforbidset', (1, 0, 4, 0)),
         ('aiforbidclear', (0, 4, 0, 0))]
MASK_CASES = [('aifmasknone', (1, 4, 0, 0)), ('aifmaskiron', (1, 0, 4, 0)),
              ('aifmaskboth', (1, 0, 4, 0))]
DUAL_CASES = [('aifdualnone', (3, 4, 0, 0)), ('aifdualboth', (3, 0, 4, 0))]
OBSERVED_CASES = [('aifdualboth', (3, 0, 4, 0)), ('aifunasingle', (2, 0, 4, 0))]


def observed_picks(build):
    import teamlog
    return teamlog.target_picks(str(ROOT / f'tests/fixtures/{build}_target_picks.txt'))


@pytest.mark.parametrize('build,expected', OBSERVED_CASES)
def test_forbidden_observed_original_status_and_counts(build, expected):
    """New runs only; script counters do not stand in for raw runtime status bits."""
    path = Path(simai.labpaths.WORK) / 're/c_forbidnew_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    measured = json.loads(path.read_text(encoding='utf-8'))[build]
    assert measured['verdict'] == 'FAIL'
    rows = [r for r in measured['rows'] if 40 <= r[0] <= 41]
    native_far = 0 if build == 'aifdualboth' else 3
    native_frame = 327 if build == 'aifdualboth' else 363
    assert rows and all(tuple(r[2]) == (expected[0], 0, native_far, 0)
                        and r[1] == native_frame for r in rows), rows
    assert all(r[2][0] == expected[0] for r in measured['rows'])
    original = measured['picks']
    for row in original:
        for key in ('brain', 'state', 'heuristic'):
            row[key] = 'redacted'
    assert json.loads(json.dumps(observed_picks(build))) == original


@pytest.mark.parametrize('build,expected', OBSERVED_CASES)
def test_forbidden_observed_same_frame_qualification(build, expected):
    """Assert the game's own filter result and selected slot, independently of why.stat."""
    import teamlog
    rows = observed_picks(build)
    assert rows
    # Preserve the pre-wake empty call as well as the later qualified call.
    assert rows[0]['frame'] == 16 and not rows[0]['found']
    assert rows[0]['candidates'] == [] and rows[0]['target'] is None
    assert any(row['found'] for row in rows)
    for row in rows:
        assert row['state_id'] == teamlog.state_hash('CNVStateTP') and row['index'] == 0
        assert row['slot'] == 0 and row['more'] == 0
        if not row['found']:
            assert row['candidates'] == [] and row['target'] is None
            continue
        near = next(c for c in row['candidates'] if c['point'] == (3150., 3300.))
        far = next(c for c in row['candidates'] if c['point'] == (3700., 2400.))
        assert not near['ok'] and 'stat' in near['why']
        assert far['ok'] and far['why'] == []
        assert row['target'] == far['id'] and row['point'] == far['point']


@pytest.mark.parametrize('build,expected', OBSERVED_CASES)
def test_forbidden_observed_named_replay(build, expected):
    """Replay the named mission's qualification and selection; timing is checked separately."""
    import ast
    if not simai.available():
        pytest.skip('no private AI model')
    w = simai_run.run(build, 'a', until=41)
    rows = [tuple(v) for second, v in w.sim.series if 40 <= second <= 41]
    assert rows and all(row == expected for row in rows), rows
    brain = w.brains['Soviet_1']
    view = brain.view
    heuristic = w.data_of('targets').heuristic('CNVForbid')
    targets = simai.model()['targets']
    native = [row for row in observed_picks(build) if row['found']]
    assert native
    for candidate in native[0]['candidates']:
        matches = [t for t in view.things if (t.x, t.y) == candidate['point']]
        assert len(matches) == 1, candidate
        # Claims are post-pick here; native qualification was before this slot claimed its target.
        assert targets.candidate_ok(heuristic, view, matches[0], unique=False) == candidate['ok']
    picks = [text for _, kind, text in brain.ai.log
             if kind == 'target' and text.startswith('CNVStateTP: ')]
    assert picks
    things = {t.id: t for t in view.things}
    for text in picks:
        ids = ast.literal_eval(text.split(' -> ')[1])
        assert len(ids) == 1
        assert (things[ids[0]].x, things[ids[0]].y) == native[0]['point']


@pytest.mark.parametrize('build,expected', OBSERVED_CASES)
@pytest.mark.xfail(strict=True, reason='New native checks miss original s40 far=4 expectation '
    '(far=0/3; logical frame=327/363). Capture/model clock alignment unresolved; '
    'see work/re/handoff-c.md and work/re/c_forbidnew_report.md.')
def test_forbidden_observed_original_arrival_prediction(build, expected):
    path = Path(simai.labpaths.WORK) / 're/c_forbidnew_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    measured = json.loads(path.read_text(encoding='utf-8'))[build]
    assert measured['verdict'] == 'PASS', measured['result']['expectations']


@pytest.mark.skipif(not simai.available(), reason='no private AI model')
@pytest.mark.parametrize('build,expected', CASES)
def test_forbidden_status_named_bench_replay(build, expected):
    w = simai_run.run(build, 'a', until=41)
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
    w = simai_run.run(build, 'a', until=41)
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


@pytest.mark.skipif(not simai.available(), reason='no private AI model')
@pytest.mark.parametrize('build,expected', [('aifunanone', (2, 4, 0, 0)),
    ('aifunasingle', (2, 0, 4, 0)), ('aifunaboth', (2, 0, 4, 0))])
def test_forbidden_unattackable_named_bench_replay(build, expected):
    """Only UNATTACKABLE is set; test the other direction of the original mask."""
    w = simai_run.run(build, 'a', until=41)
    rows = [tuple(v) for second, v in w.sim.series if 40 <= second <= 41]
    assert rows and all(row == expected for row in rows), rows


@pytest.mark.parametrize('build,expected', [('aifunanone', (2, 4, 0, 0)),
    ('aifunasingle', (2, 0, 4, 0)), ('aifunaboth', (2, 0, 4, 0))])
def test_forbidden_unattackable_original_readings(build, expected):
    path = Path(simai.labpaths.WORK) / 're/c_forbiduna_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))[build]
    rows = [r for r in evidence['rows'] if 40 <= r[0] <= 41]
    assert rows and all(tuple(r[2]) == expected for r in rows), rows
    status_rows = [r for r in evidence['rows'] if 5 <= r[0] <= 41]
    assert status_rows and all(r[2][0] == 2 for r in status_rows)
    assert evidence['verdict'] == 'PASS', evidence['result']['expectations']


@pytest.mark.skipif(not simai.available(), reason='no private AI model')
@pytest.mark.parametrize('build,expected', DUAL_CASES)
def test_forbidden_dual_status_named_bench_replay(build, expected):
    """Both original mask bits are set, with an empty-filter positive control."""
    w = simai_run.run(build, 'a', until=41)
    rows = [tuple(v) for second, v in w.sim.series if 40 <= second <= 41]
    assert rows and all(row == expected for row in rows), rows


@pytest.mark.parametrize('build,expected', DUAL_CASES)
def test_forbidden_dual_status_original_readings(build, expected):
    path = Path(simai.labpaths.WORK) / 're/c_forbiddual_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))[build]
    rows = [r for r in evidence['rows'] if 40 <= r[0] <= 41]
    assert rows and all(tuple(r[2]) == expected for r in rows), rows
    status_rows = [r for r in evidence['rows'] if 5 <= r[0] <= 41]
    assert status_rows and all(r[2][0] == 3 for r in status_rows)
    assert evidence['verdict'] == 'PASS', evidence['result']['expectations']
