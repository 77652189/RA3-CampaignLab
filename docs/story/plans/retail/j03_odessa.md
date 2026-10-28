# 原版 帝国第 3 关 敖德萨 · 反推策划案

来源：`work/retailref/camp_j03_odessa_stewart.txt`（301 个脚本）、`work/retailref/camp_j03_odessa_stewart.json`（物体、目标）、`work/mapstudy/camp_j03_odessa_stewart.png`。

格式按我们的 `docs/story/plans/README.md` 和 `a4.md`。`yaml` 块只为对照，不会编译；地点名直接用原版的路点、区域名（`wp_*`、`area_*`），我们的地图上没有这些地点。

**几条读法约定：**
- 方括号里是原版脚本名，作为证据。
- "推断"：根据坐标或命名推出来的，脚本没有直接写。"未确定"：现有材料里查不到。
- JSON 只有物体，**没有路点名、区域形状、队伍（team）编成**。所以凡是 `CREATE_REINFORCEMENT_TEAM` 刷出来的兵，具体是什么兵、几个，都查不到，下文统一写"编成未确定"。
- 时间：`SET_MILLISECOND_TIMER` 的数是秒；唯一一处 `SET_TIMER('t_intro_cine_start', 5)` 按帧算，约 0.3 秒，下文忽略不计。电台视频（`MOVIE_PLAY_RADAR`）的长度未知，记作 L。

**几个阵营：**

| 原版玩家 | 是谁 | 依据 |
|---|---|---|
| Player_1 | 人类玩家。开局只有护卫部队，没有基地，资金 0 | mapstudy `human: Player_1`；[SETUP - Starting Money *] |
| Player_2 | 友军指挥官健二（单人时是 AI，合作模式时是另一个人）。有一座现成的基地 | [Skirmish AI - Setup]、[f kenji 01] 只在 Player_2 不是人类时播 |
| Japan_01 | 第三方，只拥有运输船。玩家指挥不了它们 | [spawn transport a..j] 把船建在 `Japan_01/teamJapan_01` |
| Soviet01 | 苏军"绿"基地（地图中部偏西的海边），遭遇战 AI；还有海上那批伏击用的潜艇、魟鱼和直升机 | [enable enemy ai] |
| Soviet02 | 库可夫（地图东北角的大基地），第 3 段才唤醒遭遇战 AI；第 2 段负责追着巨人打 | [turn on ai for soviet 02] |
| PlyrCivilian/Soviets_01_Orange | 平民名下的"休眠敌人"：4 座炮兵阵地、4 座磁暴线圈。第 2 段开始时才转给 Soviet01 | [transfer soviet forces in orange border] |

## 1. 定位

- 一句话：先护送 10 艘运输船过海到仓库岛，把将军处刑者的零件运齐；然后开着拼好的将军处刑者一路踩过敖德萨，拆掉 4 座炮兵阵地，最后和健二一起拆掉库可夫的基地。
- 类型：三段换玩法。第 1 段护送（小股机动部队），第 2 段英雄单位横冲直撞，第 3 段英雄配合友军 AI 拆基地。**玩家全程没有自己的基地，也没有钱。**
- 教什么：怎么用将军处刑者——它很强，但会被磁暴类武器围攻，冲击波技能要会用；它踩上桥，桥就塌。护送段不教新东西，只是给第 2 段的登场做铺垫。

```yaml
关卡: j03
名字: 敖德萨
一句话: 护送零件船队过海到仓库岛；拼好的将军处刑者踩平炮兵阵地，再和健二一起拆掉库可夫的基地
地图: camp_j03_odessa_stewart（5000×6000；南面是海，北面是城区，东北角是库可夫）
阵营: {我: 帝国, 敌: 苏联, 其他: {健二: 帝国, 运输船: 帝国, 橙区苏军: 苏联}}
时长: 未确定（护送段约 2～3 分钟，后两段取决于玩家）
```

## 2. 开局

**玩家（Player_1）**
- 资金 0，三个难度一样 [SETUP - Starting Money EASY/MEDIUM/HARD]。
- 秘密协议点数上限 0 [set maximum player power points]；到第 2 段才给（上限 3，先给 1 点）[show objective 2]。
- 部队：`Player_1/Transport_Guards` 队的 `JapanAntiAirVehicleTech1`，困难和普通 4 辆，简单 6 辆（多出的 `EASY_striker_a/b` 在普通、困难被删掉）[delete units for medium and hard]。
  - 我们的词表把这个模板叫"天狗"，可原版给它起的名字是 `striker`，按这个名字应该是打击者-VX。词表可能把两个名字对调了，**未核实**，下文只写模板名。
  - 开场过场里它们一起变形 [transform units]，第 1 段结束时被整队删掉 [get rid of old p1 units]。
- 地图外 (-352,-348) 摆了一座属于玩家的雷达站。推断是为了让没有基地的玩家也能看到小地图。

**友军健二（Player_2）**
- 现成基地在 (3500,1200)，南岸偏东：建造厂、兵营、战车工厂、4 座电厂、2 座矿厂、2 座守卫塔。
- 资金 12000/10000/8000，协议点数上限 3、开局 1 点。
- 第 1 个目标亮出时，健二才作为遭遇战 AI 启动 [Skirmish AI - Setup]。

