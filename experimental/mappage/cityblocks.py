"""A city sketch for sketch2map: the per-map design file says where the water, the hill, the streets, the big blocks
and the named places are; this module fills every block between the streets the way retail RA3 city maps do
(buildings in rows on the kerb, a back-yard line of fences or bushes, yard props, parking lots, small squares), puts
lamps, boulevard trees and parked cars along the streets, and writes sketch.json and blocks.json.

The design frame is turned 45 degrees: u runs north-west, v north-east; xy(u, v) turns it into world (x east, y
north) round the map's centre. Polygons are handed in world points (build them with P / urect / ucircle); single
points -- sites, special blocks, ramps, put -- are (u, v) unless world=True (or, for a special block, (x, y, 'w')).

    city = City(4600, foot, seed=17, district=fn(x, y, on_hill) -> name, district_kind={name: kind},
                district_zh={name: zh}, alley_axes=fn(cx, cy) -> two unit vectors, kinds={kind: override})
    city.water(poly, what); city.island(poly, what, texture=None); city.hill(poly, what); city.ramp(lo, hi, what)
    city.road(world pts, width, name) / city.road_uv(...); city.mega(name, poly, texture); city.ground(poly, tex, what)
    city.site(code, u, v, zh, what, r, build, cast, world); city.special(pt, kind, name, why, centre=None)
    city.build()          # the blocks, then the street props
    city.put(...); city.clumps(...)    # landmarks, after build (they keep off the slope)
    city.write(folder, name, what, start, fields, bridges)    # sketch.json, blocks.json, two summary lines

foot is the caller's {template: [w, h, ...]} footprint table (not kept in this repository). city.rnd is the one seeded
random stream: the fill, the props and the caller's landmarks all draw from it in that order, so a design run twice
gives the same bytes.
"""
import json
import math
import random
from pathlib import Path

import numpy as np
from scipy import ndimage
from skimage.measure import approximate_polygon, find_contours

CELL = 10
R2 = math.sqrt(2)
GRASS, PAVED, LOT = 'Grass_Heidelberg05', 'Pavement_Heidelberg10', 'Pavement_Heidel03'
SIDEWALK = 'Pavement_Heidelberg11'
ROAD_TEXTURE = 'Pavement_Yucatan01'
TREES = ['HB_Tree02', 'HB_Tree04', 'CC_Tree03']
CARS = ['SM_Auto03', 'CC_Auto01', 'SM_AUTO04']
AXES_SCREEN = ((1, 0), (0, 1))
AXES_TURNED = ((R2 / 2, R2 / 2), (R2 / 2, -R2 / 2))
SMALL = 250             # a block of fewer cells (a sliver between streets) is a little square
BIG = 2500              # a footprint above this (w x h) counts as a building in the summary
# What a block holds. Retail's buildings stand on the kerb (garrison cover within 100 of the street 20-59%) and a
# block holds a few big ones, not many small ones (72-144 garrisonable a map). kind:
# (palette, set back from the street, gap between buildings, share of the block built, rows, inside ground, zh)
KINDS = {
    'rowhouses': (['GE_TOWNHOUSE01', 'SA_House01', 'SA_House02', 'SA_House04_02', 'CCHouse03'], 6, 6, 0.25, 1, GRASS,
                  '排屋'),
    'shops': (['SA_Store01', 'SA_IceCreamShop', 'SA_OrganicDoughnutShoppe', 'SA_TireShop', 'CCHouse03',
               'GE_TOWNHOUSE01'], 4, 8, 0.26, 1, PAVED, '商铺街'),
    'apartments': (['OD_Apartments01', 'OD_Apartments02', 'GE_Apartment01', 'BB_Hotel_01', 'BB_Hotel_02'], 6, 14,
                   0.27, 1, PAVED, '公寓院'),
    'towers': (['NY_Structure_08', 'NY_Structure_01', 'NY_Structure_03', 'NY_Structure_06', 'NY_Structure_07',
                'NY_Building01', 'OD_Apartments01'], 6, 14, 0.32, 1, PAVED, '高楼'),     # all garrisonable
    'warehouses': (['OD_Warehouse02', 'OD_Warehouse01', 'SA_TireShop', 'SA_8BallStation'], 10, 26, 0.24, 1, PAVED,
                   '仓库院'),
    'villas': (['CapeCod_House01', 'SA_House04', 'SA_House02_03', 'SA_Clubhouse01'], 16, 34, 0.15, 1, GRASS, '独栋'),
    'parking': ([], 0, 0, 0.0, 0, LOT, '停车场'),
    'square': ([], 0, 0, 0.0, 0, GRASS, '广场草坪'),
}


