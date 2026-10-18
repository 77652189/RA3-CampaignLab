"""CNV shrink-ray support vehicle (收缩射线车), a rough model to test the Cryocopter / 游隼 combo (user, 2026-10-18:
the first unit polished, the following ones rough to test gameplay). Blender headless:

  "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Blender\\blender.exe" -b --factory-startup -P experimental/units/cnv_shrinkvehicle.py -- <out dir>

A low tracked carrier with a turntable carrying a dish emitter and a projector tube (cyan rings), team colour on
the side skirts and the dish rim. Bake, previews and parts.json from cnv_lighttank.py. Pivots for the game:
turntable (Bone_Turret), dish tilt (Bone_Turret_Pitch), FXWEAPON_01 at the projector tip (the shrink ray's laser
origin, as on the Cryocopter).
"""
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cnv_lighttank as base                       # noqa: E402
from cnv_lighttank2 import STEEL, DARK, GLOW, prism, loft      # noqa: E402

box, cylinder = base.box, base.cylinder


def build(mats):
    parts = {}
    bm = bmesh.new()                                    # hull: low wedge body, side skirts with team strips
    prism(bm, [(-15.0, 3.0), (12.0, 3.0), (15.5, 5.4), (13.0, 7.6), (-13.5, 7.8), (-15.0, 6.6)], -7.6, 7.6)
    for s in (-1, 1):
        y0, y1 = sorted((s * 7.6, s * 11.4))
        prism(bm, [(-15.6, 4.2), (13.4, 4.2), (15.4, 5.6), (12.6, 7.4), (-14.6, 7.4), (-15.8, 6.4)], y0, y1)
        t0, t1 = sorted((s * 11.4, s * 11.75))
        box(bm, -11.0, t0, 5.2, 9.0, t1, 6.6, mat=2)                                            # team strip
    box(bm, -12.0, -4.0, 7.75, -6.0, 4.0, 8.2, mat=1)                                           # engine grille
    box(bm, 15.3, -2.0, 4.6, 15.7, 2.0, 5.2, mat=3)                                             # nose light
    ob = base.obj_from_bm('HULL', bm, mats)
    base.bevel_and_finish(ob, width=0.45, segments=1)
    parts['HULL'] = ob

    bm = bmesh.new()                                    # tracks
    loop = [(-15.0, 1.0), (-13.0, 0.0), (11.8, 0.0), (14.8, 2.2), (15.0, 3.8), (13.4, 5.0), (-14.0, 5.0),
            (-15.9, 3.6)]
    for s in (-1, 1):
        y0, y1 = sorted((s * 7.8, s * 11.2))
        prism(bm, loop, y0, y1, mat=1)
        out = s * 11.5
        for k in range(4):
            cylinder(bm, 'y', (-9.6 + 6.0 * k, out, 2.2), 2.0, 0.6, segments=10, mat=1)
            cylinder(bm, 'y', (-9.6 + 6.0 * k, out + 0.3 * s, 2.2), 0.9, 0.3, segments=8, mat=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    parts['TREADS'] = base.obj_from_bm('TREADS', bm, mats)

    bm = bmesh.new()                                    # turntable (local to Bone_Turret)
    cylinder(bm, 'z', (0, 0, 0.4), 4.6, 0.8, segments=12, mat=1)
    loft(bm, [(4.0, -3.2), (4.0, 3.2), (-4.0, 3.6), (-4.0, -3.6)], 0.8, [(3.0, -2.6), (3.0, 2.6), (-3.4, 3.0),
                                                                        (-3.4, -3.0)], 3.2)
    for s in (-1, 1):
        box(bm, -1.0, 2.8 * s - 0.4, 3.2, 1.6, 2.8 * s + 0.4, 5.4, mat=0)                        # yoke arms
    ob = base.obj_from_bm('TURRET', bm, mats)
    base.bevel_and_finish(ob, width=0.3, segments=1)
    parts['TURRET'] = ob

    bm = bmesh.new()                                    # dish + projector (local to Bone_Turret_Pitch)
    cylinder(bm, 'x', (0.2, 0, 0), 3.6, 0.6, segments=16, mat=0, cap_scale=0.6)                # dish
    cylinder(bm, 'x', (0.55, 0, 0), 3.7, 0.25, segments=16, mat=2)                              # team rim
    cylinder(bm, 'x', (0.7, 0, 0), 2.4, 0.15, segments=16, mat=3)                               # cyan ring
    cylinder(bm, 'x', (3.0, 0, 0), 0.55, 4.6, segments=10, mat=0)                               # projector
    cylinder(bm, 'x', (5.4, 0, 0), 0.8, 0.5, segments=10, mat=3)                                # tip glow
    for a in range(3):                                                                          # struts
        import math
        ang = math.radians(90 + 120 * a)
        box(bm, 0.6, 2.2 * math.cos(ang) - 0.15, 2.2 * math.sin(ang) - 0.15, 4.4,
            0.8 * math.cos(ang) + 0.15, 0.8 * math.sin(ang) + 0.15, mat=1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = base.obj_from_bm('BARREL', bm, mats)
    base.bevel_and_finish(ob, width=0.12, segments=1)
    parts['BARREL'] = ob
    return parts


TURRET_AT = Vector((-1.0, 0.0, 7.8))
PITCH_AT = Vector((0.3, 0.0, 4.6))
TIP_AT = (5.8, 0.0, 0.0)          # in the pitch bone: FXWEAPON_01 / muzzle bones (make_campnew29.py)


def main():
    base.TURRET_AT, base.PITCH_AT = TURRET_AT, PITCH_AT
    sc = base.reset()
    mats = [base.material('steel', STEEL), base.material('dark', DARK), base.material('team', STEEL, team=1.0),
            base.material('glow', GLOW, emit=4.0)]
    parts = build(mats)
    base.place(parts)
    color = base.bake(parts, sc)
    base.textured_materials(color)
    base.previews(sc)
    base.icon(sc)
    base.export(parts)


if __name__ == '__main__':
    main()
