"""AI targets scenes."""
from functools import cache
from types import SimpleNamespace


def aibridge_bench():
    """BridgeHeuristic on one genuine 700-unit native bridge versus an ordinary plant.

    The SDK defines BridgeHeuristic but has no named consumer in SkirmishAI XML.
    Use the original heuristic in CNVStateTP and NamedObject on both map endpoints.
    No KindOf edits. Generated bridge parts are counted independently by the check.
    Prediction: Bridge selects a real bridge, never the ordinary neutral plant;
    the endpoint names test identity rather than assuming builder names survive.
    BENCH disproves the positive prediction: Bridge finds neither; only the real
    start builder remains named. Registration/qualification remain unresolved.
    See work/re/c_bridge_report.md.
    """
    from types import SimpleNamespace

    import platmap
    from maps import island
    mission = aitargetpick_bench()["shared"].mission
    state_xml = aitargetpick_bench()["shared"].state_xml
    from benches.ai.tactics.scenes import aiteams_bench
    HOST = aiteams_bench()["shared"].HOST
    host_unit = aiteams_bench()["shared"].host_unit
    from parts import square


    def bridge(real=True):
        m = mission('CampBrTarget' if real else 'CampBrControl',
                    [('BridgeHeuristic', None)], (0, 0, 0, 4))
        m.ext, m.ext_logs = True, ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
        m.map = SimpleNamespace(**vars(m.map))
        m.map.OBJECTS = m.map.OBJECTS[6:]  # no inherited bridges in either control
        m.map.PLAYERS = {**m.map.PLAYERS, **island.NEUTRAL}
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
        origin = m.site('front')
        endpoints = platmap.bridge((2250, 4200), (2950, 4200))
        for i, (x, y, angle, flags) in enumerate(endpoints):
            m.put('HB_Bridge_02' if real else 'AlliedPowerPlant', 'front',
                  x-origin[0], y-origin[1], side='neutral', angle=angle,
                  flags=flags if real else 0, name=f'UNIT - Bridge {i}', role=f'bridge {i}')
        m.facts['native bridge'] = real
        m.areas['Bridge count'] = square(2600, 4200, 650)
        m.spawns.update('HB_Bridge_02_' + suffix for suffix in
                        ('End', 'End2', 'Center', 'Center2', 'GateHouse'))
        asset, xml, ref = m.assets[0]
        extra = []
        for i in range(2):
            hid, sid = f'CNVBridgeNamed{i}', f'CNVBridgeNamedState{i}'
            extra += [f'<AITargetingHeuristic id="{hid}" HeuristicType="NamedObject" '
                      f'Name="UNIT - Bridge {i}" RequireUniqueTarget="false"/>',
                      state_xml(sid, [(hid, None)], 1)]
            xml = xml.replace('    <StrategicState id="CNVStateTP" State="CNVStateTP"/>',
                              '    <StrategicState id="CNVStateTP" State="CNVStateTP"/>\n'
                              f'    <StrategicState id="{sid}" State="{sid}"/>')
        xml = xml.replace('<AIStrategicStateDefinition ', '\n'.join(extra) + '\n<AIStrategicStateDefinition ', 1)
        m.assets[0] = asset, xml, ref
        return m


    MISSION = {'aibridgeon': bridge, 'aibridgeoff': lambda: bridge(False)}
    return dict(MISSION=MISSION)


def aibuildexclude_bench():
    """C: identical two-factory requests, with only ExcludeThing changed.

    CNVNewPK scores 1000; CNVDearPK scores 1 and costs 200. aibex/aibin
    include Dear explicitly (IncludeThing wins over ExcludeThing); aibxo/aibxi
    include infantry by category, and only aibxo excludes Dear.
    The observer is attached to an existing copied barracks (no yard swap).
    """
    from missions.aiskirm_bench import mission as base, NEW_BARRACKS
    from benches.ai.tactics.scenes import aiorders_bench
    MODULE = aiorders_bench()["shared"].MODULE


    def mission(exclude, category=False):
        name = ('CampBXO' if exclude else 'CampBXI') if category else ('CampBEx' if exclude else 'CampBIn')
        m = base(name, new=True, dear='cs', dear_cost=200)
        path, xml, asset = m.assets[-1]
        old = '<BuildEntry Build="CNVNewPK" Heuristic="FEWEST_UNIT"/>'
        assert xml.count(old) == 1
        xml = xml.replace(old, '<BuildEntry Build="CNVNewPK" Heuristic="CONSTANT" Score="1000"/>')
        if category:
            xml = xml.replace('Include="STRUCTURE UNPACKS_INTO_BUILDING"',
                              'Include="STRUCTURE UNPACKS_INTO_BUILDING INFANTRY"')
            xml = xml.replace('<IncludeThing>CNVDearPK</IncludeThing>', '')
        if exclude:
            xml = xml.replace('</CountAsStructureForBuildPurposesFilter>',
                              '<ExcludeThing>CNVDearPK</ExcludeThing></CountAsStructureForBuildPurposesFilter>')
        m.assets[-1] = path, xml, asset
        unit, = [u for u in m.units if u.id == NEW_BARRACKS]
        assert unit.xml.count('<Behaviors>') == 1
        unit.xml = unit.xml.replace('<Behaviors>', '<Behaviors>' + MODULE, 1)
        m.ext = True
        return m


    def rule(name, value):
        """B round 198: the retail filter (Rule ANY, Include STRUCTURE UNPACKS_INTO_BUILDING) without the IncludeThing,
        only Rule changed -- aibxall Rule ALL, aibxany Rule ANY. With aibxi (Include + INFANTRY, Rule ANY) they split
        Rule (aibxall / aibxany) and Include (aibxany / aibxi). The model (_filter_passes): ALL passes both PKs, ANY
        passes neither (infantry has no STRUCTURE / UNPACKS_INTO_BUILDING)."""
        m = mission(False, category=True)
        path, xml, asset = m.assets[-1]
        xml = xml.replace('Include="STRUCTURE UNPACKS_INTO_BUILDING INFANTRY"', 'Include="STRUCTURE UNPACKS_INTO_BUILDING"')
        old = '<CountAsStructureForBuildPurposesFilter Rule="ANY"'
        assert xml.count(old) == 1 and 'INFANTRY"' not in xml.split(old)[1].split('>')[0]
        m.assets[-1] = path, xml.replace(old, f'<CountAsStructureForBuildPurposesFilter Rule="{value}"'), asset
        m.name = name
        return m


    MISSION = {'aibex': lambda: mission(True), 'aibin': lambda: mission(False),
               'aibxo': lambda: mission(True, category=True), 'aibxi': lambda: mission(False, category=True),
               'aibxall': lambda: rule('CampBXAll', 'ALL'), 'aibxany': lambda: rule('CampBXAny', 'ANY')}
    return dict(MISSION=MISSION)


@cache
def aiclosestenemy_bench():
    """FriendlyStructure ClosestToEnemy: four retail land heuristics, independent teams.

    Prediction before bench: turret / turret / plant / plant, four members
    per lane by s55. Fixed enemy structures are closest to the turret, then the plant;
    the yard and logging plant are further away. Native forbidden filters retained.
    Measured s16-80: 4/4/0/0, model 4/4/4/4; last two lanes remain gaps.
    Water host is not covered here. Evidence: work/re/c_closest_report.md.
    """
    setup = aistate_bench()["shared"]
    from benches.ai.tactics.scenes import aiteams_bench
    host_unit = aiteams_bench()["shared"].host_unit
    HOST = aiteams_bench()["shared"].HOST

    HEURISTICS = ('FriendlyLandStructureHeuristic', 'FriendlyNonRefineryLandStructureHeuristic',
                  'FriendlyLandNonDefenseStructureHeuristic', 'AITarget_A05_Defense')
    UNITS = (setup.INF, setup.TANK, 'SovietAntiInfantryInfantry', 'SovietAntiVehicleInfantry')


    def mission():
        m = setup.mission('CampClosest', gate='const')
        filename, xml, asset = m.assets[0]
        states = []
        for i, (heuristic, unit) in enumerate(zip(HEURISTICS, UNITS)):
            state = setup._state(f'CNVClosest{i}', '', unit, gate='const')
            state = state.replace('ClosestStructureHeuristic', heuristic)
            state = state.replace('Tactic="SimpleAttack"', 'Tactic="StaticDefense" Distance="100"')
            states.append(state)
        start, end = xml.index('  <AIStrategicStateDefinition '), xml.index('  <AIPersonalityDefinition ')
        xml = xml[:start] + '\n'.join(states) + '\n' + xml[end:]
        xml = xml.replace('    <StrategicState id="CNVStateInf" State="CNVStateInf"/>\n'
                          '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>',
                          '\n'.join(f'    <StrategicState id="CNVClosest{i}" State="CNVClosest{i}"/>' for i in range(4)))
        m.assets[0] = filename, xml, asset
        for i, unit in enumerate(UNITS[2:]):
            for k in range(4):
                m.put(unit, 'east base', 50 + 100*i, -150 + 70*k, side='s1',
                      name=f'UNIT - Closest Extra {i} {k}', role=f'closest extra {i} {k}')
        m.put('AlliedPowerPlant', 'carrier home', 300, 600, side='s1', name='UNIT - Closest Refinery', role='closest plant')
        m.put('AlliedBaseDefense', 'carrier home', 0, 0, side='s1', name='UNIT - Closest Turret', role='closest turret')
        m.put('AlliedPowerPlant', 'carrier home', 800, -400, name='UNIT - Closest Enemy', role='closest enemy')
        yard = m.find(m.role('player yard').name)
        yard.x, yard.y = m.site('carrier home', 800, -700)
        m.ext, m.ext_logs = True, ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
        m.cnv_units = UNITS
        m.spawns.update(UNITS)
        for i, role in enumerate(('closest turret', 'closest turret', 'closest plant', 'closest plant')):
            m.cast[f'closest goal {i}'] = m.role(role)
        # Fixed unarmed enemy anchors; refinery exclusion is not exercised here.
        return m


    MISSION = {'aiclosest': mission}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


def aiconyard_bench():
    """C conyard entrance diagnostic: only the minimum distance differs (0/300).

    Uses the existing Japan unpack host. Eligibility must be measured before any
    distance claim. INFERRED prediction: if a core becomes eligible, 300 excludes
    points close to the real yard exit until the original 15s exemption applies.
    An unchanged core is a recruitment gate, not proof of the distance rule.
    """
    from benches.ai.production.scenes import aiplacement_bench
    placement_mission = aiplacement_bench()["shared"].mission


    def mission(minimum):
        m = placement_mission(200, japan=True)
        m.name = 'CampYard' + str(minimum)
        filename, xml, asset = m.assets[0]
        xml = xml.replace('MinDistanceFromConyardEntrance="0"',
                          f'MinDistanceFromConyardEntrance="{minimum}"')
        m.assets[0] = filename, xml, asset
        m.facts['conyard entrance minimum'] = minimum
        m.ext_logs = ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
        return m


    MISSION = {'aicyard0': lambda: mission(0), 'aicyard300': lambda: mission(300)}
    return dict(MISSION=MISSION)


def aicrate_bench():
    """Crate selection: retail HealCrate versus an ordinary neutral oil derrick.

    Retail consumer: AIStateLibrary CratePickup -> CrateHeuristic (VitalKindOf
    CRATE). Constant activation isolates selection from the retail interval gate;
    this does not measure pickup, healing, ownership changes or crate lifetime.
    Predict Crate selects only HealCrate; the independent NamedObject slot selects
    the placed object in both builds. See work/re/c_crate_report.md.
    """
    mission = aitargetpick_bench()["shared"].mission
    state_xml = aitargetpick_bench()["shared"].state_xml
    from benches.ai.tactics.scenes import aiteams_bench
    HOST = aiteams_bench()["shared"].HOST
    host_unit = aiteams_bench()["shared"].host_unit


    def crate(real=True):
        m = mission('CampCrateOn' if real else 'CampCrateOff',
                    [('CrateHeuristic', None)], (0, 0, 0, 4))
        m.ext, m.ext_logs = True, ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
        m.put('HealCrate' if real else 'OilDerrick', 'east gate', -250, 0,
              side='neutral', name='UNIT - Crate Control', role='crate control')
        asset, xml, ref = m.assets[0]
        extra = ('<AITargetingHeuristic id="CNVCrateNamed" HeuristicType="NamedObject" '
                 'Name="UNIT - Crate Control" RequireUniqueTarget="false"/>\n'
                 + state_xml('CNVCrateNamedState', [('CNVCrateNamed', None)], 1))
        xml = xml.replace('<AIStrategicStateDefinition ', extra + '\n<AIStrategicStateDefinition ', 1)
        xml = xml.replace('    <StrategicState id="CNVStateTP" State="CNVStateTP"/>',
                          '    <StrategicState id="CNVStateTP" State="CNVStateTP"/>\n'
                          '    <StrategicState id="CNVCrateNamedState" State="CNVCrateNamedState"/>')
        m.assets[0] = asset, xml, ref
        return m


    MISSION = {'aicrateon': crate, 'aicrateoff': lambda: crate(False)}
    return dict(MISSION=MISSION)


