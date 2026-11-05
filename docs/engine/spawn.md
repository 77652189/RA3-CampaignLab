# 生成与从属单位：修理无人机、矿车、跟着主人的单位

引擎线第 16 轮（2026-11-05），ADR 0019 第二层第 4 批；第 18 轮补了第 2 节的复测和第 5 节。写法照 `script-semantics.md`：**测** = 测试台；**推断，未实测** = 只从资料推出来。

探针 `experimental/cnv/checks/engine_spawn.py`（`cnv_check engine_spawn spawn`），平地探针图上摆玩家的三座盟军战车工厂（加三座电厂，免得缺电）：一座第 12 秒被杀（`NAMED_KILL`），一座同时被删（`NAMED_DELETE`），一座留着做对照；对照工厂北边 170 处一辆守护者坦克、东边 380 处一辆，开局都设成 20% 血；第 12 秒用 `UNIT_KILL_ALL_IN_AREA` 杀近车那一小块地里玩家的一切。运行 `work/testbench/runs/CampSpawnSpawn_mcp_1105_052200`（测试台读数比计时器早约 1 秒）。

## 1. 工厂一出来就有 3 架，工厂死了或被删，无人机当秒全没（测）

- 地图上摆好的战车工厂，开局第一秒读数就是每座 3 架（一次出齐，不是一架一架出）。
- 杀掉的工厂和删掉的工厂，各自的 3 架在同一秒从计数里消失；对照工厂的 3 架一直在。原版这几种建筑都写了"主单位没了，从属单位一起没"（`SpawnedRequireSpawner`）。
- 被杀的工厂没有再造无人机（主单位没了就不补）。

## 2. 按模板数，数不到无人机；要按 KindOf DRONE 数（测）

- `SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER` 和 `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA` 拿 `AlliedWarFactoryRepairDrone` 去数，整局都是 0，而画面里无人机在飞（运行 `…_051912`）。
- 改用 `PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA`（KindOf `DRONE`）就数得到。注意这个条件不分玩家（`contract.kind_counts_in_area`），只在只有一方有无人机时能这么用。
- **不是因为"生成出来的"，是无人机模板本身数不到**（第 18 轮复测，探针 `engine_spawn_count`，运行 `CampCountCount_mcp_1105_064248`）：同一张图上分四块地，按模板数和按 KindOf 数各一遍——工厂生的 3 架无人机：模板 0、KindOf 3；**地图上直接摆的 1 架无人机：模板 0、KindOf 1**；精炼厂生的矿车：模板 1、KindOf 1；地图上直接摆的矿车：模板 1、KindOf 1。`SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER` 也一样：无人机 0，矿车 2（生的、摆的都算）。
- 原因推断：KindOf `DRONE`（原版带 `DRONE` 的 9 个模板也都带 `SUMMONED`；只带 `SUMMONED` 的超音速轰炸机、支援轰炸机一类没测）。模型按"带 `DRONE` 的不进模板计数"算。
- **关卡线该怎么改**：脚本里要数无人机一类（修理无人机、`DRONE`），别按模板数，按 KindOf 数；矿车之类生成出来的普通单位按模板数没问题。

## 3. 无人机只去修 200 左右以内的车（测）

- 近车（工厂中心 170）开局就有 1 架无人机贴上去修（开头 1 秒有 3 架都在那），血量从 20% 涨到第 10 秒的 58%，约每秒 5.5%；远车（380）一直 20%，没有无人机去。
- 和原版数值一致：无人机的跟随距离（`LeashRange`）和找车范围（`AttachUpdate Range`）都是 200（苏联 300）。

## 4. 区域全杀不杀无人机（测）

- `UNIT_KILL_ALL_IN_AREA` 杀死了近车，但贴在近车上的无人机没死（总数仍是 3），近车死后它就离开了那块地。所以这次没量到"死一架、隔多久补一架"。
- 补充间隔原版写的是 10 秒（`SpawnReplaceDelayData`），模型按《将军》的规则算（死后 10 秒，之后的下一次检查补上）。第 5 节实测对上了。

## 5. 无人机打不着，只能被范围伤害炸死；死后正好 10 秒补一架（测）

- **打不着**：修理无人机的 KindOf 是 `AIRCRAFT DRONE NOT_AUTOACQUIRABLE NO_COLLIDE SUMMONED`，没有 `VEHICLE`。按《将军》的规则，空中的东西不是车也不是步兵就谁都瞄不了（`docs/engine/air.md` 第 1 节），再加上 `NOT_AUTOACQUIRABLE` 不会被自动选为目标——所以"摆一辆敌方防空（如只打空中的牛蛙 `SovietAntiAirShip`）打它"这条路走不通（推断，没上测试台试）。
- **炸得死**：探针 `engine_spawn_refill`（运行 `CampFillRefill_mcp_1105_064054`）在两辆被修的残血守护者旁边各摆一架原版会爆炸的米格道具（`S02_ExplodingMig`：1 点血，死时半径 100、1000 伤害，敌我都伤），第 8、11 秒按名字杀掉米格。爆炸把车和贴在车上修理的无人机一起炸死（无人机 200 血，没有护甲）。
- **补充间隔**：总数 3 → 第 8 秒 2 → 第 11 秒 1 → **第 18 秒 2 → 第 21 秒 3**，两次都是死后 10 秒补上（测试台读数 1 秒一格）。
- **关卡线可以怎么用**：想让玩家"打掉无人机"只能给范围伤害（炮击、爆炸道具、超武）；要无人机不可摧毁就别在它附近放范围伤害。

## 没测的

- 被删掉的从属单位补不补（《将军》的规则是不补：删除不算死，主单位收不到消息）；
- 工厂缺电、被瘫痪时无人机会不会被杀（原版写了 `KillSpawnsOnDisabled`）、被占领时会不会被杀；
- 矿厂只出一辆矿车、矿车死了不补（`IsOneShotData`）；
- 锤式坦克（Hammer）吸航母得到的无人机：主人死了它跟着死（`DieOnMastersDeath`），它死了吸取升级被撤（`SlaveWatcherBehavior`）。
