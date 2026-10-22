# 交接

## 当前目标

粗模验证新单位（2026-10-21 暂停处）。用户定的顺序：战役设定 → 粗模玩法验证 → 关卡 → 美术最后。剧情大纲 [docs/story/outline.md](docs/story/outline.md)（v5），新单位方案 [docs/story/units.md](docs/story/units.md)（用户 2026-10-20 回复"可以"，按整体定稿处理，含"黑匣子"反转；用户没明确否决就照此做）。

**今天（2026-10-20 晚 – 10-21）做完的**（详情见 docs/plan.md「待启动 / 进行中」对应各行）：
- 三块对战拼图的机制都上测试台验证过，都是借原版模型的粗模：时滞炮车（`make_campnew35.py`，含展开、攻坚对照）、阻塞气球车（`make_campnew36.py`，含展开）、烟花兵（`make_campnew37.py`，花火云 + 架设）。
- 招牌单位自由号空天航母（`make_campnew38.py`）：第 1 片（基洛夫底 + 放无人机）、第 2a 片（超时空甲板，航母自己跳）、v2 空中平台的甲板跃迁和甲板工厂。
- 两关粗模：A7「鹰派」（`make_campa7.py`，敌方自由号靠脚本跃迁，炸电站停跳）、A8「海上发布会」（`make_campa8.py`，自由号归玩家，丢了就输）。
- 给用户试玩的图形启动器 `launcher.pyw` + 桌面快捷方式（下面 1b）。

**恢复时先做**（2026-10-21 深夜更新）：先看下面"下一步"第 0、0a、0b、0c 条（ra3bench MCP、编图前 lint、少操作少截图的测法、解耦后的组装命令）。用户 2026-10-21 定：甲板乘员先接受叠放，先做解耦和效率改进——都已做完（0c）：自由号和 A8 已迁到 `experimental/cnv/`，4 个检查在测试台上全部 PASS。新内容一律按 0c 的结构写；没加载 MCP 的会话用 `cnv.py make <名> --check <检查>` 或 `experimental/testbench/bench_client.py`。
**等用户回答**（2026-10-21 深夜问过）：① 要不要用新版 `cnv.py make a8` 覆盖现在装着的 CampA8（新版是原版战车工厂，造不了 CNV 轻坦）；② 排查崩溃留下的测试 mod（Mods 里的 CampBis*、CampLibertyRidersJump、CampLibRidersJump）能不能删。
**下一步候选**（推荐 1）：
1. 地图生成器写触发区域，这样计数器能数"区域里有几辆"，A8 jump 才算真正验证到守护者跟着跳到了平台边。
2. A8 有/没有自由号的难度对照，两边各写一个检查自动跑数。
3. A7 迁到 `experimental/cnv/`。
4. 小问题：liberty jump 里第 14 秒少了一辆守护者，原因没查。

其余旧项：
1. 自由号 v2 空中平台（`make_campnew38.py`，用户 2026-10-21 的设计，units.md 5.2.1）探路结果（详见 plan.md 自由号那行）：甲板跃迁**做通**（起跳时圈选、落地时传送，航母带着脚下部队一起到）；甲板工厂**做通**（自动生产：SpawnBehavior 每 20 秒出一辆守护者，能正常指挥；走生产队列那条路侧栏不认）；可拆炮塔**没做通**（能刷出、会跟着航母，但不开火）。自制模板要在地图上也摆一个才会被 SpawnBehavior 加载。还差：炮塔不开火、刷出的单位叠在一个点。
2. A7、A8 粗模都能玩（`make_campa7.py`、`make_campa8.py`，见 plan.md 两行）；还差 5.6 的"有招牌 / 没招牌"难度对照（A8 有 `CNV_NO_CARRIER=1` 对照版，要自动操作部队才有可比的数），按 units.md 5.6 的难度规矩做"有招牌 / 没招牌"对照。
3. 用户 2026-10-21 晚试玩：A7、A8 流程通；无人机回收、跃迁画面已补（plan.md 自由号行）；最大差距是"没有独立平台容纳地面单位"（像浮岛要塞那样）。甲板乘员探路（`CNV_RIDERS=1`）：守护者能自己上甲板、跟着跃迁，但叠在一点、落地开打后全灭原因没查清；下一步等用户选方向。MCP 测试时看到：落地后守护者站在地上而不在甲板上——甲板跃迁的"圈选 + 传送"把骑着的守护者也单独传了一次、把它们从航母上拆了下来。**已修**（2026-10-21 夜）：开 `CNV_RIDERS=1` 时甲板筛选和两个超时空模板都 `ExcludeThing` 乘员，乘员靠 INSTANT_TELEPORT_ON_PARENT_TELEPORT 跟着航母走；`CNV_TEST=jump` 三轮零点击测试，计数器跃迁前后都是"存活 6、在甲板 5"（runs/CampNew38_mcp_1021_212900）。"落地后全灭"是以前手点的落点 (1180, 2600) 就在敌方铁锤旁边，打起来了。**叠在一点没解决**：AttachUpdate 没有偏移参数；去掉 STICK_TO_PARENT（`CNV_RIDE_FLAGS`）时乘员在地上各站各的、也算挂着，但跃迁一落地还是全叠到航母正中（_213229）。候选：`TransportContain` 的 `PassengerData BonePrefix`（原版 15 处，双刃直升机 `SlingUnderBone` 吊一辆车），要给航母模型加几根甲板骨骼。用户 2026-10-21 定：**先接受叠放**，这条以后再做。
4. 大纲第六节"待用户决定"里还没定的：三个结局、三条背叛、关卡地点和关名。