**敌人**
- 海上伏击（Soviet01）：阿库拉潜艇（`SovietAntiNavyShipTech2`）、魟鱼（`SovietAntiNavyShipTech1`）、双刃直升机，散在南面海里和航线两旁。各难度数量：

  | | 简单 | 普通 | 困难 |
  |---|---|---|---|
  | 魟鱼 | 5 | 7 | 9 |
  | 阿库拉潜艇（脚本里叫 o_sub_*） | 4 | 6 | 6 |
  | 双刃直升机（o_chopper_*） | 2 | 3 | 3 |

  - 怎么分难度：两组队伍，`Delete_On_Easy` 简单删掉、`Delete_On_Medium` 普通删掉 [delete units for easy] [delete units for medium]。
  - 两组队伍里的魟鱼成对摆在同一个位置：(1716,172) 和 (1628,179) 一对，(3259,180) 和 (3171,187) 一对。所以这两个位置在简单、普通各留 1 艘，困难留 2 艘。
  - 一艘魟鱼 (4591,1687) 就摆在运输船出生点旁边。
- 苏军"绿"基地（Soviet01）：在 (800～2400, 1800～2000)，有机场、兵营、4 座磁暴线圈、2 座高级电厂、矿厂。资金 8000/10000/12000（困难最多）。
- 两座地标在 Soviet01 名下：歌剧院 (1862,4852)、教堂 (3758,5323)，后者就在库可夫基地里。城堡 (156,160) 开局在平民名下。
- 休眠的橙区苏军（平民名下）：4 座 `KR_ArtilleryDome` 炮兵阵地，a (2616,4186)、b (603,4750)、c (1457,2846)、d (4134,2930)；扩张点 a、c 各有 2 座磁暴线圈。
- 库可夫（Soviet02），基地在 (3400～4850, 4300～5800)：
  - 建筑：VIP 地堡（`o_krukov_conyard`，相当于建造厂）、2 座战车工厂、2 座兵营、机场、起重机、6 座高级电厂、8 座磁暴线圈、6 座防空炮（简单删掉 `MEDIUM_aaturret_a/b` 两座）；
  - 入口有一圈城墙：86 段墙、9 座塔；
  - 资金 0。
- 城区驻军：开局刷 6/12/18 队 Soviet02 的兵，各自钻进最近的建筑 [spawn soviet garrisons a..r] [team garrison nearby building]。每队编成未确定。
- 中立：4 座油井（标了"遭遇战 AI 别打"）[setup oil derricks]、1 座医院、10 个钱箱、7 个矿点。

```yaml
开局:
  资金: 0
  部队:
    - {单位: JapanAntiAirVehicleTech1, 数量: 6/4/4, 在: Player_1_Start, 角色: guards}
    # 健二的基地和资金属于另一个玩家，我们的词表写不出（见第 10 节）
    - {单位: SovietAntiNavyShipTech2, 数量: 4/6/6, 在: 南面海上航线两侧, 阵营: 敌, 角色: sub}
    - {单位: SovietAntiNavyShipTech1, 数量: 5/7/9, 在: 南面海上, 阵营: 敌}
    - {单位: 双刃直升机, 数量: 2/3/3, 在: 绿基地附近和西南角, 阵营: 敌, 角色: chopper}
    - {单位: KR_ArtilleryDome, 数量: 4, 在: [artillery a, b, c, d], 阵营: 橙区苏军, 角色: artillery}
    - {单位: GE_SovietVIPBunkerSubStructure, 在: 库可夫基地, 阵营: 敌, 角色: krukov conyard}
```

## 3. 机关

### 3.1 运输船流（护送对象）[obj 1 - escort mk parts]

- **对象**：10 艘 `JapanOdessaSpecialTransportVehicle`，名字 o_transport_a～j，归第三方 Japan_01，玩家指挥不了。
- **出生**：从 `wp_objective_1_boatspawn` 出发。开局约 9.3 秒刷第一艘，之后每 6 秒一艘，最后一艘在约 63.3 秒 [begin spawning transports]。
  - 刷出来时闪 5 下 [spawn transport *]；
  - 每一艘都挂上目标 1 的标记。
- **路线**：`NAMED_FOLLOW_WAYPOINTS('wpp_transports_path')`，一条固定的路点链。
  - 推断：东岸入口 (4948,2035) → 沿南面海往西 → 仓库岛 (980,710)，全长约 5100。
  - 船速未确定，所以单程多久也未确定。
- **走走停停**：**没有**。船从刷出来就一直沿路走到终点，不停、不等玩家。
  - 脚本里没有任何 STOP 或"等护卫"的逻辑。
  - 这和 map-language 第 7 节总结的"护送对象会等玩家，等几秒就自己走"不同：这关不等。
- **被打时**：船自己不做任何反应。脚本只做两件事 [if transport attacked a..j]：
  - 血量降到 60% 以下：EVA 喊一句 intel 20；
  - 在雷达上打一个事件点，提醒玩家去哪里救。
- **算到达**：船进入 `area_objective_1`（推断是仓库岛）就被直接删掉，"已到达"加 1 [arrive transport *]。
  - 第 8 艘（h）到达时，1 秒后播电台视频 TH06。
- **算损失**：每帧统计四方击毁运输船的总数：玩家、健二、两家苏军 [track transports]。
  - **友军误伤也算损失。**
  - 存活数 = 10 − 击毁总数；屏幕上显示存活数和要求数两个计数器 [show objective 1]。
- **要求数**：简单 6、普通 8、困难 10 [define transport totals easy/medium/hard]。
  - 失败条件是"存活数 < 要求数" [p1 loses his transports]，所以简单丢第 5 艘才输，普通丢第 3 艘，**困难丢 1 艘就输**。
