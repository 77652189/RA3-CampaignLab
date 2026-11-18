"""Find the first red on the first-parent history between two full runs."""
import argparse
from collections import defaultdict
import datetime
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def full_run(path, override):
    text = re.sub(r'\x1b\[[0-9;]*m', '', path.read_text(encoding='utf-8-sig', errors='replace'))
    lines = text.splitlines()
    if not override:
        hashes = set(re.findall(r'(?<![\w])([0-9a-f]{7,40})(?![\w])', '\n'.join(lines[:8])))
        if len(hashes) != 1:
            raise ValueError(f'{path}: cannot determine the commit from the log header')
        override = hashes.pop()
    reds = set()
    for line in lines:
        match = re.match(r'^(?:FAILED|ERROR) (\S+?::[^\s\[]+(?:\[.*?\])?)(?: - .*)?$', line)
        if match:
            reds.add(match[1])
    return override, reds


def history(git, root, good, bad):
    good, bad = [git(root, 'rev-parse', '--verify', '--end-of-options', f'{rev}^{{commit}}').strip()
                 for rev in (good, bad)]
    newer = git(root, 'rev-list', '--first-parent', f'{good}..{bad}').splitlines()
    if not newer or git(root, 'rev-parse', f'{newer[-1]}^1', check=False).strip() != good:
        raise ValueError('--good must precede --bad on its first-parent history')
    return [good, *reversed(newer)]


