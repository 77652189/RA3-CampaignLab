# 地图设计文件 v2

用 UTF-8 JSON。第一段用微缩的街区演示语法，含草图用途文字和示意的修补槽位。保存后可做结构检查。要直接出图，请复制后面的成图示例。

```json
{
  "version": 2,
  "seed": 37,
  "blocks": {
    "west": {"height": 3, "use": "老街", "at": [25,25]},
    "square": {"height": 3, "use": "广场", "at": [125,25]},
    "ridge": {"height": 4, "use": "高地", "at": [150,150]}
  },
  "roads": {
    "main": {"line": [[100,0],[100,100]], "width": "street"},
    "lane": {"line": [[25,50],[150,50]], "width": "alley", "ends": ["start","end"]}
  },
  "borders": {
    "map_edge": {"line": [[0,0],[200,0],[200,200],[0,200],[0,0]]},
    "west_scarp": {"line": [[0,100],[100,100]], "pass": ["foot"],
                   "segments": {"sealed": {"span": [20,90], "pass": []}}},
    "east_scarp": {"line": [[100,100],[200,100]],
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

成图示例可保存为 `design.json`，配合[流程](design.md#七流程)及 `Heidelberg_HB` 展开。东西各有一道坡口，分别检验避开一口后仍能走另一口。短路标出低地的运输线。

```json
{
  "version": 2,
  "seed": 37,
  "blocks": {
    "lowland": {"height": 3, "use": "wildland", "at": [2250,1920]},
    "ridge": {"height": 4, "use": "woodland", "at": [2250,2340]}
  },
  "roads": {
    "lane": {"line": [[1940,1850],[2520,1850]], "width": "alley", "ends": ["start","end"]}
  },
  "borders": {
    "frame": {"line": [[1800,1700],[2700,1700],[2700,2500],[1800,2500],[1800,1700]]},
    "scarp": {"line": [[1800,2150],[2700,2150]], "segments": {
      "west": {"span": [170,370], "pass": ["foot","vehicle","amphibian"]},
      "east": {"span": [580,740], "pass": ["foot","vehicle","amphibian"]}
    }}
  },
  "points": {
    "spawn": {"block": "lowland", "at": [2000,1950]},
    "goal": {"block": "ridge", "at": [2500,2340]},
    "muster": {"block": "lowland", "at": [2300,1950]}
  },
  "relations": {
    "westRoute": {"type": "通不通", "from": "spawn", "to": "goal", "who": "foot", "without": "scarp.east"},
    "eastRoute": {"type": "通不通", "from": "spawn", "to": "goal", "who": "vehicle", "without": "scarp.west"},
    "musterSpace": {"type": "放得下", "point": "muster", "side": 80}
  }
}
```

## 几何与编号

- 顶层必填 `version: 2` 和 `blocks`。各表用对象 ID 当键。ID 以英文字母开头，其余可用英文字母、数字、下划线和连字符。顶层各表的 ID 全局唯一，`base` 留给基础状态。过口 ID 在各自的界内唯一，引用写成 `界ID.过口ID`。未知字段和重复键会报错。
- XY 用整数世界坐标（有符号 32 位），+X 向东，+Y 向北。跨度、宽度和关系里的距离用世界单位。当前写出容器是 560×560 格、四边各留 30 格，格距 10，容器内的世界范围是 0–5000。内框还要留镜头余量。块的 `height` 用非负整数档。**一档 = 世界 70 单位 = .map 原始高度 1792**。默认水面高 200，邻海陆地从 3 档（210）画起，海水面可用 0 档标块。
- 城区先画道路，崖、岸和地图外缘用界。道路和界在交叉及 T 形接点自动拆段，共边只写一次，各段两侧的块由线围成。用块的 `at` 指定面内一点，再写 `height` 和 `use`。点在线上、落在未围合区域或重复命名同一个面时，报出块 ID。未围合的界报出界 ID。两侧都围块的路要求同高且同为陆地或水。
- 父块内部的独立围合也用 `at` 命名。可写 `parent` 校验直接父块。增加子块后，父块的锚点和仍属父块的点要留在子块以外。未命名的面自动成为块，有父块时继承其用途、高度和地面类型。无父块时用途为“未指定”，高度和类型取沿道路相邻的命名块（可经其他未命名块），缺省为 0 档陆地。展开前给每个陆地面指定可用的用途。块可选 `kind`（默认 `land`，水用 `water`）。点的 `at` 须严格在自己块的有效内部，`use` 可用中文，说明它要承担什么。
- 陆块的 `use` 影响贴图及装扮。展开使用 [`paint.USE_CLASS`](../../experimental/mapgen/paint.py) 的键，例如 `woodland`、`wildland`、`square`、`industrial`。草图校验接受其他用词，出图会报 `unknown use`。 `protagonist` 填本块套件里带真实占地的模板 ID，也可填 `building` 或 `garrison` 让工具选楼。离街的楼以块的 `at` 为原点，队伍集结点须另留净空。沿街放楼时，`build(..., fronts=...)` 要有该模板的小写 ID 及实测门面角（弧度）。
- 陆块可用 `kit` 指定原厂库里的套件 ID，例如在山镇的住宅以外给装卸岸指定 `StPetersburg_ST`。它决定块的地表、真楼、装扮及从该块向下看的陆崖。未命名的子块随父块继承套件。省略时用 `build()` 的默认套件。道路模型仍由 `road_kit` 选用。
- 冬季陆块可用 `snow`（开阔雪地）、`snow_woodland`（积雪林地）、`ice`（可走的结冰地面）。三种用途用原厂冬季地表，林地沿块的边缘向内成团种树，树种来自块的套件。用点与“放得下”关系保留建造和矿场净空。裂冰之间的开水用水块。
- 可用界把同一片水分成外锚地、港口等命名块。相邻水块共用水面和水底，岸坡沿陆水外缘生成。默认岸坡每横走 10 降高 4。陆地在 3 档（世界高度 210）时，从湾缘到最深处要约 200 世界单位才能达到海底 130（比水面低 70）。若两边都有岸，湾宽先留出约 400，再按实际轮廓查格子。
- 路宽档用 `alley`、`street`、`avenue`。路的折线实交处接成路口，整个路网必须连成一片，每段须在块内或沿块边。接到路或界的端点自动接合。只有 `ends` 明列的 `start`、`end` 可以悬空。省略 `road_kit` 时，路参与设计检查，地上可用命名路面块的 `ground_texture` 画出路带。启用模型时，[现有道路套件](../../experimental/mapgen/roads.py) 是 `Heidelberg_HB` 和 `Havana_HV`，弯道与路口要匹配套件的接口。
- 干地矩形外框可直接接街，展开器自动接上镜头缓冲区的地势。陆海混合外框需要预览镜头外缘。默认水面按设计水块外轮廓收边，画开放海岸时可用 `TerrainPlan.water` 把同一条岸线延伸到容器外。镜头水面可以延伸，离线检查仍按设计面裁范围。

## 氛围和地表

- 顶层 `commitments` 目前只接受 `mood`。地点、关型、剧情、时限与风格理由写在卡上。打开本地库的 `retail_moods`，按地点 `place`、气候 `climate` 和原版时段 `time_label` 选图。可填条目名称 `name`、原版图 ID，或带原版时段的 ID，例如 `camp_j07_yokohama_stewart@morning` 或 `camp_j07_yokohama_stewart@1`。时段只匹配原图已记录的值，库中没有黎明档时可选相近的固定清晨。倒计时、视野变化和日夜转换由任务脚本另做。省略承诺时沿用容器设置。
- 游戏图和编辑器图共用同一份氛围。它来自原版图的 `GlobalLighting`（含时段）、`WorldInfo.weather`、`FogSettings`、`EnvironmentData` 和 `PostEffectsChunk`。库从本机 `work/mapgen_probe/atmosphere.json` 导入条目及原始数据。
- 在陆地块加 `"ground_texture": "Snow_Iceland03"`，即可用库中的这张贴图打底。库列出了 SDK 描述中的贴图名，展开放之前还会查本机 `Art/Terrain` 下的 `Texture` 和 `BumpTexture` 文件。坡口、坡肩、崖面、岸坡和模型路面仍会选自己的贴图。画日式海岸时若富士山的 Hot Springs 贴图缺失，可用有可用地表的套件构建，再用 `TerrainPlan.cliffs` 指定有实测直段的富士山崖件。`ground.issues` 会列出缺件、露出的崖段和坡肩。出图后要在俯视图或游戏画面上看这些位置。

## 过口与状态

- 从渔屋一侧上到山径：在界的 `segments` 里写 `"serviceRamp": {"from": "fishingHouses", "to": "hillPath", "footpath": "ST_CargoContainer01"}`。林间平地也这样写，可以选碰撞形状合适的原版巨石。两端用已有点命名，有高差时从低到高。连线与界的唯一交点定开口，选一段高度一致的直边。生成器摆出两件有实际碰撞的原版物件，把小径夹在中间。草图把它当作步兵来路，成图关系按落地的地形和物件判断，兵车分流仍需拿本关的单位实测。要留街坡，用相同的地名写 `"pass": ["foot","vehicle","amphibian"]`。
- 沿岸做装卸码头：给陆水界写 `"shore": "quay"`。陆侧套件决定挡水墙样式，目前量过 `StPetersburg_ST`。墙件沿界连续铺设，岸后接平地，墙外留深水。会游泳的步兵和两栖车辆可从另设的缓坡登陆。码头界不另写 `pass` 或 `segments`。
- `pass` 允许 `foot`、`vehicle`、`amphibian`、`ship`。陆地容纳前三种，水容纳两栖和船。界和过口可写正数 `width`。过口 `span` 沿折线从起点累计弧长，左闭右开。结束于线尾的区间包含线尾，区间末值可写 `null` 表示线尾。区间不得重叠或越界。
- 过口的 `pass` 优先于整界默认值。只为分开地表或装扮画的同高陆界，也要显式写 `"pass": ["foot","vehicle","amphibian"]`，这样草图的块间关系才连通。显式空列表表示禁行，活动道路碰到它就报错。基础状态下，高差界须有开口或写 `closed_reason`。普通陆坡要填这三类兵种，限制到步兵时用上面的 `footpath` 做法。把坡口落在同一条直段上，每档从界线向两边各留 90 的坡面和额外一格平地。要验证过口之间确实有替代路线，分别写两条 `without`，每次排除一个过口。
- 同高陆地之间，显式 `pass: []` 的段会写进地图的通行格，段上开的口会保留原地形。把封闭段画在能解释限制的林缘或其他障碍上。只写兵种的 `pass` 可以推演草图。成图要验步兵通行和车辆绕行，各写一条关系。
- 每个命名状态都从 `base` 单独应用。先按 ID 替换声明的 `pass`，再按过口优先于整界的规则取值。也可用 `heights` 改已有水块的高度档，用 `playable` 选仍开放的块（省略时全开）。状态封住路所经过的口时，也要将碰到该口的路设为 `[]`。这些变化可先跑草图关系。常规构建只铺出基础状态的地形，状态改变了实际通行格时，要单独提供那个状态的地图才可在格子上验证。
- 舰队在雷达失守后才奉命进港：写 `"states": {"radarLive": {"hold": ["fleetEntry"]}, "radarDown": {}}`。给同一条来路写两条“通不通”，都填 `"order": "fleetEntry"`，在 `radarLive` 预期 `"reachable": false`，在 `radarDown` 预期能到。扣住航令时舰队等待，放行时离线照常检查实图航道是否通畅。任务用真实事件切换这两个状态，并按状态控制移动命令。

## 关系与修补

关系都可选 `state`，默认 `base`。`from`、`to`、`a`、`b` 引用块或点，`point` 引用点，`road` 引用路，`who` 取上述兵种。`via` 和 `only_via` 引用块、路、界或过口。

| `type` | 参数 |
|---|---|
| 通不通 | `from to who`，可选 `reachable`（布尔，默认真）、`only_via`（有路且移除该 ID 后无路）、`without`（避开该处）和 `order`（同时命名要核对的 `state`） |
| 谁先到 | `a b to who min_lead`，A 至少比 B 近多少 |
| 罩住 | `point road by fraction`，`by` 取 `range` 或 `vision`，比例为 0 到 1 |
| 绕多远 | `from to via who max_extra`，经过指定处比最短路最多多走多少 |
| 看得见 | `from to visible`，真假布尔值 |
| 放得下 | `point side`，正数边长的方形平地 |

种子是非负整数。块可显式写 `seed`，否则用 UTF-8 字符串 `全图种子:块ID` 的 SHA-256 前 8 字节转成大端无符号整数。全图种子默认 0。展开按 ID 排序，修补目标用 `块ID.类别.语义槽位`，槽位按用途命名。插入新物件时保留既有槽位名。每槽一条修补，支持 `move` 加 `at`、`delete`、`replace` 加 `with`。展开时须核对实际槽位是否存在。

从仓库根运行 `python -X utf8 -m experimental.mapgen.design design.json`。结构错误给出对象 ID 和规则，文件级错误用 `$` 定位。通行关系按块、过口和实交道路图返回 `pass` 或 `fail`。其余关系返回 `needs the grid`，留给展开后的格子检查。坡长、地表素材和楼的净空也要在展开后核对。

草图阶段用 `checks.draw_failures(design.load("design.json"), {}, "sketch.svg")` 生成查看图（两个模块均在 `experimental.mapgen` 下），在浏览器打开本地 SVG。北向上，蓝线是路，黄线表示显式通行的界或一段过口，文字用 ID，悬停可看用途。该函数的第二个参数可接展开后 `built.check_relations()`。每次保存成图，`MapBuild.write()` 会同时保存 `*-relations.svg` 和 `*-checks.md`。失败关系有定位分图，能定位到格子时会画红圈。

## 战役接口与导出

设计可在 `commitments` 里填默认的 `kit`、道路模型的 `road_kit` 和图底的 `ground_texture`。这样三者随设计传递，地块仍可覆盖自己的套件和贴图。顶层 `mission` 声明以下地图数据，各项按 ID 读取。

| 字段 | 值 |
|---|---|
| `points` | 世界坐标 `[x, y]`，用于正好落在界或路上的路点，以及镜头缓冲区里的标记。普通块内点沿用顶层 `points`。 |
| `starts` | 原生出生槽名 → 地点 ID。填 `Player_1_Start` 后可省略 `Player_2_Start` 和 `InitialCameraPosition`，两者默认使用同一点。 |
| `regions` | 触发区的多边形顶点，或 `{"point": "bayMouth", "radius": 50}`。后者以地点为中心，半边长为 50 世界单位。 |
| `paths` | 按行进顺序排列的地点 ID。每个地点最多属于三条路径，对应引擎的三格路径标签。 |
| `strongpoints` | 驻军楼名 → 地块 ID。该块必须有一座可驻军的主角建筑。 |
| `ore` | 单矿井记录写 `pad`（炼矿厂地点）、`node`（生成的矿井地点 ID）、`facing`（厂的朝向，45 + k×90 度），可写 `base` 指向它供应的玩家基地。由现有资源接口算矿轴和矿井朝向。 |

调用 `experimental.mapgen.export.export(build(design_file, library_file), container, stem)`。容器使用战役打包器对应的原始模板。输出 `<stem>-game.map`、`<stem>-editor.map`、`<stem>-locked.json` 和 `<stem>.py`。地图模块和游戏版并排放。模块由设计重建，任务用模块的 `mission(name)` 接入地图，再用 `m.site`、`m.mark` 和 `m.strongpoint` 引用发布的 ID。触发区和引擎路径标签已经写入，脚本可直接引用它们，`contract` 检查这些名字。

`STATE_BORDERS` 把 `base` 和每个命名状态映射到 `BORDERS` 中的引擎序号，0 为完整容器。状态选定地块时，取其外接矩形并按地形层的镜头余量外扩，到基础视界为止。边界相同的状态共用一个序号；开场启用 `base`，任务可按状态名查序号切换。矩形提供引擎视界，水深、过口和命令放行仍按地形与任务脚本各自执行。
