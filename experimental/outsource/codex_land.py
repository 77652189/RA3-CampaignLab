"""Land a completed Codex queue worktree from this repository."""

import argparse
import fnmatch
import importlib.util
import os
from pathlib import Path
import re
import stat
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'RA3-CampaignLab-cx-'
UPSTREAM = 'origin/main'
MAX_PUSH_ATTEMPTS = 3
IDENTITY = ('-c', 'user.email=71443605+77652189@users.noreply.github.com',
            '-c', 'user.name=77652189')  # AGENTS.md


class LandError(Exception):
    pass


class PushRejected(LandError):
    pass


def git(cwd, *args):
    result = subprocess.run(['git', '--no-optional-locks', *args], cwd=cwd, capture_output=True)
    if result.returncode:
        detail = '\n'.join(s.decode('utf-8', errors='replace').strip()
                           for s in (result.stdout, result.stderr) if s.strip())
        error = LandError
        if args[:2] == ('push', '--porcelain') and any(
                line.startswith(b'!\t') for line in result.stdout.splitlines()):
            error = PushRejected
        command = args[len(IDENTITY)] if args[:len(IDENTITY)] == IDENTITY else args[0]
        raise error(f'git {command} failed (exit {result.returncode})\n{detail}')
    return result.stdout.decode('utf-8', errors='surrogateescape')


def locate(path, remove):
    tree = Path(os.path.abspath(path))
    name = tree.name.removeprefix(PREFIX)
    if name == tree.name or not re.fullmatch(r'[A-Za-z0-9-]+', name):
        raise LandError(f'expected a {PREFIX}<name> worktree: {tree}')
    records = [row.split('\0') for row in git(ROOT, 'worktree', 'list', '--porcelain', '-z').split('\0\0')
               if row]
    main = Path(records[0][0].removeprefix('worktree '))
    for worktree, *metadata in records[1:]:
        if Path(worktree.removeprefix('worktree ')) == tree:
            if not tree.is_dir() or Path(git(tree, 'rev-parse', '--show-toplevel').strip()) != tree:
                raise LandError(f'worktree root is unavailable: {tree}')
            common_dir = ('rev-parse', '--path-format=absolute', '--git-common-dir')
            if Path(git(tree, *common_dir).strip()) != Path(git(ROOT, *common_dir).strip()):
                raise LandError(f'worktree belongs to another repository: {tree}')
            if remove and any(field == 'locked' or field.startswith('locked ') for field in metadata):
                raise LandError(f'worktree is locked: {tree}')
            return main, tree, name
    raise LandError(f'not a linked worktree of this repository: {tree}')


def allowed_paths(main, tree, name):
    briefs = sorted((main / 'shared').glob(f'codex_queue*/done/{name}.md'))
    if len(briefs) != 1:
        raise LandError(f'expected one completed brief for {name} under {main / "shared"}, found {len(briefs)}')
    # Use the queue's Files: syntax, without writing a bytecode cache during preflight.
    spec = importlib.util.spec_from_file_location('codex_task', Path(__file__).with_name('codex_task.py'))
    task = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(task)
    finally:
        sys.dont_write_bytecode = previous
    entries = task.files_allowed(briefs[0].read_text(encoding='utf-8-sig'))
    if entries is None:
        raise LandError(f'brief has no Files: section: {briefs[0]}')

    patterns = []
    for entry in entries:
        entry = re.sub(r'\s+\((?:new|only|create if absent)\)$', '', entry).strip('`')
        path = Path(entry.replace('\\', '/'))
        if path.is_absolute():
            for root in (main, tree):
                if path.is_relative_to(root):
                    patterns.append(path.relative_to(root).as_posix())
                    break
        else:
            patterns.append(path.as_posix())
    return patterns


def dirty_paths(tree):
    status = git(tree, 'status', '--porcelain=v1', '-z', '--no-renames', '--untracked-files=all',
                 '--ignore-submodules=none')
    return {record[3:] for record in status.split('\0') if record}


