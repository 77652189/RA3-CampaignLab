"""Marks the replay tests (tests/replay_tests.txt: whole-game and bench-mission replays) `replay`, by the list, so no
test file has to change. The full run (pytest tests) runs them; `pytest -m "not replay"` leaves them out, and the
daily pick (experimental/testbench/affected_tests.py) leaves them out unless --with-replays."""
import importlib.util
import os

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(     # by file path, not sys.path (G4); the list's one reader lives there
    '_affected_tests_for_conftest', os.path.join(os.path.dirname(_HERE), 'experimental', 'testbench', 'affected_tests.py'))
_at = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_at)
REPLAYS = {os.path.basename(f): kind for f, kind in _at.replay_files().items()}


def pytest_configure(config):
    config.addinivalue_line('markers', 'replay: a whole-game or bench-mission replay (tests/replay_tests.txt); '
                                       'left out of the daily pick')


def pytest_collection_modifyitems(config, items):
    for item in items:
        if os.path.basename(str(item.fspath)) in REPLAYS:
            item.add_marker(pytest.mark.replay)
