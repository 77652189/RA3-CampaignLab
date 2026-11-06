"""Engine unit test: 物理碰撞 (ADR 0019 layer 2; CrusherInfo, DestroyDie + the collapse OCL) -- two questions only:
can a unit drive over another (and which), and does a destroyed building take time to go.

Retail data (SDK SageXML): CrusherInfo CrusherLevel / CrushableLevel -- infantry crushable 10, vehicles 20, Soviet
structures 40; the Hammer (SovietAntiVehicleVehicleTech1) inherits crusher 10 from BaseVehicle and sets its own 20;
the Apocalypse (SovietAntiVehicleVehicleTech3) crusher 30. Generals rule: crushed when crusher > crushable.
A structure (AlliedPowerPlant) has DestroyDie and a CreateObjectDie whose OCL makes AlliedPowerPlant_Collapse
(NO_COLLIDE UNATTACKABLE DEBRIS; LifetimeUpdate 10-30 s, then SlowDeath 10 s).

On the festival map, west field, three lanes along +x, 300 apart; every unit on HOLD_FIRE (no shots: a death is a
crush). In each lane the player's tank 200 west of an enemy unit, ordered at 'Test Go' (one second in) to a point 200
east of it (straight through):
  lane 1  Hammer -> enemy conscript (10)          lane 2  Hammer -> enemy guardian (20)
  lane 3  Apocalypse -> enemy guardian (20)
and an enemy power plant 600 north, NAMED_KILL at 'Test Go'.

Counters (four lines), every one counted from 'Test Go' on:
  帧数  frames since Go
  步兵  1 x frames the conscript is not destroyed + 1000 x frames it is dying + 1000000 x frames it is in its own spot
       (a square of half-side 30: did it step aside?)
  坦克  1 x frames lane 2's guardian is not destroyed + 1000 x frames lane 3's guardian is not destroyed
       + 1000000 x frames lane 2's Hammer is at its goal (half-side 40)
  建筑  1 x frames the plant is not destroyed + 1000 x frames it is dying + 1000000 x frames the enemy has a collapse
       object in the plant's square (half-side 150)

Bench 11-06 (B round 5; one run each):
  all CampCrushAll_mcp_1106_042112 (s46): 步兵 170127043 -- crushed at frame 43, never left its spot, lay dead 127
    frames (8.5 s, its SlowDeath); 坦克 605069701 -- lane 2's guardian alive throughout (the Hammer went round, at
    its goal from 96), lane 3's crushed at 69; 建筑 1000 -- the plant dying the kill frame only, gone the next; the
    collapse object never counted as the enemy's.
  b CampCrushBTwo_mcp_1106_042416 (s21): 镰刀 216000329 -- the Sickle (30) never crushed by the Apocalypse (30):
    strictly greater it is; the Apocalypse went round, at its goal from 113; 到点 238238 -- the free lane and the lane
    through the killed plant both at the goal from frame 91 (the wreck does not block); 电厂 1000 as above.
docs/engine/crush.md.
"""
from maps import festival
from parts import Mission, Script, Test, square

HAMMER, APOC = 'SovietAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech3'
CONSCRIPT, GUARDIAN = 'SovietAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech1'
PLANT, COLLAPSE = 'AlliedPowerPlant', 'AlliedPowerPlant_Collapse'
LANES = {1: (HAMMER, CONSCRIPT, -300.0), 2: (HAMMER, GUARDIAN, 0.0), 3: (APOC, GUARDIAN, 300.0)}
PLANT_DY = 600.0
RUN = 45.0
HOLD_FIRE = 3


def _n(part):
    return f'UNIT - CNV Crush {part}'


def mission():
    m = Mission(name='CampCrush', map=festival, units=[], facts={})
    m.spawns |= {COLLAPSE}
    for k, (tank, target, dy) in LANES.items():
        m.put(tank, 'west field', -200.0, dy, angle=0.0, role=f'tank {k}', name=_n(f'Tank {k}'))
        m.put(target, 'west field', 0.0, dy, angle=180.0, side='s1', role=f'target {k}', name=_n(f'Target {k}'))
    m.put(PLANT, 'west field', 0.0, PLANT_DY, side='s1', role='plant', name=_n('Plant'))
    return m


