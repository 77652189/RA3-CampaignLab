# 现代 RTS 引擎与技术方案调研

调研日期 2026-11-05。方法：WebSearch / WebFetch。

标记约定：
- **[出]**：有出处，链接在同一行。
- **[推]**：我的推断，没有直接出处。
- **未查到**：搜了没有可靠结果，没有编。

诚实说明：搜索工具返回的大多是二手报道、论坛帖和百科镜像，官方技术文档很少。下面凡是"二手"的都标出来了。GDC 演讲的视频和幻灯片没有读到，只读到了演讲预告页。

---

## 1. 近十年 RTS 用什么引擎

"RTS 核心"指确定性联机、寻路、大量单位这一套。

| 游戏 | 渲染 / 主引擎 | RTS 核心 | 证据等级 | 出处 |
| --- | --- | --- | --- | --- |
| Stormgate（2025） | 虚幻 5 | 自研 SnowPlay（模拟层，独立于虚幻）；确定性 lockstep，可选回滚 | [出] 官方工程师回复 + 宣传，非技术文档 | [演讲预告](https://forums.unrealengine.com/t/1835255) / [工程师回复](https://devtrackers.gg/stormgate/p/13d80016-frost-giant-s-snowplay-gif-in-the-kickstarter-is-deceptively-misleading) |
| Iron Harvest 钢铁收割（2020） | Unity | 自研，官方开发日志写"确定性 lockstep" | [出] 2018 年日志；发售版是否仍如此未查到 | [DevBlog #6](https://kingart-games.com/article/49) / [Steam 技术栏](https://steamdb.info/app/826630) |
| Tempest Rising 风暴崛起（2025） | 虚幻（先 UE4，制作中移植到 UE5，PCGH 称 5.4.3.1） | 联机模型（lockstep 还是服务器）未查到 | [出] 仅引擎部分 | [PCGH](https://www.pcgameshardware.de/Tempest-Rising-Spiel-73832/Specials/Test-Release-Steam-Review-Command-and-Conuer-1470023/) / [Wikipedia](https://en.wikipedia.org/wiki/Tempest_Rising) |
| Total War 系列 | Warscape（自研） | 自研；Total War 负责人称 Warscape 已"untenable"，下一代 Warcore 用于 Medieval 3 | [出] 仅标题和摘要；正文 503 未读到 | [GamesRadar](https://www.gamesradar.com/games/total-war/total-wars-new-warcore-engine-will-power-total-war-medieval-3-bring-the-strategy-series-to-console-and-restore-modding-we-want-to-put-these-tools-in-the-hands-of-players) |
| Age of Empires IV（2021） | Relic Essence Engine（5.0） | 自研 | [出] 二手，无 Relic 官方声明 | [GameScrobbler](https://gamescrobbler.com/nl/games/age-of-empires-iv) / [ModDB](https://www.moddb.com/engines/essence-engine) |
| Company of Heroes 3（2023） | Essence Engine 5 | 自研 | [出] 二手（TrendHunter 转述 Steam / Wired） | [TrendHunter](https://www.trendhunter.com/trends/company-of-heroes-3) |
| Beyond All Reason | Recoil（Spring 的分支） | 开源引擎自带，lockstep | [出] 官方文档 | [netcode 文档](https://beyond-all-reason.github.io/spring/articles/netcode-overview) / [RecoilEngine 仓库](https://github.com/beyond-all-reason/RecoilEngine) |
| They Are Billions | 自研（C#/.NET，物理库 C++） | 自研；开发者称能动 2 万单位 | [出] 开发者自述，未独立验证；搜索结果里没有 Unity 的说法 | [Dev Tracker](https://v2.devtrackers.gg/theyarebillions/p/e49ddd3d-game-engine-for-20k-units)（页面本次 503，内容来自搜索摘要） / [PC Gamer](https://www.pcgamer.com/au/lords-of-xulima-dev-reveals-steampunk-strategy-game-they-are-billions) |
| Northgard | Heaps（Haxe，MIT） | Shiro 自研 | [出] | [Shiro 技术栈](https://haxe.org/blog/shirogames-stack/) |
| Dune: Spice Wars | 来源互相矛盾：媒体说 Shiro 自研引擎，数据库列 Heaps，一条 Steam 评论说 Unity | 未查到定论 | 矛盾，不采信任何一个 | [Inverse](https://nc.inverse.com/gaming/dune-spice-wars-release-date-trailer-genre-early-access-details) / [Heaps 用户列表](https://enginesdatabase.com/engine/heaps) |
| Diplomacy is Not an Option | Unity，用 DOTS（寻路和玩法优化） | 单机，无联机问题 | [出] 来自 Unity 的宣传页，是厂商说法 | [Unity DOTS 页](https://unity.com/dots) |
| Sins of a Solar Empire II（2022） | Iron Engine 3（自研 64 位多核） | 自研 | [出] 官方公告 | [Stardock 公告](https://forums.sinsofasolarempire2.com/514203) |
| Homeworld 3（2024） | 虚幻 4（不是 5） | 联机模型未查到 | [出] TechPowerUp、Dexerto | [TechPowerUp](https://techPowerUp.com/review/homeworld-3-benchmark/) |
| Manor Lords（2024） | 虚幻（先 UE4，后迁 UE5）；基本一人开发 | 单机，中世纪模拟，不走 lockstep | [出] | [GamesRadar](https://gamesradar.com/games/city-builder/manor-lords-is-still-moving-forward-even-as-the-city-builders-creator-takes-a-well-deserved-minibreak-amid-its-unreal-engine-5-move) / [Epic 访谈](https://www.unrealengine.com/developer-interviews/solo-dev-makes-sophisticated-sim-manor-lords-using-unreal-engine)（访谈页本次 403，只读到标题） |
| D.O.R.F. | 魔改 OpenRA | OpenRA 的 lockstep 骨架，移动、攻击逻辑已重写 | [出] 媒体 + Patreon | [PCGH](https://www.pcgameshardware.de/Indie-Games-Thema-239276/News/DORF-Kickstarter-1522632/) / [Patreon](https://www.patreon.com/dorfRTS/about) |
| ZeroSpace | 虚幻 4（仅一个低权重目录站说法） | 未查到 | 弱 | [目录站](https://lan-gaming.codeberg.page/games/zerospace) |
| Battle Aces（腾讯 Uncapped） | 未查到引擎；搜索显示项目似已取消（Gematsu 页面带 "canceled" 标题，未证实） | 未查到 | 未查到 | [Gematsu](https://gematsu.com/games/battle-aces) |
| Planetary Annihilation | 自研 | 客户端-服务器，不用 lockstep；服务器 10 Hz，客户端用曲线数据平滑到 60 | [出] 开发者访谈、Forrest Smith 博客 | [ChronoCam](https://www.forrestthewoods.com/blog/tech_of_planetary_annihilation_chrono_cam/) / [PC Gamer](https://www.pcgamer.com/planetary-annihilation-interview/2) |
| Supreme Commander / Demigod（较老，作对照） | 自研（Demigod 改自 SupCom 引擎） | lockstep，浮点 | [出] | [Forrest Smith](https://www.gamedeveloper.com/design/opinion-synchronous-rts-engines-and-a-tale-of-desyncs) |
| BOID（独立，1400 单位，跨平台） | C# 自研 | 定点数 lockstep | [出] | [Game Developer](https://gamedeveloper.com/programming/cross-platform-rts-synchronization-and-floating-point-indeterminism) |
| Age of Empires 1/2（对照，经典文献） | 自研 | lockstep，指令延迟约 200 ms | [出] | [1500 Archers on a 28.8](https://www.gamedeveloper.com/programming/1500-archers-on-a-28-8-network-programming-in-age-of-empires-and-beyond) |

共 20 余款。没查到的：Tempest Rising 的联机模型、Homeworld 3 / ZeroSpace / Battle Aces 的联机模型和寻路、AoE IV 和 CoH3 的官方引擎声明、Total War 联机与寻路。

### 从上表能看出的格局

- **大作基本都自研 RTS 核心**：SnowPlay、Essence、Warscape、Iron Engine、Recoil。这是观察，没有哪份材料明说"为什么"。[推] 原因多半是商业引擎没有现成的确定性模拟，和"几百上千单位"的需求不匹配。
- **用现成引擎的，渲染归引擎，模拟归自己**：Stormgate（虚幻 5 + SnowPlay）、Iron Harvest（Unity + 自研 lockstep）。这是和我们最相关的一条路线。
- **单机 / 弱联机的城建 RTS 最自由**：Manor Lords、They Are Billions、Northgard、Diplomacy is Not an Option。不用确定性，引擎随便选。
- **独立怀旧 RTS 常借开源引擎**：D.O.R.F. 用 OpenRA。
- **现成商用确定性方案几乎没在大作里出现**：在已查到的 RTS 里没找到用 Photon Quantum 的（Quantum 官方客户页列的是 Stumble Guys 等，不是 RTS）。这是"没找到"，不是"没有"。

---

## 2. 现成的 RTS 专用技术方案

### 2.1 确定性联机

| 方案 | 是什么 | 许可 / 价格 | 成熟度与用户 | 出处 |
| --- | --- | --- | --- | --- |
| Photon Quantum | 商用确定性 ECS 框架，输入同步，预测加回滚；定点数 FP（Q48.16），三角函数和开方用查表；浮点转 FP 的接口被标为不确定、不安全 | 开发期免费，量产按并发用户付费，具体价格页没读到，**未查到价格和是否给源码** | 官方客户页列 Stumble Guys 等，没有 RTS 案例 | [官网](https://www.photonengine.com/quantum) / [定点数文档](https://doc.photonengine.com/quantum/v3/manual/quantum-ecs/fixed-point)（该页标注未升级到 Quantum 3） / [FP API](https://doc-api.photonengine.com/en/quantum/current/struct_photon_1_1_deterministic_1_1_f_p.html) |
| Unity 自带（DOTS / Netcode for Entities） | Unity 没有 lockstep；Unity 6 的多人中心里 lockstep 选项写"Unity 不提供" | Unity 许可 | Unity 员工称 DOTS 物理在相同输入、相同设备上确定，但浮点跨机器不保证 | [Unity 论坛：Netcode for RTS](https://discussions.unity.com/t/netcode-for-rts/943819) / [Unity 论坛：Deterministic Networking](https://discussions.unity.com/t/deterministic-networking/654605) |
| Godot 上的 Klotho | Godot 4.4+（.NET）的确定性插件：32.32 定点数、带种子随机数，支持 P2P lockstep、回滚、旁观、重连；自述适合 RTS | 许可未查到 | 很新；版本号在素材库里不一致（0.2.10 和 0.10.0），**没有 RTS 级别的规模案例** | [Godot 素材库](https://godotengine.org/asset-library/asset/5234) / [商店页](https://store.godotengine.org/asset/xpturn/xpturn-klotho/) |
| 自写 lockstep + 定点数 | BOID、AoE 的做法；SnowPlay、Iron Harvest 是同类自研 | 无 | 最常见 | [BOID](https://gamedeveloper.com/programming/cross-platform-rts-synchronization-and-floating-point-indeterminism) / [AoE](https://www.gamedeveloper.com/programming/1500-archers-on-a-28-8-network-programming-in-age-of-empires-and-beyond) |
| 客户端-服务器（不确定性） | Planetary Annihilation：服务器模拟，客户端收曲线 | 无 | 单一案例 | [ChronoCam](https://www.forrestthewoods.com/blog/tech_of_planetary_annihilation_chrono_cam/) |

### 2.2 寻路与群体移动

| 方案 | 要点 | 许可 | 出处 |
| --- | --- | --- | --- |
| 流场（flow field） | 一个目的地算一张向量场，整个编队共用；Supreme Commander 2 用过，Emerson 在 Game AI Pro 写过唯一的公开章节；SC2 和 Planetary Annihilation 把地图切块控制内存 | 技术方案，无许可 | [howtorts 博客](https://howtorts.github.io/2014/01/04/basic-flow-fields.html) / [Continuum Crowds 笔记](https://howtorts.github.io/2014/01/09/continuum-crowds.html) / [Game AI Pro 360 目录](https://www.routledge.com/products/9780367151133) |
| RVO2 / ORCA | 避让算法，原版 C++ 现为 Apache-2.0（有一处镜像元数据写 CC-BY-SA-4.0，用前自己核实 LICENSE）；某 Java 移植版限非商用；A* Pathfinding Project 作者当年联系不上原作者，选择自己重写 | Apache-2.0（以仓库 LICENSE 为准） | [RVO2 仓库](https://github.com/snape/RVO2) / [A* 作者的帖子](https://forum.arongranberg.com/t/rvo2-licensing/341) |
| Recast & Detour | 导航网格中间件，C++98 无依赖，Unity、Unreal、Godot、O3DE 的导航底层 | zlib | [仓库](https://github.com/recastnavigation/recastnavigation) |
| 虚幻 Mass Entity | 虚幻自带的 ECS；2025 年一篇硕士论文测到 5 万单位 60 帧；官方不支持 "Mass + 状态树 + 网络复制"；**没有任何资料说它是确定性 lockstep** | 虚幻许可 | [论文](https://pure.fh-ooe.at/en/studentTheses/rendering-and-ai-optimization-in-rts-games-enhancing-performance-/) / [AtollRTS 帖](https://forums.unrealengine.com/t/randream-atoll-rts-tool/2744507) |
| Unity DOTS | Diplomacy is Not an Option 用于寻路和性能 | Unity 许可 | [Unity DOTS 页](https://unity.com/dots) |

商业寻路中间件（如 Havok AI 等）：**未查到**，本次没有搜这一项。

### 2.3 开源 RTS 引擎

| 引擎 | 语言 | 许可 | 联机 | 成熟度 / 用户 | 出处 |
| --- | --- | --- | --- | --- | --- |
| Recoil（Spring 分支） | C++，需要 x86-64 | 仓库含 GPL-2.0 与 GPL-3.0 文本，哪部分适用哪个没读清；**用前核实** | lockstep，官方文档承认硬件差异要特殊处理，所以不支持非 x86-64（2026 年 7 月更新说加了 ARM64，细节未查到） | 版本 105.0；Beyond All Reason、ZeroK、TA Prime、Metal Factions 在用；仓库 733 星 | [仓库](https://github.com/beyond-all-reason/RecoilEngine) / [netcode 文档](https://beyond-all-reason.github.io/spring/articles/netcode-overview) / [GamingOnLinux](https://www.gamingonlinux.com/2026/07/impressive-grand-scale-rts-game-beyond-all-reason-gets-a-major-engine-upgrade-with-arm64-support/) |
| OpenRA | C#，SDL + OpenGL | GPL-3.0；mod 里加载的可执行代码也要兼容开源 | 仓库页没写联机模型，社区常见说法是 lockstep，**这里未直接查到** | 17.7k 星，3 万提交，活跃；Red Alert、Tiberian Dawn、Dune 2000 复刻；D.O.R.F. 魔改 | [仓库](https://github.com/OpenRA/OpenRA) / [GPL 说明](https://libregamewiki.org/OpenRA) |
| 0 A.D. Pyrogenesis | C++，脚本用 SpiderMonkey | 引擎 GPL-2.0 或更新；二进制 GPL-3.0；美术、音频 CC BY-SA 3.0 | 确定性模拟：**未查到** | 长期项目 | [Wikipedia](https://en.wikipedia.org/wiki/0_A.D._(video_game)) / [LICENSE](https://www.github.com/0ad/0ad/blob/master/LICENSE.txt) |
| OpenSAGE | C#，.NET | 官网写 LGPLv3；GitHub 页识别为"未知"，另有 LICENSE-EA.md，**用前自己读文件** | 无 | 官方自述"远未可玩"，还没做完 | [官网](https://opensage.github.io) / [仓库](https://github.com/OpenSAGE/OpenSAGE/) |
| 《将军·绝命时刻》源码 | C++ | GPL-3.0（EA 开源，我们已读） | lockstep（自带） | 完整可编译的商业 RTS，我们已有 | 仓库内 `refs/CnC_Generals_Zero_Hour` |
| Godot 上的 RTS 框架 | C# | 见 Klotho | 见 2.1 | 没找到整套的 RTS 框架，只有零件 | 见 2.1 |

**许可的现实**：Recoil、OpenRA、0 A.D.、Generals 源码全是 GPL。基于它们做的商业游戏必须开源整套代码。Heaps 是 MIT（[Shiro 技术栈](https://haxe.org/blog/shirogames-stack/)），Recast 是 zlib，RVO2 是 Apache-2.0，这三个商用没有传染问题。

---

## 3. 公开的经验和坑

每条写：谁、什么问题、怎么解决、出处。

### 3.1 确定性和浮点

| 谁 | 问题 | 解决 | 出处 |
| --- | --- | --- | --- |
| Forrest Smith（Gas Powered Games，Demigod） | 引擎每秒对整个游戏状态做哈希，不同步就报"检测到不同步"；浮点差异是大头；最常见根因是**未初始化变量**；一个具体案例：英雄技能把小兵击飞，小兵的转向寻路组件被删，但指针没置空，内存分配器把那块放回空闲链表，如果落地前被重用，就会偏几厘米，约 5% 的 60 分钟以上对局出现 | CPU 设成严格 IEEE 754（有性能损失）；禁止未定义结果的运算；二分法打印状态哈希定位；指针删除后置 NULL | [Game Developer](https://www.gamedeveloper.com/design/opinion-synchronous-rts-engines-and-a-tale-of-desyncs) |
| Maksym Hryniv（BOID，C# RTS，约 1400 单位，PC/Mac/iOS/Android 互联） | 不同处理器（Intel/AMD/ARM/主机）浮点结果略有差别，单位路径和伤害分叉，校验和报错；C# 没有编译器开关可救 | 全改成 64 位整数定点数（12 位小数），运算符重载；三角函数查表，开方用循环；**第三方的物理、寻路、四叉树都得改成定点**；之后只剩自己代码里的 bug | [Game Developer](https://gamedeveloper.com/programming/cross-platform-rts-synchronization-and-floating-point-indeterminism) |
| Recoil / Spring 开发者 | 浮点要在所有客户端一致；差一点会像蝴蝶效应，晚些表现为资源数不同；老讨论里一个根因是 FPU 精度控制被设成双精度 | 官方文档称"极度小心"保持计算一致；2023 年论坛说 BAR 优先用 SSE 不用 x87，并定期检查 FPU 设置、不对时报警；放弃非 x86-64 | [netcode 文档](https://beyond-all-reason.github.io/spring/articles/netcode-overview) / [论坛 SYNC ERRORS](https://springrts.com/phpbb/viewtopic.php?p=182239)（流言级，当前 streflop 状态未查到） |
| KING Art（Iron Harvest） | 2018 日志：程序员 Alexander 研究 IEEE 浮点标准，目标是让模拟在不同硬件和系统上一致；日志**没有写具体问题** | 未写 | [DevBlog #6](https://kingart-games.com/article/49) |
| 论坛经验（二手，多来源） | 常见不同步源：无序容器、依赖帧率的逻辑、未初始化内存、跨 CPU 浮点；对策：每 tick 的状态 CRC、定点数、有序容器 | 同左 | [GameDev.net](https://www.gamedev.net/forums/topic/627667-lockstep-and-pathfinding/4960850/) / [Photon 的 FP 文档](https://doc-api.photonengine.com/en/quantum/current/struct_photon_1_1_deterministic_1_1_f_p.html)（官方也说浮点转定点是不安全接口） |

### 3.2 联机模型选择

| 谁 | 问题 / 取舍 | 做法 | 出处 |
| --- | --- | --- | --- |
| Age of Empires（Terrano / Bettner 一说，作者署名各处不一致） | 28.8k 调制解调器上跑 1500 单位 | 只传指令不传状态；指令延迟约 200 ms，所有人同一回合执行同一批命令 | [Game Developer](https://www.gamedeveloper.com/programming/1500-archers-on-a-28-8-network-programming-in-age-of-empires-and-beyond) |
| Frost Giant（Stormgate） | 纯 lockstep 的延迟手感差 | SnowPlay 把"时间"也当输入；回滚模式下客户端先预测前进，晚到的输入触发重载状态重放；他们的演示图用 clumsy 模拟丢包 | [工程师回复](https://devtrackers.gg/stormgate/p/13d80016-frost-giant-s-snowplay-gif-in-the-kickstarter-is-deceptively-misleading) |
| Planetary Annihilation（Uber） | 想让大战随服务器硬件增长，lockstep 只能跑到最慢玩家的速度 | 服务器模拟、客户端用曲线数据平滑；模拟 10 Hz | [ChronoCam](https://www.forrestthewoods.com/blog/tech_of_planetary_annihilation_chrono_cam/) |
| 社区评论（多人，非官方） | Supreme Commander 是少数在模拟里用浮点的 RTS，头疼不少 | — | 同上讨论线程（原帖： [GameDev.net](https://gamedev.net/forums/topic/663587-planetary-annihilation-networking/)） |

### 3.3 引擎选择与迁移的坑

| 谁 | 问题 | 做法 / 结果 | 出处 |
| --- | --- | --- | --- |
| KING Art | Unity 2018.3 还在 beta，"一些很重要的功能还不能用"，计划 Alpha 2 前换新版，而且回退到旧版也很难 | 在版本间被夹住的典型 | [DevBlog #6](https://kingart-games.com/article/49) |
| Slipgate（Tempest Rising） | 开发中从 UE4 迁到 UE5 | 迁移已完成并发售，细节未查到 | [PCGH](https://www.pcgameshardware.de/Tempest-Rising-Spiel-73832/Specials/Test-Release-Steam-Review-Command-and-Conuer-1470023/) |
| Slavic Magic（Manor Lords） | UE4 迁 UE5；发售前加人处理平台版本问题 | 迁移完成于 0.7.987 版（Wikipedia 镜像，未对官方核实） | [GamesRadar](https://gamesradar.com/games/city-builder/manor-lords-is-still-moving-forward-even-as-the-city-builders-creator-takes-a-well-deserved-minibreak-amid-its-unreal-engine-5-move) |
| Creative Assembly（Total War） | 自研 Warscape 被其负责人称为"untenable"，改做 Warcore | 正文未读到，原因细节未查到 | [GamesRadar](https://www.gamesradar.com/games/total-war/total-wars-new-warcore-engine-will-power-total-war-medieval-3-bring-the-strategy-series-to-console-and-restore-modding-we-want-to-put-these-tools-in-the-hands-of-players) |
| 商业层面：Stormgate | 引擎先进不等于成功：2025 年 8 月发售后玩家数低（来源称同时在线最多 220-250 人）、融资 4000 万美元以上、裁员传闻 | 这是商业问题，不是引擎问题，**不要当作 SnowPlay 的技术教训** | [ixbt](https://ixbt.games/en/news/2025/08/26/40-mln-dollarov-na-stormgate-uleteli-v-trubu-proval-naslednicy-starcraft-i-gotoviashhiesia-sokrashheniia.html) / [Esports Insider](https://esportsinsider.com/what-happened-to-stormgate) |

### 3.4 单位规模和性能

| 谁 | 说法 | 出处 |
| --- | --- | --- |
| Frost Giant | 称 SnowPlay 64 tick，千级单位，公司自称，未独立测 | [搜索摘要](https://en.wikipedia.org/wiki/Stormgate) |
| Numantian（They Are Billions） | 称自研引擎可动 2 万到 3 万单位，C# 自写，物理库用 C++ | [Dev Tracker](https://v2.devtrackers.gg/theyarebillions/p/e49ddd3d-game-engine-for-20k-units) |
| 论坛 / 论文 | 虚幻 Mass 能撑 5 万单位，**但没有确定性** | [论文](https://pure.fh-ooe.at/en/studentTheses/rendering-and-ai-optimization-in-rts-games-enhancing-performance-/) |

**没找到的**：Stormgate 的 SnowPlay 公开事后复盘（只有 GDC 2024 演讲预告页，视频没读到）、Iron Harvest 在 Unity 上具体踩了什么坑（只有 2018 日志）、Tempest Rising 在虚幻上的 RTS 核心做法。用户点名的这三项，**公开资料里查不到细节**，不要当作调研已覆盖。要继续，下一步是找 GDC Vault 的视频或幻灯片、Frost Giant 的 Discord / 博客、KING Art 后续日志。

---

### 自研引擎的现身说法：EXOR Studios 的 Schmetterling（《银河破裂者》）

来源：EXOR Studios 在 Steam 上的文章《我们自研游戏引擎 Schmetterling 的优点和缺点》（2023-10-20），用户 2026-11-05 转来。

- **引擎是从游戏里长出来的**：他们做第一款游戏时用开源件拼，一款款下来才成了引擎。代码都在自己手里，新物理、光追阴影都能加。组件化实体加纯文本数据，设计师不用找程序员；资源免预处理、改了立即生效，迭代很快；还有自动崩溃报告和自动测试。
- **最大的坑是联机**：引擎和游戏都按单机写，后来加合作模式，等于"为游戏的多人版本构建整个引擎"，玩家等了好几年。**对我们**：注入时凡是改逻辑的都要保证联机一致（[ADR 0020](../adr/0020-inject-into-retail-program.md) 第 5 条）；将来做自己的游戏，从第一天就按确定性模拟设计，模型里所有数值都经过 `num.py` 一处（现在是浮点，和原版一样；模块里不许直接写浮点数），将来要做确定性模拟时只换这一个文件成定点数，这就是在打地基，不要绕过 `num.py`。
- **第二个坑是没有文档**：知识全在老员工脑子里，新人门槛很高。我们的"员工"是会话，清空就没了，所以靠交接、ADR、`docs/engine/` 和可运行的模型兜底。只在本机的 `work/re/`、私有仓库推到 GitHub 私有仓库（[ADR 0021](../adr/0021-private-github-repos.md)）。
- **第三个坑是只适合自己的品类**：要做别的类型就得从头补。我们只做 RTS，不追求通用引擎。

## 4. 结论

### 4.1 三条路线

| 路线 | 做法 | 好处 | 代价 / 风险 |
| --- | --- | --- | --- |
| A. 虚幻 5（或 Unity）做渲染，自研确定性模拟核心，仿 Stormgate / Iron Harvest | 模拟层是独立的纯数据 + 定点数代码，引擎只负责显示、动画、特效、UI；光追、DLSS、高帧率靠引擎现成能力 | 画质路线最短，我们的 Python 模型思路直接对口；Stormgate 和 Iron Harvest 证明这条路能做 | 要自己写：定点数、寻路、避让、回放、同步校验、编辑器。**Stormgate 花了 4000 万美元以上、一支大团队**（来源见 3.3），独立团队要把范围缩到很小。Unity 路线还要多承担版本变动的风险（Iron Harvest 的经历）。[推] 引擎和模拟之间的数据桥，是最容易写糟的接口 |
| B. 买 Photon Quantum（Unity） | 用现成的确定性 ECS + 定点数 + 回滚 | 省去最难的同步和回滚；官方说在 Unity 下用 | 价格和源码许可**未查到**；官方客户案例里没有 RTS，寻路和千单位规模得自己验证；锁在 Unity 和 Photon 生态。[推] 要先做一个 1000 单位的原型再决定 |
| C. 改开源引擎（Recoil 或 OpenRA） | Recoil 有成熟 lockstep 和大规模单位；OpenRA 有 C# 现代代码和完整 RTS 框架 | 联机、寻路、编辑器都是现成的，D.O.R.F. 和 BAR 已证明可行 | **GPL 传染**，整个游戏代码必须开源；画质很难到光追 / DLSS 的水平：Recoil 的渲染是自己的 OpenGL；OpenRA 是 SDL + OpenGL（见 2.3）。这条路适合做"玩法验证"，不适合"现代画质" |

**推荐（2026-11-07 修订）**：路线 A，逻辑核心用纯 C# 加定点数，不依赖引擎；引擎只做表现层（照红警重制版"逻辑 DLL + 表现客户端"的结构）。用户 11-07 定下的前提有三条：
1. 画风三渲二加手绘贴图，3D 管线，固定斜视角；
2. 主打 PC，兼顾手机；
3. 程序、美术、音乐都靠 AI 生成和管理。

在这三条前提下，引擎**主选 Godot 4、备选 Unity**，最后由原型实测来定，不再推荐虚幻 5。虚幻 5 的长处是写实画质，三渲二和手机用不上；它的资源是二进制，AI 也改不了。

| 选 Godot 的理由 | 要用原型核实的风险 |
|---|---|
| 场景和资源都是文本，命令行能无界面运行，AI 能直接改 | AI 常把 Godot 3 的接口写进 Godot 4 的代码 |
| 开源，可以读引擎源码，可以把编辑器改成地图编辑器和 mod 工具 | 三渲二的现成资源比 Unity 少，要自己写 |
| 许可是 MIT，没有厂商风险 | 手机端的成熟度和 C# 导出要实测 |

Unity（以及团结引擎）在两种情况下胜出：手机实测不过关，或者需要上微信小游戏。路线 B 仍作备选。**不推荐**路线 C 做最终产品。

### 4.2 我们现在的 Python 引擎模型能带过去什么

依据：ADR 0019（`docs/adr/0019-port-game-logic-by-layer.md`）里的方针是"脚本引擎、物体模块、武器、AI，每层对拍验收，只做认知工具"。

| 带得走 | 为什么 | 带不走 / 要重做 |
| --- | --- | --- |
| 对拍方法（同场景在模型和实机跑两遍比计数器） | 这就是业界的"每 tick 状态校验 + 回放对比"的换名版（见 3.1） | — |
| 游戏规则的**清单和接口设计**：脚本动作集、物体模块分类、武器伤害公式、AI 的决策结构 | 是规则层面的知识，不依赖语言 | — |
| 纯函数、数据驱动的写法 | 利于确定性：状态进、状态出、没有隐藏全局 | Python 的浮点和字典顺序：新引擎必须换成定点数和有序结构。[推] 现在就在模型里禁用裸浮点会让以后好搬 |
| 寻路的已有结果（ADR 0019 说寻路较完整） | 算法可参考 | 正式引擎里要定点化、重新实现，性能差几个数量级 |
| 关卡 / 题卡 / 课程表的设计方法（ADR 0010） | 与引擎无关 | — |

**不能带的**：红警 3 的物体和模块、脚本是 EA 的闭源引擎行为，Generals 源码是 GPL-3。把它们的代码或数据搬进商业游戏，GPL 会传染，且 ADR 0018 已规定移植代码只放私有仓库。[推] 做新游戏时只保留"思路和接口"，规则和代码要重写，不要拷。

### 4.3 下一步可选

1. **推荐**：做引擎原型，等用户定开工时机。范围如下：
   - C# 定点数逻辑核心，先只有移动和攻击；
   - 500 个三渲二单位，带描边、边缘光、阵营色；
   - 简单界面，PC 用鼠标框选，手机用触屏；
   - 音效和音乐播放。

   Godot 版要同时跑在 PC 和一台安卓手机上；三渲二着色器另做一份 Unity 对照。要量四样：AI 从零搭起要几轮、用多少额度；改一个需求要几轮；手机帧率；画面观感。
2. 补查：GDC Vault 的 SnowPlay 演讲和 Frost Giant 公开复盘；Photon Quantum 价格页；Tempest Rising 开发者访谈。
3. 停：如果最终产品打算只做 mod，这份调研到此为止，不继续。

---

## 附：本次调研的缺口

- 未读到正文：Total War 的 GamesRadar 文章、Manor Lords 的 Epic 访谈、They Are Billions 的 Dev Tracker 页（页面或 503 / 403，内容来自搜索摘要）。
- 未查到：Battle Aces 的引擎；Tempest Rising / Homeworld 3 / ZeroSpace 的联机模型；Photon Quantum 的价格和源码许可；0 A.D. 是否有确定性模拟（它一般被认为有，但**我没查到出处，不要采信**）；OpenRA 的联机模型的直接出处；商业寻路中间件。
- Recoil、RVO2、OpenSAGE 的许可，搜索结果之间有小冲突，**使用前必须读仓库里的 LICENSE 原文**。
