# 画面线交接

## 现在在哪

- 第 0 步（DXVK + SAGE-smooth 能否同跑、帧率）做完了，结论在 [rendering.md 第 7 节](../research/rendering.md)。
- 没有正在做的事，没有未提交的改动。下一步等总控/用户定：画面放在逻辑层之后（ADR 0022），第 1 批效果不要顺手做。

## 东西在哪（都在 `work/`，不进 git）

| 路径 | 是什么 |
|---|---|
| `work/render/RA3` | 测试台副本 `work/testbench/RA3` 的硬链接副本（≥1 MB 的非 dll 文件是硬链接，其余是真拷贝）。**只往这里换 DLL**；不要写里面的硬链接文件（和 Steam 那份是同一个文件），换文件先删再建 |
| `work/render/dxvk/` | DXVK 3.1.1 官方包和解压结果，用 `x32/d3d9.dll` |
| `work/render/sage/` | 按 SAGE-smooth c2b3da2 编的 `CnCFpsUnlocker.dll`、`d3dx9_35.dll`、`d3d9.dll` |
| `work/render/tools/make_copy.py` | 重建副本 |
| `work/render/tools/switch.py <配置>` | van30 / sage120 / sage_d3d9 / smooth_dxvk / van_dxvk |
| `work/render/tools/run.sh <配置> [标签]` | 换配置 + 原速跑 `render_war` + 汇总；`RENDER_CHECK=big` 跑重战 |
| `work/render/tools/run_war.py` | 实际跑一局（调测试台 `_cnv_run`，保留帧率日志，按窗口客户区换算点击） |
| `work/render/tools/summary.py <标签>...` | 画面帧均值/最低/5% 分位、逻辑帧率 |
| `work/render/tools/frame_diff.py A B` | 两局同号截帧的逐像素差 |
| `work/render/tools/click_probe.py`、`bare_launch.py`、`start_dbg.py`、`win_scan.py` | 排查用 |
| `work/logs/render_*.log`、`*.shim.log` | 每局结果和每秒帧数 |

任务和检查进了 git：`experimental/cnv/missions/render_bench.py`、`experimental/cnv/checks/render_war.py`（检查 `war`、`big`；mod 名 CampRndrWar、CampRndrBig）。

## 踩过的坑

- `RA3_BENCH_DIR` 必须是**绝对路径**。给相对路径时测试台把游戏的工作目录设成它，`-config` 再按相对路径找就找错了，游戏弹 "DID YOU REMEMBER TO BUILD DATA / Can't open stream data\audio.manifest"（用户看到过这个弹窗）。
- DXVK 让进程感知 DPI：125% 屏上窗口客户区 1024×576，截帧还是 1280×720。测试台的 `harness.click` 按截帧坐标发 PostMessage，会点偏（卡在开局"连接中断"弹窗）。`run_war.py` 里给 `harness.lp` 套了换算；要让共用测试台支持 DXVK，得在 `harness.py` 里做同样的事（归测试台那条线）。
- `run_check.py --keep` 后另开进程调 `bench_stop` 关不掉游戏（状态在原进程里），会留下一局游戏和 `shared/locks/bench.json`。用 `run_war.py`（同一进程里跑完再关）。
- `build.py <任务> --check <检查>` 编完会直接在正式测试台上 8 倍速跑一遍；8 倍速下重战逻辑跟不上（121 秒只有 1497 帧），这不代表原速。
- 别的线的测试台游戏同时在跑时，画面帧会有假的下跌（第一轮）。量帧率前看一眼 `tasklist`，批量日志里记了"other RA3"数。
- 所有 DXVK 局里没有崩溃，没复现 0x3B 蓝屏。

## 如果接着做（建议顺序）

1. 加效果前先量显卡余量：重战时用 `nvidia-smi --query-gpu=utilization.gpu --format=csv -lms 500` 采样，或者开 `DXVK_HUD=fps,frametimes,gpuload`（HUD 会进截帧）。
2. 2b 第 1 批（各向异性、SMAA、GTAO、调色）从 DXVK 源码起步：需要 32 位 MinGW/meson 编 DXVK；每加一项用 `run.sh smooth_dxvk` + `RENDER_CHECK=big` 量一次，和本表对比。
3. 想让测试台常态支持 DXVK：把客户区换算搬进 `harness.py`（交测试台那条线）。
