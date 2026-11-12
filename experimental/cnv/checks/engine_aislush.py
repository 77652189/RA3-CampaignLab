"""AccountShare.Account=SLUSH_FUND: opening plants at s40, isolated share swap.

Prediction before measurement: 100% slush -> 2 plants; 0% -> 0 (INFERRED).
The PRODUCTION share is the complement; no deposit is made. The test measures
the opening's sensitivity, not account balances. See work/re/c_slush_report.md.
"""
from parts import Script, Test, counted


def a(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('CNV_Slush_Plants', '电厂', t, template='AlliedPowerPlant', player=m.player('s1'))
    t.expect = [('电厂', 40, '==', m.facts['plants'], 41)]
    t.bench = [('bench_watch', dict(seconds=49, every=1, sheet=False, lines=1))]
    return t


CHECKS = {build: {'a': a} for build in ('aislush100', 'aislush0')}


def d(m):
    """Round two, same income host: slush-only cannot fund ordinary defense."""
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counted('CNV_Slush_Defense', '炮塔', t, template=m.cnv_turret, player=m.player('s1'))
    t.expect = [('炮塔', 60, '==' if m.facts['slush only'] else '>', 0, 61)]
    t.bench = [('bench_watch', dict(seconds=69, every=1, sheet=False, lines=1))]
    return t


CHECKS.update({build: {'d': d} for build in ('aislsdef', 'aislddef')})
