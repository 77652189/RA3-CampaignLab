"""Armoured train tests. From GO_AT, once a second, the train is sent to the next stop it has not reached (the map's
scripts drive it, as a mission would: a move order of anyone else's -- the player's -- lasts a second at most); each
stop's area, once it is in it, makes the next one the goal. Counters: the last stop reached, the seconds on the way
(counted by the same once-a-second script, until the last stop), and (fight) the enemies left and the train's
health.

run: it follows the track, stop by stop, to the end.
fight: on the way it shoots the conscripts by the first leg, all of them, and still gets to the end.
brake: the brake on from BRAKE_AT to RELEASE_AT: the trip takes about that much longer.
astray: at ASTRAY_AT it is ordered off the track (as a player might): it is back on its way, the trip as long as run's.
"""
from parts import Script, Test, counted, square

GO_AT = 10.0
STOP = 60.0                                     # half-side of the area around each stop
BRAKE_AT, RELEASE_AT, ASTRAY_AT = 15.0, 25.0, 15.0
RUN_TRIP = 26                                   # run's seconds on the way (bench 2026-10-22)


def track(m, t):
    train = m.role('train').name
    stops = []
    while f'stop {len(stops) + 1}' in m.marks:
        stops.append(m.mark(f'stop {len(stops) + 1}'))
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - go timer', GO_AT)]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                            [('MOVE_NAMED_UNIT_TO', train, stops[0]),
                             ('SET_MILLISECOND_TIMER', 'Test - route timer', 1.0)]))
    t.counters += [('Test Stop', '到了第几站'), ('Test Trip', '行驶秒数')]
    for k, wp in enumerate(stops):              # before 'again': it pushes the timer on
        t.scripts.append(Script(f'Test - route {k + 1}', [('TIMER_EXPIRED', 'Test - route timer'),
                                                          ('COUNTER', 'Test Stop', 2, k)],
                                [('MOVE_NAMED_UNIT_TO', train, wp), ('INCREMENT_COUNTER', 1, 'Test Trip')],
                                once=False))
    t.scripts.append(Script('Test - route again', [('TIMER_EXPIRED', 'Test - route timer')],
                            [('SET_MILLISECOND_TIMER', 'Test - route timer', 1.0)], once=False))
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
    t.bench = [('bench_watch', dict(seconds=70, every=3, sheet=False, lines=len(t.counters), until=f'c1=={n}'))]
    return t


def fight(m):
    t = Test()
    n = track(m, t)
    counted('Test Enemies', '敌方步兵', t, template=m.role('enemy').template, player=m.player('s1'))
    counted('Test Train Health', '列车血量', t, health=m.role('train').name)
    t.expect += [('敌方步兵', 0, 'ever==', 3), ('敌方步兵', GO_AT, 'ever==', 0), ('到了第几站', GO_AT, 'ever==', n)]
    t.bench = [('bench_watch', dict(seconds=70, every=3, sheet=False, lines=len(t.counters), until=f'c1=={n}'))]
    return t


def brake(m):
    t = run(m)
    train = m.role('train').name
    t.scripts += [Script('Test - brake timers', [], [('SET_MILLISECOND_TIMER', 'Test - brake timer', BRAKE_AT),
                                                     ('SET_MILLISECOND_TIMER', 'Test - release timer', RELEASE_AT)]),
                  Script('Test - brake', [('TIMER_EXPIRED', 'Test - brake timer')],
                         [('NAMED_USE_COMMANDBUTTON_ABILITY', train, m.ability('train', 'brake'))]),
                  Script('Test - release', [('TIMER_EXPIRED', 'Test - release timer')],
                         [('NAMED_USE_COMMANDBUTTON_ABILITY', train, m.ability('train', 'brake'))])]
    if RUN_TRIP:
        t.expect.append(('行驶秒数', GO_AT, 'ever>=', RUN_TRIP + int(RELEASE_AT - BRAKE_AT) - 3))
    t.bench = [('bench_watch', dict(seconds=90, every=3, sheet=False, lines=len(t.counters), until='c1==3'))]
    return t


def astray(m):
    t = run(m)
    t.scripts += [Script('Test - astray timer', [], [('SET_MILLISECOND_TIMER', 'Test - astray timer', ASTRAY_AT)]),
                  Script('Test - astray', [('TIMER_EXPIRED', 'Test - astray timer')],
                         [('MOVE_NAMED_UNIT_TO', m.role('train').name, m.mark('astray'))])]
    if RUN_TRIP:
        t.expect.append(('行驶秒数', GO_AT + 4, '<=', RUN_TRIP + 3))
    return t


def braked_fire(m):
    """Braked at BRAKE_AT; at SEND_AT the conscripts walk up to 150 from it and it is sent to stop 1: it stays
    where it is (inside its start's area) and shoots them all."""
    t = Test()
    train = m.role('train').name
    send = BRAKE_AT + 3
    t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                              ('SET_MILLISECOND_TIMER', 'Test - brake timer', BRAKE_AT),
                                              ('SET_MILLISECOND_TIMER', 'Test - send timer', send)]),
                  Script('Test - brake', [('TIMER_EXPIRED', 'Test - brake timer')],
                         [('NAMED_USE_COMMANDBUTTON_ABILITY', train, m.ability('train', 'brake'))]),
                  Script('Test - send', [('TIMER_EXPIRED', 'Test - send timer')],
                         [('MOVE_NAMED_UNIT_TO', e.name, m.mark('by start')) for e in m.roles('enemy')] +
                         [('MOVE_NAMED_UNIT_TO', train, m.mark('stop 1'))])]
    t.areas['Test Start'] = square(*m.point('start'), STOP)
    counted('Test Home', '还在起点', t, named=train, area='Test Start')
    counted('Test Enemies', '敌方步兵', t, template=m.role('enemy 1').template, player=m.player('s1'))
    t.expect += [('还在起点', 0, '==', 1), ('敌方步兵', send, 'ever==', 0)]
    t.bench = [('bench_watch', dict(seconds=45, every=3, sheet=False, lines=len(t.counters)))]
    return t
