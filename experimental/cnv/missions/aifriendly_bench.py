"""E85 FriendlyUnit versus EnemyUnit, using retail's StaticDefense consumer.

Only HeuristicType differs between the pair. SAME_PLAYER is explicit in both;
the SDK documents Relationship as hooked up only for FriendlyUnit. Both MCVs
must survive. Prediction at s40: four Guardians at the corresponding MCV.
Evidence and scope: work/re/e_friendly_e85.md.
"""
from missions.aitargetpick_bench import mission as target_mission


def mission(friendly):
    name = 'CampAIFriend' if friendly else 'CampAIEnemy'
    m = target_mission(name, [('CNVHVehicle', None)], (0, 0, 0, 0))
    filename, xml, asset = m.assets[0]
    xml = xml.replace('VitalKindOf="VEHICLE"', 'VitalKindOf="MCV" Relationship="SAME_PLAYER"')
    xml = xml.replace('Tactic="SimpleAttack"', 'Tactic="StaticDefense" Distance="100"')
    if friendly:
        xml = xml.replace('HeuristicType="EnemyUnit"', 'HeuristicType="FriendlyUnit"')
    m.assets[0] = (filename, xml, asset)
    m.put('AlliedMCV', 'carrier home', side='s1', name='UNIT - Friendly MCV', role='friendly')
    m.put('AlliedMCV', 'east gate', name='UNIT - Enemy MCV', role='enemy')
    m.facts.update({'expect friendly': 4 if friendly else 0, 'expect enemy': 0 if friendly else 4})
    return m


MISSION = {'aifriend': lambda: mission(True), 'aienemy': lambda: mission(False)}
