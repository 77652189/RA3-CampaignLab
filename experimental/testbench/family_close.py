r"""Close one family moved into a kernel module (ADR 0029, refactor line R) in one command, one line per check:

    python -X utf8 experimental/testbench/family_close.py                 # HEAD against its parent
    python -X utf8 experimental/testbench/family_close.py --base <rev>    # against another base (e.g. a step's parent)
    python -X utf8 experimental/testbench/family_close.py --skip-tests -n 2

Run it from the line's own worktree after committing the step (uncommitted work under experimental/ is recorded too,
as tests/golden does, but the test pick reads base..HEAD). In order:
  1-3. golden (experimental/testbench/golden.py: its per-commit cache under work\logs\golden, the base recorded in
       the sibling RA3-CampaignLab-golden with this checkout's recorder): every simrecord task recorded on the base
       and here, compared frame by frame (simrecord.first_difference, what `simrecord.py compare` prints);
  4.   the centre (tests/guards/test_kernel.py CENTER: sim.py lines, Sim methods, Body fields, simunits defs, cells
       with old code) on the base and here, against the table: over it is red, under it says what to lower it to;
  5.   the affected tests of base..HEAD (affected_tests.py --cmd, with -n replaced: -n 2 until the machine's CPU token
       pool exists, handoff-r2 T5); a red test is rerun on the base (in the golden tree) and one red there too is
       reported as old, not this step's. --light (a small family: few fields, read nowhere else -- user 11-18) runs
       only the test files base..HEAD changed (coordinator 11-18; none: nothing) and says the rest of the affected
       tests are left to the coordinator's full run.
Each check prints one line with its log (work\logs\family_close_<stamp>_<check>.log). Exit 0 = all green (old reds
allowed); 1 = something to fix.
"""
import argparse
import ast
import datetime
import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
KERNEL_GUARD = 'tests/guards/test_kernel.py'
CENTER_SOURCES = {'sim_src': 'experimental/cnv/sim.py', 'units_src': 'experimental/cnv/engine/data/units.py',
                  'loop_src': 'experimental/cnv/engine/loop/frame.py'}
WORKERS = 2          # until the CPU token pool (handoff-r2 T5) says how many

_cpu_spec = importlib.util.spec_from_file_location('_cpupool_for_family_close', os.path.join(HERE, 'cpupool.py'))
cpupool = importlib.util.module_from_spec(_cpu_spec)
_cpu_spec.loader.exec_module(cpupool)
pytest_run = cpupool._load('pytest_run', os.path.join(HERE, 'pytest_run.py'))


def git(root, *args):
    r = subprocess.run(['git', '-C', root, *args], capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout if r.returncode == 0 else None


# ---- 4. the centre --------------------------------------------------------------------------------------------

def centre_tools(guard_src):
    """(CENTER, center) from the kernel guard's source: the table literal, and its own `center` function (with the
    helper it calls) run on given sources -- the guard stays the one place the counting rule is written."""
    tree = ast.parse(guard_src)
    table, defs = None, []
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'CENTER' for t in n.targets):
            table = ast.literal_eval(n.value)
        elif isinstance(n, ast.FunctionDef) and n.name in ('center', '_old_code', '_sim_fields'):
            defs.append(n)
    if table is None or not any(d.name == 'center' for d in defs):
        raise ValueError(f'{KERNEL_GUARD} has no CENTER table or center() any more')
    ns = {'ast': ast, 'CNV': None}
    exec(compile(ast.Module(body=defs, type_ignores=[]), KERNEL_GUARD, 'exec'), ns)
    return table, ns['center']


def centre_line(before, now, table):
    """(ok, one line): each count as before->now, red where now is over the table, and the table to write where
    now is under it (test_the_centre_only_shrinks wants them equal)."""
    parts, over, under = [], [], []
    for k, v in now.items():
        b = before.get(k) if before else None
        parts.append(f'{k} {v}' if b in (None, v) else f'{k} {b}->{v}')
        if v > table[k]:
            over.append(f'{k} {v} > {table[k]}')
        elif v < table[k]:
            under.append(k)
    text = '; '.join(parts)
    if over:
        return False, f'中心变大（红）：{", ".join(over)}。{text}'
    if under:
        return False, f'中心变小、上限表没下调（test_kernel CENTER 改成 {now}）。{text}'
    return True, f'中心与上限表一致：{text}'


