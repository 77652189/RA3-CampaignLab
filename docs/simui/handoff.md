# 模拟器界面线交接

授权和边界：[ADR 0024](../adr/0024-playable-simulator.md)（对齐优先、不改规则、代码放 `experimental/simui/`）。

## 现状（2026-11-08）

- 启动：`python -I -X utf8 experimental/simui/serve.py a4`，打开 http://127.0.0.1:8724/ （`--open` 自动开浏览器，`--level easy|normal|hard`）。`.claude/launch.json` 里有 `simui`。
- 文件：`experimental/simui/game.py`（后端：`PlaySim` 外挂 + `Session`）、`serve.py`（http.server + JSON）、`index.html`（单文件 canvas）；测试 `tests/test_simui.py`（5 项，约 2.5 分钟）。
- 对齐做法：玩家的点击变成剧本事件元组（派 / 攻击 / 放 / 占领 / 生产），放到 `Sim.events` 的当前 tick，由 `Sim.happen` 执行，和 `plays/<关>.txt` 走同一条路；`Session.tick` 就是 `Sim.run` 的循环体（去掉"两分钟没变化就停"）。`PlaySim.happened` 记下每个执行过的事件，`game.replay()` 喂回去得到同一局（测试守着）。
- 已通：A4 从开场打到结局；Esc 跳过场；1/2/4/8/尽快；按阶段跳（阶段 = `CNV_<关>_Phase_N` 旗，用全程脚本打到旗亮，再丢掉脚本剩下的命令交给玩家，A4 跳第 3 阶段约 17 秒）；赢/输画面带用时；字幕框、对白面板、目标、计数/倒计时、黑边、锁操作、过场镜头跟脚本；配音先找录音（`experimental/simui/voice`、`work/voice`、配音仓库 `RA3-ChineseVoice/work/campaign/{zh,en}/<关>/`），找不到用浏览器朗读中文；`Sim.unmodeled` 和覆盖清单列在右栏，涉及的单位画紫色虚线圈；覆盖清单有未登记项时开局弹警告。
- 16 关都能打开（冒烟：建局、跑 30 秒、出状态）；有全程脚本的是 a1 a3 a4 a6 a7 a8 a9 j7，其余关不能按阶段跳；j4 没有阶段旗。

- 配音一条声道（用户 11-08 报"语音明显重叠"）：归因是界面问题——A4 全程脚本按录音真实时长排开没有一处重叠；旧页面每条一到就播，跳过场/跳阶段/暂停时旧的不停，一次轮询收到几条就同时播，零售播报 `Aeva_*` 没录音时浏览器把英文键名念出来。现在照引擎的规则（`voice_link.Later.length`：对白事件排队，一句播完才下一句）在后端按游戏时间排队（`PlaySim.act`、`Voice`、`voice_waits`），跑到开始时刻才交给页面；页面同时只放一句，新一句来就切掉旧的，晚到的从当前位置起播，暂停跟着暂停，4×以上/跳过场/跳阶段/重开不出声。测试 `test_simui` 加 4 项（含"A4 全程没有一句被排队推迟"，挂了就是关卡的问题，转关卡线）。临时检查用的 `.claude/launch.json` 配置 `simui-check`（端口 8726），不占用户在玩的那个端口。

- 地图朝向（用户 11-08 "北基地怎么在南边"）：旧 `W2S`/`S2W` 把世界 y 当屏幕 y，整张图上下镜像。现在朝向只在 `maprender.SCREEN_Y`（= -1，北在上）定义一次，`maprender.north_up` 和页面都用它（`/api/static` 的 `screen_y`）；地形图翻行、边界、拖动平移、方向键、建筑朝向跟着改，框选和缩放走 `S2W` 不用改。已和 `cnv_map CampA4` 的俯视图对过。测试 `test_the_page_draws_north_up_by_the_map_pictures_own_definition`。
- 配音排队的依据：`docs/story/handoff.md` 第 59 行"引擎把配音排队播"（在 CampShell 游戏里看到的，`r3_fine*` 逐秒截图；不是测试台计数器量出来的）。关卡线会在游戏里再实测核实；结论变了就改 `PlaySim.act` 的排队。

## 新方向（总控 2026-11-08，排在下面"下一步"前面）

用户定了：亲手试玩改在**游戏里**做，模拟器界面只留给看自动跑的局和查问题。

1. **游戏里的开发开关**（先做 A4）：在 mod 的试玩启动方式里加三个开关：①跳到第 N 阶段；②快进，复用测试台的变速垫片（`experimental/testbench`，ADR 0007）；③跳过场，直接到交还操作。
   - 跳阶段读关卡线定的"阶段存档点清单"，游戏和模拟器共用这一份源头。格式问关卡线（会话 id 问总控）。要直接摆到那个阶段，不复刻玩家的过程。
   - 这些开关只在试玩版里有，正式版没有（ADR 0016：测试版 = 正式版加观测）。
   - 模拟器界面的"跳到阶段"也改成读同一份清单；现在是用全程脚本重放（`Session.jump`）。
   - 装 mod 前先单独检查游戏是否在运行，在运行就停下问。
   - 先读：ADR 0007、ADR 0016、`experimental/testbench`（变速垫片），还有试玩版是怎么构建的（`build.resolve` / `build_mod(ModSpec)`）。
2. 原来的"下一步"第 2 项（7 关各玩一遍）排到后面。

### 第 1 条的进度（2026-11-08）

