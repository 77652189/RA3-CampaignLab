# 交接

总控会话的交接。各线有自己的交接：音乐 [docs/music/handoff.md](docs/music/handoff.md)，单位 [docs/units/handoff.md](docs/units/handoff.md)，策划从 [docs/design/README.md](docs/design/README.md) 进。

## 当前目标

**按设计工作流返工关卡，先拿 A4 试点**（用户 2026-10-27）。11 关粗版都是从第 4 步（可玩粗版）直接做起的，要回到第 0～3 步补设计，再改策划案。工作流、闸门和准则见 [docs/design/charter.md](docs/design/charter.md)；A4 的纸面设计和给关卡线的实现清单见 [docs/design/a4-redesign.md](docs/design/a4-redesign.md)。

**先模拟、后测试台**：改策划案先跑 `plan_sim`（`experimental/cnv/sim.py`），测试台只留给引擎行为和最后的对齐。

## 下一步

1. 等用户玩试玩清单（[docs/plan.md](docs/plan.md)「试玩清单」）：返工前的 A4、原版伊贺、原版斯大林格勒、CampA4 听辨版。回答对照体验目标，归层后退回对应的那一步修。
2. 用户玩过 A4 后，关卡线按 a4-redesign.md 末尾的实现清单返工 A4，先用模拟器跑通，再上测试台。总控验收：模拟器版检查 + 受影响的测试台检查。
3. A4 走通后，其余 10 关依次过工作流的第 1～3 步（策划线），再进第 4 步（关卡线）。

## 必读

1. [docs/plan.md](docs/plan.md)：状态、待办、试玩清单。
2. [docs/architecture.md](docs/architecture.md)：各线负责的文件、「不许怎么做」。
3. [docs/adr/README.md](docs/adr/README.md)：为什么这样做。
4. [docs/engine/know-how.md](docs/engine/know-how.md)：测试工具的用法（编号 0～0h）和写新单位前要先查的坑；[docs/engine/script-semantics.md](docs/engine/script-semantics.md)：脚本引擎的运行语义。
5. `experimental/campaign/labpaths.py`：所有路径从这里来。

## 常用做法

- **动手前**：要编图或用测试台，先**单独**检查红警3有没有在运行（用户可能在玩），在运行就停下问；也看一眼有没有别的全屏游戏（`Get-Process | ? MainWindowTitle`），有就只做离线的活。
- **测试**：MCP `cnv_check(name, check)` 一次做完编图、进关、读计数器、判定；命令行 `python -I -X utf8 experimental/cnv/build.py <关> --check <检查>`（`--no-build` 只跑，默认 8 倍速）。`cnv_show` 看各层公开的接口，`cnv_list` 列出所有构建，`plan_sim` 推演策划案。
- **写新单位**照钻地运兵车的样子：`units/<名>.py`（公开 abilities）+ `missions/<名>_bench.py`（按地点放、公开 cast / marks）+ `checks/<名>.py`（计数器 + 期望），在 `build.py` 的 MISSIONS 里登记。
- **MCP 服务进程只在会话开始时加载一次代码**：改了 `bench_mcp.py`、`harness.py`、`counters.py` 以后，本会话要验证就用 `experimental/testbench/bench_client.py` 另起一个服务进程；新会话自动加载。
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
- 游戏：用户可能在玩红警3；游戏运行时不往 Mods 写、不开测试台，先单独检查进程
- 不改 Steam 游戏目录里的文件；不解密 Corona mod
- 回复用通俗中文

## 状态

```yaml
slice: design-workflow-a4-pilot-2026-10-28
blocked_on: user        # none | voice-session | user
next_gate: playtest     # test-map | coordinate-calibration | demo | playtest
```
