"""A4 tests (docs/story/plans/a4.md on maps/sapporo.py): one small scene each for what the horn device
(devices/horn.py, named 雪祭 in the plan) does. Everything is asked of the mission (its sites, cast, marks, flags); the
helpers the frozen before-rework build's checks keep (checks/a4_before.py) are theirs.

All of them play the plan as it is on normal difficulty (the first horn 35 s after the countdown starts: the plan's rule
starts it when the opening scene is over, 14 s in), the trucks kept at full health and the whole map revealed, no
ending (the troops would take them), and count what the horn made by name (`tally`: how many of a wave stand).

horn: the first horn on the streets: the lane and plaza 1 send their waves (4 each), plaza 2 sends none yet; the
  second horn: plaza 2 as well.
detour: engineer 1, brought to plaza 1's street, ices it just before the first horn: the lane's wave is made at once,
  plaza 1's later and at the lane's foot (its wave detours, 10 s late).
queue: the mouths' horns started by the test (the plan starts them after the harbour turns), engineer 1 at the north
  mouth icing it before the first one: the other mouths' waves are made, the north mouth's is kept, and made when the
  ice has melted.
smash: the same, the Ghost King's horn the next one (the counter set to 2): a transport comes over the sea, the Ghost
  King lands, and the ice wall the engineer built at the east mouth loses health with nothing else telling it to.
derrick: an engineer takes the oil derrick (docs/design/flow/mechanics.md 工程师占油井).
"""
from checks.a4_before import freeze, ice_wall, keep_up, start
from parts import Obj, Script, Test, counted, square

TAG = 'A4'
OPENING = 1.0                                   # the bench skips the opening scene: the street horns start at once
                                                # (bench 2026-10-31: the first horn between s33 and s37, normal)
GAP1 = 35.0                                     # normal: the countdown's first time
HORN1 = OPENING + GAP1                          # the first horn on the streets
MOUTHS_AT = 16.0                                # queue, smash: the mouths' horns started (after the plan's rule)
MOUTH1 = MOUTHS_AT + GAP1                       # ... their first
BUILD = 17.0                                    # the ice order given this long before the horn (walk 0, build ~9 s)
LEAD = 4.0                                      # the mission runs ~3 s ahead of the bench's clock


def flag(kind, mode):
    return f'CNV_{TAG}_Horn_{mode}_{kind}'


def wave(m, mode, n, wid):
    """The names the horn device makes for horn n of way `wid` (found in its scripts, as the plan's own)."""
    head = f'UNIT - CNV {TAG} H{mode}{n} {wid} '
    out = sorted({a[1] for s in m.scripts for a in s.do if a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT'
                  and a[1].startswith(head)})
    assert out, f'the mission makes nothing named {head!r}'
    return out


def tally(t, names, counter, label, area=None):
    """A counter of how many of `names` stand (in `area`, when given): zero every frame, one more for each."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    cond = (lambda n: [('NAMED_INSIDE_AREA', n, area)]) if area else (lambda n: [('NAMED_NOT_DESTROYED', n)])
    t.scripts += [Script(f'Test - {counter} {k}', cond(n), [('INCREMENT_COUNTER', 1, counter)], once=False)
                  for k, n in enumerate(names)]


def scene(m):
    """The test every check starts with: no ending, the map revealed, the trucks kept up, the whole map playable."""
    m.drop_endings()
    t = Test()
    start(t, m)
    keep_up(t, m)
    t.scripts += [Script('Test - whole map', [], [('MAP_SWITCH_BORDER', 0)]),
                  # the convoy parked for good (the plan's 停下 flag, set every frame): at the halt the plan goes on to
                  # 港口生变, whose scene stops the horns (the trucks cross the festival in ~60 s, the horns need minutes)
                  Script('Test - hold the convoy', [], [('SET_FLAG', f'CNV_{TAG}_Halted', 1)], once=False)]
    # the counters are read off the screen against a dark ground (testbench/counters.py): the camera goes, once the
    # opening scene is over, to the map's west edge, where the bottom left is the void beyond it (bench 2026-10-31:
    # on the start view a house stood there and every counter read None)
    t.waypoints['Test Camera'] = (0.0, m.site('start')[1])
    t.scripts += [Script('Test - camera set', [], [('SET_MILLISECOND_TIMER', 'Test - camera', OPENING + 1.0)]),
                  Script('Test - camera', [('TIMER_EXPIRED', 'Test - camera')],
                         [('MOVE_CAMERA_TO', 'Test Camera', 0.5, 0.0, 1.0, 1.0)])]
    return t


def stand(t, m, part, at, label):
    """Engineer `part` taken to `at` (x, y) at once, out of harm's way, so the ice is ordered from there."""
    name = m.role(part).name
    t.waypoints[f'Test Stand {label}'] = at
    t.scripts.append(Script(f'Test - stand {label}', [], [('UNIT_TELEPORT_TO_WAYPOINT', name, f'Test Stand {label}'),
                                                          ('UNIT_CHANGE_OBJECT_STATUS', name, 'UNATTACKABLE', 1)]))


