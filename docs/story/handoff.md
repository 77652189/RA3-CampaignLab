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

## A4 周考（2026-11-02，总控转来用户的话："美术暂时不动，音乐和台词试试能不能接入进去，质量先不管"；最新，先读这里）

- **已提交**（2e879f9、后两笔）：`plans/a4.md` 逐句对齐策划线的 `flow/a4.md`（含策划线 30c5555 按我的意见改的 ADR 0013 几句：司令/科尔只留态度，沃斯给基地、借兵、卡住提示、补工兵）。接上的有：简报十句（放在会场过场最前面，关前简报形式没定）、北营各句（基地展开、出坦克、车到正坡下、拆第一座工厂兵营、卡住）、布防"炮架好了吗"、最后一程各戏点、胜利三句（说完 14 秒再赢）、失败两句（会场/最后一程各一句，说完 9 秒再输）。
- **新事件**：号角 `绕路`、`都在歇`（至少两道墙没满冷却）、`鬼王砸墙`、`鬼王砸开`；车队 `挨打`（掉血一格 6 秒内成立，播报"关键单位遭到攻击"，会场再加沃斯一句）。测试 `tests/test_horn.py` 末四条。**这些事件的触发没有专项上测试台验证**（只证明脚本能编、整关五条检查不坏）；新规则的时机（尤其"都在歇"配"号角 2"、挨打的每隔 25 秒是否重新响）要试玩或加检查看。
- **头像可选项**：`experimental/cnv/clips.py`：录音旁 `video/<同音频名>.mp4`（288×288）存在就转 vp6、同句 `MOVIE_PLAY_RADAR`；没有就只播音频，转码失败只进 MISSING。**没有真实片子上过测试台**；连着多句台词时头像会比音频早起（对话事件排队、电影立即播），要看效果再说。测试 `tests/test_clips.py`。
- **配音线 11 句已交（2026-11-02），两个版本已重建并装进 Mods**（装前查过游戏没在运行）：`CampA4`、`CampA4En` 各 118 句进包，MISSING 清单为空，流程稿 76 句全在计划里；测试台 `demo/hold/idle/win/melt` 两个版本全 PASS（idle s64 结束，hold 号角 5 声，win s493 胜利）。`test_langs` 的 `PENDING` 已删。
- **说话头像（2026-11-02）**：计划顶层 `头像: [CNV_A4_008, 010, 020, 021, 025, 033, 034, 050, 082, 095]`（只放玩家不用看地图的句子；043、064、076、085、090 是打仗时的，不播；不写名单就没有头像；`plans/README.md` 有）。两个版本各 10 段 vp6 进包，`demo/hold/idle/win/melt` 全 PASS，已装进 `Mods\CampA4`、`CampA4En`。小窗放头像时整个替换小地图（播完恢复），字幕在屏幕下方中间，不冲突；截图 `work/logs/a4_head_radar.png`。看头像用 `a4 --check heads`（车队 20 秒挪到停车点，进港口过场；逐秒帧里找）。头像画面和嘴型对不对、声画同步，**没人看过听过**。英文版 win 比中文晚约 58 秒结束（s576 对 s518），应是英文台词更长。
- **音乐**：当前构建已带音乐线 v5（构建日志 `music: spliced map == our .mpf`，95 条流，`test_a4music` 在全量 337 通过里）；没改音乐线的文件。
- **用户试玩反馈第一批（2026-11-02，已做、两版重建装进 Mods、`demo/hold/idle/win/melt/heads` 两版 PASS，全量 345 过；没人亲眼看过游戏里的效果）**：①过场里配音台词一句接一句（`plan.py` 的 `scene()` 按录音长度 + 0.6 秒排时间，镜头到位后说话），连着的镜头只在头尾缓动、离得远自动拉长（`PAN_SPEED`）；会场过场 ≈ 110 秒、港口生变 ≈ 75 秒、布防新加过场 ≈ 37 秒（台词跟镜头，倒计时从交还控制起算）。②港口生变等队尾那辆活着的车到停车点才开始（`车队.到齐`），段上 `停火: 是` + `保护: [truck]` 过场里敌我中立、车无敌。③基地车先放超时空闪光 `{特效: 超时空}` 再出现。④国际版的单位名和提示译成英文（`a4.en.json`，`plan.py` 编译末尾翻译 `m.units` 的 strings）。⑤冰核（放置检查的那块）从 40 缩到 20（`horn.py SEED_SIZE`）：后巷坡 40 见方升 14、超过放置上限 8；**推测，没在游戏里验证**。⑥A4 地面草/土换雪（`sapporo.py SNOW`，`platmap.apply(swap=)`，用自带地形图集）。⑦演示工兵改用玩家开局那个，演完传回起点（`演示.工兵`）。⑧`副指挥官 关` 动作 + 顶层 `简报`（战役界面的任务名和概况）。⑨科尔借的兵改多功能步兵车（跟策划线 f7fc83b）。**没做**（出兵口提示已在下面"第二批"做完）：战役外壳探针（总控追加的下一件）。
- **第二批（2026-11-02 晚，出兵口提示 + 过场时长，已装进 Mods，外壳探针还没动）**：
  - **出兵口提示做完**：策划案 `街`/`口` 里每个口子写 `标志: {物件: OK_ARCH01, 偏移: [dx, dy]}`（`horn.py`）：立一个有名字的红牌坊（原版 `OK_ARCH01`，红柱，俯视像一根红杆；"红灯笼门楼"没模型，用它顶）、角色名 `标志 <名>`，目标 `把车队护送到 2 号广场` / `把车队送到港口` 的 `标记` 里挂着（一直在）。每声号角前 10 秒（`SIGN_WARN`，和号角计时器一起起一个"间隔 − 10 秒"的 `Horn Warn` 计时器）：要出兵的口子在标志上放信号烟 `CNV_A4_SignalSmoke`（`units/smoke.py`：原版阿姆斯特丹烟 `Amsterdam_01_Smoke6` 的粒子复制一份染红，原版的烟是白的、原版信标的闪光和烟测试台上画不出来）+ `OBJECT_CREATE_RADAR_EVENT` 小地图闪点；街：还没开的（二号第一声前）和这一刻冻着的不冒，口：三个都冒（冰是否在都冒）；烟活 11 秒自己消失。测试台看了：红烟清楚（暗红，截图 `work/testbench/runs/CampA4Signs_mcp_1102_181439/0004.png`、`0008.png`）；新检查 `smoke`（口号角前三口各一股烟、之后 12 个兵，PASS）、`signs`（给人看，不判定）。`tests/test_horn.py` 加一条。**烟的颜色是推测的"红"，用户要更亮可改 `smoke.py RED`。**
  - **过场按 Esc 不能跳**：实测（后台脚本在会场过场里给游戏窗口按 Esc，进游戏的时刻没变）：引擎里 `DISABLE_INPUT` 的过场不认 Esc，脚本也读不到按键（`script_catalog` 里没有按键条件、没有跳过动作），原版过场同样的做法，所以只能缩短。港口生变的 4 句（科尔抱怨、沃斯两句中场、下半场）已挪到北营开场（过场约 75→45 秒，没测实际秒数）。**会场过场的关前简报 10 句（约 65 秒）还没动**：挪到交还控制后会和开场规则的"车队出发/号角多久"排队、顺序乱，已用消息问策划线（`local_51ff7c05`）哪些必须留在过场、哪些能删；没回前保持原样。
  - **测试台检查的计时改了**：会场过场 110 秒后，测试里"从任务开始数秒"的计时器在过场里就跑完了；`checks/a4.py` 新增 `AFTER`（过场结束旗 `CNV_A4_Scene_1`），`stand`/`ice_at`/`mouths_on`/derrick/heads/相机的计时都等它。重跑：`horn`（读数器把第一帧的 0 读成 4，期望从 s4 起判）、`detour`、`queue`、`smoke` PASS；**`smash` 在 x8 下读数全 0 判 FAIL，x1 手动看（bench_start CampA4Smash）冰墙、鬼王上岸都对（s59 冰墙 1、鬼王 1），所以是 x8 下的读数或时序问题，没查清（去掉东街口的标志也一样，不是标志的错）**。`demo/melt/hold/idle/win/heads` 没重跑。
  - **测试台坑**：①首帧就是过场结束那一刻（HUD 回来）；②镜头移动在任务里要 1～7 秒，看有时限的东西（烟）要在检查里让它循环出现（`signs`）；③`bench_wait(look=false)` 之后 `bench_look` 看到的是旧帧。
  - **外壳探针（ADR 0014）还没做**：要求见总控消息：A4 放到盟军第一关位置、任务名和播报文字换成我们的、战前过场用测试视频、局势介绍讲话用沃斯头像、战役卡片占位图、世界地图那页只换两张贴图、副指挥官面板看是整块藏起来还是只变灰、单独启动器并验证原版不受影响、mod 名 ≤15 字符不带下划线；做完截四张图：战役卡片、任务列表、播报页、开局。调研在 `work/research/campaign_frontend.md`、`campaign_add_entry.md`。
