# 外壳线交接

外壳线 2026-11-03 从关卡线拆出（[architecture.md](../architecture.md) 各线负责的文件）。以前做过的事和坑在 [story/handoff.md](../story/handoff.md) 搜"外壳""CampShell"（第 33～42、61～69 行）。问题编号见 [issues.md](../issues.md) K9。

## I11 任务摘要页（2026-11-04，总控派活，git log 搜 "I11"）

- **查到的**：原版 9 关的任务摘要时间轴各不相同（A04 拉近三次、最后不拉回全图、没有箭头；A01/A03/A05/A06 不拉远；A07/A09 有拉远）。逐关原地改时间轴凑不出统一结构（帧数、物件都是固定的）。调查脚本思路：主时间轴里地图是第 4 号精灵、深度 2；标记、箭头都是从 `fe_objectiveBriefingsAssets` 导入的字符（`box 2 fill/outline`、`OI Primary *`、`blue arrow thin` + `mask`），放在主时间轴的屏幕坐标上；每关脚本常量里都有 9 关全部旁白事件的表。
- **源头改法**：9 关的任务摘要一律播 A07 的时间轴（`shell.TEMPLATE`）：全图 + 简报 → 拉近到目标 1、两支箭头合拢 → 拉回全图，目标 1 标记、箭头路线到目标 2、目标 2 标记。`apt_textures.patch(.., donor=)` 把 A07 的 AptAptData/AptConstData/AptDatData 换进第 k 关自己的流（形状 3 + 贴图 1 是每关自己的，字符编号 9 关一致），条目的尺寸、内容哈希跟着改，**四个文件都要发**。`shell.retime` 按 `ROLES`（按物件放上来的帧分：zoom / mark / route）把标记、箭头搬到我们的目标；地图每帧按原版缩放比例在我们的"全图""拉近"两个视角之间插值（`shell.views`：全图铺满窗口，拉近倍数同 A07，拉近时目标 1 落在 A07 的焦点上，再限制在地图内不露边）。旁白 5 句按播放顺序：简报第一句、目标 1、简报其余、目标 2、收尾（`narration_lines`）；事件名 `CNV_SHELL_I_<关><序>00`，别关的表改成 `CNV_SHELL_X_..`（不配字幕，也不会播）。
- **目标位置**：建好的那关读 `shell_missions*.json` 的 `targets`（地图公开的地点名，A4 是 `halt`、`harbour`），`site_targets` 按地图第一个 BORDERS（全图）折成图上比例；其余 8 关用 `PLACEHOLDER_TARGETS`。
- **地图图片**：改成 `work/shell/map_plain.png`（`maprender.py CampShell --plain --px 2 -o work/shell/map_plain.png`，只画地面，没有网格、触发区、调试标签）。`maprender.py` 加了 `--plain` / `render(plain=)`，默认行为不变。**缺点**：图是上一次构建的地图画的，地图改了要先重跑这条命令再构建。
- **检查**：`tests/test_shell.py::test_every_objective_briefing_zooms_onto_objective_1_points_arrows_and_ends_on_the_whole_map_with_both_marked`，9 关参数化：拉近（最大缩放 > 1.5 倍全图）且最后回到全图、拉近时和全图时都有箭头、全图上至少两个标记且都在窗口里、播的 5 句是本关的且都有字幕、没有原版旁白事件。
- **重建已做**（11-04）：CampShell、CampShellEn 都用新代码装进 Mods（`work/logs/i11_build_zh.log`、`i11_build_en.log`）。**游戏内自查没做成**：`shell_shots.py` 又报 D3DERR_DEVICELOST（屏幕被占），截图命令见"下一步"第 3 项（`--slot 4 --linger 26`，看第 7～15 秒拉近和箭头、第 16 秒以后拉回全图、字幕是不是我们的 5 句）。原版对照没截到：A07 的原版任务摘要可以 `--plain --slot 7` 截（之前 `--plain` 点"继续"后截不到帧，见坑）。
- **没做**（接着做）：见下面"下一步"第 1、2 项。

