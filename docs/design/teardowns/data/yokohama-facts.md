# 原版 帝国第 7 关 横滨 · 设计拆解

来源：`work/retailref/camp_j07_yokohama_stewart.txt`（437 个脚本）、`.json`（物体、目标）、map_study。读法照 `docs/story/plans/retail/j03_odessa.md`：方括号是脚本名；`SET_MILLISECOND_TIMER` 的数是秒；电台视频长度记作 L（未知）。

**一个容易看错的地方**：导出文本里，条件行末尾的后缀是 `+0100000001000000` 时，表示这个条件是"取反"（NOT）。本关有 56 处。比如占领前哨要求"区域里**没有**盟军单位"，P2 的那批台词只在"P2 **不是**人类"时才播。下文都已经按取反来理解。

## 1. 一句话 + 开局

- **一句话**：开局只有百合子一个人。先带着她闯过两座桥，沿途收编鬼王和忍者，再夺回 4 个日本前哨；然后守 5 分钟，等来海上基地车；最后在 15 分钟倒计时内，拆掉盟军基地里的 4 座中继站。
- **玩家（Player_1）**：
  - 部队：百合子 `o_yuriko_p1`，在西南角 (569,312)。血量上限简单 600、普通 500、困难 400 [setup yuriko health easy/medium/hard]。
  - 建筑：起点旁一座车库科技建筑 (942,145)；地图外 (5156,2581) 有一座雷达站（推断：让没有基地的玩家也有小地图）。
  - 资金：简单 5000、普通 4000、困难 3000 [setup player money *]。不过一开始禁造基地车 [setup starting conditions]，所以前半关这笔钱花不出去。
  - 秘密协议点数：上限 0，到第 3 段的过场结束才改成 10 [player powers p1] [cine relays done]。
- **友军新三（Player_2）**：第二个百合子 `o_yuriko_p2` 在 (542,286)，旁边一座医院。资金和玩家一样。
  - 单人时由 AI 控制：修建筑、不重建、不准造纳米虫巢 [Skirmish AI - Setup 4]。
  - 不是人类时直接全图可见 [non human player 2 gets full reveal]；双方资源共享 [setup starting conditions]。
- **敌人**：
  - Allies01：东北角的盟军主基地。有 2 座建造厂、超时空传送仪、4 座中继站（`TH_AlliedDisruptorStation`）、17 座电厂。资金 2000/4000/5000（困难最多）。简单难度禁造冷冻直升机 [delete units on easy]。
  - Allies02：前半关路上的盟军，资金 0。分三批：
    - 起点桥头 3 辆守护者坦克；
    - 过桥后 4 个维和步兵（Bridge_00）；
    - 南岛上 Bridge_01 队：坦克加标枪兵。
    - 各难度数量：起点桥头坦克 1/2/3；Bridge_01 坦克 2/4/6、标枪兵 0/1/2 [delete units on easy and normal] [delete units on easy]。
  - Hostile01：15 栋民房里刷驻军 [spawn garrisons] [garrison civ spawns]，编成未确定。
  - Soviet01：库可夫。第 3 段中途才登场。
- **中立的前哨（Outposts01）**：4 个日本小基地，开局无敌、不能卖 [setup outposts]。每个都带 4 座守卫塔、1 座高级防御塔、4 座电厂、1 座矿厂。另外：
  - 1 号、4 号各有一座纳米虫巢（超武）；
  - 1、4 号各有船厂，2 号有战车工厂，3 号有兵营。
- **地图边界**：全关不切换，没有 `SET_ACTIVE_BOUNDARY`。整张图 5000×5000 从头开放。
- **拾取**：3 个治疗箱，位置 (812,1308)、(1129,1793)、(1668,873)，都在前半关的路上，一直闪烁 [flash crates every so often]。

## 2. 分段

设 L4、L5 为视频 J07TH04、J07TH05 的长度；D1 为 4 个前哨全部到手的时刻。

### 段 0：开场过场（0～26 秒）
- 盟军轰炸机炸日本港口，海豚冲岸；镜头推到百合子 [setup cine intro] [cine harbor pan camera] [bomb *]。
- 第 26 秒交还控制 [end cinematic and give back control]，第 27 秒播 TH04。

