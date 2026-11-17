# 模拟器分层（边界和规矩）

决定见 [ADR 0029](../adr/0029-simulator-layers.md)；搬到哪一步看 [plan.md](../plan.md)"模拟器分层搬迁"一行。逐方法归层的工作表在私有仓库 `work/re/sim_split/`（`methods.csv`、`fields.csv`），由那里的脚本按代码重算，不在这里抄。

## 为什么按引擎的部件分，不按线分

模拟器复刻的是红警 3 引擎，逆向读到的每条事实都长在引擎的某个部件上（某个物体模块、武器效果、玩家系统、脚本动作）。代码边界和引擎对齐：读到一个事实就知道改哪个文件，改一个文件就知道会影响什么。线（A–E）是人怎么分活，会变；一条线的一项活常常跨好几层，按线分只会让文件跟着人事变动。

## 层（从下往上；下层不许调上层）

| 层 | 管什么 | 不管什么 |
|---|---|---|
| L0 世界 | 对象登记和生死、归属、队伍、玩家名单、帧时间、地形和区域、计数器 / 计时器存储、审计记录（哪条规则被用到） | 任何游戏规则 |
| L1 数据 | 读模板、继承链、XML（`simunits.py`） | 运行时状态 |
| L2 物体模块 | 每个对象身上的部件：血量和受伤入口、回血、死亡和移除；状态位、模型状态、修改器和光环；移动、寻路、碾压、落地；装载（驻军、渗透、运输）；开关和自身技能；生产、展开、建造；采矿和停靠 | 给单位下命令（那是 L5）；扣钱加钱（调 L4 的接口） |
| L3 战斗 | 索敌（含隐身、视野对索敌的影响）、瞄准和开火节奏、弹体、伤害效果（各种 Nugget、MetaImpact） | 追击和攻击状态机（L5） |
| L4 玩家系统 | 钱、电力、科技和升级、技能书 | 单个对象的状态 |
| L5 单位命令 | 移动、攻击（含追击）、警戒、跟随、占领、猎杀、撤退、停止、发呆时找事 | 移动的物理（调 L2）、开火的数值（调 L3） |
| L6 脚本 | 条件和动作：把脚本翻译成对下面几层接口的调用；字幕、镜头、音视频单独一块 | 自己实现规则 |
| L7 帧循环 | 每帧按固定顺序推进各子系统 | 规则本身 |
| L8 遭遇战 AI | `simai.py` 等：只通过 L4、L5 的接口下指令 | 直接改对象字段 |
| L9 汇报 | 每秒采样、指标、覆盖检查 | 改世界 |

脚本的条件求值在私有引擎模型里跑，回调 `Sim.condition` / `Sim.action`；这两个回调就是 L6 对外的接缝，保持不变。

## 规矩（拆完后由守卫测试强制）

1. **依赖单向**：一个层的文件只导入同层或更下层的模块。`tests/test_architecture.py` 按导入关系查。
2. **不伸手进别人的状态**：子系统之间只通过对方公开的函数打交道。拿着整个模拟器对象去读写内部字段的写法（现在驻军、渗透、扫射、维修、分配、AI 几个模块都这样）要改成"给一个世界句柄 + 调接口"；`simtech`、`simtopple`、`simjet`、`simcrush` 这种只收参数的写法是样板。
3. **一个字段一个主人**：钱只由 L4 写，血量只由 L2 的受伤入口写，位置只由 L2 移动写，单位的目标和模式只由 L5 写。别的层要改就调主人的接口。守卫查赋值语句出现在哪个文件。
4. **有这个部件才推进**：对象生出来时按模板登记到各子系统的名单里，帧循环只推进名单里的对象。不再每帧把所有对象扫一遍（现在有 9 处这样的全扫）。
5. **帧顺序只写一处**：帧循环是一张有序的子系统列表。有引擎模型和没有引擎模型（`Sim(model=False)`）两种跑法走同一个 `simloop.step`、同一个顺序，只差脚本那一格里跑的是什么（模型的一帧 / Python 脚本）。
6. **审计是公共服务**：记录"哪条规则被用到"的那个集合放在 L0，任何层都能写，只能追加。

## 测试分两层

