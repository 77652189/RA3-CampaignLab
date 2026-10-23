"""Shikigami tests, A against B on one map: at GUARD_AT group A's shikigami goes on guard, B's does not; at SHOOT_AT
both groups' conscripts are ordered to shoot their VIP.

cover: A's VIP comes through untouched while A's shikigami takes the fire; B's VIP is hit.
"""
from parts import Script, Test, counted

GUARD_AT, SHOOT_AT = 10.0, 11.0


def bend(m):
    """shells: A's shikigami on guard at GUARD_AT, B's not; at SHOOT_AT both V4 launchers are ordered at their VIP.
    A's first rocket bends onto the shikigami and A's VIP is untouched, while B's first one hits B's VIP (bench
    2026-10-22: one V4 rocket kills a shikigami, so A's VIP falls to the next one -- hence the window)."""
    t = Test()
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - guard timer', GUARD_AT),
                                                 ('SET_MILLISECOND_TIMER', 'Test - shoot timer', SHOOT_AT)]))
    t.scripts.append(Script('Test - guard', [('TIMER_EXPIRED', 'Test - guard timer')],
                            [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role('guard A').name, m.ability('guard A', 'guard'))]))
    t.scripts.append(Script('Test - shoot', [('TIMER_EXPIRED', 'Test - shoot timer')],
                            [('NAMED_ATTACK_NAMED', m.role(f'launcher {k}').name, m.role(f'vip {k}').name) for k in 'AB']))
    for k in 'AB':
        counted(f'Test VIP {k}', f'{k} 要人血量', t, health=m.role(f'vip {k}').name)
        counted(f'Test Guard {k}', f'{k} 式神血量', t, health=m.role(f'guard {k}').name)
    window = SHOOT_AT + 4                       # past the first rockets, before the second
    t.expect += [('A 要人血量', 0, '==', 100, window), ('A 式神血量', SHOOT_AT, 'ever<', 100, window),
                 ('B 要人血量', SHOOT_AT, 'ever<', 100, window)]
    t.bench = [('bench_watch', dict(seconds=40, every=3, sheet=False, lines=len(t.counters)))]
    return t


def cover(m):
    t = Test()
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - guard timer', GUARD_AT),
                                                 ('SET_MILLISECOND_TIMER', 'Test - shoot timer', SHOOT_AT)]))
    t.scripts.append(Script('Test - guard', [('TIMER_EXPIRED', 'Test - guard timer')],
                            [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role('guard A').name, m.ability('guard A', 'guard'))]))
    t.scripts.append(Script('Test - shoot', [('TIMER_EXPIRED', 'Test - shoot timer')],
                            [('NAMED_ATTACK_NAMED', s.name, m.role(f'vip {k}').name)
                             for k in 'AB' for s in m.roles(f'shooter {k}')]))
    for k in 'AB':
        counted(f'Test VIP {k}', f'{k} 要人血量', t, health=m.role(f'vip {k}').name)
        counted(f'Test Guard {k}', f'{k} 式神血量', t, health=m.role(f'guard {k}').name)
    t.expect += [('A 要人血量', 0, '==', 100), ('A 式神血量', SHOOT_AT, 'ever<', 100),
                 ('B 要人血量', SHOOT_AT, 'ever<', 100)]
    t.bench = [('bench_watch', dict(seconds=35, every=3, sheet=False, lines=len(t.counters)))]
    return t
