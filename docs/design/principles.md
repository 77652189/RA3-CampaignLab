# 战役关卡的设计准则

这份准则管的是"游戏设计"这一层：玩家的体验是什么、每一段让玩家想什么、为什么这样排。机制层（脚本、单位、地图、流程怎么写）在 [plans/README.md](../story/plans/README.md) 和 [map-language.md](../story/map-language.md)，那里说的是"原版怎么做"；这里说的是"为什么这样做"。

每条准则写三件事：**准则本身、为什么、出处**（哪几张拆解卡）。只写拆解卡里有证据的；没有证据的想法不进来。拆解卡在 [teardowns/](teardowns/)，拆的方法见 [README.md](README.md)。

**分层**用 MDA（Hunicke、LeBlanc、Zubek 2004）：机制（规则、脚本）→ 动态（玩家玩起来会怎样）→ 体验（玩家感受到什么）。设计师从机制往上搭，玩家从体验往下看。我们的策划案以前只写机制，所以改一处冒出几处：没有上层的标准，就判断不了改得对不对。这不是我们独有的问题：Westwood 的《泰伯利亚之日》复盘里说，脚本占了做一关约 2/3 的时间，触发器互相组合，修好一个场景坏另一个（[data/web-sources.md](teardowns/data/web-sources.md) B6）。准则从体验往下排，就是给每次改动一个上层的标准。

**速查**

