"""A4 tests; everything asked of the mission (its sites, cast, marks, facts) and the wall's published lifetime.

seal (A against B on one map): engineer 1 freezes a wall across plaza 1's gate shortly before the convoy leaves,
  plaza 2's gate stays open. The convoy breaks both plazas' sculptures on its way; plaza 2's tank buster is out on
  the road within seconds, plaza 1's stays off it while the wall stands and comes out after it melts.
placed: the control for seal's rule -- a map-placed bar holds the gate as well (plaza 3 broken by test script:
  held by plaza 1's troops, the convoy never gets there).
smash: the player breaks sculpture 3-1 early (by test script, long before the convoy): its tank buster stands in
  plaza 3 at once, while sculpture 3-2 is whole (plaza 2's can not be broken: 广场 2 无敌).
tough: plaza 2 (无敌, 补兵): the player's tanks do not hurt its sculptures; the convoy held there stays held while
  its troops are killed again and again -- they come back --, and goes on once engineer 2 ices its gate.
ambush: the convoy, as played, breaks plaza 1's sculptures as it passes the approach: the troops appear.
stop: 遇伏 停下 -- the convoy reaches plaza 1, its troops out and the gate open: it stands there; the troops killed
  (by test script, 30 s after leaving), it goes on past plaza 2's approach.
early: the player ices plaza 1's gate first (engineer 1, 30 s in): the convoy leaves 10 s after, before its time.
north: played the quick way (win's), the harbour turns: the north camp's skirmish AI, asleep and broke till then,
  wakes 30 s after with the camp's buildings and guards, spends its money and its troops come down the plateau.
win: the trucks kept at full health, plaza 1's and 3's troops killed as soon as they hold the convoy, engineer 2
  icing plaza 2's gate 5 s after it leaves: it reaches the exit and the mission ends after the drive.
lose: the trucks at 1 % health as they set off (the war factory's drones mend them while parked): the first
  ambush kills two and the mission ends well before the drive's time.
idle: as played, the player doing nothing: the convoy is lost (bench 2026-10-23: ended at s78, 18 s after leaving).
harbour: what "enemies cleared" counts at the harbour: armed ones, not its bridge.
"""
import plan
from parts import Obj, Script, Test, counted, square
from units import icewall as iw

BUILD_BEFORE = 10.0                             # seal: the power is fired this long before the convoy leaves
WALK_BUILD = 9.0                                # seal: from the road in front of the gate: 70 at speed 40, 5 s, margin
SMASH_AT = 10.0
INSIDE = 95.0                                   # half-side of the area counted as inside a plaza
GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
ROAD_MARGIN = 30.0                              # the road area stops this far short of the gates' lines
DRIVE = 43.0                                    # convoy start to exit at the ore collector's speed 50 (2140 / 50)
LEAD = 4.0                                      # the mission runs ~3 s ahead of the bench's clock (bench 2026-10-25:
                                                # "车队出发了" on screen at bench s177, leaving at 180), margin
HALT = 15.0                                     # win: the stop at the halt and the start again, when nothing holds it
STOPS = 20.0                                    # win: three ambush stops, a tick or two each
OUT_OF_REACH = 6.0                              # lose: the last truck past the war factory's drones (108 + 200, speed 50)
HARBOUR = ('harbour ambush', 'harbour guard')   # the plan's parts waiting at the harbour (docs/story/plans/a4.md)
STOP_KILL = 30.0                                # stop: plaza 1's troops die this long after the convoy leaves
STOP_SEEN = 12.0                                # stop: by then it is held (the ambush check: troops out by leave + 10)
APPROACH = 150.0                                # stop: half-side of the area counted as plaza 2's approach
EARLY_FIRE = 30.0                               # early: the power fired then (walked from the start: ~1000 at 40)
EARLY_AFTER = 10.0                              # early: the convoy leaves this long after the first gate is iced
                                                # (docs/story/plans/a4.md 布防 结束)
TOUGH_FIRST = 25.0                              # tough: plaza 2's troops first killed this long after leaving (held
                                                # there from ~18 s: start to approach 2, 700 at 50, and plaza 1)
