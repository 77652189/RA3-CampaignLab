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
simai.py): a first cut, "read" is not "acts on" -- NOTES corrects it; 未做 -- not there; 已对拍 -- an implemented item
whose last word a measured (测) line of docs/engine/ai*.md or a checks/engine_ai*.py names (generic words excluded),
or the BENCHED register.
"""
import collections
import os
import re
import xml.etree.ElementTree as ET

import labpaths

AI_DATA = os.path.join(labpaths.SDK3, 'SageXML', 'SkirmishAI')
AI_CODE = [os.path.join(labpaths.ENGINE_MODEL, 'ra3model', 'ai'), os.path.join(os.path.dirname(__file__), 'simai.py')]
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
BENCHED_REG = {}
# name -> (state, why): where the name rule is wrong (read but switched off, read under another name ...)
NOTES = {
    '组队招人/TeamTemplate.SortByDistance': (GUESSED, 'AI 模型代码里读了这个名字（台上没单独量：engine_aiskirm 里是推测）'),
    '组队招人/CreateUnits.MinUnits': (GUESSED, 'AI 模型代码里读了这个名字（台上量的是 TeamTemplate.MinUnits，不是现造兵）'),
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
            tag = _local(el.tag)
            if tag in SKIP_TAGS:
                continue
            heur = tag.endswith('Heuristic') and tag not in GROUP
            group = HEURISTIC_GROUP if heur else GROUP.get(tag)
            if tag in PRESENTATION_TAGS:
                group = '表现'
            if el.text and el.text.strip() and not el.attrib:           # IncludeThing / ExcludeThing / Side lists
                ptag = _local(parent[el].tag) if el in parent else ''
                add(f'{GROUP.get(ptag, HEURISTIC_GROUP if ptag.endswith("Heuristic") else "其他")}/{ptag}.{tag}',
                    GROUP.get(ptag, HEURISTIC_GROUP))
                continue
            if group is None:
                group = '其他'
            if heur:
                add(f'{group}/{tag}', group)
            for a, v in el.attrib.items():
                a = _local(a)
                if a in SKIP_ATTRS:
                    continue
                add(f'{group}/{tag}.{a}', group)
                if (tag, a) in SELECTORS:
                    for word in v.split():
                        add(f'{group}/{tag}.{a}={word}', group)
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
