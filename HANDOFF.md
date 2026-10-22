# 交接

## 当前目标

**单位验证**（用户 2026-10-22："关卡设计可以先往后放，我们先把单位验证做完"）。用户定的大顺序：战役设定 → 粗模玩法验证 → 关卡 → 美术最后。剧情大纲 [docs/story/outline.md](docs/story/outline.md)（v5），单位方案和**验证进度表** [docs/story/units.md](docs/story/units.md) 开头，验证顺序在 [docs/plan.md](docs/plan.md)「进度」一段。

**恢复时先做**（2026-10-22 收工时）：
1. **单独**检查红警3有没有在运行（Steam 那份 `RA3_1.13.game`，用户可能在玩）。在运行就停下问，不编图、不用测试台。2026-10-22 收工时用户正开着游戏。
2. （磁暴坦克 2026-10-22 已做完，见 units.md 验证进度表。）
3. 按 plan.md 的顺序接着做：冰幕工兵 → 协调器干扰车 → 式神护卫 → 纸鹤侦察机 → 装甲列车（脚本车），心灵巫女最后（要和"克隆体控制我方单位"一起设计）。可借的原版写法见 `work/story/unit_roster.md` 第 4 节（本地文件）。遗留：阻塞气球车低空 / 高空区分、自由号炮塔不开火。
4. 每个新单位照钻地运兵车的样子写：`units/<名>.py`（公开 abilities）+ `missions/<名>_bench.py`（按地点放、公开 cast / marks）+ `checks/<名>.py`（计数器 + 期望），在 `build.py` 的 MISSIONS 里登记；先 `cnv_show` 看接口，再 `cnv_check`。必要时用 A/B 对照（同图两个、一个用技能一个不用）和不放技能的对照检查。

**已做完的单位**（2026-10-22，结果都在 units.md 验证进度表）：钻地运兵车、超时空信标兵、合体机甲（原版 Combine 模块不能用，改成乘员舱）、磁暴坦克（原版电涌不放电，补了磁暴步兵的 FireWeaponUpdate）。之前的：时滞炮车、阻塞气球车、烟花兵、自由号 v2（旧编图脚本 `make_campnew35~38.py`）。

**工具现状**：测试首选 MCP `cnv_check(name, check)`（编图 + 进关 + 读计数器 + 判定，一次调用）；`cnv_show(name, check)` 看各层公开的接口和接口检查（不编图）；`cnv_list` 列出所有构建。各层只走接口（0f），关卡卡片 [docs/story/levels.md](docs/story/levels.md) 由测试和代码对齐（0g）。本会话改过的 `bench_mcp.py`（截帧掉线提示 BENCH DROPOUT、条件满足后照跑不带条件的观察）要 MCP 服务重启（新会话）才生效。

**往后放的**（用户 2026-10-22 说不急）：
1. A7 / A8 难度。A7 按现在的数值，玩家不动手，4 辆多功能车也会在自由号第一次跳过来约 35 秒后把它打下来（plan.md A7 行）。A8 两边都太容易。按 units.md 5.6 第 3、7 条让敌人反击、盯着自由号打，再用 `a8 --check assault` / `a8_control --check assault` 对照。要用户定"难到什么程度"。
2. 超时空甲板落到自家建筑上会弄死被传的车（`Telefrag="INSTANT_DEATH_TELEPORTER_ONLY"`）。改不改成 `NONE` / `SWAP`，等用户定。
3. 合体机甲合体后加强什么（现在只是占位）。

其余旧项：
1. 自由号 v2 的细节（甲板跃迁、甲板工厂做通；可拆炮塔不开火）见 plan.md 自由号那行。
2. 甲板乘员叠在航母正中一个点：用户 2026-10-21 定**先接受叠放**，以后再做（候选：TransportContain 的 PassengerData BonePrefix，要给航母模型加甲板骨骼）。
3. 大纲第六节"待用户决定"里还没定的：三个结局、三条背叛、关卡地点和关名。

