"""西伯利亚大铁路 (S2 西伯利亚快车, docs/story/outline.md), built the retail way (docs/story/map-language.md,
platmap): only like the Trans-Siberian -- a railway through the taiga, stations, a river bridge -- shaped by what
the level needs (snow is art, art last).

  - The railway (a road texture: the track is the trains' routes, by site) runs from the west edge past the
    player's start, bends north through a birch wood to a station, crosses a river, comes down past a second
    station to an eastern one and leaves by the east edge. Each station is a site the trains stop at.
  - Ridges (tier 2) close the line in on both sides through the middle: the fighting is along the track. Where the
    ground opens by the stations the guards stand.
  - The river is crossed by one bridge (the railway's): the river runs north-south, the line over it.

Published: SITES, PLAYERS, TEAMS, OBJECTS (ore, the bridge), SCENERY (taiga woods, rocks: platprops, kept off
every way and place), LAYOUT, BORDERS.
"""
import make_campnew18 as c18
import platmap
import platprops
from platmap import Layout, Road, poly, wobble
from platprops import area, cliff_feet, scatter, shore
from maps import island
from parts import Obj, Site

RIVER = (2900.0, 3150.0)                        # the river's west and east banks (x)
BRIDGE_Y = 3400.0                               # the railway's bridge over it
LINE = [(200, 2500), (900, 2350), (1500, 2700), (2000, 3300), (2600, BRIDGE_Y), (RIVER[0] - 80, BRIDGE_Y),
        (RIVER[1] + 80, BRIDGE_Y), (3600, 3200), (3900, 2500), (4200, 1800), (4850, 1500)]

SITES = {k: island.SITES[k] for k in ('island', 'start', 'base factory', 'base power', 'west field', 'base edge')}
SITES.update({
    'west station': Site(900.0, 2350.0, 140.0, 'the line by the start: the trains set off here'),
    'west siding': Site(400.0, 2460.0, 140.0, 'the line west of the start, behind the west station'),
    'birch station': Site(2000.0, 3300.0, 140.0, 'the station in the birch wood, north of the start'),
    'birch yard': Site(1850.0, 3550.0, 220.0, "open ground by the birch station: its guards"),
    'bridge west': Site(RIVER[0] - 150.0, BRIDGE_Y, 120.0, "the line at the river bridge's west end"),
    'river station': Site(3600.0, 3200.0, 140.0, 'the station past the river'),
    'river yard': Site(3850.0, 3000.0, 180.0, 'open ground by the line past the river station: its guards'),
    'east station': Site(4200.0, 1800.0, 140.0, 'the last station, east'),
    'east yard': Site(4350.0, 2150.0, 220.0, 'open ground by the east station: its guards'),
    'line exit': Site(4850.0, 1500.0, 150.0, 'the line at the east edge: past it a train is gone'),
})
PLAYERS = island.PLAYERS
TEAMS = dict(island.TEAMS, s1='Soviet_1/teamSoviet_1')
BORDERS = {'whole': (0.0, 0.0, 5000.0, 5000.0)}

_AT_BRIDGE = [(x, BRIDGE_Y, 150.0) for x in RIVER]
WEST_LAND = wobble([(RIVER[0], -300), (RIVER[0], 1500), (RIVER[0] - 40, 2800), (RIVER[0], BRIDGE_Y),
                    (RIVER[0] + 20, 4300), (RIVER[0], 5300)], 40.0, 91, keep=_AT_BRIDGE, closed=False)
EAST_LAND = wobble([(RIVER[1], -300), (RIVER[1] + 30, 1500), (RIVER[1], 2800), (RIVER[1], BRIDGE_Y),
                    (RIVER[1] - 10, 4300), (RIVER[1], 5300)], 40.0, 92, keep=_AT_BRIDGE, closed=False)
