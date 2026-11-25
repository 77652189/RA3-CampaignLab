"""Script control checks and their inline scenes."""

FACE = [(3700.0, 0.0, True), (3900.0, 1.5707963, True), (4100.0, 3.1415927, False), (4300.0, -2.3561945, False)]
FACE_Y = 4700.0


def engine_acts2():
    """Retail-campaign actions, batch 2 (round 212; the gaps of `inventory_retail.py --part 脚本动作`, the program read in
    work/re/d115_script_semantics.md 12, 13, 14, 27). Missions on maps/probe_border.py as checks/engine_acts.py (its SLOT
    places, clear of probe_range's lanes and start); enemies on Soviet_4. What the simulator predicts is in brackets.

      seq     UNIT_EXECUTE_SEQUENTIAL_SCRIPT at 1 s, the scripts subroutines:
              run: the player's 'runner' with 'Test - Seq Run' = [+1, MOVE <This Object> to P (300 east), +10, MOVE it
                   back to R (where it stood), +100]. (The catalog's action takes no loop count: a first build with a
                   third argument was refused by the writer.)
              queue: 'queuer' given 'Test - Seq Q1' = [MOVE <This Object> to Q (300 east), +1] and then 'Test - Seq Q2'
                   = [+10], in one script.
              sit: 'sitter' with 'Test - Seq Sit' = [+1, UNIT_IDLE_FOR_SECONDS <This Object> 5, +10].
              跑 / 排 / 等 = the three counters; 位 (every frame) = 1 runner in P, 2 runner in R
              [simulator, d115 14: one action a frame once the unit is idle, the queue's second script after the first,
              the idle a wait of 75 frames: 跑 1 -> 11 at P -> 111 back at R and no more; 排 0 -> 11 at Q (10 only after
              the move: not 10 at once); 等 1 -> 11 ~5 s later]
      BENCH 11-13 (round 212, run_queue; tests/test_simbench.py test_acts_seq_as_the_bench): 跑 / 排 / 等 / 位
        s1 1 0 11 0 | s2 1 0 11 1 | s3-s4 11 11 11 1 | s5-s6 11 11 11 0 | s7 11 11 11 2 | s8-s41 111 11 11 2.
        Against the prediction: 等 11 from the first second -- the IDLE_FOR_SECONDS step held the next back not at all
        (d115 14 has IDLE_FOR_* write the record's wait; on a standing unit it did not). The rest as predicted; the
        simulator fixed (engine.orders.seq keeps no wait).
      more    garrison: crew G1 (7 conscripts) and crew Frogs1 (two of the player's Bullfrogs, 5 places each); crew G2 (6)
                   and Frogs2 (one); TEAM_GARRISON_TEAM_INSTANTLY(G1, Frogs1), (G2, Frogs2) at 2 s; NAMED_KILL the first
                   Bullfrog of Frogs1 at KILL (KillPassengersOnDeath: its passengers die).
              force: the player's 'gunner' and 'gunner b' (conscripts, NO_ATTACK till 2 s) each 100 from a Soviet_4
                   conscript 'lure' / 'lure b' (NO_ATTACK); at 2 s NAMED_FORCE_ATTACK_WAYPOINT(gunner, the ground 100
                   on its other side), gunner b nothing; NAMED_STOP(gunner) at STOP.
              kill: UNIT_KILL_ALL_IN_AREA(Player_1, K) at KILL; in K the player's tank 'kin' and power plant 'kplant',
                   Soviet_4's tank 'kfoe'; the player's 'kout' 250 east, outside.
              move: crew Mover (one tank) ATTACK_MOVE_TEAM_TO_NAMED_OBJECT the player's 'post' (300 east) at 2 s; the
                   post moved 400 north at 3 s.
              reveal: Soviet_4's 'hide' (crew Hide) far from the player's eyes; MAP_REVEAL_PERMANENTLY_IN_TRIGGER(its area,
                   Player_1, 'CNV Act Rev') at KILL, MAP_UNDO_REVEAL_PERMANENTLY_IN_TRIGGER at UNDO.
              驻 = G1 inside (ones) + G2 inside (tens) + G1 alive (hundreds); 诱血 = lure's health %
              旗 (every frame) = 1 NAMED_ATTACKED_BY_OBJECTTYPE(lure b, conscript) 2 (lure, ...) 4 kin alive 8 kfoe alive
                16 kplant alive 32 kout alive 64 Mover in the post's first place 128 in its second
                256 TEAM_DISCOVERED(Player_1, Hide)
              [simulator, d115 12 / 13 / 27: 驻 700 -> 757 (the room asked: 5 of G2's 6) -> 353 (dealt out 4 + 3, the
              first Bullfrog 4); 诱血 100 till STOP, then falling; 旗 60 -> 61 at 2 s (gunner b fires, gunner busy at the
              ground) -> 40+1 at KILL (kin, kplant dead) + 64 (the post's place at the order) + 256 KILL..UNDO, 2 after
              STOP]
      BENCH 11-13 (round 212, run_queue; tests/test_simbench.py test_acts_more_as_the_bench): 驻 / 诱血 / 旗
        s1-s2 767 100 61 | s3-s4 767 100 125 | s5-s11 363 100 361 | s12 363 85 363 | s13-s19 363 75..15 107 | s20 5 106 |
        s21-s28 0 106 | s29-s31 0 104. The bench's seconds run 1-2 s ahead. Against the prediction: the room is not
        asked (G2's six all in one five-place Bullfrog, as TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY: 767, not 757);
        the dealing out confirmed (the first Bullfrog's kill took 4 of G1's 7: 363). The rest as predicted. The
        simulator fixed (sim.Sim.act TEAM_GARRISON_TEAM_INSTANTLY). Bits 1 / 2 stay up ~8 s after lure b's / the lure's
        death on the bench (the simulator drops them at the death; round 210's dying-unit gap, not this batch's).
    """
    from maps import probe_border
    from parts import Mission, Script, Test, square, status
    import checks.engine_scripts8 as s8

    TANK, PLANT, MAN, FROG = 'AlliedAntiVehicleVehicleTech1', 'SovietPowerPlant', 'SovietAntiInfantryInfantry', \
        'SovietAntiAirShip'
    O = (1300.0, 4300.0)                            # probe_border's 'stop row'
    RUN = {'seq': 40.0, 'more': 30.0}
    SEQ = {'runner': (600.0, 4000.0), 'queuer': (2200.0, 4000.0), 'sitter': (3800.0, 4000.0)}
    LEG = 300.0
    G = {'G1': (7, 2, (600.0, 4000.0)), 'G2': (6, 1, (1400.0, 4000.0))}     # crew: men, Bullfrogs, place
    GUN = {'gunner': (2200.0, 4000.0), 'gunner b': (3000.0, 4000.0)}
    K = (3800.0, 4000.0)
    MOVER, POST, POST2 = (600.0, 4700.0), (900.0, 4700.0), (900.0, 4300.0)
    HIDE = (4500.0, 3000.0)
    KILL, STOP, UNDO = 6.0, 12.0, 14.0


    def _n(part):
        return f'UNIT - CNV Act2 {part.title()}'


    def _put(m, template, x, y, **kw):
        m.put(template, 'stop row', x - O[0], y - O[1], **kw)


    def _unit(m, role, side, template, x, y, crew=None):
        props = {'originalOwner': m.crew(crew, side=side)} if crew else {}
        _put(m, template, x, y, side=side, angle=0.0 if side == 'p1' else 3.1416, name=_n(role), role=role, props=props)


    def mission_seq():
        m = Mission(name='CampActsS', map=probe_border, units=[], facts={})
        m.spawns |= {TANK}
        for role, (x, y) in SEQ.items():
            _unit(m, role, 'p1', TANK, x, y)
            m.waypoint(f'{role} to', f'Test Act2 {role.title()} To', 'stop row', x + LEG - O[0], y - O[1])
            m.waypoint(f'{role} back', f'Test Act2 {role.title()} Back', 'stop row', x - O[0], y - O[1])
        return m


    def seq(m):
        t = Test()
        me = '<This Object>'
        run, q, sit = 'CNV_Seq_Run', 'CNV_Seq_Q', 'CNV_Seq_Sit'
        t.scripts += [
            Script('Test - Seq Run', [], [('INCREMENT_COUNTER', 1, run), ('MOVE_NAMED_UNIT_TO', me, m.mark('runner to')),
                                          ('INCREMENT_COUNTER', 10, run),
                                          ('MOVE_NAMED_UNIT_TO', me, m.mark('runner back')),
                                          ('INCREMENT_COUNTER', 100, run)], sub=True),
            Script('Test - Seq Q1', [], [('MOVE_NAMED_UNIT_TO', me, m.mark('queuer to')), ('INCREMENT_COUNTER', 1, q)],
                   sub=True),
            Script('Test - Seq Q2', [], [('INCREMENT_COUNTER', 10, q)], sub=True),
            Script('Test - Seq Sit', [], [('INCREMENT_COUNTER', 1, sit), ('UNIT_IDLE_FOR_SECONDS', me, 5.0),
                                          ('INCREMENT_COUNTER', 10, sit)], sub=True)]
        s8.at(t, 'seq', 1.0, [('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', _n('runner'), 'Test - Seq Run'),
                              ('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', _n('queuer'), 'Test - Seq Q1'),
                              ('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', _n('queuer'), 'Test - Seq Q2'),
                              ('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', _n('sitter'), 'Test - Seq Sit')])
        for c, label in ((run, '跑'), (q, '排'), (sit, '等')):
            t.counters.append((c, label))
        t.areas['Test Act2 P'] = square(*m.point('runner to'), 80.0)
        t.areas['Test Act2 R'] = square(*m.point('runner back'), 80.0)
        s8.total(t, 'CNV_Seq_Where', '位', [(1, ('NAMED_INSIDE_AREA', _n('runner'), 'Test Act2 P')),
                                           (2, ('NAMED_INSIDE_AREA', _n('runner'), 'Test Act2 R'))])
        s8.watch(t, RUN['seq'])
        return t


    def mission_more():
        m = Mission(name='CampActsM', map=probe_border, units=[], facts={})
        m.spawns |= {TANK, PLANT, MAN, FROG}
        for crew, (men, frogs, (x, y)) in G.items():
            for k in range(frogs):
                _unit(m, f'{crew} frog {k}', 'p1', FROG, x + 160.0 * k, y, crew=f'Frogs{crew[1]}')
            for k in range(men):
                _unit(m, f'{crew} man {k}', 'p1', MAN, x - 100.0 + 35.0 * k, y - 90.0, crew=crew)
        for k, (role, (x, y)) in enumerate(GUN.items()):
            _unit(m, role, 'p1', MAN, x, y)
            _unit(m, 'lure' + role[6:], 's4', MAN, x + 100.0, y)
            m.waypoint(f'{role} at', f'Test Act2 {role.title()} At', 'stop row', x - 100.0 - O[0], y - O[1])
        _unit(m, 'kin', 'p1', TANK, K[0] - 60.0, K[1])
        _unit(m, 'kplant', 'p1', PLANT, K[0] + 40.0, K[1] + 60.0)
        _unit(m, 'kfoe', 's4', TANK, K[0], K[1] - 80.0)
        _unit(m, 'kout', 'p1', TANK, K[0] + 250.0, K[1])
        _unit(m, 'mover', 'p1', TANK, *MOVER, crew='Mover')
        _unit(m, 'post', 'p1', TANK, *POST)
        m.waypoint('post to', 'Test Act2 Post To', 'stop row', POST2[0] - O[0], POST2[1] - O[1])
        _unit(m, 'hide', 's4', TANK, *HIDE, crew='Hide')
        return m


    def more(m):
        t = Test()
        p1 = m.player()
        na = status('NO_ATTACK')
        men = lambda crew: [_n(f'{crew} man {k}') for k in range(G[crew][0])]                  # noqa: E731
        held = [_n(r) for r in ('gunner', 'gunner b', 'lure', 'lure b', 'kin', 'kfoe', 'kout', 'kplant', 'mover', 'post',
                                'hide', 'G1 frog 0', 'G1 frog 1', 'G2 frog 0')] + men('G1') + men('G2')
        t.areas['Test Act2 K'] = square(*K, 150.0)
        t.areas['Test Act2 Post A'] = square(*POST, 100.0)
        t.areas['Test Act2 Post B'] = square(*POST2, 100.0)
        t.areas['Test Act2 Rev'] = square(*HIDE, 150.0)
        t.scripts.append(Script('Test - Act2 start', [], [('UNIT_CHANGE_OBJECT_STATUS', u, na, 1) for u in held]))
        s8.at(t, 'two', 2.0, [('TEAM_GARRISON_TEAM_INSTANTLY', m.teams['G1'], m.teams['Frogs1']),
                              ('TEAM_GARRISON_TEAM_INSTANTLY', m.teams['G2'], m.teams['Frogs2']),
                              ('UNIT_CHANGE_OBJECT_STATUS', _n('gunner'), na, 0),
                              ('UNIT_CHANGE_OBJECT_STATUS', _n('gunner b'), na, 0),
                              ('NAMED_FORCE_ATTACK_WAYPOINT', _n('gunner'), m.mark('gunner at')),
                              ('ATTACK_MOVE_TEAM_TO_NAMED_OBJECT', m.teams['Mover'], _n('post'))])
        s8.at(t, 'three', 3.0, [('MOVE_NAMED_UNIT_TO', _n('post'), m.mark('post to'))])
        s8.at(t, 'kill', KILL, [('NAMED_KILL', _n('G1 frog 0')), ('UNIT_KILL_ALL_IN_AREA', p1, 'Test Act2 K'),
                                ('MAP_REVEAL_PERMANENTLY_IN_TRIGGER', 'Test Act2 Rev', p1, 'CNV Act Rev')])
        s8.at(t, 'stop', STOP, [('NAMED_STOP', _n('gunner'))])
        s8.at(t, 'undo', UNDO, [('MAP_UNDO_REVEAL_PERMANENTLY_IN_TRIGGER', 'CNV Act Rev')])
        inside = lambda crew, w: [(w, ('UNIT_HAS_OBJECT_STATUS', u, status('ENCLOSED'))) for u in men(crew)]   # noqa: E731
        s8.total(t, 'CNV_Act2_In', '驻', inside('G1', 1) + inside('G2', 10)
                 + [(100, ('NAMED_NOT_DESTROYED', u)) for u in men('G1')])
        t.counters.append(('CNV_Act2_HP', '诱血'))
        t.scripts.append(Script('Test - CNV_Act2_HP', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', _n('lure'),
                                                            'CNV_Act2_HP')], once=False))
        s8.total(t, 'CNV_Act2_Flags', '旗', [
            (1, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('lure b'), MAN)),
            (2, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('lure'), MAN)),
            (4, ('NAMED_NOT_DESTROYED', _n('kin'))), (8, ('NAMED_NOT_DESTROYED', _n('kfoe'))),
            (16, ('NAMED_NOT_DESTROYED', _n('kplant'))), (32, ('NAMED_NOT_DESTROYED', _n('kout'))),
            (64, ('NAMED_INSIDE_AREA', _n('mover'), 'Test Act2 Post A')),
            (128, ('NAMED_INSIDE_AREA', _n('mover'), 'Test Act2 Post B')),
            (256, ('TEAM_DISCOVERED', p1, m.teams['Hide']))])
        s8.watch(t, RUN['more'])
        return t


    MISSION = {'engine_acts_seq': mission_seq, 'engine_acts_more': mission_more}
    CHECKS = {'engine_acts_seq': {'seq': seq}, 'engine_acts_more': {'more': more}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_acts5():
    """Retail-campaign actions, batch 5 (round 215; the gaps of `inventory_retail.py --part 脚本动作`): model conditions by
    number, a player's whole hand-over, the player's own auto-acquire, a move to the nearest of a type, a guard from a
    point. Mission on maps/probe_border.py as checks/engine_acts4.py ('stop row' offsets, enemies on Soviet_4 / 5, nobody
    fires unless told). What the simulator predicts is in brackets.

      mc    the player's conscripts mc1 / mc2. 1 s: UNIT_SET_MODELCONDITION(mc1, 1, 1), (mc2, 2, 1); 8 s: (mc1, 1, 0),
            (mc2, 3, 1). The number read as USER_<n> (ModelState.xsd's USER_1 .. USER_10; a08's saluting conscripts are
            set 2 off, the conscript's STATE_Saluting is USER_2).
              状 (every frame) = UNIT_HAS_MODELCONDITION mc1 USER_1 1, mc1 USER_2 2, mc2 USER_2 4, mc2 USER_1 8,
                mc2 USER_3 16
      own   Soviet_5's tank xt (210 from Soviet_4's plant xplant) and conscript xm. 6 s: PLAYER_TRANSFER_OWNERSHIP_PLAYER(
            Soviet_5, Player_1) (a05's order: from, to).
      aaq   the player's tank paq 210 from Soviet_4's plant pplant. 2 s: PLAYER_ALLOW_AI_AUTOACQUIRE(Player_1, 1). xt joins
            the player at 6 s: does the player's switch reach a unit it gets later?
              旗 (every frame) = NAMED_OWNED_BY_PLAYER(P1, xt) 1 (P1, xm) 2 + NAMED_ATTACKED_BY_OBJECTTYPE(pplant, tank) 4
                (xplant, tank) 8 + NAMED_NOT_DESTROYED(gfoe) 16
      near  crew Mv (two conscripts at N0); the player's barracks nb (450 south of N0) and fb (650 east). 1 s and 12 s:
            TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE(Mv, AlliedBarracks); 10 s: NAMED_DELETE nb.
      guard crew Gd (two tanks); area 'Test Act5 Garea' (800 square), waypoint 'gd from' inside it, 100 in from its north
            edge's middle. 1 s: TEAM_GUARD_AREA_FROM_POSITION(Gd, area, 'gd from'); 15 s: Soviet_4's
            conscript gfoe teleported into the area, 600 south of 'gd from'.
              位 (every frame) = Mv's men by nb (ones) by fb (tens) + Gd's tanks by 'gd from' (hundreds) by the area's
                middle (thousands)
              守 (every frame) = Gd's tanks in the area (ones) + gfoe in the area (tens)
      The second run added: 状 +32 / 64 / 128 = NAMED_OWNED_BY_PLAYER(Soviet_5, mc1 / paq / ym), ym Soviet_6's conscript
      with PLAYER_TRANSFER_OWNERSHIP_PLAYER(Soviet_6, Soviet_5) at 20 s; 守 +100 gfoe attacked by a tank, +1000 gfoe within
      300 of 'gd from'.
      [simulator before the bench: 状 0 (UNIT_SET_MODELCONDITION unknown); 旗 16; 位 0 (both moves unknown); 守 0 -> 10]
      BENCH 11-13 (round 215, run_queue twice, CampActsVActs_mcp_1113_232329 and the next; the same readings both times;
      tests/test_simbench.py test_acts_v_as_the_bench):
        状 / 旗 / 位 / 守  s1-s2 5 20 0 0 | s3 5 20 1 0 | s4 5 20 2 0 | s5 5 20 102 0 | s6 5 20 202 2 | s7-s13 20 20 202 2 |
        s14 20 20 202 12 | s15-s18 20 20 200 12 | s19-s32 20 20 220 12 | s33-s41 20 16 220 12. The bench's seconds run ~1
        behind the scripts' (the 15 s teleport at s14).
        Model condition: n is USER_n (1, 2, 3), 0 clears. Auto-acquire: paq fired on pplant (4). Nearest: Mv to nb, after
        nb's delete and the second order to fb. Guard from position: both tanks to 'gd from' and there to the end, never
        the area's middle; gfoe in the area 600 off was never hit by a tank nor came near, and was dead at s33 (the
        simulator: dead at 36 s, not chased). Hand-over: NOTHING changed hands -- Soviet_5 -> Player_1, Soviet_6 ->
        Soviet_5, nor the other way (Player_1's units never Soviet_5's), so xt's late auto-acquire was never asked
        (handoff hypothesis: Soviet_5 / 6 have no team on this map, TEAMS has p1 / s1 / s4 only).
    """
    from maps import probe_border
    from parts import Mission, Script, Test, square
    import checks.engine_scripts8 as s8

    TANK, PLANT, MAN, BARRACKS = 'AlliedAntiVehicleVehicleTech1', 'SovietPowerPlant', 'SovietAntiInfantryInfantry', \
        'AlliedBarracks'
    O = (1300.0, 4300.0)                            # probe_border's 'stop row'
    RUN = 40.0
    MC = {'mc1': (600.0, 4000.0), 'mc2': (600.0, 4700.0)}
    PAQ, XT, XM, YM = (1400.0, 4000.0), (3800.0, 4000.0), (3800.0, 4700.0), (4600.0, 4350.0)
    N0 = (2800.0, 2100.0)
    NB, FB = (N0[0], N0[1] + 450.0), (N0[0] + 650.0, N0[1])
    GD, GAREA, GFROM = (3700.0, 2000.0), (4200.0, 2700.0), (4200.0, 2400.0)
    GFOE, GFOE_TO = (3000.0, 4350.0), (4200.0, 3000.0)
    AREA = 'Test Act5 Garea'


    def _n(part):
        return f'UNIT - CNV Act5 {part.title()}'


    def _unit(m, role, side, template, x, y, crew=None):
        props = {'originalOwner': m.crew(crew, side=side)} if crew else {}
        m.put(template, 'stop row', x - O[0], y - O[1], side=side, angle=0.0 if side == 'p1' else 3.1416,
              name=_n(role), role=role, props=props)


    def mission():
        m = Mission(name='CampActsV', map=probe_border, units=[], facts={})
        m.spawns |= {TANK, PLANT, MAN, BARRACKS}
        for role, at in MC.items():
            _unit(m, role, 'p1', MAN, *at)
        _unit(m, 'paq', 'p1', TANK, *PAQ)
        _unit(m, 'pplant', 's4', PLANT, PAQ[0] + 210.0, PAQ[1])
        _unit(m, 'xt', 's5', TANK, *XT)
        _unit(m, 'xplant', 's4', PLANT, XT[0] + 210.0, XT[1])
        _unit(m, 'xm', 's5', MAN, *XM)
        _unit(m, 'ym', 's6', MAN, *YM)
        for k in range(2):
            _unit(m, f'mv {k}', 'p1', MAN, N0[0], N0[1] - 30.0 + 60.0 * k, crew='Mv')
            _unit(m, f'gd {k}', 'p1', TANK, GD[0], GD[1] - 40.0 + 80.0 * k, crew='Gd')
        _unit(m, 'nb', 'p1', BARRACKS, *NB)
        _unit(m, 'fb', 'p1', BARRACKS, *FB)
        _unit(m, 'gfoe', 's4', MAN, *GFOE)
        for spot, at in (('gd from', GFROM), ('gfoe to', GFOE_TO)):
            m.waypoint(spot, f'Test Act5 {spot.title()}', 'stop row', at[0] - O[0], at[1] - O[1])
        return m


    def acts(m):
        t = Test()
        p1, s5, s6 = m.player(), m.player('s5'), m.player('s6')
        t.areas['Test Act5 Close'] = square(*GFROM, 300.0)
        t.areas[AREA] = square(*GAREA, 400.0)
        t.areas['Test Act5 Nb'] = square(*NB, 250.0)
        t.areas['Test Act5 Fb'] = square(*FB, 250.0)
        t.areas['Test Act5 From'] = square(*GFROM, 150.0)
        t.areas['Test Act5 Mid'] = square(*GAREA, 150.0)
        near = ('TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE', m.teams['Mv'], BARRACKS)
        s8.at(t, 'a1', 1.0, [('UNIT_SET_MODELCONDITION', _n('mc1'), 1, 1), ('UNIT_SET_MODELCONDITION', _n('mc2'), 2, 1),
                             near, ('TEAM_GUARD_AREA_FROM_POSITION', m.teams['Gd'], AREA, m.mark('gd from'))])
        s8.at(t, 'a2', 2.0, [('PLAYER_ALLOW_AI_AUTOACQUIRE', p1, 1)])
        s8.at(t, 'a6', 6.0, [('PLAYER_TRANSFER_OWNERSHIP_PLAYER', s5, p1)])
        s8.at(t, 'a8', 8.0, [('UNIT_SET_MODELCONDITION', _n('mc1'), 1, 0), ('UNIT_SET_MODELCONDITION', _n('mc2'), 3, 1)])
        s8.at(t, 'a10', 10.0, [('NAMED_DELETE', _n('nb'))])
        s8.at(t, 'a12', 12.0, [near])
        s8.at(t, 'a20', 20.0, [('PLAYER_TRANSFER_OWNERSHIP_PLAYER', s6, s5)])
        s8.at(t, 'a15', 15.0, [('UNIT_TELEPORT_TO_WAYPOINT', _n('gfoe'), m.mark('gfoe to'))])
        s8.total(t, 'CNV_Act5_Mc', '状', [(w, ('UNIT_HAS_MODELCONDITION', _n(u), c)) for w, u, c in (
            (1, 'mc1', 'USER_1'), (2, 'mc1', 'USER_2'), (4, 'mc2', 'USER_2'), (8, 'mc2', 'USER_1'), (16, 'mc2', 'USER_3'))]
            + [(w, ('NAMED_OWNED_BY_PLAYER', s5, _n(u))) for w, u in ((32, 'mc1'), (64, 'paq'), (128, 'ym'))])
        s8.total(t, 'CNV_Act5_Flags', '旗', [
            (1, ('NAMED_OWNED_BY_PLAYER', p1, _n('xt'))), (2, ('NAMED_OWNED_BY_PLAYER', p1, _n('xm'))),
            (4, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('pplant'), TANK)),
            (8, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('xplant'), TANK)),
            (16, ('NAMED_NOT_DESTROYED', _n('gfoe')))])
        mv, gd = [_n(f'mv {k}') for k in range(2)], [_n(f'gd {k}') for k in range(2)]
        s8.total(t, 'CNV_Act5_Where', '位', [(1, ('NAMED_INSIDE_AREA', u, 'Test Act5 Nb')) for u in mv]
                 + [(10, ('NAMED_INSIDE_AREA', u, 'Test Act5 Fb')) for u in mv]
                 + [(100, ('NAMED_INSIDE_AREA', u, 'Test Act5 From')) for u in gd]
                 + [(1000, ('NAMED_INSIDE_AREA', u, 'Test Act5 Mid')) for u in gd])
        s8.total(t, 'CNV_Act5_Guard', '守', [(1, ('NAMED_INSIDE_AREA', u, AREA)) for u in gd]
                 + [(10, ('NAMED_INSIDE_AREA', _n('gfoe'), AREA)),
                    (100, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('gfoe'), TANK)),
                    (1000, ('NAMED_INSIDE_AREA', _n('gfoe'), 'Test Act5 Close'))])
        s8.watch(t, RUN)
        return t


    # Round 280: ATTACK_MOVE_TEAM_TO_NEAREST_OBJECT_OF_TYPE_OF_PLAYER (team, type, player; j04 / j05). s4's crew Am (tanks
    # m0 / m1, 1600 apart) to the player's plants: X is nearest their middle, Y m0's, Z m1's, D (s4's own) nearest of all.
    # s4's tank TA (crew Ae) to the player's engineer EN, teleported 1560 off a second after the order: followed?
    NEAR = {'m0': (1800.0, 1500.0), 'm1': (3400.0, 1500.0), 'X': (2600.0, 2700.0), 'Y': (1800.0, 2700.0),
            'Z': (3600.0, 2800.0), 'D': (2600.0, 1700.0), 'TA': (4400.0, 4000.0), 'EN': (4400.0, 3400.0)}
    EN_TO = (3400.0, 4600.0)
    ENGINEER = 'AlliedEngineer'


    def near_mission():
        m = Mission(name='CampActsNear', map=probe_border, units=[], facts={})
        m.spawns |= {TANK, PLANT, ENGINEER}
        for role, (x, y) in NEAR.items():
            crew = {'m0': 'Am', 'm1': 'Am', 'TA': 'Ae'}.get(role)
            tmpl = TANK if crew else ENGINEER if role == 'EN' else PLANT
            _unit(m, role, 's4' if crew or role == 'D' else 'p1', tmpl, x, y, crew=crew)
        m.waypoint('en to', 'Test Act5 En To', 'stop row', EN_TO[0] - O[0], EN_TO[1] - O[1])
        return m


    def near(m):
        """位 = Am's tanks within 400 of X (ones), Y (tens), Z (hundreds); 打 = X attacked by a tank 1, Y 2, Z 4 + TA within
        400 of EN's first place 10, of its second 100 + EN attacked by a tank 1000."""
        t = Test()
        go = 'ATTACK_MOVE_TEAM_TO_NEAREST_OBJECT_OF_TYPE_OF_PLAYER'
        s8.at(t, 'a1', 1.0, [(go, m.teams['Am'], PLANT, m.player()), (go, m.teams['Ae'], ENGINEER, m.player())])
        s8.at(t, 'a2', 2.0, [('UNIT_TELEPORT_TO_WAYPOINT', _n('EN'), m.mark('en to'))])
        for k, at in (('X', NEAR['X']), ('Y', NEAR['Y']), ('Z', NEAR['Z']), ('En', NEAR['EN']), ('Ento', EN_TO)):
            t.areas[f'Test Act5 By {k}'] = square(*at, 400.0)
        s8.total(t, 'CNV_Act5_Near', '位', [(w, ('NAMED_INSIDE_AREA', _n(u), f'Test Act5 By {k}'))
                                            for k, w in (('X', 1), ('Y', 10), ('Z', 100)) for u in ('m0', 'm1')])
        s8.total(t, 'CNV_Act5_Hit', '打', [(w, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n(k), TANK))
                                           for k, w in (('X', 1), ('Y', 2), ('Z', 4), ('EN', 1000))]
                 + [(10, ('NAMED_INSIDE_AREA', _n('TA'), 'Test Act5 By En')),
                    (100, ('NAMED_INSIDE_AREA', _n('TA'), 'Test Act5 By Ento'))])
        s8.watch(t, RUN)
        return t


    def tow(m):
        """TEAM_ATTACK_MOVE_TOWARDS_NEAREST_OBJECT_TYPE (team, type; a03 / s03): the same handler with no player, so any
        owner's. 位 = Am's tanks within 400 of X (ones), Y (tens), Z (hundreds), s4's own D (thousands); 打 = D attacked
        by a tank 1, Y 2."""
        t = Test()
        s8.at(t, 'a1', 1.0, [('TEAM_ATTACK_MOVE_TOWARDS_NEAREST_OBJECT_TYPE', m.teams['Am'], PLANT)])
        for k in 'XYZD':
            t.areas[f'Test Act5 By {k}'] = square(*NEAR[k], 400.0)
        s8.total(t, 'CNV_Act5_Near', '位', [(w, ('NAMED_INSIDE_AREA', _n(u), f'Test Act5 By {k}'))
                                            for k, w in zip('XYZD', (1, 10, 100, 1000)) for u in ('m0', 'm1')])
        s8.total(t, 'CNV_Act5_Hit', '打', [(w, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n(k), TANK)) for k, w in (('D', 1), ('Y', 2))])
        s8.watch(t, RUN)
        return t


    MISSION = {'engine_acts_v': mission, 'engine_acts_near': near_mission}
    CHECKS = {'engine_acts_v': {'acts': acts}, 'engine_acts_near': {'all': near, 'tow': tow}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_acts6():
    """Retail-campaign actions, batch 6 (round 216): TEAM_HUNT / NAMED_HUNT (203 + 66 uses in the 27 retail missions).
    Mission on maps/probe_border.py as benches/script/control/checks.py#engine_acts5 ('stop row' offsets). What the simulator predicts is in
    brackets.

    Why these sides. Retail a01's second wave (TEAM - Wave 02 - Infantry Invaders 01..08, Soviet_1's) runs
    TEAM_ALLOW_AI_AUTOACQUIRE(team, 1) + TEAM_HUNT(team) with Soviet_1 never handed to the AI (no UNIT_AI_TRANSFER_ALL /
    SKIRMISH_AI_* on it till wave 4's SKIRMISH_AI_TRANSFER_ALL('Soviet_1', 0)); Soviet_1 has an aiPersonality
    (AIP_A01_SovietHuntMarshall) and its aiTeamBuilder / aiTactical switches 255, the other seven 240. The program
    (work/re l2_scripts1 4): TEAM_HUNT sets each member's hunt bit and hangs a HuntTactic on the team only when its
    player has an AI (two player fields non-zero). Round 11-08's hunt bench put its team on Soviet_1, whose team this
    container empties at the start (engine_scripts9 memb), so it said nothing on TEAM_HUNT. The container (Heidelberg)
    gives Soviet_4 DefaultPersonality with aiTeamBuilder / aiTactical 255 (as a01's Soviet_1) and Soviet_5
    DefaultPersonality with both 240: the pair asks whether those switches gate the hunt.

      hunt  s4's crew H4 (two conscripts) at (3800, 4000), s5's crew H5 at (3800, 4700); s4's lone conscript l4 at
            (3000, 4700), s5's l5 at (3000, 4000). The player's barracks pb at (2200, 4350) -- the nearest enemy structure
            -- and tank pt at (4600, 4350), nearer to the crews (~800) than pb (~1650). 2 s: TEAM_ALLOW_AI_AUTOACQUIRE +
            TEAM_HUNT on H4 and H5 (a01's pair), NAMED_HUNT on l4 and l5.
              家 (every frame) = H4's men within 250 of home (ones) + H5's (tens) + l4 (hundreds) + l5 (thousands)
              到 (every frame) = the same by pb (within 400 of it)
              打 (every frame) = pb attacked by a conscript 1, pt attacked by a conscript 2, + 10 x living conscripts of
                the four (H4, H5, l4, l5: 0..6)
      [simulator before the bench: 家 1122 throughout, 到 0, 打 60 -- nobody moves (TEAM_HUNT / NAMED_HUNT only noted)]
      BENCH 11-14 (round 216, run_queue once, CampActsWHunt; tests/test_simbench.py test_acts_w_hunt_as_the_bench):
        家 / 到 / 打  s1-s6 1122 0 60 | s7-s14 1120 0 60 | s15-s30 1120 0 62 | s31-s48 1120 0 52 | s49-s56 1120 0 42 |
        s57-s66 1120 0 40. The bench's seconds run ~1 behind the scripts'.
        TEAM_HUNT: Soviet_4's crew (255) left home ~4 s after the order and went for the tank (the nearest enemy, a unit),
        never the barracks (the nearest structure); it fought the tank from s15 and both died (s31, s49). Soviet_5's crew
        (240) stayed. NAMED_HUNT: neither lone conscript moved in 60 s. After the bench the simulator reads 1122 -> 1120
        at 8 s, 62 at 17 s, 52 at 33 s, 42 at 50 s (Sim.tactical + an attack-move to the nearest hostile object).
    """
    from maps import probe_border
    from parts import Mission, Test, square
    import checks.engine_scripts8 as s8

    TANK, MAN, BARRACKS = 'AlliedAntiVehicleVehicleTech1', 'SovietAntiInfantryInfantry', 'AlliedBarracks'
    O = (1300.0, 4300.0)                            # probe_border's 'stop row'
    RUN = 60.0
    HOME = {'H4': (3800.0, 4000.0), 'H5': (3800.0, 4700.0), 'l4': (3000.0, 4700.0), 'l5': (3000.0, 4000.0)}
    PB, PT = (2200.0, 4350.0), (4600.0, 4350.0)


    def _n(part):
        return f'UNIT - CNV Act6 {part.title()}'


    def _unit(m, role, side, template, x, y, crew=None):
        props = {'originalOwner': m.crew(crew, side=side)} if crew else {}
        m.put(template, 'stop row', x - O[0], y - O[1], side=side, angle=0.0 if side == 'p1' else 3.1416,
              name=_n(role), role=role, props=props)


    def mission():
        m = Mission(name='CampActsW', map=probe_border, units=[], facts={})
        m.spawns |= {TANK, MAN, BARRACKS}
        for crew in ('H4', 'H5'):
            x, y = HOME[crew]
            for k in range(2):
                _unit(m, f'{crew} {k}', 's' + crew[1], MAN, x, y - 30.0 + 60.0 * k, crew=crew)
        for lone in ('l4', 'l5'):
            _unit(m, lone, 's' + lone[1], MAN, *HOME[lone])
        _unit(m, 'pb', 'p1', BARRACKS, *PB)
        _unit(m, 'pt', 'p1', TANK, *PT)
        return m


    def men(key):
        return [_n(f'{key} {k}') for k in range(2)] if key.startswith('H') else [_n(key)]


    def hunt(m):
        t = Test()
        for key, at in HOME.items():
            t.areas[f'Test Act6 Home {key}'] = square(*at, 250.0)
        t.areas['Test Act6 Pb'] = square(*PB, 400.0)
        s8.at(t, 'h2', 2.0, [a for crew in ('H4', 'H5') for a in (('TEAM_ALLOW_AI_AUTOACQUIRE', m.teams[crew], 1),
                                                                ('TEAM_HUNT', m.teams[crew]))]
              + [('NAMED_HUNT', _n(lone)) for lone in ('l4', 'l5')])
        weight = {'H4': 1, 'H5': 10, 'l4': 100, 'l5': 1000}
        s8.total(t, 'CNV_Act6_Home', '家', [(w, ('NAMED_INSIDE_AREA', u, f'Test Act6 Home {k}'))
                                            for k, w in weight.items() for u in men(k)])
        s8.total(t, 'CNV_Act6_At', '到', [(w, ('NAMED_INSIDE_AREA', u, 'Test Act6 Pb'))
                                          for k, w in weight.items() for u in men(k)])
        s8.total(t, 'CNV_Act6_Hit', '打', [(1, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('pb'), MAN)),
                                           (2, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('pt'), MAN))]
                 + [(10, ('NAMED_NOT_DESTROYED', u)) for k in weight for u in men(k)])
        s8.watch(t, RUN)
        return t


    MISSION = {'engine_acts_w': mission}
    CHECKS = {'engine_acts_w': {'hunt': hunt}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_acts7():
    """Retail-campaign actions, batch 7 (round 217): PLAYER_TRANSFER_OWNERSHIP_PLAYER (a05 a09 ...). Mission on
    maps/probe_border.py as benches/script/control/checks.py#engine_acts5 ('stop row' offsets, engine_acts.SLOT spots). What the simulator
    predicts is in brackets.

    Why again. Round 215's bench (engine_acts_v) saw nothing change hands and guessed Soviet_5 / 6 had no team. They do:
    the container's Teams has teamSoviet_5 and teamSoviet_6 (read 11-14 off the container map, mapxml.teams), and a
    bare object placed for s5 is on teamSoviet_5 (island.like). Round 215 never asked whether its units were Soviet_5's
    before the order. The program (work/re/a217_transfer.md): the handler calls the second player's method with the first
    (retail a05 ('Japan_04_Scripted', 'Japan_03') then wakes Japan_03: from, to); it returns at once when the receiver has
    no default team, else walks a list of the giver's (read as its teams, members of one kind skipped), moves
    them onto the receiver and adds one of the giver's counters to it. Predicted: units on teams move, ones on no team --
    Soviet_2's, the container's start-up UNIT_AI_TRANSFER_ALL takes them off every team (sim.skirmish_setup) -- stay.
    The bench read the opposite (below): the list is not the map's teams (which list it is: not read further).

      own   xt5 Soviet_5's tank (bare: teamSoviet_5), xc5 Soviet_5's conscript on a crew of its own (C5), xm6 Soviet_6's
            conscript (bare), xm2 Soviet_2's (bare, off its team after the start), xm4 Soviet_4's (bare, never handed).
            1 s: PLAYER_SET_MONEY Player_1 1000, Soviet_5 5000. 4 s: TRANSFER(Soviet_5, Player_1), TRANSFER(Soviet_6,
            Soviet_4). 12 s: TRANSFER(Soviet_2, Player_1).
              主 (every frame) = NAMED_OWNED_BY_PLAYER xt5 s5 1 / p1 2, xc5 s5 4 / p1 8, xm6 s6 16 / s4 32,
                xm2 s2 64 / p1 128, xm4 s4 256
              钱 (every frame) = PLAYER_HAS_CREDITS p1 >= 5000 1, s5 >= 4000 2, s5 < 100 4, p1 >= 1000 8
      [simulator before the bench: 主 341 throughout (no hand-over), 钱 10 from 1 s]
      BENCH 11-14 run 1 (round 217, run_queue): 主 / 钱 s1-s2 341 10 | s3-s10 341 13 | s11-s31 405 13 -- nothing of
        Soviet_5 / 6 changed hands at 4 s, Soviet_2's conscript (off its team) went to Player_1 at 12 s; the money moved
        whole at 4 s (Player_1 >= 5000, Soviet_5 < 100). So the team, not the AI: the second run added xb2 (Soviet_2's,
        put on crew B2 at 2 s), UNIT_AI_TRANSFER(xc5, 1) at 2 s (off its crew, Soviet_5 not woken), 主 512 / 1024 for
        xb2 / xm4 (xm4 was 256) and 钱 16 / 32 / 64 = p1 >= 5900 / 6100, s5 >= 4900.
      BENCH 11-14 run 2 (CampActsXOwn; tests/test_simbench.py test_acts_x_own_as_the_bench): 主 / 钱 s1 1365 74 |
        s2-s9 1369 29 | s10-s31 1433 61. At 4 s xc5 (off its crew) went to Player_1, xt5 (teamSoviet_5) and xm6 stayed;
        at 12 s xm2 went, xb2 (on B2) stayed; Player_1 1000 + 5000 (>= 5900, < 6100), Soviet_5 < 100; at 12 s Soviet_2's
        money too (>= 6100; its starting money not simulated). The simulator after: 1365 / 74 at 1 s, 1369 / 29 at 4 s,
        1433 / 29 at 12 s (sim.Sim.act PLAYER_TRANSFER_OWNERSHIP_PLAYER: owner and money; units with no team only).
    """
    from maps import probe_border
    from parts import Mission, Test
    import checks.engine_scripts8 as s8

    TANK, MAN = 'AlliedAntiVehicleVehicleTech1', 'SovietAntiInfantryInfantry'
    O = (1300.0, 4300.0)                            # probe_border's 'stop row'
    RUN = 30.0
    AT = {'xt5': (600.0, 4000.0), 'xc5': (2200.0, 4000.0), 'xm6': (3800.0, 4000.0), 'xm2': (600.0, 4700.0),
          'xb2': (2200.0, 4700.0), 'xm4': (3800.0, 4700.0)}
    GE, LT = 3, 0                                   # comparisons (sim.CMP): >=, <


    def _n(part):
        return f'UNIT - CNV Act7 {part.title()}'


    def mission():
        m = Mission(name='CampActsX', map=probe_border, units=[], facts={})
        m.spawns |= {TANK, MAN}
        m.crew('B2', side='s2')                     # xb2 joins it at 2 s (after the container's start-up hand-over)
        for role, (x, y) in AT.items():
            side = 's' + role[-1]
            props = {'originalOwner': m.crew('C5', side='s5')} if role == 'xc5' else {}
            m.put(TANK if role == 'xt5' else MAN, 'stop row', x - O[0], y - O[1], side=side, angle=3.1416,
                  name=_n(role), role=role, props=props)
        return m


    def own(m):
        t = Test()
        p1, s2, s4, s5, s6 = (m.player(s) for s in ('p1', 's2', 's4', 's5', 's6'))
        s8.at(t, 'o1', 1.0, [('PLAYER_SET_MONEY', p1, 1000), ('PLAYER_SET_MONEY', s5, 5000)])
        s8.at(t, 'o2', 2.0, [('UNIT_AI_TRANSFER', _n('xc5'), 1), ('UNIT_SET_TEAM', _n('xb2'), m.teams['B2'])])
        s8.at(t, 'o4', 4.0, [('PLAYER_TRANSFER_OWNERSHIP_PLAYER', s5, p1), ('PLAYER_TRANSFER_OWNERSHIP_PLAYER', s6, s4)])
        s8.at(t, 'o12', 12.0, [('PLAYER_TRANSFER_OWNERSHIP_PLAYER', s2, p1)])
        s8.total(t, 'CNV_Act7_Own', '主', [(w, ('NAMED_OWNED_BY_PLAYER', who, _n(u))) for w, who, u in (
            (1, s5, 'xt5'), (2, p1, 'xt5'), (4, s5, 'xc5'), (8, p1, 'xc5'), (16, s6, 'xm6'), (32, s4, 'xm6'),
            (64, s2, 'xm2'), (128, p1, 'xm2'), (256, s2, 'xb2'), (512, p1, 'xb2'), (1024, s4, 'xm4'))])
        s8.total(t, 'CNV_Act7_Cash', '钱', [(w, ('PLAYER_HAS_CREDITS', who, c, n)) for w, who, c, n in (
            (1, p1, GE, 5000), (2, s5, GE, 4000), (4, s5, LT, 100), (8, p1, GE, 1000), (16, p1, GE, 5900), (32, p1, GE, 6100),
            (64, s5, GE, 4900))])
        s8.watch(t, RUN)
        return t


    MISSION = {'engine_acts_x': mission}
    CHECKS = {'engine_acts_x': {'own': own}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_acts8():
    """Retail-campaign actions, batch 8 (round 218): what TEAM_HUNT goes for, which switch gates it, NAMED_HUNT on a woken
    AI -- round 216's three hypotheses (engine_acts6 hunt). Mission on maps/probe_border.py as benches/script/control/checks.py#engine_acts6
    ('stop row' offsets). What the simulator predicts is in brackets.

    Why. Round 216's crew (Soviet_4, both switches 255) went for the tank ~870 east, not the barracks ~1650 west -- the
    two were already on opposite sides, but the tank shot back and killed the crew, so it never said whether the hunt
    re-picks when its target dies, nor (engine line B, work/re/b186_hunt.md) whether the crew went for the nearest
    *object* or for the nearest *structure* and met the tank by auto-acquire. Here the targets are engineers (no weapon)
    and every reading is a place: H1 'the nearest hostile object, units too' sends the crew east to e1; H2 'the nearest
    structure' west to pb (e1 out of sight behind it); after e1 dies, re-picking the nearest from there goes to e2.

      pick  s4's crew H4 (two conscripts) at (1500, 4400): the player's engineer e1 at (2200, 4400) (700 east), engineer e2
            at (2600, 4800) (1166 from home, 566 from e1), barracks pb at (500, 4400) (1000 west).
      gate  s5's crew H5 at (4600, 4000), set aiTeamBuilder 240 / aiTactical 255 (m.sides); s6's H6 at (4600, 4800), 255 /
            240. Each its own bait 600 west (b5 (4000, 4000), b6 (4000, 4800)): whichever switch gates the hunt, one moves.
      named s3's conscript n3 at (3400, 4400) (the container hands Soviet_3 to its AI at the start) NAMED_HUNT; c3 at
            (3400, 4700), no order (does the woken AI move it anyway).
            2 s: TEAM_ALLOW_AI_AUTOACQUIRE + TEAM_HUNT on H4 / H5 / H6, NAMED_HUNT on n3.
              家 (every frame) = men within 250 of home: H4 (ones) + H5 (tens) + H6 (hundreds) + n3 1000 + c3 10000
              到 (every frame) = H4's men within 300 of pb (ones), of e1's spot (tens), of e2's (hundreds)
              活 (every frame) = alive: e1 1, e2 2, pb 4; attacked by a conscript: e1 8, e2 16, pb 32
              饵 (every frame) = b5 alive 1, b6 alive 2, b5 attacked 4, b6 attacked 8, n3 alive 16, c3 alive 32
      [simulator before the bench: 家 11222 -> 11200 at 8 s (H4 and H5 leave: Sim.tactical reads aiTactical), 到 0 ->
       20 at 11 s (H4 by e1, one order, no re-pick), 活 7 -> 15 at 14 s -> 6 at 16 s (e1 attacked, killed; a dead
       unit's 'attacked' reads false), 饵 51 -> 55 at 12 s -> 50 at 14 s (b5 attacked, killed); n3 never moves]
      BENCH 11-14 (round 218, run_queue once, CampActsYHunt; tests/test_simbench.py test_acts_y_hunt_as_the_bench):
        家 / 到 / 活 / 饵  s1-s5 11222 0 7 51 | s6-s8 11200 0 7 51 | s9-s10 11200 20 7 51 | s11-s12 11200 20 7 55 |
        s13-s14 11200 20 15 54 | s15-s19 11200 20 14 54 | s20 11200 20 14 50 | s21 11200 220 14 50 | s22-s25 11200 220 6
        50 | s26-s28 11200 210 22 50 | s29-s30 11200 200 20 58 | s31-s35 11200 200 20 56 | s36-s37 11200 200 4 56 | s38
        11200 100 4 48 | s39-s42 11200 0 4 48 | s43-s44 11200 10 4 48 | s45 11200 20 4 48 | s46 11200 10 4 48 | s47-s48
        11200 0 4 48 | s49-s50 11201 0 4 48 | s51-s58 11202 0 4 48 | s59 11201 0 4 48 | s60-s61 11200 0 4 48.
        Gate: H4 and H5 left at s6, H6 (aiTactical 240) never -- aiTactical. Pick: H4 by e1 at s9 (east, the nearest
        object, a unit), e1 attacked s13, dead s15; by e2 at s21 (the two areas overlap: 220), e2 attacked s26, dead s29;
        out of e2's at s38-s39, by e1's spot s43-s46, past home s49-s59 westwards (pb the one left). H5: b5 attacked s11,
        dead s13, then b6 (800 on) attacked s29, dead s31. NAMED_HUNT: Soviet_3's n3 (its AI woken by the container)
        never left home, nor c3. New: a dead engineer's NAMED_ATTACKED_BY_OBJECTTYPE stays true 7 s (s15-s21, s13-s19,
        s29-s35, s31-s37) while NAMED_NOT_DESTROYED is false at once -- its body lingers (the simulator's linger for it
        is shorter: not fixed here, a unit-data matter). After the bench the simulator (engine.orders.hunt, HUNT_REPICK 45)
        reads each step a second later: 11200 at 8, 220 at 22, e2 attacked 27, dead 30, b6 attacked 30, 0 at 39, home
        50 / 52 / 60 / 61.
    """
    from maps import probe_border
    from parts import Mission, Test, square
    import checks.engine_scripts8 as s8

    MAN, ENGINEER, BARRACKS = 'SovietAntiInfantryInfantry', 'AlliedEngineer', 'AlliedBarracks'
    O = (1300.0, 4300.0)                            # probe_border's 'stop row'
    RUN = 60.0
    HOME = {'H4': (1500.0, 4400.0), 'H5': (4600.0, 4000.0), 'H6': (4600.0, 4800.0), 'n3': (3400.0, 4400.0),
            'c3': (3400.0, 4700.0)}
    PLAYER = {'e1': (ENGINEER, 2200.0, 4400.0), 'e2': (ENGINEER, 2600.0, 4800.0), 'pb': (BARRACKS, 500.0, 4400.0),
              'b5': (ENGINEER, 4000.0, 4000.0), 'b6': (ENGINEER, 4000.0, 4800.0)}
    SIDES = {'s5': {'aiTeamBuilder': 240, 'aiTactical': 255}, 's6': {'aiTeamBuilder': 255, 'aiTactical': 240}}


    def _n(part):
        return f'UNIT - CNV Act8 {part.title()}'


    def _put(m, role, side, template, x, y, crew=None):
        props = {'originalOwner': m.crew(crew, side=side)} if crew else {}
        m.put(template, 'stop row', x - O[0], y - O[1], side=side, angle=0.0 if side == 'p1' else 3.1416,
              name=_n(role), role=role, props=props)


    def mission():
        m = Mission(name='CampActsY', map=probe_border, units=[], facts={})
        m.spawns |= {MAN, ENGINEER, BARRACKS}
        for side, props in SIDES.items():
            m.sides[side] = dict(m.sides.get(side, {}), **props)
        for key, (x, y) in HOME.items():
            if key.startswith('H'):
                for k in range(2):
                    _put(m, f'{key} {k}', 's' + key[1], MAN, x, y - 30.0 + 60.0 * k, crew=key)
            else:
                _put(m, key, 's3', MAN, x, y)
        for role, (template, x, y) in PLAYER.items():
            _put(m, role, 'p1', template, x, y)
        return m


    def men(key):
        return [_n(f'{key} {k}') for k in range(2)] if key.startswith('H') else [_n(key)]


    def hunt(m):
        t = Test()
        for key, at in HOME.items():
            t.areas[f'Test Act8 Home {key}'] = square(*at, 250.0)
        for role in ('pb', 'e1', 'e2'):
            t.areas[f'Test Act8 By {role}'] = square(*PLAYER[role][1:], 300.0)
        s8.at(t, 'h2', 2.0, [a for crew in ('H4', 'H5', 'H6') for a in (('TEAM_ALLOW_AI_AUTOACQUIRE', m.teams[crew], 1),
                                                                      ('TEAM_HUNT', m.teams[crew]))]
              + [('NAMED_HUNT', _n('n3'))])
        weight = {'H4': 1, 'H5': 10, 'H6': 100, 'n3': 1000, 'c3': 10000}
        s8.total(t, 'CNV_Act8_Home', '家', [(w, ('NAMED_INSIDE_AREA', u, f'Test Act8 Home {k}'))
                                            for k, w in weight.items() for u in men(k)])
        s8.total(t, 'CNV_Act8_At', '到', [(w, ('NAMED_INSIDE_AREA', u, f'Test Act8 By {role}'))
                                          for role, w in (('pb', 1), ('e1', 10), ('e2', 100)) for u in men('H4')])
        s8.total(t, 'CNV_Act8_Alive', '活', [(w, ('NAMED_NOT_DESTROYED', _n(r))) for r, w in (('e1', 1), ('e2', 2), ('pb', 4))]
                 + [(w, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n(r), MAN)) for r, w in (('e1', 8), ('e2', 16), ('pb', 32))])
        s8.total(t, 'CNV_Act8_Bait', '饵', [(1, ('NAMED_NOT_DESTROYED', _n('b5'))), (2, ('NAMED_NOT_DESTROYED', _n('b6'))),
                                            (4, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('b5'), MAN)),
                                            (8, ('NAMED_ATTACKED_BY_OBJECTTYPE', _n('b6'), MAN)),
                                            (16, ('NAMED_NOT_DESTROYED', _n('n3'))), (32, ('NAMED_NOT_DESTROYED', _n('c3')))])
        s8.watch(t, RUN)
        return t


    MISSION = {'engine_acts_y': mission}
    CHECKS = {'engine_acts_y': {'hunt': hunt}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_acts9():
    """Retail-campaign actions, batch 9 (round 219): SKIRMISH_AI_TRANSFER_ALL (a01 a05 ... 35 uses). Mission on
    maps/probe_border.py as benches/script/control/checks.py#engine_acts7 ('stop row' offsets, engine_acts.SLOT spots). What the simulator
    predicts is in brackets.
    The program (work/re/a219_skirmish_transfer.md): the handler runs, for each player named, the same step as
    UNIT_AI_TRANSFER_ALL's -- minus the AI wake UNIT_AI_TRANSFER_ALL does after it. That step, switch 1: the members of
    the player's map default team (teamSoviet_N) and of every other map team go to the AI's defaultSkirmishTeam; switch
    0: the members of defaultSkirmishTeam and the AI's other teams go to the map default team (not back to the crew they
    came from). Predicted: 1 empties teamSoviet_5 and the crew C5; 0 puts all three onto teamSoviet_5, Soviet_2's two
    (taken off at the start by the container's UNIT_AI_TRANSFER_ALL, sim.skirmish_setup) onto teamSoviet_2; Soviet_6's
    (never handed) stays where it is.
      all   s5: a5 b5 (bare: teamSoviet_5), c5 (crew C5); s2: a2 b2 (bare); s6: a6 (bare). 2 s: TRANSFER_ALL(Soviet_5, 1).
            6 s: TRANSFER_ALL(Soviet_5, 0), (Soviet_2, 0), (Soviet_6, 0). Counters = TEAM_COMPARE_NUM_MEMBERS == n:
            队5 teamSoviet_5, 队C5 the crew, 队2 teamSoviet_2, 队6 teamSoviet_6.
      [predicted: 队5 / 队C5 / 队2 / 队6 = 2 1 0 1 at s1, 0 0 0 1 from 2 s, 3 0 2 1 from 6 s]
      BENCH 11-14 (round 219, run_queue; tests/test_simbench.py test_acts_z_all_as_the_bench): s1-s4 0 0 0 1 | s5-s13
        4 0 3 2. Switch 1 as predicted (the bench's s1 is past the 2 s timer). Switch 0: every default team one member
        more than the units sent back -- Soviet_6's too (1 -> 2), never handed: a hidden object each player has on
        defaultSkirmishTeam from the start goes over with them (its PlayerSpellBook, INFERRED: which object not read).
        The simulator after: 2 1 0 1 at 1 s, 0 0 0 1 from 2 s, 4 0 3 2 from 6 s (Sim.hidden_home).
    """
    from maps import probe_border
    from parts import Mission, Script, Test
    import checks.engine_scripts8 as s8

    MAN = 'SovietAntiInfantryInfantry'
    O = (1300.0, 4300.0)                            # probe_border's 'stop row'
    RUN = 12.0
    AT = {'a5': (600.0, 4000.0), 'b5': (1400.0, 4000.0), 'c5': (2200.0, 4000.0), 'a2': (600.0, 4700.0),
          'b2': (1400.0, 4700.0), 'a6': (3800.0, 4000.0)}
    EQ = 2                                          # TEAM_COMPARE_NUM_MEMBERS' ==


    def _n(part):
        return f'UNIT - CNV Act9 {part.title()}'


    def mission():
        m = Mission(name='CampActsZ', map=probe_border, units=[], facts={})
        m.spawns |= {MAN}
        for role, (x, y) in AT.items():
            side = 's' + role[-1]
            props = {'originalOwner': m.crew('C5', side='s5')} if role == 'c5' else {}
            m.put(MAN, 'stop row', x - O[0], y - O[1], side=side, angle=3.1416, name=_n(role), role=role, props=props)
        return m


    def _members(t, counter, label, team):
        t.counters.append((counter, label))
        t.scripts += [Script(f'Test - {counter} {n}', [('TEAM_COMPARE_NUM_MEMBERS', team, EQ, n)],
                             [('SET_COUNTER', counter, n)], once=False) for n in range(5)]


    def all_(m):
        t = Test()
        s2, s5, s6 = (m.player(s) for s in ('s2', 's5', 's6'))
        s8.at(t, 'z2', 2.0, [('SKIRMISH_AI_TRANSFER_ALL', s5, 1)])
        s8.at(t, 'z6', 6.0, [('SKIRMISH_AI_TRANSFER_ALL', p, 0) for p in (s5, s2, s6)])
        for counter, label, team in (('CNV_Act9_T5', '队5', m.team('s5')), ('CNV_Act9_C5', '队C5', m.teams['C5']),
                                     ('CNV_Act9_T2', '队2', m.team('s2')), ('CNV_Act9_T6', '队6', m.team('s6'))):
            _members(t, counter, label, team)
        s8.watch(t, RUN)
        return t


    MISSION = {'engine_acts_z': mission}
    CHECKS = {'engine_acts_z': {'all': all_}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_aichange():
    """A round 294: the AI's subsystem switches (benches/script/control/scenes.py#engine_aichange) -- s1's units out by kind, by logical frame."""
    from checks import engine_scripts8 as s8
    from parts import Test, counted


    def a(m):
        t = Test()
        m.spawns.update(('AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry', 'AlliedScoutInfantry'))
        for counter, label, template in (('CNV_AISw_PK', '维和', 'AlliedAntiInfantryInfantry'),
                                         ('CNV_AISw_Jav', '标枪', 'AlliedAntiVehicleInfantry'),
                                         ('CNV_AISw_Dog', '警犬', 'AlliedScoutInfantry')):
            counted(counter, label, t, template=template, player=m.player('s1'))
        s8.frames(t, 'CNV_AISw_Frame', '逻辑帧', [])
        s8.watch(t, 90., 2.)
        return t


    CHECKS = {name: {'a': a} for name in ('aiubon', 'aiuboff', 'aiubback', 'aitboff')}
    return dict(CHECKS=CHECKS)


def engine_aifav():
    """Engine probe: SKIRMISH_AI_SET_FAVORED_ENEMY(ai player, enemy) (retail: a04 Japan01 / Japan02 -> Player_1 right
    after the AI's setup, ...). Engine line A round 220; the mission is engine line B's build aipriodef
    (from the registry, its module untouched) plus the favored enemy; the counters are checks/engine_aiprio.py's.

    The program (work/re a219_skirmish_transfer.md section 2): with both players, the AI brain, its strategy manager
    and its enemy manager there, the enemy table is emptied (the re-sort off) and the one enemy is put back at score 10
    -- SET_ENEMY_PLAYER_PRIORITY(enemy, 10) after a clear.
      aipriofav  the wake as aipriodef (SET_ALL_ENEMY_PLAYERS_PRIORITIES 20: Player_1 and Soviet_4 one tier; the bench
                 11-10 went for the far plant, the player's), then SET_FAVORED_ENEMY(Soviet_1, Soviet_4) in the same
                 script. Predicted: the near plant (Soviet_4's) and never the far one. Without the clear (only "Soviet_4
                 at 10") Player_1 at 20 would stay the top tier -> the far plant: the two readings tell them apart.
      [simulator predicted: 到远厂 (simai tells the clear as a priority of nobody: the model has no clear yet --
       work/re a220_favored_enemy.md, asked of engine line B)]
      BENCH 11-14 (round 220, run_queue, CampAIPrioFavA_mcp_1114_035402) PASS: 步兵在家 / 到近厂 / 到远厂 s1-s13 4 0 0 |
        s14 4 2 0 | s15 2 4 0 | s16-s21 0 4 0 | s22-s23 0 3 0 (then fewer: the turrets), 到远厂 0 to s69. The clear holds:
        Soviet_4 alone in the table, at 10 (aipriodef, without it: the far plant s25). Simulator after (sim.py records
        the clear, simai not yet): Player_1 20 / Soviet_4 10; simai since holds it (benches/script/control/readings.toml#engine_aifav).
    A295 (11-22), the same wake and expectations (program, work/re a295_clear_priorities.md: CLEAR_ALL calls the favored
    enemy's clear itself; CLEAR_ONE takes one entry out, re-sort off; AUTO sets the sort, the override off, re-sorts):
      aiprioclr   CLEAR_ALL, then Soviet_4 10 (s07's use)  PASS CampAIPrioClrA_mcp_1122_003028: 到近厂 s16, 到远厂 never
      aiprioclr1  CLEAR_ONE Player_1                       PASS CampAIPrioClr1A_mcp_1122_002725: 到近厂 s15, 到远厂 never
      aiprioauto  AUTO NearestFirst_AllowTies              PASS CampAIPrioAutoA_mcp_1122_003641: 到近厂 s15, 到远厂 never --
                  the re-sort puts the nearer enemy a tier above (aipriodef alone: the far plant). The simulator does not
                  do it (no sort command in the model, asked of B) and takes the near plant by its one-tier rule: no reading.
    """
    import registry
    from checks import engine_aiprio as ap

    FAVORED = 'SKIRMISH_AI_SET_FAVORED_ENEMY'
    CLEAR_ALL = 'SKIRMISH_AI_CLEAR_ALL_ENEMY_PLAYERS_PRIORITIES'
    CLEAR_ONE = 'SKIRMISH_AI_CLEAR_ENEMY_PLAYER_PRIORITY'
    AUTO = 'SKIRMISH_AI_USE_AUTOMATIC_ENEMY_PLAYER_PRIORITY_SCHEME'
    # build -> (mod name, what the wake adds after aipriodef's SET_ALL 20: (action, arguments after Soviet_1))
    SET_ONE = 'SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY'
    EXTRA = {     # fav / clr1: Player_1 a tier up first (30), so the action undone sends them to the far plant (review ss #6)
        'aipriofav': ('CampAIPrioFav', [(SET_ONE, 'p1', 30), (FAVORED, 's4')]),
        'aiprioclr': ('CampAIPrioClr', [(CLEAR_ALL,), (SET_ONE, 's4', 10)]),
        'aiprioclr1': ('CampAIPrioClr1', [(SET_ONE, 'p1', 30), (CLEAR_ONE, 'p1')]),
        'aiprioauto': ('CampAIPrioAuto', [(AUTO, 'NearestFirst_AllowTies')]),
    }


    def mission(build):
        m = registry.get().builds['aipriodef']()      # engine line B's build, through the registry (not its module)
        m.name, extra = EXTRA[build]
        wake = next(s for s in m.scripts if s.name == 'CNV AI - Wake')
        arg = lambda x: m.player(x) if x in ('s4', 'p1') else x
        wake.do = list(wake.do) + [(act, m.player('s1'), *map(arg, rest)) for act, *rest in extra]
        return m


    def a(m):
        """engine_aiprio's counters and its 到近厂 expectation (aiprio1's), plus never 到远厂 in the same window."""
        t = ap.a(m, 'aiprio1')
        t.expect.append(('到远厂', 1, '==', 0, m.facts['wake at'] + ap.AFTER))
        return t


    MISSION = {k: (lambda k=k: mission(k)) for k in EXTRA}
    CHECKS = {k: {'a': a} for k in EXTRA}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_aiflip():
    """A round 274: the all-enemies action after s5 turns enemy at 5 s (benches/script/control/scenes.py#engine_aiflip).

    The same observation as C's engine_aiallbuild.a (four counters, 150 s watch); the readings that matter are the
    ra3ext bpick / border lines (teamlog.build_picks / build_orders), compared at the same logical frames.
    """
    from checks.engine_aiallbuild import a

    CHECKS = {name: {'a': a} for name in ('aiallflipon', 'aiallflipoff', 'aiallfliplate', 'aiallflipnever',
                                                        'aiallflipwoff', 'aiallflipwon')}
    return dict(CHECKS=CHECKS)


def engine_aistart():
    """A line: SKIRMISH_AI_START and PLAYER_TOGGLE_SKIRMISH_AI on B's aiskirm map (missions/aiskirm_bench.py).

    Program (work/re a270_skirmish_start.md): SKIRMISH_AI_START = only the wake UNIT_AI_TRANSFER_ALL ends with (the AI's
    started byte set, its start frame = now; no team moves); PLAYER_TOGGLE_SKIRMISH_AI(p, on) writes the AI's paused byte
    = not on, and the AI's per-frame update does nothing while it is set (no opening, building, protocols, states).
    Builds (s1 AlliedBalanced, 50000 at the 10 s wake; the control aiskirm d: 建筑数 2 at ~11 s after the wake, 3 at ~21):
      aistart   no script library (aiskirmnl), the wake's UNIT_AI_TRANSFER_ALL replaced by SKIRMISH_AI_START.
                Prediction: as aiskirm d -- 建筑数 2 ~11 s after the wake, money falling.
      ainowake  no library and no wake at all (MAKE_BASE and the money only). Prediction: the opening never starts --
                50000 and 建筑数 1 throughout (INFERRED: other subsystems might still order).
      aipause   aiskirm (library on), toggled off at 25 s, on at 85 s. Prediction: no new order from 25 s -- money and
                建筑数 flat (a structure already paid for may still finish), no unit; at 85 s it goes on.
      aistartx  no library, UNIT_AI_TRANSFER(the yard, 1) then SKIRMISH_AI_START (retail a07's way). Added after aistart.
      aixfer    no library, SKIRMISH_AI_TRANSFER_ALL(s1, 1) alone (the team step, no wake). Added after aistart.
    Counters: AI钱, 建筑数, 兵数, 逻辑帧 (as aibgate).
    BENCH 11-16 (A270, all NOEXPECT, work/bench_results/<build>__a.json):
      aistart   50000 / 1 / 0 from the money (f158) to f1154 -- the prediction failed: START wakes, but the yard is still
                on teamSoviet_1, not the AI's.
      ainowake  50000 / 1 / 0 to f746.   aixfer  50000 / 1 / 0 to f1104 (handed, never woken).
      aistartx  paying at f169 (49943), 建筑数 2 at f312 (f290 still 1), 3 at f461 -- as aiskirm's own wake.
      aipause   paying to 48300 at f457 (兵数 2 at f419: what was under way), then flat to f1262; 建筑数 3 at f1280 (the
                structure finished while paused is placed at the resume), paying again from f1300.
    """
    from parts import Script, Test
    from checks import engine_scripts8 as s8
    from checks import engine_aiskirm as ak

    OFF_AT, ON_AT = 25.0, 85.0


    def _counters(t, m, key):
        s1 = m.player('s1')
        t.scripts.append(Script(f'Test - {key} setup', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.counters.append((f'CNV_{key}_Money', 'AI钱'))
        t.scripts.append(Script(f'Test - {key} money', [], [
            ('SET_PLAYER_MONEY_TO_COUNTER', s1, f'CNV_{key}_Money')], once=False))
        ak._sum(t, m, s1, f'CNV_{key}_Built', '建筑数', ak.BUILDINGS + ak.TOWERS)
        ak._sum(t, m, s1, f'CNV_{key}_Army', '兵数', ak.ARMY)
        s8.frames(t, f'CNV_{key}_Clock', '逻辑帧', [])
        return s1


    def wake(m):
        """aistart / ainowake: the readings from the wake on."""
        t = Test()
        _counters(t, m, 'AIStart')
        t.bench = [('bench_watch', dict(seconds=60., every=1., sheet=False, lines=4))]
        return t


    def pause(m):
        """aipause: PLAYER_TOGGLE_SKIRMISH_AI(s1, 0) at OFF_AT, (s1, 1) at ON_AT."""
        t = Test()
        s1 = _counters(t, m, 'AIPause')
        s8.at(t, 'aipause off', OFF_AT, [('PLAYER_TOGGLE_SKIRMISH_AI', s1, 0)])
        s8.at(t, 'aipause on', ON_AT, [('PLAYER_TOGGLE_SKIRMISH_AI', s1, 1)])
        t.bench = [('bench_watch', dict(seconds=125., every=1., sheet=False, lines=4))]
        return t


    CHECKS = {'aistart': {'a': wake}, 'ainowake': {'a': wake}, 'aistartx': {'a': wake}, 'aixfer': {'a': wake},
              'aipause': {'a': pause}}
    return dict(CHECKS=CHECKS)


def engine_aixfer():
    """Engine line A round 150: TEAM_AI_TRANSFER / UNIT_AI_TRANSFER (the program read in work/re/l2_scripts1.md 7: a
    computer player's units into its AI's hands -- each set onto the player's AI team and logged in the AI's unit list,
    no order cleared; a human player's units: nothing). Retail (a01's wave 3) gives the order and the hand-over in one
    script: ATTACK_MOVE_NAMED_UNIT_TO then UNIT_AI_TRANSFER(unit, 1); this probe does the same with a plain move.

    Mission on maps/probe_border.py (level ground), rows west to east from x 700 to `far` x 1900 (1200 run):
      A  Soviet_4's crew XA, two Guardians at y 4150 / 4250 (row 4200): MOVE_TEAM_TO(XA, far A) + TEAM_AI_TRANSFER(XA, 1)
      B  Soviet_4's crew XB, one Guardian at y 4700: MOVE_NAMED_UNIT_TO(it, far B) + UNIT_AI_TRANSFER(it, 1)
      C  the player's crew XC, one Guardian at y 4450: MOVE_TEAM_TO(XC, far C) + TEAM_AI_TRANSFER(XC, 1) +
         UNIT_AI_TRANSFER(it, 1)
      D  Soviet_4's crew XD, one Guardian at y 3950: the control (late only): MOVE_TEAM_TO(XD, far D), no hand-over
    Soviet_4 has no script library (engine_scripts9 memb4: its placed crews keep their members) and its AI is never
    woken (no UNIT_AI_TRANSFER_ALL). Everyone holds fire (NO_ATTACK).
      xfer  all at 1 s, in one script, order first (as retail). D stands (not counted).
              到 = in its row's far square: A's each x1 (0-2), B x4, C x8          [simulator: all kept, 14 at ~s15]
              队 = members: XA's (0-2), XB's x4, XC's x8                         [the notes: A / B onto the AI team -> 8]
              默 = teamSoviet_4's members (Soviet_4's default team)              [0; the AI team being the default one: 3]
      late  the orders at 1 s, the hand-overs at LATE_AT (4 s); D counted (x16 in 到 / 队).
              离 = how many of A's (x1) / B (x4) are out of the 150 square round where they stood
              [simulator before round 150: 离 6 from ~s4, 到 30 at ~s15, 队 30 all along]

    BENCH 11-10 (round 150):
      xfer `CampAiXferXfer_mcp_1110_200631`: 到 0 to s13, 8 from s14 (C alone arrives); 队 8 from s1 (the bench's s1 is
        past the 1 s hand-over); 默 0 all 26 s. A computer player's units handed over leave their crew (onto none the
        scripts can name) and drop the order; the player's own: nothing.
      late `CampAiXferLate_mcp_1110_200927`: 离 6 from s1 (A and B had set off), 队 30 to s2, 24 from s3 (A / B off
        their crews at the 4 s hand-over), 到 0 to s13, 24 from s14 (C and the control D arrive; A / B never), 默 0.
        The order is dropped at the hand-over, not refused at the start. sim.py UNIT_AI_TRANSFER branch: off the team
        and Sim.stand; tests/test_simbench.py test_aixfer_*.
    """
    from maps import probe_border
    from parts import Mission, Script, Test, square, status
    import checks.engine_scripts8 as s8

    TANK = 'AlliedAntiVehicleVehicleTech1'
    O = (1300.0, 4300.0)                            # probe_border's 'stop row'
    X0, X1 = 700.0, 1900.0
    ROWS = {'A': ('s4', (4150.0, 4250.0)), 'B': ('s4', (4700.0,)), 'C': ('p1', (4450.0,)), 'D': ('s4', (3950.0,))}
    FAR_R = {'A': 120.0, 'B': 80.0, 'C': 80.0, 'D': 80.0}
    WEIGHT = {'A': 1, 'B': 4, 'C': 8, 'D': 16}
    AT, LATE_AT, RUN = 1.0, 4.0, 25.0


    def _n(part):
        return f'UNIT - CNV AX {part}'


    def mission(name='CampAiXfer'):
        m = Mission(name=name, map=probe_border, units=[], facts={})
        m.spawns |= {TANK}
        for row, (side, ys) in ROWS.items():
            c = m.crew(f'X{row}', side=side)
            kw = {'side': side} if side != 'p1' else {}
            for k, y in enumerate(ys, 1):
                m.put(TANK, 'stop row', X0 - O[0], y - O[1], angle=0.0, name=_n(f'{row} {k}'), role=f'{row} {k}',
                      props={'originalOwner': c}, **kw)
            mid = sum(ys) / len(ys)
            m.waypoint(f'far {row}', f'CNV AX Far {row}', 'stop row', X1 - O[0], mid - O[1])
        return m


    def _roles(row):
        return [f'{row} {k}' for k in range(1, len(ROWS[row][1]) + 1)]


    def _probe(m, late):
        t = Test()
        rows = list(ROWS) if late else ['A', 'B', 'C']
        every = [r for row in ROWS for r in _roles(row)]
        t.scripts.append(Script('Test - AX hold', [], [('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, status('NO_ATTACK'), 1)
                                                       for r in every]))
        team = {row: m.teams[f'X{row}'] for row in ROWS}
        ub, uc = m.role('B 1').name, m.role('C 1').name
        orders = [('MOVE_TEAM_TO', team['A'], m.mark('far A')), ('MOVE_NAMED_UNIT_TO', ub, m.mark('far B')),
                  ('MOVE_TEAM_TO', team['C'], m.mark('far C'))]
        xfers = [('TEAM_AI_TRANSFER', team['A'], 1), ('UNIT_AI_TRANSFER', ub, 1), ('TEAM_AI_TRANSFER', team['C'], 1),
                 ('UNIT_AI_TRANSFER', uc, 1)]
        if late:
            s8.at(t, 'go', AT, orders + [('MOVE_TEAM_TO', team['D'], m.mark('far D'))])
            s8.at(t, 'xfer', LATE_AT, xfers)
        else:                                       # as retail: the order, then the hand-over, in one script
            s8.at(t, 'go', AT, [orders[0], xfers[0], orders[1], xfers[1], orders[2], xfers[2], xfers[3]])
        parts = []
        for row in rows:
            area = f'Test AX Far {row}'
            t.areas[area] = square(*m.point(f'far {row}'), FAR_R[row])
            parts += [(WEIGHT[row], ('NAMED_INSIDE_AREA', m.role(r).name, area)) for r in _roles(row)]
        s8.total(t, 'CNV_AX_Far', '到', parts)
        s8.total(t, 'CNV_AX_Memb', '队', [(WEIGHT[row] * n, ('TEAM_COMPARE_NUM_MEMBERS', team[row], 2, n))
                                         for row in rows for n in range(1, len(ROWS[row][1]) + 1)])
        p4 = m.player('s4')
        t.counters.append(('CNV_AX_Default', '默'))
        t.scripts += [Script(f'Test - AX default {n}', [('TEAM_COMPARE_NUM_MEMBERS', f'{p4}/team{p4}', 2, n)],
                             [('SET_COUNTER', 'CNV_AX_Default', n)], once=False) for n in range(6)]
        if late:
            away = []
            for row in ('A', 'B'):
                for r in _roles(row):
                    area = f'Test AX Home {r}'
                    b = next(o for o in m.objects if o.name == m.role(r).name)
                    t.areas[area] = square(b.x, b.y, 150.0)
                    away.append((WEIGHT[row], ('NAMED_OUTSIDE_AREA', m.role(r).name, area)))
            s8.total(t, 'CNV_AX_Away', '离', away)
        s8.watch(t, RUN)
        return t


    def xfer(m):
        t = _probe(m, late=False)
        t.expect += [('到', RUN - 2, '==', 8), ('队', 1, '==', 8), ('默', 1, '==', 0)]      # bench 11-10 round 150
        return t


    def late(m):
        t = _probe(m, late=True)
        t.expect += [('队', 0, '==', 30, 2),('队', 4, '==', 24), ('离', 2, '==', 6), ('到', RUN - 2, '==', 24),
                     ('默', 1, '==', 0)]           # bench 11-10 round 150
        return t


    MISSION = {'engine_aixfer': mission}
    CHECKS = {'engine_aixfer': {'xfer': xfer, 'late': late}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_basegate():
    """A line: PLAYER_DISABLE_BASE_CONSTRUCTION / PLAYER_ENABLE_BASE_CONSTRUCTION on a real structure queue.

    C's engine_baseban measured the gate against JapanPowerPlantEgg, a UNIT_BUILD core, and saw no gate.
    Here the Allied yard's CONSTRUCTION_YARD_CONSTRUCT button (Command_ConstructAlliedPowerPlant, 800,
    10 s) is pressed by script on both sides; each side also has a powered barracks (engineer, 500).
    a: p1 base-disabled from the start, both yards press at 2 s, p1 enabled at 10 s.
       Prediction: s5 pays 800 over the build; p1 holds 2000 until 10 s, then pays (as the unit gate does).
    (A crossed-category variant was planned and dropped unrun: the press itself queues nothing.)
    Counters: p1 money, s5 money, made code, script logic frame. Made code: p1 plants >= 2 adds 1,
    s5 plants >= 2 adds 10, p1 engineer adds 100, s5 engineer adds 1000 (a finished structure waits
    unplaced, so the plant digits only say whether a press placed one by itself).
    BENCH 11-16 (A269): a 2000/2000/0 from f44 to f377 on BOTH sides -- a script's press of the yard's
    CONSTRUCTION_YARD_CONSTRUCT button queues nothing, so this map reads no gate.
    aibgate:a: 50000 / 1 structure from the wake (f163) to f1054; paying from f1054, 2 at f1208 --
    the base-disabled AI orders nothing till the 70 s enable, then starts as at a wake.
    """
    from maps import probe_border
    from parts import Mission, Script, Test
    from checks import engine_scripts8 as s8
    from checks import engine_aiskirm as ak

    PLANT, ENGINEER = 'AlliedPowerPlant', 'AlliedEngineer'
    PLANT_BUTTON = 'Command_ConstructAlliedPowerPlant'


    def mission():
        m = Mission(name='CampBaseGate', map=probe_border, units=[], facts={})
        m.spawns |= {PLANT, ENGINEER}
        for side, dx in (('p1', 0.), ('s5', 1800.)):
            for template, role, dy in (('AlliedConstructionYard', 'yard', -800.),
                                       ('AlliedPowerPlant', 'power', -650.),
                                       ('AlliedBarracks', 'barracks', -500.)):
                m.put(template, 'stop row', dx, dy, side=side, angle=3.1416,
                      name=f'CNV BaseGate {side} {role}', role=f'{role} {side}')
        return m


    def a(m):
        t = Test()
        t.scripts.append(Script('Test - basegate setup', [], [
            ('MAP_REVEAL_ALL_PERM', m.player('p1')),
            ('PLAYER_SET_MONEY', m.player('p1'), 2000),
            ('PLAYER_SET_MONEY', m.player('s5'), 2000),
            ('PLAYER_DISABLE_BASE_CONSTRUCTION', m.player('p1'))]))
        for side, label in (('p1', '甲资金'), ('s5', '乙资金')):
            counter = f'CNV_BaseGate_{side}'
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Test - basegate money {side}', [], [
                ('SET_PLAYER_MONEY_TO_COUNTER', m.player(side), counter)], once=False))
        s8.total(t, 'CNV_BaseGate_Made', '造出', [
            (w, ('PLAYER_HAS_OBJECT_COMPARISON', m.player(side), 3, n, template))
            for side, template, n, w in (('p1', PLANT, 2, 1), ('s5', PLANT, 2, 10),
                                         ('p1', ENGINEER, 1, 100), ('s5', ENGINEER, 1, 1000))])
        s8.frames(t, 'CNV_BaseGate_Clock', '逻辑帧', [])
        s8.at(t, 'basegate enable', 10., [('PLAYER_ENABLE_BASE_CONSTRUCTION', m.player('p1'))])
        s8.at(t, 'basegate press', 2., [('NAMED_USE_COMMANDBUTTON_ABILITY', f'CNV BaseGate {side} yard', PLANT_BUTTON)
                                        for side in ('p1', 's5')])
        t.bench = [('bench_watch', dict(seconds=32., every=1., sheet=False, lines=4))]
        return t


    def ai(m):
        """aibgate (B's aiskirm mission, s1 AlliedBalanced woken at 10 s with 50000): s1 base-disabled from frame 0,
        enabled at 70 s. Control: aiskirm d (bench 11-07) has 建筑数 2 at 11 s after the wake, 3 at 21, money falling.
        Prediction: 建筑数 stays 1 and money 50000 until 70 s, then the AI starts building."""
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - aibgate setup', [], [
            ('MAP_REVEAL_ALL_PERM', m.player('p1')), ('PLAYER_DISABLE_BASE_CONSTRUCTION', s1)]))
        t.counters.append(('CNV_AIBGate_Money', 'AI钱'))
        t.scripts.append(Script('Test - aibgate money', [], [
            ('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AIBGate_Money')], once=False))
        ak._sum(t, m, s1, 'CNV_AIBGate_Built', '建筑数', ak.BUILDINGS + ak.TOWERS)
        ak._sum(t, m, s1, 'CNV_AIBGate_Army', '兵数', ak.ARMY)
        s8.frames(t, 'CNV_AIBGate_Clock', '逻辑帧', [])
        s8.at(t, 'aibgate enable', 70., [('PLAYER_ENABLE_BASE_CONSTRUCTION', s1)])
        t.bench = [('bench_watch', dict(seconds=105., every=1., sheet=False, lines=4))]
        return t


    MISSION = {'engine_basegate': mission}
    CHECKS = {'engine_basegate': {'a': a}, 'aibgate': {'a': ai}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_conds():
    """Retail-campaign conditions, batch 1 (round 207; the gaps of `inventory_retail.py --part 脚本条件`, the program read in
    work/re/d115_script_semantics.md). Mission on maps/probe_border.py (level ground, every place absolute, as
    benches/script/control/checks.py#engine_scripts9). The enemy crew is on Soviet_4: placed units on a Soviet_1 / 2 / 3 crew are on no team
    (engine_scripts9 rounds 130-136). What the simulator predicts is in brackets.

      team    the player's crew Go (go 1 at (1000, 1000), go 2 at (1000, 1150)), the area Home round them, the area F 700
              east (both squares of half-side 150). go 1 is sent into F at 1 s, go 2 at 6 s; NO_ATTACK set on go 1 at 2 s,
              on go 2 at 4 s; the money set to 5000 at the start and to 4000 at MONEY_AT; a reinforcement team Spawn (one
              Guardian) made at 3 s, TEAM_KILL(Spawn) at 8 s; TEAM_KILL(Go) at GO_KILL_AT.
              队形 (every frame) = 1 TEAM_INSIDE_AREA_PARTIALLY(Go, F, 0) 2 _ENTIRELY(Go, F, 0) 4 TEAM_HAS_UNITS(Go)
                8 TEAM_HAS_UNITS(Spawn) 16 TEAM_CREATED(Spawn) 32 TEAM_CREATED(Go) 64 TEAM_DESTROYED(Spawn)
                128 TEAM_DESTROYED(Go)
              状态 (every frame) = 1 TEAM_SOME_HAVE_OBJECT_STATUS(Go, NO_ATTACK) 2 TEAM_ALL_HAS_OBJECT_STATUS(Go, NO_ATTACK)
                4 PLAYER_HAS_CREDITS(Player_1, >=, 5000) 8 CURRENT_PLATFORM(PC) 16 PARTIALLY(Go, F, 3) 32 PARTIALLY(Go, F, 7)
                64 PLAYER_HAS_CREDITS(Player_1, <, 4500) 128 PARTIALLY(Go, F, 1)
              离开 (only added) = frames NAMED_EXITED_AREA(go 1, Home) held; 建队帧 (only added) = frames TEAM_CREATED(Spawn)
              held (1 = an edge; growing = a state)
              [simulator 11-13 (simcond): 队形 36 to s2 (Go has units 4, Go created 32: a map team is active
              from the start); 60 from s3 (Spawn made: 8 + 16); s8 53 (go 1 in F: +1; Spawn killed, its units gone: -8);
              117 from s9 (TEAM_DESTROYED(Spawn) from the next frame, still created); 119 from s13 (go 2 in F: entirely);
              112 from s24 (Go killed: neither inside nor with units, still created).
              状态 12 to s1 (credits 5000, PC); 13 from s2 (some); 15 from s4 (all); 63 from s8 (go 1 in F: k 3 / 7 read as
              k 0, INFERRED: every Guardian has an AI); 123 from s10 (credits 4000: >= 5000 off, < 4500 on); 74 from s24
              (Go empty: ALL holds on nobody, Generals evaluateTeamHasObjectStatus returns entireTeam). 离开 1 from s1 (an
              edge, INFERRED). 建队帧 +15 a second from s3 (a state, INFERRED)]
      fight   the player's 'shot' (Guardian, (1000, 3000)) and the crew Foe of Soviet_4: foe 1 at (1400, 3000), foe 2 at
              (2900, 3000), both NO_ATTACK. At 1 s NAMED_ATTACK_NAMED(shot, foe 1); NEXT_AFTER s after foe 1 is destroyed,
              NAMED_ATTACK_NAMED(shot, foe 2).
              被打 (every frame) = 1 TEAM_ATTACKED_BY_PLAYER(Foe, Player_1) 2 (Foe, Soviet_5) 4 SKIRMISH_PLAYER_HAS_BEEN_
                ATTACKED_BY_PLAYER(Soviet_4, Player_1) 8 (Soviet_5, Player_1) 16 TEAM_ATTACKED_BY_OBJECTTYPE(Foe, Guardian)
                32 NAMED_ATTACKED_BY_OBJECTTYPE(foe 2, Guardian)
              击杀 (every frame) = 1 PLAYER_HAS_KILLED_NAMED_UNIT(Player_1, foe 1) 2 PLAYER_HAS_KILLED_TYPE_UNITS(Player_1,
                1, Guardian) 4 (Player_1, 2, Guardian) 8 NAMED_HAS_KILLED_COMPARISON_UNIT_TYPE(shot, >=, 1, Guardian)
                16 TEAM_DESTROYED(Foe) 32 NAMED_HAS_KILLED_COMPARISON_UNIT_TYPE(shot, ==, 1, Guardian)
              甲 / 乙 = foe 1's / foe 2's health % (a dead one's counter keeps its last value)
              [simulator 11-13: 被打 0, 21 from s5 (the first hit: 1 + 4 + 16) while foe 1 lives; 4 from s20 (foe 1
              dead: the team version reads its living members' last damage, D 115; the player-level flag stays); 53 from
              s44 (foe 2 hit: + 1 + 16 + 32); 4 from s59 (both dead). 击杀 0, 43 from s20 (foe 1: 1 + 2 + 8 + 32), 31 from
              s59 (foe 2: + 4 + 16, == 1 off). 甲 93 at s5 -> 0 at s20; 乙 100 to s43, 0 at s59]
      sight   (round 210; batch 2, d115_script_semantics.md 4-6, 15) every unit NO_ATTACK. The player's crew Watch (watch,
              (1000, 4500)); Soviet_4's crews Near (near, 230 east of watch: inside the sight 200 + the two radii 23 only),
              Spy (spy, 1200 east, sent to 400 east at 1 s) and Navy (a Dreadnought on dry land, (2300, 4850): Surfaces
              DEEP_WATER only) in the area N. near to 300 east at 4 s, back to 180 at 9 s, NAMED_KILLed at 14 s. Hot spots
              H1 / H2 (the map's MissionHotSpots): SET_ACTIVENESS(H1, 1) at 2 s, (Nope, 1) at 3 s (not on the map),
              VISIBILITY(H2, 1) at 4 s, LINK(H2, near, 0) at 5 s, SET(H1, 0) at 6 s, SET(H2, 1) at 16 s (its linked unit dead).
              视野 = 1 ENEMY_SIGHTED_BY_TEAM(Watch, Enemy, Soviet_4) 2 (Watch, Friend, Soviet_4) 4 (Watch, Friend, Player_1)
                8 (Near, Enemy, Player_1) 16 (Watch, Neutral, Soviet_4) 32 (Spy, Enemy, Player_1)
              发现 = 1 TEAM_DISCOVERED(Player_1, Near) 2 (Player_1, Spy) 4 (Soviet_4, Watch) 8 (Player_1, Watch)
                16 (Soviet_5, Watch)
              海军 = 1 PARTIALLY(Navy, N, 0) 2 (Navy, N, 1) 4 (Navy, N, 3) 8 (Navy, N, 7) 16 TEAM_HAS_UNITS(Navy)
                32 PARTIALLY(Watch, W, 1) 64 PARTIALLY(Watch, W, 0)
              热点 = 1 MISSION_HOT_SPOT_ACTIVE(H1) 2 (H2) 4 (Nope) 8 (h1, lower case)
              [simulator 11-13 (simcond): 视野 13 (1 near inside the circles' reach, 4 watch itself, 8 near sees
              watch; INFERRED the member itself counts) / 4 from s5 (near at 300) / 13 from s10 / 4 from s14 (near dead).
              发现 13 (Near seen, Soviet_4 sees Watch, the player's own) / 15 from s10 (spy within the player's sight 500) /
              14 from s14. 海军 88 all along (k 7 + alive + watch k 0: the ship never for k 0, D 119's prediction).
              热点 0 / 9 s2-s5 (case ignored, INFERRED) / 0 / 2 from s16; Nope, VISIBILITY and LINK never]
      BENCH 11-13 (round 210, run_queue; tests/test_simbench.py test_conds_sight_as_the_bench): 视野 / 发现 / 海军 / 热点
        s1-s2 4 13 88 1 | s3 4 12 88 1 | s4 4 13 88 1 | s5-s7 4 13 88 0 | s8 4 12 88 0 | s9 13 12 88 0 | s10-s12 13 15 88 0 |
        s13 5 14 88 0 | s14-s24 5 14 88 2 | s25 4 14 88 2. Against the prediction: near at 230 unseen (视野&1, &8 off until
        it stands at 180: centre to centre, not + both radii); its wreck seen ~11 s after the kill (&1 s13-s24); near off
        for 发现&1 while it moves (s3, s8-s9); the lower-case hot spot name never on (&8). The rest as predicted -- D 119's
        ship never for k 0. The simulator fixed to the first, third and fourth (simcond); the wreck's time
        is the Guardian's SlowDeath (0 s in the simulator), left to the module lines.
      pf      (round 329) no orders at all. 平台 (every frame) = 1 CURRENT_PLATFORM(360) 2 (PS3) 4 PLAYER_TRIGGERED_
              SCRIPT_EVENT(Player_1, ATTACK_MOVE_ISSUED) 8 CURRENT_PLATFORM(360) and that event (s01's one use: every OR
              clause of its script asks 360) 16 CURRENT_PLATFORM(PC). [simulator: 16 all along -- the program answers
              true for 'PC' only (work/re a329); no human gives the event]

    BENCH 11-13 (round 208, run_queue; tests/test_simbench.py test_conds_team_as_the_bench / _fight_):
      team (with the 128 bits): 队形 / 状态 s1 4 13 | s2 12 13 | s3-s6 12 15 | s7-s8 5 15 | s9-s10 5 75 | s11-s21 7 75 |
        s22-s31 128 74; 离开 1, 建队帧 1. Against the prediction: TEAM_CREATED holds one frame after the making (建队帧
        1) and never for the map team Go (32 never); TEAM_DESTROYED(Spawn) never after its TEAM_KILL while
        TEAM_DESTROYED(Go) holds after Go's (128); PARTIALLY with k 3 / 7 / 1 never for the Guardians (16 / 32 / 128).
        The rest as predicted (ALL_HAS on the emptied Go: 74). The simulator fixed to all three (simcond,
        TEAM_DESTROYED); the bench's seconds run a second or two before the simulator's.
      fight: 被打 / 击杀 s1-s2 0 0 | s3-s15 21 0 | s16-s38 4 43 | s39-s52 53 43 | s53-s71 4 31; 甲 87 at s3 .. 12 at s14,
        kept 12; 乙 87 at s39 .. 12 at s52, kept. Every bit as predicted (the fire sooner than the simulator's).
    """
    from maps import probe_border
    from parts import Mission, Script, Test, square, status
    import checks.engine_scripts8 as s8

    TANK = 'AlliedAntiVehicleVehicleTech1'
    O = (1300.0, 4300.0)                            # probe_border's 'stop row'
    MONEY_AT, GO_KILL_AT, NEXT_AFTER = 10.0, 24.0, 4.0
    RUN = {'team': 30.0, 'fight': 70.0}
    GO = {'go 1': (1000.0, 1000.0), 'go 2': (1000.0, 1150.0)}
    HOME, F = (1000.0, 1075.0), (1700.0, 1075.0)
    SPAWN = (1000.0, 2000.0)
    SHOT, FOE = (1000.0, 3000.0), {'foe 1': (1400.0, 3000.0), 'foe 2': (2900.0, 3000.0)}
    GE, LT, EQ = 3, 0, 2                            # sim.CMP: 0 <, 1 <=, 2 ==, 3 >=, 4 >, 5 !=
    SHIP = 'SovietAntiStructureShip'                # the Dreadnought: Locomotor Surfaces DEEP_WATER only
    WATCH, NEAR, NEAR_OUT, NEAR_IN = (1000.0, 4500.0), (1230.0, 4500.0), (1300.0, 4500.0), (1180.0, 4500.0)
    SPY, SPY_TO, NAVY = (2200.0, 4500.0), (1400.0, 4500.0), (2300.0, 4850.0)
    RUN['sight'] = 24.0
    H1, H2 = 'Test Cond H1', 'Test Cond H2'


    def _n(part):
        return f'UNIT - CNV Cond {part.title()}'


    def _put(m, template, x, y, **kw):
        m.put(template, 'stop row', x - O[0], y - O[1], **kw)


    def _mark(m, part, x, y):
        m.waypoint(part, f'Test Cond {part.title()}', 'stop row', x - O[0], y - O[1])


    def mission():
        m = Mission(name='CampConds', map=probe_border, units=[], facts={})
        m.spawns |= {TANK}
        go = m.crew('Go')
        for role, (x, y) in GO.items():
            _put(m, TANK, x, y, angle=0.0, name=_n(role), role=role, props={'originalOwner': go})
            _mark(m, f'to {role}', x + F[0] - HOME[0], y)
        m.reinforcement('Spawn', [(TANK, 1)], 'p1')
        _mark(m, 'spawn', *SPAWN)
        _put(m, TANK, *SHOT, angle=0.0, name=_n('shot'), role='shot')
        foe = m.crew('Foe', side='s4')
        for role, (x, y) in FOE.items():
            _put(m, TANK, x, y, side='s4', angle=3.1416, name=_n(role), role=role, props={'originalOwner': foe})
        # sight (round 210): the player's Watch, Soviet_4's Near / Spy / Navy (a Dreadnought on dry land)
        for key, role, side, template, (x, y) in (('Watch', 'watch', 'p1', TANK, WATCH), ('Near', 'near', 's4', TANK, NEAR),
                                                  ('Spy', 'spy', 's4', TANK, SPY), ('Navy', 'navy', 's4', SHIP, NAVY)):
            m.spawns |= {template}
            _put(m, template, x, y, side=side, angle=0.0 if side == 'p1' else 3.1416,
                 name=_n(role), role=role, props={'originalOwner': m.crew(key, side=side)})
        for part, (x, y) in (('near out', NEAR_OUT), ('near in', NEAR_IN), ('spy to', SPY_TO)):
            _mark(m, part, x, y)
        return m


    def _frames(t, counter, label, cond):
        s8.frames(t, counter, label, [cond])


    def team(m):
        t = Test()
        p1, go, spawn = m.player(), m.teams['Go'], m.teams['RSpawn']
        na = status('NO_ATTACK')
        t.areas['Test Cond Home'] = square(*HOME, 150.0)
        t.areas['Test Cond F'] = square(*F, 150.0)
        t.scripts.append(Script('Test - Cond start', [], [('PLAYER_SET_MONEY', p1, 5000)]))
        s8.at(t, 'go1', 1.0, [('MOVE_NAMED_UNIT_TO', m.role('go 1').name, m.mark('to go 1'))])
        s8.at(t, 'na1', 2.0, [('UNIT_CHANGE_OBJECT_STATUS', m.role('go 1').name, na, 1)])
        s8.at(t, 'make', 3.0, [('CREATE_REINFORCEMENT_TEAM', spawn, m.mark('spawn'))])
        s8.at(t, 'na2', 4.0, [('UNIT_CHANGE_OBJECT_STATUS', m.role('go 2').name, na, 1)])
        s8.at(t, 'go2', 6.0, [('MOVE_NAMED_UNIT_TO', m.role('go 2').name, m.mark('to go 2'))])
        s8.at(t, 'kills', 8.0, [('TEAM_KILL', spawn)])
        s8.at(t, 'money', MONEY_AT, [('PLAYER_SET_MONEY', p1, 4000)])
        s8.at(t, 'killgo', GO_KILL_AT, [('TEAM_KILL', go)])
        s8.total(t, 'CNV_Cond_Team', '队形', [
            (1, ('TEAM_INSIDE_AREA_PARTIALLY', go, 'Test Cond F', 0)),
            (2, ('TEAM_INSIDE_AREA_ENTIRELY', go, 'Test Cond F', 0)),
            (4, ('TEAM_HAS_UNITS', go)), (8, ('TEAM_HAS_UNITS', spawn)),
            (16, ('TEAM_CREATED', spawn)), (32, ('TEAM_CREATED', go)), (64, ('TEAM_DESTROYED', spawn)),
            (128, ('TEAM_DESTROYED', go))])
        s8.total(t, 'CNV_Cond_State', '状态', [
            (1, ('TEAM_SOME_HAVE_OBJECT_STATUS', go, na)), (2, ('TEAM_ALL_HAS_OBJECT_STATUS', go, na)),
            (4, ('PLAYER_HAS_CREDITS', p1, GE, 5000)), (8, ('CURRENT_PLATFORM', 'PC')),
            (16, ('TEAM_INSIDE_AREA_PARTIALLY', go, 'Test Cond F', 3)),
            (32, ('TEAM_INSIDE_AREA_PARTIALLY', go, 'Test Cond F', 7)),
            (64, ('PLAYER_HAS_CREDITS', p1, LT, 4500)),
            (128, ('TEAM_INSIDE_AREA_PARTIALLY', go, 'Test Cond F', 1))])
        _frames(t, 'CNV_Cond_Exit', '离开', ('NAMED_EXITED_AREA', m.role('go 1').name, 'Test Cond Home'))
        _frames(t, 'CNV_Cond_Made', '建队帧', ('TEAM_CREATED', spawn))
        s8.watch(t, RUN['team'])
        return t


    def fight(m):
        t = Test()
        p1, s4, s5, foe = m.player(), m.player('s4'), m.player('s5'), m.teams['Foe']
        shot, f1, f2 = (m.role(r).name for r in ('shot', 'foe 1', 'foe 2'))
        t.scripts.append(Script('Test - Cond hold', [], [('UNIT_CHANGE_OBJECT_STATUS', n, status('NO_ATTACK'), 1)
                                                          for n in (f1, f2)]))
        s8.at(t, 'attack', 1.0, [('NAMED_ATTACK_NAMED', shot, f1)])
        t.scripts += [Script('Test - Cond foe 1 down', [('NAMED_DESTROYED', f1)],
                             [('SET_MILLISECOND_TIMER', 'Test Cond Next', NEXT_AFTER)]),
                      Script('Test - Cond next', [('TIMER_EXPIRED', 'Test Cond Next')], [('NAMED_ATTACK_NAMED', shot, f2)])]
        s8.total(t, 'CNV_Cond_Hit', '被打', [
            (1, ('TEAM_ATTACKED_BY_PLAYER', foe, p1)), (2, ('TEAM_ATTACKED_BY_PLAYER', foe, s5)),
            (4, ('SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER', s4, p1)),
            (8, ('SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER', s5, p1)),
            (16, ('TEAM_ATTACKED_BY_OBJECTTYPE', foe, TANK)), (32, ('NAMED_ATTACKED_BY_OBJECTTYPE', f2, TANK))])
        s8.total(t, 'CNV_Cond_Kill', '击杀', [
            (1, ('PLAYER_HAS_KILLED_NAMED_UNIT', p1, f1)), (2, ('PLAYER_HAS_KILLED_TYPE_UNITS', p1, 1, TANK)),
            (4, ('PLAYER_HAS_KILLED_TYPE_UNITS', p1, 2, TANK)),
            (8, ('NAMED_HAS_KILLED_COMPARISON_UNIT_TYPE', shot, GE, 1, TANK)), (16, ('TEAM_DESTROYED', foe)),
            (32, ('NAMED_HAS_KILLED_COMPARISON_UNIT_TYPE', shot, EQ, 1, TANK))])
        for role, counter, label in (('foe 1', 'CNV_Cond_H1', '甲'), ('foe 2', 'CNV_Cond_H2', '乙')):
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Test - {counter}', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',
                                                               m.role(role).name, counter)], once=False))
        s8.watch(t, RUN['fight'])
        return t


    def sight(m):
        t = Test()
        p1, s4, s5 = m.player(), m.player('s4'), m.player('s5')
        watch, near, spy, navy = (m.teams[k] for k in ('Watch', 'Near', 'Spy', 'Navy'))
        t.hotspots = {H1: ('', ''), H2: ('', '')}
        t.areas['Test Cond N'] = square(*NAVY, 150.0)
        t.areas['Test Cond W'] = square(*WATCH, 100.0)
        t.scripts.append(Script('Test - Cond sight hold', [], [
            ('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, status('NO_ATTACK'), 1) for r in ('watch', 'near', 'spy', 'navy')]))
        s8.at(t, 'spy', 1.0, [('MOVE_NAMED_UNIT_TO', m.role('spy').name, m.mark('spy to'))])
        s8.at(t, 'h1on', 2.0, [('SET_MISSION_HOT_SPOT_ACTIVENESS', H1, 1)])
        s8.at(t, 'nope', 3.0, [('SET_MISSION_HOT_SPOT_ACTIVENESS', 'Test Cond Nope', 1)])
        s8.at(t, 'out', 4.0, [('SET_MISSION_HOT_SPOT_VISIBILITY', H2, 1),
                              ('MOVE_NAMED_UNIT_TO', m.role('near').name, m.mark('near out'))])
        s8.at(t, 'link', 5.0, [('LINK_MISSION_HOT_SPOT_TO_OBJECT', H2, m.role('near').name, 0)])
        s8.at(t, 'h1off', 6.0, [('SET_MISSION_HOT_SPOT_ACTIVENESS', H1, 0)])
        s8.at(t, 'in', 9.0, [('MOVE_NAMED_UNIT_TO', m.role('near').name, m.mark('near in'))])
        s8.at(t, 'kill', 14.0, [('NAMED_KILL', m.role('near').name)])
        s8.at(t, 'h2on', 16.0, [('SET_MISSION_HOT_SPOT_ACTIVENESS', H2, 1)])
        s8.total(t, 'CNV_Cond_Sight', '视野', [
            (1, ('ENEMY_SIGHTED_BY_TEAM', watch, 'Enemy', s4)), (2, ('ENEMY_SIGHTED_BY_TEAM', watch, 'Friend', s4)),
            (4, ('ENEMY_SIGHTED_BY_TEAM', watch, 'Friend', p1)), (8, ('ENEMY_SIGHTED_BY_TEAM', near, 'Enemy', p1)),
            (16, ('ENEMY_SIGHTED_BY_TEAM', watch, 'Neutral', s4)), (32, ('ENEMY_SIGHTED_BY_TEAM', spy, 'Enemy', p1))])
        s8.total(t, 'CNV_Cond_Found', '发现', [
            (1, ('TEAM_DISCOVERED', p1, near)), (2, ('TEAM_DISCOVERED', p1, spy)), (4, ('TEAM_DISCOVERED', s4, watch)),
            (8, ('TEAM_DISCOVERED', p1, watch)), (16, ('TEAM_DISCOVERED', s5, watch))])
        s8.total(t, 'CNV_Cond_Navy', '海军', [
            (1, ('TEAM_INSIDE_AREA_PARTIALLY', navy, 'Test Cond N', 0)),
            (2, ('TEAM_INSIDE_AREA_PARTIALLY', navy, 'Test Cond N', 1)),
            (4, ('TEAM_INSIDE_AREA_PARTIALLY', navy, 'Test Cond N', 3)),
            (8, ('TEAM_INSIDE_AREA_PARTIALLY', navy, 'Test Cond N', 7)), (16, ('TEAM_HAS_UNITS', navy)),
            (32, ('TEAM_INSIDE_AREA_PARTIALLY', watch, 'Test Cond W', 1)),
            (64, ('TEAM_INSIDE_AREA_PARTIALLY', watch, 'Test Cond W', 0))])
        s8.total(t, 'CNV_Cond_Spot', '热点', [
            (1, ('MISSION_HOT_SPOT_ACTIVE', H1)), (2, ('MISSION_HOT_SPOT_ACTIVE', H2)),
            (4, ('MISSION_HOT_SPOT_ACTIVE', 'Test Cond Nope')), (8, ('MISSION_HOT_SPOT_ACTIVE', H1.lower()))])
        s8.watch(t, RUN['sight'])
        return t


    def pf(m):
        t, p1, n = Test(), m.player(), 'CNV_Cond_Plat'
        s8.total(t, n, '平台', [(1, ('CURRENT_PLATFORM', '360')), (2, ('CURRENT_PLATFORM', 'PS3')),
                                (4, ('PLAYER_TRIGGERED_SCRIPT_EVENT', p1, 'ATTACK_MOVE_ISSUED')),
                                (16, ('CURRENT_PLATFORM', 'PC'))])
        t.scripts.append(Script(f'Test - {n} s01', [('CURRENT_PLATFORM', '360'), ('PLAYER_TRIGGERED_SCRIPT_EVENT', p1,
                                                     'ATTACK_MOVE_ISSUED')], [('INCREMENT_COUNTER', 8, n)], once=False))
        s8.watch(t, 6.0)
        return t


    MISSION = {'engine_conds': mission}
    CHECKS = {'engine_conds': {'team': team, 'fight': fight, 'sight': sight, 'pf': pf}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def drive():
    """Can the map's scripts play the player's side? (benches/script/control/scenes.py#drive; ADR 0010's graybox runs a level unattended
    under a "playstyle script" and reads the verdict off the counters.)

    prod: the player's barracks and 6000 money, a variant waking (or not) whatever might make it build -- read: money
      spent, infantry made (the control, drive_idle, shows what a barracks does alone: nothing);
    cmds: the three order kinds on the player's own units -- one Guardian moved by name, one told to attack a Hammer by
      name, then the whole default team attack-moved at the front;
    run: a playstyle script end to end -- the team attack-moves every ORDER_EVERY s, one Guardian is given at the base
      every GIVE_EVERY s (what a barracks would make), a flag stops the clock when one side is gone. Read at the end:
      enemy Hammers left, our Guardians left, seconds, Guardians given.
    """
    from parts import NOT, Script, Test, counted, kindof, square

    WHOLE = 'Test Whole Map'
    GUARDIAN, HAMMER = 'AlliedAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech1'


    def base(m):
        t = Test()
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('PLAYER_SET_MONEY', m.player('p1'), m.facts['money'])]))
        t.areas[WHOLE] = square(2500.0, 2500.0, 2600.0)
        return t


    def production(wake):
        """wake: the actions that start the experiment at 3 s, from the mission and the test ([] = the control)."""
        def check(m):
            t, p1 = base(m), m.player('p1')
            t.waypoints['Test Base'] = m.site('base yard')
            t.scripts.append(Script('Test - go timer', [], [('SET_MILLISECOND_TIMER', 'Test Go', 3.0)]))
            acts = wake(p1)
            if acts:
                t.scripts.append(Script('Test - wake', [('TIMER_EXPIRED', 'Test Go')], acts))
            t.counters.append(('Test_Money', '资金'))
            t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'Test_Money')], once=False))
            counted('Test_Infantry', '我方步兵', t, area=WHOLE, kind=kindof('INFANTRY'))
            counted('Test_Guardians', '守护者', t, template=GUARDIAN)
            counted('Test_Power', '电厂', t, template='AlliedPowerPlant')
            if acts:
                t.expect += [('资金', 4, 'ever<', m.facts['money'] - 500), ('我方步兵', 4, 'ever>=', 1)]
            else:
                t.expect += [('资金', 4, '==', m.facts['money']), ('我方步兵', 4, '==', 0)]
            t.bench = [('bench_watch', dict(seconds=80, every=5, sheet=False, lines=len(t.counters)))]
            return t
        return check


    def ai_wake(p1):
        return [('SKIRMISH_AI_START', p1), ('SKIRMISH_AI_MAKE_BASE', p1, 'Test Base')]


    def enable_wake(p1):
        return [('PLAYER_ENABLE_UNIT_CONSTRUCTION', p1), ('PLAYER_ENABLE_BASE_CONSTRUCTION', p1)]


    def commands(m):
        """g1 walks to the west field by name, g2 attacks the Hammer by name (its health drops), at 40 s the whole team
        attack-moves at the front (the Hammer dies, g3 who stood still joins in)."""
        t = base(m)
        team, enemy = m.team('p1'), m.player('s1')
        g1, g2, g3 = (m.role(f'guardian {k}').name for k in (1, 2, 3))
        hammer = m.role('hammer 1').name
        t.waypoints['Test Move'] = m.site('west field')
        t.waypoints['Test Front'] = m.site('front')
        t.areas['Test Move Area'] = square(*m.site('west field'), 120.0)
        t.scripts += [Script('Test - timers', [], [('SET_MILLISECOND_TIMER', 'Test Named', 3.0),
                                                   ('SET_MILLISECOND_TIMER', 'Test Team', 40.0)]),
                      Script('Test - named', [('TIMER_EXPIRED', 'Test Named')],
                             [('MOVE_NAMED_UNIT_TO', g1, 'Test Move'), ('NAMED_ATTACK_NAMED', g2, hammer)]),
                      Script('Test - team', [('TIMER_EXPIRED', 'Test Team')],
                             [('ATTACK_MOVE_TEAM_TO', team, 'Test Front')])]
        counted('Test_Moved', '走到了', t, named=g1, area='Test Move Area')
        counted('Test_Hammer', '铁锤血量', t, health=hammer)
        counted('Test_Hammers', '铁锤数', t, template=HAMMER, player=enemy)
        counted('Test_Guardians', '守护者', t, template=GUARDIAN)
        t.expect += [('走到了', 5, 'ever==', 1, 40.0), ('铁锤血量', 5, 'ever<', 100, 40.0), ('铁锤数', 40, 'ever==', 0)]
        t.bench = [('bench_watch', dict(seconds=100, every=5, sheet=False, lines=len(t.counters), until='c3==0'))]
        return t


    def run(m):
        t = base(m)
        f, team, enemy = m.facts, m.team('p1'), m.player('s1')
        t.waypoints['Test Enemy'] = m.site('front')
        t.waypoints['Test Give'] = m.site('base edge', -80, 0)
        over = ('FLAG', 'Test Over', 1, NOT)
        t.scripts += [
            Script('Test - timers', [], [('SET_MILLISECOND_TIMER', 'Test Order', 3.0), ('SET_MILLISECOND_TIMER', 'Test Give', f['give every']),
                                         ('SET_MILLISECOND_TIMER', 'Test Tick', 1.0)]),
            Script('Test - order', [('TIMER_EXPIRED', 'Test Order'), over], [('ATTACK_MOVE_TEAM_TO', team, 'Test Enemy')], once=False),
            Script('Test - order again', [('TIMER_EXPIRED', 'Test Order')], [('SET_MILLISECOND_TIMER', 'Test Order', f['order every'])], once=False),
            Script('Test - give', [('TIMER_EXPIRED', 'Test Give'), over],
                   [('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', GUARDIAN, team, 'Test Give'), ('INCREMENT_COUNTER', 1, 'Test_Given')], once=False),
            Script('Test - give again', [('TIMER_EXPIRED', 'Test Give')], [('SET_MILLISECOND_TIMER', 'Test Give', f['give every'])], once=False),
            Script('Test - clock', [('TIMER_EXPIRED', 'Test Tick'), over], [('INCREMENT_COUNTER', 1, 'Test_Time')], once=False),
            Script('Test - clock again', [('TIMER_EXPIRED', 'Test Tick')], [('SET_MILLISECOND_TIMER', 'Test Tick', 1.0)], once=False),
            Script('Test - won', [('COUNTER', 'Test_Time', 3, 3), ('COUNTER', 'Test_Enemy', 2, 0)], [('SET_FLAG', 'Test Over', 1)]),
            Script('Test - lost', [('COUNTER', 'Test_Time', 3, 3), ('COUNTER', 'Test_Ours', 2, 0)], [('SET_FLAG', 'Test Over', 1)])]
        counted('Test_Enemy', '敌方铁锤', t, template=HAMMER, player=enemy)
        counted('Test_Ours', '我方守护者', t, template=GUARDIAN)
        t.counters += [('Test_Time', '用时'), ('Test_Given', '补兵数')]
        t.expect += [('敌方铁锤', 20, 'ever==', 0), ('用时', 20, 'ever>=', 20)]
        watch = dict(seconds=120, every=5, sheet=False, lines=len(t.counters), until='c1==0|c2==0')
        t.bench = [('bench_watch', watch)] * 3
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'drive_idle': {'prod': production(lambda p1: [])},
        'drive_ai': {'prod': production(ai_wake)},
        'drive_enable': {'prod': production(enable_wake)},
        'drive_cmd': {'cmds': commands},
        'drive_run': {'run': run},
    }
    return dict(CHECKS=CHECKS)


