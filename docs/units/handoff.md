# 单位线交接

分支 `claude/units-models-b50716`，做完一件报总控，由总控验收后合进 main。工具代码在 `experimental/units/`，大文件在 `work/units/`、`work/reference/`（不进 git）。

## 硬约束

- 接入规矩（总控定的，`docs/architecture.md`「各线负责的文件」）：单位线管 `experimental/units/`、`docs/units/` 和 `experimental/cnv/units/` 里的外观接线；只换外观（模型、贴图、按钮头像、残骸、死亡特效），尺寸、血量、速度、机制归关卡线。每个外观函数都能用 `model=None` / `texture=None` / `cargo=None` 关掉。
- 时滞炮车的 `experimental/cnv/units/chronolag.py` 是总控特许单位线写的一次例外：机制照 `make_campnew35.py` 原样搬；合进 main 以后机制归关卡线，单位线只管 `dress()` 和外观。
- 要动关卡线的文件（`experimental/cnv/devices/`、`experimental/cnv/missions/`、`experimental/cnv/parts.py`、`experimental/cnv/build.py` 等），先在报告里说或者先问关卡线，不要等合并时才被发现；共用文件只加需要的那几行，用 Edit 改，不顺手重构。

## 现状

| 单位 | 外观从哪来 | 接进 `experimental/cnv` |
|---|---|---|
| 时滞炮车 `CNChrono` | GPT 四格图 → Tripo（分部件）→ `tripo_unit.py chronolag` → `make_campchrono.py`；按钮、头像 `ui_kit.py` | `chronolag.py`（`dress()` 默认穿：模型、按钮、头像、名字、展开时的青色光）；检查 `chronolag hit` / `packed` 在测试台上 PASS |
| 冰幕工兵：冰墙 `CNIceWall` / 长条 `CNIceBar`、冰核 `CNIceSeed`、碎冰 `CNIceRubble`、工兵贴图 `CNIceEngineer` | 原版冰岛冰川 `IL_GLACIER*` 拼装（`ice_kit.py`），工兵只换贴图 | `icewall.py` 默认穿；`ice_block`、`ice_build` PASS |
| 冰雕 `CNIceSculpt`（冰龙） | GPT 四格图 → Tripo 多视图 → `tripo_unit.py` 道具分支 → `ice_kit.prop` | `festival.sculpture` 默认穿 |
| 雪堆 `CNSnowBank` | 高度场直接生成（`ice_kit.bank`，原版没有雪堆），贴图 `CNSnow` 程序生成 | `festival.bank` 默认穿；现在没有任务用雪堆（广场的墙是抬高的地形），只在 `ice_look.py` 里 |
| 车队运输车 `CNConvoyCargo` | 原版矿车，矿石模块换成原版雪地货柜（`convoy_kit.py`） | `convoy.py` 默认穿；A4 `stop`、`win` PASS |
| 自由号 `CNLiberty` + 女神像 `CNLibStatue` + 陀螺环 `CNLibRings` + 跃迁充能 `CNLibCharge` | 用户定的"飞起来的自由岛"（场景图 `work/units/libertyisle/gpt/h6.png`）→ 三视图 v4 → Tripo（整块）→ `tripo_unit.py libertyisle` → `liberty_kit.py`（女神像用原版纽约 `NY_LIBERTY`）；宽 280 是用户选的 | `liberty.py` 默认穿（`liberty.dress`）；敌方自由号报警时 `devices/carrier.py` 用 `liberty.charging` 点亮充能（总控放行的一行） |

各单位外观的写法、参数和测试台上看出来的问题，写在对应脚本的开头说明和注释里（`liberty_kit.py`、`ice_kit.py`、`chronolag.py`、`liberty.py`）。截图在 `work/units/<单位>/review/`。

**构建依赖**：这些模型和图写在 SDK 共享的 `Art/` 里，不进 git。换机器或清过 SDK 要重跑：
- 只靠原版就能重建：冰墙、长条冰墙、冰核、碎冰、工兵贴图、雪堆（`ice_kit.py`），货柜（`convoy_kit.py`），女神像（`liberty_kit.py` 的一部分）。
- 只能从 `work/` 里的原件重建（gitignore，丢了要从 Tripo 账号重新导出）：冰雕（`work/units/icesculpture/tripo/icesculpture_v1.glb` → Blender 跑 `tripo_unit.py icesculpture` → `ice_kit.py CNIceSculpt`），时滞炮车（`tripo_unit.py chronolag` → `make_campchrono.py`；按钮、头像的图在 `work/units/chronolag/game/` → `ui_kit.py`），自由号平台（`work/units/libertyisle/tripo/libertyisle_v1.glb` → `tripo_unit.py libertyisle` → `liberty_kit.py`）。`ice_kit.py` 缺冰雕原件时跳过它、照做其余，并打印怎么补。

花费：GPT 出图约 20 张（订阅额度内）；Tripo 用了 180 积分（时滞炮车 80、冰雕 50、自由号 50），剩 3025。

