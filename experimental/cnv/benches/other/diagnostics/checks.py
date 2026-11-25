"""Diagnostics bench checks."""


def engine_cmd():
    """Engine line D round 60 (handoff-d ④ "connection"): a program outside the game gives the running game an order, the
    game carries it out. The write path: ra3ext's CNVCmd module (carrier `<DeletionUpdate id="ModuleTag_CNVCmd"/>` on a
    copy of the conscript) looks every frame for ra3ext_cmd.txt in the run folder, sets the map's script counter named in
    it and deletes the file. The map's own script does the rest: Cmd_Call >= 1 -> three GIs at 'Test Drop', Cmd_Done + 1,
    Cmd_Call back to 0. The sender is experimental/cnv/ext_send.py, started BEFORE the check (it waits for the run's
    'cmd: listening' line, then for DELAY seconds, then writes `set Cmd_Call 1`):

      python -I -X utf8 experimental/cnv/ext_send.py --after 8 "set /Cmd_Call 1"    (background; "Cmd_Call" is the same key)
      cnv_check engine_cmd a

    Counter names have a scope: a bare name in a map script is its script list owner's (here 'Player_1'), the outside's
    bare name is the empty scope. So the map names the shared ones '/Cmd_Call', '/Cmd_Done' (the empty scope), and the
    outside reads the map's own bare 'Cmd_Time' as 'Player_1/Cmd_Time' (case matters: 'player_1/...' is another counter).

    Counters: 援军 (GIs the player owns), 命令 (/Cmd_Call), 已执行 (/Cmd_Done), 秒 (Cmd_Time, the map's clock). The control
    is the start: no GI before the order; without the sender none ever comes.
    Bench 2026-11-11 CampCmdA_mcp_1111_220230 PASS: sent at s20 (frame 331), 命令 1 at s20, 援军 3 / 已执行 1 from s21;
    `get Player_1/Cmd_Time` = 22 = the counter's 秒 at s20; the file was taken 0.10 s after it appeared.
    """
    import os

    import labpaths
    from maps import probe_range
    from parts import Mission, Script, Test, Unit, counted

    CONSCRIPT, HOST, GI, CALLS = 'SovietAntiInfantryInfantry', 'CNVCmdHost', 'AlliedAntiInfantryInfantry', 3
    RUN = 40.0


    def host_unit():
        x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Units', CONSCRIPT + '.xml'), encoding='utf-8').read()
        assert x.count(f'id="{CONSCRIPT}"') == 1 and x.count('<Behaviors>') == 1
        x = x.replace(f'id="{CONSCRIPT}"', f'id="{HOST}"').replace(f'EditorName="{CONSCRIPT}"', f'EditorName="{HOST}"')
        x = x.replace('<Behaviors>', (
            '<Behaviors>\n'
            '\t\t\t<DeletionUpdate id="ModuleTag_CNVCmd" MinFrames="1" MaxFrames="1"/>'
        ))
        return Unit(HOST, x, names=dict(unit=HOST),
                    what='动员兵的复制：多一个 ra3ext 的 CNVCmd 模块（每帧看命令文件、写地图计数器）',
                    params=dict(of=CONSCRIPT))


    def mission():
        m = Mission(name='CampCmd', map=probe_range, units=[host_unit()], facts={}, ext=True)
        m.put(HOST, 'base gun', 0.0, -120.0, side='p1', role='cmd host')
        m.put(GI, 'probe refinery', 0.0, 0.0, side='s1', role='gi model')   # publishes GI; s1's, far: not counted
        return m


    def cmd_test(m):
        t = Test()
        team = m.team('p1')
        t.waypoints['Test Drop'] = m.site('base gun', 0.0, 120.0)
        t.scripts += [
            Script('Test - clock start', [], [('SET_MILLISECOND_TIMER', 'Test Tick', 1.0)]),
            Script('Test - clock', [('TIMER_EXPIRED', 'Test Tick')],
                   [('INCREMENT_COUNTER', 1, 'Cmd_Time'), ('SET_MILLISECOND_TIMER', 'Test Tick', 1.0)], once=False),
            Script('Test - call', [('COUNTER', '/Cmd_Call', 3, 1)],
                   [('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', GI, team, 'Test Drop')] * CALLS +
                   [('INCREMENT_COUNTER', 1, '/Cmd_Done'), ('SET_COUNTER', '/Cmd_Call', 0)], once=False)]
        counted('CNV_Cmd_GI', '援军', t, template=GI)
        t.counters += [('/Cmd_Call', '命令'), ('/Cmd_Done', '已执行'), ('Cmd_Time', '秒')]
        t.expect = [('援军', 1, '==', 0, 5.0), ('已执行', 1, '==', 0, 5.0),
                    ('援军', 5, 'ever==', CALLS, RUN), ('已执行', 5, 'ever==', 1, RUN)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
        return t


    MISSION = {'engine_cmd': mission}
    CHECKS = {'engine_cmd': {'a': cmd_test}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_ext():
    """Engine line D, stage 2 (ADR 0027/0028): does a module of ra3ext.dll run inside a mission? The probe unit is a copy of
    retail's conscript with one more module, written as the carrier `<DeletionUpdate id="ModuleTag_CNVLog" MinFrames=30
    MaxFrames=40/>`: with ra3ext injected, its create sees the tag ModuleTag_CNVLog and builds our CNVLog module instead
    (an update every frame, one log line every 30 updates, 40 lines at most) -- the unit lives on; without it, the carrier is
    the real DeletionUpdate and the unit is deleted 30..40 frames after it appears.

      engine_ext     Mission(ext=True)   the build writes ra3ext.allow, the bench starts the game through ra3ext_launch
      engine_extoff  Mission(ext=False)  the same mission, a plain start: the control

    On the range probe map, at 'base gun' (the player's): PROBES probe units and one plain conscript (the counter's own
    control: it stays 1 either way). Counters: 探针 (probes the player owns), 对照 (plain conscripts). Every second.
    The dll's own lines (ra3ext loaded / create / update) are in the run folder's ra3ext.log; cnv_check prints their count.
    """
    import os

    import labpaths
    from maps import probe_range
    from parts import Mission, Test, Unit, counted

    CONSCRIPT, PROBE, PROBES = 'SovietAntiInfantryInfantry', 'CNVExtProbe', 2
    EVERY, LINES, RUN = 30, 40, 20.0


    def _sub1(x, old, new):
        assert x.count(old) == 1, (old[:60], x.count(old))
        return x.replace(old, new, 1)


    def probe_unit():
        x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Units', CONSCRIPT + '.xml'), encoding='utf-8').read()
        x = _sub1(x, f'id="{CONSCRIPT}"', f'id="{PROBE}"')
        x = x.replace(f'EditorName="{CONSCRIPT}"', f'EditorName="{PROBE}"')
        x = _sub1(x, '<Behaviors>', (
            f'<Behaviors>\n'
            f'\t\t\t<DeletionUpdate id="ModuleTag_CNVLog" MinFrames="{EVERY}" MaxFrames="{LINES}"/>'
        ))
        return Unit(PROBE, x, names=dict(unit=PROBE),
                    what=f'动员兵的复制（探针）：多一个 ra3ext 的 CNVLog 模块（载体 DeletionUpdate）；没注入时 {EVERY}..{LINES} 帧后被删',
                    params=dict(of=CONSCRIPT, every=EVERY, lines=LINES))


    def mission(ext=True):
        m = Mission(name='CampExt' if ext else 'CampExtOff', map=probe_range, units=[probe_unit()], facts={}, ext=ext)
        for k in range(PROBES):
            m.put(PROBE, 'base gun', 40.0 * k - 20.0, 0.0, side='p1', role=f'probe {k + 1}')
        m.put(CONSCRIPT, 'base gun', 0.0, -60.0, side='p1', role='plain conscript')
        return m


    def ext_test(m, ext=True):
        t = Test()
        counted('CNV_Ext_Probe', '探针', t, template=PROBE)
        counted('CNV_Ext_Plain', '对照', t, template=CONSCRIPT)
        t.expect = [('对照', 3, '==', 1), ('探针', 3, '==', PROBES if ext else 0)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
        return t


    MISSION = {'engine_ext': mission, 'engine_extoff': lambda: mission(False)}
    CHECKS = {'engine_ext': {'a': ext_test}, 'engine_extoff': {'a': lambda m: ext_test(m, False)}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_kingref():
    """Level-line probe: does A4's Ghost King shoot a wall it is re-ordered against every frame (missions/kingref_bench.py)?
    Background: checks/a4.py smev (bench 2026-11-07) reproduced the old behaviour on the real map -- the King walks from the
    shore to the bridge either way, but with the attack order re-given every frame the wall's health stays 100; with it given
    once the King fires from the same spot. A's engine_reorder tank fires under every-frame orders, so what differs is the
    unit (King = JapanAntiVehicleVehicleTech3, a heavy tank) or the target (a SET_REF pick, not a name).

    The enemy (s1) King is made at 1 s at S; the wall W stands 900 north. Orders from 2 s:
      kone    named wall, the order once                         (control)
      kevery  named wall, the whole order every frame
      rone    unnamed wall picked with SET_REF at 1.5 s, the order once
      revery  unnamed wall, SET_REF once, the order every frame  (what A4 did)
      aref    like revery but the attacker is the Athena tank of A's probe (separates unit from target kind)
    Counters: 近墙 (the King in the square of half-side 170 round (0, 330)), 墙血 (the wall's health in percent: by name, or
    by the reference). bench_watch 45 s, every 2 s.
    """
    from parts import Script, Test, counted, square

    VARIANTS = ('kone', 'kevery', 'rone', 'revery', 'aref')
    ATK, WALL = 'UNIT - CNV Reo Atk', 'UNIT - CNV Reo Wall'
    REF = 'UNITRef - CNV Reo Nearest Wall'
    KING, ATHENA = 'JapanAntiVehicleVehicleTech3', 'AlliedAntiVehicleVehicleTech1'
    RUN = 45.0


    def frames(m):
        t = Test()
        v = VARIANTS[m.facts['variant']]
        p1 = m.player('p1')
        team = m.teams['Reo']
        named = v in ('kone', 'kevery')
        t.areas['Test Mid'] = square(*m.point('mid'), 150.0)
        t.areas['Test Near'] = square(*m.point('near'), 170.0)
        target = WALL if named else REF
        order = m.order('attack', [ATK], target, 's1', crew='Reo')
        timers = [('SET_MILLISECOND_TIMER', 'Test Make', 1.0), ('SET_MILLISECOND_TIMER', 'Test Pick', 1.5),
                  ('SET_MILLISECOND_TIMER', 'Test Go', 2.0)]
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1)] + timers))
        t.scripts.append(Script('Test - make', [('TIMER_EXPIRED', 'Test Make')],
                                [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', ATK, ATHENA if v == 'aref' else KING,
                                  m.team('s1'), m.mark('s')), ('UNIT_SET_TEAM', ATK, team)]))
        if not named:
            t.scripts.append(Script('Test - pick', [('TIMER_EXPIRED', 'Test Pick')],
                                    [('SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER', 'CNV_ReoWall', p1,
                                      m.team('s1'), REF)]))
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Go')], order, once=v in ('kone', 'rone')))
        counted('CNV_Reo_N', '近墙', t, named=ATK, area='Test Near')
        counted('CNV_Reo_H', '墙血', t, health=WALL if named else REF)
        t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {f'kingref_{v}': {'frames': frames} for v in VARIANTS}
    return dict(CHECKS=CHECKS)


