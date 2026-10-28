# 玩家视角的动态布局：时间线测量

由 [timeline_measure.py](timeline_measure.py) 生成（只读原版存档和 Mods 里我们编好的地图）；原始数据 [timeline.json](timeline.json)。算法、近似和每一项怎么量的，见 timeline_measure.py 开头。读数时记住：

- 时刻写成"锚点 + 秒"。"开局"是任务开始；P1、P2……是玩家推进（进区域、拆掉某物、目标完成……）才会发生的事，每关末尾列出它们是什么、最早从什么时候起才可能发生。"+ L"是一段长度未知的视频或语音；"≈"表示这个时刻混了几条互不相干的链，或者用了随机计时器的中值。
- "已知区域"= 当前可玩区 ∩（还没收回的永久揭图 ∪ 一次性揭图 ∪ 玩家和盟友开局单位、后来到手的单位、玩家推进到过的地方周围 500 的视野）。500 是视野的近似，"推进到过的地方"只取那个锚点条件里的区域或物体位置，玩家路上看见的不算——所以玩家推进以后的已知区域**偏小**。揭开又收回的（过场里揭全图）只算"看过一眼"。
- 排的是普通难度；只在别的难度生效的脚本不进这条线，开局计时上的差别记在 json 的 difficulty_diffs。
- "被领着看"：目标亮出前后 10 秒内（不计视频长度 L），同一条锚点链上有镜头移到标记 700 以内、揭开标记那里、闪烁标记物体或雷达事件。

## 验收表（对照手排时间线）

| 关 | 手排事件 | 手排时刻 | 排出来的 | 对上了吗 |
|---|---|---|---|---|
| 起盟1 伊贺 | 交还控制 | 约 14 | 开局 + 14.1 秒 | 对上 |
| 起盟1 伊贺 | 开局第 1 块边界（开场镜头里切） | 开场镜头中（约 9） | 开局 + 9.1 秒 | 对上 |
| 起盟1 伊贺 | 目标"护送基地车"亮 | 约 16 | 开局 + 16.1 秒 | 对上 |
| 起盟1 伊贺 | 目标"基地车必须存活"亮 | 约 28（目标 1 + 12 秒计时，且 45 号语音播完） | 开局 + 19.1 秒 + L | 对上：两个条件取晚：计时到 16.1 + 12 = 28.1，语音到 16.1 + 3 + L；排序时 L 按 15 秒估，所以写成了后者。L ≥ 9 秒时两者相同 |
| 起盟1 伊贺 | 扩到蓝边界 | 山顶清空 + 6 + 6 | P4 + 0 秒 | **对不上**：排出来挂在"基地车进 Bridge Problems 区"那条兜底路径上（桥全炸了直接扩图），它是"最早可能"的那条，不是正常路线；算法取所有路径里最早的，分不出哪条是主线 |
| 起盟1 伊贺 | 目标"打败慎三的效忠派"亮 | T2 + 30（T2 = 蓝边界） | ≈P11 + 30 秒 | 对上：秒数对上，锚点是"山顶清空"而不是蓝边界（同上一条） |
| 帝3 敖德萨 | 交还控制 | 6 | 开局 + 6 秒 | 对上 |
| 帝3 敖德萨 | 目标 1 亮 | 8.5 + L₂ | 开局 + 8.5 秒 + L | 对上 |
| 帝3 敖德萨 | 切到 0 号边界（巨人登场） | 目标 1 完成后的过场里 | P1 + 8.1 秒 | 对上 |
| 帝3 敖德萨 | 目标 2 亮 | D + 28.6 | P1 + 28.6 秒 | 对上 |
| 帝3 敖德萨 | 奖励目标亮 | D + 34.6 | P1 + 34.6 秒 | 对上 |
| 帝3 敖德萨 | 目标 3 亮 | E + 2（E = TH04、TH11 播完） | P1 + 36.6 秒 + L + L | 对上 |
| 帝2 斯大林格勒 | 开场全图揭开、交还控制时收回 | 0～7 | 开局 + 7 秒 | 对上 |
| 帝2 斯大林格勒 | 交还控制时已知区域（全图揭开已收回） | 只剩出生点附近 | 已知 4%，看过 100% | 对上 |
| 帝2 斯大林格勒 | 目标 1 亮 | 10.5 + L₇ + 1 + L₁ + 1 | 开局 + 11.5 秒 + L + L | 对上：差 1 秒（12.5 vs 11.5），没查出是哪一段的 1 秒缓冲 |
| 帝2 斯大林格勒 | 母亲像过场：揭开半径 200 | D₁ + 5～6 | P13 + 5 秒 | 对上 |
| 帝2 斯大林格勒 | 目标 2 亮 | D₁ + 14 + L₂ + 1 | P13 + 15 秒 + L | 对上 |
| 帝2 斯大林格勒 | 奖励目标亮 | 目标 2 + 6 | P13 + 21 秒 + L | 对上 |
| 帝2 斯大林格勒 | 目标 3 亮 + 河道永久揭开 | D₂ + 7 | P15 + 7 秒 | 对上 |
| 帝2 斯大林格勒 | 揭开整条河道 | D₂ + 7 | P15 + 7 秒 | 对上 |
| 起盟3 宫古岛 | 开场过场结束 | 约 32（含两段视频） | 开局 + 22 秒 + L | 对上：22 + L，L≈10 时对上 |
| 起盟3 宫古岛 | 目标 1 亮 | 过场结束 + 2 | 开局 + 24 秒 + L | 对上 |
| 起盟3 宫古岛 | 目标 2 亮 | 目标 1 完成 + 1 + 台词 + 2 | P1 + 2 秒 | **对不上**：排出"P + 2"：亮目标 2 的脚本只等一个旗标，等台词的那个旗标在另一条路上，没跟上 |
| 起盟3 宫古岛 | 奖励目标亮 | 目标 2 + 1 | P1 + 3 秒 | 对上：相对目标 2 晚 1 秒，对上 |
| 起盟3 宫古岛 | 目标 3 亮 | 高良认输 + 约 49 + L（扩图 +1、存档 +1、过场约 42、EVA 台词） | P16 + 50 秒 + L | 对上 |
| 盟8 哈瓦那 | 目标 1 亮 | 12 | 开局 + 12 秒 | 对上 |
| 盟8 哈瓦那 | 目标 2 亮 | 目标 1 完成 + 5.5 | P2 + 5.5 秒 | 对上 |
| 盟8 哈瓦那 | 目标 3 亮 | 目标 2 完成 + 5 | P17 + 5 秒 | 对上 |
| 盟8 哈瓦那 | 目标 4 亮 | P + 12（P = 第二段，目标 3 完成 + 3 + 过场 20～40） | ≈P17 + 30.2 秒 + L + L | 对上：目标 3 完成 + 30.2 + 两段影片：和"+3 + 过场 + 12"一致 |
| 盟8 哈瓦那 | 目标 5 亮 | P + 17（目标 4 + 5） | ≈P17 + 35.2 秒 + L + L | 对上 |
| 帝7 横滨 | 开场过场结束 | T26～27 | 开局 + 26 秒 | 对上 |
| 帝7 横滨 | 目标 1 亮 | T28 + L₄ | 开局 + 28 秒 + L | 对上 |
| 帝7 横滨 | 目标 3 亮 | 目标 2 完成 + 约 21 | P31 + 21 秒 | 对上 |
| 帝7 横滨 | 奖励目标 2 亮 | 库可夫到场 + 约 44 + 8 | P8 + 51 秒 | 对上：秒数对上；锚点取了"盟军快被打光，苏军提前到场"那条路，而不是 G3 + 180 的计时（同伊贺：算法取最早可能） |
| 百1 研究所 | 开场两段视频加运镜结束 | 约 78 | 开局 + 77.7 秒 | 对上 |
| 百1 研究所 | 目标 1 亮 | C + 1 | 开局 + 78.7 秒 | 对上 |
| 百1 研究所 | 武士 B 冲锋 | 进 Warrior 01 区 | P41 + 0 秒 | 对上 |
| 百1 研究所 | 目标 2 亮 | 读升级文件 F4 + 8 + IZ03 + 3 | P16 + 38.7 秒 | 对上：脚本在播 IZ03 时用 400 帧（26.7 秒）等视频放完，手排把这段写成了未知长度；8 + 1 + 26.7 + 3 = 38.7 |
| 我们 A4 冰雕里的兵 | 第 1 段主目标亮 | 段开始 2 秒 | 开局 + 2 秒 | 对上 |
| 我们 A4 冰雕里的兵 | 第 1 段第 2 个奖励目标亮 | 段开始 2 + 4 + 4 秒 | 开局 + 10 秒 | 对上 |
| 我们 A4 冰雕里的兵 | 第 2 段主目标亮 | 最晚 1:00 + 2 秒 | 开局 + 62 秒 | 对上：排的是"计时到"那条；广场封过 + 10 秒那条更早时会提前 |
| 我们 A4 冰雕里的兵 | 港口生变：扩到全图 | 车队到达 halt（玩家推进） | P17 + 0 秒 | 对上 |
| 我们 S6 拜科努尔 | 第 1 段主目标亮 | 段开始 2 秒 | 开局 + 2 秒 | 对上 |
| 我们 S6 拜科努尔 | 倒计时段主目标亮 | 1:30 + 2 秒 | 开局 + 92 秒 | 对上 |
| 我们 S6 拜科努尔 | 倒计时段两个奖励目标亮 | 1:30 + 6 / + 10 秒 | 开局 + 100 秒 | 对上 |
| 我们 S6 拜科努尔 | 开场试探（第一股敌人） | 0:30 | 开局 + 30 秒 | 对上 |

## 汇总：原版 40 关 vs 我们 11 关

| | 原版 | 我们 |
|---|---|---|
| 测到的关 | 40 | 11 |
| 交还控制时已知区域占可玩区（中位数） | 24% | 11% |
| 交还控制前在过场里"看过一眼"更大范围的关（看过的比已知多 20% 以上） | 17 | 0 |
| 交还控制时出生点在已知区域的 | 边上 13、角落 10、中间 9、框外 6、? 2 | 中间 11 |
| 开场有镜头领着看的关 | 36/40 | 2/11 |
| 其中领着看了几处（中位数） | 2 | 1 |
| 主目标总数 | 133 | 30 |
| 主目标怎么被发现 | 领着看 48、标记在未知区域 40、只有标记（在已知区域） 19、没有标记 14、走近才触发 12 | 只有标记（在已知区域） 13、标记在未知区域 12、领着看 4、走近才触发 1 |
| 主目标亮出时已知区域占比（中位数） | 19% | 11% |
| 奖励目标总数 | 43 | 16 |
| 奖励目标怎么被发现 | 标记在未知区域 15、走近才触发 13、领着看 9、没有标记 4、只有标记（在已知区域） 2 | 标记在未知区域 8、走近才触发 3、没有标记 2、只有标记（在已知区域） 2、领着看 1 |
| 敌人第一次露面：开局就在视野里 / 计时出动 / 玩家推进才出动 / 排不出 | 15 / 3 / 22 / 0 | 1 / 8 / 1 / 1 |
| 其中开局或计时的，露面时刻（中位数，秒） | 19.55 | 30 |
| 预摆的敌方机动单位：定时出动的比例（每关中位数） | 8% | 0% |
| 　　等玩家触发的比例 | 16% | 0% |
| 　　睡着（等触发 + 脚本从不调动）的比例 | 92% | 100% |
| 关键时刻个数（中位数） | 8 | 5 |
| 已知区域从交还控制到最后一个关键时刻涨了多少（中位数，按上面的近似算） | 11% | 1% |

读这张表：

- **原版几乎每关开场都领着看（36/40），我们 2/11。** 原版的开场过场平均指两处（出生点、第一个目标或敌人），17 关还在过场里把更大的范围（常常是全图）揭开给玩家看一眼、交还控制时再收回（斯大林格勒、直布罗陀是典型）。我们没有开场过场：交还控制就是开局 0 秒，玩家只看得见自己单位周围。
- **交还控制时的已知区域**：原版中位数 24%，我们 11%。原版大的那部分来自开局就永久揭开的出生区（`RevealerWP_MissionStart` 一类）和第一块小边界；我们没有揭图，已知区域只是单位周围一圈。注意：我们的检查构建本来带一条 `Test - reveal`（全图揭开，给测试台用），这里已经剔掉，否则我们每关都是 100%。
- **主目标被领着看过**：原版 48/133（36%），我们 4/30（13%）。原版另有 40 个主目标亮出时标记在玩家还不知道的地方（要自己去找），我们 12 个；我们更多是"标记就在已知区域里"——因为我们的目标多半就在出生点旁边（布局卡第 3 条）。
- **奖励目标**：原版 43 个里 13 个"走近才触发"（发现某物或进某区才亮），15 个亮出时在未知区域，只有 2 个亮出时就看得见；我们 16 个里 8 个在未知区域、3 个走近才触发。差别不在比例，而在原版奖励目标会随推进"冒出来"。
- **敌人第一次露面**：原版 22/40 是玩家推进才出动、15/40 开局就在视野里（预摆的敌方据点）、只有 3/40 靠计时；我们 8/11 靠计时（"开场试探 0:30"一类）。原版预摆的敌方机动单位每关中位数 92% 是"睡着"的（等触发或脚本从不调动，靠自身警戒），我们是 100%——但我们的敌人几乎都是脚本刷出来的，预摆的很少，这一项对我们意义不大。
- **已知区域随推进涨了多少**（原版 +11%，我们 +1%）：这是最粗的一项，玩家推进后的视野只按锚点条件里的区域或物体算，**偏小**；只用来比较"关卡有没有主动揭图"，不要当成玩家真实看到的。
- "交还控制时出生点在已知区域的中间"在已知区域只是出生点周围一圈时是必然的；这一行只在有揭图、有小边界的关才有意义（原版边上 13、角落 10）。

已知的不准确处：

1. **多条路取最早**：一个旗标或计时器有几个来源（主线和兜底路径）时，算法取最早可能的那个，分不出哪条是主线。伊贺"扩蓝边界"挂到了"桥全炸了"的兜底路径上，横滨"奖励目标 2"挂到了"盟军快被打光、苏军提前到场"上（秒数仍对得上）。
2. **"忙碌"旗标当成一直为真**：`FLAG(f_is_audio_playing, 0)` 这类"没在播别的"的门，开局为 0，算法当它一直成立，所以等台词、等别的过场的脚本会排早（宫古岛目标 2 少了一段台词）。
3. **视频和语音长度未知**写成 L；比较"计时器 vs 播完"谁晚时 L 按 15 秒估（伊贺目标 2：手排 28，排出 19.1 + L）。脚本自己用帧数等视频的（研究所 400 帧）会算成具体秒数。
4. **玩家推进的锚点不排先后**：两个互不相干的玩家推进锚点（P3、P7）谁先发生算不出；只有在同一条链上（P7 是在 P3 之后才开始等的）才算"已经发生"。所以某个关键时刻的"已知区域"只包括同一条链上已经发生的揭图和到手的单位。
5. 视野半径 500 是近似；玩家单位会走动，路上看到的不算；揭开又收回的只算"看过一眼"。
6. 开场过场里由脚本单位走进某区域才结束的（直布罗陀、库页岛、隐岐群岛），"交还控制"是个 P 锚点，不是具体秒数。
7. 只排普通难度；简单、困难只在 json 的 difficulty_diffs 里记开局计时上的差别。


## 每关

### 盟1 布莱顿海滩（camp_a01_brightonbeach_smith）

- 交还控制：开局 + 22 秒；开场镜头 2 次、指过 2 处。敌人第一次露面：开局 + 22 秒（开局就在视野里，开局，东）。开局预摆的敌方机动单位：定时出动 12、等玩家触发 6、脚本从不调动 22。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 22 秒 | 交还控制 | 1 | 100% / 100% | 角落（Intro Cine 05（1 处）） | 东 | 主 Objective 01 - Destroy Soviets 东 1438（4/4 已知） |
| 开局 + 22 秒 | 亮目标 Objective 01 - Destroy Soviets | 1 | 100% / 100% | 角落（Intro Cine 05（1 处）） | 东 | 主 Objective 01 - Destroy Soviets 东 1438（4/4 已知） |
| P14 + 0 秒 | 亮目标 Bonus Obj 05 - Construct IFVs | 1 | 100% / 100% | 角落（Intro Cine 05（1 处）） | 东 | 奖 Bonus Obj 05 - Construct IFVs（无标记）；主 Objective 01 - Destroy Soviets 东 1438（4/4 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective 01 - Destroy Soviets | 开局 + 22 秒 | 只有标记（在已知区域） |
| 奖励 Bonus Obj 05 - Construct IFVs | P14 + 0 秒 | 没有标记 |

锚点：P14 = Player_1 造出 alliedwarfactory（开局 + 5 秒 起）

### 盟2 戛纳（camp_a02_cannes_smith）

- 交还控制：开局 + 20.4 秒；开场镜头 6 次、指过 6 处。敌人第一次露面：P11 + 0 秒（NAMED_ATTACK_AREA UNIT - Soviet 01 Leviathan 01，玩家推进，东）。开局预摆的敌方机动单位：定时出动 28、等玩家触发 0、脚本从不调动 144。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 20.4 秒 | 交还控制 | 0 | 10% / 65% | 中间（出生点） | 东、东北 | — |
| 开局 + 22.4 秒 + L | 亮目标 Objective 02 - Send in Spies | 0 | 10% / 65% | 中间（出生点） | 东、东北 | 主 Objective 02 - Send in Spies 东南 2714（0/4 已知） |
| 开局 + 27.4 秒 + L | 亮目标 Objective 01 - Rescue Convention Center | 0 | 10% / 65% | 中间（出生点） | 东、东北 | 主 Objective 01 - Rescue Convention Center 东北 2733（0/1 已知）；主 Objective 02 - Send in Spies 东南 2714（0/4 已知） |
| P6 + 1 秒 | 亮目标 Objective 04 - Destroy Leviathans | 0 | 10% / 65% | 中间（出生点） | 东、东北 | 主 Objective 04 - Destroy Leviathans 东 3306（0/4 已知） |
| ≈P5 + 5 秒 | 亮目标 Objective 03 - Port Authority | 0 | 13% / 66% | 边上（出生点） | 东、东北 | 主 Objective 03 - Port Authority 东 3188（0/1 已知） |
| P8 + 5 秒 | 亮目标 Objective 05 - Destroy Soviet Base | 0 | 13% / 67% | 边上（出生点） | 东、东北 | 主 Objective 05 - Destroy Soviet Base（无标记） |
| P10 + 5 秒 | 亮目标 BonusObjective - Save Vindicators | 0 | 10% / 65% | 中间（出生点） | 东、东北 | 奖 BonusObjective - Save Vindicators 东南 4624（0/1 已知） |
| P21 + 4 秒 + L | 大块揭图 全图 | 0 | 100% / 100% | 边上（出生点） | 东、东北、东南 | — |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective 02 - Send in Spies | 开局 + 22.4 秒 + L | 标记在未知区域 |
| 主 Objective 01 - Rescue Convention Center | 开局 + 27.4 秒 + L | 标记在未知区域 |
| 主 Objective 04 - Destroy Leviathans | P6 + 1 秒 | 标记在未知区域 |
| 主 Objective 03 - Port Authority | ≈P5 + 5 秒 | 标记在未知区域 |
| 主 Objective 05 - Destroy Soviet Base | P8 + 5 秒 | 没有标记 |
| 奖励 BonusObjective - Save Vindicators | P10 + 5 秒 | 走近才触发 |

