"""札幌雪祭 (A4 / J4, docs/story/outline.md): for now the generated island's terrain (maps/island.py; snow is art,
art last) with the festival laid over it -- a road across the island from the convoy's start by the player's base to
the exit on the east shore, and three plazas beside it, two north and one south, each opening onto the road by a
gate. The plazas' walls and sculptures are the mission's to place (missions/a4.py), by these sites.

Published: SITES (the island's start, base and field sites, and the festival's), PLAYERS and TEAMS.
"""
from maps import island
from parts import Site

ROAD_Y = 2500.0
PLAZA_X = (2300.0, 2900.0, 3500.0)
NORTH = (True, False, True)                     # plaza k north of the road (its gate faces south) or south of it
GATE_OFF = 150.0                                # a gate's line from the road's middle
DEPTH = 122.0                                   # a plaza's middle from its gate line

SITES = {k: island.SITES[k] for k in ('island', 'start', 'base factory', 'base power', 'west field')}
SITES.update({
    'convoy start': Site(1700.0, ROAD_Y, 100.0, "the road's west end by the player's base: the convoy forms up here"),
    'road exit': Site(3900.0, ROAD_Y, 150.0, "the road's east end on the east shore: the convoy is safe here"),
    'north camp': Site(2900.0, 3250.0, 200.0, 'open ground north of the plazas, off the road: a force that comes '
                                               'round to the gates (J4)'),
})
for k, (x, north) in enumerate(zip(PLAZA_X, NORTH), 1):
    s = 1 if north else -1
    side = 'north' if north else 'south'
    SITES[f'gate {k}'] = Site(x, ROAD_Y + s * GATE_OFF, 0.0, f"plaza {k}'s gate: the middle of its opening onto the "
                                                                f'road ({side} of it, {GATE_OFF:g} off)')
    SITES[f'plaza {k}'] = Site(x, ROAD_Y + s * (GATE_OFF + DEPTH), 120.0, f'plaza {k}, {side} of the road: '
                                                                           'its sculptures stand here')
    SITES[f'approach {k}'] = Site(x - 350.0, ROAD_Y, 150.0, f'the road west of plaza {k}: a convoy here is '
                                                            'about to pass it')
PLAYERS = island.PLAYERS
TEAMS = dict(island.TEAMS, s1='Soviet_1/teamSoviet_1')


def terrain(m):
    island.terrain(m)


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
