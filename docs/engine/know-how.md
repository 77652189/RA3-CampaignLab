# 引擎与工具的认识

对红警 3 引擎、SDK、地图格式和测试工具的认识：做过什么、怎么用、踩过什么坑。认识变了就改这里（触发条件：我们对引擎或工具的认识变了）；进度和待办不在这里，在 [plan.md](../plan.md)。脚本引擎的运行语义另见 [script-semantics.md](script-semantics.md)。

下面三节 2026-10-28 从 plan.md 原样搬来，编号（0～0h 等）不变；文中的 work/ 路径指本仓库的 work/。

## 已完成能力与经验（原 RA3-ChineseVoice/HANDOFF.md「战役扩展与测试台」一节，2026-10-18 迁入；文中 work/ 路径指本仓库的 work/）

- 测试台 `experimental/testbench/`：`make_bench.ps1` 建 Steam 目录的硬链接副本（`work/testbench/RA3`，游戏会写的小文件复制；不能往硬链接文件里写），`capture_shim.cpp` 截帧 / 钩输入 / 挡前台，`run_bench.ps1 -Mod -Clicks -Keys -Shots` 后台全自动跑（Esc 能跳过场：先发激活消息）。到关卡约 70 秒。菜单坐标见脚本调用示例和记忆。
- 已证实（全部在测试台上看到）：改原版关卡、新增关卡和改关卡数（`splice_assets.py`，新实例要放进最上层 static.12 及 _l/_m.12）、新地图文件夹（`mapcache.py` 往原版地图清单追加登记，否则加载即崩；文件夹要带编译好的 map.* 流，否则缺地形贴图和建筑）、中文新字符串（mod 里放 `gamestrings.csf`；`mod.str` 按 Latin-1 读）。最小完整新关卡：`make_campnew4.py`。
- 自研地图工具 `mapscript.py`：27 张原版战役地图逐字节往返，脚本导出成可读文本，改字符串参数；`make_campnew5.py` 把开局通话换成 S01TH01，游戏里生效。写回 .map 时 EAR 后的大小必须是解压后的块文件大小，否则加载卡在约 60%。
- 走不通的：SDK 编的 `data\additionalmaps\mapmetadata_mod` 流（军械库的做法）启动约 3 秒就崩，原因未明；SDK 的 AllTypesHash（177706643）和 1.12（1424942948）不同。
- 测试台默认把游戏窗口挪到屏幕外、只静音测试进程自己的音频会话（`-Visible` / `-Sound` 关掉），游戏自己的 "Game crash" 弹窗会被识别并结束本次运行。
- 脚本编辑器（`mapscript.py`）：按原版 379 种条件 / 动作的目录（`script_catalog.json`）新建条件和动作、新建脚本、增删脚本和其中的条件 / 动作、读写任务目标；`make_campnew6.py` 新增两条脚本弹出中文提示、删掉一段通话、改目标名，游戏里都生效。
- 自己编 map.* 流（`mapxml.py` + `make_campnew7.py`）：从 .map 生成 map.xml（物体包含、GameMap、环境数据），BAB 只编 GameMap，其余实例按引用从 worldbuilder 流和原地图各层里取最新一层"链接"进来。**SDK 必须用 v3.0（`C:\RA3ModSDK3`）**：旧的 `C:\RA3ModSDK` 是 1.10 时代的，编出的 GameObject 是旧布局，能加载能显示（CampNew12 那次只是单位没活动），单位一开始运作就写坏堆内存、加载约 3 秒后崩（崩在分配器 RA3_1.13.game+0x607873，SDK 编的原样守护者 2/2 崩）；v3 编的同一单位 3/3 正常，链接器"旧布局"清单为空。构建脚本默认已切到 v3（`CNV_SDK` 可改）。SDK 对模型的泛型引用仍要改到同名 W3DContainer（链接器已做）；默认仍优先用原版 1.12 数据。坑：大小为 0 的补丁条目也会更新类型哈希（用旧哈希会弹 "Type hash mismatch"）；缺 EnvironmentData 时整个画面变洋红。地形图集 SDK 里没有源贴图，只能沿用原版地图的。
- 新单位 + 往地图里摆新物体（`make_campnew13.py`）：SDK 写的新模板 CNV_TestShip（水翼船逻辑 + 航母模型 + 10 倍血量 + 中文名），`mapxml.place_object` 照着 Hydrofoil 01 摆进 .map，`mapscript.duplicate_contents` 把它的 7 条脚本动作复制给新单位，测试台上它跟着船队开进地图（work/testbench/new_unit_campnew13.png）。链接器会从 BAB 输出里补上原版流没有的新资产。
- 改地形（`mapterrain.py` + `make_campnew14.py`）：HeightMapData = 560×560 格、每格 10 单位、高度值 ÷16、边框 30 格；在船队停泊点旁抬起一座岛，游戏里出现。`mapterrain.Tiles` 读写 BlendTileData 的贴图格（公式对上原版 36228 块草地），岛顶刷草、水线刷沙，游戏里显示（work/testbench/terrain_island_painted.png）；贴图过渡：混合描述表（每条 18 字节）已解析，方向含义用原版数据统计得出（`Tiles.SIDES`），`Tiles.autoblend` 自动给边缘加过渡，草地边缘变柔和（work/testbench/blend_cmp.png），27 张图 BlendTileData 逐字节往返。注意：按 ÷16 换算，水面实际在约 285 而不是水域里写的 200，原因未明，按实测用。
- 汇总演示 `make_campnew15.py`：新任务 + 自写脚本 + 新单位 + 新岛（贴图 + 混合）+ crisp 光照，测试台正常（work/testbench/showcase_campnew15.png）。
- 从零做单位：`make_campnew16.py` 把 SDK 示例单位（起义时刻的先驱者直升机，全套新模型/骨骼/动画/贴图）编进关卡，游戏里正常飞行（缺起义时刻音效，只是没声音）。`w3x.py` 从几何数据写 W3X（层级 + 网格 + ObjectsAllied 着色器 + 容器；Pivot 必须带 FixupMatrix），`make_campnew17.py` 用程序生成的飞碟模型和代码画的贴图（含阵营色带）做成新单位，游戏里正常显示（work/testbench/own_model_campnew17.png）。**单击选中靠模型容器里的碰撞盒**（`W3DCollisionBox` 子对象，原版炮艇有 5 个 OBBOX）：没有它单位能框选、单击选不中（用户 2026-10-18 在 CNV03 实测游隼和收缩射线车都这样；测试台单击原版守护者 / 冷冻直升机能选中、自制的两辆选不中）。`w3x.rig_model` 现在给每个模型加一个包住全部部件的碰撞盒，重编 CampNew30 后测试台单击全部能选中、用户 2026-10-19 进游戏确认能选中（`tests/test_w3x.py` 守住）；CampNew29 及更早的关卡没重编，仍是旧模型。换成 Blender / AI 生成的网格只是换输入；骨骼动画还没做。
- 从零生成地图（`newmap.py` + `make_campnew18.py`）：只借用海德堡 .map 当容器（尺寸、块结构、34 种地面贴图/图集、玩家与队伍），地形（噪声岛屿）、整片海面、地面贴图与全图自动过渡、不可通行位图、物体与路点、脚本、目标、时段、雷达/预览图全部生成；游戏里正常（work/testbench/generated_map_campnew18.png）。BlendTileData 四个数组之后是 8 个位图 + 每格 1 字节数组（长度 = 高 ×（宽 + 宽按 8 取整），27 张图都对）；位图 0 = 陡坡不可通行。水面高度推测：真实高度 = 高度值 × 0.04375（200 ↔ 实测 285.7）。但寻路按更高的水面算：CampBridge1 的桥面在 285.7 以上 +40 时地面单位仍停在桥头，+100 才通行（realmap.DECK = 100，桥两头 5/格 的坡道）；+40 和 +100 之间的确切值未测，做浅滩、低桥前先测
- Mod SDK v3.0（1.12）获取：archive.org 存档 `http://web.archive.org/web/20120301135129id_/http://na.llnet.cnc3tv.ea.com/u/f/eagames/cnc3/cnc3tv/RedAlert/RedAlert3_ModSDK/RA3ModSDKv3.exe`（136752107 字节，sha256 ad7240f8…，无签名，不运行它）；按"名字\0路径\0版本\0十进制大小\0数据"切出内嵌的 data1.hdr/data1.cab/data2.cab，用自编的 unshield 1.6.2（MSVC，work/downloads/unshield_src）解包，按旧布局放到 C:\RA3ModSDK3（Tools→tools，XMLFiles→SageXML 并复制 Static/global/Audio.xml 到根，Builtmods 的 1.12 引用 manifest→BuiltMods，Art，Schemas），BinaryAssetBuilder.exe 的 CLR 标志（文件偏移 4120）01→03。v3 还带 Art/Terrain 744 张地形贴图源文件和 XMLFiles/EP1。
- 带骨骼和动画的自制单位（`make_campnew19.py`，守护者逻辑 + 我们生成的车体/炮塔/炮管/雷达分件模型 + 我们写的旋转动画）：v3 下 3/3 正常，炮塔被游戏驱动转向目标、雷达动画在转（work/testbench/tank_v3_frames.png）。之前把崩溃归到动画/帧数/绘制模块上的二分，全是旧 SDK 随机崩溃造成的误判；`make_campnew20/21.py` 是那轮排查留下的。
- 自制单位模型（2026-10-17）：Blender 5.2（Steam 版，`-b --factory-startup`，只用 CPU）跑 `experimental/units/cnv_lighttank.py`（v1）/ `cnv_lighttank2.py`（v2），bmesh 搭部件 + 倒角，烘焙底色（AO、面板缝、污渍、边缘高光）和阵营色遮罩，导出 parts.json；`units/to_w3x.py` 转 W3X，挂守护者的骨骼名和逻辑。坑：法线要用 `corner_normals`（否则黑斑）；UV 不翻 v；底色中位亮度要压到零售水平（~72，`level=`，原先 107–143 在游戏里发白）；青色灯像素进 SPM 绿通道当自发光。**路线已定（用户 2026-10-17）：AI 只画概念图（HunyuanDiT，`ai_lighttank.py concept`），模型照概念图手写几何。** AI 直接生成网格（Hunyuan3D-2，`ai_lighttank.py shape` + `ai_lighttank_blend.py` 体素重建 + 平滑 + 减面）形状对但表面软、细节丢，`make_campnew24.py` 对比后放弃。`make_campnew25.py` 是 v1/v2 并排，3/3 正常（work/testbench/compare25_level_closeup.png）。AI 环境在 work/downloads/ra3gen_env（torch cu128，transformers 5 要给 DINOv2 改键名，已在脚本里），权重在 work/downloads/hf，生成走 gpu_limit.json 限流。
- 自制单位能生产（`make_campnew26.py`，2026-10-17）：v2 = 游隼坦克（快速突击坦克，$800，10 秒，去掉守护者的 Upgrade_AlliedTech2 前置），从新加的 CNV_WarFactory（AlliedWarFactory 的副本，指令集 = 原版列表 + Command_ConstructCNV_LightTank2，不覆盖原版 AlliedWarFactoryCommandSet）生产，测试台点车辆页签 + 点按钮，扣钱、出厂、能选中，6 次运行正常（work/testbench/campnew26_built_strip.png、campnew26_portrait_zoom.png）。生产按钮 106×106、选中头像 101×76 都是 PackedTextureImage（贴图 + 裁切框），`units/button_icon.py` 从原版静态流里所有同类图片逐像素投票重建空底板，再叠 Blender 透明渲染（`cnv_lighttank.icon()`）。坑：游戏按名字查的资源（CommandSet、ButtonImage、SelectPortrait、指令集里的指令）不在引用链上，链接器要用 `make_campnew7.EXTRA_OWN` 按名字前缀强制带上；工厂默认朝向出口朝东，在测试台镜头里被侧栏挡住，转 180°。
- 游隼玩法（`make_campnew27.py`，2026-10-17，用户定位：冷冻直升机的协同单位）：高射速主炮（约 2.9 发/秒，每发 11），炮塔 900°/秒，速度 125，碾压被缩小载具（CrusherLevel 20，减速 20%），去掉目标指示，400 血。冰冻单位受 90000% 伤害，所以"优先打冰冻"靠射速 + 快速换目标实现（游戏不能按状态排目标优先级）。"规避近战"切换（用户提议，最小射程照雅典娜 / V4）：250 射程、最小射程 100 的主炮 + 速度 115% + 视野 135%；RA3 没有给玩家单位的"保持距离"AI。按钮界面单独一个文件用 type="all" 引入（`map_xml(also=)` / `make_campnew7.EXTRA_ALL`），因为没人引用 UnitAbilityButtonTemplate，type="instance" 会把它丢掉。`make_campnew28.py` 是对战：测试台 `run_bench.ps1 -Actions`（click / rclick / drag 框选 / key，同一秒可多个）框选两辆游隼、开规避，它们在约 220 外（铁锤射程 150、视野 200 之外）打掉三辆铁锤、自己无伤；同样对局常规模式下两辆游隼被铁锤打掉（work/testbench/campnew28_battle.png）。没演示到：冷冻直升机冰冻（框选没选中它）、铁锤冲锋时的拉扯。**“开局往北开”已查清并修掉**：给炮塔加的“250 内看见被冰冻单位”（ObjectVisionRange）有两个坑——Range 是视野的百分比（写 250 = 250% = 500，于是去追 460 外的铁锤），而且它的 Filter 不检查 StatusBitFlags（Rule ANY / ALL 都一样，没冰冻的采矿车也被追着打；去掉这条就不追）。这条规则已删除，“优先打冰冻”只靠高射速 + 快速换目标；对照实验见 work/testbench/campnew28_miner_filter.png、campnew28_fixed.png。上面那场“220 外打掉铁锤”里游隼先自己开近了，正是这个 bug 造成的。
- 地形贴图图集自己编（`mapxml.atlas_xml` + `CNV_OWN_ATLAS=1`）：按地图贴图表逐种写 Tile（源文件从 SDK v3 `SageXML/Terrain/Terrain.xml` 查，TextureID = EA FastHash(小写贴图 id)，`sagehash.py` 调 EALA.Hash.dll，32 位宿主），BAB 编出的图集与原版同大小，替换海德堡图集后画面不变；`Tiles.add_texture` 往贴图表追加新贴图，`make_campnew22.py` 用海德堡没有的 Snow_Solvang01/02 做成雪岛，游戏里正常（work/testbench/snow_island_campnew22.png）。地面贴图从此可在 744 种里任选。
- 第四阵营入口（`make_campnew8/9/10.py`）：阵营菜单 APT 调 `%Campaign_SetFaction?FactionIndex=N`。N 不是 CampaignEnumerator 的位置；APT 常量表能安全改（在末尾追加字符串再改指针，对照组正常）；但同一条命令里串第二个调用、或在编号后面加字符，都会得到 "undefined" 简报然后崩溃。真正的第 4 个入口要改 APT 字节码（第 4 张卡片的点击事件里分两次调用 SetFaction 和 SetMission），或者改引擎；数据层面已经能把新章节挂在原版战役后面。
- 画质线索：Remix mod（B 站 BV1LJ4m1g7nT）的光照差异，对应 .map 里的 GlobalLighting / PostEffectsChunk。`make_campnew11.py` 把 GlobalLighting 的光源颜色调暖，测试台同一秒对比图明显变暖（work/testbench/light_cmp.png）：逐关重调光照可行。`maplight.py` 读写 GlobalLighting（4 个时段 × 3 盏灯，地图的时段编号选其一；末尾含阴影颜色）和 PostEffectsChunk（泛光、色彩查找表），27 张图逐字节往返；`make_lightmod.py <预设>` 只替换原版 .map 就能改**原版关卡**（盟军第 1 关实测），预设 vivid（白楼过曝，不用）/ subtle / crisp，对比图 work/testbench/light_a01_presets.png，待用户挑。crisp 套全部 27 关的光照包 LightAll：苏联第 1 关对比度更高，帝国第 1 关（夜间）几乎不变，均无异常（work/testbench/light_s01_j01_crisp.png）。`refpack_lz.py` 是真正的 RefPack 压缩器，地图压到 11–15%，`mapscript.map_file()` 已改用它（LightAll 154 MB → 19 MB，游戏里正常加载）。

