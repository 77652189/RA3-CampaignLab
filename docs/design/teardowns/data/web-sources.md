# 联网调研：SC2《自由之翼》两关拆解 + 设计理论出处

调研日期：2026-10-27。只查公开资料，未改项目文件。
说明：Liquipedia 和 StarCraft Wiki（fandom）网页直连被 403/402 拦截，内容通过两站的 MediaWiki API 取 wikitext 读到（页面 URL 照常给出）。"未确认"表示只有单一非官方来源或来源互相矛盾。

常用来源缩写：
- [LQ-ZH] https://liquipedia.net/starcraft2/Campaign/Zero_Hour
- [FD-ZH] https://starcraft.fandom.com/wiki/Zero_Hour
- [SW-ZH] https://strategywiki.org/wiki/StarCraft_II:_Wings_of_Liberty/Zero_Hour
- [LQ-DP] https://liquipedia.net/starcraft2/Campaign/The_Devil%27s_Playground
- [FD-DP] https://starcraft.fandom.com/wiki/The_Devil%27s_Playground
- [DTOID] Destructoid 对 Dustin Browder 的采访 https://www.destructoid.com/destructoid-interview-starcraft-iis-dustin-browder/

---

## A1. Zero Hour（零点，Mar Sara 第 3 关）

### 基本事实
| # | 事实 | 来源 |
|---|---|---|
| 1 | **时长**：纯坚守，倒计时 20 分钟等 Hyperion 撤离，实际通关时间略超 20 分钟。 | [LQ-ZH]、[SW-ZH] |
| 2 | **开局**：玩家在地图**右下角**，基地已经建好，有一批 SCV（要继续补，攻略建议补到约 25 个）；开局送 **4 座地堡**：2 座在主斜坡顶，2 座分别在两座桥头。还有一队初始陆战队（SW 攻略提到可分 4 人守下桥、12 人外出）。 | [LQ-ZH]、[SW-ZH] |
| 3 | **地图结构**：基地从地面只能经**两座桥**进入（fandom：accessible "by only two bridges"），桥后汇到一条**主斜坡**上高地。攻略普遍建议放弃桥头地堡、收缩到斜坡顶集中火力；高地让蟑螂/刺蛇没有视野时打不到地堡。地图上有 3 个虫族基地共 **8 个孵化场**：左上 2、右上 3、左下 3。基地外有中立建筑提供视野。 | [FD-ZH]、[LQ-ZH]、[SW-ZH] |
| 4 | **教的东西**：本关解锁**地堡（Bunker）+ 导弹塔（Missile Turret）**（Liquipedia）；fandom 写的是 Bunker + Reactor。**新兵种不是 Firebat**——火焰兵在下一关 The Evacuation 才给（fandom The Evacuation 页 newunit=Firebats）；医疗兵在上一关 The Outlaws 给。所以本关"新东西"是防御建筑而非单位。 | [LQ-ZH]、[FD-ZH]、https://starcraft.fandom.com/wiki/The_Evacuation |
| 5 | **奖励**：55,000 credits；无研究点。可选目标"救援被困的反抗军"（3 组），救下后归玩家控制；救援点附近有资源箱（每对箱子够一次升级）。 | [LQ-ZH]、[FD-ZH]、[SW-ZH] |
| 6 | **"虫巢"并非列出的奖励目标**：打孵化场只与成就挂钩——"The Best Defense..."（困难难度摧毁 4 个孵化场），10 周年成就 "A Strong Offense"（普通难度摧毁全部 8 个）。虫族会重建被拆的孵化场，拆重建中的也算。 | [LQ-ZH]、[FD-ZH] |
| 7 | **敌人优先目标**：虫族优先攻击神器卡车而不是指挥中心；只有全部建筑被毁才算输（可把建筑升空飞走苟活，高难度有飞龙时无效）。 | [FD-ZH]、[LQ-ZH] |
| 8 | **难度差别**：休闲难度不能建工程站和导弹塔；困难/残酷：虫族有攻防升级、更主动，派**蟑螂**（残酷还有**爆虫**），菌毯铺满地图并把**脊针爬虫前移**，定期用**空投囊（sac）**往基地砸跳虫和菌毯瘤；外围中立建筑会被摧毁（失去视野）。 | [FD-ZH] |
| 9 | **成就 "Hold the Line"**：普通难度不损失、不回收任何建筑通关——即"守住两座桥"的玩法。结尾过场里会有多条**虫道（nydus worm）**在西桥右侧、东北桥中央钻出拆建筑，过场损失也算。 | [FD-ZH]、[LQ-ZH] |
| 10 | **设计渊源**：与初代 SC 第 3 关 Desperate Alliance 同构（都是 Mar Sara、都是第 3 关、都是两入口坚守）。BlizzCon 2008 演示版就已是"两桥守家"，攻势"slowly escalated from a light trickle of Zerg"（TenTonHammer 记者描述）。 | [FD-ZH]、https://www.tentonhammer.com/articles/blizzcon-2008-starcraft-ii-gameplay-panel |

