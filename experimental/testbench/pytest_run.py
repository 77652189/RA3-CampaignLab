"""Run pytest with logging and read its summary and failed test IDs."""
import re
import subprocess
import sys


def pytest_counts(text):
    """{'passed': 840, 'failed': 5, ...} from pytest's last summary line, and the failed node ids (-rf)."""
    counts = {}
    for line in reversed(text.splitlines()):
        found = re.findall(r'(\d+) (passed|failed|errors?|skipped|xfailed|xpassed|deselected)', line)
        if found:
            counts = {k.rstrip('s') if k.startswith('error') else k: int(v) for v, k in found}
            break
    red = sorted(set(re.findall(r'^(?:FAILED|ERROR) (\S+)', text, re.M)))
    return counts, red


def no_result_why(returncode, stderr):
    """How a pytest run that printed no summary ended: its exit code and its last word on stderr."""
    last = next((ln.strip() for ln in reversed(stderr.splitlines()) if ln.strip()), '')
    return f'exit {returncode}' + (f'；{last[:200]}' if last else '')


def run_pytest(args, cwd, log_path, run=subprocess.run, tries=2):
    """pytest with `args` (a list starting at its options) in `cwd`; its counts, red ids and, when it gave no
    summary, how it ended. A run that gives no summary is retried up to tries; the log keeps every exit code."""
    cmd = [sys.executable, '-X', 'utf8', '-m', 'pytest', *args]
    why = ''
    for attempt in range(1, tries + 1):
        r = run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        counts, red = pytest_counts(r.stdout)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f'$ {" ".join(cmd)}\n(in {cwd}; try {attempt}, exit {r.returncode})\n{r.stdout}\n'
                    f'{r.stderr[-5000:]}\n')
        if counts or red:
            return counts, red, ''
        why = no_result_why(r.returncode, r.stderr)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f'pytest gave no summary ({why})' + ('; running it again\n' if attempt < tries else '\n'))
    return {}, [], f'跑了 {tries} 次都没结果，最后一次 {why}'
