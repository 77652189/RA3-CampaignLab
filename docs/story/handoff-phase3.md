# 关卡线·ADR 0016 第 3 阶段交接（2026-11-04，第八个会话，29 万上下文时写）

总控令（local_79408d22）：四个出口 K1 台词、K2 挂点、K5 镜头、K6 编组命令从源头做实，每个出口三样：一个出口、`contract.py` 里一条产物规则、`tests/test_architecture.py` 里一个守卫；顺手改 `model.merged`。做完每类跑 `fingerprint.py record p3_k<N>` 并和上一次比，`docs/issues.md` 对应项标"修了待验"（依据写"产物规则全关通过"＋规则名；"验过"只能独立验收标）。不许改 plan.md、ADR、HANDOFF.md，不许删文件。跑指纹时不要同时做别的构建；外壳线的视频包 video.xml 可能并发写，指纹里 video.xml 对不上先不算我的。

## 已做完

- **K1 + K2**，提交 645db93。唯一队列在 `cnv/ctx.py` 的 `Talk`：台词只"举旗要说"（`Want k`），`Enq k` 排到本档队尾（计数器 `Q`、位置 `Pos k`），`Say k` 在地板空且排第一时播，`Shift` 保位置。三档（总控 11-04）：结局句由结局脚本自己说（`ctx.ending_gate/ending_begin/final`，等地板空再说，同帧结束，排队的句子丢在任务结束里）；功能句（计划里写 `功能: 是`，设备和手写关默认功能）永不丢、排在闲话前；闲话等超过 `CHAT_LIFE`=10 秒丢，丢了记 `CNV_<tag>_Dropped`。规则里的 `失败` 动作现在也算结局。产物规则 `contract.said_outside_the_outlet`（G3b，放行结局脚本）、`said_lines_kept`；测试 `tests/test_talk_queue.py`（sim 跑顺序、分档、过期、结局）。issues.md 的 I1、I2 已标修了待验。
- **A4 标注**（`docs/story/plans/a4.md` 规则部分 26 句标了 `功能: 是`）。sim 里 A4 实际：播 10 句，丢 8 句闲话（总控要的名单）：交还控制六句里的后四句（"……长官，会场有三条街。""雪祭照常开放，号角照常吹。""是。札幌人赏雪，比车里装的要紧多了。""三条街都通大路，地道口加固过，打不坏。"）、"游客在鼓掌。他们当这是节目。""二号广场的冰雕也裂了。下一声，三条街一起来。"，以及早期的一两句。功能句积压：`号角响了！`排了 14 秒才播；结局前 `车被劫了…` 两句还在排，被结局截掉。交还控制那一刻同时有 3 句功能句（冰幕工兵提示、下一声号角、冰只撑半分钟）排在前面，占去 13 秒，所以故事六句只播得出两句——策划线复核时可以考虑把其中一两句移出这一刻。
- **model.merged**：`if test.counters and m.countdowns and 总数 > 4`（与 `contract.observes` 一致）。已改，未单独提交，随 K5 一起。
- **K5 已提交**（指纹 p3_k5 对 p3_k1q：三个目标各只有 camp_cnv01_probe 的 map / map.bin / map.imp / map.manifest / map.relo 变了，无视频文件；pytest 397 过 1 跳过；G10 守卫测试已写）。路点名只能用字母数字和空格（带逗号地图校验失败）：`plan.py` 的 `view_point` 把镜头点夹进"当时生效的边界"里再缩进半屏（`VIEW_HALF`=(950, 540)，来自 sapporo 'view start' 的注释"屏幕约 1900 宽"，**这个数还没在游戏里量过**）；过场用所在段的边界（`border_at`），规则里的镜头取全关用过的边界的交集；发布成路点 `CNV <tag> Cam <site> <x>,<y>`，范围登记在 `Mission.views`；产物规则 `contract.camera_outside_the_view`（G10）。G10 守卫测试在 `tests/test_architecture.py`（`test_g10_every_camera_move_aims_at_a_view_point`）。A4 的结果（`cam_probe` 打出来的）：走廊边界下 plaza 2 的镜头点从 (2830,2135) 夹到 (2250,2240)；"西于运河"段的 harbour 镜头（4030,2500）夹到 (2690,2500)，说明那一段本来镜头指向的港口在边界外——要告诉策划线复核这两处。
- 指纹：p3_k1q 对 p3_k1 只有三个目标的 camp_cnv01_probe.map 变了（脚本），符合预期。

