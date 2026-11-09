# 策划线交接（地图设计感）

写于 2026-11-08。只写进度和指针。

## 做完的
- A4 地图诊断：[map-diagnosis-a4.md](map-diagnosis-a4.md)，量法 [look_measure.py](../design/teardowns/data/look_measure.py)；原版实测规律并进 [map-language.md](map-language.md) 4.3。
- 用户看完诊断："先不做，先记文档，然后整理一下文档"。**地图先不改**，地图设计 skill（第 2 步）暂停。

## 接着做：整理文档（总控 2026-11-08 派的第 2 件，用 canon skill 的审计做法）
1. 先 `git add` 新文件，再跑 canon 的 `scan_docs.py`、`audit_doc_claims.py`（在 `~/.claude/skills/canon/scripts/`），修死链和失效路径。
2. 查双权威和过期内容：`docs/plan.md` 要反映 ADR 0024～0026 之后的现状（引擎优先、关卡暂停、试玩改在游戏里、模拟器界面线），旧状态直接改写，不追加。各线交接文档超过 150 行的，删掉已结束切片的细节（git 里有历史）。已知超长的：`docs/story/handoff.md` 211 行。
3. `docs/` 下没人引用、已被取代的文档列成"删 / 归档 / 保留"建议表，每条一句理由。**删除和归档要等用户点头**，不擅自做。
4. 不改 ADR 正文（ADR 只能被取代，不改写），不动 `work/re`。
5. 汇报：改了什么，加上待用户拍板的删除/归档清单。

## 坑
- `look_measure.py` 读拉什莫尔山会出错（跳过）；克里姆林宫、横滨的建筑归在玩家名下，所以读成 0 栋民用建筑。
- 工作区里有别的线没提交的改动（`docs/engine/inventory.md`、`experimental/cnv/inventory.py`、`playcheck.py`、`tests/test_docs.py`），不要带进提交。
