"""A4 tests; everything asked of the mission (its sites, cast, marks, facts) and the wall's published lifetime.

seal (A against B on one map): engineer 1 freezes a wall across plaza 1's gate shortly before the convoy leaves,
  plaza 2's gate stays open. The convoy breaks both plazas' sculptures on its way; plaza 2's tank buster is out on
  the road within seconds, plaza 1's stays off it while the wall stands and comes out after it melts.
placed: the control for seal's rule -- a map-placed bar holds the gate as well.
smash: the player breaks sculpture 2-1 early (by test script, long before the convoy): its tank buster stands in
  plaza 2 at once, while sculpture 2-2 is whole.
ambush: the convoy, as played, breaks plaza 1's sculptures as it passes the approach: the troops appear.
win: the trucks kept at full health: they reach the exit and the mission ends after the drive.
lose: the trucks at 1 % health as they set off (the war factory's drones mend them while parked): the first
  ambush kills two and the mission ends well before the drive's time.
idle: as played, the player doing nothing: the convoy is lost (bench 2026-10-23: ended at s78, 18 s after leaving).
harbour: what "enemies cleared" counts at the harbour: armed ones, not its bridge.
"""
from parts import Obj, Script, Test, counted, kindof, square
from units import icewall as iw

BUILD_BEFORE = 10.0                             # seal: the power is fired this long before the convoy leaves
WALK_BUILD = 9.0                                # seal: from the road in front of the gate: 70 at speed 40, 5 s, margin
SMASH_AT = 10.0
INSIDE = 95.0                                   # half-side of the area counted as inside a plaza
ROAD_MARGIN = 30.0                              # the road area stops this far short of the gates' lines
DRIVE = 43.0                                    # convoy start to exit at the ore collector's speed 50 (2140 / 50)
LEAD = 4.0                                      # the mission runs ~3 s ahead of the bench's clock (bench 2026-10-25:
                                                # "车队出发了" on screen at bench s177, leaving at 180), margin
HALT = 15.0                                     # win: the stop at the halt and the start again, when nothing holds it
OUT_OF_REACH = 6.0                              # lose: the last truck past the war factory's drones (108 + 200, speed 50)
HARBOUR = ('harbour ambush', 'harbour guard')   # the plan's parts waiting at the harbour (docs/story/plans/a4.md)


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
    across plaza 1's gate -- the gap in its cliff --, plaza 2's open. Bench 2026-10-23: it held plaza 1's tank buster in its
    plaza 37 s; the wall built in play did not (see missions/a4.py, units/icewall.py)."""
    m.drop_endings()                            # unescorted, the convoy is lost (2026-10-25: at s207): keep counting
    t = Test()
    start(t, m)
    w = iw.wall('CNV_A4TestWall', length=200, lifetime=300)     # across the gate's gap, as the map's description says
    t.units.append(w)
    t.objects.append(Obj(w.id, *m.site('gate 1'), name='UNIT - Test Wall', angle=0.0, site='gate 1'))
    on_road(t, m, 'troop 1-1-1', '1 号的兵上路')
    on_road(t, m, 'troop 2-1-1', '2 号的兵上路')
    in_plaza(t, m, 1, 'troop 1-1-1', '1 号的兵在广场')     # held, not never there
    leave = m.facts['convoy leaves']
    t.expect += [('2 号的兵上路', leave, 'ever==', 1), ('1 号的兵上路', 0, '==', 0, leave + 35),
                 ('1 号的兵在广场', leave - LEAD, 'ever==', 1)]      # out, they leave the plaza within seconds
    t.bench = [('bench_watch', dict(seconds=leave + 45, every=3, sheet=False, lines=len(t.counters)))]
    return t


def smash(m):
    t = Test()
    start(t, m)
    t.scripts += [Script('Test - smash set', [], [('SET_MILLISECOND_TIMER', 'Test - smash timer', SMASH_AT)]),
                  Script('Test - smash', [('TIMER_EXPIRED', 'Test - smash timer')],
                         [('NAMED_KILL', m.role('sculpture 2-1').name)])]
    in_plaza(t, m, 2, 'troop 2-1-1', '2-1 的兵')
    counted('Test Sculpture', '2-2 冰雕血量', t, health=m.role('sculpture 2-2').name)
    # out, they make for the parked trucks at once (the convoy's tick runs before it leaves): seen in the plaza only
    # for a few seconds
    t.expect += [('2-1 的兵', SMASH_AT - LEAD, 'ever==', 1, SMASH_AT + 10), ('2-2 冰雕血量', 0, '==', 100)]
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


def win(m):
    t = Test()
    start(t, m)
    t.scripts.append(Script('Test - keep the trucks up', [], [('UNIT_SET_HEALTH', r.name, 100.0)
                                                             for r in m.roles('truck')], once=False))
    # the harbour's ambush gone from the start: the convoy's stop there (phase 3) ends as soon as it begins
    t.scripts.append(Script('Test - clear the harbour', [], [('NAMED_KILL', r.name) for g in HARBOUR
                                                             for r in m.roles(g)]))
    trucks(t, m)
    leave = m.facts['convoy leaves']
    t.expect += [('1 号车血量', 0, '==', 100, leave), ('ENDED', leave + DRIVE - 10, '', None)]
    t.bench = [('bench_watch', dict(seconds=leave + DRIVE + HALT + 20, every=3, sheet=False, lines=len(t.counters)))]
    return t


def harbour(m):
    """What `敌人清空 harbour` counts: the enemy's armed (CAN_ATTACK) in the harbour area while its troops stand, and
    none once they are killed (10 s). Bench 2026-10-25: counted as SELECTABLE it never held in win, every troop
    dead -- the harbour's bridge is the enemy's (2 selectable, 3 structures, shown beside)."""
    t = Test()
    start(t, m)
    t.scripts += [Script('Test - clear set', [], [('SET_MILLISECOND_TIMER', 'Test - clear timer', 10.0)]),
                  Script('Test - clear the harbour', [('TIMER_EXPIRED', 'Test - clear timer')],
                         [('NAMED_KILL', r.name) for g in HARBOUR for r in m.roles(g)])]
    area = next(k for k in m.areas if k.endswith('Area harbour'))
    for kind, label in (('SELECTABLE', '港口可选'), ('CAN_ATTACK', '港口能打的'), ('STRUCTURE', '港口建筑')):
        counted(f'Test Harbour {kind}', label, t, area=area, kind=kindof(kind), player=m.player('s1'))
    t.expect += [('港口能打的', 3, '>=', 1, 8), ('港口能打的', 13, '==', 0)]
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
    # weakened indeed: in the drones' reach a few seconds at most (1 % + 4 % a second)
    t.expect += [('2 号车血量', leave + 2, '<=', 30, leave + OUT_OF_REACH), ('ENDED', leave, '', None)]
    t.bench = [('bench_watch', dict(seconds=leave + DRIVE - 12, every=2, sheet=False, lines=len(t.counters)))]
    return t
