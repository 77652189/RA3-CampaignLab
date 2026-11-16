r"""Can a new unit model be recognised at game distance? A minimal check, calibrated on retail units.

  python -I -X utf8 experimental/units/readability.py calibrate <faction> [--no-vision]
      renders the retail units of the faction at the game's real camera, measures size classes, the silhouette
      overlap between retail units, the team-colour share seen from above, and (Codex CLI) whether a vision model
      tells them apart in a game-size lineup -> work/units/readability/calibration_<faction>.json
  python -I -X utf8 experimental/units/readability.py check <model.glb> --faction allied|japan|soviet --size <class>
      scales the model to its size class, renders it the same way and judges it against the calibration:
      PASS / FAIL per metric + a contact sheet (game size 1x and 4x next to the retail lineup)
  python -I -X utf8 experimental/units/readability.py thumb <image.png> --size <class> [--faction allied]
      shrinks a 2D reference sheet's three-quarter view to the game pixel size of that class (the thumbnail a
      reference sheet must pass before modelling)

Size classes: infantry (humans and hero-sized: height), light, main, heavy, air (longest horizontal extent).
Outputs go to work/units/readability/ (private). The same file is the Blender script (run with -b -P ... -- job.json).

Camera (measured, not guessed). experimental/testbench/calib.py fits a ground-plane -> screen homography from real
bench frames (a grid of Guardians, 1280 x 720, the default zoom of the test maps). Its local Jacobian at the screen
centre (world 1296, 2466) is 1.502 px per world unit along east-west and 1.177 px per unit north-south, so the
ground is foreshortened by 0.784 = sin(elevation): elevation 51.6 degrees (calib.py's own comment says ~52). The
fit has a 3.5 degree shear (yaw) which is ignored. Model units are taken as map units (the Guardians of that grid
stand 45 units apart and are drawn 50 px apart, side by side, which only fits that scale; not measured on a bench
frame of a single unit, so this is the one unverified assumption). Units are rendered orthographic with
PPU px per unit, viewed from the south, turned by the azimuth about the vertical.
"""
import argparse
import importlib.util
import json
import math
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BLENDER = os.environ.get('CNV_BLENDER', r'C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe')

PPU = 1.502                                  # px per world unit, east-west at the screen centre (calib.py, see above)
PITCH_DEG = round(math.degrees(math.asin(1.177 / 1.502)), 1)   # 51.6: camera elevation from the north-south scale
AZIMUTHS = (0, 45, 90, 135, 180, 225, 270, 315)    # the unit's heading against the camera; 45 is the main view
MAIN_AZ = 45
CANVAS = 320                                 # game-size render canvas, px (King Oni fits)
SS = 2                                       # supersampling of the Blender render, box-filtered down
REF_PPU = 4.5                                # the large reference renders for the vision model
TEAM = (0.10, 0.22, 0.85, 1)                 # team colour as retail_sheet.py paints it
GROUND = (118, 118, 118)                     # mid-grey ground-like background
MEASURE = {'infantry': 'height', 'light': 'horizontal', 'main': 'horizontal', 'heavy': 'horizontal',
           'air': 'horizontal'}              # infantry meshes are in a T pose: height is the honest size

