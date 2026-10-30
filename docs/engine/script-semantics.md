# SAGE 地图脚本运行语义（据《将军/绝命时刻》官方源码 + OpenSAGE）

日期：2026-10-27。目的：给"策划案模拟器"（`experimental/cnv/sim.py`）定规则。

## 0. 来源与读法

| 源 | 网址 | 本地（只读，未构建未运行） | 版本 |
| --- | --- | --- | --- |
| EA 官方 GPL-3.0 源码 | https://github.com/electronicarts/CnC_Generals_Zero_Hour（网址已用 `git ls-remote` 确认） | `work/downloads/cnc_generals_src/repo/` | `0a05454`（2025-02-27） |
| OpenSAGE | https://github.com/OpenSAGE/OpenSAGE | `work/downloads/opensage_src/repo/` | `588ac47`（2025-12-16） |

下文路径的简写：
- `ZH/` = `cnc_generals_src/repo/GeneralsMD/Code/GameEngine/`（绝命时刻）。《将军》原版在 `Generals/Code/...`，`evaluateTimer / setTimer / executeScript / evaluateConditions / evaluateFlag` 这几个函数两版逐行相同，下面只引 ZH。
- `SE` = `ZH/Source/GameLogic/ScriptEngine/ScriptEngine.cpp`；`SC` = 同目录 `ScriptConditions.cpp`；`SA` = 同目录 `ScriptActions.cpp`。
- `OS/` = `opensage_src/repo/src/OpenSage.Game/`。

**总的结论先说：** OpenSAGE 对红警3的脚本"语义"几乎没有实现。它只能读写红警3的地图格式，真正实现的条件只有 `Counter / Flag / TimerExpired / True / False`，以及两个音乐/阵营类条件；红警3的逻辑帧率在它代码里直接 `throw NotImplementedException`。所以本报告的语义几乎全部来自《将军》源码。红警3在它之上改过的东西，两份源码都查不到（第 6 节列出）。

---

## 1. 评估频率、顺序、延时、一次性脚本

**逻辑帧率**
- 《将军》：`LOGICFRAMES_PER_SECOND = 30`（`ZH/Include/Common/GameCommon.h` 第 72 行）。
- 脚本每个逻辑帧跑一遍：`GameLogic::update()`（`ZH/Source/GameLogic/System/GameLogic.cpp`）每帧先调用 `TheScriptEngine->UPDATE()`，然后才更新 TerrainLogic、各物体、AI、PartitionManager，再 `processDestroyList()`，最后 `m_frame++`。
- 时间冻结时（脚本冻结时间或过场镜头没走完）`GameLogic::update` 在脚本更新之后直接 `return`，这一帧世界不动，但脚本照跑。
- **红警3**：两份源码都没有。OpenSAGE `OS/SageGame.cs` 里的 `LogicFramesPerSecond()` 对 `Ra3 / Ra3Uprising` 是 `throw new NotImplementedException()`。仓库里写的"每秒 15 帧"（`docs/design/teardowns/data/timeline_measure.py` 中的 `FPS = 15`）标着"推断，未核实"，源码也证实不了。

**顺序**（`SE` 里的 `ScriptEngine::update`、`executeScripts`、`executeScript`）
1. 每帧先把所有"正在倒计时"的计时器各减 1（见第 3 节），**然后**才评估脚本。
2. 按阵营（side）序号 i = 0..N 依次处理：先跑这个阵营列表里**不在组里的脚本**（按文件顺序），再按顺序跑各个**处于激活状态、且不是子程序**的脚本组。子程序只在被 `CALL_SUBROUTINE` 调用时才跑。
3. 单个脚本（`executeScript`）：不激活就跳过 → 难度不匹配就跳过 → 还没到"下次评估帧"就跳过 → 评估条件 → 条件真就按顺序执行动作；条件假且有 else 动作就执行 else 动作。
4. 难度取的是"当前阵营玩家"的难度：`m_currentPlayer->getPlayerDifficulty()`。而 `Player::getPlayerDifficulty`（`ZH/Source/Common/RTS/Player.cpp`）规定：玩家带 AI 就取**这个 AI 的难度**，否则取全局难度。
- OpenSAGE 的顺序**相反**：`OS/Scripting/ScriptList.cs` 里的 `Execute` 是先跑组、再跑散脚本，而且 `Script.Execute` 根本不看难度位。以《将军》源码为准。

