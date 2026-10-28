# 原版 A08 哈瓦那 · 反推策划案

来源：`work/retailref/camp_a08_havana_rao.txt`（脚本全文）、`work/retailref/camp_a08_havana_rao.json`（物体、目标）、`work/mapstudy/camp_a08_havana_rao.png`（俯视图）。文中【脚本名】是原版脚本名，作为证据。

**读法说明**
- yaml 块按我们 `docs/story/plans/README.md` 的写法写，只为方便对照，不会被编译。地点名是我按原版路点、物体起的描述性名字（例如 `soccer stadium`），原版地图没有公开这些名字。
- 原版的 `SET_MILLISECOND_TIMER` 数值单位是秒（例如【Introduction - Camera Pan】28.0 秒后存档，和开场节奏吻合）。`SET_TIMER` 是帧，这一关只在开场闪烁特效里用到（5 帧、35 帧），和玩法无关。
- 比较运算的编码：0 小于、1 小于等于、2 等于、3 大于等于、4 大于（由【Objective 4 - Objective Complete】`COUNTER(KLF Remaining, 1, 0)` 即"剩余 ≤ 0"、【Bonus Objective 1 - Complete】`(3, 10)` 即"≥ 10 个"反推，前后一致）。
- 导出文本只显示单个脚本的开关，**不显示脚本组（ScriptGroup）自己的开关**。不少组明显是开局关着、由 `ENABLE_SCRIPT('<组名>')` 打开的（例如"Kirovs - Final Countdown"组：组要是开着，里面的脚本开局就会触发）。凡是依赖组开关的结论都标了"推断"。
- 这是一张**合作图**：`Player_1` 是玩家；`Player_2` 是吉尔斯少校，单人时由 AI 扮演（`PLAYER_IS_HUMAN_OR_AI_PERSONALITY('Player_2','Human')` 取反的分支就是单人分支）。下文默认写单人流程，只在双人才有的地方注明"合作"。
- 敌方有 4 个玩家槽：Soviet01 由脚本控制（第一段的苏军、基洛夫、脚本小队）；Soviet02 是陆军遭遇战 AI（东北基地）；Soviet03 是海军遭遇战 AI（东北角船坞）；Soviet04 只拥有 5 座发射场（开局对玩家中立）。

## 1. 定位

- 一句话：先跟着吉尔斯的幻影坦克混进哈瓦那、用间谍收买苏军，找到并拆掉苏军前哨；然后拿到基地，拆掉 5 座伪装成体育场馆的基洛夫发射场，任何一架基洛夫飞出地图边就输。
- 类型：两段式。第一段是潜入 / 护送（没有基地，只有 2 个间谍、2 条警犬和买来的苏军）；第二段是建基地 + 拦截。
- 教玩家：
  - 第一段：间谍的收买能力（花钱换敌人的兵），用幻影坦克的伪装躲开巡逻。
  - 第二段：防空拦截要覆盖全图（基洛夫会往 8 个方向随机飞），同时要分兵拆发射场；拆得越快，剩下的发射场越凶。
- 剧情钩子：苏军把基洛夫藏在哈瓦那的体育场、拳击馆、游泳馆里，要飞去轰炸美国。

```yaml
关卡: a08
名字: 哈瓦那
一句话: 跟幻影坦克混进城、收买苏军，再拆掉五座藏着基洛夫的体育场；一架基洛夫飞出哈瓦那就输
地图: camp_a08_havana_rao
阵营: {我: 盟军, 敌: 苏联, 其他: {发射场: 苏联}}   # Soviet04：开局中立、无敌
时长: 35            # 估计：第一段约 8～12 分钟，第二段强度表一直排到 25 分钟（普通），见第 4 节
边界: part one      # 原版 MAP_SWITCH_BORDER(1)【Map Setup - Map Border 1】
```

## 2. 开局

**玩家**（第一段）：
- 2 个间谍（模板 AlliedInfiltrationInfantry，名字却叫"Player01 - Destroyer 1/2"）、2 条警犬。开场时装在一架 A08 专用世纪运输机里，空投到西南角的空降点后才归玩家【Introduction - Setup】【Introduction - Transfer Troops】。
- 吉尔斯的幻影坦克（A08_SpecialMirageTank，Player_2 的）开局在地图外，6 秒后超时空闪光、传送进来【AI - 00 - Chrono Effect】【AI - 00 - Teleport Tank】。它不自动开火、遭遇战 AI 不打它【Player02 - Setup - Mirage Tank】。
- 第一段不能建基地，只能造兵（但手里没有生产建筑），所以钱实际是**收买用的预算**【Player01 - Permissions - Part 1 Restrictions】。
- 超时空裂缝、超时空互换、3 级时间炸弹被锁【Allied Special Power Restrictions】；超级武器全体禁建【Map Setup - Build Restriction】。

**玩家**（第二段开头交付，见第 4 节）：基地车自动展开 + 2 座矿厂 + 2 座电厂，外加一笔钱【Split - Move MCV】【Split - Setup Base】【Player01 - Setup - Money - Part 2*】。

**敌人摆在哪**（坐标是地图单位，地图 6000×6000，东为 x、北为 y）：
- 第一段沿路（Soviet01，城市中部偏西，大约 x 1600～2900、y 1700～2900）：
  - 13 个磁暴步兵（TEAM - Tesla Troopers）、10 个动员兵、2 个精英磁暴步兵来回巡逻【Tesla Elite - Group A - Start Patrol】；
  - 可收买的 "UNIT - Bribed 01～10"：3 个苏军工程师 + 7 个防空步兵；另有 2 个短路放电的磁暴步兵、5 个列队敬礼的兵、1 辆镰刀（一被发现就跳走【Sickle - Jump】）、几头战熊（两头互咬取乐【Bear Fight - *】）；
  - 一座起重机（"Salvage Yard"）：2～4 辆只剩 5% 血的铁锤坦克被开过去修【Salvage - *】，纯气氛；
  - 2 辆受损天启坦克守在去基地的路上（TEAM - Damaged Apocs）。
- 第一段终点：苏军前哨基地（Soviet01 "TEAM - Base"，西北，约 x 1865～2374、y 3335～3717）：建造厂、兵营、战车工厂、8 座电厂，外加 2 辆铁锤（TEAM - Additional Opposition）和 2 个防空步兵。
- 5 座发射场（Soviet04，开局无敌、中立【Objective 1 - Invincible Stadiums】）：

  | 名字 | 原模板 | 位置 | 说明 |
  |---|---|---|---|
  | KLF 1 | 足球场 HV_SoccerStadium01 | (2524, 2038) 中西 | 第一段就在玩家走过的城里 |
  | KLF 2 | 棒球场 HV_BBallField01 | (1901, 3671) 西北 | 紧挨苏军前哨基地 |
  | KLF 4 | 拳击馆 HV_Boxing | (3120, 3111) 正中 | |
  | KLF 3 | 棒球场 HV_BBallField02 | (4295, 3609) 东北 | 在 Soviet02 陆军基地里 |
  | KLF 5 | 游泳馆 HV_SwimmingPool | (5424, 565) 东南小岛 | 有一队守军（2 牛蛙、3 铁锤、1 V4，TEAM - Pool Defense Operation） |

