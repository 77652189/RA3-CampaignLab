# 测试怎么分层（规范本身；为什么见 [ADR 0035](../adr/0035-tests-layered-by-question.md)）

先问这条测试要回答哪个问题，再决定放哪层、用什么手段。一条测试只回答一个问题。

五层和工具目录已启用，旧测试仍有一部分在 `tests/` 顶层。新测试按下表放置。

## 五层

| 目录 | 回答 | 怎么写 | 不许 |
|---|---|---|---|
| `tests/modules/` | 这条规则写对没有 | 直接用 `engine.kernel.world.World`，或用 `engine.testing.small.small_world(..., model=False)` 摆一两个物体。后者默认带岛图，省略 `model=False` 会请求私有模型。推进几帧，断言模块输出，测试名写行为 | 依赖私有模型、载入整张任务图、跑整局 |
| `tests/conformance/` | 和游戏一致吗 | `tests/conformance/test_readings.py` 按构建名、检查名和运行选项归并场景。跨场景比较把关联的运行合成一组，每个运行只做一次 | 为每条读数手写测试，或重复运行同一场景 |
| `tests/golden/` | 重构改了行为没有 | `simrecord` 固定任务在底版提交和本工作区逐帧比对（底版按提交号现录，选版、钉版不同时的跳过条件见 `tests/golden/README.md` 和 `experimental/testbench/golden.py:records`）；有意改行为时提交说明写 `Golden-Changed: <任务>` | 断言单个数值 |
| `tests/guards/` | 结构守住没有 | 检查分层、零依赖、特定文件的行数（如 `AGENTS.md`）、已登记的写点和记录耗时是否越线，按需做静态检查或小型运行；每条做过变异检验 | 断言"当前值"；目录不存在时空转 |
| `tests/content/` | 我们的关卡能不能玩 | 关卡推演（输赢、目标、节奏），归内容线 | 拿它当模拟器回归网 |

工具自己的测试放 `tests/tools/`。

## 加一条台上读数

1. 台子在 `benches/<domain>/<group>/checks.py#engine_X` 摆场景、出计数器。
2. 读数写进这个台子的读数数据 `benches/<domain>/<group>/readings.toml#engine_X`（格式写在 `experimental/cnv/readings.py` 开头，样板 `benches/ai/tactics/readings.toml#engine_aicrush`），写明证明哪个模块的哪条规则，以及模拟器对不对得上（预期始终不符用 `mismatch`，仅无私模时预期不符用 `mismatch_nomodel`，都写两边的数）。无私模时需要遭遇战 AI 的组会跳过。
3. 规则写进模块，`tests/modules/` 里加最小世界测试。
4. 一致性跑器自动核对。点跑一组用 `tests/conformance/test_readings.py` 的 pytest 参数 ID，跨场景及运行选项写法见 `experimental/cnv/readings.py` 文件头。

验收要求是读数入库、跑器核对相符、规则有模块测试。晋级门槛见 `work/re/handoff-coord.md` 的「已对拍」口径，自动取证见 `experimental/cnv/inventory.py` 的 `conformance_probes`（按台子源码归项）和 `declared_items`（`item` 可写单个字符串或列表）。两者以无全局 `mismatch` 的读数取证，清单计分时无须先跑测试。

## 耗时

