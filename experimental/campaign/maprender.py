r"""Top-down picture of a .map without starting the game: ground from the SDK's own terrain textures (tiles and
blends as BlendTileData places them), hill shading, water, objects coloured by owner, waypoints, trigger areas and a
world-coordinate grid -- to check a generated map's layout in seconds instead of a bench run.

  python -I -X utf8 experimental/campaign/maprender.py CampNew30                  -> work/maps/CampNew30.png
  python -I -X utf8 experimental/campaign/maprender.py <mod .big | .map> [-o out.png] [--px 4]
         [--around X Y R] [--bench-view] [--water H]

A mod name is looked up in Documents\Red Alert 3\Mods, then in work\staging (built while the game was running).
From code: maprender.render(MapFile, out_png, ...). World (0, 0) is the south-west corner of the playable area;
y grows north (up in the picture). --bench-view draws what the bench camera sees at the mission start (calib.py;
only for maps derived from CampNew18's island). --water: terrain below this height is drawn as water
(default newmap.WATERLINE, measured on our generated island).

TriggerAreas (v1), read here first: u32 count; each area: u16 + name, u16 + layer, u32 id, u32 point count,
points as f32 x, y, u32 0.
"""
import argparse
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import labpaths  # noqa: E402

sys.path.insert(0, labpaths.ROOT)
import mapscript  # noqa: E402
import mapterrain  # noqa: E402
import mapxml  # noqa: E402
import newmap  # noqa: E402
from ra3voice import big  # noqa: E402

TERRAIN_ART = os.path.join(labpaths.SDK3, 'Art', 'Terrain')
OUT_DIR = os.path.join(labpaths.WORK, 'maps')
MODS = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods')
STAGING = os.path.join(labpaths.WORK, 'staging')
OWNER_COLOURS = [('Soviet', (225, 50, 40)), ('Japan', (240, 200, 30)), ('Empire', (240, 200, 30)),
                 ('Allie', (50, 120, 240)), ('Player', (50, 120, 240))]
NEUTRAL = (200, 200, 200)


