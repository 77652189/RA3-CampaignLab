"""Retail MinEnemyValue 1000/2500: one 1000 miner versus 2400/3800.

Four independent team counters: 1000/one, 2500/one, 2500/two,
2500/summed inverted. Corrected data prediction: low 0/4/4/0,
high 0/4/0/4. Initial wrong cost prediction retained in the private report.
Retail dependency evidence: work/re/c_minvalue_retail.json.
"""
from missions import aistate_bench as setup


def mission(high=False):
    m = setup.mission('CampAIMinHi' if high else 'CampAIMinValue', near=True)
    units = (setup.INF, setup.TANK, 'SovietAntiInfantryInfantry', 'SovietAntiVehicleInfantry')
    cases = ((1000, False, True), (2500, False, True),
             (2500, True, True), (2500, True, False))
    filename, xml, asset = m.assets[0]
    states = []
    for i, (unit, (minimum, both, nearby)) in enumerate(zip(units, cases)):
        objects = ('AlliedMiner', 'SovietMiner') if both else ('AlliedMiner',)
        gate = (f'<EnemyNearbyHeuristic Distance="700" MinEnemyValue="{minimum}" '
                f'EnemyNearby="{str(nearby).lower()}"><EnemyFilter Relationship="ENEMIES" Rule="ANY">'
                + ''.join(f'<IncludeThing>{obj}</IncludeThing>' for obj in objects)
                + '</EnemyFilter></EnemyNearbyHeuristic>')
        state = setup._state(f'CNVMinValue{i}', '', unit, gate='const')
        states.append(state.replace('<ConstantHeuristic/>', gate)
                      .replace('ClosestStructureHeuristic', 'CNVMinValueTarget'))
    start, end = xml.index('  <AIStrategicStateDefinition '), xml.index('  <AIPersonalityDefinition ')
    target = ('  <AITargetingHeuristic id="CNVMinValueTarget" HeuristicType="EnemyStructure" '
              'SortType="Distance" VitalKindOf="FS_POWER" RequireUniqueTarget="false"/>\n')
    xml = xml[:start] + target + '\n'.join(states) + '\n' + xml[end:]
    xml = xml.replace('    <StrategicState id="CNVStateInf" State="CNVStateInf"/>\n'
                      '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>',
                      '\n'.join(f'    <StrategicState id="CNVMinValue{i}" State="CNVMinValue{i}"/>'
                                for i in range(4)))
    m.assets[0] = filename, xml, asset
    for i, unit in enumerate(units[2:]):
        for k in range(4):
            m.put(unit, 'east base', -100 + 70*i, -150 + 70*k, side='s1',
                  name=f'UNIT - MinValue Team {i} {k}', role=f'min value team {i} {k}')
    for i, unit in enumerate(('AlliedMiner', 'SovietMiner')):
        m.put(unit, 'east base', 350, 80*i, name=f'UNIT - MinValue Miner {i}', role=f'value miner {i}')
    if high:
        m.put('SovietMiner', 'east base', 350, 160,
              name='UNIT - MinValue Miner 2', role='value miner 2')
    m.cnv_units = units
    m.spawns.update((*units, 'AlliedMiner', 'SovietMiner'))
    m.facts['min value cases'] = cases
    m.facts['min value home'] = (0, 4, 0, 4) if high else (0, 4, 4, 0)
    m.facts['min value miners'] = 3 if high else 2
    return m


MISSION = {'aiminvalue': mission, 'aiminvaluehi': lambda: mission(True)}
