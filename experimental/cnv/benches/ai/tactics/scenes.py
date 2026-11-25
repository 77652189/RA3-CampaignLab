"""AI tactics scenes."""
from functools import cache
from types import SimpleNamespace


@cache
def aialphaclose_bench():
    """Independent health-threshold pair: introduce guards after target engagement.

    The target is held at 70% until second 30. Twelve guards then appear around
    it and the health hold ends. This removes the old recipe's early interception
    as a prerequisite, without forcing an AI order or changing weapon reach.
    Only AlphaStrikeTargetHealthPct differs between the builds. Target identity
    and internal AlphaStrike eligibility still require independent observations.
    """
    import math
    from pathlib import Path

    import labpaths

    ar = airetreat_bench()["shared"]
    from parts import Script, Unit


    def mission(high, observe=False, kill='1000.0'):
        """kill: AlphaStrikeTargetTimeToKill. aialobttk is aialobshi with it 0.01 (B219): only the kill-time gate differs."""
        m = ar.mission('CampAlCloseHi' if high else 'CampAlCloseLo',
                       RetreatPowerAdvantage='0.2', AlphaStrikeTargetHealthPct='0.9' if high else '0.01',
                       AlphaStrikeTargetTimeToKill=kill, Crush='false')
        plant = m.role('far plant').name
        m.facts.update({'alpha target': plant, 'guards at': 30.0, 'alpha high': float(high), 'alpha kill': float(kill)})
        m.spawns.add(ar.at.INF)
        actions = []
        for k in range(ar.GUARDS):
            angle = 2 * math.pi * k / ar.GUARDS
            role = f'alpha guard {k + 1}'
            m.waypoint(role, f'CNV Alpha Guard {k + 1}', 'carrier home',
                       ar.GUARD_RING * math.cos(angle), ar.GUARD_RING * math.sin(angle))
            actions.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', f'UNIT - CNV Alpha Guard {k + 1}',
                            ar.at.INF, m.team('p1'), m.mark(role)))
        m.scripts += [
            Script('Alpha - hold health', [('FLAG', 'Alpha guards', 0)],
                   [('UNIT_SET_HEALTH', plant, 70.0)], once=False),
            Script('Alpha - start timer', [], [('SET_MILLISECOND_TIMER', 'Alpha guard timer', 30.0)]),
            Script('Alpha - introduce guards', [('TIMER_EXPIRED', 'Alpha guard timer')],
                   [('SET_FLAG', 'Alpha guards', 1), *actions])]
        if observe:
            # Use the existing yard: no extra object, economy or recruitment candidate.
            yard = m.role('ai yard')
            original = yard.template
            host = 'CNVAlphaTeamsYard'
            xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures' / (original + '.xml')).read_text(encoding='utf-8')
            assert xml.count('<Behaviors>') == xml.count(f'id="{original}"') == 1
            xml = xml.replace(f'id="{original}"', f'id="{host}"').replace(
                '<Behaviors>', '<Behaviors>\n  <DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="4000"/>')
            m.units.append(Unit(host, xml, names=dict(unit=host), what='原建造厂附带变化日志与每秒心跳', params=dict(every=15)))
            m.find(yard.name).template = yard.template = host
            m.name = ('CampAlObsHi' if high else 'CampAlObsLo') + ('' if kill == '1000.0' else 'K')
            m.ext = True
        return m


    MISSION = {'aialcloselo': lambda: mission(False), 'aialclosehi': lambda: mission(True),
               'aialobslo': lambda: mission(False, observe=True), 'aialobshi': lambda: mission(True, observe=True),
               'aialobttk': lambda: mission(True, observe=True, kill='0.01')}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


@cache
def aialphahp_bench():
    """Finite AlphaStrikeTargetHealthPct contrast, not an exact boundary probe.

    Named far plant starts at 70%; guards match the existing retreat probe.
    High 0.9 should
    finish its tactical target before retreat; low 0.01 should retreat first.
    TimeToKill stays deliberately permissive in both, all other fields equal.
    """
    ar = airetreat_bench()["shared"]
    from parts import Script


    def mission(high):
        m = ar.mission('CampAlphaHi' if high else 'CampAlphaLo', guards=ar.GUARDS,
                       RetreatPowerAdvantage='0.2', AlphaStrikeTargetHealthPct='0.9' if high else '0.01',
                       AlphaStrikeTargetTimeToKill='1000.0', Crush='false')
        plant = m.role('far plant').name
        m.scripts.append(Script('CNV Alpha - target health', [], [('UNIT_SET_HEALTH', plant, 70.0)]))
        m.facts['alpha target'] = plant
        return m


    MISSION = {'aialphalo': lambda: mission(False), 'aialphahi': lambda: mission(True)}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


def aibasedef_bench():
    """Engine probe: the skirmish AI team's EnterBaseDefenses (engine line B, layer 4; read back by
    benches/ai/tactics/checks.py#engine_aibasedef; program: work/re l4_micro_engage.md 1.7 -- the turret-order routine, called in team states 2 / 4 / 5 with
    the AI player's object list of class 0x2e; state 8 only with EnterBaseDefensesWhenIdle).

    Retail data: AlliedBaseDefense (the Multigunner turret; KindOf FS_BASE_DEFENSE GARRISONABLE_UNTIL_DESTROYED) carries a
    GarrisonContain, ContainMax 1, PassengerFilter INFANTRY, allies inside allowed. (Soviet / Japan base defenses carry no
    garrison contain; only the Allied one qualifies.)

    airetreat_bench's airet0 (12 of the player's Peacekeepers round the far plant, RetreatPowerAdvantage 0: the team
    fights there, state 2, and dies) with FOUR of the AI's own AlliedBaseDefense 200 north of the far plant (80 apart: the
    team stands to fight within 150 of them, one place each):
      aibd1     EnterBaseDefenses true  -> the model: Peacekeepers go into the turrets (ENCLOSED), leave the team
      aibd0     EnterBaseDefenses false -> nobody goes in
      aibdidle  EnterBaseDefenses false, EnterBaseDefensesWhenIdle true -> nobody (the team fights, never idle at a turret)
      aibdwho   as aibd1, counted by turret (who stands next to which): why only one went in. The turret-order routine takes, for each
                member in one pass, the FIRST turret of the list within 150 that it can be ordered into -- if 'can' does
                not see where the earlier members of the same pass were sent, all four go to the same turret
      aibdpre   as aibdwho, with a fifth Peacekeeper of s1 put into turret 1 by script at the start (full from s0): does
                the member's 'can be ordered into' see a full turret? Seen -> the team goes on to turret 2 and one goes in
                (进炮塔 2); not seen -> they crowd turret 1 again and nobody else gets in (进炮塔 stays 1)
    Facts: wake at.
    """
    ar = airetreat_bench()["shared"]

    TURRET = 'AlliedBaseDefense'
    NEAR = 200.0                             # north (+) of the far plant
    SPREAD = (-120.0, -40.0, 40.0, 120.0)
    EAST = 40.0
    # Turrets 1 and 3 (and the sitter) stand on a wooden fence and a tree of niagara's scenery. Kept so: the round-66c
    # readings were taken here, and the row moved clear (EAST -20, NEAR 150) changes which turrets are within 150 of the
    # team (tests/test_simai.py turret order). tests/test_maps.py names these builds as placed so on purpose.


    def mission(mod, sitter=False, **fields):
        m = ar.mission(mod, guards=ar.GUARDS, RetreatPowerAdvantage='0.0', **fields)
        for k, dx in enumerate(SPREAD):
            m.put(TURRET, 'carrier home', EAST + dx, NEAR, side='s1', name=f'UNIT - CNV AI Turret {k + 1}',
                  role=f'turret {k + 1}')
        if sitter:                           # garrisoned into turret 1 at s0 by the check's script
            (inf,) = m.cnv_units
            m.put(inf, 'carrier home', EAST + SPREAD[0], NEAR + 30.0, side='s1', name='UNIT - CNV AI Sitter',
                  role='sitter')
        return m


    IDLE_TURRETS = (-180.0, (-120.0, -40.0, 40.0, 120.0))   # aibdi*: x and the ys off 'east base' (the AI's yard): the
    # four Peacekeepers stand at (-100, -90..90), each 85-90 from its nearest turret (< EnterGarrisonableStructureDistance 150)


    def idle_mission(mod, **fields):
        """D round 132 (work/re/d131_triggers.md 2): EnterBaseDefensesWhenIdle acts only in the team's micro state 8 (idle /
        default) and only with EnterBaseDefenses on too. aidefense_bench's StaticDefense team (4 Peacekeepers beside the
        AI's yard, no enemy near: the team stays in state 8) without its move order, with the micro manager's two fields
        set (airetreat_bench.micro_xml) and four of the AI's AlliedBaseDefense 80-90 west of the men; the teams host
        (tstate: the team's state when they go in)."""
        ad = aidefense_bench()["shared"]
        ar = airetreat_bench()["shared"]
        host_unit = aiteams_bench()["shared"].host_unit
        HOST = aiteams_bench()["shared"].HOST
        m = ad.mission(mod, 250, 1, 1.5)
        m.scripts = [s for s in m.scripts if s.name != 'CNV AI - Move']
        (fname, xml, asset), = m.assets
        head = '  <AIStrategicStateDefinition'
        xml = xml.replace(head, ar.micro_xml(**fields) + '\n' + head, 1)
        assert xml.count('MicroManager="StandardMicroManager_MEDIUM"') == 1
        xml = xml.replace('MicroManager="StandardMicroManager_MEDIUM"', f'MicroManager="{ar.MICRO_ID}"', 1)
        m.assets = [(fname, xml, asset)]
        m.facts['micro'] = dict(fields)
        x, ys = IDLE_TURRETS
        for k, y in enumerate(ys):
            m.put(TURRET, 'east base', x, y, side='s1', name=f'UNIT - CNV AI Turret {k + 1}', role=f'turret {k + 1}')
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
        m.ext = True
        return m


    MISSION = {
        'aibdi1': lambda: idle_mission('CampAIBdI1', EnterBaseDefenses='true', EnterBaseDefensesWhenIdle='true'),
        'aibdi0': lambda: idle_mission('CampAIBdI0', EnterBaseDefenses='true', EnterBaseDefensesWhenIdle='false'),
        'aibdi2': lambda: idle_mission('CampAIBdI2', EnterBaseDefenses='false', EnterBaseDefensesWhenIdle='true'),
        'aibd1': lambda: mission('CampAIBd1', EnterBaseDefenses='true', EnterBaseDefensesWhenIdle='false'),
        'aibd0': lambda: mission('CampAIBd0', EnterBaseDefenses='false', EnterBaseDefensesWhenIdle='false'),
        'aibdidle': lambda: mission('CampAIBdIdle', EnterBaseDefenses='false', EnterBaseDefensesWhenIdle='true'),
        'aibdwho': lambda: mission('CampAIBdWho', EnterBaseDefenses='true', EnterBaseDefensesWhenIdle='false'),
        'aibdpre': lambda: mission('CampAIBdPre', sitter=True, EnterBaseDefenses='true',
                                   EnterBaseDefensesWhenIdle='false'),
    }
    return dict(MISSION=MISSION)


def aicannot_bench():
    """CannotAttackTargetReaction: land-only Guardians versus a named Cryocopter.

    Three otherwise identical states; predictions follow the SDK enum comments.
    Ignore should retain execution, Disband should release the team, and
    TreatLikeSuccess should apply RAMPAGE. These are predictions, not coverage.
    CNVTeams records the actual team lifecycle; see work/re/c_cannot_report.md.
    """
    import resources
    from maps import niagara
    from benches.ai.targets.scenes import aistate_bench
    BASE = aistate_bench()["shared"].BASE
    INHERITED = aistate_bench()["shared"].INHERITED
    host_unit = aiteams_bench()["shared"].host_unit
    HOST = aiteams_bench()["shared"].HOST
    from parts import Mission, Script

    TANK = 'AlliedAntiVehicleVehicleTech1'
    AIR = 'AlliedSupportAircraft'
    TARGET = 'UNIT - CNV Cannot Air'
    STATE = 'CNVCannot'


    def mission(name, reaction):
        m = Mission(name=name, map=resources.measured(niagara), ext=True,
                    facts={'wake at': 10, 'cannot reaction': reaction})
        pid = 'CNVCannotPersonality'
        removed = '\n'.join(f'<StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED)
        xml = (
            f"""<?xml version="1.0" encoding="utf-8"?>\n"""
            f"""<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n"""
            f""" xmlns:xai="uri:ea.com:eala:asset:instance">\n"""
            f""" <Tags/>\n"""
            f""" <Includes><Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml"/></Includes>\n"""
            f""" <AITargetingHeuristic id="CNVCannotAir" HeuristicType="NamedObject" Name="{TARGET}"\n"""
            f"""  RequireUniqueTarget="true"/>\n"""
            f""" <AIStrategicStateDefinition id="{STATE}" MaxTargets="1" CannotAttackTargetReaction="{reaction}">\n"""
            f"""  <Heuristic><ConstantHeuristic/></Heuristic>\n"""
            f"""  <TargetHeuristic TargetHeuristic="CNVCannotAir"/>\n"""
            f"""  <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE" EndIfStateTurnsOff="false">\n"""
            f"""   <TeamTemplate MinUnits="2" MaxUnits="2" IncludeKindOf="CAN_ATTACK"\n"""
            f"""    ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER" AllowedLocomotorTypes="LAND AMPHIBIOUS"\n"""
            f"""    Priority="STANDARD" AlwaysRecruit="false" MicroManager="StandardMicroManager_MEDIUM">\n"""
            f"""    <ObjectFilter Rule="ANY"><IncludeThing>{TANK}</IncludeThing></ObjectFilter>\n"""
            f"""   </TeamTemplate>\n"""
            f"""  </Tactic>\n"""
            f""" </AIStrategicStateDefinition>\n"""
            f""" <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">\n"""
            f"""  {removed}\n"""
            f"""  <StrategicState id="{STATE}" State="{STATE}"/>\n"""
            f""" </AIPersonalityDefinition>\n"""
            f"""</AssetDeclaration>\n"""
        )
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies',
                         'aiPersonality': f'AIPersonalityDefinition:{pid}'}
        m.assets.append((pid + '.xml', xml, f'AIPersonalityDefinition:{pid}'))
        m.cnv_units = (TANK,)
        m.put('AlliedConstructionYard', 'east base', side='s1', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', role='player yard')
        m.put(AIR, 'east base', -650, 0, name=TARGET, role='air target')
        for k in range(2):
            m.put(TANK, 'east base', -200, -50 + 100*k, side='s1', role=f'guardian {k+1}')
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
        m.waypoint('ai base', 'CNV Cannot Base', 'east base')
        s1 = m.player('s1')
        m.scripts += [Script('Cannot - timer', [], [('PLAYER_SET_MONEY', s1, 0),
                          ('SET_MILLISECOND_TIMER', 'CNV Cannot Wake', 10)]),
                      Script('Cannot - wake', [('TIMER_EXPIRED', 'CNV Cannot Wake')],
                             [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, 'CNV Cannot Base'),
                              ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20),
                              ('SKIRMISH_AI_USE_REPAIRS', s1, 0), ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0),
                              ('PLAYER_SET_MONEY', s1, 0)])]
        return m


    MISSION = {
        'aicantig': lambda: mission('CampCantIg', 'Ignore'),
        'aicantdi': lambda: mission('CampCantDi', 'Disband'),
        'aicantsu': lambda: mission('CampCantSu', 'TreatLikeSuccess'),
    }
    return dict(MISSION=MISSION)


@cache
def aicombat_bench():
    """B-line AllowRecruitUnitsInCombat pair: a fighting Guardian inserted first, an idle one second.

    aisort_bench's set-up (one SimpleAttack team, MaxUnits 1, SortByDistance written false -- its default is on -- so
    the first fitting unit is taken). The first
    candidate ('fighter') stands 100 from a player Guardian (both AttackRange 150, VisionRange 200), so the two shoot at
    each other from the start; a script holds both at full health every frame until the player's tank is deleted at
    `fight ends`. The second candidate ('idle') stands ~560 from the fight, out of sight. Only the team's
    AllowRecruitUnitsInCombat differs. Prediction (the recruit gate's read rule): off -> the fighter is refused while
    its target is in range, the idle one goes; on -> the fighter is taken (first), the idle one stays home.
    """
    team_mission = aiteamfilter_bench()["shared"].mission
    TANK = aiteamfilter_bench()["shared"].TANK
    from missions.aiskirm_bench import ai_map
    from parts import Script

    FIGHT_ENDS = 30.0


    def mission(allow):
        m = team_mission(f'CampAICombat{int(allow)}', tanks=0, inf=0, max_units=1,
                         kinds='IncludeKindOf="VEHICLE"')
        m.map = ai_map(m.map, library=False)
        candidates = []
        for identity, dy in (('fighter', 160.0), ('idle', -300.0)):
            o = m.put(TANK, 'east base', -50.0, dy, side='s1', angle=3.1416,
                      name=f'UNIT - CNV Combat {identity}', role=f'candidate {identity}')
            candidates.append((identity, o.name, (o.x, o.y)))
        foe = m.put(TANK, 'east base', -50.0, 260.0, name='UNIT - CNV Combat foe', role='player foe')
        fighter = candidates[0][1]
        m.scripts += [
            Script('CNV Combat - hold health', [], [('UNIT_SET_HEALTH', fighter, 100.0),
                                                    ('UNIT_SET_HEALTH', foe.name, 100.0)], once=False),
            Script('CNV Combat - end timer', [], [('SET_MILLISECOND_TIMER', 'CNV Combat End', FIGHT_ENDS)]),
            Script('CNV Combat - end', [('TIMER_EXPIRED', 'CNV Combat End')], [('NAMED_DELETE', foe.name)])]
        m.cnv_candidates = tuple(candidates)
        m.facts |= {'allow in combat': int(allow), 'departure radius': 80.0, 'fight ends': FIGHT_ENDS}
        filename, xml, asset = m.assets[0]
        xml = xml.replace('<TeamTemplate ', f'<TeamTemplate SortByDistance="false" '
                          f'AllowRecruitUnitsInCombat="{str(allow).lower()}" ')
        m.assets[0] = filename, xml, asset
        return m


    MISSION = {'aicombat0': lambda: mission(False), 'aicombat1': lambda: mission(True)}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


@cache
def aicreate_bench():
    """C-line CreateUnits slots: identical Guardian opener, minimum slot size 1 / 3.

    The opener, not CreateUnits, supplies exactly three Guardians. Four unrelated
    Peacekeepers are available at wake. Only the CreateUnits minimum differs;
    TeamTemplate.MinUnits stays 1. This separates slot readiness from overall size.
    """
    import os

    import labpaths
    team_mission = aiteamfilter_bench()["shared"].mission
    from missions.aiskirm_bench import ai_map
    from parts import Unit


    def mission(minimum, observe=False):
        m = team_mission(f'CampAICr{minimum}', tanks=0, inf=4, late=3, max_units=3)
        m.map = ai_map(m.map, library=False)
        m.map.AI_TEAMS['create team'] = f'{m.player("s1")}/CNVStateTF_SimpleAttack_0_0'
        filename, xml, asset = m.assets[0]
        xml = xml.replace('</TeamTemplate>',
                          f'<CreateUnits UnitName="AlliedAntiVehicleVehicleTech1" '
                          f'MinUnits="{minimum}" MaxUnits="3"/></TeamTemplate>')
        m.assets[0] = filename, xml, asset
        m.facts['create minimum'] = minimum
        m.facts['home radius'] = 450.0
        m.cnv_units = ('AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry')
        if observe:
            # Same passive carrier as D's engine_aiteams.host_unit; keep content here
            # so the C check consumes only the mission interface (G5).
            plant, host = 'AlliedPowerPlant', 'CNVCreateTeamsHost'
            with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Structures', plant + '.xml'),
                      encoding='utf-8') as f:
                xml = f.read()
            assert xml.count(f'id="{plant}"') == 1 and xml.count('<Behaviors>') == 1
            xml = xml.replace(f'id="{plant}"', f'id="{host}"').replace(f'EditorName="{plant}"', f'EditorName="{host}"')
            xml = xml.replace('<Behaviors>', '<Behaviors>\n'
                              '  <DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="4000"/>')
            m.units.append(Unit(host, xml, names=dict(unit=host),
                                what='被动队伍日志电厂：每15帧记录AI队员和激活状态', params=dict(of=plant, every=15)))
            m.put(host, 'east base', 250.0, 400.0, side='s1', role='teams host')
            m.name, m.ext = f'CampAICr{minimum}C', True
        return m


    MISSION = {'aicr1': lambda: mission(1), 'aicr3': lambda: mission(3),
               'aicr1c': lambda: mission(1, observe=True), 'aicr3c': lambda: mission(3, observe=True)}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


@cache
def aicrush_bench():
    """Engine probe: the skirmish AI team's Crush and CrushPreference (engine line B, layer 4; read back by
    benches/ai/tactics/checks.py#engine_aicrush; program: work/re l4_micro_engage.md 1.5 -- the crush routine: Crush on and (seconds to reach the
    target) < CrushPreference x (...time to kill it by gun) -> drive over it, else shoot).

    airetreat_bench's airet0 (12 of the player's Peacekeepers round the far plant, RetreatPowerAdvantage 0) with the AI's
    four Peacekeepers swapped for four Hammers (SovietAntiVehicleVehicleTech1, CrusherLevel 20 against the Peacekeeper's
    10; the team template's IncludeThing and the placed units are replaced here, the shared builders untouched):
      aicrush1   Crush true, CrushPreference 1.0 (retail) -> the model: the tanks drive into the guards
      aicrush0   Crush false -> they shoot
      aicrushlo  Crush true, CrushPreference 0.01 -> the drive is never 'worth it': they shoot
      aicrush1t  aicrush1 plus D's passive CNVTeams carrier (aiteams_bench.host_unit, MinFrames 15): per sample each
                 member's goal object, where it is and the body heading (tstate aim= / hd=, D round 86)
    Facts: wake at.
    """
    from benches.ai.targets.scenes import aitarget_bench
    at = aitarget_bench()["shared"]
    ar = airetreat_bench()["shared"]

    TANK = 'SovietAntiVehicleVehicleTech1'


    def mission(mod, observe=False, **fields):
        m = ar.mission(mod, guards=ar.GUARDS, RetreatPowerAdvantage='0.0', **fields)
        (fname, xml, asset), = m.assets
        assert f'<IncludeThing>{at.INF}</IncludeThing>' in xml
        m.assets = [(fname, xml.replace(f'<IncludeThing>{at.INF}</IncludeThing>', f'<IncludeThing>{TANK}</IncludeThing>'),
                     asset)]
        for o in m.objects:
            if o.template == at.INF and o.side == 's1':
                o.template = TANK
        m.cast = {k: (r.__class__(TANK, r.name, r.side) if r.template == at.INF and r.side == 's1' else r)
                  for k, r in m.cast.items()}
        m.cnv_units = (at.INF, TANK)
        m.spawns |= {TANK}
        if observe:
            host_unit = aiteams_bench()["shared"].host_unit
            HOST = aiteams_bench()["shared"].HOST
            m.units.append(host_unit(cmd=observe == 'cmd'))     # 'cmd': the host carries out plan lines too
            m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
            m.ext = True
        return m


    MISSION = {
        'aicrush1': lambda: mission('CampAICrush1', Crush='true', CrushPreference='1.0'),
        'aicrush0': lambda: mission('CampAICrush0', Crush='false'),
        'aicrushlo': lambda: mission('CampAICrushLo', Crush='true', CrushPreference='0.01'),
        'aicrush1t': lambda: mission('CampAICrush1T', observe=True, Crush='true', CrushPreference='1.0'),
        'aicrush1g': lambda: ringed(40.0, lambda: mission('CampAICrush1G', observe=True, Crush='true', CrushPreference='1.0')),
    }


    def ringed(r, make):
        """aicrush1g: the guards 40 from the plant, not 60 -- the AI's precision strike (bomb radius 50, MinKillValue
        1000: the plant's 800 + a guard's 200) then counts guards round the plant from the start."""
        old, ar.GUARD_RING = ar.GUARD_RING, r
        try:
            return make()
        finally:
            ar.GUARD_RING = old
    return dict(MISSION=MISSION, shared=SimpleNamespace(TANK=TANK, mission=mission))


