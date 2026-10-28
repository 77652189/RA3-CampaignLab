"""The Liberty's look (自由号, the flying Liberty Island fortress; concept work/units/libertyisle/gpt/h6.png, sheet v4):
two models written to the SDK's Art folder --

  CNLiberty     the platform: Tripo (libertyisle_v1.glb) -> tripo_unit.py libertyisle (kind 'platform', one piece
                BODY with the bones liberty.py's Kirov XML names, STATUE at the core's top) -> to_w3x.convert in the
                chrono-lag's look (cool silver, cyan glow lifted, retail Allied maps)
  CNLibStatue   retail New York's Statue of Liberty (NY_LIBERTY, World Builder's stream) without her pedestal (the
                core is her pedestal), stood on STATUE, her torch a cyan chrono beacon (glow)
  CNLibRings    three glowing gyroscope rings around her, tilted, each turning on its own pivot (CNLibRings_IDLE)
  CNLibCharge   the jump's charge-up: her crown's seven rays lighting one by one, rings opening out round her feet
                (CNLibCharge_CHARGE, 15 s; drawn under USER_1, which the jump warning sets)

  python -I -X utf8 experimental/units/liberty_kit.py        (from a worktree set CNV_SDK; run tripo_unit.py first)

Both drawn at the unit's origin (two ScriptedModelDraws, liberty_look.dress), the statue carrying its place.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
sys.path.insert(0, HERE)
import labpaths                                 # noqa: E402
import make_campchrono                          # noqa: E402  (its LOOK)
import retail_mesh                              # noqa: E402
import retail_texture                           # noqa: E402
import to_w3x                                   # noqa: E402
import w3x                                      # noqa: E402
from PIL import Image                           # noqa: E402

MODEL, STATUE = 'CNLiberty', 'CNLibStatue'
SRC = os.path.join(labpaths.WORK, 'units', 'libertyisle', 'game')
STATUE_MESHES = ['NY_LIBERTY.NEWSKIN_STATUE', 'NY_LIBERTY.NEWSKIN_FILL1', 'NY_LIBERTY.NEWSKIN_FILL2']
# first bench run (2026-10-27, width 400, statue 0.35 of it): a corner filled the screen and the statue rose into the
# camera; the user picked 250..300 across and the statue about as tall as the core above the deck (~0.21 of the width)
SCALE = 0.7                                     # the bake is 400 across (tripo_unit's width) -> 280
STATUE_TALL = 0.21                              # her height (feet to torch) over the platform's width
COPPER = (0.85, 0.97, 1.06)                     # her diffuse per channel: the game's sun read her yellow


def sockets(verts):
    """The rim's turret sockets (raised rings standing above the rampart): per 5-degree sector of the outer ring the
    highest vertex; runs of sectors standing 6 above the rampart (the median sector) are one socket, its bone at
    their highest points' centre. The v1 bake has five (four corners and the west side; the east side is the elevator)."""
    import math
    w = max(max(v[0] for v in verts) - min(v[0] for v in verts), max(v[1] for v in verts) - min(v[1] for v in verts))
    top = {}
    for x, y, z in verts:
        if math.hypot(x, y) > 0.42 * w:             # past the elevator's frame (0.36..0.40), which stands higher
            b = int(math.degrees(math.atan2(y, x)) % 360 // 5)
            if z > top.get(b, (-1e9,))[0]:
                top[b] = (z, x, y)
    wall = sorted(z for z, _, _ in top.values())[len(top) // 2]       # the rampart's top, most sectors
    high = sorted(b for b, (z, _, _) in top.items() if z > wall + 6)
    runs = []
    for b in high:
        if runs and b - runs[-1][-1] <= 2:
            runs[-1].append(b)
        else:
            runs.append([b])
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] >= 70:      # a run across 0 degrees
        runs[0] = runs.pop() + runs[0]
    out = []
    for run in runs:
        pts = [top[b] for b in run]
        out.append((sum(p[1] for p in pts) / len(pts), sum(p[2] for p in pts) / len(pts), max(p[0] for p in pts)))
    return sorted(out, key=lambda p: math.atan2(p[1], p[0]) % (2 * math.pi))


def body():
    with open(os.path.join(SRC, 'parts.json'), encoding='utf-8') as f:
        data = json.load(f)
    pivots = [tuple(p) for p in data['_pivots']]
    # the turret sockets as bones TURRET01.. (not wired: liberty.py's turrets still follow as drones, 总控 2026-10-27)
    pivots += [(f'TURRET{k + 1:02d}', None, s) for k, s in enumerate(sockets(data['BODY']['vertices']))]
    n = to_w3x.convert(SRC, MODEL, pivots, {'BODY': 'BODY'}, src_name=MODEL, level=make_campchrono.LEVEL,
                       retail_maps=True, scale=SCALE, **make_campchrono.LOOK)
    print(MODEL, n, 'triangles')
    return dict((name, tuple(c * SCALE for c in at)) for name, _, at in pivots)


def _copper(rgb):
    r, g, b = rgb
    return g > r + 6 and b > r - 10            # her green copper; the pedestal's granite and brick are not


def _flame(rgb):
    r, g, b = rgb
    return r > 150 and g > 110 and b < 0.6 * g  # the gilded torch flame


def statue(top, width):
    retail_texture.main(['NY_Liberty'])
    tex = Image.open(os.path.join(retail_texture.OUT, 'NY_Liberty.png')).convert('RGB')
    w, h = tex.size
    px = tex.load()
    by = retail_mesh.library()

    def texel(m, tri):
        u = sum(m['uvs'][i][0] for i in tri) / 3
        v = sum(m['uvs'][i][1] for i in tri) / 3            # compiled: v down, as the PNG's rows
        return px[int(u % 1 * (w - 1)), int(v % 1 * (h - 1))]

    meshes = [retail_mesh.load(by, m) for m in STATUE_MESHES]
    main = meshes[0]
    keep = [t for t in main['triangles'] if _copper(texel(main, t)) or _flame(texel(main, t))]
    feet = min(main['vertices'][i][2] for t in keep for i in t)
    zs = [main['vertices'][i][2] for t in keep for i in t]
    xs = [main['vertices'][i][0] for t in keep for i in t]
    ys = [main['vertices'][i][1] for t in keep for i in t]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    k = STATUE_TALL * width / (max(zs) - feet)
    verts, normals, uvs, tris = [], [], [], []
    for j, m in enumerate(meshes):
        ts = keep if j == 0 else [t for t in m['triangles'] if min(m['vertices'][i][2] for i in t) >= feet]
        base = len(verts)
        # turned a quarter: retail's statue faces +Y, the platform's front (Tripo's front view) is +X
        verts += [((y - cy) * k, -(x - cx) * k, (z - feet) * k + top) for x, y, z in m['vertices']]
        normals += [(ny, -nx, nz) for nx, ny, nz in m['normals']] or [(0.0, 0.0, 1.0)] * len(m['vertices'])
        uvs += [(u, 1 - v) for u, v in m['uvs']]
        tris += [tuple(base + i for i in t) for t in ts]
    # her torch a cyan chrono beacon: the flame recoloured and glowing (SPM green); a little specular on the copper
    def diffuse(x, y):
        c = px[x, y]
        return (70, 230, 255, 255) if _flame(c) else tuple(min(255, int(v * k)) for v, k in zip(c, COPPER)) + (255,)

    w3x.write_texture(STATUE, w, h, diffuse)
    w3x.write_texture(STATUE + '_NRM', 16, 16, lambda x, y: (128, 128, 255, 255))
    w3x.write_texture(STATUE + '_SPM', w, h, lambda x, y: (40, 255, 0, 255) if _flame(px[x, y]) else (8, 0, 0, 255))
    w3x.write_model(STATUE, w3x.rig_model(STATUE, [], [('STATUE', 0, (verts, normals, uvs, tris))],
                                          (STATUE, STATUE + '_NRM', STATUE + '_SPM')))
    tall = (max(zs) - feet) * k
    print(STATUE, len(tris), 'triangles,', f'{tall:.0f} tall on {top:.0f}, scale {k:.2f}')
    obj = os.path.join(OUT, STATUE + '.obj')
    retail_mesh.write_obj(dict(vertices=verts, uvs=[(u, 1 - v) for u, v in uvs], triangles=tris, layout='liberty_kit'),
                          obj)
    # her head: 0.72..0.82 of her height, off the raised arm (her right, -Y, 0.07 out); the crown at 0.79
    head = [verts[i] for t in tris[:len(keep)] for i in t
            if 0.72 <= (verts[i][2] - top) / tall < 0.82 and verts[i][1] > -0.04 * tall]
    crown = (sum(p[0] for p in head) / len(head), sum(p[1] for p in head) / len(head), top + 0.79 * tall)
    return obj, os.path.join(retail_texture.OUT, 'NY_Liberty.png'), crown


OUT = os.path.join(labpaths.WORK, 'units', 'libertyisle')

# the gyroscope rings hovering around her (concept h4..h6: technology shown by floating, turning parts): each its own
# pivot over the core, its band tilted on that pivot and the pivot turning about Z, so a tilted ring sweeps round
# like an armillary sphere; (radius, tilt, phase, turns per loop) as fractions of the width / degrees
RINGS = MODEL[:2] + 'LibRings'
RING_SET = [(0.18, 22, 0, 1), (0.22, 48, 60, -1), (0.26, 70, 120, 2)]
RING_LOOP = 240                                 # frames at 30 fps: the slowest ring turns once in 8 s


def rings(top, statue_tall, width):
    """CNLibRings (+ _IDLE, the looping turn): three thin bands, metal outside and on top, a cyan glowing track on
    the inner wall and underneath (SPM green), centred at her waist."""
    import math
    zc = top + 0.45 * statue_tall
    # half the band's radial thickness and height (0.008 / 0.011 read as chunky toy hoops on the bench)
    t, h = 0.005 * width, 0.0065 * width
    parts, pivots = [], []
    for k, (r, tilt, phase, _) in enumerate(RING_SET):
        rr = r * width
        geo = w3x.lathe([(rr + t, h), (rr + t, -h), (rr - t, -h), (rr - t, h), (rr + t, h)], segments=48)
        a, p = math.radians(tilt), math.radians(phase)
        tilt_x = ((1, 0, 0), (0, math.cos(a), -math.sin(a)), (0, math.sin(a), math.cos(a)))
        turn_z = ((math.cos(p), -math.sin(p), 0), (math.sin(p), math.cos(p), 0), (0, 0, 1))
        geo = w3x.transform(w3x.transform(geo, tilt_x), turn_z)
        pivots.append((f'RING{k + 1}', 0, (0.0, 0.0, zc)))
        parts.append((f'RING{k + 1}', k + 1, geo))

    # v along the profile: 0..0.25 outer wall, ..0.5 bottom, ..0.75 inner wall, ..1 top; the middle half glows,
    # whichever way the rows run
    def glow(y):
        return 0.25 <= y / 63 <= 0.75

    w3x.write_texture(RINGS, 64, 64, lambda x, y: (70, 230, 255, 255) if glow(y) else
                      (150 + 12 * (x % 8 == 0), 156, 168, 255))
    w3x.write_texture(RINGS + '_NRM', 16, 16, lambda x, y: (128, 128, 255, 255))
    w3x.write_texture(RINGS + '_SPM', 64, 64, lambda x, y: (40, 255, 0, 255) if glow(y) else (60, 0, 0, 255))
    w3x.write_model(RINGS, w3x.rig_model(RINGS, pivots, parts, (RINGS, RINGS + '_NRM', RINGS + '_SPM')))
    # the turn: every ring's pivot about Z at its own whole number of turns per loop, so the loop is seamless
    up = RINGS.upper()
    ch = []
    for k, (_, _, _, turns) in enumerate(RING_SET):
        ch.append(f'\t\t\t<ChannelQuaternion Pivot="{k + 1}" Type="Orientation" FirstFrame="0">')
        for f in range(RING_LOOP):
            a = 2 * math.pi * turns * f / RING_LOOP
            ch.append(f'\t\t\t\t<Frame X="0.000000" Y="0.000000" Z="{math.sin(a / 2):.6f}" W="{math.cos(a / 2):.6f}"/>')
        ch.append('\t\t\t</ChannelQuaternion>')
    w3x.write_model(RINGS + '_IDLE', '\n'.join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '\t<Includes>', f'\t\t<Include type="all" source="ART:{RINGS}.w3x"/>', '\t</Includes>',
        f'\t<W3DAnimation id="{up}_IDLE" Hierarchy="{up}_SKL" NumFrames="{RING_LOOP}" FrameRate="30">',
        '\t\t<Channels>'] + ch + ['\t\t</Channels>', '\t</W3DAnimation>', '</AssetDeclaration>']) + '\n')
    print(RINGS, sum(len(g[3]) for _, _, g in parts), 'triangles, centred at', f'{zc:.0f}')