### 攻势时间线（倒计时剩余时间；公开资料拼出来的，**不是官方数据**）
StrategyWiki 说波次**不是随机的**：每波单位数固定、每次在同一时刻放出。

| 剩余时间 | 发生什么 | 来源 |
|---|---|---|
| 约 20:00–17:00 | 首波在玩家造完第一个带科技挂件的兵营、开始出医疗兵/陆战队时到达（具体秒数未确认）；第一组飞龙约在造好上桥地堡时出现。 | [SW-ZH] 建造顺序注释 |
| 约 17:20 | 第 1 组反抗军出现（5 陆战队），右侧/东侧，过桥上小坡，路上有两组埋地虫族（第二组有刺蛇）。 | [SW-ZH]、[LQ-ZH] |
| 约 15:00 | 第 2 组反抗军（1 医疗兵 + 3 陆战队），地图中央大路。 | [SW-ZH] |
| 全程 | 波次**左右两侧交替**，主体是跳虫，越往后越多、越强：先夹 1–2 刺蛇，有时 1–2 蟑螂，后期两者都有。另有约 3 组"每组 3 只飞龙"的小波次（第 1 组打上方中央导弹塔，第 2 组打左下地堡），以及周期性空投囊（部分只是演出会爆掉，部分落下跳虫或菌毯瘤，菌毯瘤之后长脊针爬虫，堵救援路线）。 | [SW-ZH] |
| 约 10:00–11:00 | 攻略建议此时（左桥刚打退一波后）出击打孵化场——说明这是两波之间的"空窗"。 | [SW-ZH]、https://www.gamepressure.com/starcraftiiwingsofliberty/zero-hour-achievements/z3269b |
| 9:05 | 第 3 组反抗军（1 医疗兵 + 5 陆战队），左侧，在左下/左上虫族基地交汇处的小坡上。没及时救会被附近虫族杀掉。 | [SW-ZH] |
| 约 5:30 | 满级升级（带翅膀）的跳虫出现。 | [SW-ZH] |
| 约 4:00 | 唯一一次**两侧同时**进攻。 | [SW-ZH] |
| 1:00 | 进入**无尽波次**（"unending waves"）。 | [LQ-ZH] |
| 0:00 | Hyperion 到达用舰炮清场，结尾过场虫道钻出。 | [FD-ZH] |

---

## A2. The Devil's Playground（魔鬼的游乐场，Redstone III）

