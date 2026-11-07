# 交接

总控会话的交接。各线有自己的交接：
- 关卡 [docs/story/handoff-phase3.md](docs/story/handoff-phase3.md)
- 外壳 [docs/shell/handoff.md](docs/shell/handoff.md)
- 音乐 [docs/music/handoff.md](docs/music/handoff.md)
- 单位 [docs/units/handoff.md](docs/units/handoff.md)
- 策划从 [docs/design/README.md](docs/design/README.md) 进
- 引擎线的交接和反编译参考在本机 `work/re/handoff.md`、`work/re/ra3-script-reference.md`。仓库在 GitHub 上是公开的，这些不进仓库。

## 当前目标

**尽快把 27 关做成草稿，进入玩法验证**（用户 2026-11-04："尽可能把制作一关的摩擦降到最小，尽可能一次解决一类问题，尽快推进到玩法验证阶段"）。
- 美术不提前、不返工。
- 第一个发布版本（用户 2026-11-04）："第一个发布版本至少盟军的9关做完"。
- git 历史里那份反编译试探报告（23c4071）："可以暂时不删"。
- 引擎线优先（用户 2026-11-04）："接下来你先自主完成引擎线的开发，如果额度充足，就把地形编辑器也做出来"；"可以，地形编辑器升级成能画新地图"。
- 引擎整体移植（用户 2026-11-05）："碰到什么查什么可能不太可行，我们能整体重构成python代码吗？"→"可以按这个顺序做"：游戏逻辑层按层移植成 Python 模型，每层开工前向用户报对拍结果和额度（[ADR 0019](docs/adr/0019-port-game-logic-by-layer.md)）。
- 草稿关的完成标准和摩擦怎么量，见 [docs/plan.md](docs/plan.md) 的"先把 27 关做成草稿"一行。
- 架构整改（[ADR 0016](docs/adr/0016-one-outlet-per-class.md)）已经做到第 3 阶段，状态在 plan.md 的"架构整改"一行。

## 下一步

1. **11-05 上午收工时做到哪了**（各线都已提交推送，总控已核对；外壳线自查 I4 I17 I22 已过，仍待独立验收）：
   - 盟军 9 关草稿 A1～A9 都有了，`build.py campaign --shell`（加 `--lang intl`）把 9 关都装进 CampShell。
   - CampShell 独立验收做了三轮（报告 `work/acceptance/2026-11-05*/report.md`，状态在 `docs/issues.md`）：验过 I1 I5 I10 I11 I12 I16 I18 I20 I23，I21 战败卡片验过；还待验 I4 I17 I22（总控会话的测试台服务早于 `menu_frames`，要在新会话里验；外壳线在自查）、I2 I3 I6 I7 I9（要真把 A4 打下去）、I13（听声音）。
   - 引擎整体移植（ADR 0019）：第一层脚本引擎做完并接进 `sim.py`；第二层物体与模块做了 5 批（框架、血量死亡、属性修正和光环、升级加状态、无人机、空中的建筑 `docs/engine/air.md`），导弹第一批（追踪弹）做了：飞行时长、连发间隔对上；追不上是因为原版 V4 有散布（`docs/engine/missile.md`）。第三层武器层（用户 11-05 批准）开了头：开火流程读出来了，下令到首中 = 约 23 帧 + 0～15 帧（随单位、确定）+ 预瞄，中间那段规则还没读出（`docs/engine/weapons.md`，私有 2 条 xfail）。模型代码分层：`core.py` 只放通用 RTS 框架、只依赖 `num.py`；红警3 规则在 `rules.py` 和各模块，每条标出处；数值都经 `num.py`（现在是浮点）。
   - 调研：`docs/research/rts-engine-survey.md`。
   - 各线每次清空后读自己的交接：关卡 `docs/story/handoff-phase4.md` 最末一节，外壳 `docs/shell/handoff.md` 第一节，引擎 `work/re/handoff.md` 开头。各线提交前至少跑 `tests/test_architecture.py`、`tests/test_docs.py`（关卡线再加 test_level_cards、test_plans；外壳线加 test_shell）。线会话一开工就容易过 15 万，派活前先看上下文，过了先清空。
