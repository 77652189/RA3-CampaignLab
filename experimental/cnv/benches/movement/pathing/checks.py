"""Movement and pathing bench checks and their inline scenes."""


COLUMN_RUN = 30.0


def column_key(lane, k):
    """The man's name is `UNIT - CNV Col <key>`."""
    return f'{lane.title()}M{k + 1}'


def drop_key(lane, k):
    """The unit's name is `UNIT - CNV Drop <key>`."""
    return f'{lane.title()}{k + 1}'


FORMATION_LANES = {'plain': 1230.0, 'formation': 1390.0}


FORMATION_X0 = 650.0


JET_TEMPLATE = 'AlliedAntiGroundAircraft'


PACE_PLACED_BENCH = {
    'paceplaced': {'tank': (88, 90), 'foot': (90, 93), 'held': (33, 84)},
    'paceplacedn': {'tank': (74, 74), 'foot': (91, 93)},
}


def engine_a01sq():
    """Engine unit tests, R3 step X (ADR 0032 5): where the first Allied mission's starting squad stops when it is sent to
    one point -- tests/test_retail_sim.py's question 1 (docs/story/retail-q1-a01.md), whose closest pair was ~42 read off
    a screenshot (11-09, units as team-blue blobs) against 27.6 on the probe bench (engine_column d6: a turned block,
    each spot snapped to its cell's centre, diagonal neighbours 20 * sqrt(2)). The bench cannot put a probe on a01 itself
    (the plain game loads no mod, ra3ext only starts with one), so the squad is copied: 4 Peacekeepers and 2 dogs, each a
    copy with ra3ext's read-only CNVProbe, standing as a01's squad stands when the intro hands it over (the simulator's
    a01 at 22.6 s), the point as far and in the same direction, and every coordinate moved by whole 20-cells (the snap
    sees the same fractions); on the blocked-way probe map's open ground (maps/probe_block.py).

      engine_a01sq squad   team   a01's squad (4 Peacekeepers, 2 dogs), one MOVE_TEAM_TO (the test's `走 队`)
                           pk6    the same spots, all six Peacekeepers: what the dogs change
                           click  a01's squad again, box-selected and right-clicked by the bench (the 11-09 order)

    No expectations: the readings are the probe lines (work/re/scripts/x_a01sq.py reads them against the simulator's stops).
    """
    import math
    import os

    import labpaths
    from maps import probe_block
    from parts import Mission, Script, Test, Unit

    MAN, DOG = 'AlliedAntiInfantryInfantry', 'AlliedScoutInfantry'
    PROBE = {MAN: 'CNV_A01Man', DOG: 'CNV_A01Dog'}
    EVERY, LINES = 150, 6000
    A01_POINT = (505.2, 1576.7)
    # a01's squad at the hand-over (simulator, retail a01 at 22.6 s): (template, x, y)
    A01_SQUAD = ((DOG, 410.0, 1630.0), (DOG, 390.0, 1670.0), (MAN, 390.0, 1610.0), (MAN, 333.3, 1669.8),
                 (MAN, 323.5, 1593.6), (MAN, 303.9, 1620.5))
    SHIFT = {'team': (2500.0, 420.0), 'pk6': (2500.0, 820.0), 'click': (2500.0, 1220.0)}   # whole 20-cells
    RUN = 20.0


    def point(lane):
        dx, dy = SHIFT[lane]
        return A01_POINT[0] + dx, A01_POINT[1] + dy


    def starts(lane):
        """[(template, x, y)] of the lane's six."""
        dx, dy = SHIFT[lane]
        return [(MAN if lane == 'pk6' else tpl, x + dx, y + dy) for tpl, x, y in A01_SQUAD]


    def probe_copy(template):
        pid = PROBE[template]
        with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', template + '.xml'), encoding='utf-8') as f:
            x = f.read()
        assert x.count(f'id="{template}"') == 1 and x.count('<Behaviors>') == 1
        x = x.replace(f'id="{template}"', f'id="{pid}"', 1).replace(f'EditorName="{template}"', f'EditorName="{pid}"')
        x = x.replace('<Behaviors>', (f'<Behaviors>\n'
            f'\t\t\t<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>'), 1)
        return Unit(pid, x, names=dict(unit=pid), what=f'原版 {template} 的复制（探针）：多一个 ra3ext 的 CNVProbe，逐帧记位置',
                    params=dict(of=template, every=EVERY, lines=LINES))


    def mission():
        m = Mission(name='CampA01Sq', map=probe_block, units=[probe_copy(MAN), probe_copy(DOG)], facts={})
        m.ext = True
        sx, sy = m.site('island')
        for lane in SHIFT:
            px, py = point(lane)
            for k, (tpl, x, y) in enumerate(starts(lane)):
                m.put(PROBE[tpl], 'island', x - sx, y - sy, role=f'{lane} {k + 1}',
                      name=f'UNIT - CNV A01 {lane.title()}M{k + 1}', angle=math.atan2(py - y, px - x))
        return m


    def squad(m):
        t = Test()
        go = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for lane in ('team', 'pk6'):
            wp = f'Test A01 {lane.title()} Point'
            t.waypoints[wp] = point(lane)
            go += m.order('move', [m.role(f'{lane} {k + 1}').name for k in range(len(A01_SQUAD))], wp,
                          crew=f'A01{lane.title()}')
        t.scripts.append(Script('Test - go', [], go))
        xs = [x for _, x, _ in starts('click')]
        ys = [y for _, _, y in starts('click')]
        px, py = point('click')
        t.bench = [('bench_view', dict(x=(min(xs) + px) / 2, y=(min(ys) + max(ys)) / 2, look=True)),
                   ('bench_box', dict(x0=min(xs) - 25, y0=min(ys) - 25, x1=max(xs) + 25, y1=max(ys) + 25, look=True)),
                   ('bench_click', dict(x=px, y=py, right=True, look=True)),
                   ('bench_watch', dict(seconds=RUN * 15.0 / 3.0, every=20, sheet=False, lines=2))]
        t.expect = []
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_a01sq': mission}
    CHECKS = {'engine_a01sq': {'squad': squad}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_air():
    """Engine probe (air rules): how a Twinblade flies and what an anti-air weapon reaches (engine_air in scenes.py, SDK
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
    return dict(CHECKS=CHECKS)


def engine_airin():
    """engine_airin:go -- TEAM_ENTER_NAMED(team, object) (retail a01: two cryocopter teams of Allied02 told to enter Allied01's
    two airfields, made under them a moment before; a08's line names a team and an airfield its map never makes).
    AlliedAirfield's CanParkHereFilter takes SAME_PLAYER ALLIES but excludes AlliedSupportAircraft (the cryocopter).

    On probe_range five lanes, each a Player_1 airfield at a gun pad and two aircraft 700 north of it, ordered at 2 s:
      己机 (base)    Player_1's two Apollos, their team told to enter the airfield
      友机 (high)    the same, Soviet_2's (made Player_1's friend both ways)
      己直 (removed) Player_1's two cryocopters, told to enter
      友直 (switch)  Soviet_2's two cryocopters, told to enter (a01's case)
      闲机 (order)   Player_1's two Apollos, no order (does an idle jet go home by itself?)
    A lane's reading: its aircraft inside 300 of the airfield + 10 x those AIRBORNE_TARGET + 100 x PARKED_AT_AIRFIELD;
    the friend's lane x 1000 on its own lane's counter (four counter lines at most)."""
    from maps import probe_range
    from parts import Mission, Test, square, status
    from checks import engine_scripts8 as s8

    JET, COPTER = 'AlliedFighterAircraft', 'AlliedSupportAircraft'
    LANES = {'base': ('己机', JET, 'p1', 'order'), 'high': ('友机', JET, 's2', 'order'),
             'removed': ('己直', COPTER, 'p1', 'order'), 'switch': ('友直', COPTER, 's2', 'order'),
             'order': ('闲机', JET, 'p1', None)}


    def _n(lane, k):
        return f'UNIT - CNV AirIn {lane.title()} {k}'


    def mission():
        m = Mission(name='CampAirIn', map=probe_range, units=[], facts={})
        for lane, (_, kind, side, _) in LANES.items():
            m.put('AlliedAirfield', f'{lane} gun', role=f'{lane} field', name=f'UNIT - CNV AirIn {lane.title()} Field')
            for k in (1, 2):
                m.put(kind, f'{lane} gun', 120.0 * k - 180.0, 700.0, side=side, role=f'{lane} {k}', name=_n(lane, k))
        return m


    def go(m):
        t = Test()
        p, ally = m.player('p1'), m.player('s2')
        orders = [('MAP_REVEAL_ALL_PERM', p), ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
                  ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend'))]
        s8.at(t, 'friend', 0.1, orders)
        enter = []
        for lane, (_, _, side, order) in LANES.items():
            if order:
                crew = m.crew(f'AirIn{lane.title()}', side)
                enter += [('UNIT_SET_TEAM', _n(lane, k), crew) for k in (1, 2)]
                enter.append(('TEAM_ENTER_NAMED', crew, m.role(f'{lane} field').name))
        s8.at(t, 'enter', 2.0, enter)
        for counter, lanes in (('Jet', ('base', 'high')), ('Copter', ('removed', 'switch')), ('Idle', ('order',))):
            parts = []
            for scale, lane in zip((1, 1000), lanes):
                area = f'Test AirIn {lane.title()} Near'
                t.areas[area] = square(*m.site(f'{lane} gun'), 300.0)
                for k in (1, 2):
                    parts += [(scale, ('NAMED_INSIDE_AREA', _n(lane, k), area)),
                              (10 * scale, ('UNIT_HAS_OBJECT_STATUS', _n(lane, k), status('AIRBORNE_TARGET'))),
                              (100 * scale, ('UNIT_HAS_OBJECT_STATUS', _n(lane, k), status('PARKED_AT_AIRFIELD')))]
            s8.total(t, f'CNV_AirIn_{counter}', '+千'.join(LANES[lane][0] for lane in lanes), parts)
        s8.watch(t, 50.0, 1.0)
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_airin': mission}
    CHECKS = {'engine_airin': {'go': go}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_bits():
    """Engine unit test: what BlendTileData's other bit fields do for passing, and at what height the game's logic puts the
    water (docs/engine/terrain.md 3 and 1; engine line round 9).

    On the probe map (maps/probe_bits.py) each pen holds two units, both ordered by script to the point 280 north, outside
    the pen's ring. A pen's counter adds 1 for the first and 10 for the second standing there: 11 both got out, 1 only
    the first, 10 only the second, 0 neither.

    bits (row 1):
      players        field 1 on the ring; the player's tank (1), warrior (10)
      air            field 6 on the ring; the player's Cryocopter (1), tank (10)
      zero three     fields 0 and 3; the player's tank (1), warrior (10): does field 3 open what field 0 shut
      players enemy  field 1 again, far east (out of reach of the player's units); the enemy's tank (1), warrior (10):
                     which side field 1 holds back
    enemy: players enemy as above, and zero (field 0 only; the enemy's tank, warrior): the control that the enemy's units
      obey field 0 too -- run it when players enemy reads 0.
    water (row 2): moats with floors at 270 / 300 / 315 / 330 ours (169 / 187.5 / 197 / 206 world, the water at 200
      world); the player's tank (1), warrior (10) each.

    Expected (测, 2026-11-04, run CampBitsBits / CampBitsWater): field 1 holds the player's units but not the enemy's;
    field 3 does not open field 0; field 6 held neither the Cryocopter nor the tank (the first run guessed "aircraft only"
    and read 11); the water's logic edge lies between 315 and 330 ours, as the game's scale puts 200 world at 320.
    """
    from maps import probe_bits
    from parts import Mission, Script, Test, square

    TANK = 'AlliedAntiVehicleVehicleTech1'
    ENEMY_TANK = 'SovietAntiVehicleVehicleTech1'
    WARRIOR = 'JapanAntiInfantryInfantry'
    COPTER = 'AlliedSupportAircraft'
    _PAIR = (('tank', TANK, 'p1', 1), ('warrior', WARRIOR, 'p1', 10))
    _ENEMY = (('enemy tank', ENEMY_TANK, 's1', 1), ('enemy warrior', WARRIOR, 's1', 10))
    # pen: ((part, template, side, worth), ...)
    WHO = {
        'players': _PAIR,
        'air': (('copter', COPTER, 'p1', 1), ('tank', TANK, 'p1', 10)),
        'zero three': _PAIR,
        'players enemy': _ENEMY,
        'zero': _ENEMY,
        'moat 270': _PAIR,
        'moat 300': _PAIR,
        'moat 315': _PAIR,
        'moat 330': _PAIR,
    }
    LABEL = {'players': '玩家位', 'air': '空军位', 'zero three': '零加三', 'players enemy': '玩家位敌', 'zero': '零位敌',
             'moat 270': '沟270', 'moat 300': '沟300', 'moat 315': '沟315', 'moat 330': '沟330'}
    ROWS = {'bits': ('players', 'air', 'zero three', 'players enemy'), 'enemy': ('players enemy', 'zero'),
            'water': ('moat 270', 'moat 300', 'moat 315', 'moat 330')}
    EXPECT = {'players': 0, 'air': 11, 'zero three': 0, 'players enemy': 11, 'zero': 0,
              'moat 270': 0, 'moat 300': 0, 'moat 315': 0, 'moat 330': 11}
    RUN = 24.0


    def _key(pen):
        return pen.title().replace(' ', '')


    def mission():
        m = Mission(name='CampBits', map=probe_bits, facts={})
        for pen, who in WHO.items():
            for k, (part, template, side, _) in enumerate(who):
                m.put(template, pen, -30.0 + 60.0 * k, 0, side=side, name=f'UNIT - CNV Bits {_key(pen)} {_key(part)}',
                      role=f'{pen} {part}')
        return m


    def _row(m, pens):
        t = Test()
        order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for pen in pens:
            out = f'Test Bits {_key(pen)} Out'
            t.waypoints[out] = m.site(f'{pen} out')
            t.areas[out] = square(*m.site(f'{pen} out'), 70)
            counter = f'CNV_Bits_{_key(pen)}'
            t.counters.append((counter, LABEL[pen]))
            t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
            for part, _, _, worth in WHO[pen]:
                name = m.role(f'{pen} {part}').name
                order.append(('MOVE_NAMED_UNIT_TO', name, out))
                t.scripts.append(Script(f'Test - {counter} {_key(part)}', [('NAMED_INSIDE_AREA', name, out)],
                                        [('INCREMENT_COUNTER', worth, counter)], once=False))
            t.expect.append((LABEL[pen], RUN - 2, '==', EXPECT[pen]))
        t.scripts.insert(0, Script('Test - go', [], order))
        t.bench = [('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=4))]
        return t


    def bits(m):
        return _row(m, ROWS['bits'])


    def enemy(m):
        return _row(m, ROWS['enemy'])


    def water(m):
        return _row(m, ROWS['water'])


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_bits': mission}
    CHECKS = {'engine_bits': {'bits': bits, 'enemy': enemy, 'water': water}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def blackcanyon():
    """A2's map (maps/blackcanyon.py) on the bench: the four questions its draft left (work/mappage/a2/notes.md, r6).
    The mission is the bare map; each check puts down what it asks about. Predictions (from SageXML and the map's
    heights and walk grid, before the bench) are the expectations.

    foot:  Stingrays in the river below the dam: three ordered at the powerhouse on the level-1 ledge (river bed 220,
           ledge 340, crest 455), two at a player plant beside it, two only moved to the tailrace pool. Predicted: they
           reach the pool (amphibious) and hurt both from it or up the boat slip (tesla 125).
    v4:    two V4s on the Arizona overlook (570 high), one ordered at a plant on the crest's east section, one at the
           west's. Predicted: rocket range 500 (minimum 200); east is 516 from the overlook's middle, ~380 from its west
           rim, so the first fires from up there; west is ~590 even from the rim, so the second drives off.
    camp:  three Hammers from the Soviet camp at a plant on crest west, three Tesla tanks at one on crest east.
           attack_routes (11-24): to west 3999 by the bridge, ~4000 round the east side (a tie, the bridge by a hair);
           to east 3766 round the east side, ~4230 by the bridge. Predicted: Hammers over the bridge, Teslas round east.
    crest: eight Hammers moved across the crest east to west (760), eight on open ground the same length (the
           control). The crest is 80 walkable across its whole run, both ends too (the rect is 130, the cliff takes 25 a
           side). Predicted: all eight get over, two abreast, the tail later than the control's.
    Bench 2026-11-24: v4 PASS (east 37 by s13 from up there; the west one off the overlook at s9). crest PASS (all eight
    over by s21, the control by s19). foot r7 (the powerhouse still neutral): the movers in the pool, the plant 100 -> 4
    shot from the water, the powerhouse's three never set out (100) -- a neutral prop is no one's target, so the map
    gives it to the player. camp r7: the Teslas round east, Hammer 0 in the camp all run -- they stood in a warehouse
    (4200, 780), moved west of it. (The counter reader misreads a long line's last digit, 1 as 7: read the frames.)
    r8, the dam the player's Allied plants (readings: blackcanyon.readings.toml): ath, the Athena on an enemy plant 50
    beside the player's own: both 100 -> 25 -> 2 (its beam hurts SELF ALLIES too). sell: CANNOT_BE_SOLD set, SELL_OBJECT
    still sells it. roads (plan-wave team orders): conscripts over the bridge at crest west, Hammers down the bend at crest
    east, both shot down. last: lake Stingrays land at the beach and drive to crest west; V4s hit east from the road.
    """
    from parts import Obj, Script, Test
    from model import counted, square, status

    RAY, V4 = 'SovietAntiNavyShipTech1', 'SovietAntiStructureVehicle'
    HAMMER, TESLA, PLANT = 'SovietAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech2', 'SovietPowerPlant'
    DAM, ATHENA, CONSCRIPT = 'AlliedPowerPlant', 'AlliedAntiStructureVehicle', 'SovietAntiInfantryInfantry'
    NOSELL = 'CNV_NoSell_AlliedPowerPlant'                 # units/unsellable.py, the bench mission carries it


    def _start(t, m, orders, at=4.0):
        t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                  ('SET_MILLISECOND_TIMER', 'Test Go', at)]),
                      Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], orders)]


    def _plant(t, m, site, tag, tpl=PLANT):
        name = f'UNIT - Test Plant {tag}'
        t.objects.append(Obj(tpl, *m.site(site), side='p1', name=name, site=site))
        return name


    def _seen(t, counter, label, marks):
        """marks: (names, area) a digit, the first one the ones: that digit turns 1 the first frame any of the names
        stands in the area and never goes back (a 4 s sample misses a fast tank; only four counter lines fit)."""
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - seen {counter} zero', [], [('SET_COUNTER', counter, 0)]))
        for d, (names, area) in enumerate(marks):
            flag = f'Test Seen {counter} {d}'
            t.scripts += [Script(f'{flag} {k}', [('NAMED_INSIDE_AREA', n, area)], [('SET_FLAG', flag, 1)])
                          for k, n in enumerate(names)]
            t.scripts.append(Script(f'{flag} add', [('FLAG', flag, 1)], [('INCREMENT_COUNTER', 10 ** d, counter)]))


    def foot(m):
        t = Test()
        hit, shoot, go = ([f'UNIT - Test Ray {tag} {k}' for k in range(n)]
                          for tag, n in (('Hit', 3), ('Plant', 2), ('Go', 2)))
        for k, n in enumerate(hit + shoot + go):            # the river at y 2400 .. 2500 runs x ~2600 .. 2860
            t.objects.append(Obj(RAY, 2660.0 + 55.0 * (k % 4), 2400.0 + 80.0 * (k // 4), side='s1', name=n,
                                 site='st_foot', angle=1.5708))
        plant = 'UNIT - Test Plant Ledge'                   # an enemy on the ledge by the slip's top, by the powerhouse
        t.objects.append(Obj(PLANT, 2715.0, 2850.0, side='p1', name=plant, site='st_foot'))
        t.waypoints['Test Pool'] = (2890.0, 2935.0)
        t.areas['Test Ledge'] = square(2650.0, 2910.0, 125.0)
        t.areas['Test Pool'] = square(2890.0, 2935.0, 100.0)
        counted('Test Foot hp', '厂房血', t, health=m.map.POWERHOUSE)
        counted('Test Plant hp', '电厂血', t, health=plant)
        _seen(t, 'Test Move', '移组 池/台', [(go, 'Test Pool'), (go, 'Test Ledge')])     # not 'Test Go': the timer's
        _seen(t, 'Test Hit', '打组 厂池/厂台/电池/电台', [(hit, 'Test Pool'), (hit, 'Test Ledge'),
                                                        (shoot, 'Test Pool'), (shoot, 'Test Ledge')])
        _start(t, m, [('NAMED_ATTACK_NAMED', n, m.map.POWERHOUSE) for n in hit] +
               [('NAMED_ATTACK_NAMED', n, plant) for n in shoot] + [('MOVE_NAMED_UNIT_TO', n, 'Test Pool') for n in go])
        # the powerhouse is a neutral prop again (r9; the low section is the plant): no one's target, as r7 read it
        t.expect += [('移组 池/台', 0, 'ever>=', 1), ('电厂血', 0, 'ever<=', 90), ('厂房血', 0, '==', 100)]
        t.bench = [('bench_watch', dict(seconds=90.0, every=5, sheet=False, lines=len(t.counters)))]
        return t


    def v4(m):
        t = Test()
        east, west = _plant(t, m, 'st_dam_e', 'East'), _plant(t, m, 'st_dam_w', 'West')
        ve, vw = 'UNIT - Test V4 East', 'UNIT - Test V4 West'
        t.objects += [Obj(V4, *m.site('overlook', 0.0, 50.0), side='s1', name=ve, site='overlook', angle=3.1416),
                      Obj(V4, *m.site('overlook', 0.0, -50.0), side='s1', name=vw, site='overlook', angle=3.1416)]
        t.areas['Test Overlook'] = square(*m.site('overlook'), 150.0)
        counted('Test East hp', '东段血', t, health=east)
        counted('Test West hp', '西段血', t, health=west)
        counted('Test V4e up', 'V4东在台上', t, named=ve, area='Test Overlook')
        counted('Test V4w up', 'V4西在台上', t, named=vw, area='Test Overlook')
        _start(t, m, [('NAMED_ATTACK_NAMED', ve, east), ('NAMED_ATTACK_NAMED', vw, west)])
        t.expect += [('东段血', 0, 'ever<=', 90), ('V4东在台上', 0, '==', 1), ('V4西在台上', 8, 'ever==', 0)]
        t.bench = [('bench_watch', dict(seconds=60.0, every=4, sheet=False, lines=len(t.counters)))]
        return t


    def camp(m):
        t = Test()
        west, east = _plant(t, m, 'st_dam_w', 'West'), _plant(t, m, 'st_dam_e', 'East')
        orders = []
        for tpl, tag, target, dy in ((HAMMER, 'Hammer', west, -150.0), (TESLA, 'Tesla', east, 150.0)):
            for k in range(3):
                n = f'UNIT - Test {tag} {k}'
                t.objects.append(Obj(tpl, *m.site('sov_camp', -450.0 + 70.0 * k, dy), side='s1', name=n, site='sov_camp'))
                orders.append(('NAMED_ATTACK_NAMED', n, target))
        t.areas['Test Bridge W'] = square(2480.0, 1700.0, 150.0)
        t.areas['Test Bridge'] = square(2885.0, 1700.0, 200.0)
        t.areas['Test East'] = square(3700.0, 2550.0, 250.0)
        for tag, word in (('锤', 'Hammer'), ('磁', 'Tesla')):
            names = [f'UNIT - Test {word} {k}' for k in range(3)]
            _seen(t, f'Test {word}', f'{tag} 桥西/桥/东', [(names, a) for a in ('Test Bridge W', 'Test Bridge', 'Test East')])
        t.areas['Test Camp'] = square(*m.site('sov_camp'), 400.0)
        counted('Test Hammer home', '锤0在营', t, named='UNIT - Test Hammer 0', area='Test Camp')
        counted('Test West hp', '西段血', t, health=west)
        _start(t, m, orders)                               # monotone: <= 11 all run = never east, <= 100 = never on the bridge
        t.expect += [('锤 桥西/桥/东', 0, 'ever==', 11), ('锤 桥西/桥/东', 0, '<=', 11),
                     ('磁 桥西/桥/东', 0, 'ever==', 100), ('磁 桥西/桥/东', 0, '<=', 100)]
        t.bench = [('bench_watch', dict(seconds=110.0, every=4, sheet=False, lines=len(t.counters)))]
        return t


    def crest(m):
        t = Test()
        t.waypoints['Test Crest End'] = (2420.0, 3085.0)
        t.waypoints['Test Flat End'] = (3180.0, 2450.0)
        orders = []
        for k in range(8):                                  # a 4 x 2 block behind the start of each lane
            dx, dy = 60.0 * (k // 2), 50.0 * (k % 2) - 25.0
            for lane, (x, y), goal, site in (('Crest', (3180.0, 3085.0), 'Test Crest End', 'st_dam_e'),
                                             ('Flat', (3940.0, 2450.0), 'Test Flat End', 'st_bend')):
                n = f'UNIT - Test {lane} {k}'
                t.objects.append(Obj(HAMMER, x + dx, y + dy, side='p1', name=n, site=site, angle=3.1416))
                orders.append(('MOVE_NAMED_UNIT_TO', n, goal))
        t.areas['Test Crest End'] = square(2420.0, 3085.0, 110.0)
        t.areas['Test Flat End'] = square(3180.0, 2450.0, 110.0)
        counted('Test Crest over', '坝上组到', t, template=HAMMER, area='Test Crest End')
        counted('Test Flat over', '平地组到', t, template=HAMMER, area='Test Flat End')
        _start(t, m, orders)
        t.expect += [('坝上组到', 0, 'ever>=', 8), ('平地组到', 0, 'ever>=', 8)]
        t.bench = [('bench_watch', dict(seconds=60.0, every=2, sheet=False, lines=len(t.counters)))]
        return t


    def athena(m):
        t = Test()
        dam = _plant(t, m, 'st_dam_w', 'Dam', DAM)
        x, y = m.site('st_dam_w')
        foe, gun = 'UNIT - Test Foe Plant', 'UNIT - Test Athena'
        t.objects += [Obj(PLANT, x, y + 50.0, side='s1', name=foe, site='st_dam_w'),
                      Obj(ATHENA, x - 350.0, y, side='p1', name=gun, site='st_dam_w')]
        counted('Test Dam hp', '坝血', t, health=dam)
        counted('Test Foe hp', '靶血', t, health=foe)
        _start(t, m, [('NAMED_ATTACK_NAMED', gun, foe)], at=6.0)
        t.expect += [('靶血', 0, 'ever<=', 50), ('坝血', 0, 'ever<=', 90)]
        t.bench = [('bench_watch', dict(seconds=50.0, every=5, sheet=False, lines=len(t.counters)))]
        return t


    def sell(m):
        t = Test()
        p1 = m.player('p1')
        kept, sold = _plant(t, m, 'st_dam_w', 'Kept', DAM), _plant(t, m, 'st_dam_e', 'Sold', DAM)
        t.counters.append(('Test Alive', '存活 留/卖'))      # a digit each, the kept one the ones
        t.scripts.append(Script('Test - alive zero', [], [('SET_COUNTER', 'Test Alive', 0)], once=False))
        t.scripts += [Script(f'Test - alive {k}', [('NAMED_NOT_DESTROYED', n)], [('INCREMENT_COUNTER', 10 ** k, 'Test Alive')],
                             once=False) for k, n in enumerate((kept, sold))]
        counted('Test Locked', '不能卖数', t, status=status('CANNOT_BE_SOLD'))
        t.counters.append(('Test Money', '资金'))
        t.scripts += [Script('Test - lock', [], [('UNIT_CHANGE_OBJECT_STATUS', kept, 'CANNOT_BE_SOLD', 1),
                                                 ('PLAYER_SET_MONEY', p1, 2000)]),
                      Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'Test Money')], once=False)]
        _start(t, m, [('SELL_OBJECT', kept), ('SELL_OBJECT', sold)])
        t.expect += [('存活 留/卖', 1, '==', 11, 3), ('不能卖数', 0, 'ever==', 1), ('存活 留/卖', 8, '==', 1),
                     ('资金', 8, '==', 2400)]
        t.bench = [('bench_watch', dict(seconds=16.0, every=2, sheet=False, lines=len(t.counters)))]
        return t


    def lock(m):
        """sell again, the kept one the plant's copy with KindOf +NOT_SELLABLE (units/unsellable.py), no status set."""
        t = Test()
        p1 = m.player('p1')
        kept, sold = _plant(t, m, 'st_dam_w', 'Kept', NOSELL), _plant(t, m, 'st_dam_e', 'Sold', DAM)
        t.counters += [('Test Alive', '存活 留/卖'), ('Test Money', '资金')]      # a digit each, the kept one the ones
        t.scripts += [Script('Test - alive zero', [], [('SET_COUNTER', 'Test Alive', 0)], once=False),
                      Script('Test - money set', [], [('PLAYER_SET_MONEY', p1, 2000)]),
                      Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'Test Money')], once=False)]
        t.scripts += [Script(f'Test - alive {k}', [('NAMED_NOT_DESTROYED', n)], [('INCREMENT_COUNTER', 10 ** k, 'Test Alive')],
                             once=False) for k, n in enumerate((kept, sold))]
        _start(t, m, [('SELL_OBJECT', kept), ('SELL_OBJECT', sold)])
        t.expect += [('存活 留/卖', 1, '==', 11, 3), ('存活 留/卖', 8, '==', 1), ('资金', 8, '==', 2400)]
        t.bench = [('bench_watch', dict(seconds=16.0, every=2, sheet=False, lines=len(t.counters)))]
        return t


    def _raid(t, m, groups, areas, seen):
        """groups: (template, tag, count, site, dx, dy, target) each one team ordered like a plan wave (TEAM_ATTACK_NAMED);
        seen: (label, tag, [area, ...]) a _seen line. via (an eighth item, a site): first moved there, the attack once
        one of them is inside it (as the plan's 先到)."""
        orders, names = [], {}
        for tpl, tag, n, site, dx, dy, target, *via in groups:
            names[tag] = [f'UNIT - Test {tag} {k}' for k in range(n)]
            t.objects += [Obj(tpl, *m.site(site, dx + 40.0 * (k % 4), dy + 40.0 * (k // 4)), side='s1', name=u, site=site)
                          for k, u in enumerate(names[tag])]
            if not via:
                orders += m.order('attack', names[tag], target, 's1')
                continue
            t.waypoints[f'Test Via {tag}'] = m.site(via[0])
            t.areas[f'Test Via {tag}'] = square(*m.site(via[0]), 150.0)
            orders += m.order('move', names[tag], f'Test Via {tag}', 's1')
            t.scripts += [Script(f'Test - via {tag} {k}', [('NAMED_INSIDE_AREA', u, f'Test Via {tag}')],
                                 m.order('attack', names[tag], target, 's1')) for k, u in enumerate(names[tag])]
        t.areas.update(areas)
        for label, tag, where in seen:
            _seen(t, f'Test {tag}', label, [(names[tag], a) for a in where])
        _start(t, m, orders)


    def roads(m):
        t = Test()
        w, e = _plant(t, m, 'st_dam_w', 'West', DAM), _plant(t, m, 'st_dam_e', 'East', DAM)
        counted('Test West hp', '西段血', t, health=w)
        counted('Test East hp', '东段血', t, health=e)
        _raid(t, m, [(CONSCRIPT, 'Conscript', 5, 'sov_camp', -450.0, -150.0, w), (HAMMER, 'Hammer', 3, 'sov_east', -120.0, 0.0, e)],
              {'Test Bridge': square(2885.0, 1700.0, 200.0), 'Test East': square(3700.0, 2550.0, 250.0),
               'Test Bend': square(*m.site('st_bend'), 250.0)},
              [('动 桥/东', 'Conscript', ['Test Bridge', 'Test East']), ('锤 长坡', 'Hammer', ['Test Bend'])])
        t.expect += [('西段血', 0, 'ever<=', 90), ('东段血', 0, 'ever<=', 90), ('动 桥/东', 0, 'ever==', 1),
                     ('动 桥/东', 0, '<=', 1), ('锤 长坡', 0, 'ever==', 1)]
        t.bench = [('bench_watch', dict(seconds=200.0, every=5, sheet=False, lines=len(t.counters)))]
        return t


    def last(m):
        t = Test()
        w, e = _plant(t, m, 'st_dam_w', 'West', DAM), _plant(t, m, 'st_dam_e', 'East', DAM)
        counted('Test West hp', '西段血', t, health=w)
        counted('Test East hp', '东段血', t, health=e)
        _raid(t, m, [(V4, 'V4', 2, 'sov_east', -120.0, 0.0, e), (RAY, 'Ray', 3, 'sov_lake', -60.0, 0.0, w)],
              {'Test Overlook': square(*m.site('overlook'), 150.0), 'Test Face': square(2660.0, 3260.0, 150.0),
               'Test Beach': square(*m.site('st_beach'), 250.0)},
              [('V4 台上', 'V4', ['Test Overlook']), ('魟 坝面/湖滩', 'Ray', ['Test Face', 'Test Beach'])])
        t.expect += [('东段血', 0, 'ever<=', 90), ('西段血', 0, 'ever<=', 90), ('魟 坝面/湖滩', 0, 'ever==', 1),
                     ('魟 坝面/湖滩', 0, '<=', 1)]
        t.bench = [('bench_watch', dict(seconds=150.0, every=5, sheet=False, lines=len(t.counters)))]
        return t


    def perch(m):
        """last's V4s as the plan's 先到 sends them: moved to the overlook first, the attack on crest east from there."""
        t = Test()
        e = _plant(t, m, 'st_dam_e', 'East', DAM)
        counted('Test East hp', '东段血', t, health=e)
        counted('Test East up', '东段在', t, owner=e)   # bench r9: the plant went s51-s56 with 东段血 still 100 (frozen)
        _raid(t, m, [(V4, 'V4', 2, 'sov_east', -120.0, 0.0, e, 'overlook')], {'Test Overlook': square(*m.site('overlook'), 150.0)},
              [('V4 台上', 'V4', ['Test Overlook'])])
        t.expect += [('V4 台上', 0, 'ever==', 1), ('东段在', 0, 'ever==', 0)]
        t.bench = [('bench_watch', dict(seconds=120.0, every=5, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {'canyon': {'foot': foot, 'v4': v4, 'camp': camp, 'crest': crest, 'ath': athena, 'sell': sell,
                         'roads': roads, 'last': last, 'lock': lock, 'perch': perch}}
    return dict(CHECKS=CHECKS)


def engine_block():
    """Engine unit tests: does a unit go round a way that structures or enemies block (docs/engine/pathing.md 6, 7;
    engine line round 10, ADR 0017). Map: maps/probe_block.py, every way round about 950 (probe_paths' 1 100 goes
    round). Whole-team orders (Mission.order), as the missions give them.

    wall: an IFV each in 'bits' (the wall on field 0, the control), 'built' (a row of the player's own structures across
      the way, there from the start) and 'late' (the same row made LATE s after the order). Counters: 1 by the far gap
      (it went round), 10 at the goal.
    enemy: the wall has a straight gap plugged by two enemy MCVs (unarmed), the far gap open; a tank ordered by move in
      'enemy move', by attack-move in 'enemy attack'. Counters as wall's, and the attack lane's front MCV's health.

    Read (测, 2026-11-04, docs/engine/pathing.md 6, 7): wall -- bits and built 11 (round, s7), late 10 at s4 (through
    the row, made by s1: `made` reads 8 and 8); enemy -- move 10 at s25 (through the plug; `plugs` again: not by s41),
    attack never there, the MCV 98 -> 24 in 90 s.
    foot (测, 2026-11-08): the row made at the start, the IFV and a peacekeeper ordered at s4 -- both 11 (round): the IFV
    by the gap s7, at the goal s13; the soldier s10 / s22. A made structure is in a new order's way, infantry's too.
    """
    from maps import probe_block
    from model import status
    from parts import Script, Test, counted
    from checks.engine_block import LABEL, WALL, _go, _key, _scored, mission

    LATE = 1.0
    AFTER = 4.0                        # foot: the order, 3 s after the late row is made
    GATE = 'GV_Ring02'                 # s02's cage doors: a retail civilian prop with no die module (a dead one stays)
    GATE_XS = (160.0, 185.0, 210.0, 235.0)     # gate: its bars across the straight way, x - x0 (each 26.7 long)
    OPEN = 2.0                         # gate: when the bars are killed / let through, 2 s before the order (s02's idle)


    def wall(m):
        t = Test()
        order = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'Test Block Late', LATE)]
        for lane in ('bits', 'built', 'late'):
            order += _go(m, t, lane)
            _scored(m, t, lane)
        make = []
        for k, xy in enumerate(probe_block.ROW['late']):
            wp = f'Test Block Late {k}'
            t.waypoints[wp] = xy
            make.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', f'UNIT - CNV Block Late Wall {k}', WALL, m.team('p1'), wp))
        t.scripts.insert(0, Script('Test - go', [], order))
        t.scripts.append(Script('Test - late wall', [('TIMER_EXPIRED', 'Test Block Late')], make))
        t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=3))]
        t.expect = [('位图墙', 0, 'ever==', 11, 60)]          # the control goes round: the rest are read, not judged
        return t


    def made(m):
        """wall's late lane again, with how many of its structures stand (does the script make them; capped at 8), and
        the built row's count for the same reading."""
        t = wall(m)
        t.counters = [c for c in t.counters if c[1] == LABEL['late']]
        t.scripts = [s for s in t.scripts if 'Bits' not in s.name and 'Built' not in s.name]
        for lane in ('late', 'built'):
            xs = [x for x, _ in probe_block.ROW[lane]]
            y = probe_block.ROW[lane][0][1]
            area = f'Test Block {_key(lane)} Row'
            t.areas[area] = [(xs[0] - 20, y - 40), (xs[-1] + 20, y - 40), (xs[-1] + 20, y + 40), (xs[0] - 20, y + 40)]
            counted(f'Test Block {_key(lane)} Walls', f'{LABEL[lane]}座数', t, template=WALL, area=area)
        t.expect = []
        return t


    def foot(m):
        """The late row made first (LATE), then -- AFTER -- the late lane's IFV and a soldier beside it ordered to the
        goal: is a structure made in the run in a new order's way, for a vehicle and for infantry (docs/engine/pathing.md
        6). Counters as wall's: 11 went round by the gap, 10 straight through."""
        t = Test()
        make = []
        for k, xy in enumerate(probe_block.ROW['late']):
            wp = f'Test Block Late {k}'
            t.waypoints[wp] = xy
            make.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', f'UNIT - CNV Block Late Wall {k}', WALL, m.team('p1'), wp))
        t.scripts.append(Script('Test - late wall', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))] + make))
        t.scripts.append(Script('Test - wait', [], [('SET_MILLISECOND_TIMER', 'Test Block After', AFTER)]))
        wp = 'Test Block Late Goal'
        t.waypoints[wp] = m.site('late goal')
        order = m.order('move', [m.role('late unit').name], wp, crew='BlockLate') + \
            m.order('move', [m.role('late foot').name], wp, crew='BlockFoot')
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Block After')], order))
        _scored(m, t, 'late')
        counter = 'CNV_Block_Foot'
        t.counters.append((counter, '后建墙步兵'))
        for k, (site, half, n) in enumerate((('late gap', 140.0, 1), ('late goal', 100.0, 10))):
            t.scripts.append(Script(f'Test - {counter} {k}', [('NAMED_INSIDE_AREA', m.role('late foot').name,
                                                               f'Test Block {_key(site)}')],
                                    [('INCREMENT_COUNTER', n, counter)], once=True))
        t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=2))]
        t.expect = []
        return t


    def gate(m, kill=False, nocoll=False, rows=()):
        """s02's cage doors (UNIT_CHANGE_OBJECT_STATUS NO_COLLISIONS on a door NAMED_KILL has just killed): foot's late
        row with GATE bars in place of its three structures across the straight way; at OPEN the bars killed (kill) and
        given NO_COLLISIONS (nocoll), then foot's order. Counters as foot's (11 round, 10 through) and the objects
        carrying NO_COLLISIONS (无碰撞). rows: map-placed bars instead (gr one row, a 5.3 line; gd three, 15+ deep).
        Read (2026-11-22): benches/movement/pathing/readings.toml#engine_block; the player's ownership-of-type counter reads 0 for these bars,
        standing or not, so it is not one."""
        t = foot(m)
        m.spawns.add(GATE)                             # made by script, nobody casts it
        make = next(s for s in t.scripts if s.name == 'Test - late wall')
        x0, y = probe_block.BOXES['late'][0][0], probe_block.ROW['late'][0][1]
        make.do = [a for a in make.do if not (a[0].startswith('CREATE') and abs(t.waypoints[a[4]][0] - x0 - 200) < 50)]
        if rows:        # map-placed (as s02's), 19 bars 5 apart over the way a row: gd's 3 rows solid whichever way they lie
            for dx in range(150, 241, 5):
                for dy in rows:
                    m.put(GATE, 'late wall', dx - 15.0, dy, angle=0.0)
            return t
        bars = [f'UNIT - CNV Block Gate {k}' for k in range(len(GATE_XS))]
        for name, dx in zip(bars, GATE_XS):
            t.waypoints[name[11:]] = (x0 + dx, y)
            make.do.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', name, GATE, m.team('p1'), name[11:]))
        make.do.append(('SET_MILLISECOND_TIMER', 'Test Block Gate', OPEN))
        opened = [('NAMED_KILL', n) for n in bars if kill] + \
            [('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_COLLISIONS', 1) for n in bars if nocoll]
        t.scripts.append(Script('Test - gate', [('TIMER_EXPIRED', 'Test Block Gate')], opened))
        counted('Test Block NoColl', '无碰撞', t, status=status('NO_COLLISIONS'))
        return t


    def enemy(m):
        t = Test()
        order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for lane, kind in (('enemy move', 'move'), ('enemy attack', 'attack_move')):
            order += _go(m, t, lane, kind)
            _scored(m, t, lane)
        counted('Test Block Plug Hp', '敌车血量', t, health=m.role('enemy attack plug 1').name)
        t.scripts.insert(0, Script('Test - go', [], order))
        t.bench = [('bench_watch', dict(seconds=90, every=3, sheet=False, lines=3))]
        t.expect = []
        return t


    def plugs(m):
        """How the move lane's tank got through the plug: its counter and both its MCVs' health."""
        t = Test()
        order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))] + _go(m, t, 'enemy move')
        _scored(m, t, 'enemy move')
        for k in (1, 2):
            counted(f'Test Block Move Plug {k} Hp', f'敌车{k}血量', t, health=m.role(f'enemy move plug {k}').name)
        t.scripts.insert(0, Script('Test - go', [], order))
        t.bench = [('bench_watch', dict(seconds=40, every=2, sheet=False, lines=3))]
        t.expect = []
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_block': mission}
    CHECKS = {'engine_block': {'wall': wall, 'made': made, 'foot': foot, 'enemy': enemy, 'plugs': plugs,
                               'gk': lambda m: gate(m, kill=True), 'gn': lambda m: gate(m, nocoll=True),
                               'gd': lambda m: gate(m, rows=(-5.0, 0.0, 5.0)), 'gr': lambda m: gate(m, rows=(0.0,))}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_column():
    """Engine unit tests, R3 step X (ADR 0032 5: the pathing details re-derived on the bench): where a group of infantry
    stops when it is sent to one point as one team -- the simulator's Sim.column_ends (the ends of an infantry group's
    move: in which rows and files the men stand round the point). Every man is a copy of the Peacekeeper with ra3ext's
    read-only CNVProbe (a `probe` line per frame it moved: its last line is where it stopped), on the blocked-way probe
    map's open ground (maps/probe_block.py).

    What decides the rule (each lane one team, one MOVE_TEAM_TO, the men standing in a block facing the point):
      - how many files across and rows back, against the number of men (3, 6, 10, 16);
      - the spacing across and back; where the front row stands against the point (on it, short of it, centred on it);
      - whether the block is turned with the way in (west / north / south-west) or kept on the world's axes;
      - whether a short move (the front man 70 from the point) makes a block at all;
      - the snap to the 20-unit grid (the north lane's point is off it).

      engine_column lanes   w6 six from the west (2 across, 3 deep), the point (3000, 2000)
                            n6 six from the north, the point (3013, 3007): off the grid
                            w3 three from the west (1 across), the point (3000, 4500)
                            near six from the west, the front man 70 short of the point (3000, 1600)
                            d6 six from the south-west (the way in at 45 degrees), the point (4300, 2000)
      engine_crowd big      w16 sixteen from the west (4 across, 4 deep), the point (3000, 2400)
                            n10 ten from the north (2 across, 5 deep), the point (3600, 3000)
      engine_colgate two    w2 two from the west, one behind the other, the point (3000, 2000)
                            w2s two from the west side by side, the point (3000, 2400)
                            close six from the west, the front man 20 short of the point (3000, 1600)
                            scat six from the west standing anyhow (SCATTER: no two level or abreast), the point (3000, 4500)

    No expectations: the readings are the probe lines (work/re/scripts/x_column.py reads them against the simulator's
    stops).
    """
    import math
    import os

    import labpaths
    from maps import probe_block
    from parts import Mission, Script, Test, Unit

    MAN = 'AlliedAntiInfantryInfantry'
    PROBE = 'CNV_ColMan'
    EVERY, LINES = 150, 6000
    SPACE = 30.0                     # the start block's spacing, across and back
    SCATTER = ((0, -8), (13, 41), (37, -47), (52, 17), (71, -21), (96, 55))   # (back, left): no two alike either way
    # build: (mission name, {lane: (the point, the front man's start, men, across)}); the block stands behind the front
    # man away from the point, `across` men a row, rows SPACE back
    BUILDS = {
        'engine_column': ('CampCols', {
            'w6': ((3000.0, 2000.0), (2500.0, 2000.0), 6, 2),
            'n6': ((3013.0, 3007.0), (3013.0, 3507.0), 6, 2),
            'w3': ((3000.0, 4500.0), (2500.0, 4500.0), 3, 1),
            'near': ((3000.0, 1600.0), (2930.0, 1600.0), 6, 2),
            'd6': ((4300.0, 2000.0), (3946.4, 1646.4), 6, 2),
        }),
        'engine_crowd': ('CampCrowd', {
            'w16': ((3000.0, 2400.0), (2450.0, 2400.0), 16, 4),
            'n10': ((3600.0, 3000.0), (3600.0, 3500.0), 10, 2),
        }),
        'engine_colgate': ('CampColGate', {
            'w2': ((3000.0, 2000.0), (2500.0, 2000.0), 2, 1),
            'w2s': ((3000.0, 2400.0), (2500.0, 2400.0), 2, 2),
            'close': ((3000.0, 1600.0), (2980.0, 1600.0), 6, 2),
            'scat': ((3000.0, 4500.0), (2500.0, 4500.0), 6, SCATTER),
        }),
    }
    RUN = COLUMN_RUN


    def watch(build):
        """Wall seconds to watch: ~20-26 probes slow the game to ~3-4 frames a second (bench 11-17 engine_drop)."""
        return RUN * 15.0 / 3.0


    def starts(build, lane):
        """Each man's start in `lane`: rows from the front, across left to right as seen walking in."""
        (px, py), (fx, fy), count, across = BUILDS[build][1][lane]
        ax, ay = px - fx, py - fy
        n = math.hypot(ax, ay)
        ux, uy = ax / n, ay / n                    # the way in; left = (-uy, ux)
        if isinstance(across, tuple):
            spots = across
        else:
            spots = [(SPACE * (k // across), (k % across - (across - 1) / 2) * SPACE) for k in range(count)]
        return [(fx - ux * back - uy * side, fy - uy * back + ux * side) for back, side in spots]


    def probe_copy():
        with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', MAN + '.xml'), encoding='utf-8') as f:
            x = f.read()
        assert x.count(f'id="{MAN}"') == 1 and x.count('<Behaviors>') == 1
        x = x.replace(f'id="{MAN}"', f'id="{PROBE}"', 1).replace(f'EditorName="{MAN}"', f'EditorName="{PROBE}"')
        x = x.replace('<Behaviors>', (f'<Behaviors>\n'
            f'\t\t\t<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>'), 1)
        return Unit(PROBE, x, names=dict(unit=PROBE), what=f'原版 {MAN} 的复制（探针）：多一个 ra3ext 的 CNVProbe，逐帧记位置',
                    params=dict(of=MAN, every=EVERY, lines=LINES))


    key = column_key


    def _mission(build):
        name, lanes = BUILDS[build]
        m = Mission(name=name, map=probe_block, units=[probe_copy()], facts={})
        m.ext = True
        sx, sy = m.site('island')
        for lane, ((px, py), _, _, _) in lanes.items():
            for k, (x, y) in enumerate(starts(build, lane)):
                m.put(PROBE, 'island', x - sx, y - sy, role=f'{lane} {k + 1}', name=f'UNIT - CNV Col {key(lane, k)}',
                      angle=math.atan2(py - y, px - x))
        return m


    def _check(build):
        def check(m):
            _, lanes = BUILDS[build]
            t = Test()
            go = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
            for lane, (point, _, count, _) in lanes.items():
                wp = f'Test Col {lane.title()} Point'
                t.waypoints[wp] = point
                go += m.order('move', [m.role(f'{lane} {k + 1}').name for k in range(count)], wp,
                              crew=f'Col{lane.title()}')
            t.scripts.append(Script('Test - go', [], go))
            t.bench = [('bench_watch', dict(seconds=watch(build), every=20, sheet=False, lines=2))]
            t.expect = []
            return t
        return check


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {b: (lambda b=b: _mission(b)) for b in BUILDS}
    CHECKS = {'engine_column': {'lanes': _check('engine_column')}, 'engine_crowd': {'big': _check('engine_crowd')},
              'engine_colgate': {'two': _check('engine_colgate')}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_dam():
    """The dolphin's jump told apart from swimming (round 252), and where a bear stands in the opening 0.1 s -- one run.
    Mission on maps/probe_dam.py: probe_air with a dry dam across its sea trench (y 3220..3280), so the trench is a south
    and a north pool. Everyone holds fire (NO_ATTACK at 0.1 s). What the data predicts in brackets (15 logic frames a
    second).
      DJ  AlliedAntiNavalScout (dolphin) in the south pool, NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT
          Command_ActivateJumpSpecialPower 250 north at PRESS (3 s), into the north pool over the dam (engine_acts_wet's
          DJ, which a swimmer matched: round 249). WeaponFireSpecialAbilityUpdate, UnpackTime 0, StartAbilityRange 300,
          weapon AlliedAntiNavalScoutJumpWeapon ProjectileSelf at 160 a second (Sim.leap_press). [DJ in the north pool
          ~1.6 s after the press (24 frames)]
      DQ  another dolphin beside it told to MOVE the same 250 north: it cannot swim there. [stays in the south pool]
      BR  SovietScoutInfantry (bear) and CS, an enemy conscript (s4) 60 north of it on the flat at 'air B' -- engine_acts_mix
          RN / C2's pair, no button pressed: does the bear walk up in the frame before NO_ATTACK holds it (round 251: the
          simulator's idle chase walks it to the conscript's feet by frame 15, which put the fitted NONE_TARGET_LAG)?
          [simulator: out of its start square from frame 1, at y >= 1445 by frame 15]
    Counters:
      跳 = DJ in its jump square + 10 x DJ in the south pool + 100 x DQ in its jump square + 1000 x DQ in the south pool
      帧 = frames DJ in its jump square (only added to: the reading minus this is the frame it came in)
      熊 = BR in its start square (half 8) + 10 x BR 20..45 north of it + 100 x BR 45..90 north of it (x within 30)
      走 = frames BR out of its start square (only added to)
      BENCH 11-15 (round 252, run_queue; CampDamAll_mcp_1115_204351; tests/test_simbench.py test_dam_all_as_the_bench,
        test_dam_bear_stands_in_the_opening): readings 1-4 1010 0 1 0 | 5-6 1000 0 1 0 | 7 1001 8 1 0 | 8 1001 17 |
        9 1001 25 | 10 1001 34 | 11 1001 44 (熊 1, 走 0 throughout).
        DJ jumped over the dam (two readings in the air: out of the south pool, not yet in its square), DQ stayed in the
        south pool. 帧 grew 8-10 a reading, not 15 (not explained), so the landing frame is not compared. The bear never
        moved: no idle chase in the opening frame (the simulator's walks it up: strict xfail).
    """
    from maps import probe_dam
    from parts import Mission, Test, square, status
    import checks.engine_scripts8 as s8

    MAN = 'SovietAntiInfantryInfantry'
    BEAR = 'SovietScoutInfantry'
    DOLPHIN = 'AlliedAntiNavalScout'
    JUMP = 'Command_ActivateJumpSpecialPower'
    LAND, SEA = 'air B', 'air sea S'
    # row -> (template, x, y, side, site)
    ROWS = {'DJ': (DOLPHIN, 2350.0, 3120.0, 'p1', SEA), 'DQ': (DOLPHIN, 2250.0, 3120.0, 'p1', SEA),
            'BR': (BEAR, 4000.0, 1400.0, 'p1', LAND), 'CS': (MAN, 4000.0, 1460.0, 's4', LAND)}
    JUMPS = {'DJ': 250.0, 'DQ': 250.0}                 # north
    PRESS, RUN = 3.0, 10.0
    SQUARE = 30.0                                      # a jump square's half side


    def _n(part):
        return f'UNIT - CNV Dam {part}'


    def _rect(x0, x1, y0, y1):
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


    def mission():
        m = Mission(name='CampDam', map=probe_dam, units=[], facts={})
        m.spawns |= {r[0] for r in ROWS.values()}
        for row, (tmpl, x, y, side, site) in ROWS.items():
            o = probe_dam.SITES[site]
            m.put(tmpl, site, x - o.x, y - o.y, side=side, angle=0.0, name=_n(row), role=row.lower())
            if row in JUMPS:
                m.waypoint(f'jump {row}', f'CNV Dam Jump {row}', site, x - o.x, y + JUMPS[row] - o.y)
        return m


    def all_(m):
        t = Test()
        s8.at(t, 'hold', 0.1, [('UNIT_CHANGE_OBJECT_STATUS', _n(r), status('NO_ATTACK'), 1) for r in ROWS]
              + [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
        s8.at(t, 'press', PRESS, [
            ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', _n('DJ'), JUMP, m.mark('jump DJ')),
            ('MOVE_NAMED_UNIT_TO', _n('DQ'), m.mark('jump DQ'))])
        # the by-name areas first (know-how: an object is counted in its first few areas only)
        for row in JUMPS:
            t.areas[f'Test Dam Jump {row}'] = square(*m.point(f'jump {row}'), SQUARE)
        t.areas['Test Dam Pool S'] = _rect(*probe_dam.POOL_S)
        bx, by = ROWS['BR'][1], ROWS['BR'][2]
        t.areas['Test Dam Bear Start'] = square(bx, by, 8.0)
        t.areas['Test Dam Bear Near'] = _rect(bx - 30.0, bx + 30.0, by + 20.0, by + 45.0)
        t.areas['Test Dam Bear Far'] = _rect(bx - 30.0, bx + 30.0, by + 45.0, by + 90.0)
        inside = lambda row, a: ('NAMED_INSIDE_AREA', _n(row), f'Test Dam {a}')  # noqa: E731
        s8.total(t, 'CNV_Dam_Jump', '跳', [(1, inside('DJ', 'Jump DJ')), (10, inside('DJ', 'Pool S')),
                                           (100, inside('DQ', 'Jump DQ')), (1000, inside('DQ', 'Pool S'))])
        s8.frames(t, 'CNV_Dam_Frames', '帧', [inside('DJ', 'Jump DJ')])
        s8.total(t, 'CNV_Dam_Bear', '熊', [(1, inside('BR', 'Bear Start')), (10, inside('BR', 'Bear Near')),
                                           (100, inside('BR', 'Bear Far'))])
        s8.frames(t, 'CNV_Dam_Walk', '走', [('NAMED_OUTSIDE_AREA', _n('BR'), 'Test Dam Bear Start')])
        s8.watch(t, RUN)
        return t


    MISSION = {'engine_dam': mission}
    CHECKS = {'engine_dam': {'all': all_}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_drop():
    """Engine unit tests, R3 step X (ADR 0032 5: the pathing details re-derived on the bench): where a unit stops when the
    point it is sent to is already someone's -- the simulator's Sim.free_spot (a move's goal kept off the spots other
    units hold, Sim.claims). Every unit is a copy with ra3ext's read-only CNVProbe (a `probe` line per frame it moved: its
    last line is where it stopped), on the blocked-way probe map's open ground (maps/probe_block.py).

    Each lane is a column of units of one kind behind a start, sent one at a time (STAGGER apart, each on its own; every
    one before it has arrived) to the lane's point. Read: each unit's stop -- the first on the point? the next ones how far
    off (a radius sum? cells?), in which direction (the world's axes, or turned with the way it came), in what order round
    the point; tanks against men (the distance with the size).

      engine_drop lanes      six of each:
                west   Guardian tanks from the west (column along y 2000, the point (3000, 2000))
                north  Guardian tanks from the north (column along x 3013, the point (3013, 3007): off the 20-unit grid)
                man    Peacekeepers from the west (column along y 4500, the point (3000, 4500))
      engine_dropring tens   ten of each, the order further round:
                tank   Guardian tanks from the west (the point (3000, 1600))
                man    Peacekeepers from the south (the point (3600, 2800))

    Each unit is put down facing the point. No expectations: the readings are the probe lines (work/re/scripts/x_drop.py
    reads them against the simulator's stops).
    """
    import math
    import os

    import labpaths
    from maps import probe_block
    from parts import Mission, Script, Test, Unit

    TANK, MAN = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
    PROBE = {TANK: 'CNV_DropTank', MAN: 'CNV_DropMan'}
    EVERY, LINES = 150, 6000
    STAGGER = 15.0
    # build: (mission name, units a lane, {lane: (template, the point, the first start, the column's step back)})
    BUILDS = {
        'engine_drop': ('CampDrop', 6, {
            'west': (TANK, (3000.0, 2000.0), (2500.0, 2000.0), (-100.0, 0.0)),
            'north': (TANK, (3013.0, 3007.0), (3013.0, 3507.0), (0.0, 100.0)),
            'man': (MAN, (3000.0, 4500.0), (2500.0, 4500.0), (-60.0, 0.0)),
        }),
        'engine_dropring': ('CampRing', 10, {
            'tank': (TANK, (3000.0, 1600.0), (2500.0, 1600.0), (-60.0, 0.0)),
            'man': (MAN, (3600.0, 2800.0), (3600.0, 2300.0), (0.0, -30.0)),
        }),
    }


    def run(build):
        """Game seconds the check needs: the last order, then the last (farthest) unit's walk (a man ~50 a second)."""
        _, count, lanes = BUILDS[build]
        return 1.0 + STAGGER * (count - 1) + 25.0


    def watch(build):
        """Wall seconds to watch: ~20 probes slow the game to ~4 frames a second, 15 a game second (bench 11-17: a first
        run watched game seconds on the wall clock and stopped at frame 450, before the third unit's order)."""
        return run(build) * 15.0 / 3.8


    def starts(build, lane):
        """Each unit's start in `lane`, the first (sent first) nearest the point."""
        _, count, lanes = BUILDS[build]
        _, _, (x, y), (dx, dy) = lanes[lane]
        return [(x + dx * k, y + dy * k) for k in range(count)]


    def probe_copy(template):
        pid = PROBE[template]
        with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', template + '.xml'), encoding='utf-8') as f:
            x = f.read()
        assert x.count(f'id="{template}"') == 1 and x.count('<Behaviors>') == 1
        x = x.replace(f'id="{template}"', f'id="{pid}"', 1).replace(f'EditorName="{template}"', f'EditorName="{pid}"')
        x = x.replace('<Behaviors>', (f'<Behaviors>\n'
            f'\t\t\t<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>'), 1)
        return Unit(pid, x, names=dict(unit=pid), what=f'原版 {template} 的复制（探针）：多一个 ra3ext 的 CNVProbe，逐帧记位置',
                    params=dict(of=template, every=EVERY, lines=LINES))


    def _role(lane, k):
        return f'{lane} {k + 1}'


    key = drop_key


    def _mission(build):
        name, _, lanes = BUILDS[build]
        m = Mission(name=name, map=probe_block, units=[probe_copy(TANK), probe_copy(MAN)], facts={})
        m.ext = True
        sx, sy = m.site('island')
        for lane, (tpl, (px, py), _, _) in lanes.items():
            for k, (x, y) in enumerate(starts(build, lane)):
                m.put(PROBE[tpl], 'island', x - sx, y - sy, role=_role(lane, k), name=f'UNIT - CNV Drop {key(lane, k)}',
                      angle=math.atan2(py - y, px - x))
        return m


    def _check(build):
        def check(m):
            _, count, lanes = BUILDS[build]
            t = Test()
            first = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
            for lane, (_, point, _, _) in lanes.items():
                wp = f'Test Drop {lane.title()} Point'
                t.waypoints[wp] = point
                for k in range(count):
                    go = m.order('move', [m.role(_role(lane, k)).name], wp, crew=f'Drop{key(lane, k)}')
                    timer = f'Test Drop {key(lane, k)}'
                    first.append(('SET_MILLISECOND_TIMER', timer, 1.0 + STAGGER * k))
                    t.scripts.append(Script(f'Test - go {_role(lane, k)}', [('TIMER_EXPIRED', timer)], go))
            t.scripts.insert(0, Script('Test - go', [], first))
            t.bench = [('bench_watch', dict(seconds=watch(build), every=20, sheet=False, lines=2))]
            t.expect = []
            return t
        return check


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {b: (lambda b=b: _mission(b)) for b in BUILDS}
    CHECKS = {'engine_drop': {'lanes': _check('engine_drop')}, 'engine_dropring': {'tens': _check('engine_dropring')}}
    return dict(MISSION=MISSION, CHECKS=CHECKS, run=run)


def engine_dynamics():
    """Engine unit test: does a vehicle's DynamicsUpdate change what it does on the ground (engine line E). Retail data
    (SDK SageXML): BaseVehicle carries `DynamicsUpdate Motion="TRACKED" Collision="OMNICOLLIDING" ContactTag="VEHICLE"`
    (no Volume); every tank, ship and aircraft inherits it (62 of the 113 retail campaign templates with the module; the
    other 51 -- the SS_Fling* props and doors -- are Uprising-only, absent from RA3's data). Question: does a Hammer
    without the module crush, go round and arrive as the retail one does.

    A child cannot take an inherited module out, so the copies inherit a copy of BaseVehicle written into their own file
    (CNVBaseVehicleNoDyn: BaseVehicle without its DynamicsUpdate; CNVBaseVehicleDyn: the same copy with it, the control),
    the Hammer's own XML on top under a new id, its NORMAL speed 60 as the campaign override gives the retail one.

    On the festival map, west field, three lanes along +x, 300 apart (engine_crush's layout); every unit on HOLD_FIRE (a
    death is a crush). Per lane a tank 200 west of an enemy target, ordered at 'Test Go' (1 s in) to a point 200 east of it:
      lane 1 retail Hammer   lane 2 CNVHammerNoDyn   lane 3 CNVHammerDyn
      a  each -> an enemy conscript (crushable 10: crushed)      b  each -> an enemy Guardian tank (20: the Hammer goes round)
    Counters (four lines), counted from 'Test Go' on:
      帧数  frames since Go
      行k   1 x frames the target is not destroyed + 1000 x frames it is dying + 1000000 x frames the tank is at its goal
            (a square of half-side 40)

    PREDICTED (engine_crush, bench 11-06: conscript crushed at frame 43, dying 127 frames; the Guardian untouched, the Hammer
    round it and at its goal from 96): the three lanes alike in each variant.
    Bench 2026-11-10 (both PASS; the three rows identical every second): a (CampDynAA_mcp_1110_173046) 607127043 at frame
    698 -- each conscript crushed at frame 43, dying 127 frames, each tank at its goal from frame 92; b
    (CampDynBB_mcp_1110_173513) 613000709 at frame 709 -- each Guardian alive all along, never dying, each Hammer round it
    and at its goal from 97. Without DynamicsUpdate a vehicle crushes, goes round and arrives as with it.
    Simulated: tests/test_simbench_c.py::test_dynamics_update_a_hammer_without_it_crushes_and_goes_round_as_the_retail_one.

      c  an Uprising fling prop (SS_FlingContainer01) between a Hammer and an enemy conscript: does the flung prop hurt.
         11-10: it does not build -- the map compile stops (Critical: GameObject:SS_FlingContainer01 inherits the
         non-existing BaseClientFlingableProp). The 44 SS_Fling* campaign templates are Uprising's alone: an RA3 mod
         cannot place them (inventory: `...:起义专有`, 不涉及; retailmodules.orphaned). Kept as that evidence; never PASSes.
    """
    import os
    import re

    import labpaths
    from maps import festival
    from parts import Mission, Script, Test, Unit, square

    SAGE = os.path.join(labpaths.SDK3, 'SageXML')
    HAMMER, CONSCRIPT, GUARDIAN = 'SovietAntiVehicleVehicleTech1', 'SovietAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech1'
    NODYN, DYN = 'CNVHammerNoDyn', 'CNVHammerDyn'
    TANKS = {1: (HAMMER, -300.0), 2: (NODYN, 0.0), 3: (DYN, 300.0)}
    TARGETS = {'a': CONSCRIPT, 'b': GUARDIAN}
    RUN, HOLD_FIRE = 45.0, 3


    def _sub1(x, old, new):
        assert x.count(old) == 1, (old[:60], x.count(old))
        return x.replace(old, new, 1)


    def hammer_copy(dyn):
        """Retail's Hammer under a new id, inheriting a copy of BaseVehicle (written into the same file) with or without
        its DynamicsUpdate; NORMAL speed 60 (CampaignOverrides gives the retail Hammer 60, a new id gets none)."""
        name, base = (DYN, 'CNVBaseVehicleDyn') if dyn else (NODYN, 'CNVBaseVehicleNoDyn')
        v = open(os.path.join(SAGE, 'BaseObjects', 'BaseVehicle.xml'), encoding='utf-8').read()
        b = re.search(r'\t<GameObject\s+id="BaseVehicle".*?</GameObject>\n', v, re.S).group(0)
        b = _sub1(b, 'id="BaseVehicle"', f'id="{base}"')
        if not dyn:
            b, k = re.subn(r'\s*<DynamicsUpdate\s+id="ModuleTag_DefaultDynamicsUpdate".*?</DynamicsUpdate>', '', b, flags=re.S)
            assert k == 1, k
        x = open(os.path.join(SAGE, 'Soviet', 'Units', HAMMER + '.xml'), encoding='utf-8').read()
        x = _sub1(x, f'id="{HAMMER}"', f'id="{name}"')
        x = _sub1(x, f'EditorName="{HAMMER}"', f'EditorName="{name}"')
        x = _sub1(x, 'inheritFrom="BaseVehicle"', f'inheritFrom="{base}"')
        x = _sub1(x, 'Condition="NORMAL"\n\t\t\tSpeed="75.0"', 'Condition="NORMAL"\n\t\t\tSpeed="60.0"')
        x = _sub1(x, '\t<GameObject', b + '\t<GameObject')
        # the base copy inherits BaseObject: its file must be in our includes (BaseVehicle.xml's own include is not ours)
        x = _sub1(x, '<Includes>', '<Includes>\n\t\t<Include type="instance" source="DATA:BaseObjects/BaseObject.xml" />')
        return Unit(name, x, names=dict(unit=name, base=base),
                    what='锤子坦克的复制（继承的 BaseVehicle 复制' + ('保留' if dyn else '去掉') + ' DynamicsUpdate；速度 60 同战役）')


    def _n(part):
        return f'UNIT - CNV Dyn {part}'


    def mission(which='a'):
        if which == 'c':
            return fling_mission()
        m =Mission(name=f'CampDyn{which.upper()}', map=festival, units=[hammer_copy(False), hammer_copy(True)], facts={})
        for k, (tank, dy) in TANKS.items():
            m.put(tank, 'west field', -200.0, dy, angle=0.0, role=f'tank {k}', name=_n(f'Tank {k}'))
            m.put(TARGETS[which], 'west field', 0.0, dy, angle=180.0, side='s1', role=f'target {k}', name=_n(f'Target {k}'))
        return m


    def dyn_test(m, which='a'):
        t = Test()
        p1 = m.player('p1')
        x, y = m.site('west field')[:2]
        lanes = {1: TANKS[1]} if which == 'c' else TANKS
        gx = -20.0 if which == 'c' else 200.0      # c: the tank stops past the prop, short of the man (only the prop hits)
        for k, (_, dy) in lanes.items():
            t.waypoints[f'Test Goal {k}'] = (x + gx, y + dy)
            t.areas[f'Test Goal {k}'] = square(x + gx, y + dy, 40.0)
        start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
        start += [('UNIT_SET_STANCE', _n(f'{w} {k}'), HOLD_FIRE) for k in lanes for w in ('Tank', 'Target')]
        t.scripts.append(Script('Test - start', [], start))
        go = [('MOVE_NAMED_UNIT_TO', _n(f'Tank {k}'), f'Test Goal {k}') for k in lanes]
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
        going = ('FLAG', 'Test Going', 1)
        t.counters.append(('CNV_Dyn_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Dyn_Frames')], once=False))
        if which == 'c':
            t.counters.append(('CNV_Dyn_Health', '血量'))
            t.scripts.append(Script('Test - health', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', _n('Target 1'),
                                                           'CNV_Dyn_Health')], once=False))
            t.counters.append(('CNV_Dyn_Prop', '道具'))
            t.scripts.append(Script('Test - prop', [going, ('NAMED_NOT_DESTROYED', _n('Prop'))],
                                    [('INCREMENT_COUNTER', 1, 'CNV_Dyn_Prop')], once=False))
        for k in lanes:
            target, tank = _n(f'Target {k}'), _n(f'Tank {k}')
            t.counters.append((f'CNV_Dyn_Row{k}', f'行{k}'))
            for j, (cond, step) in enumerate([(('NAMED_NOT_DESTROYED', target), 1), (('NAMED_DYING', target), 1000),
                                              (('NAMED_INSIDE_AREA', tank, f'Test Goal {k}'), 1000000)]):
                t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                        [('INCREMENT_COUNTER', step, f'CNV_Dyn_Row{k}')], once=False))
        t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
        t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=RUN))]
        return t


    FLING = 'SS_FlingContainer01'


    def fling_mission():
        """c: an Uprising fling prop (SS_FlingContainer01, its name in RA3's WorldBuilder hashes) 40 in front of an enemy
        conscript, a retail Hammer driving through both: does RA3 know the prop, does the flung prop hurt the man."""
        m = Mission(name='CampDynC', map=festival, units=[], facts={})
        m.put(HAMMER, 'west field', -200.0, 0.0, angle=0.0, role='tank 1', name=_n('Tank 1'))
        m.put(FLING, 'west field', -40.0, 0.0, side='civ', role='prop', name=_n('Prop'))
        m.put(CONSCRIPT, 'west field', 0.0, 0.0, angle=180.0, side='s1', role='target 1', name=_n('Target 1'))
        return m


    MISSION = {'engine_dynamics': mission, 'engine_dynamics_b': lambda: mission('b'), 'engine_dynamics_c': lambda: mission('c')}
    CHECKS = {'engine_dynamics': {'a': dyn_test}, 'engine_dynamics_b': {'b': lambda m: dyn_test(m, 'b')},
              'engine_dynamics_c': {'c': lambda m: dyn_test(m, 'c')}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_facewp():
    """Named facing contrast; predictions/evidence: work/re/c_facewp_report.md.

    Two Guardians start east, ordered north/west at 4s (swapped in b); a third
    stays untouched east. Read actual hull heading from teamlog.states().hd,
    not from unchanged position. Exact turning timing remains a gap.
    MEASURED: a human host publishes no team headings; b AI host publishes ids
    12/13/14 (alpha/beta/control) on its default team, not the named empty crews.
    b f1..46: 0/0/0; f76..226: -180/117/0; 24 stable samples in the replay.
    Both runs have 25 displayed samples with alive mask 7. The b turn itself
    f61..68 is retained privately; exact order phase is not claimed by this replay.
    """
    import os

    import labpaths
    from maps import probe_border
    from parts import Mission, Script, Test, Unit
    from checks import engine_scripts8 as s8

    TANK = 'AlliedAntiVehicleVehicleTech1'
    HOST = 'CNVFaceHost'
    ROLES = ('alpha', 'beta', 'control')


    def mission(side='p1'):
        source = os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Structures', 'AlliedPowerPlant.xml')
        with open(source, encoding='utf-8') as f:
            xml = f.read()
        xml = xml.replace('id="AlliedPowerPlant"', f'id="{HOST}"')
        xml = xml.replace('EditorName="AlliedPowerPlant"', f'EditorName="{HOST}"')
        xml = xml.replace('<Behaviors>', '<Behaviors>\n'
            '<DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="4000"/>')
        unit = Unit(HOST, xml, names=dict(unit=HOST),
                    what='电厂复制体，只用 CNVTeams 记录所属玩家队伍的真实朝向',
                    params=dict(of='AlliedPowerPlant', every=15))
        m = Mission(name='CampFaceWP', map=probe_border, units=[unit], facts={}, ext=True)
        m.put(HOST, 'stop row', -500., -3000., side=side, role='observer')
        for k, role in enumerate(ROLES):
            crew = m.crew('Face'+role.title(), side=side)
            m.put(TANK, 'stop row', 200.+500.*k, -1800., angle=0.,
                  side=side, role=role, name='CNV Face '+role, props={'originalOwner': crew})
        m.waypoint('north', 'CNV Face North', 'stop row', 200., -800.)
        m.waypoint('west', 'CNV Face West', 'stop row', -800., -1800.)
        return m


    def check(m, which):
        t = Test()
        t.scripts.append(Script('Test - face hold', [], [
            ('UNIT_ALLOW_AI_AUTOACQUIRE', m.role(r).name, 0) for r in ROLES]))
        directions = ('north', 'west') if which == 'a' else ('west', 'north')
        s8.at(t, 'face order', 4., [
            ('NAMED_FACE_WAYPOINT', m.role(r).name, m.mark(d))
            for r, d in zip(ROLES, directions)])
        s8.total(t, 'CNV_FW_Alive', '存活位', [
            (1 << k, ('NAMED_NOT_DESTROYED', m.role(r).name))
            for k, r in enumerate(ROLES)])
        s8.frames(t, 'CNV_FW_Frame', '逻辑帧', [])
        t.expect = [('存活位', 0., '==', 7)]
        s8.watch(t, 12., .5)
        return t


    MISSION = {'engine_facewp': mission, 'engine_facewpai': lambda: mission('s1')}
    CHECKS = {'engine_facewp': {'a': lambda m: check(m, 'a')},
              'engine_facewpai': {'b': lambda m: check(m, 'b')}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def fence():
    """Fence tests (fence in scenes.py): at GO_AT every soldier is sent to the middle of his ring, again every few
    seconds. Counted: the player's peacekeepers inside each ring (an area a little inside its walls).

    bar: none gets into a closed ring; all three get into the open one (the control).
    """
    from .scenes import FENCE_RINGS as RINGS
    from parts import Script, Test, counted, square

    GO_AT, RUN = 3.0, 60.0
    INSIDE = 70.0                                   # half-side of the counted area (the ring's walls stand at 110)


    def bar(m):
        t = Test()
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('SET_MILLISECOND_TIMER', 'Test - go', GO_AT)]))
        go = []
        labels = {'wood': '木篱笆里', 'stone': '石栏里', 'palace': '宫墙里', 'open': '开口的里'}
        for ring in RINGS:
            go += [('MOVE_NAMED_UNIT_TO', m.role(f'soldier {ring} {j}').name, m.mark(f'inside {ring}')) for j in (1, 2, 3)]
            t.areas[f'Test {ring}'] = square(*m.point(f'inside {ring}'), INSIDE)
            counted(f'Test {ring}', labels[ring], t, template='AlliedAntiInfantryInfantry', area=f'Test {ring}', most=4)
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go')],
                                go + [('SET_MILLISECOND_TIMER', 'Test - go', 5.0)], once=False))
        t.expect += [(labels[r], 1, '==', 0) for r in ('wood', 'stone', 'palace')] + [('开口的里', 1, 'ever==', 3)]
        t.bench = [('bench_camera', dict(x=m.point('inside wood')[0] + 230, y=m.point('inside wood')[1] - 230,
                                         look=False)),
                   ('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=len(t.counters)))]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'fence': {'bar': bar},
    }
    return dict(CHECKS=CHECKS)


def engine_float():
    """Engine unit test: a building in the air (ADR 0019 layer 2, batch 5; docs/engine/air.md) -- which of retail's
    pieces make a structure float, and what each does to targeting, ground paths, moving and dying.

    Generals' rules (read, docs/engine/air.md 1): a weapon picks its victims by KindOf and the AIRBORNE_TARGET status
    bit only, never by height; only a locomotor sets that bit, and a structure has none; an airborne object that is not
    a vehicle / infantry is nobody's target. A structure's ground footprint is laid when it is placed and does not move
    with it. Retail RA3 hints that an attached object can take its parent's bit (IrradiatedTargetDamageDealer:
    AttachUpdate ParentStatusToCopy="AIRBORNE_TARGET").

    On the range probe map (maps/probe_range.py, flat), three groups 1500 apart, the enemy's (s1) floating things each
    with two of the player's IFVs (AlliedAntiAirVehicleTech1, anti-air) and two Hammers (ground only) SHOOTERS south:

      kirov   'removed gun'  a retail Kirov (SovietBomberAircraft): the aircraft-as-platform control; two of the
                             player's peacekeeper squads under it (does its crash kill them?)
      plant   'switch gun'   a carrier Kirov and CNV_FloatPlant (an Allied power plant, 5000 health, an AttachUpdate:
                             STICK_TO_PARENT TELEPORT to a same-player Kirov within RANGE) placed BELOW south of it
      plantair 'low gun'     the same with CNV_FloatPlantAir (ParentStatusToCopy="AIRBORNE_TARGET")

    The Kirovs hold fire (NO_ATTACK by script). AA: the IFVs are sent at their group's target, deleted at GROUND;
    GROUND: the Hammers are; SPOT: the plant group's first Hammer is sent to where its plant was placed (is the old
    footprint still in the way?), the other Hammers are deleted; MOVE: both carriers fly LEG west (does the plant come
    along?); KILL: all three Kirovs are killed (does a plant fall, die, stay?).

    Counters (the bench reads all four):
      基洛夫血量  the kirov's health % + 1000 x the player's peacekeepers under it (a template count in an area)
      挂厂血量    CNV_FloatPlant's health %
      挂厂空血量  CNV_FloatPlantAir's health %
      挂态       plant ATTACHED 1, plantair ATTACHED 10, plant inside its carrier's goal 100, plantair inside its
                 carrier's goal 1000, the plant group's first Hammer inside the plant's old spot 10000

    Read (测, 2026-11-05, run CampFloatFloat_mcp_1105_053518; the bench's seconds 1-2 s ahead of the timers):
      基洛夫 2100 (2 squads + 100 %) -> 2079 s6-s14 under the IFVs, unchanged under the Hammers (2080 at s27);
      dead at s40, after which nobody resets the counter (the health action needs the living unit) and it climbs by
      2000 a frame until s46: the squads under it counted 0 from s46 -- the falling wreck killed them.
      挂厂 / 挂厂空 identical: 100 -> 92 under the IFVs (the IFV hits buildings too), -> 86 under the Hammers;
      挂态 0 throughout: neither plant ever ATTACHED nor moved with its carrier, the Hammer never got onto the plant's
      spot; ParentStatusToCopy never came into play. Why is open (docs/engine/air.md 1): an AttachUpdate on a
      STRUCTURE does nothing, or the range is 3D (the plant was ~202 from the Kirov hovering at 175, Range 200).
    """
    import os

    import labpaths
    from maps import probe_range
    from parts import Mission, Script, Test, Unit, counted, square, status

    KIROV, PLANT, IFV, HAMMER = 'SovietBomberAircraft', 'AlliedPowerPlant', 'AlliedAntiAirVehicleTech1', \
        'SovietAntiVehicleVehicleTech1'
    FOOT = 'AlliedAntiInfantryInfantry'
    GROUPS = {'kirov': 'removed gun', 'plant': 'switch gun', 'plantair': 'low gun'}
    FLOAT, FLOAT_AIR = 'CNV_FloatPlant', 'CNV_FloatPlantAir'
    BELOW, RANGE, SHOOTERS, LEG, SPOT_R, GOAL_R = 100.0, 200.0, 600.0, 300.0, 40.0, 120.0
    AA, GROUND, SPOT, MOVE, KILL, RUN = 4.0, 15.0, 25.0, 26.0, 42.0, 58.0


    def _sub1(x, old, new):
        assert x.count(old) == 1, (old[:60], x.count(old))
        return x.replace(old, new, 1)


    def float_plant(id=FLOAT, parent=KIROV, copy=False, health=5000.0, rng=RANGE):
        """A retail Allied power plant that, placed (or built) within rng of a same-player `parent`, goes onto it and
        rides it (AttachUpdate STICK_TO_PARENT TELEPORT, no offset: it sits at the parent's centre). copy: it also takes
        the parent's AIRBORNE_TARGET bit (retail IrradiatedTargetDamageDealer's ParentStatusToCopy)."""
        x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Structures', PLANT + '.xml'), encoding='utf-8').read()
        x = _sub1(x, f'id="{PLANT}"', f'id="{id}"')
        x = _sub1(x, f'EditorName="{PLANT}"', f'EditorName="{id}"')
        x = _sub1(x, 'MaxHealth="1000.0"', f'MaxHealth="{health:.1f}"')
        copied = '\n\t\t\t\tParentStatusToCopy="AIRBORNE_TARGET"' if copy else ''
        x = _sub1(x, '\t\t</Behaviors>', (f'\t\t\t<AttachUpdate id="ModuleTag_CNV_Float" Range="{rng:g}" IdleScanDelay="0.5s"\n'
            f'\t\t\t\tFlags="SAME_PLAYER_ONLY STICK_TO_PARENT TELEPORT"\n'
            f'\t\t\t\tAttachedObjectStatus="ATTACHED"{copied}>\n'
            f'\t\t\t\t<ObjectFilter Rule="NONE" Relationship="SAME_PLAYER">\n'
            f'\t\t\t\t\t<IncludeThing>{parent}</IncludeThing>\n'
            f'\t\t\t\t</ObjectFilter>\n'
            f'\t\t\t</AttachUpdate>\n'
            f'\t\t</Behaviors>'))
        return Unit(id, x, names=dict(unit=id),
                    what=f'挂在 {parent} 上的发电厂（探针）：{rng:g} 内有同一玩家的 {parent} 就瞬移上去跟着走'
                         + ('，并复制它的 AIRBORNE_TARGET' if copy else ''),
                    params=dict(parent=parent, copy=copy, health=health, range=rng))


    def mission():
        m = Mission(name='CampFloat', map=probe_range,
                    units=[float_plant(), float_plant(FLOAT_AIR, copy=True)], facts={})
        for part, site in GROUPS.items():
            P = part.title()
            m.put(KIROV, site, side='s1', role=f'{part} kirov', name=f'UNIT - CNV Float {P} Kirov')
            for k, dx in ((1, -60), (2, 60)):
                m.put(IFV, site, dx, -SHOOTERS, side='p1', role=f'{part} ifv {k}', name=f'UNIT - CNV Float {P} IFV {k}')
                m.put(HAMMER, site, dx, -SHOOTERS - 80, side='p1', role=f'{part} hammer {k}',
                      name=f'UNIT - CNV Float {P} Hammer {k}')
        for part, tpl in (('plant', FLOAT), ('plantair', FLOAT_AIR)):
            m.put(tpl, GROUPS[part], 0, -BELOW, side='s1', role=part, name=f'UNIT - CNV Float {part.title()}')
            m.waypoint(f'{part} goal', f'CNV Float {part.title()} Goal', GROUPS[part], -LEG, 0)
        m.waypoint('plant spot', 'CNV Float Plant Spot', GROUPS['plant'], 0, -BELOW)
        for k, dx in ((1, -40), (2, 40)):
            m.put(FOOT, GROUPS['kirov'], dx, 0, side='p1', role=f'foot {k}', name=f'UNIT - CNV Float Foot {k}')
        return m


    def float_test(m):
        t = Test()

        def n(part):
            return m.role(part).name

        kirovs = [n(f'{p} kirov') for p in GROUPS]
        ifvs = [n(f'{p} ifv {k}') for p in GROUPS for k in (1, 2)]
        hammers = [n(f'{p} hammer {k}') for p in GROUPS for k in (1, 2)]
        target = {'kirov': n('kirov kirov'), 'plant': n('plant'), 'plantair': n('plantair')}
        acts = {
            'AA': [('NAMED_ATTACK_NAMED', n(f'{p} ifv {k}'), target[p]) for p in GROUPS for k in (1, 2)],
            'Ground': [('NAMED_DELETE', u) for u in ifvs] +
                      [('NAMED_ATTACK_NAMED', n(f'{p} hammer {k}'), target[p]) for p in GROUPS for k in (1, 2)],
            'Spot': [('MOVE_NAMED_UNIT_TO', n('plant hammer 1'), m.mark('plant spot'))] +
                    [('NAMED_DELETE', u) for u in hammers if u != n('plant hammer 1')],
            'Move': [('MOVE_NAMED_UNIT_TO', n(f'{p} kirov'), m.mark(f'{p} goal')) for p in ('plant', 'plantair')],
            'Kill': [('NAMED_KILL', k) for k in kirovs],
        }
        timers = (('AA', AA), ('Ground', GROUND), ('Spot', SPOT), ('Move', MOVE), ('Kill', KILL))
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))] +
                                [('UNIT_CHANGE_OBJECT_STATUS', k, 'NO_ATTACK', 1) for k in kirovs] +
                                [('SET_MILLISECOND_TIMER', f'Test {k}', s) for k, s in timers]))
        t.scripts += [Script(f'Test - {k.lower()}', [('TIMER_EXPIRED', f'Test {k}')], acts[k]) for k, _ in timers]

        counted('CNV_Float_Kirov', '基洛夫血量', t, health=target['kirov'])
        counted('CNV_Float_Plant', '挂厂血量', t, health=target['plant'])
        counted('CNV_Float_Air', '挂厂空血量', t, health=target['plantair'])

        for p in ('plant', 'plantair'):
            t.areas[f'Test {p.title()} Goal'] = square(*m.point(f'{p} goal'), GOAL_R)
        t.areas['Test Plant Spot'] = square(*m.point('plant spot'), SPOT_R)
        rows = [(1, ('UNIT_HAS_OBJECT_STATUS', target['plant'], status('ATTACHED'))),
                (10, ('UNIT_HAS_OBJECT_STATUS', target['plantair'], status('ATTACHED'))),
                (100, ('NAMED_INSIDE_AREA', target['plant'], 'Test Plant Goal')),
                (1000, ('NAMED_INSIDE_AREA', target['plantair'], 'Test Plantair Goal')),
                (10000, ('NAMED_INSIDE_AREA', n('plant hammer 1'), 'Test Plant Spot'))]
        t.counters.append(('CNV_Float_Bits', '挂态'))
        t.scripts.append(Script('Test - CNV_Float_Bits zero', [], [('SET_COUNTER', 'CNV_Float_Bits', 0)], once=False))
        t.scripts += [Script(f'Test - CNV_Float_Bits {step}', [cond], [('INCREMENT_COUNTER', step, 'CNV_Float_Bits')],
                             once=False) for step, cond in rows]

        # four counter lines at most: the peacekeepers under the kirov ride on its health counter as thousands
        t.areas['Test Under Kirov'] = square(*m.site(GROUPS['kirov']), 250.0)
        t.scripts += [Script(f'Test - CNV_Float_Kirov foot {k}', [
            ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player('p1'), 3, k, FOOT, 'Test Under Kirov')],
            [('INCREMENT_COUNTER', 1000, 'CNV_Float_Kirov')], once=False) for k in range(1, 13)]
        # a measurement: no expectations, the readings are written up in docs/engine/air.md
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=4))]
        return t


    # --- engine_float_far: is it the range (3D ~202 > 200) or the structure? ---------------------------------------------
    # The same plant with Range 1000, alone with a Kirov at 'switch gun': ATTACHED and riding the Kirov to its goal =
    # the range was 3D; still never ATTACHED = an AttachUpdate on a STRUCTURE does nothing.
    # Read (测, 11-05, run CampFarFar_mcp_1105_064559, PASS): 挂态 10 (in its start spot, never ATTACHED) to s15, then
    # 1010 (the Kirov in its goal, the plant still at the start) to the end; health 100. A STRUCTURE does not attach.
    FLOAT_FAR, FAR_RANGE = 'CNV_FloatPlantFar', 1000.0
    FAR_MOVE, FAR_RUN = 10.0, 30.0


    def far_mission():
        m = Mission(name='CampFar', map=probe_range, units=[float_plant(FLOAT_FAR, rng=FAR_RANGE)], facts={})
        site = GROUPS['plant']
        m.put(KIROV, site, side='s1', role='kirov', name='UNIT - CNV FloatFar Kirov')
        m.put(FLOAT_FAR, site, 0, -BELOW, side='s1', role='plant', name='UNIT - CNV FloatFar Plant')
        m.waypoint('goal', 'CNV FloatFar Goal', site, -LEG, 0)
        return m


    def far_test(m):
        t = Test()
        kirov, plant = m.role('kirov').name, m.role('plant').name
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('UNIT_CHANGE_OBJECT_STATUS', kirov, 'NO_ATTACK', 1),
                                                     ('SET_MILLISECOND_TIMER', 'Test Move', FAR_MOVE)]))
        t.scripts.append(Script('Test - move', [('TIMER_EXPIRED', 'Test Move')],
                                [('MOVE_NAMED_UNIT_TO', kirov, m.mark('goal'))]))
        t.areas['Test Goal'] = square(*m.point('goal'), GOAL_R)
        t.areas['Test Start'] = square(*m.site(GROUPS['plant'], 0, -BELOW), SPOT_R)
        rows = [(1, ('UNIT_HAS_OBJECT_STATUS', plant, status('ATTACHED'))),
                (10, ('NAMED_INSIDE_AREA', plant, 'Test Start')),
                (100, ('NAMED_INSIDE_AREA', plant, 'Test Goal')),
                (1000, ('NAMED_INSIDE_AREA', kirov, 'Test Goal'))]
        t.counters.append(('CNV_FloatFar_Bits', '挂态'))
        t.scripts.append(Script('Test - CNV_FloatFar_Bits zero', [], [('SET_COUNTER', 'CNV_FloatFar_Bits', 0)],
                                once=False))
        t.scripts += [Script(f'Test - CNV_FloatFar_Bits {step}', [cond],
                             [('INCREMENT_COUNTER', step, 'CNV_FloatFar_Bits')], once=False) for step, cond in rows]
        counted('CNV_FloatFar_Plant', '挂厂血量', t, health=plant)
        # the Kirov reaching its goal shows the run went through; the plant's bits are the reading
        t.expect = [('挂态', 0, 'ever>=', 1000, FAR_RUN - 2)]
        t.bench = [('bench_watch', dict(seconds=FAR_RUN, every=1, sheet=False, lines=4))]
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_float': mission, 'engine_float_far': far_mission}
    CHECKS = {'engine_float': {'float': float_test}, 'engine_float_far': {'far': far_test}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_formation_player():
    """Engine line D, round 80 (coordinator 11-12, the user's ask): does the PLAYER's own group move keep its members at
    the slowest one's pace, and how far apart do they stand? docs/engine/pathing.md 3/5 measured only scripted team moves
    (the fast never waits); 5 (a) read that the formation path runs only for units the player put in a formation. This
    mission gives the player two identical mixed groups on open ground (the probe map's pace lanes): two Guardian tanks
    (speed 80) and two Peacekeepers (50), each a copy with ra3ext's read-only CNVProbe (a `probe` line per frame the
    host moved: per-unit trajectory, the step is its actual speed). The bench then plays the player:

      plain       box-select the north group, right-click the goal 600 east: the ordinary group move
      formation   box-select the south group, right-DRAG at the goal (bench_box right=true, a short north-south front):
                  the formation move with its preview (FormationAssistant)

    Counters (every frame): per lane +1 for each tank inside the goal square (half 150), +10 for each Peacekeeper.
    No expectations: the readings are the probe lines (scripts/d80_formation.py in work/re reads them).
    """
    import os

    import labpaths
    from maps import probe_range
    from parts import NOT, Mission, Script, Test, Unit, square

    TANK, MAN = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
    PROBE = {TANK: 'CNV_FormTank', MAN: 'CNV_FormMan'}
    EVERY, LINES = 150, 6000
    # one camera sees ~500 x 380 here (bench 1112_122439: a 600-long layout fell off the screen), so both lanes, starts and
    # goals fit in it: placed from the pace lane's start (500, 1200)
    LANES = FORMATION_LANES


    X0, X1 = FORMATION_X0, 1000.0
    SPOTS = [(TANK, 0.0, 25.0), (TANK, 0.0, -25.0), (MAN, -45.0, 25.0), (MAN, -45.0, -25.0)]
    VIEW = ((X0 + X1) / 2, 1300.0)
    RUN = 40.0


    def probe_copy(template):
        pid = PROBE[template]
        with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', template + '.xml'), encoding='utf-8') as f:
            x = f.read()
        assert x.count(f'id="{template}"') == 1 and x.count('<Behaviors>') == 1
        x = x.replace(f'id="{template}"', f'id="{pid}"', 1).replace(f'EditorName="{template}"', f'EditorName="{pid}"')
        x = x.replace('<Behaviors>', (f'<Behaviors>\n'
            f'\t\t\t<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>'), 1)
        return Unit(pid, x, names=dict(unit=pid), what=f'原版 {template} 的复制（探针）：多一个 ra3ext 的 CNVProbe，逐帧记位置',
                    params=dict(of=template, every=EVERY, lines=LINES))


    def mission():
        m = Mission(name='CampFormP', map=probe_range, units=[probe_copy(TANK), probe_copy(MAN)], facts={})
        m.ext = True
        for lane, y in LANES.items():
            for k, (tpl, dx, dy) in enumerate(SPOTS):
                m.put(PROBE[tpl], 'pace start', X0 - 500.0 + dx, y - 1200.0 + dy, role=f'{lane} {k}',
                      name=f'UNIT - CNV Form {lane.title()} {k}')
        return m


    def player_moves(m, both=False):
        """f: the formation lane right-drags (D 84: that pans the camera in RA3, the units do not move); b: it drags with
        both buttons held, a longer front -- a try at the formation preview."""
        t = Test()
        t.waypoints['Test Form View'] = VIEW
        t.scripts.append(Script('Test - view', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                    ('MOVE_CAMERA_TO', 'Test Form View', 0.1, 0.0, 0.0, 0.0)]))
        steps = [('bench_watch', dict(seconds=2, every=1, sheet=False, lines=2)),
                 ('bench_view', dict(x=VIEW[0], y=VIEW[1], look=True))]
        for lane, y in LANES.items():
            counter = f'CNV_Form_{lane.title()}'
            t.counters.append((counter, lane))
            goal = f'Test Form {lane.title()} Goal'
            t.areas[goal] = square(X1, y, 70.0)
            t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
            for k, (tpl, _, _) in enumerate(SPOTS):
                t.scripts.append(Script(f'Test - {counter} {k}', [('NAMED_INSIDE_AREA', m.role(f'{lane} {k}').name, goal)],
                                        [('INCREMENT_COUNTER', 1 if tpl == TANK else 10, counter)], once=False))
            steps.append(('bench_box', dict(x0=X0 - 90, y0=y - 55, x1=X0 + 40, y1=y + 55, look=True)))
            if lane == 'plain':
                steps.append(('bench_click', dict(x=X1, y=y, right=True, look=True)))
            else:
                half = 60 if both else 30
                steps.append(('bench_box', dict(x0=X1, y0=y - half, x1=X1, y1=y + half, look=True,
                                                **(dict(both=True) if both else dict(right=True)))))
        t.expect = []
        steps.append(('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=3)))
        t.bench = steps
        return t


    HOTKEYS = 'UIMouseTacticalMiscHotKeys'
    HOTKEY_SLOT, HOTKEY_VK = 'CycleHarvesters', 0x4E      # KEY_N (DefaultHotKeys); the probe map has no harvester to cycle


    class HotkeyPack:
        """D 85 canary: retail leaves the Create Formation hotkey ("keep formation when moving", MiscHotKeys.xsd) unbound.
        This pack is retail's UIMouseTacticalMiscHotKeys (SDK UI/Mouse/Settings.xml, static stream) with CreateFormation
        bound to the CycleHarvesters slot (key N), compiled into the static stream where splice_assets puts it over
        retail's (as a music pack's map). Made on first use: the offline contract never writes the SDK."""
        FOLDER = 'CNVFormKeys'
        files = ()

        @property
        def include(self):
            with open(os.path.join(labpaths.SDK3, 'SageXML', 'UI', 'Mouse', 'Settings.xml'), encoding='utf-8-sig') as f:
                x = f.read()
            head = f'<{HOTKEYS}\n\t\tid="{HOTKEYS}"'
            body = x[x.index(head):x.index(f'</{HOTKEYS}>') + len(f'</{HOTKEYS}>')]
            assert 'CreateFormation=' not in body
            body = body.replace(f'id="{HOTKEYS}"', f'id="{HOTKEYS}"\n\t\tCreateFormation="{HOTKEY_SLOT}"', 1)
            data = os.path.join(labpaths.SDK3, 'Mods', self.FOLDER, 'Data')
            os.makedirs(data, exist_ok=True)
            with open(os.path.join(data, 'hotkeys.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
                f.write('<?xml version="1.0" encoding="utf-8"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset">\n\t'
                        + body + '\n</AssetDeclaration>\n')
            return f'DATA:{self.FOLDER}/Data/hotkeys.xml'

        def check(self, files):
            """The spliced static streams carry our hotkey table (an instance retail has: it replaced retail's)."""
            from ra3voice import manifest, refpack
            unpack = lambda b: refpack.decompress(b) if refpack.is_refpack(b) else b
            where = [n for n, b in files if n.lower().startswith('data\\static') and n.lower().endswith('.manifest')
                     and any(a.name == f'{HOTKEYS}:{HOTKEYS}' for a in manifest.parse(unpack(b)))]
            assert where, f'{HOTKEYS} is in no spliced static stream: the binding never reaches the game'
            print(f'hotkeys: {HOTKEYS} spliced into {where}')


    def hotkey_mission():
        m = mission()
        m.name = 'CampFormH'
        m.statics = [HotkeyPack()]
        return m


    def hotkey_moves(m):
        """h: the formation lane is box-selected, gets Create Formation (key N, bound by HotkeyPack), then a plain
        right-click at its goal; the plain lane as in f. Same pace (tanks held to 50) = the hotkey is the same-pace entry."""
        t = player_moves(m)
        lane = [k for k, s in enumerate(t.bench) if s[0] == 'bench_box' and s[1].get('right')]
        assert len(lane) == 1
        x, y = t.bench[lane[0]][1]['x0'], (t.bench[lane[0]][1]['y0'] + t.bench[lane[0]][1]['y1']) / 2
        t.bench[lane[0]:lane[0] + 1] = [('bench_key', dict(vk=HOTKEY_VK, look=True)),
                                        ('bench_click', dict(x=x, y=y, right=True, look=True))]
        return t


    def sync_moves(m):
        """s: the formation lane's four press 同速 by script at the start (NAMED_USE_COMMANDBUTTON_ABILITY); then both lanes
        get the plain right-click. Expected (D 91): `sync:` lines in ra3ext.log with the tanks at tier ~60-65 % while the
        lane moves, the plain lane absent; 坦克先到帧 (frames a tank is in the goal and no Peacekeeper is) ~0 for the
        switched lane, ~40 for the plain one (81 vs 51 over 350, bench D 80).
        Bench D 94 (CampFormSS_mcp_1112_222330): switched 18, plain 86; tanks at tier 60 (5.33 -> 3.2 a frame), the men
        at 100 (3.33). The 18 is the layout, not the sync: the men start 45 behind (SPOTS) = 13.5 frames at their pace,
        and the first look (frame 511, the move from ~505) lets the tanks run 6 frames at full speed, ~3.6 more."""
        t = player_moves(m)
        sync = m.facts['sync command']                  # engine_formation_player in scenes.py (D 92)
        t.scripts.append(Script('Test - sync timer', [], [('SET_MILLISECOND_TIMER', 'Test Sync On', 0.5)]))
        t.scripts.append(Script('Test - sync on', [('TIMER_EXPIRED', 'Test Sync On')],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(f'formation {k}').name, sync)
                                 for k in range(len(SPOTS))]))
        lane = [k for k, s in enumerate(t.bench) if s[0] == 'bench_box' and s[1].get('right')]
        assert len(lane) == 1
        b = t.bench[lane[0]][1]
        t.bench[lane[0]] = ('bench_click', dict(x=b['x0'], y=(b['y0'] + b['y1']) / 2, right=True, look=True))
        for lane_name, y in LANES.items():
            counter, goal = f'CNV_Form_{lane_name.title()}_Ahead', f'Test Form {lane_name.title()} Goal'
            t.counters.append((counter, f'{lane_name} 坦克先到帧'))
            tank_in = [('NAMED_INSIDE_AREA', m.role(f'{lane_name} {k}').name, goal)
                       for k, s in enumerate(SPOTS) if s[0] == TANK]
            men_out = [('NAMED_INSIDE_AREA', m.role(f'{lane_name} {k}').name, goal, NOT)
                       for k, s in enumerate(SPOTS) if s[0] == MAN]
            for j, c in enumerate(tank_in):          # either tank in, both Peacekeepers out (a tank in twice counts twice)
                t.scripts.append(Script(f'Test - {counter} {j}', [c] + men_out, [('INCREMENT_COUNTER', 1, counter)],
                                        once=False))
        # all four in on both lanes; the switched tanks lead by the layout's head start only (D 94: 18 vs 86)
        t.expect = [('plain', 100, '==', 22), ('formation', 100, '==', 22),
                    ('formation 坦克先到帧', 100, '<=', 30), ('plain 坦克先到帧', 100, '>=', 60)]
        return t


    def dense_moves(m):
        """d: as s, but the formation lane's four press 密集 (ra3ext CNVSync, DENSE status bit: a moving group of ours is
        ordered again to points pulled halfway to its centre). Expected (D 93): `dense:` lines in ra3ext.log for the
        switched lane only; at the goal its members stand 30-50 apart pairwise, the plain lane's 60-100 (the last
        `probe` positions; scripts/d94_dense.py in work/re reads them). Both lanes all in."""
        t = player_moves(m)
        dense = m.facts['dense command']                # engine_formation_player in scenes.py (D 92)
        t.scripts.append(Script('Test - dense timer', [], [('SET_MILLISECOND_TIMER', 'Test Dense On', 0.5)]))
        t.scripts.append(Script('Test - dense on', [('TIMER_EXPIRED', 'Test Dense On')],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(f'formation {k}').name, dense)
                                 for k in range(len(SPOTS))]))
        lane = [k for k, s in enumerate(t.bench) if s[0] == 'bench_box' and s[1].get('right')]
        assert len(lane) == 1
        b = t.bench[lane[0]][1]
        t.bench[lane[0]] = ('bench_click', dict(x=b['x0'], y=(b['y0'] + b['y1']) / 2, right=True, look=True))
        # 紧凑帧 (D 96): the map has no "distance between two units" condition (script_catalog), so each lane tiles the
        # goal's north half with candidate squares of side COMPACT; a frame where all four stand in one of them (and in the
        # goal) counts +1 per such square. Bench D 95 (CampFormSD_mcp_1112_225220): the switched lane ends 31 x 40 around
        # lane + 31, the plain one 71 x 71 -- and neither crowd centres on the click point (15-30 north), hence the tiling.
        # Bench D 96 (CampFormSD_mcp_1112_230312) PASS: formation 紧凑帧 from s82, 767 by s118; plain 0 throughout.
        for lane_name, y in LANES.items():
            counter, goal = f'CNV_Form_{lane_name.title()}_Tight', f'Test Form {lane_name.title()} Goal'
            t.counters.append((counter, f'{lane_name} 紧凑帧'))
            members = [m.role(f'{lane_name} {k}').name for k in range(len(SPOTS))]
            for cx in TIGHT_X:
                for dy in TIGHT_DY:
                    box = f'Test Form {lane_name.title()} Tight {cx:.0f} {dy:+.0f}'
                    t.areas[box] = square(cx, y + dy, COMPACT / 2)
                    t.scripts.append(Script(f'Test - {counter} {cx:.0f} {dy:+.0f}',
                                            [('NAMED_INSIDE_AREA', n, a) for n in members for a in (box, goal)],
                                            [('INCREMENT_COUNTER', 1, counter)], once=False))
        t.expect = [('plain', 100, '==', 22), ('formation', 100, '==', 22),
                    ('formation 紧凑帧', 100, '>', 0), ('plain 紧凑帧', 100, '==', 0)]
        return t


    COMPACT = 55.0
    TIGHT_X = [950.0 + 10 * i for i in range(9)]            # 950 .. 1030
    TIGHT_DY = [-10.0 + 10 * j for j in range(8)]           # lane - 10 .. lane + 60


    MISSION = {'engine_formation_player': mission, 'engine_formation_hotkey': hotkey_mission}
    CHECKS = {'engine_formation_player': {'f': player_moves, 'b': lambda m: player_moves(m, both=True)},
              'engine_formation_hotkey': {'h': hotkey_moves},
              'engine_formation_sync': {'s': sync_moves, 'd': dense_moves}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_freefall():
    """Engine line A round 157: FreefallUpdate -- does it carry a man the Bullfrog's man cannon throws down to the ground?

    Every infantry of ours has it (SDK BaseInfantry.xml: ModuleTag_FreefallUpdate, ModelConditionsToSet STUNNED_FLAILING,
    InitialVelocity 5, Acceleration 1, TerminalVelocity 15; the comment: 'for objects that don't have Dynamics but that
    still may fall out of the sky on death'). In our 9 levels a man is in the air when the Bullfrog throws him
    (a01's waves: SovietAntiAirShip, EjectPassengersSpecialAbilityUpdate Height 200 ApexHeight 20 Speed 20,
    TimePerPassenger 0.5 s; engine_transport: down on the spot ~2 s after the press). Whether that descent is the
    eject's own arc or this module's fall is what the probe tells, by changing the module and nothing else:

    On maps/probe_border.py, three rows, each a Bullfrog of the player with one man put in at LOAD, holding fire;
    at GO each Bullfrog throws its man at its own waypoint THROW east (NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT):
      A  a retail conscript (SovietAntiInfantryInfantry)
      S  CNVFallSlow: the conscript under a new id, its FreefallUpdate (same id, overriding BaseInfantry's)
         InitialVelocity 0, Acceleration 0.05, TerminalVelocity 1 -- a fall of 200 would take ~200 frames
      F  CNVFallFast: the same with Acceleration 5, TerminalVelocity 60
    Counters (four lines fit), frames counted from GO on (the press's frame is frame 1):
      帧数        frames since GO + 1000 x frames A's man holds PARACHUTING
      A / S / F  frames the man holds AIRBORNE_TARGET + 1000 x frames until he is first inside the 120 square at his
                 waypoint (a man never there counts every frame)
    Prediction: if the module carries the descent, S's AIRBORNE frames and its square wait far exceed A's, F's
    are fewer; if the eject's arc does (the module only for the dead and the lifted), the three rows read alike.

    Bench 11-11 (round 157, CampFallFall_mcp_1111_032014, PASS -- readings only):
      A, S and F read the same every half second: AIRBORNE_TARGET from frame 1 to 125 (then never), inside the square
      from frame 22 (the throw's flat run, as engine_transport's ~2 s); final 22125 / 22125 / 22125.
      帧数 96xxx at the end: A's man PARACHUTING frames ~44-139 (96 frames), after he is over the spot.
      So the module's parameters do not change a thrown man's fall: the parachute does it, airborne ~8 s after the
      press, ~6 s over the spot. FreefallUpdate then acts on the dead and the lifted only (not benched: line C's lift
      is paused; a dead man's fall is presentation). Not ruled out: the copies' same-id FreefallUpdate not overriding
      BaseInfantry's (a copy whose FreefallUpdate is renamed / removed would tell).
    """
    import os

    from maps import probe_border
    from parts import Mission, Script, Test, Unit, square, status
    import checks.engine_scripts8 as s8

    FROG, MAN = 'SovietAntiAirShip', 'SovietAntiInfantryInfantry'
    O = (1300.0, 4300.0)                            # probe_border's 'stop row'
    X0 = 900.0
    THROW = 300.0                                   # the waypoint east of each Bullfrog
    BOX = 120.0
    FALLS = {'S': ('CNVFallSlow', 0.0, 0.05, 1.0), 'F': ('CNVFallFast', 0.0, 5.0, 60.0)}
    ROWS = {'A': (MAN, 3900.0), 'S': (FALLS['S'][0], 4200.0), 'F': (FALLS['F'][0], 4500.0)}
    LOAD, GO, RUN = 2.0, 3.0, 25.0


    def _n(part):
        return f'UNIT - CNV FF {part}'


    def fall_unit(new, v0, acc, top):
        """The conscript (SDK Soviet/Units/SovietAntiInfantryInfantry.xml) under `new`, with a FreefallUpdate of its own
        (the inherited module's id, so it replaces BaseInfantry's): only the fall changed."""
        import labpaths
        path = os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Units', f'{MAN}.xml')
        x = open(path, encoding='utf-8').read()
        for old in (f'id="{MAN}"', f'EditorName="{MAN}"'):
            assert x.count(old) == 1, old
            x = x.replace(old, old.replace(MAN, new))
        end = '\t\t</Behaviors>'
        assert x.count(end) == 1
        module = (f'\t\t\t<FreefallUpdate id="ModuleTag_FreefallUpdate" ModelConditionsToSet="STUNNED_FLAILING" '
                  f'InitialVelocity="{v0:g}" Acceleration="{acc:g}" TerminalVelocity="{top:g}"/>\n')
        x = x.replace(end, module + end)
        return Unit(new, x, what=f'对照：动员兵换了 id，下落 v0={v0:g} a={acc:g} 终速={top:g}')


    def mission(name='CampFall'):
        m = Mission(name=name, map=probe_border, units=[fall_unit(*f) for f in FALLS.values()], facts={})
        m.spawns |= {FROG, MAN}
        for row, (man, y) in ROWS.items():
            m.put(FROG, 'stop row', X0 - O[0], y - O[1], angle=0.0, name=_n(f'{row} Box'), role=f'{row} box')
            c = m.crew(f'FF{row}')
            m.put(man, 'stop row', X0 - 100.0 - O[0], y - 90.0 - O[1], angle=0.0, name=_n(f'{row} Man'),
                  role=f'{row} man', props={'originalOwner': c})
            m.waypoint(f'throw {row}', f'CNV FF Throw {row}', 'stop row', X0 + THROW - O[0], y - O[1])
        return m


    def fall(m):
        t = Test()
        hold = [('UNIT_CHANGE_OBJECT_STATUS', _n(f'{r} {k}'), status('NO_ATTACK'), 1) for r in ROWS for k in ('Box', 'Man')]
        s8.at(t, 'hold', 0.1, hold + [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
        s8.at(t, 'load', LOAD, [('TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY', m.teams[f'FF{r}'], _n(f'{r} Box'))
                                for r in ROWS])
        s8.at(t, 'go', GO, [('SET_FLAG', 'Test FF Going', 1)]
              + [('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', _n(f'{r} Box'),
                  'Command_ActivateEjectPassengersSpecialPower', m.mark(f'throw {r}')) for r in ROWS])
        going = ('FLAG', 'Test FF Going', 1)
        s8.frames(t, 'CNV_FF_Frames', '帧数', [going])
        t.scripts.append(Script('Test - FF A para', [going, ('UNIT_HAS_OBJECT_STATUS', _n('A Man'), status('PARACHUTING'))],
                                [('INCREMENT_COUNTER', 1000, 'CNV_FF_Frames')], once=False))
        for r in ROWS:
            man = _n(f'{r} Man')
            area = f'Test FF Throw {r}'
            t.areas[area] = square(*m.point(f'throw {r}'), BOX)
            c = f'CNV_FF_{r}'
            t.counters.append((c, r))
            t.scripts.append(Script(f'Test - {c} air', [going, ('UNIT_HAS_OBJECT_STATUS', man, status('AIRBORNE_TARGET'))],
                                    [('INCREMENT_COUNTER', 1, c)], once=False))
            t.scripts.append(Script(f'Test - {c} wait', [going, ('FLAG', f'Test FF In {r}', 0)],
                                    [('INCREMENT_COUNTER', 1000, c)], once=False))
            t.scripts.append(Script(f'Test - {c} in', [going, ('NAMED_INSIDE_AREA', man, area)],   # after the counts
                                    [('SET_FLAG', f'Test FF In {r}', 1)], once=False))
        t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
        t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN))]
        return t


    MISSION = {'engine_freefall': mission}
    CHECKS = {'engine_freefall': {'fall': fall}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_hull():
    """Engine unit test: does a moving tank's hull turn to where it drives, and how soon -- read by the side / rear
    scalar a hit takes (engine_shot flank: BaseTankArmor Side 105 beyond 45 degrees, Rear 110 beyond 135, by where
    the shooter stands against the victim's facing; docs/engine/weapons.md 4).

    Every pair: engine_shot's flank V4 (one 4000 EXPLOSIVE instant hit, no pre-attack, no scatter; the next hit >= 4.5 s
    later) HULL_REACH south of engine_missile's 10 000-health Hammer, which faces south (the map's default for s1: the
    shooter is in front of it). Both keep NO_ATTACK until the fire order. At MOVE the check's Hammers are sent (PAIRS:
    east, north of where they stand); each V4 is told to fire the pair's seconds after that. Counter per Hammer:
    percent lost (1 per percent; a front hit 40, a side 42, a rear 44).

      turn   still  not sent (the control)                    front 40
             north  north 600, fire 2.5 s after               turned: the shooter behind it, rear 44; not: front 40
             east   east 600, fire 2.5 s after                turned: the shooter ~110 off its facing, side 42
             short  north 120 (behind it, short), 2.5 s after turned and arrived: rear 44; reversed: front 40
      rate   r15 / r30 / r50 / r80: north 600, fire 0.15 / 0.3 / 0.5 / 0.8 s after -- the turn under way (front 40
             below 45 degrees off, side 42 to 135, rear 44 past it)

    Prediction from the data (round 187, before the bench): the Hammer's locomotor turns (TurnTimeSeconds 1.25,
    ClampOrientationToPathTangent true), so north 44, east 42; short may reverse (CanReverseMove true, the goal 120
    behind) -- not predicted; the rate pairs mid-turn. The model before this round never turned a moving hull: 40 on
    every pair.

    Bench 11-12 (round 187, run_queue at c2a4fde5, both PASS):

      turn   40 / 44 / 42 / 44 (s5-s9; still's second hit at s10)   the hull faces the way it drives; no reversing
      rate   44 / 44 / 44 / 44 (s5-s12)                              already turned 0.15 s after the order: faster
                                                                     than 180 degrees in ~0.3 s, whatever 1.25 s means

    Model (sim.Sim.move): a body that moved this step faces its step's direction at once (INFERRED: instant; the
    true rate is only known to be above that).

      rev    vshort / vnorth / vback / vtwice: NEXT_MOVE_IS_REVERSE (a08's Mirage, s02's Tsunamis) set at the start, then
             sent as short / north, vback back to its spot and vtwice 60 further north 4 s later. Predicted from the data
             (CanReverseMove, ReverseMoveSpeed 75 %): 40 40 40 44 if one move reverses. Bench 11-22 (A307): 44 44 40 44 --
             each drove forward, as without the bit; pace (north plain / with the bit, 25-wide strips): the same strip
             every half second. The bit changes nothing a script move shows; pace's 'bit' (A310: UNIT_HAS_OBJECT_STATUS on
             vnorth / north) reads 0 throughout, before the move and after -- the model keeps no such bit.
    """
    from maps import probe_range
    from parts import Mission, Script, Test, status
    from benches.weapon.firing.checks import engine_missile
    missile = engine_missile()["shared"]
    LOST_MAX = missile.LOST_MAX
    TARGET_ID = missile.TARGET_ID
    target = missile.target
    from benches.weapon.target_effects.checks import engine_shot
    shot = engine_shot()["shared"]
    FLANK_DAMAGE = shot.FLANK_DAMAGE
    DAMAGE = shot.DAMAGE
    _nuggets = shot._nuggets
    shot_v4 = shot.shot_v4
    from checks import engine_scripts8 as s8

    SHOOTER = 'CNV_HullV4'
    HULL_AT, HULL_REACH = 300.0, 250.0          # the Hammer this far north of its spot, the V4 this far south of it
    MOVE = 4.0                                   # every clip is loaded by 6 s; the fire orders all come after it
    # pair: (lane gun pad, east offset of the pair on it, where the Hammer is sent from where it stands or None,
    # seconds from the move order to the fire order); four pairs a check (four counter lines fit)
    PAIRS = {
        'still': ('base', 0.0, None, 2.5), 'north': ('high', 0.0, (0.0, 600.0), 2.5),
        'east': ('removed', -300.0, (600.0, 0.0), 2.5), 'short': ('switch', 0.0, (0.0, 120.0), 2.5),
        'r15': ('order', -300.0, (0.0, 600.0), 0.15), 'r30': ('order', 300.0, (0.0, 600.0), 0.3),
        'r50': ('low', -300.0, (0.0, 600.0), 0.5), 'r80': ('low', 300.0, (0.0, 600.0), 0.8),
        'vshort': ('base', 300.0, (0.0, 120.0), 2.5), 'vnorth': ('high', 300.0, (0.0, 600.0), 2.5),
        'vback': ('switch', 300.0, (0.0, 120.0), 6.5), 'vtwice': ('removed', 300.0, (0.0, 120.0), 6.5),
    }
    # NEXT_MOVE_IS_REVERSE (a08, s02): these Hammers get the bit at the start; vback / vtwice are sent again this long
    # after the first move, back to where they stood / 60 further north (the bit used up by the first move, or not: the
    # V4 reaches 500, from 200); 'pace' fires nothing: the strip its Hammer is in
    REVERSED = {'vshort', 'vnorth', 'vback', 'vtwice'}
    AGAIN = {'vback': (4.0, (0.0, 0.0)), 'vtwice': (4.0, (0.0, 180.0))}
    GROUPS = {'turn': ('still', 'north', 'east', 'short'), 'rate': ('r15', 'r30', 'r50', 'r80'),
              'rev': ('vshort', 'vnorth', 'vback', 'vtwice'), 'pace': ('north', 'vnorth')}
    STRIP = 25.0                                 # pace: a counter step is this far north of where the Hammer stood


    def _n(pair, part):
        return f'UNIT - CNV Hull {pair.title()} {part}'


    def mission():
        units = [shot_v4(SHOOTER, _nuggets(DAMAGE.format(d=FLANK_DAMAGE, r=0, extra='')),
                         what=f'车体朝向 V4（探针）：{FLANK_DAMAGE:g} 伤害（EXPLOSIVE），无预瞄、无开火持续、无散布'),
                 target()]
        m = Mission(name='CampHull', map=probe_range, units=units, facts={})
        for pair, (lane, dx, _, _) in PAIRS.items():
            site = f'{lane} gun'
            m.put(SHOOTER, site, dx, HULL_AT - HULL_REACH, side='p1', role=f'{pair} shooter', name=_n(pair, 'Shooter'),
                  angle=1.5707963267948966)          # facing north, at its Hammer
            m.put(TARGET_ID, site, dx, HULL_AT, side='s1', role=f'{pair} target', name=_n(pair, 'Target'))
        return m


    def hull_test(m, group):
        t = Test()
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        start += [('UNIT_CHANGE_OBJECT_STATUS', _n(pair, part), 'NO_ATTACK', 1) for pair in PAIRS
                  for part in ('Shooter', 'Target')]
        start += [('UNIT_CHANGE_OBJECT_STATUS', _n(pair, 'Target'), 'NEXT_MOVE_IS_REVERSE', 1) for pair in REVERSED]
        start += [('SET_MILLISECOND_TIMER', 'Test Move', MOVE)]
        t.scripts.append(Script('Test - start', [], start))
        moves = []
        for pair in GROUPS[group]:
            lane, dx, go, fire = PAIRS[pair]
            if go is not None:
                x, y = m.site(f'{lane} gun')[:2]
                spot = f'Test Hull {pair.title()} Goal'
                t.waypoints[spot] = (x + dx + go[0], y + HULL_AT + go[1])
                moves.append(('MOVE_NAMED_UNIT_TO', _n(pair, 'Target'), spot))
            if pair in AGAIN:
                secs, go2 = AGAIN[pair]
                t.waypoints[spot + ' 2'] = (x + dx + go2[0], y + HULL_AT + go2[1])
                moves.append(('SET_MILLISECOND_TIMER', f'Test Again {pair.title()}', secs))
                t.scripts.append(Script(f'Test - again {pair}', [('TIMER_EXPIRED', f'Test Again {pair.title()}')],
                                        [('MOVE_NAMED_UNIT_TO', _n(pair, 'Target'), spot + ' 2')]))
            if group != 'pace':
                moves.append(('SET_MILLISECOND_TIMER', f'Test Fire {pair.title()}', fire))
        t.scripts.append(Script('Test - move', [('TIMER_EXPIRED', 'Test Move')], moves))
        if group == 'pace':
            for k, pair in enumerate(GROUPS[group]):
                lane, dx, _, _ = PAIRS[pair]
                x, y = m.site(f'{lane} gun')[:2]
                y += HULL_AT
                s8.total(t, f'CNV_Hull_P{k}', pair, [(j, ('NAMED_INSIDE_AREA', _n(pair, 'Target'), _strip(
                    t, f'Test Hull {pair.title()} {j}', x + dx, y + STRIP * j))) for j in range(1, 27)])
            # the bit as a script reads it (review ww P3 #5): 1 vnorth's (set), 2 north's (never set)
            s8.total(t, 'CNV_Hull_PBit', 'bit', [(k + 1, ('UNIT_HAS_OBJECT_STATUS', _n(p, 'Target'),
                                                         status('NEXT_MOVE_IS_REVERSE'))) for k, p in enumerate(('vnorth', 'north'))])
            s8.watch(t, MOVE + 10.0, 0.5)
            return t
        for k, pair in enumerate(GROUPS[group]):
            s, tg = _n(pair, 'Shooter'), _n(pair, 'Target')
            t.scripts.append(Script(f'Test - fire {pair}', [('TIMER_EXPIRED', f'Test Fire {pair.title()}')],
                                    [('UNIT_CHANGE_OBJECT_STATUS', s, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', s, tg)]))
            c = f'CNV_Hull_{group[0].upper()}{k}'
            t.counters.append((c, pair))
            t.scripts += [Script(f'Test - {c} lost {j}', [('UNIT_HEALTH', tg, 0, 100 - j + 1)],
                                 [('INCREMENT_COUNTER', 1, c)]) for j in range(1, LOST_MAX + 1)]
        run = MOVE + max(PAIRS[p][3] for p in GROUPS[group]) + 3.0     # the last fire order and its first hit
        t.expect = [(GROUPS[group][0], 0, 'ever>=', 1, run - 1)]
        t.bench = [('bench_watch', dict(seconds=run, every=1, sheet=False, lines=6))]
        return t


    def _strip(t, name, x, y):
        t.areas[name] = [(x - 100, y - STRIP / 2), (x + 100, y - STRIP / 2), (x + 100, y + STRIP / 2),
                         (x - 100, y + STRIP / 2)]
        return name


    MISSION = {'engine_hull': mission}
    CHECKS = {'engine_hull': {g: (lambda m, g=g: hull_test(m, g)) for g in GROUPS}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def jammer():
    """Jammer tests: the enemy mech is sent up the lane past the jammer at GO_AT; the map itself counts the seconds of
    its trip (one a second until it is in the goal area), so the reading does not depend on when frames were taken.

    jam: the jammer is switched on first -- the trip takes longer than free's.
    free (the control): the jammer stays off.
    """
    from parts import Script, Test, counted, square

    JAM_AT, GO_AT = 10.0, 12.0
    GOAL = 80.0
    FREE_TRIP = 5                                   # free's trip in seconds (bench 2026-10-22: the Tengu is quick)


    def trip(m, jam):
        t = Test()
        mech = m.role('mech').name
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('SET_MILLISECOND_TIMER', 'Test - jam timer', JAM_AT),
                                                     ('SET_MILLISECOND_TIMER', 'Test - go timer', GO_AT)]))
        if jam:
            t.scripts.append(Script('Test - jam', [('TIMER_EXPIRED', 'Test - jam timer')],
                                    [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role('jammer').name,
                                      m.ability('jammer', 'jam'))]))
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                                [('MOVE_NAMED_UNIT_TO', mech, m.mark('goal')),
                                 ('SET_MILLISECOND_TIMER', 'Test - tick timer', 1.0)]))
        t.areas['Test Goal'] = square(*m.point('goal'), GOAL)
        t.counters.append(('Test Trip', '行程秒数'))
        t.scripts.append(Script('Test - tick', [('TIMER_EXPIRED', 'Test - tick timer'),
                                                ('NAMED_OUTSIDE_AREA', mech, 'Test Goal')],
                                [('INCREMENT_COUNTER', 1, 'Test Trip'),
                                 ('SET_MILLISECOND_TIMER', 'Test - tick timer', 1.0)], once=False))
        counted('Test There', '到达', t, named=mech, area='Test Goal')
        counted('Test Jammer Health', '干扰车血量', t, health=m.role('jammer').name)
        t.expect += [('到达', GO_AT, 'ever==', 1)]
        t.bench = [('bench_watch', dict(seconds=90, every=3, sheet=False, lines=len(t.counters), until='c2==1'))]
        return t


    def jam(m):
        t = trip(m, True)
        if FREE_TRIP:
            # 458 of the 750 at 40 %: about 4.5 s more
            t.expect.append(('行程秒数', GO_AT, 'ever>=', FREE_TRIP + 3))
        return t


    def free(m):
        return trip(m, False)


    def jam_air(m):
        """The jammer against a flier (J7 card A: do air units fly past it?). Only the reading: no trip-time expectation,
        the verdict is this run's 行程秒数 against the same flier's free run."""
        return trip(m, True)


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'jammer': {'jam': jam, 'free': free},
        'jammer_own': {'jam': jam},
        'jammer_air': {'jam': jam_air, 'free': free},
        'jammer_jet': {'jam': jam_air, 'free': free},
        'jammer_kirov': {'jam': jam_air, 'free': free},
    }
    return dict(CHECKS=CHECKS)


