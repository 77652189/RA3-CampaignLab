# 关卡规模随战役位置怎么变（原版 40 关）

由 [scale_measure.py](scale_measure.py) 生成，原始数据 [scale.json](scale.json)。每一项怎么量的，见脚本开头。"时长"量不出来（取决于玩家），用段数和局面变化代替。

## 按位置汇总（中位数，括号里是最少～最多）

| 位置 | 关数 | 主目标 | 段（目标分几批亮） | 地图变化 | 局面变化 | 主目标的动词种数 | 玩家有基地 | 有英雄 | 有倒计时 |
|---|---|---|---|---|---|---|---|---|---|
| 前期 | 13 | 4（2～5） | 3（1～4） | 1 | 3（0～5） | 2 | 5 | 3 | 5 |
| 中期 | 14 | 3.5（2～6） | 2.5（1～5） | 2 | 4（1～8） | 2.5 | 10 | 4 | 6 |
| 后期 | 13 | 4（3～7） | 3（2～5） | 2 | 4（1～8） | 3 | 10 | 2 | 7 |

## 下四分位（四分之三的关至少有这么多）

| 位置 | 主目标 | 段 | 地图变化 | 局面变化 | 主目标的动词种数 | 玩家指挥的兵种数 |
|---|---|---|---|---|---|---|
| 前期 | 3 | 1 | 0 | 0 | 2 | 1（中位 2） |
| 中期 | 3 | 2 | 1 | 2 | 2 | 1.25（中位 3） |
| 后期 | 3 | 2 | 2 | 3 | 2 | 1（中位 2） |

## 每关

