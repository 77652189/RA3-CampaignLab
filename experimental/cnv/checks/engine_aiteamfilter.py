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
Bench 2026-11-09 (B round 81, run_queue --jobs 2, all PASS; the second type: Riptide ACVs in the locomotor builds):
  aitfland  AllowedLocomotorTypes LAND: 坦克在家 2 @ s15, 0 from s16; 气垫船在家 4 to s55.
  aitfamph  AMPHIBIOUS: 气垫船在家 2 @ s13, 0 from s14; 坦克在家 4 to s55.
  aitfwat   WATER: both 4 to s55 -- an amphibious unit is not WATER.
  aitfosi   RegisteredObjectSet INFANTRY: 步兵在家 0 from s15; 坦克在家 4 to s55.
  aitfosv   VEHICLES: 坦克在家 2 @ s14, 0 from s15; 步兵在家 4 to s55.
  aitfosc   SKIRMISH_AI_NORMAL_COMBAT_UNITS: both go, later than the rest: 坦克在家 2 @ s20, 0 @ s21; 步兵在家 1 @
            s22, 0 from s23 (not modelled: the ~6 s).
The model had the object set as no filter (private ai/teams.py OBJECT_SET_KIND now); simai gives these six
(tests/test_simai.py test_locomotor_types_and_object_sets_take_whom_the_bench_sent).
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
    tank, other = m.cnv_units
    lt, lo = getattr(m, 'cnv_labels', ('坦克在家', '步兵在家'))
    counted('CNV_TF_Tanks', lt, t, template=tank, area=AREA, player=s1)
    counted('CNV_TF_Inf', lo, t, template=other, area=AREA, player=s1)
    t.expect += [(lt, AT, '==', m.facts['expect tanks home'], AT + 1),
                 (lo, AT, '==', m.facts['expect infantry home'], AT + 1)]
    t.bench = [('bench_watch', dict(seconds=SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a} for k in ('aitfany', 'aitfnone', 'aitfall', 'aitfki', 'aitfke', 'aitfmax',
                                 'aitfland', 'aitfamph', 'aitfwat', 'aitfosi', 'aitfosv', 'aitfosc')}
