# 模拟器内核：物体 = 模块组合（边界和约定）

决定见 [ADR 0031](../adr/0031-simulator-module-composition.md)（模块组合、端口和适配器、扩展点、绞杀者迁移）、[ADR 0032](../adr/0032-one-rules-source-per-part.md)（每块规则只留一份）、[ADR 0033](../adr/0033-kernel-no-private-dependency.md)（内核零依赖私有模型）和 [ADR 0034](../adr/0034-multi-battlefield-and-own-ai.md)（多战场：游戏适配器、快照、性能）。迁移顺序和逐字段归属在私有仓库 `work/re/sim_split/module_plan.md`；分层和层守卫仍按 [sim-layers.md](sim-layers.md)，内核是在层的基础上加扩展点。这里只写边界和约定：不写程序地址，不转写程序或《将军》源码，规则的来源只许是 XML、台上读数和行为说明（0032 第 1 条）。

文件已归进 `engine/` 包（[ADR 0036](../adr/0036-simulator-package-layout.md)）；下文的 `simX` 是 ⑩ 之前的平铺名，新位置照 0036 的表找。

## 1. 四个东西

| 东西 | 是什么 | 持有什么 | 不许 |
|---|---|---|---|
| 物体（`sim.Body`） | 地图上的一个对象，继承提供模块集合和按接口查询的 `Thing` | 名字、模板、玩家、队伍、坐标、朝向、生死和黑板（状态位、模型状态、升级位） | 存已迁移部件的私有状态（如回血计时） |
| 模块（`Module`） | 一个 XML 模块标签的运行时实例，一个物体身上可有多个 | 自己的状态；指向自己数据对象和所属物体 | 读写别的模块的字段；模块级（文件级）可变变量 |
| 模块数据（`ModuleData`） | 同一模板同一标签的解析结果，同模板的物体共用 | 从 XML 读好的数值（帧数、百分比、条件……） | 运行时状态（它是只读的） |
| 世界（`World`） | `Sim` 持有的内核世界；整局状态归 `Sim` 及其持有对象 | 调度、模板块与模块数据缓存、审计、缺口、当前调度帧 | 与别局共享可变状态（0032 第 6 条，多战场） |

## 2. 模块的固定接口

照引擎的做法：一个模块实现几个接口，调用方按接口找模块，不按具体类找。接口名取引擎里的名字（整理见私有仓库 `work/re/sim_split/sage_modules.md`）；方法用我们自己的 Python 名字。

| 接口 | 方法（语义） | 谁实现（例） |
|---|---|---|
| 更新 `Update` | `update(frame)` → 下次多少帧后再醒（至少 1）；返回 `SLEEP` 就等唤醒。`PHASE` 选格（§4）；`RUNS_DISABLED` 预留，禁用门控由各模块按需处理 | 回血、寿命、开关、采矿、压制、特殊能力…… |
| 血量 `Body` | 每物体至多一个：`attempt_damage(amount)`、`attempt_healing(amount)`、`health()` / `max_health()`；血量统一经 `set_health` 写，受伤分档接口预留 | ActiveBody、StructureBody、ImmortalBody、PropBody…… |
| 受伤 `Damage` | `set_health(..., tell=True)` 写血后，血量下降广播 `on_damaged(旧 HP)`，其余情况广播 `on_healed(旧 HP)`；`on_damage_state` 预留 | 回血（受伤推迟、唤醒）；压制在 `suppression` 格采样 |
| 死亡 `Die` | `on_die(info)`（`module.Death`：帧、原因、死法和触发来源）：`simbody.Life._out` 先设慢死停留时间，再按模块顺序广播；删除不广播 | 现有：SlavedUpdate 告诉造它的 Spawn 排补充、Contain 经 `World.vacate` 让宿主放出 / 按 KillPassengersOnDeath 杀乘员；CreateObjectDie 经 `World.create` 处理寿命到期留物和坠机，FireWeaponWhenDead 经 `World.fire` 交宿主排死亡伤害 |
| 移除 `Destroy` | `on_destroy()`：死（在 Die 之后）和删都广播一次，同在 `Life._out`（B4c） | 现有：SpawnBehavior 清补充队列、删活着的子体（`World.remove`）；Contain 删乘员（死时已空）；SlavedUpdate 被删且母体活着时记缺口 |
| 创建 `Create` | `World.build` 调 `on_create(frame)`；`World.attach` 跳过创建回调，`on_build_complete()` 尚未接线 | 寿命（算死亡帧）、初始状态、等级、子体 |
| 升级 `Upgrade` | 按 XML 的触发 / 冲突 / 必需升级判定是否生效；`on_upgrade()` / `on_remove()` | StatusBitsUpgrade、各种 Upgrade、升级触发的回血 |
| 容器 `Contain` | `interfaces.Contain` 提供乘员、原归属和升级状态接口；进出条件由 `Garrisons` 处理，死亡和删除由模块回调请求宿主清理 | 驻军、运输；渗透走 `Infiltrate` |
| 碰撞 `Collide` | `on_collide(other)` 预留 | 碾压用 `Crush` 模块数据，规则见 `simcrush` |
| 生产 `Production` | 排队、进度、取消、出口接口预留 | 现行生产流程在 `Sim` |
| 特殊能力 `SpecialPower` | `power()`、`ready_at()`、`set_ready_at(frame)`（M8：冷却在模块上，一个物体可以有好几个）、`cast(target)`（以后） | SpecialPower 一族（15 个 SpecialPowerModule 标签） |
| 移动和命令 `AIUpdate` | 命令状态机和移动接口预留 | 当前命令见 `simorder` |

