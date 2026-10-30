"""A4 tests (the rework, docs/story/plans/a4.md on maps/sapporo.py); everything asked of the mission (its sites, cast,
marks, flags). The devices' own checks (seal, smash, stop, tough ...) are the frozen before-rework build's,
checks/a4_before.py; the helpers here are theirs.

idle: as played, the player doing nothing: plaza 1's troops hold the convoy and take two trucks; the mission ends
  (a level that wins itself is no level).
hold: plaza 2's tank busters (the rework's P29: 2 号 hides tank busters) against the ice in its gate: engineer 2
  ices it as the lead truck nears plaza 1, the convoy kept going (trucks kept up, plaza 1's troops killed when they
  hold it): plaza 2's troops let out while the wall stands, it stands its lifetime and they stay in while it does.
  Bench 2026-10-28 (CampA4Hold_mcp_1028_172254): the wall up s43-s73, plaza 2 broken by s57, its tank busters never
  on the road (the simulator's fight model had them break the wall in ~7 s: now it lets our ice be).
win: played the quick way: the trucks kept at full health, plaza 1's troops killed whenever they hold the convoy,
  engineer 2 icing plaza 2's gate before the lead truck gets there, the harbour's guard gone from the start, the
  north command razed as phase 2 begins, plaza 3 iced by the two engineers in turn while the trucks pass it: the
  convoy parks at plaza 2, leaves in batches after the 布防 countdown and gets to the harbour (counted: two at
  least; the simulator, the ice played by its script, has all three in by 4:41).
"""
from checks.a4_before import blocking, freeze, ice_wall, keep_up, left, on_road, start, troops, trucks
from parts import Script, Test, counted, square

IDLE_RUN = 300.0                                # idle: ended by then (sim 2026-10-28: lost 1:42, normal)
WIN_RUN = 600.0                                 # win: ended by then (sim 2026-10-28, no combat: won 5:46, normal)
RAZE_AFTER = 5.0                                # win: the north command down this long into phase 2
DETOUR = 100.0                                  # engineer 2 goes by the avenue this far south of its middle
HOLD_ICE = 46.0                                 # hold: the wall up by then (bench 2026-10-28: s43; the convoy, off
                                                # at ~31 s, gets to plaza 2 by ~57)
HOLD_OUT = 61.0                                 # hold: plaza 2's troops out by then, the wall still up (bench:
                                                # out at s58; s64-s79 the captions hide the counters)
HOLD_RUN = 140.0
# win: who ices plaza 3, and when (s after phase k began; normal: 布防 60 s, then the convoy goes on): a block ~9 s
# after the order, 30 s up -- before truck 1 gets there (+2 s) and while trucks 2 (+52) and 3 (+112) pass
RELAY = (('engineer 1', 3, 45.0), ('engineer 2', 4, 25.0), ('engineer 1', 4, 55.0), ('engineer 2', 4, 85.0))


def phase(m, k):
    """The flag that is 1 once the plan's k-th phase began."""
    return next(a[1] for s in m.scripts for a in s.do if a[0] == 'SET_FLAG' and a[1].endswith(f'_Phase_{k}'))


def arrived(m):
    """The convoy's counter of trucks at the exit (the device's)."""
    return next(a[2] for s in m.scripts for a in s.do if a[0] == 'INCREMENT_COUNTER' and str(a[2]).endswith('_Arrived'))


def escort(t, m):
    """The convoy kept going to plaza 2, iced in time: trucks kept up, plaza 1's (and 3's) troops killed when they
    hold it, engineer 2 (unhurt) freezing plaza 2's gate before the lead truck gets there: sent at once by the
    avenue's south side, clear of the lane's foot (walking over it sets the convoy off: the plan's 出发)."""
    keep_up(t, m)
    t.scripts += [Script(f'Test - clear plaza {k}', [('FLAG', blocking(m, k), 1)],
                         [('NAMED_KILL', n) for n in troops(m, k)], once=False) for k in (1, 3)]
    name = m.role('engineer 2').name
    foot = m.site('lane foot')
    t.waypoints['Test Detour'] = (foot[0], m.site('start')[1] - DETOUR)
    t.areas['Test Detour'] = square(*t.waypoints['Test Detour'], 60.0)
    t.scripts.append(Script('Test - detour', [], [('MOVE_NAMED_UNIT_TO', name, 'Test Detour'),
                                                  ('UNIT_CHANGE_OBJECT_STATUS', name, 'UNATTACKABLE', 1)]))
    freeze(t, m, 2, 'engineer 2', [('NAMED_INSIDE_AREA', name, 'Test Detour')])


