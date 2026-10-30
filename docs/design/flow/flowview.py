"""Turns the flow scripts into one page to look at, work/flowview/flow.html: each level played through as the player
meets it (briefing, shots, lines, objectives, the on-screen text, what is said when the player is stuck), the user's
five review points one by one (story and people, the map's empty ground by segment, the ways through, the surprise,
the backup), and the whole level on one sheet, flowcheck's problems on top. Reads only -- the scripts stay the
authority (ADR 0008).

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
    data = json.dumps(dict(levels=levels, cast=cast_rows(), cell=fc.flowmap.CELL, emptyLast=fc.EMPTY_LAST),
                      ensure_ascii=False, default=str).replace('</', '<\\/')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(TEMPLATE.read_text(encoding='utf-8').replace('/*DATA*/null', data), encoding='utf-8')
    print(f'{len(levels)} levels -> {OUT}')


if __name__ == '__main__':
    main(sys.argv[1:])
