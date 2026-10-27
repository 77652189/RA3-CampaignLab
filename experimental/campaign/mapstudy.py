r"""How retail campaign maps are built, in numbers and one picture each -- the design language our levels copy.

  python -I -X utf8 experimental/campaign/mapstudy.py [name part ...]        -> work/mapstudy/<map>.json / .png
  python -I -X utf8 experimental/campaign/mapstudy.py --ours CampA4 ...      (our built mods, same measures)
  python -I -X utf8 experimental/campaign/mapstudy.py --table                -> the summary table of everything studied

Per map (playable area only, one cell = 10 world units):
  terrain   heights in world units (elevation * REAL); water height (GlobalWaterSettings); land share; `flat`:
            land whose 6 x 6 cell window (a building's footprint) rises less than FLAT; `cliff`: the engine's own
            impassable cells (BlendTileData bit field 0; rise > CLIFF per cell where that cannot be read); `tiers`:
            land heights that each hold at least TIER_SHARE of the land (20-unit bins, neighbours merged)
  objects   ore nodes, tech buildings (oil derricks, hospitals ...), bridges, civilian structures, props, decals,
            per player; ore near the human player's start
  goals     MissionObjectives (main / bonus), how scripts drive them (SET_MISSION_OBJECTIVE_STATUS 0 hidden,
            1 active, 2 done, 3 failed; LINK_MISSION_OBJECTIVE_TO_OBJECT / _WAYPOINT puts the green marker on a
            target), the rewards given where a bonus objective is done
The picture: height bands, water, cliffs (dark), flat buildable land (light), ore (gold), tech (cyan), bridges
(white), civilian structures (grey), the human player's objects (green), enemies (red), objective markers (yellow).
"""
import argparse
import glob
import json
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import labpaths  # noqa: E402

sys.path.insert(0, labpaths.ROOT)
from ra3voice import big, csf  # noqa: E402
import mapscript  # noqa: E402
import mapterrain  # noqa: E402
import mapxml  # noqa: E402

STEAM = os.path.dirname(labpaths.GAME)
ARCHIVES = {'ra3': os.path.join(labpaths.GAME, 'Data', 'MapsCampaign.big'),
            'up': os.path.join(STEAM, 'Command and Conquer Red Alert 3 Uprising', 'Data', 'MapsCampaign.big')}
STRINGS = [os.path.join(labpaths.GAME, 'Data', 'English.big'),
           os.path.join(STEAM, 'Command and Conquer Red Alert 3 Uprising', 'Data', 'English.big')]
OUT = os.path.join(labpaths.WORK, 'mapstudy')
INDEX = os.path.join(labpaths.WORK, 'sagexml_gameobjects.json')
CELL = mapterrain.CELL
REAL = 0.04375          # world height per elevation step (newmap: water written as 200 stands at 285.7 / 16)
FOOT = 6                # cells: a building footprint for the flatness window
FLAT = 8.0              # world units of rise inside the footprint still counted as flat
CLIFF = 6.0             # world units of rise per 10-unit cell (31 degrees) counted as cliff
TIER_SHARE = 0.04
NEAR_START = 1200       # ore within this many world units of the player's start counts as "near"


# ---------------------------------------------------------------- reading
def retail_maps(parts=()):
    out = []
    for game, arc in ARCHIVES.items():
        if not os.path.exists(arc):
            continue
        for n, _, _ in big.read_index(arc):
            short = n.split('\\')[-1][:-4]
            if n.lower().endswith('.map') and (not parts or any(p in short for p in parts)):
                out.append((game, arc, n, short))
    return out


def players(m):
    """{name: property dict} from SidesList (the player dicts sit at no fixed offset: scanned for)."""
    node = next(x for _, x in m.walk() if x.name == 'SidesList')
    d, out = node.head, {}
    for p in range(len(d) - 6):
        try:
            pr = mapxml._props(m, d, p)
        except Exception:
            continue
        name = pr.get('playerName')
        if name and len(pr) > len(out.get(name, {})):
            out[name] = pr
    return out


