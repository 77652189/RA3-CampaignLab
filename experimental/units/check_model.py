"""Offline check of a unit model before the bench (the game says nothing when a bone or texture is missing: a turret
that does not turn, an invisible part, a unit that cannot be clicked):

  python -I experimental/units/check_model.py <model.w3x> [<unit.xml>] [--budget 4500]

check() returns [(level, message)], level 'error' (it will break in game) or 'warn' (it will look wrong):
- the W3X parses; its ART: includes resolve (<art>/<first two letters>/<name>) and the textures the meshes name
  are declared there or in a resolved include
- hierarchy: unique pivot names, every parent before its child; container sub-objects name existing meshes and
  pivots; a W3DCollisionBox sub-object (without one a unit can be box-selected but not clicked, CampNew30)
- meshes: as many normals / texcoords (tangents, binormals) as vertices, triangle indices in range, no degenerate
  triangles, texcoords inside 0..1
- every bone the unit XML names (*Bone, BoneName, TurretNameKey, TurretPitch, ExtraPublicBone; any case) is a pivot
- z-fighting: two triangles facing the same way in one plane (within 0.02) that overlap by more than a sliver --
  the shimmer the game shows where two parts share a face (game-asset-aesthetic-test's blocky-zfight-check idea)
- the triangle count against a budget (the Guardian: 3289 + 384 treads)
tests/test_check_model.py proves each check on a model broken on purpose.
"""
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

NS = '{uri:ea.com:eala:asset}'
PLANE_TOL, NORMAL_DOT, OVERLAP = 0.02, 0.999, 0.05      # game units, cos, overlap area (game units^2)


def _art_path(art, ref):
    name = ref.split(':', 1)[1]
    return os.path.join(art, name[:2], name)


def _xyz(e):
    return tuple(float(e.get(k)) for k in 'XYZ')


def _declared_textures(root):
    return {t.get('id') for t in root.iter(NS + 'Texture') if t.get('id')}


def load(path):
    root = ET.parse(path).getroot()
    piv = [(p.get('Name'), int(p.get('Parent')), _xyz(p.find(NS + 'Translation')))
           for p in root.iter(NS + 'Pivot')]
    meshes = {}
    for m in root.iter(NS + 'W3DMesh'):
        g = {k: [_xyz(v) if k != 'TexCoords' else (float(v.get('X')), float(v.get('Y'))) for v in m.find(NS + k)]
             for k in ('Vertices', 'Normals', 'TexCoords', 'Tangents', 'Binormals') if m.find(NS + k) is not None}
        g['tris'] = [tuple(int(v.text) for v in t.findall(NS + 'V')) for t in m.find(NS + 'Triangles')]
        g['textures'] = [v.text for c in m.iter(NS + 'Texture') for v in c.findall(NS + 'Value')]
        meshes[m.get('id')] = g
    boxes = {b.get('id') for b in root.iter(NS + 'W3DCollisionBox')}
    container = root.find(NS + 'W3DContainer')
    subs = []
    if container is not None:
        for s in container.findall(NS + 'SubObject'):
            ro = s.find(NS + 'RenderObject')
            kind, ref = ro[0].tag.replace(NS, ''), ro[0].text
            subs.append((s.get('SubObjectID'), int(s.get('BoneIndex')), kind, ref))
    includes = [i.get('source') for i in root.iter(NS + 'Include')]
    return dict(root=root, pivots=piv, meshes=meshes, boxes=boxes, subs=subs, includes=includes)


def unit_bones(xml_text):
    names = set()
    for attr, value in re.findall(r'\b(\w*Bone\w*|BoneName|TurretNameKey|TurretPitch)\s*=\s*"([^"]*)"', xml_text):
        if attr.lower().endswith('followbone'):
            continue
        names.update(v for v in value.split() if v)
    return names


def _poly_area(p):
    return abs(sum(p[i][0] * p[i - 1][1] - p[i - 1][0] * p[i][1] for i in range(len(p)))) / 2


def _clip(subject, clipper):
    """Sutherland-Hodgman: subject polygon clipped by a convex counter-clockwise clipper."""
    out = subject
    for i in range(len(clipper)):
        a, b = clipper[i - 1], clipper[i]
        inp, out = out, []
        if not inp:
            break
        side = lambda p: (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])    # noqa: E731
        for j in range(len(inp)):
            p, q = inp[j - 1], inp[j]
            sp, sq = side(p), side(q)
            if sq >= 0:
                if sp < 0:
                    t = sp / (sp - sq)
                    out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
                out.append(q)
            elif sp >= 0:
                t = sp / (sp - sq)
                out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def _ccw(p):
    s = sum(p[i][0] * p[i - 1][1] - p[i - 1][0] * p[i][1] for i in range(len(p)))
    return p if s < 0 else p[::-1]        # the sum above is negative for counter-clockwise


def zfight(tris):
    """tris: [(part, (a, b, c) model-space points)] -> [(part, part, overlap area)] of coplanar same-facing pairs."""
    buckets = {}
    info = []
    for k, (part, (a, b, c)) in enumerate(tris):
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
        ln = math.sqrt(sum(x * x for x in n))
        if ln < 1e-9:
            info.append(None)
            continue
        n = [x / ln for x in n]
        d = sum(n[i] * a[i] for i in range(3))
        info.append((n, d))
        key = (round(n[0] * 10), round(n[1] * 10), round(n[2] * 10), math.floor(d / PLANE_TOL))
        buckets.setdefault(key, []).append(k)
    found = []
    seen = set()
    for key, ks in buckets.items():
        near = [j for dd in (0, 1) for j in buckets.get(key[:3] + (key[3] + dd,), [])]
        for i in ks:
            n, d = info[i]
            for j in near:
                if j <= i or (i, j) in seen:
                    continue
                seen.add((i, j))
                m, e = info[j]
                if sum(n[t] * m[t] for t in range(3)) < NORMAL_DOT or abs(d - e) > PLANE_TOL:
                    continue
                ax = max(range(3), key=lambda t: abs(n[t]))          # drop the dominant axis
                keep = [t for t in range(3) if t != ax]
                p = _ccw([(q[keep[0]], q[keep[1]]) for q in tris[i][1]])
                q = _ccw([(r[keep[0]], r[keep[1]]) for r in tris[j][1]])
                area = _poly_area(_clip(p, q)) if p and q else 0.0
                if area > OVERLAP:
                    found.append((tris[i][0], tris[j][0], area))
    return found


