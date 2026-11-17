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
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'campaign')))
import labpaths  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = labpaths.WORK

# unit: Tripo GLB (under work/), width over the tracks (game units), part indices per group (the rest is HULL),
# triangle budgets, atlas size, the model / texture name
UNITS = {
    'chronolag': dict(glb='units/chronolag/tripo/chronolag_v2_hd.glb', width=25.3,
                      TURRET=[0, 8, 15, 16, 18], BARREL=[5],
                      budget=dict(HULL=2500, TURRET=1100, BARREL=400), tex=1024, model='CNChrono'),
    # Soviet, the first two through faction_grade (2026-11-15). Turret / barrel are look-test guesses (the hook tank's
    # winch drum and boom, the burrower's hatch and drill): neither turns yet, the mechanics are the levels line's
    'hooktank': dict(glb='units/hooktank/tripo/hooktank_v1.glb', width=30, TURRET=[1], BARREL=[3],
                     budget=dict(HULL=3000, TURRET=600, BARREL=400), tex=1024, model='CNHook'),
    'burrower': dict(glb='units/burrower/tripo/burrower_v1.glb', width=24, TURRET=[4], BARREL=[1],
                     budget=dict(HULL=3000, TURRET=400, BARREL=600), tex=1024, model='CNBurrow'),
    # a map prop (prop_main): one piece, width = its larger side on the ground; no team colour, no bones
    'icesculpture': dict(glb='units/icesculpture/tripo/icesculpture_v1.glb', kind='prop', width=38,
                         budget=dict(PROP=1600), tex=512, model='CNIceSculpt'),
    # a flying platform (platform_main): one piece with team colour and the bones its XML names; width 400 is a
    # first guess (the deck jump's radius is 150; the final size is the levels line's call)
    'libertyisle': dict(glb='units/libertyisle/tripo/libertyisle_v1.glb', kind='platform', width=400,
                        budget=dict(BODY=12000), tex=2048, model='CNLiberty'),
    # 时滞炮车 deployed (split_main; user 2026-11-17 "可以，用这版，交给单位线"): the Hunyuan model the Tripo line cut
    # into Hull + Turret (work/units/tripo_batch/split_turret.py), the Turret's origin on its yaw axis; barrel to -Y
    # at a fixed ~25 deg (yaw only). Same width over the tracks as the packed chronolag, its yaw axis put on the
    # packed model's Bone_Turret so the gun pivot stays where it was when the model switches. Team colour by the
    # three reserved panels (user rule 2026-11-16, docs/units/tripo-plan.md): (object, glTF-space box) -- the plates
    # on the two track pods and the octagon on the turret roof, located by probe (blue, facing up) on 2026-11-17
    'chronolag_dep': dict(glb='units/chronolag_dep/split/chronolag_dep_hy1_split.glb', kind='split', width=25.3,
                          HULL='Hull', TURRET='Turret', axis=(0.0, -0.02, 0.24), align='chronolag',
                          panels=[('Hull', (-0.205, -0.315, 0.06), (-0.085, -0.185, 0.175)),
                                  ('Hull', (0.083, -0.315, 0.12), (0.17, -0.185, 0.175)),
                                  ('Turret', (-0.075, -0.035, 0.22), (0.078, 0.118, 0.275))],
                          budget=dict(HULL=4000, TURRET=1200), tex=1024, model='CNChronoDep'),
}
SHARP = math.radians(35)


def import_parts(path):
    bpy.ops.import_scene.gltf(filepath=path)
    parts = {}
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    named = all(o.name.startswith('tripo_part_') for o in meshes)     # generated without parts: other names
    for k, o in enumerate(meshes):
        o.data.transform(o.matrix_world)
        o.parent = None
        o.matrix_world.identity()
        parts[int(o.name.rsplit('_', 1)[1]) if named else k] = o
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


def renders(lows, mat, out_dir, size, height=8):
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
    target = Vector((0, 0, height))
    # icon: the camera off the front-right, so the nose points to the lower left as on the retail Guardian button
    for name, az, el, transparent in (('preview.png', 35, 35, False), ('icon.png', 30, 40, True),
                                      ('preview_top.png', -90, 89, False)):
        a, e = math.radians(az), math.radians(el)
        dist = size * 3.6
        cam.location = target + Vector((dist * math.cos(e) * math.cos(a), dist * math.cos(e) * math.sin(a),
                                        dist * math.sin(e)))
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = 50
        cam.data.clip_end = dist * 3            # the default 100 clips a platform hundreds of units across
        sc.render.film_transparent = transparent
        sc.render.resolution_x = sc.render.resolution_y = 512
        sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
        sc.render.filepath = os.path.join(out_dir, name)
        bpy.ops.render.render(write_still=True)


