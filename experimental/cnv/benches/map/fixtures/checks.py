"""Map fixtures bench checks."""


FOES, OURS, FRIENDS = (f"<1st Human Player's {k}>" for k in ('Enemies', 'Allies incl Self', 'Allies'))

FIELDS = ('End', 'End2', 'Center', 'Center2', 'GateHouse')


def crane():
    """Paper crane tests (no map reveal: the shroud is the point). At GO_AT the scout is sent to the stop point, 700
    short of an enemy Guardian in the shroud.

    spot: the crane gets there and the Guardian is discovered (a latch: NAMED_DISCOVERED for the player).
    blind (with retail's Twinblade, the control): it gets there, the Guardian stays undiscovered.
    """
    from parts import Script, Test, counted, square

    GO_AT = 10.0
    STOP = 100.0                                    # half-side of the area around the stop point


    def trip(m, seen):
        t = Test()
        scout, target = m.role('scout').name, m.role('target').name
        t.scripts.append(Script('Test - start', [], [('SET_MILLISECOND_TIMER', 'Test - go timer', GO_AT)]))
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                                [('MOVE_NAMED_UNIT_TO', scout, m.mark('stop'))]))
        t.areas['Test Stop'] = square(*m.point('stop'), STOP)
        t.counters.append(('Test Seen', '发现目标'))
        t.scripts.append(Script('Test - seen', [('NAMED_DISCOVERED', m.player('p1'), target)],
                                [('SET_COUNTER', 'Test Seen', 1)]))
        counted('Test There', '到达', t, named=scout, area='Test Stop')
        t.expect += [('发现目标', 0, '==', 0, GO_AT - 2), ('到达', GO_AT, 'ever==', 1),
                     ('发现目标', GO_AT, 'ever==' if seen else '==', 1 if seen else 0)]
        t.bench = [('bench_watch', dict(seconds=45, every=3, sheet=False, lines=len(t.counters)))]
        return t


    def hide(m):
        """At GO_AT both cranes are sent over their IFVs: A (no detector there) comes through untouched, B (a war bear
        with its IFVs) is hit."""
        t = Test()
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('SET_MILLISECOND_TIMER', 'Test - go timer', GO_AT)]))
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                                [('MOVE_NAMED_UNIT_TO', m.role(f'crane {k}').name, m.mark(f'over {k}')) for k in 'AB']))
        for k in 'AB':
            counted(f'Test Crane {k}', f'{k} 纸鹤血量', t, health=m.role(f'crane {k}').name)
        t.expect += [('A 纸鹤血量', 0, '==', 100), ('B 纸鹤血量', GO_AT, 'ever<', 100)]
        t.bench = [('bench_watch', dict(seconds=40, every=3, sheet=False, lines=len(t.counters)))]
        return t


    def spot(m):
        return trip(m, True)


    def blind(m):
        return trip(m, False)


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'crane': {'spot': spot},
        'crane_hide': {'hide': hide},
        'crane_retail': {'blind': blind},
    }
    return dict(CHECKS=CHECKS)


