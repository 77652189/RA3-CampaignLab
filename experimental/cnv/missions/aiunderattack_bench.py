"""AITargetingHeuristic UnderAttack: when an object counts as "under attack" and when it stops (engine line D, round 161).

The aiclosest bench (four FriendlyStructure lanes, ra3ext loaded) with lane 0's heuristic swapped for one of the
probe's own -- FriendlyStructure, UnderAttack="true", no KindOf filters -- so the friendly filter's UnderAttack gate
runs on the AI's buildings. Two player Hammer tanks stand off the AI's power plant; the check orders A onto the plant and
deletes it mid-fight, then orders B on and stops it (TIMES). ra3ext's `ua:` lines (teamlog.under_attack) give the plant's
set / clear frames and the gate's own answers; predicted: set at the first hit, clear 75 frames (5 s x 15, speed 1)
after the last hit, the gate true exactly in between, whether or not the source still exists.
"""
from missions.aiclosestenemy_bench import mission as closest

TANK = 'SovietAntiVehicleVehicleTech1'
# Round 164: A fights the plant early (before the AI's infantry arrive) and is deleted mid-fight (source deleted, window
# open); B is ordered on after A's window has run out -- its first hit sweeps A's episode closed -- then stopped and kept
# alive (ceasefire with the source alive).
TIMES = {'attack at': 2.0, 'stop at': 10.0, 'b attack at': 20.0, 'b stop at': 32.0}


def mission():
    m = closest()
    m.name = 'CampUnderAtk'
    asset, xml, ref = m.assets[0]
    heuristic = '<AITargetingHeuristic id="CNVUnderAttack" HeuristicType="FriendlyStructure" UnderAttack="true"/>'
    xml = xml.replace('<AIStrategicStateDefinition ', heuristic + '\n  <AIStrategicStateDefinition ', 1)
    xml = xml.replace('"FriendlyLandStructureHeuristic"', '"CNVUnderAttack"', 1)
    m.assets[0] = asset, xml, ref
    m.put(TANK, 'carrier home', 300, 430, name='UNIT - UA Tank', role='ua tank')
    m.put(TANK, 'carrier home', 650, 350, name='UNIT - UA Tank B', role='ua tank b')
    m.spawns.add(TANK)
    m.facts.update(TIMES)
    return m


MISSION = {'aiunderatk': mission}
