"""UnderAttackBy live source selection; work/re/c_underattackby_resume_report.md."""
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)


def readings(build):
    import teamlog
    path = ROOT / f'tests/fixtures/{build}_fight.txt'
    return path, teamlog.target_picks(str(path))


@pytest.mark.parametrize('build', ['aiuabl', 'aiuabw'])
def test_underattackby_native_hit_precedes_source_selection(build):
    import teamlog
    path, rows = readings(build)
    assert rows and all(r['state_id'] == teamlog.state_hash('CNVClosest0') for r in rows)
    events = [dict(re.findall(r'(\w+)=([^\s]+)', line))
              for line in path.read_text().splitlines() if line.startswith('ua: ')]
    hits = [e for e in events if e['ev'] == 'src' and e['obj'] == '3181']
    assert hits and int(hits[0]['frame']) == 18 and int(hits[0]['src']) == 3185
    assert rows[0]['frame'] == 16 and not rows[0]['found']
    if build == 'aiuabl':
        selected = next(r for r in rows if r['found'])
        assert selected['frame'] == 19 > int(hits[0]['frame'])
        assert selected['target'] == int(hits[0]['src'])
        assert selected['point'] == (4000.0, 2830.0)
    else:
        assert all(not r['found'] for r in rows)
    # UnderAttackBy's observer publishes the result, not its source candidate list.
    assert all(r['count'] == 0 and r['candidates'] == [] for r in rows)


@pytest.mark.xfail(strict=True, reason='Water only publishes a pre-hit f16 result; '
    'no direct post-hit selection result or source candidate list. '
    'See work/re/handoff-c.md and work/re/c_underattackby_resume_report.md.')
def test_underattackby_water_has_direct_post_hit_rejection():
    _, rows = readings('aiuabw')
    assert any(r['frame'] > 18 and not r['found'] for r in rows)


@pytest.mark.parametrize('build', ['aiuabl', 'aiuabw'])
def test_underattackby_public_records_match_original_run(build):
    archive = Path(simai.labpaths.WORK) / 're/c_underattackby_resume_measured.json'
    if not archive.exists():
        pytest.skip('private original evidence unavailable')
    original = json.loads(archive.read_text(encoding='utf-8'))[build]
    assert original['result']['verdict'] == 'NOEXPECT'
    assert original['last_frame'] > 120
    for row in original['picks']:
        for key in ('brain', 'state', 'heuristic'):
            row[key] = 'redacted'
    path, rows = readings(build)
    assert json.loads(json.dumps(rows)) == original['picks']
    import teamlog
    assert teamlog.under_attack(str(path)) == original['under_attack']