# Retail calibration set. key -> (faction, size class, meshes). Keys are the asset stems unless the unit is sure
# (guardian, athena); probable in-game names: auifv Multigunner IFV, auavt3 Mirage, auavi Peacekeeper, au air
# Vindicator / Apollo, jucommando Yuriko, juavi Rocket Angel, juaa Tengu?, juaiv Striker VX?. Textures are looked
# up by the asset stem (<stem>, <stem>_SPM for the team mask, <stem>_Treads or the faction's tread sheet).
CATALOG = {
    'guardian': ('allied', 'main', ['AUANTIVEHICLEVEHICLETECH1_SKN.NEWSKIN', 'AUANTIVEHICLEVEHICLETECH1_SKN.NEWSKIN_TREADS']),
    'athena': ('allied', 'main', ['AUANTISTRUCTUREVEHICLE_SKN.NEWSKIN', 'AUANTISTRUCTUREVEHICLE_SKN.NEWSKIN_TREADS']),
    'auifv': ('allied', 'light', ['AUIFV_SKN.NEWSKIN']),
    'auavt3': ('allied', 'light', ['AUANTIVEHICLEVEHICLETECH3_SKN.NEWSKIN', 'AUANTIVEHICLEVEHICLETECH3_SKN.NEWSKIN_TREADS']),
    'auaiv': ('allied', 'light', ['AUANTIINFANTRYVEHICLE_SKN.NEWSKIN']),
    'tanya': ('allied', 'infantry', ['AUCOMMANDOTECH1_SKN.TANYA']),
    'auengineer': ('allied', 'infantry', ['AUENGINEER_SKN.AUENGINEER']),
    'aumcv': ('allied', 'heavy', ['AUMCV_SKN.NEWSKIN', 'AUMCV_SKN.NEWSKIN_TREADS']),
    'aubomber': ('allied', 'air', ['AUBOMBERAIRCRAFT_SKN.NEWSKIN']),
    'aufighter': ('allied', 'air', ['AUFIGHTERAIRCRAFT_SKN.NEWSKIN']),
    'juavt1': ('japan', 'main', ['JUANTIVEHICLEVEHICLETECH1_SKN.NEWSKIN', 'JUANTIVEHICLEVEHICLETECH1_SKN.NEWSKIN_TREADS']),
    'juasv': ('japan', 'main', ['JUANTISTRUCTUREVEHICLE_SKN.NEWSKIN', 'JUANTISTRUCTUREVEHICLE_SKN.NEWSKIN_TREADS']),
    'juaa': ('japan', 'main', ['JUANTIAIRVEHICLETECH1_SKN.ANTIAIRVEHICLE']),
    'juaiv': ('japan', 'light', ['JUANTIINFANTRYVEHICLE_SKN.JUANTIINFANTRYVEHICLE']),
    'juavi': ('japan', 'infantry', ['JUANTIVEHICLEINFANTRY_SKN.JAPANANTIVEHICLEINFANTRY']),
    'juaii': ('japan', 'infantry', ['JUANTIINFANTRYINFANTRY_SKN.JUANTIINFANTRYINFANTRY01']),
    'jucommando': ('japan', 'infantry', ['JUCOMMANDOTECH1_SKN.JUCOMMANDOTECH1']),
    'jumcv': ('japan', 'heavy', ['JUMCV_SKN.NEWSKIN', 'JUMCV_SKN.NEWSKIN_TREADS']),
    'jumechaking': ('japan', 'heavy', ['JUMECHAKING_SKN.MECH_BASE', 'JUMECHAKING_TORSO_SKN.TORSO']),
    # soviet: written but not calibrated yet
    'hammer': ('soviet', 'main', ['SUANTIVEHICLEVEHICLETECH1_SKN.NEWSKIN', 'SUANTIVEHICLEVEHICLETECH1_SKN.NEWSKIN_TREADS']),
    'suasv': ('soviet', 'main', ['SUANTISTRUCTUREVEHICLE_SKN.NEWSKIN', 'SUANTISTRUCTUREVEHICLE_SKN.NEWSKIN_TREADS']),
    'suavt3': ('soviet', 'main', ['SUANTIVEHICLEVEHICLETECH3_SKN.NEWSKIN', 'SUANTIVEHICLEVEHICLETECH3_SKN.NEWSKIN_TREADS']),
    'suengineer': ('soviet', 'infantry', ['SUENGINEER_SKN.SUENGINEER']),
    'sumcv': ('soviet', 'heavy', ['SUMCV_SKN.NEWSKIN', 'SUMCV_SKN.NEWSKIN_TREADS']),
    'sufighter': ('soviet', 'air', ['SUFIGHTERAIRCRAFT_SKN.NEWSKIN']),
}
TREAD_SHEETS = {'AU': 'autreads', 'JU': 'jptreads', 'SU': 'soviet_treads'}


def _load(name, *rel):
    """Load a repo module by file path (guard G4: no sys.path edits in new files)."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, 'experimental', *rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def outdir():
    labpaths = _load('labpaths', 'campaign', 'labpaths.py')
    d = os.path.join(labpaths.WORK, 'units', 'readability')
    os.makedirs(d, exist_ok=True)
    return d


# ---------------------------------------------------------------- pure metric functions (tests/test_readability.py)

def median(values):
    v = sorted(values)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def class_extent(lo, hi, measure):
    """The size a class is measured by: the height of a humanoid, else the longest horizontal extent."""
    if measure == 'height':
        return hi[2] - lo[2]
    return max(hi[0] - lo[0], hi[1] - lo[1])


def px_size(extent, ppu=PPU):
    return extent * ppu


def centred(mask):
    """The mask moved so its bounding box is centred on the canvas (no wrap-around: the canvas has margin)."""
    import numpy as np
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return mask
    h, w = mask.shape
    dy = (h - 1) // 2 - (int(ys.min()) + int(ys.max())) // 2
    dx = (w - 1) // 2 - (int(xs.min()) + int(xs.max())) // 2
    out = np.zeros_like(mask)
    y0, y1 = max(0, dy), min(h, h + dy)
    x0, x1 = max(0, dx), min(w, w + dx)
    out[y0:y1, x0:x1] = mask[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
    return out


def iou(a, b):
    inter = int((a & b).sum())
    union = int((a | b).sum())
    return inter / union if union else 0.0


def best_iou(masks_a, masks_b):
    """Largest IoU of two units' centred silhouettes over the azimuths both were rendered at -> (iou, azimuth)."""
    best = (0.0, None)
    for az in sorted(set(masks_a) & set(masks_b)):
        v = iou(centred(masks_a[az]), centred(masks_b[az]))
        if v > best[0]:
            best = (v, az)
    return best


def pairwise_iou(masks):
    """{name: {azimuth: bool mask}} -> {(a, b): (iou, azimuth)} for every pair of names."""
    names = sorted(masks)
    return {(a, b): best_iou(masks[a], masks[b]) for i, a in enumerate(names) for b in names[i + 1:]}


def hsv(rgb):
    """uint8 RGB array -> uint8 HSV array (PIL's scale: every channel 0..255, hue 170 = blue)."""
    import numpy as np
    from PIL import Image
    return np.asarray(Image.fromarray(np.ascontiguousarray(rgb[..., :3])).convert('HSV'))


