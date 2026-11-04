"""terrain_rules (experimental/campaign): the rules a terrain edit follows (docs/engine/terrain.md), held to the writers
we already have (platmap, newmap, mapterrain) so the editor and the generators cannot drift apart."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experimental' / 'campaign'))

import mapterrain  # noqa: E402
import newmap  # noqa: E402
import platmap  # noqa: E402
import terrain_rules as tr  # noqa: E402

W = newmap.WATERLINE


def _ramp(rise_per_cell, n=40, base=340.0):
    """A field rising along i by `rise_per_cell` from column 10 to 30, flat elsewhere."""
    e = np.full((n, n), base)
    for i in range(n):
        e[:, i] = base + rise_per_cell * min(max(i - 10, 0), 20)
    return e


def test_units_follow_the_game_scale():
    # the game: world height = raw * 0.0390625; ours = raw / 16
    assert tr.RAW_PER_OURS == mapterrain.SCALE
    assert abs(1 / tr.RAW_PER_WORLD - 0.0390625) < 1e-12
    assert tr.world(16.0) == 10.0 and abs(float(tr.ours(tr.world(7.3))) - 7.3) < 1e-9
    assert tr.CELL == mapterrain.CELL == platmap.CELL


def test_passability_is_the_rule_the_writers_use():
    assert tr.STEEP == platmap.STEEP
    rng = np.random.default_rng(3)
    e = 340 + np.cumsum(rng.normal(0, 4, (30, 30)), axis=1)
    assert np.allclose(tr.slope(e), platmap.slope_of(e))
    assert (tr.passable(e, W) == ((e > W + 10) & (platmap.slope_of(e) <= platmap.STEEP))).all()


def test_a_ramp_stays_passable_and_a_cliff_does_not():
    gentle, cliff = _ramp(platmap.RAMP_MAX), _ramp(platmap.STEEP + 1)
    assert tr.passable(gentle, W)[20, 10:31].all()
    assert not tr.passable(cliff, W)[20, 12:29].any()
    assert tr.impassable_bits(cliff, W)[20, 12:29].all()


def test_flat_enough_is_in_world_units():
    e = np.full((20, 20), 340.0)
    assert tr.flat_enough(e, 10, 10, 40)
    lift = tr.ours(tr.BUILD_VARIATION) + 0.5            # just over 3 world units of rise
    e[10, 11] += lift
    assert not tr.flat_enough(e, 10, 10, 40)
    # our FLAT (platmap) is looser than the game's building rule: 8 ours = 5 world > 3
    assert tr.world(platmap.FLAT) > tr.BUILD_VARIATION


def test_an_edit_recomputes_field_0_only_round_the_change():
    e = np.full((30, 30), 340.0)
    bits = np.zeros((30, 30), bool)
    bits[0, 0] = True                                    # a hand-painted cell far away stays
    changed = np.zeros((30, 30), bool)
    changed[15, 15] = True
    e[15, 15] += 30.0                                    # a spike: its four neighbours turn steep too
    new = tr.apply_edit(e, bits, changed, W)
    assert new[0, 0] and new[15, 15] and new[15, 14] and new[14, 15]
    assert not new[13, 13]
    assert tr.edit_region(changed).sum() == 5


def test_must_follow_names_field_0_and_the_heights():
    names = [k for k, _ in tr.MUST_FOLLOW]
    assert names[0] == 'HeightMapData.elev' and 'BlendTileData field 0' in names
    assert tr.FIELDS[tr.IMPASSABLE] == 'impassable' and len(tr.FIELDS) == 8
