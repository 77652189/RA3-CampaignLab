# 挑战与谜题的设计理论（调研）
子 Agent 调研，2026-10-30，总控派。【已证】=有出处，【推测】=推断。

# 红警3战役「出题」外部调研(只读,项目内未改任何文件)
读法:【已证】=我读到了原文、原始转写或一手访谈;【推测】=我的推演,或把理论搬到RTS上。[简称]见文末来源表;简称带*=只读到转述或笔记,没读到原件。

## 先说结论
1. 好题=规则的"非显然但合逻辑的推论":有卡点(catch)→诱导玩家带着错误假设撞上去→顿悟(revelation)→巧解变成玩家以后的工具。【已证】[GMTK-P][Cook07]
2. Blow 与 ten Bosch(IndieCade 2011):先把一个机制的后果穷尽(每种物件都试一遍),再挑最干净、最出人意料的做题。"惊喜=信息量",只证实预期的东西没有信息。设计更像观察系统会长出什么,而不是预先规定(Blow, GDC Europe 2011)。【已证】[Blow11][tenBosch][Blow-TGD]
3. Koster:乐趣是学会模式的奖励;模式吃透就腻;看不出模式的"噪音"让人受挫放弃;玩家总会把游戏优化成最可预测的路线。【已证】[Koster03]"造兵平推就是RTS里的这条路"是我的对应【推测】。出题办法=从巧解倒推,再用"限制"把简单解堵死(Baba)。【已证】[GMTK-Baba]
4. 教学顺序:单独教→强化至少2次→组合→考试(Swift);单关内部走起承转合(Hayashida)。【已证】[Swift12][Hayashida12]
5. "难"只有在玩家具备前置能力时才有益(Bjork);失败要让人觉得是自己的、说得清为什么(Juul);最好不靠读档也能通关(Gilbert)。【已证】[Bjork11][Juul09][Gilbert89]
6. 你们记忆里的"能拆的计时压力没用/A4能平推",和 Baba"堵死万能解"同理:压力源要么拆不掉,要么"拆它"本身就是题眼。【推测】

## A. 出题单(一关填一张,A0→A6)
- A0 先写"一句话解"再倒推题面:从巧解出发加限制,让玩家被一连串小障碍引向它。【已证】[GMTK-Baba][Taylor*]
- A1 考点=技能原子,写5栏:看到什么线索→做什么→游戏怎么变→玩家看/听到什么→应得出的一句因果话;再列"玩家已会的"和"马上用到它的地方"。
  玩家只看得清往后两三步的价值,回报要近,否则"烧尽"(学了没处用就腻);一关只教一件事(这个"一"是我的操作化)。【已证】[Cook07][Hayashida12][Swift12]
  RTS 考点分三类:规则后果(机制/克制/地形/触发点)、取舍决策(先打谁/分兵/时机)、执行(手速,只求够用);前两类才是"题"。【推测】依据[Taylor*]"知道解却做不出来很糟"
- A2 错误假设+卡点:写玩家第一反应(RTS 多半是"多造兵正面压/龟缩到够强再推");卡点=这个反应与另一个目标直接冲突。故意放诱饵让玩家先走错一次:
  好处=有起点、边错边看懂机制、必然先失败、注意力聚到卡点;走不通要"明显不可能"而不是"差一点"。【已证】[GMTK-P]
- A3 巧解:一句话说完;是已有规则的非显然推论;解完成为工具,后面关复用;不能是设计者脑洞或隐藏规则(Braid 反例:玩家说"我根本不知道能这样"=花招不是顿悟,且只有一次机会没法试)。
  GMTK 对 Blow 的归纳:解开=玩家说"我懂了",而不是"我终于猜到了"。【已证】[GMTK-P][GMTK-Blow][Blow11]
- A4 暗示三层:①巧解要用的东西开局就在场(Portal 2 把方块摆在激光前);②因果看得见(线连到门、通电变色)。【已证】[GMTK-P]
  ③分级提示(环境→延迟语音→可选明示)【推测】,依据:提示能续命、但直接告诉会少学[Schell*][Bjork11]。压力下玩家学不会、也不抬头看→关键提示放视线内、安全时给。【已证】[GMTK-V*]
