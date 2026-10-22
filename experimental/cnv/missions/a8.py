"""A8「海上发布会」粗模 (docs/story/outline.md A8), declared apart (was make_campa8.py on make_campnew38's chain).

Hale holds his launch on the sea, the time machine warming up; three power platforms to destroy (rough: named
power plants on the east side, each with two Hammers and a Bullfrog -- anti-air, the carrier's counter, units.md
5.6 rule 3). The player has the Liberty (drones, deck jump with a 45 s reload, a deck factory building Guardians),
four Guardians under it, a war factory and a power plant. All three platforms down: objective done, Mission Won.
The carrier down: Mission Lost (5.6 rule 2: one copy, lose it and you lose).
carrier=False: the A/B control -- no carrier, eight Guardians and four IFVs instead.

Published (the cast): carrier, guardian, ifv (control only), platform 1-3, hammer, bullfrog, factory, power;
endings: the win and lose scripts; mark: near platform 1. Placed on the island's sites west shore / west field / base * / east 1-3.
"""
from maps import island
from parts import Mission, Script
from units import liberty as lib

CARRIER = 'UNIT - CNV A8 Liberty'
P_NAMES = [f'UNIT - CNV A8 Platform {k + 1}' for k in range(3)]
WP_P1 = 'CNV A8 Near Platform 1'
OBJ = 'Objective01 - CNV A8'
GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
WIN, LOST = 'CNV A8 - Win', 'CNV A8 - Lost'


def mission(carrier=True, name='CampA8'):
    unit = lib.liberty('CNV_Liberty', reload='45s', factory=GUARDIAN)
    m = Mission(name=name, map=island, units=[unit] if carrier else [],
                objectives=[(OBJ, 'MISSIONOBJ:CNVA8_1', 'MISSIONOBJ:CNVA8_1_DESC')])
    m.waypoint('near platform 1', WP_P1, 'east 1', -250, -50)
    m.put('AlliedWarFactory', 'base factory', angle=3.1416, role='factory')
    m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power')
    if carrier:
        m.put(unit.id, 'west shore', name=CARRIER, angle=0.0, role='carrier')
        for dx, dy in ((-60, 0), (60, 0), (0, -60), (0, 60)):
            m.put(GUARDIAN, 'west shore', dx, dy, role='guardian')
    else:
        for dx in (-90, -30, 30, 90):
            for dy in (0, 60):
                m.put(GUARDIAN, 'west field', dx, dy - 45, role='guardian')
        for dx in (-90, -30, 30, 90):
            m.put('AlliedAntiAirVehicleTech1', 'west field', dx, -125, role='ifv')
    for k, pname in enumerate(P_NAMES):
        site = f'east {k + 1}'
        m.put('AlliedPowerPlant', site, side='s1', name=pname, angle=3.1416, role=f'platform {k + 1}')
        m.put('SovietAntiVehicleVehicleTech1', site, -120, -40, side='s1', role='hammer')
        m.put('SovietAntiVehicleVehicleTech1', site, -120, 40, side='s1')
        m.put('SovietAntiAirShip_Ground', site, -60, 0, side='s1', role='bullfrog')
    m.strings.update({
        'SCRIPT:CNVA8_INTRO': 'A8 海上发布会：黑尔的时间机器正在预热。打掉三座供电平台。自由号只有一艘，丢了就输。',
        'MISSIONOBJ:CNVA8_1': 'A8 目标：摧毁三座供电平台',
        'MISSIONOBJ:CNVA8_1_DESC': '用超时空甲板把部队跃迁到平台边上。平台旁有防空车，别让自由号被打掉。',
        'SCRIPT:CNVA8_WIN': 'A8：三座供电平台全部被毁。',
        'SCRIPT:CNVA8_LOST': 'A8：自由号被击落了……',
    })
    m.scripts += [
        Script('CNV A8 - Intro', [], [('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA8_INTRO', 20.0),
                                      ('SET_MISSION_OBJECTIVE_STATUS', OBJ, 0)]),
        Script(WIN, [('NAMED_DESTROYED', n) for n in P_NAMES],
               [('SET_MISSION_OBJECTIVE_STATUS', OBJ, 2), ('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA8_WIN', 10.0),
                ('SET_FLAG', 'Mission Won', 1)])]
    m.endings.append(WIN)
    if carrier:
        m.scripts.append(Script(LOST, [('NAMED_DESTROYED', CARRIER)],
                                [('SET_MISSION_OBJECTIVE_STATUS', OBJ, 3),
                                 ('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA8_LOST', 10.0), ('SET_FLAG', 'Mission Lost', 1)]))
        m.endings.append(LOST)
    return m