### 段 1：突围 + 夺回前哨（主目标 `J07_Objective_Capture_Outposts` "Retake the Forward Bases"）
- **开始**：TH04 播完，再过 2 秒，约 28+L4 [give obj 1 - capture four outposts]。目标标记挂在 4 个前哨上。
- **6 秒后**，奖励目标 `J07_Bonus_Save_Nanoswarm`（"Capture the Nanoswarm Hives"）亮出，标记挂在两座虫巢上 [give bonus obj 1 - save the nanoswarms]。
- **盟军 AI 启动**：目标 1 亮出，或玩家先拆了它任意一座建筑，两者哪个先到算哪个 [Skirmish AI - Setup 1]。
- **玩家要做**：
  1. 沿路依次踩进这几个区域：桥 0 → 桥 1 提示区 → 桥 2 提示区 → 鬼王区 → 忍者区。每一处都按区域触发，没有计时（见第 3 节）。
  2. 到达前哨区。踩进去的条件是"玩家有单位在区内，且**没有**盟军单位在区内"，前哨整队就转给玩家 [player 1 captures outpost 1..4]。
- **前哨的分配（关键）**：
  - 玩家最多拿 2 个（`c_outposts_p1_owns < 2` 才能拿）。
  - 拿满 2 个以后再踩进别的前哨，那个前哨转给 P2 [player 2 captures outpost *] 的第二个 OR 分支。
  - 所以单人时，必然是玩家 2 个、新三 2 个。
- **到第 2 个前哨**：P2 的 AI 改成主动去占剩下的 [non human player 2 capture outposts]，新三说台词 shinzo_03。
- **交给玩家的东西**：
  - 每拿一个前哨，就得到它的全部建筑：电厂、矿厂、塔、工厂，可能还有虫巢。
  - 但基地车仍然禁造，所以玩家只能用前哨自带的工厂出兵（推断）。
- **失败**（这一段）：
  - P1 名下一个日本单位或建筑都不剩，判负 [either player has died - obj 1]。没有"百合子死了就输"的专门脚本，而地图外那座雷达站也在 P1 名下，所以百合子死了是否立即判负，未确定。
  - 合作模式下，P2（人类）全灭也判负；AI 盟友全灭则不判负。
- **结束**：4 个前哨都到手，并且奖励目标 1 已经结算（完成或失败）6 秒后，目标 1 完成，即 D1+6。D1+11 自动存档 [done obj 1] [AUTOSAVE 2]。

### 段 2：坚守 5 分钟（主目标 `J07_Objective_Defend_Outposts` "Hold Out for Reinforcements"）
- **开始顺序**：
  1. D1+12：播情报 37；
  2. 情报 37 播完 1 秒后播 TH05；
  3. TH05 播完 1 秒后，目标 2 亮出 [introduce objective 2] [f intel 37 done] [TH - J07TH05 - End] [give obj 2 - defend outposts]。
  - 合计约 D1+14+情报37 的长度+L5。
- **屏幕上**：300 秒倒计时（`SCRIPT:J07_OBJECTIVE_DEFEND_OUTPOSTS_TIMER`），标记挂在 4 个前哨上。
- **玩家要做**：守住，熬过倒计时。
  - 某个前哨区里己方建筑全没了，只是摘掉那个标记，**不判负** [lost outpost * obj 2]。
  - 段 1 期间则不同：任何一个前哨区里，前哨、P1、P2 三方的建筑都没了，就直接判负 [lost outpost 1..4] [outpost lost - fail mission]。
- **提前结束**：Allies01 和 Soviet01 的"判负清单"物体都清零 [outposts defended]（推断：基本只有拆光盟军才会走这条）。
- **交给玩家的东西**（目标完成时，记为 O2）[spawn mcvs]：
  - O2+1：海上基地车，自动展开，展开前无敌、选不中；
  - O2+3 船厂蛋、+5 兵营蛋、+7 战车工厂蛋、+9 矿厂蛋。每样只在玩家还没有这种建筑时才给。
  - 新三那份一样，O2+15 交给 AI。
  - O2+5 自动存档 [AUTOSAVE 3]。
