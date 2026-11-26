"""AI production scenes."""
from functools import cache
from types import SimpleNamespace


def ai_bench():
    """Engine probe: an enemy run by the game's skirmish AI the way the retail missions wake one (docs/story/plans/retail:
    Miyako, Havana) -- read back by checks/ai.py.

    The Niagara map's enemy player (Soviet_1, the Heidelberg container's, Soviet with a Heidelberg personality) is made
    Allied with the Mount Rushmore president's personality (mapxml.set_player: Mission.sides); it starts with a
    construction yard at the east base and three guardians by it, the player with a yard and three guardians at home.

      - asleep until `wake at`: does it build or move on its own?
      - wake (retail "enable naomi ai"): UNIT_AI_TRANSFER_ALL, SKIRMISH_AI_MAKE_BASE at the east base, all enemies
        priority 20, no repairs, no rebuilding, money;
      - attack at `attack at` (retail "give units to tatsu"): SKIRMISH_AI_TRANSFER_ALL -- does its army come over?

    Facts: wake at, attack at, money.
    """
    import resources
    from maps import niagara
    from parts import Mission, Script

    WAKE_AT, ATTACK_AT, MONEY = 60.0, 150.0, 10000
    PERSONALITY = 'AIPersonalityDefinition:AIP_A06_AlliedPresident'


    def mission(name='CampAI', wake=True):
        m = Mission(name=name, map=resources.measured(niagara), facts={'wake at': WAKE_AT, 'attack at': ATTACK_AT, 'money': MONEY})
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': PERSONALITY}
        m.spawns |= {'AlliedPowerPlant', 'AlliedBarracks'}                 # what the AI builds, the check counts
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        for k in range(3):
            m.put('AlliedAntiVehicleVehicleTech1', 'east base', -250, -60 + 60 * k, side='s1')
            m.put('AlliedAntiVehicleVehicleTech1', 'base edge', 0, -60 + 60 * k)
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts.append(Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0),
                                                       ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT),
                                                       ('SET_MILLISECOND_TIMER', 'CNV AI Attack', ATTACK_AT)]))
        if wake:
            m.scripts += [
                Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                       [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                        ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                        ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, MONEY)]),
                Script('CNV AI - Attack', [('TIMER_EXPIRED', 'CNV AI Attack')], [('SKIRMISH_AI_TRANSFER_ALL', s1, 1)])]
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'ai': lambda: mission(),
        'ai_asleep': lambda: mission(name='CampAIS', wake=False),
    }
    return dict(MISSION=MISSION)


@cache
def ai_plan_bench():
    """The plan's 敌方AI section on the bench (plan.py compile_ai, enemy_ai.py): a small plan on the Niagara map whose
    Allied enemy, a construction yard at the east base, is given to the skirmish AI with a generated personality --
    power plants capped at 2, barracks at 1. Read back by checks/ai.py (capped): it builds within its caps, and once
    woken its army comes over and hurts the player's base.

    Facts: wake at, money, caps, watch (how long after waking the run goes on).
    """
    import plan
    import resources

    WAKE_AT, MONEY = 30.0, 30000                    # bench 2026-10-25 (ai/wake): 10000 went on its base, no army
    CAPS = {'电厂': 2, '兵营': 1}
    WATCH = 300.0                                   # after waking: first contact ~60 s, its army ~150 s (bench 2026-10-25)

    PLAN = {
        '关卡': 'ap', '地图': 'niagara', '阵营': {'我': '盟军', '敌': '盟军'},
        '开局': {'部队': [
            {'单位': '建造厂', '在': 'east base', '阵营': '敌', '角色': 'ai yard'},
            {'单位': '建造厂', '在': 'base yard', '角色': 'player yard'},
            {'单位': '守护者坦克', '数量': 3, '在': 'base edge', '角色': 'guardian'}]},
        '段': [{'名字': '一'}],
        '敌方AI': {'性格': '平衡', '基地': 'east base', '资金': MONEY, '唤醒': f'开局 + {WAKE_AT:g}', '上限': dict(CAPS),
                 '接管': ['ai yard']},
    }


    def mission(name='CampAP'):
        m = plan.Compiler(dict(PLAN), name).compile()
        m.map = resources.measured(m.map)           # benched with niagara's nodes at 0 (resources.MEASURED)
        m.spawns |= {'AlliedPowerPlant', 'AlliedBarracks'}                 # what the AI builds, the check counts
        m.facts.update({'wake at': WAKE_AT, 'money': MONEY, 'power cap': CAPS['电厂'], 'barracks cap': CAPS['兵营'],
                        'watch': WATCH})
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'ai_plan': lambda: mission(),
    }
    return dict(MISSION=MISSION, shared=SimpleNamespace(PLAN=PLAN, WAKE_AT=WAKE_AT))


def aiaesthetics_bench():
    """C-line aesthetics switch pair: Distance 2000, retained team, same teleport.

    Only UseAestheticsManager differs. Prediction: enabled wanders to a stand
    point, disabled returns to the defended structure after the 30s displacement.
    Stand-point selection is INFERRED; see work/re/c_aesthetics_report.md.
    """
    from benches.ai.tactics.scenes import aidistance_bench
    distance_mission = aidistance_bench()["shared"].mission


    def mission(enabled):
        m = distance_mission(2000)
        m.name = 'CampAIAesOn' if enabled else 'CampAIAesOff'
        filename, xml, asset = m.assets[0]
        assert xml.count('UseAestheticsManager="true"') == 1
        xml = xml.replace('UseAestheticsManager="true"',
                          f'UseAestheticsManager="{str(enabled).lower()}"')
        m.assets[0] = filename, xml, asset
        m.facts['aesthetics enabled'] = int(enabled)
        return m


    MISSION = {'aiaeson': lambda: mission(True), 'aiaesoff': lambda: mission(False)}
    return dict(MISSION=MISSION)


def aiallbuild_bench():
    """C: native production with a primary infantry enemy and secondary tank enemy.

    Evidence and limits: work/re/c_allbuild_report.md. Only the explicit action
    differs between builds. The secondary player becomes friendly at 70 seconds.
    The action has one player argument; absence is the control, not a reset.
    """
    from missions.aiallbuild_bench import mission


    MISSION = {'aiallbuildon': lambda: mission(True), 'aiallbuildoff': lambda: mission(False)}
    return dict(MISSION=MISSION)


def aibuilding_bench():
    """IsBuildingHeuristic idle boundary: an existing yard is not queued construction.

    The Location bench's land target and four Twinblades, with no build funds.
    Only PassIfBuilding differs. Prediction at s40: false -> four at the plant;
    true -> four at home. KindOf=STRUCTURE. Active construction and KindOf
    matching during construction remain unmeasured; see work/re/e_building_e83.md.
    """
    from benches.ai.targets.scenes import ailocation_bench
    location = ailocation_bench()["shared"]


    def mission(pass_if_building, suffix):
        m = location.mission('Land', suffix)
        m.name = 'CampAIBuild' + suffix
        filename, xml, asset = m.assets[0]
        xml = xml.replace('<ConstantHeuristic/>',
                          '<IsBuildingHeuristic KindOf="STRUCTURE" '
                          f'PassIfBuilding="{str(pass_if_building).lower()}"/>')
        m.assets[0] = (filename, xml, asset)
        m.facts['expect target'] = 0 if pass_if_building else 4
        m.facts['expect home'] = 4 if pass_if_building else 0
        return m


    MISSION = {'aibldtrue': lambda: mission(True, 'T'),
               'aibldfalse': lambda: mission(False, 'F')}
    return dict(MISSION=MISSION)


def aibuildkind_bench():
    """C: IsBuildingHeuristic.KindOf against an active power-plant opening.

    Retail AlliedBaseStates uses STRUCTURE and FS_TECHNOLOGY SUPER_WEAPON
    to exclude construction periods. Here only KindOf differs: FS_POWER matches
    the opening's eight power plants, FS_BARRACKS does not. Existing yards and
    funds are present from map load; the standard s10 script wake is retained.
    The measured native opening already has its first plant at s9.
    Prediction at s40: matching target/home=4/0, nonmatching=0/4; at least two
    completed plants independently establish that the opening actually builds.
    The OR variants add FS_BARRACKS before FS_POWER (one match), or use
    FS_BARRACKS FS_TECHNOLOGY (no match). The false variants invert only
    PassIfBuilding; fixed target/home predictions reverse. Individual queue
    phases remain gaps.
    """
    from benches.ai.targets.scenes import ailocation_bench
    location = ailocation_bench()["shared"]


    def mission(matches, multi=False, pass_if_building=True):
        suffix = ('F' if not pass_if_building else 'O' if multi else '') + ('Y' if matches else 'N')
        m = location.mission('Land', suffix)
        m.name = 'CampAIBKind' + suffix
        filename, xml, asset = m.assets[0]
        kind = 'FS_POWER' if matches else 'FS_BARRACKS'
        if multi:
            kind = 'FS_BARRACKS FS_POWER' if matches else 'FS_BARRACKS FS_TECHNOLOGY'
        xml = xml.replace('<ConstantHeuristic/>',
                          f'<IsBuildingHeuristic KindOf="{kind}" PassIfBuilding="{str(pass_if_building).lower()}"/>')
        opening = ('  <SkirmishOpeningMove id="CNVBKindOpen" Side="PlayerTemplate:Allies">\n'
                   '    <Order Time="0s" Account="PRODUCTION" Deposit="10000"/>\n'
                   + '    <Order Build="AlliedPowerPlant"/>\n' * 8
                   + '    <Order Time="120s"/>\n  </SkirmishOpeningMove>\n')
        xml = xml.replace('  <AIPersonalityDefinition ', opening + '  <AIPersonalityDefinition ', 1)
        xml = xml.replace('    <StrategicState id="CNVStateTP" State="CNVStateTP"/>',
                          '    <OpeningMove Name="CNVBKindOpen" Weight="100%" '
                          'Difficulty="EASY MEDIUM HARD BRUTAL"/>\n'
                          '    <StrategicState id="CNVStateTP" State="CNVStateTP"/>')
        m.assets[0] = (filename, xml, asset)
        # Both start and wake scripts set the balance; fund both identically.
        for script in m.scripts:
            script.do = [(action[0], action[1], 50000) if action[0] == 'PLAYER_SET_MONEY'
                         else action for action in script.do]
        m.spawns.add('AlliedPowerPlant')
        passes = matches == pass_if_building
        m.facts.update({'building matches': matches, 'expect target': 4 if passes else 0,
                        'expect home': 0 if passes else 4})
        return m


    MISSION = {'aibkindyes': lambda: mission(True), 'aibkindno': lambda: mission(False)}
    MISSION.update({'aibkindoryes': lambda: mission(True, multi=True),
                    'aibkindorno': lambda: mission(False, multi=True)})

    MISSION.update({'aibkindfalseyes': lambda: mission(True, multi=True, pass_if_building=False),
                    'aibkindfalseno': lambda: mission(False, multi=True, pass_if_building=False)})
    return dict(MISSION=MISSION)


def aicap_bench():
    """E-line SpecificUnitCap experiment on the existing skirmish scene.

    All three builds run MEDIUM. The control has no extra cap; the other two
    cap Peacekeepers at two for MEDIUM or HARD respectively. Only the difficulty
    mask changes between the capped personalities. Evidence: work/re/e_aicap_e80.md.
    """
    from missions.aiskirm_bench import mission as skirmish


    def mission(mask=None):
        suffix = {'MEDIUM': 'Med', 'HARD': 'Hard', None: 'Ctrl'}[mask]
        m = skirmish('CampAICap' + suffix)
        m.facts['cap active'] = int(mask == 'MEDIUM')
        if mask is not None:
            pid = 'CNVCap' + suffix
            xml = '\n'.join([
                '<?xml version="1.0" encoding="utf-8"?>',
                '<AssetDeclaration xmlns="uri:ea.com:eala:asset">',
                '  <Includes><Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml"/></Includes>',
                f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="1AlliedBalanced">',
                f'    <SpecificUnitCap Unit="AlliedAntiInfantryInfantry" Difficulty="{mask}" Cap="2"/>',
                '  </AIPersonalityDefinition>', '</AssetDeclaration>', ''])
            m.sides['s1']['aiPersonality'] = 'AIPersonalityDefinition:' + pid
            m.assets.append((pid + '.xml', xml, 'AIPersonalityDefinition:' + pid))
        return m


    MISSION = {'aicapctrl': mission, 'aicapmed': lambda: mission('MEDIUM'),
               'aicaphard': lambda: mission('HARD')}
    return dict(MISSION=MISSION)


def aiconstweight_bench():
    """C: ConstantHeuristic.Weight zero/one control, same map and personality.

    Retail uses explicit 0, 0.5, 0.75 and 1. Only the zero versus positive
    eligibility boundary is measured here; relative positive draw odds remain gap.
    Prediction at s40: Weight=0 infantry home/total=4/4; Weight=1=0/4.
    Unregistered Guardians remain home in both. No money or enemy combat units.
    """
    from benches.ai.targets.scenes import aistate_bench
    setup = aistate_bench()["shared"]


    def mission(weight):
        m = setup.mission('CampAIWt' + str(weight), near=True, gate='const')
        filename, xml, asset = m.assets[0]
        xml = xml.replace(setup._state('CNVStateTank', setup.FLAG_TANK, setup.TANK, 'const'), '')
        xml = xml.replace('    <StrategicState id="CNVStateTank" State="CNVStateTank"/>', '')
        xml = xml.replace('<ConstantHeuristic/>', f'<ConstantHeuristic Weight="{weight}"/>')
        m.assets[0] = filename, xml, asset
        m.facts.update({'constant weight': weight, 'expect infantry home': 4 if weight == 0 else 0})
        return m


    MISSION = {'aicwzero': lambda: mission(0), 'aicwone': lambda: mission(1)}
    return dict(MISSION=MISSION)