- 第二段才动起来的：
  - Soviet02 陆军基地（东北，中心约 (4179, 3121)）：建造厂、兵营、战车工厂、机场、5 电厂、4 矿厂、10 哨戒炮、7 防空炮、7 铁锤、4 米格；另有 2 座超级反应堆和 2 座战斗实验室作为"Static Placed Units"摆在附近，按时移交给 AI（第 6 节）。
  - Soviet03 海军基地（东北角，中心约 (4724, 4418)）：建造厂、2 船坞、2 电厂、2 磁暴线圈、2 矿厂。
  - 脚本小队：清场队（2 战熊、2 镰刀、2 天启）、报复 1 队（3 镰刀）、报复 2 队（2 天启）、空投队（8 动员兵 + 2 牛蛙）、矿区巡逻（2 海蝎）、磁暴船（2 海蝎）、轰击舰队（无畏舰 + 海蝎，在地图外）。

```yaml
开局:
  资金: 10000/7000/5000          # Player01 - Setup - Money - Part 1 (Easy)/(无后缀)/(Hard)；第一段只用来收买
  部队:
    - {单位: 间谍, 数量: 2, 在: drop zone, 角色: spy}         # 运输机空投后才归玩家
    - {单位: 警犬, 数量: 2, 在: drop zone, 角色: dog}
    - {单位: 幻影坦克, 在: drop zone, 阵营: 吉尔斯, 角色: giles}  # Player_2；词表没有"友军指挥官"一方
    - {单位: 工程师, 数量: 3, 在: city west, 阵营: 敌, 角色: bribable engineer}   # 苏军工程师，可收买
    - {单位: 防空步兵, 数量: 7, 在: city west, 阵营: 敌, 角色: bribable flak}
    - {单位: 磁暴步兵, 数量: 13, 在: city patrol, 阵营: 敌}
    - {单位: 动员兵, 数量: 10, 在: city patrol, 阵营: 敌}
    - {单位: 天启坦克, 数量: 2, 在: stadium road, 阵营: 敌, 角色: damaged apoc}
    - {单位: 建造厂, 在: forward base, 阵营: 敌, 角色: soviet conyard}
    - {单位: 兵营, 在: forward base, 阵营: 敌, 角色: soviet barracks}
    - {单位: 战车工厂, 在: forward base, 阵营: 敌, 角色: soviet factory}
    - {单位: 铁锤坦克, 数量: 2, 在: forward base, 阵营: 敌, 角色: extra opposition}
    - {单位: HV_SoccerStadium01, 在: soccer stadium, 阵营: 发射场, 角色: klf 1}
    - {单位: HV_BBallField01, 在: baseball 1, 阵营: 发射场, 角色: klf 2}
    - {单位: HV_BBallField02, 在: baseball 2, 阵营: 发射场, 角色: klf 3}
    - {单位: HV_Boxing, 在: boxing gym, 阵营: 发射场, 角色: klf 4}
    - {单位: HV_SwimmingPool, 在: swimming pool, 阵营: 发射场, 角色: klf 5}
```

## 3. 机关

### 3.1 基洛夫发射场（这一关的核心）

**谁能发射、一次几架**
- 5 座发射场各有一架"自己的"基洛夫：KLF n 只放 "UNIT - Kirov 0n"，而且**这一架还活着就不放下一架**（每个发射脚本都带 `NAMED_NOT_DESTROYED('UNIT - Kirov 0n')` 取反）【Kirovs - Controller - Launch KLF1/2/3】【Kirovs - Controller - Launch KLF4 - A…G】【… KLF5 - A…F】。所以同一时间天上最多 5 架（加上最后一座的 3 架，见下）。
- 基洛夫模板是 `sovietbomberaircraft_special`，生成时设了 `NO_ATTACK`（不投弹，只管逃）、`SHROUD_REVEAL_TO_ALL`（全图可见）、挂上"别让基洛夫飞出哈瓦那"的目标标记，并发雷达事件；之后每帧都发一次雷达事件【Kirovs - KLF1 - Kirov 1 Launch】【… Pinger】。例外：过场里放的第一架 Kirov 01 没设 `NO_ATTACK`【Split - Spawn Kirov】。

**发射场 1～3：轮流定时放**
1. 第二段开始时把"选发射场"计时器设为 125 秒，并打开屏幕上的"天上的基洛夫"计数器【Kirovs - Controller - Setup Launch】【Kirovs - Controller - Update Display】。
2. 计时到点：在 1～3 里随机挑一座【Kirovs - Controller - Determine KLF】（`SET_RANDOM_COUNTER(…, 1, 3)`）。挑中的那座已毁、或者它的基洛夫还在天上，就顺着 ELSE 链换下一座，三座都不行就重新掷（推断：计时器到点后一直算"到点"，所以会每帧重掷，直到某座可用）。
3. 放出后重新武装"倒计时"脚本：按当前**强度**（3.2）随机取下一次间隔【Kirovs - Controller - Reactivate Countdowns】【Kirovs - Controller - Countdown Light/Medium/…】。

间隔表（秒，随机区间，`SET_RANDOM_MSEC_TIMER`）：

| 强度 | 简单表 | 普通表 | 困难表 |
|---|---|---|---|
| 轻 Light | 250～300 | 120～150 | 75～100 |
| 中 Medium | 200～250 | 90～120 | 45～60 |
| 高 High | 150～200 | 45～60 | 30～45 |
| 严重 Severe | 100～150 | 20～30 | 15～30 |
| 极端 Extreme | 50～100 | 15～20 | 10～15 |

**难度标记的问题（重要，未确定实际效果）**：三张表的脚本【Kirovs - Controller - Countdown … (Easy)】【… Countdown …】【… (Hard)】都**没有难度标记**，三个难度都生效，而且写的是同一个计时器。再加上【Kirovs - Controller - Reactivate Countdowns】每次发射后只重新武装了**普通表**的五个脚本（通过【Kirovs - Controller - Normal Countdowns - Reactivate】），简单表和困难表的单个脚本是一次性的、触发过就不再武装。所以推断：
- 每次强度升一档的那一刻，三张表各写一次计时器，同一帧里最后写的那张生效（按脚本顺序是困难表）；
- 之后每次发射后的间隔都走普通表，不分难度。
- 也就是说这一关的发射节奏**基本不随难度变**；随难度变的只有"强度什么时候升档"（3.2）。这和 map-language.md 第 7 节说的"哈瓦那三份发射节奏表一个开关都没开"一致。

**发射场 4、5：被事件和时间触发**
- "选发射场"计时器第一次到点时（约第二段 +80～155 秒，取决于哪张表最后写入计时器，未确定），设一组长计时器【Kirovs - Controller - Setup 4 & 5】：KLF4 +240 秒、KLF5 +320 秒、两座都 +900 秒和 +1300 秒。
- KLF 4 放基洛夫的时机【Kirovs - Controller - Launch KLF4 - A…G】：
  - 剩余发射场 ≤ 4、≤ 3、≤ 2 时各放一次（三个难度）；≤ 1 时再放一次（只普通、困难）；
  - +240 秒放一次（只普通、困难）；
  - +900 秒、+1300 秒以后变成 repeat：只要它的基洛夫没了就立刻再放。
- KLF 5【Kirovs - Controller - Launch KLF5 - A…F】：剩余 ≤ 3、≤ 2、≤ 1 各一次；+320 秒一次；+900 / +1300 秒以后同样无限续放。三个难度都一样。
- 所以**玩家每拆一座发射场，还活着的 4 号、5 号就各放一架**——这才是"拆一座、对面报复"里最直接的那一下。

