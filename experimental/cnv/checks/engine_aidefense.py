"""Engine probe: the AI's StaticDefense tactic, the Distance circle and the pull-back (missions/aidefense_bench.py).

  a  圈300 / 圈450 / 圈650 / 圈900   Peacekeepers of s1 inside a square of half-width r centred on the AI's yard
                                  (r = 300 / 450 / 650 / 900) -- once a second from the wake to ~65 s after it

The Peacekeepers are ordered (plain MOVE, mission second 30) 1200 from the yard toward the east gate, almost due west
(direction (-0.990, -0.141)), so a square of half-width r is the circle of radius r to within the small sideways
drift (the yard-to-unit distance is the x-distance times ~1.01). The reading is how low each ring goes after s30 and
when it is back at 4 (the team dragging them back inside Distance). The expectation is weak (the 900 ring holds >= 1
at the end, readings complete); a FAIL is a reading too.

读数
Bench 2026-11-06 aidef250 a (CampAIDef250A, one run): FAIL 0 of 1 (the weak 圈900 >= 1 at s75). 圈300 4 -> 3 @ s33,
  1 @ s34, 0 @ s42; 圈450 4 -> 3 @ s36, 1 @ s38, 0 @ s45; 圈650 4 -> 3 @ s41, 1 @ s43, 0 @ s49; 圈900 4 -> 3 @ s48,
  1 @ s50, 0 @ s57 and 0 to the end (s80). The four Peacekeepers walked out to FAR (1200) and stayed: no pull-back.
Bench 2026-11-06 aidef450 a (CampAIDef450A): FAIL, the same: 圈300 2 @ s33, 1 @ s34, 0 @ s41; 圈450 0 @ s45; 圈650
  0 @ s49; 圈900 0 @ s57, no return. Distance 450 instead of 250 changes nothing (+-1 s noise).
Bench 2026-11-06 aidefupd4 a (CampAIDefUpd4A): FAIL, the same (0 @ s42 / s45 / s49 / s57; no return): UpdateTime 4 s
  changes nothing.
Bench 2026-11-06 aidefslack a (CampAIDefSlackA): FAIL, the same: CombatLeashSlack 3.0 changes nothing.
  Caveat for all four: the move order goes through m.order (UNIT_SET_TEAM into a script team, the contract refuses a
  single-unit MOVE_NAMED_UNIT_TO), which may take the Peacekeepers out of the AI's team, so "no pull-back" may be that,
  not StaticDefense. Not yet separated; the next probe is an order that leaves the AI's team (a unit pushed by
  something else) or the unit left to walk by itself.
"""
from parts import Script, Test, counted, square

LAG = 4.0
AFTER = 65.0
RINGS = (300.0, 450.0, 650.0, 900.0)


def a(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    (inf,) = m.cnv_units
    x, y = m.site('east base')
    for r in RINGS:
        area = f'CNV AD Ring {int(r)}'
        t.areas[area] = square(x, y, r)
        counted(f'CNV_AD_{int(r)}', f'圈{int(r)}', t, template=inf, area=area, player=s1)
    w = m.facts['wake at']
    end = w + AFTER
    t.expect += [('圈900', end, '>=', 1, end + 1)]
    t.bench = [('bench_watch', dict(seconds=end + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a} for k in ('aidef250', 'aidef450', 'aidefupd4', 'aidefslack')}
