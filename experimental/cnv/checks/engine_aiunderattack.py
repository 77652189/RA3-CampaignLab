"""UnderAttack set / clear on the bench: a Hammer shoots the AI's power plant, then is deleted (the ceasefire).

Readings come from ra3ext `ua:` lines (experimental/cnv/teamlog.py under_attack); the check itself only orders the
fight and stops it. Record: work/re/d161_underattack.md.
"""
from parts import Script, Test


def a(m):
    t = Test()
    tank, plant = m.role('ua tank').name, m.role('closest plant').name
    attack, stop = m.facts['attack at'], m.facts['stop at']
    t.scripts.append(Script('Test - start', [], [('SET_MILLISECOND_TIMER', 'UA Attack', attack),
                                                 ('SET_MILLISECOND_TIMER', 'UA Stop', stop),
                                                 ('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.scripts.append(Script('Test - attack', [('TIMER_EXPIRED', 'UA Attack')], [('NAMED_ATTACK_NAMED', tank, plant)]))
    t.scripts.append(Script('Test - stop', [('TIMER_EXPIRED', 'UA Stop')], [('NAMED_DELETE', tank)]))
    t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=4))]
    return t


CHECKS = {'aiunderatk': {'a': a}}
