"""MaxDistanceToShore single-target contrast; evidence: work/re/c_shore_report.md.

The power plant is on the east bank, clear of the water. Predict 2000 permits
it, 1 rejects it; EnemyStructure is the host control. Exact shore distance and
the engine's shoreline sampling remain unmeasured.
"""
from missions.aipoweradv_bench import mission


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
