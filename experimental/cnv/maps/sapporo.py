"""札幌雪祭，返工版 (the A4 rework's map: docs/design/a4-redesign.md 第 3 步 布局草图 and 地形和地块用途, P24-P28).
The festival map (maps/festival.py) stays as it is for J4 and the benches confirmed on it; this one is laid out for the
rework's three phases, one new piece of ground each:

  1. The corridor (border 'corridor', ~x 300-3200, y 1700-3300): the player comes in at its west end, the map's
     edge behind them (P17); the convoy drives in from off the border. West of x ~2100 the avenue (300 wide) runs
     in a street valley: both sides raised a tier. The north street block has the back lane on top -- a ramp up
     from the avenue at its west end, a lane 120 wide behind plaza 1, a ramp down between plazas 1 and 2 -- with
     room for a repair depot; the south block is backdrop (cliffs all round, no ramp). Plazas 1-3 are courtyards on
     the avenue's level closed by palace walls (bench 2026-10-27 fence bar: they hold infantry, fences do not), one
     gate 120 wide each; plaza 1 is cut into the north block (its cliffs the courtyard's sides).
  2. North and south (border 'west of the canal'): the south plateau is the player's base ground (a pair of ore by
     its refinery pad); the north plateau the enemy camp, its two front ramps 200 wide and a narrow back ramp
     straight to its power plant pad; the west ridge carries the TV tower pad (an observation post the level places).
  3. The whole map: three ways from the north to the convoy's road, each 120 wide -- the north mouth (a gap in a
     raised ward east of the north block), the east street (between plaza 3's wall and the canal) and plaza 3's gate
     -- then the canal's three bridges to the harbour; the harbour strip only between the bridges, its beach the sea
     side the Tengus come from. The south-west hills are an islet now (the coast drawn north of them).

The courtyards' walls, the bridges, ore and oil are the map's OBJECTS; tech buildings the level places (named:
the repair depot in the lane, the TV tower) at their pads. Sites keep the festival's names for what the plaza and
convoy devices ask (gate k, inside k, plaza k, approach k, convoy start, road exit, harbour, halt, north base, north
camp) with the same meaning; the rest are new.

Published: SITES, BORDERS, PLAYERS, TEAMS, OBJECTS, SCENERY, LAYOUT (shapes, ramps, roads, blocks, gaps).
"""
import struct

import make_campnew18 as c18
import platmap
import platprops
from platmap import Block, Gap, Layout, Ramp, Road, poly, rect, wobble
from platprops import along, area, cliff_feet, clumps, scatter, shore
from maps import island
from parts import Obj, Site

ROAD_Y, AVENUE = 2500.0, 300.0                  # the avenue's middle and width
ROAD_S, ROAD_N = ROAD_Y - AVENUE / 2, ROAD_Y + AVENUE / 2
CANAL = (3660.0, 3820.0)
GATE = 120.0                                    # every way the ice must shut: a gate, the lane, the mouths
WALL_IN = 15.0                                  # a courtyard's front wall this far off the avenue's edge
START = (450.0, ROAD_Y)                         # the corridor's west end, the map's edge behind it

# the street blocks either side of the avenue's west half (tier 2): x from the sea to WEST_END (north: to the lane's
# east end), plaza 1 cut into the north one
WEST_END = 2100.0
P1 = (2150.0, 2460.0, 3030.0)                   # plaza 1's courtyard: x0, x1, its back (y); its front the avenue
LANE = (3030.0, 3200.0)                         # the back lane behind plaza 1 (y): raised, between two cliffs
NB_EAST = (2460.0, 2760.0, 3260.0)              # the north block's east end: x0, x1, its back -- the lane comes
LANE_DOWN = 2610.0                              # down its ramp here (x), between plazas 1 and 2
NB_BACK = 3190.0                                # the north block's back (y), west of plaza 1
SB_FRONT = 1820.0                               # the south block's south edge (y): into the sea
P2 = (2680.0, 2980.0, 1980.0)                   # plaza 2's courtyard, south of the road: x0, x1, its back (y)
P3 = (3250.0, 3490.0, 3020.0)                   # plaza 3's, north of the road: x0, x1, its back (y); its west
                                                # side the ward's cliff
