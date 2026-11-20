"""Native EnemyGarrison counterexample replays; work/re/c_enemygarr_report.md."""
import importlib.util
import json
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)
BUILDS = ('aiegarron', 'aiegarroff')
WINDOWS = json.loads((ROOT / 'tests/fixtures/enemy_garrison_windows.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=2)
def replay(build):
    # Use the recorded logical frame window, not the bench's wall seconds.
    return simai_run.run(build, 'a', until=WINDOWS[build] / simai.FPS)


def native_picks(build):
    import teamlog
    return teamlog.target_picks(str(ROOT / f'tests/fixtures/{build}_target_picks.txt'))


@pytest.mark.parametrize('build', BUILDS)
def test_enemy_garrison_native_and_named_control(build):
    import teamlog
    rows = native_picks(build)
    garr = [r for r in rows if r['state_id'] == teamlog.state_hash('CNVStateTP')]
    named = [r for r in rows if r['state_id'] == teamlog.state_hash('CNVEGarrNamedState')]
    assert garr and named
    assert garr[0]['frame'] == named[0]['frame'] == 16
    assert all(r['slot'] == 0 and r['index'] == 0 and not r['found']
               and r['target'] is None and r['count'] == 0 and not r['candidates'] for r in garr)
    assert all(r['slot'] == 1 and r['index'] == 0 and r['found']
               and r['target'] == 3173 and r['point'] == (2900.0, 3300.0) for r in named)


@pytest.mark.parametrize('build', BUILDS)
def test_enemy_garrison_named_bench_replay(build):
    import teamlog
    if not simai.available():
        pytest.skip('no private AI model')
    native = native_picks(build)
    w = replay(build)
    brain = w.brains['Soviet_1']
    control = w.sim.bodies[w.sim.m.role('garr control').name]
    occupant = w.sim.bodies[w.sim.m.role('garr occupant').name]
    assert control.owner == 'Player_1'
    assert ('ENCLOSED' in occupant.status) == (build == 'aiegarron')
    named = next(r for r in native if r['state_id'] == teamlog.state_hash('CNVEGarrNamedState'))
    named_picks = [text for _, kind, text in brain.ai.log
                   if kind == 'target' and text.startswith('CNVEGarrNamedState: ')]
    assert named_picks and named['found']
    assert all(text.endswith(f'-> [{brain.tid(control)}]') for text in named_picks)
    assert (control.x, control.y) == named['point']


@pytest.mark.parametrize('build', [
    pytest.param('aiegarron', marks=pytest.mark.xfail(strict=True, reason=
        'Native occupied enemy house has n=0; model picks an ordinary plant after wake; '
        'post-registration evaluation/search eligibility unresolved: work/re/c_enemygarr_report.md')),
    pytest.param('aiegarroff', marks=pytest.mark.xfail(strict=True, reason=
        'Native ordinary enemy plant control has n=0 but model selects an ordinary plant; '
        'post-registration evaluation/search eligibility unresolved: work/re/c_enemygarr_report.md')),
])
def test_enemy_garrison_native_absence_replay(build):
    import teamlog
    if not simai.available():
        pytest.skip('no private AI model')
    rows = [r for r in native_picks(build) if r['state_id'] == teamlog.state_hash('CNVStateTP')]
    assert rows and all(not r['found'] for r in rows)
    w = replay(build)
    brain = w.brains['Soviet_1']
    picked = [text for _, kind, text in brain.ai.log
              if kind == 'target' and text.startswith('CNVStateTP: ')]
    assert bool(picked) == any(r['found'] for r in rows)


@pytest.mark.parametrize('build', BUILDS)
def test_enemy_garrison_public_evidence_matches_original(build):
    path = Path(simai.labpaths.WORK) / 're/c_egarr_measured.json'
    if not path.exists():
        pytest.skip('private original evidence unavailable')
    original = json.loads(path.read_text(encoding='utf-8'))[build]
    assert WINDOWS[build] == original['last_log_frame']
    assert original['verdict'] == 'PASS'
    assert len(original['expectations']) == 3
    assert all(line.startswith('PASS ') for line in original['expectations'])
    for row in original['picks']:
        for key in ('brain', 'state', 'heuristic'):
            row[key] = 'redacted'
    assert json.loads(json.dumps(native_picks(build))) == original['picks']
