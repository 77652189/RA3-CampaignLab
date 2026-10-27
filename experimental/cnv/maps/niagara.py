"""尼亚加拉 (A7 鹰派, docs/story/plans/a7.md), built the retail way (docs/story/map-language.md, platmap): only like
Niagara -- a river from north to south that Goat Island splits, the hydro station on the island, the hawks across
the river, wooded banks and a gorge below the falls -- shaped by what the level needs, not by the real falls.

  - West bank (the player): low ground (tier 1) round the start, and a raised plateau (tier 2) north-east of the base
    with ramps, where two of the three outposts stand; the third is on low ground south. Behind the base a wooded
    ridge along the west edge (a peak, tier 3, in the north-west corner) and hills in the south-west: backdrop, no
    way up.
  - The river runs the map's length, bank to bank ~600, bending a little: the ground army crosses only by three
    bridges -- the north one, and two short ones from the west bank to Goat Island and on to the east bank (the
    banks run straight at the bridges). The island is the station's: water all round, wooded at its ends.
  - East bank: the hawks' base and the carrier's home, a small town south of the base; south of that a bluff
    (tier 2) drops straight into the river -- the gorge -- with one ramp up and ore on top; a ridge along the east
    edge and a hill in the north-east. The carrier leaves the battle by the north edge.
  - Borders: the west bank alone (phase 1), then the whole map.

Published: SITES, PLAYERS, TEAMS, OBJECTS (ore, a derrick, the bridges), SCENERY (retail trees, rocks, cabins ...:
platprops, kept off every way and place), LAYOUT, BORDERS.
"""
import make_campnew18 as c18
import platmap
import platprops
from platmap import Layout, Ramp, Road, poly, wobble
from platprops import along, area, cliff_feet, clumps, scatter, shore
from maps import island
from parts import Obj, Site

RIVER = (2300.0, 2900.0)                        # its west and east banks (x) at the bridges
GOAT = (2450.0, 2750.0, 2450.0, 3350.0)         # Goat Island: x0, x1, y0, y1 (roughly: its shape is GOAT_SHORE)
PLATEAU = (1500.0, 2150.0, 2950.0, 4400.0)      # the west plateau: x0, x1, y0, y1 (roughly: PLATEAU_EDGE)
BRIDGE_Y = 2900.0                               # the island's two bridges
NORTH_Y = 4200.0                                # the north bridge

SITES = {k: island.SITES[k] for k in ('island', 'start', 'base factory', 'base power', 'west field', 'base edge')}
SITES.update({
    'base yard': Site(1250.0, 2500.0, 0.0, "the construction yard's pad on the player's start", build=200.0),
    'base ore': Site(950.0, 2000.0, 150.0, "the player's own ore, ~550 from the start"),
    'front': Site(2050.0, 2900.0, 200.0, 'the west end of the island bridge: where the player meets the river'),
    'outpost 1': Site(1700.0, 3350.0, 120.0, 'an outpost on the west plateau', build=160.0),
    'outpost 2': Site(1900.0, 1650.0, 120.0, 'an outpost on low ground south of the base', build=160.0),
    'outpost 3': Site(1900.0, 4150.0, 120.0, 'an outpost on the plateau by the north bridge: the hawks pass it',
                      build=160.0),
    'goat island': Site(2600.0, 2900.0, 140.0, 'Goat Island, between the two arms of the river: the station is here'),
    'station': Site(2600.0, 2650.0, 0.0, "the hydro station's pad on the island", build=200.0),
    'north bridge': Site(2600.0, NORTH_Y, 300.0, 'the north bridge, west bank to east bank'),
    'east base': Site(3850.0, 3400.0, 500.0, "the hawks' base on the east bank"),
    'east barracks': Site(3600.0, 3250.0, 0.0, "the hawks' barracks", build=160.0),
    'east factory': Site(3950.0, 3150.0, 0.0, "the hawks' war factory", build=200.0),
    'east airfield': Site(4050.0, 3700.0, 0.0, "the hawks' airfield", build=250.0),
    'east power': Site(4250.0, 3450.0, 0.0, "the hawks' own power plant", build=100.0),
    'east refinery': Site(4450.0, 2800.0, 0.0, "the hawks' refinery, by their ore (the skirmish AI's income)",
                         build=250.0),
    'east gate': Site(3150.0, 3300.0, 200.0, "open ground between the hawks' base and the bridges: their army forms "
                                             'up here'),
    'carrier home': Site(3700.0, 2400.0, 250.0, 'over the east bank south of the base: where the carrier waits'),
    'route 1': Site(4000.0, 3000.0, 150.0, "the carrier's way out, first leg"),
    'route 2': Site(3600.0, 3950.0, 150.0, "the carrier's way out, second leg"),
    'north exit': Site(3300.0, 4700.0, 200.0, 'the north edge over the east bank: past it the carrier is gone'),
})
PLAYERS = island.PLAYERS
TEAMS = dict(island.TEAMS, s1='Soviet_1/teamSoviet_1')
BORDERS = {'whole': (0.0, 0.0, 5000.0, 5000.0), 'west bank': (0.0, 0.0, RIVER[0] - 30.0, 5000.0)}