@cache
def aiexpansion_bench():
    """C Expansion: two ore fields as candidate hypotheses and one ordinary named object.

    Only HeuristicType differs (Expansion / NamedObject). BaseSelection is identical.
    The aibsold/aibsnew pair instead keeps Expansion and only switches SortOrder.
    The aibncap/aibnnone pair only switches PreferredNotBaseTypes.
    The fields are NOT established legal expansion candidates: commands/team state
    must establish selection before any candidate rule can be promoted.
    """
    import types

    import resources
    from parts import Script
    from missions.aiskirm_bench import ai_map
    from benches.ai.targets.scenes import aitargetpick_bench
    target_mission = aitargetpick_bench()["shared"].mission
    from benches.ai.tactics.scenes import aiteams_bench
    HOST = aiteams_bench()["shared"].HOST
    host_unit = aiteams_bench()["shared"].host_unit


    def mission(expansion=True, sort_order=None, preferred_not=None):
        name = 'CampAIExp' if expansion else 'CampAIExpCtl'
        if sort_order:
            name = {'PREFER_OLDEST': 'CampAIBSOld', 'PREFER_NEWEST': 'CampAIBSNew'}[sort_order]
        if preferred_not is not None:
            name = {'CAPTURED': 'CampAIBNCap', '': 'CampAIBNNone'}[preferred_not]
        m = target_mission(name, [('ClosestStructureHeuristic', None)], (0, 0, 0, 4))
        cp = types.ModuleType(m.map.__name__)
        cp.__dict__.update(vars(m.map))
        resource_sites = resources.sites(cp.FIELDS)
        cp.SITES = {k: v for k, v in cp.SITES.items() if k not in resource_sites}
        cp.FIELDS = [f for f in cp.FIELDS if f.name in ('east', 'bluff')]
        cp.SITES.update(resources.sites(cp.FIELDS))
        cp.OBJECTS = [o for o in cp.OBJECTS if o.template != 'OreNode']
        cp.OBJECTS += resources.objects(cp.FIELDS, node_facing=resources.MEASURED)
        m.map = ai_map(cp, library=False)
        filename, xml, asset = m.assets[0]
        kind = 'Expansion' if expansion else 'NamedObject'
        heuristic = (
            f"""  <AITargetingHeuristic id="CNVExpansion" HeuristicType="{kind}"\n"""
            f"""      Name="UNIT - CNV TP Plant" MinDistanceFromEnemy="0" SearchRange="5000" Location="Land">\n"""
            f"""      <BaseSelection PreferredBaseTypes="MAIN_BASE" PreferredNotBaseTypes="CAPTURED"\n"""
            f"""                     SortOrder="PREFER_OLDEST"/>\n"""
            f"""    </AITargetingHeuristic>\n"""
        )
        xml = xml.replace('<AIStrategicStateDefinition ', heuristic + '<AIStrategicStateDefinition ', 1)
        xml = xml.replace('TargetHeuristic="ClosestStructureHeuristic"', 'TargetHeuristic="CNVExpansion"')
        m.assets[0] = filename, xml, asset
        if sort_order:
            m.assets[0] = filename, xml.replace('SortOrder="PREFER_OLDEST"',
                                              f'SortOrder="{sort_order}"'), asset
            m.facts['base sort order'] = sort_order
        if preferred_not is not None:
            filename, xml, asset = m.assets[0]
            m.assets[0] = filename, xml.replace('PreferredNotBaseTypes="CAPTURED"',
                                              f'PreferredNotBaseTypes="{preferred_not}"'), asset
            m.facts['base preferred not'] = preferred_not
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
        m.ext = True
        m.facts['expansion'] = expansion
        m.facts['candidate east'] = (4300.0, 2860.0)
        m.facts['candidate bluff'] = (3273.0, 1173.0)
        return m


    def dual(sort_order):
        """Two real yards with distinct creation times; only SortOrder differs.

        INFERRED: script-created yards become eligible separate MAIN_BASEs. The
        contrast tests this hypothesis; two ore fields alone did not establish it.
        """
        m = mission(True, sort_order)
        m.name = 'CampBS2Old' if sort_order == 'PREFER_OLDEST' else 'CampBS2New'
        m.facts['dual bases'] = True
        # The second yard stands beside the bluff ore, away from the ore node.
        m.waypoint('new yard', 'CNV BS New Yard', 'bluff refinery', -300, 0)
        m.spawns.add('AlliedConstructionYard')
        filename, xml, asset = m.assets[0]
        xml = xml.replace('<ConstantHeuristic/>', '<ScriptedFlagHeuristic FlagName="CNV BS Active"/>')
        m.assets[0] = filename, xml, asset
        m.scripts += [
            Script('BS timers', [], [('SET_MILLISECOND_TIMER', 'CNV BS New', 12.0),
                                     ('SET_MILLISECOND_TIMER', 'CNV BS Start', 18.0)]),
            Script('BS new yard', [('TIMER_EXPIRED', 'CNV BS New')],
                   [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'UNIT - CNV BS New Yard',
                     'AlliedConstructionYard', m.team('s1'), m.mark('new yard'))]),
            Script('BS activate', [('TIMER_EXPIRED', 'CNV BS Start')],
                   [('SET_FLAG', '/CNV BS Active', 1)])]
        return m


    def initial_dual(sort_order):
        """D99 contrast: both AI yards are initial map objects, not script spawns.

        Prediction: two eligible bases; OLD chooses the lower id, NEW the higher.
        Base registration/order must first be confirmed by the passive base table.
        """
        m = dual(sort_order)
        m.name = 'CampBS3Old' if sort_order == 'PREFER_OLDEST' else 'CampBS3New'
        m.facts['initial dual bases'] = True
        m.scripts = [s for s in m.scripts if s.name != 'BS new yard']
        m.put('AlliedConstructionYard', 'bluff refinery', -300, 0, side='s1',
              name='UNIT - CNV BS New Yard', role='second ai yard')
        return m


    def initial_dual_not(preferred_not):
        """Keep OLD sorting fixed; penalize one observed initial-base age type."""
        m = initial_dual('PREFER_OLDEST')
        m.name = 'CampBN2Old' if preferred_not == 'OLDEST_OF_TYPE' else 'CampBN2New'
        filename, xml, asset = m.assets[0]
        m.assets[0] = filename, xml.replace('PreferredNotBaseTypes="CAPTURED"',
                                          f'PreferredNotBaseTypes="{preferred_not}"'), asset
        m.facts['base preferred not'] = preferred_not
        return m


    def initial_dual_preferred(preferred):
        """Keep OLD sorting fixed and no penalty; reward one initial-base age type."""
        m = initial_dual('PREFER_OLDEST')
        m.name = 'CampBP1Old' if preferred == 'OLDEST_OF_TYPE' else 'CampBP1New'
        filename, xml, asset = m.assets[0]
        xml = xml.replace('PreferredBaseTypes="MAIN_BASE"', f'PreferredBaseTypes="{preferred}"')
        xml = xml.replace('PreferredNotBaseTypes="CAPTURED"', 'PreferredNotBaseTypes=""')
        m.assets[0] = filename, xml, asset
        m.facts['base preferred'] = preferred
        return m


    OFF_GRID_WAKE = 10.5                    # B round 197: wake f158/159 -- off the f1 + 15k grid (f151 = 1 + 150 is on it)


    def off_grid(wake=OFF_GRID_WAKE):
        """B round 197 (handoff-b 196 C1 / C2): aiexpc with the wake moved off the 15-frame grid. The slot team's target
        is the AI's own base, which only exists from the wake (MAKE_BASE): aiexpc's wake f151 -> team f152, airev1t's
        named target from f1 -> team f17 (draw f16). A draw pass on a fixed f1 + 15k grid puts this team at f167 (draw
        f166); a draw as soon as the target exists puts it at the wake + 1."""
        m = mission(True)
        m.name = 'CampAIExpW'
        s, = [s for s in m.scripts if s.name == 'CNV AI - Start']
        s.do = [(a[0], a[1], wake) if a[:2] == ('SET_MILLISECOND_TIMER', 'CNV AI Wake') else a for a in s.do]
        assert any(a[:2] == ('SET_MILLISECOND_TIMER', 'CNV AI Wake') and a[2] == wake for a in s.do)
        m.facts['wake at'] = wake
        return m


    MISSION = {'aibp1old': lambda: initial_dual_preferred('OLDEST_OF_TYPE'),
               'aibp1new': lambda: initial_dual_preferred('MOST_RECENT_OF_TYPE'),
               'aibn2old': lambda: initial_dual_not('OLDEST_OF_TYPE'),
               'aibn2new': lambda: initial_dual_not('MOST_RECENT_OF_TYPE'),
               'aibs3old': lambda: initial_dual('PREFER_OLDEST'),
               'aibs3new': lambda: initial_dual('PREFER_NEWEST'),
               'aibs2old': lambda: dual('PREFER_OLDEST'),
               'aibs2new': lambda: dual('PREFER_NEWEST'),
               'aiexpc': lambda: mission(True), 'aiexpw': off_grid, 'aiexpctl': lambda: mission(False),
               'aibsold': lambda: mission(True, 'PREFER_OLDEST'),
               'aibsnew': lambda: mission(True, 'PREFER_NEWEST'),
               'aibncap': lambda: mission(preferred_not='CAPTURED'),
               'aibnnone': lambda: mission(preferred_not='')}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


def aiintervalfrom_bench():
    """C: IntervalHeuristic.CountFrom, identical personality and s10 wake.

    IntervalTime=25s/ActiveTime=30s: MAP_START first on at s25, AI_START
    at s35. Predict home counts s24=4/4, s32=0/4, s42=0/0, total=4.
    Only the first active window is covered; repeated cycles remain gap.
    """
    setup = aipoweradv_bench()["shared"]


    def mission(origin):
        gate = (f'<IntervalHeuristic IntervalTime="25s" ActiveTime="30s" '
                f'CountFrom="{origin}"/>')
        m = setup.mission('CampAIInt', 4, 0, gate=gate)
        m.name = 'CampAIIntM' if origin == 'MAP_START' else 'CampAIIntA'
        m.facts.update({'count from': origin, 'home at 32': 0 if origin == 'MAP_START' else 4})
        return m


    MISSION = {'aiintmap': lambda: mission('MAP_START'), 'aiintai': lambda: mission('AI_START')}
    return dict(MISSION=MISSION)


def ailastexp_bench():
    """C: retail TimeSinceLastExpansionHeuristic.Time values before any expansion.

    The 27-mission AI dependency cache uses 60s and 240s (the compiled campaign
    states encode 240 as a float). Three independent teams share one permanent
    target: those two timers and an always-on recruitment control. Prediction:
    home counts at s40 = 4/4/0, s100 = 0/4/0, s275 = 0/0/0.
    The initial timestamp is INFERRED zero; expansion/reset is deliberately a gap.
    """
    from benches.ai.targets.scenes import aistate_bench
    setup = aistate_bench()["shared"]


    def mission():
        m = setup.mission('CampAILastExp', near=True)
        units = (setup.INF, setup.TANK, 'SovietAntiInfantryInfantry')
        gates = (60, 240, None)
        filename, xml, asset = m.assets[0]
        states = []
        for i, (unit, seconds) in enumerate(zip(units, gates)):
            state = setup._state(f'CNVLastExp{i}', '', unit, gate='const')
            if seconds is not None:
                state = state.replace('<ConstantHeuristic/>',
                    f'<TimeSinceLastExpansionHeuristic Time="{seconds}s"/>')
            state = state.replace('ClosestStructureHeuristic', 'CNVLastExpTarget')
            states.append(state)
        start = xml.index('  <AIStrategicStateDefinition ')
        end = xml.index('  <AIPersonalityDefinition ')
        target = ('  <AITargetingHeuristic id="CNVLastExpTarget" HeuristicType="EnemyStructure" '
                  'SortType="Distance" VitalKindOf="FS_POWER" RequireUniqueTarget="false"/>\n')
        xml = xml[:start] + target + '\n'.join(states) + '\n' + xml[end:]
        xml = xml.replace('    <StrategicState id="CNVStateInf" State="CNVStateInf"/>\n'
                          '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>',
                          '\n'.join(f'    <StrategicState id="CNVLastExp{i}" State="CNVLastExp{i}"/>'
                                    for i in range(3)))
        m.assets[0] = filename, xml, asset
        for k in range(4):
            m.put(units[2], 'east base', -100, -150 + 70*k, side='s1',
                  name=f'UNIT - LastExp Control {k}', role=f'last expansion control {k}')
        m.cnv_units = units
        m.facts.update({'last expansion short': 60, 'last expansion long': 240})
        m.spawns.update(units)
        return m


    # B 11-22: the reset after a real expansion. D's aiexpb200 (its miner unpacks an outpost s106) and aiexpb50 (no
    # outpost: the control) plus one state gated by Time=150s whose team is two Athena cannons (SIEGE_WEAPON: the
    # expansion team excludes them) sent at the player's yard across the river (NamedObject: out of their reach from
    # home, so the team's start shows as the cannons leaving home). No reset: both leave ~s150; a reset at the
    # outpost: aiexpb200's ~s256.
    GATE, CANNON, YARD = 150, 'AlliedAntiStructureVehicle', 'UNIT - CNV AI Player Yard'


    def after(distance):
        aisimpleexp_scene = aisimpleexp_bench()["shared"]
        m = aisimpleexp_scene.built(distance, build=True)
        m.name = f'CampAILastX{distance}'
        filename, xml, asset = m.assets[0]
        state = setup._state('CNVLastExpGate', '', CANNON, gate='const').replace(
            '<ConstantHeuristic/>', f'<TimeSinceLastExpansionHeuristic Time="{GATE}s"/>').replace(
            'ClosestStructureHeuristic', 'CNVLastExpYard')
        target = (f'  <AITargetingHeuristic id="CNVLastExpYard" HeuristicType="NamedObject" Name="{YARD}"'
                  ' MinDistanceFromEnemy="0" SearchRange="5000" Location="Land"/>\n')
        end = xml.index('  <AIPersonalityDefinition ')
        xml = xml[:end] + target + state + '\n' + xml[end:]
        xml = xml.replace('    <StrategicState id="CNVStateTP" State="CNVStateTP"/>',
                          '    <StrategicState id="CNVStateTP" State="CNVStateTP"/>\n'
                          '    <StrategicState id="CNVLastExpGate" State="CNVLastExpGate"/>', 1)
        assert xml.count('CNVLastExpGate') == 3 and m.role('player yard').name == YARD
        m.assets[0] = filename, xml, asset
        for k in range(2):
            m.put(CANNON, 'east base', 150.0, -150.0 + 80*k, side='s1', name=f'UNIT - LastExp Cannon {k}',
                  role=f'last expansion cannon {k}')
        m.spawns |= {CANNON}
        m.facts['last expansion gate'], m.facts['cannon'] = GATE, CANNON
        return m


    MISSION = {'ailastexp': mission, 'ailastx200': lambda: after(200), 'ailastx50': lambda: after(50)}
    return dict(MISSION=MISSION)


def ainodesfull_bench():
    """B208: AllNearbyNodesFullHeuristic (no fields) -- when are the AI's nearby ore nodes 'full'?

    The aistate base (the Allied AI's yard on the east bank, 4 Peacekeepers + 4 Guardians, no money) with two states of
    its own: CNVNodesFull (AllNearbyNodesFullHeuristic, the Peacekeepers) and CNVNodesCtl (ConstantHeuristic, the
    Guardians, a control that the AI is awake and its teams go). The east field's two ore nodes stand ~450 from the yard,
    inside its build radius. Three builds differ only in the AI refineries placed on that field:
      ainf0  none                      -> both nodes open
      ainf1  one, on the field's pad   -> the front node served, the side one open
      ainf2  two, one facing each node -> both served
      ainf3  ainf2 + two more AI Ore Collectors beside each refinery (B209: is 'full' counted in miners?)
      ainf4  ainf2 + one AI Ore Collector beside each refinery (B210: how many miners make a node full)
      ainf5  ainf1 + two AI Ore Collectors beside it (B210: do two miners at one refinery fill the side node too)
    A placed refinery brings its own collector. Bench (B209 / B210): the Peacekeepers leave only on ainf3 -- a node is
    full at 3 own collectors (simai NODE_MINERS, INFERRED: the engine's per-node taken / capacity wrapper is unread); the
    Guardians leave on every build.
    aiopn1900 / aiopn2250 (B, OpenNodeHeuristic Exists=true, MinDistanceFromEnemy 1900 / 2250, ainf0 otherwise): the
    engine asks every known node (not full) for an enemy object (walls aside) within the distance of it (read). Of the
    map's 9 nodes the one farthest from the player's yard and plant is 2074 from the plant: open at 1900, none at 2250.
    ains* (B 11-25, ResourceNodeShareHeuristic Above=false on both states, share = their two percents; work/re
    b1125_nodeshare.md): home iff own / known x 8 players >= the percent; ains2n adds a two-node field in the west.
    aiinc* (B 11-25, IncomeAdvantageHeuristic Value = the two values on the two states, Above as written; work/re
    b1125_income.md: own / enemy mining deposits of the last 90 s): the player's refinery mines at its base refinery;
    aiinca / aiincb have no AI refinery (own 0), aiincc ains2's two (the bench paid one refinery's worth, ratio ~1 --
    either one alone paid nothing, 11-25; simai 2: a world gap in the notes, Values 0.5 / 3 hold on both). The AI wakes at INCOME_WAKE (both well into mining,
    so no first-deposit race). kill: the player's refinery is deleted then -- its deposits leave the window 90 s later
    (both 0: the heuristic passes whatever the Value, bench aiinca 11-25).
    """
    import math

    from benches.ai.targets.scenes import aistate_bench
    from parts import Script
    setup = aistate_bench()["shared"]
    INCOME_WAKE = 100.0

    PAD2 = (150.0 * math.sqrt(0.5), 150.0 * math.sqrt(0.5))   # the side node's pad: PAIR_GAP beside the field's pad


    def mission(name, refineries, miners=0, open_node=None, share=None, extra=False, income=None):
        m = setup.mission(name, near=True)
        filename, xml, asset = m.assets[0]
        states = [setup._state('CNVNodesFull', '', setup.INF, gate='const').replace(
                      '<ConstantHeuristic/>', '<AllNearbyNodesFullHeuristic/>'),
                  setup._state('CNVNodesCtl', '', setup.TANK, gate='const')]
        if open_node is not None:
            states[0] = states[0].replace('<AllNearbyNodesFullHeuristic/>',
                                          f'<OpenNodeHeuristic Exists="true" MinDistanceFromEnemy="{open_node}"/>')
        gates = [f'<ResourceNodeShareHeuristic PercentOfFairShare="{p}%" Above="false"/>' for p in share or ()]
        if income is not None:
            above, values, kill = income
            gates = [f'<IncomeAdvantageHeuristic Value="{v}" Above="{above}"/>' for v in values]
            m.put('AlliedRefinery', 'base refinery', name='UNIT - CNV Player Refinery', role='player refinery')
            start = next(s for s in m.scripts if s.name == 'CNV AI - Start')
            start.do = [('SET_MILLISECOND_TIMER', 'CNV AI Wake', INCOME_WAKE) if a[1:2] == ('CNV AI Wake',) else a
                        for a in start.do]
            if kill is not None:
                start.do.append(('SET_MILLISECOND_TIMER', 'CNV Income Kill', kill))
                m.scripts.append(Script('CNV Income - kill', [('TIMER_EXPIRED', 'CNV Income Kill')],
                                        [('NAMED_DELETE', 'UNIT - CNV Player Refinery')]))
            m.facts['income'], m.ext = income, True
        if gates:
            states = [setup._state(sid, '', unit, gate=g)
                      for sid, unit, g in zip(('CNVNodesFull', 'CNVNodesCtl'), (setup.INF, setup.TANK), gates)]
        states = [s.replace('ClosestStructureHeuristic', 'CNVNodesTarget') for s in states]
        start = xml.index('  <AIStrategicStateDefinition ')
        end = xml.index('  <AIPersonalityDefinition ')
        target = ('  <AITargetingHeuristic id="CNVNodesTarget" HeuristicType="EnemyStructure" '
                  'SortType="Distance" VitalKindOf="FS_POWER" RequireUniqueTarget="false"/>\n')
        xml = xml[:start] + target + '\n'.join(states) + '\n' + xml[end:]
        xml = xml.replace('    <StrategicState id="CNVStateInf" State="CNVStateInf"/>\n'
                          '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>',
                          '    <StrategicState id="CNVNodesFull" State="CNVNodesFull"/>\n'
                          '    <StrategicState id="CNVNodesCtl" State="CNVNodesCtl"/>')
        m.assets[0] = filename, xml, asset
        if refineries >= 1:
            m.put('AlliedRefinery', 'east refinery', side='s1', name='UNIT - CNV AI Refinery 1', role='ai refinery 1')
        if refineries >= 2:
            m.put('AlliedRefinery', 'east refinery', *PAD2, side='s1', name='UNIT - CNV AI Refinery 2',
                  role='ai refinery 2')
        for r, pad in enumerate(((0.0, 0.0), PAD2)[:refineries]):
            for k in range(miners):                  # B209 H1: extra AI miners beside each refinery (taken / capacity?)
                m.put('AlliedMiner', 'east refinery', pad[0] - 160.0, pad[1] - 60.0 + 120.0 * k, side='s1',
                      name=f'UNIT - CNV AI Miner {r} {k}', role=f'ai miner {r} {k}')
        m.facts['ai refineries'] = refineries
        m.facts['ai miners'] = miners
        m.facts['open node'] = open_node
        m.facts['share'] = share
        m.facts['ore nodes'] = 11 if extra else 9
        if extra:                    # ains2n: two more map nodes in the west field
            import types

            import resources
            field = resources.Field('extra', 500.0, 1300.0, 45.0, 1)
            layout = types.ModuleType(m.map.__name__)
            layout.__dict__.update(vars(m.map))
            layout.FIELDS = list(m.map.FIELDS) + [field]
            layout.SITES = {**m.map.SITES, **resources.sites([field])}
            new = resources.objects([field], [])
            layout.OBJECTS = list(m.map.OBJECTS) + new
            layout.SCENERY = [o for o in m.map.SCENERY if all(math.dist((o.x, o.y), (d.x, d.y)) >= 300 for d in new)]
            m.map = layout
        return m


    MISSION = {'ainf0': lambda: mission('CampNodesFull0', 0),
               'ainf1': lambda: mission('CampNodesFull1', 1),
               'ainf2': lambda: mission('CampNodesFull2', 2),
               'ainf3': lambda: mission('CampNodesFull3', 2, miners=2),
               'ainf4': lambda: mission('CampNodesFull4', 2, miners=1),
               'ainf5': lambda: mission('CampNodesFull5', 1, miners=2),
               'aiopn1900': lambda: mission('CampOpNode1900', 0, open_node=1900),
               'aiopn2250': lambda: mission('CampOpNode2250', 0, open_node=2250),
               'ains1': lambda: mission('CampNodeShare1', 1, share=(80, 100)),
               'ains2': lambda: mission('CampNodeShare2', 2, share=(170, 190)),
               'ains2l': lambda: mission('CampNodeShr2L', 2, share=(10, 60)),
               'ains2a': lambda: mission('CampNodeShr2A', 2, share=(85, 140)),
               'ains2b': lambda: mission('CampNodeShr2B', 2, share=(100, 125)),
               'ains2c': lambda: mission('CampNodeShr2C', 2, share=(104, 118)),
               'ains2d': lambda: mission('CampNodeShr2D', 2, share=(110, 120)),
               'ains2n': lambda: mission('CampNodeShr2N', 2, share=(84, 95), extra=True),
               'aiinca': lambda: mission('CampIncomeA', 0, income=('true', (0.5, 1.5), 150.0)),
               'aiincb': lambda: mission('CampIncomeB', 0, income=('false', (0.5, 1.5), None)),
               'aiincc': lambda: mission('CampIncomeC', 2, income=('true', (0.5, 3.0), None))}
    return dict(MISSION=MISSION)