**最后一座：连放三架**
- 剩余发射场 = 1 时打开"最后倒计时"组【Kirovs - Controller - Setup Final Countdown】，播 Oleg 嘲讽（TH13）。
- 还活着的那座 10 秒后放 Kirov 06，再隔 10 秒放 07、再隔 10 秒放 08；每架出生 10 秒后分别飞向西、北、南三个出口【Kirovs - Final Countdown - Launch KLFn】【Kirovs - Final Countdown - KLFn - Launch A/B/C】【… A/B/C Moves】。这三架也是 `NO_ATTACK`，有语音。

**从哪飞、走什么航线**
- 出生点：KLF 1～3 用各自的 "WP - Kirov Spawn Point n TEST"（注意编号是交叉的：KLF1 用 Spawn Point 2，KLF2 用 Spawn Point 1）；KLF4、5 直接在拳击馆、游泳馆的揭示路点上出生。
- 出生后悬停 15 秒（"Move Delay"），然后**直线**飞向一个随机出口路点【Kirovs - KLFn - Kirov n Go …】。没有绕行航线；只有剧本里第一架 Kirov 03 先到"Kirov Move A"再去南出口【Objective 4 - KLF3 - Move A】。
- 出口方向是掷 1～8（KLF5 掷 1～5），但脚本名和实际路点对不上，实际分布：

  | 发射场 | 实际飞向的出口（次数 / 掷骰面数） |
  |---|---|
  | KLF 1、2、4 | 西 2、北 2、西北 1、南 1、东南 1、西南 1（/8）。"Go East"实际去西、"Go Northeast"实际去北 |
  | KLF 3 | 西北 2、西南 2、北 1、南 1、东南 1、西 1（/8） |
  | KLF 5 | 北 2、西 2、西北 1（/5） |

  没有一架会去东或东北出口，但失败检查里有这两块区域。
- 速度：未确定（脚本里没有，基洛夫模板的移动速度这里查不到），所以"从发射到逃出要多少秒"无法从脚本算出。

**飞到哪算逃走**
- 地图边上有 8 块 "AREA - Kirov Exit E/N/NE/NW/S/SE/SW/W" 触发区，任何一架这种基洛夫进去就设"被基洛夫打败"旗标，立刻走失败流程【Kirovs - Controller - Kirov Leaves Havana】（repeat，开局就开着）。区域的具体位置不在导出数据里，未确定。

**预警**
- 发射瞬间：EVA 语音（MA08_AlliedIntel24 / 25 交替），雷达事件，目标标记挂到这架上，屏幕计数"天上的基洛夫"+1【Kirovs - KLFn - Kirov n Launch】。
- 悬停 15 秒：这就是玩家的反应窗口。
- 接近边界：另有 8 块 "AREA - Kirov Exit Warning - *" 预警区，进去就雷达提示 + 语音"基洛夫要飞出北面/东面……"【Kirovs - Warning - N/NE/…】。**每个方向只报一次**（这些脚本是一次性的）。
- 音乐：有基洛夫进预警区就切"逃跑中"音乐；预警区里全空了切"拦截成功"音乐并播 TH03，5 秒后恢复动态音乐，循环【Kirov Music - Escaping/Intercepted/Resume Dynamic System】。
- **没有屏幕倒计时**。唯一的屏幕元素是"天上的基洛夫"计数器（`DISPLAY_COUNTER`）。原版有一个"Seconds Counter"倒计时 1200 秒的脚本，但关着、没人打开【XLevel Hack - Seconds Counter】。

### 3.2 强度（Intensity）

一个 6 档的全局等级，只用来决定发射场 1～3 的发射间隔（3.1）。每档是一个旗标，升档的脚本把其他档的旗标全清零【Intensity - 00 - None … 05 - Extreme】。

| 档 | 由时间触发（第二段开始后，秒） 简单 / 普通 / 困难 | 由进度触发 |
|---|---|---|
| 轻 | 5 / 5 / 5 | — |
| 中 | 1200 / 600 / 250 | 剩余发射场 = 4 |
| 高 | 1800 / 900 / 500 | 剩余 = 3 |
| 严重 | 2400 / 1200 / 750 | 剩余 = 2 |
| 极端 | 3000 / 1500 / 1000 | — |

证据【Intensity - 00 - Set Timers】[-N-]、【… (Hard)】[--H]、【… (Easy)】[E--]、【Intensity - 02 - Medium】等。

要点：
- 原版的"每拆一座强度升一级"准确说是：拆到剩 4、3、2 座时分别跳到中、高、严重；最后两座被拆不再升档（剩 1 座时改由"连放三架"接管）。
- 按时间也会升，哪个先到算哪个——龟缩也会越来越凶。
- **会倒退**：每档脚本都是一次性的，谁后触发谁说了算。例如普通难度玩家 600 秒前就拆到剩 3 座（强度=高），到 600 秒"中"的计时器到点，强度又被拉回"中"，直到 900 秒才回到"高"。这多半是原版的疏忽。

### 3.3 "调查哈瓦那"：跟着幻影坦克走

第一段的目标 1、2 都是**吉尔斯的幻影坦克**走进区域才完成，不是玩家：
- 目标 1"调查哈瓦那的苏军活动"：幻影坦克进 "AREA - Objective 1 Zone"【Objective 1 - Complete】。
- 目标 2"找到苏军基地"：幻影坦克进 "AREA - Objective 2 Zone"【Objective 2 - Complete】。

幻影坦克（单人时 AI 开）按一串路点 A1 → A → B → C → D 走，每一步的触发条件不一样【AI - Mirage Tank - *】：
- A1 → A：幻影坦克到"Stay Close"区域后，等 5 秒，**或者**玩家的任一个间谍 / 警犬也走进这个区域，就继续（伙伴等玩家，但最多等 5 秒）【AI - Mirage Tank - Go to A2】。
- A → B：幻影坦克和玩家任一单位都在目标 1 区域里（目标 1 完成后）【AI - Mirage Tank - Go to B】。
- B → C：路被敬礼的苏军挡住，吉尔斯提示"收买他们"，弹出收买的信息框【AI - Mirage Tank - C is Blocked】【AI - Mirage Tank - Bribe Hint】；挡路的 5 个兵被收买 3 个（Salute 01～03 归玩家）、或者被全打死、或者整队没了，就继续【AI - Mirage Tank - Go to C】。
- C → D 是一个分支（见 3.5）。
- 到目标 2 区域：吉尔斯说"我就知道"，关掉伪装场，开火打建造厂、兵营、战车工厂【AI - Mirage Tank - I Knew It】【… Fire】。

### 3.4 "招募苏军"：间谍收买

- 收买本身是间谍的技能（花钱），脚本不管；脚本只做三件事：
  1. 被收买的单位一归玩家就改成"停火"姿态，免得暴露伪装【Bribe - Hold Fire 01～10】【Bribe - Tesla 01～04】【Bribe - Sickle】【Bribe - Salute01～05】【Bribe - Fighting Bear01/02】【Bribe - Flak Trooper Base 01/02】。
  2. 奖励目标在"玩家第一次看见可收买的防空步兵（Bribed 04 / 05）"或"幻影坦克到维修场"时亮出，2 秒后在一个敬礼的动员兵头上弹 15 秒信息框【Bonus Objective 1 - Setup/Reveal/Infobox 01】。
  3. 完成条件：玩家同时拥有 ≥ 10 个"苏军全部单位"列表里的单位（`PLAYER_HAS_OBJECT_COMPARISON('Player_1', 3, 10, '_object list_soviet all units')`）【Bonus Objective 1 - Complete】。是"同时拥有"，被打死了要再买。
