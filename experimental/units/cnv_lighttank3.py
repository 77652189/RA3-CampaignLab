"""CNV light tank v3 (游隼), rebuilt after a second AI concept (work/units/lighttank_ai/concept_v3.png, HunyuanDiT,
prompt "科幻轻型坦克,暗灰金属,层叠斜面装甲,曲面炮塔,..."), in Blender (run headless):

  "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Blender\\blender.exe" -b --factory-startup -P experimental/units/cnv_lighttank3.py -- <out dir>

Why a new shape: zoomed next to the retail Guardian (CampNew25 close-up) v2 read as a boxy light-grey block; the
Guardian's language is two armoured track pods holding a narrower, higher body, layered sloped plates, an
asymmetric turret and team colour on raised parts. The v3 concept has the same structure:
  track pods     big chamfered covers reaching past the tracks, front face sloping down, skirts over the upper
                 road wheels carrying segmented raised team panels, a dark hatch frame and vent slats on top
  nose           a narrower lower wedge pushed forward between the pods: sloped glacis with a grille, cyan light
                 bar on the front face, team strips on its front corners
  turret         wide tall hexagonal turret, mantlet with two lamps, cyan light strips on the flanks, a sight module
                 with its own small gun on top, a sensor arm reaching out to the rear right, antenna
  tracks         exposed front and rear, five big road wheels with cyan hubs
Bake, previews and parts.json come from cnv_lighttank.py; prism / loft from cnv_lighttank2.py.
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
POD_IN, POD_OUT = 7.0, 13.0                        # track pod inner / outer y
TRACK_IN, TRACK_OUT = 7.6, 12.4


def build(mats):
    parts = {}

    # hull: centre body (between the pods, a little below their tops), the nose wedge, the two track pods
    bm = bmesh.new()
    prism(bm, [(-17.6, 3.2), (10.0, 3.2), (12.5, 8.2), (-15.0, 8.6), (-17.6, 8.0)], -POD_IN, POD_IN)   # body
    prism(bm, [(9.0, 3.0), (18.6, 3.4), (19.8, 4.6), (19.8, 6.0), (13.0, 8.2), (9.0, 8.4)], -5.0, 5.0)  # nose
    for s in (-1, 1):
        y0, y1 = (POD_IN, POD_OUT) if s > 0 else (-POD_OUT, -POD_IN)
        prism(bm, [(-18.6, 4.4), (15.8, 4.4), (18.4, 5.6), (18.4, 6.4), (6.0, 9.9), (-16.0, 9.9),
                   (-18.6, 8.6)], y0, y1)                                                        # pod
        out = y1 if s > 0 else y0
        r0, r1 = sorted((s * (POD_OUT - 1.6), s * POD_OUT))
        prism(bm, [(-16.0, 9.9), (6.0, 9.9), (5.0, 10.5), (-15.0, 10.5)], r0, r1)            # raised outer rim
        for x0, x1 in ((-14.5, -3.5), (-2.5, 8.5)):                                               # team skirts
            box(bm, x0, out - 0.3, 5.0, x1, out + 0.3, 7.6, mat=2)
        # raised team plate lying on the pod's front slope, (6, 9.9) -> (18.4, 6.4): from the RTS camera the
        # skirt panels alone hardly showed any team colour (4 % of the texture, all on the sides)
        zs = lambda x: 9.9 - 0.2823 * (x - 6.0)                                        # noqa: E731
        p0, p1 = sorted((s * (POD_IN + 0.9), s * (POD_OUT - 1.9)))
        prism(bm, [(8.0, zs(8.0) - 0.05), (16.0, zs(16.0) - 0.05), (16.0, zs(16.0) + 0.3), (8.0, zs(8.0) + 0.3)],
              p0, p1, mat=2)
        yc = (POD_IN + 1.2) * s
        box(bm, -9.0, yc - 1.1, 9.85, -3.0, yc + 1.1, 10.2, mat=1)                                 # hatch frame
        for k in range(3):                                                                         # vent slats
            box(bm, 1.0 + 1.3 * k, (POD_IN + 2.6) * s - 1.2, 9.85, 1.6 + 1.3 * k, (POD_IN + 2.6) * s + 1.2,
                10.15, mat=1)
    box(bm, 19.7, -1.8, 5.0, 20.0, 1.8, 5.7, mat=3)                                               # nose light
    for s in (-1, 1):
        box(bm, 19.2, 4.3 * s - 0.35, 3.8, 19.95, 4.3 * s + 0.35, 6.0, mat=2)                     # nose strips
    for k in range(4):                                                                             # glacis grille
        zt = 8.2 - 0.324 * (14.65 + 0.9 * k - 13.0)                  # on the glacis line (13, 8.2)-(19.8, 6.0)
        box(bm, 14.4 + 0.9 * k, -2.6, zt - 0.3, 14.9 + 0.9 * k, 2.6, zt + 0.08, mat=1)
    for k in range(5):                                                                             # engine vents
        box(bm, -16.5 + 1.6 * k, -4.0, 8.35, -15.7 + 1.6 * k, 4.0, 8.85, mat=1)
    ob = base.obj_from_bm('HULL', bm, mats)
    base.bevel_and_finish(ob, width=0.55)
    parts['HULL'] = ob

    # tracks: rounded loops, top-run cleats, five big road wheels with cyan hubs, drive sprocket, idler
    bm = bmesh.new()
    loop = [(-17.6, 1.2), (-15.4, 0.0), (14.0, 0.0), (17.6, 2.6), (17.8, 4.4), (16.0, 6.0), (-16.6, 6.0),
            (-18.8, 4.2)]
    for s in (-1, 1):
        y0, y1 = (TRACK_IN, TRACK_OUT) if s > 0 else (-TRACK_OUT, -TRACK_IN)
        prism(bm, loop, y0, y1, mat=1)
        for k in range(12):
            x = -15.5 + 2.7 * k
            box(bm, x, y0 - 0.15, 5.8, x + 1.2, y1 + 0.15, 6.3, mat=1)
        out = y1 + 0.3 if s > 0 else y0 - 0.3
        for k in range(5):
            x = -11.6 + 5.6 * k
            cylinder(bm, 'y', (x, out, 2.5), 2.3, 0.6, segments=10, mat=1)
            cylinder(bm, 'y', (x, out + 0.35 * s, 2.5), 1.0, 0.3, segments=8, mat=0)               # hub cap
        cylinder(bm, 'y', (15.6, out, 3.4), 1.7, 0.6, segments=10, mat=0)                          # sprocket
        cylinder(bm, 'y', (-16.4, out, 3.2), 1.5, 0.6, segments=10, mat=0)                         # idler
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = base.obj_from_bm('TREADS', bm, mats)
    parts['TREADS'] = ob

    # turret (local to the ring): wide low hexagon, mantlet with lamps, cyan flank strips, rear bustle
    bm = bmesh.new()
    loft(bm, [(7.6, -3.0), (7.6, 3.0), (3.6, 7.2), (-7.6, 7.2), (-10.2, 4.6), (-10.2, -4.6), (-7.6, -7.2),
              (3.6, -7.2)], 0.0,
         [(5.8, -2.4), (5.8, 2.4), (2.8, 6.0), (-6.8, 6.0), (-9.0, 3.8), (-9.0, -3.8), (-6.8, -6.0),
          (2.8, -6.0)], 4.6)
    box(bm, 6.4, -3.0, 0.4, 9.6, 3.0, 3.8, mat=0, taper_front=0.6)                                # mantlet
    for s in (-1, 1):
        cylinder(bm, 'x', (9.62, 2.2 * s, 2.9), 0.4, 0.2, segments=8, mat=3)                    # lamps
        box(bm, -4.2, 6.6 * s - 0.25, 2.0, 1.8, 6.6 * s + 0.25, 2.6, mat=3)                      # cyan strip
        box(bm, -7.2, 6.75 * s - 0.35, 0.4, -1.0, 6.75 * s + 0.35, 1.3, mat=2)                   # team plate
    box(bm, 2.4, -2.1, 4.55, 5.4, 2.1, 4.85, mat=2, taper_front=0.4)                             # team top plate
    box(bm, -12.4, -4.0, 0.6, -10.0, 4.0, 3.6, mat=0, taper_top=0.5)                              # bustle
    ob = base.obj_from_bm('TURRET', bm, mats)
    base.bevel_and_finish(ob, width=0.4)
    parts['TURRET'] = ob

    # barrel (origin = pitch pivot in the mantlet): thick sleeve, tube, muzzle
    bm = bmesh.new()
    cylinder(bm, 'x', (3.0, 0, 0), 1.25, 5.0, segments=10, mat=0)
    cylinder(bm, 'x', (10.5, 0, 0), 0.75, 12.0, segments=10, mat=0)
    cylinder(bm, 'x', (16.6, 0, 0), 1.05, 2.0, segments=10, mat=1)
    ob = base.obj_from_bm('BARREL', bm, mats)
    base.bevel_and_finish(ob, width=0.2, segments=1)
    parts['BARREL'] = ob
    details(parts, mats)
    return parts


def details(parts, mats):
    """Small parts with a light bevel on their parents' bones."""
    bm = bmesh.new()                                    # hull: tow hooks, exhausts, mud flaps
    for s in (-1, 1):
        box(bm, 19.0, 2.8 * s - 0.5, 3.4, 20.2, 2.8 * s + 0.5, 4.2, mat=1)
        cylinder(bm, 'z', (-17.0, 5.0 * s, 9.4), 0.5, 1.8, segments=8, mat=0)
        cylinder(bm, 'z', (-17.0, 5.0 * s, 10.35), 0.42, 0.12, segments=8, mat=1)
        f0, f1 = sorted((s * (POD_OUT - 3.8), s * POD_OUT))
        box(bm, -19.0, f0, 3.6, -18.6, f1, 5.0, mat=1)                                           # mud flap
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = base.obj_from_bm('HULL_D', bm, mats)
    base.bevel_and_finish(ob, width=0.1, segments=1)
    parts['HULL_D'] = ob

    bm = bmesh.new()                                    # turret top: sight module with a small gun, cupola, arm
    box(bm, -4.4, -2.2, 4.6, 2.0, 2.2, 5.2, mat=0)
    box(bm, -3.8, -1.7, 5.2, 1.6, 1.7, 7.2, mat=0, taper_front=0.8, taper_top=0.3)
    box(bm, 0.9, -1.2, 6.0, 1.75, 1.2, 6.6, mat=1)                                               # sight window
    cylinder(bm, 'x', (3.6, 0.9, 6.7), 0.28, 4.2, segments=6, mat=0)                            # coax gun
    cylinder(bm, 'z', (-6.0, 3.6, 4.85), 1.3, 0.5, segments=10, mat=0)                           # cupola
    box(bm, -11.6, -8.6, 2.8, -7.4, -6.8, 3.4, mat=0)                                            # sensor arm
    box(bm, -12.4, -9.6, 2.4, -10.4, -7.0, 4.4, mat=0)                                           # sensor head
    box(bm, -10.45, -9.2, 3.1, -10.25, -7.4, 3.7, mat=3)                                         # sensor lens
    box(bm, -11.6, -8.5, 4.4, -11.3, -8.2, 9.2, mat=1)                                           # antenna
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = base.obj_from_bm('TURRET_D', bm, mats)
    base.bevel_and_finish(ob, width=0.1, segments=1)
    parts['TURRET_D'] = ob


TURRET_AT = Vector((0.5, 0.0, 8.6))
PITCH_AT = Vector((8.4, 0.0, 2.1))
MUZZLE_AT = (17.6, 0.0, 0.0)        # in the pitch bone; make_campnew25.py places BONE_GUN_MUZZLE here


def main():
    base.TURRET_AT, base.PITCH_AT = TURRET_AT, PITCH_AT
    sc = base.reset()
    mats = [base.material('steel', STEEL), base.material('dark', DARK), base.material('team', STEEL, team=1.0),
            base.material('glow', GLOW, emit=4.0)]
    parts = build(mats)
    base.place(parts)
    parts['TURRET_D'].location = TURRET_AT
    color = base.bake(parts, sc)
    base.textured_materials(color)
    base.previews(sc)
    base.icon(sc)
    base.export(parts)


if __name__ == '__main__':
    main()