锚点：P5 = UNIT_HAS_MODELCONDITION(UNIT - Soviet Dock 07, INFILTRATED_VISION)（开局 + 0 秒 起）；P6 = Soviet01/TEAM - Soviet 01 - Dreadnaughts 被 Player_1 攻击（开局 + 0 秒 起）；P8 = Player_1 的单位在 TRIG_S05 - Base Radius（开局 + 0 秒 起）；P10 = Player_1 发现 Soviet03/TEAM_S3 - Bonus Objectives（开局 + 0 秒 起）；P11 = <This Player's Enemies> 的单位在 TRIG_S1 - Bombard（开局 + 0 秒 起）；P21 = BUILDING_GARRISONNED_BY_OBJECT_TYPE(UNIT - Port Authority, alliedcommandotech1, Player_1)（≈P5 + 10 秒 起）

### 盟3 海德堡（camp_a03_heidelberg_smith）

- 交还控制：开局 + 17 秒；开场镜头 1 次、指过 1 处。敌人第一次露面：P10 + 0 秒（刷出 sovietrefinery，玩家推进，北）。开局预摆的敌方机动单位：定时出动 14、等玩家触发 9、脚本从不调动 166。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 17 秒 | 交还控制 | 0 | 3% / 100% | 图外（出生点） | 西北 | — |
| 开局 + 18 秒 | 亮目标 Objective01 - Escort MCVs | 0 | 3% / 100% | 图外（出生点） | 西北 | 主 Objective01 - Escort MCVs 西北 1398（0/4 已知） |
| P5 + 0 秒 | 亮目标 Objective03 - Destroy Soviet Base | 0 | 6% / 100% | 图外（出生点） | 北、西北 | 主 Objective03 - Destroy Soviet Base 北 3789（2/7 已知） |
| P4 + 7 秒 | 大块揭图 全图 | 0 | 100% / 100% | 图外（出生点） | 北、西北、西 | — |
| P7 + 8 秒 + L | 亮目标 Objective05 - Destroy Soivet Headquarters | 0 | 6% / 100% | 图外（出生点） | 北、西北 | 主 Objective05 - Destroy Soivet Headquarters 北 4565（0/1 已知） |
| P4 + 22 秒 + L | 亮目标 Objective04 - Destroy Soivet Iron Curtain | 0 | 6% / 100% | 图外（出生点） | 西北 | 主 Objective04 - Destroy Soivet Iron Curtain 北 3641（0/1 已知） |
| P4 + 29 秒 + L + L | 亮目标 Objective02 - Destroy Advanced Power Plants | 0 | 6% / 100% | 图外（出生点） | 西北 | 主 Objective02 - Destroy Advanced Power Plants 北 3683（0/6 已知）；主 Objective04 - Destroy Soivet Iron Curtain 北 3641（0/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 - Escort MCVs | 开局 + 18 秒 | 标记在未知区域 |
| 主 Objective03 - Destroy Soviet Base | P5 + 0 秒 | 走近才触发 |
| 主 Objective05 - Destroy Soivet Headquarters | P7 + 8 秒 + L | 标记在未知区域 |
| 主 Objective04 - Destroy Soivet Iron Curtain | P4 + 22 秒 + L | 标记在未知区域 |
| 主 Objective02 - Destroy Advanced Power Plants | P4 + 29 秒 + L + L | 标记在未知区域 |

锚点：P4 = UNIT - MCV 02 进入 AREA - MCV 2 Dropoff（开局 + 0 秒 起）；P5 = UNIT - Soviet Barracks 05 被毁（开局 + 0 秒 起）；P7 = UNIT - Soviet Iron Curtain 被毁（开局 + 0 秒 起）；P10 = UNIT - Soviet Barracks 03 被毁 且 UNIT - Soviet Barracks 04 被毁（开局 + 0 秒 起）

### 盟4 直布罗陀（camp_a04_gibraltar_hayes）

- 交还控制：P1 + 3.2 秒；开场镜头 2 次、指过 2 处。敌人第一次露面：P1 + 0 秒（TEAM_FOLLOW_WAYPOINTS Japan01/TEAM - Commando Fodder 01，玩家推进，方向未知）。开局预摆的敌方机动单位：定时出动 13、等玩家触发 25、脚本从不调动 358。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| P1 + 3.2 秒 | 交还控制 | 4 | 5% / 100% | 图外（出生点） | 东北、北 | — |
| P1 + 3.2 秒 | 换边界 4 | 4 | 5% / 100% | 图外（出生点） | 东北、北 | — |
| P2 + 4.2 秒 | 换边界 1 | 1 | 100% / 100% | 图外（出生点） | 东北、北、西北 | — |
| P2 + 8 秒 | 换边界 5 | 5 | 100% / 100% | 图外（出生点） | 东北、北、西北 | — |
| P1 + 19.2 秒 | 亮目标 Objective1a | 4 | 5% / 100% | 图外（出生点） | 东北、北 | 主 Objective1a 北 5079（0/4 已知） |
| P4 + 19.2 秒 | 亮目标 OBJECTIVE 3 | 1 | 100% / 100% | 边上（Objective 2 - Transfer（1 处）） | 东北、北、西南 | 主 OBJECTIVE 3 北 2901（5/5 已知） |
| P2 + 31 秒 | 亮目标 OBJECTIVE 2 | 5 | 100% / 100% | 图外（出生点） | 东北、北、西北 | 主 OBJECTIVE 2 西北 2378（4/4 已知，雷达） |
| P1 + 54.2 秒 | 亮目标 Bonus Objective 1a | 4 | 5% / 100% | 图外（出生点） | 东北、北 | 主 Objective1a 北 5079（0/4 已知）；奖 Bonus Objective 1a 东北 4613（0/1 已知，雷达） |
| P4 + 143.2 秒 + L | 亮目标 Bonus Objective 2 | 1 | 100% / 100% | 边上（Objective 2 - Transfer（1 处）） | 东北、北、西南 | 主 OBJECTIVE 3 北 2901（5/5 已知）；奖 Bonus Objective 2 东南 1403（1/1 已知，揭图、雷达） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective1a | P1 + 19.2 秒 | 标记在未知区域 |
| 主 OBJECTIVE 3 | P4 + 19.2 秒 | 只有标记（在已知区域） |
| 主 OBJECTIVE 2 | P2 + 31 秒 | 领着看（雷达） |
| 奖励 Bonus Objective 1a | P1 + 54.2 秒 | 领着看（雷达） |
| 奖励 Bonus Objective 2 | P4 + 143.2 秒 + L | 领着看（揭图、雷达） |

锚点：P1 = UNIT - Natasha 进入 AREA - Commando Start 且 UNIT - Tanya 进入 AREA - Commando Start（开局 + 0 秒 起）；P2 = UNIT - J3 Warfactory 2 被毁 且 UNIT - Japan Hangar 01 被毁 且 UNIT - Japan Hangar 02 被毁 且 UNIT -（开局 + 0 秒 起）；P4 = UNIT - J2 - Destroyer freedom target 1 被毁 且 UNIT - J2 - Destroyer freedom target 2 被毁 且 UN（开局 + 0 秒 起）

### 盟5 北海（camp_a05_northsea_white）

- 交还控制：开局 + 18 秒；开场镜头 4 次、指过 1 处。敌人第一次露面：P3 + 0 秒（刷出 Team-RocketAngels01，玩家推进，东北）。开局预摆的敌方机动单位：定时出动 3、等玩家触发 136、脚本从不调动 60。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 18 秒 | 交还控制 | 4 | 96% / 100% | 边上（出生点） | 东北 | 主 A05-Obj01-ProtectShip 北 579（1/1 已知，镜头、闪烁） |
| 开局 + 18 秒 | 亮目标 A05-Obj01-ProtectShip | 4 | 96% / 100% | 边上（出生点） | 东北 | 主 A05-Obj01-ProtectShip 北 579（1/1 已知，镜头、闪烁） |
| 开局 + 111 秒 | 换边界 2 | 2 | 64% / 73% | 图外（出生点） | 东北、北 | — |
| 开局 + 114 秒 | 大块揭图 RevealerWP_CenterofSecondMap | 2 | 100% / 100% | 边上（Objective02a-SpawnEngineers（4 ） | 东、东北、东南 | — |
| 开局 + 132 秒 | 亮目标 A05-Obj02-DestroyRadarShips | 2 | 100% / 100% | 边上（Objective02a-SpawnEngineers（4 ） | 东、东北、东南 | 主 A05-Obj02-DestroyRadarShips 东北 1062（1/1 已知） |
| P7 + 6 秒 | 换边界 3 | 3 | 100% / 100% | 边上（Objective02b-SpawnPlayerUnits（） | 东、西、西南 | — |
| P7 + 6 秒 | 大块揭图 RevealerWP_CenterofThirdMap | 3 | 100% / 100% | 边上（Objective02b-SpawnPlayerUnits（） | 东、西、西南 | — |
| P9 + 6 秒 | 亮目标 A05-BonusObj02A-DestroyPowerGenerators | 2 | 100% / 100% | 边上（Objective02a-SpawnEngineers（4 ） | 东、东北、东南 | 主 A05-Obj02-DestroyRadarShips 东北 1062（1/1 已知）；奖 A05-BonusObj02A-DestroyPowerGenerators 北 1106（3/3 已知） |
| P7 + 13 秒 + L + L + L | 亮目标 A05-Obj02-DestroyRadarShip2 | 3 | 100% / 100% | 边上（Objective02b-SpawnPlayerUnits（） | 东、西、西南 | 主 A05-Obj02-DestroyRadarShip2 东 1732（1/1 已知，揭图） |
| P20 + 0 秒 | 亮目标 A05-BonusObj02B-CapturePowerPlants | 3 | 100% / 100% | 边上（Objective02b-SpawnPlayerUnits（） | 东、西、西南 | 奖 A05-BonusObj02B-CapturePowerPlants 东 1007（4/4 已知） |
| P19 + 7 秒 | 换边界 0 | 0 | 100% / 100% | 边上（Objective3Activate1（1 处）） | 东北、北 | — |
| P19 + 7 秒 | 大块揭图 全图 | 0 | 100% / 100% | 边上（Objective3Activate1（1 处）） | 东北、北 | — |
| P19 + 38 秒 | 亮目标 A05-Obj03-OverloadReactors | 0 | 62% / 100% | 边上（Objective3Activate1（1 处）） | 东北、北 | 主 A05-Obj03-OverloadReactors 北 4460（2/2 已知，揭图） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 A05-Obj01-ProtectShip | 开局 + 18 秒 | 领着看（镜头、闪烁） |
| 主 A05-Obj02-DestroyRadarShips | 开局 + 132 秒 | 只有标记（在已知区域） |
| 奖励 A05-BonusObj02A-DestroyPowerGenerators | P9 + 6 秒 | 走近才触发 |
| 主 A05-Obj02-DestroyRadarShip2 | P7 + 13 秒 + L + L + L | 领着看（揭图） |
| 奖励 A05-BonusObj02B-CapturePowerPlants | P20 + 0 秒 | 走近才触发 |
| 主 A05-Obj03-OverloadReactors | P19 + 38 秒 | 领着看（揭图） |

锚点：P3 = Player_1 的单位在 AT-EnemyNavyBackAtFIF（开局 + 0 秒 起）；P7 = Unit-Japan04-RadarBoat01 被毁（开局 + 132 秒 起）；P9 = Player_1 的单位在 AT-Island01_01（开局 + 132 秒 起）；P19 = Unit-Japan04-RadarBoat02 被毁（P7 + 11 秒 + L + L + L 起）；P20 = Player_1 的单位在 AT-Island02_Area01（P7 + 11 秒 + L + L + L 起）

### 盟6 总统山（camp_a06_mountrushmore_white）

- 交还控制：开局 + 25 秒 + L；开场镜头 4 次、指过 1 处。敌人第一次露面：开局 + 25 秒 + L（开局就在视野里，开局，北）。开局预摆的敌方机动单位：定时出动 0、等玩家触发 1、脚本从不调动 21。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 21 秒 | 亮目标 Objective01-DestroyComTower | 2 | 73% / 73% | 边上（出生点） | 北 | 主 Objective01-DestroyComTower 北 1088（1/1 已知） |
| 开局 + 25 秒 + L | 交还控制 | 2 | 73% / 73% | 边上（出生点） | 北 | 主 Objective01-DestroyComTower 北 1088（1/1 已知） |
| 开局 + 25 秒 + L + L | 亮目标 BonusObjective05-DestroyPowerplant | 2 | 73% / 73% | 边上（出生点） | 北 | 主 Objective01-DestroyComTower 北 1088（1/1 已知）；奖 BonusObjective05-DestroyPowerplant 北 1400（1/1 已知） |
| P1 + 3 秒 | 换边界 0 | 0 | 100% / 100% | 边上（出生点） | 东北、北 | — |
| P1 + 3 秒 | 大块揭图 全图 | 0 | 100% / 100% | 边上（出生点） | 东北、北 | — |
| P1 + 10 秒 | 大块揭图 全图 | 0 | 100% / 100% | 边上（Objective02-StartHere3（1 处）） | 东北、北 | — |
| P1 + 24 秒 | 亮目标 Objective02-DestroyFiringBase | 0 | 100% / 100% | 边上（Objective02-StartHere3（1 处）） | 东北、北 | 主 Objective02-DestroyFiringBase 北 2882（1/1 已知） |
| P2 + 6 秒 | 亮目标 BonObjective01-CaptureBarracks | 2 | 73% / 73% | 边上（出生点） | 北 | 主 Objective01-DestroyComTower 北 1088（1/1 已知）；奖 BonObjective01-CaptureBarracks 西北 1334（1/1 已知） |
| P5 + 8 秒 | 亮目标 Objective03-KillPresident | 0 | 100% / 100% | 边上（Objective02-StartHere3（1 处）） | 东北、北 | 主 Objective03-KillPresident 东北 1141（1/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01-DestroyComTower | 开局 + 21 秒 | 只有标记（在已知区域） |
| 奖励 BonusObjective05-DestroyPowerplant | 开局 + 25 秒 + L + L | 只有标记（在已知区域） |
| 主 Objective02-DestroyFiringBase | P1 + 24 秒 | 只有标记（在已知区域） |
| 奖励 BonObjective01-CaptureBarracks | P2 + 6 秒 | 走近才触发 |
| 主 Objective03-KillPresident | P5 + 8 秒 | 只有标记（在已知区域） |

锚点：P1 = Struct_CommTower 被毁（开局 + 21 秒 起）；P2 = Struct_PowerGenerator 被毁（开局 + 25 秒 + L + L 起）；P5 = Struct_AlliedLaserFireBase 被毁（P1 + 24 秒 起）

### 盟7 东京港（camp_a07_tokyoharbor_davis）

- 交还控制：开局 + 17 秒；开场镜头 4 次、指过 4 处。敌人第一次露面：P6 + 0 秒（TEAM_FOLLOW_WAYPOINTS_EXACT TEAM - Tatsu Fleet，玩家推进，北）。开局预摆的敌方机动单位：定时出动 4、等玩家触发 4、脚本从不调动 146。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 17 秒 | 交还控制 | 1 | 10% / 100% | 中间（出生点） | 东、东北、北 | — |
| 开局 + 17.2 秒 | 换边界 1 | 1 | 10% / 100% | 中间（出生点） | 东、东北、北 | — |
| 开局 + 19.2 秒 | 亮目标 A07_Objective_1 | 1 | 10% / 100% | 中间（出生点） | 东、东北、北 | 主 A07_Objective_1 东南 909（0/2 已知，镜头） |
| 开局 + 24.2 秒 | 亮目标 A07_Objective_B1 | 1 | 10% / 100% | 中间（出生点） | 东、东北、北 | 主 A07_Objective_1 东南 909（0/2 已知，镜头）；奖 A07_Objective_B1 东 2914（0/8 已知） |
| P4 + 9 秒 + L | 亮目标 A07_Objective_3 | 1 | 10% / 100% | 图外（Objectives - Objective 2 Grant） | 西、西南、南 | 主 A07_Objective_3 西南 2047（0/14 已知，雷达） |
| P3 + 26 秒 + L | 换边界 0 | 0 | 7% / 100% | 边上（出生点） | 东、东北、北 | — |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 A07_Objective_1 | 开局 + 19.2 秒 | 领着看（镜头） |
| 奖励 A07_Objective_B1 | 开局 + 24.2 秒 | 标记在未知区域 |
| 主 A07_Objective_3 | P4 + 9 秒 + L | 领着看（雷达） |

锚点：P3 = STRUCT - Japan04 - Base Defense 1 被毁 且 STRUCT - Japan04 - Base Defense 2 被毁 且 STRUCT - Jap（开局 + 0 秒 起）；P4 = Player_1 的单位在 AREA - Objective 2 - New Base Location（开局 + 0 秒 起）；P6 = TEAM_CREATED(TEAM - Tatsu Fleet)（开局 + 0 秒 起）

### 盟8 哈瓦那（camp_a08_havana_rao）

- 交还控制：开局 + 5.5 秒；开场镜头 3 次、指过 1 处。敌人第一次露面：开局 + 6 秒（MOVE_TEAM_TO TEAM - Tesla Elite，计时，东北）。开局预摆的敌方机动单位：定时出动 2、等玩家触发 9、脚本从不调动 141。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 5.5 秒 | 交还控制 | 1 | 0% / 0% | ?（出生点） | 东、东北 | — |
| 开局 + 12 秒 | 亮目标 A08_Objective_1 | 1 | 0% / 0% | ?（出生点） | 东、东北 | 主 A08_Objective_1 东北 1886（0/1 已知） |
| P3 + 2 秒 | 亮目标 A08_BonusObjective_1 | 1 | 7% / 7% | 图外（出生点） | 东、东北 | 奖 A08_BonusObjective_1 东北 1333（0/1 已知） |
| P2 + 5.5 秒 | 亮目标 A08_Objective_2 | 1 | 7% / 7% | 图外（出生点） | 东、东北 | 主 A08_Objective_2 东北 2686（0/1 已知） |
| P17 + 5 秒 | 亮目标 A08_Objective_3 | 1 | 14% / 14% | 图外（出生点） | 东、东北 | — |
| ≈P17 + 8 秒 | 大块揭图 全图 | 1 | 100% / 100% | 边上（出生点） | 东、东北 | — |
| ≈P17 + 10.2 秒 + L + L | 换边界 0 | 0 | 100% / 100% | 角落（出生点） | 东、东北、北 | — |
| ≈P17 + 30.2 秒 + L + L | 亮目标 A08_Objective_4 | 0 | 100% / 100% | 边上（Split - Setup Base（4 处）） | 北、西北、西、东南 | 主 A08_Objective_4 西北 2192（2/2 已知） |
| ≈P17 + 35.2 秒 + L + L | 亮目标 A08_Objective_5 | 0 | 9% / 100% | 角落（Split - Transfer Base（1 处）） | 西北、西 | 主 A08_Objective_4 西北 2487（2/2 已知）；主 A08_Objective_5 西北 3272（1/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 A08_Objective_1 | 开局 + 12 秒 | 标记在未知区域 |
| 奖励 A08_BonusObjective_1 | P3 + 2 秒 | 走近才触发 |
| 主 A08_Objective_2 | P2 + 5.5 秒 | 标记在未知区域 |
| 主 A08_Objective_3 | P17 + 5 秒 | 领着看（揭图、镜头、雷达） |
| 主 A08_Objective_4 | ≈P17 + 30.2 秒 + L + L | 走近才触发 |
| 主 A08_Objective_5 | ≈P17 + 35.2 秒 + L + L | 走近才触发 |