**这两天测试台上反复踩的坑**（写新单位时先查）：
- **视野**：单位只打自己视野里的目标，友军视野不算，关掉 CheckVisionRange 也没用。射程比视野远时，炮塔会转过去但永远不开火，也不靠近。时滞炮车（守护者视野 200）和自由号（基洛夫视野 150）都栽在这里。
- **步兵的"不能动"**：用 IMMOBILE_ALLOW_ROTATE，不用 IMMOBILE（步兵要转身瞄准，IMMOBILE 下一发都不打）。
- **追击**：AIUpdate 的 StandGround / StopChaseDistance 都拦不住单位追飞机，要守点就做"展开 / 架设"切换（守护者目标指示的整套切换搬过来就能用，ToggleState 里必须带 SkirmishAiInfo）。
- **复制原版单位**：同一个文件里继承它的变体（坦克杀手的伏击版、牛蛙的 _Ground 版）要一起删掉，否则编图失败。
- **飞机**：框选要点它悬停的屏幕位置（比地面点高约 170 像素）；要它回航得有机场，否则一直在目标上空盘旋。
- **测试台截图**：`--shots 10` 是"第 10 秒拍一张"，要多张写成 `--shots 1,3,5,...`。
- **复制哪个当底**：SDK 示例 mod 的先兆炮艇机复制后从不开火，招牌飞行单位用基洛夫当底；基洛夫文件里 CheckVisionRange 出现两次，改视野时两处都要看。
- **超时空**：自己写的 SpecialPowerTemplate 必须带 ObjectFilter，否则什么都传不走；超时空传送不带飞机，航母自己要用 TeleportSpecialAbilityUpdate 自跳；落点压到建筑会互相撞毁。
- **SpawnBehavior**：只能刷原版单位，或者地图上也摆了一个的自制单位（否则模板不加载、刷不出来）；刷出的单位叠在一个点。单位身上的生产队列侧栏不认，要"甲板工厂"就用自动刷。
- **任务脚本计时器**：SET_MILLISECOND_TIMER 到点后一直算"已到期"，交替触发的脚本每次都要把自己的计时器重新推远，否则每帧都触发。AI 不会自己按跃迁之类的技能，用 NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT 由脚本按。
- **攻击移动不打建筑**：`ATTACK_MOVE_TEAM_TO` 只打路上的单位，到了路点就停；要拆建筑得 `TEAM_ATTACK_NAMED` 点名（A8 对照第一轮因此打了 290 秒一座平台都没拆）。
- **超时空甲板落点挨着自家建筑**：被传的车落到建筑上会被弄死（Telefrag），自家的也一样（liberty jump 少一辆守护者就是这个）。
- **测试台开始计时的那一刻，任务已经跑了多久，每次不一样**（2026-10-22，信标兵）：差几秒。有一次第 5 秒的脚本动作在测试台第 1 帧之前就做完了。脚本里第一个动作放到第 10 秒以后，或者用条件触发。
- **脚本放技能不受距离上限限制**：`NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT` 不管 `MaxCastRange` / `LIMIT_DISTANCE`，玩家手点才受限。要测距离，只能手动选中单位再放技能（`bench_click` + `bench_ability`），而且目标点要在画面内（`bench_ability` 不会替你挪镜头）。
- **让载具能装载具**（合体机甲，2026-10-22）：
  - 载具默认占 5 个座位（BaseVehicle `TransportSlotCount="5"`），座位上限要写 5。
  - KindOf 要有 `TRANSPORT`。
  - `ConditionForEntry="INVALID"` 照双刃直升机写。
  - CONTAINER_OCCUPIED 要用 `ObjectStatusWhileContaining` 写出来，不会自动加。
  - 少一样都上不去车，脚本（`NAMED_GARRISON_SPECIFIC_BUILDING`）和手动右键都一样。
  - C&C3 留下的 Combine 模块不能用：缺骨骼会崩溃，有骨骼也不对接。