上表是核心接口；引擎还有一批专项接口（出口、停靠、弹体、子体 / 被奴役者、被卖通知、跑出地图……），搬到那一族时再加进 `interfaces.py`（`FAMILY`），不预先建。已加：寿命 `Lifetime`（M1，一个物体至多一个：`die_frame()` / `set_die_frame(frame)`）；倒塌 `Topple`（M2，一个物体至多一个：`is_toppled()` / `gone_frame()` / `knock(frame, speed)` / `fall_where_it_stands(frame)`；模块删掉自己的物体走 `World.remove`）；碾压 `Crush`（M3，CrusherInfo，只有数据：`crusher_level()` / `crushable_level()`；谁压谁还在移动里）；自动存钱 `Deposit`（M4，AutoDepositUpdate：`rules()` / `next_frame()` / `capture(frame)` 返回占领奖金并重设钟；付钱走 `World.pay`，宿主不给中立方）；开关 `Toggle`（M5，ToggleStatusSpecialAbilityUpdate，一个物体可以有几个、按块的顺序：`rules()` / `state()` / `entered()` / `press(frame)`，有 UnpackTime 的按下在 toggles 格到点再切；切到新状态后经 `World.toggled` 告诉宿主重设状态位、修改器和 LocomotorSet 速度，等修改器和移动族自己读接口时去掉这个钩子。模块数据在模块造出来之前就要读的（`Sim.add` 先放第一状态的状态位再挑武器）用 `World.data_of(模板, 标签)`，和模块拿到的是同一份解析。几个同族模块的状态在逐帧记录里合成一个字段（`toggle_at`），其 `STATE` 列模块状态，`RECORDED` 留空）；压制 `Suppression`（M6，SuppressionUpdate，一个物体至多一个：`rules()` / `hits()` / `is_suppressed()` / `until()` / `next_sample()`；每帧问宿主盖住它的压制场 `World.suppression_at`（场由武器族的 SuppressionNugget 留下，宿主存），按出生相位每 UpdateDelay 采样一次，进出压制经 `World.modify` 让宿主重读修改器；模板里 `xai:joinAction="Remove"` 的块由端口去掉，继承来的模块就没了）；子体 `Spawn` / 被奴役者 `Slaved` / 附着 `Attach`（M7：SpawnBehavior 一个物体可以有几个，`module_id()` / `child()` / `unpack_child()` / `children()` / `refills()` / `adopt()` / `child_died(template, frame)`，自己的物体结束时经 `Destroy` 清空补充、删掉子体（B4c），补充排队后睡到到点在 spawn 格经 `World.spawn` 让宿主造；SlavedUpdate 一个物体至多一个，记谁造了它，`enslave` / `slaver()` / `slaver_module()` / `spawner()`，子体模板没有 SlavedUpdate 时宿主用 `World.attach` 补一个；AttachUpdate 只有数据，`module_id()` / `rule()`；SpawnBehavior 走统一模板合并，Remove 删掉匹配的块。Spawn 和 Slaved 各自声明 `STATE`；Spawn 经 Body 转发逐帧字段，Slaved 通过 `RECORDED` 直接记录 `spawn_parent` 和 `spawn_module`）；采矿 `OreMiner`（M9，OreMinerBehavior，一个物体至多一个，只存这一趟：`trip()` / `set_trip(trip)`；谁算矿车从 KindOf HARVESTER 改成"有这个模块"，原版和全部任务自带模板上两者一致；矿车之间抢矿井、矿场排队的循环还在 `simmine` 的 mine 格里，等矿井也成模块再搬；DeliveryCapacity 和苏联 / 帝国矿车追加的 ObjectStatusValidation 照旧不读）；展开 `Unpack`（M10，StructureUnpackUpdate，一个物体至多一个，只存展开结束帧：`frames()` / `end_frame()` / `set_end(frame)`；按电力系数拉长的算法在宿主 `Sim.add`；UnpackTime 在声明它的来源文件用本地 Defines 展开，缺项查 GlobalDefines。同一模块的子块省略该属性时保留父值）；卖楼 `Sell`（M10，StructureSellUpdate，一个物体至多一个：`gone_frame()` / `start_sale(frame)`；退款、SOLD 仍在 `simbody.Life.sell`，到 SellTime 在 expire 格经 `World.remove` 删掉）；冷冻 `Freeze`（M11，SecondaryDamageTracker，一个物体至多一个：`rules()` / `held()` / `stage()` / `add(amount)` / `melt(dt)` 返回档位变没变；没有自己的更新格，冷冻光束累计和每帧消散仍由宿主 `simdamage.chill` 按原顺序驱动，档位变了由宿主重读修改器、DIE_ON_ENTER 由宿主杀；冻住时换的护甲 ArmorSet 不属于这个模块，留在 `simunits.frozen_armor`）；升级等级 `LevelUp`（M12，LevelUpUpgrade，一个物体可以有几个、按块的顺序：`module_id()` / `rules()` / `active()` / `set_active(on)`，只存"有没有生效"；升级到达时的算法（等级表、老兵升级、精英血量）仍在 `simlevel.receive`，由宿主给升级时调；不走内核的 Upgrade 广播——那个在 modify 时才动，不在给升级的那一刻；等级 `level_rank` 留在物体上：引擎里经验等级是 Object 的 ExperienceTracker，不属于哪个模块）；光环 `Aura`（M12，AttributeModifierAuraUpdate，一个物体可以有几个：`rules()` / `last_beat()` / `pulse(frame)` 问这一刻该不该刷新并推进节拍；挂到谁身上、挂多久、重读修改器仍在宿主 `simmodifier.aura_tick`；端口读取合并后的光环块，宿主按有效块顺序使用；挂在物体身上的修改器 `auras_on` 和修改器之前的原值 `base` 留在物体上：引擎里修改器表是 Object 自己的，`base` 是宿主 modify 的缓存，移动和射程修正仍由宿主从这份原值计算）；维修 `Repair`（M13，RepairUpdate：`rules()` / `measured()` / `job()` / `set_job(job)` / `refused()` / `refuse()`，只存规则、进行中的维修和"这局拒修"；谁能修（AI 难度门、低资金门）、扣钱、回血的循环仍是宿主 `simrepair.Repairs` 的 repairs 格；原版建筑的 RepairUpdate 写在 `Includes/GenericBuildingRepair.xml` 里，模板端口通用展开 include，片段插回原位置）；指派 `Assign`（M13，AssignSlavesTargetObjectSpecialPower，同时是 `SpecialPower`：`plain()` / `target()` / `assign(target, rate)`；按下、挑目标、治疗量仍在宿主 `simassign.Assignments.press`，派出后在 assignments 格由模块自己每帧回血、修满，或任一方死亡、双方异主、无活子体、任一方移动、目标血量被外部改动时停止，这一格只剩模块）；容器 `Contain`（M14，核心接口，GarrisonContain / ContestableGarrisonContain / TransportContain 各一个类：`rules()` / `passengers()` / `let_in(thing, bits)` / `let_out(thing)` / `home()` / `keep_home(owner)` / `give_home()` / `granted()` / `set_granted(upgrades)`，只存乘员、给每个乘员加的状态位、第一个人进来前的主人、单个乘员经监听器给的升级；进出条件和过程仍由宿主 `simgarrison.Garrisons` 管。楼毁和直接删除由 Contain 回调当场请求宿主清理。模板按容器和 id 合并，宿主按用途取首个匹配模块，乘员和弹出队列按宿主 serial 管理；残血线 MaxHealthReallyDamagedPercentage 是 ActiveBody 的，宿主 `simgarrison.really` 读）；渗透 `Infiltrate`（M15，InfiltratorContain，一个物体可以有几个，宿主读第一个：`rules()` / `entered(slice)` / `mark(slice)` / `blocked_until()` / `block(frame)`，只存规则、已测切片里"这栋楼已被渗透过"的标记和港口阻断到哪一帧；谁能进、走进去、效果（观察者、停电、瘫痪、偷钱）和间谍的结束仍在宿主 `siminfiltrator.Infiltrators` 的 `infiltrate` 格粗步移动帧——观察者、停电、瘫痪落在别的物体或玩家身上，不属于这栋楼的模块；原版的块写在 `Includes/InfiltratorContain*.xml` 里，同样由模板端口通用展开 include；KILL 楼有兄弟块的标记由宿主按模块个数加）。这四族都用 `STATE` 声明模块状态；`RECORDED` 留空，因为它们不直接输出逐帧字段。计时 `Clocked`（S 11d 第 10 步，一个物体可以有几个、按造出的顺序：`clocks()` 给出模块状态里的帧数，`set_clocks(values)` 写回并像模块自己的设值那样唤醒；自愈、寿命、卖楼、展开四个模块实现，供局面交换带模块计时）。`unpack_parent` 不搬：引擎里是物体自己的 producer，不属于哪个模块。

