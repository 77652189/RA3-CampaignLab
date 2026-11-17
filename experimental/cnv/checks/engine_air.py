"""Engine probe (air rules): how a Twinblade flies and what an anti-air weapon reaches (missions/air_bench.py, SDK
numbers in its docstring; maps/probe_air.py).

Counters: fly -- 帧 (+1 every frame until the Twinblade is within 100 of E), 飞帧 (the same, only after the Go), 到达
(within 100 of E), 中途 (within 150 of the S-E midpoint); B / C -- 机血 (the Twinblade's health), 原地 (the unit within 15 of its spot);
a2g -- 坦克血, 近100 / 近200 / 近300 (the Twinblade within that square half-side of the tank).  Go at 2 s (fly: move
to E; a2g: attack the tank).  The Twinblade of the range tests is NO_ATTACK and has no order; s1 and p1 both revealed.
bench_watch every 1 s.
RESULTS (bench 2026-11-07; the game's logic runs 15 frames a second: Go at 2 s = frame 30 = 帧 - 飞帧; rows are s = 15
frames; a Twinblade placed by the map STANDS ON THE GROUND and is no air target until it gets a move order -- gun280 and
flak280 placed and left alone: 机血 100 all 25 s; so every B / C Twinblade is placed 30 west and moved at Go to 30 east):
  [bench 2026-11-08 land_still / land_gun / land_flak OVERTURN the above: a Twinblade left on the ground, no order, is shot
  at once -- by the gun from frame ~18 (land_still 66 at s1, 4 at s5) and by the flak trooper (land_flak 91 at s1, 4 at s24);
  only a ground weapon (land_gun, guardian) leaves it at 100.  The 11-07 "100 all 25 s" is not reproduced.]
  fly_flat   帧 144 / 飞帧 114 at arrival (到达 1 from s8; Go at 帧 30 -> 114 frames = 7.6 s for the 1 100 to the edge of the
             100 box: 1 100 / 150 = 7.33 s + the 0.5 s acceleration, so Speed 150 holds); 中途 1 at s4 and s5 only (the
             300-wide box is crossed in 2 s: on the line to within 150).
  fly_sea    the same, row for row: 帧 144 / 飞帧 114, 中途 1 at s4 and s5.
  fly_cliff  the same: 帧 144 / 飞帧 114 (rows 1 off in 帧 by sampling only).  No lane's terrain changes the flight time.
  gun280     机血 100 -> 70 s1, 58 s2, 37 s3, 20 s4, 4 s5 and on (stays at 4: not killed); 原地 1 (a building).
  gun320     机血 100 -> 70 s1, 58 s2, 37 s3, 16 s4, 4 s5: shot as at 280 -- 320 is 300 + 20 over centre to centre, so the
             reach is the weapon's 300 + the radii (edge to edge: 320 - 40.6 = 279), not the centre distance.
  gun370     机血 100 all 26 s: no shot (370 - 40.6 = 329 > 300).  The reach lies between 320 and 370 centres.
  flak280    机血 100 -> 91 s1, then -4 or -5 a second (87, 83, 79, 75, 70 ...) down to 4 at s24; 原地 1: fires in place.
  flak312    the same row for row (91 at s1 ... 4 at s24); 原地 1: fires in place at 312 centre to centre (300 + 12).
  flak354    机血 91 at s1 ... 4 at s25 as well, but 原地 0 from s1 to s25 (it WALKED in, 1 back at s26): at 354 (300 + 5 +
             19.4 + 30) it acquired and chased (vision 200 / aircraft vision 170, but both sides are revealed here).
  noaa       机血 100, 原地 1 all 21 s: an s1 guardian under a Twinblade 100 off does nothing (AntiMask WATER GROUND
             STRUCTURE).
  land_flak  (s1 flak trooper 280 north, Twinblade NO_ATTACK, no order, both revealed) 机血 91 s1, 83 s3, 66 s7, 50 s12, 33
             s16, 16 s20, 4 s24 on; 原地 1 all 26 s (the trooper fires in place): as flak280 moved.
  (bench 2026-11-08, the Twinblade LEFT ON THE GROUND where the map put it, 'air B'; land_*: 坦克血 / 机血 / 原地 as above)
  land_gun   (s1 guardian 100 north shoots, Twinblade NO_ATTACK, no order) 机血 100 for all 26 s: a ground Twinblade is not
             hit by a ground weapon.
  land_takeoff  (s1 gun 280 north + plant; move order at Go = frame 30; 总帧 counts all frames, 掉血帧 frames with health
             under 99, 令后帧 frames since Go) 机血 66 s1, 54 s2, 37 s3, 16 s4, 4 s5 on; 掉血帧 26 where 总帧 is 44: the first
             loss is at frame ~18, i.e. 12 frames BEFORE the order (a counter of frames from the order with health 100 stays 0).
  land_still (the same without any order) 机血 66 s1, 50 s2, 29 s3, 12 s4, 4 s5 on; 掉血帧 26 at 总帧 44: the same first
             loss at frame ~18 -- not the order's doing; the gun hits this ground-placed Twinblade by itself (contradicts the
             gun280 'unplaced: 100 all 25 s' above, whose Twinblade stood 30 west; not explained).
  land_idle  (Twinblade may fire, s1 guardian NO_ATTACK 120 north, no order) 坦克血 97 s1, 90 s7, 52 s8, 46 s9 ... 38 s16,
             dead s17; 原地 1 all 23 s: it fires on its own from where it stands and does not take off.
  land_atk   (the same, attack order at Go) 坦克血 97 s1, 92 s5-s7, 74 s9, 46 s10 ... 38 s17, 10 s18, dead s19; 原地 1 all
             26 s: the attack order changes nothing (it already shot before Go); no take-off, it fires from the ground.
  a2g        坦克血 100 until s3; 近300 1 from s3, 近200 1 from s4, 近100 0 all along: the Twinblade stops 100-200 off
             (the weapon's 150 + both radii = 193 centre to centre) and does not fly overhead.  Tank health: 99 s4, 98 s5,
             96 s6, 95 s7 (the autocannon, ~1 a second), 68 s8, 51 s9 (a missile volley -27, -17), 50 .. 43 to s16, 16 s17
             (-27), 5 from s18 to the end of the 40 s (not dead: no further hit in 23 s).
"""
from parts import Script, Test, counted, square

