"""experimental/testbench/family_close.py on made-up data: the one-line verdicts of the golden compare, the centre
table and the affected tests, the -n rewrite, and the centre counted by the kernel guard's own rule."""
import importlib.util
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('family_close', ROOT / 'experimental' / 'testbench' / 'family_close.py')
fc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fc)


class FakeRun:
    """A golden.Run stand-in: per task 'same', a difference text, 'fail-new' or 'fail-base'."""

    def __init__(self, outcome, changed=()):
        self.outcome, self.changed, self.names, self.base_rev = outcome, set(changed), list(outcome), 'abcdef123456'

    def failed(self, side, name):
        return 'boom' if self.outcome[name] == f'fail-{side}' else None

    def difference(self, name):
        o = self.outcome[name]
        return None if o == 'same' else o


def test_golden_all_same_is_green():
    ok, line = fc.golden_line(FakeRun({'a': 'same', 'b': 'same'}), io.StringIO())
    assert ok and '2/2 same' in line


def test_golden_a_difference_not_declared_is_red_and_named():
    log = io.StringIO()
    ok, line = fc.golden_line(FakeRun({'a': 'same', 'b': 'frame 9: hp 10 vs 9'}), log)
    assert not ok and "['b']" in line
    assert 'frame 9' in log.getvalue()


def test_golden_a_declared_difference_and_a_declared_base_gap_are_green_but_said():
    ok, line = fc.golden_line(FakeRun({'a': 'frame 1', 'b': 'fail-base', 'c': 'same'}, changed={'a', 'b'}),
                              io.StringIO())
    assert ok and '声明改了' in line and '底版录不了' in line and '1/3 same' in line


def test_golden_a_base_gap_not_declared_is_red():
    """Nothing was compared for that task -- golden.py returns 1 for it, so the family gate must not say green."""
    log = io.StringIO()
    ok, line = fc.golden_line(FakeRun({'a': 'same', 'b': 'fail-base'}), log)
    assert not ok and "['b']" in line and '1/2 same' in line
    assert 'boom' in log.getvalue()


def test_golden_not_recordable_here_is_red(tmp_path):
    ok, _ = fc.golden_line(FakeRun({'a': 'fail-new'}), io.StringIO())
    assert not ok
    (tmp_path / 'a.failed').touch()     # the real Run: a failure with an empty log is still one (review ff P3)
    (tmp_path / 'a.txt').touch()
    golden = fc._load('golden', str(ROOT / 'experimental' / 'testbench' / 'golden.py'))
    assert golden.Run('abc', str(tmp_path), str(tmp_path), set(), ['a']).failed('base', 'a')


TABLE = {'sim.py lines': 100, 'Body fields': 10}


def test_centre_equal_to_the_table_is_green_and_shows_before_after():
    ok, line = fc.centre_line({'sim.py lines': 120, 'Body fields': 10}, dict(TABLE), TABLE)
    assert ok and 'sim.py lines 120->100' in line and 'Body fields 10' in line


def test_centre_over_the_table_is_red():
    ok, line = fc.centre_line(None, {'sim.py lines': 101, 'Body fields': 10}, TABLE)
    assert not ok and 'sim.py lines 101 > 100' in line


def test_centre_under_the_table_asks_to_lower_it():
    ok, line = fc.centre_line(None, {'sim.py lines': 99, 'Body fields': 10}, TABLE)
    assert not ok and "'sim.py lines': 99" in line


def test_centre_is_counted_by_the_guards_own_rule():
    guard = (ROOT / fc.KERNEL_GUARD).read_text(encoding='utf-8')
    table, count = fc.centre_tools(guard)
    sim = 'class Sim:\n    def a(self):\n        pass\n\nclass Body:\n    x: int = 0\n    y: int = 0\n'
    loop = 'FRAME = ("one", "two")\n\ndef one(s, frame, tick):\n    """Its modules only."""\n'
    got = count(sim_src=sim, units_src='def f():\n    pass\n', loop_src=loop)
    assert set(got) == set(table)
    assert got['Sim methods'] == 1 and got['Body fields'] == 2 and got['simunits defs'] == 1
    assert got['cells with old code'] == 1          # 'two' is no function: counts as old code; 'one' is modules only


def test_workers_are_replaced_or_added():
    assert fc.with_workers('python -m pytest -n 8 --timeout 3000 a.py', 2) == 'python -m pytest -n 2 --timeout 3000 a.py'
    assert fc.with_workers('python -m pytest -q a.py', 2) == 'python -m pytest -n 2 -q a.py'