- **规则测试**：用最小世界（一张空地图、几个按模板摆好的对象）只推进相关子系统几帧，断言一条规则。目标是几秒一个。每个子系统搬出来时同时带上它的最小世界测试。
- **整局对拍**：和台上读数对拍的整局回放保留，作为"已对拍"的证据；同一条规则不必再用整局测第二遍。
- **搬迁不改行为**：每一步都是纯搬家。验收用固定一组任务的逐帧事件记录做前后比对，必须一字不差；再跑一次全量。

## 不许怎么做

- 不许按线建文件（`sim_a.py`、`sim_c.py` 之类）。
- 不许新加反向调用来图省事；真需要上层的结果，就由上层在帧循环里把结果交下来，或者下层发一个事件让上层自己取。
- 不许一次性推倒重写：一块一块搬，旧的 `Sim` 方法先留着转调新模块，直到没人调用再删。
- 不许让工具按文件名读模拟器源码来判断"做了什么"（11-17 清单工具因此在搬家后少算 401 项）：模拟器能处理的动作、条件、状态位、模块名由各层自己的登记表公布，工具只读登记表。
- 不许在交接、提示词里写 `sim.py` 行号或"某方法在某文件"：写能搜到的名字，位置以代码为准。
- 新规则必须带一个最小世界测试（`simsmall.small_world`）；整局回放只当对拍证据，不当日常回归。

## 新规则放哪个文件（给恢复的引擎线和 Codex）

先问"这条事实长在引擎的哪个部件上"，再按下表落位。只写模块名和登记表名，位置以代码为准（搜 `def 名字`、`名字 = `）。登记表都在模块里或守卫测试里，**只追加**；rebase 时别线也在末尾加行，冲突两边都留。

| 要加 | 改哪个模块（层） | 在哪张登记表加一行 | 配什么测试 |
|---|---|---|---|
| 脚本动作 | 按它作用的层挑一组：`simact_vision`（视野）`simact_player`（钱、电、科技、技能）`simact_order`（给单位下命令）`simact_object`（对象状态）`simact_ability`（技能按钮）`simact_world`（旗标、计时器、队伍）`simact_show`（字幕、镜头、音视频）（L6）。函数 `fn(sim, name, a, script)` 只把参数翻译成下层接口的调用，规则本身写进下层模块 | 那组的 `ACTIONS`（`simact.table` 合并，重名报错；清单靠它认名字）。新开一组：加进 `simact.GROUPS` + `LAYER_OF` 记 6 | 最小世界摆好对象，跑这个动作，断言世界的变化；做不到的参数分支 `return False`（自动记成缺口） |
| 脚本条件 | 同上，`simcond_world` / `simcond_object` / `simcond_vision` / `simcond_player` / `simcond_show`（L6），`fn(sim, name, a)` 回真假 | 那组的 `CONDITIONS`；新开一组加进 `simcond.GROUPS` + `LAYER_OF` | 同上；不认得的情形回 `None`（记缺口、当不成立） |
| 物体模块（AutoHeal、Toggle 这类 XML 模块） | L2。已有部件的规则加进它的模块（`simheal` `simtoggle` `simbody` `simgarrison` `simlocomotion` `simmodifier`……）；新部件新开 `sim<部件>.py`，写成"收世界句柄 + 参数"的类或函数，状态放在自己的对象里 | `LAYER_OF` 记 2；收世界句柄 → `WORLD_TAKERS`；用到世界的新能力 → `simworld.WORLD_API`；独占字段 → `FIELD_OWNER`；还要借 sim.py 里没搬的方法 → 模块自己的 `PEERS` + `PEER_TAKERS` | 最小世界 + 只推进这个部件几帧（样板：`test_simheal`） |
| 武器伤害规则（各种 Nugget、MetaImpact） | L3 `simdamage.Damage`（`deal` 按 Nugget 派发）。索敌、瞄准、开火节奏也归 L3，但还没全搬（搜 `def can_hit`、`def shots_due`）；追击和攻击状态机归 L5 | 新缓存字段 → `FIELD_OWNER` 记 `simdamage`；要销毁、改修改器、改模型状态等 L2 动作 → `simdamage.PEERS`（只借还在 sim.py 的；已搬的直接导入调用） | 最小世界里一个开火方一个挨打方，断言血量 / 状态；只做了一部分的 Nugget 写 `world.gap(GAP_WEAPON, 'XxxNugget', 缺什么)` |
| 单位命令（移动、攻击、警戒、跟随、撤退……） | L5 `simorder`：下命令 `order_*(world, peers, b, ...)`，每帧推进 `*_due`。移动的物理调 L2，开火的数值调 L3；扣钱加钱调 L4 `simmoney.Money` | 单位的目标和模式字段只由 `simorder` 写（`FIELD_OWNER`）；借的名字进 `simorder.PEERS`；玩家能下的命令另看 `simproxy.issue` 和 `simcoverage.PLAYER_ORDERS` | 最小世界里下命令、推进几帧，断言位置 / 目标；脚本动作那一层只测"翻译对了" |
| AI 规则 | L8 `simai` 和它的适配器（样板 `simpullback`、`simmicro`）：只通过 L4（`simmoney`、`simtech`）和 L5（`simorder`）的接口下指令，不直接改对象字段 | 适配器进 `WORLD_TAKERS`、`PEER_TAKERS`；暂不进 `LAYER_OF`（`simai` 还导入 sim，只被它导入的文件清单不数，`test_simcoverage_files` 会红） | 直接喂适配器一个小局面断言它的决定；AI 回放只当对拍证据 |
| 每帧要做的事 | 规则写在主人模块（`due` / `tick` 一类方法）；L7 `simloop` 只加一个格子 `fn(s, frame, tick)`：一句调用 + 门控，调主人对象（`s.heal.autoheal`、`s.repairs.due`），不调 Sim 的转调 | `simloop.CELLS` + `simloop.FRAME`（位置 = 引擎里的先后，没台上证据标 INFERRED）。两种跑法共用这一张；只推进名单里有这个部件的对象，不每帧全扫 | 格子的规则在主人模块测；改 `FRAME` 顺序会改所有录制，要拿对拍回放当证据 |