| # | 事实 | 来源 |
|---|---|---|
| 1 | **胜利条件**：采集 **8,000 矿**（Liquipedia、portforward、一份 2011 攻略博客一致）。fandom 写"6000，随难度变化"——**按难度的具体数字未确认**。矿是"存够"制，花掉的不算，所以 Horner 提醒控制开销。 | [LQ-DP]、[FD-DP]、https://portforward.com/games/walkthroughs/Starcraft-2-Wings-of-Liberty/Mission-5-The-Devils-Playground.htm |
| 2 | **岩浆周期**：Browder 发售前说低地"flooded by lava every five minutes"（每 5 分钟淹一次）；攻略博客说每 5 分钟涨一次、持续约 1 分钟。正式版是否仍为 5 分钟**未确认**。 | [DTOID]、http://blizzard-starcraft-2-guide.blogspot.com/2011/07/mission-6-starcraft-ii-campaign-walk.html |
| 3 | **预警**：除残酷外各难度都有"下次涨潮"倒计时；残酷没有计时器，只靠警报和岩浆发亮——约提前 30 秒有灼烧声，约提前 15 秒副官语音提示（单一玩家攻略，未确认精确值）。被岩浆淹到的单位和建筑直接摧毁。 | [FD-DP]、[LQ-DP]、https://troublmaker.wordpress.com/2010/08/16/how-to-the-devils-playground-brutal-and-reaper-man/ |
| 4 | **地图结构**：最富的矿点在**低地**（会被淹）；主基地在**高地**（安全）。经典解法：指挥中心落在低地矿区中间采，涨潮前装 SCV 升空；或者每次涨潮前把 SCV 拉回高地。Liquipedia 说预警"plenty of time"。地形多层，死神能跳崖，适合这张图。 | https://starcraft.fandom.com/wiki/Lava、[LQ-DP]、https://www.superjumpmagazine.com/heres-how-starcraft-ii-pulled-off-a-the-floor-is-lava-level/ |
| 5 | **开局**：地图左中部，少量建筑和 SCV（博客：10 SCV、350 矿、200 气）。北边不远有"失踪矿工"：一个指挥中心 + 5 SCV，救下即归玩家（可提前完成，后来才作为目标给出）。 | [LQ-DP]、[FD-DP]、博客同上 |
| 6 | **新单位：死神（Reaper）**。开局约 45 秒送 4 个死神，同时解锁生产；地图上另有多组可救援的 Tosh 手下死神（"Reaper Man" 成就：困难难度找齐全部，Liquipedia 说共 26 人）。 | [LQ-DP]、[FD-DP]、troublmaker 同上 |
| 7 | **奖励目标**：①击杀**雷兽（Brutalisk）**，在地图西南角，守着资源箱，奖励 **3 点虫族研究**；1500 血、50 伤害（Liquipedia）。成就 "Red Lobster" 要求普通难度用岩浆烫死它：把它从东侧坡道引下低地、在涨潮前一刻跳回高地。②找到 Tosh 的矿工。通关奖励 110,000 credits（Liquipedia/博客；fandom 写 100,000，未确认）。 | [LQ-DP]、[FD-DP] |
| 8 | **敌人压力**：虫族"do not attack in great strength"，以小股袭扰为主（多为跳虫加少量刺蛇，可能有飞龙），从不同方向来，建议每个入口一座地堡。主动拆虫族基地可选，拆孵化场掉资源箱（一份攻略说每个 200 矿 100 气）。残酷难度东北角基地有感染虫和一只巢虫领主。 | [FD-DP]、[LQ-DP]、troublmaker 同上 |
| 9 | **安全网**：短时间损失大量 SCV 时 Raynor 补一批（仅一次）；指挥中心全丢时 Horner 补一个（仅一次）。 | [FD-DP] |
| 10 | **设计渊源**：初代 SC 的 Old Faithful 地图有相似机制（采够定额、低地定时毁灭）。开发期名 "Mining Your Own Business"。同机制做成了官方 3v3 自定义图 Burning Tide。 | [FD-DP] |

---

## B. 设计理论出处

