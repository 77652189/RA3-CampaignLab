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
whose last word a checks/engine_ai*.py a test runs names (generic words excluded; of a probe of several checks, the
check that names it, inventory.probe_parts; a line saying it was not measured does not count, inventory.measured), or
the BENCHED register. Named only by a probe no test runs, or a measured (测) line of docs/engine/ai*.md: 推断, 台上量过.
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
              '组队招人/TeamTemplate.Priority': 'docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮）',
              '组队招人/TeamTemplate.Priority=STANDARD': 'docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮）',
              '组队招人/TeamTemplate.Priority=LOW': 'docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮）',
              '组队招人/TeamTemplate.Priority=HIGH': 'docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮）',
              '组队招人/TeamTemplate.MinPowerAdvantage': 'docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮）',
              **{f'造兵/BlockIfThingNearFactory.{k}': 'tests/test_simai_bench_b.py::test_a_thing_near_the_factory_'
                 'blocks_the_entry（engine_aiskirm y aiskblkn / aiskblkr：Rule ANY + Relationship NEUTRAL 挡住，'
                 'aiskblkf 400 外不挡；ENEMIES 走同一段代码没单独上台；B 第 149 轮）' for k in ('Relationship', 'Rule')},
              '人格/AIPersonalityDefinition.PersonalityType': 'tests/test_simai_bench_b.py::test_the_personality_'
                 'condition_matches_the_id_not_the_personality_type（engine_aiskirm pt aiskpt / aiskpti：脚本条件 '
                 'PLAYER_IS_HUMAN_OR_AI_PERSONALITY 只认人格 id，PersonalityType 写成别的名字或不写都不影响；'
                 'AI 行为不读它；B 第 150 轮）',
              '组队招人/ObjectFilter.Rule':'docs/engine/aistate.md#队伍招谁（aitfany / aitfnone / aitfall：ANY、NONE + 名单只要名单，ALL + 排除名单）',
              '战略状态/StrategicState.Difficulty': 'docs/engine/aistate.md#按难度挂的状态（aidiff / aidiffx：普通 = MEDIUM，没挂 MEDIUM 的状态不跑）',
              **{f'启发条件/{k}': 'docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮）'
                 for k in ('TimerHeuristic', 'TimerHeuristic.StartTime', 'TimerHeuristic.EndTime',
                           'TimerHeuristic.CountFrom', 'IntervalHeuristic', 'IntervalHeuristic.IntervalTime',
                           'IntervalHeuristic.ActiveTime', 'EnemyNearbyHeuristic', 'EnemyNearbyHeuristic.Distance',
                           'EnemyNearbyHeuristic.EnemyNearby', 'ObjectOfTypeExistsHeuristic',
                           'ObjectOfTypeExistsHeuristic.PassIfExists')},
              '组队招人/ObjectFilter.Relationship': 'docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮）',
              '开局/Order.Time':'docs/engine/aiopen.md#开局里的 Time 从什么时候算（aiotime：从唤醒起的绝对时刻）',
              '开局/Order.Build': 'docs/engine/aiopen.md#读数（aiopen f1～f3：造的顺序和 AlliedStandard 单子一样）',
              **{f'开局/{k}': f'docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（{v}）'
                 for k, v in (('OpeningMove.Weight', 'aiowt / aiowt2：0% 永远抽不到'),
                              ('OpeningMove.Difficulty', 'aiodf / aiodf2：只留 MEDIUM 的'),
                              ('OpeningMove.Name', '每个探针按名字挂自写开局，都照它造'),
                              ('Order.Deposit', 'aiom15：带 Deposit 2000 照造、晚 4 秒'))},
              '开局/Order.Account': 'docs/engine/aiopen.md#开局存款进哪个账户（Order Account，第 116 轮）（aiskacp / aiskacd：PRODUCTION 兵营出兵、DEFENSE 兵营不出）',
              '战略状态/StrategicState.State': 'docs/engine/aistate.md#读数（人格只留台上写的状态，AI 只跑这些：aistateconst / aistateslash 等）',
              '战略状态/TargetHeuristic.TargetHeuristic': 'docs/engine/aitactics.md#读数（aitargetnear / aitargetsafe：按状态写的目标启发挑楼）',
              '战术/Tactic.Tactic': 'docs/engine/aitactics.md#读数（SimpleAttack / DefenseAvoidanceAttack / FlankAttack / StaticDefense 上台）',
              '目标/AITargetingHeuristic.HeuristicType': 'docs/engine/aitactics.md#读数（ClosestStructure / SafestToGroundStructure 是 EnemyStructure，FriendlyLandStructure 是 FriendlyStructure，都上台）',
              '目标/AITargetingHeuristic.Name': 'docs/engine/ainamed.md#给关卡线的结论（ainmfar 点名物件不管远近、ainmwp 走到路点守着、ainmnone 名字查不到不派队，全 PASS）',
              '目标/AITargetingHeuristic.Relationship': 'docs/engine/ainamed.md#给关卡线的结论（ainmrel：写了 Relationship 就按关系过滤，玩家的楼当 NEUTRAL 不算，不出门）',
              '战术/Tactic.EndBehavior=DISBAND': 'docs/engine/aitactics.md#目标没了以后（EndBehavior，2026-11-09 各一次）（aiendd：目标没了队伍解散、状态重派去兵营，和模型对上）',
              '战术/Tactic.EndBehavior=RETURN_HOME_AND_DISBAND': 'docs/engine/aitactics.md#目标没了以后（EndBehavior，2026-11-09 各一次）（aiendh：同 DISBAND，没回家，和模型对上）',
              '目标/AITargetingHeuristic.HeuristicType=EnemyStructure': 'docs/engine/aitactics.md#读数（ClosestStructureHeuristic、SafestToGroundStructureHeuristic：aitargetnear / aitargetsafe）',
              '战略状态/TargetHeuristic.Priority': 'docs/engine/aitactics.md#目标挑哪个（aitpphi / aitpplo：同一状态两条目标启发，Priority 高的先试，两向都上台）',
              '目标/AITargetingHeuristic.SortType': 'docs/engine/aitactics.md#目标挑哪个（Distance：aitpnear / aitpmt2 最近、次近；ThreatToGround：aitargetsafe）',
              '目标/AITargetingHeuristic.SortType=Distance': 'docs/engine/aitactics.md#目标挑哪个（aitpnear 挑最近、aitpmt2 第二槽挑次近、aitpvk 显式写 Distance）',
              '目标/AITargetingHeuristic.HeuristicType=FriendlyStructure': 'docs/engine/aitactics.md#读数（FriendlyLandStructureHeuristic：engine_aidefense 守自家建造厂）'}
