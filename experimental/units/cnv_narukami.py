"""帝国「鸣神」(Raijin) rough model in its two forms, Blender headless, one run per form:

  "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Blender\\blender.exe" -b --factory-startup -P experimental/units/cnv_narukami.py -- <out dir> fast|signal

v2 after the user's note (2026-10-19: Empire mechs have distinctive shapes -- Tengu jet / mech, Striker-VX
helicopter / walker, King Oni humanoid -- a plain tank does not fit). Theme: the thunder god with his ring of taiko
drums; AI concepts work/units/lighttank_ai/narukami_fast/concept_0.png (hover body, big side drum-turbines) and
narukami_signal/concept_0.png (horned humanoid in front of a ring). Look matched to a bench line-up of retail Empire
units (work/testbench/cnv32/lineup/011s.png): bright off-white armour, large team-colour areas, red accents, cyan
glows, rounded forms.

疾行形态 (fast): a hover ring with six red taiko drums, a white teardrop cockpit pod with a dark canopy, two big
team-coloured side drum-turbines with glowing faces, a small dome turret with twin barrels; glow pads underneath.
信号形态 (signal): the same ring; a humanoid upper body rises from it (team-coloured chest, red flared pauldrons,
arms spread), a horned kabuto head (the turret), and an upright halo ring with eight drums with glowing faces behind
the back -- the drums' sound is the signal zone. Both forms: parts HULL / TREADS (body), TURRET, BARREL (pitch).
Turret pivots differ per form (TURRET_AT / PITCH_AT per form; make_campnew32.py builds a hierarchy per model).
"""
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cnv_lighttank as base                       # noqa: E402
from cnv_lighttank2 import DARK, GLOW, prism       # noqa: E402

box, cylinder = base.box, base.cylinder
FORM = sys.argv[sys.argv.index('--') + 2] if '--' in sys.argv and len(sys.argv) > sys.argv.index('--') + 2 \
    else 'fast'


def lin(c):
    return tuple(round(((v + 0.055) / 1.055) ** 2.4, 3) for v in c)


WHITE = lin((0.86, 0.87, 0.89))                    # Empire armour (retail line-up: off-white, slightly cool)
RED = lin((0.72, 0.10, 0.08))
STEEL, DK, TEAM, GL, RD = 0, 1, 2, 3, 4            # material slots

BODY = 1.3                         # signal form: the figure (torso, arms, halo, head) scaled about z = 6
TURRET_AT = {'fast': Vector((4.0, 0.0, 10.4)), 'signal': Vector((0.0, 0.0, 6.0 + 18.6 * BODY))}
PITCH_AT = {'fast': Vector((1.0, 0.0, 1.2)), 'signal': Vector((0.4, 0.0, 1.6)) * BODY}
TIP_AT = (8.0, 0.0, 0.0)          # in the pitch bone: muzzle bones (make_campnew32.py)


def _new_faces(bm, fn, mat, smooth=True):
    before = set(bm.faces)
    fn()
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def ellipsoid(bm, center, size, mat, segs=(16, 10)):
    m = Matrix.Translation(center) @ Matrix.Diagonal((*size, 1.0))
    _new_faces(bm, lambda: bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=1.0,
                                                     matrix=m), mat)


