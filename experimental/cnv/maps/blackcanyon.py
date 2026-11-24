"""A2 坝上风云 (r5 draft, moved in 11-24): the dam across Black Canyon, four ways meeting at it, each over other
ground -- US-93 down the east bank, the bypass bridge from the Soviet camp, the river up to the powerhouse at river
level, a landing on Lake Mead behind the camp. Design intent and the r1-r6 record: work/mappage/a2/notes.md.

Drawn with experimental/mappage/sketch2map.py (work/mappage/a2/design.py -> sketch.json), then moved into maps/
(ADR 0017): this module is the source now, not the sketch -- edit it here. Bench readings: checks/blackcanyon.py.

Published: SITES, PLAYERS, TEAMS, BORDERS, OBJECTS, SCENERY, LAYOUT, FIELDS, DERRICKS, BRIDGES, START, POWERHOUSE
(the low section's building, named for scripts).
"""
import struct

import make_campnew18 as c18
import platmap
import resources
from platmap import Block, Gap, Ground, Layout, Ramp, Road, Shape
from maps import island
from parts import Obj, Site

START = (1550, 2350)
POWERHOUSE = 'A2 Powerhouse'

SITES = {
    'start': Site(*START, 300, 'the player camp on the west plateau', build=500),
    'st_dam_w': Site(2660, 3085, 120, 'crest section west'),
    'st_dam_e': Site(2900, 3085, 120, 'crest section east'),
    'st_foot': Site(2640, 2930, 80, 'the powerhouse at river level: the low section, boats can hit it'),
    'st_bridge': Site(2420, 1700, 120, 'the bridge choke: gas station and motel to garrison'),
    'st_bend': Site(3900, 2480, 200, 'the open bench: where the Falcons kite the heavy tanks'),
    'st_beach': Site(900, 4050, 180, 'the landing beach behind the camp, Boulder City above it'),
    'overlook': Site(3330, 2800, 140, 'the V4 perch: from here rockets reach the crest'),
    'sov_camp': Site(4350, 900, 300, 'the bypass-bridge construction yard the raiders took'),
    'sov_east': Site(4900, 2420, 100, 'reinforcements down US-93'),
    'sov_lake': Site(2900, 4900, 100, 'boats and amphibians from the north end of the lake'),
    'sov_river': Site(3020, 80, 100, 'boats up the river'),
    'fx_station': Site(4680, 4450, 260, 'the Future Tech broadcast station dressed as a Soviet base: destroy it and the map is revealed'),
    'village': Site(1050, 3450, 400, "the dam builders' town between the camp and the beach"),
}
FIELDS = [
    resources.Field('camp', 1150, 2350, 225, 1, base='start', owner='p1', build=200),
    resources.Field('rim', 1700, 1350, 315, 0, base='', owner='', build=200),
    resources.Field('mesa', 4750, 2780, 315, 0, base='', owner='', build=200),
]
DERRICKS = []
SITES.update(resources.sites(FIELDS))
BORDERS = {
    'whole': (0, 0, 5000, 5000),
}
PLAYERS = island.PLAYERS
TEAMS = dict(island.TEAMS, s1='Soviet_1/teamSoviet_1')

