"""The bench at RA3_BENCH_SPEED: mission seconds and waits are mission time (real time x speed), the shim's clocks are
hooked only when sped up, and the speed is asked for once the menus are walked -- without the game."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'testbench'))
import harness  # noqa: E402


@pytest.fixture
def clock(monkeypatch):
    now = {'t': 100.0}
    slept = []
    monkeypatch.setattr(harness.time, 'monotonic', lambda: now['t'])
    monkeypatch.setattr(harness.time, 'sleep', lambda s: slept.append(s))
    return now, slept


@pytest.mark.parametrize('speed', [1.0, 4.0])
def test_mission_seconds_run_at_the_speed(monkeypatch, clock, speed):
    now, slept = clock
    monkeypatch.setattr(harness, 'SPEED', speed)
    s = harness.Session()
    s.t0 = s.run_from = now['t']
    now['t'] += 10                                  # ten real seconds
    assert s.second() == 10 * speed
    s.run_for(40)
    assert slept[-1] == 40 / speed


def test_the_pause_keeps_mission_time(monkeypatch, clock):
    now, _ = clock
    monkeypatch.setattr(harness, 'SPEED', 4.0)
    s = harness.Session()
    s.hold, s.t0, s.run_from = True, now['t'], now['t']
    monkeypatch.setattr(s, 'window', lambda: 1)
    monkeypatch.setattr(harness, 'key', lambda h, vk: None)
    monkeypatch.setattr(s, '_capture', lambda name, **k: 'menu')
    monkeypatch.setattr(s, 'menu_open', lambda img: True)
    now['t'] += 10.5                                # 10 s running, then the 0.5 s the menu takes to come up
    s.pause()
    now['t'] += 60                                  # paused: the mission does not move
    assert s.second() == 40.0


@pytest.mark.parametrize('speed, hooked', [(1.0, None), (4.0, '1')])
def test_the_clocks_are_hooked_only_when_sped_up(monkeypatch, clock, speed, hooked):
    monkeypatch.setattr(harness, 'SPEED', speed)
    monkeypatch.setenv('CNV_SPEED', '9')            # left over in the environment: never passed on as it is
    seen = {}

    class Game:
        pid = 1

        def __init__(self, args, cwd, env):
            seen.update(env)

        def poll(self):
            return None

    monkeypatch.setattr(harness.subprocess, 'Popen', Game)
    monkeypatch.setattr(harness.slots, 'note_game', lambda i, pid: None)
    monkeypatch.setattr(harness.slots, 'free_instance', lambda pid: True)
    s = harness.Session()
    s._launch(['game'])
    assert seen.get('CNV_SPEED') == hooked
