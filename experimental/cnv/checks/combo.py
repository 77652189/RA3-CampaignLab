"""Combining mech tests. Counters: parents joined (CONTAINER_OCCUPIED), objects aboard something (ENCLOSED), the
child alive, the parent alive.

join: at JOIN_AT the child drives into the parent (joined, aboard), at PART_AT the parent lets it out (neither),
both alive throughout.
"""
from parts import Script, Test, counted, status
from units.combo import JOINED

JOIN_AT, PART_AT = 10.0, 30.0                   # well past the bench's uncertain start (see checks.beacon)


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
