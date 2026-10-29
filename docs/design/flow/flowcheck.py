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

HERE = pathlib.Path(__file__).resolve().parent
TOP = ('关', '关名', '阵营', '类型', '地点', '新东西', '出场单位', '一句话', '体验目标', '取舍', '张力', '接上一关',
       '引出下一关', '简报', '段', '胜利', '失败')
TYPES = ('护送', '突击', '基地对抗', '守', '潜入', '海战', '限时', '打自己人')
GOAL_KINDS = ('主', '奖励')
# voice-script rules (RA3-ChineseVoice lines/GLOSSARY.md): no digits, no Latin letters, no brackets
BAD_IN_LINE = re.compile(r'[0-9A-Za-z()（）\[\]【】]')


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


def check(path, speak, retail, units=None):
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
    if units is not None:
        for side, names in (p.get('出场单位') or {}).items():
            for n in names or []:
                if n not in units:
                    out.append(f'{path.name} 出场单位/{side}: {n} is in neither the voice glossary, outline.md '
                               f'section 3 nor the plan glossary')
    return out


def main(names):
    sys.stdout.reconfigure(encoding='utf-8')
    speak, retail = cast()
    paths = [HERE / f'{n.lower()}.md' for n in names] if names else sorted(
        q for q in HERE.glob('*.md') if q.name not in ('README.md', 'cast.md'))
    units = unit_names()
    problems = [x for q in paths for x in check(q, speak, retail, units)]
    for x in problems:
        print(x)
    if units is None:
        print(f'unit names not checked: {VOICE_GLOSSARY} is missing')
    print(f'{len(paths)} flow scripts, {len(problems)} problems')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
