# 模拟器分层（边界和规矩）

决定见 [ADR 0029](../adr/0029-simulator-layers.md)；搬到哪一步看 [plan.md](../plan.md)"模拟器分层搬迁"一行。逐方法归层的工作表在私有仓库 `work/re/sim_split/`（`methods.csv`、`fields.csv`），由那里的脚本按代码重算，不在这里抄。

## 为什么按引擎的部件分，不按线分

模拟器复刻的是红警 3 引擎，逆向读到的每条事实都长在引擎的某个部件上（某个物体模块、武器效果、玩家系统、脚本动作）。代码边界和引擎对齐：读到一个事实就知道改哪个文件，改一个文件就知道会影响什么。线（A–E）是人怎么分活，会变；一条线的一项活常常跨好几层，按线分只会让文件跟着人事变动。

## 层（从下往上；下层不许调上层）

| 层 | 管什么 | 不管什么 |
|---|---|---|
| L0 世界 | 对象登记和生死、归属、队伍、玩家名单、帧时间、地形和区域、审计记录（哪条规则被用到） | 任何游戏规则 |
| L1 数据 | 读模板、继承链、XML（`simunits.py`），武器组数据见 [模块文档](sim-modules.md#6-对外端口) §6 | 运行时状态 |
| L2 物体模块 | 每个对象身上的部件：血量和受伤入口、回血、死亡和移除；状态位、模型状态、修改器和光环；`WeaponSet` 持有的武器和槽位；移动、寻路、碾压、落地；装载（驻军、渗透、运输）；开关和自身技能；生产、展开、建造；采矿和停靠 | 给单位下命令（那是 L5）；扣钱加钱（调 L4 的接口） |
| L3 战斗 | 索敌（含隐身、视野对索敌的影响）、瞄准和开火节奏、弹体、伤害效果（各种 Nugget、MetaImpact）。已迁入登记表的效果在 `engine/combat/` | 追击和攻击状态机（L5） |
| L4 玩家系统 | 钱、电力、科技和升级、技能书 | 单个对象的状态 |
| L5 单位命令 | 移动、攻击（含追击）、警戒、跟随、占领、猎杀、撤退、停止、发呆时找事 | 移动的物理（调 L2）、开火的数值（调 L3） |
| L6 脚本 | 条件和动作：把脚本翻译成对下面几层接口的调用；字幕、镜头、音视频单独一块 | 自己实现规则 |
| L7 帧循环 | 每帧按固定顺序推进各子系统 | 规则本身 |
| L8 遭遇战 AI | `simai.py` 决策，通过 AI 设置及玩家系统、观测、命令端口接入宿主，射程直接读 L3 `simrange` | 组装和启动模拟局（入口 `simai_run.py`） |
| L9 汇报 | 每秒采样、指标、覆盖检查；局级工具 `simsnap`、`simaisnap` 和 `simbattlefield` | 帧内推进游戏规则 |

脚本计数器和计时器由当前执行器持有。公开执行器与可选的私有模型执行器共用 `scripts.World` 接缝，宿主适配在 `simexec.SimWorld`。

## 规矩（拆完后由守卫测试强制）

1. **依赖单向**：一个层的文件只导入同层或更下层的模块。CNV 的逐层导入由 `tests/test_sim_layers.py` 的 `LAYER_OF` 检查。各层可导入 `BOUNDARY` 里的适配模块（`engine.ports.ai`、`engine.ports.observe`、`engine.ports.readonly` 和 `modelpin`）；它们只依赖 L0 或同为边界的模块。通用架构守卫在 `tests/guards/test_architecture.py`。
2. **不伸手进别人的状态**：子系统通过公开接口交互。驻军、渗透、扫射、维修、分配和 AI 用 `WORLD_API` 接入宿主。仍须借宿主方法的模块另列 `PEERS`，AI 的端口和剩余借用见 [模块文档 §6](sim-modules.md#6-对外端口)。
3. **一个字段一个主人**：守卫按 `FIELD_OWNER` 检查已登记字段的写点。钱、位置、目标和模式的完整所有权仍是迁移目标，命令规则优先放在 `simorder`。
4. **有这个部件才推进**：已迁入内核的更新模块按 `PHASE` 登记进格，只推进该格到期的实例；宿主未迁入的格仍可能遍历全局。
5. **帧顺序只写一处**：帧循环是一张有序的子系统列表。有引擎模型和没有引擎模型（`Sim(model=False)`）两种跑法走同一个 `simloop.step`、同一个顺序，脚本格调用所选执行器。模型开关和脚本执行器可分别指定（例如 `python -X utf8 experimental/cnv/simrecord.py record DIR --executor public@model`，用法见 `simrecord.py`）。
6. **审计是公共服务**：记录"哪条规则被用到"的那个集合放在 L0，任何层都能写，只能追加。

## 测试分层

- **规则测试**：用最小世界（一张空地图、几个按模板摆好的对象）只推进相关子系统几帧，断言一条规则。目标是几秒一个。每个子系统搬出来时同时带上它的最小世界测试。
- **台上对拍**：把台上读数写成数据，由一致性跑器核对。五层测试的用途见 [testing.md](testing.md)。
- **搬迁不改行为**：纯搬迁用 golden 固定任务的逐帧记录核对前后一致。分支跑受影响测试，默认排除整局回放，全量由总控跑。

## 不许怎么做

- 不许按线建文件（`sim_a.py`、`sim_c.py` 之类）。
- 不许新加反向调用来图省事；真需要上层的结果，就由上层在帧循环里把结果交下来，或者下层发一个事件让上层自己取。
- 不许一次性推倒重写：一块一块搬，旧的 `Sim` 方法先留着转调新模块，直到没人调用再删。
- 清单按登记表认脚本动作和条件，模块、Nugget 和状态查导入链源码。导入链从 `sim` 和 `simproxy` 开始，禁止硬编码固定文件名单（11-17 搬家后曾少算 401 项）。
- 不许在交接、提示词里写 `sim.py` 行号或"某方法在某文件"：写能搜到的名字，位置以代码为准。
- 新规则必须带一个最小世界测试（`simsmall.small_world`）；对拍读数写进数据，整局回放默认不进日常挑选。

## 新规则放哪个文件（给恢复的引擎线和 Codex）

**先看 [sim-modules.md](sim-modules.md) §7"扩展点"：新规则先回答"挂在哪个扩展点上"**（ADR 0031 第 4 条）。那个部件已经搬进模块内核的，照那里写；还没搬的（迁移进度见私有仓库 `work/re/sim_split/module_plan.md`），暂按下表落位，搬的时候由重构线 R 一起挪进模块。

先问"这条事实长在引擎的哪个部件上"，再按下表落位。只写模块名和登记表名，位置以代码为准（搜 `def 名字`、`名字 = `）。登记表都在模块里或守卫测试里。新规则按表登记，涉及执行顺序的名单按规则指定的位置插入。

| 要加 | 改哪个模块（层） | 在哪张登记表加一行 | 配什么测试 |
|---|---|---|---|
| 脚本动作 | 按它作用的层挑一组：`simact_vision`（视野）`simact_player`（钱、电、科技、技能）`simact_order`（给单位下命令）`simact_object`（对象状态）`simact_ability`（技能按钮）`simact_world`（旗标、计时器、队伍）`simact_show`（字幕、镜头、音视频）（L6）。函数 `fn(sim, name, a, script)` 只翻译参数，已迁移的单位命令和按钮经 `Sim.commands` 下发，规则写在下层。队伍动作复用单体动作时，把已选成员作为 `unit=` 传给相应函数，所经的命令端口用序号传递对象。名字输入才由入口解析，见 [命令端口约定](sim-modules.md#91-游戏适配器真游戏也是端口的一个适配器) | 那组的 `ACTIONS`（`simact.table` 合并，重名报错；清单靠它认名字）。新开一组：加进 `simact.GROUPS` + `LAYER_OF` 记 6 | 最小世界摆好对象，跑这个动作，断言世界的变化；做不到的参数分支 `return False`（自动记成缺口） |
| 脚本条件 | 同上，`simcond_world` / `simcond_object` / `simcond_vision` / `simcond_player` / `simcond_show`（L6），`fn(sim, name, a)` 回真假 | 那组的 `CONDITIONS`；新开一组加进 `simcond.GROUPS` + `LAYER_OF` | 同上；不认得的情形回 `None`（记缺口、当不成立） |
| 物体模块（AutoHeal、Toggle 这类 XML 模块） | L2。AutoHeal、Toggle 的本体规则写进 `engine/modules/autoheal.py`、`toggle.py`。仍在宿主的规则加进对应的 `sim<部件>.py`，状态放在自己的对象里 | 以下登记用于宿主规则：`LAYER_OF` 记 2；收世界句柄 → `WORLD_TAKERS`；用到世界的新能力 → `simworld.WORLD_API`；独占字段 → `FIELD_OWNER`；还要借 sim.py 里没搬的方法 → 模块自己的 `PEERS` + `PEER_TAKERS` | 最小世界 + 只推进这个部件几帧（样板：`test_simheal`） |
| 武器伤害规则（各种 Nugget、MetaImpact） | L3 `simdamage.Damage.deal` 负责协调结算，已迁入 `engine/combat/` 的弹体、线伤害和直接伤害按阶段分派。射程规则在 `simrange`；追击和攻击状态机归 L5 | 处理器的阶段及顺序登记在 `engine.combat.registry.ORDER`，规则与接法见 [模块文档 §7](sim-modules.md#7-扩展点加一样东西要写什么)。宿主结算的新缓存按 `FIELD_OWNER` 登记；还在 `sim.py` 的宿主动作查 `simdamage.PEERS` | 最小世界里一个开火方一个挨打方，断言血量 / 状态；只做了一部分的 Nugget 写 `world.gap(GAP_WEAPON, 'XxxNugget', 缺什么)` |
| 单位命令（移动、攻击、警戒、跟随、撤退……） | L5 `simorder`：下命令 `order_*(world, peers, b, ...)`，每帧推进 `*_due`。移动的物理调 L2，开火的数值调 L3；扣钱加钱调 L4 `simmoney.Money` | 已登记的命令字段按 `FIELD_OWNER` 独写；借的名字进 `simorder.PEERS`；玩家输入从 `Sim.commands` 查分派 | 最小世界里下命令、推进几帧，断言位置 / 目标；脚本动作那一层只测"翻译对了" |
| AI 规则 | L8 `simai` 和它的适配器（样板 `simpullback`、`simmicro`）。`SimAI` 和 `Brain` 用 `Settings`、`PlayerSystems`、`Observe` 和持有的命令端口接宿主（详见 [模块文档 §6](sim-modules.md#6-对外端口)），单位命令推进归 `simorder` | `simmicro`（L5）和 `simpullback`（L8）均在 `WORLD_TAKERS`；`simpullback` 和 `simai` 也在 `PEER_TAKERS`。`simai` 登记为 L8，不导入 `sim`（目标是物体用内核的 `Thing` 判断；造局跑整局的入口是 `simai_run.py`，测试从它拿 `simai`，进程里只有一份）；`AI_SIDE` 成员从玩家链清单排除 | 直接喂适配器一个小局面断言它的决定；AI 回放用于整局验证 |
| 每帧要做的事 | 已迁入内核的规则写成模块，例如 AutoHeal；仍在宿主的规则用主人对象的 `due` / `tick`，例如 `s.repairs.due` | 模块用 `PHASE` 选现有格；宿主调用和门控见 `simloop.CELLS` / `FRAME`，两种跑法共用 | 规则在主人模块测；改 `FRAME` 顺序会改录制，要有台上证据 |

每件都要：

- **一个最小世界测试**（`simsmall.small_world`，几秒），测试名写行为。台上读数交给一致性跑器核对；日常挑选默认排除整局回放。
- **没做的分支记缺口**：`world.gap(GAP_*, 名字, 缺什么)`（种类在 `simworld`），清单才看得到，不静默。
- **清单怎么数到你**：动作和条件读登记表。模块、Nugget 和状态读 `simcoverage.sim_files` 的导入链源码（入口 `sim`、`simproxy`）；状态按 `STATUS_TEST` 匹配，另补 `IN_STASIS`。新文件要进入运行的导入链。
- **分层模块不调 Sim 的转调**：调规则的真身（同层或下层模块的函数、世界 API、`Peers` 借来的还没搬的方法）。`test_sim_forwarders.FORWARDER_CALLS` 只减不增。Sim 上的转调只给 sim.py 里的旧代码和测试用，新规则别再加。
- **守卫**：`tests/test_sim_layers.py`（导入方向、世界句柄、字段主人、帧顺序）、`tests/test_sim_forwarders.py`、`tests/test_simcoverage_files.py`、`tests/guards/test_architecture.py`。

### 拿已搬的三块核一遍

- **⑥ `simbody`（物体模块那一行）**：死亡、移除、卖楼、坠机、按时掉血是 L2 的血量部件 → 新文件 `simbody.Life`，独占缓存 `lose_of` 进 `FIELD_OWNER`；用到的世界能力（`kills note label change add blocks reblock`）补进 `WORLD_API`；卖楼退款不写钱字典，调 L4 的 `simmoney.Money.credit`；每帧格子 `lose_health`、`expire` 各一句调用。
- **⑦ `simdamage`（武器伤害那一行）**：伤害结算和各 Nugget → L3 `simdamage.Damage`，十个独占缓存进 `FIELD_OWNER`；要的 L2 动作（`destroy`、`modify`、`set_model_condition`……）当时都还在 sim.py，所以走 `simdamage.Peers`，名单 `PEERS`，登记 `PEER_TAKERS`；攻击状态机 `fight` 归 L5，没跟着搬；每帧格子 `deal`。
- **⑨c `simgarrison` / `siminfiltrator` / `simrepair`（旧模块改接口）**：旧写法拿整个 Sim 读写（`self.sim.X`）→ 世界 API 有的改 `world.X`，其余改 `peers.X`；维修扣钱、间谍偷钱改走 `simmoney.Money` 的 `held` / `charge`。登记成分层模块后，守卫才数到它们原有的转调调用（`siminfiltrator` 的 `destroy`、`send`），在 `FORWARDER_CALLS` 补登一次，之后只减。
