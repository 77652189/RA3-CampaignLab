"""A8「海上发布会」粗模 (docs/story/outline.md A8), declared apart (was make_campa8.py on make_campnew38's chain).

Hale holds his launch on the sea, the time machine warming up; three power platforms to destroy (rough: named
power plants on the east side, each with two Hammers and a Bullfrog -- anti-air, the carrier's counter, units.md
5.6 rule 3). The player has the Liberty (drones, deck jump with a 45 s reload, a deck factory building Guardians),
four Guardians under it, a war factory and a power plant. All three platforms down: objective done, Mission Won.
The carrier down: Mission Lost (5.6 rule 2: one copy, lose it and you lose).
carrier=False: the A/B control -- no carrier, eight Guardians and four IFVs instead.

Published (the cast): carrier, guardian, ifv (control only), platform 1-3, hammer, bullfrog 1-3, factory, power;
endings: the win and lose scripts; mark: near platform 1. Placed on the island's sites west shore / west field / base * / east 1-3.
"""
from maps import island
from parts import Goal, Mission, Script
from units import liberty as lib

CARRIER = 'UNIT - CNV A8 Liberty'
P_NAMES = [f'UNIT - CNV A8 Platform {k + 1}' for k in range(3)]
WP_P1 = 'CNV A8 Near Platform 1'
OBJ, SURVIVE, BONUS = 'Objective01 - CNV A8', 'Objective02 - CNV A8', 'Bonus01 - CNV A8'
F_NAMES = [f'UNIT - CNV A8 Bullfrog {k + 1}' for k in range(3)]
GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
WIN, LOST = 'CNV A8 - Win', 'CNV A8 - Lost'


def mission(carrier=True, name='CampA8'):
    unit = lib.liberty('CNV_Liberty', reload='45s', factory=GUARDIAN)
    goals = [Goal(OBJ, 'MISSIONOBJ:CNVA8_1', 'MISSIONOBJ:CNVA8_1_DESC', show=('platform 1', 'platform 2', 'platform 3'))]
    if carrier:
        goals.append(Goal(SURVIVE, 'MISSIONOBJ:CNVA8_2', 'MISSIONOBJ:CNVA8_2_DESC', show=('carrier',)))
    goals.append(Goal(BONUS, 'MISSIONOBJ:CNVA8_B1', 'MISSIONOBJ:CNVA8_B1_DESC', bonus=True,
                      show=('bullfrog 1', 'bullfrog 2', 'bullfrog 3')))
    m = Mission(name=name, map=island, units=[unit] if carrier else [], objectives=goals)
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
        m.put('SovietAntiAirShip_Ground', site, -60, 0, side='s1', name=F_NAMES[k], role=f'bullfrog {k + 1}')
    m.strings.update({
        'SCRIPT:CNVA8_INTRO': 'A8 海上发布会：黑尔的时间机器正在预热。打掉三座供电平台。自由号只有一艘，丢了就输。',
        'MISSIONOBJ:CNVA8_1': '摧毁三座供电平台',
        'MISSIONOBJ:CNVA8_1_DESC': '用超时空甲板把部队跃迁到平台边上。',
        'MISSIONOBJ:CNVA8_2': '自由号必须存活',
        'MISSIONOBJ:CNVA8_2_DESC': '自由号只有一艘，被击落任务就失败。平台旁的牛蛙专打它。',
        'MISSIONOBJ:CNVA8_B1': '打掉三辆牛蛙防空',
        'MISSIONOBJ:CNVA8_B1_DESC': '每座平台旁都有一辆。',
        'SCRIPT:CNVA8_WIN': 'A8：三座供电平台全部被毁。',
        'SCRIPT:CNVA8_LOST': 'A8：自由号被击落了……',
    })
    m.scripts += [
        Script('CNV A8 - Intro', [], [('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA8_INTRO', 20.0)]),
        Script('CNV A8 - Bonus Done', [('NAMED_DESTROYED', n) for n in F_NAMES], m.done(BONUS)),
        Script(WIN, [('NAMED_DESTROYED', n) for n in P_NAMES],
               m.done(OBJ) + (m.done(SURVIVE) if carrier else []) +
               [('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA8_WIN', 10.0), ('SET_FLAG', 'Mission Won', 1)])]
    m.endings.append(WIN)
    if carrier:
        m.scripts.append(Script(LOST, [('NAMED_DESTROYED', CARRIER)],
                                m.failed(SURVIVE) + m.failed(OBJ) +
                                [('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA8_LOST', 10.0), ('SET_FLAG', 'Mission Lost', 1)]))
        m.endings.append(LOST)
    return m
