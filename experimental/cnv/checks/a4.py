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

The walk-throughs (the convoy crawls at 12: the festival takes ~4 minutes, the last leg ~3, so they run long):
idle: the player does nothing: the convoy rolls on its own, the horn waves take it, the mission is lost.
hold: the trucks kept whole and nothing else: five horns sound on the festival's streets before the convoy halts at
  plaza 2's gate, and the plan goes on to the harbour scene (its second phase).
win: the trucks kept whole and the north command razed the moment the north camp phase begins: the mission goes
  through every phase and is won with the trucks at the harbour.
demo: the opening scene's demonstration: an engineer ices plaza 1's street, the pair of troops behind it turn back,
  a pair is made at the lane's foot.
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


def scene(m, park=True, endings=False, trucks_up=True, long_run=False):
    """The test every check starts with: no ending (`endings`: the plan's own), the map revealed, the trucks kept up
    (`trucks_up`), the whole map playable, the convoy parked for good (`park`: the plan's own 停下 flag, set every
    frame; at the halt the plan goes on to 港口生变, whose scene stops the horns). `long_run`: the camera is sent back
    to the dark ground every two seconds (the plan's scenes move it away, and the counters are read off that ground)."""
    if not endings:
        m.drop_endings()
    t = Test()
    start(t, m)
    if trucks_up:
        keep_up(t, m)
    t.scripts.append(Script('Test - whole map', [], [('MAP_SWITCH_BORDER', 0)]))
    if park:
        t.scripts.append(Script('Test - hold the convoy', [], [('SET_FLAG', f'CNV_{TAG}_Halted', 1)], once=False))
    # the counters are read off the screen against a dark ground (testbench/counters.py): the camera goes, once the
    # opening scene is over, to the map's west edge, where the bottom left is the void beyond it (bench 2026-10-31:
    # on the start view a house stood there and every counter read None)
    t.waypoints['Test Camera'] = (0.0, m.site('start')[1])
    t.scripts += [Script('Test - camera set', [], [('SET_MILLISECOND_TIMER', 'Test - camera', OPENING + 1.0)]),
                  Script('Test - camera', [('TIMER_EXPIRED', 'Test - camera')],
                         [('MOVE_CAMERA_TO', 'Test Camera', 0.5, 0.0, 1.0, 1.0)] +
                         ([('SET_MILLISECOND_TIMER', 'Test - camera', 2.0)] if long_run else []), once=not long_run)]
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
    stand(t, m, 'engineer', (gx, m.site('start')[1]), 'plaza 1')
    ice_at(t, m, 'engineer', 'ice V2', HORN1 - BUILD, 'plaza 1')
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
    stand(t, m, 'engineer', (mx, m.site('start')[1]), 'north mouth')
    ice_at(t, m, 'engineer', 'ice L1', MOUTH1 - BUILD, 'north mouth')
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
    stand(t, m, 'engineer', (ex, m.site('start')[1] + 60.0), 'east mouth')
    ice_at(t, m, 'engineer', 'ice L3', horn3 - 2.0, 'east mouth')
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


DEMO_RUN = 45.0                                 # demo: the scene's demonstration starts at its 12th second