TOUGH_EVERY = 6.0                               # tough: killed again this often while they hold it (back every 15 s)
TOUGH_ICE = 60.0                                # tough: engineer 2 ices plaza 2's gate then
WIN_ICE = 5.0                                   # win: ... this long after leaving: up before a truck gets there
HALT_AREA = 100.0                               # tough: half-side of the area counted as at the halt
NORTH_HALT = (20.0, 45.0)                       # north: played the quick way, the convoy at the halt this long after
                                                # leaving (soonest, latest; win: ~25 s), the harbour turning then
NORTH_WAKE = 30.0                               # north: the AI wakes this long after (docs/story/plans/a4.md 敌方AI)
NORTH_RUN = 420.0                               # north: watched this long after the latest it wakes (bench
                                                # 2026-10-26: woken s111, first down s339; with no refinery it
                                                # stopped spending at 1400 and had not come down by s326)


def ice_wall(m):
    """The wall engineer 1's power ends in: what he builds, or what that leaves (a seed's `wall` param)."""
    u = next(u for u in m.units if u.id == m.param('engineer 1', 'wall'))
    while 'wall' in u.params:
        u = next(v for v in m.units if v.id == u.params['wall'])
    return u


def start(t, m):
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))


def in_plaza(t, m, k, part, label):
    """1 while cast `part` (created when its sculpture breaks) stands inside plaza k."""
    area = f'Test Plaza {k}'
    t.areas[area] = square(*m.site(f'plaza {k}'), INSIDE)
    counted(f'Test In {k}', label, t, named=m.role(part).name, area=area)


def on_road(t, m, part, label):
    """1 while cast `part` stands on the road: between the convoy's start and the exit, short of the gates' lines (a
    troop held at its wall is still in its plaza; bench 2026-10-23: an area around the plaza's middle lost them as
    soon as they walked up to the gate)."""
    area = 'Test Road'
    (x0, y0), (x1, _) = m.site('convoy start'), m.site('road exit')
    gap = min(abs(m.site(f'gate {k}')[1] - y0) for k in (1, 2)) - ROAD_MARGIN
    t.areas[area] = [(x0, y0 - gap), (x1 + 100, y0 - gap), (x1 + 100, y0 + gap), (x0, y0 + gap)]
    counted(f'Test Road {part}', label, t, named=m.role(part).name, area=area)


def seal(m):
    m.drop_endings()                            # the convoy may be lost before the wall melts: keep counting
    t = Test()
    start(t, m)
    leave = m.facts['convoy leaves']
    wall = ice_wall(m)
    life = wall.params['lifetime']
    timer = 'Test - seal timer'
    walk_to(t, m)
    t.scripts += [Script('Test - seal set', [], [('SET_MILLISECOND_TIMER', timer, leave - BUILD_BEFORE)]),
                  Script('Test - seal', [('TIMER_EXPIRED', timer)],
                         [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role('engineer 1').name,
                           m.ability('engineer 1', 'freeze'), m.mark('seal 1'))])]
    counted('Test Walls', '冰墙', t, template=wall.id)
    on_road(t, m, 'troop 1-1-1', '1 号的兵上路')
    on_road(t, m, 'troop 2-1-1', '2 号的兵上路')
    gone = leave - BUILD_BEFORE + WALK_BUILD + life         # the wall comes when his building ends
    t.expect += [('冰墙', leave - BUILD_BEFORE + WALK_BUILD, 'ever==', 1),
                 ('2 号的兵上路', leave, 'ever==', 1),                           # the convoy breaks plaza 2 too
                 ('1 号的兵上路', 0, '==', 0, gone - 4),                        # sealed while the wall stands
                 ('1 号的兵上路', gone + 6, 'ever==', 1)]                         # out once it melts
    t.bench = [('bench_watch', dict(seconds=gone + 20, every=3, sheet=False, lines=len(t.counters)))]
    return t


def walk_to(t, m):
    """Engineer 1 walked (by test script, at once) to the road in front of plaza 1's gate; returns where."""
    x, y = m.point('seal 1')
    t.waypoints['Test Engineer Spot'] = (x, y - 70)
    t.scripts.append(Script('Test - walk', [], [('MOVE_NAMED_UNIT_TO', m.role('engineer 1').name,
                                                 'Test Engineer Spot')]))
    return t.waypoints['Test Engineer Spot']