## 测试工具与踩过的坑（2026-10-22 从 HANDOFF 原样迁入）

### 踩过的坑（写新单位时先查）

- **视野**：单位只打自己视野里的目标，友军视野不算，关掉 CheckVisionRange 也没用。射程比视野远时，炮塔会转过去但永远不开火，也不靠近。时滞炮车（守护者视野 200）和自由号（基洛夫视野 150）都栽在这里。
- **不会自己挑目标**（2026-10-22，自由号炮塔、装甲列车）：只有固定挂点武器（`WeaponSlotHardpoint`、没有炮塔位）的单位，AI 的 `UnitAITargetChooserData CanPickDynamicTargets` 不是 true 就一发不打。原版火车写的是 false；手写在 BaseObject 上的炮塔干脆没有这段。有炮塔位的不受影响（磁暴坦克写着 false 照样打）。lint 的 `chooser` 规则会警告。
- **按模板数"玩家有几个"数不到刷出来的单位**：SpawnBehavior 刷出的炮塔就在画面里，计数一直是 0。
- **步兵的"不能动"**：用 IMMOBILE_ALLOW_ROTATE，不用 IMMOBILE（步兵要转身瞄准，IMMOBILE 下一发都不打）。
- **追击**：AIUpdate 的 StandGround / StopChaseDistance 都拦不住单位追飞机，要守点就做"展开 / 架设"切换（守护者目标指示的整套切换搬过来就能用，ToggleState 里必须带 SkirmishAiInfo）。
- **复制原版单位**：同一个文件里继承它的变体（坦克杀手的伏击版、牛蛙的 _Ground 版）要一起删掉，否则编图失败。
- **飞机**：框选要点它悬停的屏幕位置（比地面点高约 170 像素）；要它回航得有机场，否则一直在目标上空盘旋。
- **测试台截图**：`--shots 10` 是"第 10 秒拍一张"，要多张写成 `--shots 1,3,5,...`。
- **复制哪个当底**：SDK 示例 mod 的先兆炮艇机复制后从不开火，招牌飞行单位用基洛夫当底；基洛夫文件里 CheckVisionRange 出现两次，改视野时两处都要看。
- **超时空**：自己写的 SpecialPowerTemplate 必须带 ObjectFilter，否则什么都传不走；超时空传送不带飞机，航母自己要用 TeleportSpecialAbilityUpdate 自跳；落点压到建筑会互相撞毁。
- **运行中才出现的自制物体**（刷出来的、造出来的）：旧编图脚本只编进地图上摆了的模板，没摆的刷不出来（生成表悄悄跳过，工程师造建筑直接崩游戏）。`experimental/cnv/parts.assemble` 从 2026-10-22 起把每个登记的单位都编进去并按名字链接，`ice_spawn --check built` 是它的回归检查；旧脚本仍要"地图上也摆一个"。SpawnBehavior 刷出的单位叠在一个点；单位身上的生产队列侧栏不认，要"甲板工厂"就用自动刷。
- **生成表刷物体**（冰幕工兵）：照原版纳米虫群罩子写，`CREATE_AT_TARGET`、`DO_NOT_TREAT_AS_STRUCTURE`，技能模块带 `AvailableAtStart="true"`。这三项是在链接问题查清之前加的，各自是否必需没有单独测过。
- **量时间让地图自己数**：每秒 `INCREMENT_COUNTER` 一次、到点就停（干扰车的行程秒数），不受截帧间隔影响。`bench_watch` 的 `until` 里计数器从 c1 数起，c0 会读到最后一行（测试 `test_every_until_names_a_counter_shown` 拦着）。
- **单位不会自己去打建筑**：守着不动的铁锤 44 秒没碰身边的冰墙，要用 `NAMED_ATTACK_NAMED` 点名。
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
- **心灵控制 / 换主人**（克隆体，2026-10-22）：
  - 能用的只有间谍收买 `DominateEnemySpecialPower` 的 `PermanentlyConvert="true"`：按下几秒内就换主人，克隆体死了也不还。`false` 什么都收不走；schema 里的 `TemporaryOwnerSpecialPower`（C&C3 留下的）会在 4 秒内弄死带着它的单位。
  - "克隆体活着才控制"靠关卡：每个克隆体站在自己的一方（底图 Heidelberg 自带闲着的 Soviet_2 到 Soviet_6，`maps/island.py` 的 `SPARE`），死了就用 `PLAYER_TRANSFER_OWNERSHIP_PLAYER` 把那一方的东西全还给玩家（`missions/clone_bench.release`）。只是换主人，血量和等级都在。
  - 只收被控的（心灵巫女）：克隆体用光环给自己这一方的单位挂一个闲置状态（`IS_BEING_HARVESTED`），巫女的收买过滤器写 `StatusBitFlags` 要这个状态——收买模块的过滤器认状态位。收买的实际范围比 `DominateRadius` 大：65 的克隆体收走了 110 外的巫女。
  - 换了主人以后，按模板数"玩家有几个"（`SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER`）要等收买的间谍死了才算进来。要问归谁，用 `counted(owner=...)`（`NAMED_OWNED_BY_PLAYER`）。
