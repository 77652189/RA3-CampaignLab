"""Daily report, built from what is already there -- nobody writes it by hand (AGENTS.md).

Prints: the commits of the last N hours in this repo and in work/re (the private one), the inventory's
per-part benched share, the structure numbers (simulator size, kernel modules, peak-load speed, the full test run),
and every handoff's `## 待答问题` section.
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
    """The summary rows of the inventory, rendered here in memory (~1 min): the page is not committed (ADR 0030), and
    a docs/engine/inventory.md on disk is whatever this checkout last generated."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('inventory', ROOT / 'experimental' / 'cnv' / 'inventory.py')
    inv = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(inv)
        out = inv.render(inv.collect())
    except SystemExit as e:                     # a source missing here (the retail cache, the SDK, the model)
        return [f'  (清单生成不了：{e})']
    return ['  ' + line for line in out.splitlines()
            if line.startswith('| 部分 |') or re.match(r'\| \S+ \| \*\*\d+%\*\*', line)]


def questions():
    rows = []
    files = sorted(WORK.glob('re/handoff*.md')) + sorted(ROOT.glob('docs/*/handoff*.md'))
    for f in files:
        text = f.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'^## 待答问题\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
        if not m and re.fullmatch(r'handoff(-[a-z]+)?\.md', f.name) and f.name != 'handoff-archive.md':
            rows.append('  [%s] 没有 "## 待答问题" 标题，它的问题汇总不到这里（AGENTS.md：写在交接开头）' % f.name)
        if m and m.group(1).strip():
            rows.append('  [%s]' % f.name)
            rows += ['    ' + line for line in m.group(1).strip().splitlines()]
    return rows or ['  (无)']


FAT = 1500          # lines: a simulator file this long is a part that wants splitting
FULL_SLOW = 3 * 3600  # seconds: the full test run past this means the structure costs every line time
SIM = ROOT / 'experimental' / 'cnv'


def _lines(p):
    return sum(1 for _ in p.open(encoding='utf-8', errors='replace'))


def structure(logs=None):
    """Structure numbers, read every day so a drift shows before it costs (11-17 retrospective: the architecture
    problems were known but only noticed once the test run had grown hours long). Each row is a number and, when
    it crosses its line, a `!!` flag. Reads files only; a missing source is said, not guessed."""
    logs = Path(logs) if logs else WORK / 'logs'
    rows, flags = [], []
    sims = sorted(SIM.glob('sim*.py'))
    big = sorted(((_lines(p), p.name) for p in sims), reverse=True)
    rows.append('  模拟器 sim*.py：%d 个文件 %d 行；sim.py %d 行（只许减）' % (
        len(sims), sum(n for n, _ in big), next((n for n, name in big if name == 'sim.py'), 0)))
    fat = [f'{name} {n}' for n, name in big if n > FAT]
    if fat:
        flags.append('超过 %d 行的模拟器文件：%s' % (FAT, '、'.join(fat)))
    mods = [p for p in (SIM / 'engine' / 'modules').glob('*.py') if p.name != '__init__.py']
    rows.append('  内核模块（engine/modules）：%d 个' % len(mods))
    peaks = sorted(logs.glob('perf/peak_*.json'), key=lambda p: p.stat().st_mtime)
    if peaks:
        import json
        d = json.loads(peaks[-1].read_text(encoding='utf-8'))
        rows.append('  高峰负载（%s）：全程 %.2f 倍实时，最慢 10 秒 %.2f 倍' % (d.get('rev', '?'), d['multiple'], d['worst']))
        if d['worst'] < 1:
            flags.append('高峰最慢段慢于实时（ADR 0034 第 10 条要求比实时快）')
    else:
        rows.append('  高峰负载：没有 perf/peak_*.json（experimental/cnv/simbench_peak.py 单独跑）')
    fulls = sorted(logs.glob('full_*.log'), key=lambda p: p.stat().st_mtime)
    tail = next((ln for ln in reversed(fulls[-1].read_text(encoding='utf-8', errors='replace').splitlines())
                 if re.search(r'\d+ passed', ln)), '') if fulls else ''
    m = re.search(r'in ([\d.]+)s', tail)
    if m:
        rows.append('  最近全量（%s）：%s' % (fulls[-1].name, tail.strip('= ')))
        if float(m.group(1)) > FULL_SLOW:
            flags.append('全量测试超过 %d 小时' % (FULL_SLOW // 3600))
    else:
        rows.append('  最近全量：没有跑完的 full_*.log')
    rows += ['  !! ' + f for f in flags] or ['  （没有越线的）']
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hours', type=int, default=24)
    a = ap.parse_args()
    print('# 每日汇报（最近 %d 小时）\n' % a.hours)
    print('## 提交：本仓库'); print('\n'.join(commits(ROOT, a.hours)))
    print('\n## 提交：work/re（私有）'); print('\n'.join(commits(WORK / 're', a.hours)))
    print('\n## 清单（按用量已对拍；9 关用到的那栏是当前主攻）'); print('\n'.join(inventory()))
    print('\n## 结构（越线标 !!，规模一变先看这里）'); print('\n'.join(structure()))
    print('\n## 待答问题'); print('\n'.join(questions()))


if __name__ == '__main__':
    main()
