"""Engine unit test: whose units the trigger-area counts count (E1; bench 2026-10-25 and 2026-11-04, probe/count).

Measured: counting by KindOf in an area counts every player's units, whichever player the condition names; counting
by template, and SKIRMISH_PLAYER_HAS_UNITS_IN_AREA, count only that player's. So "the player has fewer than N
fighting units there" written as a kind count also counts the enemy, the neutrals and the allies standing there.
Three of the player's guardians stand in the west field, two enemy warriors at the north base, each in an area:
  field (west field):the player's kind count 3; the enemy's kind count 3 too (the player's three); the enemy's template
    count 0; the enemy "has units" 0;
  camp (north base): the player's kind count 2 (the enemy's two warriors); the player's template count of warriors 0.
probe/count asks the same in the west field and expects the per-player reading (it FAILs: the record of the guess).
"""
from maps import festival
from parts import Mission, Script, Test, counted, kindof, square

WARRIOR = 'JapanAntiInfantryInfantry'
GUARDIAN = 'AlliedAntiVehicleVehicleTech1'


def mission():
    m = Mission(name='CampArea', map=festival, facts={})
    for k in (0, 1, 2):
        m.put(GUARDIAN, 'west field', 250, 30 + 60 * k, name=f'UNIT - CNV Area Guardian {k}', role=f'guardian {k}')
    for k in (1, 2):
        m.put(WARRIOR, 'north base', 60 * k, 0, side='s1', name=f'UNIT - CNV Area Warrior {k}', role=f'warrior {k}')
    return m


def _test(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.bench = [('bench_watch', dict(seconds=12, every=3, sheet=False, lines=4))]
    return t


def field(m):
    t = _test(m)
    t.areas['Test field'] = square(*m.site('west field'), 450)
    s1 = m.player('s1')
    counted('CNV_Area_KindP1', '区内我方能打的', t, kind=kindof('CAN_ATTACK'), area='Test field')
    counted('CNV_Area_KindS1', '区内敌方能打的', t, kind=kindof('CAN_ATTACK'), area='Test field', player=s1)
    counted('CNV_Area_TypeS1', '区内敌方守护者', t, template=GUARDIAN, area='Test field', player=s1)
    t.counters.append(('CNV_Area_HasS1', '区内敌方有人'))
    t.scripts += [Script('Test - has zero', [], [('SET_COUNTER', 'CNV_Area_HasS1', 0)], once=False),
                  Script('Test - has', [('SKIRMISH_PLAYER_HAS_UNITS_IN_AREA', s1, 'Test field')],
                         [('SET_COUNTER', 'CNV_Area_HasS1', 1)], once=False)]
    t.expect += [('区内我方能打的', 3, '==', 3), ('区内敌方能打的', 3, '==', 3), ('区内敌方守护者', 3, '==', 0),
                 ('区内敌方有人', 3, '==', 0)]
    return t


def camp(m):
    t = _test(m)
    t.areas['Test camp'] = square(*m.site('north base', 90, 0), 150)
    counted('CNV_Area_CampKindP1', '敌营我方能打的', t, kind=kindof('CAN_ATTACK'), area='Test camp')
    counted('CNV_Area_CampTypeP1', '敌营我方武士', t, template=WARRIOR, area='Test camp')
    t.expect += [('敌营我方能打的', 3, '==', 2), ('敌营我方武士', 3, '==', 0)]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_area': mission}
CHECKS = {'engine_area': {'field': field, 'camp': camp}}
