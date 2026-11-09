# 外壳线交接

外壳线 2026-11-03 从关卡线拆出（[architecture.md](../architecture.md) 各线负责的文件）。更早的外壳、CampShell 记录见 [story/handoff.md](../story/handoff.md) 搜"外壳""CampShell"。问题编号见 [issues.md](../issues.md) I10～I22、K9。已结束切片的过程细节都在 git log（搜下面各条括号里的关键词），这里只留当前状态和坑。

状态（2026-11-08）：引擎优先，关卡与外壳不推新内容，亲手试玩改在游戏里（ADR 0024～0026）。外壳线没有进行中的任务；下面是已交付物、没做完的项、必读指针。

## 当前状态：笔记本演示包（11-06 总控派活，git log 搜 "retail English"）

- **交付物**在 `work/demo/`：`CampShellEn_demo.zip`（INSTALL.txt + CampShellEn 文件夹：skudef、big、`Play_CampShellEn.bat`）、`a4.mp4`（118 s，开场过场 + 字幕 + "NEW PRIMARY/BONUS OBJECTIVE"）。源文件在 `work/demo/src/`；打包、驱动、合成视频的脚本在当时会话的 scratchpad，没进仓库（要重做就照下面路子再写）。
- **修了**：国际版外壳的字符串表原来以配音线装进游戏的 `CNVoice_text.big`（中文）为底本，纯英文 Steam 上原版条目全成横线。现在由 `langs.EDITIONS[...]['strings_base']` → `ModSpec.strings_base` → `make_campnew3.STRINGS_BASE` 决定，国际版用 `Lang-English11.big`。
- **模拟笔记本**：`work/testbench/RA3van` 是测试台副本，改成原版样子（没打 4GB 补丁的 .game、Steam 原样 skudef、无 SAGE-Unlocked/CNVoice/代理 DLL，只留截帧垫片），`-config RA3_chinese_t_1.13.SkuDef` 里写英文链。用 `RA3_BENCH_DIR` 指过去；菜单是英文、测试台中文模板认不出，所以按 `nav.json` 坐标定时盲点（先点断线框的 OK 634,426）。
- **录像**：截帧垫片 `CNV_SHOT_MS=50` 存 `auto_<ms>.bmp`（实际约 15 帧/秒）；按进程号录音（`listen.CAPTURE_EXE`，-80 dB）；按帧文件写入时间对齐；ffmpeg 用配音线 `third_party/ffmpeg`，音频要 loudnorm。`work/demo/rec_v2/` 是 13 GB 原始帧，可以删。
- **还剩**：没在真笔记本上装过；没人操作时 A4 约 150 s 判负（车队被打掉），演示要尽快接手；打通只用 `cnv_check a4_intl win shell unit` 验过（脚本拆北营）。

## 已交付、等验收或没做完的

- **I16～I18（9 关装进外壳）**：已重建 CampShell / CampShellEn 并进游戏自查过，两版 `bench_start(chapter=1..9)` 各 9 关能进（每关约 57 s，A4 约 130 s）；结果写在 issues.md I16～I18 备注，证据在 `work/acceptance/2026-11-05/`。等总控独立验收。没看到的：A7 自由号（开局在不能进的东岸，要看就在 A7 打到它出场）；A7、A8 的 `CNV_Liberty.xml` 内容不同，进游戏要专门看两关的自由女神。
- **I22、I21（11-05，git log 搜 "I22"、"I21"）**：等总控验收。I22：`bench_start(menu_frames=2)` 走菜单和开场过场时存半尺寸帧（`harness.Session.keep_walk`；`bench_inspect` 按 scale 换算）。I21：结局卡片 `tacticalendgamedialog` 加进 `SCREENS`，盟军胜利/战败海报换沃斯（`END_CARDS`）；没看胜利卡片；"Nan" 是存档名不改（理由在 issues.md I21）。**MCP 服务要重启才认新参数。**
- **还可以做（没派）**：原版检查只从 `SCREENS` 出发，引擎直接弹出的界面漏掉；可枚举 `Apt.big` 全部 `aptui` 界面，把战役流程里会弹出的（`tacticalnewintelligencepopup`、`tacticalplayerstatusdialog` 等）逐个归到替换或 KEEP。
- **I11 剩下的**：(a) 指挥官摘要页左边头像位空着（引擎画的 `CocommanderPortrait`，模板去掉了 Portrait；要给 mod 加 OnDemandImage 头像资源，原版头像名在编译好的数据里不在 SDK XML；检查不会报它）；(b) 星星可能还在 `fe_m_generalScreenComponents_1` 里，进游戏看，还有星就是后者；(c) 两个目标离得近时路线箭头缩小（A4 缩到 0.4 倍），进游戏看是否太细，太细就给 `retime` 的 route 加最小缩放。
- **I10、I11、I12、I15 状态**：issues.md 里改"修了待验"（只有这一处外壳线可改）；I15 国际版还差 9 关逐个进游戏看不崩，国际版要带配音线的新音频。K9 的检查查不到：脚本运行时拼出来的字串（靠前缀改写兜住）、引擎往文本框填的内容、引擎画的图。贴图按整张算，同一张里别的原版小图不会再报（要在 KEEP 理由里说清）。
- **编辑器没做**：BLOCKS/GAPS 画不了、景物没有、`block`/`unblock` 不进草图、画刷没有本地实时高度预览、容器图固定 5000×5000；真鼠标/真触屏手感没验；北营 niagara 东边 (4970, 2840) 窄缝（宽约 30、长 100）转给了关卡线，没改图。