def engine_jet():
    """JetAIUpdate minimum ordinary-move probe, engine line E.

    Retail Vindicator (AlliedAntiGroundAircraft), NORMAL speed 180, Wings locomotor,
    AccelerationSeconds 1, MinSpeed 160%, CirclingRadius 60, CirclingSpeed 50%; JetAIUpdate has
    NeedsRunway=false. No airfield, enemy, attack or ammo expenditure is involved.
    JetAIUpdate dispatches the order; speed/turning/idle circles belong to locomotion,
    JetSlowDeathBehavior to death. This check cannot establish those whole modules.

    From festival's west field, fly 1200 east at Go=1s, into a square half-side 100.
    Prediction: survive at 100% and reach the square. Constant-speed reference
    (1200-100)/180*15 = 91.67 frames; takeoff/acceleration/turning are unmeasured,
    so the exact first-entry frame is a measurement, not a predeclared speed fit.
    Four rows: frames since Go until FIRST entry (latched), first-entry flag,
    current presence in the goal square, health percent. Presence may change again
    while circling: reaching is deliberately latched separately from staying.

    Bench 2026-11-11, CampJetA_mcp_1111_050503: PASS; s1-s5 flight counter
    30/42/57/72/88, then s6-s26 97/1/1/100. First-entry counter=97;
    thereafter inside=1 and health=100 throughout the observed run. Do not derive
    an absolute order-to-arrival time from screenshot seconds (their clock differs).
    E53 model: 97/1/1/100; endpoint, survival and exact counter replay pass
    in tests/test_simjet.py. No claim about circling trajectory or whole module.

    600-distance control b, CampJetB_mcp_1111_053444: s1=29/0/0/100,
    s2=42/0/0/100, s3-s26=47/1/1/100. Engine distance delta 600 takes
    50 frames, consistent with speed 180. Ideal constant-speed entry references
    are 91.67 and 41.67; both measured counts exceed those by 5.33 frames.
    The later D43 position probe separates horizontal acceleration from takeoff
    and circling; E53 models the measured startup instead of fitting either endpoint.

    E53/D43: Go frame 16 moves 2.7 horizontally (mechanism INFERRED), then +0.8
    per frame to 12 at frame 28. The first 12 steps cover 85.2 instead of 144.
    Frame-based Jet movement under either global clock now replays a/b 97/47,
    including entry frames 112/62 and the shared startup positions. No third distance
    bench was run. Only the original Vindicator's first stationary eastbound plain
    move is enabled; modified configurations, turns and repeated orders report gaps.
    """
    from maps import festival
    from parts import Mission, Script, Test, counted, square

    JET = JET_TEMPLATE


    NAME = 'UNIT - CNV Jet'
    RUN = 25.0


    def mission():
        m = Mission(name='CampJet', map=festival, units=[], facts={})
        m.put(JET, 'west field', -600.0, 0.0, angle=0.0, role='jet', name=NAME)
        return m


    def ordinary_move(m, goal_dx=600.0, measured_frames=97):
        t = Test()
        jet = m.role('jet').name
        x, y = m.site('west field')[:2]
        t.waypoints['Jet Goal'] = (x + goal_dx, y)
        t.areas['Jet Goal'] = square(x + goal_dx, y, 100.0)
        t.scripts.append(Script('Jet - start', [], [
            ('MAP_REVEAL_ALL_PERM', m.player('p1')),
            ('UNIT_CHANGE_OBJECT_STATUS', jet, 'NO_ATTACK', 1),
            ('SET_MILLISECOND_TIMER', 'Jet Go', 1.0),
            ('SET_FLAG', 'Jet Arrived', 0),
        ]))
        t.scripts.append(Script('Jet - move', [('TIMER_EXPIRED', 'Jet Go')],
                                m.order('move', [jet], 'Jet Goal', 'p1', crew='Jet')
                                + [('SET_FLAG', 'Jet Going', 1)]))
        t.counters += [('CNV_Jet_Frames', '飞帧'), ('CNV_Jet_Arrived', '到达')]
        t.scripts.append(Script('Jet - first entry', [
            ('FLAG', 'Jet Going', 1), ('NAMED_INSIDE_AREA', jet, 'Jet Goal'),
        ], [('SET_FLAG', 'Jet Arrived', 1), ('SET_COUNTER', 'CNV_Jet_Arrived', 1)]))
        t.scripts.append(Script('Jet - flight frames', [
            ('FLAG', 'Jet Going', 1), ('FLAG', 'Jet Arrived', 0),
        ], [('INCREMENT_COUNTER', 1, 'CNV_Jet_Frames')], once=False))
        counted('CNV_Jet_Inside', '在场', t, named=jet, area='Jet Goal')
        counted('CNV_Jet_Health', '机血', t, health=jet)
        t.expect = [('到达', 0, 'ever==', 1, RUN), ('机血', 2, '==', 100, RUN),
                    ('在场', 10, '==', 1, RUN)]
        t.expect.append(('飞帧', 10, '==', measured_frames, RUN))
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=4))]
        return t


    def short_move(m):
        """600 distance control: same start/order/heading/goal size as a; bench counter 47."""
        return ordinary_move(m, goal_dx=0.0, measured_frames=47)


    MISSION = {'engine_jet': mission}
    CHECKS = {'engine_jet': {'a': ordinary_move, 'b': short_move}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_jet_probe():
    """Engine line D, round 43 (ADR 0027/0028): E line's JetAIUpdate move (engine_jet) with ra3ext's read-only probe.

    benches/movement/pathing/checks.py#engine_jet (E line's check, not changed here) flies a retail Vindicator 1200 (a) or 600 (b) east at Go = 1 s and
    counts frames from Go to the first entry into the goal square: bench 97 / 47 against a constant-speed 91.67 / 41.67.
    This mission is the same one with one change: the jet is a copy CNV_JetProbe with one more module,
    `<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames=EVERY MaxFrames=LINES/>`, built with ext=True. ra3ext's CNVProbe
    logs a `probe` line on every frame the host's x / y / z changed (and every EVERY frames), with the game frame number:
    that is the jet's trajectory from spawn through Go to after arrival, and the per-frame step is its actual speed.
    The probe only reads, so E line's expectations are kept: the counters must equal E line's readings.

    Bench 2026-11-11 (D round 43): a PASS 97, b PASS 47 (CampJPA_mcp_1111_082745, CampJPB_mcp_1111_083208). Spawn:
    xy still, z +20 a frame (TakeOffAndLandingSpeed) to frame 8, then halving towards ~386.6; no circling. Go at
    script frame 16, the jet moves that same frame: step 2.7, then +0.8 a frame (12 / 15 = max speed per frame over
    AccelerationSeconds 1 s) to 12.0 at frame 28, straight east. The accelerating 12 frames cover 85.2 instead of 144:
    4.9 frames, E line's 5-frame gap. First entry frame 112 (a) / 62 (b), counter = entry - Go + 1.
    """
    import os

    import labpaths
    from parts import Unit
    jet = engine_jet()

    JET, PROBE = JET_TEMPLATE, 'CNV_JetProbe'
    EVERY, LINES = 150, 3000


    def probe_jet():
        with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', JET + '.xml'), encoding='utf-8') as f:
            x = f.read()
        assert x.count(f'id="{JET}"') == 1 and x.count('<Behaviors>') == 1
        x = x.replace(f'id="{JET}"', f'id="{PROBE}"', 1).replace(f'EditorName="{JET}"', f'EditorName="{PROBE}"')
        x = x.replace('<Behaviors>', (f'<Behaviors>\n'
            f'\t\t\t<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>'), 1)
        return Unit(PROBE, x, names=dict(unit=PROBE),
                    what='原版 Vindicator 的复制（探针）：多一个 ra3ext 的 CNVProbe 模块，逐帧记位置',
                    params=dict(of=JET, every=EVERY, lines=LINES))


    def mission():
        m = jet['MISSION']['engine_jet']()
        m.name, m.ext = 'CampJP', True     # + the check's name stays <= 15 (CampJPA, CampJPB)
        m.units.append(probe_jet())
        for o in m.objects:
            if o.template == JET:
                o.template = PROBE
        for r in m.cast.values():
            if r.template == JET:
                r.template = PROBE
        return m


    MISSION = {'engine_jet_probe': mission}
    base_checks = jet['CHECKS']['engine_jet']
    CHECKS = {'engine_jet_probe': {'a': base_checks['a'], 'b': base_checks['b']}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_land():
    """Engine probe: the way an amphibious transport takes to a shore point behind a quay (engine_land in scenes.py; R7 of
    docs/story/sim-vs-bench-a4.md).

    At ORDER s a script makes the transport at the sea point and sends it to the shore point as A4's horn does (a team
    move, m.order). Four boxes, each a counter: frames from the order until the transport first stands in it (it
    stops counting then; never in it: the counter runs on to the end):
      岸   A4's shore area (200 square round the shore point, its sea edge 100 out on the water)
      码头  in front of the quay, on the water (4300, 2900)
      南水  the sea south, on the simulator's way round (4280, 3500)
      南岸  the land south-west, the simulator's way ashore (3800, 3600)
    """
    from parts import Script, Test, square

    RUN, ORDER = 45.0, 2.0
    BOXES = {'岸': ((4120.0, 2900.0), 100.0), '码头': ((4300.0, 2900.0), 80.0), '南水': ((4280.0, 3500.0), 100.0),
             '南岸': ((3800.0, 3600.0), 100.0)}


    def way(m):
        t = Test()
        p1, boat = m.player('p1'), 'UNIT - CNV Land Boat'
        t.scripts += [Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', ORDER)]),
                      Script('Test - go', [('TIMER_EXPIRED', 'Test Go')],
                             [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', boat, 'JapanLightTransportVehicle', m.team('s1'),
                               m.mark('sea'))] + m.order('move', [boat], m.mark('shore'), 's1') +
                             [('SET_FLAG', 'Test Going', 1)])]
        for k, (label, (p, r)) in enumerate(BOXES.items()):
            area, counter, seen = f'Test Land {k}', f'CNV_Land_{k}', f'Test Land Seen {k}'
            t.areas[area] = square(*p, r)
            t.counters.append((counter, label))
            t.scripts += [Script(f'Test - land seen {k}', [('FLAG', 'Test Going', 1), ('NAMED_INSIDE_AREA', boat, area)],
                                 [('SET_FLAG', seen, 1)]),
                          Script(f'Test - land count {k}', [('FLAG', 'Test Going', 1), ('FLAG', seen, 0)],
                                 [('INCREMENT_COUNTER', 1, counter)], once=False)]
        t.expect += [('岸', RUN - 2, 'ever>=', 1)]              # it ran (the readings are the result)
        t.bench = [('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {'engine_land': {'way': way}}
    return dict(CHECKS=CHECKS)


def lock():
    """Lock gate tests (lock in scenes.py): the ship is sent to the goal past the gate at GO_AT, again every few
    seconds. Bench 2026-10-27: a structure the map places on the water does not bar a ship (it sailed through the gate
    in 12 s) -- so the lock holds its fleet by status (IMMOBILE, as the armoured train's brake), the gate is the look.

    shut: the ship is held the whole run -- it never gets there.
    open: held, then let go (and the gate deleted) at OPEN_AT -- not there before, there after.
    """
    from parts import Script, Test, counted, square

    GO_AT, OPEN_AT, RUN = 5.0, 30.0, 75.0
    GOAL = 120.0


    def trip(m, open_at=None):
        t = Test()
        ship = m.role('ship').name
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('UNIT_CHANGE_OBJECT_STATUS', ship, 'IMMOBILE', 1),
                                                     ('SET_MILLISECOND_TIMER', 'Test - go timer', GO_AT)]))
        # sent again every few seconds: a ship refused a path may give the order up
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                                [('MOVE_NAMED_UNIT_TO', ship, m.mark('goal')),
                                 ('SET_MILLISECOND_TIMER', 'Test - go timer', 4.0)], once=False))
        if open_at is not None:
            t.scripts += [Script('Test - open timer', [], [('SET_MILLISECOND_TIMER', 'Test - open timer', open_at)]),
                          Script('Test - open', [('TIMER_EXPIRED', 'Test - open timer')],
                                 [('UNIT_CHANGE_OBJECT_STATUS', ship, 'IMMOBILE', 0),
                                  ('NAMED_DELETE', m.role('gate').name)])]
        t.areas['Test Goal'] = square(*m.point('goal'), GOAL)
        counted('Test There', '船到了', t, named=ship, area='Test Goal')
        counted('Test Ship Health', '船血量', t, health=ship)
        return t


    def shut(m):
        t = trip(m)
        t.expect += [('船到了', 1, '==', 0, RUN)]
        t.bench = [('bench_camera', dict(x=m.point('goal')[0], y=m.point('goal')[1] - 250, look=False)),
                   ('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=len(t.counters)))]
        return t


    def opened(m):
        t = trip(m, OPEN_AT)
        t.expect += [('船到了', 1, '==', 0, OPEN_AT), ('船到了', OPEN_AT, 'ever==', 1, RUN)]
        t.bench = [('bench_camera', dict(x=m.point('goal')[0], y=m.point('goal')[1] - 250, look=False)),
                   ('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=len(t.counters), until='c1==1'))]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'lock': {'shut': shut, 'open': opened},
    }
    return dict(CHECKS=CHECKS)


def engine_pace():
    """Engine unit tests: can a scripted group move at its slowest member's pace (docs/engine/pathing.md 5; user
    2026-11-04 "成群移动按最低速度前进在技术上可行吗？"). engine_paths group showed a whole-team move does not wait: an IFV
    (speed 120) at s7, an engineer (40) at s25. On the probe map's pace lanes (maps/probe_range.py: open ground, 1 500
    west to east, leg points at 500 and 1 000), an IFV and an engineer each:

      pace   the IFV is our copy with an upgrade whose SPEED modifier is 33% (120 -> 40), granted at s0; one team move
      legs   retail IFV; the pair is moved leg by leg: on to the next leg point only when both stand inside this one
      guard  retail IFV on a team of its own told to guard the engineer (TEAM_GUARD_OBJECT); the engineer alone is moved

    Counters (every frame): 1 the IFV at the goal, 10 the engineer at the goal; and per lane 100 while the IFV is more
    than 300 ahead of the engineer -- read as: the IFV inside the goal's or the second leg's strip while the engineer is
    still west of the first leg's (approximately: strips 300 wide across the lane).

    Read (测, 2026-11-04, docs/engine/pathing.md 5): pace 11 at s33 (both at once, never ahead); legs 1 from s25, 11 at
    s33 (the IFV waits at each leg point, 8 s early on the last leg); guard 10 at s33 (the IFV never reached the goal).

    engine_guard:go -- TEAM_GUARD_OBJECT(team, object) (retail a05: two boat crews guard a rescue boat). On the same lanes a
    retail IFV on a team of its own guards a retail engineer, both the player's; the guard order at 1 s:
      静 (pace lane)   the engineer stands 1 000 east of the IFV
      走 (legs lane)   both at the start, as guard above; the engineer alone is moved to the goal (1 500 east) at 2 s
      近 (guard lane)  the engineer stands 300 east of the IFV
    Counters (every frame): each IFV's and the moving engineer's (工) 100-wide strip along its lane, k = round((x - 300) /
    100) (the start x 500 = 2, the goal 2 000 = 17; 0 off the lane).
    """
    import os

    import labpaths
    from maps import probe_range
    from parts import Mission, Script, Test, Unit, square
    from checks import engine_scripts8 as s8

    IFV = 'AlliedAntiAirVehicleTech1'
    ENGINEER = 'AlliedEngineer'
    PACED = 'CNV_PacedIfv'
    PACE = 0.33                                     # the engineer's 40 over the IFV's 120
    RUN = 60.0
    LABEL = {'pace': '限速', 'legs': '分段', 'guard': '护卫'}


    def paced_ifv(id=PACED, speed=PACE):
        """Retail's IFV under our id with one OBJECT upgrade whose attribute modifier sets SPEED to `speed` of its own."""
        up, mod = f'Upgrade_{id}_Pace', f'AttributeModifier_{id}_Pace'
        x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', f'{IFV}.xml'), encoding='utf-8').read()
        for old, new in ((f'id="{IFV}"', f'id="{id}"'), (f'EditorName="{IFV}"', f'EditorName="{id}"'),
                         ('<Behaviors>', (f'<Behaviors>\n'
                             f'\t\t\t<AttributeModifierUpgrade id="ModuleTag_CNV_Pace" AttributeModifier="{mod}">\n'
                             f'\t\t\t\t<TriggeredBy>{up}</TriggeredBy>\n'
                             f'\t\t\t</AttributeModifierUpgrade>')),
                         ('</AssetDeclaration>', (f'\t<UpgradeTemplate id="{up}" Type="OBJECT"/>\n'
                             f'\t<AttributeModifier id="{mod}" Category="NONE">\n'
                             f'\t\t<Modifier Type="SPEED" Value="{round(speed * 100)}%"/>\n'
                             f'\t</AttributeModifier>\n'
                             f'</AssetDeclaration>'))):
            assert x.count(old) == 1, (old[:40], x.count(old))
            x = x.replace(old, new, 1)
        return Unit(id, x, link=[f'UpgradeTemplate:{up}', f'AttributeModifier:{mod}'], names={'pace': up},
                    what=f'探针：原版多功能步兵车，升级后速度 x{speed:g}', params=dict(speed=speed))


    def _key(s):
        return s.title().replace(' ', '')


    def mission():
        m = Mission(name='CampPace', map=probe_range, units=[paced_ifv()], facts={})
        for lane in probe_range.PACE:
            m.put(PACED if lane == 'pace' else IFV, f'{lane} start', 0, 40.0, role=f'{lane} ifv',
                  name=f'UNIT - CNV Pace {_key(lane)} Ifv')
            m.put(ENGINEER, f'{lane} start', 0, -40.0, role=f'{lane} engineer', name=f'UNIT - CNV Pace {_key(lane)} Engineer')
        return m


    def pace(m):
        t = Test()
        ifv = {lane: m.role(f'{lane} ifv').name for lane in probe_range.PACE}
        eng = {lane: m.role(f'{lane} engineer').name for lane in probe_range.PACE}

        def wp(lane, where):
            n = f'Test Pace {_key(lane)} {_key(where)}'
            t.waypoints[n] = m.site(f'{lane} {where}')
            return n

        def area(lane, where, half=100.0):
            n = f'Test Pace {_key(lane)} {_key(where)} Area'
            t.areas[n] = square(*m.site(f'{lane} {where}'), half)
            return n

        paced = next(u for u in m.units if u.id == PACED).names['pace']
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('NAMED_RECEIVE_UPGRADE', paced, ifv['pace'])]
        start += m.order('move', [ifv['pace'], eng['pace']], wp('pace', 'goal'), crew='PacePace')
        start += m.order('move', [ifv['legs'], eng['legs']], wp('legs', 'leg 1'), crew='PaceLegs')
        guards = m.crew('PaceGuardIfv')
        start += [('UNIT_SET_TEAM', ifv['guard'], guards), ('TEAM_GUARD_OBJECT', guards, eng['guard'])]
        start += m.order('move', [eng['guard']], wp('guard', 'goal'), crew='PaceGuardEng')
        t.scripts.append(Script('Test - go', [], start))
        for k, nxt in ((1, 'leg 2'), (2, 'goal')):
            here = area('legs', f'leg {k}', 120.0)
            t.scripts.append(Script(f'Test - legs {k} gathered',
                                    [('NAMED_INSIDE_AREA', ifv['legs'], here), ('NAMED_INSIDE_AREA', eng['legs'], here)],
                                    m.order('move', [ifv['legs'], eng['legs']], wp('legs', nxt), crew='PaceLegs')))
        for lane in probe_range.PACE:
            counter = f'CNV_Pace_{_key(lane)}'
            t.counters.append((counter, LABEL[lane]))
            goal = area(lane, 'goal', 120.0)
            # strips: the IFV east of the second leg point - 150, the engineer west of the first + 150 -> > 300 apart
            lx, ly = m.site(f'{lane} leg 2')
            fx, _ = m.site(f'{lane} leg 1')
            far, back = f'Test Pace {_key(lane)} Far', f'Test Pace {_key(lane)} Back'
            t.areas[far] = [(lx - 150, ly - 200), (lx + 800, ly - 200), (lx + 800, ly + 200), (lx - 150, ly + 200)]
            t.areas[back] = [(fx - 800, ly - 200), (fx - 350, ly - 200), (fx - 350, ly + 200), (fx - 800, ly + 200)]
            t.scripts += [Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False),
                          Script(f'Test - {counter} ifv', [('NAMED_INSIDE_AREA', ifv[lane], goal)],
                                 [('INCREMENT_COUNTER', 1, counter)], once=False),
                          Script(f'Test - {counter} engineer', [('NAMED_INSIDE_AREA', eng[lane], goal)],
                                 [('INCREMENT_COUNTER', 10, counter)], once=False),
                          Script(f'Test - {counter} ahead', [('NAMED_INSIDE_AREA', ifv[lane], far),
                                                             ('NAMED_INSIDE_AREA', eng[lane], back)],
                                 [('INCREMENT_COUNTER', 100, counter)], once=False)]
        t.expect = []
        t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=3))]
        return t


    GUARD = {'pace': ('静', 1000.0), 'legs': ('走', 0.0), 'guard': ('近', 300.0)}   # lane: label, the engineer's x off


    def guard_mission():
        m = Mission(name='CampGuard', map=probe_range, units=[], facts={})
        for lane, (_, dx) in GUARD.items():
            m.put(IFV, f'{lane} start', 0, 40.0, role=f'{lane} ifv', name=f'UNIT - CNV Guard {_key(lane)} Ifv')
            m.put(ENGINEER, f'{lane} start', dx, -40.0, role=f'{lane} eng', name=f'UNIT - CNV Guard {_key(lane)} Eng')
        m.waypoint('goal', 'Test Guard Goal', 'legs goal')
        return m


    def guard(m):
        t = Test()
        ifv = {lane: m.role(f'{lane} ifv').name for lane in GUARD}
        eng = {lane: m.role(f'{lane} eng').name for lane in GUARD}
        orders = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for lane in GUARD:
            crew = m.crew(f'Guard{_key(lane)}')
            orders += [('UNIT_SET_TEAM', ifv[lane], crew), ('TEAM_GUARD_OBJECT', crew, eng[lane])]
        s8.at(t, 'guard', 1.0, orders)
        s8.at(t, 'walk', 2.0, m.order('move', [eng['legs']], m.mark('goal'), crew='GuardWalk'))
        for lane, (label, _) in GUARD.items():
            y = m.site(f'{lane} start')[1]
            strip = {k: f'Test Guard {_key(lane)} {k}' for k in range(1, 20)}
            for k, n in strip.items():
                t.areas[n] = [(250 + 100 * k, y - 200), (350 + 100 * k, y - 200), (350 + 100 * k, y + 200),
                              (250 + 100 * k, y + 200)]
            for who, lab, tag in [(ifv[lane], label, 'Ifv')] + ([(eng[lane], '工', 'Eng')] if lane == 'legs' else []):
                s8.total(t, f'CNV_Guard_{_key(lane)}_{tag}', lab,
                         [(k, ('NAMED_INSIDE_AREA', who, n)) for k, n in strip.items()])
        s8.watch(t, 45.0, 1.0)
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_pace': mission, 'engine_guard': guard_mission}
    CHECKS = {'engine_pace': {'pace': pace}, 'engine_guard': {'go': guard}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_pace_placed():
    """出动 + 齐步 on the bench (engine_pace_placed in scenes.py, docs/engine/pathing.md 5b): the harbour's two tanks and two
    warriors sent off at SEND to the west field, with (`paceplaced`) and without (`paceplacedn`) 齐步.

    go: counters (every frame) -- how many of the tanks stand in the goal (a square of GOAL round the west field), how
      many of the warriors, and how many enemy units hold the pace upgrade (0 in paceplacedn). Read, not judged: with
      齐步 the tanks come in with the warriors (and the upgrade count drops to 0 once one is inside the west field's
      area); without, the tanks well ahead.

    Read (bench 11-12, bench seconds):
      paceplaced CampPacePlGo_mcp_1112_124725: 限速 2 s33-s84 (granted as sent, held by both tanks), 0 from s88; 坦克 1 at
        s88, 2 at s90; 武士 1 at s90, 2 at s93 -- together, the last warrior 5 s after the first tank.
        The simulator: 81 / 82 / 83 (bench s runs a few seconds ahead of the mission clock).
      paceplacedn CampPacePlNGo_mcp_1112_125222: 坦克 2 from s74 (0 at s71); 武士 1 at s91, 2 at s93 -- the tanks 17-19 s
        ahead. The simulator: tanks 65 / 66, warriors 82 / 83 (17 s). (A first run, CampPacePlNGo_mcp_1112_124000, read 0
        0 0 to s220: its start lost the popup connection at 38 s; the four stood short of the goal. Not a reading.)
    """
    from parts import Script, Test, counted, square

    GOAL = 250.0
    RUN = 150.0


    def go(m):
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.areas['Test PP goal'] = square(*m.site('west field'), GOAL)
        s1 = m.player('s1')
        counted('Test PP tank', '坦克', t, template=m.cast['tank 1'].template, player=s1, area='Test PP goal', most=3)
        counted('Test PP foot', '武士', t, template=m.cast['foot 1'].template, player=s1, area='Test PP goal', most=3)
        up = next((u.names['pace'] for u in m.units if u.id.startswith('CNV_Pace')), None)
        t.counters.append(('Test PP up', '限速'))
        t.scripts.append(Script('Test - pp up zero', [], [('SET_COUNTER', 'Test PP up', 0)], once=False))
        if up:
            t.scripts += [Script(f'Test - pp up {n}', [('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', s1, n, up)],
                                 [('SET_COUNTER', 'Test PP up', n)], once=False) for n in (1, 2)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=3))]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {'paceplaced': {'go': go}, 'paceplacedn': {'go': go}}

    # bench seconds the counters first read (坦克 / 武士) 1 and 2, and the span the upgrade was held
    return dict(CHECKS=CHECKS)


