"""Turns the flow scripts into one page to look at, work/flowview/flow.html: each level played through as the player
meets it (briefing, shots, lines, objectives, the on-screen text, what is said when the player is stuck), the user's
five review points one by one (story and people, the map's empty ground by segment, the ways through, the surprise,
the backup), and the whole level on one sheet, flowcheck's problems on top. Reads only -- the scripts stay the
authority (ADR 0008).

    python docs/design/flow/flowview.py            # every flow script
    python docs/design/flow/flowview.py a4 j7      # some of them
"""
import os
import html
import json
import re
import subprocess
import sys
from pathlib import Path

import flowcheck as fc
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'experimental', 'campaign')))
import labpaths  # noqa: E402

TEMPLATE = fc.HERE / 'flowview.html'
OUT = Path(labpaths.WORK) / 'flowview' / 'flow.html'
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


MAPS = fc.HERE.parent / 'maps'           # the map content scripts (layer 2), docs/design/maps/<level>.md


def content(q, sketch):
    """The level's map content script (layer 2) with every 在 drawn as boxes on the sketch's map, and mapcheck's
    problems; None when the level has none yet."""
    path = MAPS / q.name
    if not path.exists() or not sketch.get('地图'):
        return None
    sys.path.insert(0, str(MAPS))
    import mapcheck
    p = mapcheck.plan_of(path) or {}
    mod = fc.flowmap.load(sketch['地图'])
    blocks = {b.what for b in getattr(mod.LAYOUT, 'blocks', [])} if mod else set()
    tf = fc.flowmap._tf(mod) if mod else None

    def boxes(v):
        out = []
        for w in mapcheck.wheres(v):
            box = fc.flowmap._world_box(mod, {'块': w} if w in blocks else {'点': w}) if mod else None
            if box:
                (ax, ay), (bx, by) = tf(box[0], box[3]), tf(box[2], box[1])
                out.append([round(ax, 1), round(ay, 1), round(bx - ax, 1), round(by - ay, 1)])
        return out
    for lm in p.get('地标') or []:
        lm['框'] = boxes(lm.get('在'))
    for s in p.get('段') or []:
        for kind in ('布景', '地形'):
            for e in s.get(kind) or []:
                e['框'] = boxes(e.get('在'))
    problems, todo = mapcheck.check(path)
    return dict(plan=p, problems=problems, todo=todo, unseen=mapcheck.unseen(path))


# ---- the 大纲 tab: docs/story/outline.md and each level's chosen card (甲), via a small markdown converter ----
ROOT = fc.HERE.parents[2]
CARDS = fc.HERE.parent / 'cards'
ITEM = re.compile(r'^(\s*)([-*]|\d+\.)\s+(.*)$')


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]*)\)', r'<span class="lnk" title="\2">\1</span>', t)
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)


