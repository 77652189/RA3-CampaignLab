"""Three original counters for ThreatToWater; work/re/c_water_report.md.

No threat value or same-frame candidate eligibility is published by this host.
Keep all named units healthy so combat losses cannot masquerade as sorting.
"""
from parts import Test, Script, counted, square


def a(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - water reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    keep = [m.role(r).name for r in ('plant', 'barracks', 'tank', 'water sample')]
    keep += [m.role(f'ai guardian {i}').name for i in range(1, 5)]
    t.scripts.append(Script('Test - water keep', [], [('UNIT_SET_HEALTH', n, 100.0) for n in keep], once=False))
    for role, label in [('plant', '近处'), ('barracks', '远处')]:
        o = m.find(m.role(role).name)
        area = 'CNV Water ' + role
        t.areas[area] = square(o.x, o.y, 340)
        counted('CNV_Water_' + role, label, t, template=m.cnv_units[0], area=area, player=s1)
        t.expect.append((label, 40, '==', m.facts['expect ' + role], 41))
    x, y = m.site('east base')
    t.areas['CNV Water Home'] = [(x-300, y-400), (x+300, y-400), (x+300, y+450), (x-300, y+450)]
    counted('CNV_Water_Home', '在家', t, template=m.cnv_units[0], area='CNV Water Home', player=s1)
    t.expect.append(('在家', 40, '==', 0, 41))
    t.bench = [('bench_watch', dict(seconds=54, every=1, sheet=False, lines=3))]
    return t


CHECKS = {k: {'a': a} for k in ('aiwaterdist', 'aiwaterthreat', 'aiwaternear', 'aiwaterfar')}
