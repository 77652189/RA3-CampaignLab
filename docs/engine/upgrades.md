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
