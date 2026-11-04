# 架构边界

只写读代码看不出来的"为什么不许这样"。模块清单、函数说明看代码和各文件开头的 docstring。

## 分层

**目标分层**来自 2026-11-03 的架构评审（[reviews/architecture-2026-11-03.md](reviews/architecture-2026-11-03.md) 第 2.4 节）。下表是边界；现状离目标有多远、按什么顺序收，以 [plan.md](plan.md) 为准。从下往上依次是：

| 层 | 内容 | 对外接口 | 不许 |
|---|---|---|---|
| L0 格式库 | `labpaths`、`ra3voice/*`，以及 map、big、脚本、地形、光照的读写 | 读写函数 | 知道"关卡""外壳"这些概念 |
| L1 内容 | `cnv/maps`、`cnv/units`、`cnv/devices`，音乐、配音、视频的打包 | 地点 `SITES`、单位对象、机关、资源包 | import 编译器或打包层 |
| L2 编译 | `plan.py`（手写关卡也走同一个上下文） | 策划稿 → 纯数据的 Mission | 碰文件系统，碰打包层的全局变量 |
| L3 打包 | `parts.assemble` 背后的 `make_campnew*`，以及外壳 | 一个入口：按清单（ModSpec）出 mod | 读模块级的可变全局变量。外壳只往清单里加东西 |
| L4 编排 | `build.py` | 命令行入口；关卡和检查各自注册 | 手写注册表 |
| L5 验收 | `parts.contract` 的规则检查、`testbench/` | 只读最终产物；动态检查只加观测 | import L1、L2 的常量，改动被测行为 |

**现状**（评审第 1、2 节）：打包层是 `make_campnew18→7→6→4→{2,3}` 一串复制出来的版本，靠 import 时改别人模块的全局变量拼在一起；检查不能在 CampShell 上跑，还会改动被测的关卡；台词和单兵命令都有多个出口。音乐只通过 `cnv/parts.Mission.music` 进关卡 mod 的 static 流和 big（见下面"不许怎么做"）。

## 各线负责的文件（用户 2026-10-26 定按线分会话开发）

每个文件只归一条线改。`parts.py` 已按层拆成三份（[ADR 0016](adr/0016-one-outlet-per-class.md)）：`model.py`（关卡数据）归关卡线，`contract.py`（产物规则）归总控，`package.py`（打包）归外壳线。`parts.py` 本身只剩转手导出，新代码直接 import 这三份。`build.py` 仍是共用文件，要改先打招呼，只改自己那几行。守卫测试在 `tests/test_architecture.py`，由总控维护。各线做完一件事向总控报告，总控核对实际改动和测试结果后再更新 `docs/plan.md`。

| 线 | 负责 | 文件 |
|---|---|---|
| 总控 | 路线和优先级、各线接口、审查与合并、测试台工具、执行计划和需求 / 架构 / ADR | `docs/plan.md`、`requirements.md`、`architecture.md`、`docs/adr/`、`docs/engine/`、`HANDOFF.md`、`experimental/testbench/` |
| 关卡 | 策划案语言和编译器、模拟器、机关、关卡检查、各关玩法、地图（地图线 2026-10-26 结束，新关卡的地图跟着关卡一起设计）；单位的尺寸、血量和机制 | `docs/story/`、`experimental/cnv/`（`units/` 里的外观接线除外）、`experimental/campaign/platmap.py`、`platprops.py` |
| 外壳（2026-11-03 从关卡线拆出） | 战役外壳（替换原版三个战役的卡片、章节、播报、局势介绍、界面，[ADR 0014](adr/0014-replace-retail-campaigns-in-mod.md)）、启动器 | `experimental/cnv/shell.py`、`shell_missions*.json`、`play.hta`、`launcher.py`、外壳用到的 `experimental/campaign/make_campnew*.py`、`experimental/testbench/shell_shots.py`；`build.py` 只改 `--shell` 那段 |
| 单位 | 新单位建模（先出一个样品给用户定风格，再批量），在自己的分支上做 | `experimental/units/`、`docs/units/`；`experimental/cnv/units/` 里只改外观（模型、贴图、按钮头像、残骸、死亡特效的接线） |
| 策划（2026-10-27 开） | 游戏设计这一层：原版任务拆解、设计总纲和准则、战役总表、各关的纸面设计 | `docs/design/` |
| 音乐 | 自制配乐、曲谱图、战况音乐 | `experimental/music/`、`docs/music/` |
| 配音 | AI 中文配音 mod | 另一个仓库 RA3-ChineseVoice |

## 不许怎么做