- **一处废弃设计**：脚本还写了三波各 5 队的步兵和战车增援（`Player_1/r_a_*`），但刷兵脚本是 `[off]`，没有任何地方打开它们 [sub spawn reinforcements a a..b c]（推断：废弃）。b c 那一波还错挂在 `t_spawn_b_2` 上。真正到手的只有基地车和建筑蛋。

### 段 3：拆中继站（主目标 `J07_Objective_Destroy_Relay_Stations` "Destroy the Allied Relay Stations"）
- **开始**：
  - O2+12 黑屏 [introduce relays]；
  - 过场 6 秒：全图揭开，中继站亮灯；这段时间所有敌方都临时改成友好，避免过场里挨打 [cine relays begin]；
  - 过场结束：镜头回到建造厂；基地车可选、可造；协议点数上限 0 改成 10 [cine relays done]；
  - 再过 2 秒，目标 3 亮出，约 O2+21 [give obj 3 - destroy relay stations]。
- **屏幕上**：900 秒倒计时（`SCRIPT:J07_OBJECTIVE_DESTROY_RELAY_STATIONS_TIMER`）。两处中继站防区各揭开半径 100。
  - 中继站这时才去掉无敌 [activate relay stations]。
  - 拆掉，或者用工程师占领，都算 [relay station 1..4 is destroyed]。
- **奖励目标 2** `J07_Bonus_Destroy_Soviets`（"Destroy the Soviet Forces"）：
  - 库可夫登场后才亮出，见时间线 [give bonus obj 2 - destroy the soviets]；
  - 标记每帧挂在离玩家最近的 2 座苏军建筑上 [bonus objective find targets - structs]；
  - 先拆光 4 座中继站、而苏军建筑还在，就判奖励失败 [failed bonus 2]。所以想拿奖励，必须先灭苏军、最后才拆中继站。
- **结束**：
  1. 4 座中继站都没了，目标完成，倒计时停；
  2. 6 秒后播 TH09；
  3. TH09 播完 1 秒后任务胜利；两家盟军卖光建筑 [done obj 3] [TH - J07TH09 - End] [clear obj 3]。
- **失败**：倒计时归零，播失败过场 [relay timer expires] [setup loss cine intro]：
  - 镜头对准一座还在的中继站，转 4 秒，播情报 19，然后判负 [cine relay chooser] [cine loss end]。

## 3. 时间线（T = 任务开始后的秒数）