def water_height(m):
    node = next((x for _, x in m.walk() if x.name == 'GlobalWaterSettings'), None)
    if node is None or len(node.head) < 8:
        return None
    on, h = struct.unpack_from('<If', node.head, 0)
    return h if on else None


_index = None


def kind(template, owner):
    """One category per placed object."""
    global _index
    if _index is None:
        _index = json.load(open(INDEX, encoding='utf-8')) if os.path.exists(INDEX) else {}
    t = template.lower()
    e = _index.get(t, {})
    base, path, sort = e.get('inheritFrom', ''), e.get('file', ''), e.get('EditorSorting', '')
    if template == '*Waypoints/Waypoint':
        return 'waypoint'
    if 'orenode' in t or 'BaseOreNode' in base:
        return 'ore'
    if 'bridge' in t or 'BaseBridge' in base:
        return 'bridge'
    if 'TechStructure' in base or 'techstructure' in t or 'oilderrick' in t or 'observationpost' in t:
        return 'tech'
    side = owner.split('/')[0]
    if side not in ('', 'PlyrCivilian', 'PlyrNeutral', 'PlyrCreeps'):
        return 'player'
    if t.startswith('amb_') or sort == 'AUDIO':
        return 'sound'
    if sort == 'STRUCTURE' or '/buildings/' in path.lower() or '/structures/' in path.lower():
        return 'civ_building'
    if any(w in t for w in ('sidewalk', 'line', 'trim', 'marking', 'road', 'track', 'crosswalk', 'parking',
                            'footpath', 'border', 'bricks', 'decal', 'segment', 'path', 'strip')):
        return 'decal'
    if sort in ('DESTRUCTIBLE_PROPS', 'OPTIMIZED_PROPS', 'MISC_NATURAL', 'MISC_MAN_MADE') or any(
            w in t for w in ('tree', 'bush', 'plant', 'grass', 'shrub', 'rock', 'fence', 'coral', 'prop')):
        return 'prop'
    return 'other'


_text = None


def text(label):
    global _text
    if _text is None:
        _text = {}
        for p in STRINGS:
            if os.path.exists(p):
                n = 'data\\gamestrings.csf'
                for e in csf.parse_full(big.read_files(p, [n])[n])[1]:
                    _text.setdefault(e[0].lower(), e[1])
    return _text.get(label.lower(), label)


# ---------------------------------------------------------------- measuring
def terrain(m):
    hm = mapterrain.HeightMap(m)
    b = hm.border
    w, h = hm.width - 2 * b, hm.height - 2 * b
    e = np.array(hm.elev, np.float32).reshape(hm.height, hm.width)[b:b + h, b:b + w] * REAL
    water = water_height(m)
    land = e > (water + 0.5) if water is not None else np.ones_like(e, bool)
    try:                                    # the engine's own impassable bits (BlendTileData field 0)
        tiles = mapterrain.Tiles(m, hm.width)
        bits = np.unpackbits(np.frombuffer(bytes(tiles.extra[:tiles.row_bytes * tiles.height]), np.uint8),
                             bitorder='little').reshape(tiles.height, 8 * tiles.row_bytes)[:, :hm.width]
        cliff = bits[b:b + h, b:b + w].astype(bool) & land
    except (AssertionError, ValueError, StopIteration):
        rise = np.zeros_like(e)
        rise[:, 1:] = np.maximum(rise[:, 1:], abs(np.diff(e, axis=1)))
        rise[1:, :] = np.maximum(rise[1:, :], abs(np.diff(e, axis=0)))
        cliff = rise > CLIFF
    # footprint relief: max - min over a FOOT x FOOT window (sliding, via stride tricks)
    from numpy.lib.stride_tricks import sliding_window_view
    win = sliding_window_view(e, (FOOT, FOOT))
    relief = np.full_like(e, np.inf)
    relief[:win.shape[0], :win.shape[1]] = win.max(axis=(2, 3)) - win.min(axis=(2, 3))
    flat = land & (relief < FLAT)
    heights = e[land]
    tiers = []
    if heights.size:
        lo = np.floor(heights.min() / 20) * 20
        hist, edges = np.histogram(heights, bins=np.arange(lo, heights.max() + 40, 20))
        share = hist / heights.size
        k = 0
        while k < len(share):
            if share[k] >= TIER_SHARE:
                j = k
                while j + 1 < len(share) and share[j + 1] >= TIER_SHARE:
                    j += 1
                tiers.append(dict(low=float(edges[k]), high=float(edges[j + 1]), share=float(share[k:j + 1].sum())))
                k = j + 1
            else:
                k += 1
    n = e.size
    return dict(size=[w * CELL, h * CELL], water=water, land=float(land.sum() / n),
                flat_of_land=float(flat.sum() / max(1, land.sum())), cliff=float((cliff & land).sum() / n),
                height=[float(heights.min()), float(heights.max())] if heights.size else None, tiers=tiers), \
        dict(e=e, land=land, cliff=cliff, flat=flat, relief=relief)


