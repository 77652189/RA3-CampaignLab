"""Checks the map content scripts (docs/design/maps/<level>.md, layer 2) for completeness and consistency only -- whether
a level's places look right is the user's call (ADR 0008). What it checks is listed in README.md section 4; at the end
it lists what the map line, the level line and the art have to make.

    python docs/design/maps/mapcheck.py            # every map content script
    python docs/design/maps/mapcheck.py a4         # some of them

Prints one line per problem and exits 1 if there is any.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
FLOW = HERE.parent / 'flow'
sys.path.insert(0, str(FLOW))
import flowcheck as fc          # noqa: E402  -- the flow scripts' reader, and flowmap through it
import flowmap                  # noqa: E402

TOP = ('关', '地图', '场所', '方向', '地标', '段')
STATES = ('有', '要改', '要加', '关卡摆', '美术')
WHO = {'要改': '地图线', '要加': '地图线', '关卡摆': '关卡线', '美术': '美术'}


def plan_of(path):
    return fc.plan_of(path)


def wheres(v):
    """An entry's 在: one site or block, or a list of them."""
    return [] if v is None else [v] if isinstance(v, str) else list(v)


def items(p):
    """Every landmark, set piece and terrain need of the script: (where in the script, entry, kind)."""
    for lm in p.get('地标') or []:
        yield f'地标/{lm.get("名")}', lm, '地标'
    for s in p.get('段') or []:
        for kind in ('布景', '地形'):
            for e in s.get(kind) or []:
                yield f'段 {s.get("段")}/{kind}/{e.get("什么") or e.get("要")}', e, kind


def check(path):
    p = plan_of(path)
    n = path.name
    if not isinstance(p, dict):
        return [f'{n}: no yaml block'], []
    out = [f'{n}: missing {k}' for k in TOP if p.get(k) in (None, '', [], {})]
    flow_path = FLOW / path.name
    flow = fc.plan_of(flow_path) if flow_path.exists() else None
    if str(p.get('关', '')).lower() != path.stem.lower():
        out.append(f'{n}: 关 {p.get("关")} does not match the file name')
    if not isinstance(flow, dict):
        return out + [f'{n}: no flow script flow/{path.name} -- layer 2 follows the flow script'], []
    if p.get('地图') != (flow.get('示意图') or {}).get('地图'):
        out.append(f'{n}: 地图 {p.get("地图")} is not the flow script\'s map {(flow.get("示意图") or {}).get("地图")}')
    mod = flowmap.load(p['地图']) if p.get('地图') else None
    if p.get('地图') and mod is None:
        out.append(f'{n}: no map module experimental/cnv/maps/{p["地图"]}.py')
    known = set(mod.SITES) | {b.what for b in getattr(mod.LAYOUT, 'blocks', [])} if mod else set()

    flow_segs = [s.get('名') for s in flow.get('段') or []]
    verbs = {s.get('名') for s in flow.get('段') or [] if s.get('动词')}
    opens = {pl.get('名'): pl.get('开') for pl in (flow.get('示意图') or {}).get('地方') or []}
    segs = [s.get('段') for s in p.get('段') or []]
    for s in flow_segs:
        if s not in segs:
            out.append(f'{n}: flow segment {s} has no entry in 段')
    for s in p.get('段') or []:
        name = f'{n} 段 {s.get("段")}'
        if s.get('段') not in flow_segs:
            out.append(f'{name}: not a segment of the flow script ({"/".join(flow_segs)})')
            continue
        if not s.get('第一眼'):
            out.append(f'{name}: missing 第一眼 (rule 1)')
        if not s.get('布景'):
            out.append(f'{name}: no 布景 -- at least one set piece that tells what happened here (rule 3)')
        if s['段'] in verbs and not s.get('地形'):
            out.append(f'{name}: the flow gives this segment a verb, so it needs at least one 地形 (rule 4)')
        at = flow_segs.index(s['段'])
        for pl in s.get('场所') or []:
            if pl not in opens:
                out.append(f'{name}/场所: {pl} is not a place of the flow sketch')
            elif s['段'] in verbs and opens[pl] in flow_segs and flow_segs.index(opens[pl]) > at:
                # a cutscene may show what opens next (P21: a look at the bigger map first); play happens where it is open
                out.append(f'{name}/场所: {pl} opens only in {opens[pl]}')
        if not s.get('场所'):
            out.append(f'{name}: missing 场所')

    todo = []
    for where, e, kind in items(p):
        for k in ('名', '是什么', '作用') if kind == '地标' else ('什么', '讲什么') if kind == '布景' else ('要', '为了'):
            if not e.get(k):
                out.append(f'{n} {where}: missing {k}')
        if e.get('地图') not in STATES:
            out.append(f'{n} {where}: 地图 {e.get("地图")} is not one of {"/".join(STATES)}')
        elif e['地图'] in WHO:
            todo.append((WHO[e['地图']], e['地图'], where))
        for w in wheres(e.get('在')):
            if mod is not None and w not in known:
                out.append(f'{n} {where}: 在 {w} is neither a site nor a block of {p["地图"]}')
        if not e.get('在'):
            out.append(f'{n} {where}: missing 在')
    return out, todo


def unseen(path):
    """Landmarks whose name the flow script never says: the player will not use them to find the way (rule 2)."""
    p, flow = plan_of(path) or {}, fc.plan_of(FLOW / path.name) or {}
    text = '\n'.join(fc.all_text(flow))
    return [lm.get('名') for lm in p.get('地标') or [] if lm.get('名') and lm['名'] not in text]


def main(names):
    sys.stdout.reconfigure(encoding='utf-8')
    paths = [HERE / f'{x.lower()}.md' for x in names] if names else sorted(
        q for q in HERE.glob('*.md') if q.name != 'README.md')
    problems, todo = [], []
    for q in paths:
        bad, t = check(q)
        problems += bad
        todo += [(who, state, f'{q.stem.upper()} {where}') for who, state, where in t]
    for x in problems:
        print(x)
    for q in paths:
        if u := unseen(q):
            print(f'{q.name}: landmarks the flow script never names (look over): {", ".join(u)}')
    for who in ('地图线', '关卡线', '美术'):
        mine = [f'{where}（{state}）' for w, state, where in todo if w == who]
        if mine:
            print(f'给{who}：' + '；'.join(mine))
    print(f'{len(paths)} map content scripts, {len(problems)} problems')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
