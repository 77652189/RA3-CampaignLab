"""A probe map for the engine line's blocked-way tests (checks/engine_block.py, docs/engine/pathing.md 6, 7): flat
ground (tier 1), fences on BlendTileData's field 0 (docs/engine/terrain.md 3), every lane its own box.

Each box is 800 x 1000: start 250 south of a wall across the box at y0+500, goal 250 north of it, both at x0+200;
the wall's one way round is a gap at the box's east end (x1-200..x1), about 950 of way round (probe_paths' 'near'
box goes round at 1 100).

  row A (y 300..1300)   'bits': the wall on field 0 (the control); 'built': no field-0 wall, a row of structures
                        stands across instead (the ice wall is a structure: units/icewall.py); 'late': the same row,
                        made by a script a moment after the order (A4's walls come up mid-way)
  row B (y 3000..4000)  'enemy move' / 'enemy attack': the field-0 wall has a second, straight gap GAP_W across on
                        the straight line, plugged by enemy vehicles; the far gap stays open

The player's start (1250, 2500) stays clear. Published: SITES (each lane's start, goal, far gap, plug; ROW: where the
structures of 'built' / 'late' stand), PLAYERS, TEAMS, BOXES, ROW.
"""
import numpy as np

import make_campnew18 as c18
import mapterrain
import platmap
from platmap import Layout, poly
from maps import island
from parts import Site

FENCE = 40.0
W, H = 800.0, 1000.0
GAP_W = 60.0                       # the straight gap the enemy plugs
ROW_STEP = 30.0                    # the structures' spacing along the wall (overlapping: no way between them)
# box: its south-west corner, whether the wall is on field 0, whether it has the straight gap
BOXES = {
    'bits': ((300.0, 300.0), True, False),
    'built': ((1400.0, 300.0), False, False),
    'late': ((2500.0, 300.0), False, False),
    'enemy move': ((300.0, 3000.0), True, True),
    'enemy attack': ((1400.0, 3000.0), True, True),
}


def _wall_y(lane):
    return BOXES[lane][0][1] + H / 2