- 日常选测查 `python -X utf8 experimental/testbench/affected_tests.py --cmd`、该脚本文件头和 `AGENTS.md` 的测试条款（回放、CPU 令牌）。默认排除 `tests/replay_tests.txt` 的 `[game]`（含一致性跑器、golden）和 `[bench]`，改到回放文件本身或加 `--with-replays` 可纳入。G3B 静态构建检查留在 `tests/guards/test_architecture.py`，16 关字幕回放在 `[game]` 的 `tests/guards/test_g3b_queue.py`。
- 耗时按 `experimental/testbench/time_budget.py` 的 `CEILING` 四项核算，修改约定是已设上限只许降。模块合计 180 秒、守卫合计 250 秒、日常池 3600 秒，一致性最慢组为 `None`，只报告耗时。守卫合计和日常池都排除回放名单里的文件。取值理由也在该文件，守卫是 `tests/guards/test_time_budget.py`；耗时记录是总控全量后 `affected_tests.py --save-durations junit.xml` 写的 `work/testmap/durations.json`（按文件）和 `durations_tests.json`（按测试）。整项没有样本时报"没有记录"；有样本时，合计中缺计时的文件用整个记录中已知文件耗时的上中位数估算（排序后取下标 `len // 2`）。量耗时要独占令牌池：`RA3_CPU_EXCLUSIVE=1` 跑 pytest（或 `cpupool.py run --exclusive -- <命令>`），等别的重活放完令牌、期间不让新的开始（CPU 令牌池 `experimental/testbench/cpupool.py`，游戏或台子忙且至少有 8 个逻辑核时默认留 2 核，其余留 1 核；`RA3_CPU_TOKENS` 可覆盖池大小。`simbench_peak` 普通模式和 `simrecord time` 自取独占，`simbench_peak --ai` 由调用方持令牌）。
- 单条测试也有超时（T7）：`tests/conftest.py` 给每条没自带 `timeout` 标记的测试按层加上限（模块和工具 120 秒、守卫 600 秒、内容及其余测试 900 秒；回放名单优先，2400 秒。代码见 `time_budget.TEST_TIMEOUT` 和 `timeout_layer`），标记压过命令行 `--timeout`，所以命令里不用再写。Windows 上 `pytest-timeout` 超时会结束进程。xdist 下报 "crashed while running <测试 id>"，`-n 0` 时整次结束并打出 "Stack of pytest_timeout <测试 id>"；进程没了它的 CPU 令牌就空出来。`RA3_TEST_TIMEOUT_SCALE` 乘到自动分配的上限上，设为 `0` 可在调试时关掉这些上限。
- 全量出现新红时，用 `python -X utf8 experimental/testbench/culprit.py --since-full work/logs/full_A.log work/logs/full_B.log` 定位首红。日志开头没记提交号时，加 `--good <提交> --bad <提交>`。
- 已知测试 ID 时，用 `python -X utf8 experimental/testbench/culprit.py --good <提交> --bad <提交> TEST_ID [TEST_ID ...]`。工具只复跑这些测试，遇到跳过会记为未知。
- 越线在每日汇报"结构"段标 `!!`。
- 一致性跑器对每个运行从第 0 帧启动一次，按顺序推进并复用采样结果。
- `python -X utf8 experimental/cnv/simrecord.py snap DIR` 默认对全部固定任务跨进程验证（AI 任务在公开世界上走 `engine.state.ai_snapshot`），比较逐帧记录、末态快照和最终报告。切点后须至少推进一帧。单项可用 `python -X utf8 experimental/cnv/simrecord.py one NAME RECORD --snap FRACTION --save FILE` 停在切点，再用相同任务、记录路径和切点，改传 `--resume FILE`。续写前重跑到切点并逐行核对已有的 gzip 记录，验证通过才追加。Python 入口是 `simrecord.run_task`，需要续写并校验已有记录时传入 `resume` 和 `record`。
- 跑 AI 整局用 `python -I -X utf8 experimental/cnv/simai_run.py BUILD --check CHECK --until SECONDS`，Python 入口是 `simai_run.run(build, check, until)`。测试里按文件加载 `simai_run.py`，再 `simai = simai_run.simai`（即 `engine.ai.core`），保证进程里只有一份，对它打的 monkeypatch 才落到这局上。

## 退出

读数迁进数据以后，原来点名它的手写整局测试在同一次提交里删掉。

旧证据仍可用，手写登记表（如 `BENCHED_TESTS`）受条数上限约束。不许新加点名台子的测试函数。`tests/guards/bench_tests_baseline.txt` 登记尚存的旧测试函数，只减不增。代码里出现 `engine_X`、它的变体或它的构建名都算，注释和文档串里的引用除外。测试函数本身或它用到的模块级辅助函数、常量、fixture 点名都算；新的一条变红，删掉或不再点名的那条要在同一次提交里从名单删掉（`tests/guards/test_bench_tests.py`）。新读数写进该组的 `readings.toml`，用 `bench_id` 标明台子。