- 奖励：脚本里**没有发东西**——奖励就是这 10 个苏军本身，而且它们决定第一段后半的分支（3.5）。
- 第一段结束时这些兵还在，但第二段开始 15 秒后有一队清场队（2 战熊、2 镰刀、2 天启）攻击移动到 "WP - Slaughter Players Forces"【Submission Cleanup - Attack Now】——从名字看是去收拾玩家残留在城里的部队。

### 3.5 依玩家兵力分支（第一段）

- **打还是绕**：幻影坦克到 "Migs Flyby B" 附近发现 2 辆受损天启。如果玩家此时有 ≥ 4 个防空步兵 **且** ≥ 2 个磁暴步兵（都是买来的），吉尔斯解除伪装开打，玩家帮忙；否则吉尔斯倒车、绕路，天启开去守体育场【AI - Mirage Tank - Fight or Run?】【AI - Mirage Tank - Back Up】【Apoc Tanks - Move to Guard 1/2】。玩家已经买下天启的话整段跳过【AI - Mirage Tank - Skip Apoc Sequence】【Apoc Tanks - Player Owns】。
- **前哨的守军**：幻影坦克或玩家进 "Evalute Player Forces" 区域时，玩家如果**少于 4 个**苏军单位，1 秒后前哨的 2 辆铁锤（Additional Opposition）被调去守拳击馆，不在前哨了【Base - Evaluate Forces】【Base - Delete Encounter】。也就是：没怎么收买的玩家，最后一仗会更轻松。

### 3.6 交基地（第二段开头）

目标 3 完成 3 秒后开始过场【Objective 3 - Start Split】：棒球场 1 打开（模型动画），7 秒后从里面飞出第一架 Kirov 01【Split - Spawn Kirov】，全图揭示、黑边、播全屏影片 A08MM01；影片结束后：
- 边界换成 0 号（全图）【Split - Map Expand】；
- 镜头移到基地，4 秒后基地车开到位、自动展开，8 秒后在路点上直接生成 2 座矿厂、2 座电厂（第 3 座矿厂那行被关掉了），再 3 秒基地车归玩家，临时给 200 电力、5 秒后收回【Split - Move to Base】【Split - Move MCV】【Split - Setup MCVs】【Split - Setup Base】【Split - Transfer Base】【Split - Turn off Power Buffer & Set HG Stance】；
- 吉尔斯同样拿到一个基地（建造厂 + 2 矿厂 + 2 电厂），双方开启资源共享【Map Setup - Share Resources】；
- 苏军 01～03 和玩家互相变成敌人，发射场方 Soviet04 在目标 4 亮出时变成敌人、取消无敌【Objective 4 - Vulnerable Stadiums】。
- 过场一结束，Kirov 01 就朝西出口飞【Objective 4 - Setup (X-Level Workaround)】——第一架基洛夫是开场就在逃的（它离西边界多远、多久飞到，未确定）。

## 4. 段

**节拍表**（第二段时间从"Part Two"旗标置 1 算起，记作 P；单位秒）：

| 段 | 玩家要做 | 压力从哪来、怎么关掉 | 时间 |
|---|---|---|---|
| 潜入 | 跟幻影坦克走，收买苏军，避开巡逻 | 巡逻的磁暴步兵、天启；没有定时进攻；关不掉，只能绕或买 | 由幻影坦克的进度和对话决定，无固定时间 |
| 拆前哨 | 拆或占领建造厂、兵营、战车工厂 | 前哨守军（玩家兵少时被撤走一部分） | 同上 |
| 过场 + 交基地 | 无 | 无 | 目标 3 完成 +3 秒起，约 20～40 秒（含影片，长度未确定） |
| 拆发射场 | 建基地、防空、拆 5 座发射场，一架都不放走 | 基洛夫←各自的发射场；两家遭遇战 AI←它们的基地（拆了才停）；脚本小队←一次性 | 强度表排到 P+1500（普通）/ P+1000（困难）/ P+3000（简单） |

第二段内部的时间点（普通）：

| 时间 | 事 | 证据 |
|---|---|---|
| P+0 | Kirov 01 飞向西出口；Soviet02/03 唤醒；苏军对玩家变敌 | 【Objective 4 - Setup】【AI - Setup - Turn On AI】 |
| P+5 | 强度=轻，三张间隔表各写一次"选发射场"计时器（覆盖 125 秒） | 【Intensity - 01 - Light】 |
| P+12 | 亮出目标 4"摧毁基洛夫发射场"，发射场 1、2 显形、可被摧毁 | 【Objective 4 - Reveal】 |
| P+15 | 清场队出动；Soviet02 开始造兵 | 【Submission Cleanup - Attack Setup】【AI - Dynamics - Set Timers】 |
| P+17 | 亮出目标 5"别让基洛夫飞出哈瓦那" | 【Objective 5 - Reveal】 |
| P+32 | 吉尔斯的指挥面板开放（单人） | 【Objective 5 - Giles TH】 |
| P+77 | 发射场 3 显形；P+85 它放出剧本的 Kirov 03，P+100 飞向南 | 【Objective 4 - Reveal KLF 3】【… KLF3 - Launch】【… Move A】 |
| P+80～155（未确定） | 第一次随机发射（1～3 号里挑）；同时排好 4、5 号的长计时器（记作 T） | 【Kirovs - Controller - Determine KLF】【… Setup 4 & 5】 |
| P+222 | 发射场 4 显形 | 【Objective 4 - Reveal KLF 4】 |
| P+300 | 报复小队可以出动（普通、困难） | 【Retaliation - Setup】 |
| P+322 | 发射场 5 显形 | 【Objective 4 - Reveal KLF 5】 |
| T+240 / T+320 | 4 号 / 5 号定时放一架 | 【… Launch KLF4 - E】【… KLF5 - D】 |
| P+400 | Soviet02 放开"陆地进攻"，拿到超级反应堆 | 【AI - ScriptedFlagHeuristic - Timers】【AI - Dynamics - Transfer Power Plant】 |
| P+600 | 强度=中 | |
| P+650 | 两架牛蛙载 8 个动员兵空投 | 【Transport Conscripts - *】 |
| P+750 | Soviet02 拿到战斗实验室 | |
| P+900 | 强度=高；4、5 号开始无限续放（T+900） | |
| P+950 | Soviet02 放开"压倒性进攻" | |
| P+1000 | Soviet02 可以建建筑（也可能是 1200，见第 9 节） | |
| P+1200 / 1500 | 强度=严重 / 极端 | |