## ADR 0016 第 2 阶段第一块：检查叠在外壳上（2026-11-04，总控派活，git log 搜 "phase 2" + "Shell line"）

- **做了什么**：`build.py <关> --shell --check <检查>` 放开（`build.parse()` 抽出来了）。检查经 `package.check_layer(m, t)` 叠成一层：只往那一关的地图追加路点、物体、脚本、触发区（`package.write_more`，复用 `write_map` 存在 `m.cnv_like` 上的摆放模板），字串、单位走 `with_more`。构建前先过 `contract.observes(m, t)`：不是只观测就拒绝并列出原因；`--unit` 照样构建但叫机关单测，结果首行打"机关单测，不算验收"。mod 名：验收版 CampShellT / CampShellEnT，机关单测 CampShellU / CampShellEnU，正式版 CampShell 不动。
- **测试台**：检查层给 `ModSpec.bench` 写 `{'slot': k}`，`write_sidecar` 只在有这一项时写进 `cnv_map.json`（正式版 sidecar 字节不变）。`harness.start` 没给 steps 时读到 slot 就走 `harness.shell_steps(slot)`（主菜单 → 战役子菜单的章节按钮 → `chapter_step(slot)` → nav.json 第 3 步以后）。`shell_shots.chapter_step` 现在就是 `harness.chapter_step`。`bench_mcp.cnv_check` 加了 `shell`、`unit` 两个参数。
- **守卫 G8** 在 `tests/test_architecture.py` 末尾（子进程里把构建桩掉，只验接线：只观测的 → CampShellT + 层；会动手的 → 拒绝；`--unit` → CampShellU）。变异脚本 `work/shell/phase2/g8_mutate.py`（改的是副本，不碰活文件），5 种改坏都抓到，还原通过。离线等价测试 `tests/test_shell.py::test_a_check_as_a_layer_writes_the_map_the_merged_build_writes`：叠层写出的地图脚本、触发区、物体数和合并构建完全相同。
- **验证**：指纹 shell_p2b 三个目标和 baseline 一致；pytest 386 过 1 跳过（在临时 worktree `../RA3-CampaignLab-p2` 里跑的：HEAD + 外壳线这几个文件，因为关卡线工作区里 `devices/horn.py` 正改到一半，a4 编不过）。测试台：`a4 --shell --check win --unit` RESULT PASS（第 4 关从章节列表进去，计数器读到）；`a4 --check win` 单关版两次 FAIL（一次 Esc 打不开菜单，一次车数一直 0、第 526 秒结束），判定对不上的原因见汇报。
- **视频包的并发问题（11-04 修了）**：原来 `shell.contribute` 直接调 `video_pack.make()`，在构建锁外面就写 `SDK/Mods/CNVVideo/Data/video.xml`，两个构建并行时互相覆盖（指纹 shell_p2 的 CampShell 丢了 CNVHEAD01、CNVINTRO01..）。现在改用 `video_pack.Later`：片子清单在 contribute 时定下，`video.xml` 等 `build_mod` 在锁里取 `include` 时才写（测试 `tests/test_video.py` 最后一条）。音乐包（`music/pack.Later`）、配音包（`voice_link.Later`）、关卡自带的头像片（`clips.Clips`）、`movie_bench.LazyPack` 本来就是懒的，没有这个问题。指纹 shell_p2c 和 baseline 比见提交说明。
- **乱名文件 `-q`（11-04 查了，没找到写它的命令）**：`work/logs/stray_q.y4m`，11-04 00:00:32 写出。文件头 `YUV4MPEG2 W288 H288 F24000:1001 Ip A1:1 C420jpeg`、96 帧，和 `to_vp6.py` 第 65 行写的一字不差；**不是 ffmpeg**（ffmpeg 的 y4m 头会带 `XYSCSS=`/`XCOLORRANGE=`），也不是 nihav（它的 y4m 头没有 `Ip A1:1`）。仓库代码里没有任何地方把 `-q` 传成路径（to_vp6 只把 y4m 写进临时目录，调用方 clips.py、shell.py 参数都对）。4 秒后有人在仓库根目录裸跑了 `pytest -q`（`work/logs/pytest_k1_bare.log`，没给 `tests` 路径，连 `work/downloads` 和 `.claude/worktrees` 下的测试都收集了），时间上最可疑，但收集到的测试里也没找到会写 y4m 的。结论：多半是某个会话手敲的一次性命令；仓库里没有要修的代码。以后跑测试一律带 `tests` 路径。
- 临时 worktree `../RA3-CampaignLab-p2`（detached HEAD，`work` 是指回主目录的目录联接）还留着。要删时**先单独拆掉联接**（`cmd /c rmdir ..\RA3-CampaignLab-p2\work`，只删联接本身），确认主目录 work/ 还在，再 `git worktree remove`；不先拆联接就整目录删，可能把主目录的 work/ 一起删掉。