WARD = (2760.0, 3250.0, 3060.0)                 # the raised ward between the north block and plaza 3: x0, x1, back
NORTH_MOUTH_X = 3050.0                          # the gap through it (北坡口)
EAST_MOUTH = ((P3[1] + CANAL[0]) / 2, ROAD_N + 120.0)     # 东街口: between plaza 3's wall and the canal

PLAZAS = {1: ((P1[0] + P1[1]) / 2, True), 2: ((P2[0] + P2[1]) / 2, False), 3: ((P3[0] + P3[1]) / 2, True)}


def _gate(k):
    x, north = PLAZAS[k]
    return x, (ROAD_N + WALL_IN if north else ROAD_S - WALL_IN)


SITES = {'island': island.SITES['island']}
SITES.update({
    'start': Site(*START, 0.0, "the player's start: the corridor's west end, the map's edge behind it (P17); the "
                               'start camera looks here'),
    'entry': Site(80.0, ROAD_Y, 60.0, 'the avenue past the west border: what comes in from off the map is made here'),
    'convoy start': Site(250.0, ROAD_Y, 100.0, 'the avenue at the west border: the convoy forms up here (trucks made '
                                               'at the departure stand west of it, off the border)'),
    'road exit': Site(3900.0, ROAD_Y, 150.0, "the road's east end in the harbour, past the canal bridge: the convoy "
                                             'is safe here'),
    'harbour': Site(4030.0, ROAD_Y, 180.0, 'the harbour ground at the east end of the canal bridge'),
    'halt': Site((P2[0] + P2[1]) / 2, ROAD_Y, 40.0, "the road at plaza 2's gate: past plaza 2, short of plaza 3's "
                                                    'approach'),
    'lane foot': Site(1250.0, ROAD_Y + 40.0, 60.0, "the back lane's way up: the foot of the ramp from the avenue "
                                                   'onto the north street block'),
    'lane mouth': Site(P1[0] + 60.0, (LANE[0] + LANE[1]) / 2, 50.0, "the back lane's west mouth, behind plaza 1: "
                                                                    'its sculptures stand here'),
    'lane depot': Site(LANE_DOWN, 3120.0, 0.0, "the lane's east end, on the north block: a repair depot's pad",
                       build=160.0),
    'lane end': Site(LANE_DOWN, ROAD_Y + 80.0, 60.0, 'where the back lane comes down to the avenue, between plazas 1 '
                                                    'and 2'),
    'north mouth': Site(NORTH_MOUTH_X, (ROAD_N + WARD[2]) / 2, 60.0, '北坡口: the gap through the raised ward, '
                                                                    f'{GATE:g} wide, from the north camp to the road'),
    'east mouth': Site(*EAST_MOUTH, 50.0, f"东街口: the street between plaza 3's wall and the canal, {GATE:g} wide"),
    'north camp': Site(2900.0, 3250.0, 200.0, 'open low ground behind the ward, below the north plateau: where a '
                                              'force from the north gathers'),
    'north base': Site(3050.0, 4100.0, 250.0, 'the north plateau past its ore: room for a small camp', build=160.0),
    'north power': Site(2250.0, 3760.0, 0.0, "the north plateau's west end: a power plant's pad at the head of the "
                                             'back ramp', build=160.0),
    'back ramp': Site(1820.0, 3720.0, 60.0, "the foot of the north plateau's back ramp (narrow, to its power plant)"),
    'front ramp west': Site(2650.0, 3330.0, 80.0, "the foot of the north plateau's west front ramp (200 wide)"),
    'front ramp east': Site(3150.0, 3330.0, 80.0, "the foot of the north plateau's east front ramp (200 wide)"),
    'south base': Site(2850.0, 1150.0, 250.0, "the south plateau: the player's base ground (a construction yard's "
                                              'pad)', build=250.0),
    'south refinery': Site(2440.0, 1230.0, 0.0, "a refinery's pad by the south plateau's pair of ore (~180 off, as "
                                                'retail)', build=200.0),
    'south ramp': Site(2350.0, 1720.0, 80.0, "the foot of the south plateau's ramp, down to the low ground by the "
                                             'avenue'),
    'tv tower': Site(700.0, 3950.0, 0.0, "the west ridge's top: the TV tower's pad (an observation post)",
                     build=160.0),
    'ridge ramp': Site(1400.0, 3360.0, 60.0, "the foot of the west ridge's ramp"),
    'beach': Site(4120.0, 2900.0, 100.0, "the harbour's sea side: what flies in from the sea comes over here"),
    'sea east': Site(4750.0, 2900.0, 100.0, 'off the harbour, over the sea: aircraft from the sea are made here'),
    'north bridge': Site(3740.0, 3420.0, 60.0, 'the canal\'s north bridge'),
    'south bridge': Site(3740.0, 1850.0, 60.0, 'the canal\'s south bridge'),
})
for _k, (_x, _north) in PLAZAS.items():
    _s, _side = (1 if _north else -1), ('north' if _north else 'south')
    _gx, _gy = _gate(_k)
    SITES[f'gate {_k}'] = Site(_gx, _gy, 0.0, f"plaza {_k}'s gate: the one gap in its front wall ({GATE:g} wide), on "
                                             f'the road\'s {_side} edge')
    SITES[f'inside {_k}'] = Site(_gx, _gy + _s * 40.0, 0.0, f"just inside plaza {_k}'s gate, on the road's level: a "
                                                          'block of ice 160 across here shuts it', build=160.0)
    SITES[f'plaza {_k}'] = Site(_gx, _gy + _s * 200.0, 120.0, f'plaza {_k}, a walled courtyard {_side} of the road: '
                                                            'its sculptures stand here')
    SITES[f'approach {_k}'] = Site(_gx - 350.0, ROAD_Y, 150.0, f'the road west of plaza {_k}: a convoy here is '
                                                             'about to pass it')
