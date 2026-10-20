r"""Terrain from a real place: elevation (AWS Terrain Tiles, terrarium PNG, public) and land use / water / roads
(OpenStreetMap via the Overpass API) for a square around (lat, lon), squeezed onto a map's playable area and
exaggerated the RA3 way (land in a band above the waterline, water below it, roads and town as pavement).

  python -I -X utf8 experimental/campaign/realmap.py fetch goldengate 37.805 -122.465 7    -> work/realmap/goldengate/
  python -I -X utf8 experimental/campaign/realmap.py show goldengate                       -> its rasters as a PNG

From a builder (make_realmap.py): r = realmap.Real('goldengate'); r.heights(hm) -> {(i, j): height};
r.textures(hm) -> {(i, j): texture name}. Downloads are cached in work/realmap/<name>/ (dem.npy, osm.json).
Terrarium height in metres = R * 256 + G + B / 256 - 32768.
"""
import io
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import labpaths  # noqa: E402

DIR = os.path.join(labpaths.WORK, 'realmap')
TILES = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'
OVERPASS_ALL = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
                'https://overpass.private.coffee/api/interpreter']
AGENT = {'User-Agent': 'RA3-CampaignLab realmap (https://github.com/77652189/RA3-CampaignLab)'}
RASTER = 500                       # playable cells per side on our 560 x 560 maps (border 30)
DECK = 100                         # bridge deck height above WATERLINE
WATERLINE = 285.7                  # newmap.WATERLINE (kept here so this file runs without the map modules)


def _get(url, data=None):
    req = urllib.request.Request(url, data=data, headers=AGENT)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def bbox(lat, lon, km):
    dlat = km / 2 / 111.32
    dlon = km / 2 / (111.32 * math.cos(math.radians(lat)))
    return lat - dlat, lon - dlon, lat + dlat, lon + dlon


