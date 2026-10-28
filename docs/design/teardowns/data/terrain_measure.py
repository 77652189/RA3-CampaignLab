r"""Terrain complexity and how much of it a mission uses, retail campaign maps and ours, one ruler (read only: retail
archives, built mods in the Mods folder or work\staging).

  python -I -X utf8 docs/design/teardowns/data/terrain_measure.py            -> terrain.json + terrain.md here
  python -I -X utf8 docs/design/teardowns/data/terrain_measure.py j02 A4     (only these; the md is rebuilt from
                                                                              the whole json)

Only ground the player can reach counts: the walking grid's components that hold the start or an objective marker
(a landing's far shore); the rest of the stage (sea, cliffs, ground nobody can walk to: Facility's desert) is 'backdrop'.

Stages are layout_measure's: the MAP_SWITCH_BORDER rectangles that hold the start, smallest first (a 'moved' window
-- North Sea, Osaka -- is left out). Ground is mapstudy.terrain's (10-unit cells: height, land, the engine's own
impassable bits); walking is on 20-unit cells, each walkable when all four of its terrain cells are land and not
cliff (bridges laid over: layout_measure.walk_grid, stricter).

1. Terrain, over the last stage (the whole playable area by the end):
     tiers      heights of walkable ground in 20-unit bins, a tier = a run of bins each holding >= 4 % of it
     plateaus   flat walkable patches (mapstudy's 6 x 6 footprint rises < 8) >= 0.04 km2, by tier; 'raised' = above
                the lowest tier
     ramps      walkable climbing ground (rise to a walkable neighbour >= 1.5 per cell, 3 x 3 mean) >= 20 cells,
                within 80 of two flat patches (>= 0.01 km2) whose heights differ by >= 30, climbing >= 15 itself
                (any two levels, not only the tiers above); slope share =
                walkable ground that is not flat
     cliffs     impassable dry cells: share, length (km of the cliff mask's skeleton per km2), runs >= 30 cells
     water      share, bodies >= 0.02 km2, bridges (start + end object pairs)
     objects    garrisonable buildings (a civilian structure whose parent chain is a BaseCivilianStructure* without
                NoGarrison), tech buildings (mapstudy.kind), wall pieces (BaseWallPiece or
                named *wall*, not *cliffwall*: what blocks a way and can be shot down; trees, fences, rocks and
                props are left out -- RA3 gives infantry no cover bonus), ore nodes; per km2 of walkable ground
     junctions  the walkable ground's skeleton (holes < 0.02 km2 filled, spurs < 200 pruned): branch points, merged
                within 200
     chokes     skeleton runs no wider than CHOKE (300) where ground within 600 opens to twice that width
     overlook   share of the main routes (start -> each main marker, ground) with walkable ground >= 40 higher
                within 300 -- high ground beside the way; chokes_on_main: chokes the main routes pass through
   Routes start at the start; a target the start cannot reach by ground (a landing across water: Stalingrad) is
   routed from the main marker nearest the start instead (the beachhead), or not at all.
2. Use, per stage and for the part each stage newly opens (the player's view: only what is playable by then):
     used       walkable cells within 400 of a main marker, 300 of a bonus marker, 250 of a clustered enemy object
                (layout_measure.clusters), 200 of a main route (the shortest and, if no longer than 1.8 x, one
                alternative with the first one's corridor blocked), 150 of a bonus route, 200 of an enemy route
                (each spawn waypoint the scripts use and each enemy cluster >= 8 objects, to the start)
     tiles      500 x 500 tiles at least a quarter walkable, each given one role, first match:
                front    a clustered enemy object, a spawn point or a main marker
                side     a bonus marker, a tech or garrisonable building, ore away from the start (> 900)
                rear     within 900 of the start
                path     on a used route only
                empty    nothing of the above ('空地')
"""
import json
import math
import os
import re
import statistics
import sys

import numpy as np
from scipy import ndimage
from skimage import graph as skgraph
from skimage import morphology

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout_measure as LM  # noqa: E402
from layout_measure import big, mapscript, mapstudy, mapxml, OURS  # noqa: E402