# the jump's charge-up (the 15 s warning, devices/carrier.py): her crown's seven rays light one by one as the countdown
# and rings open out round her feet one by one; drawn only under USER_1 (liberty.dress), which the warning
# sets for its length, the animation played once from its start
CHARGE = MODEL[:2] + 'LibCharge'
CHARGE_SECONDS = 15                             # carrier.py's 预警 default
RAY_AT = [1 + 2 * k for k in range(7)]          # seconds: a ray every 2 s, the last 2 s before the jump
APERTURE = [(0.05, 5), (0.085, 9), (0.12, 12)]  # (radius over the width, seconds): inner to outer
HIDDEN = -5000.0                                # a part not lit yet waits this far under the map


def charge(top, crown, statue_tall, width):
    """CNLibCharge (+ _CHARGE): seven glowing cones fanned forward from her crown (each its own pivot) and three
    glowing rings round her feet over the core's top (`top`); the animation keeps each part HIDDEN below until its
    second comes. (The rings were first under the keel, as the concept's aperture: the platform hid them from the
    RTS camera, bench 2026-10-27.)"""
    import math
    parts, pivots, at = [], [], []
    ray, base = 0.30 * statue_tall, 0.02 * statue_tall     # 0.012 read as hairlines at the RTS camera's zoom
    for k in range(7):
        az, el = math.radians(-75 + 25 * k), math.radians(15)
        d = (math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))
        e1 = (-math.sin(az), math.cos(az), 0.0)
        e2 = (d[1] * e1[2] - d[2] * e1[1], d[2] * e1[0] - d[0] * e1[2], d[0] * e1[1] - d[1] * e1[0])
        # a cone; its tip and cap a hair off the axis (a lathe row at radius 0 gives zero-area triangles)
        geo = w3x.lathe([(0.1 * base, ray), (base, 0.0), (0.1 * base, 0.0)], segments=6)
        geo = w3x.transform(geo, tuple((e1[i], e2[i], d[i]) for i in range(3)))   # +Z onto d
        pivots.append((f'RAY{k + 1}', 0, tuple(c + 0.035 * statue_tall * dc for c, dc in zip(crown, d))))
        parts.append((f'RAY{k + 1}', k + 1, geo))
        at.append(RAY_AT[k])
    t, h = 0.006 * width, 0.003 * width
    for k, (r, s) in enumerate(APERTURE):
        rr = r * width
        geo = w3x.lathe([(rr + t, h), (rr + t, -h), (rr - t, -h), (rr - t, h), (rr + t, h)], segments=48)
        pivots.append((f'IRIS{k + 1}', 0, (0.0, 0.0, top + 0.01 * width)))
        parts.append((f'IRIS{k + 1}', len(pivots), geo))
        at.append(s)
    w3x.write_texture(CHARGE, 8, 8, lambda x, y: (150, 245, 255, 255))
    w3x.write_texture(CHARGE + '_NRM', 16, 16, lambda x, y: (128, 128, 255, 255))
    w3x.write_texture(CHARGE + '_SPM', 8, 8, lambda x, y: (40, 255, 0, 255))
    w3x.write_model(CHARGE, w3x.rig_model(CHARGE, pivots, parts, (CHARGE, CHARGE + '_NRM', CHARGE + '_SPM')))
    frames = CHARGE_SECONDS * 30
    up = CHARGE.upper()
    ch = []
    for k, s in enumerate(at):
        ch.append(f'\t\t\t<ChannelScalar Pivot="{k + 1}" Type="ZTranslation" FirstFrame="0">')
        ch += [f'\t\t\t\t<Frame>{HIDDEN if f < s * 30 else 0.0:.6f}</Frame>' for f in range(frames)]
        ch.append('\t\t\t</ChannelScalar>')
    w3x.write_model(CHARGE + '_CHARGE', '\n'.join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '\t<Includes>', f'\t\t<Include type="all" source="ART:{CHARGE}.w3x"/>', '\t</Includes>',
        f'\t<W3DAnimation id="{up}_CHARGE" Hierarchy="{up}_SKL" NumFrames="{frames}" FrameRate="30">',
        '\t\t<Channels>'] + ch + ['\t\t</Channels>', '\t</W3DAnimation>', '</AssetDeclaration>']) + '\n')
    print(CHARGE, sum(len(g[3]) for _, _, g in parts), 'triangles, crown at', ' '.join(f'{c:.0f}' for c in crown))


