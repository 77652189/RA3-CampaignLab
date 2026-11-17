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
Bench 2026-11-09 (B round 88): aiar0 / aiar1 / aiar2 (AlwaysRecruit false / true / true MaxUnits 4; 4 Guardians,
the AI to build 2 more by an opener in an Allied war factory): all three 坦克在家 4 to s13, 3 @ s14, 0 from s15 to
s75 -- no third tank ever seen at home: the opener most likely built nothing (no owned counter, not told apart).
Not read for AlwaysRecruit. Next: count s1's owned Guardians (SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER, as aimicro).
Bench 2026-11-09 (B round 89, 坦克拥有 = owned anywhere): aiar0 / aiar1 / aiar2 owned 4 from s1 to the end -- the
opener built no Guardian at all (not the home box). aimicro's same opener (2 infantry, a script-placed barracks)
built both. Told apart next by aiar3 (no Guardians placed: can the script-placed war factory build them) and aiar4
(4 Guardians, the opener builds 2 Riptides: is it owning that template already) -- written, not benched.
Bench 2026-11-09 (B round 92, PASS 1 of 1 each; aiar8's StaticDefense AlwaysRecruit team): aiar9 (new AI plant 1000
south at s45) 坦克在新楼 0 to s107; aiar10 (placed tank 1 teleported 1200 south at s60 and s130) 坦克在外 1 for ~5 s /
~10 s, home again ~10 s after each -- held both times, the guard keeps its first target.
"""
from parts import Test, counted, square, Script

AREA = 'CNV AI Base Area'
OUT_AREA = 'CNV AI Out Area'
PLANT_AREA = 'CNV AI Far Plant Area'
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
    x, y = m.site('east base')
    if 'plant at' in m.facts or 'named teleport 1' in m.facts:   # aiar9 / 10: 3 counters (a 4th reads ?)
        if 'plant at' in m.facts:
            t.areas[PLANT_AREA] = square(*m.point('far plant'), 350.0)
            counted('CNV_TF_Plant', '坦克在新楼', t, template=tank, area=PLANT_AREA, player=s1)
            label, want = '坦克在新楼', m.facts['expect tanks at plant']
        else:
            t.areas[OUT_AREA] = square(x, y - 1200.0, 300.0)
            counted('CNV_TF_Out', '坦克在外', t, template=tank, area=OUT_AREA, player=s1)
            label, want = '坦克在外', m.facts['expect named out']
        counted('CNV_TF_Owned', '坦克拥有', t, template=tank, player=s1)
        at = m.facts['check at']
        t.expect += [(label, at, '==', want, at + 1)]
        t.bench = [('bench_watch', dict(seconds=at + 4 + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t
    if 'teleport at' in m.facts:          # aiar5-8: the late tanks no team holds, teleported (a 4th counter reads ?)
        t.areas[OUT_AREA] = square(x, y - 1200.0, 300.0)
        counted('CNV_TF_Out', '坦克在外', t, template=tank, area=OUT_AREA, player=s1)
        counted('CNV_TF_Owned', '坦克拥有', t, template=tank, player=s1)
        at = m.facts['check at']
        t.expect += [('坦克在外', at, '==', m.facts['expect tanks out'], at + 1)]
        t.bench = [('bench_watch', dict(seconds=at + 4 + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t
    counted('CNV_TF_Inf', lo, t, template=other, area=AREA, player=s1)
    if 'late tanks' in m.facts:           # aiar*: did the opener build them at all (owned, anywhere)
        counted('CNV_TF_Owned', '坦克拥有', t, template=tank, player=s1)
        counted('CNV_TF_Owned2', '另一种拥有', t, template=other, player=s1)
    at = m.facts.get('check at', AT)      # aiar*: later, after the AI has built its own tanks
    t.expect += [(lt, at, '==', m.facts['expect tanks home'], at + 1),
                 (lo, at, '==', m.facts['expect infantry home'], at + 1)]
    t.bench = [('bench_watch', dict(seconds=max(SECONDS, at + 10) + LAG, every=1, sheet=False,
                                    lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a} for k in ('aitfany', 'aitfnone', 'aitfall', 'aitfki', 'aitfke', 'aitfmax',
                                 'aitfland', 'aitfamph', 'aitfwat', 'aitfosi', 'aitfosv', 'aitfosc', 'aiar0', 'aiar1', 'aiar2',
                                 'aiar3', 'aiar4', 'aiar5', 'aiar6', 'aiar7', 'aiar8', 'aiar9', 'aiar10')}
