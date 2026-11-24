"""ThreatToWater sorting contrast (and ThreatToAir, air()); see work/re/c_water_report.md.

Two power plants: the nearer has a Guardian nearby, the farther is undefended.
Distance predicts near; the model's INFERRED water threat predicts far. Named
controls check reachability only, not same-frame candidate qualification.
An AI ore collector supplies an amphibious sample without joining the team.
"""
import dataclasses

from missions.aitargetpick_bench import mission
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