BRIDGES = [((2250.0, BRIDGE_Y), (2520.0, BRIDGE_Y)), ((2680.0, BRIDGE_Y), (2950.0, BRIDGE_Y)),
           ((2250.0, NORTH_Y), (2950.0, NORTH_Y))]
_AT_BRIDGES = [(x, y, 120.0) for p, q in BRIDGES for x, y in (p, q)]

# the river's banks, south to north: straight (x = RIVER) from 300 short of each bridge to 300 past it; the
# gorge's bluffs follow them exactly (a bank's first points, bent the same way: _bank)
WEST_BANK = [(2300, -300), (2340, 500), (2345, 850), (2350, 1300), (2280, 2100), (2300, 2600), (2300, 3200),
             (2300, 3900), (2300, 4500), (2340, 5000), (2380, 5300)]
EAST_BANK = [(2900, -300), (3020, 500), (3000, 1300), (2965, 1750), (2930, 2100), (2900, 2600), (2900, 3200),
             (2990, 3560), (2900, 3900), (2900, 4500), (2960, 5000), (3010, 5300)]
BANK_BEND, BANK_SEED = 55.0, {'west': 31, 'east': 32}


def _bank(side, points):
    return wobble(points, BANK_BEND, BANK_SEED[side], keep=_AT_BRIDGES, closed=False)


GOAT_SHORE = wobble([(2600, 2385), (2700, 2410), (2755, 2520), (2765, 2700), (2760, 2900), (2745, 3100),
                     (2705, 3300), (2640, 3440), (2575, 3465), (2505, 3385), (2460, 3200), (2440, 2950),
                     (2435, 2700), (2448, 2500), (2510, 2410)], 18.0, 41,
                    keep=[(2520, BRIDGE_Y, 70.0), (2680, BRIDGE_Y, 70.0)])
PLATEAU_EDGE = wobble([(1530, 2950), (1800, 2950), (2100, 2965), (2150, 3300), (2135, 3800), (2155, 4150),
                       (2120, 4400), (1800, 4440), (1520, 4385), (1480, 4000), (1500, 3500), (1465, 3200)], 35.0, 43,
                      keep=[(1500, 3500, 160.0), (1800, 2950, 160.0)])
WEST_RIDGE = wobble([(-300, 900), (250, 1000), (390, 1800), (300, 2600), (430, 3400), (360, 4200), (620, 4700),
                     (1100, 4930), (1500, 5300), (-300, 5300)], 110.0, 44)
NW_PEAK = wobble([(-300, 3950), (150, 4150), (380, 4700), (780, 5020), (900, 5300), (-300, 5300)], 90.0, 45)
# the gorge below the falls: bluffs on both banks drop straight into the river, south of the ore by outpost 2
SW_HILLS = _bank('west', WEST_BANK[:3]) + wobble([(2345, 850), (2150, 880), (1750, 720), (1450, 640), (900, 800),
                                                  (420, 700), (-300, 900), (-300, -300)], 90.0, 46, closed=False)
SE_BLUFF = _bank('east', EAST_BANK[:4]) + wobble([(2965, 1750), (3300, 1800), (3700, 1850), (4100, 1720),
                                                  (4500, 1820), (5300, 1700), (5300, -300)], 80.0, 47,
                                                 keep=[(3700, 1850, 160.0)], closed=False)
EAST_RIDGE = wobble([(5300, 1700), (4880, 1800), (4810, 2600), (4890, 3300), (4850, 4000), (5300, 4000)], 90.0, 48)
NE_HILL = wobble([(4100, 5300), (4120, 4800), (4380, 4300), (4620, 4060), (5300, 4000), (5300, 5300)], 100.0, 49)
# the town on the bluff, up its ramp: its streets
TOWN = [((3700, 1650), (3950, 1400), (3950, 500)), ((3950, 1150), (4650, 1150)), ((3950, 700), (4650, 700)),
        ((4350, 1400), (4350, 400))]

