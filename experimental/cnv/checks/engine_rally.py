"""Engine unit test: where a factory's new unit stops when no rally point is set -- QueueProductionExitUpdate's
NaturalRallyPoint, on a factory whose point lies farther out than the barracks' (docs/engine/production.md).

engine_production h / i (bench 11-11): the barracks' engineer (UnitCreatePoint (0, 18), NaturalRallyPoint (40, 18))
does not stop at (40, 18) but out at about (75-80, 24-33) -- on the line from the barracks' centre through the
rally point, not on the door line (y 18). Two readings of that: the point is pushed out along the centre-to-rally
line by a fixed length (~40), or scaled from the centre (~1.9). The Allied war factory (UnitCreatePoint (-20, 20),
NaturalRallyPoint (80, 20)) tells them apart: a fixed ~40 stops the tank about (119, 30), x 1.9 about (152, 38).

On the Niagara map the player's construction yard, a power plant and an Allied war factory at 'base factory' turned
180 degrees (exit to the west); money MONEY; at PRESS_AT s a script presses the factory's Guardian tank button.
Counters (four lines): 资金; 帧数 frames the player owns no tank since the money first fell; 坦克 how many tanks;
出口位 adds the step of each box (in the factory's frame: x out of the door, y sideways) the tank stands in.

Bench 11-11 (round 159): the Guardian tank's button built nothing (it wants Upgrade_AlliedTech2; 资金 3000 for 35 s);
with the Riptide CampRallyTank_mcp_1111_044501 (PASS): 2250 paid, the Riptide counted at 帧数 160, 出口位 1000010 from
s13 to s31 -- x 112-127, y 25-34: the fixed push (~(119, 30)), not the scaling. Simulator (sim.RALLY_PUSH 40): the
same 1000010 (tests/test_simbench.py test_a_new_unit_stops_beyond_the_natural_rally_point_as_the_bench).
"""
from maps import niagara
from parts import Mission, Script, Test, counted

TANK, FACTORY_T = 'AlliedAntiInfantryVehicle_Ground', 'AlliedWarFactory'   # the Riptide (no tech; the Guardian
BUTTON_NAME = 'Command_ConstructAlliedAntiInfantryVehicle_Ground'      # wants Upgrade_AlliedTech2: run 1 built none)
MONEY, PRESS_AT, RUN = 3000, 2.0, 30.0
FACTORY = (1550.0, 2560.0)              # niagara 'base factory'
# (name, (x from, x to, y from, y to) in the factory's frame, step): five x strips 90-190 over y 0..50, three y
# strips over x 90-190 (the door line at 20)
BOXES = (('X90', (90.0, 112.0, 0.0, 50.0), 1), ('X112', (112.0, 127.0, 0.0, 50.0), 10),
         ('X127', (127.0, 142.0, 0.0, 50.0), 100), ('X142', (142.0, 162.0, 0.0, 50.0), 1000),
         ('X162', (162.0, 190.0, 0.0, 50.0), 10000), ('Y10', (90.0, 190.0, 10.0, 25.0), 100000),
         ('Y25', (90.0, 190.0, 25.0, 34.0), 1000000), ('Y34', (90.0, 190.0, 34.0, 50.0), 10000000))


def _n(part):
    return f'UNIT - CNV Rally {part}'


def mission():
    m = Mission(name='CampRally', map=niagara, units=[], facts={})
    m.spawns |= {TANK}
    m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
    m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power', name=_n('Power'))
    m.put(FACTORY_T, 'base factory', 0.0, 0.0, angle=3.1416, role='factory', name=_n('Factory'))
    return m


def rally_test(m):
    t = Test()
    p1 = m.player('p1')
    exits = []
    for name, (xa, xb, ya, yb), step in BOXES:      # turned 180 degrees: (x, y) -> (-x, -y)
        x0, x1, y0, y1 = FACTORY[0] - xb, FACTORY[0] - xa, FACTORY[1] - yb, FACTORY[1] - ya
        t.areas[f'Test {name}'] = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        exits.append((name, step))
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, MONEY),
                                                 ('SET_MILLISECOND_TIMER', 'Test Press', PRESS_AT)]))
    t.scripts.append(Script('Test - press', [('TIMER_EXPIRED', 'Test Press')],
                            [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('Factory'), BUTTON_NAME)]))
    t.counters.append(('CNV_Rally_Money', '资金'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Rally_Money')], once=False))
    t.scripts.append(Script('Test - paying', [('COUNTER', 'CNV_Rally_Money', 0, MONEY)], [('SET_FLAG', 'Test Paying', 1)]))
    t.counters.append(('CNV_Rally_Frames', '帧数'))
    counted('CNV_Rally_Made', '坦克', t, template=TANK, most=3)
    t.scripts.append(Script('Test - frames', [('FLAG', 'Test Paying', 1), ('COUNTER', 'CNV_Rally_Made', 2, 0)],
                            [('INCREMENT_COUNTER', 1, 'CNV_Rally_Frames')], once=False))
    t.counters.append(('CNV_Rally_Exit', '出口位'))
    t.scripts.append(Script('Test - exit zero', [], [('SET_COUNTER', 'CNV_Rally_Exit', 0)], once=False))
    t.scripts += [Script(f'Test - exit {a}', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', 3, 1,
                                                TANK, f'Test {a}')],
                         [('INCREMENT_COUNTER', step, 'CNV_Rally_Exit')], once=False)
                  for a, step in exits]
    t.expect = [('坦克', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


MISSION = {'engine_rally': mission}
CHECKS = {'engine_rally': {'tank': rally_test}}       # mod CampRallyTank
