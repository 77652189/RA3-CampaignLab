"""Engine probe: which units a team template recruits (missions/aiteamfilter_bench.py) -- ObjectFilter Rule ANY / NONE
/ ALL with IncludeThing / ExcludeThing, IncludeKindOf / ExcludeKindOf, MaxUnits: who leaves the AI's base?

  a  坦克在家   Guardians of s1 inside the base area (450 around the east base), once a second
     步兵在家   Peacekeepers of s1 there

Expected (the mission's facts, the model's guess): at s40 坦克在家 == expect tanks home, 步兵在家 == expect infantry
home (an always-on state's team leaves ~5 s after the wake, engine_aistate).

读数
Bench 2026-11-09 (B round 78, one run each, PASS 1 of 1 each; 4 Guardians + 4 Peacekeepers unless said):
  aitfany  a (ObjectFilter Rule ANY, IncludeThing Guardian): 坦克在家 4 -> 3 @ s14, 0 @ s15; 步兵在家 4 to s55.
  aitfnone a (Rule NONE, IncludeThing Guardian): 坦克在家 4 -> 2 @ s14, 0 @ s15; 步兵在家 4 to s55 -- NONE + the
           list takes only the list, as ANY (the model had NONE as no filter: all 8 out; fixed, private ai/teams.py).
  aitfall  a (Rule ALL, ExcludeThing Guardian): 步兵在家 4 -> 0 @ s15; 坦克在家 4 to s55.
  aitfki   a (IncludeKindOf INFANTRY, no ObjectFilter): 步兵在家 0 @ s15; 坦克在家 4 to s55.
  aitfke   a (IncludeKindOf CAN_ATTACK, ExcludeKindOf INFANTRY): 坦克在家 3 @ s14, 0 @ s15; 步兵在家 4 to s55.
  aitfmax  a (MaxUnits 3, 8 Guardians): 坦克在家 8 -> 6 @ s13, 5 from s14 to s55 -- one team of 3.
The simulator (simai) gives the same six (tests/test_simai.py test_team_filters_take_whom_the_bench_sent).
"""
from parts import Test, counted, square, Script

AREA = 'CNV AI Base Area'
LAG = 4.0
AT, SECONDS = 40.0, 50.0


def a(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[AREA] = square(*m.site('east base'), 450.0)
    tank, inf = m.cnv_units
    counted('CNV_TF_Tanks', '坦克在家', t, template=tank, area=AREA, player=s1)
    counted('CNV_TF_Inf', '步兵在家', t, template=inf, area=AREA, player=s1)
    t.expect += [('坦克在家', AT, '==', m.facts['expect tanks home'], AT + 1),
                 ('步兵在家', AT, '==', m.facts['expect infantry home'], AT + 1)]
    t.bench = [('bench_watch', dict(seconds=SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a} for k in ('aitfany', 'aitfnone', 'aitfall', 'aitfki', 'aitfke', 'aitfmax')}
