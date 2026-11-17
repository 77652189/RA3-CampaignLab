"""PostToolUse hook: tell a session when its context passes the hand-over line (CLAUDE.md: 15 万).

A session cannot see its own context size without calling get_usage, and lines kept running to 23-35 万 before
handing over (2026-11-08). This reads the latest assistant turn's usage from the transcript and, once the context
passes 150k, adds one line to the conversation; again every further 25k. Silent otherwise (costs no context).
State per transcript in the temp dir, so a cleared session starts over.
"""
import hashlib
import json
import os
import sys
import tempfile

FIRST = 150_000
STEP = 25_000
TAIL = 400_000          # bytes read from the end of the transcript


def context_tokens(path):
    with open(path, 'rb') as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - TAIL))
        lines = f.read().decode('utf-8', 'replace').splitlines()
    for line in reversed(lines):
        if '"usage"' not in line:
            continue
        try:
            u = json.loads(line)['message']['usage']
        except (ValueError, KeyError, TypeError):
            continue
        return sum(u.get(k, 0) or 0 for k in ('input_tokens', 'cache_creation_input_tokens',
                                              'cache_read_input_tokens'))
    return 0


def main():
    try:
        data = json.load(sys.stdin)
        path = data.get('transcript_path') or ''
        if not os.path.isfile(path):
            return
        n = context_tokens(path)
        if n < FIRST:
            return
        level = FIRST + (n - FIRST) // STEP * STEP
        key = os.path.join(tempfile.gettempdir(),
                           'ctx_nudge_' + hashlib.sha1(os.path.abspath(path).lower().encode()).hexdigest()[:16]
                           + '.txt')
        try:
            with open(key, encoding='ascii') as f:
                done = int(f.read().strip() or 0)
        except (OSError, ValueError):
            done = 0
        if level <= done:
            return
        with open(key, 'w', encoding='ascii') as f:
            f.write(str(level))
        msg = (f'上下文约 {n // 10000} 万，已过 15 万交接线（CLAUDE.md）。线会话：做完手头这件能提交的事就交接'
               f'（停掉后台任务，汇报末行写"可以清空：……"），改代码最多到 25 万。')
        sys.stdout.reconfigure(encoding='utf-8')        # piped stdout on Windows is the ANSI code page otherwise
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': msg}},
                         ensure_ascii=False))
    except Exception:       # a reminder must never break a tool call
        return


if __name__ == '__main__':
    main()
