# 官方 RTS 战役关卡布局调研：出生点、目标方向、敌人方向、奖励目标

调研日期：2026-10-27。只读公开资料，没有改任何项目文件。

## 来源和可信度

- 主要来源是 Liquipedia 战役页（`https://liquipedia.net/starcraft2/Campaign/<关名>`），用 MediaWiki API 批量取的 wikitext，原始文本存在 `scratchpad/raw/lq/`。
- starcraft.fandom.com 和 cnc.fandom.com 在本机连不上（ECONNREFUSED / 超时）。breezewiki 镜像被 Anubis 拦了，StrategyWiki 也没有这些关卡的攻略页。
- 红警 2 的资料来自 strategygamers.com（原 the-spoiler.com 2000 年的攻略，Steven W. Carter）和 lparchive.org。
- 方位用的是地图俯视方向：上 = 北。凡是“推断”的都注明了依据，“未确认”就是没找到文字证据。
- 引文一律是短引用或转述，都不超过 15 个英文词。

---

## 星际争霸 2《自由之翼》

### 1. Liberation Day（第 1 关）
- **出生点**：在路上空投，起点在南边。这是推断：攻略写的是一路往北走，“Make your way West and North again”，最后“Go north yet again”到总部。
- **任务类型**：英雄小队沿一条路推进，最后摧毁一座建筑。没有基地。
- **主要目标方向**：北，路线是一条“之”字形的单线。
- **敌人方向**：1 个，一直在正前方。路上有一次三个空投仓的伏击，结尾有 Viking 飞来落地守总部。
- **奖励目标**：6 块 Dominion 全息广告牌，分布在主路沿线，小地图上用黄点标出。奖励只有成就。还提醒了一个“不能回头”的点：过了这里任务很快结束，没打完的广告牌要先回去打。
- **来源**：https://liquipedia.net/starcraft2/Campaign/Liberation_Day

### 2. The Outlaws（第 2 关）
- **出生点**：南边的小基地。这是推断：攻略写“Move north out of your base”，出门往北去捡资源和打矿区守军。
- **任务类型**：发展基地，然后推进摧毁敌方基地。
- **主要目标方向**：北，“head north and take out the base”。
- **敌人方向**：基本只有北边 1 个方向，敌人不太主动进攻。
- **奖励目标**：营救叛军，在出生点以西，“outlaw base to the west of your starting point”。往左走就会触发敌人进攻叛军基地。走到入口信标，就能拿到对方全部单位、一座兵营和资源箱。另外地图上散落着资源托盘，奖励只有成就。
- **来源**：https://liquipedia.net/starcraft2/Campaign/The_Outlaws

### 3. Zero Hour（第 3 关）
- **出生点**：右下角，原文“You start in the lower right hand corner of the map”，基地已经建好。
- **任务类型**：限时死守 20 分钟，波次越来越强，最后 1 分钟无限出兵。
- **主要目标方向**：没有方向，原地守住就行。
- **敌人方向**：2 到 3 个入口，一个是坡道，另外是“two bridges leading into your base”，桥头各有一个地堡。攻略建议放弃外侧地堡，只守坡顶。
- **奖励目标**：营救 3 支叛军小队，跟着倒计时一支一支揭示。位置依次是东部、地图中央、西部，越来越远，也越来越危险，旁边埋着地下潜伏的虫族。另外有个隐藏挑战（成就）：地图上有 8 个孵化场，左上 2 个，右上 3 个，左下 3 个，也就是除了玩家这个角，其余三个角都是敌巢。
- **来源**：https://liquipedia.net/starcraft2/Campaign/Zero_Hour

### 4. The Evacuation
- **出生点**：右下，“two Firebats and two Medics on the lower right part of the map”。开局没有基地，要先走到 Hanson 的定居点（往左）才拿到基地。
- **任务类型**：护送。车队沿一条路开往太空港，共要送 50 名殖民者。
- **主要目标方向**：基地往太空港方向沿路走。太空港具体在哪个方向，原文没有直接写，未确认。
- **敌人方向**：3 个，就是路边的 3 个岔口（“3 entrances along the road”）。虫族不在主路上，都从岔路冲出来。后期还会加上空投和 Nydus 虫洞，变成随处冒出来。虫族基地有两个，一个在左上角，一个在右侧中部。
- **奖励目标和隐藏路线**：
  - 隐藏小路：出生点东北有一片看上去走不过去的森林，点它北侧就能穿过去，通到一块有几只小狗和若干资源箱的空地。
  - 3 个 DNA 茧，各 +1 虫族研究点：一个在太空港坡道旁，一个在地图中部偏左（从第一个地堡旁边的坡道上去），一个在主路右侧、基地和太空港的中点。每个都有少量潜地单位看守。
