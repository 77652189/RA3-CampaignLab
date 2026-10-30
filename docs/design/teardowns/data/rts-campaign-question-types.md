# 即时战略战役任务怎么出题（调研）
子 Agent 调研，2026-10-30，总控派。【已证】=有出处，【推测】=推断。

# RTS 战役"题目质量"调研（只读调研，没改项目任何文件，临时草稿只放在系统临时目录；2026-10-30）
- 说明：【已证】=有出处；【推测】=我的归纳；凡未另标【推测】的条目都是【已证】。[S#][L:页名][R#][O#][M#][Z#] 对应文末 URL，出处等级见文末表：原话=设计者本人说的；转述=记者/评论者的话；社区=玩家整理（Liquipedia 经其官方 API 取，CC BY-SA 3.0，可能有版本差异）；摘要=只看到搜索摘要、没抓到正文。
- 限制：没找到暴雪专讲"战役任务设计"的文字资料。Browder 的 GDC 2011 演讲有免费视频 [Z10]，日程摘要说会涉及 RTS 战役设计、多人与电竞，但所有文字转述都只记了电竞/多人内容；我看不了视频，战役部分未核对，建议人工看一遍。设计者原话主要来自 2009–2013 年的访谈、问答和 AMA；红警2/尤里、WC3、AoE、心灵终结几乎没有设计者谈任务设计的原话（第八节）。
## 一、先给结论
1. 【已证】SC2 的做法：每关是自带独有机制的"小游戏"（Browder 说一关 15–45 分钟），背后有几十个"套路"反复变奏；明确不想把 25–30 关做成类对战、或只控一两个单位的 RPG 式这两种俗套 [S8][S1][S15]。
2. 【已证】让平推/龟缩失效靠的不是多加兵，而是让威胁、目标、资源会动、会变、会倒计时：昼夜、岩浆、火墙、移动的火车、同抢目标的对手、随进度加码的攻势（第二节）。
3. 【已证·社区】难度分档改的远不止血量：首发进攻时间/间隔/数量/兵种、倒计时显不显示、失败容忍度、AI 先点杀谁、高难度专门堵"省力解法"（第三节）。
4. 【已证】巧解靠"本关新解锁的单位 + 界面提示 + 奖励目标/成就文案"来暗示，并且故意留多种解法（第四节）。
5. 【已证】流程：套路库 → 约 2 周出可玩版 → 3–4 个月打磨 → 常整关推翻重来（第七节）。
## 二、任务题型目录（每题：考/平推失效 → 暗示/分档 → 例；"考什么"是我按机制归纳的【推测】，其余若无另标均为【已证】）
- 1) 昼夜攻守（SC2《Outbreak》）｜考：抓时间窗口（白天约 3 分钟出击拆 144 座感染建筑，夜里约 5 分钟回防）、攻守分配、应对逐夜升级的突发｜平推失效：只龟缩清不完建筑，只冲锋夜里被围；Browder 2009 年就讲过这个构想（感染体白天躲地下、夜里要死守、白天才能攻），后来称它是自己最爱的一关，因为攻守平衡、两种状态压力都大 [S8][S5][L:Outbreak]
  - 暗示：本关给 Hellion/Reaper；Hard 成就要求夜里摧毁 15 座感染建筑，被 Game Informer 评为彻底改变这关的打法 [S10]｜分档：Hard 起敌人会躲 Reaper 炸弹；成就按 Normal(第 5 夜前通关)/Hard(夜战拆楼)分层 [L:Outbreak]
