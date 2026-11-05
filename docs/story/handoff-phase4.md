# 关卡线·ADR 0016 第 4 阶段交接（2026-11-04，第十一个会话，24 万上下文时写）

总控令（local_79408d22）：第 4 阶段做生成器 K4 资源（I6、I9）、K3 施法点（I3）、K7 挡路（I8）。每类四样：生成器或出口、对全部关卡生效的产物规则（放 `contract.py`）、守卫（`tests/test_architecture.py`，含变异检验）、`docs/issues.md` 标"修了待验"。每类做完：`fingerprint.py record p4_k<N>` 对上一次比；`pytest -q tests`；`cnv_preview`。不许改 plan.md、ADR、HANDOFF.md，删文件先问，05:45 收到收尾通知就停（06:00 关机）。

另有三件新规矩（总控 11-04）还**没做**：
1. 引擎行为先查 `docs/engine/ra3-script-reference.md`（引擎线在写）；查不到就写进汇报交给引擎线，别在测试台试错。
2. **K1 补"功能句不能晚"**：功能句不光不丢，还要在事件发生后一个上限内播出（上限写成常量），"号角响了！"曾比号角晚 14 秒。要加产物规则并在 sim 里断言；可以让闲话让路或让功能句插队。（`cnv/ctx.py` 的 `Talk`、`contract.said_lines_kept`、`tests/test_talk_queue.py`。）
3. **策划案和代码同源**：策划稿里写的停车点 x=2980、地图里是 2830。要查策划稿里还有哪些手写坐标 / 数值，改成引用地图公开的地点名，或者加检查让两边对不上就报错。

## 第十二个会话（11-04 凌晨，引擎线 E1～E4、E6 做完，K3、K7 还没动）

总控令（local_79408d22）：按 E6 → E1 → E3 → E2/E4（只改 sim）→ K3 → K7 做。依据 `work/re/ra3-script-reference.md` 第 1 节（本机文件，不进仓库）。

- **E6 台词通道（推翻了 K1 的一个假设）**：屏幕上有两条字幕。上方军事字幕框是单行的，新句顶掉旧句，每句到自己的秒数就没；下方对白面板累积（只有带字幕的配音句进去，约 5.4 秒后整条清）。出口现在是（`cnv/ctx.py` 的 `Talk`、`Line`）：
  - **功能句**＝军事字幕，事件那一帧发（脚本 `Now k`，条件只有"要显示"旗、没有别的），配音（如果有）进功能队首；配音事件**不带**字幕。两条功能句同一时刻：后一条等前一条显示满 `FUNC_HOLD`=2 秒再顶掉它，三条同时刚好卡在 `FUNC_LATE`=4 秒内，第四条会被 sim 报晚（`Sim.late_captions()`）。
  - **配音的闲话**（和过场里所有配音句）＝只放配音、带自己的字幕走对白面板，**不发军事字幕**。`plan.py` 登记 `m.subtitles[事件]=字串`、`voice.subtitled`，`experimental/voice/pack.py` 的 `xml(subtitles=<集合>)` 只给这些事件写 `SubtitleStringName`。同一个录音既当功能句又当闲话会报 PlanError。
  - **没录音的闲话**＝军事字幕，排队，等"字幕框空着"（旗 `Box`）再放，占框 4 秒（`CAPTION_TURN`），不会顶掉还在读的功能句。
  - 去掉了 `STRIP_CLEAR`（6.5 秒下限）：配音句占地板＝录音长度＋`SPEECH_GAP`，纯字幕句＝它自己的阅读时长；过场里一句接一句，同样按各自的时长（`plan.py scene_steps`）。
  - sim：军事字幕单槽（`box_log`、`box_at(t)`），对白面板累积（`panel_log`、`panel_at(t)`，`ctx.PANEL_CLEAR`=5.4），`late_captions()`（过场的秒数不算晚）。
  - 产物规则 `contract.said_once_and_on_time`（并进 `contract()`）：同一脚本既放带字幕的录音又发字幕＝错；字幕文字和某个带字幕录音的文字相同＝错；`Now k` 只许等自己的旗、过场结束和上一条功能句；功能队的 `Say k` 里不许有字幕；录音包带字幕的事件集合必须等于任务登记的。守卫：`tests/test_architecture.py::test_g3b_*`（所有关的产物规则、变异检验、sim 里没有晚的功能字幕）。
  - A4 sim：配音闲话进面板（47 个带字幕事件，8 组面板），军事字幕框 9 句，丢 3 句闲话（以前 8 句），"号角响了！"在 104.5 秒（号角那一刻）出，不再晚 14 秒。
  - **没在游戏里验过**：①配音事件带字幕后，对白面板里中文的显示和 20 秒保留（引擎线说 HoldTime=20s，和量到的 5.4 秒对不上）；②过场里配音句只有面板字幕、没有上方字幕，小窗头像和面板是否打架；③用户 11-03 嫌的"字幕叠"现在回来了，是面板的原版观感，要不要换由用户看了定。**注意**：之前的代码（da56a2e 起）配音事件本来就不带字幕，所以"显示两遍"只在更早的构建里有，这次是反过来让闲话重新走面板。
  - 指纹 `p4_e6` 对 `p4_k4`：a4、shell、shell_intl 三个目标各变 7 个文件（`camp_cnv01_probe.map`、`static.12/static_l.12/static_m.12` 的 bin 和 manifest）加 47 个带内容哈希的 cdata（47 个配音事件的字幕属性变了），音频视频纹理模型没变。
- **E1**：`devices/carrier.py` 的自由号落点改成"玩家在区里没有单位"取反（`SKIRMISH_PLAYER_HAS_UNITS_IN_AREA p1 区 NOT`）；`空虚` 参数保留但不再起作用（引擎数不出"玩家的单位少于几个"）。**语义变了**：以前"武装单位少于 3"，现在"一个单位也没有"（建筑也算），A7 的落点 `base edge / base ore / front` 靠近玩家基地，可能很少选到前两个——要策划线和测试台看一眼 `a7 jumps` 的选点是否还合设计。产物规则 `contract.kind_counts_in_area`：正式脚本不许用"按种类数区内单位"（检查里的 `Test ...` 脚本可用，已注明是"所有人"）。
- **E3**：`contract.team_orders_land`：每条整队命令前，同脚本里要有 `UNIT_SET_TEAM`/`CREATE…ON_TEAM` 入同一个队，或这个队是地图自带的队、或地图上放了成员；`TEAM_STOP` 只要求关里别的脚本给这个队下过入队。sim：`active` 队集合，对没人加入的队下整队命令记 `lost_orders`、不执行，日志里一条 `无效命令`。
- **E2**：sim 的"打 X"改成记最后一个打它的对象（`Body.last_by`），条件＝那个对象还在名字缓存里且主人是这个玩家；剧本里的"打/摧毁"仍按玩家算（没有对象）。还没上测试台核对技能伤害的来源对象。**E4**：`UNIT_HEALTH` 先向下取整再比。测试：`tests/test_engine_rules.py`。