- **防作弊/防漏算** [double check transports count B]：
  - 每帧核对"地图上还在的船"和"刷出 − 到达 − 被击毁"是否相等；
  - 不相等，就置 `f_player_killed_own_transports`，**跳过失败过场，直接判负** [dead transport cine over]；
  - 它具体防的是哪种情况未确定。推断：船不是被这四方击毁、却消失了。
- **完成**：到达数 ≥ 要求数，**并且** Japan_01 名下已经一艘船都没有 [all parts delivered]。
  - 也就是说，要等最后一艘船到达或者沉掉，才算完成；不会一够数就提前结束。

```yaml
机关:
  运输船:
    类型: 车队            # 只能近似：我们的车队是 3 辆、一起出发、玩家阵营、会停
    出发: 开局 + 0:09
    # 写不出：10 艘、每 6 秒一艘、第三方阵营、固定路点链、到达即删除、要求数 6/8/10
```

### 3.2 将军处刑者登场 [Mechaking Camera]

- 目标 1 完成后，按下面的顺序走一个大过场：
  1. 6 秒后黑屏 [show mission split]；
  2. 再过 2 秒，关输入、停音乐，**删掉玩家全部护卫部队** [mission split over intro mechaking] [get rid of old p1 units]；
  3. 0.1 秒后：
     - 播全屏 CG `J03MM01`；
     - 地图边界从 1 号切到 0 号（扩大到全图）；
     - 在 `wp_executioner_spawn` 建出玩家的 `o_executioner`（`JapanMechaKing`），三级武器升级全开；
     - 仓库（`o_assembly_warehouse`，原本无敌）被炸掉，屏幕震动 [spawn in mechaking]；
  4. 10.5 秒后交还控制，EVA 喊"战场扩大"；3 秒后健二说话；10 秒后亮出目标 2 [end mechaking intro and give control]。
- 从此玩家只有这一台巨人。它被摧毁就输 [p1 loses mechaking]。

### 3.3 巨人踩塌桥 [Bridges Setup]

- 地图上有 6 座桥（a～f）。
- 将军处刑者一进入某座桥的区域 `area_bridge_x`，那座桥就被直接摧毁 [if bridge a..f stepped into by mechaking]。
- 只对巨人生效，别的单位过桥不会塌。

### 3.4 跟着巨人走的磁暴骚扰 [Soviet Mechaking Tesla Attacks]

从目标 2 亮出开始一直运行到结束，**没有停止条件**。脚本每帧看巨人站在哪，决定刷什么兵：

| 巨人在哪 | 刷什么 | 从哪来 | 上限 |
|---|---|---|---|
| 海里 `area_water` | 魟鱼队 `Tesla_Boats` | 4 个点 `wp_soviet_tboat_spawn_a..d` 同时刷 | 场上 Soviet02 的魟鱼 < 8 就补 |
| 北边 `area_north` | 双刃直升机吊着魟鱼（`Hind_Transports` + `Hind_Passengers`） | 4 个点 `wp_soviet_hind_spawn_a..d` | 魟鱼 < 8，且这一路没有在途或撤离中的直升机 |
| 其他地方 | 双刃直升机运磁暴步兵 | 4 个点 `wp_objective_2_spawn_troops_a..d` | 磁暴步兵 < 8，同上 |

- 所有骚扰部队每帧都被命令攻击巨人 [tesla units attack]。
- 直升机先飞向最近的将军处刑者 [enroute teams move to land]。
  - 一看到玩家的单位，就用"疏散"技能放下乘客；5 秒后转进撤离队，飞到地图边缘被删掉 [hind transports drop off cargo *] [hind is evacuating *] [hind transports escape area]。
  - 300 秒都没看到玩家，也会撤。
- 小毛病：魟鱼直升机的 b/c/d 三路撤离时都并进了 `Hind_Escape_A`，而刷新条件查的是 `Hind_Escape_B/C/D`。所以这三路不等上一批撤完就可以再刷 [hind is evacuating b/c/d]。
- 魟鱼那 4 条刷兵脚本是 repeat，又没有间隔，而计数每帧只更新一次。推断：一帧里 4 个点可能同时刷，实际在场的数量会略超过 8。
- 配套的提示（都是对话）：
  - 被磁暴类单位攻击时 [f intel 10]；
  - 被 V4 攻击时 [f intel 32]；
  - 击毁第一辆 V4 时 [f kenji 02，只在健二是 AI 时]；
  - 击毁磁暴线圈时 [monitor shogun health - healed]→intel 22；
  - 血量 90% [f kenji 03，只在健二是 AI 时]、66% [intel 23]、50% [TH14，只在健二是 AI 时]、33% [intel 24]。

### 3.5 边界外的"休眠敌人" [transfer soviet forces in orange border]

- 开局在 1 号边界里，炮兵阵地和扩张点的磁暴线圈都在平民队 `PlyrCivilian/Soviets_01_Orange` 名下，不会动。
- 目标 2 亮出那一刻：
  - 整队转给 Soviet01；
  - 给两家苏军各建 2 座矿厂（a、b 给 Soviet01，d、e 给 Soviet02）；
  - Soviet01 名下全部单位交给 AI；
  - 库可夫的队伍开始自动索敌。

### 3.6 三个遭遇战 AI

