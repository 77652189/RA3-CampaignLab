r"""The retail feature inventory (ADR 0026): everything the retail game uses that the simulator should be able to do,
each item with a state, ordered by how much retail uses it. Generated from retail data -- never written by hand --
into docs/engine/inventory.md; tests/test_inventory.py fails when the file is stale (a new item, a changed state).

Parts (the engine A line's share of ADR 0026; AI is the B line's):
  脚本动作 / 脚本条件  every action and condition name the retail campaign scripts use (script_catalog.json), with the
                    uses counted in the retail scripts (work/retailref, retailref.py's cache); an action told apart by
                    what it is told to do (a status bit, a special power, a command button: simcoverage.refined) is
                    one item per refinement
  物体模块          every module type the retail GameObjects use (retailmodules.module_census: includes and
                    inheritance resolved), counted by templates placed in the retail campaign maps, then by all
  武器效果          every Nugget type of the retail weapons (retailmodules.weapon_census)

States (STATES): 已对拍 -- implemented and a bench comparison test cites it (BENCHED: the register, each entry naming
the test); 推断 -- the simulator has code for it, no bench comparison yet; 未做 -- nothing; 不涉及 -- presentation only
(a rule below, by name or module group: never a list). How "has code" is told:
  script names    simcoverage.name_state: the engine model's core, a Sim.act / Sim.cond branch (probed with a retail
                  use's own arguments), sim.SHOWN; sim.IGNORED is 未做 (dropped on purpose, may hide play)
  modules, nuggets  the type's name is a string constant in sim.py / simunits.py / simproxy.py (simcoverage.sim_code)
                  -- a first cut: a module read under another name shows as 未做 until NOTES says otherwise

  python -I -X utf8 experimental/cnv/inventory.py            regenerate docs/engine/inventory.md, print the summary
  python -I -X utf8 experimental/cnv/inventory.py --check    exit 1 when the file is stale
"""
import ast
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

CATALOG = os.path.join(ROOT, 'experimental', 'campaign', 'script_catalog.json')
RETAIL_SCRIPTS = os.path.join(ROOT, 'work', 'retailref')
OUT = os.path.join(ROOT, 'docs', 'engine', 'inventory.md')

BENCHED, GUESSED, TODO, NA = '已对拍', '推断', '未做', '不涉及'
STATES = (BENCHED, GUESSED, TODO, NA)
ACTION, CONDITION, MODULE, NUGGET = '脚本动作', '脚本条件', '物体模块', '武器效果'
PARTS = (ACTION, CONDITION, MODULE, NUGGET)

# (part, name) -> 'tests/<file>.py::<test>': the bench comparison that backs the item (the guard checks the test exists)
BENCHED_TESTS = {}

# (part, name) -> (state, why): where the name rule above is wrong (a module read under another name ...)
NOTES = {
    (MODULE, 'Body/ActiveBody'): (GUESSED, 'simunits.stats 读 MaxHealth（只有生命值；受伤状态、回血等另算）'),
    (MODULE, 'AI/AIUpdate'): (GUESSED, 'Sim.fight / 移动（单位 AI 的状态机细项按引擎 B 的 AI 清单推进）'),
}

# presentation only: script actions that move the camera, play sound / film, draw on screen (conditions are never NA:
# a script may wait on a camera); module groups that only draw
PRESENTATION_ACTION = re.compile(
    r'^(CAMERA_|MOVE_CAMERA|ZOOM_CAMERA|PITCH_CAMERA|ROTATE_CAMERA|RESET_CAMERA|SETUP_CAMERA|FREEZE_TIME|UNFREEZE_TIME|'
    r'CAMERA|SOUND_|PLAY_SOUND|MUSIC_|PATH_MUSIC|SPEECH_|MOVIE_|CINEMATIC|DISPLAY_CINEMATIC|FADE|SCREEN_SHAKE|'
    r'DRAW_|NAMED_FLASH|SHOW_|HIDE_|LETTERBOX|OBJECT_CREATE_RADAR_EVENT|RADAR_CREATE_EVENT|EVA_|NAMED_SET_EVAC|'
    r'SET_VISUAL_SPEED|WEATHER|TERRAIN_RENDER|WATER_|SKYBOX|OVERSIZE_TERRAIN)')
PRESENTATION_GROUPS = {'Draws', 'ClientBehaviors'}
PRESENTATION_MODULE = re.compile(r'(Draw|Sound|Audio|Particle|FXList|Decal|Shadow|Flash|Camera|Animation)', re.I)


def need(path, what):
    if not os.path.exists(path):
        raise SystemExit(f'inventory: {what} not found: {path}')


