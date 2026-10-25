"""札幌雪祭 (A4 / J4, docs/story/outline.md), built the retail way (docs/story/map-language.md, platmap): flat
ground in tiers, narrow cliffs, few ramps, a canal crossed by bridges -- shaped by what the levels need, not by
Sapporo's real streets (snow is art, art last).

  - The festival avenue runs east on the low ground (tier 1) from the convoy's start by the player's base to the
    harbour exit. Three plazas beside it, two north and one south, are raised a tier: cliffs on every side, one ramp
    down to the avenue -- the gate, the only way in or out (it was snow banks around flat ground before).
  - A canal cuts the harbour district off the east end: three bridges (bridge objects, as retail) are the only ground
    way across; the avenue's is the convoy's last stretch before the exit.
  - North and south, a raised plateau each with ramps, ore and an oil derrick: ground worth taking. The player's base
    has its own pair of ore nodes ~550 off, as retail starts do.

Published: SITES (the island's start, base and field sites, and the festival's), PLAYERS, TEAMS, OBJECTS (the map's
own: ore nodes, tech buildings, bridges -- placed with the terrain, not by a mission), LAYOUT (the terrain).
"""
import make_campnew18 as c18
import platmap
from platmap import Layout, Ramp, Road, poly, rect
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


def _plazas():
    shapes, ramps, roads = [], [], []
    for k, (x, north) in enumerate(zip(PLAZA_X, NORTH), 1):
        s = 1 if north else -1
        y0, y1 = sorted((ROAD_Y + s * PLAZA_FRONT, ROAD_Y + s * PLAZA_BACK))
        shapes.append(rect(x - PLAZA_HALF, y0, x + PLAZA_HALF, y1, 2, f'plaza {k}'))
        ramps.append(Ramp((x, ROAD_Y + s * RAMP_FOOT), (x, ROAD_Y + s * RAMP_HEAD), RAMP_WIDTH, f'gate {k}'))
        roads.append(Road(((x, ROAD_Y), (x, ROAD_Y + s * (PLAZA_FRONT + 20))), RAMP_WIDTH - 30))
    return shapes, ramps, roads


_ps, _pr, _proads = _plazas()
LAYOUT = Layout(
    shapes=[
        poly([(250, 600), (900, 420), (2000, 520), (3100, 430), (4150, 600), (4250, 1600), (4150, 2300),
              (4180, 2900), (4300, 3700), (4100, 4550), (3000, 4620), (1800, 4500), (600, 4600), (300, 3800),
              (420, 2900), (260, 2000)], 1, 'the island: low ground'),
        rect(2000, 3550, 3450, 4350, 2, 'north plateau'),
        rect(2000, 750, 3400, 1500, 2, 'south plateau'),
        rect(350, 3200, 1100, 4300, 2, 'west ridge behind the base'),
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
    roads=[Road(((1500, ROAD_Y), (4050, ROAD_Y)), 120.0), *_proads])

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


def terrain(m):
    """CampNew18's generate (objects, scripts, light, the start) with the platform terrain over its island."""
    c18.generate(m)
    previews, _ = platmap.apply(m, LAYOUT)
    c18.PREVIEWS.update(previews)


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
