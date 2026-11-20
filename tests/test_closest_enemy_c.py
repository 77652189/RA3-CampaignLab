"""Named land ClosestToEnemy replay; work/re/c_closest_report.md.

Only the measured land slice is asserted. Water and refinery filtering are gaps.
"""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)


def test_closest_enemy_original_readings():
    import json
    path = Path(simai.labpaths.WORK) / 're/c_closest_measured.json'
    if not path.exists():
        pytest.skip('private original readings unavailable')
    measured = json.loads(path.read_text(encoding='utf-8'))
    assert measured['build'] == 'aiclosest'
    for second in range(55, 61):
        assert measured['rows'][str(second)] == [4, 4, 0, 0]


def test_closest_enemy_teamlog_reads_unpadded_state_hash(monkeypatch):
    import teamlog
    monkeypatch.setattr(teamlog, '_hashed', lambda name: '019dcc78')
    names = teamlog._wants('CNVClosest0')
    assert teamlog._named({'names': ('Soviet_1', '19dcc78_StaticDefense_0_0')}, names)
    assert teamlog._named({'names': ('Soviet_1', '019dcc78_StaticDefense_0_0')}, names)
    assert not teamlog._named({'names': ('Soviet_1', '19dcc789_StaticDefense_0_0')}, names)


PICKS = ROOT / 'tests/fixtures/aiclosest_target_picks.txt'


def test_closest_enemy_same_frame_native_selection():
    """D158 run CampClosestA_mcp_1115_094417; only process tokens redacted."""
    import teamlog
    rows = teamlog.target_picks(str(PICKS))
    assert [r['slot'] for r in rows] == [0, 1, 2, 3]
    assert all(r['frame'] == 16 and r['sort'] == 'ClosestToEnemy' and r['found']
               and r['count'] == 4 and r['more'] == 0 for r in rows)
    assert [r['point'] for r in rows] == [(3700., 2400.), (4000., 3000.)] * 2
    for r in rows:
        turret = next(c for c in r['candidates'] if c['point'] == (3700., 2400.))
        assert turret['ok'] == (r['slot'] in (0, 2))
        assert turret['why'] == ([] if turret['ok'] else ['forbid'])
        assert [c['distance'] for c in r['candidates']] == [
            1544., 1118., 894. if turret['ok'] else None, 1844.
        ]
        eligible = [c for c in r['candidates'] if c['ok']]
        winner = min(eligible, key=lambda c: c['distance'])
        assert (r['target'], r['point']) == (winner['id'], winner['point'])
        assert {c['enemy'] for c in eligible} == {3183}
    raw = Path(simai.labpaths.WORK) / 'testbench/runs/CampClosestA_mcp_1115_094417'
    if raw.exists():
        original = [r for r in teamlog.target_picks(str(raw))
                    if r['frame'] == 16 and r['sort'] == 'ClosestToEnemy']
        for r in original:
            for key in ('brain', 'state', 'heuristic'):
                r[key] = 'redacted'
            r['state_id'] = r['index'] = None    # the fixture writes sid=redacted and drops hi=
        assert rows == original


def test_closest_enemy_named_selection_replays_native_picks():
    """Compare strategic selection only; later movement remains separately xfailed."""
    import ast
    import teamlog
    if not simai.available():
        pytest.skip('no private AI model')
    w = simai_run.run('aiclosest', 'a', 3, lib=simai.model()['xmldata'].Library())
    brain = w.brains['Soviet_1']
    native = teamlog.target_picks(str(PICKS))
    # Native state names are unavailable. Group by observed forbidden-turret verdict;
    # both unrestricted and both non-defense hosts have the same measured pick.
    by_forbid = {}
    for row in native:
        turret = next(c for c in row['candidates'] if c['point'] == (3700., 2400.))
        by_forbid.setdefault(not turret['ok'], set()).add(row['point'])
    things = {t.id: t for t in brain.view.things}
    for lane in range(4):
        picks = [text for _, kind, text in brain.ai.log
                 if kind == 'target' and text.startswith(f'CNVClosest{lane}: ')]
        assert picks, lane
        for text in picks:
            ids = ast.literal_eval(text.split(' -> ')[1])
            assert len(ids) == 1
            target = things[ids[0]]
            assert {(target.x, target.y)} == by_forbid[lane >= 2]