def aienemyfilter_bench():
    """EnemyNearby EnemyFilter.Include contrast; see work/re/c_enemyfilter_report.md.

    Reuse the measured near-miner host; only Include changes in the primary pair.
    SAME_PLAYER is a relationship control without an own harvester.
    aiefall / aiefnone: the aiefeng filter (Include ENGINEER) with Rule ALL / NONE -- does the Rule reach EnemyNearby?
    """
    from benches.ai.production.scenes import aipoweradv_bench
    mission = aipoweradv_bench()["shared"].mission


    def filtered(name, include, relationship, expected, rule='ANY'):
        gate = ('<EnemyNearbyHeuristic Distance="700.0" EnemyNearby="true">'
                f'<EnemyFilter Relationship="{relationship}" Rule="{rule}" Include="{include}"/>'
                '</EnemyNearbyHeuristic>')
        return mission(name, 4, 0, miner='ai base', gate=gate, expect=expected)


    MISSION = {
        'aiefharv': lambda: filtered('CampEFHarv', 'HARVESTER', 'ENEMIES', 1),
        'aiefeng': lambda: filtered('CampEFEng', 'ENGINEER', 'ENEMIES', 0),
        'aiefself': lambda: filtered('CampEFSelf', 'HARVESTER', 'SAME_PLAYER', 0),
        'aiefall': lambda: filtered('CampEFAll', 'ENGINEER', 'ENEMIES', 1, rule='ALL'),
        'aiefnone': lambda: filtered('CampEFNone', 'ENGINEER', 'ENEMIES', 0, rule='NONE'),
    }
    return dict(MISSION=MISSION)


def aienemygarr_bench():
    """EnemyGarrison: genuinely occupied enemy house versus same-site enemy plant.

    Script entry precedes strategic selection; counters independently verify ENCLOSED
    and ownership. NamedObject is the identity control, not a substitute for selection.
    See work/re/c_enemygarr_report.md.
    """
    mission = aitargetpick_bench()["shared"].mission
    state_xml = aitargetpick_bench()["shared"].state_xml
    from benches.ai.tactics.scenes import aiteams_bench
    HOST = aiteams_bench()["shared"].HOST
    host_unit = aiteams_bench()["shared"].host_unit
    from parts import Script


    def enemy_garrison(real=True):
        m = mission('CampEGarrOn' if real else 'CampEGarrOff',
                    [('EnemyGarrisonHeuristic', None)], (0, 0, 0, 4))
        m.ext, m.ext_logs = True, ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
        m.put('AM_RowHouse01' if real else 'AlliedPowerPlant', 'east gate', -250, 0,
              side='neutral' if real else 'p1', name='UNIT - EGarr Control', role='garr control')
        m.put('SovietAntiInfantryInfantry', 'east gate', -250, -80,
              side='p1', name='UNIT - EGarr Occupant', role='garr occupant')
        m.facts['enemy garrison'] = real
        m.scripts.append(Script('EGarr occupy', [],
            [('UNIT_CHANGE_OBJECT_STATUS', m.role('garr occupant').name, 'NO_ATTACK', 1)]
            + ([('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY',
                 m.role('garr occupant').name, m.role('garr control').name)] if real else [])))
        asset, xml, ref = m.assets[0]
        extra = ('<AITargetingHeuristic id="CNVEGarrNamed" HeuristicType="NamedObject" '
                 'Name="UNIT - EGarr Control" RequireUniqueTarget="false"/>\n'
                 + state_xml('CNVEGarrNamedState', [('CNVEGarrNamed', None)], 1))
        xml = xml.replace('<AIStrategicStateDefinition ', extra + '\n<AIStrategicStateDefinition ', 1)
        xml = xml.replace('    <StrategicState id="CNVStateTP" State="CNVStateTP"/>',
                          '    <StrategicState id="CNVStateTP" State="CNVStateTP"/>\n'
                          '    <StrategicState id="CNVEGarrNamedState" State="CNVEGarrNamedState"/>')
        m.assets[0] = asset, xml, ref
        return m


    MISSION = {'aiegarron': enemy_garrison, 'aiegarroff': lambda: enemy_garrison(False)}
    return dict(MISSION=MISSION)


def aiforbid_bench():
    """ForbiddenObjectStatus contrasts; work/re/c_forbidmask_report.md.

    Script-set status bits, not real ability modifiers. The original two-bit mask
    is tested with each bit separately and both together. Real invulnerability,
    aircraft and submerged targets remain gaps.
    """
    mission = aitargetpick_bench()["shared"].mission
    from benches.ai.tactics.scenes import aiteams_bench
    HOST = aiteams_bench()["shared"].HOST
    host_unit = aiteams_bench()["shared"].host_unit
    from model import Script


    def forbid(name, filtered, flagged, mask=None, status_name='UNDER_IRON_CURTAIN'):
        expected = (0, 4, 0, 0) if filtered and flagged else (4, 0, 0, 0)
        m = mission(name, [('CNVForbid', None)], expected)
        m.ext, m.ext_logs = True, ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
        statuses = status_name.split()
        m.facts['status set'] = int(flagged) * sum(
            2 if s == 'UNATTACKABLE' else 1 for s in statuses)
        forbidden = mask if mask is not None else ('UNDER_IRON_CURTAIN' if filtered else '')
        if mask is not None:
            m.facts['read unattackable'] = 1
        heuristic = ('<AITargetingHeuristic id="CNVForbid" HeuristicType="EnemyStructure" '
                     'SortType="Distance" VitalKindOf="STRUCTURE" RequireUniqueTarget="true" '
                     f'ForbiddenObjectStatus="{forbidden}"/>')
        asset, xml, ref = m.assets[0]
        xml = xml.replace('<AIStrategicStateDefinition ', heuristic + '\n  <AIStrategicStateDefinition ', 1)
        m.assets[0] = asset, xml, ref
        m.scripts.append(Script('CNV forbid status', [], [
            ('UNIT_CHANGE_OBJECT_STATUS', m.role('plant').name, s, int(flagged))
            for s in statuses]))
        return m


    MISSION = {
        'aiforbidnone': lambda: forbid('CampForbidNone', False, True),
        'aiforbidset': lambda: forbid('CampForbidSet', True, True),
        'aiforbidclear': lambda: forbid('CampForbidClr', True, False),
        'aifmasknone': lambda: forbid('CampMaskNone', False, True, ''),
        'aifmaskiron': lambda: forbid('CampMaskIron', True, True, 'UNDER_IRON_CURTAIN'),
        'aifmaskboth': lambda: forbid('CampMaskBoth', True, True, 'UNATTACKABLE UNDER_IRON_CURTAIN'),
        'aifunanone': lambda: forbid('CampUnaNone', False, True, '', 'UNATTACKABLE'),
        'aifunasingle': lambda: forbid('CampUnaSingle', True, True, 'UNATTACKABLE', 'UNATTACKABLE'),
        'aifunaboth': lambda: forbid('CampUnaBoth', True, True, 'UNATTACKABLE UNDER_IRON_CURTAIN', 'UNATTACKABLE'),
        'aifdualnone': lambda: forbid('CampDualNone', False, True, '', 'UNATTACKABLE UNDER_IRON_CURTAIN'),
        'aifdualboth': lambda: forbid('CampDualBoth', True, True, 'UNATTACKABLE UNDER_IRON_CURTAIN', 'UNATTACKABLE UNDER_IRON_CURTAIN'),
    }
    return dict(MISSION=MISSION)


def aifrdistance_bench():
    """C FriendlyUnit Distance probe: three same-player MCVs, swapped near role.

    Prediction before measurement: StaticDefense's tactical target is the MCV
    nearest the AI base, independently of whether its Guardians move there.
    Other sort modes and unique-slot arbitration remain INFERRED.
    """
    original = aifriendly_bench()["shared"].mission
    from benches.ai.tactics.scenes import aiteams_bench
    host_unit = aiteams_bench()["shared"].host_unit


    def mission(swapped=False):
        m = original(True)
        m.name = 'CampFrSwap' if swapped else 'CampFrNear'
        # All candidates stay outside the original Guardian recruitment mask.
        for role, offset in [('friendly', (1400, 0) if swapped else (-650, 0)),
                             ('second', (-650, 0) if swapped else (1400, 0)),
                             ('third', (0, 1500))]:
            if role == 'friendly':
                o = m.find(m.role(role).name)
                x, y = m.site('east base')
                o.x, o.y = x + offset[0], y + offset[1]
            else:
                m.put('AlliedMCV', 'east base', *offset, side='s1',
                      name='UNIT - Friendly ' + role, role=role)
        m.units.append(host_unit())
        m.put('CNVTeamsHost', 'east base', 250, 400, side='s1', role='teams host')
        m.ext = True
        m.facts['friendly nearest'] = 'second' if swapped else 'friendly'
        return m


    MISSION = {'aifrnear': mission, 'aifrswap': lambda: mission(True)}
    return dict(MISSION=MISSION)


@cache
def aifriendly_bench():
    """E85 FriendlyUnit versus EnemyUnit, using retail's StaticDefense consumer.

    Only HeuristicType differs between the pair. SAME_PLAYER is explicit in both;
    the SDK documents Relationship as hooked up only for FriendlyUnit. Both MCVs
    must survive. Prediction at s40: four Guardians at the corresponding MCV.
    Evidence and scope: work/re/e_friendly_e85.md.
    """
    target_mission = aitargetpick_bench()["shared"].mission


    def mission(friendly):
        name = 'CampAIFriend' if friendly else 'CampAIEnemy'
        m = target_mission(name, [('CNVHVehicle', None)], (0, 0, 0, 0))
        filename, xml, asset = m.assets[0]
        xml = xml.replace('VitalKindOf="VEHICLE"', 'VitalKindOf="MCV" Relationship="SAME_PLAYER"')
        xml = xml.replace('Tactic="SimpleAttack"', 'Tactic="StaticDefense" Distance="100"')
        if friendly:
            xml = xml.replace('HeuristicType="EnemyUnit"', 'HeuristicType="FriendlyUnit"')
        m.assets[0] = (filename, xml, asset)
        m.put('AlliedMCV', 'carrier home', side='s1', name='UNIT - Friendly MCV', role='friendly')
        m.put('AlliedMCV', 'east gate', name='UNIT - Enemy MCV', role='enemy')
        m.facts.update({'expect friendly': 4 if friendly else 0, 'expect enemy': 0 if friendly else 4})
        return m


    MISSION = {'aifriend': lambda: mission(True), 'aienemy': lambda: mission(False)}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


def aihusk_bench():
    """Husk negative: an ordinary neutral oil derrick is not a land husk.

    The NamedObject control selects the exact same placed derrick. No synthetic
    HUSK flag or pretend wreck is supplied. Real wreck registration remains a gap.
    Prediction before running: LandHuskHeuristic finds nothing; named control finds
    the derrick. Team arrival is outside this selection-only probe.
    """
    mission = aitargetpick_bench()["shared"].mission
    from benches.ai.tactics.scenes import aiteams_bench
    HOST = aiteams_bench()["shared"].HOST
    host_unit = aiteams_bench()["shared"].host_unit


    def husk(named=False):
        heuristic = 'CNVHuskNamed' if named else 'LandHuskHeuristic'
        m = mission('CampHuskNamed' if named else 'CampHuskNone',
                    [(heuristic, None)], (0, 0, 0, 4))
        m.ext, m.ext_logs = True, ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
        m.put('OilDerrick', 'east gate', -250, 0, side='neutral',
              name='UNIT - Husk Oil Control', role='husk oil control')
        if named:
            asset, xml, ref = m.assets[0]
            xml = xml.replace('<AIStrategicStateDefinition ',
                '<AITargetingHeuristic id="CNVHuskNamed" HeuristicType="NamedObject" '
                'Name="UNIT - Husk Oil Control"/>\n<AIStrategicStateDefinition ', 1)
            m.assets[0] = asset, xml, ref
        return m


    MISSION = {'aihusknone': husk, 'aihusknamed': lambda: husk(True)}
    return dict(MISSION=MISSION)


