"""Engine unit test: the player placing a structure (ADR 0019 layer 2; docs/engine/construction.md) -- the Allied way
(build it full in the queue, it waits there until placed, then it unpacks) and the Soviet way (BuildTime 0: place it
first, it unpacks while the money is paid as it goes, and stops while the money is short).

On the Niagara map the player's Allied construction yard at the base yard and a Soviet construction yard at the base
factory; each variant deletes the other at the start. The player orders a power plant by clicking the sidebar's
structure tab and the plant's button and places it by clicking the map at the build spot (no script action places
a player's structure):

  a  allied   AlliedPowerPlant (BuildTime 10, 800, UnpackTime 3 s): the clicks, then WAIT s later the place click
  b  soviet   SovietPowerPlant (BuildTime 0, 800, UnpackTime 10 s): the clicks and the place click at once
  c  broke    as b with money SHORT; GIVE s after the money falls below 5, BONUS more

Counters (four lines):
  资金    the player's money
  付款帧  frames while the money is below the start and above the start less the plant's cost (paying)
  状态帧  1 x frames the player owns an object UNDER_CONSTRUCTION + 1000 x frames one is UNPACKING
  电厂    how many power plants the player owns

Bench 11-05 (round 46; docs/engine/construction.md 3b). cnv_check's own steps never place: the bench holds the game
in its Esc menu between calls and the place click does not take (four tries). By hand: bench_start(mod, hold=false),
bench_click the tab and the button (world=false), (a: bench_watch until 付款帧 149), the button again for a, then
bench_click the map (a at (1100, 2600), b / c at (1300, 2750), near each yard), bench_watch lines=4. Read by 状态帧:
  a CampPlaceA_mcp_1105_222532: 1200 / 149 from s13.7, no plant until the place click; 状态帧 7000 .. 45000, 电厂 1 at
    once (UNPACKING only, never UNDER_CONSTRUCTION).
  b CampPlaceB_mcp_1105_222645: 2000 until placed; (状态帧, 资金) 6000 1973, 21000 1893, 144000 1237, 150000 1200.
  c CampPlaceC_mcp_1105_223014: 7000 268, 67000 1 .. 113000 1 (stopped, still UNPACKING), the 2000 4 s later, 210000
    1500.
Against the model (RA3-EngineModel production.place, tests/test_objects_bench.py placing): every pair the same.
"""
from maps import niagara
from parts import Mission, Script, Test, counted, status

ALLIED, SOVIET = 'AlliedPowerPlant', 'SovietPowerPlant'
COST, MONEY, SHORT, GIVE, BONUS = 800, 2000, 300, 4.0, 2000
RUN = {'a': 22.0, 'b': 16.0, 'c': 24.0}
WAIT = 13.0                             # a: the place click this long after the button (the plant is full by then)
BUILD = ('west field', -120.0, 260.0)   # the place click (1060, 2635), as engine_build's script spot
# the sidebar's structure tab and the power plant's button per yard, screen pixels (1280 x 720); None: not found yet
TAB = {'a': (1120, 252), 'b': (1120, 252), 'c': (1120, 252)}
BUTTON = {'a': (1137, 323), 'b': (1137, 323), 'c': (1137, 323)}   # first button of the structure page, both yards


def _n(part):
    return f'UNIT - CNV Place {part}'


def mission():
    m = Mission(name='CampPlace', map=niagara, units=[], facts={})
    m.spawns |= {ALLIED, SOVIET}
    m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='allied yard', name=_n('Allied Yard'))
    m.put('SovietConstructionYard', 'base factory', angle=3.1416, role='soviet yard', name=_n('Soviet Yard'))
    m.waypoint('build spot', 'Test Place Spot', *BUILD)
    return m


def place_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    plant = ALLIED if which == 'a' else SOVIET
    start = SHORT if which == 'c' else MONEY
    gone = _n('Soviet Yard') if which == 'a' else _n('Allied Yard')
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, start),
                                                 ('NAMED_DELETE', gone)]))
    t.counters.append(('CNV_Place_Money', '资金'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Place_Money')], once=False))
    t.counters.append(('CNV_Place_Paying', '付款帧'))
    end = max(start - COST, 0)
    t.scripts.append(Script('Test - paying', [('COUNTER', 'CNV_Place_Money', 0, start),
                                              ('COUNTER', 'CNV_Place_Money', 3, end + 1)],
                            [('INCREMENT_COUNTER', 1, 'CNV_Place_Paying')], once=False))
    if which == 'c':
        # (paying while broke counts too: the money is below the start and >= 1 only until it hits 0)
        t.scripts += [Script('Test - broke', [('COUNTER', 'CNV_Place_Money', 0, 5)],
                             [('SET_MILLISECOND_TIMER', 'Test Give', GIVE), ('SET_FLAG', 'Test Broke', 1)]),
                      Script('Test - give', [('FLAG', 'Test Broke', 1), ('TIMER_EXPIRED', 'Test Give')],
                             [('PLAYER_GIVE_MONEY', p1, BONUS)])]
    t.counters.append(('CNV_Place_Status', '状态帧'))
    t.scripts += [Script(f'Test - status {st}', [('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', p1, 3, 1,
                                                  status(st))],
                         [('INCREMENT_COUNTER', step, 'CNV_Place_Status')], once=False)
                  for st, step in (('UNDER_CONSTRUCTION', 1), ('UNPACKING', 1000))]
    counted('CNV_Place_Plants', '电厂', t, template=plant, most=3)
    t.expect = [('电厂', 0, 'ever>=', 1, RUN[which])]
    watch = dict(every=0.5, sheet=False, lines=len(t.counters))
    x, y = m.waypoints['Test Place Spot']
    if TAB[which] is None:                  # the buttons not found yet: run, look by hand (keep=true)
        t.bench = [('bench_watch', dict(watch, seconds=2.0))]
        return t
    tab = ('bench_click', dict(x=TAB[which][0], y=TAB[which][1], world=False, look=False))
    # (the first click after the camera move did not take on the bench: the tab is clicked twice, harmless)
    clicks = [tab, tab, ('bench_click', dict(x=BUTTON[which][0], y=BUTTON[which][1], world=False, look=False))]
    put = [('bench_camera', dict(x=x, y=y, look=False)), ('bench_click', dict(x=x, y=y, look=False))]
    if which == 'a':
        # the plant is full and waiting in the queue: the button (ready) starts the placing, then the map click
        t.bench = ([('bench_watch', dict(watch, seconds=2.0))] + clicks + [('bench_watch', dict(watch, seconds=WAIT))]
                   + [put[0], clicks[2],('bench_watch', dict(watch, seconds=0.5)), put[1]] + [('bench_watch', dict(watch, seconds=RUN[which] - WAIT))])
    else:
        t.bench = ([('bench_watch', dict(watch, seconds=2.0)), put[0]] + clicks + put[1:]
                   + [('bench_watch', dict(watch, seconds=RUN[which]))])
    return t


MISSION = {'engine_place': mission}
CHECKS = {'engine_place': {w: (lambda m, w=w: place_test(m, w)) for w in 'abc'}}