**"每 N 秒评估一次"**（`SE` 里的 `checkConditionsForTeamNames`、`executeScript`）
- 脚本头里有 `m_delayEvaluationSeconds`。开图时，凡是 N>0 的脚本，首次评估帧取 `GameLogicRandomValue(0, 2*LOGICFRAMES_PER_SECOND)`，也就是开局后 0～2 秒内的随机一帧。
- 之后每次"真正评估"（激活、难度对、帧到了），先把下次评估帧设为 `now + N*30`，再评估条件。条件真也好、假也好都会重排；脚本不激活时不重排。
- 我们的编译器写的是 `interval=0`（`experimental/campaign/mapscript.py` 里的 `new_script`），所以每帧都评估，上面这套用不上。
- OpenSAGE `Script.Execute` 自己的注释写着 "TODO: Is there an off-by-one error here?"，不可信。

**一次性脚本（deactivate upon success）**（`SE` 里的 `executeScript`）
- 条件为真、执行完 true 动作后，**立刻** `setActive(false)`，同一帧后面的脚本看到的就是它已关。
- 坑：在不带队伍参数的分支里，条件为**假**、而脚本又有 else 动作时，执行完 else 动作**也会关掉**。我们没写 else 动作，所以不受影响。
- 带队伍参数的条件会让脚本对该队伍的每个实例各评估一遍。

**条件为空**：`evaluateConditions` 对空的 OrCondition 直接 `continue`，一个 Or 组都没有的脚本永远是假。我们的编译器把空条件写成 `CONDITION_TRUE`（`parts.py` 里的 `write_map`），这样处理是对的。

## 2. AND/OR 结构与取反

- `SE` 的 `evaluateConditions`：脚本下面是一串 **OrCondition（彼此之间是"或"）**，每个 Or 组里是一串 Condition（彼此之间是"与"，遇到第一个假就短路）。任何一个 Or 组整组为真，脚本就为真。
- 取反：**《将军》没有**。`ZH/.../Scripts.cpp` 里的 `Condition::ParseConditionDataChunk` 只读类型、参数个数和参数，没有"取反"字段。
- OpenSAGE `OS/Scripting/ScriptCondition.cs`：Condition 块版本 ≥5 时依次读 `Enabled`（u32）和 `IsInverted`（u32）。这正好对应原版导出里条件行末的 `+0100000001000000`：前 4 字节是 enabled=1，后 4 字节是 inverted=1。但全仓库没有任何地方用到 `IsInverted`，`Enabled` 在求值时也不检查。所以"取反之后怎么算"（比如对象不存在时，取反的结果是不是简单的逻辑非）两份源码都查不到。目前只能按"对原条件结果取逻辑非"处理，这是假设。

## 3. 计时器、计数器、旗标

**存储**（`SE` 里的 `allocateCounter`、`allocateFlag`，以及 `ZH/Include/GameLogic/ScriptEngine.h`）
- 计数器和计时器是**同一张表**（`TCounter{value, name, isCountdownTimer}`）。同名的计数器和计时器是同一个东西。
- 名字第一次被用到时才分配，初值 0；旗标同样初值 0（假）。
- 上限 `MAX_COUNTERS=256`、`MAX_FLAGS=256`。超出时 release 版返回下标 0，也就是所有超额的名字共用一格。我们目前每关最多 86 个旗标、34 个计数器加计时器（a4），离上限很远。

**秒计时器 `SET_MILLISECOND_TIMER`**（`SE` 里的 `setTimer`）
- 参数是 **秒（Real）**，不是毫秒：`value = REAL_TO_INT_CEIL(ConvertDurationFromMsecsToFrames(value*1000))`，即 `ceil(秒 × 30)` 帧。同时把 `isCountdownTimer` 置真。
- 重设一个正在走的计时器 = 从头重新计时。
- `SET_RANDOM_MSEC_TIMER`：在 `[lo, hi]` 之间随机取值（`GameLogicRandomValue`），然后同上。
- 帧计时器 `SET_TIMER` 直接以帧为单位，我们没用。

