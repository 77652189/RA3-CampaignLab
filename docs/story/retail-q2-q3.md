# 原版关验收题 2、3：盟军第二关（戛纳）、第三关（海德堡），开局不操作看目标时间线（2026-11-08）

接 [retail-q1-a01.md](retail-q1-a01.md)。两关都**不派兵**（没有点击，所以这两题不需要相机标定；要派兵的题再按 retail-q1 的做法拟合相机）。量的是"开局任务目标列表什么时候出现几条"，台上用任务菜单（暂停就是它）逐帧读，模拟器用 `experimental/cnv/retail.py`。

## 怎么进这两关（关键发现）

原版战役是线性的：世界地图的"继续"只通向第一关，第二关要先打赢第一关。`bench_start(mod="")` 进不了 a02 / a03。走的路：**只带一关的战役壳**——`CNV_SHELL_NAME=CampShRetail python -I -X utf8 experimental/cnv/build.py a4 --shell` 生成 `Documents\Red Alert 3\Mods\CampShRetail`（名字是新的，不覆盖用户的 `CampShell`；`CampShell` 本身 9 关都是我们的草稿，它的第 2 槽不是戛纳）。这个壳里第 1～9 槽里没造的槽放的是原版自己的地图和脚本。`harness.shell_steps(槽号)` 走章节列表进槽。脚本：[retail_q2.py](../../experimental/testbench/retail_q2.py)（`python -X utf8 experimental/testbench/retail_q2.py <2|3> --until 60 --step 1`，输出 `work/testbench/retail_q/a0N_idle.json` 和帧存档）；读目标条数：[retail_q2_read.py](../../experimental/testbench/retail_q2_read.py)（目标列表框里绿字像素数，≈1011 一条、≈1789 两条）。

注意：壳里第 4 槽是我们自己的 a4；战役壳给每槽换了关名（"坝上风云"等占位名），目标文字、地图、脚本是原版的。

## 第二题：a02 戛纳（`camp_a02_cannes_smith`）

| 量 | 台上（游戏） | 模拟器 |
|---|---|---|
| 目标列表为空 | 任务第 0～15.6 秒 | 开场目标一个个被脚本置完成，0:26 才有"亮出" |
| 第一条出现 | 15.6～16.9 秒之间（"让间谍进入这些港口建筑物"） | 0:26 亮出 `A02_Objective_2`，0:31 亮出 `A02_Objective_1` |
| 第二条出现 | 19.7～21.1 秒之间（"解救盟军的领导者"） | （同上，较晚） |

台上时间是 bench 任务秒，采样间隔约 1.4 秒。结论：**模拟器比游戏晚约 10 秒亮目标，顺序也像是反的**（哪个名字对应哪句话还没核，不下断言）。模拟器的开场"锁住操作"0:00～0:20，台上目标 16 秒就出现了，说明开场片的真实时长也要对。没做的：目标完成时间、关键事件（需要派兵）。

## 第三题：a03 海德堡（`camp_a03_heidelberg_smith`）

| 量 | 台上（游戏） | 模拟器 |
|---|---|---|
| "护送基地车"目标 | 第 3.2 秒（第一个采样）就在，之后 70 秒一直是 1 条 | **一直没亮**，推到 2:06 判"卡住" |

原版脚本 `Intro Cine - Part 01` 设了 `TIMER - Intro Cine Part 02 Go`（12 秒），Part 02 再设 Part 03（5 秒），Part 03 设 `Show Objective 01`（1 秒），每个脚本的条件另有 `PLAYER_IS_HUMAN_OR_AI_PERSONALITY('Player_2','Human')` 的旁路。模拟器里 Part 01 跑了（锁住操作、全图揭开），但 12 秒的计时到点后什么都没发生；游戏里 3 秒内就走完整条链（看起来旁路成立，或开场被跳过，没核）。**这是对拍不上、归引擎 A 的一条**：(1) 查 sim 里 12 秒计时为什么不触发 Part 02；(2) 查 Player_2 在原版战役里读 `Human` 的真实值（模拟器按"没有 AI = Human"，a03 里 Player_2 被交给了遭遇战 AI，所以读 false）。

## 其它

- 模拟器读不了的（`retail.py` 报出）：a02：`AlliedInfiltrationInfantryDisguiser` 武器读成没有武器、`PLAYER_SPECIAL_POWER_AVAILABILITY`；a03：`OBJECTLIST_ADDOBJECTTYPE`×5、`CAMERA_LETTERBOX_BEGIN_WITH_RADAR`、`EVA_SET_ENABLED_DISABLED`。
- 另试了 j01 / s01：j01 能跑，s01 在 `sim.py:1772` 报 `KeyError: 'AREA - P2 Delete Aircraft'`（区域名带空格 / 大小写？载入器没读到那个区域），归引擎 A。
- 题 2、3 都只比"开局目标时间线"，没有结局：要比结局得有人打这两关（派兵的题要相机标定）。
