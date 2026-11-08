"""Engine probe: does a unit walk when a script gives it the same order again every frame
(missions/reorder_bench.py; A4's Ghost King, devices/horn.py ghost_scripts).

An enemy (s1) Athena-type tank is made at 1 s on the s1 crew 'Reo' at S; the player's named ice wall W stands 900
north (out of range), the player's named NO_ATTACK tank T beside it, move point M 600 from S. Orders from 2 s:
  once   one m.order('attack', wall)                       (control)
  every  the whole m.order (UNIT_SET_TEAM + TEAM_ATTACK_NAMED) every frame
  bare   only TEAM_ATTACK_NAMED every frame
  tank   m.order('attack', tank) every frame
  move   m.order('move', M) every frame
  alt    attack the wall, then attack the tank, two scripts, every frame
  late   once at 2 s, from 6 s every frame again
Counters: 起点 (within 100 of S), 中途 (within 150 of (0,0)), 近墙 (in the square of half-side 170 round (0,330)),
墙血 (the wall's health; tank: 坦克血). bench_watch 25 s, every 1 s.
RESULTS (bench 2026-11-07; bench s; counters 起点 中途 近墙 墙血; the check logs 2-s rows):
  S first tried at (0, -500): on the water's edge, the unit did not move for ANY order (even move), 起点 1 all 26 s:
    a blocked spot, not an order effect; S moved to (0, -400).
  once   起点 0 from s2; 中途 1 s4-s7; 近墙 1 from s8; 墙血 100 to s9, 96 at s10, -4 per 2 s, 64 at s26.
  every  (full order each frame): identical to once.
  bare   (TEAM_ATTACK_NAMED only each frame): identical to once.
  tank   起点 0 s2; 中途 s4-s7; 近墙 1 only at s8 (passes it), then 0 (the tank is outside the box, x 250);
         坦克血 100 to s9, 86 s10, -14 per 2 s, 3 at s22-s26. It walked and fired.
  move   起点 0 s2; 中途 s4-s7; 近墙 1 from s8 to the end (stops at M): it walked and stayed.
  alt    wall then tank each frame: 起点 0 s2; 中途 s4-s7; 近墙 1 only s8, then 0; 墙血 100 to the end: it walked
         (the last order of the frame, the tank, rules; the wall was never shot). Tank health not read in this run.
  late   once at 2 s, every frame from 6 s: identical to once (no stop at 6 s; 墙血 96 at s10, 64 at s26).
  Reading: re-giving the SAME order (or a different one) every frame does not stop a unit here: it walks and fires
  in all seven variants. So A4's King standing still is not caused by the every-frame re-order itself.

Second round (bench 2026-11-07), A4's King on the bench: attacker = JapanAntiVehicleVehicleTech3 (KING), the 'g'
variants the Athena tank. Offsets are from 'west field'; the mod names are CampRo + D1/De/Dg/U1/Ue/Ug (+ Frames).
 A. Detour (dt*): a row of 11 unnamed ice-wall blocks CNV_ReoBar (80 wide, step 70, x -420..250, one at 250, y 50,
    role 'bar'): the gap only east of x 290. Attack W (0, 500) from 2 s. Counters 起点 (100 round S), 绕口 (square
    120 round (380, 50)), 近墙 (Test Near), 墙血. bench_watch 45 s.
   dt1   once at 2 s       起点 1 s1-s2, 0 from s3; 绕口 1 s7-s10; 近墙 1 from s13; 墙血 100 to s15, 88 at s16, -12
                           per ~2 s, 6 from s30 to s46.
   dtev  every frame       起点 1 s1-s2; 绕口 1 s7-s10; 近墙 1 from s14; 墙血 100 to s15, 88 at s16, 6 from s31.
   dtevg every frame, Athena  起点 1 s1; 绕口 1 s6-s9; 近墙 1 from s11; 墙血 100 to s12, 96 at s13, -4 per ~2 s,
                           32 at s50 (the Athena is the weak shooter).
   All three went round the gap (绕口 1 for 3-4 s), stopped near the wall and fired; no difference between once and
   every frame.
 B. Turn (tu*): at 2 s a move order S to P; from 14 s the attack order on a new named wall W2 (CNV_ReoWall,
    'UNIT - CNV Reo Wall2'). Counters 起点, 在P (square 80 round P), 墙2血. bench_watch 35 s.
    First tried P (-300, -400), W2 (-300, -250), west as asked: both in the water west of the coast (preview), the
    unit never moved (起点 1 until s13), W2 not shot: a blocked spot, not an order effect. Moved EAST:
    P (200, -400), W2 (200, -250) (due north of P, the unit stands facing east, a 90 degree turn).
   tu1   once at 14 s      起点 0 from s2; 在P 1 from s3 to the end; 墙2血 100 to s13, 88 at s14, -12 per ~2 s,
                           6 from s26.
   tuev  every frame from 14 s   起点 0 from s2; 在P 1 from s3; 墙2血 100 to s13, 88 at s14, 6 from s29.
   tuevg every frame, Athena     起点 0 from s2; 在P 1 from s2; 墙2血 100 to s12, 96 at s13, -4 per ~2 s, 52 at s35.
   Reading: with the every-frame attack order, in these runs the unit (King and Athena) detoured round the barrier,
   or turned 90 degrees on the spot, and fired at the same time as with a single order (first damage within ~1-2 s
   of the target being in reach / the order); the wall health fell at the same rate once and every frame. This
   bench did not reproduce the A4 stand-still (bridge detour); the difference to A4 is not located here.
"""
from parts import Script, Test, counted, square

