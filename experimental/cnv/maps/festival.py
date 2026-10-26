"""札幌雪祭 (A4 / J4, docs/story/outline.md), built the retail way (docs/story/map-language.md, platmap): flat
ground in tiers, narrow cliffs, few ramps, a canal crossed by bridges -- shaped by what the levels need, not by
Sapporo's real streets (snow is art, art last).

  - The festival avenue runs east on the low ground (tier 1) from the convoy's start by the player's base to the
    harbour exit. Three plazas beside it, two north and one south, are raised a tier: cliffs on every side, one ramp
    down to the avenue -- the gate, the only way in or out (it was snow banks around flat ground before).
  - A canal cuts the harbour district off the east end: three bridges (bridge objects, as retail) are the only ground
    way across; the avenue's is the convoy's last stretch before the exit.
  - North and south, a raised plateau each with ramps, ore and an oil derrick: ground worth taking. The player's base
    has its own pair of ore nodes ~550 off, as retail starts do. A ridge behind the base, wooded hills in the
    south-west, a shrine on a knoll (tier 3) over the north plateau: backdrop.
  - The look (retail objects only, platprops): the avenue lined as a park (Odori: trees, lanterns, banners), side
    streets of Japanese houses up to the plateaus' ramps, the harbour's fish markets and cranes on its quay, the
    canal walked along on both banks; woods in stands on the hills, rocks at the cliffs' feet, islets off the coast.

Published: SITES (the island's start, base and field sites, and the festival's), PLAYERS, TEAMS, OBJECTS (the map's
own: ore nodes, tech buildings, bridges -- placed with the terrain, not by a mission), SCENERY (kept off every way
and place, the plazas whole), LAYOUT (the terrain).
"""
import make_campnew18 as c18
import platmap
import platprops
from platmap import Layout, Ramp, Road, circle, poly, rect, wobble
from platprops import along, area, cliff_feet, clumps, scatter, shore
from maps import island
from parts import Obj, Site

ROAD_Y = 2500.0
PLAZA_X = (2300.0, 2900.0, 3500.0)
NORTH = (True, False, True)                     # plaza k north of the road (its gate faces south) or south of it
# across the road from its middle (y): the road's edge, the ramp up (RAMP_WIDTH wide), the plaza's raised ground.
# The gate is the ramp's head, the one gap in the plaza's cliff: a bar 200 long across it closes it for real (placed
# by the map: it may lie over the cliff's edge). Ice built in play needs flat ground under it (bench 2026-10-23: none
# came mid-ramp) and a built wall bars no infantry anyway (A4's rule decides), so that goes just inside: 'inside k'.
RAMP_FOOT, RAMP_LEN, RAMP_WIDTH = 60.0, 180.0, 120.0
PLAZA_FRONT = RAMP_FOOT + RAMP_LEN              # the plaza's front edge (its cliff, the ramp's head)
RAMP_HEAD = PLAZA_FRONT + 30.0                  # the ramp ends on the plaza's flat top, past the cliff's soft edge
GATE_OFF = PLAZA_FRONT + 20.0                   # the gate: across the gap, on the cliff's line
INSIDE_OFF = RAMP_HEAD + 90.0                   # flat ground past the ramp's head: room for a 160 block
DEPTH = 300.0                                   # a plaza's middle from its gate
PLAZA_HALF, PLAZA_BACK = 150.0, 750.0           # its half width; its back edge from the road's middle
CANAL = (3660.0, 3820.0)                        # the canal's west and east banks (x)