# ------------------------------------------------------------------ raster helpers (n x n cells of `cell` units)
def mask_poly(pts, n, cell=CELL):
    from matplotlib.path import Path as MPath
    yy, xx = np.mgrid[0:n, 0:n]
    pts_c = np.c_[(xx.ravel() + 0.5) * cell, (yy.ravel() + 0.5) * cell]
    return MPath(pts).contains_points(pts_c).reshape(n, n)


def mask_road(pts, w, n, cell=CELL):
    yy, xx = np.mgrid[0:n, 0:n]
    X, Y = (xx + 0.5) * cell, (yy + 0.5) * cell
    m = np.zeros((n, n), bool)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        t = np.clip(((X - x0) * dx + (Y - y0) * dy) / (dx * dx + dy * dy), 0, 1)
        m |= (X - x0 - t * dx) ** 2 + (Y - y0 - t * dy) ** 2 <= (w / 2) ** 2
    return m


def polys_of(m, tol=1.5, cell=CELL):
    out = []
    for c in find_contours(np.pad(m, 1).astype(float), 0.5):
        c = approximate_polygon(c, tol)
        if len(c) >= 4:
            out.append([[round((p[1] - 1) * cell, 1), round((p[0] - 1) * cell, 1)] for p in c[:-1]])
    return out


def rect_cells(x, y, w, h, a, n, pad=0, cell=CELL):
    """Cells of a w x h rectangle centred at (x, y) turned by a radians (+ pad around), None when off the grid."""
    r = math.hypot(w, h) / 2 + pad + cell
    i0, i1 = max(0, int((x - r) / cell)), min(n, int((x + r) / cell) + 1)
    j0, j1 = max(0, int((y - r) / cell)), min(n, int((y + r) / cell) + 1)
    if i0 >= i1 or j0 >= j1:
        return None
    jj, ii = np.mgrid[j0:j1, i0:i1]
    X, Y = (ii + 0.5) * cell - x, (jj + 0.5) * cell - y
    ca, sa = math.cos(a), math.sin(a)
    lx, ly = X * ca + Y * sa, -X * sa + Y * ca
    inside = (abs(lx) <= w / 2 + pad) & (abs(ly) <= h / 2 + pad)
    return jj[inside], ii[inside]


