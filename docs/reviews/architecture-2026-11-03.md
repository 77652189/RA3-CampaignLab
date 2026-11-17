# 架构评审：RA3-CampaignLab 现行流水线（2026-11-03，只读评审）

评审范围：`experimental/` 全部、`tests/`、`docs/architecture.md`、`docs/adr/README.md`（0014、0015）、`docs/issues.md`。
方法：自写 AST import 追踪器（同目录优先，再按仓库实际塞进 `sys.path` 的目录 cnv/campaign/testbench/units/music/video/voice/仓库根解析；含函数内的延迟 import；`importlib.import_module` 和 `.py` 字符串字面量单独记录），再用 grep 逐处核对。追踪脚本和结果在 scratchpad（`trace.py`、`build_graph.json`、`live_graph.json`、`orphans.txt`），不进仓库。
工作区有别的线未提交的改动（`cnv/build.py`、`cnv/checks/a4.py`、`testbench/bench_mcp.py`、`harness.py`、`shell_shots.py`、`run_check.py`），只读过，未动。

## 0. 先校正症状里的数

| 症状 | 原说法 | 实测 | 说明 |
|---|---|---|---|
| Python 文件 | 328 个、4.9 万行 | `git ls-files '*.py'` = 328、49,069 行；其中 `experimental/` 264 个、38,838 行 | 328 含 `tests/` 38 个、`docs/design/` 13 个、`ra3voice/` 8 个 |
| 改 `sys.path` | 158 | 169 个文件（全仓），`experimental/` 内 120 个 | 最常见写法 `sys.path.insert(0, HERE)` 67 处 |
| subprocess | 29 | 全仓 32，`experimental/` 29 | |
| 现行代码 import 的 make_campnew | 2、3、18、23、35、38 | **现行构建链实际是 18→7→6→4→{2,3}**；23～28 只被 `testbench/calib.py:83` 拉进来（为了两个常量）；35 只被 `units/make_campchrono.py:23`、38 只被 `make_campa7.py:31`/`make_campa8.py:28` 用，这三者自己都是探针 | 现行链里有 4 和 6、7，原清单漏了 |

## 1. 现行流水线到底用了哪些文件

### 1.1 从 `cnv/build.py` 出发的闭包

`build.py` 的 import 闭包共 **174 个文件**：cnv/missions 42、cnv/checks 39、campaign 21、cnv/units 19、cnv 顶层 10、ra3voice 6、cnv/devices 6、cnv/maps 5、music 5、testbench 2、video 1、voice 1。

单关构建和 `--shell` 走的是**同一个函数** `parts.assemble`（`build.py:473`），差别只在 `shell=` 参数；但 `--shell` 明令不许带 `--check`（`build.py:447-448`），所以**任何检查都跑不到 CampShell 上**（见第 2.3 节）。

