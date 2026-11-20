"""experimental/testbench/golden.py on a made-up repository: which commit is the base, what a commit declares changed,
when this checkout's side is a new record, and simrecord.first_difference on made-up records."""
import gzip
import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('golden', ROOT / 'experimental' / 'testbench' / 'golden.py')
golden = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(golden)
TASKS = {'heal_a': None, 'ai_open': None, 'old_heal_a': None}


def _git(repo, *args):
    subprocess.run(['git', '-C', str(repo), '-c', 'user.email=t@t', '-c', 'user.name=t', *args], check=True,
                   capture_output=True)


def _commit(repo, msg, files):
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    _git(repo, 'add', '-A')
    _git(repo, 'commit', '-m', msg)
    return subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / 'repo'
    r.mkdir()
    _git(r, 'init', '-q')
    first = _commit(r, 'one', {'experimental/cnv/sim.py': 'a = 1\n', golden.PIN_REL: 'aaa\n'})
    second = _commit(r, 'two\n\nGolden-Changed: heal_a, old_heal_a', {'experimental/cnv/sim.py': 'a = 2\n'})
    return r, first, second


def test_the_base_is_the_parent_when_clean_and_head_when_not(repo):
    r, first, second = repo
    assert golden.base_rev(str(r), {}) == first
    (r / 'experimental' / 'cnv' / 'sim.py').write_text('a = 3\n', encoding='utf-8')
    assert golden.base_rev(str(r), {}) == second
    assert golden.base_rev(str(r), {'GOLDEN_BASE': first}) == first


def test_an_untracked_file_under_experimental_counts_as_uncommitted(repo):
    r, first, second = repo
    (r / 'notes.txt').write_text('x', encoding='utf-8')
    assert golden.base_rev(str(r), {}) == first
    (r / 'experimental' / 'cnv' / 'simnew.py').write_text('b = 1\n', encoding='utf-8')
    assert golden.base_rev(str(r), {}) == second


def test_declared_reads_every_commit_after_the_base_and_the_environment(repo):
    r, first, second = repo
    assert golden.declared(str(r), first, {}, TASKS) == {'heal_a', 'old_heal_a'}
    assert golden.declared(str(r), second, {}, TASKS) == set()
    assert golden.declared(str(r), second, {'GOLDEN_CHANGED': 'ai_open'}, TASKS) == {'ai_open'}
    assert golden.declared(str(r), second, {'GOLDEN_CHANGED': 'all'}, TASKS) == set(TASKS)


def test_a_declared_name_that_is_no_task_is_an_error(repo):
    r, first, second = repo
    with pytest.raises(ValueError, match='heal_b'):
        golden.declared(str(r), second, {'GOLDEN_CHANGED': 'heal_b'}, TASKS)


def test_this_checkouts_side_is_recorded_anew_when_the_work_changes(repo):
    r, first, second = repo
    clean = golden.work_key(str(r))
    assert clean.startswith('c-' + second[:12])
    sim = r / 'experimental' / 'cnv' / 'sim.py'
    sim.write_text('a = 3\n', encoding='utf-8')
    one = golden.work_key(str(r))
    sim.write_text('a = 4\n', encoding='utf-8')
    two = golden.work_key(str(r))
    assert one.startswith('w-') and two.startswith('w-') and one != two
    (r / 'experimental' / 'cnv' / 'simnew.py').write_text('b = 1\n', encoding='utf-8')
    assert golden.work_key(str(r)) != two


def test_the_pin_is_read_at_the_base_and_here(repo):
    r, first, second = repo
    assert golden.pin_at(str(r), first) == 'aaa'
    (r / golden.PIN_REL).write_text('bbb\n', encoding='utf-8')
    assert golden.pin_here(str(r)) == 'bbb'
    assert golden.pin_at(str(r), 'HEAD') == 'aaa'


def _gz(path, lines):
    with gzip.open(path, 'wt', encoding='utf-8') as f:
        f.write(''.join(x + '\n' for x in lines))


def test_first_difference_names_the_frame_and_the_field(tmp_path):
    a, b, c = tmp_path / 'a.gz', tmp_path / 'b.gz', tmp_path / 'c.gz'
    _gz(a, ['f0 t=0.0 || #1|hp=10;mode=idle', 'f1 t=0.1 || #1|hp=10;mode=idle'])
    _gz(b, ['f0 t=0.0 || #1|hp=10;mode=idle', 'f1 t=0.1 || #1|hp=9;mode=idle'])
    _gz(c, ['f0 t=0.0 || #1|hp=10;mode=idle'])
    assert golden.simrecord.first_difference(a, a) == (2, None)
    n, report = golden.simrecord.first_difference(a, b)
    assert n == 2 and 'f1 t=0.1' in report and "('#1|hp=10', '#1|hp=9')" in report and 'mode=idle' not in report.split('[')[-1]
    n, report = golden.simrecord.first_difference(a, c)
    assert n == 2 and report.startswith('DIFFERS at line 2')


def test_prune_keeps_the_newest_and_the_spared_and_nothing_else_of_others(tmp_path):
    cache = tmp_path / 'golden'
    made = []
    for i, name in enumerate(['c-1', 'w-2', 'c-3', 'c-4', 'c-5', 'other']):
        d = cache / name
        d.mkdir(parents=True)
        (d / 'x.gz').write_text('x')
        os.utime(d, (1000 + i, 1000 + i))
        made.append(str(d))
    gone = golden.prune(str(cache), keep=3, spare=(made[0],))
    assert sorted(os.path.basename(g) for g in gone) == ['c-3', 'w-2']
    assert sorted(os.listdir(cache)) == ['c-1', 'c-4', 'c-5', 'other']


