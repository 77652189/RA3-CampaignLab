# 外壳线交接

外壳线 2026-11-03 从关卡线拆出（[architecture.md](../architecture.md) 各线负责的文件）。以前做过的事和坑在 [story/handoff.md](../story/handoff.md) 搜"外壳""CampShell"（第 33～42、61～69 行）。问题编号见 [issues.md](../issues.md) K9。

## ADR 0016 第 1 阶段：打包收口（2026-11-03 恢复，总控派活）

任务四步，都是纯重构，每步要求：`fingerprint.py record shell_s<N>`（后台约 8 分钟）后 `diff baseline shell_s<N>` 三个目标一致，`pytest -q tests` 全过，小步提交只提交自己的文件。

- **第 1 步 已提交**（git log 搜 "phase 1 step 1"）：c4/c6/c7/c18 导入时的接线都挪进各自的 `install()`（逐级调下一层），`package.assemble` 和 `make_campnew23` 显式调 `c18.install()`（c23 是单位线 make_campchrono 链上的，只加了这一行）。守卫 G7 在 `tests/test_architecture.py` 末尾（新解释器里逐个 import，后面的 import 不许改前面模块的状态）。变异检验脚本 `work/shell/phase1/g7_mutate.py`（改坏 c18/c4/c6 → 报错，按字节还原 → 通过）。指纹 shell_s1 一致。
- **第 2 步 见 git log "phase 1 step 2"**：`package.py` 里 `ModSpec`（冻结数据类）、`with_more(spec, **more)`（元组追加、字典合并，层只用它往里加）、`spec_of(mission, test, shell, name)`、`mod_folder(name)`（CNV_OUT_DIR / 暂存 / Mods 的选择）、`build_mod(spec, out)`（进来快照 c2..c18 全部模块变量，`c18.install()` 后灌清单，出去原地恢复）。外壳这一步还内联在 `spec_of` 里。单测 `tests/test_package.py`（同进程构建两次不串，用假 `c4.main`）。如果 git log 里没有 step 2，说明指纹没过，先看 `work/logs/fp_shell_s2.log` 和 `fingerprint.py diff baseline shell_s2`。
- **第 3 步 下一步**：草稿在 `work/shell/phase1/contribute_s3.txt`（`shell.contribute(spec, lang) -> spec`，加 `launcher=False`）。要做的：把这段加到 `shell.py` 末尾；`ModSpec` 加字段 `launcher: bool = True`；`build_mod` 在 `write_sidecar` 前 `if not spec.launcher` 删 `Play_<name>.bat`；`spec_of` 里 `if shell:` 那段换成 `spec = shell.contribute(spec, lang)`；`build.py` 第 474～475 行删 bat 的两行去掉（只动 --shell 那段）。然后指纹 shell_s3。
- **第 4 步**：只设计接口。打算：`spec_of(..., layers=())`，每个层是 `spec -> spec` 的函数，只用 `with_more` 加东西，`map_edits` 是元组，检查层把自己的脚本作为一个追加的 map edit 叠在外壳后面；在 `ModSpec` 文档里写明。`build.py --shell --check` 下一阶段再放开（G8）。
- 之后才是下面"下一步"第 3 项（重建 CampShell/CampShellEn，装 Mods 前单独查游戏在不在跑）。

坑：Bash 里 heredoc / `python -c` 写文件只要带反斜杠（包括 `\n`）就被 hook 拦，改写成 scratchpad 里的 .py 再跑。`tests/test_architecture.py` 别的线也在改（关卡线的 G9），提交时只暂存自己那段（用 `git hash-object -w` + `git update-index --cacheinfo`）。指纹跑着的时候别改活文件：三个目标是三个新进程，各自重新 import 工作区代码。

**此前暂停（2026-11-03 夜，总控通知）**：产品线暂停，等架构评审定打包层（`make_campnew*`）怎么整合，总控通知后再按下面的"下一步"恢复。

## 做到哪了（2026-11-03 夜，第一个外壳线会话）

已提交（见 git log 里 "Shell line" 那条），**CampShell / CampShellEn 都还没用这批代码重建，Mods 里还是旧的**：

- **I10 地图标记**：原版世界地图（`fe_missionBriefingAssets` 的 `global_map2`）是经纬度直角网格，用 23 个原版局势介绍拟合出来：`shell.GRID`，x 误差 10 px、y 误差 5 px。每关在 `shell_missions*.json` 里有 `where: [纬度, 经度]`，`shell.retarget()` 改局势介绍的时间轴：地图每帧多平移 zoom·dx、在放大的帧里上移 (zoom−1)·dy，标记（方框、闪烁方块、十字线）下移 dy。这样每一帧标记都压在这个地方上，缩放到全图时地图的上下取景不变。时间轴读写在新模块 `experimental/campaign/apt_movie.py`（只读主时间轴，原地改浮点，长度不变）；`apt_textures.patch(.., movie=)` 是接口。离线检查：`tests/test_shell.py::test_every_slots_world_map_points_at_its_own_place`。**没进游戏看过**：重点看札幌那关放大后标记在不在画面里、地图上沿有没有露边。
- **I10 头像比例**：原版 `AMB0k.vp6` 是 512×288。`to_vp6.py --size head`，`shell.HEAD_SIZE`，`head_clip()` 改成按 16:9 裁沃斯定妆照（缓存文件名改成 `work/shell/voss_head169.mp4`，旧的 288 版不再使用）。
- **I12 章节列表三个阵营图标**：在 `mouse_chapterselectcomponent`（鼠标界面）和 `chapterselectcomponent`（手柄界面）的唯一一张贴图里，`shell.ICON_BOXES` + `faction_icons()` 涂成占位，两个流都进 big。
- `shell_shots.py --tour overview` 加了 `--slot K`、`--linger 秒`、`--look 帧数`。

## 下一步

1. **I11 任务摘要页**（已查清，没动手）。原版 `aNN_objective_briefing` 是固定 1140 帧（约 38 秒）的时间轴，不等配音：第 2 帧旁白 1、259 帧放大、269 帧旁白 2 + 目标方块闪、289 帧绿色目标标记、409 帧再移、419 帧旁白 3、569 帧旁白 4、799 帧拉远、809 帧旁白 5（A04 用的是 01、04、03、05、06 号旁白）。地图是精灵（A04 是第 4 号角色），缩放 0.479（全图）→0.936→平移→0.774；**最后没拉回全图**。读法：草稿脚本思路是解帧动作里的 `0xA1` 压字符串（4 字节对齐的指针），能读出 `playSound_<事件名>` 的顺序。我们的问题有三个：
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