**这两天测试台上反复踩的坑**（写新单位时先查）：
- **视野**：单位只打自己视野里的目标，友军视野不算，关掉 CheckVisionRange 也没用。射程比视野远时，炮塔会转过去但永远不开火，也不靠近。时滞炮车（守护者视野 200）和自由号（基洛夫视野 150）都栽在这里。
- **步兵的"不能动"**：用 IMMOBILE_ALLOW_ROTATE，不用 IMMOBILE（步兵要转身瞄准，IMMOBILE 下一发都不打）。
- **追击**：AIUpdate 的 StandGround / StopChaseDistance 都拦不住单位追飞机，要守点就做"展开 / 架设"切换（守护者目标指示的整套切换搬过来就能用，ToggleState 里必须带 SkirmishAiInfo）。
- **复制原版单位**：同一个文件里继承它的变体（坦克杀手的伏击版、牛蛙的 _Ground 版）要一起删掉，否则编图失败。
- **飞机**：框选要点它悬停的屏幕位置（比地面点高约 170 像素）；要它回航得有机场，否则一直在目标上空盘旋。
- **测试台截图**：`--shots 10` 是"第 10 秒拍一张"，要多张写成 `--shots 1,3,5,...`。
- **复制哪个当底**：SDK 示例 mod 的先兆炮艇机复制后从不开火，招牌飞行单位用基洛夫当底；基洛夫文件里 CheckVisionRange 出现两次，改视野时两处都要看。
- **超时空**：自己写的 SpecialPowerTemplate 必须带 ObjectFilter，否则什么都传不走；超时空传送不带飞机，航母自己要用 TeleportSpecialAbilityUpdate 自跳；落点压到建筑会互相撞毁。
- **SpawnBehavior**：只能刷原版单位，或者地图上也摆了一个的自制单位（否则模板不加载、刷不出来）；刷出的单位叠在一个点。单位身上的生产队列侧栏不认，要"甲板工厂"就用自动刷。
- **任务脚本计时器**：SET_MILLISECOND_TIMER 到点后一直算"已到期"，交替触发的脚本每次都要把自己的计时器重新推远，否则每帧都触发。AI 不会自己按跃迁之类的技能，用 NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT 由脚本按。
- **落点 / 突击点**：别放在对方建筑上（A7 第一次把突击点放在我方战车工厂上，跳来的自由号压在工厂上、防空车够不着）。
- **mod 名最多 15 个字符**：同一份内容，叫 CampLibRidersJump / CampBisjcdXXXXXXX（17 个字符）时游戏在主菜单前就崩（退出码 0xC000000D，日志里什么都没有）；叫 CampBisjcd、CampBisjcdXXXX（14）、CampLibertyJump（15）都正常。`experimental/cnv/parts.assemble` 超长直接报错，`tests/test_cnv_parts.py` 检查所有登记的编图名。
- **检查游戏在不在跑**：进程名要同时匹配 `ra3_1.xx.game`、`RA3.exe` 和起义时刻的 `ra3ep1`（之前漏了起义时刻）。
- **截图隐私**：给启动器之类的窗口截图只用 PrintWindow 截那个窗口，别用 CopyFromScreen 截整屏（会截到用户的其他窗口）。
- **弹窗自动点击**：测试台的弹窗钩子只点一次、不能 `continue` 循环（曾经在 Tacitus 窗口上空转约 15 分钟），卡住就让 150 秒超时生效。

