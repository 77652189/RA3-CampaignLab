"""The bench camera and menu walk without the game: the minimap draws only the playable area (a mission that opens
west of a canal or a river had every camera jump ~600 off), and a "connection lost" box no longer sends the walk
back to the main menu while the mission runs."""
import os
import sys

import pytest
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'cnv'))
sys.path.insert(1, os.path.join(ROOT, 'experimental', 'testbench'))
import calib  # noqa: E402
import harness  # noqa: E402
import parts  # noqa: E402

WEST = (0.0, 0.0, 3640.0, 5000.0)               # festival's 'west of the canal'


def test_the_whole_map_maps_as_calibrated():
    for p in [(1700, 1500), (3500, 1700), (3300, 3500), (1250, 2500)]:
        assert calib.world_to_minimap(*p, calib.FULL) == calib.world_to_minimap(*p)


def test_a_narrow_area_is_drawn_centred_full_height():
    # read off a bench frame (2026-10-27): 'west of the canal' drawn 1108..1242 across, the box's full height
    (u0, v0), (u1, v1) = calib.world_to_minimap(0, 5000, WEST), calib.world_to_minimap(3640, 0, WEST)
    (f0, g0), (f1, g1) = calib.world_to_minimap(0, 5000), calib.world_to_minimap(5000, 0)
    assert abs(u0 - 1108) <= 2 and abs(u1 - 1242) <= 2
    assert abs(v0 - g0) <= 1 and abs(v1 - g1) <= 1                 # (the calibration's slight skew)
    # the old mapping put an aim at x=2900 near 2200 on this map: the map line's "~600 off"
    u_old = calib.world_to_minimap(2900, 2850)[0]
    assert calib.world_to_minimap(2900, 2850, WEST)[0] - u_old > 20


def frame_with(border):
    """A frame whose minimap draws `border`: black bars round a sea-blue area of the drawn size."""
    img = Image.new('RGB', (1280, 720), (90, 120, 60))
    (b0, c0), (b1, c1) = calib.world_to_minimap(0, 5000), calib.world_to_minimap(5000, 0)
    d = ImageDraw.Draw(img)
    d.rectangle((b0, c0, b1, c1), fill=(0, 0, 0))
    if border:
        (u0, v0), (u1, v1) = (calib.world_to_minimap(border[0], border[3], border),
                              calib.world_to_minimap(border[2], border[1], border))
        d.rectangle((u0, v0, u1 - 1, v1 - 1), fill=(25, 60, 95))
    return img


def test_drawn_size_read_off_a_frame():
    for b in (calib.FULL, WEST, (0.0, 0.0, 5000.0, 2400.0)):
        w, h = calib.minimap_drawn(frame_with(b))
        pw, ph = calib.drawn_size(b)
        assert abs(w - pw) <= 4 and abs(h - ph) <= 4, b
    assert calib.minimap_drawn(frame_with(None)) is None             # a cut scene: no minimap


@pytest.fixture
def session(monkeypatch):
    s = harness.Session()
    s.borders = [('whole', calib.FULL), ('west of the canal', WEST)]
    s.last_border = s.borders[0]
    shown = {'img': frame_with(WEST)}
    clicks = []
    monkeypatch.setattr(s, '_capture', lambda name, **k: shown['img'])
    monkeypatch.setattr(s, 'window', lambda: 1)
    monkeypatch.setattr(harness, 'click', lambda h, u, v, right=False: clicks.append((u, v)))
    monkeypatch.setattr(harness.time, 'sleep', lambda t: None)
    return s, shown, clicks


def test_the_camera_follows_the_border_on_screen(session):
    s, shown, clicks = session
    s.camera(2900, 2850)
    assert clicks[-1] == calib.world_to_minimap(2900, 2850, WEST)
    shown['img'] = frame_with(calib.FULL)                            # the mission opened the whole map
    s.camera(2900, 2850)
    assert clicks[-1] == calib.world_to_minimap(2900, 2850)


def test_the_camera_refuses_outside_the_playable_area(session):
    s, _, clicks = session
    with pytest.raises(harness.BenchError, match='outside the playable area'):
        s.camera(4400, 3400)
    assert not clicks


def test_a_cut_scene_keeps_the_last_border(session):
    s, shown, _ = session
    s.camera(1000, 1000)
    shown['img'] = frame_with(None)
    assert s.border()[0] == 'west of the canal'


def test_sidecar_round_trip(tmp_path):
    parts.write_sidecar(str(tmp_path), 'festival', [('whole', [0.0, 0.0, 5000.0, 5000.0]), ('west', list(WEST))])
    sku = str(tmp_path / 'CampA4_1.0.skudef')
    assert harness.map_borders(sku) == [('whole', calib.FULL), ('west', WEST)]
    assert harness.map_borders(str(tmp_path / 'nothing' / 'X_1.0.skudef')) == []


STEPS = [dict(name='main menu', how='tpl', threshold=10), dict(name='submenu', how='tpl', threshold=10),
         dict(name='video', how='bright', threshold=50), dict(name='in game', how='tpl', threshold=10)]


def test_the_walk_resumes_from_the_screen(monkeypatch):
    on = {}
    # template steps: 0 when on screen, 99 not; the video's brightness step matches any bright screen (the mission's)
    monkeypatch.setattr(harness.nav, 'metric', lambda frame, step: 200 if step['how'] == 'bright' else
                        (0 if step['name'] == on['name'] else 99))
    on['name'] = 'in game'
    assert harness.seen_step(STEPS, 'f', 0, back=True) == 3          # the box came up in the mission
    assert harness.seen_step(STEPS, 'f', 1) == 3                     # ahead of the walk: on from there
    on['name'] = 'main menu'
    assert harness.seen_step(STEPS, 'f', 3) is None                  # back only after a "connection lost" box
    assert harness.seen_step(STEPS, 'f', 3, back=True) == 0
    on['name'] = 'none'
    assert harness.seen_step(STEPS, 'f', 1, back=True) is None       # the bright step alone moves nothing
