"""Engine probe (missions/probe_bench.py), read off the counters:

engine: the difficulty counter shows 1, 2 or 3 (exactly one of the three copies ran: the bench starts on whatever
  difficulty the profile has); the money counter shows the money set; the mission runs past the autosave.

The border is checked by hand, no counter sees it (bench 2026-10-25): bench_camera east of the canal does not move
before `open at` (west of it does), and does after. A unit a script moves crosses the border at any time -- the
first version of this check sent one east and counted it, and it got there before the border opened.
"""
from parts import Script, Test

RUN = 15.0                                      # past the autosave (5 s), margin


def engine(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.counters += [('CNV_Probe_Difficulty', '难度'), ('CNV_Probe_Money', '资金')]
    t.expect += [('难度', 3, '>=', 1), ('难度', 3, '<=', 3), ('资金', 3, '==', m.facts['money']),
                 ('资金', RUN - 3, 'ever==', m.facts['money'])]
    t.bench = [('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=len(t.counters)))]
    return t