@cache
def aiomove_bench():
    """Engine probe: which opening a personality draws (<OpeningMove> Weight / Difficulty), and OpeningMoveHeuristic
    Complete gating a strategic state on the opening being done (read back by benches/ai/production/checks.py#engine_aiomove; private
    ai/opening.py choose(), ai/states.py value 'OpeningMoveHeuristic').

    aiotime_bench's set-up (Niagara, s1 Allied with a yard at the east base, woken at 10 s with 50000,
    AlliedCoopBasePersonality with every inherited strategic state removed), the openings the probe's own:
      CNVOpenP  Build AlliedPowerPlant            CNVOpenB  Build AlliedBarracks
      CNVOpenT  aiotime's: plant / Time 30s / plant / Time 20s / plant (the third ~s59 on the bench)
    Variants (which opening: count the plants and barracks s1 has):
      aiowt   P Weight 0%, B 100%                     -> a barracks, no plant (a 0 weight is never drawn)
      aiowt2  P 100%, B 0%                            -> a plant (the control: not just the first / last line)
      aiodf   P 100% Difficulty EASY, B 100% MEDIUM HARD BRUTAL -> a barracks (the bench plays MEDIUM, aidiff)
      aiodf2  P MEDIUM HARD BRUTAL, B EASY            -> a plant
    OpeningMoveHeuristic (opening T; one more state CNVStateOM: a SimpleAttack team of 4 Guardians at the closest enemy
    structure, a player power plant ~750 west, as aipoweradv; count the Guardians at home):
      aiohc1  Complete true  -> home while the opening runs, out after the third plant (~s59)
      aiohc0  Complete false -> out right after the wake (~s14), as an always-on state

    Facts: wake at, money, plants, barracks (what stands at s40), and for aiohc*: ai tanks, home until, out by.
    """
    import resources
    from maps import niagara
    from benches.ai.targets.scenes import aistate_bench
    BASE = aistate_bench()["shared"].BASE
    INHERITED = aistate_bench()["shared"].INHERITED
    T_ORDERS = aiotime_bench()["shared"].ORDERS
    from parts import Mission, Script

    WAKE_AT, MONEY = 10.0, 50000
    PLANT, BARRACKS, TANK = 'AlliedPowerPlant', 'AlliedBarracks', 'AlliedAntiVehicleVehicleTech1'
    ALL = 'EASY MEDIUM HARD BRUTAL'
    MOVES = {'CNVOpenP': (('Build', PLANT),), 'CNVOpenB': (('Build', BARRACKS),), 'CNVOpenT': T_ORDERS,
             'CNVOpenBT': (('Build', BARRACKS), ('Time', '5s')), 'CNVOpenPP': (('Build', PLANT), ('Build', PLANT)),
             'CNVOpenPPP': (('Build', PLANT),) * 3, 'CNVOpenPT': (('Build', PLANT), ('Time', '5s')),
             'CNVOpenTP': (('Time', '5s'), ('Build', PLANT)), 'CNVOpenBP': (('Build', BARRACKS), ('Build', PLANT)),
             'CNVOpenPB': (('Build', PLANT), ('Build', BARRACKS)),
             'CNVOpenPT30': (('Build', PLANT), ('Time', '30s')), 'CNVOpenPT15': (('Build', PLANT), ('Time', '15s')),
             'CNVOpenPPT30': (('Build', PLANT), ('Build', PLANT), ('Time', '30s')),
             'CNVOpenT30P': (('Time', '30s'), ('Build', PLANT)),
             # round 88: a Time carrying an Account / Deposit, as retail AlliedStandard's does
             'CNVOpenPPTD': (('Build', PLANT), ('Build', PLANT),
                             ('Time', '30s', {'Account': 'PRODUCTION', 'Deposit': '2000'})),
             # round 89: is it the whole opening's end (the last Time point) or each Build's own wait?
             'CNVOpenBT3PT30': (('Build', BARRACKS), ('Time', '3s'), ('Build', PLANT), ('Time', '30s')),
             'CNVOpenBPT5': (('Build', BARRACKS), ('Build', PLANT), ('Time', '5s')),
             'CNVOpenPPT8': (('Build', PLANT), ('Build', PLANT), ('Time', '8s')),
             'CNVOpenPT10': (('Build', PLANT), ('Time', '10s')),
             'CNVOpenBT30': (('Build', BARRACKS), ('Time', '30s'))}


    def _order(o):
        """(kind, value) or (kind, value, {more attributes}) -> the <Order .../> line."""
        extra = ''.join(f' {k}="{v}"' for k, v in (o[2] if len(o) > 2 else {}).items())
        return f'    <Order {o[0]}="{o[1]}"{extra} />'


    def personality_xml(pid, lines, gate=None):
        """lines: [(move id, weight, difficulty)]; gate: OpeningMoveHeuristic Complete (True / False) or None."""
        removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
        used = sorted({mid for mid, _, _ in lines})
        out = ['<?xml version="1.0" encoding="utf-8"?>',
               '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
               ' xmlns:xai="uri:ea.com:eala:asset:instance">',
               '  <Tags></Tags>',
               '  <Includes>',
               f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
               '  </Includes>']
        for mid in used:
            out += [f'  <SkirmishOpeningMove id="{mid}" Side="PlayerTemplate:Allies">',
                    *[_order(o) for o in MOVES[mid]],
                    '  </SkirmishOpeningMove>']
        if gate is not None:
            out.append((
                f"""  <AIStrategicStateDefinition id="CNVStateOM" MaxTargets="1">\n"""
                f"""    <Heuristic>\n"""
                f"""      <OpeningMoveHeuristic Complete="{'true' if gate else 'false'}"/>\n"""
                f"""    </Heuristic>\n"""
                f"""    <TargetHeuristic TargetHeuristic="ClosestStructureHeuristic"/>\n"""
                f"""    <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE" EndIfStateTurnsOff="false">\n"""
                f"""      <TeamTemplate MinUnits="2" MaxUnits="8" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"\n"""
                f"""                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"\n"""
                f"""                    MicroManager="StandardMicroManager_MEDIUM">\n"""
                f"""        <ObjectFilter Rule="ANY">\n"""
                f"""          <IncludeThing>{TANK}</IncludeThing>\n"""
                f"""        </ObjectFilter>\n"""
                f"""      </TeamTemplate>\n"""
                f"""    </Tactic>\n"""
                f"""  </AIStrategicStateDefinition>"""
            ))
        out += [f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
                *[f'    <OpeningMove Name="{mid}" Weight="{w}" Difficulty="{d}"/>' for mid, w, d in lines],
                *removed]
        if gate is not None:
            out.append('    <StrategicState id="CNVStateOM" State="CNVStateOM"/>')
        out += ['  </AIPersonalityDefinition>', '</AssetDeclaration>', '']
        return '\n'.join(out)


    def mission(name, lines, plants, barracks, gate=None, home_until=None, out_by=None, money_first=False):
        """money_first: give the money before SKIRMISH_AI_MAKE_BASE in the wake script (does the opening see 0?)."""
        pid = 'CNVOMove' + name[len('CampAIOM'):]
        facts = {'wake at': WAKE_AT, 'money': MONEY, 'plants': plants, 'barracks': barracks}
        tanks = 4 if gate is not None else 0
        if tanks:
            facts |= {'ai tanks': tanks, 'out by': out_by}
            if home_until is not None:
                facts['home until'] = home_until
        m = Mission(name=name, map=resources.measured(niagara), facts=facts)
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
        m.assets.append((f'{pid}.xml', personality_xml(pid, lines, gate), f'AIPersonalityDefinition:{pid}'))
        m.spawns |= {PLANT, BARRACKS, TANK}
        if tanks:
            m.cnv_units = (TANK,)
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        if tanks:
            m.put(PLANT, 'east gate', -300.0, 0.0, name='UNIT - CNV AI Player Target', role='player target')
        for k in range(tanks):
            m.put(TANK, 'east base', -200.0 - 80.0 * (k // 4), 160.0 + 70.0 * (k % 4), side='s1', angle=3.1416,
                  name=f'UNIT - CNV AI Tank {k + 1}', role=f'ai guardian {k + 1}')
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   ([('PLAYER_SET_MONEY', s1, MONEY)] if money_first else [])
                   + [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                      ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                      ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0)]
                   + ([] if money_first else [('PLAYER_SET_MONEY', s1, MONEY)]))]
        return m


    MISSION = {
        # round 89: each opening a Build + Time 30s (a lone Build is dropped, aiom1 / aiom7; Build + Time 30s stands, aiom11)
        'aiowt': lambda: mission('CampAIOMWt', [('CNVOpenPT30', '0%', ALL), ('CNVOpenBT30', '100%', ALL)], 0, 1),
        'aiowt2': lambda: mission('CampAIOMWt2', [('CNVOpenPT30', '100%', ALL), ('CNVOpenBT30', '0%', ALL)], 1, 0),
        'aiodf': lambda: mission('CampAIOMDf', [('CNVOpenPT30', '100%', 'EASY'),
                                                ('CNVOpenBT30', '100%', 'MEDIUM HARD BRUTAL')],
                                 0, 1),
        'aiodf2': lambda: mission('CampAIOMDf2', [('CNVOpenPT30', '100%', 'MEDIUM HARD BRUTAL'),
                                                  ('CNVOpenBT30', '100%', 'EASY')],
                                  1, 0),
        'aiohc1': lambda: mission('CampAIOMHc1', [('CNVOpenT', '100%', ALL)], 1, 0, gate=True, home_until=42, out_by=46),
        'aiohc0': lambda: mission('CampAIOMHc0', [('CNVOpenT', '100%', ALL)], 1, 0, gate=False, home_until=None,
                                  out_by=25),
        # round 84: why aiowt* / aiodf* built nothing -- narrow it down (one variable each)
        'aiom1': lambda: mission('CampAIOM1', [('CNVOpenP', '100%', ALL)], 1, 0),              # one line, one Build
        'aiom2': lambda: mission('CampAIOM2', [('CNVOpenP', '100%', ALL), ('CNVOpenB', '100%', ALL)], 1, 0),  # two lines
        'aiom3': lambda: mission('CampAIOM3', [('CNVOpenT', '100%', ALL), ('CNVOpenB', '0%', ALL)], 1, 0),    # T + a 0%
        'aiom4': lambda: mission('CampAIOM4', [('CNVOpenBT', '100%', ALL)], 0, 1),             # one Build then a Time
        'aiom5': lambda: mission('CampAIOM5', [('CNVOpenPP', '100%', ALL)], 2, 0),             # two Builds, no Time
        # round 85: is it the last Build, a Build in the wake frame, or the barracks?
        'aiom6': lambda: mission('CampAIOM6', [('CNVOpenPPP', '100%', ALL)], 3, 0),            # three Builds
        'aiom7': lambda: mission('CampAIOM7', [('CNVOpenPT', '100%', ALL)], 1, 0),             # Build plant, Time 5s
        'aiom8': lambda: mission('CampAIOM8', [('CNVOpenTP', '100%', ALL)], 1, 0),             # Time 5s, Build plant
        'aiom9': lambda: mission('CampAIOM9', [('CNVOpenBP', '100%', ALL)], 1, 1),             # barracks, plant
        'aiom10': lambda: mission('CampAIOM10', [('CNVOpenPB', '100%', ALL)], 1, 1),           # plant, barracks
        # round 86: does the wait after a lone Build matter (T's first plant, 30 s before its next order, is built)
        'aiom11': lambda: mission('CampAIOM11', [('CNVOpenPT30', '100%', ALL)], 1, 0),         # plant, Time 30s
        'aiom12': lambda: mission('CampAIOM12', [('CNVOpenPT15', '100%', ALL)], 1, 0),         # plant, Time 15s
        'aiom13': lambda: mission('CampAIOM13', [('CNVOpenPPT30', '100%', ALL)], 2, 0),        # plant, plant, Time 30s
        'aiom14': lambda: mission('CampAIOM14', [('CNVOpenT30P', '100%', ALL)], 1, 0),         # Time 30s, plant
        # round 88: the retail difference (a Deposit on the Time) and the money at the wake
        'aiom15': lambda: mission('CampAIOM15', [('CNVOpenPPTD', '100%', ALL)], 2, 0),         # aiom13 + Deposit 2000
        'aiom16': lambda: mission('CampAIOM16', [('CNVOpenP', '100%', ALL)], 1, 0, money_first=True),  # aiom1, money 1st
        # round 89 (guesses by "the opening ends >= X s after the wake keeps all, else only the last Build", 5 < X <= 10)
        'aiom17': lambda: mission('CampAIOM17', [('CNVOpenBT3PT30', '100%', ALL)], 1, 1),     # B, Time 3s, P, Time 30s
        'aiom18': lambda: mission('CampAIOM18', [('CNVOpenBPT5', '100%', ALL)], 1, 0),        # B, P, Time 5s
        'aiom19': lambda: mission('CampAIOM19', [('CNVOpenPPT8', '100%', ALL)], 1, 0),        # P, P, Time 8s (X): bench 1
        'aiom20': lambda: mission('CampAIOM20', [('CNVOpenPT10', '100%', ALL)], 1, 0),        # P, Time 10s (edge)
    }
    return dict(MISSION=MISSION, shared=SimpleNamespace(ALL=ALL, mission=mission))


@cache
def aiopath_bench():
    """Engine probe: PathToTargetHeuristic in the opening pick -- does the AI judge "no way to the enemy" by the unit the
    heuristic names (benches/ai/production/checks.py#engine_aiopath; private ai/opening._holds, simai.Brain.path_to_target)?

    aiopen_bench as is (Niagara, the enemy s1 Allied with one yard, woken at 10 s with 50000 money), but s1's
    personality is the probe's: inheritFrom AlliedCoopBaseSkirmishPersonality (it and its parents have no OpeningMove),
    two lines only, every difficulty:
      AlliedStandard  PathToTargetHeuristic PathExists="true"   (barracks first, power plant at +10 s: engine_aiopen)
      AlliedIsland    PathToTargetHeuristic PathExists="false"  (power plant first, no barracks in the list)
    both tested with the same ObjectTypeToUseForTest:
      aiopath1  CNVPathP: AlliedPowerPlant -- no locomotor, so (program read, l4_states.md 3) no path: Island expected
      aiopath0  CNVPathI: SovietAntiInfantryInfantry -- the stock test unit, Niagara is land: Standard expected
      aiopathi  CNVPathO: ONE line, AlliedIsland with PathExists="true", the infantry tester -- does the probe's
                personality take at all (a power plant first = yes; barracks first = the stock opening, it did not)
      aiopathr  CNVPathR: aiopath1's two lines, order reversed (Island first) -- if both lines hold, the draw (same
                weights) takes the first: Island here; if the power plant really has a path, Standard again
    """
    aiopen_scene = aiopen_bench()["shared"]

    BASE = 'AlliedCoopBaseSkirmishPersonality'


    def personality_xml(pid, tester, moves=(('AlliedStandard', 'true'), ('AlliedIsland', 'false')),
                        condition='NORMAL'):
        test = (f'<PathToTargetHeuristic PathExists="{{}}" ObjectTypeToUseForTest="{tester}"'
                f' LocomotorConditionToUseForTest="{condition}" />')
        lines = []
        for move, exists in moves:
            lines += [f'    <OpeningMove Name="{move}" Weight="100%" Difficulty="EASY MEDIUM HARD BRUTAL">',
                      '      <Heuristic>', '        ' + test.format(exists), '      </Heuristic>',
                      '    </OpeningMove>']
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xai="uri:ea.com:eala:asset:instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
            '  </Includes>',
            f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
            *lines,
            '  </AIPersonalityDefinition>',
            '</AssetDeclaration>', ''])


    def mission(name, pid, tester, **kw):
        m = aiopen_scene.mission(name=name)
        m.draw = 0.1    # the AI's protocol draw (simtech.Book): benches aipclandt / aipcampht bought AirPower (0.1 on it)
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
        m.assets.append((f'{pid}.xml', personality_xml(pid, tester, **kw), f'AIPersonalityDefinition:{pid}'))
        return m


    def disconnected(amphibious=False):
        """C condition probe: no bridges; independent scripted crossing controls.

        INFERRED prediction: NORMAL cannot join the banks; SUPERSONIC can.
        The tester has ground NORMAL and ground + water SUPERSONIC locomotors.
        The controls use the very same sets under NORMAL, so physical reachability
        can be checked independently of the opening heuristic's chosen condition.
        """
        import types
        from parts import Unit
        from units import convoy

        tester = convoy.truck(id='CNVPathTester', cargo=None, speed=90)
        extra = ('<LocomotorSet Locomotor="TestReactiveLocomotorTANK" '
                 'Condition="SUPERSONIC" Speed="90" />\n'
                 '<LocomotorSet Locomotor="AlliedMinerWaterLocomotor" '
                 'Condition="SUPERSONIC" Speed="90" />\n')
        tester.xml = tester.xml.replace('</GameObject>', extra + '</GameObject>')
        control = Unit('CNVPathSwimmer', tester.xml.replace('CNVPathTester', 'CNVPathSwimmer')
                       .replace('Condition="SUPERSONIC"', 'Condition="NORMAL"'),
                       what='Path probe crossing control with ground and water locomotors')
        # Remove the duplicate ground set from the swimmer, retaining one of each.
        control.xml = control.xml.replace(
            '<LocomotorSet Locomotor="TestReactiveLocomotorTANK" Condition="NORMAL" Speed="90" />\n', '', 1)
        name, pid = ('CampPCAmph', 'CNVPCAmph') if amphibious else ('CampPCLand', 'CNVPCLand')
        m = mission(name, pid, tester.id, condition='SUPERSONIC' if amphibious else 'NORMAL')
        cp = types.ModuleType(m.map.__name__)
        cp.__dict__.update(vars(m.map))
        cp.BRIDGES = []
        cp.OBJECTS = [o for o in cp.OBJECTS if o.template != 'HB_Bridge_02']
        m.map = cp
        m.units += [tester, control]
        m.put(tester.id, 'east gate', 0, -100, role='land control', name='UNIT - CNV PC Land')
        m.put(control.id, 'east gate', 0, 100, role='amphib control', name='UNIT - CNV PC Amph')
        m.waypoint('crossing goal', 'CNV PC Goal', 'front')
        m.facts['path amphibious'] = amphibious
        return m


    def disconnected_ready(amphibious=False):
        """D108 follow-up: register base and enemy priorities before opening choice.

        Keep the old builds intact for replay. Money still arrives at 10 seconds.
        INFERRED: start-script registration precedes the engine's opening decision.
        The read-only path trace must confirm this before interpreting a split.
        """
        m = disconnected(amphibious)
        m.name = 'CampPCAmphY' if amphibious else 'CampPCLandY'
        m.ext = True
        s1 = m.player('s1')
        m.scripts[0].do += [('SKIRMISH_AI_MAKE_BASE', s1, m.mark('ai base')),
                            ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20)]
        return m


    def observed(m):
        """B 11-23: + the teams host (ra3ext alone logs no cmd: lines) -- which protocol does the AI buy (cmd 24e)?"""
        from benches.ai.tactics.scenes import aiteams_bench
        host_unit = aiteams_bench()["shared"].host_unit
        HOST = aiteams_bench()["shared"].HOST
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
        m.name, m.ext = m.name + 'T', True
        return m


    MISSION = {
        'aipclandt': lambda: observed(disconnected(False)),
        'aipcampht': lambda: observed(disconnected(True)),
        'aipclandy': lambda: disconnected_ready(False),
        'aipcamphy': lambda: disconnected_ready(True),
        'aipcland': lambda: disconnected(False),
        'aipcamph': lambda: disconnected(True),
        # Same tester and land endpoints: deep-water NORMAL versus flying SUPERSONIC.
        'aiopwater': lambda: mission('CampPathWater', 'CNVPathWater', 'JapanAntiAirShip'),
        'aiopair': lambda: mission('CampPathAir', 'CNVPathAir', 'JapanAntiAirShip', condition='SUPERSONIC'),
        'aiopath1': lambda: mission('CampAIPath1', 'CNVPathP', 'AlliedPowerPlant'),
        'aiopath0': lambda: mission('CampAIPath0', 'CNVPathI', 'SovietAntiInfantryInfantry'),
        'aiopathi': lambda: mission('CampAIPathI', 'CNVPathO', 'SovietAntiInfantryInfantry',
                                    moves=(('AlliedIsland', 'true'),)),
        'aiopathr': lambda: mission('CampAIPathR', 'CNVPathR', 'AlliedPowerPlant',
                                    moves=(('AlliedIsland', 'false'), ('AlliedStandard', 'true'))),
    }
    return dict(MISSION=MISSION, shared=SimpleNamespace(disconnected=disconnected, observed=observed))