def crush_test(m):
    t = Test()
    p1, s1 = m.player('p1'), m.player('s1')
    x, y = m.site('west field')[:2]
    for k, (_, _, dy) in LANES.items():
        t.waypoints[f'Test Goal {k}'] = (x + 200.0, y + dy)
    t.areas['Test Spot 1'] = square(x, y + LANES[1][2], 30.0)
    t.areas['Test Goal 2'] = square(x + 200.0, y + LANES[2][2], 40.0)
    t.areas['Test Plant'] = square(x, y + PLANT_DY, 150.0)
    names = [_n(f'Tank {k}') for k in LANES] + [_n(f'Target {k}') for k in LANES]
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    start += [('UNIT_SET_STANCE', n, HOLD_FIRE) for n in names]
    t.scripts.append(Script('Test - start', [], start))
    go = [('MOVE_NAMED_UNIT_TO', _n(f'Tank {k}'), f'Test Goal {k}') for k in LANES] + [('NAMED_KILL', _n('Plant'))]
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)

    t.counters.append(('CNV_Crush_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Crush_Frames')], once=False))
    man, g2, g3, plant = _n('Target 1'), _n('Target 2'), _n('Target 3'), _n('Plant')
    rows = {
        2: ('步兵', [(('NAMED_NOT_DESTROYED', man), 1), (('NAMED_DYING', man), 1000),
                    (('NAMED_INSIDE_AREA', man, 'Test Spot 1'), 1000000)]),
        3: ('坦克', [(('NAMED_NOT_DESTROYED', g2), 1), (('NAMED_NOT_DESTROYED', g3), 1000),
                    (('NAMED_INSIDE_AREA', _n('Tank 2'), 'Test Goal 2'), 1000000)]),
        4: ('建筑', [(('NAMED_NOT_DESTROYED', plant), 1), (('NAMED_DYING', plant), 1000),
                    (('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1, COLLAPSE, 'Test Plant'), 1000000)]),
    }
    for k, (label, conds) in rows.items():
        t.counters.append((f'CNV_Crush_Row{k}', label))
        for j, (cond, step) in enumerate(conds):
            t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                    [('INCREMENT_COUNTER', step, f'CNV_Crush_Row{k}')], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


SICKLE = 'SovietScoutVehicle'                     # crushable 30, against the Apocalypse's crusher 30
LANES_B = {1: (APOC, SICKLE, -300.0), 2: (HAMMER, None, 0.0), 3: (HAMMER, PLANT, 300.0)}


def mission_b():
    m = Mission(name='CampCrushB', map=festival, units=[], facts={})
    for k, (tank, target, dy) in LANES_B.items():
        m.put(tank, 'west field', -200.0, dy, angle=0.0, role=f'tank {k}', name=_n(f'Tank {k}'))
        if target:
            m.put(target, 'west field', 0.0, dy, angle=180.0, side='s1', role=f'target {k}', name=_n(f'Target {k}'))
    return m


def crush_b(m):
    """Lane 1 Apocalypse -> enemy Sickle (30 against 30: is an equal level crushed?); lane 2 a Hammer on an empty
    lane (the free drive, 400); lane 3 a Hammer through an enemy power plant killed at Go (does the wreck block?)."""
    t = Test()
    p1 = m.player('p1')
    x, y = m.site('west field')[:2]
    for k, (_, _, dy) in LANES_B.items():
        t.waypoints[f'Test Goal {k}'] = (x + 200.0, y + dy)
        t.areas[f'Test Goal {k}'] = square(x + 200.0, y + dy, 40.0)
    names = [_n(f'Tank {k}') for k in LANES_B] + [_n('Target 1')]
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    start += [('UNIT_SET_STANCE', n, HOLD_FIRE) for n in names]
    t.scripts.append(Script('Test - start', [], start))
    go = [('MOVE_NAMED_UNIT_TO', _n(f'Tank {k}'), f'Test Goal {k}') for k in LANES_B] + [('NAMED_KILL', _n('Target 3'))]
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)
    t.counters.append(('CNV_Crush_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Crush_Frames')], once=False))
    sickle, plant = _n('Target 1'), _n('Target 3')
    at = lambda k: ('NAMED_INSIDE_AREA', _n(f'Tank {k}'), f'Test Goal {k}')  # noqa: E731
    rows = {
        2: ('镰刀', [(('NAMED_NOT_DESTROYED', sickle), 1), (('NAMED_DYING', sickle), 1000), (at(1), 1000000)]),
        3: ('到点', [(at(2), 1), (at(3), 1000)]),
        4: ('电厂', [(('NAMED_NOT_DESTROYED', plant), 1), (('NAMED_DYING', plant), 1000)]),
    }
    for k, (label, conds) in rows.items():
        t.counters.append((f'CNV_Crush_Row{k}', label))
        for j, (cond, step) in enumerate(conds):
            t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                    [('INCREMENT_COUNTER', step, f'CNV_Crush_Row{k}')], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, 20.0)]
    t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=20.0))]
    return t


MISSION = {'engine_crush': mission, 'engine_crush_b': mission_b}
CHECKS = {'engine_crush': {'all': crush_test}, 'engine_crush_b': {'two': crush_b}}
