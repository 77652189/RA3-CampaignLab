"""UnderAttackBy diagnostic: read tgt candidates together with ua hit sources.

The prediction is land selects the real attacker / water rejects it. A missing
source in the candidate list is a world-fact gate, not a location verdict.
No counter or movement proxy establishes source registration. Evidence:
work/re/c_underattackby_fight_report.md.
"""
from checks.engine_aiunderattack import a as fight


def a(m):
    t = fight(m)
    t.bench = [('bench_watch', dict(seconds=100, every=10, sheet=False, lines=4))]
    return t


CHECKS = {name: {'a': a} for name in ('aiuabl', 'aiuabw')}