@cache
def ailocation_bench():
    """Location is a Land/Water filter, not a distance reference point.

    Identical EnemyStructure/Distance heuristics select between two power plants:
    the nearer one on the east bank, the farther one in the river. Twinblades can
    reach and attack either. Only Location differs between the three builds.
    Prediction: Land and Water Land -> land; Water -> water. See work/re/e_location_e81.md.
    """
    import resources
    from maps import niagara
    tp = aitargetpick_bench()["shared"]
    from parts import Mission, Script

    HELI = 'SovietAntiGroundAircraft'


    def mission(location, suffix):
        pid = 'CNVLocation'
        xml = tp.personality_xml(pid, [('CNVHBarracks', None)], 1)
        xml = xml.replace('VitalKindOf="FS_BARRACKS"', f'VitalKindOf="FS_POWER" Location="{location}"')
        xml = xml.replace('AllowedLocomotorTypes="LAND AMPHIBIOUS"', 'AllowedLocomotorTypes="AIR"')
        m = Mission(name='CampAILoc' + suffix, map=resources.measured(niagara),
                    facts={'wake at': 10.0, 'expect land': int(location != 'Water'),
                           'expect water': int(location == 'Water')})
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
        m.assets.append((pid + '.xml', xml, f'AIPersonalityDefinition:{pid}'))
        m.cnv_units = (HELI,)
        m.spawns.add(HELI)
        m.put('AlliedConstructionYard', 'east base', side='s1', name='UNIT - Location Yard', role='ai yard')
        m.put('AlliedPowerPlant', 'east gate', name='UNIT - Location Land', role='land')
        # River centre, away from either bridge and Goat Island; no new map needed.
        m.put('AlliedPowerPlant', 'north bridge', 0, -400, name='UNIT - Location Water', role='water')
        for k in range(4):
            m.put(HELI, 'east base', -200, 160 + 70 * k, side='s1',
                  name=f'UNIT - Location Heli {k}', role=f'heli {k}')
        m.waypoint('ai base', 'CNV Location Base', 'east base')
        s1 = m.player('s1')
        m.scripts += [
            Script('Location start', [], [('PLAYER_SET_MONEY', s1, 0),
                                         ('SET_MILLISECOND_TIMER', 'Location Wake', 10.0)]),
            Script('Location wake', [('TIMER_EXPIRED', 'Location Wake')], [
                ('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, 'CNV Location Base'),
                ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20),
                ('SKIRMISH_AI_USE_REPAIRS', s1, 0), ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0),
                ('PLAYER_SET_MONEY', s1, 0)])]
        return m


    MISSION = {'ailocland': lambda: mission('Land', 'L'),
               'ailocwater': lambda: mission('Water', 'W'),
               'ailocboth': lambda: mission('Water Land', 'B')}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


def aimindist_bench():
    """TechBuilding minimum enemy distance: 0 / 2000, plus named host control.

    The neutral oil replaces the target-pick host's power plant. Tech variants
    only differ in MinDistanceFromEnemy. Candidate qualification and live distance
    remain gaps unless independently observed; see work/re/c_mindist_report.md.
    """
    import dataclasses
    import math
    import types

    mission = aitargetpick_bench()["shared"].mission


    def minimum(name, limit, named=False):
        expected = (4, 0, 0, 0) if limit == 0 or named else (0, 0, 0, 4)
        m = mission(name, [('CNVMinEnemy', None)], expected)
        target = m.find(m.role('plant').name)
        target.template, target.side = 'OilDerrick', 'neutral'
        m.cast['plant'] = dataclasses.replace(m.cast['plant'], template='OilDerrick', side='neutral')
        asset, xml, ref = m.assets[0]
        kind = 'NamedObject' if named else 'TechBuilding'
        heuristic = (f'<AITargetingHeuristic id="CNVMinEnemy" HeuristicType="{kind}" '
                     f'Name="{target.name}" VitalKindOf="SUPPLY_SOURCE" '
                     f'ForbiddenKindOf="" Location="Land" SearchRange="1200" '
                     f'MinDistanceFromEnemy="{limit}"/>')
        xml = xml.replace('<AIStrategicStateDefinition ', heuristic + '\n  <AIStrategicStateDefinition ', 1)
        m.assets[0] = asset, xml, ref
        return m


    def two_candidates(name, limit, clear=False, search=1200, enemy='AlliedPowerPlant'):
        """Only the minimum changes: near oil has an enemy plant 200 away.

        The farther oil is over 1000 from that stationary enemy. At zero the
        closest oil to the AI base is predicted; at the retail oil threshold 350
        the farther oil is predicted. Engine instead stays home at 350; see
        work/re/c_mindist_pair_report.md. Exact boundary and qualification are gaps.
        B 11-21 (work/re/b1121_mindist.md): not the scenery by the far oil (clear:
        still home); SearchRange 3000 takes the far oil -- at 1200 it is out of
        range from the engine's AI base point (not the yard, 1011 off) at f16.
        enemy: the p1 structure 200 from the near oil (a wall should not count).
        """
        m = minimum(name, limit)
        asset, xml, ref = m.assets[0]   # B 11-21 H7: the SearchRange the find measures from the AI base
        m.assets[0] = asset, xml.replace('SearchRange="1200"', f'SearchRange="{search}"'), ref
        for role, template, side in (('barracks', 'OilDerrick', 'neutral'),
                                     ('tank', enemy, 'p1')):
            obj = m.find(m.role(role).name)
            obj.template, obj.side = template, side
            m.cast[role] = dataclasses.replace(m.cast[role], template=template, side=side)
        enemy = m.find(m.role('tank').name)
        near = m.find(m.role('plant').name)
        enemy.x, enemy.y = near.x, near.y + 200
        m.ext, m.ext_logs = True, ('target',)  # B 11-21: tgt: lines give each oil's verdict per find
        m.facts['minimum enemy distance'] = limit
        near_ok = limit == 0 or 'Wall' in enemy.template     # the enemy-distance find skips walls (b1121_mindist.md)
        m.facts['expect near oil'] = 4 if near_ok else 0
        m.facts['expect far oil'] = 0 if near_ok else 4
        if clear:   # B 11-21: the map's civilian scenery (fences, houses, trees) within 600 of the far oil removed
            far = m.find(m.role('barracks').name)
            layout = types.ModuleType(m.map.__name__)
            layout.__dict__.update(vars(m.map))
            layout.SCENERY = [o for o in m.map.SCENERY if math.dist((o.x, o.y), (far.x, far.y)) >= 600]
            m.map = layout
        return m


    def tech_kind(name, tech=True):
        """Same neutral structure/site: oil qualifies, ordinary plant does not.

        The retail ClosestTechBuildingHeuristic host has no VitalKindOf filter.
        Enemy distance is disabled to isolate the registered tech-building set;
        this does not reopen the minimum-distance or fallback probes.
        Native negative control selects the inherited far oil instead of staying
        home; preserve the original prediction. See work/re/c_techkind_report.md.
        """
        from benches.ai.tactics.scenes import aiteams_bench
        host_unit = aiteams_bench()["shared"].host_unit
        HOST = aiteams_bench()["shared"].HOST
        m = minimum(name, 0)
        asset, xml, ref = m.assets[0]
        xml = xml.replace('CNVMinEnemy', 'ClosestTechBuildingHeuristic')
        xml = xml.replace('VitalKindOf="SUPPLY_SOURCE"', 'VitalKindOf=""')
        m.assets[0] = asset, xml, ref
        if not tech:
            obj = m.find(m.role('plant').name)
            obj.template = 'AlliedPowerPlant'
            m.cast['plant'] = dataclasses.replace(m.cast['plant'], template=obj.template)
            m.facts.update({'expect plant': 0, 'expect home': 4})
        m.ext, m.ext_logs = True, ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
        return m


    MISSION = {
        'aimind0': lambda: minimum('CampMinZero', 0),
        'aimindhi': lambda: minimum('CampMinHigh', 2000),
        'aimindctl': lambda: minimum('CampMinCtl', 2000, named=True),
        'aimindpair0': lambda: two_candidates('CampMinPair0', 0),
        'aimindpair350': lambda: two_candidates('CampMinPair350', 350),
        'aimindpairclr': lambda: two_candidates('CampMinPairClr', 350, clear=True),
        'aimindpairfar': lambda: two_candidates('CampMinPairFar', 350, search=3000),
        'aimindpairwal': lambda: two_candidates('CampMinPairWal', 350, search=3000, enemy='AlliedWallSegmentPiece'),
        'aitechkind': lambda: tech_kind('CampTechKind'),
        'aitechnon': lambda: tech_kind('CampTechNon', False),
    }
    return dict(MISSION=MISSION)


def aiminvalue_bench():
    """Retail MinEnemyValue 1000/2500: one 1000 miner versus 2400/3800.

    Four independent team counters: 1000/one, 2500/one, 2500/two,
    2500/summed inverted. Corrected data prediction: low 0/4/4/0,
    high 0/4/0/4. Initial wrong cost prediction retained in the private report.
    Retail dependency evidence: work/re/c_minvalue_retail.json.
    """
    setup = aistate_bench()["shared"]


    def mission(high=False):
        m = setup.mission('CampAIMinHi' if high else 'CampAIMinValue', near=True)
        m.draw = 0.1    # the AI's protocol draw (simtech.Book): bench aiminvaluet bought AirPower (0.1 on it)
        units = (setup.INF, setup.TANK, 'SovietAntiInfantryInfantry', 'SovietAntiVehicleInfantry')
        cases = ((1000, False, True), (2500, False, True),
                 (2500, True, True), (2500, True, False))
        filename, xml, asset = m.assets[0]
        states = []
        for i, (unit, (minimum, both, nearby)) in enumerate(zip(units, cases)):
            objects = ('AlliedMiner', 'SovietMiner') if both else ('AlliedMiner',)
            gate = (f'<EnemyNearbyHeuristic Distance="700" MinEnemyValue="{minimum}" '
                    f'EnemyNearby="{str(nearby).lower()}"><EnemyFilter Relationship="ENEMIES" Rule="ANY">'
                    + ''.join(f'<IncludeThing>{obj}</IncludeThing>' for obj in objects)
                    + '</EnemyFilter></EnemyNearbyHeuristic>')
            state = setup._state(f'CNVMinValue{i}', '', unit, gate='const')
            states.append(state.replace('<ConstantHeuristic/>', gate)
                          .replace('ClosestStructureHeuristic', 'CNVMinValueTarget'))
        start, end = xml.index('  <AIStrategicStateDefinition '), xml.index('  <AIPersonalityDefinition ')
        target = ('  <AITargetingHeuristic id="CNVMinValueTarget" HeuristicType="EnemyStructure" '
                  'SortType="Distance" VitalKindOf="FS_POWER" RequireUniqueTarget="false"/>\n')
        xml = xml[:start] + target + '\n'.join(states) + '\n' + xml[end:]
        xml = xml.replace('    <StrategicState id="CNVStateInf" State="CNVStateInf"/>\n'
                          '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>',
                          '\n'.join(f'    <StrategicState id="CNVMinValue{i}" State="CNVMinValue{i}"/>'
                                    for i in range(4)))
        m.assets[0] = filename, xml, asset
        for i, unit in enumerate(units[2:]):
            for k in range(4):
                m.put(unit, 'east base', -100 + 70*i, -150 + 70*k, side='s1',
                      name=f'UNIT - MinValue Team {i} {k}', role=f'min value team {i} {k}')
        for i, unit in enumerate(('AlliedMiner', 'SovietMiner')):
            m.put(unit, 'east base', 350, 80*i, name=f'UNIT - MinValue Miner {i}', role=f'value miner {i}')
        if high:
            m.put('SovietMiner', 'east base', 350, 160,
                  name='UNIT - MinValue Miner 2', role='value miner 2')
        m.cnv_units = units
        m.spawns.update((*units, 'AlliedMiner', 'SovietMiner'))
        m.facts['min value cases'] = cases
        m.facts['min value home'] = (0, 4, 0, 4) if high else (0, 4, 4, 0)
        m.facts['min value miners'] = 3 if high else 2
        return m


    def observed():
        """B 11-23: aiminvaluehi + the teams host -- which protocol does the AI buy (cmd 24e)?"""
        from benches.ai.production.scenes import aiopath_bench
        host = aiopath_bench()["shared"].observed
        return host(mission(True))


    MISSION = {'aiminvalue': mission, 'aiminvaluehi': lambda: mission(True), 'aiminvaluet': observed}
    return dict(MISSION=MISSION)


