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
"""
from parts import Script, Test, counted, square

VARIANTS = ('once', 'every', 'bare', 'tank', 'move', 'alt', 'late')
ATK, WALL, TANK = 'UNIT - CNV Reo Atk', 'UNIT - CNV Reo Wall', 'UNIT - CNV Reo Tank'
RUN = 25.0


def frames(m):
    t = Test()
    v = VARIANTS[m.facts['variant']]
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
