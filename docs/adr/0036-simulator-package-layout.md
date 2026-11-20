# 0036 模拟器的平铺实现文件归进 `engine/` 包，命令入口留在原处（⑩ 方案 A）

状态：accepted（2026-11-20）。用户批了推荐的 A（"按推荐派活，两项都批"）。

## 背景

[0029](0029-simulator-layers.md) 的 ⑩ 是把搬出 `sim.py` 的部件做成包；[0031](0031-simulator-module-composition.md) 先暂停了它，先立了 `engine/kernel`、`engine/modules`、`engine/ports`、`engine/script`。到 11-20，`experimental/cnv/` 顶层还平铺着五十多个 `sim*.py` 实现文件，名字只说"是模拟器的"，不说是哪块。

比过两个方案（同样的内核、模块注册和端口结构）：

- **A 只搬实现**：52 个文件，改约 500 处导入；入口不动。
- **B 连入口一起收**：多搬 8 个入口（`simbench`、`simai_run` 等），多出约 150 处按文件路径加载的改动，集中在台子回放和 AI 入口，子进程、清单工具的启动方式都要跟着改。

## 决定

1. **实现按用途归包**，`experimental/cnv/engine/` 下：

   | 包 | 装什么 |
   |---|---|
   | `ai` | 遭遇战 AI（`core`、`pullback`） |
   | `combat` | 战斗：弹头注册和各弹头（已有），宿主侧的伤害 `host`、射程 `range`、扫射线 `sweeps` |
   | `data` | 模板数据 `units` |
   | `loop` | 帧顺序 `frame` |
   | `objects` | 宿主侧的物体规则（身体、寻路 `path`、移动、驻军、地雷、状态……） |
   | `orders` | 命令 `order`、微操 `micro` |
   | `players` | 玩家：钱、科技、生产队列 |
   | `script` | 脚本动作 / 条件（`act*`、`cond*`）、公用 `common`、宿主 `host`，和已有的执行器 |
   | `state` | 快照、AI 快照、多战场 |
   | `testing` | 规则测试用的最小世界 `small` |
   | `world` | 世界句柄 `handle`、存活表 `living` |

   多数文件去掉 `sim` 前缀落进所属包（`simbody` → `objects/body`、`simact_order` → `script/act_order`）；改了名的：`simai` → `ai/core`、`simdamage` → `combat/host`（`combat/damage` 已是伤害弹头）、`simsweep` → `combat/sweeps`（`combat/sweep` 已是开扫射的弹头）、`simunits` → `data/units`、`simloop` → `loop/frame`、`simproduce` → `players/production`、`simscript` → `script/common`、`simexec` → `script/host`、`simsnap` → `state/snapshot`、`simaisnap` → `state/ai_snapshot`、`simsmall` → `testing/small`、`simworld` → `world/handle`。文档里 ⑩ 之前写的旧名照这张表找。

   `kernel`、`modules`、`ports` 原样不动，真正的 XML 模块仍由 `engine/modules/__init__.py` 加载。
2. **命令入口留在顶层**：`sim.py`（组装）、`simrecord.py`（跨提交录制的固定入口）、`simbench*`、`simai_run`、`simproxy`、`simchecks`、`simcoverage`、`simshow`、`simstatic`。按文件路径加载它们的地方一处不改。
3. **纯搬家**：只改导入、按名加载和守卫表里的模块名，层号、字段归属、白名单的意思不变；不留旧名转发文件；需要时用局部绑定（如 `from engine.data import units as simunits`）让 `sim.simunits` 照旧。逐帧记录前后一字不差。
4. **派生缓存不读旧格式**：AI 快照存了类的模块路径，搬家后升它的版本号，旧缓存被拒、重建。

## 后果

- 新部件按这张表找家，不再往顶层加 `sim*.py` 实现文件。
- 入口要不要收进包（方案 B）以后单独定；顶层没用的转调、测试按部件重排、私有脚本清理各走各的工单。
- 搬家脚本和每步过关条件在私有仓库的工作笔记里（`work/re/sim_split/move_files_pack/`），不进公开仓库。
