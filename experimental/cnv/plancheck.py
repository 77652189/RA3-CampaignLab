"""A level plan read back (plan.py): the beat sheet it makes, its design check against what the retail missions do
(docs/story/map-language.md 7, the numbers below), and the build's contract -- all without the game.

  python -I -X utf8 experimental/cnv/plancheck.py a4
  python -I -X utf8 experimental/cnv/plancheck.py --vocab     the words a plan may use
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plan                                     # noqa: E402

# retail ranges (map-language.md 7; 9 late missions read, 40 maps counted)
PHASES = (3, 4, 2, 6)                           # typical low, high; still seen low, high
GOALS = (2, 9)
TOKEN = 30.0                                    # with a base from the start: a token threat within 20-30 s
FIRST_ATTACK = (80.0, 480.0)                    # real attacks start (normal difficulty)


def times_of(c, starts, devices=None):
    """When a condition first holds, in seconds from the start (normal difficulty), if a time decides it: the
    earliest of its alternatives that is `开局 + t`, `段 <phase> + t` with that phase's start known, or a device's
    event the plan times itself (车队.出发 when its 出发 is). None if the player's play decides it."""
    devices = devices if devices is not None else starts.get('', {})
    if isinstance(c, dict):
        ts = [times_of(x, starts, devices) for x in c.get('任一', [])]
        ts = [t for t in ts if t is not None]
        return min(ts) if ts else None
    if isinstance(c, list):
        ts = [times_of(x, starts, devices) for x in c]
        return None if None in ts else max(ts, default=0.0)
    s = str(c).strip()
    if s == '开局':
        return 0.0
    m = re.match(r'^(.*?)\s*\+\s*([^+]+)$', s)
    if m:
        base = times_of(m.group(1), starts, devices)
        return None if base is None else base + plan.spans(m.group(2))[1][1]     # a random time: its latest
    m = re.match(r'^段\s+(.+?)(\s+开始)?$', s)
    if m:
        return starts.get(m.group(1))
    m = re.match(r'^(\S+)\.(\S+)$', s)
    if m and m.group(2) in (devices.get(m.group(1)) or {}):
        return times_of(devices[m.group(1)][m.group(2)], starts, devices)
    return None


def sooner(c, starts, early):
    """True if the player can make c hold before times_of says, which is then only the latest (review 2026-10-24):
    an any-of with an alternative the player decides, or waiting on a phase the player can start sooner (`early`)."""
    devices = starts.get('', {})
    if isinstance(c, dict):
        xs = c.get('任一', [])
        return any(times_of(x, starts) is None or sooner(x, starts, early) for x in xs)
    if isinstance(c, list):
        return any(sooner(x, starts, early) for x in c)
    s = str(c).strip()
    m = re.match(r'^(.*?)\s*\+\s*([^+]+)$', s)
    if m:
        return sooner(m.group(1), starts, early)
    m = re.match(r'^段\s+(.+?)(\s+开始)?$', s)
    if m:
        return m.group(1) in early
    m = re.match(r'^(\S+)\.(\S+)$', s)
    if m and m.group(2) in (devices.get(m.group(1)) or {}):
        return sooner(devices[m.group(1)][m.group(2)], starts, early)
    return False


def early_phases(d, starts):
    """The phases the player can start sooner than phase_starts says."""
    early, phases = set(), d.get('段') or []
    for prev, ph in zip(phases, phases[1:]):
        if prev.get('结束') is not None and sooner(prev['结束'], starts, early):
            early.add(ph['名字'])
    return early


def at(t, c, starts, early):
    """A time as the reports show it: "最晚 m:ss" when the player can bring it forward."""
    return ('最晚 ' if sooner(c, starts, early) else '') + mmss(t)


def said(a):
    """An action as the beat sheet shows it."""
    if isinstance(a, dict):
        return '，'.join(f'{k} {v}' for k, v in a.items())
    return str(a)


