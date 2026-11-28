r"""Our 9 levels' share of the retail feature inventory, engine A's parts (ADR 0026 stop condition 1: every item our
levels use is 已对拍). Generated on demand into docs/engine/inventory-levels-a.md (not committed: ADR 0030); the AI part (engine
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
  python -I -X utf8 experimental/cnv/inventory_levels.py --write    generate docs/engine/inventory-levels-a.md
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
from contain_audit import signature              # noqa: E402

LEVELS = [f'a{k}' for k in range(1, 10)]         # the Allied 9 (missions/a1.py ...), as inventory_ai.LEVELS
OUT = os.path.join(ROOT, 'docs', 'engine', 'inventory-levels-a.md')
ACTION, CONDITION, MODULE, NUGGET = '脚本动作', '脚本条件', '物体模块', '武器效果'
WEAPON = 'WeaponTemplate'                       # retail_twin's group for a weapon's nuggets
PARTS = (ACTION, CONDITION, MODULE, NUGGET)
BENCHED, GUESSED, TODO, NA = '已对拍', '推断', '未做', '不涉及'
# reached in these levels, but nothing there makes it act (its owner's scripts, the AI, the player): (part, name) ->
# (levels, why); level_scope leaves those levels out, the page lists them. Retail use elsewhere keeps its state.
INERT = {
    (MODULE, 'Behaviors/SpiderHoleUpdate'): (('a4',), '坦克杀手归 AI 的具名脚本队伍，脚本不按入洞，微操不管（INFERRED，'
                                             'B 答 work/re/b1127_a419.md 第 1 节）'),
    (MODULE, 'Behaviors/PrematureDischargeSpecialPower'): (('a4',), 'AI 盖的高级防御塔落在不跑微操的默认队伍，脚本不按、'
                                                           '玩家占不了（INFERRED，同上第 2 节）'),
}
# our own features (retail never uses them, so the inventory has no item): (part, name) -> (state, why). Each one a level
# reaches is a 0-use row of the page (one not listed: 未做); a held reading's `item` makes it 已对拍 (apply_declared).
OWN = {
    (MODULE, 'Behaviors/TeleportSpecialAbilityUpdate'): (TODO, '自由号跳跃（engine/modules/teleport.py，engine_libjump）'),
    (ACTION, 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT:SpecialPower_CNV_ChronoDeck'): (TODO, '脚本让自由号跳（engine_libjump）'),
    (MODULE, 'Behaviors/TeleportToCasterSpecialPower'): (TODO, '信标拉回（specialpower.PullToCaster，engine_bcnpull）'),
    (ACTION, 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT:SpecialPower_CNV_IceEngineer_Freeze'): (GUESSED, '冰冻工程师走去造墙'
                                                                                          '（act_ability.script_cast）'),
    (ACTION, 'UNIT_CHANGE_OBJECT_STATUS:IMMOBILE'): (GUESSED, '状态位模拟器认（命令不动 IMMOBILE 的），没有自己的读数'),
}


# ---- the object and weapon tables, with the words each one's data holds
def _words(el):
    return {w.split(':')[-1].lower() for d in el.iter() for v in d.attrib.values() for w in v.split()} | \
        {w.lower() for d in el.iter() if rm._tag(d) != 'ExcludeThing' for w in (d.text or '').split()}


def _read(root, path, objs, weapons, override=False):
    """Add a file's GameObjects ({lower id: (id, {group: [(type, module id, words, signature)]}, parent)}) and WeaponTemplates
    ({lower id: (id, [(nugget type, signature)], words, parent)}); with override, an id already there is kept (CampaignOverrides,
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
                        (rm._tag(m), m.get('id') or m.get('ID') or '', _words(m), signature(m))
                        for m in rm._group_modules(path, g))
            objs[k] = (e.get('id'), own, (e.get('inheritFrom') or '').lower() or None)
        elif t == 'WeaponTemplate' and e.get('id'):
            k = e.get('id').lower()
            if override and k in weapons:
                continue
            nug = [(rm._tag(n), signature(n)) for n in e.iter() if rm._tag(n).endswith('Nugget')]
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
    """[(group, type, module id, words, signature)] in effect: the parent's first, a module with the same id replaced
    (retailmodules)."""
    if k not in objs or k in seen:
        return []
    _, own, parent = objs[k]
    mods = collections.defaultdict(list)
    for g, *mod in (effective(parent, objs, seen + (k,)) if parent else []):
        mods[g].append(tuple(mod))
    for g, lst in own.items():
        cur = mods[g]
        for mod in lst:
            n = next((n for n, old in enumerate(cur) if mod[1] and old[1] == mod[1]), None)
            if n is None:
                cur.append(mod)
            else:
                cur[n] = mod
    return [(g, *mod) for g in rm.GROUPS for mod in mods.get(g, [])]


