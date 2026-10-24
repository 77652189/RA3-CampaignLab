"""J4「冰雕里的兵」粗模 (docs/story/outline.md J4, card in docs/story/levels.md): 追, 镜像关① (A4 is the defence).

The same festival from the other side. The empire hid its troops in the sculptures to seize the Allies' convoy of
clones, but the Allies saw through it and froze every plaza's gate shut (ice placed with the map: it bars infantry
for real, where ice made in play does not -- see A4). The player's troops stand trapped in the three plazas; the
player's combining mechs, camped north of the plazas, must come round to the gates, join, and break the ice with
the joined form's breaker beam (units/combo.py) to let them out before the convoy (the enemy's three trucks) has
rolled past. The trucks come onto the road only when the convoy sets off (LEAVE): the time to free the troops. Allied Guardians guard the road by plazas 2 and 3. Two trucks destroyed: Mission Won; two trucks at
the exit: Mission Lost.

Objectives in stages (as A4): from the start, break the ice before the departure (with a countdown; done at the
first gate broken in time, failed if none is) and two bonuses, all three trucks and all three gates; when the
convoy appears, taking it.

Published (the cast): truck 1-3, ice 1-3 (the gate ice), escort (the enemy's); parent 1-2, child 1-2, troop
k-n (plaza k's n-th: two tank busters, two warriors) (the player's). Marks: exit, seal 1-3 (where the gate ice
stands); facts: convoy leaves, tick; endings: the win and lose scripts.
"""
from maps import festival
from missions import festival_parts as fp
from parts import Goal, Mission, Script
from units import combo
from units import icewall as iw

TROOPS = ('JapanAntiVehicleInfantry', 'JapanAntiVehicleInfantry', 'JapanAntiInfantryInfantry',
          'JapanAntiInfantryInfantry')
SPOTS = ((-45, 20), (45, 20), (-45, 70), (45, 70))  # a plaza's troops, by its middle (y: away from the gate)
LEAVE, TICK = 90.0, 3.0                         # the mechs walk ~700 round to the gates first
ICE_LENGTH, ICE_HEALTH = 200.0, 3000            # across the head of the gate's ramp (120 wide); ~4 breaker shots
FREE, OBJ, BONUS = 'Objective01 - CNV J4', 'Objective02 - CNV J4', 'Bonus01 - CNV J4'
ALL_FREE = 'Bonus02 - CNV J4'
WIN, LOST = 'CNV J4 - Win', 'CNV J4 - Lost'
BROKEN = 'CNV_J4_Broken'                        # gate ice broken so far


