"""Daily report, built from what is already there -- nobody writes it by hand (AGENTS.md).

Prints: the commits of the last N hours in this repo and in work/re (the private one), the inventory's
per-part benched share, and every handoff's `## 待答问题` section.
    python -X utf8 experimental/campaign/daily_report.py [--hours 24]
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import labpaths

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(labpaths.WORK)


def commits(repo, hours):
    if not (repo / '.git').exists():
        return ['  (不是 git 仓库: %s)' % repo]
    out = subprocess.run(['git', '-C', str(repo), 'log', '--since=%d hours ago' % hours, '--format=%h %s'],
                         capture_output=True, text=True, encoding='utf-8').stdout
    lines = out.splitlines()
    more = ['  ... 另有 %d 条' % (len(lines) - 30)] if len(lines) > 30 else []
    return ['  ' + line[:140] for line in lines[:30]] + more or ['  (无)']


def inventory():
    out = subprocess.run([sys.executable, '-I', '-X', 'utf8', str(ROOT / 'experimental/cnv/inventory.py')],
                         capture_output=True, text=True, encoding='utf-8', env=dict(os.environ)).stdout
    return ['  ' + line for line in out.splitlines() if re.match(r'\| \S+ \| \*\*\d+%\*\*', line)]


def questions():
    rows = []
    files = sorted(WORK.glob('re/handoff*.md')) + sorted(ROOT.glob('docs/*/handoff*.md'))
    for f in files:
        text = f.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'^## 待答问题\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
        if m and m.group(1).strip():
            rows.append('  [%s]' % f.name)
            rows += ['    ' + line for line in m.group(1).strip().splitlines()]
    return rows or ['  (无)']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hours', type=int, default=24)
    a = ap.parse_args()
    print('# 每日汇报（最近 %d 小时）\n' % a.hours)
    print('## 提交：本仓库'); print('\n'.join(commits(ROOT, a.hours)))
    print('\n## 提交：work/re（私有）'); print('\n'.join(commits(WORK / 're', a.hours)))
    print('\n## 清单（按用量已对拍）'); print('\n'.join(inventory()))
    print('\n## 待答问题'); print('\n'.join(questions()))


if __name__ == '__main__':
    main()
