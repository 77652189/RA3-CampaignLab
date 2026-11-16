"""UnderAttack set / clear on the bench: Hammer A shoots the AI's power plant and is deleted mid-fight (source deleted);
Hammer B shoots it after A's window ran out and is then stopped, staying alive (ceasefire, source alive).

Readings come from ra3ext `ua:` lines (experimental/cnv/teamlog.py under_attack); the check itself only orders the
fight and stops it. Record: work/re/d161_underattack.md.
"""
from parts import Script, Test


def a(m):
    t = Test()
    tank, tank_b, plant = m.role('ua tank').name, m.role('ua tank b').name, m.role('closest plant').name
    f = m.facts   # SET_MILLISECOND_TIMER takes seconds (d163)
    t.scripts.append(Script('Test - start', [], [('SET_MILLISECOND_TIMER', 'UA Attack', f['attack at']),
                                                 ('SET_MILLISECOND_TIMER', 'UA Stop', f['stop at']),
                                                 ('SET_MILLISECOND_TIMER', 'UA B Attack', f['b attack at']),
                                                 ('SET_MILLISECOND_TIMER', 'UA B Stop', f['b stop at']),
                                                 ('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.scripts.append(Script('Test - attack', [('TIMER_EXPIRED', 'UA Attack')], [('NAMED_FORCE_ATTACK_NAMED', tank, plant)]))
    t.scripts.append(Script('Test - stop', [('TIMER_EXPIRED', 'UA Stop')], [('NAMED_DELETE', tank)]))
    t.scripts.append(Script('Test - b attack', [('TIMER_EXPIRED', 'UA B Attack')],
                            [('NAMED_FORCE_ATTACK_NAMED', tank_b, plant)]))
    t.scripts.append(Script('Test - b stop', [('TIMER_EXPIRED', 'UA B Stop')], [('NAMED_STOP', tank_b)]))
    t.bench = [('bench_watch', dict(seconds=200, every=10, sheet=False, lines=4))]
    return t


CHECKS = {'aiunderatk': {'a': a}}
