"""Ice models kitbashed from retail's Iceland glaciers (IL_GLACIER01 .. 09A, World Builder's stream: faceted ice,
white-cyan, the look the game already has), for the 冰幕工兵's wall and core (experimental/cnv/units/icewall.py):

  python -I -X utf8 experimental/units/ice_kit.py [<model> ...]      (default: all of KITS)

Each kit is a few glacier meshes turned, scaled and moved (retail UVs kept: the texture tiles across), then the whole
fitted to the footprint and height asked. Written to the SDK's Art folder (w3x.write_model) as one rigid mesh on
ROOTTRANSFORM with the shared textures CNIce / CNIce_NRM / CNIce_SPM (retail IL_Glacier01's diffuse; flat normal map
-- the glaciers have no tangents, their shader is not normal-mapped; SPM: a little specular, no glow, no house
colour). A preview sheet (retail_sheet.py's renders) goes to work/units/ice/<model>_grid.png. Also the engineer's
own texture, CNIceEngineer (engineer_texture), and the festival's snow bank CNSnowBank (bank: made as a height
field, retail has no snow drift; texture CNSnow).
"""
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
sys.path.insert(0, HERE)
import labpaths                                 # noqa: E402
import retail_mesh                              # noqa: E402
import retail_sheet                             # noqa: E402
import retail_texture                           # noqa: E402
import w3x                                      # noqa: E402
from PIL import Image                           # noqa: E402

TEXTURE = 'CNIce'
DARK = (0.52, 0.62, 0.70)                       # the glacier diffuse scaled per channel (r, g, b)
OUT = os.path.join(labpaths.WORK, 'units', 'ice')
# model: (footprint side, height, [(glacier, turn degrees, (x, y) in the footprint's -1..1, relative size)])
KITS = {
    # the wall: a 160 square block over a plaza gate's ramp (devices/ice_plazas.py WALL_SIDE); a ridge of ice with
    # a tall middle, lower shards at the corners so it reads as frozen up from the ground, not a mountain
    'CNIceWall': (160, 55, [('02', 0, (0.0, 0.0), 1.0), ('05', 40, (-0.55, 0.45), 0.75), ('06', 200, (0.6, -0.4), 0.7),
                            ('06A', 110, (0.55, 0.55), 0.65), ('03', 70, (-0.5, -0.5), 0.6)]),
    # the bar wall (icewall.wall shape 'bar', 200 x 24: ice_block, J4's gate ice): a row of shards along it, a little
    # thicker than its 24 so it does not read as a sheet; (length, depth) instead of a square's side
    'CNIceBar': ((200, 34), 45, [('05', 30, (-0.8, 0.1), 0.24), ('06', 110, (-0.42, -0.2), 0.26), ('02', 0, (0.0, 0.0), 0.32),
                                 ('06A', 200, (0.42, 0.2), 0.26), ('03', 300, (0.8, -0.1), 0.24)]),
    # the core the engineer stands building for 5 s (icewall.seed: a 40 square)
    'CNIceSeed': (40, 30, [('06A', 0, (0.0, 0.0), 1.0), ('05', 150, (0.35, -0.3), 0.55)]),
    # what a shot-down wall leaves (ice_look.rubble): low broken chunks over its square, sinking away
    'CNIceRubble': (160, 16, [('05', 10, (-0.6, -0.55), 0.35), ('06', 80, (0.1, -0.6), 0.3), ('03', 140, (0.6, -0.4), 0.3),
                              ('06A', 200, (-0.35, 0.05), 0.4), ('02', 30, (0.3, 0.15), 0.45), ('05', 260, (-0.6, 0.6), 0.3),
                              ('06', 310, (0.15, 0.65), 0.35), ('03', 20, (0.65, 0.6), 0.3)]),
    # what a broken sculpture leaves (40 square, units/festival.py)
    'CNIceRubbleS': (40, 8, [('05', 10, (-0.5, -0.4), 0.5), ('06', 130, (0.45, -0.2), 0.45), ('03', 250, (0.0, 0.5), 0.5)]),
}
# Tripo props (tripo_unit.py prop_main: work/units/<unit>/game/<model>.png, _nrm.png, parts.json) in the same ice
PROPS = {'CNIceSculpt': 'icesculpture'}
# snow banks, made, not kitbashed (retail has no snow drift; its snow is on roofs and props): model -> (length,
# width at the foot, height). The festival's plaza walls (units/festival.py bank: 220 long, 24 thick): a berm a
# little wider at its foot than the 24 it blocks, so it reads as shovelled snow, not a wall
BANKS = {'CNSnowBank': (220, 36, 20)}
SNOW = 'CNSnow'
# packed snow, darker than white as the glacier had to be (DARK); (176, 188, 202) read blown-out white on the bench
SNOW_RGB = (138, 148, 164)