- **来源**：https://liquipedia.net/starcraft2/Campaign/The_Evacuation

### 5. Outbreak
- **出生点**：未确认，Liquipedia 没写。能看出基地有 2 个正面入口，基地左下角还有一块“Destructible Debris”，是第 3 个入口。
- **任务类型**：昼夜交替的清剿，要摧毁 144 座感染建筑。白天出门拆，晚上回家守。
- **主要目标方向**：没有单一方向，感染建筑“all around the map”，东北（右上）有一块可以开的分矿。
- **敌人方向**：前两夜 2 个，第 3 夜后方的碎石被打穿，变成 3 个（“units will begin coming in from all three paths”）。这是一个按时间增加进攻方向的设计。
- **奖励目标**：2 只 Infestor，各 +1 虫族研究点。地图上用白色菱形标出，周围有视野，白天会钻进地下，要造导弹塔反隐。
- **来源**：https://liquipedia.net/starcraft2/Campaign/Outbreak

### 6. Safe Haven
- **出生点**：上边，“You begin at the top of the map”，基地已经建好。
- **任务类型**：推进，按顺序摧毁 3 座 Nexus，然后打 Purifier 母舰。中间穿插限时拦截舰队。
- **主要目标方向**：南。3 座 Nexus 依次在右侧、右下、正下方，越往后守军越强。
- **敌人方向**：基地有 2 个入口（“Bunker between the two entrances”）。前期有两次进攻打到基地，另外有一台巨像会单独来袭。
- **奖励目标**：拦截 3 支 Terror Fleet。这些目标是动态出现的，看 Purifier 摧毁了几个前哨站，舰队会去袭击殖民点。救下殖民者会留下资源。
- **来源**：https://liquipedia.net/starcraft2/Campaign/Safe_Haven

### 7. Haven's Fall（和 Safe Haven 二选一）
- **出生点**：9 点钟方向，也就是西边的中段，“at the 9 o'clock position on the map”。
- **任务类型**：救火式多点防守加清剿。各殖民点会被依次感染，要赶在感染完成前去救，最后摧毁虫族主基地。
- **主要目标方向**：最近的感染基地在家门口，第一个殖民点在基地以南，北边有一个带 Ultralisk 的主巢。
- **敌人方向**：2 个，“Ultralisks might occasionally attack from the north and Brood Lords from the south”。
- **奖励目标**：Liquipedia 没有列出奖励目标。“阻止更多殖民点被感染”是一种隐性的收益：救下来，后面的压力就小。
- **来源**：https://liquipedia.net/starcraft2/Campaign/Haven%27s_Fall

### 8. The Devil's Playground
- **出生点**：左边的中部，“You start in the left middle portion of the map”。
- **任务类型**：采集，要挖 8000 晶矿。岩浆定时上涨，要把农民撤到高地上。
- **主要目标方向**：没有固定方向，到处找富矿区挖。
- **敌人方向**：多个，“Zerg attacks come from different directions”，攻略建议每个入口放一个地堡，至少 2 个。
- **奖励目标**：
  - 失踪的矿工：就在出生点旁边，“right next to your starting position”，会送一座指挥中心和 5 个 SCV。在任务正式发布之前就能先拿到。
  - Brutalisk：在左下角，+3 虫族研究点。
  - 主动去打虫巢，路上还会捡到 Reaper 小队和资源箱，这是没有写明的奖励。
- **来源**：https://liquipedia.net/starcraft2/Campaign/The_Devil%27s_Playground

### 9. Welcome to the Jungle
- **出生点**：下边中间，“You start off on the bottom center part of the map”。
- **任务类型**：采集竞速加多点争夺。要收集 7 罐 Terrazine，同时不能让神族封住 7 座祭坛。
- **主要目标方向**：祭坛集中在左侧和中部，右侧还有 4 座，攻略说可以不管。神族主基地在左上角，在出生点的对角斜上方。北边有一块神族分矿，打掉以后能抄近路去中央。
- **敌人方向**：主要从左上来，神族定期进攻。真正的威胁是祭坛被封，等于压力同时出现在好几个点。
- **奖励目标**：3 个神族遗物，各 +1 研究点，难度一个比一个高：
  - 基地北边门口一个，没人守；
  - 左侧中部一个，3 个狂热者守；
  - 右上角一个，“past the two altars there”，有光子炮和追猎者守。
- **来源**：https://liquipedia.net/starcraft2/Campaign/Welcome_to_the_Jungle