| AI | 何时开 | 设置 |
|---|---|---|
| Soviet01（绿） | 开局 [enable enemy ai] | 优先打健二（20），其次打玩家（10）；基地点 `wp_soviet_green`；不修建筑、会重建；`Soviet_Base` 队交给 AI；不准造恐怖机器人 [keep ai from building terror drones]；所有苏军都不准造矿车和基地车（所以钱只出不进；矿厂会不会附带矿车未确定）。开局有没有 `SKIRMISH_AI_START` 未见，开局多久开始主动进攻未确定 |
| Soviet01 加料 | 目标 1 完成 [transfer remaining units to soviet01] | 海上剩下的伏击部队也全交给 AI |
| 健二 Player_2 | 目标 1 亮出（只在 Player_2 不是人类时）[Skirmish AI - Setup] | 基地点 `Player_2_Start`；修建筑、不重建 |
| 库可夫 Soviet02 | 目标 3 亮出，**或者**玩家/健二先拆了它任意一座建筑（入口城墙也算建筑，推断）[turn on ai for soviet 02] | 对玩家、健二优先级都是 20；造兵时考虑所有敌人；基地点 `wp_soviet_orange`；不修、会重建 |

## 4. 段

设 L₂ 为 TH02 视频的长度；D 为目标 1 完成的时刻；E 为 TH04 加 TH11 两段视频播完的时刻。

| 段 | 时间（任务秒） | 玩家要做 | 压力从哪来、怎么关掉 | 这一段教什么 |
|---|---|---|---|---|
| 开场 | 0～6 | 无（过场） | 无 | 护卫变形 |
| 1 护送 | 9.3 起刷船，到 63.3 刷完；目标 1 约在 8.5+L₂ 亮出 | 带 4～6 辆护卫跟着船流，打掉海上的潜艇、魟鱼和直升机 | 预先摆好的海军，按随机时间进入伏击位；数量有限，打光就没了 | 无新东西 |
| 过场 | D 到 D+28.6 | 无 | 无 | 将军处刑者登场 |
| 2 炮兵阵地 | 目标 2 在 D+28.6；奖励目标在 D+34.6 | 用巨人拆 4 座炮兵阵地；顺手拆 3 座地标 | 跟着巨人刷的磁暴骚扰（停不掉，只有每种兵在场 ≤ 8 的上限）；两批守炮兵阵地的部队；Soviet01 的 AI | 巨人的冲击波；桥会塌 |
| 3 库可夫 | 目标 3 在 E+2；存档在 E+1 | 巨人和健二一起拆库可夫的所有生产建筑 | 库可夫的遭遇战 AI（会重建）；骚扰照旧 | 无新东西 |
| 结尾 | 完成后 +6 秒播视频，再 +1.5 秒、+5 秒 | 无 | 无 | 胜利动画 |

```yaml
段:
  - 名字: 护送
    目标: [Escort the Transports]
    开场:
      - {镜头: Player_1_Start}
      # 电台视频 TH02 播完 2 秒后才亮目标 1 [TH - J03TH02 END]；刷船从开局 9.3 秒就开始了，不等目标
    结束: [目标 Escort the Transports 完成]     # 还要满足：亮出满 6 秒、没在播视频 [done objective 1]
  - 名字: 巨人登场
    边界: 0号（全图）
    开场:
      - 存档                                  # 目标 1 完成后 5 秒 [AUTOSAVE 2]
      - {摧毁: guards}                        # 原版是 TEAM_DELETE：直接删掉，不是打死
      - {给: {JapanMechaKing: 1}, 在: wp_executioner_spawn}   # 带三级武器升级
    结束: 段 巨人登场 + 0:22.6               # 2 + 0.1 + 10.5 + 10，从黑屏结束算起
  - 名字: 炮兵阵地
    目标: [Destroy the Artillery Batteries, Destroy the Landmarks]   # 奖励目标晚 6 秒
    结束: 目标 Destroy the Artillery Batteries 完成
  - 名字: 库可夫
    目标: [Destroy the Soviet Bases]
    开场: [存档]                              # TH11 播完后 1 秒 [AUTOSAVE 3]
```

**地图边界**：开局 `MAP_SWITCH_BORDER(1)` [SETUP - Map Boundries]，巨人登场时切到 `MAP_SWITCH_BORDER(0)`。推断 0 号是全图。整关只切一次。

**自动存档**：只有 2 次 [AUTOSAVE 2] [AUTOSAVE 3]。名叫 "AUTOSAVE 1" 的脚本其实不存档，只负责开场黑屏。

## 5. 目标

| 原版目标 | 主/奖励 | 亮出 | 完成 | 失败 | 标记 |
|---|---|---|---|---|---|
| Escort the Transports | 主 | TH02 播完 +2 秒 [show objective 1] | 到达 ≥ 6/8/10，且场上没船了 | 存活 < 6/8/10 | 每艘船（10 个） |
| Destroy the Artillery Batteries | 主 | 巨人登场 +10 秒 [show objective 2] | 4 座炮兵阵地全毁，且巨人还活着 [mechaking has destroyed the artillery]；谁拆的都算 | 巨人死了就整关失败 | 4 座炮兵阵地；镜头进入阵地区域且阵地已被发现时，阵地闪 5 下 [point out artillery *] |
| Destroy the Landmarks（Bonus_Culture_Killer） | 奖励 | 目标 2 +6 秒 [show bonus objective] | 教堂、歌剧院、城堡全毁 [done bonus objective] | 无 | 3 座地标。城堡在亮出时才转到 Soviet01 名下，玩家才打得了它；被发现、镜头进区域时闪 5 下 [flash church/opera/castle] |
| Destroy the Soviet Bases | 主 | TH11 播完 +2 秒 [show objective 3] | Soviet02 名下一座生产建筑都不剩 [soviet bases have been destroyed] | — | 5 座生产建筑、超级武器、VIP 地堡 |

- 目标 3 说的是"苏军基地"（复数），完成条件却**只看 Soviet02**，绿基地不用拆。
  - "生产建筑"指这几类：机场、兵营、建造厂、船厂、两种超级武器、战车工厂、VIP 地堡 [_OBJECT LIST_Soviet Production Structures]。
  - 库可夫会重建，所以这里数的是"现有的"，不是"开局那几座"。