- **"没武器"的目标先查**：帝国矿车带机枪，苏联矿车会自己开动、碾死步兵（克隆体第一轮全死在矿车手里，看着像单位没刷出来）。要找打不还手的靶子，用工程师。
- **测试台的暂停会取消选位置**（冰幕工兵，2026-10-22）：`hold=true` 时每次工具调用之间按 Esc 暂停，正在选目标的技能（点了按钮、还没点地面）会被取消。要分几步做的手动操作（选中 → 按钮 → 点地面）用 `bench_start(hold=false)`。放建筑时，起点在红格（不能放的地方）就什么都不放。
- **造出来的建筑朝向和挡路**（A4 冰墙，2026-10-23）：
  - 工兵造的长条墙一律斜 45°（放置时默认的角度），脚本放技能和手点都一样。测试台发的拖动（窗口消息）转不动放置预览；横、竖两个按钮也做不了（每个单位只显示一个技能格）。
  - 生成表的 `ABSOLUTE_ANGLE` + `DispositionAngle` 不转建筑：要 0° 和要 90° 的长条墙都没挡住车（`ice_turns --check turns`），方块挡住了。要"怎么转都挡"就用方块（`icewall.wall(shape='square')`）。
  - 圆柱形碰撞体（`CYLINDER`）不挡路；加了 `PlacementShape`（小放置点）的方块也不挡，放置点好像顶替了寻路用的形状。
  - **游戏运行中出现的建筑（工兵造的、生成表刷的）不按碰撞尺寸挡步兵**：地图预先摆的长条墙把广场里的兵关了 37 秒，造出来的同样大小、甚至 400 见方的方块，兵马上从两边绕出来（`a4 --check placed` 对 `seal` 的旧版）。挡车还算管用。要靠墙关住步兵，就由关卡脚本判断"门口有墙"，让兵 `UNIT_GUARD_AREA` 守在里面（`missions/a4.py`）。
  - 生成表刷出来的建筑先有一段施工（脚手架），施工时不挡路。