## 总控 11-04 补的：K4 提交后先做引擎线查出的 4 处对不上，再做 K3、K7（详情 `work/re/ra3-script-reference.md` 第 1 节）；额度可能 04:10 前用完，所以每做完一小步就提交，并更新本文

- **E1**：`devices/carrier.py:118`（A7 自由号机关）用"按种类数区内单位"，引擎会把所有玩家的都算进去（测试台 probe count 已核）。改成"玩家在区里没有单位"取反，或按模板逐个比；`contract.py` 加一条产物规则：正式脚本（非 `Test`）不许用"按种类数区内单位"这类条件。
- **E2**：条件"打 X"（`plan.py:382`、`sim.py:604`）引擎只看最后一个打它的单位，那个单位一死或被删，条件变假。`sim.py` 改成记录"最后一个打它的单位"；策划稿别指望靠自爆单位或技能伤害触发"打 X"。还没上测试台核对。
- **E3**：只有一个成员、还没激活的队，下整队命令什么都不会发生，只有入队命令会先激活它。所以 K6 的"下令前先给每个名字发 UNIT_SET_TEAM"必须保留。`contract` 的 G6 要加一条：每条整队命令前面必须有入队，或者该队在地图上本来就放了成员；`ctx.order('stop')` 前面要保证已下过别的命令；`sim.py` 里对没激活的队下命令也应无效。
- **E4**：血量百分比向下取整，`sim.py` 判断血量先取整再比。

## K4 资源：做完，等验证结果提交（I6、I9 已标修了待验）

- **原版量出来的关系**（`work/retailref` 缓存，40 张图）：矿场朝向正前方 180 处是它采的矿（171 座里 138 座正好 (180,0)，朝向都是 45+k·90 度）；成对时第二块在第一块侧面约 150；矿单个 153 处、成对 75 处、三个以上只有 10 处；油井 96% 离任何建造厂 ≥ 400（第 5 百分位 497，中位 1687）；基地 1000 以内有一组矿。
- **出口**：新文件 `experimental/cnv/resources.py`（只依赖 `model`）：`Field(name, x, y, facing, twin, base, owner, build)`、`sites`（发布 `<name> refinery` 矿场点，带 `Site.facing`）、`objects`（出矿和油井）、`bases`。`model.Site` 加了 `facing` 和 `cast` 两个字段（`cast` 给 K3 用，还没用上）。`Mission.put`：把矿厂放在有朝向的矿场点上时，矿厂自动朝着矿。
- **迁移**：九张图里的 aso、baikonur、festival、niagara、panama、sapporo、siberia 七张有矿，全迁到 `FIELDS` / `DERRICKS`（himeji、island 没矿）。迁移脚本是一次性的，不进仓库。节日图（festival）的北高原油井挪到了 (1500,3900)（原来在敌营里，会触发新规则）；A4 的北高原油井挪到西岭 (1120,3860)，南坡脚的 (2120,1660) 没动。A4 敌方矿厂原来按 north base 偏移摆，现在写 `在: north refinery`（plans/a4.md 和 missions/a4_before.md 两处）。
- **产物规则**（`contract.py`，在 `contract()` 里每次构建都跑）：`ore_faces_refinery`（每座矿厂/矿场点正前方 180±40 有矿，矿厂没朝向也报）、`ore_in_groups`（一块矿必须是某矿场点生成的；300 内最多 2 块）、`oil_off_the_camps`（油井离敌方基地和敌方物件 ≥ 400）、`base_has_ore`（基地 1000 内有矿）、`map_design`（`platmap.lint` + `platprops.lint` + `ore_lint`，按地图模块缓存；`build.py --preview` 也改成调它，同一份）。87 个构建产物规则零问题。
- **守卫**：`tests/test_architecture.py::test_g12_ore_and_oil_come_from_relations`（任何地图文件手写 `'OreNode'`、`'OilDerrick'` 或 `'<x> refinery': Site(` 就失败，白名单 `G12_LEFT=()` 固定为空；六个变异：手摆矿、三块矿、敌营里的油井、矿厂背对矿、矿厂离矿太远走 map_design、矿厂没朝向）。
- **验证**：见下面的提交信息；指纹 p4_k4 对 p3_k6 是 Sonnet 子 Agent 跑的，结果在汇报里。**没做**：`cnv_preview` 看图（A4 `--preview` 的 LINT 是 ok）、独立验收。
- **要告诉策划线**：`docs/story/plans/a4.md` 里"北高原上有矿和油井，拆干净了就是你的"这句通报现在不准（油井不在北高原了）；电视塔还在（I9 说"电视塔删掉"，是策划线的决定，没动）。

## K3 施法点（I3）：做完（第十三个会话，11-04 04:30～05:00）

