"""C: isolate the unpack placement search distance with one preplaced power core.

Prediction (INFERRED): distance 1 cannot fit the expanded footprint; 200 can.
Only the search distance differs. No automatic production or scripted unpack.

B (aiplb*): the preplaced core never joined the team (work/re/c_placement_report.md). Guess: only a core the AI
builds itself is registered UNPACKS_INTO_BUILDING_UNITS. So aiplacej200 without the preplaced core, an opening that
builds one JapanPowerPlantEgg at the Japan yard, money at the wake, one Distance (600 / 1500, N = 1). Reading
(work/re/d63_b_fields.md 3): the plant lands (BaseCompactness 0.5 +- 0.05) x Distance from the centre, ~300 / ~750.
"""
from missions.aitargetpick_bench import mission as target_mission
from missions.aiteams_bench import HOST, host_unit

MONEY = 10000
OPENER = '''  <SkirmishOpeningMove id="CNVPlOpen" Side="PlayerTemplate:Japan">
    <Order Build="JapanPowerPlantEgg" />
    <Order Time="90s"/>
  </SkirmishOpeningMove>
'''
OPENING = '''    <OpeningMove Name="CNVPlOpen" Weight="100%"><Heuristic><ConstantHeuristic/></Heuristic></OpeningMove>
    <BuildState id="AlliedNeededUnits" xai:joinAction="Remove"/>
    <BuildState id="AlliedDefenseBuildState" xai:joinAction="Remove"/>
'''


def mission(distance, japan=False, built=False):
    name = ('CampAIPlB' if built else 'CampAIPlJ' if japan else 'CampAIPlace') + str(distance)
    m = target_mission(name, [('CNVPlacement', None)], (0, 0, 0, 0), tanks=0)
    filename, xml, asset = m.assets[0]
    xml = xml.replace('<AIStrategicStateDefinition ', f'''<AITargetingHeuristic id="CNVPlacement"
        HeuristicType="UnpackBuildingPlacement" MinDistanceFromConyardEntrance="0"
        IgnoreMinDistanceFromConyardEntranceForTime="15s">
      <BuildingPlacementDistance Distance="{distance}"/>
    </AITargetingHeuristic>
    <AIStrategicStateDefinition ''', 1)
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