| # | 一句话 |
|---|---|
| [P1](#p1) | 先写一句体验目标；每段写它为体验目标做什么 |
| [P2](#p2) | 一段一件事，段之间换玩家的"动词"；一关多长由核心玩法能好玩多久决定 |
| [P3](#p3) | 新单位是钥匙：至少一个主目标只能（或明显最省）用它完成 |
| [P4](#p4) | 教 → 练 → 考 → 变；给到手的那一刻就考 |
| [P5](#p5) | 取舍要有看得见的代价；顺路的不算决策 |
| [P6](#p6) | 压力分"能拆的"和"只能扛的"，开关形式要轮换 |
| [P7](#p7) | 张力曲线：高峰在新东西揭示时，喘息在段切换后，结尾最高 |
| [P8](#p8) | 让玩家推进节奏：下一段什么时候开始，由玩家的动作决定 |
| [P9](#p9) | 护送对象要依赖玩家的动作 |
| [P10](#p10) | 危险来之前告诉玩家哪里、何时、什么兵；后果马上看得见 |
| [P11](#p11) | 失败要说清错在哪 |
| [P12](#p12) | 剧情转折就是玩法转折 |
| [P13](#p13) | 地图分段 = 任务分段；每个决策落在两块地或两条路上 |
| [P14](#p14) | 敌人反制玩家的偏好 |
| [P15](#p15) | 环境机关要可预告、能两面用 |
| [P16](#p16) | 奖励的回报是下一段的工具 |
| [P17](#p17) | 出生点按类型选：推进的关背靠角落或边，四面受敌的关才放中间，而且要护住中间 |
| [P18](#p18) | 第一块可玩区要小，主目标在它的对面；扩边界朝推进方向长 |
| [P19](#p19) | 路线收紧：1～2 条主路，备选路要被逼出来或付代价才打开 |
| [P20](#p20) | 地图还没扩开就要有支线：第一块里摆一个绕路或贴敌的奖励 |

---

## 一、体验和结构

<a id="p1"></a>
### P1 先写一句体验目标；每段写它为体验目标做什么

- **准则**：一关开工前，先用一句话写玩家该感受到什么（写感受，不写机制）。每段写它在这条情绪弧线上管哪一截。一关只有一个最高潮。
- **为什么**：拆过的 8 关都能用一句话说出体验——伊贺"新玩具是唯一的钥匙"、敖德萨"先憋屈再爆发"、宫古岛"追猎会逃的对手"、横滨"从一个人到一支军队"、零点"被围着倒数"、魔鬼游乐场"贪心和撤退的节拍"——每段的机制都服务这一句。没有这一句，就判断不了一段该不该留、一个数该往哪调。Fullerton 的"以玩家为中心"就是先定体验目标，再拿试玩对照它（[web-sources](teardowns/data/web-sources.md) B3）。
- **出处**：[iga](teardowns/iga.md) [odessa](teardowns/odessa.md) [miyako](teardowns/miyako.md) [yokohama](teardowns/yokohama.md) [zero-hour](teardowns/zero-hour.md) [devils-playground](teardowns/devils-playground.md)

<a id="p2"></a>
### P2 一段一件事，段之间换玩家的"动词"；一关多长由核心玩法能好玩多久决定

- **准则**：一关 3～4 段，每段玩家做的事（护送 / 守 / 攻 / 潜入 / 建 / 追 / 解谜）不同。同一个动词连着两段，要能说出第二段新在哪。一关的长度跟着它的核心玩法走：核心玩法只撑得住两分钟，就别让它占满十五分钟。
- **为什么**：原版护送关里护送只占一部分：伊贺护送只占前 1/3，之后建基地、冻宅邸、找车；敖德萨护送 → 巨人横冲直撞 → 拆基地；斯大林格勒建 → 攻 → 守；横滨开路 → 占点 → 守 → 攻。换动词就是换玩家脑子里的问题。反过来，零点和魔鬼游乐场只有一件事，但它们短（约 20 分钟），而且那件事自己会变（越来越猛 / 一轮轮涨潮）。星际 2 的首席设计师 Browder 说每关就像一个自己的小游戏，关卡多长由这个小游戏能好玩多久决定（[devils-playground](teardowns/devils-playground.md)）。我们的 A4 全程 15 分钟都围着车队，车队开不停只要 44 秒（[a4-redesign.md](a4-redesign.md) 第〇节）。
- **出处**：[iga](teardowns/iga.md) [odessa](teardowns/odessa.md) [stalingrad](teardowns/stalingrad.md) [yokohama](teardowns/yokohama.md) [zero-hour](teardowns/zero-hour.md) [devils-playground](teardowns/devils-playground.md)

<a id="p12"></a>
### P12 剧情转折就是玩法转折

- **准则**：关中间的每一次过场、每一句关键对话，都同时换掉玩家的工具、目标、对手或地图中的至少一样。只讲故事、不换玩法的转折放到关尾当钩子，或者砍掉。
- **为什么**：敖德萨"零件运齐"= 护卫被删掉、换成巨人；宫古岛"龙背叛"= 新对手 + 超时空搬家 + 扩到全图，一个过场做五件事；伊贺"慎三必须活捉"= 目标只能冻，"慎三伪装逃跑"= 找车谜题；横滨"基地车从海上来了"= 从守变成攻。研究所的"被抓回去"不改玩法，原版就把它放在胜利判定之后。这和我们已有的共识"剧情服务玩法"是同一件事：剧情给玩法换挡一个理由。
- **出处**：[odessa](teardowns/odessa.md) [miyako](teardowns/miyako.md) [iga](teardowns/iga.md) [yokohama](teardowns/yokohama.md) [stalingrad](teardowns/stalingrad.md) [facility](teardowns/facility.md)

## 二、新单位和新机制

<a id="p3"></a>
### P3 新单位是钥匙：至少一个主目标只能（或明显最省）用它完成

- **准则**：本关解锁的单位，要有一个主目标离了它就完不成，或者代价大得多。演示和文字只是辅助。
- **为什么**：伊贺两个主目标都必须"冻住"，打死就输，整关没有一句"怎么用冻结技能"的教程，玩家照样学会；敖德萨把护卫全删掉，只剩巨人；研究所里压制射击的武士躲在掩体后，只能用刚拿到的诱惑拉过来（推断）。可选的新单位，玩家会用老办法硬打过去，新单位等于没教（我们 A4 的冰幕工兵就是这样）。
- **出处**：[iga](teardowns/iga.md) [odessa](teardowns/odessa.md) [facility](teardowns/facility.md)

<a id="p4"></a>
### P4 教 → 练 → 考 → 变；给到手的那一刻就考

- **准则**：新机制按四步排：**教**（给到手、第一次用，安全或有提示）→ **练**（不会跑的目标）→ **考**（会动的、有时间压力的）→ **变**（换一种用法，或者换一种代价）。单位给到手的同一刻，来一波专门考它的敌人。
- **为什么**：
  - 伊贺的冷冻直升机是标准样本：给 4 架 → 冻不会动的宅邸 → 7/5/3 分钟内冻会跑的车 → 冻变成侦察（冻错有代价）。先兆炮艇给到手的同一刻 8 辆坦克冲山顶。
  - 研究所每份文件都是同一个五步：镜头指路 → 停顿 → 给能力 → 讲用法 → 马上来一批考它的敌人；最后的竞技场把四样一起考。
  - 横滨的鬼王送到手就冲锋，接下来的路上只有它对付得了坦克；零点送的是地堡和导弹塔，飞龙小队专挑导弹塔和地堡打。
  - 魔鬼游乐场的岩浆走完了四步，最后一步是把敌人引进岩浆。
  - 少了"变"，新东西只是一个按钮；少了"考"，玩家不知道自己学会了没有。
- **出处**：[iga](teardowns/iga.md) [facility](teardowns/facility.md) [yokohama](teardowns/yokohama.md) [zero-hour](teardowns/zero-hour.md) [devils-playground](teardowns/devils-playground.md) [miyako](teardowns/miyako.md) [stalingrad](teardowns/stalingrad.md)

## 三、决策

<a id="p5"></a>
### P5 取舍要有看得见的代价；顺路的不算决策

- **准则**：每段至少一个真取舍：两个以上选项，每个都有玩家看得见的代价（时间、兵、风险、机会）。奖励目标放在要绕路、要冒险的地方，回报摆在旁边让玩家看见。一路顺手就能拿的东西是笑点或成绩，不是决策。
- **为什么**：
  - 伊贺 3 座道场一座在敌人主基地里；斯大林格勒东北角 3 座雕像最远，但旁边摆了 6 个钱箱；零点的反抗军在虫族基地之间的路口，晚了就被杀；魔鬼游乐场最富的矿在会被淹的低地。
  - 宫古岛龙的三层弱点（电 / 超时空仪 / 建造厂）效果不同，先拆哪个是一个有排序的选择；横滨只能拿 2 个前哨，先占哪个就决定后半关有什么。
  - 反过来，敖德萨的"拆地标"摆在巨人必经之路上、没有奖励——原版自己也只当它是黑色幽默。
  - Schell 的透镜里，"有意义的选择"问选择改不改变结果，"三角性"问有没有"低风险低回报 / 高风险高回报"的对照（[web-sources](teardowns/data/web-sources.md) B4）。
- **出处**：[iga](teardowns/iga.md) [stalingrad](teardowns/stalingrad.md) [zero-hour](teardowns/zero-hour.md) [devils-playground](teardowns/devils-playground.md) [miyako](teardowns/miyako.md) [yokohama](teardowns/yokohama.md) [odessa](teardowns/odessa.md)

<a id="p8"></a>
### P8 让玩家推进节奏：下一段什么时候开始，由玩家的动作决定

- **准则**：段的结束、敌人的唤醒写成"按时到，或者玩家先推进就提前"；至少一次让玩家自己决定"什么时候开打下一段"。龟缩也会挨打。
- **为什么**：斯大林格勒拆母亲像的那一刻才开始守船，玩家可以先在河边布防再去拆。宫古岛整关没有计时失败，三段都由玩家推进，拆得越多龙跑得越急，断电又能把它压下去。伊贺的炸桥由玩家自己的部队触发；横滨一路按区域触发，玩家走一步来一样。玩家觉得节奏是自己打出来的，紧张感才属于他。
- **出处**：[stalingrad](teardowns/stalingrad.md) [miyako](teardowns/miyako.md) [iga](teardowns/iga.md) [yokohama](teardowns/yokohama.md)

<a id="p9"></a>
### P9 护送对象要依赖玩家的动作

- **准则**：护送对象要么**停在火力下等玩家清路**（伏兵不清不走），要么**不等人、但容错按难度给**（送够几辆算赢、困难零容忍）。只按时间表自己走、玩家只能事先布置的护送，开局摆好就变成"看"。护送对象玩家点不了。
- **为什么**：伊贺的基地车遇伏就停在原地挨打，逼玩家冲到车前面；敖德萨、斯大林格勒的运输船不等人，6/8/10 艘的要求让"跟不上就丢船"。两种写法都让玩家此刻的动作直接决定结果。三关的护送对象都归第三方，玩家指挥不了。
- **出处**：[iga](teardowns/iga.md) [odessa](teardowns/odessa.md) [stalingrad](teardowns/stalingrad.md)

## 四、压力和节奏

<a id="p6"></a>
### P6 压力分"能拆的"和"只能扛的"，开关形式要轮换

- **准则**：一关里既要有**能拆掉的**压力（给玩家主动权），也要有**只能扛的**压力（给紧迫感），并且让玩家知道哪个是哪个。"拆什么就停"的形式在一条战役线里要轮换，不要每关都是"拆兵营和战车工厂就停"。
- **为什么**：拆过的关几乎每关一种开关——
  - 宫古岛：一层层压下去（电 / 仪 / 厂）；
  - 横滨：每路一个开关（空降←建造厂、传送部队←超时空仪、倒计时←虫群暂停）；
  - 研究所：刷兵器进区才开、离开就停、有在场上限；
  - 伊贺：西北村打得越狠出兵线越多；
  - 敖德萨巨人段、零点：停不掉，只能扛；
  - 斯大林格勒第 3 段：三档一次性反扑，没有来源，每档换兵种逼防线换。
  
  我们现在 A4、S6、J5 都是"遭遇战 AI + 拆兵营和战车工厂就停"，玩到第三关玩家就知道答案了。Westwood 做《泰伯利亚之日》时的原则是"同一种任务不做第二遍"（[web-sources](teardowns/data/web-sources.md) B6）。
- **出处**：[miyako](teardowns/miyako.md) [yokohama](teardowns/yokohama.md) [facility](teardowns/facility.md) [iga](teardowns/iga.md) [odessa](teardowns/odessa.md) [zero-hour](teardowns/zero-hour.md) [stalingrad](teardowns/stalingrad.md)

<a id="p7"></a>
### P7 张力曲线：高峰在新东西揭示时，喘息在段切换后，结尾最高

- **准则**：按分钟画一条粗线再写脚本。高峰放在新单位到手、新机制揭示的那一刻；最大的喘息放在交基地或段切换之后，**喘息的长度就是难度旋钮**（难度越高越短）；结尾是全关最紧的一段。紧和松要交替，"连着几分钟什么都不发生"和"从头紧到尾"都要避免。反差（先憋屈后爆发）本身就是一种高潮。
- **为什么**：
  - 伊贺交基地后敌人进攻延迟 210/120/0 秒，斯大林格勒布防倒计时 120/60/30 秒：都是"标明了长度的喘息"，而且就是难度。
  - 斯大林格勒、伊贺、横滨、零点、研究所的最高点都在结尾（守船、找车、最后 5 分钟、无尽的最后一分钟、关门的竞技场）。零点是教科书形状：左右轮流 → 剩 4 分钟唯一一次齐攻 → 最后 1 分钟无尽。横滨在 15 分钟倒计时的第 3 分钟插进库可夫，把曲线重新顶起来。
  - 曲线也可以是锯齿（魔鬼游乐场按周期涨潮），或者由玩家打出来（宫古岛）。敖德萨的情绪点不在张力最高处，而在护送 → 巨人的反差处。
  - Schell 的"兴趣曲线"：开头一个钩子，回落，一连串逐渐升高的峰谷，结尾最高（[web-sources](teardowns/data/web-sources.md) B4）。
- **出处**：[iga](teardowns/iga.md) [stalingrad](teardowns/stalingrad.md) [yokohama](teardowns/yokohama.md) [zero-hour](teardowns/zero-hour.md) [facility](teardowns/facility.md) [devils-playground](teardowns/devils-playground.md) [odessa](teardowns/odessa.md) [miyako](teardowns/miyako.md)

<a id="p14"></a>
### P14 敌人反制玩家的偏好

- **准则**：玩家一招鲜的时候，敌人要有反应：按玩家某种单位的数量加兵、按玩家的阵容生成克制部队、按玩家的位置换兵种。
- **为什么**：伊贺的宫殿按你带去的冷冻直升机数量多开刷兵线，专防一窝蜂；宫古岛背叛那一刻按你的炮艇、火炮、车、步兵、飞机数量给龙克制部队；敖德萨骚扰按巨人在海里、北边、城区换兵种。这让"新单位是钥匙"（P3）不至于变成"新单位无敌"。
- **出处**：[iga](teardowns/iga.md) [miyako](teardowns/miyako.md) [odessa](teardowns/odessa.md)

## 五、信息

<a id="p10"></a>
### P10 危险来之前告诉玩家哪里、何时、什么兵；后果马上看得见

- **准则**：玩家要守的东西、要守的地方、敌人来的时间，在危险到来之前摆到明面上（揭开、标记、倒计时、预警、喊话）。后果越重，预告越要清楚。玩家做了一个动作，结果要马上看得见（Doug Church 说的"看得见的后果"：游戏世界对玩家动作给出清楚的反应，[web-sources](teardowns/data/web-sources.md) B2）。故意藏起来的，只能是这一段的题目本身。
- **为什么**：
  - 斯大林格勒第 3 段揭开整条河道、沿航线挂 7 个标记、倒计时，每档敌人出发各有一句预警；横滨两段倒计时、EVA 按剩余时间密集报时；魔鬼游乐场岩浆淹到就没，所以"下次涨潮"倒计时一直在，难度最高时才拿掉——**同一个机关，难度靠给多少信息调**。
  - 敖德萨船血量 60% 就报警、雷达打点，屏幕上一直显示存活数 / 要求数；伊贺冻错一辆假车，它立刻转成敌人开火。
  - 研究所永远只挂一个标记，士兵喊话（"封门"）同时是前方的预告。
  - 伊贺唯一藏起来的是"哪辆是真车"，那正是最后一段的题目。宫古岛靠"拆了电厂他就不跳了"这个看得见的后果教弱点，但完全没有提示，对新手偏难。
- **出处**：[stalingrad](teardowns/stalingrad.md) [yokohama](teardowns/yokohama.md) [devils-playground](teardowns/devils-playground.md) [odessa](teardowns/odessa.md) [iga](teardowns/iga.md) [facility](teardowns/facility.md) [miyako](teardowns/miyako.md)

<a id="p11"></a>
### P11 失败要说清错在哪

- **准则**：失败条件按段换，每种失败有自己的原因文字；能说出"是哪一处、哪一路"就说。卡关提示针对"玩家不知道的事"，不针对"玩家没做到的事"。
- **为什么**：伊贺五种失败（丢车、全灭、基地全毁、打死慎三、超时）各有专门台词；敖德萨失败前切镜头到沉船；横滨超时输了，镜头对准一座还没拆的中继站转 4 秒。输了知道错在哪，玩家才愿意再来一遍，而且下一遍会换做法——这是试玩能对照体验目标的前提。
- **出处**：[iga](teardowns/iga.md) [odessa](teardowns/odessa.md) [yokohama](teardowns/yokohama.md)

## 六、地图和机关

<a id="p13"></a>
### P13 地图分段 = 任务分段；每个决策落在两块地或两条路上

- **准则**：任务结构（先做什么、后做什么、什么是可选的）和空间结构（地方怎么连）分开画两张图，再对齐（Adams 和 Dormans 的做法：任务和空间是两个独立的结构，[web-sources](teardowns/data/web-sources.md) B5）。每段用一块新地方，边界扩大时新地方本身就是新问题。每个关键决策在地图上要有对应：两条路、两处基地位、一块安全地和一块富地、前一层和后一层防线。前一段的投资（基地、防线）最好在后一段还用得上。
- **为什么**：
  - 敖德萨护送在海上、巨人段上岸进城，两段两块地；宫古岛背叛时炸掉中间的仓库，地图结构变化 = 段落变化。
  - 伊贺两座桥给了"改道"的余地，三座道场分出三档风险；零点两座桥汇成一条主坡，"守前还是守后"是地形给的；魔鬼游乐场高地安全、低地富；横滨 4 个前哨配置不同，选哪两个就选了打法。
  - 斯大林格勒的航线从玩家基地北面 640 处流过，前两段造的东西第 3 段都用得上；横滨每段的收获都是下一段的武器。
  - 斯大林格勒和横滨都不切边界，靠揭开和区域触发分段：分段不一定要换边界，但每段要有一块"被点亮"的新地方。
  - 这也是我们已有的共识"地图分段扩展让玩家集中注意力""地图只求神似、按玩法设计"。
- **出处**：[odessa](teardowns/odessa.md) [miyako](teardowns/miyako.md) [iga](teardowns/iga.md) [zero-hour](teardowns/zero-hour.md) [devils-playground](teardowns/devils-playground.md) [yokohama](teardowns/yokohama.md) [stalingrad](teardowns/stalingrad.md)

<a id="p15"></a>
### P15 环境机关要可预告、能两面用

- **准则**：会定时发作、会改变地形的机关（岩浆、潮汐、时停区、火山口、能炸的桥），要有周期和预告；而且要让玩家能拿它打敌人，不只是挨它的打。难度改预告和周期，不改结构。
- **为什么**：魔鬼游乐场的岩浆每轮有倒计时，老手把雷兽引下低地、涨潮前一刻跳回去，让岩浆替自己打；横滨的桥一炸，桥上的敌人当场死、绕不过来的队伍被删掉，但桥也是你自己的路；敖德萨的桥只对巨人塌，让"走哪条路"变成不可逆的选择。只伤玩家的机关是惩罚，两面用的机关才是工具。对我们 A3 时停区、J2 潮汐、S8 火山口、A8 平台摇晃都适用。
- **出处**：[devils-playground](teardowns/devils-playground.md) [yokohama](teardowns/yokohama.md) [odessa](teardowns/odessa.md)

<a id="p16"></a>
### P16 奖励的回报是下一段的工具

- **准则**：奖励目标和可选任务，回报最好是玩家在下一段用得上的东西（时间、兵、视野、一个打法上的缺口），而不只是成绩。
- **为什么**：横滨"保住虫巢"让第 3 段的倒计时能停 30 秒——保护类的奖励直接换成主线时间；伊贺每占一座道场当场给一队兵；零点救下的反抗军归你指挥；斯大林格勒雕像旁的钱箱。玩家看得见"拿了它下一段会更好打"，冒险才有理由（P5）。
- **出处**：[yokohama](teardowns/yokohama.md) [iga](teardowns/iga.md) [zero-hour](teardowns/zero-hour.md) [stalingrad](teardowns/stalingrad.md)

## 七、空间布局

这一节的证据主要来自 [teardowns/layout.md](teardowns/layout.md)：全部 40 张原版战役图和我们 11 关用同一把尺子量的结果（总表 [data/layout.md](teardowns/data/layout.md)）。数字都是从地图文件里量的；"为什么"多是推断，要靠试玩验证。

<a id="p17"></a>
### P17 出生点按类型选：推进的关背靠角落或边，四面受敌的关才放中间，而且要护住中间

- **准则**：先定这一关是"推进"（护送、摧毁、守点、突击队）还是"被包围"（救火、终局围攻）。推进的关，出生点放在第一块可玩区的角落或边上，背后是地图边、水或悬崖。只有要玩家四处救火的关才从中间出发，而且要用水、悬崖或少数几条路把中间护住。出生点要按玩法选，不能用模板的默认位置。
- **为什么**：原版 40 关里 36 关从角落、边上或从图外开进来，只有 4 关在中间，而且都是四面受敌的关（冰岛、复活节岛、纽约、大院）。摧毁 10 关、护送 5 关、守点 6 关没有一关从中间出发。冰岛的玩家在正中，但脚下是一座四面环水的岛。背后安全、前方未知，玩家的注意力自然朝前；出生点在中间，每个方向都要分心（推断）。我们 11 关有 9 关在中间，其中 A4、A5、A7、A8、J3 五关的出生点彼此相距不到 300，都在 5000×5000 图西半边的正中：7 张新地图都从 `island.py` 原样复制了 `start` 那组地点。
- **出处**：[layout](teardowns/layout.md)（第一节第 1 条）、[data/layout.md](teardowns/data/layout.md)、[iga](teardowns/iga.md) [stalingrad](teardowns/stalingrad.md) [yokohama](teardowns/yokohama.md) [zero-hour](teardowns/zero-hour.md)

<a id="p18"></a>
### P18 第一块可玩区要小，主目标在它的对面；扩边界朝推进方向长

- **准则**：开局只开一块（原版中位数占全图 41%）。出生点在这一块的一角或一边，这一块里最远的主目标在它的另一头（推进纵深约半条对角线）。扩边界时，新的一块朝推进方向长出去，出生点留在后方。任务的地点会移动时，可玩区可以跟着移（移动窗口），不一定越来越大。
- **为什么**：原版 29/40 关会扩边界或移动窗口，推进纵深中位数 0.57 条第一块对角线，纵深不到 0.15 的只有 1 关。开局那一段"走过去"，就是张力曲线的第一个上坡（P7），也是"先看见、后够得着"的信息节奏（P10）。原版扩到最后，出生点仍在边上或角落的有 35 关。我们 8/11 关开局就是全图，5/11 关最远的主目标离出生点不到 0.15 条对角线。这也是我们已有的共识"地图分段扩展让玩家集中注意力"的量化版。
- **出处**：[layout](teardowns/layout.md)（第 3 条）、[iga](teardowns/iga.md) [odessa](teardowns/odessa.md) [miyako](teardowns/miyako.md)

<a id="p19"></a>
### P19 路线收紧：1～2 条主路，备选路要被逼出来或付代价才打开

- **准则**：从出生点到主目标，陆路 1～2 条主路，或者干脆没有陆路（要靠水、两栖、空中）；敌人在第一块里从 1～2 个方位来。另外给一条备选路，但它要么被事件逼出来（桥被炸），要么要付代价才打开（修桥、炸封锁），要么是二选一的入口（任一突破口），不能是平地上本来就有的第三、第四条路。
- **为什么**：原版有陆路的 19 关里 10 关只有 1～2 条路，还有 10/40 关根本没有陆路；第一块里敌方据点中位数 2 个方位。伊贺南桥被炸逼出西桥，大阪修桥，横滨炸桥，宫古岛"任一突破口"，零点两座桥汇成一条坡：备选路都有来由。路线收紧了，"走哪条"才是决策（P5、P13）。我们 8/11 关去主目标有 3 条以上陆路，平地开阔，走哪都行。
- **出处**：[layout](teardowns/layout.md)（第 4、6 条）、[iga](teardowns/iga.md) [yokohama](teardowns/yokohama.md) [miyako](teardowns/miyako.md) [zero-hour](teardowns/zero-hour.md)

<a id="p20"></a>
### P20 地图还没扩开就要有支线：第一块里摆一个绕路或贴敌的奖励

- **准则**：第一块可玩区里就要有一个奖励目标或支线，摆在要绕路、或者贴着敌人的地方；后面几块再各放一些，可以先让玩家远远看见。地图小不是没有支线的理由。
- **为什么**：原版 56 个奖励目标里 29 个在第一块可玩区里就有，26 个要绕路，19 个贴着敌方据点。斯大林格勒东北角的雕像最远、旁边 6 个钱箱；伊贺一座道场在敌人主基地里；日内瓦的瑞士银行贴着敌人。支线让小地图里也有"去不去"的决策（P5），回报最好是下一段的工具（P16）。我们奖励目标数量够，但多数关开局就是全图，"先看见、后够得着"的层次没有了。
- **出处**：[layout](teardowns/layout.md)（第 5 条）、[stalingrad](teardowns/stalingrad.md) [iga](teardowns/iga.md)

---

## 怎么用

- 写新策划案：照 [plan-template.md](plan-template.md) 的增补栏，先写体验目标、每段的动词和决策、张力曲线，再写 yaml。
- 返工旧关：照 [a4-redesign.md](a4-redesign.md) 的做法，先列"哪里不符合准则"（每条带证据），再从体验目标往下重排。
- 判断一次改动对不对：问它让哪条准则变好了、有没有让别的变坏。
- 试玩：[playtest.md](playtest.md)。
- 加准则：先有拆解卡里的证据，再加；一条准则至少两张卡支撑（P3、P9、P11、P14、P15 现在只有两到三张，以后拆新关时优先补）。
- 量布局：改完地图或换了出生点，跑 `python -I -X utf8 docs/design/teardowns/data/layout_measure.py <构建名>` 再跑 `layout_table.py`，对照 [data/layout.md](teardowns/data/layout.md) 里原版的范围（P17～P20）。

## 参考

- Hunicke, LeBlanc, Zubek, *MDA: A Formal Approach to Game Design and Game Research*（AAAI 2004 研讨会）
- Tracy Fullerton，《游戏设计梦工厂》（*Game Design Workshop: A Playcentric Approach*）：先定玩家体验目标，再用试玩检验
- Jesse Schell，《游戏设计艺术》（*The Art of Game Design: A Book of Lenses*）：透镜就是一组检查问题；本文用到"兴趣曲线""有意义的选择""三角性"
- Ernest Adams、Joris Dormans，《游戏机制：高级游戏设计技术》（*Game Mechanics: Advanced Game Design*，2012）第 10 章任务和空间、第 11 章锁和钥匙
- Doug Church, *Formal Abstract Design Tools*（Game Developer，1999）：意图、看得见的后果
- Dustin Browder 访谈（Destructoid；Game Informer 2009-10-30）：每关一个小游戏
- Rade Stojsavljevic, *Postmortem: Command and Conquer: Tiberian Sun*（Game Developer，2000）
- 网址和短引文见 [teardowns/data/web-sources.md](teardowns/data/web-sources.md)
