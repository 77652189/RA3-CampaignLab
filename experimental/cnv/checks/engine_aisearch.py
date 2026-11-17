"""EnemySearchDistanceVisionMultiplier A/B (missions/aisearch_bench.py), before the far target falls.

Prediction, using the already measured aipas geometry: high 1.5 attacks the side plant
before wake+25 and never reaches the far plant; low 0.25 leaves side HP 100 through that
window and reaches the far plant. Both have EngagePassiveTargets=true. Four counters
retain home/far/side counts and side HP, so departure and damage are separate evidence.
Only a passive structure, these two multipliers and this geometry are covered.

Bench 2026-11-11, both PASS (counters home/far/side/sideHP):
  aisrchhi: s1-10 4/0/0/100; s11 sideHP94, s25 5, s26-40 1; far0 throughout.
  aisrchlo: sideHP100 s1-39; far2 s15, far3 s16, far4 s17-37. At s40 sideHP85
            (after the comparison window, RAMPAGE can pick the side plant).
The simulator replays the early damage versus no-damage/destination split in
tests/test_simai_search.py; no claim about exact radius boundaries or fog visibility.
"""
from checks import engine_airetreat as ar


def a(m, high):
    t = ar.a(m, 'aipas1' if high else 'aipas0')
    end = m.facts['wake at'] + 25.0
    if high:
        t.expect.append(('到远厂', 1, '==', 0, end))
    t.bench = [('bench_watch', dict(seconds=end + 4, every=1, sheet=False, lines=4))]
    return t


CHECKS = {
    'aisrchhi': {'a': lambda m: a(m, True)},
    'aisrchlo': {'a': lambda m: a(m, False)},
}
