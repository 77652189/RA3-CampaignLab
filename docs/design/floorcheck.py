r"""Floor rules (docs/design/floor-rules.md): the cases that are never fun, checked on a level's walkthrough page
(work/walkthrough/<level>.json, the shape of a4.json). Only blocks the certain failures; whether a level is fun is the
playtest of its card's hypothesis, not this.

  python -X utf8 docs/design/floorcheck.py                 -> every work/walkthrough/*.json
  python -X utf8 docs/design/floorcheck.py a4 [--verbose]  -> these levels; --verbose lists every wave / site checked

Per rule one line: PASS, FAIL (what and where), or 缺数据 (which field the page needs). The last line counts them.
Fields the rules read beyond what a4.json has today are optional and win over the guesses (floor-rules.md, 数据):
  phases[].kind      '攻' '守' '护送' '过场' '喘息' (else read from the name's brackets: 会场（护送，拮据）)
  phases[].roster    the player's unit types in that phase (else start units + reinforcements named so far, plus the
                     faction's standard roster minus start.cannot_build once a phase builds)
  waves[].warn_s     seconds between the first warning the player can see and the wave's spawn
  waves[].set_piece  true: not meant to be fought (scenery, must be avoided); F1 skips it
  devices[].answers  enemy bodies (步车空船) the device stops, counted as an answer in F1
  map.sites[].used_by  for 路线 sites: who takes it in which phase ([] = nobody: F2 fails)
"""
import glob
import json
import os
import re
import sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'experimental', 'campaign')))
import labpaths  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PAGES = os.path.join(labpaths.WORK, 'walkthrough')
DATA = os.path.join(HERE, 'teardowns', 'data')


def _data_module(name):
    """A module of teardowns/data loaded by its path (no sys.path edit: tests/test_architecture.py G4)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, os.path.join(DATA, name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

QUIET_S = 180       # F3: longest stretch of a defend / escort phase with no wave, no countdown (floor-rules.md F3)
WARN_S = 5          # F6: a wave that goes for a lose condition gives at least this much warning before it spawns
FACTION = {'A': 'allied', 'S': 'soviet', 'J': 'japan'}
ALIAS = {'鹰击者VX': '打击者-VX', '鹰击者-VX': '打击者-VX'}
GENERIC = {'帝国步兵': '步', '苏联步兵': '步', '盟军步兵': '步'}   # "some infantry": body only


def roles():
    """{Chinese unit name: (body, kills)} and {faction: [names]} from units_measure's hand table."""
    UM = _data_module('units_measure')
    table = {name: (body, kills) for name, body, kills in UM.ROLES.values()}
    standard = {f: [UM.ROLES[t][0] for t in ts if t in UM.ROLES] for f, ts in UM.STANDARD.items()}
    return table, standard


def unit_name(s):
    n = re.sub(r'[（(].*$', '', s or '').strip()
    return ALIAS.get(n, n)


def unit_names(s):
    """'海啸坦克、鹰击者VX（醒来再放开）' -> ['海啸坦克', '打击者-VX']."""
    return [unit_name(x) for x in re.split(r'[、,，+＋]|和', re.sub(r'[（(].*$', '', s or '')) if x.strip()]


def phase_kind(p):
    if p.get('kind'):
        return p['kind']
    m = re.search(r'[（(]([^，,）)]+)', p['name'])
    return m.group(1) if m else ('过场' if '过场' in p['name'] else '')


def rosters(page, table, standard):
    """{phase name: (set of unit names, guessed?)} in phase order."""
    faction = FACTION.get(page['title'][:1], 'allied')
    start = page.get('start', {})
    have = {unit_name(u['type']) for u in start.get('units', [])}
    named = [n for n in table if any(n in r for r in start.get('reinforcements', []))]
    banned = start.get('cannot_build', '')
    built, out = False, {}
    for p in page['phases']:
        if p.get('roster'):
            out[p['name']] = (set(p['roster']), False)
            continue
        built = built or '造' in (p.get('player_should') or '')
        r = set(have) | set(named)
        if built:
            r |= {n for n in standard[faction] if n not in banned}
        out[p['name']] = (r, True)
    return out


def phase_of(page, wave_phase):
    """The page's phase a wave belongs to ('会场' -> '会场（护送，拮据）'; '港口生变～布防' -> its first)."""
    for p in page['phases']:
        if p['name'].startswith(re.split(r'[～~]', wave_phase)[0]):
            return p
    return None


def f1_answers(page, table, standard):
    ros = rosters(page, table, standard)
    stops = {b for d in page.get('devices', []) for b in d.get('answers', [])}
    bad, unknown, guessed = [], set(), False
    for w in page['waves']:
        if w.get('set_piece'):
            continue
        p = phase_of(page, w['phase'])
        roster, g = ros.get(p['name'], (set(), True)) if p else (set(), True)
        guessed |= g
        for n in [n for u in w['units'] for n in unit_names(u.get('type'))]:
            if n not in table and n not in GENERIC:
                unknown.add(n)
                continue
            body = table[n][0] if n in table else GENERIC[n]
            if body in stops or any(body in table[m][1] for m in roster if m in table):
                continue
            bad.append(f"{w['phase']} {w.get('from_name') or w.get('from_site')} 的{n}（{body}）")
    if bad:
        return 'FAIL', '没有手段克制：' + '；'.join(sorted(set(bad)))
    if unknown:
        return '缺数据', '这些兵种不在 units_measure.ROLES 里，判不了：' + '、'.join(sorted(unknown))
    return 'PASS', '每一波都有兵种克制' + ('（名单按开局、援军、可造推断；可写 phases[].roster）' if guessed else '')


