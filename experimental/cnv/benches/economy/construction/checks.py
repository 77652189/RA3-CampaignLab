"""Economy and construction checks, with their co-located scenes."""


def engine_assistplace_e():
    """E169: legal refinery placement, retail placement hint versus hint removal.

    Prediction from GenericRefineryPlacementHint.xml: a click 30 units from the
    ore's suggested refinery pad snaps to that pad with AssistedPlacementBehavior
    (SnappingDistance=50); without it the click stays offset. Both must produce
    one refinery. Region counts test this prediction; they do not certify facing,
    shroud eligibility, the exact snap radius or rejected-placement reasons.
    See work/re/e169_assistplace.md for observations and remaining gaps.
    MEASURED: both original and module-removal runs paid the queue (8000 left),
    but produced zero refineries and left the completion sentinel at zero.
    Both previews remained red. The original predictions below are retained;
    this recipe has not established a legal placement or a snapping rule.
    b (11-23, the camera put by the mission): the click is accepted; on puts the refinery within 20 of the pad turned
    to the node, off (same click) by the click in its default facing -- snapping seen; the sim replays no clicks.
    """
    import re
    import types
    from pathlib import Path

    import labpaths
    import resources
    from maps import probe_range
    from parts import Mission, Script, Test, Unit, counted, square
    from checks.engine_modulebatch import native

    PAD = (3000.0, 4200.0)
    CLICK = (3030.0, 4200.0)


    def mission(enabled=True):
        mp = types.ModuleType(probe_range.__name__)
        mp.__dict__.update(vars(probe_range))
        mp.OBJECTS = resources.objects(probe_range.FIELDS)
        mp.NODES = resources.RETAIL
        xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedRefinery.xml').read_text(encoding='utf-8-sig')
        if not enabled:
            xml, n = re.subn(r'<xi:include\s+href="DATA:Includes/GenericRefineryPlacementHint.xml"\s*/>', '', xml)
            assert n == 1
        refinery = Unit('AlliedRefinery', xml)
        yard = native('AlliedConstructionYard', 'Structures', 'CNVE169Yard')
        # native() expands the local time constant; a literal duration is not an expression.
        yard.xml = yard.xml.replace('="=2.0s"', '="2.0s"')
        yard.xml = yard.xml.replace('CommandSet="AlliedConstructionYardCommandSet"', 'CommandSet="CNVE169Menu"')
        yard.xml = yard.xml.replace('</AssetDeclaration>', '''
            <LogicCommandSet id="CNVE169Menu"><Cmd>Command_ConstructAlliedRefinery</Cmd></LogicCommandSet>
            </AssetDeclaration>''')
        yard.link += ['LogicCommandSet:CNVE169Menu']
        m = Mission(name='CampAsst' + ('On' if enabled else 'Off'), map=mp, units=[refinery, yard])
        m.facts['enabled'] = enabled
        m.spawns.add('AlliedRefinery')
        m.put(yard.id, 'probe refinery', -280, -260, role='yard', name='E169 Yard')
        m.put('AlliedPowerPlant', 'probe refinery', -480, -260, role='power', name='E169 Power')
        return m


    def check(m):
        t = Test()
        p1 = m.player('p1')
        t.counters = [('E169Age', '采样完成'), ('E169Money', '资金')]
        t.scripts = [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 10000)]),
                     Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'E169Money')], once=False)]
        t.areas['E169 Snap'] = square(*PAD, 8)
        counted('E169Total', '矿场总数', t, template='AlliedRefinery', player=p1)
        counted('E169Snap', '提示位数量', t, template='AlliedRefinery', area='E169 Snap', player=p1, most=2)
        # Freeze both region and total readings after 90 script frames with a refinery.
        for script in t.scripts[2:]:
            script.when.append(('COUNTER', 'E169Age', 0, 90))
        t.scripts.append(Script('Test - age', [('COUNTER', 'E169Total', 3, 1), ('COUNTER', 'E169Age', 0, 90)],
                                [('INCREMENT_COUNTER', 1, 'E169Age')], once=False))
        t.expect = [('采样完成', 0, 'ever==', 90), ('矿场总数', 0, 'ever==', 1),
                    ('提示位数量', 0, 'ever==', int(m.facts['enabled']))]
        watch = dict(every=1, sheet=False, lines=4)
        button = ('bench_click', dict(x=1137, y=323, world=False, look=False))
        t.bench = [('bench_start', dict(hold=False)),
                   ('bench_camera', dict(x=PAD[0], y=PAD[1], look=False)),
                   ('bench_click', dict(x=1120, y=252, world=False, look=False)),
                   ('bench_click', dict(x=1120, y=252, world=False, look=False)), button,
                   ('bench_watch', dict(watch, seconds=110, until='c2<=8000')), button,
                   ('bench_click', dict(x=CLICK[0], y=CLICK[1], look=False)),
                   ('bench_watch', dict(watch, seconds=100))]
        return t


    def exact(m):
        """b: a with the camera put on the pad by the mission (MOVE_CAMERA_TO at 1 s + bench_view: bench_camera's minimap
        click is off by ~100, twice the snap distance), every click looked at, and a second click 330 from the yard (its +y)
        -- a spot near the yard and far from the node -- for when the pad's leaves the cursor up: is the pad itself red?"""
        t = check(m)
        # where it stands, near the pad (20) or at the click (8), in place of the age and the pad's 8 (four lines fit)
        t.counters = [c for c in t.counters if c[0] not in ('E169Age', 'E169Snap')]
        t.areas.update({'E169 Near': square(*PAD, 20), 'E169 Click': square(*CLICK, 8)})
        counted('E169Near', '提示位20内', t, template='AlliedRefinery', area='E169 Near', player=m.player('p1'), most=2)
        counted('E169Click', '点击处数量', t, template='AlliedRefinery', area='E169 Click', player=m.player('p1'), most=2)
        on = int(m.facts['enabled'])
        t.expect = [('矿场总数', 0, 'ever==', 1), ('提示位20内', 0, 'ever==', on), ('点击处数量', 0, 'ever==', 1 - on)]
        from checks import engine_scripts8 as s8
        t.waypoints['E169 view'] = PAD
        s8.at(t, 'view', 1., [('MOVE_CAMERA_TO', 'E169 view', 0.5, 0.0, 1.0, 1.0)])
        x, y = m.site('probe refinery')
        # money is the first line now (the age left out): the sentinel reads c1
        steps = [(name, dict(kw, look=True) if name == 'bench_click' else
                  dict(kw, until=kw.get('until', '').replace('c2', 'c1')) if name == 'bench_watch' else kw)
                 for name, kw in t.bench]
        steps[1] = ('bench_view', dict(x=PAD[0], y=PAD[1], look=True))
        t.bench = steps[:-1] + [('bench_watch', dict(steps[-1][1], seconds=5)),
                                ('bench_click', dict(x=x - 280, y=y + 70, look=True)), steps[-1]]
        return t


    MISSION = {'assistpon': lambda: mission(True), 'assistpoff': lambda: mission(False)}
    CHECKS = {name: {'a': check, 'b': exact} for name in MISSION}
    CONTROLS = {'assistpoff': 'assistpon'}
    return dict(MISSION=MISSION, CHECKS=CHECKS, CONTROLS=CONTROLS)


def engine_bankcapture():
    """E147: ordinary engineer capture of neutral Swiss banks, module on/off.

    Retail XML predicts a 750 initial bonus and 5 every 15 game frames (1s).
    Both wallets start at zero; engineers enter normally at mission second 10.
    Frame-relative wallet samples distinguish the bonus from recurring income.
    Evidence bits: on/off captured with engineer consumed=1/2; pre-entry zero=4;
    on bonus=8; off initial zero=16; on +15/+30/+45/+60 frames=32/64/128/256;
    off +60 frames zero=512. Prediction: 1023 and final wallets 770/0.
    Travel time and first deposit phase are hypotheses, not fitted clock offsets.
    MEASURED 2026-11-15 PASS: f188=750/0, f206=755/0, f223=760/0,
    f242=765/0, f257=770/0; evidence reaches 1023 and stays there. Those are
    HUD observation frames; the evidence bits verify the exact relative samples.
    Only ordinary neutral capture is covered; recapture, caps, garrison and repair
    remain gaps. See work/re/e147_bankcapture.md.
    """
    import re
    from pathlib import Path

    import labpaths
    from maps import probe_range
    from parts import Mission, Script, Test, Unit


    def mission():
        m = Mission(name='CampBankE', map=probe_range, units=[])
        source = (Path(labpaths.SDK3) / 'SageXML/Civilian/Geneva_GE/Buildings/GE_SwissBank.xml').read_text(encoding='utf-8-sig')
        for tag, side, dx in [('on', 'p1', 0), ('off', 's2', 500)]:
            ident = 'CNVE147Bank' + tag
            xml = source.replace('id="GE_SwissBank"', 'id="' + ident + '"', 1)
            if tag == 'off':
                xml, n = re.subn(r'<AutoDepositUpdate\b.*?</AutoDepositUpdate>', '', xml, flags=re.S)
                assert n == 1
            m.units.append(Unit(ident, xml))
            m.put(ident, 'base gun', dx, 0, side='neutral', role='bank ' + tag, name='Bank ' + tag)
            m.put('AlliedEngineer', 'base gun', dx, -180, side=side, role='man ' + tag, name='Engineer ' + tag)
        return m


    def check(m):
        t = Test()
        frame, evidence = 'E147Frame', 'E147Evidence'
        t.counters = [(frame, '帧数'), ('E147Moneyon', '收入'),
                      ('E147Moneyoff', '对照'), (evidence, '证据')]
        start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                 ('SET_MILLISECOND_TIMER', 'E147Enter', 10.0)]
        for tag, side in [('on', 'p1'), ('off', 's2')]:
            start += [('PLAYER_SET_MONEY', m.player(side), 0),
                      ('UNIT_CHANGE_OBJECT_STATUS', m.role('man ' + tag).name, 'NO_ATTACK', 1)]
        t.scripts = [Script('Test - E147 start', [], start),
                     Script('Test - E147 frame', [], [('INCREMENT_COUNTER', 1, frame)], once=False)]
        t.scripts.append(Script('Test - E147 enter', [('TIMER_EXPIRED', 'E147Enter')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role('man ' + tag).name, m.role('bank ' + tag).name)
            for tag in ('on', 'off')]))
        for tag, side, bit in [('on', 'p1', 1), ('off', 's2', 2)]:
            money, age = 'E147Money' + tag, 'E147Age' + tag
            captured = [('NAMED_OWNED_BY_PLAYER', m.player(side), m.role('bank ' + tag).name),
                        ('NAMED_DESTROYED', m.role('man ' + tag).name)]
            t.scripts += [
                Script('Test - E147 wallet ' + tag, [],
                       [('SET_PLAYER_MONEY_TO_COUNTER', m.player(side), money)], once=False),
                Script('Test - E147 age ' + tag, captured,
                       [('INCREMENT_COUNTER', 1, age)], once=False),
                Script('Test - E147 captured ' + tag, captured, [('INCREMENT_COUNTER', bit, evidence)])]
            samples = [(1, 750, 8), (16, 755, 32), (31, 760, 64),
                       (46, 765, 128), (61, 770, 256)] if tag == 'on' else [(1, 0, 16), (61, 0, 512)]
            for at, amount, flag in samples:
                t.scripts.append(Script(f'Test - E147 sample {tag} {at}',
                    [('COUNTER', age, 2, at), ('COUNTER', money, 2, amount)],
                    [('INCREMENT_COUNTER', flag, evidence)]))
            t.scripts.append(Script('Test - E147 remove ' + tag, [('COUNTER', age, 2, 62)],
                [('NAMED_DELETE', m.role('bank ' + tag).name)]))
        t.scripts.append(Script('Test - E147 neutral zero',
            [('COUNTER', frame, 2, 100), ('COUNTER', 'E147Moneyon', 2, 0),
             ('COUNTER', 'E147Moneyoff', 2, 0)], [('INCREMENT_COUNTER', 4, evidence)]))
        t.expect = [('收入', 22, '==', 770, 28), ('对照', 2, '==', 0, 28),
                    ('证据', 22, '==', 1023, 28)]
        t.bench = [('bench_watch', dict(seconds=28, every=1, sheet=False, lines=4))]
        return t


    MISSION = {'engine_bankcapture': mission}
    CHECKS = {'engine_bankcapture': {'a': check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_baseban():
    """C line: PLAYER_DISABLE_BASE_CONSTRUCTION(player), native production control.

    JapanConstructionYard's UNIT_BUILD Command_ConstructJapanPowerPlantEgg builds an 800-cost
    JapanPowerPlantEgg (retail BuildTime 0). No placement or artificial spawning is used.
    A disables p1; B disables s5. The human p1 clicks the first structure button; s5 receives
    the same native command by NAMED_USE_COMMANDBUTTON_ABILITY at 2 seconds.
    Prediction: p1's disabled native click spends nothing and makes no core; the normal click
    spends 800 and makes one core. Whether the scripted press bypasses this gate is unmeasured.
    Counters: human money, s5 money, human cores + 10*s5 cores, script logic frame.
    Evidence and scope: work/re/c_baseban_report.md. Other factions/AI queues remain unmeasured.
    BENCH 11-16: A at f74 2000/1426/0, final f488 1200/1200/11;
    B at f75 2000/1413/0, final f364 1200/1200/11. Disabling either player
    does not block these UNIT_BUILD core orders. The base-construction consumer remains a gap;
    do not infer a no-op action or promote it from this control. Payment timing is strict xfail.
    C: PLAYER_DISABLE_FACTORIES(each, 'japanconstructionyard') as j09 writes it (lower case): the program sets every
    matching object of the player's script-disabled (type 9, for ever). Prediction: no core either side, money 2000.
    BENCH 11-22 (A311): C, D (the own case, two walkers too), F (D at 0.5 s): every core made, both walkers walk -- as
    with no gate; E (NAMED_SET_DISABLED SCRIPT_DISABLED on the yards and walker 0, EMP walker 1) 2000/2000/0 to s53: the
    type holds both. So the action reaches no object here (why: not found). Readings: engine_baseban.readings.toml.
    """
    from maps import probe_border
    from parts import Mission, Script, Test, square
    from checks import engine_scripts8 as s8

    CORE = 'JapanPowerPlantEgg'
    BUTTON = 'Command_ConstructJapanPowerPlantEgg'
    WALKERS = (('AlliedAntiVehicleVehicleTech1', 200.), ('AlliedEngineer', 350.))


    def mission():
        m = Mission(name='CampBaseBan', map=probe_border, units=[], facts={})
        m.spawns.add(CORE)
        for side, dx in (('p1', 0.), ('s5', 1800.)):
            m.put('JapanConstructionYard', 'stop row', dx, -500., side=side,
                  name=f'CNV BaseBan {side}', role=f'yard {side}')
        for k, (unit, dy) in enumerate(WALKERS):      # D's probe of the disabled bit: does each still walk?
            m.put(unit, 'stop row', 600., dy, name=f'CNV BaseBan W{k}', role=f'walker {k}')
            m.waypoint(f'end {k}', f'CNV BaseBan End{k}', 'stop row', 1200., dy)
        return m


    def check(m, gate, walk=False, more=()):
        t = Test()
        t.scripts.append(Script('Test - baseban setup', [], [
            ('MAP_REVEAL_ALL_PERM', m.player('p1')),
            ('PLAYER_SET_MONEY', m.player('p1'), 2000),
            ('PLAYER_SET_MONEY', m.player('s5'), 2000),
            *gate]))
        for side, label in (('p1', '甲资金'), ('s5', '乙资金')):
            counter = f'CNV_BaseBan_{side}'
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Test - baseban money {side}', [], [
                ('SET_PLAYER_MONEY_TO_COUNTER', m.player(side), counter)], once=False))
        s8.total(t, 'CNV_BaseBan_Cores', '核心', [
            (w, ('PLAYER_HAS_OBJECT_COMPARISON', m.player(side), 3, 1, CORE))
            for side, w in (('p1', 1), ('s5', 10))] + [
            (100 * 10 ** k, ('NAMED_INSIDE_AREA', m.role(f'walker {k}').name, f'Test BaseBan End{k}'))
            for k in range(len(WALKERS) if walk else 0)] + list(more))
        s8.frames(t, 'CNV_BaseBan_Clock', '逻辑帧', [])
        s8.at(t, 'baseban press', 2., [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', 'CNV BaseBan s5', BUTTON)])
        watch = dict(every=1., sheet=False, lines=4)
        t.bench = [('bench_watch', dict(watch, seconds=2.)),
                   ('bench_click', dict(x=1120, y=252, world=False, look=False)),
                   ('bench_click', dict(x=1120, y=252, world=False, look=False)),
                   ('bench_click', dict(x=1137, y=323, world=False, look=False)),
                   ('bench_watch', dict(watch, seconds=18.))]
        return t


    def a(m):
        return check(m, [('PLAYER_DISABLE_BASE_CONSTRUCTION', m.player('p1'))])


    def b(m):
        return check(m, [('PLAYER_DISABLE_BASE_CONSTRUCTION', m.player('s5'))])


    def c(m):
        return check(m, [('PLAYER_DISABLE_FACTORIES', m.player(s), 'japanconstructionyard') for s in ('p1', 's5')])


    def d(m, late=False):
        """C's yards in the template's own case; walker 0 disabled by a lower-case name, walker 1 by its own, both sent
        600 east at 1 s: 核心 adds 100 walker 0 at its end + 1000 walker 1 (within 100). F: the same at 0.5 s."""
        return walked(m, late=late, gate=[('PLAYER_DISABLE_FACTORIES', m.player(s), 'JapanConstructionYard') for s in ('p1', 's5')] + [
            ('PLAYER_DISABLE_FACTORIES', m.player('p1'), WALKERS[0][0].lower()),
            ('PLAYER_DISABLE_FACTORIES', m.player('p1'), WALKERS[1][0])])


    def e(m):
        """The same, each by NAMED_SET_DISABLED: the yards and walker 0 SCRIPT_DISABLED (the type C / D set), walker 1
        EMP (the control: frozen, engine_emp)."""
        return walked(m, [('NAMED_SET_DISABLED', n, 'SCRIPT_DISABLED', 1) for n in (
            'CNV BaseBan p1', 'CNV BaseBan s5', m.role('walker 0').name)] + [
            ('NAMED_SET_DISABLED', m.role('walker 1').name, 'EMP', 1)])


    def f(m):
        return d(m, late=True)


    def walked(m, gate, late=False):
        t = check(m, [] if late else gate, walk=True)
        if late:
            s8.at(t, 'baseban off', .5, gate)
        s8.at(t, 'baseban walk', 1., [('MOVE_NAMED_UNIT_TO', m.role(f'walker {k}').name, m.mark(f'end {k}'))
                                      for k in range(len(WALKERS))])
        for k in range(len(WALKERS)):
            t.areas[f'Test BaseBan End{k}'] = square(*m.point(f'end {k}'), 100.)
        return t


    def late_mission():
        """G (review 1122yy #11, the positive control C-F lack): a yard made mid-game. Each side also has a JapanMCV,
        unpacked where it stands at 0.2 s (the name passes on, engine_unpack); at 3 s PLAYER_DISABLE_FACTORIES(s5,
        'JapanConstructionYard') -- s5's only, p1 the control; at 5 s each unpacked yard is pressed for a core.
        核心 adds p1 >= 2 cores 100 + s5 >= 2 cores 1000 + p1 >= 2 yards 10000 + s5 >= 2 yards 100000.
        [the gate reaches a yard made in play: 110111; it reaches none: 111111] BENCH 11-23 (CampBanLateG_mcp_1123_012105):
        111111 s36-s54, money 400 / 400 -- none; no positive control found, the dispatch itself stays unshown."""
        m = mission()
        m.name = 'CampBanLate'
        for side, dx in (('p1', 0.), ('s5', 1800.)):
            m.put('JapanMCV', 'stop row', dx, 400., side=side, name=f'CNV BaseBan M{side}', role=f'mcv {side}')
            m.waypoint(f'here {side}', f'CNV BaseBan Here{side}', 'stop row', dx, 400.)
        return m


    def g(m):
        t = check(m, [], more=[(w, ('PLAYER_HAS_OBJECT_COMPARISON', m.player(s), 3, 2, what)) for s, w, what in (
            ('p1', 100, CORE), ('s5', 1000, CORE), ('p1', 10000, 'JapanConstructionYard'),
            ('s5', 100000, 'JapanConstructionYard'))])
        s8.at(t, 'baseban unpack', .2, [('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', m.role(f'mcv {s}').name,
                                         'Command_UnPackJapanMCV', m.mark(f'here {s}')) for s in ('p1', 's5')])
        s8.at(t, 'baseban off', 3., [('PLAYER_DISABLE_FACTORIES', m.player('s5'), 'JapanConstructionYard')])
        s8.at(t, 'baseban late press', 5., [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(f'mcv {s}').name, BUTTON)
                                            for s in ('p1', 's5')])
        return t


    MISSION = {'engine_baseban': mission, 'engine_banlate': late_mission}
    CHECKS = {'engine_baseban': {'a': a, 'b': b, 'c': c, 'd': d, 'e': e, 'f': f}, 'engine_banlate': {'g': g}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_build():
    """Engine unit test: construction (ADR 0019 layer 2; docs/engine/construction.md) -- a structure's unpack after it is
    placed (how many frames, slower short of power, what it carries meanwhile, whether it makes power, whether it can be
    hurt) and the MCV deploying into a construction yard.

    On the Niagara map the player's construction yard (+50 power), a power plant (+100), three barracks (-25 each), an
    MCV in the west field and an enemy (Soviet_1) Hammer tank by the build spot, held (NO_ATTACK). One second in
    ('Test Go') each variant does one thing; at the start it deletes what it does not need:

      a  mcv      the MCV (health set to HALF first) is ordered to deploy (Command_UnPackAlliedMCV); yard, plant and
                  barracks deleted
      b  plant    a power plant made by script at the build spot (UnpackTime 3 s); plant and barracks deleted: supply 50,
                  demand 0; DAMAGE hit points by script 10 frames after it is made
      c  dim      as b with the three barracks kept: supply 50, demand 75 (the low-power factor 0.5)
      d  dark     as b with the yard deleted and barracks 1 kept: supply 0, demand 25 (the factor at its floor 0.3)
      e  soviet   a Soviet barracks made by script for the player (UnpackTime 10 s; BuildTime 0, no queue item behind it);
                  plant and barracks deleted; the Hammer tank is let go and ordered to attack it

    Counters (four lines), every one counted from 'Test Go' on, frames added per frame while the thing holds:
      帧数    frames since Go
      状态帧  1 x frames the player owns an object UNDER_CONSTRUCTION + 1000 x frames one is UNPACKING
      建成帧  1 x (a) frames a yard stands on the MCV's spot / (b-e) frames the made building is UNPACKING
              + 1000 x (a) frames the MCV is still there / (b-d) frames the power plant does not count yet / (e) frames
              the barracks does not draw yet
      血量    the target's health in percent (a: by the MCV's name -- it passes to the yard)

    Bench 11-05 (round 45; docs/engine/construction.md):
      a CampBuildA_mcp_1105_214815: 状态帧 6000, 建成帧 6020 at 帧数 26 (the yard from Go + 6), 血量 50 throughout
        (the counter OCR misreads it as 0-9 where the blue yard is drawn behind the counter: 50 in the frames).
      b CampBuildB_mcp_1105_214016: 46046 / 46046, 血量 90 from frame 10.
      c CampBuildC_mcp_1105_214217: 68068 / 68068.   d CampBuildD_mcp_1105_214416: 77077 / 77077.
      e CampBuildE_mcp_1105_214612: 151151 / 151151, 血量 94 at s1 down ~3 a shot to 52 at s17.
      First tries: the plain NAMED_USE_COMMANDBUTTON_ABILITY sent the MCV south-west (no point); a script
      UNIT_SET_HEALTH 2500 and a COMPLETELY_BUILT condition read 0 throughout (dropped, not looked into).
    Against the model (RA3-EngineModel construction.py, tests/test_objects_bench.py): every reading the same but e's
    health (the Hammer: layers 3-4).
    """
    import resources
    from maps import niagara
    from parts import Mission, Script, Test, square, status

    MCV, YARD, PLANT, SOVIET, HAMMER = ('AlliedMCV', 'AlliedConstructionYard', 'AlliedPowerPlant', 'SovietBarracks',
                                        'SovietAntiVehicleVehicleTech1')
    HALF, DAMAGE = 2500, 100                # MCV MaxHealth 5000; the plant's 1000
    RUN = {'a': 14.0, 'b': 8.0, 'c': 9.0, 'd': 9.0, 'e': 16.0}
    BUILD = ('west field', -120.0, 260.0)   # the spot scripts make the building on (1060, 2635)
    MCV_AT = ('west field', -220.0, -120.0)
    DELETE = {'a': ('Yard', 'Power', 'Barracks 1', 'Barracks 2', 'Barracks 3'),
              'b': ('Power', 'Barracks 1', 'Barracks 2', 'Barracks 3'), 'c': ('Power',),
              'd': ('Yard', 'Power', 'Barracks 2', 'Barracks 3'), 'e': ('Power', 'Barracks 1', 'Barracks 2', 'Barracks 3')}
    # the excess power while the new building is not counted yet (op, value): b 50 -> 150, c -25 -> 75, d -25 -> 75,
    # e 50 -> 25
    POWER_WAIT = {'b': (0, 150), 'c': (0, 75), 'd': (0, 75), 'e': (3, 50)}


    def _n(part):
        return f'UNIT - CNV Build {part}'


    def mission():
        m = Mission(name='CampBuild', map=resources.measured(niagara), units=[], facts={})
        m.spawns |= {PLANT, SOVIET}
        m.put(YARD, 'base yard', angle=0.0, role='yard', name=_n('Yard'))
        m.put(PLANT, 'base power', angle=0.0, role='power', name=_n('Power'))
        for k, dy in enumerate((0.0, 140.0, 280.0)):
            m.put('AlliedBarracks', 'base factory', 0.0, dy, angle=3.1416, role=f'barracks {k + 1}',
                  name=_n(f'Barracks {k + 1}'))
        m.put(MCV, MCV_AT[0], *MCV_AT[1:], angle=0.0, role='mcv', name=_n('MCV'))
        m.put(HAMMER, BUILD[0], BUILD[1] + 160.0, BUILD[2], side='s1', angle=3.1416, role='hammer', name=_n('Hammer'))
        m.waypoint('build spot', 'Test Build Spot', *BUILD)
        m.waypoint('mcv spot', 'Test MCV Spot', *MCV_AT)
        return m


    def build_test(m, which='a'):
        t = Test()
        p1 = m.player('p1')
        x, y = m.waypoints['Test Build Spot']
        mx, my = m.site(*MCV_AT)
        template, target, (tx, ty) = {'a': (YARD, _n('MCV'), (mx, my)), 'e': (SOVIET, _n('Made'), (x, y))}.get(
            which, (PLANT, _n('Made'), (x, y)))
        t.areas['Test Target'] = square(tx, ty, 150.0)
        start = [('MAP_REVEAL_ALL_PERM', p1), ('UNIT_CHANGE_OBJECT_STATUS', _n('Hammer'), 'NO_ATTACK', 1),
                 ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)] + [('NAMED_DELETE', _n(p)) for p in DELETE[which]]
        if which == 'a':
            start.append(('NAMED_DAMAGE', _n('MCV'), HALF))
        t.scripts.append(Script('Test - start', [], start))
        if which == 'a':
            # the plain NAMED_USE_COMMANDBUTTON_ABILITY gives the deploy no point: bench 11-05, the MCV drove south-west
            go = [('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', _n('MCV'), 'Command_UnPackAlliedMCV', 'Test MCV Spot')]
        else:
            go = [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', target, template, m.team('p1'), 'Test Build Spot')]
        if which == 'e':
            go += [('UNIT_CHANGE_OBJECT_STATUS', _n('Hammer'), 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', _n('Hammer'), target)]
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
        going = ('FLAG', 'Test Going', 1)

        t.counters.append(('CNV_Build_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Build_Frames')], once=False))
        if which in 'bcd':
            t.scripts.append(Script('Test - damage', [going, ('COUNTER', 'CNV_Build_Frames', 2, 10)],
                                    [('NAMED_DAMAGE', target, DAMAGE)]))

        t.counters.append(('CNV_Build_Status', '状态帧'))
        t.scripts += [Script(f'Test - status {st}', [going, ('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', p1, 3, 1,
                                                              status(st))],
                             [('INCREMENT_COUNTER', step, 'CNV_Build_Status')], once=False)
                      for st, step in (('UNDER_CONSTRUCTION', 1), ('UNPACKING', 1000))]

        t.counters.append(('CNV_Build_Done', '建成帧'))
        if which == 'a':                        # the yard's frames on the MCV's spot
            made = ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, YARD, 'Test Target')
        else:                                   # the made building's own UNPACKING
            made = ('UNIT_HAS_OBJECT_STATUS', target, status('UNPACKING'))
        t.scripts.append(Script('Test - made', [going, made], [('INCREMENT_COUNTER', 1, 'CNV_Build_Done')], once=False))
        if which == 'a':
            wait = ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, MCV, 'Test Target')
        else:
            wait = ('PLAYER_EXCESS_POWER_COMPARE_VALUE', p1, *POWER_WAIT[which])
        t.scripts.append(Script('Test - waiting', [going, wait], [('INCREMENT_COUNTER', 1000, 'CNV_Build_Done')],
                                once=False))

        t.counters.append(('CNV_Build_Health', '血量'))
        t.scripts.append(Script('Test - health', [going], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target,
                                                            'CNV_Build_Health')], once=False))
        t.expect = [('帧数', 0, 'ever>=', 1, RUN[which])]
        t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN[which]))]
        return t


    MISSION = {'engine_build': mission}
    CHECKS = {'engine_build': {w: (lambda m, w=w: build_test(m, w)) for w in 'abcde'}}
    return dict(MISSION=MISSION, CHECKS=CHECKS, mission=mission, build_test=build_test, MCV_AT=MCV_AT, MCV=MCV,
                YARD=YARD, object_name=_n)