SITES = {k: island.SITES[k] for k in ('island', 'start', 'base factory', 'base power', 'west field')}
SITES.update({
    'convoy start': Site(1700.0, ROAD_Y, 100.0, "the road's west end by the player's base: the convoy forms up here"),
    'road exit': Site(3900.0, ROAD_Y, 150.0, "the road's east end in the harbour, past the canal bridge: the convoy "
                                             'is safe here'),
    'north camp': Site(2900.0, 3250.0, 200.0, 'open low ground north of the plazas, off the road: a force that comes '
                                               'round to the gates (J4)'),
    'base yard': Site(1250.0, 2500.0, 0.0, "the construction yard's pad on the player's start", build=200.0),
    'base barracks': Site(1250.0, 2780.0, 0.0, "a barracks' pad north of the yard", build=160.0),
    'base refinery': Site(1150.0, 2150.0, 0.0, "a refinery's pad by the player's own ore", build=200.0),
    'harbour': Site(4030.0, 2500.0, 180.0, 'the harbour ground at the east end of the canal bridge: the convoy '
                                           'crosses it to the exit'),
    'north base': Site(3050.0, 4100.0, 250.0, 'the north plateau past its ore: room for a small camp', build=160.0),
    'halt': Site(2860.0, 2500.0, 40.0, "the road at plaza 2's gate: a convoy stopped here is past plaza 2 and short "
                                       "of plaza 3's approach (from 3000)"),
})
# MAP_SWITCH_BORDER(k) makes the k-th the playable area (world units, x0 y0 x1 y1; the first is the whole map)
BORDERS = {'whole': (0.0, 0.0, 5000.0, 5000.0), 'west of the canal': (0.0, 0.0, CANAL[0] - 20.0, 5000.0)}
for k, (x, north) in enumerate(zip(PLAZA_X, NORTH), 1):
    s = 1 if north else -1
    side = 'north' if north else 'south'
    SITES[f'gate {k}'] = Site(x, ROAD_Y + s * GATE_OFF, 0.0, f"plaza {k}'s gate: the head of its ramp down to the "
                                                                f'road ({side} of it, {GATE_OFF:g} off), the one gap '
                                                                f'in its cliff ({RAMP_WIDTH:g} wide); a bar 200 long '
                                                                'placed across it closes it')
    SITES[f'inside {k}'] = Site(x, ROAD_Y + s * INSIDE_OFF, 0.0, f'flat ground just inside plaza {k}\'s gate: a '
                                                                    'building up to 160 across fits', build=160.0)
    SITES[f'plaza {k}'] = Site(x, ROAD_Y + s * (GATE_OFF + DEPTH), 120.0, f'plaza {k}, raised {side} of the road: '
                                                                           'its sculptures stand here')
    SITES[f'approach {k}'] = Site(x - 350.0, ROAD_Y, 150.0, f'the road west of plaza {k}: a convoy here is '
                                                            'about to pass it')
PLAYERS = island.PLAYERS
TEAMS = dict(island.TEAMS, s1='Soviet_1/teamSoviet_1')


CHAMFER = 45.0                                  # a plaza's corners cut off (its front's middle, the gate, stays)


def _plazas():
    shapes, ramps, roads, footprints = [], [], [], []
    for k, (x, north) in enumerate(zip(PLAZA_X, NORTH), 1):
        s = 1 if north else -1
        y0, y1 = sorted((ROAD_Y + s * PLAZA_FRONT, ROAD_Y + s * PLAZA_BACK))
        x0, x1, c = x - PLAZA_HALF, x + PLAZA_HALF, CHAMFER
        shapes.append(poly([(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1),
                            (x0, y1 - c), (x0, y0 + c)], 2, f'plaza {k}'))
        ramps.append(Ramp((x, ROAD_Y + s * RAMP_FOOT), (x, ROAD_Y + s * RAMP_HEAD), RAMP_WIDTH, f'gate {k}'))
        roads.append(Road(((x, ROAD_Y), (x, ROAD_Y + s * (PLAZA_FRONT + 20))), RAMP_WIDTH - 30))
        footprints.append(((x, y0), (x, y1), 2 * PLAZA_HALF + 20))
    return shapes, ramps, roads, footprints


_ps, _pr, _proads, PLAZA_FOOTPRINTS = _plazas()
# the coast: rocky and bent to the west, north and south, a straight quay along the harbour (east of the canal)
COAST = (wobble([(4150, 600), (3100, 430), (2000, 520), (900, 420), (250, 600), (260, 2000), (420, 2900),
                 (300, 3800), (600, 4600), (1800, 4500), (3000, 4620), (4100, 4550)], 110.0, 51, closed=False) +
         wobble([(4100, 4550), (4300, 3700), (4180, 2900), (4150, 2300), (4250, 1600), (4150, 600)], 12.0, 52,
                closed=False))
NORTH_PLATEAU = wobble([(2000, 3560), (2650, 3550), (3150, 3550), (3450, 3580), (3530, 3900), (3430, 4300),
                        (3000, 4420), (2500, 4390), (2050, 4310), (1940, 3900)], 60.0, 53,
                       keep=[(2650, 3550, 160.0), (3150, 3550, 160.0)])
KNOLL = wobble([(2080, 4020), (2300, 3990), (2420, 4130), (2350, 4300), (2130, 4300), (2040, 4170)], 30.0, 54)
SOUTH_PLATEAU = wobble([(2000, 1490), (2350, 1500), (2800, 1510), (3400, 1480), (3480, 1100), (3380, 760),
                        (2700, 700), (2050, 760), (1930, 1100)], 60.0, 55, keep=[(2350, 1500, 160.0)])
