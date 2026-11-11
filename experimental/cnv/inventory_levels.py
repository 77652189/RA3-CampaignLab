r"""Our 9 levels' share of the retail feature inventory, engine A's parts (ADR 0026 stop condition 1: every item our
levels use is 已对拍). Generated, never written by hand, into docs/engine/inventory-levels-a.md; the AI part (engine
B's) is inventory_ai.py levels -> inventory-levels.md. States and uses come from inventory.collect().

What a level uses, statically (all it could run, not one playthrough):
  脚本动作 / 脚本条件  every action / condition of the scripts as built (parts.merged: objective reveals included),
                    actions refined the inventory's way (simcoverage.refined: a status bit, a power, a button)
  物体模块          the effective modules (inheritance, includes and id overrides resolved, as retailmodules) of the
                    templates the level has: placed on the map or by the mission, our own units (their XML; a parent
                    from the retail data), a template a script names -- and what those reach: a module word naming a
                    weapon, a weapon word naming an object (its projectile) or a weapon (reach()). Not followed: object creation
                    lists (death debris, OCL powers) and command sets (what a factory could build).
  武器效果          the Nugget types of the weapons reached that way (a weapon's own nuggets after its parents')

  python -I -X utf8 experimental/cnv/inventory_levels.py            print the summary
  python -I -X utf8 experimental/cnv/inventory_levels.py --write    regenerate docs/engine/inventory-levels-a.md
"""
import collections
import importlib
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import retailmodules as rm                       # noqa: E402

LEVELS = [f'a{k}' for k in range(1, 10)]         # the Allied 9 (missions/a1.py ...), as inventory_ai.LEVELS
OUT = os.path.join(ROOT, 'docs', 'engine', 'inventory-levels-a.md')
ACTION, CONDITION, MODULE, NUGGET = '脚本动作', '脚本条件', '物体模块', '武器效果'
PARTS = (ACTION, CONDITION, MODULE, NUGGET)
BENCHED, GUESSED, TODO, NA = '已对拍', '推断', '未做', '不涉及'


# ---- the object and weapon tables, with the words each one's data holds
def _words(el):
    return {w.split(':')[-1].lower() for d in el.iter() for v in d.attrib.values() for w in v.split()} | \
        {w.lower() for d in el.iter() for w in (d.text or '').split()}


def _read(root, path, objs, weapons, override=False):
    """Add a file's GameObjects ({lower id: (id, {group: [(type, module id, words)]}, parent)}) and WeaponTemplates
    ({lower id: (id, nugget types, words, parent)}); with override, an id already there is kept (CampaignOverrides,
    as retailmodules)."""
    for e in root.iter():
        t = rm._tag(e)
        if t == 'GameObject' and e.get('id'):
            k = e.get('id').lower()
            if override and k in objs:
                continue
            own = {}
            for g in e:
                if rm._tag(g) in rm.GROUPS:
                    own.setdefault(rm._tag(g), []).extend(
                        (rm._tag(m), m.get('id') or m.get('ID') or '', _words(m)) for m in rm._group_modules(path, g))
            objs[k] = (e.get('id'), own, (e.get('inheritFrom') or '').lower() or None)
        elif t == 'WeaponTemplate' and e.get('id'):
            k = e.get('id').lower()
            if override and k in weapons:
                continue
            nug = [rm._tag(n) for n in e.iter() if rm._tag(n).endswith('Nugget')]
            weapons[k] = (e.get('id'), nug, _words(e), (e.get('inheritFrom') or '').lower() or None)


_retail = None


def retail_tables():
    global _retail
    if _retail is None:
        rm._check_dirs()
        objs, weapons = {}, {}
        for r, _, fs in sorted(os.walk(rm.SAGEXML)):
            for f in sorted(fs):
                if not f.endswith('.xml'):
                    continue
                p = os.path.join(r, f)
                txt = open(p, encoding='utf-8', errors='replace').read()
                if '<GameObject' not in txt and '<WeaponTemplate' not in txt:
                    continue
                root = rm._parse(p)
                if root is not None:
                    _read(root, p, objs, weapons, override='CampaignOverrides' in p)
        _retail = objs, weapons
    return _retail


def own_tables(units):
    """Our units' GameObjects and weapons (their XML and extra files), over the retail tables."""
    objs, weapons = dict(retail_tables()[0]), dict(retail_tables()[1])
    fake = os.path.join(rm.SAGEXML, 'cnv_unit.xml')         # where a relative include would resolve from
    for u in units:
        for text in [u.xml] + [t for n, t in sorted(u.files.items()) if n.lower().endswith('.xml')]:
            try:
                root = ET.fromstring(text.encode('utf-8'))
            except ET.ParseError:
                continue
            _read(root, fake, objs, weapons)
    return objs, weapons


