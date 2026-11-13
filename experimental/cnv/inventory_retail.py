r"""The retail campaign's 27 missions' share of the feature inventory (user 11-13: everything the 27 use gets 已对拍).
Printed, never written: the states come from inventory.collect(), so registering an item there moves it here.

What a mission uses, statically, the way inventory_levels reads our own 9:
  脚本动作 / 脚本条件  every action / condition line of its retail scripts (the retailref cache), actions refined
                    the inventory's way (simcoverage.refined)
  物体模块 / 武器效果  the effective modules / nugget types of the templates placed on its map or named by its
                    scripts, and what those reach (inventory_levels.reach)
  AI                not here yet: the cache does not keep the maps' AI personalities (engine B adds it)

  python -I -X utf8 experimental/cnv/inventory_retail.py            summary + the 30 heaviest gaps, with owners
  python -I -X utf8 experimental/cnv/inventory_retail.py --all      every gap
  python -I -X utf8 experimental/cnv/inventory_retail.py --part 脚本条件 [--mission s06]   one part / one mission
"""
import ast
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import inventory as I                            # noqa: E402

MISSION = re.compile(r'^camp_([asj]0\d)_.*\.txt$')   # Allied / Soviet / Empire 1-9; Uprising (ep01) left out
PARTS = (I.ACTION, I.CONDITION, I.MODULE, I.NUGGET)
OWNER = {I.ACTION: 'A', I.CONDITION: 'A', I.MODULE: 'E', I.NUGGET: 'C'}   # AGENTS.md map: script / object / weapon
LINE = re.compile(r'^\s*(IF(?: NOT)?|DO|ELSE)\s+([A-Z0-9_]+)\((.*)\)\s*(?:\+[0-9a-f]+)?\s*$')


def missions():
    """{short name (a01 ... s09): cache stem}, all 27 or a SystemExit naming what is missing."""
    I.need(I.RETAIL_SCRIPTS, 'the retail scripts cache (python -I -X utf8 experimental/campaign/retailref.py cache)')
    out = {MISSION.match(f).group(1): f[:-4] for f in sorted(os.listdir(I.RETAIL_SCRIPTS)) if MISSION.match(f)}
    if len(out) != 27:
        raise SystemExit(f'inventory_retail: {len(out)} retail missions in {I.RETAIL_SCRIPTS}, want 27')
    return out


def scope():
    """({(part, name): {mission: examples}}, {mission: Counter((part, name) -> script lines)})."""
    import inventory_levels as L
    import simcoverage
    objs, weapons = L.retail_tables()
    out = collections.defaultdict(dict)
    lines = collections.defaultdict(collections.Counter)
    for short, stem in missions().items():
        named = set()
        for line in open(os.path.join(I.RETAIL_SCRIPTS, stem + '.txt'), encoding='utf-8'):
            m = LINE.match(line)
            if not m:
                continue
            try:
                args = list(ast.literal_eval('(' + m.group(3) + ',)')) if m.group(3).strip() else []
            except (ValueError, SyntaxError):
                args = []
            key = (I.CONDITION, m.group(2)) if m.group(1).startswith('IF') else \
                (I.ACTION, simcoverage.refined(m.group(2), args))
            out[key].setdefault(short, set())
            lines[short][key] += 1
            named |= {a for a in args if isinstance(a, str)}
        placed = {o['t'] for o in json.load(open(os.path.join(I.RETAIL_SCRIPTS, stem + '.json'),
                                                 encoding='utf-8'))['objects']}
        seeds = {t for t in placed | named if t.lower() in objs}
        got_o, got_w = L.reach(seeds, objs, weapons)
        for k in got_o:
            for g, t, _, _ in L.effective(k, objs):
                out[(I.MODULE, f'{g}/{t}')].setdefault(short, set()).add(objs[k][0])
        for k in got_w:
            for t in set(L.nuggets(k, weapons)):
                out[(I.NUGGET, t)].setdefault(short, set()).add(weapons[k][0])
    expanded, _ = L.expand_forms(I.collect(PARTS), out)
    return expanded, lines


def used_items():
    """[item + 'missions' (sorted short names) + 'lines' (script lines over the 27)] for every inventory item the 27
    use, 不涉及 left out; and the names the inventory does not know."""
    items = I.collect(PARTS)
    by = {(i['part'], i['name']): i for i in items}
    sc, lines = scope()
    got, unknown = {}, set()
    for (part, name), ms in sc.items():
        it = by.get((part, name)) or by.get((part, name.split(':')[0]))
        if it is None:
            unknown.add((part, name))
            continue
        if it['state'] == I.NA:
            continue
        k = (part, it['name'])
        g = got.setdefault(k, dict(it, missions=set(), lines=0))
        g['missions'] |= set(ms)
        g['lines'] += sum(lines[m].get((part, name), 0) for m in ms)
    for g in got.values():
        g['missions'] = sorted(g['missions'])
    return list(got.values()), sorted(unknown)


def main(argv):
    show_all = '--all' in argv
    part = argv[argv.index('--part') + 1] if '--part' in argv else None
    mission = argv[argv.index('--mission') + 1] if '--mission' in argv else None
    items, unknown = used_items()
    print('| 部分 | 27 关用到的按用量已对拍 | 已对拍 / 项 | 推断 | 未做 | 缺的用量 | 归 |')
    print('|---|---|---|---|---|---|---|')
    for p in PARTS:
        xs = [i for i in items if i['part'] == p]
        c = collections.Counter(i['state'] for i in xs)
        u = collections.Counter()
        for i in xs:
            u[i['state']] += i['uses']
        tot = sum(u.values())
        print(f"| {p} | {100 * u[I.BENCHED] / tot:.2f}% | {c[I.BENCHED]} / {len(xs)} | {c[I.GUESSED]} | "
              f"{c[I.TODO]} | {tot - u[I.BENCHED]} | {OWNER[p]} |")
    print('| AI | 见 inventory.py（9 关口径），原版人格待 B 补 | | | | | B |')
    gaps = sorted((i for i in items if i['state'] != I.BENCHED and (part is None or i['part'] == part)
                   and (mission is None or mission in i['missions'])),
                  key=lambda i: (-i['uses'], i['name']))
    print(f'\ngaps ({len(gaps)}; 用量 / 27 关里的行数 / 几关):')
    for i in gaps if show_all else gaps[:30]:
        print(f"  {OWNER[i['part']]} {i['part']}/{i['name']} {i['uses']} {i['state']} "
              f"lines={i['lines']} 关={len(i['missions'])}")
    if unknown:
        print(f'\nnot in the inventory ({len(unknown)}): ' + ', '.join(f'{p}/{n}' for p, n in unknown[:20]))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
