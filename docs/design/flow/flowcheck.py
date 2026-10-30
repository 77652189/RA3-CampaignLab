"""Checks the level flow scripts (docs/design/flow/<level>.md) for completeness and consistency only -- whether a
script is good is the user's call (ADR 0008). What it checks is listed in README.md section 4.

    python docs/design/flow/flowcheck.py            # every flow script
    python docs/design/flow/flowcheck.py a4 j7      # some of them

Prints one line per problem and exits 1 if there is any.
"""
import pathlib
import re
import sys

import yaml

import flowmap

HERE = pathlib.Path(__file__).resolve().parent
NOT_SCRIPTS = ('README.md', 'cast.md', 'mechanics.md', 'style.md')    # the folder's other documents
TOP = ('关', '关名', '阵营', '类型', '位置', '基地', '地点', '新东西', '出场单位', '用到的机制', '一句话', '体验目标',
       '取舍', '张力', '接上一关', '引出下一关', '简报', '段', '胜利', '失败', '示意图')
TYPES = ('护送', '突击', '基地对抗', '守', '潜入', '海战', '限时', '打自己人')
GOAL_KINDS = ('主', '奖励')
# voice-script rules (RA3-ChineseVoice lines/GLOSSARY.md): no digits, no Latin letters, no brackets
BAD_IN_LINE = re.compile(r'[0-9A-Za-z()（）\[\]【】]')
# a retail line is 3.5 s, ~16 characters of the official Chinese; 30 is the 90th percentile (teardowns/telling.md)
MAX_LINE = 30
PUNCT = re.compile(r'[\s，。！？、；：…—“”‘’"\'.,!?]')


def cast():
    """(speakers who may say new lines, retail-only characters) from cast.md's two tables."""
    speak, retail, part = set(), set(), None
    for line in (HERE / 'cast.md').read_text(encoding='utf-8').splitlines():
        if line.startswith('## '):
            part = speak if '新台词' in line else retail if '原版' in line else None
        elif part is not None and line.startswith('| ') and not line.startswith('| 键') and '---' not in line:
            part.add(line.split('|')[1].strip())
    return speak, retail


VOICE_GLOSSARY = HERE.parents[3] / 'RA3-ChineseVoice' / 'lines' / 'GLOSSARY.md'
OUTLINE = HERE.parents[1] / 'story' / 'outline.md'
PLAN_GLOSSARY = HERE.parents[2] / 'experimental' / 'cnv' / 'glossary.py'


def unit_names():
    """Names 出场单位 may list: the voice line's glossary (RA3-ChineseVoice, the authority for unit names), our own
    new units (outline.md section 3) and the plan compiler's buildings (experimental/cnv/glossary.py). None when the
    voice repo is not next to this one."""
    if not VOICE_GLOSSARY.exists():
        return None
    names = set(re.findall(r'([一-鿿A-Z0-9-]+)\([A-Za-z][^)]*\)', VOICE_GLOSSARY.read_text(encoding='utf-8')))
    for line in OUTLINE.read_text(encoding='utf-8').splitlines():
        if line.startswith(('| 盟军 |', '| 苏联 |', '| 帝国 |')):
            for cell in line.split('|')[2:4]:
                names |= {re.sub(r'[（(].*', '', w).strip('* ') for w in re.split('[、，]', cell)}
    if PLAN_GLOSSARY.exists():
        names |= set(re.findall(r"'([一-鿿][^']*)':", PLAN_GLOSSARY.read_text(encoding='utf-8')))
    return {n for n in names if n}


MECH_STATES = ('已确认', '待验证', '不能做')


def mechanics():
    """{key: (state, forbidden-phrasing regex or None)} from mechanics.md's table; a cell's '\\|' is a literal pipe."""
    out = {}
    for line in (HERE / 'mechanics.md').read_text(encoding='utf-8').splitlines():
        cells = [c.replace('\\|', '|').strip() for c in re.split(r'(?<!\\)\|', line)[1:-1]]
        if len(cells) == 5 and cells[1] in MECH_STATES:
            out[cells[0]] = (cells[1], re.compile(cells[4]) if cells[4] else None)
    return out