| 时刻 | 事件 | 类型 |
|---|---|---|
| T0～26 | 开场过场 | 固定 |
| T27 | 播 TH04 | 固定 |
| 约 T28+L4 | 目标 1 亮出；盟军 AI 启动（或者玩家先打它的建筑，更早）| 固定 / 玩家推进，哪个先到算哪个 |
| +6 | 奖励目标 1 | 固定 |
| 进入 `area_bridge_00` | Bridge_00 维和兵沿路冲来；情报 30 提示心灵冲击，技能按钮闪 [bridge 0 attacks] [f intel 30] | 玩家推进 |
| 第一次打 Allies02 | 情报 29 [player attacks first tank] | 玩家推进 |
| 进入 `area_cue_bridge_1` | Bridge_01_b 立刻全图搜敌；Bridge_01 沿路进攻，15 秒后也转成搜敌；桥 2 的门房闪 15 下 [bridge 1 attacks] [bridge 1 hunts] | 玩家推进 + 固定 15 秒 |
| 进入 `area_cue_bridge_2` | 刷 Bridge_02、Bridge_02b 两队，编成未确定，沿路进攻；桥 0 的两座门房闪 [bridge 2 attacks] | 玩家推进 |
| 进入 `area_spawn_jinzatsus` | 每人送 2 辆鬼王（`JapanAntiVehicleVehicleTech3`），出场就冲锋，冷却清零；5 秒后交出控制权，播情报 31；同时 Bridge_02_b 开始搜敌 [give players jinzatsus] [hand over jinzatsus] [trigger tank attacks] | 玩家推进 + 固定 5 秒 |
| 进入 `area_give_ninjas` | 每人 6 个忍者，在烟雾里出生，1 秒后转给玩家，播情报 32，接着新三说话 [trigger ninja spawns] [release ninjas] [f intel 32 done] | 玩家推进 |
| 进入 `area_begin_paradrops` | 盟军开始空降：每 5～10 秒一次（随机），5 个落点随机挑，最多 16 次；它的建造厂全没了也会停 [trigger paradrops] [begin paradrop] [reset paradrop] | 玩家推进，然后计时 |
| 第 1 个前哨到手 | Allies02 全队主动进攻前哨；情报 34，换音乐 [allies attack bases] [f intel 34] | 玩家推进 |
| 第 2 个 | P2 的 AI 去占剩下的 | 玩家推进 |
| 第 3、4 个 | 情报 07、36；Allies02 全图搜敌 [allied units attack outposts] | 玩家推进 |
| D1+6 / +11 | 目标 1 完成 / 自动存档 | 固定 |
| 目标 2 亮出（G2）| 300 秒倒计时；超时空传送开始：立刻传一队兵到 5 个落点之一，之后每 480 秒一次，超武计时也设成 480 [begin chronosphere]；冷冻直升机解禁（简单难度仍禁）[allow cryocopters] | 固定 |
| G2+120 | 新三："还剩 3 分钟" [f_shinzo_05] | 固定 |
| G2+240/270/290 | EVA 报剩 1 分钟、30 秒、10 秒 | 固定 |
| O2 = G2+300 | 目标 2 完成；+1 基地车，+3～+9 建筑蛋，+12 中继站过场 | 固定，拆光敌人可以提前 |
| G3 ≈ O2+21 | 目标 3：900 秒倒计时 | 固定 |
| G3+150～300 | 虫巢充能好了就提示"用纳米虫群"（情报 14）[if ready to fire superweapons] | 计时 + 超武状态 |
| G3+180 | **库可夫到场**：苏军整座基地瞬间建好（建造厂、2 机场、2 船厂、3 矿厂、9 电厂、6 防空、起重机、作战实验室、超武）；音乐换库可夫 [soviet base setup] [soviets build base] | 固定；盟军"判负清单"物体 ≤5 时提前 [if allies almost destroyed bring soviets] |
| +5 | TH01；播完以后才允许亮奖励目标 2 | 固定 |
| +30 | 苏联海军分三波，两组入口各 5 个点，A 组 +31/35/39，B 组 +32/36/40 [spawn soviet navy] [soviet spawn reinforcements *] | 固定；过场在播时延后 |
| 约 +44 | 苏军全部交给 AI，播情报 39；**+8 秒亮奖励目标 2** [reset ai control for soviet forces] | 固定 |
| G3+300 | EVA：剩 10 分钟 | 固定 |
| G3+420 | 剩 8 分钟：奖励 2 还没完成就播 TH02 [eva countdown 8m last] | 固定 |
| G3+600 | 剩 5 分钟：EVA，音乐转紧张 | 固定 |
| G3+720/780/840/870/890/892.5 | 剩 3 分（EVA）、2 分（情报 42）、1 分、30 秒、10 秒、7.5 秒（情报 18）| 固定 |
| G3+900 | 失败过场，约 5 秒后判负 | 固定 |

各难度数字汇总：

| | 简单 | 普通 | 困难 |
|---|---|---|---|
| 百合子血量 | 600 | 500 | 400 |
| 玩家/P2 资金 | 5000 | 4000 | 3000 |
| 盟军资金 | 2000 | 4000 | 5000 |
| 起点桥头坦克 | 1 | 2 | 3 |
| Bridge_01 队（坦克 + 标枪兵）| 2 + 0 | 4 + 1 | 6 + 2 |
| 冷冻直升机 | 全程禁造 | 目标 2 起可造 | 目标 2 起可造 |
| 盟军防御建筑 | 删掉 2 座（`MEDIUM_struct_a/b`）| 齐全 | 齐全 |

所有计时（300 秒、900 秒、480 秒超时空、180 秒苏军到场）三个难度都一样。

