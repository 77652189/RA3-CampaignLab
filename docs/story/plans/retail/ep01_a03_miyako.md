# 原版 · 起义时刻盟军第 3 关 宫古岛 · 反写策划案

来源：`work/retailref/camp_ep01_a03_miyako_stewart.txt`（脚本全文）、`.json`（物体、目标）、`work/mapstudy/camp_ep01_a03_miyako_stewart.png`。
**这不是能编译的关卡。** 下面的 `yaml` 块按我们的写法把原版"翻译"一遍，方便和 仓库里的 `docs/story/plans/a7.md` 对照；地点名是我起的描述名（地图没有公开地点），坐标在旁边注明。写不进词表的放在文字里，第 10 节汇总。
每条结论后面的 `'…'` 是原版脚本名。时间：这张图只用 `SET_MILLISECOND_TIMER` / `SET_RANDOM_MSEC_TIMER`，参数就是秒（例如过场镜头 `MOVE_CAMERA_TO(…, 15.0, …)` 配 `t_…_end 16.0`，对得上）；没有用帧计时的 `SET_TIMER`。

比较码（从上下文核对过）：`PLAYER_HAS_OBJECT_COMPARISON` / `COUNTER` 的第二个参数 0 `<`、1 `<=`、2 `==`、3 `>=`、5 `!=`。例：`'tatsu has limited powerplants'` 是 `(3, 4)` = 电厂 ≥4 就禁造；`'initiate chronobase to site a'` 用 `(5, 1)` = "现在不在 a 点"。

## 1. 定位

- 起义时刻盟军第 3 关。三方敌人轮流上：前哨守军（Japan_3）→ 高良 Takara（Japan_1，西北）→ 背叛的龙 Tatsu（Japan_2，东北）。
- 类型：建基地 + 连打两位指挥官（遭遇战 AI），第二位会用超时空仪把**整座基地**搬走。
- 教玩家：①用新单位（和平使者火炮车 `AlliedArtilleryVehicle`、冷冻军团兵 `AlliedLegionnaireInfantry`、两栖基地车 `AlliedMCV_Naval`）打开突破口建基地；②帝国的"会走的炮塔"和伪装运输车；③追着一座会逃跑的基地打——拆得越多它跑得越勤，但拆到电厂 / 超时空仪 / 建造厂它就跑不了。

```yaml
关卡: ep01_a03
名字: 宫古岛
一句话: 在任一突破口建基地，打败高良；盟友龙背叛，他的整座基地会用超时空仪跳到你不在的地方——拆他的电和超时空仪，把他钉死
地图: camp_ep01_a03_miyako_stewart
阵营: {我: 盟军, 敌: 帝国}     # 实际是 Japan_1 / Japan_2 / Japan_3 三个敌方玩家，词表只有一个"敌"
时长: 未确定                    # 脚本里没有任何限时；三段都由玩家推进
边界: 西半边                    # MAP_SWITCH_BORDER(1)，'map border setup'；第 3 段换成 0（全图）
```

## 2. 开局

地图 5000×5000。一条河从北往南绕过中央台地再向东流出。

| 谁 | 在哪（x, y） | 有什么 |
|---|---|---|
| 玩家 | 南边中部低地 (2995, 670) | 两栖基地车 1、和平使者火炮车 2（`o_siege_tank_a/b`）、冷冻军团兵 2（`o_cryo_a/b`）。开场过场里它们自己往前开（`'sc intro cue player artillery'`、`'sc intro cue player forces'`） |
| 突破口 A | 中央台地 (2517, 2516) | 目标标记 `wp_objective_1_a`；Japan_3 守军 + 墙（`Barrier_Hubs`） + 巡逻 B |
| 突破口 B | 西南台地 (1106, 1080) | 目标标记 `wp_objective_1_b`；Japan_3 守军 + 墙 + 巡逻 A |
| Japan_3 前哨 | 两个突破口和它们的路口 | `Guard_Tanks` 海啸坦克 5、`JapanAntiInfantryVehicle` 4；`Guard_Infantry` 帝国武士 16、弓箭少女 4；`Sentinel_Patrol_A/B` 各 4 坦克杀手；`Barrier_Hubs` 墙 26 段 |
| 高良 Japan_1 | 西北 (130–2379, 3582–4897) | 建造厂、兵营 2、战车工厂 2、船坞、科技中心、**电厂 14**、矿厂 2（+1 蛋）、守卫塔 4、波能塔 2、火箭天使 3、VIP 地堡、墙；外加 Japan_3 名下 6 个炮塔蛋、3 辆伪装运输车（各载 4 弓箭少女） |
| 龙 Japan_2 | 东北 (3588–4797, 2495–4876)，边界外 | 建造厂、兵营、战车工厂、船坞（东边河口 4564, 2670）、科技中心、电厂 4、守卫塔 6、海翼 `JapanAntiAirShip` 3、VIP 地堡；"惰性"队（`Tatsu_Inert_Teams`，第 3 段才并入）巨型要塞 2、将军战舰 2；过场部队 `Cine_Forces`（坦克杀手 3、`JapanSentinelVehicle` 3、弓箭少女 3、打击者 2） |
| 中立 | 西边缘 (153, 2137) | 废弃通讯塔 `TH_ImperialLongRangeRadar`（奖励目标）；旁边 4 辆鬼王 `Free_Onis`（中立，奖励） |
| 墙 | x≈3076–3188 一整条南北线 | 16 座仓库 `Stupid_Walls`，把东西两半隔开，第 3 段开始时被炸掉（`'objective 2 completed'`） |

