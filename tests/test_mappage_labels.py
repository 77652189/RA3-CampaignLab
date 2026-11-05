"""The map page's site-name layout (experimental/mappage/labels.js): run under node on A4's sites at the widths the map
takes on a 1024 and a 375 wide screen, and the shown labels must not overlap one another, cover another site's dot,
leave the map or have a leader line run through a label. Checked here in Python, not with labels.js's own helpers."""
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / 'experimental' / 'mappage' / 'labels.js'
_spec = importlib.util.spec_from_file_location('mappage', ROOT / 'experimental' / 'mappage' / 'mappage.py')
mappage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mappage)

pytestmark = pytest.mark.skipif(shutil.which('node') is None, reason='node not installed')

PX = 15                      # template.html LABEL: label font size in screen pixels


def _a4():
    m, _, _ = mappage.build.resolve('a4', '')
    mp = mappage.parts.merged(m, None).map
    world = list(getattr(mp, 'BORDERS', {}).get('whole', (0.0, 0.0, 5000.0, 5000.0)))
    zh = mappage.site_names(mp)
    sites = [(k, zh.get(k, ''), s.x, s.y) for k, s in mp.SITES.items() if s.r < 1000]
    return world, sites


def _items(world, sites, k):
    """Each site's dot (svg units, y down) and a label box sized the way the page draws it: CJK 1 em, the code name at
    0.8 em with Latin letters about 0.6 em wide."""
    x0, _, _, y1 = world
    em = PX * k
    out = []
    for key, zh, x, y in sites:
        w = (len(zh) + 0.5 if zh else 0) * em + len(key) * 0.8 * em * 0.6 + 4 * k
        it = {'x': x - x0, 'y': y1 - y, 'w': w, 'h': 1.25 * em + 4 * k}
        if zh:
            it['ws'] = (len(zh) + 0.5) * em + 4 * k
        out.append(it)
    return out


def _place(items, bounds, o):
    """labels.js's place(); o is the options, or a number k (map units per screen pixel) for the page's own opts(k).
    Returns (the placement, the options used)."""
    oj = f'L.opts({float(o)})' if isinstance(o, (int, float)) else json.dumps(o)
    js = f"""const L = require({json.dumps(str(LABELS))}); const o = {oj};
process.stdout.write(JSON.stringify([L.place({json.dumps(items)}, {json.dumps(bounds)}, o), o]));"""
    r = subprocess.run([shutil.which('node'), '-e', js], capture_output=True, text=True, encoding='utf-8', timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _overlap(a, b):
    return a['x'] < b['x'] + b['w'] and b['x'] < a['x'] + a['w'] and a['y'] < b['y'] + b['h'] and b['y'] < a['y'] + a['h']


def _seg_hits(p, q, b, n=200):
    """Sampled: does segment p-q pass through box b's inside."""
    for t in range(1, n):
        x, y = p[0] + (q[0] - p[0]) * t / n, p[1] + (q[1] - p[1]) * t / n
        if b['x'] + 1e-6 < x < b['x'] + b['w'] - 1e-6 and b['y'] + 1e-6 < y < b['y'] + b['h'] - 1e-6:
            return True
    return False


def _check(items, res, bounds, dot):
    shown = [(i, r) for i, r in enumerate(res) if r['shown']]
    for a in range(len(shown)):
        i, r = shown[a]
        assert bounds[0] <= r['x'] and r['x'] + r['w'] <= bounds[2] and bounds[1] <= r['y'] and r['y'] + r['h'] <= bounds[3]
        for b in range(a + 1, len(shown)):
            assert not _overlap(r, shown[b][1]), f'labels {i} and {shown[b][0]} overlap'
        for j, it in enumerate(items):
            if j != i:
                d = {'x': it['x'] - dot, 'y': it['y'] - dot, 'w': 2 * dot, 'h': 2 * dot}
                assert not _overlap(r, d), f'label {i} covers dot {j}'
        if r['leader']:
            p, q = r['leader']
            for j, other in shown:
                if j != i:
                    assert not _seg_hits(p, q, other), f'leader of {i} crosses label {j}'
    return len(shown)


@pytest.mark.parametrize('screen, map_px', [(1024, 564), (375, 375 - 32)])
def test_a4_labels_do_not_overlap(screen, map_px):
    """The two widths the hand check uses (the map's width measured in the page at a 1024 wide window; full width less
    gutters at 375). Fewer fit at 375 and the rest wait for hover -- but no two shown ever overlap."""
    world, sites = _a4()
    W, H = world[2] - world[0], world[3] - world[1]
    k = W / map_px
    items = _items(world, sites, k)
    bounds = [0, 0, W, H]
    res, o = _place(items, bounds, k)
    n = _check(items, res, bounds, o['dot'])
    assert n >= (0.6 if screen == 1024 else 0.25) * len(items), f'only {n} of {len(items)} shown'


def test_crowded_cluster_spreads_with_leaders():
    """Twelve sites packed into a few labels' room: some go further out with a leader, none overlap."""
    items = [{'x': 2000 + 40 * (i % 4), 'y': 2000 + 40 * (i // 4), 'w': 300, 'h': 60} for i in range(12)]
    o = {'dot': 32, 'gap': 10, 'rings': 4, 'step': 70}
    res, _ = _place(items, [0, 0, 5000, 5000], o)
    n = _check(items, res, [0, 0, 5000, 5000], o['dot'])
    assert n >= 8 and any(r['leader'] for r in res)