寿命到期调用 `world.kill(物体, 原因, death, cause)`，由宿主进入统一死亡流程。模板声明的寿命传 `cause="lifetime"`，供死亡留物模块判断。让血量模块接管这一入口仍是后续计划。物体造出来以后才补一个模块（遭遇战 AI 补读原版寿命）用 `world.attach(物体, 标签)`。

约定：

- **接口是类，不是鸭子类型**：模块继承它实现的接口类（在 `engine/kernel/interfaces.py`），`thing.find(接口)` 在物体有模块时按接口惰性缓存，重设模块列表时清缓存；`ONE` 接口返回单个实现者或 `None`，有多个实现时报错。不许 `hasattr(m, '某方法')` 探测，不许 `isinstance(m, 某具体模块类)`。
- **模块之间只三种说话方式**：① 调另一模块的接口方法（经 `thing.find`）；② 写 / 读物体黑板（状态位、模型状态、升级位，经物体的方法）；③ 广播（内核按接口通知血量变动、创建和升级，宿主的 `Life._out` 通知死亡与移除）。
- 接口要加方法 = 架构变更，由重构线 R 改 `interfaces.py`。

## 3. 工厂：按 XML 标签登记

- 一个模块类用 `@module('AutoHealBehavior')` 登记一个或几个标签（`engine/kernel/factory.py`）。数据类 `parse(head, inner).seal()` 解析并封存模板端口给出的 XML 块。
- 造物体时，工厂按已登记的标签向模板端口要块，每块造一个模块实例。
- 解析结果按"模板 + 标签 + 序号"缓存在`World.data`里，同模板共用一个数据对象；不在模块文件里放缓存。
- 清单做 XML 普查，并用导入链源码（`simcoverage.sim_code()`）识别模块名。