# ---- script names
def retail_uses():
    """{('act' | 'cond', key): [uses, first args]} counted in the retail campaign scripts; key refined for actions."""
    import simcoverage
    need(RETAIL_SCRIPTS, 'the retail scripts cache (python -I -X utf8 experimental/campaign/retailref.py cache)')
    rx = re.compile(r'^\s*(IF(?: NOT)?|DO|ELSE)\s+([A-Z0-9_]+)\((.*)\)\s*(?:\+[0-9a-f]+)?\s*$')
    out = {}
    names = sorted(f for f in os.listdir(RETAIL_SCRIPTS) if f.endswith('.txt'))
    if not names:
        raise SystemExit(f'inventory: no retail scripts in {RETAIL_SCRIPTS}')
    for f in names:
        for line in open(os.path.join(RETAIL_SCRIPTS, f), encoding='utf-8'):
            m = rx.match(line)
            if not m:
                continue
            kind = 'cond' if m.group(1).startswith('IF') else 'act'
            try:
                args = list(ast.literal_eval('(' + m.group(3) + ',)')) if m.group(3).strip() else []
            except (ValueError, SyntaxError):
                args = []
            key = simcoverage.refined(m.group(2), args) if kind == 'act' else m.group(2)
            got = out.setdefault((kind, key), [0, args])
            got[0] += 1
    return out


class _Inf:
    own = {}


