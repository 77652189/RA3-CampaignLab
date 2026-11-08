r"""What ground a scene's picture shows (letterbox on): fits a homography ground -> screen from the frames of
checks/engine_letterbox.py ('g': a 7 x 5 grid of guardians, 150 / 125 units apart, teleported in at once while the
scene's camera stands on C), and prints the picture band's ground: the width at its top / middle / bottom row, how far
it reaches north and south of the camera centre (model.LETTERBOX_BAND, 2026-11-07).

  python -I -X utf8 experimental/testbench/letterbox_fit.py <run dir> <frame before> <frame after>
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'cnv'))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'cnv', 'checks'))
import calib  # noqa: E402

C = (2830.0, 2225.0)
COLS = [-450.0, -300.0, -150.0, 0.0, 150.0, 300.0, 450.0]
ROWS = [-250.0, -125.0, 0.0, 125.0, 250.0]
GRID = [(C[0] + dx, C[1] + dy) for dy in ROWS for dx in COLS]
BAND = (90, 630)                                  # the picture's rows (1280 x 720, bars above and below)


def main(run, before, after, mod='CampLbxG', radius=90):
    pts = [p[:2] for p in calib.blobs(os.path.join(run, before), os.path.join(run, after))]
    ground = calib.Ground(mod)
    h0 = ground.at(*C)
    use = [g for g in GRID if abs(ground.at(*g) - h0) < 6]           # flat as the camera centre: heights move the picture
    cx, cy = calib.screen_to_world(640, 345)                           # the seed: the play camera's fit, centred on C
    H = None
    for i in range(8):
        radius = (90, 90, 60, 45, 35, 30, 30, 30)[i]                 # the fit tightens as it settles
        world, screen = [], []
        for g in use:
            u, v = calib.world_to_screen(g[0] - C[0] + cx, g[1] - C[1] + cy) if H is None else calib._apply(H, *g)
            d = [np.hypot(u - p[0], v - p[1]) for p in pts]
            if d and min(d) < radius and sorted(d)[1:2] != [min(d)]:
                world.append(g)
                screen.append(pts[int(np.argmin(d))])
        H = calib.homography(world, screen)
    err = [np.hypot(*np.subtract(calib._apply(H, *w), s)) for w, s in zip(world, screen)]
    print(f'{len(pts)} blobs, {len(world)} of {len(use)} flat grid points matched, residual mean {np.mean(err):.1f} px, '
          f'max {np.max(err):.1f} px')
    Hi = np.linalg.inv(H)

    def w(u, v):
        x, y = calib._apply(Hi, u, v)
        return x - C[0], y - C[1]

    for v in (0, BAND[0], 225, 360, 495, BAND[1], 720):
        l, r = w(0, v), w(1280, v)
        print(f'row {v}: x {l[0]:.0f} .. {r[0]:.0f} (width {r[0] - l[0]:.0f}), y {l[1]:.0f} (north +)')
    n, s = w(640, BAND[0])[1], w(640, BAND[1])[1]
    print(f'band: north {n:.0f}, south {s:.0f} of the camera centre C -> {n - s:.0f} tall, middle {(n + s) / 2:+.0f}; '
          f'the guardian at C is drawn at {[round(x) for x in calib._apply(H, *C)]}')


if __name__ == '__main__':
    main(*sys.argv[1:4])
