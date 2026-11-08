"""Engine unit test: a factory's production (ADR 0019 layer 2; docs/engine/production.md) -- the build time, paying as
it builds, waiting while short of money, building slower while short of power, where the unit comes out.

On the Niagara map the player's construction yard (+50 power), a power plant (+100) and three barracks (-25 each) at
the base; the player orders one engineer (AlliedEngineer: BuildTime 10, BuildCost 500) by clicking the sidebar's
infantry tab and its button (e / f: a script presses the factory's build button instead -- round 39's "no script
action makes a factory build" was wrong, NAMED_USE_COMMANDBUTTON_ABILITY does). At the start each variant deletes
what it does not need:

  a  normal   barracks 2 and 3 deleted: supply 150, demand 25; money MONEY
  b  broke    as a with money SHORT; GIVE s after the money falls below 5, BONUS more
  c  dark     the yard, the power plant and barracks 2, 3 deleted: supply 0, demand 25
  d  dim      the power plant deleted: supply 50, demand 75 (three barracks)

Counters (four lines): 资金 the player's money; 帧数 frames from the first one that sees the money below the start
(the flag 'Test Paying') while the player owns no engineer; 工程师 how many engineers; 出口位 an engineer of the
player's in the square around barracks 1's UnitCreatePoint (1), its NaturalRallyPoint (10), within 80 of the
barracks (100).

Bench 11-05 (round 41; the clicks land at ~s8, so read against 帧数, not the clock; docs/engine/production.md):
  a CampProdA_mcp_1105_191414: 资金 2000 - ceil(500 k / 150) at 帧数 k (1946 at 16, 1516 at 145), 1500 from 153;
    the engineer counted at 帧数 160; 出口位 101 -> 110 -> 100 (out at UnitCreatePoint, walks past the rally square).
  b CampProdB_mcp_1105_192504: 资金 stops at 3 (帧数 133), 2000 come 4 s later, the engineer at 221.
  c CampProdC_mcp_1105_192728: ~1 a frame (1866 at 132, 1507 at 488, 1500 at 496), the engineer at 505.
  d CampProdD_mcp_1105_193015: 1780 at 132, 1501 at 299, the engineer at 309.
Bench 11-08 (a script presses the button: NAMED_USE_COMMANDBUTTON_ABILITY(barracks 1, 'Command_ConstructAlliedEngineer')
at 2 s, no clicks; e / f, barracks 2 and 3 deleted as a):
  e CampProdE_mcp_1108_083724: 资金 2000 -> 1960 at s1, 1506 at 帧数 148, 1500 from 帧数 156 (a: 153; the watch
    samples twice a second); 帧数 stops at 160; 工程师 1 and 出口位 101 -> 100 -> 110 -> 100 at 帧数 160 (a: 160).
    Same curve as a: the scripted press is charged as it builds and takes the full build time (not free, not instant).
  f CampProdF_mcp_1108_083934: money 0 at the start; 30 s of 资金 0, 帧数 0 (the flag needs money below the start, so it
    never counts), 工程师 0, 出口位 0: the scripted press with no money builds nothing (refused, or waits at 0; no
    money was given later, so these two are not told apart).
Against the model (RA3-EngineModel production.py, round 41; tests/test_objects_bench.py, tools/objsidebyside.py with
orders): every pair and every 帧数 the same, once the model divides the seconds before x 15 (c: 495, not 500), keeps
the progress in float32 (10 s takes 151 updates; b owes 251 at k 75) and opens the door 10 frames (DoorOpeningTime
0.66 s). The walk to the rally point is not compared (motion).
"""
from maps import niagara
from parts import Mission, Script, Test, counted, square

ENGINEER, BARRACKS = 'AlliedEngineer', 'AlliedBarracks'
MONEY, SHORT, GIVE, BONUS = 2000, 250, 4.0, 2000     # b: GIVE s after the money reaches 0
RUN = {'a': 22.0, 'b': 30.0, 'c': 48.0, 'd': 34.0, 'e': 24.0, 'f': 30.0}
PRESS_AT, BUTTON_NAME = 2.0, 'Command_ConstructAlliedEngineer'   # e, f: a script presses the factory's button
FACTORY = (1550.0, 2560.0)              # niagara 'base factory'; the barracks turned 180 degrees (exit to the west)
CREATE, RALLY = (FACTORY[0], FACTORY[1] - 18.0), (FACTORY[0] - 40.0, FACTORY[1] - 18.0)   # (0, 18), (40, 18) turned
DELETE = {'a': ('Barracks 2', 'Barracks 3'), 'b': ('Barracks 2', 'Barracks 3'),
          'c': ('Yard', 'Power', 'Barracks 2', 'Barracks 3'), 'd': ('Power',), 'e': ('Barracks 2', 'Barracks 3'), 'f': ('Barracks 2', 'Barracks 3')}
