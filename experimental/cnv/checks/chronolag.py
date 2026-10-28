"""Phase tank tests: the map counts the enemy's objects IN_STASIS (the phase shell's status) and the target's health.

hit: the tank is deployed at DEPLOY_AT (its shell fires only deployed) -- the Apocalypse is out of time within a few
  seconds, and the 1-damage shell barely scratches it.
packed (the control): never deployed -- it never fires, nothing goes out of time.
"""
from parts import Script, Test, counted, status

DEPLOY_AT = 3.0


def run(m, deploy):
    t = Test()
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - deploy timer', DEPLOY_AT)]))
    if deploy:
        t.scripts.append(Script('Test - deploy', [('TIMER_EXPIRED', 'Test - deploy timer')],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role('tank').name, m.ability('tank', 'deploy'))]))
    counted('Test Phased', '时滞中', t, status=status('IN_STASIS'), player=m.player('s1'), most=3)
    counted('Test Target Health', '目标血量', t, health=m.role('target').name)
    t.bench = [('bench_watch', dict(seconds=20, every=1, sheet=False, lines=len(t.counters)))]
    return t


def hit(m):
    t = run(m, True)
    t.expect += [('时滞中', DEPLOY_AT, 'ever==', 1), ('目标血量', 0, '>=', 95)]
    return t


def packed(m):
    t = run(m, False)
    t.expect += [('时滞中', 0, '==', 0)]
    return t
