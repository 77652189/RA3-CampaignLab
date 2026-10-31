# 关卡线交接（总控 local_79408d22 清空会话后，从这里接着做）

写于 2026-10-30。只写进度和指针；事实以指到的文件为准。

## 我是谁、管什么

关卡线：`docs/story/`（outline、levels、plans/、map-language、units）、`experimental/cnv/`（单位外观接线除外）、模拟器（sim.py、simstatic.py、simchecks.py、simunits.py）、offline.py、platmap/platprops、terrainref。
不是我的：`docs/plan.md`（总控）、`docs/design/`（设计线 local_51ff7c05，机制结论可写进 `docs/design/flow/mechanics.md`）、音乐线的文件（`experimental/music/*`、`docs/music/handoff.md`、`missions/music_dyn.py`、`tests/test_a4music.py`、`tests/test_sampler.py`，以及 `plan.py`、`tests/test_plans.py` 里的音乐部分，都还没提交，别碰也别混进我的提交）、`build.py` MISSIONS 里的 `probe`、`experimental/voice/*`（配音线 local_0f2be670）。
规矩：`CLAUDE.md`（根目录）和总控给的那几条（通俗中文、mod 名 ≤15 字符不带下划线、提交署名、不 cd 进子目录、删文件先问、交给用户检查的只列真问题）。

## 已做完（不用再查）

- NOT 条件：`parts.unnot`，测试台确认。
- 模拟器对齐：`sim.py --align`，死亡不拖尾、帧率、揭图、血量读数、取反都按测试台改过。
- A4 离线检查：`experimental/cnv/offline.py`（相克、高地视野、一段一种兵，A4 过，5:53 通关）。
- 配音接线：任务带 `voice` 包，`CNV_` 开头的声音名必须在包里（`parts.py` 的契约）。配音测试台 `build.py voice_bench_12 --check play`（和 `ref` 原版对照）都 PASS：包按自己的长度播完，字幕自动出，音频读 `data\static.12\cdata`。细节在 `experimental/cnv/checks/voice.py` 顶部注释。
- 工程师占油井：`a4 --check derrick` 过；"兵少于 N"的数法已测准（`mechanics.md` 兵少补援一行）。

## 下一步（按顺序）

0. **灰盒（ADR 0011）已做完（2026-10-30）**：`experimental/cnv/graybox.py`（k\*，A4 三段全判平推轻松，测试 `tests/test_graybox.py`）；九张题卡的结论在 `docs/story/graybox-cards.md`，数字来自 `experimental/cnv/graybox_cards.py`（测试 `tests/test_graybox_cards.py`）。没补 `a4_before` 走查。新题卡出来后，往 `graybox_cards.py` 加函数、往 `graybox-cards.md` 加一节即可；模拟器判断不了的写"留给实机"。

0b. **引擎机制最小检查——四项都做完了（2026-10-30）**：结果在 `docs/story/drive-probe.md` 末节和 `docs/design/flow/mechanics.md`（冰面承重只能脚本做、干扰车对飞机有效、小地图闪点能按物体、信息框能当字符条）。下面是原来的派活说明，留作出处：每项上测试台做一个最小检查（`experimental/cnv/checks/` 里照现成的写，如 `jammer.py`、`probe.py`、`icewall.py`；用 `cnv_check` 跑，PASS/FAIL 加读数），结果写进 `docs/design/flow/mechanics.md` 的机制表（"冰面承重"那行 34 行附近，状态改"已确认/不行"并写读数）和 `docs/story/drive-probe.md` 旁。这是引擎事实不是打法测试，ADR 0011 允许。开跑前先查 `bench_status`，用户的游戏在跑就停下问。
   ① 冰面承重：不同重量的车压上去会不会掉，脚本能不能控制（退路是触发区里删重车 + 沉没效果，S1 甲、丙都依赖）；
   ② 干扰车（协调器）对飞机有没有效（J7 甲）；`checks/jammer.py` 已有，先看它测了什么；
   ③ 小地图能不能按物体闪点（A4 甲暗示、J7 甲）；
   ④ 任务信息框能不能显示（A4 丙的车头解冻条要用）。

