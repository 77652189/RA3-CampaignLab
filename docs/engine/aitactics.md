# 遭遇战 AI 先打哪栋楼、什么时候出门、守兵多远会被拉回

引擎线 A 第 54～65 轮（2026-11-06），ADR 0019 第四层（遭遇战 AI）的 ④ 目标和战术、⑤ 防守。写法照 `script-semantics.md`：**测** = 测试台；**读到** = 程序里读到、没上测试台；**推断** = 只从资料推出来。

探针两个，都用尼亚加拉图、敌方盟军 AI、人格只留一个常开状态（做法同 `aistate.md`）：
- `experimental/cnv/checks/engine_aitarget.py`（任务 `missions/aitarget_bench.py`）：玩家有两座电厂，近的带炮塔、远的不设防，看 AI 的 4 个维和步兵先去哪座、几秒出门。
- `experimental/cnv/checks/engine_aidefense.py`（任务 `missions/aidefense_bench.py`）：AI 用 `StaticDefense` 守自己的建造厂，用脚本把守兵弄走，看它们会不会、多久被拉回来。

## 给关卡线的结论

**先打哪栋楼**
- 一个战略状态写了几条目标启发（`TargetHeuristic`），AI 按 `Priority` 从高到低一条条试，同级的随机先后，**第一条找到目标的就用它**，后面的不看。一个目标槽只占一个目标。（读到）
- 找敌方建筑 / 敌方单位时，**距离从 AI 基地中心量**，不是从出门的队伍量。（读到）
- `ClosestStructureHeuristic`（按距离）= 离 AI 基地最近的敌方建筑；**测**：先打带炮塔的近厂，炮塔把步兵全打死了。
- `SafestToGroundStructureHeuristic`（按对地威胁）= 周围对地火力最小的那栋；**测**：绕过近厂、先打不设防的远厂，打掉以后（`RAMPAGE`）才转去近厂。量火力的半径固定 400，不看人格里的 `DefaultThreatFindRadius`。（半径：读到）
- 设计用法：想让 AI 先砸某栋楼，就让它离 AI 基地最近；对"挑软柿子"的状态，玩家在一栋楼 400 内摆防御，AI 就会改打别处——可以拿来出"引导 AI 进攻方向"的题。
- 有几个敌方玩家时，先给玩家排序（最近的 / 最强的 / 一样），只在排第一的那一档玩家里找；`HighestPriorityEnemyPlayersOnly` 为真（默认）时那一档没目标，这条启发就算失败。（读到）
- `RequireUniqueTarget`：同一个 AI 的另一个槽正在打的东西，这条启发不会再选。（读到）
- **一处没对上**：`aistate.md` 测到目标在 2600 外状态根本不启动、750 外就启动；但找敌方建筑那段程序里没看到读搜索半径（`SearchRange`）。限制在别处，没读到在哪。关卡上照测试台的来：**目标离 AI 基地太远，状态不会派兵**。

**什么时候出门**
- `SimpleAttack`：队伍凑齐当场出发，直奔目标，路上不停。（测：唤醒后约 3 秒就到了近厂）
- `DefenseAvoidanceAttack`（DA）和 `FlankAttack`：路分几段（队伍位置 → 侧移点 → 目标前 600～1000 的接近点 → 目标），**每段都要等队伍"就绪"才走下一段**。（分段：读到；等：测）
  - 就绪 = 队员站着不动超过微操的 `MaxUnitIdleTime`（标准微操 10 秒），或整队闲置超过 `MaxTeamIdleTime`（标准 15 秒），哪个先到算哪个。（读到；和下面读数对得上）
  - **测**：默认设置下 DA 比 `SimpleAttack` 晚约 15 秒出门；`MaxTeamIdleTime` 改 5 秒早约 11 秒；改 30 秒和 15 秒一样（被队员 10 秒那条先放行）。`FlankAttack` 比 DA 早约 3 秒出门，但晚约 23 秒到（随机绕一侧）。
  - 设计用法：想给玩家留准备时间，用 DA（会在家门口和接近点各停一下）；想立刻压上，用 `SimpleAttack`。
- **AI 状态开局就在跑**：属于 AI 玩家的兵，第 1 秒就被防守状态带去集合，没等第 10 秒的唤醒脚本。（测）
- 目标没了以后看 `EndBehavior`：`RAMPAGE` = 去打 99999 内最近的敌人，找不到才结束；`DISBAND` = 解散；`RETURN_HOME_AND_DISBAND` = 先走回基地 600 内再解散。（读到）关旗叫不回出了门的队伍，见 `aistate.md`。

