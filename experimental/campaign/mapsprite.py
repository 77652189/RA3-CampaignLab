"""Object sprites for the map pictures (maprender --models), the way the RA2 map renderer lays its building sprites:
RA3's objects are 3D, so each template's retail model (units/retail_mesh.py, retail_texture.py) is rendered once,
straight down, in Blender (headless) with its retail textures and a sun from the north-west, and cached in
work/reference/sprites/<template>.png with <template>.json (pixels per world unit, the model origin at the centre).
composite() lays them on a picture by the objects' positions and angles, a soft shadow under each.

  python -I -X utf8 experimental/campaign/mapsprite.py <template> [...]     render (or re-render) these sprites

A template's model: the meshes of the first W3DContainer its GameObject refers to (garrison flags and walls left out;
a prop with no container: the meshes it refers to), each with the first texture the mesh refers to, swapped for the
GameObject's own variant where it names one (SA_House04_02: the sa_house04 model in texture sa_house04_02).
"""
import importlib.util
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UNITS = os.path.join(os.path.dirname(HERE), 'units')
BLENDER = os.environ.get('CNV_BLENDER', r'C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe')
PPU = 1.0                       # sprite pixels per world unit
SKIP = ('au_garrison', 'su_garrison', 'ju_garrison', 'garrison_wall')
# meshes not seen from above in play: a building's wooden fill (shown once it is broken, it covers the roof) and a
# lamp's light cone (an additive glow card, drawn opaque it is a black blot)
HIDDEN = ('fill', 'lightplane', 'light_cone', 'glow')


def _load(name, folder=UNITS):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(folder, name + '.py'))
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


def sprite_dir():
    return os.path.join(_load('labpaths', HERE).WORK, 'reference', 'sprites')


def parts(by, key, template):
    """[(mesh id, texture id or None)] of a template's model, [] when the game has none (a decal, a script object)."""
    go = by.get('gameobject:' + template.lower())
    if go is None:
        return []
    refs = [key.get(tuple(r)) for r in go.refs]
    variants = [r.split(':', 1)[1] for r in refs if r and r.startswith('texture:')]
    box = next((r for r in refs if r and r.startswith('w3dcontainer:') and not r[13:].startswith(SKIP)), None)
    meshes = [key.get(tuple(r)) for r in by[box].refs] if box else refs
    out = []
    for m in meshes:
        if not m or not m.startswith('w3dmesh:') or m[8:].startswith(SKIP) or any(h in m for h in HIDDEN):
            continue
        tex = next((t.split(':', 1)[1] for t in (key.get(tuple(r)) for r in by[m].refs)
                    if t and t.startswith('texture:')), None)
        stem = tex.rsplit('_', 1)[0] if tex and tex[-2:].isdigit() else None
        own = stem and stem + '_' + template.lower().rsplit('_', 1)[-1]          # SA_House04_02 -> sa_house04_02
        tex = own if own in variants else tex
        out.append((m[8:], tex))
    return out


def prepare(templates):
    """Meshes to OBJ and textures to PNG for the templates not cached yet; the Blender jobs for them."""
    rm, rt = _load('retail_mesh'), _load('retail_texture')
    by = rm.library()
    key = {(i.entry[0], i.entry[1]): k for k, i in by.items()}
    os.makedirs(rm.OUT, exist_ok=True)
    os.makedirs(sprite_dir(), exist_ok=True)
    jobs, want = [], set()
    for t in templates:
        ps, half = [], 0.0
        for mesh_id, tex in parts(by, key, t):
            try:
                m = rm.load(by, mesh_id)
            except (KeyError, AssertionError, IndexError):
                continue
            path = os.path.join(rm.OUT, mesh_id + '.obj')
            rm.write_obj(m, path)
            half = max([half] + [max(abs(v[0]), abs(v[1])) for v in m['vertices']])
            ps.append({'obj': path, 'tex': tex and os.path.join(rt.OUT, tex + '.png')})
            if tex:
                want.add(tex)
        if ps:
            jobs.append({'template': t, 'parts': ps, 'half': half + 4, 'ppu': PPU,
                         'out': os.path.join(sprite_dir(), t + '.png')})
    missing = sorted(t for t in want if not os.path.exists(os.path.join(rt.OUT, t + '.png')))
    if missing:
        rt.main(missing)
    return jobs


