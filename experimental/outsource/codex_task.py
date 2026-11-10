r"""外包给 Codex: hand one bounded development task to OpenAI's Codex CLI (the user's ChatGPT quota) instead of
spending Claude's. The coordinator writes the brief; this runs `codex exec` once in a worktree; the answer and the
token counts land in files the coordinator reads and checks -- Codex's word is a draft, never the proof (the
coordinator runs the long regressions, reads the diff, then commits).

  python -I -X utf8 experimental/outsource/codex_task.py BRIEF.md --dir WORKTREE [--minutes 30] [--effort medium]

  BRIEF.md   the task: goal, files to read, done criteria, and a "Tests:" section naming the exact commands to run
             (one focused test file, or -k tests; never the whole suite) -- the rules below are added
  --dir      the git worktree Codex edits (never the main checkout: other lines work there)
  --minutes  hard limit; at the limit Codex is killed and what it changed stays for the coordinator to judge
  --effort   reasoning effort, default medium (2026-11-09: high on a rule-plus-readings task spent 30+ min, most of it
             re-running long regressions); high only for a task that needs real design judgment
  --model    default gpt-6.1-sol (2026-11-09 comparison: Astra no better at 4.5x the price)
  --read-dir extra folders Codex may write in besides --dir (e.g. the main checkout's work\ for logs)

Why the rules: Codex is thorough but defensive -- it re-runs long regressions after every change and widens the
scope (compatibility paths, extra tests). The user wants Claude's speed at no loss of quality, so the coordinator
fixes the tests and the scope, and runs the long regressions itself.

Every call is logged to <LAB>\shared\outsource\log.jsonl, like agy_task.py.
"""
import argparse, datetime, glob, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
LOG = os.path.join(LAB, 'shared', 'outsource', 'log.jsonl')

RULES = """
---
Rules for this task (from the project; they override anything above):
- Scope: change only what the done criteria need. No compatibility paths, extra options, refactors or tests beyond
  the ones the brief asks for. If you think something more is needed, say so in the report instead of doing it.
- Quality: the done criteria must hold exactly. A rule comes from the data or the code, not from fitting each number;
  say what explains each expected value. If something cannot be explained, stop and report it, do not force it.
- Tests: while working, run only the single focused test you are changing (pytest -k). At the end, run the commands
  in the brief's "Tests:" section once each. Do not run any other suite or the full regression: the coordinator runs
  those. Long output goes to work/logs/<name>.log; read only its tail.
- Time: aim to finish in about {aim} minutes; you are stopped at {limit}.
- Do not commit, push, install anything, start Red Alert 3 or the test bench, or touch the shared locks folder.
- Follow AGENTS.md / CLAUDE.md for everything else.
- End with a short report in Chinese: files changed, how each done criterion is met (and what explains each value),
  the tests you ran with their result lines, and anything left open.
"""


def changed(folder):
    r = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all', '.'], cwd=folder,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout.splitlines() if r.returncode == 0 else None


def codex():
    found = sorted(glob.glob(os.path.join(os.environ.get('LOCALAPPDATA', ''), 'OpenAI', 'Codex', 'bin', '*', 'codex.exe')),
                   key=os.path.getmtime)
    return found[-1] if found else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('brief')
    ap.add_argument('--dir', required=True)
    ap.add_argument('--minutes', type=float, default=30)
    ap.add_argument('--effort', default='medium', choices=['low', 'medium', 'high'])
    ap.add_argument('--model', default='gpt-6.1-sol')
    ap.add_argument('--read-dir', action='append', default=[])
    a = ap.parse_args()
    exe = codex()
    if not exe:
        sys.exit('Codex desktop not installed (no codex.exe under %LOCALAPPDATA%\\OpenAI\\Codex\\bin)')
    brief = open(a.brief, encoding='utf-8').read()
    if 'Tests:' not in brief:
        sys.exit('the brief needs a "Tests:" section naming the exact test commands')
    prompt = brief + RULES.format(aim=int(a.minutes * 0.7), limit=int(a.minutes))
    base = os.path.splitext(a.brief)[0]
    out, events = base + '.answer.md', base + '.events.jsonl'
    cmd = [exe, 'exec', '-m', a.model, '-c', f'model_reasoning_effort="{a.effort}"', '-s', 'workspace-write',
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
    if not os.path.exists(out):
        with open(out, 'w', encoding='utf-8') as fh:
            fh.write(f'(no final answer: {ended})\n')
    with open(out, 'a', encoding='utf-8') as fh:
        fh.write('\n\n---\nFiles changed in ' + a.dir + ' (git status):\n' + '\n'.join(touched) + '\n'
                 + f'Usage: {usage}\n')
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps({'at': datetime.datetime.now().isoformat(timespec='seconds'), 'tool': 'codex',
                             'dir': a.dir, 'brief': a.brief, 'task': brief.strip().splitlines()[0][:120],
                             'model': a.model, 'effort': a.effort, 'seconds': round(time.time() - t0),
                             'usage': usage, 'changed': len(touched), 'ended': ended, 'out': out},
                            ensure_ascii=False) + '\n')
    print(f'{ended}; {round(time.time() - t0)} s; answer -> {out}')
    sys.exit(0 if ended == 'ok' else 1)


if __name__ == '__main__':
    main()
