r"""World -> screen calibration of the bench camera at the CNV mission start (maps built on CampNew18's island:
the camera starts at its InitialCameraPosition), so bench clicks and box selections are computed, not guessed.

Two frames 3 s after the mission start (run_bench.ps1 -Nav), built with make_campnew28.py: CNV_CALIB=base (no
markers) and CNV_CALIB=grid (a 5 x 5 grid of Guardians, make_campnew28.CALIB_GRID). Their difference gives the
markers on screen; rows / columns are matched to the grid (rows top to bottom = north to south, columns left to
right = west to east; points off screen are skipped) and a homography (ground plane -> screen) is fitted.

  python -I experimental/testbench/calib.py fit [base.png grid.png]   -> work/testbench/calib.json
  python -I experimental/testbench/calib.py screen <x> <y>            world -> screen
  python -I experimental/testbench/calib.py world <u> <v>             screen -> world

From code: calib.world_to_screen(x, y), calib.screen_to_world(u, v).
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DIR = os.path.join(ROOT, 'work', 'testbench', 'calib')
OUT = os.path.join(ROOT, 'work', 'testbench', 'calib.json')
UI = [(1040, 0, 1280, 270), (1100, 575, 1280, 720), (0, 0, 140, 100), (0, 650, 200, 720),
      (345, 135, 835, 175)]                                  # minimap, panels, caption bar: never markers


def blobs(base, grid, thr=60, min_area=120):
    a = np.asarray(Image.open(base).convert('RGB'), dtype=np.int16)
    b = np.asarray(Image.open(grid).convert('RGB'), dtype=np.int16)
    mask = np.abs(a - b).sum(axis=2) > thr
    for x0, y0, x1, y1 in UI:
        mask[y0:y1, x0:x1] = False
    m = mask[::2, ::2]                                        # half resolution is plenty
    seen = np.zeros_like(m)
    out = []
    h, w = m.shape
    for y in range(h):
        for x in range(w):
            if m[y, x] and not seen[y, x]:
                stack, pts = [(y, x)], []
                seen[y, x] = True
                while stack:
                    cy, cx = stack.pop()
                    pts.append((cy, cx))
                    for ny in range(cy - 2, cy + 3):          # 5 x 5 neighbourhood joins barrels to bodies
                        for nx in range(cx - 2, cx + 3):
                            if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True
                                stack.append((ny, nx))
                if len(pts) * 4 >= min_area:
                    ys, xs = zip(*pts)
                    out.append((2 * sum(xs) / len(xs), 2 * sum(ys) / len(ys), 4 * len(pts)))
    return out


def homography(world, screen):
    A = []
    for (x, y), (u, v) in zip(world, screen):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.asarray(A, float))
    H = vt[-1].reshape(3, 3)
    return H / H[2, 2]


def _apply(H, x, y):
    p = H @ np.array([x, y, 1.0])
    return float(p[0] / p[2]), float(p[1] / p[2])


# seed: units read off CampNew28 frames by eye (offsets from make_campnew28.A): the two 游隼 and the three Hammers
SEED = [((0, 0), (530, 507)), ((45, 0), (580, 507)), ((-60, 460), (495, 62)), ((0, 460), (563, 62)),
        ((60, 460), (630, 62))]


def fit(base, grid, radius=70):
    """Markers are matched to grid points by nearest prediction (seed homography first, then refitted), not by
    sorting into rows: perspective tilts the rows and units of the base map move between the two runs."""
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
    import make_campnew28 as c28
    pts = [p[:2] for p in blobs(base, grid)]
    ax, ay = c28.A
    H = homography([(ax + dx, ay + dy) for (dx, dy), _ in SEED], [s for _, s in SEED])
    for _ in range(4):
        world, screen = [], []
        for g in c28.CALIB_GRID:
            u, v = _apply(H, *g)
            d = [np.hypot(u - p[0], v - p[1]) for p in pts]
            if d and min(d) < radius:
                world.append(g)
                screen.append(pts[int(np.argmin(d))])
        H = homography(world, screen)
    err = [np.hypot(*np.subtract(_apply(H, *w), s)) for w, s in zip(world, screen)]
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(dict(H=H.tolist(), points=[dict(world=w, screen=[round(s[0], 1), round(s[1], 1)])
                                             for w, s in zip(world, screen)],
                       note='world (map units) -> 1280x720 screen at the CNV mission start camera'), f, indent=1)
    print(f'{len(pts)} blobs, {len(world)} of {len(c28.CALIB_GRID)} grid points matched; residual mean {np.mean(err):.1f} px, '
          f'max {np.max(err):.1f} px -> {OUT}')


def _H():
    with open(OUT, encoding='utf-8') as f:
        return np.asarray(json.load(f)['H'])


def world_to_screen(x, y):
    u, v = _apply(_H(), x, y)
    return round(u), round(v)


def screen_to_world(u, v):
    x, y = _apply(np.linalg.inv(_H()), u, v)
    return round(x, 1), round(y, 1)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'fit':
        fit(*(sys.argv[2:4] or [os.path.join(DIR, 'base.png'), os.path.join(DIR, 'grid.png')]))
    elif cmd == 'screen':
        print(*world_to_screen(float(sys.argv[2]), float(sys.argv[3])))
    elif cmd == 'world':
        print(*screen_to_world(float(sys.argv[2]), float(sys.argv[3])))