def _font(size):
    for name in ('msyh.ttc', 'simhei.ttf', 'arial.ttf'):
        try:
            return ImageFont.truetype(os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', name), size)
        except OSError:
            continue
    return ImageFont.load_default()


def trigger_areas(m):
    node = next((n for _, n in m.walk() if n.name == 'TriggerAreas'), None)
    if node is None:
        return []
    d, out = node.head, []
    count = struct.unpack_from('<I', d, 0)[0]
    p = 4
    for _ in range(count):
        ln = struct.unpack_from('<H', d, p)[0]
        name = d[p + 2:p + 2 + ln].decode('latin-1')
        p += 2 + ln
        p += 2 + struct.unpack_from('<H', d, p)[0]                  # layer
        _, n = struct.unpack_from('<II', d, p)
        p += 8
        pts = [struct.unpack_from('<ff', d, p + 8 * k) for k in range(n)]
        p += 8 * n + 4
        out.append((name, pts))
    return out


class _Textures:
    """Each ground texture scaled so one map cell (tile) is `px` pixels: a texture spans 2 * size tiles."""

    def __init__(self, tiles, px):
        self.px, self.tiles, self.cache = px, tiles, {}
        self.by_cell = {}
        for name, (start, count, size) in tiles.textures.items():
            for c in range(start, start + count):
                self.by_cell[c] = (name, start, size)

    def _image(self, name, size):
        if name not in self.cache:
            side = 2 * size * self.px
            path = os.path.join(TERRAIN_ART, name + '.tga')
            if os.path.exists(path):
                img = Image.open(path).convert('RGB').resize((side, side), Image.LANCZOS)
                a = np.asarray(img, dtype=np.float32)
            else:       # retail-only texture (no SDK source, e.g. Dirt_Yucatan04): newmap's colour, or grey, + grain
                rgb = np.array(newmap.COLORS.get(name, (110, 110, 110)), np.float32)
                grain = np.random.default_rng(len(name)).normal(1.0, 0.06, (side, side, 1)).astype(np.float32)
                a = rgb * grain
            self.cache[name] = a
        return self.cache[name]

    def block(self, tile):
        """px x px pixels of one tile value (4 * cell + quadrant), image rows top = north."""
        cell, quad = divmod(tile, 4)
        hit = self.by_cell.get(cell)
        if hit is None:
            return np.full((self.px, self.px, 3), 110.0, np.float32)
        name, start, size = hit
        k = cell - start
        tx = 2 * (k % size) + quad % 2
        ty = 2 * (k // size) + quad // 2                              # tile rows count north
        a = self._image(name, size)
        rows = a.shape[0] // self.px
        r = rows - 1 - ty                                             # picture rows count south
        return a[r * self.px:(r + 1) * self.px, tx * self.px:(tx + 1) * self.px]


def _blend_mask(px, direction, flags, two_sided):
    """Weight of the blended-in texture across a tile (rows top = north), from the blend description's
    direction bytes (mapterrain.Tiles.SIDES: byte 0 east / west, 1 north / south, 2 north-east / south-east,
    3 north-west / south-west; two-sided = the inner corner of both sides)."""
    t = (np.arange(px) + 0.5) / px
    east = np.tile(t, (px, 1))
    north = np.tile(t[::-1, None], (1, px))
    sides = {0: (east, 1 - east), 1: (north, 1 - north)}
    if direction[0] or direction[1]:
        k = 0 if direction[0] else 1
        return sides[k][1 if flags & 1 else 0]
    k = 2 if direction[2] else 3
    ew = east if k == 2 else 1 - east
    ns = 1 - north if flags & 1 else north
    return np.maximum(ew, ns) if two_sided else np.minimum(ew, ns)


def render(m, out, px=4, around=None, bench_view=False, water=newmap.WATERLINE, title=None):
    hm = mapterrain.HeightMap(m)
    tiles = mapterrain.Tiles(m, hm.width)
    tex = _Textures(tiles, px)
    b = hm.border
    w, h = hm.width - 2 * b, hm.height - 2 * b
    tile, blend = tiles.arrays[0], tiles.arrays[1]
    img = np.zeros((h * px, w * px, 3), np.float32)
    masks = {}
    for j in range(h):
        r = (h - 1 - j) * px
        for i in range(w):
            k = (j + b) * hm.width + (i + b)
            blk = tex.block(tile[k])
            v = blend[k]
            if v and v - 1 < len(tiles.descs):
                dsc = tiles.descs[v - 1]
                second = struct.unpack_from('<I', dsc, 0)[0]
                key = (dsc[4:8], dsc[8], dsc[9])
                if key not in masks:
                    masks[key] = _blend_mask(px, *key)[..., None]
                blk = blk * (1 - masks[key]) + tex.block(second) * masks[key]
            img[r:r + px, i * px:(i + 1) * px] = blk
    # hill shading (light from the north-west) and water, per cell, then scaled up to pixels
    e = np.array(hm.elev, np.float32).reshape(hm.height, hm.width)[b:b + h, b:b + w] / mapterrain.SCALE
    e = e[::-1]                                                       # rows top = north
    gy, gx = np.gradient(e)
    shade = np.clip(1.0 + (-gx + gy) * 0.035, 0.6, 1.35)
    shade = np.kron(shade, np.ones((px, px)))[..., None]
    img *= shade
    wet = np.kron((e < water).astype(np.float32), np.ones((px, px)))[..., None]
    depth = np.kron(np.clip((water - e) / 120.0, 0, 1), np.ones((px, px)))[..., None]
    sea = np.array([30, 75, 110], np.float32) * (1 - 0.4 * depth)
    img = img * (1 - wet * 0.85) + sea * wet * 0.85
    pic = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(pic, 'RGBA')
    f, small = _font(max(11, 3 * px)), _font(max(9, int(2.5 * px)))
    s = px / mapterrain.CELL                                          # pixels per world unit

    def at(x, y):
        return x * s, (h * mapterrain.CELL - y) * s

    for g in range(0, int(max(w, h) * mapterrain.CELL) + 1, 500):    # world grid every 500
        X, _ = at(g, 0)
        _, Y = at(0, g)
        d.line([(X, 0), (X, pic.height)], fill=(255, 255, 255, 50))
        d.line([(0, Y), (pic.width, Y)], fill=(255, 255, 255, 50))
        d.text((X + 2, 2), str(g), fill=(255, 255, 255, 170), font=small)
        d.text((2, Y - 3 * px), str(g), fill=(255, 255, 255, 170), font=small)
    for name, pts in trigger_areas(m):
        q = [at(x, y) for x, y in pts]
        if len(q) >= 2:
            d.polygon(q, outline=(80, 230, 230, 220))
            d.text(q[0], name.replace('AREA - ', ''), fill=(80, 230, 230, 230), font=small)
    named = []
    for o in mapxml.objects(m):
        x, y = at(o['x'], o['y'])
        p = o['props']
        if o['template'] == '*Waypoints/Waypoint':
            d.polygon([(x, y - 2 * px), (x + 2 * px, y), (x, y + 2 * px), (x - 2 * px, y)],
                      fill=(255, 220, 60, 230), outline=(0, 0, 0, 255))
            named.append((x, y, p.get('waypointName', ''), (255, 220, 60)))
            continue
        owner = str(p.get('originalOwner', ''))
        col = next((c for key, c in OWNER_COLOURS if key in owner), NEUTRAL)
        rad = 1.6 * px if col != NEUTRAL else 1.0 * px
        d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=col + (235,), outline=(0, 0, 0, 255))
        a = o['angle']
        d.line([(x, y), (x + 2.6 * px * np.cos(a), y - 2.6 * px * np.sin(a))], fill=(0, 0, 0, 255), width=1)
        label = str(p.get('objectName', '')).replace('UNIT - ', '')
        if label:
            named.append((x, y, label, col))
        elif col != NEUTRAL:
            named.append((x, y, o['template'], col))
    boxes = []                                  # labels already drawn: a new one moves down, or is left out
    for x, y, label, col in named:
        for step in range(4):
            pos = (x + 2.2 * px, y - 1.6 * px + step * (small.size + 2))
            box = d.textbbox(pos, label, font=small)
            if not any(box[0] < o[2] and o[0] < box[2] and box[1] < o[3] and o[1] < box[3] for o in boxes):
                boxes.append(box)
                d.text(pos, label, fill=col + (255,), font=small, stroke_width=1, stroke_fill=(0, 0, 0, 255))
                break
    if bench_view:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'testbench'))
        import calib
        corners = [calib.screen_to_world(u, v) for u, v in ((0, 0), (1280, 0), (1280, 720), (0, 720))]
        d.polygon([at(x, y) for x, y in corners], outline=(255, 255, 255, 230))
        d.text(at(*corners[0]), 'bench start view', fill=(255, 255, 255, 230), font=small)
    if around:
        x, y, r = around
        x0, y0 = at(x - r, y + r)
        x1, y1 = at(x + r, y - r)
        pic = pic.crop((int(max(0, x0)), int(max(0, y0)), int(min(pic.width, x1)), int(min(pic.height, y1))))
        d = ImageDraw.Draw(pic, 'RGBA')
    if title:
        d.text((8, pic.height - 4 * px - 8), title, fill=(255, 255, 255, 255), font=f, stroke_width=2,
               stroke_fill=(0, 0, 0, 255))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    pic.save(out)
    return out


