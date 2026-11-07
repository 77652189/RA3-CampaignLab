"""Engine probe (R8): does a unit on its own go after an enemy out of its weapon's range -- idle, guarding,
attack-moving (missions/acquire_bench.py).

An enemy (s1) Guardian-type tank (weapon 150, vision 200, shroud 500) is made at 1 s at S on the s1 crew 'Aq'; the
player's named NO_ATTACK tank T stands d away (idle / guard: north of S; am: d beside the middle of the path S->E).
Orders at 2 s: idle none; guard TEAM_GUARD the square of half-side 100 round S; am attack-move to E (600 east).
Counters: 起点 (the attacker within 60 of S), 原地 (within 15 of S; idle / guard), 近敌 (within 200 of T),
终点 (within 100 of E; am), 坦克血 (T's health). bench_watch 25 s, every 1 s.
RESULTS (bench 2026-11-07; the s1 side has no reveal: it sees with its own vision 200):
  idle180   起点 1 原地 1 all along; 坦克血 100 -> 86 s2, -14 per 2 s, 3 from s14: it fired WITHOUT moving (within 15
            of S) at a tank 180 off, centre to centre -- the reach is more than the weapon's 150 (target / own
            radius counted?).
  idle200   起点 1; 原地 0 from s1 to s15 (it MOVED toward the tank: 近敌 1 all along), 原地 1 again from s16; 坦克血
            100 -> 86 s2, -14 per 2 s, 3 from s14 (it stops at 3: the same count as idle180).
  idle220   起点 1; 原地 0 s1-s15 (moved), 近敌 1 until s15 then 0 with 原地 1 from s16 (back at S, 220 off); 坦克血
            100 -> 86 s2, -14 per 2 s, 17 at s12, 3 from s13.  So at 220 it still acquires, walks in, fires and returns.
  idle240   起点 1, 原地 1, 近敌 0, 坦克血 100 all 26 s: no move, no shot.  Acquire reach: between 220 and 240
            (vision 200 + the tank's own radius?); idle180 fires in place, idle200 / 220 walk in first.
  idle260   起点 1, 坦克血 100 all 26 s: no move, no shot (beyond its vision 200).  Simulator: the same.
  guard260  (TEAM_GUARD the half-100 square round S) 起点 1, 坦克血 100: no move, no shot.  Simulator: the same.
  am260     walked straight to E (终点 1 from s7), 坦克血 100: no turn aside for a tank 260 beside the path.  Same.
  am400     the same as am260.  Simulator: the same.
  (idle400, guard400 not run: nothing is expected beyond 260.)
  Reading (both tanks a 20 x 12 BOX: bounding circle 23.3): the weapon reaches when the centre distance less both
  radii is within its range (Generals FROM_BOUNDINGSPHERE_2D: 196.6 here -- 180 in place, 200 a step in); an idle
  unit goes after an enemy within its VisionRange + the enemy's radius (223.3: 220 yes, 240 no), fires, and walks
  back to its spot; guarding / attack-moving at 260+ nothing. The simulator (sim.Sim.in_range / idle_chase, R8)
  holds all ten (tests/test_simbench.py 'R8'); its fire is steadier (no clips) and kills the tank (the bench's
  stays at 3: not explained), so it walks home at s18 against the bench's s16.
"""
from parts import Script, Test, counted, square

VARIANTS = ('idle180', 'idle260', 'idle400', 'guard260', 'guard400', 'am260', 'am400', 'idle200', 'idle220', 'idle240')
ATK, TANK = 'UNIT - CNV Aq Atk', 'UNIT - CNV Aq Tank'
RUN = 25.0


def frames(m):
    t = Test()
    v = VARIANTS[m.facts['variant']]
    p1 = m.player('p1')
    team = m.teams['Aq']
    sx, sy = m.point('s')
    t.areas['Test Start'] = square(sx, sy, 60.0)
    t.areas['Test Guard'] = square(sx, sy, 100.0)
    t.areas['Test End'] = square(*m.point('e'), 100.0)
    t.areas['Test Near'] = square(*m.point('t'), 200.0)
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1),
                                                 ('UNIT_CHANGE_OBJECT_STATUS', TANK, 'NO_ATTACK', 1),
                                                 ('SET_MILLISECOND_TIMER', 'Test Make', 1.0),
                                                 ('SET_MILLISECOND_TIMER', 'Test Go', 2.0)]))
    t.scripts.append(Script('Test - make', [('TIMER_EXPIRED', 'Test Make')],
                            [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', ATK, 'AlliedAntiVehicleVehicleTech1',
                              m.team('s1'), m.mark('s')), ('UNIT_SET_TEAM', ATK, team)]))
    go = ('TIMER_EXPIRED', 'Test Go')
    if v.startswith('guard'):
        t.scripts.append(Script('Test - order', [go], m.order('guard', [ATK], 'Test Guard', 's1', crew='Aq')))
    elif v.startswith('am'):
        t.scripts.append(Script('Test - order', [go], m.order('attack_move', [ATK], m.mark('e'), 's1', crew='Aq')))
    t.areas['Test Still'] = square(sx, sy, 15.0)
    counted('CNV_Aq_S', '起点', t, named=ATK, area='Test Start')
    if not v.startswith('am'):
        counted('CNV_Aq_Q', '原地', t, named=ATK, area='Test Still')
    counted('CNV_Aq_N', '近敌', t, named=ATK, area='Test Near')
    if v.startswith('am'):
        counted('CNV_Aq_E', '终点', t, named=ATK, area='Test End')
    counted('CNV_Aq_H', '坦克血', t, health=TANK)
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {f'acquire_{v}': {'frames': frames} for v in VARIANTS}