- A5 检验四层:①机制事件(脚本侦测"只有巧解才会发生的事",不只看通关)【推测】;②行为:沉默观察、不帮忙,看停顿与肢体,玩家提的"解决方案"只当数据【已证】[GMTK-V*];
  ③理解:让人一句话说出规则/回忆线索(Valve 用故事回忆查玩家有没有在注意)【已证】[Portal08];④迁移:下一关换条件能否无提示再用【已证】[Bjork11][Gee*]
- A6 变体=起承转合:起(安全处展示)→承(带压力用,没有安全网)→转(同规则换个后果,推翻原假设)→合(证明掌握/加分目标)。跨关用"成对+再现":先小版再大版,同布局换规则。
  题库来源=穷举"元素×规则"的交互,最干净的放开头当教学。任天堂一关约5分钟走完这四步。【已证】[Hayashida12][GMTK-M][GMTK-Blow][GMTK-Baba];RTS 一关更长,按段落拆【推测】
- 填写示例(只演示怎么填)【推测】:考点"断补给点比杀兵管用"|误判"硬推"|卡点"增援无限,杀不完"|巧解"炸桥/占信号塔断增援"|暗示"开场镜头扫过入口,第一波增援路径可见"|检验"增援源失效事件触发时累计击杀<N"|变体"1个点(安全)→2个点(限时)→增援源会再生(转)→换地图综合(合)"。

## B. 好题判定清单(测=怎么验)
- B1 巧解一句话说完,执行不靠手速。测:让测试者写出解;写不清→拆题。【已证】[GMTK-P][Taylor*]
- B2 巧解只用学过的东西。测:列依赖表,每个原子能指到前面某关/本关开场,没有隐藏规则。【已证】[GMTK-P][Cook07]
- B3 有真卡点:直觉解(平推/龟缩)撞上具体矛盾,而不是"数值更厚"。【已证】[GMTK-P][Schell*]测:写个"只会造兵+A过去"的脚本玩家,必须失败或明显劣于巧解(用时/损失);脚本法(可接 cnv_check)【推测】
- B4 失败自己能说清原因。测:失败后让人一句话讲原因;讲不出的比例高=反馈不足。【已证】[Juul09][Cook07]
- B5 不要求"死一次才知道":会致命的情形,发生前至少一个可见预兆(预兆怎么写【推测】)。【已证】[Gilbert89]
- B6 错有代价但不毁档:最坏合理失误后(丢X%兵/资源)仍有通关路;惩罚以局部回退/损耗为主,慎用整局终止。测:从每个存档点模拟。【已证】[Gilbert89][Juul09];模拟法【推测】
- B7 关键动作可反复试,不是一次性机会。测:可尝试次数≥3,或教学关先演过。【已证】[GMTK-P][Cook12];数字【推测】
- B8 无噪音:每个元素都属于"解/卡点/诱饵"之一。测:写出解后删掉没提到的元素,题不坏就删。【已证】[Taylor*][GMTK-P][Francis16]
- B9 一次一个新原子,新技能首用后至少再被用到2次。测:数"首次出现";看计数器。【已证】[Cook07][Hayashida12];阈值【推测】
- B10 难度可参数化:解的个数、步数、每刻选项数、所需前置机制;只改"呈现"(同概念不同布局)也能调难度。【已证】[GMTK-P]
- B11 暗示被看见。测:沉默观察N人,多少人在T分钟内看/点了关键物。【已证】[GMTK-V*][Portal08];阈值【推测】
- B12 绕不开学习:允许暴力解但代价可见(得分/时间/损耗),考试关硬性要求该技能。【已证】[Taylor*](玩家用替代解就漏学了后面要用的一课);设计做法【推测】
- B13 选择有意义:每个选项至少在某种局面最优,有取舍、有持久后果、信息够。测:列选项表,找"处处最优"的项。【已证】[Meier12][Schell*]
- B14 回报与付出成比例(越难,越要有看得见的回报)。【已证】[Blow-NYU]
- B15 27关的"一句话解"互不重复,难度曲线有起伏不单调。测:27句并排查重。【已证】[Koster03][Meier12][Juul09];查重法【推测】
- B16 附加核对(Schell 十条谜题原则):目标易懂/易上手/有进展感/有"能解"的感觉/难度渐进/并行/金字塔/提示/可以"给答案"/视角转换题慎用(要么懂要么不懂)。【已证】[Schell*]