```mermaid
graph TD
  subgraph 入口
    BUILD[cnv/build.py<br/>CLI + 手写 MISSIONS 表 + 检查判读]
    MCP[testbench/bench_mcp.py<br/>cnv_check / cnv_show]
  end
  MCP -- subprocess build.py --plan/--judge --> BUILD
  BUILD -- subprocess envs/bench_mcp python --> CLIENT[testbench/bench_client.py]
  BUILD --> MISS[cnv/missions/* 42 个<br/>a4 a5 a7 j3 j5 j7 s2 s5 s6 走策划稿<br/>a8 j4 和 *_bench 手写]
  BUILD --> CHK[cnv/checks/* 39 个]
  BUILD --> PARTS[cnv/parts.py<br/>Mission/Script/Test 数据 + contract + merged + assemble]
  BUILD --> LANGS[cnv/langs.py]
  BUILD -. --preview .-> PLATMAP[campaign/platmap.py, platprops.py lint]
  MISS --> PLAN[cnv/plan.py 策划稿编译器]
  PLAN -- importlib maps.&lt;地图&gt; --> MAPS[cnv/maps/*]
  PLAN -- registry --> DEV[cnv/devices/*]
  DEV -- import plan 反向依赖 --> PLAN
  PLAN --> UNITS[cnv/units/*]
  PLAN --> AUX[glossary enemy_ai voice_link plancheck]
  PLAN -- importlib --> MUSIC[experimental/music/pack 等]
  AUX --> VOICE[experimental/voice/pack]
  UNITS -- 只为 c2.SDK --> C2
  CHK --> PARTS
  CHK -. 越界 8 个文件 .-> MISS
  PARTS -- assemble/preview --> C18[campaign/make_campnew18]
  C18 --> C7[make_campnew7] --> C6[make_campnew6] --> C4[make_campnew4]
  C4 --> C2[make_campnew2] & C3[make_campnew3]
  PARTS -- shell=True --> SHELL[cnv/shell.py] --> APT[campaign/apt_textures]
  PARTS -- shell=True --> VIDEO[experimental/video/pack]
  PARTS --> SLOTS[testbench/slots.py 锁]
  C7 & C2 -- subprocess --> BAB[SDK BinaryAssetBuilder.exe]
  C18 & C7 & C4 & C2 --> FMT[mapxml mapscript mapfile newmap mapterrain maplight lint mapcache splice_assets sagehash labpaths]
  FMT --> RV[ra3voice big refpack csf]
  C4 --> BIG[(Mods/&lt;名字&gt;/&lt;名字&gt;.big)]
```

### 1.2 其它活的入口（不在 build.py 闭包里，但在用）

把 `testbench/bench_mcp.py`、`harness.py`、`cnv/sim.py`、`launcher.py`、`plancheck.py`、`graybox.py`、`offline.py`、`tests/*.py`、`.claude/hooks/*.py`、`cnv.py` 一起作入口，闭包 354 个文件。`experimental/` 下有 41 个文件只被这些入口用到（模拟器 sim*、测试台 harness/calib/nav、units 的建模工具、music 的分析工具、campaign 的 maprender/mapstudy/retailref/terrainref/w3x 等）。

### 1.3 没被任何入口 import 的文件（70 个，按目录）

注意：其中一部分是**单独跑的命令行工具**，不是死代码，不能一律归档。

| 类别 | 文件 | 结论 |
|---|---|---|
| 探针（可归档） | `campaign/make_campnew.py`、`make_campnew5`、`8`～`17`、`19`～`22`、`29`～`38`（共 26 个）；`make_campa7.py`、`make_campa8.py`、`make_campbridge.py`、`make_camptripo.py`、`make_lightmod.py`、`make_realmap.py`、`realmap.py`、`w3dbin.py` | 归档。`make_campnew38` 最后改动 2026-10-21 |
| 半死（可归档，先抽常量） | `make_campnew23`～`28` | 只因 `testbench/calib.py:83` 要 `c28.A` 和 `c28.CALIB_GRID` 两个常量被拉进来；而且 import 它们会顺带改写 c2/c4 的全局变量（见 2.1）。先把两个常量搬进 `calib.py`，再归档 |
| 旧地图/旧关（核实后可归档） | `cnv/maps/baikonur.py`、`himeji.py`、`panama.py`、`siberia.py`；`cnv/missions/music_dyn.py`、`music_route.py` | 没有任何 mission 引用（推测是还没排上的关卡地图，问关卡线再定） |
| 独立工具（保留） | `testbench/shell_shots.py`、`caption_rows.py`、`chaos_map.py`；`music/probe_mod.py`、`bench_listen.py`、`decode_retail.py`、`fetch_samples.py`、`timing.py`；`units/*_look.py`、`*_kit.py`、`cnv_lighttank*.py` 等；`rtx-remix/*`、`outsource/agy_task.py` | 命令行直接跑，不是死代码。`units/cnv_lighttank.py`～`3`、`ai_lighttank*.py`、`make_campchrono.py` 是同样的"复制改号"式探针，可由单位线决定归档 |