@cache
def ainamed_bench():
    """Engine probe: AI targets named in the data -- HeuristicType NamedObject / Waypoint (engine line B, layer 4;
    read back by benches/ai/targets/checks.py#engine_ainamed; RA3-EngineModel ra3model/ai/targets.py).

    The retail campaign drives its AI almost wholly through these: AITargetHeuristicLibrary.xml has 145 NamedObject
    heuristics (143 the campaign's AITarget_*) and 94 Waypoint (92 campaign), each only `Name` (an object's script name /
    a waypoint's name), sometimes Relationship, Location, RequireUniqueTarget.

    The map, AI and structures are aitarget_bench's (near power plant at the east gate with two turrets, far plant south
    of the AI base, the player's yard on the west bank); the one always-on state sends 2-4 Peacekeepers by SimpleAttack
    (EndBehavior RAMPAGE) to the probe's own heuristic, added to the personality's asset file:
      ainmfar   NamedObject Name="UNIT - CNV AI Far Plant": the far plant, though the nearest (the control aitargetnear,
                SimpleAttack + ClosestStructureHeuristic) is the near one
      ainmwp    Waypoint Name="CNV AI WP Target" at 'route 2' (north of the AI base, nothing there): the team walks there
      ainmrel   NamedObject Name="UNIT - CNV AI Far Plant" Relationship="NEUTRAL": the far plant is the player's (an enemy),
                so if Relationship filters, no target, no team leaves
      ainmnone  NamedObject Name="UNIT - CNV AI No Such Thing": a name nobody has -- no target, no team
    Facts: wake at.
    """
    at = aitarget_bench()["shared"]

    HEUR = 'CNVTgtNamed'
    WP = 'CNV AI WP Target'
    WP_SITE = 'route 2'
    FAR_NAME = 'UNIT - CNV AI Far Plant'


    def heuristic_xml(kind, name, extra=''):
        return f'  <AITargetingHeuristic id="{HEUR}" HeuristicType="{kind}" Name="{name}"{extra}/>'


    def mission(mod, kind, name, extra=''):
        m = at.mission(mod, HEUR, 'SimpleAttack')
        m.cnv_heuristic = (kind, name, extra)
        (fname, xml, asset), = m.assets
        head = '  <AIStrategicStateDefinition'
        assert head in xml
        m.assets = [(fname, xml.replace(head, heuristic_xml(kind, name, extra) + '\n' + head, 1), asset)]
        m.waypoint('wp target', WP, WP_SITE)
        return m


    MISSION = {
        'ainmfar': lambda: mission('CampAINmFar', 'NamedObject', FAR_NAME),
        'ainmwp': lambda: mission('CampAINmWp', 'Waypoint', WP),
        'ainmrel': lambda: mission('CampAINmRel', 'NamedObject', FAR_NAME, ' Relationship="NEUTRAL"'),
        'ainmnone': lambda: mission('CampAINmNone', 'NamedObject', 'UNIT - CNV AI No Such Thing'),
    }
    return dict(MISSION=MISSION, shared=SimpleNamespace(FAR_NAME=FAR_NAME, WP=WP, mission=mission))


@cache
def aipoint_bench():
    """Point water search with distinct assets: range 1500 versus range 1.

    D166 established that the old same-id override still loaded retail range 1500.
    These new IDs test the actual radii. Predict water found at 1500, none at 1;
    replay the native random candidates, without inventing a random seed/terrain.
    See work/re/c_point_resume_report.md.
    """
    mission = aitargetpick_bench()["shared"].mission
    from benches.ai.tactics.scenes import aiteams_bench
    HOST = aiteams_bench()["shared"].HOST
    host_unit = aiteams_bench()["shared"].host_unit


    def point(name, radius):
        hid = 'CNVPointTiny' if radius == 1 else 'CNVPointWater'
        m = mission(name, [(hid, None)], (0, 0, 0, 4))
        m.ext, m.ext_logs = True, ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
        m.facts['point range'] = radius
        asset, xml, ref = m.assets[0]
        heuristic = (
            f'<AITargetingHeuristic id="{hid}" HeuristicType="Point" '
            f'Location="Water" SearchRange="{radius}" SortType="ThreatToWater">'
            '<BaseSelection PreferredBaseTypes="MAIN_BASE" PreferredNotBaseTypes="CAPTURED" '
            'SortOrder="PREFER_OLDEST"/></AITargetingHeuristic>')
        xml = xml.replace('<AIStrategicStateDefinition ', heuristic + '\n<AIStrategicStateDefinition ', 1)
        m.assets[0] = asset, xml, ref
        return m


    MISSION = {
        'aipointwater': lambda: point('CampPointWater', 1500),
        'aipointtiny': lambda: point('CampPointTiny', 1),
    }
    return dict(MISSION=MISSION, shared=SimpleNamespace(point=point))


def aiprio_bench():
    """Engine probe: SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY -- one enemy player's priority (retail: 343 uses, mostly at an
    AI's start, one line per enemy, e.g. a01 Soviet_1 30 / Soviet_2 20 / Soviet_3 10 / Soviet_4 5). Read back by
    checks/engine_aiprio.py; engine line A; model: RA3-EngineModel ra3model/ai/player.py set_enemy_priority.

    aitarget_bench's map and AI (ClosestStructureHeuristic + SimpleAttack: the team goes for the enemy structure nearest
    its base), with a second enemy: the near plant and its two turrets are Soviet_4's, made an enemy of Soviet_1 both ways
    at the start (Soviet_4 has no script library, its AI asleep); the far plant and the yard stay the player's.
      aipriodef  the wake's SET_ALL_ENEMY_PLAYERS_PRIORITIES 20 only (the control). Bench 11-10: the far plant first (s25),
                 the near one only by RAMPAGE (s55): Soviet_4, made an enemy by script, is not in the table SET_ALL fills
      aiprio1    no SET_ALL; Soviet_4 30, Player_1 10: the script's put does not ask the enemy list (read) -> tiers by
                 score, the top one alone (HighestPriorityEnemyPlayersOnly) -> s4's near plant
      aiprio0    SET_ALL 20, then Player_1 0: 0 takes the player out -> Soviet_4 alone (bench 11-10: the near plant)
      aipriorm   no SET_ALL; Soviet_4 0 alone: is there a table for the script to change (the personality's, built
                 when the AI runs -> the far plant) or none yet (-> nobody leaves)? Bench 11-10: nobody left
    Facts: wake at.
    """
    import dataclasses

    at = aitarget_bench()["shared"]

    SET_ALL = 'SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES'
    SET_ONE = 'SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY'
    REL = (0, 0.0, 'Enemy')


    def mission(name, prio=(), keep_all=True):
        """aitargetnear with the near plant's group Soviet_4's; prio: (side, n) set one by one after the wake's switches."""
        m = at.mission(name, 'ClosestStructureHeuristic', 'SimpleAttack')
        s1, s4 = m.player('s1'), m.player('s4')
        for role in ('near plant', 'near turret 1', 'near turret 2'):
            m.cast[role] = dataclasses.replace(m.cast[role], side='s4')
            m.find(m.cast[role].name).side = 's4'
        start = next(s for s in m.scripts if s.name == 'CNV AI - Start')
        start.do = list(start.do) + [('PLAYER_RELATES_PLAYER', s1, s4, REL), ('PLAYER_RELATES_PLAYER', s4, s1, REL)]
        wake = next(s for s in m.scripts if s.name == 'CNV AI - Wake')
        do = [a for a in wake.do if keep_all or a[0] != SET_ALL]
        wake.do = do + [(SET_ONE, s1, m.player(side), n) for side, n in prio]
        return m


    MISSION = {
        'aipriodef': lambda: mission('CampAIPrioDef'),
        'aiprio1': lambda: mission('CampAIPrio1', (('s4', 30), ('p1', 10)), keep_all=False),
        'aiprio0': lambda: mission('CampAIPrio0', (('p1', 0),)),
        'aipriorm': lambda: mission('CampAIPrioRm', (('s4', 0),), keep_all=False),
    }
    return dict(MISSION=MISSION)


def aisearch_bench():
    """EnemySearchDistanceVisionMultiplier: aipas1 geometry, only the search multiplier differs.

    Four Peacekeepers follow a named far plant. The side plant is 250 west of their route,
    outside base vision 200. Both builds enable passive engagement and use identical units,
    scripts and micro settings. Prediction: multiplier 1.5 finds and attacks the side plant;
    0.25 (search radius 50) passes it and reaches the far plant before attacking the side one.
    This probes passive-target collection, not fog visibility or hostile-target acquisition.
    """
    from benches.ai.tactics.scenes import airetreat_bench
    ar = airetreat_bench()["shared"]


    def mission(name, multiplier):
        return ar.mission(name, side=True, EngagePassiveTargets='true',
                          EnemySearchDistanceVisionMultiplier=str(multiplier))


    MISSION = {
        'aisrchhi': lambda: mission('CampAISrchHi', 1.5),
        'aisrchlo': lambda: mission('CampAISrchLo', 0.25),
    }
    return dict(MISSION=MISSION)


def aishore_bench():
    """MaxDistanceToShore single-target contrast; evidence: work/re/c_shore_report.md.

    The power plant is on the east bank, clear of the water. Predict 2000 permits
    it, 1 rejects it; EnemyStructure is the host control. Exact shore distance and
    the engine's shoreline sampling remain unmeasured.
    """
    from benches.ai.production.scenes import aipoweradv_bench
    mission = aipoweradv_bench()["shared"].mission


    def shore(name, limit, kind='EnemyStructureCloseToShore'):
        m = mission(name, 4, 0, gate='const', expect=int(limit > 1 or kind == 'EnemyStructure'))
        target = m.find(m.role('player target').name)
        target.x, target.y = m.site('east gate', 100, 0)
        asset, xml, ref = m.assets[0]
        heuristic = (f'<AITargetingHeuristic id="CNVShore" HeuristicType="{kind}" '
                     f'SortType="Distance" VitalKindOf="FS_POWER" Location="Land" '
                     f'SearchRange="5000" MaxDistanceToShore="{limit}"/>')
        xml = xml.replace('<AIStrategicStateDefinition id="CNVStatePA"',
                          heuristic + '\n  <AIStrategicStateDefinition id="CNVStatePA"')
        xml = xml.replace('TargetHeuristic="ClosestStructureHeuristic"', 'TargetHeuristic="CNVShore"')
        m.assets[0] = asset, xml, ref
        return m


    MISSION = {
        'aishorehi': lambda: shore('CampShoreHi', 2000),
        'aishorelo': lambda: shore('CampShoreLo', 1),
        'aishorectl': lambda: shore('CampShoreCtl', 2000, 'EnemyStructure'),
    }
    return dict(MISSION=MISSION)


