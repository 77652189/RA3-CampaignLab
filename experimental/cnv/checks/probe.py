"""Engine probe (missions/probe_bench.py), read off the counters:

engine: the difficulty counter shows 1, 2 or 3 (exactly one of the three copies ran: the bench starts on whatever
  difficulty the profile has); the money counter shows the money set; the runner sent east at once is not past the
  canal before the border opens, and is once it has.
"""
from parts import Script, Test, counted, square

RUN = 45.0                                      # west field to the road exit: ~1700 at a Guardian's speed, margin


def engine(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.counters += [('CNV_Probe_Difficulty', '难度'), ('CNV_Probe_Money', '资金')]
    x, y = m.point('beyond')
    t.areas['Test Beyond'] = square(x - 300, y, 300)
    counted('Test Beyond', '过了运河', t, named=m.role('guardian').name, area='Test Beyond')
    opened = m.facts['open at']
    t.expect += [('难度', 3, '>=', 1), ('难度', 3, '<=', 3), ('资金', 3, '==', m.facts['money']),
                 ('过了运河', 0, '==', 0, opened), ('过了运河', opened + 3, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=opened + RUN, every=3, sheet=False, lines=len(t.counters)))]
    return t