RAW_OBJECTS = [
    Obj('SA_TownHall01', 720, 3860, side='neutral', angle=0, flags=0),
    Obj('SA_Store02', 553, 3438, side='neutral', angle=2.62, flags=0),
    Obj('SA_House02_03', 92, 3504, side='neutral', angle=1.95, flags=0),
    Obj('SA_House04', 455, 3377, side='neutral', angle=-0.74, flags=0),
    Obj('SA_House04', 300, 3207, side='neutral', angle=2.4, flags=0),
    Obj('CapeCod_House01', 591, 3299, side='neutral', angle=-0.29, flags=0),
    Obj('CapeCod_House01', 652, 3044, side='neutral', angle=3.08, flags=0),
    Obj('SA_House03', 886, 3050, side='neutral', angle=3.3, flags=0),
    Obj('SA_House01', 924, 3297, side='neutral', angle=0.39, flags=0),
    Obj('SA_House02', 1012, 3084, side='neutral', angle=3.53, flags=0),
    Obj('SA_House03', 1216, 3202, side='neutral', angle=3.76, flags=0),
    Obj('SA_House02_03', 1417, 3150, side='neutral', angle=2.53, flags=0),
    Obj('SA_House02', 875, 2868, side='neutral', angle=-1.57, flags=0),
    Obj('SA_House02', 645, 2868, side='neutral', angle=1.57, flags=0),
    Obj('CapeCod_House01', 189, 3210, side='neutral', angle=-2.53, flags=0),
    Obj('SA_House04', 57, 3398, side='neutral', angle=0.61, flags=0),
    Obj('SA_House03', 103, 3150, side='neutral', angle=-2.53, flags=0),
    Obj('SA_House04', -29, 3338, side='neutral', angle=0.61, flags=0),
    Obj('SA_8BallStation', 2390, 1540, side='neutral', angle=0, flags=0),
    Obj('SA_Store02', 2200, 1560, side='neutral', angle=0, flags=0),
    Obj('SA_Cafe01', 2150, 1830, side='neutral', angle=0, flags=0),
    Obj('SA_Store01', 2400, 1890, side='neutral', angle=0, flags=0),
    Obj('SA_Clubhouse01', 2050, 3020, side='neutral', angle=0, flags=0),
    Obj('SA_8BallStation', 4180, 2200, side='neutral', angle=0, flags=0),
    Obj('SA_Store01', 4330, 2220, side='neutral', angle=0, flags=0),
    Obj('CCGara04', 4650, 1650, side='neutral', angle=1.5707963267948966, flags=0),
    Obj('SA_House01', 3700, 1200, side='neutral', angle=1.5707963267948966, flags=0),
    Obj('OD_Warehouse02', 3550, 1050, side='neutral', angle=1.5707963267948966, flags=0),
    Obj('SA_House04', 4600, 3250, side='neutral', angle=0, flags=0),
    Obj('TH_LAMPPOST04', 3500, 3200, side='neutral', angle=0, flags=0),
    Obj('TH_LAMPPOST04', 4150, 3200, side='neutral', angle=0, flags=0),
    Obj('TH_LAMPPOST04', 4400, 3420, side='neutral', angle=0, flags=0),
    Obj('TH_LAMPPOST04', 4720, 3800, side='neutral', angle=0, flags=0),
    Obj('TH_LAMPPOST04', 4540, 4250, side='neutral', angle=0, flags=0),
    Obj('SA_House02', 4780, 3620, side='neutral', angle=1.5707963267948966, flags=0),
    Obj('SA_House01', 4880, 3480, side='neutral', angle=1.5707963267948966, flags=0),
    Obj('CCGara04', 4850, 3760, side='neutral', angle=0, flags=0),
    Obj('SA_TireShop', 4870, 4100, side='neutral', angle=1.5707963267948966, flags=0),
    Obj('OD_Warehouse02', 1350, 1050, side='neutral', angle=0, flags=0),
    Obj('OD_Warehouse02', 950, 1000, side='neutral', angle=0, flags=0),
    Obj('SA_TireShop', 1450, 1300, side='neutral', angle=0, flags=0),
    Obj('CC_Lighthouse01', 2600, 3250, side='neutral', angle=0, flags=0),
    Obj('CC_Lighthouse01', 2700, 3270, side='neutral', angle=0, flags=0),
    Obj('CC_Lighthouse01', 2840, 3270, side='neutral', angle=0, flags=0),
    Obj('CC_Lighthouse01', 2940, 3250, side='neutral', angle=0, flags=0),
    Obj('OD_Warehouse01', 2650, 2930, side='p1', name=POWERHOUSE, angle=0, flags=0),   # the player's: a neutral prop is no one's target (bench r7)
    Obj('OD_Warehouse02', 4200, 780, side='neutral', angle=0, flags=0),
    Obj('OD_Warehouse02', 4450, 1050, side='neutral', angle=0, flags=0),
    Obj('OD_Warehouse02', 4550, 800, side='neutral', angle=0, flags=0),
    Obj('SovietBarracks', 4250, 1000, side='s1', name='sov_camp', angle=0, flags=0),
    Obj('SovietWarFactory', 4480, 920, side='s1', name='sov_camp', angle=0, flags=0),
    Obj('SovietPowerPlant', 4600, 4380, side='s1', name='fx_station', angle=0, flags=0),
    Obj('SovietBarracks', 4750, 4520, side='s1', name='fx_station', angle=0, flags=0),
]
# bridges bank to bank (platmap.bridge: a start object and its end, one right after the other)
BRIDGES = [
    ((2540, 1700), (3230, 1700), 'HB_Bridge_02'),
]
BRIDGE_OBJECTS = [Obj(t, x, y, side='neutral', angle=a, flags=f, site='map')
                  for p, q, t in BRIDGES for x, y, a, f in platmap.bridge(p, q, t)]
