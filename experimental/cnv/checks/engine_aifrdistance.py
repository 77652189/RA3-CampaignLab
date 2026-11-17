"""Three-MCV FriendlyUnit probe; counters preserve independent survival.

Tactical target identity must be read from the same-frame team log and
matched to the idle MCV IDs/coordinates, not inferred from arrival counts.
Pre-run prediction: nearest MCV; see work/re/c_friendly_distance_report.md.
"""
from checks.engine_aifriendly import a as original
from parts import Script


def a(m):
    t = original(m)
    t.expect = [('友车存活', 30, '==', 3, 31), ('敌车存活', 30, '==', 1, 31)]
    t.scripts.append(Script('Keep extra MCVs', [], [
        ('UNIT_SET_HEALTH', m.role(role).name, 100.0) for role in ('second', 'third')], once=False))
    t.bench = [('bench_watch', dict(seconds=34, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': a} for name in ('aifrnear', 'aifrswap')}