def mission(name='CampJ4'):
    ice =iw.wall('CNV_J4GateIce', length=ICE_LENGTH, lifetime=None, health=ICE_HEALTH,
                  what=f'封门冰：盟军冻住广场出口的长条冰，长 {ICE_LENGTH:g}，{ICE_HEALTH} 血，不化（随地图摆放，真挡步兵）')
    child = combo.child()
    parent = combo.parent(child_id=child.id)
    m = Mission(name=name, map=festival, units=[parent, child, ice],
                objectives=[Goal(FREE, 'MISSIONOBJ:CNVJ4_0', 'MISSIONOBJ:CNVJ4_0_DESC', show=('ice 1', 'ice 2', 'ice 3')),
                            Goal(BONUS, 'MISSIONOBJ:CNVJ4_B1', 'MISSIONOBJ:CNVJ4_B1_DESC', bonus=True),
                            Goal(ALL_FREE, 'MISSIONOBJ:CNVJ4_B2', 'MISSIONOBJ:CNVJ4_B2_DESC', bonus=True,
                                 show=('ice 1', 'ice 2', 'ice 3')),
                            # the next stage: shown when the convoy appears (its markers come with the trucks)
                            Goal(OBJ, 'MISSIONOBJ:CNVJ4_1', 'MISSIONOBJ:CNVJ4_1_DESC',
                                 show=('truck 1', 'truck 2', 'truck 3'), at=None)],
                facts={'convoy leaves': LEAVE, 'tick': TICK})
    convoy = fp.Convoy(m, 'J4', 's1', LEAVE, TICK, enter=True)     # no convoy to hit before it sets off
    for j, dx in enumerate((-80, 80), 1):
        m.put(parent.id, 'north camp', dx, 0, name=f'UNIT - CNV J4 Parent {j}', role=f'parent {j}', angle=-1.5708)
        m.put(child.id, 'north camp', dx, 70, name=f'UNIT - CNV J4 Child {j}', role=f'child {j}', angle=-1.5708)
    for k in fp.plazas(m, 'J4'):
        s = fp.north(m, k)
        m.put(ice.id, f'gate {k}', 0, -s * fp.SEAL_IN, side='s1', name=f'UNIT - CNV J4 Ice {k}', role=f'ice {k}',
              angle=0.0)
        for n, (tmpl, (dx, dy)) in enumerate(zip(TROOPS, SPOTS), 1):
            m.put(tmpl, f'plaza {k}', dx, s * dy, name=f'UNIT - CNV J4 Troop {k}-{n}', role=f'troop {k}-{n}')
    for k in (2, 3):
        for dx in (-40, 40):
            m.put('AlliedAntiVehicleVehicleTech1', f'approach {k}', 250 + dx, 0, side='s1', role='escort')

    m.strings.update({
        'SCRIPT:CNVJ4_INTRO': 'J4 冰雕里的兵：盟军识破了冰雕，把三个广场的出口都冻住了。用合体机甲砸开冰，放兵出来劫车队。',
        'MISSIONOBJ:CNVJ4_0': '车队出发前砸开广场出口的冰',
        'MISSIONOBJ:CNVJ4_0_DESC': '兵被冻在三个广场里。合体机甲合体后能砸开冰，放他们出来。车队一分半后从西边出发。',
        'MISSIONOBJ:CNVJ4_1': '劫下克隆体车队',
        'MISSIONOBJ:CNVJ4_1_DESC': '三辆车里打掉两辆，别让两辆逃到东岸。合体机甲分开时也能打车。',
        'MISSIONOBJ:CNVJ4_B1': '三辆车全部截下',
        'MISSIONOBJ:CNVJ4_B1_DESC': '一辆车都不让它跑掉。',
        'MISSIONOBJ:CNVJ4_B2': '放出全部三个广场的兵',
        'MISSIONOBJ:CNVJ4_B2_DESC': '三个广场出口的冰都砸开。',
        'SCRIPT:CNVJ4_TIMER': '车队出发',
        'SCRIPT:CNVJ4_GO': 'J4：车队出发了！',
        'SCRIPT:CNVJ4_SAFE': 'J4：一辆车逃到了东岸。',
        'SCRIPT:CNVJ4_WIN': 'J4：车队被截下了。',
        'SCRIPT:CNVJ4_LOST': 'J4：车队跑掉了……',
    })
    m.scripts += [
        Script('CNV J4 - Intro', [], [('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVJ4_INTRO', 15.0), convoy.start(),
                                      convoy.countdown('SCRIPT:CNVJ4_TIMER')]),
        *convoy.go(), *convoy.roll(), *convoy.tail(),
        Script('CNV J4 - Convoy Goal', [('FLAG', convoy.rolling, 1)], m.reveal(OBJ)),
        # the first gate broken before the departure opens the way: that objective is done (its other markers go
        # with it; the all-gates bonus keeps its own); none broken by then: failed
        *[Script(f'CNV J4 - Freed {k}', [('NAMED_DESTROYED', m.role(f'ice {k}').name), ('FLAG', 'CNV_J4_Freed', 0),
                                         ('FLAG', convoy.rolling, 0)],
                 [('SET_FLAG', 'CNV_J4_Freed', 1)] + m.done(FREE)) for k in (1, 2, 3)],
        Script('CNV J4 - Freed None', [('FLAG', convoy.rolling, 1), ('FLAG', 'CNV_J4_Freed', 0)], m.failed(FREE)),
        *[Script(f'CNV J4 - Broken {k}', [('NAMED_DESTROYED', m.role(f'ice {k}').name)],
                 [('INCREMENT_COUNTER', 1, BROKEN)]) for k in (1, 2, 3)],
        Script('CNV J4 - All Free', [('COUNTER', BROKEN, 3, 3)], m.done(ALL_FREE)),
        Script('CNV J4 - Bonus Done', [('COUNTER', convoy.losses, 2, 3)], m.done(BONUS)),
        Script('CNV J4 - Bonus Failed', [('COUNTER', convoy.arrived, 3, 1)], m.failed(BONUS)),
        Script(WIN, [('COUNTER', convoy.losses, 3, 2)],
               m.done(OBJ) + [('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVJ4_WIN', 10.0), ('SET_FLAG', 'Mission Won', 1)]),
        Script(LOST, [('COUNTER', convoy.arrived, 3, 2)],
               m.failed(OBJ) + [('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVJ4_LOST', 10.0), ('SET_FLAG', 'Mission Lost', 1)])]
    m.endings += [WIN, LOST]
    return m
