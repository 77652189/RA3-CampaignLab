# 单位线交接（2026-10-26 晚）

分支 `claude/units-models-b50716`，没合并到 main（已合进 main 到 08d73b3，等总控验收）。工具代码在 `experimental/units/`，大文件在 `work/units/`、`work/reference/`（不进 git）。

## 现状

| 单位 | 做法 | 测试台 | 接进 `experimental/cnv` |
|---|---|---|---|
| 时滞炮车 `CNChrono` | GPT 四格图 → Tripo（分部件）→ `tripo_unit.py` → `to_w3x.py`；mod `CampChrono1`（`make_campchrono.py`） | 通过：生产、开火、炮塔、按钮头像；用户认可风格，按用户意见调亮、青色光可见（`work/units/chronolag/review/bench_1026_bright.png`） | 没有（新体系还没有它的单位模块） |
| 冰幕工兵：冰墙 `CNIceWall` / 长条 `CNIceBar`、冰核 `CNIceSeed`、碎冰 `CNIceRubble`、工兵贴图 `CNIceEngineer` | 原版冰岛冰川 `IL_GLACIER*` 拼装（`ice_kit.py`），工兵只换贴图 | 通过（`work/units/ice/review/bench_1026.png`）；`ice_block`、`ice_build` PASS | 已接：`icewall.py` 默认穿冰的外观（提交 0af20c1） |
| 冰雕 `CNIceSculpt`（冰龙） | GPT 四格图 → Tripo 多视图 → `tripo_unit.py` 道具分支 → `ice_kit.prop` | 通过（同上截图） | 已接：`festival.py`（雪堆仍是地堡外观） |
| 车队运输车 `CNConvoyCargo` | 原版矿车，矿石模块换成原版雪地货柜（`convoy_kit.py`） | 通过（`work/units/convoy/review/bench_1026.png`）；A4 `stop`、`win` PASS | 已接：`convoy.py`（提交 27f8b9a） |
| 自由号 `CNLiberty` + 女神像 `CNLibStatue` | 用户否了航母版（v1），定为"飞起来的自由岛"：场景图 `work/units/libertyisle/gpt/h6.png` 定设计 → 三视图 v4 → Tripo（整块，没分部件）→ `tripo_unit.py libertyisle`（`kind='platform'`）→ `liberty_kit.py`（平台按时滞炮车的调色写；原版纽约 `NY_LIBERTY` 女神像去掉基座、转向前方、火炬改青色发光，站在核心柱顶 `STATUE` 骨骼上）；测试关 `liberty_look.py`（`CampLibLook`） | 看过两次：宽 400 太大、女神像顶到镜头；按用户选的缩到宽 280（`liberty_kit.SCALE`），女神像约等于核心柱高（`work/units/libertyisle/review/bench280_*.png`） | 已接：`liberty.py` 默认穿（`liberty.dress`，平台 + 女神像 + 会转的陀螺环 `CNLibRings`；`model=None` 关掉）；五个炮塔座做成骨骼 `TURRET01..05`，没接线（总控 2026-10-27：跃迁半径保持 150，炮塔仍是跟着飘的无人机） |

接入规矩（总控定的，`docs/plan.md` 分工表）：单位线只换外观（模型、贴图、残骸、死亡特效），尺寸、血量、速度、机制归关卡线。每个外观函数都能用 `model=None` / `texture=None` / `cargo=None` 关掉。

**构建依赖**：这些模型写在 SDK 共享的 `Art/` 里，不进 git。换机器或清过 SDK，先跑 `ice_kit.py` 和 `convoy_kit.py`（时滞炮车由 `make_campchrono.py` 写）。
- 只靠原版就能重建的：冰墙、长条冰墙、冰核、两种碎冰、工兵贴图（`ice_kit.py`）、货柜（`convoy_kit.py`）。
- 只能从 `work/` 里的 Tripo 原件重建的（gitignore，丢了要从 Tripo 账号重新导出）：冰雕 `CNIceSculpt`（`work/units/icesculpture/tripo/icesculpture_v1.glb` → Blender 跑 `tripo_unit.py icesculpture` → `ice_kit.py CNIceSculpt`）、时滞炮车 `CNChrono`（`tripo_unit.py chronolag` → `make_campchrono.py`）、自由号 `CNLiberty`（`work/units/libertyisle/tripo/libertyisle_v1.glb` → `tripo_unit.py libertyisle` → `liberty_kit.py`，女神像从原版重建）。`ice_kit.py` 缺冰雕原件时跳过它、照做其余，并打印缺哪个文件、怎么补。