@cache
def aidefense_bench():
    """Engine probe: the skirmish AI's StaticDefense tactic -- the Distance circle and the pull-back (read back by
    benches/ai/tactics/checks.py#engine_aidefense; engine line B).

    The enemy (s1, Allied) runs a personality of this probe's own: the Allied co-op base with every inherited strategic
    state removed (as benches/ai/targets/scenes.py#aistate_bench) and one state, always on (ConstantHeuristic, MaxTargets 1), whose target is
    FriendlyLandStructureHeuristic (the retail BalancedDefense pick) and whose tactic is
      StaticDefense EndBehavior="DISBAND" Distance=D UpdateTime=U CombatLeashSlack=S UseAestheticsManager="false"
    with a team of 2-4 Peacekeepers. s1 owns one structure, its yard at 'east base' (the thing to defend), and four
    Peacekeepers beside it (100 west, 90 north .. 90 south of the yard centre, all within 150). The player has only
    its own yard at 'base yard' on the west bank, no turret, no enemy near: nothing fights.
    Ten seconds after the start the AI wakes (as aitarget_bench); 20 s later (mission second 30) a script orders the four
    Peacekeepers by name to MOVE (plain move, not attack-move) to FAR: FAR_DIST from the yard centre toward 'east gate'
    (direction (-0.990, -0.141); yard (3850, 3400)). FAR_DIST was 1200 (FAR (2662, 3231)) for every reading taken on
    2026-11-06; it is 1150 (FAR (2712, 3237)) since round 65, because 1175..1250 on that line is a thicket of trees
    (sapporo's MR_Tree06 pair at (2659, 3223) / (2648, 3249); test_maps keeps waypoints off scenery). The check reads how
    far they get from the yard and whether the team pulls them back inside Distance.
    Builds:
      aidef250    D=250, U=1 s, S=1.5 (the schema default slack)
      aidef450    D=450
      aidefupd4   D=250, UpdateTime 4 s
      aidefslack  D=250, CombatLeashSlack 3.0
    Round 62 (the push must not take the Peacekeepers out of the AI's team, so the mission gives no move): the four start
    START_FAR (700) from the yard toward the gate -- outside every ring but the 900 one -- so the team's own attack-move to
    the yard is the control (the team formed and defends); at mission second PUSH_AT (55) benches/ai/tactics/checks.py#engine_aidefense
    moves them out to FAR itself, with no UNIT_SET_TEAM:
      aidefctl    D=250, U=1 s: UNIT_TELEPORT_TO_WAYPOINT FAR, one by one
      aidefctl4   D=250, U=4 s: the same teleport
      (since round 70 the teleports go to OUT, OUT_DIST (1200) straight south of the yard on open grass: bench 11-07, the
      teleport to FAR at 1150 moved no one -- both builds 4 4 4 4 from s9 to the end; FAR sits on the river bank. 11-06's
      readings were teleports to FAR at 1200 west, the same distance.)
      aidefmv     D=250, U=1 s: MOVE_NAMED_UNIT_TO FAR, one by one (the AI's attack-move against a plain script move)
    KNOWN PIT (engine line A round 136): s1 is one of the players the container hands to the skirmish AI at the start
    (model.handed_to_ai, Lib_Skirmish_Setup), which takes the four placed Peacekeepers off every team. aidef250 / 450 /
    upd4 / slack's 'CNV AI - Move' (m.order: UNIT_SET_TEAM, then MOVE_TEAM_TO) does reach them -- a join after the start
    holds -- but puts them on a script team, out of the AI's (round 61's "nobody pulled back"): those four builds read no
    pull-back. Use the far=True builds (no mission order; the check moves them by name), or put AI-run units the mission
    must order on s4..s6 / make them by script (contract G6c refuses a team order that reaches none).
    """
    import resources
    from maps import niagara
    from benches.ai.targets.scenes import aistate_bench
    ab = aistate_bench()["shared"]
    from parts import Mission, Script

    WAKE_AT = 10.0
    MOVE_AT = 30.0
    PUSH_AT = 55.0
    START_FAR = 700.0
    FAR_DIST = 1150.0   # 1200 until round 65 (on two trees), see the docstring
    OUT_DIST = 1200.0   # the teleports' OUT, straight south of the yard (round 70)
    PID = 'CNVDefenseTest'
    INF = ab.INF
    HEURISTIC = 'FriendlyLandStructureHeuristic'


    def _state(dist, upd, slack):
        return (
            f"""  <AIStrategicStateDefinition id="CNVStateGo" MaxTargets="1">\n"""
            f"""    <Heuristic>\n"""
            f"""      <ConstantHeuristic/>\n"""
            f"""    </Heuristic>\n"""
            f"""    <TargetHeuristic TargetHeuristic="{HEURISTIC}"/>\n"""
            f"""    <Tactic id="Defend" Tactic="StaticDefense" EndBehavior="DISBAND" Distance="{dist}" UpdateTime="{upd}s"\n"""
            f"""            CombatLeashSlack="{slack}" UseAestheticsManager="false">\n"""
            f"""      <TeamTemplate MinUnits="2" MaxUnits="4" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"\n"""
            f"""                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"\n"""
            f"""                    MicroManager="StandardMicroManager_MEDIUM">\n"""
            f"""        <ObjectFilter Rule="ANY">\n"""
            f"""          <IncludeThing>{INF}</IncludeThing>\n"""
            f"""        </ObjectFilter>\n"""
            f"""      </TeamTemplate>\n"""
            f"""    </Tactic>\n"""
            f"""  </AIStrategicStateDefinition>"""
        )


    def personality_xml(dist, upd, slack):
        removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in ab.INHERITED]
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xai="uri:ea.com:eala:asset:instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml" />',
            '  </Includes>',
            _state(dist, upd, slack),
            f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{ab.BASE}">',
            *removed,
            '    <StrategicState id="CNVStateGo" State="CNVStateGo"/>',
            '  </AIPersonalityDefinition>',
            '</AssetDeclaration>', ''])


    def mission(name, dist, upd, slack, far=False):
        m = Mission(name=name, map=resources.measured(niagara), facts={'wake at': WAKE_AT, 'move at': MOVE_AT, 'push at': PUSH_AT})
        m.cnv_dist = dist
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
        m.assets.append((f'{PID}.xml', personality_xml(dist, upd, slack), f'AIPersonalityDefinition:{PID}'))
        m.cnv_units = (INF,)
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        m.spawns |= {INF}
        ex, ey = m.site('east base')
        gx, gy = m.site('east gate')
        L = ((gx - ex) ** 2 + (gy - ey) ** 2) ** 0.5
        ux, uy = (gx - ex) / L, (gy - ey) / L
        for k in range(4):
            side_off = -90.0 + 60.0 * k
            dx, dy = (START_FAR * ux - side_off * uy, START_FAR * uy + side_off * ux) if far else (-100.0, side_off)
            m.put(INF, 'east base', dx, dy, side='s1', angle=3.1416, name=f'UNIT - CNV AI Inf {k + 1}',
                  role=f'peacekeeper {k + 1}')
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.waypoint('far', 'CNV AI Far', 'east base', FAR_DIST * (gx - ex) / L, FAR_DIST * (gy - ey) / L)
        if far:
            m.waypoint('out', 'CNV AI Out', 'east base', 0.0, -OUT_DIST)
        timers = [('SET_MILLISECOND_TIMER', 'CNV AI Push', PUSH_AT)] if far else [
            ('SET_MILLISECOND_TIMER', 'CNV AI Move', MOVE_AT)]
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT),
                                          *timers]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]
        if not far:
            m.scripts.append(Script('CNV AI - Move', [('TIMER_EXPIRED', 'CNV AI Move')],
                                    m.order('move', [m.role(f'peacekeeper {k}').name for k in range(1, 5)], 'CNV AI Far',
                                            side='s1', crew='CNVDefMove')))
        return m


    MISSION = {'aidef250': lambda: mission('CampAIDef250', 250, 1, 1.5),
               'aidef450': lambda: mission('CampAIDef450', 450, 1, 1.5),
               'aidefupd4': lambda: mission('CampAIDefUpd4', 250, 4, 1.5),
               'aidefslack': lambda: mission('CampAIDefSlack', 250, 1, 3.0),
               'aidefctl': lambda: mission('CampAIDefCtl', 250, 1, 1.5, far=True),
               'aidefctl4': lambda: mission('CampAIDefCtl4', 250, 4, 1.5, far=True),
               'aidefmv': lambda: mission('CampAIDefMv', 250, 1, 1.5, far=True)}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


@cache
def aidelay_bench():
    """SpecificSpecialPowerDelay variants on the successful aimicspon Hunt team: one delay line, nothing else differs
    (no team delay, the same update/health/targets; the inherited manual warrior removed, only the automatic window read).

    aidelay0 / aidelay999 (bench 2026-11-11): RUSH_ATTACK MaximumDelay 0 / 999, MinimumDelay 0. Prediction before bench:
    zero lets both warriors charge together; 999 still lets the first charge, then samples a cooldown in 0..999 s, so
    no second charge in the window (a sampled prediction, NOT a deterministic bound).
    aidelaytype: the 999 line on PowerType AOE_ATTACK -- the warriors' RUSH_ATTACK is not delayed: predicted as zero.
    aidelaymin: MinimumDelay 999, MaximumDelay 0 -- the program's draw (work/re/l4_toggle.md) is its upper end when the
    range is empty or reversed, so 0: predicted as zero (a MinimumDelay taken as a floor would give 999).
    aidelaytog / aidelaytogdef (TogglePowerSubType): the warriors give way to TOG_PK, a Peacekeeper whose two ToggleStates
    both say TOGGLE_ALWAYS -- the program's TOGGLE heuristic then switches every micro round, target or not
    (l4_toggle.md) -- built from a copied barracks; the line is TOGGLE 999 s on sub type TOGGLE_ALWAYS / TOGGLE_DEFAULT.
    The program keys a TOGGLE cooldown by the hint of the state being switched to and keeps it per micro manager (the
    team): predicted aidelaytog one shield up for good after the first switch, aidelaytogdef switching on and off.
    aidelayteam / aidelayteammin: the RUSH_ATTACK line 0 s, the micro manager's SpecialPowerDelayMinimum / Maximum
    999 / 999 and 999 / 0 -- the team's delay after any fire, the same draw: predicted no second charge / as zero.
    """
    import dataclasses

    am = aimicro_bench()["shared"]
    from missions import aiskirm_bench as sk
    from units import production

    TOG_PK, TOG_BARRACKS = 'CNVTogPK', 'CNVTogBarracks'


    def toggle_pk():
        pk = sk.new_pk(TOG_PK)
        x = pk.xml
        # MaxHealth x 100: the kept-up conscripts killed them by s41 in the simulator; a death reads as a switch back
        for old, new in [*((h, 'ToggleHint="TOGGLE_ALWAYS"') for h in ('ToggleHint="TOGGLE_DEFAULT"',
                                                                        'ToggleHint="TOGGLE_DEFENSE_SELF_ONLY"')),
                         ('MaxHealth="150.0"', 'MaxHealth="15000.0"')]:
            assert x.count(old) == 1, old
            x = x.replace(old, new)
        return dataclasses.replace(pk, xml=x, what='维和换 id，盾的两个状态都标 TOGGLE_ALWAYS（AI 每轮都切），血 ×100')


    def mission(maximum, minimum=0, power='RUSH_ATTACK', name=None, sub=None, team=None):
        name = name or ('Long' if maximum else 'Zero')
        toggle = sub is not None
        unit = dict(unit=TOG_PK, factory=TOG_BARRACKS) if toggle else {}
        m = am.built('CampAD' + name, tactic='Hunt', foes=True, spow=True, **unit)
        if toggle:
            pk = toggle_pk()
            m.units += [pk, production.building('AlliedBarracks', [pk.id], TOG_BARRACKS)]
        filename, xml, asset = m.assets[0]
        tag = (f'<SpecificSpecialPowerDelay PowerType="{power}" '
               + (f'TogglePowerSubType="{sub}" ' if toggle else '')
               + f'MinimumDelay="{minimum}s" MaximumDelay="{maximum}s"/>')
        # SDK sequence: TargetBias*, SpecificSpecialPowerDelay*, RetreatBaseCriteria,
        # IgnoreTargets. Appending after IgnoreTargets fails BinaryAssetBuilder.
        anchor = '    <RetreatBaseCriteria'
        assert xml.count(anchor) == 1
        xml = xml.replace(anchor, '    ' + tag + '\n' + anchor)
        assert tag in xml
        if team is not None:                    # (minimum, maximum) of the team's delay
            old = ' UseSpecialPowers='
            assert xml.count(old) == 1
            xml = xml.replace(old, f' SpecialPowerDelayMinimum="{team[0]}s" SpecialPowerDelayMaximum="{team[1]}s"{old}')
        m.assets[0] = filename, xml, asset
        m.facts['specific maximum'] = maximum
        # the draw: max when max <= min, else in [min, max]; a TOGGLE line holds only its own sub type
        own = 'TOGGLE' if toggle else 'RUSH_ATTACK'
        m.facts['delayed'] = power == own and sub in (None, 'TOGGLE_ALWAYS') and maximum > 0 or (team or (0, 0))[1] > 0
        return m


    LOCK_RA, LOCK_BARRACKS = 'CNVLockRA', 'CNVLockBarr'
    FOES = {'2': 'SovietAntiAirShip', '1': 'SovietAntiAirShip', 'm': 'SovietMiner'}


    def lock_ra():
        """The Rocket Angel (SDK Japan/Units/JapanAntiVehicleInfantryTech3.xml) under LOCK_RA: its retail TOGGLE_LOCKDOWN
        states untouched; cost 900 -> 200 (two inside the opener's deposit), MaxHealth x 100 (the Bullfrogs' flak), no
        tech 3 upgrade needed (bench 11-24 first run: with it none was built, game and simulator alike)."""
        import os
        import labpaths
        from parts import Unit
        x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Japan', 'Units', 'JapanAntiVehicleInfantryTech3.xml'),
                 encoding='utf-8').read()
        for old, new in [*((f'{k}="JapanAntiVehicleInfantryTech3"', f'{k}="{LOCK_RA}"') for k in ('id', 'EditorName')),
                         ('Amount="900"', 'Amount="200"'), ('MaxHealth="400"', 'MaxHealth="40000"'),
                         # its GameDependency: the Japanese barracks' tech 3, which the copied barracks never gets
                         ('<NeededUpgrade>Upgrade_JapanBarracksTech3</NeededUpgrade>', '')]:
            assert x.count(old) == 1, old
            x = x.replace(old, new)
        return Unit(LOCK_RA, x, what='火箭天使换 id（锁定枪两个状态照原版），造价 200，血 ×100')


    def lock(team):
        """ailock2 / ailock1 / ailockm (TOGGLE_LOCKDOWN, work/re/l4_toggle.md hint 9): the aimicspon Hunt team takes
        LOCK_RA; no delay line. 2: two angels, two Bullfrogs (armed, their flak hits the angels) -- predicted one locks,
        never two at once (the switch marks TOGGLE used for the round; a target another locks is skipped). 1: the team
        takes one -- predicted never (a team of one never locks). m: two angels, two unarmed Ore Collectors -- predicted
        never (no enemy can attack)."""
        m = am.built('CampAL' + team, tactic='Hunt', foes=True, spow=True, unit=LOCK_RA, factory=LOCK_BARRACKS,
                     foe=FOES[team])
        ra = lock_ra()
        m.units += [ra, production.building('AlliedBarracks', [ra.id], LOCK_BARRACKS)]
        filename, xml, asset = m.assets[0]
        # the angel walks on AIR (its locomotor's Surfaces): the team template's LAND AMPHIBIOUS never took it
        for old, new in [('AllowedLocomotorTypes="LAND AMPHIBIOUS"', 'AllowedLocomotorTypes="LAND AMPHIBIOUS AIR"'),
                         *([('MinUnits="2" MaxUnits="2"', 'MinUnits="1" MaxUnits="1"')] if team == '1' else [])]:
            assert xml.count(old) == 1, old
            xml = xml.replace(old, new)
        m.assets[0] = filename, xml, asset
        m.facts['delayed'] = team == '2'        # toggled(): 'up once, never two' against 'never up'
        m.facts['lock team'] = 1.0 if team == '1' else 2.0
        return m


    MISSION = {'ailock2': lambda: lock('2'), 'ailock1': lambda: lock('1'), 'ailockm': lambda: lock('m'),
               'aidelay0':lambda: mission(0), 'aidelay999': lambda: mission(999),
               'aidelaytype': lambda: mission(999, power='AOE_ATTACK', name='Type'),
               'aidelaymin': lambda: mission(0, minimum=999, name='Min'),
               'aidelayteam': lambda: mission(0, name='Team', team=(999, 999)),
               'aidelayteammin': lambda: mission(0, name='TeamMin', team=(999, 0)),
               'aidelaytog': lambda: mission(999, power='TOGGLE', name='Tog', sub='TOGGLE_ALWAYS'),
               'aidelaytogdef': lambda: mission(999, power='TOGGLE', name='TogDef', sub='TOGGLE_DEFAULT')}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


def aidiff_bench():
    """Engine probe: a personality's <StrategicState Difficulty=...> -- does the AI run only the states listed for its
    difficulty, and which difficulty does an AI player of a campaign map get (read back by benches/ai/tactics/checks.py#engine_aidiff;
    private ai/data.py Personality.of / ai/states.py StrategicStates, simai's DIFFICULTY map: campaign normal -> MEDIUM).

    aiteamfilter_bench's set-up (Niagara, the enemy s1 Allied with a yard and no money, every inherited strategic state
    removed, woken at 10 s; 4 Guardians and 4 Peacekeepers at home) with TWO always-on states (ConstantHeuristic,
    MaxTargets 1, SimpleAttack at the closest player structure, MinUnits 1, MaxUnits 8):
      CNVStateDT  listed Difficulty="MEDIUM"              its team takes Guardians only (ObjectFilter ANY + IncludeThing)
      CNVStateDI  listed Difficulty="EASY HARD BRUTAL"    its team takes Peacekeepers only
    Two player power plants ~750 west (one target goes to one state, engine_aistate aistatefar2), so both could leave.
    Builds: aidiff (as above) and aidiffx (the two Difficulty lists swapped: the same answer with the other unit type,
    so a type that never leaves is not read as a difficulty).

    Facts: wake at, swapped (1: the Guardians' state is the EASY HARD BRUTAL one), expect tanks home, expect infantry home (the
    model's guess: the bench walks the campaign at normal = MEDIUM, only the MEDIUM state runs).
    """
    import resources
    from maps import niagara
    from benches.ai.targets.scenes import aistate_bench
    BASE = aistate_bench()["shared"].BASE
    INHERITED = aistate_bench()["shared"].INHERITED
    TANK = aiteamfilter_bench()["shared"].TANK
    INF = aiteamfilter_bench()["shared"].INF
    objfilter = aiteamfilter_bench()["shared"].objfilter
    from parts import Mission, Script

    WAKE_AT = 10.0
    MEDIUM, OTHERS = 'MEDIUM', 'EASY HARD BRUTAL'


    def state_xml(sid, unit):
        return (
            f"""  <AIStrategicStateDefinition id="{sid}" MaxTargets="1">\n"""
            f"""    <Heuristic>\n"""
            f"""      <ConstantHeuristic/>\n"""
            f"""    </Heuristic>\n"""
            f"""    <TargetHeuristic TargetHeuristic="ClosestStructureHeuristic"/>\n"""
            f"""    <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE" EndIfStateTurnsOff="true">\n"""
            f"""      <TeamTemplate MinUnits="1" MaxUnits="8" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"\n"""
            f"""                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"\n"""
            f"""                    MicroManager="StandardMicroManager_MEDIUM">{objfilter('ANY', inc=(unit,))}\n"""
            f"""      </TeamTemplate>\n"""
            f"""    </Tactic>\n"""
            f"""  </AIStrategicStateDefinition>"""
        )


    def personality_xml(pid, tank_diff, inf_diff):
        removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xai="uri:ea.com:eala:asset:instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
            '  </Includes>',
            state_xml('CNVStateDT', TANK),
            state_xml('CNVStateDI', INF),
            f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
            *removed,
            f'    <StrategicState id="CNVStateDT" State="CNVStateDT" Difficulty="{tank_diff}"/>',
            f'    <StrategicState id="CNVStateDI" State="CNVStateDI" Difficulty="{inf_diff}"/>',
            '  </AIPersonalityDefinition>',
            '</AssetDeclaration>', ''])


    def mission(name, swapped=False):
        pid = 'CNVDiff' + ('X' if swapped else 'M')
        tank_diff, inf_diff = (OTHERS, MEDIUM) if swapped else (MEDIUM, OTHERS)
        m = Mission(name=name, map=resources.measured(niagara), facts={'wake at': WAKE_AT, 'swapped': int(swapped),
                                                   'expect tanks home': 4 if swapped else 0,
                                                   'expect infantry home': 0 if swapped else 4})
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
        m.assets.append((f'{pid}.xml', personality_xml(pid, tank_diff, inf_diff), f'AIPersonalityDefinition:{pid}'))
        m.cnv_units = (TANK, INF)
        m.spawns |= {TANK, INF}
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        m.put('AlliedPowerPlant', 'east gate', -300.0, 120.0, name='UNIT - CNV AI Player Target', role='player target')
        m.put('AlliedPowerPlant', 'east gate', -300.0, -120.0, name='UNIT - CNV AI Player Target 2', role='player target 2')
        for k in range(4):
            m.put(TANK, 'east base', -200.0, 160.0 + 70.0 * k, side='s1', angle=3.1416,
                  name=f'UNIT - CNV AI Tank {k + 1}', role=f'ai guardian {k + 1}')
            m.put(INF, 'east base', -200.0, -160.0 - 50.0 * k, side='s1', angle=3.1416,
                  name=f'UNIT - CNV AI Peacekeeper {k + 1}', role=f'ai peacekeeper {k + 1}')
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]
        return m


    MISSION = {'aidiff': lambda: mission('CampAIDiff'), 'aidiffx': lambda: mission('CampAIDiffX', swapped=True)}
    return dict(MISSION=MISSION)


@cache
def aidistance_bench():
    """C-line StaticDefense Distance pair; identical retained AI team and teleport.

    At 30s one Guardian is teleported 1200 south on open grass, without a team
    transfer or movement order. Prediction: Distance 250 returns it; Distance
    2000 accepts the displacement. Aesthetics is enabled identically in both;
    its actual stand-point selection remains a gap, not a fitted rule.
    """
    team_mission = aiteamfilter_bench()["shared"].mission
    from missions.aiskirm_bench import ai_map
    HOST = aiteams_bench()["shared"].HOST
    host_unit = aiteams_bench()["shared"].host_unit
    from model import Script


    def mission(distance):
        m = team_mission(f'CampAID{distance}', static=True, tanks=1, inf=0, max_units=1)
        m.map = ai_map(m.map, library=False)
        filename, xml, asset = m.assets[0]
        xml = xml.replace('Distance="450"', f'Distance="{distance}" UpdateTime="1s" UseAestheticsManager="true"')
        m.assets[0] = filename, xml, asset
        if distance == 2000:
            m.ext = True
            m.units.append(host_unit())
            m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
        m.facts |= {'distance': distance, 'push at': 30.0}
        m.waypoint('distance out', 'CNV Distance Out', 'east base', 0, -1200)
        m.scripts += [Script('Distance - timer', [], [('SET_MILLISECOND_TIMER', 'CNV Distance Push', 30.0)]),
                      Script('Distance - push', [('TIMER_EXPIRED', 'CNV Distance Push')],
                             [('UNIT_TELEPORT_TO_WAYPOINT', m.role('ai guardian 1').name, 'CNV Distance Out')])]
        return m


    MISSION = {'aidist250': lambda: mission(250), 'aidist2000': lambda: mission(2000)}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


@cache
def aiengineer_bench():
    """Independent Engineer / SimpleAttack pair with one placed, named engineer.

    Both lanes use the same Standard micro manager and closest enemy structure.
    Only Tactic.Tactic changes; no production or script capture order intervenes.
    This isolates the tactic from retail CaptureAnything micro / CreateUnits.
    """
    team_mission = aiteamfilter_bench()["shared"].mission
    from missions.aiskirm_bench import ai_map


    def mission(engineer):
        m = team_mission('CampAIEng', tanks=0, inf=1, second='AlliedEngineer',
                         max_units=1, kinds='IncludeKindOf="ENGINEER"')
        m.name = 'CampAIEng' if engineer else 'CampAIEngCtl'
        m.map = ai_map(m.map, library=False)
        filename, xml, asset = m.assets[0]
        if engineer:
            xml = xml.replace('Tactic="SimpleAttack"', 'Tactic="Engineer"')
        m.assets[0] = filename, xml, asset
        m.cnv_named = {'engineer': 'UNIT - CNV AI Riptide 1',
                       'target': m.role('player target').name}
        m.waypoint('engineer target', 'CNV Engineer Target', 'east gate', -300, 0)
        m.facts['engineer tactic'] = int(engineer)
        return m


    MISSION = {'aieng': lambda: mission(True), 'aiengctl': lambda: mission(False)}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


def aifallback_bench():
    """Retreat fallback distance A/B: airetf, changing only 100 versus 500.

    Keep the original guards, power threshold, base distance and flag timing. The
    short latch should permit an earlier turn back towards the enemy once enemies
    leave the search list; the long latch should carry the team farther home.
    Area counts bound movement only; they do not expose the micro state's exit.
    """
    ar = airetreat_bench()["shared"]


    def mission(name, distance):
        m = ar.mission(name, guards=ar.GUARDS, flag=True,
                       RetreatPowerAdvantage='0.2', RetreatMinDistanceToFallback=str(distance))
        m.facts['fallback distance'] = distance
        x, y = m.site('east base')[:2]
        m.facts['fallback midway'] = (x, y - 600)
        return m


    MISSION = {
        'aifbshort': lambda: mission('CampAIFbShort', 100),
        'aifblong': lambda: mission('CampAIFbLong', 500),
        'aifbshortt': lambda: ar.observe(mission('CampAIFbShort', 100), 'CampAIFbShortT'),  # + CNVTeams (B K3)
    }
    return dict(MISSION=MISSION)


