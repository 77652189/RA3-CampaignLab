# 关卡线交接（ADR 0016 第 4 阶段起；2026-11-08 夜瘦身重写，上一个会话是第四十六个）

## 现状（一句话）

按 [ADR 0026](../adr/0026-engine-first-retail-inventory.md)（引擎优先）关卡线**暂停推新关**：A4 对照局收尾，然后做"原版战役关验收题"和"自动玩家框架"，题卡和数值区间只做纸面打磨。9 关都已有草稿（各关状态见下），但"可试玩"标准（ADR 0023 第 3 条）没有一关全部满足，所以不交用户试玩。

## 当前目标与下一步（总控 11-08 晚定，按顺序）

1. **A4 对照局收尾**（归因 2 已做完，见下"A4 对照局"）：剩的差异归战斗模型，不是关卡规则；`a4` 的 `play` 不进 `EXPECT`。把已有结论提交即可，不再继续归因关卡侧。
2. **原版战役关验收题**（第一步已查）：测试台跑 mod 战役任务**不写录像**（`Last Replay.RA3Replay` 修改时间仍是 2025-09-25，5 个手工录像是 10-15～11-05 留档）；原版战役关本身没直接试过（要手动玩一局原版战役再看 `Documents/Red Alert 3/Replays/` 有没有新文件，约几分钟）。默认走"测试台脚本驱动的检查"。**第二步已查（Sonnet 子 Agent 试盟军第一关，我核对了帧存档 `work/testbench/runs/RA3_mcp_1108_165118`）：部分能。** 不用放进 mod：`bench_start(mod="")` 起无 mod 原版游戏（`experimental/testbench/harness.py` `Session.start`），按 `nav.json` 走战役菜单约 60 秒进盟军第一关。能：`bench_status` 读任务秒、暂停保持、`bench_wait` 推进、`bench_menu` 读任务目标、`bench_look`、`bench_box` / `bench_click(world=false, right=true)` 屏幕像素框选和右键移动（部队确实动了）。不能：`bench_counters` 返回 `? ?`（原版图没有 DISPLAY_COUNTER）、`bench_caption` 无信号、**世界坐标标定无效**（`bench_where(1000,1000)` 给出 (1414,-3587)；原版图没有 `cnv_map.json`，`bench_click` / `bench_ability` 的 world 模式和 `bench_camera` 不能信）。只试了第一关；`bench_start` 的 `chapter` 参数只对 CampShell 有效，选原版第 N 关的办法没定。**下一步路径（推荐序）**：① 先按"屏幕像素 + 任务秒 + `bench_menu` 目标状态"做第一道验收题（比结局和关键时间点；派兵靠看图定位，脚本化弱）；② 给原版图补世界坐标标定（用 `map_study` 已有的边界 / 地形生成 `cnv_map.json`，让 `calib.Ground` 读原版图；测试台线的活，经总控约接口）；③ 要读内部状态才做带计数脚本的 mod 副本（会改地图，最后手段）。**第三步（Sonnet 子 Agent 只读调查，证据在报告里的文件:行号，临时输出 `work/logs/a01_probe.log`、`a01_dc.log`、`retail_s01_counter.log`）**：**A 标定读当前地图 = 中**：`calib.py:105` 屏幕映射 `_H()` 是只对 CNV 岛图默认相机拟合的固定单应矩阵（`work/testbench/calib.json`，用 5×5 网格单位拟合）、`START_VIEW=(1296,2466)`（`calib.py:165`）写死；`world_to_minimap`（`calib.py:139`）只要可玩区边界、通用；地形高度 `Ground`（`calib.py:202-233`）读 HeightMap。原版 a01 的 `.map` 在 Steam 的 `MapsCampaign.big`（`camp_a01_brightonbeach_smith`），`mapstudy.retail_maps` + `mapterrain.HeightMap` 实测读得出（575×575 格、border=50、3 组边界，单位是格要乘 CELL=10）。缺口：(a) `maprender.load`（`maprender.py:226-246`）对 .big 只取第一张图，要按包内路径读（`mapstudy.py:57` + `big.read_files`）；(b) **相机是真问题**：a01 脚本有 `ZOOM_CAMERA(0.85/0.8)`、`ROTATE_CAMERA`、`RESET_CAMERA`，H 在默认缩放下拟合，原版必偏，要用图上已知位置的建筑/单位重新拟合（**要启一次游戏做标定**）；(c) 当前跑哪张图目前只有 mod 名，`harness.start` retail 分支把 `borders=[]`（`harness.py:360`）。**B 原版关加观测层 = 难**：现有"测试版=正式版加观测"是模型层 `model.merged` + `package.check_layer`（`package.py:270-305`），依赖 cnv 的 `Mission`，原版图没有；同名覆盖不可靠（`mapxml.py:12-14`，官方图读编译 stream）；改名拷贝有先例（`make_campnew2.py`、`chaos_map.py`、`shell.py` 槽位），但要连带处理 mapxml 链接和图缓存。**附带发现**：a01 自带 2 个 `DISPLAY_COUNTER`（`A01_Javelin_Counter`、`A01_IFV_Counter`），只在对应奖励目标出现后才显示，所以 `bench_counters` 读不到**可能只是还没亮**，没验证；`bench_counters` 靠帧截图 OCR（`bench_mcp.py:346-360`）。**【11-08 夜已做通 A】** 原版图按名读、边界读地图、a01 开局相机用栅栏柱 + 小地图梯形拟合（残差 2.8 像素，跳转后平移模型也对），第一道题 [retail-q1-a01.md](retail-q1-a01.md) 出了（开局小队走到指定点 ≈2.5～3 秒）；下一道做阶段目标和两个自带计数器是否亮；别的关 / 变焦后的镜头要另拟合；MCP 服务重启后才有 `retail_map` 参数。**总控 11-08 夜追加的下一步（停止条件 ②）**：① 把第一题放进模拟器跑一遍对拍（原版 ≈2.5～3 秒、停在目标 19～23 单位外）。注意 `sim.py` 只跑 cnv 的 Mission（`parts.merged`），**读不了原版图**；两条路：(a) 只为这道题造一个"空任务"——放 a01 的地图和开局 6 个单位（位置读 `retail_objects`，开局小队是脚本生成的、不在地图物体表里，要按第一帧位置反推），不带原版脚本；(b) 做"原版脚本适配器"（`retail_scripts` 已能读出原版脚本）——大活，归引擎线，先别碰。推荐 (a)，对不上归因报引擎 A/B。② 按 `docs/engine/inventory.md` 选第二、三道原版关（用量大、状态未对拍的项覆盖面广的关），每关先拟合一台相机（做法见 retail-q1-a01.md，`calib.py fit_retail`）。**判断：先做 A，B 暂缓**（先看 a01 自带两个计数器够不够用）。验收题第一道先走像素路线不等 A：盟军第一关，读任务秒 + `bench_menu` 目标状态 + 两个自带计数器是否亮。再从 `docs/engine/inventory.md` 挑用量大、"未做 / 推断"的项、覆盖面广的几关；录像比对工具归引擎 A（`experimental/replay/`），需约接口（经总控）。
   **【总控 11-08 夜最新指示（自动玩家做完后）】** 引擎 A 的原版任务载入器 `experimental/cnv/retail.py` 已能在模拟器跑盟军第一关（提交 54a9651）。接着：① 读 `docs/engine/inventory.md`，选覆盖用量大、未对拍的项，挑第二、三道原版关；② 每关先拟合一台相机（做法见 [retail-q1-a01.md](retail-q1-a01.md)、`calib.py fit_retail`，要启一次游戏抓帧）；③ 每道题在测试台（`bench_start(mod="", retail_map=...)`，像素路线）和模拟器（经载入器）各跑一遍比结局和关键时间点，载入器读不了的东西写清楚报引擎 A；④ A3 / A4 的设计问题只记录（见 [autoplay-a4-a3.md](autoplay-a4-a3.md)），关卡暂停期间不改。装 mod / 起测试台前先检查游戏是否在运行（`RA3_1.13.game`），在运行就停下问。
   **【11-08 夜第四、五道题已做（帝国 j01、苏联 s01 第一关，开局目标时间线）】** 见 [retail-q4-q5.md](retail-q4-q5.md)：只能进各阵营第一关（`harness.faction_steps`，`retail_map=camp_j01…/camp_s01…`，脚本 `testbench/retail_q45.py`）；j01 sim 比游戏晚约 18 秒亮目标；s01 sim 跑不起来（缺区域 KeyError）且补上后 0:17 误判输（`Loss - Natasha`），均归引擎 A。后面的关（j02…、s02…）没有进法，要做得做帝国/苏联的战役壳。
   **【11-08 夜第二、三道题已做（开局目标时间线，不派兵）】** 见 [retail-q2-q3.md](retail-q2-q3.md)：进 a02 / a03 靠只带一关的战役壳 `CampShRetail`（原版战役线性，`bench_start(mod="")` 进不了第二关）；a02 模拟器比游戏晚约 10 秒亮目标，a03 模拟器目标一直不亮（卡住）——都已写明归引擎 A。下一步：要比结局就得打这两关（相机标定 + 派兵）；或先等引擎 A 修 a03 / s01 后重跑。
