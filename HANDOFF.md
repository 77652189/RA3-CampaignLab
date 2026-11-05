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

1. **11-04 晚做到哪了**（各线都已提交推送，总控已核对）：
   - 盟军 9 关草稿：A4、A5、A7、A8、A9 有了（能编、sim 过、测试台能赢），现状表在 `docs/story/handoff-phase4.md`。关卡线在挑 A1、A2、A3、A6 里的下一关。
   - 地图页（外壳线，`experimental/mappage/`，本地运行 `serve.py`）：改现有图（拖地点、批注、地形画刷），从零画新图（`serve.py --new`），Agent 直接写草图（`docs/shell/sketch-format.md`，`sketch2map.py --check`）。布鲁塞尔图就是这样画的。
   - 引擎线：放置、通行、地形、寻路已查（`docs/engine/terrain.md`、`pathing.md`、`upgrades.md`）。寻路模型在私有仓库 RA3-EngineModel（ADR 0018），正在加分层粗路径并重新标定；A9 的"无敌升级"在等测试台验。
   - 各线每次清空后读自己的交接：关卡 `docs/story/handoff-phase4.md` 最末一节，外壳 `docs/shell/handoff.md` 第一节，引擎 `work/re/handoff.md` 开头。
   - git 提交前钩子：用户 2026-11-04 定"不用加"。各线提交前至少跑 `tests/test_architecture.py` 和 `tests/test_docs.py`，总控收到汇报后再核一遍。
2. **盟军 9 关草稿做完后，在 CampShell 上做一次独立验收**：按 [docs/acceptance/brief.md](docs/acceptance/brief.md) 派一个新的子 Agent，先从干净的提交重新构建 CampShell。
3. **K7**（A4 陡坡重排）在地图页上和用户一起定。
4. **等用户的**：配音响度对比页（配音仓库 `work/campaign/loudness_ab/`）和 I14。
5. **留着的事**：
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
- 回复用通俗中文
- 声音（2026-10-26）："请你在工作的时候关掉音量，或者不要在我的耳机上播放，总之让我听不到就可以"——录游戏声音只走 `listen.record_game`（-80 dB）
- 发布（2026-11-02）："许可证有问题的话，就只在国内发布吧，不上N网"
- 反编译（2026-11-04）："只用来做mod，研究学习里面的内容，不公开"——本仓库在 GitHub 上是公开的，反编译得来的东西（伪代码、函数地址、据此写的说明）只放 `work/re/`，不进仓库
- 配音仓库 RA3-ChineseVoice：只提交、不推送（推送没授权）
- 引擎模型（2026-11-04）："我希望尽可能把引擎的算法还原成python代码，这样我们后续就有一个稳定的地基，其他语言也可以"——照反编译重写的算法放本机私有仓库 `RA3Modding/RA3-EngineModel`，只提交、不推送、不加远端（[ADR 0018](docs/adr/0018-engine-model-private-repo.md)）

## 状态

```yaml
slice: draft-levels-friction-2026-11-04
blocked_on: none        # none | voice-session | user
next_gate: playtest     # test-map | coordinate-calibration | demo | playtest
```