## 必读材料（只给指针）

- **外壳构建**：`experimental/cnv/build.py campaign --shell [--lang intl]` 出 CampShell / CampShellEn；`shell.campaign(levels, name, lang, fallback)`、`ModSpec.levels`、`package.build_mod`、`package.level_stem(k)`；国际版没有 `_intl` 的关用中文版顶上并打 MISSING 行（A4 以外现在都是）。targets 从 `ModSpec.goals`（`package.goal_points`）取，没有 BORDERS 的图按 5000×5000。测试 `tests/test_shell.py`、`tests/test_architecture.py`（G7、G8）。
- **检查叠在外壳上（ADR 0016 第 2 阶段）**：`build.py <关> --shell --check <检查> [--unit]`，`package.check_layer`；mod 名验收版 CampShellT/CampShellEnT，机关单测 CampShellU/CampShellEnU，正式版 CampShell 不动；`harness.shell_steps(slot)` 按章节进关；`cnv_check` 有 `shell`、`unit` 参数。
- **原版内容检查**：`shell.still_retail(sp)`，`KEEP` 保留清单（用不到的 KEEP 也报错）；测试 `tests/test_shell.py` 里 `test_no_retail_picture_label_or_video_...`。
- **任务摘要页**：9 关一律播 A07 的时间轴（`shell.TEMPLATE`、`apt_textures.patch(.., donor=)`、`shell.retime`、`shell.views`）；目标位置取 `shell_missions*.json` 的 `targets`；地图图片 `work/shell/map_plain.png`（`maprender.py CampShell --plain --px 2 -o ...`，是上次构建的地图画的，地图改了要先重画再构建）。
- **局势介绍世界地图标记**：`shell.GRID`、`shell.retarget()`、`experimental/campaign/apt_movie.py`；测试 `test_every_slots_world_map_points_at_its_own_place`。
- **地图页和草图编辑器**（`experimental/mappage/`，ADR 0017）：本地运行 `python -I -X utf8 experimental/mappage/serve.py --new`（`.claude/launch.json` 的 `mapsketch`，8766）；草图在 `work/mappage/<名>/sketch.json`；格式见 [sketch-format.md](sketch-format.md)；命令行 `sketch2map.py <名字> --check --sketch 文件.json`；改了 `sketch2map.py` 要重启服务；`platmap.Layout.brushes` 是关卡线文件上加的可选字段；"看不见的墙"见 [engine/terrain.md](../engine/terrain.md) 第 3 节。测试 `tests/test_mappage*.py`。
- 重建并装 Mods：先单独查游戏有没有在运行；构建工具有锁，别和关卡线同时建。

## 验证方式

- 离线：`python -m pytest -q tests/test_shell.py tests/test_architecture.py tests/test_docs.py`（跑测试一律带 `tests` 路径，裸跑 `pytest -q` 会收集到 `work/downloads` 和 `.claude/worktrees`，还曾留下乱名文件 `-q`）。
- 进游戏：`bench_start(chapter=N)`；`shell_shots.py --tour overview --slot 4 --linger 40`（世界地图标记、头像比例、任务摘要）、`--tour chapters`（三个图标）。
- 指纹：`fingerprint.py record <名>` 后 `diff baseline <名>`（后台约 8 分钟）。要在源码不动时比，用临时 worktree。

## 坑

- 指纹比"某个提交前后"：`git worktree add --detach ../RA3-CampaignLab-fp <提交>`，`work` 用 `New-Item -ItemType Junction` 指回主仓库；用完**先** `[System.IO.Directory]::Delete(联接, $false)` 只删联接，再 `git worktree remove --force`，否则可能顺着联接删掉主仓库的 `work/`。临时 worktree `../RA3-CampaignLab-p2` 可能还在，同法处理（`cmd /c rmdir` 拆联接）。
- 指纹跑着时别改活文件：三个目标是三个新进程，各自重新 import 工作区代码。
- hold 模式下战败卡片会被暂停用的 Esc 跳过，看结局卡片用 `bench_watch(every=2, sheet=false)`，别用 `bench_wait`。
- 外壳 A4 里框选常选不到人（单位在画面外），用 `bench_key(81)`（Q 全选）再右键。
- 视频包并发：`shell.contribute` 必须用 `video_pack.Later`（`video.xml` 到 `build_mod` 锁里才写），别直接调 `video_pack.make()`。
- 草稿脚本放 scratchpad：`python -c` / heredoc 写文件带反斜杠会被仓库 hook 拦，改用 Write 写 .py 再跑。
- 原版不带 mod 的 `--tour overview` 点"继续"后截不到帧（`work/logs/plain4.log`，原因没查）；看原版任务摘要页得换走法或手动驾驶。
- 游戏报 D3DERR_DEVICELOST 时是屏幕被占或锁屏，`shell_shots.py` 截不了。
- 内置浏览器窗格被缩放模拟或隐藏时，截图坐标和页面像素不成比例，`requestAnimationFrame`/`ResizeObserver` 不跑，改宽度后要手动调 `fit()`。
- `tests/test_architecture.py` 别的线也在改，提交时只暂存自己那段（`git hash-object -w` + `git update-index --cacheinfo`）。