@cache
def aigarrison_bench():
    """Engine probe: the skirmish AI team's EnterGarrisons (engine line B, layer 4; read back by
    benches/ai/tactics/checks.py#engine_aigarrison; program: work/re l4_micro_engage.md 1.7 -- the turret-order routine, called in team states 2 / 4 / 5
    only; model: RA3-EngineModel ra3model/ai/tactics.py, simai.Brain).

    airetreat_bench's airet0 (12 of the player's Peacekeepers round the far plant, RetreatPowerAdvantage 0: the team
    fights there, state 2, and dies) with one of retail's civilian apartments (AM_Apartments_01, neutral, 5 infantry;
    docs/engine/garrison.md) on the team's way in:
      aigar1    the house 200 north of the far plant (where the team stands to fight, within 150), EnterGarrisons true
                (retail MEDIUM) -> the model: the team's Peacekeepers go into the house (it turns the AI's) and leave the team
      aigar0    the same, EnterGarrisons false -> nobody goes in
      aigarfar  EnterGarrisons true, the house 450 SOUTH (behind the plant from the team's way in; beyond 150 of the fight)
                -> nobody. (First made 450 north, on the way in: the northernmost fighter stood within 150 of it and one
                Peacekeeper went in at s20 -- per member, as the model has it, but not the 'too far' case.)
    Facts: wake at, house (name).
    """
    ar = airetreat_bench()["shared"]

    HOUSE = 'AM_Apartments_01'
    HOUSE_NAME = 'UNIT - CNV AI House'
    NEAR, FAR = 200.0, -450.0                # north (+) of the far plant (3700, 2400); the AI's base is north (3850, 3400)
    geometry = SimpleNamespace(EAST=0.0)                               # towards the team's line from its base
    # Round 121 (engine A): was 40, the house then stood on a grass tuft of niagara's scenery (CC_GRASS06 at 3733, 2599;
    # tests/test_maps.py test_nothing_a_build_places_stands_on_scenery). The round-66 bench readings were at EAST 40.


    def mission(mod, north, enter, observe=False):
        m = ar.mission(mod, guards=ar.GUARDS, RetreatPowerAdvantage='0.0', EnterGarrisons=enter)
        m.put(HOUSE, 'carrier home', geometry.EAST, north, side='civ', name=HOUSE_NAME, role='house')
        m.facts['house'] = HOUSE_NAME
        if observe:
            # Engine line D round 144: aigar1 plus D's passive CNVTeams carrier (as aimicro_bench.update_time), for the
            # team's micro state sequence (tstate lines in ra3ext.log; experimental/cnv/teamlog.py).
            host_unit = aiteams_bench()["shared"].host_unit
            HOST = aiteams_bench()["shared"].HOST
            m.units.append(host_unit())
            m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
            m.ext = True
        return m


    MISSION = {
        'aigar1': lambda: mission('CampAIGar1', NEAR, 'true'),
        'aigar0': lambda: mission('CampAIGar0', NEAR, 'false'),
        'aigarfar': lambda: mission('CampAIGarFar', FAR, 'true'),
        'aigar1t': lambda: mission('CampAIGar1T', NEAR, 'true', observe=True),
    }
    return dict(MISSION=MISSION, shared=geometry)


def aihome_bench():
    """Engine probe: the personality's DefaultTacticHomeBaseCriteria -- which base a RETURN_HOME_AND_DISBAND team walks
    home to (read back by benches/ai/tactics/checks.py#engine_aihome; engine line B round 201).

    Two AI yards, both initial map objects placed one after the other (as C's aibs3 / aibn2 pairs): base A = the first
    at 'east base' (OLDEST_OF_TYPE), base B = the second NORTH north of it (MOST_RECENT_OF_TYPE), both MAIN_BASE.

    aihmg* (the probe): aitargetpick's aiendh set-up (4 Guardians at A, one always-on SimpleAttack state, EndBehavior
    RETURN_HOME_AND_DISBAND, the tactic has no HomeBaseCriteria of its own so the personality's is used, the check kills
    the target at KILL_AT) with one target only -- a NamedObject heuristic on the player's power plant at the east gate
    (~710 from A, ~1610 from B), no barracks or tank, so once the plant is gone there is no new target (aiendh's team
    went straight on to the barracks, never home). Only DefaultTacticHomeBaseCriteria differs:
      aihmgcl  SortOrder PREFER_CLOSEST, PreferredNotBaseTypes CAPTURED (the retail line)       -> A
      aihmgnw  SortOrder PREFER_NEWEST,  PreferredNotBaseTypes CAPTURED                         -> B (SortOrder)
      aihmgno  SortOrder PREFER_CLOSEST, PreferredNotBaseTypes OLDEST_OF_TYPE                   -> B (PreferredNot)

    aihomecl (bench 2026-11-14, benches/ai/tactics/checks.py#engine_aihome): aireactive_bench's ReactiveDefense team (4 Peacekeepers, the
    foe 1000 south of A, radius 1200) with the second yard -- the tactic has no TargetBaseCriteria; it guards B.
    """
    import resources
    from maps import niagara
    rb = aireactive_bench()["shared"]
    from benches.ai.targets.scenes import aistate_bench
    ab = aistate_bench()["shared"]
    from benches.ai.targets.scenes import aitargetpick_bench
    tp = aitargetpick_bench()["shared"]
    from parts import Mission, Script

    WAKE_AT = 10.0
    KILL_AT = 35.0
    FOE_DIST = rb.FOE_DIST
    RADIUS = 1200
    NORTH = 1350.0          # base B from base A
    PID = 'CNVHomeTest'
    PLANT = 'UNIT - CNV TP Plant'
    NAMED = (f'  <AITargetingHeuristic id="CNVHPlant" HeuristicType="NamedObject" Name="{PLANT}"'
             ' MinDistanceFromEnemy="0" SearchRange="5000" Location="Land"/>')


    def _wrap(states, pid, inherit_attrs, criteria):
        removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in ab.INHERITED]
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xai="uri:ea.com:eala:asset:instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml" />',
            '  </Includes>',
            *states,
            f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{ab.BASE}"{inherit_attrs}>',
            *removed,
            *criteria,
            '  </AIPersonalityDefinition>',
            '</AssetDeclaration>', ''])


    def _yards(m):
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'east base', 0, NORTH, side='s1', name='UNIT - CNV AI Yard B',
              role='second ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')


    def _wake(m):
        s1, base = m.player('s1'), 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]


    def _facts(**kw):
        return {'wake at': WAKE_AT, 'initial dual bases': True, 'north': NORTH, **kw}


    def home(name, sort, preferred_not):
        """The probe: a SimpleAttack team on the named plant, killed at KILL_AT, walks home by the criteria."""
        pid = PID + name[-3:]
        m = Mission(name=name, map=resources.measured(niagara),
                    facts=_facts(probe='home', **{'home sort': sort, 'home preferred not': preferred_not,
                                                  'kill plant at': KILL_AT}))
        state = tp.state_xml('CNVStateTP', [('CNVHPlant', None)], 1, end='RETURN_HOME_AND_DISBAND')
        crit = [f'    <DefaultTacticHomeBaseCriteria SortOrder="{sort}" PreferredNotBaseTypes="{preferred_not}"/>']
        xml = _wrap([NAMED, state], pid, '', ['    <StrategicState id="CNVStateTP" State="CNVStateTP"/>', *crit])
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
        m.assets.append((f'{pid}.xml', xml, f'AIPersonalityDefinition:{pid}'))
        m.cnv_units = (tp.TANK,)
        m.spawns |= {tp.TANK}
        _yards(m)
        m.put('AlliedPowerPlant', 'east gate', 0.0, 0.0, name=PLANT, role='plant')
        for k in range(4):
            m.put(tp.TANK, 'east base', -200.0, 160.0 + 70.0 * k, side='s1', angle=3.1416,
                  name=f'UNIT - CNV AI Tank {k + 1}', role=f'ai guardian {k + 1}')
        _wake(m)
        return m


    def reactive(name):
        """aireact1200 with the second yard and RETURN_HOME_AND_DISBAND: which base ReactiveDefense guards."""
        m = Mission(name=name, map=resources.measured(niagara), facts=_facts(probe='reactive', radius=RADIUS))
        state = rb._state().replace('EndBehavior="DISBAND"', 'EndBehavior="RETURN_HOME_AND_DISBAND"')
        xml = _wrap([state], PID, f' ReactiveDefenseRadius="{RADIUS}"',
                    ['    <StrategicState id="CNVStateGo" State="CNVStateGo"/>',
                     '    <DefaultTacticHomeBaseCriteria SortOrder="PREFER_CLOSEST" PreferredNotBaseTypes="CAPTURED"/>'])
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
        m.assets.append((f'{PID}.xml', xml, f'AIPersonalityDefinition:{PID}'))
        m.cnv_units = (ab.INF,)
        m.spawns |= {ab.INF}
        _yards(m)
        for k in range(4):
            m.put(ab.INF, 'east base', -100.0, -90.0 + 60.0 * k, side='s1', angle=3.1416,
                  name=f'UNIT - CNV AI Inf {k + 1}', role=f'peacekeeper {k + 1}')
        m.put(ab.INF, 'east base', 0.0, -FOE_DIST, angle=1.5708, name='UNIT - CNV RD Foe', role='foe')
        _wake(m)
        return m


    MISSION = {'aihomecl': lambda: reactive('CampAIHomeCl'),
               'aihmgcl': lambda: home('CampAIHmGCl', 'PREFER_CLOSEST', 'CAPTURED'),
               'aihmgnw': lambda: home('CampAIHmGNw', 'PREFER_NEWEST', 'CAPTURED'),
               'aihmgno': lambda: home('CampAIHmGNo', 'PREFER_CLOSEST', 'OLDEST_OF_TYPE')}
    return dict(MISSION=MISSION)


@cache
def aimicro_bench():
    """Engine probe: when the skirmish AI's micro manager makes Imperial Warriors use their Bonzai charge (RUSH_ATTACK;
    read back by benches/ai/tactics/checks.py#engine_aimicro; engine line B).

    The data (SDK LogicCommand Command_JapanAntiInfantryInfantryBonzai): AISpecialPowerInfo Heuristic RUSH_ATTACK,
    MICRO_MANAGER, TargetObjectInclude INFANTRY, HealthFraction 0.8, Distance 100, UseToCounterGarrison. The charge
    (SpecialPower_JapanAntiInfantryInfantryBonzai, ReloadTime 30 s) puts AttributeModifier_..Bonzai on the warrior for 10 s:
    ObjectStatus WEAPON_UPGRADED_02 (the check reads it with UNIT_HAS_OBJECT_STATUS), speed 150 %. The warrior's gun
    (JapanAntiInfantryInfantryWeapon) has AttackRange 150, the charge sword 20.
    The model (RA3-EngineModel ra3model/ai/micro.py rush): fire when the target is INFANTRY and (own health < 0.8 of max,
    or the target within weapon range and < 100 away, 2D).

    The enemy (s1, Allied faction -- the micro manager reads the unit's command set, not the faction) runs a personality
    of this probe's own, as benches/ai/tactics/scenes.py#aidefense_bench: the Allied co-op base with every inherited strategic state removed and one
    state, always on, StaticDefense of its yard (Distance 400, UseAestheticsManager false) with a team of exactly the two
    warriors and MicroManager = the build's (StandardMicroManager: UpdateTime 0.5 s, no delays; _MEDIUM: 2 s, team delay
    2..8 s after a fire). Two warriors stand 200 west of the s1 yard, 100 apart north-south, facing west; one player
    engineer (unarmed infantry; the check keeps it at full health) stands D west of each warrior (the other engineer is
    >= 134 away). Money 0. The AI wakes at WAKE_AT (the retail wake set, as benches/ai/tactics/scenes.py#aispecial_bench).
    The warriors start as the player's (friends of the engineers, nothing fights) and are handed to s1 at HAND_AT, one
    second after the wake: the program registers a unit's AISpecialPowerInfo only when it is made or changes hands while
    the AI brain is not paused (work/re l4_specials.md), and aimicpre -- the warriors s1's from the start, the
    AI asleep then -- never charged in 60 s.
    Builds:
      aimicpre    D = 90,  StandardMicroManager, the warriors s1's from the start (no hand-over)
      aimicnear   D = 90,  StandardMicroManager            (in range and < 100: the model fires at the first round)
      aimicmed    D = 90,  StandardMicroManager_MEDIUM     (one fire, then a 2..8 s team delay before the other)
      aimicfar    D = 140, StandardMicroManager            (in range but >= 100: the model never fires)
      aimichurt   D = 140, StandardMicroManager, the warriors at 70 % health from the start (health < 0.8: fires)
      aimicmade   D = 90,  StandardMicroManager, no warriors placed: the script creates them on s1's team at HAND_AT
                  (the AI awake) -- does a unit made after the wake charge where the handed-over ones did not?
      aimichunt   as aimicmade, but the team's tactic is a Targetless Hunt (as benches/ai/targets/scenes.py#aistate_bench aihunt) instead of
                  StaticDefense: does the micro manager run only under some tactics? (no: never recruited, see aitoggle)
      aimicxfer   as aimicmade, the script runs UNIT_AI_TRANSFER_ALL again right after making them (work/re
                  l4_micro_gate.md: the recruiters refuse units on teamSoviet_1; the wake's transfer saw only the units then)
      aimicnearx  as aimicnear (hand-over), UNIT_AI_TRANSFER_ALL again right after the hand-over
      aimicbuilt  no warriors placed: the AI builds them itself (round 19) -- s1 owns a Japanese barracks (JapanBarracks)
                  400 south of its yard and a power plant 400 north; an opening move of this probe's own (OPENER: a
                  deposit of 1000 to PRODUCTION, then two warriors; the build state AlliedNeededUnits removed, retail
                  budgets kept, as benches/ai/production/scenes.py#aitower_bench), money BUILT_MONEY at the wake. The units are unnamed: the check
                  counts them by player (template owned, objects with the charge status). Two player conscripts (kept at
                  full health) stand 400 south of the barracks and attack-move to it once s1 owns two warriors (the
                  warriors get hurt: under 0.8 health the model fires whatever the distance). l4_micro_gate.md: the
                  recruiters take units on the AI's default team; script-made ones sit on teamSoviet_1.
      aimicbuilth as aimicbuilt, the team a Targetless Hunt, no conscripts: are the built warriors recruited at all
                  (they walk off) -- the by-player count cannot tell whose team a unit is on.
      aimicbuiltf as aimicbuilth with the conscripts (round 20): the Hunt team has recruited the warriors (builth) and
                  now meets infantry and gets hurt -- in a running team, a target, under 0.8 health: do they charge?
    Facts: wake at, hand at, distance, health, hunt (1: the Hunt tactic), built (1: the AI builds them), foes (1: built,
    with the conscripts).
    """
    import resources
    from maps import niagara
    from benches.ai.targets.scenes import aistate_bench
    ab = aistate_bench()["shared"]
    from parts import Mission, Script

    WAKE_AT = 10.0
    HAND_AT = 11.0     # the warriors change hands (p1 -> s1) one second after the wake
    PID = 'CNVMicroTest'
    WARRIOR, ENGINEER = 'JapanAntiInfantryInfantry', 'AlliedEngineer'
    WEST, APART = 200.0, 100.0


    HUNT_HEAD = (
        '  <AIStrategicStateDefinition id="CNVStateMicro">\n'
        '    <Heuristic>\n'
        '      <ConstantHeuristic/>\n'
        '    </Heuristic>\n'
        '    <Tactic id="Hunt" Tactic="Hunt" Targetless="true">\n'
    )
    DEFEND_HEAD = (
        '  <AIStrategicStateDefinition id="CNVStateMicro" MaxTargets="1">\n'
        '    <Heuristic>\n'
        '      <ConstantHeuristic/>\n'
        '    </Heuristic>\n'
        '    <TargetHeuristic TargetHeuristic="FriendlyLandStructureHeuristic"/>\n'
        '    <Tactic id="Defend" Tactic="StaticDefense" EndBehavior="DISBAND" Distance="400" UpdateTime="1s"\n'
        '            CombatLeashSlack="1.5" UseAestheticsManager="false">\n'
    )


    def _state(micro, unit=WARRIOR, tactic='StaticDefense'):
        """tactic 'Hunt' (round 18): the attacking control, as benches/ai/targets/scenes.py#aistate_bench _hunt (Targetless, no target heuristic)."""
        head = HUNT_HEAD if tactic == 'Hunt' else DEFEND_HEAD
        return head + (
            f"""      <TeamTemplate MinUnits="2" MaxUnits="2" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"\n"""
            f"""                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"\n"""
            f"""                    MicroManager="{micro}">\n"""
            f"""        <ObjectFilter Rule="ANY">\n"""
            f"""          <IncludeThing>{unit}</IncludeThing>\n"""
            f"""        </ObjectFilter>\n"""
            f"""      </TeamTemplate>\n"""
            f"""    </Tactic>\n"""
            f"""  </AIStrategicStateDefinition>"""
        )


    BUILT_MONEY = 2000
    OPENER = 'CNVMicroOpener'
    OPENER_DEPOSIT = 1000
    BARRACKS_DY, PLANT_DY = -400.0, 400.0     # built: s1's factory south of its yard, its power plant north
    CONSCRIPT = 'SovietAntiInfantryInfantry'
    CONSCRIPT_DY = -80.0   # built: off the tree YP_Tree02 (3776, 2613) one stood on at 2 * BARRACKS_DY (test_maps)


    def _opener(unit, n=2):
        # as benches/ai/production/scenes.py#aitower_bench (retail AIOpener_A08_AlliedSpecialForces): a deposit, the builds; the Time order ends it
        return [f'  <SkirmishOpeningMove id="{OPENER}" Side="PlayerTemplate:Allies">',
                f'    <Order Time="0s" Account="PRODUCTION" Deposit="{OPENER_DEPOSIT}" />',
                *[f'    <Order Build="{unit}" />'] * n, '    <Order Time="90s"/>', '  </SkirmishOpeningMove>']


    SPOW_ID = 'CNVMicroSpow'


    def _spow_xml(use, engage=True):
        """B round 113 (UseSpecialPowers): StandardMicroManager with its chain (Base) flattened -- the type cannot be
        inherited from (aitarget_bench._micro_xml) -- only UseSpecialPowers set by the build; round 115: and
        EngageHostileTargets (aimicengoff)."""
        return (
            f"""  <AIMicroManagerData id="{SPOW_ID}" UpdateTime="0.5s" MaxTeamIdleTime="15s"\n"""
            f"""    MaxTeamIdleDistanceChange="50.0" MaxUnitIdleTime="10s" MaxUnitIdleDistanceChange="30.0"\n"""
            f"""    EnemySearchDistanceVisionMultiplier="1.8" MinTimeToKeepTempVisionRangeBonus="10s" SiegeWeaponBuffer="1.5"\n"""
            f"""    DodgeThreatsReactionTimeMin="0.5s" DodgeThreatsReactionTimeMax="0.5s" GatherTempVisionRangeBonus="1.5"\n"""
            f"""    RetreatTempVisionRangeBonus="1.5" MaxSecondaryDamageFraction="1.3" EngageHostileTargets="{'true' if engage else 'false'}"\n"""
            f"""    EngagePassiveTargets="true" EngageTacticalTarget="true" RetreatPowerAdvantage="0.2"\n"""
            f"""    RetreatMinDistanceFromBase="900.0" RetreatMinDistanceToFallback="500.0" AlphaStrikeTargetHealthPct="0.5"\n"""
            f"""    AlphaStrikeTargetTimeToKill="4.0" Crush="true" EnterGarrisons="true" EnterGarrisonableStructureDistance="150"\n"""
            f"""    EnterBaseDefensesWhenIdle="false" PullbackInjured="true" PullbackInjuredHealthPct="0.35" ReverseMove="true"\n"""
            f"""    DodgeThreats="true" UseSpecialPowers="{'true' if use else 'false'}">\n"""
            f"""    <RetreatBaseCriteria PreferredNotBaseTypes="CAPTURED" SortOrder="PREFER_CLOSEST"/>\n"""
            f"""    <IgnoreTargets Rule="ANY" Include="TIME_BOMB"/>\n"""
            f"""  </AIMicroManagerData>"""
        )


    def personality_xml(micro, unit=WARRIOR, tactic='StaticDefense', built=False, spow=None, engage=True):
        """built (round 19): the AI builds two `unit`s itself by an opening move. spow (round 113): None, or the
        UseSpecialPowers of this probe's own flattened StandardMicroManager (micro must then be SPOW_ID)."""
        removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in ab.INHERITED]
        first = []
        if built:
            removed += ['    <BuildState id="AlliedNeededUnits" xai:joinAction="Remove"/>']
            first = [f'    <OpeningMove Name="{OPENER}" Weight="100%">', '      <Heuristic>',
                     '        <ConstantHeuristic/>', '      </Heuristic>', '    </OpeningMove>']
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xai="uri:ea.com:eala:asset:instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml" />',
            '  </Includes>',
            *([_spow_xml(spow, engage)] if spow is not None else []),
            _state(micro, unit, tactic),
            *(_opener(unit) if built else []),
            f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{ab.BASE}">',
            *first,
            *removed,
            '    <StrategicState id="CNVStateMicro" State="CNVStateMicro"/>',
            '  </AIPersonalityDefinition>',
            '</AssetDeclaration>', ''])


    def mission(name, dist, micro='StandardMicroManager', health=100.0, hand=True, made=False, tactic='StaticDefense',
                xfer=False):
        facts = {'wake at': WAKE_AT, 'hand at': HAND_AT if hand or made else 0.0, 'distance': dist, 'health': health,
                 'hunt': float(tactic == 'Hunt')}
        m = Mission(name=name, map=resources.measured(niagara), facts=facts)
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
        m.assets.append((f'{PID}.xml', personality_xml(micro, tactic=tactic), f'AIPersonalityDefinition:{PID}'))
        m.cnv_units = (WARRIOR,)
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        m.spawns |= {WARRIOR}
        start, made_ = [], []
        m.cnv_named = {}       # part -> name of a unit the mission's scripts create (no cast role); the checks read it
        for k in range(2):
            dy = APART * (k - 0.5)
            w = f'UNIT - CNV AM Warrior {k + 1}'
            if made:           # created on s1's team by the script at HAND_AT, the AI awake
                m.waypoint(f'warrior {k + 1} spot', f'CNV AM Warrior Spot {k + 1}', 'east base', -WEST, dy)
                made_.append(w)
                m.cnv_named[f'warrior {k + 1}'] = w
            else:
                m.put(WARRIOR, 'east base', -WEST, dy, side='p1' if hand else 's1', angle=3.1416, name=w,
                      role=f'warrior {k + 1}')
            m.put(ENGINEER, 'east base', -WEST - dist, dy, name=f'UNIT - CNV AM Engineer {k + 1}',
                  role=f'engineer {k + 1}')
            if health < 100.0:
                start.append(('UNIT_SET_HEALTH', w, health))
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT),
                                          *([('SET_MILLISECOND_TIMER', 'CNV AI Hand', HAND_AT)] if hand or made else []),
                                          *start]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]
        # xfer: hand the new units to the AI brain again after they are made / change hands (round 18, l4_micro_gate.md:
        # the recruiters refuse a unit whose team is not the AI's own -- teamSoviet_1 -- and the wake's transfer saw only
        # the units there at the wake)
        again = [('UNIT_AI_TRANSFER_ALL', s1, 1)] if xfer else []
        if made:
            m.scripts.append(Script('CNV AI - Make', [('TIMER_EXPIRED', 'CNV AI Hand')],
                                    [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', w, WARRIOR, m.team('s1'),
                                      m.mark(f'warrior {k + 1} spot')) for k, w in enumerate(made_)] + again))
        elif hand:
            m.scripts.append(Script('CNV AI - Hand', [('TIMER_EXPIRED', 'CNV AI Hand')],
                                    [('NAMED_TRANSFER_OWNERSHIP_PLAYER', r.name, s1) for r in m.roles('warrior')] + again))
        return m


    def built_base(m, factory, money=BUILT_MONEY):
        """Round 19, the AI builds its units itself: s1's yard, `factory` south of it, a power plant north, the player's
        yard; a control spot west of the yard (the check makes a named unit there at the end) and the wake scripts."""
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put(factory, 'east base', 0, BARRACKS_DY, side='s1', name='UNIT - CNV AI Factory', role='ai factory')
        m.put('AlliedPowerPlant', 'east base', 0, PLANT_DY, side='s1', name='UNIT - CNV AI Plant', role='ai plant')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        m.waypoint('factory spot', 'CNV AI Factory Spot', 'east base', 0, BARRACKS_DY)
        m.waypoint('control spot', 'CNV AI Control Spot', 'east base', -WEST, 0)
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, money)]),
            # how many of the unit s1 owns, every frame (the mission's own counter; the check shows its own)
            Script('CNV AI - Owned', [], [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', m.cnv_units[0], s1, 'CNV_AI_Owned')],
                   once=False)]


    def built(name, tactic='StaticDefense', foes=None, spow=None, engage=True, unit=WARRIOR, factory='JapanBarracks',
              foe=CONSCRIPT):
        """tactic 'Hunt' (aimicbuilth): a membership test -- a Targetless Hunt team that takes the built warriors walks
        them off (the check counts them home round the barracks); no conscripts. foes (default: not Hunt) puts the
        conscripts in (aimicbuiltf: Hunt and conscripts -- recruited, with something to fight). spow (round 113,
        aimicspon / aimicspoff): the team's micro manager is SPOW_ID with UseSpecialPowers = spow; engage (round 115,
        aimicengoff): its EngageHostileTargets. unit / factory (benches/ai/tactics/scenes.py#aidelay_bench toggle builds): what the opener builds
        and the team takes instead of the warriors, and where from. foe: what stands in for the two conscripts."""
        hunt = tactic == 'Hunt'
        foes = not hunt if foes is None else foes
        facts = {'wake at': WAKE_AT, 'hand at': 0.0, 'distance': 0.0, 'health': 100.0, 'hunt': float(hunt), 'built': 1.0,
                 'foes': float(foes)}
        m = Mission(name=name, map=resources.measured(niagara), facts=facts)
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
        micro = 'StandardMicroManager' if spow is None else SPOW_ID
        if spow is not None:
            facts['use powers'] = float(spow)
            facts['engage hostile'] = float(engage)
        m.assets.append((f'{PID}.xml', personality_xml(micro, unit, tactic, built=True, spow=spow, engage=engage),
                         f'AIPersonalityDefinition:{PID}'))
        m.cnv_units = (unit,)
        m.spawns |= {unit}
        built_base(m, factory)
        if not foes:
            return m
        names = []
        for k in range(2):
            n = f'UNIT - CNV AM Conscript {k + 1}'
            names.append(n)
            m.put(foe, 'east base', APART * (k - 0.5), 2 * BARRACKS_DY + CONSCRIPT_DY, name=n,
                  role=f'conscript {k + 1}')
        m.scripts.append(Script('CNV AM - Go', [('COUNTER', 'CNV_AI_Owned', 3, 2)],
                                m.order('attack_move', names, m.mark('factory spot'), 'p1')))
        return m


    def update_time(name, seconds, observe=False):
        """Recruited, AI-built charge users; only AIMicroManagerData.UpdateTime differs.

        No claim that the period is a fixed first-response delay: qualification and
        the phase of the team's micro update also affect the first observed charge.
        observe adds the CNVTeams carrier for diagnosis, separately registered from
        the measured pair; host equivalence is unresolved (work/re/c_update_state_report.md).
        """
        m = built(name, tactic='Hunt', foes=True, spow=True)
        if observe:
            host_unit = aiteams_bench()["shared"].host_unit
            HOST = aiteams_bench()["shared"].HOST
            # Keep D's verified passive carrier and cadence identical in both builds.
            m.units.append(host_unit())
            m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
            m.ext = True
        m.assets = [(path, text.replace(f'id="{SPOW_ID}" UpdateTime="0.5s"',
                                       f'id="{SPOW_ID}" UpdateTime="{seconds}s"'), key)
                    for path, text, key in m.assets]
        m.facts['micro update seconds'] = float(seconds)
        return m


    def gather_bonus(name, bonus, keep=60):
        """The observed 0.5s probe (aimicupft) with GatherTempVisionRangeBonus = bonus and MinTimeToKeep = keep s, and
        one more conscript of the player's standing at the east gate, ~700-900 off the fight: past the warriors' search
        (vision 200 x 1.8 = 360), inside it times 3. Prediction: after the team has been in state 5 (gather), a bonus
        3 lists the far conscript as a hostile (the state stays 5 / 2 when the near two are dead), a bonus 1 never.
        Bench 11-25: so (bonus 3: 5 at f576 ~800 off it; bonus 1: 8 at f576, 5 at f664 ~400 off)."""
        m = update_time(name, 0.5, observe=True)
        m.assets = [(path, text.replace('GatherTempVisionRangeBonus="1.5"', f'GatherTempVisionRangeBonus="{bonus:g}"')
                     .replace('MinTimeToKeepTempVisionRangeBonus="10s"', f'MinTimeToKeepTempVisionRangeBonus="{keep:g}s"'),
                     key) for path, text, key in m.assets]
        m.put(CONSCRIPT, 'east gate', name='UNIT - CNV AM Far Conscript', role='far conscript')
        m.facts['gather bonus'], m.facts['bonus keep'] = float(bonus), float(keep)
        return m


    def engage_clock(name, enabled):
        """Engage pair on the repaired CNVTeams observer clock (MinFrames=15).

        Identical to the observed 0.5s micro-update probe except EngageHostileTargets.
        The passive carrier is retained in both sides; equivalence to a carrier-free
        mission remains a gap. Evidence: work/re/e107_engage_clock.md.
        """
        m = update_time(name, 0.5, observe=True)
        if not enabled:
            m.assets = [(path, text.replace('EngageHostileTargets="true"',
                                           'EngageHostileTargets="false"'), key)
                        for path, text, key in m.assets]
        m.facts['engage hostile'] = float(enabled)
        return m


    def keep_target(name, seconds=2, most=None):
        """Fixed nonzero keep duration on the existing observed Engage carrier.

        Min equals Max to remove the random interval from this clock measurement.
        Prediction: assignment at F expires at F + 15 * seconds; intervening
        state-2 passes hold, and the first pass at/after expiry may assign again.
        most: TimeToKeepTargetMax alone differs (aikeeprng), each record's keep drawn in [seconds, most] s.
        """
        m = engage_clock(name, True)
        m.assets = [(path, text.replace('EngageHostileTargets="true"',
                        f'EngageHostileTargets="true" TimeToKeepTargetMin="{seconds:g}s" '
                        f'TimeToKeepTargetMax="{most or seconds:g}s"'), key)
                    for path, text, key in m.assets]
        m.facts['keep seconds'] = seconds
        if most:
            m.facts['keep most'] = most
        return m


    def random_score(name, m):
        """RandomTargetScoreModifier only, on the zero-keep observed Engage carrier (aiegon): each state-2 pass every
        member re-picks; m = 0 keeps the pick the score's, a large m draws it (score x uniform(1/(1+m), 1+m))."""
        t = engage_clock(name, True)
        t.assets = [(path, text.replace('EngageHostileTargets="true"',
                        f'EngageHostileTargets="true" RandomTargetScoreModifier="{m:g}"'), key)
                    for path, text, key in t.assets]
        t.facts['random score'] = float(m)
        return t


    def dodge(name, enabled, reaction=0.5):
        """DodgeThreats only: recruited warriors fighting the same immortal conscripts.

        Native precision-strike beacon at 30 s, lifetime 4 s, DodgeSafetyDistance 200.
        No aircraft/bomb is dispatched: the beacon itself deals no damage or knockback.
        The check samples a published square before/during the beacon; this is not an
        exact reaction-time or safety-circle boundary measurement.
        """
        m = built(name, tactic='Hunt', foes=True, spow=False)
        m.assets = [(path, text.replace('DodgeThreats="true"',
                                       f'DodgeThreats="{str(enabled).lower()}"')
                              .replace('PullbackInjured="true"', 'PullbackInjured="false"')
                              .replace('DodgeThreatsReactionTimeMin="0.5s"', f'DodgeThreatsReactionTimeMin="{reaction:g}s"')
                              .replace('DodgeThreatsReactionTimeMax="0.5s"', f'DodgeThreatsReactionTimeMax="{reaction:g}s"'), key)
                    for path, text, key in m.assets]
        m.facts.update({'dodge reaction': reaction, 'dodge enabled': float(enabled), 'threat at': 30.0, 'threat lifetime': 4.0,
                        'sample half size': 150.0})
        m.cnv_named = {'beacon': 'CNV Dodge Beacon'}
        m.waypoint('dodge spot', 'CNV Dodge Spot', 'east base', 0, BARRACKS_DY - 100)
        m.spawns.add('AlliedPrecisionStrikeBeacon')
        m.scripts.append(Script('CNV Dodge - timer', [], [('SET_MILLISECOND_TIMER', 'CNV Dodge At', 30.0)]))
        m.scripts.append(Script('CNV Dodge - beacon', [('TIMER_EXPIRED', 'CNV Dodge At')],
                                [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', m.cnv_named['beacon'],
                                  'AlliedPrecisionStrikeBeacon', m.team('p1'), m.mark('dodge spot'))]))
        return m


    def ignore_distance(name, distance, observe=False):
        """Only the base-distance gate differs; unarmed engineers cannot provoke retaliation.

        INFERRED prediction: IgnoreTargets applies outside the specified base radius.
        This is a gate contrast, not a measurement of the exact retail 700 boundary.
        """
        m = built(name, tactic='Hunt', foes=False, spow=False)
        if observe:
            host_unit = aiteams_bench()["shared"].host_unit
            HOST = aiteams_bench()["shared"].HOST
            m.units.append(host_unit())
            m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
            m.ext = True
        m.facts.update({'ignore base distance': float(distance), 'target south of base': 500.0,
                        'target earliest at': 26.0})
        m.assets = [(path, text.replace('DodgeThreats="true"', 'DodgeThreats="false"')
                    .replace('PullbackInjured="true"', 'PullbackInjured="false"')
                    .replace('UseSpecialPowers="false"',
                             f'UseSpecialPowers="false" MinDistanceFromBaseToIgnoreTargets="{distance}"')
                    .replace('<IgnoreTargets Rule="ANY" Include="TIME_BOMB"/>',
                             '<IgnoreTargets Rule="ANY"><IncludeThing>AlliedEngineer</IncludeThing></IgnoreTargets>'),
                    asset) for path, text, asset in m.assets]
        m.cnv_named = {}
        actions = []
        for k in range(2):
            role = f'ignore target {k + 1}'
            target = f'UNIT - CNV Ignore Engineer {k + 1}'
            m.cnv_named[role] = target
            m.waypoint(role, f'CNV Ignore Spot {k + 1}', 'east base', APART * (k - 0.5), -500)
            actions.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', target, ENGINEER, m.team('p1'), m.mark(role)))
        m.spawns.add(ENGINEER)
        m.scripts += [Script('Ignore - delay', [], [('SET_MILLISECOND_TIMER', 'CNV Ignore Delay', 26.0)]),
                      Script('Ignore - targets', [('TIMER_EXPIRED', 'CNV Ignore Delay'),
                                                 ('COUNTER', 'CNV_AI_Owned', 3, 2)], actions)]
        return m


    def ignore_rule(name, rule, mask='Include="NEUTRAL_TECH TIME_BOMB"'):
        """Retail EASY inclusion mask, with only ANY/ALL varied on the same carrier.

        Engineers have neither NEUTRAL_TECH nor TIME_BOMB. ANY should allow them,
        ALL should ignore them; ordinary attacks may still bypass micro selection.
        The other masks: ANY Include ENGINEER ignores them; ALL Exclude ENGINEER
        does not (the Exclude kinds block before ALL lets everything through).
        Keep distance zero fixed; this does not reopen its paused boundary probe.
        """
        m = ignore_distance(name, 0, observe=True)
        m.assets = [(path, text.replace(
            '<IgnoreTargets Rule="ANY"><IncludeThing>AlliedEngineer</IncludeThing></IgnoreTargets>',
            f'<IgnoreTargets Rule="{rule}" {mask}/>'), asset)
            for path, text, asset in m.assets]
        return m


    MISSION = {'aikeeptwo': lambda: keep_target('CampAIKeepTwo'),
               'aikeeprng': lambda: keep_target('CampAIKeepRng', 1, 4),
               'airands0': lambda: random_score('CampAIRandS0', 0),
               'airandsx': lambda: random_score('CampAIRandSX', 1000),
               'aiignrany': lambda: ignore_rule('CampIgnRuleAny', 'ANY'),
               'aiignrall': lambda: ignore_rule('CampIgnRuleAll', 'ALL'),
               'aiignrinc': lambda: ignore_rule('CampIgnRuleInc', 'ANY', 'Include="ENGINEER"'),
               'aiignrexc': lambda: ignore_rule('CampIgnRuleExc', 'ALL', 'Exclude="ENGINEER"'),
               'aiegon': lambda: engage_clock('CampAIEgOn', True),
               'aiegoff': lambda: engage_clock('CampAIEgOff', False),
               'aimicupfast': lambda: update_time('CampMicUpFast', 0.5),
               'aimicupslow': lambda: update_time('CampMicUpSlow', 4),
               'aimicupft': lambda: update_time('CampMicObsFast', 0.5, observe=True),
               'aimicupst': lambda: update_time('CampMicObsSlow', 4, observe=True),
               'aigathb1': lambda: gather_bonus('CampGathBonus1', 1),
               'aigathb3': lambda: gather_bonus('CampGathBonus3', 3),
               'aiignzero': lambda: ignore_distance('CampAIIgnZero', 0),
               'aiignnear': lambda: ignore_distance('CampAIIgnNear', 2000),
               'aiignzt': lambda: ignore_distance('CampIgnObsZero', 0, observe=True),
               'aiignnt': lambda: ignore_distance('CampIgnObsNear', 2000, observe=True),
               'aidodgeon': lambda: dodge('CampAIDodgeOn', True),
               'aidodgeoff': lambda: dodge('CampAIDodgeOff', False),
               'aidodgezero': lambda: dodge('CampDodgeZero', True, 0),
               'aidodgetwo': lambda: dodge('CampDodgeTwo', True, 2),
               'aimicbuilt': lambda: built('CampAIMicBuilt'),
               'aimicbuilth': lambda: built('CampAIMicBltH', tactic='Hunt'),
               'aimicbuiltf': lambda: built('CampAIMicBltF', tactic='Hunt', foes=True),
               'aimicspon': lambda: built('CampAIMicSpOn', tactic='Hunt', foes=True, spow=True),
               'aimicspoff': lambda: built('CampAIMicSpOff', tactic='Hunt', foes=True, spow=False),
               'aimicengoff': lambda: built('CampAIMicEgOff', tactic='Hunt', foes=True, spow=True, engage=False),
               'aimicpre':lambda: mission('CampAIMicPre', 90.0, hand=False),
               'aimicnear': lambda: mission('CampAIMicNear', 90.0),
               'aimicmed': lambda: mission('CampAIMicMed', 90.0, 'StandardMicroManager_MEDIUM'),
               'aimicfar': lambda: mission('CampAIMicFar', 140.0),
               'aimichurt': lambda: mission('CampAIMicHurt', 140.0, health=70.0),
               'aimicmade': lambda: mission('CampAIMicMade', 90.0, hand=False, made=True),
               'aimichunt': lambda: mission('CampAIMicHunt', 90.0, hand=False, made=True, tactic='Hunt'),
               'aimicxfer': lambda: mission('CampAIMicXfer', 90.0, hand=False, made=True, xfer=True),
               'aimicnearx': lambda: mission('CampAIMicNearX', 90.0, xfer=True)}
    return dict(MISSION=MISSION, shared=SimpleNamespace(
        BARRACKS_DY=BARRACKS_DY, HAND_AT=HAND_AT, PID=PID, WAKE_AT=WAKE_AT, built=built,
        built_base=built_base, personality_xml=personality_xml, update_time=update_time,))