def centre(root, base):
    with open(os.path.join(root, KERNEL_GUARD), encoding='utf-8') as f:
        table, count = centre_tools(f.read())
    now = count(**{k: open(os.path.join(root, p), encoding='utf-8').read() for k, p in CENTER_SOURCES.items()})
    olds = {k: git(root, 'show', f'{base}:{p}') for k, p in CENTER_SOURCES.items()}
    before = count(**olds) if all(v is not None for v in olds.values()) else None
    return centre_line(before, now, table)


# ---- 1-3. golden ----------------------------------------------------------------------------------------------

def golden_line(run, log):
    """(ok, one line) from a golden.Run, the per-task detail written to `log` (an open file)."""
    same, declared, skipped, bad = [], [], [], []
    for n in run.names:
        if run.failed('new', n):
            bad.append(n)
            log.write(f'{n}: FAILED to record here\n{run.failed("new", n)}\n')
        elif run.failed('base', n):         # nothing compared: red unless the change declares the task (as golden.py)
            (skipped if n in run.changed else bad).append(n)
            log.write(f'{n}: not recordable on the base\n{run.failed("base", n)}\n')
        else:
            d = run.difference(n)
            log.write(f'{n}: {"same" if not d else d}\n')
            (same if not d else declared if n in run.changed else bad).append(n)
    head = f'底版 {run.base_rev[:10]} 对本工作区：{len(same)}/{len(run.names)} same'
    tail = ''.join([f'；声明改了 {declared}' if declared else '', f'；底版录不了（已声明）{skipped}' if skipped else ''])
    if bad:
        return False, f'逐帧记录有差异或录不了（红）：{bad}。{head}{tail}'
    return True, head + tail


# ---- 5. affected tests ----------------------------------------------------------------------------------------

def with_workers(cmd, n):
    """affected_tests' pytest command with its -n replaced (or added)."""
    if re.search(r'(^|\s)-n\s+\d+', cmd):
        return re.sub(r'(^|\s)-n\s+\d+', lambda m: f'{m.group(1)}-n {n}', cmd, count=1)
    return cmd.replace(' -m pytest ', f' -m pytest -n {n} ', 1)


def tests_line(counts, red, old_red, why=''):
    """(ok, one line): red tests also red on the base are old (someone else's), the rest are this step's. `why`: how
    a run that gave no summary ended (run_pytest)."""
    new = [t for t in red if t not in old_red]
    tally = ', '.join(f'{v} {k}' for k, v in counts.items()) or 'no summary'
    if not counts and not red:
        return False, f'pytest 没给出结果（{why or "看日志"}）'
    if new:
        return False, f'本步新红 {len(new)} 个：{" ".join(new)}（{tally}）'
    if red:
        return True, f'{tally}；红的 {len(red)} 个在底版上也红（旧红，不是本步的）'
    return True, tally


def affected(root, base, n, log_path, golden):
    pick = subprocess.run([sys.executable, '-X', 'utf8', os.path.join(HERE, 'affected_tests.py'), '--cmd',
                           f'{base}..HEAD'], cwd=root, capture_output=True, text=True, encoding='utf-8',
                          errors='replace')
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(pick.stderr)
    cmd = pick.stdout.strip().splitlines()[-1] if pick.stdout.strip() else ''
    if pick.returncode or ' -m pytest ' not in cmd:
        return False, f'affected_tests 没给出命令（exit {pick.returncode}）'
    return judge(with_workers(cmd, n).split(' -m pytest ', 1)[1].split() + ['-rf'], root, base, n, log_path, golden)


def changed_tests(root, base):
    """The test files base..HEAD changed that are still here (tests/**/test_*.py): --light runs them (coordinator
    11-18: M14 changed two test_simai lines and its light close ran none of them)."""
    out = git(root, 'diff', '--name-only', f'{base}..HEAD', '--', 'tests')
    return sorted(p for p in out.split() if p.startswith('tests/') and os.path.basename(p).startswith('test_')
                  and p.endswith('.py') and os.path.exists(os.path.join(root, p)))