def load(source):
    """MapFile from a .map file, a mod .big, or a mod name (Mods folder, then work\\staging)."""
    if not os.path.exists(source):
        for base in (MODS, STAGING):
            cand = os.path.join(base, source, source + '.big')
            if os.path.exists(cand):
                source = cand
                break
        else:
            raise SystemExit(f'not found: {source} (no .map/.big, and no mod of that name in {MODS} or {STAGING})')
    if source.lower().endswith('.big'):
        names = [e[0] for e in big.read_index(source)]
        maps = [n for n in names if n.lower().endswith('.map')]
        if not maps:
            raise SystemExit(f'{source}: no .map inside')
        data = big.read_files(source, maps[:1])
        data = data[maps[0]] if isinstance(data, dict) else data[0]
    else:
        with open(source, 'rb') as fh:
            data = fh.read()
    return mapscript.MapFile(data)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('source', help='mod name, mod .big or .map')
    ap.add_argument('-o', '--out')
    ap.add_argument('--px', type=int, default=4, help='pixels per map cell (10 world units)')
    ap.add_argument('--around', type=float, nargs=3, metavar=('X', 'Y', 'R'), help='crop to a square around X Y')
    ap.add_argument('--bench-view', action='store_true')
    ap.add_argument('--water', type=float, default=newmap.WATERLINE)
    a = ap.parse_args()
    stem = os.path.splitext(os.path.basename(a.source))[0]
    out = a.out or os.path.join(OUT_DIR, stem + '.png')
    print(render(load(a.source), out, a.px, a.around, a.bench_view, a.water, title=stem))


if __name__ == '__main__':
    main()
