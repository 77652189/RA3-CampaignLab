# tests/conformance：和游戏一致吗

不手写测试：台上读数写进台子旁边的读数数据，一致性跑器每个场景跑一次、核对全部读数。 规范见 [testing.md](../../docs/engine/testing.md)。

跑器 `test_readings.py`：读 `experimental/cnv/checks/*.readings.toml`（格式见 `experimental/cnv/readings.py` 开头），共用场景的读数归一组，一组一条测试、每个场景只跑一次。跑器自己的测试在 `tests/tools/test_readings_format.py`。
