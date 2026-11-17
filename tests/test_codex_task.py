"""experimental/outsource/codex_task.py: the task contract's "Files:" section -- what Codex may change."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('codex_task', os.path.join(ROOT, 'experimental', 'outsource', 'codex_task.py'))
codex_task = importlib.util.module_from_spec(spec)
spec.loader.exec_module(codex_task)


def test_files_lists_the_globs_until_the_next_section():
    brief = 'Goal.\n\nFiles:\n- experimental/cnv/sim.py\n- experimental/cnv/checks/engine_*.py, tests/test_simbench_c.py\n' \
            'Tests:\n- pytest -q tests/test_simbench_c.py\n'
    assert codex_task.files_allowed(brief) == ['experimental/cnv/sim.py', 'experimental/cnv/checks/engine_*.py',
                                               'tests/test_simbench_c.py']


def test_files_none_is_a_read_only_task_and_no_section_is_refused():
    assert codex_task.files_allowed('Files: none\nTests: none\n') == []
    assert codex_task.files_allowed('Goal only.\nTests: none\n') is None
