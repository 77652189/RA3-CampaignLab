r"""The AI part of the retail feature inventory (ADR 0026; the engine B line's share): everything the retail skirmish AI
data can tell the AI to do, each item with a state, by how often the retail data says it. Called by inventory.py, which
puts the items into docs/engine/inventory.md as the last part; never written by hand.

Source: every xml under the SDK's SageXML/SkirmishAI (65 files: personalities, strategic / build / budget states, opening
moves, target heuristics, micro managers, army definitions, AIData). The retail campaign's own AI states (AITarget_*,
the mission personalities) live there too, so they count. Items, named <组成项>/<what>:
  field     <Tag>.<Attr>         every attribute the retail data sets (and the text lists <Parent>.IncludeThing ...),
                                 uses = how many elements set it
  kind      <Tag>                every heuristic element type the retail data uses (ConstantHeuristic, EnemyNearby...)
  value     <Tag>.<Attr>=<Value> every value of a selector attribute (SELECTORS: a tactic type, an end behaviour ...)
Left out: bookkeeping (ids, inheritance, includes). 不涉及: speech / video / greeting feedback and AIData's drawing knobs.

States: 推断 -- the name is a quoted string in the AI model (the private engine model's ra3model/ai/*.py, or the public
simai.py, simtech.py for the protocol lottery): a first cut, "read" is not "acts on" -- NOTES corrects it; 未做 -- not there; 已对拍 -- an implemented item
whose last word a measured (测) line of docs/engine/ai*.md or a checks/engine_ai*.py names (generic words excluded),
or the BENCHED register.
"""
import collections
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]
import labpaths                                 # noqa: E402

AI_DATA = os.path.join(labpaths.SDK3, 'SageXML', 'SkirmishAI')
AI_CODE = [os.path.join(labpaths.ENGINE_MODEL, 'ra3model', 'ai'), os.path.join(os.path.dirname(__file__), 'simai.py'),
           os.path.join(os.path.dirname(__file__), 'simtech.py')]
PART = 'AI'
BENCHED, GUESSED, TODO, NA = '已对拍', '推断', '未做', '不涉及'

GROUP = {   # tag -> 组成项 (the parts of the retail AI)
    'AIStrategicStateDefinition': '战略状态', 'StrategicState': '战略状态', 'TargetHeuristic': '战略状态',
    'Tactic': '战术', 'TeamTemplate': '组队招人', 'CreateUnits': '组队招人', 'ObjectFilter': '组队招人',
    'AITargetingHeuristic': '目标', 'AIMicroManagerData': '微操', 'IgnoreTargets': '微操',
    'SpecificSpecialPowerDelay': '微操', 'SkirmishOpeningMove': '开局', 'Order': '开局', 'OpeningMove': '开局',
    'AIBuildStateDefinition': '造兵', 'BuildEntry': '造兵', 'BuildState': '造兵', 'BlockIfThingNearFactory': '造兵',
    'CountAsStructureForBuildPurposesFilter': '造兵', 'AIBudgetStateDefinition': '经济', 'BudgetState': '经济',
    'AccountShare': '经济', 'ResourceMultiplierCheat': '经济', 'AIPersonalityDefinition': '人格',
    'PowerChoice': '人格', 'SpecificUnitCap': '人格', 'UnitCap': '人格', 'UnitModifier': '人格',
    'PersonalityMap': '人格', 'BaseSelection': '人格', 'RetreatBaseCriteria': '人格',
    'DefaultTacticHomeBaseCriteria': '人格', 'EnemyFilter': '人格', 'Filter': '人格',
    'ArmyDefinition': '阵营', 'AIData': '全局常量'}
HEURISTIC_GROUP = '启发条件'          # the heuristic element types and their fields
SKIP_TAGS = {'AssetDeclaration', 'Tags', 'Includes', 'Include', 'AIStrategicStateName', 'Heuristic', 'Budget',
             'ObjectFilterAsset'}
SKIP_ATTRS = {'id', 'inheritFrom', 'joinAction'}
PRESENTATION_TAGS = {'FeedbackEntry', 'StrategicDirectiveFeedback', 'SkirmishGameEventFeedback',
                     'InTroubleSkirmishFeedbackControl'}