def engine_paths():
    """Engine unit tests: how the game finds a way for units a script orders (docs/engine/pathing.md; engine line
    round 10, ADR 0017). On the probe map (maps/probe_paths.py) every order is a whole-team order (Mission.order, as the
    missions give them).

    detour: an IFV each in the far / mid / near boxes, ordered to the goal on the other side of a wall whose only gap
      is about 8 200 / 3 400 / 1 100 of way round (600 straight); a tank ordered into the closed ring 'shut'. Counters:
      1 by the gap (it went the way round), 10 at the goal; shut: 1 outside the ring on its own side, 10 still at the
      start, 100 outside the ring's far side.
    group: 'team' -- an IFV (fast) and an engineer (slow) ordered as one team (move); 'attack team' the same pair by
      attack-move: 1 the IFV at the goal, 10 the engineer (does the fast one wait?). 'narrow' / 'wide': six tanks as one
      team through a gap 50 / 150 across: how many at the goal.
    stuck / alive / where: detour's far and mid IFVs read again -- at the start, under the goal, by the gap; alive and
      in which half; then by strips.

    Read (测, 2026-11-04, runs CampPaths*_mcp_1104_*; docs/engine/pathing.md): near got there by s9; far and mid, alive,
    never reached their gap -- they drove a few hundred east and stopped south of the wall (x 700..1500); shut stopped
    outside the ring on its own side; team / attack team: the IFV at s7, the engineer at s25 (nobody waits); narrow 3 at
    s9 and 6 at s11, wide 6 at s9. limit: 1 400 there by s10, 1 800 and 2 600 never at their gap in 90 s.
    """
    from maps import probe_paths
    from parts import Mission, Script, Test, counted, square

    IFV = 'AlliedAntiAirVehicleTech1'
    TANK = 'AlliedAntiVehicleVehicleTech1'
    ENGINEER = 'AlliedEngineer'
    CHOKE = 6
    LABEL = {'far': '远绕', 'mid': '中绕', 'near': '近绕', 'shut': '围死', 'team': '同队移动', 'attack team': '同队攻移',
             'narrow': '窄口', 'wide': '宽口', 'd1400': '绕1400', 'd1800': '绕1800', 'd2600': '绕2600',
             'sq ifv': '挤口车', 'sq tank': '挤口守', 'sq apoc': '挤口天'}
    SQUEEZE = {'sq ifv': IFV, 'sq tank': TANK, 'sq apoc': 'SovietAntiVehicleVehicleTech3'}    # radius 14 / 23.3 / 30.8
    LIMIT = ('near', 'd1400', 'd1800')   # limit: the way round about 1 100 (control) / 1 400 / 1 800 (2 600: the first run, no)


    def _key(s):
        return s.title().replace(' ', '')


    def mission():
        m = Mission(name='CampPaths', map=probe_paths, facts={})
        for lane in ('far', 'mid', 'near', 'd1400', 'd1800', 'd2600'):
            m.put(IFV, f'{lane} start', role=f'{lane} ifv', name=f'UNIT - CNV Paths {_key(lane)} Ifv')
        m.put(TANK, 'shut start', role='shut tank', name='UNIT - CNV Paths Shut Tank')
        for lane in ('team', 'attack team'):
            m.put(IFV, f'{lane} start', -40.0, 0, role=f'{lane} ifv', name=f'UNIT - CNV Paths {_key(lane)} Ifv')
            m.put(ENGINEER, f'{lane} start', 40.0, 0, role=f'{lane} engineer',
                  name=f'UNIT - CNV Paths {_key(lane)} Engineer')
        for lane in ('narrow', 'wide'):
            for k in range(CHOKE):
                m.put(TANK, f'{lane} start', -125.0 + 50.0 * k, 0, role=f'{lane} tank {k + 1}',
                      name=f'UNIT - CNV Paths {_key(lane)} Tank {k + 1}')
        for lane, tpl in SQUEEZE.items():
            m.put(tpl, f'{lane} start', role=f'{lane} unit', name=f'UNIT - CNV Paths {_key(lane)} Unit', angle=90.0)
        return m


    def _go(m, t, lane, parts, kind='move'):
        wp = f'Test Paths {_key(lane)} Goal'
        t.waypoints[wp] = m.site(f'{lane} goal')
        return m.order(kind, [m.role(p).name for p in parts], wp, crew=f'Paths{_key(lane)}')


    def _scored(t, lane, worth):
        """A counter for `lane`: 0 every frame, then each (named, area, worth) adds `worth` while that unit is inside."""
        counter = f'CNV_Paths_{_key(lane)}'
        t.counters.append((counter, LABEL[lane]))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        for k, (name, area, n) in enumerate(worth):
            t.scripts.append(Script(f'Test - {counter} {k}', [('NAMED_INSIDE_AREA', name, area)],
                                    [('INCREMENT_COUNTER', n, counter)], once=False))


    def _area(m, t, site, half):
        name = f'Test Paths {_key(site)}'
        t.areas[name] = square(*m.site(site), half)
        return name


    def detour(m):
        t = Test()
        order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for lane in ('far', 'mid', 'near'):
            order += _go(m, t, lane, [f'{lane} ifv'])
            ifv = m.role(f'{lane} ifv').name
            _scored(t, lane, [(ifv, _area(m, t, f'{lane} gap', 140.0), 1), (ifv, _area(m, t, f'{lane} goal', 100.0), 10)])
        order += _go(m, t, 'shut', ['shut tank'])
        tank = m.role('shut tank').name
        _scored(t, 'shut', [(tank, _area(m, t, 'shut near', 60.0), 1), (tank, _area(m, t, 'shut start', 60.0), 10),
                            (tank, _area(m, t, 'shut far', 60.0), 100)])
        t.scripts.insert(0, Script('Test - go', [], order))
        t.bench = [('bench_watch', dict(seconds=200, every=4, sheet=False, lines=4))]
        t.expect = [('近绕', 0, 'ever==', 10, 200)]          # the near one gets there: the rest are read, not judged
        return t


    def limit(m, lanes=LIMIT):
        """Between near (gets there) and mid (stops): IFVs whose way round is about 1 400 / 1 800, near as the control.
        Counters as detour's: 1 by the gap, 10 at the goal."""
        t = Test()
        order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for lane in lanes:
            order += _go(m, t, lane, [f'{lane} ifv'])
            ifv = m.role(f'{lane} ifv').name
            _scored(t, lane, [(ifv, _area(m, t, f'{lane} gap', 140.0), 1), (ifv, _area(m, t, f'{lane} goal', 100.0), 10)])
        t.scripts.insert(0, Script('Test - go', [], order))
        t.bench = [('bench_watch', dict(seconds=90, every=3, sheet=False, lines=3))]
        t.expect = [('近绕', 0, 'ever==', 10, 90)]
        return t


    def stuck(m):
        """detour's three IFVs again, read for where they stop: 1 still at the start, 10 against the wall right under
        the goal (the nearest point to it), 100 by the gap; every second."""
        t = Test()
        order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for lane in ('far', 'mid', 'near'):
            order += _go(m, t, lane, [f'{lane} ifv'])
            ifv = m.role(f'{lane} ifv').name
            gx, _ = m.site(f'{lane} goal')
            wy = probe_paths.BOXES[lane][1]
            under = f'Test Paths {_key(lane)} Under'
            t.areas[under] = square(gx, wy - 70.0, 70.0)
            _scored(t, lane, [(ifv, _area(m, t, f'{lane} start', 60.0), 1), (ifv, under, 10),
                              (ifv, _area(m, t, f'{lane} gap', 140.0), 100)])
        t.scripts.insert(0, Script('Test - go', [], order))
        t.bench = [('bench_watch', dict(seconds=60, every=1, sheet=False, lines=3))]
        t.expect = [('近绕', 0, 'ever==', 100, 60)]
        return t


    def alive(m):
        """Are the far and mid IFVs there at all (health), and in which half of the far box (south / north of the wall)."""
        t = stuck(m)
        t.counters.clear()
        t.scripts = [s for s in t.scripts if not s.name.startswith('Test - CNV_Paths')]
        for lane in ('far', 'mid'):
            counted(f'Test Paths {_key(lane)} Hp', f'{LABEL[lane]}血量', t, health=m.role(f'{lane} ifv').name)
        (x0, y0, x1, y1), wy, _ = probe_paths.BOXES['far']
        ifv = m.role('far ifv').name
        for half, (a, b) in (('south', (y0, wy)), ('north', (wy, y1))):
            t.areas[f'Test Paths Far {half}'] = [(x0, a), (x1, a), (x1, b), (x0, b)]
            counted(f'Test Paths Far {half.title()}', f'远绕{"南" if half == "south" else "北"}', t, named=ifv,
                    area=f'Test Paths Far {half}')
        t.bench = [('bench_watch', dict(seconds=30, every=2, sheet=False, lines=4))]
        t.expect = []
        return t


    BANDS_X = ((300.0, 700.0), (700.0, 1500.0), (1500.0, 3000.0), (3000.0, 4700.0))   # 1 / 10 / 100 / 1000
    BANDS_Y = 4                         # south of the wall in 4 strips from the fence up to the wall: 1 / 10 / 100 / 1000


    def where(m):
        """Where the far and mid IFVs stop south of the wall: an x counter and a y counter each (the strip's worth)."""
        t = Test()
        order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for lane in ('far', 'mid'):
            order += _go(m, t, lane, [f'{lane} ifv'])
            ifv = m.role(f'{lane} ifv').name
            (x0, y0, x1, _), wy, _ = probe_paths.BOXES[lane]
            xs, ys = [], []
            for k, (a, b) in enumerate(BANDS_X):
                n = f'Test Paths {_key(lane)} X{k}'
                t.areas[n] = [(a, y0), (b, y0), (b, wy), (a, wy)]
                xs.append((ifv, n, 10 ** k))
            step = (wy - y0) / BANDS_Y
            for k in range(BANDS_Y):
                n = f'Test Paths {_key(lane)} Y{k}'
                t.areas[n] = [(x0, y0 + k * step), (x1, y0 + k * step), (x1, y0 + (k + 1) * step), (x0, y0 + (k + 1) * step)]
                ys.append((ifv, n, 10 ** k))
            LABEL[f'{lane} x'], LABEL[f'{lane} y'] = f'{LABEL[lane]}X', f'{LABEL[lane]}Y'
            _scored(t, f'{lane} x', xs)
            _scored(t, f'{lane} y', ys)
        t.scripts.insert(0, Script('Test - go', [], order))
        t.bench = [('bench_watch', dict(seconds=40, every=2, sheet=False, lines=4))]
        return t


    def group(m):
        t = Test()
        order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for lane, kind in (('team', 'move'), ('attack team', 'attack_move')):
            order += _go(m, t, lane, [f'{lane} ifv', f'{lane} engineer'], kind)
            goal = _area(m, t, f'{lane} goal', 100.0)
            _scored(t, lane, [(m.role(f'{lane} ifv').name, goal, 1), (m.role(f'{lane} engineer').name, goal, 10)])
        for lane in ('narrow', 'wide'):
            order += _go(m, t, lane, [f'{lane} tank {k + 1}' for k in range(CHOKE)])
            counted(f'CNV_Paths_{_key(lane)}', LABEL[lane], t, template=TANK, area=_area(m, t, f'{lane} goal', 200.0))
        t.scripts.insert(0, Script('Test - go', [], order))
        t.bench = [('bench_watch', dict(seconds=90, every=2, sheet=False, lines=4))]
        t.expect = [('宽口', 0, 'ever>', 0, 90)]
        return t


    def squeeze(m):
        """Does a unit's size go into its way (A355; A2's crest, work/mappage/a2/notes.md r7)? An IFV, a Guardian and
        an Apocalypse (radius 14 / 23.3 / 30.8), each in its own box, sent through a wall whose straight gap is 30 across
        (the IFV fits, the tanks not), a 150 one at the east end. Counters: 1 in the way round, 10 at the goal, 100 at
        the 30 gap's mouth. Size ignored: all three head for the 30; size in: the tanks go round. Read (测, 11-24):
        all three straight through the 30 (at the goal s2 / s4 / s7), none round -- engine_paths.readings.toml."""
        t = Test()
        order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for lane in SQUEEZE:
            order += _go(m, t, lane, [f'{lane} unit'])
            u = m.role(f'{lane} unit').name
            _scored(t, lane, [(u, _area(m, t, f'{lane} round', 75.0), 1), (u, _area(m, t, f'{lane} goal', 100.0), 10),
                              (u, _area(m, t, f'{lane} mouth', 30.0), 100)])
        t.scripts.insert(0, Script('Test - go', [], order))
        t.bench = [('bench_watch', dict(seconds=40, every=1, sheet=False, lines=3))]
        t.expect = [('挤口车', 0, 'ever==', 10, 40)]
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_paths': mission}
    CHECKS = {'engine_paths': {'detour': detour, 'limit': limit, 'stuck': stuck, 'alive': alive, 'where': where, 'group': group,
                               'size': squeeze}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_pull():
    """Engine unit tests, R3 step X (ADR 0032 5: the pathing details re-derived on the bench): how straight a ground way
    runs -- the simulator's Ground.pull (from each anchor straight to the farthest cell it sees). Every unit is a copy with
    ra3ext's read-only CNVProbe (a `probe` line per frame it moved: its trajectory), on the blocked-way probe map
    (maps/probe_block.py, the simulator reads the same map: ground() / impassable()).

      round   the 'bits' box: a Guardian tank from the start, 250 south of a field-0 wall (x 300..900, y 780..820), sent to
              the goal 250 north of it; the one way round is the gap at the box's east end (x 900..1100). 20 s later a
              Peacekeeper from 60 west of the start, sent to the same goal (the tank is there by then, past the corner).
              Read: the leg start -> wall's east end (its largest step off the straight line), how near the corner
              (900, 780 / 820) it passes, the leg corner -> goal.
      slant   open ground east of the seal lanes: a Guardian from (3900, 1550) sent 800 east and 300 north; a Peacekeeper
              the same 400 further north. Read: the largest step off the straight line.

    Each unit is put down facing its first leg (no turn on the spot to read past). No expectations: the readings are the
    probe lines (work/re/scripts/x_pull.py reads them against the simulator's ways).
    """
    import math
    import os

    import labpaths
    from maps import probe_block
    from parts import Mission, Script, Test, Unit

    TANK, MAN = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
    PROBE = {TANK: 'CNV_PullTank', MAN: 'CNV_PullMan'}
    EVERY, LINES = 150, 6000
    CORNER = (900.0, 780.0)                   # the wall's east end, start side
    SLANT = (800.0, 300.0)
    # role: (template, start, goal, the order's delay in seconds)
    LANES = {
        'round tank': (TANK, (500.0, 550.0), (500.0, 1050.0), 0.0),
        'round man': (MAN, (440.0, 550.0), (500.0, 1050.0), 20.0),
        'slant tank': (TANK, (3900.0, 1550.0), (3900.0 + SLANT[0], 1550.0 + SLANT[1]), 0.0),
        'slant man': (MAN, (3900.0, 1950.0), (3900.0 + SLANT[0], 1950.0 + SLANT[1]), 0.0),
    }
    RUN = 50.0


    def probe_copy(template):
        pid = PROBE[template]
        with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', template + '.xml'), encoding='utf-8') as f:
            x = f.read()
        assert x.count(f'id="{template}"') == 1 and x.count('<Behaviors>') == 1
        x = x.replace(f'id="{template}"', f'id="{pid}"', 1).replace(f'EditorName="{template}"', f'EditorName="{pid}"')
        x = x.replace('<Behaviors>', (f'<Behaviors>\n'
            f'\t\t\t<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>'), 1)
        return Unit(pid, x, names=dict(unit=pid), what=f'原版 {template} 的复制（探针）：多一个 ra3ext 的 CNVProbe，逐帧记位置',
                    params=dict(of=template, every=EVERY, lines=LINES))


    def _key(role):
        return role.title().replace(' ', '')


    def _first_leg(role):
        _, (x, y), goal, _ = LANES[role]
        tx, ty = CORNER if role.startswith('round') else goal
        return math.atan2(ty - y, tx - x)


    def mission():
        m = Mission(name='CampPull', map=probe_block, units=[probe_copy(TANK), probe_copy(MAN)], facts={})
        m.ext = True
        for role, (tpl, (x, y), _, _) in LANES.items():
            sx, sy = m.site('bits start') if role.startswith('round') else m.site('seal move')
            m.put(PROBE[tpl], 'bits start' if role.startswith('round') else 'seal move', x - sx, y - sy, role=role,
                  name=f'UNIT - CNV Pull {_key(role)}', angle=_first_leg(role))
        return m


    def ways(m):
        t = Test()
        first = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for role, (_, _, goal, delay) in LANES.items():
            wp = f'Test Pull {_key(role)} Goal'
            t.waypoints[wp] = goal
            go = m.order('move', [m.role(role).name], wp, crew=f'Pull{_key(role)}')
            if delay:
                timer = f'Test Pull {_key(role)}'
                first.append(('SET_MILLISECOND_TIMER', timer, delay))
                t.scripts.append(Script(f'Test - go {role}', [('TIMER_EXPIRED', timer)], go))
            else:
                first += go
        t.scripts.insert(0, Script('Test - go', [], first))
        t.bench = [('bench_watch', dict(seconds=RUN, every=5, sheet=False, lines=2))]
        t.expect = []
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_pull': mission}
    CHECKS = {'engine_pull': {'ways': ways}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def reroute():
    """Reroute tests (reroute in scenes.py): an ice wall is put across the quay between the squad and the middle
    bridge at the start; at GO_AT the squad is sent to the west field (again every few seconds, as a wave is). Counted,
    latched: one of the squad on the middle bridge's west end (it got over that way), on the north or south bridge (it went round), how many infantry got
    to the west field, and the wall's health (it stands).

    round: the wall up, none gets over by the middle bridge; some go round by another and get to the west field.
    open: no wall -- the control: they cross by the middle bridge (the shortest way).
    """
    from .scenes import (
        REROUTE_ANGLE as ANGLE,
        REROUTE_SQUAD as SQUAD,
        REROUTE_WARRIOR as WARRIOR,
        reroute_bridges as bridges,
    )
    from parts import Script, Test, counted, square

    GO_AT, RUN = 3.0, 150.0
    BRIDGE = 80.0                                   # half-side of the area on a bridge (its middle)


    def latch(t, counter, label, when):
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)]))
        t.scripts += [Script(f'Test - {counter} {k + 1}', w, [('SET_COUNTER', counter, 1)]) for k, w in enumerate(when)]


    def trip(m, wall):
        t = Test()
        s1 = m.player('s1')
        squad = [m.role(f'warrior {j}').name for j in range(1, SQUAD + 1)]
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('SET_MILLISECOND_TIMER', 'Test - go', GO_AT)]))
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go')],
                                [('MOVE_NAMED_UNIT_TO', n, m.mark('goal')) for n in squad]
                                + [('SET_MILLISECOND_TIMER', 'Test - go', 4.0)], once=False))
        b = bridges()
        mx, my = b['middle']
        for k in ('north', 'south'):
            t.areas[f'Test {k}'] = square(*b[k], BRIDGE)
        t.areas['Test west end'] = square(mx - 200, my, BRIDGE)
        if wall:
            # up before the squad is sent, across the quay (the mission's wall mark and angle). Bench 2026-10-27: put
            # up once the squad neared the bridge it came too late; on the bridge's deck it stopped nobody
            unit = next(u for u in m.units if u.id == 'CNV_RerouteWall')
            m.spawns.add(unit.id)
            t.scripts.append(Script('Test - close', [], [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION',
                                                          'UNIT - CNV Reroute Wall', unit.id, m.team('p1'),
                                                          m.mark('wall'), ANGLE)]))
            counted('Test Wall', '冰墙血量', t, health='UNIT - CNV Reroute Wall')
        latch(t, 'Test Middle', '走中桥过去', [[('NAMED_INSIDE_AREA', n, 'Test west end')] for n in squad])
        latch(t, 'Test Round', '绕北桥或南桥', [[('NAMED_INSIDE_AREA', n, f'Test {k}')] for n in squad
                                           for k in ('north', 'south')])
        t.areas['Test goal'] = square(*m.point('goal'), 300.0)
        counted('Test Goal W', '到了西边步兵', t, template=WARRIOR, player=s1, area='Test goal', most=4)
        t.bench = [('bench_watch', dict(seconds=RUN, every=4, sheet=False, lines=len(t.counters)))]
        return t


    def round_(m):
        t = trip(m, wall=True)
        t.expect += [('冰墙血量', 1, 'ever>=', 90), ('走中桥过去', 1, '==', 0), ('绕北桥或南桥', 1, 'ever==', 1),
                     ('到了西边步兵', 1, 'ever>=', 1)]
        return t


    def opened(m):
        t = trip(m, wall=False)
        t.expect += [('走中桥过去', 1, 'ever==', 1), ('到了西边步兵', 1, 'ever>=', 1)]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'reroute': {'round': round_, 'open': opened},
    }
    return dict(CHECKS=CHECKS)


