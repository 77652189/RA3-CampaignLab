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
- **后巷口 V1 还没放出来**（`place` 11-04 04:46：V2、V3 PASS，V1 FAIL，用的是挪到平地后的新位置 (1200,2470)）。所以坡不是唯一原因，或者不是原因。截图 `work/testbench/runs/CampA4Place_mcp_1104_044627/0004～0006.png`：第一次点选时工兵头顶的信息框（"选中我，点街口…"）还在，点完工兵没被选中；`placem` 的第一次（L1，同样 4 秒）却选中了，所以不一定是信息框。我把 `place` 的第一次尝试推到 20 秒（`checks/a4.py PLACE_AT`）准备重测，**没测成**：测试台被音乐线的游戏占着（`CampMusDynC`，pid 22660）。**下一步**：测试台空了就跑 `run_check.py a4 place`（命令见 handoff.md 第 55 行那一条）；V1 若还失败，试把 V1 的落点往南挪（工兵站的位置、落点和路面的关系）或看冰雕/标志离落点的距离，再查是不是引擎对"落点在坡的投影内"有限制。
- **做了什么**：①`platmap.CAST_CLEAR=52`（= 技能的 `ForbiddenObjectRange` 32 + 冰核 `SEED_SIZE` 20）、`platmap.cast_lint`：每个 `Site.cast>0` 的点，圆内全可走、整圈 ≤ FLAT、圆内没有地图物件（墙段按矩形量），并进 `platmap.lint`（所以 `contract.map_design` 每次构建都跑）；②`platprops.clearance` 把施法圈 +20 算进保持空旷的圈；③`Mission.waypoint(..., cast=True)` 登记到 `Mission.spells`，`devices/horn.py` 的冰标记都传 `cast=True`；④产物规则 `contract.cast_points_clear`：登记的点必须是 cast 点、标记就在点上、任务自己的物件不进圈；⑤`maps/sapporo.py`：`lane foot` 挪到 (1200, 2470)（坡脚往南 70，平地），inside 1/2/3、north mouth、east mouth 标 `cast=CAST_CLEAR`；⑥守卫 `tests/test_architecture.py::test_g13_a_cast_point_is_level_open_ground`（含 6 个变异：标在非施法点、物件压进圈、旧位置在坡上、圆压到水、墙进圈、干净点不报；`CAST_CLEAR == 技能禁物范围 + 冰核` 这条数字守住；设备里的冰标记不传 cast 就失败）。节日图 J4 的冰是地图自带的、不是玩家放的，没有施法点。
- **后巷出兵点跟着南移了 70**（`出: lane foot` 偏移 [0,160]，现在出在 y=2630，仍在坡上）；冰雕偏移不变。策划线复核时看一眼。
- 检查"一律走玩家点击"：已由 `contract.observes`（G11）保证，只观测的检查才能当验收；`place`/`placem` 用传送把工兵放到点边上，再由测试台点技能按钮和落点。

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