def ice_at(t, m, part, mark, when, label):
    """Engineer `part` freezes the way marked `mark` at `when` seconds."""
    timer = f'Test - ice timer {label}'
    t.scripts += [Script(f'Test - ice set {label}', [], [('SET_MILLISECOND_TIMER', timer, when)]),
                  Script(f'Test - ice {label}', [('TIMER_EXPIRED', timer)],
                         [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role(part).name, m.ability(part, 'freeze'),
                           m.mark(mark))])]


def mouths_on(t, m, counted_horns=0):
    """The mouths' horns started by the test at MOUTHS_AT, after `counted_horns` of them are counted (the plan's own
    start of the street horns is stopped from sounding: its On flag put down every frame)."""
    t.scripts += [Script('Test - streets off', [], [('SET_FLAG', flag('On', 'V'), 0)], once=False),
                  Script('Test - mouths timer', [], [('SET_MILLISECOND_TIMER', 'Test - mouths', MOUTHS_AT)]),
                  Script('Test - mouths on', [('TIMER_EXPIRED', 'Test - mouths')],
                         [('SET_COUNTER', f'CNV_{TAG}_Horn_L_N', counted_horns), ('SET_FLAG', flag('On', 'L'), 1),
                          ('SET_FLAG', flag('Start', 'L'), 1)])]


def horn(m):
    t = scene(m)
    first = wave(m, 'V', 1, 'V1') + wave(m, 'V', 1, 'V2')       # the third street has no wave in the first horn
    tally(t, first, 'Test Horn 1', '号角1的兵')
    tally(t, wave(m, 'V', 2, 'V3'), 'Test Plaza 2', '号角2街3的兵')
    t.expect += [('号角1的兵', 0, '==', 0, HORN1 - LEAD - 3),
                 ('号角1的兵', HORN1 + 5, 'ever>=', 8),              # two streets, four each: plaza 2 is not open yet
                 ('号角1的兵', 0, '<=', 8),
                 ('号角2街3的兵', 0, '==', 0, HORN1 + 20),
                 ('号角2街3的兵', HORN1 + 50 + 5, 'ever>=', 4)]
    t.bench = [('bench_watch', dict(seconds=HORN1 + 65, every=4, sheet=False, lines=len(t.counters)))]
    return t


def detour(m):
    t = scene(m)
    plaza1 = wave(m, 'V', 1, 'V2')
    lane = wave(m, 'V', 1, 'V1')
    foot = m.point('spawn V1')
    t.areas['Test Lane'] = square(foot[0], foot[1] + 60.0, 160.0)
    gx, gy = m.point('ice V2')
    stand(t, m, 'engineer 1', (gx, m.site('start')[1]), 'plaza 1')
    ice_at(t, m, 'engineer 1', 'ice V2', HORN1 - BUILD, 'plaza 1')
    counted('Test Walls', '冰墙', t, template=ice_wall(m).id)
    tally(t, lane, 'Test Lane Wave', '后巷的兵')
    tally(t, plaza1, 'Test Plaza 1 Wave', '1号街的兵')
    tally(t, plaza1, 'Test At Lane', '1号街兵在后巷口', area='Test Lane')
    t.expect += [('冰墙', HORN1 - 3, 'ever==', 1),
                 ('后巷的兵', HORN1 + 6, 'ever>=', 4),
                 ('1号街的兵', 0, '==', 0, HORN1 - LEAD + 2),         # the ice up: plaza 1's wave is not made there
                 ('1号街的兵', HORN1 + 8, 'ever>=', 4),                # but later (bench: s45, the escort kills them soon), ...
                 ('1号街兵在后巷口', HORN1 + 4, 'ever>=', 1)]        # ... at the lane's foot (bench: s45, 10 s late)
    t.bench = [('bench_watch', dict(seconds=HORN1 + 28, every=2, sheet=False, lines=len(t.counters)))]
    return t