### 10. The Dig
- **出生点**：未确认。开局是一支小队沿着一条路走，路上会拿到攻城坦克，走到营地才接管基地。
- **任务类型**：先短暂推进，然后长时间守点。激光钻要一直轰神殿大门，大门掉得越快，神族进攻越猛。
- **主要目标方向**：神殿门的方向未确认。神族基地在北边（“two protoss nexus in the northern bases”）和东边（“eastern Protoss base”），东南有一块自己的分矿。
- **敌人方向**：2 个，基地有两条坡道（左坡和右坡，portforward 说是“2 entrances”）。中后期还有空军和折跃棱镜空投。
- **奖励目标**：3 个神族遗物。在任务进行到一半左右揭示位置。要派单位过去开视野，再用激光钻打掉存放遗物的建筑，路线会穿过敌人的进攻路线。攻略建议在一波进攻刚打完时去拿。
- **来源**：https://liquipedia.net/starcraft2/Campaign/The_Dig ，https://portforward.com/games/walkthroughs/Starcraft-2-Wings-of-Liberty/Mission-10-The-Dig.htm

### 11. Maw of the Void
- **出生点**：未确认具体方位。开局有 3 艘战列巡洋舰，先清理着陆区，基地才降落在一个“starting island”（平台）上。
- **任务类型**：推进，一路逐个拆掉 Rip-Field 发生器，往虚空宝库走。
- **主要目标方向**：未确认。沿着岛链跳岛推进，在第二个发生器那里可以换基地。
- **敌人方向**：起始岛会被折跃棱镜空投进攻，可以理解为从空中来、方向不固定。地面入口只有一个坡道，用一个坡顶地堡就能守住。
- **奖励目标**：4 座监狱，各关着 3 个黑暗圣堂武士，共 +4 研究点。都在通往宝库的路上或者旁边的小岛上，打掉监狱就会形成一座桥，“almost on the way to the Xel'Naga vault”。
- **来源**：https://liquipedia.net/starcraft2/Campaign/Maw_of_the_Void

### 12. Supernova
- **出生点**：靠近地图中间，偏西南，“near the middle of the map, but more to the south-west”。
- **任务类型**：被一堵火墙追着推进。火墙会慢慢往前推，要搬家（基地飞走）。
- **主要目标方向**：东北。先拆掉东边的神族基地，把基地搬过去，宝库在新基地的东北。左上角还有一座神族基地，开局会开始建造。
- **敌人方向**：2 个，左上和东边。火墙从反方向逼过来，等于第 3 个“敌人”，这是推断。
- **奖励目标**：4 个神族遗物，被火墙烧到就没了：
  - 基地门口右侧一个，1 个狂热者加 1 个追猎者守；
  - 基地东南、分矿右边一个；
  - 基地东北、东边神族基地的西北一个；
  - 宝库南边的凹地里一个，有圣堂武士和光子炮守。
- **来源**：https://liquipedia.net/starcraft2/Campaign/Supernova

### 13. Belly of the Beast
- **出生点**：未确认。这一关是 4 名英雄的地牢式探索，按洞穴顺序推进。
- **任务类型**：英雄小队推进，依次到 3 处裂隙放地震炸弹，每处都要守炸弹一段时间，然后杀女王，最后逃出洞穴。
- **主要目标方向**：一条单线。第一个洞穴路过地图右下角，那里有两侧夹击的伏击。第二个洞穴路过左下角，有 Aberration 加上自爆虫增援。
- **敌人方向**：放炸弹守点时，4 条 Nydus 虫从左右两侧冒出来。平时就是前方加伏击。
- **奖励目标**：没有。
- **来源**：https://liquipedia.net/starcraft2/Campaign/Belly_of_the_Beast

### 14. All-In（最终关）
- **出生点**：未确认具体方位。开局就有“two ground choke points and the Artifact cliff”。
- **任务类型**：守点，要守到神器充能完成。可以手动放神器新星，相当于清屏的“恐慌按钮”。
- **主要目标方向**：没有方向，原地守住。
- **敌人方向**：地面 2 个隘口，文中提到有一个“North Choke Point”，还建议“把东侧防线往回收”。如果上一关打的是 Belly of the Beast，还会多出大规模空军。如果打的是 Shatter the Sky，就换成 Nydus 虫在各处冒出。
- **奖励目标**：没有。
- **来源**：https://liquipedia.net/starcraft2/Campaign/All-In

---

## 红警 2

说明：用户提到的“尤里的复仇盟军 1 'Time Shift'”名字有误。按 speedrun.com 的关卡表，Time Shift 是尤里的复仇**苏军**第 1 关，盟军第 1 关叫 **Time Lapse**。这两关都没找到带方位的攻略，未确认。