PRESENTATION_ATTR = re.compile(r'(Feedback|Portrait|UIName|Greeting|Tree|Camera|Crater|Forest|Video|EvaEvent)')
SELECTORS = {('Tactic', 'Tactic'), ('Tactic', 'EndBehavior'), ('AITargetingHeuristic', 'HeuristicType'),
             ('AITargetingHeuristic', 'SortType'), ('TeamTemplate', 'ReleaseType'), ('TeamTemplate', 'Priority'),
             ('AIStrategicStateDefinition', 'PathfindingCheckType'), ('BaseSelection', 'SortOrder'),
             ('AccountShare', 'Account'), ('SpecificSpecialPowerDelay', 'TogglePowerSubType')}
# an element the model names by its xsd type instead of its tag
OWNER_ALIASES = {t: (t, 'AIBaseSelectionCriteria') for t in ('BaseSelection', 'RetreatBaseCriteria',
                                                             'DefaultTacticHomeBaseCriteria')}
# words too common to say a bench line measured this item
GENERIC = {'Distance', 'Priority', 'Value', 'Above', 'Rule', 'Include', 'Exclude', 'Relationship', 'Location', 'Name',
           'Time', 'Weight', 'Difficulty', 'State', 'Build', 'Account', 'Score', 'Type', 'Side', 'Unit', 'Cap',
           'Exists', 'Tactic', 'Land', 'Water', 'Point', 'Team', 'Random', 'Upgrade', 'Deposit', 'Percentage',
           'Budget', 'Surface', 'Event', 'Target', 'Beacon', 'KindOf', 'Engineer'}

# name -> source (a docs/engine/ai*.md section or a test) where the auto rule misses a bench comparison
BENCHED_REG = {'人格/PowerChoice.Weight': 'docs/engine/aiopen.md#买协议（aipwrb 权重 0 的不买）',
              '组队招人/TeamTemplate.AllowedLocomotorTypes': 'docs/engine/aistate.md#移动方式和对象集（第 81 轮）',
              '组队招人/TeamTemplate.RegisteredObjectSet': 'docs/engine/aistate.md#移动方式和对象集（第 81 轮）',
              '组队招人/ObjectFilter.Rule': 'docs/engine/aistate.md#队伍招谁（aitfany / aitfnone / aitfall：ANY、NONE + 名单只要名单，ALL + 排除名单）',
              '战略状态/StrategicState.Difficulty': 'docs/engine/aistate.md#按难度挂的状态（aidiff / aidiffx：普通 = MEDIUM，没挂 MEDIUM 的状态不跑）',
              '开局/Order.Time': 'docs/engine/aiopen.md#开局里的 Time 从什么时候算（aiotime：从唤醒起的绝对时刻）',
              '开局/Order.Build': 'docs/engine/aiopen.md#读数（aiopen f1～f3：造的顺序和 AlliedStandard 单子一样）',
              '战略状态/StrategicState.State': 'docs/engine/aistate.md#读数（人格只留台上写的状态，AI 只跑这些：aistateconst / aistateslash 等）',
              '战略状态/TargetHeuristic.TargetHeuristic': 'docs/engine/aitactics.md#读数（aitargetnear / aitargetsafe：按状态写的目标启发挑楼）',
              '战术/Tactic.Tactic': 'docs/engine/aitactics.md#读数（SimpleAttack / DefenseAvoidanceAttack / FlankAttack / StaticDefense 上台）',
              '目标/AITargetingHeuristic.HeuristicType': 'docs/engine/aitactics.md#读数（ClosestStructure / SafestToGroundStructure 是 EnemyStructure，FriendlyLandStructure 是 FriendlyStructure，都上台）',
              '目标/AITargetingHeuristic.HeuristicType=EnemyStructure': 'docs/engine/aitactics.md#读数（ClosestStructureHeuristic、SafestToGroundStructureHeuristic：aitargetnear / aitargetsafe）',
              '战略状态/TargetHeuristic.Priority': 'docs/engine/aitactics.md#目标挑哪个（aitpphi / aitpplo：同一状态两条目标启发，Priority 高的先试，两向都上台）',
              '目标/AITargetingHeuristic.SortType': 'docs/engine/aitactics.md#目标挑哪个（Distance：aitpnear / aitpmt2 最近、次近；ThreatToGround：aitargetsafe）',
              '目标/AITargetingHeuristic.SortType=Distance': 'docs/engine/aitactics.md#目标挑哪个（aitpnear 挑最近、aitpmt2 第二槽挑次近、aitpvk 显式写 Distance）',
              '目标/AITargetingHeuristic.HeuristicType=FriendlyStructure': 'docs/engine/aitactics.md#读数（FriendlyLandStructureHeuristic：engine_aidefense 守自家建造厂）'}
