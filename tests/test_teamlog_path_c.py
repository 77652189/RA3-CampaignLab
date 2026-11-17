"""D108 observed PathToTarget rows; process tokens redacted, measurements kept.

Evidence: work/re/d108_pathtotarget.md. Early returns must not be confused
with an actual failed route or combined with points sampled on a later frame.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    'teamlog_path_c', Path(__file__).resolve().parents[1] / 'experimental/cnv/teamlog.py')
teamlog = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(teamlog)


def test_path_evaluations_keep_same_call_measurements(tmp_path):
    p = tmp_path / 'ra3ext.log'
    p.write_text(
        'unrelated observer line\n'
        'ptt: frame=4 exists=1 surf=1 cond=6 key=probe loco=0:- set14=0 '
        'obase=-1@0:0 ebase=-1@0:0 opt=0.0:0.0:0.0 ept=0.0:0.0:0.0 '
        'path=-1 code=-1 res=1.0 why=early:nobase\n'
        'ptt: frame=4 exists=0 surf=1 cond=6 key=probe loco=0:- set14=0 '
        'obase=-1@0:0 ebase=-1@0:0 opt=0.0:0.0:0.0 ept=0.0:0.0:0.0 '
        'path=-1 code=-1 res=0.0 why=early:nobase\n'
        'ptt: frame=158 exists=1 surf=1 cond=0 key=stock loco=1:redacted set14=1 '
        'obase=3130@3850:3400 ebase=3131@1250:2500 opt=3944.4:3433.0:212.5 '
        'ept=1331.9:2557.4:212.5 path=0 code=1 res=0.0 why=path\n', encoding='utf-8')
    early, inverse, route = teamlog.path_evaluations(str(tmp_path))
    assert (early['frame'], early['cond'], early['locomotors'], early['path'],
            early['code'], early['result'], early['why']) == (4, 6, 0, -1, -1, 1.0, 'early:nobase')
    assert early['own_base'] == (-1, (0., 0.))
    assert early['own_point'] == (0., 0., 0.)
    assert (inverse['frame'], inverse['exists'], inverse['result']) == (4, 0, 0.)
    assert (route['frame'], route['cond'], route['locomotors'], route['set14'],
            route['path'], route['code'], route['result']) == (158, 0, 1, 1, 0, 1, 0.)
    assert route['own_base'] == (3130, (3850., 3400.))
    assert route['enemy_base'] == (3131, (1250., 2500.))
    assert route['own_point'] == (3944.4, 3433., 212.5)
    assert route['enemy_point'] == (1331.9, 2557.4, 212.5)
    assert 'brain' not in route and 'tmpl' not in route
    assert teamlog.path_evaluations(str(p)) == [early, inverse, route]
