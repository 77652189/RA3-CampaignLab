"""Tesla tank tests.

fight: it loads (retail's deleted unit under our id) and fights: the enemy Guardians fall, it survives.
  (bench 2026-10-22: it fires and kills one of three, then is destroyed ~s10 -- three Guardians outgun it)
surge (A against B): A turns its surge on at the start, B does not; each has an enemy Guardian 40 away. A's Guardian,
  paralysed, never fires: A stays whole. B's Guardian fights.
"""
from parts import Script, Test, counted


def fight(m):
    t = Test()
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('Test Targets', '敌方守护者', t, template=m.role('target').template, player=m.player('s1'))
    counted('Test Tesla', '磁暴坦克', t, template=m.role('tesla').template)
    counted('Test Health', '磁暴血量', t, health=m.role('tesla').name)
    t.expect += [('敌方守护者', 0, 'ever==', 3), ('敌方守护者', 4, 'ever<', 3), ('磁暴坦克', 0, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=30, every=3, sheet=False, lines=len(t.counters), until='c1==0'))]
    return t


def surge(m):
    t = Test()
    a = m.role('tesla A').name
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('NAMED_USE_COMMANDBUTTON_ABILITY', a, m.ability('tesla A', 'surge'))]))
    for k in 'AB':
        counted(f'Test {k} Health', f'{k} 血量', t, health=m.role(f'tesla {k}').name)
        counted(f'Test {k} Guard', f'{k} 守护者血量', t, health=m.role(f'guard {k}').name)
    t.expect += [('A 血量', 0, '>=', 95), ('B 血量', 0, 'ever<', 95)]
    t.bench = [('bench_watch', dict(seconds=30, every=3, sheet=False, lines=len(t.counters)))]
    return t
