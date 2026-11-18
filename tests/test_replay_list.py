"""The replay list (tests/replay_tests.txt): every name is a test file that exists, once, in a known group; conftest
marks exactly those files `replay`; the daily pick (affected_tests.py) leaves them out unless the change edits them."""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIST = os.path.join(HERE, 'replay_tests.txt')
KINDS = {'game', 'bench'}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


at = sys.modules.get('affected_tests') or _load(
    'affected_tests', os.path.join(os.path.dirname(HERE), 'experimental', 'testbench', 'affected_tests.py'))
conftest = _load('_conftest_under_test', os.path.join(HERE, 'conftest.py'))


def names_in(path):
    out = []
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.split('#', 1)[0].strip()
            if line and not line.startswith('['):
                out.append(line)
    return out


def test_every_listed_replay_is_a_test_file_that_exists():
    names = names_in(LIST)
    assert names, 'the replay list is empty'
    bad = [n for n in names if not re.match(r'test_\w+\.py$', n)
           or not os.path.isfile(os.path.join(os.path.dirname(HERE), at.current_path('tests/' + n)))]   # any layer
    assert not bad, 'listed in tests/replay_tests.txt but no such test file (renamed or deleted?): %s' % bad


def test_no_replay_is_listed_twice_and_every_group_is_known():
    names = names_in(LIST)
    twice = sorted({n for n in names if names.count(n) > 1})
    assert not twice, 'listed twice: %s' % twice
    replays = at.replay_files(LIST)
    assert len(replays) == len(names)
    assert set(replays.values()) <= KINDS, 'unknown group: %s' % (set(replays.values()) - KINDS)


def test_the_reader_takes_groups_and_skips_comments(tmp_path):
    p = tmp_path / 'r.txt'
    p.write_text('# head\n\n[game]  # whole games\ntest_a.py\n[bench]\ntest_b.py  # why\n', encoding='utf-8')
    assert at.replay_files(str(p), lambda n: n) == {'tests/test_a.py': 'game', 'tests/test_b.py': 'bench'}
    assert at.replay_files(str(tmp_path / 'none.txt')) == {}


class _Item:
    def __init__(self, path):
        self.fspath = path
        self.marks = []

    def add_marker(self, mark):
        self.marks.append(mark.name)


def test_conftest_marks_exactly_the_listed_files():
    listed = names_in(LIST)
    some_replay = os.path.join(HERE, listed[0])
    other = os.path.join(HERE, 'test_replay_list.py')
    assert 'test_replay_list.py' not in listed
    items = [_Item(some_replay), _Item(other)]
    conftest.pytest_collection_modifyitems(None, items)
    assert items[0].marks == ['replay'] and items[1].marks == []
    assert set(conftest.REPLAYS) == set(listed)


def test_daily_pick_leaves_replays_out_unless_the_change_edits_them():
    replays = {'tests/test_r.py': 'game', 'tests/test_s.py': 'bench'}
    picked = {'tests/test_r.py', 'tests/test_s.py::test_one', 'tests/test_plain.py'}
    kept, out = at.drop_replays(picked, replays, changed={'experimental/cnv/simheal.py'})
    assert kept == {'tests/test_plain.py'} and out == {'tests/test_r.py', 'tests/test_s.py::test_one'}
    kept, out = at.drop_replays(picked, replays, changed={'tests/test_r.py'})
    assert kept == {'tests/test_r.py', 'tests/test_plain.py'}