3. **自动玩家框架 `experimental/autoplay/`**（ADR 0026 第 4 条）**【11-08 夜已搭好并在 A3 / A4 出了分布】**：说明和结果见 [autoplay-a4-a3.md](autoplay-a4-a3.md)，测试 `tests/test_autoplay.py`。要点：A3 谁打都 1:20 赢（设计 16 分钟，a3 归因没做）；A4 自然玩法 0/30、照题卡 7%～47%。后续：给 rush / counter 加建造和放技能、其它关写 `levels.py`、挑一局导出剧本上测试台对拍。
4. 纸面：题卡"几句话"和各关数值区间（暂定 8～15 分钟，各关题卡可另定）的打磨。

## A4 对照局（11-08 结论，详见 `docs/story/sim-vs-bench-a4.md`、`docs/story/sim-vs-bench-plays.md`）

- 模拟器完整播开场过场（s0～79.9，锁操作），测试台跳过它：**测试台时刻 = 模拟器时刻 − 79 秒**；`playcheck.SCENE['a4']` 已按此对齐。
- 测试台 `cnv_check a4 win` PASS（重跑一次的那次；第一次 FAIL 是阶段过场里 Esc 暂停失败，老毛病，失败先重跑）。
- 测试台 a4 `play` 比模拟器早输：连跑 4 次，1 号车首次掉血在 s126～151，模拟器要到 ~s221（对齐后）。原因读到的是第二声号角的 3 个坦克杀手 + 3 个武士在路东 x≈1850 与护卫交火，其中一个坦克杀手打到车，模拟器里同一批敌兵被护卫更早杀光。**差在"最后一个坦克杀手死得早几秒"（击杀速度、索敌优先级、护卫站位），归引擎 B（AI）/ 引擎 A（武器），不是冰、号角、护卫调度。**
- 没查：坦克杀手射程是否真是 175、是否优先打车；s249～259 车的死因；测试台单局间有差异（首伤 s130 vs s151），对拍应看区间。
- 探针做法：临时把 `playcheck.BENCH_ENDS['a4']` 改成 `[118]`，`cnv_check a4 play build=false keep=true` 停在 s117，`bench_camera 1650 2500` + `bench_watch seconds=14 every=2 world=true x0=1250 x1=2050 y0=2300 y1=2750`；用完 `git checkout experimental/cnv/playcheck.py`。

