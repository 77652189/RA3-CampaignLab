"""阿苏火山 (J5 敌人的敌人, docs/story/outline.md), built the retail way (docs/story/map-language.md, platmap): only
like the volcano -- a cone with a crater in the middle of grassland, ridges round it -- shaped by what the level
needs.

  - The grassland is one low tier. The volcano stands east of the middle: a cone (tier 2), its rim (tier 3) and the
    crater inside (tier 2 again; lava is art, last). No ramp: nothing crosses it.
  - Two passes go round it, north and south, each ~650 across between the cone and an edge ridge; both meet at the
    volcano's west foot, in front of the Allied observatory -- what the player holds (J5).
  - West of the observatory, round the start, the player's base; east of the volcano, open ground: the FutureTech
    mercenaries' camp.

Published: SITES, PLAYERS, TEAMS, OBJECTS (ore, a derrick), SCENERY (grass, rocks, a few trees: platprops, kept off
every way and place), LAYOUT, BORDERS.
"""
import math

import make_campnew18 as c18
import platmap
import platprops
from platmap import Layout, Road, poly, wobble
from platprops import area, cliff_feet, scatter
from maps import island
from parts import Obj, Site

CONE = (3150.0, 2500.0)                         # the volcano's middle
CONE_R, RIM_R, CRATER_R = 600.0, 420.0, 240.0
PASSES = {'north': 3380.0, 'south': 1620.0}     # each pass's middle (y)
OBS = (1950.0, 2500.0)                          # the observatory


