r"""How big a campaign mission is, by where it sits in its campaign (read only: the retail script cache in
work/retailref/ that experimental/campaign/retailref.py builds, and timeline.json next to this file).

  python -I -X utf8 docs/design/teardowns/data/scale_measure.py      -> scale.json and scale.md next to this file

Per retail campaign map:
  position   前期 / 中期 / 后期: RA3's three lines of 9 missions by 1-3 / 4-6 / 7-9; Uprising's short lines (3-4
             missions) by the first / the middle ones / the last
  main       main objectives on the map's objective list
  waves      segments: the distinct progress anchors the main objectives are revealed at (timeline.json; Yokohama
             reveals at 开局, P7 and P31 -> 3). A wave revealed together with an earlier one does not count
  grows      the map changes after control is handed back: border switches and large reveals (timeline.json)
  base       有 when the player has a construction yard or MCV at some point: on the map as Player_1's, handed
             over by script (NAMED_TRANSFER_OWNERSHIP_PLAYER, TEAM_TRANSFER_TO_PLAYER, PLAYER_TRANSFER_OWNERSHIP_PLAYER
             to Player_1 -- retail puts the player's things on placeholder teams like Soviet01/...) or created on a
             player-1 team; when it comes is not read (the hand-checked late maps are in scale.md)
  verbs      the distinct first words of the main objectives' titles (Destroy, Capture, Hold, Escort ...), and
             how often the verb changes along the reveal order
  given      script actions creating units on a player-1 team (reinforcements and gifts; MCVs and buildings apart)
  heroes     commando templates the player starts with or is given
  kinds      how many kinds of unit the player commands over the mission (on the map, handed over, created;
             buildings, MCVs and props apart): how wide the toolkit is
  countdown  the mission shows a countdown (DISPLAY_COUNTDOWN_TIMER)
  turns      局面变化: (waves - 1) + grows -- each a moment the player's job or map changes

Not measurable from the scripts: how long a mission takes (it depends on the player). Script spawns at the very
start count as given too (the scripts do not say when they run); the hand-checked maps are in scale.md.
"""
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
CACHE = os.path.join(ROOT, 'work', 'retailref')
TIMELINE = os.path.join(HERE, 'timeline.json')

BASE = re.compile(r'(?i)mcv|constructionyard')
HERO = re.compile(r'(?i)commando')
P1_TEAM = re.compile(r'(?i)^player_1/|(?<![a-z0-9])p1(?![a-z0-9])|player ?1(?![0-9])')
CREATE = re.compile(r"DO CREATE_\w*\('[^']*', '([^']*)', '([^']*)'")
TRANSFER = re.compile(r"DO PLAYER_TRANSFER_OWNERSHIP_PLAYER\('([^']*)', 'Player_1'\)")
NAMED_TO_P1 = re.compile(r"DO NAMED_TRANSFER_OWNERSHIP_PLAYER\('([^']*)', 'Player_1'\)")
TEAM_TO_P1 = re.compile(r"DO TEAM_TRANSFER_TO_PLAYER\('([^']*)', 'Player_1'\)")
STRUCTURE = re.compile(r'(?i)egg$|yard|barracks|factory|refinery|powerplant|reactor|airfield|airpad|naval|'
                       r'construction|wall|bunker|tower|defense|turret|core$')


