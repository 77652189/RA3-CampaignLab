# 交接

## 当前目标

粗模验证新单位（2026-10-21 暂停处）。用户定的顺序：战役设定 → 粗模玩法验证 → 关卡 → 美术最后。剧情大纲 [docs/story/outline.md](docs/story/outline.md)（v5），新单位方案 [docs/story/units.md](docs/story/units.md)（用户 2026-10-20 回复"可以"，按整体定稿处理，含"黑匣子"反转；用户没明确否决就照此做）。

**今天（2026-10-20 晚 – 10-21）做完的**（详情见 docs/plan.md「待启动 / 进行中」对应各行）：
- 三块对战拼图的机制都上测试台验证过，都是借原版模型的粗模：时滞炮车（`make_campnew35.py`，含展开、攻坚对照）、阻塞气球车（`make_campnew36.py`，含展开）、烟花兵（`make_campnew37.py`，花火云 + 架设）。
- 招牌单位自由号空天航母（`make_campnew38.py`）：第 1 片（基洛夫底 + 放无人机）、第 2a 片（超时空甲板，航母自己跳）。

**恢复时先做**：
1. 自由号 v2 空中平台（`make_campnew38.py`，用户 2026-10-21 的设计，units.md 5.2.1）探路结果（详见 plan.md 自由号那行）：甲板跃迁**做通**（起跳时圈选、落地时传送，航母带着脚下部队一起到）；甲板工厂**做通**（自动生产：SpawnBehavior 每 20 秒出一辆守护者，能正常指挥；走生产队列那条路侧栏不认）；可拆炮塔**没做通**（能刷出、会跟着航母，但不开火）。自制模板要在地图上也摆一个才会被 SpawnBehavior 加载。还差：炮塔不开火、无人机不回收、刷出的单位叠在一个点。
2. 然后搭 A7（自由号当首领，像浮岛要塞那关先拆炮塔和工厂）/ A8（自由号归玩家）两关粗模，按 units.md 5.6 的难度规矩做"有招牌 / 没招牌"对照。
3. 自由号的无人机打完不回收、在航母旁越积越多，要修。
4. 大纲第六节"待用户决定"里还没定的：三个结局、三条背叛、关卡地点和关名。

**这两天测试台上反复踩的坑**（写新单位时先查）：
- **视野**：单位只打自己视野里的目标，友军视野不算，关掉 CheckVisionRange 也没用。射程比视野远时，炮塔会转过去但永远不开火，也不靠近。时滞炮车（守护者视野 200）和自由号（基洛夫视野 150）都栽在这里。
- **步兵的"不能动"**：用 IMMOBILE_ALLOW_ROTATE，不用 IMMOBILE（步兵要转身瞄准，IMMOBILE 下一发都不打）。
- **追击**：AIUpdate 的 StandGround / StopChaseDistance 都拦不住单位追飞机，要守点就做"展开 / 架设"切换（守护者目标指示的整套切换搬过来就能用，ToggleState 里必须带 SkirmishAiInfo）。
- **复制原版单位**：同一个文件里继承它的变体（坦克杀手的伏击版、牛蛙的 _Ground 版）要一起删掉，否则编图失败。
- **飞机**：框选要点它悬停的屏幕位置（比地面点高约 170 像素）；要它回航得有机场，否则一直在目标上空盘旋。
- **测试台截图**：`--shots 10` 是"第 10 秒拍一张"，要多张写成 `--shots 1,3,5,...`。

用户 2026-10-20 的写作要求（也在记忆里）：剧情为玩法服务、黑色幽默和刻板印象只调味、剧情本身要正经；新单位逐关解锁；地图只求神似、按玩法设计（realmap 照搬真实地形效果不好）；不给真人演员角色写新台词新镜头；不用中国、朝鲜半岛地点，不拿真实悲剧开玩笑。

## 下一步

1. 日常操作先用根目录的 `cnv.py`（`python -I -X utf8 cnv.py -h`）：build / map / bench / sheet / where / launcher / status，不再临时写脚本。新测试一律用 `run_bench.ps1 -Nav`（`cnv.py bench` 就是它）：时间从进入关卡算起，点击位置用 `experimental/testbench/calib.py` 的 `world_to_screen` 从世界坐标算（标定只对从 CampNew18 岛派生、开局镜头相同的地图有效；换了开局镜头要重新标定：`CNV_CALIB=base/grid` 各编一次、各跑一次，再 `calib.py fit`）。要看镜头外的地方：左键点 `calib.world_to_minimap(x, y)` 移镜头，再用 `calib.world_to_screen_at(x, y, 镜头中心)` 算点击位置；要打人就右键点敌人本身，右键点小地图只是移动。
1a. 测试台的游戏副本 `work/testbench/RA3` 里也有 Tacitus（C&C:Online 的游戏补丁，`Data\dsound.dll`）。它的版本落后于新版时，每次启动都弹更新窗口，挡住菜单；而且它是 ImGui 窗口，测试台发的点击点不到。办法：把 Steam 游戏目录里更新过的 `Data\dsound.dll` 复制到测试台副本（2026-10-20 已换成 1.1.0，旧的留作 `dsound.dll.tacitus100.bak`）。`nav.py` 的 POPUPS 只能识别出这个窗口，点不掉它。卡在菜单时，看 `shots/nav_last.png` 就知道卡在哪个画面。
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
