r"""Air power in the campaign maps, retail and ours, one ruler (read only: retail archives, built mods): may the
player build aircraft, when, and how the enemy's strongholds answer them.

  python -I -X utf8 docs/design/teardowns/data/air_measure.py            -> air.json + air.md here
  python -I -X utf8 docs/design/teardowns/data/air_measure.py j02 A4     (only these; the md is rebuilt from the json)

Why: aircraft ignore terrain -- they fly over cliffs, ramps and ice walls and see the high ground the ground army
cannot (RA3: low ground does not see high ground, user 2026-10-27) -- so every terrain choice (P25-P27) holds only
as far as the level answers the player's air: anti-air at the strongholds, or no aircraft for the player.

Per map:
  faction    the human player's (SidesList playerFaction)
  air        ALLOW_DISALLOW_ONE_BUILDING(player, template, 0 / 1) on the human faction's airfield and aircraft
             (<faction>airfield, <faction>*aircraft; Japan: its transforming fliers, JAPAN_AIR), and
             PLAYER_LOCK_PLAYER_TECH(player, PlayerTech_<faction>_AirPower, 1 lock / 0 unlock), where the player is
             the human, <All Players>, <All Human Players>, or <This Player> in the human's own script list (each
             SidesList player has one; when they cannot be matched, <This Player> counts if the template is the human
             faction's). 'At the start' = a script whose conditions are all CONDITION_TRUE. A template never mentioned
             counts as allowed (the engine's default).
             start: 'none' (air tech locked, or the airfield disallowed and no aircraft allowed), 'some' (some
             aircraft disallowed), 'all'; unlocked later: what a later script allows (or the air tech unlocked)
  base       whether the player ever has a base: a construction yard or MCV of its own on the map, one handed over
             (PLAYER_TRANSFER_OWNERSHIP_PLAYER from a player that has one), or allowed / sent in by a script -- without
             a base the player builds nothing, aircraft included
  enemy AA   placed enemy-owned objects whose template says antiair / basedefenseair / flak; the share of enemy
             strongholds (layout_measure.clusters, >= 8 objects) with one within 600
"""
import json
import os
import re
import statistics
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout_measure as LM  # noqa: E402
from layout_measure import mapstudy, mapxml  # noqa: E402

OUT_JSON = os.path.join(HERE, 'air.json')
OUT_MD = os.path.join(HERE, 'air.md')
AA = re.compile(r'antiair|basedefenseair|flak', re.I)
NEAR = 600
BASE = re.compile(r'constructionyard|mcv', re.I)
GENERIC = ('<This Player>', '<All Human Players>', '<Local Player>')


FACTION = {'PlayerTemplate:Allies': 'allied', 'PlayerTemplate:Soviet': 'soviet', 'PlayerTemplate:Japan': 'japan'}
# Japan's aircraft are transforming units built at the war factory and naval yard (their templates do not say
# 'aircraft'; the three with an airborne form in the index: *airborne_collapse)
JAPAN_AIR = ('japanantiairvehicletech1', 'japanantiairship', 'japanantiinfantryvehicle')


def air_template(t, faction):
    t = t.lower()
    if faction == 'japan':
        return t in JAPAN_AIR
    return t.startswith(faction) and (t.endswith('airfield') or 'aircraft' in t)


def owned_scripts(m, names):
    """(owner, title, conds, acts) for every script, owner from its PlayerScriptsList entry: the list holds one
    ScriptList per SidesList player, the first for the unnamed neutral player ('') -- mapstudy.players lists the
    named ones in SidesList order. If the counts do not match, every owner is None."""
    psl = next((x for _, x in m.walk() if x.name == 'PlayerScriptsList'), None)
    lists = [k for k in psl.kids if k.name == 'ScriptList'] if psl else []
    owners = [''] + list(names) if len(lists) == len(names) + 1 else [None] * len(lists)
    out = []
    for owner, sl in zip(owners, lists):
        for _, n in m.walk([sl]):
            if n.name != 'Script':
                continue
            conds, acts = [], []
            for _, k in m.walk(n.kids):
                if k.name == 'Condition':
                    conds.append(m.content(k))
                elif k.name == 'ScriptAction':
                    acts.append(m.content(k))
            out.append((owner, m.string(n.head, 0)[0], conds, acts))
    return out, owners[0] is not None


