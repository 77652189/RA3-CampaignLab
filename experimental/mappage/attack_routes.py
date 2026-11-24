"""Where the attacks go (map-design intent 3: few named crossings are where the AI's waves must pass): the
simulator's routing (sketch2map.way) routes every Soviet barracks and the player's start to every power station of a
sketch map, with the buildings (the caller's palette footprints) blocking; draws them on the map's models.png and
prints the lengths (the taut legs a unit drives; -1: no way).
Usage: attack_routes.py <sketch name> [footprint .json ...]
  (work/mappage/<name>/: <name>.py, sketch.json, models.png; footprints default to work/logs/mapdesign_1123/palette*)"""
import importlib.util
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
if 'sketch2map' not in sys.modules:     # by file, as mappage.py does: it loads build.py, which sets the path
    _spec = importlib.util.spec_from_file_location('sketch2map', os.path.join(HERE, 'sketch2map.py'))
    sys.modules['sketch2map'] = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(sys.modules['sketch2map'])
s2m = sys.modules['sketch2map']
import labpaths                                                  # noqa: E402
BIG = 2500                                                       # footprints above this (w x h) block the way
PALETTES = [os.path.join(labpaths.WORK, 'logs', 'mapdesign_1123', f) for f in ('palette.json', 'palette_props.json')]


def main(name, palettes=PALETTES):
    foot = {}
    for p in palettes:
        foot.update(json.load(open(p)))
    folder = os.path.join(s2m.OUT, name)
    mod = s2m.load(os.path.join(folder, name + '.py'))
    sk = json.load(open(os.path.join(folder, 'sketch.json'), encoding='utf-8'))
    from engine.objects.path import Ground                       # on the path build.py set
    g = Ground(mod)                     # a way's ends snap to the nearest open cell (a house may stand on a site)
    g.set_blocks([(o['x'], o['y'], o['angle'], *foot[o['template']][:2]) for o in sk['objects']
                  if foot.get(o['template']) and foot[o['template']][0] * foot[o['template']][1] >= BIG
                  and o.get('side', 'neutral') == 'neutral' and not o.get('name')])   # barracks, stations: the ends
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
            wet = g.grids['water'][g.cell(a['x'], a['y'])]       # a site on the water sends boats and amphibians
            r = s2m.way(g, (a['x'], a['y']), (z['x'], z['y']), 'both' if wet else 'ground')
            if not r['found']:
                print('no way', src, st, f"(stops {r['gap']:.0f} short)" if 'gap' in r else '')
            if len(r['points']) > 1:
                dr.line([px(*c) for c in r['points']], fill=col, width=3)
            table[(src, st)] = r['length'] if r['found'] else -1
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