def touched_paths(tree, revisions):
    paths = git(tree, 'log', '--format=', '--name-only', '--no-renames', '-m', '-z', revisions)
    return set(filter(None, paths.split('\0')))


def check_allowed(paths, patterns):
    outside = sorted(path for path in paths if not any(fnmatch.fnmatchcase(path, p) for p in patterns))
    if outside:
        raise LandError('paths outside the brief\'s Files:\n' + '\n'.join(outside))


def check_removable(tree):
    """Inspect entries without ever descending through a junction or symlink."""
    pending = [tree]
    while pending:
        path = pending.pop()
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise LandError(f'worktree removal refused: reparse point or symlink at {path}')
        if stat.S_ISDIR(info.st_mode):
            pending.extend(path.iterdir())


def pick_tests(tree, revisions, log, log_path):
    picker = subprocess.run([sys.executable, '-X', 'utf8', 'experimental/testbench/affected_tests.py',
                             '--cmd', revisions], cwd=tree, stdout=subprocess.PIPE, stderr=log, encoding='utf-8')
    if picker.returncode:
        raise LandError(f'affected_tests.py failed (exit {picker.returncode}); see {log_path}')
    # The picker emits one space-separated argv line, with diagnostics on stderr.
    lines = picker.stdout.strip().splitlines()
    command = lines[0].split() if len(lines) == 1 else []
    if command[:5] != ['python', '-X', 'utf8', '-m', 'pytest']:
        raise LandError(f'affected_tests.py did not print its pytest command; see {log_path}')
    print(lines[0], file=log, flush=True)
    return command


def run_tests(tree, command, log, log_path, known_reds):
    log.flush()
    start = log_path.stat().st_size
    tests = subprocess.run([sys.executable, *command[1:]], cwd=tree, stdout=log, stderr=subprocess.STDOUT)
    print(f'pytest exit code: {tests.returncode}', file=log, flush=True)
    if tests.returncode == 1 and known_reds:
        with log_path.open(encoding='utf-8', errors='replace') as run:
            run.seek(start)  # this run only: pytest's short summary has one FAILED / ERROR <nodeid> line per red
            reds = set(re.findall(r'^(?:FAILED|ERROR) (\S+)', run.read(), re.M))
        if reds and reds <= set(known_reds):
            print('Known reds failed: ' + ', '.join(sorted(reds)), flush=True)
            return
    if tests.returncode:
        raise LandError(f'affected tests failed (exit {tests.returncode}); see {log_path}')


def test_and_push(tree, log_path, known_reds):
    previous_base = None
    log_path.parent.mkdir(parents=True, exist_ok=True)
    print(f'Test log: {log_path}', flush=True)
    with log_path.open('w', encoding='utf-8') as log:
        for attempt in range(1, MAX_PUSH_ATTEMPTS + 1):
            git(tree, 'fetch', 'origin', 'refs/heads/main:refs/remotes/origin/main')
            # FETCH_HEAD is per-worktree. Other landings can move the shared origin/main.
            base = git(tree, 'rev-parse', 'FETCH_HEAD').strip()
            rebase_target = (base,) if previous_base is None else ('--onto', base, previous_base)
            try:
                git(tree, *IDENTITY, 'rebase', '--no-autostash', '--no-update-refs', *rebase_target)
            except LandError as exc:
                conflicts = git(tree, 'diff', '--name-only', '--diff-filter=U').rstrip('\n')
                if not conflicts:
                    raise
                print(f'Rebase conflicts in:\n{conflicts}', file=sys.stderr, flush=True)
                git(tree, 'rebase', '--abort')
                raise LandError('rebase aborted after conflicts') from exc
            head = git(tree, 'rev-parse', 'HEAD').strip()
            if dirty_paths(tree):
                raise LandError('worktree is dirty after rebase')
            revisions = f'{base}..{head}'
            command = pick_tests(tree, revisions, log, log_path)

            if previous_base is None:
                run_tests(tree, command, log, log_path, known_reds)
            else:
                if base != previous_base or command != previous_command:
                    print('Rerunning affected tests: main moved or the test command changed.', flush=True)
                    run_tests(tree, command, log, log_path, known_reds)
                else:
                    print('Reusing affected test results: main and the test command are unchanged.',
                          flush=True)

            if dirty_paths(tree) or git(tree, 'rev-parse', 'HEAD').strip() != head:
                raise LandError('worktree changed during testing')
            try:
                git(tree, 'push', '--porcelain', 'origin', f'{head}:refs/heads/main')
            except PushRejected as exc:
                if attempt == MAX_PUSH_ATTEMPTS:
                    raise LandError(f'push rejected after {MAX_PUSH_ATTEMPTS} attempts\n{exc}') from exc
                print(f'Push rejected (attempt {attempt}/{MAX_PUSH_ATTEMPTS}); fetching and rebasing.', flush=True)
                previous_base = base
                previous_command = command
            else:
                return head


