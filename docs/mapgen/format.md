# 地图设计文件 v1

用 UTF-8 JSON。下面是低街、广场和上层高地的小样。车辆从低街上高地只经东侧坡口。关闭坡口后，西侧剩下的开口只让步兵通过。

```json
{
  "version": 1,
  "seed": 37,
  "blocks": {
    "west": {"height": 3, "use": "老街", "ring": ["west_bottom", "main", "-west_scarp", "west_wall"]},
    "square": {"height": 3, "use": "广场", "ring": ["east_bottom", "east_wall", "-east_scarp", "-main"]},
    "ridge": {"height": 4, "use": "高地", "ring": ["west_scarp", "east_scarp", "ridge_edge"]}
  },
  "roads": {
    "main": {"line": [[100,0],[100,100]], "width": "street", "ends": ["start","end"]},
    "lane": {"line": [[25,50],[150,50]], "width": "alley", "ends": ["start","end"]}
  },
  "borders": {
    "west_bottom": {"line": [[0,0],[100,0]], "sides": ["west",null]},
    "west_wall": {"line": [[0,100],[0,0]], "sides": ["west",null]},
    "east_bottom": {"line": [[100,0],[200,0]], "sides": ["square",null]},
    "east_wall": {"line": [[200,0],[200,100]], "sides": ["square",null]},
    "ridge_edge": {"line": [[200,100],[200,200],[0,200],[0,100]], "sides": ["ridge",null]},
    "west_scarp": {"line": [[0,100],[100,100]], "sides": ["ridge","west"], "pass": ["foot"],
                   "segments": {"sealed": {"span": [20,90], "pass": []}}},
    "east_scarp": {"line": [[100,100],[200,100]], "sides": ["ridge","square"],
                   "segments": {"hairpin": {"span": [20,80], "pass": ["foot","vehicle"]}}}
  },
  "points": {
    "spawn": {"block": "west", "at": [25,25]},
    "goal": {"block": "ridge", "at": [150,150]},
    "muster": {"block": "square", "at": [125,25]}
  },
  "states": {"blocked": {"pass": {"east_scarp.hairpin": []}}},
  "relations": {
    "approach": {"type": "通不通", "from": "spawn", "to": "goal", "who": "vehicle", "only_via": "east_scarp.hairpin"},
    "sealed_route": {"type": "通不通", "from": "spawn", "to": "goal", "who": "vehicle", "state": "blocked", "reachable": false},
    "muster_space": {"type": "放得下", "point": "muster", "side": 30}
  },
  "patches": {"move_tree": {"op": "move", "slot": "ridge.trees.edge-a", "at": [125,160]}}
}
```

## 几何与编号

- 顶层必填 `version: 1` 和非空 `blocks`。各表用对象 ID 当键。ID 以英文字母开头，其余可用英文字母、数字、下划线和连字符。顶层各表的 ID 全局唯一，`base` 留给基础状态。过口 ID 在各自的界内唯一，引用写成 `界ID.过口ID`。未知字段和重复键会报错。
- XY 用整数世界坐标（有符号 32 位），跨度、宽度和关系里的距离用世界单位。块的 `height` 用非负整数档。**一档 = 世界 70 单位 = .map 原始高度 1792**。一侧高度直接取该侧块的高度。
- 先画城区道路。块的 `ring` 按顺序引用整条路或界，前缀 `-` 表示反向。线首尾必须接上并围出简单多边形。共边只写一次，`sides` 是沿界原方向的左、右块，图外填 `null`。围块线在共同端点相接，遇 T 形分界时在分岔处拆线。两侧都围块的路要求同高且同为陆地或水。
- 子块以 `parent` 指向直接父块，须完全在父块内部。同父的子块可共边，内部不能重叠。父块保留尚未细分的地，子块的外缘以父块为另一侧。父块余下的地面须连通，余地上的孔洞轮廓不能只在一个点相接。块可选 `kind`（默认 `land`，水用 `water`）和布局的 `protagonist`（用途文字）。点的 `at` 须严格在自己块的有效内部，可选填 `use`。
- 路宽档用 `alley`、`street`、`avenue`。路的折线实交处接成路口，整个路网必须连成一片，每段须在块内或沿块边。只有 `ends` 明列的 `start`、`end` 可以悬空。

## 过口与状态

- `pass` 允许 `foot`、`vehicle`、`amphibian`、`ship`。陆地容纳前三种，水容纳两栖和船。界和过口可写正数 `width`。过口 `span` 沿折线从起点累计弧长，左闭右开。结束于线尾的区间包含线尾，区间末值可写 `null` 表示线尾。区间不得重叠或越界。
- 过口的 `pass` 优先于整界默认值。缺省段只有路确实连到界的两侧时才生成图上的过口。显式空列表表示禁行，活动道路碰到它就报错。基础状态下，高差界须有开口或写 `closed_reason`。道路默认让步兵、车辆、两栖通过，跨水的道路段在图上提供路面。
- 每个命名状态都从 `base` 单独应用。先按 ID 替换声明的 `pass`，再按过口优先于整界的规则取值。也可用 `heights` 改已有水块的高度档，用 `playable` 选仍开放的块（省略时全开）。状态封住路所经过的口时，也要将碰到该口的路设为 `[]`。

## 关系与修补

关系都可选 `state`，默认 `base`。`from`、`to`、`a`、`b` 引用块或点，`point` 引用点，`road` 引用路，`who` 取上述兵种。`via` 和 `only_via` 引用块、路、界或过口。

| `type` | 参数 |
|---|---|
| 通不通 | `from to who`，可选 `reachable`（布尔，默认真）和 `only_via`（有路且移除该 ID 后无路） |
| 谁先到 | `a b to who min_lead`，A 至少比 B 近多少 |
| 罩住 | `point road by fraction`，`by` 取 `range` 或 `vision`，比例为 0 到 1 |
| 绕多远 | `from to via who max_extra`，经过指定处比最短路最多多走多少 |
| 看得见 | `from to visible`，真假布尔值 |
| 放得下 | `point side`，正数边长的方形平地 |

种子是非负整数。块可显式写 `seed`，否则用 UTF-8 字符串 `全图种子:块ID` 的 SHA-256 前 8 字节转成大端无符号整数。全图种子默认 0。展开按 ID 排序，修补目标用 `块ID.类别.语义槽位`，槽位按用途命名。插入新物件时保留既有槽位名。每槽一条修补，支持 `move` 加 `at`、`delete`、`replace` 加 `with`。展开时须核对实际槽位是否存在。

运行 `python -m experimental.mapgen.design design.json`。结构错误给出对象 ID 和规则；文件级错误用 `$` 定位。通行关系按块、过口和实交道路图返回 `pass` 或 `fail`。其余关系返回 `needs the grid`，留给展开后的格子检查。
