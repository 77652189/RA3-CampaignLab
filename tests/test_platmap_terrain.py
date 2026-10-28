"""The platform generator's terrain words (experimental/campaign/platmap.py; docs/design/principles.md P24-P27,
docs/design/teardowns/terrain.md): blocks with a use and the lint that holds a map to them (at most a quarter of the
ground one can walk to in no block, no backdrop one can walk to), gaps measured, wall lines with openings, a map's
strongpoints published to the missions."""
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
import platmap  # noqa: E402
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