- **运兵车的计数三个坑**（钻地运兵车，2026-10-22）：
  - 按模板数"区域里有几个"时，车里的乘客也算在车所在的区域里。数"车上还有几个"用状态 `ENCLOSED`。
  - `NAMED_EXIT_BUILDING` 不会让运兵车卸兵。用单位指令集里的 `Command_Evacuate`（`NAMED_USE_COMMANDBUTTON_ABILITY`）。
  - 单位死后，血量计数器停在最后一次读数，不会归零。
- **跃迁后，按模板数的区域计数不会把它减掉**：`PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA` 在它离开的区域里还算着它（A7 自由号跳走后 35 秒不变），到达的区域则马上算进去。要知道跃迁单位在哪，用 `counted(named=..., area=...)`（`NAMED_INSIDE_AREA` / `NAMED_OUTSIDE_AREA`）。
- **落点 / 突击点**：别放在对方建筑上（A7 第一次把突击点放在我方战车工厂上，跳来的自由号压在工厂上、防空车够不着）。
- **mod 名最多 15 个字符**：同一份内容，叫 CampLibRidersJump / CampBisjcdXXXXXXX（17 个字符）时游戏在主菜单前就崩（退出码 0xC000000D，日志里什么都没有）；叫 CampBisjcd、CampBisjcdXXXX（14）、CampLibertyJump（15）都正常。`experimental/cnv/parts.assemble` 超长直接报错，`tests/test_cnv_parts.py` 检查所有登记的编图名。
- **检查游戏在不在跑**：进程名要同时匹配 `ra3_1.xx.game`、`RA3.exe` 和起义时刻的 `ra3ep1`（之前漏了起义时刻）。
- **截图隐私**：给启动器之类的窗口截图只用 PrintWindow 截那个窗口，别用 CopyFromScreen 截整屏（会截到用户的其他窗口）。
- **弹窗自动点击**：测试台的弹窗钩子只点一次、不能 `continue` 循环（曾经在 Tacitus 窗口上空转约 15 分钟），卡住就让 150 秒超时生效。

用户 2026-10-20 的写作要求（也在记忆里）：剧情为玩法服务、黑色幽默和刻板印象只调味、剧情本身要正经；新单位逐关解锁；地图只求神似、按玩法设计（realmap 照搬真实地形效果不好）；不给真人演员角色写新台词新镜头；不用中国、朝鲜半岛地点，不拿真实悲剧开玩笑。

## 下一步

