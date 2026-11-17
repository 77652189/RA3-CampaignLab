# 音乐线交接

会话："游戏音乐生成系统"。进度状态只在 [plan.md](../plan.md)「游戏音乐」那一行，这里不重复。为什么自己逆向 Pathfinder 见 [ADR 0005](../adr/0005-own-pathfinder-music.md)。过程细节（五版配乐的迭代、录音实测、提交）在 git log。

## 当前目标

A4 配乐已接进 A4 关卡并提交；等用户在关卡线装的试玩版里听过后给反馈（用户 2026-10-26："第二版可以，接进 A4 关卡 mod，进游戏验证优劣势切换"）。当前项目阶段（2026-11-08）引擎优先，关卡暂停推新内容，亲手试玩改在游戏里。

已经定下、不用再讨论的：
- 作曲路线：代码写谱，自己的合成器 + 采样出声（用户 2026-10-26 定）。谱面 `experimental/music/a4.py`，音色 `synth.py`（纯 numpy）、`sampler.py` + `sf2.py`（真乐器采样，库在才用，没有就退回合成器）。
- 接口：关卡通过 `parts.Mission.music` 带音乐（`pack.py`）。计划里的用词（`音乐: a4` / `音乐 <提示词>` / `战况音乐 开`，胜负由编译器自动接收尾）由我们实现，内容会话审过。

## 下一步

1. **等用户听 A4 配乐后的反馈**，要问四件事：像不像红警 3、合唱听不听得出来、哪段刺耳或太吵、激战曲打完后会不会一直拖着不停。反馈来了按意见调 `a4.py`，跑 `tests/test_a4music.py`、`tests/test_sampler.py`，再提交。
2. **"扳回来"**（可放在 A4 反馈之后）：24 辆援军打赢了，游戏仍不发 `ResetAdvantage`，劣势段一直放到平息。条件（SDK `DisadvantageCombat_to_EvenCombat_Allowed`）：进劣势满 20 秒，且 20 秒内我方击杀 ≥ 损失 × 2、击杀 ≥ 3。猜测：援军到场时 16 个维和步兵还在大批阵亡，比例不够。做法：让援军直接在交战点出现、或等维和步兵死光再到（`music_dyn.py` 的 `HELP_AT` / 出生点），`build.py musicdyntr` 再录一次；还不发就自己写一个状态组（PathMusicGameDynamicStateSet）放进 `pack.include` 的 XML。
3. 可选改进（要先和关卡线商量）：真实对局里若"激烈段"拖得别扭（伏兵太少，游戏不进交战状态、不发平息，约 14 秒），加提示词 `平息`，让关卡在车队到 `approach 2` 时触发；布防段开场也可加 `音乐 布防`。
4. 发布时要带上 `MuseScore_General_License.md`（MIT 要求随衍生作品附版权声明）；VSCO 部分是 CC0，不要求署名。

## 现状要点（A4 接线，计划 `docs/story/plans/a4.md`）

- 会场开场 `音乐 布防`；北营开场 `音乐 港口` + `战况音乐 开`；最后一程开场 `音乐 最后一程`；二号广场冰雕裂开 `音乐 伏击`；港口生变（过场）和布防段接着放当时的曲子。提示词用 a4 现有的 `CUES`，不用改配乐代码。
- 听辨版：`CNV_MUSIC_CAPTIONS=1 python -I -X utf8 experimental/cnv/build.py a4`，每个提示词同时在屏幕计数器显示"音乐：<提示词>"；游戏自己发的战况切换显示不了。装进 Mods 由关卡线统一做。
- 大厅、简报、结算用原版音乐：`a4.SHELL` 四个界面事件走 `ownmap.Builder.keep`，把原版节点和 58 条原版曲子搬进我们的图（`extract.retail_streams`）；原版第 1 轨（Track_Mem）是叠在主音乐上的短插曲，不能拿来放我们的曲子。
- 混音按原版同类曲子校正（`synth.match`，目标数字 `a4.REFERENCE`，`a4.py reference` 量出；对照曲 `a4.REFERENCE_STREAMS`）；合唱音量 `a4.CHOIR_GAIN`，`test_the_choir_is_heard` 守着。采样库没有时 `a4.RECORDED` 里的声部不写。
- 编译日志只打印含 `CNV` 的脚本行，换曲指令不会出现在日志里，不是丢了；要核对就把计划编出来列 `PATH_MUSIC_*`。
- 整关曾在游戏里录过（布防→伏击→激烈→港口→最后一程→胜利，按设计切换）；战况（劣势、平息）在测试关 `musicdyntr` 里验过，A4 整关里仗太小没出现。关卡线后来改了后半段（要清港口、拆北营兵营和战车工厂才进最后一程），整关录音前要重编。

