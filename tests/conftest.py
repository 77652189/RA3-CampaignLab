"""Marks the replay tests (tests/replay_tests.txt: whole-game and bench-mission replays) `replay`, by the list, so no
test file has to change. The full run (pytest tests) runs them; `pytest -m "not replay"` leaves them out, and the
daily pick (experimental/testbench/affected_tests.py) leaves them out unless --with-replays.

Every test without a `timeout` marker of its own gets its layer's limit (experimental/testbench/time_budget.py
TEST_TIMEOUT, T7). RA3_TEST_TIMEOUT_SCALE scales those limits (0 disables them for a debugger)."""
import contextlib
import importlib.util
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_spec = importlib.util.spec_from_file_location(     # by file path, not sys.path (G4); the list's one reader lives there
    '_time_budget_for_conftest', os.path.join(_ROOT, 'experimental', 'testbench', 'time_budget.py'))
_tb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tb)
_at = _tb.at
_REPLAY_PATHS = _at.replay_files()
REPLAYS = {os.path.basename(f): kind for f, kind in _REPLAY_PATHS.items()}
_cpu_spec = importlib.util.spec_from_file_location(
    '_cpupool_for_conftest', os.path.join(os.path.dirname(_HERE), 'experimental', 'testbench', 'cpupool.py'))
cpupool = importlib.util.module_from_spec(_cpu_spec)
_cpu_spec.loader.exec_module(cpupool)
_held = contextlib.ExitStack()


def pytest_configure(config):
    config.addinivalue_line('markers', 'replay: a whole-game or bench-mission replay (tests/replay_tests.txt); '
                                       'left out of the daily pick')
    hold_cpu(config)


def hold_cpu(config):
    """The run holds the machine's CPU tokens (experimental/testbench/cpupool.py, T5) for its workers (-n, or 1) until
    it ends, waiting its turn when other lines hold them; each worker then runs inside a share of one (RA3_CPU_HELD),
    so a test's own subprocesses (golden's recorder) take only what is free. One run takes at most cpupool.cap() (2):
    -n above it runs that many workers (T5c, 11-18). RA3_CPU_EXCLUSIVE=1: the whole pool (a timed run), as many
    workers as asked. The workers themselves and a --collect-only take none."""
    if hasattr(config, 'workerinput') or config.option.collectonly:
        return
    n = max(1, getattr(config.option, 'numprocesses', None) or 1)
    exclusive = os.environ.get('RA3_CPU_EXCLUSIVE', '') not in ('', '0')
    if not exclusive and cpupool.enabled() and n > cpupool.cap():
        print('cpupool: -n %d asks for more CPU tokens than one run may take (%d): the run uses %d workers '
              '(RA3_CPU_EXCLUSIVE=1 takes the whole machine)' % (n, cpupool.cap(), cpupool.cap()), file=sys.stderr)
        n = cpupool.cap()
        _workers(config, n)
    # one process (no -n, or -n 0) does not queue (coordinator 11-18: a 0.4 s run waited two minutes for a full
    # pool): one process is one core at most, which the pool's reserve absorbs; it takes the free token when nobody
    # waits for it, else runs without one. Workers (-n 1 and up) queue as before.
    single = not getattr(config.option, 'numprocesses', None)
    try:
        got = _held.enter_context(cpupool.hold(n, 'pytest' if single else 'pytest -n %d' % n, exclusive=exclusive,
                                               wait=exclusive or not single))
    except KeyboardInterrupt:
        # pytest drops an interrupt during configure without a word (no summary, exit 2), so the run looks as if it
        # gave no result at all (R 11-18, family_close's tests step). Say why it stops.
        pytest.exit('cpupool: interrupted while waiting for %d CPU tokens; no test ran' % n, returncode=2)
    if got < n and not exclusive:
        print('cpupool: %d workers, but the run holds %d CPU tokens (the pool is %d): %d workers'
              % (n, got, cpupool.size(), got), file=sys.stderr)
        _workers(config, got)
    if os.environ.get(cpupool.HELD_ENV) and n > 1:
        os.environ[cpupool.HELD_ENV] = '1'      # each worker: a share of one


def _workers(config, n):
    """Run n xdist workers: xdist turned -n into config.option.tx before configure, and starts them from it later."""
    if getattr(config.option, 'numprocesses', None):
        config.option.numprocesses = n
        config.option.tx = ['popen'] * n


def pytest_unconfigure(config):
    _held.close()


def pytest_collection_modifyitems(config, items):
    limits = {}
    for item in items:
        if os.path.basename(str(item.fspath)) in REPLAYS:
            item.add_marker(pytest.mark.replay)
        if item.get_closest_marker('timeout') is None:
            path = os.path.relpath(str(item.fspath), _ROOT).replace(os.sep, '/')
            if path not in limits:
                limits[path] = _tb.timeout_for(path, _REPLAY_PATHS)
            item.add_marker(pytest.mark.timeout(limits[path]))