def by_type(mods):
    """{(group, type): sorted signatures}: an effective() list's modules of each type, all of them."""
    out = collections.defaultdict(list)
    for g, t, _, _, sig in mods:
        out[(g, t)].append(sig)
    return {k: tuple(sorted(v)) for k, v in out.items()}


_twins = None


def retail_twin(name, group, typ, sigs):
    """A retail template whose effective modules of this type are exactly these (the one our template `name` is
    named after when it is one of them), or None. Our copy of a retail structure (units/unsellable.py, a mission's
    renamed barracks) carries that retail config, and the inventory's per-config forms (contain_audit) are exact
    module signatures, so the copy counts under the retail name. Weapons the same way, group WEAPON and a nugget
    type: our copy of a retail weapon (the Chrono Lag's shell, the Liberty's drones) counts under the retail
    weapon's name, which the inventory's field forms list."""
    global _twins
    if _twins is None:
        objs, weapons = retail_tables()
        _twins = collections.defaultdict(list)
        for table, mods in ((objs, effective), (weapons, nugget_mods)):
            for k in sorted(table):
                for key, s in by_type(mods(k, table)).items():
                    _twins[key + (s,)].append(table[k][0])
    twins = _twins.get((group, typ, sigs), [])
    return next((t for t in twins if t.lower() in name.lower()), twins[0] if twins else None)


def nuggets(k, weapons, seen=(), sigs=False):
    """Weapon k's nugget types after its parents' ((type, signature) with sigs)."""
    if k not in weapons or k in seen:
        return []
    _, nug, _, parent = weapons[k]
    return (nuggets(parent, weapons, seen + (k,), sigs) if parent else []) + [n if sigs else n[0] for n in nug]


def nugget_mods(k, weapons):
    """Weapon k's nuggets shaped as effective() modules (group WEAPON), for by_type()."""
    return [(WEAPON, t, '', (), s) for t, s in nuggets(k, weapons, sigs=True)]


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
            todo += [w for _, _, _, words, _ in effective(k, objs) for w in words if w in weapons]
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
    retail, retail_weapons = retail_tables()
    for k in sorted(got_o):
        for (g, t), sigs in by_type(effective(k, objs)).items():
            twin = objs[k] is not retail.get(k) and retail_twin(objs[k][0], g, t, sigs)
            out[(MODULE, f'{g}/{t}')].add(twin or objs[k][0])
    for k in sorted(got_w):
        for (g, t), sigs in by_type(nugget_mods(k, weapons)).items():
            twin = weapons[k] is not retail_weapons.get(k) and retail_twin(weapons[k][0], g, t, sigs)
            out[(NUGGET, t)].add(twin or weapons[k][0])
    missing = sorted(t for t in placed if t.lower() not in objs)
    return out, missing


def level_scope(levels=LEVELS):
    """{(part, name): {level: examples}}, {level: templates not in the data}."""
    scope, missing = collections.defaultdict(dict), {}
    for lv in levels:
        uses, missing[lv] = level_uses(lv)
        for key, eg in uses.items():
            if lv not in INERT.get(key, ((),))[0]:
                scope[key][lv] = eg
    return scope, missing


