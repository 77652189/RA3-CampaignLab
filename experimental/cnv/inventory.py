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
ACTION, CONDITION, MODULE, NUGGET, AI = '脚本动作', '脚本条件', '物体模块', '武器效果', 'AI'
PARTS = (ACTION, CONDITION, MODULE, NUGGET, AI)     # AI: engine B's part, its own rules in inventory_ai.py

# (part, name) -> 'tests/<file>.py::<test>': the bench comparison that backs the item (the guard checks the test exists)
BENCHED_TESTS = {
    (MODULE, 'Behaviors/OreMinerBehavior'): 'tests/test_simbench.py::test_mining_pays_8_a_frame_and_a_trip_takes_269',
    (MODULE, 'Behaviors/OreNodeBehavior'): 'tests/test_simbench.py::test_mining_a_second_miner_on_one_node_adds_nothing',
    # batch 1 (work/re/l2_scripts1.md, checks/engine_scripts1.py, bench 11-08)
    (CONDITION, 'PLAYER_IS_HUMAN_OR_AI_PERSONALITY'): 'tests/test_simbench.py::test_scripts1_conditions_as_the_bench',
    (CONDITION, 'UNIT_HAS_OBJECT_STATUS'): 'tests/test_simbench.py::test_scripts1_conditions_as_the_bench',
    (CONDITION, 'HAS_FINISHED_AUDIO'):
        'tests/test_simbench.py::test_audio_a_dubbed_line_is_done_its_length_after_it_is_heard',
    (CONDITION, 'HAS_FINISHED_VIDEO'):
        'tests/test_simbench.py::test_video_a_radar_clip_is_done_after_its_length_full_screen_never',
    (ACTION, 'TEAM_TRANSFER_TO_PLAYER'): 'tests/test_simbench.py::test_scripts1_a_team_handed_over_drops_its_move',
    (ACTION, 'PLAYER_RELATES_PLAYER'): 'tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back',
    (CONDITION, 'PLAYER_HAS_OBJECT_COMPARISON'): 'tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back',
    (ACTION, 'UNIT_IDLE_FOR_SECONDS'): 'tests/test_simbench.py::test_scripts1_idle_for_seconds_drops_the_move',
    # protocol points (simtech.py, checks/engine_protocol.py, bench 11-08)
    (ACTION, 'PLAYER_SET_MAX_PLAYER_POWER_POINTS'):
        'tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule',
    (ACTION, 'PLAYER_SET_PLAYER_POWER_POINTS'):
        'tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule',
    (ACTION, 'PLAYER_LOCK_PLAYER_TECH'): 'tests/test_simbench.py::test_protocol_a_computer_player_spends_unless_locked',
    (CONDITION, 'PLAYER_HAS_COMPARISON_POWER_POINTS'):
        'tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule',
    (CONDITION, 'PLAYER_HAS_PLAYER_TECH'): 'tests/test_simbench.py::test_protocol_rank_two_at_frame_5400',
}

