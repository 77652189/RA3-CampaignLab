"""Point water search, retail NearbyWaterPointHeuristic versus range 1.

Predictions: range 1500 can find a water point; range 1 around the dry main
base cannot (INFERRED, not measured). Exact point generation remains a gap.
No object, waypoint or expansion node is supplied as a Point substitute.
Measured: both ranges found a non-object target at frame 16 and had total/home
4/0 at second 25. Range-1 negative prediction failed. Real point coordinates,
search origin and point candidates are unavailable; see work/re/c_point_report.md.
"""
from missions.aitargetpick_bench import mission
from missions.aiteams_bench import HOST, host_unit


def point(name, radius):
    m = mission(name, [('NearbyWaterPointHeuristic', None)], (0, 0, 0, 4))
    m.ext = True
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
    m.facts['point range'] = radius
    asset, xml, ref = m.assets[0]
    heuristic = (
        '<AITargetingHeuristic id="NearbyWaterPointHeuristic" HeuristicType="Point" '
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
