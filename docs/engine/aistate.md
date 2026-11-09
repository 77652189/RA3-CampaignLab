# 遭遇战 AI 的战略状态：地图旗标能不能切换 AI 在做的事

引擎线 B 第 7～8 轮（2026-11-06），ADR 0019 第四层（遭遇战 AI）第二块。写法照 `script-semantics.md`：**测** = 测试台；**推断，未实测** = 只从资料推出来。

探针 `experimental/cnv/checks/engine_aistate.py`（任务 `missions/aistate_bench.py`，各个 build 都跑检查 `a`）用的是尼亚加拉图，敌方是盟军 AI，人格继承 `AlliedCoopBasePersonality`，把继承来的 24 个状态全删掉，只留两个：
- `CNVStateInf`：派 2～4 个维和步兵；
- `CNVStateTank`：派 2～4 个守护者坦克。

每个状态只带一个启发条件，有两种写法：`ScriptedFlagHeuristic FlagName=...`（旗标开着才开），或 `ConstantHeuristic`（常开）。目标启发都是 `ClosestStructureHeuristic`。时间线是：第 10 秒唤醒 AI，第 20 秒开步兵旗，第 60 秒关步兵旗、开坦克旗。检查每秒数一次基地里还剩几个兵。

## 读数（测）

| build | 目标 | 状态怎么开 | 结果 |
| --- | --- | --- | --- |
| `aistate` | 只有约 2600 外的玩家建造厂 | 旗标，脚本写纯名字 | 一个都不动（旗标没加 `/`，AI 根本看不见；750 处同样写法也不动，所以这条说明不了距离） |
| `aistateconst` | 约 750 外放一座玩家电厂 | 常开 | 唤醒后约 5 秒，8 个兵一起出门 |
| `aistatefar` | 只有约 2600 外的玩家建造厂 | 常开 | 坦克唤醒后 3～4 秒全部出门；步兵一个都不动 |
| `aistatefar2` | 约 2600 外的玩家建造厂，加一座玩家基地里的电厂（约 2400 外） | 常开 | 唤醒后 4 秒，步兵和坦克**都**出门 |
| `aistatenear` | 约 750 外 | 旗标，脚本写纯名字（带空格） | 一个都不动；脚本条件 `FLAG` 看得到这个旗标 |
| `aistateplain` | 约 750 外 | 旗标，脚本写纯名字（只用字母） | 一个都不动 |
| `aistateslash` | 约 750 外 | 旗标，**脚本写 `/CNVAIInfantry`**，AI 资产写 `CNVAIInfantry` | **通了**：开旗后 74 帧（约 5 秒）步兵全部出门；坦克第 60 秒前不动，开旗后 77 帧出门 |
| `aistateoff` | 约 750 外 | 同上，步兵旗第 20 秒开、**第 28 秒关**（队伍还在半路）；结束方式 `RAMPAGE` | 步兵照样走到目标，一直待到第 62 秒 |
| `aistateoffhome` | 同上 | 同上；结束方式 `RETURN_HOME_AND_DISBAND` | 一样：走到目标、待着，没有一个回家 |
| `aistateoff1` / `aistateoffh` | 同上 | 步兵旗开后 **1 秒 / 0.5 秒就关**（队伍还没出家门）；`RAMPAGE` | 一样：照常出门（第 23～24 秒）、走到目标、待着 |
| `aihunt` | 同上 | 换成一个常开的**不需要目标**的状态（`Hunt` 战术，`Targetless="true"`），每队只要 1 个维和；不写 `MaxRunningCopies` | 4 个维和全走了，唤醒后 59～60 帧离家 |
| `aihunt2` | 同上 | 同上，`MaxRunningCopies="2"` | 正好走 2 个，另外 2 个一直在家 |

## 结论（给关卡线）