- **后巷口放不下的原因**（量出来的）：`lane foot` 原在 (1200, 2540)，正好是后巷坡道的起点（坡从 y=2540 开始升）。以点为中心的 104 见方起伏 17、120 见方起伏 20；另外五个点（inside 1/2/3、north mouth）周围是平地（起伏 0）。测试台 11-03：五个放得出，只有这一个放不出。**所以放置规则里"平地"这一条是真的：不能放在斜坡起点。** 量出的东西不能解释到"多平才行"（`lane foot` 在 40 见方内起伏 7，没超过建筑的 8 也放不出），所以施法圈取整圈（2×半径见方）起伏 ≤ 8，比建筑规则严。
- **东街口**（`east mouth`）：街（3500～3620）宽 120，施法圈如果取 60 会压到运河岸（起伏 13），所以圈取 52（= 32+20，不另加余量），3575 刚好放得下，位置没动。测试台 `placem` 在 x=3565 时三个口子（北坡口、三号广场、东街口）全 PASS（11-04 04:51，`work/testbench/runs/CampA4Placem_mcp_1104_045116`）；最终位置 3575 比测的偏东 10，没再测。**x 不能再往西挪 5 以上**：`tests/test_graybox.py::test_old_a4_can_be_pushed_through_every_stage` 会因为旧 A4 走查在"布防"阶段多撞上一批敌人而失败（量过：偏 5 就败，偏 2.5 过）。
- **后巷口 V1：已解决**（第十六个会话 11-04 重跑）。原先 FAIL 不是关卡的问题：测试台在高台边上把工兵点偏了 26 像素（查清过程见 `docs/engine/terrain.md` 第 4 节），引擎线 4fe6cb0 按地形修正了世界点击；修正后 `a4 place` V1/V2/V3 全 PASS（`work/testbench/runs/CampA4Place_mcp_1104_152808`）。上面"信息框挡着""落点在坡的投影内"这些猜测都不成立，不用再试。
- **做了什么**：①`platmap.CAST_CLEAR=52`（= 技能的 `ForbiddenObjectRange` 32 + 冰核 `SEED_SIZE` 20）、`platmap.cast_lint`：每个 `Site.cast>0` 的点，圆内全可走、整圈 ≤ FLAT、圆内没有地图物件（墙段按矩形量），并进 `platmap.lint`（所以 `contract.map_design` 每次构建都跑）；②`platprops.clearance` 把施法圈 +20 算进保持空旷的圈；③`Mission.waypoint(..., cast=True)` 登记到 `Mission.spells`，`devices/horn.py` 的冰标记都传 `cast=True`；④产物规则 `contract.cast_points_clear`：登记的点必须是 cast 点、标记就在点上、任务自己的物件不进圈；⑤`maps/sapporo.py`：`lane foot` 挪到 (1200, 2470)（坡脚往南 70，平地），inside 1/2/3、north mouth、east mouth 标 `cast=CAST_CLEAR`；⑥守卫 `tests/test_architecture.py::test_g13_a_cast_point_is_level_open_ground`（含 6 个变异：标在非施法点、物件压进圈、旧位置在坡上、圆压到水、墙进圈、干净点不报；`CAST_CLEAR == 技能禁物范围 + 冰核` 这条数字守住；设备里的冰标记不传 cast 就失败）。节日图 J4 的冰是地图自带的、不是玩家放的，没有施法点。
- **后巷出兵点跟着南移了 70**（`出: lane foot` 偏移 [0,160]，现在出在 y=2630，仍在坡上）；冰雕偏移不变。策划线复核时看一眼。
- 检查"一律走玩家点击"：已由 `contract.observes`（G11）保证，只观测的检查才能当验收；`place`/`placem` 用传送把工兵放到点边上，再由测试台点技能按钮和落点。

## 第十四个会话（11-04）：E7 做完（总控令 ADR 0017 后改顺序：E7 → 等引擎线查后巷 V1 → K7 等外壳线的地图页）

- **配乐**：任何 `音乐 <提示词>` 都会把战况音乐挂起且不自己恢复（引擎线第 5 轮测过）。`plan.Compiler.resume_music()` 在编译末尾，给"战况音乐开了之后的段（`Phase n` 开场脚本）和条件里带 `段 X` 旗的规则"里的每个非收尾 cue 后面紧跟再发一次 `PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM`（cue 在前、开在后，同一动作列表：和 `music_dyn` 里测过能响的顺序一样）。A4 现在：`Phase 4`（布防）、`Phase 5`（最后一程）各补一次；`Phase 3` 本来就是 cue 后开；`Rule 5`（伏击，只等号角、不挂段）在开之前，不补。判定函数 `contract.unresumed_cues` 编译器和产物规则共用。**没在游戏里听过**布防、最后一程里战况音乐是否真的接得上（要录音：`musicdyncue` 一类的构建加一个"开之后再发 cue + 开"的对照）。
- **胜负 cue 删了**：`plan.py` 的 `胜利`、`失败` 不再自己放 `S_EndMissionWin/Lose`，库脚本 `Lib_End_Mission` 设旗标时自己放（E7-7）。`失败` 的字幕从停 10 秒改成 `ENDING_LIBRARY_AT['Mission Lost']`（3 秒，库脚本 3 秒后 `DEFEAT()`）。手写关 a8、j4 的结局字幕同样改成引用这个常量（赢 5 秒、输 3 秒）。**没测**：①删掉我们那一发后游戏里胜负音乐是否照样响（库脚本发的是同一个事件名，理论上一样）；②旗标设下后 `HIDE_UI` 会不会把字幕框一起收掉（会的话 3 秒也看不到）。
- **产物规则**（并进 `contract()`，每次构建都查）：`music_resumes`（战况音乐开了之后的 cue 后面没再开＝错；结局脚本自己放结束音乐＝错）、`ending_line_fits`（设 `Mission Won/Lost` 的脚本里的字幕：停留不超过库脚本的 5/3 秒，字数按每秒 9 个汉字 / 17 个英文字母读得完）。守卫 `tests/test_architecture.py::test_ge7_...`（全部 92 个构建过；三个变异：A4 拿掉最后一次再开、结局自己放音乐、10 秒字幕；`plan.py` 里不得再有 `self.cue('胜利')` / `self.cue('失败')`）。测试 `tests/test_plans.py` 三条：结局不放 cue、cue 后补开（含段旗规则、不重复）、结局字幕。
- **`技能` 不用改**：第 5 轮实测脚本按按钮不看冷却（冷却只拦玩家点），所以 A4 `derrick` 等"发了就放"的写法是对的；反过来脚本连发拦不住，想要冷却得自己计时。其余 E7 条目（CREATE 朝向恒 0、AI 单玩家、建造中不数）核对过，我们的用法没有冲突。
- **验证**：`pytest -q tests` 428 passed 1 skipped；指纹 `p4_e7` 对 `p4_k3`：a4、shell、shell_intl 各只变 `camp_cnv01_probe.map` 一个文件（脚本里多两次再开、少两个结局 cue、失败字幕 3 秒），字符串、配音、模型没变。没做：游戏里听、`cnv_check` 整关走查（改的只是脚本动作，sim 不模拟音乐）。

## 第十五个会话（11-04）：平地检查按游戏规则、A7 当摩擦探针