**倒计时与到期**（`SE` 里的 `ScriptEngine::update` 和 `evaluateTimer`）
- 每帧在评估脚本**之前**：`if (value >= 0) value--`，减到 -1 就停。
- `TIMER_EXPIRED`：计时器从没启动过（`isCountdownTimer` 为假）→ 假；否则判定是 `value < 1`，即剩余帧数 ≤ 0。
- 推出来的精确时间：第 F 帧设成 N 帧，同一帧后面的脚本看到的值是 N，没到期（除非 N=0，0 秒计时器同帧就到期）。第 F+k 帧看到的值是 N−k，**第 F+N 帧首次到期**，正好 N 帧之后，按时间算就是"≥"。到期之后一直保持到期（值停在 -1），直到被重设或暂停。
- 暂停 `STOP_TIMER` 只清 `isCountdownTimer`，于是 `TIMER_EXPIRED` 变假；`RESTART_TIMER` 只在剩余帧数 >0 时才恢复。
- OpenSAGE 与此不同：它在脚本**之后**才减，并且只在 `== -1` 时算到期，会晚 1 帧（`OS/Scripting/ScriptingSystem.cs` 里的 `ScriptingTick`、`HasTimerExpired`）。以《将军》为准。

**计数器**（`SE` 里的 `evaluateCounter`、`setCounter`、`addCounter`、`subCounter`）
- 比较码：0 `<`、1 `<=`、2 `==`、3 `>=`、4 `>`、5 `!=`（`ZH/Include/GameLogic/Scripts.h` 里 `Parameter` 的枚举）。
- `INCREMENT_COUNTER` / `DECREMENT_COUNTER` 的参数顺序是 **(数值, 计数器名)**。

**旗标**（`SE` 里的 `evaluateFlag`、`setFlag`）：值按布尔比较（非 0 即真）。从没设过的旗标，`FLAG x 0` 为真。

**同一帧内是否立即可见**：是。上面这些动作都是直接改全局数组，同一帧里排在后面的脚本马上看得到；排在前面、已经评估过的脚本要到下一帧才看得到。

## 4. 我们用到的条件和动作：源码要点

我们用到的名字从 `experimental/cnv/**/*.py` 里 grep 出来，再和 `experimental/campaign/script_catalog.json` 取交集：条件 19 个，动作 72 个。其中《将军》源码里有的如下，查不到的见第 6 节。

### 4.1 区域、敌人清空

| 条件 | 函数 | 要点 |
| --- | --- | --- |
| `NAMED_INSIDE_AREA` | `SC` 里的 `evaluateNamedInsideArea` | 对象不在缓存里 → 假；否则直接拿**当前坐标**做点在多边形内判断（`pointInTrigger`）。**不检查死活**：正在播死亡动画、但还没被移除的对象仍算"在里面"。 |
| `NAMED_OUTSIDE_AREA` | `SC` 里的 `evaluateNamedOutsideArea` | 源码就是 `return !evaluateNamedInsideArea(...)`。所以**对象不存在、或已被移除时为真**。 |
| `SKIRMISH_PLAYER_HAS_UNITS_IN_AREA` | `SC` 里的 `evaluateSkirmishPlayerHasUnitsInArea` | 只数**该玩家**各队伍的成员。条件是 `isInside(区)` 且不是"已死 / INERT / 抛射物"，数到 >0 就为真。**建筑算，不动的单位也算**，与是否在移动无关。 |
| `PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA` | `SC` 里的 `evaluatePlayerHasUnitKindInArea` | 只数**该玩家**的、具有指定 KindOf、在区内、未死且不是 INERT 的对象。（仓库 2026-10-25 的实测是"所有玩家都算"，和这里矛盾，见第 7 节。） |
| `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA` | `SC` 里的 `evaluatePlayerHasUnitTypeInArea` | 同上，只是按模板计；另外箱子（CRATE）即使"已死"也算。 |