class City:
    def __init__(self, size, foot, seed, district, district_kind, district_zh, alley_axes=None, kinds=None):
        self.S, self.C, self.n = size, size / 2, size // CELL
        self.foot, self.rnd = foot, random.Random(seed)
        self.district, self.district_kind, self.district_zh = district, district_kind, district_zh
        self.alley_axes = alley_axes or (lambda cx, cy: AXES_TURNED)
        self.kinds = {**KINDS, **(kinds or {})}
        self.roads, self.sites, self.objs = [], {}, []
        self._water, self._islands, self._hills, self._ramps = None, [], [], []
        self._mega, self._specials, self._grounds = {}, [], []
        self.slope = None               # cells on a slope (shore, hill edge): nothing stands there; set by build()

    # -------------------------------------------------------------- the turned frame
    def xy(self, u, v):
        return (self.C + (v - u) / R2, self.C + (v + u) / R2)

    def uv(self, x, y):
        return ((y - self.C - (x - self.C)) / R2, (y - self.C + (x - self.C)) / R2)

    def P(self, pts):
        return [list(map(lambda a: round(a, 1), self.xy(u, v))) for u, v in pts]

    def urect(self, u0, u1, v0, v1):
        return self.P([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])

    def ucircle(self, u, v, r, n=20):
        return self.P([(u + r * math.cos(2 * math.pi * k / n), v + r * math.sin(2 * math.pi * k / n))
                       for k in range(n)])

    # -------------------------------------------------------------- what the design file feeds in
    def water(self, poly, what):
        """Tier 0 below this polygon (less the islands); the shore's slope is kept clear."""
        self._water = (poly, what)

    def island(self, poly, what, texture=None):
        """Raised land (tier 1) in the water -- a pier, an island, a headland: not cut into blocks."""
        self._islands.append((poly, what))
        if texture:
            self.ground(poly, texture, what)

    def hill(self, poly, what):
        """Tier 2; its edge (the cliff) splits blocks, and a block on it is in district(..., on_hill=True)."""
        self._hills.append((poly, what))

    def ramp(self, lo, hi, what, width=150, world=False):
        lo, hi = (lo, hi) if world else (self.xy(*lo), self.xy(*hi))
        self._ramps.append((lo, hi, what, width))

    def road(self, pts, w, name=''):
        self.roads.append(([list(p) for p in pts], w, name))

    def road_uv(self, pts, w, name=''):
        self.roads.append(([list(map(lambda a: round(a, 1), self.xy(u, v))) for u, v in pts], w, name))

    def mega(self, name, poly, texture):
        """A big block (park, fortress, plaza): no automatic buildings; its ground gets `texture`."""
        self._mega[name] = (poly, texture)

    def ground(self, poly, texture, what):
        self._grounds.append({'kind': 'poly', 'at': poly, 'texture': texture, 'what': what})

    def site(self, code, u, v, zh, what, r=60, build=0, cast=0, world=False):
        x, y = (u, v) if world else self.xy(u, v)
        self.sites[code] = {'x': round(x), 'y': round(y), 'r': r, 'zh': zh, 'what': what, 'build': build,
                            **({'cast': cast} if cast else {})}

    def special(self, pt, kind, name, why, centre=None):
        """The block nearest pt -- (u, v), or (x, y, 'w') -- is this kind and name; `centre`: a template in the middle
        of a square. Earlier calls claim their block first."""
        self._specials.append((pt, kind, name, why, centre))

    # -------------------------------------------------------------- build
    def build(self):
        """Fill every block, then put the street props. The sites, roads and terrain must all be in."""
        n = self.n
        islands = np.zeros((n, n), bool)
        for poly, _ in self._islands:
            islands |= mask_poly(poly, n)
        water = mask_poly(self._water[0], n) & ~islands
        self.land = land = ~water
        self.hillmask = hill = np.zeros((n, n), bool)
        for poly, _ in self._hills:
            hill |= mask_poly(poly, n)
        street = np.zeros((n, n), bool)
        for pts, w, _ in self.roads:
            street |= mask_road(pts, w, n)
        self.street = street = street & land
        self.megamask = {k: mask_poly(p, n) & land for k, (p, _) in self._mega.items()}
        anymega = np.zeros((n, n), bool)
        for m in self.megamask.values():
            anymega |= m
        free = land & ~street & ~anymega & ~islands
        edge = ndimage.binary_dilation(hill, iterations=10) & ~ndimage.binary_erosion(hill, iterations=8)
        for lo, hi, _, w in self._ramps:
            edge |= mask_road([lo, hi], w + 50, n)
        free &= ~edge & ~ndimage.binary_dilation(water, iterations=6)
        self.slope = edge | ndimage.binary_dilation(water, iterations=10)
        self.occ = self._fill(free, hill)
        self._street_props()

    def _fill(self, free, hill):
        n, rnd, objs, foot = self.n, self.rnd, self.objs, self.foot
        labels, nl = ndimage.label(free)
        self.block_grounds, self.table = [], []
        occ = np.zeros((n, n), bool)
        yy, xx = np.mgrid[0:n, 0:n]
        X, Y = (xx + 0.5) * CELL, (yy + 0.5) * CELL
        for s in self.sites.values():           # a site's ground stays clear: what is built or fought over there
            occ |= (X - s['x']) ** 2 + (Y - s['y']) ** 2 <= ((s['build'] * 0.75 + 30) if s['build'] else min(s['r'], 60)) ** 2
        blocks = []
        for k in range(1, nl + 1):
            B = labels == k
            if B.sum() < 60:
                continue
            jj, ii = np.nonzero(B)
            cx, cy = (ii.mean() + 0.5) * CELL, (jj.mean() + 0.5) * CELL
            d = self.district(cx, cy, bool(hill[int(cy / CELL), int(cx / CELL)]))
            blocks.append((B, d, cx, cy))
        # each block's kind: a special one where the design needs it, else its district's
        kind_of, names = {}, {}
        for pt, kind, name, why, centre in self._specials:
            x, y = (pt[0], pt[1]) if len(pt) == 3 else self.xy(*pt)
            free_ = [bi for bi in range(len(blocks)) if bi not in kind_of]
            bi = min(free_, key=lambda k: math.hypot(blocks[k][2] - x, blocks[k][3] - y))   # the nearest block
            kind_of[bi], names[bi] = kind, (name, why, centre)
        count = {}
        for bi, (B, d, cx, cy) in enumerate(blocks):
            kind = kind_of.get(bi, self.district_kind[d] if B.sum() >= SMALL else 'square')
            pal, setback, gap, share, rows, inside, zh = self.kinds[kind]
            if bi not in names:
                count[(d, kind)] = count.get((d, kind), 0) + 1
                names[bi] = (f'{self.district_zh[d]}{zh} {count[(d, kind)]}', '', None)
            dist = ndimage.distance_transform_edt(B) * CELL
            inner = dist > 30
            # a lane through the middle of the block both ways: front street and back yard join, infantry slip round a
            # post (retail blocks are never a closed ring of houses; a closed one also shuts its yard off the map)
            for ax, ay in self.alley_axes(cx, cy) if dist.max() > 120 else ():      # a shallow block is open enough
                occ |= B & (abs((X - cx) * ay - (Y - cy) * ax) <= 30)
            self.block_grounds.append({'texture': SIDEWALK, 'what': f'{names[bi][0]}: sidewalk', 'mask': B})
            self.block_grounds.append({'texture': inside, 'what': f'{names[bi][0]}: {kind}', 'mask': inner})
            placed = 0
            if kind == 'parking':
                jj, ii = np.nonzero(dist > 40)
                for j, i in zip(jj[::23], ii[::23]):
                    if rnd.random() < 0.55:
                        objs.append({'template': rnd.choice(CARS),
                                     'x': (i + 0.5) * CELL, 'y': (j + 0.5) * CELL, 'angle': math.pi / 4, 'side': 'neutral'})
            elif kind == 'square':
                jj, ii = np.nonzero(dist > 50)
                for j, i in list(zip(jj, ii))[::53]:                     # trees round the edge, the middle open
                    if dist[j, i] < 90 and rnd.random() < 0.7:
                        objs.append({'template': rnd.choice(TREES),
                                     'x': (i + 0.5) * CELL, 'y': (j + 0.5) * CELL, 'angle': rnd.random() * 6.28,
                                     'side': 'neutral'})
                if names[bi][2]:
                    objs.append({'template': names[bi][2], 'x': round(cx, 1), 'y': round(cy, 1),
                                 'angle': round(math.pi / 4, 4), 'side': 'neutral'})
                    placed = 1
            else:
                placed = self._kerb_rows(B, dist, occ, cx, cy, kind)
                jj, ii = np.nonzero(inner & ~ndimage.binary_dilation(occ, iterations=3))
                for j, i in list(zip(jj, ii))[::41]:        # yards: trees, bushes and trucks in what is left inside
                    r = rnd.random()
                    t = (rnd.choice(['SA_Truck01', 'OD_CargoContainer03']) if kind == 'warehouses' and r < 0.5 else
                         rnd.choice(['CC_BUSH02', 'ST_BUSH01']) if r < 0.3 else
                         rnd.choice(TREES) if r < (0.35 if inside == PAVED else 0.75)
                         else None)
                    if t:
                        objs.append({'template': t, 'x': (i + 0.5) * CELL, 'y': (j + 0.5) * CELL,
                                     'angle': rnd.random() * 6.28, 'side': 'neutral'})
            u, v = self.uv(cx, cy)
            self.table.append({'name': names[bi][0], 'why': names[bi][1], 'district': d, 'kind': kind,
                               'area': int(B.sum()), 'depth': int(dist.max()), 'free': int((B & ~occ).sum()),
                               'buildings': placed, 'x': round(cx), 'y': round(cy), 'u': round(u), 'v': round(v)})
        return occ

    def _kerb_rows(self, B, dist, occ, cx, cy, kind):
        """Buildings in rows on the kerb of block B, then the back-yard line behind them; returns how many stand."""
        rnd, objs = self.rnd, self.objs
        pal, setback, gap, share, rows, inside, _ = self.kinds[kind]
        gy, gx = np.gradient(dist)
        jj, ii = np.nonzero(B)
        target = share * B.sum()
        built, placed = 0.0, 0
        # walk the block's edge ring in order round its centre: buildings in rows on the kerb
        order = sorted(zip(jj, ii), key=lambda p: math.atan2((p[0] + 0.5) * CELL - cy, (p[1] + 0.5) * CELL - cx))
        shapes_ = []
        for t in dict.fromkeys(pal):
            w, h = self.foot[t][:2]
            shapes_.append((t, w, h, 0.0) if w >= h else (t, h, w, math.pi / 2))
        shapes_.sort(key=lambda s: -s[1] * s[2])               # the big ones first
        used = {}
        back = 0.0
        for depth_try in range(rows):
            for j, i in order:
                if built >= target:
                    break
                tries = shapes_[:]
                if rnd.random() < 0.3:
                    rnd.shuffle(tries)
                for t, w, h, turn in tries:
                    if used.get(t, 0) >= 3:                       # three of a kind a block at most
                        continue
                    want = setback + h / 2 + depth_try * (h + gap + 10)
                    if abs(dist[j, i] - want) > 6:
                        continue
                    a = math.atan2(gy[j, i], gx[j, i]) + math.pi / 2
                    x, y = (i + 0.5) * CELL, (j + 0.5) * CELL
                    cells = rect_cells(x, y, w, h, a, self.n, gap / 2)
                    if cells is None or not B[cells].all() or occ[cells].any():
                        continue
                    occ[cells] = True
                    objs.append({'template': t, 'x': round(x, 1), 'y': round(y, 1),
                                 'angle': round(a - turn, 4), 'side': 'neutral'})
                    built += w * h / CELL ** 2
                    placed += 1
                    used[t] = used.get(t, 0) + 1
                    back = max(back, setback + h + 12)
                    break
        # the back-yard line behind the front row: a fence where it is a garden, a row of bushes in a paved yard
        # (retail blocks read full from these, not from more houses: Brighton lays some 450 fence pieces)
        if back and kind != 'warehouses':
            ring = B & (abs(dist - back) < 5) & ~ndimage.binary_dilation(occ, iterations=1)
            rj, ri = np.nonzero(ring)
            for j, i in list(zip(rj, ri))[::3]:
                a = math.atan2(gy[j, i], gx[j, i]) + math.pi / 2
                t = rnd.choice(['CC_WOODFENCE01', 'CC_WHITEFENCE01']) if inside == GRASS else 'CC_BUSH02'
                objs.append({'template': t, 'x': (i + 0.5) * CELL, 'y': (j + 0.5) * CELL,
                             'angle': round(a, 4), 'side': 'neutral'})
        return placed

    def _street_props(self):
        """Lamps both sides of every street, trees down the boulevards, cars parked along some kerbs."""
        rnd, n, street, occ = self.rnd, self.n, self.street, self.occ
        for pts, w, name in self.roads:
            boulevard = w >= 170
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                L = math.hypot(x1 - x0, y1 - y0)
                if L < 1:
                    continue
                ux, uy = (x1 - x0) / L, (y1 - y0) / L
                nx, ny = -uy, ux
                a = math.atan2(uy, ux)
                s = 40.0
                while s < L - 40:
                    for side in (1, -1):
                        for off, kind in ((w / 2 + 14, 'lamp'), (w / 2 - 14, 'car')):
                            x, y = x0 + ux * s + nx * side * off, y0 + uy * s + ny * side * off
                            i, j = int(x / CELL), int(y / CELL)
                            if not (0 <= i < n and 0 <= j < n):
                                continue
                            if self.slope[max(0, j - 2):j + 3, max(0, i - 2):i + 3].any():     # clear of a slope's foot
                                continue
                            if kind == 'lamp':
                                if street[j, i] or occ[j, i] or int(s) % 160 >= 40:
                                    continue
                                t = rnd.choice(['HB_Tree02', 'SA_PALM02']) if boulevard and int(s) % 320 < 40 else 'TH_LAMPPOST04'
                            else:
                                # (the draw comes first even on a narrow street: the random stream depends on it)
                                if rnd.random() > (0.06 if boulevard else 0.18) or w < 110:
                                    continue
                                near = street[max(0, j - 12):j + 13, max(0, i - 12):i + 13]
                                if near.mean() > 0.75:          # at a crossing
                                    continue
                                t = rnd.choice(CARS)
                            self.objs.append({'template': t, 'x': round(x, 1), 'y': round(y, 1),
                                              'angle': round(a + (math.pi / 2 if t.startswith('SM') else 0), 4),
                                              'side': 'neutral'})
                    s += 40.0

    # -------------------------------------------------------------- landmarks (after build)
    def put(self, t, u, v, a=0.0, side='neutral', name=None, world=False, force=False):
        """One object at (u, v) (or world x, y). An unnamed neutral one on the slope is dropped unless force."""
        x, y = (u, v) if world else self.xy(u, v)
        if not (30 < x < self.S - 30 and 30 < y < self.S - 30) or (
                side == 'neutral' and not name and not force and self.slope[int(y / CELL), int(x / CELL)]):
            return
        o = {'template': t, 'x': round(x, 1), 'y': round(y, 1), 'angle': round(a, 4), 'side': side}
        if name:
            o['name'] = name
        self.objs.append(o)

    def clumps(self, n, area, keep_out, size=(5, 11), spread=70):
        """Trees in clumps with lawns between: cover at the edges of open ground, not a carpet. area ((u0, u1),
        (v0, v1)); keep_out(u, v) -> True where no clump starts."""
        rnd = self.rnd
        (u0, u1), (v0, v1) = area
        for _ in range(n):
            cu, cv = rnd.uniform(u0, u1), rnd.uniform(v0, v1)
            if keep_out(cu, cv):
                continue
            for _ in range(rnd.randint(*size)):
                self.put(rnd.choice(TREES), cu + rnd.gauss(0, spread), cv + rnd.gauss(0, spread), rnd.random() * 6.28)

    # -------------------------------------------------------------- write
    def write(self, folder, name, what, start, fields, bridges=()):
        """sketch.json and blocks.json into folder, and the two summary lines."""
        folder = Path(folder)
        json.dump(self.table, open(folder / 'blocks.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        gr = []
        for g in self.block_grounds:
            for poly in polys_of(g['mask']):
                gr.append({'kind': 'poly', 'at': poly, 'texture': g['texture'], 'what': g['what']})
        for k, (_, tex) in self._mega.items():
            for poly in polys_of(self.megamask[k]):
                gr.append({'kind': 'poly', 'at': poly, 'texture': tex, 'what': k})
        gr += self._grounds
        shapes = [{'kind': 'poly', 'at': self._water[0], 'tier': 0, 'what': self._water[1]}]
        shapes += [{'kind': 'poly', 'at': p, 'tier': 1, 'what': w} for p, w in self._islands]
        shapes += [{'kind': 'poly', 'at': p, 'tier': 2, 'what': w} for p, w in self._hills]
        ramps = [{'low': list(map(round, lo)), 'high': list(map(round, hi)), 'width': w, 'what': t}
                 for lo, hi, t, w in self._ramps]
        roads = [{'points': pts, 'width': w, 'texture': ROAD_TEXTURE} for pts, w, _ in self.roads]
        S, objs = self.S, self.objs
        sketch = {'version': 1, 'name': name, 'what': what, 'size': [S, S], 'base': 1, 'cliff': 2, 'shapes': shapes,
                  'walls': [], 'ramps': ramps, 'bridges': list(bridges), 'roads': roads, 'grounds': gr,
                  'sites': self.sites, 'start': list(start), 'fields': fields, 'derricks': [],
                  'borders': {'whole': [0, 0, S, S]},
                  'objects': [{k: (round(v, 1) if isinstance(v, float) else v) for k, v in o.items()} for o in objs]}
        json.dump(sketch, open(folder / 'sketch.json', 'w', encoding='utf-8'), ensure_ascii=False)
        area = lambda t: self.foot.get(t, [0, 0])[0] * self.foot.get(t, [0, 0])[1]      # noqa: E731
        n_b = sum(1 for o in objs if area(o['template']) > BIG)
        foot = sum(area(o['template']) for o in objs if area(o['template']) > BIG)
        land = self.land
        print('streets %.0f%% of dry land, building footprint %.1f%%' % (
            100 * self.street.sum() / land.sum(), 100 * foot / (land.sum() * CELL * CELL)))
        print('objects', len(objs), 'buildings', n_b, 'grounds', len(gr), 'roads', len(roads),
              'land %.0f%%' % (100 * land.mean()), 'dry km2 %.1f' % (land.sum() * CELL * CELL / 1e6))
        return sketch