- **平地检查**：`platmap.level_enough(e, x, y, side)` = `terrain_rules.flat_enough`（高差 3 个世界单位 = 我们的 4.8）。`Site.build` 和 `Site.cast` 的 lint 现在用它（报的数换成世界单位）；`platmap.FLAT = 8` 只留给地图自己摆的物件（矿、科技建筑、桥端）。现有所有地图的 build/cast 点高差都是 0，所以**构建一点没变**（只是 lint 规则，没跑指纹）。测试 `tests/test_terrain_rules.py::test_site_lint_holds_build_and_cast_squares_to_the_game_rule`（6 ours 的起伏过旧规则、不过新规则）。`horn.py` 注释、`issues.md` I3 已改：V1 的原因写成"工兵选不中"，V1 过之前 I3 不标完成。K7 没动。
- **探针选了 A7，不选 A5**：A5 要水位升降（panama 只有一级闸，类 ⑥），平台缺的更多；A7 的自由号设备、尼亚加拉图、东岸 AI 都现成。**用了 1 个会话。**
- **做了什么（按题卡改 A7 的第 3 段）**：`devices/carrier.py` 加 `迫降: <地点>`、`迫降血量`（默认 10）、事件 `迫降`/`落地`，以及"不跳回上次的落点"（计数器 `Jump_Last`，选点脚本多一条不等于）；`plans/a7.md` 第 3 段"它要飞走"换成"它困住了"（去掉飞走倒计时和航线；断电后它原地不动，打到一成血锁住、朝 `base edge` 迫降，`胜利: [自由号.落地, 进入 base edge]`）；`checks/a7.py` 的 `power`（不再飞走）、`win`（开局 1% 血，迫降，基地边有我方兵）改了。sim：断电后把它打到 5%、派兵去基地边，1:35 赢（`sim.py a7 --script ...`，实际命令在会话里，约 70 秒是它飞到基地边）；`plan_show` 接口检查 ok；`pytest` 相关文件过（见下）。**没在测试台跑过**（`power`/`win`/`pick` 要重跑）。
- **哪些步骤还得改平台代码（摩擦清单）**：
  1. "挑最空的一段跳"：引擎的"区域里有某类单位"对所有玩家数（E1），数不出"玩家的兵少于几个"，所以只能"按顺序挑第一个空的"。要按段比多少得先有"只数玩家的"的计数办法（或逐单位类型计）。
  2. 闸刀推回去：电站只有"毁/占"两个不可逆状态，没有"拉闸/推回"开关。要加一类"占着闸房的一方说了算"的开关机关。
  3. 一成血后"朝全场最空的地方滑"：现在固定落到 `base edge`；要选最空点同样卡在第 1 条。
  4. 登舰不分工程师：现在是"迫降后我方任意单位在落点"。要"工程师进舰"得有进入单位的条件。
  5. 保底援军（工程师援军、防空援军）、北岸哨所翻脸的补救：策划案里还没写，词表里有 `保底`/`给`，没试。
  6. sim 不认 `objectInitialHealth`，所以 `win` 检查只能上测试台；sim 里要靠 `血量 carrier 5` 的脚本事件。`plan_sim` 的 MCP 每次回 7000 多字符的"待对齐"清单，浪费上下文；以后用命令行 `sim.py` 再 grep。
  7. 题卡"好玩假设"A7 没有（策划线的盘点里就缺）；叛军轰炸机"越来越稀"等"断电"段的戏没做。
- **提交前 pytest**：全量跑过一次（改 A7 之前）434 passed 1 failed；失败的 `test_g4_sys_path_ratchet`（130 个文件改 sys.path，天花板 129）**在 HEAD 上就是红的**，不是这轮造成的（`git grep` HEAD 就是 130），多半是引擎线 88ce082 新增的文件，由总控或引擎线定是抬高天花板还是去掉一个。改完 A7 之后又跑了 test_architecture、test_plans、test_sim、test_terrain_rules、test_maps、test_check_model，除上面这条外全过。

### 第十五个会话收尾（11-04，上下文 22.7 万）：下一步

- **A4 地图页提议 1 已做**（86a5171）：`harbour refinery` 挪到 (2801, 1814)、朝向 315°；lint ok、相关测试过；没上测试台。
- **I3 / V1**：引擎线 9086bc0 查清：关卡没问题，是测试台在高台边上点偏了。等引擎线改好测试台工具，再重跑 `a4 place`（V1→V2→V3）；V1 过了就把 `docs/issues.md` I3 标完成（并把 `docs/engine/terrain.md` 第 4 节"后巷口 V1"和 K3 一节里"没查清"的话改掉）。
- **A7（摩擦探针）做到哪了**：编出来、`plan_show` 接口检查 ok、sim 能赢（见上一节）。**下一步**：测试台重跑 `cnv_check a7 power`、`win`、`pick`（`jumps` 也跑一遍，选点脚本多了"不等于上次"）；`win` 只能上测试台（sim 不认开局血量）。测试台共享，工具会自己排队。过了再往下补：保底援军、断电段的戏；上一节摩擦清单 1～4 条是平台缺的，不在这里补。
- **K7**：仍等外壳线的地形编辑器，在地图页上和用户定；现在别排。
- **没提交的别线改动**：`docs/engine/terrain.md`、`experimental/mappage/`、`tests/test_mappage_terrain.py` 不是我的。`test_g4_sys_path_ratchet` 在 HEAD 就红（130 > 129），要总控或引擎线定。
- **提醒**：`plan_sim` 的 MCP 每次回 7000 多字符，改用 `python -I -X utf8 experimental/cnv/sim.py a7 --script "..." > work/logs/x.log` 再 grep；改文件用 Edit（Bash 钩子拦带反斜杠的内联写文件）。

## 第十六个会话（11-04）：I3 收尾、A7 测试台全过、保底援军