- 2) 逼你迁移的推进灾难（《Supernova》火墙、《The Devil's Playground》岩浆、HotS《Kaldir》冰风暴）｜考：地形与站位、贪经济还是保安全、永久建筑变成临时投资｜平推失效：灾害区会毁掉固定基地，守家等于送死；Browder 讲过一关每 5 分钟岩浆上涨、杀死地面一切，评测形容 Supernova 是一边躲火墙一边带着基地搬家 [S8][S10][L:Supernova]
  - 暗示：倒计时/副官语音预警；资源故意稀缺；Kaldir 冰风暴只提前几秒预警，但玩家拿到免疫后灾害反成了掐进攻时机的节拍器（Sigaty 的意思）[S11][S14]
  - 分档：Brutal 的岩浆关取消倒计时、只剩副官语音；低难度在第一次岩浆吞光 SCV 时替你补发 SCV（Browder）；Amon's Fall 地面塌陷倒计时 12/10/8 秒 [L:The_Devil's_Playground][S3][L:Amon's_Fall]｜例：Supernova 成就把"逃"和"打"分开考——Normal 不让单位被火烧到，Hard 用隐形 Banshee 杀 75 个 [L:Supernova]
- 3) 追击移动目标（《The Great Train Robbery》）｜考：先打谁（火车还是护卫）、兵种与机动（本关解锁的 Diamondback 能边走边打）、多线（追车+守家）、经济靠拾取箱和击杀而非采矿｜平推失效：目标按固定节奏经过，漏车超限就败；越打护卫越强，第 4 列后轨道旁冒出碉堡，第 6/7 列加速 [L:The_Great_Train_Robbery]
  - 暗示：开局就在小地图揭示前几辆 Diamondback 和奖励目标，5 分钟内全部显形｜分档：Brutal 漏 2 列就败，其余难度漏 3 列才败；Hard 在轨道旁放两座碉堡可行，Brutal 不行、只能量产 Diamondback；成就：Hard 一列都不漏、Normal 不造 SCV [L:The_Great_Train_Robbery]
- 4) 与对手抢目标（《Smash and Grab》Zerg 同抢神器；HotS《Kaldir》20 分钟硬计时、《Rendezvous》援军到达前拆 15 座建筑）｜考：和对手抢速度、分兵（出击 vs 守家）、先打主目标还是副目标｜平推失效：拖得越久越难；Browder 2009 的描述是两边同打一个 Protoss 基地、看谁先到 [S8]。但《Smash and Grab》留了后路：把 Zerg 基地全拆光就能解除时间压力 [L:Smash_and_Grab]
  - 暗示：Kaldir 主目标在小地图有标记、副目标没有，评测说真正的敌人是时钟 [S11]；Zerg 空降舱只有落在带肿瘤的菌毯上才出兵，所以杀肿瘤即可破解 [L:Smash_and_Grab]
  - 分档：高阶圣堂武士只在 Brutal 出现，Brutal 敌军优先点杀医疗兵；成就：Hard 要 15 分钟内通关、Normal 要不拆 Zerg 建筑只拿 4 个遗物 [L:Smash_and_Grab][L:Rendezvous]
- 5) 守点撑到撤离（《Zero Hour》、LotV《Last Stand》）｜考：防线、修复、经济与科技取舍｜平推失效：没有可推的主目标，目标就是活到时间；Zero Hour 高难度加空降舱（把菌毯和跳虫投到离基地越来越近处）和 Mutalisk，堵死"建筑升空逃命"的省力法 [L:Campaign][L:Zero_Hour]
  - 暗示/分档：Last Stand 成就按 18 亿(Normal)/22 亿(Hard)虫群到达分层，把"撑多久"变成可量化挑战 [L:Last_Stand]｜风险：玩家文章指出 WC3/AoE/SC2 的生存关本质就是龟缩题（作者观察，非设计者）[Z7]；GamesBeat 称 LotV 少有纯"造基地碾过去"的任务，靠把目标散在地图上逼你动（摘要）[Z1]