- **玩家资金：未确定。** 脚本里没有给 Player_1 设钱（只有 `PLAYER_SET_MONEY('Japan_1', 1000)` 和 `('Japan_2', 2000)`），开局资金在地图的玩家属性里，导出里没有。三个难度脚本里都不改玩家的钱。
- 玩家不能造未来坦克（`'setup player tech lockouts'`）。
- 西南角一块矿 `o_aidonottake_a` 标了 `SKIRMISH_AI_DO_NOT_TAKE`（AI 不去占，`'mission setup'`）；通讯塔标了 `SKIRMISH_AI_DO_NOT_ATTACK`（AI 不打它）。

```yaml
开局:
  资金: 未确定
  部队:
    - {单位: AlliedMCV_Naval, 在: start, 角色: mcv}
    - {单位: AlliedArtilleryVehicle, 数量: 2, 在: start, 角色: pacifier}
    - {单位: AlliedLegionnaireInfantry, 数量: 2, 在: start, 角色: cryo}
    # 前哨（Japan_3）：数量按困难摆，简单/普通删掉的见第 9 节
    - {单位: 海啸坦克, 数量: 5, 在: breach center 和 breach southwest 的路口, 阵营: 敌, 角色: guard tanks}
    - {单位: JapanAntiInfantryVehicle, 数量: 4, 在: 同上, 阵营: 敌, 角色: guard tanks}
    - {单位: 帝国武士, 数量: 16, 在: 两个突破口, 阵营: 敌, 角色: guard infantry}
    - {单位: JapanArcherInfantry, 数量: 4, 在: 两个突破口, 阵营: 敌, 角色: guard infantry}
    - {单位: 坦克杀手, 数量: 4, 在: breach southwest, 阵营: 敌, 角色: patrol a}   # 沿 wpp_sentinel_patrol_a 巡逻
    - {单位: 坦克杀手, 数量: 4, 在: breach center, 阵营: 敌, 角色: patrol b}      # 沿 wpp_sentinel_patrol_b 巡逻
    - {单位: 围墙, 数量: 26, 在: 两个突破口, 阵营: 敌, 角色: barrier}
    # 高良（Japan_1）的基地和炮塔蛋、伪装运输车：略，见上表
    # 龙（Japan_2）的基地：略，见上表
    - {单位: TH_ImperialLongRangeRadar, 在: com tower, 阵营: 中立, 角色: com tower}
    - {单位: 鬼王, 数量: 4, 在: com tower, 阵营: 中立, 角色: free onis}
```

## 3. 机关

### 3.1 "在任一突破口建基地"怎么判定

**不看位置。** 目标 1 的完成条件是玩家有 ≥1 座建造厂（`'player builds mcv'` → `f_player_built_mcv` → `'objective 1 completed'`），在边界内哪里展开都算。两个突破口只是两个目标标记（`'obj issue objective 1 text'` 挂在 `wp_objective_1_a/b`）。
原版写过一个按区域判定的子程序 `'if player takes base a'`（看 `area_tatsu_basearea_d` 里有没有玩家关键建筑），但**没有任何脚本调用它**，是死代码。
建好建造厂 2 秒后，两个突破口的墙全部自己卖掉（`'autosave 1'`——名字叫自动存档，其实只做了 `SELL_OBJECT`，没有存档）。

### 3.2 高良的"爬行炮塔"和伪装运输车

- 6 个炮塔蛋（`JapanBaseDefenseEgg` ×3 = 守卫塔，`JapanBaseDefenseAdvancedEgg` ×3 = 波能塔），开局属于 Japan_3，摆在高良基地南缘。
- 每个蛋"启动"的条件：随机计时到了，**或者**蛋自己看见了玩家单位，哪个先到算哪个（`'begin turret spam a'`…`f`）。
- 启动后每一刻：没看见玩家 → 朝玩家**最近的关键建筑**开（`TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE_OWNED_BY_PLAYER`）；看见玩家 → 原地展开成炮塔，归高良（`'naomi turret spam sequence a'`…）。
- 3 辆突击运输车 `JapanLightTransportVehicle`，各装 4 个弓箭少女（`'setup fake turret spam'`），开局 1 秒用"强制攻击"把自己伪装成炮塔蛋（`'disguise fake turrets'`）。启动后朝玩家最近的单位或建筑开，看见玩家且"紧急卸载"技能好了就卸兵，车和兵都归高良（`'naomi fake turret spam sequence a'`…）。
- 随机时间窗（从高良唤醒算起，`'enable naomi ai'`）：

| 谁 | 窗口（秒） | 难度 |
|---|---|---|
| 炮塔 A（守卫塔） | 0–30 | 全部 |
| 伪装车 A | 0–30 | 全部 |
| 炮塔 D（波能塔） | 30–60 | 只有困难（简单、普通都删了） |
| 伪装车 B | 30–60 | 全部 |
| 炮塔 B（守卫塔） | 60–90 | 全部 |
| 伪装车 C | 60–90 | 全部 |
| 炮塔 C（守卫塔） | 120–150 | 全部 |
| 炮塔 E（波能塔） | 150–180 | 普通、困难 |
| 炮塔 F（波能塔） | 没有计时，只能被看见才启动 | 普通、困难 |

  炮塔 E 的计时被写了两次（先 90–120 又改成 150–180），F 的计时一次没设——像是笔误，结果就是上表。
- 210 秒时还没启动的全部直接交给高良，并且整个高良交给遭遇战 AI（`'finish turret spam'`）。

### 3.3 龙的超时空仪（重点）

龙一开始没有超时空仪。第 3 段目标亮出后：

