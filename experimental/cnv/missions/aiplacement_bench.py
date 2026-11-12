"""C: isolate the unpack placement search distance with one preplaced power core.

Prediction (INFERRED): distance 1 cannot fit the expanded footprint; 200 can.
Only the search distance differs. No automatic production or scripted unpack.
"""
from missions.aitargetpick_bench import mission as target_mission
from missions.aiteams_bench import HOST, host_unit


def mission(distance, japan=False):
    name = ('CampAIPlJ' if japan else 'CampAIPlace') + str(distance)
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
    m.assets[0] = filename, xml, asset
    m.cnv_units = ('JapanPowerPlantEgg',)
    m.spawns |= {'JapanPowerPlantEgg', 'JapanPowerPlant'}
    m.put('JapanPowerPlantEgg', 'east base', -400, 0, side='s1', role='core', name='UNIT - CNV Placement Core')
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
    m.ext = True
    m.facts['placement distance'] = distance
    m.facts['japan host'] = japan
    return m


MISSION = {'aiplace1': lambda: mission(1), 'aiplace200': lambda: mission(200),
           'aiplacej200': lambda: mission(200, japan=True)}
