# 单位线交接（2026-10-26）

分支 `claude/units-models-b50716`，没合并到 main。代码都在 `experimental/units/`，大文件在 `work/units/`（不进 git）。

## 选定的路线

用户 2026-10-26 定的：**GPT 出三视图 → Tripo 生成 3D → Blender 修整 → 进游戏**；步兵仍然用原版骨架和动作。

为什么这样选：
- 用户的判断：主流 3D 工作方式已经是"AI 生成 + 人工微调"。从零手搭（游隼那条代码路线）改了 5 轮还是偏方、偏浅，质量未必比得过"代码 + Tripo"。
- 以前 Tripo 效果差，用户认为主要是参考图质量不够。现在改用 GPT 的图像模型出参考图，并定死出图标准。
- 尽量依靠 Blender 这类成熟的工业软件：质量稳定，经验也能积累下来（每个单位都留一份 .blend，可以手工改）。
- 原版模型能完整解码（今天验证的），所以"改原版模型"仍然可用。步兵靠它沿用原版骨架和动作，车辆缺部件时也能拿原版部件来拼。

被放弃的：纯代码搭模型当主力（太慢，也不像原版）；本地 AI 直接生成网格（表面软，2026-10-17 已经放弃过）；只给一张正面图去生成 3D（侧面和背面会对不上）。

## 流程和工具（每一步都实际跑通过）

| 步骤 | 工具 | 产出 |
|---|---|---|
| 1. 原版参考图 | `retail_sheet.py`：解码原版网格（`retail_mesh.py`），配原版贴图和阵营色，渲成 2×2 的四格图 | `work/reference/sheets/<名>_grid.png`（已有守护者、雅典娜炮） |
| 2. GPT 三视图 | `concept_gpt.py <单位>`：用 Codex 命令行调用你订阅里的 GPT 图像模型，附上参考图；画风、版式、单位说明都写在脚本里 | `work/units/<单位>/gpt/v<N>.png`，以及裁好、比例统一的 `v<N>_views/front/left/right/back.png` |
| 3. Tripo 生成 3D | 网页 studio.tripo3d.com：多视图（前、左侧、右侧、后）→ 生成（分部件）→ 贴图生成（打开去光处理）→ 导出 GLB | `work/units/<单位>/tripo/*.glb` |
| 4. Blender 修整 | `tripo_unit.py <单位>`：按部件分成车体、炮塔、炮管，减到原版面数预算，烘焙颜色和法线，按蓝色做阵营色遮罩，摆好守护者的骨骼 | `work/units/<单位>/game/`：贴图、parts.json、预览图、图标、`<单位>.blend` |
| 5. 按钮和头像 | `button_icon.py compose button / portrait` | 同一个文件夹里的 `.tga` |
| 6. 离线检查 | `check_model.py <w3x> <单位 xml>`：检查文件能否解析，贴图、骨骼、碰撞盒是否齐全，有没有共面闪烁，面数是否超预算；`tests/test_check_model.py` 用故意做坏的模型证明每一项都能抓到问题 | 不通过的项会列出来 |
| 7. 进游戏 | 时滞炮车用 `make_campchrono.py`（其他单位照它写一个） | mod `CampChrono1` |

**出图标准**（在 `concept_gpt.py` 里）：
- 一张方图分四格：正面、侧面、背面三张同一比例的正交视图，加一张从游戏镜头高度看的斜视图。
- 四格必须在同一次生成里出，背景纯灰 `#D0D0D0`，图上不要文字。
- 画风照原版同阵营单位：盟军是冷银灰金属、深色面板缝、青色小灯。
- 阵营色一律画成饱和的蓝色，只画在凸起的顶部装甲上，这样后面能按颜色自动做遮罩。

## 时滞炮车样品做到哪一步

- 已完成：GPT 概念图 v2 → Tripo 模型（185 万面、24 个部件、4K 贴图）→ 游戏模型 4000 面（车体 2500、炮塔 1100、炮管 399）。生产按钮、头像、中文名都有。离线检查通过（只有车体内部一处面积 0.08 的小重叠，可以忽略）。`CampChrono1` 已编译并装进 Mods（装的时候游戏没在运行），能从 CNV 战车工厂生产。默认 `CNV_DEPLOY=0`，不用展开就能开火，方便看模型。
- **测试台（2026-10-26 下午）通过**：开局 1 秒和 29 秒各开一炮，启示录都被打蓝；炮口烟在炮管尖；行进中车身和炮塔各转各的；战车工厂能造（950 元、10 秒），新车正常开出；名字、头像、按钮、中文说明都对。俯视角阵营色看得清楚，大小和守护者相当。对比图在 `work/units/chronolag/review/bench_1026.png`，原始帧在 `work/testbench/runs/CampChrono1_mcp_1026_170643/`。
- 游戏里比 Blender 预览暗、偏棕灰，守护者偏银灰。如果用户觉得暗，把 `CNV_CHRONO_LEVEL` 从 62 调高（原版盟军车辆是 62 到 80）后重新构建。
- 用户认可风格（"质量很高"），随后说太暗、青色光要看得见：亮度改成不压暗（85）、加冷色、发光识别放宽并提成饱和青色，测试台对比图 `work/units/chronolag/review/bench_1026_bright.png`。

## 冰幕工兵、冰雕（2026-10-26 测试台通过）