1. **拿到超时空仪**：`o_tatsu_chronosphere` 一开始不存在，`'chronosphere destroyed'` 在目标 3 生效那一刻就成立，30 秒后（只要龙还有建造厂）在他**当前所在基地点**的 3 个预设位置里随机挑一个，凭空造一座盟军超时空仪 `AlliedSuperWeapon` 归他（`'respawn tatsu chronosphere'` → `'respawn chronosphere a a'`…）。之后每被拆一次，30 秒后照样重生，**直到他的建造厂没了**。造出来时播龙的台词 ATH03TS04（`'th - chrono he didnt'`）。
2. **没收玩家的**：目标 3 亮出 60 秒后，把玩家离得最近的那座超时空仪卖掉，并禁止玩家再造（`'if player has a chronosphere'`）。
3. **每一轮怎么判**（`'evaluate need to chrono base'`，重复）——四个条件同时成立才动：
   - 充能计时到了；
   - 龙**电力够**（`PLAYER_HAS_POWER('Japan_2')`）；
   - 龙有超时空仪；
   - 超时空仪的特殊能力就绪。
4. **两种动作二选一**：
   - **搬家**（`'evaluate relocation area a/b/c/d'` → `'evaluate possibility of relocation'` → `'initiate chronobase to site a'`…）：地图上有 4 个基地点 a/b/c/d。一个点"可以去"要同时满足：玩家在那里的单位 **少于 5 个**、建筑 **少于 2 座**，并且龙的关键建筑（第 8 节的清单）**≤5 座**。有可以去的点 → 按 a→b→c→d 的顺序，每个点掷 0–10 的随机数，<5 才去（约 5/11 的机会），而且不能是现在所在的点；挑中就搬，一个都没挑中就这一轮什么也不做。
   - **战舰突袭**（`'tatsu chrono attack'` → `'sub chrono attack'`）：没有任何点"可以去"（包括龙的关键建筑还 >5 座时）就改做这个。地图上 11 个隐形标记点 `Chrono_Spots`，第一个"看得见"玩家关键物体的点被选中，把龙的一艘将军战舰 `JapanAntiStructureShip` 用超时空仪传过去（真的放了一次超时空技能：先选战舰，再在标记点落下）。11 个点：玩家出生地 (2965, 874)、(2398, 868)、(4193, 1909)、(4202, 3253)、(3429, 2839)、(2959, 3615)、(3216, 4299)、(1759, 4284)、(436, 3206)、(951, 1765)、(800, 2277)。哪艘战舰、标记点到底靠什么"看见"（`CPDummyTarget` 的视野）**未确定**。
5. **搬家搬什么**：用 `TELEPORT_STRUCTURE` 把这几座建筑瞬移到新点（`'chronosphere entire base position a'`…）：建造厂、兵营、船坞、电厂 ×4、矿厂 ×2、科技中心、战车工厂、纳米虫群（`japansuperweapon`）、VIP 地堡。每座建筑在每个点有 3 个预设位置，随机挑（矿厂固定）。矿车删掉在新点重造（矿厂还在才造）。每座建筑都放超时空闪光特效、打雷达提示（`'chronosphere entire base effects b'`）。
   **不搬的**：部队、守卫塔等防御、第 3 座矿厂（脚本关着）、**超时空仪本身**（搬家清单里没有它；它被拆后才在新点重生——据脚本推断）。
   每次搬家前重新抓一遍各建筑的引用：原来那座被拆了，就找离得最近的同类建筑顶上（AI 后来造的也算）；顶上来的若是兵营、战车工厂、船坞，**直接给它加二级、三级科技**（`'get reference barracks'` 等；条件是取反的 `NAMED_NOT_DESTROYED`，原来那座还在就什么都不做）。
6. **多久一次**：每轮动作后按龙剩下的关键建筑数重设计时，同时把超时空仪的游戏内倒计时设成一样的值（`'chronosphere reset timer a/b/c'`）。战舰突袭真的用掉了技能，1 秒后再把倒计时改回来（`'reset chrono after attack'`）。

   | 龙的关键建筑 | 充能 |
   |---|---|
   | ≥5 | 90 秒 |
   | 4 | 75 秒 |
   | 3 | 60 秒 |
   | ≤2 | 45 秒 |

   开局龙有 7 座（建造厂、兵营、战车工厂、船坞、VIP 地堡、AI 开机时脚本送的纳米虫群、超时空仪），所以一开始 90 秒一次而且只会战舰突袭；玩家拆掉 2 座以后才开始搬家，越拆越快。
7. **预警**：没有专门的倒计时或通报。玩家能看到的只有超时空仪本身的技能倒计时（被脚本同步过）、搬家时的闪光和雷达事件；前三次搬家各有一句台词（`'audio - tatsu chronospheres 1/2/3'`：第 1 次 md28+md30，第 2 次 md32，第 3 次 md31）。
8. **什么让它停下**：
   - 龙低电 → 整套都不动（电厂最多 4 座，`'tatsu has limited powerplants'`）；
   - 超时空仪被拆 → 停 30 秒以上，等重生；
   - 建造厂没了 → 超时空仪不再重生；
   - 没有将军战舰 → 战舰突袭空放（**未确定**会发生什么）。
9. **为什么搬得动**：龙的每类建筑被限制成最多 1 座（建造厂/基地车、兵营、船坞、战车工厂、科技中心、两种超武），电厂最多 4、矿厂最多 2（`'tatsu has limited conyards'` 等 9 条），正好对上每个点的预设位置。

**4 个基地点在哪：未确定。** 区域 `area_tatsu_basearea_a..d` 和航点的名字导出里都是空的。线索：a 是龙原来的东北基地（`current_chronobase_destination` 初值 1，AI 开机时在 `wp_tatsu_chronobase_a_*` 造矿厂和纳米虫群）；b 很可能在高良的西北基地附近（玩家进 `area_tatsu_basearea_b` 会提前唤醒高良，`'enable naomi ai'`）；按航点密度推测另两个在中央台地和东南台地。`area_tatsu_basearea_c` 和 `_e` 是"开始建基地"台词的触发区（`'audio - start building'`），所以 c 很可能是中央突破口——也就是龙会把基地搬到玩家打下来又离开的突破口。