### RA2 盟军 1：Lone Guardian（纽约）
- **出生点**：未确认罗盘方位。Tanya 从水边开局，先去击沉 4 艘无畏舰。
- **任务类型**：英雄开场打击，然后会师基地（Fort Bradley），再摧毁苏军补给基地。
- **主要目标方向**：Fort Bradley 在 Tanya 第一段路线的东南。苏军基地在 Fort Bradley 以北，有 3 辆老兵灰熊坦克守着。
- **敌人方向**：动员兵从两栖登陆和空降两路来，空降落在东北方的 McBurger Kong 餐厅和加油站附近。
- **奖励目标**：西北部有 2 个箱子，一个加火力、一个加防御，攻略说可以不拿。
- **来源**：https://strategygamers.com/walkthrough/command-and-conquer-red-alert-2 （原 the-spoiler.com）

### RA2 苏军 1：Red Dawn（华盛顿）
- **出生点**：未确认罗盘方位。MCV 停在哪里就在哪里展开。
- **任务类型**：发展基地，然后推进摧毁五角大楼。
- **主要目标方向**：东北，“the Pentagon, which is northeast of your starting area”（转述）。
- **敌人方向**：中途有路口的 GI、一个盟军小基地和碉堡，基本不主动进攻。
- **奖励目标和隐藏路线**：打爆停车场和码头的卡车，会掉出箱子（火力、金钱、护甲、升级加速度），分布在多处停车场，基地东边码头也有。**隐藏路线**：修好第二个盟军基地西北那座断桥，过桥能拿到 4 辆犀牛坦克。
- **来源**：同上

### 附带：RA2 盟军 2 Eagle Dawn、苏军 2 Hostile Shore（同一份攻略）
- Eagle Dawn：目标空军学院在起点西边。出生点北边有一个护甲箱，东侧有 3 辆卡车，西北角有一个金钱箱。还有一条**捷径**：Tanya 游过一条窄水道，绕开岗哨炮。
- Hostile Shore：滩头登陆后往西打炼油厂，然后往南扫港口南侧的盟军基地。北缘油井东边、北岸酒店、地图中间的 McBurger Kong 里都有箱子。

---

## 规律小结

1. **出生点几乎不在正中，多在边或角。** 有明确方位的 9 关星际 2 里，在角上的 2 关（Zero Hour 右下、Evacuation 右下），在边中段的 5 关（Safe Haven 上、Haven's Fall 西、Devil's Playground 左中、Jungle 下中、Outlaws 南，后者是推断），只有 Supernova 接近中间，但那关有火墙逼着搬家，等于“中间”只是暂住。Liberation Day 是推断在南端的线性路线。
2. **主要目标一般在出生点的对边或对角。** Outlaws 和 Liberation Day 是南到北，Safe Haven 是北到南，Supernova 是西南到东北，Jungle 是下中对左上的神族主巢，Zero Hour 是除了玩家那个角，其余三个角都是虫巢。
3. **任务类型决定敌人从几个方向来。**
   - 推进关：敌人基本只在前方 1 个方向，靠沿路伏击制造变化。
   - 守点关：一般 2 个入口，常见的设计是让入口数随时间增加。Outbreak 第 3 夜打穿后方碎石，从 2 个变 3 个；Evacuation 后期出现空投和 Nydus，变成随处冒出；All-In 有 2 个隘口外加空军或 Nydus。
   - 救火关（Haven's Fall、Jungle 的祭坛、Safe Haven 的舰队）：敌人方向不多，但目标点会依次亮起，逼玩家分兵。
4. **奖励目标的摆法有固定套路。**
   - 第 1 个放在基地门口，几乎没人守，是教学用的（Jungle 北门、Supernova 右门、Devil's 矿工、Outlaws 西边的叛军）。
   - 后面的越摆越远、守得越来越重，常放在角落或旁边的凹地（Jungle 右上角、Devil's 左下角、Supernova 宝库南侧凹地）。
   - 常压在敌人的进攻路线上，或者限时出现（The Dig、Zero Hour 叛军跟着倒计时揭示、Supernova 被火墙吞掉）。
   - 奖励多半是研究点。早期关卡给的是“单位加建筑”这种能马上用的东西（Outlaws、Devil's 矿工、Maw 的黑暗圣堂武士）。
5. **隐藏路线很少，一般是视觉上像墙、其实能走的地方，后面藏着资源箱。** 例子有 Evacuation 出生点东北的森林、红警 2 Red Dawn 修断桥送犀牛、Eagle Dawn 游泳绕开岗哨。红警 2 更爱用“打爆卡车或民用建筑掉箱子”，箱子散布在全图各处。