def aineutralgarr_bench():
    """NeutralGarrison selection: retail garrisonable row house versus neutral oil derrick.

    SDK AM_RowHouse01 inherits BaseCivilianStructureSmall (ContestableGarrisonContain).
    Garrison/Garrison_EASY consume GarrisonHeuristic. This isolates strategic selection
    with SimpleAttack; entering, occupancy, ownership and capacity remain gaps.
    Native selection in both builds is the existing map HV_Shop01 at (3180,2760).
    The added row house is eligible; the oil derrick is absent from the native
    candidate set. NamedObject identifies the placed control in both builds.
    See work/re/c_garrison_report.md.
    """
    from benches.ai.targets.scenes import aitargetpick_bench
    mission = aitargetpick_bench()["shared"].mission
    state_xml = aitargetpick_bench()["shared"].state_xml
    HOST = aiteams_bench()["shared"].HOST
    host_unit = aiteams_bench()["shared"].host_unit


    def garrison(real=True):
        m = mission('CampGarrOn' if real else 'CampGarrOff',
                    [('GarrisonHeuristic', None)], (0, 0, 0, 4))
        m.ext, m.ext_logs = True, ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
        m.put('AM_RowHouse01' if real else 'OilDerrick', 'east gate', -250, 0,
              side='neutral', name='UNIT - Garr Control', role='garr control')
        asset, xml, ref = m.assets[0]
        extra = ('<AITargetingHeuristic id="CNVGarrNamed" HeuristicType="NamedObject" '
                 'Name="UNIT - Garr Control" RequireUniqueTarget="false"/>\n'
                 + state_xml('CNVGarrNamedState', [('CNVGarrNamed', None)], 1))
        xml = xml.replace('<AIStrategicStateDefinition ', extra + '\n<AIStrategicStateDefinition ', 1)
        xml = xml.replace('    <StrategicState id="CNVStateTP" State="CNVStateTP"/>',
                          '    <StrategicState id="CNVStateTP" State="CNVStateTP"/>\n'
                          '    <StrategicState id="CNVGarrNamedState" State="CNVGarrNamedState"/>')
        m.assets[0] = asset, xml, ref
        return m


    RETAIL_GARRISON = (
        '<Tactic id="Garrison" Tactic="GarrisonBuilding" EndBehavior="DISBAND">\n'
        '      <TeamTemplate MinUnits="1" MaxUnits="2"\n'
        '                    RegisteredObjectSet="INFANTRY"\n'
        '                    IncludeKindOf="CAN_ATTACK INFANTRY" ExcludeKindOf="SKIRMISH_AI_DONT_GARRISON IGNORES_SELECT_ALL HARVESTER"\n'
        '                    Priority="STANDARD" AlwaysRecruit="false"\n'
        '                    MicroManager="StandardMicroManager"/>\n'
        '    </Tactic>'
    )


    def building():
        """aigarrbld: retail's Garrison state whole (SkirmishAI AIStateLibrary: GarrisonBuilding over GarrisonHeuristic,
        a team of 1-2 INFANTRY, EndBehavior DISBAND) for 2 Peacekeepers of s1 and no tanks; the row house of aigarron
        and the map's own shop are the two neutral candidates (B: does the team go in, which house, when)."""
        from benches.ai.targets.scenes import aitarget_bench
        INF = aitarget_bench()["shared"].INF
        m = mission('CampGarrBld', [('GarrisonHeuristic', None)], (0, 0, 0, 0), tanks=0)
        m.ext, m.ext_logs = True, ('target',)
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
        m.spawns |= {'HV_Shop01'}                    # the map's own shop, counted by template (published for the counter)
        m.put('AM_RowHouse01', 'east gate', -250, -150, side='neutral', name='UNIT - Garr Control', role='garr control')
        for k in range(2):
            m.put(INF, 'east base', -200.0, 160.0 + 70.0 * k, side='s1', angle=3.1416, name=f'UNIT - CNV AI Inf {k + 1}',
                  role=f'ai inf {k + 1}')
        asset, xml, ref = m.assets[0]
        start = xml.index('<Tactic id="Attack"')
        m.assets[0] = asset, xml[:start] + RETAIL_GARRISON + xml[xml.index('</Tactic>', start) + len('</Tactic>'):], ref
        return m


    MISSION = {'aigarron': garrison, 'aigarroff': lambda: garrison(False), 'aigarrbld': building}
    return dict(MISSION=MISSION)


@cache
def aiorders_bench():
    """Engine line D round 77: aiskcap (B's, missions/aiskirm_bench.py, unchanged) with ra3ext's CNVOrders module
    (`<DeletionUpdate id="ModuleTag_CNVOrders" .../>`, passive) added to a copy s1 already owns, so no template changes:

      aiskcapo: on the copied barracks CNVAIBarracks (aiskcap's own new template; only a behavior is added).
      aiskcapy: on a copy of the AI's construction yard (CNVOrdersYard) -- a template swap; on the bench (D 77) this
                changes the game: the new Peacekeepers stay at the cap of 2 to s168 (aiskcap: 3 at s150).

    Every frame the module hashes the AI brain's order registry and, when it changed (and every EVERY frames), logs each
    order (vtable, template id, state, kind, whether its id is in the UnitBuilder's vector) to the run folder's
    ra3ext.log. Question (B handoff 148, D 76): is the order that takes CNVNewPK past its SpecificUnitCap of 2 after ~s150
    a UnitBuilder order? Its check is benches/ai/tactics/checks.py#engine_aiorders (aiskcap's y).
    """
    import dataclasses
    import os

    import labpaths
    from missions.aiskirm_bench import NEW_BARRACKS, mission as aiskirm_mission
    from parts import Unit

    YARD, HOST, EVERY, LINES = 'AlliedConstructionYard', 'CNVOrdersYard', 150, 20000
    MODULE = f'<DeletionUpdate id="ModuleTag_CNVOrders" MinFrames="{EVERY}" MaxFrames="{LINES}"/>'


    def host_unit():
        x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Structures', YARD + '.xml'), encoding='utf-8').read()
        assert x.count(f'id="{YARD}"') == 1 and x.count('<Behaviors>') == 1
        x = x.replace(f'id="{YARD}"', f'id="{HOST}"').replace('<Behaviors>', f'<Behaviors>\n\t\t\t{MODULE}')
        return Unit(HOST, x, names=dict(unit=HOST), what='原建造厂附带被动 AI 单表日志（CNVOrders）', params=dict(every=EVERY))


    def on_yard():
        m = aiskirm_mission('CampAISkCapY2', new=True, cap=2)
        ai_yard = [o for o in m.objects if o.template == YARD and o.side == 's1']
        assert len(ai_yard) == 1
        m.objects[m.objects.index(ai_yard[0])] = dataclasses.replace(ai_yard[0], template=HOST)
        for role in m.cast.values():
            if role.template == YARD and role.side == 's1':
                role.template = HOST
        m.units.append(host_unit())
        m.ext = True
        return m


    def on_barracks():
        m = aiskirm_mission('CampAISkCapO', new=True, cap=2)
        (u,) = [u for u in m.units if u.id == NEW_BARRACKS]
        assert u.xml.count('<Behaviors>') == 1
        u.xml = u.xml.replace('<Behaviors>', f'<Behaviors>\n\t\t\t{MODULE}')
        m.ext = True
        return m


    DEFENSE, DEFENSE_AT = 'AlliedBaseDefense', (-300.0, 300.0)   # from the east base: west of the copied barracks
    POWER, POWER_AT = 'AlliedPowerPlant', ((-300.0, -150.0), (-300.0, -350.0))


    def with_power(defense):
        """aiskcapp / aiskcapd (D 79, H4): aiskcapo + s1 owns two retail power plants from the start, and (aiskcapd) a
        retail AlliedBaseDefense. In aiskcapo the AI's first building of that kind comes at ~s150, when CNVNewPK goes past
        its cap; owned from s0, is the overrun gone? (The plants: the defense alone leaves the AI underpowered -- first
        try, D 79: the barracks stopped at s112 -- so aiskcapp is the control with the same plants.)"""
        m = on_barracks()
        m.name = 'CampAISkCapD' if defense else 'CampAISkCapP'
        m.facts['owned power'] = len(POWER_AT)
        for k, (x, y) in enumerate(POWER_AT):
            m.put(POWER, 'east base', x, y, side='s1', angle=0.0, name=f'UNIT - CNV AI Power {k}', role=f'ai power {k}')
        if defense:
            m.facts['owned defense'] = 1
            m.put(DEFENSE, 'east base', DEFENSE_AT[0], DEFENSE_AT[1], side='s1', angle=3.1416,
                  name='UNIT - CNV AI Defense', role='ai defense')
        return m


    TEAMS = '<DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="20000"/>'


    def with_teams():
        """aiskcapt (D 85, H5 / H6 of d79): aiskcapo with the copied barracks also carrying CNVTeams (team / tstate lines of
        its owner s1 and, while it watches, the AI's command lines `cmd ... src=`): which team, by which command, asks for
        the overrun Peacekeepers of the second wave (s130-s165), and are the first wave's two in a team by then?"""
        m = on_barracks()
        m.name = 'CampAISkCapT'
        (u,) = [u for u in m.units if u.id == NEW_BARRACKS]
        u.xml = u.xml.replace('<Behaviors>', f'<Behaviors>\n\t\t\t{TEAMS}', 1)
        return m


    MISSION = {'aiskcapo': on_barracks, 'aiskcapd': lambda: with_power(True), 'aiskcapp': lambda: with_power(False),
               'aiskcapy': on_yard, 'aiskcapt': with_teams}
    return dict(MISSION=MISSION, shared=SimpleNamespace(MODULE=MODULE))


def aipassive_distance_bench():
    """Passive search radius contrast; raw team states distinguish selection from damage.

    The side plant is 250 west of the route, outside the Peacekeepers' weapon range.
    EngageTacticalTarget is disabled; the named far plant only drives the tactic's
    movement. INFERRED predictions: 0 disables passive selection, 200 misses the
    side plant and 600 permits it. Zero semantics and distance origin are unproven.
    See work/re/e104_passive_distance.md for predictions and same-run evidence.

    MEASURED: 0/1/200/600 all select the side plant at logic frame 140, with
    four members, state 6; state 0 begins at 320. This route does not expose a
    consumer of the field. The predicted distance contrast was rejected; do not
    infer a global no-op or add a cutoff to the model from the field's name.
    """
    ar = airetreat_bench()["shared"]
    host_unit = aiteams_bench()["shared"].host_unit
    HOST = aiteams_bench()["shared"].HOST


    def mission(name, distance):
        m = ar.mission(name, side=True, PassiveTargetSearchDistance=str(distance),
                       EngagePassiveTargets='true', EngageTacticalTarget='false',
                       UseSpecialPowers='false', DodgeThreats='false',
                       PullbackInjured='false', EnterGarrisons='false',
                       EnterBaseDefenses='false', ReverseMove='false')
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
        m.ext = True
        m.facts['passive search distance'] = distance
        return m


    MISSION = {
        'aipsdz': lambda: mission('CampPasZero', 0),
        'aipsdt': lambda: mission('CampPasTiny', 1),
        'aipsds': lambda: mission('CampPasSmall', 200),
        'aipsdl': lambda: mission('CampPasLarge', 600),
    }
    return dict(MISSION=MISSION)