# name -> (state, why): where the name rule is wrong (read but switched off, read under another name ...)
NOTES = {
    '组队招人/TeamTemplate.SortByDistance': (GUESSED, 'AI 模型代码里读了这个名字（台上没单独量：engine_aiskirm 里是推测）'),
    '组队招人/CreateUnits.MinUnits': (GUESSED, 'AI 模型代码里读了这个名字（台上量的是 TeamTemplate.MinUnits，不是现造兵）'),
    '微操/AIMicroManagerData.PullbackInjured': (BENCHED, '只认车能开进去的维修设施：苏联 AI + 吊车，残血坦克回去被回收（aipullsov PASS）；盟军 / 日本工厂找不到（aiteamstate.md 第 6 节）'),
    '微操/AIMicroManagerData.PullbackInjuredHealthPct': (GUESSED, '30% 低于 0.35 时苏联坦克会撤（aipullsov），阈值边界没量'),
    '微操/AIMicroManagerData.ReverseMove': (GUESSED, '推断（台上未复现）：锤子 airev / airevp / airevt 都不倒车；剩门队员有没有当前攻击目标，量法见 handoff-b 第 73 节'),
    '组队招人/TeamTemplate.AlwaysRecruit': (GUESSED,'读了，出发后继续招人的门默认关（防御队吸兵和台上对不上，handoff-b 第 50、51 节）'),
}


def need(path, what):
    if not os.path.exists(path):
        raise SystemExit(f'inventory_ai: {what} not found: {path}')


def _local(tag):
    return tag.split('}')[-1]


def census():
    """{name: [uses, group]} over the retail SkirmishAI xml."""
    need(AI_DATA, 'the SDK SkirmishAI data')
    files = [os.path.join(r, f) for r, _, fs in os.walk(AI_DATA) for f in fs if f.endswith('.xml')]
    if not files:
        raise SystemExit(f'inventory_ai: no xml in {AI_DATA}')
    out = {}

    def add(name, group):
        out.setdefault(name, [0, group])[0] += 1

    for path in sorted(files):
        tree = ET.parse(path)
        parent = {c: p for p in tree.iter() for c in p}
        for el in tree.iter():
            for name, group in element_names(el, parent.get(el)):
                add(name, group)
    return out


def element_names(el, par):
    """The items one element of the AI data writes: [(name, group)] (par = its parent element, or None)."""
    tag = _local(el.tag)
    if tag in SKIP_TAGS:
        return []
    heur = tag.endswith('Heuristic') and tag not in GROUP
    group = HEURISTIC_GROUP if heur else GROUP.get(tag)
    if tag in PRESENTATION_TAGS:
        group = '表现'
    if el.text and el.text.strip() and not el.attrib:           # IncludeThing / ExcludeThing / Side lists
        ptag = _local(par.tag) if par is not None else ''
        return [(f'{GROUP.get(ptag, HEURISTIC_GROUP if ptag.endswith("Heuristic") else "其他")}/{ptag}.{tag}',
                 GROUP.get(ptag, HEURISTIC_GROUP))]
    if group is None:
        group = '其他'
    out = [(f'{group}/{tag}', group)] if heur else []
    for a, v in el.attrib.items():
        a = _local(a)
        if a in SKIP_ATTRS:
            continue
        out.append((f'{group}/{tag}.{a}', group))
        if (tag, a) in SELECTORS:
            out += [(f'{group}/{tag}.{a}={word}', group) for word in v.split()]
    return out


def ai_code():
    for p in AI_CODE:
        need(p, 'the AI model code (private engine model ra3model/ai, public simai.py)')
    files = [os.path.join(AI_CODE[0], f) for f in sorted(os.listdir(AI_CODE[0])) if f.endswith('.py')] + AI_CODE[1:]
    return '\n'.join(open(f, encoding='utf-8').read() for f in files)


def last_word(name):
    tail = name.split('/', 1)[1]
    return tail.split('=')[-1] if '=' in tail else tail.split('.')[-1]


def owner(name):
    """The element a field or value belongs to (it must be in the code too: Distance read for a Tactic is not
    EnemyNearbyHeuristic's Distance); None for a heuristic kind (the word is the element)."""
    tail = name.split('/', 1)[1].split('=')[0]
    return tail.split('.')[0] if '.' in tail else None


def quoted(word, code):
    return re.search('[\'"]' + re.escape(word) + '[\'"]', code) is not None


