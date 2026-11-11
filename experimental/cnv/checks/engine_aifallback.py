"""RetreatMinDistanceToFallback diagnostic (missions/aifallback_bench.py).

Prediction: both leave home and enter the far-plant area alive. A 500-unit
continuation latch carries the team farther home than 100 once the hostile
list clears. Keep FromBase=300 and every other airetf setting unchanged.
Home/far/midway counts observe the outward and return trips, not the internal
state's exact exit or its distance from the dynamically chosen retreat start.
No exact-distance or independent exit-condition claim can be made from these
four counters alone.

Bench 2026-11-11, both positive-control checks PASS (home/far/alive/midway):
  short100: home0 s21-32; far2 s24-25; midway4 s26-32; home4 s35-52;
            home2 s53 (leaves again), alive4 through s60, 3 from s61.
  long500:  home0 s21-28; far2 s24-25; midway4 s26-28; home4 s31-48;
            home2 s49 (leaves again), alive4 through s56, 3 from s57.
Both stay home about 18 seconds. The model returns all four in either build,
but departs again short before long (rows38/42), opposite to the bench s53/49.
tests/test_simai_fallback.py retains this as strict xfail. Do not register the
field as benched: departure includes the already known home-readiness gap,
and neither retreat exit position nor its cause was observed.
"""
from checks import engine_airetreat as ar
from parts import counted, square


def a(m):
    t = ar.a(m, 'airetf')
    # Keep only the common departure positive control: do not pre-assume home.
    t.expect = [('步兵在家', m.facts['wake at'] + 5, 'ever==', 0, 60)]
    x, y = m.facts['fallback midway']
    area = 'CNV Fallback Midway'
    t.areas[area] = square(x, y, 150)
    (inf,) = m.cnv_units
    counted('CNV_FB_Mid', '中途人数', t, template=inf, area=area, player=m.player('s1'))
    t.expect.append(('到远厂', 1, 'ever>=', 1, m.facts['wake at'] + 35))
    t.bench = [('bench_watch', dict(seconds=65, every=1, sheet=False, lines=4))]
    return t


CHECKS = {k: {'a': a} for k in ('aifbshort', 'aifblong')}