- **能用旗标切换 AI 状态，但地图脚本里旗标名前面要加一个 `/`**：脚本写 `SET_FLAG('/敌军进攻', 1)`，AI 人格的状态里写 `<ScriptedFlagHeuristic FlagName="敌军进攻"/>`（不带 `/`）。脚本自己用 `FLAG` 条件检查这个旗标时，也写带 `/` 的名字。不加 `/`，AI 永远看不见这个旗标，状态永远不会开。（测）
- 原因：旗标表是按"作用域 + 名字"记的。地图脚本属于哪个玩家的脚本列表，名字就记在那个玩家的作用域下；AI 读旗标时用的是空作用域。名字写成 `作用域/名字`，作用域就由名字自己指定，`/名字` 就是空作用域。（程序里读到；"玩家作用域就是玩家名"这一点是推断）
- **多久生效**：旗标打开后约 5 秒，那支队伍就出门了，和常开状态在唤醒后出门的速度一样。拆开算：状态占槽 1～2 帧，走出基地区域（步兵 190、速度 50；坦克 263、速度 80）57/50 帧，剩 15/26 帧是起步。也就是说这 5 秒主要是走路，队伍够人数当场就走，不另外等。（测；拆分按模型算）
- **状态要有目标才会启动**：目标启发必须找到一个目标，状态才会占槽、派兵。（原先标"测"，依据就是下面那条不成立的 2600 读数；现在只算推断，未实测）
- **找敌方建筑、敌方单位不限距离**：程序里只有找科技建筑的那种目标启发会看 `SearchRange`；找敌方建筑和敌方单位的都不量距离，所以进攻目标放多远都行，不用放在 1500 以内。（程序里读到；测：`aistatefar`，只有约 2600 外的玩家建造厂、两个状态常开，坦克队唤醒后 4 秒全部出门，和 750 处一样快。但步兵队一个没动。）
- **一个目标只给一个状态**（测）：`aistatefar` 只有一座玩家建筑时只走了一队；`aistatefar2` 多放一座远处的电厂，两队都走了。数据里找最近敌方建筑的目标启发 `ClosestStructureHeuristic` 写着 `RequireUniqueTarget="true"`：已经被别的状态占作目标的建筑，它不再选。关卡里想让几支队伍同时进攻，就多给几个目标；哪队先占到目标是随机的。（更正：本文早先写的"目标在 2600 外，旗标开着也不动（测）"不成立。那次的旗标没加 `/`，同样写法在 750 处也不动，所以那条读数说明不了距离。）
- **关旗叫不回已经出门的队伍**：队伍出门后再关旗，它照样走到目标那里、一直待着，写了 `EndIfStateTurnsOff="true"` 也一样，结束方式写"回家解散"也不回家（看了 30 秒）。关卡要撤兵，用脚本直接给那些单位下令，别指望关旗。关旗只管以后不再派新队伍。（测）
- **旗标只开一下也算数**：开旗后 0.5 秒就关，队伍照样出门进攻。只要状态在旗开着的时候被评估到一次（每秒一次），就派出一整支队伍，之后关旗不影响它。所以"开旗 = 派一波"，想只派一波可以开了马上关。（测）
- **不需要目标的状态（战术写 `Targetless="true"`，比如 `Hunt`）不受"要有目标"的限制，而且会开很多份**：每份一支队伍，AI 每 3 帧最多新开一份，直到 `MaxRunningCopies` 份；不写这个属性就不限，能招到的兵会全部被拉走。想让 AI 只派一部分兵去"巡猎"，一定要写 `MaxRunningCopies`。（份数和上限：测；每 3 帧一份：程序里读到，测试台上 3 帧的间隔被走路时间盖住了，分不出）

## 战力优势开关（PowerAdvantageHeuristic）

引擎线 B 第 77 轮（2026-11-09）。探针 `checks/engine_aipoweradv.py`（任务 `missions/aipoweradv_bench.py`）：同上的图和 AI，人格只留一个状态，启发条件 `PowerAdvantageHeuristic Value="1" Above="true"`、两边都不算防御建筑，派 2～8 辆守护者打 750 外的玩家电厂。玩家的坦克停在自家基地不动，两边不交火。

程序里的算法（读到）：力量优势 = 敌人杀光我方要的时间 ÷ 我方杀光敌人要的时间，按**模板满血**算，不看现在剩多少血；敌人什么都打不了我（时间封顶）时直接算"占优"。同样的兵，比值 = （我方数 ÷ 敌方数）²。

| build | AI 坦克 | 玩家 | 结果（测） |
| --- | --- | --- | --- |
| `aipadv2` | 8 | 4 辆守护者 | 唤醒后 3～6 秒全部出门（比值 4，开） |
| `aipadv1` | 4 | 8 辆守护者 | 一辆不动，看到第 65 秒（比值 1/4，关） |
| `aipadvh` | 4 | 只有一辆矿车 | 出门（敌人没有能打的单位 → 占优） |
| `aipadvc` | 4 | 8 辆守护者，状态换成常开 | 出门——对照：`aipadv1` 不动是战力判断挡的，不是别的原因 |

