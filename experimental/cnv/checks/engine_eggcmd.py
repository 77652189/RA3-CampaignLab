"""Generic retail Japan egg button versus the concrete SDK button.

Retail a04/j04 use Command_UnPackJapanEgg (14 occurrences); SDK publishes
only template-specific commands. Prediction: generic defense/power eggs
stay cores at home; concrete defense drives 400 east and replaces there;
untouched defense stays home. Counters: replacement-at-goal bit mask,
living-name bit mask, original-core-at-home bit mask, logic frame.
Bits: generic defense 1, generic power 2, concrete defense 4, untouched 8.
Evidence: work/re/c_eggcmd_report.md. No terrain/arrival timing claim.
MEASURED A: f59 0/15/15/59; f249 4/15/11/249;
f393 4/15/11/393; f560 4/15/11/560.
MEASURED naval A: f57 0/7/7/57; f247/390/496 2/7/5/frame.
Naval legacy/untouched cores stay home; concrete button deploys in water.
"""
from maps import probe_border, niagara
from parts import Mission, Script, Test, counted, square
from checks import engine_scripts8 as s8

ROLES = ('generic', 'power', 'concrete', 'control')


def mission():
    m = Mission(name='CampEggCmd', map=probe_border, units=[], facts={})
    m.spawns |= {'JapanBaseDefense', 'JapanPowerPlant'}
    for k, role in enumerate(ROLES):
        egg = 'JapanPowerPlantEgg' if role == 'power' else 'JapanBaseDefenseEgg'
        m.put(egg, 'stop row', 0., -3100.+k*700., role=role, name='CNV EggCmd '+role)
        m.waypoint(role, 'Test EggCmd '+role, 'stop row', 400., -3100.+k*700.)
    return m


def check(m):
    t = Test()
    for k, role in enumerate(ROLES):
        u = m.role(role)
        t.areas['Test EggHome '+role] = square(1300., 1200.+k*700., 100.)
        t.areas['Test EggGoal '+role] = square(*m.point(role), 100.)
    s8.at(t, 'egg command', 5., [
        ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', m.role(role).name,
         'Command_UnPackJapanBaseDefenseEgg' if role == 'concrete' else 'Command_UnPackJapanEgg', m.mark(role))
        for role in ROLES[:3]])
    s8.total(t, 'CNV_EggCmd_Build', '建筑位', [
        (2**k, ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player(), 3, 1,
                'JapanPowerPlant' if role == 'power' else 'JapanBaseDefense', 'Test EggGoal '+role))
        for k, role in enumerate(ROLES)])
    s8.total(t, 'CNV_EggCmd_Name', '存活位', [
        (2**k, ('NAMED_NOT_DESTROYED', m.role(role).name)) for k, role in enumerate(ROLES)])
    s8.total(t, 'CNV_EggCmd_Core', '原处位', [
        (2**k, ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player(), 3, 1,
                m.role(role).template, 'Test EggHome '+role)) for k, role in enumerate(ROLES)])
    s8.frames(t, 'CNV_EggCmd_Frame', '逻辑帧', [])
    s8.watch(t, 34., .5)
    return t


NAVAL_ROLES = ('generic', 'concrete', 'control')


def naval_mission():
    """Three separated pads in Niagara's southern river, clear of bridges/island.

    Prediction: legacy and untouched cores stay home; the concrete button
    deploys a yard 200 north. Bits 1/2/4; expected final counters 2/7/5/frame.
    SDK JapanNavalYardEgg uses the water locomotor and its dedicated unpack.
    """
    m = Mission(name='CampEggNav', map=niagara, units=[], facts={})
    m.spawns.add('JapanNavalYard')
    for k, role in enumerate(NAVAL_ROLES):
        m.put('JapanNavalYardEgg', 'start', 1400., -1900.+k*700.,
              role=role, name='CNV EggNav '+role)
        m.waypoint(role, 'Test EggNav '+role, 'start', 1400., -1700.+k*700.)
    return m


def naval_check(m):
    t = Test()
    for k, role in enumerate(NAVAL_ROLES):
        t.areas['Test NavHome '+role] = square(2650., 600.+k*700., 90.)
        t.areas['Test NavGoal '+role] = square(*m.point(role), 90.)
    s8.at(t, 'naval egg command', 5., [
        ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', m.role(role).name,
         'Command_UnPackJapanNavalYardEgg' if role == 'concrete' else 'Command_UnPackJapanEgg',
         m.mark(role)) for role in NAVAL_ROLES[:2]])
    s8.total(t, 'CNV_EggNav_Build', '建筑位', [
        (2**k, ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player(), 3, 1,
                'JapanNavalYard', 'Test NavGoal '+role)) for k, role in enumerate(NAVAL_ROLES)])
    s8.total(t, 'CNV_EggNav_Name', '存活位', [
        (2**k, ('NAMED_NOT_DESTROYED', m.role(role).name)) for k, role in enumerate(NAVAL_ROLES)])
    s8.total(t, 'CNV_EggNav_Core', '原处位', [
        (2**k, ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player(), 3, 1,
                'JapanNavalYardEgg', 'Test NavHome '+role)) for k, role in enumerate(NAVAL_ROLES)])
    s8.frames(t, 'CNV_EggNav_Frame', '逻辑帧', [])
    s8.watch(t, 30., .5)
    return t


# engine_navship (A327, retail a07: Japan06's placed JapanNavalYard is pressed Command_ConstructJapanAntiVehicleShip
# once at the start; the ship needs Upgrade_JapanNavalYardTech2, which a07 gives that yard on Normal only, after a
# timer): two yards in the eggs' water, 'yard' given the upgrade at s0, 'bare' not, a JapanPowerPlant (a yard draws 50),
# money 20000; each pressed once at 2 s. 资金 / 船 (JapanAntiVehicleShip owned: 1800, BuildTime 18) / 逻辑帧.
def ship_mission():
    m = Mission(name='CampNavShip', map=niagara, units=[], facts={})
    for k, role in enumerate(('bare', 'yard')):
        m.put('JapanNavalYard', 'start', 1400., -1200. + 700. * k, role=role, name='CNV NavShip ' + role)
    m.put('JapanPowerPlant', 'base power', role='power', name='CNV NavShip Power')
    m.spawns.add('JapanAntiVehicleShip')
    return m


def ship_check(m):
    t, p1 = Test(), m.player('p1')
    s8.at(t, 'ship money', 0., [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 20000),
                                ('NAMED_RECEIVE_UPGRADE', 'Upgrade_JapanNavalYardTech2', m.role('yard').name)])
    s8.at(t, 'ship press', 2., [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(role).name,
                                 'Command_ConstructJapanAntiVehicleShip') for role in ('bare', 'yard')])
    t.scripts.append(Script('Test - ship money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_NavShip_Money')], once=False))
    t.counters.append(('CNV_NavShip_Money', '资金'))
    counted('CNV_NavShip_Ship', '船', t, template='JapanAntiVehicleShip')
    s8.frames(t, 'CNV_NavShip_Frame', '逻辑帧', [])
    s8.watch(t, 30., .5)
    return t


MISSION = {'engine_eggcmd': mission, 'engine_eggnav': naval_mission, 'engine_navship': ship_mission}
CHECKS = {'engine_eggcmd': {'a': check}, 'engine_eggnav': {'a': naval_check}, 'engine_navship': {'a': ship_check}}
