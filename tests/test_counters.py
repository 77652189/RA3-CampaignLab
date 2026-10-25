"""The bench's counter reader (experimental/testbench/counters.py) on drawn frames: a counter line's value ends with
its dark box (bright ground past it is no digit), and a speck below the counters does not slide the lines."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'testbench'))
import counters  # noqa: E402

GRASS, SAND, BOX, TEXT = (140, 150, 50), (215, 205, 120), (40, 40, 40), (255, 255, 120)


def frame(lines, speck_line=None):
    """A frame with `lines` counter lines: each a dark box from x 4, a label glyph at 10-18 and a value glyph at
    (x0, x1) a space after it, the box ending 6 px after the value, then sand as bright as the text in patches (as
    the festival map's, 2026-10-25); grass everywhere else. The glyphs are solid: no dark between their strokes,
    only the box's rows above and below."""
    a = np.zeros((720, 1280, 3), np.uint8)
    a[:] = GRASS
    for k, (x0, x1) in enumerate(lines):
        x, y, *_ = counters.line_box(k)
        a[y:y + counters.HEIGHT, 4:x1 + 6] = BOX
        for g0, g1 in ((10, 18), (x0, x1)):
            a[y + 1:y + 14, g0:g1] = TEXT
        for s in range(x1 + 10, x1 + 30, 5):     # patches of sand 3 px wide, 2 px apart
            a[y + 3:y + 12, s:s + 3] = SAND
    if speck_line is not None:
        x, y, *_ = counters.line_box(speck_line)
        a[y + 2:y + 12, 18] = a[y + 2:y + 12, 28] = SAND     # specks where a counter line would start
    return Image.fromarray(a)


def test_the_value_ends_with_its_box():
    img = frame([(24, 32)])
    # the ground right of the box is as bright as the text: before 2026-10-25 it read as more digits
    assert [(s, e) for s, e, _ in counters.glyphs(img, counters.line_box(0))] == [(24, 32)]


def test_a_speck_below_the_counters_does_not_slide_them(monkeypatch):
    img = frame([(24, 32), (24, 40)], speck_line=3)
    assert counters.glyphs(img, counters.line_box(3))          # the specks look like a line of their own
    # which lines read() reads (the digits themselves need the templates in work/, not in git)
    monkeypatch.setattr(counters, 'read_line', lambda img, box: box[1])
    assert counters.read(img, 2) == [counters.line_box(0)[1], counters.line_box(1)[1]]
