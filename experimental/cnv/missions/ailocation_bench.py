"""Location is a Land/Water filter, not a distance reference point.

Identical EnemyStructure/Distance heuristics select between two power plants:
the nearer one on the east bank, the farther one in the river. Twinblades can
reach and attack either. Only Location differs between the three builds.
Prediction: Land and Water Land -> land; Water -> water. See work/re/e_location_e81.md.
"""
from maps import niagara
from missions import aitargetpick_bench as tp
from parts import Mission, Script

HELI = 'SovietAntiGroundAircraft'


def mission(location, suffix):
    pid = 'CNVLocation'
    xml = tp.personality_xml(pid, [('CNVHBarracks', None)], 1)
    xml = xml.replace('VitalKindOf="FS_BARRACKS"', f'VitalKindOf="FS_POWER" Location="{location}"')
    xml = xml.replace('AllowedLocomotorTypes="LAND AMPHIBIOUS"', 'AllowedLocomotorTypes="AIR"')
    m = Mission(name='CampAILoc' + suffix, map=niagara,
                facts={'wake at': 10.0, 'expect land': int(location != 'Water'),
                       'expect water': int(location == 'Water')})
    m.sides['s1'] = {'playerFaction': 'PlayerTemplate:Allies', 'aiPersonality': f'AIPersonalityDefinition:{pid}'}
    m.assets.append((pid + '.xml', xml, f'AIPersonalityDefinition:{pid}'))
    m.cnv_units = (HELI,)
    m.spawns.add(HELI)
    m.put('AlliedConstructionYard', 'east base', side='s1', name='UNIT - Location Yard', role='ai yard')
    m.put('AlliedPowerPlant', 'east gate', name='UNIT - Location Land', role='land')
    # River centre, away from either bridge and Goat Island; no new map needed.
    m.put('AlliedPowerPlant', 'north bridge', 0, -400, name='UNIT - Location Water', role='water')
    for k in range(4):
        m.put(HELI, 'east base', -200, 160 + 70 * k, side='s1',
              name=f'UNIT - Location Heli {k}', role=f'heli {k}')
    m.waypoint('ai base', 'CNV Location Base', 'east base')
    s1 = m.player('s1')
    m.scripts += [
        Script('Location start', [], [('PLAYER_SET_MONEY', s1, 0),
                                     ('SET_MILLISECOND_TIMER', 'Location Wake', 10.0)]),
        Script('Location wake', [('TIMER_EXPIRED', 'Location Wake')], [
            ('UNIT_AI_TRANSFER_ALL', s1, 1), ('SKIRMISH_AI_MAKE_BASE', s1, 'CNV Location Base'),
            ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', s1, 20),
            ('SKIRMISH_AI_USE_REPAIRS', s1, 0), ('SKIRMISH_AI_USE_REBUILD_SYSTEM', s1, 0),
            ('PLAYER_SET_MONEY', s1, 0)])]
    return m


MISSION = {'ailocland': lambda: mission('Land', 'L'),
           'ailocwater': lambda: mission('Water', 'W'),
           'ailocboth': lambda: mission('Water Land', 'B')}