def placed(m):
    """The control behind the mission's held-gate rule: a bar placed by the map (angle 0, lasting the whole run)
    across plaza 1's gate -- the gap in its cliff --, plaza 3's open. Bench 2026-10-23: it held plaza 1's tank buster in its
    plaza 37 s; the wall built in play did not (see missions/a4.py, units/icewall.py)."""
    m.drop_endings()                            # unescorted, the convoy is lost (2026-10-25: at s207): keep counting
    t = Test()
    start(t, m)
    w = iw.wall('CNV_A4TestWall', length=200, lifetime=300)     # across the gate's gap, as the map's description says
    t.units.append(w)
    t.objects.append(Obj(w.id, *m.site('gate 1'), name='UNIT - Test Wall', angle=0.0, site='gate 1'))
    on_road(t, m, 'troop 1-1-1', '1 号的兵上路')
    on_road(t, m, 'troop 3-1-1', '3 号的兵上路')
    in_plaza(t, m, 1, 'troop 1-1-1', '1 号的兵在广场')     # held, not never there
    leave = m.facts['convoy leaves']
    # 遇伏 停下: plaza 1's troops, behind a wall the plazas do not know, hold the convoy there for good -- the open
    # plaza's sculptures broken by test script when it leaves instead (bench 2026-10-26: never reached, never out);
    # plaza 3, as plaza 2's let their troops out only when a truck gets there (广场 2: 无敌)
    t.scripts += [Script('Test - break 3 set', [], [('SET_MILLISECOND_TIMER', 'Test - break 3 timer', leave)]),
                  Script('Test - break 3', [('TIMER_EXPIRED', 'Test - break 3 timer')],
                         [('NAMED_KILL', m.role(f'sculpture 3-{i}').name) for i in (1, 2)])]
    t.expect +=[('3 号的兵上路', leave, 'ever==', 1), ('1 号的兵上路', 0, '==', 0, leave + 35),
                 ('1 号的兵在广场', leave - LEAD, 'ever==', 1)]      # out, they leave the plaza within seconds
    t.bench = [('bench_watch', dict(seconds=leave + 45, every=3, sheet=False, lines=len(t.counters)))]
    return t


def smash(m):
    t = Test()
    start(t, m)
    t.scripts += [Script('Test - smash set', [], [('SET_MILLISECOND_TIMER', 'Test - smash timer', SMASH_AT)]),
                  Script('Test - smash', [('TIMER_EXPIRED', 'Test - smash timer')],
                         [('NAMED_KILL', m.role('sculpture 3-1').name)])]
    in_plaza(t, m, 3, 'troop 3-1-1', '3-1 的兵')
    counted('Test Sculpture', '3-2 冰雕血量', t, health=m.role('sculpture 3-2').name)
    # out, they make for the parked trucks at once (the convoy's tick runs before it leaves): seen in the plaza only
    # for a few seconds
    t.expect += [('3-1 的兵', SMASH_AT - LEAD, 'ever==', 1, SMASH_AT + 10), ('3-2 冰雕血量', 0, '==', 100)]
    t.bench = [('bench_watch', dict(seconds=SMASH_AT + 12, every=2, sheet=False, lines=len(t.counters)))]
    return t


def ambush(m):
    t = Test()
    start(t, m)
    leave = m.facts['convoy leaves']
    in_plaza(t, m, 1, 'troop 1-1-1', '1 号广场的兵')
    counted('Test Sculpture', '1-1 冰雕血量', t, health=m.role('sculpture 1-1').name)
    t.expect += [('1 号广场的兵', 0, '==', 0, leave - LEAD), ('1-1 冰雕血量', 0, '==', 100, leave - LEAD),
                 ('1 号广场的兵', leave - LEAD, 'ever==', 1, leave + 10)]
    t.bench = [('bench_watch', dict(seconds=leave + 12, every=2, sheet=False, lines=len(t.counters)))]
    return t


def trucks(t, m):
    for j in (1, 2):
        counted(f'Test Truck {j}', f'{j} 号车血量', t, health=m.role(f'truck {j}').name)


