"""Engine probe: an opening's Time order (missions/aiotime_bench.py) -- power plant / Time 30s / power plant / Time 20s
/ power plant: when do the three stand?

  a  电厂   power plants s1 owns, once a second

Expected (the model: Time counts from the wake, mission s10): 1 at s45, 2 at s55, 3 at s65 (since the previous Time:
2 at s65; since the mission start: 2 at s45).

读数
Bench 2026-11-09 (B round 79, one run, PASS 3 of 3): 电厂 0 to s18, 1 s19-s48, 2 s49-s58, 3 from s59 -- Time counts
from the wake (the opening's start); a Time point already passed holds nothing up. The simulator has the gaps
(30 s, 10 s) but every plant 3 s late (tests/test_simai.py, the absolute times a strict xfail).
"""
from parts import Test, counted, Script

LAG = 4.0
SECONDS = 75.0


def a(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('CNV_OT_Plants', '电厂', t, template='AlliedPowerPlant', player=m.player('s1'))
    t.expect += [('电厂', 45.0, '==', 1, 46.0), ('电厂', 55.0, '==', 2, 56.0), ('电厂', 65.0, '==', 3, 66.0)]
    t.bench = [('bench_watch', dict(seconds=SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {'aiotime': {'a': a}}
