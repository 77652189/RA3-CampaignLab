"""A5 tests (the plan: docs/story/plans/a5.md). The fleet is kept at full health every frame and its lead ship sent
for the sea every few seconds from GO_AT; the control room's guards are killed by test script RAZE_AFTER into phase
2 -- what the beacon's squad does in play.

hold: while the gates are shut the lead ship stays in the chamber; once the guards are dead the gates open and it
  leaves.
win: the same, and the fleet's three destroyers all sent: two at the sea and the mission is over.
"""
from parts import Script, Test, counted, square

GO_AT, RAZE_AFTER, AREA = 5.0, 5.0, 250.0
OUT = 60.0                                      # from the gates' opening: the lead ship out of the chamber by then
SEA = 150.0                                     # from the gates' opening: two ships at the sea, the mission over


def opened(m):
    return m.facts['段 夺控制室'] + RAZE_AFTER


def setup(m, ships):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                  ('SET_MILLISECOND_TIMER', 'Test - go timer', GO_AT)]))
    fleet = [m.role(f'fleet {k}').name for k in range(1, 4)] + [m.role('carrier').name]
    t.scripts.append(Script('Test - keep the fleet up', [], [('UNIT_SET_HEALTH', n, 100.0) for n in fleet],
                            once=False))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                            [('MOVE_NAMED_UNIT_TO', m.role(f'fleet {k}').name, m.mark('sea exit')) for k in ships] +
                            [('SET_MILLISECOND_TIMER', 'Test - go timer', 4.0)], once=False))
    flag = 'CNV_A5_Phase_2'                     # plan.py's phase flags: CNV_<tag>_Phase_<k>
    guards = [r.name for g in ('control guard', 'control tesla') for r in m.roles(g)]
    t.scripts += [Script('Test - raze timer', [('FLAG', flag, 1)],
                         [('SET_MILLISECOND_TIMER', 'Test - raze timer', RAZE_AFTER)]),
                  Script('Test - raze', [('FLAG', flag, 1), ('TIMER_EXPIRED', 'Test - raze timer')],
                         [('NAMED_KILL', g) for g in guards])]
    t.areas['Test chamber'] = square(*m.site('chamber'), AREA)
    counted('Test In chamber', '在闸室', t, named=m.role('fleet 1').name, area='Test chamber')
    return t


def hold(m):
    t = setup(m, [1])
    at = opened(m)
    t.expect += [('在闸室', 1, '==', 1, at), ('在闸室', at, 'ever==', 0, at + OUT)]
    t.bench = [('bench_camera', dict(x=m.site('chamber')[0], y=m.site('chamber')[1], look=False)),
               ('bench_watch', dict(seconds=at + OUT, every=4, sheet=False, lines=len(t.counters)))]
    return t


def win(m):
    t = setup(m, [1, 2, 3])
    t.expect += [('ENDED', opened(m), '', None)]
    t.bench = [('bench_watch', dict(seconds=opened(m) + SEA, every=4, sheet=False, lines=len(t.counters)))]
    return t


ROUTE_RUN = 100.0                               # route: seconds for the Riptide to cross and the beacon to climb
BEACH_AREA, STAIR_AREA = 150.0, 100.0


def route(m):
    """The way the plan's answer takes, in the real game (the draft's two doubts: the banks are steep, so only the
    slips let an amphibian ashore; the back stair is the only way up that the ramp's guns do not face). Phase 1, the
    east bank's guards not yet in play: a Riptide sent to the east beach from the west bank, and the beacon put down
    on the beach and sent to the back stair's head (a Riptide's cargo in play, here walked: the carry itself is
    the unit's own). Both must arrive."""
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                  ('SET_MILLISECOND_TIMER', 'Test - go timer', GO_AT)]))
    t.waypoints['Test Beach'] = tuple(m.site('east beach'))
    t.waypoints['Test Stair'] = tuple(m.site('back stair'))
    ride, beacon = m.role('riptide 1').name, m.role('beacon').name
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                            [('UNIT_TELEPORT_TO_WAYPOINT', beacon, 'Test Beach'),
                             ('MOVE_NAMED_UNIT_TO', ride, 'Test Beach'),
                             ('MOVE_NAMED_UNIT_TO', beacon, 'Test Stair')]))
    t.areas['Test beach'] = square(*m.site('east beach'), BEACH_AREA)
    t.areas['Test stair'] = square(*m.site('back stair'), STAIR_AREA)
    counted('Test Ride on beach', 'Riptide在滩头', t, named=ride, area='Test beach')
    counted('Test Beacon on stair', '信标兵在背阶顶', t, named=beacon, area='Test stair')
    t.expect += [('Riptide在滩头', 0, 'ever==', 1, ROUTE_RUN), ('信标兵在背阶顶', 0, 'ever==', 1, ROUTE_RUN)]
    t.bench = [('bench_camera', dict(x=m.site('east beach')[0], y=m.site('east beach')[1], look=False)),
               ('bench_watch', dict(seconds=ROUTE_RUN, every=4, sheet=False, lines=len(t.counters)))]
    return t


# the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
CHECKS = {
    'a5': {'hold': hold, 'win': win, 'route': route},
}
