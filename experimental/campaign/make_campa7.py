"""A7「鹰派」粗模 (CampA7): the Liberty carrier as the boss, on CampNew38's island.

Story (docs/story/outline.md A7, units.md 5.2 / 5.6): the hawk commander has taken the Liberty to "pre-emptively erase
the Soviets"; the player fights their own flagship. While the power station stands the carrier's chrono deck works:
a mission script makes it jump between its home (east) and a strike point at the edge of the player's base (west)
every GAP seconds, bringing what its deck factory has built along. The power station down: a caption, no more jumps.
The carrier down: objective done, SET_FLAG("Mission Won", 1) (CampNew30's ending).

The AI never presses the jump button itself, so the jumps are NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT on two alternating
millisecond timers (a timer stays expired, so each script also pushes its own timer far out).

Carrier = make_campnew38 (Kirov stand-in, drones, deck jump, auto deck factory of Guardians); turrets off (spawned
turrets do not fire yet). Enemy = the base map's Soviet player, so the "hawks" are red here.

  python -I -X utf8 experimental/campaign/make_campa7.py
  CNV_TEST=1: map revealed, first jump at 8 s, the power station killed by script at 30 s (so a jump, then the
              power-down caption, then no more jumps show within a minute)
  CNV_TEST=win: the carrier starts at the strike point at 1 % health beside the player's IFVs
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TEST = os.environ.get('CNV_TEST', '')
for k, v in (('CNV_FACTORY', 'auto'), ('CNV_TURRETS', '0'), ('CNV_CHRONO_MODE', 'jump'), ('CNV_PLACE_TURRET', '0'),
             ('CNV_CHRONO_RELOAD', '0s')):
    os.environ.setdefault(k, v)                 # read by make_campnew38 at import
import make_campnew38 as c38                    # noqa: E402

c23, c18 = c38.c23, c38.c23.c18
c7, c6, c4, c2 = c38.c7, c38.c6, c38.c4, c38.c2
newmap = c38.newmap
NAME = 'CampA7'
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

CARRIER, POWER = 'UNIT - CNV A7 Liberty', 'UNIT - CNV A7 Power'
WP_STRIKE, WP_HOME = 'CNV A7 Strike', 'CNV A7 Home'
# strike point on open ground ~250 from the player's army (first try (1550, 2600) was on the war factory, out of the
# IFVs' 300 reach: the win test's carrier at 1 % never got shot)
STRIKE, HOME = (1450.0, 2450.0), (3000.0, 2600.0)
POWER_AT = (3100.0, 3600.0)
FIRST, GAP = (8.0, 15.0) if TEST == '1' else (40.0, 45.0)
OBJ = c18.OBJ
# markers: the first player / enemy unit placed by make_campnew38, whose map properties (owner, team) the named
# objects copy
c38.SCENE[:] = ([('AlliedAntiVehicleVehicleTech1', (1180.0 + dx, 2330.0 + dy), True)
                 for dx in (-90, -30, 30, 90) for dy in (0, 60)]
                + [('AlliedAntiAirVehicleTech1', (1180.0 + dx, 2250.0), True) for dx in (-90, -30, 30, 90)]
                + [('AlliedAntiVehicleVehicleTech1', (POWER_AT[0] + dx, POWER_AT[1] - 150), False)
                   for dx in (-60, 0, 60)])
c4.c3.STRINGS.update({
    c18.CAPTION: 'A7 鹰派：司令开走了自由号。只要尼亚加拉电站还在，它的超时空甲板就能把它送到任何地方。',
    'MISSIONOBJ:CNV02_1': 'A7 目标：击落自由号',
    'MISSIONOBJ:CNV02_1_DESC': '自由号会跃迁到我方基地边上放无人机、卸下部队。先炸掉东北的电站，它就跳不了了。',
    'SCRIPT:CNVA7_JUMP': 'A7：自由号跃迁过来了！',
    'SCRIPT:CNVA7_POWER': 'A7：电站被毁，自由号的超时空甲板断电了！',
    'SCRIPT:CNVA7_WIN': 'A7：自由号被击落。',
})

_generate = c6.edit                              # make_campnew38.generate


def tmpl(k):
    return k.head[22:22 + struct.unpack_from('<H', k.head, 20)[0]].decode('latin-1')


def generate(m):
    _generate(m)
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    ours = next(k for k in objs.kids if tmpl(k) == 'AlliedAntiAirVehicleTech1')
    theirs = next(k for k in objs.kids if tmpl(k) == 'AlliedAntiVehicleVehicleTech1'
                  and struct.unpack_from('<f', k.head, 4)[0] > 3000)
    pr, fl = newmap.typed_props_of(m, theirs)
    at, hp = (STRIKE, {'objectInitialHealth': 1}) if TEST == 'win' else (HOME, {})
    objs.kids.append(newmap.object_node(m, pr, fl, c38.UNIT, *at, angle=math.pi, objectName=CARRIER,
                                        uniqueID='CNV A7 Liberty', **hp))
    objs.kids.append(newmap.object_node(m, pr, fl, 'AlliedPowerPlant', *POWER_AT, angle=math.pi, objectName=POWER,
                                        uniqueID='CNV A7 Power'))
    wp_like = next(k for k in objs.kids if tmpl(k) == '*Waypoints/Waypoint')
    wpr, wfl = newmap.typed_props_of(m, wp_like)
    ids = [newmap.typed_props_of(m, k)[0].get('waypointID', (1, 0))[1] for k in objs.kids
           if tmpl(k) == '*Waypoints/Waypoint']
    wid = max(ids) + 1
    for name, xy in ((WP_STRIKE, STRIKE), (WP_HOME, HOME)):
        objs.kids.append(newmap.object_node(m, wpr, wfl, '*Waypoints/Waypoint', *xy, waypointName=name,
                                            waypointID=wid, uniqueID=f'Waypoint {wid}'))
        wid += 1
    alive = m.new_content('Condition', 'NAMED_DESTROYED', POWER, inverted=True)
    act = lambda *a: m.new_content('ScriptAction', *a)                      # noqa: E731
    scripts = [
        m.new_script('CNV A7 - Init', [m.new_content('Condition', 'CONDITION_TRUE')],
                     [act('SET_MILLISECOND_TIMER', 'CNV A7 JumpA', FIRST),
                      act('SET_MILLISECOND_TIMER', 'CNV A7 JumpB', 99999.0)]),
        m.new_script('CNV A7 - Jump Strike', [m.new_content('Condition', 'TIMER_EXPIRED', 'CNV A7 JumpA'), alive],
                     [act('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', CARRIER, 'SpecialPower_CNV_ChronoDeck', WP_STRIKE),
                      act('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA7_JUMP', 5.0),
                      act('SET_MILLISECOND_TIMER', 'CNV A7 JumpA', 99999.0),
                      act('SET_MILLISECOND_TIMER', 'CNV A7 JumpB', GAP)], one_shot=False),
        m.new_script('CNV A7 - Jump Home',
                     [m.new_content('Condition', 'TIMER_EXPIRED', 'CNV A7 JumpB'),
                      m.new_content('Condition', 'NAMED_DESTROYED', POWER, inverted=True)],
                     [act('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', CARRIER, 'SpecialPower_CNV_ChronoDeck', WP_HOME),
                      act('SET_MILLISECOND_TIMER', 'CNV A7 JumpB', 99999.0),
                      act('SET_MILLISECOND_TIMER', 'CNV A7 JumpA', GAP)], one_shot=False),
        m.new_script('CNV A7 - Power Down', [m.new_content('Condition', 'NAMED_DESTROYED', POWER)],
                     [act('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA7_POWER', 8.0)]),
        m.new_script('CNV A7 - Win', [m.new_content('Condition', 'NAMED_DESTROYED', CARRIER)],
                     [act('SET_MISSION_OBJECTIVE_STATUS', OBJ, 2),
                      act('SHOW_MILITARY_CAPTION', 'SCRIPT:CNVA7_WIN', 10.0),
                      act('SET_FLAG', 'Mission Won', 1)]),
    ]
    if TEST:
        scripts.append(m.new_script('CNV A7 - Test Reveal', [m.new_content('Condition', 'CONDITION_TRUE')],
                                    [act('MAP_REVEAL_ALL_PERM', 'Player_1'),
                                     act('SET_MILLISECOND_TIMER', 'CNV A7 TestKill', 30.0)]))
    if TEST == '1':
        scripts.append(m.new_script('CNV A7 - Test Kill Power',
                                    [m.new_content('Condition', 'TIMER_EXPIRED', 'CNV A7 TestKill')],
                                    [act('NAMED_KILL', POWER)]))
    psl = next(n for _, n in m.walk() if n.name == 'PlayerScriptsList')
    psl.kids[2].kids += scripts
    print('A7: carrier', CARRIER, at, '| power', POWER, POWER_AT, '| waypoints', STRIKE, HOME, '|', len(scripts),
          'scripts', f'(test {TEST})' if TEST else '')


c6.edit = generate

if __name__ == '__main__':
    if c23.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
