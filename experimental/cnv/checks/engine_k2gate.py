"""Read first departure and foe health; verify recruitment and aim in the teams log."""

from checks import engine_aicombat
from parts import Script, counted


def a(m):
    t = engine_aicombat.a(m)
    fighter = m.role('candidate fighter').name
    foe = m.role('player foe').name
    timer = 'CNV K2 attack'
    t.scripts += [
        Script('Test - K2 attack timer', [], [('SET_MILLISECOND_TIMER', timer, m.facts['order at'])]),
        Script('Test - K2 aim', [('TIMER_EXPIRED', timer)], [('NAMED_ATTACK_NAMED', fighter, foe)]),
    ]
    # The archived teams log measures the actual join frame. Keep the first departure identity
    # on screen alongside the two position flags and foe health.
    t.counters.remove(('CNV_RC_Frame', '首离帧'))
    counted('CNV_K2_FoeHealth', '目标血量', t, health=foe)
    t.expect = [
        ('目标血量', 3, '==', 100, 24),
        ('首离身份', 1, 'ever==', 1 if m.facts['allow in combat'] else 2, 49),
    ]
    return t


CHECKS = {name: {'a': a} for name in ('k2gate0', 'k2gate1')}