## 4. 调度：休眠和唤醒

- `simloop.FRAME` 是有序的**格子**名单，更新模块用 `PHASE` 选格。调度器只推进唤醒帧 ≤ 当前帧的实例，先按 `ORDER`，再按入调度顺序；模块跑完再跑该格的宿主代码。相位守卫见 `tests/guards/test_kernel.py`。
- `update` 返回 n：n 帧后再醒；返回睡死：在格内标成 `None`，直到 `world.wake(模块, 帧)` 设回唤醒帧。同一模块对同一帧重复唤醒不算两次；唤醒到更早的帧覆盖更晚的。
- 只有登记了更新的模块才进名单；不许每帧扫所有物体（0029 规则 4 的落实）。
- 一格里挂几个模块类时，类上的 `ORDER` 定先后。新加格子、改格子顺序 = 改所有逐帧记录，是架构变更，要台上证据。

**已知和引擎不同（迁移期有意保留，等台子判）**：引擎是一个按"唤醒帧 + 少数几个相位"排序的全局队列，同一帧里谁先谁后由队列定，我们按格推进（先所有回血，再所有维修……）；引擎新造的模块排到下一帧才第一次醒，我们当帧轮到那一格就跑；引擎对"已经醒着、又被要求下一帧醒"的不改，我们迁移期照做。迁移期的验收是逐帧记录前后一字不差，这两条改不改另立决定。

## 5. 世界：全部状态在实例里

- 一局的可变状态在 `Sim` 及其持有的对象里，内核部分由 `Sim.world` 持有。模块级可变变量和 `global` 由守卫限制；`TAGS` 是只读视图，登记由模块装饰器写入。
- 按来源区分的只读模板结果（含任务 XML 和生产模板查询）可进程内共用。升级、存活前置和禁令仍实时判断。共享缓存见 `tests/guards/test_kernel.py` 的 `PROCESS_CACHES`。
- `Sim.living()` 通过宿主 `simliving.py` 读取每局 `World` 缓存的存活视图，顺序与 `bodies` 一致。`Observe.living()` 使用完整视图，`Brain.living()` 用 `unspawned=True` 排除有 `spawn_parent` 的子体。每次调用都返回独立的列表。增、换、删物体、修改 `alive`、`Slaved.enslave`（包括直接调用）和世界还原都会使视图失效，快照只保存原始状态。
- 多战场：两个世界在同一进程交替推进，各自的逐帧记录必须等于各自单独跑的（守卫测试）。

## 6. 对外端口

模拟侧用以下端口连接脚本、命令、AI、观测和模板数据。测试台上已接入的观测和命令范围见 §9.1。

**内核对私有模型零依赖**：依赖只许"私有模型 → 内核端口"一个方向。内核（`engine/**`）不导入、不按路径加载私有仓库的文件。加载与钉版本在内核外，脚本走 `sim.engine_model()`，AI 走 `modelpin.package`，由 `modelpin` 核版本。无私有模型仍可跑公开脚本、推演规则、下模拟命令、跑玩家代理（`experimental/cnv/proxy/`，只经 `simproxy` 的端口观测和下令）；只有私有遭遇战 AI 需要模型。

