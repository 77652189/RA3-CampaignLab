"""A4「冰雕里的兵」粗模 (docs/story/outline.md A4, card in docs/story/levels.md): 守, 镜像关① (J4 is the attack).

Imperial remnants hide troops in the snow festival's ice sculptures to seize a convoy carrying clones. The convoy
(three trucks; rough: ore collectors -- unarmed, 500 health) leaves `convoy leaves` seconds in and rolls east along
the road to the exit on its own; every `tick` seconds the mission sends it on again, so the player escorts it but
does not drive it. Three plazas beside the road, each walled by snow banks on three sides and open onto the road by
a gate, hold two sculptures each, each sculpture two troops. A truck on a plaza's approach breaks that plaza's
sculptures and its troops come out (a sculpture the player breaks earlier lets its own out then); from then on every
`tick` they are ordered at the leading truck still on the road. The player's ice engineers can freeze a block of ice
in a gate (it melts after a while: the wall's lifetime param) -- while one stands there the plaza's troops guard
their plaza instead -- or the player can break the sculptures early and fight the troops before the convoy comes.
Two trucks at the exit: Mission Won; two trucks lost: Mission Lost.

Published (the cast): truck 1-3, engineer 1-2, guardian, riptide (the player's); sculpture k-i (plaza k's i-th),
bank (every plaza), troop k-i-n (sculpture k-i's n-th, created where it stood when it breaks) -- the enemy's.
Marks: exit, seal 1-3 (where ice in a gate stands); facts: convoy leaves, tick; endings: the win and lose scripts.
"""
from maps import festival
from missions import festival_parts as fp
from parts import Mission, Role, Script, square
from units import festival as fest
from units import icewall as iw

TROOPS = ('JapanAntiVehicleInfantry', 'JapanAntiInfantryInfantry')     # each sculpture hides a tank buster and a warrior
LEAVE, TICK = 60.0, 3.0
GATE_AREA = 90.0                                # half-side of the area a wall must stand in to hold a gate
WALL_SIDE = 240.0                               # the A4 engineer's block: square or turned 45 degrees, it reaches
                                                # into both side banks (inner faces +-98, outer +-122)
OBJ = 'Objective01 - CNV A4'
WIN, LOST = 'CNV A4 - Win', 'CNV A4 - Lost'


def troop(k, i, n):
    return f'UNIT - CNV A4 Troop {k}-{i}-{n}'