def render(templates):
    jobs = prepare(templates)
    if not jobs:
        return []
    jf = os.path.join(sprite_dir(), f'jobs_{os.getpid()}.json')
    json.dump(jobs, open(jf, 'w', encoding='utf-8'))
    r = subprocess.run([BLENDER, '-b', '--factory-startup', '-P', os.path.abspath(__file__), '--', jf],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    os.remove(jf)
    if r.returncode:
        raise SystemExit('Blender failed:\n' + r.stdout[-1500:] + r.stderr[-1500:])
    for j in jobs:
        json.dump({'ppu': j['ppu'], 'half': j['half']}, open(j['out'][:-4] + '.json', 'w'))
    return [j['template'] for j in jobs]


def sprites(templates):
    """{template: (RGBA image, pixels per world unit)}, rendering what is not cached; templates with no model left out."""
    from PIL import Image
    have = lambda t: os.path.exists(os.path.join(sprite_dir(), t + '.json'))          # noqa: E731
    todo = sorted(t for t in set(templates) if not have(t) and not os.path.exists(os.path.join(sprite_dir(), t + '.none')))
    if todo:
        done = set(render(todo))
        for t in set(todo) - done:                      # no model in the game: remember it, do not look again
            open(os.path.join(sprite_dir(), t + '.none'), 'w').close()
    out = {}
    for t in set(templates):
        if have(t):
            meta = json.load(open(os.path.join(sprite_dir(), t + '.json')))
            out[t] = (Image.open(os.path.join(sprite_dir(), t + '.png')).convert('RGBA'), meta['ppu'])
    return out


def composite(pic, objects, at, s):
    """Lay the objects' sprites on pic (RGB): at(x, y) -> picture point, s pixels per world unit. Returns the picture
    and the set of templates drawn (the caller marks the others its own way)."""
    from PIL import Image, ImageFilter
    objs = [o for o in objects if not o['template'].startswith('*')]
    got = sprites([o['template'] for o in objs])
    base = pic.convert('RGBA')
    shadow = Image.new('RGBA', base.size, (0, 0, 0, 0))
    layer = Image.new('RGBA', base.size, (0, 0, 0, 0))
    cache = {}
    for o in sorted(objs, key=lambda o: -o['y']):              # north first: southern objects drawn over them
        if o['template'] not in got:
            continue
        img, ppu = got[o['template']]
        deg = round(math.degrees(o['angle'])) % 360
        k = (o['template'], deg)
        if k not in cache:
            side = max(1, round(img.width * s / ppu))
            cache[k] = img.resize((side, side), Image.LANCZOS).rotate(deg, Image.BICUBIC, expand=True)
        sp = cache[k]
        x, y = at(o['x'], o['y'])
        pos = (round(x - sp.width / 2), round(y - sp.height / 2))
        a = sp.getchannel('A')
        shadow.paste(Image.new('RGBA', sp.size, (0, 0, 0, 150)), (pos[0] + 2, pos[1] + 2), a)
        layer.alpha_composite(sp, pos)
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(1.5)))
    base.alpha_composite(layer)
    return base.convert('RGB'), set(got)


# ---------------------------------------------------------------- Blender side

def blender_main(jobfile):
    import bpy
    for job in json.load(open(jobfile, encoding='utf-8')):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene
        for p in job['parts']:
            bpy.ops.wm.obj_import(filepath=p['obj'], forward_axis='Y', up_axis='Z')
            ob = bpy.context.selected_objects[0]
            mat = bpy.data.materials.new('m')
            mat.use_nodes = True
            nt = mat.node_tree
            bsdf = nt.nodes['Principled BSDF']
            bsdf.inputs['Roughness'].default_value = 0.8
            if p['tex'] and os.path.exists(p['tex']):
                img = nt.nodes.new('ShaderNodeTexImage')
                img.image = bpy.data.images.load(p['tex'])
                nt.links.new(img.outputs['Color'], bsdf.inputs['Base Color'])
                nt.links.new(img.outputs['Alpha'], bsdf.inputs['Alpha'])      # tree cards, fences
                mat.blend_method = 'HASHED' if hasattr(mat, 'blend_method') else None
            ob.data.materials.clear()
            ob.data.materials.append(mat)
        half = job['half']
        cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = 2 * half
        cam.data.clip_end = 5000
        cam.location = (0, 0, 2000)
        sc.collection.objects.link(cam)
        sc.camera = cam
        sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
        sun.data.energy = 3.0
        sun.rotation_euler = (math.radians(35), 0, math.radians(135))      # from the north-west, as the hill shading
        sc.collection.objects.link(sun)
        sc.world = bpy.data.worlds.new('w')
        sc.world.use_nodes = True
        sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.6
        sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in
                                                                         bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
        sc.render.film_transparent = True
        sc.render.resolution_x = sc.render.resolution_y = max(8, round(2 * half * job['ppu']))
        sc.render.filepath = job['out']
        bpy.ops.render.render(write_still=True)


def main(argv):
    for t in render(argv):
        print('sprite', t)


if __name__ == '__main__':
    if '--' in sys.argv:
        blender_main(sys.argv[sys.argv.index('--') + 1])
    else:
        main(sys.argv[1:])