# MAP_SWITCH_BORDER(k) makes the k-th the playable area (x0 y0 x1 y1; the first is the whole map)
BORDERS = {'whole': (0.0, 0.0, 5000.0, 5000.0), 'corridor': (300.0, 1700.0, 3200.0, 3300.0),
           'west of the canal': (0.0, 0.0, CANAL[0] - 20.0, 5000.0)}
PLAYERS = island.PLAYERS
TEAMS = dict(island.TEAMS, s1='Soviet_1/teamSoviet_1')

# ---- the ground
COAST = wobble([(0, ROAD_S + 10), (0, ROAD_N - 10), (120, 2760), (230, 3300), (300, 3800), (600, 4600),
                (1800, 4500), (3000, 4620), (3600, 4600), (3700, 4590), (3700, 600), (3100, 430), (2000, 540),
                (1880, 900), (1860, 1400), (1950, 1640), (1800, 1880), (900, 1900), (250, 1950), (100, 2250)],
               100.0, 51, keep=[(0, ROAD_Y, 260.0), (3700, 2500, 2100.0), (1950, 1640, 200.0)])
HARBOUR = wobble([(3700, 1480), (4250, 1470), (4300, 2300), (4180, 2900), (4270, 3720), (3700, 3720)], 12.0, 52,
                 keep=[(3700, 2600, 1300.0)])
NORTH_PLATEAU = wobble([(2000, 3560), (2650, 3550), (3150, 3550), (3450, 3580), (3530, 3900), (3430, 4300),
                        (3000, 4420), (2500, 4390), (2050, 4310), (1940, 3900)], 60.0, 53,
                       keep=[(2650, 3550, 160.0), (3150, 3550, 160.0), (1965, 3720, 150.0)])