OUT_JSON = os.path.join(HERE, 'terrain.json')
OUT_MD = os.path.join(HERE, 'terrain.md')
CELL = LM.CELL                  # 10: terrain cells
G = LM.CELL * LM.DOWN           # 20: walking cells
TIER_SHARE = 0.04
PLATEAU_MIN = 0.04              # km2
RAMP_RISE, RAMP_MIN = 1.5, 20   # world units of rise per 10-unit cell (~9 degrees), cells
CLIFF_RUN = 30
WATER_MIN = 0.02
HOLE = 0.02                     # km2: obstacles smaller than this do not split the skeleton
SPUR = 200
MERGE = 200
CHOKE, OPEN_R = 300, 600
HIGH, HIGH_R = 40.0, 300
R_MAIN, R_BONUS, R_FOE, R_ROUTE, R_BROUTE, R_EROUTE = 400, 300, 250, 200, 150, 200
TILE, REAR = 500, 900

_idx = None


def chain(template):
    global _idx
    if _idx is None:
        mapstudy.kind('x', '')                  # loads the index
        _idx = mapstudy._index
    out, t = [], template.lower()
    for _ in range(12):
        e = _idx.get(t)
        if not e:
            break
        out.append(e.get('inheritFrom', ''))
        t = e.get('inheritFrom', '').lower()
    return out, _idx.get(template.lower(), {})


def object_kind(template, owner):
    k = mapstudy.kind(template, owner)
    parents, e = chain(template)
    if k in ('civ_building', 'other', 'prop'):
        if any(p.lower().startswith('basecivilianstructure') and 'nogarrison' not in p.lower() for p in parents) \
                and 'NO_GARRISON' not in e.get('KindOf', ''):
            return 'garrison'
        if 'BaseWallPiece' in parents or ('wall' in template.lower() and 'cliffwall' not in template.lower()):
            return 'cover'
    return k


def disk(r):
    n = int(math.ceil(r / G))
    yy, xx = np.mgrid[-n:n + 1, -n:n + 1]
    return (xx * xx + yy * yy) <= n * n


def stamp(mask, pts, r):
    if not pts:
        return
    seed = np.zeros_like(mask)
    h, w = mask.shape
    for x, y in pts:
        i, j = int(x / G), int(y / G)
        if 0 <= j < h and 0 <= i < w:
            seed[j, i] = True
    mask |= ndimage.binary_dilation(seed, structure=disk(r))