给关卡线：用这个条件的 AI 状态**数的是双方整支军队**（不是附近的），玩家在家里囤兵也会让 AI 不出门；玩家只有矿车等不能打的单位时，AI 一定判自己占优。模拟器 `simai.Brain.power_advantage` 四组都对上（`tests/test_simai.py::test_power_advantage_gates_the_state_as_on_the_bench`）。没测：`Above="false"`、Value 不是 1、算上防御建筑、多个敌人时看哪一个。

## 队伍招谁（TeamTemplate 的筛选）

引擎线 B 第 78 轮（2026-11-09）。探针 `checks/engine_aiteamfilter.py`（任务 `missions/aiteamfilter_bench.py`）：同上的图和 AI，家里 4 辆守护者 + 4 个维和步兵，一个常开状态派一队（MinUnits 1）打 750 外的玩家电厂，每个 build 只换队伍模板的筛选。看第 40 秒谁还在家。

| build | 筛选 | 出门的（测） |
| --- | --- | --- |
| `aitfany` | `ObjectFilter Rule="ANY"` + `IncludeThing` 守护者 | 只有 4 辆守护者 |
| `aitfnone` | `Rule="NONE"` + `IncludeThing` 守护者 | 只有 4 辆守护者（和 ANY 一样） |
| `aitfall` | `Rule="ALL"` + `ExcludeThing` 守护者 | 只有 4 个维和 |
| `aitfki` | 不写 ObjectFilter，`IncludeKindOf="INFANTRY"` | 只有 4 个维和 |
| `aitfke` | `IncludeKindOf="CAN_ATTACK" ExcludeKindOf="INFANTRY"` | 只有 4 辆守护者 |
| `aitfmax` | `MaxUnits="3"`，家里 8 辆守护者 | 3 辆，5 辆留家 |

给关卡线（测）：
- **点名要哪几种兵**：`Rule="ANY"` 或 `Rule="NONE"` 加一串 `IncludeThing`，都是"只要这几种"。原版 `CaptureLandHusks`（"派 1 个基础步兵去占残骸"）就是 NONE 加步兵名单。**点名不要哪几种**：`Rule="ALL"` 加 `ExcludeThing`。
- 按种类：`IncludeKindOf` 只收带这个种类的，`ExcludeKindOf` 把带这个种类的排掉。写了几个 IncludeKindOf 时是"有一个就行"还是"都得有"，这次只写一个，没分出来。
- `MaxUnits` 是一队的人数上限；同一个目标只派一队（`MaxTargets` 1），所以多出来的兵留在家里。
- 模型原先把 NONE 当"不筛"，台上否了，已改（私有 `ai/teams.py`）；模拟器六组都对上（`tests/test_simai.py::test_team_filters_take_whom_the_bench_sent`）。

### 移动方式和对象集（第 81 轮）

同一探针再加六组（移动方式那三组把维和换成 4 艘激流气垫船，种类 AMPHIBIOUS）：

| build | 队伍模板 | 出门的（测） |
| --- | --- | --- |
| `aitfland` | `AllowedLocomotorTypes="LAND"` | 只有守护者 |
| `aitfamph` | `AllowedLocomotorTypes="AMPHIBIOUS"` | 只有气垫船 |
| `aitfwat` | `AllowedLocomotorTypes="WATER"` | 谁都不走——两栖的不算 WATER |
| `aitfosi` | `RegisteredObjectSet="INFANTRY"` | 只有维和 |
| `aitfosv` | `RegisteredObjectSet="VEHICLES"` | 只有守护者 |
| `aitfosc` | `RegisteredObjectSet="SKIRMISH_AI_NORMAL_COMBAT_UNITS"` | 两种都走，但比别组晚约 6 秒（第 20～23 秒） |

给关卡线（测）：
- 想让海军队伍也带上两栖单位，要写 `WATER AMPHIBIOUS`（原版就这么写）；只写 WATER 不收两栖的。
- `RegisteredObjectSet` 也是一道筛选：INFANTRY 只收步兵、VEHICLES 只收车。模型原先没用它，已补（私有 `ai/teams.py`；AIRCRAFT、HARVESTERS 按名字推断，没量）；模拟器六组对上（`tests/test_simai.py::test_locomotor_types_and_object_sets_take_whom_the_bench_sent`）。"普通作战单位"那组晚 6 秒的原因没查，模拟器没做。