- **下一步（用户第二轮试玩 + 总控追加，2026-11-02 夜；清空后的新会话按这个顺序做，提交 54eeb87 之后）**：
  1. **按策划线新稿实装**：`docs/design/flow/a4.md`（提交 1d80869、4a0a635、374ebf4）、做法表在 `docs/design/cards/a4-layer3.md` 第二节"冰雕里出兵"。要点：过场瘦身（开场约 30 秒、港口生变约 25 秒、布防开头约 20 秒）；台词挪进游玩（交还控制 6 句顺序播、车队出发后 2 句、基地车展开半分钟后科尔两句、布防倒计时过半或走近三号广场的金奖两句、北营交还控制的几句）；删两句 A4_005、A4_012；六个出兵口各一座"出兵冰雕"（比装饰冰雕大、发暗、带地道口石底座、打不坏、挂标记、150 内不摆别的冰雕），兵出生点放底座，号角前十秒冒烟+闪点，号角响时裂开并保持裂开，第一声号角后二号广场那座裂一道缝；会场和港口路多摆小冰雕、灯笼、彩旗、摊位。**我这轮做的红牌坊 `标志` 只是占位**（`horn.py` 的 `标志`、`units/smoke.py` 的红烟、冒烟脚本可以直接复用，标志物换成出兵冰雕）。
  2. **冰雕怎么裂开（已查）**：`units/festival.py` 的 `sculpture()`（模型 `CNIceSculpt`、打碎留 `CNIceRubbleS` 碎冰，`hard` 版 `CNIceSculptHard`）就是旧 A4"冰雕里出兵"用的（`devices/ice_plazas.py`、`checks/a4_before.py`）：脚本 `NAMED_KILL` 它就碎；"裂开后保持裂开"要自己做一个碎裂后的物件（可复用 `CNIceRubbleS` 大一号，或碎冰留着不沉）。原版现成物件：`GE_STATUE01`、`HB_Statue02`、`HV_SCULPTURE01`、`KR_STATUE01`、`ST_STATUE01-04`（雕像）；本图已用的：`OK_LANTERN01`、`MJ_BANNER01/02`、`TH_LAMPDECO03`、`TH_LAMPPOST04`、`TH_Fish_Market02/03/04`（摊位）、`TH_JAPANCRATE01`、`OK_ARCH01`（红牌坊）、`OK_Pagoda01`。
  3. **过场镜头自动给视野**（总控转用户原话："到第二个检查点显示北营营地时看不到帝国的建筑和兵种"）：每个过场镜头开始移动时，在目标点周围临时揭图，过场结束收回；不开全图。先 `retail_scripts` 查原版过场怎么给视野（`MAP_REVEAL_AT_WAYPOINT` / `MAP_UNDO_REVEAL…` 一类，plan.py 已有 `揭开: <点>, 半径, 永久` 和 `看一眼`），做成 `镜头` 步骤的通用行为；测试台截北营镜头的缩小图给总控，要能看见帝国的建筑和兵。
  4. **头像名单去掉 `CNV_A4_082`**（金奖那句挪进布防倒计时，玩家在看小地图）；剩九句。
  5. **战役外壳探针**（ADR 0014，要求见上一条"外壳探针"）。
  - **过场能不能跳（已查，回给总控和策划线）**：原版没有。`retail_scripts` 查 SKIP / cinematic / escape 只有两条调试脚本（`debug skip objective`）；原版过场（如 `camp_a01_brightonbeach_smith` 的 `Intro Cine 01`）就是 `CAMERA_LETTERBOX_BEGIN` + `DISABLE_INPUT` + 镜头脚本，`script_catalog.json` 里没有按键条件和跳过动作；我们实测过场里按 Esc 进游戏时刻不变。
  - **没解决**：`smash` 检查在 x8 读数全 0（x1 手看正常），见上；`demo/melt/hold/idle/win/heads` 在 AFTER 改动后没重跑。