def engine_area():
    """Engine unit test: whose units the trigger-area counts count (E1; bench 2026-10-25 and 2026-11-04, probe/count).

    Measured: counting by KindOf in an area counts every player's units, whichever player the condition names; counting
    by template, and SKIRMISH_PLAYER_HAS_UNITS_IN_AREA, count only that player's. So "the player has fewer than N
    fighting units there" written as a kind count also counts the enemy, the neutrals and the allies standing there.
    Three of the player's guardians stand in the west field, two enemy warriors at the north base, each in an area:
      field (west field):the player's kind count 3; the enemy's kind count 3 too (the player's three); the enemy's template
        count 0; the enemy "has units" 0;
      camp (north base): the player's kind count 2 (the enemy's two warriors); the player's template count of warriors 0.
    probe/count asks the same in the west field and expects the per-player reading (it FAILs: the record of the guess).
    als (A347, l2_scripts1 1: a player argument is a mask): PLAYER_SET_MONEY 1000 for p1 and s1 at the start, 7000 for
      "<1st Human Player's Enemies>" at 3 s (retail 9 times); 钱 = PLAYER_HAS_CREDITS >= 5000 s1 1 / p1 2 / the alias 4,
      p1 >= 1000 8; 有 = SKIRMISH_PLAYER_HAS_UNITS_IN_AREA (retail 10 times with an alias) the enemies at the camp 1 /
      in the field 2, the allies incl self in the field 4, the allies (not self) 8. Predicted: 8 then 13; 有 5.
    cash (A349): every player's start money, no script setting any (measured: 10000 each = each faction's PlayerTemplate StartingMoney, Money.start).
    """
    from maps import festival
    from parts import Mission, Script, Test, counted, kindof, square
    import checks.engine_scripts8 as s8


    WARRIOR = 'JapanAntiInfantryInfantry'
    GUARDIAN = 'AlliedAntiVehicleVehicleTech1'


    def mission():
        m = Mission(name='CampArea', map=festival, facts={})
        for k in (0, 1, 2):
            m.put(GUARDIAN, 'west field', 250, 30 + 60 * k, name=f'UNIT - CNV Area Guardian {k}', role=f'guardian {k}')
        for k in (1, 2):
            m.put(WARRIOR, 'north base', 60 * k, 0, side='s1', name=f'UNIT - CNV Area Warrior {k}', role=f'warrior {k}')
        return m


    def _test(m):
        t = Test()
        t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
        t.bench = [('bench_watch', dict(seconds=12, every=3, sheet=False, lines=4))]
        return t


    def field(m):
        t = _test(m)
        t.areas['Test field'] = square(*m.site('west field'), 450)
        s1 = m.player('s1')
        counted('CNV_Area_KindP1', '区内我方能打的', t, kind=kindof('CAN_ATTACK'), area='Test field')
        counted('CNV_Area_KindS1', '区内敌方能打的', t, kind=kindof('CAN_ATTACK'), area='Test field', player=s1)
        counted('CNV_Area_TypeS1', '区内敌方守护者', t, template=GUARDIAN, area='Test field', player=s1)
        t.counters.append(('CNV_Area_HasS1', '区内敌方有人'))
        t.scripts += [Script('Test - has zero', [], [('SET_COUNTER', 'CNV_Area_HasS1', 0)], once=False),
                      Script('Test - has', [('SKIRMISH_PLAYER_HAS_UNITS_IN_AREA', s1, 'Test field')],
                             [('SET_COUNTER', 'CNV_Area_HasS1', 1)], once=False)]
        t.expect += [('区内我方能打的', 3, '==', 3), ('区内敌方能打的', 3, '==', 3), ('区内敌方守护者', 3, '==', 0),
                     ('区内敌方有人', 3, '==', 0)]
        return t


    def camp(m):
        t = _test(m)
        t.areas['Test camp'] = square(*m.site('north base', 90, 0), 150)
        counted('CNV_Area_CampKindP1', '敌营我方能打的', t, kind=kindof('CAN_ATTACK'), area='Test camp')
        counted('CNV_Area_CampTypeP1', '敌营我方武士', t, template=WARRIOR, area='Test camp')
        t.expect += [('敌营我方能打的', 3, '==', 2), ('敌营我方武士', 3, '==', 0)]
        return t


    def alias(m):
        t = _test(m)
        t.areas['Test field'], t.areas['Test camp'] = square(*m.site('west field'), 450), square(*m.site('north base', 90, 0), 150)
        p1, s1 = m.player('p1'), m.player('s1')
        t.scripts.append(Script('Test - money', [], [('PLAYER_SET_MONEY', p1, 1000), ('PLAYER_SET_MONEY', s1, 1000)]))
        s8.at(t, 'foes', 3.0, [('PLAYER_SET_MONEY', FOES, 7000)])
        s8.total(t, 'CNV_Area_Cash', '钱', [(w, ('PLAYER_HAS_CREDITS', who, 3, n)) for w, who, n in (
            (1, s1, 5000), (2, p1, 5000), (4, FOES, 5000), (8, p1, 1000))])
        s8.total(t, 'CNV_Area_Has', '有', [(w, ('SKIRMISH_PLAYER_HAS_UNITS_IN_AREA', who, area)) for w, who, area in (
            (1, FOES, 'Test camp'), (2, FOES, 'Test field'), (4, OURS, 'Test field'), (8, FRIENDS, 'Test field'))])
        s8.watch(t, 10, every=0.5)
        return t


    LADDER = (1, 1000, 1500, 1501, 2000, 5000, 5001, 10000, 10001, 20000, 20001, 50000, 50001, 100000)


    def cash(m):
        """cash (A349): no script money; a player's count = the steps of LADDER its PLAYER_HAS_CREDITS >= holds; two players
        a counter (only four lines fit): 钱 = the first's + 15 x the second's (p1 s1 | s2 s3 | s4 s5 | s6)."""
        t = _test(m)
        for i, pair in enumerate((('p1', 's1'), ('s2', 's3'), ('s4', 's5'), ('s6',))):
            s8.total(t, f'CNV_Area_Cash{i}', f'钱{i}', [(15 ** j, ('PLAYER_HAS_CREDITS', m.player(k), 3, n))
                                                      for j, k in enumerate(pair) for n in LADDER])
        s8.watch(t, 6, every=1.0)
        return t


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_area': mission}
    CHECKS = {'engine_area': {'field': field, 'camp': camp, 'als': alias, 'cash': cash}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_bridgebuilder():
    """HB_Bridge_02 generation only, Niagara 270 / 700, no damage or engineers.

    XML: end caps 75 each, alternating centers A/B 150 each, two gatehouses.
    Prediction (rounding INFERRED): ceil((length-150)/150) centers, A first:
    270 -> End/End2/A/B/Gate = 1/1/1/0/2; 700 -> 1/1/2/2/2.
    Each decimal digit is count+1 (0 means no matching count, NOT zero objects).
    Ends row = (Gate+1)*100 + (End2+1)*10 + End+1; center = (B+1)*10+A+1.
    Only exact equality 0..7 is encoded; overflow or unavailable conditions cannot
    masquerade as a valid zero. All five precise retail templates are queried.
    BENCH 2026-11-11: s1-s23 322/12/322/33; all stable-window expectations PASS.
    Only the two observed lengths are modeled; arbitrary-length rounding stays open.
    """
    from types import SimpleNamespace

    import platmap
    from maps import island, niagara
    from parts import Mission, Script, Test, square



    def mission():
        probe_map = SimpleNamespace(**vars(niagara))
        probe_map.PLAYERS = {**niagara.PLAYERS, **island.NEUTRAL}
        probe_map.OBJECTS = niagara.OBJECTS[6:]  # remove all three original bridge pairs
        m = Mission(name='CampBridge', map=probe_map, units=[])
        m.spawns.update('HB_Bridge_02_' + field for field in FIELDS)
        origin = m.site('front')
        for role, (p, q) in zip(('short', 'long'), (niagara.BRIDGES[0], niagara.BRIDGES[2])):
            for k, (x, y, angle, flags) in enumerate(platmap.bridge(p, q)):
                m.put('HB_Bridge_02', 'front', x-origin[0], y-origin[1], side='neutral',
                      angle=angle, flags=flags, role=f'{role} {k}', name=f'Bridge {role} {k}')
            # Include gatehouses outside the endpoints; no other bridge in this region.
            m.areas['Bridge ' + role] = square((p[0]+q[0])/2, p[1], 550)
        return m


    def check(m):
        t = Test()
        t.scripts = [Script('Bridge reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
        for role, labels, values in (('short', ('短端量', '短中量'), (322, 12)),
                                      ('long', ('长端量', '长中量'), (322, 33))):
            rows = [f'Bridge {role} ends', f'Bridge {role} centers']
            t.counters += list(zip(rows, labels))
            t.scripts.append(Script('Bridge reset ' + role, [],
                                    [('SET_COUNTER', row, 0) for row in rows], once=False))
            for field, row, weight in zip(FIELDS, (rows[0], rows[0], rows[1], rows[1], rows[0]),
                                          (1, 10, 1, 10, 100)):
                for n in range(8):
                    t.scripts.append(Script(f'Bridge {role} {field} {n}', [
                        ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player('neutral'),
                         2, n, 'HB_Bridge_02_' + field, 'Bridge ' + role)], [
                        ('INCREMENT_COUNTER', (n+1)*weight, row)], once=False))
            t.expect += [(label, 4, '==', value, 18) for label, value in zip(labels, values)]
        t.bench = [('bench_watch', dict(seconds=20, every=1, sheet=False, lines=4))]
        return t


    MISSION = {'engine_bridgebuilder': mission}
    CHECKS = {'engine_bridgebuilder': {'a': check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_bridgebuilder_b():
    """Retail mixed pair: HB_Bridge_02 start (16), Bridge1a end (32).

    Retail J02 uses this exact pair. Niagara lengths 270/700 keep known geometry.
    Prediction INFERRED before bench: start config wins, HB counts 1/1/1/0/2
    and 1/1/2/2/2; all five Bridge1 template counts zero. Add 1000 only when
    all five zero queries succeed; missing conditions must not look like zero.
    No damage, engineers, health sharing, pathing or repair.
    BENCH 2026-11-11: s1-s21 = 1322/12/1322/33, all expectations PASS.
    """
    from parts import Script

    base = engine_bridgebuilder()
    base_mission = base['MISSION']['engine_bridgebuilder']
    base_check = base['CHECKS']['engine_bridgebuilder']['a']
    FOREIGN = tuple('Bridge1_' + suffix for suffix in FIELDS)


    def mission():
        m = base_mission()
        m.name = 'CampBridgeB'
        for o in m.objects:
            if o.flags == 32:
                o.template = 'Bridge1a'
        for role in ('short 1', 'long 1'):
            m.cast[role].template = 'Bridge1a'
        m.spawns.update(FOREIGN)
        return m


    def check(m):
        t = base_check(m)
        for role in ('short', 'long'):
            t.scripts.append(Script('Bridge foreign zero ' + role, [
                ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player('neutral'),
                 2, 0, template, 'Bridge ' + role) for template in FOREIGN], [
                ('INCREMENT_COUNTER', 1000, 'Bridge ' + role + ' ends')], once=False))
        t.expect = [(label, start, op, value + (1000 if i % 2 == 0 else 0), until)
                    for i, (label, start, op, value, until) in enumerate(t.expect)]
        return t


    MISSION = {'engine_bridgebuilder_b': mission}
    CHECKS = {'engine_bridgebuilder_b': {'b': check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_bridgefix():
    """A315: Command_CaptureBuilding pressed on a bridge's gatehouse (retail j07 'if first bridge destroyed').

    j07 creates an AlliedEngineer on a computer team and presses NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED
    Command_CaptureBuilding at 'o_bridge_00_GateHouse2' -- a name the bridge's BridgeBuilder gives its gatehouse
    (retail: the start and the end object share the bridge's name; j07 asks UNIT_HEALTH <= 1 of it for 'destroyed').
    Niagara's three HB_Bridge_02 (managerbody's proven geometry): a broken by NAMED_DAMAGE 20000 at s8 (managerbody b:
    the proxy shows 1 %), an engineer of s1 created 150 west of its start at s14 and pressed; b the same on the whole
    bridge; c broken, no engineer (control). Lane c's end keeps the start's name, as j07; a and b's end is '<name> end'.
    PREDICTION (from HB_Bridge_02_GateHouse's ModuleTag_EngineerContainBridge, not measured): the engineer walks to
    the gatehouse, is consumed, the broken bridge's gatehouse goes back to 100; c stays 1.

    Run 1 (bench 11-22, CampBridgeFixA_mcp_1122_202051, both lanes pressed at GateHouse2): both names exist under
    either naming (start name + '_GateHouse1' / '2'); GateHouse2 not within 150 of the start; 门a / 门c 100 s1-s6,
    1 from s7 (the break); the engineers alive to s53, nobody repaired, s1 owns nothing; UNIT_HEALTH('Fix a', 4, 50)
    held true after the break. Run 2: a presses GateHouse1 (the near one?), b GateHouse2 of the whole bridge, and
    each engineer's 'left its spawn' digit tells whether the press moved it at all.
    Counters: 门a the target GateHouse1's health, 门c lane c's GateHouse1; 态a / 态b digits 1 engineer alive,
    10 engineer away from its spawn, 100 its target there, 1000 the target within 150 of the start, 10000 s1 owns it.
    Run 2 (CampBridgeFixA_mcp_1122_202537): 门a / 态a / 态b / 门c s1-s6 100 1110 110 100; s7-s13 1 1110 110 1; s14
    1 1101 101 1; s15-s17 1 1111 111 1; s18-s68 100 1110 111 1 -- a's engineer (pressed at the near GateHouse1, which is
    the start's) walked up and was gone at s18 with the bridge mended, the owner kept; b's (the whole bridge's far
    GateHouse2) walked off and lived on. The 10 digit is also set while the engineer does not exist (NAMED_OUTSIDE_AREA).
    """
    from types import SimpleNamespace

    import platmap
    from maps import island, niagara
    from parts import Mission, Script, Test, square

    # (lane, bridge, broken, engineer's target)
    LANES = (('a', 0, True, 'Fix a_GateHouse1'), ('b', 1, False, 'Fix b_GateHouse2'), ('c', 2, True, None))


    def mission():
        probe_map = SimpleNamespace(**vars(niagara))
        probe_map.PLAYERS = {**niagara.PLAYERS, **island.NEUTRAL}
        probe_map.OBJECTS = niagara.OBJECTS[6:]                     # all three retail pairs replaced by named ones
        m = Mission(name='CampBridgeFix', map=probe_map, units=[])
        m.spawns.add('AlliedEngineer')
        ox, oy = m.site('front')
        for lane, k, _, target in LANES:
            p, q = niagara.BRIDGES[k]
            for end, (x, y, angle, flags) in zip(('', ' end'), platmap.bridge(p, q)):
                name = 'Fix ' + lane + ('' if lane == 'c' else end)
                m.put('HB_Bridge_02', 'front', x - ox, y - oy, side='neutral', angle=angle, flags=flags,
                      role=f'{lane}{end}', name=name)
            m.areas['Fix start ' + lane] = square(p[0], p[1], 150)
            if target:
                m.waypoint(lane + ' spawn', 'Fix spawn ' + lane, 'front', p[0] - 150 - ox, p[1] - oy)
                m.areas['Fix home ' + lane] = square(p[0] - 150, p[1], 40)
        return m


    def check(m):
        t = Test()
        s1 = m.player('s1')
        t.scripts = [Script('Fix start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                              ('SET_MILLISECOND_TIMER', 'Fix break', 8.0),
                                              ('SET_MILLISECOND_TIMER', 'Fix press', 14.0)]),
                     Script('Fix no budget', [], [('PLAYER_SET_MONEY', s1, 0)], once=False),
                     Script('Fix break', [('TIMER_EXPIRED', 'Fix break')],
                            [('NAMED_DAMAGE', 'Fix ' + lane, 20000) for lane, _, broken, _ in LANES if broken])]
        press = []
        for lane, _, _, target in LANES:
            state, man = 'Fix state ' + lane, 'Fix man ' + lane
            if lane != 'b':
                t.counters.append(('Fix gate ' + lane, '门' + lane))
                t.scripts.append(Script('Fix read gate ' + lane, [], [
                    ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', f'Fix {lane}_GateHouse1', 'Fix gate ' + lane)], once=False))
            if not target:
                continue
            t.counters.append((state, '态' + lane))
            press += [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', man, 'AlliedEngineer', m.team('s1'), m.mark(lane + ' spawn')),
                      ('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', man, 'Command_CaptureBuilding', target)]
            t.scripts.append(Script('Fix zero ' + lane, [], [('SET_COUNTER', state, 0)], once=False))
            for bit, when in ((1, ('NAMED_NOT_DESTROYED', man)), (10, ('NAMED_OUTSIDE_AREA', man, 'Fix home ' + lane)),
                              (100, ('NAMED_NOT_DESTROYED', target)),
                              (1000, ('NAMED_INSIDE_AREA', target, 'Fix start ' + lane)),
                              (10000, ('NAMED_OWNED_BY_PLAYER', s1, target))):
                t.scripts.append(Script(f'Fix bit {lane} {bit}', [when], [('INCREMENT_COUNTER', bit, state)], once=False))
        t.scripts.append(Script('Fix press', [('TIMER_EXPIRED', 'Fix press')], press))
        t.expect = [('门a', 3, '==', 100, 7), ('门a', 10, '==', 1, 14), ('门c', 10, '==', 1, 60),
                    ('门a', 50, '==', 100, 60), ('态a', 50, '==', 1110, 60), ('态b', 50, '==', 111, 60)]
        t.bench = [('bench_watch', dict(seconds=62, every=1, sheet=False, lines=4))]
        return t


    MISSION = {'engine_bridgefix': mission}
    CHECKS = {'engine_bridgefix': {'a': check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_gate_e():
    """E190: native door-template resolution after the SDK rejects the module.

    The SDK schemas reject GateOpenAndCloseBehavior inside Behaviors. Do not
    replace it with scripted model flags. Place both native templates without
    compiling their XML, using the same script creation action as a known retail
    building sentinel. Map placement also forced SDK compilation and failed.
    Predict f180 frame/Romania door/sanitarium door/sentinel = 180/0/0/1.
    This is a template prerequisite diagnostic, NOT a gate-module deletion
    control or opening/pathing coverage. See work/re/e190_gate.md for the failed
    four-door initialization probe and the exact compiler evidence.
    MEASURED a PASS: f180=180/0/0/1; only the known building exists at sampling.
    The simulator makes both doors (readings: a mismatch row). Missing versus
    rejected creation is INFERRED; no template-resolution/acceptance field is
    available in the four HUD rows. No gate effect coverage is registered.
    """
    from maps import probe_range
    from model import Mission, Role, Script, Test


    def mission():
        m = Mission(name='CampGateNatE', map=probe_range, units=[])
        m.put('AlliedConstructionYard', 'base factory', role='anchor', name='E190 anchor')
        # Runtime cast creation belongs to the mission, including builds without a check.
        m.scripts = [Script('Test - clock', [('COUNTER', 'E190Frame', 0, 180)],
                            [('INCREMENT_COUNTER', 1, 'E190Frame')], once=False)]
        for template, tag, site in [
            ('RM_AlliedBlastDoor', 'Romania', 'base gun'),
            ('SS_Door', 'Sanitarium', 'high gun'),
            ('AlliedPowerPlant', 'Sentinel', 'removed gun')]:
            m.cast[tag] = Role(template, 'E190 ' + tag, 'p1', [site])
            m.waypoint(tag, 'E190 point ' + tag, site)
            m.scripts.append(Script('Test - create ' + tag, [('COUNTER', 'E190Frame', 2, 30)],
                [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', m.role(tag).name,
                  m.role(tag).template, m.team(), m.mark(tag))]))
        return m


    def check(m):
        t = Test()
        t.counters = [('E190Frame', 'frame'), ('E190Romania', 'Romania'),
                      ('E190Sanitarium', 'Sanitarium'), ('E190Sentinel', 'sentinel')]
        for tag in ('Romania', 'Sanitarium', 'Sentinel'):
            t.scripts.append(Script('Test - live ' + tag, [
                ('COUNTER', 'E190Frame', 2, 180),
                ('NAMED_NOT_DESTROYED', m.role(tag).name)],
                [('SET_COUNTER', 'E190' + tag, 1)]))
        t.expect = [('frame', 0, 'ever==', 180), ('Romania', 0, '==', 0),
                    ('Sanitarium', 0, '==', 0), ('sentinel', 0, 'ever==', 1)]
        t.bench = [('bench_watch', dict(seconds=100, every=1, sheet=False, lines=4, until='c1>=180'))]
        return t


    MISSION = {'engine_gate_e': mission}
    CHECKS = {'engine_gate_e': {'a': check}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_see():
    """Engine unit test: a tower on high ground, an Athena cannon below it (A6, docs/story/plans/a6.md 待做 1).

    Two questions: does a unit on the low ground see a tower up on the outer ring, and can it hit it then; and once a
    spotter of ours on the ring sees the tower, does the cannon below -- which still cannot see it itself -- fire when
    it is ordered to (know-how.md: a unit picks targets only inside its own vision; this asks about the player's order).

    The map is A6's stonehenge (imported only: outer ring tier 2, ~115 elevation above the low ground). The probe places
    its own cast, retail units; the enemy has no power plant (its towers may well be offline: they do not matter as
    shooters here). Three arms, each a tower of the enemy's (AlliedBaseDefense: range 300, vision 300) and a cannon of
    the player's (AlliedAntiStructureVehicle: weapon range 500, minimum 200, vision 500), 400 apart:
      W  blind   tower on the ring's west rim, the cannon below to the west; nobody of ours on the ring
      E  spotter tower on the ring's east side, the cannon below to the east; Tanya (vision 200) on the ring 150 from it
      S  level   tower and cannon both on the ring's south side (the control: the cannon sees and hits at 400)
    No orders before ORDER (does anything fire by itself?). At ORDER the script orders cannon W and S to attack their
    towers; cannon E: check `order` orders it by script too, check `click` leaves it to the bench -- select it with a
    left click, right click the tower (the player's own order, as a player gives it).

    Counters: 看见 = W 1 + E 10 + S 100, each added once the player has discovered that tower (NAMED_DISCOVERED), + 1000
    once Tanya is below full health (does the tower shoot?); 血西/东/南 the tower's health in percent.
    """
    from maps import stonehenge
    from parts import Mission, Script, Test, counted
    from checks.probe_view import open_in_view

    TOWER, CANNON, TANYA = 'AlliedBaseDefense', 'AlliedAntiStructureVehicle', 'AlliedCommandoTech1'
    ORDER, RUN = 8.0, 40.0
    # arm: (tower x, y), (cannon x, y) -- the ring is the circle r 720 about (1900, 1350) less the inner platform's r 380
    ARMS = {'W': ((1280.0, 1350.0), (880.0, 1350.0)),
            'E': ((2420.0, 1250.0), (2820.0, 1250.0)),
            'S': ((1700.0, 800.0), (2100.0, 800.0))}
    SPOTTER = (2420.0, 1100.0)                       # on the ring (r ~577), 150 south of tower E
    LABELS = {'W': '西', 'E': '东', 'S': '南'}


    def mission():
        m = Mission(name='CampSee', map=stonehenge, facts={})
        cx, cy = m.site('start')
        for k, ((tx, ty), (ax, ay)) in ARMS.items():
            m.put(TOWER, 'start', tx - cx, ty - cy, side='s1', name=f'UNIT - CNV See Tower {k}', role=f'tower {k}')
            m.put(CANNON, 'start', ax - cx, ay - cy, name=f'UNIT - CNV See Cannon {k}', role=f'cannon {k}',
                  angle=3.1416 if k == 'W' else 0.0)
        m.put(TANYA, 'start', SPOTTER[0] - cx, SPOTTER[1] - cy, name='UNIT - CNV See Tanya', role='tanya', angle=1.5708)
        return open_in_view(m, 'See')      # K5: the start is too near the map's edge


    def _test(m, clicked=None):
        """clicked: the arm whose cannon the bench orders by hand (the rest by script at ORDER); None: all by script."""
        t = Test()
        p1 = m.player('p1')
        arms = [k for k in ARMS if k != clicked]
        # bench 2026-11-04: left alone, Tanya ran up and blew tower E with her C4 by s2 -- she is the eyes only here:
        # hold fire (stance 3, Stance.xsd's order) and no auto-acquire
        tanya = m.role('tanya').name
        t.scripts += [Script('Test - start', [], [('UNIT_SET_STANCE', tanya, 3), ('UNIT_ALLOW_AI_AUTOACQUIRE', tanya, 0),
                                                  ('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]),
                      Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                             [('NAMED_ATTACK_NAMED', m.role(f'cannon {k}').name, m.role(f'tower {k}').name)
                              for k in arms])]
        # one line for what is seen (only four counter lines fit): W 1, E 10, S 100 once discovered; 1000 once Tanya hurts
        c = 'Test See'
        t.counters.append((c, '看见'))
        t.scripts.append(Script('Test - see zero', [], [('SET_COUNTER', c, 0)]))
        for i, k in enumerate(ARMS):
            t.scripts.append(Script(f'Test - see {k}', [('NAMED_DISCOVERED', p1, m.role(f'tower {k}').name)],
                                    [('INCREMENT_COUNTER', 10 ** i, c)]))
        t.scripts.append(Script('Test - tanya hurt', [('UNIT_HEALTH', m.role('tanya').name, 0, 100)],
                                [('INCREMENT_COUNTER', 1000, c)]))
        for k, zh in LABELS.items():
            counted(f'Test Hp {k}', f'血{zh}', t, health=m.role(f'tower {k}').name)
        # the controls: the level cannon sees its tower and hurts it once ordered; Tanya sees tower E
        t.expect += [('看见', 0, 'ever>=', 110), ('血南', ORDER, 'ever<', 100)]
        lines = len(t.counters)
        if clicked is None:
            t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=lines))]
        else:
            # the camera put by script, exactly (bench 2026-11-04: after bench_camera's minimap click the left click
            # missed the cannon by ~70 px and nothing was selected)
            (tx, ty), (ax, ay) = ARMS[clicked]
            eye = ((tx + ax) / 2, ty)
            t.waypoints['Test Eye'] = eye
            t.scripts.append(Script('Test - camera', [], [('MOVE_CAMERA_TO', 'Test Eye', 0.1, 0.0, 0.0, 0.0)]))
            t.bench = [('bench_watch', dict(seconds=ORDER, every=2, sheet=False, lines=lines)),
                       # each input leaves its pause record (gameport's transcript answers every input by one)
                       ('bench_view', dict(x=eye[0], y=eye[1], look=True)),
                       ('bench_click', dict(x=ax, y=ay, look=True)),
                       # the ring stands higher than the ground the bench maps clicks on: the tower is drawn ~22 px left
                       # and ~24 px up of its ground point (bench 2026-11-04: a right click there was a move order)
                       ('bench_click', dict(x=tx - 14.0, y=ty + 20.0, right=True, look=True)),
                       ('bench_watch', dict(seconds=RUN - ORDER, every=2, sheet=False, lines=lines))]
        return t


    def order(m):
        return _test(m)


    def click(m):
        return _test(m, clicked='E')


    def blind(m):
        """The player's right click on tower W, which nobody of ours has seen (the shroud over it)."""
        return _test(m, clicked='W')


    # the builds this module makes and their checks (cnv/registry.py)
    MISSION = {'engine_see': mission}
    CHECKS = {'engine_see': {'order': order, 'click': click, 'blind': blind}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def engine_vision():
    """Engine unit test: vision over high ground (ShroudClearingHeight) and how long a script's reveal lasts.

    Same stonehenge cast as engine_see (arms W and E; no Tanya, no S): an enemy tower (AlliedBaseDefense) on the ring and
    a player's Athena cannon (AlliedAntiStructureVehicle) on the low ground 400 away. Cannons hold fire (stance 3) and no
    auto-acquire, so nothing moves or shoots. Probe unit CNV_VisionHi = the retail cannon with ShroudClearingHeight="500"
    in its VisionInfo (CNV_VisionHi2: also ShroudClearingRange 500). Spare cannons stand in the cast and are deleted at the
    start, so one mission serves every check.

      height    W cannon = CNV_VisionHi, E cannon = retail. Counter 看见: W tower discovered 1, E tower discovered 10,
                W cannon ENEMY_SIGHTED 100, E cannon ENEMY_SIGHTED 1000. Prediction 1101 (E tower not discovered).
      height2   as height with CNV_VisionHi2 on W (ShroudClearingRange 500 as well)
      reshroud  both cannons retail. At Go (1 s) MAP_REVEAL_AT_WAYPOINT, radius 150, p1, on tower W. 揭开 = frames from
                Go on that NAMED_DISCOVERED(p1, tower W) is true; 帧数 = frames since Go. How long the reveal holds.
      resh5     as reshroud with MAP_SHROUD_SET_RESHROUD_TIME 5.0 (seconds: retail A04 uses 1.0) at the start.
      resh0 / resh1 / resh10   the same with 0, 1, 10: how the setting maps to frames.
      perm      as reshroud with MAP_REVEAL_PERMANENTLY_AT_WAYPOINT (name 'Test Look'): does it hold past 137 frames?
      undo      as perm, and MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT 'Test Look' at 11 s (Go + 10). 撤后 = frames from
                the undo on that the tower is still discovered: 0 = the fog comes back at once, ~137 = the reshroud delay.

      all       as reshroud with MAP_REVEAL_ALL p1 at Go (the whole map, not the permanent one): how long does it hold?
      allundo   MAP_REVEAL_ALL_PERM p1 at Go, MAP_REVEAL_ALL_UNDO_PERM p1 at Go + 10 (as undo): 揭开 while revealed,
                撤后 = frames tower W stays discovered after the undo (0 = fog at once, ~137 = the reshroud delay).

    (Check names are short: the mod name, mission + check, may not pass 15 characters.)

    Bench 11-06 (counters 看见 / 揭开 + 帧数; ~15 frames per second):
      height   CampVisHeight_mcp_1106_030642: 看见 1101 from the first reading (s1) to s21, as predicted: W tower
        discovered and both cannons ENEMY_SIGHTED with the ShroudClearingHeight 500 probe on W; E (retail cannon) the
        tower not discovered (no 10) yet its cannon is ENEMY_SIGHTED (the 1000). height2 not run (W already 1).
      reshroud CampVisReshroud_mcp_1106_030845: 揭开 follows 帧数 (29 at s1, 134 at s8), stops at 137 frames after Go
        (between s8 and s9, ~9.1 s) and stays 137 to the end (帧数 482): the reveal lapses after 137 frames.
      resh5    CampVisResh5_mcp_1106_031048 (MAP_SHROUD_SET_RESHROUD_TIME 5.0 at the start): 揭开 60 at s3, stops at 62
        frames (~4.1 s) and stays 62 (帧数 483): shorter than the default 137.
      resh1 CampVisResh1_mcp_1106_032237: 揭开 2. resh10 CampVisResh10_mcp_1106_032431: 137 (as the default).
      resh0 CampVisResh0_mcp_1106_032628: 0 (never shown). So a reveal holds 15 x N - 13 frames (docs/engine/vision.md 2).

    Bench 11-09 (engine line A round 119):
      perm  CampVisPerm_mcp_1109_085452: 揭开 = 帧数 from s1 (30) to s31 (483): MAP_REVEAL_PERMANENTLY_AT_WAYPOINT holds
        the whole run, far past the 137 frames of a plain reveal.
      undo  CampVisUndo_mcp_1109_085241: 揭开 = 帧数 to s9 (151), then stays 151 (帧数 484 at s31); 撤后 0 all along:
        MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT (by the reveal's name) puts the fog back the frame it runs, no reshroud
        delay. The simulator (sim.py reveals / peeks) reads the same for all seven variants
        (tests/test_simbench.py::test_vision_*).
    """
    import os

    import labpaths
    from maps import stonehenge
    from parts import Mission, Script, Test, Unit
    from checks.probe_view import open_in_view

    TOWER, CANNON = 'AlliedBaseDefense', 'AlliedAntiStructureVehicle'
    HI, HI2 = 'CNV_VisionHi', 'CNV_VisionHi2'
    GO, RUN = 1.0, {'height': 20.0, 'height2': 20.0, 'reshroud': 30.0, 'resh5': 30.0, 'resh1': 30.0, 'resh10': 30.0,
                   'resh0': 30.0, 'perm': 30.0, 'undo': 30.0, 'all': 30.0, 'allundo': 30.0}
    UNDO = 10.0  # undo: seconds after Go
    TOWERS = {'W': (1280.0, 1350.0), 'E': (2420.0, 1250.0)}
    # role: (template, x, y); W has three cannons (probe, probe2, control), the unused ones are deleted at the start
    CANNONS = {'W': (HI, 880.0, 1350.0), 'W2': (HI2, 880.0, 1450.0), 'W0': (CANNON, 880.0, 1250.0),
               'E': (CANNON, 2820.0, 1250.0)}


    def probe(id, rng=False):
        x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', CANNON + '.xml'), encoding='utf-8').read()
        old = 'VisionRange="500"\n\t\t\tShroudClearingRange="=$STANDARD_SHROUD_CLEAR"'
        new = ('VisionRange="500"\n\t\t\tShroudClearingHeight="500"\n\t\t\tShroudClearingRange="'
               + ('500' if rng else '=$STANDARD_SHROUD_CLEAR') + '"')
        for o, n in ((f'id="{CANNON}"', f'id="{id}"'), (f'EditorName="{CANNON}"', f'EditorName="{id}"'), (old, new)):
            assert x.count(o) == 1, (o[:50], x.count(o))
            x = x.replace(o, n, 1)
        return Unit(id, x, names=dict(unit=id), what='引擎探针：原版雅典娜炮，ShroudClearingHeight 500',
                    params=dict(height=500, range=rng))


    def mission():
        m = Mission(name='CampVis', map=stonehenge, units=[probe(HI), probe(HI2, True)], facts={})
        cx, cy = m.site('start')
        for k, (tx, ty) in TOWERS.items():
            m.put(TOWER, 'start', tx - cx, ty - cy, side='s1', name=f'UNIT - CNV Vis Tower {k}', role=f'tower {k}')
        for k, (tmpl, ax, ay) in CANNONS.items():
            m.put(tmpl, 'start', ax - cx, ay - cy, name=f'UNIT - CNV Vis Cannon {k}', role=f'cannon {k}',
                  angle=0.0 if k == 'E' else 3.1416)
        return open_in_view(m, 'Vision')


    def _test(m, which):
        t = Test()
        p1, s1 = m.player('p1'), m.player('s1')
        keep = {'height': ('W', 'E'), 'height2': ('W2', 'E')}.get(which, ('W0', 'E'))
        start = []
        for k in CANNONS:
            n = m.role(f'cannon {k}').name
            if k in keep:
                start += [('UNIT_SET_STANCE', n, 3), ('UNIT_ALLOW_AI_AUTOACQUIRE', n, 0)]
            else:
                start.append(('NAMED_DELETE', n))
        tw = lambda k: m.role(f'tower {k}').name
        if which.startswith('height'):
            w, e = (m.role(f'cannon {keep[0]}').name, m.role('cannon E').name)
            c = 'Test Vision'
            t.counters.append((c, '看见'))
            t.scripts.append(Script('Test - start', [], start))
            for k, step in (('W', 1), ('E', 10)):
                t.scripts.append(Script(f'Test - see {k}', [('NAMED_DISCOVERED', p1, tw(k))],
                                        [('INCREMENT_COUNTER', step, c)]))
            for n, step in ((w, 100), (e, 1000)):
                t.scripts.append(Script(f'Test - sighted {step}', [('ENEMY_SIGHTED', n, 'Enemy', s1)],
                                        [('INCREMENT_COUNTER', step, c)]))
            t.expect = [('看见', 0, 'ever>=', 1101)]
            t.bench = [('bench_watch', dict(seconds=RUN[which], every=1, sheet=False, lines=1))]
            return t
        if which.startswith('resh') and which != 'reshroud':  # resh<N>: MAP_SHROUD_SET_RESHROUD_TIME N at the start
            start.append(('MAP_SHROUD_SET_RESHROUD_TIME', float(which[4:])))
        start.append(('SET_MILLISECOND_TIMER', 'Test Go', GO))
        t.scripts.append(Script('Test - start', [], start))
        t.waypoints['Test Reveal'] = TOWERS['W']
        reveal = {'perm': ('MAP_REVEAL_PERMANENTLY_AT_WAYPOINT', 'Test Reveal', 150.0, p1, 'Test Look'),
                  'all': ('MAP_REVEAL_ALL', p1), 'allundo': ('MAP_REVEAL_ALL_PERM', p1)}.get(
            'perm' if which == 'undo' else which, ('MAP_REVEAL_AT_WAYPOINT', 'Test Reveal', 150.0, p1))
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], [reveal, ('SET_FLAG', 'Test Going', 1)]))
        going = ('FLAG', 'Test Going', 1)
        t.counters.append(('Test Open', '揭开'))
        t.counters.append(('Test Frames', '帧数'))
        t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'Test Frames')], once=False))
        t.scripts.append(Script('Test - open', [going, ('NAMED_DISCOVERED', p1, tw('W'))],
                                [('INCREMENT_COUNTER', 1, 'Test Open')], once=False))
        if which in ('undo', 'allundo'):
            t.scripts.append(Script('Test - go undo', [('TIMER_EXPIRED', 'Test Go')],
                                    [('SET_MILLISECOND_TIMER', 'Test Undo', UNDO)]))
            t.scripts.append(Script('Test - undo', [('TIMER_EXPIRED', 'Test Undo')],
                                    [('MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT', 'Test Look') if which == 'undo' else
                                     ('MAP_REVEAL_ALL_UNDO_PERM', p1), ('SET_FLAG', 'Test Undone', 1)]))
            t.counters.append(('Test After', '撤后'))
            t.scripts.append(Script('Test - after', [('FLAG', 'Test Undone', 1), ('NAMED_DISCOVERED', p1, tw('W'))],
                                    [('INCREMENT_COUNTER', 1, 'Test After')], once=False))
        t.expect = [('帧数', 0, 'ever>=', 1, RUN[which])]
        t.bench = [('bench_watch', dict(seconds=RUN[which], every=1, sheet=False, lines=3 if which in ('undo', 'allundo') else 2))]
        return t


    MISSION = {'engine_vision': mission}
    CHECKS = {'engine_vision': {w: (lambda m, w=w: _test(m, w)) for w in RUN}}
    return dict(MISSION=MISSION, CHECKS=CHECKS)


def icewall():
    """Ice-wall engineer tests.

    block (A against B): both runners are sent north to their goals at GO_AT; lane A has a wall across it. A must go
      round: it never crosses the strip right behind the wall's middle (a latch: a pass through takes under a second,
      between frames) and still arrives; B drives straight through its own strip.
    freeze: the engineer is sent to raise a wall at the spot; it stands, then melts after its lifetime.
    smash: enemy Hammers next to a wall, ordered to attack it, shoot it down before it melts.
    """
    from parts import Script, Test, counted, square

    GO_AT = 10.0
    BUILT_LATER = 10.0                              # turns: a core's wall goes up as a building does (bench 2026-10-23:
                                                    # scaffolding at s11, whole at s14)
    FREEZE_AT = 10.0
    ATTACK_AT = 10.0
    STRIP = 50.0                                    # half-side of the strip area behind the wall's middle
    GOAL = 100.0
    CLEAR_FIRE = 8.0                                # clear: told to freeze then, from the away point (~220 off at 40)
    CLEAR_STANDS = 20.0                             # clear: the block whole by then (172 back at 40, 5.5 s building)
    CLEAR_SIZE = 10.0                               # clear: the engineer's own radius, round the block's square
    CLEAR_AWAY = 300.0                              # clear: sent this far south of the spot
    CLEAR_OUT = 12.0                                # clear: out within this


    def latched(t, counter, label, who, area):
        """A counter that turns 1 the first time `who` is inside `area` and stays 1."""
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - latch {counter}', [('NAMED_INSIDE_AREA', who, area)],
                                [('SET_COUNTER', counter, 1)]))


    def block(m):
        t = Test()
        go = GO_AT
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('SET_MILLISECOND_TIMER', 'Test - go timer', go)]))
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                                [('MOVE_NAMED_UNIT_TO', m.role(f'runner {k}').name, m.mark(f'goal {k}')) for k in 'AB']))
        for k in 'AB':
            who = m.role(f'runner {k}').name
            t.areas[f'Test Strip {k}'] = square(*m.point(f'behind {k}'), STRIP)
            t.areas[f'Test Goal {k}'] = square(*m.point(f'goal {k}'), GOAL)
            latched(t, f'Test {k} Crossed', f'{k} 穿过', who, f'Test Strip {k}')
            counted(f'Test {k} There', f'{k} 到达', t, named=who, area=f'Test Goal {k}')
        t.expect += [('A 穿过', 0, '==', 0), ('B 穿过', go, 'ever==', 1), ('A 到达', go, 'ever==', 1),
                     ('B 到达', go, 'ever==', 1)]
        t.bench = [('bench_watch', dict(seconds=40, every=3, sheet=False, lines=len(t.counters)))]
        return t


    def turns(m):
        """Which built wall holds a lane: each engineer builds at his spot at once, the runners go GO_AT + BUILT_LATER
        later; a runner that never crosses the strip behind its spot was held. Bench 2026-10-23: the square held, both
        bars (asked for 0 and for 90 degrees) let theirs by -- the core's angle does nothing (units/icewall.py seed)."""
        t = Test()
        go = GO_AT + BUILT_LATER
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('SET_MILLISECOND_TIMER', 'Test - go timer', go)] +
                                [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role(f'engineer {k}').name,
                                  m.ability(f'engineer {k}', 'freeze'), m.mark(f'spot {k}')) for k in 'ABC']))
        t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go timer')],
                                [('MOVE_NAMED_UNIT_TO', m.role(f'runner {k}').name, m.mark(f'goal {k}')) for k in 'ABC']))
        for k in 'ABC':
            t.areas[f'Test Strip {k}'] = square(*m.point(f'behind {k}'), STRIP)
            latched(t, f'Test {k} Crossed', f'{k} 穿过', m.role(f'runner {k}').name, f'Test Strip {k}')
        t.expect += [('C 穿过', 0, '==', 0), ('A 穿过', go, 'ever==', 1), ('B 穿过', go, 'ever==', 1)]
        t.bench = [('bench_watch', dict(seconds=go + 20, every=3, sheet=False, lines=len(t.counters)))]
        return t


    def clear(m):
        """The engineer is not shut in his own block (A4's: a core that leaves a 160 square): walked up from afar, he
        stops to build far enough off (units/icewall.py stand) that once it stands he is clear of its square, and sent
        off he walks away. Bench 2026-10-26: at stand 30 it came out round him and he could not walk out of it."""
        t = Test()
        who, k = m.role('engineer C').name, 'C'
        x, y = m.point(f'spot {k}')
        t.waypoints['Test Away'] = (x, y - CLEAR_AWAY)
        t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                  ('MOVE_NAMED_UNIT_TO', who, 'Test Away'),
                                                  ('SET_MILLISECOND_TIMER', 'Test - freeze timer', CLEAR_FIRE),
                                                  ('SET_MILLISECOND_TIMER', 'Test - away timer', CLEAR_STANDS + 4)]),
                      Script('Test - freeze', [('TIMER_EXPIRED', 'Test - freeze timer')],
                             [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', who, m.ability(f'engineer {k}', 'freeze'),
                               m.mark(f'spot {k}'))]),
                      Script('Test - away', [('TIMER_EXPIRED', 'Test - away timer')],
                             [('MOVE_NAMED_UNIT_TO', who, 'Test Away')])]
        core = next(u for u in m.units if u.id == m.param(f'engineer {k}', 'wall'))
        side = core.params['wall']                  # the block the core leaves
        half = next(u for u in m.units if u.id == side).params['length'] / 2
        t.areas['Test Block'] = square(x, y, half + CLEAR_SIZE)
        counted('Test In Block', '工兵在冰块里', t, named=who, area='Test Block')
        counted('Test Walls', '冰墙', t, template=side)
        t.expect += [('冰墙', 0, 'ever==', 1, CLEAR_STANDS),
                     ('工兵在冰块里', CLEAR_STANDS, '==', 0, CLEAR_STANDS + 4),               # not inside it at all
                     ('工兵在冰块里', CLEAR_STANDS + 4, 'ever==', 0, CLEAR_STANDS + 4 + CLEAR_OUT)]
        t.bench = [('bench_watch', dict(seconds=CLEAR_STANDS + 6 + CLEAR_OUT, every=2, sheet=False,
                                        lines=len(t.counters)))]
        return t


    def built(m):
        """Bisect control: the engineer's structure only has to appear (retail's bunker does not melt)."""
        t = Test()
        eng = m.role('engineer').name
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', eng,
                                                      m.ability('engineer', 'freeze'), m.mark('spot'))]))
        counted('Test Walls', '建筑', t, template=m.role('wall').template)
        t.expect += [('建筑', 0, 'ever==', 1)]
        t.bench = [('bench_watch', dict(seconds=30, every=3, sheet=False, lines=len(t.counters), until='c1==1'))]
        return t


    def freeze(m):
        t = Test()
        eng = m.role('engineer').name
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('SET_MILLISECOND_TIMER', 'Test - freeze timer', FREEZE_AT)]))
        t.scripts.append(Script('Test - freeze', [('TIMER_EXPIRED', 'Test - freeze timer')],
                                [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', eng, m.ability('engineer', 'freeze'),
                                  m.mark('spot'))]))
        counted('Test Walls', '冰墙', t, template=m.role('wall').template)
        life = m.param('wall', 'lifetime')
        t.expect += [('冰墙', 0, '==', 0, FREEZE_AT - 2), ('冰墙', FREEZE_AT, 'ever==', 1),
                     ('冰墙', FREEZE_AT + life + 12, 'ever==', 0)]      # he walks there and builds first
        t.bench = [('bench_watch', dict(seconds=FREEZE_AT + life + 22, every=3, sheet=False, lines=len(t.counters)))]
        return t


    def smash(m):
        t = Test()
        wall = m.role('wall').name
        t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                     ('SET_MILLISECOND_TIMER', 'Test - attack timer', ATTACK_AT)]))
        # left alone the Hammers never shot it (bench 2026-10-22: 100 % for 44 s): ordered, as a player would
        t.scripts.append(Script('Test - attack', [('TIMER_EXPIRED', 'Test - attack timer')],
                                [('NAMED_ATTACK_NAMED', h.name, wall) for h in m.roles('hammer')]))
        counted('Test Walls', '冰墙', t, template=m.role('wall').template)
        counted('Test Wall Health', '冰墙血量', t, health=wall)
        t.expect += [('冰墙血量', 0, '==', 100, ATTACK_AT - 2), ('冰墙血量', ATTACK_AT, 'ever<', 100),
                     ('冰墙', ATTACK_AT, 'ever==', 0)]
        t.bench = [('bench_watch', dict(seconds=70, every=3, sheet=False, lines=len(t.counters), until='c1==0'))]
        return t


    GHOST_BORN = 40.0                               # ghost: the Ghost King appears (the walls have stood since ~20)
    GHOST_ORDER = 60.0                              # ghost: from here the script orders it, by the wall nearest to it
    GHOST_AREA = 90.0                               # half-side of the area round a wall's spot
    REF = 'UNITRef - CNV Nearest Wall'


    def ghost_north(m):
        """ghost, but the Ghost King is made at the far north of the walls (150, 600), nearest to B: a nearest-first walk
        from there goes B, A, C, D (300, 640, 900, 985); from the map's origin it would go D, C, A, B."""
        return ghost(m, start=m.site('west field', 150, 600), first=2, order=(2, 1, 3, 4))


    def ghost(m, start=None, first=3, order=None):
        """Three questions of A4's last stretch (docs/design/cards/a4-layer3.md), one scene. Four walls built by four
        engineers (unnamed objects, as in play); a Ghost King appears by wall C at GHOST_BORN, left alone until GHOST_ORDER:
        1. does it smash a wall on its own (the wall's health at the nearest one, GHOST_BORN .. GHOST_ORDER)?
        2. a wall in an area is countable (the player's wall count in each wall's area);
        3. from GHOST_ORDER, each frame: if the name REF points at no live object and a wall stands, point REF at the
           nearest unnamed wall to the enemy's team, the Ghost King's (SET_REF_TO_NEREST_...) and order the Ghost King at REF (every frame).
           Read: which area REF is in, the health of REF -- the visits should go C, A, B, D (nearest first)."""
        t = Test()
        p1 = m.player('p1')
        far = m.role('ghost')                       # placed far off, to give the cast an object; killed, a fresh one is made
        gk = 'UNIT - CNV Ghost King 2'
        t.waypoints['Test Ghost Start'] = start or m.point('ghost')
        wall = m.role('wall').template
        t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1),
                                                  ('SET_MILLISECOND_TIMER', 'Test - born timer', GHOST_BORN),
                                                  ('SET_MILLISECOND_TIMER', 'Test - order timer', GHOST_ORDER)] +
                              [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role(f'engineer {k}').name,
                                m.ability(f'engineer {k}', 'freeze'), m.mark(f'spot {k}')) for k in 'ABCD']),
                      Script('Test - born', [('TIMER_EXPIRED', 'Test - born timer')],
                             [('NAMED_KILL', m.role(f'engineer {k}').name) for k in 'ABCD'] +
                             [('NAMED_KILL', far.name),
                              ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', gk, far.template, m.team('s1'), 'Test Ghost Start'),
                              ('SET_FLAG', 'Test Picking', 1)]),
                      Script('Test - order on', [('TIMER_EXPIRED', 'Test - order timer')], [('SET_FLAG', 'Test Ordering', 1)])]
        # a name nobody has had reads as neither destroyed nor standing (sim: destroyed unborn): a flag says whether REF
        # points at something yet; once what it pointed at is destroyed, the flag drops and the next one is picked
        t.scripts += [Script('Test - pick', [('FLAG', 'Test Picking', 1), ('FLAG', 'Test Picked', 0),
                                             ('COUNTER', 'Test Walls', 3, 1)],
                             [('SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER', wall, p1, m.team('s1'), REF),
                              ('SET_FLAG', 'Test Picked', 1)], once=False),
                      Script('Test - dropped', [('FLAG', 'Test Picked', 1), ('NAMED_DESTROYED', REF)],
                             [('SET_FLAG', 'Test Picked', 0)], once=False),
                      Script('Test - smash', [('FLAG', 'Test Ordering', 1), ('NAMED_NOT_DESTROYED', REF),
                                              ('NAMED_NOT_DESTROYED', gk)],
                             [('NAMED_ATTACK_NAMED', gk, REF)], once=False)]
        counted('Test Walls', '墙总数', t, template=wall)
        # only four counter lines fit (the fourth reads wrong in the digit strip: the least needed goes there): areas
        # holding a wall (0-4), where the pointed wall is (1-4 = A-D, 0 nowhere), the pointed wall's health
        t.counters += [('Test Areas', '有墙的区域数'), ('Test Where', '选中的墙是')]
        counted('Test Ref Health', '目标墙血量', t, health=REF)
        t.scripts += [Script('Test - areas zero', [], [('SET_COUNTER', 'Test Areas', 0)], once=False),
                      Script('Test - where zero', [], [('SET_COUNTER', 'Test Where', 0)], once=False)]
        for i, k in enumerate('ABCD', 1):
            t.areas[f'Test Spot {k}'] = square(*m.point(f'spot {k}'), GHOST_AREA)
            t.scripts += [Script(f'Test - area {k}', [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, wall,
                                                       f'Test Spot {k}')], [('INCREMENT_COUNTER', 1, 'Test Areas')],
                                 once=False),
                          Script(f'Test - where {k}', [('NAMED_INSIDE_AREA', REF, f'Test Spot {k}')],
                                 [('SET_COUNTER', 'Test Where', i)], once=False)]
        # bench 2026-10-31: made by wall C it left it (the nearest) at 100 % for the 20 s it stood beside it, then once ordered
        # smashed C, A, D, B (distance from where it was made: C 150, A 300, D 550, B 620) in ~16-24 s a wall
        t.expect += [('墙总数', 30, 'ever==', 4), ('有墙的区域数', 30, 'ever==', 4),
                     ('选中的墙是', GHOST_BORN + 2, '==', first, GHOST_ORDER - 2),
                     ('目标墙血量', GHOST_BORN + 2, '==', 100, GHOST_ORDER - 2),
                     ('选中的墙是', GHOST_ORDER, 'ever==', (order or (3, 1, 4, 2))[1], GHOST_ORDER + 60),
                     ('墙总数', GHOST_ORDER, 'ever==', 0)]
        t.bench = [('bench_watch', dict(seconds=GHOST_ORDER + 150, every=4, sheet=False, lines=len(t.counters)))]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'ice_block': {'block': block},
        'ice_turns': {'turns': turns, 'clear': clear},
        'ice_freeze': {'freeze': freeze},
        'ice_build': {'built': built},
        'ice_spawn': {'built': built},
        'ice_smash': {'smash': smash},
        'ice_ghost': {'ghost': ghost, 'north': ghost_north},
    }
    return dict(CHECKS=CHECKS)


