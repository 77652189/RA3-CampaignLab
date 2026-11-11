r"""外包给 Codex: hand one bounded development task to OpenAI's Codex CLI (the user's ChatGPT quota) instead of
spending Claude's. The coordinator writes the brief; this runs `codex exec` once in a worktree; the answer and the
token counts land in files the coordinator reads and checks -- Codex's word is a draft, never the proof (the
coordinator runs the long regressions, reads the diff, then commits).

  python -I -X utf8 experimental/outsource/codex_task.py BRIEF.md --dir WORKTREE [--minutes 30] [--effort medium]

  BRIEF.md   the task contract: goal, files to read, done criteria, a "Files:" section (the paths / globs it may
             change, or "none" for a read-only task; a change outside them marks the run) and a "Tests:" section
             naming the exact commands to run (one focused test file, or -k tests; never the whole suite) -- the
             rules below are added (stop after the tests pass, at most two fix rounds, then report)
  --dir      the git worktree Codex edits (never the main checkout: other lines work there)
  --minutes  safety stop only (default 60): the stop condition is the tests plus two fix rounds, not the clock --
             Codex's own review of this contract (2026-11-09): a short kill cuts work off half done
  --effort   reasoning effort, default medium (2026-11-09: high on a rule-plus-readings task spent 30+ min, most of it
             re-running long regressions); high only for a task that needs real design judgment
  --model    default gpt-6.1-sol (2026-11-09 comparison: Astra no better at 4.5x the price)
  --read-dir extra folders Codex may write in besides --dir (e.g. the main checkout's work\ for logs)
  --bench    may run the bench through run_queue.py
  --full     no sandbox, so it can bench itself (the SDK compiler crashes in any sandbox); user-approved 2026-11-09
             after line C's suppression probe took 10 blind rounds through the coordinator. The limits are then in
             the prompt only (FULL), and the "Files:" check after the run still flags edits outside the worktree's list

Why the rules: Codex is thorough but defensive -- it re-runs long regressions after every change and widens the
scope (compatibility paths, extra tests). The user wants Claude's speed at no loss of quality, so the coordinator
fixes the tests and the scope, and runs the long regressions itself.

Every call is logged to <LAB>\shared\outsource\log.jsonl, like agy_task.py.
"""
import argparse, datetime, fnmatch, glob, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
LOG = os.path.join(LAB, 'shared', 'outsource', 'log.jsonl')

RULES = """
---
Rules for this task (from the project; they override anything above):
- Scope: change only what the done criteria need, and only the files the brief's "Files:" section allows (new files
  too). No compatibility paths, extra options, refactors, dependency changes or tests beyond the ones the brief asks
  for. If you think something more is needed, say so in the report instead of doing it.
- Quality: the done criteria must hold exactly. A rule comes from the data or the code, not from fitting each number;
  say what explains each expected value. If something cannot be explained, stop and report it, do not force it.
- Tests: while working, run only the single focused test you are changing (pytest -k). At the end, run the commands
  in the brief's "Tests:" section once each. Do not run any other suite or the full regression: the coordinator runs
  those. Long output goes to work/logs/<name>.log; read only its tail.
- Stop: once the "Tests:" commands pass, stop and report. If they fail, at most two rounds of fixing; still failing
  after that, stop and report what fails and why you think so -- the coordinator decides whether to go on. Aim for
  about {aim} minutes; {limit} is only a safety stop.
- {bench}
- Your final message IS the report (the harness saves it); do not write report files such as answer.md into the
  worktree.
- Progress notes: if the brief names a handoff file, append to it as you go (after each bench run or finding, one
  or two lines with the readings), not only at the end -- a run can be cut off (quota, crash) with no final report.
- Follow AGENTS.md / CLAUDE.md for everything else.
- End with a short report in Chinese: files changed, how each done criterion is met (and what explains each value),
  the tests you ran with their result lines, and anything left open.
"""


def changed(folder):
    r = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all', '.'], cwd=folder,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout.splitlines() if r.returncode == 0 else None


