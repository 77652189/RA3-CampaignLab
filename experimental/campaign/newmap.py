"""Generate a map's content from scratch inside a template .map (CampNew18 uses Heidelberg's dimensions and
terrain texture set, everything else is ours): terrain, water, ground textures + blends, passability, objects,
waypoints, scripts, objectives, time of day.

Heights here are elevation / 16 (mapterrain). Heidelberg's water area says 200 but cells only stick out above
~285 on that scale -- consistent with real height = elevation * 0.04375 (= 200 at 285.7); WATERLINE uses that.
World units: a cell is 10, world (0, 0) is cell (border, border).
"""
from functools import lru_cache
from itertools import product
import math
import random
import struct

import numpy as np

import mapterrain
import mapxml
from mapscript import Node

WATERLINE = 285.7


def value_noise(seed, cells):
    """Smooth 2-D noise in [0, 1]: random values on a grid of `cells` spacing, cosine-interpolated."""
    rnd = random.Random(seed)
    grid = {}

    def at(gx, gy):
        if (gx, gy) not in grid:
            grid[(gx, gy)] = rnd.random()
        return grid[(gx, gy)]

    def f(x, y):
        gx, gy = math.floor(x / cells), math.floor(y / cells)
        fx, fy = x / cells - gx, y / cells - gy
        sx, sy = (1 - math.cos(fx * math.pi)) / 2, (1 - math.cos(fy * math.pi)) / 2
        a = at(gx, gy) + (at(gx + 1, gy) - at(gx, gy)) * sx
        b = at(gx, gy + 1) + (at(gx + 1, gy + 1) - at(gx, gy + 1)) * sx
        return a + (b - a) * sy
    return f


def _noise_axis(points, cells):
    pos = points / cells
    grid = np.floor(pos).astype(np.intp)
    angles = (pos - grid) * math.pi
    # Keep the scalar math.cos rounding used by value_noise.
    cosine = np.fromiter(map(math.cos, angles.flat), dtype=np.float64, count=angles.size)
    return grid - grid.min(), (1.0 - cosine.reshape(angles.shape)) / 2.0


def _noise_field(seed, cells, x, y):
    gx, sx = _noise_axis(x, cells)
    gy, sy = _noise_axis(y, cells)
    stride = int(gx.max()) + 2
    tiles = gy * stride + gx
    lattice = np.empty((int(gy.max()) + 2) * stride, dtype=np.float64)
    # Visiting a tile again draws nothing. Visit each tile at its first row-major
    # sample, and each corner in value_noise's order, to reproduce the RNG stream.
    first = np.sort(np.unique(tiles, return_index=True)[1])
    rnd = random.Random(seed)
    seen = set()
    for k in tiles.ravel()[first].tolist():
        for corner in (k, k + 1, k + stride, k + stride + 1):
            if corner not in seen:
                lattice[corner] = rnd.random()
                seen.add(corner)
    lo = lattice[tiles]
    hi = lattice[tiles + stride]
    a = lo + (lattice[tiles + 1] - lo) * sx
    b = hi + (lattice[tiles + stride + 1] - hi) * sx
    return a + (b - a) * sy


def _coast_geometry(dx, dy):
    # Keep scalar trig and hypot so the coast samples and beach heights round as before.
    for y in dy:
        for x in dx:
            ang = math.atan2(y, x)
            yield 1000 + 600 * math.cos(ang), 1000 + 600 * math.sin(ang), math.hypot(x, y)


@lru_cache(maxsize=1)
def _island_field(w, h, border, cell, seed, cx, cy, radius):
    """Keep the last pure field in this process for terrain and scenery to share."""
    x = (np.arange(w) - border) * cell
    y = (np.arange(h) - border) * cell
    geometry = np.fromiter(_coast_geometry((x - cx).tolist(), (y - cy).tolist()),
                           dtype=np.dtype((np.float64, 3)), count=w * h).reshape(h, w, 3)
    coast = _noise_field(seed, 700.0, geometry[:, :, 0], geometry[:, :, 1])
    r = radius * (0.75 + 0.5 * coast)
    land = np.clip((1.0 - geometry[:, :, 2] / r) / 0.12, 0.0, 1.0)
    rough = _noise_field(seed + 1, 260.0, x[None, :], y[:, None])
    hills = _noise_field(seed + 2, 900.0, x[None, :], y[:, None])
    hill = np.maximum(0.0, hills - 0.55) / 0.45
    field = 230.0 + land * (95.0 + 25 * rough + 140 * hill * hill * land)
    field.setflags(write=False)
    return field