- **两个同底的自制单位放进一个编图**：原版文件里的 `<Define>` 会重复定义，BinaryAssetBuilder 报 Critical 编不过；`icewall.engineer` 已把它改成带 id 的名字。
- **点名攻击才会追车**：伏兵用 `ATTACK_MOVE_NAMED_UNIT_TO` 往终点走，会和车队同速走在前面、一枪不开；用 `NAMED_ATTACK_NAMED` 点名打车（A4）。
- **任务目标状态 0 是"隐藏"**（2026-10-23）：0 隐藏、1 进行中（屏幕播报 + 暂停菜单列出）、2 完成、3 失败。我们以前开局设 0，目标一直看不见。用 `parts.Goal`，别手写状态。开着目标跑 hold 模式时，有一次第 9 秒左右按 Esc 没打开暂停菜单（报"Esc did not open the mission menu"），原因没查清；要看暂停菜单就用 `bench_start(hold=false)` + `bench_key(27)`。
- **地图有了矿，矿车会自己跑去采**（2026-10-23）：车队原来借盟军矿车，放矿以后开局就开去采矿，冲进了 1 号广场的伏击区。矿车还是两栖的，会直接从水道里开过去，不走桥。车队改用 `units/convoy.py`（矿车去掉采矿、两栖、展开）。要"没有武器、不乱跑"的车就用它。
- **坡道和悬崖上不能造建筑**（2026-10-23）：工兵在坡道中间造冰，什么都没造出来。要造建筑的地点标 `Site.build`，由 `platmap.lint` 离线检查。游戏里现造的建筑本来就不挡步兵；要真挡住出口，就由地图预先摆一道墙，横跨坡道口、两头搭在悬崖上（`festival` 的 `gate k`；A4 的冰造在门里平地 `inside k`）。
- **桥是两个物件**（原版，2026-10-23）：桥头标记位 16、桥尾 32，在物件列表里紧挨着，引擎按模板的 `BridgeBuilder` 在两点之间铺桥段。两头都要在同一层的陆地上（`platmap.bridge`）。用原版石桥 `HB_Bridge_02`，运输车能过（`a4 win`）。
- **计数器的内部名字只能用英文**（地图字符串按 latin-1 编码），中文只能放在显示的标签里。
- **mod 名最多 15 个字符**：同一份内容，叫 CampLibRidersJump / CampBisjcdXXXXXXX（17 个字符）时游戏在主菜单前就崩（退出码 0xC000000D，日志里什么都没有）；叫 CampBisjcd、CampBisjcdXXXX（14）、CampLibertyJump（15）都正常。音乐探针 MusicProbeRetail（16）也一样：启动约 1 秒崩，Windows 应用日志 1000 号事件指向 MSVCR80.dll；同一份数据改名 MusRetail 就正常（2026-10-25）。CampA7East_What（15 个字符，带下划线）2026-10-25 也崩过，原因还没查清；`experimental/rtx-remix/README.md` 早先记过"不含下划线"，稳妥起见名字只用字母和数字。`experimental/cnv/parts.assemble` 超长直接报错，`tests/test_cnv_parts.py` 检查所有登记的编图名。
- **游戏以为自己在后台时不放音乐**（2026-10-25，音乐探针）：界面音效照常，音乐完全没有；同一个 mod 有时出声有时不出声，就是这个原因。录音期间每 2 秒给游戏窗口发激活消息（WM_ACTIVATEAPP / WM_ACTIVATE / WM_SETFOCUS，和 `run_bench.ps1` 发按键前那三条一样，不抬窗口），音乐就稳定了（`experimental/music/listen.py` 的 `_tell_active`）。
- **检查游戏在不在跑**：进程名要同时匹配 `ra3_1.xx.game`、`RA3.exe` 和起义时刻的 `ra3ep1`（之前漏了起义时刻）。
- **截图隐私**：给启动器之类的窗口截图只用 PrintWindow 截那个窗口，别用 CopyFromScreen 截整屏（会截到用户的其他窗口）。
- **弹窗自动点击**：测试台的弹窗钩子只点一次、不能 `continue` 循环（曾经在 Tacitus 窗口上空转约 15 分钟），卡住就让 150 秒超时生效。