def position(name):
    """('RA3' or 'Uprising', line, number, 前期 / 中期 / 后期)."""
    m = re.match(r'camp_(?:(ep01)_)?([asjy])(\d\d)_', name)
    ep, line, n = m.group(1), m.group(2), int(m.group(3))
    if not ep:
        return 'RA3', line, n, ('前期', '中期', '后期')[(n - 1) // 3]
    last = max(int(re.match(r'camp_ep01_[asjy](\d\d)', f).group(1)) for f in os.listdir(CACHE)
               if f.startswith(f'camp_ep01_{line}') and f.endswith('.txt'))
    return 'Uprising', line, n, '前期' if n == 1 else '后期' if n == last else '中期'


def anchor(t):
    """The progress anchor of a timeline moment: '开局', 'P7' (a leading ≈ dropped)."""
    return t.lstrip('≈').split(' ')[0]


def measure(name, tl):
    data = json.load(open(os.path.join(CACHE, name + '.json'), encoding='utf-8'))
    text = open(os.path.join(CACHE, name + '.txt'), encoding='utf-8').read()
    titles = {g['name']: g.get('title') or g['name'] for g in data['goals']}
    mains = [g['name'] for g in data['goals'] if not g['bonus']]
    # the reveal order and anchors of the main objectives, and the map's growth after the hand-over
    order, anchors, grows, handed = [], [], 0, False
    for m in tl['moments']:
        if m['label'] == '交还控制':
            handed = True
        elif m['label'].startswith(('换边界', '大块揭图')) and handed:
            grows += 1
        for g in m['goals']:
            if not g['bonus'] and g['name'] not in order:
                order.append(g['name'])
                if anchor(m['t']) not in anchors:
                    anchors.append(anchor(m['t']))
    verbs = [(titles.get(g) or g).split()[0] for g in order]
    changes = sum(1 for a, b in zip(verbs, verbs[1:]) if a != b)
    # the player's base and units. Retail places them on placeholder teams (Soviet01/...) and hands them over by
    # script: an object by name, a team, or a whole placeholder player; or creates them on a player-1 team
    objs = data['objects']
    mine = [o for o in objs if o['owner'].startswith('Player_1')]
    handed = [o for o in objs if o.get('name') in set(NAMED_TO_P1.findall(text))]
    handed += [o for o in objs if o['owner'] in set(TEAM_TO_P1.findall(text))]
    transfers = TRANSFER.findall(text)
    handed += [o for o in objs if o['owner'].split('/')[0] in transfers]
    made = [(t, team) for t, team in CREATE.findall(text) if P1_TEAM.search(team)]
    has_base = any(BASE.search(o['t']) for o in mine + handed) or any(BASE.search(t) for t, _ in made)
    base = '有' if has_base else '无'
    given = sum(1 for t, _ in made if not BASE.search(t) and not STRUCTURE.search(t))
    heroes = sorted({o['t'] for o in mine + handed if HERO.search(o['t'])} | {t for t, _ in made if HERO.search(t)},
                    key=str.lower)
    waves = max(len(anchors), 1)
    kinds = {o['t'].lower() for o in mine + handed if not STRUCTURE.search(o['t']) and not BASE.search(o['t'])}
    kinds |= {t.lower() for t, _ in made if not STRUCTURE.search(t) and not BASE.search(t)}
    kinds = {k for k in kinds if not re.search(r'(?i)waypoint|derrick|civilian|prop|garage|radar|hospital|lab', k)}
    game, line, n, pos = position(name)
    return dict(map=name, game=game, line=line, n=n, position=pos, main=len(mains), waves=waves, grows=grows,
                base=base, verbs=sorted(set(verbs)), verb_changes=changes, given=given, heroes=heroes,
                kinds=len(kinds),
                countdown='DISPLAY_COUNTDOWN_TIMER' in text, transfers=transfers,
                turns=(waves - 1) + grows)


def summary(rows):
    out = {}
    for pos in ('前期', '中期', '后期'):
        rs = [r for r in rows if r['position'] == pos]
        med = lambda k: statistics.median(r[k] for r in rs)       # noqa: E731
        rng = lambda k: (min(r[k] for r in rs), max(r[k] for r in rs))   # noqa: E731
        q1 = lambda k: statistics.quantiles([r[k] for r in rs], n=4, method='inclusive')[0]   # noqa: E731
        out[pos] = dict(n=len(rs), main=med('main'), main_range=rng('main'), waves=med('waves'),
                        waves_range=rng('waves'), grows=med('grows'), turns=med('turns'), turns_range=rng('turns'),
                        verbs=statistics.median(len(r['verbs']) for r in rs),
                        base=sum(r['base'] == '有' for r in rs),
                        heroes=sum(bool(r['heroes']) for r in rs), countdown=sum(r['countdown'] for r in rs),
                        given=med('given'), kinds=med('kinds'),
                        q1={k: q1(k) for k in ('main', 'waves', 'grows', 'turns', 'kinds')},
                        verbs_q1=statistics.quantiles([len(r['verbs']) for r in rs], n=4, method='inclusive')[0])
    return out


def table(rows, s):
    lines = ['# 关卡规模随战役位置怎么变（原版 40 关）', '',
             '由 [scale_measure.py](scale_measure.py) 生成，原始数据 [scale.json](scale.json)。每一项怎么量的，见脚本开头。'
             '"时长"量不出来（取决于玩家），用段数和局面变化代替。', '',
             '## 按位置汇总（中位数，括号里是最少～最多）', '',
             '| 位置 | 关数 | 主目标 | 段（目标分几批亮） | 地图变化 | 局面变化 | 主目标的动词种数 | 玩家有基地 | 有英雄 | 有倒计时 |',
             '|---|---|---|---|---|---|---|---|---|---|']
    for pos, v in s.items():
        b = v['base']
        lines.append(f"| {pos} | {v['n']} | {v['main']:g}（{v['main_range'][0]}～{v['main_range'][1]}） | "
                     f"{v['waves']:g}（{v['waves_range'][0]}～{v['waves_range'][1]}） | {v['grows']:g} | "
                     f"{v['turns']:g}（{v['turns_range'][0]}～{v['turns_range'][1]}） | {v['verbs']:g} | "
                     f"{b} | {v['heroes']} | {v['countdown']} |")
    lines += ['', '## 下四分位（四分之三的关至少有这么多）', '',
              '| 位置 | 主目标 | 段 | 地图变化 | 局面变化 | 主目标的动词种数 | 玩家指挥的兵种数 |', '|---|---|---|---|---|---|---|']
    for pos, v in s.items():
        q = v['q1']
        lines.append(f"| {pos} | {q['main']:g} | {q['waves']:g} | {q['grows']:g} | {q['turns']:g} | {v['verbs_q1']:g} | "
                     f"{q['kinds']:g}（中位 {v['kinds']:g}） |")
    lines += ['', '## 每关', '',
              '| 关 | 位置 | 主目标 | 段 | 地图变化 | 基地 | 主目标的动词 | 中途给兵（次） | 兵种数 | 英雄 | 倒计时 | 局面变化 |',
              '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in sorted(rows, key=lambda r: (r['game'], r['line'], r['n'])):
        lines.append(f"| {r['map']} | {r['position']} | {r['main']} | {r['waves']} | {r['grows']} | {r['base']} | "
                     f"{' / '.join(r['verbs'])} | {r['given']} | {r['kinds']} | {', '.join(r['heroes']) or '—'} | "
                     f"{'有' if r['countdown'] else '—'} | {r['turns']} |")
    return '\n'.join(lines) + '\n'


def main():
    tl = json.load(open(TIMELINE, encoding='utf-8'))
    rows = [measure(k, v) for k, v in tl.items() if k.startswith('camp_')]
    s = summary(rows)
    json.dump(dict(rows=rows, summary=s), open(os.path.join(HERE, 'scale.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    open(os.path.join(HERE, 'scale.md'), 'w', encoding='utf-8').write(table(rows, s))
    print(table(rows, s))


if __name__ == '__main__':
    sys.exit(main())
