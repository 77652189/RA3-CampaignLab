r"""Spatial layout of campaign maps, retail and ours, with one ruler (read only: retail archives, built mods).

  python -I -X utf8 docs/design/teardowns/data/layout_measure.py            -> layout.json next to this file
  python -I -X utf8 docs/design/teardowns/data/layout_measure.py j02 A4 CampA4Win   (only these: part of a retail
                                                         map name, one of our level ids, or any built mod name)

Per map and per border stage (MAP_SWITCH_BORDER rectangles that hold the start, smallest first; borders the
scripts switch to that do not hold it are listed as 'moved': the playable window jumps elsewhere):
  start      the human player's objects inside the first stage (median), normalised in each stage's rectangle;
             'corner' when both distances to the nearest edges are < 0.25 of that side, 'edge' when one is, else
             'centre'; 'entering' when it lies just outside (within 600: a force driving in from the map edge)
  enemy      clusters of enemy-owned objects (single linkage, 400 world units, >= 4 objects) and script spawn
             waypoints (the waypoints named by *REINFORCEMENT* / *CREATE* / *SPAWN* actions, any side) inside the
             stage or within 600 of it; their compass octants seen from the start (clusters of >= 8 objects)
  goals      every objective's green markers (LINK_MISSION_OBJECTIVE_TO_OBJECT / _WAYPOINT): distance and octant
             from the start, the first stage that contains them; main goals get a route count, bonus goals a
             detour (extra length versus going straight to the nearest main marker) and a risk (distance to the
             nearest enemy cluster)
  routes     ground routes only (land, not cliff, plus bridges; naval, amphibious and air are not counted): the
             shortest path on a 20-unit grid, then the corridor around it (radius 250, open near both ends) is
             blocked and the search repeated, up to 3 more times; a route counts if it is shorter than 1.8 x the
             first
"""
import json
import math
import os
import re
import sys
from collections import deque

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'campaign'))
import mapscript  # noqa: E402
import mapstudy  # noqa: E402
import mapterrain  # noqa: E402
import mapxml  # noqa: E402

from ra3voice import big  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'layout.json')
CELL = mapterrain.CELL
DOWN = 2                      # route grid: 20 world units
LINK = 400
CLUSTER_MIN = 4
NEAR_BORDER = 600
ENTER = 600                   # a start this close outside a border is a force entering from the map edge
BLOCK = 250
OPEN_ENDS = 450
DETOUR_MAX = 1.8
OCT = ['东', '东北', '北', '西北', '西', '西南', '南', '东南']

# our levels: the newest full build of each (a check build compiles the whole mission plus its check)
OURS = {'A4': 'CampA4Idle', 'A5': 'CampA5Win', 'A7': 'CampA7Pincer', 'A8': 'CampA8S', 'J3': 'CampJ3Run',
        'J4': 'CampJ4', 'J5': 'CampJ5Lose', 'J7': 'CampJ7Late', 'S2': 'CampS2Escape', 'S5': 'CampS5Trap',
        'S6': 'CampS6Lose'}


