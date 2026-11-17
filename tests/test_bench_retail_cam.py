"""The bench on a retail campaign map without the game: the map is read from the game's MapsCampaign.big by name, its
borders come from the map itself, and the camera fitted from landmarks on a frame of it (retail_cam/<map>.json) puts
those landmarks where they were drawn (bench 2026-11-08, first Allied mission)."""
import importlib.util
import json
import os

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# loaded by file (guard G4: no new sys.path edits); harness puts its own folder on the path
_spec = importlib.util.spec_from_file_location('harness', os.path.join(ROOT, 'experimental', 'testbench', 'harness.py'))
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)
import calib  # noqa: E402  (on the path now)

A01 = harness.RETAIL_DEFAULT


@pytest.fixture(autouse=True)
def _island_camera_after():
    yield
    calib.set_profile(None)


def test_the_fitted_camera_reproduces_its_landmarks():
    assert calib.set_profile(A01)
    with open(calib.profile_path(A01), encoding='utf-8') as f:
        d = json.load(f)
    p = [*d['pinhole']['look_at'], np.radians(d['pinhole']['pitch_deg']), d['pinhole']['distance'],
         d['pinhole']['focal_px']]
    for q in d['points']:
        # raised landmarks (fence post tops) are drawn above their ground point: the flat mapping is that point's ground
        u, v = calib.world_to_screen(*q['world'])
        want = calib.pinhole(p, *q['world'])
        assert abs(u - want[0]) <= 1 and abs(v - want[1]) <= 1          # H is the pinhole's ground plane
        top = calib.pinhole(p, *q['world'], z=d['height'])
        assert abs(top[0] - q['screen'][0]) <= 12 and abs(top[1] - q['screen'][1]) <= 12
    assert d['residual_px']['rms'] <= 5


def test_a_minimap_jump_moves_the_view_over_the_ground():
    calib.set_profile(A01)
    x, y = calib.START_VIEW
    assert calib.world_to_screen_at(x + 200, y - 100, (x + 200, y - 100)) == calib.world_to_screen(x, y)


def test_the_island_camera_comes_back():
    island = calib.START_VIEW if calib.PROFILE is None else calib.DEFAULT_VIEW
    calib.set_profile(A01)
    assert calib.START_VIEW != island
    assert calib.set_profile(None) is False
    assert calib.START_VIEW == island


def test_no_fitted_camera_for_a_map_leaves_the_island_one():
    assert calib.set_profile('camp_a02_no_such') is False and calib.PROFILE is None


@pytest.mark.skipif(not os.path.exists(r'C:\Program Files (x86)\Steam\steamapps\common\Command and Conquer Red Alert 3\Data\MapsCampaign.big'),
                    reason='needs the game files')
def test_the_map_and_its_borders_are_read_from_the_game_files_by_name():
    borders = harness.retail_borders(A01)
    assert borders[0][1] == (0.0, 0.0, 4750.0, 4750.0)
    assert (0.0, 950.0, 2700.0, 3460.0) in [b for _, b in borders]            # the playable area the minimap draws
    ground = calib.Ground(A01)                                                # by name, not a mod folder
    assert (ground.w, ground.h, ground.border) == (575, 575, 50)
    assert abs(ground.at(1500, 1500) - ground.at(400, 1700)) < 1               # a flat map: no height lift
