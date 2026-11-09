# 遭遇战 AI 打"点名"的物件和路点

引擎线 B 第 53 轮（2026-11-08），ADR 0019 第四层（遭遇战 AI）、ADR 0026 原版功能清单的"目标"项。写法照 `script-semantics.md`：**测** = 测试台；**读到** = 程序里读到、没上测试台；**推断** = 只从资料推出来。

原版战役让 AI 打指定的东西，几乎全靠两类目标启发：`NamedObject`（145 条，143 条是战役的 `AITarget_*`）和 `Waypoint`（94 条，92 条战役）。每条只写 `Name`（物件的脚本名 / 路点名），有时加 `Relationship`、`Location`、`RequireUniqueTarget`。

探针 `experimental/cnv/checks/engine_ainamed.py`（任务 `missions/ainamed_bench.py`，用 `aitarget_bench` 的图：东门有座带两座炮塔的近电厂，AI 基地南边有座不设防的远电厂）：敌方一个常开状态，2～4 个维和步兵，`SimpleAttack`，打完 `RAMPAGE`，目标启发换成本探针自己写的一条。

## 给关卡线的结论

1. **`NamedObject` = 直接打这个名字的物件，不管远近（测）**：点名远电厂（`ainmfar`），队伍绕开更近的东门、先打远电厂，打掉以后才（`RAMPAGE`）转去近厂。按距离找（`ClosestStructureHeuristic`）会先去东门。
2. **`Waypoint` = 走到这个路点，然后一直待在那儿（测）**：路点那里什么都没有（`ainmwp`），队伍走到后 60 多秒一直守在点上，不解散、不转去打别的。
3. **写了 `Relationship` 就按关系过滤（测）**：同样点名远电厂，但写 `Relationship="NEUTRAL"`（`ainmrel`）——远电厂是玩家的（敌方），不算数，**没有目标、队伍不出门**。不写 `Relationship` 时不查关系，敌方、自己、中立的物件都能当目标（读到）。
4. **名字查不到就没有目标、不派队（测）**：`ainmnone` 点了一个不存在的名字，队伍一直在家。名字区分大小写（读到）。
5. **只查这几样（读到）**：`NamedObject` 只看名字、`Location`（水 / 陆）、`RequireUniqueTarget`、`Relationship`；`VitalKindOf`、状态、`SearchRange`、`SortType` 都不看。`Waypoint` 除了 `RequireUniqueTarget` 什么都不查；它的"唯一"按坐标精确相等比——两个名字不同但坐标完全相同的路点算同一个目标。
6. 关卡用法：要 AI 打某个建筑 / 守某个点，给物件起脚本名或放路点，状态里写一条 `NamedObject` / `Waypoint` 启发；想让几支队伍分头打几个点，每条都写 `RequireUniqueTarget="true"`、`MaxTargets` 写够。

## 读数（2026-11-08，各一次）

- `ainmfar`：到远厂 2 @ s15，4 s17～s33，s34 远厂没了；到近厂 3 @ s43（`RAMPAGE`）。
- `ainmwp`：到路点 2 @ s6，4 从 s8 一直到 s75；近厂、远厂全程 0。
- `ainmrel`、`ainmnone`：步兵在家全程 4。

## 没测

同名多个物件取哪个、物件死了以后（`NamedObject` 有个对象标志位检查，没对上是哪个状态）、`Relationship` 其他取值、`Location`、`RequireUniqueTarget` 两队分头、`Waypoint` 配 `DefenseAvoidanceAttack` / 防守类战术。