## 下一步

1. 自由号剧情说法，等用户定：提案是"她本来就是灯塔 + 埃菲尔铁骨是超时空天线"（设计规律和说明在 `concept_gpt.py` 的 `libertyisle`）。
2. 自由号可选：玩家自己跃迁时的闪光要给跃迁加约 1 秒准备时间（机制，归关卡线定）；跃迁取消时让充能立刻熄灭，可以把 `carrier.py` 改用 `liberty.discharged`（要关卡线同意）；五个炮塔座骨骼 `TURRET01..05` 还没接线（总控：炮塔仍是跟着飘的无人机）。
3. 时滞炮车可以改进：UV 小块太多、概念图没画展开支腿、履带没有滚动贴图。A3 时停区机关和它是不是一回事，等策划线定。
4. 雪堆还偏光滑，像枕头，可以加脚印、铲痕。

## 流程和工具

| 步骤 | 工具 |
|---|---|
| 原版参考 | `retail_mesh.py`（解码原版网格；读静态资源流和世界编辑器资源流 `WBData.big`，地图道具只在后者）、`retail_texture.py`、`retail_sheet.py`（渲 2×2 四格图到 `work/reference/sheets/`） |
| 概念图 | `concept_gpt.py <单位> [--hero] [--from 图]`：Codex 命令行调 GPT 图像模型，全自动；画风 `STYLE`、版式 `LAYOUT`、单位说明 `BRIEFS` 都在脚本里；大单位先出场景图（`--hero`）定设计，再用 `--from` 照它出四格图 |
| 3D | Tripo 网页（见下）→ `tripo_unit.py <单位>`：车辆分车体、炮塔、炮管；`kind='prop'` 道具（一整块）；`kind='platform'` 大平台（骨骼按基洛夫的名字） |
| 原版拼装、生成 | `ice_kit.py`（冰、雪堆、冰雕上色）、`convoy_kit.py`（货柜）、`liberty_kit.py`（自由号的平台、女神像、陀螺环、充能） |
| 按钮和头像 | `button_icon.py compose button|portrait` 出图 → `ui_kit.py`（写进 `Art/`，新单位在 `ui_kit.UNITS` 加一行，`dress()` 照 `chronolag.dress` 引用） |
| 写 W3X | `to_w3x.py`（车辆，含亮度、冷色、发光参数）、`campaign/w3x.py` 的 `rig_model`、`lathe`、`write_texture` |
| 离线检查 | `check_model.py <w3x> [单位 xml] [--budget N]`（`tests/test_check_model.py` 证明每项都能抓到问题） |
| 看外观 | 测试关 `ice_look.py`（`CampIceLook`）、`convoy_look.py`（`CampConvoyLook`）、`liberty_look.py`（`CampLibLook`：充能再跃迁）、`build.py chronolag --check hit`（`CampLagHit`） |

出图标准（`concept_gpt.py`）：一张方图分四格（正、侧、背三张同比例正交视图 + 一张斜视图），同一次生成，背景 `#D0D0D0`，不要文字；阵营色画成饱和蓝色、只在凸起的顶部装甲上。

## Tripo 怎么用

