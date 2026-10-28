"""姬路城下 (J3 白鹭城下, docs/story/outline.md), built the retail way (docs/story/map-language.md, platmap): only
like Himeji -- a castle on its hill over a town -- shaped by what the level needs.

  - The castle hill (tier 2) stands north-east of the start; the keep (tier 3) on top. The hill has two ways up:
    the main gate's ramp on its south side, over the town, guarded; and a narrow back way up its north-east corner,
    out of sight -- what a scout finds. The FutureTech training ground (the archive) is on the hill's east part.
  - The town lies south of the hill on low ground, its streets lined with houses; the player comes in from the west.
  - Hills along the north edge, woods in the west.

Published: SITES, PLAYERS, TEAMS, OBJECTS (ore), SCENERY (houses along the streets, woods, rocks: platprops, kept
off every way and place), LAYOUT, BORDERS.
"""
import make_campnew18 as c18
import platmap
import platprops
from platmap import Layout, Ramp, Road, poly, wobble
from platprops import along, area, cliff_feet, scatter
from maps import island
from parts import Obj, Site

HILL = [(2300, 2900), (3000, 2850), (3800, 2950), (4100, 3400), (4000, 4100), (3400, 4300), (2600, 4250),
        (2200, 3800)]
KEEP = [(2700, 3550), (3050, 3500), (3150, 3800), (2900, 3950), (2650, 3850)]
GATE = (3000.0, 2850.0)                         # the main gate: the head of the south ramp
BACK = (4000.0, 4100.0)                         # the back way: the north-east corner

SITES = {k: island.SITES[k] for k in ('island', 'start', 'base factory', 'base power', 'west field', 'base edge')}
SITES.update({
    'west road': Site(1500.0, 2400.0, 200.0, 'the road in from the west, by the start'),
    'town': Site(2600.0, 2200.0, 300.0, 'the town south of the castle hill'),
    'gate foot': Site(3000.0, 2550.0, 150.0, "the foot of the main gate's ramp, in the town"),
    'main gate': Site(3000.0, 2950.0, 150.0, 'the main gate at the top of the south ramp: guarded'),
    'keep': Site(2900.0, 3720.0, 150.0, 'the keep on top of the hill'),
    'archive': Site(3600.0, 3500.0, 0.0, "the FutureTech training ground's archive, on the hill's east part",
                    build=220.0),
    'archive yard': Site(3600.0, 3500.0, 250.0, 'open ground round the archive'),
    'back foot': Site(4350.0, 4400.0, 120.0, "the foot of the back way up, outside the hill's north-east corner"),
    'back top': Site(3850.0, 3950.0, 120.0, "the head of the back way, on the hill"),
    'extraction': Site(700.0, 2200.0, 200.0, 'the west edge by the woods: where Yuriko is picked up'),
    'castle base': Site(2700.0, 3200.0, 250.0, "the FutureTech garrison's buildings on the hill, west part"),
    'castle barracks': Site(2550.0, 3250.0, 0.0, "the garrison's barracks", build=160.0),
    'castle factory': Site(2650.0, 3050.0, 0.0, "the garrison's war factory", build=200.0),
})
PLAYERS = island.PLAYERS
TEAMS = dict(island.TEAMS, s1='Soviet_1/teamSoviet_1')
BORDERS = {'whole': (0.0, 0.0, 5000.0, 5000.0)}

NORTH_HILLS = wobble([(-300, 4500), (1200, 4400), (2000, 4700), (2400, 5300), (-300, 5300)], 90.0, 101)
STREETS = [((1500, 2400), (2400, 2200), (3600, 2200)), ((2400, 1700), (2400, 2700)), ((3000, 1700), (3000, 2550))]

LAYOUT = Layout(
    shapes=[
        poly([(-300, -300), (5300, -300), (5300, 5300), (-300, 5300)], 1, 'the low ground'),
        poly(wobble(HILL, 50.0, 102, keep=[(*GATE, 140.0), (*BACK, 120.0)]), 2, 'the castle hill'),
        poly(wobble(KEEP, 20.0, 103), 3, 'the keep'),
        poly(NORTH_HILLS, 2, 'the north hills'),
    ],
    ramps=[Ramp((3000.0, 2550.0), (3000.0, 2950.0), 200.0, 'the main gate'),
           Ramp((4350.0, 4400.0), (3900.0, 4000.0), 110.0, 'the back way'),
           Ramp((2900.0, 3350.0), (2900.0, 3600.0), 120.0, 'up to the keep')],
    roads=[Road(s, 100.0) for s in STREETS] + [Road(((3000, 2950), (3000, 3300), (3600, 3500)), 90.0,
                                                    'Dirt_Yucatan04')])


def _objects():
    ore = [(1400, 1500), (1560, 1400)]
    return [Obj('OreNode', x, y, side='neutral', angle=0.0, site='map') for x, y in ore]


OBJECTS = _objects()

WOODS = {'OK_Tree01': 3, 'OK_Tree02': 2, 'TH_Tree01': 2, 'HB_Tree04': 1}
UNDER = {'OK_Shrub01': 3, 'OK_Shrub04': 2, 'CC_GRASS06': 2}
ROCKS = {'YU_LARGEROCKS02': 1, 'YU_SMALLROCKS01': 2, 'OK_GARDENROCK03': 1}
HOUSES = {'MJ_Structure_02': 3, 'MJ_Structure_04': 2, 'HA_Building16_02': 2, 'TH_SushiBar_01': 1}
# kept open: the start, the town's squares, the hill's top where the garrison and the archive stand
AVOID = [(1250.0, 2450.0, 500.0), (3000.0, 2550.0, 200.0), (2800.0, 3250.0, 400.0), (3600.0, 3500.0, 350.0),
         (700.0, 2200.0, 250.0)]


def _scenery():
    ground = platprops.Ground(LAYOUT)
    picks = []

    def put(cands):
        picks.extend(platprops.place(cands, LAYOUT, SITES, OBJECTS, keep=picks, avoid=AVOID, ground=ground))
    for k, street in enumerate(STREETS):
        put(along(street, HOUSES, 130, 140, 10 + k, face=True))
        put(along(street, 'OK_LANTERN01', 120, 70, 20 + k))
    put(scatter(area('poly', NORTH_HILLS), WOODS, 50, 30, density=0.85, patches=0.4))
    put(scatter(area('rect', (0, 0, 1000, 5000)), WOODS, 55, 31, density=0.8, patches=0.5))
    put(scatter(area('rect', (0, 0, 5000, 5000)), WOODS, 120, 32, density=0.5, patches=0.5))
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
