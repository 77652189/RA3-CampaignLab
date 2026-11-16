"""Named NeutralGarrison selection replays native readings; work/re/c_garrison_report.md."""
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
BUILDS = ('aigarron', 'aigarroff')


def native_picks(build):
    import teamlog
    return teamlog.target_picks(str(ROOT / f'tests/fixtures/{build}_target_picks.txt'))


@pytest.mark.parametrize('build', BUILDS)
def test_garr_native_selection_and_named_control(build):
    import teamlog
    rows = native_picks(build)
    first = {state: next(r for r in rows if r['state_id'] == teamlog.state_hash(state))
             for state in ('CNVStateTP', 'CNVGarrNamedState')}
    garr, named = first.values()
    assert garr['frame'] == named['frame'] == 16
    assert (garr['slot'], named['slot']) == (0, 1)
    assert garr['index'] == named['index'] == 0
    assert named['found'] and named['target'] > 0
    assert named['point'] == (2900.0, 3300.0)
    assert garr['found']
    assert garr['target'] == 63
    assert garr['point'] == (3180.0, 2760.0)
    # The independent named slot identifies the placed control; it is not
    # the selected map house. Native ok, not a KindOf guess, checks eligibility.
    control = [c for c in garr['candidates'] if c['id'] == named['target']]
    if build == 'aigarron':
        assert len(control) == 1 and control[0]['ok']
        assert control[0]['point'] == named['point']
    else:
        assert not control



@pytest.mark.parametrize('build', BUILDS)
def test_garr_named_bench_replays_native_selection(build):
    import teamlog
    if not simai.available():
        pytest.skip('no private AI model')
    rows = native_picks(build)
    w = simai.run(build, 'a', until=3)
    brain = w.brains['Soviet_1']
    for state in ('CNVStateTP', 'CNVGarrNamedState'):
        native = next(r for r in rows if r['state_id'] == teamlog.state_hash(state))
        picks = [text for _, kind, text in brain.ai.log
                 if kind == 'target' and text.startswith(state + ': ')]
        assert bool(picks) == native['found']
        if picks:
            chosen = {int(re.search(r'-> \[(\d+)\]', text)[1]) for text in picks}
            assert len(chosen) == 1
            obj = next(t for t in brain.view.things if t.id in chosen)
            assert obj.template == ('HV_Shop01' if state == 'CNVStateTP' else w.sim.m.role('garr control').template)
            assert (obj.x, obj.y) == native['point']


@pytest.mark.parametrize('build', BUILDS)
def test_garr_public_readings_match_original(build):
    path = Path(simai.labpaths.WORK) / 're/c_garr_measured.json'
    if not path.exists():
        pytest.skip('private original evidence unavailable')
    original = json.loads(path.read_text(encoding='utf-8'))[build]
    assert original['verdict'] == ('PASS' if build == 'aigarron' else 'FAIL')
    assert len(original['expectations']) == 1
    if build == 'aigarron':
        assert original['expectations'][0].startswith('PASS control alive == 1 from s2 until s3:')
    else:
        assert original['expectations'] == ['FAIL control alive == 1 from s2 until s3: no reading']
    for row in original['picks']:
        for key in ('brain', 'state', 'heuristic'):
            row[key] = 'redacted'
    assert json.loads(json.dumps(native_picks(build))) == original['picks']
