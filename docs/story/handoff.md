最新进度看 [handoff-phase4.md](handoff-phase4.md)（前一份是 [handoff-phase3.md](../archive/level-handoff-phase3.md)）。

# 关卡线交接（早期，2026-10-30～11-04；已瘦身，只留仍有效的坑、工具用法和被别处引用的章节）

已结束切片的过程、日志、提交号都删了（git 有历史）。ADR 0022～0026 之后关卡暂停、引擎优先，下面的"下一步"类计划不再有效。事实以指到的文件为准。

## 我是谁、管什么

关卡线：`docs/story/`（outline、levels、plans/、map-language、units）、`experimental/cnv/`（单位外观接线除外）、模拟器（sim.py、simstatic.py、simchecks.py、simunits.py）、offline.py、platmap/platprops、terrainref。
不是我的：`docs/plan.md`（总控）、`docs/design/`（设计线，机制结论可写进 `docs/design/flow/mechanics.md`）、音乐线文件（`experimental/music/*`、`docs/music/handoff.md`、`missions/music_dyn.py`）、`experimental/voice/*`（配音线）。外壳后来拆给外壳线（见 [shell/handoff.md](../shell/handoff.md)）。
规矩：根目录 `CLAUDE.md`；mod 名 ≤15 字符不带下划线；不 cd 进子目录；交给用户检查的只列真问题。

## 已有的能力（不用再查，细节在指到的文件里）

- NOT 条件 `parts.unnot`；模拟器对齐 `sim.py --align`；A4 离线检查 `experimental/cnv/offline.py`。
- 配音接线：任务带 `voice` 包，`CNV_` 开头的声音名必须在包里（`parts.py` 的契约）；细节见 `experimental/cnv/checks/voice.py` 顶部注释。
- 灰盒（ADR 0011）：`experimental/cnv/graybox.py`、`graybox_cards.py`，结论在 [graybox-cards.md](graybox-cards.md)。新题卡往 `graybox_cards.py` 加函数、往 `graybox-cards.md` 加一节；判断不了的写"留给实机"。
- 引擎机制最小检查（冰面承重只能脚本做、干扰车对飞机有效、小地图闪点按物体、信息框当字符条）：结果在 [drive-probe.md](../archive/drive-probe.md) 末节和 [../design/flow/mechanics.md](../design/flow/mechanics.md)。

## 1a 引擎事实：鬼王、数冰墙、找最近的墙（结论已写进 mechanics.md，PASS）

- 鬼王自己不砸墙，脚本 `NAMED_ATTACK_NAMED(鬼王, 墙名)` 下令才砸，一道墙约 16～24 秒。
- 区域里数冰墙：`PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA`。
- 找最近的墙：`SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER`。**写法要点**：墙一起名就不再算"没起名的"，要拿一面旗记"名字指着东西"，墙毁了才放旗再选；从没起过的名字"已毁""没毁"都是假。样子照抄 `checks/icewall.py` 的 `ghost`。用传送把鬼王挪过去再选，顺序对不上（没查原因）。

## 1b 号角机关与 A4 现状（旧方案已被实现取代，只留指针）

- A4 机关 `devices/horn.py`（计划里叫 `雪祭`），车队 `devices/convoy.py`，计划 `docs/story/plans/a4.md`（词表 `plans/README.md`），地图 `maps/sapporo.py`（测试 `tests/test_sapporo.py`，改完先 `cnv_preview a4`）。
- 整关检查 `checks/a4.py`：`horn detour queue smash demo hold idle win melt heads smoke signs place placem derrick`；测试台读数的计时靠 `AFTER`（过场结束旗 `CNV_A4_Scene_1`）。已知：`smash` 在 x8 读数全 0（x1 手看正常，没查清）；`placem` 没跑；后巷口（V1）冰核放不出（见 `docs/issues.md` I3）。
- 数字（号角间隔、每街一波、绕路秒数、补兵 45 秒、车速 12）是起步值，等实机反馈调。

## 1f 两个版本与配音路由（ADR 0013）