0. **测试台改用 MCP（2026-10-21 晚起）**：仓库根 `.mcp.json` 注册了 `ra3bench`（`experimental/testbench/bench_mcp.py`，核心在 `harness.py`，Python 用 `../envs/bench_mcp`：mcp 2.x + Pillow + NumPy + pycaw）。新会话第一次要批准这个项目 MCP。用法：`bench_start(mod)` 自己走菜单进关（约 40 秒），之后用世界坐标 `bench_click / bench_box / bench_ability / bench_camera`，`bench_wait` 推进，`bench_look` 看，`bench_inspect` 放大任意存档帧，`bench_caption` 读任务脚本在字幕里报的信号，`bench_stop` 收尾放锁。默认 hold 模式：任务菜单（Esc）暂停游戏，只有工具在动作或等待时游戏才走（实测思考 5 秒游戏时间不变）。帧全尺寸存在 `work/testbench/runs/<mod>_mcp_<时间>/`（index.json 记每帧的任务秒数和镜头）。暂停菜单模板 `work/testbench/nav/pause_menu.png`（work 不进 git，丢了要从一帧任务菜单画面重切：`harness.MENU_BOX`）。旧的 `cnv.py bench`（run_bench.ps1 开环时间线）还在，批量回归可以继续用。思路来源：VISTA（arXiv 2610.02200）的机械控制器 + 无损帧存档 + 按需细看。
0b. **少操作、少截图的测法**（2026-10-21 夜）：
   - **让任务脚本自己动手**：`make_campnew38.py` 的 `CNV_TEST=jump` 由脚本在第 `CNV_JUMP_AT`（默认 15）秒用 `NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT` 让航母跳到 `CNV_JUMP_TO`，测试时一次点击都不用。
   - **让任务脚本报数**：用 `DISPLAY_COUNTER` 把要检查的数显示在左下角（`harness.COUNTER_BOX`），每帧更新。例子：`SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER` 数存活单位；`PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS` 按状态数单位，比较符 2 是"等于"，状态参数写成 `(序号, 0.0, 名字)`，序号按 ObjectStatus.xsd 的顺序从 0 数（ATTACHED = 102）。
   - **MCP 新工具**：
     - `bench_watch(seconds, every, box)`：一次调用跑一段时间、定时存帧。返回每帧的变化量（水面和待机动画本身约 8）、字幕有没有变（超过 20），最多再加一张拼图。
     - `bench_strip()`：把多帧里的同一块区域（默认计数器）拼成一条，只读存档、不碰游戏。
     - `bench_start(look=false)`：开局不截图。
   - **飞行单位画在地面点上方约 170 像素**：框飞行单位时，`bench_watch` 要传 `air=true`。
   - 一次完整测试的流程：start → watch（sheet=false）→ `bench_counters`，只返回文字，一张图都不用看。
   - **计数器认数字**：`experimental/testbench/counters.py`。计数器从左下角 y=578 往下排、每行 16 像素，只放得下 4 行（第 5 行被底栏挡住）。数字模板在 `work/testbench/nav/digits/`（work 不进 git，丢了就重跑 `cnv.py make digits --calibrate`：地图显示 1234 / 5678 / 90，切出 0～9）。MCP 工具 `bench_counters(lines)` 把每帧的计数器读成"s19: 6 5"。
   - 任务提前结束（输了 / 赢了）时，`bench_watch` 停不住游戏也会带着已存的帧返回，计数器随任务一起消失；判"任务结束"用 0c 的 ENDED。
0c. **解耦后的组装命令**（2026-10-21 深夜，用户定"先接受叠放，先做解耦，效率改进也做"）：
   - 结构 `experimental/cnv/`，旧的 42 个 `make_camp*.py` 不动：
     - `units/`：单位 = 参数 → `Unit`（XML 文本 + 编图要知道的东西），`tag=` 给所有自有 id 加后缀，两个变体能摆在同一张图上。
     - `maps/`：地形和开局点（`island.py` 就是 CampNew18 的岛）。
     - `missions/`：摆放 + 任务脚本 + 字符串 + 目标（`a8.py`、`liberty_bench.py`）。
     - `checks/`：检查 = 附加的脚本（让任务自己按技能）+ 计数器 + 测试台步骤 + 期望值。
     - `parts.py`：声明的数据结构和 `assemble()`，走原来的 CampNew7 流水线（lint 照跑）。
     - `build.py`：一条命令编图、跑测试台、按计数器判 PASS / FAIL，失败时退出码 1。
   - 命令：
     - `cnv.py make list`：列出能编的图和检查。
     - `cnv.py make a8`：编 A8 本身。2026-10-21 深夜经用户同意已覆盖装着的 CampA8（新版是原版战车工厂，造不了 CNV 轻坦）。
     - `cnv.py make a8 --check jump|lose`、`cnv.py make liberty_riders --check jump`、`cnv.py make liberty_ride_ab`（同图 A/B）。
     - `--no-build`：只跑测试台，用已经编好的图。
   - 2026-10-21 测试台结果，全部零点击：
     - A8 jump PASS：自由号 1，守护者 6。
     - A8 lose PASS：自由号第 5 秒被击落，任务结束。
     - liberty_riders jump PASS：跃迁前后都是存活 6、在甲板 5，和旧图一致。
     - liberty jump PASS：不带乘员。第 14 秒乘员从 6 变成 5，少了一辆守护者，原因没查（可能是跃迁落点撞毁）。
     - liberty_ride_ab：A（粘在航母上）6 / 6，B（不粘）6 / 5，跃迁前后都不变。这个只是对照，不判对错。
   - 期望值写法：
     - `(标签, 从第几秒起, 比较符, 值)`：从那一秒起每帧都要满足。
     - 比较符写成 `ever==` 之类：至少有一帧满足就算。
     - 标签写 `ENDED`：计数器先出现、后来全没了，就算任务已经结束。
     - 可加第 5 项"到第几秒为止"：`(标签, 起, 比较符, 值, 止)`，比如"跃迁前落点里是 0"。任务计时器比测试台的秒数早约 1 秒（测试台从看到关卡画面才开始数），写截止时间时留 `checks/liberty.EARLY`（2 秒）余量。
