r"""CNV05 「金门抢桥」 (CampBridge1): CampNew29's units on CampReal1's Golden Gate terrain (realmap.py).

Player (the city south of the strait): two 游隼, the shrink-ray vehicle, a Cryocopter, four Guardians, the CNV War
Factory, a power plant and an MCV; the amphibious Riptides are left out so the bridge stays the way across.
Soviets: three named Hammers hold the south bridgehead; when they are gone a caption says so and three more
attack-move across the bridge from the north shore (ATTACK_MOVE_NAMED_UNIT_TO a waypoint at the south end); three
hold the north bridgehead. All nine destroyed -> objective completed and SET_FLAG("Mission Won", 1) (CampNew30).

  python -I -X utf8 cnv.py build experimental/campaign/make_campbridge.py      (or run this file directly)
  python -I -X utf8 cnv.py map CampBridge1 --around 1700 3500 1500

Every placement is checked against realmap's water raster and moved to the nearest dry, gentle cell if needed.
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_campnew29 as c29                    # noqa: E402  (units chain: 游隼, shrink vehicle, Cryocopter ...)
import make_realmap as real                     # noqa: E402  (terrain: newmap.island_heights / paint_terrain)

c23 = c29.c23
c18, c7, c6, c4, c2 = c23.c18, c23.c7, c23.c6, c23.c4, c23.c2
newmap = c23.newmap
NAME = 'CampBridge1'                            # <= 15 characters, no underscore (skudef rule)
c4.NAME = c2.NAME = NAME
c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', NAME, 'data')
c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
c7.MAP_MOD = NAME + 'Map'

START = c18.START                               # (3300, 1500): the city; camera and start waypoints
BRIDGE_SOUTH = (1720.0, 2800.0)                 # where the bridge meets the Presidio (maprender: work/maps/CampReal1)
BRIDGE_NORTH = (1560.0, 4420.0)                 # where it meets the Marin shore
SOUTH_GUARD = [(1640.0, 2700.0), (1720.0, 2690.0), (1800.0, 2680.0)]
# CNV_TEST=1 (bench check of the script chain): the south guard stands next to the player's army and dies at
# once, so the caption and the wave's attack-move across the bridge show within a minute
TEST = os.environ.get('CNV_TEST') == '1'       # ... and the whole map is revealed
if TEST:            # in among the Guardians, at 1 % health (one out of range on the first try never died)
    SOUTH_GUARD = [(2990.0, 1860.0), (3060.0, 1870.0), (3130.0, 1860.0)]
NORTH_GUARD = [(1460.0, 4520.0), (1560.0, 4540.0), (1660.0, 4520.0)]
WAVE = [(1150.0, 4600.0), (1230.0, 4650.0), (1310.0, 4600.0)]
PLAYER = {                                      # template -> slots, in the city around START
    'AlliedMCV': [(3150.0, 1450.0)],
    'CNV_WarFactory': [(3350.0, 1300.0)],
    'AlliedPowerPlant': [(3550.0, 1300.0)],
    'CNV_LightTank2': [(3050.0, 1700.0), (3110.0, 1700.0)],
    'CNV_ShrinkVehicle': [(3000.0, 1620.0)],
    'AlliedSupportAircraft': [(3180.0, 1620.0)],
    'AlliedAntiVehicleVehicleTech1': [(2950.0, 1780.0), (3020.0, 1790.0), (3090.0, 1790.0), (3160.0, 1780.0)],
}
OBJ = c18.OBJ
WP_SOUTH = 'CNV Bridge South'
S_NAMES = [f'UNIT - CNV05 South {k + 1}' for k in range(len(SOUTH_GUARD))]
N_NAMES = [f'UNIT - CNV05 North {k + 1}' for k in range(len(NORTH_GUARD))]
W_NAMES = [f'UNIT - CNV05 Wave {k + 1}' for k in range(len(WAVE))]
c4.c3.STRINGS.update({
    c18.CAPTION: 'CNV05 金门抢桥：大桥是两岸唯一的陆路。先拿下南桥头，再过桥肃清北岸。',
    'MISSIONOBJ:CNV02_1': 'CNV05 目标：夺取金门大桥，消灭两岸的苏军装甲部队',
    'MISSIONOBJ:CNV02_1_DESC': '南桥头 3 辆铁锤守桥；拿下桥头后，北岸苏军会过桥反扑。冷冻、缩小之后再让游隼收割。',
    'SCRIPT:CNV05_SOUTH': 'CNV05：南桥头已夺取！北岸苏军正过桥反扑，守住桥头。',
    'SCRIPT:CNV05_WIN': 'CNV05：金门大桥两岸已肃清。',
})


def dry(x, y):
    """Nearest point to (x, y), searched in rings of 20, on dry land at least 20 above the waterline and not on
    a cliff (realmap's rasters; a raster cell is 10 units)."""
    r = real._real
    hs = real._cache['h']
    b = 30

    def ok(px, py):
        i, j = int(round(px / 10)) + b, int(round(py / 10)) + b
        e = hs.get((i, j))
        if e is None or e < newmap.WATERLINE + 20:
            return False
        return all(abs(hs.get((i + di, j + dj), e) - e) < 8 for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)))

    for ring in range(0, 30):
        for k in range(max(1, 8 * ring)):
            a = 2 * math.pi * k / max(1, 8 * ring)
            px, py = x + 20 * ring * math.cos(a), y + 20 * ring * math.sin(a)
            if ok(px, py):
                return px, py
    raise SystemExit(f'no dry land near {x}, {y}')