NO_BENCH = 'Do not commit, push, install anything, start Red Alert 3 or the test bench, or touch the shared locks folder.'
BENCH = ('Do not commit, push or install anything. The test bench: only through '
         '`python -I -X utf8 experimental/testbench/run_queue.py <mission:check> ... --jobs 2` (it takes the bench '
         'locks, queues behind other lines and refuses at once when the user is playing -- then stop and report, do '
         'not retry in a loop); never start Red Alert 3 any other way, never touch the Steam game folder or the lock '
         'files yourself. Results land in work/bench_results/<mission>__<check>.json. You also have the ra3bench MCP '
         'tools (run from your worktree): cnv_show (what a mission publishes, its contract -- check before benching), '
         'cnv_map / cnv_preview (a built map from above, no game), cnv_check (build + run one check, PASS/FAIL), and '
         'by hand bench_start / bench_wait / bench_look / bench_inspect / bench_counters / bench_stop (always '
         'bench_stop when done: it frees the bench lock). When a reading does not explain itself, LOOK (bench_look / '
         'bench_inspect on the frames) before you change code or guess, and design a run that tells your hypotheses '
         'apart; keep a hypothesis table (hypothesis, run, result) in the handoff and read it before each round.')
FULL = (' You run WITHOUT a sandbox (the user allowed it 2026-11-09 so you can bench yourself), so these limits are '
        'yours to keep: write only inside your worktree and the main checkout\'s work/ folder (plus what the bench '
        'itself writes); never touch the main checkout\'s other files, other worktrees, the Steam game folder, the '
        'registry, system or Codex settings; never stop or kill a process you did not start (other lines and the '
        'user\'s game run here); no network beyond what the tools already do. When readings do not explain '
        'themselves, look: the bench archives frames under work/testbench/runs/ -- view them before guessing.')


def files_allowed(brief):
    """The globs under the brief's "Files:" line (one per line, or comma separated; "none" = no changes), or None
    when the brief has no such section."""
    lines = brief.splitlines()
    at = next((i for i, l in enumerate(lines) if l.strip().lower().startswith('files:')), None)
    if at is None:
        return None
    globs, first = [], lines[at].split(':', 1)[1]
    for l in [first] + lines[at + 1:]:
        l = l.strip().lstrip('-* ').strip()
        if not l and globs:
            break
        if l.endswith(':') or l.lower().startswith('tests:'):
            break
        globs += [g.strip().strip('`') for g in l.split(',') if g.strip()]
    return [] if [g.lower() for g in globs] == ['none'] else globs


def bench_dirs():
    """What the bench writes: the game copy and results (work), the mods, the locks, the SDK."""
    return [(os.environ.get('CNV_WORK') or os.path.join(LAB, 'RA3-CampaignLab', 'work')), os.path.join(LAB, 'shared'),
            os.path.join(LAB, 'sdk'), os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3'),
            os.path.join(os.environ.get('APPDATA', ''), 'Red Alert 3')]


def bench_mcp(worktree):
    """-c override: the ra3bench MCP server (declared in ~/.codex/config.toml) run from the worktree's own
    bench_mcp.py, so cnv_check / cnv_show build the worktree's missions and checks, not main's."""
    script = os.path.join(os.path.abspath(worktree), 'experimental', 'testbench', 'bench_mcp.py').replace('\\', '/')
    return ['-c', 'mcp_servers.ra3bench.args=' + json.dumps(['-I', '-X', 'utf8', script])]