区域相关的细节：
- 上面三种"按玩家数区内对象"的条件用的是对象身上的 `isInside` 标记，而不是现场算坐标。这个标记在对象位置变化时由 `Object::setTriggerAreaFlagsForChangeInPosition`（`ZH/Source/GameLogic/Object/Object.cpp`）更新：坐标取整后要变了才更新，抛射物和 INERT 物体不参与。
- 每个对象最多同时记 `MAX_TRIGGER_AREA_INFOS = 5` 个区域（`ZH/Include/GameLogic/Object.h`），超出的区域它就"不在里面"。`NAMED_INSIDE_AREA` 不受这个限制。
- 结果会缓存：只有当该玩家某个队伍有对象进出过区域，或者全局对象数在缓存之后变过，才重算。`ScriptEngine::notifyOfObjectCreationOrDestruction` 会在对象创建、析构以及进入死亡状态（`AIStates.cpp` 里的 AIDeadState）时打点。
- 源码注释（`Object::didEnterOrExit`）原话大意是：执行顺序是先脚本、后物体更新，所以第 N 帧物体更新里发生的进出，脚本要到第 N+1 帧才看得到。

### 4.2 单位被毁、存在、归属、血量、状态

| 条件 / 动作 | 函数 | 要点 |
| --- | --- | --- |
| `NAMED_DESTROYED` | `SC` 里的 `evaluateNamedUnitDestroyed` | 对象在缓存里 → 返回 `isEffectivelyDead()`；名字曾经有过、但对象已被移除（缓存里那格是 NULL）→ 真；**从没出现过的名字 → 假**。 |
| `NAMED_NOT_DESTROYED` | `SC` 里的 `evaluateNamedUnitExists` | 在缓存里且没死 → 真；不在缓存里（没造出来或已移除）→ 假。 |
| `NAMED_KILL` | `SA` 里的 `doNamedKill` → `Object::kill` | 造成一次等于最大血量、`m_kill=TRUE` 的伤害。`ActiveBody`（`ZH/.../Body/ActiveBody.cpp`）在扣血时**同步**设置 `setEffectivelyDead(health<=0)`，所以同一帧后面的 `NAMED_DESTROYED` 就是真。伤害来源是 `INVALID_ID`，不归任何玩家。 |
| `NAMED_DELETE` | `SA` 里的 `doNamedDelete` → `GameLogic::destroyObject` | 只是打上 DESTROYED 状态并排进销毁队列，**不是"死"**。帧末 `processDestroyList` 析构时才从名字缓存里清掉（`ScriptEngine::notifyOfObjectDestruction` → `removeObjectFromCache` 把那格置 NULL）。所以**同一帧里 `NAMED_DESTROYED` 仍为假、`NAMED_NOT_DESTROYED` 仍为真，下一帧才变**。 |
| 被打死的单位 | — | 有死亡动画（slow death）的单位，在动画期间仍留在缓存里：`NAMED_DESTROYED` 真（已死），`NAMED_INSIDE_AREA` 仍按尸体位置算，`UNIT_HEALTH` 读到 0%。 |
| `NAMED_OWNED_BY_PLAYER` | `SC` 里的 `evaluateNamedOwnedByPlayer` | 比较 `getControllingPlayer()`，**不检查死活**。红警3的参数顺序是（玩家, 单位），和《将军》的（单位, 玩家）相反（见 catalog）。 |
| `NAMED_ATTACKED_BY_PLAYER` | `SC` 里的 `evaluateNamedAttackedByPlayer` | 只看**最近一次**伤害（`ActiveBody` 的 `m_lastDamageInfo`）的来源玩家。被别的玩家打一下、或被 `NAMED_KILL` 杀掉，就可能变回假。不是"曾经被打过"。 |
| `UNIT_HEALTH` | `SC` 里的 `evaluateUnitHealth` | 百分比 = `(当前血*100 + 初始血/2) / 初始血`，按**初始血量**算并四舍五入成整数，不检查死活。 |
| `UNIT_HAS_OBJECT_STATUS` | `SC` 里的 `evaluateUnitHasObjectStatus` | 状态位里有任意一位命中即真；对象不存在为假。 |
| `PLAYER_HAS_OBJECT_COMPARISON` | `SC` 里的 `evaluatePlayerUnitCondition` → `Team::countObjectsByThingTemplate`（`ZH/Source/Common/RTS/Team.cpp`） | 调用时 `ignoreDead=false`，所以**死亡动画中的对象仍被计数**；正在建造中的不计（`ignoreUnderConstruction` 默认 TRUE）。结果按对象数变化来缓存。 |
| `NAMED_DISCOVERED` | `SC` 里的 `evaluateNamedDiscovered` | 对象存在、没被 HELD、不是"隐身且未被侦测"，并且对该玩家的遮蔽状态是 CLEAR 或 PARTIAL_CLEAR（FOGGED 不算）才为真。另外 `Object::getShroudedStatus` 对 `KINDOF_ALWAYS_VISIBLE` 的对象、以及不在分区系统里的对象（如驻军步兵）**一律返回 CLEAR**。这可以解释仓库实测"每个目标都读到 1"，但这是推断。 |
| `CREATE_NAMED_ON_TEAM_AT_WAYPOINT` | `SA` 里的 `createUnitOnTeamAt` | 同名的活对象已存在 → 不造；同名对象已死或已移除 → 新对象接管这个名字（于是 `NAMED_DESTROYED` 又变回假）。造好后立即 `setPosition` 到路点，同一帧后面的 `NAMED_INSIDE_AREA` 能看到。队伍名找不到就当场建一个。 |
| `MOVE_NAMED_UNIT_TO` / `NAMED_ATTACK_NAMED` / `NAMED_STOP` / `NAMED_HUNT` | `SA` 里的 `doNamedMoveToWaypoint` / `doNamedAttack` / `doNamedStop` / `doNamedHunt` | 只下命令（`aiMoveToPosition` 等）。位置在后面的物体更新里才变，**脚本下一帧起才看得到**。 |
| `TEAM_ATTACK_NAMED`、`NAMED_GARRISON_SPECIFIC_BUILDING`、`NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT`、`NAMED_USE_COMMANDBUTTON_ABILITY` | `SA` 里的 `doTeamAttackNamed` / `doUnitGarrisonSpecificBuilding` / `doNamedFireSpecialPowerAtWaypoint` / `doNamedUseCommandButtonAbility` | 同上，都只是下命令。 |
| `NAMED_TRANSFER_OWNERSHIP_PLAYER` | `SA` 里的 `doNamedTransferAssetsToPlayer` | 立即 `setTeam(目标玩家默认队伍)`，同一帧后面的脚本就能看到。 |