2. **用户 11-05 中午定的**（"3.B也做，4.地图大幅度改，目前还在开发阶段，距离交付很远，其他按推荐"）：I19 先不改，等真打 A4；I21 指挥官名不改；导弹两处对不上的先查清，同时正式开第三层武器层（引擎线在做）；K7/I8 的 A4 地形大改（关卡线在做）；配音响度用户听过："响度问题不大"（I13 验过）；I14 "音色不换也可以"。高帧率（用户 11-05 "可以，按A做"）：配音线在维护我们的 SAGE-Unlocked 分支（合上游测试版修复、联机回归测试、发行版兜底），并加 DXVK 可选项；摸底报告 `work/re/fps-unlock-survey.md`。现在没有等用户的事。
2b. **引擎线队列**（11-06 起分 A / B 两个会话：A 做建筑类、传送，交接 `work/re/handoff.md`；B 做回血、视野、开出地图外、碰撞，交接 `work/re/handoff-b.md`；清单总表在 A 的交接里，B 的项由总控勾）。第二层只剩传送（A，对拍和文档未做）；B 的四项已全完成。用户 11-06 凌晨："等六点四十额度重置之后，再让引擎线完成二阶段的剩余内容，以及遭遇战AI部分的研究。最晚10点之前关机"——第四层（遭遇战 AI）已获授权，用户原话："不止出研究计划，先重构成python代码便于后续研究。可以考虑的功能要点包括：语音响应，代理玩家指挥部队或建造，闲聊"——先把原版遭遇战 AI 移植成 Python 模型（ADR 0019 做法），三个功能方向记作模型的用途。教授演示的材料在 `work/demo/`（安装包、模拟器、流水线网页）和讲解页 https://claude.ai/artifact/P6AogyCYi18xdogwwF7cP6；用户"明天中午再具体看实机演示能不能成功"。
2c. **关卡线只靠模拟器试做**（用户 11-06 晚："等引擎线做完再对接吧，试试关卡线能不能只靠模拟器制作，不依赖测试台"）：关卡线这一轮不开测试台，逐项判断 A4 剩下的 7 项测试台检查（detour、queue、smash、derrick、melt、smoke、win）能不能用模拟器替代，报告放 `docs/story/`；报告里"缺哪几条规则"那份清单转给引擎线。引擎线第四层的 AI 结论（`docs/engine/aistate.md`、`aispecial.md`、`aiopen.md`）等引擎线做完再接进关卡。**结果（关卡线 `8a04f50`，报告 [docs/story/sim-vs-bench-a4.md](docs/story/sim-vs-bench-a4.md)）**：detour、smoke、queue 能替代；melt、smash、win 部分能；derrick 不能。缺的规则 R1～R6 排在引擎线第四层之后。总控定了两条：补这些规则时照 ADR 0019 同时在测试台量对应读数；G15 先只管已经声明 Block 的地图，其余地图等重做时再补 Block。11-07 测试台对照做完：7 项全 PASS（smash 修过）。
2d. **第四层收完，进入"补规则 + 代理玩家"阶段**（用户 11-07 选 A，见 [docs/plan.md](docs/plan.md) 引擎逻辑层一行）。分工：模拟器文件（`experimental/cnv/sim*.py`）归 A；代理玩家（私有 `ra3model/proxy/` + 公开 `experimental/cnv/simproxy.py`）归 B；A4 任务、地图、`CHOKES` 归关卡线。现状：R1～R7 已补进模拟器并和测试台对拍；生产和钱（`Sim.offers` / `order_build`）、`Sim.advance` 已加；"每帧重下令走不动"测试台否定（smash 真因未查：SET_REF 目标 / 水边上岸点）。代理玩家能在模拟器里打 A4（`python -I -X utf8 experimental/cnv/simproxy.py a4 --compare`，B 的 `work/re/scripts/sweep_a4.py` 跑多组），16 组全输，最好 3:25，手写题卡打法 3:57；关卡线判 A4 数据不改。**下一步**：A 补 R8（空闲 / 攻击移动 / 守位的自动索敌和追击范围，探针 `engine_acquire` 已提交，交接 `work/re/handoff.md`）→ B 重跑 sweep_a4、调点杀距离（`work/re/handoff-b.md` 第 27 节）→ 关卡线给 `CHOKES` 每条街加路口接点（若未做，见 `docs/story/handoff-phase4.md`）。
3. **下一轮独立验收**：在新会话里先确认 `bench_start(menu_frames=2)` 生效，再验 I4 I17 I22，并派人真打一遍 A4 验 I2 I3 I7 I9。
4. **留着的事**：
   - A4 攻略页 https://claude.ai/artifact/Dp8HUcuyyFN42vqhitJZ8r，生成脚本在 `work/walkthrough/make_page.py`；
   - 冷启动自检：`python -I -X utf8 experimental/testbench/doctor.py`；
   - 已删掉的测试 mod 名单在 `work/logs/mods_deleted.txt`。

## 必读

1. [docs/plan.md](docs/plan.md)：状态、待办、试玩清单。
2. [docs/architecture.md](docs/architecture.md)：各线负责的文件、「不许怎么做」。
3. [docs/adr/README.md](docs/adr/README.md)：为什么这样做。
4. [docs/engine/know-how.md](docs/engine/know-how.md)：测试工具的用法（编号 0～0h）和写新单位前要先查的坑；[docs/engine/script-semantics.md](docs/engine/script-semantics.md)：脚本引擎的运行语义。
5. `experimental/campaign/labpaths.py`：所有路径从这里来。

## 常用做法

