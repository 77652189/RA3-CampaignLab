"""Grade a Tripo bake toward its faction's retail vehicles, and check that it landed there (user 2026-11-15: "注意美术
风格上要协调，可以考虑靠加个滤镜"). Not a screen filter: that shifts retail units too and the gap between them stays.
Each bake is recoloured once, offline, with fixed per-faction numbers measured from retail diffuse textures:

- brightness: the body texels' channel mean mapped quantile to quantile onto the retail units' (p5..p95, each retail
  unit weighted alike) -- brightness and contrast in one step (to_w3x's `level` only ever darkened);
- colour: chromaticity (rgb / mean) moved onto the retail median at the new brightness (bands of 40), each texel
  keeping its own deviation from the bake's median, scaled by the retail spread over the bake's (never above 1) --
  accents (orange coils, red lights) stay, only quieter; GPT's clean saturated paint comes down to retail's;
- team texels (to_w3x makes them grey for the house colour): scaled to retail's team brightness (team_gain; ours
  came out half as bright and the house colour read dull); glow is left alone: grade() changes only the texels
  `body` marks.

Body = used (not black), not team colour (SPM blue < 40), not glow (SPM green < 40), as retail's SPM marks them.

  python -I -X utf8 experimental/units/faction_grade.py measure      reference stats from work/reference (pull the
                                                                     REFERENCE textures with retail_texture.py first)
  python -I -X utf8 experimental/units/faction_grade.py check <diffuse.tga> <spm.tga> <faction>

check() returns [(level, message)] as check_model.check does; tests/test_faction_grade.py proves each finding.
"""
import os
import sys

import numpy as np

QUANTILES = (5, 10, 25, 50, 75, 90, 95)
BANDS = (20, 60, 100, 140, 180, 220)            # band centres of the channel mean, 40 wide
REFERENCE = {
    'soviet': ['SUAntiVehicleVehicleTech1', 'SUAntiAirship', 'SUAntiInfantryVehicle', 'SUAntiAirVehicleTech1',
               'SUAntiAirVehicleTech3', 'SUAntiStructureVehicle', 'SUScoutVehicle', 'SUHarvester', 'SUSurveyor'],
    'allied': ['AUAntiVehicleVehicleTech1', 'AUAntiVehicleVehicleTech3', 'AUAntiStructureVehicle', 'AUIFV',
               'AUHarvester', 'AUMCV', 'AUAntiInfantryVehicle'],
    'japan': ['JUAntiVehicleVehicleTech1', 'JUAntiVehicleVehicleTech3', 'JUAntiInfantryVehicle', 'JUAntiStructureVehicle',
              'JUAntiAirVehicleTech1', 'JUHarvester', 'JUMCV', 'JUTransportVehicle'],
}
# measured 2026-11-15 (`measure`): mean = the body's channel-mean quantiles; chroma = per band (BANDS) the median
# (r, g, b) / mean; spread = median distance from that; mean50 / sat50 / sat90 = the lowest and highest retail unit
FACTIONS = {
    'soviet': {'mean': (19.2, 26.0, 40.7, 66.3, 93.9, 132.1, 162.4), 'chroma': [(1.085, 1.113, 0.803), (1.1, 1.138, 0.757), (1.066, 1.091, 0.838), (1.061, 1.081, 0.854), (1.048, 1.064, 0.892), (1.02, 1.025, 0.956)], 'spread': 0.1016, 'team50': 134.0, 'mean50_range': (42.0, 100.667), 'sat50_range': (0.09, 0.402), 'sat90_range': (0.353, 0.688), 'team50_range': (80.333, 156.667)},  # noqa: E501
    'allied': {'mean': (15.7, 20.4, 35.7, 66.2, 103.0, 143.9, 170.4), 'chroma': [(0.943, 0.989, 1.075), (0.936, 0.974, 1.085), (0.933, 0.974, 1.096), (0.952, 0.985, 1.066), (0.955, 0.986, 1.058), (0.971, 0.995, 1.032)], 'spread': 0.0647, 'team50': 155.3, 'mean50_range': (56.667, 81.0), 'sat50_range': (0.105, 0.238), 'sat90_range': (0.229, 0.5), 'team50_range': (77.333, 213.0)},  # noqa: E501
    'japan': {'mean': (23.0, 30.7, 57.1, 100.7, 158.5, 196.7, 213.0), 'chroma': [(1.01, 1.002, 0.975), (1.029, 1.014, 0.956), (1.044, 1.01, 0.944), (1.027, 1.009, 0.964), (1.024, 1.008, 0.968), (1.019, 1.007, 0.973)], 'spread': 0.0341, 'team50': 163.0, 'mean50_range': (49.667, 148.0), 'sat50_range': (0.02, 0.119), 'sat90_range': (0.12, 0.287), 'team50_range': (125.333, 214.333)},  # noqa: E501
}
TOL = dict(mean50=6, sat50=0.03, sat90=0.04)    # slack outside the retail range before check() complains