def script_items():
    import simcoverage
    need(CATALOG, 'the retail script catalog')
    catalog = json.load(open(CATALOG, encoding='utf-8'))
    uses = retail_uses()
    for name, v in catalog.items():                     # every catalog name is an item, even if no line was parsed
        kind = 'cond' if v['kind'] == 'Condition' else 'act'
        if not any(k == kind and (key == name or key.startswith(name + ':')) for k, key in uses):
            uses[(kind, name)] = [v['uses'], []]
    modelled = simcoverage.status_modelled()
    items = []
    for (kind, key), (n, args) in uses.items():
        name, _, detail = key.partition(':')
        st = simcoverage.name_state(kind, name, args, _Inf)
        part = ACTION if kind == 'act' else CONDITION
        if st in ('core', 'shown', 'handled'):
            state, why = GUESSED, {'core': '引擎模型核心', 'shown': '只记进时间线（sim.SHOWN）', 'handled': 'Sim.act / Sim.cond 有分支'}[st]
            if detail and name == 'UNIT_CHANGE_OBJECT_STATUS' and detail not in modelled:
                state, why = TODO, f'状态位 {detail} 只记下来'
            elif detail and name in ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'NAMED_USE_COMMANDBUTTON_ABILITY',
                                     'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED') and \
                    not (name == 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT' and simcoverage.power_modelled(detail, _Inf)):
                state, why = TODO, '只记进时间线，没有效果'
        elif st == 'ignored':
            state, why = TODO, 'sim.IGNORED 明确丢掉'
        else:
            state, why = TODO, 'Sim.act / Sim.cond 不认识'
        if part == ACTION and state == TODO and PRESENTATION_ACTION.match(name) and not detail:
            state, why = NA, '纯表现（名字规则）'
        items.append(dict(part=part, name=key, uses=n, state=state, why=why))
    return items


# ---- modules and weapon effects
def module_items():
    import retailmodules
    import simcoverage
    code = simcoverage.sim_code()
    items = []
    for (group, mtype), v in retailmodules.module_census().items():
        if group in PRESENTATION_GROUPS or PRESENTATION_MODULE.search(mtype):
            state, why = NA, f'纯表现（{group}）' if group in PRESENTATION_GROUPS else '纯表现（名字规则）'
        elif any(mtype in s for s in code):
            state, why = GUESSED, '模拟器代码里有这个名字'
        else:
            state, why = TODO, '模拟器代码里没有这个名字'
        items.append(dict(part=MODULE, name=f'{group}/{mtype}', uses=v['campaign'], all=v['templates'], state=state,
                          why=why, eg=', '.join(v.get('examples', [])[:2])))
    return items


def nugget_items():
    import retailmodules
    import simcoverage
    code = simcoverage.sim_code()
    items = []
    for ntype, v in retailmodules.weapon_census().items():
        hit = any(ntype in s for s in code)
        items.append(dict(part=NUGGET, name=ntype, uses=v['weapons'], state=GUESSED if hit else TODO,
                          why='模拟器代码里有这个名字' if hit else '模拟器代码里没有这个名字',
                          eg=', '.join(v.get('examples', [])[:2])))
    return items


CHECKS = os.path.join(HERE, 'checks')
ENGINE_DOCS = os.path.join(ROOT, 'docs', 'engine')


def bench_sources():
    """[(source, text)] where bench measurements live: the engine probes (checks/engine_*.py, run with cnv_check on the
    bench, their readings in the docstrings) and the lines of docs/engine/*.md marked measured (**测**, not 未实测)."""
    need(CHECKS, 'the bench checks')
    need(ENGINE_DOCS, 'the engine docs')
    out = []
    for f in sorted(os.listdir(CHECKS)):
        if f.startswith('engine_') and f.endswith('.py'):
            out.append((f'checks/{f}', open(os.path.join(CHECKS, f), encoding='utf-8').read()))
    for f in sorted(os.listdir(ENGINE_DOCS)):
        if f.endswith('.md') and f != os.path.basename(OUT):
            lines = [x for x in open(os.path.join(ENGINE_DOCS, f), encoding='utf-8')
                     if '测' in x.replace('未实测', '').replace('推断', '') and '未实测' not in x]
            out.append((f'docs/engine/{f}', ''.join(lines)))
    if not out:
        raise SystemExit('inventory: no bench sources found')
    return out


def benched(items):
    """An implemented item (推断) whose name a bench source names becomes 已对拍, citing the first such source."""
    src = bench_sources()
    for it in items:
        if it['state'] not in (GUESSED, TODO):
            continue
        name = it['name'].split('/')[-1].split(':')[-1] if it['part'] == MODULE else it['name'].split(':')[-1]
        rx = re.compile(r'(?<![A-Za-z0-9_])' + re.escape(name) + r'(?![A-Za-z0-9_])')
        hit = next((s for s, text in src if rx.search(text)), None)
        if hit and it['state'] == GUESSED:
            it['state'], it['why'] = BENCHED, f'{it["why"]}；台上量过：{hit}'
        elif hit and it['part'] in (MODULE, NUGGET):       # measured, but the name rule finds no code: look (NOTES)
            it['why'] = f'{it["why"]}；**待核**：台上量过（{hit}），可能用别的名字实现了'
    return items


def apply_registers(items):
    benched(items)
    for it in items:
        k = (it['part'], it['name'])
        if k in NOTES:
            it['state'], it['why'] = NOTES[k]
        if k in BENCHED_TESTS:
            it['state'], it['why'] = BENCHED, BENCHED_TESTS[k]
    return items


def collect(parts=PARTS):
    items = []
    if ACTION in parts or CONDITION in parts:
        items += [i for i in script_items() if i['part'] in parts]
    if MODULE in parts:
        items += module_items()
    if NUGGET in parts:
        items += nugget_items()
    return apply_registers(items)


def order(items):
    return sorted(items, key=lambda i: (PARTS.index(i['part']), -i['uses'], -i.get('all', 0), i['name']))


def render(items):
    by = collections.defaultdict(list)
    for it in order(items):
        by[it['part']].append(it)
    out = ['# 原版功能总清单（引擎 A：脚本层、物体模块、武器效果）', '',
           '由 `experimental/cnv/inventory.py` 从原版数据生成，**别手改**；`tests/test_inventory.py` 在它过期时变红。'
           '状态与判定规则见脚本 docstring（ADR 0026）。用量：脚本 = 原版战役脚本里出现的次数；模块 = 原版战役地图里摆了的、'
           '用到它的物体种数（括号里是全部物体种数）；武器效果 = 用到它的原版武器数。', '',
           '| 部分 | 项数 | 已对拍 | 推断 | 未做 | 不涉及 | 按用量已有（已对拍+推断） |', '|---|---|---|---|---|---|---|']
    for part in PARTS:
        xs = by.get(part, [])
        if not xs:
            continue
        c = collections.Counter(i['state'] for i in xs)
        rel = [i for i in xs if i['state'] != NA]
        w = sum(i['uses'] for i in rel) or 1
        done = sum(i['uses'] for i in rel if i['state'] in (BENCHED, GUESSED))
        out.append(f'| {part} | {len(xs)} | {c[BENCHED]} | {c[GUESSED]} | {c[TODO]} | {c[NA]} | {100 * done / w:.0f}% |')
    for part in PARTS:
        xs = by.get(part, [])
        if not xs:
            continue
        out += ['', f'## {part}', '', '| 状态 | 名字 | 用量 | 说明 |', '|---|---|---|---|']
        for i in xs:
            n = f"{i['uses']}" + (f" ({i['all']})" if 'all' in i else '')
            why = i['why'] + (f"；例：{i['eg']}" if i.get('eg') else '')
            out.append(f"| {i['state']} | `{i['name']}` | {n} | {why} |")
    return '\n'.join(out) + '\n'


def gaps(items, k=20):
    """The k most used items not done, across the parts."""
    return sorted((i for i in items if i['state'] == TODO), key=lambda i: (-i['uses'], i['name']))[:k]


def main():
    check = '--check' in sys.argv
    items = collect()
    text = render(items)
    old = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
    if check:
        print('inventory: up to date' if old == text else 'inventory: STALE (run experimental/cnv/inventory.py)')
        return 0 if old == text else 1
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print('\n'.join(text.splitlines()[4:4 + 2 + len(PARTS)]))
    print('top gaps:')
    for i in gaps(items):
        print(f"  {i['part']} {i['name']} {i['uses']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