def effective(k, objs, seen=()):
    """[(group, type, module id, words)] in effect: the parent's first, a module with the same id replaced (retailmodules)."""
    if k not in objs or k in seen:
        return []
    _, own, parent = objs[k]
    mods = collections.defaultdict(list)
    for g, t, i, w in (effective(parent, objs, seen + (k,)) if parent else []):
        mods[g].append((t, i, w))
    for g, lst in own.items():
        cur = mods[g]
        for typ, mid, w in lst:
            n = next((n for n, (_, i2, _) in enumerate(cur) if mid and i2 == mid), None)
            if n is None:
                cur.append((typ, mid, w))
            else:
                cur[n] = (typ, mid, w)
    return [(g, t, i, w) for g in rm.GROUPS for (t, i, w) in mods.get(g, [])]


def nuggets(k, weapons, seen=()):
    if k not in weapons or k in seen:
        return []
    _, nug, _, parent = weapons[k]
    return (nuggets(parent, weapons, seen + (k,)) if parent else []) + nug


def weapon_words(k, weapons, seen=()):
    if k not in weapons or k in seen:
        return set()
    _, _, words, parent = weapons[k]
    return words | (weapon_words(parent, weapons, seen + (k,)) if parent else set())


def reach(seeds, objs, weapons):
    """(objects, weapons) reached from the seed template names (lower ids): an object's module words naming a weapon, a
    weapon's words naming an object (its projectile) or a weapon. An object's words naming another object are not
    followed: they are mostly what it could become or carry (the IFV's passengers, the Hammer's leeched vehicles)."""
    got_o, got_w, todo = set(), set(), [s.lower() for s in seeds]
    while todo:
        k = todo.pop()
        if k in objs and k not in got_o:
            got_o.add(k)
            todo += [w for _, _, _, words in effective(k, objs) for w in words if w in weapons]
        elif k in weapons and k not in got_w:
            got_w.add(k)
            todo += [w for w in weapon_words(k, weapons) if w in objs or w in weapons]
    return got_o, got_w


# ---- what each level uses
def level_uses(level):
    """{(part, name): set of example templates (modules, nuggets) or ()}, and the template names not found."""
    import parts
    import simcoverage
    m = importlib.import_module(f'missions.{level}').mission()
    mm = parts.merged(m)
    out = collections.defaultdict(set)
    named = set()
    for s in mm.scripts:
        for c in s.when:
            out[(CONDITION, c[0])]
            named |= {a for a in c[1:] if isinstance(a, str)}
        for a in s.do:
            out[(ACTION, simcoverage.refined(a[0], list(a[1:])))]
            named |= {x for x in a[1:] if isinstance(x, str)}
    objs, weapons = own_tables(mm.units)
    placed = {o.template for o in list(getattr(m.map, 'OBJECTS', [])) + list(mm.objects)} | {u.id for u in mm.units}
    seeds = placed | {n for n in named if n.lower() in objs}
    got_o, got_w = reach(seeds, objs, weapons)
    for k in sorted(got_o):
        for g, t, _, _ in effective(k, objs):
            out[(MODULE, f'{g}/{t}')].add(objs[k][0])
    for k in sorted(got_w):
        for t in set(nuggets(k, weapons)):
            out[(NUGGET, t)].add(weapons[k][0])
    missing = sorted(t for t in placed if t.lower() not in objs)
    return out, missing


def level_scope(levels=LEVELS):
    """{(part, name): {level: examples}}, {level: templates not in the data}."""
    scope, missing = collections.defaultdict(dict), {}
    for lv in levels:
        uses, missing[lv] = level_uses(lv)
        for key, eg in uses.items():
            scope[key][lv] = eg
    return scope, missing