OBJECTS = RAW_OBJECTS + BRIDGE_OBJECTS + resources.objects(FIELDS, DERRICKS)

SHAPES = [
    Shape('poly', ((1600, 3240), (2560, 3150), (3000, 3150), (3600, 3330), (4100, 3480), (4380, 3760), (4330, 4200), (4240, 4600), (4150, 5060), (1250, 5060), (1050, 4550), (1150, 4000), (1350, 3600)), 0, 'Lake Mead: the lake behind the dam; boats and the landing come from its north end'),
    Shape('poly', ((2910, 3048), (2929, 2686), (2830, 2308), (2976, 1932), (3030, 1489), (2910, 1100), (3027, 629), (3177, -31), (2923, -89), (2773, 571), (2650, 1100), (2770, 1511), (2724, 1868), (2570, 2292), (2671, 2714), (2650, 3032)), 0, 'the Colorado in Black Canyon: the river way up to the powerhouse'),
    Shape('rect', (2560, 2840, 3000, 3030), 0, 'the tailrace pool at the dam foot'),
    Shape('rect', (2560, 3020, 3000, 3150), 2, 'the dam crest: the two crest sections, cliff on both faces'),
    Shape('rect', (2500, 2800, 2780, 3015), 1, 'the powerhouse ledge at river level: the third section, the low one'),
    Shape('circle', (2600, 3250, 70), 2, "an intake tower's footing"),
    Shape('circle', (2700, 3270, 70), 2, "an intake tower's footing"),
    Shape('circle', (2840, 3270, 70), 2, "an intake tower's footing"),
    Shape('circle', (2940, 3250, 70), 2, "an intake tower's footing"),
    Shape('circle', (3330, 2800, 140), 3, 'Arizona overlook: the V4 perch above the dam'),
    Shape('poly', ((3637.888543819998, 3095.777087639997), (3777.888543819998, 3025.777087639997), (3742.111456180002, 2954.222912360003), (3602.111456180002, 3024.222912360003)), 3, 'east north ridge (run 1)'),
    Shape('poly', ((3761.052267283529, 3029.986156774114), (3951.052267283529, 3024.986156774114), (3948.947732716471, 2945.013843225886), (3758.947732716471, 2950.013843225886)), 3, 'east north ridge (run 1)'),
    Shape('circle', (3620, 3060, 40), 3, 'east north ridge (run 1)'),
    Shape('circle', (3760, 2990, 40), 3, 'east north ridge (run 1)'),
    Shape('circle', (3950, 2985, 40), 3, 'east north ridge (run 1)'),
    Shape('poly', ((4339.601061062085, 3013.6246303408266), (4469.601061062085, 3048.6246303408266), (4490.398938937915, 2971.3753696591734), (4360.398938937915, 2936.3753696591734)), 3, 'east north ridge (run 2)'),
    Shape('poly', ((4486.575959492215, 3049.455756953286), (4606.575959492215, 3029.455756953286), (4593.424040507785, 2950.544243046714), (4473.424040507785, 2970.544243046714)), 3, 'east north ridge (run 2)'),
    Shape('poly', ((4582.111456180001, 3025.777087639997), (4682.111456180001, 3075.777087639997), (4717.888543819999, 3004.222912360003), (4617.888543819999, 2954.222912360003)), 3, 'east north ridge (run 2)'),
    Shape('circle', (4350, 2975, 40), 3, 'east north ridge (run 2)'),
    Shape('circle', (4480, 3010, 40), 3, 'east north ridge (run 2)'),
    Shape('circle', (4600, 2990, 40), 3, 'east north ridge (run 2)'),
    Shape('circle', (4700, 3040, 40), 3, 'east north ridge (run 2)'),
    Shape('poly', ((3306, 1932), (3426, 2022), (3474, 1958), (3354, 1868)), 3, 'east south ridge (run 1)'),
    Shape('poly', ((3444.713451196359, 2029.6491160273054), (3594.713451196359, 2049.6491160273054), (3605.286548803641, 1970.3508839726946), (3455.286548803641, 1950.3508839726946)), 3, 'east south ridge (run 1)'),
    Shape('circle', (3330, 1900, 40), 3, 'east south ridge (run 1)'),
    Shape('circle', (3450, 1990, 40), 3, 'east south ridge (run 1)'),
    Shape('circle', (3600, 2010, 40), 3, 'east south ridge (run 1)'),
    Shape('poly', ((4014.855627054164, 2077.1390676354104), (4164.855627054164, 2017.1390676354104), (4135.144372945836, 1942.8609323645896), (3985.144372945836, 2002.8609323645896)), 3, 'east south ridge (run 2)'),
    Shape('poly', ((4151.175962064076, 2019.982710178574), (4321.175962064076, 2014.982710178574), (4318.824037935924, 1935.017289821426), (4148.824037935924, 1940.017289821426)), 3, 'east south ridge (run 2)'),
    Shape('circle', (4000, 2040, 40), 3, 'east south ridge (run 2)'),
    Shape('circle', (4150, 1980, 40), 3, 'east south ridge (run 2)'),
    Shape('circle', (4320, 1975, 40), 3, 'east south ridge (run 2)'),
    Shape('poly', ((4705.640836827645, 1977.3338242481225), (4835.640836827645, 2027.3338242481225), (4864.359163172355, 1952.6661757518775), (4734.359163172355, 1902.6661757518775)), 3, 'east south ridge (run 3)'),
    Shape('poly', ((4857.844645405527, 2029.2232270276368), (5007.844645405527, 1999.2232270276368), (4992.155354594473, 1920.7767729723632), (4842.155354594473, 1950.7767729723632)), 3, 'east south ridge (run 3)'),
    Shape('circle', (4720, 1940, 40), 3, 'east south ridge (run 3)'),
    Shape('circle', (4850, 1990, 40), 3, 'east south ridge (run 3)'),
    Shape('circle', (5000, 1960, 40), 3, 'east south ridge (run 3)'),
    Shape('poly', ((236.8591750023491, 1857.7798718682463), (466.8591750023491, 1937.7798718682463), (493.1408249976509, 1862.2201281317537), (263.1408249976509, 1782.2201281317537)), 3, 'west south ridge (run 1)'),
    Shape('poly', ((481.816306436746, 1939.958741608412), (701.816306436746, 1929.958741608412), (698.183693563254, 1850.041258391588), (478.183693563254, 1860.041258391588)), 3, 'west south ridge (run 1)'),
    Shape('poly', ((683.9672466392117, 1926.6462933960875), (843.9672466392117, 1996.6462933960875), (876.0327533607883, 1923.3537066039125), (716.0327533607883, 1853.3537066039125)), 3, 'west south ridge (run 1)'),
    Shape('circle', (250, 1820, 40), 3, 'west south ridge (run 1)'),
    Shape('circle', (480, 1900, 40), 3, 'west south ridge (run 1)'),
    Shape('circle', (700, 1890, 40), 3, 'west south ridge (run 1)'),
    Shape('circle', (860, 1960, 40), 3, 'west south ridge (run 1)'),
    Shape('poly', ((1307.8446454055274, 2029.2232270276368), (1507.8446454055274, 1989.2232270276368), (1492.1553545944726, 1910.7767729723632), (1292.1553545944726, 1950.7767729723632)), 3, 'west south ridge (run 2)'),
    Shape('poly', ((1487.8089709158487, 1988.096965887973), (1737.8089709158487, 2068.096965887973), (1762.1910290841513, 1991.903034112027), (1512.1910290841513, 1911.903034112027)), 3, 'west south ridge (run 2)'),
    Shape('poly', ((1753.98014876084, 2069.8014876083994), (1953.98014876084, 2049.8014876083994), (1946.01985123916, 1970.1985123916004), (1746.01985123916, 1990.1985123916004)), 3, 'west south ridge (run 2)'),
    Shape('poly', ((1935.1443729458358, 2047.1390676354104), (2085.144372945836, 2107.1390676354104), (2114.855627054164, 2032.8609323645896), (1964.8556270541642, 1972.8609323645896)), 3, 'west south ridge (run 2)'),
    Shape('circle', (1300, 1990, 40), 3, 'west south ridge (run 2)'),
    Shape('circle', (1500, 1950, 40), 3, 'west south ridge (run 2)'),
    Shape('circle', (1750, 2030, 40), 3, 'west south ridge (run 2)'),
    Shape('circle', (1950, 2010, 40), 3, 'west south ridge (run 2)'),
    Shape('circle', (2100, 2070, 40), 3, 'west south ridge (run 2)'),
]
RAMPS = [
    Ramp((2560, 2880), (2380, 2840), 120, 'the powerhouse catwalk road down the west wall'),
    Ramp((2985, 2910), (2775, 2910), 110, 'the boat slip: amphibians climb onto the ledge'),
    Ramp((1260, 4100), (860, 4100), 300, 'Boulder Beach: the lake landing behind the camp'),
    Ramp((3640, 2740), (3430, 2790), 120, 'the overlook track (its one way up)'),
    Ramp((4200, 3960), (4640, 3960), 200, 'the station jetty: hovercraft land the raid'),
]
ROADS = [
    Road(((5000, 2400), (4400, 2350), (3800, 2500), (3450, 2550), (3200, 2650), (3060, 2900), (3020, 3085)), 140, 'Pavement_Heidel02'),
    Road(((2560, 3085), (2300, 3050), (1900, 2700), (1550, 2350)), 140, 'Pavement_Heidel02'),
    Road(((3230, 1700), (3600, 1500), (4100, 1150), (4350, 900)), 120, 'Pavement_Heidel02'),
    Road(((2540, 1700), (2300, 1720), (2200, 2100), (2350, 2500), (2420, 2860)), 120, 'Pavement_Heidel02'),
    Road(((2300, 1720), (1700, 1600), (1100, 2000), (1550, 2350)), 100, 'Sand_SantaMonica01'),
    Road(((1550, 2350), (1200, 2900), (1000, 3500), (900, 4050)), 110, 'Pavement_Heidel02'),
    Road(((3020, 3085), (3300, 3060), (3800, 3150), (4150, 3100), (4600, 3500), (4650, 4300)), 100, 'Sand_SantaMonica01'),
    Road(((4350, 900), (4500, 1500), (4600, 2100), (4700, 2430)), 100, 'Sand_SantaMonica01'),
    Road(((760, 3750), (1514, 3222)), 90, 'Pavement_Heidel02'),
    Road(((760, 3750), (760, 2830)), 90, 'Pavement_Heidel02'),
    Road(((760, 3750), (6, 3222)), 90, 'Pavement_Heidel02'),
    Road(((509, 3683), (530, 3628), (564, 3579), (607, 3540), (658, 3511), (715, 3494), (774, 3490), (832, 3500), (886, 3523), (934, 3557), (973, 3601)), 80, 'Pavement_Heidel02'),
    Road(((180, 3595), (230, 3468), (307, 3356), (407, 3265), (526, 3198), (656, 3159), (791, 3151), (925, 3173), (1051, 3225), (1161, 3304), (1251, 3406)), 80, 'Pavement_Heidel02'),
    Road(((1100, 2000), (1150, 1500), (1250, 1150)), 90, 'Sand_SantaMonica01'),
]
GROUNDS = [
    Ground(Shape('rect', (0, 0, 5000, 5000), 0, 'the Mojave floor'), 'Dirt_Yucatan04'),
    Ground(Shape('poly', ((3300, 2150), (3900, 2250), (4600, 2200), (5000, 2100), (5000, 2250), (4500, 2330), (3800, 2380), (3300, 2280)), 0, 'the wash across the open bench'), 'Sand_SantaMonica01'),
    Ground(Shape('poly', ((300, 2300), (900, 2450), (1300, 2650), (1250, 2780), (800, 2600), (250, 2450)), 0, 'the camp wash'), 'Sand_SantaMonica01'),
    Ground(Shape('poly', ((1600, 400), (2200, 700), (2550, 1200), (2450, 1260), (2100, 800), (1550, 520)), 0, 'Hemenway Wash'), 'Sand_SantaMonica01'),
    Ground(Shape('poly', ((3500, 300), (4000, 500), (4700, 400), (4750, 520), (4000, 640), (3450, 420)), 0, 'the south wash'), 'Sand_SantaMonica01'),
    Ground(Shape('poly', ((500, 4300), (1000, 4250), (1100, 4500), (600, 4700)), 0, 'the beach dunes'), 'Sand_SantaMonica01'),
    Ground(Shape('poly', ((1204, 3450), (1118, 3580), (1061, 3706), (983, 3765), (831, 3839), (694, 3868), (559, 3772), (494, 3715), (427, 3581), (327, 3450), (436, 3339), (466, 3198), (538, 3080), (690, 2978), (822, 3034), (945, 3106), (1117, 3248), (1096, 3312)), 0, 'Boulder City: the watered lawns of the government town (ragged edge, map-design 4)'), 'Grass_Heidelberg02'),
]
BLOCKS = []
GAPS = []
# hand strokes (raise / lower / flatten, platmap.brush), laid on the ground the shapes and ramps make
BRUSHES = []
LAYOUT = Layout(shapes=SHAPES, ramps=RAMPS, roads=ROADS, base=2, cliff=2, blocks=BLOCKS, gaps=GAPS, brushes=BRUSHES, grounds=GROUNDS)