- 超级武器（真空内爆弹）是目标 2 亮出后 18 秒，脚本在库可夫基地里现建的，名字是目标 3 的标记 `o_obj3_mark_f` [spawn in superweapon]。
  - 它的技能 `specialpowermagneticsingularity` 全员隐藏 [SETUP -Soviet AI powers Availability]，所以**永远不会开火**，只是个靶子。
- **奖励目标没有给任何东西**：脚本里只有 `MARK_MISSION_OBJECTIVE_COMPLETED`。战役层面有没有额外奖励未确定。
  - 它的看点是名字"文化杀手"：让巨人顺路拆掉敖德萨的地标，一种黑色幽默。

```yaml
目标:
  Escort the Transports:
    说明: 运输船存活数不能低于要求数（简单 6、普通 8、困难 10，共 10 艘）
    标记: [运输船 1..10]
    完成: [运输船.到终点 6/8/10, 运输船.场上没有了]   # 后半句我们没有
    失败: 运输船.损失 5/3/1
  Destroy the Artillery Batteries:
    标记: [artillery]
    完成: [摧毁 artillery, 还没 摧毁 executioner]
  Destroy the Landmarks:
    奖励: 是
    标记: [church, opera house, castle]
    完成: 摧毁 [church, opera house, castle]
  Destroy the Soviet Bases:
    标记: [krukov conyard, obj3 mark a..f]
    完成: Soviet02 没有任何生产建筑      # 我们只能写"摧毁 角色"，重建出来的就漏了
```

## 6. 进攻

### 第 1 段：海上伏击（全是预先摆好的单位，不新刷）

所有时间都从"开始刷船"（约 9.3 秒）算起，用的都是**随机区间**计时 [begin spawning transports]。

| 名字 | 开始 | 兵 | 做什么 | 难度 |
|---|---|---|---|---|
| 潜艇 a～f [submarine attack a..f] | a 15～30 秒；b 30～45；c 45～60；d 55～70；e 65～80；f 80～95 | 各 1 艘阿库拉（o_sub_x） | 移动到 `wp_sub_guard_x`（航线旁的伏击点），然后靠自动索敌开火 | o_sub_b、o_sub_d 在简单被删，那两条脚本就空跑 |
| 直升机 a～c [chopper attack a..c] | a 100～110；b 110～120；c 115～125 | 各 1 架双刃 | 攻击移动到 `wp_objective_1`（推断是仓库岛终点） | o_chopper_a 简单被删 |
| 原地魟鱼 | 一直在 | 5/7/9 艘 | 不受脚本指挥（这几队的 AI 已关）；推断：在原地对进入射程的船开火 | 见第 2 节 |

- 没有来源建筑，也不加码：打光就没了。
- 直升机出动时，如果玩家在仓库岛上一个单位都没有，播一句提示 intel 29 [clue to destroying choppers]。
- 第 1 段的 Soviet01 遭遇战 AI 会不会派兵来打船：未确定。它的优先级是健二 20 > 玩家 10，而船归 Japan_01，不在优先表里。

### 第 2、3 段

| 名字 | 开始 | 兵 | 从 | 打/守 | 间隔、上限 | 停止 |
|---|---|---|---|---|---|---|
| 磁暴骚扰（3 种，见 3.4） | 目标 2 亮出 | 魟鱼、直升机吊魟鱼、直升机运磁暴步兵；队伍编成未确定 | 4 组刷新点，按巨人位置选 | 巨人 | 每种 Soviet02 单位在场 < 8 就补；没有间隔 | **不停**，一直到任务结束 |
| 炮兵守军 A [spawn artillery a easy/medium/hard] | 目标 2 +10 秒 | `Artillery_Attacks_A_EASY/MEDIUM/HARD` 三套编成，各自未确定 | `wp_artillery_attack_a_spawn` | 守 `area_artillery_a_guard` | 一次性 | — |
| 炮兵守军 B | 目标 2 +60 秒 | `Artillery_Attacks_B_*` 三套 | `wp_artillery_attack_b` | 守 `area_artillery_b_guard` | 一次性 | — |
| Soviet01 遭遇战 AI | 开局（见 3.6）；目标 2 时多了 2 座矿厂和橙区单位 | AI 自己造：能造的兵有限制，不能造基洛夫、娜塔莎、天启、无畏舰、魟鱼、阿库拉，也不能造矿车、基地车、超级武器 | 绿基地 | 健二优先 | 资金 8000/10000/12000，不进账 | 拆它的生产建筑（不是目标） |
| 库可夫遭遇战 AI | 目标 3 亮出，或者先拆它一座建筑 | 同上 | 库可夫基地 | 玩家和健二同等 | 资金 0（目标 2 时给了 2 座矿厂） | 拆光生产建筑 = 赢 |
| 城区驻军 | 开局 | 6/12/18 队，编成未确定 | 城区各处 | 守在建筑里 | — | — |

```yaml
进攻:
  - 名字: 潜艇 a
    开始: 开局 + 0:24~0:39          # 我们没有随机区间
    兵: {SovietAntiNavyShipTech2: 1}  # 原版是移动预先摆好的 o_sub_a，不是新刷
    守: wp_sub_guard_a
  - 名字: 直升机 a
    开始: 开局 + 1:49~1:59
    兵: {双刃直升机: 0/1/1}
    打: wp_objective_1
  - 名字: 炮兵守军 A
    开始: 段 炮兵阵地 + 0:10
    兵: 未确定（三难度各一套）
    从: wp_artillery_attack_a_spawn
    守: area_artillery_a_guard
  - 名字: 磁暴步兵空投
    开始: 段 炮兵阵地
    兵: {双刃直升机: ?, 磁暴步兵: ?}
    从: wp_objective_2_spawn_troops_a
    打: executioner
    最多: 8                            # 原版是"在场不超过 8"，不是"总共 8 波"
```

