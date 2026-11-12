"""C-line aesthetics switch pair: Distance 2000, retained team, same teleport.

Only UseAestheticsManager differs. Prediction: enabled wanders to a stand
point, disabled returns to the defended structure after the 30s displacement.
Stand-point selection is INFERRED; see work/re/c_aesthetics_report.md.
"""
from missions.aidistance_bench import mission as distance_mission


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