def idle(m):
    t = Test()
    start(t, m)
    trucks(t, m)
    t.expect += [('ENDED', 30.0, '', None)]
    t.bench = [('bench_watch', dict(seconds=IDLE_RUN, every=5, sheet=False, lines=len(t.counters)))]
    return t


def hold(m):
    m.drop_endings()
    t = Test()
    start(t, m)
    escort(t, m)
    wall = ice_wall(m)
    life = wall.params['lifetime']
    counted('Test Walls', '冰墙', t, template=wall.id)
    on_road(t, m, 'troop 2-1-1', '2 号的兵上路')
    t.counters.append((left(m, 2), '2 号的伏兵'))
    t.expect += [('冰墙', HOLD_ICE, 'ever==', 1), ('2 号的伏兵', HOLD_OUT, 'ever>=', 1),
                 ('冰墙', HOLD_ICE + 3, '==', 1, HOLD_OUT + 1),                   # up while they are out
                 ('2 号的兵上路', 0, '==', 0, HOLD_OUT + 1),                       # and holds them in
                 ('2 号的兵上路', HOLD_ICE + life + 10, '==', 0, HOLD_RUN)]       # the convoy past: they stay
    t.bench = [('bench_watch', dict(seconds=HOLD_RUN, every=3, sheet=False, lines=len(t.counters)))]
    return t


def relay(t, m):
    """Plaza 3 (无敌, 补兵: only the ice gets a truck past it) kept iced while the three trucks pass it, 0 / 50 / 110 s
    after the convoy goes on: the two engineers in turn (one block lasts 30 s, an engineer's reload 40). Engineer 1
    goes there from the start, by the detour; engineer 2 once phase 2 begins, plaza 2 iced by then."""
    one, two = m.role('engineer 1').name, m.role('engineer 2').name
    gx, _ = m.site('gate 3')
    t.waypoints['Test Spot 3'] = (gx - 150.0, m.site('start')[1] - 60.0)
    t.scripts += [Script('Test - engineer 1 out', [], [('MOVE_NAMED_UNIT_TO', one, 'Test Detour'),
                                                       ('UNIT_CHANGE_OBJECT_STATUS', one, 'UNATTACKABLE', 1)]),
                  Script('Test - engineer 1 on', [('NAMED_INSIDE_AREA', one, 'Test Detour')],
                         [('MOVE_NAMED_UNIT_TO', one, 'Test Spot 3')]),
                  Script('Test - engineer 2 on', [('FLAG', phase(m, 2), 1)], [('MOVE_NAMED_UNIT_TO', two, 'Test Spot 3')])]
    for j, (part, k, after) in enumerate(RELAY, 1):
        timer = f'Test - relay timer {j}'
        t.scripts += [Script(f'Test - relay set {j}', [('FLAG', phase(m, k), 1)],
                             [('SET_MILLISECOND_TIMER', timer, after)]),
                      Script(f'Test - relay {j}', [('TIMER_EXPIRED', timer)],
                             [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role(part).name, m.ability(part, 'freeze'),
                               m.mark('seal 3'))])]


def win(m):
    t = Test()
    start(t, m)
    escort(t, m)
    relay(t, m)
    t.scripts.append(Script('Test - clear the harbour', [], [('NAMED_KILL', r.name) for r in m.roles('harbour guard')]))
    t.scripts += [Script('Test - raze set', [('FLAG', phase(m, 2), 1)],
                         [('SET_MILLISECOND_TIMER', 'Test - raze timer', RAZE_AFTER)]),
                  Script('Test - raze', [('TIMER_EXPIRED', 'Test - raze timer')],
                         [('NAMED_KILL', m.role('north command').name)])]
    trucks(t, m)
    # counted, not 'ENDED': a caption over the counters reads as their end (bench 2026-10-28: s66-s81, the mission
    # running on to s604)
    t.counters.append((arrived(m), '到终点'))
    t.expect += [('1 号车血量', 0, '==', 100, 60), ('到终点', 60, 'ever>=', 2)]
    t.bench = [('bench_watch', dict(seconds=WIN_RUN, every=5, sheet=False, lines=len(t.counters)))]
    return t