def sight():
    """Low ground looking up (missions/sight_bench.py): latched, whether the player has discovered each pair's target
    (NAMED_DISCOVERED), the map left shrouded.

    look: the controls hold -- on one level, seen within the viewer's vision, not beyond it. The two 'up' pairs are the
    finding, read off the counters: 1, the viewer below sees up the cliff; 0, it does not.
    """
    from parts import Script, Test

    RUN = 20.0
    LABELS = {'up 120': '低看高120', 'up 180': '低看高180', 'flat 180': '平地180', 'flat 400': '平地400'}


    def look(m):
        t = Test()
        p1 = m.player('p1')
        for k in LABELS:
            c = f'Test Seen {k.title()}'
            t.counters.append((c, LABELS[k]))
            t.scripts += [Script(f'{c} zero', [], [('SET_COUNTER', c, 0)]),
                          Script(f'{c} one', [('NAMED_DISCOVERED', p1, m.role(f'target {k}').name)],
                                 [('SET_COUNTER', c, 1)])]
        t.expect += [('平地180', 1, 'ever==', 1), ('平地400', 1, '==', 0)]
        t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=len(t.counters)))]
        return t


    # the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
    CHECKS = {
        'sight': {'look': look},
    }
    return dict(CHECKS=CHECKS)


BENCHES = (
    crane, engine_area, engine_bridgebuilder, engine_bridgebuilder_b, engine_bridgefix,
    engine_gate_e, engine_see, engine_vision, icewall, sight,
)