### 测试工具用法（编号沿用 HANDOFF 里的）

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
     - 任务显示的倒计时（`DISPLAY_COUNTDOWN_TIMER`）和计数器在同一张列表里，排在计数器上面，会把计数器往下挤一行。读数程序现在先数有字的行，多出来的当倒计时跳过（2026-10-24）。
     - 标签最后一个字和数字挨得太近（如以"车"结尾，只隔 3 像素）时，数字会被并进标签读错；以"量"结尾的标签没问题。
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
   - **第一轮对照两边都 FAIL，是测试脚本的错**：攻击移动只打单位、不打建筑，护卫死光后全队停在路点发呆（看了相机对准平台 1 的那几帧才看出来）。坑已记在上面「踩过的坑」。
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
   - **设计文档**：[docs/story/levels.md](../story/levels.md) 每个关卡一张卡片，只用代码公开的名字写意图。`tests/test_level_cards.py` 保证卡片和代码一致，做过 8 种变异检验。
0h. **地图工具和原版参考**（2026-10-23，用户："想想分析地图和操作地图的过程中哪些步骤是固定的，可以加入 MCP 当中"）。下面的 MCP 工具要新会话重启服务后才出现；本会话已用 stdio 客户端逐个实测：
   - `cnv_preview(name, check)`：约 10 秒出结果，不编译、不开游戏（`build.py <关> --preview` → `work/maps/<mod>.map`）。
     - 先跑地图模块的设计检查 `platmap.lint`：坡道坡度、标了 `Site.build` 的地点够不够平、矿和科技建筑是否在平地上、桥两头是否同层陆地且中间是水。
     - 再按原版 40 张图的范围逐项对比（`mapstudy.compare`），最后出俯视图。
     - 改了地图或摆位，先跑它，再跑 `cnv_check`。
   - `map_study(target)`：量一张原版图（名字片段，如 `s09_newyork`）或我们的 mod / .map，给出数字和俯视图。
   - `retail_scripts(pattern)`：原版脚本里用到某条件 / 动作的整段脚本。
   - `retail_objects(pattern)`：某模板在原版图里的摆法，给位置、朝向、标记位、归属、脚下高度。
   - `retail_goals()`：各关目标的英文标题。
   - 原版资料第一次用时缓存到 `work/retailref/`，约 2 分钟（`retailref.py`）。
   - `bench_menu()`：截任务菜单，看目标列表和标记。
   - `cnv_check` 遇到截帧断线（BENCH DROPOUT）会自动不重编再跑一次。
   - 一次观察超过 120 秒的检查，自动拆成几段（`build.steps`）。
   - 离线守卫：`tests/test_maps.py`，所有平台地图的设计检查必须为空，做过 4 种变异检验。
