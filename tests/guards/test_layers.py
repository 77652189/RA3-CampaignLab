"""The test layers (ADR 0035, docs/engine/testing.md): tests/ holds one folder per question a test answers, and the
files still at the top level are the ones from before the layers, which only leave.

1. every layer folder exists (a guard over a missing folder would pass on nothing), and tests/ has no other folder
   but fixtures;
2. a test file at the top level is one that was there when the layers came (BASE): a new test goes into a layer,
   and a file that moves out cannot come back;
3. no two test files share a name anywhere under tests/: pytest imports them by name (no __init__.py), and the
   picker finds a file the coverage map recorded before a move by it;
4. the picker's guards are the whole guard layer.
Each rule has a bite check on a made-up tree."""
import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


at = _load('affected_tests_for_layers', 'experimental/testbench/affected_tests.py')

BASE = '488035c07e5373d317b47ede73a9c44ebeb21e4d'   # origin/main when the layers came (11-17): the old top level
OTHER_FOLDERS = {'fixtures'}                         # data, not tests
TOP_FILES = {'conftest.py', 'replay_tests.txt'}      # the top level's own files besides the old tests


def base_top_level():
    """The test files at the top of tests/ at BASE (git; red, not empty, when git cannot tell)."""
    r = subprocess.run(['git', 'ls-tree', '--name-only', BASE, 'tests/'], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, 'git cannot read BASE %s: %s' % (BASE, r.stderr.strip())
    names = {p.rsplit('/', 1)[1] for p in r.stdout.split() if at.is_test_file(p) and p.count('/') == 1}
    assert len(names) > 200, 'BASE lists %d top-level test files: the guard would pass on nothing' % len(names)
    return names


def folder_problems(root):
    tests = os.path.join(root, 'tests')
    if not os.path.isdir(tests):
        return ['no tests/ folder at %s' % root]
    out = ['tests/%s/ missing (a layer: docs/engine/testing.md)' % x for x in at.LAYERS
           if not os.path.isdir(os.path.join(tests, x))]
    for d in sorted(os.listdir(tests)):
        if os.path.isdir(os.path.join(tests, d)) and d not in at.LAYERS and d not in OTHER_FOLDERS \
                and d not in at.SKIP_DIRS and not d.startswith('.'):
            out.append('tests/%s/ is not a layer: put its tests in one of %s' % (d, ', '.join(at.LAYERS)))
    return out


def top_level_problems(root, old):
    tests = os.path.join(root, 'tests')
    out = []
    for f in sorted(os.listdir(tests)):
        if not os.path.isfile(os.path.join(tests, f)) or f in TOP_FILES:
            continue
        if at.is_test_file('tests/' + f):
            if f not in old:
                out.append('tests/%s is new at the top level: put it in a layer (tests/<layer>/, '
                           'docs/engine/testing.md)' % f)
        elif f.endswith('.py'):
            out.append('tests/%s: a helper goes next to the tests that use it, in their layer' % f)
    return out


def name_problems(root):
    try:
        at.test_index(root)
    except ValueError as e:
        return [str(e)]
    return []


def test_every_layer_folder_exists_and_there_is_no_other():
    assert not folder_problems(ROOT), folder_problems(ROOT)


def test_the_top_level_only_loses_test_files():
    assert not top_level_problems(ROOT, base_top_level()), top_level_problems(ROOT, base_top_level())


def test_no_two_test_files_share_a_name():
    assert not name_problems(ROOT), name_problems(ROOT)


def test_the_picker_always_takes_the_whole_guard_layer():
    layer = {f for f in at.all_test_files(str(ROOT)) if f.startswith('tests/guards/')}
    assert 'tests/guards/test_layers.py' in layer
    assert layer <= at.guards(str(ROOT))


# ---------------------------------------------------------------- bite checks on a made-up tree

def _tree(tmp_path, files):
    for f in files:
        p = tmp_path / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('', encoding='utf-8')
    return str(tmp_path)


def _layers():
    return ['tests/%s/test_%s_one.py' % (x, x) for x in at.LAYERS]


def test_folder_guard_bites(tmp_path):
    root = _tree(tmp_path, _layers()[1:] + ['tests/odd/test_q.py', 'tests/fixtures/data.json'])
    p = folder_problems(root)
    assert any('tests/%s/ missing' % at.LAYERS[0] in x for x in p)
    assert any('tests/odd/ is not a layer' in x for x in p)
    assert not any('fixtures' in x for x in p)
    assert folder_problems(str(tmp_path / 'nowhere')) == ['no tests/ folder at %s' % (tmp_path / 'nowhere')]


def test_top_level_guard_bites(tmp_path):
    root = _tree(tmp_path, _layers() + ['tests/test_old.py', 'tests/test_new.py', 'tests/helper.py',
                                        'tests/conftest.py', 'tests/replay_tests.txt'])
    p = top_level_problems(root, {'test_old.py'})
    assert len(p) == 2 and any('test_new.py is new' in x for x in p) and any('helper.py: a helper' in x for x in p)


def test_name_guard_bites(tmp_path):
    root = _tree(tmp_path, _layers() + ['tests/guards/test_same.py', 'tests/content/test_same.py'])
    assert name_problems(root) and 'test_same.py' in name_problems(root)[0]


def test_picker_guard_bites(tmp_path):
    root = _tree(tmp_path, ['tests/test_docs.py', 'tests/modules/test_x.py'])   # the guards left the guard layer
    with pytest.raises(RuntimeError):
        at.guards(root)
