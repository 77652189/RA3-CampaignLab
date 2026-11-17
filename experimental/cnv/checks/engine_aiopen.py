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
  (b again in round 11: the same seconds. But its Riptides 2 -> 3 in 8 s cannot be: one factory, 10 s a build. The
  watch's seconds drift from the game's; the frame checks below are the authority.)

  f1 / f2 / f3 (frames from the wake, round 11; f2 run twice, the same): 兵营 152, 电厂1 305, 精炼厂1 607,
    精炼厂2 909, 电厂2 1062, 战车工厂 1364, 激流1 1555, 激流2 1716, 激流3 1877; 采矿车1 667 (= refinery + 60: its
    UnpackTime 4 s), 电厂3 1960 (past the opening). 放下 (any UNDER_CONSTRUCTION) never stopped: 2450, i.e. the AI's
    Allied structures were never seen under construction by that condition (op 0 '<' not proven for it; not chased).
    So: a structure is owned 1 frame after its head is full, the yard starts the next the frame after; the war
    factory makes nothing till unpacked (UnpackTime 2 s = 30 frames); a unit leaves the door 10 frames after its head
    is full and the next starts then (161 frames each). The opening's frame-10 lottery adds nothing here.
  m CampAIPoorM (aiopenpoor, 3000 at the wake): 2963 at s9, 兵营 s19, 电厂 s29, money 23 at s37 and 0 s38-s125 --
    the refinery is never finished (精炼厂 0 all run) and nothing after it starts: the opening stalls in order on the
    order it cannot pay, the 2000 Deposit into PRODUCTION buys nothing. s126 money jumps to 1000 and is spent
    (106 at s135), s136 +200 to 250, s138 兵营 1 -> 0 (sold?), money 3 from s139 to the end. Not read why
    (a cancelled refinery's refund and a sale are guesses).
"""
from parts import Script, Test, counted, status

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


#: frame checks: counter, label, template (None = any object of s1 UNDER_CONSTRUCTION), the how-many-th one
FRAMES = {
    'f1': (('CNV_AO_F_Placed', '放下', None, 1), ('CNV_AO_F_Barracks', '兵营', 'AlliedBarracks', 1),
           ('CNV_AO_F_Power1', '电厂1', 'AlliedPowerPlant', 1), ('CNV_AO_F_Ref1', '精炼厂1', 'AlliedRefinery', 1)),
    'f2': (('CNV_AO_F_Ref2', '精炼厂2', 'AlliedRefinery', 2), ('CNV_AO_F_Power2', '电厂2', 'AlliedPowerPlant', 2),
           ('CNV_AO_F_Factory', '战车工厂', 'AlliedWarFactory', 1),
           ('CNV_AO_F_AIV1', '激流1', 'AlliedAntiInfantryVehicle_Ground', 1)),
    'f3': (('CNV_AO_F_AIV2', '激流2', 'AlliedAntiInfantryVehicle_Ground', 2),
           ('CNV_AO_F_AIV3', '激流3', 'AlliedAntiInfantryVehicle_Ground', 3),
           ('CNV_AO_F_Miner1', '采矿车1', 'AlliedMiner', 1), ('CNV_AO_F_Power3', '电厂3', 'AlliedPowerPlant', 3)),
}


def frames(m, which):
    """Exact frames instead of the 1 s samples: every counter counts the frames from the wake (the wake timer has
    expired, and at least 30 frames in so an unset timer cannot count) while s1 owns fewer than n of its template --
    so its last value is the frame the n-th one first counts (one that never comes counts the whole run). Read once
    at the end; the frame of the wake itself is +-1 (the mission's wake script and the flag run in the same frame)."""
    t, s1 = _base(m)
    t.scripts += [Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_AO_Tick')], once=False),
                  Script('Test - woke', [('TIMER_EXPIRED', 'CNV AI Wake'), ('COUNTER', 'CNV_AO_Tick', 3, 30)],
                         [('SET_FLAG', 'Test Woke', 1)])]
    owned = {}
    for counter, label, tpl, n in FRAMES[which]:
        t.counters.append((counter, label))
        if tpl is None:
            have = ('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', s1, 0, n, status('UNDER_CONSTRUCTION'))
        else:
            if tpl not in owned:
                owned[tpl] = f'CNV_AO_Own{len(owned)}'
                t.scripts.append(Script(f'Test - own {tpl}', [],
                                        [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', tpl, s1, owned[tpl])], once=False))
            have = ('COUNTER', owned[tpl], 0, n)
        t.scripts.append(Script(f'Test - wait {counter}', [('FLAG', 'Test Woke', 1), have],
                                [('INCREMENT_COUNTER', 1, counter)], once=False))
    w = m.facts['wake at']
    t.expect += [(FRAMES[which][0][1], w + LAG, 'ever>=', 1, w + 150.0)]
    t.bench = [('bench_watch', dict(seconds=w + 150.0 + LAG, every=10, sheet=False, lines=len(t.counters)))]
    return t


def poor(m):
    """aiopenpoor (3000 at the wake): what the opening builds when the money runs out, once a second."""
    t, s1 = _base(m)
    for c, lab, tpl in (('CNV_AO_Barracks', '兵营', 'AlliedBarracks'), ('CNV_AO_Power', '电厂', 'AlliedPowerPlant'),
                        ('CNV_AO_Refinery', '精炼厂', 'AlliedRefinery')):
        counted(c, lab, t, template=tpl, player=s1)
    t.counters.append(('CNV_AO_Money', '资金'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AO_Money')], once=False))
    w = m.facts['wake at']
    t.expect += [('资金', w + LAG, 'ever>', 0, w + 30)]
    t.bench = [('bench_watch', dict(seconds=w + 150.0 + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {'aiopen': {'a': a, 'b': b, 'c': c, **{k: (lambda m, k=k: frames(m, k)) for k in FRAMES}},
          'aiopenpoor': {'m': poor}}