def player_decides(c):
    """True if some alternative is the player's doing (entering, attacking, destroying ...), not a clock."""
    text = repr(c)
    return any(w in text for w in ('进入', '攻击', '摧毁', '占领', '血量', '建成', '清空', '.'))


def mmss(t):
    return f'{int(t // 60)}:{int(t % 60):02d}'


def phase_starts(d):
    starts, t = {'': d.get('机关') or {}}, 0.0          # '': the devices' specs, for the events they time
    for k, ph in enumerate(d.get('段') or []):
        starts[ph['名字']] = t
        nxt = times_of(ph.get('结束'), starts) if ph.get('结束') else None
        if nxt is None:
            break
        t = nxt
    return starts


def beat_sheet(d):
    starts = phase_starts(d)
    early = early_phases(d, starts)
    out = ['节拍表（时间按普通难度；"?" = 看玩家打得多快；"最晚" = 玩家推进快会更早）', '']
    waves = d.get('进攻') or []
    for k, ph in enumerate(d.get('段') or [], 1):
        t = starts.get(ph['名字'])
        when = '开局' if k == 1 else '?' if t is None else ('最晚 ' if ph['名字'] in early else '') + mmss(t)
        out.append(f'第 {k} 段 {ph["名字"]}（{when} 起）')
        for title in ph.get('目标') or []:
            g = (d.get('目标') or {}).get(title, {})
            out.append(f'  {"奖励" if g.get("奖励") else "主"}  {title}')
        if ph.get('边界'):
            out.append(f'  地图边界 → {ph["边界"]}')
        for a in ph.get('开场') or []:
            out.append(f'  开场：{said(a)}')
        if ph.get('结束'):
            out.append(f'  结束：{said(ph["结束"])}')
        out.append('')
    out.append('进攻')
    for w in waves:
        t = times_of(w['开始'], starts)
        troops = '、'.join(f'{u} {n}' for u, n in (w.get('兵') or {}).items())
        rep = f'，每隔 {w["每隔"]}，最多 {w.get("最多", "不限")} 波' if w.get('每隔') else '，一次'
        src = f'，来源 {"、".join(w["来源"])}（没了就停）' if w.get('来源') else ''
        until = f'，{w["直到"]} 以后不再来' if w.get('直到') else ''
        when = at(t, w['开始'], starts, early) if t is not None else '看玩家'
        out.append(f'  {w["名字"]}：{when} 起（{w["开始"]}）；{troops}；从 {w.get("从")} 打 {w.get("打") or w.get("守")}'
                   f'{rep}{src}{until}')
    ai = d.get('敌方AI')
    if ai:
        def when(c):
            t = times_of(c, starts) if c else None
            return '不放开' if not c else at(t, c, starts, early) if t is not None else '看玩家'
        out.append(f'  敌方AI（{ai.get("性格", "平衡")}）：{when(ai.get("唤醒"))} 醒来、在 {ai.get("基地")} 建基地并自己进攻'
                   f'（测试台上：交给它守军时醒来约半分钟就过来，只给建筑约 1 分钟），资金 {ai.get("资金", 0)}'
                   + (f'；上限 {"、".join(f"{u} {n}" for u, n in ai["上限"].items())}' if ai.get('上限') else ''))
    return '\n'.join(out)


