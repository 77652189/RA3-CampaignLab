"""Engine unit test: construction (ADR 0019 layer 2; docs/engine/construction.md) -- a structure's unpack after it is
placed (how many frames, slower short of power, what it carries meanwhile, whether it makes power, whether it can be
hurt) and the MCV deploying into a construction yard.

On the Niagara map the player's construction yard (+50 power), a power plant (+100), three barracks (-25 each), an
MCV in the west field and an enemy (Soviet_1) Hammer tank by the build spot, held (NO_ATTACK). One second in
('Test Go') each variant does one thing; at the start it deletes what it does not need:

  a  mcv      the MCV (health set to HALF first) is ordered to deploy (Command_UnPackAlliedMCV); yard, plant and
              barracks deleted
  b  plant    a power plant made by script at the build spot (UnpackTime 3 s); plant and barracks deleted: supply 50,
              demand 0; DAMAGE hit points by script 10 frames after it is made
  c  dim      as b with the three barracks kept: supply 50, demand 75 (the low-power factor 0.5)
  d  dark     as b with the yard deleted and barracks 1 kept: supply 0, demand 25 (the factor at its floor 0.3)
  e  soviet   a Soviet barracks made by script for the player (UnpackTime 10 s; BuildTime 0, no queue item behind it);
              plant and barracks deleted; the Hammer tank is let go and ordered to attack it

Counters (four lines), every one counted from 'Test Go' on, frames added per frame while the thing holds:
  帧数    frames since Go
  状态帧  1 x frames the player owns an object UNDER_CONSTRUCTION + 1000 x frames one is UNPACKING
  建成帧  1 x (a) frames a yard stands on the MCV's spot / (b-e) frames the made building is UNPACKING
          + 1000 x (a) frames the MCV is still there / (b-d) frames the power plant does not count yet / (e) frames
          the barracks does not draw yet
  血量    the target's health in percent (a: by the MCV's name -- it passes to the yard)

Bench 11-05 (round 45; docs/engine/construction.md):
  a CampBuildA_mcp_1105_214815: 状态帧 6000, 建成帧 6020 at 帧数 26 (the yard from Go + 6), 血量 50 throughout
    (the counter OCR misreads it as 0-9 where the blue yard is drawn behind the counter: 50 in the frames).
  b CampBuildB_mcp_1105_214016: 46046 / 46046, 血量 90 from frame 10.
  c CampBuildC_mcp_1105_214217: 68068 / 68068.   d CampBuildD_mcp_1105_214416: 77077 / 77077.
  e CampBuildE_mcp_1105_214612: 151151 / 151151, 血量 94 at s1 down ~3 a shot to 52 at s17.
  First tries: the plain NAMED_USE_COMMANDBUTTON_ABILITY sent the MCV south-west (no point); a script
  UNIT_SET_HEALTH 2500 and a COMPLETELY_BUILT condition read 0 throughout (dropped, not looked into).
Against the model (RA3-EngineModel construction.py, tests/test_objects_bench.py): every reading the same but e's
health (the Hammer: layers 3-4).
"""
from maps import niagara
from parts import Mission, Script, Test, square, status

MCV, YARD, PLANT, SOVIET, HAMMER = ('AlliedMCV', 'AlliedConstructionYard', 'AlliedPowerPlant', 'SovietBarracks',
                                    'SovietAntiVehicleVehicleTech1')
HALF, DAMAGE = 2500, 100                # MCV MaxHealth 5000; the plant's 1000
RUN = {'a': 14.0, 'b': 8.0, 'c': 9.0, 'd': 9.0, 'e': 16.0}
BUILD = ('west field', -120.0, 260.0)   # the spot scripts make the building on (1060, 2635)
MCV_AT = ('west field', -220.0, -120.0)
DELETE = {'a': ('Yard', 'Power', 'Barracks 1', 'Barracks 2', 'Barracks 3'),
          'b': ('Power', 'Barracks 1', 'Barracks 2', 'Barracks 3'), 'c': ('Power',),
          'd': ('Yard', 'Power', 'Barracks 2', 'Barracks 3'), 'e': ('Power', 'Barracks 1', 'Barracks 2', 'Barracks 3')}
# the excess power while the new building is not counted yet (op, value): b 50 -> 150, c -25 -> 75, d -25 -> 75,
# e 50 -> 25
POWER_WAIT = {'b': (0, 150), 'c': (0, 75), 'd': (0, 75), 'e': (3, 50)}


