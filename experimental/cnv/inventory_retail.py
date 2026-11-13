r"""The retail campaign's 27 missions' share of the feature inventory (user 11-13: everything the 27 use gets 已对拍).
Printed, never written: the states come from inventory.collect(), so registering an item there moves it here.

What a mission uses, statically, the way inventory_levels reads our own 9:
  脚本动作 / 脚本条件  every action / condition line of its retail scripts (the retailref cache), actions refined
                    the inventory's way (simcoverage.refined)
  物体模块 / 武器效果  the effective modules / nugget types of the templates placed on its map or named by its
                    scripts, and what those reach (inventory_levels.reach)
  AI                the maps' computer players (non-human, a personality other than DefaultPersonality -- the
                    neutral / civilian / scripted players carry that one; INFERRED that it adds nothing): every SDK AI
                    asset their personality reaches in the game's compiled stream (retailref ai.json), their faction's
                    ArmyDefinition and AIData, followed the inventory_ai.level_scope way (inventory_ai.reached). The
                    maps' own strategic states are read back from their compiled form (retailref ai_states.xml,
                    ai_compiled; an attribute written at its default value is not seen, a lower bound); their own
                    personalities, build and budget states are not read (counted apart as 本关自带、没读)

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
ALL = PARTS + (I.AI,)
OWNER = {I.ACTION: 'A', I.CONDITION: 'A', I.MODULE: 'E', I.NUGGET: 'C', I.AI: 'B'}
NO_AI = ('', 'DefaultPersonality')   # AGENTS.md map: script / object / weapon
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


def ai_players(stem):
    """[player] of the map's computer players with a personality of their own (retailref cache 'players')."""
    d = json.load(open(os.path.join(I.RETAIL_SCRIPTS, stem + '.json'), encoding='utf-8'))
    if 'players' not in d:
        raise SystemExit('inventory_retail: the retail cache has no players: python -I -X utf8 experimental/campaign/'
                         'retailref.py cache')
    return [p for p in d['players'] if not p['human'] and p['personality'] not in NO_AI]


def compiled_states():
    """{name: element} of the stream's strategic states read back from their compiled form (retailref ai_states.xml,
    ai_compiled: attributes at their default value are not told apart from unwritten ones, a lower bound)."""
    import retailref
    I.need(retailref.AI_STATES, 'the decoded retail strategic states (python -I -X utf8 experimental/campaign/'
                                'retailref.py cache-ai-states; needs the private layout ai_compiled.LAYOUT)')
    import xml.etree.ElementTree as ET
    return {el.get('id'): el for el in ET.parse(retailref.AI_STATES).getroot()}


def ai_scope():
    """({(AI, item name): {mission: set()}}, {mission: {(asset type, name)}} of the maps' own compiled AI assets)."""
    import inventory_ai as A
    path = os.path.join(I.RETAIL_SCRIPTS, 'ai.json')
    I.need(path, 'the retail AI cache (python -I -X utf8 experimental/campaign/retailref.py cache-ai)')
    reach = json.load(open(path, encoding='utf-8'))
    states = compiled_states()
    index = A.assets()
    glob = [el for el in index.values() if A._local(el.tag) == 'AIData']
    out, local, memo = collections.defaultdict(dict), collections.defaultdict(set), {}
    for short, stem in missions().items():
        for p in ai_players(stem):
            refs = reach.get(p['personality'])
            if refs is None:
                raise SystemExit(f"inventory_retail: {short} {p['name']}: personality {p['personality']} is not in "
                                 'the compiled stream')
            local[short] |= {(t, n) for t, n, _ in refs if n not in index and n not in states}
            key = (p['personality'], p['faction'])
            if key not in memo:
                roots = [index[n] for _, n, _ in refs if n in index]
                roots += [states[n] for t, n, _ in refs if n not in index and n in states]   # the map's own, decoded
                army = [el for el in index.values() if A._local(el.tag) == 'ArmyDefinition'
                        and el.get('Side') == 'PlayerTemplate:' + p['faction']]
                memo[key] = A.reached(roots + army + glob, index)
            for name in memo[key]:
                out[(I.AI, name)].setdefault(short, set())
    return out, local


def used_items():
    """[item + 'missions' (sorted short names) + 'lines' (script lines over the 27)] for every inventory item the 27
    use, 不涉及 left out; and the names the inventory does not know."""
    items = I.collect(ALL)
    by = {(i['part'], i['name']): i for i in items}
    sc, lines = scope()
    sc.update(ai_scope()[0])
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
    for p in ALL:
        xs = [i for i in items if i['part'] == p]
        c = collections.Counter(i['state'] for i in xs)
        u = collections.Counter()
        for i in xs:
            u[i['state']] += i['uses']
        tot = sum(u.values())
        print(f"| {p} | {100 * u[I.BENCHED] / tot:.2f}% | {c[I.BENCHED]} / {len(xs)} | {c[I.GUESSED]} | "
              f"{c[I.TODO]} | {tot - u[I.BENCHED]} | {OWNER[p]} |")
    local = set().union(*ai_scope()[1].values())
    print(f'\nAI：本关自带的战略状态已从编译二进制读回（写成默认值的属性分不出，偏少）；其余本关自带的人格 / 状态 '
          f'{len(local)} 个自身字段没读，只按它们引用的 SDK 资产计')
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