### 4.3 目标、计数器显示

- `DISPLAY_COUNTER` / `DISPLAY_COUNTDOWN_TIMER`：`SA` 里的 `doDisplayCounter` / `doDisplayCountdownTimer` → `InGameUI::addNamedTimer`（`ZH/Source/GameClient/InGameUI.cpp`）。只是登记一个界面条目，绘制时现读计数器的值。倒计时显示的是 `(int)(剩余帧/30)`，向下取整。对逻辑**没有任何影响**。
- `HIDE_COUNTER` / `HIDE_COUNTDOWN_TIMER` 调用 `removeNamedTimer`。
- `SHOW_MILITARY_CAPTION`：`SA` 里的 `doMilitaryCaption` → `InGameUI::militarySubtitle`。《将军》的时长参数是 Int 毫秒；红警3的 catalog 里参数类型是 Real（秒），类型变了。
- 任务目标相关的动作（`SET_MISSION_OBJECTIVE_STATUS`、`LINK_MISSION_OBJECTIVE_TO_*`）《将军》里没有，见第 6 节。

### 4.4 边界切换、揭图

- `MAP_SWITCH_BORDER`：`SA` 里的 `doBorderSwitch` → `TerrainLogic::setActiveBoundary`（`ZH/Source/GameLogic/Map/TerrainLogic.cpp`）。
  - 序号越界、和当前相同、或那条边界宽高为 0 → 什么都不做。
  - 否则立即重建 PartitionManager 并恢复雾和揭开的格子，所有对象重新登记；落在新边界外的对象只是打上 `OFF_MAP` 状态，**不会被删或被杀**（`Object::friend_notifyOfNewMapBoundary`）。
  - 源码注释说边界切换"和永久揭图配合不好"，所以对观战者会先撤销永久揭图、切换、再重新揭。对普通玩家没有这样处理。推断：切换**之前**做的永久揭图，可能盖不到新扩出来的区域。未实测。