## 7. 规则：提示、兜底、对话、存档、援军

**对话排队**
- 电台视频共用一个旗标 `f_is_movie_playing`：每段 TH 播完，留 1～5 秒缓冲才放下一段 [TH - Controller]。
- EVA/健二的语音另用一个旗标 `f_audio_is_playing`，播完就放行。
- 目标完成、胜负都要等"没在播视频"：
  - [done objective 1] 和 [Victory Condition] 都带这个条件；
  - [Lose Condition] 也要等它（f_mission_failed 置上之后，还要等视频播完）。

**由事件触发的对话**（只列和玩法有关的）

| 触发 | 播什么 | 脚本 |
|---|---|---|
| 目标 1 亮出 | intel 19（只在困难播） | [show objective 1] [f intel 19] `[--H]` |
| 任意一艘船 ≤ 60% 血 | intel 20 + 雷达事件 | [if transport attacked *] |
| 船损失过多（失败时） | intel 21（只在困难播） | [p1 loses his transports] |
| 第一艘潜艇出动 | intel 28 | [submarine attack a] |
| 刷船 80 秒后 | TH09 | [begin spawning transports] |
| 第 8 艘船到达 +1 秒 | TH06 | [arrive transport h] |
| 巨人登场 +25 秒 | TH10 → 5 秒后 intel 30 → intel 31 | [spawn in mechaking] [TH - J03TH10 END] |
| 巨人登场 +3 秒（健二是 AI 时） | 健二 01 | [end mechaking intro and give control] |
| 巨人击杀 ≥ 5 个苏军单位 | 换"巨人狂暴"音乐，15 秒后 TH08 | [shogun music] |
| 炮兵阵地 c 或 d 被毁（合作模式才播） | intel 25 | [artillery destroyed c or d] [f intel 25] |
| 攻击库可夫的入口城墙，或拆它的建筑，或进入它的基地区域 | TH01 → intel 33 | [TH - J03TH01 - Play] |
| 目标 2 完成 | TH04 → TH11 → 目标 3 | [done objective 2] |
| 巨人血量 90/66/50/33%；被磁暴或 V4 打；击杀 V4、磁暴线圈 | 各一句 | 见 3.4 |

- 写了但永远不会触发的对话：intel 08、18、26、27，TH07、TH12、TH13（触发它们的旗标或计时器没有任何脚本去置，或者脚本开局是关着的）。
- `f_th_01`（库可夫建造厂被毁时置上）、`f_secure_expansion_a/b/c`（炮兵阵地被拆后置上，推断本来想让健二去扩张）也是只写不读。

**教学**（全是针对巨人的）
- 目标 2 亮出 +6 秒，如果玩家还没选中过巨人，就在巨人头上挂 15 秒的介绍提示框 [put infobox on mechaking if not controlled]；选中过就不挂 [disable infobox script]。
- 选中巨人时，它的冲击波技能按钮闪 15 秒 [highlight mechaking special power] [stop flashing mk power]。
- 选中巨人 15 秒后，挂一个讲冲击波的提示框；玩家已经放过冲击波，就不挂 [put infobox on mechaking special ability] [disable special power infobox script]。
- 合作模式下，人类健二造出能升级的建筑时，提示可以升科技 [if p2 built upgradeble struct]。
- 炮兵阵地、地标：镜头扫到、而且已经被发现时闪 5 下（见第 5 节）。

**兜底**
- 不送援军，也没有"快输了"的提示。
- 护送不等人；损失容忍度按难度定，困难零容忍。
- 健二（AI）被全灭时，本来写着"把它剩下的东西转给玩家"，但这一条动作被禁用了（`+00000000`）。实际只是关掉共享资源，取消它的合作 AI 资格 [if coop ai dies]。
- 只有合作模式里人类健二的基地没了才判负；AI 健二全灭不判负 [p2 loses base]。
- 苏军不能造矿车，钱会花光；目标 2 补了 2 座矿厂。推断：这是在给敌人兜底，让后半场还造得出兵（矿厂会不会自带矿车未确定）。

**援军**：只有第 2 段开头那一台将军处刑者（替换掉护卫部队）。玩家的秘密协议点数也是这时才给 [show objective 2]。

**自动存档**：2 次，见第 4 节。

## 8. 输赢

```yaml
胜利: 目标 Destroy the Soviet Bases 完成
# 然后：巨人设为无敌 → +6 秒双方设为中立、关输入、镜头跟着巨人 → 播 J07TH03（借第 7 关库可夫战败的视频）
#       → +1.5 秒巨人播庆祝动作 → +5 秒、没在播视频时才算赢
#       [done objective 3] [all objectives accounted for] [mk celebrates] [Victory Condition (OVERRIDE ME)]
失败:
  - {当: 运输船.损失 5/3/1, 原因: 运输船被击沉}     # 先黑屏 1 秒，镜头切到沉船处，5 秒后判负 [transports death cine begins]
  - {当: 运输船对不上账, 原因: 无}                 # 直接判负，不播过场 [double check transports count B]
  - {当: [段 炮兵阵地, 摧毁 executioner], 原因: 将军处刑者被毁}   # 播 TH03 后判负 [p1 loses mechaking]
  - {当: 合作模式下人类健二没有基地了, 原因: 健二的基地被毁}       # 播 TH05 后判负 [p2 loses base]
```

