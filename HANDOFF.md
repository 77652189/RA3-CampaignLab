# 交接

## 当前目标

**推进关卡**（用户 2026-10-23："A7 A8 难度可以先不考虑，我们先看看单位有没有做完，做完了就开始推进关卡"）：新单位都已验证（[docs/story/units.md](docs/story/units.md) 进度表）；后半段才用的招牌、老面孔、终局球塔做到那一关再做（plan.md「待启动」）。关卡卡片在 [docs/story/levels.md](docs/story/levels.md)，现有 A4、J4、A7、A8。J4 三个检查都过（2026-10-24，plan.md J4 行）；A4、A7 改成策划案驱动后的检查 2026-10-25 都过，启动器里的 A4、A7 要重新编过才是新版。A4 冰墙的改动（长条墙转不了向 → 方冰块；封门靠关卡脚本）用户 2026-10-23 回"可以，按你的推荐做 J4"时一并认了。用户定的大顺序：战役设定 → 粗模玩法验证 → 关卡 → 美术最后。剧情大纲 [docs/story/outline.md](docs/story/outline.md)（v5）。

**策划案驱动关卡**（用户 2026-10-24："先写好策划案，写好之后对照你说的这些条件看看是否成立，再和原版战役对比是否接近，最后再把策划案中提到的操作都做成标准化的方法接入MCP，尽可能做成只需要更改策划案就能直接改变玩法，这样我们可以让玩家自己去修改"）：
- 策划案就是关卡：[docs/story/plans/](docs/story/plans/)（现在 A4、A7），写法和词表在 `plans/README.md`；编译器 `experimental/cnv/plan.py`，机关 `experimental/cnv/devices/`，检查器 `experimental/cnv/plancheck.py`（MCP `plan_show` / `plan_vocab`）。原版节奏规则在 [map-language.md](docs/story/map-language.md) 第 7 节。
- A4 八个、A7 五个检查 2026-10-25 在测试台上都过（进度在 plan.md「关卡策划：策划案驱动关卡」一行）。
- 之前"按原版设计语言返工"的六个问题见 plan.md 对应一行；J4、A8 还是手写的任务，没有策划案。

地图工具在 MCP 里，用法见 plan.md「测试工具用法」0h。启动器（`launcher.pyw`）的分组从代码推出来，有策划案的关从策划案读一句话和检查。

**下一步**：
1. 交用户试玩 A4、A7（启动器"战役关卡"组，要先按新代码编过），按反馈改策划案。
2. 把 J4、A8 也改成策划案，接着做前半段别的关。

**等用户定的**：
- 搁置中：A7 / A8 难度、超时空落点压到自家建筑会弄死被传的车（plan.md A7、A8 行）。
- 剧情：大纲第六节"待用户决定"里还没定的（三个结局、三条背叛、关卡地点和关名）。

**动手前**：要编图或用测试台，先**单独**检查红警3有没有在运行（用户可能在玩），在运行就停下问；也看一眼有没有别的全屏游戏（`Get-Process | ? MainWindowTitle`），有就只做离线的活。

**写新单位**照钻地运兵车的样子：`units/<名>.py`（公开 abilities）+ `missions/<名>_bench.py`（按地点放、公开 cast / marks）+ `checks/<名>.py`（计数器 + 期望），在 `build.py` 的 MISSIONS 里登记；先 `cnv_show` 看接口，再 `cnv_check`。必要时用 A/B 对照（同图两个、一个用技能一个不用）和不放技能的对照检查。

**工具现状**：测试首选 MCP `cnv_check(name, check)`（编图 + 进关 + 读计数器 + 判定，一次调用）；`cnv_show(name, check)` 看各层公开的接口和接口检查（不编图）；`cnv_list` 列出所有构建。各层只走接口，关卡卡片由测试和代码对齐（plan.md「测试工具用法」0f、0g）。MCP 服务进程只在会话开始时加载一次代码：改了 `bench_mcp.py`、`harness.py`、`counters.py` 之后，本会话要验证就用 stdio 客户端另起一个服务进程（2026-10-24 用过，脚本没进仓库：照 `experimental/testbench/bench_client.py` 的写法），新会话会自动加载。

**已定、以后再做**：甲板乘员叠在航母正中一个点，用户 2026-10-21 定先接受叠放（候选做法：TransportContain 的 PassengerData BonePrefix，要给航母模型加甲板骨骼）。

用户 2026-10-20 的写作要求（也在记忆里）：剧情为玩法服务、黑色幽默和刻板印象只调味、剧情本身要正经；新单位逐关解锁；地图只求神似、按玩法设计（realmap 照搬真实地形效果不好）；不给真人演员角色写新台词新镜头；不用中国、朝鲜半岛地点，不拿真实悲剧开玩笑。

## 下一步

- 测试工具的用法（MCP、计数器、期望值写法、接口检查、lint、cnv.py、启动器、Tacitus）和**写新单位前要先查的坑**，2026-10-22 起都在 [docs/plan.md](docs/plan.md) 末尾「测试工具与踩过的坑」，原样从这里搬过去，编号 0～0g 不变。
- Bash 工具有 PreToolUse hook（`.claude/hooks/guard_inline_edits.py`）：拦下带反斜杠的 heredoc / `python -c` 写文件、带反斜杠的 `sed -i`、双引号 `python -c` 里的反引号。被拦就改用 Edit / Write，或把脚本写成 .py 文件再跑。只有在本仓库目录里打开的会话才会加载它。
- 待办与门控见 [docs/plan.md](docs/plan.md)「待启动 / 进行中」。

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
slice: plan-driven-levels-2026-10-24
blocked_on: none        # none | voice-session | user
next_gate: demo         # test-map | coordinate-calibration | demo
```