- **没做**：流程稿"部队在正坡下一直挨打"用"进入 north camp 45 秒后"近似；头像没有真片子；游戏里的声音测试台听不到，要用户试玩。

## 最新状态（2026-11-02 头像接完后；本节是 11-01 晚的旧文，只在这行补最新：A4 两个版本各 118 句、10 个说话头像，五条检查两版全 PASS，已装进 `Mods\CampA4`、`CampA4En`，已推送 a156bbf。头像细节见上面"A4 周考"节的"说话头像"一条；下一步是用户试玩后的反馈清单，由总控发给清空后的新会话）

- **A4 两个版本都做完并通过检查**：中文版 `CampA4`、国际版 `CampA4En`（`build.py a4 [--lang intl]`，逻辑在 `experimental/cnv/langs.py`，音频和字幕问配音线的 `route` 命令，ADR 0013），各 111 句进包，测试台 `demo/hold/idle/win/melt` 全 PASS，已装进 `Mods`，启动器认得国际版。详见 **1f**。
- **缺配音的 7 句**：计划里的台词和配音稿对不上，只有字幕没有声音，两个版本相同；清单每次构建开头的 `MISSING` 里就有（`python -I -X utf8 experimental/cnv/build.py a4 --lang zh` 看），文字和位置见 1f 末尾那几条；要么策划线/配音线改稿对上，要么改 `plans/a4.md` 的台词去对稿。国际版这 7 句的英文是我在 `docs/story/plans/a4.en.json` 补的临时译文。另有两处没接：流程稿"卡住了"的"关键单位遭到攻击"（车队设备没有"被拦/被攻击"事件）、两处原版播报没亲耳听过。
- **视频试验做完**：任务能播自己做的小窗视频和全屏视频，转码一条命令 `python -I -X utf8 experimental/video/to_vp6.py in.mp4 out.vp6 --size radar|full`（NihAV 的 EA/VP6 编码器，已编好），坑和结论见 **1g**。还没接进计划词。
- **下一步：等用户试玩 A4 的反馈**（试玩清单在 `work/playtest/a4.md`，不进 git），再按反馈调数字（号角间隔、每街一波兵数、绕路秒数、补兵 45 秒、车速 12）。之后候选：①视频进计划词（`{视频: 名字, 位置: 小窗|全屏}`）；②"车被拦住"事件 + 对应播报；③其他关出国际版（`MISSIONS` 里加 `<关>_intl`，启动器自动认）。
- **踩过的坑（都在 1f、1g 里有细节）**：测试台首帧已在任务约 40 秒、跳过开场过场；Esc 暂停在过场里失败会被当成"任务结束"；读数器会把连续相同数字并成一个；`cnv_check` 偶发菜单卡住（`build=false` 重试）；`git://` 连不上要用 gitweb 快照；工作目录会漂（一律用绝对路径，不要 cd）。
- 规矩：装进 Mods 前单独查红警3是否在运行；下载要用户本人在本会话里说；上下文超 15 万写交接（这次已超 50 万）。

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