def octant(dx, dy):
    return OCT[int(((math.degrees(math.atan2(dy, dx)) + 360 + 22.5) % 360) // 45)]


def script_list(m):
    out = []
    for _, n in m.walk():
        if n.name != 'Script':
            continue
        title = m.string(n.head, 0)[0]
        conds, acts = [], []
        for _, k in m.walk(n.kids):
            if k.name == 'Condition':
                conds.append(m.content(k))
            elif k.name in ('ScriptAction', 'ScriptActionFalse'):
                acts.append(m.content(k))
        out.append((title, m._script_marks(n), conds, acts))
    return out


def stages(m, scripts):
    hm = mapterrain.HeightMap(m)
    rects = [tuple(v * CELL for v in r) for r in hm.borders()]
    used, first = [], []
    for title, marks, conds, acts in scripts:
        for name, args, _ in acts:
            if name == 'MAP_SWITCH_BORDER':
                k = args[0][1] if not isinstance(args[0][1], tuple) else args[0][1][0]
                k = int(k)
                if k >= len(rects):
                    continue
                used.append(k)
                plain = all(c[0] == 'CONDITION_TRUE' for c in conds)
                if 'off' not in marks and (plain or re.search(r'setup|init|start|intro|border|boundar', title, re.I)):
                    first.append(k)
    return rects, sorted(set(used)), sorted(set(first))


def order_stages(rects, used, first, start):
    """Expanding stages: the used borders that hold the start (or lie within ENTER of it), smallest first; the
    others are 'moved' windows (the playable area jumps somewhere else: North Sea, Osaka)."""
    if not used:
        return [0] if rects else [], []
    area = lambda k: (rects[k][2] - rects[k][0]) * (rects[k][3] - rects[k][1])
    holds = [k for k in used if start is None or inside(start, rects[k], ENTER)]
    if not holds:
        holds = [min(first or used, key=area)]
    return sorted(holds, key=area), [k for k in used if k not in holds]


def inside(p, r, pad=0.0):
    return r[0] - pad <= p[0] <= r[2] + pad and r[1] - pad <= p[1] <= r[3] + pad


def clusters(points):
    if not points:
        return []
    pts = np.array(points, float)
    n = len(pts)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for i in range(n):
        d = np.hypot(pts[i + 1:, 0] - pts[i, 0], pts[i + 1:, 1] - pts[i, 1])
        for j in np.nonzero(d < LINK)[0]:
            a, b = find(i), find(i + 1 + j)
            if a != b:
                parent[a] = b
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return [(pts[g].mean(axis=0), len(g)) for g in groups.values() if len(g) >= CLUSTER_MIN]


def walk_grid(m, grids, bridges, rect):
    land = grids['land'] & ~grids['cliff']
    h, w = land.shape
    for a, b in bridges:
        steps = int(math.hypot(b[0] - a[0], b[1] - a[1]) / 5) + 1
        for t in np.linspace(0, 1, steps):
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            i, j = int(x / CELL), int(y / CELL)
            land[max(0, j - 4):j + 5, max(0, i - 4):i + 5] = True
    hh, ww = h // DOWN, w // DOWN
    g = land[:hh * DOWN, :ww * DOWN].reshape(hh, DOWN, ww, DOWN).mean(axis=(1, 3)) >= 0.5
    x0, y0, x1, y1 = (int(v / CELL / DOWN) for v in rect)
    mask = np.zeros_like(g)
    mask[max(0, y0):min(hh, y1), max(0, x0):min(ww, x1)] = True
    return g & mask


def snap(g, p):
    i, j = int(p[0] / CELL / DOWN), int(p[1] / CELL / DOWN)
    ys, xs = np.nonzero(g)
    if not len(xs):
        return None
    k = np.argmin((xs - i) ** 2 + (ys - j) ** 2)
    if (xs[k] - i) ** 2 + (ys[k] - j) ** 2 > (600 / CELL / DOWN) ** 2:
        return None
    return int(xs[k]), int(ys[k])


def bfs(g, a, b):
    h, w = g.shape
    prev = -np.ones(h * w, np.int64)
    seen = np.zeros(h * w, bool)
    s, t = a[1] * w + a[0], b[1] * w + b[0]
    seen[s] = True
    q = deque([s])
    flat = g.ravel()
    while q:
        c = q.popleft()
        if c == t:
            break
        cy, cx = divmod(c, w)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w:
                k = ny * w + nx
                if flat[k] and not seen[k]:
                    seen[k] = True
                    prev[k] = c
                    q.append(k)
    if not seen[t]:
        return None
    path, c = [], t
    while c != s:
        path.append(divmod(c, w))
        c = prev[c]
    return path


def routes(g, a, b):
    if a is None or b is None:
        return None, None
    g = g.copy()
    first = bfs(g, a, b)
    if first is None:
        return 0, None
    n, base = 1, len(first)
    path = first
    r = int(BLOCK / CELL / DOWN)
    keep = int(OPEN_ENDS / CELL / DOWN)
    for _ in range(3):
        for y, x in path:
            if math.hypot(x - a[0], y - a[1]) < keep or math.hypot(x - b[0], y - b[1]) < keep:
                continue
            g[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1] = False
        path = bfs(g, a, b)
        if path is None or len(path) > DETOUR_MAX * base:
            break
        n += 1
    return n, base * CELL * DOWN


def measure(name, m):
    scripts = script_list(m)
    rects, used, firsts = stages(m, scripts)
    sides = mapstudy.players(m)
    human = next((n for n, p in sides.items() if p.get('playerIsHuman')), 'Player_1')
    enemies = set(sides.get(human, {}).get('playerEnemies', '').split())
    objs = mapxml.objects(m)
    t, grids = mapstudy.terrain(m)
    named, wps, mine, foes, bridges = {}, {}, [], [], []
    pend = None
    for o in objs:
        owner = str(o['props'].get('originalOwner', ''))
        side = owner.split('/')[0]
        k = mapstudy.kind(o['template'], owner)
        p = (o['x'], o['y'])
        nm = str(o['props'].get('objectName', ''))
        if nm:
            named[nm] = p
        if o['template'] == '*Waypoints/Waypoint':
            wps[str(o['props'].get('waypointName', ''))] = p
        elif k == 'bridge':
            if pend is None:
                pend = p
            else:
                bridges.append((pend, p))
                pend = None
        elif side == human:
            mine.append(p)
        elif side in enemies:
            foes.append(p)
    area = lambda k: (rects[k][2] - rects[k][0]) * (rects[k][3] - rects[k][1])
    guess = min(firsts or used, key=area) if (firsts or used) else None
    first = rects[guess] if guess is not None else (0, 0, t['size'][0], t['size'][1])
    mine_in = [p for p in mine if inside(p, first, ENTER)] or mine
    start = tuple(float(v) for v in np.median(np.array(mine_in), axis=0)) if mine_in else None
    for key in ('Player_1_Start', 'Player_1 Start', 'wp_player_1_start'):
        if start is None and key in wps:
            start = wps[key]
    order, moved = order_stages(rects, used, firsts, start)
    # spawn waypoints the scripts use
    spawn = set()
    for title, marks, conds, acts in scripts:
        for an, args, _ in acts:
            for _, v in args:
                s = v[2] if isinstance(v, tuple) and len(v) == 3 else v
                if isinstance(s, str) and s in wps and re.search(r'REINFORCEMENT|CREATE|SPAWN', an):
                    spawn.add(s)
    goals, links = mapstudy.objectives(m)
    marks = {}
    for o, _, target in links:
        p = named.get(target) or wps.get(target)
        if p:
            marks.setdefault(o, []).append(p)
    out = dict(map=name, size=t['size'], human=human, start=[round(v) for v in start] if start else None,
               stages=[], goals=[], moved=[dict(border=k, rect=[round(v) for v in rects[k]]) for k in moved])
    walk_cache = {}
    for si, k in enumerate(order):
        r = rects[k]
        w, h = r[2] - r[0], r[3] - r[1]
        st = dict(border=k, rect=[round(v) for v in r], area_km2=round(w * h / 1e6, 2))
        if start:
            nx, ny = (start[0] - r[0]) / w, (start[1] - r[1]) / h
            u, v = min(nx, 1 - nx), min(ny, 1 - ny)
            st['start_norm'] = [round(nx, 2), round(ny, 2)]
            st['start_place'] = ('entering' if inside(start, r, ENTER) else 'outside') if not inside(start, r) else \
                'corner' if u < 0.25 and v < 0.25 else 'edge' if min(u, v) < 0.25 else 'centre'
            st['start_to_centre'] = round(math.hypot(nx - 0.5, ny - 0.5) / math.hypot(0.5, 0.5), 2)
        cl = [(c, n) for c, n in clusters([p for p in foes if inside(p, r)])]
        sp = [wps[s] for s in spawn if inside(wps[s], r, NEAR_BORDER)]
        st['enemy_clusters'] = [dict(at=[round(c[0]), round(c[1])], n=int(n),
                                     dir=octant(c[0] - start[0], c[1] - start[1]) if start else None,
                                     dist=round(math.hypot(c[0] - start[0], c[1] - start[1])) if start else None)
                                for c, n in sorted(cl, key=lambda q: -q[1])[:8]]
        st['spawn_points'] = len(sp)
        dirs = {e['dir'] for e in st['enemy_clusters'] if e['n'] >= 8} | \
            ({octant(p[0] - start[0], p[1] - start[1]) for p in sp} if start else set())
        st['threat_octants'] = sorted(dirs, key=OCT.index)
        out['stages'].append(st)
        walk_cache[si] = walk_grid(m, grids, bridges, r)
    allcl = []
    for st in out['stages']:
        allcl += [e['at'] for e in st['enemy_clusters']]
    mains = [p for g in goals if not g['bonus'] for p in marks.get(g['name'], [])]
    for g in goals:
        ps = marks.get(g['name'], [])
        e = dict(name=g['name'], title=g['title'], bonus=g['bonus'], markers=len(ps), on_done=g.get('on_done', []))
        if ps and start:
            c = tuple(np.mean(np.array(ps), axis=0))
            e['dist'] = round(math.hypot(c[0] - start[0], c[1] - start[1]))
            e['dir'] = octant(c[0] - start[0], c[1] - start[1])
            e['stage'] = next((i for i, k in enumerate(order) if inside(c, rects[k])), None)
            if e['stage'] is None and any(inside(c, rects[k]) for k in moved):
                e['in_moved'] = True
            if e['stage'] is not None:
                r = rects[order[e['stage']]]
                e['dist_norm'] = round(e['dist'] / math.hypot(r[2] - r[0], r[3] - r[1]), 2)
            if not g['bonus'] and e['stage'] is not None:
                gg = walk_cache[e['stage']]
                n, length = routes(gg, snap(gg, start), snap(gg, c))
                e['routes'], e['path_len'] = n, round(length) if length else None
            if g['bonus']:
                near = min(mains, key=lambda q: math.hypot(q[0] - c[0], q[1] - c[1])) if mains else None
                if near is not None:
                    straight = math.hypot(near[0] - start[0], near[1] - start[1])
                    via = e['dist'] + math.hypot(near[0] - c[0], near[1] - c[1])
                    e['detour'] = round(via - straight)
                if allcl:
                    e['risk_dist'] = round(min(math.hypot(q[0] - c[0], q[1] - c[1]) for q in allcl))
        out['goals'].append(e)
    return out


def jobs(parts):
    for _, arc, n, short in mapstudy.retail_maps():
        if not parts or any(p in short for p in parts):
            yield short, (lambda arc=arc, n=n: mapscript.MapFile(big.read_files(arc, [n])[n]))
    import maprender
    for level, mod in OURS.items():
        if not parts or level in parts or mod in parts:
            yield f'ours_{level}_{mod}', (lambda mod=mod: maprender.load(mod))
    for p in parts:                             # any other built mod named on the command line, e.g. CampA4Win
        if p.startswith('Camp') and p not in OURS.values():
            yield f'ours_{p}', (lambda p=p: maprender.load(p))


def main():
    parts = sys.argv[1:]
    old = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    for name, load in jobs(parts):
        try:
            old[name] = measure(name, load())
            s0 = old[name]['stages'][0] if old[name]['stages'] else {}
            print(name, s0.get('start_place'), s0.get('start_norm'), len(old[name]['stages']), 'stages', flush=True)
        except Exception as ex:                 # one broken map must not stop the table
            print('FAIL', name, repr(ex), flush=True)
            old[name] = dict(map=name, error=repr(ex))
        with open(OUT, 'w', encoding='utf-8') as fh:
            json.dump(old, fh, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