## C. 战役当课程表
- C0 一关固定剧本=弧(只讲成功案例,换场景就不灵);要学到可迁移的"规则",得有能反复试错的循环——所以关键机制要能试、考试要换条件。【已证】[Cook12][Bjork11]
- C1 每关先写目的标签:教/练/合/考/松(调节奏)/高光;说不出目的的关并掉或砍。【已证】[Taylor*]
- C2 先盘点玩家入场已会什么,开头关围绕它;不假设没有的技能;老手遇到冗长教学会腻→教学可跳过。【已证】[Cook07]
- C3 单元四步:教(只教一件,少干扰)→练(≥2次,每次略难)→合(几项技能撞在一起,出顿悟)→考(换环境,不新增原子)。塞尔达《Link's Awakening》神殿可作对照:先见绕不过的障碍→拿到关键道具→整座神殿被重新解读→boss要用它。【已证】[Swift12][Gee*][GMTK-BK]
- C4 复现:旧技能之后≥2次"换条件"回来;同一招连用3关≠学会(训练时好、换场景就差);技能吃透(grok)就腻,所以旧技能要以组合/新条件回来。【已证】[Bjork11][Koster03];"≥2次、隔2-3关"【推测】
- C5 节奏:紧张→高峰→放松(L4D:高峰后放松30-45秒,调的是节奏不是难度);战役尺度=考试关后接放松/叙事关;难度做波浪。【已证】[Booth09][Juul09];战役映射【推测】
- C6 金字塔+并行:小题汇成幕末综合关;同一关给2-3个并行子目标,卡一个不堵死。【已证】[Schell*]
- C7 每关两层目标:主线=够用的洞察;加分=更漂亮/更难的同一洞察,给老手伸展空间。【已证】[Browder09]
- C8 骨架建议:27=3幕×9;每幕=2个四关单元(教练合考)+1个幕末综合关(无新原子);全战役新原子约6-12个,其余是旧原子的转折。【推测】
- C9 每关当"自己的小游戏",有专属机制,别全是"建家-造兵-推"(星际2战役:"想玩遭遇战就去玩遭遇战")。【已证】[Browder09][Bycer11]
- C10 过程:每关重调5-8次、整关推倒重来很常见;先原型+沉默观察,不靠纸面。【已证】[Browder09][Swift12][GMTK-V*]

## D. 难度/救济/占优策略(A-C 的依据)
- 合意的困难:变式/间隔/交错/自己生成答案会让学习变难、但记得更牢;前提是玩家具备应对的前置知识,否则就成了"不合意的困难"。【已证】[Bjork11]
- 玩家怎么说"太简单":缺挑战36%、"不用重想策略"27%(85人小样本)→平推=不用重想。【已证】[Juul09]
- 大众+硬核:Celeste 辅助模式=独立于主流程、细粒度(速度/体力/空中冲刺/无敌)、写明意图并建议首玩不用;Hades 上帝模式=起20%、每死+2%、封顶80%、不削弱敌人、贴合"死亡循环";
  RE4 暗中调难度(强则敌强/死则敌弱/补给松紧),不羞辱玩家但会被速通钻;公开救济(Super Kong、鸡帽)硬核会嫌。【已证】[VICE18][GMTK-Assist][Inverse][GMTK-RE4]
- 自动调节的边界:Hamlet=先检测"挣扎"再介入,"刚好就行",并承认这是把控制权从设计者交给代码的代价。【已证】[Hunicke04]建议:公开可选的救济;自动只调供给/节奏,不碰解法对错;难度档只改数量/时限/资源,不改巧解本身。【推测】
- 不读档翻盘(RTS化)【推测】:阶段边界自动存档;按"损失"而非时间触发增援;敌攻势按玩家当前实力封顶;关键单位可复活;丢基地=目标改写(失败向前)。方向依据:[Gilbert89][Juul09][Booth09][Hunicke04]
- 时间压力:纯挂钟计时很难在恰当时刻出戏剧;Gilbert 主张用"好莱坞时间"(随玩家行动触发)。【已证】[Gilbert89]RTS 化:压力由玩家动作触发(抓住/破坏某点→倒计时开始)【推测】
- 占优策略:谜题=有占优解的游戏(Schell Lens 58),Lens 39 问"有占优策略吗";目标=让占优解是"巧解"而不是平推。【已证】[Schell*][Koster03]。Schell 镜头清单还有 Lens 21 心流、34 技能、38 挑战、69 兴趣曲线。【已证】[Schell*]
- 有出处的堵法:用限制堵万能解(Baba:设计者的活是把玩家"锁住");单位上限/维护费(魔兽3 upkeep,"keeps your unit count down",最初为性能);专属机制逼人动(星际2:上涨岩浆、日夜周期);
  静态得分点引来龟壳(Relic:胜利点造出"无法击破的墙",后改为鼓励进攻)。【已证】[GMTK-Baba][McNaughton20][Browder09][Boulle17]
