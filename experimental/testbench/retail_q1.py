r"""Retail acceptance question 1 (ADR 0026 item 2, pixel route): the first Allied mission's starting squad, ordered by
a right click on a world point, walks there -- how long until it stands there, and where does it stop?

It checks two things at once: the bench's world <-> screen mapping on a retail map (calib.py retail_cam/<map>.json:
the squad must end where the world click said, not where a flat island mapping would put it) and one key time of the
retail game (the walk's duration), which the simulator is to reproduce once it can play the map.

  python -X utf8 experimental/testbench/retail_q1.py            -> work/testbench/retail_q/a01_q1.json (+ frames)

The squad is found by colour (the team's blue on the lawn and road, inside ROI: the fence posts, the pavilion and the
HUD are outside it); selected by a box over the start formation; the camera stays at the mission's start camera.
"""
import json
import os
import time

import numpy as np

import calib  # this folder: first on the path when run as a script (guard G4: no sys.path edits)
import harness

OUT = os.path.join(calib.ROOT, 'work', 'testbench', 'retail_q')
ROI = (230, 262, 1000, 700)               # screen box where only the squad is blue (start camera)
SELECT = (380, 270, 780, 520)             # screen box over the start formation
TARGET_SCREEN = (900, 500)                # where the order is given: the road east of the lawn
STEP = 0.5                                # mission seconds asked between samples (a frame and the pause take ~1.5 more)
ARRIVE_R = 30.0                           # world units the squad's centre from the target that count as there (it stops
#                                           ~18 off: six units spread round the point; at 53 it was still walking)
MAX_S = 40.0


def squad(img):
    """(count, mean u, mean v) of the team-blue pixels inside ROI."""
    a = np.asarray(img.convert('RGB'), dtype=np.int16)[ROI[1]:ROI[3], ROI[0]:ROI[2]]
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = (b > 110) & (r < 95) & (g < 95) & (b - r > 60) & (b - g > 50)
    ys, xs = np.nonzero(m)
    if len(ys) < 20:
        return 0, None, None
    return int(len(ys)), float(xs.mean() + ROI[0]), float(ys.mean() + ROI[1])


def run(map_name=harness.RETAIL_DEFAULT):
    s = harness.Session()
    rows = []
    try:
        s.start('', hold=True, retail_map=map_name)
        h = s.window()
        time.sleep(1.0)
        s.frame('start')
        s.pause()
        target = s.to_world(*TARGET_SCREEN)
        s.resume()
        harness.drag(h, *SELECT)
        time.sleep(0.4)
        harness.click(h, *s.to_screen(*target), True)
        t_order = s.second()
        arrived = None
        for _ in range(int(MAX_S / STEP)):
            s.run_for(STEP)
            fid, img = s.frame('walk')
            n, u, v = squad(img)
            wx, wy = s.to_world(u, v) if n else (None, None)
            d = float(np.hypot(wx - target[0], wy - target[1])) if n else None
            rows.append(dict(frame=fid, second=s.frames[-1]['second'], blue_px=n, screen=[u, v], world=[wx, wy],
                             to_target=d))
            if d is not None and d <= ARRIVE_R:       # the first sample near the target: the walk took at most so long
                arrived = rows[-1]['second']
                break
        s.pause()
        res = dict(map=map_name, order_at=t_order, target_world=list(target), target_screen=list(TARGET_SCREEN),
                   arrived_at=arrived, walk_s_at_most=None if arrived is None else round(arrived - t_order, 1),
                   sample_gap_s=round(float(np.mean(np.diff([r['second'] for r in rows]))), 1) if len(rows) > 1 else None,
                   final_to_target=rows[-1]['to_target'], samples=rows, run_dir=s.run_dir,
                   mapping=dict(profile=bool(calib.PROFILE), start_view=list(calib.START_VIEW)))
    finally:
        s.stop()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'a01_q1.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    return res


if __name__ == '__main__':
    r = run()
    print({k: v for k, v in r.items() if k != 'samples'})
    for row in r['samples']:
        print(row)
