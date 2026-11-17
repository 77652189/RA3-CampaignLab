"""E138 KILL entry, not fling geometry or full module acceptance.

Retail SovietCrane includes Effect=KILL, Amount=1.5 and an empty infiltration
EVA event. The include describes Amount as a fling-distance multiplier.
Predict the hostile spy dies, the friendly spy is refused and survives, and
both cranes retain full health and their original owners. Entry reach and
exact timing are INFERRED; fling distance, death effects and repeat entry gap.
Bench: s1..10 enemy/ally=11100/11100; s11..31=1100/11100 (3/3 PASS).
These are survival/HP/owner counters, not a death-animation measurement.
"""
from parts import Script, Test, counted, square


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


def credit_check(m):
    """E205 diagnostic: hostile entry/refusal plus independent kill credit.

    Predict the hostile crane owner receives named kill credit (1); neither
    the spy owner nor friendly crane owner does (10/100). This prediction
    does not measure fling, death-animation or internal dispatch directly.
    MEASURED E205 b: s1..47=11100/11100/0; no accepted entry observed.
    """
    t = check(m)
    counter = 'Kill credit'
    t.counters.append((counter, 'credit'))
    t.scripts.append(Script('Test - credit reset', [],
                            [('SET_COUNTER', counter, 0)], once=False))
    for side, weight in [('s1', 1), ('p1', 10), ('s2', 100)]:
        t.scripts.append(Script('Test - credit ' + side,
            [('PLAYER_HAS_KILLED_NAMED_UNIT', m.player(side), m.role('enemy spy').name)],
            [('INCREMENT_COUNTER', weight, counter)], once=False))
    t.expect.append(('credit', 18, '==', 1, 30))
    t.bench = [('bench_watch', dict(seconds=30, every=1, sheet=False, lines=3))]
    return t


def phase_check(m):
    """E205 second run distinguishes script dispatch from approach/entry.

    Predict phase=111: start=1, enter-command dispatched=10, hostile spy has
    reached the host's inner 40-unit square=100. Region uses the mission's
    published host position. b's original expectations remain unchanged.
    MEASURED E205 c: s1..34=11100/11100/0/1, s36..45=11100/11100/0/11,
    s46..52=1100/11100/1/111. Original early-window prediction FAIL; only
    final player kill credit is established, not fling or death dispatch.
    """
    t = credit_check(m)
    counter, area = 'Kill phase', 'Kill approach'
    host = m.role('enemy')
    placed = next(obj for obj in m.objects if obj.name == host.name)
    t.areas[area] = square(placed.x, placed.y, 40)
    t.counters.append((counter, 'phase'))
    t.scripts[0].do.append(('SET_COUNTER', counter, 1))
    t.scripts[1].do.append(('INCREMENT_COUNTER', 10, counter))
    t.scripts.append(Script('Test - approach latch',
        [('NAMED_INSIDE_AREA', m.role('enemy spy').name, area)],
        [('INCREMENT_COUNTER', 100, counter)]))
    t.expect.append(('phase', 18, '==', 111, 30))
    t.bench = [('bench_watch', dict(seconds=30, every=1, sheet=False, lines=4))]
    return t


CHECKS = {'engine_infkill': {'a': check, 'b': credit_check, 'c': phase_check}}