def all_text(node):
    """Every string in the plan, keys included (a 时机 or a shot may promise something too)."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield str(k)
            yield from all_text(v)
    elif isinstance(node, list):
        for v in node:
            yield from all_text(v)
    elif node is not None:
        yield str(node)


def plan_of(path):
    m = re.search(r'```yaml\n(.*?)```', path.read_text(encoding='utf-8'), re.S)
    return yaml.safe_load(m.group(1)) if m else None


def lines_in(node, where):
    """Every spoken line under node: (where, speaker, text). Lines are one-key maps under 简报 or 台词."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ('简报', '台词') and isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict) and len(item) == 1:
                        (who, text), = item.items()
                        yield f'{where}/{k}[{i}]', who, text
                    else:
                        yield f'{where}/{k}[{i}]', None, item
            else:
                yield from lines_in(v, f'{where}/{k}')
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from lines_in(v, f'{where}[{i}]')


def check(path, speak, retail, units=None, mech=None):
    p = plan_of(path)
    if not isinstance(p, dict):
        return [f'{path.name}: no yaml block']
    out = []
    for k in TOP:
        if p.get(k) in (None, '', [], {}):
            out.append(f'{path.name}: missing {k}')
    if str(p.get('关', '')).lower() != path.stem.lower():
        out.append(f'{path.name}: 关 {p.get("关")} does not match the file name')
    if p.get('类型') not in TYPES:
        out.append(f'{path.name}: 类型 {p.get("类型")} is not one of {"/".join(TYPES)}')
    for i, seg in enumerate(p.get('段') or []):
        name = f'{path.name} 段[{i}] {seg.get("名", "?")}'
        if not seg.get('结束'):
            out.append(f'{name}: missing 结束')
        goals = seg.get('目标') or []
        for g in goals:
            if g.get('种') not in GOAL_KINDS or not g.get('题') or not g.get('说明'):
                out.append(f'{name}: objective {g.get("题")} needs 种 (主/奖励), 题 and 说明')
            elif g.get('种') == '奖励' and not g.get('回报'):
                out.append(f'{name}: bonus {g.get("题")} needs 回报, what the player gets for it (P16){REVIEW[3]}')
        if goals and not seg.get('下一步靠什么'):
            out.append(f'{name}: has objectives but no 下一步靠什么')
        if any(g.get('种') == '主' for g in goals) and not seg.get('卡住了'):
            out.append(f'{name}: has a main objective but no 卡住了')
    for f in p.get('失败') or []:
        if not f.get('原因') or not f.get('台词'):
            out.append(f'{path.name} 失败: every failure needs 原因 and 台词')
    for where, who, text in lines_in(p, path.name):
        if who is None:
            out.append(f'{where}: a line must be "speaker: text", got {text!r}')
        elif who in retail:
            out.append(f'{where}: {who} only says retail lines (cast.md) -- write it as an action in the shot')
        elif who not in speak:
            out.append(f'{where}: speaker {who} is not in cast.md')
        elif not isinstance(text, str) or not text.strip():
            out.append(f'{where}: empty line')
        elif BAD_IN_LINE.search(text):
            out.append(f'{where}: digits, Latin letters or brackets in a voice line: {text}')
        elif len(PUNCT.sub('', text)) > MAX_LINE:
            out.append(f'{where}: {len(PUNCT.sub("", text))} characters, over {MAX_LINE} (README rule 10): {text}')
    if units is not None:
        for side, names in (p.get('出场单位') or {}).items():
            for n in names or []:
                if n not in units:
                    out.append(f'{path.name} 出场单位/{side}: {n} is in neither the voice glossary, outline.md '
                               f'section 3 nor the plan glossary')
    out += check_sketch(path, p)
    out += check_scale(path, p, unlocks())
    out += check_review(path, p, speak | retail, mech)
    if mech is not None:
        for k in p.get('用到的机制') or []:
            if k not in mech:
                out.append(f'{path.name} 用到的机制: {k} is not in mechanics.md')
            elif mech[k][0] == '不能做':
                out.append(f'{path.name} 用到的机制: {k} is marked 不能做 in mechanics.md')
        text = '\n'.join(all_text(p))
        for k, (state, bad) in mech.items():
            if state == '不能做' and bad and (m := bad.search(text)):
                out.append(f'{path.name}: "{m.group(0)}" promises {k}, which cannot be done (mechanics.md)')
    return out