0a. **编图前自动静态检查**：`experimental/campaign/lint.py`，每次编图在编译前跑（`make_campnew7.compile_map`），有 ERROR 就停（`CNV_LINT=warn` 只打印）。规则对应上面"踩过的坑"：视野和射程（超过 1.5 倍只警告）、步兵 IMMOBILE、超时空模板缺 ObjectFilter、ToggleState 缺 SkirmishAiInfo、复制件里留着原版 id、SpawnBehavior 刷的自制模板没摆在地图上（按名字链接的算摆了：`experimental/cnv` 链接每个单位）、只有固定挂点武器又不会自己挑目标（只警告）。`python -I -X utf8 experimental/campaign/lint.py` 单独查全部单位文件；`tests/test_lint.py` 每条规则一个正反例。新坑出现时先加一条规则和测试。
1. 日常操作先用根目录的 `cnv.py`（`python -I -X utf8 cnv.py -h`）：build / map / bench / sheet / where / launcher / status，不再临时写脚本。新测试一律用 `run_bench.ps1 -Nav`（`cnv.py bench` 就是它）：时间从进入关卡算起，点击位置用 `experimental/testbench/calib.py` 的 `world_to_screen` 从世界坐标算（标定只对从 CampNew18 岛派生、开局镜头相同的地图有效；换了开局镜头要重新标定：`CNV_CALIB=base/grid` 各编一次、各跑一次，再 `calib.py fit`）。要看镜头外的地方：左键点 `calib.world_to_minimap(x, y)` 移镜头，再用 `calib.world_to_screen_at(x, y, 镜头中心)` 算点击位置；要打人就右键点敌人本身，右键点小地图只是移动。
1b. 给用户自己试玩用的图形启动器：根目录 `launcher.pyw`（桌面快捷方式"红警3 测试启动器"，2026-10-21）。它列出 Mods 里所有编好的 mod，双击就启动，游戏在运行时拒绝启动。分组从代码推出来（2026-10-24，用户发现手写名单过时，A4 和所有检查图都落进了"其他"）：
   - `experimental/cnv/build.py` 的登记表里，`LEVELS` 的本体归"战役关卡"，按卡片顺序；它们的检查图归"关卡检查（脚本代玩）"；其余归"单位测试图"，标题取单位的中文说明。
   - 关卡的标题、一句话玩法和检查说明从 `docs/story/levels.md` 的卡片读。
   - 只有登记表之外的旧图（make_campnew*.py）还要在 `LEGACY` 里写一行。
   - 新关卡只要登记进 `LEVELS`、写好卡片，再编一次本体（`build.py <关>`，不带检查），就会出现在"战役关卡"里。`python -I -X utf8 launcher.pyw --list` 不开窗口打印列表。
