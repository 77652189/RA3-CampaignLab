"""C: ConstantHeuristic.Weight, named zero/one engine control.

Pre-run s40 prediction: zero infantry home/total=4/4, one=0/4;
unregistered tank control home=4 in both. Relative positive odds are gap.
Measured 2026-11-13: both PASS, one run each; zero s1-s46=4/4/4,
one s1-s13=4/4/4 then s14-s46=0/4/4 (home/total/tank control).
See work/re/c_constweight_report.md. Consumes only published mission roles.
"""
from parts import Script, Test, counted, square


def check(m):
    t = Test()
    t.areas['Weight home'] = square(*m.site('east base'), 450)
    t.scripts.append(Script('Weight reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.scripts.append(Script('Weight keep target', [],
        [('UNIT_SET_HEALTH', m.role('player target').name, 100.0)], once=False))
    inf, tank = m.cnv_units
    for key, label, unit, area, expected in (
            ('CW_home', '步兵在家', inf, 'Weight home', m.facts['expect infantry home']),
            ('CW_total', '步兵总数', inf, None, 4),
            ('CW_tank', '坦克在家', tank, 'Weight home', 4)):
        counted(key, label, t, template=unit, area=area, player=m.player('s1'))
        t.expect.append((label, 40, '==', expected, 41))
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=3))]
    return t


CHECKS = {name: {'a': check} for name in ('aicwzero', 'aicwone')}
