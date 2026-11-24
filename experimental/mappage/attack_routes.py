"""Where the attacks go (map-design intent 3: few named crossings are where the AI's waves must pass): the engine
line's pathfinding model (sketch2map.pathing_model, as --pathing) routes every Soviet barracks and the player's start
to every power station of a sketch map, with the buildings (the caller's palette footprints) blocking; draws them on
the map's models.png and prints the lengths.
Usage: attack_routes.py <sketch name> [footprint .json ...]
  (work/mappage/<name>/: <name>.py, sketch.json, models.png; footprints default to work/logs/mapdesign_1123/palette*)"""
import importlib.util
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
if 'sketch2map' not in sys.modules:     # by file, as mappage.py does: it loads build.py, which sets the path
    _spec = importlib.util.spec_from_file_location('sketch2map', os.path.join(HERE, 'sketch2map.py'))
    sys.modules['sketch2map'] = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(sys.modules['sketch2map'])
s2m = sys.modules['sketch2map']
import labpaths                                                  # noqa: E402
import platmap                                                   # noqa: E402
BIG = 2500                                                       # footprints above this (w x h) block the way
PALETTES = [os.path.join(labpaths.WORK, 'logs', 'mapdesign_1123', f) for f in ('palette.json', 'palette_props.json')]


def main(name, palettes=PALETTES):
    pf = s2m.pathing_model()
    if pf is None:
        sys.exit("the engine line's pathfinding model is not on this computer (labpaths.ENGINE_MODEL)")
    foot = {}
    for p in palettes:
        foot.update(json.load(open(p)))
    folder = os.path.join(s2m.OUT, name)
    mod = s2m.load(os.path.join(folder, name + '.py'))
    sk = json.load(open(os.path.join(folder, 'sketch.json'), encoding='utf-8'))
    w, h, b = platmap.CONTAINER
    walk = s2m.walk_of(mod)[b:h - b, b:w - b].copy()
    C = platmap.CELL
    n = walk.shape[0]
    jj, ii = np.mgrid[0:n, 0:n]
    X, Y = (ii + 0.5) * C, (jj + 0.5) * C
    for o in sk['objects']:
        f = foot.get(o['template'])
        if not f or f[0] * f[1] < BIG or o.get('side', 'neutral') != 'neutral' or o.get('name'):
            continue                                             # the barracks and stations are where the routes end
        ca, sa = math.cos(o['angle']), math.sin(o['angle'])
        dx, dy = X - o['x'], Y - o['y']
        walk[(abs(dx * ca + dy * sa) <= f[0] / 2) & (abs(-dx * sa + dy * ca) <= f[1] / 2)] = False
    for s in sk['sites'].values():                               # a site's own spot stays open (a house may stand on it)
        walk[(X - s['x']) ** 2 + (Y - s['y']) ** 2 <= 70 ** 2] = True
    grid = s2m.model_grid(pf, walk)
    sites = sk['sites']
    stations = [c for c in sites if c.startswith('st_')]
    sources = [c for c in sites if c.startswith('sov_')] + ['start']
    img = Image.open(os.path.join(folder, 'models.png')).convert('RGB')
    K = img.width / 5000
    dr = ImageDraw.Draw(img, 'RGBA')
    px = lambda x, y: (x * K, (5000 - y) * K)                     # noqa: E731
    colour = {'start': (60, 140, 255, 200)}
    reds = [(255, 60, 60, 170), (255, 140, 40, 170), (230, 60, 200, 170), (255, 220, 60, 170), (160, 40, 40, 170)]
    table = {}
    for i, src in enumerate(sources):
        col = colour.get(src, reds[i % len(reds)])
        for st in stations:
            a, z = sites[src], sites[st]
            r = pf.find_path(grid, pf.world_to_cell(a['x'], a['y']), pf.world_to_cell(z['x'], z['y']), cell_limit=400000)
            if not r.found:
                print('approx', src, st, r.reason)
            if not r.cells:
                table[(src, st)] = None
                print('no path', src, st, r.reason)
                continue
            pts = [px(*pf.cell_center(*c)) for c in r.cells]
            dr.line(pts, fill=col, width=3)
            table[(src, st)] = round(pf.path_length_world(r.cells)) if r.found else -1
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 16)
    for st in stations:
        p = px(sites[st]['x'], sites[st]['y'])
        dr.regular_polygon((p, 9), 4, rotation=45, fill=(255, 230, 0, 255), outline=(0, 0, 0))
        dr.text((p[0] + 10, p[1] - 8), sites[st]['zh'], font=font, fill=(255, 255, 255))
    out = os.path.join(folder, 'routes.png')
    img.save(out)
    print('from \\ to'.ljust(16) + ''.join(s[3:].ljust(9) for s in stations))
    for src in sources:
        print(src.ljust(16) + ''.join(str(table[(src, st)]).ljust(9) for st in stations))
    print('nearest Soviet minus the player (negative: the Soviets are closer)')
    for st in stations:
        sov = [table[(s, st)] for s in sources if s != 'start' and table[(s, st)] and table[(s, st)] > 0]
        me = table[('start', st)]
        print(f'  {st:12s} player {me}  nearest soviet {min(sov) if sov else None}  diff {min(sov) - me if sov and me else None}')
    print(out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:] or PALETTES)
