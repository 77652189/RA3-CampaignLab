"""Reference sheets of retail units for the concept step (concept_gpt.py): the retail meshes with their retail
textures (team colour from the SPM's blue channel painted blue) rendered orthographic front / side / back and a 3/4
view, laid out 2 x 2 like the sheet GPT is asked for; the 3/4 view also on a transparent ground (<name>_icon.png).

  python -I experimental/units/retail_sheet.py <name> <mesh id>=<texture id>[=<spm id>] ...  -> work/reference/sheets/<name>_grid.png

e.g. guardian AUANTIVEHICLEVEHICLETECH1_SKN.NEWSKIN=AUAntiVehicleVehicleTech1=AUAntiVehicleVehicleTech1_SPM
              AUANTIVEHICLEVEHICLETECH1_SKN.NEWSKIN_TREADS=AUAntiVehicleVehicleTech1_Treads
     athena   AUANTISTRUCTUREVEHICLE_SKN.NEWSKIN=AUAntiStructureVehicle AUANTISTRUCTUREVEHICLE_SKN.NEWSKIN_TREADS=AUTreads
Run by Python it pulls the meshes (retail_mesh.py) and textures (retail_texture.py), then runs itself in Blender
(headless) for the renders. Model space: +X forward, +Z up.
"""
import math
import os
import subprocess
import sys

BLENDER = os.environ.get('CNV_BLENDER', r'C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe')
TEAM = (0.10, 0.22, 0.85, 1)
VIEWS = ['front', 'left', 'back', 'threequarter']


def render(out, specs):
    import bpy
    from mathutils import Vector
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obs = []
    for spec in specs:
        parts = spec.split('=')
        bpy.ops.wm.obj_import(filepath=parts[0], forward_axis='Y', up_axis='Z')
        ob = bpy.context.selected_objects[0]
        mat = bpy.data.materials.new('m')
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = nt.nodes['Principled BSDF']
        bsdf.inputs['Roughness'].default_value = 0.6
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(parts[1])
        col = img.outputs['Color']
        if len(parts) > 2:
            spm = nt.nodes.new('ShaderNodeTexImage')
            spm.image = bpy.data.images.load(parts[2])
            spm.image.colorspace_settings.name = 'Non-Color'
            sep = nt.nodes.new('ShaderNodeSeparateColor')
            nt.links.new(spm.outputs['Color'], sep.inputs[0])
            mix = nt.nodes.new('ShaderNodeMix')
            mix.data_type = 'RGBA'
            mix.blend_type = 'MULTIPLY'
            mix.inputs['B'].default_value = TEAM
            nt.links.new(sep.outputs['Blue'], mix.inputs['Factor'])
            nt.links.new(col, mix.inputs['A'])
            col = mix.outputs['Result']
        nt.links.new(col, bsdf.inputs['Base Color'])
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        obs.append(ob)
    pts = [o.matrix_world @ Vector(c) for o in obs for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    c = (lo + hi) / 2
    size = max(hi - lo) * 1.15
    s = bpy.context.scene
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
    s.render.resolution_x = s.render.resolution_y = 768
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    s.collection.objects.link(cam)
    s.camera = cam
    dirs = {'front': (1, 0, 0), 'left': (0, 1, 0), 'back': (-1, 0, 0), 'threequarter': (1, -1, 0.8)}
    for name in VIEWS:
        d = Vector(dirs[name]).normalized()
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = size
        cam.data.clip_end = size * 10
        cam.location = c + d * size * 3
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        s.render.filepath = f'{out}_{name}.png'
        bpy.ops.render.render(write_still=True)
    s.render.film_transparent = True             # the 3/4 view again, no background: for a portrait (ice_kit.kit_icons)
    s.render.filepath = f'{out}_icon.png'
    bpy.ops.render.render(write_still=True)


def main(name, specs):
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    sys.path.insert(0, os.path.join(os.path.dirname(here), 'campaign'))
    import labpaths
    import retail_mesh
    import retail_texture
    from PIL import Image
    by = retail_mesh.library()
    tex = {t for s in specs for t in s.split('=')[1:]}
    retail_texture.main(sorted(tex))
    os.makedirs(retail_mesh.OUT, exist_ok=True)
    resolved = []
    for s in specs:
        mesh_id, *texs = s.split('=')
        m = retail_mesh.load(by, mesh_id)
        obj = os.path.join(retail_mesh.OUT, mesh_id + '.obj')
        retail_mesh.write_obj(m, obj)
        resolved.append('='.join([obj] + [os.path.join(retail_texture.OUT, t + '.png') for t in texs]))
    out_dir = os.path.join(labpaths.WORK, 'reference', 'sheets')
    os.makedirs(out_dir, exist_ok=True)
    prefix = os.path.join(out_dir, name)
    subprocess.run([BLENDER, '-b', '--factory-startup', '-P', os.path.abspath(__file__), '--', prefix] + resolved,
                   check=True, stdout=subprocess.DEVNULL)
    grid = Image.new('RGB', (1536, 1536), (208, 208, 208))
    for k, v in enumerate(VIEWS):
        grid.paste(Image.open(f'{prefix}_{v}.png').convert('RGB').resize((768, 768)), ((k % 2) * 768, (k // 2) * 768))
    grid.resize((1024, 1024), Image.LANCZOS).save(prefix + '_grid.png')
    print(prefix + '_grid.png')


if __name__ == '__main__':
    if '--' in sys.argv:                                   # inside Blender
        args = sys.argv[sys.argv.index('--') + 1:]
        render(args[0], args[1:])
    else:
        main(sys.argv[1], sys.argv[2:])