KNOLL = wobble([(2080, 4020), (2300, 3990), (2420, 4130), (2350, 4300), (2130, 4300), (2040, 4170)], 30.0, 54)
SOUTH_PLATEAU = wobble([(2000, 1490), (2350, 1500), (2800, 1510), (3400, 1480), (3480, 1100), (3380, 760),
                        (2700, 700), (2050, 760), (1930, 1100)], 60.0, 55, keep=[(2350, 1500, 160.0)])
WEST_RIDGE = wobble([(350, 3500), (1100, 3480), (1200, 3800), (1080, 4350), (600, 4420), (330, 4000)], 70.0, 56,
                    keep=[(1080, 3600, 240.0)])
SW_HILLS = wobble([(330, 700), (1100, 590), (1520, 720), (1470, 1130), (1000, 1260), (480, 1170)], 80.0, 57)
ISLETS = [wobble([(x + r * c, y + r * s) for c, s in ((1, 0), (.7, .7), (0, 1), (-.7, .7), (-1, 0), (-.7, -.7),
                                                     (0, -1), (.7, -.7))], r * 0.3, 60 + k)
          for k, (x, y, r) in enumerate(((150, 250, 170), (4650, 1150, 190), (4700, 4100, 150), (1300, 4950, 160),
                                         (2800, 120, 130)))]
# the north street block: west part to NB_BACK, plaza 1 cut out of it, the lane's strip behind plaza 1, the east end
NORTH_BLOCK = [(-50, ROAD_N), (P1[0], ROAD_N), (P1[0], P1[2]), (P1[1], P1[2]), (P1[1], ROAD_N), (NB_EAST[1], ROAD_N),
               (NB_EAST[1], NB_EAST[2]), (P1[1], NB_EAST[2]), (P1[1], LANE[1]), (P1[0], LANE[1]), (P1[0], NB_BACK),
               (-50, NB_BACK)]
SOUTH_BLOCK = [(-50, SB_FRONT), (WEST_END - 100, SB_FRONT), (WEST_END - 100, ROAD_S), (-50, ROAD_S)]
WARD_W = (WARD[0], ROAD_N, NORTH_MOUTH_X - GATE / 2 - 40, WARD[2])     # its cliffs take ~40 off each side
WARD_E = (NORTH_MOUTH_X + GATE / 2 + 40, ROAD_N, WARD[1], WARD[2])
SHAPES = [
    poly(COAST, 1, 'the island: low ground'),
    poly(HARBOUR, 1, 'the harbour strip, between the bridges'),
    *[poly(p, 1, 'an islet') for p in ISLETS],
    poly(SW_HILLS, 2, 'the south-west hills, an islet'),
    poly(NORTH_PLATEAU, 2, 'north plateau'),
    poly(KNOLL, 3, 'the shrine knoll'),
    poly(SOUTH_PLATEAU, 2, 'south plateau'),
    poly(WEST_RIDGE, 2, 'the west ridge'),
    poly(NORTH_BLOCK, 2, 'the north street block (the back lane on top)'),
    poly(SOUTH_BLOCK, 2, 'the south street block'),
    rect(*WARD_W, 2, 'the ward west of the north mouth'),
    rect(*WARD_E, 2, 'the ward east of the north mouth'),
    rect(CANAL[0], 200, CANAL[1], 4800, 0, 'the canal'),
]
RAMPS = [
    Ramp((1250, ROAD_Y + 40), (1250, ROAD_N + 230), 160.0, 'the back lane up (west)'),
    Ramp((LANE_DOWN, ROAD_Y + 60), (LANE_DOWN, ROAD_N + 300), GATE, 'the back lane down (east)'),
    Ramp((2650, 3330), (2650, 3700), 200.0, 'north plateau west'),
    Ramp((3150, 3330), (3150, 3700), 200.0, 'north plateau east'),
    Ramp((1820, 3720), (2090, 3720), 100.0, 'north plateau back'),
    Ramp((2350, 1720), (2350, 1350), 200.0, 'south plateau'),
    Ramp((1400, 3360), (1030, 3640), 180.0, 'west ridge'),
]
# streets (ground texture only): the lane on the north block, up to the plateaus' ramps, the canal's west bank, the
# harbour's street
LANE_WAY = ((1250, ROAD_N + 230), (1300, 2980), (P1[0] - 20, 3100), (P1[1] + 40, 3100), (LANE_DOWN, 3020),
            (LANE_DOWN, ROAD_N + 300))