def mission(name='CampA4'):
    # the engineer builds a small core that leaves a square block of ice over the gate and the banks' ends
    # (units/icewall.py seed: a bar comes out at 45 degrees whatever is asked, and the gates stayed open)
    wall = iw.wall('CNV_A4IceWall', length=WALL_SIDE, shape='square')
    core = iw.seed('CNV_A4IceSeed', wall.id)
    eng = iw.engineer(wall_id=core.id)
    sculpt, bank = fest.sculpture(), fest.bank(length=fp.GATE)
    m = Mission(name=name, map=festival, units=[eng, core, wall, sculpt, bank],
                objectives=[(OBJ, 'MISSIONOBJ:CNVA4_1', 'MISSIONOBJ:CNVA4_1_DESC')],
                facts={'convoy leaves': LEAVE, 'tick': TICK})
    convoy = fp.Convoy(m, 'A4', 'p1', LEAVE, TICK)
    for j, dx in enumerate((-30, 30), 1):
        m.put(eng.id, 'west field', 250 + dx, 100, name=f'UNIT - CNV A4 Engineer {j}', role=f'engineer {j}')
    for dx in (-90, -30, 30, 90):
        m.put('AlliedAntiVehicleVehicleTech1', 'west field', 250 + dx, 30, role='guardian')
    for dx in (-30, 30):
        m.put('AlliedAntiInfantryVehicle', 'west field', 250 + dx, -40, role='riptide')

    reveal, chase = [], []
    for k in fp.plazas(m, bank, 'A4'):
        s = fp.north(m, k)
        approach = f'CNV A4 Approach {k}'
        m.areas[approach] = square(*m.site(f'approach {k}'), m.where(f'approach {k}').r)
        names = []
        for i, dx in enumerate((-45, 45), 1):
            sname = f'UNIT - CNV A4 Sculpture {k}-{i}'
            names.append(sname)
            m.put(sculpt.id, f'plaza {k}', dx, s * 30, side='s1', name=sname, role=f'sculpture {k}-{i}')
            hide = f'CNV A4 Hide {k}-{i}'
            m.waypoints[hide] = m.site(f'plaza {k}', dx, -s * 30)
            for n, tmpl in enumerate(TROOPS, 1):     # created when the sculpture breaks (contract: by that script)
                m.cast[f'troop {k}-{i}-{n}'] = Role(tmpl, troop(k, i, n), 's1', [f'plaza {k}'])
            reveal.append(Script(f'CNV A4 - Out {k}-{i}', [('NAMED_DESTROYED', sname)],
                                 [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', troop(k, i, n), tmpl, m.team('s1'), hide)
                                  for n, tmpl in enumerate(TROOPS, 1)] +
                                 [('SET_FLAG', f'CNV_A4_Out_{k}', 1)]))
        reveal += [Script(f'CNV A4 - Ambush {k} by {j + 1}', [('NAMED_INSIDE_AREA', t, approach)],
                          [('NAMED_KILL', n) for n in names]) for j, t in enumerate(convoy.trucks)]
        # a wall in the gate holds the plaza's troops in it (they guard the plaza), else they chase the convoy: a
        # rule of the mission, since a wall built in play does not bar infantry's way as its shape says (bench
        # 2026-10-23: the same wall placed by the map held them 37 s, built -- or left by a core, even 400 across
        # -- they walked round it at once)
        gate_area, plaza_area = f'CNV A4 Gate {k}', f'CNV A4 Plaza {k}'
        m.areas[gate_area] = square(*m.point(f'seal {k}'), GATE_AREA)
        m.areas[plaza_area] = square(*m.site(f'plaza {k}'), m.where(f'plaza {k}').r)
        walled = ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player('p1'), 3, 1, wall.id, gate_area)
        open_ = ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player('p1'), 2, 0, wall.id, gate_area)
        them = [troop(k, i, n) for i in (1, 2) for n in range(1, len(TROOPS) + 1)]
        # out, they go for the leading truck still on the road (bench 2026-10-23: sent toward the exit they ran
        # ahead of the convoy at its own speed and never fired on it)
        chase += [Script(f'CNV A4 - Chase {k} at {j + 1}',
                         [('FLAG', f'CNV_A4_Out_{k}', 1), ('TIMER_EXPIRED', convoy.timer), open_] + convoy.chase(j),
                         [('NAMED_ATTACK_NAMED', t, target) for t in them], once=False)
                  for j, target in enumerate(convoy.trucks)]
        chase += [Script(f'CNV A4 - Held {k}', [('FLAG', f'CNV_A4_Out_{k}', 1), ('TIMER_EXPIRED', convoy.timer), walled],
                         [('UNIT_GUARD_AREA', t, plaza_area) for t in them], once=False)]

    m.strings.update({
        'SCRIPT:CNVA4_INTRO': 'A4 冰雕里的兵：帝国残部把兵藏进了雪祭的冰雕。运送克隆体的车队一分钟后出发，护送它穿过会场。',
        'MISSIONOBJ:CNVA4_1': 'A4 目标：护送车队穿过雪祭会场',
        'MISSIONOBJ:CNVA4_1_DESC': '三辆车里至少两辆到达东岸。冰幕工兵能在广场出口冻一道冰墙，把冰雕里的兵封在里面，墙过一会儿会化。',
        'SCRIPT:CNVA4_GO': 'A4：车队出发了。',
        'SCRIPT:CNVA4_SAFE': 'A4：一辆车到达东岸。',
        'SCRIPT:CNVA4_WIN': 'A4：车队安全通过会场。',
        'SCRIPT:CNVA4_LOST': 'A4：车队被劫走了……',
    })
    m.scripts += [
        Script('CNV A4 - Intro', [], [('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA4_INTRO', 15.0),
                                      ('SET_MISSION_OBJECTIVE_STATUS', OBJ, 0), convoy.start()]),
        *convoy.go(), *reveal, *chase, *convoy.roll(), *convoy.tail(),     # the roll after the chases: it resets the tick
        Script(WIN, [('COUNTER', convoy.arrived, 3, 2)],
               [('SET_MISSION_OBJECTIVE_STATUS', OBJ, 2), ('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA4_WIN', 10.0),
                ('SET_FLAG', 'Mission Won', 1)]),
        Script(LOST, [('COUNTER', convoy.losses, 3, 2)],
               [('SET_MISSION_OBJECTIVE_STATUS', OBJ, 3), ('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA4_LOST', 10.0),
                ('SET_FLAG', 'Mission Lost', 1)])]
    m.endings += [WIN, LOST]
    return m