## 已经实测的引擎规则

- 音频：EA-XAS，22.05 kHz 单声道和 44.1 kHz 立体声都行；条目编号和校验码用我们自己的（`mus.pack`）。
- 跳转：带 PREP 立刻切；不带的等当前小段放完（每小段 2 小节、5 秒），再走路由表过渡；路由表里没有目标就直接去。路由值 v 对应 `routers[v-1]`。**路由偏移表必须多写一项表尾**（原版 132 个偏移、131 张表），不写引擎会丢最后一张表（`pfdx.build` 已补）。
- **脚本只能触发 SDK 脚本事件表里的事件**（`SageXML/PathMusic/ScriptPathMusicEvents.xml`），不在表里游戏不认；`test_every_cue_is_an_event_a_script_can_fire` 守着。
- 战况：状态组 `Standard_NoLeadIn`（测试关 CampMusDyn / CampMusDynS）。门槛在 SDK `StandardPathMusicGameDynamicState.xml`：每状态至少待 20 秒；劣势＝20 秒内击杀比 ≤ 0.5 且敌方击杀 ≥ 3；优势＝2 分钟拆 5 座重要建筑，护送关里碰不到，所以 a4 把均势、优势都接到激烈段。12 辆援军打赢了游戏也不发 `ResetAdvantage`（见下一步 2）。
- 我们所有地图的地图流里带着海德堡关的 BaseBuilding / ThreatLevel1 / ThreatLevel1_1 状态，所以游戏发的是 `S_A03HeidelbergThreat1` / `_1`；`a4.EVENTS['calm']` 已按这个名字接，`CALM_TOO` 是保险。
- 曲谱图变量有效：借原版变量 3（`a05incoming`，`a4.PHASE_VAR`），事件里 SET，平息事件里 IF / ELSE。
- 录音：游戏会话音量压到 0.0001（-80 dB，用户 2026-10-26 要求录音时听不到），`proc_capture` 浮点采集、放大后写 16 位。

## 试过、没采用：MiniMax Music 3 文生音乐（2026-11-08）

结论：替代不了 `synth.py`。脚本 `experimental/music/music3_probe.py`，产物和报告在 `work/music/music3/`（`report.txt`、`vocals.txt`、`compare/`）。
- 6 段（激烈 3、布防 3，各 40 秒）都生成成功，每段 9.5～12 分钟，显存约 8～10.6 GB。
- 不听拍号：写 96 拍测出 83～142 拍，节拍漂 100～170 ms（a4 是 5～51）；自带前奏渐强。
- 切不出无缝循环：最好接缝 5.9～11.7 dB（a4 是 0.7～3.7）；频谱离原版 7.8～32.7 dB（a4 < 4）；写了"不要人声"仍有 1 段在唱。
- 许可：社区许可可商用，但产品界面要显著标"MiniMax-Music3"，年收入超 2000 万美元要另授权，公开内容要注明机器生成。模型留在配音线 ComfyUI 的 models 里（约 14.3 GB）。

## A4 配乐的写法

规矩都在 `a4.py` 开头：
- D 小调，96 拍每分。每小段 2 小节、5 秒，这是不带 PREP 的跳转最多要等的时间。
- 卡准时机的剧情点（伏击、港口、胜负）用带 PREP 的事件。
- 过渡段写在路由表里，开头要和上一段一样响。
- 帝国用筝、三味线、尺八、太鼓；盟军用圆号进行曲主题，赢的时候加摇滚鼓、失真吉他、合成器。
- 整关流程的频谱要和原版相近。我们自己听不到，所以靠测量：各频段能量、段落交界处响度、循环接缝。
- 用户对第二版的批评（"和原版风格差异很大"）已逐项量过并改进：低频、高频、声像、动态、打击乐占比、循环长度；剩下最大差别是音色（原版是录音的管弦乐队，我们是采样 + 合成）。

