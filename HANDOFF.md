# 交接

## 当前目标

**单位验证做完**（用户 2026-10-22 定"先把单位验证做完"）：所有新单位（含心灵巫女和克隆体的心灵控制）都已上测试台验证，结果和每个单位"还差"什么在 [docs/story/units.md](docs/story/units.md) 开头的验证进度表。用户定的大顺序：战役设定 → 粗模玩法验证 → 关卡 → 美术最后。剧情大纲 [docs/story/outline.md](docs/story/outline.md)（v5）。

**单位设计已定**（用户 2026-10-22："都按你的推荐来，但是克隆体最好是选 C"）：定了什么、为什么在 units.md 第六节，都已按定下的做完并验证。

**剩下的讨论议程**（每条给 2～3 个选项和代价，别开放式提问）：
3. **之前说"不急"的两件**：A7 / A8 难度（A7 按现在的数值，玩家不动手，4 辆多功能车也会在自由号第一次跳过来约 35 秒后把它打下来；A8 两边都太容易；plan.md A7、A8 行）；超时空落点压到自家建筑会弄死被传的车（`Telefrag="INSTANT_DEATH_TELEPORTER_ONLY"`，改不改成 `NONE` / `SWAP`）。
4. **剧情**：大纲第六节"待用户决定"里还没定的（三个结局、三条背叛、关卡地点和关名）。
5. **下一阶段**：进关卡设计（[docs/story/levels.md](docs/story/levels.md) 已有 A7、A8 两张卡片），还是先清遗留。

**不用等用户、可以自己做的遗留**：
- 冰墙拖动转方向没验证成：拖动能放下，但借的地堡模型是圆的，看不出朝向；要么等墙有长条模型，要么做"拖成南北向、看车能不能东西向穿过"的挡路测试（units.md 进度表）。

**动手前**：要编图或用测试台，先**单独**检查红警3有没有在运行（用户可能在玩），在运行就停下问。

**写新单位**照钻地运兵车的样子：`units/<名>.py`（公开 abilities）+ `missions/<名>_bench.py`（按地点放、公开 cast / marks）+ `checks/<名>.py`（计数器 + 期望），在 `build.py` 的 MISSIONS 里登记；先 `cnv_show` 看接口，再 `cnv_check`。必要时用 A/B 对照（同图两个、一个用技能一个不用）和不放技能的对照检查。

**工具现状**：测试首选 MCP `cnv_check(name, check)`（编图 + 进关 + 读计数器 + 判定，一次调用）；`cnv_show(name, check)` 看各层公开的接口和接口检查（不编图）；`cnv_list` 列出所有构建。各层只走接口，关卡卡片由测试和代码对齐（plan.md「测试工具用法」0f、0g）。本会话改过的 `bench_mcp.py`（截帧掉线提示 BENCH DROPOUT、条件满足后照跑不带条件的观察）要 MCP 服务重启（新会话）才生效。

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
slice: unit-design-2026-10-22
blocked_on: user        # none | voice-session | user
next_gate: demo         # test-map | coordinate-calibration | demo
```