@cache
def aistate_bench():
    """Engine probe: the skirmish AI's strategic states switched by map flags (read back by benches/ai/targets/checks.py#engine_aistate).

    docs/design/skirmish-ai.md 五: does a script flag (ScriptedFlagHeuristic) turn an AI state on and off, and does each
    state send only the units its team asks for? The enemy (s1, Allied) runs a personality of this probe's own: the
    Allied co-op base with every inherited strategic state removed and two states of its own --
      CNVStateInf   on while flag 'CNV AI Infantry' is set: a SimpleAttack team of 2-4 Peacekeepers (AlliedAntiInfantryInfantry)
      CNVStateTank  on while flag 'CNV AI Tanks' is set: a SimpleAttack team of 2-4 Guardians (AlliedAntiVehicleVehicleTech1)
    both aimed at the closest enemy structure (the player's yard on the west bank). The AI has a yard, 4 of each unit
    and no money (it builds nothing). Woken at WAKE_AT the retail way (as benches/ai/production/scenes.py#aiopen_bench); INF_AT the infantry flag goes
    on, TANK_AT it goes off and the tank flag on.
    aistateoff / aistateoffhome (EndIfStateTurnsOff): the infantry flag also goes off at OFF_AT, while the team is on its
    way (out of the base ~5 s after the flag, ~400 short of the target at OFF_AT); EndBehavior RAMPAGE / RETURN_HOME_AND_DISBAND.
    aistateoff1 / aistateoffh: the same, off 1 s / 0.5 s after it went on -- while the team is still home.
    aihunt / aihunt2: instead of the two, one always-on state with a Targetless Hunt tactic and a team of exactly one
    Peacekeeper; MaxRunningCopies not written / 2. How soon does each next copy start, and how many run at once?

    Facts: wake at, infantry at, tanks at, infantry off at (OFF_AT, or None).
    """
    import resources
    from maps import niagara
    from parts import Mission, Script

    WAKE_AT, INF_AT, TANK_AT = 10.0, 20.0, 60.0
    OFF_AT = 28.0
    PID = 'CNVStateTest'
    INF, TANK = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech1'
    FLAG_INF, FLAG_TANK = 'CNV AI Infantry', 'CNV AI Tanks'
    PLAIN = ('CNVAIInfantry', 'CNVAITanks')     # aistateplain: letters only (is the space the trouble?)
    BASE = 'AlliedCoopBasePersonality'
    # its strategic states with the parents' (SDK BasePersonality, CoopBasePersonality, AlliedCoopBasePersonality);
    # removed so only the probe's two can recruit
    INHERITED = ('ScoutAircraft', 'EngineerIdle', 'JapanEggUnpacker', 'HarvesterController', 'BaseDefenseController',
                 'CommandAssault_Gather_Land', 'CommandAssault_Gather_Water', 'CommandAssault_Land', 'CommandAssault_Water',
                 'CommandAssault_FighterAircraft', 'CommandAssault_BomberAircraft', 'CommandHold_Land', 'CommandHold_Water',
                 'CommandHold_BomberAircraft', 'CommandHold_FighterAircraft', 'Command_StrikeTarget_Land',
                 'Command_StrikeTarget_Water', 'Command_StrikeTarget_BomberAircraft', 'CaptureLandHusks',
                 'AttachedBurstDroneRemoval', 'AlliedExpansion', 'AlliedNavalBase', 'AlliedCaptureTech',
                 'AlliedCaptureWaterHusks')


    def _state(sid, flag, unit, gate='flag', end='RAMPAGE', target='ClosestStructureHeuristic'):
        when = {'flag': f'<ScriptedFlagHeuristic FlagName="{flag}"/>', 'const': '<ConstantHeuristic/>'}.get(gate, gate)
        return (
            f"""  <AIStrategicStateDefinition id="{sid}" MaxTargets="1">\n"""
            f"""    <Heuristic>\n"""
            f"""      {when}\n"""
            f"""    </Heuristic>\n"""
            f"""    <TargetHeuristic TargetHeuristic="{target}"/>\n"""
            f"""    <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="{end}" EndIfStateTurnsOff="true">\n"""
            f"""      <TeamTemplate MinUnits="2" MaxUnits="4" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"\n"""
            f"""                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"\n"""
            f"""                    MicroManager="StandardMicroManager_MEDIUM">\n"""
            f"""        <ObjectFilter Rule="ANY">\n"""
            f"""          <IncludeThing>{unit}</IncludeThing>\n"""
            f"""        </ObjectFilter>\n"""
            f"""      </TeamTemplate>\n"""
            f"""    </Tactic>\n"""
            f"""  </AIStrategicStateDefinition>"""
        )


    def _hunt(copies):
        """round 10: one always-on state with only a Targetless Hunt tactic (as retail AIStateLibrary.xml Hunt), a team
        of exactly one Peacekeeper; MaxRunningCopies = copies (None: not written)."""
        cap = '' if copies is None else f' MaxRunningCopies="{copies}"'
        return (
            f"""  <AIStrategicStateDefinition id="CNVStateHunt"{cap}>\n"""
            f"""    <Heuristic>\n"""
            f"""      <ConstantHeuristic/>\n"""
            f"""    </Heuristic>\n"""
            f"""    <Tactic id="Hunt" Tactic="Hunt" Targetless="true">\n"""
            f"""      <TeamTemplate MinUnits="1" MaxUnits="1" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"\n"""
            f"""                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"\n"""
            f"""                    MicroManager="StandardMicroManager_MEDIUM">\n"""
            f"""        <ObjectFilter Rule="ANY">\n"""
            f"""          <IncludeThing>{INF}</IncludeThing>\n"""
            f"""        </ObjectFilter>\n"""
            f"""      </TeamTemplate>\n"""
            f"""    </Tactic>\n"""
            f"""  </AIStrategicStateDefinition>"""
        )


    def personality_xml(gate='flag', flags=(FLAG_INF, FLAG_TANK), end='RAMPAGE', hunt=False, copies=None, beacon=None):
        removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
        if hunt:
            states = [_hunt(copies)]
            used = ['    <StrategicState id="CNVStateHunt" State="CNVStateHunt"/>']
        else:
            beacons = {'exists': [dict(gate=f'<BeaconExistsHeuristic Exists="{on}" Type="Assault"/>')
                                  for on in ('true', 'false')],
                       'target': [dict(gate='const', target='BeaconAssaultHeuristic_Land'), dict(gate='const')]}
            inf, tank = beacons.get(beacon, [dict(gate=gate)] * 2)
            states = [_state('CNVStateInf', flags[0], INF, end=end, **inf),
                      _state('CNVStateTank', flags[1], TANK, end=end, **tank)]
            used = ['    <StrategicState id="CNVStateInf" State="CNVStateInf"/>',
                    '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>']
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xai="uri:ea.com:eala:asset:instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
            '  </Includes>',
            *states,
            f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{BASE}">',
            *removed,
            *used,
            '  </AIPersonalityDefinition>',
            '</AssetDeclaration>', ''])


    def mission(name='CampAIState', near=False, gate='flag', flags=(FLAG_INF, FLAG_TANK), scope=None, off_at=None,
                end='RAMPAGE', hunt=False, copies=None, far2=False, beacon=None):
        """near: the player also has a power plant 300 west of the east gate, ~750 from the AI's units (the yard on the
        west bank is ~2600 away; A round 67 read: ClosestStructureHeuristic measures no distance, SearchRange is only the
        tech heuristic's -- aistatefar tests it). gate 'const': both states
        always on (ConstantHeuristic) -- does a team go at all. scope: the scripts' flag names get this prefix
        ('/' = the empty scope, which ScriptedFlagHeuristic reads), the AI's FlagName stays the bare name.
        off_at: the infantry flag also goes off then (seconds); end: the tactics' EndBehavior.
        far2 (B round 19): the player also has a power plant on its own base (site base power, ~2400 from the AI): two
        structures, both far -- does the infantry state go when there is a second target for it?
        beacon (B 11-24): no player places a co-op command beacon here. 'exists': the infantry state on while an ally's
        Assault beacon exists (BeaconExistsHeuristic Exists=true), the tanks' while none does (Exists=false); 'target':
        both always on, the infantry aimed at retail BeaconAssaultHeuristic_Land (HeuristicType=Beacon) instead."""
        facts = {'wake at': WAKE_AT, 'infantry at': INF_AT, 'tanks at': TANK_AT, 'infantry off at': off_at,
                 'hunt copies': (copies or 0) if hunt else None}   # 0: not written
        m = Mission(name=name, map=resources.measured(niagara), facts={k: v for k, v in facts.items() if v is not None})
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
        m.assets.append((f'{PID}.xml', personality_xml(gate, flags, end, hunt, copies, beacon), f'AIPersonalityDefinition:{PID}'))
        if scope is not None:
            flags = tuple(scope + f for f in flags)
        m.cnv_flags = flags                     # the check counts with these names (as the scripts write them)
        m.cnv_units = (INF, TANK)               # and these templates
        if near:
            m.put('AlliedPowerPlant', 'east gate', -300.0, 0.0, name='UNIT - CNV AI Player Target', role='player target')
        if far2:
            m.put('AlliedPowerPlant', 'base power', name='UNIT - CNV AI Player Far Plant', role='player far plant')
        m.spawns |= {INF, TANK}
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        for k in range(4):
            m.put(INF, 'east base', -260.0, -90.0 + 60.0 * k, side='s1', angle=3.1416, name=f'UNIT - CNV AI Inf {k + 1}',
                  role=f'peacekeeper {k + 1}')
            m.put(TANK, 'east base', -200.0, 160.0 + 70.0 * k, side='s1', angle=3.1416, name=f'UNIT - CNV AI Tank {k + 1}',
                  role=f'guardian {k + 1}')
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT),
                                          ('SET_MILLISECOND_TIMER', 'CNV AI Inf', INF_AT),
                                          ('SET_MILLISECOND_TIMER', 'CNV AI Tank', TANK_AT)]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)]),
            Script('CNV AI - Infantry on', [('TIMER_EXPIRED', 'CNV AI Inf')], [('SET_FLAG', flags[0], 1)]),
            Script('CNV AI - Tanks on', [('TIMER_EXPIRED', 'CNV AI Tank')],
                   [('SET_FLAG', flags[0], 0), ('SET_FLAG', flags[1], 1)])]
        if off_at is not None:
            next(s for s in m.scripts if s.name == 'CNV AI - Start').do.append(
                ('SET_MILLISECOND_TIMER', 'CNV AI Inf Off', off_at))
            m.scripts.append(Script('CNV AI - Infantry off', [('TIMER_EXPIRED', 'CNV AI Inf Off')],
                                    [('SET_FLAG', flags[0], 0)]))
        return m


    MISSION = {'aistate': mission,
               'aistateplain': lambda: mission('CampAIPlain', near=True, flags=PLAIN),
               'aistatenear': lambda: mission('CampAINear', near=True),
               'aistateconst': lambda: mission('CampAIConst', near=True, gate='const'),
               # both states always on, only the player's yard ~2600 away: does distance stop a team (A round 67 read:
               # the enemy structure / unit heuristics measure no distance, only the tech one uses SearchRange)
               'aistatefar': lambda: mission('CampAIFar', gate='const'),
               # B round 19: aistatefar plus a second far structure -- one target per state? (the infantry went on
               # aistateconst, two structures, and stayed home on aistatefar, one)
               'aistatefar2': lambda: mission('CampAIFar2', gate='const', far2=True),
               'aistateslash': lambda: mission('CampAISlash', near=True, flags=PLAIN, scope='/'),
               'aistateoff': lambda: mission('CampAIOff', near=True, flags=PLAIN, scope='/', off_at=OFF_AT),
               'aistateoffhome': lambda: mission('CampAIHome', near=True, flags=PLAIN, scope='/', off_at=OFF_AT,
                                                 end='RETURN_HOME_AND_DISBAND'),
               # round 10: the flag off again while the team is still home (it leaves ~74 frames after the flag)
               'aistateoff1': lambda: mission('CampAIOff1', near=True, flags=PLAIN, scope='/', off_at=INF_AT + 1.0),
               'aistateoffh': lambda: mission('CampAIOffH', near=True, flags=PLAIN, scope='/', off_at=INF_AT + 0.5),
               # round 10: a Targetless always-on state, one Peacekeeper a team -- how often, how many at once
               'aihunt': lambda: mission('CampAIHunt', near=True, hunt=True),
               'aihunt2': lambda: mission('CampAIHunt2', near=True, hunt=True, copies=2),
               'aibeaconex': lambda: mission('CampAIBcnEx', near=True, beacon='exists'),
               'aibeacontg': lambda: mission('CampAIBcnTg', near=True, beacon='target')}
    return dict(MISSION=MISSION, shared=SimpleNamespace(
        BASE=BASE, FLAG_TANK=FLAG_TANK, INF=INF, INHERITED=INHERITED, TANK=TANK, _state=_state,
        mission=mission,))


