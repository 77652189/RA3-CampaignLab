"""Marks the replay tests (tests/replay_tests.txt: whole-game and bench-mission replays) `replay`, by the list, so no
test file has to change. The full run (pytest tests) runs them; `pytest -m "not replay"` leaves them out, and the
daily pick (experimental/testbench/affected_tests.py) leaves them out unless --with-replays."""
import contextlib
import importlib.util
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(     # by file path, not sys.path (G4); the list's one reader lives there
    '_affected_tests_for_conftest', os.path.join(os.path.dirname(_HERE), 'experimental', 'testbench', 'affected_tests.py'))
_at = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_at)
REPLAYS = {os.path.basename(f): kind for f, kind in _at.replay_files().items()}
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
    so a test's own subprocesses (golden's recorder) take only what is free. RA3_CPU_EXCLUSIVE=1: the whole pool (a
    timed run). The workers themselves and a --collect-only take none."""
    if hasattr(config, 'workerinput') or config.option.collectonly:
        return
    n = max(1, getattr(config.option, 'numprocesses', None) or 1)
    exclusive = os.environ.get('RA3_CPU_EXCLUSIVE', '') not in ('', '0')
    got = _held.enter_context(cpupool.hold(n, 'pytest -n %d' % n, exclusive=exclusive))
    if got < n:
        print('cpupool: %d workers, but the run holds %d CPU tokens (the pool is %d)' % (n, got, cpupool.size()),
              file=sys.stderr)
    if os.environ.get(cpupool.HELD_ENV) and n > 1:
        os.environ[cpupool.HELD_ENV] = '1'      # each worker: a share of one


def pytest_unconfigure(config):
    _held.close()


def pytest_collection_modifyitems(config, items):
    for item in items:
        if os.path.basename(str(item.fspath)) in REPLAYS:
            item.add_marker(pytest.mark.replay)