def checkout(golden, root, tree, rev):
    git = golden.git
    if golden.labpaths._linked(tree):
        raise ValueError(f'{tree}: refusing a link or junction')
    if not tree.exists():
        git(root, 'worktree', 'add', '--detach', str(tree), rev)
        return
    registered = git(root, 'worktree', 'list', '--porcelain').split('\n\n')
    for entry in registered:
        lines = entry.splitlines()
        if lines and lines[0].startswith('worktree ') and Path(lines[0][9:]) == tree:
            if 'detached' in lines and (tree / '.git').is_file():
                break
    else:
        raise ValueError(f'{tree}: expected a registered detached worktree')
    if git(tree, 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError(f'{tree}: tracked files have local changes')
    git(tree, 'checkout', '--detach', '--no-overwrite-ignore', rev)


def probe(tree, rev, ids, log, family, cpupool, say):
    results = {}
    pending = []
    for node in ids:
        path = tree / node.split('::', 1)[0]
        if path.is_file() and path.resolve().is_relative_to(tree):
            pending.append(node)
    while pending:
        say(f'{rev[:8]}: pytest {", ".join(pending)}')
        completed = None

        # pytest creates its scratch data inside the detached worktree.
        base = tempfile.mkdtemp(prefix='.culprit-pytest-', dir=tree)

        def run(cmd, **kwargs):
            nonlocal completed
            with cpupool.hold(1, 'culprit pytest'):
                env = dict(os.environ, PYTEST_ADDOPTS='', PYTHONDONTWRITEBYTECODE='1', RA3_CPU_EXCLUSIVE='0')
                completed = subprocess.run(cmd, env=env, **kwargs)
            return completed

        family.run_pytest(
            ['-n', '0', '--timeout', '900', '-p', 'no:cacheprovider', '-vv', '-o', 'addopts=',
             '--color=no', '--basetemp', base, '--', *pending],
            tree, log, run=run, tries=1)
        statuses = {'PASSED': 'green', 'XFAIL': 'green', 'FAILED': 'red', 'ERROR': 'red'}
        for node in pending:
            seen = re.findall(rf'^{re.escape(node)} (\w+)\b', completed.stdout, re.M)
            if seen and seen[-1] in statuses:
                results[node] = statuses[seen[-1]]
        # A missing selector aborts collection for the whole batch. Retry the remaining selectors together.
        missing = set(re.findall(r'^ERROR: not found: (.+)$', completed.stderr, re.M))
        if not missing.intersection(pending):
            break
        pending = [node for node in pending if node not in missing]
    return results


def locate(commits, ids, run, subject, say):
    readings = {}

    def measure(index, nodes):
        found = run(commits[index], nodes)
        readings.update(((index, node), found.get(node, 'unknown')) for node in nodes)

    bad = len(commits) - 1
    measure(bad, ids)
    red = [node for node in ids if readings[bad, node] == 'red']
    if red:
        measure(0, red)
    bounds, answers, unresolved = {}, defaultdict(list), {}
    for node in ids:
        if node not in red:
            unresolved[node] = f'bad is {readings[bad, node]} (expected red)'
        elif readings[0, node] != 'green':
            unresolved[node] = f'good is {readings[0, node]} (expected green)'
        else:
            bounds[node] = (0, bad)

    while bounds:
        batches = defaultdict(list)
        for node, (lo, hi) in list(bounds.items()):
            if hi == lo + 1:
                answers[hi].append(node)
                del bounds[node]
                continue
            mid = (lo + hi) // 2
            unmeasured = (i for i in range(lo + 1, hi) if (i, node) not in readings)
            pick = min(unmeasured, key=lambda i: abs(i - mid), default=None)
            if pick is None:
                unresolved[node] = f'first red unresolved ({commits[lo][:8]} green, {commits[hi][:8]} red)'
                del bounds[node]
            else:
                batches[pick].append(node)
        for index, nodes in batches.items():
            measure(index, nodes)
            for node in nodes:
                lo, hi = bounds[node]
                result = readings[index, node]
                if result == 'green':
                    bounds[node] = (index, hi)
                elif result == 'red':
                    bounds[node] = (lo, index)

    for index, nodes in sorted(answers.items()):
        rev, title = commits[index][:8], subject(commits[index])
        for node in nodes:
            say(f'{node}  first red {rev} {title}  (parent {commits[index - 1][:8]} green)')
    for node, why in unresolved.items():
        say(f'{node}  {why}')
    say(f'unknown: {sum(state == "unknown" for state in readings.values())} test/commit results')
    return int(bool(unresolved))


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--good')
    parser.add_argument('--bad')
    parser.add_argument('--since-full', nargs=2, type=Path, metavar=('OLD_LOG', 'NEW_LOG'))
    parser.add_argument('tests', nargs='*', metavar='TEST_ID')
    args = parser.parse_args(argv)
    if (args.since_full and args.tests) or (not args.since_full and not (args.good and args.bad and args.tests)):
        parser.error('give --good, --bad and test IDs, or --since-full OLD_LOG NEW_LOG')
    if any('::' not in node for node in args.tests):
        parser.error('test IDs must name individual pytest tests')

    # Use family_close's rerunner and the git/pin helpers it uses for the base. Its prepare_tree also prunes
    # worktrees and copies a different recorder, so keep the dedicated checkout on the tested commit's own code.
    spec = importlib.util.spec_from_file_location('family_close', HERE / 'family_close.py')
    family = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(family)
    golden = family._load('culprit_golden', HERE / 'golden.py')
    cpupool = family._load('culprit_cpupool', HERE / 'cpupool.py')
    model = family._load('culprit_modelpin', ROOT / 'experimental/cnv/modelpin.py')
    logs = Path(golden.labpaths._work(root=os.fspath(root))) / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / f'culprit_{datetime.datetime.now():%Y%m%d_%H%M%S_%f}.log'
    started = time.monotonic()

    def say(line):
        print(line, flush=True)
        with log.open('a', encoding='utf-8') as stream:
            print(line, file=stream)

    try:
        if args.since_full:
            good, old = full_run(args.since_full[0], args.good)
            bad, new = full_run(args.since_full[1], args.bad)
            ids = sorted(new - old)
        else:
            good, bad, ids = args.good, args.bad, list(dict.fromkeys(args.tests))
        commits = history(golden.git, root, good, bad)
        say(f'{commits[0][:8]}..{commits[-1][:8]}: {len(ids)} test(s), log {log}')
        if not ids:
            return 0
        tree = root.parent / 'RA3-CampaignLab-culprit'
        # Serialize checkout and pytest. The lock lives with the allowed logs, including before the tree exists.
        with golden.Lock(str(logs / 'culprit_worktree.lock')):
            def run(rev, nodes):
                pin = golden.pin_at(root, rev)
                if pin and model.head(golden.labpaths.ENGINE_MODEL) != pin:
                    say(f'{rev[:8]}: unknown (engine model does not match {pin})')
                    return {}
                checkout(golden, root, tree, rev)
                results = probe(tree, rev, nodes, log, family, cpupool, say)
                if pin and model.head(golden.labpaths.ENGINE_MODEL) != pin:
                    say(f'{rev[:8]}: unknown (engine model changed during pytest)')
                    return {}
                return results

            return locate(commits, ids, run, lambda rev: golden.git(root, 'show', '-s', '--format=%s', rev).strip(), say)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        say(f'culprit: {exc}')
        return 1
    finally:
        say(f'elapsed: {time.monotonic() - started:.1f} s')


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    sys.exit(main())
