# 遭遇战 AI 进攻队的撤退和"顺手打建筑"开关

原版进攻队出门后，每 UpdateTime（常见 2 秒）由微操管理器（AIMicroManagerData）重新判一次"队伍状态"：打、清场、撤退、什么都不做……这里写我们上台确认过的两件：**撤退**（RetreatPowerAdvantage 一族）和**交战开关 EngagePassiveTargets**。给关卡线和模拟器用。

测试台探针：`experimental/cnv/missions/airetreat_bench.py` + `checks/engine_airetreat.py`（地图、AI、远处电厂同 `ainamed_bench` 的 ainmfar：一个常开状态派 4 个维和步兵按名字去打南边约 1010 远的电厂）；读数在检查文件开头；模拟器对拍在 `tests/test_simai.py` 末尾。

## 1. 撤退

- 规则（程序）：队伍看得见的敌方单位里，"敌人杀光我方要的时间 ÷ 我方杀光敌人要的时间"叫力量优势；它低于 RetreatPowerAdvantage（原版 MEDIUM 0.2）、我方不比敌人慢、离自己基地至少 RetreatMinDistanceFromBase（原版 900，探针改成 300）时，队伍撤回基地；至少走出 RetreatMinDistanceToFallback（默认 500）才重新判。撤退结束时队伍剩下的人 ≤ DisbandAfterRetreatTeamSize 就解散。
- **测**（airet：远处电厂旁站 12 个玩家的维和步兵；RetreatPowerAdvantage 0.2、RetreatMinDistanceFromBase 300）：4 人到远厂边上（s15）就掉头，s26 全部回家，**一个没死**——撤退是**纯移动**，路上不还手。在家停约 15 秒（≈ 探针的 MaxTeamIdleTime / MaxUnitIdleTime）再出发，又在远厂边掉头……约 27～32 秒一个循环，85 秒里转了三圈。
- **测**（airet0：同样的守军，RetreatPowerAdvantage 0）：不撤，4 人 s19～s25 在远厂死光。
- 给关卡：敌方 AI 用原版微操（RetreatPowerAdvantage 0.2）时，**玩家在目标旁摆重兵，AI 进攻队会掉头回家、过一会儿再来**，不会送死；要让它死磕，得用自己的微操数据把 RetreatPowerAdvantage 设 0。原版的"离基地 900 以内不撤"意味着靠近 AI 家门的守点它不会撤。

## 2. EngagePassiveTargets（顺手打建筑）

- 规则（程序）：开着时，队伍视野（× EnemySearchDistanceVisionMultiplier）里有打得动的敌方建筑，就先打最近的那座，再继续去目标。
- **测**（aipas1：路线西边 250 放一座玩家电厂，EngagePassiveTargets 开）：醒来 1 秒旁厂就开始掉血，15 秒打到见底；85 秒里没到远厂。
- **测**（aipas0：同样摆法，EngagePassiveTargets 关）：直接去远厂（s15 到），旁厂一直满血，直到远厂倒了（s35）RAMPAGE 才转去打最近的旁厂。
- 给关卡：原版微操这个开关是开的——**AI 进攻队路过玩家建筑会停下来拆**；想让它一路直奔目标，用自己的微操数据关掉。

## 3. 进驻（打仗时进旁边的民房）

- 规则（程序）：队伍在"打"（含扫荡、守点）时，每个步兵各自看可驻建筑列表，取**第一座**离自己水平距离 150 以内、进得去的，进去并离队；不挑最近。走路途中不进。
- **测**（aigar1：远厂北 200 放一座原版中立民房，开关开）：醒来 s18 民房归 AI，活着的 3 个兵到 s75 都没死（对照组同一时间全死），按"都进去了"读。
- **测**（aigar0：同样摆法，开关关）：没人进，s28 全死。
- **测**（aigarfar：民房放在远厂南 450，背着来路）：没人进，s30 全死。第一次放在北 450（来路上）时，打的时候站最北的那个兵离楼不到 150，**一个人**进了楼——距离按每个兵自己算。
- 给关卡：原版微操这个开关是开的——**AI 进攻队打到民房边上会钻进去**，玩家要清楼；不想这样就在攻击目标 150 内别放空民房，或用自己的微操数据关掉。