用户 2026-10-20 的写作要求（也在记忆里）：剧情为玩法服务、黑色幽默和刻板印象只调味、剧情本身要正经；新单位逐关解锁；地图只求神似、按玩法设计（realmap 照搬真实地形效果不好）；不给真人演员角色写新台词新镜头；不用中国、朝鲜半岛地点，不拿真实悲剧开玩笑。

## 下一步

0. **测试台改用 MCP（2026-10-21 晚起）**：仓库根 `.mcp.json` 注册了 `ra3bench`（`experimental/testbench/bench_mcp.py`，核心在 `harness.py`，Python 用 `../envs/bench_mcp`：mcp 2.x + Pillow + NumPy + pycaw）。新会话第一次要批准这个项目 MCP。用法：`bench_start(mod)` 自己走菜单进关（约 40 秒），之后用世界坐标 `bench_click / bench_box / bench_ability / bench_camera`，`bench_wait` 推进，`bench_look` 看，`bench_inspect` 放大任意存档帧，`bench_caption` 读任务脚本在字幕里报的信号，`bench_stop` 收尾放锁。默认 hold 模式：任务菜单（Esc）暂停游戏，只有工具在动作或等待时游戏才走（实测思考 5 秒游戏时间不变）。帧全尺寸存在 `work/testbench/runs/<mod>_mcp_<时间>/`（index.json 记每帧的任务秒数和镜头）。暂停菜单模板 `work/testbench/nav/pause_menu.png`（work 不进 git，丢了要从一帧任务菜单画面重切：`harness.MENU_BOX`）。旧的 `cnv.py bench`（run_bench.ps1 开环时间线）还在，批量回归可以继续用。思路来源：VISTA（arXiv 2610.02200）的机械控制器 + 无损帧存档 + 按需细看。
0b. **少操作、少截图的测法**（2026-10-21 夜）：
   - **让任务脚本自己动手**：`make_campnew38.py` 的 `CNV_TEST=jump` 由脚本在第 `CNV_JUMP_AT`（默认 15）秒用 `NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT` 让航母跳到 `CNV_JUMP_TO`，测试时一次点击都不用。
   - **让任务脚本报数**：用 `DISPLAY_COUNTER` 把要检查的数显示在左下角（`harness.COUNTER_BOX`），每帧更新。例子：`SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER` 数存活单位；`PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS` 按状态数单位，比较符 2 是"等于"，状态参数写成 `(序号, 0.0, 名字)`，序号按 ObjectStatus.xsd 的顺序从 0 数（ATTACHED = 102）。
   - **MCP 新工具**：
     - `bench_watch(seconds, every, box)`：一次调用跑一段时间、定时存帧。返回每帧的变化量（水面和待机动画本身约 8）、字幕有没有变（超过 20），最多再加一张拼图。
     - `bench_strip()`：把多帧里的同一块区域（默认计数器）拼成一条，只读存档、不碰游戏。
     - `bench_start(look=false)`：开局不截图。
   - **飞行单位画在地面点上方约 170 像素**：框飞行单位时，`bench_watch` 要传 `air=true`。
   - 一次完整测试的流程：start → watch（sheet=false）→ `bench_counters`，只返回文字，一张图都不用看。
   - **计数器认数字**：`experimental/testbench/counters.py`。计数器从左下角 y=578 往下排、每行 16 像素，只放得下 4 行（第 5 行被底栏挡住）。数字模板在 `work/testbench/nav/digits/`（work 不进 git，丢了就重跑 `cnv.py make digits --calibrate`：地图显示 1234 / 5678 / 90，切出 0～9）。MCP 工具 `bench_counters(lines)` 把每帧的计数器读成"s19: 6 5"。
   - 任务提前结束（输了 / 赢了）时，`bench_watch` 停不住游戏也会带着已存的帧返回，计数器随任务一起消失；判"任务结束"用 0c 的 ENDED。