1e. **（2026-10-31，提交 7779639）用户定了 A4 的改法，总控转来的八条做了大半，已装进 `Mods\CampA4`。** 用户原话："先按第1种降速，加上演示镜头，冰墙不需要限制，减少初始工兵，后续只给补充到最大数量就行，其他缺失的内容也接上，包括配乐，闪点，除了3D模型之外尽可能做的完善一些"。
   - ①**车速 12**（`车队` 机关新参数 `速度`，`units/convoy.py` 的 `truck(speed=)` 改运输车 XML 里的地面速度）：会场 2730 / 12 ≈ 227 秒，加开场后倒计时，约 4 分钟到停车点；号角间隔表改成合计 225/215/180 秒（简单档车到前 22 秒响完第五声）。最后一程同一速度：920 / 12 ≈ 77 秒一辆，0/50/110 分批，第三辆 187 秒到；同一张间隔表盖得住（理由写在 `plans/a4.md` 机关节）。灰盒/离线走查 `offline.py` 的 `WALK` 时间跟着挪了（半路后的动作都 +190 秒）；`tests/test_graybox.py` 里"有敌人的阶段"多了港口生变（第五声的那一波在车到停车点时还在路上）。
   - ②**开场演示**：号角机关新动作 `雪祭.演示` / `雪祭.演示收`（参数 `演示: {街: 一号, 绕去: 后巷, 等: 4, 兵: 2}`）：过场里建一个演示工兵冻一号街口，冰立起来（`冻住` 标志）后在街内出 2 个帝国武士，4 秒后删掉、在后巷口出 2 个（"钻地道绕路"），过场末尾全收走。会场过场加长到约 34 秒（镜头回到一号街口 → 演示 → 沃斯"看见没有"→ 镜头到后巷口 → 收）。**测试台验证没做成**：见下。
   - ③**冰墙不设上限**：删了"封顶两个"；④**初始工兵 1 个，补到最大数量 2 个**：规则 `[过场 会场 结束 + 0:20, 兵少于 2 冰幕工兵]` 每隔 45 秒在 `entry` 补一个；冰幕工兵的角色现在叫 `engineer`（不带号），检查里同步改了（`a4_before.ice_wall` 兼容两种叫法）。
   - ⑤**小地图闪点**：每一波第一个兵出生、鬼王上岸，`OBJECT_CREATE_RADAR_EVENT`（`horn.py` 的 `make_at` 和 `ghost_scripts`）；`sim.py` 的 SHOWN 里加了这个动作和 `NAMED_SHOW_INFOBOX`。⑧**信息框**：`plan.py` 新动作 `{信息框: <角色>, 文字:, 秒:, 图标:}`（`plans/README.md` 有），A4 用在工兵头上两处（"选中我，点街口"、"冰墙立起来了，歇 40 秒"，固定文字，不是走条）；图标用 `Button_AlliedEngineer_on`（原版 A01 医院框用的那个），游戏里显示对不对**没看过**。
   - ⑧**整关走查三个口子**：`checks/a4.py` 新增 `idle`（什么都不做，会场里输）、`hold`（车保持满血，五声号角响完、车到二号广场门口、转港口生变）、`win`（车满血、北营一开始就拆指挥所，三辆车到港口、胜利），外加 `demo`；`build.py` 已登记。`scene()` 加了 `park/endings/trucks_up/long_run` 几个开关，`long_run` 每 2 秒把镜头拉回黑底（过场会把相机移走，数读数条要黑底）。
   - **没做完的**（（a）（b）（c）已在 1f 做完或接上，下面是当时的原文）：（a）上面四条检查 `demo/idle/hold/win` **一条都没上过测试台**——用户在玩红警2（进程 `game`，窗口"Red Alert 2"），测试台起不来（`D3DERR_DEVICELOST`，"另一个程序占着屏幕"）；屏幕空出来后先跑 `cnv_check a4 demo`，再 `hold`、`idle`、`win`（`win` 约 8 倍速下几分钟）。`demo` 要小心：测试台启动会按 Esc 跳过开场过场，跳过时演示可能被一口气收走（上一次试跑冰墙起来了、兵没出，就是这个嫌疑）；检查里加了"演示状态"读数（1 开始 / 10 冰在 / 100 已收）帮着看，必要时让检查自己在 t=1 发 `演示` 标志、不依赖过场。（b）配乐（音乐线第 5 版已提交 3eae5b4，接口等它来消息）、配音（等配音线给事件名）还没接。（c）全量 pytest 还有 6 个失败不是这条线的：`experimental/voice/pack.py` 配音线未提交的改动让 `voice_bench` 的 `pack.TEST` 解包出错（`test_cnv_parts` 四条、`test_maps` 两条）。（d）工兵"冷却"信息框是固定字不是走条。
   - 数字起步值（间隔、每街一波、绕路秒数、补兵 45 秒）实机后再调。