@cache
def aiopen_bench():
    """Engine probe: the skirmish AI's opening build order and timing (read back by benches/ai/production/checks.py#engine_aiopen).

    Same Niagara map as benches/ai/production/scenes.py#ai_bench. The enemy (s1) is Allied with the stock AlliedBalanced personality, one construction
    yard at the east base and nothing else; the player has a yard at home. Asleep until WAKE_AT, then the retail wake set
    (UNIT_AI_TRANSFER_ALL, SKIRMISH_AI_MAKE_BASE, priorities 20, no repairs, no rebuilding) with 50000 money so money is
    no limit (aiopenpoor: 3000, the opening short of money). No attack script.

    Facts: wake at, money.
    """
    import resources
    from maps import niagara
    from parts import Mission, Script

    WAKE_AT, MONEY, POOR = 10.0, 50000, 3000
    PERSONALITY = 'AIPersonalityDefinition:1AlliedBalanced'
    COUNTED = ('AlliedBarracks', 'AlliedPowerPlant', 'AlliedRefinery', 'AlliedWarFactory', 'AlliedAntiInfantryVehicle',
               'AlliedAntiInfantryVehicle_Ground', 'AlliedNavalYard', 'AlliedMiner')


    def mission(name='CampAIOpen', money=MONEY):
        m = Mission(name=name, map=resources.measured(niagara), facts={'wake at': WAKE_AT, 'money': money})
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': PERSONALITY}
        m.spawns |= set(COUNTED)
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, money)])]
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {'aiopen': mission, 'aiopenpoor': lambda: mission('CampAIPoor', money=POOR)}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


def aiopenside_bench():
    """E82: fixed Allied AI, one explicitly mounted opening; only its Side changes.

    The opening builds three power plants, then waits 120 seconds. Both Side
    values occur in retail SDK openings. Default model prediction: three plants
    for both (it stores Side but does not filter the opening by it). That prediction
    failed for Soviet (engine two plants, one barracks). The fallback source is
    unverified; evidence belongs in work/re/e_openside_e82.md.
    """
    from missions.aiskirm_bench import acct_xml, mission as skirmish


    def mission(side, suffix):
        m = skirmish('CampAIOpen' + suffix, lib=False)
        xml = acct_xml('PRODUCTION')
        head, rest = xml.split('  <SkirmishOpeningMove', 1)
        _, tail = rest.split('  </SkirmishOpeningMove>', 1)
        xml = (head + f'  <SkirmishOpeningMove id="CNVAcctOpen" Side="PlayerTemplate:{side}">\n'
               + '    <Order Build="AlliedPowerPlant"/>\n' * 3
               + '    <Order Time="120s"/>\n  </SkirmishOpeningMove>' + tail)
        m.sides['s1']['aiPersonality'] = 'AIPersonalityDefinition:CNVAcct'
        m.assets.append(('CNVAcct.xml', xml, 'AIPersonalityDefinition:CNVAcct'))
        m.facts['side matches'] = int(side == 'Allies')
        return m


    MISSION = {'aiosallies': lambda: mission('Allies', 'A'),
               'aiossoviet': lambda: mission('Soviet', 'S')}
    return dict(MISSION=MISSION)


@cache
def aiotime_bench():
    """Engine probe: an opening's <Order Time=...> -- from when is the time counted (read back by benches/ai/production/checks.py#engine_aiotime;
    private ai/opening.py Opening.step: "a Time order waits until that many seconds have passed since the opening began").

    aiopen_bench's map and wake (Niagara, s1 Allied with one yard at the east base, woken at 10 s with 50000), but the
    personality is the probe's own: AlliedCoopBasePersonality (no OpeningMove of its own, OpeningMoveBudget inherited),
    every inherited strategic state removed, one OpeningMove of the probe's SkirmishOpeningMove CNVOpenTime:
      Build AlliedPowerPlant / Time 30s / Build AlliedPowerPlant / Time 20s / Build AlliedPowerPlant
    A power plant takes ~153 frames (aiopen f1-f3). Mission seconds of the three plants under each reading of Time:
      since the wake (the model)        ~20 / ~50 / ~60   (the 20s point has passed: the third goes in at once)
      since the previous Time order     ~20 / ~50 / ~70
      since the mission start           ~20 / ~40 / ~50

    Facts: wake at, money.
    """
    import resources
    from maps import niagara
    from benches.ai.targets.scenes import aistate_bench
    BASE = aistate_bench()["shared"].BASE
    INHERITED = aistate_bench()["shared"].INHERITED
    from parts import Mission, Script

    WAKE_AT, MONEY = 10.0, 50000
    PID, MOVE = 'CNVOpenT', 'CNVOpenTime'
    PLANT = 'AlliedPowerPlant'
    ORDERS = (('Build', PLANT), ('Time', '30s'), ('Build', PLANT), ('Time', '20s'), ('Build', PLANT))


    def personality_xml(pid=PID, orders=ORDERS):
        removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xai="uri:ea.com:eala:asset:instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
            '  </Includes>',
            f'  <SkirmishOpeningMove id="{MOVE}" Side="PlayerTemplate:Allies">',
            *[f'    <Order {k}="{v}" />' for k, v in orders],
            '  </SkirmishOpeningMove>',
            f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
            f'    <OpeningMove Name="{MOVE}" Weight="100%" Difficulty="EASY MEDIUM HARD BRUTAL"/>',
            *removed,
            '  </AIPersonalityDefinition>',
            '</AssetDeclaration>', ''])


    def mission(name='CampAIOTime'):
        m = Mission(name=name, map=resources.measured(niagara), facts={'wake at': WAKE_AT, 'money': MONEY})
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
        m.assets.append((f'{PID}.xml', personality_xml(), f'AIPersonalityDefinition:{PID}'))
        m.spawns |= {PLANT}
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, MONEY)])]
        return m


    MISSION = {'aiotime': mission}
    return dict(MISSION=MISSION, shared=SimpleNamespace(ORDERS=ORDERS))


def aipathx_bench():
    """Engine line D round 108: C's river-bank PathToTarget probe (aiopath_bench.disconnected) with ra3ext on, so the
    run's ra3ext.log carries one `ptt:` line per PathToTargetHeuristic evaluation (condition, locomotor list, both
    base points, path result and code, the branch that decided). Same mission otherwise; read back by
    benches/ai/production/checks.py#engine_aipathx (C's check unchanged).
    """
    aiopath_scene = aiopath_bench()["shared"]


    def probed(amphibious):
        m = aiopath_scene.disconnected(amphibious)
        m.name = 'CampPCAmphX' if amphibious else 'CampPCLandX'
        m.ext = True
        return m


    MISSION = {'aipclandx': lambda: probed(False), 'aipcamphx': lambda: probed(True)}
    return dict(MISSION=MISSION)


@cache
def aipeak_bench():
    """The skirmish AI's peak scene (step S 11c-2, ADR 0034 item 10's B0 benchmark: simbench_peak --ai): two AIs at war
    on the Niagara map, each building a base and an army out of a million credits and sending it at the other.

    aiskirm_bench's map, wake and stock AlliedBalanced, twice over: s1 (Soviet_1) from a yard on the player's start
    (the west bank's base yard), s2 (Soviet_2) from one at the east base, enemies both ways from frame 0 (the container
    leaves the Soviet_N players at peace with one another). The player owns nothing. Not a bench check: it is the
    simulator's load at its busiest -- both sides building and fighting -- timed by simbench_peak.run_ai from a snapshot
    taken some minutes in (ai_start).

    Who stands where (probes on Sim(model=False), work/logs/r2_11c2_*probe.log): the other way round (s1 east), the west
    bank wins -- 480 s s2 91 against s1 29, s1 down to 1 by 600 s; this way it stays a fight, 360 s 71 / 61, 480 s 85 /
    68 (buildings and units), some 30 dead a minute. Four sides (two more yards, outpost 1 and carrier home) do not make
    it bigger: 166 alive in all at 420 s, the two on the east bank at each other first (s1 gone by 360 s). What holds
    the size is how fast an AI builds, not the money (a million is not spent) or how many sides -- each side's 70-90
    against the 200-400 B0 asks for is the scene's known shortfall.

    Facts: wake at, money.
    """
    from missions.aiskirm_bench import PERSONALITY, WAKE_AT, ai_map
    import resources
    from maps import niagara
    from parts import Mission, Script

    MONEY = 1_000_000                     # each side's: the simulator's miners gather nothing, so this is all they spend
    ENEMY = (0, 0.0, 'Enemy')
    # side -> (where its yard and base waypoint stand, the waypoint's name)
    BASES = {'s1': ('base yard', 'CNV Peak Base 1'), 's2': ('east base', 'CNV Peak Base 2')}


    def mission(name='CampAIPeak', money=MONEY):
        m = Mission(name=name, map=ai_map(resources.measured(niagara)), facts={'wake at': WAKE_AT, 'money': money})
        players = {side: m.player(side) for side in BASES}
        for side, (site, base) in BASES.items():
            m.sides[side] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': PERSONALITY, 'playerAllies': ''}
            m.put('AlliedConstructionYard', site, 0, 0, side=side, name=f'UNIT - CNV Peak Yard {side[1:]}',
                  role=f'yard {side}')
            m.waypoint(f'base {side}', base, site)
        m.scripts += [
            Script('CNV Peak - Start', [], [*(('PLAYER_SET_MONEY', p, 0) for p in players.values()),
                                            *(('PLAYER_RELATES_PLAYER', a, b, ENEMY) for a in players.values()
                                              for b in players.values() if a != b),
                                            ('SET_MILLISECOND_TIMER', 'CNV Peak Wake', WAKE_AT)]),
            Script('CNV Peak - Wake', [('TIMER_EXPIRED', 'CNV Peak Wake')],
                   [step for side, p in players.items() for step in (
                       ('UNIT_AI_TRANSFER_ALL', p, 1), ('SKIRMISH_AI_MAKE_BASE', p, BASES[side][1]),
                       ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', p, 20), ('SKIRMISH_AI_USE_REPAIRS', p, 0),
                       ('SKIRMISH_AI_USE_REBUILD_SYSTEM', p, 0), ('PLAYER_SET_MONEY', p, money))])]
        return m


    MISSION = {'aipeak': mission}
    return dict(MISSION=MISSION, shared=SimpleNamespace(BASES=BASES))


@cache
def aiplacement_bench():
    """C: isolate the unpack placement search distance with one preplaced power core.

    Prediction (INFERRED): distance 1 cannot fit the expanded footprint; 200 can.
    Only the search distance differs. No automatic production or scripted unpack.

    B (aiplb*): the preplaced core never joined the team (work/re/c_placement_report.md). Guess: only a core the AI
    builds itself is registered UNPACKS_INTO_BUILDING_UNITS. So aiplacej200 without the preplaced core, an opening that
    builds one JapanPowerPlantEgg at the Japan yard, money at the wake, one Distance (600 / 1500, N = 1). Reading
    (work/re/d63_b_fields.md 3): the plant lands (BaseCompactness 0.5 +- 0.05) x Distance from the centre, ~300 / ~750.
    """
    from benches.ai.targets.scenes import aitargetpick_bench
    target_mission = aitargetpick_bench()["shared"].mission
    from benches.ai.tactics.scenes import aiteams_bench
    HOST = aiteams_bench()["shared"].HOST
    host_unit = aiteams_bench()["shared"].host_unit

    MONEY = 10000
    OPENER = (
        '  <SkirmishOpeningMove id="CNVPlOpen" Side="PlayerTemplate:Japan">\n'
        '    <Order Build="JapanPowerPlantEgg" />\n'
        '    <Order Time="90s"/>\n'
        '  </SkirmishOpeningMove>\n'
    )
    OPENING = (
        '    <OpeningMove Name="CNVPlOpen" Weight="100%"><Heuristic><ConstantHeuristic/></Heuristic></OpeningMove>\n'
        '    <BuildState id="AlliedNeededUnits" xai:joinAction="Remove"/>\n'
        '    <BuildState id="AlliedDefenseBuildState" xai:joinAction="Remove"/>\n'
    )


    def mission(distance, japan=False, built=False):
        name = ('CampAIPlB' if built else 'CampAIPlJ' if japan else 'CampAIPlace') + str(distance)
        m = target_mission(name, [('CNVPlacement', None)], (0, 0, 0, 0), tanks=0)
        filename, xml, asset = m.assets[0]
        xml = xml.replace('<AIStrategicStateDefinition ', (
            f"""<AITargetingHeuristic id="CNVPlacement"\n"""
            f"""        HeuristicType="UnpackBuildingPlacement" MinDistanceFromConyardEntrance="0"\n"""
            f"""        IgnoreMinDistanceFromConyardEntranceForTime="15s">\n"""
            f"""      <BuildingPlacementDistance Distance="{distance}"/>\n"""
            f"""    </AITargetingHeuristic>\n"""
            f"""    <AIStrategicStateDefinition """
        ), 1)
        xml = xml.replace('Tactic="SimpleAttack"', 'Tactic="ExactExpansion"')
        xml = xml.replace('MaxUnits="4" IncludeKindOf="CAN_ATTACK"',
                          'MaxUnits="1" RegisteredObjectSet="UNPACKS_INTO_BUILDING_UNITS" '
                          'IncludeKindOf="UNPACKS_INTO_BUILDING"')
        xml = xml.replace('MicroManager="StandardMicroManager_MEDIUM"', 'MicroManager="DefenseMicroManager"')
        if japan:
            # Diagnostic hypothesis: the Allied side excludes preplaced Japan cores.
            xml = xml.replace('    <StrategicState id="CNVStateTP" State=',
                              '    <Side>Japan</Side>\n    <StrategicState id="CNVStateTP" State=')
            m.sides['s1']['playerFaction'] = 'PlayerTemplate:Japan'
            m.find(m.role('ai yard').name).template = 'JapanConstructionYard'
        if built:
            xml = xml.replace('  <AIPersonalityDefinition ', OPENER + '  <AIPersonalityDefinition ', 1)
            xml = xml.replace('    <StrategicState id="CNVStateTP" State=', OPENING + '    <StrategicState id="CNVStateTP" State=')
            # as retail JapanEggUnpacker's state. Bench 11-23, with it and without: the core built at s14.7 stays in the
            # default team, the ExactExpansion team never active (work/re/handoff-b.md, BuildingPlacementDistance)
            xml = xml.replace('id="CNVStateTP" MaxTargets="1">', 'id="CNVStateTP" MaxTargets="1" PathfindingCheckType="None">')
            # the egg is IGNORES_SELECT_ALL, so retail JapanEggUnpacker's team excludes only HARVESTER (work/re/d191)
            xml = xml.replace('ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"', 'ExcludeKindOf="HARVESTER"')
            wake = next(s for s in m.scripts if s.name == 'CNV AI - Wake')
            wake.do = [a if a[0] != 'PLAYER_SET_MONEY' else (a[0], a[1], MONEY) for a in wake.do]
        m.assets[0] = filename, xml, asset
        m.cnv_units = ('JapanPowerPlantEgg',)
        m.spawns |= {'JapanPowerPlantEgg', 'JapanPowerPlant'}
        if not built:
            m.put('JapanPowerPlantEgg', 'east base', -400, 0, side='s1', role='core', name='UNIT - CNV Placement Core')
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
        m.ext = True
        m.facts['placement distance'] = distance
        m.facts['japan host'] = japan
        return m


    MISSION = {'aiplace1': lambda: mission(1), 'aiplace200': lambda: mission(200),
               'aiplacej200': lambda: mission(200, japan=True),
               'aiplb600': lambda: mission(600, japan=True, built=True),
               'aiplb1500': lambda: mission(1500, japan=True, built=True)}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