- **I3 / V1 收尾**：引擎线 4fe6cb0 修了测试台后，我重跑 `a4 place`：V1/V2/V3 全 PASS（`work/testbench/runs/CampA4Place_mcp_1104_152808`）。`docs/issues.md` I3 的话改成"V1 原先过不了是测试台点偏，已修好；测试台验证完成，只差独立验收者在 CampShell 上验"（状态仍写`修了待验`：`验过`要独立验收者）。`docs/engine/terrain.md` 第 4 节引擎线已经改过，K3 一节的"V1 还没放出来"改成"已解决"。
- **A7 测试台**（`cnv_check a7 …`）：`power` PASS、`pick` PASS、`jumps` PASS、`win` PASS（改了检查，见下）、新增 `relief` PASS。
  - `win` 原先 FAIL 有两个检查自己的问题，不是机关坏：①`LAND_BY=60` 比飞行时间短（货舰 s66 才进基地边的检测区，s72 左右胜利），改成 110；②**货舰迫降飞近时会开火，把基地边那辆测试坦克打掉了**（读数 1→0 在 s63），"进入 base edge"就不成立；检查改成放 3 辆（剩 2 辆，胜利）。`win` 现在带两个诊断读数（货舰进 150 区、我方坦克在基地边），counters 只有 4 行（`counters.MAX_LINES`），所以它只剩 `base edge` 一个地点。**策划线要知道**：迫降段货舰会打基地边的兵，"登舰"得有扛得住的人，目前题卡没写。
  - **保底**（`docs/story/plans/a7.md` 规则）：用现成的 `兵少于` + `给` 写了两条，都没动平台代码：工程师全死了，第 2 段 + 1:00 在 `start` 送 2 个；第 3 段 + 0:30，标枪兵和多功能步兵车少于 3，在 `start` 送 2 辆多功能步兵车。`relief` 检查：开场杀光工程师和哨所步兵，测试台上 s55 冒出 2 个（步兵数 0→2），通报也出了。防空那条只编译过、没在测试台跑。
- **摩擦清单补充**（接上一节 1～7）：8. 按**模板**数区域里的单位，看不到脚本 `给` 出来的零售单位（`PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA` 一直是 0，按兵种 `INFANTRY` 数就看得到），`relief` 因此按兵种数；以后"检查要数给出来的单位"一律先用兵种。9. 货舰第一次跃迁到达时步兵数会多出来（s38 +1，s65 +4，是它自己带的兵，不是我们的），数兵种的检查要避开。10. `兵少于` 够用做保底，**第 5 条（保底援军）不再是平台缺口**，只剩北岸哨所翻脸的补救没写。
- **没做**：断电段的戏（叛军轰炸机越来越稀）和题卡"好玩假设"仍是策划线的活，没排；A7 以外还没动。
- **验证**：A7 五个检查 + `a4 place` 都是测试台跑的；`pytest -q tests`见提交信息。

## 第十七个会话（11-04）：A7 草稿收尾、"不可通行"位审计、摩擦按类修

总控令：A7 按草稿标准收尾；检查地图生成器写"不可通行"位有没有漏；余力挑下一关报缺口。
- **A7 草稿标准**：能打通（测试台 power/pick/jumps/win/relief 全 PASS，上一节）；地图看得懂（`cnv_preview a7` LINT ok，范围偏离只有隘口/墙段/空地块，是 niagara 图本来的样子）；新机关能用；`plan_show a7` 接口检查 ok；K 规则在 `contract()` 里，全量 pytest 过（见提交信息）；**题卡的好玩假设补上了**（`docs/design/cards/all.md` A7 一节，含成立/不成立的读数）。顺手改了 a7 策划案和题卡里过时的话：自由号落点是"玩家一个单位也没有的第一处"（E1 以后），不是"最空"；去掉了不起作用的 `空虚: 3`。
- **不可通行位审计（总控第 2 条）**：写这个位的只有 `platmap.apply`（所有平台地图）和 `newmap.paint_terrain`（island），都按"干地坡度 > STEEP"置位。把 aso/baikonur/festival/himeji/island/niagara/panama/sapporo/siberia 九张图真的编进容器图再读回第 0 个位图、和 `terrain_rules.impassable_bits` 比：**缺位 0、多位 0**（`probe_ground` 是故意缺/多的对照，不算）。所以没有"陡坡没标位"的漏，**没改生成器**。唯一的缺口是没有守卫：以前测试只比纯函数，没读回写出来的图。已加 `tests/test_maps.py::test_every_platform_map_is_written_with_the_impassable_bit_the_rule_gives`（编图读回，约 50 秒，没游戏就跳过）和它的变异检验 `test_field0_check_names_a_cliff_without_its_bit`。后面谁改了写位的代码或者在 `apply` 之后再动高度，这条会红。注意：陡但在水面下的格子不置位（交给水域），这是对的。
- **摩擦按类修**：①"按模板数看不到脚本给出来的单位"（摩擦 8）：**没修，原因没查清**。我试着写成产物规则（脚本不许按模板数本关脚本给同一玩家创建的模板），全量 pytest 马上抓到两处现成检查违反：`a4_before harbour`（数的是地图摆的坦克，别处给过同模板）和 `a7 revenge`（`Test Gate Guardians` 按模板数脚本刷出的敌方守护者，**测试台 2026-10-26 pincer 读到 5，是看得到的**）。所以"按模板数一律看不到脚本创建的单位"不成立，规则会误伤，已整个撤掉。relief 那次读数不动的真正原因还不知道（疑点：`给` 出的单位和被数的模板名是否一致、给的是玩家阵营还是别的队、有没有走和 CREATE_NAMED 同一条路）。**列给引擎线**：用 `relief` 检查换成按模板数，打印被数的模板和 `给` 的模板，对一对。在原因查清前，检查里数给出来的单位继续按兵种（`relief` 已是）。②"货舰落地时开火"：不是平台缺口，是关卡事实——迫降段货舰会打基地边的兵，登舰得有扛得住的人；已写进 A7 题卡现状栏，检查放 3 辆坦克。要不要让落地货舰停火是策划决定，列给总控。
- **下一关候选（只列缺口，没动手）**：见汇报。

## 第十八个会话（11-04）：A8 纸面 + 最小可编（总控令：下一关做 A8，落地货舰开火记进试玩清单不改）