| 端口 | 内核给什么 / 要什么 | 接在上面的 |
|---|---|---|
| 脚本执行器 | 宿主调用 `Executor.step()`；执行器经 `scripts.World` 调 `begin`、`update`、难度及 `condition(eng, name, args)` / `action(eng, name, args)` | 公开执行器可加载原版 `.map` 和自制关卡脚本；私有脚本核心可选替换 |
| 玩家输入（命令） | `engine/ports/command.py` 通过每局的 `Sim.commands` 接收和分派命令 | 玩家代理、自动玩家、地图页和已迁移的脚本命令 |
| AI | `engine/ports/ai.py`：`Settings` 提供任务的 AI 移交时间、暂停、开关、敌人优先级、禁建和边界，并接收人格及队伍查询登记。`drive(world, plugin, frames)` 每推进一帧就调插件 `tick(frame)`，到结局停止。`PlayerSystems` 提供电力、建造资格、升级卖家、菜单、生产队列、原型、工程师入口和钱包（`held` / `charge` / `multiply_income`，后两项是 AI 捷径）。战况读 `Observe`，射程规则查 L3 `simrange`，下令用自身持有的 `commands`；`simai.PEERS` 只借 `modify` | 私有遭遇战 AI（`simai.SimAI` 是插件）；自研 AI 是后续目标 |
| 观测记录 | `Observe.things` / `living` 给全局对象；按玩家过滤用 `side_sees` 等查询。另提供逐帧字段、审计、缺口、计数器及内部查询（如 `firing()` / `volleys()` / `attachments()` / `expected_damage()`）。局面交换读取 `contents`、`home`、`jobs`、`sciences`、`player_upgrades`、`power` 和 `relations` 等 | `simrecord`、报告和指标（L9）、清单、代理等 |
| 模板数据 | 模板 → 继承好的模块块列表、种类、几何；零售数据 + 任务自带 XML | 宿主用 `simunits.module_blocks` 提供合并后的模块块；模块数据类用 `engine/ports/templates.py` 的 XML 读取工具解析 |

`engine/modules/weaponset.py` 解析 `WeaponSetUpdate`，并通过 `WeaponSet` 接口持有每个物体当前的武器（`weapons`）和按状态选枪的槽位（`slots`）。`Sim.add` 和 `simbody.fill` 经 `weaponset.equip` 装备，模板没有有效模块块但有武器或槽位要装时补挂模块。`simmodifier` 重选武器和计算射程后用 `hold` 写回，`Body.weapons` / `slots` 只读转发，模块的 `STATE` 负责保存。战斗模板、状态选枪、AI 估值和覆盖清单仍共用模板端口的解析，略过注释和已移除的块。AI 估值在参与计数的槽内按 `Ordering` 取首个符合条件的条目。

私有模型只导入 `engine.ports` 是接入约定。公开执行器经 `simexec` 接入原版和自制关卡脚本。遭遇战入口 `simai_run.py` 负责建局，`simai.SimAI` 是 AI 插件。

`Observe` 的旗标、资金、队列、报告等直接读取宿主容器的接口，`Settings` 的容器属性及生产队列的行（`simproduce.Production.jobs`，S7b）用 `engine/ports/readonly.py` 的实时只读视图。读取嵌套字典、列表和集合也得到只读视图。视图保留对原容器的引用，宿主替换整张表后应重新取；物体引用仍按原样返回。

## 7. 扩展点：加一样东西要写什么

动手前先回答"它挂在哪个扩展点上"；挂不上就是架构变更，先找重构线 R 设计扩展点（0031 第 4 条）。

| 要加 | 写什么文件 | 登记到哪 | 配什么测试 |
|---|---|---|---|
| XML 物体模块（新标签） | `engine/modules/<族>.py`：数据类（`parse`）+ 模块类（继承它实现的接口）；同族已有文件就加进去 | `@module('<标签>')`（不改任何中心文件：`engine/modules` 包导入时自动导入目录里每个文件） | `tests/modules/test_<族>.py`：最小世界摆一个这个模板的物体，只推进几帧，断言行为；测试名写行为；有台读数的断言读数 |
| 已有模块的新属性 / 新分支 | 那个模块的数据类和模块类 | 无 | 同上，加一个用例；做不到的属性组合 `world.gap(...)` |
| 脚本动作 | 按作用对象挑一组 `simact_*`（以后在 `engine/script/`）：函数只翻译参数，已迁移的单位命令和技能按钮翻成 `Command` 后用 `Sim.commands.do` 下发，规则留在宿主或相应模块 | 那组的 `ACTIONS` | 最小世界里跑这个动作，断言世界的变化；不认得的参数分支 `return False`（记缺口） |
| 脚本条件 | 同上，`simcond_*`，只读接口和黑板 | 那组的 `CONDITIONS` | 同上；不认得的情形回 `None` |
| 武器效果（各种 Nugget、MetaImpact） | 入口仍是 `simdamage.Damage`；N1 起 `engine/combat` 登记表（`@nugget(kind, phase)`，执行顺序只看 `registry.ORDER`），已接 Projectile（launch）/ DOT 登记、DamageContained、SecondaryDamage、Suppression、Paralyze、Sweep（hit：直接命中目标，每发一次；N2b、N3d 绑宿主的 `sweeps.fire`）/ LineDamage（aim）/ Damage、LeechPercentMaxHealth、LeechHealth、StripMaxHealthPercent（victim；N2a，吸血回补 `leech.refund`、DOT 账本 `dot.tick`（N2c，宿主收回仍到期的条目）在帧末）/ Lift、Attach、SpecialPower、AttributeModifier（effect：所有 victim 之后、帧末扣血之前，只对主目标，每发一次；N3a、N3b、N3c）/ MetaImpact（N3e，不进 ORDER：碰撞上下文另走，`meta_impact.detonate / launch` 由弹体到达派发，`tick` 在帧首、弹体到达之前推进轨迹），其余 Nugget 仍在宿主 | 处理器只读 `registry.Context`：读游戏数据的规则（护甲 × 侧后、无侧后护甲、弹速、秒转帧、驻军乘员、冷冻门槛、记缺口）和宿主的账（DOT 表、冷冻记账、压制场、EMP 截止）由宿主递进来，包里不导入 simunits；effect 阶段的宿主调用收在 `simdamage.EffectHost`（`Context.host`：Lift 规则缓存、计时、附着链、重读修改器、升级门槛、技能模块缓存、伪装、读 / 挂修改器、目标过滤；只转手的计时、重读修改器、目标过滤、MetaImpact 的击飞物理（simunits.meta_impact_*）直接绑宿主的函数，不再包一层；MetaImpact 的体高 / 抗冲击缓存、地面高度、落水账也在这里） | 最小世界里一个开火方一个挨打方，断言血量 / 状态；只做了一部分写缺口 |
| 单位命令 | 在 `simorder` 接下令和推进，移动物理调 L2，开火调 L3 | 玩家输入从 `Sim.commands` 查分派；`@command` 是迁移目标 | 最小世界下命令、推进几帧，断言位置 / 目标 |
| AI 行为 | 私有 AI 的决策在私有模型；公开接入见 `simai` 及其适配器，建局入口是 `simai_run.py` | §6 的 AI、观测和命令端口 | 直接喂宿主一个小局面断言回答；AI 回放只当对拍证据 |
| 玩家系统规则（钱、电、科技、技能书） | 钱走 `simmoney.Money`，科技和升级走 `simtech`，电力及技能书入口仍在 `Sim`；玩家系统目录是迁移目标 | 现有系统的接口；单个物体上的效果写成 Upgrade 模块 | 最小世界断言钱 / 电 / 解锁 |
| 每帧要做的事 | 不加格子：写成更新模块，`PHASE` 选现有的格 | 模块类上的 `PHASE` / `ORDER` | 同 XML 模块 |

