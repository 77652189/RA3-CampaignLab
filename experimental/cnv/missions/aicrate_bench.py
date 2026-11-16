"""Crate selection: retail HealCrate versus an ordinary neutral oil derrick.

Retail consumer: AIStateLibrary CratePickup -> CrateHeuristic (VitalKindOf
CRATE). Constant activation isolates selection from the retail interval gate;
this does not measure pickup, healing, ownership changes or crate lifetime.
Predict Crate selects only HealCrate; the independent NamedObject slot selects
the placed object in both builds. See work/re/c_crate_report.md.
"""
from missions.aitargetpick_bench import mission, state_xml
from missions.aiteams_bench import HOST, host_unit


def crate(real=True):
    m = mission('CampCrateOn' if real else 'CampCrateOff',
                [('CrateHeuristic', None)], (0, 0, 0, 4))
    m.ext, m.ext_logs = True, ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
    m.put('HealCrate' if real else 'OilDerrick', 'east gate', -250, 0,
          side='neutral', name='UNIT - Crate Control', role='crate control')
    asset, xml, ref = m.assets[0]
    extra = ('<AITargetingHeuristic id="CNVCrateNamed" HeuristicType="NamedObject" '
             'Name="UNIT - Crate Control" RequireUniqueTarget="false"/>\n'
             + state_xml('CNVCrateNamedState', [('CNVCrateNamed', None)], 1))
    xml = xml.replace('<AIStrategicStateDefinition ', extra + '\n<AIStrategicStateDefinition ', 1)
    xml = xml.replace('    <StrategicState id="CNVStateTP" State="CNVStateTP"/>',
                      '    <StrategicState id="CNVStateTP" State="CNVStateTP"/>\n'
                      '    <StrategicState id="CNVCrateNamedState" State="CNVCrateNamedState"/>')
    m.assets[0] = asset, xml, ref
    return m


MISSION = {'aicrateon': crate, 'aicrateoff': lambda: crate(False)}
