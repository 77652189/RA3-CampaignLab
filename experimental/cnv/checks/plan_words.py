"""The plan words probe (missions/plan_words_bench.py), read off the counters:

words: money climbs by its bonus every gap (the first at once); one guardian is given between its random window's
  two ends; the shielded warrior stands while the control beside it falls, and falls once its shield is undone.
"""
from parts import Script, Test, counted

LAG = 4.0                                       # the bench's clock runs ~3 s behind the mission's (a4 LEAD)


def alive(t, counter, label, name):
    t.counters.append((counter, label))
    t.scripts += [Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False),
                  Script(f'Test - {counter} up', [('NAMED_NOT_DESTROYED', name)], [('SET_COUNTER', counter, 1)],
                         once=False)]


def words(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    f = m.facts
    t.counters.append(('CNV_PW_Money', '资金'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', m.player('p1'), 'CNV_PW_Money')],
                            once=False))
    counted('CNV_PW_Guardians', '守护者', t, template='AlliedAntiVehicleVehicleTech1')
    alive(t, 'CNV_PW_Shielded', '无敌的', m.role('shielded').name)
    alive(t, 'CNV_PW_Control', '对照', m.role('control').name)
    money, bonus, gap = f['money'], f['bonus'], f['gap']
    t.expect += [
        # the first at once, then one more each gap: by 20 s at least four more, not more than six
        ('资金', 2, 'ever>=', money + bonus, 8), ('资金', 22, '>=', money + 4 * bonus, 26),
        ('资金', 22, '<=', money + 6 * bonus, 26),
        ('守护者', 1, '==', 2, f['give from'] - LAG), ('守护者', f['give until'] + LAG, '==', 3, 26),
        ('对照', f['undo at'] - LAG, '==', 0, f['undo at'] - 2), ('无敌的', 1, '==', 1, f['undo at'] - 2),
        ('无敌的', f['undo at'] + 15, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=f['undo at'] + 20, every=2, sheet=False, lines=len(t.counters)))]
    return t