## 2. 分层边界应该怎么画

### 2.1 打包层：一串靠"导入时副作用 + 改别人模块全局变量"拼起来的链

证据：

- `make_campnew18.py:16-27`：一 import 就执行 `c4.NAME = c2.NAME = 'CampNew18'`、改 `c2.SRC_DIR/BUILT/OUT`、`c7.MAP_MOD`、往 `c4.c3.STRINGS` 塞 CNV02 的测试字串；`:118` `c6.edit = generate`；`:137` `c7._edited = edited_with_previews`（猴子补丁）。
- `make_campnew4.py:24-28`：import 时 `c2.NAME = 'CampNew4'`、改 `c2.OUT`、读环境变量 `CNV_MAP_STREAMS`。
- `parts.assemble`（`parts.py:575-675`）再把这些全局变量全改一遍：`c4.NAME = c2.NAME = name`、`c2.OUT`、`c7.MAP_MOD`、`c7.EXTRA_TEMPLATES[...]`、`c7.EXTRA_ALL.append`、`c7.EXTRA_OWN +=`、`c4.c3.STRINGS.update`、`c2.SHELL`、`c4.c3.OVERRIDES`、`c2.EXTRA_STATIC`、`c4.EXTRA_FILES`、`c4.CHECKS`，最后 `c6.edit = edit` 再 `c4.main()`。也就是说**这条链的真正接口是 6 个模块的 20 来个全局变量**。
- `c7.EXTRA_OWN/EXTRA_ALL/EXTRA_TEMPLATES` 在 `assemble` 里只追加、从不清空（只有 `SHELL/OVERRIDES/PREFIX_OVERRIDES` 在 `parts.py:629` 重置）。同一进程里 assemble 两次会串味（推测：目前每次构建都是新进程所以没炸）。
- 作者自己知道这个坑：`make_realmap.py:55` 注释 "importing it would re-point the build at CampNew23"。
- `docs/architecture.md` 的"不许怎么做"里还要求别人"用 `make_campnew7.EXTRA_OWN` 按名字前缀链接进来"——打包层的内部细节漏成了全仓规则。
- 外壳（K9）的逻辑散在 5 处：`cnv/shell.py`（生成内容）、`make_campnew2.py:47,84-115`（`SHELL` 决定槽位和 MissionTemplate）、`make_campnew3.py:40-41,131-132`（`OVERRIDES/PREFIX_OVERRIDES` 改原版字串）、`parts.py:630-660`（拼装）、`build.py:446-475`（改名、删 Play bat）。
- `cnv/units/*.py` 有 15 个文件 `import make_campnew2 as c2`，**只用了 `c2.SDK`**（16 次），而 `c2.SDK` 就是 `labpaths.SDK3`（`make_campnew2.py:27`）。`tests/test_shell.py:15` 也直接 import c2。

建议的接口：打包层对外只有一个函数和一个数据类。

```python
@dataclass(frozen=True)
class ModSpec:            # 一个 mod 要装进去的全部东西，纯数据
    name: str
    map_edit: Callable[[MapFile], None]          # 写地图（parts.write_map 闭包）
    unit_files: dict[str, str]; extra_all: list[str]; extra_own: list[bytes]; templates: dict
    strings: dict[str, str]; overrides: dict[str, str]; prefix_overrides: dict[str, str]
    static_includes: list[str]; big_files: list[tuple[str, bytes]]; checks: list[Callable]
    slot: ShellSlot | None                       # None = 单关；外壳只往这里和 strings/overrides/big_files 填东西
def build_mod(spec: ModSpec, out_dir: str) -> BuildResult   # 拿 SDK 锁、调 BAB、拼 big、写 skudef
```

c2/c3/c4/c6/c7/c18 的代码先原样留着，只是改成"`build_mod` 进来时把 spec 灌进去、出去时恢复"，以后再一点点把全局变量换成参数。外壳变成"往 ModSpec 里加东西的一个函数"（`shell.contribute(spec, lang) -> ModSpec`），不再改别的模块。

