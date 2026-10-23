"""Armoured train tests. At GO_AT the train is sent to stop 1; each time it is inside a stop's area it is sent on to
the next (the map's scripts drive it, as a mission would). Counters: the last stop reached, and (fight) the enemies
left and the train's health.

run: it follows the track, stop by stop, to the end.
fight: on the way it shoots the conscripts by the first leg, all of them, and still gets to the end.
"""
from parts import Script, Test, counted, square

GO_AT = 10.0
STOP = 60.0                                     # half-side of the area around each stop


def track(m, t):
    train = m.role('train').name
    stops = []
    while f'stop {len(stops) + 1}' in m.marks:
        stops.append(m.mark(f'stop {len(stops) + 1}'))
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - go timer', GO_AT)]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                            [('MOVE_NAMED_UNIT_TO', train, stops[0])]))
    t.counters.append(('Test Stop', '到了第几站'))
    for k, wp in enumerate(stops):
        area = f'Test Stop {k + 1}'
        t.areas[area] = square(*m.point(f'stop {k + 1}'), STOP)
        on = [('SET_COUNTER', 'Test Stop', k + 1)] + ([('MOVE_NAMED_UNIT_TO', train, stops[k + 1])]
                                                      if k + 1 < len(stops) else [])
        t.scripts.append(Script(f'Test - at stop {k + 1}', [('NAMED_INSIDE_AREA', train, area)], on))
    return len(stops)


def run(m):
    t = Test()
    n = track(m, t)
    t.expect += [('到了第几站', 0, '==', 0, GO_AT - 2), ('到了第几站', GO_AT, 'ever==', n)]
    t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=len(t.counters), until=f'c1=={n}'))]
    return t


def fight(m):
    t = Test()
    n = track(m, t)
    counted('Test Enemies', '敌方步兵', t, template=m.role('enemy').template, player=m.player('s1'))
    counted('Test Train Health', '列车血量', t, health=m.role('train').name)
    t.expect += [('敌方步兵', 0, 'ever==', 3), ('敌方步兵', GO_AT, 'ever==', 0), ('到了第几站', GO_AT, 'ever==', n)]
    t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=len(t.counters), until=f'c1=={n}'))]
    return t