## 还没做：K6 编组命令

总控的决定：编译器给每个需要整队下命令的组生成一个队伍，写进任务发布的 TEAMS；这个组的单位放下或造出来时归进这个队，`ctx.order` 只对这些队下 `TEAM_*` 命令。**动手前先在测试台确认**：成员死光时整队命令怎样、新成员入队时怎样、放置单位时能不能指定队伍。**如果测试台证明地图里的队伍这条路走不通，停下来汇报，不要退回给单个单位逐个下命令。**

我查到的：
- 地图现在只发布 `p1`、`s1` 两个队（`maps/*.TEAMS`，`maps/island.py:44`），队伍定义在地图 `.map` 的 `SidesList` 里（mapxml.py 有 `_typed_props_end` / `encode_props` / `set_player` 可以参照，改的是同一块二进制）。要新增一个自定义队（例如 `Player_1/teamConvoy` 之类的 `teamName` / `teamOwner` 属性字典）要先看 SidesList 里队伍字典的编码（`experimental/campaign/mapstudy.py:70` 读玩家字典，队伍部分还没人读过；可以拿零售战役图对照，那里有成百个自定义队）。
- 可用的整队动作（script_catalog.json）：`MOVE_TEAM_TO`、`ATTACK_MOVE_TEAM_TO`、`TEAM_ATTACK_NAMED`、`TEAM_GUARD_AREA`、`TEAM_HUNT`、`TEAM_STOP`、`TEAM_FOLLOW_WAYPOINTS`。单位入队：`CREATE_NAMED_ON_TEAM_AT_WAYPOINT(_WITH_ORIENTATION)` 的队参数；地图里放置的单位用 `originalOwner` 属性写队名。
- 现在没走 `ctx.order` 的单个单位命令：`plan.py` 里的 `NAMED_HUNT`、`ATTACK_MOVE_NAMED_UNIT_TO`；`missions/festival_parts.py` 里车队走位 `MOVE_NAMED_UNIT_TO`。`ctx.order` 现在出 `NAMED_ATTACK_NAMED` / `UNIT_GUARD_AREA`。I7（"最后一程剩余 2 辆车，但是只有一辆在移动"）对应车队这一组。
- 先想清楚：车队的单位是 `s2` 阵营还是玩家 p1？TEAMS 里没有 s2；`Compiler.side` 把 阵营 词映射到 p1/s1/…，看 `festival_parts.py:69` 的 `self.ctx.team(self.side)`。

## 做事顺序

1. K5 + model.merged 已提交；issues.md 的 I5 已标。外壳线的 `docs/shell/handoff.md`、`experimental/cnv/shell.py`、`experimental/video/pack.py`、`tests/test_video.py` 不是我的，不要带进提交。
2. K6：先写测试台探针（bench_start 进一个小关，建自定义队、放单位、整队下令，看死光和入队后的行为）；证明走得通再改编译器和 `ctx.order`；走不通就停下来汇报。
3. 验证类的活（指纹、pytest、sim、探针）仍交给 Sonnet 子 Agent，正斜杠绝对路径，用完让它停后台任务。
4. 小心：本仓库 Bash 钩子会拦"heredoc 里带反斜杠写文件"的命令，改文件用 Edit/Write；工作目录会因 cd 漂移，命令开头总是 `cd` 到仓库根。

草稿工具（临时，在会话 scratchpad，不进仓库）：`queue_probe.py <level>`（sim 里每句台词播/丢的时间）、`cam_probe.py <level>`（镜头点夹前夹后）。需要的话重写，几十行。
