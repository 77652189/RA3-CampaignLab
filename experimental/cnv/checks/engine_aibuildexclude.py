"""C ExcludeThing contrast; original readings and orders: work/re/c_buildexclude_report.md.

Predict before measurement: the included score-1 request has structure-basket
priority; ExcludeThing returns it to the unit basket behind score-1000 CNVNewPK.
Owned counts include all production paths; CNVOrders is needed to identify orders.

Measured 2026-11-13: both variants first own CNVNewPK at frame 501 and
CNVDearPK at frame 570. Neither template occurs in an order line, so the
positive production controls do not establish basket choice. The simultaneous
IncludeThing/ExcludeThing precedence and direct factory order path remain gaps.
"""
from checks.engine_aiskirm import yc


def r(m):
    t = yc(m)
    t.bench = [('bench_watch', dict(seconds=175, every=1, sheet=False, lines=len(t.counters)))]
    t.expect = [('新维和', 30, 'ever>=', 1, 45), ('贵维和', 30, 'ever>=', 1, 45)]
    return t


CHECKS = {'aibex': {'r': r}, 'aibin': {'r': r}}