def island_heights(hm, seed=7, center=None, radius=1800.0):
    """Sea everywhere, one island: noisy coastline, rolling land with a few hills. Returns {(i, j): height}."""
    w, h, border = hm.width, hm.height, hm.border
    cell = mapterrain.CELL
    size = (w - 2 * border) * cell
    cx, cy = center or (size / 2, size / 2)
    if w <= 0 or h <= 0:
        return {}
    if radius == 0:
        raise ZeroDivisionError('float division by zero')
    field = _island_field(w, h, border, cell, seed, cx, cy, radius)
    return {(i, j): height for (j, i), height in zip(product(range(h), range(w)), field.ravel().tolist())}


def texture_for(height, slope, x, y, patch):
    if height < WATERLINE - 12:
        return 'Dirt_Yucatan01'                 # sea floor
    if height < WATERLINE + 10:
        return 'Sand_SantaMonica01'             # beach
    if slope > 9:
        return 'Rock_Yucatan01'
    if patch(x, y) > 0.8:
        return 'Dirt_Yucatan04'
    return 'Grass_Heidelberg02' if patch(x + 3000, y) > 0.6 else 'Grass_Heidelberg01'


# blend order: a cell takes the highest-ranked neighbouring texture above its own as its blend
RANK = ['Rock_Yucatan01', 'Grass_Heidelberg01', 'Grass_Heidelberg02', 'Dirt_Yucatan04', 'Sand_SantaMonica01',
        'Dirt_Yucatan01']


