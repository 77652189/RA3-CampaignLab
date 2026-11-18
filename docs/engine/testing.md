# 测试怎么分层（规范本身；为什么见 [ADR 0035](../adr/0035-tests-layered-by-question.md)）

先问这条测试要回答哪个问题，再决定放哪层、用什么手段。一条测试只回答一个问题。

下面是目标结构。迁移期间旧测试还在 `tests/` 顶层，进度见 [plan.md](../plan.md)。新测试按这里写。

## 五层

| 目录 | 回答 | 怎么写 | 不许 |
|---|---|---|---|
| `tests/modules/` | 这条规则写对没有 | 最小世界（`simsmall.small_world`）摆一两个物体，推进几帧，断言模块输出；测试名写行为 | 加载地图、要私有模型、整局跑 |
| `tests/conformance/` | 和游戏一致吗 | 不手写：读数写进台子旁边的读数数据，一致性跑器每个场景跑一次、核对全部读数 | 一条读数一条测试；同一场景跑两次 |
| `tests/golden/` | 重构改了行为没有 | `simrecord` 固定任务在底版提交和本工作区逐帧比对（底版按提交号现录、不进仓库，见 `tests/golden/README.md`）；有意改行为时提交说明写 `Golden-Changed: <任务>` | 断言单个数值 |
| `tests/guards/` | 结构守住没有 | 静态检查：分层、零依赖、行数、写点、耗时上限（只许降）；每条做过变异检验 | 断言"当前值"；目录不存在时空转 |
| `tests/content/` | 我们的关卡能不能玩 | 关卡推演（输赢、目标、节奏），归内容线 | 拿它当模拟器回归网 |

工具自己的测试放 `tests/tools/`。

## 加一条台上读数

1. 台子（`checks/engine_X.py`）摆场景、出计数器。
2. 读数写进这个台子的读数数据 `checks/engine_X.readings.toml`（格式写在 `experimental/cnv/readings.py` 开头，样板 `checks/engine_aicrush.readings.toml`），写明证明哪个模块的哪条规则，以及模拟器对不对得上（对不上写 `mismatch`，两边的数都写）。
3. 规则写进模块，`tests/modules/` 里加最小世界测试。
4. 一致性跑器自动核对，不另写测试。

做完这三样才算"已对拍"：读数在数据里，跑器核对相符，有模块测试。清单（`inventory.py` 的 `conformance_probes`）现在按前两样算；第三样等 `tests/modules/` 有了测试再接进清单。迁移前的老路子（测试点名台子、手写登记表 `BENCHED_TESTS` 等）冻结：只减不增，`tests/guards/test_bench_tests.py` 守着。

## 耗时

- 每层有上限，由 `tests/guards/` 按耗时记录检查，上限只许降。上限表和每项为什么取这个数在 `experimental/testbench/time_budget.py`（模块层合计、守卫层合计、一致性跑器最慢一组、日常挑选池），守卫是 `tests/guards/test_time_budget.py`；耗时记录是总控全量后 `affected_tests.py --save-durations junit.xml` 写的 `work/testmap/durations.json`（按文件）和 `durations_tests.json`（按测试）。某项还没有记录就写"没有记录"，不猜。量耗时要独占整机：`RA3_CPU_EXCLUSIVE=1` 跑 pytest（或 `cpupool.py run --exclusive -- <命令>`），等别的重活放完令牌、期间不让新的开始（CPU 令牌池 `experimental/testbench/cpupool.py`，按核数留 2 个给游戏和台子；`simbench_peak`、`simrecord time` 自己就拿独占）。
- 越线在每日汇报"结构"段标 `!!`。
- 开局准备长的场景从快照开始，不从第 0 帧跑。

## 退出

读数迁进数据以后，原来点名它的手写整局测试在同一次提交里删掉。

不许新加点名台子的测试函数：`tests/guards/bench_tests_baseline.txt` 是 T4（11-18）时点名台子（代码里出现 `engine_X`、它的变体或它的构建名；注释和文档串里引用不算）的 880 个测试函数（T6 读全构建名后补进 7 个既有的，887），只减不增。测试函数本身或它用到的模块级辅助函数、常量、fixture 点名都算；新的一条变红，删掉或不再点名的那条要在同一次提交里从名单删掉（`tests/guards/test_bench_tests.py`）。新读数写进 `checks/<台子>.readings.toml`。