def objectives(m):
    try:
        objs = m.objectives()
    except StopIteration:
        return [], []
    goals = [dict(name=o['name'], bonus=bool(o['bonus']), title=text(o['title'])) for o in objs]
    links, rewards = [], {}
    for _, s in m.walk():
        if s.name != 'Script':
            continue
        acts = [m.content(x) for x in s.kids if x.name == 'ScriptAction']
        for name, args, _ in acts:
            vals = [a[1] for a in args]
            if name in ('LINK_MISSION_OBJECTIVE_TO_OBJECT', 'LINK_MISSION_OBJECTIVE_TO_WAYPOINT') and vals[2] == 1:
                links.append((vals[0], name.rsplit('_', 1)[1].lower(), vals[1]))
            if name == 'SET_MISSION_OBJECTIVE_STATUS' and vals[1] == 2:
                rewards.setdefault(vals[0], set()).update(
                    n for n, _, _ in acts if n not in ('SET_MISSION_OBJECTIVE_STATUS', 'ENABLE_SCRIPT', 'DISABLE_SCRIPT',
                                                       'SET_FLAG', 'SET_MILLISECOND_TIMER'))
    for g in goals:
        g['markers'] = sum(1 for o, _, _ in links if o == g['name'])
        g['on_done'] = sorted(rewards.get(g['name'], ()))
    return goals, links


def study(m, title):
    t, grids = terrain(m)
    objs = mapxml.objects(m)
    sides = players(m)
    human = next((n for n, p in sides.items() if p.get('playerIsHuman')), 'Player_1')
    enemies = set(sides.get(human, {}).get('playerEnemies', '').split())
    friends = set(sides.get(human, {}).get('playerAllies', '').split()) | {human}
    counts, where = {}, {}
    for o in objs:
        owner = str(o['props'].get('originalOwner', ''))
        k = kind(o['template'], owner)
        if k == 'player':
            k = 'mine' if owner.split('/')[0] in friends else 'enemy' if owner.split('/')[0] in enemies else 'other_side'
        if owner.split('/')[0] == human:
            where.setdefault('human', []).append((o['x'], o['y'], o['template'], ''))
        counts[k] = counts.get(k, 0) + 1
        where.setdefault(k, []).append((o['x'], o['y'], o['template'], str(o['props'].get('objectName', ''))))
    # how uneven the ground under the retail bases' own structures is (what the designers built on)
    rel, under = grids['relief'], []
    for k in ('mine', 'enemy'):
        for x, y, tpl, _ in where.get(k, []):
            if _index.get(tpl.lower(), {}).get('EditorSorting') == 'STRUCTURE':
                i, j = int(x / CELL) - FOOT // 2, int(y / CELL) - FOOT // 2
                if 0 <= j < rel.shape[0] and 0 <= i < rel.shape[1] and np.isfinite(rel[j, i]):
                    under.append(float(rel[j, i]))
    start = np.median(np.array([(x, y) for x, y, _, _ in where['human']]), axis=0) if where.get('human') else None
    ores = where.get('ore', [])
    near = sum(1 for x, y, _, _ in ores if start is not None and np.hypot(x - start[0], y - start[1]) < NEAR_START)
    km2 = t['size'][0] * t['size'][1] * t['land'] / 1e6
    goals, links = objectives(m)
    named = {n: (x, y) for k in where for x, y, _, n in where[k] if n}
    wps = {str(o['props'].get('waypointName', '')): (o['x'], o['y']) for o in objs if o['template'] == '*Waypoints/Waypoint'}
    marks = [(o, named.get(target) or wps.get(target)) for o, kind_, target in links]
    bridges = sorted({tpl for _, _, tpl, _ in where.get('bridge', [])})
    out = dict(map=title, terrain=t, counts=counts, per_km2={k: round(v / km2, 1) for k, v in counts.items()},
               ore_near_start=near, bridges=bridges,
               relief_under_bases=[round(float(q), 1) for q in np.percentile(under, [50, 90, 100])] if under else None, human=human, goals=goals,
               tech=sorted({tpl for _, _, tpl, _ in where.get('tech', [])}),
               civ_buildings_named=sum(1 for *_, n in where.get('civ_building', []) if n))
    return out, grids, where, [p for _, p in marks if p]


