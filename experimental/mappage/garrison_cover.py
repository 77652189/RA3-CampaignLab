"""How much of a map's streets the garrisonable buildings cover (map-design intent 5: streets are fire lanes, the
point is that garrisons cover them, not a street share). Street points: the road pieces retail lays (street
segments, sidewalk and line decals) or, for our sketches, points along the sketch's roads. A point is covered at
range R when a garrisonable building's edge (centre minus half its smaller side) is within R.
Usage: garrison_cover.py <retail name | .map> [...]   (a .map with sketch.json beside it uses the sketch's roads)"""
import importlib.util
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if 'sketch2map' not in sys.modules:     # by file, as mappage.py does: it loads build.py, which sets the path
    _spec = importlib.util.spec_from_file_location('sketch2map', os.path.join(HERE, 'sketch2map.py'))
    sys.modules['sketch2map'] = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(sys.modules['sketch2map'])
import numpy as np                                  # noqa: E402
import labpaths                                     # noqa: E402
import maprender                                    # noqa: E402
import mapxml                                       # noqa: E402
from engine.data import units as U                  # noqa: E402

TAGS = ('GarrisonContain', 'ContestableGarrisonContain')
ROAD = re.compile(r'streetsegment|sidewalk|whiteline|yellowline|crosswalk|roadmarking|parkinglines|road0', re.I)
SPR = os.path.join(labpaths.WORK, 'reference', 'sprites')
_g = {}


def garrison(t):
    """ContainMax of the template's garrison module, 0 when it has none."""
    if t not in _g:
        def first(xml):
            for tag in TAGS:
                for head, _ in U._blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), tag):
                    v = U._attr(head, 'ContainMax', '5')
                    return int(float(v)) if re.fullmatch(r'[\d.]+', v) else 5     # '=$CIV_CONTAIN_SMALL': a constant
            return None
        try:
            _g[t] = U._chain(t, None, first) or 0
        except (OSError, ValueError, KeyError):
            _g[t] = 0
    return _g[t]


def half(t):
    j = os.path.join(SPR, t + '.json')
    return 0.35 * json.load(open(j))['half'] if os.path.exists(j) else 35.0


def street_points(src, objs):
    sk = os.path.join(os.path.dirname(src), 'sketch.json') if src.endswith('.map') else None
    if sk and os.path.exists(sk):
        pts = []
        for r in json.load(open(sk, encoding='utf-8'))['roads']:
            for (x0, y0), (x1, y1) in zip(r['points'], r['points'][1:]):
                n = max(1, int(math.hypot(x1 - x0, y1 - y0) / 40))
                pts += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n + 1)]
        return np.array(pts)
    return np.array([(o['x'], o['y']) for o in objs if ROAD.search(o['template'])])


def main():
    for src in sys.argv[1:]:
        objs = mapxml.objects(maprender.load(src))
        gs = [(o['x'], o['y'], half(o['template']), garrison(o['template'])) for o in objs
              if not o['template'].startswith('*') and garrison(o['template'])]
        pts = street_points(src, objs)
        if not len(gs) or not len(pts):
            print(src, 'garrisons', len(gs), 'street points', len(pts))
            continue
        G = np.array(gs)
        d = np.sqrt(((pts[:, None, 0] - G[None, :, 0]) ** 2 + (pts[:, None, 1] - G[None, :, 1]) ** 2)) - G[None, :, 2]
        dmin = d.min(1)
        cov = '  '.join(f'R{r} {100 * (dmin <= r).mean():3.0f}%' for r in (100, 150, 200, 300))
        near = (d <= 200).sum(1)
        print(f'{os.path.basename(src)[:34]:34s} garrisons {len(gs):3d} (seats {int(G[:, 3].sum()):4d})  '
              f'street pts {len(pts):5d}  covered {cov}  garrisons within 200 of a point: median {np.median(near):.0f}')


if __name__ == '__main__':
    main()