def keep_up(t, m):
    t.scripts.append(Script('Test - keep the trucks up', [], [('UNIT_SET_HEALTH', r.name, 100.0)
                                                             for r in m.roles('truck')], once=False))


def blocking(m, k):
    """The flag that is 1 while plaza k's troops hold the convoy (the plazas' 拦住 k): the one their Blocked script
    sets."""
    return next(s.do[0][1] for s in m.scripts if s.name.endswith(f' - Blocked {k}'))


def troops(m, k):
    return [r.name for part, r in m.cast.items() if part.startswith(f'troop {k}-')]


def stop(m):
    m.drop_endings()
    t = Test()
    start(t, m)
    keep_up(t, m)
    leave = m.facts['convoy leaves']
    held = blocking(m, 1)
    t.counters.append(('Test Held', '被拦'))
    t.scripts += [Script('Test - held zero', [], [('SET_COUNTER', 'Test Held', 0)], once=False),
                  Script('Test - held one', [('FLAG', held, 1)], [('SET_COUNTER', 'Test Held', 1)], once=False),
                  Script('Test - kill set', [], [('SET_MILLISECOND_TIMER', 'Test - kill timer', leave + STOP_KILL)]),
                  Script('Test - kill plaza 1', [('TIMER_EXPIRED', 'Test - kill timer')],
                         [('NAMED_KILL', n) for n in troops(m, 1)])]
    t.areas['Test Approach 2'] = square(*m.site('approach 2'), APPROACH)
    counted('Test Past 1', '车到2号路口', t, named=m.role('truck 1').name, area='Test Approach 2')
    killed = leave + STOP_KILL
    t.expect += [('被拦', 0, '==', 0, leave - LEAD), ('被拦', leave, 'ever==', 1, leave + STOP_SEEN),
                 ('被拦', leave + STOP_SEEN + 2, '==', 1, killed - LEAD),        # still held, troops alive
                 ('车到2号路口', 0, '==', 0, killed - LEAD),
                 ('被拦', killed + 4, 'ever==', 0, killed + 10),
                 ('车到2号路口', killed, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=killed + 45, every=3, sheet=False, lines=len(t.counters)))]
    return t


def rolling(m):
    """The flag that is 1 once the convoy has set off: the one its departure sets."""
    go = next(s for s in m.scripts if ' - Convoy go' in s.name)
    return next(a[1] for a in go.do if a[0] == 'SET_FLAG' and a[2] == 1)


def early(m):
    """The player ices a gate first: the convoy leaves EARLY_AFTER later, before its time."""
    m.drop_endings()
    t = Test()
    start(t, m)
    walk_to(t, m)
    leave, wall = m.facts['convoy leaves'], ice_wall(m)
    t.scripts += [Script('Test - seal set', [], [('SET_MILLISECOND_TIMER', 'Test - seal timer', EARLY_FIRE)]),
                  Script('Test - seal', [('TIMER_EXPIRED', 'Test - seal timer')],
                         [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role('engineer 1').name,
                           m.ability('engineer 1', 'freeze'), m.mark('seal 1'))])]
    counted('Test Walls', '冰墙', t, template=wall.id)
    t.counters.append(('Test Left', '出发'))
    t.scripts += [Script('Test - left zero', [], [('SET_COUNTER', 'Test Left', 0)], once=False),
                  Script('Test - left one', [('FLAG', rolling(m), 1)], [('SET_COUNTER', 'Test Left', 1)], once=False)]
    built = EARLY_FIRE + WALK_BUILD
    t.expect += [('冰墙', EARLY_FIRE, 'ever==', 1, built),
                 ('出发', 0, '==', 0, EARLY_FIRE + EARLY_AFTER - LEAD),          # not before the wall's 10 s
                 ('出发', EARLY_FIRE, 'ever==', 1, leave - LEAD)]                # well before its time
    t.bench = [('bench_watch', dict(seconds=leave + 5, every=2, sheet=False, lines=len(t.counters)))]
    return t


