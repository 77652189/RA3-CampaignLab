"""A probe map for the engine line's air tests (checks/engine_air.py, missions/air_bench.py): level ground (tier 1,
340 ours, the water stands at 320), and on it, 1 200 apart west to east at x 1700 -> 2900:

  y 1500  'air flat'   nothing: flat ground all the way
  y 3300  'air sea'    a trench across x 2100..2500 (about 400 wide, floor 250 ours = sea, banks 60 wide): ground units
                       cannot cross it
  y 4100  'air cliff'  from x 2500 east a plateau 115 higher (tier 2), its face two cells wide with field 0 on it:
                       S low, E high

and two open spots for the weapon tests: 'air B' (4000, 1500) and 'air D' (4000, 900). The player's start (1250, 2500)
stays clear. Published: SITES (S / E of each lane, the two spots), PLAYERS, TEAMS.
"""
import numpy as np

import make_campnew18 as c18
import mapterrain
import platmap
import terrain_rules
from platmap import Layout, poly
from maps import island
from parts import Site

GROUND = platmap.TIER[1]
PLATEAU = platmap.TIER[2] - GROUND
TRENCH = (2100.0, 2500.0, 3300.0)          # x0, x1, y: the trench's span and lane
TRENCH_DEPTH = GROUND - 250.0
BANK = 60.0
CLIFF = (2500.0, 4100.0)                   # the face's x, the lane's y
BAND = 250.0                               # a lane's half width in y that its terrain feature covers

SITES = {k: island.SITES[k] for k in ('island', 'start', 'base factory', 'base power', 'west field')}
for _n, _y in (('flat', 1500.0), ('sea', 3300.0), ('cliff', 4100.0)):
    SITES[f'air {_n} S'] = Site(1700.0, _y, 60.0, f'the west end of the {_n} lane')
    SITES[f'air {_n} E'] = Site(2900.0, _y, 60.0, f'the east end of the {_n} lane, 1 200 east of S')
SITES['air B'] = Site(4000.0, 1500.0, 250.0, 'open flat ground for the anti-air range tests')
SITES['air D'] = Site(4000.0, 900.0, 250.0, 'open flat ground for the helicopter-against-ground test')
PLAYERS = island.PLAYERS
TEAMS = island.TEAMS
SCENERY = []                               # none: contract.map_design lints a map with ground() by its scenery

_LAYOUT = Layout(shapes=[poly([(-300, -300), (5300, -300), (5300, 5300), (-300, 5300)], 1, 'level ground')])


def shape(e, border):
    """The heights with the trench dug and the plateau raised: (e, field 0 cells) on cells (rows j)."""
    e = np.array(e, dtype=float)
    h, w = e.shape
    jj, ii = np.mgrid[0:h, 0:w]
    xs, ys = (ii - border) * mapterrain.CELL, (jj - border) * mapterrain.CELL
    x0, x1, ty = TRENCH
    lane = np.abs(ys - ty) <= BAND
    ramp = np.clip(np.minimum(xs - x0, x1 - xs) / BANK, 0.0, 1.0)
    e[lane] -= (ramp * TRENCH_DEPTH)[lane]
    fx, fy = CLIFF
    lane = np.abs(ys - fy) <= BAND
    rise = np.clip((xs - (fx - mapterrain.CELL)) / (2 * mapterrain.CELL), 0.0, 1.0)
    e[lane] += (rise * PLATEAU)[lane]
    face = lane & (np.abs(xs - fx) <= 2 * mapterrain.CELL)
    return e, face


def terrain(m):
    """CampNew18's generate (objects, scripts, light, the start), the level ground, then the trench and the cliff."""
    c18.generate(m)
    previews, _ = platmap.apply(m, _LAYOUT)
    c18.PREVIEWS.update(previews)
    hm = mapterrain.HeightMap(m)
    w, h, b = hm.width, hm.height, hm.border
    e0 = np.array(hm.elev, dtype=float).reshape(h, w) / mapterrain.SCALE
    e, face = shape(e0, b)
    hm.elev = [max(0, min(65535, int(round(v * mapterrain.SCALE)))) for v in e.ravel()]
    hm.store()
    tiles = mapterrain.Tiles(m, w)
    for j, i in zip(*np.nonzero(face)):
        tiles.set_bit(terrain_rules.IMPASSABLE, int(i), int(j), True)
    tiles.store()


def ground():
    """The heights as the simulator asks them (sim.Ground): level ground, the trench and the plateau, without the map."""
    import platprops
    w, h, b = platmap.CONTAINER
    e, _ = shape(np.full((h, w), GROUND, np.float32), b)
    return platprops.Ground(e=e.astype(np.float32))


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
