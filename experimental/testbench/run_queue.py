"""Bench batch queue: run many cnv checks in bulk and unattended, one subprocess each, a result file for every one.

    python -I -X utf8 experimental/testbench/run_queue.py aitfany:a aitfmax:a            checks as mission:check
    python -I -X utf8 experimental/testbench/run_queue.py --file work/queue.txt           one mission:check a line (# comments)
    python -I -X utf8 experimental/testbench/run_queue.py --prefix engine_ --jobs 2       every check in checks/engine_*.py
    ... --resume   skip a check that already has a PASS / FAIL result at the same git HEAD (an ERROR / DROPOUT is run again)
    ... --resume-any  the same, whatever HEAD the result was made at (the other lines commit all day)
    ... --verbose  print every check's whole output as it comes in (default: one line a check)
    ... --no-build the mods are already built;  --retry N  a dropped-out run is run again by itself N times (default 1,
                   without building again, like ra3bench's cnv_check);  --timeout S  one run's limit, seconds

Each check runs as `run_check.py <mission> <check>` in its own process (the same code ra3bench's cnv_check runs), so its
lock state is its own. This script writes no lock: the bench has two slots (slots.py) and a run that finds them full
waits its turn there, the SDK compiles are one at a time under build_lock -- --jobs N only says how many processes are
started at once (default 2 = the slots).

Results: work/bench_results/<mission>__<check>.json (the latest run of that check) and one line a run appended to
work/bench_results/summary.tsv. Verdicts: PASS / FAIL (the counters against the check's expectations), NOEXPECT (the check
expects nothing: readings only), DROPOUT (the capture stopped before the check was over, says nothing about the
mission), ERROR (build failed, bench error, no verdict in the output, timeout, crash).
"""
import argparse
import concurrent.futures
import datetime
import json
import os
import re
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RESULTS = os.path.join((os.environ.get('CNV_WORK') or os.path.join(ROOT, 'work')), 'bench_results')
RUN_CHECK = os.path.join(HERE, 'run_check.py')
# the interpreter ra3bench itself runs in (it has the mcp package bench_mcp imports)
BENCH_PY = os.path.join(os.path.dirname(ROOT), 'envs', 'bench_mcp', 'Scripts', 'python.exe')
SUMMARY_COLUMNS = ('start', 'head', 'mission', 'check', 'verdict', 'seconds', 'file')
DONE = ('PASS', 'FAIL', 'NOEXPECT')       # --resume skips these; ERROR and DROPOUT say nothing about the check


# ---------------------------------------------------------------- input

def parse_item(text):
    """'mission:check' -> (mission, check); 'mission' or 'mission:' -> check ''. A bad item is a ValueError."""
    mission, _, check = text.strip().partition(':')
    if not mission or not re.fullmatch(r'[A-Za-z0-9_]+', mission) or not re.fullmatch(r'[A-Za-z0-9_]*', check):
        raise ValueError(f'not mission:check: {text!r}')
    return mission, check


def read_list(path):
    """One check a line; blank lines and # comments (whole line or after the check) are skipped."""
    with open(path, encoding='utf-8-sig') as f:
        return [parse_item(line.split('#')[0]) for line in f if line.split('#')[0].strip()]


def listing(prefix):
    """(mission, check) of every check in a checks/<prefix>*.py module, in cnv_list's order (modules by name, builds and
    checks as each declares them); a build the module only declares as a pair is (build, '')."""
    # in a child started in experimental/cnv (python -c puts its cwd first on the path; no -I for that reason), so this
    # file needs no sys.path edit of its own (tests/test_architecture.py G4 ratchet)
    code = ('import importlib, json, sys\n'
            'import parts  # noqa: F401  (puts experimental/campaign on the path, as build.py does)\n'
            'import registry\n'
            'out = []\n'
            'for name in registry.modules():\n'
            '    folder, _, module = name.partition(".")\n'
            '    if folder != "checks" or not module.startswith(sys.argv[1]):\n'
            '        continue\n'
            '    mod = importlib.import_module(name)\n'
            '    out += [(b, c) for b, table in getattr(mod, "CHECKS", {}).items() for c in table]\n'
            '    out += [(b, "") for b in getattr(mod, "PAIR_BUILDS", {})]\n'
            'print("LISTING " + json.dumps(out))\n')
    run = subprocess.run([sys.executable, '-X', 'utf8', '-c', code, prefix], cwd=os.path.join(ROOT, 'experimental', 'cnv'),
                         capture_output=True, text=True, encoding='utf-8')
    line = next((x for x in run.stdout.splitlines() if x.startswith('LISTING ')), None)
    if run.returncode or line is None:
        raise RuntimeError(f'listing checks/{prefix}* failed:\n{run.stderr[-2000:]}')
    return [tuple(x) for x in json.loads(line[len('LISTING '):])]


