"""Engine probe: an AI attack team sent to a target named in the data (missions/ainamed_bench.py).

  a  步兵在家 / 到近厂 / 到远厂 / 到路点   Peacekeepers of s1 within 450 of the AI's base, within 300 of the near
                                          power plant, of the far one, of the waypoint -- once a second for 60 s
                                          after the wake

The first of 到近厂 / 到远厂 / 到路点 to go above 0 is the reading (afterwards RAMPAGE may take the team on).
Expectation per build (the model, RA3-EngineModel ra3model/ai/targets.py): ainmfar -> far; ainmwp -> the waypoint;
ainmrel / ainmnone -> nobody leaves. A FAIL is a reading too.

读数
Bench 2026-11-08 (one run each; all PASS):
  ainmfar   到远厂 2 @ s15, 4 s17-s33, 0 from s35 (the plant down); 到近厂 0 till s42, 3 @ s43, 4 s44-s51 (RAMPAGE);
            步兵在家 4 -> 2 @ s10, 0 from s12. NamedObject goes to the named plant, not the nearest.
  ainmwp    到路点 2 @ s6, 3 @ s7, 4 from s8 to s75; 到近厂 / 到远厂 0 all along: at the point the team stays.
  ainmrel   步兵在家 4 all 75 s: Relationship NEUTRAL drops the player's (enemy) plant -- no target, no team.
  ainmnone  步兵在家 4 all 75 s: a name nobody has, no target.
"""
from parts import Script, Test, counted, square
from checks import engine_aitarget as at

AFTER = 60.0
WPA = 'CNV AI WP Target Area'


def a(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[at.HOME] = square(*m.site('east base'), 450.0)
    for area, role in ((at.NEAR, 'near plant'), (at.FAR, 'far plant')):
        o = m.find(m.role(role).name)
        t.areas[area] = square(o.x, o.y, 300.0)
    t.areas[WPA] = square(*m.point('wp target'), 300.0)
    (inf,) = m.cnv_units
    counted('CNV_AT_Home', '步兵在家', t, template=inf, area=at.HOME, player=s1)
    counted('CNV_AT_Near', '到近厂', t, template=inf, area=at.NEAR, player=s1)
    counted('CNV_AT_Far', '到远厂', t, template=inf, area=at.FAR, player=s1)
    counted('CNV_AT_WP', '到路点', t, template=inf, area=WPA, player=s1)
    end = m.facts['wake at'] + AFTER
    pick, (kind, name, extra) = None, m.cnv_heuristic
    if kind == 'Waypoint':
        pick = '到路点'
    elif 'Far Plant' in name and not extra:
        pick = '到远厂'
    if pick:
        t.expect += [('步兵在家', end, '<', 4, end + 1), (pick, 1, 'ever>=', 1, end)]
    else:
        t.expect += [('步兵在家', 1, '==', 4, end)]
    t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a} for k in ('ainmfar', 'ainmwp', 'ainmrel', 'ainmnone')}