def probe():
    """Engine probe (missions/probe_bench.py), read off the counters:

    engine: the difficulty counter shows 1, 2 or 3 (exactly one of the three copies ran: the bench starts on whatever
      difficulty the profile has); the money counter shows the money set; the mission runs past the autosave.

    The border is checked by hand, no counter sees it (bench 2026-10-25): bench_camera east of the canal does not move
    before `open at` (west of it does), and does after. A unit a script moves crosses the border at any time -- the
    first version of this check sent one east and counted it, and it got there before the border opened.
    """
    from parts import NOT, Obj, Script, Test, counted, kindof, square

    RUN = 15.0                                      # past the autosave (5 s), margin
    STOP, DOOM = 10.0, 6.0                          # align: the NOT counter stops; the victim is killed, the other deleted


    def engine(m):
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.counters += [('CNV_Probe_Difficulty', '难度'), ('CNV_Probe_Money', '资金')]
        t.expect += [('难度', 3, '>=', 1), ('难度', 3, '<=', 3), ('资金', 3, '==', m.facts['money']),
                     ('资金', RUN - 3, 'ever==', m.facts['money'])]
        t.bench = [('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=len(t.counters)))]
        return t


    def align(m):
        """The simulator's engine guesses (sim.ALIGN), each as a counter that reads what the simulator assumes -- a FAIL is a
        guess to correct, the readings say the engine's way:
          frame rate + inverted: 帧数 counts every frame; 取反帧数 counts while flag CNV Probe Stopped is NOT set, the
            flag set at STOP s; 取反计时 counts while timer CNV Probe Stop has NOT expired -- plain negation: both stop
            near STOP x the logic rate, the inverted bit ignored: they stay 0 till STOP and run on after; the rate is 帧数
            per mission second (bench 2026-10-28: ~15 a second; 2026-10-29, the names split: 取反帧数 and 取反计时 both 0
            till STOP, then counting -- the game ignores the inverted bit of a .map's scripts, our bytes being retail's;
            the compiler reads NOT off a flag since, parts.unnot);
          timer unset: TIMER_EXPIRED of a timer nobody sets is false."""
        t = Test()
        t.counters += [('CNV_Probe_Frames', '帧数'), ('CNV_Probe_NotFrames', '取反帧数'),
                       ('CNV_Probe_NotTimer', '取反计时'), ('CNV_Probe_Unset', '未设计时器')]
        t.scripts += [
            Script('Test - stop timer', [], [('SET_MILLISECOND_TIMER', 'CNV Probe Stop', STOP)]),
            Script('Test - frames', [], [('INCREMENT_COUNTER', 1, 'CNV_Probe_Frames')], once=False),
            Script('Test - not frames', [('FLAG', 'CNV Probe Stopped', 1, NOT)],
                   [('INCREMENT_COUNTER', 1, 'CNV_Probe_NotFrames')], once=False),
            Script('Test - not timer', [('TIMER_EXPIRED', 'CNV Probe Stop', NOT)],
                   [('INCREMENT_COUNTER', 1, 'CNV_Probe_NotTimer')], once=False),
            Script('Test - stop', [('TIMER_EXPIRED', 'CNV Probe Stop')], [('SET_FLAG', 'CNV Probe Stopped', 1)]),
            Script('Test - unset', [('TIMER_EXPIRED', 'CNV Probe Never')], [('SET_COUNTER', 'CNV_Probe_Unset', 1)])]
        t.expect += [('取反帧数', 2, '>=', 1), ('取反计时', 2, '>=', 1), ('未设计时器', 2, '==', 0)]
        t.bench = [('bench_watch', dict(seconds=RUN + 5, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def death(m):
        """More of the simulator's guesses (sim.ALIGN), read the same way:
          death linger, health of the dead: the victim killed at DOOM s, 1 in 死者在区内 while the engine still has it in
            the area (the simulator: LINGER 3 s), 死者血量 0 once dead;
          deleted: the other one deleted at DOOM s, NAMED_DESTROYED of it true from the next frame (删除算摧毁)."""
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        for k, name in ((0, 'UNIT - Probe Victim'), (1, 'UNIT - Probe Gone')):
            t.objects.append(Obj('AlliedAntiVehicleVehicleTech1', *m.site('west field', 150, -90 + 60 * k), name=name,
                                 site='west field'))
        t.areas['Test field'] = square(*m.site('west field'), 450)
        t.scripts += [
            Script('Test - doom timer', [], [('SET_MILLISECOND_TIMER', 'CNV Probe Doom', DOOM)]),
            Script('Test - doom', [('TIMER_EXPIRED', 'CNV Probe Doom')],
                   [('NAMED_KILL', 'UNIT - Probe Victim'), ('NAMED_DELETE', 'UNIT - Probe Gone')])]
        counted('CNV_Probe_Linger', '死者在区内', t, named='UNIT - Probe Victim', area='Test field')
        counted('CNV_Probe_DeadHealth', '死者血量', t, health='UNIT - Probe Victim')
        t.counters.append(('CNV_Probe_GoneDead', '删除算摧毁'))
        t.scripts += [Script('Test - gone zero', [], [('SET_COUNTER', 'CNV_Probe_GoneDead', 0)], once=False),
                      Script('Test - gone dead', [('NAMED_DESTROYED', 'UNIT - Probe Gone')],
                             [('SET_COUNTER', 'CNV_Probe_GoneDead', 1)], once=False)]
        # the player's force, the way a "fewer than N" reinforcement would count it (retail Brighton Beach, Havana:
        # SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER per template, every frame): the map's guardian and the two here, then
        # the one left once these are killed and deleted; the enemy's guardian-free army does not come into it
        t.counters.append(('CNV_Probe_OwnGuardians', '我方守护者'))
        t.scripts.append(Script('Test - own guardians', [], [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER',
                                                              'AlliedAntiVehicleVehicleTech1', m.player('p1'),
                                                              'CNV_Probe_OwnGuardians')], once=False))
        # bench 2026-10-28: out of the area the reading the kill shows in (no linger; the simulator guessed 3 s)
        t.expect += [('死者在区内', 2, '==', 1, DOOM - 2), ('死者在区内', DOOM + 1, '==', 0),
                     ('死者血量', DOOM + 1, '==', 0), ('删除算摧毁', DOOM + 1, '==', 1),
                     ('我方守护者', 2, '==', 3, DOOM - 1), ('我方守护者', DOOM + 1, '==', 1)]
        t.bench = [('bench_watch', dict(seconds=RUN + 5, every=1, sheet=False, lines=len(t.counters)))]
        return t


    def reveal(m):
        """Border reveal: a permanent reveal made while the border is west of the canal (at 2 s), the whole map opened at
        `open at` -- the simulator takes the reveal to cover the new ground too. Read by hand off the frame east of the
        canal after the opening: ground in the clear, or black (shrouded)."""
        t = Test()
        t.scripts += [Script('Test - reveal timer', [], [('SET_MILLISECOND_TIMER', 'CNV Probe Reveal', 2.0)]),
                      Script('Test - reveal', [('TIMER_EXPIRED', 'CNV Probe Reveal')],
                             [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
        t.counters.append(('CNV_Probe_Money', '资金'))
        t.expect.append(('资金', 3, '==', m.facts['money']))
        t.bench = [('bench_watch', dict(seconds=m.facts['open at'] + 3, every=5, sheet=False, lines=1)),
                   ('bench_camera', dict(x=4400.0, y=3400.0))]          # east of the canal; it returns the frame
        return t


    def both(m, first='Mission Won', then='Mission Lost'):
        """Won and lost in one frame (sim 'both endings': the simulator takes the later one, the Generals way): both flags
        set by one script at 5 s, `first` then `then`; the frame after says which the game made of it."""
        t = Test()
        t.scripts += [Script('Test - end timer', [], [('SET_MILLISECOND_TIMER', 'CNV Probe End', 5.0)]),
                      Script('Test - both', [('TIMER_EXPIRED', 'CNV Probe End')],
                             [('SET_FLAG', first, 1), ('SET_FLAG', then, 1)])]
        t.counters.append(('CNV_Probe_Money', '资金'))
        t.expect.append(('ENDED', 5, '==', 1))
        t.bench = [('bench_watch', dict(seconds=12, every=2, sheet=False, lines=1)),
                   ('bench_look', dict(note=f'{first} then {then}: which ending?'))]
        return t


    def count(m):
        """Whose units the area conditions count (bench 2026-10-25: a kind-in-area count for the enemy came out as every
        player's): the player's guardian and two more of ours at the west field, two enemy warriors far off at the north
        base; the enemy's count in the west field, three ways, against the player's own."""
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        for k in (1, 2):
            t.objects.append(Obj('AlliedAntiVehicleVehicleTech1', *m.site('west field', 250, 30 + 60 * k), site='west field'))
            t.objects.append(Obj('JapanAntiInfantryInfantry', *m.site('north base', 60 * k, 0), side='s1',
                                 site='north base'))
        t.areas['Test field'] = square(*m.site('west field'), 450)
        s1 = m.player('s1')
        counted('CNV_Probe_KindP1', '我方能打的', t, kind=kindof('CAN_ATTACK'), area='Test field')
        counted('CNV_Probe_KindS1', '敌方能打的', t, kind=kindof('CAN_ATTACK'), area='Test field', player=s1)
        counted('CNV_Probe_TypeS1', '敌方守护者', t, template='AlliedAntiVehicleVehicleTech1', area='Test field', player=s1)
        t.counters.append(('CNV_Probe_EnterS1', '敌方进入'))
        t.scripts += [Script('Test - enter zero', [], [('SET_COUNTER', 'CNV_Probe_EnterS1', 0)], once=False),
                      Script('Test - enter', [('SKIRMISH_PLAYER_HAS_UNITS_IN_AREA', s1, 'Test field')],
                             [('SET_COUNTER', 'CNV_Probe_EnterS1', 1)], once=False)]
        t.expect += [('我方能打的', 3, '==', 3), ('敌方能打的', 3, '==', 0), ('敌方守护者', 3, '==', 0), ('敌方进入', 3, '==', 0)]
        t.bench = [('bench_watch', dict(seconds=12, every=3, sheet=False, lines=len(t.counters)))]
        return t


    def unset(m):
        """Timers not yet set, two ways (docs/engine/production.md and sim.ALIGN 'timer unset' disagreed): 未设计时器 is
        1 once TIMER_EXPIRED holds for a timer no script names elsewhere; 待设计时器 the same for a timer a script would set
        but whose condition (a flag nobody sets) never holds -- the bench production b's case. Read every second from
        the start (帧数 counts the frames). Engine source: a timer never started is not expired."""
        t = Test()
        t.counters += [('CNV_Probe_Unset', '未设计时器'), ('CNV_Probe_Pending', '待设计时器'), ('CNV_Probe_Tick', '帧数')]
        t.scripts += [
            Script('Test - tick', [], [('INCREMENT_COUNTER', 1, 'CNV_Probe_Tick')], once=False),
            Script('Test - set never', [('FLAG', 'CNV Probe Nobody', 1)],
                   [('SET_MILLISECOND_TIMER', 'CNV Probe Pending', 5.0)]),
            Script('Test - unset', [('TIMER_EXPIRED', 'CNV Probe Never')], [('SET_COUNTER', 'CNV_Probe_Unset', 1)]),
            Script('Test - pending', [('TIMER_EXPIRED', 'CNV Probe Pending')], [('SET_COUNTER', 'CNV_Probe_Pending', 1)])]
        t.expect += [('未设计时器', 2, '==', 0), ('待设计时器', 2, '==', 0),
                     ('未设计时器', RUN - 3, '==', 0), ('待设计时器', RUN - 3, '==', 0)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'probe': {'engine': engine, 'count': count, 'align': align, 'unset': unset, 'death': death, 'reveal': reveal, 'both': both, 'both2': lambda m: both(m, 'Mission Lost', 'Mission Won')},
        'probe_nosave': {'engine': engine},
    }
    return dict(CHECKS=CHECKS)


def render_war():
    """Render line probe (missions/render_bench.py; docs/research/rendering.md "第 0 步结果"): a battle that keeps going for
    the whole watch, under whatever renderer setup the game copy has (work/render/tools/switch.py).

    Every 2 s each side gets one of each of its kinds at its rear while it has fewer than TOP of its main tank, and every
    3 s both armies are told to attack-move to the other side's rear. Counters: 帧数 (+1 every script frame: logic frames
    since the start; against the watch's real seconds it is the logic rate), 守护者 / 铁锤 (each side's main tank left).
    """
    from parts import Script, Test, counted

    TOP, BIG, RUN = 24, 60, 120.0
    # the kinds each side gets, the same as missions/render_bench.py places (G5: a check does not import its mission);
    # the first is the side's main tank, the one counted
    ALLIED = ('AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryVehicle', 'AlliedAntiStructureVehicle',
              'AlliedAntiInfantryInfantry')
    SOVIET = ('SovietAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech3', 'SovietAntiStructureVehicle',
              'SovietAntiInfantryInfantry')


    def war(m, top=TOP):
        t = Test()
        p1, s1 = m.player('p1'), m.player('s1')
        west, east = m.mark('west rear'), m.mark('east rear')
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Order', 1.0),
                                                     ('SET_MILLISECOND_TIMER', 'Test Give', 2.0)]))
        t.counters.append(('CNV_Rw_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [], [('INCREMENT_COUNTER', 1, 'CNV_Rw_Frames')], once=False))
        counted('CNV_Rw_Allied', '守护者', t, template=ALLIED[0], player=p1)
        counted('CNV_Rw_Soviet', '铁锤', t, template=SOVIET[0], player=s1)
        t.scripts += [
            Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                   [('ATTACK_MOVE_TEAM_TO', m.team('p1'), east), ('ATTACK_MOVE_TEAM_TO', m.team('s1'), west),
                    ('SET_MILLISECOND_TIMER', 'Test Order', 3.0)], once=False),
            Script('Test - give west', [('TIMER_EXPIRED', 'Test Give'), ('COUNTER', 'CNV_Rw_Allied', 0, top)],
                   [('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', k, m.team('p1'), west) for k in ALLIED], once=False),
            Script('Test - give east', [('TIMER_EXPIRED', 'Test Give'), ('COUNTER', 'CNV_Rw_Soviet', 0, top)],
                   [('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', k, m.team('s1'), east) for k in SOVIET], once=False),
            Script('Test - give again', [('TIMER_EXPIRED', 'Test Give')], [('SET_MILLISECOND_TIMER', 'Test Give', 2.0)],
                   once=False)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {'render_war': {'war': war, 'big': lambda m: war(m, BIG)}}     # big: BIG of each main tank
    return dict(CHECKS=CHECKS)


def shikigami():
    """Shikigami tests, A against B on one map: at GUARD_AT group A's shikigami goes on guard, B's does not; at SHOOT_AT
    both groups' conscripts are ordered to shoot their VIP.

    cover: A's VIP comes through untouched while A's shikigami takes the fire; B's VIP is hit.
    """
    from parts import Script, Test, counted

    GUARD_AT, SHOOT_AT = 10.0, 11.0


    def bend(m):
        """shells: A's shikigami on guard at GUARD_AT, B's not; at SHOOT_AT both V4 launchers are ordered at their VIP.
        A's first rocket bends onto the shikigami and A's VIP is untouched, while B's first one hits B's VIP (bench
        2026-10-22: one V4 rocket kills a shikigami, so A's VIP falls to the next one -- hence the window)."""
        t = Test()
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('SET_MILLISECOND_TIMER', 'Test - guard timer', GUARD_AT),
                                                     ('SET_MILLISECOND_TIMER', 'Test - shoot timer', SHOOT_AT)]))
        t.scripts.append(Script('Test - guard', [('TIMER_EXPIRED', 'Test - guard timer')],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role('guard A').name, m.ability('guard A', 'guard'))]))
        t.scripts.append(Script('Test - shoot', [('TIMER_EXPIRED', 'Test - shoot timer')],
                                [('NAMED_ATTACK_NAMED', m.role(f'launcher {k}').name, m.role(f'vip {k}').name) for k in 'AB']))
        for k in 'AB':
            counted(f'Test VIP {k}', f'{k} 要人血量', t, health=m.role(f'vip {k}').name)
            counted(f'Test Guard {k}', f'{k} 式神血量', t, health=m.role(f'guard {k}').name)
        window = SHOOT_AT + 4                       # past the first rockets, before the second
        t.expect += [('A 要人血量', 0, '==', 100, window), ('A 式神血量', SHOOT_AT, 'ever<', 100, window),
                     ('B 要人血量', SHOOT_AT, 'ever<', 100, window)]
        t.bench = [('bench_watch', dict(seconds=40, every=3, sheet=False, lines=len(t.counters)))]
        return t


    def cover(m):
        t = Test()
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('SET_MILLISECOND_TIMER', 'Test - guard timer', GUARD_AT),
                                                     ('SET_MILLISECOND_TIMER', 'Test - shoot timer', SHOOT_AT)]))
        t.scripts.append(Script('Test - guard', [('TIMER_EXPIRED', 'Test - guard timer')],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role('guard A').name, m.ability('guard A', 'guard'))]))
        t.scripts.append(Script('Test - shoot', [('TIMER_EXPIRED', 'Test - shoot timer')],
                                [('NAMED_ATTACK_NAMED', s.name, m.role(f'vip {k}').name)
                                 for k in 'AB' for s in m.roles(f'shooter {k}')]))
        for k in 'AB':
            counted(f'Test VIP {k}', f'{k} 要人血量', t, health=m.role(f'vip {k}').name)
            counted(f'Test Guard {k}', f'{k} 式神血量', t, health=m.role(f'guard {k}').name)
        t.expect += [('A 要人血量', 0, '==', 100), ('A 式神血量', SHOOT_AT, 'ever<', 100),
                     ('B 要人血量', SHOOT_AT, 'ever<', 100)]
        t.bench = [('bench_watch', dict(seconds=35, every=3, sheet=False, lines=len(t.counters)))]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'shikigami': {'cover': cover},
        'shikigami_shells': {'bend': bend},
    }
    return dict(CHECKS=CHECKS)


BENCHES = (
    engine_cmd, engine_ext, engine_kingref, probe, render_war,
    shikigami,
)