0c. **（2026-10-30 晚）三张甲卡复算 + 没命名的车按种类杀，已提交（447e0bb）。** 结论在 `graybox-cards.md`"复算"一节：A4 甲 900 一组、第 2、4 波后各补满（设计线已采纳，brief 说 A4 甲不用再算）；J7 旧卡反扑 ≈ 驻塔大军造价 3.5 倍；没命名的车能按种类沉（`mechanics.md` 冰面承重行，`SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER`，`thin_unnamed --check kind` PASS）。工具：`graybox.fluid(..., later=[(秒, {兵: 数})])` 能算分批到达；`graybox_cards.py` 里 `a4_run`、`j7_counter` 是现成的样子。

0d. **（2026-10-30 做完，结论在 `graybox-cards.md`"第二轮"一节，数字在 `graybox_cards.py` 的 `s1_*`、`j7_*`，测试最后五条；下面是原任务说明，留作出处。待设计线按"要策划线改"改题卡；J7"按兵力分档派兵"计划词灰盒说需要，等总控定。）** S1 甲、J7 甲是重出的新题，要灰盒（设计线 local_51ff7c05，需求全文 `docs/design/cards/brief.md`，提交 635b2d3；之前对旧第三版的结论不适用）。每张末尾"请模拟器答"四个问题：①自然打法 vs 聪明打法谁占优；②每轮最优变不变；③拿掉一项还成不成立；④简单档安全网；判断不了的写"留给实机"。做法照 0 号条：往 `graybox_cards.py` 加函数、`tests/test_graybox_cards.py` 加测试、`graybox-cards.md` 加一节，别改题卡。
   - **S1 甲（拖在后面的卡车）**：钩卡车钩不动，要钩拖车的守护者、拽过薄冰让冰吞掉。要算：几何表（磁钩站冰边后 d、薄冰带宽 w、守护者离外沿 g：d+w+g ≤ 300，d+w > 150，w > 镰刀跳距；**镰刀跳距要先从数据里查**，`retail_objects`/单位数据）；三种自然打法（钩卡车、镰刀上冰、步兵上冰追）vs 钩守护者；步兵上冰追够不够亏（够亏就不用"湖心按种类杀步兵"，不够亏再用）；拿掉薄冰、拿掉钢缆。玩家没有坦克（磁钩、镰刀、动员兵、防空步兵、工程师），护卫最远射程 150。
   - **J7 甲（给谁修路）**：援军从界外进来、总走"路程秒数 + 剩下干扰车 × 15"最小的谷（打平走近的）；拆通哪条谷等于给援军修路。要算：**"拆几辆以后援军走哪条"的表**（近中远谷差 15 秒一档，每辆 +15 秒；每谷 2～3 辆）；三种自然打法（挑一谷拆通直冲、全拆、龟缩）vs 两种聪明打法（拆一条不走的谷当诱饵并自己顶着干扰走另一条、拆通一条谷并守在出口伏击）；苏联每波挪一辆后最优是否每轮在变；消融（干扰车不影响苏联单位 → 聪明 = 直冲）；简单档。最后反扑"先看会不会一边倒"，一边倒再加回"按兵力分档派兵"（我之前在 plan.py 里**没做**这个计划词，别做，除非灰盒要）。
   - 不做：`plan.py` 里"按兵力分档派兵"、S1"湖心按种类杀步兵"的计划词，brief 说新题不一定要。
   - 做完 `pytest tests -q | tail -n 5`，提交（只提交自己的文件）并推送，汇报每处一句结论给设计线（SendMessage to `local_51ff7c05-91d2-4470-98af-6d2fbcbff92a`）和总控。

