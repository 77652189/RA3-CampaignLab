"""A8「海上发布会」粗模 (CampA8): the Liberty carrier is the player's, on CampNew38's island.

Story (docs/story/outline.md A8): Hale holds his launch on the sea, the time machine warming up; three power platforms
to destroy. Rough version: the platforms are three named power plants on the east side, each guarded by two Hammers
and a Bullfrog (anti-air: the carrier's hard counter, units.md 5.6 rule 3). The player has the carrier (drones, deck
jump, deck factory building Guardians) and four Guardians under it; the deck jump carries them onto a platform.
All three platforms down: objective done, "Mission Won". The carrier down: "Mission Lost" (5.6 rule 2: one copy, lose
it and you lose -- the flag name by analogy with "Mission Won", checked on the bench with CNV_TEST=lose).

  python -I -X utf8 experimental/campaign/make_campa8.py
  CNV_TEST=1: map revealed, a script jumps the player's carrier next to platform 1 at 5 s (does a player-owned
              carrier carry the Guardians and fight there?)
  CNV_TEST=lose: the carrier starts at 1 % health next to platform 1's Bullfrog
  CNV_NO_CARRIER=1: the control -- no carrier, eight Guardians and four IFVs instead (units.md 5.6 A/B check)
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TEST = os.environ.get('CNV_TEST', '')
NO_CARRIER = os.environ.get('CNV_NO_CARRIER') == '1'
for k, v in (('CNV_FACTORY', 'auto'), ('CNV_TURRETS', '0'), ('CNV_CHRONO_MODE', 'jump'), ('CNV_PLACE_TURRET', '0'),
             ('CNV_CHRONO_RELOAD', '45s')):
    os.environ.setdefault(k, v)                 # read by make_campnew38 at import
import make_campnew38 as c38                    # noqa: E402

c23, c18 = c38.c23, c38.c23.c18
c7, c6, c4, c2 = c38.c7, c38.c6, c38.c4, c38.c2
newmap = c38.newmap
NAME = 'CampA8'
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

CARRIER = 'UNIT - CNV A8 Liberty'
PLATFORMS = [(3400.0, 2200.0), (3500.0, 2900.0), (3200.0, 3500.0)]
P_NAMES = [f'UNIT - CNV A8 Platform {k + 1}' for k in range(3)]
CARRIER_AT = (1300.0, 2300.0)
WP_P1 = 'CNV A8 Near Platform 1'
NEAR_P1 = (3150.0, 2150.0)
OBJ = c18.OBJ
ARMY = [('AlliedAntiVehicleVehicleTech1', (CARRIER_AT[0] + dx, CARRIER_AT[1] + dy), True)
        for dx, dy in ((-60, 0), (60, 0), (0, -60), (0, 60))]
if NO_CARRIER:
    ARMY = ([('AlliedAntiVehicleVehicleTech1', (1180.0 + dx, 2330.0 + dy), True) for dx in (-90, -30, 30, 90)
             for dy in (0, 60)]
            + [('AlliedAntiAirVehicleTech1', (1180.0 + dx, 2250.0), True) for dx in (-90, -30, 30, 90)])
GUARDS = []
for x, y in PLATFORMS:
    GUARDS += [('SovietAntiVehicleVehicleTech1', (x - 120, y - 40), False),
               ('SovietAntiVehicleVehicleTech1', (x - 120, y + 40), False),
               ('SovietAntiAirShip_Ground', (x - 60, y), False)]
c38.SCENE[:] = ARMY + GUARDS
c4.c3.STRINGS.update({
    c18.CAPTION: 'A8 海上发布会：黑尔的时间机器正在预热。打掉三座供电平台。自由号只有一艘，丢了就输。',
    'MISSIONOBJ:CNV02_1': 'A8 目标：摧毁三座供电平台',
    'MISSIONOBJ:CNV02_1_DESC': '用超时空甲板把部队跃迁到平台边上。平台旁有防空车，别让自由号被打掉。',
    'SCRIPT:CNVA8_WIN': 'A8：三座供电平台全部被毁。',
    'SCRIPT:CNVA8_LOST': 'A8：自由号被击落了……',
})

_generate = c6.edit                              # make_campnew38.generate


def tmpl(k):
    return k.head[22:22 + struct.unpack_from('<H', k.head, 20)[0]].decode('latin-1')


def generate(m):
    _generate(m)
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    ours = next(k for k in objs.kids if tmpl(k) == 'AlliedAntiVehicleVehicleTech1')
    theirs = next(k for k in objs.kids if tmpl(k) == 'SovietAntiAirShip_Ground')
    opr, ofl = newmap.typed_props_of(m, ours)
    epr, efl = newmap.typed_props_of(m, theirs)
    if not NO_CARRIER:
        at, hp = ((PLATFORMS[0][0] - 60, PLATFORMS[0][1] - 120), {'objectInitialHealth': 1}) if TEST == 'lose' \
            else (CARRIER_AT, {})
        objs.kids.append(newmap.object_node(m, opr, ofl, c38.UNIT, *at, angle=0.0, objectName=CARRIER,
                                            uniqueID='CNV A8 Liberty', **hp))
    for (x, y), name in zip(PLATFORMS, P_NAMES):
        objs.kids.append(newmap.object_node(m, epr, efl, 'AlliedPowerPlant', x, y, angle=math.pi, objectName=name,
                                            uniqueID=name))
    wp_like = next(k for k in objs.kids if tmpl(k) == '*Waypoints/Waypoint')
    wpr, wfl = newmap.typed_props_of(m, wp_like)
    wid = 1 + max(newmap.typed_props_of(m, k)[0].get('waypointID', (1, 0))[1] for k in objs.kids
                  if tmpl(k) == '*Waypoints/Waypoint')
    objs.kids.append(newmap.object_node(m, wpr, wfl, '*Waypoints/Waypoint', *NEAR_P1, waypointName=WP_P1,
                                        waypointID=wid, uniqueID=f'Waypoint {wid}'))
    act = lambda *a: m.new_content('ScriptAction', *a)                      # noqa: E731
    scripts = [
        m.new_script('CNV A8 - Win', [m.new_content('Condition', 'NAMED_DESTROYED', n) for n in P_NAMES],
                     [act('SET_MISSION_OBJECTIVE_STATUS', OBJ, 2), act('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA8_WIN', 10.0),
                      act('SET_FLAG', 'Mission Won', 1)]),
    ]
    if not NO_CARRIER:
        scripts.append(m.new_script('CNV A8 - Lost', [m.new_content('Condition', 'NAMED_DESTROYED', CARRIER)],
                                    [act('SET_MISSION_OBJECTIVE_STATUS', OBJ, 3),
                                     act('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA8_LOST', 10.0),
                                     act('SET_FLAG', 'Mission Lost', 1)]))
    if TEST:
        scripts.append(m.new_script('CNV A8 - Test Reveal', [m.new_content('Condition', 'CONDITION_TRUE')],
                                    [act('MAP_REVEAL_ALL_PERM', 'Player_1'),
                                     act('SET_MILLISECOND_TIMER', 'CNV A8 TestJump', 5.0)]))
    if TEST == '1' and not NO_CARRIER:
        scripts.append(m.new_script('CNV A8 - Test Jump', [m.new_content('Condition', 'TIMER_EXPIRED', 'CNV A8 TestJump')],
                                    [act('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', CARRIER, 'SpecialPower_CNV_ChronoDeck',
                                         WP_P1)]))
    psl = next(n for _, n in m.walk() if n.name == 'PlayerScriptsList')
    psl.kids[2].kids += scripts
    print('A8:', 'no carrier' if NO_CARRIER else f'carrier {CARRIER}', '| platforms', PLATFORMS, '|', len(scripts),
          'scripts', f'(test {TEST})' if TEST else '')


c6.edit = generate

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
