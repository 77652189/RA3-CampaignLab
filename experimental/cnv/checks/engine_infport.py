"""E201 independent port VISION: full retail signature, no module override.

Predict enemy spy consumed, ally refused, original owners/full HP, second spy
alive after 25s entry order. Near same-owner and third-owner markers within
600, far marker outside: predict 0 before entry and 101 in the late window.
Nine alive/owner/inside-40 marker bits must remain 511. Read visibility with
exclusive SETs. Exact entry/observer timing and blocking expiry remain gaps.
See work/re/e201_port.md; no original four-lane run is repeated.
"""
from parts import NOT, Script, Test, counted, square


def check(m):
    t = Test()
    p, ally = m.player('p1'), m.player('s5')
    t.scripts = [Script('Test - start', [], [
        ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
        ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend')),
        ('SET_MILLISECOND_TIMER', 'Port entry', 10.0),
        ('SET_MILLISECOND_TIMER', 'Port second', 25.0)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', obj.name, 'NO_ATTACK', 1) for obj in m.objects] + [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(role).name, 'IMMOBILE_ALLOW_ROTATE', 1)
        for role in ('match', 'wrong', 'third')]),
        Script('Test - enter', [('TIMER_EXPIRED', 'Port entry')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(role + ' spy').name, m.role(role).name)
            for role in ('enemy', 'ally')]),
        Script('Test - second', [('TIMER_EXPIRED', 'Port second')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role('second').name, m.role('enemy').name)])]
    for role, side in (('enemy', 's4'), ('ally', 's5')):
        c = 'Port ' + role
        counted(c, role, t, health=m.role(role).name)
        for label, cond, weight in (
                ('owner', ('NAMED_OWNED_BY_PLAYER', m.player(side), m.role(role).name), 1000),
                ('spy', ('NAMED_NOT_DESTROYED', m.role(role + ' spy').name), 10000)):
            t.scripts.append(Script('Test - ' + role + label, [cond],
                                    [('INCREMENT_COUNTER', weight, c)], once=False))
    t.scripts.append(Script('Test - second alive', [('NAMED_NOT_DESTROYED', m.role('second').name)],
                            [('INCREMENT_COUNTER', 100000, 'Port enemy')], once=False))
    t.counters.append(('Port discovery', 'seen'))
    for mask in range(8):
        conditions, value = [], 0
        for index, (role, weight) in enumerate((('match', 1), ('wrong', 10), ('third', 100))):
            cond = ('NAMED_DISCOVERED', p, m.role(role).name)
            found = bool(mask & (1 << index))
            conditions.append(cond if found else cond + (NOT,))
            value += weight if found else 0
        t.scripts.append(Script('Test - discovery ' + str(mask), conditions,
                                [('SET_COUNTER', 'Port discovery', value)], once=False))
    c = 'Port identity'
    t.counters.append((c, 'identity'))
    t.scripts.append(Script('Test - reset identity', [], [('SET_COUNTER', c, 0)], once=False))
    for index, role in enumerate(('match', 'wrong', 'third')):
        obj = m.role(role)
        area = 'Port position ' + role
        placed = next(o for o in m.objects if o.name == obj.name)
        t.areas[area] = square(placed.x, placed.y, 40)
        for bit, cond in enumerate((('NAMED_NOT_DESTROYED', obj.name),
                                    ('NAMED_OWNED_BY_PLAYER', m.player(obj.side), obj.name),
                                    ('NAMED_INSIDE_AREA', obj.name, area))):
            t.scripts.append(Script(f'Test - identity {index} {bit}', [cond],
                                    [('INCREMENT_COUNTER', 1 << (3*index + bit), c)], once=False))
    t.expect = [('enemy', 1, '==', 111100, 7), ('enemy', 20, '==', 101100, 40),
                ('ally', 1, '==', 11100, 35), ('seen', 1, '==', 0, 7),
                ('seen', 20, '==', 101, 40), ('identity', 1, '==', 511, 35)]
    t.bench = [('bench_watch', dict(seconds=40, every=1, sheet=False, lines=4))]
    return t


def no_first(m):
    """b: same second spy/order without a previous hostile infiltration.

    Predict second consumed after 25s, first spy remains, near discovery=101.
    This distinguishes blocked repeat from an invalid second-spy entry order.
    """
    t = check(m)
    t.scripts[1].do = [t.scripts[1].do[1]]  # Keep friendly control, omit hostile first.
    t.expect = [('enemy', 1, '==', 111100, 22), ('enemy', 32, '==', 11100, 40),
                ('ally', 1, '==', 11100, 40), ('seen', 1, '==', 0, 22),
                ('seen', 32, '==', 101, 40), ('identity', 1, '==', 511, 40)]
    return t


CHECKS = {'engine_infport': {'a': check, 'b': no_first}}