## ADR 0016 第 1 阶段：打包收口（2026-11-03 恢复，总控派活）

任务四步，都是纯重构，每步要求：`fingerprint.py record shell_s<N>`（后台约 8 分钟）后 `diff baseline shell_s<N>` 三个目标一致，`pytest -q tests` 全过，小步提交只提交自己的文件。

- **第 1 步 已提交**（git log 搜 "phase 1 step 1"）：c4/c6/c7/c18 导入时的接线都挪进各自的 `install()`（逐级调下一层），`package.assemble` 和 `make_campnew23` 显式调 `c18.install()`（c23 是单位线 make_campchrono 链上的，只加了这一行）。守卫 G7 在 `tests/test_architecture.py` 末尾（新解释器里逐个 import，后面的 import 不许改前面模块的状态）。变异检验脚本 `work/shell/phase1/g7_mutate.py`（改坏 c18/c4/c6 → 报错，按字节还原 → 通过）。指纹 shell_s1 一致。
- **第 2 步 见 git log "phase 1 step 2"**：`package.py` 里 `ModSpec`（冻结数据类）、`with_more(spec, **more)`（元组追加、字典合并，层只用它往里加）、`spec_of(mission, test, shell, name)`、`mod_folder(name)`（CNV_OUT_DIR / 暂存 / Mods 的选择）、`build_mod(spec, out)`（进来快照 c2..c18 全部模块变量，`c18.install()` 后灌清单，出去原地恢复）。外壳这一步还内联在 `spec_of` 里。单测 `tests/test_package.py`（同进程构建两次不串，用假 `c4.main`）。如果 git log 里没有 step 2，说明指纹没过，先看 `work/logs/fp_shell_s2.log` 和 `fingerprint.py diff baseline shell_s2`。
- **第 3 步 已提交**（git log 搜 "phase 1 step 3"）：`shell.contribute(spec, lang)` 在 `shell.py` 末尾，`spec_of` 只调它；`ModSpec.launcher`，`build_mod` 按它删 bat，`build.py` 不再自己删。指纹 shell_s3 一致。
- **第 4 步 已提交**（"phase 1 step 4"）：`spec_of` / `assemble` 收 `layers=()`，层的约定写在 `ModSpec` 文档里。`build.py --shell --check` 归第 2 阶段（总控放开）。指纹 shell_s4 一致。`tests/test_package.py` 并进了 `tests/test_shell.py`（它改 sys.path，让 G4 超了上限）。
- **重建已做**（11-03 22:44/22:47）：CampShell、CampShellEn 都用新代码装进 Mods。**游戏内自查没做成**：`shell_shots.py` 启动时游戏报 D3DERR_DEVICELOST（屏幕被占或锁屏，`work/logs/sc_zh_overview.log`）。屏幕空出来后照下面"下一步"第 3 项截图；issues.md 里 I10、I12 已标"修了待验"，I15 还是待修（差 9 关逐关进游戏），I11 没动手。