def codex():
    found = sorted(glob.glob(os.path.join(os.environ.get('LOCALAPPDATA', ''), 'OpenAI', 'Codex', 'bin', '*', 'codex.exe')),
                   key=os.path.getmtime)
    return found[-1] if found else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('brief')
    ap.add_argument('--dir', required=True)
    ap.add_argument('--minutes', type=float, default=60)
    ap.add_argument('--effort', default='medium', choices=['low', 'medium', 'high'])
    ap.add_argument('--model', default='gpt-6.1-sol')
    ap.add_argument('--read-dir', action='append', default=[])
    ap.add_argument('--bench', action='store_true', help='may run the bench through run_queue.py (a line task)')
    ap.add_argument('--full', action='store_true',
                    help='no sandbox (user-approved 2026-11-09): the SDK compiler crashes inside one, so a line task '
                         'that benches itself needs this; implies --bench')
    a = ap.parse_args()
    a.bench = a.bench or a.full
    exe = codex()
    if not exe:
        sys.exit('Codex desktop not installed (no codex.exe under %LOCALAPPDATA%\\OpenAI\\Codex\\bin)')
    brief = open(a.brief, encoding='utf-8').read()
    allowed = files_allowed(brief)
    if 'Tests:' not in brief or allowed is None:
        sys.exit('the brief needs a "Files:" section (the paths / globs it may change, or "none") and a "Tests:" '
                 'section naming the exact test commands')
    prompt = brief + RULES.format(aim=int(a.minutes / 3), limit=int(a.minutes), bench=(BENCH + (FULL if a.full else '')) if a.bench else NO_BENCH)
    if a.bench:
        a.read_dir += bench_dirs()
    base = os.path.splitext(a.brief)[0]
    out, events = base + '.answer.md', base + '.events.jsonl'
    # windows.sandbox="mxc": from 2026-11-09 21:28 the "unelevated" sandbox refused every process (CreateProcessAsUserW
    # 5, even `python --version`, across worktrees and a Codex restart); mxc runs them -- still a sandbox
    box = ['-s', 'danger-full-access'] if a.full else ['-c', 'windows.sandbox="mxc"', '-s', 'workspace-write']
    cmd = [exe, 'exec', '-m', a.model, '-c', f'model_reasoning_effort="{a.effort}"', *box,
           *(bench_mcp(a.dir) if a.bench else []),
           '-C', a.dir, *sum((['--add-dir', d] for d in a.read_dir), []), '--json', '-o', out, prompt]
    before = changed(a.dir)
    t0, ended, usage = time.time(), 'ok', None
    with open(events, 'w', encoding='utf-8') as ev:
        try:
            r = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=ev, stderr=subprocess.PIPE, text=True,
                               encoding='utf-8', errors='replace', timeout=a.minutes * 60)
            if r.returncode:
                ended = f'exit {r.returncode}: ' + (r.stderr.strip().splitlines() or [''])[-1][:300]
        except subprocess.TimeoutExpired:
            ended = 'timeout'
    with open(events, encoding='utf-8', errors='replace') as ev:
        for line in ev:
            if '"turn.completed"' in line:
                try:
                    usage = json.loads(line).get('usage')
                except ValueError:
                    pass
    after = changed(a.dir)
    touched = sorted(set(after) - set(before)) if before is not None and after is not None else []
    outside = [t for t in touched if not any(fnmatch.fnmatch(t[3:].strip().strip('"'), g) for g in allowed)]
    if outside and ended == 'ok':
        ended = 'changed files outside "Files:"'
    if not os.path.exists(out):        # cut off (quota, crash): salvage the progress notes it wrote on the way
        notes = []
        with open(events, encoding='utf-8', errors='replace') as ev:
            for line in ev:
                try:
                    it = json.loads(line).get('item') or {}
                except ValueError:
                    continue
                if it.get('type') == 'agent_message':
                    notes.append(it.get('text', '').strip())
        with open(out, 'w', encoding='utf-8') as fh:
            fh.write(f'(no final answer: {ended})\n\nProgress notes, in order:\n\n' + '\n\n'.join(notes) + '\n')
    with open(out, 'a', encoding='utf-8') as fh:
        fh.write('\n\n---\nFiles changed in ' + a.dir + ' (git status):\n' + '\n'.join(touched) + '\n'
                 + (('OUTSIDE "Files:":\n' + '\n'.join(outside) + '\n') if outside else '') + f'Usage: {usage}\n')
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps({'at': datetime.datetime.now().isoformat(timespec='seconds'), 'tool': 'codex',
                             'dir': a.dir, 'brief': a.brief, 'task': brief.strip().splitlines()[0][:120],
                             'model': a.model, 'effort': a.effort, 'seconds': round(time.time() - t0),
                             'usage': usage, 'changed': len(touched), 'outside': outside, 'ended': ended,
                             'out': out},
                            ensure_ascii=False) + '\n')
    print(f'{ended}; {round(time.time() - t0)} s; answer -> {out}')
    sys.exit(0 if ended == 'ok' else 1)


if __name__ == '__main__':
    main()