- **快进、跳过场：做在变速垫片里，不改 mod**（试玩版 = 正式版 CampShell 原样 + 从试玩专用游戏副本启动）。`capture_shim.cpp` 新增"the playtest's keys"一节，只在 `CNV_DEV_KEYS=1`（且 `CNV_SPEED` 已挂钟）时生效：Ctrl+Alt+= / - / 0 调 1/2/4/8 倍；Ctrl+Alt+空格跳过场 = 8 倍跑到黑边消失再回原速（不截断过场，脚本照常全跑，和模拟器一致）；左上角小方块显示倍速。`dev.req` 文件（faster/slower/normal/skip）走同一函数，供测试台验证。
- 启动：`python -I -X utf8 experimental/cnv/playtest.py [intl] [-win]`；副本 `work/testbench/RA3play`（`--prepare` 建副本/刷新垫片，已建好）；任何红警3在运行就拒绝。单测 `tests/test_playtest.py`（3 项过）。
- 游戏内验证：`python -X utf8 experimental/testbench/devkeys_check.py 4`（从 testbench 目录跑，走 CampShell 第 4 槽 = A4，停在开场过场里发 skip/faster/normal/skip）。11-08 结果 RESULT PASS：开场过场 8 倍跑完用 10.6 秒真实时间，黑边消失后回 1 倍；1→2→4→8→1；无过场时 1.5 秒自动结束。真键盘热键还没有人手按过（`dev.req` 和热键走同一函数）——用户第一次试玩时顺便确认。
- 踩坑：第一次实测游戏在第一帧附近崩（0xC0000005）；不开热键同副本正常，再开热键启动没复现。若再崩，先怀疑 `poll_dev` 用 `o_GetAsyncKeyState`（GetAsyncKeyState 可能被别的钩子"chained in front"）。
- 共享测试台在别的线手里时 `devkeys_check` 会拒绝（只认"有红警3在跑"），要等它空。
- `test_architecture.py::test_g4_sys_path_ratchet` 现在 130 > 129，不是本线文件造成的（新文件都没改 sys.path），没动。
- **跳阶段：暂停**（总控 11-08：用户定引擎优先，ADR 0026，关卡暂停推新内容；跳阶段等关卡恢复后的阶段存档点清单再做）。之前已向关卡线（`local_3846ee54-ebdf-4bbd-b2e4-0a3ec2535997`）回格式。已发建议：`docs/levels/checkpoints/<关>.json`，每阶段含旗、关卡秒、目标状态、钱、边界、玩家单位（角色/模板+坐标+血）、敌方剩余、可选变体；游戏侧需要编译器从第 k 段起跑的入口（如 `Compiler(start_phase=k)`）。
- 没做：桌面快捷方式/HTA 里的"试玩版"按钮（现在只能命令行启动）。

## 没做到 / 已知缺口

- 引擎 A 已加（5d41212）：`Sim.point` 认 '@x,y'（`model.coord`）、剧本动词"走"（纯移动）。界面已接上：右键 = 走，Alt+右键 = 派（攻击移动）；外挂里自己解析坐标的代码删了。测试里点击记录直接喂给原版 `sim.Sim` 也得到同一局。
- 生产出的单位名带 '#'，剧本行写不出来（引擎线已记入它的交接）；`/api/replay` 导出的文本只给人看，回放要用事件元组（`game.replay` 或 `Sim.events`）。
- G4 守卫（改 sys.path 的文件数上限 129）：`serve.py` 和测试都按文件路径加载 `game.py`，不新增 sys.path 改动；`game.py` 自己沿用 simshow 的写法把 cnv 目录加进路径。
- "对照局结局一致"这条可试玩条件界面没检查，只检查了覆盖清单。
- 雾：默认按 `Sim.sees` 隐藏雾里的敌人（"雾"按钮可显示）；小地图、编队、停止/驻守命令没有。
- 跳阶段是重放，不是存档点（`copy.deepcopy(Sim)` 因模块引用失败）；慢的关可考虑缓存。
- 生产只在 a2 验过（兵营出侦察兵）；A4 玩家不生产（脚本用"造"直接放单位）。

## 下一步（推荐顺序）

总控 2026-11-08 派的三件，按这个顺序：

1. 在前台浏览器里手点一次右键纯移动（这次预览窗格被隐藏，画布点击没重测；接口和测试已验）。预览窗格隐藏时画布尺寸是 0，合成的鼠标事件不会生效，要先让用户把窗格显示出来。
2. 其余有全程脚本的关各玩一遍找界面问题（a1 a3 a6 a7 a8 a9 j7）：用"尽快"加按阶段跳，看画面、字幕、目标、结局有没有错。
3. 可试玩条件"最近一次对照局结局一致"显示在界面上，没有记录就标"未对照"。对照局结果由关卡线产出，界面只读。
   - 现状：`experimental/cnv/playcheck.py`（对照局，跑测试台）目前不往文件里写结果，所以还没有可读的记录。
   - 先和关卡线（会话 id 问总控）商量文件位置和格式。建议：一关一个 JSON，放在 `docs/levels/compare/<关>.json`，字段有日期、提交号、模拟器结局和用时、测试台结局和用时、关键时间差，以及是否一致（按 ADR 0023：结局相同，且关键时间差在 15% 以内）。
   - 界面：`serve.py` 的 `/api/static` 读这个文件，开局警告和右栏里显示"对照局：一致 / 不一致 / 未对照"。
4. 可选：阶段跳缓存、小地图。
