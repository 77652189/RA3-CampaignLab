"""C conyard entrance diagnostic: only the minimum distance differs (0/300).

Uses the existing Japan unpack host. Eligibility must be measured before any
distance claim. INFERRED prediction: if a core becomes eligible, 300 excludes
points close to the real yard exit until the original 15s exemption applies.
An unchanged core is a recruitment gate, not proof of the distance rule.
"""
from missions.aiplacement_bench import mission as placement_mission


def mission(minimum):
    m = placement_mission(200, japan=True)
    m.name = 'CampYard' + str(minimum)
    filename, xml, asset = m.assets[0]
    xml = xml.replace('MinDistanceFromConyardEntrance="0"',
                      f'MinDistanceFromConyardEntrance="{minimum}"')
    m.assets[0] = filename, xml, asset
    m.facts['conyard entrance minimum'] = minimum
    m.ext_logs = ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
    return m


MISSION = {'aicyard0': lambda: mission(0), 'aicyard300': lambda: mission(300)}
