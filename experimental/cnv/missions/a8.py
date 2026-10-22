"""A8「海上发布会」粗模 (docs/story/outline.md A8), declared apart (was make_campa8.py on make_campnew38's chain).

Hale holds his launch on the sea, the time machine warming up; three power platforms to destroy (rough: named
power plants on the east side, each with two Hammers and a Bullfrog -- anti-air, the carrier's counter, units.md
5.6 rule 3). The player has the Liberty (drones, deck jump with a 45 s reload, a deck factory building Guardians),
four Guardians under it, a war factory and a power plant. All three platforms down: objective done, Mission Won.
The carrier down: Mission Lost (5.6 rule 2: one copy, lose it and you lose).
carrier=False: the A/B control -- no carrier, eight Guardians and four IFVs instead.
"""
from maps import island
from parts import Mission, Obj, Script
from units import liberty as lib

CARRIER = 'UNIT - CNV A8 Liberty'
PLATFORMS = [(3400.0, 2200.0), (3500.0, 2900.0), (3200.0, 3500.0)]
P_NAMES = [f'UNIT - CNV A8 Platform {k + 1}' for k in range(3)]
CARRIER_AT = (1300.0, 2300.0)
NEAR_P1 = (3150.0, 2150.0)                      # a waypoint by platform 1 (tests jump there)
WP_P1 = 'CNV A8 Near Platform 1'
OBJ = 'Objective01 - CNV A8'
GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
START = island.START


def mission(carrier=True, name='CampA8'):
    unit = lib.liberty('CNV_Liberty', reload='45s', factory=GUARDIAN)
    m = Mission(name=name, map=island, units=[unit] if carrier else [],
                objectives=[(OBJ, 'MISSIONOBJ:CNVA8_1', 'MISSIONOBJ:CNVA8_1_DESC')],
                waypoints={WP_P1: NEAR_P1}, names=unit.names)
    m.objects += [Obj('AlliedWarFactory', START[0] + 300, START[1] + 60, angle=3.1416),
                  Obj('AlliedPowerPlant', START[0] + 300, START[1] - 140, angle=0.0)]
    if carrier:
        m.objects.append(Obj(unit.id, *CARRIER_AT, name=CARRIER, angle=0.0))
        m.objects += [Obj(GUARDIAN, CARRIER_AT[0] + dx, CARRIER_AT[1] + dy)
                      for dx, dy in ((-60, 0), (60, 0), (0, -60), (0, 60))]
    else:
        m.objects += [Obj(GUARDIAN, 1180.0 + dx, 2330.0 + dy) for dx in (-90, -30, 30, 90) for dy in (0, 60)]
        m.objects += [Obj('AlliedAntiAirVehicleTech1', 1180.0 + dx, 2250.0) for dx in (-90, -30, 30, 90)]
    for (x, y), name in zip(PLATFORMS, P_NAMES):
        m.objects += [Obj('AlliedPowerPlant', x, y, side='s1', name=name, angle=3.1416),
                      Obj('SovietAntiVehicleVehicleTech1', x - 120, y - 40, side='s1'),
                      Obj('SovietAntiVehicleVehicleTech1', x - 120, y + 40, side='s1'),
                      Obj('SovietAntiAirShip_Ground', x - 60, y, side='s1')]
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
        Script('CNV A8 - Win', [('NAMED_DESTROYED', n) for n in P_NAMES],
               [('SET_MISSION_OBJECTIVE_STATUS', OBJ, 2), ('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA8_WIN', 10.0),
                ('SET_FLAG', 'Mission Won', 1)])]
    if carrier:
        m.scripts.append(Script('CNV A8 - Lost', [('NAMED_DESTROYED', CARRIER)],
                                [('SET_MISSION_OBJECTIVE_STATUS', OBJ, 3),
                                 ('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA8_LOST', 10.0), ('SET_FLAG', 'Mission Lost', 1)]))
    return m