坑：Bash 里 heredoc / `python -c` 写文件只要带反斜杠（包括 `\n`）就被 hook 拦，改写成 scratchpad 里的 .py 再跑。`tests/test_architecture.py` 别的线也在改（关卡线的 G9），提交时只暂存自己那段（用 `git hash-object -w` + `git update-index --cacheinfo`）。指纹跑着的时候别改活文件：三个目标是三个新进程，各自重新 import 工作区代码。

**此前暂停（2026-11-03 夜，总控通知）**：产品线暂停，等架构评审定打包层（`make_campnew*`）怎么整合，总控通知后再按下面的"下一步"恢复。

## 做到哪了（2026-11-03 夜，第一个外壳线会话）

已提交（见 git log 里 "Shell line" 那条），**CampShell / CampShellEn 都还没用这批代码重建，Mods 里还是旧的**：

- **I10 地图标记**：原版世界地图（`fe_missionBriefingAssets` 的 `global_map2`）是经纬度直角网格，用 23 个原版局势介绍拟合出来：`shell.GRID`，x 误差 10 px、y 误差 5 px。每关在 `shell_missions*.json` 里有 `where: [纬度, 经度]`，`shell.retarget()` 改局势介绍的时间轴：地图每帧多平移 zoom·dx、在放大的帧里上移 (zoom−1)·dy，标记（方框、闪烁方块、十字线）下移 dy。这样每一帧标记都压在这个地方上，缩放到全图时地图的上下取景不变。时间轴读写在新模块 `experimental/campaign/apt_movie.py`（只读主时间轴，原地改浮点，长度不变）；`apt_textures.patch(.., movie=)` 是接口。离线检查：`tests/test_shell.py::test_every_slots_world_map_points_at_its_own_place`。**没进游戏看过**：重点看札幌那关放大后标记在不在画面里、地图上沿有没有露边。
- **I10 头像比例**：原版 `AMB0k.vp6` 是 512×288。`to_vp6.py --size head`，`shell.HEAD_SIZE`，`head_clip()` 改成按 16:9 裁沃斯定妆照（缓存文件名改成 `work/shell/voss_head169.mp4`，旧的 288 版不再使用）。
- **I12 章节列表三个阵营图标**：在 `mouse_chapterselectcomponent`（鼠标界面）和 `chapterselectcomponent`（手柄界面）的唯一一张贴图里，`shell.ICON_BOXES` + `faction_icons()` 涂成占位，两个流都进 big。
- `shell_shots.py --tour overview` 加了 `--slot K`、`--linger 秒`、`--look 帧数`。

## 下一步

