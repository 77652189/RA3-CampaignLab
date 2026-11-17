"""A probe map for the engine line (checks/engine_bits.py, docs/engine/terrain.md 3): flat ground (tier 1, 340 ours =
212.5 world), and on it two rows of pens -- a round floor 100 across its radius, a ring round it:

  row 1 (y 2500), level rings with some of BlendTileData's eight bit fields set on them (terrain_rules.FIELDS):
    'players'     field 1 (impassable to players, 推断), for the player's units; 'players enemy' the same far east
                  (x 4300, out of the player's units' reach) for the enemy's
    'air'         field 6 (impassable to air, 推断)
    'zero three'  fields 0 and 3 (impassable, and extra passable over it?)
    'zero'        field 0 only (x 4700): the control, for the enemy's units
  row 2 (y 3300), moats dug down to a floor of a given height (ours) -- the water stands at 200 world (GlobalWaterSettings
  and the StandingWaterAreas entry) = 320 ours by the game's height scale (terrain.md 1):
    'moat 270' (169 world), 'moat 300' (187.5), 'moat 315' (197), 'moat 330' (206)

Whether a unit ordered out of a pen gets out answers what each bit field does, and at what height the game's logic
puts the water. No bits are set in row 2; the ground textures stay grass everywhere.

Published: SITES (the start, each pen and the point outside it), PLAYERS, TEAMS, PENS.
"""
import numpy as np

import make_campnew18 as c18
import mapterrain
import platmap
from platmap import Layout, poly
from maps import island
from parts import Site

FLOOR = 100.0                      # a pen's floor radius (world units)
RING = 60.0                        # a level ring's width
SLOPE = 20.0                       # a moat's sides: ours per cell (the game goes by field 0, not slopes: terrain.md 3)
MOAT_BOTTOM = 40.0                 # a moat's flat floor across
GROUND = platmap.TIER[1]
OUT = 280.0                        # the point outside a pen, north of its centre
# name: (centre, bit fields on the ring, moat floor height or None)
PENS = {
    'players': ((2000.0, 2500.0), (1,), None),
    'air': ((2400.0, 2500.0), (6,), None),
    'zero three': ((2800.0, 2500.0), (0, 3), None),
    'players enemy': ((4300.0, 2500.0), (1,), None),
    'zero': ((4700.0, 2500.0), (0,), None),
    'moat 270': ((2000.0, 3300.0), (), 270.0),
    'moat 300': ((2500.0, 3300.0), (), 300.0),
    'moat 315': ((3000.0, 3300.0), (), 315.0),
    'moat 330': ((3500.0, 3300.0), (), 330.0),
}

SITES = {k: island.SITES[k] for k in ('island', 'start', 'base factory', 'base power', 'west field')}
for _name, ((_x, _y), _bits, _floor) in PENS.items():
    SITES[_name] = Site(_x, _y, FLOOR - 20.0, f'the floor of the {_name} pen')
    SITES[f'{_name} out'] = Site(_x, _y + OUT, 60.0, f'open ground north of the {_name} pen')
PLAYERS = island.PLAYERS
TEAMS = island.TEAMS

_LAYOUT = Layout(shapes=[poly([(-300, -300), (5300, -300), (5300, 5300), (-300, 5300)], 1, 'level ground')])


def moat_width(floor):
    """A moat's width: down at SLOPE per cell to `floor`, MOAT_BOTTOM across, up again (world units)."""
    return 2 * (GROUND - floor) / SLOPE * mapterrain.CELL + MOAT_BOTTOM


def moat_depth(d, floor):
    """How far a moat lies below the ground (ours) at distance d past the pen's floor edge."""
    w, depth = moat_width(floor), GROUND - floor
    side = depth / SLOPE * mapterrain.CELL
    return float(np.clip(min(d / side, (w - d) / side, 1.0), 0.0, 1.0)) * depth if 0 <= d <= w else 0.0


def pens(e, border):
    """The heights with the moats dug and the bit fields set on the rings: (e, {field: cells}) on cells (rows j)."""
    e = np.array(e, dtype=float)
    h, w = e.shape
    bits = {}
    jj, ii = np.mgrid[0:h, 0:w]
    xs, ys = (ii - border) * mapterrain.CELL, (jj - border) * mapterrain.CELL
    for (x, y), fields, floor in PENS.values():
        d = np.hypot(xs - x, ys - y)
        if floor is not None:
            moat = (d >= FLOOR) & (d <= FLOOR + moat_width(floor))
            e[moat] -= np.vectorize(lambda r: moat_depth(r - FLOOR, floor))(d[moat])
        ring = (d >= FLOOR) & (d <= FLOOR + RING)
        for f in fields:
            bits[f] = bits.get(f, np.zeros((h, w), bool)) | ring
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
    for field, cells in bits.items():
        for j, i in zip(*np.nonzero(cells)):
            tiles.set_bit(field, int(i), int(j), True)
    tiles.store()


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
