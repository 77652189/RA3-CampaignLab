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
