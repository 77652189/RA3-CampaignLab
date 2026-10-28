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
    # the specks would look like a line of their own; with no box under them (since 2026-10-27) they are none
    assert not counters.glyphs(img, counters.line_box(3))
    # which lines read() reads (the digits themselves need the templates in work/, not in git)
    monkeypatch.setattr(counters, 'read_line', lambda img, box: box[1])
    assert counters.read(img, 2) == [counters.line_box(0)[1], counters.line_box(1)[1]]


def test_bright_ground_under_the_counters_is_no_line():
    """Bench 2026-10-27 (CampLock): sand under the last counter, bright as text and with no box under it, read as
    a line of its own -- the two counters slid a line down and read "100 7"."""
    img = frame([(24, 32), (24, 40)])
    a = np.asarray(img).copy()
    x, y, *_ = counters.line_box(2)
    for s in (0, 6, 12, 20, 26):                # sand patches where a third line's label and value would be
        a[y + 2:y + 13, s:s + 4] = SAND
    img = Image.fromarray(a)
    assert counters.glyphs(img, counters.line_box(0)) and not counters.glyphs(img, counters.line_box(2))


def test_sand_as_tall_as_the_line_past_the_value_is_no_digit():
    """Bench 2026-10-27 (CampSceneLook, a short line's "0" read as 6): right past the value, sand as tall as the line
    with only its top pixel dark (the box of the line above), then shadow: a 5-px island, no stroke."""
    img = frame([(24, 32)])
    a = np.asarray(img).copy()
    x, y, *_ = counters.line_box(0)
    a[y:y + counters.HEIGHT, 32:60] = BOX       # the box goes on a little, then shadow as dark
    a[y + 1:y + counters.HEIGHT, 39:44] = SAND
    img = Image.fromarray(a)
    assert [(s, e) for s, e, _ in counters.glyphs(img, counters.line_box(0))] == [(24, 32)]


def test_a_countdown_under_the_counters_is_skipped(monkeypatch):
    """Bench 2026-10-27 (S5 trap): a countdown shown after the counters stands below them ("援军到达 4:13"); its
    colon (two dots, a gap between) marks it, wherever it stands."""
    img = frame([(24, 32), (24, 30)])
    a = np.asarray(img).copy()
    x, y, *_ = counters.line_box(1)
    a[y:y + counters.HEIGHT, 30:52] = BOX       # the second line's value: "4" (24-30), ":" (32-34), "1" (36-40)
    a[y + 3:y + 6, 32:34] = a[y + 9:y + 12, 32:34] = TEXT
    a[y + 1:y + 14, 36:40] = TEXT
    img = Image.fromarray(a)
    assert counters.countdown(counters.glyphs(img, counters.line_box(1)))
    assert not counters.countdown(counters.glyphs(img, counters.line_box(0)))
    monkeypatch.setattr(counters, 'read_line', lambda img, box: box[1])
    assert counters.read(img, 1) == [counters.line_box(0)[1]]
