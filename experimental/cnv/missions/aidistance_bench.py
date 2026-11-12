"""C-line StaticDefense Distance pair; identical retained AI team and teleport.

At 30s one Guardian is teleported 1200 south on open grass, without a team
transfer or movement order. Prediction: Distance 250 returns it; Distance
2000 accepts the displacement. Aesthetics is enabled identically in both;
its actual stand-point selection remains a gap, not a fitted rule.
"""
from missions.aiteamfilter_bench import mission as team_mission
from missions.aiskirm_bench import ai_map
from missions.aiteams_bench import HOST, host_unit
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
