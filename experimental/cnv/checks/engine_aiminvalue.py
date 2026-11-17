"""MinEnemyValue retail 1000/2500, single/summed enemy cost and inversion.

Corrected data predictions s40-60: low 0/4/4/0, high 0/4/0/4. Source and raw results:
Measured s40-60: low 0/4/4/1 (last lane differs), high 0/4/0/4 (PASS).
work/re/c_minvalue_report.md. Equality at 2500 and damaged-unit valuation remain gaps.
"""
from parts import Script, Test, counted, square


def a(m):
    t = Test()
    t.areas['MinValue home'] = square(*m.site('east base'), 450)
    roles = ('player target',) + tuple(f'value miner {i}' for i in range(m.facts['min value miners']))
    for i, role in enumerate(roles):
        t.scripts.append(Script(f'MinValue keep {i}', [],
            [('UNIT_SET_HEALTH', m.role(role).name, 100.0)], once=False))
    for i, (unit, label, expected) in enumerate(zip(m.cnv_units,
            ('一千单矿', '二五单矿', '二五合计', '合计反向'), m.facts['min value home'])):
        counted(f'MinValue_home{i}', label, t, template=unit,
                player=m.player('s1'), area='MinValue home')
        t.expect.append((label, 40, '==', expected, 60))
    t.bench = [('bench_watch', dict(seconds=65, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': a} for name in ('aiminvalue', 'aiminvaluehi')}