def engine_killcount():
    """Native kill/type/player contrast; prediction and evidence: work/re/c_killcount_report.md.

    A orders p1's three Guardians to kill two Conscripts and one Guardian; B orders
    s5 instead. Untouched other-side crews remain NO_ATTACK. All victims start at
    1% HP and cannot attack/move. Script kills a separate untouched Conscript at
    15s; another lives. Predict active infantry/tank kills 2/1, inactive infantry 0,
    alive mask 240 (inactive three plus untouched control), excluding script death.
    Counters start at 77 to prove each query overwrites rather than increments.
    """
    from parts import Script, Test, status
    from checks import engine_scripts8 as s8


    def check(m, active):
        t = Test()
        other = 's5' if active == 'p1' else 'p1'
        roles = [f'{side} {kind} {i}' for side in ('p1', 's5')
                 for i in range(3) for kind in ('gun', 'victim')] + ['script', 'alive']
        setup = [('MAP_REVEAL_ALL_PERM', m.player()),
                 ('PLAYER_RELATES_PLAYER', m.player(active), m.player('s4'), (0, 0., 'Enemy')),
                 ('PLAYER_RELATES_PLAYER', m.player('s4'), m.player(active), (0, 0., 'Enemy'))]
        for role in roles:
            name = m.role(role).name
            setup += [('UNIT_CHANGE_OBJECT_STATUS', name, status('NO_ATTACK'), 1),
                      ('UNIT_CHANGE_OBJECT_STATUS', name, status('IMMOBILE'), 1)]
            if 'victim' in role:
                setup.append(('UNIT_SET_HEALTH', name, 1.))
        t.scripts.append(Script('Test - kill setup', [], setup))
        for i, sec in enumerate((3., 7., 11.)):
            gun = m.role(f'{active} gun {i}').name
            s8.at(t, f'kill fire {i}', sec, [
                ('UNIT_CHANGE_OBJECT_STATUS', gun, status('NO_ATTACK'), 0),
                ('NAMED_ATTACK_NAMED', gun, m.role(f'{active} victim {i}').name)])
        s8.at(t, 'kill script', 15., [('NAMED_KILL', m.role('script').name)])
        for i, (side, kind, label) in enumerate(((active, 'SovietAntiInfantryInfantry', '主步兵'),
                                               (active, 'AlliedAntiVehicleVehicleTech1', '主坦克'),
                                               (other, 'SovietAntiInfantryInfantry', '另步兵'))):
            counter = f'CNV_Kills_{i}'
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Test - query kills {i}', [], [
                ('SET_COUNTER', counter, 77),
                ('SET_PLAYER_KILLS_OF_TYPE_TO_COUNTER', m.player(side), kind, counter)], once=False))
        victims = [f'{active} victim {i}' for i in range(3)] + ['script'] + [
            f'{other} victim {i}' for i in range(3)] + ['alive']
        s8.total(t, 'CNV_Kills_Alive', '存活码', [
            (1 << i, ('NAMED_NOT_DESTROYED', m.role(role).name)) for i, role in enumerate(victims)])
        t.expect = [('主步兵', 22., '==', 2), ('主坦克', 22., '==', 1),
                    ('另步兵', 22., '==', 0), ('存活码', 22., '==', 240)]
        s8.watch(t, 25.)
        return t


    def a(m):
        return check(m, 'p1')


    def b(m):
        return check(m, 's5')


    CHECKS = {'engine_killcount': {'a': a, 'b': b}}
    return dict(CHECKS=CHECKS)