# The user's five review points for layer 1 (2026-10-29, README rules 16-20): each is a part of the template that must
# be filled and agree with the rest of the script; whether it is good is the user's call. A problem names its point,
# so the viewer can sort them.
REVIEW = {n: f' (审核第 {n} 条)' for n in range(1, 6)}
REVIEW_KEYS = {'故事': 1, '人物': 1, '开局': 3, '解法': 3, '平推会怎样': 3, '意外': 4, '保底': 5}
TURNS_LEAST = 3                 # 故事/起伏: at least this many turns, both 顺 and 逆 among them
LINES_FOR_ROLE = 3              # a speaker with this many lines in the level gets an entry in 人物
WAYS_LEAST = 2                  # 解法: at least two ways through
ARMY_KINDS = 2                  # 段/敌军: at least two kinds of enemy, and two different counters (P29)
EMPTY_LAST = 0.15               # the last segment: its largest empty patch, of the ground it lets the player reach
BACKUP_MECH = '兵少补援'          # the mechanic a 保底 promises (mechanics.md)


def _seg_index(p, name, extra=()):
    """Where a 段 named by a review entry falls in the level: 简报 before every segment, 胜利 after; None if unknown."""
    segs = [s.get('名') for s in p.get('段') or []]
    if name == '简报' and '简报' in extra:
        return -1
    if name == '胜利' and '胜利' in extra:
        return len(segs)
    return segs.index(name) if name in segs else None


def _missing(entry, keys):
    return [k for k in keys if not (entry or {}).get(k)]


