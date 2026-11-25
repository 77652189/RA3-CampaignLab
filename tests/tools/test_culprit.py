"""The culprit command on a small real Git history, with no simulator."""
import importlib.util
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('culprit_under_test', ROOT / 'experimental/testbench/culprit.py')
culprit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(culprit)
_spec = importlib.util.spec_from_file_location('pytest_run_under_test', ROOT / 'experimental/testbench/pytest_run.py')
pytest_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pytest_run)
FIRST = 'test_sample.py::test_first'
SECOND = 'test_sample.py::test_second'
OLD_RED = 'test_sample.py::test_always_red'


@pytest.fixture
def repo(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.mkdir()
    monkeypatch.delenv('CNV_WORK', raising=False)

    def git(*args):
        return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()

    git('init', '-q')
    git('config', 'user.name', 'Culprit Test')
    git('config', 'user.email', 'culprit@example.invalid')
    (source / 'test_sample.py').write_text(
        'from pathlib import Path\n'
        'import pytest\n'
        'def check():\n'
        '    state = Path("state").read_text()\n'
        '    if state == "skip":\n'
        '        pytest.skip("missing data")\n'
        '    if state == "xfail":\n'
        '        pytest.xfail("known failure")\n'
        '    assert state == "green"\n'
        'def test_first():\n'
        '    check()\n'
        'def test_second():\n'
        '    check()\n'
        'def test_always_red():\n'
        '    assert False\n'
        'def test_stays_green():\n'
        '    pass\n', encoding='utf-8')
    commits = []
    for state, title in [('xfail', 'baseline'), ('green', 'green before skip'), ('skip', 'missing data'),
                         ('green', 'last green'), ('red', 'break both'), ('red', 'still broken')]:
        (source / 'state').write_text(state, encoding='utf-8')
        git('add', 'state', 'test_sample.py')
        git('commit', '-qm', title, '--allow-empty')
        commits.append(git('rev-parse', 'HEAD'))
    return source, commits


def test_bisects_new_reds_together(repo, tmp_path, capsys):
    source, commits = repo
    old_log, new_log = tmp_path / 'full_A.log', tmp_path / 'full_B.log'
    old_log.write_text(f'HEAD {commits[0]}\nFAILED {OLD_RED} - AssertionError\n', encoding='utf-8')
    new_log.write_text(f'commit {commits[-1]}\nFAILED {OLD_RED} - AssertionError\n'
                       f'FAILED {FIRST}\nFAILED {SECOND}\n', encoding='utf-8')

    assert culprit.main(['--since-full', str(old_log), str(new_log)], root=source) == 0
    lines = capsys.readouterr().out.splitlines()
    probes = [line for line in lines if ': pytest ' in line]
    assert probes[:3] == [f'{commits[index][:8]}: pytest {FIRST}, {SECOND}' for index in (5, 0, 2)]
    assert all(line.endswith(f'{FIRST}, {SECOND}') for line in probes)
    first_red = [line for line in lines if '  first red ' in line]
    assert first_red == [f'{node}  first red {commits[4][:8]} break both  (parent {commits[3][:8]} green)'
                         for node in (FIRST, SECOND)]
    assert 'unknown: 2 test/commit results' in lines  # two tests skipped at the same midpoint
    assert (source / 'state').read_text() == 'red'
    log, = (source / 'work/logs').glob('culprit_*.log')
    assert 'SKIPPED' in log.read_text(encoding='utf-8')


def test_refuses_a_green_bad_endpoint(repo, capsys):
    source, commits = repo
    node = 'test_sample.py::test_stays_green'
    assert culprit.main(['--good', commits[0], '--bad', commits[-1], node], root=source) == 1
    lines = capsys.readouterr().out.splitlines()
    assert f'{node}  bad is green (expected red)' in lines
    assert sum(': pytest ' in line for line in lines) == 1


SUMMARY = """....F.
FAILED tests/test_a.py::test_x - assert 1 == 2
FAILED tests/test_b.py::test_y - boom
ERROR tests/test_c.py::test_z - fixture
2 failed, 840 passed, 3 skipped, 1 error in 512.30s (0:08:32)
"""


def test_pytest_counts_and_red_ids():
    counts, red = pytest_run.pytest_counts(SUMMARY)
    assert counts == {'failed': 2, 'passed': 840, 'skipped': 3, 'error': 1}
    assert red == ['tests/test_a.py::test_x', 'tests/test_b.py::test_y', 'tests/test_c.py::test_z']


class FakePytest:
    """subprocess.run stand-in: hands out the given (returncode, stdout, stderr) one per call."""

    def __init__(self, *results):
        self.results, self.calls = list(results), 0

    def __call__(self, cmd, **kw):
        self.calls += 1
        rc, out, err = self.results.pop(0)
        return type('R', (), dict(returncode=rc, stdout=out, stderr=err))()


WAITED = 'cpupool: pytest -n 2 waits for 2 of 6 CPU tokens (0 free)\n'
CUT = (2, '', WAITED)       # R 11-18: interrupted in the wait, nothing on stdout


def test_a_run_with_no_summary_is_run_again_and_logged(tmp_path):
    log = tmp_path / 'tests.log'
    run = FakePytest(CUT, (1, SUMMARY, ''))
    counts, red, why = pytest_run.run_pytest(['-q'], str(tmp_path), str(log), run=run)
    assert run.calls == 2 and counts and red and why == ''
    text = log.read_text(encoding='utf-8')
    assert 'try 1, exit 2' in text and 'gave no summary (exit 2；cpupool: pytest -n 2 waits' in text
    assert 'running it again' in text and 'try 2, exit 1' in text


def test_two_runs_with_no_summary_say_how_they_ended(tmp_path):
    run = FakePytest(CUT, (3, '', 'INTERNALERROR> boom\n'))
    counts, red, why = pytest_run.run_pytest(['-q'], str(tmp_path), str(tmp_path / 'tests.log'), run=run)
    assert run.calls == 2 and not counts and not red
    assert 'exit 3' in why and 'INTERNALERROR> boom' in why