def gate_spot(t, m, k, part):
    """Engineer `part` walked (by test script, at once) to the road in front of plaza k's gate, kept unhurt (the
    plaza's troops come out past him: the check is the ice, not his luck); returns where."""
    x, y = m.point(f'seal {k}')
    road = m.site('convoy start')[1]
    spot = f'Test Engineer Spot {k}'
    t.waypoints[spot] = (x, y + (70 if road > y else -70))
    name = m.role(part).name
    t.scripts.append(Script(f'Test - walk {part}', [], [('MOVE_NAMED_UNIT_TO', name, spot),
                                                        ('UNIT_CHANGE_OBJECT_STATUS', name, 'UNATTACKABLE', 1)]))
    return t.waypoints[spot]


def freeze(t, m, k, part, when):
    """Engineer `part` freezes plaza k's gate when `when` (script conditions) first holds."""
    t.scripts.append(Script(f'Test - freeze {k}', when, [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role(part).name,
                                                          m.ability(part, 'freeze'), m.mark(f'seal {k}'))]))


def left(m, k):
    """The counter of plaza k's troops out and alive (the device's: what its sculptures' breaking adds to)."""
    return next(a[2] for s in m.scripts if f' - Out {k}-1' in s.name for a in s.do if a[0] == 'INCREMENT_COUNTER')


def tough(m):
    """Plaza 2 (广场 2: 无敌, 补兵): the player's tanks can not hurt its sculptures; the convoy held there stays held
    however often its troops are killed -- they come back --, and goes on once engineer 2 ices the gate."""
    m.drop_endings()
    t = Test()
    start(t, m)
    keep_up(t, m)
    leave = m.facts['convoy leaves']
    held = blocking(m, 2)
    gate_spot(t, m, 2, 'engineer 2')
    t.scripts += [Script('Test - shoot sculpture', [], [('NAMED_ATTACK_NAMED', r.name, m.role('sculpture 2-1').name)
                                                         for r in m.roles('guardian')]),
                  Script('Test - clear plaza 1', [('FLAG', blocking(m, 1), 1)],
                         [('NAMED_KILL', n) for n in troops(m, 1)], once=False),
                  Script('Test - kill 2 set', [], [('SET_MILLISECOND_TIMER', 'Test - kill 2 timer', leave + TOUGH_FIRST)]),
                  Script('Test - kill plaza 2', [('FLAG', held, 1), ('TIMER_EXPIRED', 'Test - kill 2 timer')],
                         [('NAMED_KILL', n) for n in troops(m, 2)] +
                         [('SET_MILLISECOND_TIMER', 'Test - kill 2 timer', TOUGH_EVERY)], once=False),
                  Script('Test - ice set', [], [('SET_MILLISECOND_TIMER', 'Test - ice timer', leave + TOUGH_ICE)])]
    freeze(t, m, 2, 'engineer 2', [('TIMER_EXPIRED', 'Test - ice timer')])
    counted('Test Sculpture', '2-1 冰雕血量', t, health=m.role('sculpture 2-1').name)
    t.counters.append(('Test Held 2', '被拦'))
    t.scripts += [Script('Test - held zero', [], [('SET_COUNTER', 'Test Held 2', 0)], once=False),
                  Script('Test - held one', [('FLAG', held, 1)], [('SET_COUNTER', 'Test Held 2', 1)], once=False)]
    t.counters.append((left(m, 2), '2 号伏兵'))
    t.areas['Test Halt'] = square(*m.site('halt'), HALT_AREA)
    counted('Test At Halt', '车到停车点', t, named=m.role('truck 1').name, area='Test Halt')
    ice = leave + TOUGH_ICE
    t.expect += [('2-1 冰雕血量', 0, '==', 100, ice),
                 ('被拦', leave + TOUGH_FIRST, '==', 1, ice - LEAD),          # held all along, troops killed or not
                 ('2 号伏兵', leave + TOUGH_FIRST + 2, 'ever==', 0, ice - LEAD),            # killed ...
                 ('2 号伏兵', leave + TOUGH_FIRST + TOUGH_EVERY, 'ever>=', 1, ice - LEAD),  # ... and back
                 ('车到停车点', 0, '==', 0, ice - LEAD),
                 ('车到停车点', ice, 'ever==', 1, ice + 30)]
    t.bench = [('bench_watch', dict(seconds=ice + 35, every=2, sheet=False, lines=len(t.counters)))]
    return t


