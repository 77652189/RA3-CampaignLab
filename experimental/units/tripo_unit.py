"""A Tripo Studio export (GLB, generated with parts, textured) made into a game unit in Blender, headless:

  "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Blender\\blender.exe" -b --factory-startup
      -P experimental/units/tripo_unit.py -- <unit>                 -> work/units/<unit>/game/

The route (user 2026-10-26): GPT draws the three-view sheet (concept_gpt.py), Tripo turns it into a high mesh with
parts and a texture, Blender makes the game asset; to_w3x.py writes the W3X. Steps:
- the parts (tripo_part_N) grouped by UNITS[unit] into HULL / TURRET / BARREL, scaled to the retail size class
  (width over the tracks), the hull centred on the origin, the ground at z = 0; +X forward as Tripo gives it when
  the front view went into its front slot.
- each group welded and collapsed to its triangle budget (the retail Guardian is 3289 + 384 for the treads),
  sharp edges by angle; one atlas for all three (smart UV project, packed together).
- baked from the high parts with Cycles on the CPU, each low group only from its own high group (or the turret
  would pick up the hull below): base colour, and a tangent-space normal map for the detail the collapse removed.
- team-colour mask from the baked colour: GPT paints team areas saturated blue (concept_gpt.py), so blue hue and
  saturation mark it; to_w3x's retail maps turn those texels grey for the house colour.
- parts.json in each bone's space (origins at the pivots) with '_pivots' (the Guardian's bone names, placed on
  this model) for to_w3x.convert, a preview, a transparent icon render for button_icon.py, and <unit>.blend (low
  parts and their images, the high mesh left out) to touch up by hand.
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work')

# unit: Tripo GLB (under work/), width over the tracks (game units), part indices per group (the rest is HULL),
# triangle budgets, atlas size, the model / texture name
UNITS = {
    'chronolag': dict(glb='units/chronolag/tripo/chronolag_v2_hd.glb', width=25.3,
                      TURRET=[0, 8, 15, 16, 18], BARREL=[5],
                      budget=dict(HULL=2500, TURRET=1100, BARREL=400), tex=1024, model='CNChrono'),
}
SHARP = math.radians(35)


def import_parts(path):
    bpy.ops.import_scene.gltf(filepath=path)
    parts = {}
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and o.name.startswith('tripo_part_'):
            o.data.transform(o.matrix_world)
            o.parent = None
            o.matrix_world.identity()
            parts[int(o.name.rsplit('_', 1)[1])] = o
    for o in list(bpy.context.scene.objects):
        if o.type != 'MESH':
            bpy.data.objects.remove(o)
    return parts


def bbox(obs):
    pts = [o.matrix_world @ v.co for o in obs for v in o.data.vertices]
    return (Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)]))


def join(obs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = name
    return ob


def low_copy(hi, name, budget, weld):
    me = hi.data.copy()
    lo = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(lo)
    bm = bmesh.new()
    bm.from_mesh(me)
    # glTF splits every vertex on a UV seam: welded first, or the collapse stalls on the seams
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=weld)
    bm.to_mesh(me)
    bm.free()
    me.materials.clear()
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    mod = lo.modifiers.new('collapse', 'DECIMATE')
    mod.ratio = min(1.0, budget / max(n, 1))
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = lo
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in me.polygons:
        p.use_smooth = True
    me.set_sharp_from_angle(angle=SHARP)
    print(f'{name}: {n} -> {sum(len(p.vertices) - 2 for p in me.polygons)} triangles')
    return lo


def uv_atlas(lows):
    bpy.ops.object.select_all(action='DESELECT')
    for o in lows:
        o.select_set(True)
        o.data.uv_layers.new(name='UVMap')
    bpy.context.view_layer.objects.active = lows[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004)
    bpy.ops.uv.pack_islands(margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')


def bake(groups, size, out_dir, name):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 4
    sc.render.bake.use_selected_to_active = True
    sc.render.bake.margin = 8
    images = {}
    for kind in ('color', 'nrm'):
        img = bpy.data.images.new(f'{name}_{kind}', size, size, alpha=False)
        if kind == 'nrm':
            img.colorspace_settings.name = 'Non-Color'
        images[kind] = img
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    node = nt.nodes.new('ShaderNodeTexImage')
    nt.links.new(node.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
    for hi, lo in groups:
        lo.data.materials.append(mat)
    for kind in ('color', 'nrm'):
        node.image = images[kind]
        nt.nodes.active = node
        for k, (hi, lo) in enumerate(groups):
            bpy.ops.object.select_all(action='DESELECT')
            hi.select_set(True)
            lo.select_set(True)
            bpy.context.view_layer.objects.active = lo
            size_ = max(lo.dimensions)
            sc.render.bake.cage_extrusion = 0.02 * size_
            sc.render.bake.max_ray_distance = 0.06 * size_
            if kind == 'color':
                bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_clear=(k == 0))
            else:
                bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', use_clear=(k == 0))
            print('baked', kind, lo.name)
        images[kind].filepath_raw = os.path.join(out_dir, f'{name}{"_nrm" if kind == "nrm" else ""}.png')
        images[kind].file_format = 'PNG'
        images[kind].save()
    node.image = images['color']
    return images, mat


def team_mask(color_png, out_png):
    """Blue paint -> mask by how far blue stands above red and green: the team panels of the chronolag bake sit
    40..80 (of 255) above, its cool dark steel only 15..25 (saturation alone mixed the two: dark steel (51, 56, 78)
    is as saturated as light paint (128, 138, 176)); soft between 28 and 53."""
    img = bpy.data.images.load(color_png)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[..., :3] * 255
    lift = px[..., 2] - np.maximum(px[..., 0], px[..., 1])
    m = np.clip((lift - 28) / 25, 0, 1)
    out = bpy.data.images.new('mask', w, h, alpha=False)
    out.pixels[:] = np.dstack([m, m, m, np.ones_like(m)]).ravel().tolist()
    out.filepath_raw = out_png
    out.file_format = 'PNG'
    out.save()
    print(f'team mask: {(m > 0.5).mean():.3f} of the atlas')


def set_origin(ob, at):
    ob.data.transform(Matrix.Translation(-at))
    ob.location = at


def export(parts, pivots, out_dir):
    """parts.json as cnv_lighttank.export writes it (bone-space vertices, corner normals, MikkTSpace tangents)."""
    out = {}
    for name, ob in parts.items():
        me = ob.data
        me.calc_loop_triangles()
        uv = me.uv_layers.active.data
        corner = [c.vector.copy() for c in me.corner_normals]
        me.calc_tangents()
        verts, normals, uvs, tris, index, tangents, binormals = [], [], [], [], {}, [], []
        for lt in me.loop_triangles:
            tri = []
            for li in lt.loops:
                loop = me.loops[li]
                co = me.vertices[loop.vertex_index].co
                n = corner[li] if corner[li].length > 1e-6 else lt.normal
                u = uv[li].uv
                t = loop.tangent.copy()
                b = loop.bitangent_sign * n.cross(t)
                key = (tuple(round(c, 4) for c in co), tuple(round(c, 3) for c in n), (round(u[0], 4), round(u[1], 4)),
                       tuple(round(c, 3) for c in t), round(loop.bitangent_sign))
                if key not in index:
                    index[key] = len(verts)
                    verts.append(tuple(co))
                    normals.append(tuple(n))
                    tangents.append(tuple(t))
                    binormals.append(tuple(b))
                    uvs.append((u[0], u[1]))
                tri.append(index[key])
            tris.append(tri)
        me.free_tangents()
        out[name] = dict(origin=tuple(ob.location), vertices=verts, normals=normals, uvs=uvs, triangles=tris,
                         tangents=tangents, binormals=binormals)
    out['_pivots'] = pivots
    with open(os.path.join(out_dir, 'parts.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f)
    print('export:', {k: len(v['triangles']) for k, v in out.items() if not k.startswith('_')})


def renders(lows, mat, out_dir, size):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [
        e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new('w')
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.8, 0.8, 0.8, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.8
    sc.world = w
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(40), 0, math.radians(40))
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    target = Vector((0, 0, 8))
    # icon: the camera off the front-right, so the nose points to the lower left as on the retail Guardian button
    for name, az, el, transparent in (('preview.png', 35, 35, False), ('icon.png', 30, 40, True),
                                      ('preview_top.png', -90, 89, False)):
        a, e = math.radians(az), math.radians(el)
        dist = size * 3.6
        cam.location = target + Vector((dist * math.cos(e) * math.cos(a), dist * math.cos(e) * math.sin(a),
                                        dist * math.sin(e)))
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = 50
        sc.render.film_transparent = transparent
        sc.render.resolution_x = sc.render.resolution_y = 512
        sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
        sc.render.filepath = os.path.join(out_dir, name)
        bpy.ops.render.render(write_still=True)


def main(unit):
    cfg = UNITS[unit]
    out_dir = os.path.join(WORK, 'units', unit, 'game')
    os.makedirs(out_dir, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    parts = import_parts(os.path.join(WORK, cfg['glb']))
    picked = {g: [parts[i] for i in cfg[g]] for g in ('TURRET', 'BARREL')}
    used = {i for g in ('TURRET', 'BARREL') for i in cfg[g]}
    picked['HULL'] = [o for i, o in sorted(parts.items()) if i not in used]
    # scale and place: width over everything, hull centred in x / y, ground at 0
    lo_all, hi_all = bbox(list(parts.values()))
    s = cfg['width'] / (hi_all.y - lo_all.y)
    hl, hh = bbox(picked['HULL'])
    shift = Vector((-(hl.x + hh.x) / 2, -(lo_all.y + hi_all.y) / 2, -lo_all.z))
    for o in parts.values():
        o.data.transform(Matrix.Translation(shift))
        o.data.transform(Matrix.Scale(s, 4))
    his = {g: join(obs, 'HI_' + g) for g, obs in picked.items()}
    tl, th = bbox([his['TURRET']])
    bl, bh = bbox([his['BARREL']])
    turret_at = Vector(((tl.x + th.x) / 2, 0, tl.z))
    pitch_at = Vector((bl.x, 0, (bl.z + bh.z) / 2))
    muzzle_at = Vector((bh.x, 0, (bl.z + bh.z) / 2))
    weld = 1e-4 * cfg['width']
    lows = {g: low_copy(his[g], g, cfg['budget'][g], weld) for g in ('HULL', 'TURRET', 'BARREL')}
    uv_atlas(list(lows.values()))
    name = cfg['model']
    images, mat = bake([(his[g], lows[g]) for g in ('HULL', 'TURRET', 'BARREL')], cfg['tex'], out_dir, name)
    team_mask(os.path.join(out_dir, name + '.png'), os.path.join(out_dir, name + '_mask.png'))
    for o in his.values():
        bpy.data.objects.remove(o)
    set_origin(lows['TURRET'], turret_at)
    set_origin(lows['BARREL'], pitch_at)
    hl, hh = bbox([lows['HULL']])
    tr = cfg['width'] / 2 - 1.5
    # the Guardian's bone names (make_campnew23.PIVOTS), placed on this model; (name, parent, offset from parent)
    pv = [('BODY', None, (0, 0, 0)),
          ('Bone_Turret', None, tuple(turret_at)), ('Bone_Turret_Pitch', 'Bone_Turret', tuple(pitch_at - turret_at)),
          ('BONE_GUN_MUZZLE', 'Bone_Turret_Pitch', tuple(muzzle_at - pitch_at)),
          ('FXBone_Muzzle', 'Bone_Turret_Pitch', tuple(muzzle_at - pitch_at + Vector((0.7, 0, 0)))),
          ('FX_Laser', 'Bone_Turret', (0.0, 0.0, th.z - tl.z)), ('FX_Damage01', None, (0.0, 0.0, hh.z)),
          ('FXTracksL', None, (hl.x, tr, 0)), ('FXTracksR', None, (hl.x, -tr, 0))] + \
         [(f'Bone_{kind}_{fr}_{side}', None, (0.45 * (hh.x if fr == 'Front' else hl.x), tr if side == 'Left' else -tr, 2.4))
          for kind in ('Tread', 'Tracks') for fr in ('Front', 'Rear') for side in ('Left', 'Right')]
    export(lows, pv, out_dir)
    renders(list(lows.values()), mat, out_dir, cfg['width'])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, unit + '.blend'))
    print('done', out_dir)


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1])