```yaml
段:
  - 名字: 潜入
    目标: [调查哈瓦那的苏军活动]          # P1 开局 12 秒亮出【Objective 1 - Setup】
    开场:
      - {镜头: drop zone}
      - 存档                              # 开场镜头开始 28 秒后【Introduction - Checkpoint】
    结束: giles.进入 objective 1 zone      # 词表写不出：条件是"友军的幻影坦克"进区域，不是玩家
  - 名字: 找基地
    目标: [找到苏军基地]                   # 目标 1 完成 5.5 秒后
    结束: giles.进入 objective 2 zone
  - 名字: 拆前哨
    目标: [摧毁苏军基地]                   # 目标 2 完成 5 秒后
    结束: [{任一: [摧毁 soviet conyard, 占领 soviet conyard]},
           {任一: [摧毁 soviet barracks, 占领 soviet barracks]},
           {任一: [摧毁 soviet factory, 占领 soviet factory]}]
  - 名字: 拆发射场
    边界: whole                            # MAP_SWITCH_BORDER(0)
    目标: [摧毁基洛夫发射场, 别让基洛夫飞出哈瓦那]
    开场:
      - {镜头: baseball 1}
      - 发射场.过场放一架                  # 词表写不出
      - {给: {基地车: 1, 矿厂: 2, 电厂: 2}, 在: allied base}   # 原版是在路点上直接造建筑、基地车自动展开
      - {资金: +15000/+5000/+5000}
    存档: 是                               # 条件其实是"玩家和吉尔斯都有了建造厂"【Split - Setup New Loss Condition (and Checkpoint)】
```

注意：原版的段切换几乎全是"某句对话播完"或"伙伴走到某处"，不是固定计时（第一段的 HAS_FINISHED_AUDIO 链）。

## 5. 目标

| 原版目标 | 主 / 奖励 | 完成 | 失败 |
|---|---|---|---|
| A08_Objective_1 调查哈瓦那的苏军活动 | 主 | 幻影坦克进目标 1 区域 | — |
| A08_Objective_2 找到苏军基地 | 主 | 幻影坦克进目标 2 区域 | — |
| A08_Objective_3 摧毁苏军基地 | 主 | 建造厂、兵营、战车工厂各自被摧毁**或被玩家占领**（可以用买来的苏军工程师占）；每拆一个摘一个标记 | — |
| A08_Objective_4 摧毁基洛夫发射场 | 主 | 剩余计数 ≤ 0；标记 1、2 先挂，3、4、5 随显形再挂 | — |
| A08_Objective_5 别让基洛夫飞出哈瓦那 | 主 | 发射场全毁 **且** 天上没有基洛夫；标记挂在每架活着的基洛夫上 | 任一架进出口区域 |
| A08_BonusObjective_1 招募 10 个苏军 | 奖励 | 同时拥有 ≥ 10 个苏军单位 | 无失败条件 |

```yaml
目标:
  调查哈瓦那的苏军活动:
    标记: [objective 1 zone]
    完成: giles.进入 objective 1 zone          # 写不出
  找到苏军基地:
    标记: [objective 2 zone]
    完成: giles.进入 objective 2 zone          # 写不出
  摧毁苏军基地:
    标记: [{soviet conyard: 摧毁 soviet conyard}, {soviet barracks: 摧毁 soviet barracks}, {soviet factory: 摧毁 soviet factory}]
    完成: [摧毁 soviet conyard, 摧毁 soviet barracks, 摧毁 soviet factory]   # 原版"摧毁或占领"都算
  摧毁基洛夫发射场:
    标记: [klf 1, klf 2]                         # 3/4/5 在 P+77/222/322 才挂上：写不出
    完成: 摧毁 [klf 1, klf 2, klf 3, klf 4, klf 5]
  别让基洛夫飞出哈瓦那:
    标记: []                                     # 原版挂在每架飞起来的基洛夫上：写不出
    完成: [目标 摧毁基洛夫发射场 完成, 发射场.天上没有]   # 写不出
    失败: 发射场.逃走                            # 写不出
  招募 10 个苏军:
    奖励: 是
    说明: 用间谍收买苏军。收买来的兵会自动停火，不会暴露伪装。
    完成: 拥有 苏军单位 >= 10                    # 写不出：词表只有"建成 X"（≥1）
```

目标弹出用一个"目标正在显示"旗标排队，每个占 5 秒【Objective 0 - Controller】；各目标的"完成"脚本也要等这个旗标空闲才判定。

## 6. 进攻

### 6.1 第一段

没有定时进攻。压力只来自：巡逻（精英磁暴步兵来回走 6 个路点，每点停 3 秒）、被发现时的反应（镰刀跳走、磁暴步兵开始放电）、一架潜艇和几架米格飞过（米格是 1～4 秒随机刷出、飞到终点删掉的循环，纯气氛【Flight Group B - *】）。失败来自幻影坦克被打掉或玩家全军覆没（第 8 节）。

### 6.2 第二段：脚本小队

```yaml
进攻:
  - 名字: 清场队
    开始: 段 拆发射场 + 0:15
    兵: {战熊: 2, 镰刀: 2, 天启坦克: 2}
    从: forward base east          # 摆在 (3466, 3770)
    打: slaughter point            # WP - Slaughter Players Forces，位置未确定
  - 名字: 动员兵空投
    开始: 段 拆发射场 + 10:50      # 650 秒；三个难度一样
    兵: {动员兵: 8}                # 装在 2 架牛蛙里，飞到投放区自动跳伞，牛蛙飞走删掉
    从: north sea                  # 摆在 (3446, -311) 地图外
    打: conscript drop target      # 位置未确定
  - 名字: 报复一队
    开始: [段 拆发射场 + 5:00, 发射场.剩余 4]      # 普通、困难；简单直接删掉这队【Easy - Delete Teams】
    兵: {镰刀: 0/3/3}
    从: soviet02 base east         # (4793, 3336)
    打: scripted attack point      # WP - Attack Move Scripted Teams，位置未确定
  - 名字: 报复二队
    开始: [段 拆发射场 + 5:00, 发射场.剩余 3]
    兵: {天启坦克: 0/2/2}
    从: soviet02 base east
    打: scripted attack point
  - 名字: 矿区巡逻
    开始: 段 拆发射场
    兵: {海蝎: 2}
    从: south ore field            # (3139, 300)，沿 PATH - Ore Node Patrol 攻击巡逻
    打: south ore field
  - 名字: 轰击舰队
    开始: 发射场.剩余 2           # 只困难【Bombarders - Group C - Attack】[--H]
    兵: {无畏舰: 0/0/1, 海蝎: 0/0/3}
    从: north offmap               # (2040, 6328)
    打: soviet naval attack point
```

报复小队的写法有个坑：条件是"5 分钟到了 **且** 剩余恰好 = 4（或 3）"。玩家 5 分钟内已经拆到剩 3 座，一队就永远不来了【Retaliate01 - Attack】。

只在合作（Player_2 是真人）时才有：磁暴船打玩家矿区（玩家在 1 号扩张点有 ≥ 2 座矿厂）【Tesla Boats - Group A - Attack Expansion】；困难下 450 秒一艘无畏舰、800 秒一队轰击舰【Bombarders - Group A/B】。

### 6.3 第二段：遭遇战 AI

**Soviet02 陆军**（东北基地）：

