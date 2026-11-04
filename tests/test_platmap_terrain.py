"""The platform generator's terrain words (experimental/campaign/platmap.py; docs/design/principles.md P24-P27,
docs/design/teardowns/terrain.md): blocks with a use and the lint that holds a map to them (at most a quarter of the
ground one can walk to in no block, no backdrop one can walk to), gaps measured, wall lines with openings, a map's
strongpoints published to the missions."""
import sys
import types
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
import mapterrain  # noqa: E402
import newmap  # noqa: E402
import platmap  # noqa: E402
import terrain_rules as tr  # noqa: E402
from platmap import Block, Gap, Layout, rect  # noqa: E402

START = types.SimpleNamespace(x=500.0, y=500.0, build=0.0)


def island(**kw):
    """Low ground 0..2000 square over the sea, a raised block (1400..1900) with no ramp: walked on, never reached."""
    return Layout(shapes=[rect(0, 0, 2000, 2000, 1, 'island'), rect(1400, 1400, 1900, 1900, 2, 'shut plateau')], **kw)


def problems(layout, objects=()):
    walk = platmap.walkable(layout, objects)
    return platmap.block_lint(layout, {'start': START}, walk) + platmap.gap_lint(layout, walk)


def test_no_blocks_no_block_problems():
    assert problems(island()) == []


def test_ground_in_no_block_is_empty_and_at_most_a_quarter():
    few = island(blocks=[Block((0, 0, 1000, 1000), '后方', 'base')])
    assert any('in no block' in p for p in problems(few))
    most = island(blocks=[Block((0, 0, 2000, 1000), '后方', 'base'), Block((0, 1000, 1300, 2000), '前线', 'camp')])
    use = platmap.block_use(most, {'start': START}, platmap.walkable(most))
    assert use['share']['空地'] <= platmap.EMPTY_MOST and not problems(most)


def test_backdrop_must_be_out_of_reach():
    ok = island(blocks=[Block((0, 0, 2000, 2000), '通道'), Block((1400, 1400, 1900, 1900), '远景', 'plateau')])
    assert not problems(ok)
    bad = island(blocks=[Block((0, 0, 2000, 2000), '通道'), Block((200, 200, 600, 600), '远景', 'lawn')])
    assert any('lawn (远景)' in p for p in problems(bad))


def test_a_use_outside_the_five_is_named():
    assert any("'空闲'" in p for p in problems(island(blocks=[Block((0, 0, 2000, 2000), '空闲')])))


def test_a_gap_between_two_plateaus_is_measured():
    lay = Layout(shapes=[rect(0, 0, 2000, 2000, 1), rect(0, 1000, 900, 1400, 2), rect(1100, 1000, 2000, 1400, 2)])
    got = platmap.gap_width(platmap.walkable(lay), 1000, 1200)
    assert 120 <= got <= 200                    # 200 between the shapes, the cliffs' soft edges take a little
    lay.gaps = [Gap(1000, 1200, got, 'street')]
    assert not problems(lay)
    lay.gaps = [Gap(1000, 1200, got + 100, 'street')]
    assert any('gap street' in p for p in problems(lay))


def test_a_wall_line_leaves_its_opening_and_bars_the_rest():
    pieces = platmap.wall_line([(200, 1000), (1800, 1000)], gaps=[(1000, 1000, 120)])
    Obj = types.SimpleNamespace
    objs = [Obj(template=t, x=x, y=y, angle=a, flags=None) for t, x, y, a in pieces]
    assert all(abs(o.x - 1000) >= 60 + 30 - 1e-6 for o in objs)          # no piece reaches into the opening
    walk = platmap.walkable(Layout(shapes=[rect(0, 0, 2000, 2000, 1)]), objs)
    assert abs(platmap.gap_width(walk, 1000, 1000) - 120) <= platmap.GAP_SLACK
    assert platmap.gap_width(walk, 600, 1000) == 0                        # on the wall: shut


def test_festival_gates_as_wide_as_their_ramp():
    from maps import festival
    assert len(festival.LAYOUT.gaps) == 3
    walk = platmap.walkable(festival.LAYOUT, festival.OBJECTS)
    assert not platmap.gap_lint(festival.LAYOUT, walk)


def test_a_mission_names_a_maps_strongpoint():
    from parts import Mission, Obj
    t, x, y, a = platmap.strongpoint(300, 400)
    house = Obj(t, x, y, side='civ', angle=a, name='MAP - Strongpoint Mill', site='map')
    m = Mission(name='T', map=types.SimpleNamespace(__name__='maps.t', STRONGPOINTS={'mill': house}, SITES={}))
    assert m.strongpoint('mill') == 'MAP - Strongpoint Mill'
    with pytest.raises(AssertionError):
        m.strongpoint('tower')


def test_the_retail_ranges_for_the_preview():
    """cnv_preview's TERRAIN lines set a map against the 40 retail maps' quartiles (the design line's table)."""
    import terrainref
    r = terrainref.retail_ranges()
    assert {'chokes_on_main', 'overlook', 'used', 'empty'} <= set(r)
    q1, med, q3 = r['used']
    assert 0.4 < q1 <= med <= q3 < 0.9                  # retail: 59 % of the walkable ground used (terrain.md)


# -- terrain_rules (experimental/campaign): the rules a terrain edit follows (docs/engine/terrain.md), held to
# the writers we already have (platmap, newmap, mapterrain) so the editor and the generators cannot drift apart.
# (Moved here from tests/test_terrain_rules.py: guard G4, one file fewer that edits sys.path.)
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


def test_site_lint_holds_build_and_cast_squares_to_the_game_rule(monkeypatch):
    # platmap.level_enough = terrain_rules.flat_enough in map coordinates: a rise of 6 ours (3.75 world) passes the old
    # FLAT = 8 but not the game's 3 world units; 4 ours (2.5 world) passes both
    b = platmap.CONTAINER[2]
    e = np.full((560, 560), 340.0)
    x = y = 500.0
    i = j = int(round(x / platmap.CELL)) + b
    assert platmap.level_enough(e, x, y, 100.0, b)
    e[j, i + 1] += 4.0
    assert platmap.level_enough(e, x, y, 100.0, b)
    e[j, i + 1] += 2.0                                   # 6 ours in all
    assert platmap.relief(e, x, y, 100.0, b) <= platmap.FLAT
    assert not platmap.level_enough(e, x, y, 100.0, b)
    # lint reports both kinds of site, in world units, on that ground (and a flat one stays quiet)
    from model import Site                               # experimental/cnv is on the path (top of this file)
    monkeypatch.setattr(platmap, 'heights', lambda layout, w, h, bb: (e, []))
    monkeypatch.setattr(platmap, 'walkable', lambda *a, **k: np.ones((560, 560), bool))
    sites = {'b': Site(x, y, 0.0, build=100.0), 'c': Site(x, y, 0.0, cast=50.0), 'f': Site(1500.0, 1500.0, 0.0, build=100.0)}
    got = [p for p in platmap.lint(platmap.Layout(shapes=[]), sites) if p.startswith('site ')]
    assert len(got) == 2 and all('world units' in p for p in got) and not any(p.startswith('site f') for p in got), got


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
