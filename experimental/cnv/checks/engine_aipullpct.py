"""PullbackInjuredHealthPct finite contrast; reuse engine_aipullback aipullsov.

Before measurement: HURT=30 at wake+0.5, unchanged faction/Crane/other fields.
High 0.5 should return to the Crane then be recycled; low 0.2 should reach
the far plant first. Count health, living tanks, far area, home area. These
readings cannot establish an exact threshold or the internal leave frame.

Bench 2026-11-11, both checks PASS (health, alive, far, home):
  low0.2: health30 s9-13; far3 s15-16, far4 s17; home0 s3-33;
          after further injury one survivor home s34-39, alive0 from s40.
  high0.5: health30 s9-25; far0 throughout; home1 s19-20, home4 s23;
           alive3 s24-25, 2 s26, 1 s27, 0 from s28 (Crane recycling).
The simulator's live facility hook now distinguishes the initial return:
high sends four vehicles home without reaching the far plant; low reaches
the far plant first. tests/test_simai_pullpct.py separates the passing return
from the strict-xfail Crane recycling. Exact seconds, late return and
recycling are not claimed by the passing threshold tests.
"""
from checks.engine_aipullback import a as original


def a(m, high):
    t = original(m, 'aipullsov')
    wake = m.facts['wake at']
    t.expect = [('血量', wake + 1, 'ever==', 30, wake + 5)]
    if high:
        t.expect += [('回家', wake + 5, 'ever>=', 1, wake + 25),
                     ('坦克数', wake + 15, 'ever==', 0, wake + 35)]
    else:
        t.expect += [('到远厂', wake + 1, 'ever>=', 3, wake + 20)]
    return t


CHECKS = {'aipullpctlo': {'a': lambda m: a(m, False)},
          'aipullpcthi': {'a': lambda m: a(m, True)}}
