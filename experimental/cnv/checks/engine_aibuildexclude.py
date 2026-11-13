"""C ExcludeThing contrast; original readings and orders: work/re/c_buildexclude_report.md.

Original prediction (superseded by D103): excluding an explicitly included
request would remove its structure-basket priority. Direct factory observations
show IncludeThing wins instead. Category-only probes below isolate exclusion.

Measured 2026-11-13: both variants first own CNVNewPK at frame 501 and
CNVDearPK at frame 570. Neither template occurs in an order line, so the
positive production controls do not establish basket choice. D103's build picks
and direct orders resolve the filter and basket boundary; whole-game production
timing is still a separate gap (work/re/c_buildexclude_follow_report.md).
"""
from checks.engine_aiskirm import yc


def r(m):
    t = yc(m)
    t.bench = [('bench_watch', dict(seconds=175, every=1, sheet=False, lines=len(t.counters)))]
    t.expect = [('新维和', 30, 'ever>=', 1, 45), ('贵维和', 30, 'ever>=', 1, 45)]
    return t


def x(m):
    """Category includes both infantry; only aibxo excludes Dear (no IncludeThing).

    Prediction: New passes in both; Dear passes only in aibxi. New's score
    wins the structure basket in both. Read build_picks/build_orders, since
    production counters alone cannot identify this filter.
    """
    t = r(m)
    t.bench = [('bench_watch', dict(seconds=55, every=1, sheet=False, lines=len(t.counters)))]
    t.expect = [('新维和', 30, 'ever>=', 1, 55), ('贵维和', 30, 'ever>=', 1, 55)]
    return t


CHECKS = {'aibex': {'r': r}, 'aibin': {'r': r}, 'aibxo': {'x': x}, 'aibxi': {'x': x}}