def check_review(path, p, cast_keys, mech):
    """The five review points: 故事 and 人物 (1), the last segment's empty ground (2), 开局, 解法 and 平推会怎样 (3;
    every bonus's 回报 is checked with the objectives), 意外 (4) and 保底 (5), each surprise paired with a 保底."""
    out, n = [], path.name
    for k, point in REVIEW_KEYS.items():
        if p.get(k) in (None, '', [], {}):
            out.append(f'{n}: missing {k}{REVIEW[point]}')
    if out:
        return out                      # fill the five parts first; the details are checked once they are there
    story = p.get('故事') or {}
    for k in _missing(story, ('开头', '结尾')):
        out.append(f'{n} 故事: missing {k}{REVIEW[1]}')
    turns = story.get('起伏') or []
    if len(turns) < TURNS_LEAST:
        out.append(f'{n} 故事/起伏: {len(turns)} turns, needs at least {TURNS_LEAST}{REVIEW[1]}')
    if turns and not {'顺', '逆'} <= {t.get('向') for t in turns}:
        out.append(f'{n} 故事/起伏: the turns go one way only -- both 顺 (for the player) and 逆 are needed{REVIEW[1]}')
    last = -2
    for t in turns:
        i = _seg_index(p, t.get('段'), ('简报', '胜利'))
        if i is None:
            out.append(f'{n} 故事/起伏: 段 {t.get("段")} is not a segment of this level{REVIEW[1]}')
            continue
        if t.get('向') not in ('顺', '逆') or not t.get('事'):
            out.append(f'{n} 故事/起伏/{t.get("段")}: needs 向 (顺/逆) and 事{REVIEW[1]}')
        if i < last:
            out.append(f'{n} 故事/起伏: {t.get("段")} comes before the turn above it -- write them in order{REVIEW[1]}')
        last = max(last, i)
    roles = {}
    for r in p.get('人物') or []:
        who = r.get('谁')
        roles[who] = r
        if who not in cast_keys:
            out.append(f'{n} 人物: {who} is not in cast.md{REVIEW[1]}')
        for k in _missing(r, ('想要', '看得出')):
            out.append(f'{n} 人物/{who}: missing {k}{REVIEW[1]}')
        turn = r.get('转折') or {}
        if not turn.get('事') or _seg_index(p, turn.get('段'), ('简报', '胜利')) is None:
            out.append(f'{n} 人物/{who}: 转折 needs 段 (a segment of this level) and 事{REVIEW[1]}')
    said = {}
    for _, who, _ in lines_in(p, n):
        said[who] = said.get(who, 0) + 1
    for who, k in said.items():
        if k >= LINES_FOR_ROLE and who != '播报' and who not in roles:
            out.append(f'{n} 人物: {who} has {k} lines in this level but no entry in 人物{REVIEW[1]}')

    segs = [s.get('名') for s in p.get('段') or []]
    if segs and (p.get('示意图') or {}).get('可玩区'):
        gap = flowmap.empty(p).get(segs[-1])
        if gap and gap['占'] > EMPTY_LAST:
            out.append(f'{n} 示意图: in the last segment ({segs[-1]}) {gap["占"]:.0%} of the ground is one empty patch '
                       f'(no place or route near it), over {EMPTY_LAST:.0%} -- shrink its 可玩区 or give that ground a '
                       f'use (P24){REVIEW[2]}')

    for k in _missing(p.get('开局'), ('手上', '敌方')):
        out.append(f'{n} 开局: missing {k}{REVIEW[3]}')
    ways = p.get('解法') or []
    if len(ways) < WAYS_LEAST:
        out.append(f'{n} 解法: {len(ways)} ways through, needs at least {WAYS_LEAST}{REVIEW[3]}')
    for w in ways:
        for k in _missing(w, ('打法', '提示')):
            out.append(f'{n} 解法/{w.get("打法")}: missing {k}{REVIEW[3]}')
        if _seg_index(p, w.get('段')) is None:
            out.append(f'{n} 解法/{w.get("打法")}: 段 {w.get("段")} is not a segment of this level{REVIEW[3]}')

    foes = set((p.get('出场单位') or {}).get('敌') or [])
    for s in p.get('段') or []:
        if not s.get('动词'):
            continue
        name = f'{n} 段 {s.get("名")} 敌军'
        army = s.get('敌军')
        if isinstance(army, str) and army.startswith('无'):
            continue                    # a breather: 无：why
        if not isinstance(army, list) or not army:
            out.append(f'{name}: a playable segment says who it fights (P29), or 无：why{REVIEW[3]}')
            continue
        for e in army:
            for k in _missing(e, ('兵', '怎么来', '克制')):
                out.append(f'{name}/{e.get("兵")}: missing {k}{REVIEW[3]}')
            if e.get('兵') and e['兵'] not in foes:
                out.append(f'{name}/{e["兵"]}: not in 出场单位/敌{REVIEW[3]}')
        if len({e.get('兵') for e in army}) < ARMY_KINDS or len({e.get('克制') for e in army}) < ARMY_KINDS:
            out.append(f'{name}: at least {ARMY_KINDS} kinds of enemy, answered by at least {ARMY_KINDS} different '
                       f'counters -- one kind of unit must not clear the segment (P29){REVIEW[3]}')

    backups = {b.get('名'): b for b in p.get('保底') or []}
    for s in p.get('意外') or []:
        name = f'{n} 意外/{s.get("名")}'
        for k in _missing(s, ('名', '初见', '准备', '补救')):
            out.append(f'{name}: missing {k}{REVIEW[4]}')
        at = _seg_index(p, s.get('段'))
        if at is None:
            out.append(f'{name}: 段 {s.get("段")} is not a segment of this level{REVIEW[4]}')
        hint = s.get('伏笔') or {}
        before = _seg_index(p, hint.get('段'), ('简报',))
        if not hint.get('事') or before is None:
            out.append(f'{name}: 伏笔 needs 段 (简报 or a segment) and 事 -- where a returning player sees it '
                       f'coming{REVIEW[4]}')
        elif at is not None and before > at:
            out.append(f'{name}: 伏笔 in {hint.get("段")} comes after the surprise itself{REVIEW[4]}')
        if s.get('补救') and s['补救'] not in backups:
            out.append(f'{name}: 补救 {s["补救"]} is not one of this level\'s 保底 -- every surprise has a way '
                       f'back{REVIEW[4]}')
    names = places(p)
    for b in p.get('保底') or []:
        name = f'{n} 保底/{b.get("名")}'
        for k in _missing(b, ('名', '坏档', '条件', '援军', '从哪来')):
            out.append(f'{name}: missing {k}{REVIEW[5]}')
        if _seg_index(p, b.get('段')) is None:
            out.append(f'{name}: 段 {b.get("段")} is not a segment of this level{REVIEW[5]}')
        if b.get('从哪来') and names and b['从哪来'] not in names:
            out.append(f'{name}: 从哪来 {b["从哪来"]} is not a place of the sketch (示意图){REVIEW[5]}')
    if p.get('保底') and mech is not None and BACKUP_MECH not in (p.get('用到的机制') or []):
        out.append(f'{n} 用到的机制: a 保底 promises {BACKUP_MECH} -- list it{REVIEW[5]}')
    return out + check_placing(path, p)