每件都要：

- **一个最小世界测试**（`simsmall.small_world`，几秒），测试名写行为。整局回放只当"已对拍"的证据，不当日常回归。
- **没做的分支记缺口**：`world.gap(GAP_*, 名字, 缺什么)`（种类在 `simworld`），清单才看得到，不静默。
- **清单怎么数到你**：清单只读登记表和导入链（`simcoverage.sim_files` 从 sim.py 按 import 算）。XML 模块名、Nugget 名要作为字符串出现在导入链能到的文件里；状态位写成 `'X' in b.status` 才算"有作用"。所以新文件必须被导入链导入，别只被测试导入。
- **分层模块不调 Sim 的转调**：调规则的真身（同层或下层模块的函数、世界 API、`Peers` 借来的还没搬的方法）。`test_sim_forwarders.FORWARDER_CALLS` 只减不增。Sim 上的转调只给 sim.py 里的旧代码和测试用，新规则别再加。
- **守卫**：`test_sim_layers`（导入方向、世界句柄、字段主人、帧顺序）、`test_sim_forwarders`、`test_simcoverage_files`、`test_architecture`。

### 拿已搬的三块核一遍

- **⑥ `simbody`（物体模块那一行）**：死亡、移除、卖楼、坠机、按时掉血是 L2 的血量部件 → 新文件 `simbody.Life`，独占缓存 `lose_of` 进 `FIELD_OWNER`；用到的世界能力（`kills note label change add blocks reblock`）补进 `WORLD_API`；卖楼退款不写钱字典，调 L4 的 `simmoney.Money.credit`；每帧格子 `lose_health`、`expire` 各一句调用。
- **⑦ `simdamage`（武器伤害那一行）**：伤害结算和各 Nugget → L3 `simdamage.Damage`，十个独占缓存进 `FIELD_OWNER`；要的 L2 动作（`destroy`、`modify`、`set_model_condition`……）当时都还在 sim.py，所以走 `simdamage.Peers`，名单 `PEERS`，登记 `PEER_TAKERS`；攻击状态机 `fight` 归 L5，没跟着搬；每帧格子 `deal`。
- **⑨c `simgarrison` / `siminfiltrator` / `simrepair`（旧模块改接口）**：旧写法拿整个 Sim 读写（`self.sim.X`）→ 世界 API 有的改 `world.X`，其余改 `peers.X`；维修扣钱、间谍偷钱改走 `simmoney.Money` 的 `held` / `charge`。登记成分层模块后，守卫才数到它们原有的转调调用（`siminfiltrator` 的 `destroy`、`send`），在 `FORWARDER_CALLS` 补登一次，之后只减。