def engine_runoffmap():
    """Engine unit test: 开出地图外 (ADR 0019 layer 2; RunOffMapBehavior) -- what PLAYER_SET_ALL_UNITS_TO_FLEE does:
    where a unit runs, whether it is gone on arrival and how (removed or killed), what an object without the module
    does, whether a later order stops the run.

    On the Niagara map the player's construction yard and one Allied peacekeeper (BaseInfantry: RunOffMapBehavior,
    RequiresSpecificTrigger, RunOffMapWaypointName "RunOffMap") on the west field, facing +x. In the 'Test Go' frame
    (one second in) each variant fires PLAYER_SET_ALL_UNITS_TO_FLEE on the player:

      a  near    a waypoint "RunOffMap" 200 east of the man (and a trigger area of half-side 40 around it)
      b  none    no such waypoint (read: the module falls back to 1000 straight ahead along the facing); the area
                 1000 east
      c  plant   as a, plus a power plant of the player (a structure: no RunOffMapBehavior); the plant is the target
                 of rows 2-3, the man moves to row 4
      d  stop    as a; NAMED_STOP on the man at frame 15

    Counters (four lines), every one counted from 'Test Go' on:
      帧数   frames since Go
      逃帧   1 x frames the target is not destroyed + 1000 x frames it carries FLEE_OFF_MAP (status 54 = the read 0x36)
      死法   1 x frames it is destroyed (NAMED_DESTROYED) + 1000 x frames it is dying (NAMED_DYING: killed, not removed)
      第四行  a, b, d: 1 x frames the man is inside the waypoint's area
             c: 1 x frames the man is not destroyed + 1000 x frames he carries FLEE_OFF_MAP

    Bench 11-06 (B round 4; one run each, rows every second, the first ~25 frames in):
      a CampRunoffmapA_mcp_1106_035353: 逃帧 64064 (FLEE_OFF_MAP from Go, gone after 64 frames); 死法 +1 a frame from
        65, never dying (removed, not killed); 第四行 15 (in the area from frame 50 to 64).
      b CampRunoffmapB_mcp_1106_035552: no waypoint -> 1000 east (the facing): 逃帧 304304, 第四行 15 (290-304).
        50/s from the order's frame, removed 3 frames after the point: 200 -> 64, 1000 -> 304.
      c CampRunoffmapC_mcp_1106_040133: the plant = frames only (never fleeing, never killed); the man 64064 as a.
      d CampRunoffmapD_mcp_1106_040353: after NAMED_STOP at 15 the man stays to the end, FLEE_OFF_MAP on throughout.
    Against the model (RA3-EngineModel runoffmap.py, tests/test_objects_bench.py "runoffmap"): every row the same.
    """
    import resources
    from maps import niagara
    from parts import Mission, Script, Test, square, status

    MAN, PLANT = 'AlliedAntiInfantryInfantry', 'AlliedPowerPlant'
    SPOT = ('west field', 0.0, 0.0)
    RUNS = {'a': 20.0, 'b': 50.0, 'c': 20.0, 'd': 20.0}
    FLEE = status('FLEE_OFF_MAP')


    def _n(part):
        return f'UNIT - CNV Runoffmap {part}'


    def mission():
        m = Mission(name='CampRunoffmap', map=resources.measured(niagara), units=[], facts={})
        m.spawns |= {PLANT}
        m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
        m.put(MAN, *SPOT, angle=0.0, role='man', name=_n('Man'))
        return m


    def runoffmap_test(m, which='a'):
        t = Test()
        p1 = m.player('p1')
        man, run = _n('Man'), RUNS[which]
        x, y = m.site(SPOT[0])[:2]
        far = 1000.0 if which == 'b' else 200.0
        if which != 'b':
            t.waypoints['RunOffMap'] = (x + far, y)
        t.areas['Test RunOff Spot'] = square(x + far, y, 40.0)
        start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
        target = man
        if which == 'c':
            target = _n('Plant')
            start.insert(0, ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', target, PLANT, m.team('p1'), 'Test Plant Spot'))
            t.waypoints['Test Plant Spot'] = (x - 250.0, y + 250.0)
        t.scripts.append(Script('Test - start', [], start))
        go = [('PLAYER_SET_ALL_UNITS_TO_FLEE', p1)]
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
        going = ('FLAG', 'Test Going', 1)

        t.counters.append(('CNV_Runoffmap_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Runoffmap_Frames')], once=False))
        if which == 'd':
            t.scripts.append(Script('Test - stop', [going, ('COUNTER', 'CNV_Runoffmap_Frames', 2, 15)],
                                    [('NAMED_STOP', man)]))
        rows = {
            2: ('逃帧', [(('NAMED_NOT_DESTROYED', target), 1), (('UNIT_HAS_OBJECT_STATUS', target, FLEE), 1000)]),
            3: ('死法', [(('NAMED_DESTROYED', target), 1), (('NAMED_DYING', target), 1000)]),
            4: ('第四行', [(('NAMED_NOT_DESTROYED', man), 1), (('UNIT_HAS_OBJECT_STATUS', man, FLEE), 1000)]
                if which == 'c' else [(('NAMED_INSIDE_AREA', man, 'Test RunOff Spot'), 1)]),
        }
        for k, (label, conds) in rows.items():
            t.counters.append((f'CNV_Runoffmap_Row{k}', label))
            for j, (cond, step) in enumerate(conds):
                t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                        [('INCREMENT_COUNTER', step, f'CNV_Runoffmap_Row{k}')], once=False))
        t.expect = [('帧数', 0, 'ever>=', 1, run)]
        t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=run))]
        return t


    MISSION = {'engine_runoffmap': mission}
    CHECKS = {'engine_runoffmap': {w: (lambda m, w=w: runoffmap_test(m, w)) for w in 'abcd'}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_seal():
    """Engine unit tests: what a unit does when it has NO way (docs/engine/pathing.md; engine line, 2026-11-08). The
    player's own structures made in the run (SovietBunker stands in for the ice wall) close a ring round it, the goal /
    target is outside. Map: maps/probe_block.py (the 'seal *' sites on open ground, goal 600 east of the start).
    Ring: RING bunkers on a circle of radius R round the start, made at MAKE s (nothing between them).

    move: an IFV and a peacekeeper sealed in, ordered by move at ORDER s to the goal 600 east. Counters per unit: sum of
      1 = left the start's 60, 2 = been at the east wall's inside, 10 = at the goal (0: never left the start).
    idle: a peacekeeper alone in the ring, no order, an unarmed enemy MCV 210 east (in sight, out of range; 60 beyond the
      ring). Counters: the peacekeeper as above (1, 2), the MCV's health. idle_open: the same, no ring (the control).
    spawn: a power plant of the player's stands; MAKE s: an IFV and a peacekeeper made at its centre; ORDER s: move to
      the goal 600 east. Counters per unit: 1 = out of the centre's 40, 2 = out of 110, 10 = at the goal.

    (Move's counters also add 4 = in the strip 60..80 east of the start, 8 / 16 / 32 = in the north / south / west part of
    the ring, 100 = at the goal. The idle_open check is named 'open': a mod name with an underscore crashes.)

    Read (测, 2026-11-08):
    move -- the ring is made s1, the order s4. The peacekeeper: 7 at s4 (out of the start, mid strip, east wall's inside)
      and it stays there to s61; never 100 (no way through, no way round: it stands at the east wall). The IFV: 17 (left
      the start, sits in the south part of the ring), never at the east wall, never at the goal to s61.
    idle -- the peacekeeper 0 and the enemy MCV 100 for 61 s: it neither moves nor fires (the ring is up from s1).
    open (no ring) -- the peacekeeper 0 too (never leaves the start's 60), the MCV 99 at s1 .. 88 at s61, 1 % per ~5 s:
      it fires from where it stands at 210 (an MCV is big; its edge is nearer), no walk.
    spawn -- a peacekeeper and an IFV made at the power plant's centre (s1): not out of the centre's 40 at s1 (0 0); the IFV
      out of 110 at s4 (3), the soldier out of 40 at s4 (1), out of 110 at s7 (3); goal: IFV s10, soldier s13. Units made
      inside a building come out of it by themselves and walk the 600 east.
    cut -- open's set-up, a closed box of field-0 ground (40 thick, 100 inside, no structure) round the MCV: the peacekeeper
      0 (stands), the MCV 99 at s1 .. 88 at s61, the same 1 % per ~5 s as open: terrain between does NOT stop the fire.
    row -- open's set-up, 11 player bunkers in a row 105 east of the soldier (330 long, ends open), made s1: the peacekeeper 0
      (never leaves, never goes round), the MCV 99 from s1 to s61 (one hit at most before the row stood): a structure in
      the line stops the fire. So 'sealed in, no fire' is the structures blocking the shot, not 'no way, no target'.
    erow -- row's set-up, the 11 bunkers the ENEMY's (s1): the peacekeeper 0 (stands), the MCV 99 and the middle bunker (Row
      Wall 5) 100, both flat from s1 to s61: it fires at neither the MCV nor the bunkers.
    tank -- a Guardian (AttackRange 150, LINE_OF_SIGHT flag) at the lane's start, the MCV 130 east, 11 player bunkers 65 east:
      the tank 0 (stands), the MCV 100 for s1..s61.  topen (control, no row): the tank 0, the MCV 98 s1, 96 s4-s10, 98 s13,
      99 s16-s19, 100 from s22 (hit by 4 % at most, then back up: NOT a clean control -- the cannon should hit harder;
      unexplained, the MCV may repair itself).
    arty (V4 launcher range 500, min 200, no LINE_OF_SIGHT flag; the Athena unit's only own weapon is a 500 / min 200
      targeter, so V4 stands in; MCV 350 east, the player's row 200 east) -- the V4 0, the MCV 100 s1..s61.  artyhp (the
      same, the middle bunker counted): the bunker 100 too.  artyo (no row, the control): the MCV 100 s1..s62 as well --
      the idle V4 does not fire at all, the row is not why (not split: unseen, or takes nothing by itself).
    artyrv (artyo + the player's MAP_REVEAL_ALL_PERM at the start; 测 2026-11-08 08:38) -- the V4 0, the MCV 100 s1..s61:
      seeing it is not the missing piece.  arty250 (artyo, the MCV 250 east; 08:40) -- the V4 0 at s1 but 1 from s4 (it
      LEFT its start's 60: idle, it walked off by itself), the MCV 100 s1..s61: no fire.  artyatk (artyo + an attack order
      on the MCV at 2 s; 08:43) -- the V4 0 (stays inside its 60 until s61, 1 at s61), the MCV 100 s1-s7, 84 s10, 85 s13-16,
      71 s19-22, 56 s25, 57 s28, 42 s31, 43 s34, 28 s37, 29 s40, 14 s43, 15 s46, 1 s49-s58: ordered, it fires from where it
      stands (~15 %/volley every ~7 s, the MCV regenerates ~1 between) and kills it by ~s60.  artytk (artyo with an s1
      Guardian tank, NO_ATTACK, 350 east instead; 08:48) -- the V4 0, the tank 100 s1..s61: an idle V4 picks no tank either.
      So the weapon / map / line are fine; only AutoAcquire of the idle V4 does not trigger (target seen, 350 inside 500).
    artyb (artyo with an s1 AlliedPowerPlant 350 east; 测 2026-11-08 08:55) -- the V4 0, the plant 100 s1..s61; artybk (an s1
      SovietBunker 350 east; 08:57) -- the V4 0, the bunker 100 s1..s61: an idle V4 picks no structure either, so 'siege units
      pick only structures when idle' is NOT it (the V4 stayed inside its 60 in both; the counter works on both targets).
    artyfe / artyf15 / artyf30 (artyo with the V4 put down facing 0 / 15 / 30 degrees off the MCV 350 east instead of the
      player's default north = 90 off; 测 2026-11-08 15:11-15:17) -- all three alike: the V4 0 throughout, the MCV 100 s1-s7,
      84 at s10 (s11 in f15), then only regenerating ~1 per 3 s up to 97 at s61: an idle V4 facing within 30 degrees fires
      ONE volley and never again; facing 90 off (artyo) it fires none.  So the facing matters, but not by the rocket's
      AcceptableAimDelta 20 alone (30 fires), and something stops it after the first volley (not split yet).
      artyf60 (60 off, its own lane at (300, 2500); 15:24) -- the same: 84 at s10, then regenerating to 97: one volley.
      So 0..60 off: one volley, 90 off: none (CanOnlyAttackTargetsInFront-like strict half plane?); the V4 rocket is
      ClipSize 1, ClipReloadTime 4.5-5.5 s, ReAcquireDetailType PRE_FIRE: the stop is after its one clip.
    attack -- the soldier 1 at s4 (left the start), 5 from s7 (north of the row's end, never east of it); the MCV 99 s1-s7,
      97 s10, 96 s13 ... 86 s37, 85 s40-s61: told to attack, it walks round the row's end and fires from there.
    aa (IFV, a hovering Twinblade with NO_ATTACK 200 east, the row 100 east) and aaopen (no row): the same readings, 79 s1,
      50 s4, 16 s7, 4 from s10: the row does not stop a shot at a target in the air.
    (All four measured 2026-11-08 06:41-06:59; arty / attack / aa / aaopen had failed on a lost Direct3D device before.)
    (A first spawn run read 3 3 at s1: a named unit that does not exist yet counts as 'outside' an area; the scripts now
    also ask it to be inside a big area.)
    """
    import math

    from maps import probe_block
    from parts import Mission, Script, Test, counted, square

    IFV = 'AlliedAntiAirVehicleTech1'
    FOOT = 'AlliedAntiInfantryInfantry'
    WALL = 'SovietBunker'
    ENEMY = 'AlliedMCV'
    TANK, V4, HELI = 'AlliedAntiVehicleVehicleTech1', 'SovietAntiStructureVehicle', 'SovietAntiGroundAircraft'
    BUILDING = 'AlliedPowerPlant'
    FACING = {'artyfe': 0.0, 'artyf15': 15.0, 'artyf30': 30.0, 'artyf60': 60.0}    # the V4's facing off the MCV, degrees (p1's default: 90)
    RING, R = 36, 150.0
    MAKE, ORDER = 1.0, 4.0


    def _ring(m, t, site):
        """The script that makes the ring round `site` when MAKE has run out."""
        x0, y0 = m.site(site)
        make = []
        for k in range(RING):
            a = 2 * math.pi * k / RING
            wp = f'Test Seal {site.title()} Ring {k}'
            t.waypoints[wp] = (x0 + R * math.cos(a), y0 + R * math.sin(a))
            make.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', f'UNIT - CNV Seal {site.title()} Ring {k}', WALL,
                         m.team('p1'), wp))
        t.scripts.append(Script(f'Test - seal ring {site}', [('TIMER_EXPIRED', 'Test Seal Make')], make))


    def _timers(t):
        t.scripts.append(Script('Test - seal timers', [], [('SET_MILLISECOND_TIMER', 'Test Seal Make', MAKE),
                                                           ('SET_MILLISECOND_TIMER', 'Test Seal Order', ORDER)]))


    def _order(m, t, site, names, crew):
        wp = f'Test Seal {site.title()} Goal'
        t.waypoints[wp] = m.site(f'{site} goal')
        t.scripts.append(Script(f'Test - seal go {site}', [('TIMER_EXPIRED', 'Test Seal Order')],
                                m.order('move', names, wp, crew=crew)))


    def _score(m, t, counter, label, unit, parts):
        """parts: [(site-relative area, n, 'out' | 'in')]: once a unit is out of / in the area, the counter gets n."""
        t.counters.append((counter, label))
        for k, (area, n, how) in enumerate(parts):
            t.scripts.append(Script(f'Test - {counter} {k}',
                                    [('NAMED_OUTSIDE_AREA' if how == 'out' else 'NAMED_INSIDE_AREA', unit, area)],
                                    [('INCREMENT_COUNTER', n, counter)], once=True))


    def _areas(m, t, site, tag, root=True, goal=True):
        x, y = m.site(site)
        out = []
        t.areas[f'Test Seal {tag} Start'] = square(x, y, 60.0)
        out.append((f'Test Seal {tag} Start', 1, 'out'))
        if root:
            for nm, n, (ax0, ay0, ax1, ay1) in (('North', 8, (-140, 60, 140, 140)), ('South', 16, (-140, -140, 140, -60)),
                                                ('West', 32, (-140, -60, -60, 60))):
                t.areas[f'Test Seal {tag} {nm}'] = [(x + ax0, y + ay0), (x + ax1, y + ay0), (x + ax1, y + ay1),
                                                    (x + ax0, y + ay1)]
                out.append((f'Test Seal {tag} {nm}', n, 'in'))
            t.areas[f'Test Seal {tag} Mid'] = [(x + 60, y - 70), (x + 80, y - 70), (x + 80, y + 70), (x + 60, y + 70)]
            out.append((f'Test Seal {tag} Mid', 4, 'in'))
            t.areas[f'Test Seal {tag} Root'] = [(x + 80, y - 70), (x + 140, y - 70), (x + 140, y + 70), (x + 80, y + 70)]
            out.append((f'Test Seal {tag} Root', 2, 'in'))
        if goal:
            gx, gy = m.site(f'{site} goal')
            t.areas[f'Test Seal {tag} Goal'] = square(gx, gy, 100.0)
            out.append((f'Test Seal {tag} Goal', 100, 'in'))
        return out


    def mission():
        m = Mission(name='CampSeal', map=probe_block, facts={})
        m.put(IFV, 'seal move', -20.0, 0.0, role='move ifv', name='UNIT - CNV Seal Move Ifv')
        m.put(FOOT, 'seal move', 20.0, 0.0, role='move foot', name='UNIT - CNV Seal Move Foot')
        for lane in ('idle', 'idle open', 'cut', 'row'):
            k = lane.title()
            m.put(FOOT, f'seal {lane}', role=f'{lane} foot', name=f'UNIT - CNV Seal {k} Foot')
            m.put(ENEMY, f'seal {lane}', 210.0, 0.0, side='s1', angle=90.0, role=f'{lane} enemy',
                  name=f'UNIT - CNV Seal {k} Enemy')
        for lane, kind, dx in (('erow', FOOT, 210.0), ('attack', FOOT, 210.0), ('tank', TANK, 130.0),
                               ('tankopen', TANK, 130.0), ('arty', V4, 350.0), ('arty250', V4, 250.0),
                               ('artytk', V4, None), ('artyb', V4, None), ('artybk', V4, None)):
            k = lane.title()
            m.put(kind, f'seal {lane}', role=f'{lane} foot', name=f'UNIT - CNV Seal {k} Foot')
            if lane in ('artyb', 'artybk'):    # an s1 structure 350 east instead of the MCV
                m.put(BUILDING if lane == 'artyb' else WALL, f'seal {lane}', 350.0, 0.0, side='s1', role=f'{lane} enemy',
                      name=f'UNIT - CNV Seal {k} Enemy')
                continue
            if dx is None:    # artytk: an s1 Guardian instead of the MCV
                m.put(TANK, f'seal {lane}', 350.0, 0.0, side='s1', role=f'{lane} enemy', name=f'UNIT - CNV Seal {k} Enemy')
                continue
            m.put(ENEMY, f'seal {lane}', dx, 0.0, side='s1', angle=90.0, role=f'{lane} enemy', name=f'UNIT - CNV Seal {k} Enemy')
        for lane, deg in FACING.items():    # artyo's lane with the V4 turned: 0 = facing the MCV 350 east
            k = lane.title()
            m.put(V4, f'seal {lane}', angle=math.radians(deg), role=f'{lane} foot', name=f'UNIT - CNV Seal {k} Foot')
            m.put(ENEMY, f'seal {lane}', 350.0, 0.0, side='s1', angle=90.0, role=f'{lane} enemy',
                  name=f'UNIT - CNV Seal {k} Enemy')
        for lane in ('aa', 'aaopen'):
            k = lane.title()
            m.put(IFV, f'seal {lane}', role=f'{lane} foot', name=f'UNIT - CNV Seal {k} Foot')
            m.put(HELI, f'seal {lane}', 200.0, 0.0, side='s1', role=f'{lane} enemy', name=f'UNIT - CNV Seal {k} Enemy')
        m.put(BUILDING, 'seal spawn', role='spawn building', name='UNIT - CNV Seal Spawn Building')
        for lane, (bx, by), (px, py), (us, them) in (('ebld', (120.0, 0.0), (-150.0, 0.0), ('s1', 'p1')),
                                                     ('ebldam', (500.0, 100.0), (500.0, -120.0), ('s1', 'p1')),
                                                     ('pam', (500.0, 100.0), (500.0, -120.0), ('p1', 's1'))):
            k = lane.title()
            m.put(FOOT, f'seal {lane}', side=us, role=f'{lane} foot', name=f'UNIT - CNV Seal {k} Foot')
            m.put(WALL, f'seal {lane}', bx, by, side=them, role=f'{lane} bunker', name=f'UNIT - CNV Seal {k} Bunker')
            m.put(BUILDING, f'seal {lane}', px, py, side=them, role=f'{lane} plant', name=f'UNIT - CNV Seal {k} Plant')
        return m


    def move(m):
        t = Test()
        _timers(t)
        _ring(m, t, 'seal move')
        for role, tag, counter, label in (('move ifv', 'Ifv', 'CNV_Seal_Ifv', '车'), ('move foot', 'Foot', 'CNV_Seal_Foot', '兵')):
            unit = m.role(role).name
            _score(m, t, counter, label, unit, _areas(m, t, 'seal move', f'Move {tag}'))
        _order(m, t, 'seal move', [m.role('move ifv').name, m.role('move foot').name], 'SealMove')
        t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=2))]
        t.expect = []
        return t


    def _idle(m, lane, ring):
        t = Test()
        site = f'seal {lane}'
        if ring:
            _timers(t)
            _ring(m, t, site)
        _score(m, t, 'CNV_Seal_Foot', '兵', m.role(f'{lane} foot').name, _areas(m, t, site, lane.title(), goal=False,
                                                                           root=lane in ('idle', 'idle open')))
        counted('CNV_Seal_Hp', '敌车血量', t, health=m.role(f'{lane} enemy').name)
        t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=2))]
        t.expect = []
        return t


    def idle(m):
        return _idle(m, 'idle', True)


    def idle_open(m):
        return _idle(m, 'idle open', False)


    def cut(m):
        """open's set-up with a closed ring of field-0 ground (no structure) round the MCV, between it and the soldier."""
        return _idle(m, 'cut', False)


    def row(m):
        """open's set-up with a row of the player's bunkers (ROW_N, spacing 30, 105 east of the start, centred on its y)
        made at MAKE s: the ends are open (the row is 330 long), a soldier can walk round. Counters: 1 = left the start's
        60, 2 = east of the row, 4 / 8 = north / south of the row's end."""
        t = _idle(m, 'row', False)
        _timers(t)
        x0, y0 = m.site('seal row')
        make = []
        for k in range(11):
            wp = f'Test Seal Row {k}'
            t.waypoints[wp] = (x0 + 105.0, y0 - 150.0 + 30.0 * k)
            make.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', f'UNIT - CNV Seal Row Wall {k}', WALL, m.team('p1'), wp))
        t.scripts.append(Script('Test - seal row make', [('TIMER_EXPIRED', 'Test Seal Make')], make))
        unit = m.role('row foot').name
        t.areas['Test Seal Row East'] = [(x0 + 130, y0 - 400), (x0 + 600, y0 - 400), (x0 + 600, y0 + 400), (x0 + 130, y0 + 400)]
        t.areas['Test Seal Row North'] = [(x0 - 200, y0 + 170), (x0 + 130, y0 + 170), (x0 + 130, y0 + 400), (x0 - 200, y0 + 400)]
        t.areas['Test Seal Row South'] = [(x0 - 200, y0 - 400), (x0 + 130, y0 - 400), (x0 + 130, y0 - 170), (x0 - 200, y0 - 170)]
        for k, (area, n) in enumerate((('Test Seal Row East', 2), ('Test Seal Row North', 4), ('Test Seal Row South', 8))):
            t.scripts.append(Script(f'Test - CNV_Seal_Foot r{k}', [('NAMED_INSIDE_AREA', unit, area)],
                                    [('INCREMENT_COUNTER', n, 'CNV_Seal_Foot')], once=True))
        return t


    def _wall(m, lane, side, dx, step=30.0, n=11, wall_hp=False):
        """A row of n bunkers of `side`, dx east of the lane's start, centred on its y, made at MAKE s. Counters:
        CNV_Seal_Foot (1 = left the start's 60, 2 = east of the row, 4 / 8 = north / south of the row's end),
        CNV_Seal_Hp the target's health, CNV_Seal_Wall the middle bunker's health when wall_hp."""
        t = _idle(m, lane, False)
        _timers(t)
        x0, y0 = m.site(f'seal {lane}')
        half = step * (n - 1) / 2
        names = [f'UNIT - CNV Seal {lane.title()} Wall {k}' for k in range(n)]
        make = []
        for k in range(n):
            wp = f'Test Seal {lane.title()} Row {k}'
            t.waypoints[wp] = (x0 + dx, y0 - half + step * k)
            make.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', names[k], WALL, m.team(side), wp))
        t.scripts.append(Script(f'Test - seal {lane} make', [('TIMER_EXPIRED', 'Test Seal Make')], make))
        unit = m.role(f'{lane} foot').name
        e, hy, tag = x0 + dx + 25.0, half + 20.0, lane.title()
        t.areas[f'Test Seal {tag} East'] = [(e, y0 - 400), (x0 + 900, y0 - 400), (x0 + 900, y0 + 400), (e, y0 + 400)]
        t.areas[f'Test Seal {tag} North'] = [(x0 - 200, y0 + hy), (e, y0 + hy), (e, y0 + 400), (x0 - 200, y0 + 400)]
        t.areas[f'Test Seal {tag} South'] = [(x0 - 200, y0 - 400), (e, y0 - 400), (e, y0 - hy), (x0 - 200, y0 - hy)]
        for k, (area, nn) in enumerate(((f'Test Seal {tag} East', 2), (f'Test Seal {tag} North', 4),
                                        (f'Test Seal {tag} South', 8))):
            t.scripts.append(Script(f'Test - CNV_Seal_Foot {lane} r{k}', [('NAMED_INSIDE_AREA', unit, area)],
                                    [('INCREMENT_COUNTER', nn, 'CNV_Seal_Foot')], once=True))
        if wall_hp:
            counted('CNV_Seal_Wall', '中墙血', t, health=names[n // 2])
        return t


    def erow(m):
        """row with the 11 bunkers the ENEMY's (s1): does the soldier shoot the MCV, the bunkers, or nothing."""
        return _wall(m, 'erow', 's1', 105.0, wall_hp=True)


    def tank(m):
        """a Guardian tank (range 150), the MCV 130 east, the player's row 65 east."""
        return _wall(m, 'tank', 'p1', 65.0)


    def tankopen(m):
        return _idle(m, 'tankopen', False)


    def arty(m):
        """a Soviet V4 launcher (range 500, min 200; no LINE_OF_SIGHT flag), the MCV 350 east, the player's row 200 east."""
        return _wall(m, 'arty', 'p1', 200.0)


    def artyhp(m):
        """arty's set-up, the middle bunker's health counted too: does the V4's rocket hit the row in between."""
        t = _wall(m, 'arty', 'p1', 200.0, wall_hp=True)
        t.bench[0][1]['lines'] = 3
        return t


    def artyopen(m):
        """arty's lane with no row (the control): does the idle V4 fire at the MCV 350 off at all."""
        return _idle(m, 'arty', False)


    def artyrv(m):
        """artyo's set-up plus the player's MAP_REVEAL_ALL_PERM at the start: is it 'the player does not see it'."""
        t = _idle(m, 'arty', False)
        t.scripts.append(Script('Test - seal reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        return t


    def arty250(m):
        """artyo's set-up with the MCV 250 east (lane 'arty250'): a range-edge / acquire-range issue?"""
        return _idle(m, 'arty250', False)


    def artyatk(m):
        """artyo's set-up plus an explicit attack order on the MCV at 2 s: does the V4 fire at it at all here."""
        t = _idle(m, 'arty', False)
        t.scripts.append(Script('Test - seal arty attack', [('TIMER_EXPIRED', 'Test Seal Atk')],
                                m.order('attack', [m.role('arty foot').name], m.role('arty enemy').name, 'p1',
                                        crew='SealArtyAtk')))
        t.scripts.append(Script('Test - seal arty timer', [], [('SET_MILLISECOND_TIMER', 'Test Seal Atk', 2.0)]))
        return t


    def artytk(m):
        """artyo's set-up with an s1 Guardian tank (NO_ATTACK) 350 east instead of the MCV: does an idle V4 pick a unit."""
        t = _idle(m, 'artytk', False)
        t.scripts.append(Script('Test - seal artytk start', [], [('UNIT_CHANGE_OBJECT_STATUS', m.role('artytk enemy').name,
                                                                  'NO_ATTACK', 1)]))
        return t


    def artyb(m):
        """artyo's set-up with an s1 AlliedPowerPlant 350 east: does an idle (siege) V4 pick a structure by itself."""
        return _idle(m, 'artyb', False)


    def artybk(m):
        """artyb with an s1 SovietBunker instead of the power plant."""
        return _idle(m, 'artybk', False)


    def artyfe(m):
        """artyo with the V4 placed facing the MCV 350 east (p1 units face north by default: the MCV was 90 degrees off its
        nose). The V4's rocket is on a hardpoint (no turret) and it writes no RotateToTargetWhenAiming (default false; the
        peacekeeper, which does fire idle, writes true): does an idle V4 take what is in front of it."""
        return _idle(m, 'artyfe', False)


    def artyf15(m):
        """artyfe with the V4 turned 15 degrees off the MCV (its rocket's AcceptableAimDelta is 20)."""
        return _idle(m, 'artyf15', False)


    def artyf30(m):
        """artyfe with the V4 turned 30 degrees off the MCV."""
        return _idle(m, 'artyf30', False)


    def artyf60(m):
        """artyfe with the V4 turned 60 degrees off the MCV (between 30, one volley, and the default 90, none)."""
        return _idle(m, 'artyf60', False)


    def attack(m):
        """row's set-up (lane 'attack'), plus an explicit attack order on the MCV at 4 s."""
        t = _wall(m, 'attack', 'p1', 105.0)
        t.scripts.append(Script('Test - seal attack', [('TIMER_EXPIRED', 'Test Seal Order')],
                                m.order('attack', [m.role('attack foot').name], m.role('attack enemy').name, 'p1',
                                        crew='SealAttack')))
        return t


    def aa(m):
        """an IFV (range 300), an s1 Twinblade (NO_ATTACK, on the ground) 200 east, the player's row 100 east."""
        t = _wall(m, 'aa', 'p1', 100.0)
        t.scripts.append(Script('Test - seal aa start', [], [('UNIT_CHANGE_OBJECT_STATUS', m.role('aa enemy').name,
                                                              'NO_ATTACK', 1)]))
        return t


    def aaopen(m):
        t = _idle(m, 'aaopen', False)
        t.scripts.append(Script('Test - seal aa start', [], [('UNIT_CHANGE_OBJECT_STATUS', m.role('aaopen enemy').name,
                                                              'NO_ATTACK', 1)]))
        return t


    def _ebld(m, lane):
        """The computer side's soldier by the player's buildings (Generals PartitionFilterRejectBuildings: a computer
        player's units take enemy buildings by themselves, a human's only base defences): a bunker and a power plant of
        the player's in range, the line clear. Counters: the bunker's and the plant's health, the soldier (1 = left the
        start's 60, 10 = at the goal)."""
        t = Test()
        counted('CNV_Seal_Wall', '地堡血', t, health=m.role(f'{lane} bunker').name)
        counted('CNV_Seal_Hp', '电厂血', t, health=m.role(f'{lane} plant').name)
        x, y = m.site(f'seal {lane}')
        t.areas[f'Test Seal {lane.title()} Start'] = square(x, y, 60.0)
        parts = [(f'Test Seal {lane.title()} Start', 1, 'out')]
        if lane in ('ebldam', 'pam'):
            k = lane.title()
            gx, gy = m.site(f'seal {lane} goal')
            t.areas[f'Test Seal {k} Goal'] = square(gx, gy, 100.0)
            parts.append((f'Test Seal {k} Goal', 10, 'in'))
            # 100 = back by the plant (a strip south of the attack-move's line, round the plant: not on the way)
            t.areas[f'Test Seal {k} By Plant'] = [(x + 300, y - 300), (x + 700, y - 300), (x + 700, y - 70), (x + 300, y - 70)]
            parts.append((f'Test Seal {k} By Plant', 100, 'in'))
            wp = f'Test Seal {k} Goal Point'
            t.waypoints[wp] = (gx, gy)
            _timers(t)
            side = 's1' if lane == 'ebldam' else 'p1'
            t.scripts.append(Script(f'Test - seal {lane} go', [('TIMER_EXPIRED', 'Test Seal Order')],
                                    m.order('attack_move', [m.role(f'{lane} foot').name], wp, side, crew=f'Seal{k}')))
        _score(m, t, 'CNV_Seal_Foot', '兵', m.role(f'{lane} foot').name, parts)
        t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=3))]
        t.expect = []
        return t


    def ebld(m):
        """the enemy's soldier idle, the player's bunker 120 east and power plant 150 west."""
        return _ebld(m, 'ebld')


    def ebldam(m):
        """the enemy's soldier attack-moves 1000 east at 4 s past the player's bunker (100 north of its line) and power
        plant (120 south), both 500 along."""
        return _ebld(m, 'ebldam')


    def pam(m):
        """ebldam with the sides swapped: the player's soldier attack-moves past the enemy's bunker and plant."""
        return _ebld(m, 'pam')


    def spawn(m):
        t = Test()
        _timers(t)
        x, y = m.site('seal spawn')
        t.waypoints['Test Seal Spawn Centre'] = (x, y)
        names = ['UNIT - CNV Seal Spawn Ifv', 'UNIT - CNV Seal Spawn Foot']
        t.scripts.append(Script('Test - seal make', [('TIMER_EXPIRED', 'Test Seal Make')],
                                [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', names[0], IFV, m.team('p1'), 'Test Seal Spawn Centre'),
                                 ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', names[1], FOOT, m.team('p1'),
                                  'Test Seal Spawn Centre')]))
        gx, gy = m.site('seal spawn goal')
        for tag, counter, label, unit in (('Ifv', 'CNV_Seal_Ifv', '车', names[0]), ('Foot', 'CNV_Seal_Foot', '兵', names[1])):
            t.areas[f'Test Seal Spawn {tag} Near'] = square(x, y, 40.0)
            t.areas[f'Test Seal Spawn {tag} Far'] = square(x, y, 110.0)
            t.areas[f'Test Seal Spawn {tag} Goal'] = square(gx, gy, 100.0)
            t.areas[f'Test Seal Spawn {tag} Big'] = square(x + 300, y, 800.0)    # alive: a missing unit is 'outside'
            t.counters.append((counter, label))
            for k, (area, n, how) in enumerate(((f'Test Seal Spawn {tag} Near', 1, 'out'),
                                                (f'Test Seal Spawn {tag} Far', 2, 'out'),
                                                (f'Test Seal Spawn {tag} Goal', 10, 'in'))):
                cond = [('NAMED_OUTSIDE_AREA' if how == 'out' else 'NAMED_INSIDE_AREA', unit, area),
                        ('NAMED_INSIDE_AREA', unit, f'Test Seal Spawn {tag} Big')]
                t.scripts.append(Script(f'Test - {counter} {k}', cond, [('INCREMENT_COUNTER', n, counter)], once=True))
        _order(m, t, 'seal spawn', names, 'SealSpawn')
        t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=2))]
        t.expect = []
        return t


    MISSION = {'engine_seal': mission}
    CHECKS = {'engine_seal': {'move': move, 'idle': idle, 'open': idle_open, 'cut': cut, 'row': row, 'spawn': spawn,
                               'erow': erow, 'tank': tank, 'topen': tankopen, 'arty': arty, 'artyhp': artyhp, 'artyo': artyopen, 'artyrv': artyrv, 'arty250': arty250,
                               'artyatk': artyatk, 'artytk': artytk, 'artyb': artyb, 'artybk': artybk, 'artyfe': artyfe,
                               'artyf15': artyf15, 'artyf30': artyf30, 'artyf60': artyf60, 'attack': attack,
                               'aa': aa, 'aaopen': aaopen, 'ebld': ebld, 'ebldam': ebldam, 'pam': pam}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_spots():
    """Engine probe for sim.HOLD_SPOTS (Sim.claims: every move's goal kept off the spots other units hold): mission
    engine_spots in scenes.py, three trucks on teams of their own sent to one point (MOVE_TEAM_TO each team).

      same    all three sent at 1 s. 环k = how many of the nested squares (half-sides RINGS) round the point truck k
              stands in: 4 within 10, 3 within 25, 2 within 45, 1 within 80, 0 farther. [HOLD_SPOTS: one truck 4, the
              other two 1-3 (moved off by about two radii); without it all three 4, or pushed about]
      late    truck k sent at 1 + STAGGER (k - 1) s: each arrives after the one before stands on the point.

    读数
    Bench 2026-11-09 (one run each; sim pairs in tests/test_simbench.py test_spots_*):
      same    环1 环2 环3: s9 0 1 1 | s10 1 4 1 | s11 3 2 1 | s12-s36 4 2 1 -- they stand apart: truck 1 (ordered first) on
              the point, truck 2 25-45 off (it passed over the point at s10 on its way), truck 3 45-80 off. sim.HOLD_SPOTS
              on: 4 2 2 (0 / 50 / 44.7 off); off: 4 4 4 (all three on the point).
      late    s9 1 0 0 | s11-s27 4 0 0 | s29 4 1 0 | s31-s47 4 2 0 | s49-s75 4 2 1 -- the same: each one sent later stops
              off the spots already held.
    (A first build had them at -250 / +300: in the sea, nobody moved.)
    """
    from parts import Script, Test, square

    RINGS = (80.0, 45.0, 25.0, 10.0)
    STAGGER = 20.0
    RUN = {'same': 35.0, 'late': 75.0}


    def _at(t, key, secs, actions):
        timer = f'Test {key} Timer'
        t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                      Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


    def _rings(t, m):
        spot = m.point('spot')
        for r in RINGS:
            t.areas[f'Test Spot {r:g}'] = square(*spot, r)
        for k in (1, 2, 3):
            name, counter = m.role(f'truck {k}').name, f'CNV_Spots_Ring{k}'
            t.counters.append((counter, f'环{k}'))
            t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
            t.scripts += [Script(f'Test - {counter} {r:g}', [('NAMED_INSIDE_AREA', name, f'Test Spot {r:g}')],
                                 [('INCREMENT_COUNTER', 1, counter)], once=False) for r in RINGS]


    def _send(m, k):
        return m.order('move', [m.role(f'truck {k}').name], m.mark('spot'), crew=f'T{k}')


    def _watch(t, run, every=1.0):
        t.bench = [('bench_watch', dict(seconds=run, every=every, sheet=False, lines=len(t.counters)))]


    def same(m):
        t = Test()
        _at(t, 'go', 1.0, sum((_send(m, k) for k in (1, 2, 3)), []))
        _rings(t, m)
        _watch(t, RUN['same'])
        return t


    def late(m):
        t = Test()
        for k in (1, 2, 3):
            _at(t, f'go{k}', 1.0 + STAGGER * (k - 1), _send(m, k))
        _rings(t, m)
        _watch(t, RUN['late'], 2.0)
        return t


    CHECKS = {'engine_spots': {'same': same, 'late': late}}     # (a mod name over 15 characters crashes: not 'stagger')
    return dict(CHECKS=CHECKS)


def engine_stance():
    """Engine unit test: stance (ADR 0019 layer 2; StancesBehavior) -- does HOLD_FIRE stop a shooting unit, does it stop a
    standing order, does an idle unit fire by itself, does a held unit hit back.

    On the festival map's west field a player's guardian tank A (AlliedAntiVehicleVehicleTech1) and an enemy (s1) guardian
    T 150 away (in range, as in engine_attack); 2000 money; map revealed. T carries NO_ATTACK from the start (not in e). In
    the 'Test Go' frame (one second in) each variant does (stance integers: GUARD 0, AGGRESSIVE 1, HOLD_POSITION 2,
    HOLD_FIRE 3, all set with UNIT_SET_STANCE; "frame n" = the n-th frame of the 帧数 counter):

      a  mid     Go: A ordered to attack T (NAMED_ATTACK_NAMED); frame 45: A set to HOLD_FIRE
      b  held    A set to HOLD_FIRE before Go; Go: A ordered to attack T
      c  idle    nothing at all (A default stance, T cannot shoot)
      d  idleHF  as c, A set to HOLD_FIRE before Go
      e  hitback A set to HOLD_FIRE before Go; T not NO_ATTACK; Go: T ordered to attack A
      f  resume  as a; frame 90: A set back to GUARD

    Counters (four lines), every one counted from 'Test Go' on:
      帧数   frames since Go
      T状态  1 x frames T is at full health + 1000 x frames it is below (first drop = frame count of the 1 part + 1)
      T血量  T's health in percent, set every frame
      A血量  A's health in percent, set every frame (e)

    Bench 11-06 (first row already ~28 frames in; T hits are 12.5 percent each, ~7 frames after a row seen at 87/75/...):
      a CampStanceA_mcp_1106_025915: T 100 -> 87 (first drop frame 16) -> 75 (between frames 44 and 51, i.e. a shot
        already flying or fired at the stance frame); then 75 to frame 179: no more hits. HOLD_FIRE stops a standing order.
      b CampStanceB_mcp_1106_030114: HOLD_FIRE before the order does NOT stop it: 87 (frame 16), 75, 62 (<=81), 50 (<=128),
        37 (<=142), 25 (<=173), 12 (<=200); a hit about every 45-50 frames. The order beats the stance.
      c CampStanceC_mcp_1106_030325: A fires by itself, default stance: first drop frame 13 (12015 at frame 27), then
        75, 62, 50, 37, 25 at the same rhythm as b.
      d CampStanceD_mcp_1106_030532: A set HOLD_FIRE, no order: T 100 throughout (T状态 = 帧数 to frame 180), no fire.
      e CampStanceE_mcp_1106_030744: A held, T ordered to attack A: A 87 -> 75 -> 62 -> 50 -> 37 -> 25 (first seen
        87 at frame 29); T stays 100 all the way: a held unit does not hit back.
      f CampStanceF_mcp_1106_030945: as a, GUARD at frame 90: 87, 75 (<=52), none to frame ~90, then 62 (<=98), 50
        (<=129), 37 (<=158): the original order is still there and runs again.
    Against the model (RA3-EngineModel stance.py + weapons.py, tests/test_objects_bench.py "stance", run with real
    weapons): a, b, d, e, f the same (the hits' frames inside the bench's row bounds); c differs (strict xfail): idle
    auto-acquire is the AI layer, not modelled, the model's A never fires without an order.
    """
    from maps import festival
    from parts import Mission, Script, Test, counted

    GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
    RUN = 10.0
    HOLD_FIRE, GUARD = 3, 0
    SPOT = ('west field', 0, -150)


    def _n(part):
        return f'UNIT - CNV Stance {part}'


    def mission():
        m = Mission(name='CampStance', map=festival, facts={})
        m.put(GUARDIAN, SPOT[0], SPOT[1], SPOT[2], name=_n('A'), role='guard A')
        m.put(GUARDIAN, SPOT[0], SPOT[1], SPOT[2] + 150, side='s1', name=_n('T'), role='guard T')
        return m


    def stance_test(m, which='a'):
        t = Test()
        p1 = m.player('p1')
        A, T = m.role('guard A').name, m.role('guard T').name
        start = [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 2000), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
        if which != 'e':
            start.append(('UNIT_CHANGE_OBJECT_STATUS', T, 'NO_ATTACK', 1))
        if which in 'bde':
            start.append(('UNIT_SET_STANCE', A, HOLD_FIRE))
        t.scripts.append(Script('Test - start', [], start))
        go = []
        if which in 'abf':
            go.append(('NAMED_ATTACK_NAMED', A, T))
        if which == 'e':
            go.append(('NAMED_ATTACK_NAMED', T, A))
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
        going = ('FLAG', 'Test Going', 1)

        t.counters.append(('CNV_Stance_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Stance_Frames')], once=False))
        if which in 'af':
            t.scripts.append(Script('Test - hold fire', [going, ('COUNTER', 'CNV_Stance_Frames', 2, 45)],
                                    [('UNIT_SET_STANCE', A, HOLD_FIRE)]))
        if which == 'f':
            t.scripts.append(Script('Test - guard', [going, ('COUNTER', 'CNV_Stance_Frames', 2, 90)],
                                    [('UNIT_SET_STANCE', A, GUARD)]))

        t.counters.append(('CNV_Stance_TState', 'T状态'))
        for j, (cond, step) in enumerate(((('UNIT_HEALTH', T, 3, 100), 1), (('UNIT_HEALTH', T, 0, 100), 1000))):
            t.scripts.append(Script(f'Test - tstate {j}', [going, cond], [('INCREMENT_COUNTER', step, 'CNV_Stance_TState')],
                                    once=False))
        counted('CNV_Stance_THp', 'T血量', t, health=T)
        counted('CNV_Stance_AHp', 'A血量', t, health=A)
        t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
        t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN))]
        return t


    MISSION = {'engine_stance': mission}
    CHECKS = {'engine_stance': {w: (lambda m, w=w: stance_test(m, w)) for w in 'abcdef'}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_terrain():
    """Engine unit test: does the game walk by the map's impassable bits (BlendTileData field 0) alone, or does it work out
    cliffs from the heights itself? (docs/engine/terrain.md 3; engine line round 8.)

    On the probe map (maps/probe_ground.py) four pens differ only in their ring: steep and unmarked, flat and marked,
    steep and marked (the control: as our writers do it), flat and unmarked (the control). In each pen a guardian tank and
    an Imperial warrior are ordered to the point 260 north, outside the ring. Each pen's counter adds 1 for the tank and
    10 for the warrior standing there: 11 both got out, 1 only the tank, 10 only the warrior, 0 neither.

    walk expects the game to go by the bits only (steep unmarked 11, flat marked 0); the controls must read 0 and 11 or
    the probe says nothing.
    """
    from maps import probe_ground
    from parts import Mission, Script, Test, square

    TANK = 'AlliedAntiVehicleVehicleTech1'
    WARRIOR = 'JapanAntiInfantryInfantry'
    WHO = (('tank', TANK, -30.0, 1), ('warrior', WARRIOR, 30.0, 10))
    LABEL = {'steep unmarked': '陡坡没标', 'flat marked': '平地标了', 'steep marked': '陡坡标了', 'flat unmarked': '平地没标'}
    RUN = 20.0                         # all out by ~s7 (run CampGroundWalk_mcp_1104_153225)


    def _key(pen):
        return pen.title().replace(' ', '')


    def mission():
        m = Mission(name='CampGround', map=probe_ground, facts={})
        for pen in probe_ground.PENS:
            for part, template, dx, _ in WHO:
                m.put(template, pen, dx, 0, name=f'UNIT - CNV Ground {_key(pen)} {part}', role=f'{pen} {part}')
        return m


    def walk(m):
        t = Test()
        order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for pen in probe_ground.PENS:
            out = f'Test Ground {_key(pen)} Out'
            t.waypoints[out] = m.site(f'{pen} out')
            t.areas[out] = square(*m.site(f'{pen} out'), 70)
            counter = f'CNV_Ground_{_key(pen)}'
            t.counters.append((counter, LABEL[pen]))
            t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
            for part, _, _, worth in WHO:
                name = m.role(f'{pen} {part}').name
                order.append(('MOVE_NAMED_UNIT_TO', name, out))
                t.scripts.append(Script(f'Test - {counter} {part}', [('NAMED_INSIDE_AREA', name, out)],
                                        [('INCREMENT_COUNTER', worth, counter)], once=False))
        t.scripts.insert(0, Script('Test - go', [], order))
        t.expect += [(LABEL['steep unmarked'], RUN - 2, '==', 11), (LABEL['flat marked'], RUN - 2, '==', 0),
                     (LABEL['steep marked'], RUN - 2, '==', 0), (LABEL['flat unmarked'], RUN - 2, '==', 11)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=4))]
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_terrain': mission}
    CHECKS = {'engine_terrain': {'walk': walk}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def train():
    """Armoured train tests. From GO_AT, once a second, the train is sent to the next stop it has not reached (the map's
    scripts drive it, as a mission would: a move order of anyone else's -- the player's -- lasts a second at most); each
    stop's area, once it is in it, makes the next one the goal. Counters: the last stop reached, the seconds on the way
    (counted by the same once-a-second script, until the last stop), and (fight) the enemies left and the train's
    health.

    run: it follows the track, stop by stop, to the end.
    fight: on the way it shoots the conscripts by the first leg, all of them, and still gets to the end.
    brake: the brake on from BRAKE_AT to RELEASE_AT: the trip takes about that much longer.
    astray: at ASTRAY_AT it is ordered off the track (as a player might): it is back on its way, the trip as long as run's.
    """
    from parts import Script, Test, counted, square

    GO_AT = 10.0
    STOP = 60.0                                     # half-side of the area around each stop
    BRAKE_AT, RELEASE_AT, ASTRAY_AT = 15.0, 25.0, 15.0
    RUN_TRIP = 26                                   # run's seconds on the way (bench 2026-10-22)


    def track(m, t):
        train = m.role('train').name
        stops = []
        while f'stop {len(stops) + 1}' in m.marks:
            stops.append(m.mark(f'stop {len(stops) + 1}'))
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('SET_MILLISECOND_TIMER', 'Test - go timer', GO_AT)]))
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                                [('MOVE_NAMED_UNIT_TO', train, stops[0]),
                                 ('SET_MILLISECOND_TIMER', 'Test - route timer', 1.0)]))
        t.counters += [('Test Stop', '到了第几站'), ('Test Trip', '行驶秒数')]
        for k, wp in enumerate(stops):              # before 'again': it pushes the timer on
            t.scripts.append(Script(f'Test - route {k + 1}', [('TIMER_EXPIRED', 'Test - route timer'),
                                                              ('COUNTER', 'Test Stop', 2, k)],
                                    [('MOVE_NAMED_UNIT_TO', train, wp), ('INCREMENT_COUNTER', 1, 'Test Trip')],
                                    once=False))
        t.scripts.append(Script('Test - route again', [('TIMER_EXPIRED', 'Test - route timer')],
                                [('SET_MILLISECOND_TIMER', 'Test - route timer', 1.0)], once=False))
        for k, wp in enumerate(stops):
            area = f'Test Stop {k + 1}'
            t.areas[area] = square(*m.point(f'stop {k + 1}'), STOP)
            on = [('SET_COUNTER', 'Test Stop', k + 1)] + ([('MOVE_NAMED_UNIT_TO', train, stops[k + 1])]
                                                          if k + 1 < len(stops) else [])
            t.scripts.append(Script(f'Test - at stop {k + 1}', [('NAMED_INSIDE_AREA', train, area)], on))
        return len(stops)


    def run(m):
        t = Test()
        n = track(m, t)
        t.expect += [('到了第几站', 0, '==', 0, GO_AT - 2), ('到了第几站', GO_AT, 'ever==', n)]
        t.bench = [('bench_watch', dict(seconds=70, every=3, sheet=False, lines=len(t.counters), until=f'c1=={n}'))]
        return t


    def fight(m):
        t = Test()
        n = track(m, t)
        counted('Test Enemies', '敌方步兵', t, template=m.role('enemy').template, player=m.player('s1'))
        counted('Test Train Health', '列车血量', t, health=m.role('train').name)
        t.expect += [('敌方步兵', 0, 'ever==', 3), ('敌方步兵', GO_AT, 'ever==', 0), ('到了第几站', GO_AT, 'ever==', n)]
        t.bench = [('bench_watch', dict(seconds=70, every=3, sheet=False, lines=len(t.counters), until=f'c1=={n}'))]
        return t


    def brake(m):
        t = run(m)
        train = m.role('train').name
        t.scripts += [Script('Test - brake timers', [], [('SET_MILLISECOND_TIMER', 'Test - brake timer', BRAKE_AT),
                                                         ('SET_MILLISECOND_TIMER', 'Test - release timer', RELEASE_AT)]),
                      Script('Test - brake', [('TIMER_EXPIRED', 'Test - brake timer')],
                             [('NAMED_USE_COMMANDBUTTON_ABILITY', train, m.ability('train', 'brake'))]),
                      Script('Test - release', [('TIMER_EXPIRED', 'Test - release timer')],
                             [('NAMED_USE_COMMANDBUTTON_ABILITY', train, m.ability('train', 'brake'))])]
        if RUN_TRIP:
            t.expect.append(('行驶秒数', GO_AT, 'ever>=', RUN_TRIP + int(RELEASE_AT - BRAKE_AT) - 3))
        t.bench = [('bench_watch', dict(seconds=90, every=3, sheet=False, lines=len(t.counters), until='c1==3'))]
        return t


    def astray(m):
        t = run(m)
        t.scripts += [Script('Test - astray timer', [], [('SET_MILLISECOND_TIMER', 'Test - astray timer', ASTRAY_AT)]),
                      Script('Test - astray', [('TIMER_EXPIRED', 'Test - astray timer')],
                             [('MOVE_NAMED_UNIT_TO', m.role('train').name, m.mark('astray'))])]
        if RUN_TRIP:
            t.expect.append(('行驶秒数', GO_AT + 4, '<=', RUN_TRIP + 3))
        return t


    def braked_fire(m):
        """Braked at BRAKE_AT; at SEND_AT the conscripts walk up to 150 from it and it is sent to stop 1: it stays
        where it is (inside its start's area) and shoots them all."""
        t = Test()
        train = m.role('train').name
        send = BRAKE_AT + 3
        t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                  ('SET_MILLISECOND_TIMER', 'Test - brake timer', BRAKE_AT),
                                                  ('SET_MILLISECOND_TIMER', 'Test - send timer', send)]),
                      Script('Test - brake', [('TIMER_EXPIRED', 'Test - brake timer')],
                             [('NAMED_USE_COMMANDBUTTON_ABILITY', train, m.ability('train', 'brake'))]),
                      Script('Test - send', [('TIMER_EXPIRED', 'Test - send timer')],
                             [('MOVE_NAMED_UNIT_TO', e.name, m.mark('by start')) for e in m.roles('enemy')] +
                             [('MOVE_NAMED_UNIT_TO', train, m.mark('stop 1'))])]
        t.areas['Test Start'] = square(*m.point('start'), STOP)
        counted('Test Home', '还在起点', t, named=train, area='Test Start')
        counted('Test Enemies', '敌方步兵', t, template=m.role('enemy 1').template, player=m.player('s1'))
        t.expect += [('还在起点', 0, '==', 1), ('敌方步兵', send, 'ever==', 0)]
        t.bench = [('bench_watch', dict(seconds=45, every=3, sheet=False, lines=len(t.counters)))]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'train': {'run': run, 'brake': brake, 'astray': astray},
        'train_braked': {'fire': braked_fire},
        'train_fight': {'fight': fight},
    }
    return dict(CHECKS=CHECKS)


