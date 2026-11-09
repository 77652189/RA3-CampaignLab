# 策划线交接（地图设计感 → 整理文档）

写于 2026-11-08。只写进度和指针。状态以 [plan.md](../plan.md) 为准。

## 做完的
- A4 地图诊断：[map-diagnosis-a4.md](map-diagnosis-a4.md)，量法 [look_measure.py](../design/teardowns/data/look_measure.py)；原版实测规律并进 [map-language.md](map-language.md) 4.3。用户："先不做，先记文档，然后整理一下文档"——**地图先不改**，地图设计 skill 暂停。
- 整理文档（canon 审计）：`docs/plan.md` 改写成 ADR 0022～0026 后的现状（各线一张表）；四份超长交接瘦身（`story/handoff-phase4.md` 71 行、`story/handoff.md` 104 行、`shell/handoff.md` 51 行、`music/handoff.md` 91 行）；修死链（`experimental/cnv/missions/a4_before.md` 搬家后的相对链接、一处被当成链接的引文）；`HANDOFF.md` 里指向 plan.md 旧行的指针和过期的"当前目标"改成指向 ADR 0026；`look_measure.py` 不再自己改 `sys.path`（它让 G4 守卫超了上限）。

## 待用户拍板：文档删 / 归档 / 保留（还没动）

| 文件 | 建议 | 理由 |
|---|---|---|
| `docs/story/handoff-phase3.md` | 归档 | 第 3 阶段已结束，开头自己写着转去 phase4；只剩 `story/handoff.md` 两处引用 |
| `docs/design/handoff.md` | 归档 | 策划线 11-04 的旧交接，没人引用；现在用本文件 |
| `docs/design/story-questions.md` | 归档 | 5 题 10-28 已全定，结论在 `design/campaign.md` 第六节 |
| `docs/story/comparison.md` | 归档 | 10-20 拿大纲 v3 做的对照，大纲已到 v6 |
| `docs/story/drive-probe.md` | 归档 | 自述已被 ADR 0011 取代、"到此为止"；归档时改 3 处引用 |
| `docs/design/cards/brief.md`、`pick.md` | 归档 | 一次性的出题任务说明和挑卡记录，结果已在 `cards/all.md` |
| `docs/design/flow/beats_brief.md`、`beats_brief2.md` | 删 | 给外包模型的一次性任务说明，产物已写进流程稿；删时同步 `flowcheck.py` 的 `NOT_SCRIPTS` |
| 工作区未跟踪的 `-q`（12 MB）、两个 `grep.exe.stackdump` | 删 | 命令误写出的输出文件和崩溃转储，不是文档 |
| `docs/design/a4-redesign.md` | 保留 | 已被 A4 甲卡取代，但被 19 处引用，归档要改一串链接，收益小 |
| `docs/reviews/architecture-2026-11-03.md` | 保留 | ADR 0016 的依据，ADR 引用它 |
| `docs/acceptance/brief.md` | 保留 | CampShell 待验项还要用 |
| `docs/render/handoff.md` | 保留 | 画面线挂起，恢复时的入口 |
| `experimental/cnv/missions/a4_before.md` | 保留 | 构建 `a4_before` 和测试的输入 |

## 接着做
1. 用户点头后按上表删 / 归档（归档进 `docs/archive/`，改掉指向它们的链接，跑 `tests/test_docs.py`）。
2. 之后回到地图设计（等用户说恢复）：从 map-diagnosis-a4.md 的四层做起。

## 坑
- canon 的两个脚本输出中文要先 `export PYTHONIOENCODING=utf-8`，否则 GBK 乱码；`audit_doc_claims.py` 会把反引号里的 `f(self, name, spec)` 当成死链（`reviews/architecture-2026-11-03.md`），是误报。剩下的"失效路径"大多是 `work/`、私有引擎模型仓库、配音仓库里的文件，不是错。
- `look_measure.py` 读拉什莫尔山会出错（跳过）；克里姆林宫、横滨的建筑归在玩家名下，所以读成 0 栋民用建筑。
- 工作区里有别的线没提交的改动（`docs/engine/inventory.md`、`experimental/cnv/inventory.py`、`sim.py`、`tests/test_simbench.py` 等），不要带进提交。