def check(path, unit_xml=None, budget=None, art=None):
    art = art or os.path.dirname(os.path.dirname(os.path.abspath(path)))
    out = []
    try:
        m = load(path)
    except ET.ParseError as e:
        return [('error', f'W3X does not parse: {e}')]
    declared = _declared_textures(m['root'])
    for inc in m['includes']:
        if not inc.startswith('ART:'):
            continue
        p = _art_path(art, inc)
        if not os.path.exists(p):
            out.append(('error', f'include {inc} not found ({p})'))
            continue
        try:
            declared |= _declared_textures(ET.parse(p).getroot())
        except ET.ParseError as e:
            out.append(('error', f'include {inc} does not parse: {e}'))
    names = [p[0].upper() for p in m['pivots']]
    for k, (name, parent, _) in enumerate(m['pivots']):
        if names.count(name.upper()) > 1:
            out.append(('error', f'pivot {name} appears {names.count(name.upper())} times'))
        if not -1 <= parent < k or (parent == -1 and k != 0):
            out.append(('error', f'pivot {name}: parent {parent} must come before it'))
    world = []
    for name, parent, t in m['pivots']:
        world.append(t if parent < 0 or parent >= len(world) else tuple(a + b for a, b in zip(world[parent], t)))
    if not any(kind == 'CollisionBox' for _, _, kind, _ in m['subs']):
        out.append(('error', 'no W3DCollisionBox sub-object: the unit cannot be clicked'))
    total, tris = 0, []
    for sub, bone, kind, ref in m['subs']:
        if not 0 <= bone < len(m['pivots']):
            out.append(('error', f'sub-object {sub}: bone {bone} out of range'))
            continue
        if kind == 'CollisionBox':
            if ref not in m['boxes']:
                out.append(('error', f'sub-object {sub}: collision box {ref} not declared'))
            continue
        g = m['meshes'].get(ref)
        if g is None:
            out.append(('error', f'sub-object {sub}: mesh {ref} not declared'))
            continue
        n = len(g['Vertices'])
        for k in ('Normals', 'TexCoords', 'Tangents', 'Binormals'):
            if k in g and len(g[k]) != n:
                out.append(('error', f'{ref}: {len(g[k])} {k.lower()} for {n} vertices'))
        bad = [t for t in g['tris'] if len(t) != 3 or not all(0 <= i < n for i in t)]
        if bad:
            out.append(('error', f'{ref}: {len(bad)} triangles index past the {n} vertices'))
            continue
        uv = g.get('TexCoords', [])
        off = sum(1 for u, v in uv if not (-0.001 <= u <= 1.001 and -0.001 <= v <= 1.001))
        if off:
            out.append(('warn', f'{ref}: {off} texcoords outside 0..1 (they wrap onto other parts of the atlas)'))
        for tex in g['textures']:
            if tex not in declared:
                out.append(('error', f'{ref}: texture {tex} not declared in the model or its includes'))
        o = world[bone]
        degenerate = 0
        for a, b, c in g['tris']:
            pa, pb, pc = (tuple(x + y for x, y in zip(g['Vertices'][i], o)) for i in (a, b, c))
            u = [pb[i] - pa[i] for i in range(3)]
            v = [pc[i] - pa[i] for i in range(3)]
            cr = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            if math.sqrt(sum(x * x for x in cr)) < 1e-6:
                degenerate += 1
            else:
                tris.append((sub, (pa, pb, pc)))
        if degenerate:
            out.append(('warn', f'{ref}: {degenerate} degenerate (zero-area) triangles'))
        total += len(g['tris'])
    pairs = zfight(tris)
    if pairs:
        by = {}
        for a, b, area in pairs:
            by.setdefault(tuple(sorted((a, b))), []).append(area)
        for (a, b), areas in sorted(by.items()):
            out.append(('warn', f'z-fighting: {len(areas)} coplanar overlapping triangle pairs between {a} and {b} '
                                f'(largest {max(areas):.2f})'))
    if unit_xml:
        text = open(unit_xml, encoding='utf-8').read() if os.path.exists(unit_xml) else unit_xml
        for bone in sorted(unit_bones(text)):
            if bone.upper() not in names:
                out.append(('error', f'the unit XML names bone {bone}, the model has no such pivot'))
    if budget and total > budget:
        out.append(('warn', f'{total} triangles, over the budget of {budget}'))
    return out


def main(argv):
    budget = None
    if '--budget' in argv:
        k = argv.index('--budget')
        budget = int(argv[k + 1])
        argv = argv[:k] + argv[k + 2:]
    found = check(argv[0], argv[1] if len(argv) > 1 else None, budget)
    for level, msg in found:
        print(f'{level.upper():5} {msg}')
    print('OK' if not any(lv == 'error' for lv, _ in found) else 'FAILED', f'({len(found)} findings)')
    return 1 if any(lv == 'error' for lv, _ in found) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