def engine_countmodifier():
    """CountModifier 0.5/4 contrast, identical seeded counts 4/2 and one copied factory.

    Prediction before bench: FEWEST_UNIT scores at 4/2 are 11.11/33.33 for
    0.5 and 50/33.33 for 4, so the higher modifier should favour Peacekeepers.
    This is a model prediction, not a measured engine score. Record 65 seconds;
    candidate eligibility and per-factory choice remain gaps without direct readings.
    """
    from parts import Test, Script, counted


    def a(m):
        t = Test()
        t.scripts.append(Script('CM reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        for template, suffix, label in [('CNVNewPK', 'PK', '新维和'), ('CNVNewJav', 'JAV', '新标枪')]:
            counted('CNV_CM_' + suffix, label, t, template=template, player=m.player('s1'))
        t.bench = [('bench_watch', dict(seconds=65, every=1, sheet=False, lines=2))]
        return t


    def b(m):
        """B round 206: who else spends the opening's PRODUCTION Deposit 2000. The model (simai, before bench) has the
        retail barracks buy 3 dogs + 1 Javelin + 1 Peacekeeper = 1100 in both, the copied one 3 Javelins = 900 (aicmhalf,
        the Deposit spent: stops at 4/5 as the bench) and 5 Peacekeepers = 1000 (aicmfour, the last paid 100; the bench
        stops at 7/2). Prediction: the bench's retail barracks spends 1400 in aicmfour (one more unit than the model), so
        both groups stop with the Deposit gone. Counters: the copied unit the state builds, retail dogs, Javelins,
        Peacekeepers (four lines)."""
        t = Test()
        t.scripts.append(Script('CM reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        new = ('CNVNewPK', 'PK', '新维和') if m.facts['count modifier'] > 1 else ('CNVNewJav', 'JAV', '新标枪')
        for template, suffix, label in [new, ('AlliedScoutInfantry', 'DOG', '狗'),
                                        ('AlliedAntiVehicleInfantry', 'RJ', '原标枪'),
                                        ('AlliedAntiInfantryInfantry', 'RP', '原维和')]:
            m.spawns.add(template)           # published for the contract: the AI makes it, the check counts it
            counted('CNV_CM_' + suffix, label, t, template=template, player=m.player('s1'))
        t.bench = [('bench_watch', dict(seconds=65, every=1, sheet=False, lines=2))]
        return t


    CHECKS = {build: {'a': a, 'b': b} for build in ('aicmhalf', 'aicmfour')}
    return dict(CHECKS=CHECKS)


def engine_mining():
    """Engine unit test: ore mining (ADR 0019 layer 2; docs/engine/mining.md) -- the trip, what a load is worth, when the
    money comes, two collectors on one node.

    On the probe range's ore pad (maps/probe_range.py 'probe refinery': a refinery facing 45 with one OreNode 180 ahead)
    an Allied refinery is placed; it gives its own collector on unpacking (SpawnBehavior SpawnOnUnpack, round 39). The
    player's money is set to 0 at the start.

      a  one      the refinery's collector alone
      b  two      as a, plus one AlliedMiner placed beside the refinery: two collectors on one node
      c  legs     as a; where the collector is, to tell the drive from the docks

    Counters (four lines), frames from the mission's first frame:
      a  资金 the money; 首笔 frames while the money is 0; 收满 while it is below LOAD; 二笔 while it is below LOAD + 1
      b  资金; 首笔 (< 1), 二笔 (< LOAD + 1), 三笔 (< 2 LOAD + 1)
      c  资金; 到矿 frames until a collector is first in the square around the node; 离矿 until it has left that
         square again; 到场 until it is in the refinery's square after that
      d  as b; frames (summed) with: 名车 the placed collector in c's node square, 一车 at least one collector there,
         两车 both there (which of the two works?)
      e  as d, the placed collector deleted once the money reaches LOAD (does the waiting one get the dock then?)
      f  as b; 首笔; 自到矿 frames until a collector other than the placed one is first in c's node square; 名到矿 until
         the placed one is (does the refinery's own come later, or come first and still wait?)

    Bench 11-05 (round 43; docs/engine/mining.md):
      a CampMineA_mcp_1105_201253: 首笔 239, 收满 268 (8 a frame: 16 / 72 / 128 / 200 at 2 / 9 / 16 / 25 frames, then 250),
        二笔 508; 250 more every 269 frames, 1000 by s69.
      b CampMineB_mcp_1105_201544: 首笔 290, 二笔 559, 三笔 828: one collector's income, at a's period.
      c CampMineC_mcp_1105_201837: 到矿 56, 离矿 71, 到场 226, money from 239 -- the node's square (half side 70) misses
        where it docks: the collector only passes through it.
      d CampMineD_mcp_1105_203036: 名车 64 frames in a row each trip, 一车 - 名车 9 frames in 45 s, 两车 0: the placed one
        works; the refinery's own reaches the node later and waits outside for good.
      e CampMineE_mcp_1105_203435: the placed one deleted at s19: the money stays 250 to s61, nobody in the square.
    Bench 2026-11-12 (round 178):
      f CampMineF_mcp_1112_095956: 首笔 290 (b's), 名到矿 107, 自到矿 121 -- alone (c) the refinery's own is in the square
        at 56: the placed one, standing by the refinery, holds it up ~65 frames, so it comes second and waits for good.
        (Round 178 read it as a collision; round 189 below shows it is not.)
      g  as f, plus 自离场 frames until the refinery's own has left the pad square (half side 50) it fades in in
      h  g with the placed one deleted at the start (the own one alone)
      mineaway g  g's counters, the placed one AWAY south-east (its drive clear of the refinery and the own one's way)
    Bench 2026-11-12 (round 189, work/bench_results/engine_mining__g / __h / mineaway__g.json): 首笔 / 自离场 / 自到矿 /
      名到矿 -- g 290 / 19 / 121 / 107, h 239 / 19 / 56 / -, mineaway g 261 / 19 / 170 / 114. The own one leaves its pad at
      19 every time (not held at its way out), and with the placed one far away it still comes second and waits for
      good: the placed one, made before the refinery's own fades in, claims the node when it looks for it (H2 of
      round 177, which round 178 had ruled out on f's arrival frames alone); the waiting one's square entry is where it
      waits, not an arrival. Sim: sim.Sim._claimed.
    Against the model (RA3-EngineModel mining.py, round 43; tests/test_objects_bench.py mining): a, b, e the same with the
    drives fitted (spawn -> node 101, node <-> refinery 104, placed -> node 153); b's period and the stuck collector are
    predictions. c and d need motion (not compared).
    """
    import dataclasses
    import math

    from maps import probe_range
    from parts import Mission, Script, Test, counted, square

    MINER, REFINERY = 'AlliedMiner', 'AlliedRefinery'
    SITE = 'probe refinery'
    LOAD = 250                                  # OreMinerBehavior DeliveryCapacity / OreNodeBehavior DeliveryAmount
    RUN = {'a': 75.0, 'b': 75.0, 'c': 45.0, 'd': 45.0, 'e': 60.0, 'f': 30.0, 'g': 30.0, 'h': 30.0}
    PLACED = (-110.0, 0.0)                      # b, d: the second collector, from the pad
    PAD = (probe_range.SITES[SITE].x, probe_range.SITES[SITE].y)
    NODE = probe_range.OBJECTS[0].x, probe_range.OBJECTS[0].y
    NODE_R, PAD_R = 70.0, 50.0                  # the squares' half sides (the node 127 + 127 from the pad)


    def _n(part):
        return f'UNIT - CNV Mine {part}'


    def mission():
        m = Mission(name='CampMine', map=probe_range, units=[], facts={})
        m.put(REFINERY, SITE, role='refinery', name=_n('Refinery'))
        m.put(MINER, SITE, *PLACED, angle=0.0, role='miner', name=_n('Miner'))   # b only (deleted at the start else)
        m.spawns.add(MINER)
        return m


    def _below(t, counter, label, limit):
        """counter: frames while the money is below limit (the first frame at or above it stops it)."""
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter}', [('COUNTER', 'CNV_Mine_Money', 0, limit)],
                                [('INCREMENT_COUNTER', 1, counter)], once=False))


    def _until(t, counter, label, flag, cond, after=None):
        """counter: frames until cond first holds (after flag `after` is set); then flag is set."""
        t.counters.append((counter, label))
        gate = [('FLAG', after, 1)] if after else []
        t.scripts.append(Script(f'Test - {counter}', [('FLAG', flag, 0)], [('INCREMENT_COUNTER', 1, counter)], once=False))
        t.scripts.append(Script(f'Test - {counter} seen', gate + [cond], [('SET_FLAG', flag, 1)]))


    def mining_test(m, which='a'):
        t = Test()
        p1 = m.player('p1')
        start = [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 0)]
        if which not in 'bdefg':
            start.append(('NAMED_DELETE', _n('Miner')))
        t.scripts.append(Script('Test - start', [], start))
        t.counters.append(('CNV_Mine_Money', '资金'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Mine_Money')], once=False))
        if which == 'a':
            _below(t, 'CNV_Mine_First', '首笔', 1)
            _below(t, 'CNV_Mine_Full', '收满', LOAD)
            _below(t, 'CNV_Mine_Second', '二笔', LOAD + 1)
        elif which == 'b':
            _below(t, 'CNV_Mine_First', '首笔', 1)
            _below(t, 'CNV_Mine_Second', '二笔', LOAD + 1)
            _below(t, 'CNV_Mine_Third', '三笔', 2 * LOAD + 1)
        elif which == 'f':
            t.areas['Test Node'] = square(*NODE, NODE_R)
            placed_in = ('NAMED_INSIDE_AREA', _n('Miner'), 'Test Node')
            _below(t, 'CNV_Mine_First', '首笔', 1)
            _until(t, 'CNV_Mine_OwnAt', '自到矿', 'Test Own At',
                   ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', 3, 1, MINER, 'Test Node'))
            t.scripts[-1].when.append(placed_in + ('NOT',))
            _until(t, 'CNV_Mine_PlacedAt', '名到矿', 'Test Placed At', placed_in)
        elif which in 'gh':                     # round 189: f's two arrivals and when the refinery's own leaves its pad
            t.areas['Test Node'] = square(*NODE, NODE_R)
            t.areas['Test Pad'] = square(*PAD, PAD_R)
            placed_in = ('NAMED_INSIDE_AREA', _n('Miner'), 'Test Node')
            in_pad = lambda k, op: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', op, k,  # noqa: E731
                                    MINER, 'Test Pad')
            _below(t, 'CNV_Mine_First', '首笔', 1)
            t.scripts.append(Script('Test - own in pad', [in_pad(1, 3)], [('SET_FLAG', 'Test Own In Pad', 1)]))
            _until(t, 'CNV_Mine_OwnOut', '自离场', 'Test Own Out', in_pad(0, 2), after='Test Own In Pad')
            _until(t, 'CNV_Mine_OwnAt', '自到矿', 'Test Own At',
                   ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', 3, 1, MINER, 'Test Node'))
            t.scripts[-1].when.append(placed_in + ('NOT',))
            _until(t, 'CNV_Mine_PlacedAt', '名到矿', 'Test Placed At', placed_in)
            t.counters = t.counters[1:]             # the money's own counter not shown: four lines
        elif which in 'de':
            if which == 'e':                    # the worker (d: the placed one) goes once the first load is in
                t.scripts.append(Script('Test - worker gone', [('COUNTER', 'CNV_Mine_Money', 3, LOAD)],
                                        [('NAMED_DELETE', _n('Miner'))]))
            t.areas['Test Node'] = square(*NODE, NODE_R)
            has = lambda k: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', 3, k, MINER,  # noqa: E731
                             'Test Node')
            for counter, label, cond in (
                    ('CNV_Mine_Named', '名车', ('NAMED_INSIDE_AREA', _n('Miner'), 'Test Node')),
                    ('CNV_Mine_Any', '一车', has(1)), ('CNV_Mine_Two', '两车', has(2))):
                t.counters.append((counter, label))
                t.scripts.append(Script(f'Test - {counter}', [cond], [('INCREMENT_COUNTER', 1, counter)], once=False))
        else:
            t.areas['Test Node'] = square(*NODE, NODE_R)
            t.areas['Test Pad'] = square(*PAD, PAD_R)
            has = lambda area, k=1, op=3: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', op, k,  # noqa
                                            MINER, area)
            _until(t, 'CNV_Mine_AtNode', '到矿', 'Test At Node', has('Test Node'))
            _until(t, 'CNV_Mine_LeftNode', '离矿', 'Test Left Node', has('Test Node', 0, 2), after='Test At Node')
            _until(t, 'CNV_Mine_AtPad', '到场', 'Test At Pad', has('Test Pad'), after='Test Left Node')
        t.expect = [('首笔', 0, 'ever>=', 1, RUN[which])] if which in 'gh' else [('资金', 0, 'ever>=', LOAD, RUN[which])]
        t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN[which]))]
        return t


    # Round 174 (the miner's drive by the node's facing): retail stands every node facing its refinery (node angle =
    # the refinery's + 180: heidelberg, gibraltar, north sea, all six pairs), the generator (resources.objects) put it
    # at 0 till round 175 (probe_range keeps that: NODES = resources.MEASURED) -- 135 off on this pad (a's 104-frame
    # leg), 45 off on niagara's east pad (aitowerinc5 f: a trip of 185).
    # mineturn<k>: this pad with its node turned to retail's facing + k degrees (m: minus), nothing else changed; check p
    # = a's start (the refinery's own collector) with b's three counters (the period twice).
    # Bench 2026-11-12 (work/bench_results/mineturn*__p.json, runs CampMineT<k>P_mcp_1112_01*): 首笔 / 二笔 / 三笔
    #   0: 111 / 262 / 413 (trip 151)    45: 156 / 342 / 528 (186)    -45: 157 / 344 / 531 (187)
    #   90: 214 / 455 / 696 (241)        -90: 214 / 455 / 696 (241)   180: 296 / 619 / 942 (323)
    # with a's 269 at 135: the drive round a node turned away (simmine.MINE_TURN_EXTRA; tests/test_simbench.py mining).
    TURNS = (0, 45, 90, 180, -45, -90)


    def _turned(k):
        """probe_range with its one node turned to face the refinery + k degrees."""
        import types
        mp = types.ModuleType(probe_range.__name__)
        mp.__dict__.update({n: v for n, v in vars(probe_range).items() if not n.startswith('__')})
        face = math.radians(probe_range.FIELDS[0].facing + 180.0 + k)
        mp.OBJECTS = [dataclasses.replace(o, angle=face) if o.template == 'OreNode' else o for o in probe_range.OBJECTS]
        assert sum(o.template == 'OreNode' for o in mp.OBJECTS) == 1
        return mp


    def _tag(k):
        return f'{k}' if k >= 0 else f'm{-k}'


    def turned_mission(k):
        m = mission()
        m.map, m.name = _turned(k), f'CampMineT{_tag(k)}'
        return m


    def turned_test(m):
        t = mining_test(m, 'a')
        t.counters = [c for c in t.counters if c[0] == 'CNV_Mine_Money']
        t.scripts = [s for s in t.scripts if s.name in ('Test - start', 'Test - money')]
        _below(t, 'CNV_Mine_First', '首笔', 1)
        _below(t, 'CNV_Mine_Second', '二笔', LOAD + 1)
        _below(t, 'CNV_Mine_Third', '三笔', 2 * LOAD + 1)
        return t


    CAP = {'cap': 400, 'capz': 0}


    def cap_test(m, which):
        """PLAYER_SET_MONEY_CAP on harvest income (A round 254; 25 uses in the retail missions: a07 sets its allies' cap 0
        at the start with their money 0, the AI's 9999 with 3000). engine_acts_tel showed no script's money is held to it;
        what it caps was not read. p's start (mineturn0: a load of 250 every 151 frames from 111) with the player's cap
        CAP[which] set beside the money 0 in the first script: cap  400 -- does the second load stop the money at 400, keep
        it at 250 (a load not paid that would pass it), or pass it?  capz  0 -- no money at all, or 0 = no cap?
        Counters as p's: 资金, 首笔 / 二笔 / 三笔 frames while the money is below 1 / LOAD + 1 / 2 LOAD + 1.
        The simulator then (cap stored, not used): p's 111 / 262 / 413, money 1000 by s30.
        Bench 2026-11-15 (work/bench_results/mineturn0__cap / __capz.json): cap 250 from 111, then 8 a frame of the second
        load to 394 (二笔 262) and nothing more; capz 0 to the end. A deposit that would pass the cap is not paid (Sim._pay;
        tests/test_simbench.py::test_money_cap_holds_harvest_income_as_the_bench)."""
        t = turned_test(m)
        start = next(s for s in t.scripts if s.name == 'Test - start')
        start.do.append(('PLAYER_SET_MONEY_CAP', m.player('p1'), CAP[which]))
        t.expect = []
        t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=30.0))]
        return t


    FAR = 38.0             # minefar: the refinery this much further back from its node (contract: 180 +- 40, AXIS_SLACK)


    def far_mission():
        """mineturn0 with the refinery FAR further back (240 from its node, still facing it): a longer drive at retail's
        facing -- does the trip grow by the drive (2 x 11 frames), or is the node's own cycle (151) what bounds it?
        Bench 2026-11-12 (work/bench_results/minefar__p.json / __q.json): p 133 / 288 / 443 (a trip of 155) -- the
        round-179 sim's prediction to the frame (a 36-frame leg at 0 and the node's 151; the old 45-frame leg said 144 /
        317 / 490); q 133 / 34 / 107 / 190."""
        m = Mission(name='CampMineFar', map=_turned(0), units=[], facts={})
        back = math.radians(probe_range.FIELDS[0].facing)
        dx, dy = -FAR * math.cos(back), -FAR * math.sin(back)
        m.put(REFINERY, SITE, dx, dy, role='refinery', name=_n('Refinery'))
        m.put(MINER, SITE, dx + PLACED[0], dy + PLACED[1], angle=0.0, role='miner', name=_n('Miner'))   # deleted
        m.spawns.add(MINER)
        return m


    def legs_test(m):
        """q (round 179): p's start with the legs apart -- 首笔; 到矿 / 离矿 frames until the collector is first in / out
        of c's node square; 二到矿 until it is in it again (the second leg starts as the unloading ends, 首笔 + 30).
        Bench 2026-11-12: mineturn0 q (CampMineT0Q_mcp_1112_101613) 111 / 23 / 96 / 156 -- 73 frames at the node the
        first time, 91 after: the node's cycle (151) bounds retail's facing, a leg is 36; the first leg 8 longer from
        where the collector faded in (15 from the dock). At 45 / 90 / 180 the drive round the node goes in and out of the
        square (90: 77 / 151 / 191 before its 首笔 214): no legs to read there."""
        t = mining_test(m, 'a')
        t.counters = [c for c in t.counters if c[0] == 'CNV_Mine_Money']
        t.scripts = [s for s in t.scripts if s.name in ('Test - start', 'Test - money')]
        _below(t, 'CNV_Mine_First', '首笔', 1)
        t.areas['Test Node'] = square(*NODE, NODE_R)
        has = lambda k=1, op=3: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', op, k,  # noqa: E731
                                 MINER, 'Test Node')
        _until(t, 'CNV_Mine_AtNode', '到矿', 'Test At Node', has())
        _until(t, 'CNV_Mine_LeftNode', '离矿', 'Test Left Node', has(0, 2), after='Test At Node')
        _until(t, 'CNV_Mine_AtNode2', '二到矿', 'Test At Node 2', has(), after='Test Left Node')
        t.counters = t.counters[1:]                 # the money's own counter not shown: four lines
        t.expect = [('首笔', 0, 'ever>=', 1, 30.0)]
        t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=30.0))]
        return t


    # mineniag (round 176): niagara as the generator now makes it (round 175: its nodes at retail's facing, not the
    # benches' resources.measured copy), the player's refinery on the east pad (A7's ore), check p as mineturn's. The
    # simulator's prediction: the trip of mineturn0 p, 151 (tests/test_simbench.py niagara_at_retail).
    # Bench 2026-11-12 (work/bench_results/mineniag__p.json, run CampMineNiagP_mcp_1112_045758): 首笔 / 二笔 / 三笔
    #   111 / 262 / 413 -- a trip of 151, as predicted (mineturn0 p's very numbers); 1910 by s77.
    NIAGARA_SITE = 'east refinery'


    def niagara_mission():
        from maps import niagara
        m = Mission(name='CampMineNiag', map=niagara, units=[], facts={})
        m.put(REFINERY, NIAGARA_SITE, role='refinery', name=_n('Refinery'))
        m.put(MINER, NIAGARA_SITE, *PLACED, angle=0.0, role='miner', name=_n('Miner'))   # deleted at the start
        m.spawns.add(MINER)
        return m


    AWAY = (300.0, -200.0)      # mineaway: the placed collector south-east of the pad, its drive to the node clear of the
                                # refinery (171 off its centre) and of the own one's way out


    def away_mission():
        """engine_mining with the placed collector AWAY (round 189): is the refinery's own held up by it only when it
        stands by the refinery (f)?"""
        m = Mission(name='CampMineAway', map=probe_range, units=[], facts={})
        m.put(REFINERY, SITE, role='refinery', name=_n('Refinery'))
        m.put(MINER, SITE, *AWAY, angle=0.0, role='miner', name=_n('Miner'))
        m.spawns.add(MINER)
        return m


    # minejap (E219): JapanMiner's MonitorConditionUpdate (CARRYING + WEAPONSTATE_ONE -> DUMP_ORE and OCL_DroppedOrePile,
    # PreDelay 0.5 s, PostDelay 5 s) and its OreMinerBehavior's ForbiddenStatus GENERIC_TOGGLE_STATE. mineturn0's pad, a
    # JapanMiner where b's collector stands (it claims the node, the refinery's own waits). j: its gun pressed on
    # (Command_ToggleDeployWeapon, the second state GENERIC_TOGGLE_STATE + WEAPONSTATE_ONE) as it first leaves c's node
    # square loaded, off 3 s later; e: the same at 0.5 s, empty; k: never. 离矿 frames until it first leaves the square,
    # 堆 until a DroppedOrePile stands, 首笔 / 二笔 as b. [j: 堆 = 离矿 + 8, 首笔 a trip later than k's; e: no 堆, 首笔
    # 3 s later than k's]
    JAP, GUN = 'JapanMiner', 'Command_ToggleDeployWeapon'


    def jap_mission():
        m = Mission(name='CampMineJap', map=_turned(0), units=[], facts={})
        m.put(REFINERY, SITE, role='refinery', name=_n('Refinery'))
        m.put(JAP, SITE, *PLACED, angle=0.0, role='miner', name=_n('Miner'))
        m.spawns |= {MINER, JAP, 'DroppedOrePile'}
        return m


    def jap_test(m, which):
        t = Test()
        p1, press = m.player('p1'), [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('Miner'), GUN)]
        t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 0)]),
                      Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Mine_Money')], once=False),
                      Script('Test - at node', [('NAMED_INSIDE_AREA', _n('Miner'), 'Test Node')],
                             [('SET_FLAG', 'Test At Node', 1)])]
        t.areas['Test Node'], t.areas['Test Field'] = square(*NODE, NODE_R), square(*PAD, 400.0)
        _until(t, 'CNV_Mine_LeftNode', '离矿', 'Test Left Node', ('NAMED_INSIDE_AREA', _n('Miner'), 'Test Node', 'NOT'),
               after='Test At Node')
        _until(t, 'CNV_Mine_Pile', '堆', 'Test Pile', ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', 3, 1,
                                                      'DroppedOrePile', 'Test Field'))
        _below(t, 'CNV_Mine_First', '首笔', 1)
        _below(t, 'CNV_Mine_Second', '二笔', LOAD + 1)
        if which != 'k':                            # 武装 (not shown) counts the frames the gun is on, to press it off
            on = [('FLAG', 'Test Left Node', 1)] if which == 'j' else [('COUNTER', 'CNV_Mine_Second', 3, 8)]
            t.scripts += [Script('Test - gun on', on, press),
                          Script('Test - armed', on, [('INCREMENT_COUNTER', 1, 'CNV_Mine_Armed')], once=False),
                          Script('Test - gun off', [('COUNTER', 'CNV_Mine_Armed', 3, 45)], press)]
        t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=40.0))]
        return t


    MISSION = {'engine_mining': mission, 'mineaway': away_mission, 'mineniag': niagara_mission, 'minefar': far_mission,
               'minejap': jap_mission, **{f'mineturn{_tag(k)}': (lambda k=k: turned_mission(k)) for k in TURNS}}
    CHECKS = {'engine_mining': {w: (lambda m, w=w: mining_test(m, w)) for w in 'abcdefgh'},
              'mineaway': {'g': lambda m: mining_test(m, 'g')}, 'mineniag': {'p': turned_test},
              'minefar': {'p': turned_test, 'q': legs_test},
              **{f'mineturn{_tag(k)}': {'p': turned_test, 'q': legs_test} for k in TURNS}}
    CHECKS['minejap'] = {w: (lambda m, w=w: jap_test(m, w)) for w in 'jek'}
    CHECKS['mineturn0'] |= {w: (lambda m, w=w: cap_test(m, w)) for w in CAP}
    return dict(MISSION=MISSION, CHECKS=CHECKS, mission=mission, REFINERY=REFINERY)