- 冰墙 `CNIceWall`（160 见方）、冰核 `CNIceSeed`、碎冰 `CNIceRubble` / `CNIceRubbleS`：用原版冰岛地图的冰川道具 `IL_GLACIER*` 拼的（`ice_kit.py`，从世界编辑器资源包 `WBData.big` 解码），贴图用原版冰川的，压暗偏青（原样在游戏里白成一片）。
- 工兵：不重做模型，只换贴图 `CNIceEngineer`（衣服浅蓝灰、工具箱冰青色），XML 里用 `<Texture Original="AUEngineer" New=...>`。
- 冰雕 `CNIceSculpt`：GPT 四格图 → Tripo 多视图（50 积分）→ `tripo_unit.py` 的道具分支（1599 面）→ `ice_kit.prop`（颜色对齐冰墙）。
- 换装函数在 `ice_look.py`：`dress(unit, model, leaves)` 换掉地堡的模型、残骸、小爆炸（改成原版解冻音效）；`dress_engineer(unit)`；`rubble()` 碎冰物体。测试关 `CampIceLook`，截图 `work/units/ice/review/bench_1026.png`。
- 坑：原版冰冻步兵的碎块（`InfantryShatter_Collapse`）是中立方，染成了红色，不能用；冰墙被打碎留碎冰，化掉（FADED）不留。
- **已接进正式单位**（总控批准，只换外观）：`icewall.py` 的 `wall()` / `seed()` / `engineer()` 默认穿冰的外观（`dress` / `dress_engineer` / `rubble` 挪进了 `icewall.py`；长条墙用 `CNIceBar`，方块用 `CNIceWall`，`model=None` 保留地堡）；`festival.py` 的冰雕是冰龙，雪堆保留地堡外观。pytest 109 过；测试台 `ice_block`、`ice_build` 都 PASS。构建依赖 SDK Art 里的模型：换机器先跑 `ice_kit.py`。
- 发现（不归单位线）：工兵站在冰核旁边造，160 见方的墙长出来会把他包在里面。
- 已知可以改进的地方：
  - UV 切成了很多小块，贴图利用率低。可以试更大的合并角度，或者手工展 UV。
  - 概念图还没画出"展开支腿"。
  - 履带没有滚动贴图，因为守护者的 TreadScrollingMap 被去掉了。

花费：GPT 出图 2 张（在订阅额度内）；Tripo 用了 80 积分（生成 60、贴图 20），还剩 3125。

## Tripo 上传需要用户做什么

内置浏览器没有上传文件的工具，页面脚本也取不到本机文件（试过本机服务和剪贴板，都被拦了）。所以目前每个单位要请用户：
1. 在 Tripo 页面登录（会话会保持）；
2. 把 `v<N>_views/` 里的 front、left、right、back 四张图拖进左栏的四个格子（前、左侧、右侧、后）。

其余（选参数、点生成、补贴图、导出、下载）都由 Claude 来做。注意：浏览器面板被隐藏或者会话不在窗口里显示时，Tripo 不渲染模型，但导出对话框仍然能用。下载的文件在 `~/Downloads`，要核对 glTF 头里记的长度。

## 要全自动需要什么

任选一条：
- **Claude in Chrome 扩展**：在用户的 Chrome 里装上扩展并登录 Tripo，它有上传文件的工具。不额外花钱，最省事。
- **Tripo API key**（platform.tripo3d.ai）：可以直接调用多视图生成和贴图接口，完全脚本化，最稳定；但 API 是单独计费的，不走 Studio 的订阅积分，要用户去开通并给 key。
- GPT 出图已经是全自动的，不需要额外条件。

## 下一步

1. 用户看调亮后的时滞炮车、冰幕工兵、冰雕、车队运输车截图。
2. 接着做自由号（平台主体用 Tripo 或代码，炮塔和建筑件取原版）。它现在套的是基洛夫 `SUBomberAircraft_SKN`，XML 点名的骨骼有 `B_Bombs`、`B_Prop05`、`FX_Fire_02/03`、`FX_WEAPON`，新模型要带上这些骨骼，或者改 XML。

## 车队运输车（2026-10-26 测试台通过）

- 矿车的矿石绘制模块 `ModuleTag_Draw_Ore` 换成货柜 `CNConvoyCargo`（`convoy_look.dress`）。货柜是原版雪地货柜 `AP_SNOWYCARGOCONTAINER01` 缩到 0.72 倍、放进车斗（`convoy_kit.py`，位置写在模型里，按车的原点画）。行驶中跟车走。截图 `work/units/convoy/review/bench_1026.png`。
- 坑：Blender 预览里的位置和游戏里差约 3 个单位（游戏里偏后），以测试台为准。
- 同样还没接进 `experimental/cnv/units/convoy.py`，等总控答复。
3. 改 `experimental/cnv/units/*.py` 里的模型引用之前先问总控（关卡线在用这些单位跑测试）。新体系 `experimental/cnv` 还不支持挂自制模型，接入方式要和总控商量。

## 坑

- 在 Git Bash 里用 `tasklist | grep` 查游戏进程会漏掉（中文编码问题）。查红警3 是否在运行要用 PowerShell：`Get-Process | ? ProcessName -match ra3`。
- worktree 里的 `labpaths` 会把 SDK 推算到错误的位置。构建时要设 `CNV_SDK=C:\Users\63097\Documents\RA3Modding\sdk\RA3ModSDK3`。本分支的 `work` 是指向主仓库 `work/` 的目录链接（junction）。
- 原版网格的坐标都是相对骨骼的，每个网格还带一张骨骼编号对照表（详见 `retail_mesh.py` 开头）。不套骨架时车体看着对，但炮管和天线会缩在原点附近。
- Tripo 打开"分部件生成"后会自动关掉"贴图生成"，要在生成完之后用"贴图生成"另外补，参考图会自动带过来。
- 导出的 Tripo 模型是 +X 朝前、Z 朝上（前提是前视图放进了"前"那一格），和原版一致。
