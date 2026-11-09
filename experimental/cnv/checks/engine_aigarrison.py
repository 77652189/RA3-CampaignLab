"""Engine probe: the skirmish AI team's EnterGarrisons (missions/aigarrison_bench.py; docs/engine/aiteamstate.md; the
simulator against these readings: tests/test_simai.py).

  a  步兵在家 / 到远厂     Peacekeepers of s1 within 450 of the AI's base / 300 of the far power plant
     步兵数               Peacekeepers s1 owns (in the house too)
     楼归AI               the house is s1's (a garrisoned civilian building is its first occupant's: garrison.md 2)
     once a second, AFTER seconds after the wake

Expectations are the model's (l4_micro_engage.md 1.7); a FAIL is a reading too:
  aigar1    the house turns the AI's (someone of the team went in)
  aigar0    the house never the AI's
  aigarfar  the house never the AI's
"""
from checks import engine_aitarget as at
from parts import Script, Test, counted, square

AFTER = 60.0


def a(m, build):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[at.HOME] = square(*m.site('east base'), 450.0)
    o = m.find(m.role('far plant').name)
    t.areas[at.FAR] = square(o.x, o.y, 300.0)
    (inf,) = m.cnv_units
    counted('CNV_AG_Home', '步兵在家', t, template=inf, area=at.HOME, player=s1)
    counted('CNV_AG_Far', '到远厂', t, template=inf, area=at.FAR, player=s1)
    counted('CNV_AG_Count', '步兵数', t, template=inf, player=s1)
    house = m.role('house')
    counted('CNV_AG_House', '楼归AI', t, template=house.template, player=s1)
    wake = m.facts['wake at']
    end = wake + AFTER
    t.expect += [('步兵在家', wake + 5, 'ever==', 0, end)]              # it left
    if build == 'aigar1':
        t.expect += [('楼归AI', 1, 'ever>=', 1, end)]
    else:
        t.expect += [('楼归AI', 1, '==', 0, end)]
    t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in ('aigar1', 'aigar0', 'aigarfar')}