# the sidebar's infantry tab and the engineer's button, screen pixels (1280 x 720): bench 11-05, round 41
TAB, BUTTON = (1174.0, 251.0), (1135.0, 367.0)


def _n(part):
    return f'UNIT - CNV Prod {part}'


def mission():
    m = Mission(name='CampProd', map=niagara, units=[], facts={})
    m.spawns |= {ENGINEER}
    m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
    m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power', name=_n('Power'))
    for k, dy in enumerate((0.0, 140.0, 280.0)):
        m.put(BARRACKS, 'base factory', 0.0, dy, angle=3.1416, role=f'barracks {k + 1}', name=_n(f'Barracks {k + 1}'))
    return m


def production_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    t.areas['Test Create'] = square(*CREATE, 10.0)
    t.areas['Test Rally'] = square(*RALLY, 10.0)
    t.areas['Test Near'] = square(*FACTORY, 80.0)
    start = SHORT if which == 'b' else 0 if which == 'f' else MONEY
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, start)] + [
        ('NAMED_DELETE', _n(p)) for p in DELETE[which]]))
    t.counters.append(('CNV_Prod_Money', '资金'))
    if which == 'b':                        # by events: the clicks' mission second is not known (bench 11-05: ~s8)
        # (op 1, meant as <=, held at 250 <= 0 -- bench 11-05; op 0 '<' as 'paying' reads right)
        t.scripts += [Script('Test - broke', [('FLAG', 'Test Paying', 1), ('COUNTER', 'CNV_Prod_Money', 0, 5)],
                             [('SET_MILLISECOND_TIMER', 'Test Give', GIVE), ('SET_FLAG', 'Test Broke', 1)]),
                      # a timer never set reads expired (bench 11-05: the bonus came at the start)
                      Script('Test - give', [('FLAG', 'Test Broke', 1), ('TIMER_EXPIRED', 'Test Give')],
                             [('PLAYER_GIVE_MONEY', p1, BONUS)])]
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Prod_Money')], once=False))
    t.scripts.append(Script('Test - paying', [('COUNTER', 'CNV_Prod_Money', 0, start)], [('SET_FLAG', 'Test Paying', 1)]))
    t.counters.append(('CNV_Prod_Frames', '帧数'))
    counted('CNV_Prod_Made', '工程师', t, template=ENGINEER, most=3)
    t.scripts.append(Script('Test - frames', [('FLAG', 'Test Paying', 1), ('COUNTER', 'CNV_Prod_Made', 2, 0)],
                            [('INCREMENT_COUNTER', 1, 'CNV_Prod_Frames')], once=False))
    t.counters.append(('CNV_Prod_Exit', '出口位'))
    t.scripts.append(Script('Test - exit zero', [], [('SET_COUNTER', 'CNV_Prod_Exit', 0)], once=False))
    t.scripts += [Script(f'Test - exit {a}', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', 3, 1,
                                                ENGINEER, f'Test {a}')],
                         [('INCREMENT_COUNTER', step, 'CNV_Prod_Exit')], once=False)
                  for a, step in (('Create', 1), ('Rally', 10), ('Near', 100))]
    if which in 'ef':                       # no clicks: a script presses barracks 1's engineer button
        t.scripts += [Script('Test - press set', [], [('SET_MILLISECOND_TIMER', 'Test Press', PRESS_AT)]),
                      Script('Test - press', [('TIMER_EXPIRED', 'Test Press')],
                             [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('Barracks 1'), BUTTON_NAME)])]
    t.expect = [('工程师', 0, 'ever>=', 1, RUN[which])] if which != 'f' else []
    watch = dict(every=0.5, sheet=False, lines=len(t.counters))
    if which in 'ef':
        t.bench = [('bench_watch', dict(watch, seconds=RUN[which]))]
    elif TAB[0] is None:                     # the buttons not found yet: run, look by hand (keep=true)
        t.bench = [('bench_watch', dict(watch, seconds=2.0))]
    else:
        t.bench = [('bench_watch', dict(watch, seconds=2.0)),
                   ('bench_click', dict(x=TAB[0], y=TAB[1], world=False, look=False)),
                   ('bench_click', dict(x=BUTTON[0], y=BUTTON[1], world=False, look=False)),
                   ('bench_watch', dict(watch, seconds=RUN[which]))]
    return t


MISSION = {'engine_production': mission}
CHECKS = {'engine_production': {w: (lambda m, w=w: production_test(m, w)) for w in 'abcdef'}}