def made_names(m, part):
    """The names the plan's scripts create that hold `part` (the demonstration's pairs: ' Demo Foe ', ' Demo Out ')."""
    return sorted({a[1] for s in m.scripts for a in s.do if a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT' and part in a[1]})


def demo(m):
    """The opening scene's demonstration (the bench plays the scene's timed steps, only the camera is its own): the
    engineer ices plaza 1's street, the pair behind the ice is made and turned back, a pair is made at the lane."""
    t = scene(m)
    foes, outs = made_names(m, ' Demo Foe '), made_names(m, ' Demo Out ')
    assert foes and outs, 'the plan has no 演示'
    counted('Test Walls', '冰墙', t, template=ice_wall(m).id)
    tally(t, foes, 'Test Demo Foes', '演示的兵')
    tally(t, outs, 'Test Demo Outs', '绕路出的兵')
    # what the demonstration is doing, in one number: 1 started, 10 the street's ice stands, 100 the scene took it away
    t.counters.append(('Test Demo State', '演示状态'))
    t.scripts.append(Script('Test - state zero', [], [('SET_COUNTER', 'Test Demo State', 0)], once=False))
    t.scripts += [Script(f'Test - state {k}', [('FLAG', f, 1)], [('INCREMENT_COUNTER', k, 'Test Demo State')], once=False)
                  for f, k in ((f'CNV_{TAG}_Demo_Started', 1), (f'CNV_{TAG}_Frozen_V2', 10), (f'CNV_{TAG}_Demo_Off', 100))]
    t.expect += [('冰墙', 5, 'ever>=', 1), ('演示的兵', 5, 'ever>=', len(foes)), ('绕路出的兵', 5, 'ever>=', len(outs))]
    t.bench = [('bench_watch', dict(seconds=DEMO_RUN, every=2, sheet=False, lines=len(t.counters)))]
    return t


def phase(m, k):
    """The flag that is 1 once the plan's phase k begins."""
    return next(a[1] for s in m.scripts for a in s.do if a[0] == 'SET_FLAG' and a[1].endswith(f'_Phase_{k}'))


def mark_phase(t, m, k, counter, label):
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter}', [('FLAG', phase(m, k), 1)], [('SET_COUNTER', counter, 1)],
                            once=False))


FESTIVAL = 250.0                                # the convoy leaves ~16 s in and crawls ~227 s to the halt
HARBOUR_SCENE = 40.0                            # the harbour scene's length, with a margin
LAST_LEG = 420.0                                # win: after the harbour scene: the build-up (to 90 s), the three trucks
                                                # 0/50/110 s apart, ~77 s each at 12


def idle(m):
    """The player does nothing: the convoy rolls on its own (nobody walks out to it), the horn waves take two trucks
    and the mission ends in the festival -- a defence level must not win itself."""
    t = scene(m, park=False, endings=True, trucks_up=False, long_run=True)
    for j in (1, 2):
        counted(f'Test Truck {j}', f'{j}号车血量', t, health=m.role(f'truck {j}').name)
    t.expect += [('ENDED', 60, '', None, FESTIVAL)]
    t.bench = [('bench_watch', dict(seconds=FESTIVAL, every=3, sheet=False, lines=len(t.counters)))]
    return t


def hold(m):
    """The trucks kept whole, nobody else doing anything: five horns sound on the streets before the convoy halts, the
    first truck gets to plaza 2's gate, and the plan goes on to the harbour scene (its second phase)."""
    t = scene(m, park=False, long_run=True)
    t.counters.append((f'CNV_{TAG}_Horn_V_N', '街的号角声数'))
    t.areas['Test Halt'] = square(*m.site('halt'), 80.0)
    counted('Test At Halt', '车到停车点', t, named=m.role('truck 1').name, area='Test Halt')
    mark_phase(t, m, 2, 'Test Phase 2', '港口生变')
    t.expect += [('街的号角声数', 0, '<=', 5), ('街的号角声数', FESTIVAL, 'ever>=', 5),
                 ('车到停车点', FESTIVAL + 30, 'ever>=', 1), ('港口生变', FESTIVAL + 60, 'ever>=', 1)]
    t.bench = [('bench_watch', dict(seconds=FESTIVAL + 70, every=4, sheet=False, lines=len(t.counters)))]
    return t


def win(m):
    """The whole mission with the trucks kept whole: the north command razed when the north camp phase (the third)
    begins, the build-up counts down, the last leg runs, and the trucks reach the harbour: the mission is won."""
    t = scene(m, park=False, endings=True, long_run=True)
    t.counters.append((f'CNV_{TAG}_Arrived', '到港口车数'))
    mark_phase(t, m, 3, 'Test Phase 3', '北营')
    t.scripts.append(Script('Test - raze the north command', [('FLAG', phase(m, 3), 1)],
                            [('NAMED_KILL', m.role('north command').name)]))
    end = FESTIVAL + HARBOUR_SCENE + LAST_LEG
    t.expect += [('到港口车数', 0, 'ever>=', 2), ('ENDED', FESTIVAL + HARBOUR_SCENE + 120, '', None, end)]
    t.bench = [('bench_watch', dict(seconds=end + 20, every=5, sheet=False, lines=len(t.counters)))]
    return t
