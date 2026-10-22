"""A7「鹰派」粗模 (docs/story/outline.md A7, card in docs/story/levels.md), declared apart (was make_campa7.py on
make_campnew38's chain).

The hawk commander has taken the Liberty to "pre-emptively erase the Soviets"; the player fights their own flagship.
While the power station stands the carrier's deck jump works: the mission's scripts make it jump between its home
and a strike point at the edge of the player's base, every 'jump every' seconds from 'first jump' on, bringing what
its deck factory has built along (the AI never presses the jump button itself: NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT
on two alternating timers -- a timer stays expired, so each script pushes its own far out). The station down: a
caption, no more jumps. The carrier down: objective done, Mission Won. The enemy is the map's Soviet player, so the
hawks are red here.

Published (the cast): carrier, station, escort (the enemy's); guardian, ifv, factory, power (the player's);
marks: strike, home; facts: first jump, jump every; endings: the win script.
"""
from maps import island
from parts import Mission, Script
from units import liberty as lib

CARRIER, STATION = 'UNIT - CNV A7 Liberty', 'UNIT - CNV A7 Power'
WP_STRIKE, WP_HOME = 'CNV A7 Strike', 'CNV A7 Home'
JUMP_A, JUMP_B = 'CNV A7 JumpA', 'CNV A7 JumpB'
OBJ = 'Objective01 - CNV A7'
GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
FIRST, GAP = 40.0, 45.0
FAR = 99999.0                                   # a timer pushed out of the way
WIN = 'CNV A7 - Win'


def mission(name='CampA7'):
    unit = lib.liberty('CNV_Liberty', reload='0s', factory=GUARDIAN)      # the scripts pace the jumps, not a reload
    jump = unit.abilities['jump']
    m = Mission(name=name, map=island, units=[unit], objectives=[(OBJ, 'MISSIONOBJ:CNVA7_1', 'MISSIONOBJ:CNVA7_1_DESC')],
                facts={'first jump': FIRST, 'jump every': GAP})
    m.waypoint('strike', WP_STRIKE, 'base edge')
    m.waypoint('home', WP_HOME, 'east field')
    m.put('AlliedWarFactory', 'base factory', angle=3.1416, role='factory')
    m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power')
    for dx in (-90, -30, 30, 90):
        for dy in (0, 60):
            m.put(GUARDIAN, 'west field', dx, dy - 45, role='guardian')
    for dx in (-90, -30, 30, 90):
        m.put('AlliedAntiAirVehicleTech1', 'west field', dx, -125, role='ifv')
    m.put(unit.id, 'east field', side='s1', name=CARRIER, angle=3.1416, role='carrier')
    m.put('AlliedPowerPlant', 'east 3', -100, 100, side='s1', name=STATION, angle=3.1416, role='station')
    for dx in (-60, 0, 60):
        m.put(GUARDIAN, 'east 3', dx - 100, -50, side='s1', role='escort')
    m.strings.update({
        'SCRIPT:CNVA7_INTRO': 'A7 鹰派：司令开走了自由号。只要尼亚加拉电站还在，它的超时空甲板就能把它送到任何地方。',
        'MISSIONOBJ:CNVA7_1': 'A7 目标：击落自由号',
        'MISSIONOBJ:CNVA7_1_DESC': '自由号会跃迁到我方基地边上放无人机、卸下部队。先炸掉东北的电站，它就跳不了了。',
        'SCRIPT:CNVA7_JUMP': 'A7：自由号跃迁过来了！',
        'SCRIPT:CNVA7_POWER': 'A7：电站被毁，自由号的超时空甲板断电了！',
        'SCRIPT:CNVA7_WIN': 'A7：自由号被击落。',
    })
    alive = ('NAMED_NOT_DESTROYED', STATION)
    m.scripts += [
        Script('CNV A7 - Intro', [], [('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA7_INTRO', 20.0),
                                      ('SET_MISSION_OBJECTIVE_STATUS', OBJ, 0),
                                      ('SET_MILLISECOND_TIMER', JUMP_A, FIRST), ('SET_MILLISECOND_TIMER', JUMP_B, FAR)]),
        Script('CNV A7 - Jump Strike', [('TIMER_EXPIRED', JUMP_A), alive],
               [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', CARRIER, jump, WP_STRIKE),
                ('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA7_JUMP', 5.0),
                ('SET_MILLISECOND_TIMER', JUMP_A, FAR), ('SET_MILLISECOND_TIMER', JUMP_B, GAP)], once=False),
        Script('CNV A7 - Jump Home', [('TIMER_EXPIRED', JUMP_B), alive],
               [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', CARRIER, jump, WP_HOME),
                ('SET_MILLISECOND_TIMER', JUMP_B, FAR), ('SET_MILLISECOND_TIMER', JUMP_A, GAP)], once=False),
        Script('CNV A7 - Power Down', [('NAMED_DESTROYED', STATION)],
               [('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA7_POWER', 8.0)]),
        Script(WIN, [('NAMED_DESTROYED', CARRIER)],
               [('SET_MISSION_OBJECTIVE_STATUS', OBJ, 2), ('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA7_WIN', 10.0),
                ('SET_FLAG', 'Mission Won', 1)])]
    m.endings.append(WIN)
    return m