- 构建：`python -I -X utf8 experimental/cnv/build.py a4 [--lang intl]`（名字 `a4` / `a4_intl`）。逻辑全在 `experimental/cnv/langs.py`（文件顶有接口说明）；每句用哪条音频、哪条字幕问配音线的 `RA3-ChineseVoice` `tools/campaign_lines.py route <关> --version zh|intl`（接口在它的 `docs/campaign_voice.md` 第 7 节，在配音线仓库里）。
- 缺的句子不静默：构建开头打印 `MISSING`（只有字幕没录音等几类）；计划自己的字符串英文在 `docs/story/plans/a4.en.json`；`tests/test_langs.py` 守着。
- 原版播报（`Aeva_...`）编译成 `PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT`，构建时用 `voice_link.Later.eva()` 核对。
- 测试台名字不超过 15 字符（`CampA4EnHold` 等）。游戏里的声音测试台听不到，要用户试玩。

## 1g 任务脚本能播自己做的视频（2026-11-01，`cnv_check movie play` PASS）

- **进 mod**：和原版一样两处声明（`<Video id=X Filename=X Volume=190/>` + 同 id 的 `<VideoEventList>` 里 `<Movie MovieAsset=X/>`，`experimental/video/pack.py`）；片子 `X.vp6` 放进 mod 的 .big，路径 `data\movies\X.vp6`，不往游戏目录放文件。脚本 `MOVIE_PLAY_RADAR('X')` 小窗、`MOVIE_PLAY_FULLSCREEN('X', 0)` 全屏。
- **转码**：ffmpeg 不能编 VP6，用 NihAV 的 nihav-encoder（已编好，Rust 在 `~/.cargo`，源码快照在 `work/downloads/nihav/`；`git://` 连不上，用 gitweb 的 https 快照）。一条命令：`python -I -X utf8 experimental/video/to_vp6.py in.mp4 out.vp6 --size radar|full`（小窗 288×288、全屏 1280×720 留黑边、23.976 fps；输入宽高必须是 16 的倍数）。
- **原版片子格式**：`MVhd` + `MV0K` + `MV0F`，**没有音频块**，声音是脚本另配的对白事件；所以我们的片也无声，声音走语音包。
- **坑**：①`HAS_FINISHED_VIDEO` 对小窗片成立、对全屏片一直不成立（全屏靠定时器）；②全屏时计数条被盖住，读数读不出；③小窗放片子时小地图被替换，播完恢复；④测试台不出声，没验 Esc 能否跳过全屏片。
- 接进计划：顶层 `头像: [CNV_A4_…]`（只放玩家不用看地图的句子，不写名单就没有头像，见 `plans/README.md`）；`experimental/cnv/clips.py`：录音旁 `video/<同音频名>.mp4` 存在就转 vp6、同句小窗播；头像画面/嘴型/同步没人看过。代码：`parts.py` 的 `Mission.video`、`missions/movie_bench.py`、`checks/movie.py`、`tests/test_video.py`、`tests/test_clips.py`。

## 配音叠播的真根因（4、7 叠播的真根因 ②；ADR 0015 第 1 类）

- 规则的 `做:` 列表编译时整串同一帧发出，"顺序播"只在 `过场` 里实现过；旧检查（单关、x8、只数读数器）永远抓不到。
- 引擎把配音排队播，但**字幕条**（`SHOW_MILITARY_CAPTION` 和对话字幕共用）是累积的日志：新句追加一行，**最后一句加入后约 5.4 秒整条一起清空**，与字幕秒数无关（`r3_fine*` 一秒一帧测的；`work/shell/shots/r3_before/`、`r3_fine3/`）。原版没有清字幕条的动作。
- 现做法：过场外所有 `通报` 走唯一队列出口 `Compiler.say()`/`compile_talk()`（`Say k` 脚本占住话筒 `max(录音长度+0.6, STRIP_CLEAR=6.5)` 秒）；配音事件不带自带字幕（`pack.py xml(subtitles=False)`），由脚本按录音长度显示字幕；过场里 `scene_steps` 也按 `STRIP_CLEAR` 一句一句排，过场因此变长（会场过场实测超 2 分钟）。测试 `tests/test_plan_lines.py`、`tests/test_plan_scenes.py`。复验用 `experimental/testbench/caption_rows.py <目录>`（每帧黄字行数应 ≤1），`shell_shots.py --hud-wait 150 --every 1`。
- 过场不能跳：`DISABLE_INPUT` 的过场不认 Esc，脚本里没有按键条件和跳过动作，原版同样，只能缩短。

## 画面和台词对照表（用户 2026-11-03 说"画面和台词也有不统一的时候"；`docs/issues.md` I2 引用本节）