def check_placing(path, p):
    """摆放要求 (README rule 21, ADR 0009): points 2, 3 and 5 written as what the level line places -- a 边界 entry
    for every change of the playable area, at least one 资源点 and one 伏击点, every one on a place of the sketch (and,
    on a real map, a site of it); every 保底 on a real map names the site its reinforcement comes in at."""
    out, n = [], path.name
    want = p.get('摆放要求') or {}
    if not want:
        return [f'{n}: missing 摆放要求 -- points 2, 3 and 5 as what the level line places{REVIEW[2]}']
    sk = p.get('示意图') or {}
    mod = flowmap.load(sk['地图']) if sk.get('地图') else None
    names = places(p)
    zones = sk.get('可玩区') or {}
    segs = [s.get('名') for s in p.get('段') or []]
    borders = {b.get('段'): b for b in want.get('边界') or []}
    for a, b in zip(segs, segs[1:]):
        if a in zones and b in zones and str(zones[a]) != str(zones[b]):
            e = borders.get(b)
            if not e or not e.get('何时'):
                out.append(f'{n} 摆放要求/边界: the playable area changes at {b} -- say when (何时){REVIEW[2]}')
            elif str(e.get('换成')) != str(zones[b]):
                out.append(f'{n} 摆放要求/边界/{b}: 换成 {e.get("换成")} but 示意图 has {zones[b]}{REVIEW[2]}')

    def spot(kind, e, point):
        where = f'{n} 摆放要求/{kind}/{e.get("地方")}'
        res = [f'{where}: missing {k}{REVIEW[point]}' for k in _missing(e, ('地方', '什么', '为了'))]
        if e.get('地方') not in names:
            res.append(f'{where}: 地方 is not a place of the sketch (示意图){REVIEW[point]}')
        if _seg_index(p, e.get('段')) is None:
            res.append(f'{where}: 段 {e.get("段")} is not a segment of this level{REVIEW[point]}')
        if mod is not None and e.get('点') not in mod.SITES:
            res.append(f'{where}: 点 {e.get("点")} is not a site of {sk["地图"]}{REVIEW[point]}')
        return res
    for kind, point in (('资源点', 3), ('伏击点', 3), ('援军', 5)):
        entries = want.get(kind) or []
        if kind != '援军' and not entries:
            out.append(f'{n} 摆放要求: no {kind} -- name at least one for the level line to place{REVIEW[point]}')
        for e in entries:
            out += spot(kind, e, point)
    if mod is not None:
        for b in p.get('保底') or []:
            if b.get('点') not in mod.SITES:
                out.append(f'{n} 保底/{b.get("名")}: 点 {b.get("点")} is not a site of {sk["地图"]} -- where the '
                           f'reinforcement comes in{REVIEW[5]}')
    return out


USES = ('前线', '支线', '通道', '后方', '远景')
GRID = (100, 60)

# P31 (principles.md): a level's scale follows its place in its campaign line. The floors are the retail missions'
# lower quartiles by position (teardowns/data/scale.md): main objectives, waves (segments revealing a main
# objective), map changes (the 可玩区 changing between segments), turns (waves - 1 + map changes), verbs (distinct
# 段/动词). A late level gives a base unless it says why not, and combines at least two earlier tools of its line.
POSITION = {n: pos for pos, ns in (('前期', (1, 2, 3)), ('中期', (4, 5, 6)), ('后期', (7, 8, 9))) for n in ns}
FLOOR = {'前期': dict(main=3, waves=1, grows=0, turns=0, verbs=2),
         '中期': dict(main=3, waves=2, grows=1, turns=2, verbs=2),
         '后期': dict(main=3, waves=2, grows=2, turns=3, verbs=2)}
MEASURE = {'main': '主目标', 'waves': '段（亮出主目标的段）', 'grows': '地图变化', 'turns': '局面变化',
           'verbs': '段的动词种数'}
BASES = ('开局', '中途', '无')
LINE = {'盟军': 'A', '苏联': 'S', '帝国': 'J'}


def unlocks():
    """{unit or hero: (line letter, level number)} from outline.md section 3, e.g. 纸鹤侦察机 -> ('J', 3)."""
    out = {}
    for line in OUTLINE.read_text(encoding='utf-8').splitlines():
        if line.startswith(('| 盟军 |', '| 苏联 |', '| 帝国 |')):
            for cell in line.split('|')[2:4]:
                for w in re.split('、', cell):
                    m = re.match(r'\s*\**([^*（(]+?)\**\s*[（(]([ASJ])(\d)', w)
                    if m:
                        out[m.group(1).strip()] = (m.group(2), int(m.group(3)))
    return out