FLY = ('fly_flat', 'fly_sea', 'fly_cliff')
RANGE = {'gun': (280, 320, 370), 'flak': (280, 312, 354)}
VARIANTS = FLY + tuple(f'{k}{d}' for k, ds in RANGE.items() for d in ds) + ('noaa', 'a2g', 'land_gun', 'land_takeoff', 'land_idle', 'land_atk', 'land_still', 'land_flak')
HELI, UNIT, TANK = 'UNIT - CNV Air Heli', 'UNIT - CNV Air Unit', 'UNIT - CNV Air Target'
RUN = {'a2g': 40.0, 'noaa': 20.0, 'land_gun': 25.0, 'land_takeoff': 15.0, 'land_idle': 20.0, 'land_atk': 20.0, 'land_still': 15.0, 'land_flak': 25.0}


def frames(m):
    t = Test()
    v = VARIANTS[m.facts['variant']]
    p1, s1 = m.player('p1'), m.player('s1')
    start = [('MAP_REVEAL_ALL_PERM', p1), ('MAP_REVEAL_ALL_PERM', s1), ('SET_MILLISECOND_TIMER', 'Test Go', 2.0)]
    go = ('TIMER_EXPIRED', 'Test Go')
    if v in FLY:
        sx, sy = m.point('s')
        ex, ey = m.point('e')
        mx, my = m.point('mid')
        t.areas['Test Start'] = square(sx, sy, 60.0)
        t.areas['Test End'] = square(ex, ey, 100.0)
        t.areas['Test Mid'] = square(mx, my, 150.0)
        start.append(('UNIT_CHANGE_OBJECT_STATUS', HELI, 'NO_ATTACK', 1))
        t.scripts.append(Script('Test - start', [], start))
        t.scripts.append(Script('Test - order', [go], m.order('move', [HELI], m.mark('e'), 'p1', crew='Ah')))
        t.scripts.append(Script('Test - went', [go], [('SET_FLAG', 'Test Went', 1)]))
        t.counters += [('CNV_Air_F', '帧'), ('CNV_Air_G', '飞帧')]
        t.scripts.append(Script('Test - frame', [('NAMED_OUTSIDE_AREA', HELI, 'Test End')],
                                [('INCREMENT_COUNTER', 1, 'CNV_Air_F')], once=False))
        t.scripts.append(Script('Test - fly frame', [('NAMED_OUTSIDE_AREA', HELI, 'Test End'), ('FLAG', 'Test Went', 1)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Air_G')], once=False))
        counted('CNV_Air_E', '到达', t, named=HELI, area='Test End')
        counted('CNV_Air_M', '中途', t, named=HELI, area='Test Mid')
        t.bench = [('bench_watch', dict(seconds=14.0, every=1, sheet=False, lines=len(t.counters)))]
        return t
    if v == 'a2g':
        tx, ty = m.point('t')
        for r in (100, 200, 300):
            t.areas[f'Test Near {r}'] = square(tx, ty, float(r))
        start.append(('UNIT_CHANGE_OBJECT_STATUS', TANK, 'NO_ATTACK', 1))
        t.scripts.append(Script('Test - start', [], start))
        t.scripts.append(Script('Test - order', [go], m.order('attack', [HELI], TANK, 'p1', crew='Ah')))
        counted('CNV_Air_H', '坦克血', t, health=TANK)
        for r in (100, 200, 300):
            counted(f'CNV_Air_N{r}', f'近{r}', t, named=HELI, area=f'Test Near {r}')
    elif v.startswith('land_'):
        ux, uy = m.point('u')
        t.areas['Test Still'] = square(ux, uy, 15.0)
        if v in ('land_gun', 'land_takeoff', 'land_still', 'land_flak'):
            start.append(('UNIT_CHANGE_OBJECT_STATUS', HELI, 'NO_ATTACK', 1))
        if v in ('land_idle', 'land_atk'):
            start.append(('UNIT_CHANGE_OBJECT_STATUS', TANK, 'NO_ATTACK', 1))
        t.scripts.append(Script('Test - start', [], start))
        if v in ('land_takeoff', 'land_still'):
            if v == 'land_takeoff':      # land_still: no order, the same counters (is the hit the order's doing?)
                t.scripts.append(Script('Test - order', [go], m.order('move', [HELI], m.mark('h'), 'p1', crew='Ah')))
            t.scripts.append(Script('Test - went', [go], [('SET_FLAG', 'Test Went', 1)]))
            # 令后帧 - 掉血帧 = frames from the order to the first hit (掉血帧: frames with health under 99)
            t.counters += [('CNV_Air_F', '掉血帧'), ('CNV_Air_G', '令后帧'), ('CNV_Air_B', '总帧')]
            t.scripts.append(Script('Test - all frames', [], [('INCREMENT_COUNTER', 1, 'CNV_Air_B')], once=False))
            t.scripts.append(Script('Test - hurt frames', [('UNIT_HEALTH', HELI, 0, 99)],
                                    [('INCREMENT_COUNTER', 1, 'CNV_Air_F')], once=False))
            t.scripts.append(Script('Test - frames after', [('FLAG', 'Test Went', 1)],
                                    [('INCREMENT_COUNTER', 1, 'CNV_Air_G')], once=False))
            counted('CNV_Air_H', '机血', t, health=HELI)
        elif v in ('land_gun', 'land_flak'):
            counted('CNV_Air_H', '机血', t, health=HELI)
            if v == 'land_flak':       # the trooper's own 15 box: does it stay or walk?
                fx, fy = m.point('f')
                t.areas['Test Flak'] = square(fx, fy, 15.0)
                counted('CNV_Air_Q', '原地', t, named=UNIT, area='Test Flak')
        else:
            if v == 'land_atk':
                t.scripts.append(Script('Test - order', [go], m.order('attack', [HELI], TANK, 'p1', crew='Ah')))
            counted('CNV_Air_H', '坦克血', t, health=TANK)
            counted('CNV_Air_Q', '原地', t, named=HELI, area='Test Still')
    else:
        ux, uy = m.point('u')
        t.areas['Test Still'] = square(ux, uy, 15.0)
        start.append(('UNIT_CHANGE_OBJECT_STATUS', HELI, 'NO_ATTACK', 1))
        t.scripts.append(Script('Test - start', [], start))
        # moved at Go 60 east (kept from 11-07, when a placed Twinblade was thought no air target; land_* 11-08: it is)
        t.scripts.append(Script('Test - order', [go], m.order('move', [HELI], m.mark('h'), 'p1', crew='Ah')))
        counted('CNV_Air_H', '机血', t, health=HELI)
        counted('CNV_Air_Q', '原地', t, named=UNIT, area='Test Still')
    t.bench = [('bench_watch', dict(seconds=RUN.get(v, 25.0), every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {f'air_{v}': {'frames': frames} for v in VARIANTS}