# name -> (state, why): where the name rule is wrong (read but switched off, read under another name ...)
NOTES = {
    '经济/AccountShare.Account=SLUSH_FUND': (TODO,
        'C按名台子engine_aislush：aislush100/aislush0仅交换SLUSH_FUND与PRODUCTION份额，'
        '两组电厂均s19一座、s29两座，零份额原预测FAIL保留；开局未区分此账户。'
        '第二轮有收入无开局：aislsdef全程零炮塔，aislddef在s28/48/68造出1/2/3座，s60为2。'
        'tests/test_slush_account.py原读数及模型回放；账户余额/实际支出消费者仍gap，'
        '不以开局计数吻合晋升；见work/re/c_slush_report.md'),
    '目标/AITargetingHeuristic.HeuristicType=Expansion': (TODO,
        'C已上台：aiexpc:a东矿区4、崖矿区0、普通实体0，命令指向东矿点；'
        '模型已保留BaseSelection，增加显式候选回调和槽位点，Expansion不再回退普通实体。'
        '自动候选资格/基地发现与排序尚未证实，模型按名回放strict xfail；'
        '仅接口实现，不晋升；见 work/re/c_expansion_probe_report.md'),
    '造兵/CountAsStructureForBuildPurposesFilter.ExcludeThing': (TODO,
        'C静态核查：原版过滤器用于建造优先级，排除矿车/勘探车/日本矿厂核心；'
        '不是现有建筑计数。模型未消费该过滤器，候选分类需接B共享build_units，'
        '普通建筑BuildState优先级亦缺消费者；按工单接口门禁停止，未上台、未晋升。'
        '待B给候选分类/优先级接口；见work/re/c_buildfilter_report.md'),
    '造兵/BuildEntry.Upgrade': (BENCHED,
        'C engine_aiupgrade a：aicupgon常量状态含UPGRADE_TECH/Tech2，s39起持有2（建造厂+它够得着的兵营）；'
        'aicupgoff移除专用状态后恒0；见work/re/c_upgrade_report.md。B第153轮接模型：'
        '升级条目按状态权重×分（UPGRADE 140；UPGRADE_TECH MinTime前0、ForceTime后200推断、中间140推断）'
        '挑最高下单，扣PRODUCTION，下了升级这一轮不下兵；模拟器s20下单、s40起持有2。'
        'tests/test_simai_upgrade_c.py按名回放两组通过。电力门、效率/兵力比两道、开局里的升级单没建模'),
    '目标/AITargetingHeuristic.Location': (BENCHED,
        'E81/E87 engine_ailocation a：同型电厂一陆一水、四架双刃，仅切Land/Water/Water Land；'
        's40到陆厂/到水厂分别4/0、0/4、4/0；'
        'tests/test_simai_bench_e.py::test_target_location按名回放三组通过。'
        'Location按位置地形过滤；只验证EnemyStructure/Distance，浅滩、桥面及空中目标仍INFERRED；'
        '见 work/re/e_location_e87.md'),
    '目标/AITargetingHeuristic.HeuristicType=FriendlyUnit': (GUESSED,
        'E85 engine_aifriendly a：仅切FriendlyUnit/EnemyUnit、同挂StaticDefense与SAME_PLAYER，'
        '两组s40到友车/到敌车均0/0、MCV存活1/1，原始预测均FAIL；'
        'tests/test_simai_bench_e.py::test_friendly_unit_target按名回放strict xfail。'
        '目标选择与招人/站位边界未分，保持gap不晋升；见 work/re/e_friendly_e85.md'),
    '启发条件/PathToTargetHeuristic.LocomotorConditionToUseForTest': (GUESSED,
        'E84 engine_aiopathcond a：同JapanAntiAirShip仅切NORMAL深水/SUPERSONIC空中；'
        '两组s22-s24均兵营1/电厂0，水组原始Island预测FAIL、空中PASS。'
        'tests/test_simai_bench_e.py按名回放实际计数通过，但不能区分条件生效与路径判定边界；'
        '保持gap不晋升，未改B模型；见 work/re/e_pathcond_e84.md'),
    **{f'启发条件/{k}': (BENCHED,
        'E83 engine_aibuilding a：STRUCTURE空队列、现成基地1；PassIfBuilding=false时s40到陆厂4/在家0，'
        'true时0/4，两组PASS；tests/test_simai_bench_e.py::test_is_building_idle按名回放通过。'
        '只验空队列边界，建造中的行为未量；见 work/re/e_building_e83.md')
       for k in ('IsBuildingHeuristic', 'IsBuildingHeuristic.PassIfBuilding')},
    '启发条件/IsBuildingHeuristic.KindOf': (GUESSED,
        'E83 engine_aibuilding只测STRUCTURE空队列，无法区分KindOf匹配与忽略此字段；'
        '有效建造队列、匹配/不匹配、多个token仍gap，不晋升；见 work/re/e_building_e83.md'),
    '开局/SkirmishOpeningMove.Side': (BENCHED,
        'E82 engine_aiopenside a：固定盟军玩家显式挂载三电厂开局，仅切Side。'
        'Allies在[s55,s60)电厂3/兵营0，Soviet电厂2/兵营1。D66：Side和玩家阵营全等才进候选，'
        '候选全空=开局直接完成、不下单、不回退；模型照此（B第147节）。'
        'tests/test_simai_bench_e.py::test_opening_side[aiosallies]、test_an_opening_of_another_side_is_not_run'
        '按名回放、断言台上读数（Soviet s19-s28 无电厂）。gap：Soviet之后的2电厂1兵营是没开局时的结构建造，'
        '模型没建（strict xfail，同第123节）；见 work/re/e_openside_e82.md'),
    **{f'人格/SpecificUnitCap.{k}': (BENCHED,
        'engine_aiskirm aiskcap:y（2026-11-12）：子人格给父人格没写的CNVNewPK四档Cap=2，'
        '新维和s33到2、停到s149（无上限aisknew2 s44已4），兵营改造标枪/维和；'
        'tests/test_simai_bench_b.py::test_a_specific_unit_cap_holds_our_unit_at_two按名回放、断言台上读数。'
        'E80父人格已有维和Cap=20时子人格Cap=2不生效=第一条命中（test_simai_bench_e.py）。'
        'gap：s150后又造到4、没死人，引擎拿什么数对上限未知（strict xfail '
        'test_after_s150_the_capped_unit_is_built_again）；见 work/re/handoff-b.md 第145节')
       for k in ('Unit', 'Difficulty', 'Cap')},
    '组队招人/TeamTemplate.ReleaseType=NEVER_RELEASE': (BENCHED,
        'engine_airelease airelnever/airelprio仅ReleaseType不同；CNVTeams两组f166防御激活持3166/3167，'
        'priority在(526,541]同两ID转进攻，never保留至末样本；'
        'tests/test_simai_bench_c.py::test_never_release_engine_members_and_model_replay按名跑两台、'
        '断言实机ID/n/active及模型f301/601/976成员归属；仅固定两辆车的保留/转队，'
        '精确激活/转队时钟、priority后段短暂第三ID及其他释放模式仍gap；见 work/re/c_release_teams_report.md'),
    '组队招人/TeamTemplate.ReleaseType': (GUESSED,
        'engine_aiskirm aiskirm:m 实机s128防御8/清扫99，s129防御0/清扫8，转队时逐帧兵池峰1；'
        '后续s134峰2，不能宣称全程峰1；tests/test_simai_bench_c.py 按名回放至170秒无非空清扫计数，'
        'strict xfail；新airelnever/airelprio的CNVTeams已证原两ID保留/转队且模型阶段归属匹配，'
        '原八人补测的独立建造厂日志宿主实测防御9→2、清扫0→7，同名空实例并存；'
        'tests/test_simai_bench_c.py::test_release_eight_named_model_replays_carrier_partial_transfer为strict xfail，'
        '宿主等价性/精确时钟/后段第三ID和其他模式仍gap，整个字段未晋升；'
        '见 work/re/c_release_eight_report.md、c_release_teams_report.md、c_release_report.md'),
    '微操/AIMicroManagerData.PassiveTargetSearchDistance': (TODO,
        'C接口闸门阻塞：被动目标分类/选择在B的tactics._team_state；'
        'micro.Team.enemies无被动分类，MicroBlock仅有技能回调，缺候选与距离基准及选敌回写；'
        'SDK显式600/650/0、默认400，距离基准和零值语义未证实；'
        '本轮未上台、不实现消费者、不晋升已对拍；见 work/re/c_passive_distance_report.md'),
    '微操/AIMicroManagerData.MinDistanceFromBaseToIgnoreTargets': (TODO,
        'engine_aiignore aiignzero/aiignnear：仅基地距离阈值0/2000不同，'
        '无武装工程师延迟至26秒且两武士造出后；零阈值仍受伤，'
        'tests/test_ai_ignore_distance.py 按名回放伤害观测；'
        'Hunt/普通自动攻击与微操过滤入口尚未分离，基地取点和精确边界未量，'
        '不实现消费者、不晋升已对拍；见 work/re/c_ignore_distance_report.md'),
    '造兵/BuildEntry.Heuristic': (BENCHED,
        'E78 engine_aiskirm z：BEST_UNIT_EXPECTED 两组台上 PASS；[s150,s160) 征召兵组维和5→6、标枪0，'
        '锤子组标枪7→8→9、维和0；tests/test_simai_bench_e.py::test_best_unit_expected_infantry_choice '
        '两组按来源断言通过（建造状态造的另一种=0；锤子组多的那个维和是单位生成器均匀抽签，台上 t 也抽2次：'
        '狗 s23、工程师 s144）；B 第 149 轮模拟器侧排除"一帧多单""队列非空仍下单"；'
        'FEWEST_UNIT 见 aisknew2 y、RANDOM_UNIT 见 aiskrand s；抽签结果属运气不对拍，'
        '"每次评估无条件掷一次随机数"没建模；见 work/re/e_aiheur_e78.md、work/re/handoff-b.md 第 149 节'),
    '微操/AIMicroManagerData.DodgeThreats': (TODO,
        'engine_aidodge aidodgeon/aidodgeoff 原版精确打击信标开关对照；'
        'tests/test_ai_dodge.py 按名回放，开启组 strict xfail：模型无躲避消费者，'
        'simai.micro_team 缺威胁视图与移动回调（归B）；见 work/re/c_dodge_report.md；'
        '固定0.5秒反应，截图秒窗与游戏帧漂移亦留gap；未量精确时间、圆边界、过滤和多威胁，不晋升已对拍'),
    '微操/AIMicroManagerData.EnterGarrisonableStructureDistance': (BENCHED,
        'engine_aigarrison aigar1/aigar0/aigarfar：默认150、旧楼EAST=40，近楼归AI、关闭或远楼不进；'
        'tests/test_simai_garrison_distance.py::test_garrison_distance_replays_recorded_near_far_and_disabled；'
        '仅现成近远行为回放，精确边界、其他配置值和进门死亡时序未量；距离0仅模型敏感性守卫'),
    '微操/AIMicroManagerData.RetreatMinDistanceToFallback': (BENCHED,
        'engine_aifallback aifbshort100/aifblong500：四人存活回齐、在家约18秒、长组先于短组再出发；'
        'tests/test_simai_fallback.py::test_fallback_distance_first_return_and_departure；'
        '仅此固定FromBase=300场景的行为回放，未量内部退出位置、精确距离边界或其他基地选择'),
    '微操/AIMicroManagerData.EnemySearchDistanceVisionMultiplier': (BENCHED,
        'engine_aisearch aisrchhi/aisrchlo 仅倍率1.5/0.25不同：高先打旁厂、到远厂0；低旁厂100且到远厂4；'
        'tests/test_simai_search.py 回放；仅被动建筑搜索，精确边界、敌军目标取得和揭雾未量'),
    '组队招人/TeamTemplate.SortByDistance': (BENCHED,
        '专用engine_aisort aisort0/aisort1：容量1，关闭远候选f177先离、开启近候选f178先离，另一名留原位；'
        '固定到目标距离约985/700、到基地顺序相反；tests/test_simai_bench_c.py::'
        'test_sort_by_distance_replays_named_departure按名断言两组台内计数并回放匹配；'
        '已对拍限具名候选离开顺序；招走解释仍INFERRED，同帧动态队成员ID/实际距离和等距规则仍gap；'
        '见 work/re/c_sort_report.md'),
    '组队招人/CreateUnits.MinUnits': (BENCHED,
        'engine_aicreate aicr1c/aicr3c：最低1在(301,316]帧激活，最低3在(631,646]帧激活；'
        '后者f316一人/f481两人均未激活；tests/test_simai_bench_c.py按名回放激活区间和成员；'
        '仅孤立单槽位最低数1/3，多槽位/替补/MaxUnits仍gap；s70额外造兵另有strict xfail；'
        '见 work/re/e_create_e88.md'),
    '组队招人/CreateUnits.UnitName': (BENCHED,
        'engine_aicreate aicr1c/aicr3c：最低1是一名新成员加两名已知预摆维和，最低3等三名新成员；'
        'tests/test_simai_bench_c.py按名回放首次组成；新成员兵种由固定生产归属仍INFERRED；'
        '仅指定最低数优先再普通补位，不是排他过滤；其他兵种/多槽位/替补仍gap；'
        '见 work/re/e_create_e88.md'),
    '战术/Tactic.Distance': (GUESSED,
        '专用engine_aidistance aidist250/aidist2000保留AI队、同次传送1200，仅Distance不同；'
        's65小组圈300/900=1/1，大组0/0，存活均1；两组各5条PASS、模型末态匹配；'
        '大组实机传送前离300、传送后回900再离，模型美学轨迹strict xfail；'
        '精确边界/动态队成员仍gap，不晋升；tests/test_simai_bench_c.py；见 work/re/c_distance_report.md'),
    '战术/Tactic.UseAestheticsManager': (GUESSED,
        '专用engine_aiaesthetics aiaeson/aiaesoff固定Distance=2000，仅切美学开关；'
        '两组各5条PASS：on先离300、传送后回900再离，off回双圈，存活/锁存均1；'
        'tests/test_simai_bench_c.py关闭组完整轨迹已回放；探针战术附加属性现传入消费者；'
        '开启组站位仍strict xfail，不晋升；见 work/re/c_aesthetics_report.md、work/re/e_aesthetics_e89.md'),
    '微操/AIMicroManagerData.PullbackInjured': (BENCHED,
        'engine_aipullback aipullsov 残血坦克离队回吊车；tests/test_simai_bench_b.py::'
        'test_a_hurt_soviet_tank_team_is_pulled_back_to_the_crane 回放；普通盟军/日本工厂不可进入；'
        '仅地面车辆回撤，吊车回收仍 strict xfail，未验证空海军/精确时间'),
    '微操/AIMicroManagerData.PullbackInjuredHealthPct': (BENCHED,
        'engine_aipullpct 固定30%血量、苏联吊车，仅阈值0.2/0.5不同；'
        'tests/test_simai_pullpct.py::test_pullback_threshold_high_returns_before_recycling 完整回放四车回家且不到远厂；'
        '同文件 low 对照先到远厂；仅初次回撤阈值，精确边界/晚段/吊车回收未闭环（回收 strict xfail）'),
    '微操/AIMicroManagerData.AlphaStrikeTargetHealthPct': (GUESSED,
        'engine_aialphahp 旧固定70%对照；engine_aialphaclose 独立延迟守军、仅阈值0.01/0.9不同；'
        'tests/test_simai_bench_c.py 保留读数回放，有限诊断不等于字段闭环；'
        '目标适用条件与回放差异仍gap，见 work/re/c_alpha_close_report.md'),
    '微操/AIMicroManagerData.ReverseMove': (GUESSED, '推断（台上未复现）：锤子 airev / airevp / airevt 都不倒车；'
        '工单入口未发布同帧成员当前攻击目标、位置和车身朝向观测，暂停新台，不把普通后退当倒车；'
        '所需最小接口及假设表见 work/re/c_reverse_observation_report.md'),
    # B round 108: a test names the probe but only the switch-off case matches; the effect itself is a strict xfail
    '微操/AIMicroManagerData.Crush': (GUESSED, '台上量过（engine_aicrush：开了 s28 前碾光守军）；模拟器已验证派发，'
                                     '碾压 move 终点不再被避让挪开（A 161 Sim.claims）；原场景仍 strict xfail：'
                                     '到厂晚约 6 s、目标死后等 UpdateTime 才重选（handoff A 161）'),
    '微操/AIMicroManagerData.CrushPreference': (GUESSED, '同 Crush：派发已验证，碾压 move 终点已不挪；'
                                               'engine_aicrush 原场景 strict xfail 保留（handoff A 161）'),
    '微操/AIMicroManagerData.UpdateTime': (GUESSED,
        'engine_aimicro aimicupfast/aimicupslow:a 仅切微操0.5/4s；台内首冲帧363/317、首活均2；'
        'tests/test_simai_bench_c.py 按名回放存活通过，精确时钟strict xfail（模型271/309）；'
        '资格/更新相位仍gap，不能解释为固定延迟；旧aidefctl4改的是Tactic.UpdateTime，非本字段证据；'
        '见work/re/c_update_time_report.md，不晋升'),
    '微操/SpecificSpecialPowerDelay.MaximumDelay': (GUESSED,
        '模型按成功施放后同类冷却消费上限；tests/test_simai_delay.py 验证上端点和真实冲锋执行接线；'
        'engine_aidelay 0/999实机PASS，脚本冲峰值2/1且曾冲>0已有回放；'
        '台上帧数减曾冲恒362、模型270，精确观测时钟strict xfail；'
        '随机分布及原版TOGGLE两种子类仍gap，不晋升原版用量；见work/re/c_delay_clock_report.md'),
    **{f'微操/SpecificSpecialPowerDelay.{field}': (GUESSED,
        '模型已读取；engine_aidelay 0/999实机配对仅改变MaximumDelay，'
        '本字段没有独立变量对照，不因探针出现字段名登记已对拍')
       for field in ('MinimumDelay', 'PowerType')},
    '微操/AIMicroManagerData.EnterBaseDefensesWhenIdle': (GUESSED,
        'engine_aibasedef aibd1 是战斗中总开关开、idle关的正例（s21起1人进炮塔）；'
        'aibd0/aibdidle 总开关均关且无人进驻，不是idle分支正例；'
        'tests/test_simai_basedef_idle.py 直接计数回放，aibd1仍strict xfail；'
        '消费者已调用，到达/炮塔存活差异待A/B接口；见 handoff-c'),
    '人格/AIPersonalityDefinition.BaseCompactness': (GUESSED, '台上量过（engine_aitower：0.5 / 0.75 / 1.0 塔落在不同圈）；'
                                                     '模拟器只对上 0.5，0.75 / 1.0 和 0.5 一样（strict xfail）'),
    # B round 110: the A/B pairs of engine_airetreat change one field of the data the team's MicroManager names
    '组队招人/TeamTemplate.MicroManager': (BENCHED, '台上量过（engine_airetreat：airet / airet0 只差 MicroManager 指名的'
                                        '那份数据里的 RetreatPowerAdvantage，一个撤一个不撤；aipas1 / aipas0 只差 '
                                        'EngagePassiveTargets）、测试对拍 tests/test_simai.py——队伍跑的是 MicroManager '
                                        '指名的那份微操数据；指名不存在的 id 会怎样没量'),
    # B round 111: aiskmod u -- zeroed modifiers, the same build seconds as the stock aiskirm c
    **{f'人格/UnitModifier.{k}': (BENCHED, '台上量过（engine_aiskirm u：aiskmod 把维和、标枪的 UnitModifier 两个系数都设 0，'
                                 '造兵逐秒和原版 aiskirm c 一样）、测试对拍 tests/test_simai.py——没有选兵策略表时 '
                                 'UnitModifier 不影响造什么；有策略表时的打分没量（原版人格都没有）')
       for k in ('Unit', 'OffensiveModifier', 'DefensiveModifier')},
    # B round 118: aiskirm d / f -- CoopBudget's DEFENSE 5 % against the bank decides how many towers (simulator matches)
    '经济/AccountShare.Percent': (BENCHED, '台上量过（engine_aiskirm d / f：开局后 CoopBudget 防御 5%，存款约 36000 两座塔、'
                                 '约 17000 一座、15000 没有）、测试对拍 tests/test_simai.py——塔数对上；第一座的时刻'
                                 '模拟器早 ~36 s（strict xfail），别的份额 / 状态没单独量'),
    # B round 113: aimicspon / aimicspoff PASS on the bench; round 114: the simulator runs them (tests/test_simai.py)
    '微操/AIMicroManagerData.UseSpecialPowers': (BENCHED, '台上量过（engine_aimicro：aimicspon 开 两个武士 s41 冲锋，'
                                              'aimicspoff 关 一直没冲、s51 前被打死，脚本按的对照照样冲）、测试对拍 '
                                              'tests/test_simai.py（模拟器读进探针自写的微操数据：开的想冲、关的从不冲；'
                                              '技能本身模拟器没接，只记"想用"）'),
    # B round 114: state 2's per-member pick (tactics._assign); round 115: aimicengoff (off) on the bench
    '微操/AIMicroManagerData.EngageHostileTargets': (GUESSED, '台上 aimicspon（开）/ aimicengoff（关）两个武士都在家'
                                                  '跟征召兵打、都冲锋活到最后——关掉不让队伍躲开战斗；差别只在首次冲锋：'
                                                  '关 ~258 帧、开 ~362 帧（各两次一致）。模拟器开关都冲，但先后相反'
                                                  '（关 ~457、开 ~275），tests/test_simai.py strict xfail；'
                                                  '私有模型里的打分式没读（按"杀死所需秒数"推断）'),
    # B round 112: airetf / airetfd (the state on a flag, off once the team has its slot) differ only in this field
    '战术/Tactic.DisbandAfterRetreatTeamSize': (BENCHED, '台上量过（engine_airetreat：airetf 0 撤回家后再出门，airetfd '
                                             '999 撤回家后一直在家——撤退结束那轮人数 ≤ 它就结束战术、放人）、测试对拍 '
                                             'tests/test_simai.py；1 / 4 / 5 这种"剩几人才散"的中间值没量'),
    # B round 109: the gate is on in the model since round 100 (keep_on); aiar0-3 replayed on the simulator
    **{k: (BENCHED, '台上量过（engine_aiskirm y aisknew / aisknew2：没列进任何建造状态的我们的兵不造、列成 FEWEST_UNIT '
                    '占兵营约一半；z aiskvinf / aiskvveh：BEST_UNIT_EXPECTED 兵营只造克制兵），测试对拍 '
                    'tests/test_simai_bench_b.py（B 第 126–131 轮）；RANDOM_UNIT（PercentLow/High）、MinTime 没单独量')
       for k in ('造兵/BuildEntry.Build', '造兵/BuildState.State')},
    # B round 138: aiskrand / aiskdiff (check s)
    **{k: (BENCHED, '台上量过（engine_aiskirm s aiskrand：RANDOM_UNIT "0%–30%" 和不带百分号的 "30–100" 两条都造出来'
                    '——不带 % 的数也按百分比读，原版 _RANDOM 状态就这么写），测试对拍 tests/test_simai_bench_b.py；'
                    '两条的比例（预测 3:7，台上 4:4）样本太少没定')
       for k in ('造兵/BuildEntry.PercentLow', '造兵/BuildEntry.PercentHigh')},
    '造兵/BuildState.Difficulty': (BENCHED, '台上量过（engine_aiskirm s aiskdiff：只挂 HARD 的建造状态在普通难度一个不造，'
                                    '挂 MEDIUM 的照造），测试对拍 tests/test_simai_bench_b.py'),
    '组队招人/TeamTemplate.AlwaysRecruit': (BENCHED,'台上量过（engine_aiteamfilter aiar0～3，第 90 轮）、测试对拍 '
                                         'tests/test_simai_bench_b.py：关着新造的车留家、开着出门的队把它招走、'
                                         '满员不招、不预放时第一辆自己组队（模拟器每次晚 3～4 s）；模拟器多造'
                                         '第 3、4 辆是造兵的缺口（strict xfail），不是这个开关'),
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


def ai_items(bench_sources, tested):
    """The AI items; bench_sources = inventory.bench_sources() ([(source, text)]), tested = inventory.tested_probes()
    (the probes a test runs: only those make an item 已对拍, as inventory.bench_verdict)."""
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
            hits = [s for s, t in src if rx.search(t)]
            run = next((s for s in hits if s in tested), None)
            if run:
                state, why = BENCHED, f'{why}；台上量过、测试对拍：{run}'
            elif hits:
                why = f'{why}；台上量过（{hits[0]}），没有测试跑这个台子'
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
