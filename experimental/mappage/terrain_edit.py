"""The map page's terrain editor, Python side (ADR 0017: the page only stores proposals). A terrain proposal is a list
of brush strokes; this file says what a stroke does to the ground (the height part is platmap.brush, which a new map's
Layout.brushes run through at build time too), and terrain.js (the page's live preview) is its mirror, held to it by tests/test_mappage_terrain.py. The rules after the heights move -- which cells
get the impassable bit, what is flat enough to build on, the unit conversions -- are the engine line's
experimental/campaign/terrain_rules.py, read here and handed to the page as numbers (params()), never retyped.

A stroke: {op, r, s, dabs, height?}
  op      'raise' | 'lower' | 'flatten' (heights) or 'block' | 'unblock' (the impassable bit, field 0, painted)
  r       brush radius, world units; a dab moves the cells closer than r to its centre
  s       strength, our height units (elevation / 16) per dab at the centre, falling off linearly to 0 at r
  dabs    [[x, y], ...] world points, in the order they were laid
  height  flatten only: the level (ours) the cells are pulled toward, by at most s * weight per dab
After a height stroke the heights are stored as the map stores them (round(ours * 16) / 16, 0..65535 raw) and field 0
is recomputed over the cells that moved and a ring round them (terrain_rules.apply_edit); painted cells elsewhere stay.
A paint stroke sets or clears field 0 on the cells within r of each dab and touches no height.

Arithmetic is kept to what JS does the same way (sqrt, not hypot; floor(v + .5) for the stored height; Python's
round-half-even where terrain_rules / platmap use round()) so the page and this file agree to the bit.
"""
import contextlib
import math

import numpy as np

HEIGHT_OPS = ('raise', 'lower', 'flatten')
PAINT_OPS = ('block', 'unblock')
OPS = HEIGHT_OPS + PAINT_OPS


def _rules():
    import terrain_rules                         # experimental/campaign, on the path build.py set
    return terrain_rules


class Ground:
    """A map's height field (ours, rows j, columns i), its impassable bit (field 0) and the numbers to place it."""

    def __init__(self, e, bits, border, waterline, cell=10.0):
        self.e = np.asarray(e, dtype=float)
        self.bits = np.asarray(bits, dtype=bool)
        self.h, self.w = self.e.shape
        self.b = int(border)
        self.waterline = float(waterline)
        self.cell = float(cell)

    def copy(self):
        return Ground(self.e.copy(), self.bits.copy(), self.b, self.waterline, self.cell)

    def cell_of(self, x, y):
        """The cell a world point is on, the way platmap.level_enough picks it (round: half to even)."""
        return int(round(x / self.cell)) + self.b, int(round(y / self.cell)) + self.b


def from_map(mf):
    """The ground of a written map file (the map a build writes: mappage.built_map)."""
    import mapterrain
    import newmap
    hm = mapterrain.HeightMap(mf)
    e = np.array(hm.elev, dtype=float).reshape(hm.height, hm.width) / mapterrain.SCALE
    t = mapterrain.Tiles(mf, hm.width)
    rows = np.frombuffer(bytes(t.extra[:t.row_bytes * t.height]), dtype=np.uint8).reshape(t.height, t.row_bytes)
    bits = np.unpackbits(rows, axis=1, bitorder='little')[:, :hm.width].astype(bool)
    return Ground(e, bits, hm.border, newmap.WATERLINE, mapterrain.CELL)


def params(g):
    """The numbers the page's preview runs on, all from terrain_rules and the map (the page types none of its own)."""
    tr = _rules()
    return {'cell': g.cell, 'w': g.w, 'h': g.h, 'b': g.b, 'waterline': g.waterline, 'steep': tr.STEEP,
            'build_variation': tr.BUILD_VARIATION, 'world_per_ours': tr.WORLD_PER_OURS, 'raw_per_ours': tr.RAW_PER_OURS,
            'raw_max': 65535, 'ring': 1}


def _window(g, x, y, r):
    """The cells within the square round a dab, and each one's distance to the dab's centre."""
    c = g.cell
    i0, i1 = max(0, math.floor((x - r) / c) + g.b), min(g.w - 1, math.ceil((x + r) / c) + g.b)
    j0, j1 = max(0, math.floor((y - r) / c) + g.b), min(g.h - 1, math.ceil((y + r) / c) + g.b)
    if i0 > i1 or j0 > j1:
        return None, None
    dx = (np.arange(i0, i1 + 1) - g.b) * c - x
    dy = (np.arange(j0, j1 + 1) - g.b) * c - y
    d = np.sqrt(dx[None, :] * dx[None, :] + dy[:, None] * dy[:, None])
    return (slice(j0, j1 + 1), slice(i0, i1 + 1)), d


def dabs(d):
    """A stroke's dabs as stored: flat [x0, y0, x1, y1, ...] (the page's store takes no array of arrays), or pairs."""
    d = list(d)
    if d and isinstance(d[0], (list, tuple)):
        return [(float(x), float(y)) for x, y in d]
    return [(float(d[k]), float(d[k + 1])) for k in range(0, len(d) - 1, 2)]


