"""J4 tests; everything asked of the mission (its sites, cast, marks, facts) and the mech's published ability.

breach: at JOIN_AT pair 1 joins; at ATTACK_AT parent 1 is ordered at ice 1, and a tank buster of plaza 1 and one of
  plaza 2 are ordered out onto the road. Ice 1 falls and plaza 1's comes out; plaza 2's ice stands and its man
  stays in (the map-placed ice bars a player's infantry ordered through it).
play: the level as meant (by test script): both pairs join and break ice 1 and 2; the freed troops go for the
  leading truck; no truck is on the map before the convoy sets off (bench 2026-10-23: parked trucks were taken at
  s64, before the departure); the convoy is taken and the mission ends before it could have reached the exit.
lose: the player does nothing: the convoy appears at its departure, drives the road untouched, reaches the exit,
  and only then does the mission end.
"""
from checks.a4 import DRIVE, on_road, start
from parts import Script, Test, counted

JOIN_AT, ATTACK_AT = 10.0, 16.0                 # past the bench's uncertain start; then a walk round to the gates


def join(t, m, pairs):
    t.scripts += [Script('Test - timers', [], [('SET_MILLISECOND_TIMER', 'Test - join timer', JOIN_AT),
                                               ('SET_MILLISECOND_TIMER', 'Test - attack timer', ATTACK_AT)]),
                  Script('Test - join', [('TIMER_EXPIRED', 'Test - join timer')],
                         [('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(f'child {j}').name, m.role(f'parent {j}').name)
                          for j in pairs]),
                  Script('Test - break', [('TIMER_EXPIRED', 'Test - attack timer')],
                         [('NAMED_ATTACK_NAMED', m.role(f'parent {j}').name, m.role(f'ice {j}').name) for j in pairs])]


def breach(m):
    m.drop_endings()
    t = Test()
    start(t, m)
    join(t, m, (1,))
    t.waypoints['Test Road Point'] = (m.site('gate 1')[0], m.site('convoy start')[1])
    # both men ordered out when the mech is sent, and again when ice 1 falls (as a player would)
    out = [('MOVE_NAMED_UNIT_TO', m.role(f'troop {k}-1').name, 'Test Road Point') for k in (1, 2)]
    t.scripts += [Script('Test - out', [('TIMER_EXPIRED', 'Test - attack timer')], out),
                  Script('Test - out again', [('NAMED_DESTROYED', m.role('ice 1').name)], out)]
    t.counters.append(('Test Ice 1', '1 号冰倒了'))
    t.scripts.append(Script('Test - ice 1', [('NAMED_DESTROYED', m.role('ice 1').name)],
                            [('SET_COUNTER', 'Test Ice 1', 1)]))
    counted('Test Ice 2', '2 号冰血量', t, health=m.role('ice 2').name)
    on_road(t, m, 'troop 1-1', '1 号的兵上路')
    on_road(t, m, 'troop 2-1', '2 号的兵上路')
    t.expect += [('1 号冰倒了', ATTACK_AT, 'ever==', 1), ('1 号的兵上路', ATTACK_AT, 'ever==', 1),
                 ('2 号冰血量', 0, '==', 100), ('2 号的兵上路', 0, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=75, every=3, sheet=False, lines=len(t.counters)))]
    return t


def play(m):
    t = Test()
    start(t, m)
    join(t, m, (1, 2))
    trucks = [m.role(f'truck {j}').name for j in (1, 2, 3)]
    for k in (1, 2):
        them = [r.name for p, r in m.cast.items() if p.startswith(f'troop {k}-')]
        t.scripts.append(Script(f'Test - tick {k}', [('NAMED_DESTROYED', m.role(f'ice {k}').name)],
                                [('SET_MILLISECOND_TIMER', f'Test - go timer {k}', 0.0)]))
        for j, target in enumerate(trucks):
            t.scripts.append(Script(f'Test - go {k} at {j + 1}',
                                    [('TIMER_EXPIRED', f'Test - go timer {k}'), ('NAMED_NOT_DESTROYED', target)] +
                                    [('NAMED_DESTROYED', a) for a in trucks[:j]],
                                    [('NAMED_ATTACK_NAMED', u, target) for u in them], once=False))
        t.scripts.append(Script(f'Test - go again {k}', [('TIMER_EXPIRED', f'Test - go timer {k}')],
                                [('SET_MILLISECOND_TIMER', f'Test - go timer {k}', 3.0)], once=False))
    counted('Test Trucks', '路上车辆数量', t, template=m.role('truck 1').template, player=m.player('s1'))
    leave = m.facts['convoy leaves']
    t.expect += [('路上车辆数量', 0, '==', 0, leave - 5), ('路上车辆数量', leave, 'ever==', 3), ('ENDED', leave, '', None)]
    t.bench = [('bench_watch', dict(seconds=leave + DRIVE - 8, every=3, sheet=False, lines=len(t.counters)))]
    return t


def lose(m):
    t = Test()
    start(t, m)
    for j in (1, 2):
        counted(f'Test Truck {j}', f'{j} 号车血量', t, health=m.role(f'truck {j}').name)
    leave = m.facts['convoy leaves']
    t.expect += [('1 号车血量', leave, '==', 100, leave + DRIVE - 10), ('ENDED', leave + DRIVE - 10, '', None)]
    t.bench = [('bench_watch', dict(seconds=leave + DRIVE + 20, every=3, sheet=False, lines=len(t.counters)))]
    return t
