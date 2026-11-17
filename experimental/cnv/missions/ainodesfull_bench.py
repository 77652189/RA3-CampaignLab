"""B208: AllNearbyNodesFullHeuristic (no fields) -- when are the AI's nearby ore nodes 'full'?

The aistate base (the Allied AI's yard on the east bank, 4 Peacekeepers + 4 Guardians, no money) with two states of
its own: CNVNodesFull (AllNearbyNodesFullHeuristic, the Peacekeepers) and CNVNodesCtl (ConstantHeuristic, the
Guardians, a control that the AI is awake and its teams go). The east field's two ore nodes stand ~450 from the yard,
inside its build radius. Three builds differ only in the AI refineries placed on that field:
  ainf0  none                      -> both nodes open
  ainf1  one, on the field's pad   -> the front node served, the side one open
  ainf2  two, one facing each node -> both served
  ainf3  ainf2 + two more AI Ore Collectors beside each refinery (B209: is 'full' counted in miners?)
  ainf4  ainf2 + one AI Ore Collector beside each refinery (B210: how many miners make a node full)
  ainf5  ainf1 + two AI Ore Collectors beside it (B210: do two miners at one refinery fill the side node too)
A placed refinery brings its own collector. Bench (B209 / B210): the Peacekeepers leave only on ainf3 -- a node is
full at 3 own collectors (simai NODE_MINERS, INFERRED: the engine's per-node taken / capacity wrapper is unread); the
Guardians leave on every build.
"""
import math

from missions import aistate_bench as setup

PAD2 = (150.0 * math.sqrt(0.5), 150.0 * math.sqrt(0.5))   # the side node's pad: PAIR_GAP beside the field's pad


def mission(name, refineries, miners=0):
    m = setup.mission(name, near=True)
    filename, xml, asset = m.assets[0]
    states = [setup._state('CNVNodesFull', '', setup.INF, gate='const').replace(
                  '<ConstantHeuristic/>', '<AllNearbyNodesFullHeuristic/>'),
              setup._state('CNVNodesCtl', '', setup.TANK, gate='const')]
    states = [s.replace('ClosestStructureHeuristic', 'CNVNodesTarget') for s in states]
    start = xml.index('  <AIStrategicStateDefinition ')
    end = xml.index('  <AIPersonalityDefinition ')
    target = ('  <AITargetingHeuristic id="CNVNodesTarget" HeuristicType="EnemyStructure" '
              'SortType="Distance" VitalKindOf="FS_POWER" RequireUniqueTarget="false"/>\n')
    xml = xml[:start] + target + '\n'.join(states) + '\n' + xml[end:]
    xml = xml.replace('    <StrategicState id="CNVStateInf" State="CNVStateInf"/>\n'
                      '    <StrategicState id="CNVStateTank" State="CNVStateTank"/>',
                      '    <StrategicState id="CNVNodesFull" State="CNVNodesFull"/>\n'
                      '    <StrategicState id="CNVNodesCtl" State="CNVNodesCtl"/>')
    m.assets[0] = filename, xml, asset
    if refineries >= 1:
        m.put('AlliedRefinery', 'east refinery', side='s1', name='UNIT - CNV AI Refinery 1', role='ai refinery 1')
    if refineries >= 2:
        m.put('AlliedRefinery', 'east refinery', *PAD2, side='s1', name='UNIT - CNV AI Refinery 2',
              role='ai refinery 2')
    for r, pad in enumerate(((0.0, 0.0), PAD2)[:refineries]):
        for k in range(miners):                  # B209 H1: extra AI miners beside each refinery (taken / capacity?)
            m.put('AlliedMiner', 'east refinery', pad[0] - 160.0, pad[1] - 60.0 + 120.0 * k, side='s1',
                  name=f'UNIT - CNV AI Miner {r} {k}', role=f'ai miner {r} {k}')
    m.facts['ai refineries'] = refineries
    m.facts['ai miners'] = miners
    return m


MISSION = {'ainf0': lambda: mission('CampNodesFull0', 0),
           'ainf1': lambda: mission('CampNodesFull1', 1),
           'ainf2': lambda: mission('CampNodesFull2', 2),
           'ainf3': lambda: mission('CampNodesFull3', 2, miners=2),
           'ainf4': lambda: mission('CampNodesFull4', 2, miners=1),
           'ainf5': lambda: mission('CampNodesFull5', 1, miners=2)}