def measure(name, m):
    sides = mapstudy.players(m)
    human = next((n for n, p in sides.items() if p.get('playerIsHuman')), 'Player_1')
    enemies = set(sides.get(human, {}).get('playerEnemies', '').split())
    faction = FACTION.get(str(sides.get(human, {}).get('playerFaction', '')))
    foes, aa, yards = [], [], set()
    for o in mapxml.objects(m):
        side = str(o['props'].get('originalOwner', '')).split('/')[0]
        if BASE.search(o['template']):
            yards.add(side)
        if side in enemies:
            foes.append((o['x'], o['y']))
            if AA.search(o['template']):
                aa.append((o['x'], o['y']))
    scripts, attributed = owned_scripts(m, list(sides))
    banned, allowed, later, locked, unlocked = set(), set(), set(), False, False
    base = human in yards
    for owner, title, conds, acts in scripts:
        for an, args, _ in acts:
            vals = [str(a[1]) for a in args]
            if an == 'PLAYER_TRANSFER_OWNERSHIP_PLAYER' and len(vals) >= 2 and vals[1] == human and vals[0] in yards:
                base = True
            if an in ('ALLOW_DISALLOW_ONE_BUILDING', 'CREATE_REINFORCEMENT_TEAM', 'CREATE_REINFORCEMENT_TEAM_WITH_STANCE') \
                    and any(BASE.search(v) for v in vals) and (an != 'ALLOW_DISALLOW_ONE_BUILDING' or vals[-1] == '1'):
                base = True
    for owner, title, conds, acts in scripts:
        start = all(c[0] == 'CONDITION_TRUE' for c in conds)
        for an, args, _ in acts:
            if an not in ('ALLOW_DISALLOW_ONE_BUILDING', 'PLAYER_LOCK_PLAYER_TECH'):
                continue
            vals = [a[1] for a in args]
            who, what = str(vals[0]), str(vals[1])
            flag = int(vals[2]) if len(vals) > 2 else 1
            mine = who == human or who in ('<All Players>', '<All Human Players>') or \
                (who == '<This Player>' and (owner == human or (owner is None and what.lower().startswith(faction or '-'))))
            if not mine:
                continue
            if an == 'PLAYER_LOCK_PLAYER_TECH':
                if 'airpower' in what.lower() and faction and faction[:4] in what.lower():
                    if flag and start:
                        locked = True
                    elif not flag and not start:
                        unlocked = True
                continue
            if not faction or not air_template(what, faction):
                continue
            if start:
                (allowed if flag else banned).add(what.lower())
            elif flag:
                later.add(what.lower())
    banned -= allowed
    airfield = f'{faction}airfield'
    if faction == 'japan':
        state = 'none' if banned and not allowed else 'some' if banned else 'all'
    elif locked or (airfield in banned and not allowed):
        state = 'none'
    elif banned:
        state = 'some'
    else:
        state = 'all'
    if unlocked:
        later.add('PlayerTech AirPower')
    big = [c for c, n in LM.clusters(foes) if n >= 8]
    covered = sum(1 for c in big if any(np.hypot(x - c[0], y - c[1]) < NEAR for x, y in aa))
    return dict(map=name, faction=faction, attributed=attributed, base=base, air_start=state, banned=sorted(banned),
                allowed=sorted(allowed), tech_locked=locked, unlocked_later=sorted(later), enemy_aa=len(aa),
                strongholds=len(big), strongholds_with_aa=covered)


def short(name):
    if name.startswith('ours_'):
        return name.split('_')[1]
    s = name.replace('camp_', '').replace('ep01_', 'up-')
    return '_'.join(s.split('_')[:2])