def prop_main(unit, cfg, out_dir):
    """A map prop: every part one piece, its larger side on the ground `width`, centred, ground at 0; collapsed to
    its budget, baked (colour, tangent normals), exported as one part PROP with no pivots (ice_kit.prop writes it)."""
    parts = import_parts(os.path.join(WORK, cfg['glb']))
    lo_all, hi_all = bbox(list(parts.values()))
    s = cfg['width'] / max(hi_all.x - lo_all.x, hi_all.y - lo_all.y)
    shift = Vector((-(lo_all.x + hi_all.x) / 2, -(lo_all.y + hi_all.y) / 2, -lo_all.z))
    for o in parts.values():
        o.data.transform(Matrix.Translation(shift))
        o.data.transform(Matrix.Scale(s, 4))
    hi = join(list(parts.values()), 'HI_PROP')
    lo = low_copy(hi, 'PROP', cfg['budget']['PROP'], 1e-4 * cfg['width'])
    uv_atlas([lo])
    images, mat = bake([(hi, lo)], cfg['tex'], out_dir, cfg['model'])
    height = hi.dimensions.z
    bpy.data.objects.remove(hi)
    export({'PROP': lo}, [], out_dir)
    renders([lo], mat, out_dir, cfg['width'], height=height / 2)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, unit + '.blend'))
    print('done', out_dir, f'height {height:.1f}')


def platform_main(unit, cfg, out_dir):
    """A flying platform (the Liberty): one piece BODY, `width` across, centred, its lowest point at z = 0 (the
    locomotor sets the hover height); collapsed, baked, team mask from the blue paint; pivots for the bones the
    Kirov-based XML names (liberty.py) plus STATUE, the top of the core where the retail statue stands."""
    parts = import_parts(os.path.join(WORK, cfg['glb']))
    lo_all, hi_all = bbox(list(parts.values()))
    s = cfg['width'] / max(hi_all.x - lo_all.x, hi_all.y - lo_all.y)
    shift = Vector((-(lo_all.x + hi_all.x) / 2, -(lo_all.y + hi_all.y) / 2, -lo_all.z))
    for o in parts.values():
        o.data.transform(Matrix.Translation(shift))
        o.data.transform(Matrix.Scale(s, 4))
    hi = join(list(parts.values()), 'HI_BODY')
    lo = low_copy(hi, 'BODY', cfg['budget']['BODY'], 1e-4 * cfg['width'])
    uv_atlas([lo])
    name = cfg['model']
    images, mat = bake([(hi, lo)], cfg['tex'], out_dir, name)
    team_mask(os.path.join(out_dir, name + '.png'), os.path.join(out_dir, name + '_mask.png'))
    # the core's top: the highest vertex near the centre
    r = 0.08 * cfg['width']
    top = max((v.co.z for v in hi.data.vertices if v.co.x * v.co.x + v.co.y * v.co.y < r * r), default=hi.dimensions.z)
    height = hi.dimensions.z
    bpy.data.objects.remove(hi)
    w = cfg['width'] / 2
    pv = [('BODY', None, (0, 0, 0)), ('STATUE', None, (0.0, 0.0, top)),
          ('B_Bombs', None, (0.0, 0.0, 0.0)), ('FX_WEAPON', None, (0.0, 0.0, 0.0)),
          ('B_Prop05', None, (0.0, 0.0, 0.3 * height)),
          ('FX_Fire_02', None, (0.3 * w, 0.5 * w, 0.4 * height)), ('FX_Fire_03', None, (-0.4 * w, -0.4 * w, 0.4 * height))]
    export({'BODY': lo}, pv, out_dir)
    renders([lo], mat, out_dir, cfg['width'], height=height / 2)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, unit + '.blend'))
    print('done', out_dir, f'height {height:.1f}, core top {top:.1f}')


PANEL_UP, PANEL_LIFT = 0.6, 8      # a panel face looks up and is at least faintly blue (drops the grey rim in its box)