### B1. 暴雪谈 SC2 战役"每关一个小游戏/特殊机制 + 新单位"
- **Dustin Browder，Destructoid 采访**（发售前，约 2008–2009，日期未确认）："each mission is like its own minigame"；关卡长度由"这个小游戏能好玩多久"决定。举例：低地每 5 分钟被岩浆淹（即 Devil's Playground）、感染人类只在夜里进攻（即 Outbreak）。他明确反对"这是你的基地、那是敌人基地、去杀"的模式。 [DTOID]
- **Dustin Browder，Game Informer 2009-10-30**："We definitely try to create each mission as its own unique mini-game."；军械库 Swan 每关为你准备一件特殊装备/单位（例："Swan might prepare Firebats for you"）；不去做需要玩家重新学 UI 的机制；设计组有一个"几十种 play 的库"可以反复变奏。 https://gameinformer.com/games/starcraft_ii_wings_of_liberty/b/pc/archive/2009/10/30/feature-lead-designer-dustin-browder-on-story-and-map-design-in-starcraft-ii.aspx
- **"每关一个新单位"作为明文原则：未找到暴雪原话**。能确认的是事实层面：《自由之翼》大多数任务解锁一个新单位或建筑（见 A1 第 4 条、A2 第 6 条），但设计师采访里说的是"每关一个小游戏"+"军械库每关给特殊装备"。
- **GDC 2011，Dustin Browder《Remaking a Classic / The Game Design of STARCRAFT II》**，免费版在 GDC Vault：http://www.gdcvault.com/play/1014488/The-Game-Design-of-STARCRAFT （Game Developer 报道：https://www.gamedeveloper.com/design/gdc-vault-adds-trio-of-free-strategy-game-sessions ）。官方简介说会谈到 RTS 战役设计，但公开报道几乎只讲电竞/多人部分；战役部分讲了什么未确认（需要看视频）。
- 二手来源提到 Browder 的"三幕结构"（低强度开场简报 → 意外变故 → 最终大战）：https://gamedesignskills.com/game-design/real-time-strategy/ ——**该文没给原始出处，未确认**，不建议直接引用。

### B2. Doug Church, "Formal Abstract Design Tools"（Game Developer / Gamasutra，1999-07-16）
URL：https://www.gamedeveloper.com/design/formal-abstract-design-tools
- **Intention（意图）**："Making an implementable plan of one's own creation"——玩家根据对世界和选项的理解，自己定一个能执行的计划。
- **Perceivable consequence（看得见的后果）**："A clear reaction from the game world to the action of the player."
- **Story（故事）**："The narrative thread ... that binds events together"——无论是设计者驱动还是玩家驱动的叙事线，把事件串起来并推动玩家完成游戏。
- 要点：这几样工具会合作也会冲突；脚本化的情节越多，玩家意图的空间越小。例子是 Mario 64：操作简单一致、世界行为可预测，所以玩家能定计划、试、看懂为什么失败。

### B3. Tracy Fullerton《Game Design Workshop: A Playcentric Approach to Creating Innovative Games》
- 书摘（Game Developer）：https://gamedeveloper.com/design/book-excerpt-game-design-workshop
  - 先在头脑风暴阶段就定 **player experience goals**；功能之后再为达成目标去想，并通过 playtest 检验"if the player experience goals are being met"。
  - playcentric 的定义：全程把玩家体验放在心上，每个开发阶段都和目标玩家一起测试。
- 第 5 版出版社页（Routledge）：https://www.routledge.com/link/link/p/book/9781032607016 ——新增"设定以情感为中心的体验目标并管理流程去达成"；目录含第 9 章 Playtesting。

### B4. Jesse Schell《The Art of Game Design: A Book of Lenses》
- 总述：书里有 100 个透镜，每个都是"一组问自己的问题"，帮你从一个角度检查设计（出版社页/书评均这么描述，如 Lost Garden 书评 https://lostgarden.com/2009/02/19/review-of-the-art-of-game-design-by-jesse-schell/ ）。透镜分类大纲（非官方）：https://xmind.app/m/jnM5/
- 透镜编号在不同版本不一样（第 1 版目录 Interest Curve 是 #61，Meaningful Choices #32，Triangularity #33；第 3 版编号未确认），引用时建议只写名字。
- 下面"核心问题"是按书本内容转述，未逐字核对原文：
  1. **Lens of the Interest Curve（兴趣曲线）**：玩家的兴趣随时间应该怎么变？有没有开场钩子？中间是否逐渐上升、峰谷交替、有喘息？结尾是否有压过之前一切的高潮？我凭直觉画的曲线和试玩者实际画的一致吗？**形状**：开场一个小高峰（hook）→ 回落 → 一连串逐渐升高的峰与谷 → 最终高潮 → 短暂收尾。（形状描述的二手佐证：https://notesbylex.com/interest-curve ，引书第 16 章）
  2. **Lens of Meaningful Choices（有意义的选择）**：我让玩家做哪些选择？它们有意义吗？数量合适吗？有没有一个明显占优的策略让选择失效？
  3. **Lens of Triangularity（三角性）**：有没有"低风险低回报 vs 高风险高回报"的取舍？回报大小和风险高低是否匹配？
  4. **Lens of Surprise（惊喜）**：玩家玩的时候会被什么惊到？规则、故事、画面里有没有惊喜？玩家能不能自己制造惊喜？
  5. **Lens of Challenge（挑战）**：挑战是什么？太难还是太易？能否适应不同水平的玩家？难度怎么随玩家进步而提高？
  6. **Lens of Flow（心流）**：目标清楚吗？有没有分散注意力的东西？反馈是否及时直接？挑战是否持续而不过量？

