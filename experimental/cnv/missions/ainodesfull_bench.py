"""B208: AllNearbyNodesFullHeuristic (no fields) -- when are the AI's nearby ore nodes 'full'?

The aistate base (the Allied AI's yard on the east bank, 4 Peacekeepers + 4 Guardians, no money) with two states of
its own: CNVNodesFull (AllNearbyNodesFullHeuristic, the Peacekeepers) and CNVNodesCtl (ConstantHeuristic, the
Guardians, a control that the AI is awake and its teams go). The east field's two ore nodes stand ~450 from the yard,
inside its build radius. Three builds differ only in the AI refineries placed on that field:
  ainf0  none                      -> both nodes open
  ainf1  one, on the field's pad   -> the front node served, the side one open
  ainf2  two, one facing each node -> both served
Prediction (simai Brain.open_nodes: a node is served by an own refinery within 300 whose nearest node it is,
INFERRED; the engine's per-node taken / capacity wrapper is unread): the Peacekeepers stay home on ainf0 and ainf1
and leave on ainf2; the Guardians leave on all three.
"""
import math

from missions import aistate_bench as setup

PAD2 = (150.0 * math.sqrt(0.5), 150.0 * math.sqrt(0.5))   # the side node's pad: PAIR_GAP beside the field's pad


def mission(name, refineries):
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
    m.facts['ai refineries'] = refineries
    return m


MISSION = {'ainf0': lambda: mission('CampNodesFull0', 0),
           'ainf1': lambda: mission('CampNodesFull1', 1),
           'ainf2': lambda: mission('CampNodesFull2', 2)}
