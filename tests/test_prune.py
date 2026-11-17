"""experimental/testbench/prune.py loads and points at the bench folders.

The daily ra3-prune-bench task runs it with --apply; a typo in a module-level line (11-10, `os.path.joinlabpaths`)
made every run die at import for four days and the test mods filled the disk. Importing it here catches that.
"""
import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('prune', ROOT / 'experimental' / 'testbench' / 'prune.py')
prune = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prune)


def test_runs_is_the_bench_archive():
    assert Path(prune.RUNS).parts[-2:] == ('testbench', 'runs')


def test_mods_is_the_game_mod_folder():
    assert Path(prune.MODS).parts[-3:] == ('Documents', 'Red Alert 3', 'Mods')


def test_player_mods_are_kept():
    assert 'CampShell' in prune.KEEP and 'CampA4Demo' in prune.KEEP
    assert callable(prune.candidates) and callable(prune.main)