def aipathcheck_bench():
    """Engine line D round 152: AIStrategicStateDefinition.PathfindingCheckType (24 retail uses, 23 of them None; read
    back by benches/ai/tactics/checks.py#engine_aipathcheck; RA3-EngineModel ra3model/ai/tactics.py _path_check).

    The program (work/re d62_b_fields.md 1): the tactic's periodic check, once its teams are idle, puts every ground
    member with no way to the target (QuickDoesPathExist) or to a spot in its weapon's reach (QuickDoesAttackPathExist)
    back in the player's default team; a team left empty ends the tactic. None: no check. Not written: the tactic class's
    default (SimpleAttack: QuickDoesAttackPathExist).

    ainamed_bench's ainmfar (2-4 Peacekeepers by SimpleAttack, EndBehavior RAMPAGE, at a NamedObject) aimed at the
    player's yard on the west bank, with Niagara's bridges taken away (aiopath_bench.disconnected: no land way across);
    a passive CNVTeams host logs the team's members; the player's three turrets are taken away. The four builds differ in the state's PathfindingCheckType only:
      aipfdef    not written (the class default, QuickDoesAttackPathExist)
      aipfatk    QuickDoesAttackPathExist
      aipfpath   QuickDoesPathExist
      aipfnone   None -- the team keeps its members on the east bank
    Facts: wake at; 'path check' (the value, '' not written).
    """
    import types

    from benches.ai.targets.scenes import ainamed_bench
    an = ainamed_bench()["shared"]
    _host = aiteamfields_bench()["shared"]._host

    YARD = 'UNIT - CNV AI Player Yard'
    STATE = '<AIStrategicStateDefinition id="CNVStateGo" MaxTargets="1"'


    def _no_bridges(m):
        cp = types.ModuleType(m.map.__name__)
        cp.__dict__.update(vars(m.map))
        cp.BRIDGES = []
        cp.OBJECTS = [o for o in cp.OBJECTS if o.template != 'HB_Bridge_02']
        m.map = cp


    def mission(mod, check=''):
        m = an.mission(mod, 'NamedObject', YARD)
        (fname, xml, asset), = m.assets
        assert xml.count(STATE) == 1
        if check:
            xml = xml.replace(STATE, f'{STATE} PathfindingCheckType="{check}"')
        m.assets = [(fname, xml, asset)]
        _no_bridges(m)
        # the player's turrets (two at the east gate on the team's way, one by the yard) go: nothing should shoot the team
        m.objects = [o for o in m.objects if 'Turret' not in o.name]
        m.cast = {k: r for k, r in m.cast.items() if 'turret' not in k}
        m.facts['path check'] = check
        return _host(m)


    MISSION = {
        'aipfdef': lambda: mission('CampAIPfDef'),
        'aipfatk': lambda: mission('CampAIPfAtk', 'QuickDoesAttackPathExist'),
        'aipfpath': lambda: mission('CampAIPfPath', 'QuickDoesPathExist'),
        'aipfnone': lambda: mission('CampAIPfNone', 'None'),
    }
    return dict(MISSION=MISSION)


@cache
def aipullback_bench():
    """Engine probe: the skirmish AI team's PullbackInjured and ReverseMove (engine line B, layer 4; read back by
    benches/ai/tactics/checks.py#engine_aipullback; model: an injured member (health ratio < PullbackInjuredHealthPct, MEDIUM 0.35) leaves the
    team for the AI's nearest VehicleRepairFacility (ArmyDefAllied: AlliedWarFactory); a member whose distance d to its
    target is 0 < d < longest range - 10 backs up to range - 10 from it, staying in the team).

    aicrush_bench's aicrush0 (Crush false; 4 Hammers against 12 Peacekeepers round the far plant -- the tanks are shot at
    and some get hurt) with:
      aipull1   an AlliedWarFactory of s1 beside the base yard; PullbackInjured true (default) -> the model: a hurt tank goes home
      aipull0   the same, PullbackInjured false -> they stay at the far plant
      airev1    no factory; ReverseMove true (default)
      airev0    no factory; ReverseMove false
    Facts: wake at.
    """
    ac = aicrush_bench()["shared"]

    FACTORY = 'AlliedWarFactory'
    FACTORY_NAME = 'UNIT - CNV AI War Factory'
    REPAIR = {'Soviet': 'SovietCrane', 'Japan': 'JapanWarFactory'}   # ArmyDef*.xml VehicleRepairFacility
    FACTORY_AT = (0.0, 300.0)              # off the yard's east base site, clear of the yard and the tanks' way west


    CLOSE_AT = (-360.0, 0.0)               # airevp*: the far plant moved here off 'east base' -- 100 west of the tanks'
                                           # column (-260, -90..90): every tank 100-135 from its centre, well in range
    TURRET = 'AlliedBaseDefense'           # airevt*: a hostile target -- the plant is only a tactical one (state 6), and
    TURRET_NAME = 'UNIT - CNV AI Rev Turret'   # the reverse-move routine runs in states 2 and 4 only (work/re l4_micro_engage 1.4)
    TURRET_AT = (-340.0, 0.0)              # 80-120 from the tanks
    TURRET_PLANT_AT = (-480.0, 0.0)        # the plant behind it, out of the way
    FOE = 'AlliedAntiVehicleVehicleTech1'  # airevk*: the player's Guardian tanks, a moving unit target (work/re/d131 1)
    FOE_AT = ((-305.0, -60.0), (-305.0, 60.0))   # ~54 centre to centre from each of the column's tanks (-260, -90..90),
                                           # far inside the reverse gate d < R - 10 (cannon AttackRange 150: R 145)
    BEAR = 'SovietScoutInfantry'           # airevb*: war bears, they bite infantry only (no hostile can fire at a tank)
    BEAR_AT = ((-200.0, 320.0), (-320.0, 320.0))   # north of the column (-260, -90..90), 230+ off its nearest tank


    def mission(mod, factory=False, faction=None, close=False, observe=False, **fields):
        """faction 'Soviet' / 'Japan': s1 that faction's player, its repair place that faction's VehicleRepairFacility
        (REPAIR) -- the pull-back looks the ArmyDefinition up by the player's faction (its Side; work/re handoff-b 71).
        close: no guards, and the team's target (the far plant) stands beside the tanks at the start (CLOSE_AT) -- the
        ReverseMove read (work/re/l4_micro_engage.md 1.4): a member 0 < d < range - 10 from its target backs off to range - 10.
        close='turret': a player's turret beside the tanks instead (TURRET_AT), the plant behind it.
        close='unit': two of the player's Guardian tanks beside the tanks (FOE_AT), the far plant where it was.
        close='bear': two of the player's war bears off the tanks' way (BEAR_AT), the far plant where it was."""
        m = ac.mission(mod, observe=observe, Crush='false', **fields)
        if close:
            m.objects = [o for o in m.objects if not o.name.startswith('UNIT - CNV AI Guard')]
            m.cast = {k: r for k, r in m.cast.items() if not k.startswith('guard ')}
        if close in ('unit', 'bear'):
            foe, at = (FOE, FOE_AT) if close == 'unit' else (BEAR, BEAR_AT)
            m.spawns |= {foe}
            for k, (dx, dy) in enumerate(at):
                m.put(foe, 'east base', dx, dy, angle=0.0, name=f'UNIT - CNV AI Rev Foe {k + 1}', role=f'rev foe {k + 1}')
        elif close:
            o = m.find(m.role('far plant').name)
            o.x, o.y = m.site('east base', *(TURRET_PLANT_AT if close == 'turret' else CLOSE_AT))[:2]
            if close == 'turret':
                m.put(TURRET, 'east base', *TURRET_AT, name=TURRET_NAME, role='rev turret')
        if faction:
            m.sides['s1'] = dict(m.sides['s1'], playerFaction=f'PlayerTemplate:{faction}')
        if factory:
            m.put(REPAIR.get(faction, FACTORY), 'east base', *FACTORY_AT, side='s1', name=FACTORY_NAME, role='ai factory')
        return m


    GUARDIAN = 'AlliedAntiVehicleVehicleTech1'


    def guardians(m, tank=GUARDIAN, angle=None):
        """The AI's Hammers swapped for Allied Guardian tanks (as aicrush_bench swaps Peacekeepers for Hammers), or for
        `tank`; angle (radians): the tanks' starting facing instead of west."""
        (fname, xml, asset), = m.assets
        m.assets = [(fname, xml.replace(f'<IncludeThing>{ac.TANK}</IncludeThing>',
                                        f'<IncludeThing>{tank}</IncludeThing>'), asset)]
        for o in m.objects:
            if o.template == ac.TANK:
                o.template = tank
                if angle is not None:
                    o.angle = angle
        m.cast = {k: (r.__class__(tank, r.name, r.side) if r.template == ac.TANK else r) for k, r in m.cast.items()}
        m.cnv_units = (m.cnv_units[0], tank)
        m.spawns |= {tank}
        return m


    APOCALYPSE = 'SovietAntiVehicleVehicleTech3'
    CONSCRIPT = 'SovietAntiInfantryInfantry'


    SECOND = 's6'                          # airevidx: a second AI side, a player index of its own (s1 logs index=4)
    SECOND_AT = (450.0, -500.0)            # its yard off 'east base' (4300, 2900), its four tanks 260 west of it


    def second_ai(m, side=SECOND, at=SECOND_AT):
        """B round 196 (handoff-b 195 C3): a second AI side with s1's faction and personality, its yard, four tanks and a
        teams host laid out as s1's are (`at` off 'east base'), woken with s1 -- do the slot team's first draw (s1 f16) and
        its fill (s1 f21 = draw + 5) move with the player index?"""
        from parts import Script
        HOST = aiteams_bench()["shared"].HOST
        m.sides[side] = dict(m.sides['s1'])
        ox, oy = at
        k = 0
        for o in list(m.objects):
            if o.side != 's1':
                continue
            dx, dy = o.x - 3850.0, o.y - 3400.0           # off 'east base', as mission() placed them
            k += 1
            kw = {} if getattr(o, 'angle', None) is None else {'angle': o.angle}
            m.put(o.template, 'east base', ox + dx, oy + dy, side=side, name=f'UNIT - CNV AI2 {k}' if o.name else '',
                  role=f'second ai {k}' if o.name else '', **kw)
        p = m.player(side)
        base = 'CNV AI Base 2'
        m.waypoint('ai base 2', base, 'east base', ox, oy)
        m.scripts += [
            # run 1 (B196): s6's units stayed in the map's teamSoviet_6 (s1's are in defaultSkirmishTeamSoviet_1 from f1),
            # so nothing was recruited before the wake's transfer (f151 -> full f152): hand them over at the start
            Script('CNV AI2 - Start', [], [('PLAYER_SET_MONEY', p, 0), ('UNIT_AI_TRANSFER_ALL', p, 1)]),
            Script('CNV AI2 - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', p, 1), ('SKIRMISH_AI_MAKE_BASE', p, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', p, 20), ('SKIRMISH_AI_USE_REPAIRS', p, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', p, 0), ('PLAYER_SET_MONEY', p, 0)])]
        assert any(o.template == HOST and o.side == side for o in m.objects)
        return m


    MISSION = {
        'aipull1':lambda: mission('CampAIPull1', factory=True),
        'aipull0': lambda: mission('CampAIPull0', factory=True, PullbackInjured='false'),
        # the first aipull1 run: no tank went home (a tank shot down from 35 % in under one 2 s micro update?) -- so the
        # check's script sets the tanks to HURT % at HURT_AT, on the road, before the fight (benches/ai/tactics/checks.py#engine_aipullback)
        'aipullh1': lambda: mission('CampAIPullH1', factory=True),
        'aipullh0': lambda: mission('CampAIPullH0', factory=True, PullbackInjured='false'),
        # aipullh1 too: no tank went home -- the same with the AI's own faction's tank (an Allied AI, Soviet Hammers)
        'aipullga': lambda: guardians(mission('CampAIPullGa', factory=True)),
        # the garrison routine's gates all pass statically (work/re handoff-b 69): hurt the tanks at the wake, ~1000 from any enemy
        # (no AlphaStrike state 0), with a health counter (did UNIT_SET_HEALTH take?); aipullr1 also turns the AI's
        # repair switch on (aitarget_bench's wake sets SKIRMISH_AI_USE_REPAIRS 0)
        'aipulli1': lambda: mission('CampAIPullI1', factory=True),
        'aipullr1': lambda: mission('CampAIPullR1', factory=True),
        # aipulli1 / r1 no tank went home: hurt BEFORE the wake (the tanks idle ~400 from the factory) and count 近家
        # (within 600) for 到远厂 -- a tank sent home then recruited again would linger near home
        'aipullp1': lambda: mission('CampAIPullP1', factory=True),
        # aipullp1 none either (they join the team at 30 % and drive off): is Body slot 0x40 a 0..1 ratio? any health
        # passes a PullbackInjuredHealthPct this big
        'aipullbig': lambda: mission('CampAIPullBig', factory=True, PullbackInjuredHealthPct='100000.0'),
        # aipulli1 with a Soviet AI and a SovietCrane: the lookup is by faction (s1 Allied -> AlliedArmy, AlliedWarFactory,
        # as the probe has it) -- does another faction / facility draw them home?
        'aipullsov': lambda: mission('CampAIPullSov', factory=True, faction='Soviet'),
        'aipulljp': lambda: mission('CampAIPullJp', factory=True, faction='Japan'),
        'airev1': lambda: mission('CampAIRev1'),
        'airev0': lambda: mission('CampAIRev0', ReverseMove='false'),
        # Identical passive carriers on both sides; body heading and goal object are
        # observations, while region counts alone cannot identify reverse travel.
        'airev1t': lambda: mission('CampAIRev1T', observe=True),
        'airev0t': lambda: mission('CampAIRev0T', observe=True, ReverseMove='false'),
        # B round 196: airev1t with a second AI side (s6, its own index) laid out the same -- the recruit delay by index
        'airevidx': lambda: second_ai(mission('CampAIRevIdx', observe=True)),
        # A round 227: airev1t's form-up with another locomotor -- the turn in place (Hammer TurnTimeSeconds 1.25 s:
        # 19 deg / frame on the bench). Guardians (1.0 s) start facing north-west, so the go order turns them < 90 deg
        # (TurnThresholdHS 90: do they drive while turning?); Apocalypses (3 s) as airev1t, facing west
        'airevgt': lambda: guardians(mission('CampAIRevGT', observe=True), angle=-2.3562),
        'airevat': lambda: guardians(mission('CampAIRevAT', observe=True), tank=APOCALYPSE),
        # A round 231: airev1t's form-up with infantry -- Conscripts (TestReactiveLocomotorHUMAN, TurnTimeSeconds 0.5 s,
        # no TurnThresholdHS; Peacekeepers and every engineer walk on it too), facing west as airev1t (the form-up turn
        # ~150 deg): do they turn in place before they walk, as the tanks do, and at 48 deg a frame?
        'airevit': lambda: guardians(mission('CampAIRevIT', observe=True), tank=CONSCRIPT),
        # airev1 / 0 too alike: the target beside the tanks from the start, no guards (handoff-b 69's measure)
        'airevp1': lambda: mission('CampAIRevP1', close=True),
        'airevp0': lambda: mission('CampAIRevP0', close=True, ReverseMove='false'),
        # B 11-23: airevp1 observed (the host: ra3ext alone logs no cmd: lines here): the simulator's AI casts its
        # precision strike f166 at the plant, counting its own four Hammers 100 off -- does the game (24e / 1fe / 1ff)?
        'airevp1t': lambda: mission('CampAIRevP1T', close=True, observe=True),
        # airevp1 / 0 alike (no back-up): a plant is a tactical target, the team in state 6. A hostile turret instead, and
        # state 2 forced: CleanupPowerAdvantage out of reach (no state 3), UseGatherState off (no state 5)
        'airevt1': lambda: mission('CampAIRevT1', close='turret', CleanupPowerAdvantage='1000.0', UseGatherState='false'),
        'airevt0': lambda: mission('CampAIRevT0', close='turret', CleanupPowerAdvantage='1000.0', UseGatherState='false',
                                   ReverseMove='false'),
        # D round 132 (work/re/d131_triggers.md 1): airevt's state 2 with a MOVING target of the player's, ~54 centre to
        # centre (a structure's radius kept the centre distance outside d < R - 10), the host observed (aim / dest / hd)
        'airevk1': lambda: mission('CampAIRevK1', close='unit', observe=True, CleanupPowerAdvantage='1000.0',
                                   UseGatherState='false'),
        'airevk0': lambda: mission('CampAIRevK0', close='unit', observe=True, CleanupPowerAdvantage='1000.0',
                                   UseGatherState='false', ReverseMove='false'),
        # D round 182: airevk1 with the two foes' health % read before the frame's keep (how the near foe dies s13)
        'airevkh': lambda: mission('CampAIRevKH', close='unit', observe=True, CleanupPowerAdvantage='1000.0',
                                   UseGatherState='false'),
        # the same with the AI's own Guardians (another weapon template: d131 1 gate 4, the weapon field not read)
        'airevkg1': lambda: guardians(mission('CampAIRevKG1', close='unit', observe=True,
                                              CleanupPowerAdvantage='1000.0', UseGatherState='false')),
        # D round 133: airevk1's start (the team forms f213, state 2 f242 with aim = a far foe 166+ off), then at LATE_AT
        # the check deletes the two foes and spawns one of the player's Guardians on each Hammer (checks/engine_aipullback
        # LATE_*): every member's nearest -- and only -- foe a few tens off, far inside d < R - 10 = 135
        'airevk2': lambda: mission('CampAIRevK2', close='unit', observe=True, CleanupPowerAdvantage='1000.0',
                                   UseGatherState='false'),
        'airevk2o': lambda: mission('CampAIRevK2Off', close='unit', observe=True, CleanupPowerAdvantage='1000.0',
                                    UseGatherState='false', ReverseMove='false'),
        # D round 135b ("注入摆"): airevk1 / 0 as they are (nothing deleted or spawned), plus the host's CNVCmd; the check's
        # plan moves the two foes beside the two team members at f250 (checks/engine_aipullback POKE_*)
        'airevkp1': lambda: mission('CampAIRevKP1', close='unit', observe='cmd', CleanupPowerAdvantage='1000.0',
                                    UseGatherState='false'),
        'airevkp0': lambda: mission('CampAIRevKP0', close='unit', observe='cmd', CleanupPowerAdvantage='1000.0',
                                    UseGatherState='false', ReverseMove='false'),
        # B 11-24 SiegeWeaponBuffer (work/re l4_micro_retreat.md 1.1): airev1t with two war bears for the guards, off the
        # tanks' way -- 1.5 x a bear's reach is under the Hammer's 150: state 4, each tank attacks the nearest bear;
        # at 1000 no siege, UseGatherState on: state 5
        'airevb1': lambda: mission('CampAIRevB1', close='bear', observe=True, CleanupPowerAdvantage='1000.0'),
        'airevb0': lambda: mission('CampAIRevB0', close='bear', observe=True, CleanupPowerAdvantage='1000.0',
                                   SiegeWeaponBuffer='1000.0'),
    }
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


def aipullpct_bench():
    """Pullback health threshold only: keep aipullsov's Soviet AI and Crane.

    Prediction before measurement: at scripted 30% health, 0.2 does not trigger
    pullback yet; 0.5 does. Later combat may take the low lane below 20%, so this
    does not predict that it can never return. All other mission settings match.
    """
    mission = aipullback_bench()["shared"].mission


    MISSION = {
        'aipullpctlo': lambda: mission('CampPullPctLo', factory=True, faction='Soviet',
                                     PullbackInjuredHealthPct='0.2'),
        'aipullpcthi': lambda: mission('CampPullPctHi', factory=True, faction='Soviet',
                                     PullbackInjuredHealthPct='0.5'),
    }
    return dict(MISSION=MISSION)


@cache
def aireactive_bench():
    """Engine probe: the skirmish AI's ReactiveDefense tactic and the personality's ReactiveDefenseRadius (read back by
    benches/ai/tactics/checks.py#engine_aireactive; engine line B round 199).

    Same setup as aidefense_bench's non-far builds: s1 (Allied AI) owns its yard at 'east base' and four Peacekeepers
    beside it, the player has only its yard at 'base yard', s1's money is 0, the AI wakes at WAKE_AT (the retail wake
    actions, MAKE_BASE included). The personality is the Allied co-op base with every inherited strategic state removed
    and one state, always on: a Targetless ReactiveDefense tactic (EndBehavior DISBAND, aesthetics off) with a team of 2-4
    Peacekeepers. The AIPersonalityDefinition carries ReactiveDefenseRadius = R.
    One player Peacekeeper (the 'foe') stands FOE_DIST straight south of the AI yard on open grass (aidefense's OUT
    direction), facing north, owner p1. Between the radii: 750 < 1000 < 1200.
    Builds:
      aireact750   R = 750   (the foe is outside the radius)
      aireact1200  R = 1200  (inside)
    """
    import resources
    from maps import niagara
    from benches.ai.targets.scenes import aistate_bench
    ab = aistate_bench()["shared"]
    from parts import Mission, Script

    WAKE_AT = 10.0
    FOE_DIST = 1000.0
    PID = 'CNVReactiveTest'
    INF = ab.INF


    def _state():
        return (
            f"""  <AIStrategicStateDefinition id="CNVStateGo" MaxTargets="1">\n"""
            f"""    <Heuristic>\n"""
            f"""      <ConstantHeuristic/>\n"""
            f"""    </Heuristic>\n"""
            f"""    <Tactic id="Defend" Tactic="ReactiveDefense" Targetless="true" EndBehavior="DISBAND"\n"""
            f"""            UseAestheticsManager="false">\n"""
            f"""      <TeamTemplate MinUnits="2" MaxUnits="4" IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"\n"""
            f"""                    AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD" AlwaysRecruit="false"\n"""
            f"""                    MicroManager="StandardMicroManager_MEDIUM">\n"""
            f"""        <ObjectFilter Rule="ANY">\n"""
            f"""          <IncludeThing>{INF}</IncludeThing>\n"""
            f"""        </ObjectFilter>\n"""
            f"""      </TeamTemplate>\n"""
            f"""    </Tactic>\n"""
            f"""  </AIStrategicStateDefinition>"""
        )


    def personality_xml(radius):
        removed = [f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in ab.INHERITED]
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xai="uri:ea.com:eala:asset:instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{ab.BASE}.xml" />',
            '  </Includes>',
            _state(),
            f'  <AIPersonalityDefinition id="{PID}" PersonalityType="{PID}" inheritFrom="{ab.BASE}"'
            f' ReactiveDefenseRadius="{int(radius)}">',
            *removed,
            '    <StrategicState id="CNVStateGo" State="CNVStateGo"/>',
            '  </AIPersonalityDefinition>',
            '</AssetDeclaration>', ''])


    def mission(name, radius):
        m = Mission(name=name, map=resources.measured(niagara), facts={'wake at': WAKE_AT, 'radius': radius})
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{PID}'}
        m.assets.append((f'{PID}.xml', personality_xml(radius), f'AIPersonalityDefinition:{PID}'))
        m.cnv_units = (INF,)
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        m.spawns |= {INF}
        for k in range(4):
            m.put(INF, 'east base', -100.0, -90.0 + 60.0 * k, side='s1', angle=3.1416, name=f'UNIT - CNV AI Inf {k + 1}',
                  role=f'peacekeeper {k + 1}')
        m.put(INF, 'east base', 0.0, -FOE_DIST, angle=1.5708, name='UNIT - CNV RD Foe', role='foe')
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)])]
        return m


    MISSION = {'aireact750': lambda: mission('CampAIReact750', 750),
               'aireact1200': lambda: mission('CampAIRea1200', 1200)}
    return dict(MISSION=MISSION, shared=SimpleNamespace(FOE_DIST=FOE_DIST, _state=_state))


@cache
def airelease_bench():
    """C independent release pair: two fixed Guardians, defense then timed attack.

    Only the defense TeamTemplate.ReleaseType differs. A passive CNVTeams host
    records actual team identity and members; legacy named counters are diagnostic.
    """
    import os

    import labpaths
    from parts import Unit
    team_mission = aiteamfilter_bench()["shared"].mission
    from missions.aiskirm_bench import ai_map


    def mission(never):
        m = team_mission('CampAIRel',
                         tanks=2, inf=0, max_units=2, static=True,
                         kinds='IncludeKindOf="VEHICLE"')
        m.name = 'CampAIRelNever' if never else 'CampAIRelPrio'
        m.map = ai_map(m.map, library=False)
        filename, xml, asset = m.assets[0]
        release = 'NEVER_RELEASE' if never else 'RELEASE_TO_PRIORITY'
        xml = xml.replace('<TeamTemplate ', f'<TeamTemplate ReleaseType="{release}" ', 1)
        attack = (
            '  <AIStrategicStateDefinition id="CNVReleaseAttack" MaxTargets="1">\n'
            '    <Heuristic><TimerHeuristic StartTime="35s" EndTime="-1s"/></Heuristic>\n'
            '    <TargetHeuristic TargetHeuristic="ClosestStructureHeuristic"/>\n'
            '    <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE">\n'
            '      <TeamTemplate MinUnits="2" MaxUnits="2" IncludeKindOf="VEHICLE"\n'
            '        AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD"\n'
            '        MicroManager="StandardMicroManager_MEDIUM"/>\n'
            '    </Tactic>\n'
            '  </AIStrategicStateDefinition>\n'
        )
        xml = xml.replace('  <AIPersonalityDefinition ', attack + '  <AIPersonalityDefinition ')
        xml = xml.replace('    <StrategicState id="CNVStateTF" State="CNVStateTF"/>',
                          '    <StrategicState id="CNVStateTF" State="CNVStateTF"/>\n'
                          '    <StrategicState id="CNVReleaseAttack" State="CNVReleaseAttack"/>')
        m.assets[0] = filename, xml, asset
        m.map.AI_TEAMS.update({'release defense': 'Soviet_1/CNVStateTF_StaticDefense_0_0',
                               'release attack': 'Soviet_1/CNVReleaseAttack_SimpleAttack_0_0'})
        m.facts.update({'never release': int(never), 'attack at': 35.0})
        # Same passive carrier as D's engine_aiteams.host_unit; keep content here
        # so the C check consumes only the mission interface (G5).
        plant, host = 'AlliedPowerPlant', 'CNVReleaseHost'
        with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Structures', plant + '.xml'),
                  encoding='utf-8') as f:
            xml = f.read()
        assert xml.count(f'id="{plant}"') == 1 and xml.count('<Behaviors>') == 1
        xml = xml.replace(f'id="{plant}"', f'id="{host}"').replace(f'EditorName="{plant}"', f'EditorName="{host}"')
        xml = xml.replace('<Behaviors>', '<Behaviors>\n'
                          '  <DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="4000"/>')
        m.units.append(Unit(host, xml, names=dict(unit=host),
                            what='被动队伍日志电厂：每15帧记录AI队员和激活状态', params=dict(of=plant, every=15)))
        m.put(host, 'east base', 250.0, 400.0, side='s1', role='teams host')
        m.ext = True
        return m


    MISSION = {'airelnever': lambda: mission(True), 'airelprio': lambda: mission(False)}
    return dict(MISSION=MISSION, shared=SimpleNamespace(mission=mission))


