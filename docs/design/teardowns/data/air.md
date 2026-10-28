# 空军：玩家能不能造飞机、敌人据点有没有防空（每关一行）

由 [air_measure.py](air_measure.py) 生成，口径见脚本开头。"开局禁"：玩家阵营的机场在开局被禁，而且没有一种飞机开局可造；"后来放开"：之后某个脚本允许造的机场或飞机。

| 关 | 阵营 | 玩家有基地 | 玩家空军（开局） | 后来放开 | 敌方防空（预摆） | 有防空的敌方据点 / 据点数 |
|---|---|---|---|---|---|---|
| a01_brightonbeach | allied | — | （没基地，造不了） | — | 0 | 0 / 2 |
| a02_cannes | allied | 有 | 开局禁 | antigroundaircraft | 0 | 0 / 6 |
| a03_heidelberg | allied | — | （没基地，造不了） | — | 28 | 1 / 3 |
| a04_gibraltar | allied | 有 | 开局禁 | supportaircraft | 7 | 1 / 4 |
| a05_northsea | allied | — | （没基地，造不了） | bomberaircraft | 7 | 3 / 6 |
| a06_mountrushmore | allied | — | （没基地，造不了） | — | 0 | 0 / 3 |
| a07_tokyoharbor | allied | 有 | 不限 | PlayerTech AirPower | 8 | 2 / 7 |
| a08_havana | allied | — | （没基地，造不了） | — | 18 | 4 / 4 |
| a09_leningrad | allied | — | （没基地，造不了） | — | 15 | 3 / 7 |
| up-a01_igaprefecture | allied | 有 | 不限 | — | 3 | 0 / 8 |
| up-a02_osaka | allied | 有 | 不限 | — | 11 | 1 / 1 |
| up-a03_miyako | allied | 有 | 不限 | — | 5 | 1 / 4 |
| up-j01_sakhalin | japan | — | （没基地，造不了） | — | 17 | 3 / 7 |
| up-j02_okiislands | japan | — | （没基地，造不了） | — | 8 | 2 / 5 |
| up-j03_vladivostok | japan | 有 | 不限 | — | 34 | 3 / 3 |
| up-s01_romania | soviet | — | （没基地，造不了） | — | 10 | 1 / 4 |
| up-s02_murmansk | soviet | 有 | 部分禁 | — | 5 | 1 / 5 |
| up-s03_yucatan | soviet | — | （没基地，造不了） | — | 9 | 2 / 5 |
| up-s04_warbotisland | soviet | 有 | 开局禁 | airfield、antigroundaircraft、bomberaircraft、fighteraircraft | 2 | 1 / 8 |
| up-y01_facility | None | — | （没基地，造不了） | — | 2 | 0 / 5 |
| up-y02_blacksite | None | — | （没基地，造不了） | — | 2 | 0 / 1 |
| up-y03_compound | None | — | （没基地，造不了） | — | 4 | 0 / 7 |
| j01_russianvillage | japan | — | （没基地，造不了） | — | 11 | 2 / 4 |
| j02_stalingrad | japan | 有 | 部分禁 | — | 2 | 1 / 2 |
| j03_odessa | japan | 有 | 部分禁 | — | 6 | 1 / 5 |
| j04_pearlharbor | japan | 有 | 部分禁 | — | 2 | 1 / 1 |
| j05_deepocean | japan | 有 | 不限 | — | 4 | 1 / 3 |
| j06_losangeles | japan | 有 | 不限 | — | 2 | 1 / 7 |
| j07_yokohama | japan | 有 | 不限 | — | 0 | 0 / 4 |
| j08_kremlin | japan | 有 | 不限 | — | 0 | 0 / 4 |
| j09_amsterdam | japan | 有 | 不限 | — | 18 | 4 / 10 |
| s01_leningradcanals | soviet | — | （没基地，造不了） | — | 26 | 3 / 6 |
| s02_krasna45 | soviet | — | （没基地，造不了） | — | 7 | 2 / 4 |
| s03_vladivostok | soviet | — | （没基地，造不了） | — | 0 | 0 / 3 |
| s04_geneva | soviet | 有 | 开局禁 | — | 0 | 0 / 4 |
| s05_mykonos | soviet | 有 | 部分禁 | fighteraircraft | 0 | 0 / 4 |
| s06_iceland | soviet | 有 | 部分禁 | bomberaircraft | 5 | 2 / 5 |
| s07_mountfuji | soviet | — | （没基地，造不了） | — | 6 | 0 / 5 |
| s08_easterisland | soviet | 有 | 不限 | — | 38 | 5 / 5 |
| s09_newyork | soviet | — | （没基地，造不了） | — | 18 | 2 / 5 |
| A4 | allied | 有 | 不限 | — | 0 | 0 / 2 |
| A5 | allied | 有 | 不限 | — | 0 | 0 / 1 |
| A7 | allied | 有 | 不限 | — | 2 | 1 / 1 |
| A8 | allied | — | （没基地，造不了） | — | 3 | 0 / 0 |
| J3 | allied | 有 | 不限 | — | 0 | 0 / 1 |
| J4 | allied | — | （没基地，造不了） | — | 0 | 0 / 0 |
| J5 | allied | 有 | 不限 | — | 0 | 0 / 0 |
| J7 | allied | 有 | 不限 | — | 0 | 0 / 1 |
| S2 | allied | — | （没基地，造不了） | — | 0 | 0 / 0 |
| S5 | allied | 有 | 不限 | — | 0 | 0 / 1 |
| S6 | allied | 有 | 不限 | — | 0 | 0 / 0 |

## 汇总

| | 原版 | 我们 |
|---|---|---|
| 玩家没有基地的关（造不了飞机） | 19 | 3 |
| 有基地的关，空军开局开局禁 | 4 | 0 |
| 有基地的关，空军开局部分禁 | 6 | 0 |
| 有基地的关，空军开局不限 | 11 | 8 |
| 有基地的关，后来放开空军 | 6 | 0 |
| 敌方预摆防空（中位数） | 5.5 | 0 |
| 有防空的敌方据点 | 54 / 186 | 1 / 7 |