def cells(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def md_table(rows):
    body = [cells(r) for r in rows if not re.match(r'^\s*\|[\s:|-]+\|\s*$', r)]
    head, body = body[0], body[1:]
    return ('<div class="wrapx"><table><thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in head) + '</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>' for r in body) + '</tbody></table></div>')


def md_list(items):
    stack, h = [], ''
    for ind, tag, tx in items:
        while stack and stack[-1][0] > ind:
            h += f'</li></{stack.pop()[1]}>'
        if stack and stack[-1][0] == ind:
            h += '</li>'
        else:
            stack.append((ind, tag))
            h += f'<{tag}>'
        h += f'<li>{inline(tx)}'
    while stack:
        h += f'</li></{stack.pop()[1]}>'
    return h


def md_html(text, base=1):
    """# headings (shifted to h{base}), paragraphs, -/1. lists with nesting, | tables |, **bold**, `code`, links as text."""
    out, lines, i = [], text.split('\n'), 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r'^(#{1,6})\s+(.*)$', ln)
        if not ln.strip():
            i += 1
        elif m:
            n = min(len(m.group(1)) + base - 1, 6)
            out.append(f'<h{n}>{inline(m.group(2))}</h{n}>')
            i += 1
        elif ln.lstrip().startswith('|'):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith('|'):
                rows.append(lines[i])
                i += 1
            out.append(md_table(rows))
        elif ITEM.match(ln):
            items = []
            while i < len(lines) and lines[i].strip() and (ITEM.match(lines[i]) or lines[i].startswith(' ')):
                m = ITEM.match(lines[i])
                if m:
                    items.append([len(m.group(1)), 'ol' if m.group(2)[0].isdigit() else 'ul', m.group(3)])
                else:
                    items[-1][2] += ' ' + lines[i].strip()
                i += 1
            out.append(md_list(items))
        else:
            par = []
            while i < len(lines) and lines[i].strip() and not re.match(r'^(#{1,6}\s|\s*\|)', lines[i]) and not ITEM.match(lines[i]):
                par.append(lines[i].strip().lstrip('> '))
                i += 1
            out.append('<p>' + '<br>'.join(inline(x) for x in par) + '</p>')
    return '\n'.join(out)


def git_date(path):
    r = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', str(path)], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    return r.stdout.strip()


ALL_LEVELS = [f'{side}{n}' for side in 'ASJ' for n in range(1, 10)]     # campaign order, with a flow script or not
ALL_CARDS = CARDS / 'all.md'        # one card a level (2026-11-01); A4, S1, J7 keep their own file and pick ## 甲


def outline_data():
    cards = []
    every = ALL_CARDS.read_text(encoding='utf-8') if ALL_CARDS.exists() else ''
    for lid in ALL_LEVELS:
        card, flow = CARDS / f'{lid.lower()}.md', fc.HERE / f'{lid.lower()}.md'
        own = card.exists()
        if own:
            txt = card.read_text(encoding='utf-8')
            title = re.search(r'^# (.+)$', txt, re.M)
            sec = re.search(r'^## 甲.*?(?=^## |\Z)', txt, re.M | re.S)
        else:
            card = ALL_CARDS
            title = re.search(rf'^### ({lid} .+)$', every, re.M)
            sec = re.search(rf'^### {lid} .*?\n(.*?)(?=^##|\Z)', every, re.M | re.S)
        if not sec:
            continue
        first = re.search(r'^\*\*(2026-\d\d-\d\d)', flow.read_text(encoding='utf-8'), re.M) if flow.exists() else None
        cd, fd = git_date(card), (git_date(flow) if flow.exists() else '')
        cards.append(dict(id=lid, title=title.group(1) if title else lid,
                          html=md_html(sec.group(0) if own else sec.group(1), 3),
                          cardDate=cd, flowDate=fd, flowFirst=first.group(1) if first else '', hasFlow=flow.exists(),
                          stale=bool(own and flow.exists() and fd and cd and fd < cd)))
    return dict(html=md_html((ROOT / 'docs' / 'story' / 'outline.md').read_text(encoding='utf-8'), 1), cards=cards)


def main(names):
    sys.stdout.reconfigure(encoding='utf-8')
    speak, retail = fc.cast()
    units, mech = fc.unit_names(), fc.mechanics()
    paths = [fc.HERE / f'{n.lower()}.md' for n in names] if names else sorted(
        q for q in fc.HERE.glob('*.md') if q.name not in fc.NOT_SCRIPTS)
    levels = []
    for q in paths:
        plan = fc.plan_of(q)
        if not isinstance(plan, dict):
            continue
        problems = fc.check(q, speak, retail, units, mech)
        empty, scene = {}, None
        if plan.get('示意图'):
            sketch = fc.flowmap.drawn(plan)                      # the real map's ground, places and borders
            empty = fc.flowmap.empty(plan, sketch)               # each segment's empty ground (README rule 17)
            scene = content(q, sketch)                           # layer 2, where it is written
            plan = dict(plan, 示意图=sketch)
        levels.append(dict(id=q.stem.upper(), plan=plan, problems=problems, empty=empty, scene=scene,
                           minutes=[minutes(s.get('时长')) for s in plan.get('段') or []]))
    data = json.dumps(dict(levels=levels, cast=cast_rows(), cell=fc.flowmap.CELL, emptyLast=fc.EMPTY_LAST,
                           outline=outline_data()),
                      ensure_ascii=False, default=str).replace('</', '<\\/')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(TEMPLATE.read_text(encoding='utf-8').replace('/*DATA*/null', data), encoding='utf-8')
    print(f'{len(levels)} levels -> {OUT}')


if __name__ == '__main__':
    main(sys.argv[1:])
