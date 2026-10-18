# 交接

## 当前目标

收尾搬迁（两条线已搬到 `Documents\RA3Modding\`），然后做**测试专用地图**：开局直接进游戏、单位摆在固定屏幕位置，去掉每轮约 70 秒的加载和简报。

## 下一步

1. 配音会话搬完并验证后：在 RA3-ChineseVoice 里删 `experimental/`、清 `.gitignore` 相关行、把 HANDOFF 那一节换成指向本仓库的一行（配音会话已同意）。
2. 本仓库推到 GitHub（公开，77652189/RA3-CampaignLab）。
3. 测试专用地图 → 坐标标定 → 游隼协同演示。顺序和门控见 [docs/plan.md](docs/plan.md)「待启动 / 进行中」。

## 必读

1. [docs/plan.md](docs/plan.md)：状态、待办、已完成能力与经验（含各种格式和坑）。
2. [docs/architecture.md](docs/architecture.md)「不许怎么做」。
3. [docs/adr/README.md](docs/adr/README.md)：为什么不用旧 SDK、不用 AI 网格、不用状态过滤视野。
4. `experimental/campaign/labpaths.py`：所有路径从这里来。

## 验证方式

- 文档守卫：`python -I -m pytest -q tests`
- 编一张图并上测试台：`python -I -X utf8 experimental/campaign/make_campnew28.py`，再 `pwsh -NoProfile -File experimental/testbench/run_bench.ps1 -Mod "$env:USERPROFILE\Documents\Red Alert 3\Mods\CampNew28\CampNew28_1.0.skudef" -Seconds 80 -Shots 74 -Clicks '36:330,258;38:370,313;41:637,315;43:875,676;52:715,672;60:1040,676;64:877,675;70:877,675' -Keys '47:27;56:27'`，应得到 `RESULT alive 80 s` 和一张截图
- 锁：`python -I -m ra3voice.reslock status`

## 硬约束（用户原话）

- 下载："需要任何内容直接下载就行，不要停下来，你最多可以用50G硬盘"（只走可信来源，不绕过验证码）
- 删文件："只要不乱删文件就行"——删除前先问
- 显卡："可以，限流开始做吧"——显卡任务一律限流（`shared\gpu_limit.json`）
- 游戏：用户可能在玩红警3；游戏运行时不往 Mods 写、不开测试台，先单独检查进程
- 不改 Steam 游戏目录里的文件；不解密 Corona mod
- 回复用通俗中文

## 状态

```yaml
slice: post-migration
blocked_on: none        # none | voice-session | user
next_gate: test-map     # test-map | coordinate-calibration | demo
```