def expand_forms(items, scope):
    """(scope, split): the scope with a nugget the inventory splits by field form (an item's weapon_ids) attributed
    to its forms' items, each reached weapon once; a weapon no form lists (our own, an unknown one) keeps the base
    name. Modules with template_ids are partitioned by exact template membership;
    unknown/custom templates keep the base gap. The returned split only contains
    {nugget type: {lower weapon id: form item name}}."""
    split = collections.defaultdict(dict)
    module_split = collections.defaultdict(dict)
    for it in items:
        if it['part'] == MODULE and 'template_ids' in it:
            for template in it['template_ids']:
                module_split[it['name'].split(':')[0]][template.lower()] = it['name']
        if it['part'] == NUGGET and 'weapon_ids' in it:
            for w in it['weapon_ids']:
                split[it['name'].split(':')[0]][w.lower()] = it['name']
    expanded = collections.defaultdict(lambda: collections.defaultdict(set))
    for (part, name), lvs in scope.items():
        if part == MODULE and name in module_split:
            for lv, examples in lvs.items():
                for template in examples:
                    expanded[(part, module_split[name].get(template.lower(), name))][lv].add(template)
            continue
        if part == NUGGET and name in split:
            for lv, examples in lvs.items():
                for w in examples:
                    expanded[(part, split[name].get(w.lower(), name))][lv].add(w)
        else:
            for lv, examples in lvs.items():
                expanded[(part, name)][lv].update(examples)
    return expanded, split


def render(items, scope, missing, declared=None):
    # Field-form partitions carry exact retail weapon membership. Attribute each
    # reached weapon once; unknown/custom weapons conservatively keep the TODO base.
    scope, split = expand_forms(items, scope)
    import inventory
    by = {(i['part'], i['name']): i for i in items}
    # All retail forms can be measured while a custom weapon is not: keep its TODO row (no retail uses to the total)
    by.update({(NUGGET, n): dict(part=NUGGET, name=n, uses=0, state=TODO, why='未覆盖的自制或未知武器写法；原版字段分片'
                                 '另行登记') for p, n in scope if p == NUGGET and n in split and (p, n) not in by})
    own = {k: dict(part=k[0], name=k[1], uses=0, state=st, why=f'自制，原版不用；{why}') for k in scope if k not in by
           for st, why in [OWN.get(k, (TODO, '没登记（inventory_levels.OWN）'))]}
    inventory.apply_declared(list(own.values()), declared, notes={})
    by.update(own)
    rows = []
    for (part, name), lvs in scope.items():
        it = by[(part, name)]
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
             '自制技能（原版不用、清单没有）按 0 用量列进来，状态登记在 `inventory_levels.OWN`。停止条件①：下表全部已对拍。', '',
             f'**已对拍 {done} / {len(live)}**（不涉及的不算）。', '',
             '| 部分 | 已对拍 | 推断 | 未做 | 不涉及 |', '|---|---|---|---|---|']
    lines += [f'| {p} | {count[(p, BENCHED)]} | {count[(p, GUESSED)]} | {count[(p, TODO)]} | '
              f'{sum(r[0]["part"] == p and r[0]["state"] == NA for r in rows)} |' for p in PARTS]
    lines += ['', f'按原版用量加权：已对拍 {pct({BENCHED})}%，已有（已对拍+推断）{pct({BENCHED, GUESSED})}%。']
    gone = {lv: t for lv, t in missing.items() if t}
    if gone:
        lines += ['', '摆了、但原版数据和我们的单位里都找不到的模板（模块没算）：'
                  + '；'.join(f'{lv} ' + '、'.join(f'`{t}`' for t in ts) for lv, ts in gone.items()) + '。']
    lines += ['', '摆了、但在这几关里不会动的（不算）：'
              + '；'.join(f'`{n}` {" ".join(lvs)}：{why}' for (_, n), (lvs, why) in INERT.items()) + '。']
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