- 第 1 段巨人还没出来，巨人那条失败条件带 `f_objective_2` 门槛，不会误判。
- 第 3 段之后巨人仍然可以被打死而判负。完成目标 3 那一刻才给它加无敌。

## 9. 难度

| 项 | 简单 | 普通 | 困难 | 脚本 |
|---|---|---|---|---|
| 健二资金 | 12000 | 10000 | 8000 | [SETUP - Starting Money *] |
| Soviet01 资金 | 8000 | 10000 | 12000 | 同上 |
| 玩家护卫 | 6 | 4 | 4 | [delete units for medium and hard] |
| 要求送到 / 可以丢几艘 | 6 / 4 | 8 / 2 | 10 / 0 | [define transport totals *] |
| 海上伏击：魟鱼 / 阿库拉 / 双刃 | 5/4/2 | 7/6/3 | 9/6/3 | [delete units for easy] [delete units for medium] |
| 城区驻军队数 | 6 | 12 | 18 | [spawn soviet garrisons *] 的 `[-NH]` `[--H]` |
| 库可夫防空炮 | 4 | 6 | 6 | [delete units for easy] |
| 炮兵守军 A/B | EASY 编成 | MEDIUM 编成 | HARD 编成 | [spawn artillery a/b easy/medium/hard] |
| 对话 | 少了 intel 19、21 | 少了 intel 19、21 | 多 intel 19、21 | [f intel 19] [f intel 21] 只开困难；[f intel 26] 只开简单、普通，但永远不会触发 |

- 不变的：分段结构，所有计时（刷船间隔、伏击时间、过场时长、骚扰规则），骚扰上限 8，船的数量 10。
- 名字和开关一致，这一关没发现标错（对照 map-language 第 7 节"名字和开关要一起检查"）。
  - `Delete_On_Medium` 这个队简单保留、普通删掉，看起来反直觉。但它和 `Delete_On_Easy` 是成对摆的（见第 2 节），推断是故意的：让同一个位置在简单、普通各有 1 艘魟鱼。

## 10. 我们的词表写不出的

按重要程度排。

1. **一股一股发出去的护送流，而不是一个车队** [begin spawning transports] [spawn transport a..j]
   - 原版：10 个护送对象，每 6 秒刷一艘；各自沿固定路点链走；到终点就删掉、计数。
   - 我们的"车队"机关：固定 3 辆、开局摆好、一起出发；数量、间隔、路线都写不了。
2. **护送对象归第三方，而且不停不等** [spawn transport *]
   - 原版：运输船归 Japan_01，跟着路点直接开到底。
   - 我们的车队：归"我"，靠每 3 秒重新下一次命令推着走，还有停下、继续。"一次给完路线、谁也别管"的模式写不了；"第三方友军阵营"也写不了。`其他` 里的一方开局是中立，不是友军。
3. **损失和要求按难度定，友军误伤算损失，还要等场上清空才算完成** [define transport totals *] [track transports] [all parts delivered]
   - `车队.损失 n`、`车队.到终点 n` 能按难度写数，但车只有 3 辆，"6/8/10 中的 10"写不出。
   - "场上已经没有护送对象了"这个条件没有。
   - "账对不上就直接判负"的兜底也没有。
4. **随机时间** [begin spawning transports] 的 `SET_RANDOM_MSEC_TIMER`
   - 原版：伏击在一个区间里随机出动，例如 15～30 秒。
   - 我们的 `开始` 只有确定的时间。
5. **调动预先摆好的单位** [submarine attack *] [chopper attack *]
   - 原版：让地图上已有的某艘潜艇在某个时刻移动到伏击点，或者攻击移动到某处。玩家能提前把它打掉，这一路进攻就没了。
   - 我们的 `进攻` 只会新刷兵；开局部队只有 `守`，没有"到点出动"。
6. **按目标的位置换兵种** [evaluate spawning of tesla boats / hinds and tesla boats / hinds and tesla troopers]
   - 原版：同一路骚扰按巨人在海里、北边还是其他地方，刷不同的兵，从不同的点来。
   - 我们的条件里有 `进入 <地点>`，但它看的是玩家任意单位，不是某个角色，而且只成立一次，不能在两个状态之间反复切换。
7. **按在场数补兵** [spawn tesla boats if needed *] 的 `c_objective_2_tboat_max = 8`
   - 原版：场上少于 8 就补，没有固定间隔，也没有总波数。
   - 我们的 `最多` 是波数上限，`每隔` 是固定间隔。
8. **直升机空投** [spawn hinds carrying * if needed] [hind transports drop off *] [hind is evacuating *] [hind transports escape area]
   - 原版：运输机把兵装进去，看到玩家的单位就卸兵，5 秒后飞走，到地图边缘删掉。
   - 我们的 `进攻.从` 只能让兵从一个地点直接出现。
9. **英雄单位替换整支部队，外加专门的失败条件** [get rid of old p1 units] [spawn in mechaking] [p1 loses mechaking]
   - `给` 能给，`摧毁 <角色>` 能拆。
   - 写不出的：直接删掉（不是打死）；给单位加升级状态（三级武器）；"英雄死了就输"要等某段开始以后才生效（可以用 `[段 X, 摧毁 Y]` 近似）。
10. **踩到就塌的桥** [if bridge a..f stepped into by mechaking]
    - 条件是"某个角色进入某个区域"，动作是"摧毁一座中立的桥"。
    - 我们的 `进入` 不分角色；桥也不是我们的角色。