def collect(items, file=None, prefix=None, lister=listing):
    """The queue: the command line's items, then the file's, then the prefix's -- each once, in first-seen order."""
    queue = [parse_item(x) for x in items or ()]
    if file:
        queue += read_list(file)
    if prefix:
        found = lister(prefix)
        if not found:
            raise ValueError(f'no check file starts with {prefix!r}')
        queue += found
    return list(dict.fromkeys(queue))


# ---------------------------------------------------------------- one run

def head():
    r = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, cwd=ROOT)
    return r.stdout.strip() or 'unknown'


def subprocess_runner(timeout=3600, python=None):
    """runner(mission, check, build) -> (exit code, output): run_check.py in its own process. A timeout is code None."""
    py = python or (BENCH_PY if os.path.exists(BENCH_PY) else sys.executable)

    def run(mission, check, build):
        args = [py, '-I', '-X', 'utf8', RUN_CHECK, mission, check] + ([] if build else ['--no-build'])
        try:
            r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=ROOT,
                               timeout=timeout)
        except subprocess.TimeoutExpired as e:
            out = e.stdout.decode('utf-8', 'replace') if isinstance(e.stdout, bytes) else (e.stdout or '')
            return None, out + f'\nTIMEOUT after {timeout}s'
        return r.returncode, r.stdout + (('\n' + r.stderr) if r.stderr.strip() else '')
    return run


def judge(code, output):
    """(verdict, expectation lines, readings line) from what run_check printed."""
    lines = output.splitlines()
    expectations = [x for x in lines if x.startswith(('PASS ', 'FAIL '))]
    readings = next((x for x in lines if x.startswith('counters (')), '')
    result = next((x[7:].strip() for x in lines if x.startswith('RESULT ')), '')
    if code is None or code != 0 or output.startswith('BUILD FAILED'):
        verdict = 'ERROR'
    elif 'BENCH DROPOUT' in output:
        verdict = 'DROPOUT'
    elif result in ('PASS', 'FAIL'):
        verdict = result
    elif result == 'NO EXPECTATIONS':
        verdict = 'NOEXPECT'
    else:
        verdict = 'ERROR'                  # no RESULT line: the run stopped before the judge (bench_start failed ...)
    return verdict, expectations, readings


def run_one(mission, check, runner, git_head, build=True, retry=1):
    """Run a check (a dropout again up to `retry` times, without building) and describe it as one result dict."""
    started = datetime.datetime.now()
    t0 = time.monotonic()
    attempts = []
    while True:
        try:
            code, output = runner(mission, check, build and not attempts)
        except Exception as e:                                   # a runner that cannot even start is an ERROR too
            code, output = None, f'RUNNER CRASHED: {type(e).__name__}: {e}'
        verdict, expectations, readings = judge(code, output)
        attempts.append(verdict)
        if verdict != 'DROPOUT' or len(attempts) > retry:
            break
    return dict(mission=mission, check=check, head=git_head, start=started.isoformat(timespec='seconds'),
                seconds=round(time.monotonic() - t0, 1), verdict=verdict, attempts=attempts,
                expectations=expectations, readings=readings, exit_code=code, output=output)


# ---------------------------------------------------------------- results

def result_path(results_dir, mission, check):
    return os.path.join(results_dir, f'{mission}__{check}.json')