1a. **2026-10-21 晚起测试台副本不加载 Tacitus**：Tacitus 出了 1.1.1，又在每次启动时弹更新窗口，Steam 目录里的也还是 1.1.0、没有新版可抄，就把副本的 `Data\dsound.dll` 改名成 `dsound.dll.tacitus110.off`（测试台不联网，用不着它；改回原名即恢复）。没有 Tacitus 时游戏会弹"连接中断通知"并退回主菜单：`nav.py` 的 POPUPS 认得它、点确定，`run_bench.ps1` 随后从第 0 步重新走菜单（约第 29 秒进关）；ra3bench（`harness.py`）则看画面停在哪一步就从哪一步接着走——这个弹窗也在关卡里出现过，从第 0 步重走会一直等主菜单到超时（2026-10-27 修）。以下是旧情况：测试台的游戏副本 `work/testbench/RA3` 里也有 Tacitus（C&C:Online 的游戏补丁，`Data\dsound.dll`）。它的版本落后于新版时，每次启动都弹更新窗口，挡住菜单；而且它是 ImGui 窗口，测试台发的点击点不到。办法：把 Steam 游戏目录里更新过的 `Data\dsound.dll` 复制到测试台副本（2026-10-20 已换成 1.1.0，旧的留作 `dsound.dll.tacitus100.bak`）。`nav.py` 的 POPUPS 只能识别出这个窗口，点不掉它。卡在菜单时，看 `shots/nav_last.png` 就知道卡在哪个画面。
