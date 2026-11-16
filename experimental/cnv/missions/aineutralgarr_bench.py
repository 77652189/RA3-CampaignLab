"""NeutralGarrison selection: retail garrisonable row house versus neutral oil derrick.

SDK AM_RowHouse01 inherits BaseCivilianStructureSmall (ContestableGarrisonContain).
Garrison/Garrison_EASY consume GarrisonHeuristic. This isolates strategic selection
with SimpleAttack; entering, occupancy, ownership and capacity remain gaps.
Native selection in both builds is the existing map HV_Shop01 at (3180,2760).
The added row house is eligible; the oil derrick is absent from the native
candidate set. NamedObject identifies the placed control in both builds.
See work/re/c_garrison_report.md.
"""
from missions.aitargetpick_bench import mission, state_xml
from missions.aiteams_bench import HOST, host_unit


def garrison(real=True):
    m = mission('CampGarrOn' if real else 'CampGarrOff',
                [('GarrisonHeuristic', None)], (0, 0, 0, 4))
    m.ext = True
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
    m.put('AM_RowHouse01' if real else 'OilDerrick', 'east gate', -250, 0,
          side='neutral', name='UNIT - Garr Control', role='garr control')
    asset, xml, ref = m.assets[0]
    extra = ('<AITargetingHeuristic id="CNVGarrNamed" HeuristicType="NamedObject" '
             'Name="UNIT - Garr Control" RequireUniqueTarget="false"/>\n'
             + state_xml('CNVGarrNamedState', [('CNVGarrNamed', None)], 1))
    xml = xml.replace('<AIStrategicStateDefinition ', extra + '\n<AIStrategicStateDefinition ', 1)
    xml = xml.replace('    <StrategicState id="CNVStateTP" State="CNVStateTP"/>',
                      '    <StrategicState id="CNVStateTP" State="CNVStateTP"/>\n'
                      '    <StrategicState id="CNVGarrNamedState" State="CNVGarrNamedState"/>')
    m.assets[0] = asset, xml, ref
    return m


MISSION = {'aigarron': garrison, 'aigarroff': lambda: garrison(False)}