def escorted(t, m):
    """Played the quick way (win's): trucks kept up, plaza 1's and 3's troops killed as they hold the convoy, plaza
    2's gate iced before it gets there, the harbour's ambush gone from the start."""
    keep_up(t, m)
    t.scripts += [Script(f'Test - clear plaza {k}', [('FLAG', blocking(m, k), 1)],
                         [('NAMED_KILL', n) for n in troops(m, k)], once=False) for k in (1, 3)]
    t.scripts.append(Script('Test - clear the harbour', [], [('NAMED_KILL', r.name) for g in HARBOUR
                                                             for r in m.roles(g)]))
    gate_spot(t, m, 2, 'engineer 2')
    t.scripts.append(Script('Test - ice set', [], [('SET_MILLISECOND_TIMER', 'Test - ice timer',
                                                    m.facts['convoy leaves'] + WIN_ICE)]))
    freeze(t, m, 2, 'engineer 2', [('TIMER_EXPIRED', 'Test - ice timer')])


def north(m):
    """The north camp given to the skirmish AI (敌方AI) once the harbour turns (段 港口生变 + 0:30): asleep and broke
    until then, it is handed the barracks, factory, power plant and guards, gets its money and spends it on troops,
    which come down off the plateau."""
    m.drop_endings()                            # the convoy gets through: keep counting
    t = Test()
    start(t, m)
    escorted(t, m)
    ai, leave = m.ai_player(), m.facts['convoy leaves']
    for part, label in (('north barracks', 'AI的兵营'), ('north factory', 'AI的工厂')):
        counted(f'Test AI {part}', label, t, template=m.role(part).template, player=ai)
    t.counters.append(('Test AI Money', '敌方资金'))
    t.scripts.append(Script('Test - AI money', [], [('SET_PLAYER_MONEY_TO_COUNTER', ai, 'Test AI Money')], once=False))
    # the low ground between the plateau and the road (the has-units test is the AI's alone)
    (x0, y0), (x1, _) = m.site('convoy start'), m.site('road exit')
    top = m.site('north camp')[1]               # the low ground north of the plazas, below the plateau's ramps
    t.areas['Test Below'] = [(x0, y0), (x1, y0), (x1, top), (x0, top)]
    t.counters.append(('Test AI Below', 'AI下山'))
    t.scripts += [Script('Test - AI below zero', [], [('SET_COUNTER', 'Test AI Below', 0)], once=False),
                  Script('Test - AI below', [('SKIRMISH_PLAYER_HAS_UNITS_IN_AREA', ai, 'Test Below')],
                         [('SET_COUNTER', 'Test AI Below', 1)], once=False)]
    money = plan.counts(plan.load('a4')['敌方AI']['资金'])[1]
    asleep, woken = leave + NORTH_HALT[0] + NORTH_WAKE, leave + NORTH_HALT[1] + NORTH_WAKE
    t.expect += [('敌方资金', 1, '==', 0, asleep - LEAD), ('敌方资金', asleep - LEAD, 'ever>', 0, woken + 12),
                 ('敌方资金', asleep, 'ever<', money - 1000, woken + NORTH_RUN),
                 ('AI下山', 1, '==', 0, asleep), ('AI下山', asleep, 'ever==', 1, woken + NORTH_RUN),
                 ('AI的兵营', woken + 8, '>=', 1), ('AI的工厂', woken + 8, '>=', 1)]
    t.bench = [('bench_watch', dict(seconds=woken + NORTH_RUN, every=4, sheet=False, lines=len(t.counters)))]
    return t


def win(m):
    t = Test()
    start(t, m)
    # a plaza's troops die as soon as they hold the convoy: it goes on (遇伏 停下); plaza 2's come back -- iced
    # before the convoy gets there instead; the harbour's stop (phase 3) ends as soon as it begins
    escorted(t, m)
    trucks(t, m)
    leave = m.facts['convoy leaves']
    t.expect += [('1 号车血量', 0, '==', 100, leave), ('ENDED', leave + DRIVE - 10, '', None)]
    t.bench = [('bench_watch', dict(seconds=leave + DRIVE + HALT + STOPS + 20, every=3, sheet=False,
                                    lines=len(t.counters)))]
    return t