0d. **触发区域 + MCP 一次调用测完**（2026-10-21 深夜，用户："地图生成器写触发区域，完善 MCP 工具，尽可能让大模型直接和 MCP 交流，避免直接操作"）：
   - **触发区域**：`mapscript.MapFile.trigger_areas()` / `set_trigger_areas({名: [(x, y), ...]})`（格式见那里的注释，按原版地图核对过）。任务和检查写 `t.areas['名'] = parts.square(x, y, 半边长)`；`parts.counted(..., template=..., area='名')` 用 `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA` 数区域里我方某种单位有几辆。底图（海德堡）原有的区域随它的脚本一起被替换掉；脚本里引用了没声明的区域，`assemble` 编图前就报错。`maprender` 会画出区域（青色框）。
   - **MCP 新工具**（`bench_mcp.py`）：
     - `cnv_list()`：列出所有任务、检查、计数器和期望值。
     - `cnv_check(name, check)`：编图 → 进关 → 看 → 读计数器 → 判 PASS / FAIL，一次调用全做完，返回文字，不点击、不看图。编图在单独进程里跑（每次都用最新代码）。`build=false` 用已编好的图，`keep=true` 留着游戏好接着查。
     - `cnv_map(mod, x, y, r)`：不开游戏看编好的地图俯视图（摆放、路点、触发区域）。
   - 本机已在 `.claude/settings.local.json` 批准 ra3bench（不进 git），**下个会话开始就能直接调这些工具**；没加载 MCP 时，用 `bench_client.py '[["cnv_check", {"name": "a8", "check": "jump"}]]'` 走同一条 MCP 路径。
   - `build.py` 给 MCP 用的两个模式：`--plan`（编图后打印测试台步骤）、`--judge "<计数器文字>"`（离线判定，改了期望值不用重跑游戏）。
   - 计数器读数修了一个 bug：数字右边地面上 1 个像素的亮点被当成一组字，0 读成了 8（`counters.MIN_HEIGHT`）。
   - 2026-10-21 深夜三个检查全部走 MCP 的 `cnv_check` 跑，都 PASS：
     - A8 jump：守护者到平台，第 1 秒 0 辆，第 6 秒起 6 辆。**守护者确实跟着跳到了平台边**，之前证明不了的这一点现在证明了。
     - liberty_riders jump：落点里跃迁前 0 辆、跃迁后 5 辆，在甲板 5、存活 6。
     - liberty jump：落点里跃迁后 4 辆；存活在跃迁那一刻从 6 变 5（老问题，候选 3）。
   - 已知缺口：
     - 按类别数（`parts.counted(kind=parts.kindof('VEHICLE'), area=...)`，0e 接上了）会多算：A8 对照里 12 辆车读成 20、敌方 9 辆读成 12，大概是多功能车、牛蛙带着附属对象；探针图 `cnv.py make kinds`（3 辆守护者 + 2 座建筑）四种数法都对。对照、判定用按型号数。
     - `cnv_check` 一次约 2～3 分钟，MCP 客户端要等这么久（Claude Code 默认不会超时）。
