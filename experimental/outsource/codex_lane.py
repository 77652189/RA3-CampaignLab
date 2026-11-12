r"""One item of an engine line, done by Codex in a fresh session (`codex exec`), then a report on how it went.

  python -I -X utf8 experimental/outsource/codex_lane.py c|e [--minutes 120] [--effort medium]

The line's worktree is <LAB>\RA3-CampaignLab-codex<lane>; it reads AGENTS.md and work/re/handoff-<lane>.md, does
ONE item, pushes main, updates the handoff and stops. A fresh session per item keeps its context small (no lossy
compaction); the handoff carries the state. Unlike codex_task.py, Codex commits and pushes itself.

After the run it prints one summary (and appends it to <LAB>\shared\outsource\lanes.jsonl): minutes, tokens, the
pushes, and warnings the coordinator reports to the user -- a full-suite pytest run (it once stalled a line for an
hour), the same command run 3+ times (retrying instead of thinking), many bench runs, no push, no handoff change.
The raw events are in work\logs\codex_<lane>_<stamp>.jsonl.
"""
import argparse, collections, datetime, importlib.util, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, path):
    """Import a sibling module by its file (no sys.path edit: tests/test_architecture.py G4 only lets that count fall)."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_task = _load('codex_task', os.path.join(HERE, 'codex_task.py'))
codex, bench_mcp = _task.codex, _task.bench_mcp
_paths = _load('labpaths', os.path.join(os.path.dirname(HERE), 'campaign', 'labpaths.py'))
LAB, WORK = _paths.LAB, _paths.WORK

LOGS = os.path.join(WORK, 'logs')
SUMMARY = os.path.join(LAB, 'shared', 'outsource', 'lanes.jsonl')

PROMPT = """你是引擎 {L} 线。工作区 {wt}（这是你的独立工作区，推送用 `git push origin HEAD:main`）。
开工只读 AGENTS.md 和 work/re/handoff-{lane}.md（存档 handoff-{lane}-archive.md、别的线的交接都不读；要查历史用
Select-String 按关键词搜，只看命中的几行），做交接"工单"里的**一项**，做完就停，不接下一项。
工单写了入口和证据位置：先照它去读，别全仓库摸索；工单里缺的才去搜。
交接没写明下一项、或写着"由总控安排"时，不要停下等：自己按用量从清单（docs/engine/inventory.md 你这一块）
挑用量最大、没被暂停、不归别的线的一项，在报告里说为什么挑它。只有真被卡住（需要别的线的东西、要用户拍板）才停。

这一项的规矩（总控定的，压过别处）：
- 测试：干活时只跑你在改的那一条（`pytest tests/<文件> -k <名字>`）。收尾用 lane_close.py（见下面"收尾"），它按
  改动挑收尾测试，别自己再跑一遍清单测试和守卫（新 check 不许直接 import 关卡内容层，见 G5）。**不跑全量**（`pytest` 不带文件、`pytest tests/`）：太慢，会拖垮进度；全量由总控跑。
  长输出写 work/logs/，只看末几行。**推到 main 的测试必须是绿的**：台上和模拟器对不上、这轮修不了的，
  写成 `pytest.mark.xfail(strict=True, reason=...)`（原因写清、指向交接），不许把失败的测试推上去。
- 不重试同一件事：同一个命令或同一次上台失败两次，先想清楚为什么（看画面、读数据、列假设表）再动；
  连续两次运行解释不了，就把问题、假设表、你倾向的答案写进交接开头的 `## 待答问题`，提交推送后停下。
- 红线：程序地址（0x8xxxxx 之类）和反编译说明只写 work/re，公开仓库的文件、测试、提交说明里都不许出现；
  公开处写"见 work/re/<笔记>"，用自己的话描述行为。
- 缺上下文：交接、docs/engine/know-how.md、相关 check 的 docstring 里找；还找不到就写进待答问题，别猜。
- review：不读 skill 文件，按四条自查：① 断言的是台上读数，没为迎合读数改阈值或模型；② 猜的规则都标了
  INFERRED 或登记成 gap；③ 只改了本线的文件，新 check 不 import 关卡内容层；④ 公开文件和提交说明里没有程序地址。
- 收尾：提交后跑 `python -I -X utf8 experimental/outsource/lane_close.py {lane} <改到的测试文件...>`（它跑收尾测试、
  rebase、推 main，只打末几行；红了就修了再跑，生成的清单冲突照 AGENTS.md 重跑生成器）→ 改写交接 → 推私有仓库
  work/re → 停。
- 交接限 60 行，只放：**工单**（下一项：做什么、为什么、入口文件和行、已有证据在哪、怎么判、上不上台、验收、
  什么算卡住）、没答的问题（每条 ≤ 3 行，细节放报告文件）、当前状态（几行）、固定指针。做完的轮次、答过的
  问题和长证据搬进 handoff-{lane}-archive.md。下一个新会话只读 AGENTS.md 和交接就能接上。