@cache
def airetreat_bench():
    """Engine probe: the skirmish AI's team state (work/re/l4_states.md) -- retreat on a lost power advantage and the
    EngagePassiveTargets switch (engine line B, layer 4; read back by benches/ai/tactics/checks.py#engine_airetreat; program: work/re
    l4_micro_retreat.md, l4_micro_engage.md; model: RA3-EngineModel ra3model/ai/tactics.py TacticsBlock._team_state,
    simai.Brain.fight).

    The map, AI and the player's structures are ainamed_bench's ainmfar (one always-on state sends 2-4 Peacekeepers by
    SimpleAttack at the far power plant, ~1010 south of the AI's base); the team's micro manager is the probe's own:
    StandardMicroManager_MEDIUM flattened (aitarget_bench._micro_xml) with RetreatMinDistanceFromBase 300 (retail 900:
    the far plant is too near the base for a retreat by the retail number) and:
      airet    RetreatPowerAdvantage 0.2 (retail MEDIUM); GUARDS of the player's Peacekeepers stand round the far plant:
               the team is outgunned there (power advantage = their time to kill us / ours to kill them, ~0.1) -> the
               model: the team turns round to the AI's base (state 1, attack-move home), then stands where the retreat
               ends (RetreatMinDistanceToFallback 500 from where it began, or 300 from the base)
      airetd   airet with the tactic's DisbandAfterRetreatTeamSize 999 (retail 999 x71, 1 x10, 4 x3, 5, 0; xsd 0): the
               team ends its tactic the update its retreat ends (work/re/l4_states.md: was state 1, now 8, members <= the size);
               the always-on state makes a new team at once -- the simulator: out again 2 s later than airet, no reading
      airetf   airet with the state on a map flag: on at the wake, off FLAG_OFF later (one team, no second) -> the
               model: the team cycles as airet's (the tactic goes on with its state off: bench aistateoff1)
      airetfd  airetf + DisbandAfterRetreatTeamSize 999 -> the model: the tactic ends when the retreat does, no state
               to make a new team: the four stay home to the end
      airet0   RetreatPowerAdvantage 0.0: the same fight, no retreat (the advantage is never below 0) -> it fights there
      aipas1   no guards; a SIDE plant of the player's 250 west of the team's way to the far plant; EngagePassiveTargets
               true -> the model: the side plant (a structure: the passive list) comes within a member's vision x 1.5,
               the team attacks it first (state 6)
      aipas0   the same, EngagePassiveTargets false -> straight on to the far plant
      airett   airet with the AI's yard observed (DeletionUpdate CNVTeams: the team state each micro round and a 1 s
               heartbeat) -- which state the team is in when the guards first come in its search circle (6 or 2: the
               work/re d140 gate) and where its members stand when it turns home (D round 149)
    Facts: wake at, side plant (name; aipas*).
    """
    import math
    from pathlib import Path

    import labpaths

    from benches.ai.targets.scenes import ainamed_bench
    an = ainamed_bench()["shared"]
    from benches.ai.targets.scenes import aitarget_bench
    at = aitarget_bench()["shared"]
    from parts import Script, Unit

    MICRO_ID = 'CNVMicroRetreat'
    GUARDS = 12
    GUARD_RING = 60.0                       # packed: the whole guard is in a member's search circle at once
    SIDE = 'UNIT - CNV AI Side Plant'
    SIDE_AT = (3400.0, 2823.0)              # 250 west of the line from the AI's Peacekeepers to the far plant: inside a
    #                                         member's search circle (vision 200 x 1.5), outside its vision
    FLAG = 'CNVRetGo'                       # airetf*: the state's ScriptedFlagHeuristic; the scripts write '/' + FLAG
    FLAG_OFF = 8.0                          # s after the wake: the team has its slot (bench aistateoff1: off 1 s after on
    #                                         still sends the team), well before its retreat ends (bench airet ~s26)


    def micro_xml(**fields):
        """aitarget_bench's flattened StandardMicroManager_MEDIUM under MICRO_ID with these fields replaced."""
        xml = at._micro_xml(15).replace(f'id="{at.IDLE_ID}"', f'id="{MICRO_ID}"', 1)
        fields.setdefault('RetreatMinDistanceFromBase', '300.0')
        for k, v in fields.items():
            key = f' {k}="'
            if key in xml:
                head, rest = xml.split(key, 1)
                xml = head + key + str(v) + rest[rest.index('"'):]
            else:
                xml = xml.replace(f'id="{MICRO_ID}"', f'id="{MICRO_ID}" {k}="{v}"', 1)
        return xml


    def mission(mod, guards=0, side=False, disband=None, flag=False, **fields):
        m = an.mission(mod, 'NamedObject', an.FAR_NAME)
        (fname, xml, asset), = m.assets
        if flag:                                # the state on at the wake, off FLAG_OFF later: one team, never a second
            const = '<ConstantHeuristic/>'
            assert xml.count(const) == 1
            xml = xml.replace(const, f'<ScriptedFlagHeuristic FlagName="{FLAG}"/>', 1)
            m.scripts += [Script('CNV AI - Ret on', [('TIMER_EXPIRED', 'CNV AI Wake')],
                                 [('SET_FLAG', '/' + FLAG, 1), ('SET_MILLISECOND_TIMER', 'CNV AI Ret Off', FLAG_OFF)]),
                          Script('CNV AI - Ret off', [('TIMER_EXPIRED', 'CNV AI Ret Off')], [('SET_FLAG', '/' + FLAG, 0)])]
            m.facts['state off at'] = m.facts['wake at'] + FLAG_OFF
        if disband is not None:
            tac = 'EndBehavior="RAMPAGE">'
            assert xml.count(tac) == 1
            xml = xml.replace(tac, f'EndBehavior="RAMPAGE" DisbandAfterRetreatTeamSize="{disband}">', 1)
            m.facts['disband after retreat'] = disband
        head = '  <AIStrategicStateDefinition'
        xml = xml.replace(head, micro_xml(**fields) + '\n' + head, 1)
        xml = xml.replace('MicroManager="StandardMicroManager_MEDIUM"', f'MicroManager="{MICRO_ID}"', 1)
        m.assets = [(fname, xml, asset)]
        m.facts['micro'] = dict(fields)
        for k in range(guards):
            a =2 * math.pi * k / guards
            m.put(at.INF, 'carrier home', shared.GUARD_RING * math.cos(a), shared.GUARD_RING * math.sin(a),
                  name=f'UNIT - CNV AI Guard {k + 1}', role=f'guard {k + 1}')
        if side:
            cx, cy = m.site('carrier home')[:2]
            m.put('AlliedPowerPlant', 'carrier home', SIDE_AT[0] - cx, SIDE_AT[1] - cy, name=SIDE, role='side plant')
            m.facts['side plant'] = SIDE
        return m


    def observe(m, name):
        """The AI's yard swapped for a copy carrying the CNVTeams log (team state changes and a 1 s heartbeat, ra3ext):
        no extra object, economy or recruit (as aialphaclose_bench's observed pair)."""
        yard = m.role('ai yard')
        original, host = yard.template, 'CNVRetTeamsYard'
        xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures' / (original + '.xml')).read_text(encoding='utf-8')
        assert xml.count('<Behaviors>') == xml.count(f'id="{original}"') == 1
        xml = xml.replace(f'id="{original}"', f'id="{host}"').replace(
            '<Behaviors>', '<Behaviors>\n  <DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="4000"/>')
        m.units.append(Unit(host, xml, names=dict(unit=host), what='原建造厂附带变化日志与每秒心跳', params=dict(every=15)))
        m.find(yard.name).template = yard.template = host
        m.name = name
        m.ext = True
        return m


    MISSION = {
        'airet': lambda: mission('CampAIRet', guards=GUARDS, RetreatPowerAdvantage='0.2'),
        'airett': lambda: observe(mission('CampAIRet', guards=GUARDS, RetreatPowerAdvantage='0.2'), 'CampAIRetT'),
        'airetd': lambda: mission('CampAIRetD', guards=GUARDS, disband=999, RetreatPowerAdvantage='0.2'),
        'airetf': lambda: mission('CampAIRetF', guards=GUARDS, flag=True, RetreatPowerAdvantage='0.2'),
        'airetfd': lambda: mission('CampAIRetFD', guards=GUARDS, flag=True, disband=999, RetreatPowerAdvantage='0.2'),
        'airet0': lambda: mission('CampAIRet0', guards=GUARDS, RetreatPowerAdvantage='0.0'),
        'aipas1': lambda: mission('CampAIPas1', side=True, EngagePassiveTargets='true'),
        'aipas0': lambda: mission('CampAIPas0', side=True, EngagePassiveTargets='false'),
    }
    shared = SimpleNamespace(
        GUARD_RING=GUARD_RING, GUARDS=GUARDS, MICRO_ID=MICRO_ID, at=at, micro_xml=micro_xml,
        mission=mission, observe=observe,)
    return dict(MISSION=MISSION, shared=shared)


def aisort_bench():
    """C-line SortByDistance pair: far Guardian inserted first, near second.

    One SimpleAttack team, capacity one, identical candidates/target/wake in both
    builds. Candidate-to-target distances differ from candidate-to-yard ordering.
    The check observes named departures, not an unresolved dynamic team counter.
    """
    team_mission = aiteamfilter_bench()["shared"].mission
    TANK = aiteamfilter_bench()["shared"].TANK
    from missions.aiskirm_bench import ai_map


    def mission(sort):
        m = team_mission(f'CampAISort{int(sort)}', tanks=0, inf=0, max_units=1,
                         kinds='IncludeKindOf="VEHICLE"')
        m.map = ai_map(m.map, library=False)
        candidates = []
        for identity, dx in (('far', -50.0), ('near', -350.0)):
            o = m.put(TANK, 'east base', dx, 160.0, side='s1', angle=3.1416,
                      name=f'UNIT - CNV Sort {identity}', role=f'candidate {identity}')
            candidates.append((identity, o.name, (o.x, o.y)))
        target = next(o for o in m.objects if o.name == m.role('player target').name)
        m.cnv_candidates = tuple(candidates)
        m.cnv_target = (target.x, target.y)
        m.facts |= {'sort by distance': int(sort), 'departure radius': 80.0}
        filename, xml, asset = m.assets[0]
        xml = xml.replace('<TeamTemplate ', f'<TeamTemplate SortByDistance="{str(sort).lower()}" ')
        m.assets[0] = filename, xml, asset
        return m


    MISSION = {'aisort0': lambda: mission(False), 'aisort1': lambda: mission(True)}
    return dict(MISSION=MISSION)


def aispecial_bench():
    """Engine probe: when the skirmish AI fires its superweapon and at what (read back by benches/ai/tactics/checks.py#engine_aispecial).

    Same Niagara map as benches/ai/production/scenes.py#aiopen_bench. The enemy (s1) is Allied, AlliedBalanced, a construction yard and a power plant
    at the east base plus an AlliedSuperWeaponAdvanced (the proton collider, SpecialPowerParticleCannon: PLAYER_AOE_ATTACK
    at STRUCTUREs only, not CONSTRUCTION_YARD / SUPER_WEAPON, MinTargetsHit 4; weapon ParticleCannonWeapon -> 400 damage,
    radius 250, taper 200, on the SDK's ParticleAcceleratorFinalWeapon). No money (0 all along), so the AI builds nothing.
    Asleep until WAKE_AT, then the retail wake set.

    The player (p1) piles (spacing inside a pile < 250, the piles >= 640 apart; costs from the SDK's BuildCost):
      A  4 x AlliedBarracks (500)    = 2000  at outpost 1, 150 apart   (cheapest, 4 buildings)
      B  3 x AlliedWarFactory (2000) = 6000  at outpost 2, 200 apart   (dearest, only 3 buildings)
      C  5 x AlliedBaseDefense (800) = 4000  at front, 120 apart       (in between, 5 buildings)
    Builds:
      aispecial     the three piles, all revealed to s1 (checks a, b, c, t)
      aispecialhid  one pile of 5 AlliedBaseDefense at west field, far from the AI and NOT revealed to s1 (check d)
    Facts: wake at.
    """
    import resources
    from maps import niagara
    from parts import Mission, Script

    WAKE_AT = 10.0
    PERSONALITY = 'AIPersonalityDefinition:1AlliedBalanced'
    SUPER, POWER, PLANT = 'AlliedSuperWeaponAdvanced', 'SpecialPowerParticleCannon', 'AlliedPowerPlant'
    SUPER_NAME = 'UNIT - CNV AS Collider'
    # pile: (letter, template, site, spacing, count, hit weight)
    PILES = (('A', 'AlliedBarracks', 'outpost 1', 150.0, 4, 1), ('B', 'AlliedWarFactory', 'outpost 2', 200.0, 3, 10),
             ('C', 'AlliedBaseDefense', 'front', 120.0, 5, 100))
    HIDDEN = (('H', 'AlliedBaseDefense', 'west field', 120.0, 5, 1),)
    # pile letter -> (dx, dy) off its site: A and B stood on niagara's trees (barracks 4 at (1925, 3350) on YP_Tree02,
    # war factory 1 at (1700, 1650) on MR_Tree04; test_maps' scenery check). Moved 2026-11-06 (B round 16) to the
    # nearest spots clear by 40+ of every tree. The readings of 11-06 (checks a-h, aispecialhid d) were taken before the
    # move; they need no rerun: the piles keep their counts, spacing and costs, A moves 56 and B 56 units, still well
    # apart (> 600) and far from the AI base, and the result (C is hit: A and B fail MinTargetsHit / value) does not hang
    # on where inside the outpost a pile stands.
    SHIFT = {'A': (-50.0, 25.0), 'B': (50.0, -25.0)}


    def names(pile):
        return [f'UNIT - CNV AS {pile[0]} {k + 1}' for k in range(pile[4])]


    POWERS_PID = 'CNVPowers'              # aispecoff / aispechb: 1AlliedBalanced with UsePlayerPowersAtDifficulty changed


    def powers_xml(at):
        """1AlliedBalanced with UsePlayerPowersAtDifficulty=`at` (a difficulty bit set; D126: the AI fires its powers only
        at a difficulty in it; 1AlliedBalanced inherits the XSD default, all four)."""
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            '    <Include type="instance" source="DATA:SkirmishAI/Personalities/AlliedBalanced.xml" />',
            '  </Includes>',
            f'  <AIPersonalityDefinition id="{POWERS_PID}" PersonalityType="{POWERS_PID}" inheritFrom="1AlliedBalanced"'
            f' UsePlayerPowersAtDifficulty="{at}"/>',
            '</AssetDeclaration>', ''])


    def mission(name='CampAISpecial', piles=PILES, use_at=None):
        # facts for the check (it may not import this module): the power, which piles (letters, cast 'A 1' ...) with their
        # hit weights, and whether the piles are revealed to the AI
        facts = {'wake at': WAKE_AT, 'power': POWER, 'piles': {p[0]: p[5] for p in piles}, 'reveal to ai': piles is PILES}
        m = Mission(name=name, map=resources.measured(niagara), facts=facts)
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': PERSONALITY}
        if use_at is not None:               # aispecoff / aispechb (check t): the bench plays MEDIUM
            m.facts['powers at medium'] = int('MEDIUM' in use_at.split())
            m.sides['s1']['aiPersonality'] = f'AIPersonalityDefinition:{POWERS_PID}'
            m.assets.append((f'{POWERS_PID}.xml', powers_xml(use_at), f'AIPersonalityDefinition:{POWERS_PID}'))
        m.spawns |= {SUPER}
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put(PLANT, 'east power', 0, 0, side='s1', name='UNIT - CNV AS Plant', role='ai plant')
        m.put(SUPER, 'east base', -150.0, -250.0, side='s1', name=SUPER_NAME, role='collider')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        for pile in piles:
            letter, tpl, site, step, n, _ = pile
            dx, dy = SHIFT.get(letter, (0.0, 0.0))
            for k, nm in enumerate(names(pile)):
                m.put(tpl, site, dx + step * (k - (n - 1) / 2.0), dy, name=nm, role=f'{letter} {k + 1}')
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT)]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0)])]
        return m


    MISSION = {'aispecial': mission, 'aispecialhid': lambda: mission('CampAIHid', HIDDEN),
               'aispecoff': lambda: mission('CampAISpecOff', use_at=''),           # check t: powers at no difficulty
               'aispechb': lambda: mission('CampAISpecHB', use_at='HARD BRUTAL')}  # check t: not at MEDIUM
    return dict(MISSION=MISSION)


def aiswitch_bench():
    """Engine probe: the skirmish AI's script switches our levels send at its wake (plan.py 敌方AI: priorities 20, repairs
    and rebuild 0) -- SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES, SKIRMISH_AI_USE_REPAIRS, SKIRMISH_AI_USE_REBUILD_SYSTEM
    (engine line B, layer 4; read back by benches/ai/tactics/checks.py#engine_aiswitch; program: work/re l4_aiswitches.md; model:
    RA3-EngineModel ra3model/ai/player.py set_enemy_priorities / repairs / use_rebuild, simai.Brain.switches).

    The map, AI and the player's structures are aitarget_bench's (one always-on state sends 2-4 Peacekeepers by
    SimpleAttack); only the wake's switches differ, plus for the repair / rebuild builds a power plant of the AI's own
    north of its yard:
      aisw0near  aitargetnear (ClosestStructureHeuristic) with priorities 0: read, the enemy table is emptied -> no
                 enemy player -> no target, no team leaves (the control aitargetnear went to the near plant at s13)
      aisw0far   ainmfar (NamedObject, the far plant) with priorities 0: does a named target look at the enemy table?
                 (the program, work/re/l4_states.md, reads no relationship tier: the model says the team still goes)
      aiswrep1 / aiswrep0  the AI's plant at 50 % health from the start, repairs 1 / 0: read, repairing needs the switch
                 and the personality's RepairBuildingsAtDifficulty (MEDIUM HARD BRUTAL); the model says 1 heals, 0 not
      aiswreb1 / aiswreb0  the AI's plant killed 5 s after the wake, 5000 money at the wake, rebuild 1 / 0: is it put
                 back, how soon? (who reads the rebuild list is NOT READ; the model rebuilds nothing)
    Facts: wake at, own plant (name), kill at (rebuild builds).
    """
    from benches.ai.targets.scenes import ainamed_bench
    an = ainamed_bench()["shared"]
    from benches.ai.targets.scenes import aitarget_bench
    at = aitarget_bench()["shared"]
    from parts import Script

    OWN = 'UNIT - CNV AI Own Plant'
    KILL_AFTER = 5.0
    MONEY = 5000


    def switches(m, prio=20, repairs=0, rebuild=0, money=0):
        """The wake script's switches set to these (the rest of aitarget_bench's wake kept)."""
        s1 = m.player('s1')
        (wake,) = [s for s in m.scripts if s.name == 'CNV AI - Wake']
        vals = {'SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES': prio, 'SKIRMISH_AI_USE_REPAIRS': repairs,
                'SKIRMISH_AI_USE_REBUILD_SYSTEM': rebuild, 'PLAYER_SET_MONEY': money}
        wake.do = [(a[0], s1, vals[a[0]]) if a[0] in vals else a for a in wake.do]
        return m


    def own_plant(m):
        m.put('AlliedPowerPlant', 'east base', 0.0, 300.0, side='s1', name=OWN, role='ai plant')
        m.facts['own plant'] = OWN
        return m


    def repair(mod, on):
        m = own_plant(switches(at.mission(mod, 'ClosestStructureHeuristic', 'SimpleAttack'), repairs=on))
        m.scripts.append(Script('CNV AI - Hurt', [], [('UNIT_SET_HEALTH', OWN, 50.0)]))
        return m


    def rebuild(mod, on):
        m = own_plant(switches(at.mission(mod, 'ClosestStructureHeuristic', 'SimpleAttack'), rebuild=on, money=MONEY))
        m.facts['kill at'] = m.facts['wake at'] + KILL_AFTER
        m.scripts.append(Script('CNV AI - Kill own plant', [('TIMER_EXPIRED', 'CNV AI Kill')], [('NAMED_KILL', OWN)]))
        (wake,) = [s for s in m.scripts if s.name == 'CNV AI - Wake']
        wake.do = list(wake.do) +[('SET_MILLISECOND_TIMER', 'CNV AI Kill', KILL_AFTER)]
        return m


    MISSION = {
        'aisw0near': lambda: switches(at.mission('CampAISw0Near', 'ClosestStructureHeuristic', 'SimpleAttack'), prio=0),
        'aisw0far': lambda: switches(an.mission('CampAISw0Far', 'NamedObject', an.FAR_NAME), prio=0),
        'aiswrep1': lambda: repair('CampAISwRep1', 1),
        'aiswrep0': lambda: repair('CampAISwRep0', 0),
        'aiswreb1': lambda: rebuild('CampAISwReb1', 1),
        'aiswreb0': lambda: rebuild('CampAISwReb0', 0),
    }
    return dict(MISSION=MISSION)


