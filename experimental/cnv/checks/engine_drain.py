"""LoseHealthUpdate on its retail host: three Dreadnoughts (SovietAntiStructureShip, 1500 HP; ModuleTag_RapidLaunchHealthDrain
HealthTrigger 101 %, DamagePerSecond 50, RequiredStatus GENERIC_TOGGLE_STATE, ForbiddenStatus UNDER_IRON_CURTAIN), the
player's, in the sea west of the island, holding fire. Its ToggleState names the drain (`<Module ModuleId=...>`), as the
Kirov's names its own (engine_acts11 KV: drained 200 a second while on).
  P  Command_ToggleRapidLaunchSpecialPower pressed at 3 s and again at 15 s.   [100 -> 60 at 15 s, held]
  C  pressed at 3 s, UNDER_IRON_CURTAIN given by script at 8 s.                [100 -> 83 at 8 s, held]
  S  GENERIC_TOGGLE_STATE given by script at 3 s, no press (E146's script bit, on the retail host this time). [100]
Counters: 血P, 血C, 血S (health %); 态 = P GENERIC + 10 C GENERIC + 100 S GENERIC + 1000 C UNDER_IRON_CURTAIN
[0 -> 111 (3 s) -> 1111 (8 s) -> 1110 (15 s)].
"""
from maps import island
from parts import Mission, Script, Test, status
from checks import engine_scripts8 as s8

SHIPS = {'P': 2200.0, 'C': 2500.0, 'S': 2800.0}
PRESS = 'Command_ToggleRapidLaunchSpecialPower'


def _n(row):
    return 'CNV Drain ' + row


def mission():
    m = Mission(name='CampDrain', map=island, units=[], facts={})
    for row, y in SHIPS.items():
        m.put('SovietAntiStructureShip', 'start', 400.0 - 1250.0, y - 2500.0, angle=0.0, name=_n(row), role=row)
    return m


def check(m):
    t = Test()
    s8.at(t, 'hold', 0.1, [('UNIT_CHANGE_OBJECT_STATUS', _n(r), status('NO_ATTACK'), 1) for r in SHIPS] +
          [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
    s8.at(t, 'press', 3.0, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n(r), PRESS) for r in 'PC'] +
          [('UNIT_CHANGE_OBJECT_STATUS', _n('S'), status('GENERIC_TOGGLE_STATE'), 1)])
    s8.at(t, 'curtain', 8.0, [('UNIT_CHANGE_OBJECT_STATUS', _n('C'), status('UNDER_IRON_CURTAIN'), 1)])
    s8.at(t, 'back', 15.0, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('P'), PRESS)])
    bit = lambda row, b: ('UNIT_HAS_OBJECT_STATUS', _n(row), status(b))  # noqa: E731
    for row in SHIPS:
        t.counters.append(('CNV_Drain_' + row, '血' + row))
        t.scripts.append(Script('Test - Drain hp ' + row, [],
                                [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', _n(row), 'CNV_Drain_' + row)], once=False))
    s8.total(t, 'CNV_Drain_State', '态', [(1, bit('P', 'GENERIC_TOGGLE_STATE')), (10, bit('C', 'GENERIC_TOGGLE_STATE')),
                                          (100, bit('S', 'GENERIC_TOGGLE_STATE')),
                                          (1000, bit('C', 'UNDER_IRON_CURTAIN'))])
    s8.watch(t, 22.0)
    return t


MISSION = {'engine_drain': mission}
CHECKS = {'engine_drain': {'a': check}}
