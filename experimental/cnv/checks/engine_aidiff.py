"""Engine probe: StrategicState Difficulty (missions/aidiff_bench.py) -- two always-on states, one listed for MEDIUM,
one for EASY HARD BRUTAL, each sending one unit type: which type leaves, and at which campaign difficulty?

  a  难度       the campaign difficulty the bench walked into: 1 easy, 2 normal, 3 hard (scripts with one
                difficulty bit each, the script header's bits)
     坦克在家   Guardians of s1 inside the base area (450 around the east base), once a second
     步兵在家   Peacekeepers of s1 there

Expected (the mission's facts, the model's guess): 难度 2 and at s40 坦克在家 / 步兵在家 == expect tanks / infantry
home (only the state listed for MEDIUM runs).

读数
Bench 2026-11-09 (B round 79, one run each, PASS 3 of 3 each):
  aidiff  a: 难度 2 throughout (the bench walks the campaign at normal); 坦克在家 4 -> 1 @ s15, 0 from s16 to s55;
          步兵在家 4 to s55 -- only the state listed MEDIUM sent its team.
  aidiffx a (the lists swapped): 难度 2; 步兵在家 4 -> 1 @ s16, 0 from s17; 坦克在家 4 to s55.
So campaign normal = AI difficulty MEDIUM (simai's DIFFICULTY map), and a state not listed for it never runs.
The simulator gives the same two (tests/test_simai.py test_only_the_states_listed_for_the_difficulty_run).
"""
from parts import Test, counted, square, Script

AREA = 'CNV AI Base Area'
LAG = 4.0
AT, SECONDS = 40.0, 50.0
DIFF = 'CNV_Diff'


def a(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.counters.append((DIFF, '难度'))
    t.scripts += [Script(f'Test - difficulty {k + 1}', [], [('SET_COUNTER', DIFF, k + 1)], once=False,
                         levels=tuple(j == k for j in range(3))) for k in range(3)]
    t.areas[AREA] = square(*m.site('east base'), 450.0)
    tank, inf = m.cnv_units
    counted('CNV_D_Tanks', '坦克在家', t, template=tank, area=AREA, player=s1)
    counted('CNV_D_Inf', '步兵在家', t, template=inf, area=AREA, player=s1)
    t.expect += [('难度', 5.0, '==', 2, 6.0),
                 ('坦克在家', AT, '==', m.facts['expect tanks home'], AT + 1),
                 ('步兵在家', AT, '==', m.facts['expect infantry home'], AT + 1)]
    t.bench = [('bench_watch', dict(seconds=SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a} for k in ('aidiff', 'aidiffx')}
