"""Four land ClosestToEnemy hosts; predicted four members at each selected structure.

Measured s16-80: 4/4/0/0 versus predicted 4/4/4/4.
Raw readings and unresolved candidate qualifications: work/re/c_closest_report.md.
"""
from parts import Script, Test, counted, square


def a(m):
    t = Test()
    for i, unit in enumerate(m.cnv_units):
        target = m.find(m.role(f'closest goal {i}').name)
        area = f'Closest area {i}'
        t.areas[area] = square(target.x, target.y, 250)
        label = ('普通数量', '非矿数量', '非塔数量', '原关数量')[i]
        counted(f'Closest_count{i}', label, t, template=unit, area=area, player=m.player('s1'))
        t.expect.append((label, 55, '==', 4, 60))
    for i, role in enumerate(('closest plant', 'closest turret', 'closest enemy')):
        t.scripts.append(Script(f'Closest keep {i}', [],
            [('UNIT_SET_HEALTH', m.role(role).name, 100.0)], once=False))
    for i, role in enumerate(r for r in m.cast if r.startswith(('peacekeeper ', 'guardian ', 'closest extra '))):
        t.scripts.append(Script(f'Closest member keep {i}', [],
            [('UNIT_SET_HEALTH', m.role(role).name, 100.0)], once=False))
    t.bench = [('bench_watch', dict(seconds=65, every=1, sheet=False, lines=4))]
    return t


CHECKS = {'aiclosest': {'a': a}}