- 最后一条消息用中文：做了什么、台上读数、提交号、跑了哪些测试和结果、用时、下一步。
"""

NOT_A_RUN = ('Get-CimInstance', 'CommandLine', 'Select-String', 'grep ', 'rg ')  # only names pytest
NARROW = re.compile(r"""tests[/\\][\w*]+\.py|::|\s-k\s|[\s"'][@$]\w""")  # @name / $name: a PowerShell list of test files


def full_suite(cmd):
    """A pytest run with no test file, node or -k: the arguments up to the next pipe / ; / & name none."""
    if any(n in cmd for n in NOT_A_RUN):
        return False
    # an invocation (`-m pytest` or a command starting with pytest), not pytest.mark / pytest.skip inside test code
    for m in re.finditer(r'(?:-m\s+pytest|(?:^|[;&|]\s*)pytest)(?![\w.])', cmd, re.M):
        args = re.split(r'[|;&>]', cmd[m.end():], maxsplit=1)[0]
        if not NARROW.search(args + ' '):
            return True
    return False


def origin_main(wt):
    subprocess.run(['git', 'fetch', '-q', 'origin'], cwd=wt)
    return subprocess.run(['git', 'rev-parse', 'origin/main'], cwd=wt, capture_output=True, text=True).stdout.strip()


PRIV = os.path.join(WORK, 're')
HANDOFF_LINES = 60


def handoff_rev(lane):
    """The handoff's last commit on the private repo's remote (a line may push it from its own clone) plus the local
    file's mtime: either moving means the handoff was updated."""
    subprocess.run(['git', 'fetch', '-q', 'origin'], cwd=PRIV)
    rev = subprocess.run(['git', 'log', '-1', '--format=%H', 'origin/main', '--', f'handoff-{lane}.md'], cwd=PRIV,
                         capture_output=True, text=True).stdout.strip()
    f = os.path.join(PRIV, f'handoff-{lane}.md')
    return rev, (os.path.getmtime(f) if os.path.exists(f) else 0)


def set_aside_copies():
    """An untracked file in work/re that origin now tracks with the same text (a line wrote its evidence here and
    committed it from a temporary worktree) blocks the merge. Move such copies to backup/sync-aside/ -- never delete
    (deleting is the user's call); one whose text differs is set aside under a time stamp."""
    names = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], cwd=PRIV, capture_output=True,
                           text=True, encoding='utf-8', errors='replace').stdout.split('\n')
    # only the ones origin tracks (one listing): thousands of untracked decompiler outputs made one `git show` each
    tracked = set(subprocess.run(['git', 'ls-tree', '-r', '--name-only', 'origin/main'], cwd=PRIV, capture_output=True,
                                 text=True, encoding='utf-8', errors='replace').stdout.split('\n'))
    for name in (n for n in names if n and n in tracked):
        theirs = subprocess.run(['git', 'show', f'origin/main:{name}'], cwd=PRIV, capture_output=True)
        if theirs.returncode:
            continue
        path = os.path.join(PRIV, name)
        with open(path, 'rb') as f:
            mine = f.read()
        # a differing copy is an earlier write the line later committed from its own worktree (11-11 c_dodge_*.json
        # blocked two launches): set it aside too, under its own stamp -- moved, never deleted
        same = mine.replace(b'\r', b'') == theirs.stdout.replace(b'\r', b'')
        dest = os.path.join(PRIV, 'backup', 'sync-aside', name if same else name + time.strftime('.%m%d_%H%M%S'))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        os.replace(path, dest)
    # a tracked file edited here whose text is already what origin has (the edit was pushed from elsewhere): take
    # origin's copy, nothing is lost; an edit origin does not have stays and the merge reports it
    names = subprocess.run(['git', 'diff', '--name-only'], cwd=PRIV, capture_output=True, text=True,
                           encoding='utf-8', errors='replace').stdout.split('\n')
    for name in filter(None, names):
        theirs = subprocess.run(['git', 'show', f'origin/main:{name}'], cwd=PRIV, capture_output=True)
        path = os.path.join(PRIV, name)
        if theirs.returncode or not os.path.exists(path):
            continue
        with open(path, 'rb') as f:
            mine = f.read()
        if mine.replace(b'\r', b'') == theirs.stdout.replace(b'\r', b''):
            subprocess.run(['git', 'checkout', '-q', 'origin/main', '--', name], cwd=PRIV)


