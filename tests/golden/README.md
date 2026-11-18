# tests/golden：重构改了行为没有

`simrecord` 固定任务逐帧比对；有意改行为时在提交说明写明。 规范见 [testing.md](../../docs/engine/testing.md)。

`test_simrecord_golden.py`：`experimental/cnv/simrecord.py` 的 11 个固定任务，在底版提交和本工作区各录一遍、逐行比，一个任务一条测试。怎么选底版、录到哪、怎么声明有意改行为，写在 `experimental/testbench/golden.py` 开头：

- 底版不进仓库，按提交号现录（一套录制约 130 MB，含原版地图和私有模型的行为，进不了公开仓库）：`GOLDEN_BASE` 指定；否则 `experimental/` 下有没提交的改动就比 HEAD，没有就比 HEAD~1。底版在旁边的工作区 `RA3-CampaignLab-golden` 里录，用本工作区的 `simrecord.py`。
- 录制缓存在 `work/logs/golden/`，按提交号（没提交的按改动的哈希）；第二次只比不录。
- 有意改行为：提交说明里写一行 `Golden-Changed: old_heal_a ai_open`（或 `all`）；没提交时设 `GOLDEN_CHANGED`。声明了的任务不同时记 skip 并带上差异。
- 是回放（`tests/replay_tests.txt`），不进日常挑选；手跑：`python -X utf8 experimental/testbench/golden.py`。工具自己的测试在 `tests/tools/test_golden.py`。