# (part, name) -> (state, why): where the name rule above is wrong (a module read under another name ...)
_NOT_IN_SIM = '已核（11-08）：模拟器没有这个效果'
NOTES = {
    (MODULE, 'Body/ActiveBody'): (GUESSED, 'simunits.stats 读 MaxHealth（只有生命值；受伤状态、回血等另算）'),
    (MODULE, 'AI/AIUpdate'): (GUESSED, 'Sim.fight / 移动（单位 AI 的状态机细项按引擎 B 的 AI 清单推进）'),
    # the 26 the bench measured but the name rule called 未做 (checked 11-08 against sim.py / simunits.py)
    (MODULE, 'Behaviors/DestroyDie'): (GUESSED, 'Sim.destroy：死了当帧移出（LINGER 0，台上 death 探针量过）；'
                                                'DeathTypes 筛选、几个 Die 模块选哪个没读'),
    (MODULE, 'Behaviors/FireWeaponUpdate'): (GUESSED, '部分：simunits.ocl_round 把召出物的 FireWeaponNugget + '
                                                      'LifetimeUpdate 折成伤害，不模拟召出物本身'),
    (MODULE, 'Behaviors/SlowDeath'): (TODO, f'{_NOT_IN_SIM}（死了立即移出，没有慢死、倒塌延迟）'),
    (MODULE, 'Behaviors/BuildingBehavior'): (TODO, f'{_NOT_IN_SIM}（没有出售建筑）'),
    (MODULE, 'Behaviors/StructureSellUpdate'): (TODO, f'{_NOT_IN_SIM}（没有出售、返还金钱）'),
    (MODULE, 'Behaviors/InvisibilityBehavior'): (TODO, f'{_NOT_IN_SIM}（没有隐身）'),
    (MODULE, 'Behaviors/InvisibilityBroadcastUpdate'): (TODO, f'{_NOT_IN_SIM}（没有隐身）'),
    (MODULE, 'Behaviors/StealthDetectorUpdate'): (TODO, f'{_NOT_IN_SIM}（没有反隐）'),
    (MODULE, 'Behaviors/ContestableGarrisonContain'): (TODO, f'{_NOT_IN_SIM}（没有驻军）'),
    (MODULE, 'Behaviors/GarrisonContain'): (TODO, f'{_NOT_IN_SIM}（没有驻军；NAMED_GARRISON_SPECIFIC_BUILDING 另算）'),
    (MODULE, 'Behaviors/StancesBehavior'): (TODO, f'{_NOT_IN_SIM}（没有姿态）'),
    (MODULE, 'Behaviors/AutoHealBehavior'): (TODO, f'{_NOT_IN_SIM}（没有自动回血）'),
    (MODULE, 'Behaviors/RunOffMapBehavior'): (TODO, f'{_NOT_IN_SIM}（没有逃离地图）'),
    (MODULE, 'Behaviors/ToggleStatusSpecialAbilityUpdate'): (TODO, f'{_NOT_IN_SIM}（没有按钮切换状态）'),
    (MODULE, 'Behaviors/ReplaceSelfSpecialAbility'): (TODO, f'{_NOT_IN_SIM}（没有换形态）'),
    (MODULE, 'Behaviors/SpawnBehavior'): (TODO, f'{_NOT_IN_SIM}（没有母体造随从）'),
    (MODULE, 'Behaviors/SlavedUpdate'): (TODO, f'{_NOT_IN_SIM}（没有随从跟随）'),
    (MODULE, 'Behaviors/BezierProjectile'): (TODO, f'{_NOT_IN_SIM}（开火按每秒伤害直接扣血，没有弹体）'),
    (MODULE, 'Behaviors/ProjectileUpdate'): (TODO, f'{_NOT_IN_SIM}（开火按每秒伤害直接扣血，没有弹体飞行时间）'),
    (MODULE, 'Behaviors/AttachUpdate'): (TODO, f'{_NOT_IN_SIM}（没有附着）'),
    (MODULE, 'Behaviors/StoreObjectsSpecialPower'): (TODO, f'{_NOT_IN_SIM}（没有存放单位）'),
    (MODULE, 'Behaviors/TeleportStoredObjectsSpecialPower'): (TODO, f'{_NOT_IN_SIM}（没有传送存放的单位）'),
    (MODULE, 'Behaviors/TeleportStoredObjectsUpdate'): (TODO, f'{_NOT_IN_SIM}（UNIT_TELEPORT_TO_WAYPOINT 另算）'),
    (NUGGET, 'ActivateLaserNugget'): (TODO, f'{_NOT_IN_SIM}（没有激光束）'),
    # batch 1 (work/re/l2_scripts1.md, checks/engine_scripts1.py, bench 11-08)
    (ACTION, 'UNIT_IDLE_FOR_FRAMECOUNT'): (GUESSED, 'Sim.stand：和 UNIT_IDLE_FOR_SECONDS 同一个处理函数，'
                                                     '秒版台上量过（命令清掉，不是暂停）'),
    (ACTION, 'TEAM_HUNT'): (GUESSED, '没交给 AI 的玩家（含玩家自己）：不动，台上量过（engine_scripts1 hunt 60 s）；'
                                     'AI 玩家的 HuntTactic 不模拟（引擎 B），碰到记 Sim.unmodeled'),
    (ACTION, 'NAMED_HUNT'): (GUESSED, '同 TEAM_HUNT：没交给 AI 不动（台上量过）；AI 玩家的猎杀不模拟（引擎 B）'),
    (ACTION, 'UNIT_AI_TRANSFER'): (GUESSED, '程序读到：人类玩家的单位无效、不清命令；交给 AI 后的行为归引擎 B，'
                                            '碰到记 Sim.unmodeled（台上没量）'),
    (ACTION, 'TEAM_AI_TRANSFER'): (GUESSED, '同 UNIT_AI_TRANSFER，对队里每个成员（台上没量）'),
    # engine A round 106: judged by what reads them
    (ACTION, 'UNIT_SET_MODELCONDITION_GENERIC'): (NA, '纯表现：设模型状态只换画法。原版脚本设的是 SUPPRESSED（a01 '
                                                      '摆拍枪战的趴下动作），SDK 数据里读 SUPPRESSED 的只有绘制模块的 '
                                                      'ConditionsYes；我们 a7 设的 USER_1 只有自由号的充能画法读'),
    (ACTION, 'UNIT_CLEAR_MODELCONDITION'): (NA, '纯表现：同 UNIT_SET_MODELCONDITION_GENERIC，清掉画法状态'),
    (MODULE, 'Behaviors/ObjectSMCHelper'): (NA, '纯表现：《将军》ObjectSMCHelper 到时清掉"定时模型状态"'
                                                '（UNIT_SET_MODELCONDITION_GENERIC 的秒数），只换画法'),
    (MODULE, 'Behaviors/AttributeModifierPoolUpdate'): (GUESSED, 'Sim.modify：属性修正挂在这个池里，到期规则'
                                                                 '（到期帧 >= 即失效、再挂覆盖不叠加）读自程序，'
                                                                 'work/re/l2_ability.md 第 51 轮'),
    (ACTION, 'SET_COOP_AI_COMMAND_UI_ENABLED'): (NA,'纯界面：开关玩家给盟友 AI 下令的按钮；模拟器的玩家没有给盟友'
                                                     '下令的命令，开关无从起作用（以后加了这个命令再算）'),
    # engine A round 107: the freeze; what the front modules are, read in the SDK data
    (MODULE, 'Behaviors/SecondaryDamageTracker'): (GUESSED, 'Sim.chill（ALIGN freeze）：冷冻光束的冷冻值累计、每秒'
                                                            '消散、按生命值分档减速、满档冻住（CryoBeamFrozenArmor '
                                                            '90000%，一碰就碎）；规则读自 SDK 数据，程序和台上都没对'),
    (NUGGET, 'SecondaryDamageNugget'): (GUESSED, 'simunits._weapons 读 Amount（不要升级的那条）→ sdps，Sim.chill'),
    (MODULE, 'Body/PropBody'): (TODO, '弹体和特效道具的身体（9 关 22 个模板里 16 个是弹体）：模拟器没有弹体'
                                      '（同 BezierProjectile），道具能不能挨打没读'),
    (MODULE, 'Behaviors/SquishCollide'): (TODO, '碾压步兵：模拟器没有碾压（坦克压过步兵不死）；影响玩法，没做'),
    (MODULE, 'Behaviors/Physics'): (TODO, '移动物理（坠落、弹跳、被击飞、倾倒）：模拟器走路按速度直走，没有物理'),
    # engine A round 108: read in the SDK data
    (MODULE, 'Behaviors/ObjectDefectionHelper'): (NA, '没人触发：原版只在 BaseObject 挂一个空的（所以每个物体都有），'
                                                      'SageXML 里没有一处 DefectorSpecialPower，脚本动作表里也没有'
                                                      '叛变；《将军》里它管"叛变后一段时间不被发现"'),
    (MODULE, 'Behaviors/BuildingDestructionBehavior'): (NA, '纯表现：建筑死后按骨骼放特效、甩碎块（CreationObject '
                                                            '如 AlliedBarracks_Debris：只有画法、寿命和碎片体积，'
                                                            '没有身体和武器）、烟尘'),
    (MODULE, 'Behaviors/ToppleUpdate'): (TODO, '倒伏：车压过的灯笼、栏杆、路灯倒下即死（OK_Lantern01 '
                                              'KillWhenStartToppled）。模拟器没有碾压（同 SquishCollide）：'
                                              'OK_LANTERN01 在模拟器里不是物体（不挡路），platprops.STRUCTURE 里的'
                                              '栏杆路灯是永久障碍（游戏里车能压倒）；跟碾压一起做'),
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
    items = apply_registers(items)
    if AI in parts:                                 # engine B: its own state rules and registers (inventory_ai.py)
        import inventory_ai
        items += inventory_ai.ai_items(bench_sources())
    return items


def order(items):
    return sorted(items, key=lambda i: (PARTS.index(i['part']), -i['uses'], -i.get('all', 0), i['name']))


def render(items):
    by = collections.defaultdict(list)
    for it in order(items):
        by[it['part']].append(it)
    out = ['# 原版功能总清单（引擎 A：脚本层、物体模块、武器效果；引擎 B：AI）', '',
           '由 `experimental/cnv/inventory.py` 从原版数据生成，**别手改**；`tests/test_inventory.py` 在它过期时变红。'
           '状态与判定规则见脚本 docstring（ADR 0026）。用量：脚本 = 原版战役脚本里出现的次数；模块 = 原版战役地图里摆了的、'
           '用到它的物体种数（括号里是全部物体种数）；武器效果 = 用到它的原版武器数；'
           'AI = 原版 AI 数据（SDK SkirmishAI，含战役关的 AI 状态）里写它的次数，判定规则见 `inventory_ai.py`。', '',
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