def render(items, scope, missing):
    # Field-form partitions carry exact retail weapon membership. Attribute each
    # reached weapon once; unknown/custom weapons conservatively keep the TODO base.
    split = collections.defaultdict(dict)
    for it in items:
        if it['part'] == NUGGET and 'weapon_ids' in it:
            for w in it['weapon_ids']:
                split[it['name'].split(':')[0]][w.lower()] = it['name']
    expanded = collections.defaultdict(lambda: collections.defaultdict(set))
    for (part, name), lvs in scope.items():
        if part == NUGGET and name in split:
            for lv, examples in lvs.items():
                for w in examples:
                    expanded[(part, split[name].get(w.lower(), name))][lv].add(w)
        else:
            for lv, examples in lvs.items():
                expanded[(part, name)][lv].update(examples)
    scope = expanded
    by = {(i['part'], i['name']): i for i in items}
    rows, unknown = [], []
    for (part, name), lvs in scope.items():
        it = by.get((part, name))
        if it is None and part == NUGGET and name in split:
            # All retail forms can be measured while a custom weapon is not.
            # Keep its TODO row; it adds no retail uses to the weighted total.
            it = dict(part=part, name=name, uses=0, state=TODO,
                      why='未覆盖的自制或未知武器写法；原版字段分片另行登记')
        if it is None:
            unknown.append((part, name, sorted(lvs)))
            continue
        eg = sorted({e for v in lvs.values() for e in v})
        rows.append((it, sorted(lvs, key=LEVELS.index), eg))
    order = {TODO: 0, GUESSED: 1, BENCHED: 3, NA: 4}
    rows.sort(key=lambda r: (order[r[0]['state']], PARTS.index(r[0]['part']), -r[0]['uses'], r[0]['name']))
    live = [r for r in rows if r[0]['state'] != NA]
    count = collections.Counter((r[0]['part'], r[0]['state']) for r in live)
    done = sum(r[0]['state'] == BENCHED for r in live)
    total = sum(r[0]['uses'] for r in live) or 1
    pct = lambda states: round(100 * sum(r[0]['uses'] for r in live if r[0]['state'] in states) / total)  # noqa: E731
    lines = ['# 我们 9 关用到的脚本、物体模块、武器效果（引擎 A 部分）', '',
             '由 `experimental/cnv/inventory_levels.py --write` 生成，**别手改**。范围：9 关（`missions/a1.py`～`a9.py`）'
             '编出的全部脚本（`parts.merged`，含目标显示脚本）里的动作和条件；地图和任务摆的物体、我们自己的单位、脚本点名'
             '的模板，连同模块点名的武器、武器点名的物体（抛射体）和武器，取生效的模块（继承、include、同 id 覆盖）和武器'
             '效果。没跟：模块点名的别的物体（多是能变成 / 能装的东西：多功能步兵车的乘客、锤子坦克吸来的车）、物体生成表'
             '（死亡碎片、OCL 技能）和命令表（工厂能造什么）。AI 部分（引擎 B）在 '
             '[inventory-levels.md](inventory-levels.md)。状态和原版用量取自 [inventory.md](inventory.md)。'
             '停止条件①：下表全部已对拍。', '',
             f'**已对拍 {done} / {len(live)}**（不涉及的不算）。', '',
             '| 部分 | 已对拍 | 推断 | 未做 | 不涉及 |', '|---|---|---|---|---|']
    lines += [f'| {p} | {count[(p, BENCHED)]} | {count[(p, GUESSED)]} | {count[(p, TODO)]} | '
              f'{sum(r[0]["part"] == p and r[0]["state"] == NA for r in rows)} |' for p in PARTS]
    lines += ['', f'按原版用量加权：已对拍 {pct({BENCHED})}%，已有（已对拍+推断）{pct({BENCHED, GUESSED})}%。']
    gone = {lv: t for lv, t in missing.items() if t}
    if gone:
        lines += ['', '摆了、但原版数据和我们的单位里都找不到的模板（模块没算）：'
                  + '；'.join(f'{lv} ' + '、'.join(f'`{t}`' for t in ts) for lv, ts in gone.items()) + '。']
    if unknown:
        lines += ['', '编出的脚本里有、清单里没有的名字（不算）：'
                  + '、'.join(f'`{n}`' for _, n, _ in sorted(unknown)) + '。']
    lines += ['', '| 状态 | 部分 | 项 | 原版用量 | 关 | 说明 |', '|---|---|---|---|---|---|']
    for it, lvs, eg in rows:
        why = it['why'] + (f'；例：{", ".join(eg[:2])}' if eg else '')
        lines.append(f'| {it["state"]} | {it["part"]} | `{it["name"]}` | {it["uses"]} | {" ".join(lvs)} | {why} |')
    return '\n'.join(lines) + '\n'


def main(write=False):
    import inventory
    items = [i for i in inventory.collect() if i['part'] in PARTS]
    scope, missing = level_scope()
    text = render(items, scope, missing)
    if write:
        with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    print('\n'.join(text.splitlines()[4:14]))
    return text


if __name__ == '__main__':
    main(write='--write' in sys.argv)