def engine_kind():
    """Retail-campaign conditions, batch 7 (round 243): PLAYER_HAS_COMPARISON_UNIT_KIND (3 uses: s04 (Player_1, ==, 0,
    BEACON), ep01 (Allied02, <=, 3, FS_FACTORY), ep01 (Player_1, >, 0, ENGINEER)), PLAYER_LOST_OBJECT_TYPE (2: j06
    (Player_1, the map's object list '_object list_japan all structs'), ep01 (Player_1, sovietchiefengineer -- an
    Uprising unit the SDK lacks: AlliedEngineer stands in)) and NAMED_DESTROYED_BY_OBJECTTYPE (2, a04: (King Oni,
    alliedcommandotech1) OR (King Oni, sovietcommandotech1) -> the bonus crate). Mission on maps/probe_border.py (level
    ground), every place absolute; clear of probe_range's lanes (y 400, 1200-1900, 3300-3750) and the start (1250, 2500).
    No trigger areas.

      all  kinds and losses: the player's AlliedEngineers eng p (1800, 2300) / eng p2 (1800, 2900), war factory F1
           (2500, 2400) and barracks F2 (3300, 2400); Soviet_4's war factory G1 (4200, 2400) and barracks G2 (4400,
           2950). Soviet_4's AlliedEngineer eng e (1000, 4600), Guardian truck w (2200, 4600) and King Oni (3600, 4600);
           the player's Tanya A (1000, 4000), Guardian gun (2200, 4000), Tanya B (3600, 4000): 600 north of their marks,
           beyond sight (200 / shroud 400). Every Soviet_4 unit and the player's engineers NO_ATTACK; truck w at 5 %.
           Object list 'CNV Kind Structs' = {AlliedWarFactory, AlliedBarracks} at 0 s.
           gun -> truck w at 2 s; NAMED_KILL eng p 4 s; Tanya A -> eng e 6 s (pistols); Tanya B -> King Oni 10 s (her
           charge: a vehicle); NAMED_KILL F1 12 s, eng p2 16 s, G1 20 s.
           种 (every frame) = 1 PLAYER_HAS_COMPARISON_UNIT_KIND(Player_1, >, 0, ENGINEER) 2 (Player_1, ==, 0, BEACON)
             4 (Soviet_4, <=, 3, FS_FACTORY) 8 (Soviet_4, >=, 1, ENGINEER) 16 (Player_1, ==, 2, FS_FACTORY)
           失 (adds its weight every frame a reader holds, never reset; in this order) = 1 PLAYER_LOST_OBJECT_TYPE(
             Player_1, AlliedEngineer) 2 (the same again) 4 (Soviet_4, AlliedEngineer) 8 (Player_1, AlliedWarFactory)
             16 (Player_1, 'CNV Kind Structs') 32 (Soviet_4, AlliedWarFactory)
           毁 (every frame) = 1 NAMED_DESTROYED_BY_OBJECTTYPE(eng e, alliedcommandotech1) 2 (King Oni,
             alliedcommandotech1) 4 (King Oni, sovietcommandotech1) 8 (truck w, alliedantivehiclevehicletech1)
             16 (eng p, alliedcommandotech1: a script's kill)
      [prediction from the data. PLAYER_HAS_COMPARISON_UNIT_KIND: Generals has only the _IN_TRIGGER_AREA one, which
       counts the one player's living non-INERT objects of the KindOf; RA3's _IN_TRIGGER_AREA was read (bench 10-25
       probe/count) to count EVERY player's objects. The two read apart here -- own (H-own): 31 to ~7 s (eng e dies:
       &8 off) 23, 12 s 7 (F1: &16 off), 16 s 6 (eng p2: &1 off), 6 after G1; every player's (H-all): 11 (4 FS_FACTORY:
       &4 / &16 off), 11 after eng e (eng p2 still an ENGINEER, any owner), 12 s 15 (3: &4 on), 16 s 6, 20 s 22 (2:
       &16 on). BEACON: only props (AIBeacon, MultiplayerBeacon ...) carry it, none here: &2 all run either way.
       PLAYER_LOST_OBJECT_TYPE (Generals evaluatePlayerLostObjectType): ONE stored count per (player, type string), the
       player's living objects of the type(s); a reader that finds fewer than stored stores the new count and is true
       -- one frame, and only for the first reader of that string (the second never sees it); a rise is stored
       silently. 失 1 at 4 s, 5 at ~7 s, 29 at 12 s (+8 +16: the list is its own string), 30 at 16 s, 62 at 20 s;
       per-reader memory would read 3 / 7 / 31 / 34 / 66. NAMED_DESTROYED_BY_OBJECTTYPE (RA3 only, no source): dead,
       and its killer's template that type; a script's kill has no killer. 毁 8 from ~3 s, 9 from ~7 s, 11 from ~13 s
       if her charge's kill is credited to Tanya (9 if to the charge object).]
      [bench 11-15 CampKindAll_mcp_1115_045506 (round 244): 种 11 / s11 15 / s15 6 / s18 22 -- every player's (H-all);
       失 s3 1 / s11 25 / s13 29 (eng e died late: Tanya walked) / s15 30 / s18 62 -- one shared count (the second
       reader never); 毁 0 all run. The steps ~1-2 s before the script timers.]

      by   all's units and timers, 毁 split into counters that add every evaluation (see by()). [bench 11-15
           CampKindBy_mcp_1115_045838: 死 s2 8 (eng p), s6 10 (truck w), s13 11 (eng e), s20 15 (King Oni); 毁 坦 王 0
           all run -- NAMED_DESTROYED_BY_OBJECTTYPE never true, not one evaluation, either case, any killer.]
    """
    from maps import probe_border
    from parts import Mission, Script, Test, kindof, status
    import checks.engine_scripts8 as s8

    TANK, ENG, TANYA, KING = ('AlliedAntiVehicleVehicleTech1', 'AlliedEngineer', 'AlliedCommandoTech1', 'JapanMechaKing')
    NATASHA = 'SovietCommandoTech1'
    FACTORY, BARRACKS = 'AlliedWarFactory', 'AlliedBarracks'
    O = (1300.0, 4300.0)                            # probe_border's 'stop row'
    UNITS = {'eng p': ('p1', ENG, (1800.0, 2300.0)), 'eng p2': ('p1', ENG, (1800.0, 2900.0)),
             'eng e': ('s4', ENG, (1000.0, 4600.0)), 'truck w': ('s4', TANK, (2200.0, 4600.0)),
             'oni': ('s4', KING, (3600.0, 4600.0)),
             'tanya a': ('p1', TANYA, (1000.0, 4000.0)), 'gun': ('p1', TANK, (2200.0, 4000.0)),
             'tanya b': ('p1', TANYA, (3600.0, 4000.0))}
    BUILDINGS = {'f1': ('p1', FACTORY, (2500.0, 2400.0)), 'f2': ('p1', BARRACKS, (3300.0, 2400.0)),
                 'g1': ('s4', FACTORY, (4200.0, 2400.0)), 'g2': ('s4', BARRACKS, (4400.0, 2950.0))}
    LIST = 'CNV Kind Structs'
    RUN = 30.0


    def _n(part):
        return f'UNIT - CNV Kind {part.title()}'


    def _put(m, template, x, y, **kw):
        m.put(template, 'stop row', x - O[0], y - O[1], **kw)


    def mission():
        m = Mission(name='CampKind', map=probe_border, units=[], facts={})
        m.spawns |= {TANK, ENG, TANYA, KING, NATASHA}
        for role, (side, template, (x, y)) in {**UNITS, **BUILDINGS}.items():
            angle = 0.0 if role in BUILDINGS else (1.5708 if side == 'p1' else -1.5708)
            _put(m, template, x, y, side=side, angle=angle, name=_n(role), role=role)
        return m


    def _seen(t, counter, label, parts):
        """counter += weight every frame a reader holds (never reset), one script per reader, in this order."""
        t.counters.append((counter, label))
        t.scripts += [Script(f'Test - {counter} {k}', [c], [('INCREMENT_COUNTER', w, counter)], once=False)
                      for k, (w, c) in enumerate(parts)]


    def all_(m):
        t = Test()
        p1, s4 = m.player(), m.player('s4')
        n = {r: m.role(r).name for r in list(UNITS) + list(BUILDINGS)}
        quiet = ['eng p', 'eng p2', 'eng e', 'truck w', 'oni']
        t.scripts.append(Script('Test - Kind start', [], [
            ('UNIT_CHANGE_OBJECT_STATUS', n[r], status('NO_ATTACK'), 1) for r in quiet] + [
            ('UNIT_SET_HEALTH', n['truck w'], 5.0),
            ('OBJECTLIST_ADDOBJECTTYPE', FACTORY.lower(), LIST), ('OBJECTLIST_ADDOBJECTTYPE', BARRACKS.lower(), LIST)]))
        s8.at(t, 'gun', 2.0, [('NAMED_ATTACK_NAMED', n['gun'], n['truck w'])])
        s8.at(t, 'p', 4.0, [('NAMED_KILL', n['eng p'])])
        s8.at(t, 'ta', 6.0, [('NAMED_ATTACK_NAMED', n['tanya a'], n['eng e'])])
        s8.at(t, 'tb', 10.0, [('NAMED_ATTACK_NAMED', n['tanya b'], n['oni'])])
        s8.at(t, 'f1', 12.0, [('NAMED_KILL', n['f1'])])
        s8.at(t, 'p2', 16.0, [('NAMED_KILL', n['eng p2'])])
        s8.at(t, 'g1', 20.0, [('NAMED_KILL', n['g1'])])
        k = 'PLAYER_HAS_COMPARISON_UNIT_KIND'
        s8.total(t, 'CNV_Kind_Kind', '种', [
            (1, (k, p1, 4, 0, kindof('ENGINEER'))), (2, (k, p1, 2, 0, kindof('BEACON'))),
            (4, (k, s4, 1, 3, kindof('FS_FACTORY'))), (8, (k, s4, 3, 1, kindof('ENGINEER'))),
            (16, (k, p1, 2, 2, kindof('FS_FACTORY')))])
        lost = 'PLAYER_LOST_OBJECT_TYPE'
        _seen(t, 'CNV_Kind_Lost', '失', [
            (1, (lost, p1, ENG)), (2, (lost, p1, ENG)), (4, (lost, s4, ENG)), (8, (lost, p1, FACTORY)),
            (16, (lost, p1, LIST)), (32, (lost, s4, FACTORY))])
        d = 'NAMED_DESTROYED_BY_OBJECTTYPE'
        s8.total(t, 'CNV_Kind_By', '毁', [
            (1, (d, n['eng e'], TANYA.lower())), (2, (d, n['oni'], TANYA.lower())), (4, (d, n['oni'], NATASHA.lower())),
            (8, (d, n['truck w'], TANK.lower())), (16, (d, n['eng p'], TANYA.lower()))])
        t.expect = [('失', RUN - 1, '>=', 1), ('毁', RUN - 1, '>=', 1)]
        s8.watch(t, RUN)
        return t


    def by(m):
        """all's 毁 read 0 all run (bench 11-15 CampKindAll_mcp_1115_045506) while eng e died (种 &8 off, 失 &4 at s13):
        tells a one-frame truth (a counter that never resets: its weight every evaluation a reader holds) from never
        true, the killer's template's case, and whether the victims died at all. 毁 = 1 (eng e, alliedcommandotech1) +
        1000 (eng e, AlliedCommandoTech1); 坦 = 1 (truck w, alliedantivehiclevehicletech1) + 1000 (eng p,
        alliedcommandotech1: a script's kill); 王 = 1 (King Oni, alliedcommandotech1) + 1000 (King Oni,
        sovietcommandotech1); 死 (every frame) = 1 NAMED_DESTROYED eng e, 2 truck w, 4 King Oni, 8 eng p."""
        t = all_(m)
        t.scripts = [s for s in t.scripts if s.name.startswith(('Test - Kind start', 'Test - S8'))]
        t.counters = []
        n = {r: m.role(r).name for r in list(UNITS) + list(BUILDINGS)}
        d = 'NAMED_DESTROYED_BY_OBJECTTYPE'
        _seen(t, 'CNV_Kind_By', '毁', [(1, (d, n['eng e'], TANYA.lower())), (1000, (d, n['eng e'], TANYA))])
        _seen(t, 'CNV_Kind_Tank', '坦', [(1, (d, n['truck w'], TANK.lower())), (1000, (d, n['eng p'], TANYA.lower()))])
        _seen(t, 'CNV_Kind_Oni', '王', [(1, (d, n['oni'], TANYA.lower())), (1000, (d, n['oni'], NATASHA.lower()))])
        s8.total(t, 'CNV_Kind_Dead', '死', [(w, ('NAMED_DESTROYED', n[r])) for w, r in
                                            ((1, 'eng e'), (2, 'truck w'), (4, 'oni'), (8, 'eng p'))])
        t.expect = [('死', RUN - 1, '>=', 1)]
        s8.watch(t, RUN)
        return t


    MISSION = {'engine_kind': mission}
    CHECKS = {'engine_kind': {'all': all_, 'by': by}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_razed():
    """Retail-campaign conditions, batch 5 (round 240): PLAYER_DESTROYED_N_BUILDINGS_PLAYER (8 uses, j03 / j07: always
    N = 1 -- (Player_1, 1, Soviet02), (Allies01, 1, Player_1), ...; ep01 j03 N = 2) and
    SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED (8, j02 (Player_1, <=, 0) seven times, j07 (Player_2, >=, 1)). Mission on
    maps/probe_border.py (level ground), every place absolute. Clear of probe_range's lanes (y 400, 1200-1900,
    3300-3750) and the start (1250, 2500). No trigger areas.

      all  razing: the player's guns (Guardians) 600 north of their marks, out of sight: gun 0 at (1000, 4000) for
           Soviet_4's 'foe' (a Guardian, NO_ATTACK) at (1000, 4600); gun a / gun b at (2200 / 3400, 4000) for Soviet_4's
           power plants A / B at (2200 / 3400, 4600). Soviet_5's plant C at (4400, 4600); the player's plant M at
           (4500, 2400) and Soviet_4's 'raider' (a Guardian) 600 south of it at (4500, 3000). At 0 s foe, A, B, M set to
           5 % health. NAMED_ATTACK_NAMED gun 0 -> foe at 1 s, gun a -> A at 4 s, gun b -> B at 10 s, raider -> M at 16 s;
           NAMED_KILL(C) at 13 s (no killer).
           摧毁 (every frame) = 1 PLAYER_DESTROYED_N_BUILDINGS_PLAYER(Player_1, 1, Soviet_4) 2 (Player_1, 2, Soviet_4)
             4 (Player_1, 1, Soviet_5: a script's kill) 8 (Soviet_4, 1, Player_1) 16 (Player_1, 0, Soviet_4)
           死 (every frame) = 1 NAMED_DESTROYED(foe) 2 (A) 4 (B) 8 (C) 16 (M)
           garrisons: three of retail's AM_Apartments_01 (the civilians') at (2400 / 3000 / 3600, 2800), H1 H2 H3; the
           player's conscripts man a / man b / man c and Soviet_4's man d 200 south of them (every man NO_ATTACK). At 2 s
           NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY man a, man b -> H1, man d -> H3; at 6 s man c -> H2;
           NAMED_EXIT_BUILDING man a at 10 s, man b at 14 s, man c at 18 s.
           驻军 (every frame) = 1 SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED(Player_1, <=, 0) 2 (Player_1, >=, 1)
             4 (Player_1, ==, 1) 8 (Player_1, ==, 2) 16 (Player_1, >=, 3) 32 (Soviet_4, >=, 1)
      [prediction from the data (the simulator before this round knew neither; Generals' ScriptConditions read as a
       guide, INFERRED). Generals' evaluatePlayerDestroyedNOrMoreBuildings is a stub (`@todo implement me`, FALSE);
       RA3's retail scripts use it as a live trigger (j07's AI turns on once the player razes one of its buildings), so
       predicted: the player's count of the opponent's structures it killed by weapon, at least N; a unit and a script's
       kill not counted: 摧毁 16 from the start (N 0), 17 once A falls (~s5), 19 once B falls (~s11), 27 once M falls
       (~s17); &4 never; the foe's death (~s2) changes nothing. The stub would read 0 all run.
       SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED = the number of the player's garrisonable objects holding anyone (a
       building, not its men; a civilian building is the occupant's while held): 驻军 1 to s2, 6 + 32 = 38 s2-s6 (H1),
       42 s6-s14 (H1 + H2; the men counted would read 2 + 16 + 32 = 50 s6-s10), 38 s14-s18 (H2), 33 after]
      BENCH 11-15 (round 240, CampRazedAll_mcp_1115_030516 PASS; the bench's seconds ~1.5 behind the timers): 摧毁 /
        死 / 驻军 s1-s4 0 0 42 | s5-s6 0 1 50 | s7-s11 0 3 50 | s12 0 11 42 | s13-s16 0 15 42 | s17-s18 0 15 38 |
        s20-s37 0 31 33. So: PLAYER_DESTROYED_N_BUILDINGS_PLAYER false all run, N 0 too -- the stub, as Generals';
        SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED counts the MEN inside (2 -> == 2, 3 -> >= 3, then 2 / 1 / 0), not the
        buildings; a man counts at once on NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY but is dropped ~3.5 s after
        NAMED_EXIT_BUILDING (NAMED_BUILDING_IS_EMPTY flipped at once, engine_sighted: INFERRED he counts while climbing
        out; the simulator drops him at once, not modelled). The kills came 2-4 s earlier than the simulator's (死).
        Simulator: simcond (tests/test_simbench.py test_razed_all_as_the_bench).
    """
    from maps import probe_border
    from parts import Mission, Script, Test, status
    import checks.engine_scripts8 as s8

    TANK, MAN, HOUSE, POWER = ('AlliedAntiVehicleVehicleTech1', 'SovietAntiInfantryInfantry', 'AM_Apartments_01',
                               'AlliedPowerPlant')
    O = (1300.0, 4300.0)                            # probe_border's 'stop row'
    UNITS = {'gun 0': ('p1', TANK, (1000.0, 4000.0)), 'gun a': ('p1', TANK, (2200.0, 4000.0)),
             'gun b': ('p1', TANK, (3400.0, 4000.0)), 'foe': ('s4', TANK, (1000.0, 4600.0)),
             'raider': ('s4', TANK, (4500.0, 3000.0))}
    PLANTS = {'a': ('s4', (2200.0, 4600.0)), 'b': ('s4', (3400.0, 4600.0)), 'c': ('s5', (4400.0, 4600.0)),
              'm': ('p1', (4500.0, 2400.0))}
    HOUSES = {'h1': (2400.0, 2800.0), 'h2': (3000.0, 2800.0), 'h3': (3600.0, 2800.0)}
    MEN = {'man a': ('p1', 'h1', -60.0), 'man b': ('p1', 'h1', 60.0), 'man c': ('p1', 'h2', 0.0),
           'man d': ('s4', 'h3', 0.0)}
    RUN = 30.0


    def _n(part):
        return f'UNIT - CNV Razed {part.title()}'


    def _put(m, template, x, y, **kw):
        m.put(template, 'stop row', x - O[0], y - O[1], **kw)


    def mission():
        m = Mission(name='CampRazed', map=probe_border, units=[], facts={})
        m.spawns |= {TANK, MAN}
        for role, (side, template, (x, y)) in UNITS.items():
            _put(m, template, x, y, side=side, angle=1.5708 if side == 'p1' else -1.5708, name=_n(role), role=role)
        for k, (side, (x, y)) in PLANTS.items():
            _put(m, POWER, x, y, side=side, angle=0.0, name=_n(f'plant {k}'), role=f'plant {k}')
        for role, (x, y) in HOUSES.items():
            _put(m, HOUSE, x, y, side='civ', angle=0.0, name=_n(role), role=role)
        for role, (side, house, dx) in MEN.items():
            x, y = HOUSES[house]
            _put(m, MAN, x + dx, y - 200.0, side=side, angle=0.0, name=_n(role), role=role)
        return m


    def all_(m):
        t = Test()
        p1, s4, s5 = m.player(), m.player('s4'), m.player('s5')
        n = {r: m.role(r).name for r in list(UNITS) + list(HOUSES) + list(MEN) + [f'plant {k}' for k in PLANTS]}
        t.scripts.append(Script('Test - Razed start', [], [
            ('UNIT_CHANGE_OBJECT_STATUS', n[r], status('NO_ATTACK'), 1) for r in ['foe'] + list(MEN)] + [
            ('UNIT_SET_HEALTH', n[r], 5.0) for r in ('foe', 'plant a', 'plant b', 'plant m')]))
        s8.at(t, 'foe', 1.0, [('NAMED_ATTACK_NAMED', n['gun 0'], n['foe'])])
        s8.at(t, 'in', 2.0, [('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', n['man a'], n['h1']),
                             ('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', n['man b'], n['h1']),
                             ('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', n['man d'], n['h3'])])
        s8.at(t, 'a', 4.0, [('NAMED_ATTACK_NAMED', n['gun a'], n['plant a'])])
        s8.at(t, 'in c', 6.0, [('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', n['man c'], n['h2'])])
        s8.at(t, 'b', 10.0, [('NAMED_ATTACK_NAMED', n['gun b'], n['plant b'])])
        s8.at(t, 'out a', 10.0, [('NAMED_EXIT_BUILDING', n['man a'])])
        s8.at(t, 'c', 13.0, [('NAMED_KILL', n['plant c'])])
        s8.at(t, 'out b', 14.0, [('NAMED_EXIT_BUILDING', n['man b'])])
        s8.at(t, 'm', 16.0, [('NAMED_ATTACK_NAMED', n['raider'], n['plant m'])])
        s8.at(t, 'out c', 18.0, [('NAMED_EXIT_BUILDING', n['man c'])])
        d = 'PLAYER_DESTROYED_N_BUILDINGS_PLAYER'
        s8.total(t, 'CNV_Razed_Razed', '摧毁', [
            (1, (d, p1, 1, s4)), (2, (d, p1, 2, s4)), (4, (d, p1, 1, s5)), (8, (d, s4, 1, p1)), (16, (d, p1, 0, s4))])
        s8.total(t, 'CNV_Razed_Dead', '死', [(w, ('NAMED_DESTROYED', n[r])) for w, r in (
            (1, 'foe'), (2, 'plant a'), (4, 'plant b'), (8, 'plant c'), (16, 'plant m'))])
        g = 'SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED'
        s8.total(t, 'CNV_Razed_Held', '驻军', [
            (1, (g, p1, 1, 0)), (2, (g, p1, 3, 1)), (4, (g, p1, 2, 1)), (8, (g, p1, 2, 2)), (16, (g, p1, 3, 3)),
            (32, (g, s4, 3, 1))])
        t.expect = [('死', 0, 'ever>=', 1, RUN)]
        s8.watch(t, RUN)
        return t


    MISSION = {'engine_razed': mission}
    CHECKS = {'engine_razed': {'all': all_}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_script():
    """Engine unit test: the script engine's own clock and bookkeeping, nothing on the map but scripts (ADR 0019 layer 1,
    the side-by-side of the Python script-engine model against the game).

    All four readings freeze within ~2 s; read at s6. Scripts in this order, all on the first frame F:
      early count  [repeat] FLAG run -> +1 early         (before start: does not see run at F)
      start        [once]   run on; timer T 1.1 s; timer Shared 2.0 s; Out = 7; Out := Shared (SET_COUNTER_TO_COUNTER)
      count        [repeat] FLAG run -> +1 frames        (after start: sees run at F)
      stop         [once]   TIMER_EXPIRED T -> run off
      once         [once]   FLAG run -> +1 rearm
      rearm        [once]   COUNTER rearm >= 1 -> ENABLE_SCRIPT once

      计时帧数 frames: 1 + the frames T takes. Model (15 frames/s, ceil, timers tick before the scripts): ceil(16.5) =
        17 -> 18. 30 frames/s would read 35; floor or round 17; ticking after the scripts (OpenSAGE) 19.
      先看帧数 early: one fewer than frames (17) when a change is seen by later scripts the same frame and by earlier
        ones the next frame.
      一次性重开 rearm: 2 when ENABLE_SCRIPT re-arms a one-shot script that has fired (Generals: one-shot = inactive),
        1 when it does not (the old simulator's guess).
      计时器当计数器 out: 30 when counters and timers share one table (a 2 s timer holds 30 frames), 0 when they do
        not, 7 when SET_COUNTER_TO_COUNTER is (source, destination).
    """
    from maps import festival
    from parts import Mission, Script, Test

    RUN, T, EARLY, FRAMES, REARM = 'CNV_Scr_Run', 'CNV_Scr_T', 'CNV_Scr_Early', 'CNV_Scr_Frames', 'CNV_Scr_Rearm'
    SHARED, OUT = 'CNV_Scr_Shared', 'CNV_Scr_Out'


    def mission():
        return Mission(name='CampScr', map=festival, facts={})


    def frames(m):
        t = Test()
        t.scripts += [
            Script('Scr - early count', [('FLAG', RUN, 1)], [('INCREMENT_COUNTER', 1, EARLY)], once=False),
            Script('Scr - start', [], [('SET_FLAG', RUN, 1), ('SET_MILLISECOND_TIMER', T, 1.1),
                                       ('SET_MILLISECOND_TIMER', SHARED, 2.0), ('SET_COUNTER', OUT, 7),
                                       ('SET_COUNTER_TO_COUNTER', OUT, SHARED)]),
            Script('Scr - count', [('FLAG', RUN, 1)], [('INCREMENT_COUNTER', 1, FRAMES)], once=False),
            Script('Scr - stop', [('TIMER_EXPIRED', T)], [('SET_FLAG', RUN, 0)]),
            Script('Scr - once', [('FLAG', RUN, 1)], [('INCREMENT_COUNTER', 1, REARM)]),
            Script('Scr - rearm', [('COUNTER', REARM, 3, 1)], [('ENABLE_SCRIPT', 'Scr - once')])]
        t.counters += [(FRAMES, '计时帧数'), (EARLY, '先看帧数'), (REARM, '一次性重开'), (OUT, '计时器当计数器')]
        t.expect += [('计时帧数', 6, '==', 18), ('先看帧数', 6, '==', 17), ('一次性重开', 6, '==', 2),
                     ('计时器当计数器', 6, '==', 30)]
        t.bench = [('bench_watch', dict(seconds=9, every=3, sheet=False, lines=4))]
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_script': mission}
    CHECKS = {'engine_script': {'frames': frames}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_scripts1():
    """Engine probe, inventory batch 1 (docs/engine/inventory.md; the program read in work/re/l2_scripts1.md): mission
    benches/script/control/scenes.py#engine_scripts1. What the notes predict is in brackets; the readings go below.

      cond    条件位 = the sum, every frame, of 1 PLAYER_IS_HUMAN_OR_AI_PERSONALITY(Player_1, Human) [1], 2 (Soviet_1,
              Human) [2: "Human" = the player has no AI] until UNIT_AI_TRANSFER_ALL(Soviet_1, 1) at AI_AT [then 0],
              4 (Soviet_1, AIP_A01_Coop_AlliedSpecialForces) [0], 8 HAS_FINISHED_AUDIO of a line never played [8: true],
              16 HAS_FINISHED_VIDEO of a clip never played [?: false if unregistered reads false].
              状态 = 1 UNIT_HAS_OBJECT_STATUS(idle 1, NO_ATTACK), set at 2 s and cleared at 5 s [1 between]
              + 2 the same of idle 2, set at the start and killed at KILL_AT [2 until then; 0 once it is gone]
      xfer    crew Go sent to `far` (650 east) at 1 s, TEAM_TRANSFER_TO_PLAYER(Go, Soviet_2) at XFER_AT. 易主 = go 1
              owned by Soviet_2 [1 from XFER_AT]; 到终点 = how many of go 1-2 in `far` [0: the move is cleared];
              离家 = how many left `home` (150) [2: they had started]; 队里几个 = crew Go's members [0: on Soviet_2's team]
      idle    idle 1 and 2 sent to `far2` at 1 s; UNIT_IDLE_FOR_SECONDS(idle 1, 3) at IDLE_AT. 一到 / 二到 = 1 while
              idle k is in `far2` [二到 at ~1 + 900 / speed; 一到 never: the move is cleared; or 3 s late]
      hunt    TEAM_HUNT(Hunt) and NAMED_HUNT(lone) at 2 s, (s1 has no AI); TEAM_HUNT(Go) the player's. 敌队离家 /
              孤狼离家 / 我队离家 = how many left their marks (250) [the notes: a flag bit and the unit's AI woken, nobody
              reads it outside an AI player's HuntTactic: 0 0 0?]
      button  TEAM_USE_COMMANDBUTTON_ABILITY(Pk, Command_ToggleRiotShieldSpecialPower) at 2 s. 举盾 = the player's
              objects with GENERIC_TOGGLE_STATE [2 from 2 s]

    读数
    Bench 2026-11-08 (one run each; the bench's seconds run ~2 s behind the game's; sim pairs in tests/test_simbench.py
    test_scripts1_* / test_video_* / test_audio_*):
      cond    条件位 9 all run: Player_1 Human (1), a line never played reads done (8); Soviet_1 NOT Human from the start
              and after the wake (a campaign computer player has its AI object), the personality 0, a clip never played
              not done. 状态 3 -> 1 (idle 2 killed: false at once) -> 0 (idle 1 cleared).
      xfer    易主 1 from s3; 到终点 0 all 40 s (both had left home: 离家 2 before the hand-over) -- the move dropped;
              队里几个 2 -> 0 at the hand-over. (A first run had the tanks in the sea at -300: nobody moved.)
      idle    二到 1 from s7; 一到 0 all 45 s: UNIT_IDLE_FOR_SECONDS drops the order, it does not pause it.
      hunt    敌队离家 孤狼离家 我队离家 0 0 0 all 60 s: hunting without an AI player's tactic moves nobody.
      button  举盾 2 from s1 (the first reading): every member pressed. The simulator has no toggle (strict xfail).
    """
    from parts import Script, Test, counted, square, status

    AI_AT, KILL_AT, XFER_AT, IDLE_AT = 8.0, 4.0, 4.0, 3.0
    RUN = {'cond': 12.0, 'xfer': 40.0, 'idle': 45.0, 'hunt': 60.0, 'button': 10.0}
    LINE, CLIP = 'MA01_AlliedIntel24', 'CNVTEST01'
    SHIELD, BUTTON = 'GENERIC_TOGGLE_STATE', 'Command_ToggleRiotShieldSpecialPower'


    def _at(t, key, secs, actions):
        """actions at `secs` s from the start (a timer of its own)."""
        timer = f'Test {key} Timer'
        t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                      Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


    def _sum(t, counter, label, parts):
        """counter = the sum of the weights whose condition holds, recounted every frame. parts: [(weight, condition)]."""
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        t.scripts += [Script(f'Test - {counter} {k}', [c], [('INCREMENT_COUNTER', w, counter)], once=False)
                      for k, (w, c) in enumerate(parts)]


    def _away(t, counter, label, names, mark_point, r):
        """counter = how many of `names` are outside a square of half-side r around mark_point."""
        area = f'Test {counter} Home'
        t.areas[area] = square(*mark_point, r)
        _sum(t, counter, label, [(1, ('NAMED_OUTSIDE_AREA', n, area)) for n in names])


    def _watch(t, run, every=1.0):
        t.bench = [('bench_watch', dict(seconds=run, every=every, sheet=False, lines=len(t.counters)))]


    def cond(m):
        t = Test()
        p1, s1 = m.player('p1'), m.player('s1')
        i1, i2 = m.role('idle 1').name, m.role('idle 2').name
        na = status('NO_ATTACK')
        t.scripts.append(Script('Test - start', [], [('UNIT_CHANGE_OBJECT_STATUS', i2, na, 1)]))
        _at(t, 'set', 2.0, [('UNIT_CHANGE_OBJECT_STATUS', i1, na, 1)])
        _at(t, 'clear', 5.0, [('UNIT_CHANGE_OBJECT_STATUS', i1, na, 0)])
        _at(t, 'kill', KILL_AT, [('NAMED_KILL', i2)])
        _at(t, 'ai', AI_AT, [('UNIT_AI_TRANSFER_ALL', s1, 1)])
        _sum(t, 'CNV_S1_Cond', '条件位', [(1, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', p1, 'Human')),
                                          (2, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', s1, 'Human')),
                                          (4, ('PLAYER_IS_HUMAN_OR_AI_PERSONALITY', s1, 'AIP_A01_Coop_AlliedSpecialForces')),
                                          (8, ('HAS_FINISHED_AUDIO', LINE)), (16, ('HAS_FINISHED_VIDEO', CLIP))])
        _sum(t, 'CNV_S1_Status', '状态', [(1, ('UNIT_HAS_OBJECT_STATUS', i1, na)), (2, ('UNIT_HAS_OBJECT_STATUS', i2, na))])
        _watch(t, RUN['cond'], 0.5)
        return t


    def xfer(m):
        t = Test()
        go = m.teams['Go']
        names = [m.role(f'go {k}').name for k in (1, 2)]
        _at(t, 'go', 1.0, [('MOVE_TEAM_TO', go, m.mark('far'))])
        _at(t, 'xfer', XFER_AT, [('TEAM_TRANSFER_TO_PLAYER', go, m.player('s2'))])
        counted('CNV_S1_Owner', '易主', t, owner=names[0], player=m.player('s2'))
        t.areas['Test S1 Far'] = square(*m.point('far'), 80.0)
        _sum(t, 'CNV_S1_Far', '到终点', [(1, ('NAMED_INSIDE_AREA', n, 'Test S1 Far')) for n in names])
        _away(t, 'CNV_S1_Left', '离家', names, m.point('home'), 150.0)
        t.counters.append(('CNV_S1_Members', '队里几个'))
        t.scripts += [Script(f'Test - members {n}', [('TEAM_COMPARE_NUM_MEMBERS', go, 2, n)],
                             [('SET_COUNTER', 'CNV_S1_Members', n)], once=False) for n in range(3)]
        _watch(t, RUN['xfer'])
        return t


    def idle(m):
        t = Test()
        names = [m.role(f'idle {k}').name for k in (1, 2)]
        _at(t, 'go', 1.0, [('MOVE_NAMED_UNIT_TO', n, m.mark('far2')) for n in names])
        _at(t, 'idle', IDLE_AT, [('UNIT_IDLE_FOR_SECONDS', names[0], 3)])
        t.areas['Test S1 Far2'] = square(*m.point('far2'), 80.0)
        for k, n in enumerate(names, 1):
            counted(f'CNV_S1_At{k}', '一到' if k == 1 else '二到', t, named=n, area='Test S1 Far2')
        _watch(t, RUN['idle'])
        return t


    def hunt(m):
        t = Test()
        _at(t, 'hunt', 2.0, [('TEAM_HUNT', m.teams['Hunt']), ('NAMED_HUNT', m.role('lone').name),
                             ('TEAM_HUNT', m.teams['Go'])])
        _away(t, 'CNV_S1_EAway', '敌队离家', [m.role(f'hunt {k}').name for k in (1, 2)], m.point('ehome'), 250.0)
        _away(t, 'CNV_S1_LAway', '孤狼离家', [m.role('lone').name], m.point('lhome'), 250.0)
        _away(t, 'CNV_S1_GAway', '我队离家', [m.role(f'go {k}').name for k in (1, 2)], m.point('home'), 250.0)
        _watch(t, RUN['hunt'], 2.0)
        return t


    def button(m):
        t = Test()
        _at(t, 'press', 2.0, [('TEAM_USE_COMMANDBUTTON_ABILITY', m.teams['Pk'], BUTTON)])
        counted('CNV_S1_Shield', '举盾', t, status=status(SHIELD), most=3)
        _watch(t, RUN['button'], 0.5)
        return t


    CHECKS = {'engine_scripts1': {'cond': cond, 'xfer': xfer, 'idle': idle, 'hunt': hunt, 'button': button}}
    return dict(CHECKS=CHECKS)


def engine_scripts2():
    """Engine probe, the inferred script items (docs/engine/inventory-levels-a.md): mission benches/script/control/scenes.py#engine_scripts2.
    What the simulator predicts is in brackets; the readings go below.

    Counters (both checks): A血 = the player's MCV in the west (only the enemy's Guardian can shoot it), B血 = the enemy's
    MCV in the east (only the player's Guardian can shoot it), in percent; 比较数 = how many Guardians the player has by
    PLAYER_HAS_OBJECT_COMPARISON (==, n = 0..3), 类型数 = by SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER. tank 1 is killed at
    KILL_AT (the player then has gun b + tank 2: 3 -> 2).

      one   PLAYER_RELATES_PLAYER(Soviet_1, Player_1, Neutral) at the start, (Soviet_1, Player_1, Enemy) at BACK_AT.
            [A血 100 until BACK_AT, then falls: the enemy's view of the player is its own; B血 falls from the start:
            the player's view of the enemy is unchanged (one way)]. 比较数 [3 -> 2 at KILL_AT: LINGER 0, the dying
            counted only while in the name cache]
      all   PLAYER_RELATES_PLAYER(Soviet_1, <All Players>, Neutral) at the start (retail a01's retreat), (Player_1,
            Soviet_1, Neutral) at BACK_AT. [simulator before this probe: '<All Players>' never matched a pair, A血 falls
            from the start; B血 falls until BACK_AT, then stays]

    读数
    Bench 2026-11-09 (one run each; the bench's seconds ~2 s behind the game's; sim pairs tests/test_simbench.py
    test_scripts2_*):
      one   CampScr2One_mcp_1109_054230: A血 100 to s8, 98 s9, 86 s25 -- one way, and Enemy again takes at once. 比较数 3
            -> 2 at s2 with 类型数: the killed tank is not counted while it dies (Generals' ignoreDead false is not RA3's;
            docs/engine/script-semantics.md 6 was a guess).
      all   CampScr2All_mcp_1109_054518: A血 98 s1 -> 80 s25: '<All Players>' as the second player changes nothing (the
            simulator never matched it: right). Retail a01's retreat line does not stop Soviet_1's fire.
      both  B血 98 s1 -> 95 s5, then 96 -> 99 by s25, in both runs (the player's view of Soviet_1 untouched in one,
            Neutral from BACK_AT in all): the player's Guardian stops shooting the unarmed MCV after ~4 s and the MCV
            heals. Not explained (auto-acquire of an unarmed target? an MCV's self-repair?) -- not this probe's question.
    """
    from parts import Script, Test, counted

    KILL_AT, BACK_AT = 3.0, 10.0
    RUN = {'one': 24.0, 'all': 24.0}
    TANK = 'AlliedAntiVehicleVehicleTech1'
    REL = {'Enemy': 0, 'Neutral': 1, 'Friend': 2}


    def _rel(a, b, r):
        return ('PLAYER_RELATES_PLAYER', a, b, (REL[r], 0.0, r))


    def _at(t, key, secs, actions):
        timer = f'Test {key} Timer'
        t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                      Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


    def _common(t, m):
        counted('CNV_S2_A', 'A血', t, health=m.role('mcv a').name)
        counted('CNV_S2_B', 'B血', t, health=m.role('mcv b').name)
        t.counters.append(('CNV_S2_Cmp', '比较数'))
        t.scripts += [Script(f'Test - cmp {n}', [('PLAYER_HAS_OBJECT_COMPARISON', m.player('p1'), 2, n, TANK)],
                             [('SET_COUNTER', 'CNV_S2_Cmp', n)], once=False) for n in range(4)]
        counted('CNV_S2_Type', '类型数', t, template=TANK)
        _at(t, 'kill', KILL_AT, [('NAMED_KILL', m.role('tank 1').name)])
        t.bench = [('bench_watch', dict(seconds=RUN['one'], every=0.5, sheet=False, lines=len(t.counters)))]


    def one(m):
        t = Test()
        p1, s1 = m.player('p1'), m.player('s1')
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), _rel(s1, p1, 'Neutral')]))
        _at(t, 'back', BACK_AT, [_rel(s1, p1, 'Enemy')])
        _common(t, m)
        return t


    def all_(m):
        t = Test()
        p1, s1 = m.player('p1'), m.player('s1')
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), _rel(s1, '<All Players>', 'Neutral')]))
        _at(t, 'back', BACK_AT, [_rel(p1, s1, 'Neutral')])
        _common(t, m)
        return t


    CHECKS = {'engine_scripts2': {'one': one, 'all': all_}}
    return dict(CHECKS=CHECKS)