0e. **A8 难度对照、MCP 第二轮改进、少一辆守护者**（2026-10-21 深夜）：
   - **难度对照** `a8 --check assault` / `a8_control --check assault`（同一套脚本，两边都 PASS）：每 8 秒全队攻向第一座还在的平台，平台周围区域里没有铁锤了就改成点名攻击平台；有自由号时冷却一好就跃迁过去。去掉了任务自己的输赢脚本，计数器一直在。结果：有自由号第 60 秒三座全灭，丢 1 辆守护者，自由号活着；没自由号第 82 秒，12 辆里丢 4 辆（守护者 1、多功能车 3）。符合 5.6"有招牌不能无伤、没招牌能打但更难"，但两边都太容易，见候选 1。
   - **第一轮对照两边都 FAIL，是测试脚本的错**：攻击移动只打单位、不打建筑，护卫死光后全队停在路点发呆（看了相机对准平台 1 的那几帧才看出来）。坑已记在下面。
   - **MCP 改进**：
     - `bench_watch(lines=n, until='c1==0')`：每帧读计数器，条件满足就提前停；`cnv_check` 随后跳过剩下的等待。这次两个对照分别 60、82 秒停，不用等满 290 秒。
     - `cnv_check` 的返回只留一遍计数器，相同读数合并（`s18-s50: 2 4 6 1`），菜单日志、逐帧行都省掉：两个检查一共约 3 KB，以前一个就约 9 KB。完整逐帧行仍在 `bench_watch` 自己的返回和帧存档里。
     - 检查可以先 `bench_camera` 把镜头对准要看的地方：数字说不通时，翻一帧就知道发生了什么。
     - 修了一个隐患：`a8_control` 原来也叫 CampA8，一编就会覆盖正式 A8，现在叫 CampA8C。
   - **liberty jump 少一辆守护者的原因**：落点 (1480, 2315) 紧挨我方电站 (1550, 2360)。航母东边 60 那辆被传过去正好压在电站上，超时空的 Telefrag 把它弄死了。对照 `liberty --check open`（落点往南挪 165，离电站 210 以上，其余不变）：6 辆全活、5 辆到落点，坐实。带乘员的版本不丢，是因为乘员挂在航母上，不单独传送。
0f. **地图 / 单位 / 关卡 / 检查之间只走接口**（2026-10-22，用户："先把关卡设计，单位设计，地图设计解耦"、"让整个流程尽可能变成接口对接口的对话，不进行直接操作"）：
   - 每层只公开给下一层用的东西（`experimental/cnv/parts.py` 开头）：
     - **地图**公开 `SITES`（命名地点：坐标、范围、用途，如 `west shore`、`east 1`）和 `PLAYERS` / `TEAMS`。
     - **单位**公开 `abilities`（如 `jump` → 特殊能力 id）、`what`（一句话用途）、`params`（造它用的选项）。
     - **关卡**用 `m.put(模板, 地点, dx, dy, role=...)` 按地点放东西，公开 `cast`（谁演哪个角色、站在哪个地点）和 `endings`（输赢脚本）。
     - **检查**只问关卡：`m.role('carrier').name`、`m.ability('carrier', 'jump')`、`m.site(...)`、`m.roles('platform')`、`m.player('s1')`、`m.drop_endings()`；不再 import 关卡模块的常量，也不写自己的坐标。
   - **接口检查** `parts.contract()`：编图前查一遍，`assemble` 有问题就停。查的是：物体有没有按地图地点放；脚本参数里的物体名、路点、触发区域、队伍、玩家、字符串、特殊能力、模板有没有人公开过；点名放技能的那个物体，它的单位有没有公开这个技能。`tests/test_cnv_parts.py` 有正反例。
   - **看接口**：`build.py <名> [--check <检查>] --show`，以及 MCP 的 `cnv_show(name, check)`。不编图，把地图地点、单位能力、关卡角色表、检查的计数和期望、接口检查结果打成文字。写新关卡、新检查之前先看一眼，写完再看一眼。`cnv_show` 是新工具，MCP 服务进程重启（新会话）后才有。
   - **验证**：14 个构建改造前后逐项比对全部一致，每个构建 contract ok。测试台上截帧掉线时，`cnv_check` 会加一行 `BENCH DROPOUT`，提示用 `build=false` 重跑（第一次 a8 jump 就是这样，重跑 PASS）。