def aitactical_bench():
    """EngageTacticalTarget on/off, with hostile/passive acquisition disabled.

    Prediction before bench: the on team receives explicit attacks on the nearest
    power plant, the off team only attack-moves to its point. The unarmed plant
    cannot provoke retaliation. At 40 s on has damaged it, off leaves it at 100%.
    Both retain four Peacekeepers. This tests dispatch, not exact firing timing.

    Bench 2026-11-11: aitacon:a / aitacoff:a PASS (one run each). On reads
    100% through s12, 84% at s13, 0% from s22 through s43; off stays 100%
    through s48. Both retain four infantry. Replay: tests/test_engage_tactical.py.
    Only an object target in range, with passive/hostile dispatch disabled, is
    covered; point targets, competing enemies and the exact scan boundary are not.
    """
    import resources
    from maps import niagara
    from benches.ai.targets.scenes import aitarget_bench
    ab = aitarget_bench()["shared"]
    from parts import Mission, Script


    def mission(enabled):
        m = Mission(name='CampTacOn' if enabled else 'CampTacOff', map=resources.measured(niagara),
                    facts={'wake at': ab.WAKE_AT, 'tactical enabled': float(enabled)})
        xml = ab.personality_xml('ClosestStructureHeuristic', 'SimpleAttack', idle=15)
        xml = xml.replace('EngageHostileTargets="true"', 'EngageHostileTargets="false"')
        xml = xml.replace('EngagePassiveTargets="true"', 'EngagePassiveTargets="false"')
        xml = xml.replace('EngageTacticalTarget="true"',
                          f'EngageTacticalTarget="{str(enabled).lower()}"')
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies',
                         'aiPersonality': f'AIPersonalityDefinition:{ab.PID}'}
        m.assets.append((f'{ab.PID}.xml', xml, f'AIPersonalityDefinition:{ab.PID}'))
        m.cnv_units = (ab.INF,)
        m.put('AlliedConstructionYard', 'east base', side='s1', name='Tac AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='Tac Player Yard', role='player yard')
        m.put('AlliedPowerPlant', 'east base', -450, 0, name='Tac Plant', role='target')
        for k in range(4):
            m.put(ab.INF, 'east base', -260, -90 + 60 * k, side='s1',
                  name=f'Tac Infantry {k + 1}', role=f'infantry {k + 1}', angle=3.1416)
        m.spawns.add(ab.INF)
        m.waypoint('ai base', 'Tac Base', 'east base')
        s1 = m.player('s1')
        m.scripts = [
            Script('Tac start', [], [('PLAYER_SET_MONEY', s1, 0),
                                    ('SET_MILLISECOND_TIMER', 'Tac Wake', ab.WAKE_AT)]),
            Script('Tac wake', [('TIMER_EXPIRED', 'Tac Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, m.mark('ai base')),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20),
                    ('SKIRMISH_AI_USE_REPAIRS', s1, 0), ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0),
                    ('PLAYER_SET_MONEY', s1, 0)])]
        return m


    MISSION = {'aitacon': lambda: mission(True), 'aitacoff': lambda: mission(False)}
    return dict(MISSION=MISSION)


@cache
def aiteamfields_bench():
    """Engine line D round 148: three team / tactic fields the retail campaign uses and no bench had (work/re
    d130_untouched_census.md section 2; read back by benches/ai/tactics/checks.py#engine_aiteamfields). Each pair differs in that one field;
    every build carries a passive CNVTeams host (aiteams_bench.host_unit; airelease's own in aihot*) for the team states and members.

    Tactic.GatherWaypoint (SimpleAttack only; 22 retail tactics in 7 levels) -- ainamed_bench's ainmfar (2-4 Peacekeepers
    by SimpleAttack at the far power plant, south of the AI base) with the tactic's GatherWaypoint:
      aigathwp   GatherWaypoint "CNV AI WP Target" (ainamed's waypoint at 'route 2', ~550 north of the team): the program
                 (work/re d130) sends the team to the waypoint first, to the target once every team is still -> the model:
                 at the waypoint, then the far plant
      aigathno   no GatherWaypoint (the same waypoint on the map): straight to the far plant
      aigathbad  GatherWaypoint "CNV AI WP Nowhere" (no such waypoint): the lookup fails -> as aigathno

    TeamTemplate.MaxTypesOfUnits (58 uses) -- aiteamfilter_bench's SimpleAttack team (no ObjectFilter, CAN_ATTACK,
    MinUnits 1, MaxUnits 8) over 2 Guardians, 2 Peacekeepers and 2 Javelins at home:
      aimaxty1   MaxTypesOfUnits 1: the team takes the first type it meets only, the other two stay home
      aimaxty3   MaxTypesOfUnits 3: all six go

    TeamTemplate.Priority=HOTSPOT (47 uses, the highest, 8) -- airelease_bench's airelprio (2 Guardians held by a
    StaticDefense team, ReleaseType RELEASE_TO_PRIORITY; a SimpleAttack state from 35 s wants the same 2), with the
    defender's Priority and the attacker's set here (release: the holder's priority strictly below the recruiter's):
      aihotstd   defender STANDARD, attacker HOTSPOT -> released: the tanks go to the player's plant
      aihotdef   defender STANDARD, attacker DEFAULT -> kept home
      aihotscr   defender SCRIPTED (7), attacker HOTSPOT -> released (only HOTSPOT outranks SCRIPTED)
    TeamTemplate.Priority=COOP (12 uses, 6: the co-op commander's beacon states), the same pair:
      aicoophi   defender HIGH (5), attacker COOP -> released;  aicoopsc   defender SCRIPTED (7), attacker COOP -> kept
    TeamTemplate.Priority=DEFENSE_HIGH (10 uses, 4: the AI's emergency defense), the same pair:
      aidefhst   defender STANDARD (3), attacker DEFENSE_HIGH -> released;  aidefhhi   defender HIGH (5) -> kept
    Facts: wake at (+ airelease's attack at).
    """
    from benches.ai.targets.scenes import ainamed_bench
    an = ainamed_bench()["shared"]
    tf = aiteamfilter_bench()["shared"]
    rel = airelease_bench()["shared"]
    HOST = aiteams_bench()["shared"].HOST
    host_unit = aiteams_bench()["shared"].host_unit

    JAV = 'AlliedAntiVehicleInfantry'
    NOWHERE = 'CNV AI WP Nowhere'
    # the model's order (ra3model/ai/teams.py PRIORITY; work/re d130: HOTSPOT 8 the highest)
    PRIORITY = ('DEFAULT', 'DEFENSE', 'LOW', 'STANDARD', 'DEFENSE_HIGH', 'HIGH', 'COOP', 'SCRIPTED', 'HOTSPOT')


    def _host(m):
        if HOST not in {u.name for u in m.units}:
            m.units.append(host_unit())
            m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
        m.ext = True
        return m


    def gather(mod, name=None):
        m = an.mission(mod, 'NamedObject', an.FAR_NAME)
        if name:
            (fname, xml, asset), = m.assets
            tac = 'Tactic="SimpleAttack" EndBehavior="RAMPAGE">'
            assert xml.count(tac) == 1
            m.assets = [(fname, xml.replace(tac, f'Tactic="SimpleAttack" EndBehavior="RAMPAGE" GatherWaypoint="{name}">'),
                         asset)]
        m.facts['gather waypoint'] = int(name == an.WP)     # 1: the named waypoint is on the map
        return _host(m)


    def max_types(mod, n):
        m = tf.mission(mod, tanks=2, inf=2)
        (fname, xml, asset), = m.assets
        head = '<TeamTemplate MinUnits="1"'
        assert xml.count(head) == 1
        m.assets = [(fname, xml.replace(head, f'<TeamTemplate MaxTypesOfUnits="{n}" MinUnits="1"'), asset)]
        for k in range(2):
            m.put(JAV, 'east base', -200.0, -310.0 - 50.0 * k, side='s1', angle=3.1416,
                  name=f'UNIT - CNV AI Javelin {k + 1}', role=f'ai javelin {k + 1}')
        m.spawns |= {JAV}
        m.cnv_units = (tf.TANK, tf.INF, JAV)
        m.facts['max types'] = n
        return _host(m)


    def hotspot(mod, holder, recruiter):
        m = rel.mission(False)
        m.name = mod
        (fname, xml, asset), = m.assets
        head, sep, attack = xml.partition('<AIStrategicStateDefinition id="CNVReleaseAttack"')
        assert sep and head.count('Priority="DEFENSE"') == 1 and attack.count('Priority="STANDARD"') == 1
        xml = head.replace('Priority="DEFENSE"', f'Priority="{holder}"') + sep + \
            attack.replace('Priority="STANDARD"', f'Priority="{recruiter}"')
        m.assets = [(fname, xml, asset)]
        m.facts['released'] = int(PRIORITY.index(recruiter) > PRIORITY.index(holder))
        return m                        # airelease's own CNVTeams host (CNVReleaseHost) logs the teams


    MISSION = {
        'aigathwp': lambda: gather('CampAIGathWp', an.WP),
        'aigathno': lambda: gather('CampAIGathNo'),
        'aigathbad': lambda: gather('CampAIGathBad', NOWHERE),
        'aimaxty1': lambda: max_types('CampAIMaxTy1', 1),
        'aimaxty3': lambda: max_types('CampAIMaxTy3', 3),
        'aihotstd': lambda: hotspot('CampAIHotStd', 'STANDARD', 'HOTSPOT'),
        'aihotdef': lambda: hotspot('CampAIHotDef', 'STANDARD', 'DEFAULT'),
        'aihotscr': lambda: hotspot('CampAIHotScr', 'SCRIPTED', 'HOTSPOT'),
        'aicoophi': lambda: hotspot('CampAICoopHi', 'HIGH', 'COOP'),
        'aicoopsc': lambda: hotspot('CampAICoopSc', 'SCRIPTED', 'COOP'),
        'aidefhst': lambda: hotspot('CampAIDefHiSt', 'STANDARD', 'DEFENSE_HIGH'),
        'aidefhhi': lambda: hotspot('CampAIDefHiHi', 'HIGH', 'DEFENSE_HIGH'),
    }
    return dict(MISSION=MISSION, shared=SimpleNamespace(_host=_host))


@cache
def aiteamfilter_bench():
    """Engine probe: which of the AI's units a team template takes -- ObjectFilter Rule ANY / ALL / NONE with IncludeThing
    / ExcludeThing, TeamTemplate IncludeKindOf / ExcludeKindOf, MaxUnits (read back by benches/ai/tactics/checks.py#engine_aiteamfilter;
    private ai/teams.py fits() / Team.full, simai through it).

    aipoweradv_bench's set-up (Niagara, the enemy s1 Allied with a yard and no money, every inherited strategic state
    removed, woken at 10 s), one always-on state CNVStateTF (ConstantHeuristic, MaxTargets 1): a SimpleAttack team at
    the closest enemy structure (a player power plant ~750 west of them). s1 has 4 Guardians (AlliedAntiVehicleVehicleTech1)
    and 4 Peacekeepers (AlliedAntiInfantryInfantry) at home; the team's filter is the variant's:
      aitfany   ObjectFilter Rule ANY, IncludeThing Guardian (the earlier probes' filter): tanks only
      aitfnone  Rule NONE, IncludeThing Guardian (retail CaptureLandHusks: "any 1 basic infantry" = NONE + the list)
      aitfall   Rule ALL, ExcludeThing Guardian (retail AIStateLibrary's ALL + aircraft list)
      aitfki    no ObjectFilter, IncludeKindOf INFANTRY
      aitfke    no ObjectFilter, IncludeKindOf CAN_ATTACK, ExcludeKindOf INFANTRY
      aitfmax   no ObjectFilter, IncludeKindOf CAN_ATTACK, MaxUnits 3, 8 Guardians and no Peacekeepers
    Round 81 (no ObjectFilter, KindOf CAN_ATTACK): aitfland / aitfamph / aitfwat -- AllowedLocomotorTypes LAND /
    AMPHIBIOUS / WATER, the Peacekeepers swapped for 4 Riptide ACVs (AlliedAntiInfantryVehicle, KindOf AMPHIBIOUS);
    aitfosi / aitfosv / aitfosc -- RegisteredObjectSet INFANTRY / VEHICLES / SKIRMISH_AI_NORMAL_COMBAT_UNITS.
    Every team: MinUnits 1, MaxUnits 8 (but aitfmax), AllowedLocomotorTypes LAND AMPHIBIOUS (but round 81's), Priority
    STANDARD.

    Facts: wake at, ai tanks, ai infantry, expect tanks home, expect infantry home (the model's guess before the bench:
    ANY / NONE + Include = only those, ALL + Exclude = all but those; kinds: any of Include, none of Exclude).
    """
    import resources
    from maps import niagara
    from benches.ai.targets.scenes import aistate_bench
    BASE = aistate_bench()["shared"].BASE
    INHERITED = aistate_bench()["shared"].INHERITED
    from parts import Mission, Script

    WAKE_AT = 10.0
    PID = 'CNVTeamF'
    TANK, INF = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
    RIPTIDE = 'AlliedAntiInfantryVehicle'           # KindOf AMPHIBIOUS (simai's surface 'AMPHIBIOUS')
    KINDS = 'IncludeKindOf="CAN_ATTACK" ExcludeKindOf="IGNORES_SELECT_ALL HARVESTER"'


    # aiar*: the AI builds `late` more Guardians itself (script-made units are never recruited: engine_aimicro
    # aimicbuilth), by aimicro_bench's opener (Time 0s with a Deposit, the Builds, Time 90s: both built there)
    LATE_MONEY, LATE_DEPOSIT, LATE_CHECK_AT = 10000, 5000, 60.0
    OPENER = 'CNVTeamFOpener'
    FACTORY_DY, PLANT_DY = -250.0, 400.0   # round 90: factory -400 -> -250, inside the yard's Tech2 reach (~300)
    TECH2 = 'Upgrade_AlliedTech2'
    FAR_PLANT_DY = -1000.0                 # round 92: outside the 450 home box, on the open grass south (aiskirm's OUT)


    def personality_xml(pid, kinds, filt, max_units, locos='LAND AMPHIBIOUS', objset='', always=False, late=0,
                        late_unit=TANK, static=False):
        if static:      # round 91: LandDefense_MEDIUM's shape (AIStateLibrary.xml:495) with MaxTargets 1
            target, tactic = 'FriendlyLandStructureHeuristic', \
                '<Tactic id="Attack" Tactic="StaticDefense" Distance="450" EndBehavior="DISBAND">'
            prio, micro = 'DEFENSE', 'DefenseMicroManager_MEDIUM'
        else:
            target, tactic = 'ClosestStructureHeuristic', \
                '<Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE" EndIfStateTurnsOff="true">'
            prio, micro = 'STANDARD', 'StandardMicroManager_MEDIUM'
        removed =[f'    <StrategicState id="{k}" xai:joinAction="Remove"/>' for k in INHERITED]
        opener, first = [], []
        if late:
            removed += ['    <BuildState id="AlliedNeededUnits" xai:joinAction="Remove"/>']
            opener = [f'  <SkirmishOpeningMove id="{OPENER}" Side="PlayerTemplate:Allies">',
                      f'    <Order Time="0s" Account="PRODUCTION" Deposit="{LATE_DEPOSIT}" />',
                      *[f'    <Order Build="{late_unit}" />'] * late, '    <Order Time="90s"/>', '  </SkirmishOpeningMove>']
            first = [f'    <OpeningMove Name="{OPENER}" Weight="100%">', '      <Heuristic>',
                     '        <ConstantHeuristic/>', '      </Heuristic>', '    </OpeningMove>']
        return '\n'.join([
            '<?xml version="1.0" encoding="utf-8"?>',
            '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xai="uri:ea.com:eala:asset:instance">',
            '  <Tags></Tags>',
            '  <Includes>',
            f'    <Include type="instance" source="DATA:SkirmishAI/Personalities/{BASE}.xml" />',
            '  </Includes>',
            (
                f"""  <AIStrategicStateDefinition id="CNVStateTF" MaxTargets="1">\n"""
                f"""    <Heuristic>\n"""
                f"""      <ConstantHeuristic/>\n"""
                f"""    </Heuristic>\n"""
                f"""    <TargetHeuristic TargetHeuristic="{target}"/>\n"""
                f"""    {tactic}\n"""
                f"""      <TeamTemplate MinUnits="1" MaxUnits="{max_units}" {kinds}\n"""
                f"""                    AllowedLocomotorTypes="{locos}" Priority="{prio}" AlwaysRecruit="{'true' if always else 'false'}"{objset}\n"""
                f"""                    MicroManager="{micro}">{filt}\n"""
                f"""      </TeamTemplate>\n"""
                f"""    </Tactic>\n"""
                f"""  </AIStrategicStateDefinition>"""
            ),
            *opener,
            f'  <AIPersonalityDefinition id="{pid}" PersonalityType="{pid}" inheritFrom="{BASE}">',
            *first,
            *removed,
            '    <StrategicState id="CNVStateTF" State="CNVStateTF"/>',
            '  </AIPersonalityDefinition>',
            '</AssetDeclaration>', ''])


    def objfilter(rule, inc=(), exc=(), kinds=''):
        body = [f'          <IncludeThing>{t}</IncludeThing>' for t in inc] + \
               [f'          <ExcludeThing>{t}</ExcludeThing>' for t in exc]
        return '\n'.join(['', f'        <ObjectFilter Rule="{rule}"{kinds}>', *body, '        </ObjectFilter>'])


    def mission(name, kinds=KINDS, filt='', max_units=8, tanks=4, inf=4, tanks_home=0, inf_home=4, second=INF,
                locos='LAND AMPHIBIOUS', objset='', always=False, late=0, late_unit=TANK, static=False, tp_at=None,
                tanks_out=0, plant_at=None, at_plant=0, tp_named=(), named_out=0):
        """second: the other unit type (Peacekeepers, or Riptide ACVs in the locomotor builds); inf / inf_home count it.
        always: the team's AlwaysRecruit; late: Guardians the AI builds itself (a war factory, a plant, the opener);
        late_unit: what the opener builds instead (round 89: aiar4 Riptides)."""
        pid = PID + name[-1]
        facts = {'wake at': WAKE_AT, 'ai tanks': tanks, 'ai infantry': inf,
                 'expect tanks home': tanks_home, 'expect infantry home': inf_home}
        if late:
            facts |= {'late tanks': late, 'check at': LATE_CHECK_AT}
        if tp_at:       # round 91: the default team teleported out -- only units no AI team holds go (read at tp + 2)
            facts |= {'teleport at': tp_at, 'check at': tp_at + 2.0, 'expect tanks out': tanks_out}
        if plant_at:    # round 92: a new AI plant far out at plant_at -- does the defense team move its guard there
            facts |= {'plant at': plant_at, 'check at': plant_at + 50.0, 'expect tanks at plant': at_plant}
        if tp_named:    # round 92: placed tank 1 teleported out at each time -- back = still held, stays = released
            facts |= {f'named teleport {k + 1}': at for k, at in enumerate(tp_named)}   # facts are numbers
            facts |= {'check at': tp_named[-1] + 30.0, 'expect named out': named_out}
        m = Mission(name=name, map=resources.measured(niagara), facts=facts)
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
        xml = personality_xml(pid, kinds, filt, max_units, locos, f' RegisteredObjectSet="{objset}"' if objset else '',
                              always, late, late_unit, static)
        m.assets.append((f'{pid}.xml', xml, f'AIPersonalityDefinition:{pid}'))
        m.cnv_units = (TANK, second)
        m.cnv_labels = ('坦克在家', '步兵在家' if second == INF else '气垫船在家')
        m.spawns |= {TANK, second}
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        m.put('AlliedPowerPlant', 'east gate', -300.0, 0.0, name='UNIT - CNV AI Player Target', role='player target')
        for k in range(tanks):
            m.put(TANK, 'east base', -200.0 - 80.0 * (k // 4), 160.0 + 70.0 * (k % 4), side='s1', angle=3.1416,
                  name=f'UNIT - CNV AI Tank {k + 1}', role=f'ai guardian {k + 1}')
        for k in range(inf):
            if second == INF:
                m.put(INF, 'east base', -200.0, -160.0 - 50.0 * k, side='s1', angle=3.1416,
                      name=f'UNIT - CNV AI Peacekeeper {k + 1}', role=f'ai peacekeeper {k + 1}')
            else:
                m.put(second, 'east base', -200.0 - 70.0 * (k % 2), -160.0 - 70.0 * (k // 2), side='s1', angle=3.1416,
                      name=f'UNIT - CNV AI Riptide {k + 1}', role=f'ai riptide {k + 1}')
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT),
                                          # round 90: the Guardian needs Upgrade_AlliedTech2 (its GameDependency); the
                                          # yard holding it lends it to a war factory within ~300 (engine_tech c / d)
                                          *([('NAMED_RECEIVE_UPGRADE', TECH2, 'UNIT - CNV AI Yard')] if late else [])]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, LATE_MONEY if late else 0)])]
        if tp_at:
            m.waypoint('out', 'CNV AI Out', 'east base', 0.0, -1200.0)
            m.scripts += [Script('CNV AI - Tp timer', [], [('SET_MILLISECOND_TIMER', 'CNV AI Tp', tp_at)]),
                          Script('CNV AI - Tp', [('TIMER_EXPIRED', 'CNV AI Tp')],
                                 [('TEAM_TELEPORT_TO_WAYPOINT', m.team('s1'), 'CNV AI Out')])]
        if plant_at:
            m.waypoint('far plant', 'CNV AI Far Plant', 'east base', 0.0, FAR_PLANT_DY)
            m.scripts += [Script('CNV AI - Plant timer', [], [('SET_MILLISECOND_TIMER', 'CNV AI Plant', plant_at)]),
                          Script('CNV AI - Plant', [('TIMER_EXPIRED', 'CNV AI Plant')],
                                 [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'UNIT - CNV AI Far Plant', 'AlliedPowerPlant',
                                   m.team('s1'), 'CNV AI Far Plant')])]
        if tp_named:
            m.waypoint('out', 'CNV AI Out', 'east base', 0.0, -1200.0)
            for k, at in enumerate(tp_named):
                m.scripts += [Script(f'CNV AI - Tpn timer {k}', [], [('SET_MILLISECOND_TIMER', f'CNV AI Tpn {k}', at)]),
                              Script(f'CNV AI - Tpn {k}', [('TIMER_EXPIRED', f'CNV AI Tpn {k}')],
                                     [('UNIT_TELEPORT_TO_WAYPOINT', 'UNIT - CNV AI Tank 1', 'CNV AI Out')])]
        if late:
            m.put('AlliedWarFactory', 'east base', 0, FACTORY_DY, side='s1', name='UNIT - CNV AI Factory', role='ai factory')
            m.put('AlliedPowerPlant', 'east base', 0, PLANT_DY, side='s1', name='UNIT - CNV AI Plant', role='ai plant')
        return m


    MISSION = {
        'aitfany': lambda: mission('CampAITFAny', filt=objfilter('ANY', inc=(TANK,))),
        'aitfnone': lambda: mission('CampAITFNone', filt=objfilter('NONE', inc=(TANK,))),
        'aitfall': lambda: mission('CampAITFAll', filt=objfilter('ALL', exc=(TANK,)), tanks_home=4, inf_home=0),
        'aitfki': lambda: mission('CampAITFKi', kinds='IncludeKindOf="INFANTRY"', tanks_home=4, inf_home=0),
        'aitfke': lambda: mission('CampAITFKe', kinds='IncludeKindOf="CAN_ATTACK" ExcludeKindOf="INFANTRY"'),
        # 11-23: the filter's own KindOf Include / Exclude (retail EngineerIdle ANY Include, BombardmentShipAttack
        # ANY Include + IncludeThing, AttachedBurstDroneRemoval ALL Exclude; the model ignored them in a team). Guesses (the
        # program's filter, CampaignLab work/re d61_b_fields.md 3 / d59 2): IncludeThing passes first; then Exclude kinds
        # refuse; ALL passes; ANY = any Include kind; NONE = nothing but the IncludeThing list. Bench 11-23: the first
        # three as guessed; aitfokn sent the Peacekeepers (NONE = ANY), expectation set to the reading.
        'aitfoki': lambda: mission('CampAITFOKi', filt=objfilter('ANY', kinds=' Include="INFANTRY"'), tanks_home=4,
                                   inf_home=0),
        'aitfokt': lambda: mission('CampAITFOKt', filt=objfilter('ANY', inc=(TANK,), kinds=' Include="INFANTRY"'),
                                   tanks_home=0, inf_home=0),
        'aitfoke': lambda: mission('CampAITFOKe', filt=objfilter('ALL', kinds=' Exclude="INFANTRY"')),
        'aitfokn': lambda: mission('CampAITFOKn', filt=objfilter('NONE', kinds=' Include="INFANTRY"'), tanks_home=4,
                                   inf_home=0),
        'aitfmax': lambda: mission('CampAITFMax', max_units=3, tanks=8, inf=0, tanks_home=5, inf_home=0),
        # round 81: AllowedLocomotorTypes (Guardians: no AMPHIBIOUS kind = LAND; Riptide ACVs: AMPHIBIOUS) and
        # RegisteredObjectSet (the model reads it but filters on nothing; the guesses are "a filter by kind")
        'aitfland': lambda: mission('CampAITFLand', second=RIPTIDE, locos='LAND', tanks_home=0, inf_home=4),
        'aitfamph': lambda: mission('CampAITFAmph', second=RIPTIDE, locos='AMPHIBIOUS', tanks_home=4, inf_home=0),
        'aitfwat': lambda: mission('CampAITFWat', second=RIPTIDE, locos='WATER', tanks_home=4, inf_home=4),
        'aitfosi': lambda: mission('CampAITFOsI', objset='INFANTRY', tanks_home=4, inf_home=0),
        'aitfosv': lambda: mission('CampAITFOsV', objset='VEHICLES', tanks_home=0, inf_home=4),
        'aitfosc': lambda: mission('CampAITFOsC', objset='SKIRMISH_AI_NORMAL_COMBAT_UNITS', tanks_home=0, inf_home=0),
        # round 88: AlwaysRecruit -- 4 Guardians go at ~s14 (ANY Guardian, MaxUnits 8), 2 more the AI builds itself after:
        # does the gone team take them (private ai/teams.py keep_recruiting, switched off: TeamMaker.keep_on False)?
        'aiar0': lambda: mission('CampAITFAr0', filt=objfilter('ANY', inc=(TANK,)), inf=0, inf_home=0, late=2,
                                 tanks_home=2),
        'aiar1': lambda: mission('CampAITFAr1', filt=objfilter('ANY', inc=(TANK,)), inf=0, inf_home=0, late=2,
                                 always=True, tanks_home=0),
        'aiar2': lambda: mission('CampAITFAr2', filt=objfilter('ANY', inc=(TANK,)), inf=0, inf_home=0, late=2,
                                 always=True, max_units=4, tanks_home=2),     # full at 4: no room for the late ones
        # round 89: aiar0-2 owned 4 Guardians throughout -- the opener built none. Why: the script-placed war factory
        # (aiar3: no Guardians placed, does it build the 2) or owning that template already (aiar4: 4 Guardians, the
        # opener builds 2 Riptides). Guesses: both built, then out with the team (homes 0).
        # Bench round 90 (factory still at -400, no Tech2): aiar3 owned 0 Guardians to s75 -- the Guardian needs
        # Upgrade_AlliedTech2, nobody had it. From round 90 every late build gives the yard Tech2, factory at -250.
        # Then (round 90, 坦克在家 / 坦克拥有): aiar0 built s20 / s30, both stay home (2/6); aiar1 built s19 -> taken s29,
        # s30 -> taken s56 (0/6): the gone team recruits on; aiar2 (full at 4) both stay (2/6); aiar3 (none placed) the
        # first s21 forms a team and goes s30, the second s32 stays (expectation 0 was a guess; reading 1).
        'aiar3': lambda: mission('CampAITFAr3', filt=objfilter('ANY', inc=(TANK,)), tanks=0, inf=0, inf_home=0, late=2,
                                 tanks_home=1),
        'aiar4': lambda: mission('CampAITFAr4', filt=objfilter('ANY', inc=(TANK, RIPTIDE)), second=RIPTIDE, inf=0,
                                 inf_home=0, late=2, late_unit=RIPTIDE, tanks_home=0),
        # round 91: which units a gone team holds -- at 70 s s1's default team is teleported 1200 south; a unit an AI team
        # took is no longer in it and stays (bench: does TEAM_TELEPORT move only the default team's?). 坦克在外 at 72 s
        # = late tanks nobody holds. aiar5 / 6: aiar0 / 1 (SimpleAttack, AlwaysRecruit off / on: 2 / 0 out);
        # aiar7 / 8: the same as LandDefense_MEDIUM's StaticDefense team (DEFENSE, DISBAND, at a friendly structure):
        # does a gone defense team recruit on (private teams.keep_on)? Guesses 2 / 0.
        # Bench round 91 (坦克在家 / 在外 / 拥有): 在外 0 in all four -- TEAM_TELEPORT_TO_WAYPOINT on teamSoviet_1 moved
        # nothing (aiar5's 2 free tanks home s30-s81), so the method fails; expectations set to the reading 0. aiar7
        # (off): 6 home and still s30-s81; aiar8 (on): home 6 -> 5 s42, 4 s43-58, 6 s60, 4 s69-78, 6 s80 -- the
        # late ones joined and the team shifts (INFERRED: a gone StaticDefense AlwaysRecruit team recruits on in a
        # quiet base; what holds LandDefense back in a skirmish is not this gate).
        'aiar5': lambda: mission('CampAITFAr5', filt=objfilter('ANY', inc=(TANK,)), inf=0, inf_home=0, late=2,
                                 tp_at=70.0, tanks_out=0),
        'aiar6': lambda: mission('CampAITFAr6', filt=objfilter('ANY', inc=(TANK,)), inf=0, inf_home=0, late=2,
                                 always=True, tp_at=70.0, tanks_out=0),
        'aiar7': lambda: mission('CampAITFAr7', filt=objfilter('ANY', inc=(TANK,)), inf=0, inf_home=0, late=2,
                                 static=True, tp_at=70.0, tanks_out=0),
        'aiar8': lambda: mission('CampAITFAr8', filt=objfilter('ANY', inc=(TANK,)), inf=0, inf_home=0, late=2,
                                 static=True, always=True, tp_at=70.0, tanks_out=0),
        # round 92: when does a gone defense team let go (in a full skirmish the defense team gave its units back:
        # round 51)? aiar9: aiar8 + at s45 a new AI plant 1000 south (FriendlyLandStructure, MaxTargets 1: does the guard
        # move there?); aiar10: aiar8 + placed tank 1 teleported 1200 south at s60 and s130 (held = it comes back).
        # Guesses: the team keeps its first target (0 at the plant); the tank is held both times (0 out at the end).
        # Bench round 92 (both PASS): aiar9 (在家 / 在新楼 / 拥有) 在新楼 0 to s107, home swings 6-4-6 as aiar8 -- the
        # guard never moved to the new plant. aiar10 (在家 / 在外 / 拥有): tank 1 out s60-64, home again by s70; out
        # s130-139, home by s145 -- back in ~10 s both times: a quiet base's defense team holds its members >= 130 s.
        'aiar9': lambda: mission('CampAITFAr9', filt=objfilter('ANY', inc=(TANK,)), inf=0, inf_home=0, late=2,
                                 static=True, always=True, plant_at=45.0, at_plant=0),
        'aiar10': lambda: mission('CampAITFAr10', filt=objfilter('ANY', inc=(TANK,)), inf=0, inf_home=0, late=2,
                                  static=True, always=True, tp_named=(60.0, 130.0), named_out=0),
    }
    return dict(MISSION=MISSION, shared=SimpleNamespace(
        INF=INF, RIPTIDE=RIPTIDE, TANK=TANK, mission=mission, objfilter=objfilter,))


