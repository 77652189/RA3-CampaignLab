"""How a map handles its height steps (principles.md P36): the steep faces' share of the land, their thickness, the
textures on them, and the objects standing along them -- retail city maps against ours.

    python -I -X utf8 docs/design/teardowns/data/edge_measure.py osaka heidelberg tokyoharbor work/maps/CampA4.map

An argument ending in .map is one of our builds; anything else is part of a retail map's name. Steep = rise over
6 world units per 10-unit cell (31 degrees, mapstudy.CLIFF); thickness = twice the distance to the face's edge,
sampled on its skeleton (2026-11-03: retail city maps 20, ours 40-60).
"""
import collections
import os
import sys

import numpy as np
from scipy import ndimage
from skimage import morphology

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'campaign'))
import mapstudy as MS  # noqa: E402
import mapterrain  # noqa: E402
import mapscript  # noqa: E402
import mapxml  # noqa: E402
from ra3voice import big  # noqa: E402

STEEP = 6.0             # world units of rise per cell (mapstudy.CLIFF)
NEAR = 3                # cells: an object this close to a steep face stands along it


def measure(m, title):
    hm = mapterrain.HeightMap(m)
    b, W, H = hm.border, hm.width, hm.height
    e = np.array(hm.elev, np.float32).reshape(H, W) * MS.REAL
    water = MS.water_height(m)
    land = e > (water + 0.5) if water is not None else np.ones_like(e, bool)
    inner = np.zeros_like(land)
    inner[b:H - b, b:W - b] = True
    land &= inner
    rise = np.zeros_like(e)
    rise[:, 1:] = np.maximum(rise[:, 1:], abs(np.diff(e, axis=1)))
    rise[1:, :] = np.maximum(rise[1:, :], abs(np.diff(e, axis=0)))
    steep = land & (rise > STEEP)
    sk = morphology.skeletonize(steep)
    thick = 2 * ndimage.distance_transform_edt(steep)[sk] * MS.CELL if sk.any() else np.array([0.0])
    step = (ndimage.maximum_filter(e, 9) - ndimage.minimum_filter(e, 9))[sk] if sk.any() else np.array([0.0])
    tiles = mapterrain.Tiles(m, W)
    tex = collections.Counter(tiles.texture_at(i, j) for j, i in zip(*np.nonzero(steep)))
    near = ndimage.binary_dilation(steep, iterations=NEAR)
    objs = collections.Counter()
    for o in mapxml.objects(m):
        i, j = int(o['x'] / MS.CELL) + b, int(o['y'] / MS.CELL) + b
        if 0 <= i < W and 0 <= j < H and near[j, i]:
            objs[o['template']] += 1
    km, n, s = sk.sum() * MS.CELL / 1000, sum(objs.values()), max(1, steep.sum())
    print(f'== {title}')
    print(f'  steep faces {steep.sum() / land.sum():.1%} of land, {km:.1f} km long, thickness median '
          f'{np.median(thick):.0f} p90 {np.percentile(thick, 90):.0f}, step median {np.median(step):.0f}')
    print('  textures', ', '.join(f'{k}:{v / s:.0%}' for k, v in tex.most_common(5)))
    print(f'  objects along them {n} ({n / max(km, .01):.0f}/km):', ', '.join(f'{k}:{v}' for k, v in objs.most_common(8)))


def main(args):
    for a in args:
        if a.endswith('.map'):
            with open(a, 'rb') as f:
                measure(mapscript.MapFile(f.read()), os.path.basename(a))
            continue
        found = MS.retail_maps([a])
        if not found:
            print(f'== {a}: no retail map')
            continue
        _, arc, n, short = found[0]
        measure(mapscript.MapFile(big.read_files(arc, [n])[n]), short)


if __name__ == '__main__':
    main(sys.argv[1:])