每件都要：

- **一个最小世界测试**（`simsmall.small_world`，几秒）；整局回放只当"已对拍"的证据。
- **没做的记缺口**：`world.gap(种类, 名字, 缺什么)`，不静默。
- **来源写清**：台读数（写台子和读数）/ XML / INFERRED。不许照程序或《将军》源码转写（0032 第 1 条）。
- **私有模型有对应类的**（它的物体部分已冻结，0032 第 4 条）：搬或新写时拿它对一次，对不上上台判谁对。

## 8. 守卫（`tests/guards/test_kernel.py`，加上 sim-layers 的层守卫）

1. 模块文件互不导入；只在自己身上赋值，改别人只调接口；按接口取模块。
2. 中心只许变小：`sim.py` 行数、`Sim` 方法数、`Body` 字段数、`simunits` 函数数、还没换成调度阶段的格子数，只减不增。
3. 不许模块级可变状态和 `global`（今天的例外列在名单里，只减）。
4. 多世界：两个世界交替推进 = 各自单独跑。
5. 工厂登记的每个标签都有按名字的模块测试。
6. 内核零依赖私有模型（[ADR 0033](../adr/0033-kernel-no-private-dependency.md)）：`engine/**` 里不出现私有仓库的导入、路径和名字；在 `CNV_ENGINE_MODEL` 指向不存在目录时，子进程复跑本守卫文件（含多世界用例），不得跳过。
7. 状态声明：守卫检查每个模块类的 `STATE`；精确快照往返的验收见 §9.2。
8. 性能和 AI 观测的目标见 §9。高峰最慢段低于 1 倍实时由日报标 `!!`；端口守卫检查导入和世界句柄边界。
9. 血量唯一写点是模块的 `engine.modules.body.Body.set_health(hp, max_hp=None, tell=True)`。伤害、治疗和宿主设血入口都汇入这里；`tell=True` 经 `Thing.health_moved` 广播，建物体和死亡清零用 `tell=False`。守卫检查 `sim*.py` 和 `engine/` 中对 `hp` / `max_hp` 的写点。

## 9. 多战场要的三样（[ADR 0034](../adr/0034-multi-battlefield-and-own-ai.md) 第 6、10 条）

### 9.1 游戏适配器：真游戏也是端口的一个适配器