1g. **（2026-11-01，用户批准的小试验）任务脚本能播自己做的视频：小窗和全屏都成了，测试台 `cnv_check movie play` PASS。**
   - **怎么进 mod**：和原版一样两处声明（SDK `SageXML/Video/`）：`<Video id=X Filename=X Volume=190/>` 加同 id 的 `<VideoEventList id=X><EventList><Movie MovieAsset=X/>`，放进 mod 的静态流（`experimental/video/pack.py`，同语音包的 include 方式）；片子 `X.vp6` 放进 **mod 的 .big，路径 `data\movies\X.vp6`**（原版放在游戏目录 `Data\Movies\`，**不用往游戏目录放文件**，原版文件没动）。脚本 `MOVIE_PLAY_RADAR('X')` 小窗、`MOVIE_PLAY_FULLSCREEN('X', 0)` 全屏。
   - **转码**：ffmpeg 只能解 VP6、不能编。唯一现成的 EA 封装 VP6 编码器是 NihAV 的 nihav-encoder（作者页 nihav.org/vp6enc.html，他说没在原版里测过，这次测了：能播）。本机已装好：Rust（`~/.cargo`，stable-msvc minimal，rustup-init 来自 static.rust-lang.org）、源码快照下自 `git.nihav.org`（`git://` 连不上、https 的 gitweb 快照 `https://git.nihav.org/?p=nihav.git;a=snapshot;h=HEAD;sf=tgz` 和 `nihav-encoder.git` 同法能下），解在 `work/downloads/nihav/src/nihav-HEAD-63ac44b/`（encoder 放进它里面改名 `nihav-encoder`，`cargo build --release` 约 40 秒），可执行文件 `…/nihav-encoder/target/release/nihav-encoder.exe`。**一条命令转任何视频**：`python -I -X utf8 experimental/video/to_vp6.py in.mp4 out.vp6 --size radar|full`（OpenCV 解码 → 23.976 fps、小窗 288×288 / 全屏 1280×720 留黑边 → y4m → `nihav-encoder --output-format ea --ostream0 timebase=1000/23976,encoder=vp6,version=vp61,quant=40`）。输入宽高必须是 16 的倍数。
   - **原版片子的格式**（`Data\Movies\A01TH01.vp6` 读过头）：`MVhd`(32 字节：vp60、288×288、帧数、最大帧、23976/1000 fps) + 一个 `MV0K` + 若干 `MV0F`，**没有音频块**：原版的声音是脚本另外 `PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT` 配的对白（`MA02_AlliedIntel21` 和 `A02TH..` 同时放），所以我们的小窗片也该是无声的、声音走语音包事件；带声音的 EA 封装没试，没必要。nihav 的输出结构和原版一致（只是关键帧多：每 ~10 帧一个）。
   - **坑**：①`HAS_FINISHED_VIDEO` 对**小窗**片成立（63 帧 ≈ 4 秒，播完才为真，找不到的片子会立刻为真），对**全屏**片一直不成立——原版也只对 TH 小窗片用它，全屏片靠定时器；②全屏播放时屏幕上的计数条被盖住（读数条读不出，测试台里一段 `?`），播完恢复；③小窗里放片子时小地图被替换，播完变回小地图；④nihav 输出比输入少一帧（48 帧进 47 帧出），无所谓；⑤测试台不出声，没验证 Esc 能不能跳过全屏片、也没试 1280×720 以外的全屏尺寸；⑥`git://` 协议在本机连不上，下源码要用 gitweb 快照。
   - 代码：`experimental/video/pack.py`（Pack：include/files/events/check）、`to_vp6.py`、`parts.py` 的 `Mission.video` 和 assemble 里一段、`missions/movie_bench.py`、`checks/movie.py`、`build.py` 的 `movie`、`tests/test_video.py`。测试片在 `work/video_test/`（不进 git，`make_test.py` 能重造）。
   - 没做：把真的小窗视频（给 A4 的"工兵演示"之类）接进计划词（`plan.py` 要加一个 `{视频: 名字, 位置: 小窗|全屏}` 动作和视频清单，现在只有测试台任务能放）；视频内容谁来做（AI 视频？剪辑？）是总控的事。