STREETS = [((2650, ROAD_N), (2650, 3330)), ((3150, ROAD_N), (3150, 3330)), ((2350, ROAD_S), (2350, 1720)),
           ((EAST_MOUTH[0], ROAD_N), (EAST_MOUTH[0], 4300)), ((3580, ROAD_S), (3580, 1600)),
           ((3900, 1600), (3900, 3650)), ((1400, 3360), (1400, 3200)), ((1820, 3720), (1700, 3400))]
ROADS = [Road(((0, ROAD_Y), (4050, ROAD_Y)), 160.0), Road(LANE_WAY, 90.0), *[Road(s, 90.0) for s in STREETS]]

# ---- the courtyards' walls: palace wall pieces round three sides and the front, one gate each (plaza 1's sides are
# the north block's cliffs: only its front is walled)
WALLS = []


def _walls():
    out = []
    gx, gy = _gate(1)
    out += platmap.wall_line([(P1[0] - 10, gy), (P1[1] + 10, gy)], gaps=[(gx, gy, GATE)])
    gx, gy = _gate(2)
    out += platmap.wall_line([(P2[0], gy), (P2[0], P2[2]), (P2[1], P2[2]), (P2[1], gy), (P2[0], gy)],
                             gaps=[(gx, gy, GATE)])
    gx, gy = _gate(3)
    out += platmap.wall_line([(P3[0] - 20, P3[2]), (P3[1], P3[2]), (P3[1], gy), (P3[0] - 20, gy)],
                             gaps=[(gx, gy, GATE)])
    return out


WALLS = _walls()
BRIDGES = [((3590, 2500), (3890, 2500)), ((3590, 3420), (3890, 3420)), ((3590, 1850), (3890, 1850))]


def _objects():
    out = []
    for p, q in BRIDGES:
        for x, y, a, flags in platmap.bridge(p, q, 'HB_Bridge_02'):
            out.append(Obj('HB_Bridge_02', x, y, side='neutral', angle=a, flags=flags, site='map'))
    ore = [(2350, 1080), (2540, 1020),              # the south plateau: the player's base
           (2600, 3900), (2790, 3960),              # north plateau
           (4000, 1650), (4000, 1830),              # the harbour, past the canal
           (2450, 2120)]                            # the low ground between the south plateau and the avenue
    out += [Obj('OreNode', x, y, side='neutral', angle=0.0, site='map') for x, y in ore]
    for x, y in ((3200, 4050), (2120, 1660)):     # the north plateau's; one at the south ramp's foot (the base's)
        out.append(Obj('OilDerrick', x, y, side='neutral', angle=0.0, site='map'))
    out += [Obj(t, round(x, 1), round(y, 1), side='civ', angle=round(a, 4), site='map') for t, x, y, a in WALLS]
    return out


OBJECTS = _objects()