只读计划核对，没上游戏看。过场镜头和台词基本对得上；可疑五处：
- `雪祭.号角 1 + 0:08` 的"二号广场的冰雕也裂了"：玩家镜头不一定在二号广场，没挂镜头。
- "金奖两句"在倒计时过半或走近三号广场触发，时间触发时玩家可能没看三号广场。
- 过场里"看见没有？他们只认车"在 `停 9` 之后，兵转向/下地道是否已发生没验。
- 科尔通讯（基地车展开半分钟后）没有画面可挂。
- 原版播报"冰墙已就位/即将融化"挂事件没挂位置。
ADR 0015 第 2 类要求编译器拒收没挂镜头/事件的台词（I2，已有 `said_lines_kept` 检查，见 issues.md）。

## ADR 0015 七类错误里本线的做法与没验证的（修了待验的以 `docs/issues.md` I1–I9 为准）

- 车队（第 9 条）：`分批 [0,50,110]` + 失败条件 `车队.损失 2` 会让第二辆还在等；`devices/convoy.py` 现在任一辆被毁后其余等待的车立刻全部出发（`Release k after truck i lost`），没在游戏里杀一辆验证。
- 开场黑区：新站点 `view start`（x=1000），会场过场首尾镜头用它；"编译时把所有镜头夹进可玩区"没做。
- 演示：兵遇冰墙先走回出兵口再钻地道消失（`horn.py demo_scripts`，`Demo down`），没进游戏看。
- 矿：A4 的矿点按"成对贴矿场"猜的，要用 `retail_objects`/`map_study` 对原版摆法；`cnv_map` 不画矿，矿看 `cnv_preview a4` 的图。
- 冰墙放置：玩家点的是 `AssembleStructureSpecialAbilityUpdate` 放"冰核"（`units/icewall.py seed`，`SEED_SIZE=20`），技能 `ForbiddenObjectRange=32`、`PATHABLE_ONLY`；旧检查用脚本直接放，不走放置合法性。新检查 `a4 --check place`：用 `bench_view`（脚本镜头下点位在屏幕 (640,350)）+ `bench_click` + `bench_ability`，要用 bench 环境的 python 跑 `experimental/testbench/run_check.py a4 place`（`--no-build --keep --x1`；x1 过场 110 秒会被"连接中断"弹窗拉回主菜单）。x8 下点击让游戏跑约 29 秒，所以用锁存读数。源头修法（生成器保证冰点周围平地、可走、无物件，并进 lint）没做。
- 过场镜头自动揭图（`plan.py scene()`，`不揭: 是` 关掉）；头像去掉 `CNV_A4_082`；A4 地面草/土换雪（`sapporo.py SNOW`）；冰核 40→20（推测，没在游戏验证）。

## 1 ADR 0016 重构（关卡部分）留下的坑

交接在 [handoff-phase3.md](../archive/level-handoff-phase3.md)。已做：`cnv/plantime.py`（`PlanError`/`times` 等，`plan.py` re-export）、`cnv/registry.py`（扫 `missions/`、`checks/` 里的 `MISSION`/`CHECKS`/`PAIR_BUILDS`；`build.MISSIONS/PAIRS` 是它的视图）、`cnv/ctx.py`（机关只拿 Ctx，不再有 `self.c/self.m`）。
- 基线只信指纹：`python -I -X utf8 experimental/testbench/fingerprint.py record <名>`（约 8 分钟，跑时别改源码），`diff baseline` 三目标一致；`git archive`/`git worktree` 在仓库外解出的树跑 `sim.py a4` 结局不同，别当基线；`self.c.xxx` 遗漏要到运行才报 NameError，改完做一次 symtable 检查（函数里引用但模块没定义的全局名）。
- `tests/test_architecture.py` 的 G4（sys.path 上限只降不升）、G9、G3a 白名单；不能新建带 `sys.path.insert` 的测试文件；混着别人未提交改动时只暂存自己的函数（`git hash-object` + `update-index --cacheinfo`）。
- `plan.py` 和多数源文件是 CRLF，批量改写要保留换行风格；`sed -i` 往 .py 塞 `\r\n` 会弄坏文件。

## 外壳（已拆给外壳线；这里只留以前搜"外壳""CampShell"的人需要的坑；`docs/shell/handoff.md`、issues.md K9 引用）

