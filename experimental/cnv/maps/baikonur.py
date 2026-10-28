"""拜科努尔发射场 (S6 / J7 拜科努尔, docs/story/outline.md), built the retail way (docs/story/map-language.md,
platmap): only like the cosmodrome -- a launch pad on the open steppe, ridges, a dry river valley -- shaped by what
the levels need.

  - The steppe is one low tier. The launch complex stands in the middle on open ground; the Soviet base west of
    it, round the start.
  - East of the complex two long ridges (tier 2) split the way in three valleys -- north, middle, south -- each
    500-700 wide where it meets the complex (its gap): where a jammer parked mid-way slows most of what comes through
    (S6), and what an attacker must get past (J7). Past the ridges, in the east, open ground: the Japanese stage
    there (S6) or the player's strike force starts (J7).
  - Ridges along the north and south edges close the valleys off; hills behind the Soviet base.

Published: SITES, PLAYERS, TEAMS, OBJECTS (ore, a derrick), SCENERY (sparse steppe grass, rocks, a few trees:
platprops, kept off every way and place), LAYOUT, BORDERS.
"""
import make_campnew18 as c18
import platmap
import platprops
from platmap import Layout, Road, poly, wobble
from platprops import area, cliff_feet, scatter
from maps import island
from parts import Obj, Site

PAD = (2500.0, 2500.0)                          # the launch pad
GAP_X = 2950.0                                  # the valleys' gaps toward the complex (x)
LANES = {'north': 3550.0, 'middle': 2500.0, 'south': 1450.0}   # each valley's middle (y)

SITES = {k: island.SITES[k] for k in ('island', 'start', 'base factory', 'base power', 'west field', 'base edge')}
SITES.update({
    'base yard': Site(1250.0, 2500.0, 0.0, "the construction yard's pad on the player's start", build=200.0),
    'base barracks': Site(1250.0, 2800.0, 0.0, "a barracks' pad north of the yard", build=160.0),
    'base refinery': Site(1130.0, 2060.0, 0.0, "a refinery's pad by the base's own ore (~180 from the nearer node)",
                          build=200.0),
    'launch pad': Site(*PAD, 0.0, 'the launch tower on its pad, in the middle of the steppe', build=260.0),
    'launch yard': Site(*PAD, 350.0, 'open ground round the launch pad'),
    'east base': Site(4250.0, 2500.0, 450.0, 'open ground in the east past the ridges: the Japanese stage here'),
    'east barracks': Site(4100.0, 2800.0, 0.0, 'a barracks in the east', build=160.0),
    'east factory': Site(4400.0, 2200.0, 0.0, 'a war factory in the east', build=200.0),
    'east power': Site(4550.0, 2750.0, 0.0, 'a power plant in the east', build=120.0),
    'east refinery': Site(4430.0, 3180.0, 0.0, 'a refinery in the east, by its ore (~180 from the nearer node)',
                          build=200.0),
})
for lane, y in LANES.items():
    SITES[f'{lane} gap'] = Site(GAP_X, y, 150.0, f'the {lane} valley where it meets the complex (500-700 '
                                                 'across): a jammer parked here slows most that comes through')
    SITES[f'{lane} valley'] = Site(3500.0, y, 200.0, f'the {lane} valley halfway, between the ridges')
    SITES[f'{lane} mouth'] = Site(3950.0, y, 200.0, f'the {lane} valley\'s east end, open to the east')
PLAYERS = island.PLAYERS
TEAMS = dict(island.TEAMS, s1='Soviet_1/teamSoviet_1')
BORDERS = {'whole': (0.0, 0.0, 5000.0, 5000.0), 'west of the ridges': (0.0, 0.0, 3000.0, 5000.0)}

# the two ridges between the valleys (east of the gaps), and the edge ridges closing the north and south valleys
RIDGE_N = wobble([(GAP_X + 30, 2850), (3300, 2750), (3800, 2780), (3900, 2900), (3850, 3150), (3400, 3200),
                  (GAP_X + 30, 3200)], 45.0, 81, keep=[(GAP_X, 2850, 80.0), (GAP_X, 3200, 80.0)])
RIDGE_S = wobble([(GAP_X + 30, 1800), (3400, 1800), (3850, 1850), (3900, 2100), (3800, 2220), (3300, 2250),
                  (GAP_X + 30, 2150)], 45.0, 82, keep=[(GAP_X, 1800, 80.0), (GAP_X, 2150, 80.0)])
