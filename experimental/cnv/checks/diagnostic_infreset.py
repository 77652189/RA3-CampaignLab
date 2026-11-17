"""RESET prediction: zero countdown makes both retail Iron Curtains ready.

At ten seconds send one enemy spy and one mutually allied spy. Predict enemy
consumed, full-health building keeps owner and loses ready; ally refuses and
keeps ready. No power is fired and no positive countdown is set: normal elapsed
time cannot turn an already ready power off. This measures ready state only,
not the reset duration, cooldown progress, effect execution or other templates.

E61 measured a: s1-s8 1011100/1011100; s9-s10 1111100/1111100;
s11-s20 1001100/1111100; s21-s36 1101100/1111100.
b (zero at 12, enter at 30): s1-s7 1011100/1011100;
s8-s30 1111100/1111100; s31-s40 1001100/1111100;
s41-s56 1101100/1111100. Positive power is present throughout.
Both runs violate the initial prediction of a full retail reload. In b the
condition is true before the zero command. Readiness semantics and actual
cooldown are unresolved; no RESET model or module coverage is claimed.
Original predictions intentionally remain failing. Paused after two runs;
see work/re/e_infreset_e61.md and strict xfail named replays.
"""
from parts import Script, Test, counted

POWER = 'SpecialPowerIronCurtain'


def check(m, late=False):
    t = Test()
    p, ally = m.player('p1'), m.player('s2')
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', p),
        ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
        ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend')),
        ('SET_MILLISECOND_TIMER', 'Reset ready', 12.0 if late else 2.0),
        ('SET_MILLISECOND_TIMER', 'Reset enter', 30.0 if late else 10.0)]),
        Script('Test - ready', [('TIMER_EXPIRED', 'Reset ready')], [
            ('NAMED_SET_SPECIAL_POWER_COUNTDOWN', m.role(role).name, POWER, 0)
            for role in ('enemy', 'ally')]),
        Script('Test - enter', [('TIMER_EXPIRED', 'Reset enter')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(role + ' spy').name, m.role(role).name)
            for role in ('enemy', 'ally')])]
    for role, side in (('enemy', 's1'), ('ally', 's2')):
        c = 'Reset ' + role
        counted(c, role, t, health=m.role(role).name)
        for label, cond, value in (
                ('owner', ('NAMED_OWNED_BY_PLAYER', m.player(side), m.role(role).name), 1000),
                ('spy', ('NAMED_NOT_DESTROYED', m.role(role + ' spy').name), 10000),
                ('ready', ('SKIRMISH_SPECIAL_POWER_READY', m.player(side), POWER), 100000),
                ('powered', ('PLAYER_EXCESS_POWER_COMPARE_VALUE', m.player(side), 3, 0), 1000000)):
            t.scripts.append(Script('Test - ' + role + label, [cond],
                                    [('INCREMENT_COUNTER', value, c)], once=False))
    # Keep the original failed predictions; b shifts both actions to distinguish
    # a start-up transient from a repeated short readiness interruption.
    t.expect = [('enemy', 14 if late else 4, '==', 1111100, 27 if late else 7),
                ('ally', 14 if late else 4, '==', 1111100),
                ('enemy', 38 if late else 18, '==', 1001100)]
    t.bench = [('bench_watch', dict(seconds=55 if late else 35, every=1, sheet=False, lines=2))]
    return t


CHECKS = {'engine_infreset': {'a': check, 'b': lambda m: check(m, late=True)}}