@cache
def aipower_bench():
    """Engine probe: which protocol a skirmish AI buys with its point (PowerChoice lottery; benches/ai/production/checks.py#engine_aipower;
    simtech.power_choices / Book.ai_buy). The island map and cast of protocol_bench (no units needed); the enemy (s1,
    Soviet) is a computer player with starting point 1 (InitialTechPoints), its personality the probe's:
      aipwra  CNVPowerA: DefaultPersonality's children with ONE PowerChoice, X (PlayerTech_Soviet_MagneticSatellite_Rank_1,
              1 point, needs only PlayerTech_Soviet, which Soviet holds)
      aipwrb  CNVPowerB: two lines, Y (PlayerTech_Soviet_OrbitalRefuse_Rank1, Weight 0%) first, then X (100%)
      aipwrd  the stock DefaultPersonality (no PowerChoice at all): the model says it never buys
      aipwre  CNVPowerE: two lines of equal weight, X (50%) first, then Y (50%) -- which is drawn, does it vary per run
      aipwrf  CNVPowerF: the same two lines, order reversed: Y (50%) first, then X (50%)
      aipwrg  CNVPowerG: X (30%) first, then Y (70%) -- where the draw falls: X iff draw / sum < 0.3
      aipwrh  CNVPowerH: X (10%) first, then Y (90%) -- X iff draw / sum < 0.1
    """
    from benches.script.control.scenes import scripts1_mission
    from parts import Mission

    X = 'PlayerTech_Soviet_MagneticSatellite_Rank_1'
    Y = 'PlayerTech_Soviet_OrbitalRefuse_Rank1'
    BASE = 'DefaultPersonality'


    def personality_xml(pid, lines):
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xai="uri:ea.com:eala:asset:instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
            '  </Includes>',
            f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
            *[f'    <PowerChoice PlayerPower="{p}" Weight="{w}"/>' for p, w in lines],
            '  </AIPersonalityDefinition>',
            '</AssetDeclaration>', ''])


    def mission(name, pid=None, lines=()):
        m = scripts1_mission(name=name)
        m.cnv_power = lines
        if pid:
            m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Soviet', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
            m.assets.append((f'{pid}.xml', personality_xml(pid, lines), f'AIPersonalityDefinition:{pid}'))
        else:
            m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Soviet', 'aiPersonality': f'AIPersonalityDefinition:{BASE}'}
        return m


    MISSION = {
        'aipwra': lambda: mission('CampAIPwrA', 'CNVPowerA', [(X, '100%')]),
        'aipwrb': lambda: mission('CampAIPwrB', 'CNVPowerB', [(Y, '0%'), (X, '100%')]),
        'aipwrd': lambda: mission('CampAIPwrD'),
        'aipwre': lambda: mission('CampAIPwrE', 'CNVPowerE', [(X, '50%'), (Y, '50%')]),
        'aipwrf': lambda: mission('CampAIPwrF', 'CNVPowerF', [(Y, '50%'), (X, '50%')]),
        'aipwrg': lambda: mission('CampAIPwrG', 'CNVPowerG', [(X, '30%'), (Y, '70%')]),
        'aipwrh': lambda: mission('CampAIPwrH', 'CNVPowerH', [(X, '10%'), (Y, '90%')]),
    }
    return dict(MISSION=MISSION, shared=SimpleNamespace(X=X, Y=Y))


def aipowerabove_bench():
    """C: PowerAdvantageHeuristic.Above, fixed four versus eight Guardians.

    Only Above changes in the personality. With identical armies' templates,
    the predicted power ratio is 0.25, below the fixed Value=1.0.
    At s40 Above=true should leave four home; false should send all four.
    Exact evaluation frames, other ratios and defense inclusion remain gap.
    """
    setup = aipoweradv_bench()["shared"]


    def mission(above):
        gate = (f'<PowerAdvantageHeuristic Value="1.0" Above="{str(above).lower()}" '
                'IncludeOwnDefenses="false" IncludeEnemyDefenses="false"/>')
        m = setup.mission('CampAIPAb', 4, 8, gate=gate, expect=int(not above))
        m.name = 'CampAIPAbT' if above else 'CampAIPAbF'
        m.facts.update({'power above': above, 'home at 40': 4 if above else 0})
        return m


    MISSION = {'aipabtrue': lambda: mission(True), 'aipabfalse': lambda: mission(False)}
    return dict(MISSION=MISSION)


