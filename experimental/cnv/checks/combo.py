"""Combining mech tests. Counters: parents joined (CONTAINER_OCCUPIED), objects aboard something (ENCLOSED), the
child alive, the parent alive.

join: at JOIN_AT the child drives into the parent (joined, aboard), at PART_AT the parent lets it out (neither),
both alive throughout.
"""
from parts import Script, Test, counted, status
from units.combo import JOINED

JOIN_AT, PART_AT = 10.0, 30.0                   # well past the bench's uncertain start (see checks.beacon)


ATTACK_AT = 16.0


def breach(m):
    """At JOIN_AT pair A joins; at ATTACK_AT A's parent and both of B's are ordered at their walls. The map counts
    each wall's seconds standing from ATTACK_AT (ticks while it stands). A's wall falls; B's seconds tell how much
    slower the two apart are."""
    t = Test()
    t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                              ('SET_MILLISECOND_TIMER', 'Test - join timer', JOIN_AT),
                                              ('SET_MILLISECOND_TIMER', 'Test - attack timer', ATTACK_AT)]),
                  Script('Test - join', [('TIMER_EXPIRED', 'Test - join timer')],
                         [('NAMED_GARRISON_SPECIFIC_BUILDING', m.role('child A').name, m.role('parent A').name)]),
                  Script('Test - attack', [('TIMER_EXPIRED', 'Test - attack timer')],
                         [('NAMED_ATTACK_NAMED', m.role(p).name, m.role(f'wall {p[-1]}').name)
                          for p in ('parent A', 'parent B', 'child B')] +
                         [('SET_MILLISECOND_TIMER', 'Test - tick timer', 1.0)])]
    for k in 'AB':
        t.counters.append((f'Test Stand {k}', f'{k} 墙撑了几秒'))
        t.scripts.append(Script(f'Test - tick {k}', [('TIMER_EXPIRED', 'Test - tick timer'),
                                                     ('NAMED_NOT_DESTROYED', m.role(f'wall {k}').name)],
                                [('INCREMENT_COUNTER', 1, f'Test Stand {k}')], once=False))
    t.scripts.append(Script('Test - tick again', [('TIMER_EXPIRED', 'Test - tick timer')],
                            [('SET_MILLISECOND_TIMER', 'Test - tick timer', 1.0)], once=False))
    counted('Test Joined', '合体', t, status=status(JOINED))
    t.counters.append(('Test Fell A', 'A 墙倒了'))
    t.scripts.append(Script('Test - fell A', [('NAMED_DESTROYED', m.role('wall A').name)],
                            [('SET_COUNTER', 'Test Fell A', 1)]))
    # bench 2026-10-22: joined 5 s, the two apart 12 s
    t.expect += [('合体', JOIN_AT + 2, 'ever==', 1), ('A 墙倒了', ATTACK_AT, 'ever==', 1),
                 ('A 墙撑了几秒', ATTACK_AT + 12, '<=', 7), ('B 墙撑了几秒', ATTACK_AT, 'ever>=', 10)]
    t.bench = [('bench_watch', dict(seconds=75, every=3, sheet=False, lines=len(t.counters)))]
    return t


SEND_AT = 16.0


def spare(m):
    """At JOIN_AT pair A joins; at SEND_AT both enemy engineers walk up to 100 from their parent: A's (joined: a
    breaker, buildings only) is spared, B's (the parent alone, its plain beam) is shot."""
    t = Test()
    t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                              ('SET_MILLISECOND_TIMER', 'Test - join timer', JOIN_AT),
                                              ('SET_MILLISECOND_TIMER', 'Test - send timer', SEND_AT)]),
                  Script('Test - join', [('TIMER_EXPIRED', 'Test - join timer')],
                         [('NAMED_GARRISON_SPECIFIC_BUILDING', m.role('child A').name, m.role('parent A').name)]),
                  Script('Test - send', [('TIMER_EXPIRED', 'Test - send timer')],
                         [('MOVE_NAMED_UNIT_TO', m.role(f'enemy {k}').name, m.mark(f'near {k}')) for k in 'AB'])]
    counted('Test Joined', '合体', t, status=status(JOINED))
    for k in 'AB':
        counted(f'Test Enemy {k}', f'{k} 敌人血量', t, health=m.role(f'enemy {k}').name)
    t.expect += [('合体', JOIN_AT + 2, 'ever==', 1), ('A 敌人血量', 0, '==', 100), ('B 敌人血量', SEND_AT, 'ever<', 100)]
    t.bench = [('bench_watch', dict(seconds=45, every=3, sheet=False, lines=len(t.counters)))]
    return t


def join(m):
    t = Test()
    c, p = m.role('child'), m.role('parent')
    t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                              ('SET_MILLISECOND_TIMER', 'Test - join timer', JOIN_AT),
                                              ('SET_MILLISECOND_TIMER', 'Test - part timer', PART_AT)]),
                  Script('Test - join', [('TIMER_EXPIRED', 'Test - join timer')],
                         [('NAMED_GARRISON_SPECIFIC_BUILDING', c.name, p.name)]),
                  Script('Test - part', [('TIMER_EXPIRED', 'Test - part timer')],
                         [('NAMED_USE_COMMANDBUTTON_ABILITY', p.name, m.ability('parent', 'part'))])]
    counted('Test Joined', '合体', t, status=status(JOINED))
    counted('Test Aboard', '子体在内', t, status=status('ENCLOSED'))
    counted('Test Child', '子体', t, template=c.template)
    counted('Test Parent', '母体', t, template=p.template)
    t.expect += [('合体', 0, '==', 0, JOIN_AT - 2), ('合体', JOIN_AT, 'ever==', 1), ('子体在内', JOIN_AT, 'ever==', 1),
                 ('合体', PART_AT + 5, '==', 0), ('子体在内', PART_AT + 5, '==', 0), ('子体', 0, '==', 1),
                 ('母体', 0, '==', 1)]
    t.bench = [('bench_watch', dict(seconds=PART_AT + 12, every=2, sheet=False, lines=len(t.counters)))]
    return t
