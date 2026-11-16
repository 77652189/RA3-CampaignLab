"""B-line Tactic UseTransports pair: a SimpleAttack team of four Peacekeepers and a Riptide, the target over water.

aiteamfilter_bench's set-up (Niagara, s1 Allied with a yard, one always-on state, SimpleAttack at the closest enemy
structure, KindOf CAN_ATTACK, MaxUnits 8, LAND AMPHIBIOUS) with Niagara's six bridge pieces removed (aibridge_bench's
trick), so the east bank is cut off from Goat Island and the west bank. The player's target plant stands on Goat
Island ('station'). s1 has four Peacekeepers (cannot cross) and one Riptide ACV (AlliedAntiInfantryVehicle:
TRANSPORT AMPHIBIOUS, TransportContain ContainMax 5). Only the tactic's UseTransports differs (retail's 27 levels
write it false 14 times; its default is true).

Read rule (work/re b221): the flag is read once, in SimpleAttack's per-frame update; true -> while the team still has
passenger / transport pairs not boarded, the update returns without a move order (they board first); false -> the
team attack-moves at once. Pairing itself (at recruiting) ignores the flag. Prediction: true -> the Peacekeepers
ride the Riptide over; false -> the Riptide crosses empty, the Peacekeepers stay on the east bank.
"""
from types import SimpleNamespace

from missions.aiteamfilter_bench import mission as team_mission, RIPTIDE
from missions.aiskirm_bench import ai_map

TACTIC = '<Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE" EndIfStateTurnsOff="true"'


def mission(use):
    m = team_mission(f'CampAITrans{int(use)}', tanks=0, inf=4)
    m.map = SimpleNamespace(**vars(ai_map(m.map, library=False)))
    assert all(o.template == 'HB_Bridge_02' for o in m.map.OBJECTS[:6])
    m.map.OBJECTS = m.map.OBJECTS[6:]                       # no bridges: the east bank is cut off
    target = next(o for o in m.objects if o.name == 'UNIT - CNV AI Player Target')
    target.x, target.y = m.site('station')
    m.put(RIPTIDE, 'east base', -350.0, -160.0, side='s1', angle=3.1416, name='UNIT - CNV AI Riptide',
          role='ai riptide')
    m.spawns |= {RIPTIDE}
    m.facts |= {'use transports': int(use)}
    filename, xml, asset = m.assets[0]
    assert TACTIC in xml
    xml = xml.replace(TACTIC, f'{TACTIC} UseTransports="{str(use).lower()}"')
    m.assets[0] = filename, xml, asset
    return m


MISSION = {'aitrans0': lambda: mission(False), 'aitrans1': lambda: mission(True)}
