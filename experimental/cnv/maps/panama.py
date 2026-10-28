"""巴拿马运河船闸 (A5 / S5 巴拿马之锁, docs/story/outline.md), built the retail way (docs/story/map-language.md,
platmap): only like the canal -- a lock between the sea and a lake, jungle on both banks -- shaped by what the
levels need.

  - The canal runs south to north up the map's middle (bank to bank 200), from the sea at the south edge to the
    lake that fills the north. Halfway it widens to the lock chamber (400 across, 700 long) between two gates:
    the Allied fleet is shut in it (a structure on the water bars no ship, bench 2026-10-27: the plan holds the
    fleet IMMOBILE while the gates are shut; the gates are their look).
  - West bank (the player): low ground round the start, a ridge behind it, jungle hills in the south-west.
  - East bank: the lock's control room on a bluff (tier 2) that drops straight into the chamber -- one ramp up,
    on its east side, away from the water; the Soviet base north-east by the lake, a beach south of the bluff
    where a boat can land. No bridge crosses the canal: a bridge bars ships (bench 2026-10-27: the fleet stood at
    its piers), and the fleet must sail its length (A5 out to the sea, S5 down from the lake). Across the water go
    what swims (the Riptide, the Bullfrog, the burrower) and whom the beacon pulls.
  - Borders: the west bank and the canal (phase 1), then the whole map.

Published: SITES, PLAYERS, TEAMS, OBJECTS (ore, a derrick), SCENERY (retail jungle trees, rocks ...:
platprops, kept off every way and place), LAYOUT, BORDERS.
"""
import make_campnew18 as c18
import platmap
import platprops
from platmap import Layout, Ramp, Road, poly, wobble
from platprops import area, cliff_feet, scatter, shore
from maps import island
from parts import Obj, Site

CANAL = (2400.0, 2600.0)                        # its west and east banks (x), north and south of the chamber
CHAMBER = (2300.0, 2700.0, 2150.0, 2850.0)      # the lock chamber: x0, x1, y0, y1
LAKE_Y = 3700.0                                 # the lake's south shore (the canal opens into it)
SOUTH_Y = 900.0                                 # the east bank's south shore landing (once a bridge, see above)
BLUFF = (2700.0, 3250.0, 2200.0, 2800.0)        # the control room's bluff on the east bank: x0, x1, y0, y1

SITES = {k: island.SITES[k] for k in ('island', 'start', 'base factory', 'base power', 'west field', 'base edge')}
SITES.update({
    'base yard': Site(1250.0, 2500.0, 0.0, "the construction yard's pad on the player's start", build=200.0),
    'base barracks': Site(1250.0, 2800.0, 0.0, "a barracks' pad north of the yard", build=160.0),
    'base refinery': Site(1130.0, 2060.0, 0.0, "a refinery's pad by the player's own ore (~180 from the nearer "
                                               'node, as retail)', build=200.0),
    'west quay': Site(2150.0, 2500.0, 150.0, "the west bank by the lock chamber: the player's side of the water"),
    'chamber': Site(2500.0, 2500.0, 180.0, 'the lock chamber, between the gates: the fleet is shut in here'),
    'south gate': Site(2500.0, CHAMBER[2], 0.0, "the chamber's south gate, across the canal (200 of water)"),
    'north gate': Site(2500.0, CHAMBER[3], 0.0, "the chamber's north gate, across the canal toward the lake"),
    'sea exit': Site(2500.0, 300.0, 250.0, 'the canal at the south edge: past it the fleet is out at sea'),
    'south canal': Site(2500.0, 1500.0, 150.0, 'the canal south of the chamber: the way to the sea'),
    'control room': Site(3000.0, 2500.0, 0.0, "the lock's control room on the bluff over the chamber", build=200.0),
    'control yard': Site(3000.0, 2500.0, 220.0, "the bluff's top round the control room: its guards stand here"),
    'bluff ramp': Site(3450.0, 2500.0, 120.0, "the foot of the bluff's one ramp, on its east side"),
    'east beach': Site(2780.0, 1850.0, 120.0, 'low ground on the east bank south of the bluff, at the water: a '
                                              'boat lands here'),
    'east shore': Site(2900.0, SOUTH_Y, 150.0, 'the east bank by the water, far south: the Soviets guard it'),
    'east base': Site(4000.0, 3500.0, 450.0, 'the Soviet base on the east bank by the lake'),
    'east barracks': Site(3750.0, 3300.0, 0.0, 'the Soviet barracks', build=160.0),
    'east factory': Site(4100.0, 3250.0, 0.0, 'the Soviet war factory', build=200.0),
    'east power': Site(4300.0, 3650.0, 0.0, 'the Soviet power plant', build=120.0),
    'east refinery': Site(4380.0, 2900.0, 0.0, 'the Soviet refinery, by their ore (~180 from the nearer node)',
                          build=200.0),
    'east gate': Site(3600.0, 2900.0, 200.0, 'open ground between the Soviet base and the bluff: their army forms '
                                             'up here'),
    'lake': Site(2600.0, 4300.0, 400.0, 'the lake north of the lock: the Soviet boats'),
})
PLAYERS = island.PLAYERS
TEAMS = dict(island.TEAMS, s1='Soviet_1/teamSoviet_1')
BORDERS = {'whole': (0.0, 0.0, 5000.0, 5000.0), 'west bank': (0.0, 0.0, CHAMBER[1] + 30.0, 5000.0)}