### 2.2 编译器 `plan.py` 和内容模块之间

现状：
- 机关拿到的是整个编译器对象：`plan.py:969-976` `DEVICES[kind](self, name, spec)`。机关代码用到编译器的 `c.tag`(52)、`c.when`(8)、`c.unit`(7)、`c.area`(6)、`c.mark`(5)、`c.m`(5，直接拿 Mission)、`c.side`(4)、`c.text`(2)、`c.part_names`(2)、`c.devices`(2，拿别的机关)、`c.d`(1，原始策划稿)。
- 反向依赖：`devices/carrier.py`、`ice_plazas.py` 各 3 处、`convoy.py`、`horn.py`、`train.py` 各 1 处 `import plan`（为了 `plan.times/by_level/counts/PlanError`）。plan ↔ devices 成环。
- 机关自己直接产出台词和单兵命令（见第 3 节 K1、K6），绕过编译器的唯一出口。
- 关卡注册是手写的：`build.py:22-65` 显式 import 39 个检查模块、42 个关卡模块，`build.py:88-200` 手写 `MISSIONS` 表。新增一关或一个检查必须改 `build.py`，所以这个"共用文件"72 次提交里都被改过（`git log -- experimental/cnv/build.py` 72 条），是并行开发的冲突热点。
- 关卡分两种：`docs/story/plans/` 里有策划稿的 9 关（a4 a5 a7 j3 j5 j7 s2 s5 s6）走 `plan.py`；`LEVELS`（`build.py:207`）里的 a8、j4 是手写 Script（`missions/a8.py:65-74`、`missions/j4.py:81-99` 直接写 `SHOW_MILITARY_CAPTION`），编译器的任何源头修法都管不到它们。

建议：
- 机关只拿一个窄的"编译上下文"接口（`Ctx`：`tag`、`when(cond)`、`unit(name, side)`、`area/mark(site)`、`say(line)`、`order(team, verb, target)`、`times/by_level/counts` 这些纯函数），不给 `m`、`d`、`devices`。纯函数 `times/by_level/counts/PlanError` 挪到一个小模块（如 `cnv/plantime.py`），机关和 plan 都从那里取，断开环。
- 关卡和检查自注册：每个 `missions/<x>.py` 导出 `MISSION = mission`，每个 `checks/<x>.py` 导出 `CHECKS = {...}`，`build.py` 用 `pkgutil` 扫一遍。`build.py` 不再因为加关卡而改动。
- a8、j4 迁到策划稿（或至少让手写关卡也只能通过 `Ctx.say` 出台词）。

### 2.3 测试和验收层：检查拿到的不是"正式 mod 的实际效果"

现状：
- 检查构建的是**另一个 mod**：`resolve()` 返回 `m.name + check.title()`（`build.py:237-246`），`parts.merged(mission, test)` 把检查自己的脚本合进地图；`--shell` 不许带 `--check`（`build.py:447-448`）。所以 cnv_check 永远验不到 CampShell 的槽位、外壳字串覆盖、外壳视频、外壳的 APT 文件。
- 检查会改写被测关卡本身：`checks/a4.py:95-100` 把工兵瞬移到点位并设 `UNATTACKABLE`；`:103-109` `ice_at` 用 `NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT` 放冰墙——`checks/a4.py:432-436` 自己的注释承认这个动作"ignores [placement rules]"，正是 I3（冰墙放不下）漏掉的原因；`:112-119` `mouths_on` 每帧把关卡自己的号角开关压成 0。detour/queue/melt 等检查都建立在 `ice_at` 上。
- 检查越过接口取关卡内部常量（违反 architecture.md 的"不 import 关卡模块的常量"）：8 个文件——`checks/fence.py:6`、`liberty.py:13-14`、`mech.py:11`、`reroute.py:9`、`sight.py:7`（import `missions.*_bench` 的常量），`a4_before.py:30`、`clone.py:10`、`combo.py:8`（import `units.*` 常量）。
- 外壳的验证另走一条：`testbench/shell_shots.py`（外壳线）对 CampShell 截图，人眼看。