WEST_RIDGE = wobble([(350, 3200), (1100, 3200), (1150, 3700), (1060, 4300), (600, 4380), (330, 3900)], 70.0, 56,
                    keep=[(1100, 3200, 230.0)])
SW_HILLS = wobble([(330, 700), (1100, 590), (1520, 720), (1470, 1130), (1000, 1260), (480, 1170)], 80.0, 57)
ISLETS = [wobble([(x + r * c, y + r * s) for c, s in ((1, 0), (.7, .7), (0, 1), (-.7, .7), (-1, 0), (-.7, -.7),
                                                     (0, -1), (.7, -.7))], r * 0.3, 60 + k)
          for k, (x, y, r) in enumerate(((150, 250, 170), (4650, 1150, 190), (4700, 4100, 150), (1300, 4950, 160),
                                         (2800, 120, 130)))]
# streets (ground texture only): up to the plateaus' ramps, along the canal's west bank (round plaza 3), the
# harbour's street, the way up the west ridge
STREETS = [((2650, ROAD_Y + 60), (2650, 3330)), ((3150, ROAD_Y + 60), (3150, 3330)),
           ((2350, ROAD_Y - 60), (2350, 1720)), ((3580, 700), (3580, 2440)), ((3580, 3320), (3580, 4300)),
           ((3900, 900), (3900, 4250)), ((1300, 2880), (1300, 3000))]
LAYOUT = Layout(
    shapes=[
        poly(COAST, 1, 'the island: low ground'),
        *[poly(p, 1, 'an islet') for p in ISLETS],
        poly(NORTH_PLATEAU, 2, 'north plateau'),
        poly(KNOLL, 3, 'the shrine knoll'),
        poly(SOUTH_PLATEAU, 2, 'south plateau'),
        poly(WEST_RIDGE, 2, 'west ridge behind the base'),
        poly(SW_HILLS, 2, 'the south-west hills'),
        *_ps,
        rect(CANAL[0], 200, CANAL[1], 4800, 0, 'the canal'),
    ],
    ramps=[
        *_pr,
        Ramp((2650, 3330), (2650, 3700), 200.0, 'north plateau west'),
        Ramp((3150, 3330), (3150, 3700), 200.0, 'north plateau east'),
        Ramp((2350, 1720), (2350, 1350), 200.0, 'south plateau'),
        Ramp((1300, 3000), (1000, 3400), 180.0, 'west ridge'),
    ],
    roads=[Road(((1500, ROAD_Y), (4050, ROAD_Y)), 120.0), *_proads, *[Road(s, 90.0) for s in STREETS]])

BRIDGES = [((3590, 2500), (3890, 2500)), ((3590, 3420), (3890, 3420)), ((3590, 1850), (3890, 1850))]


def _objects():
    out = []
    for p, q in BRIDGES:
        for x, y, a, flags in platmap.bridge(p, q, 'HB_Bridge_02'):
            out.append(Obj('HB_Bridge_02', x, y, side='neutral', angle=a, flags=flags, site='map'))
    ore = [(850, 2050), (1010, 1930),               # the player's own, ~550 from the start
           (2600, 3900), (2790, 3960),              # north plateau
           (2350, 1080), (2540, 1020),              # south plateau
           (4000, 1650), (4000, 1830),              # the harbour, past the canal
           (2450, 2120)]                            # one in the middle, between the plazas
    out += [Obj('OreNode', x, y, side='neutral', angle=0.0, site='map') for x, y in ore]
    for x, y in ((3200, 4050), (700, 1500)):
        out.append(Obj('OilDerrick', x, y, side='neutral', angle=0.0, site='map'))
    out.append(Obj('ObservationPostTechStructure', 3050, 1100, side='neutral', angle=0.0, site='map'))
    return out


OBJECTS = _objects()

WOODS = {'HB_Tree03': 3, 'HB_Tree04': 2, 'HB_Tree05': 2, 'OK_Tree01': 3, 'OK_Tree02': 2, 'TH_Tree01': 1}
PARK = {'OK_Tree01': 3, 'OK_Tree02': 2, 'TH_Tree02': 2, 'HB_TREE09': 1}
UNDER = {'OK_Shrub01': 3, 'OK_Shrub04': 2, 'GC_Bush01': 2, 'HB_GRASS02': 3, 'ST_PLANT09': 2}
ROCKS = {'YU_LARGEROCKS02': 1, 'YU_SMALLROCKS01': 2, 'HA_GardenRock01': 2, 'OK_GARDENROCK03': 1}
HOUSES = {'MJ_Structure_02': 3, 'MJ_Structure_04': 2, 'HA_Building16_02': 3, 'HA_Building16_03': 2,
          'TH_SushiBar_01': 2, 'TH_PHpagoda_04': 1, 'TH_PHpagoda_02': 1}
