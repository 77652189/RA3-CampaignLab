"""Paper crane tests (no map reveal: the shroud is the point). At GO_AT the scout is sent to the stop point, 700
short of an enemy Guardian in the shroud.

spot: the crane gets there and the Guardian is discovered (a latch: NAMED_DISCOVERED for the player).
blind (with retail's Twinblade, the control): it gets there, the Guardian stays undiscovered.
"""
from parts import Script, Test, counted, square

GO_AT = 10.0
STOP = 100.0                                    # half-side of the area around the stop point


def trip(m, seen):
    t = Test()
    scout, target = m.role('scout').name, m.role('target').name
    t.scripts.append(Script('Test - start', [], [('SET_MILLISECOND_TIMER', 'Test - go timer', GO_AT)]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                            [('MOVE_NAMED_UNIT_TO', scout, m.mark('stop'))]))
    t.areas['Test Stop'] = square(*m.point('stop'), STOP)
    t.counters.append(('Test Seen', '发现目标'))
    t.scripts.append(Script('Test - seen', [('NAMED_DISCOVERED', m.player('p1'), target)],
                            [('SET_COUNTER', 'Test Seen', 1)]))
    counted('Test There', '到达', t, named=scout, area='Test Stop')
    t.expect += [('发现目标', 0, '==', 0, GO_AT - 2), ('到达', GO_AT, 'ever==', 1),
                 ('发现目标', GO_AT, 'ever==' if seen else '==', 1 if seen else 0)]
    t.bench = [('bench_watch', dict(seconds=45, every=3, sheet=False, lines=len(t.counters)))]
    return t


def hide(m):
    """At GO_AT both cranes are sent over their IFVs: A (no detector there) comes through untouched, B (a war bear
    with its IFVs) is hit."""
    t = Test()
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - go timer', GO_AT)]))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                            [('MOVE_NAMED_UNIT_TO', m.role(f'crane {k}').name, m.mark(f'over {k}')) for k in 'AB']))
    for k in 'AB':
        counted(f'Test Crane {k}', f'{k} 纸鹤血量', t, health=m.role(f'crane {k}').name)
    t.expect += [('A 纸鹤血量', 0, '==', 100), ('B 纸鹤血量', GO_AT, 'ever<', 100)]
    t.bench = [('bench_watch', dict(seconds=40, every=3, sheet=False, lines=len(t.counters)))]
    return t


def spot(m):
    return trip(m, True)


def blind(m):
    return trip(m, False)
