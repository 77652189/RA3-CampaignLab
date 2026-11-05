# 生成与从属单位：修理无人机、矿车、跟着主人的单位

引擎线第 16 轮（2026-11-05），ADR 0019 第二层第 4 批。写法照 `script-semantics.md`：**测** = 测试台；**推断，未实测** = 只从资料推出来。

探针 `experimental/cnv/checks/engine_spawn.py`（`cnv_check engine_spawn spawn`），平地探针图上摆玩家的三座盟军战车工厂（加三座电厂，免得缺电）：一座第 12 秒被杀（`NAMED_KILL`），一座同时被删（`NAMED_DELETE`），一座留着做对照；对照工厂北边 170 处一辆守护者坦克、东边 380 处一辆，开局都设成 20% 血；第 12 秒用 `UNIT_KILL_ALL_IN_AREA` 杀近车那一小块地里玩家的一切。运行 `work/testbench/runs/CampSpawnSpawn_mcp_1105_052200`（测试台读数比计时器早约 1 秒）。

## 1. 工厂一出来就有 3 架，工厂死了或被删，无人机当秒全没（测）

- 地图上摆好的战车工厂，开局第一秒读数就是每座 3 架（一次出齐，不是一架一架出）。
- 杀掉的工厂和删掉的工厂，各自的 3 架在同一秒从计数里消失；对照工厂的 3 架一直在。原版这几种建筑都写了"主单位没了，从属单位一起没"（`SpawnedRequireSpawner`）。
- 被杀的工厂没有再造无人机（主单位没了就不补）。

## 2. 按模板数，数不到无人机；要按 KindOf DRONE 数（测）

- `SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER` 和 `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA` 拿 `AlliedWarFactoryRepairDrone` 去数，整局都是 0，而画面里无人机在飞（运行 `…_051912`）。
- 改用 `PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA`（KindOf `DRONE`）就数得到。注意这个条件不分玩家（`contract.kind_counts_in_area`），只在只有一方有无人机时能这么用。
- **关卡线该怎么改**：脚本里要数生成出来的单位（修理无人机、甲板炮塔一类），别按模板数。为什么按模板数不到没查（推断：从属单位不记在玩家的"单位表"里）。

## 3. 无人机只去修 200 左右以内的车（测）

- 近车（工厂中心 170）开局就有 1 架无人机贴上去修（开头 1 秒有 3 架都在那），血量从 20% 涨到第 10 秒的 58%，约每秒 5.5%；远车（380）一直 20%，没有无人机去。
- 和原版数值一致：无人机的跟随距离（`LeashRange`）和找车范围（`AttachUpdate Range`）都是 200（苏联 300）。

## 4. 区域全杀不杀无人机（测）

- `UNIT_KILL_ALL_IN_AREA` 杀死了近车，但贴在近车上的无人机没死（总数仍是 3），近车死后它就离开了那块地。所以这次没量到"死一架、隔多久补一架"。
- 补充间隔原版写的是 10 秒（`SpawnReplaceDelayData`），模型按《将军》的规则算（死后 10 秒，之后的下一次检查补上）；**推断，未实测**，下一轮用敌方防空打无人机来量。

## 没测的

- 被删掉的从属单位补不补（《将军》的规则是不补：删除不算死，主单位收不到消息）；
- 工厂缺电、被瘫痪时无人机会不会被杀（原版写了 `KillSpawnsOnDisabled`）、被占领时会不会被杀；
- 矿厂只出一辆矿车、矿车死了不补（`IsOneShotData`）；
- 锤式坦克（Hammer）吸航母得到的无人机：主人死了它跟着死（`DieOnMastersDeath`），它死了吸取升级被撤（`SlaveWatcherBehavior`）。