- **做了什么**：①`docs/story/plans/a8.md` 重写（去掉"击落"）：自由号归玩家，三座平台（原版电厂 + 每座 2 座浪涌炮塔 + 2 个标枪兵），12 分钟预热倒计时，三段、护航机一股；`plan_show a8` 接口检查 ok，`build.py a8 --show` contract ok。②**通用设备 `节律`**（`devices/rhythm.py`，类 ⑦）：一批单位按节拍在两种状态间切换，每组自己的相位；状态 = 单位自己的两个升级（`on`/`off`），设备给一个、拿掉另一个（`NAMED_RECEIVE_UPGRADE`/`REMOVE_UPGRADE`）。设备不认识状态是什么：S2 冰甲、A9 球、S8 喷口、A3 时停区只要各自的单位公开 `on/off` 两个升级（升级里装 INVULNERABLE / DAMAGE_MULT / 区域效果的属性修改器）就能用，策划案写 `{类型: 节律, 单位: <名册名>, 周期, 开, 组: [{角色, 相位}]}`。事件 `开 <角色>`/`关 <角色>`/`开始`，动作 `停`/`继续`。③单位 `units/platform.py` `tide_gun`：原版 SovietBaseDefenseGround（哨戒炮，单武器）去掉依赖，加两个 AttributeModifierUpgrade（RANGE x2 / x0.6，原版属性修改器里有 RANGE 类型：Unit_Heroic、Garrisoned 用过）。④名册加 `浪涌炮塔`、`自由号空天航母`（玩家的，复用 `units/liberty.py`，45 秒冷却，甲板造守护者）。⑤`island.TEAMS` 加了敌方队 `s1`（和 niagara 一样，是容器图自带的队，值没变，只是登记成"地图公开"）。⑥旧手写粗模改名：`missions/a8_rough.py`、`checks/a8_rough.py`，构建名 `a8_rough` / `a8_rough_control`（模组名 CampA8R / CampA8RC），`tests/test_cnv_parts.py` 跟着改；`a8` 现在是计划编的。⑦检查 `a8 beat`（`checks/a8.py`）：三组炮按 25/60 秒、相隔 20 秒轮流"浪高"，读脚本旗，模拟器版 PASS（`simchecks.py` 登记，因预热倒计时 12 分钟，推演到头是输，读数在这之前）。⑧sim 认识了 `NAMED_RECEIVE/REMOVE_UPGRADE`（只记在单位上，不模拟效果）。测试 `tests/test_rhythm.py`。
- **没做、要测试台答的（拆成清单）**：
  1. **升级撤销后修正还在不在**（`AttributeModifierUpgrade` 的修正会不会随 `NAMED_REMOVE_UPGRADE` 去掉）；设备现在是"拿掉另一个 + 给这个"，若修正不撤销，两个倍率会叠（x2 再 x0.6），要改成同 Category 互相替换或改机制。**写 `a8 swell` 检查**：一个标靶单位站在平台炮 150～300 之间，读炮在"高"和"低"时有没有开火（计数标靶掉血）。
  2. **RANGE 改不改索敌距离**（只改武器射程、炮塔不主动打更远的目标就白改）。
  3. 12 分钟预热、三座平台血量、标枪兵 `守:` 的写法、护航机 2 架够不够；周期 60/开 25/倍率 2.0/0.6 都是占位。
  4. 玩家要的"提示高低"：炮塔高低现在**玩家看不出来**（题卡"看懂"层）。要加看得见的东西：模型换（单位线）、或雷达提示/通报"北平台浪高了"（`节律` 的 `开 <角色>` 事件可以直接挂通报，策划案还没写，等 swell 测过再加）。
  5. 自由号载兵跳平台、"跳上去的兵要接走"是玩家操作，计划里没有脚本；草稿靠玩家自己做。
  6. 地图：island 东端当占位，真公海平台要一张海图（地图线）；黑匣子小目标没做。
  7. 外观：平台=原版电厂，炮塔=原版哨戒炮；换模型归单位线。
- **各线接口**：单位线接炮塔外观：`units/platform.py` 的 `tide_gun(id, high, low, health)`，`roster` 名 `浪涌炮塔`；高/低的视觉差（升级触发的 SubObjects/ModelCondition）由它定。落地货舰开火：已记题卡，不改（总控令）。

### 第十八个会话续（11-04）：swell 验过、"高"加了 VISION

- 总控转引擎线结论（`docs/engine/upgrades.md`）：撤升级时修正跟着撤，节律设备"先撤再给"不叠，设备不用改；RANGE 只改武器射程、索敌看视野（哨戒炮视野 300）。所以 `units/platform.py` `tide_gun` 的"高"修正里加了 `VISION` x2（参数 `vision=2.0`，`None` 去掉；引擎线 `checks/engine_range.py` 的对照炮改成 `vision=None`，视野版用 `vision=2.0`，不再靠字符串替换）。
- **`a8 swell` 写好并上测试台，连跑两次 PASS**（`checks/a8.py`，`work/testbench/runs/CampA8Swell_mcp_1104_171857`、`…_172050`）：中间平台第一门炮西边 250、450 处各一个中立工程师；s15 把 250 的转给玩家（浪低：射程 180，看得到打不着）→ 到 s28 没受伤；s33 把 450 的转给玩家（浪高：射程 600、视野 600）→ s34 受伤，250 的也在浪高开始后受伤。读数 `s1-s25: 0 0 0 | s28: 0 0 1 | s31: 1 0 1 | s34-s52: 1 1 1`。
- 注意：同一个原版文件在一个 mod 里拷两份会重复定义 Define 让构建停（`platform.py` 文档串已写）；a8 里只有一份，没事。
- 还没做：整关一局实打（自由号载兵跳平台、12 分钟够不够）；炮塔高低玩家看不出来的提示；真公海图；下一轮总控说做"一队一起走"（引擎线测过 SPEED 33% 升级让快慢单位同时到，`docs/engine/pathing.md` 第 5 节）。

### 第十八个会话续二（11-04）："一队一起走"进编译器（`齐步`）