# ridges hemming the line in through the middle (between them the track and ~300 either side)
RIDGE_A = wobble([(1000, 3100), (1450, 3150), (1600, 3600), (1300, 4000), (900, 3800), (850, 3300)], 60.0, 99)
RIDGE_B = wobble([(1700, 2200), (2300, 2400), (2600, 2900), (2500, 3050), (2050, 2900), (1800, 2600)], 60.0, 94)
RIDGE_C = wobble([(3450, 3650), (3900, 3750), (4300, 3550), (4350, 3050), (4150, 2850), (3950, 3150)], 60.0, 95)
RIDGE_D = wobble([(3250, 2300), (3500, 2650), (3600, 2150), (3750, 1600), (3500, 1300), (3250, 1800)], 60.0, 96)
SOUTH_HILLS = wobble([(-300, 300), (1500, 400), (2400, 900), (2500, 1600), (1400, 1700), (-300, 1500)], 90.0, 97)
NE_HILLS = wobble([(3600, 5300), (3700, 4500), (4500, 4200), (5300, 4300), (5300, 5300)], 90.0, 98)

LAYOUT = Layout(
    shapes=[
        poly(WEST_LAND + [(-300, 5300), (-300, -300)], 1, 'the west bank'),
        poly(EAST_LAND + [(5300, 5300), (5300, -300)], 1, 'the east bank'),
        poly(RIDGE_A, 2, 'the ridge north-west of the line'),
        poly(RIDGE_B, 2, 'the ridge south of the line, west of the river'),
        poly(RIDGE_C, 2, 'the ridge north of the line, east of the river'),
        poly(RIDGE_D, 2, 'the ridge west of the line, east of the river'),
        poly(SOUTH_HILLS, 2, 'the south hills'),
        poly(NE_HILLS, 2, 'the north-east hills'),
    ],
    ramps=[],
    roads=[Road(tuple(LINE), 90.0, 'Dirt_Yucatan04')])

BRIDGES = [((RIVER[0] - 80.0, BRIDGE_Y), (RIVER[1] + 80.0, BRIDGE_Y))]


def _objects():
    out = []
    for p, q in BRIDGES:
        for x, y, a, flags in platmap.bridge(p, q, 'HB_Bridge_02'):
            out.append(Obj('HB_Bridge_02', x, y, side='neutral', angle=a, flags=flags, site='map'))
    ore = [(850, 2050), (1010, 1930), (4500, 2550), (4650, 2450)]
    out += [Obj('OreNode', x, y, side='neutral', angle=0.0, site='map') for x, y in ore]
    return out


OBJECTS = _objects()

WOODS = {'MR_Redwood01': 1, 'MR_Tree04': 3, 'MR_TREE01': 3, 'MR_Tree05': 2, 'YP_Tree02': 2}
UNDER = {'CC_Bush01': 2, 'YP_Fern01': 2, 'CC_GRASS06': 3}
ROCKS = {'YU_LARGEROCKS02': 1, 'YU_SMALLROCKS01': 2, 'YU_SMALLROCKS02': 2}
# kept open: the player's start, the stations' yards
AVOID = [(1000.0, 2450.0, 500.0), (1900.0, 3450.0, 320.0), (3750.0, 3100.0, 320.0), (4300.0, 2000.0, 360.0)]


def _scenery():
    ground = platprops.Ground(LAYOUT)
    picks = []

    def put(cands):
        picks.extend(platprops.place(cands, LAYOUT, SITES, OBJECTS, keep=picks, avoid=AVOID, ground=ground))
    for k, region in enumerate((RIDGE_A, RIDGE_B, RIDGE_C, RIDGE_D, SOUTH_HILLS, NE_HILLS)):
        put(scatter(area('poly', region), WOODS, 50, 30 + k, density=0.85, patches=0.4))
    put(scatter(area('rect', (0, 0, 5000, 5000)), WOODS, 60, 42, density=0.75, patches=0.55))
    put(shore(ground, {**WOODS, **ROCKS}, 60, 60))
    put(cliff_feet(ground, ROCKS, 85, 61))
    put(scatter(area('rect', (0, 0, 5000, 5000)), UNDER, 100, 63, density=0.4, patches=0.35))
    return [Obj(t, round(x, 1), round(y, 1), side='civ', angle=round(a, 3), site='map') for t, x, y, a in picks]


SCENERY = _scenery()


def terrain(m):
    """CampNew18's generate (objects, scripts, light, the start) with the platform terrain over its island."""
    c18.generate(m)
    previews, _ = platmap.apply(m, LAYOUT)
    c18.PREVIEWS.update(previews)


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