def land(args):
    main, tree, name = locate(args.worktree, args.remove)
    git_dir = Path(git(tree, 'rev-parse', '--absolute-git-dir').strip())
    for marker in ('rebase-merge', 'rebase-apply', 'MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'sequencer'):
        if (git_dir / marker).exists():
            raise LandError(f'Git operation in progress in {tree} ({marker})')
    patterns = allowed_paths(main, tree, name)
    if args.remove:
        check_removable(tree)

    changed = dirty_paths(tree)
    outgoing = f'{UPSTREAM}..HEAD'
    if not changed and not git(tree, 'log', '--format=%H', outgoing).strip():
        raise LandError(f'{tree} has no changes or unpushed commits')
    check_allowed(changed | touched_paths(tree, outgoing), patterns)
    git(tree, 'remote', 'get-url', 'origin')

    if args.dry_run:
        print(f'Dry run: {tree}')
        if changed:
            print('Would stage and commit:\n' + '\n'.join(sorted(changed)))
        print(f'Would fetch, rebase onto {UPSTREAM}, run affected tests, push and verify'
              + (', then remove the worktree.' if args.remove else '.'))
        return

    if changed:
        git(tree, '--literal-pathspecs', 'add', '-A', '--', *sorted(changed))
        git(tree, *IDENTITY, 'commit', '-m', args.message, '--trailer', args.co_author)
    pushed_head = test_and_push(tree, main / 'work' / 'logs' / f'land_{name}.log', args.known_red)
    if git(tree, 'log', '--format=%H', outgoing).strip():
        raise LandError(f'push verification failed: git log {outgoing} is not empty')
    print(f'Pushed and verified {pushed_head}')
    if args.remove:
        check_removable(tree)
        git(main, 'worktree', 'remove', str(tree))
        print(f'Removed {tree}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('worktree', type=Path)
    parser.add_argument('-m', '--message', required=True)
    parser.add_argument('--co-author', required=True, metavar='TRAILER',
                        help='full Co-authored-by: Name <email> trailer for a new commit')
    parser.add_argument('--dry-run', action='store_true', help='check eligibility without changing anything')
    parser.add_argument('--remove', action='store_true', help='remove a verified worktree with no reparse points')
    parser.add_argument('--known-red', action='append', default=[], metavar='NODEID')
    args = parser.parse_args()
    if not re.fullmatch(r'Co-authored-by: [^<>\r\n]+ <[^<>\s]+>', args.co_author, re.IGNORECASE):
        parser.error('--co-author must be a Co-authored-by: Name <email> trailer')
    if not args.message.strip():
        parser.error('commit message is empty')
    try:
        land(args)
    except (LandError, OSError, ValueError) as exc:
        print(f'Land stopped: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
