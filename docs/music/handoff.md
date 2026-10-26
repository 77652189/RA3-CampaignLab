# 音乐线交接

会话："游戏音乐生成系统"。进度状态只在 [plan.md](../plan.md)「游戏音乐」那一行，这里不重复。为什么这么走见 [ADR 0005](../adr/0005-own-pathfinder-music.md)。

## 当前目标

我们自己的音频、自己从零写的曲谱图都能用了，关卡 mod 也能带上它们。接口是 `parts.Mission.music`，由音乐线的 `pack.py` 提供，和内容会话商定（2026-10-25）。跳转规律见 `pfdx.py` 开头 `PREP` 一条：带 PREP 的事件立刻切；不带的要等当前小段放完，再走路由表的过渡。现在的目标：**定作曲路线**。

## 下一步

1. 定作曲路线（AI 生成 / 代码写谱渲染 / 两者结合），先用 A4 一关做样品给用户试听。剧情与关卡见 [outline.md](../story/outline.md) 第四节、[plans/a4.md](../story/plans/a4.md)「节拍」。写谱时按跳转规律安排：
   - 段落切成几秒长的小段，因为不带 PREP 的跳转要等小段放完。
   - 卡准时机的剧情点用带 PREP 的事件。
   - 段落之间的过渡写成路由表里的过渡段。
2. 样品通过以后，给 A4 写正式曲谱图：`ownmap.Builder` 搭段落；关卡脚本发事件，用 `Mission.music` 公开的事件名（`parts.contract` 会检查拼写）。新的 mod 名字不超过 15 个字符、只用字母和数字（plan.md「踩过的坑」里"mod 名最多 15 个字符"那条）。
3. 没做的：战况状态机（优势 / 劣势自动切换，`PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM`）怎么接我们的曲谱图，还没在游戏里试过。

已知能用的音频格式：EA-XAS，22.05 kHz 单声道和 44.1 kHz 立体声都可以；同一个 `.mus` 里可以和原版的 EALayer3 段混放；条目编号和校验码可以用我们自己的（`mus.pack`）。不需要自己写 EALayer3 编码器。

## 必读

- 格式：`experimental/music/pfdx.py` 和 `mus.py` 开头的说明（以代码为准）。
- 原版状态机：`sdk/RA3ModSDK3/SageXML/PathMusic/StandardPathMusicGameDynamicState.xml`（战况条件）、`ScriptPathMusicEvents.xml`（关卡脚本用的事件）；地图脚本动作 `PATH_MUSIC_PLAY_EVENT` / `PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM`（`experimental/campaign/script_catalog.json`）。
- 注入：`experimental/campaign/splice_assets.py` 开头（为什么要拼进 static 流）。
- 本地数据（不进 git）：`work/music/retail/`（`extract.py` 取出的原版曲谱图和音轨、`decode_retail.py` 解出的 715 段 wav、`listen.py index` 建的指纹 `index.npz`、`event_hashes.json`），`work/music/probe/`（录音和测试台日志）。

## 验证方式

- 离线：`python -m pytest tests/test_pfdx.py tests/test_mus.py tests/test_tracer.py tests/test_ownmap.py`。
- 游戏里：`python -I -X utf8 experimental/music/bench_listen.py 60 <skudef 或 retail> ...`（每轮之间自动隔 20 秒，只输出文字报告；录音时会一直告诉游戏"你在前台"，否则它不放音乐）。加 `--nav <任务秒数>` 就从菜单一路点进第一关，报告里列出每一步菜单操作。原版音乐看 `retail:` 行（段号 @ 段内秒数），示踪音看 `tracer:` 行（`ownmap.spy` 的段号 = 事件序号）。量跳转延迟：`python -I -X utf8 experimental/cnv/build.py music`，然后 `bench_listen.py --nav 90 150 <CampMusic 的 skudef>`，最后 `python -I -X utf8 experimental/music/timing.py work/music/probe/CampMusic_1.0.wav`。预期的播放顺序用 `pfdx.walk(map, 节点)` 离线算。

## 动手前

- 测试台和内容会话（"红色警戒3 游戏内容与工具链"）共用：先发消息约时间，用完回一声；`run_bench.ps1` 自己拿锁。用之前单独查一下红警3有没有在运行。
- 长时间的显卡任务（音乐生成）开跑前先问用户要不要限流。

## 硬约束原文

- 用户 2026-10-25（选路线 B 时）："代码开源还是不要抱多大希望，靠自己做出来的才是可靠的"
- 用户 2026-10-25（提需求时）："作为游戏音乐，你的创作最需要做的是符合剧情和情景，好的音乐对营造氛围感来说是至关重要的"