- **写法**：策划案 `进攻` 条目加 `齐步: 是`（`docs/story/plans/README.md` 进攻一行）。出口只有一个：`plan.Compiler.pace_plan` → `units/pace.py`。编译器按本波各兵种速度（`simunits.stats`）找最慢者，比它快的每种造一个升级副本（`CNV_Pace<百分比>_<原模板>`，原版文件拷一份加 `AttributeModifierUpgrade`，SPEED 修正 = 最慢/自己，向上取整），出生后马上给升级；每个被压速的单位一个脚本：它进了 `打`/`守` 地点的圈（半径取地点自己的、至少 250 `PACE_ARRIVE`）就把本批所有压速升级撤掉。空军、建筑不算；全队同速不加东西；`出动` 暂不支持（摆的是原版模板，写了会报错）。
- **产物规则**：`contract.pace_released`（接在 `contract()` 里）：每个 `NAMED_RECEIVE_UPGRADE Upgrade_CNV_Pace…` 必须有一个以 `NAMED_INSIDE_AREA` 为条件的脚本撤掉同一对（升级、单位）。变异检验在 `tests/test_pace.py`（删掉撤销脚本、或把条件换成别的，规则报出来）。没单独加 `test_architecture` 守卫（规则对每一关都在 `contract()` 里跑，`parts.contract(m) == []` 的测试已经全覆盖）。
- **模拟器**：`sim.py` 认 SPEED 修正（`simunits.speed_scale` 读单位自己的 XML）：给升级速度变、撤掉恢复；别的升级效果仍不模拟。`tests/test_pace.py` 里模拟器验过：不压速坦克先到，压速后两个同时进圈，进圈后速度恢复。
- **用在 S5 `反扑`**（`docs/story/plans/s5.md`，守护者 80 + 维和步兵 50 → 坦克压到 63%）。选它是因为没有按名字读它的检查，也不像 A7 夹击那样踩着航母预警的时间。模拟器里整关跑过：第一批 6 个单位 35.5 秒出生，都进了圈、升级撤净、速度回 80。
- **测试台验过了**（重置后）：`cnv_check s5 pace`（读数两行：`齐步` 1 坦克进圈、10 步兵进圈、100 坦克独自在前；`限速` 1 = 敌方有单位带着限速升级，用 `PLAYER_HAS_NUM_UNITS_WITH_UPGRADE(玩家, 1, 升级)` 读）。压速：限速 s35–s55 为 1、s57 撤净；坦克 s59、步兵 s61 进圈。对照（临时写 `齐步: 否`，已改回）：坦克 s51、步兵 s61，差 10 秒。所以：脚本创建的单位立刻收得到升级；同时到（差 ≤ 4 秒）；到圈就撤。没测：交火时是否仍同时到、撤后速度本身（读不到，信引擎线 upgrades.md）。顺手修了：`齐步` 只认 `是`/真，写 `否` 不再被当成开。
- **没有 A4/A8 要用齐步的进攻**：A8 只有护航机（空军不算），A4 的进攻波来自 horn 机关（没有混编地面波）。别的关里混编的有 A5（V4+铁锤、钻地车+动员兵）、J3、J5、S6，各自按设计要不要齐步由那几关的返工时定，我没动。
- **绕路上限 lint 做了**（总控令，引擎线 a2f4abf 的 1 400）：`simstatic.long_detours`，报告里多"绕路"一行，`tests/test_detours.py` 对每一关守卫（名单 `LEFT` 只删不加，变异检验在里面）。规则只查同一脚本里造兵（或地图里摆好的命名单位）后的整队 `MOVE_TEAM_TO`/`ATTACK_MOVE_TEAM_TO`，路长 > 1 400 且 > 直线 1.5 倍；其余下令方式不查。**现状只有一处：A4 鬼王运输车（海 → 岸）绕 2 420 对直线 630**（模拟器的两栖格；真实游戏里船能不能到岸没读过）。已列名单。**列给 A4 的线**：开 A4 时测一次 boats 到岸；若到不了就分段路点。S2 有两处长直路（直线 3 346、3 857，绕比 1.3～1.4）不在规则内，但引擎线没量过长直路，想放心也要分段。
- 已知限制：中途被拦住、进不了圈的兵一直慢着；SPEED 修正只压平地速度，坡度、地形造成的减速不在内（引擎线原结论：大致同速）。
- 验证：`pytest tests/test_architecture.py tests/test_docs.py tests/test_pace.py tests/test_plans.py tests/test_sim.py tests/test_rhythm.py` 99 passed。完整 pytest 没跑（6 分半，没改别的模块）。
- 接下来按总控令：A8 按草稿标准做。

### 第十九个会话（11-04）：A8 草稿收尾（总控令：A8 按草稿标准做完）

- **草稿标准对照**：能打通——赢、到点输的接线测试台验过：`a8 win`（三座平台由脚本相隔 5 秒摧毁，约 s18 结束、没有输的旗）、`a8 lose`（12 分钟预热倒计时压成 40 秒，约 s38 结束），再加 `swell`、`beat`、`plan_sim a8`（能赢能输、浪高通报按时出）。地图看得懂——island 东端占位，真公海图归地图线。新单位机关能用——`swell` 验过。K 规则——`contract ok`，`pytest` 架构、文档、计划、模拟器、节律、绕路、cnv_parts 共 131 过。题卡好玩假设在 `cards/all.md` A8，现状栏已更新。
- **新加**：三条规则，每座平台浪第一次升起时通报一句（`当: 浪.开 gun north` 等，规则只做一次，是"炮会忽远忽近"的教学，之后靠玩家自己看）；段 2、3 的通报改成按真实次序（第一座断电、第二座没了）。
- **检查的读法（摩擦）**：任务结束后计数器读不到（`counters gone`），所以"输了"旗没法在结束后读；`win`/`lose` 靠"结束的时间点"区分是谁结束的（win ~s18，lose ~s38，窗口里计数器仍为 0）。**平台代码缺口**：想直接读"赢/输"需要测试台在结束帧留一次读数或读结局类型，列给引擎线；现在这样够用。
- **要玩家试的（攒进试玩清单）**：一局实打——自由号载兵跳平台、12 分钟够不够、平台血量（原版电厂）、标枪兵专打自由号会不会太狠、护航机 2 架、浪的周期 60/开 25/倍率 2.0、0.6 是占位。炮塔高低玩家看不出来（只有首次通报），真提示等单位线换模型。
- **摩擦探针汇总（A8）**：①节律设备、齐步、绕路 lint 都用上了，没改平台代码；②只有上一条的"结束帧读数"；③`plan_show`/`plan_sim` 的参数名叫 `level` 其实是关卡名（`plan_show` 的 `name` 是空的）——容易用错，列给总控看要不要改。
- 下一关由总控定；盟军 9 关里 A8 现在够草稿标准。

## 第十三个会话收尾（11-04 05:40，上下文 23 万）：K3 提交 41e0c73，K7、E7 没动