def _piece(by, glacier, turn, at, size, unit):
    """One glacier turned by `turn` degrees, scaled so its larger side is `size` x unit, centred at `at`."""
    m = retail_mesh.load(by, 'IL_GLACIER' + glacier)
    v = m['vertices']
    lo = [min(p[i] for p in v) for i in range(3)]
    hi = [max(p[i] for p in v) for i in range(3)]
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    s = size * unit / max(hi[0] - lo[0], hi[1] - lo[1])
    c, sn = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    verts = [((x - cx) * s * c - (y - cy) * s * sn + at[0], (x - cx) * s * sn + (y - cy) * s * c + at[1], z * s)
             for x, y, z in v]
    normals = [(nx * c - ny * sn, nx * sn + ny * c, nz) for nx, ny, nz in m['normals']]
    uvs = [(u, 1 - t) for u, t in m['uvs']]            # compiled meshes are v-down; ours as Blender's (v up)
    return verts, normals, uvs, m['triangles']


def build(by, model):
    side, height, recipe = KITS[model]
    sx, sy = side if isinstance(side, tuple) else (side, side)
    verts, normals, uvs, tris = [], [], [], []
    for glacier, turn, (x, y), size in recipe:
        v, n, u, t = _piece(by, glacier, turn, (x * sx / 2, y * sy / 2), size, max(sx, sy))
        tris += [tuple(i + len(verts) for i in tri) for tri in t]
        verts, normals, uvs = verts + v, normals + n, uvs + u
    # fit: the footprint within the side (a little inside, so it does not hang over its building's edges), the top
    # at `height`; a non-uniform scale, so the normals by the inverse
    lo = [min(p[i] for p in verts) for i in range(3)]
    hi = [max(p[i] for p in verts) for i in range(3)]
    k = [0.96 * sx / (hi[0] - lo[0]), 0.96 * sy / (hi[1] - lo[1]), height / hi[2]]
    mid = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, 0.0]
    verts = [tuple((p[i] - mid[i]) * k[i] for i in range(3)) for p in verts]
    normals = [tuple(n[i] / k[i] for i in range(3)) for n in normals]
    normals = [tuple(c / (math.sqrt(sum(x * x for x in n)) or 1) for c in n) for n in normals]
    w3x.write_model(model, w3x.rig_model(model, [], [('ICE', 0, (verts, normals, uvs, tris))],
                                         (TEXTURE, TEXTURE + '_NRM', TEXTURE + '_SPM')))
    os.makedirs(OUT, exist_ok=True)
    obj = os.path.join(OUT, model + '.obj')
    retail_mesh.write_obj(dict(vertices=verts, uvs=[(u, 1 - t) for u, t in uvs], triangles=tris, layout='ice_kit'), obj)
    return obj, len(tris)


