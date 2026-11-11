r"""Retail question 1, where each unit stops (engine line A, round 109): the first Allied mission's squad, ordered as in
retail_q1.py, is let walk and settle (SETTLE seconds after its middle is near the point); then each unit is found as
one blob of team blue and mapped to the world -- each one's distance to the point and the closest pair. Then the
spots rule (sim.HOLD_SPOTS): two units picked one by one and each sent alone to one new point -- do they stand apart?

  python -X utf8 experimental/testbench/retail_q1_spots.py   -> work/testbench/retail_q/a01_q1_spots.json (+ frames)
"""
import json
import os
import time

import numpy as np
from scipy import ndimage

import calib  # this folder: first on the path when run as a script (guard G4: no sys.path edits)
import harness
from retail_q1 import ARRIVE_R, MAX_S, ROI, SELECT, STEP, TARGET_SCREEN, squad
import sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'campaign')))
import labpaths  # noqa: E402

OUT = os.path.join(labpaths.WORK, 'testbench', 'retail_q')
SETTLE = 4.0                     # mission seconds sampled after the middle is near the point
SECOND_SCREEN = (700, 600)       # the two lone orders' point: the lawn south of the start (inside ROI)
MIN_PX = 60                      # a blob smaller than this is shading or a flower, not a unit
DESELECT = (300, 640)            # empty road: a left click there clears the selection (no outlines, bars on the units)


def blobs(img):
    """[(pixels, u, v)] of the team-blue blobs inside ROI, biggest first."""
    a = np.asarray(img.convert('RGB'), dtype=np.int16)[ROI[1]:ROI[3], ROI[0]:ROI[2]]
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = (b > 110) & (r < 95) & (g < 95) & (b - r > 60) & (b - g > 50)
    m = ndimage.binary_dilation(m, iterations=2)
    lab, n = ndimage.label(m)
    out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(ys) >= MIN_PX:
            out.append((int(len(ys)), float(xs.mean() + ROI[0]), float(ys.mean() + ROI[1])))
    return sorted(out, reverse=True)


def placed(s, img, target):
    """The blobs in world units: [{px, world, to_target}], plus the closest pair's distance."""
    rows = []
    for n, u, v in blobs(img):
        wx, wy = s.to_world(u, v)
        rows.append(dict(px=n, screen=[round(u), round(v)], world=[round(wx, 1), round(wy, 1)],
                         to_target=round(float(np.hypot(wx - target[0], wy - target[1])), 1)))
    pair = min((float(np.hypot(a['world'][0] - b['world'][0], a['world'][1] - b['world'][1]))
                for i, a in enumerate(rows) for b in rows[i + 1:]), default=None)
    return rows, None if pair is None else round(pair, 1)


def run(map_name=harness.RETAIL_DEFAULT):
    s = harness.Session()
    res = dict(map=map_name)
    try:
        s.start('', hold=True, retail_map=map_name)
        h = s.window()
        time.sleep(1.0)
        s.frame('start')
        s.pause()
        target = s.to_world(*TARGET_SCREEN)
        second = s.to_world(*SECOND_SCREEN)
        s.resume()
        harness.drag(h, *SELECT)
        time.sleep(0.4)
        harness.click(h, *s.to_screen(*target), True)
        t_order = s.second()
        near = None
        for _ in range(int(MAX_S / STEP)):
            s.run_for(STEP)
            fid, img = s.frame('walk')
            n, u, v = squad(img)
            if n:
                wx, wy = s.to_world(u, v)
                if np.hypot(wx - target[0], wy - target[1]) <= ARRIVE_R:
                    near = s.frames[-1]['second']
                    break
        s.run_for(SETTLE)
        harness.click(h, *DESELECT)
        time.sleep(0.3)
        fid, img = s.frame('settled')
        units, pair = placed(s, img, target)
        mid = squad(img)
        mx, my = s.to_world(mid[1], mid[2]) if mid[0] else (None, None)
        res['group'] = dict(order_at=t_order, near_at=near, settled_frame=fid, target=[round(c, 1) for c in target],
                            middle_to_target=None if mx is None else round(float(np.hypot(mx - target[0],
                                                                                         my - target[1])), 1),
                            units=units, closest_pair=pair)
        # two lone orders to one point: pick the two blobs nearest the point, each alone
        lone = sorted(units, key=lambda r: r['to_target'])[:2]
        for r in lone:
            harness.click(h, *r['screen'])
            time.sleep(0.3)
            harness.click(h, *s.to_screen(*second), True)
            time.sleep(0.3)
        s.run_for(8.0)
        harness.click(h, *DESELECT)
        time.sleep(0.3)
        fid, img = s.frame('lone')
        units2, _ = placed(s, img, second)
        at = sorted(units2, key=lambda r: r['to_target'])[:2]
        res['lone'] = dict(sent=[r['world'] for r in lone], point=[round(c, 1) for c in second], frame=fid,
                           nearest_two=at,
                           their_gap=None if len(at) < 2 else round(float(np.hypot(
                               at[0]['world'][0] - at[1]['world'][0], at[0]['world'][1] - at[1]['world'][1])), 1),
                           units=units2)
        s.pause()
        res['run_dir'] = s.run_dir
    finally:
        s.stop()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'a01_q1_spots.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    return res


if __name__ == '__main__':
    r = run()
    g = r.get('group', {})
    print('group: near_at', g.get('near_at'), 'order_at', g.get('order_at'), 'middle_to_target',
          g.get('middle_to_target'), 'closest_pair', g.get('closest_pair'))
    for u in g.get('units', []):
        print('  ', u)
    lone = r.get('lone', {})
    print('lone: point', lone.get('point'), 'their_gap', lone.get('their_gap'))
    for u in lone.get('nearest_two', []):
        print('  ', u)
    print('run_dir', r.get('run_dir'))
