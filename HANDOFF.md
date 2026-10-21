# 交接

## 当前目标

写战役剧情（2026-10-20 暂停处）。用户定的顺序：战役设定 → 粗模玩法验证 → 关卡 → 美术最后。剧情大纲在 [docs/story/outline.md](docs/story/outline.md)（v5：盟军胜利时间线；黑尔造第二台时间机器，要回 1927 年布鲁塞尔和爱因斯坦签合同；三样零件 = 赛林斯基本人 + 超时空网络 + 协调器；心灵只用来控制人；三方各 9 关、镜像关、同一张布鲁塞尔终局、各自结局）。检验方法：[docs/story/comparison.md](docs/story/comparison.md)（原作逐关一句话对照）。

**恢复时先做**：
1. 新单位已按用户两条标准重筛（像该阵营会造的 + 补社区对战缺口、对手能反制，靠机制不靠数值），草案在 [docs/story/units.md](docs/story/units.md)：每方一块"拼图"（盟军时滞炮车、苏联阻塞气球车、帝国烟花兵），收缩射线车和鸣神降为战役专属，苏联 S7 用原版删除的磁暴坦克，浪人卫队改式神。依据是本地的 `work/story/pvp_meta.md`（社区短板与补丁方向）和 `work/story/unit_roster.md`（SDK 单位表、删除单位、15 种机制可行性）。等用户审第五节。
2. 用户定了单位后：粗模验证三块拼图（时滞炮车最便宜：UNATTACKABLE + NO_ATTACK 状态），钻地 / 超时空信标 / 合体先上测试台探路。
3. 大纲第六节"待用户决定"还有：前提和三样零件、三个结局、三条背叛、关卡地点和关名。

用户 2026-10-20 的写作要求（也在记忆里）：剧情为玩法服务、黑色幽默和刻板印象只调味、剧情本身要正经；新单位逐关解锁；地图只求神似、按玩法设计（realmap 照搬真实地形效果不好）；不给真人演员角色写新台词新镜头；不用中国、朝鲜半岛地点，不拿真实悲剧开玩笑。

## 下一步

1. 日常操作先用根目录的 `cnv.py`（`python -I -X utf8 cnv.py -h`）：build / map / bench / sheet / where / launcher / status，不再临时写脚本。新测试一律用 `run_bench.ps1 -Nav`（`cnv.py bench` 就是它）：时间从进入关卡算起，点击位置用 `experimental/testbench/calib.py` 的 `world_to_screen` 从世界坐标算（标定只对从 CampNew18 岛派生、开局镜头相同的地图有效；换了开局镜头要重新标定：`CNV_CALIB=base/grid` 各编一次、各跑一次，再 `calib.py fit`）。要看镜头外的地方：左键点 `calib.world_to_minimap(x, y)` 移镜头，再用 `calib.world_to_screen_at(x, y, 镜头中心)` 算点击位置；要打人就右键点敌人本身，右键点小地图只是移动。
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
slice: bench-speedup-done
blocked_on: none        # none | voice-session | user
next_gate: demo         # test-map | coordinate-calibration | demo
```