@cache
def aipoweradv_bench():
    """Engine probe: PowerAdvantageHeuristic -- does a strategic state turn on by the two armies' kill times (read back by
    benches/ai/production/checks.py#engine_aipoweradv; private ai/states.py PowerAdvantage, simai.Brain.power_advantage)?

    aistate_bench's set-up (Niagara, the enemy s1 Allied with a yard and no money, every inherited strategic state
    removed, woken at 10 s), one state of the probe's own:
      CNVStatePA  PowerAdvantageHeuristic Value="1" Above="true" (no defences either side, KindOf CAN_ATTACK, the
                  defaults): a SimpleAttack team of 2-8 Guardians (AlliedAntiVehicleVehicleTech1) at the closest enemy
                  structure (a player power plant ~750 from them, as aistatenear).
    Program read (work/re l4_states.md 11): theirs = the enemy's time to kill all of ours, ours = ours to kill all of
    theirs (template health, each capped 10000); theirs > 9999 -> Above; else ours > 9999 -> !Above; else
    theirs / ours > Value == Above. Same units both sides: theirs / ours = (ours count / theirs count)^2.
      aipadv2  s1 8 Guardians, the player 4 (on the player's base, idle): 4 > 1 -> on, the tanks go
      aipadv1  s1 4, the player 8: 1/4 -> off, they stay home
      aipadvh  s1 4, the player only an Ore Collector (AlliedMiner, no CAN_ATTACK): nothing to kill us -> on
      aipadvc  aipadv1's armies, the state ConstantHeuristic: the control -- the team goes at all with 4 against 8

    Facts: wake at, ai tanks, player tanks, expect on (1 / 0).
    """
    import resources
    from maps import niagara
    from benches.ai.targets.scenes import aistate_bench
    BASE = aistate_bench()["shared"].BASE
    INHERITED = aistate_bench()["shared"].INHERITED
    from parts import Mission, Script

    WAKE_AT = 10.0
    PID = 'CNVPowerAdv'
    TANK, MINER, DOLPHIN = 'AlliedAntiVehicleVehicleTech1', 'AlliedMiner', 'AlliedAntiNavalScout'


    def personality_xml(pid, gate, min_power=None):
        removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
        mpa = '' if min_power is None else f' MinPowerAdvantage="{min_power}"'
        if gate.startswith('<'):                      # round 83: any heuristic, as written
            when = gate
        else:
            when = ('<PowerAdvantageHeuristic Value="1.0" Above="true" IncludeOwnDefenses="false"'
                    ' IncludeEnemyDefenses="false"/>' if gate == 'power' else '<ConstantHeuristic/>')
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xai="uri:ea.com:eala:asset:instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
            '  </Includes>',
            (
                f"""  <AIStrategicStateDefinition id="CNVStatePA" MaxTargets="1">\n"""
                f"""    <Heuristic>\n"""
                f"""      {when}\n"""
                f"""    </Heuristic>\n"""
                f"""    <TargetHeuristic TargetHeuristic="ClosestStructureHeuristic"/>\n"""
                f"""    <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE" EndIfStateTurnsOff="true">\n"""
                f"""      <TeamTemplate MinUnits="2" MaxUnits="8"{mpa} IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"\n"""
                f"""                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"\n"""
                f"""                    MicroManager="StandardMicroManager_MEDIUM">\n"""
                f"""        <ObjectFilter Rule="ANY">\n"""
                f"""          <IncludeThing>{TANK}</IncludeThing>\n"""
                f"""        </ObjectFilter>\n"""
                f"""      </TeamTemplate>\n"""
                f"""    </Tactic>\n"""
                f"""  </AIStrategicStateDefinition>"""
            ),
            f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
            *removed,
            '    <StrategicState id="CNVStatePA" State="CNVStatePA"/>',
            '  </AIPersonalityDefinition>',
            '</AssetDeclaration>', ''])


    def mission(name, ai, player, miner=False, gate='power', expect=1, min_power=None, home_until=None, out_by=None,
                ai_miner=False, dolphin=False):
        pid = PID + name[len('CampAIPAdv'):]
        facts = {'wake at': WAKE_AT, 'ai tanks': ai, 'player tanks': player, 'expect on': expect}
        if home_until is not None:
            facts['home until'] = home_until
        if out_by is not None:
            facts['out by'] = out_by
        m = Mission(name=name, map=resources.measured(niagara), facts=facts)
        m.draw = 0.6    # the AI's protocol draw (simtech.Book): bench aipval1t bought the cryo satellite (0.6 on it)
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
        m.assets.append((f'{pid}.xml', personality_xml(pid, gate, min_power), f'AIPersonalityDefinition:{pid}'))
        m.cnv_units = (TANK,)
        m.spawns |= {TANK, MINER, DOLPHIN}
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        m.put('AlliedPowerPlant', 'east gate', -300.0, 0.0, name='UNIT - CNV AI Player Target', role='player target')
        for k in range(ai):
            m.put(TANK, 'east base', -200.0 - 80.0 * (k // 4), 160.0 + 70.0 * (k % 4), side='s1', angle=3.1416,
                  name=f'UNIT - CNV AI Tank {k + 1}', role=f'ai guardian {k + 1}')
        for k in range(player):
            m.put(TANK, 'base yard', 300.0 + 80.0 * (k // 4), -120.0 + 70.0 * (k % 4), name=f'UNIT - CNV Player Tank {k + 1}',
                  role=f'player guardian {k + 1}')
        if miner == 'ai base':                       # round 83 EnemyNearby: behind the AI's yard, 350 from its centre
            m.put(MINER, 'east base', 350.0, 0.0, name='UNIT - CNV Player Miner', role='player miner')
        elif miner:
            m.put(MINER, 'base yard', 300.0, 0.0, name='UNIT - CNV Player Miner', role='player miner')
        if dolphin:                                  # the river south of Goat Island (the terrain under water)
            m.put(DOLPHIN, 'goat island', 0.0, -900.0, name='UNIT - CNV Player Dolphin', role='player dolphin')
        if ai_miner:
            m.put(MINER, 'east base', 350.0, 0.0, side='s1', name='UNIT - CNV AI Miner', role='ai miner')
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]
        return m


    MISSION = {
        'aipadv2': lambda: mission('CampAIPAdv2', 8, 4, expect=1),
        'aipadv1': lambda: mission('CampAIPAdv1', 4, 8, expect=0),
        'aipadvh': lambda: mission('CampAIPAdvH', 4, 0, miner=True, expect=1),
        'aipadvc': lambda: mission('CampAIPAdvC', 4, 8, gate='const', expect=1),
        # round 82: the team's MinPowerAdvantage (the state always on). The first guess (the heuristic's ratio: 4 v 8 +
        # 1.0 and 8 v 4 + 5.0 stay home) was wrong on the bench -- all three go as without it; expected now as read.
        'aipadm1': lambda: mission('CampAIPAdvM1', 8, 4, gate='const', expect=1, min_power=1.0),
        'aipadm0': lambda: mission('CampAIPAdvM0', 4, 8, gate='const', expect=1, min_power=1.0),
        'aipadm5': lambda: mission('CampAIPAdvM5', 8, 4, gate='const', expect=1, min_power=5.0),
    }

    # round 83: the condition heuristics (4 Guardians against none; the gate any heuristic). Expected as the program read
    # / the model (private ai/states.py value): 'home until' = all 4 still home that second, 'out by' = fewer by then.
    _OOT = ('<ObjectOfTypeExistsHeuristic PassIfExists="{p}"><ObjectFilter Relationship="{r}" Rule="ANY">'
            '<IncludeThing>AlliedMiner</IncludeThing></ObjectFilter></ObjectOfTypeExistsHeuristic>')
    _OOL = ('<ObjectOfTypeExistsHeuristic PassIfExists="true" Location="{w}"><ObjectFilter Relationship="ENEMIES" '
            'Rule="{r}">{t}</ObjectFilter></ObjectOfTypeExistsHeuristic>')
    HEUR = {
        # TimerHeuristic: on after StartTime from CountFrom (MAP_START default; AI_START = the wake), EndTime a length
        'aihtim': ('Tim', dict(gate='<TimerHeuristic StartTime="30s" EndTime="-1s"/>', home_until=29, out_by=42)),
        'aihtima': ('TimA', dict(gate='<TimerHeuristic StartTime="25s" EndTime="-1s" CountFrom="AI_START"/>',
                                 home_until=34, out_by=47)),
        'aihtimx': ('TimX', dict(gate='<TimerHeuristic StartTime="20s" EndTime="10s"/>', home_until=19, out_by=30)),
        # IntervalHeuristic: off IntervalTime, then on ActiveTime
        'aihint': ('Int', dict(gate='<IntervalHeuristic IntervalTime="25s" ActiveTime="30s"/>', home_until=24,
                               out_by=37)),
        # EnemyNearbyHeuristic: an enemy (the player's Ore Collector: it drives to the ore node 527 off) within Distance
        'aihen1': ('En1', dict(gate='<EnemyNearbyHeuristic Distance="700.0" EnemyNearby="true"/>', miner='ai base')),
        'aihen0': ('En0', dict(gate='<EnemyNearbyHeuristic Distance="700.0" EnemyNearby="true"/>', expect=0)),
        'aihenn': ('Enn', dict(gate='<EnemyNearbyHeuristic Distance="700.0" EnemyNearby="false"/>')),
        # ObjectOfTypeExistsHeuristic with the retail's ObjectFilter Relationship (the model ignores it: own templates)
        'aihoe1': ('Oe1', dict(gate=_OOT.format(p='true', r='ENEMIES'), miner=True)),
        'aihoe0': ('Oe0', dict(gate=_OOT.format(p='true', r='ENEMIES'), expect=0)),
        'aihoef': ('Oef', dict(gate=_OOT.format(p='false', r='ENEMIES'), miner=True, expect=0)),
        'aihoea': ('Oea', dict(gate=_OOT.format(p='true', r='ALLIES'), miner=True, expect=0)),
        'aihoes': ('Oes', dict(gate=_OOT.format(p='true', r='ALLIES'), ai_miner=True)),
        # its Location (Water / Land; read: the terrain under the object below the water level), as the retail's
        # land / water unit build states (ENEMIES Rule ALL: any enemy object; the player's yard stands on land and
        # its target power plant, 'east gate' -300 at the river's east arm, on terrain below the water: aihow goes)
        'aihol': ('Ol', dict(gate=_OOL.format(w='Land', r='ALL', t=''))),
        'aihow': ('Ow', dict(gate=_OOL.format(w='Water', r='ALL', t=''))),
        'aihoww': ('Oww', dict(gate=_OOL.format(w='Water', r='ALL', t=''), dolphin=True)),
        'aihold': ('Old', dict(gate=_OOL.format(w='Land', r='ANY', t=f'<IncludeThing>{DOLPHIN}</IncludeThing>'),
                               dolphin=True, expect=0)),
    }
    for _k, (_tail, _kw) in HEUR.items():
        MISSION[_k] = (lambda tail, kw: lambda: mission('CampAIPAdv' + tail, 4, 0, **kw))(_tail, _kw)
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


def aipowerenemy_bench():
    """C: IncludeEnemyDefenses only, fixed 8:4 Guardians and a powered Spectrum Tower.

    Value=2.0, Above=true; predict off home=0, on home=8 at s40.
    Exact army ratio and other defense categories remain gaps.
    """
    setup = aipoweradv_bench()["shared"]


    def mission(include):
        gate = ('<PowerAdvantageHeuristic Value="2.0" Above="true" '
                f'IncludeOwnDefenses="false" IncludeEnemyDefenses="{str(include).lower()}"/>')
        m = setup.mission('CampAIPEnemy', 8, 4, gate=gate, expect=int(not include))
        m.name = 'CampAIPEnemyOn' if include else 'CampAIPEnOff'
        tower = 'AlliedBaseDefenseAdvanced'
        m.put(tower, 'base yard', 300.0, -200.0, side='p1',
              name='UNIT - CNV Enemy Tower', role='enemy tower')
        m.put('AlliedPowerPlant', 'base yard', 300.0, 200.0, side='p1',
              name='UNIT - CNV Enemy Power', role='enemy power')
        m.spawns |= {tower, 'AlliedPowerPlant'}
        m.facts.update({'home at 40': 8 if include else 0, 'defense template': tower})
        return m


    MISSION = {'aipenoff': lambda: mission(False), 'aipenon': lambda: mission(True)}
    return dict(MISSION=MISSION)


def aipowerown_bench():
    """C: IncludeOwnDefenses only, fixed 4:8 Guardians and a powered Spectrum Tower.

    Value=0.5, Above=true; predict off home=4, on home=0 at s40.
    Exact army ratio and other defense categories remain gaps.
    """
    setup = aipoweradv_bench()["shared"]


    def mission(include):
        gate = ('<PowerAdvantageHeuristic Value="0.5" Above="true" '
                f'IncludeOwnDefenses="{str(include).lower()}" IncludeEnemyDefenses="false"/>')
        m = setup.mission('CampAIPOwn', 4, 8, gate=gate, expect=int(include))
        m.name = 'CampAIPOwnOn' if include else 'CampAIPOwnOff'
        tower = 'AlliedBaseDefenseAdvanced'
        m.put(tower, 'east base', 300.0, -200.0, side='s1',
              name='UNIT - CNV Own Tower', role='own tower')
        m.put('AlliedPowerPlant', 'east base', 300.0, 200.0, side='s1',
              name='UNIT - CNV Own Power', role='own power')
        m.spawns |= {tower, 'AlliedPowerPlant'}
        m.facts.update({'home at 40': 0 if include else 4, 'defense template': tower})
        return m


    MISSION = {'aipownoff': lambda: mission(False), 'aipownon': lambda: mission(True)}
    return dict(MISSION=MISSION)


def aipowervalue_bench():
    """C: PowerAdvantageHeuristic.Value, fixed Above=true and 4:8 Guardians.

    Pre-run s40 home/AI total/player prediction: Value=1.0 gives 4/4/8;
    Value=0.1 gives 0/4/8. Only Value changes in the personality.
    This brackets the predicted ratio 0.25; the exact formula remains gap.
    """
    setup = aipoweradv_bench()["shared"]


    def mission(value, observe=False):
        gate = (f'<PowerAdvantageHeuristic Value="{value}" Above="true" '
                'IncludeOwnDefenses="false" IncludeEnemyDefenses="false"/>')
        home = 4 if value == 1.0 else 0
        m = setup.mission('CampAIPVal', 4, 8, gate=gate, expect=int(not home))
        m.name = 'CampAIPVal1' if home else 'CampAIPVal01'
        m.facts.update({'power value': value, 'home at 40': home})
        if observe:                 # B 11-23: does the AI buy / cast its precision strike here (24e / 1fe / 1ff)?
            from benches.ai.tactics.scenes import aiteams_bench
            host_unit = aiteams_bench()["shared"].host_unit
            HOST = aiteams_bench()["shared"].HOST
            m.units.append(host_unit())
            m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
            m.name, m.ext = m.name + 'T', True
        return m


    MISSION = {'aipval1': lambda: mission(1.0), 'aipval01': lambda: mission(0.1),
               'aipval1t': lambda: mission(1.0, observe=True)}
    return dict(MISSION=MISSION)


@cache
def aisimpleexp_bench():
    """D round 154: Tactic SimpleExpansion -- the AI's miner unpacks into an outpost at an Expansion target.

    C's aiexpc map (benches/ai/production/scenes.py#aiexpansion_bench: two ore fields, the Expansion heuristic picks the east one, bench
    f151 pick 44 at (4173, 2987)) with its state's SimpleAttack swapped for retail AlliedExpansion's tactic
    (SageXML SkirmishAI/States/AlliedBaseStates.xml: Tactic="SimpleExpansion" Distance="200", TeamTemplate MinUnits 1
    MaxUnits 8 ... NEVER_RELEASE, ExpansionMicroManager, CreateUnits AlliedMiner 1 / 1) and one AI-owned AlliedMiner
    placed at the AI's base: the named slot takes a placed unit of its template (model teams.recruit, bench aicr*), so
    the AI needs no money or refinery. The four AI Guardians stay (the template's general fill: escorts).

    Only Distance differs across the three builds (B's Tactic.Distance: what it governs in SimpleExpansion is the
    question): aiexpse = retail 200, aiexpd50 = 50, aiexpd400 = 400. Checks: benches/ai/production/checks.py#engine_aisimpleexp.
    """
    import math
    import re
    import types

    expansion_mission = aiexpansion_bench()["shared"].mission

    MINER = 'AlliedMiner'
    OUTPOST = 'AlliedOutpost'
    PICK = (4173.0, 2987.0)             # bench aiexpc expc f151: pick 44 (the Expansion candidate the team goes to)


    def tactic_xml(distance):
        return (
            f"""<Tactic id="Expand" Tactic="SimpleExpansion" Distance="{distance}">\n"""
            f"""      <TeamTemplate MinUnits="1" MaxUnits="8" MinPowerAdvantage="1.0"\n"""
            f"""                    RegisteredObjectSet="SKIRMISH_AI_NORMAL_COMBAT_UNITS"\n"""
            f"""                    IncludeKindOf="CAN_ATTACK" ExcludeKindOf="AIRCRAFT SIEGE_WEAPON IGNORES_SELECT_ALL HARVESTER"\n"""
            f"""                    AllowedLocomotorTypes="LAND AMPHIBIOUS"\n"""
            f"""                    Priority="STANDARD" ReleaseType="NEVER_RELEASE" AlwaysRecruit="false"\n"""
            f"""                    MicroManager="ExpansionMicroManager">\n"""
            f"""        <CreateUnits UnitName="{MINER}" MinUnits="1" MaxUnits="1"/>\n"""
            f"""      </TeamTemplate>\n"""
            f"""    </Tactic>"""
        )


    def mission(distance=200, placed=True):
        m = expansion_mission(True)
        m.name = {200: 'CampAIExpSE', 50: 'CampAIExpD50', 400: 'CampAIExpD400'}[distance]
        filename, xml, asset = m.assets[0]
        xml, n = re.subn(r'<Tactic id="Attack".*?</Tactic>', tactic_xml(distance), xml, count=1, flags=re.S)
        assert n == 1 and 'SimpleAttack' not in xml
        m.assets[0] = filename, xml, asset
        if placed:
            m.put(MINER, 'east base', -200.0, -150.0, side='s1', angle=3.1416, name='UNIT - CNV AI Miner',
                  role='ai miner')
        m.spawns |= {MINER, OUTPOST}
        m.facts['tactic distance'] = distance
        m.facts['expansion pick'] = PICK
        m.facts['miner'], m.facts['outpost'] = MINER, OUTPOST
        return m


    # D round 155 (d154's H1): the AI builds its miner itself. No placed miner; s1 owns a refinery (it makes the
    # AlliedMiner) by the bluff ore (the map's lint wants a refinery within 250 of a node; the bluff is the candidate
    # the Expansion pick passes over, so its free miner harvests far from the east pick) and a power plant north, gets BUILT_MONEY at the wake and an opener of this probe's
    # own that only deposits BUILT_DEPOSIT to PRODUCTION (aiteamfilter_bench's aiar* opener without its Builds); the
    # build state AlliedNeededUnits (retail's miner top-up) removed, so a miner made comes from the team's CreateUnits.
    BUILT_MONEY, BUILT_DEPOSIT = 10000, 5000
    OPENER = 'CNVSExpOpener'
    PLANT_DY = 400.0


    def built(distance=200, build=False):
        m = mission(distance, placed=False)
        m.name = f'CampAIExp{"B" if build else "H"}{distance}'
        filename, xml, asset = m.assets[0]
        opener = '\n'.join([f'  <SkirmishOpeningMove id="{OPENER}" Side="PlayerTemplate:Allies">',
                            f'    <Order Time="0s" Account="PRODUCTION" Deposit="{BUILT_DEPOSIT}" />',
                            *([f'    <Order Build="{MINER}" />'] if build else []),
                            '    <Order Time="5s"/>', '  </SkirmishOpeningMove>', ''])
        first = '\n'.join([f'    <OpeningMove Name="{OPENER}" Weight="100%">', '      <Heuristic>',
                           '        <ConstantHeuristic/>', '      </Heuristic>', '    </OpeningMove>',
                           '    <BuildState id="AlliedNeededUnits" xai:joinAction="Remove"/>', ''])
        xml, n = re.subn(r'(  <AIPersonalityDefinition [^>]*>\n)', lambda g: opener + g.group(1) + first, xml, count=1)
        assert n == 1
        m.assets[0] = filename, xml, asset
        m.put('AlliedRefinery', 'bluff refinery', side='s1', name='UNIT - CNV AI Refinery', role='ai refinery')
        m.put('AlliedPowerPlant', 'east base', 0.0, PLANT_DY, side='s1', name='UNIT - CNV AI Plant', role='ai plant')
        s1 = m.player('s1')
        wake, = [s for s in m.scripts if s.name == 'CNV AI - Wake']
        wake.do = [(a[0], a[1], BUILT_MONEY) if a[0] == 'PLAYER_SET_MONEY' else a for a in wake.do]
        assert ('PLAYER_SET_MONEY', s1, BUILT_MONEY) in wake.do
        m.facts['ai builds miner'] = True
        m.facts['opener builds miner'] = build
        return m


    # D round 172 (d171's gap): aiexpb50 with node 45 taken away. There the miner's slot (4215, 3039) sits in the gap
    # between node 44 (the pick) and node 45, 150 apart; the bench miner stopped at (4201, 3081), 98 from 44, not at its
    # slot 67. With 44 alone: a stop at the slot says the narrow gap held it off; 98 again says it is node 44 alone.
    GAP_NODE = (4279.0, 3093.0)


    def lone_node():
        m = built(50, build=True)
        m.name = 'CampAIExpB50N'
        cp = types.ModuleType(m.map.__name__)
        cp.__dict__.update({k: v for k, v in vars(m.map).items() if not k.startswith('__')})
        gone = [o for o in cp.OBJECTS
                if o.template == 'OreNode' and math.hypot(o.x - GAP_NODE[0], o.y - GAP_NODE[1]) < 5.0]
        assert len(gone) == 1, gone
        cp.OBJECTS = [o for o in cp.OBJECTS if o is not gone[0]]
        m.map = cp
        m.facts['gap node removed'] = GAP_NODE
        return m


    # D round 156 (d155's H4): the same probe, its opener also orders one AlliedMiner (aiteamfilter_bench's aiar* form)
    # -- is a miner built after the SimpleExpansion team exists taken into it? One build, retail Distance 200.
    MISSION = {'aiexpse': lambda: mission(200), 'aiexpd50': lambda: mission(50), 'aiexpd400': lambda: mission(400),
               'aiexph200': lambda: built(200), 'aiexph50': lambda: built(50), 'aiexph400': lambda: built(400),
               'aiexpb200': lambda: built(200, build=True), 'aiexpb50': lambda: built(50, build=True),
               'aiexpb400': lambda: built(400, build=True), 'aiexpb50n': lambda: lone_node()}
    return dict(MISSION=MISSION, shared=SimpleNamespace(built=built))


def aiskirm_bench():
    """Skirmish AI build registrations. The scene factory also serves the script and economy benches."""

    from missions.aiskirm_bench import (
        AIDATA_RUNS, ARMY_INF, GATHERER_RUN, ARMY_VEH, MT_CONST, MT_TECH, MT_TIMES, UC_CAPS, UMOD_ZERO, mission,
    )


    MISSION = {
        'aiskirm': mission, 'aiskirmc': lambda: mission(observe=True),
        'aiskxn': lambda: mission('CampAISkXN', carrier='name'),   # D 105: the carrier's rename alone
        'aiskxo': lambda: mission('CampAISkXO', carrier='ext'),    # D 105: ra3ext loaded, stock yard, no host
        'aiskirmlow': lambda: mission('CampAISkLow', money=15000),
        'aiskirm20': lambda: mission('CampAISk20', money=20000),    # check d: the first tower's time vs 50000
        'aiskjav': lambda: mission('CampAISkJav', jav=True),
        'aiskirmnl': lambda: mission('CampAISkNoLib', lib=False),
        'aiskexp': lambda: mission('CampAISkExp', expire=12.0),
        'aiskuc': lambda: mission('CampAISkUC', unitcap=UC_CAPS),   # check uc: UnitCap 3 MEDIUM, 1 others
        # D 124 U1: Cap 7 -- do the miners count (the army stops 1-2 lower than with miners left out)?
        'aiskuc7': lambda: mission('CampAISkUC7', unitcap=((7, 'MEDIUM'), (1, 'EASY HARD BRUTAL'))),
        # D 124 U2 (check ucn): aisknew2 + UnitCap 3 MEDIUM -- does the cap hold the build state's unit too?
        'aiskucn': lambda: mission('CampAISkUCN', new=True, unitcap=((3, 'MEDIUM'),)),
        'aiskinb': lambda: mission('CampAISkInB', inert=True),   # check ib: seven inert fields vs aiskirm ib
        'aiskinc': lambda: mission('CampAISkInC', inert2=True),  # check ib: eleven more (round 185) vs aiskirm ib
        'aiskind': lambda: mission('CampAISkInD', inert2='radius'),  # check ib: ResourceNodeSearchRadius 5000 only
        'aiskine': lambda: mission('CampAISkInE', inert2='rest'),    # check ib: the other ten of INERT2
        'aiskinp': lambda: mission('CampAISkInP', inert2='place'),   # check ib: the three RefineryPlacement only
        'aiskins': lambda: mission('CampAISkInS', inert2='seven'),   # check ib: Cleanup, Coop, beacons, emergencies
        'aiskin1': lambda: mission('CampAISkIn1', inert2='start'),   # check rp: StartDistanceDelta 1000 only
        'aiskin0': lambda: mission('CampAISkIn0', inert2='ticks'),   # check rp: ...IncreaseTicksBeforeGivingUp 0 only
        'aiskirmr': lambda: mission('CampAISkIrmR', flip=True),   # check rpx: aiskirm, east nodes facing pi (F2)
        'aiskin0r': lambda: mission('CampAISkIn0R', inert2='ticks', flip=True),   # rpx / rpb: aiskin0 the same (F1)
        # rpx (B192, D138 1): StartDistanceDelta -40 / -20 (retail -30) -- where the ring 4 / ring 5 line moves.
        # bench 2026-11-14 (both PASS): -40 first s49 x27 y10 (node A ring 6 or 7 at k -2), second +28 +11;
        # -20 first s49 x26 y9 (ring 5, k -3), second +28 +12. The simulator (60 x 45 boxes): x26 y10 both.
        'aiskst40': lambda: mission('CampAISkSt40', inert2=(('RefineryPlacementStartDistanceDelta', '-40.0'),)),
        'aiskst20': lambda: mission('CampAISkSt20', inert2=(('RefineryPlacementStartDistanceDelta', '-20.0'),)),
        'aiskmod': lambda: mission('CampAISkMod', umod=UMOD_ZERO),     # check q: SecondsTillTargetsExpire 12, not 5   # s1 without the container's Lib_Skirmish_Setup
        'aiskacp': lambda: mission('CampAISkAcP', account='PRODUCTION'),    # check v: the rebuilt AI, retail Account
        'aiskacd': lambda: mission('CampAISkAcD', account='DEFENSE'),
        'aiskpw0': lambda: mission('CampAISkPw0', buffer=0),       # check x: DesiredExcessPowerBuffer 0 (retail 100)
        'aiskpw3': lambda: mission('CampAISkPw300', buffer=300),   # check x: 300
        'aisknew': lambda: mission('CampAISkNew', new=False),      # check y: a barracks of s1's builds our unit too
        'aisknew2': lambda: mission('CampAISkNew2', new=True),     # check y: + a build state listing it
        'aiskcap': lambda: mission('CampAISkCap', new=True, cap=2),   # check y: + SpecificUnitCap 2 on it
        'aiskblkn': lambda: mission('CampAISkBlkN', new=True, block='near'),    # check y: blocker 120 away
        'aiskblkf': lambda: mission('CampAISkBlkF', new=True, block='far'),     # check y: 400 away
        'aiskblkr': lambda: mission('CampAISkBlkR', new=True, block='radius'),  # check y: a plant at 190
        'aiskoff': lambda: mission('CampAISkOff', new=True, off=True),   # check y: the state's heuristic 0
        'aiskcu': lambda: mission('CampAISkCU', new=True, dear='cu'),   # check yc: + a 100000-cost unit, filter retail
        'aiskcs': lambda: mission('CampAISkCS', new=True, dear='cs'),   # check yc: + the filter counts it as structure
        'aiskcu3': lambda: mission('CampAISkCU3', new=True, dear='cu', dear_cost=30000),   # check ycm: cu at 30000
        'aiskpt': lambda: mission('CampAISkPt', ptype=True),      # check pt: PersonalityType != id
        'aiskpti': lambda: mission('CampAISkPtI', ptype=False),   # check pt: PersonalityType not written
        'aisksd1': lambda: mission('CampAISkSd1', side=False),    # check sd: Side Soviet, Japan s1, gate closed
        'aisksd2': lambda: mission('CampAISkSd2', side=True),     # check sd: the same, SkirmishPersonality true
        'aisksd4': lambda: mission('CampAISkSd4', side='none'),   # check sd: s1 without an aiPersonality
        'aiskmt': lambda: mission('CampAISkMT', mintime=MT_TIMES['aiskmt']),      # check mt: MinTime 150 Force 151
        'aiskmto': lambda: mission('CampAISkMTO', mintime=MT_TIMES['aiskmto']),   # check mt: MinTime 250 Force 151
        'aiskmt0': lambda: mission('CampAISkMT0', mintime=(0, 1)),   # check mt: TECH 0/1, 6 plants (D82 G1 + G2)
        'aiskmt03': lambda: mission('CampAISkMT03', mintime=(0, 1), power_more=False),   # mt: TECH 0/1, 3 plants
        'aiskmt2': lambda: mission('CampAISkMT2', mintime=(200, 201), power_more=True),  # mt: TECH 200/201, 6
        'aiskmt20': lambda: mission('CampAISkMT20', mintime=(20, 22), power_more=True, mt_secs=600.0),  # 20/22
        # (20 / 21 compiled a map stream whose hash began d1 fb: the game took it for RefPack and crashed)
        'aiskmt14': lambda: mission('CampAISkMT14', mintime=(140, 142), power_more=True, mt_secs=600.0),
        'aiskmt16': lambda: mission('CampAISkMT16', mintime=(160, 162), power_more=True, mt_secs=600.0),
        'aiskmt15': lambda: mission('CampAISkMT15', mintime=(150, 152), power_more=True, mt_secs=600.0),  # G2e
        'aiskmt40': lambda: mission('CampAISkMT40', mintime=(400, 402), power_more=True, mt_secs=780.0),  # G2e
        # aiskmt40 with BuildTechMinPowerAdvantage 1000 (retail 1.25): does the f5857 tech building still come?
        'aiskmtp': lambda: mission('CampAISkMTP', mintime=(400, 402), power_more=True, mt_secs=780.0,
                                   power_adv=1000),
        'aiskmt99': lambda: mission('CampAISkMT99', mintime=(1000, 1002), power_more=True, mt_secs=780.0),
        'aiskmtc': lambda: mission('CampAISkMTC', mintime=(None, None)),          # check mt: CONSTANT 300 tower
        'aiskmtt': lambda: mission('CampAISkMTT', mintime=(200, 201, MT_CONST[0])),   # check mt: TECH 200/201 tower
        'aiskmtk': lambda: mission('CampAISkMTK', mintime=(None, None, MT_TECH, MT_TECH)),   # mt: CONSTANT 300 tech
        'aiskmtl': lambda: mission('CampAISkMTL', mintime=(None, None, MT_TECH, MT_TECH, 200)),   # mt: CONST 200 tech
        'aiskrand': lambda: mission('CampAISkRand', two='rand'),   # check s: RANDOM_UNIT 0%-30% / bare 30-100
        'aiskdiff': lambda: mission('CampAISkDiff', two='diff'),   # check s: a HARD-only state at MEDIUM
        'aiskvinf': lambda: mission('CampAISkVInf', army=ARMY_INF),   # check z: the player owns 10 conscripts
        'aiskvveh': lambda: mission('CampAISkVVeh', army=ARMY_VEH),   # check z: 10 Hammer tanks
        # UnitBuilderOverallDefensivePreference A/B on the aiskvveh layout. Model: BEST_UNIT_EXPECTED scores the
        # candidate's expected efficiency, linear in this preference, so 1000% ranks the barracks' candidates like the
        # stock 25% (aiskvveh bench 2026-11-11: Javelin 1 at s29 .. 14 by s185, Peacekeeper 0) -> Javelins only again;
        # 0% scores every BEST_UNIT_EXPECTED entry 0, the build states order nothing, the barracks gets only the unit
        # builder's uniform draws -> Peacekeepers appear, far fewer Javelins.
        'aiskvd0': lambda: mission('CampAISkVD0', army=ARMY_VEH, defpref='0%'),
        'aiskvd9': lambda: mission('CampAISkVD9', army=ARMY_VEH, defpref='1000%'),
        # CanBuildInAlliedBuildRadii false / true under a friendly yard (check rpb): l4_allied_radii H1 / H2
        'acbr0': lambda: mission('CampAIAcbr0', allied=False),
        'acbr1': lambda: mission('CampAIAcbr1', allied=True),
        'aiskad': lambda: mission('CampAISkAD', aidata=AIDATA_RUNS['aiskad']),      # check a: AIData canary
        'aiskfon': lambda: mission('CampAISkFOn', aidata=AIDATA_RUNS['aiskfon']),   # check fm: UseFormations true
        'aiskfof': lambda: mission('CampAISkFOff', aidata=AIDATA_RUNS['aiskfof']),  # check fm: false
        'aiskna': lambda: mission('CampAISkNA', aidata=AIDATA_RUNS['aiskna']),      # check fm: nine unread fields
        'aiskmrd': lambda: mission('CampAISkMRD', aidata=AIDATA_RUNS['aiskmrd']),   # check fm: MaxRecruitDistance 1
        'aiskts': lambda: mission('CampAISkTS', aidata=AIDATA_RUNS['aiskts']),      # check fm: TeamSeconds 600
        'aiskgf': lambda: mission('CampAISkGF', aidata=AIDATA_RUNS['aiskgf']),      # check fm: GroupFudge 200
        'aiskga': lambda: mission('CampAISkGA', armydef=GATHERER_RUN),              # check fm: Gatherer canary
    }

    def teams_logged(name, run):
        from benches.ai.tactics.scenes import aiteams_bench
        shared = aiteams_bench()['shared']
        m = mission(name, aidata=AIDATA_RUNS[run])
        m.ext = True
        m.units.append(shared.host_unit())
        m.put(shared.HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
        return m

    MISSION['aiskn1'] = lambda: teams_logged('CampAISkN1', 'aiskn1')      # check fm: NumTeamsToRecruit 1
    MISSION['aiskn10'] = lambda: teams_logged('CampAISkN10', 'aiskn10')   # check fm: 10, the same host
    return dict(MISSION=MISSION)


def aislush_bench():
    """SLUSH_FUND share isolation, using aiom13's two-plant opening.

    Only the budget allocation changes: slush 100 / production 0 versus the reverse.
    INFERRED prediction: the opening spends SLUSH_FUND, hence two plants versus none
    at s40. No deposits, income, combat teams or defense production are introduced.
    Original readings and ownership: work/re/c_slush_report.md.
    """
    ALL = aiomove_bench()["shared"].ALL
    opening_mission = aiomove_bench()["shared"].mission
    RICH = aitower_bench()["shared"].RICH
    RICH_WATCH = aitower_bench()["shared"].RICH_WATCH
    tower_mission = aitower_bench()["shared"].mission


    def mission(slush):
        m = opening_mission('CampAISlush' + ('S' if slush else 'P'),
                            [('CNVOpenPPT30', '100%', ALL)], 2 if slush else 0, 0)
        name, xml, ref = m.assets[0]
        budget = (
            f"""  <AIBudgetStateDefinition id="CNVSlushBudget">\n"""
            f"""    <Heuristic><ConstantHeuristic/></Heuristic>\n"""
            f"""    <Budget>\n"""
            f"""      <AccountShare Account="PRODUCTION" Percent="{0 if slush else 100}%"/>\n"""
            f"""      <AccountShare Account="DEFENSE" Percent="0%"/>\n"""
            f"""      <AccountShare Account="SLUSH_FUND" Percent="{100 if slush else 0}%"/>\n"""
            f"""    </Budget>\n"""
            f"""  </AIBudgetStateDefinition>\n"""
        )
        xml = xml.replace('  <AIPersonalityDefinition', budget + '  <AIPersonalityDefinition')
        removed = '\n'.join(f'    <BudgetState id="{key}" xai:joinAction="Remove"/>'
                            for key in ('CoopBudget', 'DefenseBudget', 'HeavyDefenseBudget', 'OpeningMoveBudget'))
        xml = xml.replace('  </AIPersonalityDefinition>', removed +
                          '\n    <BudgetState id="CNVSlushBudget" State="CNVSlushBudget"/>\n'
                          '  </AIPersonalityDefinition>')
        m.assets[0] = name, xml, ref
        return m


    def defense(slush):
        """Round two: funded refinery, no opening, only the defense build state.

        Prediction: SLUSH_FUND 100% buys no turret; DEFENSE 100% buys at least one.
        The positive control distinguishes an idle host from account separation.
        """
        m = tower_mission('CampAISl' + ('SDef' if slush else 'DDef'), 0.5,
                          opener=False, refinery=True, defense=100, watch=65)
        name, xml, ref = m.assets[0]
        if slush:
            xml = xml.replace('Account="DEFENSE" Percent="100%"', 'Account="DEFENSE" Percent="0%"')
            xml = xml.replace('Account="SLUSH_FUND" Percent="0%"', 'Account="SLUSH_FUND" Percent="100%"')
        m.assets[0] = name, xml, ref
        m.facts['slush only'] = slush
        return m


    def rich():
        """Round three (B): aitowerinc10r (PRODUCTION 90 / DEFENSE 10, 20000 at the wake: two turrets, no third) plus
        SLUSH_FUND 100 %. Read (work/re d64 2): the shares sum only the other accounts' lines, SLUSH_FUND takes what they
        leave -- its own line is ignored, DEFENSE stays 10 %: two turrets. Counted (200 %, each halved): 5 %, one."""
        m = tower_mission('CampAISlRich', 0.5, opener=False, refinery=True, defense=10, watch=RICH_WATCH, money=RICH)
        name, xml, ref = m.assets[0]
        m.assets[0] = name, xml.replace('Account="SLUSH_FUND" Percent="0%"', 'Account="SLUSH_FUND" Percent="100%"'), ref
        return m


    MISSION = {'aislush100': lambda: mission(True), 'aislush0': lambda: mission(False),
               'aislsdef': lambda: defense(True), 'aislddef': lambda: defense(False), 'aislrich': rich}
    return dict(MISSION=MISSION)


def aistep_bench():
    """敌方AI 分档 on the bench (plan.py compile_ai): ai_plan_bench's plan (Niagara, the Allied AI on a construction yard
    at the east base, lots of money) with its IFVs held back -- let go STEP after it woke. Read back by checks/aistep.py.
    The IFV, not the guardian tank: bench 2026-10-27, this AI built four IFVs (the first ~135 s after waking, the last
    ~180 s) and never a guardian, held back or not, even with a liking for them (aistep_free).

    Facts: wake at, step (seconds after waking the IFVs are let go), watch.
    """
    import plan
    ap = ai_plan_bench()["shared"]

    STEP, WATCH = 150.0, 300.0                      # let go after the control (aistep_free) had its first IFV
    HELD = '多功能步兵车'


    def mission(name='CampStep', held=True):
        """held=False: the control -- nothing held back."""
        d = dict(ap.PLAN, 关卡='as')
        d['敌方AI'] = dict(ap.PLAN['敌方AI'])
        if held:
            d['敌方AI']['分档'] = [{'当': f'敌方AI 醒来 + {STEP:g}', '放开': [HELD]}]
        m = plan.Compiler(d, name).compile()
        m.facts.update({'wake at': ap.WAKE_AT, 'step': STEP, 'watch': WATCH})
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'aistep': lambda: mission(),
        'aistep_free': lambda: mission(held=False),
    }
    return dict(MISSION=MISSION)


def aitechshare_bench():
    """C: initial tech ownership below/above retail's 75% fair-share gate.

    Retail Allied/Japan/SovietBaseStates use 75%, 100%, 125%, Above=false.
    Four OilDerricks (one map-neutral, three placed here). C's first prediction (two active players: 50 / 100 %) read
    4/0/4 on both; B 11-25 (SWEEP, aitechsn): every owner's derricks over 4, x the map's 7 declared players + 1 = 8 --
    own=1 -> 200 %, own=2 -> 400 %. Three independent states each; equality and a zero total are gaps.
    """
    import math
    import types

    from benches.ai.targets.scenes import aistate_bench
    setup = aistate_bench()["shared"]


    SWEEP = ((180, False), (375, False), (1000, False))


    def mission(high, gates=((75, False), (75, True), (125, False)), name=None, others='p1'):
        """gates: the three states' (PercentOfFairShare, Above). B 11-25 SWEEP (aitechsl / aitechsh): all Above=false at
        180 / 375 / 1000 %, a state on (units away, home 0) iff share < its percent -- C's two runs read share >= 125 % for
        both; the sweep tells 7 map players x 1/4, 2/4 (175 / 350 %) from a total of the one neutral derrick (200 / 400 %)
        and from a divide by zero (none on). others: the side of the placed derricks not ours (aitechsn: neutral --
        a total of neutral ones only 1/3 x 2 = 67 %, 8 players x 1/4 still 200 %). work/re/b1125_techshare.md."""
        m = setup.mission(name or ('CampAITechH' if high else 'CampAITechL'), near=True)
        filename, xml, asset = m.assets[0]
        units = (setup.INF, setup.TANK, 'SovietAntiGroundAircraft')
        states = []
        for i, (unit, (percent, above)) in enumerate(zip(units, gates)):
            sid = f'CNVTechShare{i}'
            state = setup._state(sid, '', unit, gate='const')
            state = state.replace('<ConstantHeuristic/>',
                f'<TechBuildingShareHeuristic PercentOfFairShare="{percent}%" Above="{str(above).lower()}"/>')
            state = state.replace('ClosestStructureHeuristic', 'CNVTechTarget')
            state = state.replace('LAND AMPHIBIOUS', 'LAND AMPHIBIOUS AIR')
            states.append(state)
        start = xml.index('  <AIStrategicStateDefinition ')
        end = xml.index('  <AIPersonalityDefinition ')
        target = ('  <AITargetingHeuristic id="CNVTechTarget" HeuristicType="EnemyStructure" '
                  'SortType="Distance" VitalKindOf="FS_POWER" RequireUniqueTarget="false"/>\n')
        xml = xml[:start] + target + '\n'.join(states) + '\n' + xml[end:]
        xml = xml.replace('    <StrategicState id="CNVStateInf" State="CNVStateInf"/>\n'
                          '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>',
                          '\n'.join(f'    <StrategicState id="CNVTechShare{i}" State="CNVTechShare{i}"/>'
                                    for i in range(3)))
        m.assets[0] = filename, xml, asset
        for k in range(4):
            m.put(units[2], 'east base', 100, -100 + 70*k, side='s1',
                  name=f'UNIT - Tech Heli {k}', role=f'tech heli {k}')
        m.cnv_units = units
        m.spawns.update((*units, 'OilDerrick'))
        # The fourth derrick is already in map.OBJECTS, neutral and unchanged.
        for k, site in enumerate(('outpost 1', 'outpost 2', 'outpost 3')):
            m.put('OilDerrick', site, side='s1' if k < (2 if high else 1) else others,
                  name=f'UNIT - Tech Oil {k}')
        # Initial map resources, not a scripted capture or a camp emplacement.
        # A local map copy also keeps the shared measured map unchanged.
        layout = types.ModuleType(m.map.__name__)
        layout.__dict__.update(vars(m.map))
        layout.OBJECTS = list(m.map.OBJECTS) + m.objects[-3:]
        layout.SCENERY = [o for o in m.map.SCENERY if all(
            math.dist((o.x, o.y), (d.x, d.y)) >= 250 for d in m.objects[-3:])]
        m.objects = m.objects[:-3]
        m.map = layout
        m.facts.update({'tech own': 2 if high else 1, 'tech total': 4})
        m.cnv_tech_home = tuple(4 * (100 * m.facts['tech own'] / 4 * 8 >= p) ^ (4 * a) for p, a in gates)  # B 11-25
        return m


    MISSION = {'aitechlow': lambda: mission(False), 'aitechhigh': lambda: mission(True),
               'aitechsl': lambda: mission(False, SWEEP, 'CampAITechSL'), 'aitechsh': lambda: mission(True, SWEEP, 'CampAITechSH'),
               'aitechsn': lambda: mission(False, ((60, False), (180, False), (375, False)), 'CampAITechSN', 'neutral')}
    return dict(MISSION=MISSION)


@cache
def aitower_bench():
    """Engine probe: where a skirmish AI puts a base defence tower (read back by benches/ai/production/checks.py#engine_aitower; engine line A,
    layer 4 block 5, RA3-EngineModel ra3model/ai/defense.py tower_site / tower_centre / tower_spots).

    The enemy (s1, Allied) runs a personality of this probe's own: the Allied co-op base with every inherited strategic
    state removed (as benches/ai/targets/scenes.py#aitarget_bench), the build state AlliedNeededUnits removed (only AlliedDefenseBuildState is
    left: Multigunner turrets), the four inherited budget states removed and one of its own, always on (ConstantHeuristic),
    PRODUCTION 50% / DEFENSE 50% (which account pays for a tower is not read -- either share buys one at the wake money).
    Its BaseCompactness is the build's.
      AI     the yard on the east base, a power plant 450 south of it (the AI building nearest the enemy)
      enemy  the player's power plant 1250 south of the yard (800 south of the AI's plant: the nearest enemy to both), the
             player's yard on the west bank ~2700 away
    Read (l4_defense2.md 2.1-2.3): the tower's centre is the AI building nearest an enemy (the plant, not the yard), the
    first angle points from the base centre to its nearest enemy (south), the radius is (BaseCompactness +- 0.05) x 500.
    So the first tower should stand south of the AI plant, 250 / 375 / 475-500 from it for 0.5 / 0.75 / 1.0.
    Builds: aitower50 (0.5, the Allied co-op default), aitower75, aitower100 -- these build the turret by an opening move
    (a deposit of 1000 to PRODUCTION, then AlliedBaseDefense; retail budgets kept): the build state alone built nothing in
    70 s (aitowerstate: the own budget above, no opener). aitowerfoe (round 71): as aitowerstate, plus FOES of the
    player's Guardian tanks (HOLD_FIRE) 600 south of the AI plant -- does the build state (BEST_UNIT_EXPECTED) build once
    there is an enemy army, and round which building (the opener's turret stood round the yard). aitowerdep: as
    aitowerfoe, but an opener that only deposits 1000 to DEFENSE (no Build order; retail budgets kept) -- is the script's
    money just never in the accounts? Round 133 (handoff-b section 125's table): aitowerinc -- as aitowerstate, plus an
    AI refinery on the east ore and a miner (does a share need income?); aitoweropen -- as aitowerstate, plus an opener
    of one empty Time 0s order, own budget kept (does a share fund nothing before an opening is done?). Round 135
    (handoff-b section 137's table): aitowerinc10 -- as aitowerinc, but DEFENSE 10% / PRODUCTION 90% (does the share
    borrow against its income -- a turret soon after the wake -- or wait for 10% of the money to reach 800?). Readings in
    benches/ai/production/checks.py#engine_aitower.
    Facts: wake at, money.
    """
    import resources
    from maps import niagara
    from benches.ai.targets.scenes import aistate_bench
    ab = aistate_bench()["shared"]
    from parts import Mission, Script

    WAKE_AT = 10.0
    MONEY = 1700                                # 2 x 800 + 100: a tower from either account at 50%
    PID = 'CNVTowerTest'
    TURRET = 'AlliedBaseDefense'
    PLANT = 'AlliedPowerPlant'
    YARD_AT = (3850.0, 3400.0)                  # niagara 'east base'
    AI_PLANT_DY = -450.0
    ENEMY_DY = -1250.0
    BUDGETS = ('CoopBudget', 'DefenseBudget', 'HeavyDefenseBudget', 'OpeningMoveBudget')
    BUDGET_ID = 'CNVTowerBudget'
    OPENER = 'CNVTowerOpener'
    OPENER_DEPOSIT = 1000
    FOE = 'AlliedAntiVehicleVehicleTech1'       # Guardian tank
    FOES = 4
    FOE_DY = AI_PLANT_DY - 600.0                # 600 south of the AI plant (1050 from the yard)
    HOLD_FIRE = 3
    RICH, RICH_WATCH = 20000, 150.0             # aitowerinc10r: the bank 20000 at the wake
    CHEAT_WATCH = 90.0                          # aicheat*: ~7 miner trips after the wake
    CHEAT = {'aicheat2': (('200%', 'MEDIUM'),),
             'aicheat1': (('300%', 'EASY HARD BRUTAL'), ('100%', 'MEDIUM'))}


    INC10_WATCH = 420.0                         # aitowerinc10 (DEFENSE 10%): long enough for a second turret
    # B round 178 (work/re d122_ai_rules.md 1, R1-R3): two budget states of the probe's own, in this list order:
    # (id, heuristic, DEFENSE %); heuristic = a ConstantHeuristic Weight, or 'opening' (OpeningMoveHeuristic
    # Complete=false: holds until the opening is done). DEFENSE 100 % buys turrets with the bank; PRODUCTION 100 % buys
    # nothing (no unit build state left), so a turret says which state runs.
    BS_DEF, BS_PROD = 'CNVBsDef', 'CNVBsProd'
    BSETS = {'aibsmax': ((BS_DEF, '0.4', 100), (BS_PROD, '0.6', 0)),      # R1: the larger, though second -> 0 turrets
             'aibstie': ((BS_DEF, '0.5', 100), (BS_PROD, '0.5', 0)),      # R2: a tie -> the earlier -> turrets
             'aibszero': ((BS_DEF, '0', 100), (BS_PROD, 'opening', 0)),   # R3: PROD until the opening ends, then all 0
             # BudgetState.Difficulty: as aibsmax, the heavier line for every difficulty but the bench's MEDIUM
             'aibsdiff': ((BS_DEF, '0.4', 100), (BS_PROD, '0.6', 0, 'EASY HARD BRUTAL'))}
    ZERO_OPENING = 40.0                         # aibszero: the opener's one Time order, 40 s after the wake
    # B round 184 (d122 R4): the retail budgets (OpeningMoveBudget, Coop 85/5/10, Defense 80/20 when an enemy worth >= 1000
    # is within 700 of the base, Heavy 65/35 within 400 and >= 2500), an opening done at once, 5000 at the wake: Coop's
    # DEFENSE 5 % (250) buys no turret. RAID_IN s after the wake RAID_N Guardians (the player's, HOLD_FIRE) appear 650
    # west of the yard (790 from the AI plant: inside 700 of the yard only, never inside 400); RAID_OUT they are deleted;
    # RAID_GIVE the AI is given 5000 more: back on Coop (5 %) it buys no second turret, still on Defense (20 %) it would.
    RAID_IN, RAID_OUT, RAID_GIVE, RAID_WATCH = 20.0, 50.0, 65.0, 110.0
    RAID_N, RAID_DX, RAID_MONEY = 4, -650.0, 5000


    def _budget(defense=50, bid=BUDGET_ID, heuristic=None):
        if heuristic == 'opening':
            h = '<OpeningMoveHeuristic Complete="false"/>'
        else:
            h = '<ConstantHeuristic/>' if heuristic is None else f'<ConstantHeuristic Weight="{heuristic}"/>'
        return (
            f"""  <AIBudgetStateDefinition id="{bid}">\n"""
            f"""    <Heuristic>\n"""
            f"""      {h}\n"""
            f"""    </Heuristic>\n"""
            f"""    <Budget>\n"""
            f"""      <AccountShare Account="PRODUCTION" Percent="{100 - defense}%"/>\n"""
            f"""      <AccountShare Account="DEFENSE" Percent="{defense}%"/>\n"""
            f"""      <AccountShare Account="SLUSH_FUND" Percent="0%"/>\n"""
            f"""    </Budget>\n"""
            f"""  </AIBudgetStateDefinition>"""
        )


    def _opener(build=True, empty=False, wait=0):
        # as retail AIOpener_A08_AlliedSpecialForces: a deposit, then the build; the trailing Time order ends the opening.
        # build=False: the deposit only, to DEFENSE (the build state spends it, if it builds at all)
        # empty=True: one Time 0s order and nothing else -- an opening that is done at once
        account = 'PRODUCTION' if build else 'DEFENSE'
        order = [f'    <Order Build="{TURRET}" />'] if build else []
        # wait (aibszero): the empty opener's one Time order -- the opening is done that many seconds after the wake
        body = ([f'    <Order Time="{wait:g}s"/>'] if empty else
                [f'    <Order Time="0s" Account="{account}" Deposit="{OPENER_DEPOSIT}" />', *order, '    <Order Time="90s"/>'])
        return '\n'.join([f'  <SkirmishOpeningMove id="{OPENER}" Side="PlayerTemplate:Allies">', *body,
                          '  </SkirmishOpeningMove>'])


    def personality_xml(compactness, opener=False, build=True, empty=False, defense=50, cheat=(), state=BUDGET_ID,
                        bsets=(), wait=0):
        # bsets (aibs*): ((id, heuristic, DEFENSE %), ...) -- several own budget states, their BudgetState lines in order
        # empty=True: the empty opener (_opener) with this probe's own budget, not the retail ones
        # cheat: ((Percentage, Difficulty), ...) -- the personality's own ResourceMultiplierCheat lines (aicheat*)
        removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in ab.INHERITED]
        removed += ['    <BuildState id="AlliedNeededUnits" xai:joinAction="Remove"/>']
        first = [f'    <OpeningMove Name="{OPENER}" Weight="100%">', '      <Heuristic>',
                 '        <ConstantHeuristic/>', '      </Heuristic>', '    </OpeningMove>'] if opener or empty else []
        if opener:                              # retail budgets kept; the opening move first (as 1AlliedBalanced's)
            own, budget = [], []
        else:
            removed += [f'    <BudgetState id="{k}" xai:joinAction="Remove"/>' for k in BUDGETS]
            # state (aibsprod): the line's State names another budget definition than the own one (still declared)
            own, budget = [_budget(defense)], [f'    <BudgetState id="{BUDGET_ID}" State="{state}"/>']
            if bsets:
                own = [_budget(d, b, h) for b, h, d, *_ in bsets]
                budget = [f'    <BudgetState id="{b}" State="{b}"' + ''.join(f' Difficulty="{x}"' for x in diff) + '/>'
                          for b, _, _, *diff in bsets]
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xai="uri:ea.com:eala:asset:instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml" />',
            '  </Includes>',
            *own,
            *([_opener(build, empty, wait)] if opener or empty else []),
            f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{ab.BASE}"'
            f' BaseCompactness="{compactness}">',
            *first,
            *removed,
            *budget,
            *[f'    <ResourceMultiplierCheat Percentage="{p}" Difficulty="{d}"/>' for p, d in cheat],
            '  </AIPersonalityDefinition>',
            '</AssetDeclaration>', ''])


    def mission(name, compactness, opener=True, foes=0, build=True, empty=False, refinery=False, defense=50,
                watch=None, money=MONEY, cheat=(), state=BUDGET_ID, bsets=(), wait=0, raid=False):
        facts = {'wake at': WAKE_AT, 'money': money}
        if raid:                                # aibsback (engine_aitower r4): the raid's times after the wake
            facts.update({'raid in': RAID_IN, 'raid out': RAID_OUT, 'raid give': RAID_GIVE})
        if wait:
            facts['opening'] = wait             # engine_aitower i: the opening is done this long after the wake
        if watch:
            facts['watch'] = watch              # how long benches/ai/production/checks.py#engine_aitower e watches after the wake
        m = Mission(name=name, map=resources.measured(niagara), facts=facts)
        m.cnv_compactness = compactness         # the check says the model's radius by it
        m.cnv_turret = TURRET                   # what the check counts (checks ask the mission, not this module)
        # the income multiplier predicted at the bench's MEDIUM: the MEDIUM line's Percentage (engine_aitower g)
        m.cnv_state = state                     # engine_aitower h: which budget definition the one BudgetState names
        m.cnv_bsets = bsets                     # engine_aitower i: the budget states, in list order
        m.cnv_cheat = next((float(p.rstrip('%')) / 100 for p, d in cheat if 'MEDIUM' in d.split()), 1.0)
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
        m.assets.append((f'{PID}.xml', personality_xml(compactness, opener, build, empty, defense, cheat, state,
                                                       bsets, wait),
                          f'AIPersonalityDefinition:{PID}'))
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put(PLANT, 'east base', 0.0, AI_PLANT_DY, side='s1', name='UNIT - CNV AI Plant', role='ai plant')
        m.put(PLANT, 'east base', 0.0, ENEMY_DY, name='UNIT - CNV AI Enemy Plant', role='enemy plant')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        m.spawns |= {TURRET}
        if refinery:                            # income: the AI's refinery on the east ore and a miner by it
            m.put('AlliedRefinery', 'east refinery', side='s1', name='UNIT - CNV AI Refinery', role='ai refinery')
            m.put('AlliedMiner', 'east refinery', -150.0, 150.0, side='s1', name='UNIT - CNV AI Miner', role='ai miner')
        base = 'CNV AI Base'
        foe = [f'UNIT - CNV AI Foe {k}' for k in range(foes)]
        for k, n in enumerate(foe):
            m.put(FOE, 'east base', 60.0 * k - 30.0 * (foes - 1), FOE_DY, name=n, role=f'foe {k}')
        m.waypoint('ai base', base, 'east base')
        if raid:                                # aibsback: the raid comes and goes by script, the AI is given more
            raiders = [f'UNIT - CNV AI Raid {k}' for k in range(RAID_N)]
            for k in range(RAID_N):
                m.waypoint(f'raid {k}', f'CNV AI Raid {k}', 'east base', RAID_DX, 60.0 * k - 30.0 * (RAID_N - 1))
            m.spawns.add(FOE)
            m.scripts += [
                Script('CNV AI - Raid timers', [('TIMER_EXPIRED', 'CNV AI Wake')],
                       [('SET_MILLISECOND_TIMER', 'CNV AI Raid In', RAID_IN),
                        ('SET_MILLISECOND_TIMER', 'CNV AI Raid Out', RAID_OUT),
                        ('SET_MILLISECOND_TIMER', 'CNV AI Raid Give', RAID_GIVE)]),
                Script('CNV AI - Raid in', [('TIMER_EXPIRED', 'CNV AI Raid In')],
                       [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', n, FOE, m.team('p1'), m.mark(f'raid {k}'))
                        for k, n in enumerate(raiders)] + [('UNIT_SET_STANCE', n, HOLD_FIRE) for n in raiders]),
                Script('CNV AI - Raid out', [('TIMER_EXPIRED', 'CNV AI Raid Out')], [('NAMED_DELETE', n) for n in raiders]),
                Script('CNV AI - Raid give', [('TIMER_EXPIRED', 'CNV AI Raid Give')],
                       [('PLAYER_GIVE_MONEY', s1, RAID_MONEY)])]
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]
                   + [('UNIT_SET_STANCE', n, HOLD_FIRE) for n in foe]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, money)])]
        return m


    MISSION = {'aitower50': lambda: mission('CampAITow50', 0.5),
               'aitower75': lambda: mission('CampAITow75', 0.75),
               'aitower100': lambda: mission('CampAITow100', 1.0),
               'aitowerstate': lambda: mission('CampAITowState', 0.5, opener=False),
               'aitowerfoe': lambda: mission('CampAITowFoe', 0.5, opener=False, foes=FOES),
               'aitowerdep': lambda: mission('CampAITowDep', 0.5, foes=FOES, build=False),
               'aitowerinc': lambda: mission('CampAITowInc', 0.5, opener=False, refinery=True),
               'aitoweropen': lambda: mission('CampAITowOpen', 0.5, opener=False, empty=True),
               'aitowerinc10': lambda: mission('CampAITowInc10', 0.5, opener=False, refinery=True, defense=10,
                                               watch=INC10_WATCH),
               'aitowerinc5': lambda: mission('CampAITowInc5', 0.5, opener=False, refinery=True, defense=5,
                                              watch=INC10_WATCH),
               # round 136: as aitowerinc10 with 20000 at the wake -- does the bank count at all (10 % = 2000: 2 turrets)?
               'aitowerinc10r': lambda: mission('CampAITowRich', 0.5, opener=False, refinery=True, defense=10,
                                                watch=RICH_WATCH, money=RICH),
               # B round 172: ResourceMultiplierCheat on the miner's income (DEFENSE 0 %: nothing is bought, the money
               # only grows). The bench runs MEDIUM (engine_aidiff). aicheat2: a MEDIUM 200 % line; aicheat1: the retail
               # values' other side -- a 300 % line for EASY HARD BRUTAL (not MEDIUM: skipped) and a MEDIUM 100 % one
               # B round 173: BudgetState.State -- as aitowerinc (own budget DEFENSE 50 % still declared), the one
               # BudgetState line naming retail ProductionOnlyBudget (opening done -> PRODUCTION 100 %, DEFENSE 0 %)
               'aibsprod': lambda: mission('CampAIBSProd', 0.5, opener=False, refinery=True, watch=RICH_WATCH,
                                           money=RICH, state='ProductionOnlyBudget'),
               # B round 178: which budget state runs (d122 R1-R3) -- as aibsprod (refinery, 20000), two own states
               'aibsmax': lambda: mission('CampAIBSMax', 0.5, opener=False, refinery=True, watch=RICH_WATCH, money=RICH,
                                          bsets=BSETS['aibsmax']),
               'aibstie': lambda: mission('CampAIBSTie', 0.5, opener=False, refinery=True, watch=RICH_WATCH, money=RICH,
                                          bsets=BSETS['aibstie']),
               'aibszero': lambda: mission('CampAIBSZero', 0.5, opener=False, empty=True, refinery=True,
                                           watch=RICH_WATCH, money=RICH, bsets=BSETS['aibszero'], wait=ZERO_OPENING),
               'aibsdiff': lambda: mission('CampAIBSDiff', 0.5, opener=False, refinery=True, watch=RICH_WATCH,
                                           money=RICH, bsets=BSETS['aibsdiff']),
               # B round 184 (d122 R4): retail budgets, an opening done at once, a raid within 700 that comes and goes
               'aibsback': lambda: mission('CampAIBSBack', 0.5, opener=True, empty=True, refinery=True,
                                           watch=RAID_WATCH, money=RAID_MONEY, raid=True),
               'aicheat2': lambda: mission('CampAICheat2', 0.5, opener=False, refinery=True, defense=0,
                                           watch=CHEAT_WATCH, cheat=CHEAT['aicheat2']),
               'aicheat1': lambda: mission('CampAICheat1', 0.5, opener=False, refinery=True, defense=0,
                                           watch=CHEAT_WATCH, cheat=CHEAT['aicheat1'])}
    return dict(MISSION=MISSION, shared=SimpleNamespace(RICH=RICH, RICH_WATCH=RICH_WATCH, mission=mission))


