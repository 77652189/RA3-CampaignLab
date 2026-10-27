"""Lock gate tests (missions/lock_bench.py): the ship is sent to the goal past the gate at GO_AT, again every few
seconds. Bench 2026-10-27: a structure the map places on the water does not bar a ship (it sailed through the gate
in 12 s) -- so the lock holds its fleet by status (IMMOBILE, as the armoured train's brake), the gate is the look.

shut: the ship is held the whole run -- it never gets there.
open: held, then let go (and the gate deleted) at OPEN_AT -- not there before, there after.
"""
from parts import Script, Test, counted, square

GO_AT, OPEN_AT, RUN = 5.0, 30.0, 75.0
GOAL = 120.0


def trip(m, open_at=None):
    t = Test()
    ship = m.role('ship').name
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('UNIT_CHANGE_OBJECT_STATUS', ship, 'IMMOBILE', 1),
                                                 ('SET_MILLISECOND_TIMER', 'Test - go timer', GO_AT)]))
    # sent again every few seconds: a ship refused a path may give the order up
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                            [('MOVE_NAMED_UNIT_TO', ship, m.mark('goal')),
                             ('SET_MILLISECOND_TIMER', 'Test - go timer', 4.0)], once=False))
    if open_at is not None:
        t.scripts += [Script('Test - open timer', [], [('SET_MILLISECOND_TIMER', 'Test - open timer', open_at)]),
                      Script('Test - open', [('TIMER_EXPIRED', 'Test - open timer')],
                             [('UNIT_CHANGE_OBJECT_STATUS', ship, 'IMMOBILE', 0),
                              ('NAMED_DELETE', m.role('gate').name)])]
    t.areas['Test Goal'] = square(*m.point('goal'), GOAL)
    counted('Test There', '船到了', t, named=ship, area='Test Goal')
    counted('Test Ship Health', '船血量', t, health=ship)
    return t


def shut(m):
    t = trip(m)
    t.expect += [('船到了', 1, '==', 0, RUN)]
    t.bench = [('bench_camera', dict(x=m.point('goal')[0], y=m.point('goal')[1] - 250, look=False)),
               ('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=len(t.counters)))]
    return t


def opened(m):
    t = trip(m, OPEN_AT)
    t.expect += [('船到了', 1, '==', 0, OPEN_AT), ('船到了', OPEN_AT, 'ever==', 1, RUN)]
    t.bench = [('bench_camera', dict(x=m.point('goal')[0], y=m.point('goal')[1] - 250, look=False)),
               ('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=len(t.counters), until='c1==1'))]
    return t
