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

## 模拟器怎么做

`simai.Brain.fight` 把队员和视野里的敌人交给模型（私有 `ra3model/ai/tactics.py` 的 `TacticsBlock._team_state`）；撤退下纯移动令回基地，撤退期间攻击战术不重新下令，回来后队伍"准备好"（同分段进攻的判据）再出发。

和台上的已知差别（`tests/test_simai.py` strict xfail）：第一次回家后模拟器只停约 9 秒（台上约 16 秒），第二趟死 1 人（台上一个没死）。模拟器的队伍醒来后出门比台上晚约 8 秒，对拍从出门算起。

没测：进驻、伤兵后撤、另两个交战开关（打敌方单位、打战术目标）关掉时。
