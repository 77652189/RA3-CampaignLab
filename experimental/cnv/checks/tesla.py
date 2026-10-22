"""Tesla tank tests. Counters: the enemy Guardians left, the Tesla tank alive, its health.

fight: it loads (retail's deleted unit under our id) and fights: the enemy Guardians fall, it survives.
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