| 设置 | 值 | 证据 |
|---|---|---|
| 唤醒 | P，把预摆单位全部交给 AI；1～2 秒后再把第一段的天启、战熊、米格、维修场的坦克、镰刀转过来 | 【AI - Setup - Turn On AI】【… Scripted Transfers】【… Turn On】 |
| 资金 | 10000，三个难度一样；之后没有补钱 | 【AI - Setup - Money】 |
| 维修 / 重建 | 维修开，重建关 | 【AI - Setup - Settings】 |
| 威胁等级加成 | 关 | 【AI - Setup - Turn Off Red Alerts】 |
| 偏好的敌人 | 玩家（Player_1）。随机在玩家和吉尔斯之间切换的脚本写了但没人打开，所以一直是玩家 | 【AI - Preferred Enemy - *】 |
| 造兵 | P+15 起；"地面防守"小队里能打的不到 12 个（困难 16 个）才允许造，满了就停（repeat 开关） | 【AI - Dynamics - Allow Unit Production】 |
| 造建筑 | P+1000 秒（脚本另有一份 1200，标记有问题），或者只剩 1 座发射场时马上放开；放开时允许造矿厂、继续禁超级武器 | 【AI - Dynamics - Allow Structure Production】 |
| 科技 | 超级反应堆 P+400（困难 300）、战斗实验室 P+750（困难 600）移交给 AI，相当于定时解锁高级兵种 | 【AI - Dynamics - Transfer Power Plant/Battle Lab】 |
| 进攻种类旗标（AI 人格文件读） | "陆地进攻"：P+400 或剩 3 座；"压倒性进攻"：P+950 或剩 ≤ 2 座（同时关掉陆地进攻）；"全体保护基洛夫"：剩 ≤ 0 座；"起飞战斗机"：玩家有 ≥ 4 架攻击机 / ≥ 5 架阿波罗 / ≥ 2 架世纪轰炸机（困难各 ≥ 2）时开，否则关 | 【AI - ScriptedFlagHeuristic - *】 |

这些旗标具体让 AI 派多少兵，写在 AI 人格（AIP）里，不在这份脚本里，未确定。

**Soviet03 海军**（东北角船坞）：唤醒 P；资金 10000；维修开、重建关；基地位置定在 "WP - Soviet Naval Reactive Defense"（`SKIRMISH_AI_MAKE_BASE`）；偏好的敌人是吉尔斯；禁造建筑和矿厂（只能用现有的船坞出船）；超级反应堆 P+300、战斗实验室 P+600 移交【AI - Setup - *】（第二份）【AI - Dynamics - *】（第二份）。

**吉尔斯（Player_2，单人时是 AI）**：资金 10000（加上第二段的 5000/15000 赠款）；维修开；敌人优先级 Soviet01 10、Soviet02 20、Soviet03 30、发射场方 40；第二段里苏军（Soviet03）海军剩 2 艘以下、两个船坞都没了以后改打 Soviet02 并停造海军【AI - Preferred Enemy】【AI - Switch to Land】。玩家能通过合作指挥面板的"热点"命令他去打某座发射场或抢扩张点（3～5 号发射场的热点开局就可见，1、2 号在第二段可见；扩张点的不会出现，见下条）【AI - Hotspots - *】。

### 6.4 压力和它的开关

| 压力 | 开始 | 拆什么就停 |
|---|---|---|
| 1～3 号的轮流发射 | P+80～155 起，间隔随强度缩短 | 拆掉那一座就少一路；三座都没了这一路就停 |
| 4、5 号的报复发射 | 每拆一座各放一架；T+240/320 定时；T+900 起无限续放 | 拆掉它本身 |
| 最后三连发 | 剩 1 座时 | 拆掉最后一座（三架照样要打下来） |
| Soviet02 陆军 | P+15 造兵，P+400/950 放开进攻 | 拆它的生产建筑（AI 不重建） |
| Soviet03 海军 | P | 拆船坞（不能造建筑） |
| 脚本小队 | 一次性 | 打掉就没了 |

## 7. 规则

**提示**
- 单人第一段几乎全靠吉尔斯的语音一句接一句讲（"跟紧我""他们挡路了，收买他们"等），对话完一句才走下一步【AI - Mirage Tank - *】。
- 信息框：收买说明 15 秒（奖励目标亮出 2 秒后）；"C 点挡路"时第二个收买信息框，一直挂到那个兵被收买或死掉【Bonus Objective 1 - Infobox 01/02/02 Clear】。
- 第二段 65 秒时，如果玩家（或吉尔斯）有间谍和兵营，播一句关于间谍的 EVA【Spy - Create Line】（内容未确定）。
- 扩张点热点的提示文字写了，但它的计时器"TIMER - Reveal Expansions"没人设，推断不会出现【AI - Hotspots - Expand - Reveal】。
- 合作时才有的屏幕提示：目标 1、目标 3 的提示文字【Objective 1/3 - Human Hint Text *】。
- 电厂被毁时临时打开"低电力"语音再关上【EVA - Low Power】（玩家自己的那座初始电厂那行被关了，所以推断基本不会触发）。

**兜底**
- 第一段：玩家兵少时撤掉前哨两辆铁锤（3.5）。
- 伙伴等人：幻影坦克在"Stay Close"处最多等 5 秒。
- 第二段**没有**给玩家的兜底：不送援军、不给钱、没有"X 分钟还没拆就提示"。
- 反过来给敌人"加压兜底"：4、5 号发射场 T+900 后无限续放；剩 1 座时 Soviet02 立刻能建建筑。

**对话**（TH 是雷达小窗视频，统一用"正在播放"旗标排队，结束后留 1～3 秒）：
- TH04 开场；TH05 吉尔斯介绍幻影坦克；TH09/11 过场；TH07 吉尔斯在 P+32；
- TH12（Oleg 嘲讽）剩 4 座；TH13 剩 3 座、以及剩 1 座时；
- TH03 有基洛夫被拦下（预警区清空）；
- TH01 / TH10 胜利；TH02 失败。
- 第二段那一整套吉尔斯剧本（运输轰炸机炸 2 号场、玩家造 6 辆酋长坦克后给 3 级时间炸弹、打完 3 号场放 logo）所在的"AI - Part Two"组，入口脚本【AI - 12 - Split Complete】关着且没人打开，推断是演示版遗留，正式流程里不运行。

**自动存档**：2 次。开场镜头开始约 28 秒后【Introduction - Checkpoint】→【Checkpoints - Part One】；第二段玩家和吉尔斯都有建造厂时【Split - Setup New Loss Condition (and Checkpoint)】→【Checkpoints - Part Two】。

**给援军**：第二段开头的基地套装和钱（2.、3.6）；合作时给吉尔斯一队水翼船【Split - Spawn Reinforcements (Human)】。此外没有。

```yaml
规则:
  - 当: [段 拆发射场 + 1:05, 建成 间谍, 建成 兵营]   # 【Spy - Create Line】；语音内容未确定
    做: [通报 （关于间谍的 EVA 提示）]
  - 当: 发射场.剩余 4
    做: [通报 （Oleg 嘲讽）]
  - 当: 发射场.剩余 3
    做: [通报 （Oleg 嘲讽）]
```

## 8. 输赢