| 关 | 位置 | 主目标 | 段 | 地图变化 | 基地 | 主目标的动词 | 中途给兵（次） | 兵种数 | 英雄 | 倒计时 | 局面变化 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| camp_a01_brightonbeach_smith | 前期 | 4 | 1 | 0 | 有 | Eliminate | 0 | 2 | — | 有 | 0 |
| camp_a02_cannes_smith | 前期 | 5 | 4 | 1 | 有 | Get / Save / Sink / Wipe | 0 | 3 | AlliedCommandoTech1 | — | 4 |
| camp_a03_heidelberg_smith | 前期 | 5 | 4 | 1 | 有 | Destroy / Escort | 0 | 6 | AlliedCommandoTech1 | — | 4 |
| camp_a04_gibraltar_hayes | 中期 | 3 | 3 | 3 | 有 | Destroy / Recover | 0 | 3 | AlliedCommandoTech1 | — | 5 |
| camp_a05_northsea_white | 中期 | 4 | 3 | 6 | 有 | Capture / Destroy / Protect | 5 | 3 | alliedcommandotech1 | 有 | 8 |
| camp_a06_mountrushmore_white | 中期 | 3 | 3 | 3 | 有 | Destroy / Eliminate | 0 | 2 | AlliedCommandoTech1 | — | 5 |
| camp_a07_tokyoharbor_davis | 后期 | 4 | 2 | 2 | 无 | Hold / Take | 1 | 1 | — | 有 | 3 |
| camp_a08_havana_rao | 后期 | 5 | 3 | 2 | 有 | Destroy / Do / Investigate / Locate | 0 | 2 | — | 有 | 4 |
| camp_a09_leningrad_rao | 后期 | 5 | 2 | 2 | 有 | Clear / Destroy / Unpack | 10 | 2 | — | 有 | 3 |
| camp_j01_russianvillage_white | 前期 | 4 | 3 | 2 | 无 | Bring / Destroy | 5 | 5 | — | — | 4 |
| camp_j02_stalingrad_stewart | 前期 | 3 | 3 | 1 | 有 | Defend / Destroy / Establish | 0 | 1 | — | 有 | 3 |
| camp_j03_odessa_stewart | 前期 | 3 | 2 | 1 | 有 | Destroy / Escort | 1 | 2 | — | — | 2 |
| camp_j04_pearlharbor_davis | 中期 | 4 | 1 | 1 | 有 | Defend / Destroy | 0 | 8 | — | 有 | 1 |
| camp_j05_deepocean_davis | 中期 | 4 | 2 | 1 | 无 | Destroy / Protect / Stop | 0 | 2 | — | 有 | 2 |
| camp_j06_losangeles_white | 中期 | 2 | 2 | 1 | 有 | Capture / Clear | 0 | 3 | — | — | 2 |
| camp_j07_yokohama_stewart | 后期 | 3 | 3 | 2 | 有 | Destroy / Hold / Retake | 8 | 5 | JapanCommandoTech1 | 有 | 4 |
| camp_j08_kremlin_stewart | 后期 | 4 | 2 | 3 | 有 | Await / Destroy / The | 0 | 2 | — | 有 | 4 |
| camp_j09_amsterdam_bass | 后期 | 5 | 3 | 4 | 有 | Destroy | 18 | 8 | JapanCommandoTech1 | — | 6 |
| camp_s01_leningradcanals_rao | 前期 | 4 | 1 | 0 | 无 | Secure / Train | 0 | 2 | SovietCommandoTech1 | 有 | 0 |
| camp_s02_krasna45_rao | 前期 | 3 | 1 | 0 | 无 | Get | 4 | 1 | — | — | 0 |
| camp_s03_vladivostok_davis | 前期 | 5 | 3 | 1 | 无 | Clear / Construct / Destroy | 0 | 2 | — | — | 3 |
| camp_s04_geneva_bass | 中期 | 4 | 2 | 3 | 有 | Destroy / General | 0 | 3 | — | — | 4 |
| camp_s05_mykonos_smith | 中期 | 6 | 4 | 2 | 有 | Capture / Destroy / Expand / Hold | 0 | 0 | — | 有 | 5 |
| camp_s06_iceland_bass | 中期 | 3 | 2 | 4 | 有 | Destroy / Eliminate | 0 | 6 | — | — | 5 |
| camp_s07_mountfuji_white | 后期 | 7 | 5 | 3 | 有 | Assassinate / Create / Destroy / Kill | 4 | 5 | — | — | 7 |
| camp_s08_easterisland_stewart | 后期 | 5 | 4 | 5 | 有 | Build / Destroy / Stop | 0 | 0 | — | 有 | 8 |
| camp_s09_newyork_rao | 后期 | 3 | 3 | 2 | 有 | Destroy / Eliminate | 0 | 4 | — | — | 4 |
| camp_ep01_a01_igaprefecture_davis | 前期 | 5 | 4 | 2 | 无 | Defeat / Escort / Find / Freeze / The | 0 | 0 | — | 有 | 5 |
| camp_ep01_a02_osaka_white | 中期 | 3 | 1 | 4 | 有 | Deactivate | 7 | 10 | alliedcommandotech1 | — | 4 |
| camp_ep01_a03_miyako_stewart | 后期 | 3 | 3 | 2 | 有 | Defeat / Set | 0 | 3 | — | — | 4 |
| camp_ep01_j01_sakhalin_smith | 前期 | 5 | 4 | 0 | 无 | Capture / Commander / Destroy / Rendezvous | 0 | 0 | — | — | 3 |
| camp_ep01_j02_okiislands_smith | 中期 | 6 | 2 | 0 | 无 | Garrison / Sink / The / Unpack | 0 | 0 | — | — | 1 |
| camp_ep01_j03_vladivostok_smith | 后期 | 3 | 2 | 2 | 无 | Defeat / Eliminate | 0 | 0 | — | — | 3 |
| camp_ep01_s01_romania_stewart | 前期 | 3 | 1 | 0 | 无 | Rendezvous | 0 | 4 | — | 有 | 0 |
| camp_ep01_s02_murmansk_white | 中期 | 3 | 3 | 1 | 有 | Crush / Regroup / Scout | 0 | 6 | — | 有 | 3 |
| camp_ep01_s03_yucatan_stewart | 中期 | 3 | 3 | 0 | 无 | Clear / Crush / Destroy | 0 | 1 | — | 有 | 2 |
| camp_ep01_s04_warbotisland_white | 后期 | 3 | 3 | 3 | 有 | Destroy / Establish / Stop | 0 | 6 | — | 有 | 5 |
| camp_ep01_y01_facility_rao | 前期 | 2 | 2 | 0 | 无 | Access / Escape | 0 | 0 | — | — | 1 |
| camp_ep01_y02_blacksite_davis | 中期 | 4 | 5 | 2 | 无 | Escape / Head / Objective_B1_FreePrisoners / Sink / Utterly | 0 | 1 | — | — | 6 |
| camp_ep01_y03_compound_rao | 后期 | 4 | 2 | 0 | 无 | Gain / Kill | 0 | 1 | — | — | 1 |
