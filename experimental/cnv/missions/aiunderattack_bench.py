"""AITargetingHeuristic UnderAttack: when an object counts as "under attack" and when it stops (engine line D, round 161).

The aiclosest bench (four FriendlyStructure lanes, ra3ext loaded) with lane 0's heuristic swapped for one of the
probe's own -- FriendlyStructure, UnderAttack="true", no KindOf filters -- so the friendly filter's UnderAttack gate
runs on the AI's buildings. One player Hammer tank stands off the AI's power plant; the check orders it onto the plant
at ATTACK_AT and deletes it at STOP_AT (the ceasefire). ra3ext's `ua:` lines (teamlog.under_attack) give the plant's
set / clear frames and the gate's own answers; predicted: set at the first hit, clear 75 frames (5 s x 15, speed 1)
after the last hit, the gate true exactly in between, whether or not the source still exists.
"""
from missions.aiclosestenemy_bench import mission as closest

TANK = 'SovietAntiVehicleVehicleTech1'
ATTACK_AT, STOP_AT = 15.0, 30.0


def mission():
    m = closest()
    m.name = 'CampUnderAtk'
    asset, xml, ref = m.assets[0]
    heuristic = '<AITargetingHeuristic id="CNVUnderAttack" HeuristicType="FriendlyStructure" UnderAttack="true"/>'
    xml = xml.replace('<AIStrategicStateDefinition ', heuristic + '\n  <AIStrategicStateDefinition ', 1)
    xml = xml.replace('"FriendlyLandStructureHeuristic"', '"CNVUnderAttack"', 1)
    m.assets[0] = asset, xml, ref
    m.put(TANK, 'carrier home', 300, 1000, name='UNIT - UA Tank', role='ua tank')
    m.spawns.add(TANK)
    m.facts.update({'attack at': ATTACK_AT, 'stop at': STOP_AT})
    return m


MISSION = {'aiunderatk': mission}