**守兵多远会被拉回（`StaticDefense`）**
- 队伍先攻击移动到守的点。之后每 `UpdateTime`（默认 1 秒）看一次：队伍中心离点超过 `Distance` → 攻击移动回去；正在打仗时这个圈放大成 `Distance × CombatLeashSlack`（默认 1.5 倍）。目标是会动的东西就跟着走。（读到）
- **测**：守兵被瞬移到 1200 外，`UpdateTime` 1 秒时 25 秒内全回到 300 圈里（基本就是走回来的时间），4 秒时晚约 2 秒。
- 在圈里时：`UseAestheticsManager` 开着（默认）由"美化"在点周围摆站位；关着时，**队伍就绪且中心偏离点超过 100，就再走回点**。（读到）
- **测**（美化关，`Distance` 250）：脚本用 `MOVE_NAMED_UNIT_TO` 把守兵往外派，**没走出 175 就被叫回**，远没到 `Distance`。原因是"就绪"按旧的站立记录判断，兵刚被推走时还算就绪。
- 所以：**用脚本把 AI 的守兵调走基本不行**，会被叫回。要调走，得先把它们编进脚本小队（`UNIT_SET_TEAM`，`m.order` 就是这么做的）：**测**：这样派出 1200 后一个都没回来，改 `Distance` 250/450、`UpdateTime`、`CombatLeashSlack` 都一样（推断：编进脚本小队就脱离了 AI 的队伍）。
- 守兵的战术里没有找敌人的逻辑，打不打靠微操（`aimicro.md`）。（读到）
- 原版遭遇战人格里：`LandDefense` 守离敌人最近的 3 栋自家建筑、`Distance` 450；`BalancedDefense` 在敌人进到 750 内时才开。（读到，数据）
- `ReactiveDefense`：每个 AI 同时只有一个，约每 2 秒看一次，追基地 `ReactiveDefenseRadius` 内的敌人，敌人跑出这个圈就放手回基地；原版只有一处演示用到。`SimpleDefense`：走到点、全员就绪就解散。`RoamingDefense`：程序里根本不建，写了也没用。（读到，没测）

**基地"挨打"旗标和防御塔**（读到，没测）
- 任一建筑最近约 1 秒（`BaseBuilderUpdateUnderAttackTime` 默认值换算）挨过打 → 基地记"被攻击"；敌人进到建筑 300 内（建筑本身更大就按建筑半径）→ 记"敌人在基地里"。原版的"救援"队伍（`EmergencyDefense`）是 `SimpleAttack` 去打 `UnderAttackBy` 目标。
- 防御塔放哪：以离敌人最近的自家建筑为中心，朝最近敌人的方向，距离约 `BaseCompactness × 500`，依次试正对、±36°、±72° 五个角度，第一个能放的就放。

## 读数（测）

| 探针 | 设置 | 结果 |
| --- | --- | --- |
| `aitargetnear` | `ClosestStructure` + `SimpleAttack` | 唤醒后 3 秒到近厂，被炮塔打光；远厂一直没人去 |
| `aitargetsafe` | `SafestToGround` + DA，默认微操 | 唤醒后 18 秒出门、25 秒到远厂；拆掉后转去近厂 |
| `aitargetidle5` | 同上，`MaxTeamIdleTime` 5 秒 | 7 秒出门、12 秒到远厂（早约 11 秒） |
| `aitargetidle30` | 同上，30 秒 | 和默认（15 秒）一样 |
| `aitargetflank` | `SafestToGround` + `FlankAttack` | 15 秒出门、48 秒到远厂 |
| `aidefctl` / `aidefctl4` | `StaticDefense` `Distance` 250，`UpdateTime` 1 / 4 秒，瞬移到 1200 外 | 第 25 / 27 秒全回 300 圈 |
| `aidefmv` | 同上，脚本 `MOVE_NAMED_UNIT_TO` 往外派 | 没走出 175 就回来，之后一直在 100 圈里 |
| `aidef250` 等 4 个 | `m.order` 编进脚本小队再派出 | 全部走到 1200 外，不回来 |

（时间都是唤醒后秒数，测试台每秒读一次，±1 秒。11-06 的 `aidefense` 读数里外派点在 1200，压着两棵树；第 65 轮挪到 1150，读数没重测，结论不受影响。）

## 没测 / 没建模

- DA 怎么选"防御最弱的一侧"绕路，没进模型；`MaxTeamIdleTime` 5 对 15 秒，模型差 8.8 秒、测试台差 11 秒（推断是集结那一段的状态没读）。
- 除了敌方建筑 / 单位、友方建筑 / 单位，其余目标启发（科技建筑、靠岸建筑、`UnderAttackBy`……）怎么挑都是推断；一个槽多久重选一次没读到。
- 防御塔落点、建筑修理、"挨打"旗标的时间窗都没上测试台（要让 AI 有钱造塔）。
- `BaseDefenseMaxDistance` 按说明是"防御建筑多远还算同一队"，不是拴绳；谁读它没找到。
