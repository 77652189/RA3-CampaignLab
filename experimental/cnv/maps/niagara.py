"""尼亚加拉 (A7 鹰派, docs/story/plans/a7.md), built the retail way (docs/story/map-language.md, platmap): only like
Niagara -- a river from north to south that Goat Island splits, the hydro station on the island, the hawks across
the river -- shaped by what the level needs, not by the real falls.

  - West bank (the player): low ground (tier 1) round the start, and a raised plateau (tier 2) north-east of the base
    with ramps, where two of the three outposts stand; the third is on low ground south.
  - The river cuts the map in two: the ground army crosses only by three bridges -- the north one, and two short
    ones from the west bank to Goat Island and on to the east bank. The island is the station's: water on three
    sides, a bridge at each end.
  - East bank: the hawks' base and the carrier's home; the carrier leaves the battle by the north edge.
  - Borders: the west bank alone (phase 1), then the whole map.

Published: SITES, PLAYERS, TEAMS, OBJECTS (ore, a derrick, the bridges), LAYOUT, BORDERS.
"""
import make_campnew18 as c18
import platmap
from platmap import Layout, Ramp, Road, poly, rect
from maps import island
from parts import Obj, Site

RIVER = (2300.0, 2900.0)                        # its west and east banks (x)
GOAT = (2450.0, 2750.0, 2450.0, 3350.0)         # Goat Island: x0, x1, y0, y1
PLATEAU = (1500.0, 2150.0, 2950.0, 4400.0)      # the west plateau: x0, x1, y0, y1
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

LAYOUT = Layout(
    shapes=[
        poly([(300, 500), (1200, 380), (2300, 420), (2300, 4650), (1300, 4620), (380, 4500), (250, 3000),
              (330, 1600)], 1, 'west bank: low ground'),
        poly([(2900, 420), (3900, 380), (4650, 550), (4720, 2500), (4600, 4600), (3600, 4700), (2900, 4650)], 1,
             'east bank: low ground'),
        rect(GOAT[0], GOAT[2], GOAT[1], GOAT[3], 1, 'Goat Island'),
        rect(PLATEAU[0], PLATEAU[2], PLATEAU[1], PLATEAU[3], 2, 'the west plateau'),
    ],
    ramps=[
        Ramp((1350.0, 3500.0), (1580.0, 3500.0), 200.0, 'west plateau, west side'),
        Ramp((1800.0, 2780.0), (1800.0, 3030.0), 200.0, 'west plateau, south side'),
    ],
    roads=[Road(((1300, 2500), (2050, 2500), (2050, BRIDGE_Y), (2250, BRIDGE_Y)), 120.0),
           Road(((2950, BRIDGE_Y), (3150, 3300), (3600, 3300)), 120.0)])

BRIDGES = [((2250.0, BRIDGE_Y), (2520.0, BRIDGE_Y)), ((2680.0, BRIDGE_Y), (2950.0, BRIDGE_Y)),
           ((2250.0, NORTH_Y), (2950.0, NORTH_Y))]


def _objects():
    out = []
    for p, q in BRIDGES:
        for x, y, a, flags in platmap.bridge(p, q, 'HB_Bridge_02'):
            out.append(Obj('HB_Bridge_02', x, y, side='neutral', angle=a, flags=flags, site='map'))
    ore = [(850, 2050), (1010, 1930),               # the player's own, ~550 from the start
           (1050, 3750), (1230, 3850),              # north of the base, below the plateau
           (2000, 1150), (2180, 1060),              # the south, by outpost 2
           (4150, 2950), (4250, 3120),              # the hawks' own
           (3400, 1300)]                            # one on the east bank's open south
    out += [Obj('OreNode', x, y, side='neutral', angle=0.0, site='map') for x, y in ore]
    out.append(Obj('OilDerrick', 700, 3200, side='neutral', angle=0.0, site='map'))
    return out


OBJECTS = _objects()


def terrain(m):
    """CampNew18's generate (objects, scripts, light, the start) with the platform terrain over its island."""
    c18.generate(m)
    previews, _ = platmap.apply(m, LAYOUT)
    c18.PREVIEWS.update(previews)


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