# same order as missions/reorder_bench.py (architecture test G5: a check does not import missions)
OLD = ('once', 'every', 'bare', 'tank', 'move', 'alt', 'late')
DT = ('dt1', 'dtev', 'dtevg')
TU = ('tu1', 'tuev', 'tuevg')
VARIANTS = OLD + DT + TU
WALL2 = 'UNIT - CNV Reo Wall2'
KING, ATHENA = 'JapanAntiVehicleVehicleTech3', 'AlliedAntiVehicleVehicleTech1'
ATK, WALL, TANK = 'UNIT - CNV Reo Atk', 'UNIT - CNV Reo Wall', 'UNIT - CNV Reo Tank'
RUN = 25.0


def frames_new(m, v):
    """dt* / tu* variants: the attacker is the Ghost King (g suffix: Athena tank)."""
    t = Test()
    p1 = m.player('p1')
    team = m.teams['Reo']
    kind = ATHENA if v.endswith('g') else KING
    every = v.endswith('ev') or v.endswith('evg')
    t.areas['Test Start'] = square(*m.point('s'), 100.0)
    t.areas['Test Near'] = square(*m.point('near'), 170.0)
    tgt = WALL2 if v in TU else WALL
    order = lambda kind_, target: m.order(kind_, [ATK], target, 's1', crew='Reo')
    attack_o = order('attack', tgt)
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1)]
                            + [('SET_MILLISECOND_TIMER', 'Test Make', 1.0),
                               ('SET_MILLISECOND_TIMER', 'Test Go', 14.0 if v in TU else 2.0)]
                            + ([('SET_MILLISECOND_TIMER', 'Test Walk', 2.0)] if v in TU else [])))
    t.scripts.append(Script('Test - make', [('TIMER_EXPIRED', 'Test Make')],
                            [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', ATK, kind, m.team('s1'), m.mark('s')),
                             ('UNIT_SET_TEAM', ATK, team)]))
    if v in TU:
        t.scripts.append(Script('Test - walk', [('TIMER_EXPIRED', 'Test Walk')], order('move', m.mark('p'))))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Go')], attack_o, once=not every))
    counted('CNV_Reo_S', '起点', t, named=ATK, area='Test Start')
    if v in DT:
        t.areas['Test Gap'] = square(*m.point('gap'), 120.0)
        counted('CNV_Reo_G', '绕口', t, named=ATK, area='Test Gap')
        counted('CNV_Reo_N', '近墙', t, named=ATK, area='Test Near')
        counted('CNV_Reo_H', '墙血', t, health=WALL)
        run = 45.0
    else:
        t.areas['Test P'] = square(*m.point('p'), 80.0)
        counted('CNV_Reo_P', '在P', t, named=ATK, area='Test P')
        counted('CNV_Reo_H', '墙2血', t, health=WALL2)
        run = 35.0
    t.bench = [('bench_watch', dict(seconds=run, every=1, sheet=False, lines=len(t.counters)))]
    return t


def frames(m):
    v = VARIANTS[m.facts['variant']]
    if v in DT or v in TU:
        return frames_new(m, v)
    t = Test()
    p1 = m.player('p1')
    team = m.teams['Reo']
    t.areas['Test Start'] = square(*m.point('s'), 100.0)
    t.areas['Test Mid'] = square(*m.point('mid'), 150.0)
    t.areas['Test Near'] = square(*m.point('near'), 170.0)
    full = lambda kind, target: m.order(kind, [ATK], target, 's1', crew='Reo')
    tgt = TANK if v == 'tank' else WALL
    wall_o, tank_o = full('attack', WALL), full('attack', TANK)
    timers = [('SET_MILLISECOND_TIMER', 'Test Make', 1.0), ('SET_MILLISECOND_TIMER', 'Test Go', 2.0)]
    if v == 'late':
        timers.append(('SET_MILLISECOND_TIMER', 'Test Late', 6.0))
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1),
                                                 ('UNIT_CHANGE_OBJECT_STATUS', TANK, 'NO_ATTACK', 1)] + timers))
    t.scripts.append(Script('Test - make', [('TIMER_EXPIRED', 'Test Make')],
                            [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', ATK, 'AlliedAntiVehicleVehicleTech1',
                              m.team('s1'), m.mark('s')), ('UNIT_SET_TEAM', ATK, team)]))
    go = ('TIMER_EXPIRED', 'Test Go')
    if v == 'once':
        t.scripts.append(Script('Test - order', [go], wall_o))
    elif v == 'every':
        t.scripts.append(Script('Test - order', [go], wall_o, once=False))
    elif v == 'bare':
        t.scripts.append(Script('Test - order', [go], [wall_o[-1]], once=False))
    elif v == 'tank':
        t.scripts.append(Script('Test - order', [go], tank_o, once=False))
    elif v == 'move':
        t.scripts.append(Script('Test - order', [go], full('move', m.mark('m')), once=False))
    elif v == 'alt':
        t.scripts += [Script('Test - order wall', [go], wall_o, once=False),
                      Script('Test - order tank', [go], tank_o, once=False)]
    elif v == 'late':
        t.scripts += [Script('Test - order', [go], wall_o),
                      Script('Test - order again', [('TIMER_EXPIRED', 'Test Late')], wall_o, once=False)]
    counted('CNV_Reo_S', '起点', t, named=ATK, area='Test Start')
    counted('CNV_Reo_M', '中途', t, named=ATK, area='Test Mid')
    counted('CNV_Reo_N', '近墙', t, named=ATK, area='Test Near')
    counted('CNV_Reo_H', '坦克血' if v == 'tank' else '墙血', t, health=tgt)
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {f'reorder_{v}': {'frames': frames} for v in VARIANTS}