@cache
def aitarget_bench():
    """Engine probe: which of the player's structures a skirmish AI attack team goes for first (read back by
    benches/ai/targets/checks.py#engine_aitarget; engine line A, layer 4 block 4, RA3-EngineModel ra3model/ai/targets.py).

    The enemy (s1, Allied) runs a personality of this probe's own: the Allied co-op base with every inherited strategic
    state removed (as benches/ai/targets/scenes.py#aistate_bench) and one state, always on (ConstantHeuristic), sending a team of 2-4 Peacekeepers.
    The player has three structures:
      near  a power plant at the east gate, ~710 from the AI's base centre, two Multigunner turrets 150 north and south
      far   a power plant south of the AI's base (the carrier's spot), ~1010 from the base centre, nothing near it
      yard  the player's yard on the west bank, ~2700 away, one Multigunner turret beside it (so it is not as safe as far)
    Builds:
      aitargetsafe  the retail main attack's pair: SafestToGroundStructureHeuristic + DefenseAvoidanceAttack
                    (1AlliedBalanced BalancedAttackGround_MEDIUM). The model (least threat within 400) says: far.
      aitargetnear  ClosestStructureHeuristic + SimpleAttack, the control. The model (nearest the base centre): near.
      aitargetidle5 / aitargetidle30  aitargetsafe with the team's MaxTeamIdleTime 5 s / 30 s (retail 15 s): the
                    DefenseAvoidanceAttack legs wait for the team to be ready or idle that long (l4_tactics.md).
      aitargetstill aitargetsafe with MaxTeamIdleTime and MaxUnitIdleTime both 600 s: does either idle time let the
                    legs go? (bench 2026-11-07: no, to the frame as 15 s)
      aitargetflank aitargetsafe with FlankAttack (the same class as DefenseAvoidanceAttack, a random side).
    Facts: wake at.
    """
    import resources
    from maps import niagara
    ab = aistate_bench()["shared"]
    from parts import Mission, Script

    WAKE_AT = 10.0
    PID = 'CNVTargetTest'
    INF = ab.INF
    TURRET = 'AlliedBaseDefense'


    def _state(heuristic, tactic, micro='StandardMicroManager_MEDIUM'):
        return (
            f"""  <AIStrategicStateDefinition id="CNVStateGo" MaxTargets="1">\n"""
            f"""    <Heuristic>\n"""
            f"""      <ConstantHeuristic/>\n"""
            f"""    </Heuristic>\n"""
            f"""    <TargetHeuristic TargetHeuristic="{heuristic}"/>\n"""
            f"""    <Tactic id="Attack" Tactic="{tactic}" EndBehavior="RAMPAGE">\n"""
            f"""      <TeamTemplate MinUnits="2" MaxUnits="4" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"\n"""
            f"""                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"\n"""
            f"""                    MicroManager="{micro}">\n"""
            f"""        <ObjectFilter Rule="ANY">\n"""
            f"""          <IncludeThing>{INF}</IncludeThing>\n"""
            f"""        </ObjectFilter>\n"""
            f"""      </TeamTemplate>\n"""
            f"""    </Tactic>\n"""
            f"""  </AIStrategicStateDefinition>"""
        )


    IDLE_ID = 'CNVMicroIdle'


    def _micro_xml(idle, unit_idle=10):
        # StandardMicroManager_MEDIUM with its chain (Standard, Base) flattened -- the type cannot be inherited from
        # (the build says: not BaseInheritableAsset) -- only MaxTeamIdleTime (and for aitargetstill MaxUnitIdleTime)
        return (
            f"""  <AIMicroManagerData id="{IDLE_ID}" UpdateTime="2.0s" MaxTeamIdleTime="{idle}s"\n"""
            f"""    MaxTeamIdleDistanceChange="50.0" MaxUnitIdleTime="{unit_idle}s" MaxUnitIdleDistanceChange="30.0"\n"""
            f"""    EnemySearchDistanceVisionMultiplier="1.5" MinTimeToKeepTempVisionRangeBonus="10s" SiegeWeaponBuffer="1.5"\n"""
            f"""    DodgeThreatsReactionTimeMin="6s" DodgeThreatsReactionTimeMax="14s" GatherTempVisionRangeBonus="1.5"\n"""
            f"""    RetreatTempVisionRangeBonus="1.5" MaxSecondaryDamageFraction="1.3" EngageHostileTargets="true"\n"""
            f"""    EngagePassiveTargets="true" EngageTacticalTarget="true" RetreatPowerAdvantage="0.2"\n"""
            f"""    RetreatMinDistanceFromBase="900.0" RetreatMinDistanceToFallback="500.0" AlphaStrikeTargetHealthPct="0.5"\n"""
            f"""    AlphaStrikeTargetTimeToKill="4.0" Crush="true" EnterGarrisons="true" EnterGarrisonableStructureDistance="150"\n"""
            f"""    EnterBaseDefensesWhenIdle="false" PullbackInjured="true" PullbackInjuredHealthPct="0.35" ReverseMove="true"\n"""
            f"""    DodgeThreats="true" UseSpecialPowers="true" TimeToKeepTargetMin="3s" TimeToKeepTargetMax="5s"\n"""
            f"""    RandomTargetScoreModifier="1.0" SpecialPowerDelayMinimum="2s" SpecialPowerDelayMaximum="8s">\n"""
            f"""    <SpecificSpecialPowerDelay PowerType="TOGGLE" TogglePowerSubType="TOGGLE_LOCKDOWN" MinimumDelay="20s" MaximumDelay="40s"/>\n"""
            f"""    <RetreatBaseCriteria PreferredNotBaseTypes="CAPTURED" SortOrder="PREFER_CLOSEST"/>\n"""
            f"""    <IgnoreTargets Rule="ANY" Include="TIME_BOMB"/>\n"""
            f"""  </AIMicroManagerData>"""
        )


    def personality_xml(heuristic, tactic, idle=None, unit_idle=10):
        removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in ab.INHERITED]
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xai="uri:ea.com:eala:asset:instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml" />',
            '  </Includes>',
            *([_micro_xml(idle, unit_idle)] if idle else []),
            _state(heuristic, tactic, IDLE_ID if idle else 'StandardMicroManager_MEDIUM'),
            f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{ab.BASE}">',
            *removed,
            '    <StrategicState id="CNVStateGo" State="CNVStateGo"/>',
            '  </AIPersonalityDefinition>',
            '</AssetDeclaration>', ''])


    def mission(name, heuristic, tactic, idle=None, unit_idle=10):
        m = Mission(name=name, map=resources.measured(niagara), facts={'wake at': WAKE_AT})
        m.cnv_heuristic = heuristic             # the check says the model's pick by it
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
        m.assets.append((f'{PID}.xml', personality_xml(heuristic, tactic, idle, unit_idle),
                         f'AIPersonalityDefinition:{PID}'))
        m.cnv_units = (INF,)
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        m.put(TURRET, 'base yard', 220.0, 0.0, name='UNIT - CNV AI Yard Turret', role='yard turret')
        m.put('AlliedPowerPlant', 'east gate', 0.0, 0.0, name='UNIT - CNV AI Near Plant', role='near plant')
        for k, dy in enumerate((-150.0, 150.0)):
            m.put(TURRET, 'east gate', 0.0, dy, name=f'UNIT - CNV AI Near Turret {k + 1}', role=f'near turret {k + 1}')
        m.put('AlliedPowerPlant', 'carrier home', 0.0, 0.0, name='UNIT - CNV AI Far Plant', role='far plant')
        m.spawns |= {INF}
        for k in range(4):
            m.put(INF, 'east base', -260.0, -90.0 + 60.0 * k, side='s1', angle=3.1416, name=f'UNIT - CNV AI Inf {k + 1}',
                  role=f'peacekeeper {k + 1}')
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]
        return m


    MISSION = {'aitargetsafe': lambda: mission('CampAISafe', 'SafestToGroundStructureHeuristic', 'DefenseAvoidanceAttack'),
               'aitargetnear': lambda: mission('CampAINearest', 'ClosestStructureHeuristic', 'SimpleAttack'),
               'aitargetidle5': lambda: mission('CampAIIdle5', 'SafestToGroundStructureHeuristic',
                                                'DefenseAvoidanceAttack', idle=5),
               'aitargetidle30': lambda: mission('CampAIIdle30', 'SafestToGroundStructureHeuristic',
                                                 'DefenseAvoidanceAttack', idle=30),
               'aitargetstill': lambda: mission('CampAIStill', 'SafestToGroundStructureHeuristic',
                                                'DefenseAvoidanceAttack', idle=600, unit_idle=600),
               'aitargetflank': lambda: mission('CampAIFlank', 'SafestToGroundStructureHeuristic', 'FlankAttack')}
    return dict(MISSION=MISSION, shared=SimpleNamespace(
        IDLE_ID=IDLE_ID, INF=INF, PID=PID, WAKE_AT=WAKE_AT, _micro_xml=_micro_xml, mission=mission,
        personality_xml=personality_xml,))


@cache
def aitargetpick_bench():
    """Engine probe: which target a strategic state's team picks -- AITargetingHeuristic VitalKindOf / ForbiddenKindOf /
    HeuristicType EnemyUnit, the state's TargetHeuristic Priority, and MaxTargets (read back by
    benches/ai/targets/checks.py#engine_aitargetpick; private ai/targets.py, simai through it).

    aiteamfilter_bench's set-up (Niagara, the enemy s1 Allied with a yard and no money, every inherited strategic state
    removed, woken at 10 s), one always-on state CNVStateTP (ConstantHeuristic): a SimpleAttack team, IncludeKindOf
    CAN_ATTACK, MinUnits 1, MaxUnits 4. s1 has 4 Guardians at home (8 in the MaxTargets variants). The player has three
    targets, all kept at full health by the check (so a team stays on its first pick):
      plant    AlliedPowerPlant (KindOf FS_POWER) at the east gate, ~710 west of the AI's base centre
      barracks AlliedBarracks (FS_BARRACKS) at the carrier's spot, ~1010 south
      tank     a player Guardian (VEHICLE, a unit) 700 north of the east gate, ~910 north-west
    Builds (the state's TargetHeuristic list):
      aitpnear  ClosestStructureHeuristic (control): plant
      aitpvk    CNVHBarracks (EnemyStructure, SortType Distance, VitalKindOf FS_BARRACKS): barracks
      aitpfk    CNVHNoPower (EnemyStructure, VitalKindOf STRUCTURE, ForbiddenKindOf FS_POWER): barracks
      aitpunit  CNVHVehicle (HeuristicType EnemyUnit, VitalKindOf VEHICLE, as retail's vehicle heuristics): tank
      aitpphi   CNVHBarracks Priority 20 + ClosestStructureHeuristic Priority 10: the higher first -> barracks
      aitpplo   CNVHBarracks Priority 5 + ClosestStructureHeuristic Priority 10: plant
      aitpmt1   ClosestStructureHeuristic, MaxTargets 1, 8 Guardians: one team of 4 at the plant, 4 at home
      aitpmt2   the same with MaxTargets 2: the model's reading -- a team per slot, the second slot's unique nearest is
                the barracks: 4 at the plant, 4 at the barracks
      aitpairn  + a player Kirov (HOLD_FIRE, airborne) at (-150, +650) from the AI's base: ~350 from the Guardians'
                centre the distance is taken from (the tank ~495; b1121_mindist); CNVHSurface
                (EnemyUnit, Distance, VitalKindOf empty, ForbiddenObjectStatus empty): the Kirov (bench 11-23: 3 under
                it s14-s16, then RAMPAGE to the nearest structure, the plant, 4 from s21)
      aitpairf  the same with retail ClosestSurfaceUnitHeuristic's ForbiddenObjectStatus="AIRBORNE_TARGET SUBMERGED":
                the tank (the Guardians cannot hit the Kirov either way: TeamTemplate RequireCanAttackTarget default false)
    Facts: wake at, ai tanks, expect plant / barracks / tank / home (the model's guess, Guardians there at the end).
    """
    import resources
    from maps import niagara
    BASE = aistate_bench()["shared"].BASE
    INHERITED = aistate_bench()["shared"].INHERITED
    from parts import Mission, Script

    WAKE_AT = 10.0
    PID = 'CNVTPick'
    TANK = 'AlliedAntiVehicleVehicleTech1'
    WALLS = ('NEUTRAL_TECH CIVILIAN_BUILDING WALK_ON_TOP_OF_WALL DEFENSIVE_WALL WALL_UPGRADE WALL_HUB WALL_SEGMENT '
             'WALL_PIECE WALL_GATE BASE_FOUNDATION')
    HEURISTICS = {
        'CNVHBarracks': dict(HeuristicType='EnemyStructure', SortType='Distance', VitalKindOf='FS_BARRACKS',
                             ForbiddenKindOf=WALLS, RequireUniqueTarget='true'),
        'CNVHNoPower': dict(HeuristicType='EnemyStructure', SortType='Distance', VitalKindOf='STRUCTURE',
                            ForbiddenKindOf='FS_POWER ' + WALLS, RequireUniqueTarget='true'),
        'CNVHVehicle': dict(HeuristicType='EnemyUnit', SortType='Distance', VitalKindOf='VEHICLE', ForbiddenKindOf='',
                            RequireUniqueTarget='true'),
        **{h: dict(HeuristicType='EnemyUnit', SortType='Distance', VitalKindOf='', ForbiddenObjectStatus=f,
                   RequireUniqueTarget='true') for h, f in (('CNVHSurface', ''), ('CNVHSurfaceF', 'AIRBORNE_TARGET SUBMERGED'))},
    }
    KIROV = 'SovietBomberAircraft'


    def state_xml(sid, targets, max_targets, priority='STANDARD', end='RAMPAGE', require=False):
        th = ['    <TargetHeuristic TargetHeuristic="{}"{}/>'.format(h, '' if p is None else f' Priority="{p}"')
              for h, p in targets]
        return '\n'.join([
            f'  <AIStrategicStateDefinition id="{sid}" MaxTargets="{max_targets}">',
            '    <Heuristic>',
            '      <ConstantHeuristic/>',
            '    </Heuristic>',
            *th,
            '''    <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="''' + end + (
                '" EndIfStateTurnsOff="true">\n'
                '      <TeamTemplate MinUnits="1" MaxUnits="4" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"\n'
                '                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="'
            ) + priority + (
                            '" AlwaysRecruit="false"\n'
                            '                    MicroManager="StandardMicroManager_MEDIUM"'
                        ) + (' RequireCanAttackTarget="true"' if require else '') + (
                            '/>\n'
                            '    </Tactic>\n'
                            '  </AIStrategicStateDefinition>'
                        )])


    def personality_xml(pid, targets, max_targets, priority='STANDARD', second=None, end='RAMPAGE', require=False):
        """second = (TargetHeuristic list, team Priority) of a second always-on state CNVStateTQ, or None."""
        removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
        every = list(targets) + (list(second[0]) if second else [])
        own = sorted({h for h, _ in every if h in HEURISTICS})
        heur = ['  <AITargetingHeuristic id="{}" {} />'.format(
            h, ' '.join(f'{k}="{v}"' for k, v in HEURISTICS[h].items())) for h in own]
        states = [state_xml('CNVStateTP', targets, max_targets, priority, end, require)]
        if second:
            states.append(state_xml('CNVStateTQ', second[0], max_targets, second[1]))
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xai="uri:ea.com:eala:asset:instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
            '  </Includes>',
            *heur,
            *states,
            f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
            *removed,
            '    <StrategicState id="CNVStateTP" State="CNVStateTP"/>',
            *(['    <StrategicState id="CNVStateTQ" State="CNVStateTQ"/>'] if second else []),
            '  </AIPersonalityDefinition>',
            '</AssetDeclaration>', ''])


    def mission(name, targets, expect, max_targets=1, tanks=4, priority='STANDARD', second=None, end='RAMPAGE',
                kill_at=None, kirov=None, require=False):
        """expect = (plant, barracks, tank, home): Guardians there at the end, the model's guess; kirov = the Guardians
        expected under a player Kirov south of the Guardians (None: no Kirov)."""
        pid = PID + name[-3:]
        plant, barracks, tank, home = expect
        m = Mission(name=name, map=resources.measured(niagara), facts={'wake at': WAKE_AT, 'ai tanks': tanks, 'expect plant': plant,
                                                   'expect barracks': barracks, 'expect tank': tank,
                                                   'expect home': home})
        if kill_at is not None:
            m.facts['kill plant at'] = kill_at
        if kirov is not None:
            m.facts['expect kirov'] = kirov
            m.spawns |= {KIROV}
            m.put(KIROV, 'east base', -150.0, 650.0, name='UNIT - CNV TP Kirov', role='kirov')
            m.scripts.append(Script('CNV TP - Kirov holds fire', [], [('UNIT_SET_STANCE', 'UNIT - CNV TP Kirov', 3)]))
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
        m.assets.append((f'{pid}.xml', personality_xml(pid, targets, max_targets, priority, second, end, require),
                         f'AIPersonalityDefinition:{pid}'))
        m.cnv_units = (TANK,)
        m.spawns |= {TANK}
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        m.put('AlliedPowerPlant', 'east gate', 0.0, 0.0, name='UNIT - CNV TP Plant', role='plant')
        m.put('AlliedBarracks', 'carrier home', 0.0, 0.0, name='UNIT - CNV TP Barracks', role='barracks')
        m.put(TANK, 'east gate', 0.0, 700.0, name='UNIT - CNV TP Tank', role='tank')
        for k in range(tanks):
            m.put(TANK, 'east base', -200.0 - 80.0 * (k // 4), 160.0 + 70.0 * (k % 4), side='s1', angle=3.1416,
                  name=f'UNIT - CNV AI Tank {k + 1}', role=f'ai guardian {k + 1}')
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]
        return m


    CLOSEST = 'ClosestStructureHeuristic'
    BARRACKS = [('CNVHBarracks', None)]
    MISSION = {
        'aitpnear': lambda: mission('CampAITPNear', [(CLOSEST, None)], (4, 0, 0, 0)),
        'aitpvk': lambda: mission('CampAITPVk', [('CNVHBarracks', None)], (0, 4, 0, 0)),
        'aitpfk': lambda: mission('CampAITPFk', [('CNVHNoPower', None)], (0, 4, 0, 0)),
        'aitpunit': lambda: mission('CampAITPUnit', [('CNVHVehicle', None)], (0, 0, 4, 0)),
        'aitpphi': lambda: mission('CampAITPPhi', [('CNVHBarracks', 20), (CLOSEST, 10)], (0, 4, 0, 0)),
        'aitpplo': lambda: mission('CampAITPPlo', [('CNVHBarracks', 5), (CLOSEST, 10)], (4, 0, 0, 0)),
        'aitpmt1': lambda: mission('CampAITPMt1', [(CLOSEST, None)], (4, 0, 0, 4), tanks=8),
        'aitpmt2': lambda: mission('CampAITPMt2', [(CLOSEST, None)], (4, 4, 0, 0), max_targets=2, tanks=8),
        'aitpairn': lambda: mission('CampAITPAirN', [('CNVHSurface', None)], (4, 0, 0, 0), kirov=4),
        'aitpairf': lambda: mission('CampAITPAirF', [('CNVHSurfaceF', None)], (0, 0, 4, 0), kirov=0),
        # TeamTemplate RequireCanAttackTarget="true" (work/re d61 2: the recruit gate takes a unit only if it can attack
        # the slot's target object, now or after moving): aitpairn's Kirov -> no Guardian is taken, 4 at home;
        # aitpunit's tank -> all 4 go as without it
        'aitpairr': lambda: mission('CampAITPAirR', [('CNVHSurface', None)], (0, 0, 0, 4), kirov=0, require=True),
        'aitpunr': lambda: mission('CampAITPUnR', [('CNVHVehicle', None)], (0, 0, 4, 0), require=True),
        # round 82: TeamTemplate.Priority -- two always-on states, P (CNVStateTP, the plant, a target from s13) and B
        # (CNVStateTQ, the barracks, from s19), both general-path teams of MaxUnits 4 over the same 4 Guardians.
        # The model guessed (4, 0, 0, 0) for all four (the plant's team first, no taking from another team); the bench
        # (round 82) sent all 4 to the barracks unless the plant's team is the higher (HIGH over STANDARD): expected now
        # as read.
        'aitpprs': lambda: mission('CampAITPPrS', [(CLOSEST, None)], (0, 4, 0, 0), second=(BARRACKS, 'STANDARD')),
        'aitpprh': lambda: mission('CampAITPPrH', [(CLOSEST, None)], (0, 4, 0, 0), second=(BARRACKS, 'HIGH')),
        'aitpprp': lambda: mission('CampAITPPrP', [(CLOSEST, None)], (4, 0, 0, 0), priority='HIGH',
                                   second=(BARRACKS, 'STANDARD')),
        'aitpprl': lambda: mission('CampAITPPrL', [(CLOSEST, None)], (0, 4, 0, 0), priority='LOW',
                                   second=(BARRACKS, 'STANDARD')),
        # round 84: Tactic EndBehavior -- ClosestStructure's team at the plant, the check kills the plant at s35 (the
        # barracks and the tank stay full). From the plant the tank is 700 off, the barracks 1055; from the AI's base the
        # barracks is the closest structure left (1010; the player's yard 2740). The model (private ai/tactics.py _end):
        # RAMPAGE = the nearest enemy of the team -> the tank; DISBAND = the team ends, the state's target re-picked ->
        # a new team to the barracks; RETURN_HOME_AND_DISBAND = home first, then the barracks; PICK_NEW_TARGET = the
        # barracks straight from the plant. expect = where they stand at the end.
        'aiendr': lambda: mission('CampAIEndR', [(CLOSEST, None)], (0, 0, 4, 0), kill_at=35.0),
        'aiendd': lambda: mission('CampAIEndD', [(CLOSEST, None)], (0, 4, 0, 0), end='DISBAND', kill_at=35.0),
        'aiendh': lambda: mission('CampAIEndH', [(CLOSEST, None)], (0, 4, 0, 0), end='RETURN_HOME_AND_DISBAND',
                                  kill_at=35.0),
        'aiendp': lambda: mission('CampAIEndP', [(CLOSEST, None)], (0, 4, 0, 0), end='PICK_NEW_TARGET', kill_at=35.0),
    }
    return dict(MISSION=MISSION, shared=SimpleNamespace(
        TANK=TANK, mission=mission, personality_xml=personality_xml, state_xml=state_xml,))


