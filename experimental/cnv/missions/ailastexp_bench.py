"""C: retail TimeSinceLastExpansionHeuristic.Time values before any expansion.

The 27-mission AI dependency cache uses 60s and 240s (the compiled campaign
states encode 240 as a float). Three independent teams share one permanent
target: those two timers and an always-on recruitment control. Prediction:
home counts at s40 = 4/4/0, s100 = 0/4/0, s275 = 0/0/0.
The initial timestamp is INFERRED zero; expansion/reset is deliberately a gap.
"""
from missions import aistate_bench as setup


def mission():
    m = setup.mission('CampAILastExp', near=True)
    units = (setup.INF, setup.TANK, 'SovietAntiInfantryInfantry')
    gates = (60, 240, None)
    filename, xml, asset = m.assets[0]
    states = []
    for i, (unit, seconds) in enumerate(zip(units, gates)):
        state = setup._state(f'CNVLastExp{i}', '', unit, gate='const')
        if seconds is not None:
            state = state.replace('<ConstantHeuristic/>',
                f'<TimeSinceLastExpansionHeuristic Time="{seconds}s"/>')
        state = state.replace('ClosestStructureHeuristic', 'CNVLastExpTarget')
        states.append(state)
    start = xml.index('  <AIStrategicStateDefinition ')
    end = xml.index('  <AIPersonalityDefinition ')
    target = ('  <AITargetingHeuristic id="CNVLastExpTarget" HeuristicType="EnemyStructure" '
              'SortType="Distance" VitalKindOf="FS_POWER" RequireUniqueTarget="false"/>\n')
    xml = xml[:start] + target + '\n'.join(states) + '\n' + xml[end:]
    xml = xml.replace('    <StrategicState id="CNVStateInf" State="CNVStateInf"/>\n'
                      '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>',
                      '\n'.join(f'    <StrategicState id="CNVLastExp{i}" State="CNVLastExp{i}"/>'
                                for i in range(3)))
    m.assets[0] = filename, xml, asset
    for k in range(4):
        m.put(units[2], 'east base', -100, -150 + 70*k, side='s1',
              name=f'UNIT - LastExp Control {k}', role=f'last expansion control {k}')
    m.cnv_units = units
    m.facts.update({'last expansion short': 60, 'last expansion long': 240})
    m.spawns.update(units)
    return m


MISSION = {'ailastexp': mission}