# kept open: the player's base round the start, the plazas whole (raised ground the level fights over)
AVOID = [(1300.0, 2500.0, 600.0)] + PLAZA_FOOTPRINTS


def _scenery():
    ground = platprops.Ground(LAYOUT)
    picks = []

    def put(cands):
        picks.extend(platprops.place(cands, LAYOUT, SITES, OBJECTS, keep=picks, avoid=AVOID, ground=ground))
    # landmarks by hand: the shrine on its knoll and its torii, a pagoda by the canal, cranes on the harbour quay
    put([('OK_Pagoda01', 2230, 4150, 0.0), ('OK_ARCH01', 2230, 3990, 0.0), ('TH_PHpagoda_01', 3420, 3420, 1.57),
         ('TH_harbor_crane01', 4150, 1300, 0.0), ('TH_harbor_crane01', 4120, 3300, 0.0),
         ('TH_harbor_crane01', 4180, 3900, 0.0)])
    # the avenue as a park: trees in rows outside lanterns and banners, both sides, all the way
    avenue = [(1500, ROAD_Y), (4050, ROAD_Y)]
    put(along(avenue, ['OK_LANTERN01', 'MJ_BANNER01', 'MJ_BANNER02', 'TH_LAMPDECO03'], 70, 85, 1, jitter=0.0))
    put(along(avenue, PARK, 55, 150, 2))
    put(along(avenue, PARK, 70, 205, 3))
    put(along(avenue, ['GE_BENCH', 'TH_PLANTER01'], 160, 105, 4, face=True, jitter=0.0))
    # the side streets: houses facing them, lamps; the canal's banks walked along, the harbour's markets
    for k, street in enumerate(STREETS[:3]):
        put(along(street, HOUSES, 120, 150, 10 + k, face=True))
        put(along(street, 'TH_LAMPPOST04', 120, 62, 20 + k))
    for k, street in enumerate(STREETS[3:5]):
        put(along(street, 'TH_LAMPPOST04', 120, 62, 25 + k, sides=(1,)))
        put(along(street, HOUSES, 120, 150, 27 + k, face=True, sides=(1,)))
    put(along(STREETS[5], {'TH_Fish_Market02': 2, 'TH_Fish_Market03': 2, 'TH_FISH_MARKET04': 2}, 95, 125, 30,
              face=True, sides=(-1,)))
    put(along(STREETS[5], 'TH_LAMPPOST04', 120, 62, 31))
    put(clumps(area('rect', (3950, 700, 4300, 4300)), 14, 40, 6,
               {'TH_JAPANCRATE01': 2, 'TH_JAPANOILDRUM01': 1}, 32))
    put(along([(2560, 1800), (2560, 2280)], 'TH_JAPANFENCE01', 32, 0, 33, sides=(1,), face=True, jitter=0.0))
    # a town round the base side of the avenue, west of plaza 1, both sides of it
    put(scatter(area('rect', (1700, 1700, 2150, 3300)), HOUSES, 140, 34, density=0.8))
    # woods in stands on the hills and the ridge, the plateaus' edges, the coast; rocks at the cliffs' feet
    for k, region in enumerate((WEST_RIDGE, SW_HILLS, KNOLL, *ISLETS)):
        put(scatter(area('poly', region), WOODS, 50, 40 + k, density=0.85, patches=0.4))
    for k, region in enumerate((NORTH_PLATEAU, SOUTH_PLATEAU)):
        put(scatter(area('poly', region), WOODS, 60, 50 + k, density=0.8, patches=0.55))
    put(scatter(area('poly', COAST), WOODS, 60, 52, density=0.75, patches=0.62))
    put(shore(ground, {**WOODS, **ROCKS}, 70, 53))
    put(cliff_feet(ground, ROCKS, 90, 54))
    put(scatter(area('rect', (0, 0, 5000, 5000)), UNDER, 100, 55, density=0.4, patches=0.35))
    return [Obj(t, round(x, 1), round(y, 1), side='civ', angle=round(a, 3), site='map') for t, x, y, a in picks]


SCENERY = _scenery()


def terrain(m):
    """CampNew18's generate (objects, scripts, light, the start) with the platform terrain over its island."""
    c18.generate(m)
    previews, _ = platmap.apply(m, LAYOUT)
    c18.PREVIEWS.update(previews)


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