def textures():
    retail_texture.main(['IL_Glacier01'])
    im = Image.open(os.path.join(retail_texture.OUT, 'IL_Glacier01.png')).convert('RGB')
    px = im.load()
    w, h = im.size
    # retail's glacier diffuse as it is read near white in game (bench 2026-10-26, ObjectsAllied: the facets washed
    # out): darker and a little cyan, so the sun picks the facets apart
    def diffuse(x, y):
        r, g, b = px[x, y]
        return int(r * DARK[0]), int(g * DARK[1]), int(b * DARK[2]), 255
    w3x.write_texture(TEXTURE, w, h, diffuse)
    w3x.write_texture(TEXTURE + '_NRM', 16, 16, lambda x, y: (128, 128, 255, 255))
    # a little specular (retail Allied bodies ~21): wet ice shines a little, no glow, no team colour
    w3x.write_texture(TEXTURE + '_SPM', w, h, lambda x, y: (sum(px[x, y]) // 30, 0, 0, 255))
    return os.path.join(retail_texture.OUT, 'IL_Glacier01.png')


def bank(model):
    """A snow bank as a height field: a grid along its length and across, the cross-section a rounded berm, both ends
    rounded off and pinched, lumps along the top (fixed sines, the same every build) and a wobbling foot, the foot
    sunk a little so uneven ground does not show under it. Normals from the faces; the texture tiles every 64."""
    length, width, height = BANKS[model]
    ns, nt = 88, 14
    verts, uvs = [], []
    for i in range(ns + 1):
        s = -1 + 2 * i / ns
        end = math.sqrt(max(0.0, 1 - s ** 8))                       # 1 along it, 0 at its two ends
        # the foot and the top each a few waves of unrelated lengths (bench 2026-10-27: one foot wave and the top's
        # in step read as a row of even bulges, a white caterpillar; before that, 3..13 waves at up to 0.18 read as a
        # jagged ice ridge)
        foot = (0.25 + 0.75 * end) * (1 + 0.05 * math.sin(2 * math.pi * 1.3 * s + 0.7)
                                      + 0.04 * math.sin(2 * math.pi * 3.1 * s + 2.3))
        for j in range(nt + 1):
            t = -1 + 2 * j / nt
            lump = (1 + 0.10 * math.sin(2 * math.pi * 0.9 * s + 1.3)
                    + 0.05 * math.sin(2 * math.pi * 2.3 * s + 0.4 + 1.2 * t)
                    + 0.03 * math.sin(2 * math.pi * 4.7 * s + 2.1 - 0.8 * t))
            z = height * (1 - t * t) ** 0.7 * end * lump / 1.10 - 1.5
            x, y = s * length / 2, t * width / 2 * foot
            verts.append((x, y, z))
            uvs.append((x / 64, y / 64))
    row = nt + 1
    tris = []
    for i in range(ns):
        for j in range(nt):
            a, b, c, d = i * row + j, (i + 1) * row + j, (i + 1) * row + j + 1, i * row + j + 1
            tris += [(a, b, c), (a, c, d)]
    acc = [[0.0, 0.0, 0.0] for _ in verts]
    for tri in tris:
        p, q, r = (verts[k] for k in tri)
        u = [q[k] - p[k] for k in range(3)]
        v = [r[k] - p[k] for k in range(3)]
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        for k in tri:
            acc[k] = [acc[k][m] + n[m] for m in range(3)]
    normals = [tuple(c / (math.sqrt(sum(x * x for x in n)) or 1) for c in n) for n in acc]
    if any(n[2] < 0 for n in normals):
        raise SystemExit(f'{model}: a face points down (winding)')
    w3x.write_model(model, w3x.rig_model(model, [], [('SNOW', 0, (verts, normals, uvs, tris))],
                                         (SNOW, SNOW + '_NRM', SNOW + '_SPM')))
    os.makedirs(OUT, exist_ok=True)
    obj = os.path.join(OUT, model + '.obj')
    retail_mesh.write_obj(dict(vertices=verts, uvs=uvs, triangles=tris, layout='ice_kit'), obj)
    return obj, len(tris)


def snow_texture():
    """CNSnow: packed snow, tiling (whole periods of sines over its 128 square), soft drifts and a fine grain, a
    little bluer where darker; a glint of specular, no glow, no house colour. Also its PNG for the preview."""
    size = 128

    def value(x, y):
        a, b = 2 * math.pi * x / size, 2 * math.pi * y / size
        drift = 0.5 * math.sin(a * 2 + b + 0.3) + 0.3 * math.sin(a * 3 - b * 2 + 1.1) + 0.2 * math.sin(b * 5 + a + 2.0)
        grain = ((x * 73856093) ^ (y * 19349663)) % 1000 / 1000 - 0.5
        return 0.12 * drift + 0.08 * grain           # 0.06 / 0.05 vanished in the sun

    def diffuse(x, y):
        k = 1 + value(x, y)
        r, g, b = SNOW_RGB
        return min(255, int(r * k * (1 - 0.3 * max(0.0, 1 - k)))), min(255, int(g * k)), min(255, int(b * k)), 255
    w3x.write_texture(SNOW, size, size, diffuse)
    w3x.write_texture(SNOW + '_NRM', 16, 16, lambda x, y: (128, 128, 255, 255))
    w3x.write_texture(SNOW + '_SPM', size, size, lambda x, y: (18, 0, 0, 255))
    out = os.path.join(OUT, SNOW + '.png')
    os.makedirs(OUT, exist_ok=True)
    Image.frombytes('RGBA', (size, size), bytes(c for y in range(size) for x in range(size) for c in diffuse(x, y))
                    ).save(out)
    return out


def missing(model):
    """The files prop() reads that are not there: the props are rebuilt only from tripo_unit.py's bake of a Tripo
    download under work/ (gitignored), not from retail like the kits."""
    src = os.path.join(labpaths.WORK, 'units', PROPS[model], 'game')
    return [p for p in (os.path.join(src, f) for f in (model + '.png', model + '_nrm.png', 'parts.json'))
            if not os.path.exists(p)]


def prop(model):
    """A Tripo prop baked by tripo_unit.py written as a W3X in the kits' ice: its bake scaled per channel so its
    median colour is CNIce's (a de-lit Tripo bake is near white, as the glacier was), little specular, no glow, no
    house colour; its baked normal map kept (to_w3x.convert, one part on BODY)."""
    import numpy as np
    import to_w3x
    src = os.path.join(labpaths.WORK, 'units', PROPS[model], 'game')
    bake = np.asarray(Image.open(os.path.join(src, model + '.png')).convert('RGB'), float)
    used = bake.max(axis=2) > 10
    ice = np.asarray(Image.open(os.path.join(retail_texture.OUT, 'IL_Glacier01.png')).convert('RGB'), float) * DARK
    k = np.median(ice.reshape(-1, 3), axis=0) / np.median(bake[used], axis=0)
    out = np.where(used[..., None], np.clip(bake * k, 0, 255), bake).astype(np.uint8)
    Image.fromarray(out).save(os.path.join(src, model + 'Ice.png'))
    Image.new('L', out.shape[1::-1], 0).save(os.path.join(src, model + 'Ice_mask.png'))
    Image.open(os.path.join(src, model + '_nrm.png')).save(os.path.join(src, model + 'Ice_nrm.png'))
    n = to_w3x.convert(src, model, [('BODY', None, (0.0, 0.0, 0.0))], {'PROP': 'BODY'}, src_name=model + 'Ice',
                       level=None, grade=False, spec=0.12)
    print(model, n, 'triangles; colour x', k.round(2))
    return n


ENGINEER = 'CNIceEngineer'
SUIT = (0, 52, 72, 92)                          # AUEngineer (128 square): the dark green shirt and dark sleeves
CASE = (0, 92, 48, 128)                         # the yellow tool case


def engineer_texture():
    """The 冰幕工兵's look on the retail engineer (a texture swap, no new model: ice_look.dress_engineer): his dark
    work clothes a pale blue-grey arctic suit, the yellow tool case an ice-cyan cryo case; face, apron and helmet as
    they are (the alpha -- the house-colour mask, apron and helmet -- kept)."""
    retail_texture.main(['AUEngineer'])
    im = Image.open(os.path.join(retail_texture.OUT, 'AUEngineer.png')).convert('RGBA')
    px = im.load()
    w, h = im.size

    def inside(box, x, y):
        return box[0] <= x < box[2] and box[1] <= y < box[3]

    def pixel(x, y):
        r, g, b, a = px[x, y]
        lum = 0.3 * r + 0.59 * g + 0.11 * b
        if a == 0 and inside(SUIT, x, y) and not r > g + 25:            # not the skin of his hands
            base = min(255, 150 + 0.9 * lum)                             # the folds kept as shading
            return int(base * 0.82), int(base * 0.9), int(base), a
        if inside(CASE, x, y) and r > 90 and g > 70 and b < 0.6 * min(r, g):
            return int(lum * 0.45), min(255, int(lum * 1.0)), min(255, int(lum * 1.15)), a
        return r, g, b, a
    w3x.write_texture(ENGINEER, w, h, pixel)
    out = os.path.join(OUT, ENGINEER + '.png')
    os.makedirs(OUT, exist_ok=True)
    Image.frombytes('RGBA', (w, h), bytes(c for y in range(h) for x in range(w) for c in pixel(x, y))).save(out)
    return out


def sheet(model, obj, tex):
    """retail_sheet.py's four renders of the OBJ in its texture -> work/units/ice/<model>_grid.png."""
    prefix = os.path.join(OUT, model)
    subprocess.run([retail_sheet.BLENDER, '-b', '--factory-startup', '-P', retail_sheet.__file__, '--', prefix,
                    f'{obj}={tex}'], check=True, stdout=subprocess.DEVNULL)
    grid = Image.new('RGB', (1536, 1536), (208, 208, 208))
    for k, v in enumerate(retail_sheet.VIEWS):
        grid.paste(Image.open(f'{prefix}_{v}.png').convert('RGB').resize((768, 768)), ((k % 2) * 768, (k // 2) * 768))
    grid.resize((1024, 1024), Image.LANCZOS).save(prefix + '_grid.png')
    return prefix + '_grid.png'


def main(models):
    by = retail_mesh.library()
    tex = textures()
    print('engineer texture ->', engineer_texture())
    skipped = []
    for model in [m for m in models or sorted(PROPS) if m in PROPS]:
        if missing(model):
            skipped.append(model)
            continue
        prop(model)
    for model in [m for m in models or sorted(KITS) if m in KITS]:
        obj, n = build(by, model)
        print(model, n, 'triangles ->', sheet(model, obj, tex))
    snow = snow_texture() if [m for m in models or BANKS if m in BANKS] else None
    for model in [m for m in models or sorted(BANKS) if m in BANKS]:
        obj, n = bank(model)
        print(model, n, 'triangles ->', sheet(model, obj, snow))
    for model in skipped:
        unit = PROPS[model]
        print(f'SKIPPED {model}: missing ' + ', '.join(missing(model)) + '\n  it is rebuilt only from the Tripo '
              f'download (tripo_unit.py UNITS["{unit}"]["glb"], under work/; re-export it from the Tripo account if '
              f'lost): blender -b --factory-startup -P experimental/units/tripo_unit.py -- {unit}, then '
              f'ice_kit.py {model}')
    if skipped and models:
        raise SystemExit(1)


if __name__ == '__main__':
    main(sys.argv[1:])
