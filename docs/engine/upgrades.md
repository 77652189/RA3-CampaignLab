# 升级和属性修正：脚本给、撤升级时修正怎么变

引擎线第 10 轮（2026-11-04），先答 A8 卡着的两问（`docs/story/handoff-phase4.md` 第十八个会话"没做、要测试台答的"第 1、2 条）。写法照 `script-semantics.md`：**码** = 读了游戏程序；**测** = 测试台；**推断，未实测** = 只从资料推出来。

探针图 `experimental/cnv/maps/probe_range.py`（平地，六条炮道，每门炮正北按距离摆靶子）。炮是 A8 的浪涌炮塔（`units/platform.py` `tide_gun`：原版哨戒炮，武器射程 300、视野 300；升级"高" = RANGE x2，"低" = RANGE x0.6，`Category="NONE"`），归玩家；靶子是工程师，先归中立（谁都不打），第 8 秒才转给敌方，所以每门炮见到靶子时，升级已经给完、撤完。靶子掉血或死了就记一次。检查在 `experimental/cnv/checks/engine_range.py`：`cnv_check engine_range swell`（看炮自己挑不挑）、`cnv_check engine_reach reach`（强令攻击量武器射程：炮不会动，够不着就不开火）。日志 `work/logs/engine10_range.log`、`engine10_reach.log`。

## 1. 撤掉升级，它带来的修正就跟着没了；再给一次又回来（测）

- 给"高"、过 4 秒撤掉，再强令打 450 处的靶子：**不开火**（x2 没了）。
- 给"高" → 撤"高"给"低" → 撤"低"给"高"（节律设备的切法，一轮半），强令打 450：**开火**（第二次给的"高"照样生效）。
- 先"高"、再按设备的两步"撤高、给低"，强令打 250：**不开火**；自己只打得到 150。和只给"低"那门一样（150 打、250 不打）。没有叠成 x1.2（360）。
- 对照：不给升级的炮强令打 450 不开火（300 够不着）；只给"低"的炮强令打 250 不开火（180）。
- **关卡线该怎么改**：不用改。`devices/rhythm.py` 现在"先撤另一个、再给这个"的写法是对的，修正不会叠，可以一直来回切。`units/platform.py` 文档串里"没测"那段可以改成指向本节。

## 2. RANGE 只改武器射程，不改自动索敌距离；索敌跟着视野走（测）

- 只给"高"（RANGE x2 = 600）、谁也不命令：450、550 处的靶子**都不打**。强令它打 450：**打得到**。所以武器射程确实变成了 x2，但炮自己找目标时看不到 300 以外。
- 另一门炮的"高"同时带 `VISION` x2（原版就这么配：`GlobalData/AttributeModifier.xml` 第 56 行，RANGE 175% 配 VISION 250%）：450、550 处的靶子**自己就打了**。
- 结论：自动索敌的距离受视野（`VisionRange`）限制，不看武器射程。哨戒炮视野 300 正好等于射程，所以只加射程等于白加。
- **关卡线该怎么改**：浪涌炮塔的"高"修正里加一行 `<Modifier Type="VISION" Value="200%"/>`（和 RANGE 同倍数；视野比射程大一点也行）。"低"那条 x0.6 不用加：射程短于视野时，看得到也打不着，炮不会去够。单位线换模型时保留这两行。改法见 `checks/engine_range.py` 的 `mission(seen=True)`。

## 3. 顺带踩到的坑

- 同一个模组里放两份由同一个原版文件改出来的单位（例如两门 id 不同的 `tide_gun`），原版文件里的 `<Define>`（哨戒炮的 `SOVIET_BASE_DEFENSE_GROUND_LOCAL_UNPACK_TIME`）会被定义两次，地图编译报 Critical 停下。第二份要把 Define 改名（`engine_range.py` 里有写法）。A8 现在只有一种炮塔，不受影响；以后同一关要两种浪涌炮塔时，`tide_gun` 要做这件事（单位线）。
- 靶子先归中立、到点再转给敌人，是"让单位在指定状态下才见到敌人"的通用办法，比挪位置可靠。

## 4. 无敌：光写 `INVULNERABLE 100%` 不管用，要再设铁幕状态位；撤掉就能打，再给又无敌（测）