def ai_items(bench_sources):
    """The AI items; bench_sources = inventory.bench_sources() ([(source, text)])."""
    code = ai_code()
    src = [(s, t) for s, t in bench_sources if re.match(r'(checks/engine_ai|docs/engine/ai(?!r))', s)]
    items = []
    for name, (n, group) in census().items():
        word = last_word(name)
        tag_attr = name.split('/', 1)[1].split('=')[0]
        if group == '表现' or (group != HEURISTIC_GROUP and PRESENTATION_ATTR.search(tag_attr)):
            state, why = NA, '纯表现（语音、视频、画面）'
        elif quoted(word, code) and (owner(name) is None or any(
                re.search(r'(?<![A-Za-z])' + o + r'(?![A-Za-z])', code) for o in OWNER_ALIASES.get(owner(name), (owner(name),)))):
            state, why = GUESSED, 'AI 模型代码里读了这个名字'
        else:
            state, why = TODO, 'AI 模型代码里没有这个名字'
        if state == GUESSED and word not in GENERIC and len(word) >= 5:
            rx = re.compile(r'(?<![A-Za-z0-9_])' + re.escape(word) + r'(?![A-Za-z0-9_])')
            hit = next((s for s, t in src if rx.search(t)), None)
            if hit:
                state, why = BENCHED, f'{why}；台上量过：{hit}'
        if name in NOTES:
            state, why = NOTES[name]
        if name in BENCHED_REG:
            state, why = BENCHED, BENCHED_REG[name]
        items.append(dict(part=PART, name=name, uses=n, state=state, why=why))
    return items


# ---- what our own levels' enemy AI uses (the "AI done" bar's first point: all of it 已对拍)
LEVELS = [f'a{k}' for k in range(1, 10)]          # the Allied 9 (experimental/cnv/missions/a1.py ...)
LEVELS_OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                          'docs', 'engine', 'inventory-levels.md')


def assets():
    """{id: element} of every top-level asset of the retail AI data."""
    need(AI_DATA, 'the SDK SkirmishAI data')
    out = {}
    for r, _, fs in os.walk(AI_DATA):
        for f in sorted(fs):
            if f.endswith('.xml'):
                for el in ET.parse(os.path.join(r, f)).getroot():
                    if el.get('id'):
                        out[el.get('id')] = el
    return out


CAMPAIGN_DIFFICULTIES = {'EASY', 'MEDIUM', 'HARD'}      # the campaign's three (plan.py LEVELS); BRUTAL is skirmish's


def _effective(el, index):
    """(the inheritFrom chain, the children in effect): a child's own children first; a parent's child whose id the
    child already gave (or removed with joinAction Remove) is left out, the way instance inheritance overrides."""
    chain, kids, ids = [], [], set()
    while el is not None and el not in chain:
        chain.append(el)
        for c in el:
            cid = c.get('id')
            if cid is not None:
                if cid in ids:
                    continue
                ids.add(cid)
                if any(_local(a) == 'joinAction' and v == 'Remove' for a, v in c.attrib.items()):
                    continue
            if c.get('Difficulty') and not set(c.get('Difficulty').split()) & CAMPAIGN_DIFFICULTIES:
                continue                     # a BRUTAL-only state or move: no campaign runs it
            kids.append(c)
        el = index.get(el.get('inheritFrom'))
    return chain, kids


def reached(roots, index):
    """{item name: group} over every asset the roots (elements) reach: down their inheritance and every attribute
    value or text naming another asset (a state, tactic, team, heuristic, micro manager, build or budget state ...)."""
    names, seen, todo = {}, set(), list(roots)
    while todo:
        el = todo.pop()
        if id(el) in seen:
            continue
        seen.add(id(el))
        chain, kids = _effective(el, index)
        els = [(c, None) for c in chain]
        for k in kids:
            par = {c: p for p in k.iter() for c in p}
            els += [(d, par.get(d, chain[0])) for d in k.iter()]
        for d, par in els:
            for name, group in element_names(d, par):
                names[name] = group
            words = [w for v in d.attrib.values() for w in v.split()] + ((d.text or '').split())
            for w in words:
                w = w.split(':')[-1]
                if w in index and id(index[w]) not in seen:
                    todo.append(index[w])
    return names


def level_ai(levels=LEVELS):
    """[(level, ai player, faction template, personality xml, [(action or condition, args)] on the AI player)] for
    the levels whose plan has an enemy AI (plan.py compile_ai)."""
    import importlib
    out = []
    for lv in levels:
        m = importlib.import_module(f'missions.{lv}').mission()
        for side, spec in m.sides.items():
            pid = spec.get('aiPersonality', '').split(':')[-1]
            xml = next((x for _, x, aid in m.assets if aid.endswith(':' + pid)), None)
            if not pid or xml is None:
                continue
            player = m.player(side)
            used = [(a[0], a[1:]) for s in m.scripts for a in list(s.when) + list(s.do)
                    if isinstance(a, tuple) and player in a[1:]]
            out.append((lv, player, spec['playerFaction'], xml, used))
    return out


