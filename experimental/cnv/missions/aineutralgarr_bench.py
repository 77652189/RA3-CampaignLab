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
    m.ext, m.ext_logs = True, ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
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


RETAIL_GARRISON = '''<Tactic id="Garrison" Tactic="GarrisonBuilding" EndBehavior="DISBAND">
      <TeamTemplate MinUnits="1" MaxUnits="2"
                    RegisteredObjectSet="INFANTRY"
                    IncludeKindOf="CAN_ATTACK INFANTRY" ExcludeKindOf="SKIRMISH_AI_DONT_GARRISON IGNORES_SELECT_ALL HARVESTER"
                    Priority="STANDARD" AlwaysRecruit="false"
                    MicroManager="StandardMicroManager"/>
    </Tactic>'''


def building():
    """aigarrbld: retail's Garrison state whole (SkirmishAI AIStateLibrary: GarrisonBuilding over GarrisonHeuristic,
    a team of 1-2 INFANTRY, EndBehavior DISBAND) for 2 Peacekeepers of s1 and no tanks; the row house of aigarron
    and the map's own shop are the two neutral candidates (B: does the team go in, which house, when)."""
    from missions.aitarget_bench import INF
    m = mission('CampGarrBld', [('GarrisonHeuristic', None)], (0, 0, 0, 0), tanks=0)
    m.ext, m.ext_logs = True, ('target',)
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
    m.spawns |= {'HV_Shop01'}                    # the map's own shop, counted by template (published for the counter)
    m.put('AM_RowHouse01', 'east gate', -250, -150, side='neutral', name='UNIT - Garr Control', role='garr control')
    for k in range(2):
        m.put(INF, 'east base', -200.0, 160.0 + 70.0 * k, side='s1', angle=3.1416, name=f'UNIT - CNV AI Inf {k + 1}',
              role=f'ai inf {k + 1}')
    asset, xml, ref = m.assets[0]
    start = xml.index('<Tactic id="Attack"')
    m.assets[0] = asset, xml[:start] + RETAIL_GARRISON + xml[xml.index('</Tactic>', start) + len('</Tactic>'):], ref
    return m


MISSION = {'aigarron': garrison, 'aigarroff': lambda: garrison(False), 'aigarrbld': building}