**下一步按顺序**：
1. **后巷 V1 放不出冰墙**：先看上面 K3 一节最后一条。测试台空了就跑 `place`（`PLACE_AT` 已推到 20 秒，没测）。I3 在 issues.md 里仍是"修了待验"但写明 V1 未过，V1 过了才算完。
2. **K7（I8）**：设计见下面"K7 挡路"一节，没动手。现状量数（`platmap.heights` 算的，A4 当前）：陆地里高度 ≥455（第二层）占 39.4%，坡度 >9 的占陆地 15.0%（原版城市图 1.4～3.4%，目标 ≤4%）。垫高的块：北街区（含后巷）、南街区、北坡口两侧的 ward、西岭、西南山、北南高原、神社丘（`sapporo.py` 的 `SHAPES`）。要改的是前四个（街区和 ward），南北高原留。改完后后巷的两个坡口要重新定位，`lane foot`/`lane end` 以及 horn 的后巷出兵点、`Gap`、`tests/test_sapporo.py`、graybox 走查（见下条坑）都要跟着看。产物规则要一条：非悬崖的大片坡地（坡度 >1.5 且面积 ≥ 阈值）出现在路上就报，阈值先量原版（`docs/design/teardowns/data/edge_measure.py`）。守卫 G14 + 变异检验，I8 标"修了待验"。
3. ~~**E7**~~ 第十四个会话做完，见上面那节。原记录（`work/re/ra3-script-reference.md` E7-6、E7-4）：①配乐 cue（`PATH_MUSIC_PLAY_EVENT`）会把战况音乐挂起，之后不自己恢复：`plan.py` 里 `战况音乐` 的 PlanError 文字和 `plan.py:521` 一带注释说"没有关的动作"不对，A4 `战况音乐 开`（plans/a4.md:203）之后再有 `音乐`/`胜利` cue 的地方要核对顺序，必要时在 cue 后再发 `战况音乐 开`（要先在 sim/测试台确认再 ENABLE 会不会把刚放的 cue 盖掉；`music_dyn` 里是先 PLAY_EVENT 再 ENABLE）；②`NAMED_USE_COMMANDBUTTON_ABILITY`（`plan.py:630` 的 `技能`）技能用不了（冷却、没就绪）时静默什么也不做：靠它"一定放"的地方（A4 `derrick` 等）要在放之前确认冷却，测试台连发两次看第二次有没有效果。
4. 小心：①跑 pytest 要 6 分半，指纹约 6 分，都交给 Sonnet 子 Agent，别和任何构建同时跑；②`tests/test_graybox.py::test_old_a4_can_be_pushed_through_every_stage` 很脆，动 sapporo 的站点坐标几个单位就会因"布防"阶段多撞到敌人失败（东街口偏 5 就败）；③测试台是共享的：音乐线可能占着游戏，`bench_start` 会拒绝，别杀别人的进程；④Bash 钩子拦"heredoc 里带反斜杠写文件"，改文件用 Edit。

## K3 施法点（原设计，留作参考）

- 现状：冰墙落点是 horn 设备的 `点:` 里写的地点：`lane foot`、`inside 1`、`inside 2`、`north mouth`、`inside 3`、`east mouth`（plans/a4.md:125-135）。设备在 `devices/horn.py:265` 用 `ctx.waypoint(f'ice {wid}', ...)` 发布成标记。玩家点的是 `AssembleStructureSpecialAbilityUpdate` 放"冰核"（`units/icewall.py`，`SEED_SIZE=20`，`ForbiddenObjectRange=32`，`PATHABLE_ONLY`）；脚本放技能完全不检查位置（引擎线 11-04 从代码确认），所以旧检查 PASS 不代表玩家放得下。玩家点击的检查已有：`checks/a4.py` 的 `place`（街口）和 `placem`（口子），走 bench_click/bench_ability。
- 做法（照 K4）：①地图点标 `Site(..., cast=CAST_CLEAR)`（常量 = 32 禁物范围 + 20 冰核 + 余量，约 60），`platprops.clearance`（`experimental/campaign/platprops.py:88`）把 `cast` 也算进保持空旷的圈，布景生成器就不会压上去；②`platmap.lint` 加施法点检查：圆内全是可走格（`walkable`）、起伏不超过 `FLAT`（P36 第 6 条：平地）、圆内没有地图物件（墙段按 `platmap.WALLS`，其他按 `platprops.radius`）；③`contract.py` 加产物规则：任务里所有 `ice ...` 标记必须落在 `cast>0` 的地点上，任务摆的物件（标志、冰雕、建筑）不压施法圈（半径 + 32）；④守卫 G13 + 变异检验；⑤`lane foot` 在坡脚（`Ramp` 起点），大概率不平，lint 会报，到时候改 plans/a4.md 的 `点:`。⑥issues.md I3 标修了待验，依据写产物规则名；"检查必须走玩家点击"那条已由 `contract.observes`（G11）保证：只观测的检查才能当验收。
- 要把冰墙标记点设成 `cast` 的是 sapporo.py 的 SITES 字面量（`lane foot`、`inside k`、`north mouth`、`east mouth`）；festival.py 同名点同样要标。

## K7 挡路（I8）：还没动手，设计

- 准则 P36（`docs/design/principles.md:151`）和 A4 逐块处理表（`docs/design/maps/a4.md:136`）。要做的是生成器默认值：①`platmap` 加"成排房子"生成函数（沿线一栋挨一栋、缝里补宫墙，进地图 `OBJECTS`，算进 `walkable`：现在只算 `WALLS` 里的墙段，房子要加半径）；②产物规则：除声明了"要高处视野"的块外，不许垫高（`Block` 用途加一个"高地"标记，`SHAPES` 里 tier>1 的块必须对应一块高地）；陡面占陆地 ≤ 4%（原版 1.4～3.4%）、陡面边上每公里 ≥ 15 件包边物件（量法 `docs/design/teardowns/data/edge_measure.py`）；③A4 的北侧街区、后巷、南侧街区、北坡口两边要改成不垫高（这是地图改动，会动 `LAYOUT`，要走 `cnv_preview` 看图）；④守卫 G14 + 变异检验；⑤I8 标修了待验。
- 注意：这一类改动最大，改的是 A4 地图本身；预计要一整个会话。先量现状（`map_study a4` 或 `cnv_preview a4` 的 TERRAIN 行），再定做多少。

## 做事顺序

1. 读本文、`docs/adr/0016-one-outlet-per-class.md`、`resources.py`、`contract.py` 里 K4 那一段（照它的写法做 K3、K7）。
2. 先做 K3（小），再做 K7；K1 的"功能句不能晚"和"策划案同源"两条规矩穿插做，每条独立提交。
3. 验证类的活（指纹、pytest、测试台）仍交给 Sonnet 子 Agent，正斜杠绝对路径，用完让它停后台任务；跑指纹时自己别改代码、别同时构建。
4. 小心：本仓库 Bash 钩子会拦"内联写文件里带反斜杠"和 `sed -i` 带反斜杠，改文件用 Edit/Write；工作目录会因 `cd` 漂移，命令开头总是 `cd` 到仓库根；工作区里 README.md、docs/design/ 下有别的线没提交的改动，不要带进提交。