def _tile_xy(lat, lon, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def fetch_dem(box, size=RASTER):
    """Elevation (metres) on a size x size grid over box, rows north to south."""
    s, w, n, e = box
    z = 14
    x0, y0 = _tile_xy(n, w, z)
    x1, y1 = _tile_xy(s, e, z)
    tiles = {}
    for ty in range(int(y0), int(y1) + 1):
        for tx in range(int(x0), int(x1) + 1):
            a = np.asarray(Image.open(io.BytesIO(_get(TILES.format(z=z, x=tx, y=ty)))).convert('RGB'), np.float64)
            tiles[(tx, ty)] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    out = np.zeros((size, size))
    for r in range(size):
        for c in range(size):
            fx = x0 + (x1 - x0) * (c + 0.5) / size
            fy = y0 + (y1 - y0) * (r + 0.5) / size
            t = tiles[(int(fx), int(fy))]
            out[r, c] = t[min(255, int((fy % 1) * 256)), min(255, int((fx % 1) * 256))]
    return out


def fetch_osm(box):
    s, w, n, e = box
    q = f"""[out:json][timeout:120];
(
  way["natural"~"water|coastline|wood|beach|sand|bare_rock|scrub|grassland"]({s},{w},{n},{e});
  relation["natural"="water"]({s},{w},{n},{e});
  way["waterway"~"river|riverbank|canal"]({s},{w},{n},{e});
  way["landuse"~"residential|commercial|industrial|retail|forest|grass|meadow|park|railway"]({s},{w},{n},{e});
  way["leisure"~"park|golf_course|pitch"]({s},{w},{n},{e});
  way["highway"~"motorway|trunk|primary|secondary|tertiary|residential|unclassified"]({s},{w},{n},{e});
  way["man_made"~"bridge|pier"]({s},{w},{n},{e});
);
out geom;"""
    body = urllib.parse.urlencode({'data': q}).encode()
    last = None
    for attempt in range(6):            # the public servers answer 502 / 504 when busy: retry, then mirrors
        url = OVERPASS_ALL[attempt % len(OVERPASS_ALL)]
        try:
            return json.loads(_get(url, body))
        except (urllib.error.URLError, TimeoutError) as err:
            last = err
            print('overpass', url, err, '- retrying')
            time.sleep(10 * (attempt + 1))
    raise SystemExit(f'Overpass failed: {last}')


def fetch(name, lat, lon, km):
    d = os.path.join(DIR, name)
    os.makedirs(d, exist_ok=True)
    box = bbox(lat, lon, km)
    with open(os.path.join(d, 'place.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(lat=lat, lon=lon, km=km, bbox=box), f)
    if not os.path.exists(os.path.join(d, 'dem.npy')):
        np.save(os.path.join(d, 'dem.npy'), fetch_dem(box))
    if not os.path.exists(os.path.join(d, 'osm.json')):
        osm = fetch_osm(box)                     # fetched first: a failed download leaves no empty cache file
        with open(os.path.join(d, 'osm.json'), 'w', encoding='utf-8') as f:
            json.dump(osm, f)
    print('cached in', d)


# cells (a cell is 10 world units); a 7 km square puts a city block at about one tank, so side streets stay thin
ROAD_WIDTH = {'motorway': 5, 'trunk': 5, 'primary': 4, 'secondary': 3, 'tertiary': 2, 'residential': 1,
              'unclassified': 1}
TOWN = ('residential', 'commercial', 'industrial', 'retail', 'railway')
GREEN = ('forest', 'wood', 'park', 'golf_course', 'grass', 'meadow', 'scrub', 'grassland', 'pitch')


def _grow(mask, cells):
    """mask dilated by `cells` (4-neighbour steps)."""
    out = mask.copy()
    for _ in range(cells):
        g = out.copy()
        g[1:] |= out[:-1]
        g[:-1] |= out[1:]
        g[:, 1:] |= out[:, :-1]
        g[:, :-1] |= out[:, 1:]
        out = g
    return out


def _blur(a, sigma):
    """Separable Gaussian blur of a float array (edges repeat)."""
    r = int(3 * sigma) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    for axis in (0, 1):
        p = np.pad(a, [(r, r) if ax == axis else (0, 0) for ax in (0, 1)], mode='edge')
        a = sum(w * np.take(p, range(o, o + a.shape[axis]), axis=axis) for o, w in enumerate(k))
    return a


class Real:
    """A fetched place rasterised onto RASTER x RASTER playable cells (rows north to south)."""

    def __init__(self, name):
        d = os.path.join(DIR, name)
        with open(os.path.join(d, 'place.json'), encoding='utf-8') as f:
            self.place = json.load(f)
        self.dem = np.load(os.path.join(d, 'dem.npy'))
        with open(os.path.join(d, 'osm.json'), encoding='utf-8') as f:
            self.osm = json.load(f)
        s, w, n, e = self.place['bbox']
        self.box = (s, w, n, e)
        self._layers()

    def _px(self, lat, lon):
        s, w, n, e = self.box
        return (lon - w) / (e - w) * RASTER, (n - lat) / (n - s) * RASTER

    def _layers(self):
        size = (RASTER, RASTER)
        water, road, town, green, sand = (Image.new('L', size) for _ in range(5))
        dr = {k: ImageDraw.Draw(v) for k, v in dict(water=water, road=road, town=town, green=green,
                                                     sand=sand).items()}
        for el in self.osm.get('elements', []):
            t = el.get('tags', {})
            rings = []
            if 'geometry' in el:
                rings.append([self._px(p['lat'], p['lon']) for p in el['geometry']])
            for mem in el.get('members', []):
                if mem.get('role') == 'outer' and 'geometry' in mem:
                    rings.append([self._px(p['lat'], p['lon']) for p in mem['geometry']])
            for pts in rings:
                if len(pts) < 2:
                    continue
                closed = len(pts) > 2 and pts[0] == pts[-1]
                hw = t.get('highway')
                if hw in ROAD_WIDTH:
                    dr['road'].line(pts, fill=255, width=ROAD_WIDTH[hw])
                elif t.get('waterway') in ('river', 'canal') and not closed:
                    dr['water'].line(pts, fill=255, width=4)
                elif not closed:
                    continue
                elif t.get('natural') == 'water' or t.get('waterway') == 'riverbank':
                    dr['water'].polygon(pts, fill=255)
                elif t.get('natural') in ('beach', 'sand', 'bare_rock'):
                    dr['sand'].polygon(pts, fill=255)
                elif t.get('landuse') in TOWN:
                    dr['town'].polygon(pts, fill=255)
                elif t.get('landuse') in GREEN or t.get('leisure') in GREEN or t.get('natural') in GREEN:
                    dr['green'].polygon(pts, fill=255)
                elif t.get('man_made') in ('bridge', 'pier'):
                    dr['road'].polygon(pts, fill=255)
        a = lambda im: np.asarray(im) > 127                      # noqa: E731
        # the sea: terrain tiles put open water at <= 0 m (coastline ways are not closed in a bbox, so the DEM
        # decides); OSM lakes / rivers on top
        self.sea = (self.dem <= 0.5) | a(water)
        self.road, self.town, self.green, self.sand = a(road), a(town), a(green), a(sand)
        self.bridge = self.road & self.sea                     # roads over water stay land (bridges, piers)

    def heights(self, hm, land_band=230.0, exaggerate=1.0, floor=40.0):
        """{(i, j): height} for every cell of the map: sea `floor` below the waterline, land from 12 above it,
        rising with the real elevation (highest point -> land_band above, times exaggerate)."""
        b = hm.border
        land = ~self.sea | self.bridge
        top = max(1.0, float(self.dem[land].max())) if land.any() else 1.0
        elev = np.where(land, WATERLINE + 12 + np.clip(self.dem, 0, None) / top * land_band * exaggerate,
                        WATERLINE - floor)
        elev = _blur(elev, 1.2)
        # bridges (CampBridge1 bench, 2026-10-20): a 3-4 cell causeway at +12 stopped every ground unit at the
        # bridge head, and a 9-cell deck at +14 still looked awash on screen (the real water surface sits higher
        # than WATERLINE). The deck: ~9 cells, flat, DECK above the waterline; the land near it ramps towards the
        # deck height (at most 5 a cell, cut down or built up) so it never meets a cliff or a step.
        if self.bridge.any():
            deck = _grow(self.bridge, 2)
            self.road |= deck
            self.bridge = deck
            elev[deck] = WATERLINE + DECK
            near = deck.copy()
            for k in range(1, 41):
                ring = _grow(near, 1) & ~near & ~self.sea
                near |= ring
                lo, hi = WATERLINE + DECK - 5 * k, WATERLINE + DECK + 5 * k
                elev[ring] = np.clip(elev[ring], lo, hi)
        out = {}
        for j in range(hm.height):
            for i in range(hm.width):
                r = RASTER - 1 - min(RASTER - 1, max(0, j - b))     # map rows count north
                c = min(RASTER - 1, max(0, i - b))
                out[(i, j)] = float(elev[r, c])
        return out

    def textures(self, hm, heights):
        """{(i, j): ground texture} from the land-use rasters (Heidelberg's texture set)."""
        b = hm.border
        out = {}
        # beach = a 3-cell band along the water (low-lying districts such as the Marina are not beaches)
        sea = self.sea & ~self.bridge
        shore = sea.copy()
        for _ in range(3):
            shore[1:] |= shore[:-1].copy()
            shore[:-1] |= shore[1:].copy()
            shore[:, 1:] |= shore[:, :-1].copy()
            shore[:, :-1] |= shore[:, 1:].copy()
        for (i, j), e in heights.items():
            r = RASTER - 1 - min(RASTER - 1, max(0, j - b))
            c = min(RASTER - 1, max(0, i - b))
            near = [heights.get((i + di, j + dj), e) for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            slope = max(abs(x - e) for x in near)
            if e < WATERLINE - 12:
                t = 'Dirt_Yucatan01'
            elif self.road[r, c]:
                t = 'Pavement_Heidel01'
            elif e < WATERLINE + 8 or self.sand[r, c] or (shore[r, c] and e < WATERLINE + 40):
                t = 'Sand_SantaMonica01'
            elif slope > 9:
                t = 'Rock_Yucatan01'
            elif self.town[r, c]:
                t = 'Pavement_Heidelberg10'
            elif self.green[r, c]:
                t = 'Grass_Heidelberg02'
            else:
                t = 'Grass_Heidelberg01'
            out[(i, j)] = t
        return out

    def picture(self, out):
        rgb = np.zeros((RASTER, RASTER, 3), np.uint8)
        g = np.clip(self.dem / max(1.0, self.dem.max()) * 200 + 40, 0, 255).astype(np.uint8)
        rgb[...] = g[..., None]
        rgb[self.green] = (60, 120, 50)
        rgb[self.town] = (150, 140, 130)
        rgb[self.road] = (240, 240, 240)
        rgb[self.sea & ~self.bridge] = (30, 70, 120)
        Image.fromarray(rgb).save(out)
        return out


if __name__ == '__main__':
    cmd, name = sys.argv[1], sys.argv[2]
    if cmd == 'fetch':
        fetch(name, float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]))
    elif cmd == 'show':
        print(Real(name).picture(os.path.join(DIR, name, 'layers.png')))
