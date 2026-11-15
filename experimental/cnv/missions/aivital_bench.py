"""Four retail VitalObjectStatus hosts with script-set native status bits.

This isolates the bit filter, not aircraft flight or the attachment lifecycle.
Three airborne samples avoid unique-target contention between the three hosts.
Before AI wake: set at s0, clear at s4, set again at s6 only in the matching build.
Prediction: native status mask 15/0/15 (matching), 15/0/0 (nonmatching);
at s55 each matching team has four at its goal, each nonmatching team four home.
Any unobserved candidate qualification remains a gap. See work/re/c_vital_report.md.
Measured s55-60: on 24/4/4/140, off 24/4/4/4. Ground AIRBORNE_TARGET
samples read zero throughout. Only the script-controlled ATTACHED slice matched;
lane zero's goal/home areas overlap, so its counts are not disjoint membership.
"""
from missions import aistate_bench as setup
from parts import Script

HEURISTICS = ('ClosestAirborneTargetHeuristic', 'ClosestAirborneTargetHeuristic_All',
              'SafestToAirAirborneTargetHeuristic', 'AttachedVehicleTargetHeuristic_NonUnique')
UNITS = ('AlliedAntiVehicleInfantry', 'AlliedAntiAirVehicleTech1',
         'SovietAntiVehicleInfantry', setup.TANK)
BITS = ('AIRBORNE_TARGET',) * 3 + ('ATTACHED',)


def mission(matching=True):
    m = setup.mission('CampVitalOn' if matching else 'CampVitalOff', gate='const')
    filename, xml, asset = m.assets[0]
    states = [setup._state(f'CNVVital{i}', '', unit, gate='const').replace(
        'ClosestStructureHeuristic', heuristic)
        for i, (unit, heuristic) in enumerate(zip(UNITS, HEURISTICS))]
    start, end = xml.index('  <AIStrategicStateDefinition '), xml.index('  <AIPersonalityDefinition ')
    xml = xml[:start] + '\n'.join(states) + '\n' + xml[end:]
    xml = xml.replace('    <StrategicState id="CNVStateInf" State="CNVStateInf"/>\n'
                      '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>',
                      '\n'.join(f'    <StrategicState id="CNVVital{i}" State="CNVVital{i}"/>' for i in range(4)))
    m.assets[0] = filename, xml, asset
    for k in range(4):
        m.find(m.role(f'peacekeeper {k+1}').name).template = UNITS[0]
    for i, unit in enumerate(UNITS[1:3], 1):
        for k in range(4):
            m.put(unit, 'east base', 50 + 100*i, -150 + 70*k, side='s1',
                  name=f'UNIT - Vital Member {i} {k}', role=f'vital member {i} {k}')
    for i in range(4):
        m.put(setup.TANK, 'east gate' if i < 3 else 'carrier home', 80*i if i < 3 else 0, 0,
              name=f'UNIT - Vital Sample {i}', role=f'vital sample {i}')
        m.cast[f'vital goal {i}'] = m.role(f'vital sample {i if i == 3 else 0}')
    names = [m.role(f'vital sample {i}').name for i in range(4)]
    m.scripts.append(Script('Vital initial set', [], [
        ('UNIT_CHANGE_OBJECT_STATUS', name, bit, 1) for name, bit in zip(names, BITS)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1) for name in names] + [
        ('SET_MILLISECOND_TIMER', 'Vital clear', 4.0),
        ('SET_MILLISECOND_TIMER', 'Vital final', 6.0)]))
    for timer, value in [('Vital clear', 0), ('Vital final', int(matching))]:
        m.scripts.append(Script(timer, [('TIMER_EXPIRED', timer)], [
            ('UNIT_CHANGE_OBJECT_STATUS', name, bit, value) for name, bit in zip(names, BITS)]))
    m.cnv_units = UNITS
    m.spawns.update(UNITS)
    m.facts.update({'vital matching': int(matching), 'vital bits': BITS})
    return m


MISSION = {'aivitalon': mission, 'aivitaloff': lambda: mission(False)}
