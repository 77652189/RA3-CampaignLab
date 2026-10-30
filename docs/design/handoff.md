# 策划线交接

清空上下文以后从这里接着做。规则和现状以各自的权威文件为准，这里只写"现在做到哪、下一步做什么、容易踩的坑"。

## 这条线管什么

关卡设计按层走（[ADR 0008](../adr/0008-levels-by-layer.md)：剧情流程 → 地图内容 → 摆放），有问题改模板或原则再重新生成，不手改某一关。[ADR 0009](../adr/0009-one-level-through-all-layers-first.md)：A4 先走完全部层、进游戏试玩通过，S1、J7 跟着，其余 24 关等 A4 过了再批量做。

- 第 1 层流程剧本：[flow/README.md](flow/README.md)（模板和第 0～23 条），检查 [flowcheck.py](flow/flowcheck.py)，查看器 [flowview.py](flow/flowview.py) 生成 `work/flowview/flow.html`（玩家视角、五条审核、整关一张表、地图内容四种看法）。
- 台词去 AI 腔：[flow/style.md](flow/style.md)（唯一一份，配音线也引用），流程 [flowpolish.py](flow/flowpolish.py) 交给 Gemini（`experimental/outsource/agy_task.py`）。
- 第 2 层地图内容：[maps/README.md](maps/README.md)，检查 [maps/mapcheck.py](maps/mapcheck.py)。
- 原则 [principles.md](principles.md)（P1～P35），证据卡在 [teardowns/data/](teardowns/data/)。

## 现状（2026-10-30）

- **A4**：流程剧本用户已通过（2026-10-29）；五条审核字段、每段敌军、摆放要求齐全，flowcheck 0 处问题。台词润色两轮（8a29662），目标说明压到两句以内（4481350）。第 2 层地图内容稿写完（9eadc68），mapcheck 0 处问题。
- **刚做完**（525484b，用户审 A4 时提的"资源点和建筑的摆放呢"）：`摆放要求/建筑`（八座：北营指挥所、电厂、波能塔、工厂、兵营，修理厂、电视塔，玩家基地）；资源点写矿和油井的数，flowcheck 拿地图 OBJECTS 里的矿和油井对数；查看器每段地图画矿、油井、按阵营上色的建筑、这一段的伏击点和援军，还没看见的画淡，拆掉的不画。运河东岸那对矿原来剧本没交代，现在写成最后一程前可扩的矿。
- **S1、J7**：有五条审核字段，还缺 `摆放要求` 和每段 `敌军`（flowcheck 总数 8 处都是这两关的，排在 A4 之后）。
- 用户正在审 A4，意见由总控陆续转来。

## 下一步

1. 接总控转来的用户对 A4 的意见，照"改模板，不改单关"处理，改完重新生成网页、汇报。
2. 用户审过地图内容稿以后：三处"要加"发给地图线（金奖牌子、二号广场的地道口、北营的冰雕作坊），关卡线开始摆 A4。
3. A4 之后：S1、J7 补摆放要求（含建筑）、敌军，再按 style.md 润色一遍。

## 常用命令（输出长的写进 work/logs，只看最后几行）

```
python -X utf8 docs/design/flow/flowcheck.py > work/logs/flowcheck.log 2>&1; tail -n 1 work/logs/flowcheck.log
python -X utf8 docs/design/maps/mapcheck.py a4 | tail -n 1
python -X utf8 docs/design/flow/flowview.py
python -m pytest -q tests/test_docs.py | tail -n 1
python -X utf8 docs/design/flow/flowpolish.py brief a4 <文件夹> [说明]
```

## 坑

- 钩子不让 heredoc、`python -c`、`sed -i` 里带反斜杠：写成草稿目录里的 .py 再跑。
- 查看器 `flowview.html` 是一整段脚本，一处语法错就整页空白（控制台不一定报）：改完用 node 检查——把 `<script>` 抽出来 `node --check`。全局名字别撞（`SIDE` 已经是角色阵营的颜色，建筑用 `OWNER`）。
- YAML：值不要以引号开头；流式列表里名字带逗号要加引号。
- 地图范围用 `BORDERS['whole']` 的矩形，不是 `island` 那个圆。
- 只提交 `docs/design/` 下自己的文件；`mechanics.md` 有时有关卡线没提交的改动，别带进去。不改 `docs/plan.md`、`docs/story/`。