- 6) 多线资源逼迫（《Welcome to the Jungle》神殿永久封印气点；《The Devil's Playground》在会被岩浆淹的低洼采 8000 矿）｜考：多线分兵（开采+守家）、侦察、保护 SCV｜平推失效：采第一个气点就引来敌袭，被封的气点不再恢复；Game Informer 记者评语：这设置把人从缩在好守的基地里攒兵再碾压的传统单人 RTS 习惯里拽出来，同时管多条战线是必须 [S9]
  - 暗示：成就要求所有 SCV 存活、不让任何气点被封；评测者自己摸到一个没人守的后门 [S9]｜分档：未见专门说明；社区提示用 Vulture 偷袭 Probe 可打断封印 [L:Welcome_to_the_Jungle]
- 7) 攻势随进度加码（《The Dig》激光钻拆神庙门）｜考：何时推进、钻机火力打兵还是打门｜平推/龟缩失效：社区发现 Protoss 攻势强度与神庙门受损程度挂钩，门剩约 1000 HP 起不停进攻，Brutal 末段才出高阶圣堂武士；Game Informer 记者警告：允许自由架设静态防御的任务容易很无聊（这是要避免的风险）[L:The_Dig][S9]
  - 暗示：Normal 成就要用钻机杀 20 个敌人，10 周年新增的成就却要求不用钻机杀任何敌人通关，互相拉扯，等于把两种打法都写进文案 [L:The_Dig]
- 8) 单英雄/潜行/特种（SC2《Zeratul 闪回》《Whispers of Doom》；RA3 起义时刻尤里子战役；Tempest Rising 特种兵关）｜考：侦察与信息、技能时机、保护单位｜平推失效：没有建造、没有可堆的兵；SC2 专门加了显示敌方侦测范围的界面元素；评测指出 Zeratul 这关每个挑战都有离散的正确打法、会限制创造力，Game Wisdom 也警告谜题关易沦为猜设计者要什么 [S9][S16]
  - 尤里子：开发者目标是更像《暗黑 2》而非 RTS，故意只做 3 关免得玩腻，评测说短到只算消遣 [R5]｜Tempest Rising 主设计称特种兵关是最爱之一，并强调各关不要同一格式 [O5]｜分档：Whispers 的 Hard 成就要求 Zeratul 全程不掉血 [L:Whispers_of_Doom]
- 9) 定时开启的多目标/Boss（LotV《Amon's Fall》）｜考：先打谁、多线分兵、时间窗口、克制｜平推失效：10 个虚空水晶(Void Crystal)要毁 7 个，7 个虚空裂口(Void Chasm)按各自时间表激活，水晶只在短暂暴露时可打；世界劈裂(World Cleaver)按时间表轮流摧毁三方基地（首次 7 分 20 秒，之后每 4–6 分钟，小地图预警约 19.5 秒），路径上还有踩到就塌的陷阱，逼你多开基地、别依赖单一基地 [L:Amon's_Fall]
  - 分档（数据最全）：首发进攻 200/160/120 秒（Normal/Hard/Brutal），裂口被毁后休眠 600/420/285 秒，水晶 HP 4000/5000/6000；守军 Hard 约 +20–50%，Brutal 的高阶兵翻倍到近三倍（Stalker 3→8、Void Ray 2→5）；敌方 Hard 起 +1 升级、仅 Brutal 有科技升级；Casual=Normal，部分守卫建筑在 Casual/Normal 干脆不刷 [L:Amon's_Fall]
- 10) 取舍与分支（Hyperion 实验室永久二选一、WoL 三处二选一任务、HotS 进化任务）｜考：决策与后果，而非对错｜规则：选一个另一个锁死（攻速+5% 或生命+5%）[S9]；WoL 有三处二选一任务、剧情上只能走一条 [L:Campaign]；Sigaty 说科技选择都是二选一，所以想玩第二遍 [S7]；HotS 每个单位两条进化线，进化任务里先试用再选，评测批评它们像杂务拖慢叙事 [Z2]
  - Browder 承认这些选择主要是玩法选择、不是剧情分支 [S2]；WC3 的 Pardo 只做有限分支，希望一次通关就能看到大部分内容 [O9]；AoE4 威廉第二关可付丹麦金打发维京人或开战 [O4]；Stormgate 原型里英雄升级跨任务保留，逼你做取舍 [O7]
