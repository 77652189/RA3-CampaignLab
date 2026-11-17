"""A Windows box the game puts up before any menu (bench 2026-11-08: "Failed to initialize Steam" after a boot, Steam's
library not ready) is reported as that box, not as "menus stuck"; doctor.py tells whether Steam is ready -- without
the game: the window list is a stand-in."""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.join(ROOT, 'experimental', 'testbench')


def _load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(BENCH, name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


harness = _load('harness')
doctor = _load('doctor')

STEAM = [('Red Alert 3', ['确定', 'Steam: Failed to initialize Steam. Please make sure Steam is running.'])]


def test_box_error_names_the_box_and_says_what_to_do_for_steam():
    assert harness.box_error([]) is None
    said = harness.box_error(STEAM)
    assert 'Red Alert 3: Steam: Failed to initialize Steam' in said
    assert '确定' not in said                       # the button is no news
    assert 'restart Steam' in said
    assert 'restart Steam' not in harness.box_error([('Game crash', ['OK', 'it broke'])])


def test_boxes_reads_real_windows():
    assert harness.boxes(os.getpid()) == []          # this test process puts up no dialog box


class _Game:
    pid = 4242

    def poll(self):
        return None


def _walk(monkeypatch, found, timeout=150):
    now = {'t': 0.0}
    monkeypatch.setattr(harness.time, 'monotonic', lambda: now['t'])
    monkeypatch.setattr(harness.time, 'sleep', lambda s: now.__setitem__('t', now['t'] + s))
    monkeypatch.setattr(harness, 'main_window', lambda pid: None)     # no window to capture: no frame ever
    s = harness.Session()
    s.p, s.run_dir = _Game(), 'run'
    s._alive = lambda: None
    asked = []
    s.boxes = lambda pid: asked.append(pid) or found(now['t'])
    with pytest.raises(harness.BenchError) as e:
        s._walk_menus(False, timeout, steps=[{'name': 'main menu'}])
    return str(e.value), now['t'], asked


def test_a_box_that_stays_up_is_the_error_long_before_the_timeout(monkeypatch):
    said, t, asked = _walk(monkeypatch, lambda t: STEAM if t >= 5 else [])
    assert said.startswith('the game put up a box: Red Alert 3: Steam: Failed to initialize Steam')
    assert 'menus at "main menu"' in said
    assert t == 5 + harness.BOX_WAIT and set(asked) == {4242}


def test_a_box_that_closes_again_is_no_error(monkeypatch):
    said, t, _ = _walk(monkeypatch, lambda t: STEAM if 5 <= t < 8 else [], timeout=30)
    assert said.startswith('menus stuck at "main menu" after 31 s')


def test_doctor_steam_state_reads_the_login_log_tail():
    ok = ('[2026-11-08 15:05:41] [ WaitingForServerResponse ] SetLoginState: WaitingForLibraryReady - OK\n'
          '[2026-11-08 15:05:43] [ WaitingForLibraryReady ] SetLoginState: Success - OK\n')
    assert doctor.steam_state(ok)[0] == 'OK'
    stuck = ok + '[2026-11-08 15:10:43] [ WaitingForLibraryReady ] Timed out waiting for library ready: 300.000000s - online\n'
    assert doctor.steam_state(stuck) == ('BROKEN', 'Steam timed out waiting for its library (WaitingForLibraryReady)')
    waiting = '[x] [ None ] SetLoginState: WaitingForNetwork - OK\n'
    assert doctor.steam_state(waiting) == ('BROKEN', 'Steam login state WaitingForNetwork')
    assert doctor.steam_state('nothing here\n')[0] == 'WARN'