def _n(part):
    return f'UNIT - CNV Build {part}'


def mission():
    m = Mission(name='CampBuild', map=niagara, units=[], facts={})
    m.spawns |= {PLANT, SOVIET}
    m.put(YARD, 'base yard', angle=0.0, role='yard', name=_n('Yard'))
    m.put(PLANT, 'base power', angle=0.0, role='power', name=_n('Power'))
    for k, dy in enumerate((0.0, 140.0, 280.0)):
        m.put('AlliedBarracks', 'base factory', 0.0, dy, angle=3.1416, role=f'barracks {k + 1}',
              name=_n(f'Barracks {k + 1}'))
    m.put(MCV, MCV_AT[0], *MCV_AT[1:], angle=0.0, role='mcv', name=_n('MCV'))
    m.put(HAMMER, BUILD[0], BUILD[1] + 160.0, BUILD[2], side='s1', angle=3.1416, role='hammer', name=_n('Hammer'))
    m.waypoint('build spot', 'Test Build Spot', *BUILD)
    m.waypoint('mcv spot', 'Test MCV Spot', *MCV_AT)
    return m


def build_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    x, y = m.waypoints['Test Build Spot']
    mx, my = m.site(*MCV_AT)
    template, target, (tx, ty) = {'a': (YARD, _n('MCV'), (mx, my)), 'e': (SOVIET, _n('Made'), (x, y))}.get(
        which, (PLANT, _n('Made'), (x, y)))
    t.areas['Test Target'] = square(tx, ty, 150.0)
    start = [('MAP_REVEAL_ALL_PERM', p1), ('UNIT_CHANGE_OBJECT_STATUS', _n('Hammer'), 'NO_ATTACK', 1),
             ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)] + [('NAMED_DELETE', _n(p)) for p in DELETE[which]]
    if which == 'a':
        start.append(('NAMED_DAMAGE', _n('MCV'), HALF))
    t.scripts.append(Script('Test - start', [], start))
    if which == 'a':
        # the plain NAMED_USE_COMMANDBUTTON_ABILITY gives the deploy no point: bench 11-05, the MCV drove south-west
        go = [('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', _n('MCV'), 'Command_UnPackAlliedMCV', 'Test MCV Spot')]
    else:
        go = [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', target, template, m.team('p1'), 'Test Build Spot')]
    if which == 'e':
        go += [('UNIT_CHANGE_OBJECT_STATUS', _n('Hammer'), 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', _n('Hammer'), target)]
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)

    t.counters.append(('CNV_Build_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Build_Frames')], once=False))
    if which in 'bcd':
        t.scripts.append(Script('Test - damage', [going, ('COUNTER', 'CNV_Build_Frames', 2, 10)],
                                [('NAMED_DAMAGE', target, DAMAGE)]))

    t.counters.append(('CNV_Build_Status', '状态帧'))
    t.scripts += [Script(f'Test - status {st}', [going, ('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', p1, 3, 1,
                                                          status(st))],
                         [('INCREMENT_COUNTER', step, 'CNV_Build_Status')], once=False)
                  for st, step in (('UNDER_CONSTRUCTION', 1), ('UNPACKING', 1000))]

    t.counters.append(('CNV_Build_Done', '建成帧'))
    if which == 'a':                        # the yard's frames on the MCV's spot
        made = ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, YARD, 'Test Target')
    else:                                   # the made building's own UNPACKING
        made = ('UNIT_HAS_OBJECT_STATUS', target, status('UNPACKING'))
    t.scripts.append(Script('Test - made', [going, made], [('INCREMENT_COUNTER', 1, 'CNV_Build_Done')], once=False))
    if which == 'a':
        wait = ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, MCV, 'Test Target')
    else:
        wait = ('PLAYER_EXCESS_POWER_COMPARE_VALUE', p1, *POWER_WAIT[which])
    t.scripts.append(Script('Test - waiting', [going, wait], [('INCREMENT_COUNTER', 1000, 'CNV_Build_Done')],
                            once=False))

    t.counters.append(('CNV_Build_Health', '血量'))
    t.scripts.append(Script('Test - health', [going], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target,
                                                        'CNV_Build_Health')], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN[which])]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN[which]))]
    return t


MISSION = {'engine_build': mission}
CHECKS = {'engine_build': {w: (lambda m, w=w: build_test(m, w)) for w in 'abcde'}}
