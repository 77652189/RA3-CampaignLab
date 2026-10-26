"""Read retail W3D meshes (and their hierarchies) out of the game's static stream as plain geometry, for reference
sheets and kitbashing (the OBJs go to work/, not git).

  python -I experimental/units/retail_mesh.py <mesh id> [<hierarchy id>] [...]   -> work/reference/mesh/<mesh id>.obj
  (the hierarchy defaults to <model>_SKL)
  python -I experimental/units/retail_mesh.py --list <regex>                     names of matching meshes / hierarchies

e.g. AUANTIVEHICLEVEHICLETECH1_SKN.NEWSKIN (the Guardian), AUENGINEER_SKN.AUENGINEER AUENGINEER_SKL (skinned).

Compiled W3DMesh (2026-10-26, checked on the Guardian, Athena and engineer: renders with the retail texture match):
  12..35 bounding box, 52 u32 triangle count, 56 pointer to the triangles (pointers are offsets from the instance
  start); a triangle is 24 bytes: u32 3, pointer to its three u32 vertex indices, plane normal (3 f32) and distance.
  4 pointer to the vertex block: u32 count, u32 stride, pointer to the data, u32 length + pointer of an ASCII layout
  ("p0:00:3f32 n0:0C:3f32 c0:18:4u8n g0:1C:3f32 b0:28:3f32 t0:34:2f32 i0:3C:4u8": name, byte offset, type).
  Then u32 count + pointer of a u16 palette: vertex bone index -> hierarchy pivot. Positions are in their bone's
  space: p0 of bone i0[0], and (skinned, infantry) p1 of bone i0[1], blended by w0; load() takes the hierarchy
  <model>_SKL for <model>_SKN.<mesh>. (Raw p0 of a vehicle looks almost right -- hull and turret bones sit near
  the origin -- but its barrel and antennas collapse; the engineer's palette is 0..20, so only the palette makes the
  Guardian and Athena come out right.)
Compiled W3DHierarchy: u32 0, u32 pivot count, pointer; a pivot is 100 bytes: u32 name hash, i32 parent, translation
(3 f32), rotation (x y z w), fixup matrix (16 f32). Names exist only as hashes.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
sys.path.insert(0, HERE)
import labpaths                                 # noqa: E402
import button_icon                              # noqa: E402  (its STATIC layer list)

OUT = os.path.join(labpaths.WORK, 'reference', 'mesh')


def _qmat(x, y, z, w):
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def _mul(a, b):
    (ra, ta), (rb, tb) = a, b
    return ([[sum(ra[i][k] * rb[k][j] for k in range(3)) for j in range(3)] for i in range(3)],
            [sum(ra[i][k] * tb[k] for k in range(3)) + ta[i] for i in range(3)])


def _apply(m, p):
    r, t = m
    return [sum(r[i][k] * p[k] for k in range(3)) + t[i] for i in range(3)]


def hierarchy(d):
    """[(name hash, parent, world (rotation 3x3, translation))] in bind pose."""
    _, n, off = struct.unpack_from('<3I', d, 0)
    out = []
    for k in range(n):
        b = off + 100 * k
        h, parent = struct.unpack_from('<Ii', d, b)
        local = (_qmat(*struct.unpack_from('<4f', d, b + 20)), list(struct.unpack_from('<3f', d, b + 8)))
        out.append((h, parent, local if parent < 0 else _mul(out[parent][2], local)))
    return out


def mesh(d, skeleton=None):
    """{'vertices', 'uvs', 'bones' (hierarchy pivot of each vertex's first bone), 'triangles', 'layout'} in model
    space; skeleton (hierarchy()) None leaves the vertices in their bones' space."""
    ntri, tptr = struct.unpack_from('<2I', d, 52)
    n, stride, data, ln, lp, npal, pp = struct.unpack_from('<7I', d, struct.unpack_from('<I', d, 4)[0])
    layout = d[lp:lp + ln].decode()
    palette = struct.unpack_from(f'<{npal}H', d, pp)
    f = {name: int(off, 16) for name, off, _ in (e.split(':') for e in layout.split())}
    verts, uvs, bones = [], [], []
    for k in range(n):
        b = data + k * stride
        i0, i1 = (palette[d[b + f['i0'] + j]] for j in (0, 1))
        p = list(struct.unpack_from('<3f', d, b + f['p0']))
        if skeleton is not None:
            w0, w1 = (d[b + f['w0']] / 255, d[b + f['w0'] + 1] / 255) if 'w0' in f else (1, 0)
            a = _apply(skeleton[i0][2], p)
            c = _apply(skeleton[i1][2], struct.unpack_from('<3f', d, b + f['p1'])) if w1 > 0 else a
            p = [(w0 * a[j] + w1 * c[j]) / ((w0 + w1) or 1) for j in range(3)]
        verts.append(p)
        uvs.append(struct.unpack_from('<2f', d, b + f['t0']))
        bones.append(i0)
    tris = []
    for k in range(ntri):
        cnt, ip = struct.unpack_from('<2I', d, tptr + 24 * k)
        assert cnt == 3, (k, cnt)
        tris.append(struct.unpack_from('<3I', d, ip))
    assert max(max(t) for t in tris) < n
    return dict(vertices=verts, uvs=uvs, bones=bones, triangles=tris, layout=layout)


def load(by, mesh_id, skl=None):
    """mesh() of a library() entry in model space, through skl or the hierarchy named after its model."""
    skl = skl or mesh_id.split('.')[0].upper().replace('_SKN', '_SKL')
    return mesh(bytes(by['w3dmesh:' + mesh_id.lower()].chunks[0]),
                hierarchy(bytes(by['w3dhierarchy:' + skl.lower()].chunks[0])))


def write_obj(m, path):
    with open(path, 'w') as o:
        o.write(f'# {m["layout"]}\n')
        for x, y, z in m['vertices']:
            o.write(f'v {x:.4f} {y:.4f} {z:.4f}\n')
        for u, v in m['uvs']:
            o.write(f'vt {u:.5f} {1 - v:.5f}\n')
        for t in m['triangles']:
            o.write('f ' + ' '.join(f'{i + 1}/{i + 1}' for i in t) + '\n')


def library():
    import mapxml
    lib = mapxml.layered(button_icon.STATIC)
    return {i.name.decode(errors='replace').lower(): i for i in lib.values()}


def main(argv):
    by = library()
    if argv[0] == '--list':
        pat = re.compile(argv[1], re.I)
        for k in sorted(by):
            if k.startswith(('w3dmesh:', 'w3dhierarchy:')) and pat.search(k):
                print(by[k].name.decode(), len(bytes(by[k].chunks[0])))
        return
    os.makedirs(OUT, exist_ok=True)
    meshes = [a for a in argv if not a.upper().endswith('_SKL')]
    skl = [a for a in argv if a.upper().endswith('_SKL')]
    for name in meshes:
        m = load(by, name, skl[0] if skl else None)
        path = os.path.join(OUT, name + '.obj')
        write_obj(m, path)
        print(path, len(m['vertices']), 'vertices', len(m['triangles']), 'triangles')


if __name__ == '__main__':
    main(sys.argv[1:])
