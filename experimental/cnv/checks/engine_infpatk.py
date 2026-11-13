"""E139: fixed pre-entry, paused and recovered attack trials.

Prediction from retail 30s PARALYZE and explicit Mirage filter: all three
isolated factory targets take nonlethal damage in the s2..6 baseline.
Enter at s10; reset target HP at s17; attack s18..24: only the same-owner
Mirage target stays full. Reset at s45; attack s46..52: all take damage.
These windows are fixed before the bench; exact entry/expiry INFERRED.
Each trial issues a new named attack, so retained orders are not measured.
Bench a: 20/20 PASS. Stable target HP: baseline 76/95/76,
pause 100/92/68, recovery 68/92/68; all targets alive. Entry bits
111111 before, 111011 after. Raw samples: work/re/e139_paralyze_attack.md.
"""
from parts import Script, Test, counted


def check(m):
    t = Test()
    roles = ('included', 'excluded', 'third')
    quiet = ('enemy', 'ally', 'enemy spy', 'ally spy') + roles + tuple(r + ' target' for r in roles)
    timers = [('enter', 10), ('reset pause', 17), ('reset recovery', 45),
              ('baseline', 2), ('baseline stop', 6), ('pause', 18),
              ('pause stop', 24), ('recovery', 46), ('recovery stop', 52)]
    p, ally = m.player('p1'), m.player('s2')
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', p),
        ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
        ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend'))] + [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(role).name, 'NO_ATTACK', 1) for role in quiet] + [
        ('SET_MILLISECOND_TIMER', 'Attack ' + name, float(at)) for name, at in timers]),
        Script('Test - budget', [], [('PLAYER_SET_MONEY', m.player(side), 0)
                                    for side in ('p1', 's1', 's2', 's3')], once=False),
        Script('Test - enter', [('TIMER_EXPIRED', 'Attack enter')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(role + ' spy').name,
             m.role(role).name) for role in ('enemy', 'ally')])]
    for phase in ('reset pause', 'reset recovery'):
        t.scripts.append(Script('Test - ' + phase, [('TIMER_EXPIRED', 'Attack ' + phase)], [
            ('UNIT_SET_HEALTH', m.role(role + ' target').name, 100.0) for role in roles]))
    for phase in ('baseline', 'pause', 'recovery'):
        actions = []
        for role in roles:
            actions += [('UNIT_CHANGE_OBJECT_STATUS', m.role(role).name, 'NO_ATTACK', 0),
                        ('NAMED_ATTACK_NAMED', m.role(role).name, m.role(role + ' target').name)]
        t.scripts += [Script('Test - ' + phase, [('TIMER_EXPIRED', 'Attack ' + phase)], actions),
                      Script('Test - ' + phase + ' stop', [('TIMER_EXPIRED', 'Attack ' + phase + ' stop')], [
                          ('UNIT_CHANGE_OBJECT_STATUS', m.role(role).name, 'NO_ATTACK', 1) for role in roles])]
    counter = 'Attack entry'
    t.counters.append((counter, 'entry'))
    t.scripts.append(Script('Test - entry zero', [], [('SET_COUNTER', counter, 0)], once=False))
    for role, side, scale in [('enemy', 's1', 1), ('ally', 's2', 1000)]:
        for label, condition, value in [
                ('full', ('UNIT_HEALTH', m.role(role).name, 2, 100), 1),
                ('owner', ('NAMED_OWNED_BY_PLAYER', m.player(side), m.role(role).name), 10),
                ('spy', ('NAMED_NOT_DESTROYED', m.role(role + ' spy').name), 100)]:
            t.scripts.append(Script('Test - ' + role + label, [condition],
                                    [('INCREMENT_COUNTER', value * scale, counter)], once=False))
    for role in roles:
        counter = 'Attack HP ' + role
        counted(counter, role, t, health=m.role(role + ' target').name)
        t.scripts.append(Script('Test - target alive ' + role,
                                [('NAMED_NOT_DESTROYED', m.role(role + ' target').name)],
                                [('INCREMENT_COUNTER', 1000, counter)], once=False))
    t.expect = [('entry', 1, '==', 111111, 7), ('entry', 18, '==', 111011, 55)]
    for role in roles:
        for start, end in [(8, 9), (26, 40), (54, 55)]:
            full = role == 'included' and start == 26
            t.expect.append((role, start, '==' if full else '<', 1100, end))
            t.expect.append((role, start, '>', 1000, end))
    t.bench = [('bench_watch', dict(seconds=55, every=1, sheet=False, lines=4))]
    return t


CHECKS = {'engine_infpatk': {'a': check}}
# E140: same fixed predictions and controls, retail Soviet host configuration.
CHECKS['engine_infasov'] = {'a': check}