def engine_scripts3():
    """Engine probe, the inferred script items (docs/engine/inventory-levels-a.md): counter arithmetic and DISABLE_INPUT.
    Mission: benches/script/control/scenes.py#engine_scripts2's island scene as build engine_scripts3. What the model / simulator predicts is
    in brackets; the readings go below.

      math   SET_COUNTER at the start, then at OP_AT one COUNTER_MATH_COUNTER(counter, op, 'CNV_S3_Four' = 4) each:
             加 3 op 0 [7], 减 3 op 1 [-1: no floor at 0], 乘 3 op 2 [12], 除 13 op 3 [3]. The model
             (RA3-EngineModel ra3model/scripts.py) reads 0 / 1 off retail's use (a total of kills; what is left of the
             transports); 2 / 3 were its guess.
      input  DISABLE_INPUT at the start, ENABLE_INPUT at FREE_AT. At GO_AT MOVE_NAMED_UNIT_TO(tank 1, 'Test S3 Go', 300
             south of east 3) [走到 1 by ~GO_AT + 10: a script's order is not the player's input -- the simulator keeps
             DISABLE_INPUT a flag nothing reads]; B血 = the enemy MCV the player's Guardian shoots [falls from the start:
             the unit's own fire is not input]; 负数 = SET 2, DECREMENT_COUNTER 5 at GO_AT [-3]; 除负 = SET -13, op 3 by
             4 at GO_AT [-3: C's division truncates toward 0, -4 would be floor].

    读数
    Bench 2026-11-09 (one run each; sim pairs tests/test_simbench.py test_scripts3_*; docs/engine/script-semantics.md
    3 and 8.13):
      math   CampScr3Math_mcp_1109_063100: 3 3 3 13 at s1, 7 -1 12 3 from s2 -- all four as the model. (-1 read "?"
             at first: the counter reader dropped the minus as a speck; experimental/testbench/counters.minus since.)
      input  CampScr3Input_mcp_1109_063847 (frames re-read with the fixed reader; the running bench server still had
             the old one): 走到 1 from bench s9 (the move, given at 7 while locked, done), B血 98 -> 96 then back to 100
             (the Guardian's ~4 s on the unarmed MCV, as in scripts2), 负数 -3 and 除负 -3 from s6. With DISABLE_INPUT
             at 1 s (and at the start) bench_start failed: Esc opened no mission menu -- the lock takes Esc too.
    """
    from parts import Script, Test, counted, square

    OP_AT, LOCK_AT, GO_AT, FREE_AT = 3.0, 5.0, 7.0, 20.0
    RUN = {'math': 10.0, 'input': 24.0}
    FOUR = 'CNV_S3_Four'


    def _at(t, key, secs, actions):
        timer = f'Test {key} Timer'
        t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                      Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


    def _watch(t, run):
        t.bench = [('bench_watch', dict(seconds=run, every=0.5, sheet=False, lines=len(t.counters)))]


    def math(m):
        t = Test()
        rows = [('CNV_S3_Add', '加', 3, 0), ('CNV_S3_Sub', '减', 3, 1), ('CNV_S3_Mul', '乘', 3, 2), ('CNV_S3_Div', '除', 13, 3)]
        t.counters += [(c, label) for c, label, _, _ in rows]
        t.scripts.append(Script('Test - start', [], [('SET_COUNTER', FOUR, 4)] + [('SET_COUNTER', c, v) for c, _, v, _ in rows]))
        _at(t, 'op', OP_AT, [('COUNTER_MATH_COUNTER', c, op, FOUR) for c, _, _, op in rows])
        t.expect += [('加', OP_AT + 3, '==', 7, RUN['math']), ('减', OP_AT + 3, '==', -1, RUN['math']),
                     ('乘', OP_AT + 3, '==', 12, RUN['math']), ('除', OP_AT + 3, '==', 3, RUN['math'])]
        _watch(t, RUN['math'])
        return t


    def input_(m):
        t = Test()
        tank = m.role('tank 1').name
        t.waypoints['Test S3 Go'] = m.site('east 3', 0.0, -300.0)
        t.areas['Test S3 Go Area'] = square(*m.site('east 3', 0.0, -300.0), 80.0)
        counted('CNV_S3_At', '走到', t, named=tank, area='Test S3 Go Area')
        counted('CNV_S3_B', 'B血', t, health=m.role('mcv b').name)
        t.counters += [('CNV_S3_Neg', '负数'), ('CNV_S3_NegDiv', '除负')]
        t.scripts.append(Script('Test - start', [], [('SET_COUNTER', FOUR, 4), ('SET_COUNTER', 'CNV_S3_Neg', 2),
                                                    ('SET_COUNTER', 'CNV_S3_NegDiv', -13)]))
        _at(t, 'lock', LOCK_AT, [('DISABLE_INPUT',)])   # after bench_start's Esc check: locked from the start, Esc
                                                        # opened no menu and the bench could not start (11-09)
        _at(t, 'go', GO_AT, [('MOVE_NAMED_UNIT_TO', tank, 'Test S3 Go'), ('DECREMENT_COUNTER', 5, 'CNV_S3_Neg'),
                             ('COUNTER_MATH_COUNTER', 'CNV_S3_NegDiv', 3, FOUR)])
        _at(t, 'free', FREE_AT, [('ENABLE_INPUT',)])
        t.expect += [('走到', GO_AT + 12, '==', 1, FREE_AT), ('负数', GO_AT + 3, '==', -3, RUN['input']),
                     ('除负', GO_AT + 3, '==', -3, RUN['input'])]
        _watch(t, RUN['input'])
        return t


    CHECKS = {'engine_scripts3': {'math': math, 'input': input_}}
    return dict(CHECKS=CHECKS)


