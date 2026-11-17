"""Native Point selection and named replay; work/re/c_point_resume_report.md."""
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
        reason='Point selector replays observed candidates, but the world still has no '
               'random Point search provider. See work/re/c_point_resume_report.md.')),
    'aipointtiny',
])
def test_point_named_selection_matches_native(build):
    if not simai.available():
        pytest.skip('no private AI model')
    native = resumed_picks(build)
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


def resumed_picks(build):
    import teamlog
    return teamlog.target_picks(str(FIXTURES / f'{build}_point_resume.txt'))


@pytest.mark.parametrize('build,radius,found', [
    ('aipointwater', 1500, True), ('aipointtiny', 1, False),
])
def test_point_resume_native_search_and_named_slot_replay(build, radius, found):
    """Replay the named mission with native candidates, not the selected point."""
    if not simai.available():
        pytest.skip('no private AI model')
    import build as builds
    import teamlog
    from types import SimpleNamespace
    targets = simai.model()['targets']
    mission, _, _ = builds.resolve(build, 'a')
    data = targets.TargetData()
    for _, xml, _ in mission.assets:
        data.add_text(xml)
    hid = 'CNVPointTiny' if radius == 1 else 'CNVPointWater'
    heuristic = data.heuristic(hid)
    assert heuristic.type == 'Point' and heuristic.search_range == radius
    assert heuristic.location == frozenset({'Water'})
    rows = resumed_picks(build)
    assert rows and rows[0]['frame'] == 16
    assert rows[0]['point_search']['anchor'] == 3163
    states = simai.model()['data'].AIData()
    for _, xml, _ in mission.assets:
        states.add_text(xml)
    for row in rows:
        assert row['state_id'] == teamlog.state_hash('CNVStateTP')
        assert row['index'] == row['slot'] == 0 and row['frame'] >= 16
        assert row['found'] == found
        assert row['target'] == (0 if found else None)
        ps = row['point_search']
        assert ps['range'] == radius and ps['mask'] == 1
        assert ps['origin'] == (3850, 3400)
        # Anchor identity is world-owned: tiny switches to 0 at f151 while
        # the supplied search origin remains unchanged; no lifecycle inferred.
        assert ps['tries'] == 40
        assert all(c['threat'] is None for c in ps['candidates'])
        kept = [c for c in ps['candidates'] if c['ok']]
        assert bool(kept) == found and ps['new'] == found
        assert len(ps['candidates']) == (38 if found else 40)
        assert len(kept) == (8 if found else 0)
        search = targets.PointSearch(ps['origin'], tuple(
            targets.PointCandidate(c['point'], c['ok'], c['threat'])
            for c in ps['candidates']))
        calls = []
        def provider(h):
            calls.append(h.id)
            return search
        # No output coordinates are given to the selector. Ordinary objects and
        # the caller origin are deliberately unrelated to the selected base.
        view = targets.View('s1', [], point_search=provider)
        block = targets.TargetsBlock(data, lambda ai, frame: ['CNVStateTP'],
                                     lambda ai, frame: view, lambda ai, sid: (0, 0))
        ai = SimpleNamespace(data=states, rng=None, log=[])
        block.tick(ai, row['frame'])
        tid = block.slot_target('CNVStateTP')
        got = block.points.get(tid)
        assert calls == [hid]
        assert (got is not None) == found
        if found:
            assert (got.x, got.y) == ps['point'][:2]
            assert got.kindof == frozenset({'POINT'})
        else:
            assert kept == []


def test_point_without_world_search_never_uses_an_object():
    if not simai.available():
        pytest.skip('no private AI model')
    targets = simai.model()['targets']
    h = targets.TargetHeuristic('point', 'Point')
    view = targets.View('s1', [targets.Thing(42, 's1', x=1, y=1)])
    assert targets.find(h, view, (0, 0)) is None
