"""BridgeHeuristic on one genuine 700-unit native bridge versus an ordinary plant.

The SDK defines BridgeHeuristic but has no named consumer in SkirmishAI XML.
Use the original heuristic in CNVStateTP and NamedObject on both map endpoints.
No KindOf edits. Generated bridge parts are counted independently by the check.
Prediction: Bridge selects a real bridge, never the ordinary neutral plant;
the endpoint names test identity rather than assuming builder names survive.
BENCH disproves the positive prediction: Bridge finds neither; only the real
start builder remains named. Registration/qualification remain unresolved.
See work/re/c_bridge_report.md.
"""
from types import SimpleNamespace

import platmap
from maps import island
from missions.aitargetpick_bench import mission, state_xml
from missions.aiteams_bench import HOST, host_unit
from parts import square


def bridge(real=True):
    m = mission('CampBrTarget' if real else 'CampBrControl',
                [('BridgeHeuristic', None)], (0, 0, 0, 4))
    m.ext = True
    m.map = SimpleNamespace(**vars(m.map))
    m.map.OBJECTS = m.map.OBJECTS[6:]  # no inherited bridges in either control
    m.map.PLAYERS = {**m.map.PLAYERS, **island.NEUTRAL}
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
    origin = m.site('front')
    endpoints = platmap.bridge((2250, 4200), (2950, 4200))
    for i, (x, y, angle, flags) in enumerate(endpoints):
        m.put('HB_Bridge_02' if real else 'AlliedPowerPlant', 'front',
              x-origin[0], y-origin[1], side='neutral', angle=angle,
              flags=flags if real else 0, name=f'UNIT - Bridge {i}', role=f'bridge {i}')
    m.facts['native bridge'] = real
    m.areas['Bridge count'] = square(2600, 4200, 650)
    m.spawns.update('HB_Bridge_02_' + suffix for suffix in
                    ('End', 'End2', 'Center', 'Center2', 'GateHouse'))
    asset, xml, ref = m.assets[0]
    extra = []
    for i in range(2):
        hid, sid = f'CNVBridgeNamed{i}', f'CNVBridgeNamedState{i}'
        extra += [f'<AITargetingHeuristic id="{hid}" HeuristicType="NamedObject" '
                  f'Name="UNIT - Bridge {i}" RequireUniqueTarget="false"/>',
                  state_xml(sid, [(hid, None)], 1)]
        xml = xml.replace('    <StrategicState id="CNVStateTP" State="CNVStateTP"/>',
                          '    <StrategicState id="CNVStateTP" State="CNVStateTP"/>\n'
                          f'    <StrategicState id="{sid}" State="{sid}"/>')
    xml = xml.replace('<AIStrategicStateDefinition ', '\n'.join(extra) + '\n<AIStrategicStateDefinition ', 1)
    m.assets[0] = asset, xml, ref
    return m


MISSION = {'aibridgeon': bridge, 'aibridgeoff': lambda: bridge(False)}