花费：GPT 出图约 20 张（订阅额度内）；Tripo 用了 180 积分（时滞炮车 80、冰雕 50、自由号 50），剩 3025。

## 下一步

1. **自由号**：外观已接进 `liberty.py`。模型带基洛夫 XML 点名的骨骼（`B_Bombs`、`B_Prop05`、`FX_Fire_02/03`、`FX_WEAPON`，位置是估的）和炮塔座骨骼 `TURRET01..05`（`liberty_kit.sockets` 从模型量出来：四角加西侧，东侧是升降井）。剩下的：
   - 陀螺环：第一次太粗（`bench_rings_a/b.png`），调细后在测试台上看过，转动、发光正常（`bench_rings_thin_a/b.png`）。
   - 还没做：底部光圈跃迁时张开、头冠七根光芒做跃迁倒计时（设计见 `concept_gpt.py` 的 `libertyisle` 说明和这次对话：剧情说法"她本来就是灯塔 + 埃菲尔铁骨是超时空天线"等用户定）。
   - 设计规律（大型空中要塞，参考各家即时战略游戏）：一个视觉中心、威胁朝下、悬浮旋转部件显科技、盟军流线型而不是方块、弱点是看得出的独立模块。写在 `concept_gpt.py` 的 `libertyisle` 说明里。
2. 时滞炮车接进新体系：新体系里还没有它的单位模块，要和总控商量放哪。
3. 雪堆（`festival.bank`）还没有自己的外观。
4. 时滞炮车可以改进：UV 小块太多、概念图没画展开支腿、履带没有滚动贴图。

## 流程和工具

| 步骤 | 工具 |
|---|---|
| 原版参考 | `retail_mesh.py`（解码原版网格；读静态资源流和世界编辑器资源流 `WBData.big`，地图道具只在后者）、`retail_texture.py`、`retail_sheet.py`（渲 2×2 四格图到 `work/reference/sheets/`） |
| 概念图 | `concept_gpt.py <单位>`：Codex 命令行调 GPT 图像模型，全自动；画风 `STYLE`（盟军、冰）、版式 `LAYOUT`、单位说明 `BRIEFS` 都在脚本里 |
| 3D | Tripo 网页（见下）→ `tripo_unit.py <单位>`：车辆分车体、炮塔、炮管；`kind='prop'` 走道具分支（一整块，不做阵营色和骨骼） |
| 原版拼装 | `ice_kit.py`（冰川拼冰墙、冰核、碎冰；冰雕上色）、`convoy_kit.py`（货柜放进矿车） |
| 写 W3X | `to_w3x.py`（车辆，含亮度、冷色、发光参数）、`campaign/w3x.py` 的 `rig_model` |
| 离线检查 | `check_model.py <w3x> [单位 xml] [--budget N]`（`tests/test_check_model.py` 证明每项都能抓到问题） |
| 看外观 | 测试关 `ice_look.py`（`CampIceLook`）、`convoy_look.py`（`CampConvoyLook`）、`make_campchrono.py`（`CampChrono1`） |

出图标准（`concept_gpt.py`）：一张方图分四格（正、侧、背三张同比例正交视图 + 一张斜视图），同一次生成，背景 `#D0D0D0`，不要文字；阵营色画成饱和蓝色、只在凸起的顶部装甲上。

## Tripo 怎么用

