"""Crate/native named-slot selection; evidence work/re/c_crate_report.md.

Counter verifies the placed control survives through the selection window.
Only target_picks establishes the native heuristic's selection verdict.
"""
from parts import Test, Script


def a(m):
    t = Test()
    names = [m.role(r).name for r in ('plant', 'barracks', 'tank')]
    names += [m.role(f'ai guardian {i}').name for i in range(1, 5)]
    t.scripts.append(Script('Crate keep', [],
        [('UNIT_SET_HEALTH', n, 100.0) for n in names], once=False))
    t.scripts.append(Script('Crate reveal', [],
        [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.counters.append(('CrateControl', 'control alive'))
    control = m.role('crate control').name
    t.scripts.append(Script('Crate alive reset', [], [('SET_COUNTER', 'CrateControl', 0)], once=False))
    t.scripts.append(Script('Crate alive', [('NAMED_NOT_DESTROYED', control)],
        [('SET_COUNTER', 'CrateControl', 1)], once=False))
    t.expect = [('control alive', 2, '==', 1, 3)]
    t.bench = [('bench_watch', dict(seconds=15, every=1, sheet=False, lines=1))]
    return t


CHECKS = {build: {'a': a} for build in ('aicrateon', 'aicrateoff')}