EDGE_N = wobble([(GAP_X - 200, 3900), (3300, 3950), (3900, 4000), (4400, 4100), (5300, 4200), (5300, 5300),
                 (2200, 5300), (2300, 4400)], 70.0, 83)
EDGE_S = wobble([(GAP_X - 200, 1100), (3300, 1050), (3900, 1000), (4400, 900), (5300, 800), (5300, -300),
                 (2200, -300), (2300, 600)], 70.0, 84)
WEST_HILLS = wobble([(-300, 3300), (400, 3400), (700, 3900), (500, 4500), (-300, 4800)], 80.0, 85)
SW_HILLS = wobble([(-300, 600), (600, 500), (900, 1000), (500, 1500), (-300, 1600)], 80.0, 86)

LAYOUT = Layout(
    shapes=[
        poly([(-300, -300), (5300, -300), (5300, 5300), (-300, 5300)], 1, 'the steppe'),
        poly(RIDGE_N, 2, 'the ridge between the north and middle valleys'),
        poly(RIDGE_S, 2, 'the ridge between the middle and south valleys'),
        poly(EDGE_N, 2, 'the north edge ridge'),
        poly(EDGE_S, 2, 'the south edge ridge'),
        poly(WEST_HILLS, 2, 'hills behind the base'),
        poly(SW_HILLS, 2, 'hills south-west of the base'),
    ],
    ramps=[],
    roads=[Road(((1250, 2500), PAD), 140.0),
           Road((PAD, (GAP_X, LANES['middle']), (4250, 2500)), 120.0),
           Road((PAD, (GAP_X, LANES['north']), (4000, LANES['north']), (4250, 2900)), 100.0, 'Dirt_Yucatan04'),
           Road((PAD, (GAP_X, LANES['south']), (4000, LANES['south']), (4250, 2100)), 100.0, 'Dirt_Yucatan04')])


def _objects():
    ore = [(850, 2050), (1010, 1930),               # the base's own
           (4520, 3350), (4650, 3220),              # the east
           (2000, 3600), (2150, 1350)]              # north and south of the complex
    out = [Obj('OreNode', x, y, side='neutral', angle=0.0, site='map') for x, y in ore]
    out.append(Obj('OilDerrick', 1900, 4200, side='neutral', angle=0.0, site='map'))
    return out


OBJECTS = _objects()

WOODS = {'HB_Tree04': 1, 'MR_Tree04': 1, 'CC_Tree03': 1}
UNDER = {'CC_GRASS06': 4, 'CC_Grass01': 3, 'HB_GRASS02': 3, 'CC_Bush01': 1}
ROCKS = {'YU_LARGEROCKS02': 1, 'YU_SMALLROCKS01': 3, 'YU_SMALLROCKS02': 2}
# building ground kept open: the Soviet base round the start, the launch complex, the east's staging ground, the
# valleys' gaps (J7's jammers and their guards stand there)
AVOID = [(1250.0, 2500.0, 700.0), (PAD[0], PAD[1], 450.0), (4250.0, 2600.0, 600.0)] + \
    [(GAP_X - 100.0, y, 300.0) for y in LANES.values()]


def _scenery():
    ground = platprops.Ground(LAYOUT)
    picks = []

    def put(cands):
        picks.extend(platprops.place(cands, LAYOUT, SITES, OBJECTS, keep=picks, avoid=AVOID, ground=ground))
    for k, region in enumerate((RIDGE_N, RIDGE_S, EDGE_N, EDGE_S, WEST_HILLS, SW_HILLS)):
        put(scatter(area('poly', region), ROCKS, 70, 30 + k, density=0.6, patches=0.5))
    put(cliff_feet(ground, ROCKS, 80, 61))
    put(scatter(area('rect', (0, 0, 5000, 5000)), WOODS, 260, 42, density=0.4))
    put(scatter(area('rect', (0, 0, 5000, 5000)), UNDER, 80, 63, density=0.5, patches=0.4))
    return [Obj(t, round(x, 1), round(y, 1), side='civ', angle=round(a, 3), site='map') for t, x, y, a in picks]


SCENERY = _scenery()


def terrain(m):
    """CampNew18's generate (objects, scripts, light, the start) with the platform terrain over its island."""
    c18.generate(m)
    previews, _ = platmap.apply(m, LAYOUT)
    c18.PREVIEWS.update(previews)


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
