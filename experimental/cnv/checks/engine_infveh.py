"""VISION_UNITS: test existing vehicles against infantry and third-side controls.

Retail AlliedWarFactory inherits BaseStructure and includes the vehicle rule:
Duration=UnitDuration=30s, UnitFilter=VEHICLE, ObjectRef=UnitVisionObserver.
Hypothesis (unverified): existing same-owner vehicles are revealed globally.
Predict enemy consumed, friendly refused, both factories full HP/unchanged owner;
discovery bits vehicle/infantry/third = 1/0/0 after entry. No timing/expiry claim.
If the existing vehicle stays hidden, production-only application remains a gap.
Bench E77: enemy consumed from s10, ally remains 11100 throughout. Discovery
is intermittent: s10-s16=1, s18=0, s19-s25=1, s26-s27=0, s28-s29=1,
s30=0, s32=1, s33=0, s34-s38=1. Original continuous window FAIL retained.
Only vehicle bit appears; exact observer scheduling/expiry remain unexplained.
"""
from parts import Script, Test, counted


def check(m):
    t = Test()
    p, ally = m.player('p1'), m.player('s2')
    t.scripts = [Script('Test - start', [], [
        ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
        ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend')),
        ('SET_MILLISECOND_TIMER', 'Vehicle enter', 10.0)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(role).name, 'NO_ATTACK', 1)
        for role in ('enemy', 'ally', 'enemy spy', 'ally spy', 'vehicle', 'infantry', 'third')]),
        Script('Test - enter', [('TIMER_EXPIRED', 'Vehicle enter')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(role + ' spy').name, m.role(role).name)
            for role in ('enemy', 'ally')])]
    for role, side in (('enemy', 's1'), ('ally', 's2')):
        c = 'Vehicle ' + role
        counted(c, role, t, health=m.role(role).name)
        for label, cond, value in (
                ('owner', ('NAMED_OWNED_BY_PLAYER', m.player(side), m.role(role).name), 1000),
                ('spy', ('NAMED_NOT_DESTROYED', m.role(role + ' spy').name), 10000)):
            t.scripts.append(Script('Test - ' + role + label, [cond],
                                    [('INCREMENT_COUNTER', value, c)], once=False))
    c = 'Vehicle seen'
    t.counters.append((c, 'seen'))
    t.scripts.append(Script('Test - reset seen', [], [('SET_COUNTER', c, 0)], once=False))
    for role, bit in (('vehicle', 1), ('infantry', 10), ('third', 100)):
        t.scripts.append(Script('Test - seen ' + role,
                                [('NAMED_DISCOVERED', p, m.role(role).name)],
                                [('INCREMENT_COUNTER', bit, c)], once=False))
    t.expect = [('enemy', 0, '==', 11100, 7), ('enemy', 20, '==', 1100),
                ('ally', 0, '==', 11100), ('seen', 0, '==', 0, 7),
                ('seen', 20, '==', 1, 30)]
    t.bench = [('bench_watch', dict(seconds=35, every=1, sheet=False, lines=3))]
    return t


CHECKS = {'engine_infveh': {'a': check}}