SUMMARY = """....F.
FAILED tests/test_a.py::test_x - assert 1 == 2
FAILED tests/test_b.py::test_y - boom
ERROR tests/test_c.py::test_z - fixture
2 failed, 840 passed, 3 skipped, 1 error in 512.30s (0:08:32)
"""


def test_pytest_counts_and_red_ids():
    counts, red = fc.pytest_counts(SUMMARY)
    assert counts == {'failed': 2, 'passed': 840, 'skipped': 3, 'error': 1}
    assert red == ['tests/test_a.py::test_x', 'tests/test_b.py::test_y', 'tests/test_c.py::test_z']


def test_reds_also_red_on_the_base_are_old():
    counts, red = fc.pytest_counts(SUMMARY)
    ok, line = fc.tests_line(counts, red, set(red))
    assert ok and '旧红' in line
    ok, line = fc.tests_line(counts, red, {'tests/test_a.py::test_x', 'tests/test_c.py::test_z'})
    assert not ok and 'tests/test_b.py::test_y' in line and 'test_x' not in line


def test_no_pytest_summary_is_red():
    assert not fc.tests_line({}, [], set())[0]


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
    counts, red, why = fc.run_pytest(['-q'], str(tmp_path), str(log), run=run)
    assert run.calls == 2 and counts and red and why == ''
    text = log.read_text(encoding='utf-8')
    assert 'try 1, exit 2' in text and 'gave no summary (exit 2；cpupool: pytest -n 2 waits' in text
    assert 'running it again' in text and 'try 2, exit 1' in text


def test_two_runs_with_no_summary_say_how_they_ended(tmp_path):
    run = FakePytest(CUT, (3, '', 'INTERNALERROR> boom\n'))
    counts, red, why = fc.run_pytest(['-q'], str(tmp_path), str(tmp_path / 'tests.log'), run=run)
    assert run.calls == 2 and not counts and not red
    ok, line = fc.tests_line(counts, red, set(), why)
    assert not ok and 'exit 3' in line and 'INTERNALERROR> boom' in line


def test_light_skips_the_affected_tests_and_says_they_are_left_to_the_full_run(tmp_path, monkeypatch, capsys):
    import types
    fake = types.SimpleNamespace(base_rev=lambda root, env: 'abcdef123456', records=lambda env, jobs: FakeRun({'a': 'same'}),
                                 labpaths=types.SimpleNamespace(WORK=str(tmp_path)), Skip=RuntimeError)
    monkeypatch.setattr(fc, '_load', lambda name, path: fake)
    monkeypatch.setattr(fc, 'git', lambda root, *args: 'abcdef1234')
    monkeypatch.setattr(fc, 'centre', lambda root, base: (True, 'same'))
    called = []
    monkeypatch.setattr(fc, 'affected', lambda *a: called.append(a) or (False, 'red'))
    assert fc.main(['--light']) == 0 and not called
    assert '受影响测试留给全量' in capsys.readouterr().out
    assert fc.main([]) == 1 and called


def test_light_runs_the_test_files_the_step_changed(tmp_path, monkeypatch, capsys):
    import types
    fake = types.SimpleNamespace(base_rev=lambda root, env: 'abcdef123456', records=lambda env, jobs: FakeRun({'a': 'same'}),
                                 labpaths=types.SimpleNamespace(WORK=str(tmp_path)), Skip=RuntimeError)
    monkeypatch.setattr(fc, '_load', lambda name, path: fake)
    diff = 'tests/test_simai.py\ntests/guards/test_kernel.py\ntests/conftest.py\nexperimental/cnv/sim.py\ntests/test_gone.py\n'
    monkeypatch.setattr(fc, 'git', lambda root, *args: diff if args[0] == 'diff' else 'abcdef1234')
    monkeypatch.setattr(fc, 'centre', lambda root, base: (True, 'same'))
    assert fc.changed_tests(fc.ROOT, 'b') == ['tests/guards/test_kernel.py', 'tests/test_simai.py']   # gone: left out
    ran = []
    monkeypatch.setattr(fc, 'judge', lambda args, *a: ran.append(args) or (False, '本步新红 1 个'))
    assert fc.main(['--light']) == 1
    assert ran and ran[0][-2:] == ['tests/guards/test_kernel.py', 'tests/test_simai.py']
    out = capsys.readouterr().out
    assert '本步改过的测试文件 2 个' in out and '受影响测试留给全量' in out