关卡线 A9 原子球问的（`experimental/cnv/units/tower_ball.py`：暗 = 升级挂 `INVULNERABLE 100%`，亮 = 无修正）。探针 `experimental/cnv/checks/engine_invuln.py`：同一张炮道图，靶子是探针自己复制的原版地堡（去掉驻军、光环、隐身，4000 血），哨戒炮强令攻击（哨戒炮不会自己挑建筑打，不下令谁都不掉血）。`cnv_check engine_invuln invuln`、`engine_invuln_enemy invuln`、`engine_invuln_kinds invuln`。

- **只写 `<Modifier Type="INVULNERABLE" Value="100%"/>`，经 `AttributeModifierUpgrade` 挂上：照样掉血。** 两轮（靶子先中立再转敌方 / 一直归敌方）都一样，亮暗来回切的那个血一直匀速往下掉。
- **同一个修正加 `ObjectStatusToSet="NO_BRIBE UNDER_IRON_CURTAIN"`（原版铁幕修正设的状态位）：不掉血。** 一直挂着的那个整局满血；打的途中撤掉升级，马上开始掉血；按节律设备的两步切"亮"（撤暗、给亮）8 秒掉到 90% 以下，再切回"暗"后到结束不再掉。
- 对照：原版战役 A09 的铁幕光环物体（`A09_IronCurtainEffect`）放在靶子旁边：不掉血。升级直接挂原版 `AttributeModifier_IronCurtain`：前 20 秒不掉血，之后开始掉——修正自带的 `Duration` 经升级挂上也照样到时失效，所以长期开关的修正不能写 `Duration`。
- **关卡线该怎么改**：`tower_ball.py` 的暗修正加一个属性，`<AttributeModifier id="..._Dark" Category="NONE" ObjectStatusToSet="NO_BRIBE UNDER_IRON_CURTAIN" ...>`，`INVULNERABLE` 那行留着（测过的组合是两样都有；只设状态位、不写 INVULNERABLE 没测）。别的不用改：撤升级、再给升级都按第 1 节的规律走。

## 5. 时停区：一个隐形的光环物体，圈里敌我中立全停住；删掉物体或离开圈 1 秒内恢复（测）

关卡线 A3 问的（`docs/design/flow/a3.md`：子午线以东成了时停区，进去的全停住、敌我不分、打不坏，每隔一阵往西扩一圈）。

**找过的路子**：脚本动作里没有"给一块区域里的单位加状态"的（按区域的只有 `UNIT_KILL_ALL_IN_AREA`、守区、攻区；`UNIT_CHANGE_OBJECT_STATUS` / `TEAM_CHANGE_OBJECT_STATUS` 只给点名的单位或一队，管不到后来进圈的追兵）。原版的时间类效果：超时空裂隙（`SpecialPowerChronoRift`）是选一片再传送，不是冻住；时间炸弹（`AlliedTimeBombLvl1`）有寿命、最后要炸。现成能用的是两样拼起来：**光环模块 `AttributeModifierAuraUpdate`**（原版 A09 铁幕光环物体、本仓库干扰车 `units/jammer.py` 都这么用，`Relationship="ALLIES ENEMIES NEUTRAL"` 管敌我中立）+ **时滞炮车的"推出时间"修正**（`units/chronolag.py`：状态位 `UNATTACKABLE NO_ATTACK NON_AUTOACQUIRABLE IN_STASIS`、`SPEED 0%`、超时空裂隙的着色）。光环每隔 `RefreshDelay` 给圈里的单位挂一次修正，修正自带很短的 `Duration`，不再被挂就到时自己掉。

探针 `experimental/cnv/checks/engine_stasis.py`（单位就是里面的 `zone()`）。`cnv_check engine_stasis zone`（平地，测了两次，读数一样）、`cnv_check engine_stasis_plug plug`（窄口，`pathing.md` 第 7 节那张图）。时停区物体归敌方，半径 200，刷新 0.25 秒，修正 `Duration` 1 秒。

