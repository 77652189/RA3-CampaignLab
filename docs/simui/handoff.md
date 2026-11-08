# 模拟器界面线交接

授权和边界：[ADR 0024](../adr/0024-playable-simulator.md)（对齐优先、不改规则、代码放 `experimental/simui/`）。

## 现状（2026-11-08）

- 启动：`python -I -X utf8 experimental/simui/serve.py a4`，打开 http://127.0.0.1:8724/ （`--open` 自动开浏览器，`--level easy|normal|hard`）。`.claude/launch.json` 里有 `simui`。
- 文件：`experimental/simui/game.py`（后端：`PlaySim` 外挂 + `Session`）、`serve.py`（http.server + JSON）、`index.html`（单文件 canvas）；测试 `tests/test_simui.py`（5 项，约 2.5 分钟）。
- 对齐做法：玩家的点击变成剧本事件元组（派 / 攻击 / 放 / 占领 / 生产），放到 `Sim.events` 的当前 tick，由 `Sim.happen` 执行，和 `plays/<关>.txt` 走同一条路；`Session.tick` 就是 `Sim.run` 的循环体（去掉"两分钟没变化就停"）。`PlaySim.happened` 记下每个执行过的事件，`game.replay()` 喂回去得到同一局（测试守着）。
- 已通：A4 从开场打到结局；Esc 跳过场；1/2/4/8/尽快；按阶段跳（阶段 = `CNV_<关>_Phase_N` 旗，用全程脚本打到旗亮，再丢掉脚本剩下的命令交给玩家，A4 跳第 3 阶段约 17 秒）；赢/输画面带用时；字幕框、对白面板、目标、计数/倒计时、黑边、锁操作、过场镜头跟脚本；配音先找录音（`experimental/simui/voice`、`work/voice`、配音仓库 `RA3-ChineseVoice/work/campaign/{zh,en}/<关>/`），找不到用浏览器朗读中文；`Sim.unmodeled` 和覆盖清单列在右栏，涉及的单位画紫色虚线圈；覆盖清单有未登记项时开局弹警告。
- 16 关都能打开（冒烟：建局、跑 30 秒、出状态）；有全程脚本的是 a1 a3 a4 a6 a7 a8 a9 j7，其余关不能按阶段跳；j4 没有阶段旗。

## 没做到 / 已知缺口

- 没有纯移动：剧本只有"派"（攻击移动），右键就是攻击移动。已向引擎 A 请求加动词，并请 `Sim.point` 认 '@x,y'（现在是外挂里解析的，所以导出的操作只能用 `game.replay` 回放，不能直接给 `simulate()`）。
- 生产出的单位名带 '#'，剧本行写不出来；`/api/replay` 导出的文本只给人看。
- "对照局结局一致"这条可试玩条件界面没检查，只检查了覆盖清单。
- 雾：默认按 `Sim.sees` 隐藏雾里的敌人（"雾"按钮可显示）；小地图、编队、停止/驻守命令没有。
- 跳阶段是重放，不是存档点（`copy.deepcopy(Sim)` 因模块引用失败）；慢的关可考虑缓存。
- 生产只在 a2 验过（兵营出侦察兵）；A4 玩家不生产（脚本用"造"直接放单位）。

## 下一步（推荐顺序）

1. 引擎 A 加了 point/纯移动后：外挂里的 `point` 删掉，右键改纯移动、A+右键攻击移动，导出改成可给 `simulate()` 的剧本。
2. 其余有全程脚本的关各玩一遍找界面问题（a1 a3 a6 a7 a8 a9 j7）。
3. 可选：阶段跳缓存、小地图。