建议的分层（验收层只消费"正式产物"）：
1. **静态验收**：从**最终的 ModSpec / 编出的 map 脚本**（不是从策划稿）读出脚本表，跑只认规则的检查（K1 一时一句、K5 镜头在可玩区、K6 命令下给队）。这类检查和谁写实现无关，对单关和 CampShell 跑的是同一份产物。`parts.contract` 已经是这个位置，往里加规则即可。
2. **动态验收**：允许 `build.py <关> --shell --check <名>`，即在 CampShell 上叠检查脚本；检查脚本只许"加观测"（计数器、区域、等待），不许改被测对象（瞬移、无敌、关机关、脚本放技能），需要玩家动作的用测试台点击（`checks/a4.py` 未提交的 `place` 已经这么做了）。
3. 检查归验收者写（ADR 0015 的"做的和验的分开"），实现线只提供公开接口（`m.role/ability/site/player`）。

### 2.4 建议的整体分层（自下而上）

| 层 | 内容 | 对外接口 | 不许 |
|---|---|---|---|
| L0 格式库 | `labpaths`、`ra3voice/*`、`mapscript/mapfile/mapxml/mapterrain/maplight/mapcache/splice_assets/sagehash/refpack_lz` | 读写函数 | 不知道"关卡""外壳" |
| L1 内容 | `cnv/maps`、`cnv/units`、`cnv/devices`、music/voice/video 的 pack | `SITES`、单位对象、`Device.cond/action/scripts(ctx)`、`Pack(include, files, check)` | 不 import plan、不 import 打包层 |
| L2 编译 | `plan.py`（+ 手写关卡改为同一 Ctx） | `compile(plan) -> Mission`（纯数据） | 不碰文件系统、不碰 c2..c18 |
| L3 打包 | `parts.assemble` 背后的 c2..c18、`shell.contribute` | `build_mod(ModSpec) -> BuildResult` | 不读模块级可变全局；外壳只往 ModSpec 加东西 |
| L4 编排 | `build.py` | CLI；关卡/检查自注册 | 不手写注册表 |
| L5 验收 | `parts.contract` 规则检查、`testbench/` | 只读 ModSpec 或 .big；动态检查只加观测 | 不 import L1/L2 的常量；不改被测行为 |

## 3. "唯一源头"逐类核对（K1～K10）

