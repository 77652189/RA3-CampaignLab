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

0. **灰盒校准（ADR 0011，最优先）**：探针做完了（`docs/story/drive-probe.md`，提交 c6e0ac7）；实机打法脚本已被 ADR 0011 取代，不再铺。接着做：在 `experimental/cnv/` 新写 `graybox.py`（借 `offline.py` 的 `walk`、`dps`、`cost`），按该文末"接下来"一节算每段 k\*，先拿现在的 A4 校准（得判出平推轻松），再补 `a4_before` 的走查。过了就写测试 `tests/test_graybox.py` 并提交；判不出就先报告原因。

1. **A4 按设计线新稿重做第 3 层。** 读：`docs/design/flow/a4.md`（流程稿，待用户审；第 2 层地图内容稿也还没出来）、`docs/design/flow/mechanics.md`（哪些机制能承诺）、`docs/design/maps/`（第 2 层，地图内容，设计线在做）。现有计划 `docs/story/plans/a4.md`；做法是改生成器和计划，不手改产物。要加的东西：
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
- 音频的脚本帧数（约 44 帧/音频秒）和计时器帧率（约 15/秒）对不上，原因没查清：别把音频帧数换算成任务秒（`docs/engine/script-semantics.md` 第 11 条）。
