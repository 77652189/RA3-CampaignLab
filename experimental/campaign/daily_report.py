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


def _time_budget():
    import importlib.util
    spec = importlib.util.spec_from_file_location('time_budget', ROOT / 'experimental' / 'testbench' / 'time_budget.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def structure(logs=None, testmap=None):
    """Structure numbers, read every day so a drift shows before it costs (11-17 retrospective: the architecture
    problems were known but only noticed once the test run had grown hours long). Each row is a number and, when
    it crosses its line, a `!!` flag. Reads files only; a missing source is said, not guessed. The test layers'
    time ceilings are experimental/testbench/time_budget.py's (ADR 0035 6), read from the time record in testmap."""
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
    budget_rows, budget_flags = _time_budget().rows(str(testmap) if testmap else None)
    rows += budget_rows
    flags += budget_flags
    rows += ['  !! ' + f for f in flags] or ['  （没有越线的）']
    return rows


STEP = re.compile(r'^(M\d+ |K\d|R3 |Z |X |Test layers T3)')   # a refactor step's commit subject (ADR 0029 / 0035)
NEW_REDS_PER_STEP = 0.5   # full run's new reds per step past this: small steps' light checks cost too much (user 11-18)
WAIT_SLOW = 600           # seconds: the mean wait for CPU tokens past this, the machine is the bottleneck
BACKLOG = 15              # entries on R's after-the-move behaviour list past this: a round of only those


def _step_commits(repo, hours):
    out = subprocess.run(['git', '-C', str(repo), 'log', '--since=%d hours ago' % hours, '--format=%ct %s'],
                         capture_output=True, text=True, encoding='utf-8').stdout
    return [(int(t), s) for t, s in (ln.split(' ', 1) for ln in out.splitlines() if ' ' in ln) if STEP.match(s)]


def _reds(log):
    return {ln.split(' - ')[0][7:].strip() for ln in log.read_text(encoding='utf-8', errors='replace').splitlines()
            if ln.startswith('FAILED ')}


def flow(logs=None, re_dir=None, steps=None, hours=24):
    """Flow numbers (11-18, the user: "如果不带来额外负担的话可以加进去"), read from what tools already leave: refactor
    steps from git subjects, the full runs' red lists, the CPU token pool's wait log, R's after-the-move list. Each
    has its action when it crosses (handoff-coord); a missing source is said, not guessed."""
    logs = Path(logs) if logs else WORK / 'logs'
    re_dir = Path(re_dir) if re_dir else WORK / 're'
    rows, flags = [], []
    steps = sorted(_step_commits(ROOT, hours) if steps is None else steps)
    gaps = sorted((b - a) / 60 for (a, _), (b, _) in zip(steps, steps[1:]))
    rows.append('  重构步（最近 %d 小时，各线合计）：%d 步%s' % (hours, len(steps),
                '，相邻两步中位间隔 %d 分钟' % gaps[len(gaps) // 2] if gaps else ''))
    fulls = sorted(logs.glob('full_*.log'), key=lambda p: p.stat().st_mtime)
    if len(fulls) >= 2:
        prev, last = fulls[-2], fulls[-1]
        new = _reds(last) - _reds(prev)
        between = [t for t, _ in steps if prev.stat().st_mtime <= t <= last.stat().st_mtime]
        rows.append('  全量新红：%s 对 %s 新 %d 条，其间 %d 步' % (last.name, prev.name, len(new), len(between)))
        if between and len(new) / len(between) > NEW_REDS_PER_STEP:
            flags.append('全量新红平均每步超过 %.1f 条：小族验证放轻的代价偏大，报用户定要不要改回' % NEW_REDS_PER_STEP)
    else:
        rows.append('  全量新红：不到两次全量，没法比')
    waits = logs / 'cpupool_waits.jsonl'
    if waits.is_file():
        import json
        import time
        cut = time.time() - hours * 3600
        ws = [w['waited'] for w in map(json.loads, waits.read_text(encoding='utf-8').splitlines()) if w['t'] >= cut]
        if ws:
            mean = sum(ws) / len(ws)
            rows.append('  等 CPU 令牌：%d 次，平均 %d 秒，最长 %d 秒' % (len(ws), mean, max(ws)))
            if mean > WAIT_SLOW:
                flags.append('等令牌平均超过 %d 分钟：查谁占着' % (WAIT_SLOW // 60))
        else:
            rows.append('  等 CPU 令牌：最近 %d 小时没有记录' % hours)
    else:
        rows.append('  等 CPU 令牌：没有 cpupool_waits.jsonl（令牌池还不记）')
    hand = re_dir / 'handoff-r.md'
    if hand.is_file():
        sec = re.search(r'^## 搬完后有意改行为.*?$(.*?)(?=^## |\Z)', hand.read_text(encoding='utf-8'), re.M | re.S)
        n = len(re.findall(r'^- ', sec.group(1), re.M)) if sec else 0
        rows.append('  搬完再改的清单：%d 条' % n)
        if n > BACKLOG:
            flags.append('搬完再改的清单超过 %d 条：插一轮专门清' % BACKLOG)
    else:
        rows.append('  搬完再改的清单：没有 handoff-r.md')
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
    print('\n## 流程（越线标 !!，动作见 handoff-coord）'); print('\n'.join(flow(hours=a.hours)))
    print('\n## 待答问题'); print('\n'.join(questions()))


if __name__ == '__main__':
    main()