```yaml
胜利: [目标 摧毁基洛夫发射场 完成, 发射场.天上没有]   # 再等 4 秒 + TH01 播完 + 3 秒【Objective 5 - Mission Complete】【TH - A08TH01 - End】
失败:
  - {当: [段 潜入, 摧毁 giles], 原因: 吉尔斯的幻影坦克被摧毁。}      # 第一段，空投落地后才启用【Win & Loss - Loss Condition - Part 1 (TH)】
  - {当: [还没 段 拆发射场, 没有 苏军和盟军单位], 原因: 全军覆没。}   # 【AI - Mirage Tank - Lose All Units】
  - {当: 发射场.逃走, 原因: 一架基洛夫飞出了哈瓦那。}                # 【Win & Loss - Loss Condition 02 (TH)】
  - {当: [段 拆发射场, 没有 盟军和苏军的"失败判定"建筑], 原因: 基地没了。}   # 要先等双方都有建造厂才生效【Win & Loss - Loss Condition (TH)】
```

失败都是：EVA 一句 → 4 秒后播 TH02 → 播完 3 秒判负。第二段的"基地没了"用的是对象列表 `_object list_allied loss condition` 和 `_object list_soviet loss condition`（玩家买来的苏军建筑也算命），列表内容未确定。

## 9. 难度

| 改了什么 | 简单 | 普通 | 困难 | 证据 |
|---|---|---|---|---|
| 第一段收买预算 | 10000 | 7000 | 5000 | 【Player01 - Setup - Money - Part 1*】 |
| 第二段赠款（玩家 / 吉尔斯各） | +15000 | +5000 | +5000 | 【Player01 - Setup - Money - Part 2*】 |
| 强度升档时间（中/高/严重/极端） | 1200/1800/2400/3000 | 600/900/1200/1500 | 250/500/750/1000 | 【Intensity - 00 - Set Timers*】 |
| 发射间隔表 | 名义上分三张，实际基本只用普通表（3.1） | | | 【Kirovs - Controller - Countdown*】无难度标记 |
| 4 号场"剩 1 座"和"T+240"两次发射 | 无 | 有 | 有 | 【Launch KLF4 - D/E】[-NH] |
| 报复两队、磁暴船 | 删除 | 有 | 有 | 【Easy - Delete Teams】【Retaliation - Setup】[-NH] |
| 轰击舰队（剩 2 座时） | 无 | 无 | 有 | 【Bombarders - Group C - Attack】[--H] |
| Soviet02 地面防守上限 | 12 | 12 | 16 | 【AI - Dynamics - Allow Unit Production*】 |
| Soviet02 科技移交（反应堆/实验室/建筑） | 400/750/1000 | 400/750/1000 | 300/600/1200 | 【AI - Dynamics - Set Timers】[EN-] 和【… (Hard)】（无标记） |
| Soviet02 起飞战斗机的门槛 | 4/5/2 架 | 4/5/2 架 | 2/2/2 架 | 【AI - ScriptedFlagHeuristic - Activate Mig Attacks*】 |
| 敌方 AI 资金 | 10000 | 10000 | 10000 | 不随难度变 |

标记有问题的地方：【AI - Dynamics - Set Timers (Hard)】没有难度标记，三个难度都跑；简单 / 普通下它和 [EN-] 那份在同一条件上同时触发，最后谁的值留下未确定（按顺序推断是困难那份）。发射间隔表的问题见 3.1。

不改的：分段结构、发射场数量、Kirov 1～3 的轮换规则、出口、失败条件。

## 10. 我们的词表写不出的

逐条，括号里是原版脚本。

1. **会生成飞行单位的"发射场"机关**。每座发射场一次只放一架、这一架被打下来才放下一架（【Kirovs - Controller - Launch KLF1/2/3】的 `NAMED_NOT_DESTROYED('UNIT - Kirov 0n')` 取反）。我们的进攻是"一波一波按间隔来"，没有"上一个还活着就不来"。
2. **随机**。1～3 号发射场随机轮流（`SET_RANDOM_COUNTER(…,1,3)`，【Determine KLF】），出口随机（【Kirov n Launch】`SET_RANDOM_COUNTER(…,1,8)`），间隔是随机区间（`SET_RANDOM_MSEC_TIMER`，【Countdown *】）。词表里所有时间都是定值，也没有"从几处里挑一处"。
3. **全局"强度"等级改变间隔**。6 档，时间或进度哪个先到就升档，升档后改的是发射间隔（【Intensity - *】【Countdown *】）。我们的 `加码` 只能"条件成立后每波多几个兵"，不能缩短 `每隔`，也没有能被多处读的等级变量。
4. **"一组里已经毁了几个"的条件**。发射场剩余计数 = 4、3、2、1（`COUNTER('COUNTER - KLF Remaining', 2, n)`）驱动强度、报复、AI 旗标、嘲讽。我们只有 `摧毁 <角色>`（一组全毁才成立），写不出"5 座里任意 2 座没了"。
5. **拆一座、其余报复**。剩余 ≤ 4/3/2/1 时 4、5 号各放一架（【Launch KLF4 - A…D】【Launch KLF5 - A…C】），T+900 后无限续放（【… - F/G】【… - E/F】[repeat]）。词表的 `来源` 只有"全毁就停"一个方向，没有"毁一个就让别的加强"。
6. **最后一座三连发**（【Kirovs - Controller - Setup Final Countdown】【Kirovs - Final Countdown - *】）：剩 1 座时 10 秒间隔放 3 架，分飞西、北、南。
7. **"敌方单位进区域就输"**（【Kirovs - Controller - Kirov Leaves Havana】）。我们的 `进入 <地点>` 只看玩家的单位；失败条件写不出"某种敌方单位进了一组区域里的任何一块"。
8. **敌方单位的预警区**：基洛夫进"出口预警区"时雷达提示 + 分方向语音，每方向一次（【Kirovs - Warning - N/…】），以及"逃跑中 / 拦截成功"音乐切换（【Kirov Music - *】）。我们的 `预警` 只在进攻出发时报一次。
9. **脚本生成的单位的状态和标记**：不攻击（`NO_ATTACK`）、全图可见（`SHROUD_REVEAL_TO_ALL`）、每帧雷达点（【… Pinger】[repeat]）、目标标记挂到新生成的每一架上、死了摘掉（【… Unlink Objective】）。我们的 `标记` 只能挂在开局就摆好的角色上。
10. **屏幕计数器**：`DISPLAY_COUNTER('COUNTER - Kirovs - Kirovs in the Sky')` 实时显示天上还有几架（【Kirovs - Controller - Update Display】）。我们只有 `倒计时`。
11. **"天上没有某种敌方单位"做胜利条件**（【Objective 5 - Complete】`COUNTER(Kirovs in the Sky, 2, 0)`）。我们的胜利条件里没有"某类敌方单位数 = 0"。
12. **目标标记分批挂、建筑分批显形**：发射场 3、4、5 在 65/210/310 秒后才挂标记、揭开周围迷雾、播放模型动画、雷达提示（【Objective 4 - Reveal KLF 3/4/5】）。我们的目标标记在目标亮出时一次挂齐；也没有"揭开某处迷雾""播建筑动画"的动作。
13. **无敌 → 可摧毁**：发射场第一段无敌（`UNIT_AFFECT_OBJECT_PANEL_FLAGS(…,'Indestructible',1)`），第二段才能打（【Objective 1 - Invincible Stadiums】【Objective 4 - Vulnerable Stadiums】）。我们能用 `其他` + `翻脸` 做"中立后变敌"，但没有无敌开关。
14. **遭遇战 AI 整套**（【AI - Setup - *】【AI - Dynamics - *】【AI - ScriptedFlagHeuristic - *】【AI - Preferred Enemy】）：唤醒并接管预摆单位、资金、维修开重建关、基地位置、敌人优先级、按时移交科技建筑（定时解锁高级兵种）、"防守小队满 12 个就停造"、用旗标按时间或进度逐级放开进攻种类、根据玩家空军数量开关战斗机。词表里敌人只有写死的 `进攻`；A7 的策划案也把这条列在"还没做的"里。
15. **伙伴带路**：目标 1、2 由友军的幻影坦克走进区域完成；它按对话和路点走，会等玩家（最多 5 秒，或玩家走进同一区域就走）、遇到收买点停下等玩家收买 3 个或清掉（【AI - Mirage Tank - Go to A2/B/C】）；它死了就输。我们的 `车队` 机关是"三辆车按时间表、玩家指挥不了"，不会等人，也不能当目标的主语。
16. **收买 / 招募**：奖励目标是"同时拥有 ≥ 10 个苏军单位"（`PLAYER_HAS_OBJECT_COMPARISON(…, 3, 10, '_object list_soviet all units')`），被收买的单位自动改为停火姿态（【Bribe - *】）。我们的 `建成 <单位>` 只有"至少 1 个"，没有数量门槛，也没有"按阵营 / 类别"的单位列表；也没有改单位姿态的动作。
17. **按玩家兵力走分支**：有 ≥ 4 防空步兵且 ≥ 2 磁暴步兵就打天启，否则绕路（【AI - Mirage Tank - Fight or Run?】带 ELSE）；苏军不到 4 个就撤走前哨两辆铁锤（【Base - Evaluate Forces】【Base - Delete Encounter】）。我们的规则只有"条件成立做什么"，没有"否则做什么"，也没有数量条件。
18. **"移动到某处"类的敌方小动作**：撤守军（`MOVE_TEAM_TO`）、空投兵（牛蛙装兵、飞到区域自动跳伞，【Transport Conscripts - *】）、被发现就跳走的镰刀（【Sickle - Jump】）、被发现就放电的磁暴兵。我们的 `进攻` 只有"打 / 守"，没有"运过去再放下"、"被发现时做什么"（`NAMED_DISCOVERED`）。
19. **合作指挥官**：吉尔斯是有自己基地、资源共享、能被玩家用热点下令的 AI 队友（【AI - Hotspots - *】【Map Setup - Share Resources】`SET_COOP_AI_COMMAND_UI_ENABLED`）。我们的 `其他` 一方只能"中立 → 转给我 / 翻脸"。
20. **在路点上直接生成建筑交给玩家**：基地车自动展开 + 2 矿厂 + 2 电厂、临时电力 200（【Split - Setup Base】【Split - Move MCV】）。`给` 能给单位，能不能给"已经建好的建筑"、能不能让基地车自动展开，词表没说，未确定。
21. **由对话驱动的节奏**：第一段每一步都是 `HAS_FINISHED_AUDIO(…)` 接下一步，段切换也等对话。我们的条件里没有"某句对话播完"。
22. **存档条件**：第二段的存档等"玩家和吉尔斯都有建造厂"才存（【Split - Setup New Loss Condition (and Checkpoint)】）；同一个条件也是"基地没了就输"开始生效的闸门。我们的 `存档` 只能挂在段开头或规则上，大致能模拟，但"失败条件等某事发生后才生效"要每条失败都手写 `[X, …]`。