# the look: retail objects placed as they are (a new map has none yet: the level line adds platprops)
SCENERY = [
    Obj('CC_BUSH02', 4104, 1744, side='neutral', angle=0.21, flags=0),
    Obj('YU_LARGEROCKS02', 3859, 1799, side='neutral', angle=1.96, flags=0),
    Obj('CC_BUSH02', 4131, 1755, side='neutral', angle=0.24, flags=0),
    Obj('OK_Shrub01', 3824, 1749, side='neutral', angle=2.57, flags=0),
    Obj('OK_Shrub01', 3813, 1655, side='neutral', angle=3.62, flags=0),
    Obj('YU_SMALLROCKS02', 3936, 1643, side='neutral', angle=5.27, flags=0),
    Obj('YU_LARGEROCKS02', 3878, 1778, side='neutral', angle=1.85, flags=0),
    Obj('YU_LARGEROCKS02', 3946, 1553, side='neutral', angle=5.02, flags=0),
    Obj('YU_LARGEROCKS02', 4088, 1582, side='neutral', angle=5.72, flags=0),
    Obj('YU_LARGEROCKS02', 4560, 2714, side='neutral', angle=2.8, flags=0),
    Obj('OK_Shrub04', 4613, 2557, side='neutral', angle=4.81, flags=0),
    Obj('YU_SMALLROCKS02', 4431, 2704, side='neutral', angle=3.12, flags=0),
    Obj('OK_Shrub01', 4514, 2497, side='neutral', angle=4.31, flags=0),
    Obj('CC_BUSH02', 4541, 2621, side='neutral', angle=4.07, flags=0),
    Obj('YU_SMALLROCKS01', 4110, 2985, side='neutral', angle=4.77, flags=0),
    Obj('YU_SMALLROCKS02', 599, 2607, side='neutral', angle=1.78, flags=0),
    Obj('YU_SMALLROCKS01', 508, 2499, side='neutral', angle=3.97, flags=0),
    Obj('OK_Shrub04', 564, 2641, side='neutral', angle=2.29, flags=0),
    Obj('YU_SMALLROCKS02', 586, 2611, side='neutral', angle=2.47, flags=0),
    Obj('YU_SMALLROCKS02', 391, 2676, side='neutral', angle=2.79, flags=0),
    Obj('OK_Shrub01', 710, 2572, side='neutral', angle=6.04, flags=0),
    Obj('OK_Shrub04', 602, 2626, side='neutral', angle=1.49, flags=0),
    Obj('YU_SMALLROCKS02', 782, 2635, side='neutral', angle=0.19, flags=0),
    Obj('YU_SMALLROCKS02', 1864, 1501, side='neutral', angle=1.75, flags=0),
    Obj('YU_LARGEROCKS02', 2003, 1353, side='neutral', angle=0.48, flags=0),
    Obj('OK_Shrub01', 1903, 1485, side='neutral', angle=1.55, flags=0),
    Obj('YU_SMALLROCKS01', 1983, 1399, side='neutral', angle=0.88, flags=0),
    Obj('YU_LARGEROCKS02', 2026, 1387, side='neutral', angle=0.6, flags=0),
    Obj('YU_SMALLROCKS02', 1919, 1438, side='neutral', angle=1.44, flags=0),
    Obj('YU_SMALLROCKS02', 1946, 1390, side='neutral', angle=1.1, flags=0),
    Obj('OK_Shrub04', 2129, 1245, side='neutral', angle=6.05, flags=0),
    Obj('YU_SMALLROCKS02', 2020, 1349, side='neutral', angle=0.39, flags=0),
    Obj('YU_LARGEROCKS02', 739, 1197, side='neutral', angle=6.19, flags=0),
    Obj('OK_Shrub04', 711, 1213, side='neutral', angle=0.87, flags=0),
    Obj('CC_BUSH02', 554, 1173, side='neutral', angle=3.32, flags=0),
    Obj('CC_BUSH02', 795, 1149, side='neutral', angle=5.79, flags=0),
    Obj('OK_Shrub01', 742, 1278, side='neutral', angle=1.08, flags=0),
    Obj('YU_SMALLROCKS01', 678, 1179, side='neutral', angle=3.89, flags=0),
    Obj('YU_SMALLROCKS01', 663, 1256, side='neutral', angle=2.15, flags=0),
    Obj('OK_Shrub01', 682, 1176, side='neutral', angle=4.05, flags=0),
    Obj('YU_SMALLROCKS02', 717, 1252, side='neutral', angle=1.26, flags=0),
    Obj('CC_BUSH02', 589, 1249, side='neutral', angle=2.73, flags=0),
    Obj('CC_BUSH02', 3614, 717, side='neutral', angle=2.58, flags=0),
    Obj('YU_LARGEROCKS02', 3840, 647, side='neutral', angle=0.86, flags=0),
    Obj('OK_Shrub01', 3806, 623, side='neutral', angle=1.3, flags=0),
    Obj('YU_SMALLROCKS02', 3807, 566, side='neutral', angle=4.92, flags=0),
    Obj('YU_SMALLROCKS01', 3764, 392, side='neutral', angle=4.54, flags=0),
    Obj('YU_SMALLROCKS01', 4025, 565, side='neutral', angle=6.13, flags=0),
    Obj('YU_LARGEROCKS02', 3709, 522, side='neutral', angle=3.85, flags=0),
    Obj('YU_SMALLROCKS02', 3800, 577, side='neutral', angle=4.71, flags=0),
    Obj('CC_BUSH02', 387, 4107, side='neutral', angle=0.89, flags=0),
    Obj('CC_BUSH02', 480, 3844, side='neutral', angle=5.57, flags=0),
    Obj('YU_LARGEROCKS02', 480, 3841, side='neutral', angle=5.56, flags=0),
    Obj('OK_Shrub01', 230, 3875, side='neutral', angle=4.2, flags=0),
    Obj('OK_Shrub04', 402, 4187, side='neutral', angle=1.07, flags=0),
    Obj('CC_BUSH02', 310, 3940, side='neutral', angle=4.88, flags=0),
    Obj('YU_SMALLROCKS02', 224, 4097, side='neutral', angle=2.23, flags=0),
    Obj('OK_Shrub01', 509, 4353, side='neutral', angle=3.62, flags=0),
    Obj('OK_Shrub01', 673, 4390, side='neutral', angle=6.15, flags=0),
    Obj('YU_SMALLROCKS02', 689, 4385, side='neutral', angle=6.12, flags=0),
    Obj('CC_BUSH02', 676, 4481, side='neutral', angle=0.82, flags=0),
    Obj('OK_Shrub04', 517, 4564, side='neutral', angle=2.04, flags=0),
    Obj('OK_Shrub04', 771, 4428, side='neutral', angle=0.16, flags=0),
    Obj('OK_Shrub01', 4626, 1366, side='neutral', angle=3.97, flags=0),
    Obj('OK_Shrub04', 4795, 1446, side='neutral', angle=5.41, flags=0),
    Obj('YU_LARGEROCKS02', 4819, 1432, side='neutral', angle=5.51, flags=0),
    Obj('YU_SMALLROCKS01', 4977, 1577, side='neutral', angle=0.33, flags=0),
    Obj('OK_Shrub01', 4902, 1657, side='neutral', angle=0.8, flags=0),
    Obj('YU_LARGEROCKS02', 4777, 1458, side='neutral', angle=5.29, flags=0),
    Obj('OK_Shrub01', 4834, 1498, side='neutral', angle=6.25, flags=0),
    Obj('YU_SMALLROCKS01', 4826, 1486, side='neutral', angle=6.11, flags=0),
    Obj('YU_LARGEROCKS02', 1545, 735, side='neutral', angle=0.66, flags=0),
    Obj('YU_LARGEROCKS02', 1486, 917, side='neutral', angle=1.63, flags=0),
    Obj('YU_SMALLROCKS01', 1399, 483, side='neutral', angle=4.28, flags=0),
    Obj('YU_LARGEROCKS02', 1445, 880, side='neutral', angle=1.87, flags=0),
    Obj('CC_BUSH02', 1480, 702, side='neutral', angle=3.05, flags=0),
    Obj('CC_BUSH02', 1521, 877, side='neutral', angle=1.45, flags=0),
    Obj('YU_SMALLROCKS01', 1528, 607, side='neutral', angle=5.01, flags=0),
    Obj('YU_SMALLROCKS02', 1429, 626, side='neutral', angle=3.95, flags=0),
    Obj('OK_Shrub01', 2145, 2398, side='neutral', angle=3.54, flags=0),
    Obj('YU_LARGEROCKS02', 2115, 2480, side='neutral', angle=1.98, flags=0),
    Obj('YU_LARGEROCKS02', 2012, 2547, side='neutral', angle=2.33, flags=0),
    Obj('YU_LARGEROCKS02', 2194, 2435, side='neutral', angle=0.67, flags=0),
    Obj('YU_LARGEROCKS02', 2092, 2515, side='neutral', angle=2.04, flags=0),
    Obj('YU_SMALLROCKS02', 3642, 2335, side='neutral', angle=6.12, flags=0),
    Obj('YU_SMALLROCKS01', 3638, 2380, side='neutral', angle=0.33, flags=0),
    Obj('CC_BUSH02', 3462, 2413, side='neutral', angle=2.52, flags=0),
    Obj('OK_Shrub01', 3363, 2211, side='neutral', angle=3.78, flags=0),
    Obj('YU_SMALLROCKS02', 3578, 2335, side='neutral', angle=5.79, flags=0),
    Obj('OK_Shrub04', 3325, 2398, side='neutral', angle=2.93, flags=0),
    Obj('OK_Shrub01', 3568, 2385, side='neutral', angle=1.09, flags=0),
    Obj('OK_Shrub04', 3533, 2327, side='neutral', angle=4.09, flags=0),
    Obj('YU_LARGEROCKS02', 4268, 2664, side='neutral', angle=2.73, flags=0),
    Obj('YU_SMALLROCKS02', 4187, 2717, side='neutral', angle=2.61, flags=0),
    Obj('OK_Shrub04', 4464, 2724, side='neutral', angle=0.42, flags=0),
    Obj('OK_Shrub01', 4291, 2649, side='neutral', angle=3.27, flags=0),
    Obj('YU_SMALLROCKS01', 4152, 2743, side='neutral', angle=2.58, flags=0),
    Obj('OK_Shrub04', 4370, 2620, side='neutral', angle=5.88, flags=0),
    Obj('YU_SMALLROCKS02', 3446, 1214, side='neutral', angle=5.75, flags=0),
    Obj('YU_LARGEROCKS02', 3426, 1285, side='neutral', angle=6.16, flags=0),
    Obj('YU_SMALLROCKS02', 3367, 1368, side='neutral', angle=0.79, flags=0),
    Obj('YU_LARGEROCKS02', 3178, 1210, side='neutral', angle=3.78, flags=0),
    Obj('OK_Shrub04', 3210, 1492, side='neutral', angle=2.01, flags=0),
    Obj('YU_LARGEROCKS02', 3124, 1359, side='neutral', angle=2.82, flags=0),
    Obj('OK_Shrub01', 3289, 1290, side='neutral', angle=3.86, flags=0),
    Obj('YU_SMALLROCKS02', 3274, 1241, side='neutral', angle=4.3, flags=0),
    Obj('OK_Shrub01', 5012, 4488, side='neutral', angle=5.5, flags=0),
    Obj('OK_Shrub01', 4989, 4827, side='neutral', angle=0.91, flags=0),
    Obj('YU_LARGEROCKS02', 4482, 4782, side='neutral', angle=0.78, flags=0),
    Obj('OK_Shrub01', 4449, 4755, side='neutral', angle=1.84, flags=0),
    Obj('OK_Shrub04', 4342, 4618, side='neutral', angle=4.03, flags=0),
    Obj('OK_Shrub04', 4564, 4785, side='neutral', angle=0.3, flags=0),
    Obj('YU_LARGEROCKS02', 4400, 4884, side='neutral', angle=1.93, flags=0),
    Obj('OK_Shrub04', 4539, 4760, side='neutral', angle=0.11, flags=0),
]


def terrain(m):
    """CampNew18's generate with the platform terrain over its island, and the starts moved to START."""
    import newmap
    c18.generate(m)
    previews, _ = platmap.apply(m, LAYOUT)
    c18.PREVIEWS.update(previews)
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    for k in objs.kids:
        name = newmap.typed_props_of(m, k)[0].get('waypointName', (0, ''))[1]
        if name in ('Player_1_Start', 'InitialCameraPosition', 'Player_2_Start'):
            dx = 60.0 if name == 'Player_2_Start' else 0.0
            k.head = struct.pack('<ff', START[0] + dx, START[1] + dx) + k.head[8:]


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
