"""Turns the flow scripts into one page to look at, work/flowview/flow.html: each level played through as the player
meets it (briefing, shots, lines, objectives, the on-screen text, what is said when the player is stuck) and the whole
level on one sheet, flowcheck's problems on top. Reads only -- the scripts stay the authority (ADR 0008).

    python docs/design/flow/flowview.py            # every flow script
    python docs/design/flow/flowview.py a4 j7      # some of them
"""
import json
import re
import sys

import flowcheck as fc

TEMPLATE = fc.HERE / 'flowview.html'
OUT = fc.HERE.parents[2] / 'work' / 'flowview' / 'flow.html'
CN = dict(zip('一二两三四五六七八九', (1, 2, 2, 3, 4, 5, 6, 7, 8, 9)))


def cast_rows():
    """key -> (name, side) from cast.md; the retail-only table's side is '原版'."""
    rows, part = {}, None
    for line in (fc.HERE / 'cast.md').read_text(encoding='utf-8').splitlines():
        if line.startswith('## '):
            part = 'new' if '新台词' in line else 'retail' if '原版' in line else None
        elif part and line.startswith('| ') and not line.startswith('| 键') and '---' not in line:
            cells = [c.strip() for c in line.split('|')[1:-1]]
            rows[cells[0]] = (cells[1], cells[2]) if part == 'new' else (cells[0], '原版')
    return rows


def number(s):
    if re.fullmatch(r'[0-9.]+', s):
        return float(s)
    if '十' in s:
        a, _, b = s.partition('十')
        return CN.get(a, 1) * 10 + CN.get(b, 0)
    return float(CN.get(s, 0))


def minutes(text):
    """The first length in a segment's 时长 ("约 3 分钟", "约 15 秒", "一分半到半分钟"), in minutes; None if none."""
    m = re.search(r'([0-9.]+|[一二两三四五六七八九十]+)\s*(分钟|分|秒)(半)?', str(text or ''))
    if not m:
        return None
    n = number(m.group(1)) + (0.5 if m.group(3) else 0)
    return n / 60 if m.group(2) == '秒' else n


def main(names):
    sys.stdout.reconfigure(encoding='utf-8')
    speak, retail = fc.cast()
    units, mech = fc.unit_names(), fc.mechanics()
    paths = [fc.HERE / f'{n.lower()}.md' for n in names] if names else sorted(
        q for q in fc.HERE.glob('*.md') if q.name not in ('README.md', 'cast.md'))
    levels = []
    for q in paths:
        plan = fc.plan_of(q)
        if not isinstance(plan, dict):
            continue
        problems = fc.check(q, speak, retail, units, mech)
        if plan.get('示意图'):
            plan = dict(plan, 示意图=fc.flowmap.drawn(plan))      # the real map's ground, places and borders
        levels.append(dict(id=q.stem.upper(), plan=plan, problems=problems,
                           minutes=[minutes(s.get('时长')) for s in plan.get('段') or []]))
    data = json.dumps(dict(levels=levels, cast=cast_rows()), ensure_ascii=False, default=str).replace('</', '<\\/')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(TEMPLATE.read_text(encoding='utf-8').replace('/*DATA*/null', data), encoding='utf-8')
    print(f'{len(levels)} levels -> {OUT}')


if __name__ == '__main__':
    main(sys.argv[1:])