def design_check(d):
    """[(level, text)]: level '问题' (against what retail does, fix it), '注意' (check it is meant), '符合'."""
    out = []
    phases = d.get('段') or []
    n = len(phases)
    lo, hi, lo2, hi2 = PHASES
    out.append(('符合' if lo <= n <= hi else '注意' if lo2 <= n <= hi2 else '问题',
                f'分段：{n} 段（原版一般 {lo}～{hi} 段，见过 {lo2}～{hi2} 段）'))
    starts = phase_starts(d)
    early = early_phases(d, starts)
    mids = [p['名字'] for p in phases[1:-1] if p.get('边界') or any(isinstance(a, dict) and '镜头' in a
                                                                      for a in p.get('开场') or [])]
    out.append(('符合' if mids else '注意', f'中段反转（过场里扩地图或镜头）：{"、".join(mids) or "没有"}'))
    for p in phases[:-1]:
        end = p.get('结束')
        if end is None:
            out.append(('问题', f'第 {p["名字"]} 段没有"结束"，下一段开始不了'))
        elif times_of(end, starts) is None and '+' not in repr(end):
            hint = [r for r in d.get('规则') or [] if f'段 {p["名字"]} +' in repr(r.get('当'))]
            out.append(('符合', f'{p["名字"]} 段靠玩家推进才结束，卡住了有定时的提示（规则）') if hint else
                       ('注意', f'{p["名字"]} 段只靠玩家推进才结束（{end}）：卡住了有没有提示或时间兜底？'))
    base = any(u.get('单位') in ('建造厂', '基地车') and u.get('阵营', '我') == '我'
               for u in (d.get('开局') or {}).get('部队') or [])
    waves = list(d.get('进攻') or [])
    ai = d.get('敌方AI')
    if ai and ai.get('唤醒'):       # the skirmish AI's army: retail's lasting pressure (retail/README.md 1); it
        waves.append({'名字': '敌方AI', '开始': ai['唤醒']})        # fights from waking (plan.py compile_ai)
        out.append(('符合', '持续压力来自遭遇战 AI（敌方AI）：拆掉它的生产建筑就停（原版的做法）'))
    first = sorted((t, w['名字']) for w in waves if (t := times_of(w['开始'], starts)) is not None)
    if base:
        token = [x for x in first if x[0] <= TOKEN + 30]
        out.append(('符合' if token else '注意', f'开局有基地：第一股威胁 {mmss(first[0][0]) + " " + first[0][1] if first else "没有定时的"}'
                    f'（原版 20～30 秒内有一股象征性威胁）'))
    real = [x for x in first if x[0] > TOKEN + 30]
    if real:
        t, name = real[0]
        lo, hi = FIRST_ATTACK
        w = next(x for x in waves if x['名字'] == name)
        soon = '（玩家推进快会更早）' if sooner(w['开始'], starts, early) else ''
        out.append(('符合' if lo <= t <= hi else '注意', f'第一波真正的进攻：{at(t, w["开始"], starts, early)} {name}'
                                                        f'{soon}（原版 {mmss(lo)}～{mmss(hi)}）'))
    for w in waves:
        if w.get('每隔') and not (w.get('最多') or w.get('来源')):
            out.append(('问题', f'进攻 {w["名字"]} 每隔一段时间来一波，却没有上限也没有来源：玩家关不掉它'))
        elif w.get('每隔'):
            out.append(('符合', f'进攻 {w["名字"]}：{"来源 " + "、".join(w["来源"]) if w.get("来源") else ""}'
                                f'{" 最多 " + str(w["最多"]) + " 波" if w.get("最多") else ""}（原版每路压力都有来源或上限）'))
        both = isinstance(w['开始'], dict) and times_of(w['开始'], starts) is not None and player_decides(w['开始'])
        if both:
            out.append(('符合', f'进攻 {w["名字"]}：按时到，或者玩家先推进就提前（原版最常见的写法）'))
    goals = d.get('目标') or {}
    bonus = [t for t, g in goals.items() if g.get('奖励')]
    out.append(('符合' if GOALS[0] <= len(goals) <= GOALS[1] and bonus else '注意',
                f'目标 {len(goals)} 个，其中奖励 {len(bonus)} 个（原版 2～9 个，几乎每关有奖励目标）'))
    for t, g in goals.items():
        if not g.get('奖励') and not g.get('标记'):
            out.append(('注意', f'主目标"{t}"没有标记（原版 95% 的目标挂了标记）'))
    shown = {t for p in phases for t in p.get('目标') or []}
    for t in goals:
        if t not in shown:
            out.append(('问题', f'目标"{t}"不在任何一段里，永远不会亮出来'))
    saves = [p['名字'] for p in phases[1:] if not p.get('存档')]
    out.append(('符合' if not saves else '注意', '每段开头自动存档' + (f'：{"、".join(saves)} 没有' if saves else '')))
    money = (d.get('开局') or {}).get('资金')
    if money is not None:
        m = plan.counts(money)
        out.append(('符合' if m[0] >= m[1] >= m[2] else '问题', f'开局资金 {"/".join(map(str, m))}（原版困难最少）'))
    for w in waves:
        for u, c in (w.get('兵') or {}).items():
            c3 = plan.counts(c)
            if not c3[0] <= c3[1] <= c3[2]:
                out.append(('问题', f'进攻 {w["名字"]} 的 {u} {"/".join(map(str, c3))}：难度越高应该越多'))
    hints = sum(1 for r in d.get('规则') or [] for a in r.get('做') or [] if isinstance(a, str) and a.startswith('通报'))
    out.append(('符合' if hints else '注意', f'提示：规则里有 {hints} 条通报（原版快输了不送援军，只给提示）'))
    return out