**龙的自保**：纳米虫群就绪、且玩家已经发现了他的建造厂时，把虫群罩在自己的建造厂上（`'nanoswarm hive protects conyard'`，重复）。

### 3.4 "拉平"部队（按玩家兵力生成）

龙背叛过场开始那一刻（`t_sc_tatsu_setup`）数一次玩家的东西，按配比给龙生成部队，出生在龙基地里 30 个随机标记点之一（`PlyrNeutral/Spots`），生成后交给 AI（`'sub oncreate levelers'`）。只数这一次。

| 玩家每有 | 龙得到（简单 / 普通 / 困难） | 脚本 |
|---|---|---|
| 1 架先兆炮艇、1 座机场或 1 座质子对撞机 | 一个队（`Anti_Harbinger_Team_EASY` 预设队 + 天狗机甲 3 + 弓箭少女 4）/ 天狗 3 + 打击者 2 + 火箭天使 1 / 天狗 4 + 打击者 2 + 火箭天使 1 | `'sub counter harbingers *'` |
| 1 辆和平使者、1 座战车工厂或 1 座船坞 | 鬼王 1 + 海啸 1 / 鬼王 2 + 海啸 1 / 鬼王 2 + 海啸 2 | `'sub counter pacifiers *'` |
| 每 5 辆车（不满 5 也算一份） | 海啸 2 / 鬼王 1 + 海啸 1 / 鬼王 2 | `'spawn anti vehicle teams *'` |
| 每 5 个步兵 | 帝国武士 2 / 天狗 1 / 天狗 2 | `'spawn anti infantry teams *'` |
| 每 5 架飞机 | 弓箭少女 2 / 3 / 4 | `'spawn anti aircraft teams *'` |

（"天狗"指 `JapanAntiInfantryVehicle`，"打击者"指 `JapanAntiAirVehicleTech1`。注意我们 `experimental/cnv/glossary.py` 里这两个中文名对应的模板好像是反的，`jammer_bench.py` 把 `JapanAntiInfantryVehicle` 叫作 Mecha Tengu。）

## 4. 段

| 段 | 玩家要做 | 压力从哪来、怎么关掉 | 结束 |
|---|---|---|---|
| 0 开场过场 | 看 | — | 约 32 秒（两段镜头 16 s + 11 s，加上淡入淡出；还要等两段视频播完） |
| 1 打开突破口 | 展开基地车 | 前哨巡逻；守军被打才反击；无计时进攻 | 有建造厂 |
| 2 打败高良 | 打高良的基地；可选去占通讯塔 | 高良遭遇战 AI、爬行炮塔、伪装运输车（拆光他的关键建筑就停） | 高良的关键建筑全没 + 他的认输台词播完 |
| 3 打败龙 | 全图追龙的基地 | 龙遭遇战 AI、拉平部队、巨型要塞、超时空搬家 / 战舰突袭（断电、拆超时空仪、拆建造厂可以压住） | 龙的关键建筑全没 |

实际时间（三个难度一样，脚本里没有按难度改的计时）：

- 0 s：黑屏；约 32 s 过场结束。之后 +1 s 自动存档 0，+2 s 亮出目标 1（`'sc intro end'`、`'autosave 0'`、`'issue objective 1'`）。
- 目标 1 完成（玩家自定）→ +1 s 高良出场台词 ATH03TK01 → 台词完 +2 s 缓冲 → 亮出目标 2，再 +1 s 亮出奖励目标（`'objective 1 completed'`、`'th - takara intro'`、`'issue objective 2'`、`'issue objective b1'`）。
- 目标 2 生效（亮出后约 5 s）= 高良唤醒 T2。T2+0–180 s 炮塔、伪装车陆续出发，T2+210 s 高良的全部部队交给遭遇战 AI。
- 高良关键建筑全没 → +2 s 认输台词 CH16TK02 → 播完 +3 s → 目标 2 完成；炸掉中间那排仓库；+1 s 地图扩大到全图、"战场扩大"通报、龙的巨型要塞和将军战舰并入龙；+1 s 自动存档 2；+2 s 起龙背叛过场（约 42 s：龙的部队用精确打击炸逃跑的日军，巨型要塞变形开进；过场末尾把高良残部直接 `PLAYER_KILL`）。
- 过场结束 +2 s → EVA 台词 ATH03EV02 → 播完 +1 s → 亮出目标 3 = T3。T3+1 s 龙 AI 开机；约 T3+35 s 龙拿到超时空仪；T3+60 s 卖掉玩家的超时空仪；T3+121 s 龙的全部部队交给遭遇战 AI；约 T3+125 s 第一次超时空动作，之后每 90→45 s。

```yaml
段:
  - 名字: 打开突破口
    目标: [在任一突破口建立基地]
    开场: [{镜头: start}]              # 过场 'Intro Cine'
    存档: 是                            # 'autosave 0'
    结束: 建成 建造厂
  - 名字: 打败高良
    目标: [打败高良, 占领废弃通讯塔]
    开场: [通报 高良出场（视频 ATH03TK01）]
    结束: [高良.关键建筑全没, 台词 CH16TK02 播完]   # 词表写不出"敌方某一方没有某类建筑"
  - 名字: 打败龙
    边界: whole                         # MAP_SWITCH_BORDER(0)
    目标: [打败龙]
    开场:
      - {摧毁: 中间那排仓库}
      - 通报 战场扩大了
      - 龙背叛过场
    存档: 是                            # 'autosave 2'
```