def fit_team_box(on, off, mask, pct=(2, 98), min_diff=60):
    """HSV box of team-colour pixels, learned from retail renders: the pixels inside the silhouette that change
    when the team tint is switched on (rgb arrays `on` / `off`). Percentile bounds of hue, saturation, value."""
    import numpy as np
    diff = np.abs(on[..., :3].astype(int) - off[..., :3].astype(int)).sum(axis=2) > min_diff
    sel = diff & mask
    if sel.sum() < 20:
        raise ValueError('no team-colour pixels found: is the tint on?')
    px = hsv(on)[sel]
    return {c: [int(np.percentile(px[:, i], pct[0])), int(np.percentile(px[:, i], pct[1]))]
            for i, c in enumerate('hsv')}


def team_pixels(rgb, mask, box):
    import numpy as np
    h = hsv(rgb)
    ok = mask.copy()
    for i, c in enumerate('hsv'):
        ok &= (h[..., i] >= box[c][0]) & (h[..., i] <= box[c][1])
    return ok


def team_fraction(rgb, mask, box):
    """Share of the silhouette (top-down render) that is team-colour blue."""
    n = int(mask.sum())
    return float(team_pixels(rgb, mask, box).sum()) / n if n else 0.0


TEAM_LIFT = 40.5      # tripo_unit.team_mask: blue this far above max(red, green) is mask > 0.5 (team-coloured in game)


def ingame_team_fraction(rgb, mask):
    """Share of the silhouette that becomes team colour in game for a Tripo model: the same blue-lift rule
    tripo_unit.team_mask bakes into the mask. Measured the same way on retail renders with the team tint on, it
    gives about what the retail HSV box gives, so one ruler serves both."""
    import numpy as np
    a = rgb[..., :3].astype(int)
    lift = a[..., 2] - np.maximum(a[..., 0], a[..., 1])
    n = int(mask.sum())
    return float(((lift > TEAM_LIFT) & mask).sum()) / n if n else 0.0


def pass_range(values):
    return (min(values), max(values))


def in_range(value, rng):
    return rng[0] <= value <= rng[1]


def bbox(mask):
    import numpy as np
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def score_answer(answer, truth):
    """answer {number: name} vs truth {number: name} -> (hits, total)."""
    return sum(1 for k, v in truth.items() if str(answer.get(str(k), '')).strip().lower() == v.lower()), len(truth)


def parse_json(text):
    """The first {...} object in a model's reply (it may wrap it in prose or a fence)."""
    a, b = text.find('{'), text.rfind('}')
    if a < 0 or b < a:
        return None
    try:
        return json.loads(text[a:b + 1])
    except ValueError:
        return None


# ---------------------------------------------------------------- Blender side

def blender_main(jobfile):
    import bpy
    from mathutils import Vector
    jobs = json.load(open(jobfile, encoding='utf-8'))
    for job in jobs:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        root = bpy.data.objects.new('root', None)
        pivot = bpy.data.objects.new('pivot', None)
        scene.collection.objects.link(root)
        scene.collection.objects.link(pivot)
        root.parent = pivot
        meshes = []
        for part in job['parts']:
            before = set(scene.objects)
            if part['path'].lower().endswith(('.glb', '.gltf')):
                bpy.ops.import_scene.gltf(filepath=part['path'])
                new = [o for o in scene.objects if o not in before]
            else:
                bpy.ops.wm.obj_import(filepath=part['path'], forward_axis='Y', up_axis='Z')
                new = [o for o in scene.objects if o not in before]
                for ob in new:
                    if ob.type == 'MESH':
                        _retail_material(ob, part)
            for ob in new:
                if ob.parent is None:
                    ob.parent = root
            meshes += [o for o in new if o.type == 'MESH']
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
        lo = Vector([min(p[i] for p in pts) for i in range(3)])
        hi = Vector([max(p[i] for p in pts) for i in range(3)])
        ctr = (lo + hi) / 2
        scale = 1.0
        if job.get('target'):
            measure = job['target']['measure']
            have = (hi.z - lo.z) if measure == 'height' else max(hi.x - lo.x, hi.y - lo.y)
            scale = job['target']['value'] / have
        root.location = -ctr
        pivot.scale = (scale, scale, scale)
        if job.get('info_out'):
            json.dump({'lo': list(lo), 'hi': list(hi), 'scale': scale}, open(job['info_out'], 'w'))
        s = scene
        w = bpy.data.worlds.new('w')
        w.use_nodes = True
        w.node_tree.nodes['Background'].inputs[0].default_value = (0.8, 0.8, 0.8, 1)
        w.node_tree.nodes['Background'].inputs[1].default_value = 0.9
        s.world = w
        for ang, e in ((50, 3.0), (-60, 1.2)):
            sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
            sun.data.energy = e
            sun.rotation_euler = (math.radians(45), 0, math.radians(ang))
            s.collection.objects.link(sun)
        engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
        s.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in engines else 'BLENDER_EEVEE_NEXT'
        s.view_settings.view_transform = 'Standard'
        s.render.film_transparent = True
        s.render.image_settings.file_format = 'PNG'
        s.render.image_settings.color_mode = 'RGBA'
        cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
        cam.data.type = 'ORTHO'
        cam.data.clip_end = 5000
        s.collection.objects.link(cam)
        s.camera = cam
        for v in job['views']:
            for ob in meshes:
                if ob.type == 'MESH' and ob.data.materials:
                    _set_team(ob, v.get('team', True))
            pivot.rotation_euler = (0, 0, math.radians(v['az']))
            el = math.radians(v['el'])
            d = Vector((0, -math.cos(el), math.sin(el)))
            if v['el'] >= 89.9:
                d = Vector((0, -1e-3, 1)).normalized()
            cam.location = d * 1000
            cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
            cam.data.ortho_scale = v['canvas'] / v['ppu']
            s.render.resolution_x = s.render.resolution_y = v['canvas'] * v['ss']
            s.render.filepath = v['out']
            bpy.ops.render.render(write_still=True)