def scale(p):
    """The level's measures for P31."""
    segs = p.get('段') or []
    zones = (p.get('示意图') or {}).get('可玩区') or {}
    seq = [str(zones.get(s.get('名'))) for s in segs if s.get('名') in zones]
    waves = sum(1 for s in segs if any(g.get('种') == '主' for g in s.get('目标') or []))
    grows = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    return dict(main=sum(1 for s in segs for g in s.get('目标') or [] if g.get('种') == '主'), waves=waves,
                grows=grows, turns=max(waves - 1, 0) + grows,
                verbs=len({s['动词'] for s in segs if s.get('动词')}))


def check_scale(path, p, tools):
    out, lvl = [], str(p.get('关', ''))
    m = re.fullmatch(r'([ASJ])(\d)', lvl.upper())
    if not m:
        return out
    pos = POSITION[int(m.group(2))]
    if p.get('位置') != pos:
        out.append(f'{path.name}: 位置 is {p.get("位置")}, but {lvl} is {pos} (1-3 前期, 4-6 中期, 7-9 后期)')
    if p.get('基地') not in BASES:
        out.append(f'{path.name}: 基地 is one of {"/".join(BASES)}, got {p.get("基地")}')
    for s in p.get('段') or []:
        if any(g.get('种') == '主' for g in s.get('目标') or []) and not s.get('动词'):
            out.append(f'{path.name} 段 {s.get("名")}: a segment with a main objective names its 动词')
    have = scale(p)
    for k, floor in FLOOR[pos].items():
        if have[k] < floor:
            out.append(f'{path.name}: P31 {pos} needs {MEASURE[k]} >= {floor}, has {have[k]}')
    if pos == '后期':
        if p.get('基地') == '无' and not p.get('无基地的理由'):
            out.append(f'{path.name}: P31 a late level gives a base; without one it says why (无基地的理由)')
        used = p.get('综合') or []
        if len(used) < 2:
            out.append(f'{path.name}: P31 a late level combines at least two earlier tools of its line (综合)')
        for t in used:
            u = tools.get(t)
            if not u or u[0] != m.group(1) or u[1] >= int(m.group(2)):
                out.append(f'{path.name} 综合: {t} is not a tool an earlier {m.group(1)} level gave (outline.md '
                           f'section 3)')
    return out


def places(p):
    """{name or alias: place name} of the sketch map (示意图)."""
    out = {}
    for pl in (p.get('示意图') or {}).get('地方') or []:
        for n in [pl.get('名')] + list(pl.get('又名') or []):
            out.setdefault(n, pl.get('名'))
    return out


def framed(text, names):
    """The place a shot or an objective names, as flowview matches it (the longest name or alias it contains)."""
    hits = [n for n in names if n and n in str(text)]
    return names[max(hits, key=len)] if hits else None


def check_sketch(path, p):
    """The sketch map: every place well formed and opening in a segment that exists, the roads and the route
    between places it has, no name or alias given to two places."""
    sk, out = p.get('示意图') or {}, []
    segs = {s.get('名') for s in p.get('段') or []}
    seen = {}
    out += flowmap.problems(p, path.name)
    mod = flowmap.load(sk['地图']) if sk.get('地图') else None
    grid = flowmap.grid_of(mod) if mod else GRID      # a real map is drawn 100 wide, as tall as its shape
    for pl in sk.get('地方') or []:
        name = pl.get('名')
        where = f'{path.name} 示意图/{name}'
        real = sk.get('地图') and ('块' in pl or '点' in pl)      # placed by the map (flowmap), not the grid
        for key, size in () if real else (('位', grid), ('大', grid)):
            v = pl.get(key)
            if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) and 0 <= x <= m
                                                                 for x, m in zip(v, size))):
                out.append(f'{where}: {key} must be [x, y] within the {grid[0]}x{grid[1]} grid, got {v}')
        if pl.get('用途') not in USES:
            out.append(f'{where}: 用途 {pl.get("用途")} is not one of {"/".join(USES)}')
        if pl.get('开') not in segs:
            out.append(f'{where}: 开 {pl.get("开")} is not a segment of this level ({"/".join(map(str, segs))})')
        for n in [name] + list(pl.get('又名') or []):
            if n in seen and seen[n] != name:
                out.append(f'{where}: {n} also names {seen[n]} -- the map could not tell which one is meant')
            seen[n] = name
    names = {pl.get('名') for pl in sk.get('地方') or []}
    for i, road in enumerate(sk.get('路') or []):
        for n in road:
            if n not in names:
                out.append(f'{path.name} 示意图/路[{i}]: {n} is not a place of the sketch')
    for n in [] if sk.get('地图') else sk.get('路线') or []:      # on a real map flowmap checks it (sites too)
        if n not in names:
            out.append(f'{path.name} 示意图/路线: {n} is not a place of the sketch')
    return out