## 5. 目标

| 标题（原文） | 主/奖励 | 完成 | 失败 | 标记 |
|---|---|---|---|---|
| Set Up a Base at Either Breach Point | 主 | 玩家有建造厂（不看位置） | 这一段里玩家关键单位全没 | 两个突破口 |
| Defeat Takara | 主 | 高良关键建筑全没（`'japan naomi is defeated'`） | 同上 | 3 个标记，持续指向**离标记最近的剩余关键建筑**，被拆一个就换（`'obj objective 2 mark target a/b/c'`） |
| Defeat Tatsu | 主 | 龙关键建筑全没（`'japan tatsu is defeated'`） | 同上 | 同上，3 个 |
| Capture the Abandoned Com Tower | 奖励 | 通讯塔归玩家（`'objective b1 completed'`） | 通讯塔被毁，**或者**目标 3 完成时还没占（这时脚本顺手把塔炸了，`'objective b1 failed'`） | 通讯塔 |

奖励给什么（`'tatsu hands over bonus units'`）：塔边上 4 辆中立的鬼王闪白光、转给玩家，EVA"获得增援"；以通讯塔为中心永久揭开半径 1500 的地图，塔被毁时盖回去（`'reshroud if radar destroyed'`）。脚本名说是"龙交出奖励部队"——这时龙还是"盟友"。龙在第 2 段对玩家是什么外交关系，脚本里看不出，**未确定**。

```yaml
目标:
  在任一突破口建立基地:
    标记: [breach center, breach southwest]
    完成: 建成 建造厂
  打败高良:
    标记: 最近的 3 座高良关键建筑（会换）
    完成: 高良.关键建筑全没
  打败龙:
    标记: 最近的 3 座龙关键建筑（会换）
    完成: 龙.关键建筑全没
  占领废弃通讯塔:
    奖励: 是
    标记: [com tower]
    完成: 占领 com tower
    失败: {任一: [摧毁 com tower, 目标 打败龙 完成]}
```

## 6. 进攻

**这一关没有一条写死的出兵波次。** 压力全部来自预先摆好的部队、两个遭遇战 AI 和机关。

### 6.1 第 1 段：前哨（Japan_3）

- 巡逻：两队坦克杀手各沿一条航点路线攻击移动（`'setup forward positions'`）。
- 守军：坦克队或步兵队任何一个被玩家打了，坦克队整队去打玩家（`'if guard tanks attacked'`）；步兵队被打，步兵队整队去打（`'if infantry attacked'`）。没人打它们就不动。
- 没有计时进攻、没有 20～30 秒的象征性威胁。
- 目标 1 完成时，前哨的守军和巡逻全部转给高良（`'clean up objective 1 stuff'`），算进高良的兵力。

### 6.2 第 2 段：高良（Japan_1）的遭遇战 AI

`'enable naomi ai'`，条件：目标 2 生效，**或者**玩家提前走进 `area_tatsu_basearea_b`（哪个先到算哪个）。

| 设置 | 值 |
|---|---|
| 单位 AI | 开（`UNIT_AI_TRANSFER_ALL(…, 1)`：单位自己会反击，但还不受遭遇战 AI 调度） |
| 基地 | `wp_japan_1_base` |
| 对所有敌人的优先级 | 20 |
| 修理 / 按原位重建 | 都关 |
| 资金 | 1000（三个难度一样） |
| 将军技能点 | 上限 0、现有 0（`'prevent naomi from buying specials'`，开局就设） |
| 禁造 | 巨型要塞（蛋和本体） |
| 交给遭遇战 AI | 唤醒后 210 秒（`'finish turret spam'`，`SKIRMISH_AI_TRANSFER_ALL(…, 1)`） |
| 进攻种类逐步放开 | **没有**。脚本里没有放开进攻种类的旗标；只有台词脚本提到 AI 的一个攻击状态名 `AIState_EP01_A03_NaomiAngelAttacks_SimpleAttack`（火箭天使进攻，`'audio - takara has air'`），说明 AI 的进攻配置在地图外的 AI 数据里，**未确定** |

另加 3.2 的爬行炮塔和伪装运输车。拆光高良的关键建筑：AI 关掉、卖光所有建筑、残兵逃跑，炮塔和伪装车全部炸掉（`'japan naomi is defeated'`）。

### 6.3 第 3 段：龙（Japan_2）的遭遇战 AI

`'tatsu turn on ai'`，条件：目标 3 亮出 1 秒后且目标 3 生效。

| 设置 | 值 |
|---|---|
| 单位 AI | 开 |
| 基地 | `wp_japan_2_base` |
| 优先级 | 20 |
| 修理 / 重建 | 都关 |
| 资金 | 2000（三个难度一样） |
| 将军技能点 | 0 |
| 脚本白送 | 矿厂 2、纳米虫群 1（造在 a 点的预设位置） |
| 建造上限 | 每类 1 座、电厂 4、矿厂 2（3.3 第 9 条） |
| 交给遭遇战 AI | 开机后 120 秒（`'give units to tatsu'`；同时转交的 `Japan_2/Anti_Harbinger_Team` 不带难度后缀，可能根本不存在，**未确定**） |

兵力来源：龙的预置部队 + 过场部队 + 巨型要塞 2（简单、普通各 1）+ 将军战舰 2 + 3.4 的拉平部队 + AI 自己造的。
加上 3.3 的超时空：搬家本身不打人，但会把基地挪到玩家够不着的地方；战舰突袭会把将军战舰直接送到能看见玩家基地的地方。