def sub_mask(a, r):
    x0, y0, x1, y1 = (int(v / G) for v in r)
    s = np.zeros_like(a)
    s[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = True
    return s


def sub(a, r, cell):
    """The part of a (rows y, columns x, `cell` units) inside the world rectangle r."""
    x0, y0, x1, y1 = (int(v / cell) for v in r)
    return a[max(0, y0):max(0, y1), max(0, x0):max(0, x1)]


def tiers_of(heights):
    out = []
    if not heights.size:
        return out
    lo = np.floor(heights.min() / 20) * 20
    hist, edges = np.histogram(heights, bins=np.arange(lo, heights.max() + 40, 20))
    share = hist / heights.size
    k = 0
    while k < len(share):
        if share[k] >= TIER_SHARE:
            j = k
            while j + 1 < len(share) and share[j + 1] >= TIER_SHARE:
                j += 1
            out.append((float(edges[k]), float(edges[j + 1]), float(share[k:j + 1].sum())))
            k = j + 1
        else:
            k += 1
    return out


def band(h, tiers):
    lab = np.zeros(h.shape, np.int16)
    for n, (lo, hi, _) in enumerate(tiers, 1):
        lab[(h >= lo - 10) & (h < hi + 10)] = n
    return lab


def drop_small(mask, km2):
    comp, k = ndimage.label(mask)
    if not k:
        return mask
    sizes = ndimage.sum(np.ones_like(comp), comp, range(1, k + 1)) * G * G / 1e6
    keep = np.concatenate([[False], sizes >= km2])
    return keep[comp]


def prune(sk, n):
    sk = sk.copy()
    k = np.ones((3, 3), int)
    for _ in range(n):
        nb = ndimage.convolve(sk.astype(int), k, mode='constant') - sk
        ends = sk & (nb <= 1)
        if not ends.any():
            break
        sk &= ~ends
    return sk


def terrain_of(grids, g, rect, objs, paths):
    """Section 1 over rect; g = walking grid of that stage; paths = main route paths (lists of (y, x) in g)."""
    e, land, cliff, flat, relief = (sub(grids[k], rect, CELL) for k in ('e', 'land', 'cliff', 'flat', 'relief'))
    reach = sub(np.repeat(np.repeat(g, LM.DOWN, axis=0), LM.DOWN, axis=1), rect, CELL)
    reach = ndimage.binary_dilation(reach, iterations=2)       # cliff cells next to reachable ground stay in
    h_, w_ = min(reach.shape[0], e.shape[0]), min(reach.shape[1], e.shape[1])
    e, land, cliff, flat, relief, reach = (a[:h_, :w_] for a in (e, land, cliff, flat, relief, reach))
    walk = land & ~cliff & reach
    area = e.size * CELL * CELL / 1e6
    walk_km2 = walk.sum() * CELL * CELL / 1e6
    tiers = tiers_of(e[walk])
    lab = band(e, tiers)
    # plateaus: flat walkable components per tier
    plate, raised = [], 0
    for n in range(1, len(tiers) + 1):
        comp, k = ndimage.label(flat & walk & (lab == n))
        if not k:
            continue
        sizes = ndimage.sum(np.ones_like(comp), comp, range(1, k + 1)) * CELL * CELL / 1e6
        big_ = int((sizes >= PLATEAU_MIN).sum())
        plate.append(big_)
        if n > 1:
            raised += big_
    # ramps: walkable climbing ground (rise to a walkable neighbour >= RAMP_RISE per cell) touching flat ground of
    # two tiers and spanning at least half the step between them
    rise = np.zeros_like(e)
    for ax in (0, 1):
        d = np.abs(np.diff(e, axis=ax))
        both = walk[1:, :] & walk[:-1, :] if ax == 0 else walk[:, 1:] & walk[:, :-1]
        d = np.where(both, d, 0)
        if ax == 0:
            rise[1:, :] = np.maximum(rise[1:, :], d)
            rise[:-1, :] = np.maximum(rise[:-1, :], d)
        else:
            rise[:, 1:] = np.maximum(rise[:, 1:], d)
            rise[:, :-1] = np.maximum(rise[:, :-1], d)
    slope = walk & (ndimage.uniform_filter(rise, 3) >= RAMP_RISE)
    comp, k = ndimage.label(slope)
    ramps = 0
    if k:
        flat_lab, nf = ndimage.label(flat & walk)
        fs = ndimage.sum(np.ones_like(flat_lab), flat_lab, range(1, nf + 1))
        fh = ndimage.mean(e, flat_lab, range(1, nf + 1))
        keep = np.concatenate([[False], fs * CELL * CELL / 1e6 >= 0.01])
        flat_lab = np.where(keep[flat_lab], flat_lab, 0)
        sizes = ndimage.sum(np.ones_like(comp), comp, range(1, k + 1))
        objs_ = ndimage.find_objects(comp)
        for c in range(1, k + 1):
            if sizes[c - 1] < RAMP_MIN:
                continue
            sl = objs_[c - 1]
            sl = tuple(slice(max(0, s.start - 8), s.stop + 8) for s in sl)
            here = comp[sl] == c
            m = ndimage.binary_dilation(here, iterations=8)
            near = [fh[f - 1] for f in set(np.unique(flat_lab[sl][m])) - {0}]
            hs = e[sl][here]
            if near and max(near) - min(near) >= 30 and hs.max() - hs.min() >= 15:
                ramps += 1
    dry_cliff = cliff & land & reach
    comp, k = ndimage.label(dry_cliff, structure=np.ones((3, 3)))
    runs = int((ndimage.sum(np.ones_like(comp), comp, range(1, k + 1)) >= CLIFF_RUN).sum()) if k else 0
    cliff_km = morphology.skeletonize(dry_cliff).sum() * CELL / 1000.0
    water = ~land
    comp, k = ndimage.label(water)
    bodies = int((ndimage.sum(np.ones_like(comp), comp, range(1, k + 1)) * CELL * CELL / 1e6 >= WATER_MIN).sum()) \
        if k else 0
    counts = {}
    for kind_, x, y in objs:
        if LM.inside((x, y), rect):
            counts[kind_] = counts.get(kind_, 0) + 1
    # skeleton of the walking grid: junctions, chokes
    gg = drop_small(~drop_small(~g, HOLE), HOLE)          # holes, then islands, smaller than HOLE
    dt = ndimage.distance_transform_edt(gg) * G
    sk = prune(morphology.skeletonize(gg), int(SPUR / G))
    nb = ndimage.convolve(sk.astype(int), np.ones((3, 3), int), mode='constant') - sk
    branch = sk & (nb >= 3)
    jl, junctions = ndimage.label(ndimage.binary_dilation(branch, structure=disk(MERGE / 2)))
    wide = ndimage.maximum_filter(dt, footprint=disk(OPEN_R))
    narrow = sk & (2 * dt <= CHOKE) & (wide >= 2 * dt) & (dt > 0)
    cl, k = ndimage.label(ndimage.binary_dilation(narrow, structure=disk(60)))
    if k:
        keep = np.concatenate([[False], ndimage.sum(narrow, cl, range(1, k + 1)) >= 2])
        cl = np.where(keep[cl], cl, 0)
    chokes = len(set(np.unique(cl)) - {0})
    # high ground beside the main routes (heights on the walking grid)
    eh = e[:e.shape[0] // 2 * 2, :e.shape[1] // 2 * 2].reshape(e.shape[0] // 2, 2, e.shape[1] // 2, 2).mean(
        axis=(1, 3))
    x0, y0 = int(rect[0] / G), int(rect[1] / G)
    gsub = g[y0:y0 + eh.shape[0], x0:x0 + eh.shape[1]]
    eh = eh[:gsub.shape[0], :gsub.shape[1]]
    up = ndimage.maximum_filter(np.where(gsub, eh, -1e9), footprint=disk(HIGH_R))
    cells = seen = 0
    for p in paths:
        for y, x in p:
            yy, xx = y - y0, x - x0
            if 0 <= yy < eh.shape[0] and 0 <= xx < eh.shape[1]:
                cells += 1
                seen += up[yy, xx] - eh[yy, xx] >= HIGH
    hit = set()
    for p in paths:
        for y, x in p:
            if 0 <= y < cl.shape[0] and 0 <= x < cl.shape[1] and cl[y, x]:
                hit.add(int(cl[y, x]))
    per = lambda v: round(v / max(walk_km2, 1e-9), 2)  # noqa: E731
    return dict(area_km2=round(area, 2), walk_share=round(float(walk.sum() / walk.size), 2),
                tiers=len(tiers), tier_shares=[round(s, 2) for _, _, s in tiers],
                tier_heights=[round((lo + hi) / 2) for lo, hi, _ in tiers],
                plateaus=sum(plate), raised_plateaus=raised, ramps=ramps,
                slope_share=round(float((walk & ~flat).sum() / max(1, walk.sum())), 2),
                cliff_share=round(float(dry_cliff.sum() / dry_cliff.size), 3), cliff_km_per_km2=round(cliff_km / area, 2),
                cliff_runs=runs, water_share=round(float(water.sum() / water.size), 2), water_bodies=bodies,
                bridges=counts.get('bridge', 0) // 2,
                garrison=counts.get('garrison', 0), tech=counts.get('tech', 0), cover=counts.get('cover', 0),
                ore=counts.get('ore', 0), garrison_per_km2=per(counts.get('garrison', 0)),
                tech_per_km2=per(counts.get('tech', 0)), cover_per_km2=per(counts.get('cover', 0)),
                junctions=int(junctions), junctions_per_km2=per(junctions), chokes=chokes, chokes_per_km2=per(chokes),
                overlook=round(seen / cells, 2) if cells else None, chokes_on_main=len(hit))


def tree_paths(g, start, targets):
    """Ground paths (lists of (y, x) cells of g) from start to each target, None where unreachable."""
    a = LM.snap(g, start)
    if a is None:
        return [None] * len(targets)
    cost = np.where(g, 1.0, np.inf)
    mcp = skgraph.MCP_Geometric(cost)
    costs, _ = mcp.find_costs([(a[1], a[0])])
    out = []
    for t in targets:
        b = LM.snap(g, t)
        if b is None or not np.isfinite(costs[b[1], b[0]]):
            out.append(None)
            continue
        out.append(mcp.traceback((b[1], b[0])))
    return out


def routed(g, start, mains, targets):
    """tree_paths from the start; targets it cannot reach by ground from the main marker nearest the start."""
    if not start:
        return [None] * len(targets)
    out = tree_paths(g, start, targets)
    if any(p is None for p in out) and mains:
        near = min(mains, key=lambda q: math.hypot(q[0] - start[0], q[1] - start[1]))
        again = tree_paths(g, near, [q for q, p in zip(targets, out) if p is None])
        it = iter(again)
        out = [p if p is not None else next(it) for p in out]
    return out


def alternative(g, start, target, first):
    if first is None:
        return None
    g = g.copy()
    r, keep = int(LM.BLOCK / G), int(LM.OPEN_ENDS / G)
    a, b = first[0], first[-1]
    for y, x in first:
        if math.hypot(x - a[1], y - a[0]) < keep or math.hypot(x - b[1], y - b[0]) < keep:
            continue
        g[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1] = False
    p = tree_paths(g, start, [target])[0]
    return p if p is not None and len(p) <= LM.DETOUR_MAX * len(first) else None


def paint_paths(mask, paths, r):
    seed = np.zeros_like(mask)
    for p in paths:
        if p:
            ys, xs = zip(*p)
            seed[list(ys), list(xs)] = True
    if seed.any():
        mask |= ndimage.binary_dilation(seed, structure=disk(r))


def use_of(g, rect, prev, start, mains, bonuses, foes, spawns, big_cl, objs, main_paths, pic=None):
    """Section 2 over rect (prev: the stage before, or None)."""
    used = np.zeros_like(g)
    routes = np.zeros_like(g)
    ins = lambda ps: [p for p in ps if LM.inside(p, rect)]  # noqa: E731
    stamp(used, ins(mains), R_MAIN)
    stamp(used, ins(bonuses), R_BONUS)
    stamp(used, ins(foes), R_FOE)
    paint_paths(routes, main_paths, R_ROUTE)
    bpaths = routed(g, start, ins(mains), ins(bonuses))
    paint_paths(routes, bpaths, R_BROUTE)
    srcs = ins(spawns) + ins(big_cl)
    epaths = routed(g, start, ins(mains), srcs)
    paint_paths(routes, epaths, R_EROUTE)
    used |= routes
    used &= g
    x0, y0, x1, y1 = rect
    roles = dict(front=0, side=0, rear=0, path=0, empty=0)
    tiles = []
    new_roles = dict(roles)
    tc = int(TILE / G)
    kinds = {}
    for k, x, y in objs:
        kinds.setdefault(k, []).append((x, y))
    marks = dict(front=ins(foes) + ins(spawns) + ins(mains),
                 side=ins(bonuses) + ins(kinds.get('tech', [])) + ins(kinds.get('garrison', [])) +
                 [p for p in ins(kinds.get('ore', [])) if not start or math.hypot(p[0] - start[0], p[1] - start[1]) > REAR])
    for ty in range(int(y0 / TILE), int(math.ceil(y1 / TILE))):
        for tx in range(int(x0 / TILE), int(math.ceil(x1 / TILE))):
            tr = (max(x0, tx * TILE), max(y0, ty * TILE), min(x1, (tx + 1) * TILE), min(y1, (ty + 1) * TILE))
            cell = g[int(tr[1] / G):int(tr[3] / G), int(tr[0] / G):int(tr[2] / G)]
            if cell.size == 0 or cell.mean() < 0.25:
                continue
            in_t = lambda ps: any(tr[0] <= x < tr[2] and tr[1] <= y < tr[3] for x, y in ps)  # noqa: E731
            cx, cy = (tr[0] + tr[2]) / 2, (tr[1] + tr[3]) / 2
            if in_t(marks['front']):
                role = 'front'
            elif in_t(marks['side']):
                role = 'side'
            elif start and math.hypot(cx - start[0], cy - start[1]) < REAR:
                role = 'rear'
            elif routes[int(tr[1] / G):int(tr[3] / G), int(tr[0] / G):int(tr[2] / G)].any():
                role = 'path'
            else:
                role = 'empty'
            roles[role] += 1
            tiles.append((tr, role))
            if prev is None or not LM.inside((cx, cy), prev):
                new_roles[role] += 1
    if pic is not None:
        pic.update(g=g, used=used, routes=routes, tiles=tiles)
    n, nn = sum(roles.values()), sum(new_roles.values())
    gm = g.copy()
    if prev is not None:
        px0, py0, px1, py1 = (int(v / G) for v in prev)
        gm[max(0, py0):py1, max(0, px0):px1] = False
    return dict(used=round(float(used.sum() / max(1, g.sum())), 2),
                used_new=round(float((used & gm).sum() / max(1, gm.sum())), 2) if prev is not None else None,
                tiles=n, roles={k: round(v / n, 2) for k, v in roles.items()} if n else {},
                new_tiles=nn, new_roles={k: round(v / nn, 2) for k, v in new_roles.items()} if nn and prev else {})


def walk_grid(grids, bridges, rect):
    """layout_measure.walk_grid, but a 20-unit cell is walkable only when all four of its 10-unit cells are: the
    majority rule leaks through cliffs one or two cells thin (Facility's walls)."""
    land = grids['land'] & ~grids['cliff']
    h, w = land.shape
    for a, b in bridges:
        steps = int(math.hypot(b[0] - a[0], b[1] - a[1]) / 5) + 1
        for s in np.linspace(0, 1, steps):
            x, y = a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s
            i, j = int(x / CELL), int(y / CELL)
            land[max(0, j - 4):j + 5, max(0, i - 4):i + 5] = True
    d = LM.DOWN
    hh, ww = h // d, w // d
    g = land[:hh * d, :ww * d].reshape(hh, d, ww, d).all(axis=(1, 3))
    return g & sub_mask(g, rect)


def reachable(g, seeds):
    """The walking grid's components that hold (within 600) the start or an objective marker."""
    comp, k = ndimage.label(g)
    keep = set()
    for p in seeds:
        s = LM.snap(g, p)
        if s is not None:
            keep.add(int(comp[s[1], s[0]]))
    keep.discard(0)
    return np.isin(comp, sorted(keep)) if keep else g


def measure(name, m):
    scripts = LM.script_list(m)
    rects, used, firsts = LM.stages(m, scripts)
    sides = mapstudy.players(m)
    human = next((n for n, p in sides.items() if p.get('playerIsHuman')), 'Player_1')
    enemies = set(sides.get(human, {}).get('playerEnemies', '').split())
    t, grids = mapstudy.terrain(m)
    named, wps, mine, foes, bridges, objs = {}, {}, [], [], [], []
    pend = None
    for o in mapxml.objects(m):
        owner = str(o['props'].get('originalOwner', ''))
        side = owner.split('/')[0]
        k = object_kind(o['template'], owner)
        p = (o['x'], o['y'])
        nm = str(o['props'].get('objectName', ''))
        if nm:
            named[nm] = p
        if o['template'] == '*Waypoints/Waypoint':
            wps[str(o['props'].get('waypointName', ''))] = p
            continue
        if k == 'bridge':
            if pend is None:
                pend = p
            else:
                bridges.append((pend, p))
                pend = None
        if side == human:
            mine.append(p)
        elif side in enemies:
            foes.append(p)
        else:
            objs.append((k, o['x'], o['y']))
    area = lambda k: (rects[k][2] - rects[k][0]) * (rects[k][3] - rects[k][1])  # noqa: E731
    guess = min(firsts or used, key=area) if (firsts or used) else None
    first = rects[guess] if guess is not None else (0, 0, t['size'][0], t['size'][1])
    mine_in = [p for p in mine if LM.inside(p, first, LM.ENTER)] or mine
    start = tuple(float(v) for v in np.median(np.array(mine_in), axis=0)) if mine_in else None
    order, _ = LM.order_stages(rects, used, firsts, start)
    if not order:
        order = [None]
    spawn = set()
    for title, marks, conds, acts in scripts:
        for an, args, _ in acts:
            for _, v in args:
                s = v[2] if isinstance(v, tuple) and len(v) == 3 else v
                if isinstance(s, str) and s in wps and re.search(r'REINFORCEMENT|CREATE|SPAWN', an):
                    spawn.add(s)
    spawns = [wps[s] for s in spawn]
    goals, links = mapstudy.objectives(m)
    bonus_of = {g_['name']: g_['bonus'] for g_ in goals}
    mains, bonuses = [], []
    for o, _, target in links:
        p = named.get(target) or wps.get(target)
        if p:
            (bonuses if bonus_of.get(o) else mains).append(p)
    mains, bonuses = sorted(set(mains)), sorted(set(bonuses))
    cl = LM.clusters(foes)
    clustered = []
    if cl:
        pts = np.array(foes, float)
        for c, n in cl:
            d = np.hypot(pts[:, 0] - c[0], pts[:, 1] - c[1])
            clustered += [tuple(q) for q in pts[d < 900]]
    big_cl = [tuple(c) for c, n in cl if n >= 8]
    out = dict(map=name, start=[round(v) for v in start] if start else None, stages=[])
    prev = None
    for k in order:
        r = rects[k] if k is not None else (0, 0, t['size'][0], t['size'][1])
        g_all = walk_grid(grids, bridges, r)
        g = reachable(g_all, ([start] if start else []) + mains + bonuses)
        ms = [p for p in mains if LM.inside(p, r)]
        mp = routed(g, start, ms, ms)
        alts = [alternative(g, (p[0][1] * G, p[0][0] * G), q, p) if p else None for q, p in zip(ms, mp)]
        paths = [p for p in mp if p] + [p for p in alts if p]
        st = dict(border=k, rect=[round(v) for v in r])
        pic = {}
        st['use'] = use_of(g, r, prev, start, mains, bonuses, clustered, spawns, big_cl, objs, paths, pic)
        if PNG:
            picture(os.path.join(PNG, f'{name}_s{len(out["stages"])}.png'), pic, grids, start, mains, bonuses)
        st['terrain'] = terrain_of(grids, g, r, objs, [p for p in mp if p])
        st['terrain']['backdrop'] = round(float(1 - g.sum() / max(1, g_all[sub_mask(g_all, r)].size)), 2)
        out['stages'].append(st)
        prev = r
    return out


PNG = os.environ.get('TERRAIN_PNG')      # a folder: one picture per stage (checking the measure by eye)
COLOURS = dict(front=(200, 60, 60), side=(60, 120, 220), rear=(60, 170, 90), path=(200, 170, 60), empty=(0, 0, 0))


def picture(path, pic, grids, start, mains, bonuses):
    from PIL import Image, ImageDraw
    g, used = pic['g'], pic['used']
    eh = grids['e'][::LM.DOWN, ::LM.DOWN][:g.shape[0], :g.shape[1]]
    lo, hi = np.percentile(eh, [2, 98])
    shade = np.clip((eh - lo) / max(1, hi - lo), 0, 1)
    img = np.zeros(g.shape + (3,), np.uint8)
    img[..., :] = (shade * 60)[..., None].astype(np.uint8)              # backdrop: dark, by height
    walk = (90 + shade * 110).astype(np.uint8)
    img[g] = np.stack([walk, walk, walk], -1)[g]                        # reachable ground: grey, by height
    img[used] = (np.array([110, 200, 110]) * (0.6 + 0.4 * shade[used, None])).astype(np.uint8)
    im = Image.fromarray(img[::-1])
    d = ImageDraw.Draw(im)
    H = g.shape[0]
    for (x0, y0, x1, y1), role in pic['tiles']:
        box = [x0 / G, H - y1 / G, x1 / G - 1, H - y0 / G - 1]
        d.rectangle(box, outline=COLOURS[role], width=2 if role != 'empty' else 1)
        if role == 'empty':
            d.line([box[0], box[1], box[2], box[3]], fill=(230, 60, 230), width=1)
    for pts, col in ((mains, (255, 230, 0)), (bonuses, (0, 230, 255))):
        for x, y in pts:
            d.ellipse([x / G - 4, H - y / G - 4, x / G + 4, H - y / G + 4], outline=col, width=2)
    if start:
        d.rectangle([start[0] / G - 5, H - start[1] / G - 5, start[0] / G + 5, H - start[1] / G + 5], fill=(0, 255, 0))
    im.save(path)


def jobs(parts):
    yield from LM.jobs(parts)


# ---------------------------------------------------------------- table
def short(name):
    if name.startswith('ours_'):
        return name.split('_')[1]
    s = name.replace('camp_', '').replace('ep01_', 'up-')
    return '_'.join(s.split('_')[:2])


def write_md(data):
    rows, keys = [], ['tiers', 'raised_plateaus', 'ramps', 'slope_share', 'cliff_km_per_km2', 'water_share',
                      'bridges', 'garrison', 'tech', 'cover', 'junctions_per_km2', 'chokes', 'chokes_on_main',
                      'overlook']
    retail = {k: [] for k in keys + ['used', 'empty', 'first_used', 'first_empty', 'new_used', 'new_empty']}
    ours = {k: [] for k in retail}
    lines = ['# 地形复杂度和地图利用率（每关一行）', '',
             '由 [terrain_measure.py](terrain_measure.py) 生成，口径见脚本开头。地形一栏量的是最后一个阶段'
             '（关末整块可玩区）；利用率按阶段量：第一块、关末整块、每个阶段新开的那一块。', '',
             '| 关 | 层 | 高台 | 坡道 | 斜坡占比 | 悬崖 km/km² | 水 | 桥 | 驻军楼 | 科技 | 墙段 | 路口/km² | 隘口 | 主路过隘口 | '
             '主路旁有高地 | 第一块：用到 / 空地 | 关末：用到 / 空地 | 新开的块：用到 / 空地 |',
             '|' + '---|' * 18]
    for name in sorted(data, key=lambda n: (n.startswith('ours'), n)):
        v = data[name]
        if 'error' in v or not v.get('stages'):
            lines.append(f'| {short(name)} | 读不出：{v.get("error", "无阶段")} |' + ' |' * 17)
            continue
        last, first = v['stages'][-1], v['stages'][0]
        tt = last['terrain']
        bag = ours if name.startswith('ours') else retail
        for k in keys:
            if tt.get(k) is not None:
                bag[k].append(tt[k])
        bag['used'].append(last['use']['used'])
        bag['empty'].append(last['use']['roles'].get('empty', 0))
        bag['first_used'].append(first['use']['used'])
        bag['first_empty'].append(first['use']['roles'].get('empty', 0))
        news = [s['use'] for s in v['stages'][1:] if s['use'].get('used_new') is not None]
        nu = '、'.join(f"{u['used_new']:.2f} / {u['new_roles'].get('empty', 0):.2f}" for u in news) or '—'
        for u in news:
            bag['new_used'].append(u['used_new'])
            bag['new_empty'].append(u['new_roles'].get('empty', 0))
        ov = '—' if tt['overlook'] is None else f"{tt['overlook']:.2f}"
        lines.append(
            f"| {short(name)} | {tt['tiers']} | {tt['raised_plateaus']} | {tt['ramps']} | {tt['slope_share']:.2f} | "
            f"{tt['cliff_km_per_km2']:.2f} | {tt['water_share']:.2f} | {tt['bridges']} | {tt['garrison']} | {tt['tech']} | "
            f"{tt['cover']} | {tt['junctions_per_km2']:.2f} | {tt['chokes']} | {tt['chokes_on_main']} | {ov} | "
            f"{first['use']['used']:.2f} / {first['use']['roles'].get('empty', 0):.2f} | "
            f"{last['use']['used']:.2f} / {last['use']['roles'].get('empty', 0):.2f} | {nu} |")
    med = lambda xs: round(statistics.median(xs), 2) if xs else None  # noqa: E731
    lines += ['', '## 中位数', '', '| 量 | 原版 | 我们 |', '|---|---|---|']
    names = dict(tiers='高度层数', raised_plateaus='高台块数（高于最低层、≥0.04 km²）', ramps='坡道数',
                 slope_share='斜坡占可走地面', cliff_km_per_km2='悬崖长度 km/km²', water_share='水面占比', bridges='桥',
                 garrison='能驻军的建筑', tech='科技建筑', cover='墙段', junctions_per_km2='路口 / km²',
                 chokes='隘口', chokes_on_main='主路经过的隘口', overlook='主路旁有高地的比例', used='关末：任务用到的可走地面',
                 empty='关末：空地块占比', first_used='第一块：用到', first_empty='第一块：空地块',
                 new_used='新开的块：用到', new_empty='新开的块：空地块')
    for k, label in names.items():
        lines.append(f'| {label} | {med(retail[k])} | {med(ours[k])} |')
    lines.append('')
    lines.append(f'原版 {len(retail["used"])} 张，我们 {len(ours["used"])} 关。')
    open(OUT_MD, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')


def main():
    parts = sys.argv[1:]
    old = json.load(open(OUT_JSON, encoding='utf-8')) if os.path.exists(OUT_JSON) else {}
    for name, load in jobs(parts):
        try:
            old[name] = measure(name, load())
            s = old[name]['stages'][-1]
            print(name, s['terrain']['tiers'], 'tiers', s['terrain']['ramps'], 'ramps', 'used', s['use']['used'],
                  'empty', s['use']['roles'].get('empty'), flush=True)
        except Exception as ex:                 # one broken map must not stop the table
            import traceback
            traceback.print_exc()
            old[name] = dict(map=name, error=repr(ex))
        with open(OUT_JSON, 'w', encoding='utf-8') as fh:
            json.dump(old, fh, ensure_ascii=False, indent=1)
    write_md(old)


if __name__ == '__main__':
    main()