| 类别 | `issues.md` 说的源头 | 现在是不是唯一 | 重复/绕过的地方（证据） |
|---|---|---|---|
| K1 台词出口 | `plan.py` 一个排队出口 | **不唯一** | 排队：`plan.say` `plan.py:716-725` + `compile_talk` `:727-737`。过场内另有一套时间轴排队 `:834-857`（同样用 `STRIP_CLEAR`，但不看场外的 `Talking` 旗，场外刚举旗的一句和过场第一句可能叠，推测）。绕过：`plan.py:695`（失败）、`plan.py:1098`（进攻预警 `warn` 直接 `SHOW_MILITARY_CAPTION`）、`devices/horn.py:370`（号角 alert）、`devices/carrier.py:110`、`missions/festival_parts.py:77,90`、手写关 `missions/a8.py:65,69,74`、`missions/j4.py:81,97,99`。合计 1 个队列 + 1 个过场排队 + 9 处绕过 |
| K2 台词挂点 | 编译器不接受只写秒数的台词 | **源头不存在** | `plan.action` 的 `通报` 分支（`plan.py:583-610`）接受任何位置的台词，带 `秒` 也照收；没有"必须挂在镜头/事件上"的校验。状态"待修"属实 |
| K3 施展点 | 生成器按施展条件整平；检查走玩家放置流程 | **检查一侧不唯一** | 旧检查 `checks/a4.py:103-109 ice_at` 用脚本放技能绕过放置规则，被 detour/queue/melt 等复用；新的 `place`/`place_mouths`（未提交）走玩家点击。生成器整平没找到对应代码（推测未实现） |
| K4 资源摆法 | 生成器按规则摆，不手写坐标 | **不是源头，是事后 lint** | `cnv/maps/festival.py:160-167` 矿和油井是手写坐标；`campaign/platmap.py:480 ore_lint` 只查"矿场附近有没有矿"，而且只在 `build.py --preview`（`:453-458`）里跑，`assemble` 不跑 |
| K5 镜头范围 | 编译时夹在可玩区 | **源头不存在** | `plan.camera`（`plan.py:698-704`）直接出 `MOVE_CAMERA_TO`，不看可玩区；I5 的修法是把开场镜头挪到 x 1000（提交 da56a2e 的说明），属于修单例 |
| K6 编组命令 | 编译器只接受编组命令 | **不唯一** | 单兵命令散在 `plan.py:955,1131,1140`、`devices/convoy.py:106`、`horn.py:554,557`、`ice_plazas.py:217,221`、`train.py:80`（`NAMED_ATTACK_NAMED`/`UNIT_GUARD_AREA` 对名字逐个下）。没有 TEAM_* 出口 |
| K7 挡路与观感 | 准则 P36 + 生成器默认值 | 准则唯一（`docs/design/`），生成器默认值未核到 | 推测：地图模块各自写 `SCENERY`，`platprops.lint` 只在 `--preview` 跑 |
| K8 演示可信 | 演示步骤的编译规则 | 未核到单一出口 | 演示步骤在 `plan.py` 过场时间轴里，检查 `checks/a4.py:292 demo`；无规则级断言（推测） |
| K9 外壳替换 | 外壳构建 | **不唯一** | 5 处：`shell.py`、`make_campnew2.py:47,84-115`、`make_campnew3.py:40-41,131-132`、`parts.py:630-660`、`build.py:446-475` |
| K10 配音 | 配音管线 | 另一仓库，本仓只有 `cnv/voice_link.py` + `experimental/voice/pack.py` 接入点，单一 | — |

## 4. 整改清单（按收益/成本排序，均可小步做）

验证通用手段："构建指纹"——对一关（a4）和 CampShell 各做一次构建，记录 `.big` 里每个文件名 + sha1（已有 `ra3voice/big.py` 能读），整改前后比对，除预期变化外必须一致。下面简称"指纹不变"。