## 11. 和我们 A7 比

只列有实质的差别。

**1. "别让它逃走"的做法正好相反**
- A7：一个首领、一次逃跑。断电后自由号沿固定航线飞，屏幕有 6/4/3 分钟倒计时，倒计时到了就输；玩家有明确的"最后期限"，还送 2 架阿波罗 + 2 辆多功能步兵车。
- 哈瓦那：几十次小逃跑、每次都是"一架飞出去就输"。没有倒计时，期限是基洛夫的飞行距离；出生后悬停 15 秒是唯一的固定反应窗口；出口在 8 个方向里随机（实际只用到 6 个）。基洛夫不投弹（`NO_ATTACK`），纯粹是"拦截靶子"；全图可见、每帧雷达点、屏幕计数，信息给得很足，难的是**防空覆盖面**而不是找到它。
- 对我们的启发：A7 的"它要飞走"是一段收尾高潮；哈瓦那把"拦截"做成了贯穿第二段的持续税，逼玩家在地图四周铺防空。A7 要更像哈瓦那，就得让逃跑的威胁在第 2 段就出现（比如自由号每次跳回家时都有一小段可被拦截的窗口），而不是只在最后。

**2. "压力来源拆掉就停"——哈瓦那是"拆一个，其余更凶"**
- A7：电站一断，跃迁就停（再进入逃跑段）；东岸兵营 + 战车工厂全毁，地面进攻就停。拆掉 = 关掉，干净。
- 哈瓦那：每座发射场只管自己那一架，拆掉它这一路确实停了；但拆到剩 4/3/2 座时强度升档、剩下的 1～3 号发射更勤，4、5 号各报复一架，Soviet02 的进攻种类被提前放开，普通 / 困难还有报复小队，剩 1 座时三连发。**进度本身就是加压器**，玩家越快越难，龟缩则按时间也会升档。我们的词表只表达了前一半（`来源`），后一半要新机关（第 10 节第 3～6 条）。

**3. 敌方基地靠遭遇战 AI 施压，脚本波次只是点缀**
- A7：敌方东岸是写死的两路波次（地面进攻每 2:30/2:00/1:40 一波、最多 6 波，最后一波倾巢），有 `来源`。
- 哈瓦那：两家遭遇战 AI（陆军、海军）从第二段开始就在造兵，节奏由"防守满 12/16 个停造""按时间移交反应堆和实验室""按时间或拆场进度放开进攻种类"控制；脚本小队一共 4～6 支，全是一次性的。A7 策划案自己也写了"AI 基地以后再试"——哈瓦那是这条最直接的参照。

**4. 奖励目标的作用**
- A7：两个奖励都是"打法上的缺口"（占电站得电、拆东岸断兵）。
- 哈瓦那：奖励就是收买来的 10 个苏军本身，没有额外发东西；但收买多少会改变第一段的走向（够了就跟吉尔斯正面打天启，不够就绕；兵少还会撤掉前哨守军）。也就是奖励目标同时充当了**动态难度**。

**5. 兜底**
- A7：8 分钟没断电再提示一次；第 3 段直接送防空部队；最后一分钟提示。
- 哈瓦那：第二段对玩家零兜底（无援军、无提示、无补钱），反而给敌人加压兜底（T+900 后无限续放）；它的兜底全在第一段（伙伴等人、兵少撤守军、对话一步步讲）。

**6. 节奏结构**
- A7：先建基地，三段都在基地战里，第 1 段是"侦察哨所"。
- 哈瓦那：第一段完全没有基地，是对话驱动的潜入 / 收买，段切换等吉尔斯走到位、等对话播完；中间一个过场交基地并把边界扩到全图。这正是 map-language.md 第 7 节说的"后几关多数开局没有能用的基地"的典型。

**7. 难度**
- A7：自由号血量、倒计时长度、进攻间隔和兵力都按难度写。
- 哈瓦那：真正随难度变的是钱和"强度什么时候升档"；发射间隔表因为脚本标记问题基本不分难度（3.1）。我们照抄时要把"间隔"和"升档时间"都按难度写清楚，别重演这个问题。