def _move(node, x, y, angle=None):
    head = bytearray(node.head)
    struct.pack_into('<ff', head, 0, x, y)
    if angle is not None:
        struct.pack_into('<f', head, 12, angle)
    node.head = bytes(head)


_generate = c6.edit


def generate(m):
    _generate(m)                                 # CampNew29 chain on the real terrain
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    tmpl = lambda k: k.head[22:22 + struct.unpack_from('<H', k.head, 20)[0]].decode('latin-1')     # noqa: E731
    soviet = next(k for k in objs.kids if tmpl(k) == 'SovietAntiVehicleVehicleTech1')
    wp_like = next(k for k in objs.kids if tmpl(k) == '*Waypoints/Waypoint')
    keep, used, moved = [], {t: 0 for t in PLAYER}, []
    for k in objs.kids:
        t = tmpl(k)
        if t == '*Waypoints/Waypoint':
            keep.append(k)
        elif t in PLAYER and used[t] < len(PLAYER[t]):
            x, y = dry(*PLAYER[t][used[t]])
            _move(k, x, y, angle=math.pi * 0.75)  # facing the bridge (north-west)
            used[t] += 1
            moved.append(t)
            keep.append(k)
    missing = {t: len(v) - used[t] for t, v in PLAYER.items() if used[t] < len(v)}
    assert not missing, f'the units chain no longer places {missing}'
    objs.kids[:] = keep
    pr, flags = newmap.typed_props_of(m, soviet)
    placed = {}
    for spots, names, angle in ((SOUTH_GUARD, S_NAMES, -math.pi / 2), (NORTH_GUARD, N_NAMES, -math.pi / 2),
                                (WAVE, W_NAMES, -math.pi / 2)):
        for (x, y), name in zip(spots, names):
            x, y = dry(x, y)
            placed[name] = (round(x), round(y))
            extra = {'objectInitialHealth': 1} if TEST and name in S_NAMES else {}
            objs.kids.append(newmap.object_node(m, pr, flags, 'SovietAntiVehicleVehicleTech1', x, y, angle=angle,
                                                objectName=name, uniqueID=f'Hammer {len(objs.kids)}', **extra))
    wpr, wflags = newmap.typed_props_of(m, wp_like)
    ids = [p.get('waypointID', (1, 0))[1] for p in (newmap.typed_props_of(m, k)[0] for k in objs.kids
                                                      if tmpl(k) == '*Waypoints/Waypoint')]
    wid = max(ids) + 1
    objs.kids.append(newmap.object_node(m, wpr, wflags, '*Waypoints/Waypoint', *BRIDGE_SOUTH,
                                        waypointName=WP_SOUTH, waypointID=wid, uniqueID=f'Waypoint {wid}'))

    south = m.new_script('CNV05 - South Taken', [m.new_content('Condition', 'NAMED_DESTROYED', n) for n in S_NAMES],
                         [m.new_content('ScriptAction', 'SHOW_MILITARY_CAPTION', 'SCRIPT:CNV05_SOUTH', 10.0)]
                         + [m.new_content('ScriptAction', 'ATTACK_MOVE_NAMED_UNIT_TO', n, WP_SOUTH) for n in W_NAMES])
    win = m.new_script('CNV05 - Win', [m.new_content('Condition', 'NAMED_DESTROYED', n)
                                       for n in S_NAMES + N_NAMES + W_NAMES],
                       [m.new_content('ScriptAction', 'SET_MISSION_OBJECTIVE_STATUS', OBJ, 2),
                        m.new_content('ScriptAction', 'SHOW_MILITARY_CAPTION', 'SCRIPT:CNV05_WIN', 10.0),
                        m.new_content('ScriptAction', 'SET_FLAG', 'Mission Won', 1)])
    psl = next(n for _, n in m.walk() if n.name == 'PlayerScriptsList')
    psl.kids[2].kids += [south, win]
    if TEST:            # the bench camera then sees the wave through the shroud on the far shore
        psl.kids[2].kids.append(m.new_script('CNV05 - Test Reveal', [m.new_content('Condition', 'CONDITION_TRUE')],
                                             [m.new_content('ScriptAction', 'MAP_REVEAL_ALL_PERM', 'Player_1')]))
    print('CNV05: player', moved, '\n  soviets', placed, '\n  waypoint', WP_SOUTH, BRIDGE_SOUTH, '+ 2 scripts')


c6.edit = generate

if __name__ == '__main__':
    if real.game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', NAME)
        print('RA3 is running -> staging at', c4.OUT)
    c4.main()
