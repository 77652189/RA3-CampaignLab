# 原版怎么做：扩图、兵少补援、意外、奖励的回报（子 Agent 整理，2026-10-29）

用户 2026-10-29 给第 1 层加了五条审核标准，这张卡是原版 40 关脚本里对应的做法。用 ra3bench 的 `retail_scripts`、`retail_goals` 查的，脚本名照原文。

## 1. 扩大地图

原版全靠 `MAP_SWITCH_BORDER(n)` 切换地图里预设的几块边界，0 号是全图，40 关里调用 87 次。大多是"事件成立 → 设一个短计时 → 计时到了再切"，留出放过场的时间。
- **目标完成**：宫古岛 `map expands for objective 3`，目标 2 完成后先炸掉隔墙（`TEAM_KILL Stupid_Walls`），再切到全图，EVA 报"战场扩大"，龙的部队同时并入；直布罗陀 `Objective 1a - Complete` 切到 1 号。
- **按难度计时**：冰岛扩大 B 段，简单 / 普通 / 困难 540 / 480 / 360 秒，目标提前完成就只等 5 秒。
- **旗标连锁**：伊贺 `Initial / Blue / Orange Border` 三档；克里姆林宫 `borders - first/second expansion`。
- **也会缩小**：黑区 `Shrink Border`，百合子进入指定区域后切回小边界；阿姆斯特丹关尾也缩图。

## 2. 兵少时补援军

原版有，只有 1 关。**深海（帝国第 5 关）** `Japan01 - Player Reinforcements P1`：目标 1 还没完成，且 `PLAYER_HAS_OBJECT_COMPARISON('Player_1', 0, 3, '_object list_japan all units')`（玩家单位少于 3 个），就用 `CREATE_REINFORCEMENT_TEAM` 在指定路点刷一队，走到交接区后 `TEAM_MERGE_INTO_TEAM` 并进玩家部队，播"增援已到达"。只触发一次；P2 的门槛是少于 4 个。

其余关靠别的办法避免坏档：
- **按兵力调喘息**：布莱顿海滩 `Wave 02 - Second Wave Timer`，玩家步兵不超过 15 个时给 60 秒倒计时再来下一波，16 个以上只给 1 秒。
- **按进度给援军**：伊贺每占一座道场给一队兵；直布罗陀目标 1a 完成后超时空送来援军。
- **给基地**：基地车开局，兵死了能再造。
- **合作方全灭时**：斯大林格勒、敖德萨把盟友的东西转给玩家（`PLAYER_TRANSFER_OWNERSHIP_PLAYER`）。

## 3. 背叛、科技限制、兵力限制

- **背叛**：
  - 冰岛：总理的通讯视频放完后，先把玩家对库可夫设成敌人（玩家能先动手）；玩家打了库可夫 5 秒后，库可夫才反过来设成敌人。翻脸的时机由玩家决定，前面有通讯视频预警。
  - 宫古岛：龙本来就是敌方玩家，"盟友"部队挂在平民一方，背叛过场里并入龙。
  - 哈瓦那 `Split - Begin Part 2`：三个苏军玩家一起改成敌人。
- **科技**：用 `ALLOW_DISALLOW_ONE_BUILDING` 和 `PLAYER_LOCK_PLAYER_TECH` 先锁后放：布莱顿海滩开局锁住机场、战车工厂，剧情走到再放开。中途收回：哈瓦那第二部分禁掉玩家的超时空传送仪。
- **兵力**：只给固定部队（直布罗陀 `FLAG - Commando Only`）；按数量封顶（东京港 `Only One Yuriko`、宫古岛 `tatsu has limited barracks`），"达到 N 就禁造，少于 N 再放开"。

## 4. 奖励目标的回报

| 回报 | 例子 |
|---|---|
| 钱 | 直布罗陀 +2500；纽约每人 +2500；富士山 +5000，外加 2 个单位 |
| 单位 | 宫古岛 4 个鬼王（`TEAM_TRANSFER_TO_PLAYER`）；海德堡谭雅转给玩家；海参崴 2 艘无畏舰 |
| 科技 | 戛纳放开 1 个建筑；战争机器人岛放开机场和三种飞机 |
| 揭图 | 宫古岛给鬼王的同时揭开 1500 半径 |

很多奖励只设旗标、不给东西，或者回报是一段剧情。

## 5. 脚本能不能判断"玩家兵力少于 N"

能。比较码 0 `<`、1 `<=`、2 `==`、3 `>=`、4 `>`。

| 条件 | 参数 | 原版用过 | 我们的编译器 |
|---|---|---|---|
| `PLAYER_HAS_OBJECT_COMPARISON` | 玩家、比较、N、模板或对象列表 | 628 处，深海的保底援军用它 | 只接了单个模板：`建成`（≥1）、`没有`（==0）、AI 上限 |
| `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA` | 再加一个区域 | 278 处，宫古岛判断"区内玩家兵少于 5" | 冰雕广场机关、测试计数器在用；策划案词表里没有 |
| `PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA` | 玩家、比较、N、单位种类、区域 | 28 处 | 自由号"空虚"判断在用；测试台实测它把所有玩家都算进去 |
| `PLAYER_HAS_COMPARISON_UNIT_KIND` | 不限区域的单位种类版 | 3 处 | 没接 |
| `TEAM_HAS_FEWER_THAN_X_UNITS_WITH_KINDOF` / `TEAM_COMPARE_NUM_MEMBERS` | 某支队伍 | 12 / 10 处 | 没接 |
| `SKIRMISH_PLAYER_HAS_UNITS_IN_AREA` | 区内有没有 | 410 处 | 已接（`进入`、`敌人清空`），只能判断有或没有 |

深海用的对象列表 `_object list_<阵营> all units` 在地图文件里搜不到定义，多半在游戏数据里；我们的编译器从没传过对象列表，要上测试台确认。退路是对几种主力兵各写一条单模板条件。结论写进 [flow/mechanics.md](../../flow/mechanics.md)。