LAYOUT = Layout(
    shapes=[
        poly(_bank('west', WEST_BANK) + [(-300, 5300), (-300, -300)], 1, 'west bank: low ground'),
        poly(_bank('east', EAST_BANK) + [(5300, 5300), (5300, -300)], 1, 'east bank: low ground'),
        poly(GOAT_SHORE, 1, 'Goat Island'),
        poly(PLATEAU_EDGE, 2, 'the west plateau'),
        poly(WEST_RIDGE, 2, 'the west ridge behind the base'),
        poly(NW_PEAK, 3, 'the north-west peak'),
        poly(SW_HILLS, 2, 'the south-west hills'),
        poly(SE_BLUFF, 2, 'the bluff over the gorge, east bank south'),
        poly(EAST_RIDGE, 2, 'the east ridge'),
        poly(NE_HILL, 2, 'the north-east hill'),
    ],
    ramps=[
        Ramp((1350.0, 3500.0), (1580.0, 3500.0), 200.0, 'west plateau, west side'),
        Ramp((1800.0, 2780.0), (1800.0, 3030.0), 200.0, 'west plateau, south side'),
        Ramp((3700.0, 2150.0), (3700.0, 1650.0), 200.0, 'the bluff'),
    ],
    roads=[Road(((1300, 2500), (2050, 2500), (2050, BRIDGE_Y), (2250, BRIDGE_Y)), 120.0),
           Road(((2950, BRIDGE_Y), (3150, 3300), (3600, 3300)), 120.0),
           Road(((2520, BRIDGE_Y), (2680, BRIDGE_Y)), 100.0),
           Road(((2600, BRIDGE_Y), (2600, 2760)), 80.0),
           Road(((2250, NORTH_Y), (2225, 4520), (1800, 4620), (1250, 4330), (1150, 3900), (1250, 3000),
                 (1250, 2620)), 90.0, 'Dirt_Yucatan04'),
           Road(((1250, 3500), (1350, 3500)), 90.0, 'Dirt_Yucatan04'),
           Road(((2950, NORTH_Y), (3300, 3900), (3600, 3500), (3600, 3300)), 110.0),
           Road(((3600, 3300), (4250, 3000), (4400, 2950)), 100.0),
           Road(((1250, 2380), (1550, 1950), (1900, 1720)), 90.0, 'Dirt_Yucatan04'),
           Road(((3150, 3300), (3500, 2700), (3700, 2350), (3700, 2150)), 90.0, 'Dirt_Yucatan04'),
           Road(((3700, 1650), (3450, 1420)), 90.0, 'Dirt_Yucatan04'),
           *[Road(s, 90.0) for s in TOWN]])


def _objects():
    out = []
    for p, q in BRIDGES:
        for x, y, a, flags in platmap.bridge(p, q, 'HB_Bridge_02'):
            out.append(Obj('HB_Bridge_02', x, y, side='neutral', angle=a, flags=flags, site='map'))
    ore = [(850, 2050), (1010, 1930),               # the player's own, ~550 from the start
           (1050, 3750), (1230, 3850),              # north of the base, below the plateau
           (2000, 1150), (2180, 1060),              # the south, by outpost 2
           (4150, 2950), (4250, 3120),              # the hawks' own
           (3400, 1300)]                            # one on the bluff over the gorge, east bank south
    out += [Obj('OreNode', x, y, side='neutral', angle=0.0, site='map') for x, y in ore]
    out.append(Obj('OilDerrick', 700, 3200, side='neutral', angle=0.0, site='map'))
    return out


OBJECTS = _objects()

WOODS = {'MR_Redwood01': 2, 'MR_Tree04': 3, 'MR_TREE01': 2, 'MR_Tree05': 2, 'MR_Tree06': 2, 'YP_Tree02': 3,
         'CC_Tree03': 1}
