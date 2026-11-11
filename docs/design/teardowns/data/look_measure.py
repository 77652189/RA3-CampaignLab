"""How a map looks (docs/story/map-diagnosis-a4.md): the same measures on a built mod of ours and the retail maps.
  python -I -X utf8 docs/design/teardowns/data/look_measure.py --ours CampA4      (A4, then every retail map)
  python -I -X utf8 docs/design/teardowns/data/look_measure.py tokyo osaka         (only those retail maps)
Per map: civilian buildings / props / decals / ambient sounds per km2 of land; man-made things' angles (share on
0/90 degrees, share on 45); template counts; civilian buildings' nearest-neighbour spacing (median, CV, share in
an exactly repeated spacing); vignette props (a man-made prop with 2+ other man-made templates within 120);
ground textures used inside the playable area, top texture's share, blended cells; machine-flat land; steep
terrain edges' direction (share within 10 degrees of the axes / of 45); man-made template count (no trees or
rocks), vehicles and war damage per km2 (by name); rhythm: of the 250 x 250 cells that are mostly land, the share
with nothing and the share at least twice the mean. Classes come from mapstudy.kind (by
name and SageXML sorting: a map whose buildings belong to a player, e.g. Kremlin, reads 0 civilian buildings).
"""
import importlib.util, json, math, os, re, sys
from collections import Counter
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
# layout_measure (next to this file) already puts experimental/campaign on the path; load it by file so this
# script adds no sys.path edit of its own (G4 ratchet in tests/test_architecture.py)
_spec = importlib.util.spec_from_file_location('layout_measure', os.path.join(os.path.dirname(__file__), 'layout_measure.py'))
_spec.loader.exec_module(importlib.util.module_from_spec(_spec))
import mapstudy as ms  # noqa
import mapterrain  # noqa
import mapxml  # noqa
from ra3voice import big  # noqa

VEG = ('tree', 'bush', 'plant', 'grass', 'shrub', 'flower', 'palm', 'pine', 'weed', 'reed', 'fern', 'bamboo')
WAR = re.compile(r'wreck|rubble|crater|debris|barricade|sandbag|burn|destroy|damag|tanktrap|hedgehog|ruin|broken|husk'
                 r'|scorch|bombed|dead', re.I)
VEHICLE = re.compile(r'car\d|_car|truck|bus\b|bus_|van\b|van_|taxi|tram|train|forklift|boat|trailer', re.I)