def body_mask(rgb, spm):
    return (rgb.max(2) > 10) & (spm[..., 2] < 40) & (spm[..., 1] < 40)


def saturation(p):
    mx = p.max(-1)
    return (mx - p.min(-1)) / np.maximum(mx, 1)


def _chroma(p):
    return p / np.maximum(p.mean(-1, keepdims=True), 1)


def band_medians(rgb, mean, keep, min_texels=200):
    """Per band of BANDS the median chromaticity of the kept texels (None for a band too thin to tell)."""
    n = _chroma(rgb)
    out = []
    for c in BANDS:
        sel = keep & (np.abs(mean - c) <= 20)
        out.append(tuple(np.median(n[sel], 0)) if sel.sum() >= min_texels else None)
    return out


def _fill(meds):
    """Thin bands take the nearest measured band's value."""
    have = [k for k, v in enumerate(meds) if v is not None]
    if not have:
        return np.ones((len(BANDS), 3))
    return np.array([meds[min(have, key=lambda h: abs(h - k))] for k in range(len(BANDS))], float)


def _at(table, m):
    """Chromaticity from a band table at each brightness, linear between band centres."""
    return np.stack([np.interp(m, BANDS, table[:, c]) for c in range(3)], -1)


def stats(rgb, keep):
    mean = rgb.mean(2)
    p = rgb[keep]
    meds = band_medians(rgb, mean, keep)
    table = _fill(meds)
    dev = np.linalg.norm(_chroma(p) - _at(table, p.mean(-1)), axis=-1)
    s = saturation(p)
    return dict(mean=tuple(float(np.percentile(p.mean(-1), q)) for q in QUANTILES), chroma=meds,
                spread=float(np.median(dev)), mean50=float(np.median(p.mean(-1))), sat50=float(np.median(s)),
                sat90=float(np.percentile(s, 90)))


def team_mask(spm):
    return spm[..., 2] > 128


def team_gain(rgb, team, faction):
    """The factor that brings the team texels' median brightness to the faction's retail one (team50): the house
    colour multiplies 2 x diffuse, retail paints those texels light grey (median 80..157), our bakes came out 64..75
    and the house colour read dull on the bench (CampGradeLook 2026-11-15). 1 without team texels; at most 2.5."""
    if team.sum() < 50:
        return 1.0
    return float(np.clip(FACTIONS[faction]['team50'] / max(np.median(rgb[team].mean(-1)), 1), 0.5, 2.5))