BRIDGES = []                                    # none (see above)
_AT_SOUTH = [(x, SOUTH_Y, 140.0) for x in (CANAL[0], CANAL[1])]
_AT_CHAMBER = [(x, y, 60.0) for x in (CHAMBER[0], CHAMBER[1]) for y in (CHAMBER[2], CHAMBER[3])]

# the banks, south to north: straight along the canal and the chamber, bent a little elsewhere
WEST_BANK = wobble([(CANAL[0], -300), (CANAL[0], SOUTH_Y), (CANAL[0], CHAMBER[2] - 60), (CHAMBER[0], CHAMBER[2]),
                    (CHAMBER[0], CHAMBER[3]), (CANAL[0], CHAMBER[3] + 60), (CANAL[0], LAKE_Y), (1900, 3850),
                    (1500, 4100), (1200, 4600), (900, 5300)], 30.0, 71, keep=_AT_SOUTH + _AT_CHAMBER, closed=False)
EAST_BANK = wobble([(CANAL[1], -300), (CANAL[1], SOUTH_Y), (CANAL[1], CHAMBER[2] - 60), (CHAMBER[1], CHAMBER[2]),
                    (CHAMBER[1], CHAMBER[3]), (CANAL[1], CHAMBER[3] + 60), (CANAL[1], LAKE_Y), (3100, 3850),
                    (3600, 4000), (4100, 4300), (4500, 4800), (4700, 5300)], 30.0, 72,
                   keep=_AT_SOUTH + _AT_CHAMBER, closed=False)
BLUFF_EDGE = [(BLUFF[0], BLUFF[2]), (BLUFF[0], BLUFF[3]), (3050, BLUFF[3] + 20), (BLUFF[1], 2700),
              (BLUFF[1] + 10, 2500), (BLUFF[1], 2300), (3050, BLUFF[2] - 20)]
WEST_RIDGE = wobble([(-300, 3200), (350, 3300), (600, 3700), (700, 4200), (500, 4700), (-300, 5300)], 90.0, 73)
SW_HILLS = wobble([(-300, 300), (700, 400), (1300, 650), (1500, 1100), (1100, 1400), (500, 1300), (-300, 1500)],
                  80.0, 74)
