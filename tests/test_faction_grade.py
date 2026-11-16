"""faction_grade.py: a bake painted like the faction's retail vehicles passes check(), each kind of off-style bake is
caught, and grade() brings the off-style ones back into range (a checker that has never caught anything proves
nothing -- test_check_model.py's rule)."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'units'))
import faction_grade  # noqa: E402

SIZE = 128


def bake(base, spread=25.0, sat_boost=0.0, seed=1):
    """A texture of noisy panels around `base` (r, g, b): brightness varies, chroma follows base; sat_boost pushes
    every texel away from grey. Returns rgb and an SPM with no team colour or glow."""
    rng = np.random.default_rng(seed)
    base = np.array(base, float)
    shade = rng.uniform(0.35, 1.9, (SIZE, SIZE, 1)) + rng.normal(0, 0.05, (SIZE, SIZE, 3))
    rgb = base * shade + rng.normal(0, spread * 0.1, (SIZE, SIZE, 3))
    if sat_boost:
        m = rgb.mean(2, keepdims=True)
        rgb = m + (rgb - m) * (1 + sat_boost)
    return np.clip(rgb, 12, 255), np.zeros((SIZE, SIZE, 3))


def retail_like(faction):
    ref = faction_grade.FACTIONS[faction]
    mid = np.array(ref['chroma'][1]) * ref['mean'][3]
    return bake(mid)


def keys(found):
    return {m.split()[0] for _, m in found}


def test_retail_like_bakes_pass():
    for faction in faction_grade.FACTIONS:
        rgb, spm = retail_like(faction)
        assert faction_grade.check(rgb, spm, faction) == [], faction


def test_too_bright_is_caught():
    rgb, spm = retail_like('soviet')
    assert 'mean50' in keys(faction_grade.check(np.clip(rgb * 2.2, 0, 255), spm, 'soviet'))


def test_too_saturated_is_caught():
    rgb, spm = bake((60, 90, 200), sat_boost=0.8)          # GPT's clean saturated paint
    assert {'sat50', 'sat90'} & keys(faction_grade.check(rgb, spm, 'allied'))


def test_too_grey_is_caught():
    rgb, spm = bake((90, 90, 90), spread=2)
    assert {'sat50', 'sat90'} & keys(faction_grade.check(rgb, spm, 'soviet'))


def test_all_team_colour_is_an_error():
    rgb, spm = retail_like('soviet')
    spm[..., 2] = 255
    assert faction_grade.check(rgb, spm, 'soviet')[0][0] == 'error'


def test_dull_team_colour_is_caught_and_team_gain_fixes_it():
    rgb, spm = retail_like('soviet')
    spm[:40, :, 2] = 255                                   # team texels, painted dark grey as our bakes came out
    rgb[:40] = 66
    assert 'team50' in keys(faction_grade.check(rgb, spm, 'soviet'))
    team = faction_grade.team_mask(spm)
    rgb[team] *= faction_grade.team_gain(rgb, team, 'soviet')
    assert faction_grade.check(rgb, spm, 'soviet') == []


def test_grade_brings_off_style_bakes_into_range():
    for base, faction in (((150, 150, 150), 'soviet'), ((60, 90, 200), 'allied'), ((200, 120, 60), 'japan')):
        rgb, spm = bake(base, sat_boost=0.5)
        body = faction_grade.body_mask(rgb, spm)
        graded, _ = faction_grade.grade(rgb, body, faction)
        assert faction_grade.check(graded, spm, faction) == [], (base, faction)


def test_grade_keeps_accents_and_leaves_other_texels():
    rgb, spm = bake((90, 95, 70))
    rgb[:8, :8] = (220, 110, 30)                           # an orange light
    spm[100:, 100:, 2] = 255                               # team colour: not body
    body = faction_grade.body_mask(rgb, spm)
    graded, lift = faction_grade.grade(rgb, body, 'soviet')
    r, g, b = graded[:8, :8].mean((0, 1))
    assert r > g > b and r > 1.3 * b                       # still orange
    assert np.array_equal(graded[100:, 100:], rgb[100:, 100:])
    assert lift(np.array([0.0]))[0] == 0.0 and np.all(np.diff(lift(np.linspace(0, 255, 50))) >= 0)