def load_result(results_dir, mission, check):
    try:
        with open(result_path(results_dir, mission, check), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


_write_lock = threading.Lock()


def write_result(results_dir, result):
    """The check's json, and a line on summary.tsv (a header when the file is new)."""
    os.makedirs(results_dir, exist_ok=True)
    path = result_path(results_dir, result['mission'], result['check'])
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    summary = os.path.join(results_dir, 'summary.tsv')
    row = [result['start'], result['head'], result['mission'], result['check'], result['verdict'],
           str(result['seconds']), os.path.basename(path)]
    with _write_lock, open(summary, 'a', encoding='utf-8', newline='') as f:
        if f.tell() == 0:
            f.write('\t'.join(SUMMARY_COLUMNS) + '\n')
        f.write('\t'.join(row) + '\n')
    return path


def already_done(results_dir, mission, check, git_head, any_head=False):
    """A PASS / FAIL / NOEXPECT result at this HEAD (any_head: at any HEAD -- the other lines commit all day)."""
    old = load_result(results_dir, mission, check)
    return bool(old) and (any_head or old.get('head') == git_head) and old.get('verdict') in DONE


# ---------------------------------------------------------------- the queue

def line_of(result):
    reading = result['readings'] or (result['output'].strip().splitlines() or [''])[-1]
    retried = f" (tries {'>'.join(result['attempts'])})" if len(result['attempts']) > 1 else ''
    return f"{result['verdict']:8} {result['mission']}:{result['check']}  {result['seconds']:.0f}s{retried}  {reading[:100]}"


def run_queue(queue, runner, results_dir=RESULTS, jobs=2, resume=False, build=True, retry=1, verbose=False,
              git_head=None, out=None, any_head=False):
    """Run the checks, `jobs` processes at a time; returns {(mission, check): result}. Skipped ones (resume) are not in it."""
    git_head = git_head or head()
    out = out or (lambda text: print(text, flush=True))       # flushed: a log file shows the queue as it goes
    todo = []
    for mission, check in queue:
        if resume and already_done(results_dir, mission, check, git_head, any_head):
            old = load_result(results_dir, mission, check)
            out(f'SKIP     {mission}:{check}  already {old["verdict"]} at {old["head"]}')
        else:
            todo.append((mission, check))
    results, shown = {}, threading.Lock()

    def work(item):
        result = run_one(*item, runner, git_head, build, retry)
        write_result(results_dir, result)
        with shown:
            out(line_of(result))
            if verbose:
                out(result['output'].rstrip() + '\n')
        return item, result

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = [pool.submit(work, item) for item in todo]
        try:
            for f in concurrent.futures.as_completed(futures):
                item, result = f.result()
                results[item] = result
        except KeyboardInterrupt:
            pool.shutdown(wait=False, cancel_futures=True)
            raise
    return results


def summary_line(results):
    count = {}
    for r in results.values():
        count[r['verdict']] = count.get(r['verdict'], 0) + 1
    return f'{len(results)} run: ' + ', '.join(f'{v} {n}' for v, n in sorted(count.items())) if results else '0 run'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('checks', nargs='*', metavar='mission:check')
    ap.add_argument('--file', help='a list, one mission:check a line')
    ap.add_argument('--prefix', help='every check of the checks/<prefix>*.py modules (engine_ ...)')
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--resume', action='store_true', help='skip a check with a PASS / FAIL result at this git HEAD')
    ap.add_argument('--resume-any', action='store_true', help='like --resume, whatever HEAD the result was made at')
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--no-build', action='store_true')
    ap.add_argument('--retry', type=int, default=1, help='runs again for a dropout (default 1)')
    ap.add_argument('--timeout', type=int, default=3600, help='seconds one run may take (default 3600)')
    ap.add_argument('--results', default=RESULTS)
    a = ap.parse_args(argv)
    try:
        queue = collect(a.checks, a.file, a.prefix)
    except (ValueError, OSError) as e:
        sys.exit(f'run_queue: {e}')
    if not queue:
        sys.exit('run_queue: nothing to run (mission:check, --file or --prefix)')
    print(f'{len(queue)} checks, {a.jobs} at a time -> {a.results}', flush=True)
    results = run_queue(queue, subprocess_runner(a.timeout), a.results, a.jobs, a.resume or a.resume_any,
                        not a.no_build, a.retry, a.verbose, any_head=a.resume_any)
    print(summary_line(results))
    sys.exit(0 if all(r['verdict'] in ('PASS', 'NOEXPECT') for r in results.values()) else 1)


if __name__ == '__main__':
    main()