```yaml
进攻:      # 只能近似：原版没有波次，这里把遭遇战 AI 和机关当成"进攻"列出来
  - 名字: 高良
    开始: {任一: [段 打败高良, 进入 naomi base]}
    来源: 高良的关键建筑（全部）
    # 遭遇战 AI，写不进词表
  - 名字: 爬行炮塔
    开始: 段 打败高良 + 随机 0–180 秒（见 3.2），或者被看见
    兵: {守卫塔蛋: 3, 波能塔蛋: 0/2/3}
    打: 玩家最近的关键建筑（开到看见玩家就展开）
  - 名字: 伪装运输车
    开始: 段 打败高良 + 随机 0–90 秒，或者被看见
    兵: {突击运输车: 3, JapanArcherInfantry: 12}
    打: 玩家最近的单位或建筑（看见就卸兵）
  - 名字: 龙
    开始: 段 打败龙 + 0:01
    来源: 龙的关键建筑（全部）
  - 名字: 战舰突袭
    开始: 超时空机关决定
    兵: {将军战舰: 1}
    打: 第一个看见玩家关键物体的超时空标记点
```

## 7. 规则：提示、兜底、对话、存档、援军

**对话排队**：所有台词、视频、目标弹出、过场共用 4 个"正在播放"旗标（`f_is_audio_playing` / `f_is_movie_playing` / `f_is_objective_display_active` / `f_is_cine_playing`），每句后留 1～5 秒缓冲；段落切换和胜负都等它们全空。

**由玩家行为触发的台词**（`'audio - *'`）：

| 条件 | 台词 |
|---|---|
| 目标 1 期间选中基地车 | md20 |
| 目标 1 期间基地车血量 ≤85% | md21 |
| 目标 1 期间玩家走进 area c 或 e（突破口） | md22（"开始建"） |
| 目标 2 期间玩家看见炮塔展开 | md24 |
| 目标 2 期间高良的火箭天使攻击队出现 | md25 |
| 目标 3 期间龙有巨型要塞 | md43 |
| 龙第 1/2/3 次搬家 | md28+30 / md32 / md31 |
| 龙拿到超时空仪 | 龙视频 ATH03TS04 |
| 龙认输（目标 3 完成） | 龙视频 ATH03TS05，播完胜利 |

另有 md23、26、27、29、33～40、42、44 有播放脚本但没有触发，`'audio - player has pacifier'`、`'th tatsu 01/02/03 play'`、`'th 01 play'` 等是关着的、也没人打开，是剪掉的内容。

**兜底**：没有。没有"N 分钟还没做到就提示"，没有给玩家钱或援军（剪掉的 `'th 01 end'` 原本要在 EVA 台词后送 4 辆和平使者，计时器设了但没有接收脚本）。唯一的"帮忙"是奖励目标的 4 辆鬼王和揭图。

**给敌人兜底**：搬家时矿车删了在新点重造；兵营、战车工厂、船坞被拆后，AI 重造的那座直接带满科技；超时空仪被拆 30 秒重生；纳米虫群保护建造厂。

**自动存档**：2 次——过场后（`'autosave 0'`）、地图扩大时（`'autosave 2'`）。`'autosave 1'` 名不副实，只卖墙。

**过场保护**：过场期间玩家默认队无敌、全图揭开、禁输入（`'sc set cine environment'`）。

```yaml
规则:
  - 当: 建成 建造厂 + 0:02
    做: [{卖掉: barrier}]                 # 'autosave 1'
  - 当: 目标 占领废弃通讯塔 完成
    做: [{转给我: free onis}, 通报 获得增援, {揭开: com tower, 半径: 1500}]
  - 当: 段 打败龙 + 1:00
    做: [{卖掉: 玩家的超时空仪}, {禁造: 超时空仪}]
```

## 8. 输赢

- **胜利**：龙认输视频播完（`'Victory Condition (OVERRIDE ME)'` 等 `t_tatsu_losing_done` + `f_mission_complete`）。也就是龙的关键建筑清单全没。
  - 关键建筑清单（`'_OBJECT LIST_Japan Loss Condition'`）：兵营、建造厂、船坞、两种超武、战车工厂、它们的蛋、两种基地车、**超时空仪**、**VIP 地堡**。电厂、矿厂、科技中心、防御不算。
  - 超时空仪在清单里，又会在建造厂还在时 30 秒重生——所以实际要先拆建造厂（或者同时清）。
  - `'all objectives accounted for'` 设了一个叫 `t_tatsu_defeated` 的**旗标**，没人读，死代码。
- **失败**：每一段各一条，玩家"关键单位清单"`_object list_allied loss condition` 一个都没有（`'player lost relevent units objective 1/2/3'`），该段目标标为失败、任务失败。清单内容在脚本里没定义（地图级），**未确定**，按惯例应是建造厂和基地车。

```yaml
胜利: 龙.关键建筑全没
失败:
  - {当: [没有 建造厂, 没有 基地车], 原因: 未确定（原版没有显示原因，只把当前目标标红）}
```

## 9. 难度

脚本里只有两处按难度分：删单位、拉平部队的配比。资金、AI 资金、唤醒时间、超时空充能、所有计时三个难度一样。（AI 本身的强弱也许随游戏难度走，**未确定**。）

| 删掉的 | 简单 `'EASY delete units'` | 普通 `'MEDIUM delete units'` | 困难 |
|---|---|---|---|
| 龙的巨型要塞（`easy_delete_a`） | 删 | 删 | 留（2 艘） |
| 龙的海翼 3（`easy_delete_b/c/d`） | 删 | 留 | 留 |
| 过场部队里的打击者 2（`easy_delete_e/f`） | 删 | 留 | 留 |
| 高良的波能塔蛋 D / E / F | 全删 | 删 D | 留 |
| 前哨弓箭少女 4（`w/x/y/z`） | 全删 | 删 w、z | 留 |
| 前哨坦克杀手 4（`g/h/i/j`） | 全删 | 删 g、j | 留 |
| 前哨 `JapanAntiInfantryVehicle` 1（`k`）、海啸 1（`l`） | 删 | 留 | 留 |

