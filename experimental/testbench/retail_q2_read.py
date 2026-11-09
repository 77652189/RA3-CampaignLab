r"""Reads retail_q2.py's frames (mission menu up): how many objective lines the list shows per mission second.
Green text pixels in the list box = lines shown (about 280 per line at 1280 x 720; it prints the raw count and a rounded
line estimate). Also tells whether a frame is the mission menu at all (the red title bar).

  python -I -X utf8 experimental/testbench/retail_q2_read.py work/testbench/retail_q/a02_idle.json
"""
import json
import os
import sys

import numpy as np
from PIL import Image

LIST = (650, 100, 1090, 320)        # the objectives list box of the mission menu in a 1280 x 720 frame


def lines(img):
    a = np.asarray(img.convert('RGB'), dtype=np.int16)[LIST[1]:LIST[3], LIST[0]:LIST[2]]
    m = (a[..., 1] > 130) & (a[..., 0] < 110) & (a[..., 2] < 110)
    return int(m.sum())


if __name__ == '__main__':
    res = json.load(open(sys.argv[1], encoding='utf-8'))
    for r in res['samples']:
        img = Image.open(os.path.join(res['run_dir'], f"{r['frame']:04d}.png"))
        print(f"{r['second']:6.1f}  green px {lines(img)}")
