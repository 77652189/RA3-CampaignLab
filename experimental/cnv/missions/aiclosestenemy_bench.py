"""FriendlyStructure ClosestToEnemy: four retail land heuristics, independent teams.

Prediction before bench: turret / turret / plant / plant, four members
per lane by s55. Fixed enemy structures are closest to the turret, then the plant;
the yard and logging plant are further away. Native forbidden filters retained.
Measured s16-80: 4/4/0/0, model 4/4/4/4; last two lanes remain gaps.
Water host is not covered here. Evidence: work/re/c_closest_report.md.
"""
from missions import aistate_bench as setup
from missions.aiteams_bench import host_unit, HOST

HEURISTICS = ('FriendlyLandStructureHeuristic', 'FriendlyNonRefineryLandStructureHeuristic',
              'FriendlyLandNonDefenseStructureHeuristic', 'AITarget_A05_Defense')
UNITS = (setup.INF, setup.TANK, 'SovietAntiInfantryInfantry', 'SovietAntiVehicleInfantry')


def mission():
    m = setup.mission('CampClosest', gate='const')
    filename, xml, asset = m.assets[0]
    states = []
    for i, (heuristic, unit) in enumerate(zip(HEURISTICS, UNITS)):
        state = setup._state(f'CNVClosest{i}', '', unit, gate='const')
        state = state.replace('ClosestStructureHeuristic', heuristic)
        state = state.replace('Tactic="SimpleAttack"', 'Tactic="StaticDefense" Distance="100"')
        states.append(state)
    start, end = xml.index('  <AIStrategicStateDefinition '), xml.index('  <AIPersonalityDefinition ')
    xml = xml[:start] + '\n'.join(states) + '\n' + xml[end:]
    xml = xml.replace('    <StrategicState id="CNVStateInf" State="CNVStateInf"/>\n'
                      '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>',
                      '\n'.join(f'    <StrategicState id="CNVClosest{i}" State="CNVClosest{i}"/>' for i in range(4)))
    m.assets[0] = filename, xml, asset
    for i, unit in enumerate(UNITS[2:]):
        for k in range(4):
            m.put(unit, 'east base', 50 + 100*i, -150 + 70*k, side='s1',
                  name=f'UNIT - Closest Extra {i} {k}', role=f'closest extra {i} {k}')
    m.put('AlliedPowerPlant', 'carrier home', 300, 600, side='s1', name='UNIT - Closest Refinery', role='closest plant')
    m.put('AlliedBaseDefense', 'carrier home', 0, 0, side='s1', name='UNIT - Closest Turret', role='closest turret')
    m.put('AlliedPowerPlant', 'carrier home', 800, -400, name='UNIT - Closest Enemy', role='closest enemy')
    yard = m.find(m.role('player yard').name)
    yard.x, yard.y = m.site('carrier home', 800, -700)
    m.ext, m.ext_logs = True, ('target',)  # D174: ra3ext tgt: lines (costly, on demand)
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
    m.cnv_units = UNITS
    m.spawns.update(UNITS)
    for i, role in enumerate(('closest turret', 'closest turret', 'closest plant', 'closest plant')):
        m.cast[f'closest goal {i}'] = m.role(role)
    # Fixed unarmed enemy anchors; refinery exclusion is not exercised here.
    return m


MISSION = {'aiclosest': mission}