def mark_panels(ob, boxes):
    """Team colour by reserved panels (user rule 2026-11-16), not by how blue the bake is: the faces of `ob` inside one
    of `boxes` (min, max in the object's current space), facing up and faintly blue in its own texture -- the box
    bounds the area, so a texture the generator darkened or brightened cannot shrink or spread it. Kept as the FACE
    attribute 'team' (survives join and transforms); returns the faces marked."""
    me = ob.data
    n = len(me.polygons)
    cen, nrm = np.zeros(n * 3), np.zeros(n * 3)
    me.polygons.foreach_get('center', cen)
    me.polygons.foreach_get('normal', nrm)
    cen, nrm = cen.reshape(n, 3), nrm.reshape(n, 3)
    inside = np.zeros(n, bool)
    for lo, hi in boxes:
        inside |= np.all((cen >= lo) & (cen <= hi), axis=1)
    sel = inside & (nrm[:, 2] > PANEL_UP)
    img = next(nd.image for m in me.materials if m and m.use_nodes for nd in m.node_tree.nodes
               if nd.type == 'TEX_IMAGE' and nd.image and nd.image.colorspace_settings.name == 'sRGB')
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[..., :3] * 255
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers.active.data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2)
    start, total = np.zeros(n, int), np.zeros(n, int)
    me.polygons.foreach_get('loop_start', start)
    me.polygons.foreach_get('loop_total', total)
    owner = np.repeat(np.arange(n), total)
    u = np.zeros((n, 2))
    np.add.at(u, owner, uv[np.concatenate([np.arange(s, s + t) for s, t in zip(start, total)])])
    u /= total[:, None]
    c = px[np.clip((u[:, 1] % 1) * h, 0, h - 1).astype(int), np.clip((u[:, 0] % 1) * w, 0, w - 1).astype(int)]
    sel &= (c[:, 2] - np.maximum(c[:, 0], c[:, 1])) > PANEL_LIFT
    att = me.attributes.new('team', 'INT', 'FACE')
    att.data.foreach_set('value', sel.astype(int))
    print(f'panels on {ob.name}: {int(sel.sum())} faces in {len(boxes)} boxes')
    return int(sel.sum())