def aiupgrade_bench():
    """C-line BuildEntry.Upgrade probe; stock Allied Tech2, with its refinery prerequisite preplaced.

    The two personalities differ only in the presence of the constant Upgrade state. Retail tech entries
    wait at least 180 seconds, beyond this probe. No MinTime is changed or tested here.
    """
    from missions import aiskirm_bench


    def personality(enabled, heuristic='<ConstantHeuristic/>', pid='CNVCUpgrade'):
        state = (
            f"""<AIBuildStateDefinition id="CNVCUpgradeBuild">\n"""
            f"""    <Heuristic>{heuristic}</Heuristic>\n"""
            f"""    <BuildEntry Upgrade="Upgrade_AlliedTech2" Heuristic="UPGRADE_TECH"/>\n"""
            f"""  </AIBuildStateDefinition>"""
        ) if enabled else ''
        link = ('<BuildState id="CNVCUpgradeBuild" State="CNVCUpgradeBuild" '
                'Difficulty="EASY MEDIUM HARD BRUTAL"/>') if enabled else ''
        return (
            f"""<?xml version="1.0" encoding="utf-8"?>\n"""
            f"""<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n"""
            f"""  <Tags/>\n"""
            f"""  <Includes>\n"""
            f"""    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml"/>\n"""
            f"""  </Includes>\n"""
            f"""  {state}\n"""
            f"""  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="1AlliedBalanced">\n"""
            f"""    {link}\n"""
            f"""  </AIPersonalityDefinition>\n"""
            f"""</AssetDeclaration>\n"""
        )


    def mission(enabled, name=None, pid='CNVCUpgrade', **kw):
        """kw: personality's heuristic (aiopath_bench.in_state: the state's PathToTargetHeuristic)."""
        m = aiskirm_bench.mission(name or ('CampCUpOn' if enabled else 'CampCUpOff'), lib=False)
        m.facts['upgrade entry'] = int(enabled)
        m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{pid}'
        m.assets.append((f'{pid}.xml', personality(enabled, pid=pid, **kw), f'AIPersonalityDefinition:{pid}'))
        m.put('AlliedRefinery', 'east refinery', side='s1', role='upgrade prerequisite')
        m.put('AlliedPowerPlant', 'east base', -250, 250, side='s1', role='upgrade power')
        return m


    def path_test(condition, surface='Land', tester='JapanAntiAirVehicleTech1', tag=None):
        """B 11-25, PathToTargetHeuristic.LocomotorConditionToUseForTest where the heuristic is judged with both bases
        known (a build state; the opening is drawn at f4 before them, D108 why=early:nobase): aicupgon's state with its
        heuristic one PathToTarget PathExists="true" tested by the stock Jet Tengu (JapanAntiAirVehicleTech1: NORMAL =
        GROUND, SUPERSONIC = AIR, no PANIC set), ra3ext on (ptt rows). Prediction: NORMAL -- a land way, Tech2 as
        aicupgon; PANIC -- no set for it (why=noloco), no way, none as aicupgoff."""
        test = (f'<PathToTargetHeuristic Surface="{surface}" PathExists="true" ObjectTypeToUseForTest="{tester}"'
                f' LocomotorConditionToUseForTest="{condition}" />')
        tag = tag or condition.title()
        m = mission(True, name=f'CampPTT{tag}', pid=f'CNVPTT{tag}', heuristic=test)
        m.facts['upgrade entry'], m.ext = int(condition == 'NORMAL' and surface == 'Land'), True
        return m


    MISSION = {'aicupgon': lambda: mission(True), 'aicupgoff': lambda: mission(False),
               'aipttn': lambda: path_test('NORMAL'), 'aipttp': lambda: path_test('PANIC'),
               'aipttw': lambda: path_test('NORMAL', 'Water', 'AlliedAntiNavalScout', 'WNav'),
               'aipttwg': lambda: path_test('NORMAL', 'Water', tag='WGnd')}
    return dict(MISSION=MISSION)


BENCHES = (
    ai_bench, ai_plan_bench, aiaesthetics_bench, aiallbuild_bench,
    aibuilding_bench, aibuildkind_bench, aicap_bench, aiconstweight_bench,
    aiexpansion_bench, aiintervalfrom_bench, ailastexp_bench, ainodesfull_bench,
    aiomove_bench, aiopath_bench, aiopen_bench, aiopenside_bench,
    aiotime_bench, aipathx_bench, aipeak_bench, aiplacement_bench,
    aipower_bench, aipowerabove_bench, aipoweradv_bench, aipowerenemy_bench,
    aipowerown_bench, aipowervalue_bench, aisimpleexp_bench, aiskirm_bench,
    aislush_bench, aistep_bench, aitechshare_bench, aitower_bench,
    aiupgrade_bench,
)