SE_HILLS = wobble([(3300, -300), (3400, 300), (3900, 500), (4600, 400), (5300, 600), (5300, -300)], 80.0, 75)
EAST_RIDGE = wobble([(5300, 1200), (4800, 1400), (4700, 2100), (4850, 2600), (5300, 2700)], 80.0, 76)

LAYOUT = Layout(
    shapes=[
        poly(WEST_BANK + [(-300, 5300), (-300, -300)], 1, 'west bank: low ground'),
        poly(EAST_BANK + [(5300, 5300), (5300, -300)], 1, 'east bank: low ground'),
        poly(BLUFF_EDGE, 2, "the control room's bluff"),
        poly(WEST_RIDGE, 2, 'the ridge behind the base'),
        poly(SW_HILLS, 2, 'the south-west hills'),
        poly(SE_HILLS, 2, 'the south-east hills'),
        poly(EAST_RIDGE, 2, 'the east ridge'),
    ],
    ramps=[Ramp((3500.0, 2500.0), (3230.0, 2500.0), 200.0, 'the bluff, east side')],
    roads=[Road(((1250, 2380), (1500, 1600), (1900, SOUTH_Y), (CANAL[0] - 60, SOUTH_Y)), 110.0),
           Road(((CANAL[1] + 60, SOUTH_Y), (3100, 1300), (3500, 2000), (3600, 2500), (3500, 2500)), 110.0),
           Road(((3600, 2500), (3700, 3000), (3800, 3300)), 110.0),
           Road(((1250, 2620), (1700, 2600), (2150, 2500)), 90.0, 'Dirt_Yucatan04'),
           Road(((3250, 2500), (2950, 2500)), 90.0, 'Dirt_Yucatan04')])


def _objects():
    out = []
    for p, q in BRIDGES:
        for x, y, a, flags in platmap.bridge(p, q, 'HB_Bridge_02'):
            out.append(Obj('HB_Bridge_02', x, y, side='neutral', angle=a, flags=flags, site='map'))
    ore = [(850, 2050), (1010, 1930),               # the player's own, ~550 from the start
           (1650, 1150), (1800, 1250),              # the west bank south
           (4250, 3050), (4450, 3150),              # the Soviets' own
           (3300, 1200)]                            # one on the east bank south
    out += [Obj('OreNode', x, y, side='neutral', angle=0.0, site='map') for x, y in ore]
    out.append(Obj('OilDerrick', 700, 3000, side='neutral', angle=0.0, site='map'))
    return out


OBJECTS = _objects()

# retail's jungle trees (YU_TreeSerengeti*, HV_Tree01) are not in platprops' catalog yet: broadleaf stands in
# (art last)
WOODS = {'HB_Tree04': 3, 'HB_Tree02': 2, 'HB_Tree03': 2, 'HB_TREE09': 1}
UNDER = {'YU_BUSH05': 3, 'CC_Bush01': 2, 'YP_Fern01': 3, 'CC_GRASS06': 2}
ROCKS = {'YU_LARGEROCKS02': 1, 'YU_SMALLROCKS01': 2, 'YU_SMALLROCKS02': 2}
# building ground kept open: the player's base round the start, the Soviets' round theirs and the ground before
# it where S5's army stands, the bluff's top
AVOID = [(1250.0, 2500.0, 700.0), (4000.0, 3400.0, 600.0), (3650.0, 2850.0, 350.0), (3000.0, 2500.0, 260.0)]


def _scenery():
    ground = platprops.Ground(LAYOUT)
    picks = []

    def put(cands):
        picks.extend(platprops.place(cands, LAYOUT, SITES, OBJECTS, keep=picks, avoid=AVOID, ground=ground))
    for k, region in enumerate((WEST_RIDGE, SW_HILLS, SE_HILLS, EAST_RIDGE)):
        put(scatter(area('poly', region), WOODS, 50, 30 + k, density=0.85, patches=0.42))
    put(scatter(area('rect', (0, 0, 5000, 5000)), WOODS, 58, 42, density=0.8, patches=0.6))
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