- 构建：`python -I -X utf8 experimental/cnv/build.py a4 --shell [--lang intl]`（`cnv/shell.py` 管一切；`make_campnew2.SHELL` 以原版 `Allies_1` 为底、盟军 9 个位置全是我们的模板；`make_campnew3.OVERRIDES/PREFIX_OVERRIDES` 改字符串；`campaign/apt_textures.py` 改 APT 贴图/脚本常量）。mod `CampShell`、`CampShellEn`；启动器 `experimental/cnv/launcher.py`、`play.hta`（中文/国际两个按钮，选择存 `Mods\CampShell\last_edition.txt`）。
- 测试台走菜单：`experimental/testbench/shell_shots.py <mod> <输出目录> [--plain] [--tour cards,overview,chapters] [--slot K] [--every 秒] [--hud-wait 秒]`。
- APT 画面换贴图可行：换原版流的 `Texture:apt_*` 实例像素、其余字节不动，放进 mod 的 big 的 `data\aptui\<名>.bin`；带 `.5` 补丁的 `fes_m_factionmenu` 只换基础 `.bin`。阵营卡文字是 `APT:ALLIES_FACTION_DESCRIPTION`。
- 副指挥官面板去干净：21 条 `MONITOR:*` 标签覆盖成空格 + `apt_textures.hollow(.., renames=)` 把 `AptConstData` 里的 `RenderImage` 改成同长度 `RenderImagx`。**坑**：改 `AptAptData` 里的会进游戏就崩（0xC0000005）。
- 简报旁白事件 `MA0k_AlliedIntelNN` 在 APT 里写死，`apt_textures.patch(..., renames=)` 同长度改名成不存在的事件，字幕标签在 csf 里。
- **坑**：①游戏启动后约 40 秒弹一次"连接中断通知"并把游戏拉回主菜单，`shell_shots.py settle()` 先等它过去；`harness._walk_menus` 步骤表必须完整才能从主菜单重新接上。②mshta 窗口里 `PrintWindow` 截不到内容，只能 `CopyFromScreen`，且先 `SetProcessDPIAware`；别整屏截图。③HTA `border="dialog"` 不让 `resizeTo`，用 `thin`。④阵营选择屏用标题栏模板认（`work/testbench/nav/`，不进 git）。⑤偶发启动成 800×600，重试就好。
- 没做：章节页上方三个小阵营图标、任务播报页的原版指挥官概要（`AICommander`）、缩略图其余关、两个全屏视频/头像都无声。用户原话："原本的测试启动器也去掉吧，我们只维护一个mod就行了"——老启动器已删；Mods 里旧的测试台单关 mod 都留着，清理由总控定。

## 还没测的

走近就归你（平民建筑转给玩家）；A4 plaza 3 的接力冰；J4 返工（车停下来、人活着）；A7 友军 AI 重查。J4/J7/S5 的游戏内标题还是旧名，等这几关重做时改。

## 踩过的坑

- 实测前先查 `bench_status`，用户的游戏在跑就停下问，不要重试。装进 Mods 前也单独查游戏没在运行；下载要用户本人说。
- 长检查放后台，输出写 `work/logs/`，屏幕只看 `PASS|FAIL|RESULT`。
- 测试台启动会跳过开场过场，首帧已在任务约 40 秒；Esc 暂停在过场里失败会被当成"任务结束"；读数器会把连续相同数字并成一个（用位值互不相同的闩锁）；`cnv_check` 偶发菜单卡住（`build=false` 重试）；读数条要在黑底上才读得出，标签里别用"一"这种一横的字和全角括号。
- 测试台一个检查最多 4 行读数（`counters.MAX_LINES`），第 4 行读不准，要紧的放前三行；`cnv_list` 输出几百行，用 Grep 查 `build.py`；`bench_wait(look=false)` 之后 `bench_look` 看到的是旧帧；镜头移动在任务里要 1～7 秒，看有时限的东西要在检查里让它循环出现。
- 钩子 `guard_inline_edits.py` 拦带反斜杠的 heredoc / `python -c`：改文件用 Edit/Write。
- Bash 工具里 `cd` 会让工作目录漂，一律用绝对路径；停测试游戏用 PowerShell 按 pid 杀，别碰不是自己起的进程。
- 配音包会拿 SDK 构建锁，同进程里已重入不再卡死。
- 检查里需要"脚本才创建的单位"时，基础任务也要有一个放好的对象，否则契约测试 `test_every_build_keeps_the_contract` 失败（做法：远处放一个，检查里杀掉再创建，见 `ghost`）。
- 音频脚本帧数（约 44 帧/音频秒）和计时器帧率（约 15/秒）对不上，别把音频帧数换算成任务秒（`docs/engine/script-semantics.md` 第 11 条）。