# ---------------------------------------------------------------- picture
def picture(path, info, grids, where, marks, px=2):
    e, land, cliff, flat = grids['e'], grids['land'], grids['cliff'], grids['flat']
    h, w = e.shape
    lo, hi = (info['terrain']['height'] or [0, 1])
    t = np.clip((e - lo) / max(1.0, hi - lo), 0, 1)
    band = np.floor(t * 6) / 6                                    # six height bands, low green -> high brown
    low, high = np.array([95, 120, 70], np.float32), np.array([170, 140, 100], np.float32)
    img = low + (high - low) * band[..., None]
    img = np.where(flat[..., None], img * 1.15 + 12, img * 0.85)
    img = np.where(cliff[..., None], np.array([60, 35, 30], np.float32), img)
    img = np.where(land[..., None], img, np.array([35, 70, 120], np.float32))
    img = np.clip(img[::-1], 0, 255).astype(np.uint8)
    pic = Image.fromarray(img).resize((w * px, h * px), Image.NEAREST)
    d = ImageDraw.Draw(pic, 'RGBA')
    s = px / CELL

    def at(x, y):
        return x * s, (h * CELL - y) * s
    style = {'prop': ((25, 60, 25, 150), 0.5), 'civ_building': ((150, 150, 150, 200), 1.2),
             'tech': ((60, 230, 230, 255), 3), 'ore': ((255, 200, 40, 255), 3), 'bridge': ((255, 255, 255, 255), 3),
             'enemy': ((230, 50, 50, 200), 1.4), 'mine': ((60, 230, 60, 230), 1.6)}
    for k in ('prop', 'civ_building', 'enemy', 'mine', 'tech', 'bridge', 'ore'):
        col, r = style[k]
        for x, y, _, _ in where.get(k, []):
            X, Y = at(x, y)
            d.ellipse([X - r * px, Y - r * px, X + r * px, Y + r * px], fill=col)
    for x, y in marks:
        X, Y = at(x, y)
        d.polygon([(X, Y - 5 * px), (X + 4 * px, Y + 3 * px), (X - 4 * px, Y + 3 * px)],
                  outline=(255, 255, 0, 255), width=2)
    d.text((6, 6), info['map'], fill=(255, 255, 255, 255))
    pic.save(path)


