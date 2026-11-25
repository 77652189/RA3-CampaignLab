"""UI presentation checks, including the scenes defined with their probes."""


def engine_camera():
    """Engine unit test: where a ground point is drawn once the mission's MOVE_CAMERA_TO stands the camera on a point, when
    the ground around is not flat (engine line round 8: at A4's back lane V1 the engineer was drawn 26 px below the
    screen point (640, 350) the bench assumed, a terrace edge 40-60 units south of him; V2 and V3, on flat ground, were not).

    On A4's map (maps/sapporo.py) one guardian is parked far west; for each probe the camera moves to a point C (0.1 s),
    the guardian is parked again, and 2 s later he is teleported to a point U. Two archived frames, before and after
    the teleport, differ only by him: their difference (calib.blobs) gives where he is drawn. Probes with U = C ask what
    height the camera looks at (only the ground under C, or the ground around it, and how far around); probes with one
    C and several U at different heights ask how many pixels a unit of height moves a point on screen. '第几步' counts
    the probes so the frames line up (the archive's mission seconds run ~2 s behind these timers: step k+1 shows at
    about FIRST + k * PERIOD).

    Measured (run CampCameraWhere_mcp_1104_150834): the camera looks up to 43 of our units above the ground beside a
    terrace (V1), not lower where the ground around is lower; a unit of height moves a point 0.48 world units north on
    screen (~52 deg down). Fitted into calib.Ground (HEIGHT_Y, PIVOT_R), which the bench's world clicks now use.
    """
    from maps import sapporo
    from parts import Mission, Script, Test
    from checks.probe_view import open_in_view

    GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
    PARK = (250.0, 2500.0)                     # 'convoy start': ~950 west of the nearest probe, off every probe's screen
    FIRST, PERIOD, SHOW = 3.0, 5.0, 2.0        # probe k: camera at FIRST + k * PERIOD, the guardian SHOW seconds later
    # (camera point C, unit point U); heights in our units (ours = stored / 16): the lane at 340, the terraces at 455
    PROBES = [
        ((2830.0, 2225.0), (2830.0, 2225.0)),  # V3: flat for 300 around (the control: drawn at (640, 350) by the engineer)
        ((2830.0, 2225.0), (2830.0, 2325.0)),  # same camera, flat: the bench's ground mapping alone
        ((1200.0, 2400.0), (1200.0, 2400.0)),  # V1 (the engineer: (640, 376))
        ((1200.0, 2400.0), (1200.0, 2480.0)),  # same camera, the lane (340)
        ((1200.0, 2400.0), (1200.0, 2250.0)),  # same camera, the south terrace (455): height against pixels
        ((1200.0, 2400.0), (1080.0, 2200.0)),  # same camera, the south terrace further off
        ((1200.0, 2450.0), (1200.0, 2450.0)),  # U = C along x 1200, the cliff edge 2340-2380 south, a ramp 2550-2880 north
        ((1200.0, 2500.0), (1200.0, 2500.0)),
        ((1200.0, 2540.0), (1200.0, 2540.0)),
        ((1200.0, 2700.0), (1200.0, 2700.0)),  # the middle of a straight ramp: the mean around = the ground, the max is not
        ((1200.0, 2250.0), (1200.0, 2250.0)),  # the terrace 90 above the edge: the ground around is lower
        ((1200.0, 2150.0), (1200.0, 2150.0)),
        ((2015.0, 2635.0), (2015.0, 2635.0)),  # V2: flat for 100 around (the engineer: (640, 350))
    ]
    RUN = FIRST + len(PROBES) * PERIOD + 2.0


    def mission():
        m = Mission(name='CampCamera', map=sapporo, facts={})
        m.put(GUARDIAN, 'convoy start', 0, 0, name='UNIT - CNV Camera Guardian', role='guardian')
        return open_in_view(m, 'Camera')    # K5: the map's start (450, 2500) is too near the west edge


    def where(m):
        t = Test()
        name = m.role('guardian').name
        t.waypoints['Test Camera Park'] = PARK
        t.counters.append(('Test Step', '第几步'))
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_COUNTER', 'Test Step', 0)] +
                                [('SET_MILLISECOND_TIMER', f'Test - camera {k}', FIRST + k * PERIOD) for k in range(len(PROBES))]))
        for k, (c, u) in enumerate(PROBES):
            t.waypoints[f'Test Camera C{k}'] = c
            t.waypoints[f'Test Camera U{k}'] = u
            t.scripts += [Script(f'Test - camera {k}', [('TIMER_EXPIRED', f'Test - camera {k}')],
                                 [('UNIT_TELEPORT_TO_WAYPOINT', name, 'Test Camera Park'),
                                  ('MOVE_CAMERA_TO', f'Test Camera C{k}', 0.1, 0.0, 0.0, 0.0),
                                  ('SET_MILLISECOND_TIMER', f'Test - show {k}', SHOW)]),
                          Script(f'Test - show {k}', [('TIMER_EXPIRED', f'Test - show {k}')],
                                 [('UNIT_TELEPORT_TO_WAYPOINT', name, f'Test Camera U{k}'), ('SET_COUNTER', 'Test Step', k + 1)])]
        t.expect.append(('第几步', RUN - 1, 'ever==', len(PROBES)))
        t.bench = [('bench_watch', dict(seconds=RUN, every=0.5, sheet=False, lines=1))]
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_camera': mission}
    CHECKS = {'engine_camera': {'where': where}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_caption():
    """Engine unit test: when does the caption strip clear, and is the tutorial text box a strip that does not stack?

    The strip (the military caption, through ctx.caption, shared with dialogue subtitles) stacks lines and clears them all together. What
    sets the moment: a fixed hold after the last line (seen ~5.4 s with 6 s captions), or the last line's own seconds?
      A at A_AT for 15 s alone, B at B_AT for 2 s alone, C at C_AT for 2 s then D a second later for 10 s.
      Fixed hold: each clears ~5.4 s after its last line. Own seconds: A ~15 s, B ~2 s, C+D ~10 s after D.
    Then the tutorial text box (DISPLAY_TUTORIAL_TEXT): shown, replaced by a second text, hidden by HIDE_TUTORIAL_TEXT.
    '第几步' counts the events so the frames line up; bench_watch says per frame whether the strip changed.
    """
    from ctx import caption
    from maps import festival
    from parts import Mission, Script, Test

    A_AT, B_AT, C_AT, TIP_AT = 3.0, 25.0, 35.0, 52.0
    RUN = TIP_AT + 10.0
    EVENTS = [(A_AT, [caption('SCRIPT:CNVTEST_CAP_A', 15.0)]),
              (B_AT, [caption('SCRIPT:CNVTEST_CAP_B', 2.0)]),
              (C_AT, [caption('SCRIPT:CNVTEST_CAP_C', 2.0)]),
              (C_AT + 1, [caption('SCRIPT:CNVTEST_CAP_D', 10.0)]),
              (TIP_AT, [('DISPLAY_TUTORIAL_TEXT', 'SCRIPT:CNVTEST_TIP_1')]),
              (TIP_AT + 3, [('DISPLAY_TUTORIAL_TEXT', 'SCRIPT:CNVTEST_TIP_2')]),
              (TIP_AT + 6, [('HIDE_TUTORIAL_TEXT',)])]
    TEXT = {'SCRIPT:CNVTEST_CAP_A': 'TEST A：15 秒', 'SCRIPT:CNVTEST_CAP_B': 'TEST B：2 秒',
            'SCRIPT:CNVTEST_CAP_C': 'TEST C：2 秒', 'SCRIPT:CNVTEST_CAP_D': 'TEST D：10 秒',
            'SCRIPT:CNVTEST_TIP_1': 'TEST 提示框一', 'SCRIPT:CNVTEST_TIP_2': 'TEST 提示框二'}


    def mission():
        m = Mission(name='CampCaption', map=festival, facts={})
        m.put('AlliedAntiVehicleVehicleTech1', 'west field', 250, 30, name='UNIT - CNV Caption Guardian', role='guardian')
        return m


    def clears(m):
        t = Test()
        t.strings.update(TEXT)
        t.counters.append(('Test Step', '第几步'))
        t.scripts.append(Script('Test - start', [], [('SET_COUNTER', 'Test Step', 0)] +
                                [('SET_MILLISECOND_TIMER', f'Test - event {k}', at) for k, (at, _) in enumerate(EVENTS)]))
        for k, (_, acts) in enumerate(EVENTS):
            t.scripts.append(Script(f'Test - event {k}', [('TIMER_EXPIRED', f'Test - event {k}')],
                                    list(acts) + [('SET_COUNTER', 'Test Step', k + 1)]))
        t.expect += [('第几步', RUN - 2, 'ever==', len(EVENTS))]
        t.bench = [('bench_watch', dict(seconds=TIP_AT + 1.5, every=1, sheet=False, lines=1)),
                   ('bench_look', dict(note='the tutorial text box: where, how it looks (TEST 提示框一)')),
                   ('bench_watch', dict(seconds=RUN - TIP_AT - 1.5, every=1, sheet=False, lines=1))]
        return t


    # a build that is both mission and check (cnv/registry.py)
    PAIR_BUILDS = {'caption': lambda: (lambda m: (m, clears(m)))(mission())}
    return dict(PAIR_BUILDS=PAIR_BUILDS)


def engine_dialog():
    """Engine unit test: when the dialogue subtitle panel clears.

    The panel: bottom of the screen, yellow lines on a dark band, the subtitles of played dialogue (not the military
    caption box at the top, engine_caption). The game data sets it to hold a line 20 s; it was seen to clear
    after ~5.4 s.

    Bench 2026-11-04: it clears 5.1 - 5.6 game seconds after a line comes up, whatever the line's length (retail lines of
    3.3, 4.3 and 4.34 s) and whatever speed the bench runs the mission at (x1, x2.9, x8) -- not the 20 s, not the
    audio's end (at x2.9 the 4.34 s line's audio was still playing when the panel cleared), not real seconds (at x8 the
    audio had not finished in 33 game seconds, the panel was long gone). At x1, as a player sees it: up at 0.9 s, the
    audio done at 5.3 s, the panel gone between 5.7 and 6.0 s. So a dubbed line's subtitle stays ~5.5 s however long it is.
    Stack, the same day: the first line up at 1.0 s, the second joins under it at 2.8 - 3.1 s (the first moves up a row);
    both stay till 7.7 s and are gone together by 8.1 s -- the first line ~7 s, not its own 5.5. The panel clears as a
    whole ~5.2 s after its last line came; each new line starts the wait again.

    The checks: one retail line (its own subtitle) at PLAY_AT s, or two 20 s apart (pair), or two 2 s apart (stack: do
    the two leave together or each after its own ~5.5 s?); real and stack watch at x1 (a frame
    every 0.35 s), fast at x2.9 (every 1 s), slow at x8 (every 4 s). 第k句帧数 counts the game frames from the line's start
    till HAS_FINISHED_AUDIO -- the game's own clock (15 a second) to time the frames by, since the bench's seconds are its
    estimate. The panel is read off the frames: mean brightness and bright text pixels in its box (x 380-820, y 566-632
    of the 1280x720 frame), no counter can see it.
    """
    from maps import festival
    from parts import Mission, Script, Test

    PLAY_AT, RUN = 3.0, 33.0
    LINE = 'MA01_AlliedIntel24'                     # retail, 4.34 s, with its own subtitle
    PAIR = (('MA01_AlliedIntel36', PLAY_AT), ('MA01_AlliedIntel40', PLAY_AT + 20))     # 3.3 s and 4.3 s
    STACK = (('MA01_AlliedIntel36', PLAY_AT), ('MA01_AlliedIntel40', PLAY_AT + 2))     # stack: the second while the first is up


    def mission():
        m = Mission(name='CampDialog', map=festival, facts={})
        m.put('AlliedAntiVehicleVehicleTech1', 'west field', 250, 30, name='UNIT - CNV Dialog Guardian', role='guardian')
        return m


    def _line(t, k, line, at):
        """Play `line` at `at` s; counter k counts the frames till it has finished."""
        frames, played, done = f'CNV_Dialog_Frames{k}', f'CNV Dialog Played {k}', f'CNV Dialog Finished {k}'
        t.counters.append((frames, f'第{k}句帧数'))
        t.scripts += [
            Script(f'Test - play {k} timer', [], [('SET_MILLISECOND_TIMER', f'CNV Dialog Play {k}', at)]),
            Script(f'Test - play {k}', [('TIMER_EXPIRED', f'CNV Dialog Play {k}')],
                   [('PLAY_SOUND_EFFECT', line), ('SET_FLAG', played, 1)]),
            Script(f'Test - playing {k}', [('FLAG', played, 1), ('FLAG', done, 0)],
                   [('INCREMENT_COUNTER', 1, frames)], once=False),
            Script(f'Test - finished {k}', [('FLAG', played, 1), ('HAS_FINISHED_AUDIO', line)], [('SET_FLAG', done, 1)])]


    def _watch(every, lines=((LINE, PLAY_AT),), run=RUN):
        def check(m):
            t = Test()
            for k, (line, at) in enumerate(lines, 1):
                _line(t, k, line, at)
            t.expect += [('第1句帧数', 2, '>', 0)]            # the line played (the panel itself is read off the frames)
            t.bench = [('bench_watch', dict(seconds=run, every=every, sheet=False, lines=len(t.counters)))]
            return t
        return check


    # the builds this module makes and their checks (cnv/registry.py); the bench's rate is set by the frame interval
    MISSION = {'engine_dialog': mission}
    CHECKS = {'engine_dialog': {'real': _watch(0.35, run=14.0), 'fast': _watch(1), 'slow': _watch(4),
                                'pair': _watch(1, PAIR, run=48.0), 'stack': _watch(0.35, STACK, run=16.0)}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_eyes():
    """Retail-campaign conditions, batch 3 (round 237): CAMERA_ENTERED_AREA (60 uses, j02's statues with NAMED_DISCOVERED),
    ENEMY_SIGHTED (59: a02 / j06 / s08 / ep01, 'Enemy' 58 times, 'Friend' once) and TYPE_SELECTED (38: a06 / j01 hint
    scripts, the player's own click, the template written in lower case). Mission on maps/probe_border.py (level
    ground), every place absolute; every unit NO_ATTACK. Clear of probe_range's lanes (y 400, 1200-1900, 3300-3750) and
    the start (1250, 2500). Trigger areas do not overlap (round 236: a unit in too many at once freezes them).

      all  sight: the player's 'watch' (Guardian, sight 200) at (1000, 4500), its 'mate' 150 north, 'lone' alone at
           (2200, 4100); Soviet_4's 'near' 150 east of watch; Soviet_5's 'far' 600 east, sent at 5 s to 150 west of watch.
           看见 (every frame) = 1 ENEMY_SIGHTED(watch, Enemy, Soviet_4) 2 (watch, Enemy, Soviet_5) 4 (watch, Friend,
             Player_1) 8 (lone, Friend, Player_1) 16 (watch, Enemy, Player_1) 32 (near, Enemy, Player_1)
             64 (watch, Neutral, Soviet_4)
           camera: P1 (3500, 2500), P2 (2000, 2500). MOVE_CAMERA_TO P1 at 1 s (0.1 s), P2 at 6 s, P1 again at 9 s over
           4 s (passing M), P2 at 16 s. Areas: A (P1, half-side 100); strips round it, x 3300-3700: N1 y 2610-2900,
           N2 2900-3250, S1 2100-2390, S2 1500-2100, S3 600-1500; E x 3610-4100, y 2400-2600; M (2750, 2500) half-side 100.
           镜头 (every frame) = 1 CAMERA_ENTERED_AREA(A) 2 (N1) 4 (N2) 8 (S1) 16 (S2) 32 (S3) 64 (E) 128 (M)
           帧 (only added) = 1 a frame CAMERA_ENTERED_AREA(A) holds, 10000 a frame TYPE_SELECTED(Guardian, either case)
             holds (an edge or a state)
           selection: the player's 'pick' (Guardian, (3000, 4300)) and 'other' (Peacekeeper, (3300, 4300));
           SELECT_OBJECT(Player_1, pick) at 3 s. After 20 s by hand (bench_camera, bench_click): the player's own
           camera to P1, clicks on pick, other, the bare ground.
           选中 (every frame) = 1 NAMED_SELECTED(pick) 2 TYPE_SELECTED(Guardian) 4 TYPE_SELECTED(guardian, lower case)
             8 NAMED_SELECTED(other) 16 TYPE_SELECTED(Peacekeeper)
      [prediction from the data (the simulator before this round: the camera a point, set at once by MOVE_CAMERA_TO;
       ENEMY_SIGHTED any enemy of the viewer, the player argument unread, other relations a gap; TYPE_SELECTED never):
       看见 1 + 4 + 8 + 32 = 45 to ~s7 (the third argument the sighted object's owner: 2 only once far is within 200 of
       watch; a viewer counts itself as BY_TEAM's member does: 8, INFERRED), 47 after. 镜头 1 s2-s6, 0, 128 about
       s10-s11 (the camera moves, it is not set at once), 1 s13-s16, 0; the strips never (the camera's point is where it
       looks, not the eye or the view). 帧 grows while 1 holds (a state). 选中 1 from s3 (A222), TYPE_SELECTED only
       after a player's click: 1 + 2 + 4 while pick is clicked, 8 + 16 for other, 0 on the bare ground]
      BENCH 11-14 (round 237; build.py's own run CampSeeAll_mcp_1114_234139 PASS, then by hand _234250): 看见 / 镜头 /
        帧 / 选中 s1 45 129 27 0 | s2-s8 45 129 41..131 1 | s9-s21 47 129 146..328 1. By hand: the player's camera
        (minimap) to N2 133, to (4300, 4300) 133 still; left clicks on pick 1, on other 8, on pick 1, a box on pick 1; 帧
        never +10000. So: ENEMY_SIGHTED as predicted (the owner, Friend with the viewer itself); CAMERA_ENTERED_AREA
        latches for good once the camera's point has been in the area, the way there too (M from the 0.1 s move at 1 s),
        the player's camera as well, never the strips round the point; TYPE_SELECTED never (exact or lower case; a
        double click not tried); NAMED_SELECTED follows the player's clicks. Simulator: sim.Sim.cond ENEMY_SIGHTED /
        CAMERA_ENTERED_AREA, MOVE_CAMERA_TO (tests/test_simbench.py test_eyes_all_as_the_bench).
    """
    from maps import probe_border
    from parts import Mission, Script, Test, square, status
    import checks.engine_scripts8 as s8

    TANK, PK = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
    O = (1300.0, 4300.0)                            # probe_border's 'stop row'
    WATCH, MATE, LONE = (1000.0, 4500.0), (1000.0, 4650.0), (2200.0, 4100.0)
    NEAR, FAR, FAR_TO = (1150.0, 4500.0), (1600.0, 4500.0), (850.0, 4500.0)
    PICK, OTHER = (3000.0, 4300.0), (3300.0, 4300.0)
    P1, P2, M = (3500.0, 2500.0), (2000.0, 2500.0), (2750.0, 2500.0)
    STRIPS = {'N1': (3300.0, 2610.0, 3700.0, 2900.0), 'N2': (3300.0, 2900.0, 3700.0, 3250.0),
              'S1': (3300.0, 2100.0, 3700.0, 2390.0), 'S2': (3300.0, 1500.0, 3700.0, 2100.0),
              'S3': (3300.0, 600.0, 3700.0, 1500.0), 'E': (3610.0, 2400.0, 4100.0, 2600.0)}
    RUN = 20.0                                      # the scripted part; the bench run goes on by hand


    def _n(part):
        return f'UNIT - CNV Eyes {part.title()}'


    def _put(m, template, x, y, **kw):
        m.put(template, 'stop row', x - O[0], y - O[1], **kw)


    def _mark(m, part, x, y):
        m.waypoint(part, f'Test Eyes {part.title()}', 'stop row', x - O[0], y - O[1])


    def _rect(x0, y0, x1, y1):
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


    def mission():
        m = Mission(name='CampEyes', map=probe_border, units=[], facts={})
        m.spawns |= {TANK, PK}
        for role, side, template, (x, y) in (('watch', 'p1', TANK, WATCH), ('mate', 'p1', TANK, MATE),
                                             ('lone', 'p1', TANK, LONE), ('near', 's4', TANK, NEAR),
                                             ('far', 's5', TANK, FAR), ('pick', 'p1', TANK, PICK),
                                             ('other', 'p1', PK, OTHER)):
            _put(m, template, x, y, side=side, angle=0.0 if side == 'p1' else 3.1416, name=_n(role), role=role)
        for part, (x, y) in (('far to', FAR_TO), ('p1', P1), ('p2', P2)):
            _mark(m, part, x, y)
        return m


    def all_(m):
        t = Test()
        p1, s4, s5 = m.player(), m.player('s4'), m.player('s5')
        n = {r: m.role(r).name for r in ('watch', 'mate', 'lone', 'near', 'far', 'pick', 'other')}
        t.areas['Test Eyes A'] = square(*P1, 100.0)
        t.areas['Test Eyes M'] = square(*M, 100.0)
        for k, r in STRIPS.items():
            t.areas[f'Test Eyes {k}'] = _rect(*r)
        t.scripts.append(Script('Test - Eyes hold', [], [
            ('UNIT_CHANGE_OBJECT_STATUS', name, status('NO_ATTACK'), 1) for name in n.values()]))
        p1w, p2w = m.mark('p1'), m.mark('p2')
        s8.at(t, 'cam1', 1.0, [('MOVE_CAMERA_TO', p1w, 0.1, 0.0, 0.0, 0.0)])
        s8.at(t, 'sel', 3.0, [('SELECT_OBJECT', p1, n['pick'])])
        s8.at(t, 'far', 5.0, [('MOVE_NAMED_UNIT_TO', n['far'], m.mark('far to'))])
        s8.at(t, 'cam2', 6.0, [('MOVE_CAMERA_TO', p2w, 0.1, 0.0, 0.0, 0.0)])
        s8.at(t, 'cam3', 9.0, [('MOVE_CAMERA_TO', p1w, 4.0, 0.0, 0.0, 0.0)])
        s8.at(t, 'cam4', 16.0, [('MOVE_CAMERA_TO', p2w, 0.1, 0.0, 0.0, 0.0)])
        s8.total(t, 'CNV_Eyes_Sight', '看见', [
            (1, ('ENEMY_SIGHTED', n['watch'], 'Enemy', s4)), (2, ('ENEMY_SIGHTED', n['watch'], 'Enemy', s5)),
            (4, ('ENEMY_SIGHTED', n['watch'], 'Friend', p1)), (8, ('ENEMY_SIGHTED', n['lone'], 'Friend', p1)),
            (16, ('ENEMY_SIGHTED', n['watch'], 'Enemy', p1)), (32, ('ENEMY_SIGHTED', n['near'], 'Enemy', p1)),
            (64, ('ENEMY_SIGHTED', n['watch'], 'Neutral', s4))])
        s8.total(t, 'CNV_Eyes_Cam', '镜头', [(w, ('CAMERA_ENTERED_AREA', f'Test Eyes {k}')) for w, k in (
            (1, 'A'), (2, 'N1'), (4, 'N2'), (8, 'S1'), (16, 'S2'), (32, 'S3'), (64, 'E'), (128, 'M'))])
        t.counters.append(('CNV_Eyes_Frames', '帧'))
        t.scripts += [Script('Test - CNV_Eyes_Frames A', [('CAMERA_ENTERED_AREA', 'Test Eyes A')],
                             [('INCREMENT_COUNTER', 1, 'CNV_Eyes_Frames')], once=False),
                      Script('Test - CNV_Eyes_Frames T', [('TYPE_SELECTED', TANK)],
                             [('INCREMENT_COUNTER', 10000, 'CNV_Eyes_Frames')], once=False),
                      Script('Test - CNV_Eyes_Frames t', [('TYPE_SELECTED', TANK.lower())],
                             [('INCREMENT_COUNTER', 10000, 'CNV_Eyes_Frames')], once=False)]
        s8.total(t, 'CNV_Eyes_Sel', '选中', [
            (1, ('NAMED_SELECTED', n['pick'])), (2, ('TYPE_SELECTED', TANK)), (4, ('TYPE_SELECTED', TANK.lower())),
            (8, ('NAMED_SELECTED', n['other'])), (16, ('TYPE_SELECTED', PK))])
        t.expect = [('看见', 0, 'ever>=', 1, RUN)]
        s8.watch(t, RUN)
        return t


    MISSION = {'engine_eyes': mission}
    CHECKS = {'engine_eyes': {'all': all_}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_joypad():
    """C: retail Joypad element disable/restore observation probe.

    Untouched baseline through 4 s; disable the two retail button names at 4 s;
    restore tech store at 8 s; restore assault directive at 12 s. The phase counter
    marks script execution only, NOT element enabled state or input acceptance.
    Prediction: one untouched power plant remains alive throughout all four phases.
    This is a liveness/control prediction, not whole-action simulation equivalence.
    No mouse or keyboard event is passed off as native Joypad input: the current
    bench publishes keyboard/mouse injection but no controller input/state contract.
    Observe the real run before deciding whether a native UI gate can be measured.
    Evidence and remaining gate: work/re/c_joypad_report.md.
    BENCH 11-16: one run, 17 readings f40..182, all phases 0/1/2/3 observed,
    untouched alive=1 throughout; final phase/alive/frame=3/1/182, NOEXPECT.
    These are script markers, not native Joypad state. No enabled/accept/reject
    field is published; the native gate remains unmeasured and the action TODO.
    """
    from maps import probe_border
    from parts import Mission, Script, Test
    from checks import engine_scripts8 as s8


    def mission():
        m = Mission(name='CampJoypad', map=probe_border, units=[], facts={})
        m.put('AlliedPowerPlant', 'stop row', 0., -500., side='p1',
              name='CNV Joypad untouched', role='untouched')
        return m


    def a(m):
        t = Test()
        phase = 'CNV_Joypad_Phase'
        t.counters.append((phase, '脚本阶段'))
        t.scripts.append(Script('Test - joypad baseline', [], [
            ('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_COUNTER', phase, 0)]))
        buttons = ('buttonopenplayertechstore', 'buttonaiassaultdirective')
        for seconds, number, changes in (
                (4., 1, [(button, 1) for button in buttons]),
                (8., 2, [(buttons[0], 0)]),
                (12., 3, [(buttons[1], 0)])):
            s8.at(t, f'joypad phase {number}', seconds, [
                *[('DISABLE_JOYPAD_COMMANDBAR_BUTTON', button, disabled)
                  for button, disabled in changes], ('SET_COUNTER', phase, number)])
        s8.total(t, 'CNV_Joypad_Alive', '未操作存活', [
            (1, ('NAMED_NOT_DESTROYED', m.role('untouched').name))])
        s8.frames(t, 'CNV_Joypad_Clock', '逻辑帧', [])
        s8.watch(t, 16.)
        return t


    MISSION = {'engine_joypad': mission}
    CHECKS = {'engine_joypad': {'a': a}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_letterbox():
    """Engine measurement: what ground a scene's picture shows (letterbox on) -- the width of the band at its top, middle and
    bottom row, and where the band's middle sits against the camera centre (K8; model.LETTERBOX_BAND).

    On A4's map (maps/sapporo.py) a grid of guardians stands parked far west. The scene opens (CAMERA_LETTERBOX_BEGIN), the
    camera moves to a flat point C (0.1 s); a few seconds later every guardian is teleported to its grid point at once. Two
    archived frames, before and after, differ only by the guardians: their difference (calib.blobs) gives where each is
    drawn; matched to the grid (rows top to bottom = north to south) they fit a homography of ground -> screen (calib.fit's
    way) for this camera. tools: python -I experimental/testbench/letterbox_fit.py <run dir> <frame before> <frame after>.
    """
    from maps import sapporo
    from parts import Mission, Script, Test
    from checks.probe_view import open_in_view

    GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
    PARK = (250.0, 2500.0)                      # 'convoy start'
    C = (2830.0, 2225.0)                        # camera centre: A4's V3, the ground flat for 300 around, the avenue
    COLS = [-450.0, -300.0, -150.0, 0.0, 150.0, 300.0, 450.0]       # grid offsets from C (x)
    ROWS = [-250.0, -125.0, 0.0, 125.0, 250.0]                       # (y)
    GRID = [(C[0] + dx, C[1] + dy) for dy in ROWS for dx in COLS
            if (dx, dy) != (450.0, 125.0)]      # (that spot stands on a tree: test_maps, nothing a build places on scenery)
    SCENE_AT, SHOW_AT, RUN = 2.0, 6.0, 9.0


    def mission():
        m = Mission(name='CampLbx', map=sapporo, facts={})
        for k in range(len(GRID)):
            m.put(GUARDIAN, 'convoy start', 0, 0, name=f'UNIT - CNV Letterbox G{k}', role=f'g{k}')
        return open_in_view(m, 'Letterbox')


    def grid(m):
        t = Test()
        t.waypoints['Test Letterbox C'] = C
        t.counters.append(('Test Step', '第几步'))
        for k, p in enumerate(GRID):
            t.waypoints[f'Test Letterbox P{k}'] = p
        t.scripts += [
            Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_COUNTER', 'Test Step', 0),
                                        ('SET_MILLISECOND_TIMER', 'Test - scene', SCENE_AT),
                                        ('SET_MILLISECOND_TIMER', 'Test - show', SHOW_AT)]),
            Script('Test - scene', [('TIMER_EXPIRED', 'Test - scene')],
                   [('CAMERA_LETTERBOX_BEGIN',), ('MOVE_CAMERA_TO', 'Test Letterbox C', 0.1, 0.0, 0.0, 0.0)]),
            Script('Test - show', [('TIMER_EXPIRED', 'Test - show')],
                   [('UNIT_TELEPORT_TO_WAYPOINT', f'UNIT - CNV Letterbox G{k}', f'Test Letterbox P{k}') for k in range(len(GRID))] +
                   [('SET_COUNTER', 'Test Step', 1)])]
        t.expect.append(('第几步', RUN - 1, 'ever==', 1))
        t.bench = [('bench_watch', dict(seconds=RUN, every=0.5, sheet=False, lines=1))]
        return t


    MISSION = {'engine_letterbox': mission}
    CHECKS = {'engine_letterbox': {'g': grid}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_markobj():
    """Engine probe, MARK_MISSION_OBJECTIVE_COMPLETED (14 retail uses) and MARK_MISSION_OBJECTIVE_NOT_COMPLETED (1): what
    each does to an objective in the mission menu, from each status. No condition reads an objective, so -- as
    engine_scripts5 -- the counter 阶段 (1 at STEP1, 2 at STEP2) only says the steps ran and the reading is the menu
    (the check's last bench step, bench_menu: a frame in the run folder). Retail: a04 'Objective1a' is shown (status 1)
    and later only MARKed completed, no status 2; j07 'failed bonus 2' MARKs a bonus NOT_COMPLETED -- used as its failure. Mission here (build
    engine_markobj) on maps/probe_border.py: one tank of the player's at 'line', all six objectives hidden at the start.

      goals   STEP1 sets the starting status, STEP2 the MARK:
                M1 一：1, then COMPLETED                  -- a04's use: done?
                M2 二：never shown, then COMPLETED        -- listed done (as status 2 without 1, engine_scripts5 O4)?
                M3 三：1, then NOT_COMPLETED              -- no mark (shown) or failed?
                M4 四：2, then NOT_COMPLETED              -- done taken back: no mark, or failed?
                M5 五：3, then COMPLETED                  -- failed turned done?
                M6 六 (bonus)：1, then NOT_COMPLETED      -- j07's use
              [The simulator (sim.py, before this probe): the engine model's core keeps COMPLETED = 2 and NOT_COMPLETED =
              1 in its own table, the simulator's objectives never see them -- so M1 stays 1, M2 hidden, M3 1, M4 2,
              M5 3, M6 1. The model's own guess: M1 2, M2 2, M3 1, M4 1, M5 2, M6 1.]

    读数 (bench 11-16, two runs, the same menu: CampMarkGoals_mcp_1116_124443 (its verdict FAIL only for the menu's
    pause hiding the s16 reading: the expectation now ends at s15) and _124638 PASS; 阶段 2 from s6; menu frame 14)
      menu list (main, green):  1. 一 [check]   2. 三 [empty box]   3. 四 [empty box]   4. 五 [check]   5. 二 [check]
                (bonus, yellow):  1. 六 [empty box]
      - COMPLETED = status 2 from any status: M1 shown -> done (a04's use), M5 failed -> done, M2 hidden -> listed done,
        last (first shown at STEP2, the list in order of first appearance as engine_scripts5).
      - NOT_COMPLETED = status 1: M3 stays shown unticked, M4 done -> unticked, M6 bonus unticked -- no failed mark
        anywhere, so j07's 'failed bonus 2' only takes the tick back. The model's guess holds; the simulator now passes
        both to its own objectives (Sim.act), tests/test_simbench.py test_mark_objective_as_the_bench.
    """
    from maps import probe_border
    from parts import Goal, Mission, Script, Test

    TANK = 'AlliedAntiVehicleVehicleTech1'
    STEP1, STEP2, RUN = 2.0, 6.0, 12.0
    DONE, NOT_DONE = 'MARK_MISSION_OBJECTIVE_COMPLETED', 'MARK_MISSION_OBJECTIVE_NOT_COMPLETED'
    GOALS = [('M1', '一 亮出后标完成'), ('M2', '二 不亮直接标完成'), ('M3', '三 亮出后标未完成'),
             ('M4', '四 完成后标未完成'), ('M5', '五 失败后标完成'), ('M6', '六 奖励 亮出后标未完成')]
    STEPS = {'M1': (1, DONE), 'M2': (None, DONE), 'M3': (1, NOT_DONE), 'M4': (2, NOT_DONE), 'M5': (3, DONE),
             'M6': (1, NOT_DONE)}


    def goal(name):
        return f'CNV MK {name}'


    def mission():
        goals, strings = [], {}
        for name, title in GOALS:
            key = f'MISSIONOBJ:CNVMK_{name}'
            strings[key], strings[key + '_DESC'] = title, f'探针目标 {name}：{title}'
            goals.append(Goal(goal(name), key, key + '_DESC', bonus=name == 'M6', at=None))
        m = Mission(name='CampMark', map=probe_border, objectives=goals, facts={})
        m.strings.update(strings)
        m.put(TANK, 'line', 0.0, 0.0, angle=0.0, name='UNIT - CNV MK Tank', role='tank')
        return m


    def _at(t, key, secs, actions):
        timer = f'Test {key} Timer'
        t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                      Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


    def goals(m):
        t = Test()
        first = [('SET_MISSION_OBJECTIVE_STATUS', goal(n), s) for n, (s, _) in STEPS.items() if s is not None]
        second = [(mark, goal(n)) for n, (_, mark) in STEPS.items()]
        t.counters.append(('CNV_MK_Step', '阶段'))
        t.scripts.append(Script('Test - step 0', [], [('SET_COUNTER', 'CNV_MK_Step', 0)]))
        _at(t, 'one', STEP1, first + [('SET_COUNTER', 'CNV_MK_Step', 1)])
        _at(t, 'two', STEP2, second + [('SET_COUNTER', 'CNV_MK_Step', 2)])
        t.expect += [('阶段', STEP2 + 2, '==', 2, RUN + 3)]         # the menu step's pause: no reading after it
        t.bench = [('bench_watch', dict(seconds=RUN, every=1.0, sheet=False, lines=1)), ('bench_menu', dict(scale=0.5))]
        return t


    MISSION = {'engine_markobj': mission}
    CHECKS = {'engine_markobj': {'goals': goals}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_mousehud():
    """C: native SellButton disable/restore against script sale and untouched controls.

    Retail a01 uses SellButton,1; a03 restores other fixed elements with 0.
    A keeps SellButton disabled. B disables then restores it before the same native clicks.
    Prediction: the native target survives A and is sold in B; script SELL_OBJECT sells
    its separate target in both. The untouched third power plant survives both.
    Alive bits: native=1, scripted=2, untouched=4; expected final A=5, B=4.
    Money starts at 2000; full-health AlliedPowerPlant costs 800, refund 400.
    This is a UI probe, not evidence that every fixed element is a simulation no-op.
    Evidence/scope: work/re/c_mousehud_report.md. No HUD-state interface is assumed.
    BENCH 11-16: A f356 and B f414 both finish alive=5, money=2400.
    Native clicks select the target instead of selling it, even after restoration.
    The original B positive prediction is retained as a strict xfail, not fitted away.
    Final archived frames show A's dollar button grey, B's lit; no numeric HUD state
    or accepted sale-mode field is published. Per-call Esc may cancel the mode
    (INFERRED). Two-run budget exhausted; the action remains TODO.
    """
    from maps import probe_border
    from parts import Mission, Script, Test
    from checks import engine_scripts8 as s8


    def mission():
        m = Mission(name='CampMouseHUD', map=probe_border, units=[], facts={})
        for role, dx in (('native', 0.), ('scripted', 450.), ('untouched', 900.)):
            m.put('AlliedPowerPlant', 'stop row', dx, -500., side='p1',
                  name=f'CNV MouseHUD {role}', role=role)
        return m


    def check(m, restore):
        t = Test()
        actions = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                   ('PLAYER_SET_MONEY', m.player('p1'), 2000),
                   ('DISABLE_MOUSE_HUD_FIXED_ELEMENT', 'SellButton', 1)]
        if restore:
            actions.append(('DISABLE_MOUSE_HUD_FIXED_ELEMENT', 'SellButton', 0))
        t.scripts.append(Script('Test - mousehud setup', [], actions))
        s8.at(t, 'mousehud script sale', 2., [('SELL_OBJECT', m.role('scripted').name)])
        s8.total(t, 'CNV_MouseHUD_Alive', '存活', [
            (w, ('NAMED_NOT_DESTROYED', m.role(role).name))
            for w, role in ((1, 'native'), (2, 'scripted'), (4, 'untouched'))])
        t.counters.append(('CNV_MouseHUD_Money', '资金'))
        t.scripts.append(Script('Test - mousehud money', [], [
            ('SET_PLAYER_MONEY_TO_COUNTER', m.player('p1'), 'CNV_MouseHUD_Money')], once=False))
        s8.frames(t, 'CNV_MouseHUD_Clock', '逻辑帧', [])
        target = m.find(m.role('native').name)
        watch = dict(every=1., sheet=False, lines=3)
        t.bench = [('bench_watch', dict(watch, seconds=4.)),
                   ('bench_camera', dict(x=target.x, y=target.y, look=False)),
                   ('bench_click', dict(x=1126, y=222, world=False, look=False)),
                   ('bench_click', dict(x=target.x, y=target.y, look=False)),
                   ('bench_watch', dict(watch, seconds=7.))]
        return t


    def a(m):
        return check(m, False)


    def b(m):
        return check(m, True)


    MISSION = {'engine_mousehud': mission}
    CHECKS = {'engine_mousehud': {'a': a, 'b': b}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_radar():
    """E158 RadarBehavior: isolated retail dish / module-removal HUD control.

    Prediction (INFERRED, before bench): without the native PlayerSpellBook
    RadarBehavior, the minimap works only with the dish's module, and stops after
    the dish is deleted at 12 seconds. The second build removes only that module.
    No reveal-all, radar UI toggle, or injected effect state is used. Four counters
    measure frame, dish survival, support survival and sufficient power, NOT radar.
    Saved full frames must be inspected for the independent minimap output.
    SpellBook is linked over retail under its own id; no other radar host is placed.
    This diagnostic alone does not register module coverage. See work/re/e158_radar.md.

    MEASURED 2026-11-15: both prerequisites PASS. On: f151=1/1/1,
    minimap terrain; f303=0/1/1, Allied emblem. Off: f149=1/1/1,
    f308=0/1/1, emblem both times. Named model provider replay passes;
    PLAYER_HAS_POWER script replay is a separate strict xfail.
    E159 engine_radarlow:a: f147=1/1/1, f302=1/1/0; minimap terrain
    in both frames. Supply/demand 150/75 -> 50/75 after plant deletion.
    Only this retail dish's low-power case is measured; other hosts remain gaps.
    """
    import re
    from pathlib import Path

    import labpaths
    from maps import probe_range
    from model import Mission, Script, Test, Unit


    def without_radar(xml):
        xml, count = re.subn(r'<RadarBehavior\b[^>]*/>', '', xml)
        assert count == 1
        return xml


    def mission(enabled=True):
        m = Mission(name='CampRadarE' if enabled else 'CampRadarOffE', map=probe_range,
                    facts={'radar_module': enabled})
        sage = Path(labpaths.SDK3) / 'SageXML'
        spellbook = (sage / 'System/PlayerSpellBook.xml').read_text(encoding='utf-8-sig')
        m.assets.append(('E158SpellBook.xml', without_radar(spellbook), 'GameObject:PlayerSpellBook'))
        m.replaces.append('GameObject:PlayerSpellBook')
        source = (sage / 'Allied/Structures/AlliedRadarDish.xml').read_text(encoding='utf-8-sig')
        ident = 'CNVE158Radar'
        source = source.replace('id="AlliedRadarDish"', f'id="{ident}"', 1)
        m.units.append(Unit(ident, source if enabled else without_radar(source)))
        m.put(ident, 'base gun', role='dish', name='E158 dish')
        m.put('AlliedConstructionYard', 'base gun', 0, 650, role='yard', name='E158 yard')
        m.put('AlliedPowerPlant', 'base gun', 400, 0, role='power', name='E158 power')
        return m


    def check(m):
        t = Test()
        t.counters = [('E158Frame', '帧数'), ('E158Dish', '宿主量'),
                      ('E158Support', '前置量'), ('E158Power', '供电量')]
        t.scripts = [
            Script('Test - E158 start', [], [('SET_MILLISECOND_TIMER', 'E158 delete', 12.)]),
            Script('Test - E158 frame', [], [('INCREMENT_COUNTER', 1, 'E158Frame')], once=False),
            Script('Test - E158 clear', [], [('SET_COUNTER', c, 0) for c, _ in t.counters[1:]], once=False),
            Script('Test - E158 dish', [('NAMED_NOT_DESTROYED', m.role('dish').name)],
                   [('SET_COUNTER', 'E158Dish', 1)], once=False),
            Script('Test - E158 support', [('NAMED_NOT_DESTROYED', m.role('yard').name),
                                          ('NAMED_NOT_DESTROYED', m.role('power').name)],
                   [('SET_COUNTER', 'E158Support', 1)], once=False),
            Script('Test - E158 powered', [('PLAYER_HAS_POWER', m.player('p1'))],
                   [('SET_COUNTER', 'E158Power', 1)], once=False),
            Script('Test - E158 delete', [('TIMER_EXPIRED', 'E158 delete')],
                   [('NAMED_DELETE', m.role('dish').name)]),
        ]
        t.expect = [('宿主量', 5, '==', 1, 10), ('宿主量', 16, '==', 0, 20),
                    ('前置量', 5, '==', 1, 20), ('供电量', 5, '==', 1, 20)]
        t.bench = [('bench_watch', dict(seconds=24, every=1, sheet=False, lines=4))]
        return t


    def low_power_mission():
        """E159: retail supply 150 -> 50, demand 75; only the plant is deleted.

        INFERRED prediction: the dish lacks POWERED KindOf, so radar may remain
        available even when PLAYER_HAS_POWER becomes false. HUD decides the rule.
        SpellBook isolation is identical to E158. See work/re/e159_radar_power.md.
        """
        m = mission()
        m.name = 'CampRadarLowE'
        for i in range(3):
            m.put('AlliedBarracks', 'base gun', 650 + i * 250, 650,
                  role=f'load{i}', name=f'E159 load{i}')
        return m


    def low_power_check(m):
        t = check(m)
        # Preserve dish and all consumers; change only the supply at 12 seconds.
        t.scripts[-1] = Script('Test - E159 remove supply', [('TIMER_EXPIRED', 'E158 delete')],
                               [('NAMED_DELETE', m.role('power').name)])
        t.scripts[4] = Script('Test - E159 consumers',
                             [('NAMED_NOT_DESTROYED', m.role(r).name)
                              for r in ('yard', 'load0', 'load1', 'load2')],
                             [('SET_COUNTER', 'E158Support', 1)], once=False)
        t.expect = [('宿主量', 5, '==', 1, 20), ('前置量', 5, '==', 1, 20),
                    ('供电量', 5, '==', 1, 10), ('供电量', 16, '==', 0, 20)]
        return t


    def two_provider_mission():
        """E160: same retail providers, delete first at 12s and last at 24s.

        INFERRED prediction before bench: terrain -> terrain -> emblem.
        Independent named survival/power counters establish prerequisites; the
        saved HUD frames decide radar output. See work/re/e160_radar_multi.md.
        MEASURED: f114=1/1/1 terrain, f197=0/1/1 terrain, f386=0/0/1 emblem.
        Slow-run wall-time expectations failed; retained without widening them.
        Named logic-frame replays assert the measured lifetime and HUD instead.
        """
        m = mission()
        m.name = 'CampRadarTwoE'
        m.put('CNVE158Radar', 'base gun', -500, 0, role='second', name='E160 second')
        return m


    def two_provider_check(m):
        t = check(m)
        t.counters.insert(2, ('E160Second', '第二宿主'))
        t.counters = [(c, label) for c, label in t.counters if c != 'E158Support']
        t.scripts[0].do.append(('SET_MILLISECOND_TIMER', 'E160 last', 24.))
        t.scripts[2].do.append(('SET_COUNTER', 'E160Second', 0))
        t.scripts[2].do = [a for a in t.scripts[2].do if a[1] != 'E158Support']
        t.scripts.insert(4, Script('Test - E160 second',
                                  [('NAMED_NOT_DESTROYED', m.role('second').name)],
                                  [('SET_COUNTER', 'E160Second', 1)], once=False))
        # Four HUD lines: the last line proves power AND both support hosts.
        support = t.scripts.pop(5)
        t.scripts[5].when.extend(support.when)
        t.scripts.append(Script('Test - E160 last', [('TIMER_EXPIRED', 'E160 last')],
                                [('NAMED_DELETE', m.role('second').name)]))
        t.expect = [('宿主量', 5, '==', 1, 10), ('宿主量', 16, '==', 0, 32),
                    ('第二宿主', 5, '==', 1, 20), ('第二宿主', 28, '==', 0, 32),
                    ('供电量', 5, '==', 1, 32)]
        t.bench = [('bench_watch', dict(seconds=36, every=1, sheet=False, lines=4))]
        return t


    def death_mission():
        """E161: retail 500 HP dish, 250 damage at 6s, 1000 damage at 12s.

        NAMED_DAMAGE is the measured health-changing entry in engine_immortal.
        INFERRED prediction: 100 -> 50 percent while alive, then destroyed;
        terrain before the lethal hit, emblem afterwards. Retail SlowDeath has
        an 8s destruction delay: this does not predict its exact unregister frame.
        No delete, forced health, reveal, or radar toggle. See work/re/e161_radar_death.md.
        MEASURED: f87=0/100, f95/f173=0/50 (gone/HP), terrain;
        f182=1/0 HUD shutdown transition, f192/f374=1/0 emblem. Support=1.
        Queue expectations PASS; exact unregister frame remains unmeasured.
        """
        m = mission()
        m.name = 'CampRadarDeadE'
        return m


    def death_check(m):
        t = Test()
        dish = m.role('dish').name
        t.counters = [('E161Frame', '帧数'), ('E161Gone', '死亡'),
                      ('E161HP', '血量'), ('E161Support', '供电前置')]
        t.scripts = [
            Script('Test - E161 start', [], [('SET_MILLISECOND_TIMER', 'E161 hurt', 6.),
                                            ('SET_MILLISECOND_TIMER', 'E161 lethal', 12.)]),
            Script('Test - E161 frame', [], [('INCREMENT_COUNTER', 1, 'E161Frame')], once=False),
            Script('Test - E161 hp', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', dish, 'E161HP')], once=False),
            Script('Test - E161 gone', [('NAMED_DESTROYED', dish)], [('SET_COUNTER', 'E161Gone', 1)]),
            Script('Test - E161 clear support', [], [('SET_COUNTER', 'E161Support', 0)], once=False),
            Script('Test - E161 support', [('PLAYER_HAS_POWER', m.player('p1')),
                                          ('NAMED_NOT_DESTROYED', m.role('yard').name),
                                          ('NAMED_NOT_DESTROYED', m.role('power').name)],
                   [('SET_COUNTER', 'E161Support', 1)], once=False),
            Script('Test - E161 hurt', [('TIMER_EXPIRED', 'E161 hurt')], [('NAMED_DAMAGE', dish, 250)]),
            Script('Test - E161 lethal', [('TIMER_EXPIRED', 'E161 lethal')], [('NAMED_DAMAGE', dish, 1000)]),
        ]
        t.expect = [('血量', 0, 'ever<=', 50, 40), ('死亡', 0, 'ever>=', 1, 40),
                    ('供电前置', 0, '==', 1, 40)]
        t.bench = [('bench_watch', dict(seconds=40, every=1, sheet=False, lines=4))]
        return t


    def transfer_mission(incoming=False):
        """E162: reciprocal scripted owner transfer, NOT engineer capture.

        INFERRED prediction: outgoing local HUD terrain -> emblem; incoming
        emblem -> terrain. Both owners retain live yards/plants and power.
        Two runs observe the local HUD as old and new owner respectively;
        no claim about the unobserved Soviet_4 HUD. See work/re/e162_radar_owner.md.
        MEASURED: out f91 owner1 terrain -> f312 owner2 emblem;
        in f87 owner2 emblem -> f282 owner1 terrain; alive/support=1 throughout.
        Exact transfer callback timing and engineer capture remain gaps.
        """
        m = mission()
        m.name = 'CampRadarInE' if incoming else 'CampRadarOutE'
        m.facts['incoming'] = incoming
        if incoming:
            m.objects[0].side = 's4'
            m.cast['dish'].side = 's4'
        m.put('AlliedConstructionYard', 'high gun', 0, 650, side='s4',
              role='other yard', name='E162 other yard')
        m.put('AlliedPowerPlant', 'high gun', 400, 0, side='s4',
              role='other power', name='E162 other power')
        return m


    def transfer_check(m):
        t = Test()
        dish = m.role('dish').name
        t.counters = [('E162Frame', '帧数'), ('E162Owner', '归属量'),
                      ('E162Alive', '存活量'), ('E162Support', '供电前置')]
        t.scripts = [
            Script('Test - E162 start', [], [('SET_MILLISECOND_TIMER', 'E162 swap', 12.)]),
            Script('Test - E162 frame', [], [('INCREMENT_COUNTER', 1, 'E162Frame')], once=False),
            Script('Test - E162 clear', [], [('SET_COUNTER', c, 0) for c, _ in t.counters[1:]], once=False),
            Script('Test - E162 alive', [('NAMED_NOT_DESTROYED', dish)],
                   [('SET_COUNTER', 'E162Alive', 1)], once=False),
            Script('Test - E162 support', [('PLAYER_HAS_POWER', m.player(s)) for s in ('p1', 's4')]
                   + [('NAMED_NOT_DESTROYED', m.role(r).name)
                      for r in ('yard', 'power', 'other yard', 'other power')],
                   [('SET_COUNTER', 'E162Support', 1)], once=False),
        ]
        for value, side in ((1, 'p1'), (2, 's4')):
            t.scripts.append(Script('Test - E162 owner ' + side,
                                    [('NAMED_OWNED_BY_PLAYER', m.player(side), dish)],
                                    [('SET_COUNTER', 'E162Owner', value)], once=False))
        t.scripts.append(Script('Test - E162 transfer', [('TIMER_EXPIRED', 'E162 swap')],
                                [('NAMED_TRANSFER_OWNERSHIP_PLAYER', dish,
                                  m.player('p1' if m.facts['incoming'] else 's4'))]))
        before, after = (2, 1) if m.facts['incoming'] else (1, 2)
        t.expect = [('归属量', 0, 'ever>=', before, 40),
                    ('归属量', 0, 'ever==', after, 40),
                    ('存活量', 0, '==', 1, 40), ('供电前置', 0, '==', 1, 40)]
        t.bench = [('bench_watch', dict(seconds=40, every=1, sheet=False, lines=4))]
        return t


    MISSION = {'engine_radar': mission, 'engine_radaroff': lambda: mission(False),
               'engine_radarlow': low_power_mission, 'engine_radartwo': two_provider_mission,
               'engine_radardeath': death_mission, 'engine_radarout': transfer_mission,
               'engine_radarin': lambda: transfer_mission(True)}
    CHECKS = {name: {'a': {'engine_radarlow': low_power_check,
                          'engine_radartwo': two_provider_check,
                          'engine_radarout': transfer_check, 'engine_radarin': transfer_check,
                          'engine_radardeath': death_check}.get(name, check)} for name in MISSION}
    CONTROLS = {'engine_radaroff': 'engine_radar'}
    return dict(MISSION=MISSION, CHECKS=CHECKS, CONTROLS=CONTROLS)


def engine_scripts5():
    """Engine probe, the mission objective items (docs/engine/inventory-levels-a.md, the three heaviest inferred script
    actions): SET_MISSION_OBJECTIVE_STATUS (732), LINK_MISSION_OBJECTIVE_TO_OBJECT (950), LINK_MISSION_OBJECTIVE_TO_WAYPOINT
    (194). No condition reads an objective, so the check only steps the statuses (counter 阶段: 1 at STEP1, 2 at STEP2)
    and the reading is the mission menu (cnv_check keep=true, then bench_menu by hand). Mission here (build
    engine_scripts5) on maps/probe_border.py (the simulator's level ground): one tank of the player's at 'line' for the object markers.

      goals   six objectives, all hidden at the start (the mission's own goal_scripts), then:
                O1 一：1 at STEP1, 2 at STEP2                        -- shown, then done
                O2 二：1 at STEP1, 3 at STEP2                        -- shown, then failed
                O3 三：1 at STEP1, 0 at STEP2                        -- shown, then hidden again?
                O4 四：2 at STEP2, never 1                           -- done without being shown: listed?
                O5 五：1 at STEP1, 7 at STEP2                        -- a status out of 0..3 [源码: ignored, stays shown]
                O6 六 (bonus)：1 at STEP1                            -- a yellow one, shown
              markers: O1 on the tank (TO_OBJECT 1 at STEP1, left on after done), O2 on the tank too, taken off at STEP2
              (TO_OBJECT 0), O6 on a waypoint 600 east of it (TO_WAYPOINT 1 at STEP1).
              [The simulator (sim.py): objectives[name] = status as written, 7 too; markers a set per objective, apart
              from the status.]

    读数 (bench 11-09, CampScr5Goals_mcp_1109_095326: PASS 阶段 1 s1-s4, 2 from s5; bench_menu at s14, minimap frames 4 / 13)
      menu list at s14 (main, green):  1. 一 [check]   2. 二 [red X]   3. 五 [empty box]   4. 四 [check]
                   (bonus, yellow, numbered apart):  1. 六 [empty box]
      - O1 1 -> 2: done mark; O2 1 -> 3: failed mark.
      - O3 1 -> 0: gone from the list, the numbers close up (五 is 3) -- 0 hides an objective already shown.
      - O4 2 without ever 1: listed, done -- a done / failed status shows it too.
      - the list is in order of first appearance, not of the mission's goal list: 四 (first shown at STEP2) after 五
        (STEP1).
      - O5 1 -> 7: still listed, no mark -- 7 ignored, as the source (and the simulator since round 119).
      - O6 bonus: a separate yellow list, its own numbers from 1.
      - markers (minimap, s4): a green '!' on the tank (main; O1 and O2 both on it, one icon drawn), a yellow '!' at the
        east waypoint (bonus). s13: the tank's marker gone (O1 done with its link left on, O2 unlinked and failed), the
        waypoint's stays. The menu map at s14 shows only the bonus pin ('1', yellow). So a done objective's marker is not
        drawn [not told apart: done hides the marker vs one icon per object that O2's unlink took away].
    """
    from maps import probe_border
    from parts import Goal, Mission, Script, Test

    TANK = 'AlliedAntiVehicleVehicleTech1'
    STEP1, STEP2, RUN = 2.0, 6.0, 12.0
    GOALS = [('O1', '一 亮出后完成'), ('O2', '二 亮出后失败'), ('O3', '三 亮出后藏回'), ('O4', '四 不亮直接完成'),
             ('O5', '五 亮出后写 7'), ('O6', '六 奖励 只亮出')]
    STEPS = {'O1': (1, 2), 'O2': (1, 3), 'O3': (1, 0), 'O4': (None, 2), 'O5': (1, 7), 'O6': (1, None)}


    def _goal(name):
        return f'CNV S5 {name}'


    def mission():
        goals, strings = [], {}
        for name, title in GOALS:
            key = f'MISSIONOBJ:CNVS5_{name}'
            strings[key], strings[key + '_DESC'] = title, f'探针目标 {name}：{title}'
            goals.append(Goal(_goal(name), key, key + '_DESC', bonus=name == 'O6', at=None))
        m = Mission(name='CampScr5', map=probe_border, objectives=goals, facts={})
        m.strings.update(strings)
        m.put(TANK, 'line', 0.0, 0.0, angle=0.0, name='UNIT - CNV S5 Tank', role='tank')
        m.waypoint('east', 'CNV S5 East', 'line', 600.0, 0.0)
        return m


    def _at(t, key, secs, actions):
        timer = f'Test {key} Timer'
        t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                      Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


    def goals(m):
        t = Test()
        tank, east = m.role('tank').name, m.mark('east')
        first = [('SET_MISSION_OBJECTIVE_STATUS', _goal(n), s) for n, (s, _) in STEPS.items() if s is not None]
        second = [('SET_MISSION_OBJECTIVE_STATUS', _goal(n), s) for n, (_, s) in STEPS.items() if s is not None]
        first += [('LINK_MISSION_OBJECTIVE_TO_OBJECT', _goal('O1'), tank, 1),
                  ('LINK_MISSION_OBJECTIVE_TO_OBJECT', _goal('O2'), tank, 1),
                  ('LINK_MISSION_OBJECTIVE_TO_WAYPOINT', _goal('O6'), east, 1)]
        second.append(('LINK_MISSION_OBJECTIVE_TO_OBJECT', _goal('O2'), tank, 0))
        t.counters.append(('CNV_S5_Step', '阶段'))
        t.scripts.append(Script('Test - step 0', [], [('SET_COUNTER', 'CNV_S5_Step', 0)]))
        _at(t, 'one', STEP1, first + [('SET_COUNTER', 'CNV_S5_Step', 1)])
        _at(t, 'two', STEP2, second + [('SET_COUNTER', 'CNV_S5_Step', 2)])
        t.expect += [('阶段', STEP2 + 2, '==', 2)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1.0, sheet=False, lines=1))]
        return t


    MISSION = {'engine_scripts5': mission}
    CHECKS = {'engine_scripts5': {'goals': goals}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def movie():
    """Movie probe checks (the movie scene in scenes.py), read off the counters:

    play: CNVTEST01 starts in the radar window at `radar at` s, CNVTEST02 full screen at `full at` s. 雷达帧数 / 全屏帧数 count
      the frames from the start till HAS_FINISHED_VIDEO holds, 雷达播完 / 全屏播完 are 1 from then on (radar only: see below).
      A radar clip the game plays runs its own length (4 s); one it cannot find is finished at once. The frame a second into
      each clip is looked at (the picture: the colour bar, the square, CNV TEST nnn). The mission is still running at the
      end (the counters can be read): the game did not crash.
    """
    from parts import Script, Test

    RUN = 30.0


    def play(m):
        t = Test()
        r, f = m.facts['radar at'], m.facts['full at']
        t.counters += [('CNV_Movie_RFrames', '雷达帧数'), ('CNV_Movie_RDone', '雷达播完'),
                       ('CNV_Movie_FFrames', '全屏帧数'), ('CNV_Movie_FDone', '全屏播完')]
        t.scripts += [
            Script('Test - radar timer', [], [('SET_MILLISECOND_TIMER', 'CNV Movie Radar', r)]),
            Script('Test - radar', [('TIMER_EXPIRED', 'CNV Movie Radar')],
                   [('MOVIE_PLAY_RADAR', 'CNVTEST01'), ('SET_FLAG', 'CNV Movie RPlayed', 1)]),
            Script('Test - radar playing', [('FLAG', 'CNV Movie RPlayed', 1), ('FLAG', 'CNV Movie RFinished', 0)],
                   [('INCREMENT_COUNTER', 1, 'CNV_Movie_RFrames')], once=False),
            Script('Test - radar finished', [('FLAG', 'CNV Movie RPlayed', 1), ('HAS_FINISHED_VIDEO', 'CNVTEST01')],
                   [('SET_FLAG', 'CNV Movie RFinished', 1), ('SET_COUNTER', 'CNV_Movie_RDone', 1)]),
            Script('Test - full timer', [], [('SET_MILLISECOND_TIMER', 'CNV Movie Full', f)]),
            Script('Test - full', [('TIMER_EXPIRED', 'CNV Movie Full')],
                   [('MOVIE_PLAY_FULLSCREEN', 'CNVTEST02', 0), ('SET_FLAG', 'CNV Movie FPlayed', 1)]),
            Script('Test - full playing', [('FLAG', 'CNV Movie FPlayed', 1), ('FLAG', 'CNV Movie FFinished', 0)],
                   [('INCREMENT_COUNTER', 1, 'CNV_Movie_FFrames')], once=False),
            Script('Test - full finished', [('FLAG', 'CNV Movie FPlayed', 1), ('HAS_FINISHED_VIDEO', 'CNVTEST02')],
                   [('SET_FLAG', 'CNV Movie FFinished', 1), ('SET_COUNTER', 'CNV_Movie_FDone', 1)])]
        # bench 2026-11-01: the radar clip counts 63 frames (4 s at 15 a second) and HAS_FINISHED_VIDEO holds; the full-screen
        # clip is on screen (the picture, counters hidden meanwhile) but HAS_FINISHED_VIDEO never holds for it -- retail
        # uses that condition for its radar clips only and waits for the full-screen ones with a timer -- so full screen is
        # judged by the picture and by the mission running on after it (the counter goes on counting)
        t.expect += [('雷达播完', RUN - 3, '==', 1), ('雷达帧数', RUN - 3, '>=', 50), ('雷达帧数', RUN - 3, '<=', 75),
                     ('全屏帧数', RUN - 3, '>=', 100)]
        t.bench = [('bench_watch', dict(seconds=r + 1.5, every=1, sheet=False, lines=len(t.counters))),
                   ('bench_look', dict(note='the radar window: CNV TEST movie (colour bar, square, frame number)?')),
                   ('bench_watch', dict(seconds=f - r - 2.8, every=1, sheet=False, lines=len(t.counters))),
                   ('bench_look', dict(note='full screen: CNV TEST movie over the whole screen? (the mission runs ~2 s ahead)')),
                   ('bench_watch', dict(seconds=RUN - f + 1.3, every=1, sheet=False, lines=len(t.counters)))]
        return t


    RETAIL = (('A02TH06', 'A'), ('J01TH05', 'B'))      # the game's own radar clips: 454 / 258 frames at 23.976 (VP6 header)


    def retail(m):
        """retail: two of the game's own radar clips, one after the other -- A02TH06 at `radar at` s, J01TH05 as soon as
        HAS_FINISHED_VIDEO holds for the first. 原版A帧数 / 原版B帧数 count the frames from each play till it holds. Asks
        whether a retail clip reads finished after its own length (the simulator, Sim.video_len, says 18.9 s = 284 frames
        and 10.8 s = 161) or earlier: a02 / j01's objectives hang on these clips (engine line A round 110).
        Bench 2026-11-09 (run CampMovieRetail_mcp_1109_033257): A02TH06 plays in the radar window (Lisa) from s2.2 and is
        still on screen at s39.8; HAS_FINISHED_VIDEO never held (621 frames by s42), so B never started -- FAIL. Retail
        a02 lights its objective 2 ~16 s after the HUD comes back with this clip in the chain, so the game does finish it
        there. It was the run: the bench ran the mission at x8 / x5.7 and a retail clip plays in real time (18.9 real s
        = 100+ mission s). At x1 (round 111: build.py movie --check retail, then bench_start + bench_watch by hand, the
        server's own driving is x1) A finished at 291 frames, B at 169: both PASS, a retail clip runs its header's length
        -- Sim.video_len reads it from the game's Data/Movies. cnv_check runs this at x8: judge it only at x1."""
        t = Test()
        r = m.facts['radar at']
        t.scripts.append(Script('Test - retail timer', [], [('SET_MILLISECOND_TIMER', 'CNV Movie Retail', r)]))
        start = [('TIMER_EXPIRED', 'CNV Movie Retail')]
        for clip, k in RETAIL:
            t.counters += [(f'CNV_Movie_{k}Frames', f'原版{k}帧数'), (f'CNV_Movie_{k}Done', f'原版{k}播完')]
            t.scripts += [
                Script(f'Test - retail {k}', start, [('MOVIE_PLAY_RADAR', clip), ('SET_FLAG', f'CNV Movie {k}Played', 1)]),
                Script(f'Test - retail {k} playing', [('FLAG', f'CNV Movie {k}Played', 1), ('FLAG', f'CNV Movie {k}Fin', 0)],
                       [('INCREMENT_COUNTER', 1, f'CNV_Movie_{k}Frames')], once=False),
                Script(f'Test - retail {k} finished', [('FLAG', f'CNV Movie {k}Played', 1), ('HAS_FINISHED_VIDEO', clip)],
                       [('SET_FLAG', f'CNV Movie {k}Fin', 1), ('SET_COUNTER', f'CNV_Movie_{k}Done', 1)])]
            start = [('FLAG', f'CNV Movie {k}Fin', 1)]
        run = r + 19.0 + 11.0 + 6.0
        t.expect += [('原版A播完', run - 2, '==', 1), ('原版A帧数', run - 2, '>=', 270), ('原版A帧数', run - 2, '<=', 300),
                     ('原版B播完', run - 2, '==', 1), ('原版B帧数', run - 2, '>=', 150), ('原版B帧数', run - 2, '<=', 175)]
        t.bench = [('bench_watch', dict(seconds=r + 3.0, every=1, sheet=False, lines=len(t.counters))),
                   ('bench_look', dict(note='the radar window: a retail talking head (A02TH06)?')),
                   ('bench_watch', dict(seconds=run - r - 3.0, every=2, sheet=False, lines=len(t.counters)))]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'movie': {'play': play, 'retail': retail},
    }
    return dict(CHECKS=CHECKS)


def scene():
    """Scene tests (scene in scenes.py). Counted, each latched at 1 once it happened: the camera got to the north
    base in phase 2's 过场 (CAMERA_ENTERED_AREA; phase 1's to the harbour: bench 2026-10-27, counted 1 -- four counter
    lines are all that fit), each goal shown (its shown flag), and
    anything shown too early -- the timed goal before phase 2's 过场 handed the input back, the bonus before the test
    script sent the dog. The order is counted, not the second: the bench's seconds start some seconds after the mission's
    (bench 2026-10-27, ~8).

    look: both scenes take the camera where they say; the timed goal is shown after the hand-back; the bonus once the dog
      (sent by test script SEND_AFTER past phase 2's hand-back) got to the convoy start; nothing too early. The frames
      while phase 2's scene runs show the letterbox and the whole map.
    """
    from parts import Script, Test, square

    SEND_AFTER, RUN = 8.0, 75.0
    CAMERA = 500.0                                  # half-side of the area round a place the camera must enter


    def latch(t, counter, label, when):
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)]))
        t.scripts.append(Script(f'Test - {counter}', when, [('SET_COUNTER', counter, 1)]))


    def look(m):
        t = Test()
        t.areas['Test Harbour'] = square(*m.site('harbour'), CAMERA)
        t.areas['Test Camp'] = square(*m.site('north base'), CAMERA)
        latch(t, 'Test Camera 2', '镜头到了北营', [('FLAG', 'CNV_SC_Phase_2', 1), ('CAMERA_ENTERED_AREA', 'Test Camp')])
        latch(t, 'Test Timed', '定时目标亮了', [('FLAG', 'CNV_SC_Objective01_Shown', 1)])
        latch(t, 'Test Near', '奖励目标亮了', [('FLAG', 'CNV_SC_Bonus01_Shown', 1)])
        t.counters.append(('Test Early', '亮早了'))
        t.scripts += [Script('Test - Test Early zero', [], [('SET_COUNTER', 'Test Early', 0)]),
                      Script('Test - early timed', [('FLAG', 'CNV_SC_Objective01_Shown', 1), ('FLAG', 'CNV_SC_Scene_2', 0)],
                             [('SET_COUNTER', 'Test Early', 1)]),
                      Script('Test - early bonus', [('FLAG', 'CNV_SC_Bonus01_Shown', 1), ('FLAG', 'Test_Sent', 0)],
                             [('SET_COUNTER', 'Test Early', 1)])]
        m.waypoint('test convoy start', 'Test convoy start', 'convoy start')
        t.scripts += [Script('Test - send timer', [('FLAG', 'CNV_SC_Scene_2', 1)],
                             [('SET_MILLISECOND_TIMER', 'Test - send', SEND_AFTER)]),
                      Script('Test - send', [('TIMER_EXPIRED', 'Test - send')],
                             [('SET_FLAG', 'Test_Sent', 1), ('MOVE_NAMED_UNIT_TO', m.role('dog').name,
                                                              m.mark('test convoy start'))])]
        t.expect += [('镜头到了北营', 1, 'ever==', 1), ('定时目标亮了', 1, 'ever==', 1),
                     ('奖励目标亮了', 1, 'ever==', 1), ('亮早了', 1, '==', 0)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=len(t.counters)))]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'scene': {'look': look},
    }
    return dict(CHECKS=CHECKS)


