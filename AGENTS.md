# 在本仓库干活（所有 agent 通用：Claude Code、Codex 等）

开工：读完本文件 → 读你那条线的交接（见"地图"）→ 交接开头"待答问题"里有新回答就先处理。
本文件只放红线和地图，限 60 行（tests/test_docs.py 守着）。只有做某块活才要知道的，写进那块的文件，这里只留指针。

## 红线
- 含目录联接的文件夹不许递归删除（`work/extsdk`、各工作区的 `work`、`.claude/worktrees/RA3-ChineseVoice`），删除会穿过联接清空目标（2026-11-10 因此清空过 work/ 和 SDK）。先 `python work/re/scripts/extsdk_setup.py --unlink`，或者问。
- 删除或清理任何东西前，先把它推到私有仓库。
- 逆向产物（地址、反编译说明）只放 `work/re/`（私有仓库）。本仓库是公开的，跟踪的文件里不许出现。
- 不改 Steam 游戏目录；游戏在运行时不装 mod、不往 Mods 写。上台排队用锁（ra3bench MCP、`experimental/testbench/run_queue.py` 自动拿）。
- mod 名和构建名不超过 15 个字符、不带下划线，否则游戏启动即崩（`test_every_build_name_fits` 守着）。
- 不改远端仓库可见性；不输入密码、密钥；不改系统和安全设置；用户的个人信息不进文件、不进外部请求。
- 不抄 Uprising / EA 的代码。

## 提交
- 身份 `git -c user.email=71443605+77652189@users.noreply.github.com -c user.name=77652189 commit ...`。做完、跑过相关测试就提交推送。
- 只 add 自己的文件。先提交再 `git pull --rebase`；不加 `--autostash`，不 stash、不碰别人没提交的改动。
- 引擎各线（A–E）改公开仓库的代码一律在自己的独立工作区里做，不在主仓库留没提交的改动（11-13 三条线的改动混在主仓库，测试红了分不清是谁的）——`git worktree add ../RA3-CampaignLab-<线名> origin/main`（没有自己的 work 时自动用主仓库的，不建联接），在那里 cherry-pick、rebase、`git push origin HEAD:main`。在独立工作区里上台用本工作区的 `experimental/testbench/run_queue.py`：ra3bench MCP 跑的是主仓库的代码，看不到你没推的改动。`work/re`（私有仓库）各线共用一份：交接改完马上提交推送，不留没提交的改动（11-13 一份没提交的交接挡住了所有线的 pull）。
- 生成的文件（`docs/engine/inventory*.md`）冲突不手改：取一边，重跑 `inventory.py`、`inventory_levels.py --write`、`inventory_ai.py levels --write`。

## 干活
- 目标（ADR 0026）：清单各部分按用量已对拍 ≥ 90%，再往 100% 推。"已对拍" = 有测试按名字跑那个台子、断言台上读数。
- 每项：先从数据预测 → 上台 → 读数不符照数据修模拟器（猜的标 INFERRED）→ 登记 + 测试。每轮只做一件能提交的事。
- 难题在交接里列一张假设表（假设、能区分它的那次运行、结果）。连续两轮解释不了就停。
- 卡住不等人：写进自己交接开头的 `## 待答问题`（问题、你倾向的答案、卡住了哪项），转去做下一项。回答的人写在问题下面。
- 测试：收尾只跑你改到的测试文件、导入了你改动模块的测试文件（`git grep -l <模块名> tests/`；超过 10 个时只挑和改动功能直接相关的，其余在提交说明里写"留给总控全量"）、`tests/test_inventory*.py`、`tests/test_docs.py`、`tests/test_architecture.py`。不跑全量（要 45 分钟以上，拖垮进度），全量由总控跑。
- 输出只看结论：长输出写 `work/logs/<名字>.log`，屏幕只看末几行；`pytest -q | tail -n 5`；能用数字（`cnv_check`、`bench_counters`）就不截图；读文件先搜索再按行读。数字解释不了时再看画面，别猜。
- 上下文快满：写交接（在做什么、下一步、没提交的改动、坑；只写指针）→ 提交推送 → 停掉后台任务 → 最后一行"可以清空：读 <交接> 接着做 <下一步>"。

## 地图
| 要做 | 先读 |
|---|---|
| 引擎线 A 脚本 / B AI / C 武器 / D 注入 / E 物体模块 | `work/re/handoff.md` / `handoff-b.md` / `handoff-c.md` / `handoff-d.md` / `handoff-e.md` |
| 台子怎么跑、坑 | `docs/engine/know-how.md` |
| 清单和进度 | `python -I -X utf8 experimental/cnv/inventory.py` |
| 其他各线（shell、units、story、music、render、simui） | `docs/<线>/handoff.md` |
| 为什么这么定 | `docs/adr/README.md` |
| 总控 | `work/re/handoff-coord.md` |
| 每日汇报 | `python -X utf8 experimental/campaign/daily_report.py` |
