"""A probe map for the engine line (checks/engine_terrain.py, docs/engine/terrain.md 3): flat ground, and on it four
pens -- a round floor 100 across its radius, a ring 60 wide round it -- that differ only in the ring:

  steep, unmarked   the ring is a wall 80 high (ours) rising 40 per cell, BlendTileData field 0 left off
  flat, marked      the ring is level ground, field 0 set on it
  steep, marked     the wall with field 0 set as our writers set it (terrain_rules.impassable_bits): the control
  flat, unmarked    nothing: the control

Whether a unit ordered out of a pen gets out answers whether the game walks by the map's field 0 alone or works out
cliffs from the heights itself. The ground textures stay grass everywhere (only looks, 推断).

Published: SITES (the start, each pen and the point outside it), PLAYERS, TEAMS, PENS.
"""
import numpy as np

import make_campnew18 as c18
import mapterrain
import platmap
import terrain_rules
from platmap import Layout, poly
from maps import island
from parts import Site

FLOOR, RING = 100.0, 60.0          # a pen: the floor's radius, the ring's width round it (world units)
WALL = 80.0                        # the steep ring's height over the ground (ours), up and down over 20 each
OUT = 260.0                        # the point outside a pen, north of its centre
# name: (centre, steep ring, field 0 on the ring)
PENS = {
    'steep unmarked': ((2000.0, 2500.0), True, False),
    'flat marked': ((2400.0, 2500.0), False, True),
    'steep marked': ((2800.0, 2500.0), True, True),
    'flat unmarked': ((3200.0, 2500.0), False, False),
}

SITES = {k: island.SITES[k] for k in ('island', 'start', 'base factory', 'base power', 'west field')}
for _name, ((_x, _y), _steep, _marked) in PENS.items():
    SITES[_name] = Site(_x, _y, FLOOR - 20.0, f'the floor of the pen with the {_name} ring')
    SITES[f'{_name} out'] = Site(_x, _y + OUT, 60.0, f'open ground north of the {_name} pen')
PLAYERS = island.PLAYERS
TEAMS = island.TEAMS

_LAYOUT = Layout(shapes=[poly([(-300, -300), (5300, -300), (5300, 5300), (-300, 5300)], 1, 'level ground')])


def ring_height(d):
    """The steep ring's rise over the ground (ours) at distance d from the pen's centre: up 40 per cell, a top 20
    across, down again."""
    a, b = FLOOR, FLOOR + RING
    up = (d - a) / 20.0
    down = (b - d) / 20.0
    return float(np.clip(min(up, down, 1.0), 0.0, 1.0)) * WALL


def pens(e, border):
    """The heights with the pens' walls raised and the field 0 the pens want: (e, bits) on cells (rows j)."""
    e = np.array(e, dtype=float)
    h, w = e.shape
    bits = np.zeros((h, w), bool)
    jj, ii = np.mgrid[0:h, 0:w]
    xs, ys = (ii - border) * mapterrain.CELL, (jj - border) * mapterrain.CELL
    for (x, y), steep, marked in PENS.values():
        d = np.hypot(xs - x, ys - y)
        ring = (d >= FLOOR) & (d <= FLOOR + RING)
        if steep:
            e[ring] += np.vectorize(ring_height)(d[ring])
        if marked:
            near = d <= FLOOR + RING + 2 * mapterrain.CELL
            bits[near] = (terrain_rules.impassable_bits(e, -1e9) | ring)[near] if steep else ring[near]
    return e, bits


def terrain(m):
    """CampNew18's generate (objects, scripts, light, the start), the level ground, then the pens."""
    c18.generate(m)
    previews, _ = platmap.apply(m, _LAYOUT)
    c18.PREVIEWS.update(previews)
    hm = mapterrain.HeightMap(m)
    w, h, b = hm.width, hm.height, hm.border
    e0 = np.array(hm.elev, dtype=float).reshape(h, w) / mapterrain.SCALE
    e, bits = pens(e0, b)
    hm.elev = [max(0, min(65535, int(round(v * mapterrain.SCALE)))) for v in e.ravel()]
    hm.store()
    tiles = mapterrain.Tiles(m, w)
    for j, i in zip(*np.nonzero(bits)):
        tiles.set_bit(terrain_rules.IMPASSABLE, int(i), int(j), True)
    tiles.store()


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