def unframed(path):
    """Shots (看) and objectives (题) that name no place of the sketch: the minimap frames nothing for them. Not a
    problem by itself (a shot of the convoy, "百合子必须活着"), listed for the writer to look over."""
    p = plan_of(path) or {}
    names = places(p)
    out = []
    for seg in p.get('段') or []:
        for shot in seg.get('镜头') or []:
            if not framed(shot.get('看'), names):
                out.append(f'镜头 {shot.get("看")}')
        for g in seg.get('目标') or []:
            if not framed(g.get('题'), names):
                out.append(f'目标 {g.get("题")}')
    return out


RETAIL_EVA = VOICE_GLOSSARY.parent / 'eva.csv'
EVA_PREFIX = {'盟军': 'Aeva_', '苏联': 'Seva_', '帝国': 'Ieva_'}


def retail_eva():
    """{side: {retail EVA line without punctuation: (asset, the line)}} from the voice line's eva.csv; None when the
    voice repo is not next to this one. The voice tools match a line only word for word (punctuation aside)."""
    if not RETAIL_EVA.exists():
        return None
    import csv
    out = {side: {} for side in EVA_PREFIX}
    with RETAIL_EVA.open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            for side, pre in EVA_PREFIX.items():
                if row['asset'].startswith(pre) and row.get('zh'):
                    out[side].setdefault(PUNCT.sub('', row['zh']), (row['asset'], row['zh']))
    return out


def new_eva(path, eva):
    """播报 lines that are not a retail line of the level's side word for word (README rule 10): each needs a new
    recording, with the closest retail line to compare. Not a problem by itself (冰墙已就位 has no retail line)."""
    import difflib
    p = plan_of(path) or {}
    lines = (eva or {}).get(p.get('阵营')) or {}
    out = []
    for _, who, text in lines_in(p, path.name):
        if who != '播报' or not isinstance(text, str) or PUNCT.sub('', text) in lines:
            continue
        near = difflib.get_close_matches(PUNCT.sub('', text), list(lines), n=1, cutoff=0.5)
        out.append(text + (f'（最接近的原版：{lines[near[0]][1]}）' if near else ''))
    return sorted(set(out))


def unverified(path, mech):
    """The 待验证 mechanics a flow script promises: what layer 3 has to test first."""
    p = plan_of(path) or {}
    return [k for k in p.get('用到的机制') or [] if mech.get(k, ('',))[0] == '待验证']


def main(names):
    sys.stdout.reconfigure(encoding='utf-8')
    speak, retail = cast()
    paths = [HERE / f'{n.lower()}.md' for n in names] if names else sorted(
        q for q in HERE.glob('*.md') if q.name not in NOT_SCRIPTS)
    units, mech, eva = unit_names(), mechanics(), retail_eva()
    problems =[x for q in paths for x in check(q, speak, retail, units, mech)]
    for x in problems:
        print(x)
    for q in paths:
        if u := unverified(q, mech):
            print(f'{q.name}: promises mechanics not yet tested (layer 3 tests these first): {", ".join(u)}')
        if u := new_eva(q, eva):
            print(f'{q.name}: 播报 lines the voice line records new (not retail word for word): {"; ".join(u)}')
        if u := unframed(q):
            print(f'{q.name}: the minimap frames no place for (look over): {"; ".join(u)}')
        p = plan_of(q) or {}
        if p.get('位置') in FLOOR:
            have, floor = scale(p), FLOOR[p['位置']]
            print(f'{q.name}: {p["位置"]} scale (P31) ' + ', '.join(f'{MEASURE[k]} {have[k]}/{floor[k]}' for k in floor))
    if units is None:
        print(f'unit names not checked: {VOICE_GLOSSARY} is missing')
    print(f'{len(paths)} flow scripts, {len(problems)} problems')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