- 针对"龟缩+平推"的做法(没找到成体系的设计者文献,以下是归纳):压力源不能被兵力直接拆掉;目标奖励机动(限时/多点轮替/推进线);资源限量逼扩张或袭扰;兵力上限+少而贵的单个单位。【推测】

## 来源表(*=二手)
[Cook07] D.Cook《The Chemistry of Game Design》Gamasutra 2007-07-19 https://www.gamedeveloper.com/design/the-chemistry-of-game-design (原版"skill atom"4步;2021转载改称 interaction loop 并加 Decision 步 https://lostgarden.com/2021/03/13/the-chemistry-of-game-design-2/)
[Cook12] D.Cook《Loops and Arcs》2012-04-30 https://lostgarden.com/2012/04/30/loops-and-arcs
[Koster03] 奥斯汀游戏大会2003主题演讲 https://www.raphkoster.com/wp-content/uploads/2026/07/Austin-Game-Conference-2003-Keynote-Theory-of-Fun.pdf ;同站《Theory of Fun 10 Years Later》PDF;书《A Theory of Fun for Game Design》ch.2 How the Brain Works / ch.3 What Games Are
[Blow11] M.Kumar,Gamasutra 2011-10-08(Blow+ten Bosch 的 IndieCade 讲座报道) https://www.gamedeveloper.com/design/indiecade-inside-jonathan-blow-s-puzzle-design-process ;[tenBosch] 博客 https://marctenbosch.com/news/?p=181
[Blow-TGD]《Truth in Game Design》(GDC Europe 2011)摘要 https://www.gamedeveloper.com/design/video-jon-blow-on-the-truth-in-game-design- ;[Francis16] https://www.gamedeveloper.com/design/how-jonathan-blow-found-the-roots-of-i-the-witness-i-inside-i-braid-i- ;[Blow-NYU] https://gamecenter.nyu.edu/game-designers-in-detail-jonathan-blow/
[GMTK-P]《What Makes a Good Puzzle?》2018 https://www.youtube.com/watch?v=zsjC6fa_YBg ;[GMTK-Blow]《How Jonathan Blow Designs a Puzzle》2016 https://amara.org/v/C3BFd
[GMTK-Baba]《How Baba Is You Makes Brain Busting Puzzles》2019-12(YouTube,未取得链接);[GMTK-M]《Super Mario 3D World's 4 Step Level Design》2015 https://www.youtube.com/watch?v=dBmIkEvEBtA
[Hayashida12] C.Nutt,Gamasutra 2012-04-13 https://www.gamedeveloper.com/design/the-secret-to-i-mario-i-level-design ;[GMTK-BK]《Boss Keys: Link's Awakening》 https://amara.org/v/C3BF3
[GMTK-V*]《Valve's "Secret Weapon"》文字版 https://gmtk.substack.com/p/valves-secret-weapon ;[Portal08] https://www.gamedeveloper.com/game-platforms/best-of-gdc-the-secrets-of-i-portal-i-s-huge-success
[Swift12] Kim Swift,GDC China 2012报道 https://gamedeveloper.com/design/10-years-of-design-lessons-from-em-portal-em-s-kim-swift
[GMTK-RE4]《What Capcom Didn't Tell You About Resident Evil 4》 https://amara.org/en-gb/videos/3wSkYr9aPpPY ;[GMTK-Assist]《What Makes Celeste's Assist Mode Special》2018-02 https://amara.org/v/C3BEh
[VICE18] P.Klepek 2018-02-07 https://www.vice.com/en/article/celeste-difficulty-assist-mode ;[Inverse] Hades 上帝模式访谈 https://www.inverse.com/gaming/hades-god-mode-interview
[Taylor*] Brett Taylor(Linelight)讲座笔记 https://notes.hamatti.org/gaming/puzzle-game-design ;其 GDC 2019《Puzzle Game Magic Secrets》 https://www.gdcvault.com/play/1026440
[Schell*]《The Art of Game Design》第3版 ch.14 Game Mechanics Must Be in Balance / ch.15 Game Mechanics Support Puzzles;镜头号按第2版笔记 https://notesbylex.com/the-art-of-game-design-a-book-of-lenses-2nd-edition-by-jesse-schell
[Meier12] L.Alexander 2012-03-07 https://www.gamedeveloper.com/design/gdc-2012-sid-meier-on-how-to-see-games-as-sets-of-interesting-decisions ;"有趣一次≠有趣十次"见 Escapist https://www.escapistmagazine.com/gdc-2012-sid-meier-sees-interesting-decisions-even-in-rhythm-games/
[Bjork11] https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/04/EBjork_RBjork_2011.pdf ;[Juul09] https://www.jesperjuul.net/text/fearoffailing/ ;[Gilbert89] https://grumpygamer.com/why_adventure_games_suck/
[Hunicke04] Hunicke & Chapman《AI for Dynamic Difficulty Adjustment in Games》 https://users.cs.northwestern.edu/~hunicke/pubs/Hamlet.pdf ;[Booth09] https://cdn.fastly.steamstatic.com/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf
[Gee*] J.P.Gee《What Video Games Have to Teach Us About Learning and Literacy》36原则(Prensky 改编版) https://faculty.elgin.edu/tmoore/ECC_Games_Workshop/36principles.pdf
[Browder09] P.Kollar 2009-10-30 https://gameinformer.com/games/starcraft_ii_wings_of_liberty/b/pc/archive/2009/10/30/feature-lead-designer-dustin-browder-on-story-and-map-design-in-starcraft-ii.aspx ;[Bycer11] https://www.gamedeveloper.com/design/one-man-war-examining-single-player-rts-design-
[Boulle17] https://waywardstrategy.com/2017/04/03/legacy-of-war/ ;[McNaughton20] https://www.gameinformer.com/interview/2020/01/28/what-makes-warcraft-iii-reforged-different-from-the-original