### B5. Ernest Adams & Joris Dormans《Game Mechanics: Advanced Game Design》（New Riders, 2012）
- 书的第 10 章 "Integrating Level Design and Mechanics" 讲 "Missions and Game Spaces"，第 11 章 "Progression Mechanisms" 讲 "Lock-and-Key Mechanisms"（据图书馆目录，可从 https://research.hva.nl/en/publications/game-mechanics-advanced-game-design/ 等查到）。
- 原始论文：Dormans 2010 "Adventures in level design: generating missions and spaces for action adventure games"（PCG 研讨会）https://www.pcgworkshop.com/archive/dormans2010adventures.pdf ——核心句转述：把关卡区分为 **mission（玩家要完成的任务序列）和 space（实际地形布局）两个独立结构，分两步生成**。扩展版：Dormans & Bakkes 2011, IEEE TCIAIG 3(3):216–228。
- Lock and key 的通俗解释：lock 是任何挡住推进的东西，key 是任何让推进变得可能的东西，不必是字面上的锁和钥匙（Boris the Brave 的综述：https://www.boristhebrave.com/2021/02/27/lock-and-key-dungeons ）。

### B6. RTS 战役关卡设计公开复盘（挑 2 篇）
1. **Rade Stojsavljevic，"Postmortem: Westwood Studios' Command and Conquer: Tiberian Sun"**，Game Developer，2000-04-04。https://www.gamedeveloper.com/design/postmortem-westwood-studios-command-and-conquer-tiberian-sun
   - 混排"建基地任务"和"不建基地任务"控制节奏，并允许一关中途达成某目标后切换类型："We tried not to do the same mission twice."
   - 分支子任务：先打子任务会让主任务变容易，等于给设计者一个更细的难度旋钮。
   - 流程：每关先写 2–3 页提案（名字、阵营、难度、地图大小、任务类型、简报、目标、胜负条件、过场、新语音）→ 纸上画图 → 编辑器先地形后建筑 → **脚本占做一关约 2/3 的时间**。
   - 教训：触发器互相组合导致"修好一个场景、坏另一个"；音频脚本锁得太早，试玩才发现"certain objectives were not clear"，只能补屏幕文字。
2. **Greg Street & Ian Fischer，"Classic Postmortem: Ensemble Studio's Age of Mythology"**，Game Developer 杂志 2003-02（网页版 2017-10-30）。https://www.gamedeveloper.com/design/classic-postmortem-ensemble-studio-s-classic-rts-i-age-of-mythology-i-
   - 战役定为头号卖点，专门招内容设计师；剧本评审委员会人太多太早，后来收缩到 2 人。
   - 场景工具要数据驱动、让设计师不依赖程序员；AI 来得太晚，设计师先用触发器"hacked in fake AI"，后来很难拆。
   - 全员每周固定试玩，用来判断"够不够好玩可以发"。对新手团队："double your estimates" 并 "halve your plans for the content"。
- 没找到 C&C/红警系列设计师专门谈任务设计的 GDC 演讲（未确认是否存在）。

### B7. MDA（可选）
- Hunicke, LeBlanc, Zubek, "MDA: A Formal Approach to Game Design and Game Research"，AAAI 2004 Workshop on Challenges in Game AI。https://aaai.org/papers/ws04-04-001-mda-a-formal-approach-to-game-design-and-game-research/
- 一句话：从设计者视角，mechanics 产生 dynamics，dynamics 再带来 aesthetics（玩家体验）；玩家视角正好反过来（据论文原文的二手引述；PDF 未用 MinerU 精读，原文逐字未核对）。