## 必读

- 格式：`experimental/music/pfdx.py` 和 `mus.py` 开头（以代码为准）；`ownmap.py`、`a4.py` 开头。
- 关卡接口：`experimental/cnv/parts.py` 的 `Mission.music`、`contract`；`plan.py` 的 `load_music` / `cue`；`docs/story/plans/README.md` 的"一关的各部分"和"动作"表。
- 原版状态机：SDK `SageXML/PathMusic/` 下的 `StandardPathMusicGameDynamicState.xml`、`ScriptedPathMusicGameDynamicState.xml`、`PathMusicEvents.xml`。脚本动作见 `experimental/campaign/script_catalog.json` 的 `PATH_MUSIC_*`。
- 注入：`experimental/campaign/splice_assets.py` 开头（为什么要拼进 static 流）。
- 剧情：[outline.md](../story/outline.md) 第四节、[plans/a4.md](../story/plans/a4.md)「节拍」。
- 采样库来源：`experimental/music/fetch_samples.py`（VSCO-2 CC0，`work/music/vsco2`；MuseScore_General.sf2 MIT，`work/music/musescore`；下载要用户同意）。
- 本地数据（不进 git）：`work/music/retail/`（原版曲谱图、wav、指纹、`event_hashes.json`）；`work/music/a4/`（试听页、`streams/`）；`work/music/probe/`（录音和报告）。

## 验证方式

- 离线：`python -m pytest tests/test_pfdx.py tests/test_mus.py tests/test_tracer.py tests/test_ownmap.py tests/test_a4music.py tests/test_sampler.py tests/test_plans.py`。全部：`python -m pytest -q tests`。
- A4 样品：`python -I -X utf8 experimental/music/a4.py`，约 25 秒，输出到 `work/music/a4/`。
- 游戏里：`python -I -X utf8 experimental/music/bench_listen.py --nav <任务秒数> <录音秒数> <skudef>`。只出文字报告；录音时会一直告诉游戏"你在前台"，否则它不放音乐；`tracer:` 行的 stream 号就是曲谱图的流号；任务开始时间看报告里第一段属于任务的示踪音，菜单的 NAV 时间不准。
- 认我们自己的音乐：`python -I -X utf8 experimental/music/a4.py heard <录音.wav>`。我们的曲子在录音里约 -55 dB、votes 偏低，激烈段和最后一程会认混，要确证就用示踪音版。

## 坑

- **在锁里编 mod 要确认编译跑完**（输出有 `PLAN` 行、写进了 Mods），否则游戏跑的是旧 mod，录音白录。`CampA4Win` 和关卡线 win 检查同名，用之前重编。
- 测试台按锁排队（`run_bench.ps1` 自己拿锁，见锁就放弃、不排队）：用之前先约，用完回一声；开跑前锁空了也再等几秒；单独查红警 3 有没有在运行。游戏在运行时编 mod 会自动写到 `work/staging`。
- 提交只暂存音乐线自己的文件；`build.py`、`plan.py` 两边都改，用补丁只暂存自己那几块（这里 `git add -p` 不能交互）；`build.py` 只用 Edit 改，不要整文件覆盖。
- mod 名字不超过 15 个字符，只用字母和数字。
- 长时间显卡任务开跑前先问用户要不要限流；下载模型要用户同意。

## 分工

- 总控管路线、接口、审查和 `docs/plan.md`（**plan.md 只由总控改**，音乐那一行的进度发给它）。关卡线管策划案、`plan.py`、`build.py`，要改先找它说好，涉及接口的抄送总控；地图线改 `experimental/cnv/maps/`。
- 音乐线自己的改动由音乐线提交（按仓库规则做完、测过就提交）。

## 硬约束原文

- 用户 2026-10-25（选路线 B 时）："代码开源还是不要抱多大希望，靠自己做出来的才是可靠的"
- 用户 2026-10-25（提需求时）："作为游戏音乐，你的创作最需要做的是符合剧情和情景，好的音乐对营造氛围感来说是至关重要的"
- 用户 2026-10-26（听完第一版）："风格不太像红色警戒3，前面的神秘感营造的很好，但是交战的时候音乐应该表现出紧张（处于劣势）和激烈（处于优势），而且带有阵营的特色"
