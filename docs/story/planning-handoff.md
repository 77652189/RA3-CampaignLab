# 策划线交接（地图设计感 → 整理文档）

写于 2026-11-08。只写进度和指针。状态以 [plan.md](../plan.md) 为准。

## 做完的
- A4 地图诊断：[map-diagnosis-a4.md](map-diagnosis-a4.md)，量法 [look_measure.py](../design/teardowns/data/look_measure.py)；原版实测规律并进 [map-language.md](map-language.md) 4.3。用户："先不做，先记文档，然后整理一下文档"——**地图先不改**，地图设计 skill 暂停。
- 整理文档（canon 审计）：`docs/plan.md` 改写成 ADR 0022～0026 后的现状（各线一张表）；四份超长交接瘦身（`story/handoff-phase4.md` 71 行、`story/handoff.md` 104 行、`shell/handoff.md` 51 行、`music/handoff.md` 91 行）；修死链（`experimental/cnv/missions/a4_before.md` 搬家后的相对链接、一处被当成链接的引文）；`HANDOFF.md` 里指向 plan.md 旧行的指针和过期的"当前目标"改成指向 ADR 0026；`look_measure.py` 不再自己改 `sys.path`（它让 G4 守卫超了上限）。

## 接着做
- 文档清理做完（用户 2026-11-08 "照表做"：7 份过期文档归档进 `docs/archive/`、两份一次性任务说明删掉）。
- 下一步：回到地图设计（等用户说恢复），从 map-diagnosis-a4.md 的四层做起。

## 坑
- canon 的两个脚本输出中文要先 `export PYTHONIOENCODING=utf-8`，否则 GBK 乱码；`audit_doc_claims.py` 会把反引号里的 `f(self, name, spec)` 当成死链（`reviews/architecture-2026-11-03.md`），是误报。剩下的"失效路径"大多是 `work/`、私有引擎模型仓库、配音仓库里的文件，不是错。
- `look_measure.py` 读拉什莫尔山会出错（跳过）；克里姆林宫、横滨的建筑归在玩家名下，所以读成 0 栋民用建筑。
- 工作区里有别的线没提交的改动（`docs/engine/inventory.md`、`experimental/cnv/inventory.py`、`sim.py`、`tests/test_simbench.py` 等），不要带进提交。