- 11) 新单位教学/展示关（几乎每关）｜考：兵种克制与新单位用法｜规则：几乎每关解锁一个新单位并配为它量身定做的任务，还藏教学和奖励目标 [S12]；每个战役前几关是种族小教学，之后才是一关一个噱头 [S17]；SC2 另有挑战模式专教克制 [S7]；AoE4 的 Art of War 教你应对 AI 施压的特定局面 [O3]
  - 反例：第三方评论称 HotS 约一半任务是 WoL 套路换皮（火车伏击换成运输机、采气换成采生物质），Kerrigan 太强使许多关赢法几乎一样 [Z3]；PCWorld 说关卡被引导得太死 [Z2]
- 12) 带约束的挑战地图（RA3 起义时刻"指挥官挑战"、SC2 成就、心灵终结 Challenge 图、Zero Hour 将军挑战）｜考：同一套单位在限制下换打法｜规则：RA3U 共 50 关（13 主线+37 支线），每关自带规则：垃圾雨、产出单位缩小、"Blood Feud"里两位指挥官互殴直到你攻击其中一个；起始只有基础单位，通关逐步解锁对手科技 [R1][R2]；多数限时、不可中途存档、有排行榜 [R3]；前几关后难度陡增，因为 AI 会用你尚未解锁的单位 [R4]
  - SC2：约一半任务有改变玩法的成就，其余是表现类（限时、不损失）[S10]；心灵终结 3.3.5 加 4 张 Challenge 图、总计 22 张（摘要）[M2][M4]；Generals 的将军挑战是 Zero Hour 里介于战役与遭遇战之间的模式，被 RA3U 借鉴 [R7]
