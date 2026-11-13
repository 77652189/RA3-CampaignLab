"""E128: PARALYZE=30s, exact retail template filter, existing-unit controls.

Prediction before running: enemy spy consumed, allied spy refused, HP/owner
unchanged. Same-owner Mirage is PARALYZED for about thirty seconds; same-owner
Guardian and third-owner Mirage stay clear. Exact arrival/expiry INFERRED.
Only this host and these existing ground units are probed, not production.
E128 a/b: spy consumption from s11, both hosts retain HP/owner, all queried
PARALYZED model bits remain zero. b arrivals=110 at s21..44, 111 at s45..60.
The original model-bit prediction below remains a known failed diagnostic;
movement supports a real pause without the queried visual condition.
"""
from parts import Script, Test, counted


def check(m):
    t = Test()
    p, ally = m.player('p1'), m.player('s2')
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', p),
        ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
        ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend')),
        ('SET_MILLISECOND_TIMER', 'Paralyze enter', 10.0)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(role).name, 'NO_ATTACK', 1)
        for role in ('enemy', 'ally', 'enemy spy', 'ally spy', 'included', 'excluded', 'third')]),
        Script('Test - budget', [], [('PLAYER_SET_MONEY', m.player(side), 0)
                                    for side in ('s1', 's2', 's3')], once=False),
        Script('Test - enter', [('TIMER_EXPIRED', 'Paralyze enter')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(role + ' spy').name, m.role(role).name)
            for role in ('enemy', 'ally')])]
    for role, side in [('enemy', 's1'), ('ally', 's2')]:
        counter = 'Paralyze ' + role
        counted(counter, role, t, health=m.role(role).name)
        for label, condition, value in [
                ('owner', ('NAMED_OWNED_BY_PLAYER', m.player(side), m.role(role).name), 1000),
                ('spy', ('NAMED_NOT_DESTROYED', m.role(role + ' spy').name), 10000)]:
            t.scripts.append(Script('Test - ' + role + label, [condition],
                                    [('INCREMENT_COUNTER', value, counter)], once=False))
    counter = 'Paralyze bits'
    t.counters.append((counter, 'paralyzed'))
    t.scripts.append(Script('Test - clear bits', [], [('SET_COUNTER', counter, 0)], once=False))
    for role, bit in [('included', 1), ('excluded', 10), ('third', 100)]:
        t.scripts.append(Script('Test - bit ' + role,
                                [('UNIT_HAS_MODELCONDITION', m.role(role).name, 'PARALYZED')],
                                [('INCREMENT_COUNTER', bit, counter)], once=False))
    t.expect = [('enemy', 1, '==', 11100, 7), ('ally', 1, '==', 11100, 50),
                ('enemy', 18, '==', 1100, 50), ('paralyzed', 1, '==', 0, 7),
                ('paralyzed', 18, '==', 1, 35), ('paralyzed', 46, '==', 0, 50)]
    t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=3))]
    return t


CHECKS = {'engine_infpara': {'a': check}}


def movement_check(m):
    """Second discriminator: order all controls 400 units north at s18.

    If PARALYZE blocks movement, only excluded/third arrive by s30 (110),
    included arrives after recovery by s50 (111). Travel windows INFERRED;
    equal movement with zero model bits leaves the entry effect unresolved.
    """
    t = check(m)
    t.scripts[0].do.append(('SET_MILLISECOND_TIMER', 'Paralyze move', 18.0))
    orders = []
    counter = 'Paralyze arrivals'
    t.counters.append((counter, 'arrived'))
    t.scripts.append(Script('Test - clear arrival', [], [('SET_COUNTER', counter, 0)], once=False))
    x, y = m.site('removed gun')
    for role, offset, bit in [('included', -100, 1), ('excluded', 100, 10), ('third', 300, 100)]:
        point = 'Paralyze goal ' + role
        gx, gy = x + offset, y + 400
        t.waypoints[point] = (gx, gy)
        t.areas[point] = [(gx-60, gy-60), (gx+60, gy-60), (gx+60, gy+60), (gx-60, gy+60)]
        orders += m.order('move', [m.role(role).name], point, crew='Para' + role)
        t.scripts.append(Script('Test - arrive ' + role,
                                [('NAMED_INSIDE_AREA', m.role(role).name, point)],
                                [('INCREMENT_COUNTER', bit, counter)], once=False))
    t.scripts.append(Script('Test - move', [('TIMER_EXPIRED', 'Paralyze move')], orders))
    t.expect += [('arrived', 1, '==', 0, 15), ('arrived', 30, '==', 110, 35),
                 ('arrived', 48, '==', 111, 50)]
    t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=4))]
    return t


CHECKS['engine_infpara']['b'] = movement_check
