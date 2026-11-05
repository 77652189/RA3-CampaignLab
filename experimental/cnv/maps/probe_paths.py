"""A probe map for the engine line's pathing tests (checks/engine_paths.py, docs/engine/pathing.md): flat ground
(tier 1), walls drawn with BlendTileData's field 0 (the one bit the game walks by: docs/engine/terrain.md 3).

  row A (y 300..1300)   'far' box: a wall across it with one gap at the far east end -- start and goal sit either
                        side of the wall at the west end, so the only way round is about 8 200 long for 500 straight
  row B (y 3000..4000)  'mid' box (the way round about 3 400), near box (about 1 100), and 'shut': a closed ring
                        with the goal inside it (nobody can get there)
  between (y 1500..2800, x >= 2000)  'team' and 'attack team' lanes (open ground, a fast and a slow unit ordered as
                        one team), 'narrow' and 'wide' boxes: a wall across with a gap 50 / 150 across in its middle

Every lane is its own box (fenced with field 0) so no way round one leaks into another. The player's start (1250,
2500) stays clear. Published: SITES (each lane's start, goal and the gap's side), PLAYERS, TEAMS, BOXES, GAPS.
"""
import numpy as np

import make_campnew18 as c18
import mapterrain
import platmap
from platmap import Layout, poly
from maps import island
from parts import Site

FENCE = 40.0                       # a fence's / inner wall's thickness (world units, 4 cells)
RING = 60.0                        # 'shut': the ring's width, round a floor FLOOR across its radius
FLOOR = 100.0
# box: (x0, y0, x1, y1), the inner wall's y, its gap (x0, x1) or None
BOXES = {
    'far': ((300.0, 300.0, 4700.0, 1300.0), 800.0, (4500.0, 4700.0)),
    'mid': ((300.0, 3000.0, 2300.0, 4000.0), 3500.0, (2100.0, 2300.0)),
    'near': ((2600.0, 3000.0, 3400.0, 4000.0), 3500.0, (3200.0, 3400.0)),
    'narrow': ((3100.0, 1500.0, 3800.0, 2800.0), 2150.0, (3425.0, 3475.0)),
    'wide': ((3900.0, 1500.0, 4700.0, 2800.0), 2150.0, (4225.0, 4375.0)),
    # row C (y 4150..4950): the detour limit between near and mid -- start / goal 200 either side of the wall at
    # x0+200, the gap's middle 877 / 1285 east of them, so the way round is about 1 800 / 2 600 for 400 straight
    'd1800': ((300.0, 4150.0, 1477.0, 4950.0), 4550.0, (1277.0, 1477.0)),
    'd2600': ((1700.0, 4150.0, 3285.0, 4950.0), 4550.0, (3085.0, 3285.0)),
    'd1400': ((3400.0, 4150.0, 4371.0, 4950.0), 4550.0, (4171.0, 4371.0)),     # 671 east: about 1 400
}
SHUT = (4200.0, 3600.0)            # the closed ring's centre
GAPS = {k: g for k, (_, _, g) in BOXES.items()}
# lane: (start, goal)
LANES = {
    'far': ((500.0, 550.0), (500.0, 1050.0)),
    'mid': ((500.0, 3250.0), (500.0, 3750.0)),
    'near': ((2800.0, 3250.0), (2800.0, 3750.0)),
    'shut': ((4200.0, 3150.0), SHUT),
    'team': ((2200.0, 1600.0), (2200.0, 2700.0)),
    'attack team': ((2700.0, 1600.0), (2700.0, 2700.0)),
    'narrow': ((3450.0, 1700.0), (3450.0, 2600.0)),
    'wide': ((4300.0, 1700.0), (4300.0, 2600.0)),
    'd1800': ((500.0, 4350.0), (500.0, 4750.0)),
    'd2600': ((1900.0, 4350.0), (1900.0, 4750.0)),
    'd1400': ((3600.0, 4350.0), (3600.0, 4750.0)),
}

SITES = {k: island.SITES[k] for k in ('island', 'start', 'base factory', 'base power', 'west field')}
for _name, ((_sx, _sy), (_gx, _gy)) in LANES.items():
    SITES[f'{_name} start'] = Site(_sx, _sy, 60.0, f'where the {_name} lane\'s units stand')
    SITES[f'{_name} goal'] = Site(_gx, _gy, 60.0, f'where the {_name} lane\'s units are sent')
for _name, ((_x0, _y0, _x1, _y1), _wy, (_g0, _g1)) in BOXES.items():
    SITES[f'{_name} gap'] = Site((_g0 + _g1) / 2, _wy - 150.0, 60.0, f'the {_name} box\'s gap, on the start side')
SITES['shut near'] = Site(SHUT[0], SHUT[1] - FLOOR - RING - 60.0, 50.0, "outside the ring, the start's side")
SITES['shut far'] = Site(SHUT[0], SHUT[1] + FLOOR + RING + 60.0, 50.0, 'outside the ring, the far side')
PLAYERS = island.PLAYERS
TEAMS = island.TEAMS

_LAYOUT = Layout(shapes=[poly([(-300, -300), (5300, -300), (5300, 5300), (-300, 5300)], 1, 'level ground')])


def walls(h, w, border):
    """Field 0's cells (rows j): every box's fence and inner wall (less its gap), and the ring round SHUT."""
    jj, ii = np.mgrid[0:h, 0:w]
    xs, ys = (ii - border) * mapterrain.CELL, (jj - border) * mapterrain.CELL
    on = np.zeros((h, w), bool)

    def rect(x0, y0, x1, y1):
        return (xs >= x0) & (xs <= x1) & (ys >= y0) & (ys <= y1)

    for (x0, y0, x1, y1), wy, (g0, g1) in BOXES.values():
        on |= rect(x0 - FENCE, y0 - FENCE, x1 + FENCE, y0) | rect(x0 - FENCE, y1, x1 + FENCE, y1 + FENCE)
        on |= rect(x0 - FENCE, y0, x0, y1) | rect(x1, y0, x1 + FENCE, y1)
        on |= rect(x0, wy - FENCE / 2, x1, wy + FENCE / 2) & ~rect(g0, -1e9, g1, 1e9)
    d = np.hypot(xs - SHUT[0], ys - SHUT[1])
    on |= (d >= FLOOR) & (d <= FLOOR + RING)
    return on


def terrain(m):
    """CampNew18's generate (objects, scripts, light, the start), the level ground, then the walls on field 0."""
    c18.generate(m)
    previews, _ = platmap.apply(m, _LAYOUT)
    c18.PREVIEWS.update(previews)
    hm = mapterrain.HeightMap(m)
    tiles = mapterrain.Tiles(m, hm.width)
    for j, i in zip(*np.nonzero(walls(hm.height, hm.width, hm.border))):
        tiles.set_bit(0, int(i), int(j), True)
    tiles.store()


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
