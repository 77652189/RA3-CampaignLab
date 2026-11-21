# 测试怎么分层（规范本身；为什么见 [ADR 0035](../adr/0035-tests-layered-by-question.md)）

先问这条测试要回答哪个问题，再决定放哪层、用什么手段。一条测试只回答一个问题。

下面是目标结构。迁移期间旧测试还在 `tests/` 顶层，进度见 [plan.md](../plan.md)。新测试按这里写。

## 五层

| 目录 | 回答 | 怎么写 | 不许 |
|---|---|---|---|
| `tests/modules/` | 这条规则写对没有 | 最小世界（`simsmall.small_world`）摆一两个物体，推进几帧，断言模块输出；测试名写行为 | 加载地图、要私有模型、整局跑 |
| `tests/conformance/` | 和游戏一致吗 | 不手写：读数写进台子旁边的读数数据，`tests/conformance/test_readings.py` 按场景分组，跑一次并核对组内读数 | 一条读数一条测试；同一场景跑两次 |
| `tests/golden/` | 重构改了行为没有 | `simrecord` 固定任务在底版提交和本工作区逐帧比对（底版按提交号现录、不进仓库，见 `tests/golden/README.md`）；有意改行为时提交说明写 `Golden-Changed: <任务>` | 断言单个数值 |
| `tests/guards/` | 结构守住没有 | 检查分层、零依赖、行数、写点、耗时上限（只许降）等结构约束，按需做静态检查或小型运行；每条做过变异检验 | 断言"当前值"；目录不存在时空转 |
| `tests/content/` | 我们的关卡能不能玩 | 关卡推演（输赢、目标、节奏），归内容线 | 拿它当模拟器回归网 |

工具自己的测试放 `tests/tools/`。

## 加一条台上读数

1. 台子（`checks/engine_X.py`）摆场景、出计数器。
2. 读数写进这个台子的读数数据 `checks/engine_X.readings.toml`（格式写在 `experimental/cnv/readings.py` 开头，样板 `checks/engine_aicrush.readings.toml`），写明证明哪个模块的哪条规则，以及模拟器对不对得上（对不上写 `mismatch`，两边的数都写）。
3. 规则写进模块，`tests/modules/` 里加最小世界测试。
4. 一致性跑器自动核对，不另写测试。

做完这三样才算"已对拍"：读数在数据里，跑器核对相符，有模块测试。清单（`inventory.py`）把未标 `mismatch` 的读数用作新证据，跑器另行核对。`conformance_probes` 按台子源码中的名字归项；`declared_items` 读取 `item = "<部分> <名字>"`（格式见 `readings.py` 文档串）。迁移前的旧证据（点名台子的测试、手写登记表 `BENCHED_TESTS` 等）仍可使用，只减不增，`tests/guards/test_bench_tests.py` 守着。

## 耗时

- 整局模拟单独列入 `tests/replay_tests.txt` 的 `[game]` 组，日常挑选默认略过，总控全量运行。G3B 的静态构建检查留在 `tests/guards/test_architecture.py`，16 关的字幕回放在 `tests/guards/test_g3b_queue.py`，后者列在 `[game]`，日常挑选默认跳过；修改回放文件本身，或运行 `affected_tests.py --with-replays` 时可纳入。
- 耗时按 `experimental/testbench/time_budget.py` 的 `CEILING` 四项核算，已设上限只许降。模块合计 180 秒、守卫合计 250 秒、日常池 3600 秒，一致性最慢组的上限待定。守卫合计和日常池都排除回放名单里的文件。取值理由也在该文件，守卫是 `tests/guards/test_time_budget.py`；耗时记录是总控全量后 `affected_tests.py --save-durations junit.xml` 写的 `work/testmap/durations.json`（按文件）和 `durations_tests.json`（按测试）。整项没有样本时报"没有记录"；有样本时，合计中缺计时的文件用已知文件耗时的上中位数估算（排序后取下标 `len // 2`）。量耗时要独占令牌池：`RA3_CPU_EXCLUSIVE=1` 跑 pytest（或 `cpupool.py run --exclusive -- <命令>`），等别的重活放完令牌、期间不让新的开始（CPU 令牌池 `experimental/testbench/cpupool.py`，游戏或台子忙且至少有 8 个逻辑核时默认留 2 核，其余留 1 核；`RA3_CPU_TOKENS` 可覆盖池大小。`simbench_peak` 普通模式和 `simrecord time` 自取独占，`simbench_peak --ai` 由调用方持令牌）。
- 单条测试也有超时（T7）：`tests/conftest.py` 给每条没自带 `timeout` 标记的测试按层加上限（模块和工具 120 秒、守卫 600 秒、内容及其余测试 900 秒；回放名单优先，2400 秒。代码见 `time_budget.TEST_TIMEOUT` 和 `timeout_layer`），标记压过命令行 `--timeout`，所以命令里不用再写。超时即红：xdist 下报 "crashed while running <测试 id>"，`-n 0` 时整次结束并打出 "Stack of pytest_timeout <测试 id>"；进程没了它的 CPU 令牌就空出来。`RA3_TEST_TIMEOUT_SCALE` 乘到自动分配的上限上，设为 `0` 可在调试时关掉这些上限。
- 全量出现新红时，用 `python -X utf8 experimental/testbench/culprit.py --since-full work/logs/full_A.log work/logs/full_B.log` 定位首红。日志开头没记提交号时，加 `--good <提交> --bad <提交>`。
- 已知测试 ID 时，用 `python -X utf8 experimental/testbench/culprit.py --good <提交> --bad <提交> TEST_ID [TEST_ID ...]`。工具只复跑这些测试，遇到跳过会记为未知。
- 越线在每日汇报"结构"段标 `!!`。
- 一致性跑器对同一场景从第 0 帧启动一次，按顺序推进并复用采样结果。
- `python -X utf8 experimental/cnv/simrecord.py snap DIR` 默认对全部固定任务跨进程验证（AI 任务在公开世界上走 `engine.state.ai_snapshot`），比较逐帧记录、末态快照和最终报告。切点后须至少推进一帧。单项可用 `python -X utf8 experimental/cnv/simrecord.py one NAME RECORD --snap FRACTION --save FILE` 停在切点，再用相同任务、记录路径和切点，改传 `--resume FILE`。续写前重跑到切点并逐行核对已有的 gzip 记录，验证通过才追加。Python 入口是 `simrecord.run_task`，需要续写并校验已有记录时传入 `resume` 和 `record`。
- 跑 AI 整局用 `python -I -X utf8 experimental/cnv/simai_run.py BUILD --check CHECK --until SECONDS`，Python 入口是 `simai_run.run(build, check, until)`。测试里按文件加载 `simai_run.py`，再 `simai = simai_run.simai`（即 `engine.ai.core`），保证进程里只有一份，对它打的 monkeypatch 才落到这局上。

## 退出

读数迁进数据以后，原来点名它的手写整局测试在同一次提交里删掉。

不许新加点名台子的测试函数：`tests/guards/bench_tests_baseline.txt` 登记尚存的旧测试函数，只减不增。代码里出现 `engine_X`、它的变体或它的构建名都算，注释和文档串里的引用除外。测试函数本身或它用到的模块级辅助函数、常量、fixture 点名都算；新的一条变红，删掉或不再点名的那条要在同一次提交里从名单删掉（`tests/guards/test_bench_tests.py`）。新读数写进 `checks/<台子>.readings.toml`。
