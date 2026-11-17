"""Point selection is read through teamlog.target_picks, not inferred from arrival.

Only the survival control is asserted by on-screen counters. Selection and
search-range predictions are recorded before running in work/re/c_point_report.md.
"""
from model import Test, Script, counted


def a(m):
    t = Test()
    names = [m.role(r).name for r in ('plant', 'barracks', 'tank')]
    names += [m.role(f'ai guardian {i}').name for i in range(1, 5)]
    t.scripts.append(Script('Test - point keep', [],
        [('UNIT_SET_HEALTH', name, 100.0) for name in names], once=False))
    t.scripts.append(Script('Test - point reveal', [],
        [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('CNV_Point_All', '总数', t, template=m.cnv_units[0], player=m.player('s1'))
    x, y = m.site('east base')
    t.areas['CNV Point Home'] = [(x-300, y-400), (x+300, y-400),
                                (x+300, y+450), (x-300, y+450)]
    counted('CNV_Point_Home', '在家', t, template=m.cnv_units[0],
            player=m.player('s1'), area='CNV Point Home')
    t.expect.append(('总数', 25, '==', 4, 26))
    t.bench = [('bench_watch', dict(seconds=32, every=1, sheet=False, lines=2))]
    return t


CHECKS = {build: {'a': a} for build in ('aipointwater', 'aipointtiny')}