def engine_trial():
    """Engine unit test: where a unit stops when the pathfinder's search runs out (engine line round 11, part 2b;
    docs/engine/pathing.md). The map is the shell line's trial map drawn on the map page (work/mappage/trial/trial.py,
    a draft in work/: ADR 0017 -- this check reads it from there and says so when it is missing).

    Read from the program (RA3 1.13, engine line's private notes): a plain move request that cannot reach its goal --
    the search used up its cell limit, or ran out of cells -- does not fail; it walks to the cell, among those it
    looked at, nearest the goal in a straight line, and stops there. The engine model (RA3-EngineModel, find_path)
    says, on this map: from the start, the plateau and the lake shore run out of the limit although the walkable regions
    join them; the unit stops at about (1930, 1810), under the plateau's south cliff, and (990, 510), against the west
    face of the cliff wall; the ramp foot is reached (the control).

    trial: an IFV each from the start to the plateau, the lake shore and the ramp foot. Counters: 10 at the goal,
    1 by the model's stop, 100 on the way round (plateau: the ramp foot; lake shore: the wall gap).
    """
    import importlib.util
    import os

    from parts import Mission, Script, Test, square
    from checks.probe_view import open_in_view
    import labpaths

    IFV = 'AlliedAntiAirVehicleTech1'
    MAPPAGE = os.path.join(labpaths.WORK, 'mappage')
    DRAFT = os.path.join(MAPPAGE, 'trial', 'trial.py')
    # the engine line's copies of the trial map (work/mappage/<v>/<v>.py, never the shell line's original):
    # trial2 -- the west cliff wall runs into the south map edge (no slit under its cap);
    # trial3 -- the wall ends at y 400 (a 350-wide way round to the south).
    VARIANTS = {'engine_trial': 'trial', 'engine_trial2': 'trial2', 'engine_trial3': 'trial3'}
    LANES = {   # goal: (model's stop, the way round, label)
        'plateau': ((1930.0, 1810.0), 'ramp foot', '东北高地'),
        'lake shore': ((990.0, 510.0), 'wall gap', '湖南岸'),
        'ramp foot': (None, None, '坡脚'),
    }


    def _key(s):
        return s.title().replace(' ', '')


    def _draft(v='trial'):
        path = os.path.join(MAPPAGE, v, f'{v}.py')
        if not os.path.exists(path):
            raise FileNotFoundError(f'the trial map draft is not there: {path} (the map page, serve.py --new trial; '
                                    f'trial2/trial3 are the engine line\'s copies of it)')
        spec = importlib.util.spec_from_file_location(f'engine_{v}_map', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


    def _mission(v):
        m = Mission(name=f'Camp{v.title()}', map=_draft(v), facts={})
        for k, lane in enumerate(LANES):
            m.put(IFV, 'start', -60.0 + 60.0 * k, 0, role=f'{lane} ifv', name=f'UNIT - CNV Trial {_key(lane)} Ifv')
        return open_in_view(m, 'Trial')    # K5: the start is too near the map's edge


    def mission():
        return _mission('trial')


    def trial(m):
        t = Test()
        order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for lane, (stop, way, label) in LANES.items():
            wp = f'Test Trial {_key(lane)} Goal'
            t.waypoints[wp] = m.site(lane)
            order += m.order('move', [m.role(f'{lane} ifv').name], wp, crew=f'Trial{_key(lane)}')
            ifv = m.role(f'{lane} ifv').name
            counter = f'CNV_Trial_{_key(lane)}'
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
            worth = [(f'Test Trial {_key(lane)} At', square(*m.site(lane), 120.0), 10)]
            if stop is not None:
                worth.append((f'Test Trial {_key(lane)} Stop', square(*stop, 150.0), 1))
                worth.append((f'Test Trial {_key(lane)} Way', square(*m.site(way), 150.0), 100))
            for k, (area, box, n) in enumerate(worth):
                t.areas[area] = box
                t.scripts.append(Script(f'Test - {counter} {k}', [('NAMED_INSIDE_AREA', ifv, area)],
                                        [('INCREMENT_COUNTER', n, counter)], once=False))
        t.scripts.insert(0, Script('Test - go', [], order))
        t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=3))]
        t.expect = [('坡脚', 0, 'ever==', 10, 60)]          # the control; plateau / lake shore are read, not judged
        return t


    BANDS_X = ((0.0, 500.0), (500.0, 800.0), (800.0, 950.0), (950.0, 1050.0), (1050.0, 3000.0))   # 1 .. 10 000
    BANDS_Y = ((0.0, 300.0), (300.0, 600.0), (600.0, 900.0), (900.0, 1300.0), (1300.0, 3000.0))


    def where(m):
        """Where the lake shore IFV stops: an x counter and a y counter, the strip it is in worth 1, 10, ... 10 000."""
        t = Test()
        lane = 'lake shore'
        wp = 'Test Trial LakeShore Goal'
        t.waypoints[wp] = m.site(lane)
        order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        order += m.order('move', [m.role(f'{lane} ifv').name], wp, crew='TrialLakeShore')
        ifv = m.role(f'{lane} ifv').name
        for axis, bands in (('X', BANDS_X), ('Y', BANDS_Y)):
            counter = f'CNV_Trial_Lake{axis}'
            t.counters.append((counter, f'湖南岸{axis}'))
            t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
            for k, (a, b) in enumerate(bands):
                area = f'Test Trial Lake {axis}{k}'
                t.areas[area] = [(a, 0.0), (b, 0.0), (b, 3000.0), (a, 3000.0)] if axis == 'X' else \
                    [(0.0, a), (3000.0, a), (3000.0, b), (0.0, b)]
                t.scripts.append(Script(f'Test - {counter} {k}', [('NAMED_INSIDE_AREA', ifv, area)],
                                        [('INCREMENT_COUNTER', 10 ** k, counter)], once=False))
        t.scripts.insert(0, Script('Test - go', [], order))
        t.bench = [('bench_watch', dict(seconds=45, every=3, sheet=False, lines=2))]
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {b: (lambda v=v: _mission(v)) for b, v in VARIANTS.items()}
    CHECKS = {b: {'trial': trial, 'where': where} for b in VARIANTS}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_waypath():
    """Engine probe for the waypoint paths (Sim.order_follow: *_FOLLOW_WAYPOINTS): mission missions/waypath_bench.py,
    convoy trucks (speed 50) in the west field and an L of waypoints A (+150, -150) -> B (+450, -150) -> C (+450, +150).
    Each check writes its own waypoints on A, B, C (the check layer may not put the mission's on a path) and labels them.

    Counters: 段k = the last of truck k's boxes (40 half-side) it was in: 1 A, 2 B, 3 C (0 none yet); 近B = how near
    truck 1 came to B: 4 within 10, 3 within 25, 2 within 50, 1 within 100 (nested squares; the highest it reached).

      line   NAMED_FOLLOW_WAYPOINTS truck 1 'CNVRoad' (A -> B -> C) at 1 s. [sim: 段1 1 -> 2 -> 3, then stays; 近B 4 --
             it walks to each waypoint, no corner cut (INFERRED)]
      exact  the same with NAMED_FOLLOW_WAYPOINTS_EXACT. [sim: as line; the two differ on the bench by 近B, if at all]
      near   truck 1 first sent to N (by B, MOVE_TEAM_TO), the path at 15 s. [sim: B nearest -- 段1 2 -> 3, A never]
      loop   the path linked C -> A as well (a ring), truck 1 at 1 s. [sim: 段1 1 2 3 1 2 3 ... round and round]
      team   TEAM_FOLLOW_WAYPOINTS team W23 (trucks 2, 3) 'CNVRoad' asTeam=1 at 1 s; boxes 100 half-side here. [sim:
             joined at A (nearest the team's middle), group legs: both 1 -> 2 -> 3]
      start  NAMED_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT truck 2 'CNVRoad' from B at 1 s (A is nearest it, 250 off; its
             straight run to B passes 50 north of A's box). [sim: 段2 0 -> 2 -> 3, A never]
      texact TEAM_FOLLOW_WAYPOINTS_EXACT team W23 'CNVRoad' asTeam=1 at 1 s; boxes 100. [sim: as team]

    Simulator 11-10 (round 143, work/logs/a143_waypath_sim.log; 段 boxes 40): line / exact s5 段1 1, s11 2 (近B 4), s17 3;
    near s5 1 (passing A on the way to N), s17 2, s23 3 (A never again: joined at B); loop 1 2 3 every ~20 s, round and
    round; team (boxes 40 then) truck 3 never in A's or B's box -- its group legs ran 100 aside: boxes 100 since.

    读数 (bench 2026-11-10, after package._drop_dangling_links -- the first line / exact runs had the container's stale
    links on our waypoint ids, 10 -> 9, 8 -> 7 ...: line went C -> B -> C ..., exact forked at A to N -- the same fork,
    the two runs took different links: random -- and on through unlabelled waypoints N, C, B, A to the camera's)
      line   段1 s3 1, s9 2 (近B 4), s15 3, stays.             exact  the same, second by second: no corner cut either.
      near   段1 s3 1 (on the way to N), s15 2 (近B 3, s16 4), s21 3; A never again: joined at B.
      loop   段1 1 2 3 at s3 9 15, s23 29 35, s43 49 55, s63 70 76, s84 90: a lap 20-21 s, round and round.
      team   段2 s3 1, s10 2, s17 3; 段3 s5 1, s10 2, s14 3: both within 100 of every waypoint (each to the waypoint plus
             its offset from the team's middle, ±75), the one ahead on the last leg (truck 3) there 3 s first.
      start  (round 151) CampPathStart_mcp_1110_211156: 段2 0 s1-s8, 2 s9, 3 s15 on: straight to B, A never.
      texact (round 151) CampPathTexact_mcp_1110_211438: 段2 s3 1, s10 2, s17 3; 段3 s5 1, s10 2, s14 3 -- team's
             readings second by second: _EXACT changes nothing here either.
    Simulator after the round-144 fix (Generals m_moveAsGroup offsets, the first there moves the team on): every reading
    LAG 2 s later (loop drifts to 3 s by the third lap); tests/test_simbench.py test_waypath_*.
    """
    from parts import Script, Test, square
    from checks.engine_waypath import PATH, _at, _road

    RINGS = (100.0, 50.0, 25.0, 10.0)
    RUN = {'line': 40.0, 'exact': 40.0, 'near': 50.0, 'loop': 90.0, 'team': 45.0, 'start': 45.0, 'texact': 45.0}


    def _legs(t, m, trucks, half=40.0):
        for k in trucks:
            name, counter = m.role(f'truck {k}').name, f'CNV_Waypath_Leg{k}'
            t.counters.append((counter, f'段{k}'))
            for i, p in enumerate(PATH, 1):
                area = f'Test Waypath Box {p}'
                t.areas[area] = square(*m.point(p), half)
                t.scripts.append(Script(f'Test - {counter} {p}', [('NAMED_INSIDE_AREA', name, area)],
                                        [('SET_COUNTER', counter, i)], once=False))


    def _near_b(t, m):
        name, counter = m.role('truck 1').name, 'CNV_Waypath_NearB'
        t.counters.append((counter, '近B'))
        for level, r in enumerate(RINGS, 1):
            area = f'Test Waypath B {r:g}'
            t.areas[area] = square(*m.point('B'), r)
            t.scripts.append(Script(f'Test - {counter} {r:g}', [('NAMED_INSIDE_AREA', name, area)],
                                    [('SET_COUNTER', counter, level)]))


    def _watch(t, run, every=1.0):
        t.bench = [('bench_watch', dict(seconds=run, every=every, sheet=False, lines=len(t.counters)))]


    def _one(m, action, run):
        t = Test()
        _road(t, m, 'CNVRoad')
        _at(t, 'go', 1.0, [(action, m.role('truck 1').name, 'CNVRoad')])
        _legs(t, m, (1,))
        _near_b(t, m)
        _watch(t, run)
        return t


    def line(m):
        return _one(m, 'NAMED_FOLLOW_WAYPOINTS', RUN['line'])


    def exact(m):
        return _one(m, 'NAMED_FOLLOW_WAYPOINTS_EXACT', RUN['exact'])


    def near(m):
        t = Test()
        _road(t, m, 'CNVRoad')
        _at(t, 'go', 1.0, m.order('move', [m.role('truck 1').name], m.mark('N'), crew='W1'))
        _at(t, 'path', 15.0, [('NAMED_FOLLOW_WAYPOINTS', m.role('truck 1').name, 'CNVRoad')])
        _legs(t, m, (1,))
        _near_b(t, m)
        _watch(t, RUN['near'])
        return t


    def loop(m):
        t = Test()
        _road(t, m, 'CNVRing', loop=True)
        _at(t, 'go', 1.0, [('NAMED_FOLLOW_WAYPOINTS', m.role('truck 1').name, 'CNVRing')])
        _legs(t, m, (1,))
        _watch(t, RUN['loop'])
        return t


    def team(m):
        t = Test()
        _road(t, m, 'CNVRoad')
        _at(t, 'go', 1.0, [('TEAM_FOLLOW_WAYPOINTS', m.crew('W23'), 'CNVRoad', 1, 0)])
        _legs(t, m, (2, 3), half=100.0)         # a group's legs end apart (order_group): boxes of 100
        _watch(t, RUN['team'])
        return t


    def start(m):
        t = Test()
        _road(t, m, 'CNVRoad')
        _at(t, 'go', 1.0, [('NAMED_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT', m.role('truck 2').name, 'CNVRoad',
                            'Test Waypath B')])
        _legs(t, m, (2,))
        _watch(t, RUN['start'])
        return t


    def texact(m):
        t = Test()
        _road(t, m, 'CNVRoad')
        _at(t, 'go', 1.0, [('TEAM_FOLLOW_WAYPOINTS_EXACT', m.crew('W23'), 'CNVRoad', 1)])
        _legs(t, m, (2, 3), half=100.0)
        _watch(t, RUN['texact'])
        return t


    def tstart(m):
        """TEAM_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT team W23 'CNVRoad' (1, 1: s04's flags) from C, the last (from B
        the boxes of 100 take A on the way); boxes 100."""
        t = Test()
        _road(t, m, 'CNVRoad')
        _at(t, 'go', 1.0, [('TEAM_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT', m.crew('W23'), 'CNVRoad', 1, 1,
                            'Test Waypath C')])
        _legs(t, m, (2, 3), half=100.0)
        _watch(t, RUN['texact'])
        return t


    CHECKS = {'engine_waypath': {'line': line, 'exact': exact, 'near': near, 'loop': loop, 'team': team,
                                 'start': start, 'texact': texact, 'tstart': tstart}}
    return dict(CHECKS=CHECKS)


BENCHES = (
    engine_a01sq, engine_air, engine_airin, engine_bits, blackcanyon,
    engine_block, engine_column, engine_dam, engine_drop, engine_dynamics,
    engine_facewp, fence, engine_float, engine_formation_player, engine_freefall,
    engine_hull, jammer, engine_jet, engine_jet_probe, engine_land,
    lock, engine_pace, engine_pace_placed, engine_paths, engine_pull,
    reroute, engine_runoffmap, engine_seal, engine_spots, engine_stance,
    engine_terrain, train, engine_trial, engine_waypath,
)