def ring(c, r, n, seed, amp):
    pts = [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return wobble(pts, amp, seed)


SITES = {k: island.SITES[k] for k in ('island', 'start', 'base factory', 'base power', 'west field', 'base edge')}
SITES.update({
    'base yard': Site(1250.0, 2500.0, 0.0, "the construction yard's pad on the player's start", build=200.0),
    'base barracks': Site(1250.0, 2800.0, 0.0, "a barracks' pad north of the yard", build=160.0),
    'base refinery': Site(1130.0, 2060.0, 0.0, "a refinery's pad by the base's own ore (~180 from the nearer node)",
                          build=200.0),
    'observatory': Site(*OBS, 0.0, "the Allied observatory at the volcano's west foot", build=220.0),
    'observatory yard': Site(*OBS, 350.0, 'open ground round the observatory'),
    'west foot': Site(2400.0, 2500.0, 200.0, "the volcano's west foot, where both passes come out"),
    'crater': Site(*CONE, CRATER_R, 'the crater (no way in): only to look at'),
    'merc camp': Site(4250.0, 2500.0, 450.0, "open ground east of the volcano: the mercenaries' camp"),
    'merc barracks': Site(4100.0, 2800.0, 0.0, 'a barracks in the camp', build=160.0),
    'merc factory': Site(4400.0, 2200.0, 0.0, 'a war factory in the camp', build=200.0),
    'merc power': Site(4550.0, 2750.0, 0.0, 'a power plant in the camp', build=120.0),
    'merc refinery': Site(4430.0, 3180.0, 0.0, 'a refinery in the camp, by its ore (~180 from the nearer node)',
                          build=200.0),
})
for side, y in PASSES.items():
    SITES[f'{side} pass'] = Site(CONE[0], y, 200.0, f'the {side} pass between the volcano and the edge ridge, '
                                                    'halfway (~650 across)')
    SITES[f'{side} mouth'] = Site(3950.0, y, 200.0, f"the {side} pass's east end, open to the camp")
    SITES[f'{side} exit'] = Site(2550.0, y, 150.0, f"the {side} pass's west end, toward the observatory")
PLAYERS = island.PLAYERS
TEAMS = dict(island.TEAMS, s1='Soviet_1/teamSoviet_1')
BORDERS = {'whole': (0.0, 0.0, 5000.0, 5000.0)}

CONE_POLY = ring(CONE, CONE_R, 18, 91, 40.0)
RIM_POLY = ring(CONE, RIM_R, 16, 92, 30.0)
CRATER_POLY = ring(CONE, CRATER_R, 12, 93, 20.0)
EDGE_N = wobble([(2300, 3750), (3100, 3720), (3900, 3760), (4500, 3900), (5300, 4100), (5300, 5300), (1900, 5300),
                 (1900, 4300)], 60.0, 94)
EDGE_S = wobble([(2300, 1250), (3100, 1280), (3900, 1240), (4500, 1100), (5300, 900), (5300, -300), (1900, -300),
                 (1900, 700)], 60.0, 95)
WEST_HILLS = wobble([(-300, 3300), (400, 3400), (700, 3900), (500, 4500), (-300, 4800)], 80.0, 96)
SW_HILLS = wobble([(-300, 600), (600, 500), (900, 1000), (500, 1500), (-300, 1600)], 80.0, 97)

LAYOUT = Layout(
    shapes=[
        poly([(-300, -300), (5300, -300), (5300, 5300), (-300, 5300)], 1, 'the grassland'),
        poly(CONE_POLY, 2, "the volcano's cone"),
        poly(RIM_POLY, 3, "the crater's rim"),
        poly(CRATER_POLY, 2, 'the crater'),
        poly(EDGE_N, 2, 'the north edge ridge'),
        poly(EDGE_S, 2, 'the south edge ridge'),
        poly(WEST_HILLS, 2, 'hills behind the base'),
        poly(SW_HILLS, 2, 'hills south-west of the base'),
    ],
    ramps=[],
    roads=[Road(((1250, 2500), OBS, (2400, 2500)), 140.0),
           Road(((2400, 2500), (2550, PASSES['north']), (3950, PASSES['north']), (4250, 2850)), 110.0,
                'Dirt_Yucatan04'),
           Road(((2400, 2500), (2550, PASSES['south']), (3950, PASSES['south']), (4250, 2150)), 110.0,
                'Dirt_Yucatan04')])


def _objects():
    ore = [(850, 2050), (1010, 1930),               # the base's own
           (4520, 3350), (4650, 3220),              # the camp's
           (1800, 3500), (1800, 1500)]              # north and south of the observatory
    out = [Obj('OreNode', x, y, side='neutral', angle=0.0, site='map') for x, y in ore]
    out.append(Obj('OilDerrick', 1500, 4100, side='neutral', angle=0.0, site='map'))
    return out


OBJECTS = _objects()

WOODS = {'HB_Tree04': 1, 'MR_Tree04': 1, 'CC_Tree03': 1}
UNDER = {'CC_GRASS06': 4, 'CC_Grass01': 3, 'HB_GRASS02': 3, 'CC_Bush01': 1}
ROCKS = {'YU_LARGEROCKS02': 1, 'YU_SMALLROCKS01': 3, 'YU_SMALLROCKS02': 2}
# building ground kept open: the base round the start, the observatory, the camp, both passes and the west foot
AVOID = [(1250.0, 2500.0, 700.0), (OBS[0], OBS[1], 450.0), (2400.0, 2500.0, 300.0), (4250.0, 2600.0, 600.0)] + \
    [(x, y, 280.0) for y in PASSES.values() for x in (2550.0, CONE[0], 3950.0)]


def _scenery():
    ground = platprops.Ground(LAYOUT)
    picks = []

    def put(cands):
        picks.extend(platprops.place(cands, LAYOUT, SITES, OBJECTS, keep=picks, avoid=AVOID, ground=ground))
    for k, region in enumerate((CONE_POLY, EDGE_N, EDGE_S, WEST_HILLS, SW_HILLS)):
        put(scatter(area('poly', region), ROCKS, 70, 30 + k, density=0.7, patches=0.5))
    put(cliff_feet(ground, ROCKS, 80, 61))
    put(scatter(area('rect', (0, 0, 5000, 5000)), WOODS, 240, 42, density=0.45))
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