0c. **解耦后的组装命令**（2026-10-21 深夜，用户定"先接受叠放，先做解耦，效率改进也做"）：
   - 结构 `experimental/cnv/`，旧的 42 个 `make_camp*.py` 不动：
     - `units/`：单位 = 参数 → `Unit`（XML 文本 + 编图要知道的东西），`tag=` 给所有自有 id 加后缀，两个变体能摆在同一张图上。
     - `maps/`：地形和开局点（`island.py` 就是 CampNew18 的岛）。
     - `missions/`：摆放 + 任务脚本 + 字符串 + 目标（`a8.py`、`liberty_bench.py`）。
     - `checks/`：检查 = 附加的脚本（让任务自己按技能）+ 计数器 + 测试台步骤 + 期望值。
     - `parts.py`：声明的数据结构和 `assemble()`，走原来的 CampNew7 流水线（lint 照跑）。
     - `build.py`：一条命令编图、跑测试台、按计数器判 PASS / FAIL，失败时退出码 1。
   - 命令：
     - `cnv.py make list`：列出能编的图和检查。
     - `cnv.py make a8`：编 A8 本身。**还没执行**：现在装着的 CampA8 仍是旧 `make_campa8.py` 的产物；新版把 CNV 装甲工厂换成了原版战车工厂（造不了 CNV 轻坦），用户确认后再覆盖。
     - `cnv.py make a8 --check jump|lose`、`cnv.py make liberty_riders --check jump`、`cnv.py make liberty_ride_ab`（同图 A/B）。
     - `--no-build`：只跑测试台，用已经编好的图。
   - 2026-10-21 测试台结果，全部零点击：
     - A8 jump PASS：自由号 1，守护者 6。
     - A8 lose PASS：自由号第 5 秒被击落，任务结束。
     - liberty_riders jump PASS：跃迁前后都是存活 6、在甲板 5，和旧图一致。
     - liberty jump PASS：不带乘员。第 14 秒乘员从 6 变成 5，少了一辆守护者，原因没查（可能是跃迁落点撞毁）。
     - liberty_ride_ab：A（粘在航母上）6 / 6，B（不粘）6 / 5，跃迁前后都不变。这个只是对照，不判对错。
   - 期望值写法：
     - `(标签, 从第几秒起, 比较符, 值)`：从那一秒起每帧都要满足。
     - 比较符写成 `ever==` 之类：至少有一帧满足就算。
     - 标签写 `ENDED`：计数器先出现、后来全没了，就算任务已经结束。
   - 已知缺口：
     - 计数只能按"玩家拥有的某种单位"或"带某状态的单位"数，数不了"某个区域里的单位"。触发区域我们的地图生成器还不会写。所以 A8 jump 证明不了守护者真的跟着跳到了平台边。
     - 测试台建的 CampBis*、CampLibertyRidersJump、CampLibRidersJump 是排查崩溃留下的 mod，在 Mods 里，等用户同意再删。
