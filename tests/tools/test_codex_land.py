"""Exercise the landing command against disposable local repositories."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
TRAILER = 'Co-authored-by: Codex <codex@example.test>'


def git(cwd, *args):
    result = subprocess.run(['git', *args], cwd=cwd, capture_output=True, encoding='utf-8')
    assert result.returncode == 0, (args, result.stdout, result.stderr)
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    origin = tmp_path / 'origin.git'
    main = tmp_path / 'RA3-CampaignLab'
    tree = tmp_path / 'RA3-CampaignLab-cx-demo'
    git(tmp_path, 'init', '--bare', '--initial-branch=main', str(origin))
    git(tmp_path, 'init', '--initial-branch=main', str(main))
    git(main, 'config', 'user.email', 'local@example.test')
    git(main, 'config', 'user.name', 'Local Coordinator')
    git(main, 'config', 'commit.gpgsign', 'false')
    git(main, 'remote', 'add', 'origin', str(origin))

    tool_dir = main / 'experimental' / 'outsource'
    tool_dir.mkdir(parents=True)
    for filename in ('codex_land.py', 'codex_task.py'):
        shutil.copyfile(ROOT / 'experimental' / 'outsource' / filename, tool_dir / filename)
    picker_dir = main / 'experimental' / 'testbench'
    picker_dir.mkdir()
    (picker_dir / 'affected_tests.py').write_text(
        'import sys\n'
        'assert len(sys.argv) == 3 and sys.argv[1] == "--cmd" and ".." in sys.argv[2]\n'
        'print("picker selected the guard", file=sys.stderr)\n'
        'print("python -X utf8 -m pytest -q -p no:cacheprovider guards/test_gate.py")\n', encoding='utf-8')
    (main / 'guards').mkdir()
    (main / 'guards' / 'test_gate.py').write_text(
        'from pathlib import Path\n'
        'def test_gate():\n'
        '    assert Path("allowed.txt").read_text().strip() != "red"\n', encoding='utf-8')
    (main / '.gitignore').write_text('/shared/\n/work/\n/local-work/\n', encoding='utf-8')
    (main / 'allowed.txt').write_text('top\nmiddle one\nmiddle two\nmiddle three\nbottom\n', encoding='utf-8')
    git(main, 'add', '.')
    git(main, 'commit', '-m', 'base')
    git(main, 'push', 'origin', 'main')
    git(main, 'worktree', 'add', '--detach', str(tree), 'origin/main')

    done = main / 'shared' / 'codex_queue_b' / 'done'
    done.mkdir(parents=True)
    (done / 'demo.md').write_text(
        f'Files: {main.as_posix()}/allowed.txt, `second file.txt` (new)\n\nTests: as selected\n', encoding='utf-8')
    return main, tree, origin


def land(main, tree, *args):
    env = {**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
    return subprocess.run(
        [sys.executable, '-I', '-X', 'utf8', 'experimental/outsource/codex_land.py', str(tree),
         '-m', 'Land demo', '--co-author', TRAILER, *args], cwd=main, env=env,
        capture_output=True, encoding='utf-8')


def log_path(main):
    return main / 'work' / 'logs' / 'land_demo.log'


def test_red_test_stops_push(repo):
    main, tree, origin = repo
    head = git(tree, 'rev-parse', 'HEAD')
    (tree / 'allowed.txt').write_text('red\n', encoding='utf-8')
    (tree / 'second file.txt').write_text('new\n', encoding='utf-8')
    before = git(tree, 'status', '--porcelain')
    preview = land(main, tree, '--dry-run')
    assert preview.returncode == 0, preview.stderr
    assert 'second file.txt' in preview.stdout
    assert git(tree, 'rev-parse', 'HEAD') == head
    assert git(tree, 'status', '--porcelain') == before
    assert not log_path(main).exists()

    # Advance the remote after the linked worktree was started, without updating main's local branch.
    upstream = main.parent / 'upstream'
    git(main.parent, 'clone', str(origin), str(upstream))
    (upstream / 'upstream.txt').write_text('upstream\n', encoding='utf-8')
    git(upstream, 'add', 'upstream.txt')
    git(upstream, '-c', 'user.name=Upstream', '-c', 'user.email=upstream@example.test',
        '-c', 'commit.gpgsign=false', 'commit', '-m', 'advance main')
    git(upstream, 'push', 'origin', 'main')
    remote_tip = git(origin, 'rev-parse', 'main')

    result = land(main, tree, '--remove')
    assert result.returncode != 0
    assert 'affected tests failed (exit 1)' in result.stderr
    assert git(origin, 'rev-parse', 'main') == remote_tip
    assert git(tree, 'rev-parse', 'HEAD^') == remote_tip
    assert git(main, 'symbolic-ref', 'HEAD') == 'refs/heads/main'
    assert git(main, 'rev-parse', 'HEAD') == head
    log = log_path(main).read_text(encoding='utf-8')
    assert 'picker selected the guard' in log and '1 failed' in log and 'pytest exit code: 1' in log


def test_rejected_push_keeps_worktree(repo):
    main, tree, origin = repo
    remote_tip = git(origin, 'rev-parse', 'main')
    hook = origin / 'hooks' / 'pre-receive'
    hook.write_bytes(b'#!/bin/sh\necho "reject demo landing" >&2\nexit 1\n')
    hook.chmod(0o755)
    (tree / 'allowed.txt').write_text('green\n', encoding='utf-8')

    result = land(main, tree, '--remove')
    assert result.returncode != 0
    assert 'push rejected after 3 attempts' in result.stderr
    assert 'reject demo landing' in result.stderr
    assert git(origin, 'rev-parse', 'main') == remote_tip
    kept = git(tree, 'rev-parse', 'HEAD')
    assert kept != remote_tip
    assert git(tree, 'log', '-1', '--format=%an <%ae>') == '77652189 <71443605+77652189@users.noreply.github.com>'
    assert TRAILER in git(tree, 'log', '-1', '--format=%B')
    assert log_path(main).read_text(encoding='utf-8').count('pytest exit code: 0') == 1

    hook.unlink()
    retry = land(main, tree, '--remove')
    assert retry.returncode == 0, retry.stderr
    assert git(origin, 'rev-parse', 'main') == kept
    assert git(main, 'log', '--format=%H', f'origin/main..{kept}') == ''
    assert not tree.exists()


@pytest.mark.parametrize('scenario', ['unrelated', 'same_file', 'conflict', 'changed_test'])
def test_push_retry(repo, scenario):
    main, tree, origin = repo
    upstream = main.parent / 'racer'
    git(main.parent, 'clone', str(origin), str(upstream))
    if scenario == 'same_file':
        original = (upstream / 'allowed.txt').read_text(encoding='utf-8')
        (upstream / 'allowed.txt').write_text(original.replace('bottom', 'remote'), encoding='utf-8')
        local = original.replace('top', 'local')
        expected = local.replace('bottom', 'remote')
    elif scenario == 'changed_test':
        (upstream / 'guards' / 'test_gate.py').write_text(
            'def test_gate():\n    assert False\n', encoding='utf-8')
        local = 'local\n'
    else:
        path = 'unrelated.txt' if scenario == 'unrelated' else 'allowed.txt'
        (upstream / path).write_text('remote\n', encoding='utf-8')
        local = expected = 'local\n'
    git(upstream, 'add', '.')
    git(upstream, '-c', 'user.name=Upstream', '-c', 'user.email=upstream@example.test',
        '-c', 'commit.gpgsign=false', 'commit', '-m', 'advance main during landing')
    upstream_head = git(upstream, 'rev-parse', 'HEAD')
    (tree / 'allowed.txt').write_text(local, encoding='utf-8')

    # Publish once, after the initial tests and after the first push sees the old remote tip.
    hook = main / '.git' / 'hooks' / 'pre-push'
    hook.write_bytes(b'#!/bin/sh\nset -e\n'
                     b'if [ ! -f ../racer/.git/raced ]; then\n'
                     b'    touch ../racer/.git/raced\n'
                     b'    unset $(git rev-parse --local-env-vars)\n'
                     b'    git -C ../racer push --no-verify origin main\n'
                     b'fi\n')
    hook.chmod(0o755)

    result = land(main, tree, '--remove')
    assert 'Push rejected (attempt 1/3)' in result.stdout, (result.stdout, result.stderr)
    log = log_path(main).read_text(encoding='utf-8')
    if scenario == 'conflict':
        assert result.returncode != 0
        assert 'git rebase failed' in result.stderr and 'CONFLICT' in result.stderr
        assert git(origin, 'rev-parse', 'main') == upstream_head
        assert git(tree, 'status', '--porcelain') == 'UU allowed.txt'
        assert git(tree, 'rev-parse', 'REBASE_HEAD')
        exit_codes = [0]
    elif scenario == 'changed_test':
        assert result.returncode == 1, (result.stdout, result.stderr)
        assert 'affected tests failed (exit 1)' in result.stderr
        assert git(origin, 'rev-parse', 'main') == upstream_head
        assert git(tree, 'rev-parse', 'HEAD^') == upstream_head
        exit_codes = [0, 1]
    else:
        assert result.returncode == 0, result.stderr
        assert git(origin, 'rev-parse', 'main^') == upstream_head
        assert git(origin, 'show', 'main:allowed.txt') == expected.strip()
        assert not tree.exists()
        assert 'Rerunning affected tests' in result.stdout
        exit_codes = [0, 0]
    assert log.count('picker selected the guard') == len(exit_codes)
    assert [line for line in log.splitlines() if line.startswith('pytest exit code: ')] == [
        f'pytest exit code: {code}' for code in exit_codes
    ]


def test_junction_stops_removal(repo):
    main, tree, origin = repo
    tip = git(tree, 'rev-parse', 'HEAD')
    (tree / 'allowed.txt').write_text('green\n', encoding='utf-8')
    target = main / 'work'
    target.mkdir()
    sentinel = target / 'keep.txt'
    sentinel.write_text('keep\n', encoding='utf-8')
    junction = tree / 'local-work'
    if os.name == 'nt':
        import _winapi

        _winapi.CreateJunction(str(target), str(junction))
    else:
        junction.symlink_to(target, target_is_directory=True)
    try:
        result = land(main, tree, '--remove')
        assert result.returncode != 0
        assert 'reparse point or symlink' in result.stderr and 'local-work' in result.stderr
        assert git(tree, 'rev-parse', 'HEAD') == tip
        assert git(origin, 'rev-parse', 'main') == tip
        assert sentinel.read_text(encoding='utf-8') == 'keep\n'
        assert junction.is_dir()
        assert not log_path(main).exists()
    finally:
        if os.name == 'nt':
            junction.rmdir()
        else:
            junction.unlink()


def test_outside_files_are_refused_without_changes(repo):
    main, tree, origin = repo
    base = git(origin, 'rev-parse', 'main')
    (tree / 'already committed.txt').write_text('outside\n', encoding='utf-8')
    git(tree, 'add', 'already committed.txt')
    git(tree, 'commit', '-m', 'out of scope')
    head = git(tree, 'rev-parse', 'HEAD')
    (tree / 'already staged.txt').write_text('outside\n', encoding='utf-8')
    git(tree, 'add', 'already staged.txt')
    (tree / 'untracked.txt').write_text('outside\n', encoding='utf-8')
    (tree / 'allowed.txt').write_text('inside\n', encoding='utf-8')
    before = git(tree, 'status', '--porcelain')
    index = (Path(git(tree, 'rev-parse', '--absolute-git-dir')) / 'index').read_bytes()

    result = land(main, tree)
    assert result.returncode != 0
    assert result.stderr.splitlines() == ["Land stopped: paths outside the brief's Files:",
                                          'already committed.txt', 'already staged.txt', 'untracked.txt']
    assert (Path(git(tree, 'rev-parse', '--absolute-git-dir')) / 'index').read_bytes() == index
    assert git(tree, 'status', '--porcelain') == before
    assert git(tree, 'rev-parse', 'HEAD') == head
    assert git(origin, 'rev-parse', 'main') == base
    assert not log_path(main).exists()