拉平部队配比见 3.4。没有标错开关的脚本（名字里的 HARD / MEDIUM / EASY 和开关一致）。

## 10. 我们的词表写不出的

按重要程度排。

1. **整座基地超时空搬家**（`'Chronosphere Base Structures'` 整组、`'evaluate need to chrono base'`、`'evaluate relocation area a..d'`、`'initiate chronobase to site a..d'`、`'chronosphere entire base position a..d'`）。把一组建筑按"每点每座 3 个预设位置"瞬移到 4 个点之一；挑点的规则是"玩家**不在**那里"（单位 <5 且建筑 <2）、不是当前点、逐点掷骰。我们的"自由号"是一个单位跳向玩家防守**最空**的地方去**进攻**再跳回家；没有"把基地挪走、躲开玩家"的机关，也没有"建筑瞬移""每点多套布局"。
2. **充能随敌人剩余关键建筑数变快**（`'chronosphere reset timer a/b/c'`：≥5→90 s、4→75、3→60、≤2→45），并同步到游戏内超武倒计时（`NAMED_SET_SPECIAL_POWER_COUNTDOWN`）。自由号的 `每隔` 只能按难度写死；也没有"让玩家看到的超武倒计时和机关一致"的写法。
3. **搬家和突袭二选一**：没有可去的点（含敌人还 >5 座关键建筑）就改用真超时空技能把一艘将军战舰送到"看得见玩家关键物体"的标记点（`'tatsu chrono attack'`、`'sub chrono attack'`）。我们没有"按条件在两个动作之间切换"的机关，也没有"落点 = 能看见玩家基地的点"。
4. **机关的停止条件是多重的、可恢复的**：敌方低电（`PLAYER_HAS_POWER`，不是某一座指定电站）、超时空仪被拆后 30 秒在当前点重生、建造厂没了才彻底停（`'chronosphere destroyed'`、`'respawn tatsu chronosphere'`）。自由号的 `电站` 是一个角色，一断就永久断。
5. **遭遇战 AI 指挥官**（`'enable naomi ai'`、`'tatsu turn on ai'`）：基地点、优先级、修理/重建开关、AI 资金、将军技能点清零、禁造某单位；而且分两步交权——先 `UNIT_AI_TRANSFER_ALL`（单位自卫），过 210 / 120 秒再 `SKIRMISH_AI_TRANSFER_ALL`（AI 调兵进攻）（`'finish turret spam'`、`'give units to tatsu'`）。词表只有写死的 `进攻`。
6. **多个敌方玩家**：Japan_1、Japan_2、Japan_3 三方，按段唤醒；前哨在目标 1 完成时整体转给高良（`'clean up objective 1 stuff'`）；龙的惰性部队在第 3 段并入龙（`TEAM_MERGE_INTO_TEAM`）；高良残部在过场里被抹掉（`PLAYER_KILL`）。词表只有一个"敌"，"其他"只能从中立翻脸。
7. **敌方 AI 的建造上限**（`'tatsu has limited *'` 9 条：每类最多 1、电厂 4、矿厂 2，用重复脚本动态 ALLOW/DISALLOW）。
8. **按玩家兵力组成生成的"拉平"部队**（`'Leveling Out'` 整组）：每架炮艇/每座机场/每座质子对撞机、每辆和平使者/每座战车工厂/每座船坞各一队，每 5 辆车/5 个步兵/5 架飞机各一队，分难度配兵。词表的 `兵` 是固定数，`加码` 只能按条件加固定的兵。
9. **会走的炮塔和伪装运输车**（`'naomi turret spam sequence a..f'`、`'naomi fake turret spam sequence a..c'`、`'disguise fake turrets'`）：朝玩家最近的关键建筑开，看见玩家就展开 / 卸兵并换主人。需要"移动目标 = 玩家最近的某类物体""看见即触发""用单位技能（展开、紧急卸载、伪装）"三样，词表都没有。
10. **随机时间窗**（`SET_RANDOM_MSEC_TIMER`，例如 0–30 s、60–90 s）和**随机挑位置**（`SET_RANDOM_COUNTER`）。词表只有固定时间。
11. **"敌方某一方的某类建筑全没了"作为条件**（`'japan naomi is defeated'`、`'japan tatsu is defeated'`，清单含 AI 后造的建筑、蛋、基地车）。词表的 `摧毁 <角色>` 只认摆好的角色，`没有 <单位>` 只看玩家。
12. **目标标记跟着最近的剩余目标走**（`'obj objective 2/3 mark target a/b/c'`：3 个标记，被拆一个就换到离它最近的下一座）。词表的 `标记` 是固定角色，只能摘不能换。
13. **被打才反击的守军、沿路线巡逻**（`'if guard tanks attacked'`、`'setup forward positions'`）："攻击 <角色>" 能当条件，但没有"让已经摆好的这队转为进攻"的动作；`守` 是原地守，没有巡逻路线。
14. **敌人用自己的超武保护自己**（`'nanoswarm hive protects conyard'`：就绪且玩家已发现建造厂时罩住建造厂）。条件"玩家发现了某建筑"和动作"敌方放技能"都没有。
15. **改玩家的科技**（`'setup player tech lockouts'` 禁未来坦克；`'if player has a chronosphere'` 卖掉玩家的超时空仪并禁造）。
16. **奖励的揭图**（`MAP_REVEAL_PERMANENTLY_AT_WAYPOINT` 半径 1500，塔被毁再盖回）和 **AI 不打某物 / 不占某矿**（`SKIRMISH_AI_DO_NOT_ATTACK`、`SKIRMISH_AI_DO_NOT_TAKE`，`'mission setup'`）。
17. **打败一方后的收尾**：AI 关机、卖光建筑、残兵逃跑（`PLAYER_SELL_EVERYTHING`、`PLAYER_SET_ALL_UNITS_TO_FLEE`）。词表只有 `摧毁 <角色>`。
18. **由玩家操作触发的台词**：选中基地车（`NAMED_SELECTED`）、看见炮塔、某个 AI 攻击队出现（`TEAM_HAS_UNITS('…AIState_…')`）、机关第 N 次发生（`COUNTER('c_tatsu_times_chronosphere', ==, N)`）。词表能写 `血量 <角色> < 50`、`进入 <地点>`，其余没有。
19. **段落切换等对话播完**：原版每一段的结束都要等 4 个"正在播放"旗标空闲（第 7 节），我们的 `结束` 只看条件，目标按固定 2 s + 4 s 间隔弹出。
20. **卖掉**（`SELL_OBJECT`）和 **摧毁**不同（卖有动画、退钱）——小事，`'autosave 1'` 卖墙、`'if player has a chronosphere'` 卖玩家建筑都用它。

