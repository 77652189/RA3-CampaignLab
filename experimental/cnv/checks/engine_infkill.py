"""E138 KILL entry, not fling geometry or full module acceptance.

Retail SovietCrane includes Effect=KILL, Amount=1.5 and an empty infiltration
EVA event. The include describes Amount as a fling-distance multiplier.
Predict the hostile spy dies, the friendly spy is refused and survives, and
both cranes retain full health and their original owners. Entry reach and
exact timing are INFERRED; fling distance, death effects and repeat entry gap.
Bench: s1..10 enemy/ally=11100/11100; s11..31=1100/11100 (3/3 PASS).
These are survival/HP/owner counters, not a death-animation measurement.
"""
from parts import Script, Test, counted


def check(m):
    t = Test()
    p, ally = m.player('p1'), m.player('s2')
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', p),
        ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
        ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend')),
        ('SET_MILLISECOND_TIMER', 'Kill enter', 10.0)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(role).name, 'NO_ATTACK', 1)
        for role in ('enemy', 'ally', 'enemy spy', 'ally spy')]),
        Script('Test - enter', [('TIMER_EXPIRED', 'Kill enter')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(role + ' spy').name,
             m.role(role).name) for role in ('enemy', 'ally')])]
    for role, side in [('enemy', 's1'), ('ally', 's2')]:
        counter = 'Kill ' + role
        counted(counter, role, t, health=m.role(role).name)
        for label, condition, value in [
                ('owner', ('NAMED_OWNED_BY_PLAYER', m.player(side), m.role(role).name), 1000),
                ('spy', ('NAMED_NOT_DESTROYED', m.role(role + ' spy').name), 10000)]:
            t.scripts.append(Script('Test - ' + role + label, [condition],
                                    [('INCREMENT_COUNTER', value, counter)], once=False))
    t.expect = [('enemy', 1, '==', 11100, 7), ('enemy', 18, '==', 1100, 30),
                ('ally', 1, '==', 11100, 30)]
    t.bench = [('bench_watch', dict(seconds=30, every=1, sheet=False, lines=2))]
    return t


CHECKS = {'engine_infkill': {'a': check}}