### 两队抢兵和 MinPowerAdvantage（第 82 轮）

两个常开状态抢同一批 4 辆守护者：P 打电厂（ClosestStructure，单独跑时 s13 就有目标）、B 打兵营（单独跑 s19 才有目标）。探针 `missions/aitargetpick_bench.py` aitppr*，读数在 `checks/engine_aitargetpick.py`。

| build | P / B 的队伍 Priority | 去哪（测） |
| --- | --- | --- |
| `aitpprs` | STANDARD / STANDARD | 4 辆全去兵营（s17～20 出门），电厂一辆没有 |
| `aitpprh` | STANDARD / HIGH | 同上 |
| `aitpprl` | LOW / STANDARD | 同上 |
| `aitpprp` | HIGH / STANDARD | 4 辆全去电厂（s12 出门） |

队伍 `MinPowerAdvantage`（探针 `missions/aipoweradv_bench.py` aipadm*，状态常开）：8 对 4 写 1.0、4 对 8 写 1.0、8 对 4 写 5.0，**三组都照常出门**——它不拦队伍（模型本来就只解析不用；它管什么没找到）。

给关卡线（测）：
- 两个状态抢同一批兵时，**队伍 Priority 高的那队拿走全部**；一样高时归后写的那个状态（B），哪怕它的目标晚找到——不是"先找到目标的先招"。一样高时是按写的顺序还是抽签没分开。
- 想让 AI 留着兵等优势再出门，别靠队伍的 MinPowerAdvantage，用状态的 PowerAdvantageHeuristic（见上"战力优势开关"）。
- 模拟器：HIGH 对 STANDARD 那组对上；另三组模拟器给"全去电厂"，对不上（`tests/test_simai.py::test_team_priority_as_on_the_bench` strict xfail）。

## 按难度挂的状态（StrategicState 的 Difficulty）

引擎线 B 第 79 轮（2026-11-09）。探针 `checks/engine_aidiff.py`（任务 `missions/aidiff_bench.py`）：同上的图和 AI，家里 4 辆守护者 + 4 个维和，两个常开状态，一个挂 `Difficulty="MEDIUM"`、一个挂 `Difficulty="EASY HARD BRUTAL"`，各只招一种兵；玩家放两座电厂（一个目标只给一个状态，两队都能走）。另用三条各只开一个难度位的任务脚本把战役难度写进计数器。

| build | 守护者那个状态挂 | 维和那个状态挂 | 战役难度 | 出门的（测） |
| --- | --- | --- | --- | --- |
| `aidiff` | MEDIUM | EASY HARD BRUTAL | 普通 | 只有 4 辆守护者（唤醒后约 5 秒） |
| `aidiffx` | EASY HARD BRUTAL | MEDIUM | 普通 | 只有 4 个维和 |

给关卡线（测）：
- **战役"普通"难度下，地图里的遭遇战 AI 按 MEDIUM 跑**；没挂 MEDIUM 的状态根本不跑。测试台走菜单进的是普通难度。
- 想让敌人在不同难度下做不同的事，就在人格里给同一个状态挂不同难度的版本（原版 `LandDefense` HARD BRUTAL、`LandDefense_MEDIUM`、`LandDefense_EASY` 就这么写）。
- 简单、困难两档对应 EASY / HARD 是推断（测试台只走普通）；模拟器（simai 的 DIFFICULTY）按这个对应，两组都对上（`tests/test_simai.py::test_only_the_states_listed_for_the_difficulty_run`）。

## 没测的

- `EndIfStateTurnsOff` 到底在什么时候起作用：出门前、出门后关旗都不管用，程序里也没找到判据。队伍凑不齐 MinUnits、一直在家等人时关旗会怎样，没测。
- 开旗后不到 0.5 秒（还没被评估到）就关，会不会漏掉：按每秒评估一次推，可能漏，没测。
- 关旗以后过更久（超过 30 秒）、或者目标被打掉以后，队伍会不会结束。
- 旗标在多个 AI 之间是不是共用：都读空作用域，按程序读法应该是共用的，没测。
- 原版关卡的热点脚本写在哪个玩家的列表里，为什么不带 `/` 也能用（猜是写在中立玩家的列表里，那里的作用域本来就是空的）。
