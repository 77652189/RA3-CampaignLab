"""Ice models kitbashed from retail's Iceland glaciers (IL_GLACIER01 .. 09A, World Builder's stream: faceted ice,
white-cyan, the look the game already has), for the 冰幕工兵's wall and core (experimental/cnv/units/icewall.py):

  python -I -X utf8 experimental/units/ice_kit.py [<model> ...]      (default: all of KITS)

Each kit is a few glacier meshes turned, scaled and moved (retail UVs kept: the texture tiles across), then the whole
fitted to the footprint and height asked. Written to the SDK's Art folder (w3x.write_model) as one rigid mesh on
ROOTTRANSFORM with the shared textures CNIce / CNIce_NRM / CNIce_SPM (retail IL_Glacier01's diffuse; flat normal map
-- the glaciers have no tangents, their shader is not normal-mapped; SPM: a little specular, no glow, no house
colour). A preview sheet (retail_sheet.py's renders) goes to work/units/ice/<model>_grid.png. Also the engineer's
own texture, CNIceEngineer (engineer_texture).
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
    verts, normals, uvs, tris = [], [], [], []
    for glacier, turn, (x, y), size in recipe:
        v, n, u, t = _piece(by, glacier, turn, (x * side / 2, y * side / 2), size, side)
        tris += [tuple(i + len(verts) for i in tri) for tri in t]
        verts, normals, uvs = verts + v, normals + n, uvs + u
    # fit: the footprint within the side (a little inside, so it does not hang over its building's edges), the top
    # at `height`; a non-uniform scale, so the normals by the inverse
    lo = [min(p[i] for p in verts) for i in range(3)]
    hi = [max(p[i] for p in verts) for i in range(3)]
    k = [0.96 * side / (hi[0] - lo[0]), 0.96 * side / (hi[1] - lo[1]), height / hi[2]]
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


def main(models):
    by = retail_mesh.library()
    tex = textures()
    print('engineer texture ->', engineer_texture())
    for model in [m for m in models or sorted(PROPS) if m in PROPS]:
        prop(model)
    for model in [m for m in models or sorted(KITS) if m in KITS]:
        obj, n = build(by, model)
        prefix = os.path.join(OUT, model)
        subprocess.run([retail_sheet.BLENDER, '-b', '--factory-startup', '-P', retail_sheet.__file__, '--', prefix,
                        f'{obj}={tex}'], check=True, stdout=subprocess.DEVNULL)
        grid = Image.new('RGB', (1536, 1536), (208, 208, 208))
        for k, v in enumerate(retail_sheet.VIEWS):
            grid.paste(Image.open(f'{prefix}_{v}.png').convert('RGB').resize((768, 768)), ((k % 2) * 768, (k // 2) * 768))
        grid.resize((1024, 1024), Image.LANCZOS).save(prefix + '_grid.png')
        print(model, n, 'triangles ->', prefix + '_grid.png')


if __name__ == '__main__':
    main(sys.argv[1:])