def f2_routes(page):
    """A route site is used when it says so (used_by) or the rest of the page names it (id or name)."""
    sites = [s for s in page['map'].get('sites', []) if s.get('kind') == '路线']
    rest = json.dumps({k: v for k, v in page.items() if k != 'map'}, ensure_ascii=False)
    idle = [s for s in sites if not s.get('used_by') and s['id'] not in rest and s['name'] not in rest]
    told = [s['name'] for s in idle if 'used_by' in s]
    if told:
        return 'FAIL', '这些路线写明了没人用（used_by 为空）：' + '、'.join(told)
    if idle:
        return '缺数据', '这些路线页面上没有一波、目标、机关或段落提到，要写 used_by（谁走、哪一段）或删掉：' + '、'.join(
            s['name'] for s in idle)
    return 'PASS', f'{len(sites)} 条路线都有用处'


def f3_quiet(page):
    """Defend / escort phases: no stretch longer than QUIET_S with neither a wave nor a countdown on screen."""
    counting = [x for x in page.get('pressures', []) if '倒计时' in x['what']]
    missing, worst = [], []
    for p in page['phases']:
        kind = phase_kind(p)
        if kind not in ('守', '护送'):
            continue
        if any(p['name'][:2] in x['what'] for x in counting):
            continue
        a, b = p.get('from_s'), p.get('to_s')
        times = sorted(w['at_s'] for w in page['waves'] if phase_of(page, w['phase']) is p and w.get('at_s') is not None)
        if a is None or b is None or not times:
            missing.append(p['name'])
            continue
        gap = max(y - x for x, y in zip([a] + times, times + [b]))
        if gap > QUIET_S:
            worst.append(f"{p['name']} {gap} 秒")
    if worst:
        return 'FAIL', f'守 / 护送段里超过 {QUIET_S} 秒没有一波也没有倒计时：' + '、'.join(worst)
    if missing:
        return '缺数据', '这些守 / 护送段没有倒计时，也缺起止时刻或出兵时刻：' + '、'.join(missing)
    return 'PASS', '守 / 护送段都有倒计时或波次压着'


def f4_idle(page):
    r = page.get('sim_result') or {}
    if '什么都不做' not in r.get('player', ''):
        return '缺数据', '要一次玩家挂机的结果（sim_result，player 写明挂机）'
    if r.get('outcome') == '赢':
        return 'FAIL', f"玩家什么都不做也赢了（{r.get('text')}）"
    return 'PASS', f"挂机{r.get('outcome')}（{r.get('text')}）"


def f6_warning(page):
    general = [x for x in page.get('pressures', []) if '预警' in x['what']]
    m = re.search(r'约?\s*(\d+)\s*秒', general[0]['effect']) if general else None
    default = int(m.group(1)) if m else None
    short, missing = [], []
    for w in page['waves']:
        if w.get('set_piece'):
            continue
        s = w.get('warn_s', default)
        if s is None:
            missing.append(f"{w['phase']} {w.get('from_name') or w.get('from_site')}")
        elif s < WARN_S:
            short.append(f"{w['phase']} {w.get('from_name') or w.get('from_site')} {s} 秒")
    if short:
        return 'FAIL', f'出兵前的预警不到 {WARN_S} 秒：' + '、'.join(short)
    if missing:
        return '缺数据', '这些波没有 warn_s，页面上也没有通用的出兵预警：' + '、'.join(sorted(set(missing)))
    return 'PASS', f'每一波出兵前都有预警（{default} 秒' + ('，取自通用的出兵预警）' if default is not None else '）')


RULES = [('F1 有一波没有手段克制', f1_answers), ('F2 有一条路从头到尾用不上', f2_routes),
         ('F3 守 / 护送段很久没有压力', f3_quiet), ('F4 挂机也能赢', f4_idle), ('F6 致命的一波没有预警', f6_warning)]


def main(argv):
    verbose = '--verbose' in argv
    names = [a for a in argv if not a.startswith('--')]
    paths = [os.path.join(PAGES, f'{n.lower()}.json') for n in names] or sorted(
        p for p in glob.glob(os.path.join(PAGES, '*.json')) if not p.endswith('_map.json'))
    table, standard = roles()
    count = {'PASS': 0, 'FAIL': 0, '缺数据': 0}
    for path in paths:
        page = json.load(open(path, encoding='utf-8'))
        level = os.path.basename(path)[:-5].upper()
        for title, rule in RULES:
            r = rule(page, table, standard) if rule is f1_answers else rule(page)
            count[r[0]] += 1
            text = r[1] if verbose or r[0] != 'PASS' else r[1][:60]
            print(f'{level} {title}: {r[0]} {text}')
    print(f"floorcheck: {len(paths)} 关，PASS {count['PASS']}，FAIL {count['FAIL']}，缺数据 {count['缺数据']}")
    return 1 if count['FAIL'] else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
