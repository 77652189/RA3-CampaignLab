# 交接

总控会话的交接。各线有自己的交接：音乐 [docs/music/handoff.md](docs/music/handoff.md)，单位 [docs/units/handoff.md](docs/units/handoff.md)，策划从 [docs/design/README.md](docs/design/README.md) 进。

## 当前目标

**先解决管理和架构问题，再恢复产品线**（用户 2026-11-03："先把管理问题解决了"）。关卡线、外壳线已经暂停，原因是额度；策划、配音、音乐、单位四条线都空闲。

为什么要先解决：A4 试玩三轮下来，用户提的问题大多是"坏了""看不懂"两类，而且有几条报过修好又复发。结构原因记在 [ADR 0015](docs/adr/0015-fix-error-classes-at-source.md)；代码层面的原因在只读架构评审 [docs/reviews/architecture-2026-11-03.md](docs/reviews/architecture-2026-11-03.md) 里，五个核心问题摘要在 [docs/plan.md](docs/plan.md) 的"架构整改"一行。

## 下一步

1. **为五个问题设计一套完整方案**，交给用户定。用户否掉了"只做低风险止血"，原话："A没办法解决全部五个问题吧"。方案要包括：
   - 每个问题的目标状态：评审第 2.4 节的 L0～L5 分层，已写进 [docs/architecture.md](docs/architecture.md)；
   - 分几步走，每步怎么验证没有回退：评审第 4 节建议用"构建指纹"，即对比整改前后 `.big` 里每个文件的 sha1；
   - 守卫测试 G1～G10（评审第 5 节）分别在哪一步加；
   - 各线分工：关卡负责 `cnv/`，外壳负责打包和 `shell.py`，总控负责 `testbench/` 和守卫；
   - 独立验收怎么落地，也就是在 CampShell 上当玩家去验 I1～I15（[docs/issues.md](docs/issues.md)）；
   - 额度估算，以及先后顺序。

   评审里的"不建议"也要遵守：不一次性重写 c2～c18，也不把整个 `experimental/` 改成可安装包。
2. 用户定下方案后，重大决定记成 ADR，再恢复关卡线（交接见 `docs/story/handoff.md`）和外壳线（交接见 `docs/shell/handoff.md`，如果它写了的话）。
3. 等用户的：
   - 配音响度对比页还没听，在配音仓库的 `work/campaign/loudness_ab/`，决定 -14 LUFS 要不要降；
   - 英文播报和沃斯的声音是不是还像（I14）。
4. 留着的事：用 `work/logs/mods_deleted.txt` 查已删掉的测试 mod；三个不能重建的 mod 备份在 `Documents\RA3Modding\mods_backup\`。

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

## 状态

```yaml
slice: architecture-remediation-design-2026-11-03
blocked_on: none        # none | voice-session | user
next_gate: playtest     # test-map | coordinate-calibration | demo | playtest
```
