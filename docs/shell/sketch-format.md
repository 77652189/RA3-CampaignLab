# 地图草图格式（sketch.json，版本 1）

给人和 Agent 共用：页面（`serve.py --new`）画出来的、脚本直接写出来的，是同一种文件。生成器是 `experimental/mappage/sketch2map.py`，它文件开头的说明和这里一致；两边对不上时以代码为准，并改这份文档。

## 不开页面：写文件 → 生成 → 检查

```bash
python -I -X utf8 experimental/mappage/sketch2map.py mymap --check --sketch my.json
```

- `--sketch 文件`（`-` 读标准输入）：存成 `work/mappage/mymap/sketch.json`，`name` 字段会被改成命令行里的名字。
- `--check`：只打摘要（结论、每项检查、橙色提醒、文件位置），十来行；全文在 `work/mappage/mymap/report.json`。退出码 0 = 全部通过。
- `--no-map`：不写 .map、不跑 mapstudy（快几秒）；`--pathing`：加跑引擎线寻路模型。
- 产物：`work/mappage/mymap/mymap.py`、`mymap_names.py`（地图模块草稿）、`.map`、`ground.png`、`regions.png`。模块草稿只在 work/；关卡线审过搬进 `experimental/cnv/maps/` 后，**模块就是源**，别再从草图重生成覆盖它（ADR 0017）。
- 页面也能接：右栏"草图 JSON"粘贴导入，或者直接把文件写到 `work/mappage/<名字>/sketch.json` 再开页面。

## 坐标和单位

- 世界单位，和地图模块（`Site(x, y, r)`）一样。原点在容器图西南角，**x 向东、y 向北**。容器固定 5000×5000，可玩区是 `borders` 的第一块。
- 层（tier）：0 水面、1 低地、2 高地、3 更高。高度是 `platmap.TIER`：220 / 340 / 455 / 570。层和层交界生成时自动成陡坡（过不去），只有坡道能上下。
- 所有数字都可以是整数或小数；生成器原样写进模块（同一份草图永远出同一份文本）。

## 字段

| 字段 | 形状 | 说明 |
| --- | --- | --- |
| `version` | `1` | 必填 |
| `name` | 字符串 | 小写字母、数字、下划线；命令行和页面会改成图名 |
| `what` | 字符串 | 一句话说明，成为模块的文档首行 |
| `size` | `[W, H]` | 可玩区大小（`borders` 为空时用），最大 5000 |
| `base` | 0～3 | 没画到的地方是哪一层 |
| `cliff` | 整数 | 悬崖平滑次数（`Layout.cliff`），一般 2 |
| `shapes` | `[{kind, at, tier, what}]` | 地块，按顺序画，后画盖先画。`kind`：`poly`（`at` = `[[x, y], ...]`，至少 3 点）、`rect`（`[x0, y0, x1, y1]`）、`circle`（`[x, y, r]`） |
| `walls` | `[{points, width, tier, what}]` | 悬崖墙：沿折线的一条陡崖（默认第 3 层），谁都过不去，不是看不见的墙 |
| `ramps` | `[{low, high, width, what}]` | 坡道：`low`、`high` 各 `[x, y]`，两端站在不同层的平地上；每格最多升 6.5 |
| `bridges` | `[{a, b, template}]` | 桥：`a`、`b` 是两岸的 `[x, y]`，桥面宽 120；两端要在同一高度的干地上（设计检查会量）；`template` 默认 `HB_Bridge_02`；原版长度 270～1780 |
| `roads` | `[{points, width, texture}]` | 路：只换地面贴图，不改高度；贴图默认 `Pavement_Heidel02` |
| `sites` | `{代码名: {x, y, r, zh, what, build, cast}}` | 命名地点。代码名英文小写，任务按它放东西；`zh` 中文名；`build` 要能建造的方块边长；`cast` 施法圆半径 |
| `start` | `[x, y]` | 玩家出生点和开场镜头。`sites` 里的 `start` 会自动放在这里，**别再在同一位置另放一个地点**（检查会报"地点重合"） |
| `fields` | `[{name, x, y, facing, twin, base, owner, build}]` | 矿场：(x, y) 是精炼厂位置，矿在 `facing`（45 东北 / 135 西北 / 225 西南 / 315 东南）方向 180 处；`twin` 1 / -1 两块、0 一块；`owner` `""` / `p1` / `s1`；`build` 200 = 精炼厂要建在这。自动出 `<name> refinery` 地点 |
| `derricks` | `[[x, y]]` | 油井 |
| `borders` | `{名字: [x0, y0, x1, y1]}` | 第一块是可玩区 |
| `brushes` | `[{op, r, s, dabs, height}]` | 地形画刷：`raise` / `lower` / `flatten`，`dabs` 平铺 `[x0, y0, x1, y1, ...]`，`flatten` 要 `height`；生成时叠在地块、坡道之后 |
| `blocks`, `gaps` | | 地块用途、缺口：目前只从已有图带过来，页面不能画 |
| `objects`, `scenery` | `[{template, x, y, side, name, angle, flags, site}]` | 原样放的物体、景物（新图一般是空的） |

缺的列表字段按空处理。

## 例子

```json
{"version": 1, "name": "demo", "what": "a river town with one bridge", "size": [3000, 2400], "base": 1, "cliff": 2,
 "shapes": [{"kind": "rect", "at": [1400, 0, 1600, 2400], "tier": 0, "what": "river"},
            {"kind": "circle", "at": [2400, 1800, 300], "tier": 2, "what": "hill"}],
 "walls": [],
 "ramps": [{"low": [2100, 1500], "high": [2250, 1650], "width": 160, "what": "hill ramp"}],
 "bridges": [{"a": [1340, 1200], "b": [1660, 1200]}],
 "roads": [{"points": [[400, 1200], [1340, 1200]], "width": 120, "texture": "Pavement_Heidel02"}],
 "sites": {"town": {"x": 2300, "y": 1000, "r": 250, "zh": "镇子", "what": "the enemy town", "build": 300},
           "hilltop": {"x": 2400, "y": 1800, "r": 150, "zh": "山顶", "what": "watch post"}},
 "start": [500, 1200],
 "fields": [{"name": "west", "x": 700, "y": 600, "facing": 45, "twin": 1, "base": "", "owner": "p1", "build": 0}],
 "derricks": [], "borders": {"whole": [0, 0, 3000, 2400]}}
```

## 检查读数怎么看

- **失败**（`ok` 为假）：草图本身的问题、设计检查（LINT：坡道太陡、建造方块压到悬崖/河岸、矿点不平、桥两端不在同一高度的干地上……）、CONTRACT、出生点走不到的地点、写不出 .map。
- **橙色提醒**（不算失败）：可能半路停住（引擎线寻路模型）、贴边窄缝（比 50 窄）、地点重合（两个地点相距不到 40 或较小半径的五分之一）。