def engine_pack():
    """Engine unit test: a construction yard packing back into its MCV -- ReplaceSelfSpecialAbility on
    SpecialPower_PackReplaceSelf (TargetType NONE, no PackTime, ReplaceOptions DISABLE_DURING_REPLACE
    DISABLE_NEW_OBJECT_DURING_UNPACK, NewObjectUnpackTime the yard's local unpack time). engine_unpack measured the other
    way (an MCV / an egg deploying at a point); the three yards are the rest of the module's templates but the miner and
    the surveyor.

    On the Niagara map the player's yard (named) in the west field, a waypoint 400 east of it. At 1 s the yard's pack
    button, NAMED_USE_COMMANDBUTTON_ABILITY(yard, Command_Pack...MCV); the first frame the player owns the MCV, and again
    GO_AGAIN s after the press, MOVE_NAMED_UNIT_TO(the yard's name, there) -- the name is the MCV's if it passes on.
    Counters, frames added from the press on (four lines):
      帧数    frames since the press
      车帧    +1 a frame the player owns the yard's template, +1000 a frame he owns the MCV's
      名字帧  +1 a frame the yard's name is not destroyed
      走帧    +1 a frame the MCV stands within 40 of where the yard stood, +1000 a frame it stands within 100 of there

    Predictions from the data: the MCV 6 frames after the press (the deploy on the spot, engine_build a) or at once (no
    PackTime); the name passes on (engine_unpack); the first order lost while the MCV unpacks (NewObjectUnpackTime 2 s,
    DISABLE_NEW_OBJECT_DURING_UNPACK), the second (GO_AGAIN 4 s) taken.

    Bench 11-11 (round 159), 帧数 车帧 名字帧 走帧 at the last reading:
      a CampPackAGo_mcp_1111_043158: 473 473000 473 353050 -- the MCV owned from the press frame (no yard frame at all),
        the name passed on, out of the 40 square at frame 50, within 100 of there from frame 121.
      s CampPackSGo_mcp_1111_043431: 483 483000 483 355051 -- out at 51, there at 128.
      j CampPackJGo_mcp_1111_043652: 720 720000 720 570054 -- out at 54, there at 150.
      So: the yard is its MCV at once (not the deploy's 6 frames, no PackTime), the order given that frame is kept and
      the MCV drives ~20 frames later than NewObjectUnpackTime (2 s = 30) alone would let it: fitted 30 + 14 standing
      (simunits.PACK_EXTRA_FRAMES, INFERRED). Simulator (tests/test_simbench.py
      test_a_yard_packs_into_its_mcv_at_once_and_the_mcv_stands_before_it_drives): a 676 676001 676 547054 at 46 s --
      out at 54, there at 129; the press frame still counts the yard once.
    """
    import resources
    from maps import niagara
    from parts import Mission, Script, Test, square

    KINDS = {'a': ('AlliedConstructionYard', 'AlliedMCV', 'Command_PackAlliedMCV'),
             's': ('SovietConstructionYard', 'SovietMCV', 'Command_PackSovietMCV'),
             'j': ('JapanConstructionYard', 'JapanMCV', 'Command_PackJapanMCV')}
    VARIANTS = tuple(KINDS)
    AT, THERE = ('west field', -200.0, 0.0), ('west field', 200.0, 0.0)
    NAME = 'UNIT - CNV Pack'
    RUN, GO_AGAIN = 30.0, 4.0


    def mission(variant='a'):
        yard, mcv, _ = KINDS[variant]
        m = Mission(name=f'CampPack{variant.upper()}', map=resources.measured(niagara), units=[], facts={'variant': VARIANTS.index(variant)})
        m.spawns |= {mcv}
        m.put(yard, AT[0], *AT[1:], angle=0.0, role='yard', name=NAME)
        m.waypoint('there', 'Test Pack There', *THERE)
        return m


    def frames(m):
        t = Test()
        yard, mcv, button = KINDS[VARIANTS[m.facts['variant']]]
        p1 = m.player('p1')
        t.areas['Test Home'] = square(*m.site(*AT), 40.0)
        t.areas['Test There'] = square(*m.point('there'), 100.0)
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0),
                                                     ('SET_MILLISECOND_TIMER', 'Test Again', 1.0 + GO_AGAIN)]))
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY', NAME, button), ('SET_FLAG', 'Test Going', 1)]))
        going = ('FLAG', 'Test Going', 1)
        owns_mcv = ('PLAYER_HAS_OBJECT_COMPARISON', p1, 3, 1, mcv)
        move = ('MOVE_NAMED_UNIT_TO', NAME, m.mark('there'))
        t.scripts.append(Script('Test - move first', [going, owns_mcv], [move]))
        t.scripts.append(Script('Test - move again', [going, ('TIMER_EXPIRED', 'Test Again')], [move]))

        def per_frame(counter, label, rows):
            t.counters.append((counter, label))
            t.scripts += [Script(f'Test - {counter} {k}', [going, cond], [('INCREMENT_COUNTER', step, counter)],
                                 once=False) for k, (cond, step) in enumerate(rows)]

        per_frame('CNV_Pack_Frames', '帧数', [(going, 1)])
        per_frame('CNV_Pack_Own', '车帧', [(('PLAYER_HAS_OBJECT_COMPARISON', p1, 3, 1, yard), 1), (owns_mcv, 1000)])
        per_frame('CNV_Pack_Name', '名字帧', [(('NAMED_NOT_DESTROYED', NAME), 1)])
        per_frame('CNV_Pack_Walk', '走帧', [(('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, mcv,
                                              'Test Home'), 1),
                                            (('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, mcv,
                                              'Test There'), 1000)])
        t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=0.5, sheet=False, lines=len(t.counters)))]
        return t


    MISSION = {f'engine_pack_{v}': (lambda v=v: mission(v)) for v in VARIANTS}
    CHECKS = {f'engine_pack_{v}': {'go': frames} for v in VARIANTS}      # mod CampPackAGo: 15 characters at most
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_place():
    """Engine unit test: the player placing a structure (ADR 0019 layer 2; docs/engine/construction.md) -- the Allied way
    (build it full in the queue, it waits there until placed, then it unpacks) and the Soviet way (BuildTime 0: place it
    first, it unpacks while the money is paid as it goes, and stops while the money is short).

    On the Niagara map the player's Allied construction yard at the base yard and a Soviet construction yard at the base
    factory; each variant deletes the other at the start. The player orders a power plant by clicking the sidebar's
    structure tab and the plant's button and places it by clicking the map at the build spot (no script action places
    a player's structure):

      a  allied   AlliedPowerPlant (BuildTime 10, 800, UnpackTime 3 s): the clicks, then WAIT s later the place click
      b  soviet   SovietPowerPlant (BuildTime 0, 800, UnpackTime 10 s): the clicks and the place click at once
      c  broke    as b with money SHORT; GIVE s after the money falls below 5, BONUS more

    Counters (four lines):
      资金    the player's money
      付款帧  frames while the money is below the start and above the start less the plant's cost (paying)
      状态帧  1 x frames the player owns an object UNDER_CONSTRUCTION + 1000 x frames one is UNPACKING
      电厂    how many power plants the player owns

    Bench 11-05 (round 46; docs/engine/construction.md 3b). cnv_check's own steps never place: the bench holds the game
    in its Esc menu between calls and the place click does not take (four tries). By hand: bench_start(mod, hold=false),
    bench_click the tab and the button (world=false), (a: bench_watch until 付款帧 149), the button again for a, then
    bench_click the map (a at (1100, 2600), b / c at (1300, 2750), near each yard), bench_watch lines=4. Read by 状态帧:
      a CampPlaceA_mcp_1105_222532: 1200 / 149 from s13.7, no plant until the place click; 状态帧 7000 .. 45000, 电厂 1 at
        once (UNPACKING only, never UNDER_CONSTRUCTION).
      b CampPlaceB_mcp_1105_222645: 2000 until placed; (状态帧, 资金) 6000 1973, 21000 1893, 144000 1237, 150000 1200.
      c CampPlaceC_mcp_1105_223014: 7000 268, 67000 1 .. 113000 1 (stopped, still UNPACKING), the 2000 4 s later, 210000
        1500.
    Against the model (RA3-EngineModel production.place, tests/test_objects_bench.py placing): every pair the same.
    """
    import resources
    from maps import niagara
    from parts import Mission, Script, Test, counted, status

    ALLIED, SOVIET = 'AlliedPowerPlant', 'SovietPowerPlant'
    COST, MONEY, SHORT, GIVE, BONUS = 800, 2000, 300, 4.0, 2000
    RUN = {'a': 22.0, 'b': 16.0, 'c': 24.0}
    WAIT = 13.0                             # a: the place click this long after the button (the plant is full by then)
    BUILD = ('west field', -120.0, 260.0)   # the place click (1060, 2635), as engine_build's script spot
    # the sidebar's structure tab and the power plant's button per yard, screen pixels (1280 x 720); None: not found yet
    TAB = {'a': (1120, 252), 'b': (1120, 252), 'c': (1120, 252)}
    BUTTON = {'a': (1137, 323), 'b': (1137, 323), 'c': (1137, 323)}   # first button of the structure page, both yards


    def _n(part):
        return f'UNIT - CNV Place {part}'


    def mission():
        m = Mission(name='CampPlace', map=resources.measured(niagara), units=[], facts={})
        m.spawns |= {ALLIED, SOVIET}
        m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='allied yard', name=_n('Allied Yard'))
        m.put('SovietConstructionYard', 'base factory', angle=3.1416, role='soviet yard', name=_n('Soviet Yard'))
        m.waypoint('build spot', 'Test Place Spot', *BUILD)
        return m


    def place_test(m, which='a'):
        t = Test()
        p1 = m.player('p1')
        plant = ALLIED if which == 'a' else SOVIET
        start = SHORT if which == 'c' else MONEY
        gone = _n('Soviet Yard') if which == 'a' else _n('Allied Yard')
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, start),
                                                     ('NAMED_DELETE', gone)]))
        t.counters.append(('CNV_Place_Money', '资金'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Place_Money')], once=False))
        t.counters.append(('CNV_Place_Paying', '付款帧'))
        end = max(start - COST, 0)
        t.scripts.append(Script('Test - paying', [('COUNTER', 'CNV_Place_Money', 0, start),
                                                  ('COUNTER', 'CNV_Place_Money', 3, end + 1)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Place_Paying')], once=False))
        if which == 'c':
            # (paying while broke counts too: the money is below the start and >= 1 only until it hits 0)
            t.scripts += [Script('Test - broke', [('COUNTER', 'CNV_Place_Money', 0, 5)],
                                 [('SET_MILLISECOND_TIMER', 'Test Give', GIVE), ('SET_FLAG', 'Test Broke', 1)]),
                          Script('Test - give', [('FLAG', 'Test Broke', 1), ('TIMER_EXPIRED', 'Test Give')],
                                 [('PLAYER_GIVE_MONEY', p1, BONUS)])]
        t.counters.append(('CNV_Place_Status', '状态帧'))
        t.scripts += [Script(f'Test - status {st}', [('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', p1, 3, 1,
                                                      status(st))],
                             [('INCREMENT_COUNTER', step, 'CNV_Place_Status')], once=False)
                      for st, step in (('UNDER_CONSTRUCTION', 1), ('UNPACKING', 1000))]
        counted('CNV_Place_Plants', '电厂', t, template=plant, most=3)
        t.expect = [('电厂', 0, 'ever>=', 1, RUN[which])]
        watch = dict(every=0.5, sheet=False, lines=len(t.counters))
        x, y = m.waypoints['Test Place Spot']
        if TAB[which] is None:                  # the buttons not found yet: run, look by hand (keep=true)
            t.bench = [('bench_watch', dict(watch, seconds=2.0))]
            return t
        tab = ('bench_click', dict(x=TAB[which][0], y=TAB[which][1], world=False, look=False))
        # (the first click after the camera move did not take on the bench: the tab is clicked twice, harmless)
        clicks = [tab, tab, ('bench_click', dict(x=BUTTON[which][0], y=BUTTON[which][1], world=False, look=False))]
        put = [('bench_camera', dict(x=x, y=y, look=False)), ('bench_click', dict(x=x, y=y, look=False))]
        if which == 'a':
            # the plant is full and waiting in the queue: the button (ready) starts the placing, then the map click
            t.bench = ([('bench_watch', dict(watch, seconds=2.0))] + clicks + [('bench_watch', dict(watch, seconds=WAIT))]
                       + [put[0], clicks[2],('bench_watch', dict(watch, seconds=0.5)), put[1]] + [('bench_watch', dict(watch, seconds=RUN[which] - WAIT))])
        else:
            t.bench = ([('bench_watch', dict(watch, seconds=2.0)), put[0]] + clicks + put[1:]
                       + [('bench_watch', dict(watch, seconds=RUN[which]))])
        return t


    MISSION = {'engine_place': mission}
    CHECKS = {'engine_place': {w: (lambda m, w=w: place_test(m, w)) for w in 'abc'}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_powerdef():
    """Engine probe: does a POWERED defence building fire while its owner is short of power, and how soon does it change
    when the power is cut or comes back (engine_powerdef in scenes.py)?

    s1 owns a SovietBaseDefenseAdvanced (EnergyProduction -75, KindOf +POWERED; SageXML Soviet/Structures line 64-66; weapon
    AttackRange 350, Damage 450) and, per variant, a SovietPowerPlant (EnergyProduction +100, line 52). Six player tanks
    (NO_ATTACK) stand 175 north of it. Variants: on (plant, supply 100 >= 75), off (no plant), cut (plant, deleted by
    NAMED_DELETE at 10 s), back (no plant, one made at 10 s at its waypoint on the s1 team).
    Counters: 帧数 (frames from the start), 坦克 (player tanks left, of 6), 首损 (frames counted while all 6 stand: the
    frame of the first loss), 事后 (frames since the 10 s event; cut / back).
    RESULTS (bench 2026-11-07; script frames run ~15 a second; 帧数 is the frame, one tank lost per shot: damage 450):
      on    CampPdOnFrames_mcp_1107_153616: first loss at frame 111 (首损 111), then one tank per ~125 frames (坦克
            6 -> 5 at 帧数 117, 4 at 238, 3 at 374, 2 at 496, 1 at 616): fires.
      off   CampPdOffFrames_mcp_1107_153902: 坦克 6 and 首损 = 帧数 for all 728 frames: never fires with supply 0 < 75.
      cut   CampPdCutFrames_mcp_1107_154116: first loss 111 as in on; the plant deleted at 帧数 ~150 (事后 starts); 坦克 stays
            5 to 帧数 692 (on's next loss was due ~236, 86 frames after the cut): it stops within a shot interval
            (the 1 s rows cannot say closer).
      back  CampPdBkFrames_mcp_1107_154336: plant made at 帧数 ~150 (事后 starts); first loss at 帧数 475 (事后 ~325, ~22 s
            later; on fired 111 frames after the start), then 坦克 5 -> 4 at 603, -> 3 at 724 (~130 frames apart): it fires
            again after power returns, but only after a delay (the plant's own construction / the coil's power-up is not
            separated here).
      Reading: a POWERED defence with its owner short of power does not fire; cutting the supply stops it within a shot
      interval; restoring it starts it again after about 325 frames (the first shot; not the exact power-up time).
    """
    from parts import Script, Test, counted

    VARIANTS = ('on', 'off', 'cut', 'back')           # the mission's (engine_powerdef in scenes.py), in its order
    PLANT = 'SovietPowerPlant'
    EVENT, RUN = 10.0, 45.0


    def frames(m):
        t = Test()
        v = VARIANTS[m.facts['variant']]
        N_TANKS = m.facts['tanks']
        p1 = m.player('p1')
        start = [('MAP_REVEAL_ALL_PERM', p1)] + [('UNIT_CHANGE_OBJECT_STATUS', m.role(f'tank {k}').name, 'NO_ATTACK', 1)
                                                 for k in range(N_TANKS)]
        if v in ('cut', 'back'):
            start.append(('SET_MILLISECOND_TIMER', 'Test Event', EVENT))
        t.scripts.append(Script('Test - start', [], start))
        if v == 'cut':
            t.scripts.append(Script('Test - event', [('TIMER_EXPIRED', 'Test Event')],
                                    [('NAMED_DELETE', m.role('plant').name), ('SET_FLAG', 'Test Event Done', 1)]))
        if v == 'back':
            t.scripts.append(Script('Test - event', [('TIMER_EXPIRED', 'Test Event')],
                                    [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'UNIT - CNV Pd Plant2', PLANT, m.team('s1'),
                                      m.mark('plant')), ('SET_FLAG', 'Test Event Done', 1)]))
        t.counters.append(('CNV_Pd_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [], [('INCREMENT_COUNTER', 1, 'CNV_Pd_Frames')], once=False))
        counted('CNV_Pd_Tanks', '坦克', t, template='AlliedAntiVehicleVehicleTech1', most=N_TANKS + 1)
        t.counters.append(('CNV_Pd_First', '首损'))
        t.scripts.append(Script('Test - first', [('COUNTER', 'CNV_Pd_Tanks', 2, N_TANKS)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Pd_First')], once=False))
        t.counters.append(('CNV_Pd_After', '事后'))
        t.scripts.append(Script('Test - after', [('FLAG', 'Test Event Done', 1)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Pd_After')], once=False))
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
        return t


    CHECKS = {f'powerdef_{v}': {'frames': frames} for v in VARIANTS}
    return dict(CHECKS=CHECKS)


def engine_powerupgrade_e():
    """E175: retail turbine upgrade, normal/advanced plants and module deletion.

    Prediction from EnergyProduction/EnergyBonus: 100/350 before grant, 110/360
    after Upgrade_PowerPlantTurbine only with PowerUpgrade. INFERRED until bench.
    Four isolated owners; f60 baseline, f90 grant, f180 upgraded, f210 remove,
    f300 removed. Frozen bits assert exact excess power (no power consumers).
    No purchased-upgrade, exact update-frame, death or ownership claim.
    MEASURED a: final 330/11/10/11. b: power stays 100/100/500/350 and
    upgrade-holder stays zero through grant/removal. Campaign override explains
    500 vs the raw SDK clone's 350. Trigger Upgrade_PowerPlantTurbine has no
    definition in SDK GlobalData/Upgrade.xml; no positive module-effect claim.
    See work/re/e175_powerupgrade.md. Both failed predictions remain unchanged.
    """
    from model import Script, Test

    UP = 'Upgrade_PowerPlantTurbine'
    ROWS = [('normalon', 'p1', 'base gun', False, True),
            ('normaloff', 's1', 'high gun', False, False),
            ('advancedon', 's2', 'removed gun', True, True),
            ('advancedoff', 's3', 'switch gun', True, False)]


    def check(m):
        t = Test()
        t.counters = [('E175Frame', 'frame'), ('E175Base', 'baseline'),
                      ('E175Grant', 'upgraded'), ('E175Remove', 'removed')]
        t.scripts = [
            Script('Test - frame', [('COUNTER', 'E175Frame', 0, 330)],
                   [('INCREMENT_COUNTER', 1, 'E175Frame')], once=False),
            Script('Test - grant', [('COUNTER', 'E175Frame', 2, 90)],
                   [('NAMED_RECEIVE_UPGRADE', UP, m.role(tag).name) for tag, *_ in ROWS]),
            Script('Test - remove', [('COUNTER', 'E175Frame', 2, 210)],
                   [('NAMED_REMOVE_UPGRADE', UP, m.role(tag).name) for tag, *_ in ROWS])]
        for frame, counter in [(60, 'E175Base'), (180, 'E175Grant'), (300, 'E175Remove')]:
            for bit, (tag, side, _, advanced, enabled) in enumerate(ROWS):
                power = (350 if advanced else 100) + (10 if frame == 180 and enabled else 0)
                t.scripts.append(Script(f'Test - power {frame} {tag}', [
                    ('COUNTER', 'E175Frame', 2, frame),
                    ('PLAYER_EXCESS_POWER_COMPARE_VALUE', m.player(side), 2, power)],
                    [('INCREMENT_COUNTER', 1 << bit, counter)]))
        t.expect = [(label, 0, 'ever>=', value) for label, value in
                    [('frame', 330), ('baseline', 15), ('upgraded', 15), ('removed', 15)]]
        t.bench = [('bench_watch', dict(seconds=120, every=1, sheet=False, lines=4, until='c1>=330'))]
        return t


    def diagnostic(m):
        """Second and final run: exact candidate power, upgrade possession and frame.

        Each line = frame*100000 + upgrade-holder*10000 + exact power; 9999
        means no candidate matched. This preserves the first run's failed prediction.
        """
        t = Test()
        t.counters = [('E175Read' + str(i), tag) for i, (tag, *_) in enumerate(ROWS)]
        t.scripts = [
            Script('Test - clock', [('COUNTER', 'E175Frame', 0, 330)],
                   [('INCREMENT_COUNTER', 1, 'E175Frame')], once=False),
            Script('Test - grant', [('COUNTER', 'E175Frame', 2, 90)],
                   [('NAMED_RECEIVE_UPGRADE', UP, m.role(tag).name) for tag, *_ in ROWS]),
            Script('Test - remove', [('COUNTER', 'E175Frame', 2, 210)],
                   [('NAMED_REMOVE_UPGRADE', UP, m.role(tag).name) for tag, *_ in ROWS])]
        for i, (tag, side, *_) in enumerate(ROWS):
            c = 'E175Read' + str(i)
            active = [('COUNTER', 'E175Frame', 0, 331)]
            t.scripts.append(Script('Test - clear ' + tag, active, [('SET_COUNTER', c, 9999)], once=False))
            for value in (0, 10, 100, 110, 200, 300, 350, 360, 500, 510, 1000, 1010, 1100, 3500, 3510, 3850):
                t.scripts.append(Script(f'Test - read {tag} {value}', active + [
                    ('PLAYER_EXCESS_POWER_COMPARE_VALUE', m.player(side), 2, value)],
                    [('SET_COUNTER', c, value)], once=False))
            t.scripts.append(Script('Test - held ' + tag, active + [
                ('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', m.player(side), 1, UP)],
                [('INCREMENT_COUNTER', 10000, c)], once=False))
            t.scripts.append(Script('Test - stamp ' + tag, active, [
                ('SET_COUNTER_TO_COUNTER', 'E175Stamp', 'E175Frame'),
                ('COUNTER_MATH_VALUE', 'E175Stamp', 2, 100000),
                ('COUNTER_MATH_COUNTER', c, 0, 'E175Stamp')], once=False))
        t.bench = [('bench_watch', dict(seconds=100, every=1, sheet=False, lines=4, until='c1>=33000000'))]
        return t


    CHECKS = {'engine_powerupgrade_e': {'a': check, 'b': diagnostic}}
    return dict(CHECKS=CHECKS)


def engine_production():
    """Engine unit test: a factory's production (ADR 0019 layer 2; docs/engine/production.md) -- the build time, paying as
    it builds, waiting while short of money, building slower while short of power, where the unit comes out.

    On the Niagara map the player's construction yard (+50 power), a power plant (+100) and three barracks (-25 each) at
    the base; the player orders one engineer (AlliedEngineer: BuildTime 10, BuildCost 500) by clicking the sidebar's
    infantry tab and its button (e / f: a script presses the factory's build button instead -- round 39's "no script
    action makes a factory build" was wrong, NAMED_USE_COMMANDBUTTON_ABILITY does). At the start each variant deletes
    what it does not need:

      a  normal   barracks 2 and 3 deleted: supply 150, demand 25; money MONEY
      b  broke    as a with money SHORT; GIVE s after the money falls below 5, BONUS more
      c  dark     the yard, the power plant and barracks 2, 3 deleted: supply 0, demand 25
      d  dim      the power plant deleted: supply 50, demand 75 (three barracks)

    Counters (four lines): 资金 the player's money; 帧数 frames from the first one that sees the money below the start
    (the flag 'Test Paying') while the player owns no engineer; 工程师 how many engineers; 出口位 an engineer of the
    player's in the square around barracks 1's UnitCreatePoint (1), its NaturalRallyPoint (10), within 80 of the
    barracks (100).

    Bench 11-05 (round 41; the clicks land at ~s8, so read against 帧数, not the clock; docs/engine/production.md):
      a CampProdA_mcp_1105_191414: 资金 2000 - ceil(500 k / 150) at 帧数 k (1946 at 16, 1516 at 145), 1500 from 153;
        the engineer counted at 帧数 160; 出口位 101 -> 110 -> 100 (out at UnitCreatePoint, walks past the rally square).
      b CampProdB_mcp_1105_192504: 资金 stops at 3 (帧数 133), 2000 come 4 s later, the engineer at 221.
      c CampProdC_mcp_1105_192728: ~1 a frame (1866 at 132, 1507 at 488, 1500 at 496), the engineer at 505.
      d CampProdD_mcp_1105_193015: 1780 at 132, 1501 at 299, the engineer at 309.
    Bench 11-08 (a script presses the button: NAMED_USE_COMMANDBUTTON_ABILITY(barracks 1, 'Command_ConstructAlliedEngineer')
    at 2 s, no clicks; e / f, barracks 2 and 3 deleted as a):
      e CampProdE_mcp_1108_083724: 资金 2000 -> 1960 at s1, 1506 at 帧数 148, 1500 from 帧数 156 (a: 153; the watch
        samples twice a second); 帧数 stops at 160; 工程师 1 and 出口位 101 -> 100 -> 110 -> 100 at 帧数 160 (a: 160).
        Same curve as a: the scripted press is charged as it builds and takes the full build time (not free, not instant).
      f CampProdF_mcp_1108_083934: money 0 at the start; 30 s of 资金 0, 帧数 0 (the flag needs money below the start, so it
        never counts), 工程师 0, 出口位 0: the scripted press with no money builds nothing (refused, or waits at 0; no
        money was given later, so these two are not told apart).
    Bench 11-09 (g: the engineer banned at the start, ALLOW_DISALLOW_ONE_BUILDING(p1, 'alliedengineer', 0); presses at
    2 / 8 / 19 s, let go at 6 s, banned at 21 s, let go at 30 s; the watch's s runs ~1.3 s behind the timers):
      g CampProdG_mcp_1109_055742: 2000 to s4, paying from s5 (the 2 s press queued and waited for the let-go), the
        first engineer at 帧数 160 (as a); the second job 1500 -> 1286 by s20, 1286 from s20 to s28 (banned halfway: it
        stands, nothing refunded or cancelled), paying again from s29, the second engineer at s35; the third 1000 -> 500
        by s45. A ban stops the building, not the queueing (docs/engine/production.md section 4).
    Bench 11-11 (round 158, h: where the engineer stops -- strips 35-45 / 45-55 / 55-65 / 65-80 west of the barracks):
      h CampProdH_mcp_1111_034429 (PASS): 帧数 160 out (as a); 出口位 0 -> 10 -> 1100 -> 1000 from s13 to s25: it walks
        past the natural rally point (40) and stops 65-80 west, 25-40 beyond it; never sampled in 35-45 (2 Hz watch).
        The simulator stops at 40 (reads 1): not yet fixed (round 159; the extra distance not pinned, INFERRED).
      i CampProdI_mcp_1111_041259 (PASS, round 159; boxes BOXES_I in the barracks' frame): 出口位 1000010 at s13
        (x 60-65, y 24-36: on its way), 1010000 from s13 to s28 (x 75-90, y 24-36). With h (x 65-80, y 3-33) it stops
        about (75-80, 24-33): on the line from the barracks' centre through (40, 18), not on the door line (y 18).
    Against the model (RA3-EngineModel production.py, round 41; tests/test_objects_bench.py, tools/objsidebyside.py with
    orders): every pair and every 帧数 the same, once the model divides the seconds before x 15 (c: 495, not 500), keeps
    the progress in float32 (10 s takes 151 updates; b owes 251 at k 75) and opens the door 10 frames (DoorOpeningTime
    0.66 s). The walk to the rally point is not compared (motion).
    """
    import resources
    from maps import niagara
    from parts import Mission, Script, Test, counted, square

    ENGINEER, BARRACKS = 'AlliedEngineer', 'AlliedBarracks'
    MONEY, SHORT, GIVE, BONUS = 2000, 250, 4.0, 2000     # b: GIVE s after the money reaches 0
    RUN = {'a': 22.0, 'b': 30.0, 'c': 48.0, 'd': 34.0, 'e': 24.0, 'f': 30.0, 'g': 44.0, 'h': 24.0, 'i': 24.0}
    PRESS_AT, BUTTON_NAME = 2.0, 'Command_ConstructAlliedEngineer'   # e, f: a script presses the factory's button
    FACTORY = (1550.0, 2560.0)              # niagara 'base factory'; the barracks turned 180 degrees (exit to the west)
    CREATE, RALLY = (FACTORY[0], FACTORY[1] - 18.0), (FACTORY[0] - 40.0, FACTORY[1] - 18.0)   # (0, 18), (40, 18) turned
    DELETE = {'a': ('Barracks 2', 'Barracks 3'), 'b': ('Barracks 2', 'Barracks 3'),
              'c': ('Yard', 'Power', 'Barracks 2', 'Barracks 3'), 'd': ('Power',), 'e': ('Barracks 2', 'Barracks 3'), 'f': ('Barracks 2', 'Barracks 3'),
              'g': ('Barracks 2', 'Barracks 3'), 'h': ('Barracks 2', 'Barracks 3'), 'i': ('Barracks 2', 'Barracks 3')}
    # h: where the engineer stops -- strips across the exit line, (from, to) map units west of the barracks, y within 15
    # of the exit line; 出口位 adds the step of each strip it stands in
    STRIPS_H = (('Rally', 35.0, 45.0, 1), ('Past10', 45.0, 55.0, 10), ('Past20', 55.0, 65.0, 100), ('Far', 65.0, 80.0, 1000))
    # i: where exactly -- (name, (x from, x to, y from, y to) in the barracks' frame (x = out of the door, y = sideways,
    # the exit line at 18), step): five x strips 55-90 over y -5..50, three y strips 5-50 over x 50-95. Along the door
    # line pushed out puts it at y 18 (the y 5-24 box); along the centre-to-rally line (40, 18) out to x 65-75 puts it
    # at y 29-33 (24-36)
    BOXES_I = (('X55', (55.0, 60.0, -5.0, 50.0), 1), ('X60', (60.0, 65.0, -5.0, 50.0), 10),
               ('X65', (65.0, 70.0, -5.0, 50.0), 100), ('X70', (70.0, 75.0, -5.0, 50.0), 1000),
               ('X75', (75.0, 90.0, -5.0, 50.0), 10000), ('Y5', (50.0, 95.0, 5.0, 24.0), 100000),
               ('Y24', (50.0, 95.0, 24.0, 36.0), 1000000), ('Y36', (50.0, 95.0, 36.0, 50.0), 10000000))
    # g: ALLOW_DISALLOW_ONE_BUILDING(p1, 'alliedengineer', allow) at the start (0) and these seconds; presses at PRESS_G
    BAN_G = ((6.0, 1), (21.0, 0), (30.0, 1))
    PRESS_G = (2.0, 8.0, 19.0)
    # the sidebar's infantry tab and the engineer's button, screen pixels (1280 x 720): bench 11-05, round 41
    TAB, BUTTON = (1174.0, 251.0), (1135.0, 367.0)


    def _n(part):
        return f'UNIT - CNV Prod {part}'


    def mission():
        m = Mission(name='CampProd', map=resources.measured(niagara), units=[], facts={})
        m.spawns |= {ENGINEER}
        m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
        m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power', name=_n('Power'))
        for k, dy in enumerate((0.0, 140.0, 280.0)):
            m.put(BARRACKS, 'base factory', 0.0, dy, angle=3.1416, role=f'barracks {k + 1}', name=_n(f'Barracks {k + 1}'))
        return m


    def production_test(m, which='a'):
        t = Test()
        p1 = m.player('p1')
        t.areas['Test Create'] = square(*CREATE, 10.0)
        t.areas['Test Rally'] = square(*RALLY, 10.0)
        t.areas['Test Near'] = square(*FACTORY, 80.0)
        exits = (('Create', 1), ('Rally', 10), ('Near', 100))
        if which == 'h':
            exits = []
            for name, a, b, step in STRIPS_H:
                x0, x1, y = FACTORY[0] - b, FACTORY[0] - a, CREATE[1]
                t.areas[f'Test {name}'] = [(x0, y - 15.0), (x1, y - 15.0), (x1, y + 15.0), (x0, y + 15.0)]
                exits.append((name, step))
        if which == 'i':                        # boxes in the barracks' own frame (x out of the door, y sideways)
            exits = []
            for name, (xa, xb, ya, yb), step in BOXES_I:
                x0, x1, y0, y1 = FACTORY[0] - xb, FACTORY[0] - xa, FACTORY[1] - yb, FACTORY[1] - ya
                t.areas[f'Test {name}'] = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
                exits.append((name, step))
        start = SHORT if which == 'b' else 0 if which == 'f' else MONEY
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, start)] + [
            ('NAMED_DELETE', _n(p)) for p in DELETE[which]] + (
            [('ALLOW_DISALLOW_ONE_BUILDING', p1, ENGINEER.lower(), 0)] if which == 'g' else [])))
        t.counters.append(('CNV_Prod_Money', '资金'))
        if which == 'b':                        # by events: the clicks' mission second is not known (bench 11-05: ~s8)
            # (op 1, meant as <=, held at 250 <= 0 -- bench 11-05; op 0 '<' as 'paying' reads right)
            t.scripts += [Script('Test - broke', [('FLAG', 'Test Paying', 1), ('COUNTER', 'CNV_Prod_Money', 0, 5)],
                                 [('SET_MILLISECOND_TIMER', 'Test Give', GIVE), ('SET_FLAG', 'Test Broke', 1)]),
                          # gated by the flag too (11-05 the bonus came at the start; not an unset timer, which reads
                          # not expired: probe align / unset 11-13, docs/engine/production.md 5)
                          Script('Test - give', [('FLAG', 'Test Broke', 1), ('TIMER_EXPIRED', 'Test Give')],
                                 [('PLAYER_GIVE_MONEY', p1, BONUS)])]
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Prod_Money')], once=False))
        t.scripts.append(Script('Test - paying', [('COUNTER', 'CNV_Prod_Money', 0, start)], [('SET_FLAG', 'Test Paying', 1)]))
        t.counters.append(('CNV_Prod_Frames', '帧数'))
        counted('CNV_Prod_Made', '工程师', t, template=ENGINEER, most=3)
        t.scripts.append(Script('Test - frames', [('FLAG', 'Test Paying', 1), ('COUNTER', 'CNV_Prod_Made', 2, 0)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Prod_Frames')], once=False))
        t.counters.append(('CNV_Prod_Exit', '出口位'))
        t.scripts.append(Script('Test - exit zero', [], [('SET_COUNTER', 'CNV_Prod_Exit', 0)], once=False))
        t.scripts += [Script(f'Test - exit {a}', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', 3, 1,
                                                    ENGINEER, f'Test {a}')],
                             [('INCREMENT_COUNTER', step, 'CNV_Prod_Exit')], once=False)
                      for a, step in exits]
        if which in 'efhi':                       # no clicks: a script presses barracks 1's engineer button
            t.scripts += [Script('Test - press set', [], [('SET_MILLISECOND_TIMER', 'Test Press', PRESS_AT)]),
                          Script('Test - press', [('TIMER_EXPIRED', 'Test Press')],
                                 [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('Barracks 1'), BUTTON_NAME)])]
        if which == 'g':                        # a ban, a press while banned, a let go, a ban halfway through a build
            t.scripts.append(Script('Test - g set', [], [('SET_MILLISECOND_TIMER', f'Test Press {k}', s)
                                                         for k, s in enumerate(PRESS_G)] +
                                    [('SET_MILLISECOND_TIMER', f'Test Ban {k}', s) for k, (s, _) in enumerate(BAN_G)]))
            t.scripts += [Script(f'Test - press {k}', [('TIMER_EXPIRED', f'Test Press {k}')],
                                 [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('Barracks 1'), BUTTON_NAME)])
                          for k in range(len(PRESS_G))]
            t.scripts += [Script(f'Test - ban {k}', [('TIMER_EXPIRED', f'Test Ban {k}')],
                                 [('ALLOW_DISALLOW_ONE_BUILDING', p1, ENGINEER.lower(), allow)])
                          for k, (_, allow) in enumerate(BAN_G)]
        t.expect = [('工程师', 0, 'ever>=', 1, RUN[which])] if which != 'f' else []
        watch = dict(every=0.5, sheet=False, lines=len(t.counters))
        if which in 'efghi':
            t.bench = [('bench_watch', dict(watch, seconds=RUN[which]))]
        elif TAB[0] is None:                     # the buttons not found yet: run, look by hand (keep=true)
            t.bench = [('bench_watch', dict(watch, seconds=2.0))]
        else:
            t.bench = [('bench_watch', dict(watch, seconds=2.0)),
                       ('bench_click', dict(x=TAB[0], y=TAB[1], world=False, look=False)),
                       ('bench_click', dict(x=BUTTON[0], y=BUTTON[1], world=False, look=False)),
                       ('bench_watch', dict(watch, seconds=RUN[which]))]
        return t


    # engine_press (retail j07 / s08: a repeating script presses a factory's build button every frame while it holds):
    # a Japanese refinery and s08's war factory, two power plants (supply 200, demand 100), money MONEY_P; from PRESS_AT
    # one script presses both buttons PRESSES frames running. Counters: 资金, 按 (the presses made), each unit's count
    PRESSES, MONEY_P = 30, 20000
    PRESSED = (('Refinery', 'JapanRefinery', 'base refinery', 'Command_ConstructJapanMinerFromRefinery', 'JapanMiner', '矿车'),
               ('Tesla', 'S08_SovietWarFactory', 'base factory', 'Command_ConstructSovietAntiVehicleVehicleTech2',
                'SovietAntiVehicleVehicleTech2', '磁暴'))


    def press_mission():
        m = Mission(name='CampPress', map=resources.measured(niagara), units=[], facts={})
        for part, tmpl, site, _, unit, _ in PRESSED:
            m.put(tmpl, site, angle=None if part == 'Refinery' else 3.1416, role=part.lower(), name=_n(part))  # pad's
            m.spawns |= {unit}
        for k in range(2):
            m.put('SovietPowerPlant', 'base power', 0.0, 160.0 * k, angle=0.0, role=f'power {k + 1}', name=_n(f'Power {k}'))
        return m


    def press_test(m):
        t, p1 = Test(), m.player('p1')
        t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, MONEY_P),
                                                  ('SET_MILLISECOND_TIMER', 'Test Press', PRESS_AT)]),
                      Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Prod_Money')], once=False),
                      Script('Test - press', [('TIMER_EXPIRED', 'Test Press'), ('COUNTER', 'CNV_Prod_Press', 0, PRESSES)],
                             [('NAMED_USE_COMMANDBUTTON_ABILITY', _n(part), button) for part, _, _, button, _, _ in PRESSED] +
                             [('INCREMENT_COUNTER', 1, 'CNV_Prod_Press')], once=False)]
        t.counters += [('CNV_Prod_Money', '资金'), ('CNV_Prod_Press', '按')]
        for part, _, _, _, unit, label in PRESSED:
            counted(f'CNV_Prod_{part}', label, t, template=unit, most=8)
        t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=75.0))]
        return t


    MISSION = {'engine_production': mission, 'engine_press': press_mission}
    CHECKS = {'engine_production': {w: (lambda m, w=w: production_test(m, w)) for w in 'abcdefghi'},
              'engine_press': {'a': press_test}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_rally():
    """Engine unit test: where a factory's new unit stops when no rally point is set -- QueueProductionExitUpdate's
    NaturalRallyPoint, on a factory whose point lies farther out than the barracks' (docs/engine/production.md).

    engine_production h / i (bench 11-11): the barracks' engineer (UnitCreatePoint (0, 18), NaturalRallyPoint (40, 18))
    does not stop at (40, 18) but out at about (75-80, 24-33) -- on the line from the barracks' centre through the
    rally point, not on the door line (y 18). Two readings of that: the point is pushed out along the centre-to-rally
    line by a fixed length (~40), or scaled from the centre (~1.9). The Allied war factory (UnitCreatePoint (-20, 20),
    NaturalRallyPoint (80, 20)) tells them apart: a fixed ~40 stops the tank about (119, 30), x 1.9 about (152, 38).

    On the Niagara map the player's construction yard, a power plant and an Allied war factory at 'base factory' turned
    180 degrees (exit to the west); money MONEY; at PRESS_AT s a script presses the factory's Guardian tank button.
    Counters (four lines): 资金; 帧数 frames the player owns no tank since the money first fell; 坦克 how many tanks;
    出口位 adds the step of each box (in the factory's frame: x out of the door, y sideways) the tank stands in.

    Bench 11-11 (round 159): the Guardian tank's button built nothing (it wants Upgrade_AlliedTech2; 资金 3000 for 35 s);
    with the Riptide CampRallyTank_mcp_1111_044501 (PASS): 2250 paid, the Riptide counted at 帧数 160, 出口位 1000010 from
    s13 to s31 -- x 112-127, y 25-34: the fixed push (~(119, 30)), not the scaling. Simulator (sim.RALLY_PUSH 40): the
    same 1000010 (tests/test_simbench.py test_a_new_unit_stops_beyond_the_natural_rally_point_as_the_bench).
    """
    import resources
    from maps import niagara
    from parts import Mission, Script, Test, counted

    TANK, FACTORY_T = 'AlliedAntiInfantryVehicle_Ground', 'AlliedWarFactory'   # the Riptide (no tech; the Guardian
    BUTTON_NAME = 'Command_ConstructAlliedAntiInfantryVehicle_Ground'      # wants Upgrade_AlliedTech2: run 1 built none)
    MONEY, PRESS_AT, RUN = 3000, 2.0, 30.0
    FACTORY = (1550.0, 2560.0)              # niagara 'base factory'
    # (name, (x from, x to, y from, y to) in the factory's frame, step): five x strips 90-190 over y 0..50, three y
    # strips over x 90-190 (the door line at 20)
    BOXES = (('X90', (90.0, 112.0, 0.0, 50.0), 1), ('X112', (112.0, 127.0, 0.0, 50.0), 10),
             ('X127', (127.0, 142.0, 0.0, 50.0), 100), ('X142', (142.0, 162.0, 0.0, 50.0), 1000),
             ('X162', (162.0, 190.0, 0.0, 50.0), 10000), ('Y10', (90.0, 190.0, 10.0, 25.0), 100000),
             ('Y25', (90.0, 190.0, 25.0, 34.0), 1000000), ('Y34', (90.0, 190.0, 34.0, 50.0), 10000000))


    def _n(part):
        return f'UNIT - CNV Rally {part}'


    def mission():
        m = Mission(name='CampRally', map=resources.measured(niagara), units=[], facts={})
        m.spawns |= {TANK}
        m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
        m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power', name=_n('Power'))
        m.put(FACTORY_T, 'base factory', 0.0, 0.0, angle=3.1416, role='factory', name=_n('Factory'))
        return m


    def rally_test(m):
        t = Test()
        p1 = m.player('p1')
        exits = []
        for name, (xa, xb, ya, yb), step in BOXES:      # turned 180 degrees: (x, y) -> (-x, -y)
            x0, x1, y0, y1 = FACTORY[0] - xb, FACTORY[0] - xa, FACTORY[1] - yb, FACTORY[1] - ya
            t.areas[f'Test {name}'] = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            exits.append((name, step))
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, MONEY),
                                                     ('SET_MILLISECOND_TIMER', 'Test Press', PRESS_AT)]))
        t.scripts.append(Script('Test - press', [('TIMER_EXPIRED', 'Test Press')],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('Factory'), BUTTON_NAME)]))
        t.counters.append(('CNV_Rally_Money', '资金'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Rally_Money')], once=False))
        t.scripts.append(Script('Test - paying', [('COUNTER', 'CNV_Rally_Money', 0, MONEY)], [('SET_FLAG', 'Test Paying', 1)]))
        t.counters.append(('CNV_Rally_Frames', '帧数'))
        counted('CNV_Rally_Made', '坦克', t, template=TANK, most=3)
        t.scripts.append(Script('Test - frames', [('FLAG', 'Test Paying', 1), ('COUNTER', 'CNV_Rally_Made', 2, 0)],
                                [('INCREMENT_COUNTER', 1, 'CNV_Rally_Frames')], once=False))
        t.counters.append(('CNV_Rally_Exit', '出口位'))
        t.scripts.append(Script('Test - exit zero', [], [('SET_COUNTER', 'CNV_Rally_Exit', 0)], once=False))
        t.scripts += [Script(f'Test - exit {a}', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', 3, 1,
                                                    TANK, f'Test {a}')],
                             [('INCREMENT_COUNTER', step, 'CNV_Rally_Exit')], once=False)
                      for a, step in exits]
        t.expect = [('坦克', 0, 'ever>=', 1, RUN)]
        t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN))]
        return t


    MISSION = {'engine_rally': mission}
    CHECKS = {'engine_rally': {'tank': rally_test}}       # mod CampRallyTank
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_replace():
    """Engine unit test: ReplaceSelfSpecialAbility (the MCV deploying; docs/engine/construction.md) -- two questions the
    round-45 reading (engine_build a: ordered to deploy at its own spot, the MCV is gone in the 7th script pass after the
    order, carrying UNPACKING meanwhile) left open:

      f  far   as engine_build a, but the deploy point is FAR east of the MCV: is the wait a drive to the point (more
               frames with the distance) or a fixed delay?
      g  bad   as engine_build a with our MCV copy whose ReplacementTemplate names no object: when no new object can be
               made, does the old MCV stay or go (the code goes on to destroy it)?

    Counters as engine_build (帧数, 状态帧, 建成帧 = 1 x yard frames in the area + 1000 x MCV frames in the area, 血量 by
    the MCV's name). The area here is the square of half-side AREA around the MCV and the point.
    """
    import os

    import labpaths
    from parts import Unit, square

    base = engine_build()

    FAR = 100.0                             # f: the deploy point this far east of the MCV
    AREA = 200.0
    BAD_MCV, NO_SUCH = 'CNVBadMCV', 'CNVNoSuchObject'
    RUN = {'f': 14.0, 'g': 14.0}


    def _sub1(x, old, new):
        assert x.count(old) == 1, (old[:60], x.count(old))
        return x.replace(old, new, 1)


    def bad_mcv(target=NO_SUCH):
        x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', 'AlliedMCV.xml'), encoding='utf-8').read()
        x = _sub1(x, 'id="AlliedMCV"', f'id="{BAD_MCV}"')
        x = _sub1(x, 'EditorName="AlliedMCV"', f'EditorName="{BAD_MCV}"')
        x = _sub1(x, '<ReplacementTemplate>AlliedConstructionYard</ReplacementTemplate>',
                  f'<ReplacementTemplate>{target}</ReplacementTemplate>')
        i = x.index('<GameObject\n\t\tid="AlliedMCV_Naval"')
        j = x.index('</GameObject>', i) + len('</GameObject>')
        x = x[:i] + x[j:]
        return Unit(BAD_MCV, x, what='盟军基地车的复制：展开目标模板不存在（测创建失败）')


    def mission(which='f', control=False):
        m = base['mission']()
        m.name = 'CampRepl' if which == 'f' else ('CampReplCopy' if control else 'CampReplBad')
        if which == 'g':
            m.units = [bad_mcv(base['YARD'] if control else NO_SUCH)]
            m.spawns |= {BAD_MCV}
            for o in m.objects:
                if o.name == base['object_name']('MCV'):
                    o.template = BAD_MCV
            m.cast['mcv'].template = BAD_MCV
        else:
            m.waypoint('mcv spot', 'Test MCV Spot', base['MCV_AT'][0], base['MCV_AT'][1] + FAR, base['MCV_AT'][2])
        return m


    def test(m, which):
        t = base['build_test'](m, 'a')
        mx, my = m.site(*base['MCV_AT'])
        t.areas['Test Target'] = square(mx + (FAR / 2 if which == 'f' else 0.0), my, AREA)
        if which == 'g':                        # the MCV counted in the area is our copy
            for s in t.scripts:
                s.when = [tuple(BAD_MCV if v == base['MCV'] else v for v in c) for c in s.when]
        t.expect = [('帧数', 0, 'ever>=', 1, RUN[which])]
        t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN[which]))]
        return t


    MISSION = {'engine_replace': lambda: mission('f'), 'engine_replace_bad': lambda: mission('g'),
               'engine_replace_copy': lambda: mission('g', control=True)}
    CHECKS = {'engine_replace': {'f': lambda m: test(m, 'f')}, 'engine_replace_bad': {'g': lambda m: test(m, 'g')},
              'engine_replace_copy': {'h': lambda m: test(m, 'g')}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_sell():
    """Engine unit test: selling (ADR 0019 layer 2) -- what SELL_OBJECT does to a structure: the money back, how long it
    takes, whether it is counted as power meanwhile, what happens to a garrison, to a half-built one, to a hurt one.

    On the Niagara map the player's construction yard (+50 power), a power plant (+100, cost 800, 1000 health) and
    the three barracks of engine_build (deleted: not needed); 2000 money set at the start. In the 'Test Go' frame (one
    second in) each variant sells its target:

      a  full    the map's power plant
      b  half    as a, health set to 500 before Go
      c  unpack  the map's plant deleted; one made by script at Go (unpacks 46 frames); sold at frame 10 of the count
      d  bunker  a SovietBunker for the player (cost 500) with two Allied peacekeepers garrisoned instantly at the
                 start (NO_ATTACK); the bunker is sold at Go
      g  bunker  as d, but the fourth line counts from the start, not from Go: d's counting began in the sale's own
                 frame, so "never ENCLOSED" there could be "never got in" or "let out at once by the sale"
      e  killed  as a; 5000 damage at frame 5 (killed half way through the sale)
      f  twice   as a; SELL_OBJECT written twice in the Go actions

    Counters (four lines), every one counted from 'Test Go' on:
      帧数   frames since Go
      资金   the player's money
      卖帧   1 x frames the target is not destroyed + 1000 x frames it carries SOLD
      第四行  a-c, e, f: 1 x frames excess power >= 150 (the plant still counts) + 1000 x frames excess power <= 50
              d: 1 x frames the first peacekeeper is alive + 1000 x frames it is ENCLOSED (still in the bunker)

    Bench 11-06 (round 49; the counters read from s1 on, the first row already 26-29 frames in; one run each):
      a CampSellA_mcp_1106_021303: 资金 2000 -> 2400 (half of the 800) by frame 28; 卖帧 31031; 第四行 31 then 1000 a
        frame: SOLD from frame 1, the plant gone at frame 31 and counted as power until then.
      b CampSellB_mcp_1106_021504: 2000 -> 2200 by frame 27 (800 x 0.5 x health 0.5); 卖帧 31031; 第四行 as a.
      c CampSellC_mcp_1106_021657: sold at frame 10 of the unpack: NOTHING -- 资金 2000, 卖帧 = 帧数 (never SOLD,
        never gone), 第四行 46 frames of no power (46000) then the plant counts (46004 ... 46071): refused while it
        unpacks.
      d CampSellD_mcp_1106_022301 (2nd try; the 1st, garrison in the start script, read the same): 资金 2000 -> 2250
        (half of 500); 卖帧 31031; 第四行 = frames only: the first peacekeeper alive throughout, ENCLOSED never seen
        (the garrison did not take, or the bunker does not give that status: open, not looked into).
      g CampSellG_mcp_1117_225033 (bench 11-17): s1 27 2250 27027 9042 -- the peacekeeper was ENCLOSED 9 frames (in at
        0.4 s, the sale at 1.0 s) and out from the sale's frame on, alive: the garrison took, the sale lets it out at once
        (d's counting simply began in that frame). The simulator reads the same.
      e CampSellE_mcp_1106_022507: killed at frame 5: 资金 2400 (the refund comes at the start of the sale); 卖帧 5004
        (gone after 4 frames, SOLD 5); 第四行 4 then 1000 a frame: the power goes with it.
      f CampSellF_mcp_1106_022713: SELL_OBJECT twice: 2400 (paid once); 卖帧 31031; 第四行 as a.
    Against the model (RA3-EngineModel sell.py, tests/test_objects_bench.py "selling"): every final reading and the
    frames after the first row the same, d included (the model empties the bunker in the sell's frame).
    """
    import resources
    from maps import niagara
    from parts import Mission, Script, Test, status

    PLANT, BUNKER, MAN = 'AlliedPowerPlant', 'SovietBunker', 'AlliedAntiInfantryInfantry'
    RUN = 6.0
    BUILD = ('west field', -120.0, 260.0)


    def _n(part):
        return f'UNIT - CNV Sell {part}'


    def mission():
        m = Mission(name='CampSell', map=resources.measured(niagara), units=[], facts={})
        m.spawns |= {PLANT}
        m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
        m.put(PLANT, 'base power', angle=0.0, role='power', name=_n('Power'))
        m.put(BUNKER, *BUILD[:1], BUILD[1], BUILD[2], angle=0.0, role='bunker', name=_n('Bunker'))
        for k in range(2):
            m.put(MAN, BUILD[0], BUILD[1] + 150.0, BUILD[2] + 60.0 * k, angle=0.0, role=f'man {k}', name=_n(f'Man {k}'))
        m.waypoint('build spot', 'Test Build Spot', *BUILD)
        return m


    def sell_test(m, which='a'):
        t = Test()
        p1 = m.player('p1')
        d = which in 'dg'
        target = _n('Bunker') if d else (_n('Made') if which == 'c' else _n('Power'))
        gone = [_n('Bunker'), _n('Man 0'), _n('Man 1')] if not d else [_n('Power')]
        if which == 'c':
            gone.append(_n('Power'))
        start = [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 2000), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
        start += [('NAMED_DELETE', n) for n in gone]
        if which == 'b':
            start.append(('NAMED_DAMAGE', target, 500))
        if d:
            for k in range(2):
                start.append(('UNIT_CHANGE_OBJECT_STATUS', _n(f'Man {k}'), 'NO_ATTACK', 1))
            start.append(('SET_MILLISECOND_TIMER', 'Test In', 0.4))
            t.scripts.append(Script('Test - in', [('TIMER_EXPIRED', 'Test In')], [
                ('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', _n(f'Man {k}'), target) for k in range(2)]))
        t.scripts.append(Script('Test - start', [], start))
        go = []
        if which == 'c':
            go.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', target, PLANT, m.team('p1'), 'Test Build Spot'))
        else:
            go += [('SELL_OBJECT', target)] * (2 if which == 'f' else 1)
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
        going = ('FLAG', 'Test Going', 1)

        t.counters.append(('CNV_Sell_Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Sell_Frames')], once=False))
        if which == 'c':
            t.scripts.append(Script('Test - sell', [going, ('COUNTER', 'CNV_Sell_Frames', 2, 10)],
                                    [('SELL_OBJECT', target)]))
        if which == 'e':
            t.scripts.append(Script('Test - kill', [going, ('COUNTER', 'CNV_Sell_Frames', 2, 5)],
                                    [('NAMED_DAMAGE', target, 5000)]))

        t.counters.append(('CNV_Sell_Money', '资金'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Sell_Money')], once=False))

        t.counters.append(('CNV_Sell_Sold', '卖帧'))
        for cond, step, nm in ((('NAMED_NOT_DESTROYED', target), 1, 'alive'),
                               (('UNIT_HAS_OBJECT_STATUS', target, status('SOLD')), 1000, 'sold')):
            t.scripts.append(Script(f'Test - {nm}', [going, cond], [('INCREMENT_COUNTER', step, 'CNV_Sell_Sold')],
                                    once=False))

        t.counters.append(('CNV_Sell_Four', '第四行'))
        if d:
            rows = [(('NAMED_NOT_DESTROYED', _n('Man 0')), 1), (('UNIT_HAS_OBJECT_STATUS', _n('Man 0'),
                                                                  status('ENCLOSED')), 1000)]
        else:
            rows = [(('PLAYER_EXCESS_POWER_COMPARE_VALUE', p1, 3, 150), 1),
                    (('PLAYER_EXCESS_POWER_COMPARE_VALUE', p1, 0, 51), 1000)]
        for k, (cond, step) in enumerate(rows):
            t.scripts.append(Script(f'Test - four {k}', [cond] if which == 'g' else [going, cond],
                                    [('INCREMENT_COUNTER', step, 'CNV_Sell_Four')],
                                    once=False))
        t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
        t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN))]
        return t


    MISSION = {'engine_sell': mission}
    CHECKS = {'engine_sell': {w: (lambda m, w=w: sell_test(m, w)) for w in 'abcdefg'}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_sellall():
    """PLAYER_SELL_EVERYTHING ownership/refund probe; work/re/c_sellall_report.md.

    Before bench prediction: 3s empty Soviet_6, 5s sell target, 9s repeat.
    Allied power plants cost 800: target receives 400 once; its plant carries
    SOLD then disappears, all three Guardians and other owners' plants remain.
    a targets Soviet_4; b targets Player_1. Counters: weighted balances
    (p1 + 10*s4 + 100*s5), living mask (units 1/2/4, plants 8/16/32),
    plant SOLD mask (1/2/4), logic frame. Initial 222000/63/0/frame;
    predicted final a 226000/47/0/frame, b 222400/55/0/frame.
    """
    from maps import probe_border
    from parts import Mission, Script, Test, status
    from checks import engine_scripts8 as s8

    SIDES = ('p1', 's4', 's5')


    def mission():
        m = Mission(name='CampSellAll', map=probe_border, units=[], facts={})
        for k, side in enumerate(SIDES):
            for kind, template, dx in (('unit', 'AlliedAntiVehicleVehicleTech1', 0.),
                                       ('plant', 'AlliedPowerPlant', 300.)):
                role = side+' '+kind
                m.put(template, 'stop row', -500.+k*1500.+dx, -2300., side=side,
                      role=role, name='CNV SellAll '+role)
        return m


    def check(m, which):
        t = Test()
        target = 's4' if which == 'a' else 'p1'
        t.scripts.append(Script('Test - SellAll init', [], [
            ('PLAYER_SET_MONEY', m.player(side), 2000) for side in SIDES] + [
            ('UNIT_CHANGE_OBJECT_STATUS', m.role(side+' '+kind).name, status('NO_ATTACK'), 1)
            for side in SIDES for kind in ('unit', 'plant')]))
        s8.at(t, 'sell empty player', 3., [('PLAYER_SELL_EVERYTHING', m.player('s6'))])
        s8.at(t, 'sell target player', 5., [('PLAYER_SELL_EVERYTHING', m.player(target))])
        s8.at(t, 'sell target again', 9., [('PLAYER_SELL_EVERYTHING', m.player(target))])
        t.counters.append(('CNV_SA_Money', '资金码'))
        t.scripts.append(Script('Test - SellAll money', [], [
            ('SET_COUNTER', 'CNV_SA_Money', 0)] + [
            action for k, side in enumerate(SIDES) for action in (
                ('SET_PLAYER_MONEY_TO_COUNTER', m.player(side), 'CNV_SA_Tmp'),
                ('COUNTER_MATH_VALUE', 'CNV_SA_Tmp', 2, 10**k),
                ('COUNTER_MATH_COUNTER', 'CNV_SA_Money', 0, 'CNV_SA_Tmp'))], once=False))
        s8.total(t, 'CNV_SA_Alive', '存活位', [
            (2**(k+3*j), ('NAMED_NOT_DESTROYED', m.role(side+' '+kind).name))
            for j, kind in enumerate(('unit', 'plant')) for k, side in enumerate(SIDES)])
        s8.total(t, 'CNV_SA_Sold', '出售位', [
            (2**k, ('UNIT_HAS_OBJECT_STATUS', m.role(side+' plant').name, status('SOLD')))
            for k, side in enumerate(SIDES)])
        s8.frames(t, 'CNV_SA_Frame', '逻辑帧', [])
        s8.watch(t, 16., .25)
        return t


    MISSION = {'engine_sellall': mission}
    CHECKS = {'engine_sellall': {w: (lambda m, w=w: check(m, w)) for w in 'ab'}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_share():
    """Retail-campaign leftovers, one bench (round 222): PLAYER_TOGGLE_RESOURCE_SHARING on mining income (111 uses; a01
    both players of the co-op pair) and the conditions NAMED_SELECTED (50) / TYPE_SELECTED (38), with the selection set by
    SELECT_OBJECT(player, object) / DESELECT(). Mission on engine_mining's pad (maps/probe_range.py 'probe refinery': the
    refinery's own collector alone, the placed one deleted at the start -- engine_mining a: 250 a load, the first at frame
    239, then every 269 frames).

      all  money: Player_1 (the refinery's owner), Soviet_5 and Soviet_6 friends of the player both ways, money 0 at the
           start; sharing on for Player_1 and Soviet_5 at the start, Soviet_6 on at 24 s, Soviet_5 off at 42 s.
           So the first load is split with one sharer, the second with two, the third with one again (Soviet_6).
           selection: the player's 'pick' (a Guardian on 'power 1') and Soviet_4's 'foe' (a Hammer on 'low gun'), both
           NO_ATTACK; SELECT_OBJECT(Player_1, pick) at 3 s, (Player_1, refinery) at 6 s, DESELECT at 9 s,
           (Player_1, foe) at 12 s, DESELECT at 15 s, (Player_1, pick) at 18 s, NAMED_KILL(pick) at 21 s.
           甲钱 / 乙钱 / 丙钱 = Player_1's / Soviet_5's / Soviet_6's money
           选 (every frame) = 1 NAMED_SELECTED(pick) 2 NAMED_SELECTED(refinery) 4 TYPE_SELECTED(Guardian)
             8 TYPE_SELECTED(AlliedRefinery) 16 NAMED_SELECTED(foe) 32 TYPE_SELECTED(Hammer)
      [program (work/re d115_script_semantics.md 19): money coming in to a sharing player is split among k sharing allies
       + itself, floor(amount / (k + 1)) each. Predicted: load 1 125 / 125 / 0; load 2 (k = 2) about 83 each (the
       rounding per deposit tells whether the earner keeps the same share or the rest); load 3 125 to Player_1 and
       Soviet_6, Soviet_5 unchanged. Selection predicted: 5 (3-6 s), 10 (6-9 s: SELECT_OBJECT replaces), 0, 16 + 32 or 0
       (an enemy's selectable?), 0, 5, 0 after the kill.]
      BENCH 11-14 (round 222, run_queue, CampShareAll_mcp_1114_052045) PASS: 甲钱 / 乙钱 / 丙钱 / 选 s1 0 0 0 0 | s2-s4
        0 0 0 1 | s5-s10 0 0 0 2 | s11-s13 0 0 0 16 | s14 4 4 0 16 | s15 64 64 0 16 | s16 125 125 0 16 | s17-s23 125 125 0 1
        | s24-s31 125 125 0 0 | s32 141 133 8 0 | s33 201 163 38 | s34-s49 249 188 63 | s50 277 188 91 | s51 341 188 155 |
        s52-s67 374 188 188. Against the prediction: the earner keeps the rest, not one share (two sharers: 124 / 63 / 63
        a load -- each Friend 8 // 3 = 2 of a deposit of 8, the earner 4); SELECT_OBJECT replaces (2 alone at s5), an
        enemy's object is selected too (16); DESELECT changes nothing (2 to s10, 16 to s16); TYPE_SELECTED never true
        (no 4 / 8 / 32); the killed pick still selected ~3 s (1 to s23). Simulator: Money.earn, SELECT_OBJECT,
        NAMED_SELECTED / TYPE_SELECTED (tests/test_simbench.py test_share_all_as_the_bench).
    """
    from parts import Script, Test, status
    import checks.engine_scripts8 as s8

    mining = engine_mining()

    TANK, FOE = 'AlliedAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech1'
    FRIEND = (2, 0.0, 'Friend')
    RUN = 66.0


    def _n(part):
        return f'UNIT - CNV Share {part}'


    def mission():
        m = mining['mission']()
        m.name = 'CampShare'
        m.put(TANK, 'power 1', role='pick', name=_n('Pick'))
        m.put(FOE, 'low gun', role='foe', side='s4', name=_n('Foe'))
        return m


    def all_(m):
        t = Test()
        p1, s5, s6 = m.player('p1'), m.player('s5'), m.player('s6')
        pick, foe, refinery = _n('Pick'), _n('Foe'), m.role('refinery').name
        na = status('NO_ATTACK')
        t.scripts.append(Script('Test - Share start', [], [
            ('MAP_REVEAL_ALL_PERM', p1), ('NAMED_DELETE', m.role('miner').name),
            *[('PLAYER_RELATES_PLAYER', a, b, FRIEND) for a, b in ((p1, s5), (s5, p1), (p1, s6), (s6, p1))],
            *[('PLAYER_SET_MONEY', p, 0) for p in (p1, s5, s6)],
            ('PLAYER_TOGGLE_RESOURCE_SHARING', p1, 1), ('PLAYER_TOGGLE_RESOURCE_SHARING', s5, 1),
            ('UNIT_CHANGE_OBJECT_STATUS', pick, na, 1), ('UNIT_CHANGE_OBJECT_STATUS', foe, na, 1)]))
        for key, secs, acts in (
                ('sel1', 3.0, [('SELECT_OBJECT', p1, pick)]),
                ('sel2', 6.0, [('SELECT_OBJECT', p1, refinery)]),
                ('desel1', 9.0, [('DESELECT',)]),
                ('sel3', 12.0, [('SELECT_OBJECT', p1, foe)]),
                ('desel2', 15.0, [('DESELECT',)]),
                ('sel4', 18.0, [('SELECT_OBJECT', p1, pick)]),
                ('kill', 21.0, [('NAMED_KILL', pick)]),
                ('share6', 24.0, [('PLAYER_TOGGLE_RESOURCE_SHARING', s6, 1)]),
                ('unshare5', 42.0, [('PLAYER_TOGGLE_RESOURCE_SHARING', s5, 0)])):
            s8.at(t, key, secs, acts)
        for counter, label, player in (('CNV_Shr_M1', '甲钱', p1), ('CNV_Shr_M5', '乙钱', s5), ('CNV_Shr_M6', '丙钱', s6)):
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Test - {counter}', [], [('SET_PLAYER_MONEY_TO_COUNTER', player, counter)],
                                    once=False))
        s8.total(t, 'CNV_Shr_Sel', '选', [
            (1, ('NAMED_SELECTED', pick)), (2, ('NAMED_SELECTED', refinery)),
            (4, ('TYPE_SELECTED', TANK)), (8, ('TYPE_SELECTED', mining['REFINERY'])),
            (16, ('NAMED_SELECTED', foe)), (32, ('TYPE_SELECTED', FOE))])
        t.expect = [('甲钱', 0, 'ever>=', 1, RUN)]
        s8.watch(t, RUN)
        return t


    MISSION = {'engine_share': mission}
    CHECKS = {'engine_share': {'all': all_}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_structureplace_e():
    """E183: refinery front placement exclusion, native shape versus module removal.

    SDK RestrictedAreaShape is a box (30,45) centered 90 ahead of the refinery.
    A power plant centered 120 ahead clears the refinery's base box (60,45)
    but overlaps the reserved box: predict no placement on, one placement off.
    Only this fixed geometry is probed; placement acceptance/rejection reasons,
    rotation and exact edge rules remain gaps.
    MEASURED (11-16, a): zero plants in both -- the plant's GameDependency wants the retail yard (not the clone).
    11-23, b: with that dropped the plant is paid, but both previews are red alike: the ore node's own no-build
    (ProjectedBuildabilityInfo 120 x 105, refineries excepted) covers 60..300 ahead of a refinery 180 from it, the
    reserved box inside it: this geometry cannot tell the module. So (11-23, b again): the refinery 200 further back
    (380 from the node) and the plant 140 ahead: it laps 33 into the reserved box, ~27 clear of the refinery and the
    node's no-build (box test). Any node 180 ahead (the ore contract, K4) covers the reserved box whole, so the probe is a
    clone CNVE183Ref (not a '...Refinery' the ore rules hold to their ore; only its id changes). a's readings were taken
    with the old geometry (the retail id on the pad, the plant 120 ahead).
    See work/re/e183_structureplace.md.
    """
    import re
    from pathlib import Path

    import labpaths
    from maps import probe_range
    from parts import Mission, Script, Test, Unit, counted, square
    from checks.engine_modulebatch import native

    BACK = 200 / 2 ** 0.5                     # the refinery 200 behind the pad (45 degrees)
    CLICK = (2957.573593, 4157.573593)       # the plant 140 ahead of it
    INCLUDE = r'<xi:include\s+href="DATA:Includes/GenericRefineryStructurePlacementBehavior.xml"\s*/>'


    def mission(enabled=True):
        refinery = native('AlliedRefinery', 'Structures', 'CNVE183Ref')
        if not enabled:
            refinery.xml, n = re.subn(INCLUDE, '', refinery.xml)
            assert n == 1
        yard = native('AlliedConstructionYard', 'Structures', 'CNVE183Yard')
        for u in (refinery, yard):    # native() puts the local Defines into '=' expressions: '=4s' would not parse
            u.xml = re.sub(r'="=([0-9.]+s)"', r'="\1"', u.xml)
        yard.xml = yard.xml.replace('CommandSet="AlliedConstructionYardCommandSet"', 'CommandSet="CNVE183Menu"')
        yard.xml = yard.xml.replace('</AssetDeclaration>', '<LogicCommandSet id="CNVE183Menu"><Cmd>Command_ConstructAlliedPowerPlant</Cmd></LogicCommandSet></AssetDeclaration>')
        yard.link += ['LogicCommandSet:CNVE183Menu']
        # the plant's GameDependency wants the retail yard, not this clone (a's two runs could not queue it): dropped
        plant = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedPowerPlant.xml').read_text(encoding='utf-8-sig')
        plant, n = re.subn(r'<GameDependency>.*?</GameDependency>', '', plant, flags=re.S)
        assert n == 1
        m = Mission(name='CampSp' + ('On' if enabled else 'Off'), map=probe_range,
                    units=[refinery, yard, Unit('AlliedPowerPlant', plant)])
        m.facts['enabled'] = enabled
        m.spawns.add('AlliedPowerPlant')
        m.put(refinery.id, 'probe refinery', -BACK, -BACK, angle=0.7853981633974483, role='refinery', name='E183 Refinery')
        m.put(yard.id, 'probe refinery', 0, -260, role='yard', name='E183 Yard')
        return m


    def check(m):
        t = Test()
        p1 = m.player('p1')
        t.counters = [('E183Age', '采样帧'), ('E183Money', '资金')]
        t.scripts = [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 10000)]),
                     Script('Test - age', [], [('INCREMENT_COUNTER', 1, 'E183Age')], once=False),
                     Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'E183Money')], once=False)]
        t.areas['E183 Front'] = square(*CLICK, 12)
        counted('E183Total', '电厂总数', t, template='AlliedPowerPlant', player=p1)
        counted('E183Front', '前方电厂', t, template='AlliedPowerPlant', player=p1, area='E183 Front', most=2)
        expected = int(not m.facts['enabled'])
        t.expect = [('资金', 0, 'ever==', 9200), ('电厂总数', 20, '==', expected),
                    ('前方电厂', 20, '==', expected)]
        watch = dict(every=1, sheet=False, lines=4)
        button = ('bench_click', dict(x=1137, y=323, world=False, look=False))
        t.bench = [('bench_start', dict(hold=False)),
                   ('bench_camera', dict(x=CLICK[0], y=CLICK[1], look=False)),
                   ('bench_click', dict(x=1120, y=252, world=False, look=False)),
                   ('bench_click', dict(x=1120, y=252, world=False, look=False)), button,
                   ('bench_watch', dict(watch, seconds=100, until='c2<=9200')), button,
                   ('bench_watch', dict(watch, seconds=0.5)),
                   ('bench_click', dict(x=CLICK[0], y=CLICK[1], look=False)),
                   ('bench_watch', dict(watch, seconds=40))]
        return t


    def exact(m):
        """b: a with the camera put on the click by the mission (MOVE_CAMERA_TO at 1 s + bench_view, as E169's assistp b:
        bench_camera's minimap click is off by ~100), every click looked at, and a 40 s wait for the 10 s plant in place of
        the 9200 sentinel the miner's income (+250 a trip) keeps money above: a paid 800 shows as money off the 250 grid."""
        t = check(m)
        from checks import engine_scripts8 as s8
        t.waypoints['E183 view'] = CLICK
        s8.at(t, 'view', 1., [('MOVE_CAMERA_TO', 'E183 view', 0.5, 0.0, 1.0, 1.0)])
        # off: a plant in front some time (when is the bench's queue); on: none ever
        t.expect = [('前方电厂', 0, 'ever==', 1)] if not m.facts['enabled'] else [('电厂总数', 0, '==', 0)]
        t.bench = [(name, dict(kw, look=True) if name == 'bench_click' else kw) for name, kw in t.bench]
        t.bench[1] = ('bench_view', dict(x=CLICK[0], y=CLICK[1], look=True))
        t.bench[5] = ('bench_watch', dict(t.bench[5][1], seconds=40, until=''))
        return t


    MISSION = {'structpon': lambda: mission(True), 'structpoff': lambda: mission(False)}
    CHECKS = {name: {'a': check, 'b': exact} for name in MISSION}
    CONTROLS = {'structpoff': 'structpon'}
    return dict(MISSION=MISSION, CHECKS=CHECKS, CONTROLS=CONTROLS)