锚点：P2 = Player02 - Mirage Tank 1 进入 AREA - Objective 1 Zone（开局 + 0 秒 起）；P3 = Player_2 的单位在 AREA - Tanks Salvage（开局 + 0 秒 起）；P17 = Player02 - Mirage Tank 1 进入 AREA - Objective 2 Zone（P2 + 5.5 秒 起）

### 盟9 列宁格勒（camp_a09_leningrad_rao）

- 交还控制：开局 + 18.1 秒；开场镜头 4 次、指过 0 处。敌人第一次露面：开局 + 18.1 秒（开局就在视野里，开局，东、东北、北）。开局预摆的敌方机动单位：定时出动 26、等玩家触发 44、脚本从不调动 136。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 4.5 秒 | 亮目标 A09_Objective_1 | 2 | 100% / 100% | 边上（出生点） | 东、东北、北 | 主 A09_Objective_1（无标记） |
| 开局 + 18.1 秒 | 交还控制 | 2 | 38% / 100% | 角落（Introduction - Transfer Units（） | 东、东北、北 | 主 A09_Objective_1（无标记） |
| 开局 + 22.4 秒 | 亮目标 A09_Objective_0a | 2 | 38% / 100% | 角落（Introduction - Transfer Units（） | 东、东北、北 | 主 A09_Objective_0a 东北 1741（1/1 已知，揭图）；主 A09_Objective_1（无标记） |
| 开局 + 27.1 秒 | 亮目标 A09_Objective_0b | 2 | 38% / 100% | 角落（Introduction - Transfer Units（） | 东、东北、北 | 主 A09_Objective_0a 东北 1741（1/1 已知，揭图）；主 A09_Objective_0b 东北 1732（1/1 已知，揭图）；主 A09_Objective_1（无标记） |
| P6 + 5 秒 | 换边界 0 | 0 | 100% / 100% | 角落（Introduction - Transfer Units（） | 东、东北、北 | — |
| P6 + 5 秒 | 大块揭图 全图 | 0 | 100% / 100% | 角落（Introduction - Transfer Units（） | 东、东北、北 | — |
| P6 + 6 秒 + L + L | 亮目标 A09_Objective_2 | 0 | 10% / 100% | 角落（Introduction - Transfer Units（） | 东、东北、北 | 主 A09_Objective_2 东北 4311（0/7 已知，揭图、雷达） |
| P6 + 15 秒 + L + L | 亮目标 A09_Objective_3 | 0 | 10% / 100% | 角落（Introduction - Transfer Units（） | 东、东北、北 | 主 A09_Objective_2 东北 4311（0/7 已知，揭图、雷达）；主 A09_Objective_3 东北 3856（0/1 已知，揭图、镜头）；奖 A09_BonusObjective_1 东北 6420（0/1 已知，揭图、雷达） |
| P6 + 15 秒 + L + L | 亮目标 A09_BonusObjective_1 | 0 | 10% / 100% | 角落（Introduction - Transfer Units（） | 东、东北、北 | 主 A09_Objective_2 东北 4311（0/7 已知，揭图、雷达）；主 A09_Objective_3 东北 3856（0/1 已知，揭图、镜头）；奖 A09_BonusObjective_1 东北 6420（0/1 已知，揭图、雷达） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 A09_Objective_1 | 开局 + 4.5 秒 | 没有标记 |
| 主 A09_Objective_0a | 开局 + 22.4 秒 | 领着看（揭图） |
| 主 A09_Objective_0b | 开局 + 27.1 秒 | 领着看（揭图） |
| 主 A09_Objective_2 | P6 + 6 秒 + L + L | 领着看（揭图、雷达） |
| 主 A09_Objective_3 | P6 + 15 秒 + L + L | 领着看（揭图、镜头） |
| 奖励 A09_BonusObjective_1 | P6 + 15 秒 + L + L | 领着看（揭图、雷达） |

锚点：P6 = Soviet02 的 _object list_soviet all units and structs 数量（开局 + 0 秒 起）

### 起盟1 伊贺（camp_ep01_a01_igaprefecture_davis）

- 交还控制：开局 + 14.1 秒；开场镜头 4 次、指过 3 处。敌人第一次露面：开局 + 14.1 秒（开局就在视野里，开局，东、东北）。开局预摆的敌方机动单位：定时出动 4、等玩家触发 206、脚本从不调动 31。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 14.1 秒 | 交还控制 | 1 | 42% / 44% | 角落（出生点） | 东、东北 | — |
| 开局 + 16.1 秒 | 亮目标 EP01_A01_Objective_1 | 1 | 42% / 44% | 角落（出生点） | 东、东北 | 主 EP01_A01_Objective_1 东北 1301（2/2 已知，镜头） |
| 开局 + 19.1 秒 + L | 亮目标 EP01_A01_Objective_2 | 1 | 42% / 44% | 角落（出生点） | 东、东北 | 主 EP01_A01_Objective_1 东北 2168（2/3 已知，镜头）；主 EP01_A01_Objective_2 西 524（1/1 已知，镜头） |
| P4 + 0 秒 | 换边界 2 | 2 | 23% / 29% | 角落（出生点） | 东、东北 | — |
| ≈P11 + 30 秒 | 亮目标 EP01_A01_Objective_2p5 | 1 | 50% / 52% | 边上（Msn Logic - Transfer and Spawn） | 东北、西北、西南、南 | 主 EP01_A01_Objective_2p5 西北 504（0/3 已知） |
| ≈P11 + 75 秒 | 亮目标 EP01_A01_Objective_B1 | 1 | 50% / 52% | 边上（Msn Logic - Transfer and Spawn） | 东北、西北、西南、南 | 主 EP01_A01_Objective_2p5 西北 504（0/3 已知）；奖 EP01_A01_Objective_B1 西北 116（0/3 已知） |
| P13 + 6 秒 | 换边界 0 | 0 | 16% / 20% | 边上（Msn Logic - Transfer and Spawn） | 东北、西北、西南、南 | — |
| P13 + 10 秒 | 亮目标 EP01_A01_Objective_3 | 0 | 16% / 20% | 边上（Msn Logic - Transfer and Spawn） | 东北、西北、西南、南 | 主 EP01_A01_Objective_3 东北 3473（0/1 已知） |
| P18 + 15 秒 | 亮目标 EP01_A01_Objective_4 | 0 | 19% / 23% | 中间（Msn Logic - Transfer and Spawn） | 东北、西北、西南、南 | 主 EP01_A01_Objective_4 东北 3309（6/6 已知，镜头） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 EP01_A01_Objective_1 | 开局 + 16.1 秒 | 领着看（镜头） |
| 主 EP01_A01_Objective_2 | 开局 + 19.1 秒 + L | 领着看（镜头） |
| 主 EP01_A01_Objective_2p5 | ≈P11 + 30 秒 | 标记在未知区域 |
| 奖励 EP01_A01_Objective_B1 | ≈P11 + 75 秒 | 标记在未知区域 |
| 主 EP01_A01_Objective_3 | P13 + 10 秒 | 标记在未知区域 |
| 主 EP01_A01_Objective_4 | P18 + 15 秒 | 领着看（镜头） |

锚点：P4 = UNIT - Allied02 - MCV 进入 Area - Bridge Problems（开局 + 0 秒 起）；P11 = Japan02 的单位在 Area - MCV Escort - HillTop Clear（P8 + 0 秒 起）；P13 = Japan02 的 _object list_japan all production 数量 且 Japan03 的 _object list_japan all producti（≈P11 + 30 秒 起）；P18 = UNIT_HAS_OBJECT_STATUS(STRUCT - Objective 3, UNDER_FROZEN)（P13 + 10 秒 起）

### 起盟2 大阪（camp_ep01_a02_osaka_white）

- 交还控制：开局 + 3 秒 + L + L；开场镜头 4 次、指过 1 处。敌人第一次露面：P5 + 0 秒（TEAM_ATTACK_TEAM Japan_1/Team-OpenArea02-Inf1，玩家推进，东北）。开局预摆的敌方机动单位：定时出动 10、等玩家触发 0、脚本从不调动 109。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 3 秒 + L + L | 交还控制 | 2 | 29% / 100% | 角落（出生点） | 东北、北 | 主 Objective01 北 655（0/1 已知，揭图、镜头） |
| 开局 + 3 秒 + L + L | 亮目标 Objective01 | 2 | 29% / 100% | 角落（出生点） | 东北、北 | 主 Objective01 北 655（0/1 已知，揭图、镜头） |
| P4 + 3 秒 | 换边界 6 | 5 | 8% / 100% | 图外（出生点） | 东北、北 | — |
| ≈P4 + 3 秒 | 换边界 5 | 5 | 8% / 100% | 图外（出生点） | 东北、北 | — |
| P4 + 3 秒 | 大块揭图 RevealWP-KenjisVilla | 5 | 8% / 100% | 图外（出生点） | 东北、北 | — |
| ≈P4 + 6 秒 | 换边界 4 | 4 | 11% / 100% | 角落（SwarmDown-FadeIn01（1 处）） | 东北、北 | — |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 | 开局 + 3 秒 + L + L | 领着看（揭图、镜头） |

锚点：P4 = Struct-Nanoswarm02 被毁（开局 + 3 秒 + L + L 起）；P5 = Struct-Nanoswarm01 被 Player_1 攻击（P4 + 3 秒 起）

### 起盟3 宫古岛（camp_ep01_a03_miyako_stewart）

- 交还控制：开局 + 22 秒 + L；开场镜头 5 次、指过 1 处。敌人第一次露面：P1 + 0 秒（交给 Japan_1: Japan_3/Guard_Infantry，玩家推进，西北）。开局预摆的敌方机动单位：定时出动 11、等玩家触发 133、脚本从不调动 18。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 22 秒 + L | 交还控制 | 1 | 4% / 100% | 边上（出生点） | 北、西北、西 | — |
| 开局 + 24 秒 + L | 亮目标 MO_Build_Base | 1 | 4% / 100% | 边上（出生点） | 北、西北、西 | 主 MO_Build_Base 西北 1602（0/2 已知） |
| P1 + 2 秒 | 亮目标 MO_Defeat_Naomi | 1 | 4% / 100% | 边上（出生点） | 北、西北、西 | 主 MO_Defeat_Naomi（无标记） |
| P1 + 3 秒 | 亮目标 MO_Garrison_Structure | 1 | 4% / 100% | 边上（出生点） | 北、西北、西 | 主 MO_Defeat_Naomi（无标记） |
| P18 + 0 秒 | 大块揭图 wp_longrangeradar | 1 | 32% / 100% | 边上（tatsu hands over bonus units（1） | 东、东北、北、东南 | 主 MO_Defeat_Naomi（无标记） |
| P16 + 4 秒 | 换边界 0 | 0 | 4% / 100% | 中间（出生点） | 北、西北、西 | — |
| P16 + 50 秒 + L | 亮目标 MO_Defeat_Tatsu | 0 | 4% / 100% | 中间（出生点） | 北、西北、西 | 主 MO_Defeat_Tatsu（无标记） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 MO_Build_Base | 开局 + 24 秒 + L | 标记在未知区域 |
| 主 MO_Defeat_Naomi | P1 + 2 秒 | 没有标记 |
| 奖励 MO_Garrison_Structure | P1 + 3 秒 | 标记在未知区域 |
| 主 MO_Defeat_Tatsu | P16 + 50 秒 + L | 没有标记 |

锚点：P1 = Player_1 的 alliedconstructionyard 数量（开局 + 0 秒 起）；P16 = Japan_1 的 _object list_japan loss condition 数量（P1 + 2 秒 起）；P18 = o_tatsu_radar_structure 拿到 Player_1（P1 + 3 秒 起）

### 起帝1 库页岛（camp_ep01_j01_sakhalin_smith）

- 交还控制：P6 + 3 秒；开场镜头 1 次、指过 1 处。敌人第一次露面：P1 + 0 秒（刷出 sovietantivehiclevehicletech1，玩家推进，西北）。开局预摆的敌方机动单位：定时出动 0、等玩家触发 1、脚本从不调动 149。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| P6 + 3 秒 | 交还控制 | 0 | 42% / 42% | 边上（出生点） | — | — |
| P2 + 10 秒 + L | 亮目标 Objective 03 - Destroy the Soviet Forward Base | 0 | 42% / 42% | 边上（Objective 02 Complete（1 处）） | 东 | 主 Objective 03 - Destroy the Soviet Forward Base 东南 1954（0/9 已知） |
| P6 + 8 秒 + L + L | 亮目标 Objective 02 - Capture the Soviet Base | 0 | 42% / 42% | 边上（出生点） | — | 主 Objective 02 - Capture the Soviet Base 北 4984（0/1 已知） |
| P2 + 18 秒 + L + L | 亮目标 Bonus Objective 01 - Destroy Soviet Outpost | 0 | 42% / 42% | 边上（Objective 02 Complete（1 处）） | 东 | 奖 Bonus Objective 01 - Destroy Soviet Outpost 西 2694（0/3 已知）；主 Objective 03 - Destroy the Soviet Forward Base 东南 1954（0/9 已知） |
| P8 + 18 秒 + L + L + L | 亮目标 Objective 01 - Rendezvous With Soviets | 0 | 40% / 40% | 边上（出生点） | — | 主 Objective 01 - Rendezvous With Soviets 北 5471（0/1 已知） |
| P9 + 3 秒 + L | 亮目标 Objective 04 - Destroy Grinder Tanks | 0 | 42% / 42% | 边上（出生点） | 东北 | 主 Objective 04 - Destroy Grinder Tanks 东北 7158（0/5 已知） |
| P8 + 25 秒 + L + L + L + L | 亮目标 Objective 05 - Protect Kenji | 0 | 40% / 40% | 边上（出生点） | — | 主 Objective 01 - Rendezvous With Soviets 北 5471（0/1 已知）；主 Objective 05 - Protect Kenji 西北 820（1/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective 03 - Destroy the Soviet Forward Base | P2 + 10 秒 + L | 标记在未知区域 |
| 主 Objective 02 - Capture the Soviet Base | P6 + 8 秒 + L + L | 标记在未知区域 |
| 奖励 Bonus Objective 01 - Destroy Soviet Outpost | P2 + 18 秒 + L + L | 标记在未知区域 |
| 主 Objective 01 - Rendezvous With Soviets | P8 + 18 秒 + L + L + L | 标记在未知区域 |
| 主 Objective 04 - Destroy Grinder Tanks | P9 + 3 秒 + L | 标记在未知区域 |
| 主 Objective 05 - Protect Kenji | P8 + 25 秒 + L + L + L + L | 走近才触发 |

锚点：P1 = OBJECT_IS_DISGUISED_AS_TYPE(UNIT - Intro Transport, _object list_soviet all units) 且 PlyrJ（开局 + 0 秒 起）；P2 = UNIT - VIP Building 拿到 PlyrJapan（开局 + 0 秒 起）；P6 = UNIT - Player Transport 进入 AREA - Drop Off Players Transport（开局 + 0 秒 起）；P8 = PlyrJapan 的单位在 AREA - Intro Cine 06 Go（开局 + 2 秒 + L 起）；P9 = PlyrSoviet 的 sovietgrindervehicle 数量（P3 + 7 秒 起）

### 起帝2 隐岐群岛（camp_ep01_j02_okiislands_smith）

- 交还控制：≈P35 + 22 秒；开场镜头 4 次、指过 2 处。敌人第一次露面：P26 + 0 秒（TEAM_ATTACK_NAMED TEAM - Naval Attackers，玩家推进，东北）。开局预摆的敌方机动单位：定时出动 0、等玩家触发 33、脚本从不调动 42。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| P14 + 0 秒 | 大块揭图 AREA - OP 01 Reveal Area | 1 | 20% / 20% | 图外（出生点） | — | — |
| P16 + 0 秒 | 大块揭图 AREA - OP 02 Reveal Area | 1 | 17% / 17% | 图外（出生点） | — | — |
| P18 + 0 秒 | 大块揭图 AREA - OP 03 Reveal Area | 1 | 17% / 17% | 图外（出生点） | — | — |
| P20 + 0 秒 | 大块揭图 AREA - OP 04 Reveal Area | 1 | 26% / 26% | 图外（出生点） | — | — |
| P22 + 0 秒 | 大块揭图 AREA - OP 05 Reveal Area | 1 | 37% / 37% | 图外（出生点） | — | — |
| P24 + 0 秒 | 大块揭图 AREA - OP 06 Reveal Area | 1 | 57% / 57% | 图外（出生点） | — | — |
| P31 + 8 秒 + L | 亮目标 Objective 5 - Setup Ambush | 1 | 21% / 21% | 图外（出生点） | — | 主 Objective 5 - Setup Ambush 东北 2425（4/8 已知） |
| P31 + 24 秒 + L + L | 亮目标 Objective 2 - Awaken the Ronin | 1 | 21% / 21% | 图外（出生点） | — | 主 Objective 2 - Awaken the Ronin 北 1905（4/4 已知，雷达）；主 Objective 5 - Setup Ambush 东北 2425（4/8 已知） |
| ≈P35 + 11 秒 | 换边界 2 | 2 | 100% / 100% | 图外（出生点） | — | — |
| ≈P35 + 11 秒 | 大块揭图 全图 | 2 | 100% / 100% | 图外（出生点） | — | — |
| ≈P35 + 22 秒 | 交还控制 | 2 | 100% / 100% | 图外（出生点） | — | — |
| ≈P35 + 25 秒 | 亮目标 Objective 3 - Sink the Soviet Navy | 2 | 100% / 100% | 图外（出生点） | — | 主 Objective 3 - Sink the Soviet Navy 东北 4547（0/17 已知） |
| ≈P35 + 31 秒 | 亮目标 Objective 6 - Protrect the Emperor's Tomb | 2 | 100% / 100% | 图外（出生点） | — | 主 Objective 3 - Sink the Soviet Navy 东北 4547（0/17 已知）；主 Objective 6 - Protrect the Emperor's Tomb 北 2030（1/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective 5 - Setup Ambush | P31 + 8 秒 + L | 走近才触发 |
| 主 Objective 2 - Awaken the Ronin | P31 + 24 秒 + L + L | 领着看（雷达） |
| 主 Objective 3 - Sink the Soviet Navy | ≈P35 + 25 秒 | 标记在未知区域 |
| 主 Objective 6 - Protrect the Emperor's Tomb | ≈P35 + 31 秒 | 只有标记（在已知区域） |