def _retail_material(ob, part):
    import bpy
    mat = bpy.data.materials.new('m')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.6
    col = None
    if part.get('tex'):
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(part['tex'])
        col = img.outputs['Color']
    if col is not None:
        # the team mix node: Factor 0 = untinted (switched per view by _set_team), SPM blue channel gates the tint
        if part.get('spm'):
            spm = nt.nodes.new('ShaderNodeTexImage')
            spm.image = bpy.data.images.load(part['spm'])
            spm.image.colorspace_settings.name = 'Non-Color'
            sep = nt.nodes.new('ShaderNodeSeparateColor')
            nt.links.new(spm.outputs['Color'], sep.inputs[0])
            mix = nt.nodes.new('ShaderNodeMix')
            mix.name = 'team'
            mix.data_type = 'RGBA'
            mix.blend_type = 'MULTIPLY'
            mix.inputs['B'].default_value = tuple(TEAM)
            nt.links.new(sep.outputs['Blue'], mix.inputs['Factor'])
            nt.links.new(col, mix.inputs['A'])
            col = mix.outputs['Result']
        nt.links.new(col, bsdf.inputs['Base Color'])
    ob.data.materials.clear()
    ob.data.materials.append(mat)


def _set_team(ob, on):
    """Team tint on / off: with it off the mix node's tint colour is white (the plain texture)."""
    for mat in ob.data.materials:
        node = mat.node_tree.nodes.get('team') if mat and mat.use_nodes else None
        if node is not None:
            node.inputs['B'].default_value = tuple(TEAM) if on else (1, 1, 1, 1)


# ---------------------------------------------------------------- retail side (Python)

def prepare_retail(keys):
    """Retail meshes -> OBJ, textures -> PNG (reference caches in work/reference). Returns
    {key: {'parts': [{'path', 'tex', 'spm'}], 'lo', 'hi'}} with the bind-pose bounding box over the parts."""
    rm = _load('retail_mesh', 'units', 'retail_mesh.py')
    rt = _load('retail_texture', 'units', 'retail_texture.py')
    by = rm.library()
    os.makedirs(rm.OUT, exist_ok=True)
    out = {}
    want = set()
    for key in keys:
        _, _, meshes = CATALOG[key]
        parts, vs = [], []
        for mid in meshes:
            stem = mid.split('_SKN')[0]
            cands = [stem.lower() + '_treads', TREAD_SHEETS[stem[:2]]] if mid.endswith('_TREADS') else [stem.lower()]
            tex = next((c for c in cands if 'texture:' + c in by), None)
            spm = tex + '_spm' if tex and 'texture:' + tex + '_spm' in by and not mid.endswith('_TREADS') else None
            for t in (tex, spm):
                if t:
                    want.add(t)
            m = rm.load(by, mid)
            vs += m['vertices']
            path = os.path.join(rm.OUT, mid + '.obj')
            rm.write_obj(m, path)
            parts.append({'path': path, 'tex': tex, 'spm': spm})
        out[key] = {'parts': parts,
                    'lo': [min(v[i] for v in vs) for i in range(3)], 'hi': [max(v[i] for v in vs) for i in range(3)]}
    missing = [t for t in want if not os.path.exists(os.path.join(rt.OUT, t + '.png'))]
    if missing:
        rt.main(sorted(missing))
    for e in out.values():
        for p in e['parts']:
            for k in ('tex', 'spm'):
                if p[k]:
                    p[k] = os.path.join(rt.OUT, p[k] + '.png')
    return out


def view_list(base, azimuths=AZIMUTHS, top=True, ref=False):
    """Blender views of one unit: every azimuth at the game camera (team tint on); a top-down pair (tint on /
    off) for the team colour; optionally the large clean reference at the main azimuth."""
    v = [dict(out=f'{base}_az{az:03d}_ss.png', az=az, el=PITCH_DEG, ppu=PPU, canvas=CANVAS, ss=SS, team=True)
         for az in azimuths]
    if top:
        v += [dict(out=f'{base}_top_{t}_ss.png', az=0, el=90, ppu=PPU, canvas=CANVAS, ss=SS, team=t == 'on')
              for t in ('on', 'off')]
    if ref:
        v.append(dict(out=f'{base}_ref.png', az=MAIN_AZ, el=PITCH_DEG, ppu=REF_PPU, canvas=int(CANVAS * REF_PPU / PPU),
                      ss=1, team=True))
    return v


