# 音乐线交接

会话："游戏音乐生成系统"。进度状态只在 [plan.md](../plan.md)「游戏音乐」那一行，这里不重复。为什么自己逆向 Pathfinder 见 [ADR 0005](../adr/0005-own-pathfinder-music.md)。

## 当前目标

把 A4 的配乐接进 A4 关卡 mod，并在游戏里验证优劣势切换（用户 2026-10-26："第二版可以，接进 A4 关卡 mod，进游戏验证优劣势切换"）。

已经定下、不用再讨论的：
- 作曲路线：代码写谱，用我们自己的合成器出声（用户 2026-10-26 定）。谱面在 `experimental/music/a4.py`，音色在 `synth.py`（纯 numpy，无采样）。
- A4 第二版用户已认可。
- 接口：关卡 mod 通过 `parts.Mission.music` 带音乐（`pack.py`，2026-10-25 和内容会话商定）。策划案用词由我们实现，内容会话已审过 diff。

## 接手时的状态

音乐用词（`plan.py` 的 `音乐:` / `音乐 <提示词>` / `战况音乐 开` / 胜负先放收尾）、A4 第二版（`a4.py`、`synth.py`）、`ownmap` 的变量和条件、音乐测试关 musicdyn / musicroute 已提交（用户 2026-10-26 同意）。

同一工作区里关卡线也在改文件（`a4.md`、`checks/a4.py`、`devices/` 等）：提交时只暂存音乐线自己的文件；`build.py`、`plan.py` 两边都改，用补丁只暂存自己那几块（这里 `git add -p` 不能交互）。`docs/plan.md` 归总控。

## 下一步

1. **查清引擎的路由规则**：先编 `python -I -X utf8 experimental/cnv/build.py musicroute`，已经编好在 Mods 里，再跑 `bench_listen.py --nav 175 185 <CampMusRoute 的 skudef>`。
   - 场景写在 `missions/music_route.py` 开头。读 `tracer:` 行，stream 号对应 `music_route.streams()` 的顺序：P1 0-1、P2 2-3、F 4-5、G 6-7、E 8-9、X 10-11、Y 12-13，过渡 14 起。
   - 预期顺序：离线 `ownmap.timeline(...)` 算出的结果。前提是"待跳转"走完一次就清掉，按这个前提 F / G 会一直在自己身上循环。
   - 要回答的问题：起点段落的路由表里没有目标时（P1 → F，P1 → G），目标段落放完第一小段后去了哪里？是跟着 F / G 路由表里某一条的位置走，还是跟着 b 值走？
   - 起因：CampMusDynT 里，`Combat`（不带 PREP）从布防跳进激烈段，激烈段只放了一小段，没有新事件就直接进了"最后一程"，没放过渡。最后一程是激烈段路由表的第 2 条。
2. 按结果修 `a4.music_map`。可能的修法：
   - 每个会被"不带 PREP 的跳转"离开的段落，路由表里都写全它能去的目标；
   - 或者战况事件改用 PREP；
   - 结果写进 `pfdx.py` 开头的 PREP / routers 说明，并补 `ownmap.timeline` 和测试。
3. **再跑战况测试关**：`build.py musicdyn`，再 `bench_listen.py --nav 240 250 <CampMusDyn skudef>`，最后 `a4.py heard <录音>`。
   - 援军已加到 24 辆，看游戏这回发不发 `ResetAdvantage`（我方扳回来）。要发的条件：进入劣势 20 秒以后，20 秒内我方击杀至少是损失的 2 倍，且至少 3 个。
   - 要是还不发，考虑自己写一个状态组（PathMusicGameDynamicStateSet），放进 `pack.include` 那份 XML。
   - 听不出段落的时候，用 musicdyntr（a4 曲谱图配示踪音）或 musicdynspy（每个事件一个示踪音）定位。
4. **接进 A4 策划案**：先找关卡线说好，抄送总控，关卡线正在改 `a4.md`。
   - 顶层写 `音乐: a4`。
   - 布防开场写 `音乐 布防`。
   - 第一程开场写 `音乐 行进` 和 `战况音乐 开`。
   - 规则 `{当: {任一: [广场.伏兵出来 1, 广场.伏兵出来 2, 广场.伏兵出来 3]}, 做: [音乐 伏击]}`（内容会话给的写法）。
   - 港口生变开场写 `音乐 港口`，最后一程开场写 `音乐 最后一程`。
   - 最后进游戏完整录一遍。
5. 提交前问用户。

## 已经实测的（2026-10-25～26）

- 音频：EA-XAS，22.05 kHz 单声道和 44.1 kHz 立体声都行；条目编号和校验码用我们自己的（`mus.pack`）。
- 跳转：带 PREP 立刻切；不带的等当前小段放完，再走路由表的过渡（CampMusic）。路由值 v 对应 `routers[v-1]`。
- 战况（测试关 CampMusDyn / CampMusDynS，状态组 `Standard_NoLeadIn`）：
  - 任务第 26 秒：小规模接触。第 45 秒：`Combat`。第 65 秒：`SetAdvantageEnemy`。第 142 秒：战斗平息。
  - 12 辆援军打赢了，游戏也没有发 `ResetAdvantage`。
