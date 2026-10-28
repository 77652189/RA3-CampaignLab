# 游戏设计（策划线）

这个文件夹管战役关卡的"游戏设计"这一层：玩家的体验是什么、每一段让玩家在什么之间取舍、设计师为什么这样排。用户 2026-10-27 开的策划线，关卡线以后按这里返工。

**从 [charter.md](charter.md) 读起**：一关好玩要具备的四个条件（自主、胜任、代入、节奏），以及从想法到成品的 7 步工作流和每一步的闸门。其余文件都挂在工作流的某一步上：

| 文件 | 是什么 | 工作流里的位置 |
|---|---|---|
| [charter.md](charter.md) | **设计总纲**：四个条件、工作流、问题归层 | 入口 |
| [campaign.md](campaign.md) | 战役总表草稿：27 关的一句话概念、新花样、类型、出生布局、难度位置，标出重复、撞车、断档；最后是用户 2026-10-27 定下的 6 条 | 第 0 步 |
| [principles.md](principles.md) | 28 条设计准则（P24～P28 是地形和空军），按四个条件归组，标明在哪一步检查；每条写准则、为什么、出处 | 第 0～5 步的检查清单 |
| [a4-redesign.md](a4-redesign.md) | A4 试点：走完第 1～3 步（概念、体验设计、纸面原型和推演），写好第 5 步的试玩问题和给关卡线的实现清单 | 第 1～5 步的样板 |
| [plan-template.md](plan-template.md) | 策划案模板的增补建议，以及 plancheck 能查什么（只是建议，策划案和编译器归关卡线） | 第 3～4 步 |
| [playtest.md](playtest.md) | 给用户的试玩问题：玩哪两关原版，每关问什么；A4 的问题在试点里 | 第 5 步 |
| [teardowns/](teardowns/) | 准则的证据：原版任务的拆解卡，加布局卡和测量数据 | 证据 |

和其他文档的分工：
- [story/map-language.md](../story/map-language.md)、[story/plans/retail/](../story/plans/retail/)：原版**怎么做**（机制层，从脚本反推，带脚本名作证据）。拆解卡直接引用它们的事实，不重复抄。
- 这里：原版**为什么这样做**，以及我们该怎么做。

## 拆解卡怎么拆

每张卡先写 MDA 三层（机制 → 动态 → 体验），再回答 7 个问题：

1. **体验目标**：一句话，设计师想让玩家感受到什么。
2. **关键决策**：每一段玩家在什么之间取舍，为什么是真取舍。
3. **新机制怎么教**：教、练、考、变各在哪里。
4. **张力曲线**：紧张和喘息怎么交替，按分钟画一条粗线（`█` 0～5 格）。
5. **信息**：玩家什么时候知道什么；后果看不看得见；失败了知不知道错在哪。
6. **剧情转折是不是正好就是玩法转折。**
7. **地图**：哪条路、哪块地在支撑这些决策；出生点在可玩区的什么位置、背后是什么、目标在哪个方向多远、有几条路、奖励摆在哪（实测见布局卡）。

最后一节"可以借的 / 不该照搬的"把卡片连到准则编号上。

读法约定：
- 方括号里是原版脚本名（出自 `work/retailref/`，经 `plans/retail/` 的反推策划案转引），是事实的证据。
- "推断"：从脚本行为推出来的设计意图，原版设计师没说过。体验目标几乎都是推断，要靠试玩验证。
- 非红警的关（星际 2）用公开资料，每条事实注明出处网址。

## 拆了哪些

| 卡片 | 原版 | 类型 | 对照我们的 |
|---|---|---|---|
| [iga](teardowns/iga.md) | 起义时刻 盟军 1 伊贺国 | 护送 → 建基地 → 限时找人 | A4（护送 + 新单位教学） |
| [odessa](teardowns/odessa.md) | 红警 3 帝国 3 敖德萨 | 护航 → 英雄单位 → 拆基地 | A4、S2 |
| [stalingrad](teardowns/stalingrad.md) | 红警 3 帝国 2 斯大林格勒 | 建 → 攻 → 守护送路线 | A4、S6、J5 |
| [miyako](teardowns/miyako.md) | 起义时刻 盟军 3 宫古岛 | 基地对抗（会逃跑的首领） | A7 |
| [yokohama](teardowns/yokohama.md) | 红警 3 帝国 7 横滨 | 英雄开路 → 占点 → 守倒计时 → 限时拆 | S6、J7、J5 |
| [facility](teardowns/facility.md) | 起义时刻 百合子 1 研究所 | 突击队 | J3、A5、J7、S5 |
| [zero-hour](teardowns/zero-hour.md) | 星际 2 自由之翼 零点 | 守点 + 限时 | S6、J5 |
| [devils-playground](teardowns/devils-playground.md) | 星际 2 自由之翼 魔鬼的游乐场 | 机关式（环境周期） | A3、J2、S8、A8 |
| [layout](teardowns/layout.md) | **全部 40 张原版战役图** + 我们 11 关 | 空间布局：出生点、可玩区、目标方向、路线、奖励摆放 | 全部 |
| [terrain](teardowns/terrain.md) | **全部 40 张原版战役图** + 我们 11 关 | 地形复杂度（层、坡道、水、驻军楼、墙、隘口、俯瞰）和地图利用率（按阶段，只算走得到的地面）；末尾是给关卡线的生成器缺口 | 全部 |

布局卡的原始测量在 [teardowns/data/layout.md](teardowns/data/layout.md)（每关一行），由 [layout_measure.py](teardowns/data/layout_measure.py)（只读原版存档和 Mods 里我们编好的地图）和 [layout_table.py](teardowns/data/layout_table.py) 生成，改了地图可以重跑。玩家视角的时间线（每个时刻玩家看见什么）在 [teardowns/data/timeline.md](teardowns/data/timeline.md)，由 [timeline_measure.py](teardowns/data/timeline_measure.py) 生成，验收表在它开头。地形和利用率在 [teardowns/data/terrain.md](teardowns/data/terrain.md)，由 [terrain_measure.py](teardowns/data/terrain_measure.py) 生成（每张约 1 秒，`TERRAIN_PNG=<文件夹>` 出核对用的图）。玩家能不能造飞机、敌方据点有没有防空在 [teardowns/data/air.md](teardowns/data/air.md)，由 [air_measure.py](teardowns/data/air_measure.py) 生成。

[teardowns/data/](teardowns/data/) 里另外几份是子 Agent 整理的原始事实（横滨、研究所的脚本时间线，星际 2 和设计理论的公开资料网址），拆解卡引用它们；横滨、研究所的关键几条已对照原版脚本原文核过。

读原版导出时注意：`work/retailref/*.txt` 里条件行末的后缀 `+0100000001000000` 表示这个条件**取反**（横滨 56 处、研究所 25 处）。不看后缀会把规则读反。`plans/retail/` 里更早的几份反推策划案有没有读反，还没复查。
