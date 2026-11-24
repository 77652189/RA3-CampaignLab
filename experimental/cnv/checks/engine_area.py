"""Engine unit test: whose units the trigger-area counts count (E1; bench 2026-10-25 and 2026-11-04, probe/count).

Measured: counting by KindOf in an area counts every player's units, whichever player the condition names; counting
by template, and SKIRMISH_PLAYER_HAS_UNITS_IN_AREA, count only that player's. So "the player has fewer than N
fighting units there" written as a kind count also counts the enemy, the neutrals and the allies standing there.
Three of the player's guardians stand in the west field, two enemy warriors at the north base, each in an area:
  field (west field):the player's kind count 3; the enemy's kind count 3 too (the player's three); the enemy's template
    count 0; the enemy "has units" 0;
  camp (north base): the player's kind count 2 (the enemy's two warriors); the player's template count of warriors 0.
probe/count asks the same in the west field and expects the per-player reading (it FAILs: the record of the guess).
als (A347, l2_scripts1 1: a player argument is a mask): PLAYER_SET_MONEY 1000 for p1 and s1 at the start, 7000 for
  "<1st Human Player's Enemies>" at 3 s (retail 9 times); 钱 = PLAYER_HAS_CREDITS >= 5000 s1 1 / p1 2 / the alias 4,
  p1 >= 1000 8; 有 = SKIRMISH_PLAYER_HAS_UNITS_IN_AREA (retail 10 times with an alias) the enemies at the camp 1 /
  in the field 2, the allies incl self in the field 4, the allies (not self) 8. Predicted: 8 then 13; 有 5.
cash (A349): every player's start money, no script setting any (measured: 10000 each = each faction's PlayerTemplate StartingMoney, Money.start).
"""
from maps import festival
from parts import Mission, Script, Test, counted, kindof, square
import checks.engine_scripts8 as s8

FOES, OURS, FRIENDS = (f"<1st Human Player's {k}>" for k in ('Enemies', 'Allies incl Self', 'Allies'))

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


def alias(m):
    t = _test(m)
    t.areas['Test field'], t.areas['Test camp'] = square(*m.site('west field'), 450), square(*m.site('north base', 90, 0), 150)
    p1, s1 = m.player('p1'), m.player('s1')
    t.scripts.append(Script('Test - money', [], [('PLAYER_SET_MONEY', p1, 1000), ('PLAYER_SET_MONEY', s1, 1000)]))
    s8.at(t, 'foes', 3.0, [('PLAYER_SET_MONEY', FOES, 7000)])
    s8.total(t, 'CNV_Area_Cash', '钱', [(w, ('PLAYER_HAS_CREDITS', who, 3, n)) for w, who, n in (
        (1, s1, 5000), (2, p1, 5000), (4, FOES, 5000), (8, p1, 1000))])
    s8.total(t, 'CNV_Area_Has', '有', [(w, ('SKIRMISH_PLAYER_HAS_UNITS_IN_AREA', who, area)) for w, who, area in (
        (1, FOES, 'Test camp'), (2, FOES, 'Test field'), (4, OURS, 'Test field'), (8, FRIENDS, 'Test field'))])
    s8.watch(t, 10, every=0.5)
    return t


LADDER = (1, 1000, 1500, 1501, 2000, 5000, 5001, 10000, 10001, 20000, 20001, 50000, 50001, 100000)


def cash(m):
    """cash (A349): no script money; a player's count = the steps of LADDER its PLAYER_HAS_CREDITS >= holds; two players
    a counter (only four lines fit): 钱 = the first's + 15 x the second's (p1 s1 | s2 s3 | s4 s5 | s6)."""
    t = _test(m)
    for i, pair in enumerate((('p1', 's1'), ('s2', 's3'), ('s4', 's5'), ('s6',))):
        s8.total(t, f'CNV_Area_Cash{i}', f'钱{i}', [(15 ** j, ('PLAYER_HAS_CREDITS', m.player(k), 3, n))
                                                  for j, k in enumerate(pair) for n in LADDER])
    s8.watch(t, 6, every=1.0)
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_area': mission}
CHECKS = {'engine_area': {'field': field, 'camp': camp, 'als': alias, 'cash': cash}}