11. **边界外的休眠敌人：划到平民名下，扩边界时转给敌方 AI** [transfer soviet forces in orange border]
    - `其他` 加 `翻脸` 能近似"开局中立、后来变敌"。
    - 写不出的："转给敌方主阵营，并交给它的 AI"；`建造`（脚本现建矿厂、超级武器）。
12. **遭遇战 AI**（`SKIRMISH_AI_*`）[enable enemy ai] [turn on ai for soviet 02] [Skirmish AI - Setup]
    - 写不出的：基地点、敌人优先级、修不修、重建开关；"拆它一座建筑就提前唤醒"；限制 AI 能造什么。
    - 我们的压力全靠写死的 `进攻`。
13. **友军 AI 指挥官**：健二有自己的基地、资金、秘密协议点数，到点启动 AI。我们只有"我"和"敌"两个真正的玩家。
14. **"一种建筑都不剩"的胜利条件** [soviet bases have been destroyed] [_OBJECT LIST_Soviet Production Structures]
    - 原版：按建筑类别数（敌人会重建）。
    - 我们只有 `摧毁 <角色>`（重建出来的不算）和 `敌人清空 <地点>`（数的是能打的东西，不数生产建筑）。
15. **针对单位的教学 UI** [put infobox on mechaking *] [highlight mechaking special power] [point out artillery *] [flash church]
    - 写不出的动作：挂在单位头上的提示框，按钮闪烁，物体闪烁，雷达事件点。
    - 写不出的条件："选中某个单位"、"用过某个技能"、"镜头进入区域"、"已经被发现"。
    - 我们只有通报、镜头、目标标记。
16. **按"被谁打 / 打死了什么"触发** [f intel 10] [f intel 32] [f kenji 02] [monitor shogun health - healed] [shogun music]
    - 例如被磁暴类单位攻击、击杀 ≥ 5 个苏军单位。我们只有 `攻击 <角色>`（玩家打了它）和 `血量 <角色> < n`。血量这一档写得出。
17. **对话排队，目标和胜负等对话播完** [TH - Controller] [done objective 1] [Victory Condition (OVERRIDE ME)]
    - 我们的通报、目标、胜负都是到点就执行，没有"等上一句播完"。
18. **只在某个难度生效的规则**（例如 intel 19、21 只在困难播）
    - 我们的难度只能改数，不能开关一条规则。
19. **结尾仪式**：设无敌、双方中立、关输入、镜头跟随、播放模型动作，然后才判胜 [all objectives accounted for] [mk celebrates]。我们的 `胜利` 是立即生效的。
20. 小项：
    - 秘密协议点数 [set maximum player power points] [show objective 2]；
    - 隐藏超级武器的技能 [SETUP -Soviet AI powers Availability]；
    - 限制建造和科技 [P1-Japan Unit Restrictions 等]；
    - 失败前的过场：黑屏，镜头切到沉船 [transports death cine begins]；
    - 地图外放雷达站给小地图；
    - 合作模式和单人的分支 [PLAYER_IS_HUMAN_OR_AI_PERSONALITY]。

## 11. 和我们 A4 比

只写有实质的差别。

1. **护送规则相反**
   - 原版：护送对象不等人，10 艘一股股地流过去；容错按难度定（4/2/0）；整段很短（约 1 分钟刷完，2 分钟左右走完，具体看船速，未确定）。
   - A4：3 辆一起走，有 4:00/3:00/2:30 的准备时间；港口出事会停下来等，最多等 4 分钟；容错固定是 1 辆。
   - 原版的难点在"跟不上就丢船"，A4 的难点在"提前布置"。
2. **压力的来源和关法**
   - 原版护送段：压力全是预先摆在航线两旁、按随机时间出动的有限海空单位，没有来源建筑；把它们先找出来打掉就是解法。
   - A4："冰雕里的兵"是可以封住的，北营靠拆兵营关掉，都是"有来源、拆了就停"。
   - 原版后半段的骚扰**永远停不掉**，只是在场不超过 8，靠巨人自身的强度去扛。持续压力还来自两个遭遇战 AI（库可夫拆它一座建筑就提前醒）。A4 没有遭遇战 AI。
3. **一关之内换三次玩法，教学集中在新单位**
   - 原版：护送用的部队在第 2 段被直接删掉，换成一台英雄巨人；第 3 段再加上友军 AI 拆基地。教学全部围绕巨人：提示框、技能按钮闪烁、按血量分档的对话、"桥会塌"。符合第 7 节"新单位：过场交给你 → 马上来专门考它的敌人"（磁暴类骚扰正好克巨人）。
   - A4：4 段都围着同一个车队，教冰幕工兵（演示冰雕 + 通报）。两边都是"一关教一个新东西"，但原版把护送当成新单位登场前的铺垫，A4 把护送当主体。
4. **奖励目标**
   - 原版：拆地标，没有实际奖励，纯黑色幽默；地标摆在巨人横冲直撞的路上，顺手就能拆。
   - A4：两个奖励目标都改变玩法（封口、断北营兵源）。
5. **兜底**
   - 原版：不送援军，不等人，困难丢 1 艘船就输；输之前给一个镜头切到沉船的过场；还有防漏算的直接判负。
   - A4：工兵死光了补 1 个，港口超时车队自己走。原版这一关的兜底比 A4 严得多。
6. **基地和经济**
   - 原版：玩家全程 0 元、没有基地，生产交给友军 AI 健二。
   - A4：给了玩家一座小基地和 5000/3000/2000 的钱。
