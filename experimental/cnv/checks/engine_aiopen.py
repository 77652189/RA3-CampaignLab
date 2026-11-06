"""Engine probe: the skirmish AI's opening (missions/aiopen_bench.py) -- when each structure / unit first appears
for the enemy (s1, AlliedBalanced, woken at 10 s with 50000 money), counted once a second for 150 s after waking.

  a  兵营 / 电厂 / 精炼厂 / 战车工厂   AlliedBarracks, AlliedPowerPlant, AlliedRefinery, AlliedWarFactory
  b  反步兵车 / 激流 / 资金 / 采矿车   AlliedAntiInfantryVehicle, AlliedAntiInfantryVehicle_Ground, money, AlliedMiner
  c  船坞                           AlliedNavalYard

Four lines a check (the counter display). Counts are the player's own, capped at 8. The expectation is loose; the
point is the reading.

读数
Bench 2026-11-06 (one run each; bench seconds, the money first moves at s9 = the wake, so after-wake = s - 9):
  a CampAIOpenA: 兵营 0->1 @ s19 (wake+10); 电厂 0->1 @ s29 (+20), ->2 @ s79, ->3 @ s137, ->4 @ s147;
    精炼厂 0->1 @ s49 (+40), ->2 @ s69 (+60); 战车工厂 0->1 @ s99 (+90), stays 1.
  b CampAIOpenB: 资金 50000 at the wake, 49966 s9, 49371 s20, 45006 s52, ~42300 s77-80, ~40700 s111, 33397 s167
    (spending is slow and steady, no big single drops; income from the miners flattens it now and then);
    采矿车 0->1 @ s53 (+44), ->2 @ s73 (+64); 反步兵车 and 激流 (_Ground, same unit counted by both templates)
    0->1 @ s111 (+102), ->2 @ s123, ->3 @ s131, ->4 @ s142, ->5 @ s153.
  c CampAIOpenC: 船坞 stays 0 all 167 s.
"""
from parts import Script, Test, counted

LAG = 4.0
SECONDS = 160.0                      # wake 10 s + 150 s


def _base(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    return t, m.player('s1')


def _finish(t, m):
    w = m.facts['wake at']
    t.expect += [('兵营', 1, 'ever>=', 1, w + 150.0)] if any(c[1] == '兵营' for c in t.counters) else []
    t.bench = [('bench_watch', dict(seconds=w + 150.0 + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


def a(m):
    t, s1 = _base(m)
    for c, lab, tpl in (('CNV_AO_Barracks', '兵营', 'AlliedBarracks'), ('CNV_AO_Power', '电厂', 'AlliedPowerPlant'),
                        ('CNV_AO_Refinery', '精炼厂', 'AlliedRefinery'), ('CNV_AO_Factory', '战车工厂', 'AlliedWarFactory')):
        counted(c, lab, t, template=tpl, player=s1)
    return _finish(t, m)


def b(m):
    t, s1 = _base(m)
    counted('CNV_AO_AIV', '反步兵车', t, template='AlliedAntiInfantryVehicle', player=s1)
    counted('CNV_AO_AIVG', '激流', t, template='AlliedAntiInfantryVehicle_Ground', player=s1)
    t.counters.append(('CNV_AO_Money', '资金'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AO_Money')], once=False))
    counted('CNV_AO_Miner', '采矿车', t, template='AlliedMiner', player=s1)
    w = m.facts['wake at']
    t.expect += [('资金', w + LAG, 'ever>', 0, w + 30)]
    t.bench = [('bench_watch', dict(seconds=w + 150.0 + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


def c(m):
    t, s1 = _base(m)
    counted('CNV_AO_Naval', '船坞', t, template='AlliedNavalYard', player=s1)
    return _finish(t, m)


CHECKS = {'aiopen': {'a': a, 'b': b, 'c': c}}