- `MAP_REVEAL_ALL_PERM` / `MAP_REVEAL_ALL_UNDO_PERM`：`SA` 里的 `doRevealMapEntirePermanently`。玩家参数为空时作用于所有人类玩家。
- `MAP_REVEAL_ALL`：`SA` 里的 `doRevealMapEntire`，一次性揭开，之后照常回雾。
- `MAP_REVEAL_AT_WAYPOINT`：`SA` 里的 `doRevealMapAtWaypoint`，`doShroudReveal` 后紧跟 `undoShroudReveal`，只是一瞬间照亮。
- `MAP_REVEAL_PERMANENTLY_AT_WAYPOINT` / `MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT`：`SA` 里的 `doRevealMapAtWaypointPermanent` → `ScriptEngine::createNamedMapReveal` + `doNamedMapReveal`，按名字登记、按名字撤销。

### 4.5 胜负

- 《将军》靠 `VICTORY` / `DEFEAT` 动作结束任务（`SA` 里的 `doVictory` / `doDefeat`）：关窗、禁止输入、弹出胜/负窗口、`TheCampaignManager->SetVictorious(...)`，并启动 `startEndGameTimer`（`m_endGameTimer = 120` 帧，即 `FRAMES_TO_SHOW_WIN_LOSE_MESSAGE`）。
- `ScriptEngine::update` 里只要 `m_endGameTimer >= 0` 就直接 `return`，所以**从下一帧起脚本停跑**。但**当前这一帧排在后面的脚本照常执行**：如果同一帧里后面又有一个脚本执行了 DEFEAT，它会再关一次窗、再 `SetVictorious(FALSE)`，最后生效的是后执行的那个。
- `VictoryConditions::update`（同目录 `VictoryConditions.cpp`）只在多人游戏里起作用，单人战役不会自动判胜负。
- **`"Mission Won"` / `"Mission Lost"` 旗标**：两份源码里都**搜不到**这两个字符串。"设这个旗标就结束任务"是红警3自己的机制，只有我们的实测为证（`experimental/cnv/checks/a7.py` 注释写着 "Mission Won ends the mission"）。它在帧内的什么时刻被读取、同一帧后面的脚本还跑不跑，都查不到。

## 5. 同一帧里，一个动作造成的变化后面的脚本能不能马上看到

| 变化 | 后面的脚本当帧可见？ | 依据 |
| --- | --- | --- |
| 旗标、计数器、计时器的设置 | 是 | 直接改数组（第 3 节） |
| 一次性脚本被关 / `ENABLE_SCRIPT` / `DISABLE_SCRIPT` | 是；被打开的脚本如果排在后面，当帧就会跑 | `SE` 里的 `executeScript`、`enableScript` |
| `NAMED_KILL` 之后的 `NAMED_DESTROYED` | 是 | 扣血时同步设"已死" |
| `NAMED_KILL` 之后"按玩家数区内对象"的条件 | 可能读到旧缓存，下一帧才更新 | 缓存靠"对象数变化帧"，死亡打点发生在 AI 更新阶段（在脚本之后） |
| `NAMED_DELETE` 之后的 `NAMED_DESTROYED` | 否，下一帧才真 | 帧末销毁队列 |
| 新建命名单位 | 是：它在缓存里，有位置，`NAMED_INSIDE_AREA` 能看到 | `createUnitOnTeamAt` |
| 移动、攻击命令的效果（位置、血量） | 否，至少下一帧 | 物体更新在脚本之后 |
| 归属转移 | 是 | `setTeam` 是同步的 |
| `VICTORY` / `DEFEAT` | 当帧后面的脚本照跑，下一帧起停 | `m_endGameTimer` |

## 6. 《将军》与红警3的差异

**OpenSAGE 里红警3特有的脚本处理**，只有格式层面：
- `OS/Scripting/Script.cs` 解析 Script 块时，版本 ≥6（Uprising）多读 `Unknown2`（i32）和 `Unknown3`（u16）；版本 5 多读 `UsesEvaluationIntervalType` 和 `EvaluationIntervalType`（`[AddedIn(SageGame.Cnc3)]`）。
- Condition 块版本 ≥5 多读 `Enabled` 和 `IsInverted`（`OS/Scripting/ScriptCondition.cs`），但求值时两个都不用。
- 求值时按 `InternalName` 字符串映射到《将军》的枚举（`OS/Scripting/Conditions/ScriptConditions.cs` 里的 `Evaluate`；`ScriptContent.cs` 里有 "TODO: Need to make game-specific TContentType enums"）。
- 实现了的条件只有 `Counter, False, Flag, MusicTrackHasCompleted, SkirmishPlayerFaction, TimerExpired, True`；动作只有计数器、计时器、旗标、启停脚本、子程序、镜头等少数几个。
- OpenSAGE 里没有任何红警3专属的条件或动作实现，也没有红警3的帧率。