def preview(statue_obj, statue_tex):
    """The two together rendered as retail_sheet's four views -> work/units/libertyisle/liberty_grid.png."""
    import subprocess
    import retail_sheet
    with open(os.path.join(SRC, 'parts.json'), encoding='utf-8') as f:
        p = json.load(f)['BODY']
    body_obj = os.path.join(OUT, MODEL + '.obj')
    retail_mesh.write_obj(dict(vertices=[tuple(c * SCALE for c in v) for v in p['vertices']], uvs=[(u, 1 - v) for u, v in p['uvs']], triangles=p['triangles'],
                               layout='liberty_kit'), body_obj)
    prefix = os.path.join(OUT, 'liberty')
    subprocess.run([retail_sheet.BLENDER, '-b', '--factory-startup', '-P', retail_sheet.__file__, '--', prefix,
                    f'{body_obj}={os.path.join(SRC, MODEL + ".png")}', f'{statue_obj}={statue_tex}'], check=True,
                   stdout=subprocess.DEVNULL)
    grid = Image.new('RGB', (1536, 1536), (208, 208, 208))
    for k, v in enumerate(retail_sheet.VIEWS):
        grid.paste(Image.open(f'{prefix}_{v}.png').convert('RGB').resize((768, 768)), ((k % 2) * 768, (k // 2) * 768))
    grid.resize((1024, 1024), Image.LANCZOS).save(prefix + '_grid.png')
    print('preview ->', prefix + '_grid.png')


def main():
    pv = body()
    with open(os.path.join(SRC, 'parts.json'), encoding='utf-8') as f:
        verts = json.load(f)['BODY']['vertices']
    width = SCALE * max(max(v[0] for v in verts) - min(v[0] for v in verts),
                        max(v[1] for v in verts) - min(v[1] for v in verts))
    obj, tex, crown = statue(pv['STATUE'][2], width)
    preview(obj, tex)
    rings(pv['STATUE'][2], STATUE_TALL * width, width)
    charge(pv['STATUE'][2], crown, STATUE_TALL * width, width)


if __name__ == '__main__':
    main()
