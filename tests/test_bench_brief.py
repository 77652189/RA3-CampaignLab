"""cnv_check's step texts, cut down to what the verdict does not already say (experimental/testbench/bench_mcp.py)."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'testbench'))
bench_mcp = pytest.importorskip('bench_mcp')          # needs the mcp package (envs/bench_mcp)


def test_brief_watch_keeps_span_and_events():
    text = ('box (0, 0, 1280, 720); #1 s1.0 change - [3 12 16 1] | #2 s6.3 change 10.1 CAPTION CHANGED (36.5) '
            '[3 12 16 1] | #3 s11.6 change 8.8 [3 12 14 1] | UNTIL met: c1==0')
    assert bench_mcp.brief('bench_watch', text) == '3 frames s1.0..s11.6; #2 s6.3 caption changed; UNTIL met: c1==0'
    assert bench_mcp.brief('bench_counters', 's1: 3 | s6: 3') == 'read'
    assert bench_mcp.brief('bench_start', 'started X; menu 0 main menu at 22 s; menu 8 in game at 39 s; in game') \
        == 'started X; in game'


def test_until():
    assert bench_mcp.until_met('c1==0|c4==0', [2, 0, 5, 0]) == 'c4==0'
    assert bench_mcp.until_met('c1==0', [2, None]) is None
