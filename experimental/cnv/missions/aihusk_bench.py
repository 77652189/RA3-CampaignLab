"""Husk negative: an ordinary neutral oil derrick is not a land husk.

The NamedObject control selects the exact same placed derrick. No synthetic
HUSK flag or pretend wreck is supplied. Real wreck registration remains a gap.
Prediction before running: LandHuskHeuristic finds nothing; named control finds
the derrick. Team arrival is outside this selection-only probe.
"""
from missions.aitargetpick_bench import mission
from missions.aiteams_bench import HOST, host_unit


def husk(named=False):
    heuristic = 'CNVHuskNamed' if named else 'LandHuskHeuristic'
    m = mission('CampHuskNamed' if named else 'CampHuskNone',
                [(heuristic, None)], (0, 0, 0, 4))
    m.ext = True
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
    m.put('OilDerrick', 'east gate', -250, 0, side='neutral',
          name='UNIT - Husk Oil Control', role='husk oil control')
    if named:
        asset, xml, ref = m.assets[0]
        xml = xml.replace('<AIStrategicStateDefinition ',
            '<AITargetingHeuristic id="CNVHuskNamed" HeuristicType="NamedObject" '
            'Name="UNIT - Husk Oil Control"/>\n<AIStrategicStateDefinition ', 1)
        m.assets[0] = asset, xml, ref
    return m


MISSION = {'aihusknone': husk, 'aihusknamed': lambda: husk(True)}