# ---- what each piece of ground is for (P24; the table in a4-redesign.md 地形和地块用途), the ways the ice shuts
BLOCKS = [
    Block(rect(P1[0], ROAD_N, P1[1], P1[2], 1), '前线', 'plaza 1'),
    Block(rect(P2[0], P2[2], P2[1], ROAD_S, 1), '前线', 'plaza 2'),
    Block(rect(P3[0], ROAD_N, P3[1], P3[2], 1), '前线', 'plaza 3'),
    Block((-50, ROAD_S, CANAL[0], ROAD_N), '通道', 'the avenue'),
    Block(poly(NORTH_BLOCK, 2), '支线', 'the north street block: the back lane, the repair depot'),
    Block(poly(SOUTH_BLOCK, 2), '远景', 'the south street block'),
    Block(WARD_W, '支线', 'the ward west of the north mouth: the north block goes on over it'),
    Block(WARD_E, '远景', 'the ward east of the north mouth'),
    Block((WARD_W[2], ROAD_N, WARD_E[0], WARD[2] + 40), '前线', 'the north mouth'),
    Block((P3[1], ROAD_N, CANAL[0], 4400), '前线', 'the east street along the canal'),
    Block((1700, 1450, CANAL[0], ROAD_S), '通道', 'the low ground between the south plateau and the avenue'),
    Block(poly(SOUTH_PLATEAU, 2), '后方', "the south plateau: the player's base"),
    Block((-50, NB_BACK, CANAL[0], 3560), '前线', 'the north camp and the low ground below the north plateau'),
    Block(poly(NORTH_PLATEAU, 2), '前线', 'the north plateau: the enemy camp'),
    Block(poly(KNOLL, 3), '远景', 'the shrine knoll'),
    Block((1300, 3560, 2000, 4500), '通道', 'the way to the back ramp'),
    Block(poly(WEST_RIDGE, 2), '支线', 'the west ridge: the TV tower'),
    Block((300, 3560, 1300, 4600), '通道', 'below the west ridge'),
    Block((CANAL[0] - 40, 1400, 4400, 3800), '前线', 'the canal bridges and the harbour'),
    Block(poly(SW_HILLS, 2), '远景', 'the south-west hills'),
]
GAPS = [Gap(*_gate(k), GATE, f'gate {k}') for k in (1, 2, 3)] + [
    Gap(P1[0] + 150, (LANE[0] + LANE[1]) / 2, GATE, 'the back lane'),
    Gap(NORTH_MOUTH_X, (ROAD_N + WARD[2]) / 2, GATE, 'the north mouth'),
    Gap(*EAST_MOUTH, GATE, 'the east mouth'),
]
LAYOUT = Layout(shapes=SHAPES, ramps=RAMPS, roads=ROADS, blocks=BLOCKS, gaps=GAPS)

# ---- the look (retail objects only, platprops)
WOODS = {'HB_Tree03': 3, 'HB_Tree04': 2, 'HB_Tree05': 2, 'OK_Tree01': 3, 'OK_Tree02': 2, 'TH_Tree01': 1}
PARK = {'OK_Tree01': 3, 'OK_Tree02': 2, 'TH_Tree02': 2, 'HB_TREE09': 1}
UNDER = {'OK_Shrub01': 3, 'OK_Shrub04': 2, 'GC_Bush01': 2, 'HB_GRASS02': 3, 'ST_PLANT09': 2}
ROCKS = {'YU_LARGEROCKS02': 1, 'YU_SMALLROCKS01': 2, 'HA_GardenRock01': 2, 'OK_GARDENROCK03': 1}
HOUSES = {'MJ_Structure_02': 3, 'MJ_Structure_04': 2, 'HA_Building16_02': 3, 'HA_Building16_03': 2,
          'TH_SushiBar_01': 2, 'TH_PHpagoda_04': 1, 'TH_PHpagoda_02': 1}
# kept open: the courtyards whole, the start, the harbour ground, the base ground, the camp
AVOID = [(*START, 250.0), (SITES['harbour'].x, SITES['harbour'].y, SITES['harbour'].r + 80.0),
         (SITES['south base'].x, SITES['south base'].y, 450.0), (SITES['north base'].x, SITES['north base'].y, 350.0),
         (SITES['north camp'].x, SITES['north camp'].y, 200.0)] + \
    [(((P[0] + P[1]) / 2, y0), ((P[0] + P[1]) / 2, y1), (P[1] - P[0]) / 2 + 30)
     for P, y0, y1 in ((P1, ROAD_N, P1[2]), (P2, ROAD_S, P2[2]), (P3, ROAD_N, P3[2]))]
LANDMARKS = [('OK_Pagoda01', 2230, 4150, 0.0), ('OK_ARCH01', 2230, 4040, 0.0),
             ('TH_harbor_crane01', 4180, 2150, 0.0), ('TH_harbor_crane01', 4140, 3350, 0.0)]


