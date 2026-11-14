"""Engine probe: the AI's ReactiveDefense tactic and ReactiveDefenseRadius (missions/aireactive_bench.py).

  a  家300 / 敌300 / 敌存活   s1 Peacekeepers inside a square of half-width 300 around the AI yard / around the foe spot
                           (1000 straight south of the yard) / the player's Peacekeepers inside a half-width-2500
                           square around the foe spot (the one foe) -- once a second from the start to wake + 60 s

Model prediction: R = 1200 -> the team (the state runs every 31st frame once the base exists after the wake's
MAKE_BASE) attack-moves to the foe (1000 < 1200): 敌300 >= 1 and the foe dies (敌存活 0). R = 750 -> the foe is never
chased (1000 > 750): 家300 stays 4, 敌300 stays 0, 敌存活 stays 1. Expectation (since the first readings below): 敌存活
at mission second 30 is 0 for R > 1000, 1 otherwise.

读数
Bench 2026-11-14 aireact750 a (CampAIReact750A, run CampAIReact750A_mcp_1114_133453): PASS. 家300 4 / 敌300 0 / 敌存活 1
  at s1 and unchanged to the end (s80): the foe 1000 away is never chased with R = 750.
Bench 2026-11-14 aireact1200 a (CampAIRea1200A, run CampAIRea1200A_mcp_1114_134120; the build name is CampAIRea1200:
  CampAIReact1200A is 16 characters, which the first attempt hit): FAIL 0 of 1 -- only the weak 敌存活 >= 0 at s70,
  "no reading" (the watch ran to s102.8 and the s70 frame is not in the readings; not a game result). Readings:
  家300 4 @ s1-s3, 3 @ s4, 2 @ s5, 1 @ s7, 0 @ s8-s36, 4 again from s37 to the end (s103); 敌300 0 until s12, 2 @ s14,
  3 @ s15, 4 @ s17-s27, 2 @ s28, 0 from s29 to the end; 敌存活 1 until s19, 0 from s20 to the end. So with R = 1200
  the team leaves in the first seconds (before the s10 wake: the state runs without it, as aidefense's control),
  reaches the foe at ~s14, the foe is dead by s20, and after the team disbands (EndBehavior DISBAND) the four walk
  home (out of the foe square s28-s36, back inside the home square at s37). The foe is chased at 1000 with R = 1200
  and not with R = 750: the radius gates the reaction. The prediction was right about the radius, wrong about the
  timing (it expected the state to wait for the wake's MAKE_BASE).
"""
from parts import Script, Test, counted, square

LAG = 4.0
AFTER = 60.0
NEAR = 300.0
BIG = 2500.0
FOE_DIST = 1000.0   # missions/aireactive_bench.py
CHASED_BY = 30.0


def a(m):
    t = Test()
    s1, p1 = m.player('s1'), m.player('p1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
    (inf,) = m.cnv_units
    x, y = m.site('east base')
    fx, fy = m.site('east base', 0.0, -FOE_DIST)
    t.areas['CNV RD Home'] = square(x, y, NEAR)
    t.areas['CNV RD Foe'] = square(fx, fy, NEAR)
    t.areas['CNV RD FoeBig'] = square(fx, fy, BIG)
    counted('CNV_RD_HOME', '家300', t, template=inf, area='CNV RD Home', player=s1)
    counted('CNV_RD_FOE', '敌300', t, template=inf, area='CNV RD Foe', player=s1)
    counted('CNV_RD_ALIVE', '敌存活', t, template=inf, area='CNV RD FoeBig', player=p1)
    end = m.facts['wake at'] + AFTER
    # bench 2026-11-14: R 1200 kills the foe 1000 out by s20, R 750 never goes -- asserted at mission second 30
    alive = 0 if m.facts['radius'] > FOE_DIST else 1
    t.expect += [('敌存活', CHASED_BY, '==', alive, CHASED_BY + 1)]
    t.bench = [('bench_watch', dict(seconds=end + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a} for k in ('aireact750', 'aireact1200')}
