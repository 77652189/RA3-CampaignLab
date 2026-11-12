"""Ordinary VISION: enemy entry, friendly refusal and actual discovered markers.

Retail AlliedConstructionYard uses VISION/Duration=-1s/VisionObserver;
Amount defaults to zero and the default enter filter accepts enemy spies only.
Predict enemy spy consumed, yard stays full HP and owned by s1; ally refuses.
Near marker (700 north of yard) starts outside spy vision, inside yard shroud.
Far same-owner and third-player controls distinguish local from whole-side vision.
No map reveal: expected near discovered after entry; distant bits are measured,
not assumed. RADAR_FREEZE also exists on the retail yard and is outside scope.
Bench 2026-11-11: s1-s10 11100/11100/0; s11-s15 1100/11100/0;
s16-s37 1100/11100/1. Only local near marker is discovered. Five-second
activation delay is a sampled fit (INFERRED), not a measured engine mechanism.
"""
from parts import Script, Test, counted


def check(m):
    t = Test()
    p, ally = m.player('p1'), m.player('s2')
    t.scripts = [Script('Test - start', [], [
        ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
        ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend')),
        ('SET_MILLISECOND_TIMER', 'Vision enter', 10.0)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(role).name, 'NO_ATTACK', 1)
        for role in ('enemy', 'ally', 'enemy spy', 'ally spy', 'near', 'far', 'control')]),
        Script('Test - enter', [('TIMER_EXPIRED', 'Vision enter')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(role + ' spy').name, m.role(role).name)
            for role in ('enemy', 'ally')])]
    for role, side in (('enemy', 's1'), ('ally', 's2')):
        c = 'Vision ' + role
        counted(c, role, t, health=m.role(role).name)
        for label, cond, value in (
                ('owner', ('NAMED_OWNED_BY_PLAYER', m.player(side), m.role(role).name), 1000),
                ('spy', ('NAMED_NOT_DESTROYED', m.role(role + ' spy').name), 10000)):
            t.scripts.append(Script('Test - ' + role + label, [cond],
                                    [('INCREMENT_COUNTER', value, c)], once=False))
    c = 'Vision seen'
    t.counters.append((c, 'vision'))
    t.scripts.append(Script('Test - reset seen', [], [('SET_COUNTER', c, 0)], once=False))
    for role, bit in (('near', 1), ('far', 10), ('control', 100)):
        t.scripts.append(Script('Test - seen ' + role,
                                [('NAMED_DISCOVERED', p, m.role(role).name)],
                                [('INCREMENT_COUNTER', bit, c)], once=False))
    t.expect = [('enemy', 0, '==', 11100, 7), ('enemy', 18, '==', 1100),
                ('ally', 0, '==', 11100), ('vision', 0, '==', 0, 7),
                ('vision', 12, '==', 0, 14), ('vision', 18, '==', 1)]
    t.bench = [('bench_watch', dict(seconds=35, every=1, sheet=False, lines=3))]
    return t


def check_soviet(m):
    """b: Soviet yard shares the retail ordinary VISION include with Allied yard.

    Predict the same enemy consumption, unchanged HP/owner, friendly refusal,
    and local-only discovered marker; preserve a's timing windows and controls.
    Radar freeze, exact timing and observer cleanup remain outside this slice.
    Bench: s1-s10 11100/11100/0; s11-s17 1100/11100/0;
    s18-s38 1100/11100/1. First discovery differs from a; no timing fit added.
    """
    for role in ('enemy', 'ally'):
        yard = m.role(role)
        yard.template = 'SovietConstructionYard'
        m.find(yard.name).template = yard.template
    return check(m)


CHECKS = {'engine_infvis': {'a': check, 'b': check_soviet}}
