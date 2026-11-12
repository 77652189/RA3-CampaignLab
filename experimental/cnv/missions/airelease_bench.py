"""C independent release pair: two fixed Guardians, defense then timed attack.

Only the defense TeamTemplate.ReleaseType differs. Named team counters must
show initial recruitment before any later absence can mean release.
"""
from missions.aiteamfilter_bench import mission as team_mission
from missions.aiskirm_bench import ai_map


def mission(never):
    m = team_mission('CampAIRel',
                     tanks=2, inf=0, max_units=2, static=True,
                     kinds='IncludeKindOf="VEHICLE"')
    m.name = 'CampAIRelNever' if never else 'CampAIRelPrio'
    m.map = ai_map(m.map, library=False)
    filename, xml, asset = m.assets[0]
    release = 'NEVER_RELEASE' if never else 'RELEASE_TO_PRIORITY'
    xml = xml.replace('<TeamTemplate ', f'<TeamTemplate ReleaseType="{release}" ', 1)
    attack = '''  <AIStrategicStateDefinition id="CNVReleaseAttack" MaxTargets="1">
    <Heuristic><TimerHeuristic StartTime="35s" EndTime="-1s"/></Heuristic>
    <TargetHeuristic TargetHeuristic="ClosestStructureHeuristic"/>
    <Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE">
      <TeamTemplate MinUnits="2" MaxUnits="2" IncludeKindOf="VEHICLE"
        AllowedLocomotorTypes="LAND AMPHIBIOUS" Priority="STANDARD"
        MicroManager="StandardMicroManager_MEDIUM"/>
    </Tactic>
  </AIStrategicStateDefinition>
'''
    xml = xml.replace('  <AIPersonalityDefinition ', attack + '  <AIPersonalityDefinition ')
    xml = xml.replace('    <StrategicState id="CNVStateTF" State="CNVStateTF"/>',
                      '    <StrategicState id="CNVStateTF" State="CNVStateTF"/>\n'
                      '    <StrategicState id="CNVReleaseAttack" State="CNVReleaseAttack"/>')
    m.assets[0] = filename, xml, asset
    m.map.TEAMS.update({'release defense': 'Soviet_1/CNVStateTF_StaticDefense_0_0',
                        'release attack': 'Soviet_1/CNVReleaseAttack_SimpleAttack_0_0'})
    m.facts.update({'never release': int(never), 'attack at': 35.0})
    return m


MISSION = {'airelnever': lambda: mission(True), 'airelprio': lambda: mission(False)}