def judge(args, root, base, n, log_path, golden):
    """pytest with `args` in `root`, its reds rerun on the base: (ok, the line)."""
    counts, red, why = pytest_run.run_pytest(args, root, log_path)
    old = set()
    if red:   # rerun the reds on the base, in the golden tree (held under golden's lock)
        with golden.Lock(os.path.join(golden.CACHE, 'golden.lock')):
            golden.prepare_tree(base, root)
            git(golden.TREE, 'checkout', '--', golden.SIMRECORD_REL)   # the base's own recorder for its tests
            here = [t for t in red if os.path.exists(os.path.join(golden.TREE, t.split('::')[0]))]
            if here:   # --timeout for a base before T7 (since then conftest marks each test with its layer's limit)
                _, old_red, _ = pytest_run.run_pytest(['-n', str(n), '--timeout', '3000', '-p', 'no:cacheprovider', '-q', '-rf',
                                            *here], golden.TREE, log_path)
                old = set(old_red)
    return tests_line(counts, red, old, why)


LIGHT = '受影响测试留给全量（--light：小族，用户 11-18 定；总控约每 3 步全量一次）'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--base', help='the base commit (default: HEAD~1, or HEAD with uncommitted work, as golden)')
    ap.add_argument('-n', type=int, default=WORKERS, help=f'pytest workers (default {WORKERS})')
    ap.add_argument('-j', type=int, default=None, help='simrecord jobs per side (golden default)')
    ap.add_argument('--skip-tests', action='store_true', help='checks 1-4 only')
    ap.add_argument('--light', action='store_true',
                    help='a small family (user 11-18): checks 1-4, the affected tests left to the coordinator\'s full run')
    a = ap.parse_args(argv)
    golden = cpupool._load('golden', os.path.join(HERE, 'golden.py'))
    env = dict(os.environ)
    if a.base:
        env['GOLDEN_BASE'] = a.base
    base = golden.base_rev(ROOT, env)
    stamp = datetime.datetime.now().strftime('%m%d_%H%M%S')
    logs = os.path.join(golden.labpaths.WORK, 'logs')
    os.makedirs(logs, exist_ok=True)
    log = lambda check: os.path.join(logs, f'family_close_{stamp}_{check}.log')
    print(f'底版 {base[:10]}，本工作区 {git(ROOT, "rev-parse", "--short=10", "HEAD").strip()}')
    results = []

    path = log('golden')
    with open(path, 'w', encoding='utf-8') as f:
        try:
            ok, line = golden_line(golden.records(env=env, jobs=a.j), f)
        except golden.Skip as e:
            ok, line = False, f'没法比：{e}'
    results.append((ok, '逐帧记录', line, path))
    print(('✓' if ok else '✗'), '逐帧记录', line, '|', path, flush=True)

    ok, line = centre(ROOT, base)
    results.append((ok, '中心计数', line, None))
    print(('✓' if ok else '✗'), '中心计数', line, flush=True)

    if a.light:
        own = [] if a.skip_tests else changed_tests(ROOT, base)
        if own:     # the step's own test files still run (coordinator 11-18); the rest is left to the full run
            path = log('tests')
            ok, line = judge(['-n', str(a.n), '-p', 'no:cacheprovider', '-q', '-rf', *own], ROOT, base, a.n, path,
                             golden)
            line = f'本步改过的测试文件 {len(own)} 个：{line}；其余{LIGHT}'
            results.append((ok, '受影响测试', line, path))
            print(('✓' if ok else '✗'), '受影响测试', line, '|', path, flush=True)
        else:
            results.append((True, '受影响测试', LIGHT, None))
            print('·', '受影响测试', LIGHT, flush=True)
    elif not a.skip_tests:
        path = log('tests')
        ok, line = affected(ROOT, base, a.n, path, golden)
        results.append((ok, '受影响测试', line, path))
        print(('✓' if ok else '✗'), '受影响测试', line, '|', path, flush=True)
    return 0 if all(r[0] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