- 网址是 `studio.tripo3d.com`（`.ai` 是另一个版本）。多视图是上传方式的第二个图标（四格），第三个是"最多 10 张"。
- 内置浏览器没有上传文件的工具，每个单位要请用户：登录 Tripo（这个浏览器面板的登录会保持），把 `v<N>_views/` 的 front、left、right、back 拖进四格（左上前、右上左侧、左下右侧、右下后）。其余步骤 Claude 来做。
- 面板窄时开关在可视区外：先 `resize_window` 到 1280×800。打开"去光处理"。
- 打开"分部件生成"会自动关掉"贴图生成"，生成完再用"贴图生成"补；分部件开关点"生成"后可能被页面复位（自由号那次扣了 30 却没分部件），生成前再看一眼。
- 生成后进"贴图生成"页，参考图会自动带过来（刷新生成页反而会丢）；贴图 20 积分。
- 导出对话框在截图里看不见，用页面脚本读、改文件名、点"导出"；按钮变灰就是在打包，两百万面约一分钟，先落成 `.tmp` 再改名 `.glb`，到 `Downloads`；核对 glTF 头里的长度。模型太大时视口可能加载失败（QUIC 报错），刷新再点一次资产卡片。
- 全自动的办法查过，用户 2026-10-28 定了暂不用，继续走网页：
  - Claude in Chrome 扩展：用户的学校账号没有权限，用不了。
  - Tripo 官方终端 `tripo-cli`（`npm install -g tripo-cli`，`tripo login --region cn` 授权）：支持本地多图出模型和 `mesh segment` 分部件，`tripo mcp` 能当 MCP 跑，已在本机装好登录过。但它走 API 积分，**网页订阅积分不能用**（帮助中心原话"网页端积分不等于 API 积分"），API 账户余额是 0。
  - API 价格（[定价页](https://developers.tripo3d.com/zh/pricing)）：1 积分 = ¥0.07，订阅折下来约 ¥0.0225，贵约 3 倍。四视图出模型 20（带贴图 30），分部件 +20，高清贴图 +10；一个带贴图、分部件的单位约 50 到 60 积分，约 ¥3.5 到 4.2。失败的任务不扣费。
  - 官方 Blender 插件只做单张图出模型，官方 MCP（`tripo-mcp`，alpha）只做文字或单图加 Blender 操作，都不支持四视图和分部件，没用。
  - 内置浏览器没有上传文件的工具，也拦截网页访问 127.0.0.1，本机起服务器喂图走不通；DCC Bridge 只能把模型推进 Blender，帮不了上传。

## 坑

- **游戏美术**：
  - 游戏阳光下白色、浅色会发白一片：原版冰川贴图要压暗偏青（`ice_kit.DARK`），雪也一样（`ice_kit.SNOW_RGB`）；原版地图道具偏黄（女神像的铜绿要每通道压一点红、低高光，`liberty_kit.COPPER`）。
  - 时滞炮车的亮度系数封顶在 1，设的值低于烘焙贴图的中位亮度时只会压暗。
  - 原版碎冰物体是中立方，会染成红色。
  - Blender 预览里的位置、颜色和游戏里有差别，以测试台为准。
  - 几百单位宽的模型，`tripo_unit.renders` 的相机要加大裁剪距离（默认 100 会渲出空图）。
  - 大单位先看在 RTS 镜头里的尺寸和能看见的面：镜头从上往下看，平台底下的东西（自由号原来放在龙骨下的光圈）完全看不见；细于约 1 单位的部件在正常缩放下像头发丝。
  - 程序生成的起伏要用几种不成倍数的波长叠加，波长对齐会一节一节等距鼓起（雪堆第一版像白毛毛虫）。
  - 只在某个模型状态下出现的部件：默认状态写 `<Model Name="" />`；没亮的部件可以用动画平移藏到地图下面。
  - 原版青色超时空粒子都是一次性的，要一直亮的光效就复制一个会循环的粒子再改颜色（`chronolag.dress` 的展开光）。我们的模型没有原版要的骨骼时（比如 `FX_Laser`），粒子会冒在模型原点。
- **XML**：`FXListBehavior` 不能变空（编译器报内容不完整），要换特效而不是删掉。
- **脚本、能力**：
  - 脚本设模型状态用 `UNIT_SET_MODELCONDITION_GENERIC(单位, 状态, 秒数)`，秒数 0 表示一直保持，用 `UNIT_CLEAR_MODELCONDITION` 清掉。
  - 能力的 `ActiveModelCondition` 在没有准备时间的能力上看不到（自由号跃迁试过）。
- **测试台**：
  - 场景别放在 `west field` 西边（x < −100 是浅水，工兵会骑水上摩托过去），也别压着别的单位摆。
  - 暂停状态下 `bench_look` 可能拍到菜单，先 `bench_wait 0.5`。
  - 暂停模式（`hold=true`）下脚本计时器和带时长的模型状态照样按真实时间走，两次调用之间的空档也会算进去。要按秒对时间的效果，用 `bench_start(hold=false)` 连续跑，或者只用一次 `bench_watch`。
  - 脚本化检查（`build.py --check`、`bench_client`）默认 8 倍速（ADR 0007）；用脚本化检查看动画、特效时设 `RA3_BENCH_SPEED=1`。手动驾驶（`bench_start`）仍是 1 倍。
  - `cnv_check` 用的是主仓库的代码。要测本分支的改动，先在本工作目录跑 `build.py <名> --check <项> --plan`（编译并装进 Mods），再 `cnv_check(build=false)`；主仓库还没有这个检查时，手动 `bench_start` + `bench_watch(lines=n)` + `bench_counters`，再用本分支的 `build.py <名> --check <项> --no-build --judge "<计数文本>"` 判定。
- **环境**：
  - 查游戏进程用 PowerShell `Get-Process | ? ProcessName -match ra3`（Git Bash 的 tasklist 会漏）。上测试台前单独查一次，再看 `python -I ra3voice/reslock.py status`（在主仓库目录跑）；测试台有两个位置，另一个被占时可以用空的那个。
  - worktree 里构建要设 `CNV_SDK=C:\Users\63097\Documents\RA3Modding\sdk\RA3ModSDK3`；本分支的 `work` 是指向主仓库 `work/` 的目录链接。跑命令别 `cd` 出工作目录，用绝对路径或子 shell。
  - 编译器报错的详细信息在 `SDK/_build_<mod>Map.log`，"找不到原版美术文件"那几行是正常的。
- **原版网格**：坐标是相对骨骼的，要按网格自带的骨骼编号对照表套骨架（`retail_mesh.py` 开头）；地图道具没有骨骼编号，整块在模型空间。编译后的 UV 是 V 朝下，写进我们的 W3X 要 `1 - v`。