def run_blender(jobs, tmp):
    jf = os.path.join(tmp, f'jobs_{os.getpid()}.json')       # parallel runs must not share a job file
    json.dump(jobs, open(jf, 'w', encoding='utf-8'))
    r = subprocess.run([BLENDER, '-b', '--factory-startup', '-P', os.path.abspath(__file__), '--', jf],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode:
        raise SystemExit('Blender failed:\n' + r.stdout[-1500:] + r.stderr[-1500:])


def downsample(tmp_png, final_png):
    """2x supersampled RGBA render -> game-size RGBA (premultiplied-correct box filter)."""
    from PIL import Image
    im = Image.open(tmp_png).convert('RGBA')
    n = CANVAS
    im = im.resize((n, n), Image.BOX)
    im.save(final_png)
    return im


def game_images(base):
    """Collect the game-size renders of one unit: {az: RGBA ndarray}, top on, top off."""
    import numpy as np
    from PIL import Image
    az = {a: np.asarray(Image.open(f'{base}_az{a:03d}.png').convert('RGBA')) for a in AZIMUTHS}
    top = {t: np.asarray(Image.open(f'{base}_top_{t}.png').convert('RGBA')) for t in ('on', 'off')}
    return az, top


def finish_renders(base):
    for a in AZIMUTHS:
        downsample(f'{base}_az{a:03d}_ss.png', f'{base}_az{a:03d}.png')
    for t in ('on', 'off'):
        downsample(f'{base}_top_{t}_ss.png', f'{base}_top_{t}.png')


def mask_of(rgba):
    return rgba[..., 3] > 127


def on_ground(rgba):
    """RGBA -> RGB on the mid-grey ground."""
    from PIL import Image
    bg = Image.new('RGBA', (rgba.shape[1], rgba.shape[0]), GROUND + (255,))
    bg.alpha_composite(Image.fromarray(rgba))
    return bg.convert('RGB')


# ---------------------------------------------------------------- vision model (Codex CLI)

def lineup_image(items, seed=7, blur=0.6, scale=2):
    """items [(name, RGBA game-size ndarray)] -> (image, {number: name}): tight cells at game pixel size, slightly
    blurred, shuffled, numbered, then enlarged `scale`x so the model's own downscaling does not eat them."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    order = list(items)
    random.Random(seed).shuffle(order)
    boxes = [bbox(mask_of(a)) for _, a in order]
    side = max(max(b[2] - b[0], b[3] - b[1]) for b in boxes) + 16
    font = ImageFont.load_default(size=14)
    sheet = Image.new('RGB', (side * len(order), side + 20), GROUND)
    d = ImageDraw.Draw(sheet)
    truth = {}
    for i, ((name, a), b) in enumerate(zip(order, boxes)):
        cell = on_ground(a).crop(b)
        cell = cell.filter(ImageFilter.GaussianBlur(blur))
        sheet.paste(cell, (i * side + (side - cell.width) // 2, 20 + (side - cell.height) // 2))
        d.text((i * side + side // 2 - 4, 2), str(i + 1), fill=(255, 255, 255), font=font)
        truth[str(i + 1)] = name
    return sheet.resize((sheet.width * scale, sheet.height * scale), Image.BICUBIC), truth


def reference_sheet(items, cell=300, cols=4):
    """items [(name, large RGBA ndarray)] -> labelled grid of clean references."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.load_default(size=16)
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cell, rows * (cell + 22)), GROUND)
    d = ImageDraw.Draw(sheet)
    for i, (name, a) in enumerate(sorted(items, key=lambda t: t[0])):
        b = bbox(mask_of(a))
        im = on_ground(a).crop(b)
        im.thumbnail((cell - 10, cell - 10))
        x, y = (i % cols) * cell, (i // cols) * (cell + 22)
        sheet.paste(im, (x + (cell - im.width) // 2, y + 22 + (cell - im.height) // 2))
        d.text((x + 6, y + 3), name, fill=(255, 255, 255), font=font)
    return sheet


def ask_vision(lineup_png, ref_png, names, run_dir):
    """Codex CLI with two images; returns the parsed {number: name} or None with a message printed."""
    try:
        exe = _load('concept_gpt', 'units', 'concept_gpt.py').codex()
    except BaseException as e:                     # SystemExit when codex.exe is not found
        print('vision skipped: codex unavailable:', e)
        return None
    os.makedirs(run_dir, exist_ok=True)
    prompt = (
        'Image 1 is a lineup of numbered, shuffled, low-resolution top-left-to-right game thumbnails of units seen '
        'from a real-time-strategy game camera. Image 2 is a sheet of large clean reference renders of the same '
        'units, each labelled with its name. Every thumbnail is exactly one of the labelled units, each name used '
        f'once. Candidate names: {", ".join(sorted(names))}. Decide which number is which name.\n'
        'Reply with ONLY a JSON object mapping the number (string) to the name, nothing else.')
    last = os.path.join(run_dir, 'last.txt')
    cmd = [exe, 'exec', '--skip-git-repo-check', '-s', 'read-only', '-C', run_dir, '--json', '-o', last,
           '-i', os.path.abspath(lineup_png), '-i', os.path.abspath(ref_png), '-']
    try:
        subprocess.run(cmd, input=prompt, text=True, encoding='utf-8', stdout=subprocess.DEVNULL,
                       stderr=open(os.path.join(run_dir, 'stderr.txt'), 'w', encoding='utf-8'), check=True,
                       cwd=run_dir, timeout=420)
        return parse_json(open(last, encoding='utf-8').read())
    except Exception as e:
        print('vision skipped: codex failed:', repr(e)[:200])
        return None


# ---------------------------------------------------------------- commands

def retail_keys(faction):
    return [k for k, v in CATALOG.items() if v[0] == faction]


def render_retail(faction, reuse=False):
    d = outdir()
    tmp = os.path.join(d, 'tmp')
    rdir = os.path.join(d, 'render')
    os.makedirs(tmp, exist_ok=True)
    os.makedirs(rdir, exist_ok=True)
    keys = retail_keys(faction)
    info = prepare_retail(keys)
    jobs = [dict(name=k, parts=info[k]['parts'], target=None, views=view_list(os.path.join(rdir, k), ref=True))
            for k in keys]
    if reuse and all(os.path.exists(os.path.join(rdir, k + '_ref.png')) for k in keys):
        return info
    run_blender(jobs, tmp)
    for k in keys:
        finish_renders(os.path.join(rdir, k))
    return info


def load_retail(faction):
    d = outdir()
    masks, rgba, tops = {}, {}, {}
    for k in retail_keys(faction):
        az, top = game_images(os.path.join(d, 'render', k))
        rgba[k] = az
        masks[k] = {a: mask_of(v) for a, v in az.items()}
        tops[k] = top
    return masks, rgba, tops


def vision_lineup(names_rgba, names_ref, tag, d):
    """Run one lineup; returns (hits per name dict, answer, truth) or None."""
    from PIL import Image
    import numpy as np
    items = [(n, a) for n, a in names_rgba]
    img, truth = lineup_image(items)
    lp = os.path.join(d, f'lineup_{tag}.png')
    img.save(lp)
    rp = os.path.join(d, f'reference_{tag}.png')
    reference_sheet(names_ref).save(rp)
    ans = ask_vision(lp, rp, [n for n, _ in items], os.path.join(d, f'codex_{tag}'))
    if ans is None:
        return None
    ok = {truth[k]: str(ans.get(k, '')).strip().lower() == truth[k].lower() for k in truth}
    return ok, ans, truth


def ref_rgba(key, d):
    import numpy as np
    from PIL import Image
    return np.asarray(Image.open(os.path.join(d, 'render', key + '_ref.png')).convert('RGBA'))


def calibrate(faction, vision=True, reuse=False):
    d = outdir()
    keys = retail_keys(faction)
    if not keys:
        raise SystemExit(f'no retail units for {faction}')
    info = render_retail(faction, reuse)
    masks, rgba, tops = load_retail(faction)
    # size classes: median extent (world units) and median silhouette box (px at the main azimuth) per class
    ext, box = {}, {}
    for k in keys:
        c = CATALOG[k][1]
        ext.setdefault(c, []).append(class_extent(info[k]['lo'], info[k]['hi'], MEASURE[c]))
        b = bbox(masks[k][MAIN_AZ])
        box.setdefault(c, []).append((b[2] - b[0], b[3] - b[1]))
    classes = {c: dict(measure=MEASURE[c], extent=round(median(v), 2), members=[k for k in keys if CATALOG[k][1] == c],
                       silhouette_px=[round(median([b[0] for b in box[c]]), 1), round(median([b[1] for b in box[c]]), 1)])
               for c, v in ext.items()}
    # silhouette distinctness
    pw = pairwise_iou(masks)
    top_pair = max(pw.items(), key=lambda kv: kv[1][0])
    # team colour
    onoff = [(tops[k]['on'], tops[k]['off']) for k in keys]
    import numpy as np
    on = np.concatenate([a[..., :3].reshape(-1, 3) for a, _ in onoff]).reshape(-1, 1, 3)
    off = np.concatenate([b[..., :3].reshape(-1, 3) for _, b in onoff]).reshape(-1, 1, 3)
    msk = np.concatenate([mask_of(a).reshape(-1) for a, _ in onoff]).reshape(-1, 1)
    box_hsv = fit_team_box(on, off, msk)
    frac = {k: team_fraction(tops[k]['on'][..., :3], mask_of(tops[k]['on']), box_hsv) for k in keys}
    fp = {k: team_fraction(tops[k]['off'][..., :3], mask_of(tops[k]['off']), box_hsv) for k in keys}
    res = dict(faction=faction, camera=dict(pitch_deg=PITCH_DEG, ppu=PPU, canvas=CANVAS, azimuths=list(AZIMUTHS)),
               classes=classes,
               iou=dict(pass_max=round(top_pair[1][0], 4), worst_pair=list(top_pair[0]), at_azimuth=top_pair[1][1],
                        pairs={f'{a}|{b}': round(v[0], 4) for (a, b), v in sorted(pw.items())}),
               team=dict(hsv_box=box_hsv, fraction={k: round(v, 4) for k, v in frac.items()},
                         pass_range=[round(x, 4) for x in pass_range([v for v in frac.values() if v > 0])],
                         untinted_retail=[k for k, v in frac.items() if v == 0],   # no team mask in their texture
                         false_positive_untinted={k: round(v, 4) for k, v in fp.items()}))
    if vision:
        v = vision_lineup([(k, rgba[k][MAIN_AZ]) for k in keys], [(k, ref_rgba(k, d)) for k in keys], 'cal_' + faction, d)
        if v is None:
            res['vision'] = dict(skipped=True)
        else:
            ok, ans, truth = v
            res['vision'] = dict(hit_rate=round(sum(ok.values()) / len(ok), 3), hits=ok, answer=ans, truth=truth)
    else:
        res['vision'] = dict(skipped=True)
    path = os.path.join(d, f'calibration_{faction}.json')
    json.dump(res, open(path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps({k: res[k] for k in ('classes', 'iou', 'vision')}, indent=1, ensure_ascii=False)[:6000])
    print('team fraction', res['team']['fraction'], 'pass range', res['team']['pass_range'])
    print('->', path)


def load_calibration(faction):
    p = os.path.join(outdir(), f'calibration_{faction}.json')
    if not os.path.exists(p):
        raise SystemExit(f'run `calibrate {faction}` first ({p} missing)')
    return json.load(open(p, encoding='utf-8'))


def class_info(cal, size):
    if size in cal['classes']:
        return cal['classes'][size]
    for f in ('allied', 'japan', 'soviet'):          # a class the faction has no retail unit in: use another's
        p = os.path.join(outdir(), f'calibration_{f}.json')
        if os.path.exists(p):
            c = json.load(open(p, encoding='utf-8'))['classes']
            if size in c:
                print(f'note: no retail {size} in this faction, using the class median of {f}')
                return c[size]
    raise SystemExit(f'unknown size class {size}; known: {sorted(cal["classes"])}')


def contact_sheet(name, new_rgba, new_top, rgba, keys, cal, size, path):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.load_default(size=14)
    items = [('NEW ' + name, new_rgba)] + [(k, rgba[k][MAIN_AZ]) for k in keys]
    boxes = [bbox(mask_of(a)) for _, a in items]
    side = max(max(b[2] - b[0], b[3] - b[1]) for b in boxes) + 16
    peers = [k for k in keys if CATALOG[k][1] == size][:3] or keys[:3]
    row2 = [items[0]] + [(k, rgba[k][MAIN_AZ]) for k in peers]
    rows = [(items, 1), (row2, 4)]
    sheet_w = max(len(r) * (side if m == 1 else (side + 8) * m) for r, m in rows)
    h = (side + 24) + (side * 4 + 24) + 24
    sheet = Image.new('RGB', (sheet_w, h), GROUND)
    d = ImageDraw.Draw(sheet)
    y = 0
    for row, m in rows:
        cell_w = side * m
        for i, (n, a) in enumerate(row):
            b = bbox(mask_of(a))
            cell = on_ground(a).crop(b)
            if m != 1:
                cell = cell.resize((cell.width * m, cell.height * m), Image.NEAREST)
            x = i * cell_w
            sheet.paste(cell, (x + (cell_w - cell.width) // 2, y + 20 + (side * m - cell.height) // 2))
            d.text((x + 4, y + 2), f'{n} ({m}x)', fill=(255, 255, 255), font=font)
        y += side * m + 24
    sheet.crop((0, 0, sheet_w, y)).save(path)


def check(model, faction, size):
    from PIL import Image
    import numpy as np
    d = outdir()
    cal = load_calibration(faction)
    model = os.path.abspath(model)
    name = os.path.splitext(os.path.basename(model))[0]
    keys = retail_keys(faction)
    masks, rgba, tops = load_retail(faction)
    ci = class_info(cal, size)
    rdir = os.path.join(d, 'render')
    tmp = os.path.join(d, 'tmp')
    os.makedirs(tmp, exist_ok=True)
    info_out = os.path.join(tmp, name + '_info.json')
    base = os.path.join(rdir, 'new_' + name)
    job = dict(name=name, parts=[{'path': model}], target=dict(measure=ci['measure'], value=ci['extent']),
               views=view_list(base, ref=True), info_out=info_out)
    run_blender([job], tmp)
    finish_renders(base)
    az, top = game_images(base)
    nm = {a: mask_of(v) for a, v in az.items()}
    inf = json.load(open(info_out))
    print(f'{name}: scaled x{inf["scale"]:.4g} to {size} ({ci["measure"]} {ci["extent"]} units = '
          f'{ci["extent"] * PPU:.0f} px)')
    lines = []
    ok_all = True
    # 1 silhouette distinctness
    vs = {k: best_iou(nm, masks[k]) for k in keys}
    worst = max(vs.items(), key=lambda kv: kv[1][0])
    line = cal['iou']['pass_max']
    p1 = worst[1][0] <= line
    ok_all &= p1
    lines.append(f'1 silhouette IoU: {"PASS" if p1 else "FAIL"}  max vs retail {worst[1][0]:.3f} ({worst[0]}, az {worst[1][1]}) '
                 f'line <= {line:.3f}')
    # 2 team colour
    # one ruler for both: the in-game mask rule (retail renders with the tint on, the new model's own paint)
    frac = ingame_team_fraction(top['on'][..., :3], mask_of(top['on']))
    rv = [ingame_team_fraction(tops[k]['on'][..., :3], mask_of(tops[k]['on'])) for k in keys
          if CATALOG[k][1] != 'infantry']
    rng = pass_range([v for v in rv if v > 0])
    if size == 'infantry':     # retail infantry and heroes carry no team mask at all: nothing to compare against
        lines.append(f'2 team colour on top: N/A for infantry/heroes (retail ones have none); {frac:.3f} would be '
                     f'team-coloured')
    else:
        p2 = in_range(frac, rng)
        ok_all &= p2
        lines.append(f'2 team colour on top: {"PASS" if p2 else "FAIL"}  {frac:.3f} becomes team colour in game; '
                     f'retail vehicles [{rng[0]:.3f}, {rng[1]:.3f}]')
    # 3 vision
    v = vision_lineup([(name, az[MAIN_AZ])] + [(k, rgba[k][MAIN_AZ]) for k in keys],
                      [(name, np.asarray(Image.open(base + '_ref.png').convert('RGBA')))] +
                      [(k, ref_rgba(k, d)) for k in keys], 'chk_' + name, d)
    if v is None:
        lines.append('3 vision model: SKIPPED (codex unavailable or failed, see message above)')
    else:
        ok, ans, truth = v
        retail_hits = [h for n, h in ok.items() if n != name]
        rate = sum(retail_hits) / len(retail_hits)
        cal_rate = cal.get('vision', {}).get('hit_rate')
        if rate < 0.5:
            lines.append(f'3 vision model: INCONCLUSIVE  retail hit rate only {rate:.2f} here '
                         f'(calibration {cal_rate}); new model {"identified" if ok[name] else "NOT identified"}')
        else:
            p3 = ok[name]
            ok_all &= p3
            lines.append(f'3 vision model: {"PASS" if p3 else "FAIL"}  new model '
                         f'{"identified" if p3 else "NOT identified"}; retail hit rate {rate:.2f} (calibration {cal_rate})')
    sheet = os.path.join(d, f'contact_{name}.png')
    contact_sheet(name, az[MAIN_AZ], top, rgba, keys, cal, size, sheet)
    print('\n'.join(lines))
    print('OVERALL', 'PASS' if ok_all else 'FAIL (or inconclusive, see above)')
    print('contact sheet:', sheet)


def thumb(image, size, faction):
    from PIL import Image, ImageChops
    cal = load_calibration(faction)
    ci = class_info(cal, size)
    im = Image.open(image).convert('RGB')
    bg = im.getpixel((5, 5))
    fg = ImageChops.difference(im, Image.new('RGB', im.size, bg)).convert('L').point(lambda v: 255 if v > 18 else 0)
    b = fg.getbbox()
    unit = im.crop(b)
    w = ci['silhouette_px'][0]
    t = unit.resize((max(1, round(w)), max(1, round(unit.height * w / unit.width))), Image.LANCZOS)
    d = outdir()
    stem = os.path.splitext(os.path.basename(image))[0]
    parts = os.path.normpath(os.path.abspath(image)).split(os.sep)
    if 'gpt' in parts:                     # work/units/<unit>/gpt/v1_views/x.png -> <unit>_x
        stem = parts[parts.index('gpt') - 1] + '_' + stem
    cell = Image.new('RGB', (t.width + 16, t.height + 16), GROUND)
    cell.paste(t, (8, 8))
    p1 = os.path.join(d, f'{stem}_thumb.png')
    cell.save(p1)
    cell.resize((cell.width * 4, cell.height * 4), Image.NEAREST).save(os.path.join(d, f'{stem}_thumb4x.png'))
    print(f'{size}: retail silhouette at the main azimuth is {ci["silhouette_px"][0]:.0f} x {ci["silhouette_px"][1]:.0f} px; '
          f'thumbnail {t.width} x {t.height} px -> {p1} (and _thumb4x.png)')


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('calibrate')
    c.add_argument('faction', choices=['allied', 'japan', 'soviet'])
    c.add_argument('--no-vision', action='store_true')
    c.add_argument('--reuse', action='store_true', help='keep existing retail renders')
    k = sub.add_parser('check')
    k.add_argument('model')
    k.add_argument('--faction', required=True, choices=['allied', 'japan', 'soviet'])
    k.add_argument('--size', required=True)
    t = sub.add_parser('thumb')
    t.add_argument('image')
    t.add_argument('--size', required=True)
    t.add_argument('--faction', default='allied', choices=['allied', 'japan', 'soviet'])
    a = ap.parse_args(argv)
    if a.cmd == 'calibrate':
        calibrate(a.faction, not a.no_vision, a.reuse)
    elif a.cmd == 'check':
        check(a.model, a.faction, a.size)
    else:
        thumb(a.image, a.size, a.faction)


def _in_blender():
    try:
        import bpy  # noqa: F401
        return True
    except ImportError:
        return False


if __name__ == '__main__':
    if '--' in sys.argv and _in_blender():
        blender_main(sys.argv[sys.argv.index('--') + 1])
    else:
        main(sys.argv[1:])
