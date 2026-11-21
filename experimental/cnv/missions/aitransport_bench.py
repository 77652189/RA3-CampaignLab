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
from missions.aiteams_bench import HOST, host_unit

TWINBLADE = 'SovietAntiGroundAircraft'          # AIRCRAFT TRANSPORT, TransportContain ContainMax 5, takes INFANTRY
TACTIC = '<Tactic id="Attack" Tactic="SimpleAttack" EndBehavior="RAMPAGE" EndIfStateTurnsOff="true"'


def mission(use, inf=4, name=None, site='station', boat=RIPTIDE):
    locos = 'LAND AMPHIBIOUS AIR' if boat == TWINBLADE else 'LAND AMPHIBIOUS'
    m = team_mission(name or f'CampAITrans{int(use)}', tanks=0, inf=inf, inf_home=inf, locos=locos)
    m.map = SimpleNamespace(**vars(ai_map(m.map, library=False)))
    assert all(o.template == 'HB_Bridge_02' for o in m.map.OBJECTS[:6])
    m.map.OBJECTS = m.map.OBJECTS[6:]                       # no bridges: the east bank is cut off
    target = next(o for o in m.objects if o.name == 'UNIT - CNV AI Player Target')
    if site:                                                # None: aiteamfilter's 'east gate' plant (B223)
        target.x, target.y = m.site(site)
    m.put(boat, 'east base', -350.0, -160.0, side='s1', angle=3.1416, name='UNIT - CNV AI Riptide',
          role='ai riptide')
    m.spawns |= {boat}
    # B222: the ra3ext host (team: samples, tgt: picks) tells "no team" from "a team that does not move"
    m.ext, m.ext_logs = True, ('target',)
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250, 400, side='s1', role='teams host')
    m.facts |= {'use transports': int(use), 'target on island': int(site == 'station'),
                'target x': target.x, 'target y': target.y, 'air transport': int(boat == TWINBLADE)}
    filename, xml, asset = m.assets[0]
    assert TACTIC in xml
    xml = xml.replace(TACTIC, f'{TACTIC} UseTransports="{str(use).lower()}"')
    m.assets[0] = filename, xml, asset
    return m


def player_shot():
    """E 11-21: aitranst0's Twinblade hits the plant at half the data's rate (every other rocket clip misses). Here
    the Twinblade is the player's own, put on the line it hovered on (400 out, east-north-east of the plant), and a
    script force-attacks the plant: no AI orders. Every clip lands -> the AI's re-sent orders cost the clips."""
    m = mission(False, inf=0, name='CampAITransTP')         # the Riptide alone: nobody is recruited (B222 aitransr)
    m.put(TWINBLADE, 'station', 344.0, 204.0, angle=-2.6, name='UNIT - CNV Twinblade', role='player twinblade')
    m.facts |= {'air transport': 1, 'player shot': 1}
    return m


# B222: aitrans0 / 1 with the ra3ext host: the target pick finds the island plant, the team is made (f17) and
# stays empty, remade every ~90 frames -- nobody is recruited. aitransr: the Riptide alone (no infantry), the
# flag at its default: is the Riptide itself turned away (its own way to the island, or as a transport) or do the
# unpairable infantry block the whole recruit?
MISSION = {'aitrans0': lambda: mission(False), 'aitrans1': lambda: mission(True),
           'aitransr': lambda: mission(True, inf=0, name='CampAITransR'),
           # the Riptide alone is not taken either: the island itself (its way there) is what turns it away. The
           # same three with the plant on the west bank's bridge landing ('front'): water-only for both
           'aitransw0': lambda: mission(False, name='CampAITransW0', site='front'),
           'aitransw1': lambda: mission(True, name='CampAITransW1', site='front'),
           'aitransrw': lambda: mission(True, inf=0, name='CampAITransRW', site='front'),
           # B223: the Riptide alone, still no bridges, the plant back on the east bank's land ('east gate', where
           # aitfamph took Riptides): taken -> "no way there" turns it away on the island / west bank; not taken ->
           # this bench itself (no bridges, no library, LAND AMPHIBIOUS) turns the Riptide away
           'aitransre': lambda: mission(True, inf=0, name='CampAITransRE', site=None),
           # B 11-21: the recruit gate (work/re b1121_transports.md) takes an aircraft always and, when a unit cannot
           # reach the target, tries it again with a member that can carry it (their surfaces or'd): a Twinblade
           # (AIR) in the team lets the Peacekeepers in as its passengers, so the pair forms and the flag can tell
           'aitranst0': lambda: mission(False, name='CampAITransT0', boat=TWINBLADE),
           'aitranst1': lambda: mission(True, name='CampAITransT1', boat=TWINBLADE),
           'aitranstp': player_shot}