- **动手前**：编图和测试台工具自己查红警3在不在运行（用户 2026-10-28 同意，省掉各线每次手动查）：用户的游戏开着时，编图自动改放 `work/staging`，测试台拒绝开局并报错——看到这个报错就停下问用户；槽位都被别的测试台局占着时，工具自己排队，最多等 10 分钟（`RA3_BENCH_WAIT`）。不用再单独 tasklist、查锁或写循环等。别的游戏不用先查：直接开，只有独占全屏的游戏会让测试台弹 DirectX 错误框，工具当场报出来（`harness.CRASH_TITLES`），那时改做离线的活。跑几分钟的检查放后台，等完成通知，不要轮询。
- **测试**：MCP `cnv_check(name, check)` 一次做完编图、进关、读计数器、判定；命令行 `python -I -X utf8 experimental/cnv/build.py <关> --check <检查>`（`--no-build` 只跑，默认 8 倍速）。`cnv_show` 看各层公开的接口，`cnv_list` 列出所有构建，`plan_sim` 推演策划案。
- **写新单位**照钻地运兵车的样子：`units/<名>.py`（公开 abilities）+ `missions/<名>_bench.py`（按地点放、公开 cast / marks）+ `checks/<名>.py`（计数器 + 期望），在 `build.py` 的 MISSIONS 里登记。
- **MCP 服务进程只在会话开始时加载一次代码**：改了 `bench_mcp.py`、`harness.py`、`counters.py` 以后，本会话要验证就用 `experimental/testbench/bench_client.py` 另起一个服务进程；新会话自动加载。
- **额度用完、会话中断时**：看到某条线的一轮因额度报错，先 `get_usage` 读重置时间，再用 `CronCreate` 定一个一次性任务（重置后 3 分钟，避开整点），提示里写明要唤醒哪几个会话 id、各自上一轮在做什么；到点后先 `list_sessions {"linked": true}` 排除已经在跑的，再给其余的发"额度已重置，请接着做上一轮没做完的事"。定时任务只活在本会话里，关掉应用就没了。
- **Bash 工具的 hook**（`.claude/hooks/guard_inline_edits.py`）拦下带反斜杠的 heredoc / `python -c` 写文件、带反斜杠的 `sed -i`、双引号 `python -c` 里的反引号。被拦就改用 Edit / Write，或把脚本写成 .py 文件再跑。

## 验证方式

- 全部离线测试（含文档守卫）：`python -I -X utf8 -m pytest -q tests`
- 一关的推演：`python -I -X utf8 experimental/cnv/sim.py a4`（加 `--align` 看还没和游戏对齐的假设）
- 一个测试台检查：`python -I -X utf8 experimental/cnv/build.py a4 --check win`，应得到 `RESULT PASS`
- 锁：`python -I ra3voice/reslock.py status`

## 硬约束（用户原话）

- 下载："需要任何内容直接下载就行，不要停下来，你最多可以用50G硬盘"（只走可信来源，不绕过验证码）
- 删文件："只要不乱删文件就行"——删除前先问
- 显卡："可以，限流开始做吧"——显卡任务一律限流（`shared\gpu_limit.json`）
- 游戏：用户可能在玩红警3；游戏运行时不往 Mods 写、不开测试台（2026-10-28 起由编图和测试台工具自己检查，见「常用做法」）
- 不改 Steam 游戏目录里的文件；不解密 Corona mod
- 注入（2026-11-05）："既然我们已经用了DLL注入的方式做帧率解锁，那注入原版程序应该是可以的"——只用代理 DLL 加内存补丁，规则见 [ADR 0020](docs/adr/0020-inject-into-retail-program.md)
- 回复用通俗中文
- 声音（2026-10-26）："请你在工作的时候关掉音量，或者不要在我的耳机上播放，总之让我听不到就可以"——录游戏声音只走 `listen.record_game`（-80 dB）
- 发布（2026-11-02）："许可证有问题的话，就只在国内发布吧，不上N网"
- 反编译（2026-11-04）："只用来做mod，研究学习里面的内容，不公开"——本仓库在 GitHub 上是公开的，反编译得来的东西（伪代码、函数地址、据此写的说明）只放 `work/re/`，不进仓库
- 配音仓库 RA3-ChineseVoice：公开的 origin 只提交、不推送（推送没授权）；私有远端 backup 每次提交后推（[ADR 0021](docs/adr/0021-private-github-repos.md)）
- 引擎模型（2026-11-04）："我希望尽可能把引擎的算法还原成python代码，这样我们后续就有一个稳定的地基，其他语言也可以"——照反编译重写的算法放本机私有仓库 `RA3Modding/RA3-EngineModel`，只推到 GitHub 私有仓库，不改可见性（[ADR 0018](docs/adr/0018-engine-model-private-repo.md)、[ADR 0021](docs/adr/0021-private-github-repos.md)：用户 2026-11-05 "那就做成github私有仓库吧"）；`work/re` 同样是推私有仓库的单独 git 仓库

## 状态

```yaml
slice: draft-levels-friction-2026-11-04
blocked_on: none        # none | voice-session | user
next_gate: playtest     # test-map | coordinate-calibration | demo | playtest
```