def panel_mask(groups, size, out_png):
    """Bake the 'team' face attribute of the high parts onto the low atlas (emission white / black) -> <model>_mask.png,
    the file to_w3x reads for the team colour."""
    sc = bpy.context.scene
    sc.render.bake.target = 'IMAGE_TEXTURES'
    img = bpy.data.images.new('mask', size, size, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    mats = []
    for v in (0.0, 1.0):
        m = bpy.data.materials.new(f'team{int(v)}')
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.remove(nt.nodes['Principled BSDF'])
        e = nt.nodes.new('ShaderNodeEmission')
        e.inputs['Color'].default_value = (v, v, v, 1)
        nt.links.new(e.outputs['Emission'], nt.nodes['Material Output'].inputs['Surface'])
        mats.append(m)
    lm = bpy.data.materials.new('mask_target')
    lm.use_nodes = True
    tex = lm.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = img
    lm.node_tree.nodes.active = tex
    for k, (hi, lo) in enumerate(groups):
        me = hi.data.copy()
        tmp = bpy.data.objects.new(hi.name + '_team', me)
        sc.collection.objects.link(tmp)
        me.materials.clear()
        for m in mats:
            me.materials.append(m)
        vals = np.zeros(len(me.polygons), int)
        if 'team' in me.attributes:
            me.attributes['team'].data.foreach_get('value', vals)
        me.polygons.foreach_set('material_index', vals)
        saved = list(lo.data.materials)
        lo.data.materials.clear()
        lo.data.materials.append(lm)
        bpy.ops.object.select_all(action='DESELECT')
        tmp.select_set(True)
        lo.select_set(True)
        bpy.context.view_layer.objects.active = lo
        size_ = max(lo.dimensions)
        sc.render.bake.cage_extrusion = 0.02 * size_
        sc.render.bake.max_ray_distance = 0.06 * size_
        bpy.ops.object.bake(type='EMIT', use_clear=(k == 0))
        lo.data.materials.clear()
        for m in saved:
            lo.data.materials.append(m)
        bpy.data.objects.remove(tmp)
    img.filepath_raw = out_png
    img.file_format = 'PNG'
    img.save()
    m = np.array(img.pixels[:], dtype=np.float32).reshape(size, size, 4)[..., 0]
    print(f'team mask (panels): {(m > 0.5).mean():.3f} of the atlas')


def split_main(unit, cfg, out_dir):
    """A model already cut into named objects (HULL / TURRET, the turret's origin on its yaw axis): team panels marked
    in glTF space, then turned +X forward (the barrel points to -Y), scaled to the width over the tracks (the hull's
    x extent), its yaw axis put on the `align` unit's Bone_Turret (from that unit's parts.json) and the ground at 0;
    collapsed, baked, the panel mask baked; bones as main()'s with no pitch part (the barrel's elevation is fixed: the
    pitch bone sits on the yaw axis, the muzzle bones at the barrel's tip)."""
    bpy.ops.import_scene.gltf(filepath=os.path.join(WORK, cfg['glb']))
    obs = {o.name: o for o in bpy.context.scene.objects if o.type == 'MESH'}
    for o in obs.values():
        o.data.transform(o.matrix_world)
        o.parent = None
        o.matrix_world.identity()
    for o in list(bpy.context.scene.objects):
        if o.type != 'MESH':
            bpy.data.objects.remove(o)
    his = {g: obs[cfg[g]] for g in ('HULL', 'TURRET')}
    for g, ob in his.items():
        mark_panels(ob, [(Vector(lo), Vector(hi)) for name, lo, hi in cfg['panels'] if name == ob.name])
    for g, ob in his.items():
        ob.name = ob.data.name = 'HI_' + g
    axis = Vector(cfg['axis'])
    hl, hh = bbox([his['HULL']])
    s = cfg['width'] / (hh.x - hl.x)
    with open(os.path.join(WORK, 'units', cfg['align'], 'game', 'parts.json'), encoding='utf-8') as f:
        at = dict((n, a) for n, p, a in json.load(f)['_pivots'])['Bone_Turret']
    move = (Matrix.Translation(Vector((at[0], at[1], 0))) @ Matrix.Scale(s, 4) @ Matrix.Rotation(math.pi / 2, 4, 'Z')
            @ Matrix.Translation(Vector((-axis.x, -axis.y, 0))))
    for ob in his.values():
        ob.data.transform(move)
    lo_all, _ = bbox(list(his.values()))
    for ob in his.values():
        ob.data.transform(Matrix.Translation(Vector((0, 0, -lo_all.z))))
    turret_at = Vector((at[0], at[1], axis.z * s - lo_all.z))
    weld = 1e-4 * cfg['width']
    lows = {g: low_copy(his[g], g, cfg['budget'][g], weld) for g in ('HULL', 'TURRET')}
    uv_atlas(list(lows.values()))
    name = cfg['model']
    groups = [(his[g], lows[g]) for g in ('HULL', 'TURRET')]
    images, mat = bake(groups, cfg['tex'], out_dir, name)
    panel_mask(groups, cfg['tex'], os.path.join(out_dir, name + '_mask.png'))
    tv = np.array([v.co[:] for v in his['TURRET'].data.vertices])
    tip = tv[tv[:, 0] > tv[:, 0].max() - 0.04 * cfg['width']]
    muzzle_at = Vector((tv[:, 0].max(), tip[:, 1].mean(), tip[:, 2].mean()))
    for o in his.values():
        bpy.data.objects.remove(o)
    set_origin(lows['TURRET'], turret_at)
    hl, hh = bbox([lows['HULL']])
    th = bbox([lows['TURRET']])[1]
    tr = cfg['width'] / 2 - 1.5
    pv = [('BODY', None, (0, 0, 0)),
          ('Bone_Turret', None, tuple(turret_at)), ('Bone_Turret_Pitch', 'Bone_Turret', (0.0, 0.0, 0.0)),
          ('BONE_GUN_MUZZLE', 'Bone_Turret_Pitch', tuple(muzzle_at - turret_at)),
          ('FXBone_Muzzle', 'Bone_Turret_Pitch', tuple(muzzle_at - turret_at + Vector((0.7, 0, 0)))),
          ('FX_Laser', 'Bone_Turret', (0.0, 0.0, th.z - turret_at.z)), ('FX_Damage01', None, (0.0, 0.0, hh.z)),
          ('FXTracksL', None, (hl.x, tr, 0)), ('FXTracksR', None, (hl.x, -tr, 0))] + \
         [(f'Bone_{kind}_{fr}_{side}', None, (0.45 * (hh.x if fr == 'Front' else hl.x), tr if side == 'Left' else -tr, 2.4))
          for kind in ('Tread', 'Tracks') for fr in ('Front', 'Rear') for side in ('Left', 'Right')]
    export(lows, pv, out_dir)
    renders(list(lows.values()), mat, out_dir, cfg['width'])
    lows['TURRET'].rotation_euler.z = math.radians(60)          # the gun turned: the hull below it, the panel with it
    sc = bpy.context.scene
    sc.render.film_transparent = False
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.filepath = os.path.join(out_dir, 'preview_rot60.png')
    cam = sc.camera
    a, e, dist = math.radians(35), math.radians(35), cfg['width'] * 3.6
    cam.location = Vector((0, 0, 8)) + Vector((dist * math.cos(e) * math.cos(a), dist * math.cos(e) * math.sin(a),
                                               dist * math.sin(e)))
    cam.rotation_euler = (Vector((0, 0, 8)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.render.render(write_still=True)
    lows['TURRET'].rotation_euler.z = 0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, unit + '.blend'))
    print('done', out_dir, f'scale {s:.1f}, turret at {tuple(round(c, 2) for c in turret_at)}, '
                           f'muzzle at {tuple(round(c, 2) for c in muzzle_at)}')


def main(unit):
    cfg = UNITS[unit]
    out_dir = os.path.join(WORK, 'units', unit, 'game')
    os.makedirs(out_dir, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if cfg.get('kind') == 'prop':
        return prop_main(unit, cfg, out_dir)
    if cfg.get('kind') == 'platform':
        return platform_main(unit, cfg, out_dir)
    if cfg.get('kind') == 'split':
        return split_main(unit, cfg, out_dir)
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