## A4 当前状态（ADR 0023 验收三条）

- 放冰明显长于不放冰：成立（模拟器：放冰 5:11 完成丢 1 辆，不放冰 3:12 输）。巧解能赢：成立，全程 `experimental/cnv/plays/a4.txt` 模拟器 14:48 赢，丢 1 辆（落在 8～15 分钟）。"自然打法明显更难但不必输"：放宽后基本成立（不放冰输在 3:00～4:00，一种接力站位活到底）。
- 容错窄的真因是**兵只认车、路过军队不理，车尾后面的街出来的兵从后面扑车**，不是兵数 / 车血 / 冰寿命。已改规则（`docs/story/plans/a4.md`）：`雪祭.收`（过场前停号角并删场上兵）、新键 `止: k`、`每口一波`、会场每街一波 2 武士 + 1 坦克杀手；绕路表 25/35/25/45/35/45 秒（落在两声号角中间）。
- 测试台已验这批规则编出的脚本无报错（`cnv_check a4 win` PASS）。
- **没做**：`plays/*.txt` 里 `造` 换 `生产`（2342aca；a4 北营 14 行 `造`，换后重跑 a4 看时间落在 8～15 分钟）；最后一程有冰版 / `hard` 难度；电视塔奖励目标；a3 为什么 1:25 赢的归因（剧本绕开时停区，还是规则太易，题卡设计约 16 分钟；B 线 a24c6c0 已把时停区补进模拟器）；按难度分绕路表（`25/25/20` 写法）。