@cache
def aiteams_bench():
    """Engine line D round 68: aicreate_bench's aicr3 plus one object of the AI's own, a copy of the Allied power plant
    with ra3ext's CNVTeams module (`<DeletionUpdate id="ModuleTag_CNVTeams" .../>`; a structure without CAN_ATTACK, so
    no team takes it), built with ext=True. Every EVERY frames the module logs the host owner's teams to the run folder's
    ra3ext.log (read by experimental/cnv/teamlog.py). Its check is benches/ai/tactics/checks.py#engine_aiteams.
    """
    import os

    import labpaths
    aicreate_mission = aicreate_bench()["shared"].mission
    from parts import Unit

    PLANT, HOST, EVERY, LINES = 'AlliedPowerPlant', 'CNVTeamsHost', 15, 4000


    def host_unit(cmd=False):
        """cmd: also ra3ext's CNVCmd module, which carries out the build's plan lines ("注入摆", inject.py pos())."""
        x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Structures', PLANT + '.xml'), encoding='utf-8').read()
        assert x.count(f'id="{PLANT}"') == 1 and x.count('<Behaviors>') == 1
        x = x.replace(f'id="{PLANT}"', f'id="{HOST}"').replace(f'EditorName="{PLANT}"', f'EditorName="{HOST}"')
        more = '\n\t\t\t<DeletionUpdate id="ModuleTag_CNVCmd" MinFrames="1" MaxFrames="1"/>' if cmd else ''
        x = x.replace('<Behaviors>', (
            f"""<Behaviors>\n"""
            f"""			<DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="{EVERY}" MaxFrames="{LINES}"/>{more}"""
        ))
        return Unit(HOST, x, names=dict(unit=HOST),
                    what=f'盟军电厂的复制（探针）：多一个 ra3ext 的 CNVTeams 模块，每 {EVERY} 帧记所属玩家的队伍和成员'
                         + ('；加 CNVCmd（按计划在指定帧摆物体）' if cmd else ''),
                    params=dict(of=PLANT, every=EVERY, cmd=cmd))


    def mission():
        m = aicreate_mission(3)
        m.name, m.ext = 'CampAICrT3', True
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
        return m


    MISSION = {'aicr3t': mission}
    return dict(MISSION=MISSION, shared=SimpleNamespace(HOST=HOST, host_unit=host_unit))


def aitoggle_bench():
    """Engine probe: when the skirmish AI's micro manager raises and lowers the Peacekeepers' riot shield (TOGGLE,
    TOGGLE_DEFENSE_SELF_ONLY; read back by benches/ai/tactics/checks.py#engine_aitoggle; engine line B).

    The data (SDK AlliedAntiInfantryInfantry): SpecialPower_ToggleRiotShield, two toggle states, TOGGLE_DEFAULT then
    TOGGLE_DEFENSE_SELF_ONLY with DontUseIfInRange; shield on = ObjectStatus GENERIC_TOGGLE_STATE (the check reads it with
    UNIT_HAS_OBJECT_STATUS). The program (work/re l4_toggle.md): on when an enemy targets the unit and (with
    DontUseIfInRange) its own target is not in its range; off on the same test negated, no hysteresis -- off the next micro
    round after nobody targets it. The model: RA3-EngineModel ra3model/ai/micro.py toggle / self_defence.

    The enemy s1 runs the same one-state personality as benches/ai/tactics/scenes.py#aimicro_bench (StaticDefense of its yard, team of exactly two
    Peacekeepers, StandardMicroManager: UpdateTime 0.5 s). The Peacekeepers stand 200 west of the s1 yard, 100 apart.
    The attacker is a player Twinblade (SovietAntiGroundAircraft, gun 150): a Peacekeeper's shotgun cannot hit the air
    (AntiMask ANTI_GROUND ...), so it has no target of its own in range and DontUseIfInRange never blocks the shield.
    At ATTACK_AT the script creates it 250 west of Peacekeeper 1 and orders it to attack Peacekeeper 1; at STOP_AT it is
    deleted (nobody targets anyone). Peacekeeper 2 is never targeted: its shield should stay down.
    The Peacekeepers must be known to the AI as units with powers (l4_specials.md: registered when made or
    changed hands with the AI awake; yet aimicro's hand-over 1 s after the wake did not make the warriors charge), so
    two builds:
      aitogglehand  the Peacekeepers start as the player's, handed to s1 at GIVE_AT (as benches/ai/tactics/scenes.py#aimicro_bench)
      aitogglemade  none placed: the script creates them on s1's team at GIVE_AT
      aitogglehunt  as aitogglemade, the team's tactic a Targetless Hunt instead of StaticDefense (round 18: does the micro
                    manager run only under some tactics? the Peacekeepers walk off towards the player; the Twinblade follows)
      aitogglexfer  as aitogglemade (StaticDefense), UNIT_AI_TRANSFER_ALL again right after making them (work/re
                    l4_micro_gate.md: units left on teamSoviet_1 are never recruited)
    Facts: wake at, give at, attack at, stop at, hunt (1: the Hunt tactic).
    """
    import resources
    from maps import niagara
    am = aimicro_bench()["shared"]
    from parts import Mission, Script

    WAKE_AT = am.WAKE_AT
    GIVE_AT = am.HAND_AT
    ATTACK_AT, STOP_AT = 20.0, 35.0
    PK, GUNSHIP = 'AlliedAntiInfantryInfantry', 'SovietAntiGroundAircraft'
    GUNSHIP_NAME = 'UNIT - CNV AT Gunship'
    WEST, APART, STANDOFF = 200.0, 100.0, 250.0


    def mission(name, made, tactic='StaticDefense', xfer=False):
        facts = {'wake at': WAKE_AT, 'give at': GIVE_AT, 'attack at': ATTACK_AT, 'stop at': STOP_AT, 'hunt': float(tactic == 'Hunt')}
        m = Mission(name=name, map=resources.measured(niagara), facts=facts)
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{am.PID}'}
        m.assets.append((f'{am.PID}.xml', am.personality_xml('StandardMicroManager', PK, tactic),
                         f'AIPersonalityDefinition:{am.PID}'))
        m.cnv_units = (PK,)
        s1 = m.player('s1')
        m.put('AlliedConstructionYard', 'east base', 0, 0, side='s1', name='UNIT - CNV AI Yard', role='ai yard')
        m.put('AlliedConstructionYard', 'base yard', name='UNIT - CNV AI Player Yard', role='player yard')
        m.spawns |= {PK, GUNSHIP}
        m.cnv_named = {'gunship': GUNSHIP_NAME}
        pks = []
        for k in range(2):
            dy = APART * (k - 0.5)
            n = f'UNIT - CNV AT Peacekeeper {k + 1}'
            pks.append(n)
            if made:
                m.waypoint(f'peacekeeper {k + 1} spot', f'CNV AT Peacekeeper Spot {k + 1}', 'east base', -WEST, dy)
                m.cnv_named[f'peacekeeper {k + 1}'] = n
            else:
                m.put(PK, 'east base', -WEST, dy, side='p1', angle=3.1416, name=n, role=f'peacekeeper {k + 1}')
        m.waypoint('gunship spot', 'CNV AT Gunship Spot', 'east base', -WEST - STANDOFF, -APART / 2)
        base = 'CNV AI Base'
        m.waypoint('ai base', base, 'east base')
        give = ([('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', n, PK, m.team('s1'), m.mark(f'peacekeeper {k + 1} spot'))
                 for k, n in enumerate(pks)] if made else [('NAMED_TRANSFER_OWNERSHIP_PLAYER', n, s1) for n in pks])
        give += [('UNIT_AI_TRANSFER_ALL', s1, 1)] if xfer else []   # round 18: as benches/ai/tactics/scenes.py#aimicro_bench xfer
        m.scripts += [
            Script('CNV AI - Start', [], [('PLAYER_SET_MONEY', s1, 0), ('SET_MILLISECOND_TIMER', 'CNV AI Wake', WAKE_AT),
                                          ('SET_MILLISECOND_TIMER', 'CNV AI Give', GIVE_AT),
                                          ('SET_MILLISECOND_TIMER', 'CNV AT Attack', ATTACK_AT),
                                          ('SET_MILLISECOND_TIMER', 'CNV AT Stop', STOP_AT)]),
            Script('CNV AI - Wake', [('TIMER_EXPIRED', 'CNV AI Wake')],
                   [('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, base),
                    ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20), ('SKIRMISH_AI_USE_REPAIRS', s1, 0),
                    ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0), ('PLAYER_SET_MONEY', s1, 0)]),
            Script('CNV AI - Give', [('TIMER_EXPIRED', 'CNV AI Give')], give),
            Script('CNV AT - Attack', [('TIMER_EXPIRED', 'CNV AT Attack')],
                   [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', GUNSHIP_NAME, GUNSHIP, m.team('p1'), m.mark('gunship spot')),
                    *m.order('attack', [GUNSHIP_NAME], pks[0], 'p1')]),
            Script('CNV AT - Stop', [('TIMER_EXPIRED', 'CNV AT Stop')], [('NAMED_DELETE', GUNSHIP_NAME)])]
        return m


    # bench 2026-11-07 first run (attack 30 / stop 45): the Allied barracks gave the second Peacekeeper only at ~s51
    BUILT_ATTACK_AT, BUILT_STOP_AT = 70.0, 85.0
    HUNT_DELAY = 12.0   # aitogglebltf: seconds after s1 owns two before the gunship (the Hunt recruits ~10-20 s after)


    def built(name, tactic='StaticDefense'):
        """aitogglebuilt (round 19): the AI builds the two Peacekeepers itself (benches/ai/tactics/scenes.py#aimicro_bench built_base: an opening
        move, an Allied barracks 400 south of the yard). The units are unnamed: the check counts by player. Once s1 owns
        two, the barracks is deleted (nothing but the Peacekeepers for the gunship to hit near there); at BUILT_ATTACK_AT
        the gunship is made 300 south of the barracks spot and attack-moves to it; deleted at BUILT_STOP_AT.
        tactic 'Hunt' (aitogglebltf, round 20, as benches/ai/tactics/scenes.py#aimicro_bench aimicbuiltf): a Targetless Hunt team recruits them and
        walks them off; once s1 owns two, all three of s1's structures are deleted and HUNT_DELAY later the gunship is
        made at the barracks spot and HUNTs (TEAM_HUNT) -- the Peacekeepers are the only thing of s1's left to aim at.
        (Bench 11-07: TEAM_HUNT at s70 never hit them; attack-move at the moment of two owned killed both by s41 with no
        shield -- likely before the Hunt took them.) The check's 帧数 still counts from BUILT_ATTACK_AT; 曾盾 counts from
        the first shield whenever."""
        hunt = tactic == 'Hunt'
        facts = {'wake at': WAKE_AT, 'give at': 0.0, 'attack at': BUILT_ATTACK_AT, 'stop at': BUILT_STOP_AT,
                 'hunt': float(hunt), 'built': 1.0}
        m = Mission(name=name, map=resources.measured(niagara), facts=facts)
        m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{am.PID}'}
        m.assets.append((f'{am.PID}.xml', am.personality_xml('StandardMicroManager', PK, tactic, built=True),
                         f'AIPersonalityDefinition:{am.PID}'))
        m.cnv_units = (PK,)
        m.spawns |= {PK, GUNSHIP}
        m.cnv_named = {'gunship': GUNSHIP_NAME}
        am.built_base(m, 'AlliedBarracks')
        m.waypoint('gunship spot', 'CNV AT Gunship Spot', 'east base', 0, am.BARRACKS_DY - 300)
        m.scripts += [
            Script('CNV AT - Timers', [], [('SET_MILLISECOND_TIMER', 'CNV AT Attack', BUILT_ATTACK_AT),
                                           ('SET_MILLISECOND_TIMER', 'CNV AT Stop', BUILT_STOP_AT)]),
            Script('CNV AT - Clear', [('COUNTER', 'CNV_AI_Owned', 3, 2)],
                   [('NAMED_DELETE', n) for n in ('UNIT - CNV AI Factory',
                                                  *(('UNIT - CNV AI Plant', 'UNIT - CNV AI Yard') if hunt else ()))]),
            *([Script('CNV AT - Go timer', [('COUNTER', 'CNV_AI_Owned', 3, 2)],
                      [('SET_MILLISECOND_TIMER', 'CNV AT Go', HUNT_DELAY)])] if hunt else []),
            Script('CNV AT - Attack', [('TIMER_EXPIRED', 'CNV AT Go')] if hunt else [('TIMER_EXPIRED', 'CNV AT Attack')],
                   [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', GUNSHIP_NAME, GUNSHIP, m.team('p1'),
                     m.mark('factory spot' if hunt else 'gunship spot')),
                    *(m.order('hunt', [GUNSHIP_NAME], None, 'p1') if hunt else
                      m.order('attack_move', [GUNSHIP_NAME], m.mark('factory spot'), 'p1'))]),
            Script('CNV AT - Stop', [('TIMER_EXPIRED', 'CNV AT Stop')], [('NAMED_DELETE', GUNSHIP_NAME)])]
        return m


    MISSION = {'aitogglebuilt': lambda: built('CampAITogBuilt'),
               'aitogglebltf': lambda: built('CampAITogBltF', tactic='Hunt'),
               'aitogglehand':lambda: mission('CampAITogHand', made=False),
               'aitogglemade': lambda: mission('CampAITogMade', made=True),
               'aitogglehunt': lambda: mission('CampAITogHunt', made=True, tactic='Hunt'),
               'aitogglexfer': lambda: mission('CampAITogXfer', made=True, xfer=True)}
    return dict(MISSION=MISSION)


def aitransport_bench():
    """B-line Tactic UseTransports pair: a SimpleAttack team of four Peacekeepers and a Riptide, the target over water.

    aiteamfilter_bench's set-up (Niagara, s1 Allied with a yard, one always-on state, SimpleAttack at the closest enemy
    structure, KindOf CAN_ATTACK, MaxUnits 8, LAND AMPHIBIOUS) with Niagara's six bridge pieces removed (aibridge_bench's
    trick), so the east bank is cut off from Goat Island and the west bank. The player's target plant stands on Goat
    Island ('station'). s1 has four Peacekeepers (cannot cross) and one Riptide ACV (AlliedAntiInfantryVehicle:
    TRANSPORT AMPHIBIOUS, TransportContain ContainMax 5). Only the tactic's UseTransports differs (retail's 27 levels
    write it false 14 times; its default is true).

    Read rule (work/re b221): the flag is read once, in SimpleAttack's per-frame update; true -> while the team still has
    passenger / transport pairs not boarded, the update returns without a move order (they board first); false -> the
    team attack-moves at once. Pairing itself (at recruiting) ignores the flag. Prediction: true -> the Peacekeepers
    ride the Riptide over; false -> the Riptide crosses empty, the Peacekeepers stay on the east bank.
    """
    from types import SimpleNamespace

    team_mission = aiteamfilter_bench()["shared"].mission
    RIPTIDE = aiteamfilter_bench()["shared"].RIPTIDE
    from missions.aiskirm_bench import ai_map
    HOST = aiteams_bench()["shared"].HOST
    host_unit = aiteams_bench()["shared"].host_unit

    TWINBLADE = 'SovietAntiGroundAircraft'          # AIRCRAFT TRANSPORT, TransportContain ContainMax 5, takes INFANTRY
    TACTIC = '<Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE" EndIfStateTurnsOff="true"'


    def mission(use, inf=4, name=None, site='station', boat=RIPTIDE):
        locos = 'LAND AMPHIBIOUS AIR' if boat == TWINBLADE else 'LAND AMPHIBIOUS'
        m = team_mission(name or f'CampAITrans{int(use)}', tanks=0, inf=inf, inf_home=inf, locos=locos)
        m.map = SimpleNamespace(**vars(ai_map(m.map, library=False)))
        assert all(o.template == 'HB_Bridge_02' for o in m.map.OBJECTS[:6])
        m.map.OBJECTS = m.map.OBJECTS[6:]                       # no bridges: the east bank is cut off
        target = next(o for o in m.objects if o.name == 'UNIT - CNV AI Player Target')
        if site:                                                # None: aiteamfilter's 'east gate' plant (B223)
            target.x, target.y = m.site(site)
        m.put(boat, 'east base', -350.0, -160.0, side='s1', angle=3.1416, name='UNIT - CNV AI Riptide',
              role='ai riptide')
        m.spawns |= {boat}
        # B222: the ra3ext host (team: samples, tgt: picks) tells "no team" from "a team that does not move"
        m.ext, m.ext_logs = True, ('target',)
        m.units.append(host_unit())
        m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
        m.facts |= {'use transports': int(use), 'target on island': int(site == 'station'),
                    'target x': target.x, 'target y': target.y, 'air transport': int(boat == TWINBLADE)}
        filename, xml, asset = m.assets[0]
        assert TACTIC in xml
        xml = xml.replace(TACTIC, f'{TACTIC} UseTransports="{str(use).lower()}"')
        m.assets[0] = filename, xml, asset
        return m


    def player_shot():
        """E 11-21: aitranst0's Twinblade hits the plant at half the data's rate (every other rocket clip misses). Here
        the Twinblade is the player's own, put on the line it hovered on (400 out, east-north-east of the plant), and a
        script force-attacks the plant: no AI orders. Every clip lands -> the AI's re-sent orders cost the clips."""
        m = mission(False, inf=0, name='CampAITransTP')         # the Riptide alone: nobody is recruited (B222 aitransr)
        m.put(TWINBLADE, 'station', 344.0, 204.0, angle=-2.6, name='UNIT - CNV Twinblade', role='player twinblade')
        m.facts |= {'air transport': 1, 'player shot': 1}
        return m


    # B222: aitrans0 / 1 with the ra3ext host: the target pick finds the island plant, the team is made (f17) and
    # stays empty, remade every ~90 frames -- nobody is recruited. aitransr: the Riptide alone (no infantry), the
    # flag at its default: is the Riptide itself turned away (its own way to the island, or as a transport) or do the
    # unpairable infantry block the whole recruit?
    MISSION = {'aitrans0': lambda: mission(False), 'aitrans1': lambda: mission(True),
               'aitransr': lambda: mission(True, inf=0, name='CampAITransR'),
               # the Riptide alone is not taken either: the island itself (its way there) is what turns it away. The
               # same three with the plant on the west bank's bridge landing ('front'): water-only for both
               'aitransw0': lambda: mission(False, name='CampAITransW0', site='front'),
               'aitransw1': lambda: mission(True, name='CampAITransW1', site='front'),
               'aitransrw': lambda: mission(True, inf=0, name='CampAITransRW', site='front'),
               # B223: the Riptide alone, still no bridges, the plant back on the east bank's land ('east gate', where
               # aitfamph took Riptides): taken -> "no way there" turns it away on the island / west bank; not taken ->
               # this bench itself (no bridges, no library, LAND AMPHIBIOUS) turns the Riptide away
               'aitransre': lambda: mission(True, inf=0, name='CampAITransRE', site=None),
               # B 11-21: the recruit gate (work/re b1121_transports.md) takes an aircraft always and, when a unit cannot
               # reach the target, tries it again with a member that can carry it (their surfaces or'd): a Twinblade
               # (AIR) in the team lets the Peacekeepers in as its passengers, so the pair forms and the flag can tell
               'aitranst0': lambda: mission(False, name='CampAITransT0', boat=TWINBLADE),
               'aitranst1': lambda: mission(True, name='CampAITransT1', boat=TWINBLADE),
               'aitranstp': player_shot}
    return dict(MISSION=MISSION)


def k2gate_bench():
    """One open recruitment slot, a Guardian in pre-attack, and an idle fallback."""

    from dataclasses import replace
    from pathlib import Path
    import re

    import labpaths
    combat_mission = aicombat_bench()["shared"].mission
    TANK = aiteamfilter_bench()["shared"].TANK
    HOST = aiteams_bench()["shared"].HOST
    host_unit = aiteams_bench()["shared"].host_unit
    from parts import Script, Unit


    FIGHTER = 'CNVK2Guardian'
    PRE_ATTACK = 60
    ORDER_AT = 2.0


    def pre_attack_guardian():
        sage = Path(labpaths.SDK3) / 'SageXML'
        cannon = TANK + 'Cannon'
        marker = FIGHTER + 'Cannon'
        xml = (sage / 'Allied' / 'Units' / f'{TANK}.xml').read_text(encoding='utf-8')
        xml = xml.replace(f'id="{TANK}"', f'id="{FIGHTER}"')
        xml = xml.replace(f'EditorName="{TANK}"', f'EditorName="{FIGHTER}"')
        xml = xml.replace(f'Template="{cannon}"', f'Template="{marker}"')
        weapons = (sage / 'GlobalData' / 'Weapon.xml').read_text(encoding='utf-8')
        weapon = re.search(rf'<WeaponTemplate\s+id="{cannon}".*?</WeaponTemplate>', weapons, re.S).group()
        assert '<PreAttackDelay' not in weapon and 'AttackRange="150.0"' in weapon
        weapon = weapon.replace(f'id="{cannon}"', f'id="{marker}"')
        pre_attack = f'<PreAttackDelay MinSeconds="{PRE_ATTACK}s" MaxSeconds="{PRE_ATTACK}s"/>'
        weapon = weapon.replace('<FiringDuration', pre_attack + '\n\t\t<FiringDuration')
        return Unit(FIGHTER, xml.replace('</AssetDeclaration>', weapon + '\n</AssetDeclaration>'),
                    link=[f'WeaponTemplate:{marker}'], what='守护者探针，主炮预瞄 60 秒')


    def mission(allow):
        m = combat_mission(allow)
        m.name = f'CampK2Gate{int(allow)}'
        m.ext = True
        m.units += [pre_attack_guardian(), host_unit()]
        m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
        fighter = m.role('candidate fighter').name
        foe = m.role('player foe').name
        m.find(fighter).template = FIGHTER
        m.cast['candidate fighter'] = replace(m.role('candidate fighter'), template=FIGHTER)
        # With no return fire, a 100% foe health sample is a clean no-hit check.
        m.scripts = [script for script in m.scripts if script.name != 'CNV Combat - hold health']
        m.scripts.append(Script('CNV K2 - passive target', [], [('UNIT_CHANGE_OBJECT_STATUS', foe, 'NO_ATTACK', 1)]))
        m.facts |= {'order at': ORDER_AT, 'pre-attack': PRE_ATTACK}
        return m


    MISSION = {'k2gate0': lambda: mission(False), 'k2gate1': lambda: mission(True)}
    return dict(MISSION=MISSION)


BENCHES = (
    aialphaclose_bench, aialphahp_bench, aibasedef_bench, aicannot_bench,
    aicombat_bench, aicreate_bench, aicrush_bench, aidefense_bench,
    aidelay_bench, aidiff_bench, aidistance_bench, aiengineer_bench,
    aifallback_bench, aigarrison_bench, aihome_bench, aimicro_bench,
    aineutralgarr_bench, aiorders_bench, aipassive_distance_bench, aipathcheck_bench,
    aipullback_bench, aipullpct_bench, aireactive_bench, airelease_bench,
    airetreat_bench, aisort_bench, aispecial_bench, aiswitch_bench,
    aitactical_bench, aiteamfields_bench, aiteamfilter_bench, aiteams_bench,
    aitoggle_bench, aitransport_bench, k2gate_bench,
)