def queue(m):
    t = scene(m)
    mouths_on(t, m)
    north, plaza3, east = (wave(m, 'L', 1, w) for w in ('L1', 'L2', 'L3'))
    mx, _ = m.point('ice L1')
    stand(t, m, 'engineer 1', (mx, m.site('start')[1]), 'north mouth')
    ice_at(t, m, 'engineer 1', 'ice L1', MOUTH1 - BUILD, 'north mouth')
    counted('Test Walls', '冰墙', t, template=ice_wall(m).id)
    tally(t, north, 'Test North', '北坡口的兵')
    tally(t, plaza3 + east, 'Test Others', '另两口的兵')
    life = ice_wall(m).params['lifetime']
    t.expect += [('冰墙', MOUTH1 - 3, 'ever==', 1),
                 ('另两口的兵', MOUTH1 + 6, 'ever>=', 8),               # open mouths: made at once, four each
                 # the ice stands s31-s59 (bench 2026-10-31), the horn at ~s48: kept in between, made at ~s61
                 ('北坡口的兵', 0, '==', 0, MOUTH1 - LEAD + 6),         # kept while the ice stands
                 ('北坡口的兵', MOUTH1 + 15, 'ever>=', 4)]              # made when it is gone
    t.bench = [('bench_watch', dict(seconds=MOUTH1 + life + 30, every=3, sheet=False, lines=len(t.counters)))]
    return t


GHOST_WAIT = 45.0                               # smash: the wall's health read for this long after the horn


def smash(m):
    t = scene(m)
    mouths_on(t, m, counted_horns=2)            # the next horn is the third: the Ghost King's
    horn3 = MOUTH1
    ex, _ = m.point('ice L3')
    stand(t, m, 'engineer 1', (ex, m.site('start')[1] + 60.0), 'east mouth')
    ice_at(t, m, 'engineer 1', 'ice L3', horn3 - 2.0, 'east mouth')
    t.counters += [(f'CNV_{TAG}_Walls', '冰墙'), (f'CNV_{TAG}_Kings', '鬼王上岸')]
    ref = f'UNITRef - CNV {TAG} Nearest Wall'
    counted('Test Ref Health', '目标墙血量', t, health=ref)
    t.expect += [('冰墙', horn3 + 8, 'ever==', 1), ('鬼王上岸', horn3 + 5, 'ever>=', 1),
                 ('目标墙血量', horn3 + 8, 'ever<', 100)]            # nobody ordered it: the Ghost King smashes it
    t.bench = [('bench_watch', dict(seconds=horn3 + GHOST_WAIT + 10, every=3, sheet=False, lines=len(t.counters)))]
    return t


DERRICK_RUN = 45.0


def derrick(m):
    """The new draft's resource point (docs/design/flow/a4.md 摆放要求: an engineer takes the oil derrick at the south
    ramp's foot; mechanics.md 工程师占油井, to be tested): a neutral derrick by the start, an engineer of the player's
    ordered at 2 s to capture it (the engineer's own button, retail's NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED):
    the derrick turns the player's, and the player's money (0 in A4) goes up. Bench 2026-10-29
    (CampA4Derrick_mcp_1029_202131): the player's from the first reading, 605 then, ~10 a second on (950 at s46)."""
    t = Test()
    start(t, m)
    # both on the avenue (bench 2026-10-29: an engineer 150 north of the start stood on the cliff above the road and
    # never moved)
    t.objects += [Obj('OilDerrick', *m.site('start', 330, 80), side='neutral', name='UNIT - Test Derrick',
                      site='start'),
                  Obj('AlliedEngineer', *m.site('start', 200, 0), name='UNIT - Test Engineer', site='start')]
    t.scripts += [Script('Test - capture timer', [], [('SET_MILLISECOND_TIMER', 'Test Capture', 2.0)]),
                  Script('Test - capture', [('TIMER_EXPIRED', 'Test Capture')],
                         [('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', 'UNIT - Test Engineer',
                           'Command_CaptureBuilding', 'UNIT - Test Derrick')]),
                  Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', m.player('p1'), 'Test Money')],
                         once=False)]
    counted('Test Derrick Ours', '油井归我', t, owner='UNIT - Test Derrick', player=m.player('p1'))
    t.counters.append(('Test Money', '资金'))
    t.expect += [('油井归我', DERRICK_RUN - 10, 'ever==', 1),
                 ('资金', DERRICK_RUN - 10, 'ever>', 0)]
    t.bench = [('bench_watch', dict(seconds=DERRICK_RUN, every=3, sheet=False, lines=len(t.counters)))]
    return t
