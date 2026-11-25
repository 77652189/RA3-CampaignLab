"""maps/probe_air.py with one change: a dry dam across its sea trench (round 252, benches/movement/pathing/checks.py#engine_dam). The dam runs
west to east over the whole trench at y DAM_Y (DAM_HALF either side, back up to the level ground), so the trench is two
pools -- south y 3050..DAM_Y - DAM_HALF, north DAM_Y + DAM_HALF..3550 -- and nothing that swims gets from one to the
other: a ship's way across is a jump over the dam. Everything else (lanes, sites, the player's start) as probe_air.
Published: SITES (probe_air's), PLAYERS, TEAMS, DAM_Y, DAM_HALF, POOL_S / POOL_N (the pools' x0, x1, y0, y1)."""
import numpy as np

import make_campnew18 as c18
import mapterrain
import platmap
import terrain_rules
from maps import probe_air

DAM_Y, DAM_HALF = 3250.0, 30.0
_X0, _X1, _TY = probe_air.TRENCH
POOL_S = (_X0 + probe_air.BANK, _X1 - probe_air.BANK, _TY - probe_air.BAND, DAM_Y - DAM_HALF)
POOL_N = (_X0 + probe_air.BANK, _X1 - probe_air.BANK, DAM_Y + DAM_HALF, _TY + probe_air.BAND)
SITES = dict(probe_air.SITES)
PLAYERS = probe_air.PLAYERS
TEAMS = probe_air.TEAMS
SCENERY = []


def shape(e, border):
    """probe_air's heights, then the dam: the trench's cells within DAM_HALF of DAM_Y back to the level ground."""
    e0 = np.array(e, dtype=float)
    e, face = probe_air.shape(e0, border)
    h, w = e.shape
    jj, ii = np.mgrid[0:h, 0:w]
    xs, ys = (ii - border) * mapterrain.CELL, (jj - border) * mapterrain.CELL
    dam = (np.abs(ys - DAM_Y) <= DAM_HALF) & (xs >= _X0 - mapterrain.CELL) & (xs <= _X1 + mapterrain.CELL)
    e[dam] = e0[dam]
    return e, face


def terrain(m):
    """probe_air's terrain with the dam."""
    c18.generate(m)
    previews, _ = platmap.apply(m, probe_air._LAYOUT)
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
    """The heights as the simulator asks them (sim.Ground): probe_air's with the dam."""
    import platprops
    w, h, b = platmap.CONTAINER
    e, _ = shape(np.full((h, w), probe_air.GROUND, np.float32), b)
    return platprops.Ground(e=e.astype(np.float32))


def like(m, objs, tmpl):
    return probe_air.like(m, objs, tmpl)