ROW = {lane: [(BOXES[lane][0][0] + 15.0 + ROW_STEP * k, _wall_y(lane)) for k in range(int((W - 200.0) // ROW_STEP))]
       for lane in ('built', 'late')}

SITES = {k: island.SITES[k] for k in ('island', 'start', 'base factory', 'base power', 'west field')}
for _lane, ((_x0, _y0), _, _) in BOXES.items():
    SITES[f'{_lane} start'] = Site(_x0 + 200.0, _y0 + 250.0, 60.0, f'where the {_lane} lane\'s unit stands')
    SITES[f'{_lane} goal'] = Site(_x0 + 200.0, _y0 + 750.0, 60.0, f'where the {_lane} lane\'s unit is sent')
    SITES[f'{_lane} gap'] = Site(_x0 + W - 100.0, _y0 + H / 2 - 150.0, 60.0, f'the {_lane} box\'s far gap, start side')
    SITES[f'{_lane} wall'] = Site(_x0 + 15.0, _y0 + H / 2, 20.0, f'the {_lane} wall\'s west end (ROW runs east)')
for _lane in ('enemy move', 'enemy attack'):
    _x0, _y0 = BOXES[_lane][0]
    SITES[f'{_lane} plug'] = Site(_x0 + 200.0, _y0 + H / 2, 30.0, 'the straight gap, where the enemy stands')
CUT = (3900.0 + 120.0, 3500.0 - 140.0, 3900.0 + 300.0, 3500.0 + 140.0)    # 'seal cut': a closed ring of field-0 ground
for _k, _y in (('move', 700.0), ('idle', 1400.0), ('idle open', 2100.0), ('spawn', 2800.0), ('cut', 3500.0),
               ('row', 4200.0)):                                                  # checks/engine_seal.py
    SITES[f'seal {_k}'] = Site(3900.0, _y, 60.0, f'the {_k} seal test: where its units stand (open ground)')
    SITES[f'seal {_k} goal'] = Site(4500.0, _y, 60.0, f'the {_k} seal test: 600 east of its start')
for _k, _x, _y in (('erow', 2800.0, 1800.0), ('tank', 2800.0, 2600.0), ('arty', 2800.0, 3400.0),
                   ('attack', 2800.0, 4200.0), ('aa', 4600.0, 1400.0), ('aaopen', 4600.0, 2300.0),
                   ('tankopen', 4600.0, 3300.0), ('arty250', 4600.0, 4200.0), ('artytk', 4600.0, 4800.0),
                   ('artyb', 1400.0, 3400.0), ('artybk', 1400.0, 2600.0)):                                   # engine_seal shot-blocking lanes
    SITES[f'seal {_k}'] = Site(_x, _y, 60.0, f'the {_k} seal test: where its shooter stands (open ground)')
for _k, _x in (('ebld', 600.0), ('ebldam', 1300.0)):                              # engine_seal: the enemy's soldier
    SITES[f'seal {_k}'] = Site(_x, 4800.0, 60.0, f'the {_k} seal test: where the enemy soldier stands (open ground)')
SITES['seal ebldam goal'] = Site(2300.0, 4800.0, 60.0, 'the ebldam seal test: where the enemy soldier attack-moves')
SITES['seal pam'] = Site(2800.0, 4800.0, 60.0, 'the pam seal test: where the player\'s soldier stands (open ground)')
SITES['seal pam goal'] = Site(3800.0, 4800.0, 60.0, 'the pam seal test: where the player\'s soldier attack-moves')
PLAYERS = island.PLAYERS
TEAMS = island.TEAMS

_LAYOUT = Layout(shapes=[poly([(-300, -300), (5300, -300), (5300, 5300), (-300, 5300)], 1, 'level ground')])


def walls(h, w, border):
    """Field 0's cells (rows j): every box's fence, and its inner wall where it is on field 0 (less its gaps)."""
    jj, ii = np.mgrid[0:h, 0:w]
    xs, ys = (ii - border) * mapterrain.CELL, (jj - border) * mapterrain.CELL
    on = np.zeros((h, w), bool)

    def rect(x0, y0, x1, y1):
        return (xs >= x0) & (xs <= x1) & (ys >= y0) & (ys <= y1)

    for (x0, y0), bits, straight in BOXES.values():
        x1, y1, wy = x0 + W, y0 + H, y0 + H / 2
        on |= rect(x0 - FENCE, y0 - FENCE, x1 + FENCE, y0) | rect(x0 - FENCE, y1, x1 + FENCE, y1 + FENCE)
        on |= rect(x0 - FENCE, y0, x0, y1) | rect(x1, y0, x1 + FENCE, y1)
        if bits:
            wall = rect(x0, wy - FENCE / 2, x1, wy + FENCE / 2) & ~rect(x1 - 200.0, -1e9, x1, 1e9)
            if straight:
                wall &= ~rect(x0 + 200.0 - GAP_W / 2, -1e9, x0 + 200.0 + GAP_W / 2, 1e9)
            on |= wall
    cx0, cy0, cx1, cy1 = CUT                  # a closed box (walls 40 thick, 100 inside) on field 0: nothing walks in
    on |= rect(cx0, cy0, cx1, cy1) & ~rect(cx0 + 40, cy0 + 40, cx1 - 40, cy1 - 40)
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


SCENERY = []                               # none: contract.map_design lints a map with ground() by its scenery


def ground():
    """The heights as the simulator asks them (sim.Ground): level ground, without the map."""
    import platprops
    w, h, b = platmap.CONTAINER
    return platprops.Ground(e=np.full((h, w), platmap.TIER[1], np.float32))


def impassable():
    """Field 0's cells as the simulator asks them (sim.Ground): the fences and the field-0 walls."""
    w, h, b = platmap.CONTAINER
    return walls(h, w, b)


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
