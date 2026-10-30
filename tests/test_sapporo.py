"""The A4 rework's map (experimental/cnv/maps/sapporo.py, docs/design/a4-redesign.md 第 3 步): each way the ice is to
shut is the only way, on the walking grid the lint uses -- shut a courtyard's gate and nobody gets into it; shut the
back lane's two ramps and its depot is out of reach; shut the three ways from the north (the north mouth, the east
street, plaza 3's gate) and the north bridge, and the north camp cannot reach the road. And the player starts at the
corridor's west end, not at the template's default (island.py)."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
import platmap  # noqa: E402
from maps import island, sapporo as sp  # noqa: E402

_E, _ = platmap.heights(sp.LAYOUT, *platmap.CONTAINER)
WALK = platmap.walkable(sp.LAYOUT, sp.OBJECTS, platmap.CONTAINER, _E)


def shut(*places, half=90.0):
    """The walking grid with a square of `half` taken out round each (x, y)."""
    w = WALK.copy()
    x, y = platmap._cells(platmap.CONTAINER)
    for px, py in places:
        w &= ~((abs(x - px) <= half) & (abs(y - py) <= half))
    return w


def reached(walk, site):
    s = sp.SITES['start']
    got = platmap.reach(walk, s.x, s.y)
    b = platmap.CONTAINER[2]
    p = sp.SITES[site]
    return bool(got[int(round(p.y / platmap.CELL)) + b, int(round(p.x / platmap.CELL)) + b])


def test_the_map_passes_its_lint():
    assert not platmap.lint(sp.LAYOUT, sp.SITES, sp.OBJECTS, sp.SCENERY)


def test_every_place_a_level_goes_is_reached_from_the_start():
    for name in sp.SITES:
        if sp.SITES[name].r < 1000 and name != 'sea east':
            assert reached(WALK, name), name


def test_a_shut_gate_shuts_its_courtyard():
    for k in (1, 2, 3):
        assert reached(WALK, f'plaza {k}')
        assert not reached(shut(sp.SITES[f'gate {k}'][:2] if isinstance(sp.SITES[f'gate {k}'], tuple)
                                else (sp.SITES[f'gate {k}'].x, sp.SITES[f'gate {k}'].y)), f'plaza {k}'), k


def test_the_back_lane_is_only_its_two_ramps():
    up, down = sp.RAMPS[0], sp.RAMPS[1]
    assert not reached(shut(up.low, down.low, half=110.0), 'lane depot')
    assert reached(shut(up.low, half=110.0), 'lane depot') and reached(shut(down.low, half=110.0), 'lane depot')


def test_the_north_comes_to_the_road_by_its_mouths():
    """The north mouth and the east street (plaza 3's gate, the third way in the redesign, lets out the troops in
    its own courtyard: a shut courtyard, above); the north bridge goes round by the harbour."""
    ways = [(sp.SITES[n].x, sp.SITES[n].y) for n in ('north mouth', 'east mouth', 'north bridge')]
    assert not reached(shut(*ways), 'north camp')
    for k in range(3):                          # any one of them open is a way
        assert reached(shut(*(w for j, w in enumerate(ways) if j != k)), 'north camp'), k


def test_the_convoy_parks_between_two_approaches():
    """Stopped at the halt (its lead entering the halt's circle, then rolling up to ROLL on), all three trucks (TRAIN
    from first to last) stand past plaza 2's approach and short of plaza 3's: a truck left on an approach is held
    there by that plaza's troops for good once the ice melts (bench 2026-10-28, a4 win)."""
    TRAIN, ROLL = 120.0, 50.0
    halt, a2, a3 = (sp.SITES[k] for k in ('halt', 'approach 2', 'approach 3'))
    assert halt.x - halt.r - TRAIN > a2.x + a2.r
    assert halt.x - halt.r + ROLL < a3.x - a3.r


def test_its_own_start():
    assert (sp.SITES['start'].x, sp.SITES['start'].y) == sp.START != island.START
    assert sp.START[0] - sp.BORDERS['corridor'][0] < 200          # the map's edge behind the player (P17)
    assert np.isclose(sp.SITES['start'].y, sp.ROAD_Y)
