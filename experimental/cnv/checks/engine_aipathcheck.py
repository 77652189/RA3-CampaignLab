"""Engine line D round 152: PathfindingCheckType (missions/aipathcheck_bench.py). Three counters, once a second, to
90 s after the wake; the team's members are in the CNVTeams log (the kick = members leaving with no death).

  步兵总数 / 步兵在家 / 到对岸   s1's Peacekeepers alive; within 450 of the AI base; within 600 of the player's yard
  expected (no land way across): 到对岸 0 all along, 步兵总数 never below 2 (nothing reaches them across the river)
"""
from checks import engine_aitarget as at
from parts import Script, Test, counted, square

HOME = 'CNV AI Base Area'
ACROSS = 'CNV AI Across Area'
SPAN = 90.0


def check(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[HOME] = square(*m.site('east base'), 450.0)
    o = m.find(m.role('player yard').name)
    t.areas[ACROSS] = square(o.x, o.y, 600.0)
    s1, (inf,) = m.player('s1'), m.cnv_units
    counted('CNV_PF_Live', '步兵总数', t, template=inf, player=s1)
    counted('CNV_PF_Home', '步兵在家', t, template=inf, area=HOME, player=s1)
    counted('CNV_PF_Across', '到对岸', t, template=inf, area=ACROSS, player=s1)
    end = m.facts['wake at'] + SPAN
    t.expect += [('到对岸', 1, '==', 0, end), ('步兵总数', 1, '>=', 2, end)]
    t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': check} for k in ('aipfdef', 'aipfatk', 'aipfpath', 'aipfnone')}
