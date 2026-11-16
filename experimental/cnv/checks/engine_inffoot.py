"""E198 infantry VISION_UNITS, independent of the paused four-lane map.

Prediction: hostile spy consumed, friendly refused, full HP/original owners;
existing matching infantry discovered, separated wrong-kind/third-side hidden.
Discovery is read with mutually exclusive SETs, not reset/increment sampling.
Fourth row publishes nine independent alive/owner/inside-40 predicates for the
three markers, all-pass=511. A held marker still needs its position predicate.
Exact observer clock, lifetime and expiry are not predicted. See work/re/e198_infantry.md.
"""
from parts import NOT, Script, Test, counted, square


def check(m):
    t = Test()
    p, ally = m.player('p1'), m.player('s5')
    t.scripts = [Script('Test - start', [], [
        ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
        ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend')),
        ('SET_MILLISECOND_TIMER', 'Infantry entry', 10.0)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', obj.name, 'NO_ATTACK', 1) for obj in m.objects] + [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(role).name, 'IMMOBILE_ALLOW_ROTATE', 1)
        for role in ('match', 'wrong', 'third')]),
        Script('Test - enter', [('TIMER_EXPIRED', 'Infantry entry')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(role + ' spy').name, m.role(role).name)
            for role in ('enemy', 'ally')])]
    for role, side in (('enemy', 's2'), ('ally', 's5')):
        c = 'Infantry ' + role
        counted(c, role, t, health=m.role(role).name)
        for label, cond, weight in (
                ('owner', ('NAMED_OWNED_BY_PLAYER', m.player(side), m.role(role).name), 1000),
                ('spy', ('NAMED_NOT_DESTROYED', m.role(role + ' spy').name), 10000)):
            t.scripts.append(Script('Test - ' + role + label, [cond],
                                    [('INCREMENT_COUNTER', weight, c)], once=False))
    t.counters.append(('Infantry discovery', 'seen'))
    for mask in range(8):
        conditions, value = [], 0
        for index, (role, weight) in enumerate((('match', 1), ('wrong', 10), ('third', 100))):
            cond = ('NAMED_DISCOVERED', p, m.role(role).name)
            found = bool(mask & (1 << index))
            conditions.append(cond if found else cond + (NOT,))
            value += weight if found else 0
        t.scripts.append(Script('Test - discovery ' + str(mask), conditions,
                                [('SET_COUNTER', 'Infantry discovery', value)], once=False))
    c = 'Infantry identity'
    t.counters.append((c, 'identity'))
    t.scripts.append(Script('Test - reset identity', [], [('SET_COUNTER', c, 0)], once=False))
    for index, role in enumerate(('match', 'wrong', 'third')):
        obj = m.role(role)
        area = 'Infantry position ' + role
        t.areas[area] = square(*m.site(obj.site), 40)
        for bit, cond in enumerate((('NAMED_NOT_DESTROYED', obj.name),
                                    ('NAMED_OWNED_BY_PLAYER', m.player(obj.side), obj.name),
                                    ('NAMED_INSIDE_AREA', obj.name, area))):
            t.scripts.append(Script(f'Test - identity {index} {bit}', [cond],
                                    [('INCREMENT_COUNTER', 1 << (3*index + bit), c)], once=False))
    t.expect = [('enemy', 1, '==', 11100, 7), ('enemy', 20, '==', 1100, 35),
                ('ally', 1, '==', 11100, 35), ('seen', 1, '==', 0, 7),
                ('seen', 20, '==', 1, 35), ('identity', 1, '==', 511, 35)]
    t.bench = [('bench_watch', dict(seconds=40, every=1, sheet=False, lines=4))]
    return t


def no_hostile_entry(m):
    """E198 final contrast: same objects, no hostile spy entry order.

    Predict both spies alive and all discovery bits zero. This distinguishes
    entry-driven discovery from unrelated baseline vision, without fitting
    the first run's intermittent observer or wall-clock timestamps.
    """
    t = check(m)
    t.scripts[1].do = t.scripts[1].do[1:]
    t.expect = [('enemy', 1, '==', 11100, 35), ('ally', 1, '==', 11100, 35),
                ('seen', 1, '==', 0, 35), ('identity', 1, '==', 511, 35)]
    return t


CHECKS = {'engine_inffoot': {'a': check, 'b': no_hostile_entry}}
