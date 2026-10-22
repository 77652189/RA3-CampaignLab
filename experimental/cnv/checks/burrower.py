"""Burrowing APC tests, A against B on one map: A presses burrow, B does not, then both drive past the Hammers to
their goals. Counters: health (percent; it stays at the last value when the unit dies -- bench 2026-10-22, B read 8
after it blew up), whether one reached its goal (named in an area), conscripts aboard and in A's goal area.

pass: A underground is never shot (100 % all the way) and arrives; B on the surface takes fire.
drop (deliver): A also surfaces at its goal and unloads its three conscripts there; surfaced, it can be hit again.
"""
from parts import Script, Test, counted, square, status

BURROW_AT, GO_AT = 3.0, 6.0
GOAL = 100.0                                    # half-side of the area around each goal
UNLOAD_AFTER = 2.0                              # deliver: seconds between surfacing and unloading
SURFACE_BY = 10.0                               # A reaches its goal (and surfaces) between s10 and s12


def orders(m, t, burrow=('A',)):
    """Scripts: burrow the listed ones at BURROW_AT, send both to their goals at GO_AT; a goal area each."""
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - burrow', BURROW_AT),
                                                 ('SET_MILLISECOND_TIMER', 'Test - go', GO_AT)]))
    t.scripts.append(Script('Test - burrow', [('TIMER_EXPIRED', 'Test - burrow')],
                            [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(f'burrower {k}').name,
                              m.ability(f'burrower {k}', 'burrow')) for k in burrow]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go')],
                            [('MOVE_NAMED_UNIT_TO', m.role(f'burrower {k}').name, m.mark(f'goal {k}')) for k in 'AB']))
    for k in 'AB':
        t.areas[f'Test Goal {k}'] = square(*m.point(f'goal {k}'), GOAL)


def burrow_pass(m):
    t = Test()
    orders(m, t)
    for k in 'AB':
        who = m.role(f'burrower {k}').name
        counted(f'Test {k} Health', f'{k} 血量', t, health=who)
        counted(f'Test {k} There', f'{k} 到达', t, named=who, area=f'Test Goal {k}')
    t.expect += [('A 血量', 0, '==', 100), ('A 到达', GO_AT, 'ever==', 1), ('B 血量', GO_AT, 'ever<', 100)]
    t.bench = [('bench_watch', dict(seconds=40, every=3, sheet=False, lines=len(t.counters)))]
    return t


def deliver(m):
    t = Test()
    orders(m, t)
    a = m.role('burrower A').name
    t.scripts += [Script('Test - surface', [('NAMED_INSIDE_AREA', a, 'Test Goal A')],
                         [('NAMED_USE_COMMANDBUTTON_ABILITY', a, m.ability('burrower A', 'burrow')),
                          ('SET_MILLISECOND_TIMER', 'Test - unload', UNLOAD_AFTER)]),
                  Script('Test - unload', [('TIMER_EXPIRED', 'Test - unload')],
                         [('NAMED_USE_COMMANDBUTTON_ABILITY', a, m.ability('burrower A', 'unload'))])]
    counted('Test A Health', 'A 血量', t, health=a)
    counted('Test A There', 'A 到达', t, named=a, area='Test Goal A')
    # passengers count in an area where their transport stands (bench 2026-10-22: 3 "out" the moment A arrived,
    # 2 s before the unload): what is still aboard is told apart by the status passengers carry, ENCLOSED
    counted('Test Aboard', '车上步兵', t, status=status('ENCLOSED'))
    counted('Test Out', '区域步兵', t, template=m.role('passenger').template, area='Test Goal A')
    # underground untouched; surfaced it can be shot again (bench 2026-10-22: the Hammers came after it, 83 % at s12,
    # dead by s19 -- the unload had worked)
    t.expect += [('A 血量', 0, '==', 100, SURFACE_BY), ('车上步兵', 0, '>=', 3, GO_AT), ('车上步兵', GO_AT, 'ever==', 0),
                 ('区域步兵', GO_AT, 'ever==', 3), ('A 血量', SURFACE_BY, 'ever<', 100)]
    # no early stop: the frames after the unload show where the conscripts went
    t.bench = [('bench_watch', dict(seconds=22, every=2, sheet=False, lines=len(t.counters)))]
    return t
