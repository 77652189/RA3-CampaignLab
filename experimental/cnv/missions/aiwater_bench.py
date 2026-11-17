"""ThreatToWater sorting contrast; see work/re/c_water_report.md.

Two power plants: the nearer has a Guardian nearby, the farther is undefended.
Distance predicts near; the model's INFERRED water threat predicts far. Named
controls check reachability only, not same-frame candidate qualification.
An AI ore collector supplies an amphibious sample without joining the team.
"""
import dataclasses

from missions.aitargetpick_bench import mission


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


MISSION = {
    'aiwaterdist': lambda: water('CampWaterDist', 'Distance'),
    'aiwaterthreat': lambda: water('CampWaterThrt'),
    'aiwaternear': lambda: water('CampWaterNear', named='plant'),
    'aiwaterfar': lambda: water('CampWaterFar', named='barracks'),
}