- `experimental/testbench/gameport.py` 是真机端口的适配器，目前有固定地图 `FORMSS` 的契约。观测按契约读取 HUD 计数器、任务秒和可用的逻辑帧；物体用名字绑定模板、归属及可用的在场信号。缺测值用 `MISSING`，没有读取通道的查询报 `Unsupported`。用于引用的 `Ref` 含运行 ID、名字和代次。
- `GameCommands` 当前只接受玩家对契约公布的整组单位下达的移动命令。目的地用世界坐标（`pos` 或 `@x,y`）。适配器向传输层发镜头、框选、右键输入。有计数器可作回执时，须见到后续采样读到契约的完成值才确认成功；回执未到时，`sent()` 中该命令的结果为 `None`。
- `Recorder` 记录传输问答，`Replay` 按顺序核对问答。归档转录命令见 [know-how.md 的测试工具用法](know-how.md#测试工具用法编号沿用-handoff-里的)。让 AI 和玩家代理共用这套端口仍是目标。
- `check` 查路由，`do` 分派并返回该路由的结果。`post` 检查脚本行路由和事件形状，通过后将命令原样入队，到点经 `do` 执行。`post_line` 接收按名字书写的脚本行；`Commands.line` 拒绝携带物体编号的 `unit_serials` / `target_serial`。按真游戏定义共同命令集合、统一前置检查和拒绝理由仍是目标。
- 已选中的物体直接传对象，跨命令端口则用 `Thing.serial`。只有输入本身是名字时才由入口解析。端口用 `objects='serial'` 和 `units` 传单位序号，用 `target_serial` 传选好的攻击或占领目标，也可指定生产所用工厂。`target` 可留显示名。序号失效时跳过该单位或拒绝找不到的目标。宿主需要确认对象仍在世界时用 `simworld.held` 检查登记身份。AI 的招募包装、目标编号和猎杀状态也按物体序号保存。保留玩家命令的名字路由时，用 `unit_serials` 和 `target_serial` 标记已选物体（例如 SimUI）。`unit_serials` 与 `units` 中的名字一一对应，编号对应的物体名字不符时拒绝整条命令，已离开登记表的物体不会被后来的同名物体替代。点名输入由 `Commands` 解析。
- 经 `do` 下发带 `objects` 的移动命令时，`drop_target` 先清攻击目标，单体移动的 `face` 是到达后的朝向（弧度）。独立的 `face` 命令令单位停下并朝向 `place`。AI 用 `attack` 的 `goal_only=True` 只改目标，保留当前模式、路径和跟随状态。可只给 `target_serial`，显式目标找不到就拒绝，省略名字和序号才清除目标。

### 9.2 整局快照和还原（端口能力）

模拟侧已能从快照恢复到同一任务的新实例。还原时按 serial 匹配，快照里有而新实例里没有的局中物体和后挂模块会补建，跳过创建回调，调度照快照恢复。新实例多出物体、物体身份或模块不匹配、执行器未支持快照时会报错。模拟侧另有公开局面交换格式；真机导出和摆入仍是目标。

| 级别 | 用在哪 | 内容 | 验收 |
|---|---|---|---|
| **精确快照** `simsnap.snapshot(sim)` / `restore(sim, data)`，带遭遇战 AI 用 `simaisnap` | 同任务的新实例可在另一个进程恢复 | JSON 快照含内核、宿主和脚本执行器状态。落盘用 `snapfile.save(path, snapshot, **meta)` / `load(path)`，将快照和调用方元数据封装成 gzip JSON，经临时文件原子替换 | 逐帧记录、末态快照和最终报告与连续运行一致 |
| **局面交换** `Battlefield`（一个公开的数据格式） | 当前可在模拟侧导出和摆入，目标是真机局面交换 |模板、归属、位置朝向、血量、状态位、升级、等级、乘员及驻军前归属、生产进度及已付款、AI 建造场队列、模块计时（自愈、寿命、卖楼、展开）、玩家资源和外交、脚本旗标、计数器、计时器和目标 | 模拟侧 `round_trip` 逐字段核对，未还原的字段须有对应缺口；格式舍弃的状态见 `NOT_CARRIED` |

宿主 `simsnap` 和外层 `simaisnap` 分别检查自己的格式版本（各自模块里的 `VERSION`），版本不符的快照整体拒绝。读 `VERSION` 时由 `version()` 生成 `<SHA-256 前 8 位十六进制>.<SEMANTICS>`。摘要包含字段归类表里快照真正携带的部分（`simsnap.kept`：STATE、交给端口的 KERNEL / EXECUTOR / HOST / BRAINS / MODEL 和部件名；WIRE、CACHE、STATIC、ALIAS 由新世界自己造，增删不换版本）和选定编解码函数的语法树，宿主还纳入各登记模块类的 `STATE`。跨版本不迁移：拒绝时报错写明两边版本，调用方重拍。只有摘要未覆盖的格式语义变动才手加 `SEMANTICS`，并在提交说明里写原因。宿主保留 `areas.missing`、原样入队的命令和脚本参数，按对象或序号保存驻军、渗透、采矿等关系，武器和槽位在 `WeaponSet.STATE` 里。宿主先检查版本和结构，再由执行器检查并恢复自己的部分。AI 外层在创建大脑前检查两层格式，并拒绝 `level`、`seed`、`blocks` 或 `record` 不一致的快照。

- `engine/kernel/snap.py` 负责 JSON 值和引用的编解码，物体引用按本局 serial 恢复，模块引用按物体 serial 和模块在该物体上的位置恢复，宿主专用值经 `extra` 扩展，无法编码的值会点名报错。模块按 `STATE` 序列化，宿主检查新增字段时同时查实例字典和 slots。
- 精确快照依赖 §5 的实例状态归属。守卫检查状态声明及多世界隔离，模块和工具测试覆盖快照往返，`simrecord snap` 的验收见 [testing.md 的耗时一节](testing.md#耗时)。
- 带遭遇战 AI 的局用 `simaisnap.snapshot(w)` / `restore(w, data)`，宿主用 `Sim(model=False)`，AI 仍经插件运行。字段按 `SIMAI`、`BRAIN`、`UNIT` 分类，漏项报错。每个大脑单独通过插件 `snapshot` 端口拍一份：`Taker(roots, key)` 以大脑的 MODEL 字段为根，`ref(x)` 为宿主保留的插件值生成记号，`taken()` 输出 JSON 数据。恢复先按阵营和人格创建大脑，再写回宿主，随后用 `Putter(roots, data, obj, wire)` 写回插件状态并用 `get(记号)` 取回引用。同一会话内共享的对象还原后仍共享。`key` / `obj` 按序号对应旧局与新局的物体或 Unit，也可对应大脑或 SimAI。原型和插件引用的物体交给 `simsnap` 当额外的根。随机数生成器保留状态，撤回单位当前路径以引用关系恢复，后来下令取消的撤回保持取消。XML 对象从根路径找回，已知的宿主战斗闭包由 `wire` 重建，缺端口和不能还原的闭包会被点名。启用 `record=True` 时，快照还保留 HOOKS 9 轨迹。Run 按首次出现排序，轨迹据 Run 的身份取序号，`_rec_mem` 保留最近一次见到的内存是否仍是当前那份。逐帧续跑、轨迹和拒绝条件见 `tests/tools/test_aisnapshot.py`。
- 局面交换由 L9 `simbattlefield.py` 实现，文件头定义 `battlefield/1`。`export(Observe(sim))` 只读局面；`check(doc)` 检查格式，`preflight(sim, doc)` 还检查宿主的地图、玩家、模板和物体名等，`refuse(sim, doc)` 汇总问题并拒绝摆入。`place(sim, doc)` 的宿主用同图空局，按玩家、物体（含乘员和生产队列）、玩家回读、脚本状态的顺序处理，并返回带字段路径的缺口。局面摆入使用自己的时钟，生产队列的满进度帧、模块计时（物体的 `clocks`，经 `Observe.clocks` 读、`interfaces.Clocked` 写）和计时器按切点换算。`round_trip(host, doc)` 摆入后再导出，换回原文件时钟逐项比较，返回差异及覆盖它的缺口，缺口为 `None` 表示该差异没有解释。

### 9.3 性能：一个世界一个进程，高峰负载要快过实时

- **运行时一个世界一个进程**（后端开几个战场就开几个进程，用满多核）；同一进程多个世界只用于测试和批量推演的单机便利，不当运行时的并行手段。
- **高峰负载基准**：`simbench_peak` 普通版新建合成局面，`--ai` 默认从双 AI 交战的 `aipeak` 开局，`--ai --from SECS` 经 `simbench_peak.ai_start` 从该场景首个超过 SECS 的 tick 的快照开始计时。起点经 `snapfile.cached` 按场景名、场景内容、切点、两层快照版本及模型钉版存在 `work/cache/snaps/`，缺失或恢复被拒时重拍，结果用 `snapfile.digest` 标出起点文件。两种模式都量**实时倍数**（模拟秒 / 墙钟秒）和分段耗时。目标是高峰负载下 > 1 倍实时（ADR 0034 第 10 条），快进要远快于实时。11-17 的起点：原版关开头约 6 倍实时，带 AI 的遭遇战开局约 1.5 倍。
- **速度守卫**：固定任务用 `simrecord time DIR`，默认测三次取最小值。`simrecord compare BASE NEW` 在基准运行耗时至少 1 秒时标记超过 10% 的回退。高峰最慢段低于 1 倍实时由日报标 `!!`。休眠唤醒（§4）和减少全局遍历是主要提速手段。

## 10. 迁移期怎么和旧代码共存（绞杀者）

- 今天的 `Body` 就是物体：先长出 `modules`，字段一族一族搬进模块实例；外面还在读的字段留只读转发属性（名单只减），写一律走模块接口。转发写成 `Body` 上的 `名字 = kernel_module.forward(接口, 读法)`，名字列进 `Body.FORWARDS`（逐帧记录照旧当字段记，没模块的记 None，或 `forward(..., default)` 给的旧默认值，如 `toppled` 的 False）和 `tests/guards/test_kernel.py` 的 `BODY_FORWARDS`。转发命中缓存时直接定位模块，每次读取模块当前状态。寿命只读任务自带同名定义里的 LifetimeUpdate。CrusherInfo 和 AutoDepositUpdate 取 SDK 式合并后的模板块。
- 今天的 `Sim` 是世界的宿主，持有内核 `World`；旧分层模块用的 `simworld.WORLD_API` 仍主要由 `Sim` 提供。`Sim` 上的转调只给旧代码和测试用，不许再加。宿主生成内部物体键走 `simworld.free_key`：跳过活物体、还有模块留在调度表中的死物体，以及调用方预留的键。地图加载由 `load_keys` 为之后才摆下的点名物体预留名字。
- 每一步仍按 [sim-layers.md](sim-layers.md) 的比对方法验收：固定任务逐帧记录前后一字不差；有意改行为的步单独提交、写明、上台。