def paint_terrain(m, hm, tiles, seed=11):
    patch = value_noise(seed, 150.0)
    w, h, b = hm.width, hm.height, hm.border
    grid = {}
    for j in range(h):
        for i in range(w):
            e = hm.get(i, j)
            slope = max(abs(hm.get(min(w - 1, max(0, i + a)), min(h - 1, max(0, j + c))) - e)
                        for a, c in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            grid[(i, j)] = texture_for(e, slope, (i - b) * 10.0, (j - b) * 10.0, patch)
            # passability: steep dry ground is impassable (field 0, as on retail maps)
            tiles.set_bit(0, i, j, slope > 9 and e > WATERLINE)
    return paint_grid(tiles, grid)


def paint_grid(tiles, grid, rank=None):
    """Paint {(i, j): texture} and blend each cell's edge with the highest-ranked neighbouring texture above its
    own (RANK order; textures not in it rank last). Returns ({texture: cells}, cells blended)."""
    rank = rank or RANK
    order = lambda t: rank.index(t) if t in rank else len(rank)      # noqa: E731
    by_tex = {}
    for c, t in grid.items():
        by_tex.setdefault(t, []).append(c)
    for t, cells in by_tex.items():
        tiles.paint(cells, t)
    blended = 0
    for (i, j), own in grid.items():
        near = {}
        for d, (di, dj) in tiles.STEP.items():
            t = grid.get((i + di, j + dj))
            if t and order(t) < order(own):
                near.setdefault(t, set()).add(d)
        if not near:
            continue
        top = min(near, key=order)
        for need, (byte, flags, two) in tiles.SIDES:
            if set(need) <= near[top]:
                direction = [0, 0, 0, 0]
                direction[byte] = 1
                tiles.blend(i, j, top, direction, flags, two)
                blended += 1
                break
    return {t: len(c) for t, c in by_tex.items()}, blended


def set_water(m, x0, y0, x1, y1):
    """The (single) standing water area becomes the rectangle (x0, y0)-(x1, y1); its other settings stay."""
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    node = next(n for _, n in m.walk() if n.name == 'StandingWaterAreas')
    p, tail = _water_style(node.head)
    node.head = node.head[:p] + _water_points(pts) + tail


def _water_style(d):
    p = 8
    for _ in range(2):
        p += 2 + struct.unpack_from('<H', d, p)[0]
    p += 5
    for _ in range(2):
        p += 2 + struct.unpack_from('<H', d, p)[0]
    k = struct.unpack_from('<I', d, p)[0]
    return p, d[p + 4 + 8 * k:]


def _water_points(points):
    return struct.pack('<I', len(points)) + b''.join(struct.pack('<ff', *q) for q in points)


def set_water_area(m, points, level):
    """Write the global plane and its standing-water polygon, using the container's water style."""
    standing = next(n for _, n in m.walk() if n.name == 'StandingWaterAreas')
    if points:
        if struct.unpack_from('<I', standing.head)[0] != 1:
            raise ValueError('standing water needs a container with one water style')
        p, tail = _water_style(standing.head)
        standing.head = standing.head[:p] + _water_points(points) + struct.pack('<I', level) + tail[4:]
    else:
        standing.head = struct.pack('<I', 0)
    for _, node in m.walk():
        if node.name == 'GlobalWaterSettings':
            node.head = struct.pack('<If', bool(points), level)
        elif node.name in ('RiverAreas', 'StandingWaveAreas'):
            node.head = struct.pack('<I', 0)


def object_node(m, like_props, flags, template, x, y, z=0.0, angle=0.0, **props):
    """An Object node with properties copied from `like_props` ({key: (type, value)}) and overridden."""
    pr = dict(like_props)
    for k, v in props.items():
        t = pr[k][0] if k in pr else (1 if isinstance(v, int) else 3)
        pr[k] = (t, v)
    raw = template.encode('latin-1')
    head = struct.pack('<ffffI', x, y, z, angle, flags) + struct.pack('<H', len(raw)) + raw + mapxml.encode_props(m, pr)
    return Node('Object', 3, head, [])


def typed_props_of(m, node):
    ln = struct.unpack_from('<H', node.head, 20)[0]
    return mapxml._typed_props(m, node.head, 22 + ln), struct.unpack_from('<I', node.head, 16)[0]


def clear_scripts(m):
    """Empty every player's script list; returns the lists (index 2 runs our scripts, as in CampNew6)."""
    psl = next(n for _, n in m.walk() if n.name == 'PlayerScriptsList')
    for sl in psl.kids:
        sl.kids = []
    return psl.kids


COLORS = {'Dirt_Yucatan01': (40, 70, 95), 'Sand_SantaMonica01': (200, 185, 140), 'Dirt_Yucatan04': (150, 125, 85),
          'Grass_Heidelberg01': (70, 110, 50), 'Grass_Heidelberg02': (85, 120, 55), 'Rock_Yucatan01': (120, 115, 110)}


def preview_tga(hm, tiles, size, bpp):
    """Radar / preview picture of the playable area (TGA, bottom row first, as the retail map pictures):
    ground colour by texture, shaded by height; under water a flat sea colour."""
    b = hm.border
    span = hm.width - 2 * b
    names = {}
    for name, (s, cnt, _) in tiles.textures.items():
        for c in range(s, s + cnt):
            names[c] = name
    body = bytearray()
    for r in range(size):
        j = b + int(r * span / size)
        for q in range(size):
            i = b + int(q * span / size)
            e = hm.get(i, j)
            if e < WATERLINE:
                rgb = (25, 60, 90)
            else:
                base = COLORS.get(names.get(tiles.arrays[0][j * hm.width + i] // 4), (100, 100, 100))
                k = 0.8 + 0.4 * min(1.0, (e - WATERLINE) / 150)
                rgb = tuple(min(255, int(c * k)) for c in base)
            body += bytes((rgb[2], rgb[1], rgb[0])) + (b'\xff' if bpp == 32 else b'')
    head = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, size, size, bpp, 8 if bpp == 32 else 0)
    return head + bytes(body)
