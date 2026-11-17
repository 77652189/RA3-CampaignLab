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
Bench 11-09 (g: the engineer banned at the start, ALLOW_DISALLOW_ONE_BUILDING(p1, 'alliedengineer', 0); presses at
2 / 8 / 19 s, let go at 6 s, banned at 21 s, let go at 30 s; the watch's s runs ~1.3 s behind the timers):
  g CampProdG_mcp_1109_055742: 2000 to s4, paying from s5 (the 2 s press queued and waited for the let-go), the
    first engineer at 帧数 160 (as a); the second job 1500 -> 1286 by s20, 1286 from s20 to s28 (banned halfway: it
    stands, nothing refunded or cancelled), paying again from s29, the second engineer at s35; the third 1000 -> 500
    by s45. A ban stops the building, not the queueing (docs/engine/production.md section 4).
Bench 11-11 (round 158, h: where the engineer stops -- strips 35-45 / 45-55 / 55-65 / 65-80 west of the barracks):
  h CampProdH_mcp_1111_034429 (PASS): 帧数 160 out (as a); 出口位 0 -> 10 -> 1100 -> 1000 from s13 to s25: it walks
    past the natural rally point (40) and stops 65-80 west, 25-40 beyond it; never sampled in 35-45 (2 Hz watch).
    The simulator stops at 40 (reads 1): not yet fixed (round 159; the extra distance not pinned, INFERRED).
  i CampProdI_mcp_1111_041259 (PASS, round 159; boxes BOXES_I in the barracks' frame): 出口位 1000010 at s13
    (x 60-65, y 24-36: on its way), 1010000 from s13 to s28 (x 75-90, y 24-36). With h (x 65-80, y 3-33) it stops
    about (75-80, 24-33): on the line from the barracks' centre through (40, 18), not on the door line (y 18).
Against the model (RA3-EngineModel production.py, round 41; tests/test_objects_bench.py, tools/objsidebyside.py with
orders): every pair and every 帧数 the same, once the model divides the seconds before x 15 (c: 495, not 500), keeps
the progress in float32 (10 s takes 151 updates; b owes 251 at k 75) and opens the door 10 frames (DoorOpeningTime
0.66 s). The walk to the rally point is not compared (motion).
"""
import resources
from maps import niagara
from parts import Mission, Script, Test, counted, square

ENGINEER, BARRACKS = 'AlliedEngineer', 'AlliedBarracks'
MONEY, SHORT, GIVE, BONUS = 2000, 250, 4.0, 2000     # b: GIVE s after the money reaches 0
RUN = {'a': 22.0, 'b': 30.0, 'c': 48.0, 'd': 34.0, 'e': 24.0, 'f': 30.0, 'g': 44.0, 'h': 24.0, 'i': 24.0}
PRESS_AT, BUTTON_NAME = 2.0, 'Command_ConstructAlliedEngineer'   # e, f: a script presses the factory's button
FACTORY = (1550.0, 2560.0)              # niagara 'base factory'; the barracks turned 180 degrees (exit to the west)
CREATE, RALLY = (FACTORY[0], FACTORY[1] - 18.0), (FACTORY[0] - 40.0, FACTORY[1] - 18.0)   # (0, 18), (40, 18) turned
DELETE = {'a': ('Barracks 2', 'Barracks 3'), 'b': ('Barracks 2', 'Barracks 3'),
          'c': ('Yard', 'Power', 'Barracks 2', 'Barracks 3'), 'd': ('Power',), 'e': ('Barracks 2', 'Barracks 3'), 'f': ('Barracks 2', 'Barracks 3'),
          'g': ('Barracks 2', 'Barracks 3'), 'h': ('Barracks 2', 'Barracks 3'), 'i': ('Barracks 2', 'Barracks 3')}
# h: where the engineer stops -- strips across the exit line, (from, to) map units west of the barracks, y within 15
# of the exit line; 出口位 adds the step of each strip it stands in
STRIPS_H = (('Rally', 35.0, 45.0, 1), ('Past10', 45.0, 55.0, 10), ('Past20', 55.0, 65.0, 100), ('Far', 65.0, 80.0, 1000))
# i: where exactly -- (name, (x from, x to, y from, y to) in the barracks' frame (x = out of the door, y = sideways,
# the exit line at 18), step): five x strips 55-90 over y -5..50, three y strips 5-50 over x 50-95. Along the door
# line pushed out puts it at y 18 (the y 5-24 box); along the centre-to-rally line (40, 18) out to x 65-75 puts it
# at y 29-33 (24-36)
BOXES_I = (('X55', (55.0, 60.0, -5.0, 50.0), 1), ('X60', (60.0, 65.0, -5.0, 50.0), 10),
           ('X65', (65.0, 70.0, -5.0, 50.0), 100), ('X70', (70.0, 75.0, -5.0, 50.0), 1000),
           ('X75', (75.0, 90.0, -5.0, 50.0), 10000), ('Y5', (50.0, 95.0, 5.0, 24.0), 100000),
           ('Y24', (50.0, 95.0, 24.0, 36.0), 1000000), ('Y36', (50.0, 95.0, 36.0, 50.0), 10000000))
# g: ALLOW_DISALLOW_ONE_BUILDING(p1, 'alliedengineer', allow) at the start (0) and these seconds; presses at PRESS_G
BAN_G = ((6.0, 1), (21.0, 0), (30.0, 1))
PRESS_G = (2.0, 8.0, 19.0)
# the sidebar's infantry tab and the engineer's button, screen pixels (1280 x 720): bench 11-05, round 41
TAB, BUTTON = (1174.0, 251.0), (1135.0, 367.0)


def _n(part):
    return f'UNIT - CNV Prod {part}'


def mission():
    m = Mission(name='CampProd', map=resources.measured(niagara), units=[], facts={})
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
    exits = (('Create', 1), ('Rally', 10), ('Near', 100))
    if which == 'h':
        exits = []
        for name, a, b, step in STRIPS_H:
            x0, x1, y = FACTORY[0] - b, FACTORY[0] - a, CREATE[1]
            t.areas[f'Test {name}'] = [(x0, y - 15.0), (x1, y - 15.0), (x1, y + 15.0), (x0, y + 15.0)]
            exits.append((name, step))
    if which == 'i':                        # boxes in the barracks' own frame (x out of the door, y sideways)
        exits = []
        for name, (xa, xb, ya, yb), step in BOXES_I:
            x0, x1, y0, y1 = FACTORY[0] - xb, FACTORY[0] - xa, FACTORY[1] - yb, FACTORY[1] - ya
            t.areas[f'Test {name}'] = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            exits.append((name, step))
    start = SHORT if which == 'b' else 0 if which == 'f' else MONEY
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, start)] + [
        ('NAMED_DELETE', _n(p)) for p in DELETE[which]] + (
        [('ALLOW_DISALLOW_ONE_BUILDING', p1, ENGINEER.lower(), 0)] if which == 'g' else [])))
    t.counters.append(('CNV_Prod_Money', '资金'))
    if which == 'b':                        # by events: the clicks' mission second is not known (bench 11-05: ~s8)
        # (op 1, meant as <=, held at 250 <= 0 -- bench 11-05; op 0 '<' as 'paying' reads right)
        t.scripts += [Script('Test - broke', [('FLAG', 'Test Paying', 1), ('COUNTER', 'CNV_Prod_Money', 0, 5)],
                             [('SET_MILLISECOND_TIMER', 'Test Give', GIVE), ('SET_FLAG', 'Test Broke', 1)]),
                      # gated by the flag too (11-05 the bonus came at the start; not an unset timer, which reads
                      # not expired: probe align / unset 11-13, docs/engine/production.md 5)
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
                  for a, step in exits]
    if which in 'efhi':                       # no clicks: a script presses barracks 1's engineer button
        t.scripts += [Script('Test - press set', [], [('SET_MILLISECOND_TIMER', 'Test Press', PRESS_AT)]),
                      Script('Test - press', [('TIMER_EXPIRED', 'Test Press')],
                             [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('Barracks 1'), BUTTON_NAME)])]
    if which == 'g':                        # a ban, a press while banned, a let go, a ban halfway through a build
        t.scripts.append(Script('Test - g set', [], [('SET_MILLISECOND_TIMER', f'Test Press {k}', s)
                                                     for k, s in enumerate(PRESS_G)] +
                                [('SET_MILLISECOND_TIMER', f'Test Ban {k}', s) for k, (s, _) in enumerate(BAN_G)]))
        t.scripts += [Script(f'Test - press {k}', [('TIMER_EXPIRED', f'Test Press {k}')],
                             [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('Barracks 1'), BUTTON_NAME)])
                      for k in range(len(PRESS_G))]
        t.scripts += [Script(f'Test - ban {k}', [('TIMER_EXPIRED', f'Test Ban {k}')],
                             [('ALLOW_DISALLOW_ONE_BUILDING', p1, ENGINEER.lower(), allow)])
                      for k, (_, allow) in enumerate(BAN_G)]
    t.expect = [('工程师', 0, 'ever>=', 1, RUN[which])] if which != 'f' else []
    watch = dict(every=0.5, sheet=False, lines=len(t.counters))
    if which in 'efghi':
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
CHECKS = {'engine_production': {w: (lambda m, w=w: production_test(m, w)) for w in 'abcdefghi'}}