词表**能**写的：奖励目标"占领 / 被毁或后续主目标完成就失败"、通讯塔旁的中立鬼王 `转给我`、炸掉中间那排仓库（如果把它们写成角色）、换边界、两次存档、难度删单位（写成 `简单/普通/困难` 的数量）。

## 11. 和我们 A7 比

只写有实质的差别。

1. **首领机制方向相反。** 自由号是"进攻型跃迁"：跳到玩家**最空**的落点放兵，停 30 秒回家，每次提前 15 秒报警。龙是"逃跑型跃迁"：整座基地跳到玩家**不在**的点；真正打到玩家脸上的是将军战舰突袭，落点是"能看见玩家基地"的标记点。龙没有专门的预警（只有超武倒计时和闪光）。玩家在 A7 学"守住空当、找电站"，在宫古岛学"追着打、先钉死它"。
2. **越打越频繁，而不是一刀断。** A7 拆 / 占一座电站就永久断电，然后进入"飞走倒计时"段。龙越输跑得越快（90→45 秒），而且要拆 2 座关键建筑后才开始搬；压住它的办法有三层：打低电（4 座电厂里的几座）→ 拆超时空仪（30 秒重生）→ 拆建造厂（不再重生）。A7 的弱点是一个角色，原版的弱点是一个"系统"。
3. **敌方基地靠遭遇战 AI 施压，不靠波次。** 原版两位指挥官都是遭遇战 AI，钱很少（1000 / 2000，不分难度），不修不重建，没有将军技能，分两步交权（先自卫，210 / 120 秒后才调兵）；龙还有建造上限，保证他的基地搬得动。A7 东岸是写死的三路波次加"来源"。我们在 a7.md "还没做的"里自己列过这一条。
4. **对玩家阵容的针对。** 原版在背叛那一刻按玩家的炮艇、和平使者、车 / 步兵 / 飞机数量给龙生成克制部队；A7 的兵力和玩家造什么无关。
5. **节奏完全由玩家推进，没有任何计时失败。** 三段都等玩家做到；没有"6 分钟后强制进下一段"，没有第 3 段那种倒计时输。第 1 段连象征性进攻都没有（守军被打才动）；第 2 段的第一股压力是唤醒后 0～30 秒随机出发的爬行炮塔和伪装车，A7 是 30 秒定时骚扰。
6. **两位首领，中间夹一个背叛。** 原版是"打完盟友交代的敌人，盟友翻脸"；A7 是开局就知道司令叛变、哨所真假要侦察。原版的背叛在一个过场里完成：边界扩大、隔墙炸掉、惰性舰队并入、拉平部队生成、自动存档。
7. **奖励和兜底都更少。** 原版 1 个奖励（占通讯塔 → 4 鬼王 + 揭图），没有任何"N 分钟还没做到"的提示，没有援军，存档 2 次。A7 有 2 个奖励（占电站给电、拆东岸停兵）、8 分钟提示、断电送防空部队；存档也是 2 次（第 2、3 段开头）。
8. **胜利条件。** 原版"打败龙"= 关键建筑清单全没（含会重生的超时空仪和 VIP 地堡，标记会自己换到最近的剩余目标）；A7 = 击落一个单位，标记固定。

## 附：原版里的死代码和笔误

- `'if player takes base a'`：按区域判定"在突破口建基地"的子程序，没人调用。
- `'autosave 1'`：不存档，只卖墙。
- `'th - intro pacifier'`、`'th 01 play'`、`'th tatsu 01/02/03 play'`、`'th - intro objective 1'`、`'th - intro objective 3 a'`、`'th - intro objective bonus'`、`'audio - player has pacifier'`：开关关着、没人打开。`t_spawn_siege_tank_a..d` 设了没人读。
- `'enable naomi ai'`：炮塔 E 的计时设了两次，炮塔 F 没设。
- `'all objectives accounted for'`：设的是旗标 `t_tatsu_defeated`，没人读。
- `'give units to tatsu'`：转交的 `Japan_2/Anti_Harbinger_Team` 不带难度后缀。
- `'clean up objective 1 stuff'`、`'japan naomi is defeated'`：用到 `Japan_3/Missile_Guards` 队，但地图上没摆这个队的单位。
- `'evaluate possibility of relocation'`：设了 `c_tatsu_ambush_location`，没人读。