- 我们所有地图（A4 也是）的地图流里都带着海德堡关的 BaseBuilding / ThreatLevel1 / ThreatLevel1_1 状态，所以游戏发的是 `S_A03HeidelbergThreat1` / `S_A03HeidelbergThreat1_1`，不是通用的 Threat1 / Threat1_1。`a4.EVENTS['calm']` 已按这个名字接，`CALM_TOO` 是保险。
- 曲谱图变量有效：借用原版变量 3（`a05incoming`，`a4.PHASE_VAR`），事件里 SET，平息事件里 IF / ELSE。平息以后经过渡回到行进段（CampMusDynT）。
- 原版战况的门槛在 SDK `SageXML/PathMusic/StandardPathMusicGameDynamicState.xml`：
  - 每个状态至少待 20 秒才能离开。
  - 劣势：20 秒内击杀比 ≤ 0.5，且敌方击杀 ≥ 3。
  - 优势：2 分钟内拆掉 5 座重要建筑，护送关里基本碰不到，所以 a4 把均势、优势都接到激烈段。

## A4 配乐的写法

规矩都在 `a4.py` 开头：
- D 小调，96 拍每分。每小段 2 小节，5 秒，这是不带 PREP 的跳转最多要等的时间。
- 卡准时机的剧情点（伏击、港口、胜负）用带 PREP 的事件。
- 过渡段写在路由表里，开头要和上一段一样响。
- 帝国用筝、三味线、尺八、太鼓；盟军用圆号进行曲主题，赢的时候加摇滚鼓、失真吉他、合成器。
- 整关流程的频谱要和原版相近。我们自己听不到，所以靠测量：各频段能量、段落交界处的响度、循环接缝。

## 必读

- 格式：`experimental/music/pfdx.py` 和 `mus.py` 开头（以代码为准）；`ownmap.py`、`a4.py` 开头。
- 关卡接口：`experimental/cnv/parts.py` 的 `Mission.music`、`contract`；`plan.py` 的 `load_music` / `cue`；`docs/story/plans/README.md` 的"一关的各部分"和"动作"表。
- 原版状态机：SDK `SageXML/PathMusic/` 下的 `StandardPathMusicGameDynamicState.xml`、`ScriptedPathMusicGameDynamicState.xml`、`PathMusicEvents.xml`。脚本动作见 `experimental/campaign/script_catalog.json` 的 `PATH_MUSIC_*`。
- 注入：`experimental/campaign/splice_assets.py` 开头（为什么要拼进 static 流）。
- 剧情：[outline.md](../story/outline.md) 第四节、[plans/a4.md](../story/plans/a4.md)「节拍」。
- 本地数据（不进 git）：
  - `work/music/retail/`：原版曲谱图、wav、指纹、`event_hashes.json`。
  - `work/music/a4/`：试听页、各段，`streams/` 是各段音频和指纹，`a4.py heard` 用。
  - `work/music/probe/`：录音和报告，`musdyn_*.txt`。

## 验证方式

- 离线：`python -m pytest tests/test_pfdx.py tests/test_mus.py tests/test_tracer.py tests/test_ownmap.py tests/test_a4music.py tests/test_plans.py`。全部：`python -m pytest -q tests`。
- A4 样品：`python -I -X utf8 experimental/music/a4.py`，约 25 秒，输出到 `work/music/a4/`。
- 游戏里：`python -I -X utf8 experimental/music/bench_listen.py --nav <任务秒数> <录音秒数> <skudef>`。
  - 只出文字报告。录音时会一直告诉游戏"你在前台"，否则它不放音乐。
  - `tracer:` 行的 stream 号就是曲谱图的流号。
  - 任务开始时间：看报告里第一段属于任务的示踪音，菜单的 NAV 时间不准。
- 认我们自己的音乐：`python -I -X utf8 experimental/music/a4.py heard <录音.wav>`。激烈段和最后一程听着像，会认混，要确证就用示踪音版。

## 动手前

- 分工（用户 2026-10-26 定，按线分会话）：
  - 总控（原内容会话，"红色警戒3 游戏内容与工具链"）管路线、接口、审查和 `docs/plan.md`。**plan.md 只由总控改**，音乐那一行的进度发给它，由它来写。
  - 关卡线（会话 local_3846ee54-ebdf-4bbd-b2e4-0a3ec2535997）管关卡策划案、`plan.py`、`build.py`。要改这些，先找关卡线说好；涉及接口的，抄送总控一句。
  - 地图线（local_4e108d07-fd01-483c-8ea4-e79e9e35c081）在自己的工作目录里改 `experimental/cnv/maps/`。
  - 音乐线自己的改动由音乐线提交，关卡线不会帮着暂存。提交前要用户同意。
- 测试台按锁排队（`run_bench.ps1` 自己拿锁）：用之前先约，用完回一声；单独查一下红警3有没有在运行。A4 的检查现在由关卡线跑，它用完会通知。游戏在运行时编 mod 会自动写到 `work/staging`。
- `build.py` 只用 Edit 改，不要整文件覆盖。
- mod 名字不超过 15 个字符，只用字母和数字。
- 长时间的显卡任务开跑前，先问用户要不要限流；下载模型要用户同意。

## 硬约束原文

- 用户 2026-10-25（选路线 B 时）："代码开源还是不要抱多大希望，靠自己做出来的才是可靠的"
- 用户 2026-10-25（提需求时）："作为游戏音乐，你的创作最需要做的是符合剧情和情景，好的音乐对营造氛围感来说是至关重要的"
- 用户 2026-10-26（听完第一版）："风格不太像红色警戒3，前面的神秘感营造的很好，但是交战的时候音乐应该表现出紧张（处于劣势）和激烈（处于优势），而且带有阵营的特色"