| # | 改什么 | 动哪些文件 | 风险 | 小步与验证 | 归属 |
|---|---|---|---|---|---|
| 1 | 台词只有一个出口：把 9 处绕过改走 `say`；机关拿到 `ctx.say`；`parts.contract` 加规则"`SHOW_MILITARY_CAPTION`/配音 `PLAY_SOUND_EFFECT` 只能出现在 `CNV <tag> - Say k` 或过场脚本里" | `plan.py:695,1098`、`devices/horn.py`、`carrier.py`、`missions/festival_parts.py`、`parts.py`（contract）；a8/j4 先进白名单 | 低：台词时序会变（就是要它变） | ①先加 contract 规则 + 白名单（现状全绿）②逐处迁移、每迁一处删一条白名单 ③`pytest tests/test_plan_lines.py tests/test_plan_scenes.py`、`sim.py a4` 看台词时间表 | 关卡 |
| 2 | 检查能跑在 CampShell 上：放开 `--shell --check`；cnv_check 加 `shell=True` 选项；验收检查默认在 CampShell 上跑 | `build.py:446-475`（外壳那段）、`testbench/bench_mcp.py`（`_cnv_check`） | 中：外壳槽位下检查脚本的计数器读法可能变 | ①放开参数，先拿 `a4 --shell --check win` 跑一次，与单关结果对比 ②再把 `place` 这类玩家流程检查切到外壳 | 外壳（build.py 段）+ 总控（bench_mcp） |
| 3 | 15 个 `cnv/units/*.py` 的 `import make_campnew2 as c2` 改成 `labpaths.SDK3` | `cnv/units/` 15 个文件 | 极低 | 一次改完；`grep -l make_campnew2 experimental/cnv/units` 为空；指纹不变 | 关卡（units 的接线非外观部分） |
| 4 | 归档 26 个探针 `make_campnew*` + 8 个 `make_camp*`/`realmap` 等；`calib.py` 抽出 `c28.A`、`CALIB_GRID` 后再归档 23～28 | `git mv` 到 `experimental/archive/campaign/`；`testbench/calib.py:82-90` | 低：可能有文档或口头流程还在跑某个探针 | ①先加守卫 G1/G2（冻结名单）②移 26 个，`pytest -q` + 一次 a4 构建 ③改 calib 后移 23～28 | 外壳（make_campnew）；calib 归总控 |
| 5 | 打包层收口：`ModSpec` + `build_mod`，内部仍调 c2..c18，但进出时灌入/恢复全局；先把 `make_campnew18` 的导入副作用挪进函数 | `parts.py`（assemble 拆成 `spec_of(mission, test, shell)` + `build_mod`）、`campaign/make_campnew18.py`、`make_campnew4.py` 顶层赋值 | 中：全局变量顺序敏感 | ①`spec_of` 纯函数先落地，assemble 内部改用它（指纹不变）②18 的导入副作用进函数（指纹不变）③守卫 G7 ④外壳改成 `shell.contribute(spec)`（CampShell 指纹不变） | 关卡（parts）+ 外壳（campnew、shell） |
| 6 | 关卡/检查自注册，`build.py` 不再手写 MISSIONS | `missions/*.py` 导出 `MISSION`、`checks/*.py` 导出 `CHECKS`、`build.py:22-200` | 低 | ①新旧并存：自注册结果与手写表比对相等（测试）②删手写表 | 关卡 |
| 7 | 编组命令单一出口：`ctx.order(team, ...)` 产出 TEAM_* 动作；plan 和 4 个机关改用它；contract 规则禁止 `NAMED_ATTACK_NAMED`/`UNIT_GUARD_AREA` 出现在出口之外 | `plan.py`、`devices/convoy,horn,ice_plazas,train.py`、`parts.py` | 中：TEAM 语义要先在测试台确认（成员死光、新成员入队） | 先一个机关（convoy，对应 I7），测试台跑 j4/a4 车队检查，再推广 | 关卡 |
| 8 | 镜头夹到可玩区：`plan.camera` 查地图 `BORDERS`/策划稿 `边界`，越界就夹或报 `PlanError`；contract 加规则 | `plan.py:698-715`、`parts.py` | 低 | `cnv_preview a4` + 新的 plan 单测 | 关卡 |
| 9 | 资源摆法：`ore_lint`/`platprops.lint` 挪进 `contract`（每次构建都跑），再做"按相对关系生成矿/矿场"的生成器 | `parts.py`、`campaign/platmap.py`、`cnv/maps/*` | 低→中 | ①lint 进 contract（现有地图若不过先白名单）②生成器逐图替换 | 关卡 |
| 10 | 检查不改被测行为、不越界：`ice_at` 之类的"脚本代行"只留在明确标为"机关单测"的检查里，验收检查只加观测；8 个越界 import 换成 `m.role/m.site` | `checks/*.py` | 中：现有检查要重写 | 每次一个检查；守卫 G5 用白名单递减 | 关卡写机关单测；验收检查由总控/独立验收者写 |
| 11 | 机关接口变窄 + 断开 plan↔devices 环：纯函数挪 `plantime.py`，机关只拿 `Ctx` | `plan.py`、`devices/*.py` | 中 | 先挪纯函数（行为不变，`pytest` + `sim`），再逐个机关换 Ctx | 关卡 |
| 12 | `sys.path` 收敛：先冻结（棘轮），新文件统一 `from experimental.xxx import`（仓库根已在 `sys.path`，`parts.py:638` 已这么用） | 全仓 | 低（只冻结）/中（真正改） | 守卫 G4 | 总控定规则，各线改自己的文件 |