- 13) 双人分工与护送/保护（RA3 原版联机战役；SC2 疏散/护送类）｜考：多线分兵、保护单位、协作｜规则：RA3 从一开始就围绕两个玩家设计任务（例：哈瓦那分两条战线），并限制每位指挥官能造的东西以迫使协作，评测说有时显得被迫（摘要）[Z6]；SC2 的护送关被评为相对简单，玩家反而有空去打 Zerg 基地 [S19]
- 14) 先打谁决定后面对谁 + 分阶段（《Media Blitz》）｜考：先打谁、阶段切换（先只控一个英雄限时突击，再转入建基地）、兵种克制｜规则：突击阶段只来得及毁三座敌基地（空军/机械/步兵）中的一两座；活下来的基地之后会来攻你，上传广播塔时还会被不在该基地里的另两类兵围攻，所以先毁哪个决定后面打谁；社区观察 Hard 敌军似乎不专点 SCV、Brutal 会 [L:Media_Blitz]
- 15) 中途冒出的突发目标（SC2 多个任务）｜考：应对突发、临场重分配兵力｜规则：ComputerBase 评测称支线常在任务进行中才弹出（例：防守时收到营救被困平民的呼叫），逼玩家临场取舍 [Z9]；Browder 2009 讲的殖民地一块块被感染、要边救火边打的守卫构想同属此类 [S8]
## 三、SC2 四档难度实际改了什么（汇总；设计者本人只讲过两点；数字主要来自 LotV 终局关 Amon's Fall 的社区数据，其余是各关攻略里的零散观察，不代表所有任务）
- Casual：敌人很少进攻、单位只有一半血（Liquipedia 总览页的说法，无官方数字）；LotV 里很多参数 Casual=Normal [L:Campaign][L:Amon's_Fall]
- Normal：基线；Normal 档成就常是"不损失/限定手段"类（据多页成就描述归纳）【推测】[L:Campaign]
- Hard：数量略增、首发进攻更早、敌方起始 +1 升级；AI 更聪明（躲 Reaper 炸弹、至少带一个观察者）；加新威胁（Zero Hour 空降舱）[L:Amon's_Fall][L:Outbreak][L:Maw_of_the_Void]
- Brutal：高阶兵翻倍以上、计时更短（首发 120 秒 vs 200 秒）；取消岩浆倒计时；失败容忍度更低（火车）；AI 点杀医疗兵/SCV、观察者被毁后持续补；只在 Brutal 出现的单位（高阶圣堂武士）与科技升级 [L:Smash_and_Grab][L:Maw_of_the_Void][L:Amon's_Fall]
- 设计者原话：难度由玩家自选，尽量引导但最终在玩家手里 [S1]；低难度有安全网（SCV 补发）[S3]。网上"Brutal 采集翻倍"之类说法没找到出处，不采信。
## 四、奖励目标/科研/成就怎么引导换打法；巧解怎么被暗示
- 研究点：开场就公布本关研究目标；高风险目标给研究点（飞去杀 Brutalisk 得 4 点），Browder 说这是给强玩家伸展自己的机会 [S1]；全战役 36 Zerg+39 Protoss 点、各 25 封顶，多的折成 credits [L:Campaign]；奖励目标常早早显形 [L:The_Great_Train_Robbery]
- 成就：多数任务三层——全部支线(任意难度)/Normal 以上/Hard 以上 [L:Campaign]；约一半是改变玩法类，例：Outbreak 夜战成就逼你从守变攻，Supernova 的成就要求不造兵营/工厂单位，逼你走空军 [S10][L:Supernova]
- 解锁顺序：你选的任务顺序决定手里有什么单位；很多任务被迫防守，所以坦克特别值钱 [L:Campaign]
- 多解：评测称多数任务有任意多种兵种/战术解法 [S10]；社区找到的省力解（Supernova 核弹/Banshee/MULE 抢遗物，Train Robbery 坦克守轨道）说明解空间是故意留宽的【推测】[L:Supernova][L:The_Great_Train_Robbery]
- 暗示手段汇总【推测，据上文归纳】：(a)本关新单位+量身任务 (b)界面元素直接显示规则（侦测范围）(c)奖励目标早显形、成就文案点题 (d)规则可观察（空降舱只在带肿瘤菌毯上出兵）(e)主目标有标记、副目标要探索
## 五、设计者怎么避免"平推/龟缩成为最优"（具体做法）
1. 不做遭遇战式任务：Browder 说 "If you wanted a Skirmish level, you'd just go play Skirmish." [S1]；同时不要求玩家重学界面、不突然变成 FPS [S1]。
2. 每关独有机制+套路库；种族通用的机制优先用，种族专属的留给后面战役 [S2]。
3. 威胁/目标会动：昼夜、每 5 分钟岩浆、火墙、冰风暴 [S8][S10]；硬计时（Kaldir 20 分钟）[S11]。
4. 把灾害变工具而非纯惩罚：冰风暴获得免疫后成了进攻节拍器 [S14]。
5. 攻势挂钩玩家进度（The Dig）、对手同抢目标（Smash and Grab）[L]；多目标逼你分兵（Welcome to the Jungle 记者评语）[S9]。
6. 高难度补堵省力解：Zero Hour 加 Mutalisk、Maw of the Void 加观察者（社区）[L]。
7. 结构性：World in Conflict 用固定增援池、重在夺取而非防守，白送一个小队不划算（Game Developer 专栏）[O8]；CoH3 减少脚本、更依赖 AI，大小任务交替 [O2]。
8. 并不一刀切禁守：Browder 最爱的 Outbreak 就是攻守交替 [S5]；设计风险是静态防御太好用会让任务无聊 [S9]。
9. 心灵终结：PC Gamer 评语：很多任务开局只有一小撮兵、容错极低，但可一开始就选任意关跳过难点（摘要）[M3]；3.3.6 称 AI 大幅增强且多档难度 [M2]。
## 六、同时照顾大众与硬核的做法
1. 难度自选（尽量引导，最终在玩家手里）[S1]；成就三层把硬核需求放进可选项 [L:Campaign]；可选目标是强玩家自己加难度的出口 [S1]。
2. 多数任务压力会把你推出舒适区 [S10]；少数任务让你尽情玩自己的玩具、碾压敌人，但常带个转折 [S4]。
3. 低难度安全网：SCV 补发 [S3]；Casual 敌人很少进攻 [L:Campaign]；HotS 里 Kerrigan 阵亡不判负，会在最近孵化场复活 [S13]。
4. 失败要看得懂：Browder 说做了大量调校打磨，让玩家失败时明白为什么（转述，未取到整句）[S3]。
5. 战役与多人脱钩：战役可放飞，用各种单位和升级 [S6]；战役专属升级强到不会放进多人 [S8]；战役的任务是教操作与基础克制，不负责教高端对战 [S18]；Tempest Rising 战役单位数值独立，为稳住战役难度 [O6]。
6. 兜底保证：CoH3 任务无论选哪个阵营/连队/单位都能通关，但仍有挑战 [O1][O2]。
7. 教学内嵌：AoE4 分析式教程+Art of War [O3]；SC2 早期种族小教学+隐藏教学 [S12][S17]。
8. 难度上线即定：SC2 尽量不给战役打平衡补丁 [S5]；RA3 起义时刻把磨技术的需求拆成独立"指挥官挑战"模式（制作人称它是磨技术的好方式）[R2]。
## 七、任务设计工作流程（设计者说法）
1. 套路库：Blizzard 有几十个套路可变奏（访谈提到约 10 名设计师）[S1]。
2. 速度：可玩版有时只要 2 周；Blizzard 水准的打磨通常 3–4 个月；第一次从没成功过；经常整关推翻 [S1]。
3. 反复推翻：有一关核心机制改了 7–8 次；有 5–6 关只剩文件名没变；佣兵任务因为不管怎么选玩起来每次都一样被简化、复杂度加到别处——这是公开的试玩判据 [S2]。
4. 设计会：连开几天后有同事说 RTS 任务点子用完了，新单位和故事又催生新点子；能给任何种族用的机制当场就用 [S2]。
5. 方向会变：战役一度更像 RPG，后来收敛成正经的 RTS 加强成长线 [S18]。
6. 先机制还是先故事：C&C3 的 Sam Bass 说双线并行（故事+任务清单）再合并，好关卡约 1 份脚本配 3 份 AI 动态遭遇 [R6]；Kindregan 称写作与设计必须是一个团队（摘要）[Z4]；SC2 设计师称故事与任务间来回修改（摘要）[Z5]。
7. 打磨判据：玩家输了知道原因 [S3]；难点是做出能逼出指挥水平的仗，机制要与故事绑定 [S4]。灰盒测试：没找到设计者明确说法；2 周可玩版约等于灰盒【推测】。
8. 上线后：Stormgate 把战役当起跑线，上线后继续改目标和脚本事件 [O7]。
## 八、没找到/抓不到
- 抓不到正文：GameSpot E3 2015 暴雪四人访谈、Co-Optimus 对 Kasavin 的 RA3 访谈、PC Gamer（心灵终结两篇、CoH3 复盘）、ppmforums/ModDB 心灵终结公告、Hive Workshop 的 WC3 设计师访谈与 Blizzard 设计文档、TL.net 任务讨论；Liquipedia/Fandom 网页端被拦，改走 Liquipedia API（早期 4 次 parse 请求间隔仅约 3 秒，短于其建议的 30 秒，之后改用批量 query）。
- 没找到：设计者谈 RA2/尤里战役的原话（只知 Browder 当年是 RA2 主设计，尤里发行时 Westwood PR 称新单位用来反坦克海 [Z8]）；RA3 原版战役设计者谈难度；Revora/ppmforums 上心灵终结设计者谈任务设计的帖子（mentalomega.com 仅说第三幕由社区资深任务设计者制作 [M1]）；Northgard、C&C 重制版、CoH1/CoH2、Halo Wars 2、AoE2 决定版（只见战役修订时尽量少改的说法 [Z11]，非设计原则）也没找到设计者谈任务设计的原话。
## 九、给本项目的借用【推测】
1. 每关一句话机制+一个会动的威胁，别用"打光为止"。
2. 难度三层：Casual≈Normal 数值，Hard/Brutal 改首发时间/计时/容忍度/点杀/堵省力解。
3. 把成就和可选目标写成提示，并留 2 种以上解法和 1 个要观察规则才发现的捷径。
4. 流程：2 周出灰盒，用"是否每次玩起来都一样"当判据。
5. 起义时刻的指挥官挑战思路可做成"同图换约束"的重玩层。
## 十、下一步（推荐 ①）
1. 【推荐】请你（我看不了视频）看一遍 Browder 的 GDC 2011 视频 [Z10]，把战役设计相关段落记下来或转写后交给我补进本目录（目前唯一可能的"设计者讲战役"一手来源）。
2. 把本目录落成"每关一页"的任务模板（机制一句话 / 平推失效规则 / 暗示手段 / 三档难度 / 内部试玩判据），再套到 27 关总表上查缺题型。
3. 用 RA3 原版战役的目标分布（项目里的 retail_goals）对照这 15 型，先看原版缺哪几型，再决定补哪些。
## 来源（括号=出处等级；未标=转述/评测）
- S1(原话) https://gameinformer.com/games/starcraft_ii_wings_of_liberty/b/pc/archive/2009/10/30/feature-lead-designer-dustin-browder-on-story-and-map-design-in-starcraft-ii
- S2(原话) https://gameinformer.com/b/features/archive/2010/09/19/afterwords-starcraft-ii ｜ S3(原话) https://www.engadget.com/2010-05-02-blizzards-dustin-browder-talks-starcraft-2.html
- S4(原话) https://www.blizzplanet.com/blog/comments/blizzchat_developer_chat_on_twitter_4_30_transcript ｜ S5(原话) https://news.blizzard.com/en-us/article/8983614/reddit-ama-full-transcript
- S6(原话) https://www.gamedeveloper.com/business/the-design-of-i-starcraft-ii-i- ｜ S7(原话) https://www.shacknews.com/article/63450/starcraft-2-interview-lead-producer ｜ S8(原话) https://www.shacknews.com/onearticle.x/59317
- S9 https://gameinformer.com/games/starcraft_ii_wings_of_liberty/b/pc/archive/2010/04/23/preview-hands-on-with-three-new-starcraft-ii-missions
- S10 https://gameinformer.com/b/news/archive/2010/07/29/starcraft-ii-campaign-reactions.aspx ｜ S11 https://gameinformer.com/games/starcraft_ii_heart_of_the_swarm/b/pc/archive/2011/06/01/heart-of-the-swarm-preview-mission-walkthroughs
- S12 https://www.pcgamesn.com/starcraft-2/campaign-revisit-2026 ｜ S13(原话) https://news.blizzard.com/en-gb/article/9983609/blizzard-insider-interview-mit-dustin-browder ｜ S14(原话) https://www.engadget.com/2011-05-31-starcraft-2-heart-of-the-swarm-preview-kerrigan-again.html
- S15(二手转述，原始出处未具名) https://news.17173.com/content/2009-01-05/20090105090704305.shtml ｜ S16 https://game-wisdom.com/critical/one-man-war-examining-single-player-rts-design ｜ S17 https://waywardstrategy.com/2018/06/22/campaign-design-world/
- S18(原话) https://gameinformer.com/b/features/archive/2010/04/08/an-extensive-interview-with-starcraft-ii-design-director ｜ S19 https://shacknews.com/onearticle.x/60009
- L(社区) https://liquipedia.net/starcraft2/Campaign 及 https://liquipedia.net/starcraft2/Campaign/{页名}：Outbreak、The_Great_Train_Robbery、Supernova、Smash_and_Grab、The_Devil's_Playground、Zero_Hour、The_Dig、Welcome_to_the_Jungle、Whispers_of_Doom、Maw_of_the_Void、Media_Blitz、Rendezvous、Amon's_Fall、Last_Stand
- R1(社区) https://en.wikipedia.org/wiki/Command_%26_Conquer:_Red_Alert_3_%E2%80%93_Uprising ｜ R2(原话) https://www.shacknews.com/article/56657/command-conquer-red-alert-3 ｜ R3 https://www.gamerevolution.com/?p=44700 ｜ R4 https://futurefive.co.nz/story/review-red-alert-3-commanders-challenge
- R5(转述开发者) https://www.bit-tech.net/previews/gaming/pc/c-c-red-alert-3-uprising-preview/3/ ｜ R6(原话) https://forums.cncnz.com/topic/9901-tacitus-thursday-interview-with-sam-bass/ ｜ R7(社区) https://en.wikipedia.org/wiki/Command_%26_Conquer:_Generals_%E2%80%93_Zero_Hour
- O1 https://gamedeveloper.com/press-release/company-of-heroes-3-campaign-missions ｜ O2 https://www.computerbase.de/2022-02/company-of-heroes-3-missionen-muessen-flexibel-sein/ ｜ O3 https://www.kitguru.net/?p=438898 ｜ O4 https://www.gamedeveloper.com/design/writing-history-for-winners-and-losers-in-age-of-empires-IV
- O5(原话) https://www.gameshedge.com/interview-splitgate-ironworks/ ｜ O6 https://support.saber.games/hc/en/tempest-rising/articles/tempest-rising-faq-1 ｜ O7(原话) https://devtrackers.gg/stormgate/p/59071553-stormgate-developer-update-the-road-ahead-for-campaign ｜ O8 https://www.gamedeveloper.com/design/design-lesson-101---em-world-in-conflict-em- ｜ O9(原话) http://www.gamebanshee.com/kcp3
- M1 https://www.mentalomega.com/ ｜ M2 https://www.gamepressure.com/newsroom/cc-red-alert-2-mental-omega-336-released/z63c00 ｜ M3(摘要) https://www.pcgamer.com/uk/let-red-alert-2-mod-mental-omega-expand-your-mind ｜ M4(摘要) https://ppmforums.com/post-597003/mental-omega-335-is-out-now/
- Z1(摘要) https://gamesbeat.com/?p=112467 ｜ Z2 https://www.pcworld.com/article/457196/review-heart-of-the-swarm-a-big-step-in-starcraft-iis-evolution.html ｜ Z3 https://scientificgamer.com/thoughts-heart-of-the-swarm/ ｜ Z4(摘要) https://www.gamedeveloper.com/game-platforms/pc?page=128
- Z5(摘要) https://www.gamespot.com/articles/blizzards-secrets-of-storytelling-in-starcraft-2-l/1100-6428469 ｜ Z6(摘要) https://www.co-optimus.com/interview/101/red-alert-3-interview-greg-kasavin-on-influences-and-design-of-a-co-op-rts.html 与 https://www.co-optimus.com/review/124/page/2/red-alert-3-co-op-review.html
- Z7 https://gamesbeat.com/why-turtling-is-awesome/ ｜ Z8 https://gamespy-archives.quaddicted.com/sites/www.strategyplanet.com/features/previews/yurisrevenge/index.html ｜ Z9 https://www.computerbase.de/artikel/gaming/starcraft-2-wings-of-liberty-test.1282/seite-3
- Z10 GDC 2011 Browder 视频（官方 GDC YouTube，内容未核对）https://www.youtube.com/watch?v=VIv5UgCbDho ｜ GDC Vault 页（无摘要无文字稿）http://www.gdcvault.com/play/1014488/The-Game-Design-of-STARCRAFT ｜ 日程摘要提到战役设计（摘要）https://warcraft.blizzplanet.com/?p=9747 ｜ Z11 https://www.ageofempires.com/news/meet-team-cedric-van-de-sande-campaign-lead/