## 其它关的全程脚本与缺口（`experimental/cnv/plays/<关>.txt`，命令 `python -I -X utf8 experimental/cnv/simshow.py <关> --script experimental/cnv/plays/<关>.txt`）

- a1 6:54 赢、a8 4:24 赢、a3 1:25 赢、a6 12:56 赢、a7 6:27 赢、a9 3:42 赢（不可信）、j7 2:01 赢（模拟器数值会随引擎线变，以重跑为准；引擎 A 44b9bc5 后 j7 7:00 输、a7 / a8 的"赢"不再成立）。`playcheck.EXPECT` 只放两边一致过的，现在只有 a3。
- 对照局：a3 对上；a1 / j7 走路阶段对上，最后一仗对不上（模拟器过乐观）；a6、a9 的测试台 `play` 没跑；a7、a8 的 `play` 检查没注册（等模拟器稳）。
- 覆盖清单：`python -I -X utf8 experimental/cnv/simcoverage.py`，最近一次 293 项全已登记；`Sim.unmodeled` / `Sim.gap` 由引擎 A 线加。关卡线后续：a7 剧本把"派 engineer 去 station"换成 `占领 engineer 进 station` 并更新 simcoverage 登记；A 线 `fire_spot` 提交后隔墙 `攻击` 结果可能变，要重跑 `test_sim -k wiring`。
- a6 脆弱：撤出段是惊险的仗，内圈段命令时间按塔倒的时间估，参数变了要重调。
- 剧本动词：`派`、`造`（造出来就在，没有造价和建造时间）、`攻击 <谁> 打 <目标>`、`占领 <谁> 进 <建筑>`、`放 <谁> <技能> 在 <地点>`、时间可写 `旗标+秒`。

## 各关现状（草稿标准：能打通、地图看得懂、新单位机关能用、K 规则全过、题卡写清好玩假设）

设计侧总表见 `docs/design/draft-inventory.md`（A7/A8 行已过时）。有草稿：A1 金门、A2 胡佛坝、A3 格林尼治、A4 札幌、A5 巴拿马、A6 巨石阵、A7 尼亚加拉、A8 海岛（占位图）、A9 布鲁塞尔（S9、J9 共用此图）。**A5 水位升降引擎里没有对应动作**，草稿用按时出现 / 消失的实体代替，向引擎线问的三件事（改水面 / 地形高度办法；物体按时出现且步兵能走上去；船当梯子）总控一直没回，仍未知。

## 模拟器在其中的位置（ADR 0022～0026 约束，勿改）

- 对齐优先、修改同步（用户 2026-11-08 原话）："最重要的一点是模拟器和游戏需要对齐，这是最优先事项，否则模拟器会成为新的bug来源"；"不能只在模拟器修好，模拟器必须完全和游戏行为一致，修改要同步"。关卡问题只改游戏与模拟器共用的源头，不许出现"只在模拟器里好了"。
- 用户 11-08 关于引擎：（"引擎线给关卡线服务是依赖倒置的设计，我们应该先确保引擎线有实现原版各个功能的能力，然后再去做关卡，不然就得反复回头重做"）。
- 模拟器结论要有三个前提才可信：规则有对拍、覆盖可查、对照局复核（差 ≥15% 停下归因）。试玩放游戏里（ADR 0025），攒一批再交。
- 文件所有权：`sim.py` / `simunits.py` / `simcoverage.py` 归引擎 A；`simproxy.py` / `ra3model` 归 B；关卡线只提供关卡侧数据、剧本和对照局。**不要带进提交别的线没提交的改动**（现工作区有 `docs/engine/inventory.md`、`experimental/cnv/inventory.py`、`sim.py`、`tests/test_simbench.py` 等）。

## 仍有效的规矩与坑

