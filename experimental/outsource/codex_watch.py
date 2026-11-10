r"""Watch the Codex task that is running now, live, in a terminal: what it says, what it runs, when it ends.

  python -I -X utf8 experimental/outsource/codex_watch.py [FOLDER]

FOLDER is where the briefs and their <brief>.events.jsonl live (default: the newest events file anywhere under the
user's temp folder). It follows the newest events file, prints one short line per step, and moves on to the next
task's file when one starts. Ctrl-C to stop. Read only: it never touches Codex or the files.
"""
import glob
import json
import os
import sys
import time

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TEMP', '.')


def newest():
    files = glob.glob(os.path.join(ROOT, '**', '*.events.jsonl'), recursive=True)
    return max(files, key=os.path.getmtime) if files else None


def line(e):
    t, it = e.get('type'), e.get('item') or {}
    kind = it.get('type')
    if t == 'turn.completed':
        u = e.get('usage') or {}
        return f'== 完成  输入 {u.get("input_tokens", 0):,}（缓存 {u.get("cached_input_tokens", 0):,}）输出 {u.get("output_tokens", 0):,}'
    if t == 'turn.failed' or kind == 'error':
        return '!! ' + str(it.get('message') or e.get('error') or e)[:160]
    if t != 'item.completed':
        return None
    if kind == 'agent_message':
        return '说: ' + (it.get('text') or '').replace('\n', ' ')[:200]
    if kind == 'command_execution':
        cmd = (it.get('command') or '').split('\n')[-1]
        return f'跑: {cmd[-150:]}  -> {it.get("exit_code")}'
    if kind == 'mcp_tool_call':
        return '查: ' + str((it.get('arguments') or {}).get('title') or it.get('tool'))[:150]
    if kind == 'file_change':
        return '改: ' + ', '.join(c.get('path', '') for c in it.get('changes') or [])[:180]
    return None


def main():
    current, pos = None, 0
    print(f'watching {ROOT} for Codex tasks (Ctrl-C to stop)')
    while True:
        f = newest()
        if f and f != current:
            current, pos = f, 0
            print(f'\n### {time.strftime("%H:%M:%S")}  {os.path.basename(f)[:-len(".events.jsonl")]}')
        if current:
            with open(current, 'rb') as fh:          # bytes: the file has CRLF line ends on Windows
                fh.seek(pos)
                for raw in fh:
                    if not raw.endswith(b'\n'):
                        break
                    pos += len(raw)
                    try:
                        out = line(json.loads(raw.decode('utf-8', 'replace')))
                    except ValueError:
                        continue
                    if out:
                        print(time.strftime('%H:%M:%S'), out, flush=True)
        time.sleep(2)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