def engine_scripts4():
    """Engine probe, the inferred script items (docs/engine/inventory-levels-a.md): MAP_SWITCH_BORDER, the countdown shown
    and hidden (DISPLAY_COUNTDOWN_TIMER / HIDE_COUNTDOWN_TIMER), TEAM_STOP, TEAM_GUARD_AREA. Mission here (build
    engine_scripts4) on maps/probe_border.py, flat ground with a second border (the west half, x <= 2500). What the
    Generals source / the simulator predicts is in brackets; the readings go below.

      border   MAP_SWITCH_BORDER 1 (the west half) in the first frame, 0 (the whole map) at OPEN_AT. Three Guardian
               pairs 120 apart, the player's facing the enemy's: X across the line (the player's west of it, the
               enemy's 60 east: on the map / off it), Y both east (both off), Z both west (both on). X血 / Y血 / Z血 the
               enemy Guardian's health; Y在 1 while the player's Y Guardian is in an area round where it stands (RA3's
               ObjectStatus has no OFF_MAP to count). [源码 4.4: the object is not killed or deleted, only marked
               OFF_MAP -- Y在 1 throughout; Generals' auto-targeting filters
               on the same map status (PartitionFilterSameMapStatus, INFERRED for RA3): X holds its fire till OPEN_AT,
               Y and Z fight. The simulator: the border changes no fight -- X falls from the start.]
      team     two Guardians on team Stop sent east along the stop row (MOVE_TEAM_TO, at 1 s, 1400 away), TEAM_STOP at
               STOP_AT; two on team Guard told TEAM_GUARD_AREA of a zone 700 east of them at 1 s. 停起点 / 停中段 /
               停终点 the stop team's Guardians in the start / middle / far area; 守区内 the guard team's in the zone.
               [Sim.order_stop drops the way: 0 / 2 / 0 to the end; Sim.order_guard sends each to the zone's middle
               (UNIT_GUARD_AREA, engine_acquire): 守区内 2 and stays.]
      clock    timer 20 s set and DISPLAY_COUNTDOWN_TIMER in the first frame, HIDE_COUNTDOWN_TIMER at 8 s, shown
               again at 14 s; 到点 1 once the timer expires. [源码 4.3: showing is UI only -- the hidden timer runs on,
               到点 1 at 20; shown again it reads what is left (~0:06).] The countdown line itself is skipped by the
               counter reader (a colon): read off the frames by hand.

    读数
    Bench 2026-11-09 (one run each; bench seconds run ~2 ahead of mission time; sim pairs tests/test_simbench.py
    test_scripts4_*; docs/engine/script-semantics.md 4.3, 4.4):
      border  CampScr4Border_mcp_1109_072744: X血 and Y血 100 till s18, then 87 at s19 and down ~6 a second (12 at
              s31); Z血 87 at s1 down to 12 at s12, held there (one of the pair dead); Y在 1 all along (0 at s33: the
              player's Y Guardian died in its fight). So an object off the border neither fires nor is fired on -- X
              (ours inside, theirs outside) as Y (both outside): stricter than Generals' same-status filter; it lives
              on and the area conditions see it. Sim.on_map since.
      team    CampScr4Team_mcp_1109_073024: PASS -- 停中段 2 from s1, 停起点 / 停终点 0 to the end (TEAM_STOP: they stop
              where they are and stay); 守区内 1 at s6, 2 from s8 to s32 (TEAM_GUARD_AREA: both go in and stay).
      clock   CampScr4Clock_mcp_1109_073246: PASS -- 到点 1 from s19 (the hidden timer ran on). The countdown line read
              off the frames by hand: "测试倒计时 0:15" above 到点 at s3, gone s6-s11, back from s12 reading 0:04 (what
              was left, not reset) and **below** 到点 (shown again, it goes to the end of the list), "0:00" still shown
              after it expired (s20-s27: an expired countdown stays till hidden).
    """
    import math

    from maps import probe_border
    from parts import Mission, Script, Test, counted, square

    GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
    OPEN_AT, STOP_AT, HIDE_AT, SHOW_AT, CD = 20.0, 4.0, 8.0, 14.0, 20.0
    RUN = {'border': 32.0, 'team': 30.0, 'clock': 26.0}
    # the border scene: (pair, dx, dy) of the player's Guardian from the line; the enemy's 120 east of it
    PAIRS = {'x': (-60.0, 0.0), 'y': (440.0, 200.0), 'z': (-560.0, 200.0)}
    ROW = 700.0                                     # the team rows: start dx -ROW, the far end / the zone further east


    def _n(part):
        return f'UNIT - CNV S4 {part}'


    def mission():
        m = Mission(name='CampScr4', map=probe_border, facts={})
        m.spawns |= {GUARDIAN}
        for pair, (dx, dy) in PAIRS.items():
            m.put(GUARDIAN, 'line', dx, dy, angle=0.0, name=_n(f'Mine {pair}'), role=f'mine {pair}')
            m.put(GUARDIAN, 'line', dx + 120.0, dy, side='s1', angle=math.pi, name=_n(f'Foe {pair}'), role=f'foe {pair}')
        for row, key in (('stop row', 'Stop'), ('guard row', 'Guard')):
            for k, dy in enumerate((-30.0, 30.0), 1):
                m.put(GUARDIAN, row, -ROW, dy, angle=0.0, name=_n(f'{key} {k}'), role=f'{key.lower()} {k}')
            m.crew(key)
        m.waypoint('stop far', 'CNV S4 Stop Far', 'stop row', ROW, 0.0)
        return m


    def _at(t, key, secs, actions):
        timer = f'Test {key} Timer'
        t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                      Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


    def _watch(t, run):
        t.bench = [('bench_watch', dict(seconds=run, every=1.0, sheet=False, lines=len(t.counters)))]


    def border(m):
        t = Test()
        t.scripts.append(Script('Test - border', [], [('MAP_SWITCH_BORDER', list(probe_border.BORDERS).index('west half'))]))
        _at(t, 'open', OPEN_AT, [('MAP_SWITCH_BORDER', 0)])
        for pair in PAIRS:
            counted(f'CNV_S4_{pair.upper()}', f'{pair.upper()}血', t, health=m.role(f'foe {pair}').name)
        t.areas['Test S4 Y'] = square(*m.site('line', *PAIRS['y']), 80.0)
        counted('CNV_S4_YIn', 'Y在', t, named=m.role('mine y').name, area='Test S4 Y')
        t.expect += [('Z血', 8, '<', 100), ('Y血', 1, '==', 100, OPEN_AT - 2), ('X血', 1, '==', 100, OPEN_AT - 2),
                     ('X血', OPEN_AT + 8, '<', 100), ('Y血', OPEN_AT + 8, '<', 100), ('Y在', 1, '==', 1, 10)]
        _watch(t, RUN['border'])
        return t


    def team(m):
        t = Test()
        x, y = m.site('stop row', 0.0, 0.0)
        t.areas['Test S4 Stop Start'] = square(x - ROW, y, 100.0)
        t.areas['Test S4 Stop Mid'] = [(x - ROW + 101, y - 150), (x + ROW - 101, y - 150), (x + ROW - 101, y + 150),
                                       (x - ROW + 101, y + 150)]
        t.areas['Test S4 Stop Far'] = square(x + ROW, y, 100.0)
        gx, gy = m.site('guard row', 0.0, 0.0)
        zone = 'Test S4 Guard Zone'
        t.areas[zone] = square(gx, gy, 150.0)
        for area, label in (('Start', '停起点'), ('Mid', '停中段'), ('Far', '停终点')):
            counted(f'CNV_S4_Stop{area}', label, t, template=GUARDIAN, area=f'Test S4 Stop {area}')
        counted('CNV_S4_Guard', '守区内', t, template=GUARDIAN, area=zone)
        stop, guard = m.teams['Stop'], m.teams['Guard']
        joins = [('UNIT_SET_TEAM', m.role(f'{key} {k}').name, m.teams[key.capitalize()])
                 for key in ('stop', 'guard') for k in (1, 2)]
        _at(t, 'go', 1.0, joins + [('MOVE_TEAM_TO', stop, m.mark('stop far')), ('TEAM_GUARD_AREA', guard, zone)])
        _at(t, 'halt', STOP_AT, [('TEAM_STOP', stop)])
        t.expect += [('停起点', STOP_AT + 2, '==', 0), ('停中段', STOP_AT + 2, '==', 2), ('停终点', 0, '==', 0),
                     ('守区内', RUN['team'] - 4, '==', 2)]
        _watch(t, RUN['team'])
        return t


    def countdown(m):
        t = Test()
        timer, text = 'Test S4 Countdown', 'CNV:S4Countdown'
        t.strings[text] = '测试倒计时'
        t.counters.append(('CNV_S4_Due', '到点'))
        t.scripts += [Script('Test - countdown', [], [('SET_COUNTER', 'CNV_S4_Due', 0), ('SET_MILLISECOND_TIMER', timer, CD),
                                                      ('DISPLAY_COUNTDOWN_TIMER', timer, text)]),
                      Script('Test - countdown due', [('TIMER_EXPIRED', timer)], [('SET_COUNTER', 'CNV_S4_Due', 1)])]
        _at(t, 'hide', HIDE_AT, [('HIDE_COUNTDOWN_TIMER', timer)])
        _at(t, 'show', SHOW_AT, [('DISPLAY_COUNTDOWN_TIMER', timer, text)])
        t.expect += [('到点', 1, '==', 0, CD - 1), ('到点', CD + 2, '==', 1)]
        _watch(t, RUN['clock'])
        return t


    MISSION = {'engine_scripts4': mission}
    CHECKS = {'engine_scripts4': {'border': border, 'team': team, 'clock': countdown}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_scripts6():
    """Engine probe, the script machinery (docs/engine/inventory.md, the heaviest inferred script items with no unit in
    them): CONDITION_TRUE, DISABLE_SCRIPT / ENABLE_SCRIPT, NO_OP, CALL_SUBROUTINE, a script's ELSE actions, SET_TIMER,
    SET_RANDOM_COUNTER, SET_RANDOM_MSEC_TIMER, COUNTER_SECONDS, COUNTER_COUNTER. Mission here (build engine_scripts6) on
    maps/probe_border.py, no units: every reading is a counter (checks `switch`: 帧 开关 自关 子程序; `timers`: 否则 随机 计时 -- four lines fit;
    both run every script). What the Generals source / the
    engine model (RA3-EngineModel ra3model/scripts.py, 15 frames a second) predicts is in brackets.

      帧    a repeating script, CONDITION_TRUE only, adds 1 a frame; DISABLE_SCRIPT on it at OFF_AT, ENABLE_SCRIPT at
            ON_AT. [15 a second, flat from OFF_AT to ON_AT, then on again]
      开关  sum of: 1 a script off at the start ([off]), never enabled [never]; 2 one off at the start, ENABLE_SCRIPT at
            ARM_AT [2 from ARM_AT]; 4 a once-script switched off by a script before it in the list, the same frame [never];
            8 a once-script switched off by a script after it, the same frame [8: it already ran]; 16 a once-script that
            adds 16 and is ENABLE_SCRIPTed again at REARM_AT [16, then 32: a fired once-script is only switched off]
            -- [24 at the start, 26 from ARM_AT, 42 from REARM_AT]
      自关  a repeating script: add 1, NO_OP, DISABLE_SCRIPT itself, add 10 [11 and stays: the actions after the switch
            still run in that pass, NO_OP changes nothing]
      子程序 a caller runs CALL_SUBROUTINE at CALL1 and CALL2 on: S1 a once-sub adding 1 [1: closed after the first call];
            S2 a repeating sub adding 10 [20; never run by the frame pass itself]; S4 a repeating sub off at the start
            adding 100 [0: an inactive sub is not run] -- [11 from CALL1, 21 from CALL2]
      否则  1 a once-script whose condition never holds, ELSE adds 1 [1 and stays: Generals closes a once-script after its
            ELSE too]; S3 a repeating sub whose condition never holds, ELSE adds 10, called at CALL1 and CALL2 [10, 20]
            -- [1, 11 from CALL1, 21 from CALL2]
      随机  SET_RANDOM_COUNTER(R, 1, 3) every 0.5 s (a timer re-armed); a value v seen adds 2^v once [14: 1..3 inclusive,
            0 and 4 never]
      计时  sum of: 1 SET_TIMER 45 expired [at 3 s: frames]; 2 SET_RANDOM_MSEC_TIMER(T, 6, 6) expired [6 s: (timer, lo,
            hi) in seconds]; 4 SET_RANDOM_MSEC_TIMER(T, 8, 10) expired [8..10 s]; 8 COUNTER_SECONDS(a 20 s timer, <=, 15)
            [5 s: the seconds left]; 16 COUNTER_SECONDS(the same, <, 12) [8 s]; 32 COUNTER_COUNTER(帧, >=, K = 60)
            [4 s] -- [1 at 3, 33 at 4, 41 at 5, 43 at 6, 59 at 8, 63 by 10]

    读数 (bench 2026-11-09, run_queue engine_scripts6:switch / :timers, both PASS; the bench's seconds run ~2 ahead of
    mission time here: 帧 45 at s1 = 3 s; sim pair tests/test_simbench.py test_scripts6_*). Every bracket held:
      switch  帧 45 60 75 90 105 ... 150 at s8, 151 s9-s12, 167 at s13 and on 15 a second (287 at s21): CONDITION_TRUE
              holds every frame, 15 frames a second; DISABLE_SCRIPT stops a repeating script (151 = frame 151, the timer's
              10 s), ENABLE_SCRIPT starts it again. 开关 24 at s1, 26 from s2, 42 from s4: an [off] script never runs
              till enabled; DISABLE_SCRIPT from an earlier script in the same frame stops a once-script before its turn,
              from a later one too late; ENABLE_SCRIPT re-arms a fired once-script (16 -> 32). 自关 11 from s1: the
              actions after a script's own DISABLE_SCRIPT still run in that pass, NO_OP is nothing, the script stays
              off. 子程序 11 from s1 (CALL1), 21 from s3 (CALL2): a once-sub runs on its first call only, a repeating sub
              on each call and never in the frame pass, an [off] sub not at all.
      timers  否则 11 at s1, 21 from s3: a once-script's ELSE ran once and closed it; a called sub's ELSE runs when its
              condition fails. 随机 6 at s1, 14 from s3: SET_RANDOM_COUNTER(c, 1, 3) gives 1, 2 and 3, never 0 or 4
              (inclusive). 计时 1 at s2 (SET_TIMER 45 = 45 frames, 3 s), 33 at s3 (COUNTER_COUNTER 帧 >= 60 at 4 s), 41 at
              s4 (COUNTER_SECONDS <= 15 of a 20 s timer at 5 s: the seconds left), 43 s5-s6 (SET_RANDOM_MSEC_TIMER(t, 6, 6)
              at 6 s: (timer, lo, hi) in seconds), 63 from s7 (COUNTER_SECONDS < 12 at 8 s, the (8, 10) one by 9 s).
    """
    from maps import probe_border
    from parts import Mission, Script, Test

    OFF_AT, ON_AT, ARM_AT, REARM_AT, CALL1, CALL2 = 10.0, 14.0, 3.0, 5.0, 2.0, 4.0
    RUN = 20.0
    LT, LE, EQ, GE = 0, 1, 2, 3


    def mission():
        return Mission(name='CampScr6', map=probe_border, facts={})


    def _at(t, key, secs, actions):
        timer = f'Test S6 {key} Timer'
        t.scripts += [Script(f'Test - S6 {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                      Script(f'Test - S6 {key}', [('TIMER_EXPIRED', timer)], actions)]


    def _add(n, counter):
        return ('INCREMENT_COUNTER', n, counter)


    SHOW = {'switch': ('帧', '开关', '自关', '子程序'), 'timers': ('否则', '随机', '计时', '随帧')}


    def core(m, show):
        t = Test()
        F, SW, SELF, SUB, ELSE, RND, CLK, RTM = (f'CNV_S6_{k}' for k in ('Frames', 'Switch', 'Self', 'Sub', 'Else', 'Rnd',
                                                                           'Clock', 'RTim'))
        t.counters += [(F, '帧'), (SW, '开关'), (SELF, '自关'), (SUB, '子程序'), (ELSE, '否则'), (RND, '随机'),
                       (CLK, '计时'), (RTM, '随帧')]
        never = ('FLAG', 'CNV S6 Never', 1)
        s = t.scripts
        s.append(Script('Test - S6 init', [], [('SET_COUNTER', c, 0) for c, _ in t.counters]
                        + [('SET_COUNTER', 'CNV_S6_R', 9), ('SET_COUNTER', 'CNV_S6_T', 9),
                           ('SET_COUNTER', 'CNV_S6_K', 60)]))
        # 帧
        s.append(Script('Test - S6 frames', [('CONDITION_TRUE',)], [_add(1, F)], once=False))
        _at(t, 'off', OFF_AT, [('DISABLE_SCRIPT', 'Test - S6 frames')])
        _at(t, 'on', ON_AT, [('ENABLE_SCRIPT', 'Test - S6 frames')])
        # 开关
        s.append(Script('Test - S6 never on', [], [_add(1, SW)], active=False))
        s.append(Script('Test - S6 armed later', [], [_add(2, SW)], active=False))
        _at(t, 'arm', ARM_AT, [('ENABLE_SCRIPT', 'Test - S6 armed later')])
        s.append(Script('Test - S6 cut before', [], [('DISABLE_SCRIPT', 'Test - S6 victim before')]))
        s.append(Script('Test - S6 victim before', [], [_add(4, SW)]))
        s.append(Script('Test - S6 victim after', [], [_add(8, SW)]))
        s.append(Script('Test - S6 cut after', [], [('DISABLE_SCRIPT', 'Test - S6 victim after')]))
        s.append(Script('Test - S6 rearmed', [], [_add(16, SW)]))
        _at(t, 'rearm', REARM_AT, [('ENABLE_SCRIPT', 'Test - S6 rearmed')])
        # 自关
        s.append(Script('Test - S6 self', [], [_add(1, SELF), ('NO_OP',), ('DISABLE_SCRIPT', 'Test - S6 self'),
                                               _add(10, SELF)], once=False))
        # 子程序, 否则
        s.append(Script('Test - S6 S1', [], [_add(1, SUB)], sub=True))
        s.append(Script('Test - S6 S2', [], [_add(10, SUB)], once=False, sub=True))
        s.append(Script('Test - S6 S3', [never], [_add(1000, ELSE)], orelse=[_add(10, ELSE)], once=False, sub=True))
        s.append(Script('Test - S6 S4', [], [_add(100, SUB)], once=False, sub=True, active=False))
        calls = [('CALL_SUBROUTINE', f'Test - S6 {k}') for k in ('S1', 'S2', 'S3', 'S4')]
        _at(t, 'call1', CALL1, calls)
        _at(t, 'call2', CALL2, calls)
        s.append(Script('Test - S6 else once', [never], [_add(1000, ELSE)], orelse=[_add(1, ELSE)]))
        # 随机
        s.append(Script('Test - S6 roll', [], [('SET_MILLISECOND_TIMER', 'Test S6 Roll', 0.5)]))
        s.append(Script('Test - S6 reroll', [('TIMER_EXPIRED', 'Test S6 Roll')],
                        [('SET_RANDOM_COUNTER', 'CNV_S6_R', 1, 3), ('SET_RANDOM_TIMER', 'CNV_S6_T', 1, 3),
                         ('STOP_TIMER', 'CNV_S6_T'), ('SET_MILLISECOND_TIMER', 'Test S6 Roll', 0.5)], once=False))
        s += [Script(f'Test - S6 seen {v}', [('COUNTER', 'CNV_S6_R', EQ, v)], [_add(2 ** v, RND)]) for v in range(5)]
        s += [Script(f'Test - S6 tseen {v}', [('COUNTER', 'CNV_S6_T', EQ, v)], [_add(2 ** v, RTM)]) for v in range(5)]
        # 计时
        s.append(Script('Test - S6 clocks', [], [('SET_TIMER', 'Test S6 Frames45', 45),
                                                 ('SET_RANDOM_MSEC_TIMER', 'Test S6 Six', 6.0, 6.0),
                                                 ('SET_RANDOM_MSEC_TIMER', 'Test S6 Eight', 8.0, 10.0),
                                                 ('SET_MILLISECOND_TIMER', 'Test S6 Twenty', 20.0)]))
        s += [Script('Test - S6 t45', [('TIMER_EXPIRED', 'Test S6 Frames45')], [_add(1, CLK)]),
              Script('Test - S6 t6', [('TIMER_EXPIRED', 'Test S6 Six')], [_add(2, CLK)]),
              Script('Test - S6 t8', [('TIMER_EXPIRED', 'Test S6 Eight')], [_add(4, CLK)]),
              Script('Test - S6 le15', [('COUNTER_SECONDS', 'Test S6 Twenty', LE, 15.0)], [_add(8, CLK)]),
              Script('Test - S6 lt12', [('COUNTER_SECONDS', 'Test S6 Twenty', LT, 12.0)], [_add(16, CLK)]),
              Script('Test - S6 k60', [('COUNTER_COUNTER', F, GE, 'CNV_S6_K')], [_add(32, CLK)])]
        t.expect += [('帧', 6, '>', 50), ('自关', 2, '==', 11), ('开关', RUN - 2, '==', 42), ('子程序', RUN - 2, '==', 21),
                     ('否则', RUN - 2, '==', 21), ('随机', RUN - 2, '==', 14), ('计时', RUN - 2, '==', 63),
                     ('随帧', RUN - 2, '==', 14)]
        t.counters = [(c, label) for c, label in t.counters if label in SHOW[show]]     # four lines fit; all scripts run
        t.expect = [e for e in t.expect if e[0] in SHOW[show]]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1.0, sheet=False, lines=len(t.counters)))]
        return t


    MISSION = {'engine_scripts6': mission}
    CHECKS = {'engine_scripts6': {k: (lambda m, k=k: core(m, k)) for k in SHOW}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_scripts7():
    """Engine probe, inventory batch 2 (docs/engine/inventory.md, the heaviest inferred script actions that need units):
    UNIT_IDLE_FOR_FRAMECOUNT, CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION / CREATE_UNNAMED_..._WITH_ORIENTATION,
    OBJECTLIST_ADDOBJECTTYPE (read by PLAYER_HAS_OBJECT_COMPARISON and the nearest-reference actions),
    UNIT_AFFECT_OBJECT_PANEL_FLAGS / TEAM_AFFECT_OBJECT_PANEL_FLAGS (Indestructible), ATTACK_MOVE_NAMED_UNIT_TO,
    SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER. Mission here (build engine_scripts7) on maps/probe_border.py (the
    simulator's level ground, 5000 x 5000); the scenes stand >= 1000 apart where an enemy is, so nobody fires across. What
    the simulator (sim.py) predicts is in brackets.

      idle    the player's Guardians idle 1-3 at (2900, 4200 / 4350 / 4500), each sent 1200 east at 1 s; at IDLE_AT
              UNIT_IDLE_FOR_FRAMECOUNT(idle 1, 15), (idle 3, 1); idle 2 the control. 一到 / 二到 / 三到 = 1 while idle k is
              at its goal [二到 only: like the seconds version (engine_scripts1 idle) the order is dropped]
      face    at 1 s CREATE_NAMED_..._WITH_ORIENTATION a Guardian at (3700, 4700) angle 0 and (3900, 4700) angle pi/2,
              CREATE_UNNAMED_..._WITH_ORIENTATION at (4100, 4700) pi and (4300, 4700) -3pi/4 (retail's value); 造出 = the
              player's Guardians in that row [4]; the facing is the picture (bench_look at 4 s) [angle in radians, 0 east,
              pi/2 north: the map's own convention, as placed objects]
      panel   the player's Guardians pan 1-4 at (2900 .. 3500, 4700): Indestructible on pan 1 (UNIT_...) and on crew Pan
              = pan 3, pan 4 (TEAM_...) at the start; NAMED_DAMAGE 300 to all four at 2 s, NAMED_KILL pan 1, pan 2, pan 3
              at 4 s; flags off (UNIT pan 1, TEAM Pan) at 6 s; NAMED_DAMAGE 300 to pan 4 and NAMED_KILL pan 1, pan 3 at 8 s.
              血一 / 血二 / 血四 = pan 1 / 2 / 4 health %; 活着 = 1 pan 1 + 2 pan 2 + 4 pan 3 + 8 pan 4 not destroyed
              [damage none on an indestructible one; NAMED_KILL kills it anyway: 15 -> 15 at 2 s -> 8 at 4 s -> 0 at 8 s?
              (Generals' Object::kill goes through attemptDamage, which an indestructible body refuses)]
      amove   lane A: am 1 (400, 4050) ATTACK_MOVE_NAMED_UNIT_TO (2400, 4050) at 1 s; lane B: am 2 (400, 4850)
              MOVE_NAMED_UNIT_TO (2400, 4850); an enemy (s1, NO_ATTACK so it does not shoot back) Guardian 60 off each
              lane halfway (1400). 到一 / 到二 = 1 while am k is at its goal; 敌一 / 敌二 = the enemy's health %
              [am 1 stops, kills e1 and goes on; am 2 drives by, e2 stays 100]
      list    s1's Guardian 'near' (named, 3900, 3000), Peacekeeper 'mid' (unnamed, 4100, 3000), Guardian 'far'
              (unnamed, 4300, 3000); the player's crew Ref, one Guardian at (2900, 3000). At the start
              OBJECTLIST_ADDOBJECTTYPE(Guardian, L), (Peacekeeper, P) twice; at LIST_AT (Peacekeeper, L).
              列表 = s1's objects of L (PLAYER_HAS_OBJECT_COMPARISON) [4 (with the two amove enemies), then 5 from LIST_AT]; 单类 = of P [1];
              at REF_AT SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER(L, s1, Ref, R1) and the UNNAMED one (L, ..., R2):
              参考 / 无名参考 = 1 / 2 / 4 as the reference stands at near / mid / far [R1 near (named ones count),
              R2 mid (named ones skipped)]

    读数 (bench 2026-11-09, run_queue engine_scripts7:*; sim pairs tests/test_simbench.py test_scripts7_*):
      idle    PASS. 二到 1 from s14; 一到, 三到 0 all 25 s: UNIT_IDLE_FOR_FRAMECOUNT drops the order, 15 frames or 1 (as
              the seconds version). The simulator agrees.
      face    PASS. 造出 4 from s1: CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION and CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT_
              WITH_ORIENTATION make their object at the waypoint. The facing (bench 2026-11-10, CampScr7Face_mcp_1110_
              232041 frame 11, s30; the hull by its two rear aerials, the turret turns on its own): east, north, west,
              south-west for 0, pi/2, pi, -3pi/4 -- radians, 0 east, pi/2 north, as the simulator. The check's own look
              (frame 5) again showed open ground: its bench_camera did not move the camera (the minimap box elsewhere);
              a second bench_camera by hand did.
      panel   PASS (third run; the first two gave NAMED_DAMAGE 300.0 / 200.0, a float, which does nothing --
              engine_garrison). 甲血 乙血 丁血 58 58 58 from s1, 活着 15 -> 11 at s3, 甲血 丁血 16 from s7: NAMED_DAMAGE 200
              took 42 % off pan 1 (UNIT_AFFECT_OBJECT_PANEL_FLAGS Indestructible) and pan 4 (TEAM_..._FLAGS) as off the
              control; NAMED_KILL killed pan 3 (TEAM flag; the first run: pan 1 too). So the flag stops no scripted damage
              nor a kill [the Generals reading was wrong for RA3]; whether it stops a weapon's damage is not measured.
              The simulator now lets NAMED_DAMAGE through (it refused it); weapons still refused (推断).
      list    (third run; the first two stopped in the contract: a ref set by SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_
              PLAYER and an object list's name as a type were not published -- contract.py knows both now). 列表 4 all
              run (s1-s11): OBJECTLIST_ADDOBJECTTYPE's list counts in PLAYER_HAS_OBJECT_COMPARISON (s1's 4 Guardians, a
              type given lower case); the Peacekeeper added to it at LIST_AT (4 s) NOT counted (still 4 at s11) [the
              condition keeps its answer till objects are made / removed / killed / change hands, A358];
              单类 1 (a type added twice counts once). 参考 1, 无名参考 2 from s5: SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_
              PLAYER took the named Guardian nearest the team, the UNNAMED one skipped it for the Peacekeeper -- both with
              an object list for the type. The simulator agrees on the refs.
      amove   PASS (second run; the first run's labels 到一 / 敌一 read '?': a label ending in 一 before the number does
              not parse -- the labels now start with 甲 / 乙). 乙到 1 from s23, 甲到 from s38; 乙敌 100 -> 87 -> 74 -> 60
              (s10-s15) then 60: MOVE_NAMED_UNIT_TO's tank fires as it drives by (3 hits); 甲敌 100 -> 12 by s22 (8 hits,
              ~12.5 % each) then 12 to the end: ATTACK_MOVE_NAMED_UNIT_TO's tank stopped to fight, left the enemy at 12 %
              and went on (arrived 15 s after the mover). The simulator: the attack-mover kills it (0 at 28 s) and has not
              arrived by 60 s; its hits ~6 % each (the weapon's damage: engine line C). strict xfail in test_simbench.
    """
    from maps import probe_border
    from parts import Mission, Script, Test, counted, square, status

    TANK, PK = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
    O = (1300.0, 4300.0)                            # probe_border's 'stop row': every place below is absolute
    IDLE_AT, LIST_AT, REF_AT = 3.0, 4.0, 6.0
    RUN = {'idle': 25.0, 'face': 8.0, 'panel': 12.0, 'amove': 60.0, 'list': 10.0}
    EQ = 2
    L, P = 'cnv s7 list', 'cnv s7 pk'
    LIST_SPOTS = {'near': (3900.0, TANK, True), 'mid': (4100.0, PK, False), 'far': (4300.0, TANK, False)}
    LIST_Y = 3000.0


    def _n(part):
        return f'UNIT - CNV S7 {part}'


    def _put(m, template, x, y, **kw):
        m.put(template, 'stop row', x - O[0], y - O[1], **kw)


    def _wp(m, part, x, y):
        m.waypoint(part, f'CNV S7 {part.title()}', 'stop row', x - O[0], y - O[1])


    def mission():
        m = Mission(name='CampScr7', map=probe_border, units=[], facts={})
        m.spawns |= {TANK, PK}
        pan, ref = m.crew('Pan'), m.crew('Ref')
        for k, y in enumerate((4200.0, 4350.0, 4500.0), 1):
            _put(m, TANK, 2900.0, y, angle=0.0, name=_n(f'Idle {k}'), role=f'idle {k}')
            _wp(m, f'goal {k}', 4100.0, y)
        for k in range(1, 5):
            _put(m, TANK, 2700.0 + 200.0 * k, 4700.0, angle=0.0, name=_n(f'Pan {k}'), role=f'pan {k}',
                 **({'props': {'originalOwner': pan}} if k > 2 else {}))
        for k, (x, _, _) in enumerate(FACE, 1):
            _wp(m, f'face {k}', x, FACE_Y)
        for k, y, e in ((1, 4050.0, 4110.0), (2, 4850.0, 4790.0)):
            _put(m, TANK, 400.0, y, angle=0.0, name=_n(f'Am {k}'), role=f'am {k}')
            _put(m, TANK, 1400.0, e, side='s1', angle=3.1416, name=_n(f'Enemy {k}'), role=f'enemy {k}')
            _wp(m, f'lane {k}', 2400.0, y)
        for part, (x, template, named) in LIST_SPOTS.items():
            _put(m, template, x, LIST_Y, side='s1', angle=3.1416, name=_n(part.title()) if named else '',
                 role=part if named else '')
        _put(m, TANK, 2900.0, LIST_Y, angle=0.0, name=_n('Ref'), role='ref', props={'originalOwner': ref})
        return m


    def _at(t, key, secs, actions):
        timer = f'Test S7 {key} Timer'
        t.scripts += [Script(f'Test - S7 {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                      Script(f'Test - S7 {key}', [('TIMER_EXPIRED', timer)], actions)]


    def _sum(t, counter, label, parts):
        """counter = the sum of the weights whose condition holds, recounted every frame. parts: [(weight, condition)]."""
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        t.scripts += [Script(f'Test - {counter} {k}', [c], [('INCREMENT_COUNTER', w, counter)], once=False)
                      for k, (w, c) in enumerate(parts)]


    def _exact(t, counter, label, player, kind, most=6):
        """counter = how many objects of `kind` (a type or an object list) `player` has (PLAYER_HAS_OBJECT_COMPARISON ==)."""
        t.counters.append((counter, label))
        t.scripts += [Script(f'Test - {counter} {n}', [('PLAYER_HAS_OBJECT_COMPARISON', player, EQ, n, kind)],
                             [('SET_COUNTER', counter, n)], once=False) for n in range(most)]


    def _watch(t, run, every=1.0, look=None):
        w = dict(seconds=run, every=every, sheet=False, lines=len(t.counters))
        if look is None:
            t.bench = [('bench_watch', w)]
            return
        at, x, y, note = look
        t.bench = [('bench_watch', dict(w, seconds=at)), ('bench_camera', dict(x=x, y=y, look=False)),
                   ('bench_look', dict(note=note)), ('bench_watch', dict(w, seconds=run - at))]


    def idle(m):
        t = Test()
        names = [m.role(f'idle {k}').name for k in (1, 2, 3)]
        _at(t, 'go', 1.0, [('MOVE_NAMED_UNIT_TO', n, m.mark(f'goal {k}')) for k, n in enumerate(names, 1)])
        _at(t, 'idle', IDLE_AT, [('UNIT_IDLE_FOR_FRAMECOUNT', names[0], 15), ('UNIT_IDLE_FOR_FRAMECOUNT', names[2], 1)])
        for k, n in enumerate(names, 1):
            area = f'Test S7 Goal {k}'
            t.areas[area] = square(*m.point(f'goal {k}'), 80.0)
            counted(f'CNV_S7_At{k}', '一二三'[k - 1] + '到', t, named=n, area=area)
        t.expect += [('二到', RUN['idle'] - 2, '==', 1)]
        _watch(t, RUN['idle'])
        return t


    def face(m):
        t = Test()
        team = f'{m.player()}/team{m.player()}'
        acts = []
        for k, (x, angle, named) in enumerate(FACE, 1):
            wp = m.mark(f'face {k}')
            acts.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION', _n(f'Face {k}'), TANK, team, wp, angle)
                        if named else ('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION', TANK, team, wp, angle))
        _at(t, 'make', 1.0, acts)
        t.areas['Test S7 Face Row'] = square(4000.0, FACE_Y, 400.0)
        counted('CNV_S7_Made', '造出', t, template=TANK, area='Test S7 Face Row')
        t.expect += [('造出', 4, '==', 4)]
        _watch(t, RUN['face'], look=(4.0, 4000.0, FACE_Y, 'four Guardians made at 1 s, left to right: angle 0, pi/2 '
                                     '(named), pi, -3pi/4 (unnamed) -- which way does each face?'))
        return t


    def panel(m):
        t = Test()
        pan = [m.role(f'pan {k}').name for k in range(1, 5)]
        crew = m.teams['Pan']
        t.scripts.append(Script('Test - S7 flags on', [], [('UNIT_AFFECT_OBJECT_PANEL_FLAGS', pan[0], 'Indestructible', 1),
                                                          ('TEAM_AFFECT_OBJECT_PANEL_FLAGS', crew, 'Indestructible', 1)]))
        _at(t, 'hurt', 2.0, [('NAMED_DAMAGE', n, 200) for n in (pan[0], pan[1], pan[3])])     # an integer (engine_garrison)
        _at(t, 'kill', 4.0, [('NAMED_KILL', pan[2])])
        _at(t, 'off', 6.0, [('UNIT_AFFECT_OBJECT_PANEL_FLAGS', pan[0], 'Indestructible', 0),
                            ('TEAM_AFFECT_OBJECT_PANEL_FLAGS', crew, 'Indestructible', 0)])
        _at(t, 'again', 8.0, [('NAMED_DAMAGE', pan[0], 200), ('NAMED_DAMAGE', pan[3], 200)])
        for k, label in ((1, '甲血'), (2, '乙血'), (4, '丁血')):
            counted(f'CNV_S7_H{k}', label, t, health=pan[k - 1])
        _sum(t, 'CNV_S7_Alive', '活着', [(2 ** k, ('NAMED_NOT_DESTROYED', n)) for k, n in enumerate(pan)])
        t.expect += [('活着', RUN['panel'] - 2, '==', 11)]
        _watch(t, RUN['panel'], 0.5)
        return t


    def amove(m):
        t = Test()
        am = [m.role(f'am {k}').name for k in (1, 2)]
        en = [m.role(f'enemy {k}').name for k in (1, 2)]
        t.scripts.append(Script('Test - S7 hold fire', [], [('UNIT_CHANGE_OBJECT_STATUS', n, status('NO_ATTACK'), 1)
                                                           for n in en]))
        _at(t, 'go', 1.0, [('ATTACK_MOVE_NAMED_UNIT_TO', am[0], m.mark('lane 1')),
                           ('MOVE_NAMED_UNIT_TO', am[1], m.mark('lane 2'))])
        for k in (1, 2):
            area = f'Test S7 Lane {k}'
            t.areas[area] = square(*m.point(f'lane {k}'), 80.0)
            counted(f'CNV_S7_Lane{k}', '甲乙'[k - 1] + '到', t, named=am[k - 1], area=area)
        for k in (1, 2):
            counted(f'CNV_S7_E{k}', '甲乙'[k - 1] + '敌', t, health=en[k - 1])
        t.expect += [('甲到', RUN['amove'] - 2, '==', 1), ('乙到', RUN['amove'] - 2, '==', 1)]
        _watch(t, RUN['amove'])
        return t


    def list_(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts.append(Script('Test - S7 lists', [], [('OBJECTLIST_ADDOBJECTTYPE', TANK.lower(), L),
                                                        ('OBJECTLIST_ADDOBJECTTYPE', PK.lower(), P),
                                                        ('OBJECTLIST_ADDOBJECTTYPE', PK.lower(), P)]))
        _at(t, 'grow', LIST_AT, [('OBJECTLIST_ADDOBJECTTYPE', PK.lower(), L)])
        ref = m.teams['Ref']
        _at(t, 'refs', REF_AT, [('SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER', L, s1, ref, 'UNITRef - CNV S7 R1'),
                                ('SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER', L, s1, ref, 'UNITRef - CNV S7 R2')])
        _exact(t, 'CNV_S7_L', '列表', s1, L)
        _exact(t, 'CNV_S7_P', '单类', s1, P)
        for part, (x, _, _) in LIST_SPOTS.items():
            t.areas[f'Test S7 At {part}'] = square(x, LIST_Y, 60.0)
        for counter, label, r in (('CNV_S7_R1', '参考', 'UNITRef - CNV S7 R1'), ('CNV_S7_R2', '无名参考', 'UNITRef - CNV S7 R2')):
            _sum(t, counter, label, [(w, ('NAMED_INSIDE_AREA', r, f'Test S7 At {part}'))
                                     for w, part in ((1, 'near'), (2, 'mid'), (4, 'far'))])
        t.expect += [('列表', 2, '==', 4), ('列表', RUN['list'] - 2, '==', 4), ('单类', RUN['list'] - 2, '==', 1)]
        _watch(t, RUN['list'])
        return t


    MISSION = {'engine_scripts7': mission}
    CHECKS = {'engine_scripts7': {'idle': idle, 'face': face, 'panel': panel, 'amove': amove, 'list': list_}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_scripts8():
    """Engine probe, inventory batch 3 (docs/engine/inventory.md, the heaviest script actions the simulator lacked):
    TEAM_DELETE / TEAM_KILL, TEAM_IDLE_FOR_SECONDS / TEAM_IDLE_FOR_FRAMECOUNT, TEAM_MERGE_INTO_TEAM,
    UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION. Mission here (build engine_scripts8) on maps/probe_border.py
    (level ground 5000 x 5000; every place absolute, the scenes >= 1000 apart where an enemy is). The rest of the batch
    (the team status, the base power, the player's superweapon cast and its availability) is benches/script/control/checks.py#engine_scripts8b
    (the bench crashed at start on 11-09; measured the same evening).
    What the simulator (sim.py) predicts is in brackets.

      team    the player's crews Del, Kil, Liv (two Guardians each, row y 1000); at 2 s TEAM_DELETE Del, TEAM_KILL Kil,
              Liv the control (the DELETE_LIVING variant is not in script_catalog.json: not asked). 活着 = 1 / 2 Del's, 4 / 8
              Kil's, 16 / 32 Liv's not destroyed; 甲死帧 / 乙死帧 = frames Kil 1 / Del 1 is NAMED_DYING [63 -> 51 at 2 s
              -> 48 a frame later (Del's gone a frame after Kil's); 甲死帧 1, 乙死帧 0]
      idle    crews Idl, Idf, Ctl (two Guardians each, y 2000 / 2200 / 2400) sent 1300 east (MOVE_TEAM_TO) at 1 s; at 3 s
              TEAM_IDLE_FOR_SECONDS(Idl, 3), TEAM_IDLE_FOR_FRAMECOUNT(Idf, 15). 到 = Idl's at the goal x1 + Idf's x10 +
              Ctl's x100 [200 from s15: the order dropped, as the unit versions (engine_scripts7 idle)]
      merge   crews Src (2) and Dst (1); at 1 s TEAM_MERGE_INTO_TEAM(Src, Dst), at 2 s MOVE_TEAM_TO(Dst, goal M). Crews
              Sr2 (2) and Ds2 (1); at 1 s TEAM_MERGE_INTO_TEAM(Sr2, Ds2), at 2 s MOVE_TEAM_TO(Sr2, goal N). 合 = in goal M:
              Src's x1 + Dst's x10; 源 = in goal N: Sr2's x1 + Ds2's x10 [合 1 from s13, 12 from s15; 源 0: the source empty]
      spawn   at 1 s UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION('... Spawned', Guardian, the player's team,
              the player's Guardian 'anchor' at (3500, 3500)). 生 = 1 the spawned one not destroyed + 2 within 150 of the
              anchor [3 from s1]

    读数 (bench 2026-11-09, run_queue engine_scripts8:*; the bench's seconds run ~1 s ahead of the timers):
      team    活着 48 from s1 to the end (s9), 甲死帧 1, 乙死帧 1: TEAM_DELETE and TEAM_KILL take every member at once;
              both the killed and the deleted one are NAMED_DYING for one frame. The first run asked 活着 63 at s1 (FAIL:
              the bench's clock, not the game). The simulator: Del's gone a frame after Kil's, and a deleted one never
              dying (乙死帧 0) -- a frame's difference, not fixed.
      idle    PASS. 到 100 at s12 (the control's first), 200 from s13: TEAM_IDLE_FOR_SECONDS 3 and TEAM_IDLE_FOR_FRAMECOUNT
              15 drop the move order (not a pause), as the unit versions. The simulator agrees.
      merge   PASS. 合 1 at s11, 12 from s13; 源 0 all run: TEAM_MERGE_INTO_TEAM moves the source's members to the target
              (they took the target's order); an order to the source afterwards moves nobody. The simulator agrees.
      spawn   PASS. 生 3 from s1: UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION makes the named object at the
              object's place (within 150). The simulator agrees.
    """
    from parts import Test, square
    from checks.engine_scripts8 import (
        ANCHOR, IDLE_ROW, RUN, SPAWNED, TANK, TEAM_ROW, at, frames, mission, total, watch,
    )


    def _goal(t, m, part):
        area = f'Test S8 {part.title()}'
        t.areas[area] = square(*m.point(part), 150.0)
        return area


    def team(m):
        t = Test()
        at(t, 'end', 2.0, [('TEAM_DELETE', m.teams['Del']), ('TEAM_KILL', m.teams['Kil'])])
        names = [m.role(f'{c} {k}').name for c in TEAM_ROW for k in (1, 2)]
        total(t, 'CNV_S8_Alive', '活着', [(2 ** k, ('NAMED_NOT_DESTROYED', n)) for k, n in enumerate(names)])
        frames(t, 'CNV_S8_KDie', '甲死帧', [('NAMED_DYING', m.role('Kil 1').name)])
        frames(t, 'CNV_S8_DDie', '乙死帧', [('NAMED_DYING', m.role('Del 1').name)])
        t.expect += [('活着', RUN['team'] - 2, '==', 48)]        # the bench's seconds run ~1 s ahead: s1 already 48
        watch(t, RUN['team'], 0.5)
        return t


    def idle(m):
        t = Test()
        at(t, 'go', 1.0, [('MOVE_TEAM_TO', m.teams[c], m.mark(f'idle {c}')) for c in IDLE_ROW])
        at(t, 'idle', 3.0, [('TEAM_IDLE_FOR_SECONDS', m.teams['Idl'], 3), ('TEAM_IDLE_FOR_FRAMECOUNT', m.teams['Idf'], 15)])
        parts = []
        for w, c in ((1, 'Idl'), (10, 'Idf'), (100, 'Ctl')):
            area = _goal(t, m, f'idle {c}')
            parts += [(w, ('NAMED_INSIDE_AREA', m.role(f'{c} {k}').name, area)) for k in (1, 2)]
        total(t, 'CNV_S8_At', '到', parts)
        t.expect += [('到', RUN['idle'] - 2, '>=', 200)]
        watch(t, RUN['idle'])
        return t


    def merge(m):
        t = Test()
        at(t, 'merge', 1.0, [('TEAM_MERGE_INTO_TEAM', m.teams['Src'], m.teams['Dst']),
                             ('TEAM_MERGE_INTO_TEAM', m.teams['Sr2'], m.teams['Ds2'])])
        at(t, 'go', 2.0, [('MOVE_TEAM_TO', m.teams['Dst'], m.mark('merge M')),
                          ('MOVE_TEAM_TO', m.teams['Sr2'], m.mark('merge N'))])
        for counter, label, goal, src, dst in (('CNV_S8_M', '合', 'merge M', 'Src', 'Dst'),
                                               ('CNV_S8_N', '源', 'merge N', 'Sr2', 'Ds2')):
            area = _goal(t, m, goal)
            total(t, counter, label, [(1, ('NAMED_INSIDE_AREA', m.role(f'{src} {k}').name, area)) for k in (1, 2)]
                  + [(10, ('NAMED_INSIDE_AREA', m.role(f'{dst} 1').name, area))])
        t.expect += [('合', RUN['merge'] - 2, '==', 12)]
        watch(t, RUN['merge'])
        return t


    def spawn(m):
        t = Test()
        at(t, 'spawn', 1.0, [('UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION', SPAWNED, TANK, m.team(),
                              m.role('anchor').name)])
        t.areas['Test S8 Anchor'] = square(*ANCHOR, 150.0)
        total(t, 'CNV_S8_Spawn', '生', [(1, ('NAMED_NOT_DESTROYED', SPAWNED)),
                                        (2, ('NAMED_INSIDE_AREA', SPAWNED, 'Test S8 Anchor'))])
        t.expect += [('生', RUN['spawn'] - 2, '==', 3)]
        watch(t, RUN['spawn'], 0.5)
        return t


    MISSION = {'engine_scripts8': mission}
    CHECKS = {'engine_scripts8': {'team': team, 'idle': idle, 'merge': merge, 'spawn': spawn}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_scripts8b():
    """Inventory batch 3, the part measured second (it crashed at start, DirectX box, 11-09 x5; run the same evening after
    the user closed Red Alert 2): the team status, the base power, the player's superweapon cast and its availability.
    Builds engine_scripts8b (engine_scripts8's map) and engine_scripts8bs (missions/super_bench.py's Niagara). What the
    simulator predicted is in brackets; the bench's seconds run ~1 s ahead of the timers (engine_scripts8).

      status  (engine_scripts8's map) crew Hold (two Guardians) ~140 from an enemy Guardian (NO_ATTACK, so it does not
              shoot back); a lone Guardian 'free' 120 from another (the control), 1200 south. The team status action,
              NO_ATTACK on at the start, off at OFF_AT. 甲敌 / 乙敌 = the held crew's / the control's enemy's health %
              [甲敌 100 until OFF_AT, 88 at 11 s; 乙敌 94 at 1 s, down ~6 a second]
      power   the base power action (player, 1000) at 2 s, (player, 300) at 6 s. 电级 = how many of 0 / 1 / 300 / 1000 /
              1001 / 1300 the excess power is at least [1 -> 4 at 2 s -> 3 at 6 s: a supply set, not added]
      pfire   (the player's proton collider, enemy base defenses at 0 / 150 / 240 / 300 from 'Test Proton Spot'; the rest
              deleted at the start) the player-level superweapon cast at frame CAST of the tick; 帧数 = frames since;
              满血帧 = frames target 0 is at 100 after the cast; 血0 = its health %; 施放数 = frames the player's power is
              seen triggered [as engine_super q's named cast: 满血帧 56, 血0 44]
      pdis    the same with the availability action ('Disabled') at the start, and the named cast (the collider) at
              CAST + LATER [a script's cast goes all the same: 满血帧 56; a player's click would be refused]
      near / team  (the same map, round 283; the four vacuum-spot base defenses kept: vtarget 0 / 350 are s4's crew Vt,
              150 / 280 s1's; p1's crew Ft, two tanks 800 apart, its middle 262 off vtarget 350 and 489 off 150) at CAST:
              near = FIRE_SPECIAL_POWER_ON_NEAREST_OBJECTTYPE_BY_PLAYER (p1, collider, AlliedBaseDefense, Ft, s1), team =
              FIRE_SPECIAL_POWER_ON_TEAM (p1, collider, Vt). 血<d> = vtarget d's health % [near: 150 hit (0 and 280 with
              it), 350 whole -- s1's nearest the middle, not s4's; team: 0 and 350 hit, 150 / 280 whole -- the middle]
      nae / nas  near with the target players "<This Player's Enemies>" (our scripts are Player_1's list: Soviet_1..6);
              nas has s1's 150 / 280 deleted at the start [the first in slot order that has one (work/re a283): nae as
              near, s1's 150, not s4's nearer 350; nas s4's 350]

    读数 (bench 2026-11-09 evening, run_queue pend_scripts8:* -- the names before this file's move):
      status  甲敌 100 to s8, 75 at s9, 50 s11, 25 s13, 12 from s15; 乙敌 87 at s1, down ~6 a second to 12 at s12:
              TEAM_CHANGE_OBJECT_STATUS NO_ATTACK holds every member's fire and lifting it frees them at once (the timer's
              10 s = the bench's s9). As the simulator. The first run asked 甲敌 100 from s9 (FAIL: the bench's clock).
      power   电级 4 at s1-s4, 3 from s5: PLAYER_SET_BASE_POWER sets the supply (1000, then 300), it does not add. As
              the simulator (the timers' 2 / 6 s = the bench's s1 / s5). The first run asked 4 from s4 to the end (FAIL:
              the expectation's end second missing).
      pfire   满血帧 56, 血0 44, 施放数 1 (from s7): PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT casts the player's collider as
              the named cast does, and PLAYER_TRIGGERED_SPECIAL_POWER sees it for one frame. As the simulator.
      pdis    满血帧 56, 血0 44, 施放数 1 at s7: with PLAYER_SPECIAL_POWER_AVAILABILITY Disabled a script's player-level
              cast goes all the same (as the simulator). The named cast 300 ticks (~20 s) later: 施放数 2 from s26 but
              血0 stays 44 -- seen as triggered, no blast. The simulator had it hit again; now sim.py's rule (INFERRED):
              a cast in the reload its own last cast started brings no blast (a collider never cast fires uncharged,
              engine_super p / q).
    """
    from parts import Script, Test, status
    import checks.engine_scripts8 as s8

    OFF_AT, CAST, LATER = 10.0, 75, 300
    RUN = {'status': 20.0, 'power': 10.0, 'pfire': 20.0, 'pdis': 40.0, 'near': 20.0, 'nae': 20.0, 'nas': 20.0, 'team': 20.0, 'most': 20.0, 'two': 20.0}
    GE = 3
    LEVELS = (0, 1, 300, 1000, 1001, 1300)
    TEAM_STATUS, BASE_POWER = 'TEAM_CHANGE_OBJECT_STATUS', 'PLAYER_SET_BASE_POWER'
    P_FIRE, P_AVAIL = 'PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'PLAYER_SPECIAL_POWER_AVAILABILITY'
    POWER_P = 'SpecialPowerParticleCannon'      # missions/super_bench.py's collider power (G5: a check asks no mission)
    TARGET, VDIST = 'AlliedBaseDefense', (0, 150, 280, 350)
    VT = ('near', 'team', 'nae', 'nas')                 # the checks on the vacuum-spot targets
    NEAREST, ON_TEAM = 'FIRE_SPECIAL_POWER_ON_NEAREST_OBJECTTYPE_BY_PLAYER', 'FIRE_SPECIAL_POWER_ON_TEAM'
    AT_MOST = 'SKIRMISH_FIRE_SPECIAL_POWER_AT_' + 'MOST_COST'
    PDIST = (0, 150, 240, 300)
    TWO = ('target 240', 'target 300', 'dtarget 0', 'dtarget 150', 'dtarget 250', 'dtarget 350')  # two: 2 defenses vs 4


    def mission():
        return s8.mission('CampS8b')


    def status_(m):
        t = Test()
        foes = [m.role(f'{p} foe').name for p in s8.STATUS]
        t.scripts.append(Script('Test - S8 hold', [], [('UNIT_CHANGE_OBJECT_STATUS', n, status('NO_ATTACK'), 1) for n in foes]
                                + [(TEAM_STATUS, m.teams['Hold'], status('NO_ATTACK'), 1)]))
        s8.at(t, 'off', OFF_AT, [(TEAM_STATUS, m.teams['Hold'], status('NO_ATTACK'), 0)])
        for counter, label, n in (('CNV_S8_E1', '甲敌', foes[0]), ('CNV_S8_E2', '乙敌', foes[1])):
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Test - {counter}', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', n, counter)],
                                    once=False))
        t.expect += [('甲敌', 0, '==', 100, OFF_AT - 2), ('甲敌', OFF_AT + 1, '<', 100), ('乙敌', 2, '<', 100)]
        s8.watch(t, RUN['status'])
        return t


    def power(m):
        t = Test()
        p1 = m.player()
        s8.at(t, 'set', 2.0, [(BASE_POWER, p1, 1000)])
        s8.at(t, 'reset', 6.0, [(BASE_POWER, p1, 300)])
        s8.total(t, 'CNV_S8_Power', '电级', [(1, ('PLAYER_EXCESS_POWER_' + 'COMPARE_VALUE', p1, GE, n)) for n in LEVELS])
        t.expect += [('电级', 2, '==', 4, 4), ('电级', 6, '==', 3)]
        s8.watch(t, RUN['power'], 0.5)
        return t


    def _super(m, which):
        t = Test()
        p1 = m.player('p1')
        AIMS = {'near': lambda: (NEAREST, p1, POWER_P, TARGET, m.teams['Ft'], m.player('s1')),
                'nae': lambda: (NEAREST, p1, POWER_P, TARGET, m.teams['Ft'], "<This Player's Enemies>"),
                'team': lambda: (ON_TEAM, p1, POWER_P, m.teams['Vt']),
                'most': lambda: (AT_MOST, m.player('s1'), POWER_P)}
        AIMS['two'], AIMS['nas'], most = AIMS['most'], AIMS['nae'], which in ('most', 'two')
        gone = {'vtarget 150', 'vtarget 280'} if which == 'nas' else set()
        power, spot = POWER_P, m.mark('proton spot')
        hit = [f'vtarget {d}' for d in VDIST if f'vtarget {d}' not in gone] if which in VT else \
            [f'target {d}' for d in PDIST]
        hit = list(TWO) if which == 'two' else hit
        keep = {'collider', 'yard', 'power', 'ft a', 'ft b'} - ({'power'} if most else set()) | {'spower'} | set(hit)
        start = [('MAP_REVEAL_ALL_PERM', p1)]
        start += [('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, 'NO_ATTACK', 1) for r in hit + (['yard'] if most else ['ft a', 'ft b'])]
        start += [('NAMED_DELETE', r.name) for k, r in m.cast.items() if k not in keep and r.name]
        if which == 'pdis':
            start.append((P_AVAIL, p1, power, 'Disabled'))
        t.scripts.append(Script('Test - S8 start', [], start))
        t.scripts.append(Script('Test - S8 tick', [], [('INCREMENT_COUNTER', 1, 'CNV_S8_Tick')], once=False))
        t.scripts.append(Script('Test - S8 cast', [('COUNTER', 'CNV_S8_Tick', 2, CAST)],
                                [AIMS.get(which, lambda: (P_FIRE, p1, power, spot))(), ('SET_FLAG', 'Test S8 Cast', 1)]))
        on = ('FLAG', 'Test S8 Cast', 1)
        if which in AIMS:
            rows = [(f'target {d}', d) for d in (0, 240, 300)] + [('yard', 'Y')] if which == 'most' else \
                [(r, r.split()[1]) for r in hit]
            rows = [(r, r[0] + r.split()[1]) for r in TWO[:4]] if which == 'two' else rows     # four lines fit
            for role, d in rows:
                t.counters.append((f'CNV_S8_V{d}', f'血{d}'))
                t.scripts.append(Script(f'Test - S8 health {d}', [on], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',
                                                                         m.role(role).name, f'CNV_S8_V{d}')], once=False))
            t.expect = []
            s8.watch(t, RUN[which], 0.5)
            return t
        if which == 'pdis':
            t.scripts.append(Script('Test - S8 named cast', [('COUNTER', 'CNV_S8_Tick', 2, CAST + LATER)],
                                    [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role('collider').name, power, spot)]))
        target = m.role('target 0').name
        if which == 'pfire':
            s8.frames(t, 'CNV_S8_Frames', '帧数', [on])
        s8.frames(t, 'CNV_S8_Full', '满血帧', [on, ('UNIT_HEALTH', target, 3, 100)])
        t.counters.append(('CNV_S8_H0', '血0'))
        t.scripts.append(Script('Test - S8 health', [on], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, 'CNV_S8_H0')],
                                once=False))
        s8.frames(t, 'CNV_S8_Seen', '施放数', [('PLAYER_TRIGGERED_SPECIAL_POWER', p1, power)])
        t.expect = []
        s8.watch(t, RUN[which], 0.5)
        return t


    MISSION = {'engine_scripts8b': mission}     # engine_scripts8bs / 8bm: missions/super_bench.py makes them
    CHECKS = {'engine_scripts8b': {'status': status_, 'power': power},
              'engine_scripts8bs': {w: (lambda m, w=w: _super(m, w)) for w in ('pfire', 'pdis') + VT},
              'engine_scripts8bm': {w: (lambda m, w=w: _super(m, w)) for w in ('most', 'two')}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_scripts9():
    """Inventory batch 4: the relation overrides (TEAM_SET_OVERRIDE_RELATION_TO_PLAYER,
    PLAYER_SET_OVERRIDE_RELATION_TO_TEAM, TEAM_SET_OVERRIDE_RELATION_TO_TEAM) and the attacks on a team (TEAM_ATTACK_TEAM,
    NAMED_ATTACK_TEAM), benched in round 134 on engine_scripts9b (the enemy crews on Soviet_4 / 5: placed units on a
    Soviet_1 / 2 / 3 crew are on no team, rounds 130-133 below). Was checks/pending_scripts9.py, builds pend_scripts9*
    (the bench_results files of rounds 130-133 carry those names); now engine_scripts9*. Run with run_queue
    engine_scripts9b:rel engine_scripts9b:atk engine_scripts9b:atkr.
    Mission on maps/probe_border.py (level ground; every place absolute, scenes >= 1000 apart). What the simulator
    (sim.py hostile / the two attack branches, INFERRED from Generals' Team::getRelationship and groupAttackTeam)
    predicts is in brackets.

      rel     four pairs, each the player's Guardian at x 1000 and an enemy (s1) Guardian 120 east of it, rows y 1000 /
              2000 / 3000 / 4000; the one whose health is read has NO_ATTACK, so only the side asked about can fire.
                A  the enemy's team FoeA to the player: Neutral at the start, Enemy at OFF_AT. 甲 = the player's health %
                B  the player to the enemy team FoeB: Neutral, Enemy at OFF_AT. 乙 = the enemy's health %
                C  the enemy team FoeC to the player's team MeC: Neutral, Enemy at OFF_AT. 丙 = the player's health %
                D  the control: no override. 丁 = the player's health %
              [simulator 11-09 PASS: 甲 乙 丙 100 to s10, 94 at s11, down ~6 a second (38 at s20); 丁 94 at s1, 0 from s16]
      atk     the player's crew Att (two Guardians, x 3000, y 1000 / 1150) and an enemy crew Tgt (two, x 3500, NO_ATTACK);
              the player's lone 'solo' (3000, 2500) and an enemy crew Tg2 (two, x 3500, y 2500 / 2650, NO_ATTACK); the
              control: the player's 'idle' (3000, 3500) and an enemy 'dummy' (3500, 3500, NO_ATTACK), no order (500 apart:
              nobody fires on his own, engine_scripts8's first status run). At 1 s TEAM_ATTACK_TEAM(Att, Tgt),
              NAMED_ATTACK_TEAM(solo, Tg2). 靶 = not destroyed: Tgt 1 x1, Tgt 2 x2, Tg2 1 x4, Tg2 2 x8, dummy x16
              [simulator 11-09 PASS: 31 to s20; 24 from s21 (Att's two kill Tgt's two side by side, solo kills Tg2 1);
              16 from s38 (solo goes on to Tg2 2: an attack on a team takes the next member); dummy untouched. Without
              the 'next member' rule solo stopped after one (24 to the end): that is what the bench decides]

    BENCH 11-09 (round 130). rel, the relation argument fixed (mapscript.encode_arg now writes index + name; before it a bare
      'Neutral' went out as 0 = Enemy): still 甲乙丙丁 all alike, 87 at s1, 12 from s12 (= dead: the minimap shows each read
      tank gone; a weapon-killed unit's health counter keeps its last value, sim.py now does so too).
      memb: 留 23 from s1 -- TEAM_KILL of the player's crew MeC killed it, of the enemy crews FoeA / Tgt killed nobody: the
      units placed on an ENEMY crew are not members of it (the map has them: originalOwner 'Soviet_1/teamCNVFoeA', the team
      in Teams). atk / atkr (health read, with and without MAP_REVEAL_ALL_PERM): all 100 to s61 -- the target crews are
      empty, so the attacks have nobody to attack. Not an answer on the five actions yet.
    BENCH 11-09 (round 131): why the enemy crews are empty. (The bench's s1 is past the 2 s kill: memb's 23 is the kill's.)
      memb again with every crew written as retail's a02 'TEAM - Dock 01' (24 keys, teamIsSingleton 0, byte for byte):
        23, the same -- the team's shape is not it (mapxml.add_team left as it was).
      memb2 (UNIT_SET_TEAM of each onto its crew at the start, as Mission.order does): 23, the same.
      memb3 (member counts): 甲 (FoeA + 10 x Tgt) 0, 丙 teamSoviet_1 0 while the dummy (placed on it) lives: Soviet_1's
        units are on none of the map's teams.
      memb4 (pend_scripts9b: FoeX on Soviet_4, Tgt / Tg2 on Soviet_5, both DefaultPersonality): 留 16 -- TEAM_KILL takes
        the enemy crews. Soviet_4's AI modules are all 255 like Soviet_1's, so it is the personality: the container
        (Heidelberg, maps/island.py) gives Soviet_1 retail's AIP_A03_Soviet01BaseMarshall, which takes its player's units
        off every team at the start. Retail a02's scripted Soviet04 (whose 'TEAM - Dock 01' its TEAM_KILL takes) is
        DefaultPersonality, base / unit builder 240.
    BENCH 11-09 (round 132): the personality is NOT it. Soviet_1 (and every crew owner) written DefaultPersonality by
      package.write_map (tried, reverted): the change took (engine_protocol pts 敌方点数 1 from s1, was 0: a Default
      player keeps its point), yet memb 23, memb3 甲 0 / 丙 0, rel 甲乙丙丁 alike (87 -> dead), atk / atkr 100 to s61 --
      the enemy crews on Soviet_1 still empty. Only the test's own script names Soviet_1 in the merged mission. Left
      between Soviet_1 and Soviet_4 / 5 in the container: playerAllies 'Soviet_2 Soviet_3' (4 / 5: none), the
      container's own Soviet_1 teams / build lists (Teams, BuildLists chunks), Soviet_4 enemies also StartingUnits.
    BENCH 11-09 (round 133): it is Soviet_1 / 2 / 3 as such, not personality or alliance. memb's 留 (16 = crews killed):
      memb5 (9c: FoeX on Soviet_2, Tgt / Tg2 on Soviet_6, both Marshalls, only 2 allied) 17: Soviet_2's A foe lives,
      Soviet_6's crew dies. memb10 (9h: FoeX on Soviet_3, InnerBaseMarshall like Soviet_6 but allied) 17, the same.
      memb6 (9d: Soviet_1 playerAllies '') 23; memb7 (9e: allies '' on 1 / 2 / 3) 23; memb8 (9f: 2 / 3 Default) 23;
      memb9 (9g: 1 / 2 / 3 Default and no allies) 23. owner (pend_scripts9): the placed A foe and dummy ARE Soviet_1's
      (NAMED_OWNED_BY_PLAYER), so they are owned but on no team. Script-made Soviet_1 units do join a crew
      (engine_reorder / kingref: CREATE_NAMED_ON_TEAM teamSoviet_1 + UNIT_SET_TEAM, PASS). The container's BuildLists
      are per faction (no player names); its other files name no player. Left: what places Soviet_1..3 apart from 4..6
      -- their place in SidesList (before PlyrCivilian), anything SidesList carries per side past the property dict.
      The memb family's expectations are these readings (留 from s4; the bench's s1 is past the 2 s kill, so the 31
      before it is not read): they pin the Soviet_1..3 crews' emptiness, the simulator (16 on any side) differs there.
      rel / atk / atkr left the Soviet_1 build (their readings there are above) for engine_scripts9b.
    BENCH 11-09 (round 134): rel / atk / atkr on engine_scripts9b (FoeX on Soviet_4, Tgt / Tg2 on Soviet_5): PASS, all
      five actions as the simulator has them.
      rel: 甲乙丙 100 to s8, 87 at s9 (the bench's seconds run one ahead of the timers, engine_scripts8b), then ~6 a second,
        12 (= dead) from s21: each of the three overrides holds fire at Neutral and lets it go at Enemy. 丁 (no override)
        87 at s1, 12 from s13. Simulator before this round: 丁 100 to the end -- its fallback took Soviet_2..6 as the
        player's enemies only once their AI was woken; the container's Player_1 has all six in playerEnemies (and they
        fire unprompted), so sim.Sim.enemy now takes every published player as the human's enemy.
      atk / atkr alike (MAP_REVEAL_ALL_PERM changes nothing): 甲 Tgt 1 and 乙 Tg2 1 from s4, ~6 a second, 12 from s16
        (Att's two take Tgt's two side by side: Tgt 1 falls at one tank's rate, like Tg2 1 under solo); 丙 Tg2 2 from s20,
        12 from s32 -- solo goes on to the team's next member; 丁 the dummy 100 to s61. Simulator: the same order, the
        kills at s20 / s37 (first fire s6), 2-4 s behind the bench.
    BENCH 11-09 (round 135): the cause. SidesList decoded whole (u8 1, u32 12 sides, each the property dict + u32 0: no
      build list, nothing else per side); Teams ordinary (teamSoviet_1 like teamSoviet_4). LibraryMapLists (one per side,
      SidesList order) gives Player_2 and Soviet_1 / 2 / 3 Lib_Skirmish_Setup, Soviet_4 / 5 / 6 none -- and
      package.write_map clears every side's scripts but not their libraries. The library's 'Skirmish AI - Transfer Units'
      runs UNIT_AI_TRANSFER_ALL('<This Player>', 1) at the start (with SKIRMISH_AI_MAKE_BASE, _USE_REPAIRS, ...), which
      takes the player's placed units off every team (memb2's start-up UNIT_SET_TEAM did not survive it).
      memb11 (9i: Soviet_1's library list emptied): 留 16 from s1 -- the s1 crews die like Soviet_4's.
      memb12 (9j: 9b's sides with Lib_Skirmish_Setup copied onto Soviet_4 and 5): 留 23 -- their crews go empty.
      Simulator before round 136: neither ran the container's libraries nor took units off teams on UNIT_AI_TRANSFER_ALL
      (16 on s1). Round 136: sim.skirmish_setup runs Lib_Skirmish_Setup for model.handed_to_ai's players after the
      mission's list, and UNIT_AI_TRANSFER_ALL takes the player's units off every team: memb 23, memb3 23, memb4 16,
      memb11 16, memb12 23 -- the bench's. The product side: contract G6c (placed_ai_units_unordered) refuses a level
      order to such a team.
    """
    from maps import probe_border
    from parts import Mission, Script, Test, status
    import checks.engine_scripts8 as s8

    TANK = 'AlliedAntiVehicleVehicleTech1'
    O = (1300.0, 4300.0)                            # probe_border's 'stop row'
    OFF_AT = 10.0
    RUN = {'rel': 20.0, 'atk': 60.0}
    REL = {'A': 1000.0, 'B': 2000.0, 'C': 3000.0, 'D': 4000.0}
    ASKED = {'A': 'me', 'B': 'foe', 'C': 'me', 'D': 'me'}       # whose health is read; the other side holds fire
    ATK = {'Att': ('p1', 3000.0, (1000.0, 1150.0)), 'Tgt': ('s1', 3500.0, (1000.0, 1150.0)),
           'Tg2': ('s1', 3500.0, (2500.0, 2650.0))}


    def _n(part):
        return f'UNIT - CNV S9 {part}'


    def _put(m, template, x, y, **kw):
        m.put(template, 'stop row', x - O[0], y - O[1], **kw)


    def mission(name='CampPend9', foe='s1', moved=None, map=probe_border):
        """foe: the side of the FoeX crews; moved: {crew: side} for an ATK crew moved off its side (pend_scripts9b)."""
        m = Mission(name=name, map=map, units=[], facts={})
        m.spawns |= {TANK}
        for k, y in REL.items():
            me, foe_c = m.crew(f'Me{k}'), m.crew(f'Foe{k}', side=foe)
            _put(m, TANK, 1000.0, y, angle=0.0, name=_n(f'{k} Me'), role=f'{k} me', props={'originalOwner': me})
            _put(m, TANK, 1120.0, y, side=foe, angle=3.1416, name=_n(f'{k} Foe'), role=f'{k} foe',
                 props={'originalOwner': foe_c})
        for crew, (side, x, ys) in ATK.items():
            side = (moved or {}).get(crew, side)
            c = m.crew(crew, side=side)
            for k, y in enumerate(ys, 1):
                kw = {'side': side} if side != 'p1' else {}
                _put(m, TANK, x, y, angle=0.0 if side == 'p1' else 3.1416, name=_n(f'{crew} {k}'), role=f'{crew} {k}',
                     props={'originalOwner': c}, **kw)
        _put(m, TANK, 3000.0, 2500.0, angle=0.0, name=_n('Solo'), role='solo')
        _put(m, TANK, 3000.0, 3500.0, angle=0.0, name=_n('Idle'), role='idle')
        _put(m, TANK, 3500.0, 3500.0, side='s1', angle=3.1416, name=_n('Dummy'), role='dummy')
        return m


    def _hold(m, roles):
        return [('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, status('NO_ATTACK'), 1) for r in roles]


    def rel(m, remove=False, p1=None):
        """remove (rmv, s01's Legion): at OFF_AT TEAM_REMOVE_ALL_OVERRIDE_RELATIONS of FoeA / FoeB / FoeC, not Enemy.
        Predicted (Generals) 甲 丙 as rel, 乙 100. BENCH 11-23 (CampP9bRmv): 丙 87 at s9, 12 from s20, as rel -- the
        team-to-team override goes; 甲 and 乙 100 to s25 -- FoeA's override to the player stays, like the player's to FoeB.
        ral (A348): A and B name the player as retail s04's docks, "<1st Human Player's Allies incl Self>"; ra1 as
        "<1st Human Player>". Predicted as rel (each player of the mask). BENCH 11-24: both 甲 乙 87 at s1, down as 丁, 丙 as
        rel -- the two player overrides take no alias at all (INFERRED: a name lookup, not the mask parse)."""
        t = Test()
        p1 = p1 or m.player()
        held = [f'{k} {ASKED[k]}' for k in REL]      # the one read is the one shot at: it does not shoot back
        over = lambda r: [('TEAM_SET_OVERRIDE_RELATION_TO_PLAYER', m.teams['FoeA'], p1, r),
                          ('PLAYER_SET_OVERRIDE_RELATION_TO_TEAM', p1, m.teams['FoeB'], r),
                          ('TEAM_SET_OVERRIDE_RELATION_TO_TEAM', m.teams['FoeC'], m.teams['MeC'], r)]
        t.scripts.append(Script('Test - S9 start', [], _hold(m, held) + over('Neutral')))
        s8.at(t, 'off', OFF_AT, [('TEAM_REMOVE_ALL_OVERRIDE_RELATIONS', m.teams[f'Foe{k}']) for k in 'ABC']
              if remove else over('Enemy'))
        for k, label in zip(REL, '甲乙丙丁'):
            counter = f'CNV_S9_{k}'
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Test - {counter}', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',
                                                               m.role(f'{k} {ASKED[k]}').name, counter)], once=False))
        t.expect += [(x, 0, '==', 100, OFF_AT - 2) for x in '甲乙丙'] + [('丁', OFF_AT - 2, '<', 100)]
        t.expect += [(x, RUN['rel'] - 2, '<', 100) for x in ('丙' if remove else '甲乙丙')]
        t.expect += [(x, RUN['rel'] - 2, '==', 100) for x in '甲乙'] if remove else []
        s8.watch(t, RUN['rel'])
        return t


    def atk(m, reveal=False):
        t = Test()
        t.scripts.append(Script('Test - S9 hold', [], _hold(m, ['Tgt 1', 'Tgt 2', 'Tg2 1', 'Tg2 2', 'dummy']) +
                                ([('MAP_REVEAL_ALL_PERM', m.player())] if reveal else [])))
        s8.at(t, 'attack', 1.0, [('TEAM_ATTACK_TEAM', m.teams['Att'], m.teams['Tgt']),
                                 ('NAMED_ATTACK_TEAM', m.role('solo').name, m.teams['Tg2'])])
        for k, (role, label) in enumerate(zip(('Tgt 1', 'Tg2 1', 'Tg2 2', 'dummy'), '甲乙丙丁')):  # a dead one's counter keeps its last value
            counter = f'CNV_S9_H{k}'
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Test - {counter}', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',
                                                               m.role(role).name, counter)], once=False))
        t.expect += [('甲', 20, '<', 100), ('乙', 20, '<', 100), ('丙', RUN['atk'] - 2, '<', 100), ('丁', 0, '==', 100)]
        s8.watch(t, RUN['atk'])
        return t


    def atkr(m):
        return atk(m, reveal=True)


    LEFT = {'memb': 23, 'memb2': 23, 'memb3': 23, 'memb4': 16, 'memb5': 17, 'memb6': 23, 'memb7': 23, 'memb8': 23,
            'memb9': 23, 'memb10': 17, 'memb11': 16, 'memb12': 23}        # 留 on the bench (rounds 130-133); members everywhere would be 16


    def memb(m, left=23):
        """Are the placed units members of their crews? Everyone holds fire; at 2 s TEAM_KILL the enemy crews FoeA and Tgt
        and the player's crew MeC. 留 = alive: A foe x1, Tgt 1 x2, Tgt 2 x4, C me x8, dummy (no crew) x16. Members: 16.
        left: the bench's 留 (LEFT)."""
        t = Test()
        every = [f'{k} {w}' for k in REL for w in ('me', 'foe')] + [f'{c} {k}' for c in ATK for k in (1, 2)] + \
            ['solo', 'idle', 'dummy']
        t.scripts.append(Script('Test - S9 hold all', [], _hold(m, every)))
        s8.at(t, 'kill', 2.0, [('TEAM_KILL', m.teams[c]) for c in ('FoeA', 'Tgt', 'MeC')])
        names = [m.role(r).name for r in ('A foe', 'Tgt 1', 'Tgt 2', 'C me', 'dummy')]
        s8.total(t, 'CNV_S9_Alive', '留', [(2 ** k, ('NAMED_NOT_DESTROYED', n)) for k, n in enumerate(names)])
        t.expect += [('留', 4, '==', left)]
        s8.watch(t, 10.0)
        return t


    def memb2(m, left=23):
        """memb with every crew's units put on their crew by script at the start (UNIT_SET_TEAM, as Mission.order does
        before an order): does a script-made membership of an enemy crew hold where the placed originalOwner did not?
        Members: 16, as in memb."""
        t = memb(m, left)
        crews = {'A foe': 'FoeA', 'Tgt 1': 'Tgt', 'Tgt 2': 'Tgt', 'C me': 'MeC'}
        t.scripts.insert(0, Script('Test - S9 set teams', [],
                                   [('UNIT_SET_TEAM', m.role(r).name, m.teams[c]) for r, c in crews.items()]))
        return t


    def memb3(m):
        """memb2 and each crew's member count read every frame (TEAM_COMPARE_NUM_MEMBERS ==): 甲 = FoeA's (1 placed) +
        10 x Tgt's (2), 乙 MeC's (1), 丙 the enemy's default team teamSoviet_1's (dummy, and whoever is not on a crew).
        Before the kill at 2 s a member count says whether the enemy crews have members at all; after it, whether
        TEAM_KILL emptied them."""
        return _members(m, [m.teams['MeC'], _default(m, 's1')], LEFT['memb3'])


    def _default(m, side):
        p = m.player(side)
        return f'{p}/team{p}'


    def _members(m, teams, left):
        """memb2 with 甲 = FoeA's members + 10 x Tgt's, and 乙 / 丙 the member counts of `teams`."""
        t = memb2(m, left)
        s8.total(t, 'CNV_S9_NA', '甲', [(w * n, ('TEAM_COMPARE_NUM_MEMBERS', m.teams[c], 2, n))
                                        for c, w in (('FoeA', 1), ('Tgt', 10)) for n in range(1, 10)])
        for team, counter, label in zip(teams, ('CNV_S9_NC', 'CNV_S9_ND'), '乙丙'):
            t.counters.append((counter, label))
            t.scripts += [Script(f'Test - {counter} {n}', [('TEAM_COMPARE_NUM_MEMBERS', team, 2, n)],
                                 [('SET_COUNTER', counter, n)], once=False) for n in range(10)]
        return t


    def memb4(m):
        """pend_scripts9b: the FoeX crews on Soviet_4 (DefaultPersonality, AI modules 255), Tgt / Tg2 on Soviet_5
        (DefaultPersonality, base / unit builder 240 like retail a02's scripted Soviet04); the dummy stays on Soviet_1
        (the container's BaseMarshall). 甲 = FoeA's + 10 x Tgt's members, 乙 MeC's, 丙 teamSoviet_1's (as memb3; the
        spare players' default teams are not published)."""
        return _members(m, [m.teams['MeC'], _default(m, 's1')], LEFT['memb4'])


    def memb5(m):
        """pend_scripts9c: FoeX on Soviet_2 (the container's Marshall, allied to Soviet_1 / 3), Tgt / Tg2 on Soviet_6
        (a Marshall too, no allies). 留's bits split them: A foe x1 is Soviet_2's, Tgt x2 / x4 Soviet_6's."""
        return memb(m, LEFT['memb5'])


    def memb6(m):
        """pend_scripts9d: memb with Soviet_1's playerAllies emptied (the container: 'Soviet_2 Soviet_3')."""
        return memb(m, LEFT['memb6'])


    def memb7(m):
        """pend_scripts9e: memb with playerAllies emptied on Soviet_1, 2 and 3 (nobody allied to Soviet_1 either way)."""
        return memb(m, LEFT['memb7'])


    def memb8(m):
        """pend_scripts9f: memb with Soviet_2 and 3 (Soviet_1's allies) made DefaultPersonality, the alliances kept."""
        return memb(m, LEFT['memb8'])


    def memb9(m):
        """pend_scripts9g: memb with Soviet_1, 2 and 3 all DefaultPersonality and none allied (9e and 9f at once)."""
        return memb(m, LEFT['memb9'])


    def memb10(m):
        """pend_scripts9h: FoeX on Soviet_3 (InnerBaseMarshall like Soviet_6, but allied to Soviet_1 / 2), Tgt / Tg2 on
        Soviet_6 again (the control). A foe x1 is Soviet_3's."""
        return memb(m, LEFT['memb10'])


    OWNERS = ['Player_1', 'Soviet_1', 'Soviet_2', 'Soviet_3', 'Soviet_4', 'Soviet_5', 'Soviet_6']    # the published ones


    def owner(m):
        """Who owns the placed enemy units (NAMED_OWNED_BY_PLAYER, every frame; the counter = 1 + the owner's place in
        OWNERS, 0 = none of them): 甲 'A foe' (Soviet_1, crew FoeA), 乙 the dummy (Soviet_1's default team), 丙 'C me'
        (the player's, crew MeC: the control, 1). Everyone holds fire, nobody is killed."""
        t = Test()
        every = [f'{k} {w}' for k in REL for w in ('me', 'foe')] + [f'{c} {k}' for c in ATK for k in (1, 2)] + \
            ['solo', 'idle', 'dummy']
        t.scripts.append(Script('Test - S9 hold all', [], _hold(m, every)))
        for role, counter, label in (('A foe', 'CNV_S9_OA', '甲'), ('dummy', 'CNV_S9_OB', '乙'), ('C me', 'CNV_S9_OC', '丙')):
            s8.total(t, counter, label, [(k + 1, ('NAMED_OWNED_BY_PLAYER', p, m.role(role).name))
                                         for k, p in enumerate(OWNERS)])
        t.expect += [('甲', 2, '==', 2), ('乙', 2, '==', 2), ('丙', 2, '==', 1)]
        s8.watch(t, 6.0)
        return t


    def memb11(m):
        """engine_scripts9i: memb with Soviet_1's library list emptied (the container gives Soviet_1 / 2 / 3 and Player_2
        Lib_Skirmish_Setup, whose 'Skirmish AI - Transfer Units' runs UNIT_AI_TRANSFER_ALL on its player at the start)."""
        return memb(m, LEFT['memb11'])


    def memb12(m):
        """engine_scripts9j: memb on engine_scripts9b's sides (FoeX Soviet_4, Tgt / Tg2 Soviet_5) with Soviet_1's library
        list (Lib_Skirmish_Setup) given to Soviet_4 and Soviet_5 as well: the other half of memb11."""
        return memb(m, LEFT['memb12'])


    def _libraries(players):
        """probe_border with the container's script libraries changed (a map module's LIBRARIES, model.libraries: written
        by package.write_map, run by the simulator): {player: 'none' | 'skirmish'} -- 'skirmish' gives it Soviet_1's
        list (Lib_Skirmish_Setup). Rounds 135's builds wrote the same bytes by editing LibraryMaps in terrain()."""
        import types
        from model import SKIRMISH_SETUP
        mod = types.ModuleType(probe_border.__name__)
        mod.__dict__.update({k: v for k, v in vars(probe_border).items() if not k.startswith('__')})
        mod.LIBRARIES = {p: () if what == 'none' else (SKIRMISH_SETUP,) for p, what in players.items()}
        return mod


    def _sides(name, **sides):
        m = mission(name)
        for side, props in sides.items():
            m.sides[side] = dict(m.sides.get(side, {}), **props)
        return m


    def _no_allies():
        return _sides('CampP9d', s1={'playerAllies': ''})


    MISSION = {'engine_scripts9': mission,
               'engine_scripts9b': lambda: mission('CampP9b', foe='s4', moved={'Tgt': 's5', 'Tg2': 's5'}),
               'engine_scripts9c': lambda: mission('CampP9c', foe='s2', moved={'Tgt': 's6', 'Tg2': 's6'}),
               'engine_scripts9d': _no_allies,
               'engine_scripts9e': lambda: _sides('CampP9e', **{s: {'playerAllies': ''} for s in ('s1', 's2', 's3')}),
               'engine_scripts9f': lambda: _sides('CampP9f', **{s: {'aiPersonality': 'AIPersonalityDefinition:DefaultPersonality'}
                                                              for s in ('s2', 's3')}),
               'engine_scripts9g': lambda: _sides('CampP9g', **{s: {'playerAllies': '', 'aiPersonality':
                                                                  'AIPersonalityDefinition:DefaultPersonality'}
                                                              for s in ('s1', 's2', 's3')}),
               'engine_scripts9h': lambda: mission('CampP9h', foe='s3', moved={'Tgt': 's6', 'Tg2': 's6'}),
               'engine_scripts9i': lambda: mission('CampP9i', map=_libraries({'Soviet_1': 'none'})),
               'engine_scripts9j': lambda: mission('CampP9j', foe='s4', moved={'Tgt': 's5', 'Tg2': 's5'},
                                                   map=_libraries({'Soviet_4': 'skirmish', 'Soviet_5': 'skirmish'}))}
    CHECKS = {'engine_scripts9': {'memb': memb, 'memb2': memb2, 'memb3': memb3,
                                'owner': owner},
              'engine_scripts9b': {'memb4': memb4, 'rel': rel, 'rmv': lambda m: rel(m, remove=True), 'atk': atk,
                                   'ral': lambda m: rel(m, p1="<1st Human Player's Allies incl Self>"),
                                   'ra1': lambda m: rel(m, p1='<1st Human Player>'),
                                   'atkr': atkr},
              'engine_scripts9c': {'memb5': memb5}, 'engine_scripts9d': {'memb6': memb6},
              'engine_scripts9e': {'memb7': memb7}, 'engine_scripts9f': {'memb8': memb8},
              'engine_scripts9g': {'memb9': memb9}, 'engine_scripts9h': {'memb10': memb10},
              'engine_scripts9i': {'memb11': memb11}, 'engine_scripts9j': {'memb12': memb12}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_seqstop():
    """Stop a unit's sequential queue during a move, with an untouched control.

    Predict: both start at 1; stop removes +10 and the separately queued +100,
    but the current move still reaches the destination (mask 3). At 20 seconds
    a new +1000 script on the stopped unit distinguishes clearing from disabling.
    Read counters plus logic frame; evidence: work/re/c_seqstop_report.md.
    MEASURED A: f43 1/1/0/43; f242 both at destination (mask 3);
    f282 111/1/3/282; f308 111/1001/3/308; f360 111/1001/3/360.
    Only the script queue boundary is measured; exact movement/idle timing,
    self-stop, loops, dead/missing units and non-move orders remain gaps.

    engine_seqteam:t -- TEAM_EXECUTE / TEAM_STOP_SEQUENTIAL_SCRIPT (d115 14, A288 read of the handlers: the record on the
    team, a group of its members made at the call; a step waits till the group is idle). Three two-tank crews, at 1 s:
      W: [+1, MOVE_NAMED_UNIT_TO(w1, WF 600 east), +10, ATTACK_MOVE_TEAM_TO(<This Team>, W2), +100], then [+1000] queued.
      S: [+1, MOVE_NAMED_UNIT_TO(s1, SF 600 east), +10] and [+100] queued; TEAM_STOP_SEQUENTIAL_SCRIPT(S) at 2 s, [+1000]
         given at 20 s.  L: [+1, MOVE_NAMED_UNIT_TO(l1, LF 900 east), +10]; NAMED_KILL(l1) at 3 s.
      走 / 停 = W's / S's counters; 位 = 1 w1 in WF, 2 w1 in W2, 4 w2 in W2, 8 s1 in SF, 16 / 32 L's counter >= 1 / 11.
      [simulator, the group idle = every living member idle: 走 1 -> 11 once w1 is at WF (~7 s; not at once, w2 being
      idle) -> 111, 1111 once both are at W2 (~16 s); 位 1 -> 6; 停 1 -> 1001 at 20 s, s1 still at SF (8); L 1 -> 11 at
      the kill (the dead member out of the group: 位 16 -> 48)]

    engine_seqguard:g -- TEAM_FACE_WAYPOINT / TEAM_GUARD_FOR_SECONDS as retail j04 writes them in a team's sequential script
    (A298 read of the handlers: the team face is NAMED_FACE_WAYPOINT on each member with an AI; the team guard is the team
    idle's handler -- each member's order dropped, the team's record waits n x 15 frames). Two two-tank crews and a tank:
      G: [+1, TEAM_FACE_WAYPOINT(<This Team>, N), +10, TEAM_GUARD_FOR_SECONDS(<This Team>, 6), +100,
          MOVE_TEAM_TO(<This Team>, GF 600 east), +1000];  K: the same with TEAM_IDLE_FOR_SECONDS 6 (the same handler);
      I: UNIT_EXECUTE_SEQUENTIAL_SCRIPT [+1, UNIT_IDLE_FOR_SECONDS(<This Object>, 5), +10] -- 5 an integer (engine_acts2's
         5.0 went into the argument's float slot; the handler reads the integer one).
      守帧 / 闲帧 / 单帧 = frames with G == 11 / K == 11 / I == 1 (the wait); 位 = 1 G >= 111, 2 K >= 111, 4 I >= 11,
      8 g1 in GF, 16 k1 in KF.
    """
    from maps import probe_border
    from parts import Mission, Script, Test, square
    from checks import engine_scripts8 as s8


    def mission():
        m = Mission(name='CampSeqStop', map=probe_border, units=[], facts={})
        for k, role in enumerate(('control', 'stopped')):
            m.put('AlliedAntiVehicleVehicleTech1', 'stop row', 0., -1000. - k*400.,
                  name='CNV SeqStop '+role, role=role, angle=0.)
            m.waypoint(role, 'CNV SeqStop Goal '+role, 'stop row', 1300., -1000. - k*400.)
        return m


    def check(m):
        t = Test()
        s8.at(t, 'seqstop start', 1., [
            (action, m.role(role).name, script)
            for role in ('control', 'stopped')
            for action, script in [('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', 'Test SeqStop '+role),
                                   ('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', 'Test SeqStop Queue '+role)]])
        for role, label in (('control', '继续'), ('stopped', '停止')):
            c = 'CNV_SeqStop_'+role
            t.counters.append((c, label))
            t.scripts += [Script('Test SeqStop '+role, [], [
                ('INCREMENT_COUNTER', 1, c),
                ('MOVE_NAMED_UNIT_TO', '<This Object>', m.mark(role)),
                ('INCREMENT_COUNTER', 10, c)], sub=True),
                Script('Test SeqStop Queue '+role, [], [('INCREMENT_COUNTER', 100, c)], sub=True)]
            t.areas['SeqStop '+role] = square(*m.point(role), 100.)
        s8.at(t, 'seqstop stop', 2., [('UNIT_STOP_SEQUENTIAL_SCRIPT', m.role('stopped').name)])
        t.scripts.append(Script('Test SeqStop Fresh', [], [
            ('INCREMENT_COUNTER', 1000, 'CNV_SeqStop_stopped')], sub=True))
        s8.at(t, 'seqstop fresh', 20., [('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', m.role('stopped').name,
                                       'Test SeqStop Fresh')])
        s8.total(t, 'CNV_SeqStop_Where', '到达', [
            (2**k, ('NAMED_INSIDE_AREA', m.role(role).name, 'SeqStop '+role))
            for k, role in enumerate(('control', 'stopped'))])
        s8.frames(t, 'CNV_SeqStop_Clock', '逻辑帧', [])
        s8.watch(t, 27., .5)
        return t


    TEAM = {k: ((600., y), (600., y + 120.), x) for k, y, x in (('W', 4100., 1200.), ('S', 4400., 1200.),
                                                                ('L', 4700., 1500.))}
    W2 = (1500., 4160.)


    def team_mission():
        m = Mission(name='CampSeqTeam', map=probe_border, units=[], facts={})
        o = probe_border.SITES['stop row']
        for k, (a, b, fx) in TEAM.items():
            for i, (x, y) in enumerate((a, b), 1):
                m.put('AlliedAntiVehicleVehicleTech1', 'stop row', x - o.x, y - o.y, name=f'CNV SeqTeam {k}{i}',
                      role=f'{k}{i}', angle=0., props={'originalOwner': m.crew(k)})
            m.waypoint(k, f'CNV SeqTeam {k} Goal', 'stop row', fx - o.x, a[1] - o.y)
        m.waypoint('W2', 'CNV SeqTeam W2', 'stop row', W2[0] - o.x, W2[1] - o.y)
        return m


    def team(m):
        t = Test()
        c = {k: 'CNV_SeqTeam_' + k for k in TEAM}
        go = {k: [('INCREMENT_COUNTER', 1, c[k]), ('MOVE_NAMED_UNIT_TO', m.role(k + '1').name, m.mark(k)),
                  ('INCREMENT_COUNTER', 10, c[k])] for k in TEAM}
        go['W'] += [('ATTACK_MOVE_TEAM_TO', '<This Team>', m.mark('W2')), ('INCREMENT_COUNTER', 100, c['W'])]
        later = {'W': 1000, 'S': 100}
        t.scripts += [Script(f'Test SeqTeam {k}', [], acts, sub=True) for k, acts in go.items()]
        t.scripts += [Script(f'Test SeqTeam {k} Q', [], [('INCREMENT_COUNTER', n, c[k])], sub=True)
                      for k, n in later.items()]
        t.scripts.append(Script('Test SeqTeam Fresh', [], [('INCREMENT_COUNTER', 1000, c['S'])], sub=True))
        s8.at(t, 'seqteam go', 1., [('TEAM_EXECUTE_SEQUENTIAL_SCRIPT', m.crew(k), f'Test SeqTeam {k}') for k in TEAM] +
              [('TEAM_EXECUTE_SEQUENTIAL_SCRIPT', m.crew(k), f'Test SeqTeam {k} Q') for k in later])
        s8.at(t, 'seqteam stop', 2., [('TEAM_STOP_SEQUENTIAL_SCRIPT', m.crew('S'))])
        s8.at(t, 'seqteam kill', 3., [('NAMED_KILL', m.role('L1').name)])
        s8.at(t, 'seqteam fresh', 20., [('TEAM_EXECUTE_SEQUENTIAL_SCRIPT', m.crew('S'), 'Test SeqTeam Fresh')])
        t.counters += [(c['W'], '走'), (c['S'], '停')]
        for k, r in (('W', 80.), ('W2', 150.), ('S', 80.)):
            t.areas['SeqTeam ' + k] = square(*m.point(k), r)
        s8.total(t, 'CNV_SeqTeam_Where', '位', [
            (1, ('NAMED_INSIDE_AREA', m.role('W1').name, 'SeqTeam W')),
            (2, ('NAMED_INSIDE_AREA', m.role('W1').name, 'SeqTeam W2')),
            (4, ('NAMED_INSIDE_AREA', m.role('W2').name, 'SeqTeam W2')),
            (8, ('NAMED_INSIDE_AREA', m.role('S1').name, 'SeqTeam S')),
            (16, ('COUNTER', c['L'], 3, 1)), (32, ('COUNTER', c['L'], 3, 11))])
        s8.frames(t, 'CNV_SeqTeam_Clock', '逻辑帧', [])
        s8.watch(t, 24.)
        return t


    GUARD = {'G': 4100., 'K': 4400.}


    def guard_mission():
        m = Mission(name='CampSeqGuard', map=probe_border, units=[], facts={})
        o = probe_border.SITES['stop row']
        rows = [(k + str(i), k, 600., y + 120. * (i - 1)) for k, y in GUARD.items() for i in (1, 2)] + [('I1', 'I', 600., 4700.)]
        for role, k, x, y in rows:
            m.put('AlliedAntiVehicleVehicleTech1', 'stop row', x - o.x, y - o.y, name=f'CNV SeqGuard {role}', role=role,
                  angle=0., props={'originalOwner': m.crew(k)})
        for k, y in GUARD.items():
            m.waypoint(k, f'CNV SeqGuard {k} Goal', 'stop row', 1200. - o.x, y - o.y)
        m.waypoint('W', 'CNV SeqGuard West', 'stop row', 200. - o.x, 4160. - o.y)    # G's back: a half turn and back
        return m


    def guard(m):
        t = Test()
        c = {k: 'CNV_SeqGuard_' + k for k in ('G', 'K', 'I')}
        wait = {'G': 'TEAM_GUARD_FOR_SECONDS', 'K': 'TEAM_IDLE_FOR_SECONDS'}
        t.scripts += [Script(f'Test SeqGuard {k}', [], [
            ('INCREMENT_COUNTER', 1, c[k])] + [('TEAM_FACE_WAYPOINT', '<This Team>', m.mark('W'))] * (k == 'G') + [
            ('INCREMENT_COUNTER', 10, c[k]), (w, '<This Team>', 6), ('INCREMENT_COUNTER', 100, c[k]),
            ('MOVE_TEAM_TO', '<This Team>', m.mark(k)), ('INCREMENT_COUNTER', 1000, c[k])], sub=True)
            for k, w in wait.items()]
        t.scripts.append(Script('Test SeqGuard I', [], [
            ('INCREMENT_COUNTER', 1, c['I']), ('UNIT_IDLE_FOR_SECONDS', '<This Object>', 5),
            ('INCREMENT_COUNTER', 10, c['I'])], sub=True))
        s8.at(t, 'seqguard go', 1., [('TEAM_EXECUTE_SEQUENTIAL_SCRIPT', m.crew(k), f'Test SeqGuard {k}') for k in wait] +
              [('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', m.role('I1').name, 'Test SeqGuard I')])
        def tally(counter, label, parts):       # the frames each (weight, crew, step) holds, weighted: four lines fit
            t.counters.append((counter, label))
            t.scripts.extend(Script(f'Test - {counter} {k}{n}', [('COUNTER', c[k], 2, n)],
                                    [('INCREMENT_COUNTER', w, counter)], once=False) for w, k, n in parts)
        tally('CNV_SeqGuard_W', '守闲帧', [(1, 'G', 11), (1000, 'K', 11)])
        s8.frames(t, 'CNV_SeqGuard_IW', '单帧', [('COUNTER', c['I'], 2, 1)])
        for k in GUARD:
            t.areas['SeqGuard ' + k] = square(*m.point(k), 80.)
        s8.total(t, 'CNV_SeqGuard_Where', '位', [
            (1, ('COUNTER', c['G'], 3, 111)), (2, ('COUNTER', c['K'], 3, 111)), (4, ('COUNTER', c['I'], 3, 11)),
            (8, ('NAMED_INSIDE_AREA', m.role('G1').name, 'SeqGuard G')),
            (16, ('NAMED_INSIDE_AREA', m.role('K1').name, 'SeqGuard K'))])
        tally('CNV_SeqGuard_M', '行帧', [(1, 'G', 111), (1000, 'K', 111)])     # G faced west first, K did not
        s8.watch(t, 20., .5)
        return t


    MISSION = {'engine_seqstop': mission, 'engine_seqteam': team_mission, 'engine_seqguard': guard_mission}
    CHECKS = {'engine_seqstop': {'a': check}, 'engine_seqteam': {'t': team}, 'engine_seqguard': {'g': guard}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_statusbits():
    """Engine unit test: status-bits upgrade module -- an upgrade the unit gets sets an ObjectStatus bit (engine line C round 10;
    docs/engine/weaponset.md). Retail: the 30-odd unit templates carry the status-bits upgrade module (`StatusToSet=WEAPON_UPGRADED_0x`
    `TriggeredBy Upgrade_Veterancy_HEROIC`) (mirage tank / conscript: _01, guardian: _02); the weapon sets then choose by that
    bit (engine_weaponset). The simulator has the code (`simunits.status_bits`: the held upgrades' bits; INFERRED, never
    read on the bench) and the probe asks four things: does the script's NAMED_RECEIVE_UPGRADE of the veterancy upgrade
    set the bit, does it change the fire, does a late grant do the same from then on, does NAMED_REMOVE_UPGRADE take it back.

    On the range probe map, one lane each (the lane names are the map's; the units are the probe's):
      base     mirage tank   no upgrade                                      (control)
      high     mirage tank   Upgrade_Veterancy_HEROIC at s0                  (_01 set: the Veteran cannon)
      order    mirage tank   Upgrade_Veterancy_HEROIC at LATE (8 s)          (the bit set in the middle of the fight)
      removed  mirage tank   HEROIC at s0, NAMED_REMOVE_UPGRADE at LATE      (is the bit cleared again?)
      switch   conscript     HEROIC at s0                                    (_01 set, nothing chooses by it: status only)
      low      guardian      HEROIC at s0                                    (_02 set, not _01: status only)
    Each attacker is told at ORDER (3 s) to attack a Tsunami tank 100 north of it (the enemy's, NO_ATTACK, never answers).

    Counters: a: 基准血 / 英雄血 / 晚血 / 去血 (the Tsunami's health in percent, base / high / order / removed lane, every
    second); b: 英雄位 / 晚位 / 去位 -- 1 while the lane's mirage tank (high / order / removed) reads WEAPON_UPGRADED_01 via
    UNIT_HAS_OBJECT_STATUS, else 0; 兵守位 = 1 x (conscript reads _01) + 10 x (guardian reads _02) + 100 x (guardian reads
    _01, the wrong bit: should stay 0). Sampled every 0.5 s.

    Bench 2026-11-09 (docs/engine/weaponset.md; StatusBitsUpgrade registered): b s1-s6 = 1 0 1 11, s7-s41 = 1 1 0 11 (the grant
    sets the bit, a late grant sets it from then on, a removal clears it; the conscript reads _01, the guardian _02 and not
    _01) -- as the simulator predicted. a = 47 34 47 34 from s1 on (the mirage tank's one shot: 200 / 250 of 380 hp, then
    no more; the late grant came after the fight had stopped, so it changes nothing).
    """
    from maps import probe_range
    from parts import Mission, Script, Test, counted, status

    CONSCRIPT, MIRAGE, GUARD, TANK = ('SovietAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech3',
                                      'AlliedAntiVehicleVehicleTech1', 'JapanAntiVehicleVehicleTech1')
    LANES = {'base': MIRAGE, 'high': MIRAGE, 'order': MIRAGE, 'removed': MIRAGE, 'switch': CONSCRIPT, 'low': GUARD}
    HEROIC = 'Upgrade_Veterancy_HEROIC'
    BIT = {'high': 'WEAPON_UPGRADED_01', 'order': 'WEAPON_UPGRADED_01', 'removed': 'WEAPON_UPGRADED_01',
           'switch': 'WEAPON_UPGRADED_01', 'low': 'WEAPON_UPGRADED_02'}
    ORDER, LATE, RUN = 3.0, 8.0, 40.0


    def _n(lane, part):
        return f'UNIT - CNV Sbits {lane.title()} {part}'


    def mission():
        m = Mission(name='CampSbits', map=probe_range, units=[], facts={})
        for lane, tpl in LANES.items():
            m.put(tpl, f'{lane} gun', side='p1', role=f'{lane} attacker', name=_n(lane, 'Man'))
            m.put(TANK, f'{lane} gun', 0.0, 100.0, side='s1', role=f'{lane} tank', name=_n(lane, 'Tank'))
        return m


    def statusbits_test(m, which='a'):
        t = Test()
        p1 = m.player('p1')
        tanks = [_n(lane, 'Tank') for lane in LANES]
        early = [lane for lane in LANES if lane not in ('base', 'order')]
        t.scripts.append(Script('Test - start', [], [('UNIT_CHANGE_OBJECT_STATUS', u, 'NO_ATTACK', 1) for u in tanks] + [
            ('NAMED_RECEIVE_UPGRADE', HEROIC, _n(lane, 'Man')) for lane in early] + [
            ('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Order', ORDER),
            ('SET_MILLISECOND_TIMER', 'Test Late', LATE)]))
        t.scripts += [
            Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                   [('NAMED_ATTACK_NAMED', _n(lane, 'Man'), _n(lane, 'Tank')) for lane in LANES]),
            Script('Test - late', [('TIMER_EXPIRED', 'Test Late')],
                   [('NAMED_RECEIVE_UPGRADE', HEROIC, _n('order', 'Man')),
                    ('NAMED_REMOVE_UPGRADE', HEROIC, _n('removed', 'Man'))])]
        if which == 'a':
            for key, label in (('Base', '基准血'), ('High', '英雄血'), ('Order', '晚血'), ('Removed', '去血')):
                counted(f'CNV_Sbits_{key}Hp', label, t, health=_n(key, 'Tank'))
            t.expect = [('基准血', 0, 'ever<=', 99, RUN)]
        else:
            for key, label in (('High', '英雄位'), ('Order', '晚位'), ('Removed', '去位')):
                c = f'CNV_Sbits_{key}Bit'
                t.counters.append((c, label))
                t.scripts += [
                    Script(f'Test - bit {key} zero', [], [('SET_COUNTER', c, 0)], once=False),
                    Script(f'Test - bit {key} seen', [('UNIT_HAS_OBJECT_STATUS', _n(key, 'Man'), status(BIT[key.lower()]))],
                           [('SET_COUNTER', c, 1)], once=False)]
            t.counters.append(('CNV_Sbits_Other', '兵守位'))
            t.scripts += [Script('Test - bit other zero', [], [('SET_COUNTER', 'CNV_Sbits_Other', 0)], once=False)] + [
                Script(f'Test - bit other {k}', [('UNIT_HAS_OBJECT_STATUS', _n(lane, 'Man'), status(bit))],
                       [('INCREMENT_COUNTER', step, 'CNV_Sbits_Other')], once=False)
                for k, (lane, bit, step) in enumerate((('switch', 'WEAPON_UPGRADED_01', 1), ('low', 'WEAPON_UPGRADED_02', 10),
                                                       ('low', 'WEAPON_UPGRADED_01', 100)))]
            t.expect = [('英雄位', 0, 'ever>=', 0, RUN)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=0.5, sheet=False, lines=len(t.counters)))]
        return t


    # engine_kingbits:k (A309): retail j03 / j08 set WEAPON_UPGRADED_01 / 02 / 03 together on a JapanMechaKing at the start.
    # Its three katana slots name no status bit (SDK), so the data says: no effect. Two lanes: the 'high' King gets the
    # three bits, the 'base' King none; each is told at ORDER to attack a NO_ATTACK s1 King 120 north (10 000 hp, the
    # katana 5 000 / radius 100: several cuts). 设血 / 平血 = the two targets' health in percent; 位 = 1 x _01 + 10 x _02 +
    # 100 x _03 read back on the high King. Review xx #6 (A313): the 'order' lane's King (no bits) is never told; 令血 = its
    # target's health in percent (does the King cut on its own before ORDER?). BENCH 11-22 CampKbitsK_mcp_1122_183003: it
    # does, as the told ones from s1 (75 50 25 0): the order adds nothing.
    KING = 'JapanMechaKing'
    KBITS = ('WEAPON_UPGRADED_01', 'WEAPON_UPGRADED_02', 'WEAPON_UPGRADED_03')


    def king_mission():
        m = Mission(name='CampKbits', map=probe_range, units=[], facts={})
        for lane in ('high', 'base', 'order'):
            m.put(KING, f'{lane} gun', side='p1', role=f'{lane} king', name=_n(lane, 'King'))
            m.put(KING, f'{lane} gun', 0.0, 120.0, side='s1', role=f'{lane} king target', name=_n(lane, 'Prey'))
        return m


    def king_test(m):
        t = Test()
        t.scripts.append(Script('Test - start', [], [
            ('UNIT_CHANGE_OBJECT_STATUS', _n(lane, 'Prey'), 'NO_ATTACK', 1) for lane in ('high', 'base', 'order')] + [
            ('UNIT_CHANGE_OBJECT_STATUS', _n('high', 'King'), bit, 1) for bit in KBITS] + [
            ('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [('NAMED_ATTACK_NAMED', _n(lane, 'King'), _n(lane, 'Prey')) for lane in ('high', 'base')]))
        for lane, label in (('high', '设血'), ('base', '平血'), ('order', '令血')):
            counted(f'CNV_Kbits_{lane}', label, t, health=_n(lane, 'Prey'))
        t.counters.append(('CNV_Kbits_Bits', '位'))
        t.scripts += [Script('Test - kbits zero', [], [('SET_COUNTER', 'CNV_Kbits_Bits', 0)], once=False)] + [
            Script(f'Test - kbits {k}', [('UNIT_HAS_OBJECT_STATUS', _n('high', 'King'), status(bit))],
                   [('INCREMENT_COUNTER', 10 ** k, 'CNV_Kbits_Bits')], once=False) for k, bit in enumerate(KBITS)]
        t.expect = [('设血', 0, 'ever<=', 99, 20.0)]
        t.bench = [('bench_watch', dict(seconds=20.0, every=0.5, sheet=False, lines=len(t.counters)))]
        return t


    # engine_statusbits:n (A310): retail a08 sets NO_AUTO_ACQUIRE on its Mirage Tank at the start. Same lanes, no upgrade:
    # base's Mirage plain, high's and order's given the bit at s0; only order's is told at ORDER to attack its Tsunami.
    # 基准血 / 不找血 / 令血 = the three Tsunamis' health in percent; 位 = high's Mirage reads the bit. c (A327): removed's Mirage
    # gets CAN_ATTACK 0 at s0 too (a06 clears it on a Rushmore head, which has no weapon), never told; counters 基准血 /
    # 无攻血 (its Tsunami's health) / 攻位 = 1 x (base's Mirage reads CAN_ATTACK) + 10 x (removed's does).
    def acquire_test(m, which='n'):
        t = Test()
        t.scripts.append(Script('Test - start', [], [
            ('UNIT_CHANGE_OBJECT_STATUS', _n(lane, 'Tank'), 'NO_ATTACK', 1) for lane in LANES] + [
            ('UNIT_CHANGE_OBJECT_STATUS', _n(lane, 'Man'), 'NO_AUTO_ACQUIRE', 1) for lane in ('high', 'order')] + [
            ('UNIT_CHANGE_OBJECT_STATUS', _n('removed', 'Man'), 'CAN_ATTACK', 0)][:which == 'c'] + [
            ('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                                [('NAMED_ATTACK_NAMED', _n('order', 'Man'), _n('order', 'Tank'))]))
        lanes = (('base', '基准血'), ('high', '不找血'), ('order', '令血')) if which == 'n' else (('base', '基准血'), ('removed', '无攻血'))
        for lane, label in lanes:
            counted(f'CNV_Sbits_A{lane}', label, t, health=_n(lane, 'Tank'))
        t.counters.append(('CNV_Sbits_ABit', '位') if which == 'n' else ('CNV_Sbits_CBit', '攻位'))
        t.scripts += [Script('Test - abit zero', [], [('SET_COUNTER', 'CNV_Sbits_ABit', 0)], once=False),
                      Script('Test - abit seen', [('UNIT_HAS_OBJECT_STATUS', _n('high', 'Man'), status('NO_AUTO_ACQUIRE'))],
                             [('SET_COUNTER', 'CNV_Sbits_ABit', 1)], once=False)]
        if which == 'c':
            t.scripts += [Script('Test - cbit zero', [], [('SET_COUNTER', 'CNV_Sbits_CBit', 0)], once=False)] + [
                Script(f'Test - cbit {lane}', [('UNIT_HAS_OBJECT_STATUS', _n(lane, 'Man'), status('CAN_ATTACK'))],
                       [('INCREMENT_COUNTER', step, 'CNV_Sbits_CBit')], once=False) for lane, step in (('base', 1), ('removed', 10))]
        t.expect = [('基准血', 0, 'ever<=', 99, 15.0)]
        t.bench = [('bench_watch', dict(seconds=15.0, every=0.5, sheet=False, lines=len(t.counters)))]
        return t


    MISSION = {'engine_statusbits': mission, 'engine_kingbits': king_mission}
    CHECKS = {'engine_statusbits': {'a': statusbits_test, 'b': lambda m: statusbits_test(m, 'b'), 'n': acquire_test,
                                    'c': lambda m: acquire_test(m, 'c')},
              'engine_kingbits': {'k': king_test}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_team():
    """Engine unit test: a whole-team order to a team nobody has used yet (E3).

    Bench 2026-11-04: an order to a team with nobody on it yet is not kept for a unit put on it afterwards (early); a unit
    put on the team and the order in the same script go together (fresh); a team never used reads neither destroyed nor
    having units, with its one member it has units, and once that member is deleted it reads destroyed (ghost). So
    TEAM_DESTROYED of a team that never had anyone stays false. Three guardians stand on the player's default team in the west field, `far` 600 north of them
    (the team bench's leg, land all the way); each team below is a fresh one (Mission.crew), used only as written:
      early (tank 1): MOVE_TEAM_TO at 1 s, tank 1 put on the team at 3 s, no order after -- does tank 1 ever go?
      fresh (tank 2): tank 2 put on the team and the team ordered in one script at 1 s (what Mission.order writes) --
        tank 2 goes;
      ghost: TEAM_DESTROYED and TEAM_HAS_UNITS read every frame; tank 3 put on it at GHOST_AT s and deleted 4 s later --
        what the two read never used, with a member, and emptied.
    """
    from maps import island
    from parts import Mission, Script, Test, counted, square

    GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
    GHOST_AT, RUN = 6.0, 40.0
    FAR = 'Test Far Area'


    def mission():
        m = Mission(name='CampTeamE', map=island, facts={})
        for k, dy in enumerate((-60, 0, 60), 1):
            m.put(GUARDIAN, 'west field', dy, -300, name=f'UNIT - CNV Fresh Tank {k}', role=f'tank {k}', angle=0.0)
        m.waypoint('far', 'CNV Fresh Far', 'west field', 0, 300)
        for key in ('Early', 'Fresh', 'Ghost'):
            m.crew(key)
        return m


    def fresh(m):
        t = Test()
        early, fresh_, ghost = (m.teams[key] for key in ('Early', 'Fresh', 'Ghost'))
        tank = {k: m.role(f'tank {k}').name for k in (1, 2, 3)}
        t.areas[FAR] = square(*m.point('far'), 60.0)
        t.scripts += [
            Script('Test - start', [], [('SET_MILLISECOND_TIMER', 'Test Order', 1.0), ('SET_MILLISECOND_TIMER', 'Test Join', 3.0),
                                        ('SET_MILLISECOND_TIMER', 'Test Ghost', GHOST_AT)]),
            Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                   [('MOVE_TEAM_TO', early, m.mark('far')),
                    ('UNIT_SET_TEAM', tank[2], fresh_), ('MOVE_TEAM_TO', fresh_, m.mark('far'))]),
            Script('Test - join', [('TIMER_EXPIRED', 'Test Join')], [('UNIT_SET_TEAM', tank[1], early)]),
            Script('Test - ghost', [('TIMER_EXPIRED', 'Test Ghost')], [('UNIT_SET_TEAM', tank[3], ghost),
                                                                       ('SET_MILLISECOND_TIMER', 'Test Ghost Out', 4.0)]),
            Script('Test - ghost out', [('TIMER_EXPIRED', 'Test Ghost Out')], [('NAMED_DELETE', tank[3])])]
        counted('CNV_Fresh_Early', '早令车到终点', t, named=tank[1], area=FAR)
        counted('CNV_Fresh_Fresh', '同令车到终点', t, named=tank[2], area=FAR)
        for counter, label, cond in (('CNV_Fresh_Gone', '空队算全灭', 'TEAM_DESTROYED'),
                                     ('CNV_Fresh_Has', '空队有人', 'TEAM_HAS_UNITS')):
            t.counters.append((counter, label))
            t.scripts += [Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False),
                          Script(f'Test - {counter}', [(cond, ghost)], [('SET_COUNTER', counter, 1)], once=False)]
        t.expect += [('早令车到终点', 0, '==', 0), ('同令车到终点', 0, 'ever==', 1),
                     ('空队有人', 0, '==', 0, GHOST_AT - 1), ('空队算全灭', 0, '==', 0, GHOST_AT + 3),
                     ('空队有人', GHOST_AT, '==', 1, GHOST_AT + 3),
                     ('空队有人', GHOST_AT + 5, '==', 0), ('空队算全灭', GHOST_AT + 5, '==', 1)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=len(t.counters)))]
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_team': mission}
    CHECKS = {'engine_team': {'fresh': fresh}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def team():
    """K6 team probe (benches/script/control/scenes.py#team): what the engine does with a map's own team that a script orders as one. The
    convoy trucks are ordered to `far` by MOVE_TEAM_TO only (never by name); counters read who got there.

    Bench 2026-11-04 (K6 go): a placed unit joins the team and the order reaches every member; a member made after the
    order does NOT follow it (once: late 0) but the next order does (tick: late 1); the survivors of a killed member both
    move (tick: 2 of 2); with every member dead the team reads 0 members, no units, TEAM_DESTROYED, and a unit made on it
    afterwards is a member again and takes the next order (dead).

    once: one order at 1 s, nothing after. Placed trucks 1-3 are on the team: do all three go? Late 1 is made on the team
      at 8 s, after the order: does it go too? Counters: trucks in `far`, late 1 in `far`, team members, team has units.
    tick: the order again every 3 s (the convoy's tick); late 1 made at 8 s; truck 1 killed at 12 s. The survivors (trucks
      2, 3) and late 1: all in `far`?
    dead: the order every 3 s; all three trucks killed at 10 s, a late member made at 16 s. Members and HasUnits while the
      team is empty, TEAM_DESTROYED, and whether the member made after it went.
    """
    from parts import Script, Test, square

    LATE_AT, KILL_AT = 8.0, 12.0
    FAR = 'Test Far Area'
    LABELS = ('在终点的车', '后来的车到终点', '队里几个', '队里有人吗')


    def _sum(t, counter, names):
        """counter = how many of `names` are inside FAR (zeroed and counted every frame)."""
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        t.scripts += [Script(f'Test - {counter} {k}', [('NAMED_INSIDE_AREA', n, FAR)], [('INCREMENT_COUNTER', 1, counter)],
                             once=False) for k, n in enumerate(names)]


    def _team_counters(t, team, members, has):
        t.scripts += [Script(f'Test - {members} {n}', [('TEAM_COMPARE_NUM_MEMBERS', team, 2, n)],
                             [('SET_COUNTER', members, n)], once=False) for n in range(6)]
        t.scripts += [Script(f'Test - {has} zero', [], [('SET_COUNTER', has, 0)], once=False),
                      Script(f'Test - {has} one', [('TEAM_HAS_UNITS', team)], [('SET_COUNTER', has, 1)], once=False)]


    def _setup(m, t, tick, order=None):
        team = m.teams.get('Probe')
        order = order or [('MOVE_TEAM_TO', team, m.mark('far'))]
        t.areas[FAR] = square(*m.point('far'), 60.0)
        t.scripts.append(Script('Test - order start', [], [('SET_MILLISECOND_TIMER', 'Test Order Timer', 1.0),
                                                           ('SET_MILLISECOND_TIMER', 'Test Late Timer', LATE_AT)]))
        if tick:
            t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order Timer')],
                                    order + [('SET_MILLISECOND_TIMER', 'Test Order Timer', 3.0)],
                                    once=False))
        else:
            t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order Timer')],
                                    order))
        return team


    def _late(m, t, team, at_timer, name='UNIT - CNV Probe Late 1'):
        t.scripts.append(Script('Test - late', [('TIMER_EXPIRED', at_timer)],
                                [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION', name, m.role('truck 1').template,
                                  team, m.mark('late'), 0.0)]))
        return name


    def once(m):
        t = Test()
        team = _setup(m, t, tick=False)
        late = _late(m, t, team, 'Test Late Timer')
        names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
        _sum(t, 'Test Far', names)
        _sum(t, 'Test Late', [late])
        _team_counters(t, team, 'Test Members', 'Test Has')
        t.counters += list(zip(('Test Far', 'Test Late', 'Test Members', 'Test Has'), LABELS))
        t.expect += [(LABELS[0], 0, 'ever==', 3), (LABELS[1], 0, '==', 0)]      # a member made after the order does not follow
        t.bench = [('bench_watch', dict(seconds=60, every=4, sheet=False, lines=4))]
        return t


    def tick(m):
        t = Test()
        team = _setup(m, t, tick=True)
        late = _late(m, t, team, 'Test Late Timer')
        names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
        t.scripts += [Script('Test - kill start', [('TIMER_EXPIRED', 'Test Late Timer')],
                             [('SET_MILLISECOND_TIMER', 'Test Kill Timer', KILL_AT - LATE_AT)]),
                      Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill Timer')], [('NAMED_KILL', names[0])])]
        _sum(t, 'Test Far', names[1:])
        _sum(t, 'Test Late', [late])
        _team_counters(t, team, 'Test Members', 'Test Has')
        t.counters += list(zip(('Test Far', 'Test Late', 'Test Members', 'Test Has'), LABELS))
        t.expect += [(LABELS[0], 0, 'ever==', 2), (LABELS[1], 0, 'ever==', 1)]
        t.bench = [('bench_watch', dict(seconds=60, every=4, sheet=False, lines=4))]
        return t


    def dead(m):
        t = Test()
        team = _setup(m, t, tick=True)
        names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
        t.scripts += [Script('Test - kill timer', [], [('SET_MILLISECOND_TIMER', 'Test Kill Timer', 10.0),
                                                        ('SET_MILLISECOND_TIMER', 'Test Late Timer', 16.0)]),
                      Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill Timer')], [('NAMED_KILL', n) for n in names])]
        late = _late(m, t, team, 'Test Late Timer')
        _sum(t, 'Test Late', [late])
        _team_counters(t, team, 'Test Members', 'Test Has')
        t.scripts += [Script('Test - gone', [('TEAM_DESTROYED', team)], [('SET_COUNTER', 'Test Gone', 1)], once=False)]
        t.counters += list(zip(('Test Late', 'Test Members', 'Test Has', 'Test Gone'),
                               ('后来的车到终点', '队里几个', '队里有人吗', '队被判毁了')))
        t.expect += [('后来的车到终点', 0, 'ever==', 1), ('队里几个', 9, '==', 0, 15), ('队里几个', 17, '==', 1)]
        t.bench = [('bench_watch', dict(seconds=60, every=4, sheet=False, lines=4))]
        return t


    def _control(order):
        """The trucks ordered every 3 s by `order(m, team, names)`; counters as in once."""
        def check(m):
            t = Test()
            team = m.teams.get('Probe')
            names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
            _setup(m, t, tick=True, order=order(m, team, names))
            _sum(t, 'Test Far', names)
            t.counters += [('Test Far', LABELS[0])]
            if team:
                _team_counters(t, team, 'Test Members', 'Test Has')
                t.counters += [('Test Members', LABELS[2])]
            t.expect += [(LABELS[0], 0, 'ever==', 3)]
            t.bench = [('bench_watch', dict(seconds=45, every=4, sheet=False, lines=2))]
            return t
        return check


    # named: each truck by name (what A4 does today); attack: ATTACK_MOVE_TEAM_TO
    named =_control(lambda m, team, names: [('MOVE_NAMED_UNIT_TO', n, m.mark('far')) for n in names])
    attack = _control(lambda m, team, names: [('ATTACK_MOVE_TEAM_TO', team, m.mark('far'))])


    def join(m):
        """The exit's way in (ctx.order): units that were NOT placed on the team join it by UNIT_SET_TEAM in the same script
        that gives the whole-team order, every 3 s. Run on team_plain (the trucks on the player's default team). The order
        names late 1 too, which does not exist till 8 s (a name not made yet: no harm?) and is made then on the default
        team; truck 1 is killed at 12 s (a dead name: no harm?). Do the survivors and late 1 all reach `far`?"""
        t = Test()
        team = m.crew('Probe')
        late = 'UNIT - CNV Probe Late 1'
        names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
        _setup(m, t, tick=True, order=[('UNIT_SET_TEAM', n, team) for n in names + [late]] +
               [('MOVE_TEAM_TO', team, m.mark('far'))])
        t.scripts += [Script('Test - late', [('TIMER_EXPIRED', 'Test Late Timer')],
                             [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION', late, m.role('truck 1').template,
                               m.team('p1'), m.mark('late'), 0.0),
                              ('SET_MILLISECOND_TIMER', 'Test Kill Timer', KILL_AT - LATE_AT)]),
                      Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill Timer')], [('NAMED_KILL', names[0])])]
        _sum(t, 'Test Far', names[1:])
        _sum(t, 'Test Late', [late])
        t.counters += [('Test Far', LABELS[0]), ('Test Late', LABELS[1])]
        t.expect += [(LABELS[0], 0, 'ever==', 2), (LABELS[1], 0, 'ever==', 1)]
        t.bench = [('bench_watch', dict(seconds=60, every=4, sheet=False, lines=2))]
        return t


    def made(m):
        """A unit made on the team in the SAME script that gives the order, once, at 1 s (a plan's wave: create, then
        send). Run on team: truck 1-3 are placed on the team, late 1 is made with the order. Does late 1 go?"""
        t = Test()
        team = m.teams.get('Probe')
        late = 'UNIT - CNV Probe Late 1'
        names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
        _setup(m, t, tick=False, order=[('CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION', late, m.role('truck 1').template,
                                         team, m.mark('late'), 0.0), ('MOVE_TEAM_TO', team, m.mark('far'))])
        _sum(t, 'Test Far', names)
        _sum(t, 'Test Late', [late])
        t.counters += [('Test Far', LABELS[0]), ('Test Late', LABELS[1])]
        t.expect += [(LABELS[0], 0, 'ever==', 3), (LABELS[1], 0, 'ever==', 1)]
        t.bench = [('bench_watch', dict(seconds=45, every=4, sheet=False, lines=2))]
        return t


    def guard(m):
        """TEAM_GUARD_AREA (the area `far`) at 1 s: do all three go to the area and stay?"""
        t = Test()
        team = m.teams.get('Probe')
        names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
        _setup(m, t, tick=False, order=[('TEAM_GUARD_AREA', team, FAR)])
        _sum(t, 'Test Far', names)
        t.counters += [('Test Far', LABELS[0])]
        t.expect += [(LABELS[0], 0, 'ever==', 3)]
        t.bench = [('bench_watch', dict(seconds=45, every=4, sheet=False, lines=2))]
        return t


    def stop(m):
        """MOVE_TEAM_TO at 1 s, TEAM_STOP at 5 s (the trucks have gone about 125 of the 300 at speed 25): none may ever
        reach `far`."""
        t = Test()
        team = m.teams.get('Probe')
        names = [m.role(f'truck {k}').name for k in (1, 2, 3)]
        _setup(m, t, tick=False)
        t.scripts += [Script('Test - stop arm', [('TIMER_EXPIRED', 'Test Order Timer')],
                             [('SET_MILLISECOND_TIMER', 'Test Stop Timer', 4.0)]),
                      Script('Test - stop', [('TIMER_EXPIRED', 'Test Stop Timer')], [('TEAM_STOP', team)])]
        _sum(t, 'Test Far', names)
        t.counters += [('Test Far', LABELS[0])]
        t.expect += [(LABELS[0], 0, '==', 0)]
        t.bench = [('bench_watch', dict(seconds=45, every=4, sheet=False, lines=2))]
        return t


    CHECKS = {'team': {'once': once, 'tick': tick, 'dead': dead, 'named': named, 'attack': attack, 'made': made,
                       'guard': guard, 'stop': stop},
              'team_plain': {'named': named, 'join': join}}
    return dict(CHECKS=CHECKS)


def engine_timer():
    """Engine unit test: pausing and shifting the script timers -- STOP_TIMER, RESTART_TIMER, SUB_FROM_MSEC_TIMER --
    nothing on the map but scripts (as benches/script/control/checks.py#engine_script: festival, no facts).

    A timer shares the counters' table (engine_script out: a 2 s timer read as a counter shows 30, its frames left), so
    the counter lines show a timer's own frames left; the expired lines are live (cleared at the top of every frame by a
    repeating script, set again below it while TIMER_EXPIRED holds).

      stop   P (10 s at 0) stopped at 2 s, restarted at 5 s; E (2 s at 0) stopped at 4 s, after it ran out.
             Lines: 停表帧 P's frames left; 停表到 P expired (live); 过期停 E expired (live).
             [model (RA3-EngineModel scripts.py, Generals TCounter isCountdownTimer): P 150 -> ~120 at 2 s, holds there
             to 5 s, runs on, out ~3 s late (~13 s); a stopped timer is no countdown: TIMER_EXPIRED false even at 0 --
             过期停 1 from 2 s to 4 s, then 0; RESTART_TIMER only when frames are left]
      shift  S (10 s at 0) SUB_FROM_MSEC_TIMER 5 s at 2 s. Lines: 减帧 S's frames left; 减到 S expired (live).
             [model: S 150 -> ~120 at 2 s -> ~45, out at ~5 s; frames = ceil(seconds x 15)]. The ADD_TO_ twin is not
             in the catalog (mapscript.catalog: no retail map has it, so no ctype to write): not probed (named so here
             that inventory.benched does not take it for measured).

    读数 (bench 2026-11-10; the bench's seconds ~1 s ahead of the mission's)
      stop   CampTimerStop_mcp_1110_211657: 停表帧 120 s1-s3, 109 94 80 64 48 34 17 3 s4-s11, -1 from s12; 停表到 1 from
             s12; 过期停 1 s1-s2, 0 from s3. As the model: STOP_TIMER holds the frames, RESTART_TIMER runs them on, a
             stopped timer is not expired at -1. The simulator's readout had hidden running timers (0 while P ran): its
             lines now read the table (sim.py series, eng.value).
      shift  CampTimerShift_mcp_1110_211936: 减帧 32 17 3 s1-s3, -1 from s4; 减到 1 from s4 -- 75 frames off.
    Simulator after the fix: each reading 1-2 s later (tests/test_simbench.py test_timer_*).
    """
    from maps import festival
    from parts import Mission, Script, Test

    STEP = 'CNV_Tmr_'


    def mission():
        return Mission(name='CampTimer', map=festival, facts={})


    def _at(t, key, secs, actions):
        timer = f'{STEP}At_{key}'
        t.scripts += [Script(f'Tmr - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                      Script(f'Tmr - {key}', [('TIMER_EXPIRED', timer)], actions)]


    def _live(t, timer, counter, label):
        """counter 1 while TIMER_EXPIRED timer holds, 0 else (read at the frame's end)."""
        t.scripts += [Script(f'Tmr - {counter} clear', [], [('SET_COUNTER', counter, 0)], once=False),
                      Script(f'Tmr - {counter} set', [('TIMER_EXPIRED', timer)], [('SET_COUNTER', counter, 1)],
                             once=False)]
        t.counters.append((counter, label))


    def stop(m):
        t = Test()
        p, e = f'{STEP}P', f'{STEP}E'
        t.scripts.append(Script('Tmr - start', [], [('SET_MILLISECOND_TIMER', p, 10.0), ('SET_MILLISECOND_TIMER', e, 2.0)]))
        _at(t, 'stop p', 2.0, [('STOP_TIMER', p)])
        _at(t, 'stop e', 4.0, [('STOP_TIMER', e)])
        _at(t, 'restart p', 5.0, [('RESTART_TIMER', p)])
        t.counters.append((p, '停表帧'))
        _live(t, p, f'{STEP}POut', '停表到')
        _live(t, e, f'{STEP}EOut', '过期停')
        t.bench = [('bench_watch', dict(seconds=18, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def shift(m):
        t = Test()
        s = f'{STEP}S'
        t.scripts.append(Script('Tmr - start', [], [('SET_MILLISECOND_TIMER', s, 10.0)]))
        _at(t, 'sub s', 2.0, [('SUB_FROM_MSEC_TIMER', 5.0, s)])
        t.counters.append((s, '减帧'))
        _live(t, s, f'{STEP}SOut', '减到')
        t.bench = [('bench_watch', dict(seconds=12, every=1, sheet=False, lines=len(t.counters)))]
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_timer': mission}
    CHECKS = {'engine_timer': {'stop': stop, 'shift': shift}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


BENCHES = (
    engine_acts2, engine_acts5, engine_acts6, engine_acts7,
    engine_acts8, engine_acts9, engine_aichange, engine_aifav,
    engine_aiflip, engine_aistart, engine_aixfer, engine_basegate,
    engine_conds, drive, engine_killcount, engine_kind,
    engine_razed, engine_script, engine_scripts1, engine_scripts2,
    engine_scripts3, engine_scripts4, engine_scripts6, engine_scripts7,
    engine_scripts8, engine_scripts8b, engine_scripts9, engine_seqstop,
    engine_statusbits, engine_team, team, engine_timer,
)
