"""Engine probe (missions/probe_bench.py), read off the counters:

engine: the difficulty counter shows 1, 2 or 3 (exactly one of the three copies ran: the bench starts on whatever
  difficulty the profile has); the money counter shows the money set; the mission runs past the autosave.

The border is checked by hand, no counter sees it (bench 2026-10-25): bench_camera east of the canal does not move
before `open at` (west of it does), and does after. A unit a script moves crosses the border at any time -- the
first version of this check sent one east and counted it, and it got there before the border opened.
"""
from parts import Obj, Script, Test, counted, kindof, square

RUN = 15.0                                      # past the autosave (5 s), margin


def engine(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.counters += [('CNV_Probe_Difficulty', '难度'), ('CNV_Probe_Money', '资金')]
    t.expect += [('难度', 3, '>=', 1), ('难度', 3, '<=', 3), ('资金', 3, '==', m.facts['money']),
                 ('资金', RUN - 3, 'ever==', m.facts['money'])]
    t.bench = [('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=len(t.counters)))]
    return t


def count(m):
    """Whose units the area conditions count (bench 2026-10-25: a kind-in-area count for the enemy came out as every
    player's): the player's guardian and two more of ours at the west field, two enemy warriors far off at the north
    base; the enemy's count in the west field, three ways, against the player's own."""
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    for k in (1, 2):
        t.objects.append(Obj('AlliedAntiVehicleVehicleTech1', *m.site('west field', 250, 30 + 60 * k), site='west field'))
        t.objects.append(Obj('JapanAntiInfantryInfantry', *m.site('north base', 60 * k, 0), side='s1',
                             site='north base'))
    t.areas['Test field'] = square(*m.site('west field'), 450)
    s1 = m.player('s1')
    counted('CNV_Probe_KindP1', '我方能打的', t, kind=kindof('CAN_ATTACK'), area='Test field')
    counted('CNV_Probe_KindS1', '敌方能打的', t, kind=kindof('CAN_ATTACK'), area='Test field', player=s1)
    counted('CNV_Probe_TypeS1', '敌方守护者', t, template='AlliedAntiVehicleVehicleTech1', area='Test field', player=s1)
    t.counters.append(('CNV_Probe_EnterS1', '敌方进入'))
    t.scripts += [Script('Test - enter zero', [], [('SET_COUNTER', 'CNV_Probe_EnterS1', 0)], once=False),
                  Script('Test - enter', [('SKIRMISH_PLAYER_HAS_UNITS_IN_AREA', s1, 'Test field')],
                         [('SET_COUNTER', 'CNV_Probe_EnterS1', 1)], once=False)]
    t.expect += [('我方能打的', 3, '==', 3), ('敌方能打的', 3, '==', 0), ('敌方守护者', 3, '==', 0), ('敌方进入', 3, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=12, every=3, sheet=False, lines=len(t.counters)))]
    return t
