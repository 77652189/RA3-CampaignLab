"""Engine probe: the AI's StaticDefense tactic, the Distance circle and the pull-back (missions/aidefense_bench.py).

  a  圈300 / 圈450 / 圈650 / 圈900   Peacekeepers of s1 inside a square of half-width r centred on the AI's yard
                                  (r = 300 / 450 / 650 / 900) -- once a second from the wake to ~65 s after it

The Peacekeepers are ordered (plain MOVE, mission second 30) to FAR, 1150 from the yard (1200, on two trees, for every
reading below: see missions/aidefense_bench.py) toward the east gate, almost due west
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

  b  (round 62: aidefctl / aidefctl4 / aidefmv) the four start 700 out toward the gate, no m.order; at s55 this check
     moves them to FAR by name (teleport, or MOVE_NAMED_UNIT_TO), no UNIT_SET_TEAM. Expectation: the control, 圈300
     >= 1 just before the push (the team brought them to the yard).
Bench 2026-11-06 aidefctl b (CampAIDefCtlB, D=250 U=1 s, teleport): PASS. The control: 圈900 4 @ s1, 圈650 4 @ s2,
  圈450 4 @ s6, 圈300 4 @ s9 -- they walk to the yard from the first second, before the s10 wake script (the AI's
  state runs from the start; the wake's UNIT_AI_TRANSFER_ALL is not what starts it). The teleport: all rings 0 @ s55
  (1 left @ s54, the watch clock ~1 s off); back: 圈900 4 @ s66, 圈650 4 @ s72, 圈450 4 @ s76, 圈300 4 @ s80, and 4 4 4 4
  to the end (s120). Pulled back: StaticDefense holds the team that the earlier m.order probes had taken away.
Bench 2026-11-06 aidefctl4 b (CampAIDefCtl4B, U=4 s): PASS. The control the same (圈300 4 @ s9); after the teleport
  圈900 4 @ s68, 圈650 4 @ s75, 圈450 4 @ s79, 圈300 4 @ s82: ~2 s later than U=1 (the next update comes up to 4 s on).
Bench 2026-11-06 aidefmv b (CampAIDefMvB, MOVE_NAMED_UNIT_TO): PASS. The control the same; after the move order no ring
  ever drops (4 4 4 4 from s9 to s120): never 300 out.
  c  (aidefmv) the same with rings 100 / 175 / 225 / 275, to see how far the script move gets.
Bench 2026-11-06 aidefmv c (CampAIDefMvC): PASS. 圈100 1 @ s54-55, 2 @ s56, 4 @ s57 to the end; 圈175 / 225 / 275 hold 4
  throughout: called back before 175, long before Distance 250, and no back and forth. Read as the aesthetics-off
  re-gather (ready and the centre more than 100 off -> attack-move to the point); the model's ready test misses it
  (RA3-EngineModel tests/test_ai_defense.py, strict xfail).
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


PUSH_AFTER = 105.0


def push(how, rings=RINGS):
    """Round 62 (missions aidefctl / aidefctl4 / aidefmv): the four start 700 out, so the rings filling after the wake
    is the control (the team formed and walks to the yard it defends); at 'push at' this script moves them out to FAR
    by name, with no UNIT_SET_TEAM (how: UNIT_TELEPORT_TO_WAYPOINT or MOVE_NAMED_UNIT_TO)."""
    def b(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        (inf,) = m.cnv_units
        x, y = m.site('east base')
        for r in rings:
            area = f'CNV AD Ring {int(r)}'
            t.areas[area] = square(x, y, r)
            counted(f'CNV_AD_{int(r)}', f'圈{int(r)}', t, template=inf, area=area, player=s1)
        t.scripts.append(Script('Test - push', [('TIMER_EXPIRED', 'CNV AI Push')],
                                [(how, m.role(f'peacekeeper {k}').name, 'CNV AI Far') for k in range(1, 5)]))
        w, p = m.facts['wake at'], m.facts['push at']
        end = w + PUSH_AFTER
        t.expect += [(f'圈{int(rings[-1])}', p - 1, '>=', 1, p)]   # the control: the team brought them to the yard
        t.bench = [('bench_watch', dict(seconds=end + LAG, every=1, sheet=False, lines=len(t.counters)))]
        return t
    return b


CHECKS = {k: {'a': a} for k in ('aidef250', 'aidef450', 'aidefupd4', 'aidefslack')}
CHECKS |= {'aidefctl': {'b': push('UNIT_TELEPORT_TO_WAYPOINT')},
           'aidefctl4': {'b': push('UNIT_TELEPORT_TO_WAYPOINT')},
           'aidefmv': {'b': push('MOVE_NAMED_UNIT_TO'), 'c': push('MOVE_NAMED_UNIT_TO', (100.0, 175.0, 225.0, 275.0))}}
