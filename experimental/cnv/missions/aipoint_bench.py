"""Point water search with distinct assets: range 1500 versus range 1.

D166 established that the old same-id override still loaded retail range 1500.
These new IDs test the actual radii. Predict water found at 1500, none at 1;
replay the native random candidates, without inventing a random seed/terrain.
See work/re/c_point_resume_report.md.
"""
from missions.aitargetpick_bench import mission
from missions.aiteams_bench import HOST, host_unit


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
