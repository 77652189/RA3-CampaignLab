"""The golden layer (docs/engine/testing.md): each simrecord fixed task, recorded frame by frame on the base commit and
on this checkout, must read the same line for line. How the base is chosen, where records go and how a commit
declares an intended change: experimental/testbench/golden.py. A replay (tests/replay_tests.txt): both sides take
minutes the first time, then come from the cache."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('golden', ROOT / 'experimental' / 'testbench' / 'golden.py')
golden = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(golden)


@pytest.fixture(scope='module')
def run():
    try:
        return golden.records()
    except golden.Skip as e:
        pytest.skip(str(e))


@pytest.mark.parametrize('task', list(golden.simrecord.TASKS))
def test_the_frame_by_frame_record_is_unchanged(run, task):
    here = run.failed('new', task)
    assert not here, f'{task} could not be recorded on this checkout ({run.new}):\n{here}'
    if run.failed('base', task):
        pytest.skip(f'{task} is not recordable on the base {run.base_rev[:10]} (a task newer than it?)')
    differs = run.difference(task)
    if differs and task in run.changed:
        pytest.skip(f'{task} declared changed (Golden-Changed): {differs}')
    assert not differs, (f'{task}: base {run.base_rev[:10]} ({run.base}) vs this checkout ({run.new}):\n{differs}\n'
                         f'A change meant to alter behaviour says so in its commit message: "Golden-Changed: {task}" '
                         f'(uncommitted: GOLDEN_CHANGED={task}).')