0a. **编图前自动静态检查**：`experimental/campaign/lint.py`，每次编图在编译前跑（`make_campnew7.compile_map`），有 ERROR 就停（`CNV_LINT=warn` 只打印）。规则对应下面"踩过的坑"：视野和射程（超过 1.5 倍只警告）、步兵 IMMOBILE、超时空模板缺 ObjectFilter、ToggleState 缺 SkirmishAiInfo、复制件里留着原版 id、SpawnBehavior 刷的自制模板没摆在地图上。`python -I -X utf8 experimental/campaign/lint.py` 单独查全部单位文件；`tests/test_lint.py` 每条规则一个正反例。新坑出现时先加一条规则和测试。
1. 日常操作先用根目录的 `cnv.py`（`python -I -X utf8 cnv.py -h`）：build / map / bench / sheet / where / launcher / status，不再临时写脚本。新测试一律用 `run_bench.ps1 -Nav`（`cnv.py bench` 就是它）：时间从进入关卡算起，点击位置用 `experimental/testbench/calib.py` 的 `world_to_screen` 从世界坐标算（标定只对从 CampNew18 岛派生、开局镜头相同的地图有效；换了开局镜头要重新标定：`CNV_CALIB=base/grid` 各编一次、各跑一次，再 `calib.py fit`）。要看镜头外的地方：左键点 `calib.world_to_minimap(x, y)` 移镜头，再用 `calib.world_to_screen_at(x, y, 镜头中心)` 算点击位置；要打人就右键点敌人本身，右键点小地图只是移动。
1b. 给用户自己试玩用的图形启动器：根目录 `launcher.pyw`（桌面快捷方式"红警3 测试启动器"，2026-10-21）。它列出 Mods 里所有编好的 mod，按"关卡 / 单位测试图 / 其他"分组，双击就启动，游戏在运行时拒绝启动。新关卡或新单位测试图要在 `launcher.pyw` 的 KNOWN 里加一行中文说明，否则会落进"其他"组。
1a. **2026-10-21 晚起测试台副本不加载 Tacitus**：Tacitus 出了 1.1.1，又在每次启动时弹更新窗口，Steam 目录里的也还是 1.1.0、没有新版可抄，就把副本的 `Data\dsound.dll` 改名成 `dsound.dll.tacitus110.off`（测试台不联网，用不着它；改回原名即恢复）。没有 Tacitus 时游戏会弹"连接中断通知"并退回主菜单：`nav.py` 的 POPUPS 认得它、点确定，`run_bench.ps1` 随后从第 0 步重新走菜单（约第 29 秒进关）。以下是旧情况：测试台的游戏副本 `work/testbench/RA3` 里也有 Tacitus（C&C:Online 的游戏补丁，`Data\dsound.dll`）。它的版本落后于新版时，每次启动都弹更新窗口，挡住菜单；而且它是 ImGui 窗口，测试台发的点击点不到。办法：把 Steam 游戏目录里更新过的 `Data\dsound.dll` 复制到测试台副本（2026-10-20 已换成 1.1.0，旧的留作 `dsound.dll.tacitus100.bak`）。`nav.py` 的 POPUPS 只能识别出这个窗口，点不掉它。卡在菜单时，看 `shots/nav_last.png` 就知道卡在哪个画面。
2. Bash 工具有 PreToolUse hook（`.claude/hooks/guard_inline_edits.py`）：拦下带反斜杠的 heredoc / `python -c` 写文件、带反斜杠的 `sed -i`、双引号 `python -c` 里的反引号。被拦就改用 Edit / Write，或把脚本写成 .py 文件再跑。只有在本仓库目录里打开的会话才会加载它。
3. 待办与门控见 [docs/plan.md](docs/plan.md)「待启动 / 进行中」。

## 必读

1. [docs/plan.md](docs/plan.md)：状态、待办、已完成能力与经验（含各种格式和坑）。
2. [docs/architecture.md](docs/architecture.md)「不许怎么做」。
3. [docs/adr/README.md](docs/adr/README.md)：为什么不用旧 SDK、不用 AI 网格、不用状态过滤视野。
4. `experimental/campaign/labpaths.py`：所有路径从这里来。

## 验证方式

- 文档守卫：`python -I -m pytest -q tests`
- 编一张图并上测试台：`python -I -X utf8 experimental/campaign/make_campnew28.py`，再 `pwsh -NoProfile -File experimental/testbench/run_bench.ps1 -Nav -Mod "$env:USERPROFILE\Documents\Red Alert 3\Mods\CampNew28\CampNew28_1.0.skudef" -Seconds 5 -Shots 3`，应得到 `NAV in game at ~23 s`、`RESULT alive 5 s` 和一张截图（导航模板第一次要从参考截图生成：`python -I experimental/testbench/nav.py build <截图目录>`）
- 锁：`python -I ra3voice/reslock.py status`

## 硬约束（用户原话）

- 下载："需要任何内容直接下载就行，不要停下来，你最多可以用50G硬盘"（只走可信来源，不绕过验证码）
- 删文件："只要不乱删文件就行"——删除前先问
- 显卡："可以，限流开始做吧"——显卡任务一律限流（`shared\gpu_limit.json`）
- 游戏：用户可能在玩红警3；游戏运行时不往 Mods 写、不开测试台，先单独检查进程
- 不改 Steam 游戏目录里的文件；不解密 Corona mod
- 回复用通俗中文

## 状态

```yaml
slice: unit-probes-2026-10-21
blocked_on: none        # none | voice-session | user
next_gate: demo         # test-map | coordinate-calibration | demo
```
