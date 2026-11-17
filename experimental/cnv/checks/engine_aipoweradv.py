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
Bench 2026-11-09 (B round 82, the team's MinPowerAdvantage, the state ConstantHeuristic; one run each):
  aipadm1 (8 v 4, 1.0): 坦克在家 8 -> 0 s13-15; 坦克出门 4 @ s18.
  aipadm0 (4 v 8, 1.0): 坦克在家 4 -> 0 s14-15; 坦克出门 4 s18-31 -- goes (the first guess said stay).
  aipadm5 (8 v 4, 5.0; ratio 4 < 5): 坦克在家 8 -> 0 s13-16; 坦克出门 8 s21-26 -- goes (the guess said stay).
Read: MinPowerAdvantage holds no team back here (as the model: parsed, not used); what it gates, if anything, not
found. simai agrees (it ignores the field): tests/test_simai.py test_team_min_power_advantage_holds_nobody_back.
Bench 2026-11-09 (B round 83, the condition heuristics, 4 Guardians against none; one run each, all PASS):
  aihtim  (Timer 30s, MAP_START):         home 4 to s32, 0 @ s34 -- on after 30 s from the mission start.
  aihtima (Timer 25s AI_START, wake s10): home 4 to s37, 0 @ s39 -- from the wake.
  aihtimx (Timer 20s EndTime 10s):        home 4 to s22, 0 @ s23; out s27-s65 (they stay out after s30).
  aihint  (Interval 25s off, 30s on):     home 4 to s27, 0 @ s28 -- off first, then on.
  aihen1  (EnemyNearby 700 true, the player's Ore Collector ~527 off at the ore node): out s14-16.
  aihen0  (the same, no collector): home 4 to s65.   aihenn (EnemyNearby false, none): out s14-16.
  aihoe1  (ObjectOfTypeExists ENEMIES AlliedMiner, the player has one): out s15-17 -- the model said off.
  aihoe0  (none): home to s65.   aihoef (PassIfExists false, the player has one): home to s65 -- the model said on.
  aihoea  (ALLIES, only the player's): home to s65.   aihoes (ALLIES, s1's own collector): out s15-17 -- ALLIES
          includes oneself.
Read: Timer / Interval / EnemyNearby as the model; ObjectOfTypeExists counts the filter's Relationship (the model
looks only at its own templates: tests/test_simai.py test_object_of_type_exists_* strict xfail).
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
    if 'home until' in m.facts:                  # round 83: still all home that second
        hu = m.facts['home until']
        t.expect += [('坦克在家', hu, '==', n, hu + 1)]
    if m.facts['expect on']:
        by = m.facts.get('out by', ON_BY)
        t.expect += [('坦克在家', by, '<', n, by + 1)]
    else:
        t.expect += [('坦克在家', SECONDS, '==', n, SECONDS + 1)]
    t.bench = [('bench_watch', dict(seconds=SECONDS + LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': a} for k in ('aipadv2', 'aipadv1', 'aipadvh', 'aipadvc', 'aipadm1', 'aipadm0', 'aipadm5',
                                 # round 83: the condition heuristics
                                 'aihtim', 'aihtima', 'aihtimx', 'aihint', 'aihen1', 'aihen0', 'aihenn',
                                 'aihoe1', 'aihoe0', 'aihoef', 'aihoea', 'aihoes')}
