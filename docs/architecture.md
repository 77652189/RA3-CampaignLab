# 架构边界

只写读代码看不出来的"为什么不许这样"。模块清单、函数说明看代码和各文件开头的 docstring。

## 分层

```
units/ (Blender 建模、贴图、图标)  ─┐
campaign/ (地图、脚本、地形、光照) ─┼─> campaign/mapxml + make_campnew7 (编译 + 链接成 map.* 流)
                                    │        └─> sdk\RA3ModSDK3 的 BinaryAssetBuilder
testbench/ (隔离的游戏副本 + 截帧/输入 shim) <── 只读消费上面的产物，验证在游戏里的效果
```

## 不许怎么做

- **`experimental/cnv` 里各层不越界取东西**（用户 2026-10-22："接口对接口"）。关卡只按地图公开的地点（`SITES`）放东西，不写裸坐标；检查只通过关卡的接口拿东西（`m.role` / `m.ability` / `m.site` / `m.player`），不 import 关卡模块的常量。`parts.contract()` 在编图前拦截越界的地方。原因：任何一层改了内部（比如挪平台、换单位 id），其他层不跟着坏；大模型读 `cnv_show` 就知道能用什么，不用读别层的代码。
- **代码里不写绝对路径。** 一律从 `experimental/campaign/labpaths.py` 取（ROOT、WORK、SHARED、ENVS、SDK3、SDK_OLD）。整个 RA3Modding 目录再搬一次也不用改代码。
- **只用 SDK v3.0 编单位和地图**（`sdk\RA3ModSDK3`）。`sdk\RA3ModSDK` 只给最早几个探针保留，见 [ADR 0001](adr/0001-sdk-v3-only.md)。
- **不改 Steam 游戏目录里的文件。** 测试一律走测试台的副本（`work/testbench/RA3`，硬链接副本：游戏会写的小文件是复制的，**不能往硬链接文件里写**，写了会改到 Steam 原文件）。
- **游戏在运行时不往 `文档\Red Alert 3\Mods\` 写**，改写到 `work/staging/`（各 make_campnewNN 已自动判断）。
- **测试台只通过 `experimental/testbench/run_bench.ps1` 启动**：它拿 `shared\locks\bench.json` 独占锁，保证同一时间只有一个红警。
- **显卡任务必须走 `ra3voice/throttle.py`**：读 `shared\gpu_limit.json` 限流，并自动登记 `shared\locks\gpu-*.json` 租约。
- **游戏按名字查找的资源**（CommandSet、ButtonImage、SelectPortrait、指令集里的指令）不在引用链上：要用 `make_campnew7.EXTRA_OWN` 按名字前缀链接进来；没人引用的资源（UnitAbilityButtonTemplate 等）要放进单独的文件，用 `EXTRA_ALL` 以 `type="all"` 引入。否则 BAB 和链接器会静默丢掉它们。
- **改游戏数据前查 schema 的字段类型**（`sdk\RA3ModSDK3\Schemas\xsd`），尤其是百分比、时间、引用。
- **`ra3voice/` 下的 big / refpack / csf / throttle / reslock 和配音仓库各有一份。** 改接口时通知配音线；`reslock.py` 两边必须保持一致。

## 共享资源（两条线共用，在仓库外）

`<RA3Modding>\shared\`：`locks\`（bench.json 独占；gpu-*.json 租约；进程退出或过期即失效）与 `gpu_limit.json`（限流的唯一来源）。格式见 `ra3voice/reslock.py` 开头。
