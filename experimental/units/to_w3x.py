"""Turn a Blender unit export (cnv_lighttank.py: parts.json + baked PNGs) into W3X model, textures and a still
animation under the SDK's Art folder, rigged with the bone names a retail logic XML expects.

  convert(src_dir, model, pivots, part_bones, spec=110)

pivots: [(name, parent pivot name or None for ROOTTRANSFORM, (x, y, z) relative to the parent)]
part_bones: {part name in parts.json: pivot name}. Textures: <model>.tga (diffuse), <model>_NRM.tga (flat),
<model>_SPM.tga (R specular, G glow 0, B team colour mask from <model>_mask.png). Writes <model>_IDLE.w3x, a
one-frame animation of this hierarchy, so no retail animation (other hierarchy) is ever played on it.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
import w3x                                      # noqa: E402
from PIL import Image                           # noqa: E402


# retail Allied diffuse colour by brightness (AUAntiVehicleVehicleTech1, mean of r g b): (mean, B/R, G/R) -- darker is
# bluer, highlights near neutral. grade=True recolours every non-glow pixel to this curve at its own brightness.
RETAIL_TINT = [(40, 1.33, 1.10), (85, 1.28, 1.09), (145, 1.13, 1.07), (210, 1.02, 1.01)]


def tint(m):
    pts = RETAIL_TINT
    if m <= pts[0][0]:
        return pts[0][1:]
    for (m0, b0, g0), (m1, b1, g1) in zip(pts, pts[1:]):
        if m <= m1:
            t = (m - m0) / (m1 - m0)
            return b0 + t * (b1 - b0), g0 + t * (g1 - g0)
    return pts[-1][1:]


def convert(src, model, pivots, part_bones, src_name='CNTankL', spec=0.45, scale=1.0, level=72, grade=True,
            retail_maps=False, edge_gain=1.0, edge_spec=110, plate_spec=18, plate_share=12, body_spec=18, contrast=1.0,
            glow_margin=60, glow_floor=0, glow_lift=False, cool=1.0):
    """spec: specular (SPM red) as a fraction of the diffuse luminance -- retail Allied SPM red averages ~21;
    a flat 110 made the whole tank mirror the warm environment map (tan / pink in game, CampNew23 first run).
    scale: uniform size factor for vertices and pivots (the first in-game run read ~0.6 of a Guardian).
    level: median diffuse luminance to scale to (retail Allied vehicle diffuse medians are 62..80; our bakes came
    out at 107..143 and read white in game, CampNew25). Cyan light pixels keep their colour and go into SPM green
    (glow), as on retail units. None keeps the bake as is.
    grade: recolour to the retail cool-silver curve (RETAIL_TINT); our bakes came out near neutral (B/R ~1.07) and
    read warm under the game's sun.
    glow_margin / glow_floor: a texel glows (SPM green) when its green and blue both exceed red by the margin and both
    reach the floor -- 60 / 0 caught 0.9 % of the chrono-lag's bake, its pale cyan rings were left out and in game
    the lights could not be seen (user 2026-10-26: "青色光要看得见"; 30 / 120 catch 1.3 %). glow_lift: glowing texels
    recoloured a saturated bright cyan at their own hue's strength. cool: the non-glow, non-team body's blue x cool,
    red / cool (the chrono-lag read brown beside the Guardian)."""
    with open(os.path.join(src, 'parts.json'), encoding='utf-8') as f:
        parts = json.load(f)
    index = {name: k + 1 for k, (name, _, _) in enumerate(pivots)}          # ROOTTRANSFORM is 0
    piv = [(name, 0 if parent is None else index[parent], tuple(c * scale for c in at)) for name, parent, at in pivots]
    geo = []
    for part, bone in part_bones.items():
        p = parts[part]
        verts = [tuple(c * scale for c in v) for v in p['vertices']]
        g = (verts, p['normals'], p['uvs'], p['triangles'])
        if 'tangents' in p:             # frame of the baked normal map (cnv_lighttank.export)
            g += (p['tangents'], p['binormals'])
        geo.append((part, index[bone], g))
    diffuse = Image.open(os.path.join(src, src_name + '.png')).convert('RGBA')
    mask = Image.open(os.path.join(src, src_name + '_mask.png')).convert('L').resize(diffuse.size)
    w, h = diffuse.size
    dp, mp = diffuse.load(), mask.load()
    debug = os.environ.get('CNV_UV_DEBUG') == '1'     # unbaked background (pure black) shown magenta in game

    def lum(r, g, b):
        return 0.3 * r + 0.59 * g + 0.11 * b

    def glow(r, g, b):
        return g > r + glow_margin and b > r + glow_margin and min(g, b) >= glow_floor
    k = 1.0
    if level:
        ls = sorted(lum(*dp[x, y][:3]) for x in range(0, w, 2) for y in range(0, h, 2)
                    if max(dp[x, y][:3]) > 10 and not glow(*dp[x, y][:3]))
        k = min(1.0, level / ls[len(ls) // 2]) if ls else 1.0

    def diffuse_px(x, y):
        r, g, b, _ = dp[x, y]
        if debug and r == g == b == 0:
            return 255, 0, 255, 255
        if glow(r, g, b):
            return r, g, b, 255
        r, g, b = r * k, g * k, b * k
        if grade:
            m = (r + g + b) / 3
            br, gr = tint(m)
            r = 3 * m / (1 + gr + br)
            r, g, b = r, r * gr, r * br
        return min(255, int(r)), min(255, int(g)), min(255, int(b)), 255

    if retail_maps:
        # ObjectsAllied.fx (SDK Max plugin, disassembled with fx_disasm.py): colour = diffuse * (1 + mask * (2 *
        # RecolorColor - 1)) -- a fully masked texel shows 2 x diffuse x house colour; specular = SPM.r * 0.8 *
        # (N.H)^50, white. So team areas are neutral grey (no tint: the house colour does the tinting) keeping the
        # body's own shading -- AO, seams, edges -- and soft mask edges (half the retail Guardian's mask texels are
        # partial); our uniform hard-edged blue panels read as stickers, and a 2x grey went pale lavender. The
        # retail specular is two-level: 70 % of the body texels ~0, 17 % at 64-128 (edges, raised plates).
        import numpy as np
        from PIL import ImageFilter
        src_rgb = np.asarray(diffuse.convert('RGB'), float)
        out = np.array([[diffuse_px(x, y)[:3] for x in range(w)] for y in range(h)], float)
        lb = src_rgb @ (0.3, 0.59, 0.11)
        is_glow = ((src_rgb[..., 1] > src_rgb[..., 0] + glow_margin) & (src_rgb[..., 2] > src_rgb[..., 0] + glow_margin)
                   & (np.minimum(src_rgb[..., 1], src_rgb[..., 2]) >= glow_floor))
        soft = np.asarray(mask.filter(ImageFilter.GaussianBlur(1.5)), float) / 255
        used = lb > 10
        body = used & ~is_glow & (soft < 0.05)
        med = np.median(lb[body]) if body.any() else 1.0
        team_grey = np.clip(lb * k, 0, 235)[..., None].repeat(3, 2)            # keeps AO, seams, edges
        a = soft[..., None]
        out = np.where(is_glow[..., None], out, out * (1 - a) + team_grey * a)
        dark = lb < 0.55 * med
        # edges = thin bright lines (the bake's pointiness highlight), not the brightest texels overall -- those were
        # whole upward faces (grime gradient, AO) and boosting them washed the tank out (close-up median 79 -> 88)
        # (local mean over baked texels only: with the black background in the blur every UV island border read
        # as an edge -- 26 % of the texels)
        def blur(v):
            return np.asarray(Image.fromarray(np.clip(v, 0, 255).astype(np.uint8)).filter(
                ImageFilter.GaussianBlur(4)), float)
        local = blur(np.where(used, lb, 0)) / np.maximum(blur(used * 255.0) / 255.0, 1e-3)
        edge = used & ~is_glow & (lb > local * 1.2 + 10)
        # contrast like the Guardian's on screen (CampNew25 close-up: median 66, p90 170, p10 6 vs our 79 / 143 /
        # 13): edge highlights x edge_gain, dark parts x 0.7 (team texels too: the house colour is a multiply)
        gain = np.where(edge, edge_gain, np.where(dark, 0.7, 1.0))[..., None]
        out = np.where(is_glow[..., None], out, out * gain)
        if contrast != 1.0:
            # spread around the body median: the game's specular (exponent 50) barely lifts the RTS view, the
            # Guardian's highlights are in its diffuse (texture p90 152 at median 69)
            lo = out.mean(axis=2, keepdims=True)
            m = np.median(lo[body]) if body.any() else 1.0
            r = np.maximum(lo, 1e-3) / m
            curve = np.where(r > 1, r ** contrast, r ** (0.5 + 0.5 * contrast))
            out = np.where(is_glow[..., None], out, np.clip(out * (curve / r), 0, 240))
        if cool != 1.0:
            out = np.where(body[..., None], out * (1 / cool, 1.0, cool), out)
        if glow_lift:
            # the lights a saturated cyan as bright as their own green / blue allow (never below 3/4): pale baked
            # cyan (110, 181, 205) went grey in game
            strength = np.clip(np.maximum(src_rgb[..., 1], src_rgb[..., 2]) / 255 * 1.15, 0.75, 1.0)[..., None]
            out = np.where(is_glow[..., None], np.array((70.0, 230.0, 255.0)) * strength, out)
        # plates: the brightest body texels (upward faces) shine without being brightened -- the retail Guardian's
        # highlights are mostly specular on broad plates (17 % of its SPM at 64-128); thin edges alone left the
        # close-up dull (p90 114 vs the Guardian's 170)
        plate = body & ~edge & (lb > np.percentile(lb[body], 100 - plate_share)) if body.any() else np.zeros_like(edge)
        spec_r = np.where(dark, 4, np.where(edge, edge_spec, np.where(plate, plate_spec, body_spec))).astype(float)
        spec_r = np.where(is_glow, 0, spec_r)
        spm_rgb = np.stack([spec_r, np.where(is_glow, 255, 0), np.clip(soft * 255, 0, 255)], 2)
        out8, spm8 = np.clip(out, 0, 255).astype(np.uint8), spm_rgb.astype(np.uint8)
        w3x.write_texture(model, w, h, lambda x, y: (*map(int, out8[y, x]), 255))
        w3x.write_texture(model + '_SPM', w, h, lambda x, y: (*map(int, spm8[y, x]), 255))
        print(f'{model}: retail-style maps: team texels {(soft > 0.05).mean():.3f}, glow {is_glow.mean():.4f}, '
              f'edges {edge.mean():.3f}, plates {plate.mean():.3f}, '
              f'matte {dark.mean():.3f}')
    else:
        w3x.write_texture(model, w, h, diffuse_px)

        def spm(x, y):
            r, g, b, _ = dp[x, y]
            if glow(r, g, b):
                return 0, 255, 0, 255
            return int(spec * k * lum(r, g, b)), 0, 255 if mp[x, y] > 127 else 0, 255
        w3x.write_texture(model + '_SPM', w, h, spm)
    nrm_png = os.path.join(src, src_name + '_nrm.png')
    if os.path.exists(nrm_png) and all('tangents' in parts[pt] for pt in part_bones):
        # baked tangent-space normal map (panel seams as grooves). Green as Blender bakes it (+v up): the retail
        # Guardian NRM has the same convention (curl test on its R / G gradients, +0.22 over 34k texels).
        # CNV_NRM_FLIP_G=1 flips it for an in-game A/B. Unbaked texels (black) become flat.
        import numpy as np
        flip = os.environ.get('CNV_NRM_FLIP_G') == '1'

        def vec(path):
            return np.asarray(Image.open(path).convert('RGB').resize((w, h)), float) / 127.5 - 1.0
        n1 = vec(nrm_png)
        n0_png = os.path.join(src, src_name + '_nrm0.png')
        n0 = vec(n0_png) if os.path.exists(n0_png) else np.zeros_like(n1) + (0.0, 0.0, 1.0)
        # seams relative to the unbumped bake (its bevel patches are tangent-frame mismatch, not relief)
        n = n1 - n0 + (0.0, 0.0, 1.0)
        n /= np.linalg.norm(n, axis=2, keepdims=True)
        rgb = np.clip((n + 1.0) * 127.5, 0, 255).astype(np.uint8)
        rgb[np.asarray(Image.open(nrm_png).convert('L').resize((w, h))) < 10] = (128, 128, 255)   # unbaked texels
        if flip:
            rgb[..., 1] = 255 - rgb[..., 1]

        def nrm(x, y):
            r, g, b = rgb[y, x]
            return int(r), int(g), int(b), 255
        w3x.write_texture(model + '_NRM', w, h, nrm)
    else:
        w3x.write_texture(model + '_NRM', 16, 16, lambda x, y: (128, 128, 255, 255))
    print(f'{model}: diffuse x{k:.2f} to median {level}')
    w3x.write_model(model, w3x.rig_model(model, piv, geo, (model, model + '_NRM', model + '_SPM')))
    w3x.write_model(model + '_IDLE', w3x.spin_animation(model + '_IDLE', model, 1, frames=1, turns=0.0))
    return sum(len(g[2][3]) for g in geo)