def test_a_base_before_the_observation_port_is_refused_before_the_tree_is_touched(repo, tmp_path):
    r, first, _ = repo
    port = {rel.replace(os.sep, '/'): 'x = 1\n' for rel in golden.RECORDER_RELS}
    assert sorted(golden.missing_recorder(str(r), first)) == sorted(port)
    tree = tmp_path / 'golden-tree'
    with pytest.raises(RuntimeError, match='predates the observation port'):
        golden.prepare_tree(first, str(r), str(tree))
    assert not tree.exists()
    later = _commit(r, 'three', port)
    assert golden.missing_recorder(str(r), later) == []


def test_complete_counts_a_failed_task_as_done(tmp_path):
    (tmp_path / 'heal_a.gz').write_text('x')
    assert not golden.complete(str(tmp_path), ['heal_a', 'ai_open'])
    (tmp_path / 'ai_open.failed').write_text('')
    assert golden.complete(str(tmp_path), ['heal_a', 'ai_open'])


def test_a_change_to_how_a_base_is_prepared_is_a_new_cache_key(tmp_path, monkeypatch):
    # review 1120dd P2: the readonly.py copy (RECORDER_HELPERS) fixed, the key stayed and the old base's .failed was
    # read as done -- the key now covers the helpers and golden.py itself (prepare_tree)
    for rel in golden.RECORDER_RELS + golden.RECORDER_HELPERS:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('x\n', encoding='utf-8')
    one = golden.recorder_hash(str(tmp_path))
    (tmp_path / golden.RECORDER_HELPERS[0]).write_text('y\n', encoding='utf-8')
    two = golden.recorder_hash(str(tmp_path))
    me = tmp_path / 'golden.py'
    me.write_text('z\n', encoding='utf-8')
    monkeypatch.setattr(golden, '__file__', str(me))
    assert len({one, two, golden.recorder_hash(str(tmp_path))}) == 3


def test_a_task_the_base_does_not_record_is_no_pass(tmp_path, monkeypatch, capsys):
    # a base failure compared nothing: the CLI says why and fails, unless the change declares the task (a new one)
    base, new = tmp_path / 'base', tmp_path / 'new'
    for d in (base, new):
        d.mkdir()
        (d / 'heal_a.gz').write_bytes(b'')
    (new / 'ai_open.gz').write_bytes(b'')
    (base / 'ai_open.failed').write_text('')
    (base / 'ai_open.txt').write_text("No module named 'engine.ports.readonly'", encoding='utf-8')
    monkeypatch.setattr(golden.Run, 'difference', lambda self, name: None)
    for changed, code in [(set(), 1), ({'ai_open'}, 0)]:
        monkeypatch.setattr(golden, 'records', lambda *a, **k: golden.Run('1' * 40, str(base), str(new), changed,
                                                                         ['heal_a', 'ai_open']))
        monkeypatch.setattr(golden.sys, 'argv', ['golden.py'])
        assert golden.main() == code
        out = capsys.readouterr().out
        assert 'ai_open        not recordable on the base' in out and 'engine.ports.readonly' in out


def test_a_recorder_helper_the_base_lacks_is_copied_over_with_the_recorder(repo, tmp_path):
    """Review 1120bb P2 #3: the base tree got this checkout's simrecord and observe.py but not engine/ports/readonly.py,
    which observe.py had come to import -- a base before it could not be recorded (ModuleNotFoundError). A helper
    (RECORDER_HELPERS) goes over with the recorder whether the base has it or not."""
    r, first, _ = repo
    later = _commit(r, 'three', {rel.replace(os.sep, '/'): 'x = 1\n' for rel in golden.RECORDER_RELS})
    for rel in golden.RECORDER_HELPERS:
        p = r / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('helper = 1\n', encoding='utf-8')
    assert golden.missing_recorder(str(r), later) == []          # a helper the base lacks is no reason to refuse
    tree = tmp_path / 'golden-tree'
    try:
        golden.prepare_tree(later, str(r), str(tree))
        for rel in golden.RECORDER_RELS + golden.RECORDER_HELPERS:
            assert (tree / rel).read_text(encoding='utf-8') == (r / rel).read_text(encoding='utf-8')
    finally:
        _git(r, 'worktree', 'remove', '--force', str(tree))


def _imports(path):
    """The modules a file imports, anywhere in it (simrecord imports where it uses), as dotted names."""
    import ast
    out = set()
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            out.add(node.module)
            out |= {f'{node.module}.{a.name}' for a in node.names}
    return out


def test_every_lab_module_the_recorder_imports_goes_over_with_it_or_is_the_bases():
    """The class of 1120bb P2 #3: a recorder file that comes to import a module of experimental/cnv must say whether
    the module goes over with it (RECORDER_RELS / RECORDER_HELPERS) or is the base's own simulator (RECORDER_READS);
    unsaid, a base without it cannot be recorded."""
    cnv = ROOT / 'experimental' / 'cnv'

    def in_lab(name):
        p = cnv.joinpath(*name.split('.'))
        return p.with_suffix('.py').exists() or (p / '__init__.py').exists()

    def module(rel):
        return Path(rel).with_suffix('').relative_to(Path('experimental', 'cnv')).as_posix().replace('/', '.')
    files = golden.RECORDER_RELS + golden.RECORDER_HELPERS
    seen = set()
    for rel in files:
        seen |= {m for m in _imports(ROOT / rel) if in_lab(m)}
    seen = {m for m in seen if not any(o.startswith(m + '.') for o in seen)}   # a package stands for its module
    assert sorted(seen - {module(rel) for rel in files} - set(golden.RECORDER_READS)) == []
    assert sorted(set(golden.RECORDER_READS) - seen) == []      # none listed that it no longer imports