- 内置浏览器没有上传文件的工具，每个单位要请用户：登录 Tripo（这个浏览器面板的登录会保持），把 `v<N>_views/` 的 front、left、right、back 拖进多视图四格（左上前、右上左侧、左下右侧、右下后；多视图是上传方式里的第三个图标）。其余步骤 Claude 来做。
- 面板窄时开关在可视区外：先 `resize_window` 到 1280×800。打开"去光处理"。
- 打开"分部件生成"会自动关掉"贴图生成"，生成完再用"贴图生成"补。
- 面板隐藏时截图里看不到对话框，但页面脚本能读、能点。导出先变成 `.tmp`，写完才改名成 `.glb`；核对 glTF 头里的长度。
- 全自动的办法：Claude in Chrome 扩展——用户的学校账号没有这个权限，用不了；开 Tripo API key（单独计费）；或者用 Playwright 驱动本机的 Edge（没做）。内置浏览器拦截网页访问 127.0.0.1（`ERR_BLOCKED_BY_CLIENT`），本机起服务器喂图的路走不通。DCC Bridge 只能把做好的模型推进 Blender，帮不了上传。
- 网址是 `studio.tripo3d.com`（`.ai` 是另一个版本）。新版多视图是上传方式的第二个图标（四格），第三个是"最多 10 张"。
- 生成后进"贴图生成"页，参考图会自动带过来（刷新生成页反而会丢）；贴图 20 积分。分部件开关点"生成"后会被页面复位，这次实际没分部件（扣 30）。
- 导出对话框在截图里看不见，用页面脚本读、改文件名、点"导出"；按钮变灰就是在打包，两百万面的模型大约一分钟，落到 `Downloads`。模型太大时视口可能加载失败（QUIC 报错），刷新再点一次资产卡片。

## 坑

- **游戏美术**：
  - 原版冰川贴图原样在游戏里白成一片，要压暗偏青（`ice_kit.DARK`）。
  - 时滞炮车的亮度系数封顶在 1，设的值低于烘焙贴图的中位亮度时只会压暗。
  - 原版碎冰物体是中立方，会染成红色。
  - Blender 预览里货柜的位置和游戏里差约 3 个单位，以测试台为准。
  - 几百单位宽的模型，`tripo_unit.renders` 的相机要加大裁剪距离（默认 100 会渲出空图）。
  - 大单位先看在 RTS 镜头里的尺寸：宽 400 时一屏只装得下一角，女神像顶到镜头。
  - 原版地图道具在游戏阳光下偏黄（女神像的铜绿）：每通道压一点红、低高光（`liberty_kit.COPPER`）。
- **XML**：`FXListBehavior` 不能变空（编译器报内容不完整），要换特效而不是删掉。
- **测试台**：
  - 场景别放在 `west field` 西边（x < −100 是浅水，工兵会骑水上摩托过去）。
  - 暂停状态下 `bench_look` 可能拍到菜单，先 `bench_wait 0.5`。
  - `cnv_check` 编译的是主仓库的代码。要测本分支的改动，先在本工作目录跑 `build.py <名> --check <项> --plan`（它会编译并装进 Mods），再 `cnv_check(build=false)`。
- **环境**：
  - 查游戏进程用 PowerShell `Get-Process | ? ProcessName -match ra3`（Git Bash 的 tasklist 会漏）。上测试台前单独查一次，再看 `python -I ra3voice/reslock.py status`（在主仓库目录跑）。
  - worktree 里构建要设 `CNV_SDK=C:\Users\63097\Documents\RA3Modding\sdk\RA3ModSDK3`；本分支的 `work` 是指向主仓库 `work/` 的目录链接。
  - 编译器报错的详细信息在 `SDK/_build_<mod>Map.log`，"找不到原版美术文件"那几行是正常的。
- **原版网格**：坐标是相对骨骼的，要按网格自带的骨骼编号对照表套骨架（`retail_mesh.py` 开头）；地图道具没有骨骼编号，整块在模型空间。编译后的 UV 是 V 朝下，写进我们的 W3X 要 `1 - v`。