1f. **（2026-11-01，提交 8c4af8f、62640a7、70a59bb）1e 没做完的 (a) 做完了；冰墙即将融化接上；A4 出两个版本（总控转来的用户要求"一次做全"）。**
   - **测试台四条整关检查全 PASS**：`demo/hold/idle/win`（外加新的 `melt`）。踩的坑：①测试台跳过开场过场，首帧已在任务约 40 秒（整条演示在首帧前跑完、过场末尾的 `演示收` 一下触发），所以 `demo` 改读"闩锁"标志（开始 1、兵在冰后出 20、转向 300、收走 4000，位值互不相同：读数器会把连续相同数字 `111` 并成 `1`），并摘掉过场自己的 `演示收`、演示开始后 30 秒由检查自己收；②`hold/win` 的暂停（Esc）在港口生变过场里会失败，测试台就当"任务结束"跳过后面的观察，所以 `checks/a4.py` 的 `scene_proof_watch` 把观察切成过场前（FESTIVAL−60）停一次、一次长观察盖住过场；③`cnv_check` 偶发"菜单卡住 / Esc 打不开暂停菜单 / 连接丢失弹窗"，`build=false` 重试即可。读数：idle 约 s62 失败，hold 号角 5 声、车 s242 到停车点、过场后读到港口生变，win 约 s479 胜利。
   - **冰快化**：`horn.py` 事件 `雪祭.冰快化`（冰墙只剩 8 秒、`MELT_WARN`；墙没了就落），`plans/a4.md` 规则 `每隔 0:20` 放播报"冰墙即将融化"（`CNV_A4_016`）。`melt` 检查只证"旗曾升起、墙没了旗落"（测试台首帧时刻每次不同，不能按钟点判）。
   - **两个版本**：`python -I -X utf8 experimental/cnv/build.py a4 [--lang intl]`，等价于名字 `a4` / `a4_intl`（`cnv_check` 直接传 `a4_intl`）。中文版 `CampA4`（中文字幕、中文配音，已用冰幕工兵 46 句和沃斯的句子重建，96 句进包）；国际版 `CampA4En`（英文字幕，配音按角色阵营：盟军/未来科技 en、苏联 ru、帝国 ja；已建成，**目前没有英文音频和字幕文本，只带翻译过的界面文字**，工兵保留原版语音）。逻辑全在新文件 `experimental/cnv/langs.py`（文件顶有接口说明）：事件名各语言相同、音频读 `work/campaign/<配音语言>/<关>/<事件>.wav`、字幕读 `lines/campaign/<关>.json` 的 `text[en]`、条目可带 `voice_lang` 覆盖；缺的句子不静默，构建开头打印 `MISSING in CampA4En (n)`（`m.missing`），并跳过让计划退回字幕。计划自己的字符串（目标、固定提示、标签）从 `docs/story/plans/a4.en.json`（中文原文 → 英文）出，缺的列出；说话人的句子（沃斯/司令/科尔/播报/冰幕工兵）不翻，等配音线的英文文本，所以国际版现在这些字幕仍是中文并列在清单里。`experimental/voice/pack.py` 的 `make` 加了一个 `items=` 参数（配音线的文件，只加了这一处）。
   - **ADR 0013 之后（2026-11-01，取代上面"按阵营算配音语言"的做法）**：每句用哪条音频、哪条字幕不再由 `langs.py` 自己推，而是问配音线：`RA3-ChineseVoice` 的 `python -I -X utf8 tools/campaign_lines.py route <关> --version zh|intl`（`langs.route()` 调它，`docs/campaign_voice.md` 第 7 节）。中文版只有播报、情报官（沃斯等）、单位语音说中文，剧情角色（司令、科尔…）是母语原声配中文字幕；国际版同一套原声换英文字幕、播报/情报官/单位语音也换母语。`langs.Resolved(levels, lang)` 给 items / missing / said / retail；一关的事件清单以配音线的 `lines/campaign/<关>.json` 为准（不再是 `zh/<关>/manifest.json`）；冰幕工兵的单位语音组名由 `u_ice_engineer.json` 的 `where` 推（`langs.unit_groups`，和旧 manifest 核对一致）；`audio_lang` 为 None 的是原版播报事件。缺清单现在多一类：`caption only, no recording of it`（计划里有说话人、但没有任何录音的台词），和 `plays the interim … recording`。现状：zh 版 96 句进包（沃斯 46 + 播报 4 + 工兵 46），司令 11 句、科尔 4 句还没有英文原声（只有字幕，列在清单里）；国际版目前一句音频都没有。**没重装** `Mods\CampA4`（用户在试玩），只用 `build.py a4 --check idle --plan` 验证两个版本都能编。
   - **英语配音交付后（2026-11-01 晚）已收尾**：配音线交了 A4 英文 65 句和冰幕工兵 46 句（共 111 句，播报 4 句仍播原版事件）；`CampA4`（zh）和 `CampA4En`（intl）都已重新构建装进 Mods（装前单独确认游戏没在运行），各 111 句进包；两个版本在测试台上 `demo/hold/idle/win/melt` 全 PASS。缺失清单只剩 7 句：计划里的台词和配音稿对不上、只有字幕没有声音（沃斯"港口桥头被堵了"等 4 句、科尔 2 句、司令"又调来一个冰幕工兵"），中文版和国际版相同；国际版这 7 句的英文字幕是我在 `a4.en.json` 里补的临时译文，配音稿对上以后以配音线的为准。`checks/a4.py` 的 `scene_proof_watch` 后半段改成 120+90 秒分段，避开 win 的任务结束区间（s430–520），不再靠重跑碰运气。
   - **等配音线交付英文后**：`build.py a4 --lang intl` 看 MISSING 清单是否清空，再对 `a4_intl` 跑 `demo/hold/idle/win/melt`（名字 `CampA4EnHold` 等，不超过 15 字符），跑过就算国际版完成。配音线若把英文文本放在别处（不是 `lines/campaign/a4.json` 的 `text.en`）、或音频目录与 `langs.py` 假设不符，改 `langs.lines()` 一处即可；`tests/test_langs.py` 6 条守着。
   - **配音线 2026-11-01 回复确认了上面的假设**（接口写在 RA3-ChineseVoice `docs/campaign_voice.md` 第 7 节）：每个语言目录只放用该语言说的句子；manifest 的 `text` 是说出来的文本（配音语言），**不是字幕**，字幕只取 `lines/campaign/<关>.json` 的 `text.en`（`langs.py` 正是这样）；manifest 新增 `voice_lang` 字段（zh 现有的没有，缺省 zh）；en 目录 manifest 没有 eva 项。他们交了英文译文和英文配音会通知。
   - **原版播报做完了（2026-11-01，总控要求"一次做全"）**：zh manifest 里只有 `eva`、没有 `event` 的播报（"关键单位遭到攻击/损失"）现在编译成 `PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT('Aeva_CritUnitLost')`，不带字幕，两个版本都直接播原版事件（国际版跑英文原版；中文版由中文配音 mod 给同一个原版事件配中文，`lines/eva.csv` 有该音频的中文稿）。对照表不用查了：`Aeva_...` 就是 SDK `SageXML/Sounds/Voice.xml` 里的 AudioEvent id，`voice_link.Later.eva()` 构建时拿它核对，查不到就列进 MISSING（现在两条都查得到）。接线：`plan.py` 的 `通报`（先找自己的配音事件，再找原版事件），A4 计划新增一条规则 `车队.损失 2` → 播"关键单位损失"（流程稿失败台词）。**没接**：流程稿"卡住了"的"关键单位遭到攻击"（车被拦住就说，车队设备没有"车被拦/被攻击"的事件，要引擎条件，没做）；游戏里没亲耳听（测试台不出声）。顺带：`sim.py` 的 SHOWN 补了 `PLAY_SOUND_EFFECT`（配音）和这个动作，`test_sim` 不再报未知动作。
   - 没做：国际版的其他关（`a4_intl` 之外没有版本；`MISSIONS` 里照样加 `<关>_intl` 即可）；冰幕工兵的英文单位语音（等配音线交付，包里有 `CNV_IceEngineer_VoiceSelect` 组才会开）；游戏里实际听/看两个版本（测试台不出声，要用户或录音）。