def harbour(m):
    """What `敌人清空 harbour` tests, with the player's own army standing in the harbour (as it does when it clears
    it): enemy there while its troops stand, none once they are killed (10 s), the player's tanks there throughout.
    Bench 2026-10-25: the condition first counted the enemy's CAN_ATTACK in the area, which the engine counts for
    every player (probe/count) -- the player's army there would have kept it from ever holding."""
    t = Test()
    start(t, m)
    for k in range(3):                              # unattackable: they stay while the enemy is killed
        t.objects.append(Obj(GUARDIAN, *m.site('harbour', -60 + 60 * k, -120), name=f'UNIT - Test Harbour Tank {k}',
                             site='harbour'))
    t.scripts += [Script('Test - our tanks stay', [], [('UNIT_CHANGE_OBJECT_STATUS', f'UNIT - Test Harbour Tank {k}',
                                                         'UNATTACKABLE', 1) for k in range(3)]),
                  Script('Test - clear set', [], [('SET_MILLISECOND_TIMER', 'Test - clear timer', 10.0)]),
                  Script('Test - clear the harbour', [('TIMER_EXPIRED', 'Test - clear timer')],
                         [('NAMED_KILL', r.name) for g in HARBOUR for r in m.roles(g)])]
    area = next(k for k in m.areas if k.endswith('Area harbour'))
    clear = next(c for s in m.scripts for c in s.when if c[0] == 'SKIRMISH_PLAYER_HAS_UNITS_IN_AREA' and c[2] == area)
    t.counters.append(('Test Harbour clear', '港口清空'))
    t.scripts += [Script('Test - clear zero', [], [('SET_COUNTER', 'Test Harbour clear', 0)], once=False),
                  Script('Test - clear one', [clear], [('SET_COUNTER', 'Test Harbour clear', 1)], once=False)]
    counted('Test Harbour ours', '我方在港口', t, template=GUARDIAN, area=area)
    t.expect += [('港口清空', 3, '==', 0, 8), ('港口清空', 13, '==', 1), ('我方在港口', 3, '==', 3)]
    t.bench = [('bench_watch', dict(seconds=20, every=3, sheet=False, lines=len(t.counters)))]
    return t


def idle(m):
    """The mission as played, the player doing nothing: the troops take two trucks and the mission ends before the
    convoy could have reached the exit (a defence level must not win itself)."""
    t = Test()
    start(t, m)
    trucks(t, m)
    leave = m.facts['convoy leaves']
    t.expect += [('ENDED', leave, '', None)]
    t.bench = [('bench_watch', dict(seconds=leave + DRIVE - 6, every=2, sheet=False, lines=len(t.counters)))]
    return t


def lose(m):
    """The trucks to 1 % as they set off, and once more when out of the war factory's reach: its repair drones (200
    from it, 20 a second: bench 2026-10-25) mend what stands at the convoy's start, set at the start they were whole
    again before leaving."""
    t = Test()
    start(t, m)
    trucks(t, m)
    leave = m.facts['convoy leaves']
    for k, at in enumerate((leave, leave + OUT_OF_REACH)):
        timer = f'Test - weaken timer {k + 1}'
        t.scripts += [Script(f'Test - weaken set {k + 1}', [], [('SET_MILLISECOND_TIMER', timer, at)]),
                      Script(f'Test - weaken {k + 1}', [('TIMER_EXPIRED', timer)],
                             [('UNIT_SET_HEALTH', r.name, 1.0) for r in m.roles('truck')])]
    # weakened indeed: in the drones' reach a few seconds at most (1 % + 4 % a second); read early, the demo's
    # troop at the first approach kills them within seconds (2026-10-25: ended at bench s181)
    t.expect += [('2 号车血量', leave - LEAD, 'ever<=', 30, leave + OUT_OF_REACH), ('ENDED', leave, '', None)]
    t.bench = [('bench_watch', dict(seconds=leave + DRIVE - 12, every=2, sheet=False, lines=len(t.counters)))]
    return t