def _scenery():
    ground = platprops.Ground(LAYOUT)
    picks = []

    def put(cands, must=False, avoid=AVOID):
        picks.extend(platprops.place(cands, LAYOUT, SITES, OBJECTS, keep=picks, avoid=avoid, ground=ground,
                                     must=must))
    put(LANDMARKS, must=True)
    # the avenue as a park east of the street valley: lanterns and banners all the way, trees where there is room
    avenue = [(300, ROAD_Y), (CANAL[0] - 60, ROAD_Y)]
    put(along(avenue, ['OK_LANTERN01', 'MJ_BANNER01', 'MJ_BANNER02', 'TH_LAMPDECO03'], 70, 105, 1, jitter=0.0))
    put(along([(WEST_END, ROAD_Y), (CANAL[0] - 60, ROAD_Y)], PARK, 60, 175, 2))
    # the street blocks: houses on both, facing the avenue, the lane's way kept (a road)
    put(along([(0, ROAD_Y), (WEST_END, ROAD_Y)], HOUSES, 120, 240, 10, face=True))
    put(scatter(area('poly', NORTH_BLOCK), HOUSES, 150, 11, density=0.7))
    put(scatter(area('poly', SOUTH_BLOCK), HOUSES, 140, 12, density=0.8))
    put(along(LANE_WAY, 'TH_LAMPPOST04', 110, 55, 13))
    for k, street in enumerate(STREETS[:2]):
        put(along(street, HOUSES, 120, 150, 20 + k, face=True))
        put(along(street, 'TH_LAMPPOST04', 120, 62, 22 + k))
    put(along(STREETS[5], {'TH_Fish_Market02': 2, 'TH_Fish_Market03': 2, 'TH_FISH_MARKET04': 2}, 95, 125, 30,
              face=True, sides=(-1,)))
    put(along(STREETS[5], 'TH_LAMPPOST04', 120, 62, 31))
    put(clumps(area('rect', (3950, 1550, 4250, 3650)), 10, 40, 6, {'TH_JAPANCRATE01': 2, 'TH_JAPANOILDRUM01': 1}, 32))
    # woods on the hills, the ridge, the plateaus' edges, the coast; rocks at the cliffs' feet
    for k, region in enumerate((WEST_RIDGE, SW_HILLS, KNOLL, *ISLETS)):
        put(scatter(area('poly', region), WOODS, 50, 40 + k, density=0.85, patches=0.4))
    for k, region in enumerate((NORTH_PLATEAU, SOUTH_PLATEAU)):
        put(scatter(area('poly', region), WOODS, 60, 50 + k, density=0.8, patches=0.55))
    put(scatter(area('poly', COAST), WOODS, 60, 52, density=0.6, patches=0.62))
    put(shore(ground, {**WOODS, **ROCKS}, 70, 53))
    put(cliff_feet(ground, ROCKS, 90, 54))
    put(scatter(area('rect', (0, 0, 5000, 5000)), UNDER, 100, 55, density=0.4, patches=0.35))
    return [Obj(t, round(x, 1), round(y, 1), side='civ', angle=round(a, 3), site='map') for t, x, y, a in picks]


SCENERY = _scenery()


def terrain(m):
    """CampNew18's generate with the platform terrain over its island, and the starts moved to this map's own
    (c18 puts them at island.py's, the template's default)."""
    c18.generate(m)
    previews, _ = platmap.apply(m, LAYOUT)
    c18.PREVIEWS.update(previews)
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    import newmap
    for k in objs.kids:
        name = newmap.typed_props_of(m, k)[0].get('waypointName', (0, ''))[1]
        if name in ('Player_1_Start', 'InitialCameraPosition', 'Player_2_Start'):
            dx = 60.0 if name == 'Player_2_Start' else 0.0
            k.head = struct.pack('<ff', START[0] + dx, START[1] + dx) + k.head[8:]


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