# ---------------------------------------------------------------- report
def row(i):
    t = i['terrain']
    c = i['counts']
    tiers = '/'.join(f"{x['low']:.0f}-{x['high']:.0f}" for x in t['tiers'])
    main = sum(1 for g in i['goals'] if not g['bonus'])
    bonus = sum(1 for g in i['goals'] if g['bonus'])
    marked = sum(1 for g in i['goals'] if g['markers'])
    return (f"| {i['map']} | {t['size'][0]:.0f}x{t['size'][1]:.0f} | {t['land']:.0%} | {t['flat_of_land']:.0%} | "
            f"{t['cliff']:.1%} | {len(t['tiers'])} ({tiers}) | {c.get('ore', 0)} ({i['ore_near_start']}) | "
            f"{c.get('tech', 0)} | {c.get('bridge', 0)} | {c.get('civ_building', 0)} | {c.get('prop', 0)} | "
            f"{main}+{bonus} ({marked} marked) |")


COMMANDO = ('y01', 'y02', 'y03', 's01_romania')       # no base building: left out of the ranges
MEASURES = [('land', lambda i: i['terrain']['land'], '{:.0%}'),
            ('flat of land', lambda i: i['terrain']['flat_of_land'], '{:.0%}'),
            ('cliff', lambda i: i['terrain']['cliff'], '{:.1%}'),
            ('height tiers', lambda i: len(i['terrain']['tiers']), '{:.0f}'),
            ('ore nodes', lambda i: i['counts'].get('ore', 0), '{:.0f}'),
            ('tech buildings', lambda i: i['counts'].get('tech', 0), '{:.0f}'),
            ('bridges (objects, 2 each)', lambda i: i['counts'].get('bridge', 0), '{:.0f}'),
            ('civilian buildings', lambda i: i['counts'].get('civ_building', 0), '{:.0f}'),
            ('props (trees, rocks, fences ...)', lambda i: i['counts'].get('prop', 0), '{:.0f}'),
            ('objectives', lambda i: len(i['goals']), '{:.0f}'),
            ('bonus objectives', lambda i: sum(g['bonus'] for g in i['goals']), '{:.0f}')]


def compare(info):
    """Each measure of `info` against the retail maps' range (min / median / max, commando maps left out)."""
    rows = [json.load(open(p, encoding='utf-8')) for p in glob.glob(os.path.join(OUT, 'camp_*.json'))]
    rows = [r for r in rows if not any(c in r['map'] for c in COMMANDO)]
    if not rows:
        return ['(no retail maps studied yet: run mapstudy.py with no arguments)']
    out = []
    for label, f, fmt in MEASURES:
        v = sorted(f(r) for r in rows)
        mine, lo, hi, mid = f(info), v[0], v[-1], v[len(v) // 2]
        flag = 'ok' if lo <= mine <= hi else 'OUTSIDE'
        out.append(f'{label}: {fmt.format(mine)} (retail {fmt.format(lo)}..{fmt.format(hi)}, median '
                   f'{fmt.format(mid)}) {flag}')
    return out


HEAD = ('| map | size | land | flat of land | cliff | tiers | ore (near start) | tech | bridge | civ bldg | props '
        '| goals main+bonus |\n|---|---|---|---|---|---|---|---|---|---|---|---|')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('parts', nargs='*')
    ap.add_argument('--ours', nargs='*')
    ap.add_argument('--table', action='store_true')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.table:
        print(HEAD)
        for p in sorted(glob.glob(os.path.join(OUT, '*.json'))):
            print(row(json.load(open(p, encoding='utf-8'))))
        return
    jobs = []
    if a.ours:
        import maprender
        jobs = [(os.path.splitext(os.path.basename(name))[0], lambda name=name: maprender.load(name))
                for name in a.ours]
    else:
        jobs = [(short, lambda arc=arc, n=n: mapscript.MapFile(big.read_files(arc, [n])[n]))
                for _, arc, n, short in retail_maps(a.parts)]
    for name, load in jobs:
        info, grids, where, marks = study(load(), name)
        with open(os.path.join(OUT, name + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(info, fh, ensure_ascii=False, indent=1)
        picture(os.path.join(OUT, name + '.png'), info, grids, where, marks)
        print(row(info), flush=True)
        if a.ours:
            print('\n'.join(compare(info)))
            print('PICTURE ' + os.path.join(OUT, name + '.png'))


if __name__ == '__main__':
    main()