def grade(rgb, body, faction):
    """rgb (h, w, 3) float -> (graded rgb, brightness map f(mean) -> mean) for the texels `body` marks; the rest
    unchanged (the caller maps their brightness with the returned function)."""
    ref = FACTIONS[faction]
    mean = rgb.mean(2)
    src_q = np.percentile(mean[body], QUANTILES)
    src_q = np.maximum.accumulate(src_q + np.arange(len(QUANTILES)) * 1e-3)    # strictly rising for interp
    xs, ys = np.r_[0.0, src_q, 255.0], np.r_[0.0, ref['mean'], max(255.0, ref['mean'][-1])]

    def lift(m):
        return np.interp(m, xs, ys)
    src_table = _fill(band_medians(rgb, mean, body))
    ref_table = _fill(ref['chroma'])
    n = _chroma(rgb)
    dev = n - _at(src_table, mean)
    src_spread = float(np.median(np.linalg.norm(dev[body], axis=-1)))
    k = min(1.0, ref['spread'] / max(src_spread, 1e-6))
    m2 = lift(mean)
    out = (_at(ref_table, m2) + k * dev) * m2[..., None]
    out = np.clip(out, 0, 255)
    return np.where(body[..., None], out, rgb), lift


def check(rgb, spm, faction):
    """[(level, message)]: the body's median brightness, median and 90th-percentile saturation against the
    faction's retail range (TOL slack). 'warn': it will read off-style beside retail units."""
    ref, body = FACTIONS[faction], body_mask(rgb, spm)
    if body.sum() < 100:
        return [('error', f'only {int(body.sum())} body texels (everything team colour, glow or black?)')]
    got = stats(rgb, body)
    found = []
    for key in ('mean50', 'sat50', 'sat90'):
        lo, hi = ref[key + '_range']
        if not lo - TOL[key] <= got[key] <= hi + TOL[key]:
            found.append(('warn', f'{key} {got[key]:.2f} outside {faction} retail {lo:.2f}..{hi:.2f}'))
    team = team_mask(spm) & (rgb.max(2) > 10)
    if team.sum() >= 50:
        lo, hi = ref['team50_range']
        t = float(np.median(rgb[team].mean(-1)))
        if not lo - TOL['mean50'] <= t <= hi + TOL['mean50']:
            found.append(('warn', f'team50 {t:.2f} outside {faction} retail {lo:.2f}..{hi:.2f} (house colour dull / '
                                  'washed out)'))
    return found


def load(path):
    from PIL import Image
    return np.asarray(Image.open(path).convert('RGB'), float)


def measure(ref_dir):
    from PIL import Image
    out = {}
    for faction, names in REFERENCE.items():
        per = []
        for n in names:
            d = load(os.path.join(ref_dir, n + '.png'))
            spm = np.asarray(Image.open(os.path.join(ref_dir, n + '_SPM.png')).convert('RGB').resize(d.shape[1::-1]),
                             float)
            st = stats(d, body_mask(d, spm))
            st['team50'] = float(np.median(d[team_mask(spm)].mean(-1)))
            per.append(st)
        chroma = []
        for b in range(len(BANDS)):
            vals = [p['chroma'][b] for p in per if p['chroma'][b] is not None]
            chroma.append(tuple(round(float(v), 3) for v in np.mean(vals, 0)) if vals else None)
        out[faction] = dict(
            mean=tuple(round(float(v), 1) for v in np.mean([p['mean'] for p in per], 0)), chroma=chroma,
            spread=round(float(np.mean([p['spread'] for p in per])), 4),
            team50=round(float(np.median([p['team50'] for p in per])), 1),
            **{k + '_range': (round(min(p[k] for p in per), 3), round(max(p[k] for p in per), 3))
               for k in ('mean50', 'sat50', 'sat90', 'team50')})
    return out


def main(argv):
    if argv[:1] == ['measure']:
        import importlib.util
        spec = importlib.util.spec_from_file_location('labpaths', os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'campaign', 'labpaths.py')))
        labpaths = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(labpaths)
        for faction, v in measure(os.path.join(labpaths.WORK, 'reference')).items():
            print(f'    {faction!r}: {v!r},')
        return 0
    if argv[:1] == ['check'] and len(argv) == 4:
        found = check(load(argv[1]), load(argv[2]), argv[3])
        for lv, msg in found:
            print(lv, msg)
        print('ok' if not found else f'{len(found)} finding(s)')
        return 1 if found else 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