- 引擎行为先查 `docs/engine/` 下各篇（脚本参考原在本机 `work/re/ra3-script-reference.md`）；查不到写进汇报交引擎线，别在测试台试错。
- 字幕：游戏里军事字幕与配音字幕进同一累积框；功能句靠 `ctx.py` 的 `Talk`、`FUNC_HOLD`、`FUNC_LATE`、产物规则 `contract.said_once_and_on_time`；展示层 K1 / K5 检查在 `experimental/cnv/simshow.py`。没在游戏里验过的：对白面板里中文显示与保留时间、过场里只有面板字幕时小窗头像是否打架。
- 策划案与代码同源（用户要求）：策划稿里手写坐标 / 数值要改成引用地图公开地点名或加检查（曾有停车点 x=2980 与地图 2830 对不上）；还没系统查过其它策划稿。
- 过场画面是梯形（`model.LETTERBOX_BAND`、`in_letterbox`），不是矩形；`plans/a4.md` 里"约 820×345"是旧数，下次动该文件时改成"梯形，远边 1125 宽、近边 733、带高约 500"。
- `stance` 类命令（停火姿态）在测试台试过没用，兵照样开火（`docs/engine/terrain.md`）；时间 0 的镜头移动会被游戏重置，要延后（`plan.opening_camera`）。
- 房子行（`platmap.house_row`）挡不挡得住步兵没单独在测试台验；其它图（brussels、greenwich、hoover、siberia、niagara）仍有大片垫高、同类地形问题，G15 守卫只管声明了 `Block` 的图（现 4 张）。
- `a4 win` 测试台失败先重跑一次（阶段过场里 Esc 暂停失败会被当"任务结束"）；`bench_watch` 的段尾别落在阶段过场里（阶段起止时间漂 ±15 秒，留余量）；手动 `bench_wait` 进过场后游戏不再暂停，要 `bench_stop`。
- 装 mod / 测试台前单独检查游戏是否在运行（`RA3_1.13.game`），在运行就停下问；Steam 重启可解"menus stuck at main menu"。
- 全量测试写 `pytest -q tests`（不带目录会扫进 `work/downloads/blender`）；全量约 26 分钟，输出写 `work/logs/`；本机 8 核，并行跑 `a4waves` 超过 8 个会很慢。
- Bash 钩子会拦 heredoc / `sed -i` 里带反斜杠的写文件，改文件用 Edit / Write；Git Bash 里 `pgrep` 看不到 Windows 进程，用日志首行判断后台任务是否结束。
- 已知未结的 smash 谜：鬼王"每帧重下攻击令 + 目标要绕路"时不开火，机制没弄清（`horn.py` 每面墙只下一次令的写法保留）；G16 守卫是否恢复由 `contract.py` 主人定，见 `docs/story/sim-vs-bench-a4.md`。

## 指针（只给位置，不抄正文）

- 总方向：`docs/adr/0022-simulator-before-levels.md`、`0023-simulator-as-daily-verifier.md`、`0024-playable-simulator.md`、`0025-playtest-in-game-replays-check-sim.md`、`0026-engine-first-retail-inventory.md`；归类修法 `0015`；一类一个出口 `0016`；分层移植 `0019`。
- 引擎清单：`docs/engine/inventory.md`（脚本生成，勿手改）。
- A4：`docs/story/plans/a4.md`（规则）、`experimental/cnv/plays/a4.txt`（全程剧本）、`experimental/cnv/checks/a4.py`、`experimental/cnv/playcheck.py`、`experimental/cnv/simbench.py`、`docs/story/sim-vs-bench-a4.md`、`docs/story/sim-vs-bench-plays.md`、`docs/story/map-diagnosis-a4.md`（地图设计感诊断）。
- 设计：`docs/design/principles.md`（P36 地形）、`docs/design/draft-inventory.md`、`docs/story/map-language.md`、`docs/story/graybox-cards.md`。
- 缺陷台账：`docs/issues.md`（I19 A4 不操作约 60 秒战败仍等用户，不动）。
- 本机临时工具（`work/` 不进 git，可能已变）：`work/re/scripts/a4plays.py`、`a4rules.py`、`a4climb.py`、`a4probe.py`、`a4pos.py`、`a4kills.py`、`a4waves.py`、`simall.py`；日志 `work/logs/`、测试台 run `work/testbench/runs/`。

**可以清空：读本文 + `docs/adr/0026-engine-first-retail-inventory.md`，接着做"当前目标与下一步"第 2 条：先查原版战役地图能否放进 mod 由测试台起局，再挑验收关并与引擎 A 约录像比对接口；然后第 3 条。**