1. **I11 剩下的**：(a) 指挥官摘要页：11-04 截图（`work/shell/i11_before/commander_02.png`）里任务说明已经是我们的文字，还剩原版的是指挥官名一栏的"—"、五颗星、左边空着的头像框、"指挥官 2 —"；先用第 2 项的检查列出这一屏和它导入的组件里所有 `$标签`，再逐条换或写进保留清单。(b) 地图图片改成构建时从正在构建的地图画（现在用上一次构建的图；做法：`ModSpec` 加一个拿到改完的 MapFile 后再出文件的钩子，`build_mod` 在 `c4.main` 拼 `EXTRA_FILES` 之前调用——`make_campnew4.main` 第 58 行是在 `c2.map_files()` 之后才读 `EXTRA_FILES` 的）。(c) 两个目标离得近时路线箭头跟着缩小（A4 缩到 0.4 倍），进游戏看是否太细，太细就给 `retime` 的 route 加最小缩放。
   以下是 11-03 的调查，已按上面的"I11 任务摘要页"一节做完：原版 `aNN_objective_briefing` 是固定 1140 帧（约 38 秒）的时间轴，不等配音：第 2 帧旁白 1、259 帧放大、269 帧旁白 2 + 目标方块闪、289 帧绿色目标标记、409 帧再移、419 帧旁白 3、569 帧旁白 4、799 帧拉远、809 帧旁白 5（A04 用的是 01、04、03、05、06 号旁白）。地图是精灵（A04 是第 4 号角色），缩放 0.479（全图）→0.936→平移→0.774；**最后没拉回全图**。读法：草稿脚本思路是解帧动作里的 `0xA1` 压字符串（4 字节对齐的指针），能读出 `playSound_<事件名>` 的顺序。我们的问题有三个：
   - **地图图片是开发用的预览图**（`work/maps/CampA4_mcp.png`），带"CNV A4 Truck1""Approach 1"这类调试标签和触发区方框，放大后玩家看得见。要换成不带标注的俯视图（先查 `cnv_map` / `cnv_preview` 有没有干净的出图选项；`cnv/` 是关卡线的，要加选项先打招呼）。
   - **放大落点是原版直布罗陀的坐标**，在我们的图上是空角落；绿色目标标记也在原版位置。做法：把时间轴分成"静止段"和"运动段"，每个静止段的焦点换成我们第 k 个目标的位置（从关卡公开的地点取，`m.site`，在 `shell_missions.json` 里写地点名，不写坐标），运动段按帧插值；屏幕上的标记跟着焦点走就不用单独挪。最后一段改成拉回第 0 帧的全图视角。精灵坐标约等于贴图像素（0.479×1024≈490，正好是全图框宽），先离线算、再进游戏核对。
   - **旁白字幕**：现在第 1 句是简报、第 2 句是所有目标、其余是标题占位（`narration_strings`）。要按时间轴里出现的顺序配：第 1 句简报，第 2、3 句是目标 1、2 的说明（和放大同步），最后一句收尾。
   - 指挥官摘要页剩下的原版文字：先在 CampShell 上 `--tour overview --slot 4` 截 `commander_*` 看还剩哪些，再查标签覆盖。
2. **K9 类检查（ADR 0015，还没写）**：外壳构建时列出玩家能看到的原版内容，凡没替换、也没显式标"保留原版"（要写原因）的就报错。范围：`fes_m_factionmenu`、`fes_m_chapterselect`、`fes_m_missionbriefing`、各关 `aNN_global/objective_briefing`、`tacticalhudcoopaiorderpanel`、`loadscreencampaign`，**加上它们按名字导入的组件库**（AptAptData 里的导入是"库路径 + 符号名"两串，取路径最后一段小写就是流名，如 `mouse_chapterSelectComponent`、`fe_missionBriefingAssets`、`fe_m_generalScreenComponents`）。I12 就是漏在导入的组件里，所以必须递归导入。检查三样：每张 `Texture`、每个 `$标签`（AptAptData/AptConstData 里以 `$` 开头的字符串，`$DIALOGEVENT:` 另算）、战役模板里每个视频字段。通用界面框架（按钮、边框、扫描线）列进保留清单，逐张写原因。
3. **重建并装 Mods**：先单独查游戏有没有在运行；`python -I -X utf8 experimental/cnv/build.py a4 --shell` 和 `... --shell --lang intl`（I15，国际版还要带配音线的新音频）。然后 CampShell 上截：`--tour overview --slot 4 --linger 40`（世界地图标记、头像比例、任务摘要），`--tour chapters`（三个图标）；国际版 9 关逐个 `--slot K` 走进游戏看不崩。
4. 改 `docs/issues.md` 里 I10、I11、I12、I15 的状态为"修了待验"（只有这一处允许外壳线改），报告写类别怎么从源头改、对应检查、提交号、CampShell 已重建。

## 坑

- 草稿脚本放 scratchpad 时，`python -c` / heredoc 写文件里带反斜杠会被仓库的 hook 拦，改用 Write 写 .py 再跑。
- 原版不带 mod 的 `--tour overview` 在点"继续"之后截不到帧了（`work/logs/plain4.log`），原因没查；要看原版任务摘要页得换个走法，或者手动驾驶。
- 测试 `test_level_cards.py::test_plans_compile_against_the_published_interfaces` 现在失败，是关卡线没提交的 `checks/a4.py`（多了 `placem`），不是外壳线的。