1a. **（2026-10-31 做完，已提交 e77bae9）A4 第 3 层需求里的三项引擎检查**：`ice_ghost --check ghost` 和 `--check north`（`checks/icewall.py` 的 `ghost`、`ghost_north`，场景 `missions/icewall_bench.py` 的 `ghost`，用 aso 地图因为要敌方队伍）。结论已写进 `docs/design/flow/mechanics.md`（"鬼王砸冰墙""区域里数冰墙""找最近的冰墙并下令"三行），都是 PASS，用不上需求里的退路：
   - 鬼王**自己不砸**墙（站在墙边 20 秒墙血量 100），脚本 `NAMED_ATTACK_NAMED(鬼王, 墙名)` 下令就砸，一道墙约 16～24 秒（含走位）；
   - 区域里数冰墙：`PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA(玩家, 比较, 数, 冰墙种类, 区域)`，和老广场机关 `封住` 同一个条件；
   - 找最近的墙：`SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER(冰墙种类, 玩家, 敌方队伍, 名字)`，按鬼王位置由近到远（C、A、D、B；北头出生则 B、A、C、D）。**写法要点**：一道墙起了名就不再算"没起名的"，所以要拿一面旗记"名字指着东西"，墙毁了才放旗再选；从没起过的名字"已毁""没毁"都是假。样子照抄 `checks/icewall.py` 的 `ghost`（`Test - pick`、`Test - dropped`、`Test - smash` 三条）。
   - 用传送把鬼王挪过去再选，顺序对不上（原因没查）；A4 的鬼王是运输车卸下来的，等于创建，不受影响。

1b. **接着做：第 2 步，A4 的摆放和脚本按新流程稿重做。** 读 `docs/design/cards/a4-layer3.md`（地图要改、脚本表、要测的）、`docs/design/flow/a4.md`、`docs/design/maps/a4.md`。还没动手，要做的东西和落点：
   - **地图** `experimental/cnv/maps/sapporo.py`（测试 `tests/test_sapporo.py`，改完先 `cnv_preview(a4)`）：一号广场往西挪到接点约 x 2050，使后巷口（x 1250）、一号广场、二号广场三个街口相距 ≥ 800；三条街之间留后街（后巷当后街用），绕路长短差 ≥ 10 秒；最后一程三个口子（北坡口、三号广场、东街口）后面各一块炮位空地；布景（地道口、舞台、金奖牌）不挡试玩，先用替代品。
   - **计划** `docs/story/plans/a4.md`（编译器 `plan.py`，`plan_vocab` 查能写的词）：旧的"广场"机关（`devices/ice_plazas.py`，冰雕里藏兵、车到才碎、2/3 号杀不完）和新题对不上，要换成"号角"机关：号角计时器 + 倒计时显示，间隔表按难度（简单都 ≥ 45，普通 30/50 混，困难短的多）；号角响，开着的地道口各出一波（900：2 武士 + 2 坦克杀手，`打: 猎杀` 车队）；会场冻住的街（口子区域里有冰墙）那波改从后街绕路的起点晚 10 秒出；第一声号角只开后巷、一号广场；最后一程三口同号角，冻住的口子这波不出、记账（每口一个计数），墙没了一起放出；第三声号角起鬼王从海上靠岸，按上面 1a 的写法砸最近的墙，没有墙就 `打: 猎杀`。要删的：二号广场杀不完的地道、修理厂奖励、北坡口那路反扑（旧"北坡反扑"进攻）、海上天狗（旧"海上来的"进攻）。
   - **保留**：车队机关（`devices/convoy.py`）、北营 AI、电视塔/修理厂的"走近就归你"规则、兵少补援、补派冰幕工兵、冰幕工兵封顶两个（禁造/准造）、基地车交付、港口生变后号角停。
   - **检查** `experimental/cnv/checks/a4.py`：`idle`、`hold`、`win` 都是按旧题写的，要换成新题的几条（号角出兵、冻街改道、冻口攒兵、鬼王砸墙）；`derrick` 不变。
   - 做完 `cnv_preview` + 相关 `cnv_check` + `pytest tests -q | tail -n 5`，写进 `docs/design/flow/mechanics.md` 的新结论，A4 能不能试玩、缺什么（音乐、单位外观、配音）汇报总控。

