"""帝国「鸣神」突击机甲 (暂名), rough model in its two forms (user, 2026-10-18: units after 游隼 rough first, to test
gameplay). Blender headless, one run per form:

  "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Blender\\blender.exe" -b --factory-startup -P experimental/units/cnv_narukami.py -- <out dir> fast|signal

疾行形态 (fast): a low arrowhead hover sled on two hover pods (cyan thrusters underneath), swept tail fins, a small
turret with twin short barrels. 信号形态 (signal): the same sled with the fins swung up as side panels and a tall
antenna mast with crossbars and a glowing tip -- the game swaps the whole model on the deploy (USER_1 model
condition), so both forms share the part names and pivots (HULL / TREADS on the body, TURRET, BARREL).
"""
import math
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cnv_lighttank as base                       # noqa: E402
from cnv_lighttank2 import STEEL, DARK, GLOW, prism, loft      # noqa: E402

box, cylinder = base.box, base.cylinder
FORM = sys.argv[sys.argv.index('--') + 2] if '--' in sys.argv and len(sys.argv) > sys.argv.index('--') + 2 \
    else 'fast'


def build(mats, signal):
    parts = {}
    bm = bmesh.new()                                    # hull: arrowhead sled, raised spine, team strips
    prism(bm, [(-14.0, 3.4), (8.0, 3.4), (17.0, 4.6), (16.0, 6.0), (6.0, 8.0), (-12.0, 8.2), (-14.5, 6.6)],
          -6.4, 6.4)
    loft(bm, [(8.0, -2.6), (8.0, 2.6), (-10.0, 3.2), (-10.0, -3.2)], 8.0,
         [(5.0, -1.6), (5.0, 1.6), (-8.0, 2.0), (-8.0, -2.0)], 9.6)                             # spine
    for s in (-1, 1):
        t0, t1 = sorted((s * 6.4, s * 6.75))
        box(bm, -9.0, t0, 5.0, 10.0, t1, 6.6, mat=2)                                            # team strip
        box(bm, 14.0, s * 2.2 - 0.6, 4.4, 16.6, s * 2.2 + 0.6, 5.0, mat=3)                      # nose lights
    if signal:                                          # fins up as side panels, antenna mast with crossbars
        for s in (-1, 1):
            y0, y1 = sorted((s * 6.8, s * 7.4))
            prism(bm, [(-13.0, 7.0), (-4.0, 7.0), (-6.0, 17.0), (-11.0, 18.5)], y0, y1)
            box(bm, -11.5, y0 - 0.05, 12.0, -6.5, y1 + 0.05, 14.0, mat=2)                       # panel team band
        cylinder(bm, 'z', (-4.0, 0.0, 19.0), 0.8, 20.0, segments=10, mat=1)                    # mast
        for k, w in enumerate((5.0, 3.6, 2.4)):
            box(bm, -4.4, -w, 16.0 + 6.0 * k, -3.6, w, 16.6 + 6.0 * k, mat=0)                  # crossbars
            for s in (-1, 1):
                box(bm, -4.5, s * w - 0.4, 15.6 + 6.0 * k, -3.5, s * w + 0.4, 17.0 + 6.0 * k, mat=3)
        cylinder(bm, 'z', (-4.0, 0.0, 29.6), 1.4, 1.4, segments=10, mat=3)                     # glowing tip
    else:                                               # swept tail fins
        for s in (-1, 1):
            y0, y1 = sorted((s * 3.0, s * 3.6))
            prism(bm, [(-14.0, 7.5), (-6.0, 8.0), (-10.0, 12.5), (-14.5, 12.0)], y0, y1)
    ob = base.obj_from_bm('HULL', bm, mats)
    base.bevel_and_finish(ob, width=0.35, segments=1)
    parts['HULL'] = ob

    bm = bmesh.new()                                    # hover pods with cyan thrusters underneath
    for s in (-1, 1):
        y0, y1 = sorted((s * 6.6, s * 11.0))
        prism(bm, [(-13.0, 1.6), (11.0, 1.6), (14.0, 3.6), (11.0, 6.0), (-12.0, 6.0), (-14.0, 3.6)], y0, y1,
              mat=1)
        for k in range(3):
            box(bm, -9.0 + 8.0 * k, s * 8.8 - 1.2, 1.2, -6.0 + 8.0 * k, s * 8.8 + 1.2, 1.6, mat=3)
        box(bm, -14.6, s * 8.8 - 1.4, 2.4, -14.0, s * 8.8 + 1.4, 5.0, mat=3)                    # rear exhaust
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    parts['TREADS'] = base.obj_from_bm('TREADS', bm, mats)

    bm = bmesh.new()                                    # turret (local to Bone_Turret): low faceted dome
    loft(bm, [(4.4, -3.4), (5.4, 0.0), (4.4, 3.4), (-3.6, 3.8), (-4.4, 0.0), (-3.6, -3.8)], 0.0,
         [(2.8, -2.2), (3.6, 0.0), (2.8, 2.2), (-2.6, 2.6), (-3.2, 0.0), (-2.6, -2.6)], 2.8)
    box(bm, -1.0, -0.5, 2.8, 1.6, 0.5, 3.6, mat=3)                                              # sensor
    ob = base.obj_from_bm('TURRET', bm, mats)
    base.bevel_and_finish(ob, width=0.25, segments=1)
    parts['TURRET'] = ob

    bm = bmesh.new()                                    # twin short barrels (local to Bone_Turret_Pitch)
    for s in (-1, 1):
        cylinder(bm, 'x', (3.2, s * 1.1, 0.0), 0.45, 6.4, segments=8, mat=0)
        cylinder(bm, 'x', (6.6, s * 1.1, 0.0), 0.6, 0.8, segments=8, mat=1)
    box(bm, -0.6, -1.8, -0.7, 1.4, 1.8, 0.7, mat=1)                                             # mantlet
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = base.obj_from_bm('BARREL', bm, mats)
    base.bevel_and_finish(ob, width=0.1, segments=1)
    parts['BARREL'] = ob
    return parts


TURRET_AT = Vector((3.0, 0.0, 8.0))
PITCH_AT = Vector((2.4, 0.0, 1.6))
TIP_AT = (7.0, 0.0, 0.0)          # in the pitch bone: muzzle bones (make_campnew32.py)


def main():
    base.TURRET_AT, base.PITCH_AT = TURRET_AT, PITCH_AT
    sc = base.reset()
    mats = [base.material('steel', STEEL), base.material('dark', DARK), base.material('team', STEEL, team=1.0),
            base.material('glow', GLOW, emit=4.0)]
    parts = build(mats, FORM == 'signal')
    base.place(parts)
    color = base.bake(parts, sc)
    base.textured_materials(color)
    base.previews(sc)
    base.icon(sc)
    base.export(parts)
    print('narukami form', FORM, '->', base.OUT)


if __name__ == '__main__':
    main()
