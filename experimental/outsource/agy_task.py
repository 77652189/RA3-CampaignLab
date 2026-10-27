r"""外包: hand one bounded task to Google's Antigravity CLI (agy, the user's Google AI Pro quota) instead of spending
Claude's. The calling session writes a brief, this runs agy once without a terminal, and the answer lands in a file
the session reads and checks -- agy's word is a draft, never the proof (run the tests, read the diff).

  python -I -X utf8 experimental/outsource/agy_task.py BRIEF.md --dir WORKTREE [--edit] [--minutes 15] [--out FILE]

  BRIEF.md   the task: goal, files to read, what to produce, what done looks like (the rules below are added)
  --dir      the only folder agy works in (a worktree or a scratch folder; never the main checkout when --edit)
  --edit     let agy change files there (accept-edits); without it agy only reads and answers (plan mode)
  --minutes  hard limit; agy's print mode can hang without a terminal (antigravity-cli issue 318), so it is killed
  --out      where the answer goes (default: next to the brief, <brief>.answer.md)
  --model    default Gemini 3.8 Flash (a blind review of the map branch found the real problem in full); the Claude
             models in agy have a tiny quota (one review ran it out for ~5 h); `agy models` lists them

Every call is logged to <LAB>\shared\outsource\log.jsonl (who, where, how long, how it ended) so the coordinator
sees what went out and what came back.
"""
import argparse, datetime, json, os, subprocess, sys, time

AGY = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'agy', 'bin', 'agy.exe')
HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
LOG = os.path.join(LAB, 'shared', 'outsource', 'log.jsonl')

RULES = """
---
Rules for this task (from the project; they override anything above):
- Work only inside this folder. Do not touch Documents\\Red Alert 3, the Steam game folder, or other repositories.
- Do not start Red Alert 3 or the test bench, and do not use the shared locks folder.
- Do not commit, push, delete files, or install anything.
- {edit}
- End with a short report: what you did, every file you changed or created, what you could not do or are unsure of.
"""


def changed(folder):
    """git status lines of a folder (None outside a repository): what a task changed is after minus before."""
    r = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all', '.'], cwd=folder,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout.splitlines() if r.returncode == 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('brief')
    ap.add_argument('--dir', required=True)
    ap.add_argument('--edit', action='store_true')
    ap.add_argument('--minutes', type=float, default=15)
    ap.add_argument('--out')
    ap.add_argument('--model')
    a = ap.parse_args()
    if not os.path.exists(AGY):
        sys.exit(f'agy not installed at {AGY} (irm https://antigravity.google/cli/install.ps1 | iex)')
    brief = open(a.brief, encoding='utf-8').read()
    prompt = brief + RULES.format(edit='You may edit files in this folder.' if a.edit else
                                  'Read only: change no files; put everything in your answer.')
    out = a.out or os.path.splitext(a.brief)[0] + '.answer.md'
    # no one is there to answer a permission prompt: a denied command ends the turn with an empty answer (bench
    # 2026-10-26), so tools are approved; reading runs in plan mode and agy's sandbox, and git tells what changed
    cmd = [AGY, '-p', prompt, '--output-format', 'json', '--mode', 'accept-edits' if a.edit else 'plan',
           *([] if a.edit else ['--sandbox']), '--dangerously-skip-permissions',
           '--print-timeout', f'{int(a.minutes * 60)}s', *(['--model', a.model] if a.model else [])]
    before = changed(a.dir)
    t0, ended, tokens = time.time(), 'ok', None
    try:
        r = subprocess.run(cmd, cwd=a.dir, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=a.minutes * 60 + 30)
        raw, code = r.stdout, r.returncode
        if code:
            ended = f'exit {code}: ' + (r.stderr.strip().splitlines() or [''])[-1][:300]
    except subprocess.TimeoutExpired as e:
        raw, code, ended = (e.stdout or b'').decode('utf-8', 'replace') if isinstance(e.stdout, bytes) else (e.stdout or ''), -1, 'timeout'
    try:
        data = json.loads(raw)
        answer, tokens = data.get('response') or '', (data.get('usage') or {}).get('total_tokens')
        if data.get('status') != 'SUCCESS' and ended == 'ok':
            ended = 'agy: ' + str(data.get('error') or data.get('status'))[:300]
        if not answer.strip() and ended == 'ok':
            ended = f'empty answer (denied: {data.get("denied_actions")})'
    except (ValueError, AttributeError):
        answer = raw
    after = changed(a.dir)
    touched = sorted(set(after) - set(before)) if before is not None and after is not None else []
    if touched:
        answer += '\n\n---\nFiles changed in ' + a.dir + ' (git status):\n' + '\n'.join(touched) + '\n'
        if not a.edit and ended == 'ok':
            ended = 'read-only task changed files'
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(answer)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps({'at': datetime.datetime.now().isoformat(timespec='seconds'), 'dir': a.dir,
                             'brief': a.brief, 'task': brief.strip().splitlines()[0][:120] if brief.strip() else '',
                             'edit': a.edit, 'model': a.model or 'default', 'seconds': round(time.time() - t0),
                             'tokens': tokens, 'changed': len(touched), 'ended': ended, 'out': out},
                            ensure_ascii=False) + '\n')
    print(f'{ended}; {round(time.time() - t0)} s; answer -> {out}')
    sys.exit(0 if ended == 'ok' else 1)


if __name__ == '__main__':
    main()
