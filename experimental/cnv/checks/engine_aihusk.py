"""Selection-only Husk probe; expectations recorded in work/re/c_husk_report.md.

Only survival/placed-derrick controls use counters. Native selection is read
from target_picks, never inferred from whether a team moves or attacks.
"""
from model import Test, Script, counted


def a(m):
    t = Test()
    names = [m.role(r).name for r in ('plant', 'barracks', 'tank', 'husk oil control')]
    names += [m.role(f'ai guardian {i}').name for i in range(1, 5)]
    t.scripts.append(Script('Husk keep', [],
        [('UNIT_SET_HEALTH', n, 100.0) for n in names], once=False))
    t.scripts.append(Script('Husk reveal', [],
        [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('Husk_all', '总数', t, template=m.cnv_units[0], player=m.player('s1'))
    t.expect.append(('总数', 20, '==', 4, 21))
    t.bench = [('bench_watch', dict(seconds=25, every=1, sheet=False, lines=1))]
    return t


CHECKS = {build: {'a': a} for build in ('aihusknone', 'aihusknamed')}
