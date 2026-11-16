"""experimental/units/readability.py: the pure metric functions (no Blender, no game files)."""
import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('readability', ROOT / 'experimental' / 'units' / 'readability.py')
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def rect(x0, y0, x1, y1, n=64):
    m = np.zeros((n, n), bool)
    m[y0:y1, x0:x1] = True
    return m


def test_iou_basic():
    a = rect(10, 10, 30, 30)
    assert R.iou(a, a) == 1.0
    assert R.iou(a, rect(40, 40, 50, 50)) == 0.0
    assert abs(R.iou(a, rect(20, 10, 40, 30)) - 1 / 3) < 1e-9


def test_centred_makes_shifted_copies_identical():
    a = rect(5, 5, 25, 15)
    b = rect(30, 40, 50, 50)                 # same shape somewhere else
    assert R.iou(a, b) == 0.0
    assert R.iou(R.centred(a), R.centred(b)) == 1.0


def test_best_iou_takes_best_azimuth_and_pairwise_covers_all_pairs():
    wide, tall = rect(10, 28, 54, 36), rect(28, 10, 36, 54)
    ma, mb = {0: wide, 90: tall}, {0: tall, 90: tall}
    v, az = R.best_iou(ma, mb)
    assert v == 1.0 and az == 90
    pw = R.pairwise_iou({'a': ma, 'b': mb, 'c': ma})
    assert set(pw) == {('a', 'b'), ('a', 'c'), ('b', 'c')}
    assert pw[('a', 'c')][0] == 1.0


def test_class_extent_and_median():
    assert R.class_extent([0, 0, 0], [70, 25, 23], 'horizontal') == 70
    assert R.class_extent([0, 0, 0], [6, 21, 24], 'height') == 24
    assert R.median([3, 1, 2]) == 2 and R.median([1, 2, 3, 4]) == 2.5
    assert abs(R.px_size(70) - 70 * R.PPU) < 1e-9


def test_camera_constants_follow_the_measured_ratio():
    assert 50 < R.PITCH_DEG < 53
    assert 1.4 < R.PPU < 1.6


def blue_image(n=32):
    off = np.full((n, n, 3), (150, 120, 90), np.uint8)          # brown-grey paint
    on = off.copy()
    on[8:16, 8:24] = (30, 60, 220)                               # a team-colour patch
    mask = np.ones((n, n), bool)
    return on, off, mask


def test_team_box_is_learned_from_the_patch_and_fraction_matches():
    on, off, mask = blue_image()
    box = R.fit_team_box(on, off, mask)
    assert 150 < box['h'][0] <= box['h'][1] < 190             # blue hue (PIL scale, 170 = blue)
    assert abs(R.team_fraction(on, mask, box) - (8 * 16) / (32 * 32)) < 1e-9
    assert R.team_fraction(off, mask, box) == 0.0
    half = mask.copy()
    half[:, 16:] = False                                      # silhouette halves: only part of the patch inside
    assert abs(R.team_fraction(on, half, box) - (8 * 8) / (32 * 16)) < 1e-9


def test_pass_range_and_answers():
    assert R.pass_range([0.2, 0.05, 0.3]) == (0.05, 0.3)
    assert R.in_range(0.1, (0.05, 0.3)) and not R.in_range(0.4, (0.05, 0.3))
    assert R.score_answer({'1': 'Guardian', '2': 'x'}, {'1': 'guardian', '2': 'athena'}) == (1, 2)
    assert R.parse_json('Here: ```json\n{"1": "a"}\n```') == {'1': 'a'}
    assert R.parse_json('no json') is None


def test_bbox():
    assert R.bbox(rect(3, 4, 10, 12)) == (3, 4, 10, 12)
    assert R.bbox(np.zeros((8, 8), bool)) is None


def test_ingame_team_fraction_uses_the_team_mask_rule():
    """Team paint (blue 65 above red/green) counts; cool dark steel (51, 56, 78, lift 22) does not (tripo_unit.team_mask)."""
    img = np.zeros((10, 10, 3), np.uint8)
    img[:, :5] = (110, 125, 190)
    img[:, 5:] = (51, 56, 78)
    mask = np.ones((10, 10), bool)
    assert R.ingame_team_fraction(img, mask) == 0.5
    assert R.ingame_team_fraction(img, np.zeros((10, 10), bool)) == 0.0