0g. **A7 迁入、设计文档改成接口形式**（2026-10-22，用户："把 A7 搬进来，设计文档也改"）：
   - **A7**：`missions/a7.py` + `checks/a7.py`（`jumps` / `power` / `win` 在测试台全过，发现见 plan.md A7 行）。和 A8 同一张岛图，只给地图加了 `base edge`、`east field` 两个地点，旧构建快照仍一致。关卡另外公开路点 `marks` 和时间 `facts`，检查用 `m.point` / `m.facts` 取。
   - **设计文档**：[docs/story/levels.md](docs/story/levels.md) 每个关卡一张卡片，只用代码公开的名字写意图。`tests/test_level_cards.py` 保证卡片和代码一致，做过 8 种变异检验。
0a. **编图前自动静态检查**：`experimental/campaign/lint.py`，每次编图在编译前跑（`make_campnew7.compile_map`），有 ERROR 就停（`CNV_LINT=warn` 只打印）。规则对应下面"踩过的坑"：视野和射程（超过 1.5 倍只警告）、步兵 IMMOBILE、超时空模板缺 ObjectFilter、ToggleState 缺 SkirmishAiInfo、复制件里留着原版 id、SpawnBehavior 刷的自制模板没摆在地图上。`python -I -X utf8 experimental/campaign/lint.py` 单独查全部单位文件；`tests/test_lint.py` 每条规则一个正反例。新坑出现时先加一条规则和测试。
1. 日常操作先用根目录的 `cnv.py`（`python -I -X utf8 cnv.py -h`）：build / map / bench / sheet / where / launcher / status，不再临时写脚本。新测试一律用 `run_bench.ps1 -Nav`（`cnv.py bench` 就是它）：时间从进入关卡算起，点击位置用 `experimental/testbench/calib.py` 的 `world_to_screen` 从世界坐标算（标定只对从 CampNew18 岛派生、开局镜头相同的地图有效；换了开局镜头要重新标定：`CNV_CALIB=base/grid` 各编一次、各跑一次，再 `calib.py fit`）。要看镜头外的地方：左键点 `calib.world_to_minimap(x, y)` 移镜头，再用 `calib.world_to_screen_at(x, y, 镜头中心)` 算点击位置；要打人就右键点敌人本身，右键点小地图只是移动。
1b. 给用户自己试玩用的图形启动器：根目录 `launcher.pyw`（桌面快捷方式"红警3 测试启动器"，2026-10-21）。它列出 Mods 里所有编好的 mod，按"关卡 / 单位测试图 / 其他"分组，双击就启动，游戏在运行时拒绝启动。新关卡或新单位测试图要在 `launcher.pyw` 的 KNOWN 里加一行中文说明，否则会落进"其他"组。
1a. **2026-10-21 晚起测试台副本不加载 Tacitus**：Tacitus 出了 1.1.1，又在每次启动时弹更新窗口，Steam 目录里的也还是 1.1.0、没有新版可抄，就把副本的 `Data\dsound.dll` 改名成 `dsound.dll.tacitus110.off`（测试台不联网，用不着它；改回原名即恢复）。没有 Tacitus 时游戏会弹"连接中断通知"并退回主菜单：`nav.py` 的 POPUPS 认得它、点确定，`run_bench.ps1` 随后从第 0 步重新走菜单（约第 29 秒进关）。以下是旧情况：测试台的游戏副本 `work/testbench/RA3` 里也有 Tacitus（C&C:Online 的游戏补丁，`Data\dsound.dll`）。它的版本落后于新版时，每次启动都弹更新窗口，挡住菜单；而且它是 ImGui 窗口，测试台发的点击点不到。办法：把 Steam 游戏目录里更新过的 `Data\dsound.dll` 复制到测试台副本（2026-10-20 已换成 1.1.0，旧的留作 `dsound.dll.tacitus100.bak`）。`nav.py` 的 POPUPS 只能识别出这个窗口，点不掉它。卡在菜单时，看 `shots/nav_last.png` 就知道卡在哪个画面。
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