**我们用到、但《将军》源码里查不到的名字**（在 `ZH/Include/GameLogic/Scripts.h` 的枚举和 `SE` 的 `m_internalName = "..."` 表里都 grep 过，OpenSAGE 里也一个都没有）：

- 条件（2 个）：`CAMERA_ENTERED_AREA`、`PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS`
- 动作（28 个）：
  - 移动、攻击、生成：`ATTACK_MOVE_NAMED_UNIT_TO`、`ATTACK_MOVE_TEAM_TO`、`CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION`、`UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION`、`UNIT_TELEPORT_TO_WAYPOINT`、`UNIT_GUARD_AREA`
  - 血量、状态：`UNIT_SET_HEALTH`、`NAMED_SET_MAX_HEALTH`、`UNIT_CHANGE_OBJECT_STATUS`、`SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER`
  - 任务目标、存档、镜头：`SET_MISSION_OBJECTIVE_STATUS`、`LINK_MISSION_OBJECTIVE_TO_OBJECT`、`LINK_MISSION_OBJECTIVE_TO_WAYPOINT`、`CAMPAIGN_CREATE_AUTO_SAVE`、`MOVE_CAMERA_TO_NAMED`
  - 经济、电力、计数：`PLAYER_SET_PLAYER_POWER_POINTS`、`PLAYER_SET_MAX_PLAYER_POWER_POINTS`、`SET_PLAYER_MONEY_TO_COUNTER`、`SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER`、`ALLOW_DISALLOW_ONE_BUILDING`
  - 遭遇战 AI：`SKIRMISH_AI_MAKE_BASE`、`SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES`、`SKIRMISH_AI_TRANSFER_ALL`、`SKIRMISH_AI_USE_REBUILD_SYSTEM`、`SKIRMISH_AI_USE_REPAIRS`、`UNIT_AI_TRANSFER_ALL`
  - 音乐：`PATH_MUSIC_PLAY_EVENT`、`PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM`
- 还有这些也查不到：
  - `"Mission Won"` / `"Mission Lost"` 旗标的结束机制；
  - 条件取反位的求值方式（测试台已测，见下表第 13 条）；
  - 红警3的逻辑帧率（测试台已测：每秒约 15 帧，见下表第 11 条）；
  - 红警3改过的参数顺序和类型（例如 `NAMED_OWNED_BY_PLAYER` 是玩家在前；`SHOW_MILITARY_CAPTION` 的时长是秒、Real）。

名字两边都有、红警3可能改过实现的，目前只发现一个确凿的矛盾：`PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA`。《将军》只数指定玩家的对象，仓库实测是"所有玩家都算"（`plan.py` 的 `敌人清空` 注释，bench 2026-10-25）。

## 7. 与 sim.py、编译器现有假设的对照

都是对照 `experimental/cnv/sim.py`（未提交的新文件）和 `plan.py` 读出来的。