def measure(m, name):
    info, grids, where, _ = ms.study(m, name)
    hm = mapterrain.HeightMap(m)
    b = hm.border
    w, h = hm.width - 2 * b, hm.height - 2 * b
    e = np.array(hm.elev, np.float32).reshape(hm.height, hm.width)[b:b + h, b:b + w] * ms.REAL
    water = info['terrain']['water']
    land = e > water + 2
    out = {'map': name, 'land_km2': round(float(land.sum()) * 1e-4, 2)}
    km2 = max(out['land_km2'], 0.1)
    objs = mapxml.objects(m)
    rows = []
    for o in objs:
        owner = str(o['props'].get('originalOwner', ''))
        k = ms.kind(o['template'], owner)
        rows.append((k, o['template'], o['x'], o['y'], o['angle']))
    c = Counter(k for k, *_ in rows)
    for k in ('civ_building', 'prop', 'decal', 'sound'):
        out[k + '_per_km2'] = round(c.get(k, 0) / km2, 1)
    # angles of man-made placed things (civ buildings + non-vegetation props)
    def manmade(k, t):
        return k == 'civ_building' or (k == 'prop' and not any(v in t.lower() for v in VEG))
    ang = [r[4] for r in rows if manmade(r[0], r[1])]
    if ang:
        deg = np.degrees(np.array(ang)) % 90.0
        d0 = np.minimum(deg, 90 - deg)
        out['manmade_n'] = len(ang)
        out['angle_axis_share'] = round(float((d0 < 2).mean()), 2)          # 0/90/180/270
        out['angle_diag_share'] = round(float((abs(deg - 45) < 2).mean()), 2)
        out['angle_bins_used'] = int(len(set((np.degrees(np.array(ang)) % 360 // 10).astype(int))))  # of 36
    # template variety
    civ = [r for r in rows if r[0] == 'civ_building' and 'wall' not in r[1].lower()]
    out['wall_segments'] = sum(1 for r in rows if r[0] == 'civ_building' and 'wall' in r[1].lower())
    props = [r for r in rows if r[0] == 'prop']
    for lab, rs in (('civ', civ), ('prop', props)):
        cc = Counter(r[1] for r in rs)
        out[lab + '_templates'] = len(cc)
        out[lab + '_top1_share'] = round(cc.most_common(1)[0][1] / len(rs), 2) if rs else None
    # spacing regularity of civ buildings: NN distance CV
    if len(civ) > 5:
        p = np.array([(r[2], r[3]) for r in civ])
        dd = np.hypot(p[:, None, 0] - p[None, :, 0], p[:, None, 1] - p[None, :, 1])
        np.fill_diagonal(dd, 1e9)
        nn = dd.min(1)
        out['civ_nn_median'] = round(float(np.median(nn)))
        out['civ_nn_cv'] = round(float(nn.std() / nn.mean()), 2)
        # how many buildings share an exactly repeated NN distance (rounded to 2 units): grid signature
        rc = Counter(np.round(nn / 2).astype(int))
        out['civ_nn_repeat_share'] = round(sum(v for v in rc.values() if v >= 4) / len(nn), 2)
    # vignettes: man-made non-building props with >=2 other man-made props of a different template within 120
    mm = [r for r in props if manmade(r[0], r[1])]
    if mm:
        p = np.array([(r[2], r[3]) for r in mm]); t = [r[1] for r in mm]
        dd = np.hypot(p[:, None, 0] - p[None, :, 0], p[:, None, 1] - p[None, :, 1])
        vig = 0
        for i in range(len(mm)):
            near = np.where((dd[i] < 120) & (dd[i] > 0))[0]
            if len({t[j] for j in near if t[j] != t[i]}) >= 2:
                vig += 1
        out['vignette_props_per_km2'] = round(vig / km2, 1)
    # what kind of place: man-made template count (no trees / rocks), vehicles, war damage

    things = [r for r in rows if r[0] in ('civ_building', 'prop', 'other')]
    out['manmade_templates'] = len({r[1] for r in things if not any(v in r[1].lower() for v in VEG + ('rock',))})
    out['vehicle_per_km2'] = round(sum(1 for r in things if VEHICLE.search(r[1])) / km2, 2)
    out['war_per_km2'] = round(sum(1 for r in things if WAR.search(r[1])) / km2, 2)
    # rhythm: 250 x 250 cells that are mostly land, how many are empty / at least twice the mean
    C = 25
    cnt = np.zeros((h // C, w // C))
    for r in things:
        i, j = int(r[2] / 10) // C, int(r[3] / 10) // C
        if 0 <= j < cnt.shape[0] and 0 <= i < cnt.shape[1]:
            cnt[j, i] += 1
    lc = np.array([[land[j * C:(j + 1) * C, i * C:(i + 1) * C].mean() > 0.8 for i in range(cnt.shape[1])]
                   for j in range(cnt.shape[0])])
    v = cnt[lc]
    if v.size and v.mean():
        out['empty_cells'] = round(float((v == 0).mean()), 2)
        out['dense_cells'] = round(float((v >= 2 * v.mean()).mean()), 2)
    # ground textures inside the playable area
    try:
        tiles = mapterrain.Tiles(m, hm.width)
        tile = np.array(tiles.arrays[0], np.int64).reshape(hm.height, hm.width)[b:b + h, b:b + w]
        blend = np.array(tiles.arrays[1], np.int64).reshape(hm.height, hm.width)[b:b + h, b:b + w]
        starts = sorted((s, cnt, nm) for nm, (s, cnt, _) in tiles.textures.items())
        cell = tile // 4
        tex = np.full(cell.shape, -1)
        for k, (s, cnt, nm) in enumerate(starts):
            tex[(cell >= s) & (cell < s + cnt)] = k
        tl = tex[land]
        cc = Counter(tl.tolist())
        out['textures_used'] = sum(1 for v in cc.values() if v > 0.005 * tl.size)
        out['texture_top1_share'] = round(cc.most_common(1)[0][1] / tl.size, 2)
        out['blended_share'] = round(float((blend[land] > 0).mean()), 2)
    except Exception as ex:  # noqa
        out['textures_err'] = str(ex)[:80]
    # perfectly flat land (3x3 range < 0.5 world units): machine-flat ground
    r = np.zeros_like(e)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            r = np.maximum(r, abs(np.roll(np.roll(e, dy, 0), dx, 1) - e))
    out['machine_flat_share'] = round(float((r[land] < 0.5).mean()), 2)
    # steep edges (cliff faces, shores): which way they run
    from scipy import ndimage
    gy, gx = np.gradient(ndimage.gaussian_filter(e, 1.5))
    sel = np.hypot(gx, gy) > 3.0
    a = np.degrees(np.arctan2(gy[sel], gx[sel])) % 90
    out['edge_axis_share'] = round(float((np.minimum(a, 90 - a) < 10).mean()), 2)
    out['edge_diag_share'] = round(float((abs(a - 45) < 10).mean()), 2)
    # occlusion from the player's start: share of land within 1500 hidden by buildings (r 40) or higher ground
    hum = [(x, y) for x, y, *_ in where.get('human', [])]
    if hum and os.environ.get('OCCLUSION'):
        sx, sy = np.median(np.array(hum), axis=0)
        si, sj = int(sx / 10), int(sy / 10)
        se = e[min(max(sj, 0), h - 1), min(max(si, 0), w - 1)]
        occ = np.zeros_like(land)
        for x, y in [(r_[2], r_[3]) for r_ in civ]:
            i, j = int(x / 10), int(y / 10)
            occ[max(j - 4, 0):j + 4, max(i - 4, 0):i + 4] = True
        tot = hid = 0
        rng = np.random.default_rng(1)
        for _ in range(3000):
            a = rng.uniform(0, 2 * math.pi); d = 1500 * math.sqrt(rng.uniform(0.01, 1))
            tx, ty = sx + d * math.cos(a), sy + d * math.sin(a)
            ti, tj = int(tx / 10), int(ty / 10)
            if not (0 <= ti < w and 0 <= tj < h) or not land[tj, ti]:
                continue
            tot += 1
            te = e[tj, ti]
            n = int(d / 20)
            for s in range(1, n):
                f = s / n
                ci, cj = int((sx + f * (tx - sx)) / 10), int((sy + f * (ty - sy)) / 10)
                eye = se + 15 + f * (te - se)
                if occ[cj, ci] or e[cj, ci] > eye + 15:
                    hid += 1
                    break
        out['hidden_from_start_1500'] = round(hid / max(tot, 1), 2)
    return out


def main():
    args = sys.argv[1:]
    ours = []
    if '--ours' in args:
        i = args.index('--ours'); ours = [args[i + 1]]; args = args[:i] + args[i + 2:]
    res = []
    if ours:
        import maprender
        for n in ours:
            res.append(measure(maprender.load(n), n)); print(res[-1], flush=True)
    for _, arc, n, short in ms.retail_maps(args):
        try:
            import mapscript
            res.append(measure(mapscript.MapFile(big.read_files(arc, [n])[n]), short)); print(res[-1], flush=True)
        except Exception as ex:  # noqa
            print('ERR', short, ex, flush=True)
    os.makedirs(os.path.join((os.environ.get('CNV_WORK') or os.path.join(ROOT, 'work')), 'mapdiag'), exist_ok=True)
    path = os.path.join((os.environ.get('CNV_WORK') or os.path.join(ROOT, 'work')), 'mapdiag', 'measures%s.json' % ('_' + '_'.join(ours + args) if (ours or args) else ''))
    json.dump(res, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
