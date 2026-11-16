"""EnemyGarrison: genuinely occupied enemy house versus same-site enemy plant.

Script entry precedes strategic selection; counters independently verify ENCLOSED
and ownership. NamedObject is the identity control, not a substitute for selection.
See work/re/c_enemygarr_report.md.
"""
from missions.aitargetpick_bench import mission, state_xml
from missions.aiteams_bench import HOST, host_unit
from parts import Script


def enemy_garrison(real=True):
    m = mission('CampEGarrOn' if real else 'CampEGarrOff',
                [('EnemyGarrisonHeuristic', None)], (0, 0, 0, 4))
    m.ext, m.ext_logs = True, ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
    m.put('AM_RowHouse01' if real else 'AlliedPowerPlant', 'east gate', -250, 0,
          side='neutral' if real else 'p1', name='UNIT - EGarr Control', role='garr control')
    m.put('SovietAntiInfantryInfantry', 'east gate', -250, -80,
          side='p1', name='UNIT - EGarr Occupant', role='garr occupant')
    m.facts['enemy garrison'] = real
    m.scripts.append(Script('EGarr occupy', [],
        [('UNIT_CHANGE_OBJECT_STATUS', m.role('garr occupant').name, 'NO_ATTACK', 1)]
        + ([('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY',
             m.role('garr occupant').name, m.role('garr control').name)] if real else [])))
    asset, xml, ref = m.assets[0]
    extra = ('<AITargetingHeuristic id="CNVEGarrNamed" HeuristicType="NamedObject" '
             'Name="UNIT - EGarr Control" RequireUniqueTarget="false"/>\n'
             + state_xml('CNVEGarrNamedState', [('CNVEGarrNamed', None)], 1))
    xml = xml.replace('<AIStrategicStateDefinition ', extra + '\n<AIStrategicStateDefinition ', 1)
    xml = xml.replace('    <StrategicState id="CNVStateTP" State="CNVStateTP"/>',
                      '    <StrategicState id="CNVStateTP" State="CNVStateTP"/>\n'
                      '    <StrategicState id="CNVEGarrNamedState" State="CNVEGarrNamedState"/>')
    m.assets[0] = asset, xml, ref
    return m


MISSION = {'aiegarron': enemy_garrison, 'aiegarroff': lambda: enemy_garrison(False)}