## 没能核实/要注意
- 没看视频本体:GMTK 各期用的是第三方整理的自动字幕(HuggingFace 数据集 taesiri/GMTK-Transcripts,可能有错字);Blow/ten Bosch 2011讲座只读到 Gamasutra 报道和 ten Bosch 博客。
- 你说的"去掉噪音"出自 Brett Taylor 讲座笔记(噪音=占用记忆却不帮助解题的东西)和 Koster(噪音=看不出模式的信息),不是我读到的 Blow/ten Bosch 内容;Blow 那边对应的是"惊喜=信息量""穷尽后果"。
- Koster 书正文没读到:grok/chunking 来自书评,原话以他2003/2012幻灯片为准。Schell 只看到目录与他人笔记,镜头号第2/3版可能不同;"谜题=有占优策略的游戏"来自 Schell Games 博客等转述。
- RTS 防龟缩/占优策略没找到成体系的设计者文献(查了 Rise of Nations 事后总结,无相关);BotW 神庙教学法、Into the Breach、Empuzzlement(IndieCade 2013)没能核实,未采用。
- 数字阈值(≥3次、≥2次、隔2-3关、6-12个原子)是我的建议,不是文献数据。
- 副作用:抓取的网页/转写在 C:\Users\63097\AppData\Local\Temp\claude\C--Users-63097-Documents-RA3Modding-RA3-CampaignLab\79408d22-3edb-4f25-bfe1-4a45a3f495b2\scratchpad\txt\ ,PDF 解析在 C:\Users\63097\AppData\Local\Temp\claude\C--Users-63097-Documents-RA3Modding-RA3-CampaignLab\79408d22-3edb-4f25-bfe1-4a45a3f495b2\scratchpad\mineru\ ;用了 MinerU 标准接口解析2份 Koster 幻灯片(约189页),其余走 flash 接口。

## 下一步(★推荐)
1★ 拿 A4(或 S1/J7)按 A 出题单回填、按 B 清单体检,看缺哪几栏,验证这套单子好不好用。
2 把 B3 的"只会造兵平推"脚本玩家做成通用检查(接 cnv_check),让"平推被堵死"可自动验。
3 先出27关"一句话解+目的标签"总表(C1/C8/B15),再配剧情地图。