def level_scope(levels=LEVELS):
    """{(part, name): set of levels}: the AI items (part AI) the levels' personalities reach, plus the script actions
    and conditions (inventory parts 脚本动作 / 脚本条件) their scripts aim at the AI player."""
    index = assets()
    glob = [el for el in index.values() if _local(el.tag) == 'AIData']
    scope = collections.defaultdict(set)
    for lv, player, faction, xml, used in level_ai(levels):
        root = ET.fromstring(xml.encode('utf-8'))
        mine = [el for el in root if el.get('id')]
        army = [el for el in index.values() if _local(el.tag) == 'ArmyDefinition' and el.get('Side') == faction]
        for name in reached(mine + army + glob, index):
            scope[(PART, name)].add(lv)
        for what, _ in used:
            scope[('?', what)].add(lv)
    return scope


def render_levels(items, scope):
    """docs/engine/inventory-levels.md from the inventory items and level_scope()."""
    by = {(i['part'], i['name']): i for i in items}
    rows = []
    for (part, name), lvs in scope.items():
        it = by.get((part, name)) or next((i for (p, n), i in by.items() if part == '?' and n == name), None)
        if it is None:
            continue                         # an action no inventory part lists (the map's own bookkeeping)
        rows.append((it, sorted(lvs)))
    order = {BENCHED: 3, GUESSED: 1, TODO: 0, NA: 4}
    rows.sort(key=lambda r: (order[r[0]['state']], r[0]['part'], -r[0]['uses'], r[0]['name']))
    live = [r for r in rows if r[0]['state'] != NA]
    done = sum(r[0]['state'] == BENCHED for r in live)
    count = collections.Counter((r[0]['part'], r[0]['state']) for r in live)
    parts = sorted({r[0]['part'] for r in live}, key=lambda p: (p != PART, p))
    lines = ['# 我们 9 关的敌方 AI 用到的清单项', '',
             '由 `experimental/cnv/inventory_ai.py levels` 生成，**别手改**。范围：9 关（`missions/a1.py`～`a9.py`）里由'
             '遭遇战 AI 带的敌人：它的人格（`enemy_ai.py` 生成）沿继承、战略状态、战术、组队、目标启发、微操、造兵 / 预算'
             '状态、开局一路引用到的原版 AI 数据项，加上全局常量 AIData 和本阵营的 ArmyDefinition；再加关卡脚本里点了 AI '
             '玩家名字的脚本动作 / 条件。状态取自 [inventory.md](inventory.md)。"AI 做完"的第一条：下表全部已对拍。', '',
             f'**已对拍 {done} / {len(live)}**（不涉及的不算）。用到敌方 AI 的关：'
             + '、'.join(sorted({lv for _, lvs in live for lv in lvs})) + '。', '',
             '| 部分 | 已对拍 | 推断 | 未做 |', '|---|---|---|---|']
    lines += [f'| {p} | {count[(p, BENCHED)]} | {count[(p, GUESSED)]} | {count[(p, TODO)]} |' for p in parts]
    total = sum(r[0]['uses'] for r in live) or 1
    pct = lambda states: round(100 * sum(r[0]['uses'] for r in live if r[0]['state'] in states) / total)  # noqa: E731
    lines += ['', f'按原版用量加权：已对拍 {pct({BENCHED})}%，已有（已对拍+推断）{pct({BENCHED, GUESSED})}%。']
    lines += ['', '| 状态 | 部分 | 项 | 原版用量 | 关 | 说明 |', '|---|---|---|---|---|---|']
    lines += [f'| {it["state"]} | {it["part"]} | `{it["name"]}` | {it["uses"]} | {" ".join(lvs)} | {it["why"]} |'
              for it, lvs in rows]
    return '\n'.join(lines) + '\n'


def main_levels(write=False):
    import inventory
    items = inventory.collect()
    text = render_levels(items, level_scope())
    if write:
        with open(LEVELS_OUT, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    print('\n'.join(text.splitlines()[4:12]))
    return text


if __name__ == '__main__':
    if sys.argv[1:2] == ['levels']:
        main_levels(write='--write' in sys.argv)