## 4. 进自家基地防御

- 规则（程序）：同进驻，候选是 AI 自己的基地防御；打的时候进（EnterBaseDefenses，xsd 默认开），闲着时还要 WhenIdle 也开（默认关）。原版能装步兵的防御**只有盟军多管炮塔** AlliedBaseDefense（装 1 人，只收步兵）；苏联、日本的防御只有工程师修理口。
- **测**（aibd1：远厂北 200 放 4 座 AI 自己的多管炮塔，主开关开）：s21 起有 **1 个**维和进了炮塔，活到结束，其余 s33 前死光。只进了一个：aibdwho（每座炮塔旁分别计数）看到几个兵一起挤到 1 号炮塔边（s22 有 3 个），进去 1 个，其余散开——读作同一轮里大家都被派去列表里第一座、没给前面的人占位，不是"离得远"（没完全证实）。
- **测**（aibd0：主开关关）：没人进，s33 全死。aibdidle（主开关关、只开 EnterBaseDefensesWhenIdle）：同 aibd0——光开 WhenIdle 不够。
- 给关卡：盟军 AI 的步兵打到自家多管炮塔边上会钻进去。

## 5. 碾压

- 规则（程序）：坦克能压目标（CrusherLevel 大于 CrushableLevel）、且"开到目标的秒数 < CrushPreference × 开枪打死它的秒数"，就直接开过去压，不离队。
- **测**（aicrush1：AI 4 辆锤子坦克打远厂旁 12 个玩家维和，Crush 开、CrushPreference 1.0）：s19 起开压，约 9 秒压死 12 人，坦克一辆没掉。
- **测**（aicrush0：Crush 关）：开枪对打，4 辆坦克 s38 全被打光，守军只死 1 个。aicrushlo（Crush 开、CrushPreference 0.01）：同 aicrush0，几乎不压。
- 给关卡：原版 AI 的坦克见到步兵会直接压过去，玩家拿步兵海挡坦克没用；想让 AI 坦克老实开枪，微操数据关掉 Crush。

## 6. 伤员撤退、倒车（台上没对上）

- 规则（程序）：队员血量比 < PullbackInjuredHealthPct（MEDIUM 0.35）→ 离队，去自己/盟友的建筑里模板正好是 ArmyDefinition 车辆维修设施（盟军 AlliedWarFactory、苏联 SovietCrane）、走得到的最近一座。倒车：离目标比"最远射程 − 10"近就退到那个距离。
- **测**（aipullback_bench：AI 4 辆坦克打远厂旁 12 个维和，Crush 关，AI 家里放一座 AlliedWarFactory）：aipull1 一辆没回家，被打光；aipullh1 第 12 秒在路上把坦克血设成 30%，照样开去送死；aipullga 换成盟军自己的守护者坦克，也不回。**和程序读法对不上，原因没定**（队员的类别过滤 0x808990 没读懂，最可疑）。
- **测**（airev1 / airev0：倒车开 / 关）：两边"离远厂 150 内的坦克数"几乎一样，看不出倒车。
- 给关卡：别指望原版 AI 的坦克受伤会回家修；按"打到死"设计。

## 模拟器怎么做

`simai.Brain.fight` 把队员和视野里的敌人交给模型（私有 `ra3model/ai/tactics.py` 的 `TacticsBlock._team_state`）；撤退下纯移动令回基地，撤退期间攻击战术不重新下令，回来后队伍"准备好"（同分段进攻的判据）再出发。

和台上的已知差别（`tests/test_simai.py` strict xfail）：第一次回家后模拟器只停约 9 秒（台上约 16 秒），第二趟死 1 人（台上一个没死）。模拟器的队伍醒来后出门比台上晚约 8 秒，对拍从出门算起。

模拟器没有进楼、进炮塔和碾压：这几样只在私有模型里有，模拟器的队伍照旧在外面开枪。

没测：伤兵后撤、另两个交战开关（打敌方单位、打战术目标）关掉时。