def engine_tech():
    """Engine probe: the Allied tech upgrade (Upgrade_AlliedTech2) and what it lets a war factory build (the Guardian
    tank, AlliedAntiVehicleVehicleTech1, NeededUpgrade Upgrade_AlliedTech2, 950). Mission engine_tech in scenes.py: yard,
    power plant, a war factory inside the yard's TechUpgrade radius (600 rectangular) and one outside; variants delete
    the factory they do not use.

      a  nothing given, click the Guardian         b  GIVE_PLAYER_UPGRADE Tech2, click the Guardian
      c  yard NAMED_RECEIVE_UPGRADE (near factory) d  same, only the far factory
      e  the player buys Tech2 on the yard, then the Guardian    g  only the near factory receives Tech2
      h  yard AND the far factory (750 from the yard) both receive Tech2 by script, only the far factory stands
    The yard's Tech2 button (structures tab, row 3 col 2) needs an ore refinery (tooltip: needs refinery), so the mission
    places one. Counters: 资金, 守护者, 二级持有 / 三级持有 (0..3: PLAYER_HAS_NUM_UNITS_WITH_UPGRADE n = 1, 2, 3 -> the
    highest n that holds, i.e. how many of the player's objects carry the upgrade), 帧数 (e: frames from the first money
    below the start while no Guardian).

    Bench 11-07 (Guardian clicked by hand coordinates at ~s16; the missions' money 4000, Guardian 950):
      a CampTechA  nothing given: money stays 4000, no Guardian; 二级持有 0 and 三级持有 0 all run (nobody holds Tech2/3).
      b CampTechB  GIVE_PLAYER_UPGRADE (Player_1, Upgrade_AlliedTech2): 二级持有 0 (no object takes it), money 4000, no
                   Guardian: the player-level give does not unlock the Guardian.
      c CampTechC  yard NAMED_RECEIVE_UPGRADE, near factory (300 away): 二级持有 2 from s1 (yard + factory), money 4000 ->
                   3050 over s17..s19 (950 paid), Guardian 1 from s19. PASS (expect ever>= 1).
      d CampTechD  same, only the far factory (750 from the yard): 二级持有 1 (the yard alone), money 4000 flat, no
                   Guardian: the TechUpgrade radius (600, rectangular) does govern buildability.
      g CampTechG  only the near factory receives Tech2 directly: 二级持有 1 (the factory), money flat, no Guardian.
      h CampTechH  yard and the far factory both receive: 二级持有 2, no Guardian (money only rises: refinery income).
      e CampTechE  the player buys Tech2 on the yard (tab click ~s16.6): money falls ~6.1-7 a frame net of income (3626 at
                   帧数 94 -> 3013 at 186, then 3000), 二级持有 2 at 帧数 195 (~15 s = 225 frames from the click), then
                   the Guardian button works (3050 paid, Guardian 1 at 帧数 824).
    """
    from parts import Script, Test, counted, square

    GUARDIAN = 'AlliedAntiVehicleVehicleTech1'      # the Guardian (NeededUpgrade Upgrade_AlliedTech2): G5, no mission import

    MONEY = 4000
    UP2, UP3 = 'Upgrade_AlliedTech2', 'Upgrade_AlliedTech3'
    RUN = {'a': 25.0, 'b': 25.0, 'c': 25.0, 'd': 25.0, 'e': 60.0, 'g': 25.0, 'h': 25.0}
    DELETE = {'a': ('Far',), 'b': ('Far',), 'c': ('Far',), 'd': ('Near',), 'e': ('Far',), 'g': ('Far',), 'h': ('Near',)}
    # sidebar coordinates (screen pixels 1280 x 720); None until found by hand
    VEH_TAB, GUARD_BUTTON = (1200.0, 251.0), (1136.0, 368.0)      # vehicle tab, the Guardian's button (greyed: needs Tech2)
    STR_TAB, YARD_UP_BUTTON = (1120.0, 251.0), (1188.0, 415.0)    # structures tab, row 3 col 2 (tech upgrade)


    def _n(part):
        return f'UNIT - CNV Tech {part}'


    def _holders(t, counter, label, up, p1):
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        for n in (1, 2, 3):
            t.scripts.append(Script(f'Test - {counter} {n}', [('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', p1, n, up)],
                                    [('SET_COUNTER', counter, n)], once=False))


    def tech_test(m, which='a'):
        t = Test()
        p1 = m.player('p1')
        start = [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, MONEY)]
        start += [('NAMED_DELETE', _n(p)) for p in DELETE[which]]
        keep = 'Far' if which in ('d', 'h') else 'Near'
        if which == 'b':
            start.append(('GIVE_PLAYER_UPGRADE', p1, UP2))
        if which in ('c', 'd', 'h'):
            start.append(('NAMED_RECEIVE_UPGRADE', UP2, _n('Yard')))
        if which in ('g', 'h'):
            start.append(('NAMED_RECEIVE_UPGRADE', UP2, _n(keep)))
        t.scripts.append(Script('Test - start', [], start))
        t.counters.append(('CNV_Tech_Money', '资金'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Tech_Money')], once=False))
        t.scripts.append(Script('Test - paying', [('COUNTER', 'CNV_Tech_Money', 0, MONEY)], [('SET_FLAG', 'Test Paying', 1)]))
        counted('CNV_Tech_Made', '守护者', t, template=GUARDIAN, most=3)
        _holders(t, 'CNV_Tech_Up2', '二级持有', UP2, p1)
        if which == 'a':
            _holders(t, 'CNV_Tech_Up3', '三级持有', UP3, p1)
        if which == 'e':
            t.counters.append(('CNV_Tech_Frames', '帧数'))
            t.scripts.append(Script('Test - frames', [('FLAG', 'Test Paying', 1), ('COUNTER', 'CNV_Tech_Made', 2, 0)],
                                    [('INCREMENT_COUNTER', 1, 'CNV_Tech_Frames')], once=False))
        t.expect = [('守护者', 0, 'ever>=', 1, 40.0)] if which == 'c' else []     # c: the one variant that builds by script
        watch = dict(every=0.5, sheet=False, lines=len(t.counters))
        steps = [('bench_watch', dict(watch, seconds=2.0))]
        if which == 'e' and YARD_UP_BUTTON[0] is not None:
            steps += [('bench_click', dict(x=STR_TAB[0], y=STR_TAB[1], world=False, look=False)),
                      ('bench_click', dict(x=YARD_UP_BUTTON[0], y=YARD_UP_BUTTON[1], world=False, look=False)),
                      ('bench_watch', dict(watch, seconds=25.0))]
        if VEH_TAB[0] is not None:
            steps += [('bench_click', dict(x=VEH_TAB[0], y=VEH_TAB[1], world=False, look=False)),
                      ('bench_click', dict(x=GUARD_BUTTON[0], y=GUARD_BUTTON[1], world=False, look=False))]
        steps.append(('bench_watch', dict(watch, seconds=RUN[which])))
        t.bench = steps
        return t


    CHECKS = {'engine_tech': {w: (lambda m, w=w: tech_test(m, w)) for w in 'abcdegh'}}
    return dict(CHECKS=CHECKS)


def engine_threatbonus():
    """C-line probe: REDALERT_DISABLE_THREAT_LEVEL_BONUS(player), 20 retail uses in six missions.

    SDK GlobalData/RedAlerts.xml: deaths contribute threat at 3 times their value; orange/red thresholds
    12500/37500, capped at 50000, decay 150/300 per second; protocol XP multipliers 1/1.5/2.
    System/PlayerTechRanks.xml: rank 2 needs 360 XP, normally 1 XP/s. INFERRED: scripted NAMED_KILL
    contributes death threat too. Two players lose ten 2000-cost Apocalypses at 2, 62, 122, 182,
    242, 302 seconds, with an anchor surviving. A disables p1's bonus, B disables s5's.
    Prediction before measuring: disabled rank at frame 5400; enabled before frame 4500 if scripted
    deaths activate the threat multiplier. Do not promote the action on an equal baseline alone.
    Counters A: p1 rank-2 frame, s5 rank-2 frame, living sacrifice count, completed loss waves.
    Counters B: the same first three, then the script logic frame. B stops at frame 5700 rather than
    assuming captured seconds are mission seconds. A ended after only three waves (both ranks still 0).
    B also uses HOLD_FIRE (3); A used HOLD_POSITION (2), with the two sides outside weapon range.
    BENCH 11-16 B: both players reach rank 2 at frame 2893, even disabled s5; final counters
    2893/2893/0/5708. The simulator's 5400/5400 is retained as a strict xfail. The script's
    unit-experience bonus scope and actual player threat/multiplier remain gaps; no promotion.
    No combat or AI world input is assumed. Evidence and unresolved inputs: work/re/c_threatbonus_report.md.
    """
    from maps import probe_border
    from parts import Mission, Script, Test
    from checks import engine_scripts8 as s8

    TANK = 'SovietAntiVehicleVehicleTech3'
    SIDES = ('p1', 's5')
    WAVES = (2., 62., 122., 182., 242., 302.)
    RUN = 375.


    def _name(side, wave, k):
        return f'CNV TB {side} {wave} {k}'


    def mission():
        m = Mission(name='CampThreat', map=probe_border, units=[], facts={})
        m.spawns.add(TANK)
        for side, x in (('p1', 700.), ('s5', 3000.)):
            for wave in range(len(WAVES)):
                for k in range(10):
                    m.put(TANK, 'stop row', x + k % 5 * 130 - 1300.,
                          700. + wave * 400 + k // 5 * 140 - 4300., side=side,
                          name=_name(side, wave, k))
            m.put(TANK, 'stop row', x - 1300., 4500. - 4300., side=side, name=f'CNV TB {side} anchor')
        return m


    def check(m, disabled):
        t = Test()
        names = [_name(side, wave, k) for side in SIDES for wave in range(len(WAVES)) for k in range(10)]
        t.scripts.append(Script('Test - threat setup', [],
                                [('REDALERT_DISABLE_THREAT_LEVEL_BONUS', m.player(disabled)),
                                 ('MAP_REVEAL_ALL_PERM', m.player('p1'))] +
                                [('UNIT_SET_STANCE', n, 2 if disabled == 'p1' else 3)
                                 for n in names + [f'CNV TB {s} anchor' for s in SIDES]]))
        t.scripts.append(Script('Test - threat clock', [], [('INCREMENT_COUNTER', 1, 'CNV_TB_Clock')], once=False))
        for side, label in (('p1', '甲升级帧'), ('s5', '乙升级帧')):
            counter = f'CNV_TB_{side}'
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Test - threat rank {side}',
                                    [('PLAYER_HAS_PLAYER_TECH', m.player(side), 'PlayerTech_Generic_Rank_2')],
                                    [('SET_COUNTER_TO_COUNTER', counter, 'CNV_TB_Clock')]))
        s8.total(t, 'CNV_TB_Alive', '余车', [(1, ('NAMED_NOT_DESTROYED', n)) for n in names])
        t.counters.append(('CNV_TB_Waves', '批次') if disabled == 'p1' else ('CNV_TB_Clock', '逻辑帧'))
        for wave, secs in enumerate(WAVES):
            s8.at(t, f'threat loss {wave}', secs,
                  [('NAMED_KILL', _name(side, wave, k)) for side in SIDES for k in range(10)] +
                  [('INCREMENT_COUNTER', 1, 'CNV_TB_Waves')])
        s8.watch(t, RUN, 10.)
        if disabled == 's5':
            t.bench = [('bench_watch', dict(seconds=1500., every=10., sheet=False, lines=4, until='c4>=5700'))]
        return t


    def a(m):
        return check(m, 'p1')


    def b(m):
        return check(m, 's5')


    MISSION = {'engine_threatbonus': mission}
    CHECKS = {'engine_threatbonus': {'a': a, 'b': b}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_unpack():
    """Engine unit test: NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT(unit, Command_UnPack..., waypoint) with the waypoint
    AWAY from the unit -- retail's 264 uses are mostly deploys at a point (MCVs 47, Japanese eggs ~90, the Allied miner 9):
    every one a ReplaceSelfSpecialAbility on SpecialPower_UnpackReplaceSelf (StartAbilityRange 2, object geometry,
    ReplacementTemplate, PackTime 2-3 s). engine_build a measured the deploy on the spot (the yard 6 frames after the
    order, the MCV's name and health passed on); here the unit stands 400 west of the point.

    On the Niagara map the player's unit (named) in the west field, the waypoint 400 east of it, ordered at 1 s:
      mcv  AlliedMCV -> AlliedConstructionYard (Command_UnPackAlliedMCV)
      egg  JapanBaseDefenseEgg -> JapanBaseDefense (Command_UnPackJapanBaseDefenseEgg)
    Counters, frames added from the order on (four lines):
      帧数    frames since the order
      车帧    +1 a frame the player owns the unit's template, +1000 a frame one stands within 100 of the waypoint
      场帧    +1 a frame the replacement stands within 100 of the waypoint, +1000 a frame the player owns one anywhere
      名字帧  +1 a frame the unit's name is not destroyed (passed on: counts on after the replacement)

    Bench 11-10 (round 138), last reading s41 (帧数 车帧 场帧 名字帧):
      mcv  CampUnpackMcvGo_mcp_1110_022434: 631 31121 510510 631 -- the MCV drives there (within 100 of the point from
           frame 90), is gone at frame 121, the yard stands on the point from frame 121 (owned and in the area alike),
           the name passes on (名字帧 = 帧数).
      egg  CampUnpackEggGo_mcp_1110_022725: 634 29112 522 634 -- the same: within 100 from frame 83, the defense on the
           point from frame 112, the name passes on; but PLAYER_HAS_OBJECT_COMPARISON(JapanBaseDefense) never held
           (场帧's thousands 0) while the area count did -- not looked into (still unfolding: not counted as owned?).
    Simulator (sim: NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT with SpecialPower_UnpackReplaceSelf, REPLACE_FRAMES 6;
    tests/test_simbench.py test_mcv_deploys_at_a_far_waypoint_as_the_bench): mcv 586 44128 458458 586 (the yard from
    frame 128). egg 586 39108 478478 586 (round 139: the defense from frame 108; the egg came into the unit table once
    simunits.resolve read EditorSorting / KindOf up its chain from BaseEgg -- its own LocomotorSet writes Speed 60;
    test_nanocore_deploys_at_a_far_waypoint_as_the_bench). The bench's owned count of the defense (场帧's thousands 0)
    is not modelled: the sim counts it owned.

    Round 281 (11-21): pwr = j08's power plant egg at the waypoint; pin / mid = a07 / s07's untargeted press
    NAMED_USE_COMMANDBUTTON_ABILITY(egg, Command_UnPackJapanBaseDefenseEgg), standing (pin) or 1 s into its unpack trip
    (mid); 场帧's thousands then count a defense within 290 of the start (the way there) instead of owned. Bench pin
    CampUnpackPinGo_mcp_1121_123012 633 633 0 633, mid CampUnpackMidGo_mcp_1121_123227 632 632 0 632: nothing unfolds,
    and mid's egg stops short of the point. pwr CampUnpackPwrGo_mcp_1121_123504 632 28105 527 632: as egg (the plant from
    frame 105, never counted owned). crs = the defense egg pressed at the waypoint with the power plant egg's button (the
    same SpecialPower_UnpackReplaceSelf, not in its CommandSet). brk / ref / fac = a07 / j08's barracks, refinery and war
    factory eggs at the waypoint, as pwr. Round 322: nvl / jpn = j04's naval MCV and s02's Japanese MCV pressed their
    unpack button untargeted, standing (as pin); jpk = s02's escape, the MCV driving to the waypoint pressed the yard's
    Command_PackJapanMCV at it 1 s on (not in the MCV's CommandSet). Readings: engine_unpack.readings.toml.
    """
    import resources
    from maps import niagara
    from parts import Mission, Script, Test, square

    EGG = ('JapanBaseDefenseEgg', 'JapanBaseDefense', 'Command_UnPackJapanBaseDefenseEgg')
    KINDS = {'mcv': ('AlliedMCV', 'AlliedConstructionYard', 'Command_UnPackAlliedMCV'), 'egg': EGG,
             'pwr': ('JapanPowerPlantEgg', 'JapanPowerPlant', 'Command_UnPackJapanPowerPlantEgg'), 'pin': EGG, 'mid': EGG,
             'crs': EGG[:2] + ('Command_UnPackJapanPowerPlantEgg',),
             **{v: (f'Japan{k}Egg', f'Japan{k}', f'Command_UnPackJapan{k}Egg')          # a07 / j08 / s07's eggs
                for v, k in (('brk', 'Barracks'), ('ref', 'Refinery'), ('fac', 'WarFactory'))},
             'nvl': ('AlliedMCV_Naval', 'AlliedConstructionYard', 'Command_UnPackAlliedMCV'),      # j04's, untargeted
             'jpn': ('JapanMCV', 'JapanConstructionYard', 'Command_UnPackJapanMCV'),                # s02's, untargeted
             'jpk': ('JapanMCV', 'JapanConstructionYard', 'Command_PackJapanMCV')}                  # s02's, at a waypoint
    PLAIN = ('pin', 'nvl', 'jpn')       # pressed untargeted, standing
    VARIANTS = tuple(KINDS)
    AT, THERE = ('west field', -200.0, 0.0), ('west field', 200.0, 0.0)
    NAME = 'UNIT - CNV Unpack'
    RUN = 40.0


    def mission(variant='mcv'):
        unit, yard, _ = KINDS[variant]
        m = Mission(name=f'CampUnpack{variant.title()}', map=resources.measured(niagara), units=[],
                    facts={'variant': VARIANTS.index(variant)})
        m.spawns |= {yard}
        m.put(unit, AT[0], *AT[1:], angle=0.0, role='unit', name=NAME)
        m.waypoint('there', 'Test Unpack There', *THERE)
        m.waypoint('short', 'Test Unpack Short', *AT)
        return m


    def frames(m):
        t = Test()
        v = VARIANTS[m.facts['variant']]
        unit, yard, button = KINDS[v]
        p1 = m.player('p1')
        t.areas['Test There'] = square(*m.point('there'), 100.0)
        t.areas['Test Short'] = square(*m.point('short'), 290.0)    # pin / mid: west of There, the egg's way included
        press = ('NAMED_USE_COMMANDBUTTON_ABILITY', NAME, button)
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0),
                                                     ('SET_MILLISECOND_TIMER', 'Test Mid', 2.0)]))
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')],
                                [press if v in PLAIN else ('MOVE_NAMED_UNIT_TO', NAME, m.mark('there')) if v == 'jpk' else
                                 ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', NAME, button, m.mark('there')),
                                 ('SET_FLAG', 'Test Going', 1)]))
        if v == 'mid':      # pressed again untargeted on its way (a07 / s07's eggs when attacked)
            t.scripts.append(Script('Test - mid', [('TIMER_EXPIRED', 'Test Mid')], [press]))
        if v == 'jpk':      # s02's escape: the packed MCV on its way pressed the yard's pack button at the point
            t.scripts.append(Script('Test - mid', [('TIMER_EXPIRED', 'Test Mid')],
                                    [('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', NAME, button, m.mark('there'))]))
        going = ('FLAG', 'Test Going', 1)

        def per_frame(counter, label, rows):
            t.counters.append((counter, label))
            t.scripts += [Script(f'Test - {counter} {k}', [going, cond], [('INCREMENT_COUNTER', step, counter)],
                                 once=False) for k, (cond, step) in enumerate(rows)]

        per_frame('CNV_Unpack_Frames', '帧数', [(going, 1)])
        per_frame('CNV_Unpack_Unit', '车帧', [(('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, unit,
                                                'Test There'), 1000),
                                              (('PLAYER_HAS_OBJECT_COMPARISON', p1, 3, 1, unit), 1)])
        per_frame('CNV_Unpack_Yard', '场帧', [(('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, yard,
                                                'Test There'), 1),
                                              (('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, yard, 'Test Short')
                                               if v in PLAIN + ('mid',) else ('PLAYER_HAS_OBJECT_COMPARISON', p1, 3, 1, yard),
                                               1000)])
        per_frame('CNV_Unpack_Name', '名字帧', [(('NAMED_NOT_DESTROYED', NAME), 1)])
        t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
        return t


    MISSION = {f'engine_unpack_{v}': (lambda v=v: mission(v)) for v in VARIANTS}
    CHECKS = {f'engine_unpack_{v}': {'go': frames} for v in VARIANTS}      # mod CampUnpackMcvGo: 15 characters at most
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def plan_words():
    """The plan words probe (plan_words in scenes.py), read off the counters:

    words: money climbs by its bonus every gap (the first at once); one guardian is given between its random window's
      two ends; the shielded warrior stands while the control beside it falls, and falls once its shield is undone.
    """
    from parts import Script, Test, counted

    LAG = 4.0                                       # the bench's clock runs ~3 s behind the mission's (a4 LEAD)


    def alive(t, counter, label, name):
        t.counters.append((counter, label))
        t.scripts += [Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False),
                      Script(f'Test - {counter} up', [('NAMED_NOT_DESTROYED', name)], [('SET_COUNTER', counter, 1)],
                             once=False)]


    def words(m):
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        f = m.facts
        t.counters.append(('CNV_PW_Money', '资金'))
        t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', m.player('p1'), 'CNV_PW_Money')],
                                once=False))
        counted('CNV_PW_Guardians', '守护者', t, template='AlliedAntiVehicleVehicleTech1')
        alive(t, 'CNV_PW_Shielded', '无敌的', m.role('shielded').name)
        alive(t, 'CNV_PW_Control', '对照', m.role('control').name)
        money, bonus, gap = f['money'], f['bonus'], f['gap']
        t.expect += [
            # the first at once, then one more each gap: by 20 s at least four more, not more than six
            ('资金', 2, 'ever>=', money + bonus, 8), ('资金', 22, '>=', money + 4 * bonus, 26),
            ('资金', 22, '<=', money + 6 * bonus, 26),
            ('守护者', 1, '==', 2, f['give from'] - LAG), ('守护者', f['give until'] + LAG, '==', 3, 26),
            ('对照', f['undo at'] - LAG, '==', 0, f['undo at'] - 2), ('无敌的', 1, '==', 1, f['undo at'] - 2),
            ('无敌的', f['undo at'] + 15, '==', 0)]
        t.bench = [('bench_watch', dict(seconds=f['undo at'] + 20, every=2, sheet=False, lines=len(t.counters)))]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'plan_words': {'words': words},
    }
    return dict(CHECKS=CHECKS)


BENCHES = (engine_assistplace_e, engine_bankcapture, engine_baseban, engine_build, engine_countmodifier,
           engine_mining, engine_pack, engine_place, engine_powerdef, engine_powerupgrade_e, engine_production,
           engine_rally, engine_replace, engine_sell, engine_sellall, engine_share, engine_structureplace_e,
           engine_tech, engine_threatbonus, engine_unpack, plan_words,)
