# 原版关验收题 1：盟军第一关，开局小队走到指定点要多久（2026-11-08）

[ADR 0026](../adr/0026-engine-first-retail-inventory.md) 第 2 条的第一道题，走"测试台像素路线"（原版关不写录像，也没有计数器，见 [handoff-phase4.md](handoff-phase4.md) 第 2 条）。

## 题目

起无 mod 的原版游戏进盟军第一关（`camp_a01_brightonbeach_smith`），开局镜头不动：框选开局小队（4 个维和步兵 + 2 条警犬），在**世界坐标 (505, 1577)**（草坪东边的马路上）右键移动。量：小队中心离目标 30 单位内的任务秒；停下时的位置。

命令：`python -I -X utf8 experimental/testbench/retail_q1.py`（脚本 [retail_q1.py](../../experimental/testbench/retail_q1.py)，输出 `work/testbench/retail_q/a01_q1.json` 和帧存档）。

## 答案（游戏里量的，跑了 3 次）

| 量 | 值 |
|---|---|
| 下令时刻 | 任务第 2.6 秒 |
| 小队中心进入目标 30 单位内 | 第 5.5～5.6 秒（采样间隔 0.8 秒，所以"走路用时 ≤ 3.0 秒"，约 2.5 秒） |
| 小队中心最终位置 | 离目标 19～23 单位（六个单位围着点站开，不会重合） |
| 走过的路 | 从 (383, 1638) 到 (487, 1585)，约 120 单位，折合约 50 单位/秒 |

模拟器要复现的是"走路用时 2.5～3 秒、停在目标附近"。模拟器还不能玩这张图，对拍留给引擎线的录像比对工具；这一行先当原版数据。

## 这道题顺带做通的事（原版图的世界坐标）

- 原版图按名读：`maprender.load('camp_a01_brightonbeach_smith')`（短名或 `档案.big::包内路径`），`calib.Ground` 读它的地形（这张图是平地，没有高度修正）。
- 边界读地图本身：`harness.retail_borders`（这张图两个：全图 4750×4750，可玩区 2700×2510，小队开局在后者，小地图只画后者）。
- 相机：原版开局镜头是朝北的针孔相机（俯角约 44°，焦距约 1069 像素，看着 (384, 1671)），不是岛图那台。标定数据在 [retail_cam/camp_a01_brightonbeach_smith.json](../../experimental/testbench/retail_cam/camp_a01_brightonbeach_smith.json)：12 个栅栏柱顶 + 小地图视野梯形四角，拟合残差 2.8 像素。拟合命令 `python -I experimental/testbench/calib.py fit_retail <图名>`。
- 小地图跳转后的平移模型也对：跳到三处（900,2200）（1500,1500）（400,3000）各抓一帧，用桌子、树、灯柱、围栏的位置对，误差约 5～10 像素。
- `bench_start(mod="")` 现在读这张图的标定；`retail_map` 参数可指定别的图，**别的图没有标定文件时会在日志里说"没标定"**，世界坐标点击不可信。

## 没做的

- 标定只有这一个相机状态（开局镜头）。脚本里 `ZOOM_CAMERA` / `ROTATE_CAMERA` 之后相机变了，要按那时的画面再拟合一次；别的关同理（做法见上，找几个已知位置的栅栏 / 建筑角，读帧上的像素）。
- `bench_mcp.py` 的 MCP 服务进程是旧代码，**重启后**才有 `retail_map` 参数和原版图标定（直接用脚本不受影响）。
- 带阶段目标的题（"消灭布莱顿的苏军"何时完成、两个自带计数器 `A01_Javelin_Counter` / `A01_IFV_Counter` 是否亮）还没做，下一道题做。
