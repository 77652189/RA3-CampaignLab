"""PreToolUse hook (Bash): refuse file edits written as fragile inline shell text.

Blocked, because the shell mangles them before the program sees them (seen many times in this project: backslashes
eaten by heredocs / sed, backticks run as command substitution inside double-quoted python -c, a garbled row left
in docs/plan.md):
  1. a heredoc or a `python -c` one-liner that writes a file (open(..., 'w'/'a'), write_text, write_bytes)
     and contains a backslash
  2. `sed -i` whose command contains a backslash
  3. `python -c "..."` (double-quoted) that contains a backtick
Read-only commands, and edits without those characters, pass. Exit 2 + stderr = block, shown to Claude.
"""
import json
import re
import sys

WRITES = re.compile(r"""open\([^)]*['"][wa]b?['"]|\.write_text\(|\.write_bytes\(""")
PY_C = re.compile(r'\bpython[0-9.]*(\.exe)?\b[^|;&]*?\s-[A-Za-z]*c\s')
HEREDOC = re.compile(r'<<-?\s*[\'"]?\w+')


def reasons(cmd):
    out = []
    inline_py = bool(PY_C.search(cmd)) or bool(HEREDOC.search(cmd))
    if inline_py and WRITES.search(cmd) and '\\' in cmd:
        out.append('a heredoc / python -c that writes a file contains backslashes (the shell may eat or change them)')
    for m in re.finditer(r'\bsed\s+(-[A-Za-z]*\s+)*-i\b[^|;&]*', cmd):
        if '\\' in m.group(0):
            out.append('sed -i with a backslash in its expression')
            break
    for m in re.finditer(r'-[A-Za-z]*c\s+"((?:[^"\\]|\\.)*)"', cmd):
        if '`' in m.group(1) and PY_C.search(cmd):
            out.append('python -c "..." contains backticks (bash runs them as command substitution)')
            break
    return out


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get('tool_name') != 'Bash':
        return 0
    cmd = (data.get('tool_input') or {}).get('command') or ''
    why = reasons(cmd)
    if not why:
        return 0
    sys.stderr.write('Blocked by .claude/hooks/guard_inline_edits.py: ' + '; '.join(why) +
                     '. Edit files with the Edit / Write tools, or write the script to a .py file in the scratchpad '
                     'and run that file.\n')
    return 2


if __name__ == '__main__':
    sys.exit(main())