锚点：P14 = UNIT - OP 01 拿到 PlyrJapan（开局 + 0 秒 起）；P16 = UNIT - OP 02 拿到 PlyrJapan（开局 + 0 秒 起）；P18 = UNIT - OP 03 拿到 PlyrJapan（开局 + 0 秒 起）；P20 = UNIT - OP 04 拿到 PlyrJapan（开局 + 0 秒 起）；P22 = UNIT - OP 05 拿到 PlyrJapan（开局 + 0 秒 起）；P24 = UNIT - OP 06 拿到 PlyrJapan（开局 + 0 秒 起）；P26 = TEAM - Naval Attackers 进入 AREA - Attack Emperors Tomb（开局 + 0 秒 起）；P31 = UNIT - Tank 01 拿到 PlyrJapan 且 UNIT - Tank 02 拿到 PlyrJapan 且 UNIT - Tank 03 拿到 PlyrJapan 且 （开局 + 1 秒 起）；P35 = PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA_WITH_MODELCONDITION(PlyrJapan, 2, 1, allie（P31 + 8 秒 + L 起）

### 起帝3 海参崴（camp_ep01_j03_vladivostok_smith）

- 交还控制：开局 + 18 秒 + L + L；开场镜头 5 次、指过 1 处。敌人第一次露面：P1 + 6 秒（UNIT_AI_TRANSFER_ALL PlyrOleg_01，玩家推进，西北）。开局预摆的敌方机动单位：定时出动 4、等玩家触发 114、脚本从不调动 339。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 18 秒 + L + L | 交还控制 | 1 | 11% / 100% | 中间（出生点） | 西北、西 | — |
| 开局 + 22 秒 + L + L | 亮目标 Objective 01 - Destroy the Soviet Base | 1 | 11% / 100% | 中间（出生点） | 西北、西 | 主 Objective 01 - Destroy the Soviet Base 西北 2439（0/6 已知） |
| P1 + 6 秒 | 换边界 0 | 0 | 6% / 100% | 角落（出生点） | 西北、西 | — |
| P1 + 10 秒 | 大块揭图 全图 | 0 | 100% / 100% | 边上（出生点） | 北、西北、西 | — |
| ≈P2 + 2 秒 + L + L | 亮目标 Bonus Objective 02 - Destroy the Allies Base | 1 | 11% / 100% | 中间（出生点） | 西北、西 | 奖 Bonus Objective 02 - Destroy the Allies Base 东 2029（0/1 已知） |
| P1 + 33 秒 + L | 亮目标 Objective 02 - Destroy Oleg's Base | 0 | 9% / 100% | 角落（Sub-mission Split - Part 05（1 ） | 东北、北、西 | 主 Objective 02 - Destroy Oleg's Base 北 2181（0/3 已知） |
| P1 + 39 秒 + L | 亮目标 Objective 03 - Destroy Moskvin's Base | 0 | 9% / 100% | 角落（Sub-mission Split - Part 05（1 ） | 东北、北、西 | 主 Objective 02 - Destroy Oleg's Base 北 2181（0/3 已知）；主 Objective 03 - Destroy Moskvin's Base 北 3468（0/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective 01 - Destroy the Soviet Base | 开局 + 22 秒 + L + L | 标记在未知区域 |
| 奖励 Bonus Objective 02 - Destroy the Allies Base | ≈P2 + 2 秒 + L + L | 标记在未知区域 |
| 主 Objective 02 - Destroy Oleg's Base | P1 + 33 秒 + L | 标记在未知区域 |
| 主 Objective 03 - Destroy Moskvin's Base | P1 + 39 秒 + L | 标记在未知区域 |

锚点：P1 = UNIT - Oleg 01 - APP 被毁 且 UNIT - Oleg 01 - Airfield 被毁 且 UNIT - Oleg 01 - Barracks 被毁 且 UN（开局 + 0 秒 起）；P2 = SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER(PlyrAllies, PlyrJapan)（开局 + 0 秒 起）

### 起苏1 罗马尼亚（camp_ep01_s01_romania_stewart）

- 交还控制：开局 + 14 秒；开场镜头 3 次、指过 1 处。敌人第一次露面：开局 + 14 秒（开局就在视野里，开局，北、西北、西）。开局预摆的敌方机动单位：定时出动 24、等玩家触发 44、脚本从不调动 254。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 3 秒 | 亮目标 MO_Gather_Forces | 0 | 100% / 100% | 角落（出生点） | 北、西北、西 | 主 MO_Gather_Forces 西北 3334（3/3 已知，揭图） |
| 开局 + 14 秒 | 交还控制 | 0 | 3% / 100% | 中间（sc intro cue spawn conscripts ） | 北、西北、西 | — |
| ≈P12 + 3 秒 | 亮目标 MO_Rescue_Scientists | 0 | 8% / 100% | 角落（hand over desolators（1 处）） | 东、南、东南 | — |
| ≈P12 + 3 秒 | 亮目标 MO_Escape_Hurry | 0 | 8% / 100% | 角落（hand over desolators（1 处）） | 东、南、东南 | — |
| ≈P12 + 5 秒 | 亮目标 MO_Bonus_Objective | 0 | 8% / 100% | 角落（hand over desolators（1 处）） | 东、南、东南 | — |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 MO_Gather_Forces | 开局 + 3 秒 | 领着看（揭图） |
| 主 MO_Rescue_Scientists | ≈P12 + 3 秒 | 标记在未知区域 |
| 主 MO_Escape_Hurry | ≈P12 + 3 秒 | 标记在未知区域 |
| 奖励 MO_Bonus_Objective | ≈P12 + 5 秒 | 没有标记 |

锚点：P12 = Player_1 的单位在 area_observation_outpost_c（开局 + 0 秒 起）

### 起苏2 摩尔曼斯克（camp_ep01_s02_murmansk_white）

- 交还控制：开局 + 22 秒；开场镜头 3 次、指过 1 处。敌人第一次露面：P1 + 19 秒 + L + L + L（交给 Plyr2_Allied01: Unit-AttackCliff01，玩家推进，北）。开局预摆的敌方机动单位：定时出动 0、等玩家触发 17、脚本从不调动 82。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 22 秒 | 交还控制 | 2 | 12% / 27% | 图外（出生点） | — | 主 Objective01 东北 3447（0/1 已知） |
| 开局 + 22 秒 | 亮目标 Objective01 | 2 | 12% / 27% | 图外（出生点） | — | 主 Objective01 东北 3447（0/1 已知） |
| P1 + 6 秒 + L | 换边界 0 | 0 | 14% / 21% | 角落（出生点） | — | — |
| P1 + 17 秒 + L + L + L + L | 亮目标 Objective02 | 0 | 14% / 21% | 角落（出生点） | 北 | 主 Objective02 西 853（0/1 已知，雷达） |
| P2 + 175 秒 + L + L | 亮目标 Objective03 | 0 | 18% / 25% | 角落（Objective02-ConvertBase（8 处）） | 东、东北、北 | 主 Objective03 东北 3994（1/4 已知） |
| P2 + 415 秒 + L + L + L | 亮目标 BonusObjective01 | 0 | 18% / 25% | 角落（Objective02-ConvertBase（8 处）） | 东、东北、北 | 主 Objective03 东北 3994（1/4 已知）；奖 BonusObjective01 东北 3714（0/3 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 | 开局 + 22 秒 | 标记在未知区域 |
| 主 Objective02 | P1 + 17 秒 + L + L + L + L | 领着看（雷达） |
| 主 Objective03 | P2 + 175 秒 + L + L | 只有标记（在已知区域） |
| 奖励 BonusObjective01 | P2 + 415 秒 + L + L + L | 标记在未知区域 |

锚点：P1 = Player_1 的单位在 AT_Objective01（开局 + 22 秒 起）；P2 = Player_1 的单位在 AT_Player1_Base（P1 + 17 秒 + L + L + L + L 起）

### 起苏3 尤卡坦（camp_ep01_s03_yucatan_stewart）

- 交还控制：开局 + 2 秒 + L；开场镜头 2 次、指过 2 处。敌人第一次露面：开局 + 2 秒 + L（开局就在视野里，开局，北、西北、西）。开局预摆的敌方机动单位：定时出动 8、等玩家触发 13、脚本从不调动 44。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 2 秒 | 亮目标 MO_Clear_Island_Zones | 0 | 100% / 100% | 角落（出生点） | 北、西北、西 | 主 MO_Clear_Island_Zones 西北 4409（3/3 已知，揭图） |
| 开局 + 7 秒 | 亮目标 MO_Bonus_Objective | 0 | 100% / 100% | 角落（出生点） | 北、西北、西 | 主 MO_Clear_Island_Zones 西北 4409（3/3 已知，揭图） |
| 开局 + 2 秒 + L | 交还控制 | 0 | 2% / 100% | 角落（出生点） | 西北、西 | 主 MO_Clear_Island_Zones 西北 4409（0/3 已知，揭图） |
| ≈P21 + 0 秒 | 亮目标 MO_Intercept_Allied_Miners | 0 | 6% / 100% | 角落（eject reinforcements on island） | 南、东南 | 主 MO_Intercept_Allied_Miners（无标记） |
| ≈P24 + 0 秒 | 亮目标 MO_Destroy_Allied_Base | 0 | 6% / 100% | 角落（eject reinforcements on island） | 东、南、东南 | 主 MO_Destroy_Allied_Base（无标记） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 MO_Clear_Island_Zones | 开局 + 2 秒 | 领着看（揭图） |
| 奖励 MO_Bonus_Objective | 开局 + 7 秒 | 领着看（揭图） |
| 主 MO_Intercept_Allied_Miners | ≈P21 + 0 秒 | 没有标记 |
| 主 MO_Destroy_Allied_Base | ≈P24 + 0 秒 | 没有标记 |

锚点：P21 = Soviet_1 的单位在 area_island_base_c_rp_a（P19 + 0 秒 起）；P24 = o_allied_miners_bounty_i 被毁（≈P21 + 185 秒 起）

### 起苏4 战斗机器人岛（camp_ep01_s04_warbotisland_white）

- 交还控制：开局 + 30 秒；开场镜头 3 次、指过 1 处。敌人第一次露面：开局 + 30 秒（开局就在视野里，开局，东）。开局预摆的敌方机动单位：定时出动 7、等玩家触发 2、脚本从不调动 82。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 30 秒 | 交还控制 | 1 | 77% / 77% | 图外（出生点） | 东 | 主 Objective01 东 1512（1/1 已知） |
| 开局 + 30 秒 | 亮目标 Objective01 | 1 | 77% / 77% | 图外（出生点） | 东 | 主 Objective01 东 1512（1/1 已知） |
| P1 + 0 秒 | 换边界 2 | 2 | 7% / 11% | 角落（出生点） | 东 | — |
| P1 + L + L | 亮目标 Objective02 | 2 | 7% / 11% | 角落（出生点） | 东 | 主 Objective02 北 1803（0/4 已知） |
| P3 + L | 换边界 0 | 0 | 9% / 13% | 角落（出生点） | 东、东北、北 | 主 Objective03 东北 5640（1/1 已知，揭图、镜头） |
| P3 + L | 亮目标 Objective03 | 0 | 9% / 13% | 角落（出生点） | 东、东北、北 | 主 Objective03 东北 5640（1/1 已知，揭图、镜头） |
| P3 + 2 秒 + L | 大块揭图 全图 | 0 | 9% / 100% | 角落（出生点） | 东、东北、北 | 主 Objective03 东北 5640（1/1 已知，揭图、镜头） |
| P1 + 150 秒 + L + L + L | 亮目标 BonusObjective02 - Airfield | 2 | 7% / 11% | 角落（出生点） | 东、东北、西北 | 主 Objective02 北 1803（0/4 已知）；奖 BonusObjective02 - Airfield 东北 4750（0/1 已知） |
| P6 + L | 亮目标 BonusObjective01 - CoolingTowers | 2 | 7% / 12% | 角落（出生点） | 东、东北、西北 | 主 Objective02 北 1803（0/4 已知）；奖 BonusObjective01 - CoolingTowers 北 1971（1/3 已知）；奖 BonusObjective02 - Airfield 东北 4750（0/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 | 开局 + 30 秒 | 只有标记（在已知区域） |
| 主 Objective02 | P1 + L + L | 标记在未知区域 |
| 主 Objective03 | P3 + L | 领着看（揭图、镜头） |
| 奖励 BonusObjective02 - Airfield | P1 + 150 秒 + L + L + L | 标记在未知区域 |
| 奖励 BonusObjective01 - CoolingTowers | P6 + L | 走近才触发 |

锚点：P1 = Player_1 的 sovietconstructionyard 数量（开局 + 30 秒 起）；P3 = Struct-FutureTechScience 被毁 且 Struct_WarbotFactory01 被毁 且 Struct_WarbotFactory02 被毁 且 Stru（P1 + L + L 起）；P6 = Player_1 发现 Struct_CoolingTower01（P1 + 160 秒 + L + L + L 起）

### 百1 研究所（camp_ep01_y01_facility_rao）

- 交还控制：开局 + 77.7 秒；开场镜头 4 次、指过 1 处。敌人第一次露面：开局 + 77.7 秒（开局就在视野里，开局，东、东北、东南）。开局预摆的敌方机动单位：定时出动 21、等玩家触发 40、脚本从不调动 187。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 77.7 秒 | 交还控制 | 0 | 100% / 100% | 边上（出生点） | 东、东北、东南 | — |
| 开局 + 78.7 秒 | 亮目标 Y01_Powers | 0 | 100% / 100% | 边上（出生点） | 东、东北、东南 | 主 Y01_Powers（无标记） |
| P16 + 38.7 秒 | 亮目标 Y01_GetFree | 0 | 100% / 100% | 边上（出生点） | 东、东北、东南 | 主 Y01_GetFree 东 3146（1/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Y01_Powers | 开局 + 78.7 秒 | 领着看（镜头） |
| 主 Y01_GetFree | P16 + 38.7 秒 | 只有标记（在已知区域） |

锚点：P16 = PLAYER_HAS_COMPARISON_POWER_POINTS(Yuriko, 3, 1)（开局 + 0 秒 起）

### 百2 黑色设施（camp_ep01_y02_blacksite_davis）

- 交还控制：开局 + 15.1 秒；开场镜头 3 次、指过 2 处。敌人第一次露面：开局 + 15.1 秒（开局就在视野里，开局，东、东北）。开局预摆的敌方机动单位：定时出动 3、等玩家触发 15、脚本从不调动 439。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 15.1 秒 | 交还控制 | 2 | 100% / 100% | 角落（出生点） | 东、东北 | — |
| 开局 + 21 秒 | 亮目标 Objective_1_Escape | 2 | 100% / 100% | 角落（出生点） | 东、东北 | 主 Objective_1_Escape 东北 160（1/1 已知，镜头） |
| ≈P5 + 8 秒 | 亮目标 Objective_2A_GetToThePort | 2 | 100% / 100% | 角落（出生点） | 东、东北 | 主 Objective_2A_GetToThePort 东 2538（1/1 已知） |
| P17 + 0 秒 | 换边界 0 | 0 | 100% / 100% | 角落（出生点） | 东、东北 | — |
| P17 + 6 秒 | 亮目标 Objective_3_DestroyAircraftCarriers | 0 | 100% / 100% | 角落（出生点） | 东、东北 | 主 Objective_3_DestroyAircraftCarriers 东北 3624（2/2 已知） |
| P18 + 7 秒 + L + L | 亮目标 Objective_2_DestroyFacility | 2 | 100% / 100% | 角落（出生点） | 东、东北 | 主 Objective_2_DestroyFacility 东北 1616（2/2 已知） |
| P19 + 0 秒 | 换边界 1 | 1 | 100% / 100% | 图外（出生点） | 东 | — |
| P22 + 6 秒 | 亮目标 Objective_B1_FreePrisoners | 2 | 100% / 100% | 角落（出生点） | 东、东北 | 主 Objective_2_DestroyFacility 东北 1616（2/2 已知）；主 Objective_B1_FreePrisoners（无标记） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective_1_Escape | 开局 + 21 秒 | 领着看（镜头） |
| 主 Objective_2A_GetToThePort | ≈P5 + 8 秒 | 走近才触发 |
| 主 Objective_3_DestroyAircraftCarriers | P17 + 6 秒 | 只有标记（在已知区域） |
| 主 Objective_2_DestroyFacility | P18 + 7 秒 + L + L | 走近才触发 |
| 主 Objective_B1_FreePrisoners | P22 + 6 秒 | 没有标记 |

锚点：P5 = STRUCTURE - Allied02 - Airfield 被毁 且 STRUCTURE - Allied02 - Barracks 被毁 且 STRUCTURE - Alli（开局 + 0 秒 起）；P17 = UNIT - Yuriko 进入 Area - Objective 2A（≈P5 + 8 秒 起）；P18 = UNIT - Yuriko 在 Area - Delay Objective 2 外（P12 + 0 秒 起）；P19 = UNIT - Yuriko 进入 Area - Shrink Border（P17 + 0 秒 起）；P22 = UNIT - Yuriko 在 Area - Objective B1 - Check 外（P18 + 10 秒 + L + L 起）

### 百3 大院（camp_ep01_y03_compound_rao）

- 交还控制：开局 + 10.3 秒；开场镜头 1 次、指过 1 处。敌人第一次露面：开局 + 10.3 秒（开局就在视野里，开局，东北、北、西北、西、西南、东南）。开局预摆的敌方机动单位：定时出动 27、等玩家触发 25、脚本从不调动 238。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 10.3 秒 | 交还控制 | 0 | 100% / 100% | 中间（出生点） | 东北、北、西北、西、西南、东南 | — |
| 开局 + 11.3 秒 | 亮目标 Y03_Objective_00 | 0 | 100% / 100% | 中间（出生点） | 东北、北、西北、西、西南、东南 | 主 Y03_Objective_00 西南 8（4/4 已知，镜头） |
| P19 + 5 秒 | 亮目标 Y03_Objective_01 | 0 | 100% / 100% | 中间（出生点） | 东北、北、西北、西、西南、东南 | 主 Y03_Objective_01 北 601（4/4 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Y03_Objective_00 | 开局 + 11.3 秒 | 领着看（镜头） |
| 主 Y03_Objective_01 | P19 + 5 秒 | 只有标记（在已知区域） |

锚点：P19 = Enemies 的单位在 AREA - Trigger - Backtrack 03（开局 + 21.3 秒 起）

### 帝1 俄罗斯村（camp_j01_russianvillage_white）

- 交还控制：开局 + 22 秒 + L + L；开场镜头 9 次、指过 1 处。敌人第一次露面：P4 + 0 秒（ATTACK_MOVE_NAMED_UNIT_TO Unit-Statue01_01，玩家推进，东）。开局预摆的敌方机动单位：定时出动 7、等玩家触发 22、脚本从不调动 68。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 19 秒 + L | 亮目标 Obj01-DestroyCoastalGuns | 1 | 22% / 99% | 图外（出生点） | 南、东南 | 主 Obj01-DestroyCoastalGuns 南 1482（0/2 已知，镜头） |
| 开局 + 22 秒 + L + L | 交还控制 | 1 | 22% / 99% | 图外（出生点） | 南、东南 | 主 Obj01-DestroyCoastalGuns 南 1482（0/2 已知，镜头） |
| P1 + 3 秒 + L | 亮目标 Obj02-DestroyStatues | 2 | 20% / 100% | 图外（出生点） | 南、东南 | 主 Obj02-DestroyStatues 东南 2654（0/4 已知） |
| P3 + 4 秒 | 亮目标 BonusObj01-CaptureBarracks | 2 | 30% / 100% | 图外（出生点） | 南、东南 | 奖 BonusObj01-CaptureBarracks 东南 2033（1/2 已知） |
| P10 + 0 秒 | 亮目标 BonusObj09-CaptureHospital | 2 | 30% / 100% | 图外（出生点） | 南、东南 | 奖 BonusObj09-CaptureHospital 东南 3008（1/1 已知）；主 Obj02-DestroyStatues 东南 2654（1/4 已知） |
| P8 + 1 秒 + L | 换边界 0 | 0 | 22% / 59% | 边上（出生点） | 南、东南 | — |
| P8 + 1 秒 + L + L | 亮目标 BonusObj08-BringDownTeslaCoils | 0 | 22% / 59% | 边上（出生点） | 东、南、东南 | 主 BonusObj08-BringDownTeslaCoils 东 2456（0/5 已知） |
| P8 + 31 秒 + L + L | 大块揭图 RevealWP-NavalYard | 0 | 82% / 95% | 边上（出生点） | 东、东北、南、东南 | 主 BonusObj08-BringDownTeslaCoils 东 2456（5/5 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Obj01-DestroyCoastalGuns | 开局 + 19 秒 + L | 领着看（镜头） |
| 主 Obj02-DestroyStatues | P1 + 3 秒 + L | 标记在未知区域 |
| 奖励 BonusObj01-CaptureBarracks | P3 + 4 秒 | 走近才触发 |
| 奖励 BonusObj09-CaptureHospital | P10 + 0 秒 | 走近才触发 |
| 主 BonusObj08-BringDownTeslaCoils | P8 + 1 秒 + L + L | 标记在未知区域 |

锚点：P1 = Struct_P4Powerplant 被毁 且 Struct_P7Powerplant 被毁（开局 + 19 秒 + L 起）；P3 = Struct_Statue01 被毁（P1 + 0 秒 起）；P4 = Struct_Statue01 被 Player_1 攻击（P1 + 0 秒 起）；P8 = Struct_Statue01 被毁 且 Struct_Statue02 被毁 且 Struct_Statue03 被毁 且 Struct_Statue04 被毁（P1 + 3 秒 + L 起）；P10 = Player_1 的单位在 AT-Hospital（P1 + 3 秒 + L 起）

### 帝2 斯大林格勒（camp_j02_stalingrad_stewart）

- 交还控制：开局 + 7 秒；开场镜头 1 次、指过 1 处。敌人第一次露面：P12 + 6 秒（TEAM_HUNT Soviet_01/Choppers_Preplaced，玩家推进，东）。开局预摆的敌方机动单位：定时出动 1、等玩家触发 6、脚本从不调动 36。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 7 秒 | 交还控制 | 0 | 4% / 100% | 中间（出生点） | 东南 | — |
| 开局 + 11.5 秒 + L + L | 亮目标 Objective_1_Beachhead | 0 | 4% / 100% | 中间（出生点） | 东南 | 主 Objective_1_Beachhead 东 2715（0/2 已知） |
| P13 + 15 秒 + L | 亮目标 Objective_2_Statue | 0 | 8% / 100% | 边上（出生点） | 东、东南 | 主 Objective_1_Beachhead 东 2715（0/2 已知）；主 Objective_2_Statue 北 3929（0/1 已知，揭图、镜头、闪烁） |
| P13 + 21 秒 + L | 亮目标 Bonus_Kill_Monuments | 0 | 8% / 100% | 边上（出生点） | 东、东南 | 奖 Bonus_Kill_Monuments 北 3795（1/8 已知）；主 Objective_1_Beachhead 东 2715（0/2 已知）；主 Objective_2_Statue 北 3929（0/1 已知，揭图、镜头、闪烁） |
| P15 + 7 秒 | 亮目标 Objective_3_Transports | 0 | 28% / 100% | 角落（出生点） | 东、东北、北、西北、西南、东南 | 主 Objective_1_Beachhead 东 2715（0/2 已知）；主 Objective_2_Statue 北 3929（1/1 已知，揭图、镜头、闪烁）；主 Objective_3_Transports 东北 2566（7/7 已知，揭图） |
| P15 + 7 秒 | 大块揭图 area_reveal_river | 0 | 28% / 100% | 角落（出生点） | 东、东北、北、西北、西南、东南 | 主 Objective_1_Beachhead 东 2715（0/2 已知）；主 Objective_2_Statue 北 3929（1/1 已知，揭图、镜头、闪烁）；主 Objective_3_Transports 东北 2566（7/7 已知，揭图） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective_1_Beachhead | 开局 + 11.5 秒 + L + L | 标记在未知区域 |
| 主 Objective_2_Statue | P13 + 15 秒 + L | 领着看（揭图、镜头、闪烁） |
| 奖励 Bonus_Kill_Monuments | P13 + 21 秒 + L | 走近才触发 |
| 主 Objective_3_Transports | P15 + 7 秒 | 领着看（揭图） |

锚点：P12 = Player_1 的单位在 area_advance_choppers（开局 + 0 秒 起）；P13 = Player_2 的 japanconstructionyard 数量 且 Player_2 的单位在 area_water_area（开局 + 11.5 秒 + L + L 起）；P15 = o_obj_2_statue 被毁（P13 + 15 秒 + L 起）

### 帝3 敖德萨（camp_j03_odessa_stewart）

- 交还控制：开局 + 6 秒；开场镜头 1 次、指过 1 处。敌人第一次露面：≈开局 + 31.8 秒（MOVE_NAMED_UNIT_TO o_sub_a，计时，南）。开局预摆的敌方机动单位：定时出动 5、等玩家触发 13、脚本从不调动 0。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 6 秒 | 交还控制 | 1 | 24% / 24% | 边上（出生点） | 西北、西 | — |
| 开局 + 8.5 秒 + L | 亮目标 Objective_1_Escort_Parts | 1 | 24% / 24% | 边上（出生点） | 西北、西 | 主 Objective_1_Escort_Parts 东北 520（3/3 已知，镜头、闪烁） |
| P1 + 8.1 秒 | 换边界 0 | 0 | 12% / 12% | 边上（spawn in mechaking（1 处）） | 东北、北 | — |
| P1 + 28.6 秒 | 亮目标 Objective_2_Destroy_Artillery | 0 | 12% / 12% | 边上（spawn in mechaking（1 处）） | 东北、北 | 主 Objective_2_Destroy_Artillery 东北 3155（0/4 已知） |
| P1 + 34.6 秒 | 亮目标 Bonus_Culture_Killer | 0 | 12% / 12% | 边上（spawn in mechaking（1 处）） | 东北、北 | 奖 Bonus_Culture_Killer 北 2831（0/3 已知）；主 Objective_2_Destroy_Artillery 东北 3155（0/4 已知） |
| P1 + 36.6 秒 + L + L | 亮目标 Objective_3_Destroy_Krukov | 0 | 12% / 12% | 边上（spawn in mechaking（1 处）） | 东北、北 | 奖 Bonus_Culture_Killer 北 2831（0/3 已知）；主 Objective_2_Destroy_Artillery 东北 3155（0/4 已知）；主 Objective_3_Destroy_Krukov 东北 5542（0/7 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective_1_Escort_Parts | 开局 + 8.5 秒 + L | 领着看（镜头、闪烁） |
| 主 Objective_2_Destroy_Artillery | P1 + 28.6 秒 | 标记在未知区域 |
| 奖励 Bonus_Culture_Killer | P1 + 34.6 秒 | 标记在未知区域 |
| 主 Objective_3_Destroy_Krukov | P1 + 36.6 秒 + L + L | 标记在未知区域 |

锚点：P1 = o_debug_skip_obj2 被毁（开局 + 0 秒 起）

### 帝4 珍珠港（camp_j04_pearlharbor_davis）

- 交还控制：开局 + 19.5 秒；开场镜头 5 次、指过 4 处。敌人第一次露面：P5 + 0 秒（TEAM_AI_TRANSFER teamAllied01，玩家推进，东北）。开局预摆的敌方机动单位：定时出动 19、等玩家触发 8、脚本从不调动 24。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 19.5 秒 | 交还控制 | 0 | 28% / 41% | 角落（出生点） | 东北 | — |
| 开局 + 24.5 秒 | 亮目标 J04_Objective_3 | 0 | 28% / 41% | 角落（出生点） | 东北 | 主 J04_Objective_3 东北 2189（5/5 已知） |
| 开局 + 54.5 秒 | 亮目标 J04_Objective_B3 | 0 | 28% / 41% | 角落（出生点） | 东北 | 主 J04_Objective_3 东北 2189（5/5 已知）；奖 J04_Objective_B3 东北 2562（0/3 已知） |
| ≈P22 + 0 秒 | 大块揭图 Area - Bonus Objective 1 Reveal | 0 | 95% / 95% | 角落（出生点） | 东北 | 主 J04_Objective_3 东北 2189（5/5 已知） |
| 开局 + 836.5 秒 | 亮目标 J04_Objective_5 | 0 | 28% / 41% | 角落（出生点） | 东北 | 主 J04_Objective_5（无标记）；奖 J04_Objective_B3 东北 2562（0/3 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 J04_Objective_3 | 开局 + 24.5 秒 | 只有标记（在已知区域） |
| 奖励 J04_Objective_B3 | 开局 + 54.5 秒 | 标记在未知区域 |
| 主 J04_Objective_5 | 开局 + 836.5 秒 | 没有标记 |

锚点：P5 = Player_1 的单位在 Area - Turn On AI Sooner（开局 + 0 秒 起）；P22 = STRUCTURE - Objective_B1_3 拿到 Player_1（开局 + 54.5 秒 起）

### 帝5 深海（camp_j05_deepocean_davis）

- 交还控制：开局 + 21 秒；开场镜头 3 次、指过 3 处。敌人第一次露面：P13 + 0 秒（刷出 TEAM - Wave 3 - MCVs，玩家推进，东北）。开局预摆的敌方机动单位：定时出动 6、等玩家触发 0、脚本从不调动 30。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 21 秒 | 交还控制 | 1 | 100% / 100% | 边上（出生点） | 东 | — |
| 开局 + 25 秒 | 亮目标 J05_Objective_1 | 1 | 100% / 100% | 边上（出生点） | 东 | 主 J05_Objective_1（无标记） |
| ≈P7 + 18 秒 | 亮目标 J05_Objective_4 | 1 | 100% / 100% | 边上（出生点） | 东 | 主 J05_Objective_4 北 3630（0/2 已知） |
| ≈P7 + 24 秒 | 换边界 0 | 0 | 58% / 58% | 边上（出生点） | 东 | 主 J05_Objective_4 北 3630（2/2 已知） |
| ≈P7 + 33 秒 | 亮目标 J05_Objective_5 | 0 | 58% / 58% | 边上（出生点） | 东 | 主 J05_Objective_4 北 3630（2/2 已知）；主 J05_Objective_5（无标记） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 J05_Objective_1 | 开局 + 25 秒 | 没有标记 |
| 主 J05_Objective_4 | ≈P7 + 18 秒 | 走近才触发 |
| 主 J05_Objective_5 | ≈P7 + 33 秒 | 没有标记 |

锚点：P7 = STRUCTURE - Power Core 2 血量（开局 + 0 秒 起）；P13 = TEAM - Wave 2 - MCVs 全灭（开局 + 0 秒 起）

### 帝6 洛杉矶（camp_j06_losangeles_white）

- 交还控制：开局 + 10.5 秒；开场镜头 2 次、指过 2 处。敌人第一次露面：P1 + 0 秒（NAMED_HUNT Unit-MirageTank01，玩家推进，东）。开局预摆的敌方机动单位：定时出动 0、等玩家触发 11、脚本从不调动 7。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 10.5 秒 | 交还控制 | 3 | 24% / 24% | 边上（出生点） | — | — |
| 开局 + 13.5 秒 | 亮目标 Objective0-ClearBeach | 3 | 24% / 24% | 边上（出生点） | — | 主 Objective0-ClearBeach（无标记） |
| P4 + 4.4 秒 | 换边界 0 | 0 | 14% / 14% | 边上（出生点） | 东、东北 | — |
| P4 + 23 秒 + L | 亮目标 Objective01-CaptureMediaCenters | 0 | 14% / 14% | 边上（出生点） | 东、东北 | 主 Objective01-CaptureMediaCenters 东北 3256（0/3 已知） |
| P10 + L | 亮目标 BonObjective02-CaptureLAX | 0 | 17% / 17% | 角落（出生点） | 东、东北 | 奖 BonObjective02-CaptureLAX 东 3050（1/1 已知，雷达）；主 Objective01-CaptureMediaCenters 东北 3256（0/3 已知） |
| P11 + L | 亮目标 BonObjective03-DestroyGriffithObs | 0 | 17% / 17% | 角落（出生点） | 东、东北 | 奖 BonObjective03-DestroyGriffithObs 东北 4601（1/1 已知，雷达）；主 Objective01-CaptureMediaCenters 东北 3256（0/3 已知） |
| P12 + L | 亮目标 BonObjective05-DestroySantaMonicaPier | 0 | 17% / 17% | 边上（出生点） | 东、东北、北 | 奖 BonObjective05-DestroySantaMonicaPier 北 1494（1/1 已知，雷达）；主 Objective01-CaptureMediaCenters 东北 3256（0/3 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective0-ClearBeach | 开局 + 13.5 秒 | 没有标记 |
| 主 Objective01-CaptureMediaCenters | P4 + 23 秒 + L | 标记在未知区域 |
| 奖励 BonObjective02-CaptureLAX | P10 + L | 领着看（雷达） |
| 奖励 BonObjective03-DestroyGriffithObs | P11 + L | 领着看（雷达） |
| 奖励 BonObjective05-DestroySantaMonicaPier | P12 + L | 领着看（雷达） |

锚点：P1 = Player_1 的单位在 Area-MirageSneakAttack01（开局 + 0 秒 起）；P4 = Allies_07 的单位在 Area-P1Clear 且 Allies_07 的单位在 Area-P2Clear（开局 + 13.5 秒 起）；P10 = Player_1 发现 Struct_LAXControlTower（P4 + 23 秒 + L 起）；P11 = Player_1 发现 Struct_Observatory（P4 + 23 秒 + L 起）；P12 = Player_1 的单位在 AT-SMPier（P4 + 23 秒 + L 起）

### 帝7 横滨（camp_j07_yokohama_stewart）

- 交还控制：开局 + 26 秒；开场镜头 6 次、指过 3 处。敌人第一次露面：P8 + 0 秒（刷出 sovietconstructionyard，玩家推进，东北）。开局预摆的敌方机动单位：定时出动 6、等玩家触发 24、脚本从不调动 10。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 26 秒 | 交还控制 | 0 | 11% / 100% | 角落（出生点） | 东北 | — |
| 开局 + 28 秒 + L | 亮目标 J07_Objective_Capture_Outposts | 0 | 11% / 100% | 角落（出生点） | 东北 | 主 J07_Objective_Capture_Outposts 东北 1988（2/4 已知） |
| ≈P7 + 14 秒 + L + L | 亮目标 J07_Objective_Defend_Outposts | 0 | 14% / 100% | 角落（出生点） | 东北 | 主 J07_Objective_Defend_Outposts 东北 1988（3/4 已知） |
| P8 + 51 秒 | 亮目标 J07_Bonus_Destroy_Soviets | 0 | 11% / 100% | 角落（出生点） | 东、东北、北 | 奖 J07_Bonus_Destroy_Soviets（无标记） |
| P30 + 0 秒 | 亮目标 J07_Bonus_Save_Nanoswarm | 0 | 15% / 100% | 角落（player 1 captures outpost 1（1 ） | 东、东南 | 奖 J07_Bonus_Save_Nanoswarm 东南 1446（1/2 已知） |
| P31 + 13 秒 | 大块揭图 全图 | 0 | 100% / 100% | 边上（spawn mcv for player 1（1 处）） | 东、东北、东南 | — |
| P31 + 21 秒 | 亮目标 J07_Objective_Destroy_Relay_Stations | 0 | 16% / 100% | 边上（spawn mcv for player 1（1 处）） | 东 | 主 J07_Objective_Destroy_Relay_Stations 东北 4606（0/4 已知，揭图、镜头） |
| P31 + 922 秒 | 大块揭图 全图 | 0 | 100% / 100% | 边上（spawn mcv for player 1（1 处）） | 东、东北、东南 | 主 J07_Objective_Destroy_Relay_Stations 东北 4606（4/4 已知，揭图、镜头） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 J07_Objective_Capture_Outposts | 开局 + 28 秒 + L | 只有标记（在已知区域） |
| 主 J07_Objective_Defend_Outposts | ≈P7 + 14 秒 + L + L | 走近才触发 |
| 奖励 J07_Bonus_Destroy_Soviets | P8 + 51 秒 | 没有标记 |
| 奖励 J07_Bonus_Save_Nanoswarm | P30 + 0 秒 | 只有标记（在已知区域） |
| 主 J07_Objective_Destroy_Relay_Stations | P31 + 21 秒 | 领着看（揭图、镜头） |

锚点：P7 = op_01_hive 被毁（开局 + 0 秒 起）；P8 = Allies01 的 _object list_allied loss condition 数量（开局 + 0 秒 起）；P30 = 计数 c_capture_outposts_counter 到 0（P10 + 0 秒 起）；P31 = Allies01 的 _object list_allied loss condition 数量 且 Soviet01 的 _object list_soviet loss con（≈P7 + 14 秒 + L + L 起）

### 帝8 克里姆林宫（camp_j08_kremlin_stewart）

- 交还控制：开局 + 21 秒；开场镜头 4 次、指过 0 处。敌人第一次露面：开局 + 21 秒（开局就在视野里，开局，北、西北）。开局预摆的敌方机动单位：定时出动 9、等玩家触发 98、脚本从不调动 0。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 21 秒 | 交还控制 | 2 | 30% / 100% | 中间（cine transport garrison（2 处）） | 北、西北 | — |
| 开局 + 24 秒 + L | 亮目标 J08_Wait_For_MechaKing | 2 | 30% / 100% | 中间（cine transport garrison（2 处）） | 北、西北 | 主 J08_Wait_For_MechaKing 西南 218（2/2 已知） |
| 开局 + 30 秒 + L + L | 亮目标 J08_Capture_VIP_Bunkers | 2 | 30% / 100% | 中间（cine transport garrison（2 处）） | 北、西北 | 主 J08_Wait_For_MechaKing 西南 218（2/2 已知）；奖 J08_Capture_VIP_Bunkers 北 1531（0/1 已知） |
| P1 + 0 秒 | 换边界 1 | 0 | 11% / 100% | 中间（cine transport garrison（2 处）） | 东北、北、西北 | — |
| P1 + 0 秒 | 换边界 0 | 0 | 11% / 100% | 中间（cine transport garrison（2 处）） | 东北、北、西北 | — |
| P1 + 6 秒 | 亮目标 J08_MechaKing_Must_Live | 0 | 13% / 100% | 边上（cine transport garrison（2 处）） | 东北、北、西北 | 主 J08_MechaKing_Must_Live 东南 1436（0/1 已知，揭图、闪烁、雷达） |
| P1 + 7 秒 | 大块揭图 全图 | 0 | 100% / 100% | 边上（cine transport garrison（2 处）） | 东、东北、北、西北 | 主 J08_MechaKing_Must_Live 东南 1436（0/1 已知，揭图、闪烁、雷达） |
| P1 + 7 秒 + L | 亮目标 J08_Destroy_Time_Machine | 0 | 13% / 100% | 边上（cine transport garrison（2 处）） | 东、东北、北、西北 | 主 J08_Destroy_Time_Machine 北 5128（1/1 已知，揭图）；主 J08_MechaKing_Must_Live 东南 1436（0/1 已知，揭图、闪烁、雷达） |
| P1 + 20 秒 + L + L | 亮目标 J08_Destroy_Everything | 0 | 13% / 100% | 边上（cine transport garrison（2 处）） | 东、东北、北、西北 | 主 J08_Destroy_Everything 北 2753（1/15 已知）；主 J08_Destroy_Time_Machine 北 5128（1/1 已知，揭图）；主 J08_MechaKing_Must_Live 东南 1436（0/1 已知，揭图、闪烁、雷达） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 J08_Wait_For_MechaKing | 开局 + 24 秒 + L | 只有标记（在已知区域） |
| 奖励 J08_Capture_VIP_Bunkers | 开局 + 30 秒 + L + L | 标记在未知区域 |
| 主 J08_MechaKing_Must_Live | P1 + 6 秒 | 领着看（揭图、闪烁、雷达） |
| 主 J08_Destroy_Time_Machine | P1 + 7 秒 + L | 领着看（揭图） |
| 主 J08_Destroy_Everything | P1 + 20 秒 + L + L | 只有标记（在已知区域） |

锚点：P1 = Soviet01 的 _object list_soviet production 数量（开局 + 0 秒 起）

### 帝9 阿姆斯特丹（camp_j09_amsterdam_bass）

- 交还控制：开局 + 25.7 秒；开场镜头 4 次、指过 4 处。敌人第一次露面：开局 + 25.7 秒（开局就在视野里，开局，东、东北、北）。开局预摆的敌方机动单位：定时出动 45、等玩家触发 91、脚本从不调动 0。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 25.7 秒 | 交还控制 | 2 | 8% / 100% | 边上（出生点） | 东、东北、北 | — |
| 开局 + 28.7 秒 | 亮目标 Objective 0 - Clear Base Area | 2 | 8% / 100% | 边上（出生点） | 东、东北、北 | 主 Objective 0 - Clear Base Area 东 595（3/4 已知） |
| ≈P7 + 8 秒 | 大块揭图 全图 | 2 | 100% / 100% | 角落（出生点） | 东、东北、北 | — |
| P8 + L | 大块揭图 全图 | 2 | 100% / 100% | 角落（出生点） | 东、东北、北 | — |
| P15 + 5 秒 | 大块揭图 全图 | 2 | 100% / 100% | 角落（出生点） | 东、东北、北 | — |
| P15 + 9.3 秒 + L | 亮目标 Objective 1 - Allied Air Base | 2 | 9% / 100% | 边上（出生点） | 东、东北、北 | 主 Objective 1 - Allied Air Base 东北 1737（0/3 已知，揭图、镜头） |
| P8 + 28.2 秒 + L | 换边界 3 | 3 | 100% / 100% | 图外（出生点） | 东、东北、北 | — |
| P8 + 28.3 秒 + L | 亮目标 Objective 3 - FutureTech HQ | 3 | 100% / 100% | 图外（出生点） | 东、东北、北 | 主 Objective 3 - FutureTech HQ 东北 5615（1/1 已知，镜头） |
| P15 + 14.3 秒 + L | 亮目标 Objective 2 - Allied Main Base | 2 | 9% / 100% | 边上（出生点） | 东、东北、北 | 主 Objective 1 - Allied Air Base 东北 1737（0/3 已知，揭图、镜头）；主 Objective 2 - Allied Main Base 东北 4464（0/1 已知，揭图） |
| P15 + 121.3 秒 + L | 亮目标 Bonus Objective 1 - Particle Cannons | 2 | 9% / 100% | 边上（出生点） | 东、东北、北 | 主 Objective 1 - Allied Air Base 东北 1737（0/3 已知，揭图、镜头）；主 Objective 2 - Allied Main Base 东北 4464（0/1 已知，揭图）；主 Objective 3 - FutureTech HQ 东北 5615（0/1 已知，镜头）；奖 Bonus Objective 1 - Particle Cannons 东北 3747（0/4 已知，揭图） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective 0 - Clear Base Area | 开局 + 28.7 秒 | 只有标记（在已知区域） |
| 主 Objective 1 - Allied Air Base | P15 + 9.3 秒 + L | 领着看（揭图、镜头） |
| 主 Objective 3 - FutureTech HQ | P8 + 28.3 秒 + L | 领着看（镜头） |
| 主 Objective 2 - Allied Main Base | P15 + 14.3 秒 + L | 领着看（揭图） |
| 奖励 Bonus Objective 1 - Particle Cannons | P15 + 121.3 秒 + L | 领着看（揭图） |

锚点：P7 = Allied02 的 _object list_allied loss condition 数量（开局 + 0 秒 起）；P8 = STRUC_Civ - FutureTech HQ - A 1 血量（开局 + 0 秒 起）；P15 = Allied01 的单位在 TRIG_N - Intro - P1 - Base Area（开局 + 18.1 秒 起）

### 苏1 列宁格勒运河（camp_s01_leningradcanals_rao）

- 交还控制：开局 + 14 秒；开场镜头 3 次、指过 2 处。敌人第一次露面：开局 + 14 秒（开局就在视野里，开局，东、东北、北、西南）。开局预摆的敌方机动单位：定时出动 30、等玩家触发 28、脚本从不调动 103。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 14 秒 | 交还控制 | 0 | 100% / 100% | 角落（出生点） | 东、东北、北、西南 | — |
| 开局 + 7 秒 + L | 亮目标 S01_Objective_01 | 0 | 100% / 100% | 角落（出生点） | 东、东北、北、西南 | 主 S01_Objective_01 东北 2166（1/1 已知，揭图、镜头） |
| 开局 + 23 秒 | 亮目标 S01_Objective_1B | 0 | 100% / 100% | 中间（Objective 1b - Reveal (CAMERA)） | 西北、西、西南、南、东南 | 主 S01_Objective_01 西 409（1/1 已知，揭图、镜头）；主 S01_Objective_1B 东 0（1/1 已知，镜头） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 S01_Objective_01 | 开局 + 7 秒 + L | 领着看（揭图、镜头） |
| 主 S01_Objective_1B | 开局 + 23 秒 | 领着看（镜头） |

### 苏2 克拉斯纳 45（camp_s02_krasna45_rao）

- 交还控制：开局 + 12 秒；开场镜头 4 次、指过 0 处。敌人第一次露面：P2 + 0 秒（MOVE_TEAM_TO TEAM - Tengus 01，玩家推进，东北）。开局预摆的敌方机动单位：定时出动 23、等玩家触发 41、脚本从不调动 47。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 12 秒 | 交还控制 | 0 | 0% / 0% | ?（出生点） | 东、东北、北、南 | — |
| 开局 + 38 秒 | 亮目标 S02_Objective_1 | 0 | 2% / 2% | 图外（出生点） | 东、东北、北、南 | 主 S02_Objective_1 东 2732（0/1 已知） |
| P4 + 0 秒 | 亮目标 S02_BonusObjective_1 | 0 | 6% / 6% | 图外（出生点） | 东、东北、北、南 | 奖 S02_BonusObjective_1 东 1443（1/1 已知） |
| P5 + 0 秒 | 亮目标 S02_BonusObjective_2 | 0 | 6% / 6% | 图外（出生点） | 东、东北、北、南 | 奖 S02_BonusObjective_2 北 1166（1/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 S02_Objective_1 | 开局 + 38 秒 | 标记在未知区域 |
| 奖励 S02_BonusObjective_1 | P4 + 0 秒 | 走近才触发 |
| 奖励 S02_BonusObjective_2 | P5 + 0 秒 | 走近才触发 |

锚点：P2 = Player_1 的单位在 AREA - Mecha - Fly In（开局 + 0 秒 起）；P4 = Player_1 的单位在 AREA - Bonus 01 - Reveal（开局 + 0 秒 起）；P5 = Player_1 的单位在 AREA - Bonus 02 - Reveal（开局 + 0 秒 起）

### 苏3 海参崴（camp_s03_vladivostok_davis）

- 交还控制：开局 + 13.2 秒 + L；开场镜头 3 次、指过 3 处。敌人第一次露面：P19 + 0 秒（MOVE_TEAM_TO TEAM - Infantry Guards 1，玩家推进，东北）。开局预摆的敌方机动单位：定时出动 2、等玩家触发 23、脚本从不调动 75。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 26 秒 | 亮目标 S03_Objective_4 | 1 | 9% / 39% | 中间（Soviet01 - P1 - Initial Forces） | 东北 | 主 S03_Objective_4 东北 6122（0/1 已知） |
| 开局 + 13.2 秒 + L | 交还控制 | 1 | 9% / 39% | 中间（Soviet01 - P1 - Initial Forces） | 东北 | 主 S03_Objective_1 东北 1790（0/2 已知）；主 S03_Objective_4 东北 6122（0/1 已知） |
| 开局 + 13.2 秒 + L | 亮目标 S03_Objective_1 | 1 | 9% / 39% | 中间（Soviet01 - P1 - Initial Forces） | 东北 | 主 S03_Objective_1 东北 1790（0/2 已知）；主 S03_Objective_4 东北 6122（0/1 已知） |
| P16 + 3 秒 | 亮目标 S03_Objective_Bonus_2 | 1 | 9% / 39% | 中间（Soviet01 - P1 - Initial Forces） | 东北 | 主 S03_Objective_1 东北 1790（0/2 已知）；主 S03_Objective_4 东北 6122（0/1 已知）；奖 S03_Objective_Bonus_2（无标记） |
| P3 + 13 秒 | 亮目标 S03_Objective_2 | 1 | 22% / 40% | 角落（Soviet01 - P1 - Initial Forces） | 东北 | 主 S03_Objective_2 东北 1537（2/6 已知，镜头）；主 S03_Objective_4 东北 6122（0/1 已知） |
| P17 + 23 秒 | 亮目标 S03_Objective_Bonus_3 | 1 | 9% / 39% | 中间（Soviet01 - P1 - Initial Forces） | 东北 | 主 S03_Objective_1 东北 1790（0/2 已知）；主 S03_Objective_4 东北 6122（0/1 已知）；奖 S03_Objective_Bonus_3 东北 2126（0/2 已知） |
| ≈P7 + 18 秒 + L | 换边界 0 | 0 | 2% / 10% | 中间（Soviet01 - P1 - Initial Forces） | 东北 | 主 S03_Objective_1 东北 1790（0/2 已知）；主 S03_Objective_4 东北 6122（0/1 已知） |
| ≈P7 + 27 秒 + L | 亮目标 S03_Objective_3a | 0 | 2% / 10% | 中间（Soviet01 - P1 - Initial Forces） | 东北 | 主 S03_Objective_1 东北 1790（0/2 已知）；主 S03_Objective_3a 东北 4427（0/1 已知）；主 S03_Objective_4 东北 6122（0/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 S03_Objective_4 | 开局 + 26 秒 | 标记在未知区域 |
| 主 S03_Objective_1 | 开局 + 13.2 秒 + L | 标记在未知区域 |
| 奖励 S03_Objective_Bonus_2 | P16 + 3 秒 | 走近才触发 |
| 主 S03_Objective_2 | P3 + 13 秒 | 领着看（镜头） |
| 奖励 S03_Objective_Bonus_3 | P17 + 23 秒 | 标记在未知区域 |
| 主 S03_Objective_3a | ≈P7 + 27 秒 + L | 标记在未知区域 |

锚点：P3 = STRUCT - Japan04 - Base Defense 1 被毁 且 STRUCT - Japan04 - Base Defense 2 被毁 且 STRUCT - Jap（开局 + 0 秒 起）；P7 = Player_2 的 sovietbarracks 数量（开局 + 0 秒 起）；P16 = Player_1 的单位在 Area - Japan03 - Bonus Objective 2 Reveal（开局 + 0 秒 起）；P17 = Player_1 的 sovietrefinery 数量（开局 + 0 秒 起）；P19 = Player_1 发现 TEAM - Infantry Guards 1（开局 + 0 秒 起）

### 苏4 日内瓦（camp_s04_geneva_bass）

- 交还控制：开局 + 20.4 秒；开场镜头 6 次、指过 6 处。敌人第一次露面：开局 + 30 秒（UNIT_AI_TRANSFER_ALL Allied_02，计时，东）。开局预摆的敌方机动单位：定时出动 22、等玩家触发 24、脚本从不调动 51。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 20.4 秒 | 交还控制 | 1 | 20% / 100% | 中间（出生点） | 东、东北、东南 | — |
| 开局 + 21.7 秒 + L | 亮目标 Objective 1 - Destroy Allied Supply Port | 1 | 20% / 100% | 中间（出生点） | 东、东北、东南 | 主 Objective 1 - Destroy Allied Supply Port 东 2720（0/1 已知，雷达） |
| 开局 + 26.7 秒 + L | 亮目标 Objective 2 - Destroy Allied Army Base | 1 | 20% / 100% | 中间（出生点） | 东、东北、东南 | 主 Objective 1 - Destroy Allied Supply Port 东 2720（0/1 已知，雷达）；主 Objective 2 - Destroy Allied Army Base 东南 3248（0/3 已知，雷达） |
| 开局 + 31.7 秒 + L | 亮目标 Bonus Objective 1 - Capture Banks | 1 | 20% / 100% | 中间（出生点） | 东、东北、东南 | 主 Objective 1 - Destroy Allied Supply Port 东 2720（0/1 已知，雷达）；主 Objective 2 - Destroy Allied Army Base 东南 3248（0/3 已知，雷达）；奖 Bonus Objective 1 - Capture Banks 东 1687（0/6 已知，雷达） |
| ≈P7 + 4 秒 + L | 换边界 0 | 0 | 100% / 100% | 边上（_Sub-Mission Split - Setup（1 处） | 东北、北 | — |
| ≈P7 + 4 秒 + L | 大块揭图 全图 | 0 | 100% / 100% | 边上（_Sub-Mission Split - Setup（1 处） | 东北、北 | — |
| ≈P7 + 4 秒 + L | 大块揭图 WP - S2 - AI Base | 0 | 100% / 100% | 边上（_Sub-Mission Split - Setup（1 处） | 东北、北 | — |
| ≈P7 + 17.1 秒 + L | 亮目标 Objective 3 - Destroy Allied Command HQ | 0 | 24% / 100% | 边上（_Sub-Mission Split - Setup（1 处） | 东北、北 | 主 Objective 3 - Destroy Allied Command HQ（无标记） |
| ≈P7 + 25.1 秒 + L | 亮目标 Objective 4 - Defend Krukov's HQ | 0 | 24% / 100% | 边上（_Sub-Mission Split - Setup（1 处） | 东北、北 | 主 Objective 3 - Destroy Allied Command HQ（无标记）；主 Objective 4 - Defend Krukov's HQ 东 1616（1/1 已知，雷达） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective 1 - Destroy Allied Supply Port | 开局 + 21.7 秒 + L | 领着看（雷达） |
| 主 Objective 2 - Destroy Allied Army Base | 开局 + 26.7 秒 + L | 领着看（雷达） |
| 奖励 Bonus Objective 1 - Capture Banks | 开局 + 31.7 秒 + L | 领着看（雷达） |
| 主 Objective 3 - Destroy Allied Command HQ | ≈P7 + 17.1 秒 + L | 没有标记 |
| 主 Objective 4 - Defend Krukov's HQ | ≈P7 + 25.1 秒 + L | 领着看（雷达） |

锚点：P7 = STRUC - A1 - Supply Port 被毁（开局 + 0 秒 起）

### 苏5 米科诺斯（camp_s05_mykonos_smith）

- 交还控制：开局 + 22 秒 + L；开场镜头 5 次、指过 4 处。敌人第一次露面：P9 + 0 秒（UNIT_AI_TRANSFER_ALL Allied04，玩家推进，东北）。开局预摆的敌方机动单位：定时出动 0、等玩家触发 5、脚本从不调动 42。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 22 秒 + L | 交还控制 | 1 | 15% / 100% | 边上（出生点） | — | — |
| 开局 + 25 秒 + L | 亮目标 Objective_1 | 1 | 15% / 100% | 边上（出生点） | — | 主 Objective_1 北 2091（0/2 已知） |
| 开局 + 33 秒 + L | 亮目标 Bonus Objective 01 | 1 | 15% / 100% | 边上（出生点） | — | 主 Objective_1 北 2091（0/2 已知）；奖 Bonus Objective 01 东 2358（0/1 已知） |
| P4 + 0 秒 | 亮目标 Objective_3 | 1 | 19% / 100% | 边上（出生点） | 东北 | 主 Objective_3 东北 3253（3/5 已知） |
| P6 + 0 秒 | 亮目标 Objective_4 | 1 | 19% / 100% | 边上（出生点） | — | 主 Objective_4 东北 4196（0/1 已知） |
| ≈P5 + 8 秒 + L | 换边界 0 | 0 | 13% / 100% | 边上（出生点） | 东北 | — |
| ≈P5 + 12 秒 + L | 大块揭图 全图 | 0 | 100% / 100% | 角落（出生点） | 东、东北、北 | — |
| ≈P5 + 40 秒 + L | 亮目标 Objective_5_MEDIUM | 0 | 13% / 100% | 边上（出生点） | 东北 | 主 Objective_5_MEDIUM 东北 4196（0/1 已知，镜头） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective_1 | 开局 + 25 秒 + L | 标记在未知区域 |
| 奖励 Bonus Objective 01 | 开局 + 33 秒 + L | 标记在未知区域 |
| 主 Objective_3 | P4 + 0 秒 | 走近才触发 |
| 主 Objective_4 | P6 + 0 秒 | 走近才触发 |
| 主 Objective_5_MEDIUM | ≈P5 + 40 秒 + L | 领着看（镜头） |

锚点：P4 = UNIT - Allied 03 Barracks 被 <1st Human Player's Allies incl Self> 攻击（开局 + 0 秒 起）；P5 = UNIT - Allied 03 Barracks 被毁 且 UNIT - Allied 03 Conyard 被毁 且 UNIT - Allied 03 Naval Yard 0（开局 + 0 秒 起）；P6 = <1st Human Player's Allies incl Self> 的单位在 AREA - Tech Lab（开局 + 0 秒 起）；P9 = SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER(Allied03, Player_1)（开局 + 0 秒 起）

### 苏6 冰岛（camp_s06_iceland_bass）

- 交还控制：开局 + 19.2 秒；开场镜头 5 次、指过 4 处。敌人第一次露面：P5 + 20 秒（UNIT_AI_TRANSFER_ALL Allied03，玩家推进，东北）。开局预摆的敌方机动单位：定时出动 8、等玩家触发 0、脚本从不调动 20。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 19.2 秒 | 交还控制 | 1 | 25% / 100% | 中间（出生点） | 东、东北、西北、西 | — |
| P1 + 0 秒 | 换边界 2 | 2 | 20% / 100% | 中间（出生点） | 东、东北、西北、西 | — |
| P1 + 11 秒 | 大块揭图 全图 | 2 | 100% / 100% | 中间（出生点） | 东、东北、西北、西 | — |
| P6 + 1 秒 + L | 亮目标 Obj_1 - Sub Bases | 1 | 25% / 100% | 中间（出生点） | 东、东北、西北、西 | 主 Obj_1 - Sub Bases 北 1022（0/2 已知，雷达） |
| ≈P1 + 28.3 秒 + L | 换边界 0 | 0 | 100% / 100% | 中间（出生点） | 东、东北、北、西北、西 | — |
| ≈P1 + 28.3 秒 + L | 大块揭图 全图 | 0 | 100% / 100% | 中间（出生点） | 东、东北、北、西北、西 | — |
| P1 + 23.3 秒 + L + L | 亮目标 Obj_2 - Krukov | 0 | 14% / 100% | 中间（出生点） | 东、东北、西北、西 | 主 Obj_2 - Krukov 东南 2137（0/2 已知，揭图、雷达） |
| ≈P1 + 42.7 秒 + L | 亮目标 Obj_3 - Main Base | 0 | 14% / 100% | 中间（出生点） | 东、东北、西北、西 | 主 Obj_2 - Krukov 东南 2137（0/2 已知，揭图、雷达）；主 Obj_3 - Main Base（无标记） |
| P7 + 30 秒 | 亮目标 BonusObj_1 - Expansion | 2 | 20% / 100% | 中间（出生点） | 东、东北、西北、西 | 奖 BonusObj_1 - Expansion（无标记） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Obj_1 - Sub Bases | P6 + 1 秒 + L | 领着看（雷达） |
| 主 Obj_2 - Krukov | P1 + 23.3 秒 + L + L | 领着看（揭图、雷达） |
| 主 Obj_3 - Main Base | ≈P1 + 42.7 秒 + L | 没有标记 |
| 奖励 BonusObj_1 - Expansion | P7 + 30 秒 | 没有标记 |

锚点：P1 = STRUC - Allied01 - Sub Base E - Conyard 被毁 且 STRUC - Allied01 - Sub Base W - Conyard 被毁（开局 + 0 秒 起）；P5 = SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER(Allied03, Player_1)（开局 + 0 秒 起）；P6 = CURRENT_PLATFORM(PC)（开局 + 19.2 秒 起）；P7 = SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER(SovietKrukov, Player_1)（P1 + 17.3 秒 + L 起）

### 苏7 富士山（camp_s07_mountfuji_white）

- 交还控制：开局 + 24 秒 + L；开场镜头 2 次、指过 2 处。敌人第一次露面：开局 + 24 秒 + L（开局就在视野里，开局，东、东北、北、东南）。开局预摆的敌方机动单位：定时出动 14、等玩家触发 99、脚本从不调动 55。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 24 秒 + L | 交还控制 | 2 | 100% / 100% | 边上（出生点） | 东、东北、北、东南 | 主 Objective 01-Assassinate the Emperor 东 2095（1/1 已知，雷达） |
| 开局 + 24 秒 + L | 亮目标 Objective 01-Assassinate the Emperor | 2 | 100% / 100% | 边上（出生点） | 东、东北、北、东南 | 主 Objective 01-Assassinate the Emperor 东 2095（1/1 已知，雷达） |
| P2 + L | 亮目标 Objective 02-Create Diversion | 2 | 100% / 100% | 边上（出生点） | 东、东北、北、东南 | 主 Objective 02-Create Diversion 东 3227（1/1 已知，雷达） |
| P1 + 14 秒 + L | 换边界 3 | 3 | 12% / 100% | 边上（SplitDone-OnToObj03AfterSave（1） | 东北、北 | — |
| P1 + 30 秒 + L | 亮目标 Objective 03-Defeat Shinzo | 3 | 13% / 100% | 边上（SplitDone-OnToObj03AfterSave（1） | 东北、北 | 主 Objective 03-Defeat Shinzo 北 2543（0/2 已知，雷达） |
| P9 + 10 秒 | 换边界 0 | 0 | 12% / 100% | 边上（SplitDone-OnToObj03AfterSave（1） | 东北、北 | — |
| P9 + 12 秒 | 亮目标 Objective 06-Destroy Emperor's Palace | 0 | 12% / 100% | 边上（SplitDone-OnToObj03AfterSave（1） | 东北、北 | 主 Objective 06-Destroy Emperor's Palace 北 4853（0/1 已知，雷达） |
| P9 + 42 秒 | 亮目标 Bonus 01-Destroy Powerplants | 0 | 12% / 100% | 边上（SplitDone-OnToObj03AfterSave（1） | 东北、北 | 奖 Bonus 01-Destroy Powerplants 东北 6048（0/3 已知）；奖 Bonus 02-RescueConscript 北 4716（0/1 已知）；主 Objective 06-Destroy Emperor's Palace 北 4853（0/1 已知，雷达） |
| P9 + 42 秒 | 亮目标 Bonus 02-RescueConscript | 0 | 12% / 100% | 边上（SplitDone-OnToObj03AfterSave（1） | 东北、北 | 奖 Bonus 01-Destroy Powerplants 东北 6048（0/3 已知）；奖 Bonus 02-RescueConscript 北 4716（0/1 已知）；主 Objective 06-Destroy Emperor's Palace 北 4853（0/1 已知，雷达） |
| P10 + 1 秒 | 大块揭图 SpawnWP-EmperorMecha | 0 | 23% / 100% | 边上（SplitDone-OnToObj03AfterSave（1） | 东北、北 | — |
| P10 + 6 秒 + L | 亮目标 Objective 07-Kill Emperor | 0 | 15% / 100% | 边上（SplitDone-OnToObj03AfterSave（1） | 东北、北 | 主 Objective 07-Kill Emperor 北 4823（1/1 已知，揭图、镜头、雷达） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective 01-Assassinate the Emperor | 开局 + 24 秒 + L | 领着看（雷达） |
| 主 Objective 02-Create Diversion | P2 + L | 领着看（雷达） |
| 主 Objective 03-Defeat Shinzo | P1 + 30 秒 + L | 领着看（雷达） |
| 主 Objective 06-Destroy Emperor's Palace | P9 + 12 秒 | 领着看（雷达） |
| 奖励 Bonus 01-Destroy Powerplants | P9 + 42 秒 | 标记在未知区域 |
| 奖励 Bonus 02-RescueConscript | P9 + 42 秒 | 标记在未知区域 |
| 主 Objective 07-Kill Emperor | P10 + 6 秒 + L | 领着看（揭图、镜头、雷达） |

锚点：P1 = EmperorPrime 被毁（开局 + 24 秒 + L 起）；P2 = Player_1 的单位在 AT-P1Area02（开局 + 24 秒 + L 起）；P9 = 计数 Count-JapaneseDefeated 到 3（P7 + L 起）；P10 = Struct_EmperorsPalace 被毁（P9 + 12 秒 起）

### 苏8 复活节岛（camp_s08_easterisland_stewart）

- 交还控制：开局 + 4 秒；开场镜头 0 次、指过 0 处。敌人第一次露面：P2 + 0 秒（TEAM_HUNT Allies01/Allied_Emissary，玩家推进，方向未知）。开局预摆的敌方机动单位：定时出动 1、等玩家触发 1、脚本从不调动 21。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 4 秒 | 交还控制 | 2 | 15% / 15% | 角落（出生点） | — | — |
| 开局 + 7 秒 + L | 亮目标 S08_Ambush_Emissary | 2 | 15% / 15% | 角落（出生点） | — | 主 S08_Ambush_Emissary 东 933（0/2 已知） |
| P2 + 0 秒 | 亮目标 S08_Destroy_Emissary | 2 | 15% / 15% | 角落（出生点） | 东、北 | 主 S08_Destroy_Emissary 东 2693（0/1 已知，闪烁、雷达） |
| 开局 + 313 秒 + L | 换边界 1 | 1 | 100% / 100% | 中间（出生点） | 东、西、西南、东南 | 主 S08_Ambush_Emissary 东 2693（1/1 已知） |
| 开局 + 313 秒 + L | 大块揭图 全图 | 1 | 100% / 100% | 中间（出生点） | 东、西、西南、东南 | 主 S08_Ambush_Emissary 东 2693（1/1 已知） |
| 开局 + 322 秒 + L | 亮目标 S08_Defeat_Allied_Forces | 1 | 9% / 100% | 角落（出生点） | 东、西、西南、东南 | 主 S08_Ambush_Emissary 东 2693（0/1 已知）；主 S08_Defeat_Allied_Forces（无标记） |
| P4 + 8 秒 | 换边界 0 | 0 | 13% / 100% | 边上（出生点） | 东、北、西、西南、东南 | 主 S08_Ambush_Emissary 东 2693（0/1 已知） |
| P4 + 8 秒 | 大块揭图 wp_reveal_volcano | 0 | 13% / 100% | 边上（出生点） | 东、北、西、西南、东南 | 主 S08_Ambush_Emissary 东 2693（0/1 已知） |
| P4 + 9 秒 | 大块揭图 全图 | 0 | 100% / 100% | 边上（出生点） | 东、东北、北、西北、西、西南、东南 | 主 S08_Ambush_Emissary 东 2693（1/1 已知） |
| P4 + 28.1 秒 | 亮目标 S08_Destroy_Superweapon | 0 | 13% / 100% | 边上（出生点） | 东、北、西、西南、东南 | 主 S08_Ambush_Emissary 东 2693（0/1 已知）；主 S08_Destroy_Superweapon 北 4425（0/1 已知） |
| P6 + 6 秒 | 亮目标 S08_Defeat_the_Premiere | 0 | 16% / 100% | 边上（出生点） | 东、北、西、西南、东南 | 主 S08_Ambush_Emissary 东 2693（0/1 已知）；主 S08_Defeat_the_Premiere 北 4129（3/3 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 S08_Ambush_Emissary | 开局 + 7 秒 + L | 标记在未知区域 |
| 主 S08_Destroy_Emissary | P2 + 0 秒 | 领着看（闪烁、雷达） |
| 主 S08_Defeat_Allied_Forces | 开局 + 322 秒 + L | 没有标记 |
| 主 S08_Destroy_Superweapon | P4 + 28.1 秒 | 标记在未知区域 |
| 主 S08_Defeat_the_Premiere | P6 + 6 秒 | 只有标记（在已知区域） |

锚点：P2 = SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER(Allies01, Player_1)（开局 + 0 秒 起）；P4 = Allies02 的 _object list_allied all structs 数量（开局 + 326 秒 + L 起）；P6 = o_vacuumbomb 被毁（P4 + 28.1 秒 起）

### 苏9 纽约（camp_s09_newyork_rao）

- 交还控制：开局 + 0.5 秒 + L；开场镜头 2 次、指过 1 处。敌人第一次露面：开局 + 0.5 秒 + L（开局就在视野里，开局，东、东北、北、西、西南、南、东南）。开局预摆的敌方机动单位：定时出动 24、等玩家触发 1、脚本从不调动 134。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 15.1 秒 | 亮目标 Objective_1 | 1 | 9% / 100% | 边上（Introduction - End（1 处）） | 东、东北、北、西、西南、南、东南 | 主 Objective_1 东北 1270（0/3 已知） |
| 开局 + 0.5 秒 + L | 交还控制 | 1 | 9% / 100% | 边上（Introduction - End（1 处）） | 东、东北、北、西、西南、南、东南 | 主 Objective_1 东北 1270（0/3 已知） |
| P4 + 15.5 秒 + L | 亮目标 Objective_2 | 1 | 18% / 100% | 边上（Introduction - End（1 处）） | 东、东北、北、西、西南、南、东南 | 主 Objective_2 东北 1367（1/1 已知） |
| P8 + 7.2 秒 | 换边界 0 | 0 | 100% / 100% | 角落（Introduction - End（1 处）） | 东、东北、北、西、西南、南、东南 | — |
| P8 + 7.2 秒 | 大块揭图 全图 | 0 | 100% / 100% | 角落（Introduction - End（1 处）） | 东、东北、北、西、西南、南、东南 | — |
| P8 + 34.8 秒 | 亮目标 Objective_3 | 0 | 20% / 100% | 边上（Objective 3 - Setup（1 处）） | 北、西 | 主 Objective_3 北 3357（1/1 已知） |
| P8 + 109.8 秒 | 亮目标 BonusObjective_2 | 0 | 20% / 100% | 边上（Objective 3 - Setup（1 处）） | 北、西 | 主 Objective_3 北 3357（1/1 已知）；奖 BonusObjective_2 北 2059（0/1 已知） |
| P8 + 214.8 秒 | 亮目标 BonusObjective_1 | 0 | 20% / 100% | 边上（Objective 3 - Setup（1 处）） | 北、西 | 主 Objective_3 北 3357（1/1 已知）；奖 BonusObjective_1 西 2745（0/1 已知）；奖 BonusObjective_2 北 2059（0/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective_1 | 开局 + 15.1 秒 | 标记在未知区域 |
| 主 Objective_2 | P4 + 15.5 秒 + L | 走近才触发 |
| 主 Objective_3 | P8 + 34.8 秒 | 只有标记（在已知区域） |
| 奖励 BonusObjective_2 | P8 + 109.8 秒 | 标记在未知区域 |
| 奖励 BonusObjective_1 | P8 + 214.8 秒 | 走近才触发 |

锚点：P4 = Allies02 的单位在 AREA - Prospectors A 且 Allies02 的单位在 AREA - Prospectors B 且 Allies02 的单位在 AR（开局 + 15.1 秒 起）；P8 = Allies02 的单位在 AREA - Manhattan（P4 + 15.5 秒 + L 起）

### 我们 A4 冰雕里的兵（ours_A4_CampA4Idle）

- 交还控制：开局 + 0 秒；开场镜头 0 次、指过 0 处。敌人第一次露面：开局 + 0 秒（NAMED_ATTACK_NAMED UNIT - CNV A4 W2-1 JapanAntiInfantryInfantry 1，计时，东北）。开局预摆的敌方机动单位：定时出动 0、等玩家触发 8、脚本从不调动 15。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 0 秒 | 交还控制 | 1 | 11% / 11% | 中间（出生点） | 东北 | — |
| 开局 + 2 秒 | 亮目标 Objective01 - CNV A4 | 1 | 11% / 11% | 中间（出生点） | 东北 | 主 Objective01 - CNV A4 东 792（3/4 已知） |
| 开局 + 6 秒 | 亮目标 Bonus01 - CNV A4 | 1 | 11% / 11% | 中间（出生点） | 东北 | 主 Objective01 - CNV A4 东 792（3/4 已知）；奖 Bonus01 - CNV A4 东 1451（0/3 已知） |
| 开局 + 10 秒 | 亮目标 Bonus02 - CNV A4 | 1 | 11% / 11% | 中间（出生点） | 东北 | 主 Objective01 - CNV A4 东 792（3/4 已知）；奖 Bonus01 - CNV A4 东 1451（0/3 已知）；奖 Bonus02 - CNV A4（无标记） |
| 开局 + 62 秒 | 亮目标 Objective02 - CNV A4 | 1 | 11% / 11% | 中间（出生点） | 东北 | 主 Objective01 - CNV A4 东 792（3/4 已知）；奖 Bonus01 - CNV A4 东 1451（0/3 已知）；奖 Bonus02 - CNV A4（无标记）；主 Objective02 - CNV A4 东 1401（0/1 已知） |
| 开局 + 66 秒 | 亮目标 Objective03 - CNV A4 | 1 | 11% / 11% | 中间（出生点） | 东北 | 主 Objective01 - CNV A4 东 792（3/4 已知）；奖 Bonus01 - CNV A4 东 1451（0/3 已知）；奖 Bonus02 - CNV A4（无标记）；主 Objective02 - CNV A4 东 1401（0/1 已知）；主 Objective03 - CNV A4 东 1471（0/1 已知） |
| P17 + 0 秒 | 换边界 0 | 0 | 11% / 11% | 中间（CNV A4 - Phase 3 (1)（3 处）） | 东北 | 主 Objective01 - CNV A4 东 550（3/4 已知）；奖 Bonus01 - CNV A4 东 1206（1/3 已知）；奖 Bonus02 - CNV A4（无标记） |
| P17 + 2 秒 | 亮目标 Objective05 - CNV A4 | 0 | 11% / 11% | 中间（CNV A4 - Phase 3 (1)（3 处）） | 东北 | 主 Objective01 - CNV A4 东 550（3/4 已知）；奖 Bonus01 - CNV A4 东 1206（1/3 已知）；奖 Bonus02 - CNV A4（无标记）；主 Objective05 - CNV A4 东 2330（0/1 已知，镜头） |
| P17 + 6 秒 | 亮目标 Objective04 - CNV A4 | 0 | 11% / 11% | 中间（CNV A4 - Phase 3 (1)（3 处）） | 东北 | 主 Objective01 - CNV A4 东 550（3/4 已知）；奖 Bonus01 - CNV A4 东 1206（1/3 已知）；奖 Bonus02 - CNV A4（无标记）；主 Objective04 - CNV A4 东北 2159（0/2 已知）；主 Objective05 - CNV A4 东 2330（0/1 已知，镜头） |
| P44 + 2 秒 | 亮目标 Objective06 - CNV A4 | 0 | 14% / 14% | 中间（CNV A4 - Phase 3 (1)（3 处）） | 东北 | 主 Objective01 - CNV A4 东 550（3/4 已知）；奖 Bonus01 - CNV A4 东 1206（1/3 已知）；奖 Bonus02 - CNV A4（无标记）；主 Objective06 - CNV A4 东 2200（0/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 - CNV A4 | 开局 + 2 秒 | 只有标记（在已知区域） |
| 奖励 Bonus01 - CNV A4 | 开局 + 6 秒 | 标记在未知区域 |
| 奖励 Bonus02 - CNV A4 | 开局 + 10 秒 | 没有标记 |
| 主 Objective02 - CNV A4 | 开局 + 62 秒 | 标记在未知区域 |
| 主 Objective03 - CNV A4 | 开局 + 66 秒 | 标记在未知区域 |
| 主 Objective05 - CNV A4 | P17 + 2 秒 | 领着看（镜头） |
| 主 Objective04 - CNV A4 | P17 + 6 秒 | 标记在未知区域 |
| 主 Objective06 - CNV A4 | P44 + 2 秒 | 标记在未知区域 |

锚点：P17 = UNIT - CNV A4 Truck 1 进入 CNV A4 Area halt（开局 + 60 秒 起）；P44 = UNIT - CNV A4 north barracks 被毁 且 UNIT - CNV A4 north factory 被毁（P17 + 0 秒 起）

### 我们 A5 巴拿马之锁（ours_A5_CampA5Win）

- 交还控制：开局 + 0 秒；开场镜头 0 次、指过 0 处。敌人第一次露面：开局 + 30 秒（刷出 SovietAntiInfantryInfantry，计时，东）。开局预摆的敌方机动单位：定时出动 0、等玩家触发 3、脚本从不调动 14。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 0 秒 | 交还控制 | 1 | 19% / 19% | 中间（出生点） | — | — |
| 开局 + 2 秒 | 亮目标 Objective01 - CNV A5 | 1 | 19% / 19% | 中间（出生点） | — | 主 Objective01 - CNV A5 东 1060（3/3 已知） |
| 开局 + 150 秒 | 换边界 0 | 0 | 12% / 12% | 中间（出生点） | 东、东北 | 主 Objective01 - CNV A5 东 1060（3/3 已知） |
| 开局 + 152 秒 | 亮目标 Objective02 - CNV A5 | 0 | 12% / 12% | 中间（出生点） | 东、东北 | 主 Objective01 - CNV A5 东 1060（3/3 已知）；主 Objective02 - CNV A5 东 1542（1/1 已知，镜头） |
| 开局 + 156 秒 | 亮目标 Bonus01 - CNV A5 | 0 | 12% / 12% | 中间（出生点） | 东、东北 | 主 Objective01 - CNV A5 东 1060（3/3 已知）；主 Objective02 - CNV A5 东 1542（1/1 已知，镜头）；奖 Bonus01 - CNV A5 东 2611（0/2 已知） |
| P10 + 2 秒 | 亮目标 Objective03 - CNV A5 | 0 | 13% / 13% | 边上（CNV A5 - Phase 3（1 处）） | 东、东北、西南 | 主 Objective01 - CNV A5 西 514（3/3 已知）；主 Objective03 - CNV A5 南 2256（0/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 - CNV A5 | 开局 + 2 秒 | 只有标记（在已知区域） |
| 主 Objective02 - CNV A5 | 开局 + 152 秒 | 领着看（镜头） |
| 奖励 Bonus01 - CNV A5 | 开局 + 156 秒 | 标记在未知区域 |
| 主 Objective03 - CNV A5 | P10 + 2 秒 | 标记在未知区域 |

锚点：P10 = UNIT - CNV A5 control guard 1 被毁 且 UNIT - CNV A5 control guard 2 被毁 且 UNIT - CNV A5 contro（开局 + 150 秒 起）

### 我们 A7 鹰派（ours_A7_CampA7Pincer）

- 交还控制：开局 + 0 秒；开场镜头 0 次、指过 0 处。敌人第一次露面：开局 + 30 秒（刷出 AlliedAntiAirVehicleTech1，计时，东北）。开局预摆的敌方机动单位：定时出动 0、等玩家触发 1、脚本从不调动 17。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 0 秒 | 交还控制 | 1 | 10% / 10% | 中间（出生点） | — | — |
| 开局 + 2 秒 | 亮目标 Objective01 - CNV A7 | 1 | 10% / 10% | 中间（出生点） | — | 主 Objective01 - CNV A7 东北 94（1/1 已知） |
| 开局 + 6 秒 | 亮目标 Objective02 - CNV A7 | 1 | 10% / 10% | 中间（出生点） | — | 主 Objective01 - CNV A7 东北 94（1/1 已知）；主 Objective02 - CNV A7 东北 890（0/3 已知） |
| P5 + 0 秒 | 换边界 0 | 0 | 8% / 8% | 中间（出生点） | — | 主 Objective01 - CNV A7 东北 94（1/1 已知） |
| P5 + 2 秒 | 亮目标 Objective03 - CNV A7 | 0 | 8% / 8% | 中间（出生点） | — | 主 Objective01 - CNV A7 东北 94（1/1 已知）；主 Objective03 - CNV A7 东 1410（0/1 已知，镜头） |
| P5 + 6 秒 | 亮目标 Bonus01 - CNV A7 | 0 | 8% / 8% | 中间（出生点） | — | 主 Objective01 - CNV A7 东北 94（1/1 已知）；主 Objective03 - CNV A7 东 1410（0/1 已知，镜头）；奖 Bonus01 - CNV A7 东 1410（0/1 已知，镜头） |
| P5 + 10 秒 | 亮目标 Bonus02 - CNV A7 | 0 | 8% / 8% | 中间（出生点） | — | 主 Objective01 - CNV A7 东北 94（1/1 已知）；主 Objective03 - CNV A7 东 1410（0/1 已知，镜头）；奖 Bonus01 - CNV A7 东 1410（0/1 已知，镜头）；奖 Bonus02 - CNV A7 东 2822（0/3 已知） |
| P11 + 2 秒 | 亮目标 Objective04 - CNV A7 | 0 | 11% / 11% | 中间（CNV A7 - Phase 3 (1)（4 处）） | 东、东北 | 主 Objective01 - CNV A7 西 206（1/1 已知）；主 Objective04 - CNV A7 东 2251（0/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 - CNV A7 | 开局 + 2 秒 | 只有标记（在已知区域） |
| 主 Objective02 - CNV A7 | 开局 + 6 秒 | 标记在未知区域 |
| 主 Objective03 - CNV A7 | P5 + 2 秒 | 领着看（镜头） |
| 奖励 Bonus01 - CNV A7 | P5 + 6 秒 | 领着看（镜头） |
| 奖励 Bonus02 - CNV A7 | P5 + 10 秒 | 标记在未知区域 |
| 主 Objective04 - CNV A7 | P11 + 2 秒 | 标记在未知区域 |

锚点：P5 = UNIT - CNV A7 loyal 1 拿到 Player_1 且 UNIT - CNV A7 loyal 2 拿到 Player_1 且 UNIT - CNV A7 trai（开局 + 6 秒 起）；P11 = UNIT - CNV A7 station 被毁（P5 + 0 秒 起）

### 我们 A8 海上发布会（ours_A8_CampA8S）

- 交还控制：开局 + 0 秒；开场镜头 0 次、指过 0 处。敌人第一次露面：未确定（，，方向未知）。开局预摆的敌方机动单位：定时出动 0、等玩家触发 0、脚本从不调动 9。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 0 秒 | 交还控制 | 0 | 5% / 5% | 中间（出生点） | — | — |
| 开局 + 2 秒 | 亮目标 Objective01 - CNV A8 | 0 | 5% / 5% | 中间（出生点） | — | 主 Objective01 - CNV A8 东 2143（0/3 已知） |
| 开局 + 6 秒 | 亮目标 Objective02 - CNV A8 | 0 | 5% / 5% | 中间（出生点） | — | 主 Objective01 - CNV A8 东 2143（0/3 已知）；主 Objective02 - CNV A8 东 0（1/1 已知） |
| 开局 + 10 秒 | 亮目标 Bonus01 - CNV A8 | 0 | 5% / 5% | 中间（出生点） | — | 主 Objective01 - CNV A8 东 2143（0/3 已知）；主 Objective02 - CNV A8 东 0（1/1 已知）；奖 Bonus01 - CNV A8 东 2085（0/3 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 - CNV A8 | 开局 + 2 秒 | 标记在未知区域 |
| 主 Objective02 - CNV A8 | 开局 + 6 秒 | 只有标记（在已知区域） |
| 奖励 Bonus01 - CNV A8 | 开局 + 10 秒 | 标记在未知区域 |

### 我们 J3 白鹭城下（ours_J3_CampJ3Run）

- 交还控制：开局 + 0 秒；开场镜头 0 次、指过 0 处。敌人第一次露面：P1 + 0 秒（交给 Soviet_2: UNIT - CNV J3 castle barracks，玩家推进，东北）。开局预摆的敌方机动单位：定时出动 0、等玩家触发 0、脚本从不调动 16。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 0 秒 | 交还控制 | 0 | 4% / 4% | 中间（出生点） | — | — |
| 开局 + 2 秒 | 亮目标 Objective01 - CNV J3 | 0 | 4% / 4% | 中间（出生点） | — | 主 Objective01 - CNV J3 东北 2433（0/1 已知） |
| 开局 + 6 秒 | 亮目标 Objective02 - CNV J3 | 0 | 4% / 4% | 中间（出生点） | — | 主 Objective01 - CNV J3 东北 2433（0/1 已知）；主 Objective02 - CNV J3 东 70（1/1 已知） |
| P1 + 2 秒 | 亮目标 Objective03 - CNV J3 | 0 | 7% / 7% | 边上（出生点） | 东北 | 主 Objective03 - CNV J3 西 757（0/1 已知，镜头） |
| P1 + 6 秒 | 亮目标 Bonus01 - CNV J3 | 0 | 7% / 7% | 边上（出生点） | 东、东北 | 主 Objective03 - CNV J3 西 757（0/1 已知，镜头）；奖 Bonus01 - CNV J3 东北 2433（1/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 - CNV J3 | 开局 + 2 秒 | 标记在未知区域 |
| 主 Objective02 - CNV J3 | 开局 + 6 秒 | 只有标记（在已知区域） |
| 主 Objective03 - CNV J3 | P1 + 2 秒 | 领着看（镜头） |
| 奖励 Bonus01 - CNV J3 | P1 + 6 秒 | 走近才触发 |

锚点：P1 = UNIT - CNV J3 yuriko 进入 CNV J3 Area archive yard（开局 + 0 秒 起）

### 我们 J4 冰雕里的兵（ours_J4_CampJ4）

- 交还控制：开局 + 0 秒；开场镜头 0 次、指过 0 处。敌人第一次露面：开局 + 90 秒（刷出 CNV_ConvoyTruck，计时，西南）。开局预摆的敌方机动单位：定时出动 0、等玩家触发 0、脚本从不调动 7。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 0 秒 | 交还控制 | 0 | 13% / 13% | 中间（出生点） | — | — |
| 开局 + 2 秒 | 亮目标 Objective01 - CNV J4 | 0 | 13% / 13% | 中间（出生点） | — | 主 Objective01 - CNV J4 南 518（3/3 已知） |
| 开局 + 6 秒 | 亮目标 Bonus01 - CNV J4 | 0 | 13% / 13% | 中间（出生点） | — | 主 Objective01 - CNV J4 南 518（3/3 已知）；奖 Bonus01 - CNV J4（无标记） |
| 开局 + 10 秒 | 亮目标 Bonus02 - CNV J4 | 0 | 13% / 13% | 中间（出生点） | — | 主 Objective01 - CNV J4 南 518（3/3 已知）；奖 Bonus01 - CNV J4（无标记）；奖 Bonus02 - CNV J4 南 518（3/3 已知） |
| 开局 + 90 秒 | 亮目标 Objective02 - CNV J4 | 0 | 13% / 13% | 中间（出生点） | 西南 | 奖 Bonus01 - CNV J4（无标记）；奖 Bonus02 - CNV J4 南 518（3/3 已知）；主 Objective02 - CNV J4 西南 1344（0/3 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 - CNV J4 | 开局 + 2 秒 | 只有标记（在已知区域） |
| 奖励 Bonus01 - CNV J4 | 开局 + 6 秒 | 没有标记 |
| 奖励 Bonus02 - CNV J4 | 开局 + 10 秒 | 只有标记（在已知区域） |
| 主 Objective02 - CNV J4 | 开局 + 90 秒 | 标记在未知区域 |

### 我们 J5 敌人的敌人（ours_J5_CampJ5Lose）

- 交还控制：开局 + 0 秒；开场镜头 0 次、指过 0 处。敌人第一次露面：开局 + 30 秒（刷出 AlliedScoutInfantry，计时，东北）。开局预摆的敌方机动单位：定时出动 4、等玩家触发 0、脚本从不调动 0。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 0 秒 | 交还控制 | 0 | 11% / 11% | 中间（出生点） | — | — |
| 开局 + 2 秒 | 亮目标 Objective01 - CNV J5 | 0 | 11% / 11% | 中间（出生点） | — | 主 Objective01 - CNV J5 西 170（1/1 已知） |
| 开局 + 6 秒 | 亮目标 Objective02 - CNV J5 | 0 | 11% / 11% | 中间（出生点） | — | 主 Objective01 - CNV J5 西 170（1/1 已知）；主 Objective02 - CNV J5 东 80（1/1 已知） |
| 开局 + 62 秒 | 亮目标 Objective03 - CNV J5 | 0 | 11% / 11% | 中间（出生点） | 东、东北 | 主 Objective01 - CNV J5 西 170（1/1 已知）；主 Objective02 - CNV J5 东 80（1/1 已知）；主 Objective03 - CNV J5 西 170（1/1 已知） |
| 开局 + 66 秒 | 亮目标 Bonus01 - CNV J5 | 0 | 11% / 11% | 中间（出生点） | 东、东北 | 主 Objective01 - CNV J5 西 170（1/1 已知）；主 Objective02 - CNV J5 东 80（1/1 已知）；主 Objective03 - CNV J5 西 170（1/1 已知）；奖 Bonus01 - CNV J5 东 2130（0/2 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 - CNV J5 | 开局 + 2 秒 | 只有标记（在已知区域） |
| 主 Objective02 - CNV J5 | 开局 + 6 秒 | 只有标记（在已知区域） |
| 主 Objective03 - CNV J5 | 开局 + 62 秒 | 只有标记（在已知区域） |
| 奖励 Bonus01 - CNV J5 | 开局 + 66 秒 | 标记在未知区域 |

### 我们 J7 拜科努尔（ours_J7_CampJ7Late）

- 交还控制：开局 + 0 秒；开场镜头 1 次、指过 1 处。敌人第一次露面：开局 + 40 秒（刷出 SovietAntiInfantryInfantry，计时，西）。开局预摆的敌方机动单位：定时出动 0、等玩家触发 0、脚本从不调动 19。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 0 秒 | 交还控制 | 0 | 6% / 6% | 中间（出生点） | — | — |
| 开局 + 2 秒 | 亮目标 Objective01 - CNV J7 | 0 | 6% / 6% | 中间（出生点） | — | 主 Objective01 - CNV J7 西 1720（0/1 已知） |
| P1 + 2 秒 | 亮目标 Bonus01 - CNV J7 | 0 | 9% / 9% | 中间（出生点） | 西 | 奖 Bonus01 - CNV J7 西 1270（1/3 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 - CNV J7 | 开局 + 2 秒 | 标记在未知区域 |
| 奖励 Bonus01 - CNV J7 | P1 + 2 秒 | 走近才触发 |

锚点：P1 = UNIT - CNV J7 north jammer 被毁（开局 + 0 秒 起）

### 我们 S2 西伯利亚快车（ours_S2_CampS2Escape）

- 交还控制：开局 + 0 秒；开场镜头 0 次、指过 0 处。敌人第一次露面：开局 + 5 秒（MOVE_NAMED_UNIT_TO UNIT - CNV S2 cryo，计时，西北）。开局预摆的敌方机动单位：定时出动 1、等玩家触发 0、脚本从不调动 12。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 0 秒 | 交还控制 | 0 | 6% / 6% | 中间（出生点） | — | — |
| 开局 + 2 秒 | 亮目标 Objective01 - CNV S2 | 0 | 6% / 6% | 中间（出生点） | — | 主 Objective01 - CNV S2 西北 107（1/1 已知） |
| P4 + 2 秒 | 亮目标 Objective02 - CNV S2 | 0 | 15% / 15% | 边上（CNV S2 - Phase 2（4 处）） | 东 | 主 Objective01 - CNV S2 东 0（1/1 已知）；主 Objective02 - CNV S2 西 512（1/1 已知） |
| P4 + 6 秒 | 亮目标 Bonus01 - CNV S2 | 0 | 15% / 15% | 边上（CNV S2 - Phase 2（4 处）） | 东 | 主 Objective01 - CNV S2 东 0（1/1 已知）；奖 Bonus01 - CNV S2 东 3021（1/1 已知）；主 Objective02 - CNV S2 西 512（1/1 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 - CNV S2 | 开局 + 2 秒 | 只有标记（在已知区域） |
| 主 Objective02 - CNV S2 | P4 + 2 秒 | 只有标记（在已知区域） |
| 奖励 Bonus01 - CNV S2 | P4 + 6 秒 | 走近才触发 |

锚点：P4 = UNIT - CNV S2 cryo 进入 CNV S2 Area river station（P3 + 0 秒 起）

### 我们 S5 巴拿马之锁（ours_S5_CampS5Trap）

- 交还控制：开局 + 0 秒；开场镜头 1 次、指过 1 处。敌人第一次露面：开局 + 0 秒（开局就在视野里，开局，西南）。开局预摆的敌方机动单位：定时出动 3、等玩家触发 3、脚本从不调动 8。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 0 秒 | 交还控制 | 0 | 11% / 11% | 中间（出生点） | 西南 | — |
| 开局 + 2 秒 | 亮目标 Objective01 - CNV S5 | 0 | 11% / 11% | 中间（出生点） | 西南 | 主 Objective01 - CNV S5 西南 799（0/1 已知） |
| P1 + 2 秒 | 亮目标 Objective02 - CNV S5 | 0 | 13% / 13% | 角落（CNV S5 - Phase 2（1 处）） | 东、西 | 主 Objective02 - CNV S5 东 0（1/1 已知） |
| P1 + 6 秒 | 亮目标 Bonus01 - CNV S5 | 0 | 13% / 13% | 角落（CNV S5 - Phase 2（1 处）） | 东、西 | 主 Objective02 - CNV S5 东 0（1/1 已知）；奖 Bonus01 - CNV S5 北 1844（0/3 已知） |
| P1 + 10 秒 | 亮目标 Bonus02 - CNV S5 | 0 | 13% / 13% | 角落（CNV S5 - Phase 2（1 处）） | 东、西 | 主 Objective02 - CNV S5 东 0（1/1 已知）；奖 Bonus01 - CNV S5 北 1844（0/3 已知）；奖 Bonus02 - CNV S5 西 1610（0/2 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 - CNV S5 | 开局 + 2 秒 | 标记在未知区域 |
| 主 Objective02 - CNV S5 | P1 + 2 秒 | 走近才触发 |
| 奖励 Bonus01 - CNV S5 | P1 + 6 秒 | 标记在未知区域 |
| 奖励 Bonus02 - CNV S5 | P1 + 10 秒 | 标记在未知区域 |

锚点：P1 = UNIT - CNV S5 control guard 1 被毁 且 UNIT - CNV S5 control guard 2 被毁 且 UNIT - CNV S5 contro（开局 + 0 秒 起）

### 我们 S6 拜科努尔（ours_S6_CampS6Lose）

- 交还控制：开局 + 0 秒；开场镜头 0 次、指过 0 处。敌人第一次露面：开局 + 30 秒（刷出 JapanAntiInfantryVehicle，计时，东）。开局预摆的敌方机动单位：定时出动 0、等玩家触发 6、脚本从不调动 0。

| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |
|---|---|---|---|---|---|---|
| 开局 + 0 秒 | 交还控制 | 0 | 13% / 13% | 中间（出生点） | — | — |
| 开局 + 2 秒 | 亮目标 Objective01 - CNV S6 | 0 | 13% / 13% | 中间（出生点） | — | 主 Objective01 - CNV S6 东 30（1/1 已知） |
| 开局 + 92 秒 | 亮目标 Objective02 - CNV S6 | 0 | 13% / 13% | 中间（出生点） | 东 | 主 Objective01 - CNV S6 东 30（1/1 已知）；主 Objective02 - CNV S6 东 30（1/1 已知） |
| 开局 + 96 秒 | 亮目标 Bonus02 - CNV S6 | 0 | 13% / 13% | 中间（出生点） | 东 | 主 Objective01 - CNV S6 东 30（1/1 已知）；主 Objective02 - CNV S6 东 30（1/1 已知）；奖 Bonus02 - CNV S6 东 1780（0/2 已知） |
| 开局 + 100 秒 | 亮目标 Bonus01 - CNV S6 | 0 | 13% / 13% | 中间（出生点） | 东 | 主 Objective01 - CNV S6 东 30（1/1 已知）；主 Objective02 - CNV S6 东 30（1/1 已知）；奖 Bonus01 - CNV S6 东 180（2/2 已知）；奖 Bonus02 - CNV S6 东 1780（0/2 已知） |

| 目标 | 亮出 | 怎么被发现 |
|---|---|---|
| 主 Objective01 - CNV S6 | 开局 + 2 秒 | 只有标记（在已知区域） |
| 主 Objective02 - CNV S6 | 开局 + 92 秒 | 只有标记（在已知区域） |
| 奖励 Bonus02 - CNV S6 | 开局 + 96 秒 | 标记在未知区域 |
| 奖励 Bonus01 - CNV S6 | 开局 + 100 秒 | 只有标记（在已知区域） |

