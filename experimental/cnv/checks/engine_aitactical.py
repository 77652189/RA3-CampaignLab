"""EngageTacticalTarget on/off, with hostile/passive acquisition disabled.

Prediction before bench: the on team receives explicit attacks on the nearest
power plant, the off team only attack-moves to its point. The unarmed plant
cannot provoke retaliation. At 40 s on has damaged it, off leaves it at 100%.
Both retain four Peacekeepers. This tests dispatch, not exact firing timing.

Bench 2026-11-11: aitacon:a / aitacoff:a PASS (one run each). On reads
100% through s12, 84% at s13, 0% from s22 through s43; off stays 100%
through s48. Both retain four infantry. Replay: tests/test_engage_tactical.py.
Only an object target in range, with passive/hostile dispatch disabled, is
covered; point targets, competing enemies and the exact scan boundary are not.
"""
from parts import Script, Test, counted


def check(m):
    t = Test()
    t.counters.append(('Tac HP', '目标血量'))
    t.scripts = [Script('Tac reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                 Script('Tac hp', [], [('SET_COUNTER', 'Tac HP', 0),
                                      ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', m.role('target').name, 'Tac HP')],
                        once=False)]
    counted('Tac Alive', '步兵存活', t, template=m.cnv_units[0], player=m.player('s1'))
    t.expect = [('目标血量', 40, '<' if m.facts['tactical enabled'] else '==', 100, 42),
                ('步兵存活', 40, '==', 4, 42)]
    t.bench = [('bench_watch', dict(seconds=42, every=1, sheet=False, lines=2))]
    return t


CHECKS = {key: {'a': check} for key in ('aitacon', 'aitacoff')}