1d. **（2026-10-31 做完，提交 d43deba、4ce8a77、1f2bcd8 和检查那一笔；下面 1c 的四件都做了，1c 留作出处）A4 新稿已装好试玩（`Mods\CampA4`，`build.py a4`）。**
   - ①地图：`sapporo.py` 街口 1200 / 2015 / 2830（≥ 800），后巷坡宽 120，三个炮位站点 `gun north/plaza 3/east`（站点，没摆东西；炮位上放什么还没定）；`tests/test_sapporo.py` 加了间距和炮位两条。
   - ②机关：`devices/horn.py`（计划里叫 `雪祭`，类型 `号角`）。街口冻住绕路表在 `plans/a4.md` 机关块，`check_delays` 编译时查"任两条绕路差 ≥ 10 秒"，`tests/test_horn.py` 8 条。冻住的口子攒兵、鬼王砸最近的墙、`鬼王上岸`、`放出` 事件都在里面。
   - ③计划：`plans/a4.md` 按流程稿六段重写，删了广场、北坡反扑、海上天狗、后巷冰雕、修理厂；末尾有"检查"和"号角返工"两节记没做的。
   - ④检查（测试台都 PASS，2026-10-31）：`horn`（第一声 8 个兵，二号街第二声才出）、`detour`（一号街冻住：后巷的兵 s35 出，一号的兵晚 10 秒在后巷口 s45 出）、`queue`（北坡口冻住：另两口 8 个照出，北坡口这 4 个攒到冰化 s61 才出）、`smash`（鬼王上岸，没人下令，墙血量 100→76→65→53）。
   - **试玩前要知道的三件事**：①**车队只要约 1 分钟就开到二号广场门口**（速度 50，路 2580），号角第一声约 35～45 秒才响，会场里最多听到一两声；流程稿说"约 4 分钟五声"，要么车速降到 ~12、要么号角后停车队、要么号角间隔缩短，需要用户或设计线定（我没改）。②开场"工兵冻一号街口、兵掉头绕后巷"的演示镜头没做（现在是镜头扫三个街口加台词）；"冰幕工兵封顶两个"缺条件词"兵多于"；小地图闪点没接。③`a4` 没有整关 `win` 检查了（旧的按广场写的，已删），三个口子的整段跑通要手动试玩。
   - **测试台新踩的坑**：测试台启动会跳过开场过场，开场过场计时从 0 起算；读数条要在黑底上才读得出（相机挪到地图西边 `(0, start.y)` 的虚空，见 `checks/a4.py` 的 `scene`）；标签里不能有"一"这种一横的字（会被当成噪点，整行读不出）和全角括号（后面留空太宽，行被当成结束），用数字（"1号街的兵"）；灰盒/离线的老测试里"带空军的一段"现在用手写的敌人组成（`tests/test_graybox.py`），新 A4 自己没有空军。
   - 下一步建议：先定车队节奏（上面第①条），再按用户试玩反馈调间隔、每街一波、绕路秒数；然后补演示镜头和封顶。