WORD = dict(none='开局禁', some='部分禁', all='不限')


def write_md(data):
    lines = ['# 空军：玩家能不能造飞机、敌人据点有没有防空（每关一行）', '',
             '由 [air_measure.py](air_measure.py) 生成，口径见脚本开头。"开局禁"：玩家阵营的机场在开局被禁，'
             '而且没有一种飞机开局可造；"后来放开"：之后某个脚本允许造的机场或飞机。', '',
             '| 关 | 阵营 | 玩家有基地 | 玩家空军（开局） | 后来放开 | 敌方防空（预摆） | 有防空的敌方据点 / 据点数 |',
             '|---|---|---|---|---|---|---|']
    agg = {}
    for name in sorted(data, key=lambda n: (n.startswith('ours'), n)):
        v = data[name]
        if 'error' in v:
            lines.append(f'| {short(name)} | 读不出：{v["error"]} | | | | | |')
            continue
        side = 'ours' if name.startswith('ours') else 'retail'
        a = agg.setdefault(side, dict(n=0, states={}, later=0, aa=[], cov=[0, 0]))
        a['n'] += 1
        if v['base']:
            a['states'][v['air_start']] = a['states'].get(v['air_start'], 0) + 1
            a['later'] += bool(v['unlocked_later'])
        else:
            a['nobase'] = a.get('nobase', 0) + 1
        a['aa'].append(v['enemy_aa'])
        a['cov'][0] += v['strongholds_with_aa']
        a['cov'][1] += v['strongholds']
        later = '、'.join(t.replace(v['faction'] or '', '') for t in v['unlocked_later']) or '—'
        lines.append(f"| {short(name)} | {v['faction']} | {'有' if v['base'] else '—'} | "
                     f"{WORD[v['air_start']] if v['base'] else '（没基地，造不了）'} | {later} | {v['enemy_aa']} | "
                     f"{v['strongholds_with_aa']} / {v['strongholds']} |")
    lines += ['', '## 汇总', '', '| | 原版 | 我们 |', '|---|---|---|']
    r, o = agg.get('retail', {}), agg.get('ours', {})
    lines.append(f"| 玩家没有基地的关（造不了飞机） | {r.get('nobase', 0)} | {o.get('nobase', 0)} |")
    for k in ('none', 'some', 'all'):
        lines.append(f"| 有基地的关，空军开局{WORD[k]} | {r.get('states', {}).get(k, 0)} | {o.get('states', {}).get(k, 0)} |")
    lines.append(f"| 有基地的关，后来放开空军 | {r.get('later', 0)} | {o.get('later', 0)} |")
    med = lambda xs: statistics.median(xs) if xs else None  # noqa: E731
    lines.append(f"| 敌方预摆防空（中位数） | {med(r.get('aa', []))} | {med(o.get('aa', []))} |")
    lines.append(f"| 有防空的敌方据点 | {r.get('cov', [0, 0])[0]} / {r.get('cov', [0, 0])[1]} | "
                 f"{o.get('cov', [0, 0])[0]} / {o.get('cov', [0, 0])[1]} |")
    open(OUT_MD, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')


def main():
    parts = sys.argv[1:]
    old = json.load(open(OUT_JSON, encoding='utf-8')) if os.path.exists(OUT_JSON) else {}
    for name, load in LM.jobs(parts):
        try:
            old[name] = measure(name, load())
            v = old[name]
            print(name, v['faction'], v['air_start'], v['unlocked_later'], 'AA', v['enemy_aa'],
                  f"{v['strongholds_with_aa']}/{v['strongholds']}", flush=True)
        except Exception as ex:
            old[name] = dict(map=name, error=repr(ex))
            print('FAIL', name, repr(ex), flush=True)
        with open(OUT_JSON, 'w', encoding='utf-8') as fh:
            json.dump(old, fh, ensure_ascii=False, indent=1)
    write_md(old)


if __name__ == '__main__':
    main()