## 4. 压力来源，以及怎么关掉

| 压力 | 从哪来 | 怎么关 |
|---|---|---|
| 桥头小队 | 预先摆好的 Allies02，按区域触发进攻 | 打光；或者炸桥：桥 1 断了，桥上的单位当场被杀；绕不过来的队伍被送回出生点删掉 [kill objects on bridge a..h] [bridge0X units cut off - move] [allies02 units despawn] |
| 民房驻军 | Hostile01，开局就在 15 栋楼里 | 打光，或者绕开（推断）|
| 盟军空降 | 进区以后最多 16 次 | 拆光它的 2 座建造厂；或者耗完 16 次 |
| 超时空传送部队 | 目标 2 起，每 480 秒一次 | 拆掉超时空传送仪 `o_allied_super` (4469,4271) |
| 盟军遭遇战 AI | 东北基地，会重建 | 只能拆。拆到"判负清单"里只剩 ≤5 个物体时，库可夫提前登场 [if allies almost destroyed bring soviets]。"建筑 ≤6 座就停止重建"那条脚本还要求 `/f_soviet_arrival`，可这个标志全图没有地方设置，所以它不会生效 [if allied player is nearly defeated]（推断）|
| 苏军 | G3+180 起，一整座基地加海军 | 拆光苏军建筑，奖励目标 2 完成。苏军 AI 的启动 [Skirmish AI - Setup 2] 和停止重建 [if soviet player is nearly defeated] 也都卡在这个没人设置的 `/f_soviet_arrival` 上，所以苏军可能根本没走"遭遇战 AI 建基地"这一路，只是单位交给了 AI 去打（未确定）|
| 15 分钟倒计时 | 目标 3 | 拆完 4 座中继站；用纳米虫群打中继站区，计时暂停 30 秒 |

## 5. 新单位 / 新机制的教学

- **心灵冲击**：到第一座桥时，情报 30 加技能按钮闪光 [f intel 30]。迎面就是 4 个维和步兵，正好练（推断）。
- **鬼王**：在区域里直接送 2 辆，出场即冲锋 [give players jinzatsus]。第一次"必须用"，是因为接下来的路上只有它们能对付坦克（推断）。
- **忍者**：烟雾里出场 6 个 [spawn ninjas in smoke p1]。没有专门的必须用场景。
- **占领前哨**：教法是"踩进去、并且清掉区内的盟军"。这条规则只有脚本知道，屏幕上靠目标标记加情报 34 引导。
- **给 AI 盟友下命令（只在 P2 是 AI 时）**：
  - 走进 `area_player_show_outpost_hotspots`，4 个前哨出现可点的热点 [show hotspots to player]；
  - 点一个，就叫新三去占那里；点满 2 个，热点全部消失 [do hotspot *] [erase hotspot *]；
  - 镜头第一次扫到前哨，TH11 讲这套用法，并打开协同 AI 的界面 [TH - J07TH11 - Play]。
- **请 AI 盟友放纳米虫群**：
  - 第 3 段，新三手里有虫巢时，两处中继站各有一个热点，点了他就放 [show hotspot 5 a/b] [player 2 fire nanoswarm at a/b]；
  - 冷却 120 秒，而且要求区域里没有双方单位时才重新出现 [reset hotspot 5 a]；
  - 剩不到 10 分钟时，TH12 再提醒一次 [if ready to fire superweapons again]。
- **纳米虫群压住倒计时**：任意一方在中继站区放了虫群，倒计时停 30 秒，中继站灭灯，然后继续走 [relay stations unpowered] [relay stations powered]。这是本关的核心机制：保住两座虫巢，就是在为最后一段"买时间"，所以奖励目标 1 直接为第 3 段铺路。

## 6. 信息

- **倒计时**：目标 2 的 300 秒，目标 3 的 900 秒，都显示在屏幕上。超时空传送仪的特殊能力计时被设成 480 秒 [begin chronosphere]（推断：玩家可以在超武计时里看到）。
- **EVA 报时**：
  - 目标 2：剩 60/30/10 秒；
  - 目标 3：剩 10/5/3/1 分钟、30 秒、10 秒；另外 8 分钟、2 分钟、7.5 秒各插一段剧情台词。