def report(level):
    d = plan.load(level)
    lines = [f'{d.get("关卡")} {d.get("名字")}：{d.get("一句话", "")}', '', beat_sheet(d), '', '设计检查（对照原版）']
    for lv, text in design_check(d):
        lines.append(f'  [{lv}] {text}')
    try:
        import parts
        m = plan.mission(level)
        bad = parts.contract(parts.merged(m))
        lines += ['', f'编译：{len(m.scripts)} 个脚本、{len(m.objects)} 个物体、{len(m.objectives)} 个目标；'
                      f'接口检查 {"ok" if not bad else str(len(bad)) + " 个问题"}'] + [f'  {b}' for b in bad[:20]]
    except plan.PlanError as e:
        lines += ['', f'编译失败：{e}']
    return '\n'.join(lines)


def vocab(map_name=None):
    """The words a plan may write: conditions, actions, devices (their params, events, actions), units, and with
    map_name that map's sites and borders."""
    import glossary
    from devices import registry
    with open(os.path.join(plan.PLANS, 'README.md'), encoding='utf-8') as f:
        readme = f.read()
    a, b = readme.index('## 词表'), readme.index('<!-- plan_vocab 读到这里 -->')
    words = '\n'.join(x for x in readme[a:b].splitlines() if not x.startswith('<!--'))
    out = [words.rstrip(), '', '机关（类型）']
    for kind, cls in registry().items():
        out.append(f'  {kind}：{cls.WHAT}')
        for group, items in (('参数', cls.PARAMS), ('事件', cls.EVENTS), ('动作', cls.ACTIONS)):
            for k, v in items.items():
                out.append(f'    {group} {k}：{v}')
        if cls.TARGET:
            out.append(f'    进攻的"打"写它：{cls.TARGET}')
    n = glossary.names()
    out += ['', '单位（各阵营通用，按阵营换成对应的）：' + '、'.join(n['shared']),
            '单位（某一阵营自己的）：' + '、'.join(n['own'])]
    if map_name:
        import importlib
        mm = importlib.import_module(f'maps.{map_name}')
        out += ['', f'地图 {map_name} 的地点：'] + [f'  {k}：{s.what}' for k, s in mm.SITES.items()]
        out.append(f'地图边界：{list(getattr(mm, "BORDERS", {})) or "只有全图"}')
    return '\n'.join(out)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('level', nargs='?')
    ap.add_argument('--vocab', nargs='?', const='', default=None, help='the words a plan may use (with a map name: '
                                                                      'its sites too)')
    a = ap.parse_args()
    print(vocab(a.vocab or None) if a.vocab is not None else report(a.level))