def aitoponly_bench():
    """HighestPriorityEnemyPlayersOnly: missing top-tier candidate versus fallback.

    Explicit priorities: s4=30 (yard only), p1=10 (barracks). Predict on stays
    home, off reaches barracks. Control gives s4 the barracks: on reaches it.
    Original evidence: work/re/c_toponly_report.md.
    """
    import dataclasses

    mission = aitargetpick_bench()["shared"].mission


    def top_only(name, enabled, positive=False):
        expect = (0, 4, 0, 0) if not enabled or positive else (0, 0, 0, 4)
        m = mission(name, [('CNVHBarracks', None)], expect)
        for role in ('player yard', 'barracks') if positive else ('player yard',):
            m.cast[role] = dataclasses.replace(m.cast[role], side='s4')
            m.find(m.cast[role].name).side = 's4'
        s1, s4 = m.player('s1'), m.player('s4')
        start = next(s for s in m.scripts if s.name == 'CNV AI - Start')
        rel = (0, 0.0, 'Enemy')
        start.do = list(start.do) + [('PLAYER_RELATES_PLAYER', s1, s4, rel),
                                     ('PLAYER_RELATES_PLAYER', s4, s1, rel)]
        wake = next(s for s in m.scripts if s.name == 'CNV AI - Wake')
        wake.do = [a for a in wake.do if a[0] != 'SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES']
        wake.do += [('SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY', s1, s4, 30),
                    ('SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY', s1, m.player('p1'), 10)]
        asset, xml, ref = m.assets[0]
        xml = xml.replace('<AITargetingHeuristic id="CNVHBarracks" ',
                          '<AITargetingHeuristic id="CNVHBarracks" '
                          f'HighestPriorityEnemyPlayersOnly="{str(enabled).lower()}" ')
        m.assets[0] = asset, xml, ref
        return m


    MISSION = {
        'aitopon': lambda: top_only('CampTopOn', True),
        'aitopoff': lambda: top_only('CampTopOff', False),
        'aitopctl': lambda: top_only('CampTopCtl', True, positive=True),
    }
    return dict(MISSION=MISSION)


@cache
def aiunderattack_bench():
    """AITargetingHeuristic UnderAttack: when an object counts as "under attack" and when it stops (engine line D, round 161).

    The aiclosest bench (four FriendlyStructure lanes, ra3ext loaded) with lane 0's heuristic swapped for one of the
    probe's own -- FriendlyStructure, UnderAttack="true", no KindOf filters -- so the friendly filter's UnderAttack gate
    runs on the AI's buildings. Two player Hammer tanks stand off the AI's power plant; the check orders A onto the plant and
    deletes it mid-fight, then orders B on and stops it (TIMES). ra3ext's `ua:` lines (teamlog.under_attack) give the plant's
    set / clear frames and the gate's own answers; predicted: set at the first hit, clear 75 frames (5 s x 15, speed 1)
    after the last hit, the gate true exactly in between, whether or not the source still exists.
    """
    closest = aiclosestenemy_bench()["shared"].mission

    TANK = 'SovietAntiVehicleVehicleTech1'
    # Round 164: A fights the plant early (before the AI's infantry arrive) and is deleted mid-fight (source deleted, window
    # open); B is ordered on after A's window has run out -- its first hit sweeps A's episode closed -- then stopped and kept
    # alive (ceasefire with the source alive).
    TIMES = {'attack at': 2.0, 'stop at': 10.0, 'b attack at': 20.0, 'b stop at': 32.0}


    def mission():
        m = closest()
        m.name = 'CampUnderAtk'
        asset, xml, ref = m.assets[0]
        heuristic = '<AITargetingHeuristic id="CNVUnderAttack" HeuristicType="FriendlyStructure" UnderAttack="true"/>'
        xml = xml.replace('<AIStrategicStateDefinition ', heuristic + '\n  <AIStrategicStateDefinition ', 1)
        xml = xml.replace('"FriendlyLandStructureHeuristic"', '"CNVUnderAttack"', 1)
        m.assets[0] = asset, xml, ref
        m.put(TANK, 'carrier home', 300, 430, name='UNIT - UA Tank', role='ua tank')
        m.put(TANK, 'carrier home', 650, 350, name='UNIT - UA Tank B', role='ua tank b')
        m.spawns.add(TANK)
        m.facts.update(TIMES)
        return m


    MISSION = {'aiunderatk': mission}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


def aiunderattack_gate_c():
    """Delayed UnderAttack gates with identical friendly-structure controls.

    INFERRED prediction: flag activation at 3/9 seconds delays the first target
    evaluation until after a real hit / after ceasefire. Native ua: gate rows,
    not episode-derived clear times, decide whether that premise holds.
    Evidence: work/re/c_underattack_reopen_report.md.
    Measured: ordinary controls choose buildings at f49/f139; injured plant is
    absent from all four candidate lists, so the post-hit positive remains a gap.
    """
    import re

    original = aiunderattack_bench()["shared"].mission
    from parts import Script


    def mission():
        m = original()
        m.name = 'CampUAGate'
        filename, xml, asset = m.assets[0]
        xml = xml.replace('<AIStrategicStateDefinition ',
            '<AITargetingHeuristic id="CNVUAControl" HeuristicType="FriendlyStructure"/>'
            '\n  <AIStrategicStateDefinition ', 1)
        for i in range(4):
            pattern = rf'(<AIStrategicStateDefinition id="CNVClosest{i}".*?</AIStrategicStateDefinition>)'
            def change(match, i=i):
                state = match[0].replace('<ConstantHeuristic/>',
                    f'<ScriptedFlagHeuristic FlagName="CNV UA {i}"/>')
                return re.sub(r'TargetHeuristic="[^"]+"',
                    'TargetHeuristic="' + ('CNVUnderAttack' if i < 2 else 'CNVUAControl') + '"', state)
            xml, n = re.subn(pattern, change, xml, flags=re.S)
            assert n == 1
        m.assets[0] = filename, xml, asset
        start = next(s for s in m.scripts if s.name == 'CNV AI - Start')
        for i in range(4):
            timer = f'CNV UA Gate {i}'
            start.do.append(('SET_MILLISECOND_TIMER', timer, 3.0 if i % 2 == 0 else 9.0))
            m.scripts.append(Script(f'CNV UA Gate {i}', [('TIMER_EXPIRED', timer)],
                                    [('SET_FLAG', f'/CNV UA {i}', 1)]))
        m.facts['stop at'] = 3.0
        return m


    MISSION = {'aiuagate': mission}
    return dict(MISSION=MISSION)