- **标记**：
  - 目标 1、2 挂在前哨路点上，拿到或丢掉一个就摘掉那个；
  - 奖励 1 挂在两座虫巢上；
  - 目标 3 挂在 4 座中继站上，第一次被看见时闪 5 下 [flash relay stations 1/2]；
  - 奖励 2 挂在最近的苏军建筑上；
  - 苏军基洛夫一直全图可见 [reveal enemy kirovs a/b]，它的加速技能被禁用。
- **雷达事件**：前哨到手、基地车到达、苏军新刷的队伍，都在小地图上打点。
- **失败原因**：
  - 丢前哨，播情报 15；
  - 目标 2、3 期间失去"判负清单"里的全部物体，播情报 16；
  - 超时，播失败过场加情报 19。
- **废弃台词**：情报 05/06/08/09/17 的标志从来没被设置；TH03 是 `[off]`，没人打开；TH10 的标志也没人设置（推断：废弃）。开场的库可夫用的是第 2 关的语音 `MI02_ImperialIntel12` [f intel 12 j02]。

## 7. 地图（map_study：5000×5000，陆地 42%，陆地里平地 76%，悬崖 2.6%，两层高度 300～320 / 380～400，矿点 14 个（起点附近 0 个），科技建筑 7 座，桥端点 4 个，目标 3 主 + 2 奖励，5 个都有标记）

- **西南角高台（地面高 392）**：起点。有医院、车库两座科技建筑，被水隔开。出口是桥 0：(800,800) 到 (1110,1120)。
- **桥 1**：(1663,741) 到 (1906,493)，通往南面小岛。Bridge_01 队守在岛上 (2000～2170,230～410)。这座桥可以拆，拆了能断掉敌人的来路。
- **桥的修复兜底**：
  - 桥被炸断、玩家还困在起点区时，会凭空传送来一个**敌方**工程师去修桥，15 秒后把他杀掉，再重新检查 [if first bridge destroyed] [reset bridge fixer]；
  - 第二座桥同理。这是一个防卡关的兜底。
  - 门房名字有 00/01/02 三个编号，地图上只有 2 座桥，编号和桥的对应关系未确定。
- **中部对角大陆（地面高 314）**：从西北 (900,3400) 斜到东南 (3400,950)。
  - 4 个前哨依次排开：1 号 (1000～1340, 2790～3410)、2 号 (1530～2080, 2160～2670)、3 号 (2200～2680, 1570～2030)、4 号 (2790～3440, 950～1330)。
  - 每个前哨带 1 个矿点和 1 座矿厂。
  - 15 栋驻军民房沿着大陆中线分布；两口油井 (827,2460)、(2445,806) 标了"遭遇战 AI 别打"。
- **东北高地（392）**：盟军主基地 (2700～4900, 2860～4840)，与中部大陆隔着一条斜向水道，有 5 个矿点。
  - 中继站 A 组 (3673,4727)、(4012,4727) 在北缘；B 组 (4691,3709)、(4691,4049) 在东缘。两组分在基地深处的两个角上，逼玩家要么两路进攻，要么用两次虫群（推断）。
- **两座"留给玩家扩张"的小岛**：西北小岛 (162, 2892/3105) 有 2 个矿点，标了"AI 别拿" [setup flags]；东南小岛 (3005～3111, 114～220) 也有 2 个矿点。
- **水域 58%**：这就是为什么给的是海上基地车和船厂蛋，苏军也是从海上来。

## 8. 给我们的要点（推断）

1. 用"突击队开路 → 占据点 → 守计时 → 带着基地限时拆目标"四段，把一个英雄单位慢慢变成一整支军队。每一段的奖赏，都是下一段的工具。
2. 用"玩家最多拿 2 个、其余自动给盟友"，把合作伙伴强行带进局里。
3. 超武暂停倒计时：一个保护类的奖励目标，直接换成主线时间。
4. 炸桥既是危险，也是工具；配上"敌方工程师来修桥"的防卡关兜底。