1c. **（2026-10-31 清空后第一轮，只读不改，没有任何未提交改动）第 2、3 步的落地方案，已读完下面这些文件，下个会话不用重读：`a4-layer3.md`、`flow/a4.md`、旧 `plans/a4.md`、`maps/sapporo.py`、`devices/ice_plazas.py`、`devices/convoy.py`、`plans/README.md` 词表。**
   - **做法分四件，按顺序**：①地图 ②新机关 `devices/horn.py`（类型 `号角`）③重写 `plans/a4.md` ④重写 `checks/a4.py`。旧 `ice_plazas.py` 别删（`a4_before` 还在用），只是 a4 不再引用。
   - **①地图（sapporo.py）**：街口间距 ≥ 800 要同时满足 后巷口—一号—二号。二号门中心 x = 2830 不动，所以：后巷口 1250 → **1200**（`Ramp((1250,…))`、`lane foot` 站点、`LANE_WAY` 第一个点同步改，坡宽 160 → **GATE=120**，否则 200 长的冰墙封不住），`P1 = (1860, 2170, 3030)`（门中心 2015，间距 815/815）。`NORTH_BLOCK` 多边形、`lane mouth`、`inside 1` 等都由 `P1` 派生，会自动跟着；`WEST_END=2100` 比新的 `P1[0]` 大，改成 `P1[0]-100`（南街区 `WEST_END-100` 同理）后跑 `tests/test_sapporo.py`，别的断言（`test_the_back_lane_is_only_its_two_ramps` 用 RAMPS[0]）会跟着坡走。`LANE_DOWN` 坡（2610）留着：敌人是脚本在街口出生，不靠它绕路。最后一程三口后各加一块炮位空地：北坡口、三号广场（门在 x 3370，北边）、东街口各一个站点（`gun north`、`gun plaza 3`、`gun east`，半径 ~100，口子后面 200～300 处），加进 BLOCKS 的『前线』里不要和现有块冲突；布景先不做。改完先 `cnv_preview(a4)`，再 `pytest tests/test_sapporo.py -q`。
   - **绕路用"出生点换位 + 延迟"做**（不做物理后街）：每条街一个出生点（后巷＝`lane foot` 上方一点、一号＝`inside 1`、二号＝`inside 2`），号角响时看街口区域里有没有冰墙（`PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA`，和旧 `封住` 同一条件，区域取 `m.areas[...]=square(...)`，样子照 `ice_plazas.py` 的 `place()` 里 `walls[k]`）；冻住的街，那波改在开着的街出生、晚 N 秒：开一号 ← 后巷 +10、二号 +20；开后巷 ← 一号 +10、二号 +30；开二号 ← 一号 +10、后巷 +20（两条绕路之间都差 ≥ 10 秒）；只冻一条时去最近的开着的街（后巷↔一号↔二号 的次序）。把这张表写进 `horn.py` 的参数 `绕路`，并写一条测试证明"任意两条绕路差 ≥ 10 秒"。
   - **②`horn.py`**：模仿 `ice_plazas.py`（工兵、冰墙、种子核心、`iw.clear_of` 传送、倒计时 `DISPLAY_COUNTDOWN_TIMER`、`cv.chase(j)` 猎杀车队）。参数：`车队`、`间隔`（按难度的一张表，如 `简单 [45,50,45,50,45]`，普通 30/50 混，困难短多）、`每街一波`（`{帝国武士:2, 坦克杀手:2}`）、`街`（出生点和区域）、`绕路`、`冷却`。事件：`号角 <n>`（第 n 声）、`冻住 <街>`。动作：`停`（港口生变）、`开`（布防倒计时归零后恢复）。最后一程：同一机关另一组口子（北坡口、三号广场门、东街口），**号角时口子区域有冰墙就不出、给这口计数 +1，墙没了一起放出**（`INCREMENT_COUNTER` 记、放出时循环 `CREATE…` 按计数；`COUNTER_MATH_COUNTER`/`SET_COUNTER_TO_COUNTER` 测试台还没验，需要的话先 `plan_words` 里做最小检查，或者改成"每口最多攒 3 波，放出时三个固定的 Release 脚本各按计数 ≥1/≥2/≥3 放一波"，用不到那两个动作）。鬼王：第三声号角起 `突击运输车` 从 `beach` 靠岸卸鬼王，砸最近冰墙的写法见上面 1a（`checks/icewall.py` 的 `ghost`：`Test - pick`、`Test - dropped`、`Test - smash`）。注册进 `devices/__init__.py` 的 `registry()`。
   - **③a4.md**：保留 车队、北营 AI、电视塔/修理厂"走近就归你"（修理厂奖励已删：流程稿说第 1 段不修，修理厂规则、目标、`depot` 都去掉）、兵少补援（科尔借两辆守护者和一队维和：丢车且鬼王在场时）、补派冰幕工兵、冰幕工兵封顶两个（`禁造/准造`）、基地车交付、港口生变后号角停。要删：`广场` 机关、`进攻` 里的 北坡反扑 和 海上来的（后巷无人机一并删：后巷冰雕也去掉）、2 号广场目标/规则、`冰雕演示` 过场（改成流程稿开场镜头：工兵冻一号街口、兵掉头绕后巷）。段名对应流程稿：开场/会场/港口生变/北营/布防/最后一程（现有四段加一段"港口生变"）。台词用 `{通报: …, 说: 沃斯, 原文: …}` 照 `flow/a4.md` 的台词写；护卫补满（第 2、4 声号角后 `给` 4250 的兵：3 守护者 + 4 维和 + 2 标枪，在 `entry`）。
   - **④checks/a4.py**：换成 `horn`（号角出兵数）、`detour`（冻一条街，那波在开着的街晚到）、`queue`（冻住的口子攒兵、墙没了放出）、`smash`（鬼王砸墙）；`derrick` 不变。每条一个最小场景，别复制旧 `idle/hold/win`。
   - **试玩缺什么（汇报用）**：音乐线 `experimental/music/*` 未提交且在等用户听 v5；配音线还没交 A4 台词（`RA3-ChineseVoice/work/campaign/zh/A4/manifest.json` 不存在）；单位外观（工兵/鬼王/冰墙/地道口布景）用替代品；舞台、金奖牌、地道口布景没做。
   - **适合派 Sonnet 的**：②②之后"照现成样子"的检查批量改；`test_sapporo` 加断言（间距 ≥ 800、绕路差 ≥ 10）。②本身（新机关）和③（计划）自己做。

1b. **（旧说明，留作出处；落地方案看上面 1c）第 2 步，A4 的摆放和脚本按新流程稿重做。** 读 `docs/design/cards/a4-layer3.md`（地图要改、脚本表、要测的）、`docs/design/flow/a4.md`、`docs/design/maps/a4.md`。还没动手，要做的东西和落点：
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
