"""Reachability uses the same snapped, eight-connected grid as Ground.way."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('simbench', ROOT / 'experimental/cnv/simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)
from sim import Ground  # noqa: E402


def terrain(cells):
    height = np.repeat(np.repeat(np.asarray(cells, bool), 2, axis=0), 2, axis=1)
    # A flat, dry heightmap with explicit impassable cells.
    return Ground(SimpleNamespace(DIMS=(*height.shape[::-1], 0), WATERLINE=320,
                                  ground=lambda: SimpleNamespace(e=np.full(height.shape, 350)),
                                  impassable=lambda: ~height))


def assert_way(ground, start, end, expected, closest=False):
    p, q = ground.world(start), ground.world(end)
    assert (ground.way('ground', p, q, closest) is not None) is expected
    assert ground.can_way('ground', p, q, closest) is expected


def test_reach_snaps_to_the_nearest_cell_across_a_wall():
    ground = terrain([[1, 0, 0, 1, 1]] * 3)
    # Column 2 is blocked and closer to column 3 than column 0.
    assert_way(ground, (1, 4), (1, 2), True)
    assert_way(ground, (1, 0), (1, 2), False)


@pytest.mark.parametrize('end, expected', [((1, 2), True), ((1, 20), False)])
def test_reach_closest_still_needs_both_snapped_endpoints(end, expected):
    ground = terrain([[1, 0, 1]] * 3)
    start = (1, 0)
    assert_way(ground, start, end, False)
    assert_way(ground, start, end, expected, closest=True)
    if expected:
        assert ground.way('ground', ground.world(start), ground.world(end), True) == []


def test_reach_rebuilds_components_when_blocks_change():
    ground = terrain([[1, 1, 1]] * 3)
    p, q = (1, 0), (1, 2)
    assert_way(ground, p, q, True)
    assert ground.set_blocks([(*ground.world((1, 1)), np.pi / 2, 60, 20)])     # not thinner than a CELL (covered)
    assert_way(ground, p, q, False)
    assert ground.set_blocks([])
    assert_way(ground, p, q, True)


def test_only_a_measured_thin_bar_shuts_cells_by_their_centres():
    """A 6-thick bar on the cells' points: ours shuts them (review vv #2), a measured prop's (BARS, `centres`) misses
    every CELL centre and leaves the way open (bench 11-22 engine_block gr)."""
    ground = terrain([[1, 1, 1]] * 3)
    p, q = (1, 0), (1, 2)
    assert ground.set_blocks([(*ground.world((1, 1)), np.pi / 2, 60, 6, False)])
    assert_way(ground, p, q, False)
    assert ground.set_blocks([(*ground.world((1, 1)), np.pi / 2, 60, 6, True)])
    assert_way(ground, p, q, True)


def test_the_ai_reach_of_infantry_is_on_the_foot_grid_its_moves_use():
    """A fence that holds only infantry (set_blocks' foot) across the way: the AI's reach says no for a conscript and
    yes for a tank (review 1126d P2: it asked 'ground' while the move went on 'foot')."""
    from engine.ai.core import Brain
    ground = terrain([[1, 1, 1]] * 3)
    assert ground.set_blocks([], foot=[(*ground.world((1, 1)), np.pi / 2, 60, 20)])
    (x, y), q = ground.world((1, 0)), ground.world((1, 2))
    me = SimpleNamespace(world=SimpleNamespace(ground=ground))
    for kinds, expected in ((['INFANTRY'], False), (['VEHICLE'], True)):
        u = SimpleNamespace(body=SimpleNamespace(surface='ground', kinds=kinds, alive=True, x=x, y=y, weapons=[]))
        assert Brain.reach(me, None, u, q, 'QuickDoesPathExist') is expected


def test_reach_can_step_diagonally_between_two_blocked_cells():
    ground = terrain([[1, 0], [0, 1]])
    assert_way(ground, (0, 0), (1, 1), True)
