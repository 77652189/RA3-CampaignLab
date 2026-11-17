"""The bench's stop never costs a run its result (bench 2026-11-10: the game was not out 10 s after its kill, the
TimeoutExpired from harness.stop ran out of cnv_check's finally and the readings and the verdict were lost): stop()
kills only its own game's pid, warns on a timeout and still frees the slot; cnv_check judges and writes
cnv_result.txt before it stops -- without the game."""
import importlib.util
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    """A testbench module by its path (as test_bench_ext.py does), not by editing the import path."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, 'experimental', 'testbench', name + '.py'))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


class StuckGame:
    """A game that takes the kill but does not exit in time."""
    def __init__(self, pid):
        self.pid, self.killed = pid, 0

    def poll(self):
        return None

    def kill(self):
        self.killed += 1

    def wait(self, timeout=None):
        raise subprocess.TimeoutExpired('game', timeout)


def test_stop_warns_on_a_stuck_game_and_frees_the_slot(monkeypatch):
    harness = _load('harness')
    freed = []
    monkeypatch.setattr(harness.slots, 'release', freed.append)
    s = harness.Session()
    s.p, s.slot, s.mod, s.run_dir = StuckGame(4242), 2, 'CampX', 'runs/x'
    r = s.stop(wait=0.01)
    assert s.p.killed == 1                      # its own process only (Popen / GameProcess kill by its handle)
    assert freed == [2] and s.slot is None
    assert '4242' in r['warning'] and r['mod'] == 'CampX'


def test_stop_of_an_exited_game_has_no_warning(monkeypatch):
    harness = _load('harness')
    monkeypatch.setattr(harness.slots, 'release', lambda i: None)

    class Gone(StuckGame):
        def poll(self):
            return 0
    s = harness.Session()
    s.p, s.slot = Gone(1), 1
    assert 'warning' not in s.stop() and s.p.killed == 0


def test_cnv_check_keeps_its_verdict_when_the_stop_fails(monkeypatch, tmp_path):
    pytest.importorskip('mcp')                  # needs the mcp package (envs/bench_mcp)
    bench_mcp = _load('bench_mcp')
    plan = {'mod': 'CampX', 'steps': [['bench_start', {'mod': 'CampX'}], ['bench_counters', {}]]}
    order = []

    def lab(*a, **k):
        if '--plan' in a:
            return 0, 'PLAN ' + json.dumps(plan)
        order.append('judge')
        return 0, 'c1 = 3\nRESULT PASS'
    monkeypatch.setattr(bench_mcp, 'lab', lab)
    S = bench_mcp.S

    def start(**a):
        S.p, S.run_dir = StuckGame(7), str(tmp_path)
        return 'started'
    monkeypatch.setattr(bench_mcp, 'bench_start', start)
    monkeypatch.setattr(bench_mcp, 'bench_counters', lambda **a: 's1: 3')

    def stop():
        order.append('stop')
        raise subprocess.TimeoutExpired('game', 10)
    monkeypatch.setattr(bench_mcp, 'bench_stop', stop)
    monkeypatch.setattr(bench_mcp.harness, 'ext_summary', lambda log: '')
    try:
        out = bench_mcp.cnv_check('x', 'win')
    finally:
        S.p, S.run_dir = None, None
    assert order == ['judge', 'stop']
    assert 'RESULT PASS' in out and 'bench_stop: WARNING TimeoutExpired' in out
    saved = (tmp_path / 'cnv_result.txt').read_text(encoding='utf-8')
    assert 'RESULT PASS' in saved and 'bench_counters: ' in saved