- **`experimental/cnv` 里各层不越界取东西**（用户 2026-10-22："接口对接口"）。关卡只按地图公开的地点（`SITES`）放东西，不写裸坐标；检查只通过关卡的接口拿东西（`m.role` / `m.ability` / `m.site` / `m.player`），不 import 关卡模块的常量。`parts.contract()` 在编图前拦截越界的地方。原因：任何一层改了内部（比如挪平台、换单位 id），其他层不跟着坏；大模型读 `cnv_show` 就知道能用什么，不用读别层的代码。关卡设计（`docs/story/levels.md` 的卡片）也只用这些公开的名字，由 `tests/test_level_cards.py` 和代码对齐；要改设计时先改卡片。
- **代码里不写绝对路径。** 一律从 `experimental/campaign/labpaths.py` 取（ROOT、WORK、SHARED、ENVS、SDK3、SDK_OLD）。整个 RA3Modding 目录再搬一次也不用改代码。
- **只用 SDK v3.0 编单位和地图**（`sdk\RA3ModSDK3`）。`sdk\RA3ModSDK` 只给最早几个探针保留，见 [ADR 0001](adr/0001-sdk-v3-only.md)。
- **不改 Steam 游戏目录里的文件。** 测试一律走测试台的副本（`work/testbench/RA3`，硬链接副本：游戏会写的小文件是复制的，**不能往硬链接文件里写**，写了会改到 Steam 原文件）。
- **游戏在运行时不往 `文档\Red Alert 3\Mods\` 写**，改写到 `work/staging/`（各 make_campnewNN 已自动判断）。
- **测试台的游戏只由 `experimental/testbench/harness.py` 启动，按槽位加锁**（[ADR 0006](adr/0006-bench-slots.md)）：每局占一个槽位（`shared\locks\bench.json`、`bench-2.json`……，`slots.py`），锁里记着游戏进程号；不是测试台开的游戏（用户在玩）开着时不启动。老工具（`run_bench.ps1`、各个 `make_*.py`、音乐线的 `probe_mod.py`）只认 `bench.json`，看见任何游戏开着就不启动，只会更保守。从 git 工作树里跑时，锁目录要找回主仓库旁边的 `shared\`（`slots.lab`），否则看不见别的线的锁。
- **SDK 一次只编一个**：`parts.assemble` 拿 `shared\locks\sdk-build.json` 才写 CNVUnits、调 BinaryAssetBuilder（两个同时编，其中一个会失败且日志为空）；游戏照样能并排跑。
- **检查默认 8 倍速，手动驾驶 1 倍**（[ADR 0007](adr/0007-bench-game-speed.md)）：加速只改游戏眼里的时间；"关卡第几秒"和各种等待都按关卡时间算。怀疑问题是加速造成的，用 `RA3_BENCH_SPEED=1` 重跑一次区分。
- **策划案模拟器不替代游戏**（`experimental/cnv/sim.py`）：它按我们编译器的语义推演，对引擎的假设写在 [engine/script-semantics.md](engine/script-semantics.md)，查不到的由 `sim.py --align` 列出。日常改策划案先跑它；它和测试台结果不一致时以测试台为准，再改模拟器。
- **显卡任务必须走 `ra3voice/throttle.py`**：读 `shared\gpu_limit.json` 限流，并自动登记 `shared\locks\gpu-*.json` 租约。
- **游戏按名字查找的资源**（CommandSet、ButtonImage、SelectPortrait、指令集里的指令）不在引用链上：要用 `make_campnew7.EXTRA_OWN` 按名字前缀链接进来；没人引用的资源（UnitAbilityButtonTemplate 等）要放进单独的文件，用 `EXTRA_ALL` 以 `type="all"` 引入。否则 BAB 和链接器会静默丢掉它们。
- **听游戏的声音只录游戏进程本身**（`experimental/music/listen.py record_game`，Windows 进程回环），不录整个扬声器的混音：电脑上别的程序也在出声，混进去以后认不出音乐。Windows 会按程序记住音频会话的音量和静音（测试台每次都会把游戏静音），所以录之前要把会话调成低音量、不静音，录完放回静音，不能留着让别人的 `-Sound` 运行变小声。
- **我们的曲谱图只通过 `Mission.music` 进关卡 mod**（2026-10-25 和内容会话商定）：它要进 static 流（游戏在菜单里就用它），不能放进地图流（EXTRA_ALL）；也不能另做一个音乐 mod 和关卡 mod 叠着装，两个 big 里的 static.bin 会互相覆盖。关卡脚本的音乐事件名由 `parts.contract` 对照 `Mission.music.events` 检查。`cnv/build.py` 不在顶层导入音乐线的代码（`_music_bench()` 用到时才导入），这样音乐线出错不会连累其他关卡的构建。
- **音乐线借用配音仓库的 vgmstream**（`RA3-ChineseVoice/third_party/vgmstream`），只用来解码分析原版音频、核对我们写的文件，不复制到本仓库，也不进 mod。
- **改游戏数据前查 schema 的字段类型**（`sdk\RA3ModSDK3\Schemas\xsd`），尤其是百分比、时间、引用。
- **`ra3voice/` 下的 big / refpack / csf / throttle / reslock / manifest / xas 和配音仓库各有一份**（manifest、xas 是音乐线 2026-10-25 复制过来的）。 改接口时通知配音线；`reslock.py` 两边必须保持一致。

## 共享资源（两条线共用，在仓库外）

`<RA3Modding>\shared\`：`locks\`（bench.json 独占；gpu-*.json 租约；进程退出或过期即失效）与 `gpu_limit.json`（限流的唯一来源）。格式见 `ra3voice/reslock.py` 开头。
