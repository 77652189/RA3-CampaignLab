"""Read the mission's on-screen counters (DISPLAY_COUNTER) as numbers, so a test reports "s19 乘员在甲板 = 5" as text
instead of a picture to look at.

The counters stand bottom left, one line each from TOP down, LINE px apart (bench 1280x720); only MAX_LINES fit
above the bottom bar (a fifth is cut off). Each line is the label, a space, the value: the value is cut into digit
glyphs (text columns after the label's last gap) and each glyph matched against the digit templates in
work/testbench/nav/digits/, cut once from a map that shows 1234 / 5678 / 90 (build.py digits --calibrate).

  python -I -X utf8 experimental/testbench/counters.py calibrate <frame.png>
  python -I -X utf8 experimental/testbench/counters.py read <frame.png> <lines>
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DIGITS = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'testbench', 'nav', 'digits')
TOP, LINE, HEIGHT = 578, 16, 15                # the first line's top row, the pitch, a line's height
MAX_LINES = 4
LEFT, RIGHT = 0, 330
TEXT = 170                                      # text pixels (yellow or white): red and green both above this
GAP = 4                                         # columns of no text between the label and the value
END_GAP = 12                                    # a wider gap: the line's text has ended
START_BY = 30                                   # a counter line's text starts left of this
MIN_HEIGHT = 6                                  # text columns shorter than this are specks (digits are 13 tall; a
                                                # 1-px sparkle 6 px right of a 0 read as 8, bench 2026-10-21)
BOX_DARK, BOX_END = 90, 4                       # the counters' backing box: darker than this; ends after so many
                                                # columns without it
SIZE = (8, 12)                                # a glyph is compared at this size
CALIBRATION = [1234, 5678, 90]


def line_box(k, n=None):
    """Screen box of counter line k (0 = top)."""
    top = TOP + LINE * k
    return (LEFT, top, RIGHT, top + HEIGHT)


def glyphs(img, box):
    """The value's glyphs on one line: [(x0, x1, mask)] left to right, from the text columns after the last gap."""
    rgb = np.asarray(img.crop(box).convert('RGB')).astype(int)
    a = np.minimum(rgb[:, :, 0], rgb[:, :, 1]) > TEXT
    # the text stands on a dark box, which ends a few px after the value: bright ground beyond it (sand) read as
    # more digits, "0" as 47 (bench 2026-10-25, A4 smash). A box column has some dark pixels (between glyphs:
    # few, 2 columns at most) or, a glyph's stroke filling it, its few other pixels dark; the ground has neither
    # (shadow in spots). The box ends at the first BOX_END columns in a row that are not the box
    rest, deep = ~a, rgb.max(2) < BOX_DARK
    dark = (deep.mean(0) > 0.15) | (rest.any(0) & ((rest & deep).sum(0) > 0.5 * rest.sum(0)))
    for x in range(START_BY, len(dark) - BOX_END):
        if not dark[x:x + BOX_END].any():
            a[:, x:] = False
            break
    cols = a.any(0)
    runs, x = [], 0
    while x < len(cols):
        if cols[x]:
            s = x
            while x < len(cols) and cols[x]:
                x += 1
            ys = np.where(a[:, s:x].any(1))[0]
            if ys[-1] - ys[0] + 1 >= MIN_HEIGHT:    # a sparkle on the ground next to the value is no glyph
                runs.append([s, x])
        x += 1
    if not runs:
        return []
    if runs[0][0] > START_BY:                   # no text where the counters start: terrain, not a counter line
        return []
    groups = [[runs[0]]]
    for r in runs[1:]:
        gap = r[0] - groups[-1][-1][1]
        if gap > END_GAP:                       # past the end of the line's text (sparkles on the water beyond)
            break
        (groups[-1].append(r) if gap < GAP else groups.append([r]))
    if len(groups) < 2:                         # a label and a value, or nothing to read
        return []
    out = []
    for s, e in groups[-1]:
        m = a[:, s:e]
        ys = np.where(m.any(1))[0]
        out.append((s, e, m[ys[0]:ys[-1] + 1]))
    return out


def norm(mask):
    return np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).resize(SIZE)).astype(float) / 255


_tpl = None


def templates():
    global _tpl
    if _tpl is None:
        _tpl = {}
        for d in range(10):
            p = os.path.join(DIGITS, f'{d}.png')
            if os.path.exists(p):
                _tpl[d] = np.asarray(Image.open(p).convert('L')).astype(float) / 255
    return _tpl


def read_line(img, box):
    """The number on a counter line, or None (no glyphs, or no templates yet)."""
    tpl = templates()
    gs = glyphs(img, box)
    if not gs or len(tpl) < 10:
        return None
    digits = []
    for _, _, m in gs:
        g = norm(m)
        digits.append(min(tpl, key=lambda d: np.abs(tpl[d] - g).sum()))
    return int(''.join(map(str, digits)))


def read(img, n):
    """The n counters' values, top to bottom. A countdown the mission shows (DISPLAY_COUNTDOWN_TIMER, "车队出发
    0:50") stands in the same list above the counters (bench 2026-10-24: it pushed them a line down and the top
    counter read 253): the lines with text beyond the n counters are taken as such and skipped. Only the lines
    from the top without a break count: a speck on the ground below the counters (bench 2026-10-25, A4 at s59: a
    1-px column on line 3) slid every reading a line down."""
    lines = 0
    while lines < MAX_LINES and glyphs(img, line_box(lines)):
        lines += 1
    skip = max(0, lines - n)
    return [read_line(img, line_box(k + skip, n)) for k in range(n)]


def calibrate(img):
    """From a frame showing the CALIBRATION counters (top to bottom): the digit templates."""
    os.makedirs(DIGITS, exist_ok=True)
    for k, value in enumerate(CALIBRATION):
        gs = glyphs(img, line_box(k))
        assert len(gs) == len(str(value)), f'line {k}: {len(gs)} glyphs for {value}'
        for d, (_, _, m) in zip(str(value), gs):
            Image.fromarray((norm(m) * 255).astype(np.uint8)).save(os.path.join(DIGITS, f'{d}.png'))
    global _tpl
    _tpl = None
    return read(img, len(CALIBRATION))


if __name__ == '__main__':
    im = Image.open(sys.argv[2]).convert('RGB')
    if sys.argv[1] == 'calibrate':
        print('read back:', calibrate(im))
    else:
        print(read(im, int(sys.argv[3])))