def rod(bm, p0, p1, r0, r1, mat, segs=10, smooth=True):
    """A (tapered) cylinder from point p0 to p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    m = Matrix.Translation((p0 + p1) / 2) @ rot
    _new_faces(bm, lambda: bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r0,
                                                 radius2=r1, depth=d.length, matrix=m), mat, smooth)


def torus(bm, center, R, r, mat, axis='z', seg=(28, 8)):
    """A ring of major radius R, tube radius r, around `axis` through center."""
    cx, cy, cz = center
    rings = []
    for i in range(seg[0]):
        a = 2 * math.pi * i / seg[0]
        ring = []
        for j in range(seg[1]):
            b = 2 * math.pi * j / seg[1]
            u, w = (R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a)
            h = r * math.sin(b)
            p = {'z': (cx + u, cy + w, cz + h), 'x': (cx + h, cy + u, cz + w)}[axis]
            ring.append(bm.verts.new(p))
        rings.append(ring)
    for i in range(seg[0]):
        for j in range(seg[1]):
            a, b = rings[i], rings[(i + 1) % seg[0]]
            f = bm.faces.new([a[j], b[j], b[(j + 1) % seg[1]], a[(j + 1) % seg[1]]])
            f.material_index, f.smooth = mat, True


def drum(bm, center, outward, radius, length, body=RD, face=STEEL):
    """A taiko drum: a barrel along `outward` (unit vector) with its two heads (`face`) and a rim of studs."""
    c, o = Vector(center), Vector(outward).normalized()
    rod(bm, c - o * length / 2, c + o * length / 2, radius, radius, body, segs=12)
    for s in (-1, 1):
        rod(bm, c + o * s * length / 2, c + o * s * (length / 2 + 0.25), radius * 0.92, radius * 0.92, face,
            segs=12, smooth=False)


def ring_base(bm):
    torus(bm, (0, 0, 5.0), 11.5, 2.3, STEEL)                                    # hover ring
    torus(bm, (0, 0, 3.4), 11.5, 1.6, DK, seg=(28, 6))                          # gunmetal underside
    torus(bm, (0, 0, 7.0), 11.5, 0.7, TEAM, seg=(28, 6))                        # team band on top
    for k in range(6):                                                          # six drums around the ring
        a = math.radians(30 + 60 * k)
        o = (math.cos(a), math.sin(a), 0.0)
        drum(bm, (11.5 * o[0], 11.5 * o[1], 8.4), o, 1.9, 2.6)
    for s in (-1, 1):                                                           # big side drum-turbines
        rod(bm, (-3.0, s * 12.2, 5.2), (-3.0, s * 17.0, 5.2), 5.0, 4.6, TEAM, segs=16)
        rod(bm, (-3.0, s * 17.0, 5.2), (-3.0, s * 17.4, 5.2), 3.6, 3.6, GL, segs=16, smooth=False)
        rod(bm, (-3.0, s * 11.6, 5.2), (-3.0, s * 12.4, 5.2), 5.3, 5.3, RD, segs=16)   # red rim
    # front prow: a low wedge joining the ring, nose lights
    prism(bm, [(9.0, 3.2), (18.0, 3.6), (19.0, 5.0), (16.0, 6.6), (9.0, 7.2)], -3.0, 3.0, mat=STEEL)
    for s in (-1, 1):
        box(bm, 17.0, s * 1.8 - 0.5, 5.0, 18.8, s * 1.8 + 0.5, 5.8, mat=GL)


def build(mats, signal):
    parts = {}
    bm = bmesh.new()
    ring_base(bm)
    if not signal:
        ellipsoid(bm, (1.0, 0.0, 7.4), (12.5, 6.0, 3.6), STEEL)                 # cockpit pod
        ellipsoid(bm, (6.5, 0.0, 9.0), (4.6, 3.0, 1.9), DK)                     # canopy
        ellipsoid(bm, (-8.0, 0.0, 8.2), (4.0, 4.2, 2.6), TEAM)                  # engine hump
        for s in (-1, 1):
            box(bm, -12.0, s * 2.2 - 0.3, 8.0, -6.0, s * 2.2 + 0.3, 12.5, mat=RD, taper_front=3.0)   # tail fins
    else:
        before = set(bm.verts)
        rod(bm, (0, 0, 6.0), (0, 0, 13.0), 3.6, 2.8, DK)                        # waist
        ellipsoid(bm, (0.0, 0.0, 18.0), (4.4, 6.4, 5.0), TEAM)                  # chest
        ellipsoid(bm, (2.2, 0.0, 18.4), (2.8, 4.6, 3.6), STEEL)                 # chest plate
        torus(bm, (0.0, 0.0, 13.6), 3.4, 0.8, RD, seg=(16, 6))                  # red sash at the waist
        ellipsoid(bm, (4.4, 0.0, 18.6), (0.6, 1.2, 1.2), GL, segs=(8, 6))       # core light
        for s in (-1, 1):
            ellipsoid(bm, (0.0, s * 8.4, 21.4), (3.6, 3.0, 1.4), RD)            # flat sode pauldrons
            ellipsoid(bm, (0.0, s * 8.8, 20.4), (3.4, 2.8, 1.2), STEEL)
            sh, el, ha = (0.0, s * 8.8, 19.6), (1.5, s * 15.0, 15.5), (4.0, s * 20.0, 19.5)
            rod(bm, sh, el, 1.8, 1.5, STEEL)                                    # upper arm
            ellipsoid(bm, el, (1.8, 1.8, 1.8), DK, segs=(10, 6))                # elbow
            rod(bm, el, ha, 1.7, 2.1, TEAM)                                     # forearm
            ellipsoid(bm, ha, (1.9, 1.6, 2.0), STEEL, segs=(10, 6))             # fist
        torus(bm, (-6.0, 0.0, 22.0), 12.5, 1.3, STEEL, axis='x', seg=(24, 6))   # upright halo ring
        for k in range(6):                                                      # six drums with glowing heads
            a = 2 * math.pi * k / 6
            o = (0.0, math.cos(a), math.sin(a))
            drum(bm, (-6.0, 12.5 * o[1], 22.0 + 12.5 * o[2]), (1.0, 0.0, 0.0), 2.8, 2.4, body=RD, face=GL)
        rod(bm, (-1.0, 0.0, 19.0), (-6.0, 0.0, 22.0), 1.0, 1.0, DK)             # halo mount
        # the figure 1.3 x around the ring's centre: at 1.0 it did not read next to the King Oni (bench line-up)
        bmesh.ops.scale(bm, vec=(BODY,) * 3, space=Matrix.Translation((0, 0, -6.0)),
                        verts=list(set(bm.verts) - before))
    ob = base.obj_from_bm('HULL', bm, mats)
    parts['HULL'] = ob

    bm = bmesh.new()                                    # hover glow pads under the ring
    for k in range(6):
        a = math.radians(60 * k)
        rod(bm, (11.5 * math.cos(a), 11.5 * math.sin(a), 2.4), (11.5 * math.cos(a), 11.5 * math.sin(a), 2.8),
            2.0, 2.0, GL, segs=10, smooth=False)
    rod(bm, (1.0, 0.0, 3.0), (1.0, 0.0, 3.6), 4.0, 4.0, GL, segs=14, smooth=False)
    parts['TREADS'] = base.obj_from_bm('TREADS', bm, mats)

    bm = bmesh.new()                                    # turret (local to Bone_Turret)
    if not signal:
        ellipsoid(bm, (0.0, 0.0, 0.6), (3.6, 3.2, 1.8), STEEL, segs=(14, 8))
        box(bm, -1.2, -0.6, 1.8, 0.8, 0.6, 2.8, mat=GL)                          # sensor
    else:                                               # kabuto helmet with a glowing visor
        ellipsoid(bm, (0.0, 0.0, 0.8), (3.0, 2.8, 2.8), STEEL, segs=(14, 8))
        ellipsoid(bm, (-0.6, 0.0, 0.0), (3.4, 4.4, 1.0), TEAM, segs=(14, 6))     # helmet brim
        box(bm, 2.4, -1.6, 0.2, 3.0, 1.6, 1.0, mat=GL)                           # visor
    parts['TURRET'] = base.obj_from_bm('TURRET', bm, mats)

    bm = bmesh.new()                                    # pitch bone: twin barrels / the kabuto's crescent horns
    if not signal:
        for s in (-1, 1):
            rod(bm, (0.0, s * 1.0, 0.0), (8.0, s * 1.0, 0.0), 0.45, 0.4, DK, segs=8, smooth=False)
            rod(bm, (7.2, s * 1.0, 0.0), (8.2, s * 1.0, 0.0), 0.65, 0.65, RD, segs=8, smooth=False)
    else:
        for s in (-1, 1):
            pts = [(0.6, s * 1.2, 1.4), (1.0, s * 3.0, 3.0), (0.4, s * 4.2, 5.4), (-0.6, s * 4.4, 7.4)]
            for p0, p1 in zip(pts, pts[1:]):
                rod(bm, p0, p1, 0.55, 0.4, RD, segs=6)
        ellipsoid(bm, (1.2, 0.0, 1.6), (0.8, 0.8, 1.2), GL, segs=(8, 6))        # crest jewel
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    parts['BARREL'] = base.obj_from_bm('BARREL', bm, mats)
    if signal:                                          # head and horns at the figure's scale
        for name in ('TURRET', 'BARREL'):
            me = parts[name].data
            for v in me.vertices:
                v.co *= BODY
    for ob in parts.values():
        base.bevel_and_finish(ob, width=0.12, segments=1, angle=50)
    return parts


def main():
    base.TURRET_AT, base.PITCH_AT = TURRET_AT[FORM], PITCH_AT[FORM]
    sc = base.reset()
    mats = [base.material('steel', WHITE), base.material('dark', DARK), base.material('team', WHITE, team=1.0),
            base.material('glow', GLOW, emit=4.0), base.material('red', RED)]
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