1. **A4 按设计线新稿重做第 3 层。** 第 3 层要什么：`docs/design/cards/a4-layer3.md`（设计线 f4b7635，会场三街接点 ≥ 800、后街绕路差 ≥ 10 秒、口子后炮位、脚本表）。**最后一程灰盒已做（2026-10-31，`graybox-cards.md`"第三轮"，`graybox_cards.py` 的 `a4_last`）**：大军堵三口平推轻松（k\* 0.5～0.6）；鬼王只欺负车、冰墙只多拖 3 秒，转折在数字上不成立；每口一波要对着玩家的钱定。还要做的：地图改（sapporo 接点、后街、炮位）、脚本表照 a4-layer3.md、两项引擎检查（鬼王砸不砸冰墙、脚本能不能数到区域里的冰墙）。读：`docs/design/flow/a4.md`（流程稿，待用户审；第 2 层地图内容稿也还没出来）、`docs/design/flow/mechanics.md`（哪些机制能承诺）、`docs/design/maps/`（第 2 层，地图内容，设计线在做）。现有计划 `docs/story/plans/a4.md`；做法是改生成器和计划，不手改产物。要加的东西：
   不依赖流程稿定稿的三项准备已做（2026-10-30，测试 `tests/test_plan_lines.py`，全量 286 过，已提交；`plan.py` 里音乐线的 `CNV_MUSIC_CAPTIONS` 那段没带进去，还在工作区）：
   - 计划词 `兵少于 <n> <单位>、<单位>`（`plan.py` 的 `troops()`，比较码 0 是 `<`）；模拟器补了 `COUNTER_MATH_COUNTER`（0 加、1 减）和 `SET_COUNTER_TO_COUNTER`，**测试台还没验这两个动作**（只看过原版怎么用）；
   - 通报可以写 `{通报: 文字, 说: 说话人, 原文: 流程稿原文}`，任务的 `lines` 里留一张台词表；
   - `a4.md` 里改成术语表的叫法：天狗机甲、鹰击者VX、多功能步兵车。
   整体按新流程稿重做 A4 还没开始，要等用户审流程稿、第 2 层地图内容稿出来。
2. **配音接进 A4。** 卡在配音线还没交 A4 台词（`RA3-ChineseVoice/work/campaign/zh/A4/manifest.json` 还不存在）。到了就用 `experimental/voice/pack.py` 的 `make(levels=('A4',))` 接进 A4 的任务（参考 `missions/voice_bench.py` 的 `LazyPack`）。
3. **A4 的 `win` 检查**：旧版里后两辆车没到港口；重做后这条会换，先别查旧的。
4. **输出瘦身**（总控要求）：总控会列出输出最多的脚本，`experimental/cnv` 下的由我改成默认只打摘要，加 `--verbose` 才打全。

## 还没测的

走近就归你（平民建筑转给玩家）；A4 plaza 3 的接力冰；J4 返工（车停下来、人活着）；A7 友军 AI 重查。J4/J7/S5 的游戏内标题还是旧名，等这几关重做时改。

## 等谁

- 配音线：A4 台词。
- 设计线：A4 第 2 层地图内容。
- 用户：音乐 v5 试听（音乐线的未提交文件在等）。

## 踩过的坑

- 实测前先查 `get_status`，用户的游戏在跑就停下问，不要重试。
- 长检查放后台，输出写 `work/logs/`，屏幕只看 `PASS|FAIL|RESULT`。
- 配音包会拿 SDK 构建锁，已改成同进程里重入不再卡死（333f09e）。
- 测试台一个检查最多 4 行读数（`counters.MAX_LINES`）；第 4 行的数读不准（会读出 647 这种固定噪声），要紧的读数放前三行；多个状态可以压成一个数（位置编号、区域数）。标签别用"目标在哪"这类会读错的字，`cnv_list` 输出很长（几百行），别整条调用，用 Grep 查 `build.py`。
- 钩子 `guard_inline_edits.py` 会拦下带反斜杠的 heredoc / `python -c`（连 `newline='\n'` 也算）：改文件用 Edit/Write，别用内联 python。
- 检查里需要"脚本才创建的单位"时，基础任务（不带检查）也要有一个放好的对象，否则契约测试 `test_every_build_keeps_the_contract` 失败；做法是 mission 里在远处放一个，检查里杀掉再创建（`ghost`）。
- 音频的脚本帧数（约 44 帧/音频秒）和计时器帧率（约 15/秒）对不上，原因没查清：别把音频帧数换算成任务秒（`docs/engine/script-semantics.md` 第 11 条）。