UNDER = {'CC_Bush01': 3, 'CC_BUSH02': 3, 'OK_Shrub01': 2, 'YP_Fern01': 3, 'CC_GRASS06': 3, 'CC_Grass01': 2}
ROCKS = {'YU_LARGEROCKS02': 1, 'YU_SMALLROCKS01': 2, 'YU_SMALLROCKS02': 2}
# building ground kept open: the player's base round the start, the hawks' round theirs
AVOID = [(1250.0, 2500.0, 700.0), (3850.0, 3400.0, 650.0)]
# buildings by hand (template, x, y, angle), placed first and every one of them (place(must=True) raises if one may
# not stand where it is): a ranger station and lookouts over the falls on the west bank, cabins in the south-west
# woods, a few houses on the east bank south of the hawks' base
LANDMARKS = [('YP_RSTATION', 2020, 2240, 0.5), ('YP_WatchTower', 2190, 2640, 0.0),
             ('YP_WatchTower', 2240, 3240, 0.0),
             ('YP_Cabin', 700, 1480, 0.3), ('YP_Cabin', 860, 1330, -0.4), ('YP_Cabin', 1040, 1460, 1.2),
             ('YP_Cabin', 560, 1250, 2.0), ('YP_Cabin', 1400, 4780, 0.2),
             ('CCHOUSE02D', 3300, 2420, 1.0), ('CCHOUSE02D', 3330, 2610, 1.0), ('HV_Shop01', 3180, 2760, 0.9),
             ('CCHOUSE02D', 3420, 2150, 2.6), ('YP_Cabin', 4300, 2350, 1.6), ('YP_Cabin', 4450, 2150, 0.1)]


def _scenery():
    ground = platprops.Ground(LAYOUT)
    picks = []

    def put(cands, must=False):
        picks.extend(platprops.place(cands, LAYOUT, SITES, OBJECTS, keep=picks, avoid=AVOID, ground=ground,
                                     must=must))
    put(LANDMARKS, must=True)
    put(along([(2620, 2410), (2740, 2520), (2750, 2780)], 'YP_PICNIC01', 90, 0, 3, sides=(1,)))
    # the town on the bluff (the Canadian side): houses facing its streets, lamps and garden trees between
    for k, street in enumerate(TOWN):
        put(along(street, {'CCHOUSE02D': 2, 'HV_Shop01': 3, 'YP_Cabin': 3}, 165, 150, 70 + k, face=True))
        put(along(street, 'TH_LAMPPOST04', 140, 70, 75 + k))
        put(along(street, ['HB_Tree03', 'CC_Tree03', 'CC_BUSH02'], 70, 92, 80 + k))
    # lamps along the main roads to the bridges, fences along the country roads
    for k, rd in enumerate(LAYOUT.roads[:2] + LAYOUT.roads[6:8]):
        put(along(rd.points, 'TH_LAMPPOST04', 150, rd.width / 2 + 25, 10 + k))      # clear of it: half + 10 + 4 + 8
    for k, rd in enumerate([LAYOUT.roads[4], LAYOUT.roads[8], LAYOUT.roads[9]]):
        put(along(rd.points, ['CC_WOODFENCE01', 'CC_WOODFENCE02'], 34, rd.width / 2 + 40, 20 + k, face=True,
                  jitter=0.0))
    # woods in stands: the ridges and hills mostly wooded, the low ground here and there, Goat Island all over
    for k, region in enumerate((WEST_RIDGE, NW_PEAK, SW_HILLS, SE_BLUFF, EAST_RIDGE, NE_HILL)):
        put(scatter(area('poly', region), WOODS, 52, 30 + k, density=0.85, patches=0.42))
    put(scatter(area('poly', GOAT_SHORE), WOODS, 46, 40))
    put(scatter(area('poly', PLATEAU_EDGE), WOODS, 60, 41, density=0.8, patches=0.55))
    put(scatter(area('rect', (0, 0, 5000, 5000)), WOODS, 58, 42, density=0.8, patches=0.6))
    put(shore(ground, {**WOODS, 'CC_BUSH02': 4, 'YU_SMALLROCKS01': 3}, 60, 60))
    put(cliff_feet(ground, ROCKS, 85, 61))
    put(clumps(area('rect', (0, 0, 5000, 5000)), 40, 60, 3, {'YP_LOG01': 1, 'YP_LOG02': 1, 'YU_LARGEROCKS02': 1}, 62))
    put(scatter(area('rect', (0, 0, 5000, 5000)), UNDER, 100, 63, density=0.4, patches=0.35))
    put(scatter(area('rect', (0, 0, 5000, 5000)), WOODS, 300, 64, density=0.5))
    return [Obj(t, round(x, 1), round(y, 1), side='civ', angle=round(a, 3), site='map') for t, x, y, a in picks]


SCENERY = _scenery()


def terrain(m):
    """CampNew18's generate (objects, scripts, light, the start) with the platform terrain over its island."""
    c18.generate(m)
    previews, _ = platmap.apply(m, LAYOUT)
    c18.PREVIEWS.update(previews)


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