不建议做的：一次性把 c2..c18 合并重写、把 `experimental/` 整体改成可安装包。都是大爆炸，收益靠第 5、12 项的小步就能拿到大半。

## 5. 守卫测试（建议放 `tests/test_architecture.py`，由总控维护）

```python
LIVE_CAMPNEW = {'make_campnew2', 'make_campnew3', 'make_campnew4', 'make_campnew6', 'make_campnew7', 'make_campnew18'}

# G1 不许再新增 make_campnewNN（归档前用全部 38 个的冻结名单，归档后收紧到 LIVE_CAMPNEW）
assert {p.stem for p in Path('experimental/campaign').glob('make_campnew*.py')} <= LIVE_CAMPNEW

# G2 不许 import 已归档模块：AST 扫描 experimental/ 和 tests/（排除 experimental/archive/），
#    所有 Import/ImportFrom 的顶层名都不在 archived 集合里（archived = archive 目录下的文件名）
assert not [(f, n) for f, n in imports_of(live_files()) if n in archived_names()]

# G3 全仓只有一个台词出口（两层）
#  a) 源码层：字面量 'SHOW_MILITARY_CAPTION' 只出现在允许的文件里（白名单只减不增）
assert files_with_literal('SHOW_MILITARY_CAPTION', 'experimental/cnv') <= {'plan.py', 'parts.py', *CAPTION_ALLOW}
#  b) 产物层：对 LEVELS 里每一关 mm = parts.merged(m)，凡含台词动作的脚本名都匹配出口
for s in mm.scripts:
    if any(a[0] in DIALOG for a in s.do):
        assert re.fullmatch(r'CNV \w+ - (Say \d+|Scene .+)', s.name), s.name

# G4 sys.path 棘轮：改 sys.path 的文件数不超过上次记录（169），只许降
assert count_files_with('sys.path.insert', 'sys.path.append') <= SYS_PATH_CEILING

# G5 检查不越界：checks/*.py 不从 missions/maps/devices/units 取东西（白名单只减不增，现 8 个）
assert {f for f in Path('experimental/cnv/checks').glob('*.py')
        if imports_any(f, ('missions', 'maps', 'devices', 'units'))} <= CHECK_IMPORT_ALLOW

# G6 编组命令一个出口（K6）：产物层，单兵命令动作只出现在 ctx.order 生成的脚本里
assert not [s.name for s in mm.scripts for a in s.do if a[0] in SINGLE_UNIT_ORDERS and not s.name.startswith(ORDER_PREFIX)]

# G7 打包层没有导入副作用（第 5 项之后）
import make_campnew2 as c2; before = (c2.NAME, c2.OUT)
import make_campnew18                                  # noqa
assert (c2.NAME, c2.OUT) == before

# G8 检查也能对外壳构建（第 2 项之后）：build.py 的参数解析不再拒绝 --shell --check
assert build.parse(['a4', '--shell', '--check', 'win']).shell

# G9 机关不反向依赖编译器（第 11 项之后）
assert not [f for f in Path('experimental/cnv/devices').glob('*.py') if imports_any(f, ('plan',))]

# G10 镜头只拍可玩区（K5）：产物层，每个 MOVE_CAMERA_TO 的目标点落在当时生效的 MAP_SWITCH_BORDER 内
```

G1、G2、G3a、G4、G5 现在就能加（用当前状态做白名单，只许收紧）；G3b、G6、G10 依赖 `parts.merged` 能离线跑（它已不需要游戏，可行）；G7、G8、G9 在对应整改落地后加。