| # | 现有假设 | 源码（《将军》） | 影响 |
| --- | --- | --- | --- |
| 1 | `NAMED_OUTSIDE_AREA`：对象不存在或已死 → 假（`sim.py` 里的 `cond`：`b and b.alive and ...`） | 对象不存在（已移除）→ **真**；正在死的对象按尸体位置算 | 用"离开某区"做条件时，单位死了可能被当作"离开了" |
| 2 | `NAMED_INSIDE_AREA` 要求活着 | 不检查死活，死亡动画期间仍按位置算 | 一般影响很小 |
| 3 | `UNIT_HEALTH` 要求活着 | 不检查死活；死亡动画期间读到 0%。测试台 2026-10-28（`probe --check death`）：打死后下一次读数就不在区内了，血量计数读 0，看不出死亡动画的停留；sim 的 `LINGER` 改成 0 | "血量 X < N 判负"不要指望单位被打死那一刻成立 |
| 4 | `NAMED_ATTACKED_BY_PLAYER` = 曾经被该玩家打过（集合） | 只看**最近一次**伤害的来源；被别人打或被脚本杀后就可能变假 | 用"攻击 X"做触发的脚本，在游戏里可能更难触发，或只在一个窗口期内成立 |
| 5 | `NAMED_DELETE` 当帧就算"被毁" | 下一帧才算 | 差 1 帧，基本可忽略 |
| 6 | `PLAYER_HAS_OBJECT_COMPARISON` 只数活的 | 死亡动画中的仍计，建造中的不计 | "没有 X"会比 sim 晚成立（晚一个死亡动画的时长）；"建成 X"要等建完 |
| 7 | 赢 / 输：设旗标后 sim 立即停（`step` 里的 `if self.ending: return`） | 《将军》的 VICTORY 当帧后面的脚本照跑；红警3旗标机制源码查不到 | 同一帧里同时满足赢和输时，sim 的判定可能和游戏不一致。sim 应报告"同帧双结局"，交给实测 |
| 8 | `ENABLE_SCRIPT` 不会重新武装已触发的一次性脚本（`sim.py` 把 `done` 和 `disabled` 分开放） | 一次性 = `setActive(false)`，`ENABLE_SCRIPT` 会把它重新打开 | 目前编译器和 devices 没用 `ENABLE_SCRIPT`，暂无影响；以后用到就会不一致 |
| 9 | 计数器和计时器分两张表（`self.counters` / `self.timers`） | 同一张表，同名即同一个 | 编译器的计时器名（`CNV <关> Wait k`）和中文计数器名不会撞，暂无影响 |
| 10 | 难度位按全局难度过滤（`s.levels[self.level]`） | 按**脚本所在阵营玩家**的难度：该玩家带 AI 时用 AI 的难度 | 我们的脚本都放在 `PlayerScriptsList` 第 2 个列表（`newmap.clear_scripts`）。如果那个阵营是 AI，且红警3沿用这条规则，难度分支会跟 AI 难度走。需要查第 2 个列表属于哪个玩家 |
| 11 | sim 每 0.5 s 一个 tick（`DT = 0.5`） | 每帧一次（《将军》30 帧/秒；红警3测试台 2026-10-28/29 实测每秒约 15 帧，10 秒的计时器 150 帧到期）；秒计时器到期 = `ceil(秒×帧率)` 帧之后 | 时间线误差最多约 0.5 s；同一帧内的先后在 sim 里也一样成立 |
| 12 | 区内对象计数实时、没有上限 | 依赖对象身上的进出区标记：每个对象最多同时记 5 个区；移动造成的进出要下一帧才看得到 | 地图上某点叠了超过 5 个触发区时，计数类条件可能漏算（`NAMED_INSIDE_AREA` 不受影响） |
| 13 | 取反 = 对条件结果取逻辑非（`sim.py` 里的 `holds`） | 测试台 2026-10-29（`probe --check align`）：我们写的取反位和原版逐字节一样，可游戏从 .map 读的脚本不认这一位，取反的标志、取反的计时器都照原条件算；原版的脚本是编译进资源流的 | 编译器不再写取反位：每个取反条件换成一个标志，由列表最前面两条每帧脚本维护（`parts.unnot`），复测通过 |
| 14 | `PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA` 数所有玩家（实测） | 只数指定玩家 | 以实测为准，并标明"红警3与《将军》不同" |
| 15 | 边界切换和永久揭图可以随意先后 | 源码注释说两者配合不好；测试台 2026-10-28（`probe --check reveal`）：切换前做的永久揭图盖得到新区域 | 一致 |

一致、不用改的：
- 条件与/或结构：编译器把"任一"拆成多个脚本，再用旗标闩住；
- 空条件写成 `CONDITION_TRUE`；
- 没设过的旗标为 0；
- 没启动过的计时器不算到期；
- 从没出现过的名字，`NAMED_DESTROYED` 和 `NAMED_NOT_DESTROYED` 都是假；
- `NAMED_KILL` 当帧就算被毁；
- `SKIRMISH_PLAYER_HAS_UNITS_IN_AREA` 对建筑和不动的单位都算（"敌人清空也算建筑"与源码一致）；
- 动作效果当帧对后面的脚本可见；
- 计时器到期判定是"≥"；
- 比较码 0～5 的含义。