def sync_handoffs():
    """Bring the shared private repo (work/re, where the lines' handoffs live) up to origin before Codex reads it: a
    stale copy once sent a fresh session back to an already-answered question. Fast-forward only, keeping other lines'
    uncommitted edits; returns '' or the reason it could not."""
    subprocess.run(['git', 'fetch', '-q', 'origin'], cwd=PRIV)
    set_aside_copies()
    r = subprocess.run(['git', 'merge', '-q', '--ff-only', 'origin/main'], cwd=PRIV, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode:
        # local commits that are already on origin (a line pushed them from a temporary worktree): move past them,
        # keeping uncommitted edits (--keep refuses rather than overwrite one)
        cherry = subprocess.run(['git', 'cherry', 'origin/main', 'HEAD'], cwd=PRIV, capture_output=True,
                                text=True).stdout.split('\n')
        if all(line.startswith('-') for line in cherry if line.strip()):
            r = subprocess.run(['git', 'reset', '-q', '--keep', 'origin/main'], cwd=PRIV, capture_output=True,
                               text=True, encoding='utf-8', errors='replace')
    return '' if r.returncode == 0 else 'work/re 没同步到远端，Codex 可能读到旧交接：' + (r.stderr.strip()[-200:])


def analyse(events_path):
    cmds, msgs, usage = [], [], collections.Counter()
    for raw in open(events_path, encoding='utf-8', errors='replace'):
        try:
            e = json.loads(raw)
        except ValueError:
            continue
        it = e.get('item') or {}
        if e.get('type') == 'item.completed' and it.get('type') == 'command_execution':
            cmds.append(it.get('command', ''))
        if e.get('type') == 'item.completed' and it.get('type') == 'agent_message':
            msgs.append(it.get('text', ''))
        if e.get('type') == 'turn.completed':
            usage.update({k: v for k, v in (e.get('usage') or {}).items() if isinstance(v, int)})
    return cmds, msgs, usage


def warnings(cmds, pushed, handoff_changed, minutes, limit):
    w = []
    full = [c for c in cmds if full_suite(c)]
    if full:
        w.append(f'跑了全量测试 {len(full)} 次：' + full[0][-160:])
    # reading a log's tail while a test runs is waiting, not retrying
    rep = [(c, n) for c, n in collections.Counter(cmds).items() if n >= 3 and not re.search(r'Get-Content|\btail\b', c)]
    for c, n in rep[:3]:
        w.append(f'同一个命令跑了 {n} 次：' + c[-160:])
    bench = sum(len(re.findall(r'run_queue\.py\s+\w+:\w+', c)) for c in cmds)  # a real queue run, not a read of the file
    if bench >= 6:
        w.append(f'上台 {bench} 次')
    if not pushed:
        w.append('没有推到 main')
    if not handoff_changed:
        w.append('交接没改')
    if minutes >= limit * 0.95:
        w.append('到了时间上限被停掉')
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lane', choices=['c', 'e'])
    ap.add_argument('--minutes', type=int, default=120)
    ap.add_argument('--effort', default='medium')
    a = ap.parse_args()
    wt = os.path.join(LAB, f'RA3-CampaignLab-codex{a.lane}')
    exe = codex()
    if not exe or not os.path.isdir(wt):
        sys.exit(f'no codex.exe ({exe}) or no worktree {wt}')
    stamp = datetime.datetime.now().strftime('%m%d_%H%M')
    events = os.path.join(LOGS, f'codex_{a.lane}_{stamp}.jsonl')
    stale = sync_handoffs()
    if stale:   # a session that reads an old ticket redoes or skips work: do not start it (11-11 20:45 a C run did)
        sys.exit(stale)
    before, h0, t0 = origin_main(wt), handoff_rev(a.lane), time.time()
    prompt = PROMPT.format(L=a.lane.upper(), lane=a.lane, wt=wt)
    cmd = [exe, 'exec', '--json', '--dangerously-bypass-approvals-and-sandbox', '-C', wt,
           '-c', f'model_reasoning_effort="{a.effort}"', *bench_mcp(wt), prompt]
    with open(events, 'w', encoding='utf-8') as out:
        try:
            subprocess.run(cmd, cwd=wt, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                           timeout=a.minutes * 60)
        except subprocess.TimeoutExpired:
            pass
    minutes = round((time.time() - t0) / 60, 1)
    after = origin_main(wt)
    pushed = subprocess.run(['git', 'log', '--oneline', f'{before}..{after}'], cwd=wt, capture_output=True,
                            text=True, encoding='utf-8').stdout.split('\n')
    pushed = [p for p in pushed if p.strip()]
    cmds, msgs, usage = analyse(events)
    size = []
    try:
        lines = open(os.path.join(PRIV, f'handoff-{a.lane}.md'), encoding='utf-8').read().splitlines()
        if len(lines) > HANDOFF_LINES:   # a long handoff is read whole at the start and replayed on every command
            size = [f'交接 {len(lines)} 行，超过 {HANDOFF_LINES}：做完的、答过的要搬进 handoff-{a.lane}-archive.md']
    except OSError:
        pass
    rec = {'time': stamp, 'lane': a.lane, 'minutes': minutes, 'commands': len(cmds),
           'tokens_in': usage.get('input_tokens', 0), 'tokens_cached': usage.get('cached_input_tokens', 0),
           'tokens_out': usage.get('output_tokens', 0), 'pushed': pushed[:10],
           'warnings': ([stale] if stale else []) + warnings(cmds, pushed, handoff_rev(a.lane) != h0, minutes,
                                                            a.minutes) + size,
           'events': events, 'last': (msgs[-1] if msgs else '')[:1500]}
    os.makedirs(os.path.dirname(SUMMARY), exist_ok=True)
    with open(SUMMARY, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print(json.dumps(rec, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
