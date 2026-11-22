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


# B 11-22: the reset after a real expansion. D's aiexpb200 (its miner unpacks an outpost s106) and aiexpb50 (no
# outpost: the control) plus one state gated by Time=150s whose team is two Athena cannons (SIEGE_WEAPON: the
# expansion team excludes them) sent at the player's yard across the river (NamedObject: out of their reach from
# home, so the team's start shows as the cannons leaving home). No reset: both leave ~s150; a reset at the
# outpost: aiexpb200's ~s256.
GATE, CANNON, YARD = 150, 'AlliedAntiStructureVehicle', 'UNIT - CNV AI Player Yard'


def after(distance):
    from missions import aisimpleexp_bench
    m = aisimpleexp_bench.built(distance, build=True)
    m.name = f'CampAILastX{distance}'
    filename, xml, asset = m.assets[0]
    state = setup._state('CNVLastExpGate', '', CANNON, gate='const').replace(
        '<ConstantHeuristic/>', f'<TimeSinceLastExpansionHeuristic Time="{GATE}s"/>').replace(
        'ClosestStructureHeuristic', 'CNVLastExpYard')
    target = (f'  <AITargetingHeuristic id="CNVLastExpYard" HeuristicType="NamedObject" Name="{YARD}"'
              ' MinDistanceFromEnemy="0" SearchRange="5000" Location="Land"/>\n')
    end = xml.index('  <AIPersonalityDefinition ')
    xml = xml[:end] + target + state + '\n' + xml[end:]
    xml = xml.replace('    <StrategicState id="CNVStateTP" State="CNVStateTP"/>',
                      '    <StrategicState id="CNVStateTP" State="CNVStateTP"/>\n'
                      '    <StrategicState id="CNVLastExpGate" State="CNVLastExpGate"/>', 1)
    assert xml.count('CNVLastExpGate') == 3 and m.role('player yard').name == YARD
    m.assets[0] = filename, xml, asset
    for k in range(2):
        m.put(CANNON, 'east base', 150.0, -150.0 + 80*k, side='s1', name=f'UNIT - LastExp Cannon {k}',
              role=f'last expansion cannon {k}')
    m.spawns |= {CANNON}
    m.facts['last expansion gate'], m.facts['cannon'] = GATE, CANNON
    return m


MISSION = {'ailastexp': mission, 'ailastx200': lambda: after(200), 'ailastx50': lambda: after(50)}
