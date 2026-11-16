"""The affected-tests picker (experimental/testbench/affected_tests.py): selection logic on a fake coverage map and
fake diffs -- never the real work/testmap/coverage.db."""
import importlib.util
import os
import sqlite3
import sys

_spec = importlib.util.spec_from_file_location('affected_tests', os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'experimental', 'testbench', 'affected_tests.py'))
at = sys.modules['affected_tests'] = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(at)

SRC = '''X = 1

def f(a):
    if a:
        return 1
    return 2

def g():
    return f(0)
'''
KEY = 'experimental/cnv/fake.py'


def bits(nums):
    out = bytearray(max(nums) // 8 + 1)
    for n in nums:
        out[n // 8] |= 1 << (n % 8)
    return bytes(out)


def make_db(path, covered):
    """covered: {context name: {file path: [lines]}}"""
    db = sqlite3.connect(str(path))
    db.executescript('create table file(id integer primary key, path text);'
                     'create table context(id integer primary key, context text);'
                     'create table line_bits(file_id integer, context_id integer, numbits blob);')
    files = {}
    for ci, (ctx, per) in enumerate(covered.items(), 1):
        db.execute('insert into context values (?,?)', (ci, ctx))
        for p, lines in per.items():
            fid = files.setdefault(p, len(files) + 1)
            if len(files) == fid and not db.execute('select 1 from file where id=?', (fid,)).fetchone():
                db.execute('insert into file values (?,?)', (fid, p))
            db.execute('insert into line_bits values (?,?,?)', (fid, ci, bits(lines)))
    db.commit()
    db.close()


def fake_map(tmp_path):
    p = 'C:\\repo\\experimental\\cnv\\fake.py'
    make_db(tmp_path / 'cov.db', {
        '': {p: [1, 3, 8]},                                    # import time: owned by no test
        'tests/test_a.py::test_one|run': {p: [4, 6, 9]},        # f(False) via g
        'tests/test_b.py::test_two[x]|run': {p: [4, 5]},        # f(True)
        'tests/test_c.py::test_three|run': {'C:\\repo\\experimental\\cnv\\other.py': [2]},
    })
    return at.CovMap(str(tmp_path / 'cov.db'))


def test_numbits_roundtrip():
    assert at.nums_from_bits(bits([1, 7, 8, 40])) == [1, 7, 8, 40]


def test_path_key_maps_worktrees_and_engine():
    assert at.path_key('C:\\a\\RA3-CampaignLab-x\\experimental\\cnv\\sim.py') == 'experimental/cnv/sim.py'
    assert at.path_key('C:\\a\\RA3-EngineModel\\ra3model\\m.py') == 'ENGINE:ra3model/m.py'
    assert at.path_key('C:\\elsewhere\\x.py') is None


def test_parse_diff_and_old_side_lines():
    diff = ('diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -5 +5,2 @@\n-a\n+b\n+c\n'
            '@@ -9,0 +11 @@\n+d\n@@ -20,2 +22,0 @@\n-e\n-f\n'
            'diff --git a/new.txt b/new.txt\n--- /dev/null\n+++ b/new.txt\n@@ -0,0 +1 @@\n+z\n')
    h = at.parse_diff(diff)
    assert h['x.py'] == [(5, 1, 5, 2), (9, 0, 11, 1), (20, 2, 22, 0)]
    assert h['new.txt'] is None                                 # an added file: no old lines
    # changed line, insertion after 9 (neighbours 9 and 10), deletion of 20-21 (neighbours 19 and 22)
    assert at.old_side_lines(h['x.py']) == {5, 9, 10, 19, 20, 21, 22}


def test_remap_lines_moves_to_the_coverage_numbering():
    hunks = [(3, 0, 3, 2)]                                      # two lines were inserted after base line 3
    assert at.remap_lines({2, 4, 9}, hunks) == {2, 6, 11}
    assert at.remap_lines({4}, [(4, 1, 4, 3)]) >= {3, 4, 5, 6}  # a changed line: its whole new range, plus before


def test_select_by_line_function_and_file(tmp_path):
    cov = fake_map(tmp_path)
    src = at.Source(SRC)
    sel = lambda *lines: at.select(cov, KEY, set(lines), src)
    assert sel(6) == {'tests/test_a.py'}                        # only a ran `return 2`
    assert sel(5) == {'tests/test_b.py'}
    assert sel(9, 10) == {'tests/test_a.py'}                    # g's body; the neighbour line 10 is past the end
    assert sel(3) == {'tests/test_a.py', 'tests/test_b.py'}     # a def header runs at import: whole function
    assert sel(1) == {'tests/test_a.py', 'tests/test_b.py'}     # a module constant: every test on the file
    assert sel(2) == set()                                      # a blank line
    assert sel(7) == set()


def test_continuation_line_widens_to_its_statement(tmp_path):
    p = 'C:\\repo\\experimental\\cnv\\fake.py'
    src = at.Source('def h(a,\n      b):\n    return foo(a,\n               b)\n')
    make_db(tmp_path / 'c2.db', {'tests/test_d.py::t|run': {p: [3]}})
    cov = at.CovMap(str(tmp_path / 'c2.db'))
    assert at.select(cov, KEY, {4}, src) == {'tests/test_d.py'}     # line 4 is part of the statement on line 3


def test_pick_falls_back_by_name_and_takes_changed_tests(tmp_path):
    cov = fake_map(tmp_path)
    src = {KEY: at.Source(SRC)}
    ident = {KEY: lambda ls: ls}
    changes = [(KEY, KEY, [(6, 1, 6, 1)], False),
               ('data/units.xml', 'data/units.xml', [(1, 1, 1, 1)], False),    # not in the coverage map
               ('tests/test_new.py', 'tests/test_new.py', None, False)]
    tests, why, fell = at.pick(cov, changes, src, ident, lambda p: {'tests/test_x.py'} if 'units' in p else set())
    assert tests == {'tests/test_a.py', 'tests/test_x.py', 'tests/test_new.py'}
    assert fell == ['data/units.xml']
    assert why['tests/test_x.py'] == ['by name: data/units.xml']


def test_guards_always_present():
    g = at.guards()
    assert {'tests/test_docs.py', 'tests/test_architecture.py', 'tests/test_no_program_addresses.py'} <= g
    assert any(x.startswith('tests/test_inventory') for x in g)


def test_workers_follow_free_memory():
    assert at.workers(100) == 8 and at.workers(6.1) == 4 and at.workers(1.0) == 1 and at.workers(0) == 1


def test_tests_without_a_coverage_record_are_always_picked(tmp_path, monkeypatch):
    cov = fake_map(tmp_path)                                    # records: test_a, test_b, test_c
    (tmp_path / 'tests').mkdir()
    for f in ('test_a.py', 'test_b.py', 'test_c.py', 'test_new.py', 'helper.py'):
        (tmp_path / 'tests' / f).write_text('')
    monkeypatch.setattr(at, 'ROOT', str(tmp_path))
    assert at.unrecorded(cov) == ['tests/test_new.py']


def test_estimate_uses_median_for_unknown_files():
    serial, par, unknown = at.estimate(['a', 'b', 'c'], {'a': 80.0, 'b': 40.0})
    assert unknown == 1 and serial == 200.0                    # c gets the median (index 1 of 40, 80 -> 80)
    assert par == 80.0                                         # no faster than the longest single file
