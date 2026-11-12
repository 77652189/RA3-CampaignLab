"""E84: PathToTargetHeuristic.LocomotorConditionToUseForTest, same JapanAntiAirShip.

SDK JapanAntiAirShip NORMAL names a DEEP_WATER locomotor; SUPERSONIC names AIR.
Niagara's two construction yards are on land. Prediction before running:
aiopwater chooses Island (power plant first, no barracks); aiopair chooses
Standard (barracks first). Only the condition differs in the heuristic input.
Count the opening's actual buildings, not an internal path score.
Bench 2026-11-12: aiopwater FAIL, aiopair PASS; both have barracks=1,
power=0 at s22-s24. The failed water prediction below is retained. These
equal readings do not establish that the condition selects a locomotor.
tests/test_simai_bench_e.py replays the observed counts, not that prediction.
Evidence and any mismatch: work/re/e_pathcond_e84.md.
"""
from parts import Script, Test, counted


def opening(m, island):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    for counter, label, template in (
            ('CNV_PC_Barracks', '兵营', 'AlliedBarracks'),
            ('CNV_PC_Power', '电厂', 'AlliedPowerPlant')):
        counted(counter, label, t, template=template, player=m.player('s1'))
    wake = m.facts['wake at']
    t.expect += [('兵营', wake + 12, '==', 0 if island else 1, wake + 15),
                 ('电厂', wake + 12, '==', 1 if island else 0, wake + 15)]
    t.bench = [('bench_watch', dict(seconds=wake + 20, every=1, sheet=False, lines=2))]
    return t


CHECKS = {'aiopwater': {'a': lambda m: opening(m, True)},
          'aiopair': {'a': lambda m: opening(m, False)}}