def aiunderattackby_bench():
    """UnderAttackBy land/water contrast after a real hit on the aiunderatk plant.

    INFERRED prediction: the land slot selects the attacking Hammer, the water
    slot does not. Wake is set to 4s, but the measured first selection precedes it:
    Land has no target at f16, takes a real hit source at f19 after the f18 hit.
    Water only publishes f16, so its post-hit rejection remains unproved.
    Evidence: work/re/c_underattackby_resume_report.md.
    """
    underattack = aiunderattack_bench()["shared"].mission


    def mission(water=False):
        m = underattack()
        m.name = 'CampUAByW' if water else 'CampUAByL'
        asset, xml, ref = m.assets[0]
        heuristic = 'UnderAttackByWaterEnemyHeuristic' if water else 'UnderAttackByLandEnemyHeuristic'
        xml = xml.replace('TargetHeuristic="CNVUnderAttack"', f'TargetHeuristic="{heuristic}"', 1)
        m.assets[0] = asset, xml, ref
        start = next(s for s in m.scripts if s.name == 'CNV AI - Start')
        start.do = [(a[0], a[1], 4.0) if a[:2] == ('SET_MILLISECOND_TIMER', 'CNV AI Wake') else a
                    for a in start.do]
        return m


    MISSION = {'aiuabl': mission, 'aiuabw': lambda: mission(True)}
    return dict(MISSION=MISSION)


def aivital_bench():
    """Four retail VitalObjectStatus hosts with script-set native status bits.

    This isolates the bit filter, not aircraft flight or the attachment lifecycle.
    Three airborne samples avoid unique-target contention between the three hosts.
    Before AI wake: set at s0, clear at s4, set again at s6 only in the matching build.
    Prediction: native status mask 15/0/15 (matching), 15/0/0 (nonmatching);
    at s55 each matching team has four at its goal, each nonmatching team four home.
    Any unobserved candidate qualification remains a gap. See work/re/c_vital_report.md.
    Measured s55-60: on 24/4/4/140, off 24/4/4/4. Ground AIRBORNE_TARGET
    samples read zero throughout. Only the script-controlled ATTACHED slice matched;
    lane zero's goal/home areas overlap, so its counts are not disjoint membership.
    """
    setup = aistate_bench()["shared"]
    from parts import Script

    HEURISTICS = ('ClosestAirborneTargetHeuristic', 'ClosestAirborneTargetHeuristic_All',
                  'SafestToAirAirborneTargetHeuristic', 'AttachedVehicleTargetHeuristic_NonUnique')
    UNITS = ('AlliedAntiVehicleInfantry', 'AlliedAntiAirVehicleTech1',
             'SovietAntiVehicleInfantry', setup.TANK)
    BITS = ('AIRBORNE_TARGET',) * 3 + ('ATTACHED',)


    def mission(matching=True):
        m = setup.mission('CampVitalOn' if matching else 'CampVitalOff', gate='const')
        filename, xml, asset = m.assets[0]
        states = [setup._state(f'CNVVital{i}', '', unit, gate='const').replace(
            'ClosestStructureHeuristic', heuristic)
            for i, (unit, heuristic) in enumerate(zip(UNITS, HEURISTICS))]
        start, end = xml.index('  <AIStrategicStateDefinition '), xml.index('  <AIPersonalityDefinition ')
        xml = xml[:start] + '\n'.join(states) + '\n' + xml[end:]
        xml = xml.replace('    <StrategicState id="CNVStateInf" State="CNVStateInf"/>\n'
                          '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>',
                          '\n'.join(f'    <StrategicState id="CNVVital{i}" State="CNVVital{i}"/>' for i in range(4)))
        m.assets[0] = filename, xml, asset
        for k in range(4):
            m.find(m.role(f'peacekeeper {k+1}').name).template = UNITS[0]
        for i, unit in enumerate(UNITS[1:3], 1):
            for k in range(4):
                m.put(unit, 'east base', 50 + 100*i, -150 + 70*k, side='s1',
                      name=f'UNIT - Vital Member {i} {k}', role=f'vital member {i} {k}')
        for i in range(4):
            m.put(setup.TANK, 'east gate' if i < 3 else 'carrier home', 80*i if i < 3 else 0, 0,
                  name=f'UNIT - Vital Sample {i}', role=f'vital sample {i}')
            m.cast[f'vital goal {i}'] = m.role(f'vital sample {i if i == 3 else 0}')
        names = [m.role(f'vital sample {i}').name for i in range(4)]
        m.scripts.append(Script('Vital initial set', [], [
            ('UNIT_CHANGE_OBJECT_STATUS', name, bit, 1) for name, bit in zip(names, BITS)] + [
            ('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1) for name in names] + [
            ('SET_MILLISECOND_TIMER', 'Vital clear', 4.0),
            ('SET_MILLISECOND_TIMER', 'Vital final', 6.0)]))
        for timer, value in [('Vital clear', 0), ('Vital final', int(matching))]:
            m.scripts.append(Script(timer, [('TIMER_EXPIRED', timer)], [
                ('UNIT_CHANGE_OBJECT_STATUS', name, bit, value) for name, bit in zip(names, BITS)]))
        m.cnv_units = UNITS
        m.spawns.update(UNITS)
        m.facts.update({'vital matching': int(matching), 'vital bits': BITS})
        return m


    MISSION = {'aivitalon': mission, 'aivitaloff': lambda: mission(False)}
    return dict(MISSION=MISSION)


def aiwake_bench():
    """Engine probe (line B): does a side with an aiPersonality run its teams before the mission wakes it?

    Bench aialobslo (E99 / E101, benches/ai/tactics/scenes.py#aialphaclose_bench, wake script at 10 s = f150) shows the AI's named team
    empty at f17, 4 members at f21 and its first team move at f26 -- long before f150; the simulator only builds the AI
    player at the wake. Two readings fit:
      H-a  the wake already ran at f0: its only condition is TIMER_EXPIRED and a never-set timer counts as expired, so if
           it is tested before 'CNV AI - Start' sets the timer, UNIT_AI_TRANSFER_ALL / MAKE_BASE happen at once
      H-b  a side with a personality runs teams / states from frame 0, whatever the wake does
    aialobsw is aialobslo with the wake moved to 30 s AND gated by a frame tick >= WAKE_TICK (so it cannot run at f0).
    H-a: the team forms and leaves only after ~f450 (步兵在家 4 until ~s30); H-b: 4 members at ~f21 again, out by ~s17.
    Counters: 帧 (the tick: one per script pass), 唤醒前 (passes before the wake script ran).
    """
    from benches.ai.tactics.scenes import aialphaclose_bench
    ac = aialphaclose_bench()["shared"]
    st = aistate_bench()["shared"]
    from parts import Script

    WAKE_AT = 30.0
    WAKE_TICK = 450                         # script passes: 30 s at 15 a second
    TICK = 'CNV_AW_Tick'
    PRE = 'CNV_AW_Pre'
    WOKE = 'CNV AW Woke'


    def gate(m):
        """The mission's wake moved to WAKE_AT and held to script pass WAKE_TICK (it cannot run before), with counters."""
        start = next(s for s in m.scripts if s.name == 'CNV AI - Start')
        start.do = [a if a[0] != 'SET_MILLISECOND_TIMER' else (a[0], a[1], WAKE_AT) for a in start.do]
        wake = next(s for s in m.scripts if s.name == 'CNV AI - Wake')
        wake.when = list(wake.when) + [('COUNTER', TICK, 3, WAKE_TICK)]
        wake.do = list(wake.do) + [('SET_FLAG', WOKE, 1)]
        m.scripts += [Script('CNV AW - tick', [], [('INCREMENT_COUNTER', 1, TICK)], once=False),
                      Script('CNV AW - before wake', [('FLAG', WOKE, 0)], [('INCREMENT_COUNTER', 1, PRE)], once=False)]
        m.facts.update({'wake at': WAKE_AT, 'wake tick': WAKE_TICK, 'tick counter': TICK, 'pre counter': PRE})
        return m


    def mission():
        m = ac.mission(False, observe=True)
        m.name = 'CampAlObsW'
        return gate(m)


    def const():
        """B round 163: aistateconst (two always-on states aimed by ClosestStructureHeuristic, EnemyStructure Distance)
        with the wake gated as aialobsw. H-g (no enemy is searched before 'make base'): both teams leave ~5 s after the
        wake, ~s33 (步兵在家 4 to ~s30); targets found before the wake: out s14-16 as on the 10 s wake's bench."""
        return gate(st.mission('CampAIConstW', near=True, gate='const'))


    MISSION = {'aialobsw': mission, 'aistateconstw': const}
    return dict(MISSION=MISSION)


def aiwater_bench():
    """ThreatToWater sorting contrast (and ThreatToAir, air()); see work/re/c_water_report.md.

    Two power plants: the nearer has a Guardian nearby, the farther is undefended.
    Distance predicts near; the model's INFERRED water threat predicts far. Named
    controls check reachability only, not same-frame candidate qualification.
    An AI ore collector supplies an amphibious sample without joining the team.
    """
    import dataclasses

    mission = aitargetpick_bench()["shared"].mission
    from parts import Script


    def water(name, sort='ThreatToWater', named=None):
        expected = (4, 0, 0, 0) if sort == 'Distance' or named == 'plant' else (0, 4, 0, 0)
        m = mission(name, [('CNVWater', None)], expected)
        far = m.find(m.role('barracks').name)
        far.template = 'AlliedPowerPlant'
        m.cast['barracks'] = dataclasses.replace(m.cast['barracks'], template=far.template)
        guard = m.find(m.role('tank').name)
        guard.x, guard.y = m.site('east gate', -100, 200)
        m.put('AlliedMiner', 'east base', 100, -100, side='s1',
              name='UNIT - CNV Water Sample', role='water sample')
        kind = 'NamedObject' if named else 'EnemyStructureCloseToShore'
        target = f' Name="{m.role(named).name}"' if named else ''
        heuristic = (f'<AITargetingHeuristic id="CNVWater" HeuristicType="{kind}" '
                     f'SortType="{sort}" VitalKindOf="FS_POWER" Location="Land" '
                     f'SearchRange="5000" MaxDistanceToShore="5000"{target}/>')
        asset, xml, ref = m.assets[0]
        xml = xml.replace('<AIStrategicStateDefinition ', heuristic + '\n  <AIStrategicStateDefinition ', 1)
        m.assets[0] = asset, xml, ref
        return m


    def air(name, sample):
        """ThreatToAir: the guard by the near plant is a player IFV (its missiles hit the air), both sides' guns held;
        the AI's air sample is its first unit of KindOf AIRCRAFT (l4_targets_binary 3.1), here a Cryocopter its LAND
        team does not take, or none: no sample -> every air threat 0 -> near; a sample -> the IFV's plant is the riskier
        -> far."""
        m = water(name, 'ThreatToAir')
        m.facts['expect plant'], m.facts['expect barracks'] = (0, 4) if sample else (4, 0)
        guard = m.find(m.role('tank').name)
        guard.template = 'AlliedAntiAirVehicleTech1'
        guard.x, guard.y = m.site('east gate', -40, 160)  # water()'s spot stands on an MR_Tree04
        m.cast['tank'] = dataclasses.replace(m.cast['tank'], template=guard.template)
        held = [guard.name]
        if sample:
            m.put('AlliedSupportAircraft', 'east base', 300, -300, side='s1', name='UNIT - CNV Air Sample', role='air sample')
            held.append('UNIT - CNV Air Sample')
        m.spawns |= {m.find(n).template for n in held}
        m.scripts.append(Script('CNV Air - hold fire', [], [('UNIT_SET_STANCE', n, 3) for n in held]))
        return m


    MISSION = {
        'aiairnone': lambda: air('CampAirNone', False),
        'aiairsamp': lambda: air('CampAirSamp', True),
        'aiwaterdist': lambda: water('CampWaterDist', 'Distance'),
        'aiwaterthreat': lambda: water('CampWaterThrt'),
        'aiwaternear': lambda: water('CampWaterNear', named='plant'),
        'aiwaterfar': lambda: water('CampWaterFar', named='barracks'),
    }
    return dict(MISSION=MISSION)


BENCHES = (
    aibridge_bench, aibuildexclude_bench, aiclosestenemy_bench, aiconyard_bench,
    aicrate_bench, aienemyfilter_bench, aienemygarr_bench, aiforbid_bench,
    aifrdistance_bench, aifriendly_bench, aihusk_bench, ailocation_bench,
    aimindist_bench, aiminvalue_bench, ainamed_bench, aipoint_bench,
    aiprio_bench, aisearch_bench, aishore_bench, aistate_bench,
    aitarget_bench, aitargetpick_bench, aitoponly_bench, aiunderattack_bench,
    aiunderattack_gate_c, aiunderattackby_bench, aivital_bench, aiwake_bench,
    aiwater_bench,
)
