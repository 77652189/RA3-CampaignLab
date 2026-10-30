# 模拟器能不能对比打法（代码调查）
子 Agent 调研，2026-10-30，总控派。【已证】=有出处，【推测】=推断。

**前提**：以下全是只读调查，没启动游戏或测试台，只用 python 读缓存 JSON 数了数。路径以 R=`C:\Users\63097\Documents\RA3Modding\RA3-CampaignLab` 为根。`sim.py`、`simunits.py`、`simstatic.py`、`simchecks.py`、`offline.py`、`plan.py`、`parts.py` 在 `R\experimental\cnv\`，`platmap.py`、`mapstudy.py` 在 `R\experimental\campaign\`。

**一句话**：它现在是"给一份人写的剧本，推演任务脚本的时间线和结局"，还不是"两种打法谁更好"的比较器。战斗、移动、视野有粗模型，经济、生产、AI 压力完全没有。

**1 战斗：有模型，但粗，现有走查都绕开它**
- 算法：每 0.5 秒，每个武器打射程内最近、打得着、己方看得见的敌人。伤害 = dps × 0.5 × 目标护甲对该伤害类型的百分比，同一刻结算（`sim.py:942-1002`，公式在 988）。只追被点名的目标（1006-1012），攻击移动遇敌停下（992、1013）。
- 数据字段：MaxHealth，ArmorSet 对应 Armor.xml（没列的伤害类型按 100%），每个武器槽的 PRIMARY 武器（`simunits.py:151,192-264`）。武器取 AttackRange、RequiredAntiMask、DamageNugget、弹体战斗部、ClipSize、FiringDuration、DelayBetweenShots、ClipReloadTime。没血量数据时建筑按 2000、单位按 300（`sim.py:433-436`）。没有溅射、弹道、最小射程、命中率、升级、技能、驻军、姿态、治疗（`sim.py:113-117`）。
- 精度：自己标"未对齐、最后上测试台调"（`sim.py:113-120`），测试台只对上"没人打冰墙"一条。测试只手算核对了一对单位（`tests/test_sim.py:169-179`）。数据有洞：`work/sim_combat_v2.json` 的 696 个模板只有 55 个读到武器，63 个三阵营可动单位里 23 个没有，含征召兵、阿波罗（`docs/design/teardowns/data/units_measure.py:17-18` 也说"三分之一读不到"）。够看量级，不够判"明显更好"。
- 所以现有走查都把战斗关掉、结果由剧本给：`不打; 自动打掉 5`（`tests/test_sim.py:193`，`offline.py:36`）。MCP 的 `plan_sim` 说明还写着"Combat is not simulated"（`experimental/testbench/bench_mcp.py:507`），已过时。

**2 移动**
- 时间 = 路径长 ÷ 速度，每 0.5 秒一步（`sim.py:51,1015-1025`）。速度取 LocomotorSet(NORMAL) 的 Speed（`simunits.py:68-76`），缺了按兵种默认，并列进"猜的"（`simunits.py:45-47`，`sim.py:1156`）。
- 路径既不是直线也不是路网：在高度图生成的 20×20 栅格上求最短路（`sim.py:64,246,315-334`）。可走 = 干地且坡度 ≤ 9/格，桥面 120 宽（`platmap.py:26,285,294-314`）。飞机走直线（`sim.py:317`），公路只是贴图（`platmap.py:49-54`）。
- 高地、悬崖只决定能不能走和看不看得见，不改速度；桥算（`sim.py:110-111,251-259`）。口子宽度：`Layout.gaps` 不被读（`platmap.py:72-91`，`sim.py` 无引用），只靠栅格几何间接起作用：整格须全可走（`sim.py:246`），冰墙和建筑圆盘能堵死（403-421）。单位没有体积、不拥堵，120 宽和 1000 宽的口子通行一样快。可玩边界不限制移动（`sim.py:1080-1081`）。

**3 经济和生产：没有**
- 没有收入、矿车、油井、费用、造兵时间、产能。money 只是脚本能设能加的数（`sim.py:364,731-736`）。玩家 `造` 免费、瞬间刷出，只查禁造（893-909）。`占领` 瞬间改归属，没有油井收入（888-890；`sim.py` 里没有 derrick）。
- 周边：造价只在 `offline.py:68-80` 读，BuildTime 哪都没读。测试台量过一次油井约 10/秒（`experimental/cnv/checks/a4.py:77-78`）。AI 造兵不模拟（`sim.py:106-107,757`）。

**4 敌人的波次**
- 策划案 `进攻` 的字段：名字、开始（条件）、兵 {单位: 数量，可按难度}、从（地点）、打/守、每隔、最多、来源、直到、加码（`docs/story/plans/README.md:68`，例子 139-151）。`plan.py:877-933` 把每一波 × 每个难度编成一条脚本，条件是旗标、计时器、计数 == i-1、来源未毁（出发点 901，上限 887，来源 898 和 927-930）。
- 模拟器直接跑编出来的脚本（`sim.py:656-670`）。拆掉 `来源` 里的建筑，后续波次条件不成立，不再来（`sim.py:543-550`），前提是策划案写了 `来源`。随机时间取最晚（653-655）。
- 两个洞。(a) 遭遇战 AI 只记一笔、不模拟（`sim.py:763-767`）：A4 北营是 AI 接管（`docs/story/plans/a4.md:234-242`），拆它在模拟里无事可发生；波次写了 `直到: 敌方AI 醒来`，之后脚本波次也停（`plan.py:899-900`），压力归零。(b) `打: 猎杀` 编成 NAMED_HUNT（`plan.py:941`），`sim.py` 没有这个动作，落进"不认识"（821-822），这些兵出来后原地不动。我们的 a4 到 s6 策划案没用，原版复刻稿用了（`docs/story/plans/retail/j02_stalingrad.md:336,341`）。

**5 玩家打法的输入**
- `--script` 只是带时间的事件清单：派/摧毁/删除/血量/打/占领/旗标/造，加全局开关 自动打掉/不打/高地不挡（`sim.py:19-34,866-910,1192-1228`）。没有条件、循环、"钱够了再……"。`派` 一律是攻击移动（872），`摧毁` 不要求有人在场、瞬间生效（874-880）。
- "守家造兵，第 N 分钟出击"只能手写 N 条免费瞬时的 `造`，再加一条 `派 名字含 SIM Made 去 …`（`sim.py:848-850,906`）。没有"策略"这一层：一次一条剧本、出一份文本报告，没有批量对比和评分（`sim.py:1231-1252`）。`simchecks.py:20-58` 只是"剧本 → 期望结局"的接线检查。`sim.simulate()` 可编程调用，一关几秒（`README.md:17`）。

**6 视野与迷雾：做了一半**
- 有：视野 = max(VisionRange, ShroudClearingRange)（`sim.py:430`）；看不到比自己高 40 以上的地面（65、600-609）；开火的远程单位 3 秒内暴露（67、616）；揭图（594-597、775-790）；战斗只打己方看得见的（972、981）；已知面积统计（1062-1083）。
- 没有：建筑树木遮挡、隐身探测，玩家下命令也不需要先看见目标。高地规则和 NAMED_DISCOVERED 都是"未对齐"（85-87、121-128）。11 关对照开关，结局一样（`docs/story/plans/README.md:32`）。所以"地形伏击"目前靠一条没验证的假设。

**7 地图的形式**
- 地图是 Python 模块 `experimental/cnv/maps/*.py`，发布 `SITES`（`parts.py:47-56`，命名地点 x、y、r）、`BORDERS`、`OBJECTS`（矿、油井、桥）、`SCENERY`、`LAYOUT`（`platmap.py:84-91`：地块高度、坡道、路、`blocks` 用途、`gaps` 口子）。
- `sim.py` 用 SITES 当地点名（451-466），LAYOUT 只取高度再算可走栅格（231-237），OBJECTS 和 SCENERY 建筑当障碍（254-259、385-389）。blocks 和 gaps 不用。没有"区域—通道—据点"图，路线靠栅格自己找。
- 与 cnv_map、mapstudy 没连：它们看编好的 .map（`bench_mcp.py:596-608`，`mapstudy.py:1-19`），`sim.py` 直接读 Python 模块（227-259）。只共享 `work/sagexml_gameobjects.json`（`mapstudy.py:46`，`simunits.py:17`）。旁路文件 `cnv_map.json` 只存边界，给测试台用（`parts.py:650-658`）。`docs/story/map-language.md` 第 7 节（155-240）是原版节奏的文字总结，没有机器可读的对应物。

**8 ALIGN 表里没对齐的**（`sim.py:76-129`，共 21 项）
- 标"未对齐"的 7 项：kind all players（80，测试台已测、只是与《将军》不同）、discovered（85）、both endings（90）、difficulty side（98）、ra3 only（103，32 个动作和条件见 132-142，`docs/story/plans/README.md:36` 写 30，已过时）、combat（113）、high ground（121）。
- 另有记下但无效果的：special power（104）、ai（106）、attack（108）、guard（109）。其余已按源码或测试台定下。对比打法要紧的是 combat、high ground、discovered、ai、special power、difficulty side。

**总结**：要让模拟器可信地比较打法，最缺三样。(1) 经济和生产：最小版是油井和矿厂的定额收入、BuildCost/BuildTime、每个生产建筑一条队列、`造` 要花钱排队。约 3 到 4 天，再加约 2 到 3 天上测试台对齐收入。没有它就说不出"平推更贵"，因为 `造` 现在免费瞬时，也表达不了"先占油井"的收益。(2) 能写成策略的玩家层加批量对比：带条件的规则（钱够造、兵够了出击、敌人近了），一次跑"策略 × 难度"，输出统一指标（通关时间、花费、按造价算的损失、剩余血量、首次接敌）。约 2 到 3 天，`simulate()`、`metrics()`（`sim.py:1160-1181`）和造价读取（`offline.py:68-80`）可复用。(3) 敌人和战斗的可信度：补武器数据约 1 天，实现 NAMED_HUNT 不到半天，做 AI 压力的替身约 2 天（可参照 `docs/story/plans/README.md:70` 的测试台实测和 `map-language.md:174-177` 的唤醒时间），战斗和高地视野上测试台标定约 3 到 5 天。这样才能回答"拆压力来源""地形伏击"。合计约 2 到 3 周，以上人天是我按代码现状的粗估，仓库里没有这些数。在此之前它只能回答"这条路线能不能走通、会不会触发胜负"，支撑不了"巧解明显优于平推"的结论。