def apply_stroke(g, stroke):
    """One stroke applied to g in place; returns the cells whose stored height changed (bool array)."""
    op, r, s = stroke['op'], float(stroke['r']), float(stroke.get('s', 0.0))
    if op not in OPS:
        raise ValueError(f'unknown terrain op {op!r}')
    changed = np.zeros(g.e.shape, dtype=bool)
    if op in PAINT_OPS:
        for x, y in dabs(stroke['dabs']):
            win, d = _window(g, float(x), float(y), r)
            if win is not None:
                g.bits[win][d <= r] = op == 'block'
        return changed
    import platmap                               # the stroke rule itself (a new map's Layout.brushes use it too)
    tr = _rules()
    e0 = g.e.copy()
    e = platmap.brush(g.e.astype(float), dict(stroke, r=r, s=s), g.b, g.cell)
    raw = np.clip(np.floor(e * tr.RAW_PER_OURS + 0.5), 0, 65535)
    g.e = raw / tr.RAW_PER_OURS
    changed = g.e != e0
    g.bits = tr.apply_edit(g.e, g.bits, changed, g.waterline)
    return changed


def apply_proposals(g, proposals):
    """Every terrain proposal's strokes in order on a copy of g; returns (the new ground, cells whose height moved)."""
    out = g.copy()
    moved = np.zeros(g.e.shape, dtype=bool)
    for p in proposals:
        for st in p.get('strokes', ()):
            moved |= apply_stroke(out, st)
    return out, moved


def flat_sites(g, sites):
    """Per site meant to be built or cast on: whether its square is flat enough (platmap.level_enough's way)."""
    tr = _rules()
    out = {}
    for k, s in sites.items():
        for what, side in (('build', getattr(s, 'build', 0) or 0), ('cast', 2 * (getattr(s, 'cast', 0) or 0))):
            if side:
                i, j = g.cell_of(s.x, s.y)
                out[(k, what)] = bool(tr.flat_enough(g.e, i, j, side))
    return out


@contextlib.contextmanager
def lint_on(g):
    """Inside: the map's design lint (platmap.lint, through contract.map_design) reads ground g instead of the heights
    its layout makes -- g's heights, and g's painted field 0 (cells blocked or opened by hand, against what the slope
    gives) on top of platmap.walkable. Nothing in platmap changes; its two lookups are swapped for the block's length
    and contract's per-map cache is set aside."""
    import contract
    import platmap
    tr = _rules()
    by_slope = tr.impassable_bits(g.e, g.waterline)
    shut, opened = g.bits & ~by_slope, ~g.bits & by_slope
    dry = g.e > g.waterline + 10
    heights, walkable = platmap.heights, platmap.walkable

    def edited_heights(layout, w, h, b):
        e, problems = heights(layout, w, h, b)
        if e.shape != g.e.shape:
            raise ValueError(f'ground {g.e.shape} is not the layout\'s {e.shape}')
        return g.e.copy(), problems

    def edited_walkable(layout, objects=(), dims=platmap.CONTAINER, e=None):
        ok = walkable(layout, objects, dims, g.e if e is None else e)
        return (ok & ~shut) | (opened & dry)

    cache = dict(contract._DESIGN)
    contract._DESIGN.clear()
    platmap.heights, platmap.walkable = edited_heights, edited_walkable
    try:
        yield
    finally:
        platmap.heights, platmap.walkable = heights, walkable
        contract._DESIGN.clear()
        contract._DESIGN.update(cache)


def encode(g):
    """The ground for the page: raw elevations (u16 little-endian) and field 0 packed per row (little-endian bits), base64."""
    import base64
    tr = _rules()
    raw = np.clip(np.floor(g.e * tr.RAW_PER_OURS + 0.5), 0, 65535).astype('<u2')
    packed = np.packbits(g.bits, axis=1, bitorder='little')
    return {'elev': base64.b64encode(raw.tobytes()).decode(), 'bits': base64.b64encode(packed.tobytes()).decode()}


def summary(p, g0, g1):
    """One proposal's effect in numbers: the box its brushes cover, heights moved, field 0 set and cleared."""
    pts = [d for st in p.get('strokes', ()) for d in dabs(st['dabs'])]
    rad = max((float(st['r']) for st in p.get('strokes', ())), default=0.0)
    if not pts:
        return None
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    box = (min(xs) - rad, min(ys) - rad, max(xs) + rad, max(ys) + rad)
    diff = g1.e - g0.e
    return {'box': box, 'ops': [st['op'] for st in p.get('strokes', ())],
            'moved': int((diff != 0).sum()), 'up': float(diff.max()), 'down': float(diff.min()),
            'blocked': int((g1.bits & ~g0.bits).sum()), 'opened': int((~g1.bits & g0.bits).sum())}
