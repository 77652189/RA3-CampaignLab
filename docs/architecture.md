# 架构边界

只写读代码看不出来的"为什么不许这样"。模块清单、函数说明看代码和各文件开头的 docstring。

## 分层

```
units/ (Blender 建模、贴图、图标)  ─┐
campaign/ (地图、脚本、地形、光照) ─┼─> campaign/mapxml + make_campnew7 (编译 + 链接成 map.* 流)
                                    │        └─> sdk\RA3ModSDK3 的 BinaryAssetBuilder
testbench/ (隔离的游戏副本 + 截帧/输入 shim) <── 只读消费上面的产物，验证在游戏里的效果
music/ (Pathfinder 曲谱图 .mpf + 音轨 .mus) ──> pack.py ──> cnv/parts.Mission.music ──> 关卡 mod 的 static 流和 big
```

## 各线负责的文件（用户 2026-10-26 定按线分会话开发）

每个文件只归一条线改。共用文件（`experimental/cnv/build.py`、`parts.py`）要改先打招呼，只改自己那几行。各线做完一件事向总控报告，总控核对实际改动和测试结果后再更新 `docs/plan.md`。

| 线 | 负责 | 文件 |
|---|---|---|
| 总控 | 路线和优先级、各线接口、审查与合并、测试台工具、执行计划和需求 / 架构 / ADR | `docs/plan.md`、`requirements.md`、`architecture.md`、`docs/adr/`、`docs/engine/`、`HANDOFF.md`、`experimental/testbench/` |
| 关卡 | 策划案语言和编译器、模拟器、机关、关卡检查、各关玩法、地图（地图线 2026-10-26 结束，新关卡的地图跟着关卡一起设计）；单位的尺寸、血量和机制 | `docs/story/`、`experimental/cnv/`（`units/` 里的外观接线除外）、`experimental/campaign/platmap.py`、`platprops.py` |
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
