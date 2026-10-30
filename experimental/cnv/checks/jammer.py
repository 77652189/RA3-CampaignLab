"""Jammer tests: the enemy mech is sent up the lane past the jammer at GO_AT; the map itself counts the seconds of
its trip (one a second until it is in the goal area), so the reading does not depend on when frames were taken.

jam: the jammer is switched on first -- the trip takes longer than free's.
free (the control): the jammer stays off.
"""
from parts import Script, Test, counted, square

JAM_AT, GO_AT = 10.0, 12.0
GOAL = 80.0
FREE_TRIP = 5                                   # free's trip in seconds (bench 2026-10-22: the Tengu is quick)


def trip(m, jam):
    t = Test()
    mech = m.role('mech').name
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - jam timer', JAM_AT),
                                                 ('SET_MILLISECOND_TIMER', 'Test - go timer', GO_AT)]))
    if jam:
        t.scripts.append(Script('Test - jam', [('TIMER_EXPIRED', 'Test - jam timer')],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role('jammer').name,
                                  m.ability('jammer', 'jam'))]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                            [('MOVE_NAMED_UNIT_TO', mech, m.mark('goal')),
                             ('SET_MILLISECOND_TIMER', 'Test - tick timer', 1.0)]))
    t.areas['Test Goal'] = square(*m.point('goal'), GOAL)
    t.counters.append(('Test Trip', '行程秒数'))
    t.scripts.append(Script('Test - tick', [('TIMER_EXPIRED', 'Test - tick timer'),
                                            ('NAMED_OUTSIDE_AREA', mech, 'Test Goal')],
                            [('INCREMENT_COUNTER', 1, 'Test Trip'),
                             ('SET_MILLISECOND_TIMER', 'Test - tick timer', 1.0)], once=False))
    counted('Test There', '到达', t, named=mech, area='Test Goal')
    counted('Test Jammer Health', '干扰车血量', t, health=m.role('jammer').name)
    t.expect += [('到达', GO_AT, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=90, every=3, sheet=False, lines=len(t.counters), until='c2==1'))]
    return t


def jam(m):
    t = trip(m, True)
    if FREE_TRIP:
        # 458 of the 750 at 40 %: about 4.5 s more
        t.expect.append(('行程秒数', GO_AT, 'ever>=', FREE_TRIP + 3))
    return t


def free(m):
    return trip(m, False)


def jam_air(m):
    """The jammer against a flier (J7 card A: do air units fly past it?). Only the reading: no trip-time expectation,
    the verdict is this run's 行程秒数 against the same flier's free run."""
    return trip(m, True)