- **圈里的全停住，不分敌我中立**：我方坦克、我方步兵班、敌方坦克、中立坦克开局就在圈里，第 3 秒都下令开走：都没动。一直不动，到删掉物体为止。
- **追兵进圈就停**：圈外的敌方坦克下令穿过圈：在圈边停住。另一辆敌方坦克奉命去打圈里的我方坦克：自己开进圈里也停了（追着冻住的目标会把自己送进去）。
- **停住的打不坏、也不开火**：圈里的我方坦克从第 4 秒起被下令攻击，到删掉物体前一直满血；圈里敌我挨着站，没人掉血。删掉物体后马上开始掉血（对照）。
- **中途造出来的圈照样管用**：第 14 秒用 `CREATE_NAMED_ON_TEAM_AT_WAYPOINT` 在别处造第二个物体，站在那里的我方坦克马上停住，之后下令也不动。
- **离开圈就恢复**：圈里的敌方坦克被 `UNIT_TELEPORT_TO_WAYPOINT` 传到圈外，下一个命令照常执行开走。
- **到时间恢复 = 删掉物体**：`NAMED_DELETE` 那一秒，圈里所有单位的时滞状态位就没了（计数 1 秒内归零），可以动、可以打。
- **停着的时候下的命令不会丢**：第 3 秒下令开走的两辆车，删掉物体后没再下令，自己开走了（解冻后 3～7 秒出圈）；同在圈里、从没下过令的中立车一直没动（对照）。
- **冻住的车能把窄口堵死**：60 宽的口里停两辆敌方 MCV，各罩一个半径 45 的小时停圈。我方坦克一辆用移动、一辆用攻击移动去口对面：60 秒都没过去，也没去走远处开着的口（绕约 950）；冻住的车一直满血（攻击移动打不动它）；有一辆坦克挤着挤着自己进了小圈，也停了。对照 `pathing.md` 第 7 节：没冻的敌车，移动命令有一次 25 秒挤过去、攻击移动会把车打烂再走。

**关卡线照抄的写法**：

1. 单位：用 `checks/engine_stasis.py` 的 `zone(id, radius, hold, refresh, include)`（复制原版铁幕效果物体：不碰撞、打不着；去掉寿命和杀步兵的武器；换成上面的光环）。要正式用就搬进 `units/`（关卡线或单位线搬，模样是单位线的事；探针里沿用铁幕的球形模型，没管好不好看）。**已搬（关卡线 11-05）**：`units/stasis_zone.py`（探针的 `zone()` 的拷贝，`tests/test_stasis.py` 守两份一致）+ 设备 `时停区`（`devices/stasis.py`：几个圆拼一圈、到点造、可收）；A3 在用，测试台 `cnv_check a3 freeze`：圈一里的我方、敌方都停住，圈二到点长出来。圈心离悬崖/墙太近（`goal_invalid`）不影响光环。
2. 摆圈：圈是圆的，半径就是 `radius`。一块不规则的区（子午线以东一整片）用几个物体拼；往西扩一圈 = 到点在新的路点上 `CREATE_NAMED_ON_TEAM_AT_WAYPOINT` 再造一批。物体归谁都行（测的是归敌方；`Relationship` 三样全写了，归玩家或中立应当一样，没测）。
3. 收圈：到点 `NAMED_DELETE` 那批物体；1 秒（`hold`）内全恢复。只想要"冻一阵自己化开"也可以给物体加寿命（`LifetimeUpdate`：测试台 2026-11-07 `engine_life` 量过，秒数 × 15 截断成帧，30 秒活 450 帧、5.5 秒 82 帧；到点算"被摧毁"，当帧就从区域计数里消失，死法对得上的 `CreateObjectDie` 当帧在原地造出东西）。
4. 设计上要知道的：玩家停着时点的命令解冻后会接着执行；追敌的单位会把自己送进圈；冻住的车挡在窄路上就是一堵打不坏的墙，寻路也不会因为它去绕别的路（要绕得脚本改路点）。

没测：飞机（`include` 没写 `AIRCRAFT`，悬停的飞机会怎样不知道）；建筑（`include` 写了 `STRUCTURE`，没放建筑进去）；圈边上判定是到单位中心还是到外形（追兵在圈边停住，离圆心多远没量）；冻住的车解冻后是不是还记得原来的目标。
