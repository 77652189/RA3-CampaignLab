"""Engine probe: PowerAdvantageHeuristic switches a strategic state (missions/aipoweradv_bench.py) -- do the AI's
Guardians leave its base when its army out-kills the player's, and stay when it does not?

  a  坦克在家   Guardians of s1 inside the base area (450 around the east base), once a second
     坦克出门   Guardians of s1 within 300 of the player's power plant ~750 west of them (the state's target)

Expected (program read, work/re l4_states.md 11; the mission's 'expect on'): on -- 坦克在家 below the AI's count by
s40 (an always-on state's team leaves ~5 s after the wake, engine_aistate); off -- all still home at s60.

读数
Bench 2026-11-09 (B round 77, one run each, PASS 1 of 1 each):
  aipadv1 a (CampAIPAdv1A, 4 against 8): 坦克在家 4 / 坦克出门 0 from s1 to s65 -- off.
  aipadvc a (CampAIPAdvCA, 4 against 8, ConstantHeuristic): 坦克在家 4 -> 3 @ s14, 0 @ s15; 坦克出门 4 s18-s31
    (then 0: the plant dead) -- the control, so aipadv1's stay is the heuristic's.
  aipadv2 a (CampAIPAdv2A, 8 against 4): 坦克在家 8 -> 7 @ s13, 5 @ s14, 1 @ s15, 0 @ s16; 坦克出门 8 s21-s26 -- on.
  aipadvh a (CampAIPAdvHA, 4 against an Ore Collector only): 坦克在家 4 -> 3 @ s15, 0 @ s16; 坦克出门 4 s20-s31 -- on.
The simulator (simai) gives the same four (tests/test_simai.py test_power_advantage_gates_the_state_as_on_the_bench).
"""
from parts import Script, Test, counted, square

AREA, THERE = 'CNV AI Base Area', 'CNV AI Target Area'
LAG = 4.0
ON_BY, SECONDS = 40.0, 60.0


def a(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[AREA] = square(*m.site('east base'), 450.0)
    goal = m.find(m.role('player target').name)
    t.areas[THERE] = square(goal.x, goal.y, 300.0)
    tank, = m.cnv_units
    counted('CNV_PA_Home', '坦克在家', t, template=tank, area=AREA, player=s1)
    counted('CNV_PA_There', '坦克出门', t, template=tank, area=THERE, player=s1)
    n = m.facts['ai tanks']
    if m.facts['expect on']:
        t.expect += [('坦克在家', ON_BY, '<', n, ON_BY + 1)]
    else:
        t.expect += [('坦克在家', SECONDS, '==', n, SECONDS + 1)]
    t.bench = [('bench_watch', dict(seconds=SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a} for k in ('aipadv2', 'aipadv1', 'aipadvh', 'aipadvc')}