def voice():
    """Voice probe checks (voice in scenes.py), read off the counters:

    play: the line played at `play at` s; 播放帧数 counts the frames from then till HAS_FINISHED_AUDIO holds, 播完 is 1
      from then on. A line the game plays runs ~4.8 s (~70 frames at 15 a second); one it cannot find is finished at
      once (a frame or two). The frame a second after the start is looked at for the subtitle.

    Bench 2026-10-29: the audio is read from data\\static.12\\cdata -- voice_bench_s (static only) finished in 4 frames,
    voice_bench_12 and voice_bench (both) played; the subtitle came up by itself (CampVoice12Play frame 5). The 4.8 s
    line took 212 frames to finish, at 24 kHz and again at 48 kHz (75c5c90): not the sample rate. The control (`ref`,
    retail's MA01_AlliedIntel24, 4.34 s) took 190: 44 frames per second of audio for both (44.2 and 43.8), so a line
    plays at its own length and the pack is right. Why an audio second is 44 script frames when a 10 s timer is 150
    (15 a second) is not known (the bench holds the game between calls: the audio may run on in real time); so the
    audio's frames are never converted to mission seconds, only compared with the control's. Expected: frames within
    15% of 44 x the line's length (bench 2026-10-30: play 213, ref 190, both PASS).
    """
    from parts import Script, Test

    RUN = 20.0
    FRAMES_PER_S = 44.0                             # per second of audio (bench 2026-10-30: 212 / 4.8, 190 / 4.34)
    TOLERANCE = 0.15
    LINE_SECONDS = 4.8                              # CNV_TEST_001 (the pack's 115200 samples at 24 kHz)
    REFERENCE_SECONDS = 4.34
    REFERENCE = 'MA01_AlliedIntel24'                # a retail mission line: the control for the same check


    def play(m):
        return _play(m, next(iter(m.voice.events)), LINE_SECONDS)


    def ref(m):
        """The same check on a retail line: the frames a line of that length takes with nothing of ours in it."""
        return _play(m, REFERENCE, REFERENCE_SECONDS)


    def _play(m, line, seconds):
        t = Test()
        frames = FRAMES_PER_S * seconds
        at = m.facts['play at']
        t.counters += [('CNV_Voice_Frames', '播放帧数'), ('CNV_Voice_Done', '播完')]
        t.scripts += [
            Script('Test - play timer', [], [('SET_MILLISECOND_TIMER', 'CNV Voice Play', at)]),
            Script('Test - play', [('TIMER_EXPIRED', 'CNV Voice Play')],
                   [('PLAY_SOUND_EFFECT', line), ('SET_FLAG', 'CNV Voice Played', 1)]),
            Script('Test - playing', [('FLAG', 'CNV Voice Played', 1), ('FLAG', 'CNV Voice Finished', 0)],
                   [('INCREMENT_COUNTER', 1, 'CNV_Voice_Frames')], once=False),
            Script('Test - finished', [('FLAG', 'CNV Voice Played', 1), ('HAS_FINISHED_AUDIO', line)],
                   [('SET_FLAG', 'CNV Voice Finished', 1), ('SET_COUNTER', 'CNV_Voice_Done', 1)])]
        t.expect += [('播完', RUN - 3, '==', 1),
                     ('播放帧数', RUN - 3, '>=', frames * (1 - TOLERANCE)),
                     ('播放帧数', RUN - 3, '<=', frames * (1 + TOLERANCE))]
        t.bench = [('bench_watch', dict(seconds=at + 1, every=1, sheet=False, lines=len(t.counters))),
                   ('bench_look', dict(note='the subtitle of CNV_TEST_001 at the bottom?')),
                   ('bench_watch', dict(seconds=RUN - at - 1, every=1, sheet=False, lines=len(t.counters)))]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'voice_bench': {'play': play},
        'voice_bench_s': {'play': play},
        'voice_bench_12': {'play': play, 'ref': ref},
    }
    return dict(CHECKS=CHECKS)


BENCHES = (engine_camera, engine_caption, engine_dialog, engine_eyes, engine_joypad, engine_letterbox,
           engine_markobj, engine_mousehud, engine_radar, engine_scripts5, movie, scene, voice)
