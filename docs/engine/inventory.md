# 原版功能总清单（引擎 A：脚本层、物体模块、武器效果；引擎 B：AI）

由 `experimental/cnv/inventory.py` 从原版数据生成，**别手改**；`tests/test_inventory.py` 在它过期时变红。状态与判定规则见脚本 docstring（ADR 0026）。用量：脚本 = 原版战役脚本里出现的次数；模块 = 原版战役地图里摆了的、用到它的物体种数（括号里是全部物体种数）；武器效果 = 用到它的原版武器数；AI = 原版 AI 数据（SDK SkirmishAI，含战役关的 AI 状态）里写它的次数，判定规则见 `inventory_ai.py`。**主数字是"按用量已对拍"**：已对拍项的用量占全部用量的比例，推断不算，不涉及不进分母；目标每部分 90%。

| 部分 | 按用量已对拍 | 项数 | 已对拍 | 推断 | 未做 | 不涉及 | 按用量已有（已对拍+推断） |
|---|---|---|---|---|---|---|---|
| 脚本动作 | **89%** | 451 | 112 | 28 | 194 | 117 | 91% |
| 脚本条件 | **94%** | 89 | 27 | 5 | 54 | 3 | 94% |
| 物体模块 | **91%** | 186 | 36 | 7 | 121 | 22 | 92% |
| 武器效果 | **64%** | 25 | 13 | 1 | 9 | 2 | 76% |
| AI | **70%** | 415 | 97 | 134 | 150 | 34 | 88% |

## 脚本动作

| 状态 | 名字 | 用量 | 说明 |
|---|---|---|---|
| 已对拍 | `ENABLE_SCRIPT` | 5727 | 引擎模型核心；台上量过、测试对拍：checks/engine_script.py |
| 已对拍 | `SET_MILLISECOND_TIMER` | 4153 | 引擎模型核心；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `SET_FLAG` | 4105 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | `ALLOW_DISALLOW_ONE_BUILDING` | 3466 | tests/test_simbench.py::test_a_ban_holds_the_queue_and_does_not_cancel |
| 已对拍 | `PLAYER_LOCK_PLAYER_TECH` | 1887 | tests/test_simbench.py::test_protocol_a_computer_player_spends_unless_locked |
| 已对拍 | `DISABLE_SCRIPT` | 1099 | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `MOVE_NAMED_UNIT_TO` | 1000 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aidefense.py |
| 已对拍 | `LINK_MISSION_OBJECTIVE_TO_OBJECT` | 950 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts5.py |
| 已对拍 | `NAMED_DELETE` | 908 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attack.py |
| 已对拍 | `CREATE_REINFORCEMENT_TEAM` | 753 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_reinf.py |
| 已对拍 | `SET_MISSION_OBJECTIVE_STATUS` | 732 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts5.py |
| 不涉及 | `PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT` | 640 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `CALL_SUBROUTINE` | 533 | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `UNIT_IDLE_FOR_FRAMECOUNT` | 504 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 不涉及 | `PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT_WITH_SUBTITLE` | 445 | 纯表现（名字规则） |
| 不涉及 | `MOVIE_PLAY_RADAR` | 433 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION` | 399 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 已对拍 | `OBJECTLIST_ADDOBJECTTYPE` | 383 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 已对拍 | `PLAYER_SET_MONEY` | 345 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aitower.py |
| 未做 | `SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY` | 343 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `PLAYER_RELATES_PLAYER` | 319 | tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back |
| 已对拍 | `UNIT_AFFECT_OBJECT_PANEL_FLAGS` | 317 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 不涉及 | `SET_MISSION_HOT_SPOT_VISIBILITY` | 300 | 纯表现（名字规则） |
| 已对拍 | `MOVE_TEAM_TO` | 298 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_reinf.py |
| 已对拍 | `CREATE_NAMED_ON_TEAM_AT_WAYPOINT` | 291 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `NAMED_ATTACK_NAMED` | 271 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attack.py |
| 已对拍 | `CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION` | 259 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 已对拍 | `MOVE_CAMERA_TO` | 255 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_camera.py |
| 不涉及 | `OBJECT_CREATE_RADAR_EVENT` | 254 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `UNIT_IDLE_FOR_SECONDS` | 237 | tests/test_simbench.py::test_scripts1_idle_for_seconds_drops_the_move |
| 已对拍 | `TEAM_TRANSFER_TO_PLAYER` | 235 | tests/test_simbench.py::test_scripts1_a_team_handed_over_drops_its_move |
| 已对拍 | `NAMED_TRANSFER_OWNERSHIP_PLAYER` | 231 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_invuln.py |
| 已对拍 | `INCREMENT_COUNTER` | 229 | 引擎模型核心；台上量过、测试对拍：checks/engine_aimicro.py |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:SHROUD_REVEAL_TO_ALL` | 218 | 状态位 SHROUD_REVEAL_TO_ALL 只记下来 |
| 已对拍 | `PLAYER_SET_MAX_PLAYER_POWER_POINTS` | 206 | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 已对拍 | `NAMED_KILL` | 204 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 推断 | `TEAM_HUNT` | 203 | 没交给 AI 的玩家（含玩家自己）：不动，台上量过（engine_scripts1 hunt 60 s）；AI 玩家的 HuntTactic 不模拟（引擎 B），碰到记 Sim.unmodeled |
| 已对拍 | `CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT` | 196 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_ref.py |
| 已对拍 | `LINK_MISSION_OBJECTIVE_TO_WAYPOINT` | 194 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts5.py |
| 已对拍 | `NAMED_FOLLOW_WAYPOINTS` | 192 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_wayatk.py |
| 未做 | `TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY` | 186 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS` | 184 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_wayatk.py |
| 不涉及 | `FADE_OUT_TO_BLACK` | 177 | 纯表现（名字规则） |
| 不涉及 | `FADE_IN_FROM_BLACK` | 176 | 纯表现（名字规则） |
| 不涉及 | `NAMED_FLASH` | 173 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `SET_COUNTER` | 171 | 引擎模型核心；台上量过、测试对拍：checks/engine_aidiff.py |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:SKIRMISH_AI_DO_NOT_ATTACK` | 171 | 状态位 SKIRMISH_AI_DO_NOT_ATTACK 只记下来 |
| 不涉及 | `NAMED_SHOW_INFOBOX` | 166 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `TEAM_USE_COMMANDBUTTON_ABILITY` | 162 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts1.py |
| 已对拍 | `PLAYER_SPECIAL_POWER_AVAILABILITY` | 158 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8b.py |
| 不涉及 | `PATH_MUSIC_PLAY_EVENT` | 155 | 纯表现（名字规则）；只记进时间线（sim.SHOWN）；台上量过（docs/engine/inventory-levels-a.md），没有测试跑这个台子 |
| 不涉及 | `CAMERA_LETTERBOX_END` | 154 | 纯表现（名字规则） |
| 已对拍 | `DISABLE_INPUT` | 152 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts3.py |
| 推断 | `TEAM_AI_TRANSFER` | 152 | 同 UNIT_AI_TRANSFER，对队里每个成员（台上没量） |
| 不涉及 | `EVA_SET_ENABLED_DISABLED` | 148 | 纯表现（名字规则） |
| 不涉及 | `PLAY_SOUND_EFFECT_AT` | 147 | 纯表现（名字规则） |
| 已对拍 | `ATTACK_MOVE_NAMED_UNIT_TO` | 146 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 不涉及 | `SOUND_PLAY_NAMED` | 137 | 纯表现（名字规则） |
| 已对拍 | `UNIT_AI_TRANSFER_ALL` | 137 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aidefense.py |
| 已对拍 | `ENABLE_INPUT` | 132 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts3.py |
| 已对拍 | `NO_OP` | 130 | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `TEAM_AFFECT_OBJECT_PANEL_FLAGS` | 130 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 推断 | `UNIT_AI_TRANSFER` | 129 | 程序读到：人类玩家的单位无效、不清命令；交给 AI 后的行为归引擎 B，碰到记 Sim.unmodeled（台上没量） |
| 不涉及 | `TELEPORT_STRUCTURE` | 128 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `CAMPAIGN_CREATE_AUTO_SAVE` | 127 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `UNIT_SET_STANCE` | 124 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `TEAM_DELETE` | 122 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 已对拍 | `TEAM_KILL` | 121 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 已对拍 | `SET_TIMER` | 119 | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `NAMED_STOP` | 118 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_emp.py |
| 已对拍 | `UNIT_TELEPORT_TO_WAYPOINT` | 118 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aidefense.py |
| 不涉及 | `PLAYER_CAMERA_MOVE_TO` | 117 | 纯表现（名字规则） |
| 已对拍 | `ATTACK_MOVE_TEAM_TO` | 116 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_wayatk.py |
| 已对拍 | `PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT` | 116 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8b.py |
| 已对拍 | `TEAM_IDLE_FOR_SECONDS` | 114 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 已对拍 | `PLAYER_SET_BASE_POWER` | 112 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8b.py |
| 未做 | `PLAYER_TOGGLE_RESOURCE_SHARING` | 111 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `UNIT_SET_MODELCONDITION_GENERIC` | 111 | 纯表现：设模型状态只换画法。原版脚本设的是 SUPPRESSED（a01 摆拍枪战的趴下动作），SDK 数据里读 SUPPRESSED 的只有绘制模块的 ConditionsYes；我们 a7 设的 USER_1 只有自由号的充能画法读 |
| 不涉及 | `PLAY_SOUND_AS_AI_COCOMMANDER_DIALOG` | 109 | 纯表现（名字规则） |
| 不涉及 | `TEAM_CREATE_RADAR_EVENT` | 107 | 纯表现（名字规则） |
| 已对拍 | `MAP_REVEAL_PERMANENTLY_AT_WAYPOINT` | 105 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 不涉及 | `CAMERA_LETTERBOX_BEGIN` | 104 | 纯表现（名字规则） |
| 已对拍 | `NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY` | 103 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aibasedef.py |
| 未做 | `TEAM_ALLOW_AI_AUTOACQUIRE` | 103 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER` | 101 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_ref.py |
| 不涉及 | `RESET_CAMERA` | 100 | 纯表现（名字规则） |
| 不涉及 | `CAMERA_LETTERBOX_BEGIN_WITH_RADAR` | 98 | 纯表现（名字规则） |
| 已对拍 | `SET_RANDOM_COUNTER` | 97 | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `PLAYER_SET_PLAYER_POWER_POINTS` | 95 | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 已对拍 | `SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER` | 94 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 已对拍 | `MAP_REVEAL_ALL_PERM` | 89 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `MAP_SWITCH_BORDER` | 87 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 未做 | `NAMED_SET_DISABLED` | 86 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `NAMED_REMOVE_INFOBOX` | 83 | 纯表现（名字规则） |
| 已对拍 | `TEAM_FOLLOW_WAYPOINTS` | 83 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_waypath.py |
| 已对拍 | `SKIRMISH_AI_MAKE_BASE` | 82 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiomove.py |
| 已对拍 | `SET_RANDOM_MSEC_TIMER` | 77 | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `TEAM_ATTACK_NAMED` | 76 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_reorder.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateEjectPassengersSpecialPowerUntargeted` | 75 | 只记进时间线，没有效果 |
| 已对拍 | `SKIRMISH_AI_USE_REPAIRS` | 75 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aipullback.py |
| 不涉及 | `NAMED_OUTLINE` | 74 | 纯表现（名字规则） |
| 不涉及 | `FLASH_UI_UNIT_ABILITY_BUTTON` | 72 | 纯表现（名字规则） |
| 已对拍 | `MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT` | 72 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 已对拍 | `PLAYER_GIVE_MONEY` | 72 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `UNIT_SET_TEAM` | 72 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `TEAM_CHANGE_OBJECT_STATUS` | 71 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8b.py |
| 未做 | `TEAM_GARRISON_TEAM_INSTANTLY` | 68 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `UNIT_CLEAR_MODELCONDITION` | 68 | 纯表现：同 UNIT_SET_MODELCONDITION_GENERIC，清掉画法状态 |
| 不涉及 | `CREATE_UNNAMED_ON_TEAM_AT_NAMED_OBJECT_LOCATION` | 67 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `LINK_MISSION_HOT_SPOT_TO_OBJECT` | 67 | 纯表现（名字规则） |
| 已对拍 | `SKIRMISH_AI_USE_REBUILD_SYSTEM` | 67 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiswitch.py |
| 已对拍 | `TEAM_MERGE_INTO_TEAM` | 67 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 推断 | `NAMED_HUNT` | 66 | 同 TEAM_HUNT：没交给 AI 不动（台上量过）；AI 玩家的猎杀不模拟（引擎 B） |
| 不涉及 | `TEAM_FLASH` | 66 | 纯表现（名字规则） |
| 已对拍 | `TEAM_SET_OVERRIDE_RELATION_TO_PLAYER` | 64 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 未做 | `SET_MISSION_HOT_SPOT_ACTIVENESS` | 61 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION` | 60 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 未做 | `NAMED_FORCE_ATTACK_NAMED` | 59 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_FORCE_ATTACK_WAYPOINT` | 59 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM` | 59 | 纯表现（名字规则）；只记进时间线（sim.SHOWN）；台上量过（docs/engine/inventory-levels-a.md），没有测试跑这个台子 |
| 不涉及 | `SET_REFERENCE_TO_RANDOM_TEAM_MEMBER` | 59 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `MAP_REVEAL_ALL_UNDO_PERM` | 58 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 不涉及 | `SHOW_MILITARY_CAPTION` | 58 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `NAMED_FOLLOW_WAYPOINTS_EXACT` | 56 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_waypath.py |
| 未做 | `UNIT_EXECUTE_SEQUENTIAL_SCRIPT` | 56 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_SET_MAX_HEALTH` | 53 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_maxhealth.py |
| 不涉及 | `TOGGLE_RADAR_UI` | 53 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `DISPLAY_TUTORIAL_TEXT` | 52 | 纯表现（名字规则） |
| 已对拍 | `PLAY_SOUND_EFFECT` | 51 | 只记进时间线（sim.SHOWN）；台上量过、测试对拍：checks/engine_dialog.py |
| 未做 | `TEAM_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT` | 51 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `DECREMENT_COUNTER` | 50 | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts3.py |
| 已对拍 | `DISPLAY_COUNTDOWN_TIMER` | 50 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 已对拍 | `SELL_OBJECT` | 50 | tests/test_simbench.py::test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames |
| 已对拍 | `TEAM_ATTACK_TEAM` | 50 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateEjectPassengersSpecialPower` | 49 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `FLASH_UI_BUILD_BUTTON` | 48 | 纯表现（名字规则） |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JAAVT1_Transform` | 48 | 只记进时间线，没有效果 |
| 未做 | `SET_UNIT_REFERENCE` | 48 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_ATTACK_FOLLOW_WAYPOINTS` | 47 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_wayatk.py |
| 已对拍 | `NAMED_RECEIVE_UPGRADE` | 47 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_invuln.py |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanBaseDefenseEgg` | 46 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_unpack.py |
| 未做 | `TEAM_SET_STANCE` | 45 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `NAMED_CUSTOM_COLOR` | 44 | 纯表现（名字规则） |
| 已对拍 | `HIDE_COUNTDOWN_TIMER` | 43 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_SovietAntiGroundAircraftEvacuate` | 43 | 只记进时间线，没有效果 |
| 已对拍 | `PLAYER_SET_OVERRIDE_RELATION_TO_TEAM` | 43 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleSpiderHole` | 41 | 只记进时间线，没有效果 |
| 未做 | `PLAYER_SET_SPECIAL_POWER_COUNTDOWN` | 41 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `FOR_EACH_PLAYER_OBJECT_EXECUTE_SCRIPT` | 39 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JAIV_Transform` | 38 | 只记进时间线，没有效果 |
| 未做 | `TECHTREE_MODIFY_BUILDABILITY_OBJECT` | 38 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `EVALUATE_SCRIPT` | 35 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `SKIRMISH_AI_TRANSFER_ALL` | 35 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_CONTEXT_SENSITIVE_ATTACK` | 35 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `FOR_EACH_TEAM_MEMBER_EXECUTE_SCRIPT` | 34 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `LINK_MISSION_HOT_SPOT_TO_WAYPOINT` | 34 | 纯表现（名字规则） |
| 已对拍 | `NAMED_DAMAGE` | 34 | tests/test_simbench.py::test_sell_a_killed_building_stays_paid_and_a_building_unpacking_is_not_sold |
| 不涉及 | `FLASH_MOUSE_HUD_FIXED_ELEMENT` | 33 | 纯表现（名字规则） |
| 未做 | `GATE_OPEN` | 33 | Sim.act / Sim.cond 不认识 |
| 未做 | `MAP_REVEAL_PERMANENTLY_IN_TRIGGER` | 33 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_DisguisedEvacuate` | 33 | 只记进时间线，没有效果 |
| 推断 | `STOP_TIMER` | 33 | 引擎模型核心 |
| 已对拍 | `TEAM_SET_OVERRIDE_RELATION_TO_TEAM` | 33 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 已对拍 | `UNIT_CHANGE_OBJECT_STATUS:NO_ATTACK` | 33 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 推断 | `ALLOW_DISALLOW_ONE_UPGRADE` | 32 | Sim.act / Sim.cond 有分支 |
| 已对拍 | `NAMED_ATTACK_TEAM` | 32 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 未做 | `UNIT_KILL_ALL_IN_AREA` | 32 | Sim.act / Sim.cond 不认识 |
| 未做 | `ATTACK_MOVE_TEAM_TO_NAMED_OBJECT` | 31 | Sim.act / Sim.cond 不认识 |
| 推断 | `CREATE_REINFORCEMENT_TEAM_AT_UNIT_POSITION` | 31 | Sim.act / Sim.cond 有分支 |
| 未做 | `SKIRMISH_AI_SET_FAVORED_ENEMY` | 31 | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT` | 30 | Sim.act / Sim.cond 有分支 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:SKIRMISH_AI_DO_NOT_TAKE` | 30 | 状态位 SKIRMISH_AI_DO_NOT_TAKE 只记下来 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleAlliedArtilleryVehicle` | 29 | 只记进时间线，没有效果 |
| 未做 | `PLAYER_ALLOWED_TOBE_COOPAI` | 29 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER` | 29 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiopen.py |
| 不涉及 | `DESELECT` | 28 | 纯表现（名字规则） |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_CAMPAlliedBomberDrop2` | 28 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SOUND_DISABLE_TYPE` | 28 | 纯表现（名字规则） |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackAlliedMCV` | 27 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_unpack.py |
| 不涉及 | `PLAYER_CAMERA_MOVE_TO_NAMED` | 27 | 纯表现（名字规则） |
| 未做 | `TEAM_GARRISON_SPECIFIC_BUILDING` | 27 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_PLAYERS_NEAREST_UNIT_OF_TYPE_TO_REFERENCE` | 27 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `TEAM_STOP` | 27 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 未做 | `TEAM_TELEPORT_TO_WAYPOINT` | 27 | Sim.act / Sim.cond 不认识 |
| 未做 | `MAP_UNDO_REVEAL_PERMANENTLY_IN_TRIGGER` | 26 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `NAMED_FLASH_WHITE` | 26 | 纯表现（名字规则） |
| 不涉及 | `RADAR_CREATE_EVENT` | 26 | 纯表现（名字规则） |
| 未做 | `TEAM_GUARD_AREA_FROM_POSITION` | 26 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `TEAM_SET_DISABLED` | 26 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `LINK_MISSION_OBJECTIVE_TO_OBJECT_WITH_CATEGORY` | 25 | 纯表现（名字规则） |
| 推断 | `NAMED_GARRISON_SPECIFIC_BUILDING` | 25 | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JapanBaseDefenseToggleBinaryWeapon` | 25 | 只记进时间线，没有效果 |
| 未做 | `PLAYER_SET_MONEY_CAP` | 25 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_ALLOW_AI_AUTOACQUIRE` | 25 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_SET_MODELCONDITION` | 25 | Sim.act / Sim.cond 不认识 |
| 推断 | `DISPLAY_COUNTER` | 24 | 引擎模型核心 |
| 不涉及 | `HIDE_COUNTER` | 24 | 纯表现（名字规则） |
| 未做 | `PLAYER_ALLOW_AI_AUTOACQUIRE` | 24 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PLAY_SOUND_AS_AI_COCOMMANDER_DIALOG_WITH_SUBTITLE` | 24 | 纯表现（名字规则） |
| 不涉及 | `SETUP_CAMERA` | 24 | 纯表现（名字规则） |
| 不涉及 | `SET_COOP_AI_COMMAND_UI_ENABLED` | 24 | 纯界面：开关玩家给盟友 AI 下令的按钮；模拟器的玩家没有给盟友下令的命令，开关无从起作用（以后加了这个命令再算） |
| 不涉及 | `LINK_MISSION_OBJECTIVE_TO_WAYPOINT_WITH_CATEGORY` | 23 | 纯表现（名字规则） |
| 未做 | `PLAYER_GRANT_SPECIAL_POWER` | 23 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_TRANSFER_OWNERSHIP_PLAYER` | 23 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE` | 23 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `HIDE_TUTORIAL_TEXT` | 22 | 纯表现（名字规则） |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NO_ATTACK_FROM_AI` | 22 | 状态位 NO_ATTACK_FROM_AI 只记下来 |
| 不涉及 | `MOVE_NAMED_UNIT_TO_UNIT` | 21 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `NAMED_USE_LOGIC_COMMAND_ABILITY_ON_NAMED_POSITION` | 21 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `SELECT_OBJECT` | 21 | 纯表现（名字规则） |
| 推断 | `TEAM_FOLLOW_WAYPOINTS_EXACT` | 21 | Sim.act / Sim.cond 有分支 |
| 不涉及 | `MOVE_CAMERA_TO_NAMED` | 20 | 纯表现（名字规则）；Sim.act / Sim.cond 有分支 |
| 未做 | `REDALERT_DISABLE_THREAT_LEVEL_BONUS` | 20 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `UNIT_EXECUTE_SEQUENTIAL_SCRIPT_COPY` | 20 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `CAMERA_FOLLOW_NAMED` | 19 | 纯表现（名字规则）；Sim.act / Sim.cond 有分支 |
| 已对拍 | `COUNTER_MATH_COUNTER` | 19 | 引擎模型核心；台上量过、测试对拍：checks/engine_contained.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_SmokeBombSpecialPower` | 19 | 只记进时间线，没有效果 |
| 未做 | `PLAYER_DISABLE_BASE_CONSTRUCTION` | 16 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_ENABLE_UNIT_CONSTRUCTION` | 16 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PLAY_SOUND_EFFECT_AT_TEAM` | 16 | 纯表现（名字规则） |
| 不涉及 | `TOGGLE_LOCK_CURRENT_SELECTION` | 16 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `UNIT_SET_MODELCONDITION_FOR_DURATION` | 16 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_STOP_SEQUENTIAL_SCRIPT` | 16 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_EXIT_BUILDING` | 15 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_garrison.py |
| 未做 | `TEAM_UPGRADE` | 15 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `UNIT_SET_HEALTH` | 15 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | `GIVE_PLAYER_UPGRADE` | 14 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_tech.py |
| 推断 | `MARK_MISSION_OBJECTIVE_COMPLETED` | 14 | 引擎模型核心 |
| 不涉及 | `MOVIE_PLAY_FULLSCREEN` | 14 | 纯表现（名字规则） |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleEnergizedArmorSpecialPower` | 14 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanEgg` | 14 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_KILL` | 14 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `PLAYER_SET_ALL_UNITS_TO_FLEE` | 14 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_runoffmap.py |
| 不涉及 | `SET_REFERENCE_TO_FIRST_TEAM_MEMBER_IN_AREA` | 14 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES` | 14 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiswitch.py |
| 未做 | `UNIT_EXECUTE_SEQUENTIAL_SCRIPT_LOOPING` | 14 | Sim.act / Sim.cond 不认识 |
| 未做 | `DISABLE_MOUSE_HUD_FIXED_ELEMENT` | 13 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SET_LAST_CREATED_UNIT_TO_REFERENCE` | 13 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `TEAM_EXIT_ALL_BUILDINGS` | 13 | Sim.act / Sim.cond 不认识 |
| 未做 | `GATE_CLOSE` | 12 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_GARRISON_NEAREST_BUILDING` | 12 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_SET_SPECIAL_POWER_COUNTDOWN` | 12 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleAfterburners` | 12 | 只记进时间线，没有效果 |
| 不涉及 | `OPTIONS_SET_OCCLUSION_MODE` | 12 | 纯表现（名字规则） |
| 未做 | `PLAYER_SELL_EVERYTHING` | 12 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER` | 12 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aipullback.py |
| 未做 | `TEAM_GARRISON_NEAREST_BUILDING` | 12 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_MOVE_TO_NEAREST_OBJECT_OF_KINDOF_OWNED_BY_PLAYER` | 12 | Sim.act / Sim.cond 不认识 |
| 未做 | `DISABLE_JOYPAD_COMMANDBAR_BUTTON` | 11 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `FLASH_JOYPAD_COMMANDBAR_BUTTON` | 11 | 纯表现（名字规则） |
| 不涉及 | `FLASH_JOYPAD_HUD_FIXED_ELEMENT` | 11 | 纯表现（名字规则） |
| 已对拍 | `NAMED_REMOVE_UPGRADE` | 11 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_invuln.py |
| 不涉及 | `ORE_NODE_SET_MAX_GATHER_VALUE` | 11 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ArcherArrowBarrageSpecialPower` | 10 | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanMCV` | 10 | Sim.act / Sim.cond 有分支 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackSovietMCV` | 10 | Sim.act / Sim.cond 有分支 |
| 未做 | `PLAYER_ENABLE_BASE_CONSTRUCTION` | 10 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `ROTATE_CAMERA` | 10 | 纯表现（名字规则） |
| 未做 | `SKIRMISH_AI_CONSIDER_ALL_ENEMIES_WHEN_BUILDING` | 10 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `ZOOM_CAMERA` | 10 | 纯表现（名字规则） |
| 已对拍 | `MAP_SHROUD_SET_RESHROUD_TIME` | 9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleHarpoonSpecialPower` | 9 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateLaserGlaiveBlastSpecialPower` | 9 | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackAlliedMiner` | 9 | Sim.act / Sim.cond 有分支 |
| 未做 | `PLAYER_DISABLE_UNIT_CONSTRUCTION` | 9 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_TOGGLE_SKIRMISH_AI` | 9 | Sim.act / Sim.cond 不认识 |
| 未做 | `SET_COUNTER_TO_NUMBER_OBJECTS_PLAYER_OWNS_WITH_KINDOF` | 9 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_AI_START` | 9 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SOUND_ENABLE_TYPE` | 9 | 纯表现（名字规则） |
| 推断 | `SUB_FROM_MSEC_TIMER` | 9 | 引擎模型核心 |
| 已对拍 | `TEAM_GUARD_AREA` | 9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 已对拍 | `TEAM_IDLE_FOR_FRAMECOUNT` | 9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 未做 | `TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE_OWNED_BY_PLAYER` | 9 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `COUNTER_MATH_VALUE` | 8 | 引擎模型核心；台上量过、测试对拍：checks/engine_contained.py |
| 未做 | `EXIT_SPECIFIC_BUILDING` | 8 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `FLASH_UI_PLAYER_POWER_BUTTON` | 8 | 纯表现（名字规则） |
| 已对拍 | `MAP_REVEAL_AT_WAYPOINT` | 8 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_CivilianStructureEvacuate` | 8 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleAlliedEngineerHeal` | 8 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_UnPackJapanBaseDefenseEgg` | 8 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateJumpSpecialPower` | 8 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateLeapSpecialPower` | 8 | Sim.act / Sim.cond 不认识 |
| 推断 | `RESTART_TIMER` | 8 | 引擎模型核心 |
| 已对拍 | `SET_COUNTER_TO_COUNTER` | 8 | 引擎模型核心；台上量过、测试对拍：checks/engine_contained.py |
| 未做 | `SET_PLAYER_KILLS_OF_TYPE_TO_COUNTER` | 8 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `CAMERA_STOP_FOLLOW` | 7 | 纯表现（名字规则） |
| 不涉及 | `FIRE_SPECIAL_POWER_ON_UNIT` | 7 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `NAMED_FACE_NAMED` | 7 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateRoarSpecialPower` | 7 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JAAS_Transform` | 7 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleMirageField` | 7 | 只记进时间线，没有效果 |
| 不涉及 | `PATH_MUSIC_ENABLE_DYNAMIC_SYSTEM` | 7 | 纯表现（名字规则） |
| 推断 | `TEAM_DELETE_LIVING` | 7 | Sim.act / Sim.cond 有分支 |
| 已对拍 | `UNIT_CHANGE_OBJECT_STATUS:NON_AUTOACQUIRABLE` | 7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_stasis.py |
| 已对拍 | `UNIT_CHANGE_OBJECT_STATUS:UNATTACKABLE` | 7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_crush.py |
| 未做 | `ATTACK_MOVE_TEAM_TO_NEAREST_OBJECT_OF_TYPE_OF_PLAYER` | 6 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `DISABLE_COUNTDOWN_TIMER_DISPLAY` | 6 | 纯表现（名字规则） |
| 未做 | `NAMED_FACE_WAYPOINT` | 6 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleBinaryWeapon` | 6 | 只记进时间线，没有效果 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanPowerPlantEgg` | 6 | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_ActivateRoarSpecialPower` | 6 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_TriggerRushAttackSpecialPower` | 6 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PLAYER_FIRE_MULTI_TARGET_SPECIAL_POWER_AT_WAYPOINTS` | 6 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `TEAM_LOAD_TRANSPORTS` | 6 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `UNIT_ENABLE_HOUSE_COLOR` | 6 | 纯表现（名字规则） |
| 不涉及 | `BORDER_SHROUD_SET_OPACITY` | 5 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `CAMERA_STOP_TETHER_NAMED` | 5 | 纯表现（名字规则） |
| 未做 | `FIRE_SPECIAL_POWER_ON_NEAREST_OBJECTTYPE_BY_PLAYER` | 5 | Sim.act / Sim.cond 不认识 |
| 未做 | `FIRE_SPECIAL_POWER_ON_TEAM` | 5 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `HIDE_UI` | 5 | 纯表现（名字规则） |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleDeployWeapon` | 5 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleRiotShieldSpecialPower` | 5 | 只记进时间线，没有效果 |
| 未做 | `TEAM_SET_HEALTH` | 5 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_MODELCONDITION_FOR_DURATION` | 5 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_SLEEP_STATUS` | 5 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `ENABLE_COUNTDOWN_TIMER_DISPLAY` | 4 | 纯表现（名字规则） |
| 未做 | `NAMED_ATTACK_AREA` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanMinerFromRefinery` | 4 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructSovietAntiVehicleVehicleTech2` | 4 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleJapanFortressShipTransformMode` | 4 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleMagneticArmor` | 4 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleShortCircuit` | 4 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_TriggerRushAttackSpecialPower` | 4 | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanBarracksEgg` | 4 | Sim.act / Sim.cond 有分支 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanRefineryEgg` | 4 | Sim.act / Sim.cond 有分支 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanWarFactoryEgg` | 4 | Sim.act / Sim.cond 有分支 |
| 未做 | `PLAYER_AI_CHANGEUNITBUILDER` | 4 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PLAYER_SET_DISABLED` | 4 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `SET_BLOOM_INTENSITY` | 4 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER_INCLUDE_DEAD` | 4 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SET_TEXTURE_LOOKUP_TABLE` | 4 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `SKIRMISH_AI_CLEAR_ALL_ENEMY_PLAYERS_PRIORITIES` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_FIRE_SPECIAL_POWER_AT_MOST_COST` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_CONTEXT_SENSITIVE_ATTACK` | 4 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `TEAM_ENABLE_HOUSE_COLOR` | 4 | 纯表现（名字规则） |
| 未做 | `TEAM_EXECUTE_SEQUENTIAL_SCRIPT` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_ATTACK_MOVE_TOWARDS_NEAREST_OBJECT_TYPE` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NO_COLLISIONS` | 4 | 状态位 NO_COLLISIONS 只记下来 |
| 已对拍 | `UNIT_GUARD_AREA` | 4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 未做 | `UNIT_GUARD_OBJECT` | 4 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `MAP_REVEAL_ALL` | 3 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JapanAntiInfantryInfantryBonzai` | 3 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleShieldSphere` | 3 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_CAMPAlliedBomberDrop1` | 3 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PATH_MUSIC_FADE_IN_MUSIC` | 3 | 纯表现（名字规则） |
| 不涉及 | `RESET_CAMERA_AT_OBJECT` | 3 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `SKIRMISH_AI_CLEAR_ENEMY_PLAYER_PRIORITY` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ATTACK_MOVE_TOWARDS_NEAREST_OBJECT_TYPE` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ENTER_NAMED` | 3 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `TEAM_FLASH_WHITE` | 3 | 纯表现（名字规则） |
| 推断 | `TEAM_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT` | 3 | Sim.act / Sim.cond 有分支 |
| 未做 | `TEAM_GUARD_OBJECT` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_MODELCONDITION` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_STOP_SEQUENTIAL_SCRIPT` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NEXT_MOVE_IS_REVERSE` | 3 | 状态位 NEXT_MOVE_IS_REVERSE 只记下来 |
| 推断 | `ADD_TO_MSEC_TIMER` | 2 | 引擎模型核心 |
| 不涉及 | `AUDIO_FADE_VOLUME` | 2 | 纯表现（名字规则） |
| 不涉及 | `AUDIO_POP_MUSIC` | 2 | 纯表现（名字规则） |
| 不涉及 | `AUDIO_SET_SOUNDEFFECTS_SLIDER_FADEABLE` | 2 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `DISABLE_BORDER_SHROUD` | 2 | 纯表现（名字规则） |
| 未做 | `DISABLE_UI_UNIT_ABILITY_BUTTON` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT:specialpowercampalliedbomberdrop2` | 2 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateDisguiseSpecialPower` | 2 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_AlliedAntiInfantryVehicleEvacuate` | 2 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JASV_FireKiCannon` | 2 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JapanEngineerSprint` | 2 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateCryoLeapSpecialPower` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_DisguisedEvacuate` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_SovietAntiGroundAircraftEvacuate` | 2 | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanNavalYardEgg` | 2 | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_ActivateDisguiseSpecialPower` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_AlliedSupportAircraftShrinkRay` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_CaptureBuilding` | 2 | 只记进时间线，没有效果 |
| 不涉及 | `OVERRIDE_GLOBAL_TERRAIN_HEIGHT` | 2 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `PATH_MUSIC_FADE_OUT_MUSIC` | 2 | 纯表现（名字规则） |
| 不涉及 | `PATH_MUSIC_STOP_MUSIC` | 2 | 纯表现（名字规则） |
| 不涉及 | `PLAYER_CAMERA_TETHER_NAMED` | 2 | 纯表现（名字规则） |
| 未做 | `PLAYER_DISABLE_FACTORIES` | 2 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SCREEN_SHAKE` | 2 | 纯表现（名字规则） |
| 已对拍 | `SET_PLAYER_MONEY_TO_COUNTER` | 2 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiopen.py |
| 推断 | `SET_RANDOM_TIMER` | 2 | 引擎模型核心 |
| 不涉及 | `SHOW_MISSION_OBJECTIVE` | 2 | 纯表现（名字规则） |
| 未做 | `SKIRMISH_AI_CONSIDER_ENEMY_WHEN_BUILDING` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_AI_USE_AUTOMATIC_ENEMY_PLAYER_PRIORITY_SCHEME` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ALL_USE_COMMANDBUTTON_ON_NEAREST_ENEMY_UNIT` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_FACE_WAYPOINT` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_GUARD_FOR_SECONDS` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_PARTIAL_USE_COMMANDBUTTON` | 2 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `TERRAIN_RENDER_DISABLE` | 2 | 纯表现（名字规则） |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:DYNAMICS_DISABLED` | 2 | 状态位 DYNAMICS_DISABLED 只记下来 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NO_AUTO_ACQUIRE` | 2 | 状态位 NO_AUTO_ACQUIRE 只记下来 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:WEAPON_UPGRADED_01` | 2 | 状态位 WEAPON_UPGRADED_01 只记下来 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:WEAPON_UPGRADED_02` | 2 | 状态位 WEAPON_UPGRADED_02 只记下来 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:WEAPON_UPGRADED_03` | 2 | 状态位 WEAPON_UPGRADED_03 只记下来 |
| 不涉及 | `CAMERA_BLOOM_EFFECT_BEGIN` | 1 | 纯表现（名字规则） |
| 不涉及 | `CAMERA_TETHER_NAMED` | 1 | 纯表现（名字规则） |
| 未做 | `DAMAGE_MEMBERS_OF_TEAM` | 1 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `FREEZE_TIME` | 1 | 纯表现（名字规则） |
| 推断 | `MARK_MISSION_OBJECTIVE_NOT_COMPLETED` | 1 | 引擎模型核心 |
| 不涉及 | `MOVE_TEAM_TO_UNIT` | 1 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `MUSIC_SET_TRACK` | 1 | 纯表现（名字规则） |
| 不涉及 | `MUSIC_SET_VOLUME` | 1 | 纯表现（名字规则） |
| 未做 | `NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT:specialpowernanoswarmhive` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_SET_SLEEP_STATUS` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateBribeSpecialPower` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateYurikoShieldRank3` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanAntiInfantryVehicle` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanAntiStructureVehicle` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanAntiVehicleShip` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanAntiVehicleVehicleTech1` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanAntiVehicleVehicleTech3` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanSentinelVehicle` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_Evacuate` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_PackAlliedMCV` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_PackJapanMCV` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_PackSovietMCV` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_PsyonicBlastSpecialPower` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_TimeBeltSpecialPower` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleAlliedGunshipAircraft` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleTargetPainter` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_UnPackAlliedMCV` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_UnPackJapanMCV` | 1 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_PackJapanMCV` | 1 | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackSovietSurveyor` | 1 | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_VacuumBomb` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_ActivateLaserGlaiveBlastSpecialPower` | 1 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PATH_MUSIC_ENABLE_RESUME_SYSTEM` | 1 | 纯表现（名字规则） |
| 不涉及 | `PITCH_CAMERA` | 1 | 纯表现（名字规则） |
| 未做 | `PLAYER_AI_CHANGEBASEBUILDER` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_AI_CHANGESCIENCEUPGRADER` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_AI_CHANGETEAMBUILDER` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_AI_CHANGE_ECONOMY_MANAGER` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_EXIT_ALL_BUILDINGS` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_UNIT_TYPE_SPECIAL_POWER_IGNORE_REQUIREMENTS` | 1 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `RESUME_BACKGROUND_SOUNDS` | 1 | 纯表现（名字规则） |
| 未做 | `SKIRMISH_AI_DONT_CONSIDER_ENEMY_WHEN_BUILDING` | 1 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SOUND_AMBIENT_PAUSE` | 1 | 纯表现（名字规则） |
| 不涉及 | `SOUND_AMBIENT_RESUME` | 1 | 纯表现（名字规则） |
| 不涉及 | `SOUND_ENABLE_ALL` | 1 | 纯表现（名字规则） |
| 不涉及 | `SUSPEND_BACKGROUND_SOUNDS` | 1 | 纯表现（名字规则） |
| 未做 | `TEAM_CLEAR_MODELCONDITION` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_FACE_NAMED` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_REMOVE_ALL_OVERRIDE_RELATIONS` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_EXPERIENCE_POINTS` | 1 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `TOGGLE_SHADER_OVERRIDE` | 1 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `UNFREEZE_TIME` | 1 | 纯表现（名字规则） |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:CAN_ATTACK` | 1 | 状态位 CAN_ATTACK 只记下来 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NO_BRIBE` | 1 | 状态位 NO_BRIBE 只记下来 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:UNDER_FROZEN` | 1 | 状态位 UNDER_FROZEN 只记下来 |
| 未做 | `UNIT_GIVE_EXPERIENCE_POINTS` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_GUARD_AREA_FROM_POSITION` | 1 | Sim.act / Sim.cond 不认识 |

## 脚本条件

| 状态 | 名字 | 用量 | 说明 |
|---|---|---|---|
| 已对拍 | `FLAG` | 5099 | 引擎模型核心；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | `TIMER_EXPIRED` | 3917 | 引擎模型核心；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `CONDITION_TRUE` | 2947 | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `NAMED_DESTROYED` | 922 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_immortal.py |
| 已对拍 | `PLAYER_HAS_OBJECT_COMPARISON` | 628 | tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back |
| 已对拍 | `COUNTER` | 577 | 引擎模型核心；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | `HAS_FINISHED_AUDIO` | 495 | tests/test_simbench.py::test_audio_a_dubbed_line_is_done_its_length_after_it_is_heard |
| 已对拍 | `PLAYER_IS_HUMAN_OR_AI_PERSONALITY` | 470 | tests/test_simbench.py::test_scripts1_conditions_as_the_bench |
| 已对拍 | `HAS_FINISHED_VIDEO` | 422 | tests/test_simbench.py::test_video_a_radar_clip_is_done_after_its_length_full_screen_never |
| 已对拍 | `NAMED_INSIDE_AREA` | 413 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_block.py |
| 已对拍 | `SKIRMISH_PLAYER_HAS_UNITS_IN_AREA` | 410 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_area.py |
| 已对拍 | `NAMED_OWNED_BY_PLAYER` | 397 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_garrison.py |
| 已对拍 | `NAMED_NOT_DESTROYED` | 374 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_contained.py |
| 已对拍 | `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA` | 278 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | `NAMED_ATTACKED_BY_PLAYER` | 150 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attack.py |
| 已对拍 | `UNIT_HAS_OBJECT_STATUS` | 142 | tests/test_simbench.py::test_scripts1_conditions_as_the_bench |
| 已对拍 | `COUNTER_SECONDS` | 141 | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `UNIT_HEALTH` | 134 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_air.py |
| 未做 | `MISSION_HOT_SPOT_ACTIVE` | 110 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_DISCOVERED` | 104 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 未做 | `TEAM_ATTACKED_BY_PLAYER` | 93 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_HAS_MODELCONDITION` | 88 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_INSIDE_AREA_PARTIALLY` | 80 | Sim.act / Sim.cond 不认识 |
| 未做 | `ENEMY_SIGHTED_BY_TEAM` | 69 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `IS_OBJECT_OF_TYPE` | 69 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 推断 | `CAMERA_ENTERED_AREA` | 60 | Sim.act / Sim.cond 有分支 |
| 未做 | `ENEMY_SIGHTED` | 59 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `COUNTER_COUNTER` | 55 | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 未做 | `NAMED_SELECTED` | 50 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_DISCOVERED` | 47 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER` | 44 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_HAS_UNITS` | 39 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_OUTSIDE_AREA` | 38 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_air.py |
| 未做 | `TYPE_SELECTED` | 38 | Sim.act / Sim.cond 不认识 |
| 推断 | `TEAM_DESTROYED` | 35 | Sim.act / Sim.cond 有分支；台上量过（checks/engine_team.py），没有测试跑这个台子 |
| 未做 | `TEAM_INSIDE_AREA_ENTIRELY` | 33 | Sim.act / Sim.cond 不认识 |
| 未做 | `DISTANCE_BETWEEN_TEAM` | 32 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_KILLED_TYPE_UNITS` | 29 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA` | 28 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_spawn.py |
| 已对拍 | `PLAYER_HAS_PLAYER_TECH` | 26 | tests/test_simbench.py::test_protocol_rank_two_at_frame_5400 |
| 未做 | `DISTANCE_BETWEEN_OBJ` | 25 | Sim.act / Sim.cond 不认识 |
| 推断 | `CURRENT_PLATFORM` | 24 | Sim.act / Sim.cond 有分支 |
| 未做 | `PLAYER_HAS_KILLED_NAMED_UNIT` | 24 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_HAS_KILLED_COMPARISON_UNIT_TYPE` | 21 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_CREATED` | 20 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ALL_HAS_OBJECT_STATUS` | 18 | Sim.act / Sim.cond 不认识 |
| 未做 | `TYPE_SIGHTED` | 17 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_SPECIAL_POWER_READY` | 16 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SOME_HAVE_OBJECT_STATUS` | 15 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_BUILDING_IS_EMPTY` | 13 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_HAS_FEWER_THAN_X_UNITS_WITH_KINDOF` | 12 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_ATTACKED_BY_OBJECTTYPE` | 10 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `OBJECT_IS_DISGUISED_AS_TYPE` | 10 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `PLAYER_HAS_COMPARISON_POWER_POINTS` | 10 | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 未做 | `TEAM_ATTACKED_BY_OBJECTTYPE` | 10 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_COMPARE_NUM_MEMBERS` | 10 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA_WITH_MODELCONDITION` | 9 | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `PLAYER_HAS_POWER` | 9 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `PLAYER_TRIGGERED_SPECIAL_POWER` | 9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8b.py |
| 未做 | `BUILT_BY_PLAYER` | 8 | Sim.act / Sim.cond 不认识 |
| 未做 | `GATE_IS_OPEN` | 8 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_DESTROYED_N_BUILDINGS_PLAYER` | 8 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_CREDITS` | 8 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED` | 8 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_EXITED_AREA` | 7 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_SPECIAL_POWER_READY` | 7 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_NO_POWER` | 6 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `PLAYER_EXCESS_POWER_COMPARE_VALUE` | 5 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_sell.py |
| 推断 | `PLAYER_TRIGGERED_SPECIAL_POWER_FROM_NAMED` | 5 | Sim.act / Sim.cond 有分支 |
| 未做 | `PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS` | 4 | Sim.act / Sim.cond 不认识 |
| 推断 | `PLAYER_TRIGGERED_SPECIAL_POWER_IN_AREA` | 4 | Sim.act / Sim.cond 有分支 |
| 未做 | `TEAM_CAN_PATH_TO_WAYPOINT` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_COMPARISON_UNIT_KIND` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_COMMAND_BUTTON_READY_PARTIAL` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_DESTROYED_BY_OBJECTTYPE` | 2 | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_DYING` | 2 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_crush.py |
| 未做 | `PLAYER_HAS_NUMBER_OBJECTS_WITH_MODELCONDITION` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_LOST_OBJECT_TYPE` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ENTERED_AREA_PARTIALLY` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_IS_ATTACKED_AND_CANNOT_RETALIATE_ANY` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_OUTSIDE_AREA_ENTIRELY` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_HAS_UPGRADE` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `BUILDING_GARRISONNED_BY_OBJECT_TYPE` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `EVAL_TEAM_HEALTH` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA_COMPLETELY_BUILT` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_NUM_UNITS_WITH_UPGRADE` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_TRIGGERED_SCRIPT_EVENT` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_EXITED_AREA_PARTIALLY` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_OWNED_BY_PLAYER` | 1 | Sim.act / Sim.cond 不认识 |

## 物体模块

| 状态 | 名字 | 用量 | 说明 |
|---|---|---|---|
| 不涉及 | `Draws/ScriptedModelDraw` | 1895 (2888) | 纯表现（Draws）；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 已对拍 | `Body/PropBody` | 1443 (2758) | tests/test_simbench_c.py::test_prop_body_no_health_a_kill_leaves_the_street_and_topples_the_tree_and_lantern_at_the_bench_frames；例：AlliedAirField_Collapse, AlliedAntiAirShip_Collapse |
| 不涉及 | `Behaviors/FXListBehavior` | 796 (1241) | 纯表现（名字规则）；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 已对拍 | `Body/ActiveBody` | 790 (1398) | tests/test_simbench.py::test_super_the_proton_collider_ends_as_the_bench；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 不涉及 | `Behaviors/ObjectDefectionHelper` | 640 (1059) | 没人触发：原版只在 BaseObject 挂一个空的（所以每个物体都有），SageXML 里没有一处 DefectorSpecialPower，脚本动作表里也没有叛变；《将军》里它管"叛变后一段时间不被发现"；例：AlliedSatelliteSweepShroudRevealer, AlliedTimeBombLvl1 |
| 不涉及 | `Behaviors/ObjectSMCHelper` | 640 (1059) | 纯表现：《将军》ObjectSMCHelper 到时清掉"定时模型状态"（UNIT_SET_MODELCONDITION_GENERIC 的秒数），只换画法；例：AlliedSatelliteSweepShroudRevealer, AlliedTimeBombLvl1 |
| 已对拍 | `Behaviors/AttributeModifierPoolUpdate` | 622 (910) | tests/test_simbench.py::test_super_the_iron_curtain_holds_off_fire_some_23_seconds；例：AlliedAntiVehicleVehicleTech3CannonNodeBase, AlliedAntiVehicleVehicleTech3CannonNodeEnd |
| 已对拍 | `Behaviors/SecondaryDamageTracker` | 617 (852) | tests/test_simbench.py::test_cryo_a_frozen_tank_melts_334_frames_after_the_beam_whatever_the_beam；例：AlliedSatelliteSweepShroudRevealer, AlliedTimeBombLvl1 |
| 已对拍 | `Behaviors/CreateObjectDie` | 591 (838) | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_crush.py；例：AlliedAntiGroundAircraft_Dying, AlliedBomberAircraft_Dying |
| 已对拍 | `Behaviors/DestroyDie` | 578 (1006) | tests/test_simbench.py::test_destroy_die_a_building_killed_is_dying_one_frame_and_gone；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 已对拍 | `Behaviors/SquishCollide` | 569 (749) | tests/test_simbench.py::test_crush_a_tank_drives_over_a_lower_level_and_leaves_an_equal_one；例：AlliedSatelliteSweepShroudRevealer, AlliedWallPiece |
| 已对拍 | `Behaviors/SlowDeath` | 565 (1480) | tests/test_simbench.py::test_slow_death_a_crushed_conscript_lies_127_frames_dying_and_in_its_spot；例：AlliedAirField_Collapse, AlliedAntiAirShip_Collapse |
| 不涉及 | `Behaviors/BuildingDestructionBehavior` | 493 (650) | 纯表现：建筑死后按骨骼放特效、甩碎块（CreationObject 如 AlliedBarracks_Debris：只有画法、寿命和碎片体积，没有身体和武器）、烟尘；例：AlliedAirfield, AlliedBarracks |
| 不涉及 | `ClientBehaviors/ModelConditionAudioLoopClientBehavior` | 466 (649) | 纯表现（ClientBehaviors）；例：AlliedSatelliteSweepShroudRevealer, AlliedAirfield |
| 不涉及 | `Behaviors/Physics:不动` | 454 (630) | 模板上没有 AIUpdate 类模块（不能下命令、没有移动器）：默认物理不让它自己动，被甩飞、击飞另算（DynamicsUpdate、MetaImpactNugget）；原版字段全是默认（E 线 work/re/e_na_physics_mcu.md） |
| 已对拍 | `Behaviors/ProductionUpdate` | 351 (465) | tests/test_simbench.py::test_production_pays_as_it_builds_and_comes_out_after_the_door；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | `Behaviors/ToppleUpdate` | 347 (410) | tests/test_simbench_c.py::test_topple_the_five_props_disappear_at_the_bench_frames_without_ever_dying；例：BaseTopple, BaseTree |
| 不涉及 | `Behaviors/ModelConditionUpgrade` | 341 (465) | 纯表现：只加模型状态（民房/步兵按阵营换画法、支援技能画法），同模板的非画法模块和原版脚本 UNIT_HAS_MODELCONDITION 都不读（E 线 work/re/e_na_physics_mcu.md）；例：AlliedAntiInfantryInfantry, AlliedAntiVehicleInfantry |
| 已对拍 | `Behaviors/BuildingBehavior` | 334 (440) | tests/test_simbench.py::test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | `Behaviors/AttributeModifierAuraUpdate` | 311 (420) | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_invuln.py；例：A09_IronCurtainEffect, BaseCivilianStructure |
| 已对拍 | `Behaviors/InvisibilityBehavior` | 305 (412) | tests/test_simbench_c.py::test_invisibility_behavior_a_house_given_garrison_can_stealth_by_script_is_shot_like_a_plain_one；例：BaseCivilianStructure, BaseCivilianStructureLarge |
| 已对拍 | `Behaviors/ContestableGarrisonContain` | 305 (411) | tests/test_simbench_c.py::test_garrison_script_entry_skips_room_and_relation_owner_follows_and_damage_or_kill_ejects_alive_at_the_bench；例：BaseCivilianStructure, BaseCivilianStructureLarge |
| 不涉及 | `Draws/PropDraw` | 221 (301) | 纯表现（Draws）；例：AM_Trash01, AM_Debris01 |
| 已对拍 | `Behaviors/FireWeaponWhenDead` | 146 (230) | tests/test_simbench_c.py::test_fire_weapon_when_dead_a_scripted_kill_blows_the_mig_and_the_guardian_beside_it；例：AlliedAntiGroundAircraft_Dying, AlliedAntiStructureVehicleCannonEffect |
| 未做 | `Behaviors/Physics` | 143 (206) | 移动物理（坠落、弹跳、被击飞、倾倒）：模拟器走路按速度直走，没有物理；例：AlliedAntiGroundAircraft_Dying, AlliedBomberAircraft_Dying |
| 不涉及 | `ClientBehaviors/ModelConditionSoundSelectorClientBehavior` | 140 (195) | 纯表现（ClientBehaviors）；例：AlliedSatelliteSweepShroudRevealer, AlliedAirfield |
| 不涉及 | `Draws/DynamicsDraw` | 138 (857) | 纯表现（Draws）；例：AlliedAirField_Collapse, AlliedAntiAirShip_Collapse |
| 已对拍 | `Behaviors/EnableDynamicsCollide` | 137 (154) | tests/test_simbench_c.py::test_enable_dynamics_collide_a_lantern_without_it_is_crushed_and_gone_at_the_same_frames；例：BaseSimulatedProp, AM_Boat01 |
| 已对拍 | `AI/AIUpdate` | 136 (237) | tests/test_simbench.py::test_r8_idle_within_sight_walks_up_fires_and_comes_back；例：AlliedSatelliteSweepShroudRevealer, AlliedSuperWeaponEffect |
| 已对拍 | `Behaviors/StancesBehavior` | 108 (148) | tests/test_simbench_c.py::test_stance_hold_fire_stops_a_standing_attack_order；例：AlliedSatelliteSweepShroudRevealer, AlliedAirfield |
| 已对拍 | `Body/ImmortalBody` | 91 (111) | tests/test_simbench_c.py::test_immortal_damage_stops_at_one_hp_kill_is_damage_and_delete_removes；例：BaseRock, CPDummyTarget |
| 未做 | `Behaviors/LevelUpUpgrade` | 88 (124) | 模拟器代码里没有这个名字；例：AlliedSatelliteSweepShroudRevealer, AlliedAntiAirShip |
| 已对拍 | `Behaviors/AutoHealBehavior` | 88 (123) | tests/test_simbench.py::test_autoheal_an_apocalypse_mends_two_points_every_7_frames_after_a_15_frame_wait；例：AlliedSatelliteSweepShroudRevealer, AlliedAntiAirShip |
| 已对拍 | `Behaviors/RunOffMapBehavior` | 88 (123) | tests/test_simbench_c.py::test_run_off_map_the_peacekeeper_is_gone_64_and_304_frames_after_the_order_never_dying；例：AlliedSatelliteSweepShroudRevealer, AlliedAntiAirShip |
| 已对拍 | `Behaviors/WeaponSetUpdate` | 82 (110) | tests/test_simbench_c.py::test_weapon_set_the_status_picks_the_gun_molotov_under_the_toggle_and_the_painter_does_no_harm；例：AlliedBaseDefense, AlliedBaseDefenseAdvanced |
| 已对拍 | `Behaviors/SpecialPower` | 74 (95) | tests/test_simbench.py::test_super_a_scripts_cast_starts_the_retail_reload；例：AlliedConstructionYard, AlliedAntiAirShip |
| 未做 | `Behaviors/EngineerContain` | 70 (105) | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | `Behaviors/DynamicsUpdate` | 69 (101) | tests/test_simbench_c.py::test_dynamics_update_a_hammer_without_it_crushes_and_goes_round_as_the_retail_one；例：AlliedDynamicsImpact, AlliedSatelliteSweepShroudRevealer |
| 未做 | `Behaviors/RepairUpdate` | 66 (91) | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | `Behaviors/StatusBitsUpgrade` | 66 (85) | tests/test_simbench_c.py::test_status_bits_upgrade_the_heroic_grant_sets_weapon_upgraded_and_a_removal_clears_it；例：AlliedBaseDefense, AlliedAntiAirShip |
| 已对拍 | `Behaviors/StructureUnpackUpdate` | 59 (96) | tests/test_simbench.py::test_power_back_after_the_plant_unpacks；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | `Behaviors/StructureSellUpdate` | 52 (72) | tests/test_simbench.py::test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames；例：AlliedAirfield, AlliedBarracks |
| 不涉及 | `ClientBehaviors/AnimationSoundClientBehavior` | 48 (67) | 纯表现（ClientBehaviors）；例：AlliedTimeBombLvl3, AlliedRefinery |
| 不涉及 | `Behaviors/DynamicsUpdate:起义专有` | 44 (53) | 起义时刻专有模板：继承链上的父模板 RA3 数据里没有（SS_Fling* 的 BaseClientFlingableProp），RA3 的 mod 编不过（engine_dynamics c，11-10 地图编译报 Critical），玩家在 RA3 里见不到 |
| 不涉及 | `Draws/TruckDraw` | 35 (51) | 纯表现（Draws）；例：AlliedTimeBombLvl1, AlliedTimeBombLvl2 |
| 未做 | `Behaviors/InfiltratorContain` | 34 (38) | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 未做 | `Behaviors/LUAEventList` | 32 (44) | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 未做 | `Behaviors/ToggleStatusSpecialAbilityUpdate` | 27 (34) | 已核（11-08）：模拟器没有这个效果（没有按钮切换状态）；例：AlliedAntiAirShip, AlliedAntiInfantryInfantry |
| 不涉及 | `Behaviors/SubObjectsUpgrade` | 26 (30) | 纯表现（名字规则）；例：AlliedAirfield, AlliedBarracks |
| 未做 | `Behaviors/FreefallUpdate` | 24 (31) | 模拟器代码里没有这个名字；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 已对拍 | `Behaviors/AttributeModifierUpgrade` | 22 (30) | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_invuln.py；例：AlliedOutpost, AlliedAntiGroundAircraft |
| 已对拍 | `Behaviors/CrushDie` | 22 (28) | tests/test_simbench.py::test_crush_a_tank_drives_over_a_lower_level_and_leaves_an_equal_one；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 推断 | `Behaviors/SuppressionUpdate` | 22 (28) | 部分：阈值>=50、SPEED/ARMOR 75%已实测；短贡献寿命与晚恢复56帧未解释，不登记整项已对拍；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 不涉及 | `Draws/LaserDraw` | 21 (37) | 纯表现（Draws）；例：AlliedAntiVehicleVehicleTech3CannonNodeBase, AlliedAntiVehicleVehicleTech3CannonNodeEnd |
| 未做 | `Behaviors/LaserState` | 19 (25) | 模拟器代码里没有这个名字；**待核**：台上量过（checks/engine_laser.py），可能用别的名字实现了；例：AlliedBaseDefense, AlliedBaseDefenseAdvanced |
| 未做 | `Behaviors/QueueProductionExitUpdate` | 19 (20) | 模拟器代码里没有这个名字；例：AlliedBarracks, AlliedConstructionYard |
| 未做 | `Behaviors/ReplaceSelfSpecialAbility` | 18 (24) | 已核（11-08）：模拟器没有这个效果（没有换形态）；例：AlliedConstructionYard, AlliedMCV |
| 不涉及 | `Draws/TracerModelDraw` | 18 (22) | 纯表现（Draws）；例：AlliedAntiAirShip, AlliedAntiAirVehicleTech1 |
| 未做 | `Behaviors/WeaponFireSpecialAbilityUpdate` | 16 (23) | 模拟器代码里没有这个名字；例：AlliedSuperWeaponAdvanced, AlliedAntiNavalScout |
| 未做 | `Body/ManagerBody` | 14 (32) | 模拟器代码里没有这个名字；例：BaseBridge, BaseCivilianBridge |
| 未做 | `Behaviors/BridgeBuilder` | 14 (30) | 模拟器代码里没有这个名字；例：AM_Bridge_01, AM_Bridge_01a |
| 未做 | `AI/JetAIUpdate` | 13 (17) | 模拟器代码里没有这个名字；例：AlliedAntiGroundAircraft, AlliedAttackDrone |
| 未做 | `Behaviors/TransportContain` | 13 (16) | 模拟器代码里没有这个名字；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryVehicle |
| 未做 | `Behaviors/SpawnBehavior` | 10 (16) | 已核（11-08）：模拟器没有这个效果（没有母体造随从）；例：AlliedAirfield, AlliedConstructionYardRepairBay |
| 未做 | `Behaviors/ProductionUpdateInfo` | 9 (9) | 模拟器代码里没有这个名字；例：AlliedConstructionYard, AlliedMCV |
| 未做 | `Behaviors/EjectPassengersSpecialAbilityUpdate` | 7 (8) | 模拟器代码里没有这个名字；例：AlliedBomberAircraft, A08_CenturyTransportAircraft |
| 未做 | `Behaviors/BezierProjectile` | 6 (78) | 已核（11-08）：模拟器没有这个效果（开火按每秒伤害直接扣血，没有弹体）；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 未做 | `Behaviors/AssignSlavesTargetObjectSpecialPower` | 6 (10) | 模拟器代码里没有这个名字；例：AlliedConstructionYardRepairBay, AlliedNavalYard |
| 未做 | `Behaviors/TrackDamage` | 6 (9) | 模拟器代码里没有这个名字；例：AlliedAntiNavalScout, AlliedFighterAircraft |
| 未做 | `Behaviors/TrackIncomingWeaponFireBehavior` | 6 (9) | 模拟器代码里没有这个名字；例：AlliedAntiNavalScout, AlliedFighterAircraft |
| 未做 | `Behaviors/OCLSpecialPower` | 6 (7) | 模拟器代码里没有这个名字；例：AlliedSuperWeaponAdvanced, CAMP_PowerStore_AlliedBomberDrop |
| 未做 | `Behaviors/SubStructureStorageBehavior` | 6 (6) | 模拟器代码里没有这个名字；例：AlliedMCV, AlliedMCV_Naval |
| 未做 | `Behaviors/WallBuilderBehavior` | 6 (6) | 模拟器代码里没有这个名字；例：AlliedWallPiece, AlliedWallSegmentPiece |
| 未做 | `Behaviors/PassiveAreaEffectBehavior` | 5 (14) | 模拟器代码里没有这个名字；例：AlliedAirfieldRepairDrone, AlliedEngineer |
| 未做 | `Behaviors/EmotionTrackerUpdate` | 5 (7) | 模拟器代码里没有这个名字；例：AlliedCommandoTech1, AlliedEngineer |
| 未做 | `Behaviors/MonitorSpecialPowerTimerUpdate` | 5 (6) | 模拟器代码里没有这个名字；例：AlliedSuperWeapon, AlliedSuperWeaponAdvanced |
| 未做 | `Behaviors/AttackAssistResponseBehavior` | 5 (5) | 模拟器代码里没有这个名字；例：AlliedBaseDefenseAdvanced, SovietBaseDefenseAdvanced |
| 未做 | `Behaviors/CaptureSpecialAbilityUpdate` | 5 (5) | 模拟器代码里没有这个名字；例：AlliedCommandoTech1, AlliedEngineer |
| 推断 | `Behaviors/CommandSetUpgrade` | 5 (5) | 模拟器代码里有这个名字；例：AlliedConstructionYard, AlliedOutpost |
| 未做 | `Behaviors/QueueDockBehavior` | 4 (12) | 模拟器代码里没有这个名字；例：AlliedRefinery, AlliedRefinery_NoHarvester |
| 推断 | `Behaviors/AutoDepositUpdate` | 4 (8) | 模拟器代码里有这个名字；例：GE_SwissBank, NY_NYStockExchange |
| 未做 | `Behaviors/ActivateModuleSpecialPower` | 4 (5) | 模拟器代码里没有这个名字；例：AlliedAntiStructureVehicle, JapanAntiVehicleVehicleTech1 |
| 未做 | `Behaviors/RadarBehavior` | 4 (5) | 模拟器代码里没有这个名字；例：AlliedRadarDish, PlayerSpellBook |
| 推断 | `Behaviors/SpecialAbilityUpdate` | 4 (5) | 模拟器代码里有这个名字；例：JapanAntiInfantryInfantry, JapanAntiVehicleVehicleTech1 |
| 推断 | `Behaviors/TechUpgradeReceiver` | 4 (5) | 模拟器代码里有这个名字；例：AlliedAirfield, AlliedBarracks |
| 未做 | `Behaviors/HealCrateCollide` | 4 (4) | 模拟器代码里没有这个名字；例：SS_SecretFile1, SS_SecretFile2 |
| 未做 | `Behaviors/ParkingPlaceBehavior` | 4 (4) | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedAntiStructureShip |
| 未做 | `Behaviors/SpecialDisguiseUpdate` | 4 (4) | 模拟器代码里没有这个名字；例：AlliedAntiVehicleVehicleTech3, AlliedInfiltrationInfantry |
| 未做 | `Behaviors/AttachUpdate` | 3 (24) | 已核（11-08）：模拟器没有这个效果（没有附着）；例：ChronoTargetMarker, AlliedAirfieldRepairDrone |
| 未做 | `Behaviors/StealthDetectorUpdate` | 3 (8) | 已核（11-08）：模拟器没有这个效果（没有反隐）；例：AlliedScoutInfantry, A08_Dog1 |
| 未做 | `Behaviors/SlaughterHordeContain` | 3 (6) | 模拟器代码里没有这个名字；**待核**：台上量过（checks/engine_aipullback.py），可能用别的名字实现了；例：AlliedAntiStructureShip, S08_AlliedAntiStructureShip |
| 未做 | `AI/AnimalAIUpdate` | 3 (4) | 模拟器代码里没有这个名字；例：BaseCivilian, CivilianFemale1 |
| 未做 | `Behaviors/AssistedPlacementBehavior` | 3 (4) | 模拟器代码里没有这个名字；例：AlliedRefinery, AlliedRefinery_NoHarvester |
| 未做 | `Behaviors/LoseHealthUpdate` | 3 (4) | 模拟器代码里没有这个名字；例：SovietAntiStructureShip, SovietBomberAircraft |
| 未做 | `Behaviors/MovementSpecialPower` | 3 (4) | 模拟器代码里没有这个名字；例：JapanAntiStructureShip, JapanAntiVehicleVehicleTech3 |
| 未做 | `Behaviors/SecondaryObjectListenerModule` | 3 (4) | 模拟器代码里没有这个名字；例：AlliedBaseDefense, AlliedAntiAirVehicleTech1 |
| 未做 | `Behaviors/StructurePlacementBehavior` | 3 (4) | 模拟器代码里没有这个名字；例：AlliedRefinery, AlliedRefinery_NoHarvester |
| 未做 | `Behaviors/HitReactionBehavior` | 3 (3) | 模拟器代码里没有这个名字；例：AlliedAntiInfantryInfantry, JapanEmperor |
| 未做 | `Behaviors/LiftObjectUpdate` | 3 (3) | 模拟器代码里没有这个名字；例：AlliedBaseDefense, AlliedAntiAirVehicleTech1 |
| 未做 | `Behaviors/ReturnToProducerSpecialPower` | 3 (3) | 模拟器代码里没有这个名字；例：AlliedAntiGroundAircraft, AlliedFighterAircraft |
| 未做 | `Behaviors/SubStructureBehavior` | 2 (11) | 模拟器代码里没有这个名字；例：AlliedConstructionYardRepairBay, AlliedCrane |
| 未做 | `Behaviors/AttributeCrateCollide` | 2 (3) | 模拟器代码里没有这个名字；例：SS_SecretFile1, SS_SecretFile2 |
| 未做 | `Behaviors/ConvergingLaserState` | 2 (3) | 模拟器代码里没有这个名字；例：AlliedAntiStructureVehicle, SovietAntiVehicleVehicleTech1 |
| 未做 | `Behaviors/AimWeapon` | 2 (2) | 模拟器代码里没有这个名字；例：AlliedAntiVehicleInfantry, SovietAntiVehicleInfantry |
| 未做 | `Behaviors/GateOpenAndCloseBehavior` | 2 (2) | 模拟器代码里没有这个名字；例：RM_AlliedBlastDoor, SS_Door |
| 已对拍 | `Behaviors/InvisibilityBroadcastUpdate` | 2 (2) | tests/test_simbench_c.py::test_invisibility_broadcast_the_aura_holds_its_guardian_at_full_health_and_the_control_dies；例：AlliedAntiVehicleVehicleTech3, A08_SpecialMirageTank |
| 未做 | `Behaviors/NotifyWhenAttackingBehavior` | 2 (2) | 模拟器代码里没有这个名字；例：AlliedBaseDefenseAdvanced, SovietBaseDefenseAdvanced |
| 未做 | `Behaviors/PowerUpgrade` | 2 (2) | 模拟器代码里没有这个名字；例：SovietPowerPlantAdvanced, SovietPowerPlant |
| 未做 | `Behaviors/PrematureDischargeSpecialPower` | 2 (2) | 模拟器代码里没有这个名字；例：JapanBaseDefenseAdvanced, JapanAntiStructureVehicle |
| 未做 | `Behaviors/RecallUnitsSpecialPower` | 2 (2) | 模拟器代码里没有这个名字；例：AlliedAirfield, SovietAirfield |
| 未做 | `Behaviors/SpiderHoleUpdate` | 2 (2) | 模拟器代码里没有这个名字；例：JapanAntiVehicleInfantry, JapanAntiVehicleInfantry_Ambush |
| 已对拍 | `Behaviors/TechUpgrade` | 2 (2) | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_tech.py；例：AlliedConstructionYard, AlliedOutpost |
| 已对拍 | `Behaviors/LifetimeUpdate` | 1 (855) | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_crush.py；例：AlliedAirField_Collapse, AlliedAntiAirShip_Collapse |
| 推断 | `Behaviors/FireWeaponUpdate` | 1 (21) | 部分：simunits.ocl_round 把召出物的 FireWeaponNugget + LifetimeUpdate 折成伤害，不模拟召出物本身；例：AlliedAntiStructureVehicleCannonEffect, AlliedAntiStructureVehicleCannonEffect_Vet |
| 已对拍 | `Behaviors/OreNodeBehavior` | 1 (8) | tests/test_simbench.py::test_mining_a_second_miner_on_one_node_adds_nothing；例：BaseOreNode, OreNode |
| 未做 | `Behaviors/AssistedPlacementInfoBehavior` | 1 (7) | 模拟器代码里没有这个名字；例：OreNode, OreNode2a |
| 已对拍 | `Behaviors/OreMinerBehavior` | 1 (7) | tests/test_simbench.py::test_mining_pays_8_a_frame_and_a_trip_takes_269；例：AlliedMiner, AlliedMiner_Naval |
| 未做 | `Behaviors/FireWeaponCollide` | 1 (4) | 模拟器代码里没有这个名字；例：SovietAntiVehicleInfantry, JapanAntiVehicleShipTorpedoSpreadProjectile |
| 未做 | `Behaviors/StrafeAreaUpdate` | 1 (3) | 模拟器代码里没有这个名字；例：AlliedSatelliteSweepShroudRevealer, JapanFinalSquadronAircraft |
| 不涉及 | `Behaviors/AudioLoopUpgrade` | 1 (2) | 纯表现（名字规则）；例：SovietAntiVehicleVehicleTech1, Tutorial_SovietTech1Tank |
| 推断 | `Behaviors/GarrisonContain` | 1 (2) | simgarrison 同一套规则（不可争夺）；没单独上台对拍；例：AlliedBaseDefense, SovietBunker |
| 未做 | `Behaviors/MoneyCrateCollide` | 1 (2) | 模拟器代码里没有这个名字；例：MoneyCrate, MoneyCrateMP |
| 未做 | `Behaviors/MonitorConditionUpdate` | 1 (2) | 模拟器代码里没有这个名字；例：JapanMiner, JapanMiner_Naval |
| 未做 | `Behaviors/OCLMonitorUpdate` | 1 (2) | 模拟器代码里没有这个名字；例：SovietCommandoTech1, Soviet_BombingRun |
| 未做 | `Behaviors/ObjectCreationUpgrade` | 1 (2) | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech1, Tutorial_SovietTech1Tank |
| 未做 | `Behaviors/SlaveWatcherBehavior` | 1 (2) | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech1, Tutorial_SovietTech1Tank |
| 未做 | `Behaviors/StoreObjectsSpecialPower` | 1 (2) | 已核（11-08）：模拟器没有这个效果（没有存放单位）；例：AlliedSuperWeapon, PlayerSpellBook |
| 未做 | `Behaviors/SwitchLocomotorUpdate` | 1 (2) | 模拟器代码里没有这个名字；例：SovietBomberAircraft, SovietBomberAircraft_Special |
| 未做 | `Behaviors/TeleportStoredObjectsSpecialPower` | 1 (2) | 已核（11-08）：模拟器没有这个效果（没有传送存放的单位）；例：AlliedSuperWeapon, PlayerSpellBook |
| 未做 | `Behaviors/TeleportStoredObjectsUpdate` | 1 (2) | 已核（11-08）：模拟器没有这个效果（UNIT_TELEPORT_TO_WAYPOINT 另算）；例：AlliedSuperWeapon, PlayerSpellBook |
| 未做 | `Behaviors/VeterancyCrateCollide` | 1 (2) | 模拟器代码里没有这个名字；例：VeterancyCrate, VeterancyCrateMP |
| 未做 | `Behaviors/ActivateSpecialPowerOnCreate` | 1 (1) | 模拟器代码里没有这个名字；例：JapanAntiVehicleInfantry_Ambush |
| 已对拍 | `Behaviors/AssembleStructureSpecialAbilityUpdate` | 1 (1) | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_skill.py；例：SovietEngineer |
| 未做 | `Behaviors/ChargeWeaponUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：JapanBaseDefenseAdvanced |
| 未做 | `Behaviors/CircularDamageUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：SovietAntiNavyShipTech1 |
| 未做 | `Behaviors/DieOnProducerDeathUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：AlliedAttackDrone |
| 未做 | `Behaviors/DominateEnemySpecialPower` | 1 (1) | 模拟器代码里没有这个名字；例：AlliedInfiltrationInfantry |
| 未做 | `Behaviors/GrapplingHookUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech3 |
| 已对拍 | `Behaviors/LinearDamageUpdate` | 1 (1) | tests/test_simsweep.py::test_sweep_the_line_walks_out_and_a_stop_does_not_cut_it_at_the_bench_frames；例：AlliedAntiNavalScout |
| 未做 | `Behaviors/MagneticEffectUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：AlliedAntiNavyShipTech1 |
| 未做 | `Behaviors/ReconstituteStateSpecialAbility` | 1 (1) | 模拟器代码里没有这个名字；例：AlliedCommandoTech1 |
| 未做 | `Behaviors/ShieldSphereUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：AlliedAntiStructureVehicle |
| 未做 | `Behaviors/StoreCurrentStateUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：AlliedCommandoTech1 |
| 未做 | `Behaviors/SweepingLaserState` | 1 (1) | 模拟器代码里没有这个名字；例：SovietScoutVehicle |
| 不涉及 | `Behaviors/TimedOpacityUpdate` | 1 (1) | 纯表现（名字规则）；例：JapanInfiltrationInfantry |
| 不涉及 | `ClientBehaviors/ModelConditionEvaEventSelectorClientBehavior` | 1 (1) | 纯表现（ClientBehaviors）；例：AlliedInfiltrationInfantry |
| 不涉及 | `ClientBehaviors/UpgradeSoundSelectorClientBehavior` | 1 (1) | 纯表现（ClientBehaviors）；例：AlliedAntiAirVehicleTech1 |
| 不涉及 | `Draws/TankDraw` | 1 (1) | 纯表现（Draws）；例：SovietAntiVehicleVehicleTech2 |
| 未做 | `Body/ManagedImmortalBody` | 0 (44) | 模拟器代码里没有这个名字；例：BaseIndestructableBridgeSegment, BaseBridgeEnd |
| 未做 | `Body/ManagedActiveBody` | 0 (31) | 模拟器代码里没有这个名字；例：BaseBridgeSegment, AM_Bridge_01_Center |
| 未做 | `Behaviors/ProjectileUpdate` | 0 (18) | 已核（11-08）：模拟器没有这个效果（开火按每秒伤害直接扣血，没有弹体飞行时间）；例：AlliedAntiVehicleVehicleTech1Projectile, AlliedBomberAircraftBombProjectile |
| 未做 | `Behaviors/LaserScatterUpdate` | 0 (10) | 模拟器代码里没有这个名字；例：AlliedAntiVehicleVehicleTech3CannonNodeBase, AlliedAntiVehicleVehicleTech3CannonNodeEnd |
| 未做 | `Behaviors/SlavedUpdate` | 0 (9) | 已核（11-08）：模拟器没有这个效果（没有随从跟随）；例：AlliedAirfieldRepairDrone, AlliedAttackDrone_Leeched |
| 未做 | `Behaviors/BombardAreaUpdate` | 0 (8) | 模拟器代码里没有这个名字；例：BaseBalloonBombEffect, BalloonBombEffectLvl1 |
| 未做 | `Behaviors/WeaponScatterEffectUpdate` | 0 (8) | 模拟器代码里没有这个名字；例：AlliedAntiVehicleVehicleTech3CannonNodeEnd, AlliedAntiVehicleVehicleTech3CannonNodeRegular |
| 未做 | `Behaviors/DestroyObjectsUpdate` | 0 (7) | 模拟器代码里没有这个名字；例：AlliedAntiStructureVehicleCannonEffect, AlliedAntiStructureVehicleCannonEffect_Vet |
| 未做 | `Body/HighlanderBody` | 0 (5) | 模拟器代码里没有这个名字；例：BaseMountRushmoreHead, MR_LaserMtRushmore_Jefferson_Ready |
| 未做 | `Behaviors/StrafeAreaTargetChooser` | 0 (4) | 模拟器代码里没有这个名字；例：JapanFinalSquadronAircraft, JapanFinalSquadronSeed_L1 |
| 未做 | `Behaviors/InvalidTargetsDeathUpdate` | 0 (3) | 模拟器代码里没有这个名字；例：AlliedProtonColliderBeacon, SovietBombingRunBeacon |
| 未做 | `Behaviors/ParabolicCurveUpdate` | 0 (3) | 模拟器代码里没有这个名字；例：AlliedSupersonicBomber, SovietSupportBomber |
| 未做 | `Behaviors/SelectiveVisibilityBehavior` | 0 (3) | 模拟器代码里没有这个名字；例：ChronoTargetMarker, MultiplayerBeacon |
| 未做 | `Behaviors/SuckUpObjectsUpdate` | 0 (3) | 模拟器代码里没有这个名字；例：MagneticSatelliteEffectLvl1, MagneticSatelliteEffectLvl2 |
| 未做 | `Behaviors/CrateCollide` | 0 (2) | 模拟器代码里没有这个名字；例：BombCrate, ShroudCrate |
| 未做 | `Behaviors/SetLocomotorSpeedUpdate` | 0 (2) | 模拟器代码里没有这个名字；例：BaseCivilianAuto, CUAuto01 |
| 未做 | `Behaviors/ShipSlowDeath` | 0 (2) | 模拟器代码里没有这个名字；例：SovietBomberAircraft_Dying, SovietBomberAircraft_Special_Dying |
| 未做 | `AI/HordeAIUpdate` | 0 (1) | 模拟器代码里没有这个名字；例：YOURSQUAD |
| 未做 | `Behaviors/CaptureAndGiveUpgradeBehavior` | 0 (1) | 模拟器代码里没有这个名字；例：VeterancyTechStructure |
| 未做 | `Behaviors/DistributeEnergyToAlliesBehavior` | 0 (1) | 模拟器代码里没有这个名字；例：NeutralPowerPlant |
| 未做 | `Behaviors/EncloseBehavior` | 0 (1) | 模拟器代码里没有这个名字；例：NanoSwarmHiveEffect |
| 未做 | `Behaviors/EnergyDisablingBehavior` | 0 (1) | 模拟器代码里没有这个名字；例：EnergyDisabler |
| 未做 | `Behaviors/GatherEjectUpdate` | 0 (1) | 模拟器代码里没有这个名字；例：VacuumBombEffect |
| 未做 | `Behaviors/GiveProductionBonusSpecialPower` | 0 (1) | 模拟器代码里没有这个名字；例：PlayerSpellBook |
| 未做 | `Behaviors/HeightDieUpdate` | 0 (1) | 模拟器代码里没有这个名字；例：JapanBalloonBomb |
| 未做 | `Behaviors/HordeContain` | 0 (1) | 模拟器代码里没有这个名字；例：YOURSQUAD |
| 未做 | `Behaviors/LineSegmentDamageUpdate` | 0 (1) | 模拟器代码里没有这个名字；例：IrradiatedTargetDamageDealer |
| 未做 | `Behaviors/MoneyGainAttachUpdate` | 0 (1) | 模拟器代码里没有这个名字；例：SovietProductionKickbackHelper |
| 未做 | `Behaviors/PlayerPowerManager` | 0 (1) | 模拟器代码里没有这个名字；例：PlayerSpellBook |
| 未做 | `Behaviors/PlayerUpgradeSpecialPower` | 0 (1) | 模拟器代码里没有这个名字；例：PlayerSpellBook |
| 未做 | `Behaviors/RandomCrateCollide` | 0 (1) | 模拟器代码里没有这个名字；例：RandomCrate |
| 未做 | `Behaviors/RenderStoredThingTemplate` | 0 (1) | 模拟器代码里没有这个名字；例：OrbitalRefuseRandomDebris |
| 未做 | `Behaviors/SalvageCrateCollide` | 0 (1) | 模拟器代码里没有这个名字；例：SalvageCrate |
| 未做 | `Behaviors/SpawnCrateUpdate` | 0 (1) | 模拟器代码里没有这个名字；例：GenericCrateSpawner |
| 未做 | `Behaviors/SqueezeFlingUpdate` | 0 (1) | 模拟器代码里没有这个名字；例：MagneticSingularityEffect |
| 未做 | `Behaviors/StoreTemplateIDBehavior` | 0 (1) | 模拟器代码里没有这个名字；例：PlayerSpellBook |
| 未做 | `Behaviors/UnitCrateCollide` | 0 (1) | 模拟器代码里没有这个名字；例：UnitCrate |
| 未做 | `Behaviors/UnitVisionBehavior` | 0 (1) | 模拟器代码里没有这个名字；例：UnitVisionObserver |

## 武器效果

| 状态 | 名字 | 用量 | 说明 |
|---|---|---|---|
| 已对拍 | `DamageNugget` | 183 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_clip.py；例：BaseExplodingPropVehicleWeapon, MountRushmoreHeadEyeWeapon |
| 已对拍 | `ProjectileNugget` | 88 | tests/test_simbench_c.py::test_projectile_nugget_flight_uses_retail_shell_speed_and_resolved_warhead；例：BB_EuropeCoastalGunWeapon, KremlinArtilleryDomeMissle |
| 未做 | `InformTargetNugget` | 69 | engine_inform仅隔离并用伤害；目标对来弹的响应尚未模拟，不以HP隔离检查登记整项已对拍；例：BB_EuropeCoastalGunWeapon, AlliedPrecisionBomb |
| 推断 | `SuppressionNugget` | 64 | 部分：长3s贡献48/50阈值已实测；1s贡献与恢复时序未解释，不登记整项已对拍；例：BB_EuropeCoastalGunWeapon, KremlinArtilleryDomeMissle |
| 未做 | `MetaImpactNugget` | 36 | 模拟器代码里没有这个名字；**待核**：台上量过（checks/engine_knock_probe.py），可能用别的名字实现了；例：KremlinArtilleryDomeMissleWarhead, AlliedTimeBomb_Level1 |
| 不涉及 | `ActivateLaserNugget` | 27 | 纯表现：Lifetime/LaserId/HitGroundFX/OverShootDistance驱动LaserState/LaserDraw；engine_laser pair实测2/90/2/90，无附加伤害或首发延迟，test_simbench_c重放；例：MountRushmoreHeadEyeWeapon, JapanAntiVehicleInfantryTech3LockDownGun |
| 已对拍 | `WeaponOCLNugget` | 26 | tests/test_simbench_c.py::test_weapon_ocl_lifetime_damage_reads_the_fire_delay_before_counting_updates；例：MountRushmoreHeadEyeWeapon, AlliedPrecisionBombWarhead |
| 已对拍 | `AttributeModifierNugget` | 20 | tests/test_simbench_c.py::test_weaponfx_predictions_and_finite_bursts；例：NanoHiveSwarmEffectTrigger, JapanCommandoSoftLanding |
| 已对拍 | `ParalyzeNugget` | 11 | tests/test_simbench_c.py::test_weapon_first_hit_is_observed_one_frame_after_the_order_script；例：JapanAntiVehicleInfantryTech3LockDownGun, AlliedAntiStructureShipEMPCruiseMissleWarhead |
| 不涉及 | `TintObjectsNugget` | 9 | 纯表现：Color及Pre/Sustained/PostColorTime、Frequency/Amplitude仅控制染色动画；engine_tint pair实测2/90/2/90，独立DamageNugget解释全部伤害，test_simbench_c重放；不声称像素已验证；例：SovietCommandoCallBombingRun, AlliedCommandoAttachWeapon |
| 未做 | `ActivateLiftObjectNugget` | 6 | 模拟器代码里没有这个名字；例：JapanCommandoTech1PsyonicCrush, JapanCommandoTech1AirborneKiller |
| 已对拍 | `LineDamageNugget` | 6 | tests/test_simbench_c.py::test_weaponfx_predictions_and_finite_bursts；例：SovietCommandoSniperRifle, AAAVT1_SovietCommandoSniperRifle |
| 未做 | `SpecialPowerNugget` | 6 | 模拟器代码里没有这个名字；例：SovietCommandoCallBombingRun, AlliedAntiVehicleVehicleTech1TargetPainter |
| 未做 | `FireOnObjectsNugget` | 5 | 未实现：子武器派发条件与空间锚点尚未解释；失败诊断不作为已对拍依据；例：PlayerPowerJapanEmperorsResolveWeapon_L1, PlayerPowerJapanEmperorsResolveWeapon_L2 |
| 已对拍 | `SecondaryDamageNugget` | 5 | tests/test_simbench_c.py::test_secondary_damage_delivers_one_amount_at_hit_without_damaging_health；例：MountRushmoreHeadEyeWeapon, AlliedCryoSatelliteLvl1 |
| 未做 | `AttachNugget` | 4 | 模拟器代码里没有这个名字；例：AlliedCommandoAttachWeapon, SovietAntiVehicleInfantryMagneticBombAttachWeapon |
| 已对拍 | `StripMaxHealthPercentNugget` | 3 | tests/test_simbench_c.py::test_strip_max_health_percent_uses_maximum_at_full_and_half_health；例：JapanCommandoTech1PsyonicCrush, AAAVT1_JapanCommandoTech1PsyonicCrush |
| 已对拍 | `ActivateLinearDamageNugget` | 2 | tests/test_simsweep.py::test_sweep_a_killed_shooters_line_stops_with_it_and_the_second_ones_rows_are_hit；例：AlliedAntiNavalScoutSonar, AlliedAntiNavalScoutSonarForBridges |
| 已对拍 | `DamageContainedNugget` | 2 | tests/test_simbench_c.py::test_damage_contained_limits_eligible_passengers_without_damaging_the_others；例：SovietAntiInfantryInfantryMolotovCocktailWarhead, Weapon_DesolatorBombFieldUpdate |
| 已对拍 | `LeechPercentMaxHealthDamageNugget` | 2 | tests/test_simbench_c.py::test_leech_percent_uses_victim_maximum_not_current_health_or_caster_maximum；例：SovietCrushWeapon, SovietHarpoonCrushWeapon |
| 未做 | `ReportWeaponFiredStatNugget` | 2 | 模拟器代码里没有这个名字；例：SovietVacuumBomb, ParticleCannonWeapon |
| 未做 | `ActivateCircularDamageNugget` | 1 | 模拟器代码里没有这个名字；例：SovietAntiNavyShipTech1TeslaNova |
| 已对拍 | `DOTNugget` | 1 | tests/test_simbench_c.py::test_dot_counts_interval_ticks_for_two_durations_and_observes_first_damage_frame；例：PlayerPowerIrradiateTargetWeapon |
| 未做 | `GrapplingHookNugget` | 1 | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech3Harpoon |
| 已对拍 | `LeechHealthDamageNugget` | 1 | tests/test_simbench_c.py::test_leech_health_heals_from_damage_and_respects_the_heal_fraction；例：SovietAntiVehicleVehicleTech1LeechBeamWeapon |

## AI

| 状态 | 名字 | 用量 | 说明 |
|---|---|---|---|
| 已对拍 | `开局/Order.Build` | 635 | docs/engine/aiopen.md#读数（aiopen f1～f3：造的顺序和 AlliedStandard 单子一样） |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType` | 392 | docs/engine/aitactics.md#读数（ClosestStructure / SafestToGroundStructure 是 EnemyStructure，FriendlyLandStructure 是 FriendlyStructure，都上台） |
| 未做 | `造兵/BuildEntry.Heuristic` | 380 | AI 模型代码里没有这个名字 |
| 未做 | `造兵/BuildEntry.Build` | 364 | AI 模型代码里没有这个名字 |
| 已对拍 | `组队招人/ObjectFilter.ExcludeThing` | 288 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 已对拍 | `战略状态/TargetHeuristic.TargetHeuristic` | 287 | docs/engine/aitactics.md#读数（aitargetnear / aitargetsafe：按状态写的目标启发挑楼） |
| 已对拍 | `战略状态/StrategicState.Difficulty` | 268 | docs/engine/aistate.md#按难度挂的状态（aidiff / aidiffx：普通 = MEDIUM，没挂 MEDIUM 的状态不跑） |
| 已对拍 | `战略状态/StrategicState.State` | 268 | docs/engine/aistate.md#读数（人格只留台上写的状态，AI 只跑这些：aistateconst / aistateslash 等） |
| 已对拍 | `目标/AITargetingHeuristic.Name` | 241 | docs/engine/ainamed.md#给关卡线的结论（ainmfar 点名物件不管远近、ainmwp 走到路点守着、ainmnone 名字查不到不派队，全 PASS） |
| 不涉及 | `表现/FeedbackEntry.FeedbackKey` | 238 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/FeedbackEntry.FeedbackTo` | 238 | 纯表现（语音、视频、画面） |
| 已对拍 | `开局/Order.Time` | 237 | docs/engine/aiopen.md#开局里的 Time 从什么时候算（aiotime：从唤醒起的绝对时刻） |
| 已对拍 | `战术/Tactic.Tactic` | 184 | docs/engine/aitactics.md#读数（SimpleAttack / DefenseAvoidanceAttack / FlankAttack / StaticDefense 上台） |
| 已对拍 | `组队招人/TeamTemplate.AlwaysRecruit` | 182 | 台上量过（engine_aiteamfilter aiar0～3，第 90 轮）、测试对拍 tests/test_simai_bench_b.py：关着新造的车留家、开着出门的队把它招走、满员不招、不预放时第一辆自己组队（模拟器每次晚 3～4 s）；模拟器多造第 3、4 辆是造兵的缺口（strict xfail），不是这个开关 |
| 已对拍 | `组队招人/TeamTemplate.MicroManager` | 182 | 台上量过（engine_airetreat：airet / airet0 只差 MicroManager 指名的那份数据里的 RetreatPowerAdvantage，一个撤一个不撤；aipas1 / aipas0 只差 EngagePassiveTargets）、测试对拍 tests/test_simai.py——队伍跑的是 MicroManager 指名的那份微操数据；指名不存在的 id 会怎样没量 |
| 已对拍 | `组队招人/TeamTemplate.MinUnits` | 182 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `组队招人/TeamTemplate.Priority` | 182 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | `战略状态/TargetHeuristic.Priority` | 170 | docs/engine/aitactics.md#目标挑哪个（aitpphi / aitpplo：同一状态两条目标启发，Priority 高的先试，两向都上台） |
| 已对拍 | `组队招人/TeamTemplate.ExcludeKindOf` | 170 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 已对拍 | `组队招人/TeamTemplate.IncludeKindOf` | 170 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 已对拍 | `组队招人/TeamTemplate.MaxUnits` | 170 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 不涉及 | `表现/FeedbackEntry.Video` | 168 | 纯表现（语音、视频、画面） |
| 已对拍 | `战略状态/AIStrategicStateDefinition.MaxTargets` | 156 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `组队招人/ObjectFilter.Rule` | 155 | docs/engine/aistate.md#队伍招谁（aitfany / aitfnone / aitfall：ANY、NONE + 名单只要名单，ALL + 排除名单） |
| 已对拍 | `目标/AITargetingHeuristic.RequireUniqueTarget` | 154 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | `战术/Tactic.EndBehavior` | 152 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | `组队招人/ObjectFilter.IncludeThing` | 152 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 已对拍 | `组队招人/TeamTemplate.RegisteredObjectSet` | 148 | docs/engine/aistate.md#移动方式和对象集（第 81 轮） |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=NamedObject` | 145 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_ainamed.py |
| 已对拍 | `组队招人/TeamTemplate.AllowedLocomotorTypes` | 145 | docs/engine/aistate.md#移动方式和对象集（第 81 轮） |
| 已对拍 | `目标/AITargetingHeuristic.VitalKindOf` | 129 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 已对拍 | `组队招人/TeamTemplate.Priority=STANDARD` | 126 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | `启发条件/ConstantHeuristic` | 119 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipoweradv.py |
| 已对拍 | `人格/PowerChoice.PlayerPower` | 117 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipower.py |
| 已对拍 | `人格/PowerChoice.Weight` | 117 | docs/engine/aiopen.md#买协议（aipwrb 权重 0 的不买） |
| 已对拍 | `战术/Tactic.EndBehavior=DISBAND` | 105 | docs/engine/aitactics.md#目标没了以后（EndBehavior，2026-11-09 各一次）（aiendd：目标没了队伍解散、状态重派去兵营，和模型对上） |
| 已对拍 | `目标/AITargetingHeuristic.ForbiddenKindOf` | 102 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 已对拍 | `微操/AIMicroManagerData.RetreatPowerAdvantage` | 94 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_airetreat.py |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=Waypoint` | 94 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_ainamed.py |
| 已对拍 | `人格/UnitModifier.DefensiveModifier` | 92 | 台上量过（engine_aiskirm u：aiskmod 把维和、标枪的 UnitModifier 两个系数都设 0，造兵逐秒和原版 aiskirm c 一样）、测试对拍 tests/test_simai.py——没有选兵策略表时 UnitModifier 不影响造什么；有策略表时的打分没量（原版人格都没有） |
| 已对拍 | `人格/UnitModifier.OffensiveModifier` | 92 | 台上量过（engine_aiskirm u：aiskmod 把维和、标枪的 UnitModifier 两个系数都设 0，造兵逐秒和原版 aiskirm c 一样）、测试对拍 tests/test_simai.py——没有选兵策略表时 UnitModifier 不影响造什么；有策略表时的打分没量（原版人格都没有） |
| 已对拍 | `人格/UnitModifier.Unit` | 92 | 台上量过（engine_aiskirm u：aiskmod 把维和、标枪的 UnitModifier 两个系数都设 0，造兵逐秒和原版 aiskirm c 一样）、测试对拍 tests/test_simai.py——没有选兵策略表时 UnitModifier 不影响造什么；有策略表时的打分没量（原版人格都没有） |
| 已对拍 | `战术/Tactic.DisbandAfterRetreatTeamSize` | 86 | 台上量过（engine_airetreat：airetf 0 撤回家后再出门，airetfd 999 撤回家后一直在家——撤退结束那轮人数 ≤ 它就结束战术、放人）、测试对拍 tests/test_simai.py；1 / 4 / 5 这种"剩几人才散"的中间值没量 |
| 已对拍 | `微操/AIMicroManagerData.EnterGarrisons` | 84 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aigarrison.py |
| 未做 | `造兵/BuildState.Difficulty` | 84 | AI 模型代码里没有这个名字 |
| 未做 | `造兵/BuildState.State` | 84 | AI 模型代码里没有这个名字 |
| 已对拍 | `微操/AIMicroManagerData.UseSpecialPowers` | 83 | 台上量过（engine_aimicro：aimicspon 开 两个武士 s41 冲锋，aimicspoff 关 一直没冲、s51 前被打死，脚本按的对照照样冲）、测试对拍 tests/test_simai.py（模拟器读进探针自写的微操数据：开的想冲、关的从不冲；技能本身模拟器没接，只记"想用"） |
| 推断 | `微操/AIMicroManagerData.EngageHostileTargets` | 82 | 台上 aimicspon（开）/ aimicengoff（关）两个武士都在家跟征召兵打、都冲锋活到最后——关掉不让队伍躲开战斗；差别只在首次冲锋：关 ~258 帧、开 ~362 帧（各两次一致）。模拟器开关都冲，但先后相反（关 ~457、开 ~275），tests/test_simai.py strict xfail；私有模型里的打分式没读（按"杀死所需秒数"推断） |
| 已对拍 | `微操/AIMicroManagerData.EngagePassiveTargets` | 82 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_airetreat.py |
| 推断 | `开局/Order.Account` | 81 | AI 模型代码里读了这个名字 |
| 已对拍 | `开局/Order.Deposit` | 81 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（aiom15：带 Deposit 2000 照造、晚 4 秒） |
| 推断 | `微操/AIMicroManagerData.EngageTacticalTarget` | 79 | AI 模型代码里读了这个名字 |
| 已对拍 | `微操/AIMicroManagerData.PullbackInjured` | 78 | 只认车能开进去的维修设施：苏联 AI + 吊车，残血坦克回去被回收（aipullsov PASS）；盟军 / 日本工厂找不到（aiteamstate.md 第 6 节） |
| 推断 | `微操/AIMicroManagerData.Crush` | 77 | 台上量过（engine_aicrush：开了 s28 前碾光守军）；模拟器不会碾压，tests/test_simai_bench_b.py 只对上"关着不碾"，开着是 strict xfail |
| 已对拍 | `目标/AITargetingHeuristic.SortType` | 76 | docs/engine/aitactics.md#目标挑哪个（Distance：aitpnear / aitpmt2 最近、次近；ThreatToGround：aitargetsafe） |
| 推断 | `组队招人/TeamTemplate.SortByDistance` | 75 | AI 模型代码里读了这个名字（台上没单独量：engine_aiskirm 里是推测） |
| 推断 | `微操/AIMicroManagerData.ReverseMove` | 74 | 推断（台上未复现）：锤子 airev / airevp / airevt 都不倒车；剩门队员有没有当前攻击目标，量法见 handoff-b 第 73 节 |
| 推断 | `目标/AITargetingHeuristic.Location` | 74 | AI 模型代码里读了这个名字 |
| 推断 | `组队招人/TeamTemplate.ReleaseType` | 71 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.EnemySearchDistanceVisionMultiplier` | 70 | AI 模型代码里读了这个名字 |
| 不涉及 | `表现/FeedbackEntry.EvaEvent` | 70 | 纯表现（语音、视频、画面） |
| 已对拍 | `启发条件/EnemyNearbyHeuristic` | 68 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/EnemyNearbyHeuristic.Distance` | 68 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/EnemyNearbyHeuristic.EnemyNearby` | 68 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/ObjectOfTypeExistsHeuristic` | 67 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/ObjectOfTypeExistsHeuristic.PassIfExists` | 67 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `组队招人/ObjectFilter.Relationship` | 67 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 推断 | `开局/SkirmishOpeningMove.Side` | 64 | AI 模型代码里读了这个名字 |
| 已对拍 | `组队招人/TeamTemplate.MinPowerAdvantage` | 64 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 推断 | `人格/SpecificUnitCap.Cap` | 60 | AI 模型代码里读了这个名字 |
| 推断 | `人格/SpecificUnitCap.Difficulty` | 60 | AI 模型代码里读了这个名字 |
| 推断 | `人格/SpecificUnitCap.Unit` | 60 | AI 模型代码里读了这个名字 |
| 已对拍 | `组队招人/CreateUnits.MaxUnits` | 60 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 推断 | `组队招人/CreateUnits.MinUnits` | 60 | AI 模型代码里读了这个名字（台上量的是 TeamTemplate.MinUnits，不是现造兵） |
| 推断 | `组队招人/CreateUnits.UnitName` | 60 | AI 模型代码里读了这个名字 |
| 已对拍 | `战术/Tactic.Tactic=SimpleAttack` | 59 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 不涉及 | `表现/FeedbackEntry.Timeout` | 56 | 纯表现（语音、视频、画面） |
| 未做 | `造兵/BuildEntry.PercentHigh` | 54 | AI 模型代码里没有这个名字 |
| 未做 | `造兵/BuildEntry.PercentLow` | 54 | AI 模型代码里没有这个名字 |
| 已对拍 | `微操/AIMicroManagerData.UseGatherState` | 51 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipullback.py |
| 已对拍 | `启发条件/OpeningMoveHeuristic` | 47 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiomove.py |
| 已对拍 | `启发条件/OpeningMoveHeuristic.Complete` | 47 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiomove.py |
| 已对拍 | `开局/OpeningMove.Difficulty` | 46 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（aiodf / aiodf2：只留 MEDIUM 的） |
| 已对拍 | `开局/OpeningMove.Name` | 46 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（每个探针按名字挂自写开局，都照它造） |
| 已对拍 | `开局/OpeningMove.Weight` | 46 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（aiowt / aiowt2：0% 永远抽不到） |
| 已对拍 | `战术/Tactic.EndBehavior=RAMPAGE` | 46 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_ainamed.py |
| 已对拍 | `组队招人/TeamTemplate.ReleaseType=RELEASE_TO_PRIORITY` | 46 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `启发条件/PathToTargetHeuristic` | 45 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiopath.py |
| 推断 | `启发条件/PathToTargetHeuristic.LocomotorConditionToUseForTest` | 45 | AI 模型代码里读了这个名字 |
| 已对拍 | `启发条件/PathToTargetHeuristic.ObjectTypeToUseForTest` | 45 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiopath.py |
| 已对拍 | `启发条件/PathToTargetHeuristic.PathExists` | 45 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiopath.py |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=EnemyUnit` | 44 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 已对拍 | `战术/Tactic.Tactic=DefenseAvoidanceAttack` | 43 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 推断 | `战术/Tactic.Distance` | 41 | AI 模型代码里读了这个名字 |
| 已对拍 | `微操/AIMicroManagerData.RetreatMinDistanceFromBase` | 40 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_airetreat.py |
| 推断 | `战术/Tactic.UseAestheticsManager` | 40 | AI 模型代码里读了这个名字 |
| 已对拍 | `目标/AITargetingHeuristic.Relationship` | 40 | docs/engine/ainamed.md#给关卡线的结论（ainmrel：写了 Relationship 就按关系过滤，玩家的楼当 NEUTRAL 不算，不出门） |
| 未做 | `造兵/BlockIfThingNearFactory.IncludeThing` | 40 | AI 模型代码里没有这个名字 |
| 推断 | `微操/AIMicroManagerData.RetreatMinDistanceToFallback` | 38 | AI 模型代码里读了这个名字 |
| 已对拍 | `目标/AITargetingHeuristic.SortType=Distance` | 37 | docs/engine/aitactics.md#目标挑哪个（aitpnear 挑最近、aitpmt2 第二槽挑次近、aitpvk 显式写 Distance） |
| 未做 | `人格/AIPersonalityDefinition.PersonalityType` | 35 | AI 模型代码里没有这个名字 |
| 未做 | `造兵/BuildEntry.MinTime` | 34 | AI 模型代码里没有这个名字 |
| 推断 | `启发条件/IsBuildingHeuristic` | 30 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/IsBuildingHeuristic.KindOf` | 30 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/IsBuildingHeuristic.PassIfBuilding` | 30 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.PullbackInjuredHealthPct` | 30 | 30% 低于 0.35 时苏联坦克会撤（aipullsov），阈值边界没量 |
| 推断 | `微操/AIMicroManagerData.AlphaStrikeTargetHealthPct` | 28 | AI 模型代码里读了这个名字 |
| 已对拍 | `战术/Tactic.Tactic=StaticDefense` | 28 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aidefense.py |
| 未做 | `造兵/BlockIfThingNearFactory.Relationship` | 28 | AI 模型代码里没有这个名字 |
| 未做 | `造兵/BlockIfThingNearFactory.Rule` | 28 | AI 模型代码里没有这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=FriendlyUnit` | 27 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.UpdateTime` | 26 | 台上量过（engine_aidefense aidefctl4：每圈晚 1～2 s）；模拟器 4 s 与 1 s 逐秒相同（tests/test_simai_bench_b.py strict xfail） |
| 已对拍 | `启发条件/TimerHeuristic` | 25 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/TimerHeuristic.EndTime` | 25 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/TimerHeuristic.StartTime` | 25 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=EnemyStructure` | 25 | docs/engine/aitactics.md#读数（ClosestStructureHeuristic、SafestToGroundStructureHeuristic：aitargetnear / aitargetsafe） |
| 推断 | `组队招人/TeamTemplate.ReleaseType=NEVER_RELEASE` | 25 | AI 模型代码里读了这个名字 |
| 推断 | `战术/Tactic.Tactic=Engineer` | 24 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.EnterBaseDefensesWhenIdle` | 23 | 台上量过（engine_aibasedef：s21 起 1 人进炮塔）；模拟器没人进炮塔，只对上总开关关着的情形（strict xfail） |
| 已对拍 | `启发条件/IntervalHeuristic` | 22 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/IntervalHeuristic.ActiveTime` | 22 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/IntervalHeuristic.IntervalTime` | 22 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 推断 | `微操/AIMicroManagerData.EnterGarrisonableStructureDistance` | 21 | AI 模型代码里读了这个名字 |
| 未做 | `人格/AIPersonalityDefinition.SkirmishPersonality` | 20 | AI 模型代码里没有这个名字 |
| 已对拍 | `战术/Tactic.EndIfStateTurnsOff` | 19 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 推断 | `经济/AccountShare.Account` | 18 | AI 模型代码里读了这个名字 |
| 推断 | `经济/AccountShare.Percent` | 18 | AI 模型代码里读了这个名字 |
| 推断 | `人格/BaseSelection.PreferredNotBaseTypes` | 17 | AI 模型代码里读了这个名字 |
| 推断 | `人格/BaseSelection.SortOrder` | 17 | AI 模型代码里读了这个名字 |
| 已对拍 | `启发条件/TimerHeuristic.CountFrom` | 16 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 未做 | `战略状态/AIStrategicStateDefinition.CannotAttackTargetReaction` | 16 | AI 模型代码里没有这个名字 |
| 已对拍 | `战略状态/AIStrategicStateDefinition.MaxRunningCopies` | 16 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 未做 | `造兵/BuildEntry.Upgrade` | 16 | AI 模型代码里没有这个名字 |
| 推断 | `人格/BaseSelection.PreferredBaseTypes` | 15 | AI 模型代码里读了这个名字 |
| 推断 | `人格/BaseSelection.SortOrder=PREFER_OLDEST` | 15 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/ConstantHeuristic.Weight` | 15 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/IntervalHeuristic.CountFrom` | 15 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/TechBuildingShareHeuristic` | 15 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/TechBuildingShareHeuristic.Above` | 15 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/TechBuildingShareHeuristic.PercentOfFairShare` | 15 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.AlphaStrikeTargetTimeToKill` | 15 | AI 模型代码里读了这个名字 |
| 未做 | `微操/AIMicroManagerData.DodgeThreats` | 15 | AI 模型代码里没有这个名字 |
| 已对拍 | `微操/IgnoreTargets.IncludeThing` | 15 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 推断 | `目标/AITargetingHeuristic.HighestPriorityEnemyPlayersOnly` | 15 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.MinDistanceFromEnemy` | 15 | AI 模型代码里读了这个名字 |
| 已对拍 | `组队招人/TeamTemplate.Priority=LOW` | 15 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 未做 | `造兵/BuildEntry.CountModifier` | 15 | AI 模型代码里没有这个名字 |
| 不涉及 | `人格/AIPersonalityDefinition.PersonalityUIName` | 14 | 纯表现（语音、视频、画面） |
| 推断 | `目标/AITargetingHeuristic.SortType=ThreatToWater` | 14 | AI 模型代码里读了这个名字 |
| 推断 | `人格/AIPersonalityDefinition.Side` | 13 | AI 模型代码里读了这个名字 |
| 推断 | `微操/IgnoreTargets.Rule` | 13 | AI 模型代码里读了这个名字 |
| 已对拍 | `组队招人/TeamTemplate.Priority=DEFENSE` | 13 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 推断 | `启发条件/AllNearbyNodesFullHeuristic` | 12 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.CrushPreference` | 12 | 同 Crush：模拟器不会碾压（engine_aicrush，strict xfail） |
| 推断 | `微操/AIMicroManagerData.RandomTargetScoreModifier` | 12 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.TimeToKeepTargetMax` | 12 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.TimeToKeepTargetMin` | 12 | AI 模型代码里读了这个名字 |
| 推断 | `战术/Tactic.Tactic=SimpleExpansion` | 12 | AI 模型代码里读了这个名字 |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=Expansion` | 12 | AI 模型代码里没有这个名字 |
| 已对拍 | `目标/AITargetingHeuristic.SortType=ThreatToGround` | 12 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 未做 | `造兵/CountAsStructureForBuildPurposesFilter.ExcludeThing` | 12 | AI 模型代码里没有这个名字 |
| 不涉及 | `战略状态/AIStrategicStateDefinition.ExecutionBeginFeedbackKey` | 11 | 纯表现（语音、视频、画面） |
| 不涉及 | `战略状态/AIStrategicStateDefinition.ExecutionCanceledFeedbackKey` | 11 | 纯表现（语音、视频、画面） |
| 不涉及 | `战略状态/AIStrategicStateDefinition.ExecutionCompleteFeedbackKey` | 11 | 纯表现（语音、视频、画面） |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=FriendlyStructure` | 11 | docs/engine/aitactics.md#读数（FriendlyLandStructureHeuristic：engine_aidefense 守自家建造厂） |
| 未做 | `组队招人/ObjectFilter.Include` | 11 | AI 模型代码里没有这个名字 |
| 推断 | `组队招人/TeamTemplate.Priority=COOP` | 11 | AI 模型代码里读了这个名字 |
| 不涉及 | `人格/AIPersonalityDefinition.CommanderPortrait` | 10 | 纯表现（语音、视频、画面） |
| 未做 | `其他/BuildingPlacementDistance.Distance` | 10 | AI 模型代码里没有这个名字 |
| 已对拍 | `启发条件/PowerAdvantageHeuristic` | 10 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipoweradv.py |
| 推断 | `启发条件/PowerAdvantageHeuristic.Above` | 10 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/PowerAdvantageHeuristic.IncludeEnemyDefenses` | 10 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/PowerAdvantageHeuristic.IncludeOwnDefenses` | 10 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/PowerAdvantageHeuristic.Value` | 10 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/TimeSinceLastExpansionHeuristic` | 10 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/TimeSinceLastExpansionHeuristic.Time` | 10 | AI 模型代码里读了这个名字 |
| 已对拍 | `目标/AITargetingHeuristic.SearchRange` | 10 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 推断 | `组队招人/TeamTemplate.AllowRecruitUnitsInCombat` | 9 | AI 模型代码里读了这个名字 |
| 已对拍 | `组队招人/TeamTemplate.Priority=HIGH` | 9 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 不涉及 | `表现/StrategicDirectiveFeedback.Event` | 9 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/StrategicDirectiveFeedback.FeedbackKey` | 9 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/StrategicDirectiveFeedback.StrategicDirective` | 9 | 纯表现（语音、视频、画面） |
| 推断 | `启发条件/EnemyNearbyHeuristic.MinEnemyValue` | 8 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/ObjectOfTypeExistsHeuristic.Location` | 8 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.ForbiddenObjectStatus` | 8 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.SortType=ThreatToAir` | 8 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.Beacon` | 7 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=Beacon` | 7 | AI 模型代码里读了这个名字 |
| 推断 | `组队招人/TeamTemplate.MaxTypesOfUnits` | 7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/AIPersonalityDefinition.BaseCompactness` | 6 | 台上量过（engine_aitower：0.5 / 0.75 / 1.0 塔落在不同圈）；模拟器只对上 0.5，0.75 / 1.0 和 0.5 一样（strict xfail） |
| 未做 | `人格/AIPersonalityDefinition.RepairBuildingsAtDifficulty` | 6 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.UsePlayerPowersAtDifficulty` | 6 | AI 模型代码里没有这个名字 |
| 推断 | `启发条件/BeaconExistsHeuristic` | 6 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/BeaconExistsHeuristic.Exists` | 6 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/BeaconExistsHeuristic.Type` | 6 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/PathToTargetHeuristic.Surface` | 6 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/ResourceNodeShareHeuristic` | 6 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/ResourceNodeShareHeuristic.Above` | 6 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/ResourceNodeShareHeuristic.PercentOfFairShare` | 6 | AI 模型代码里读了这个名字 |
| 未做 | `微操/AIMicroManagerData.DodgeThreatsReactionTimeMax` | 6 | AI 模型代码里没有这个名字 |
| 未做 | `微操/AIMicroManagerData.DodgeThreatsReactionTimeMin` | 6 | AI 模型代码里没有这个名字 |
| 推断 | `微操/SpecificSpecialPowerDelay.MaximumDelay` | 6 | AI 模型代码里读了这个名字 |
| 推断 | `微操/SpecificSpecialPowerDelay.MinimumDelay` | 6 | AI 模型代码里读了这个名字 |
| 推断 | `微操/SpecificSpecialPowerDelay.PowerType` | 6 | AI 模型代码里读了这个名字 |
| 推断 | `微操/SpecificSpecialPowerDelay.TogglePowerSubType` | 6 | AI 模型代码里读了这个名字 |
| 推断 | `战术/Tactic.Tactic=ExactExpansion` | 6 | AI 模型代码里读了这个名字 |
| 推断 | `战术/Tactic.Tactic=GarrisonBuilding` | 6 | AI 模型代码里读了这个名字 |
| 已对拍 | `战术/Tactic.Targetless` | 6 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aimicro.py |
| 未做 | `战略状态/AIStrategicStateDefinition.PathfindingCheckType` | 6 | AI 模型代码里没有这个名字 |
| 推断 | `组队招人/TeamTemplate.Priority=DEFENSE_HIGH` | 6 | AI 模型代码里读了这个名字 |
| 未做 | `组队招人/TeamTemplate.RequireCanAttackTarget` | 6 | AI 模型代码里没有这个名字 |
| 已对拍 | `经济/AccountShare.Account=DEFENSE` | 6 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `经济/AccountShare.Account=PRODUCTION` | 6 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiomove.py |
| 未做 | `经济/AccountShare.Account=SLUSH_FUND` | 6 | AI 模型代码里没有这个名字 |
| 不涉及 | `表现/SkirmishGameEventFeedback.Event` | 6 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/SkirmishGameEventFeedback.FeedbackKey` | 6 | 纯表现（语音、视频、画面） |
| 未做 | `人格/EnemyFilter.Include` | 5 | AI 模型代码里没有这个名字 |
| 未做 | `人格/EnemyFilter.Relationship` | 5 | AI 模型代码里没有这个名字 |
| 未做 | `人格/EnemyFilter.Rule` | 5 | AI 模型代码里没有这个名字 |
| 未做 | `微操/AIMicroManagerData.MinDistanceFromBaseToIgnoreTargets` | 5 | AI 模型代码里没有这个名字 |
| 未做 | `微操/AIMicroManagerData.PassiveTargetSearchDistance` | 5 | AI 模型代码里没有这个名字 |
| 推断 | `微操/AIMicroManagerData.SiegeWeaponBuffer` | 5 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.SpecialPowerDelayMaximum` | 5 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.SpecialPowerDelayMinimum` | 5 | AI 模型代码里读了这个名字 |
| 未做 | `微操/IgnoreTargets.Include` | 5 | AI 模型代码里没有这个名字 |
| 未做 | `微操/SpecificSpecialPowerDelay.TogglePowerSubType=TOGGLE_LOCKDOWN` | 5 | AI 模型代码里没有这个名字 |
| 未做 | `战略状态/AIStrategicStateDefinition.PathfindingCheckType=None` | 5 | AI 模型代码里没有这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=EnemyStructureCloseToShore` | 5 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=TechBuilding` | 5 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.MaxDistanceToShore` | 5 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.SortType=ClosestToEnemy` | 5 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.UnderAttack` | 5 | AI 模型代码里读了这个名字 |
| 推断 | `经济/BudgetState.Difficulty` | 5 | AI 模型代码里读了这个名字 |
| 推断 | `经济/BudgetState.State` | 5 | AI 模型代码里读了这个名字 |
| 推断 | `人格/UnitCap.Cap` | 4 | AI 模型代码里读了这个名字 |
| 推断 | `人格/UnitCap.Difficulty` | 4 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/IncomeAdvantageHeuristic` | 4 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/IncomeAdvantageHeuristic.Above` | 4 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/IncomeAdvantageHeuristic.Value` | 4 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/OpenNodeHeuristic` | 4 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/OpenNodeHeuristic.Exists` | 4 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/OpenNodeHeuristic.MinDistanceFromEnemy` | 4 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.CanUseSiegeState` | 4 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.GatherTempVisionRangeBonus` | 4 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.RetreatTempVisionRangeBonus` | 4 | AI 模型代码里读了这个名字 |
| 未做 | `微操/IgnoreTargets.Exclude` | 4 | AI 模型代码里没有这个名字 |
| 推断 | `目标/AITargetingHeuristic.VitalObjectStatus` | 4 | AI 模型代码里读了这个名字 |
| 未做 | `造兵/CountAsStructureForBuildPurposesFilter.Include` | 4 | AI 模型代码里没有这个名字 |
| 未做 | `造兵/CountAsStructureForBuildPurposesFilter.Rule` | 4 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EmergencyManagerHandleConyardInDangerAtDifficulty` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `人格/PersonalityMap.Personality` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `人格/PersonalityMap.Side` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `战术/Tactic.AestheticsManagerMinDistanceFromHarvester` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `战术/Tactic.AestheticsManagerPatrolIdleTime` | 3 | AI 模型代码里没有这个名字 |
| 推断 | `战术/Tactic.Tactic=NullTactic` | 3 | AI 模型代码里读了这个名字 |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=Point` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=UnpackBuildingPlacement` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.AircraftRepairFacility` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.EnergyProducer` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.ExpanderTemplate` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.GathererTemplate` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.MCVTemplate` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.NavalRepairFacility` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.PrimaryResourceNodeCollector` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.PrimaryResourceThingToBuild` | 3 | AI 模型代码里没有这个名字 |
| 推断 | `阵营/ArmyDefinition.Side` | 3 | AI 模型代码里读了这个名字 |
| 未做 | `阵营/ArmyDefinition.VehicleRepairFacility` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.WallPiece` | 3 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.BuildTechEfficiencyThreshold` | 2 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.BuildTechMinPowerAdvantage` | 2 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.DesiredExcessPowerBuffer` | 2 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EmergencyManagerHandleNoConyardAtDifficulty` | 2 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EmergencyManagerHandleNoIncomeAtDifficulty` | 2 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EmergencyManagerHandleUnderAttackAtDifficulty` | 2 | AI 模型代码里没有这个名字 |
| 推断 | `人格/BaseSelection.SortOrder=PREFER_NEWEST` | 2 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/CanBuildBuildingsOnSurfaceHeuristic` | 2 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/CanBuildBuildingsOnSurfaceHeuristic.MaxPlacementGridCells` | 2 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/CanBuildBuildingsOnSurfaceHeuristic.MinPlacementGridCells` | 2 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/CanBuildBuildingsOnSurfaceHeuristic.Surfaces` | 2 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.MaxUnitIdleDistanceChange` | 2 | AI 模型代码里读了这个名字 |
| 推断 | `战术/Tactic.Tactic=Hunt` | 2 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=Husk` | 2 | AI 模型代码里读了这个名字 |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=Team` | 2 | AI 模型代码里没有这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=UnderAttackBy` | 2 | AI 模型代码里读了这个名字；台上量过（docs/engine/aitactics.md），没有测试跑这个台子 |
| 未做 | `目标/AITargetingHeuristic.IgnoreMinDistanceFromConyardEntranceForTime` | 2 | AI 模型代码里没有这个名字 |
| 未做 | `目标/AITargetingHeuristic.MinDistanceFromConyardEntrance` | 2 | AI 模型代码里没有这个名字 |
| 未做 | `组队招人/ObjectFilter.Exclude` | 2 | AI 模型代码里没有这个名字 |
| 未做 | `经济/ResourceMultiplierCheat.Difficulty` | 2 | AI 模型代码里没有这个名字 |
| 未做 | `经济/ResourceMultiplierCheat.Percentage` | 2 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.AssaultBeaconRadius` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.CleanupRefineries` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.ConyardInDangerEmergencyEngineerDistance` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.ConyardInDangerEmergencyHealthPercent` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.ConyardInDangerEmergencyUnderAttackTime` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.CoopPersonality` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.DefaultThreatFindRadius` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemyResortingTime` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemySortingBrutalDifficulty` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemySortingEasyDifficulty` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemySortingHardDifficulty` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemySortingMediumDifficulty` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.HoldObjectBeaconRadius` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.HoldPositionBeaconRadius` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.MaxWallDestroyTimeToCountAsGoThroughWalls` | 1 | AI 模型代码里没有这个名字 |
| 推断 | `人格/AIPersonalityDefinition.ReactiveDefenseRadius` | 1 | AI 模型代码里读了这个名字；台上量过（docs/engine/aitactics.md），没有测试跑这个台子 |
| 未做 | `人格/AIPersonalityDefinition.RefineryPlacementIncreaseTickAmount` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.RefineryPlacementNumberOfIncreaseTicksBeforeGivingUp` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.RefineryPlacementStartDistanceDelta` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.ResourceNodeSearchRadius` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.ResourceNodeValueRemainingForExpansion` | 1 | AI 模型代码里没有这个名字 |
| 已对拍 | `人格/AIPersonalityDefinition.SecondsTillTargetsExpire` | 1 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 不涉及 | `人格/AIPersonalityDefinition.SkirmishTimeTillGreeting` | 1 | 纯表现（语音、视频、画面） |
| 未做 | `人格/AIPersonalityDefinition.UnitBuilderEnemyNearbyDistance` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.UnitBuilderEnemyNearbyMultiplier` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.UnitBuilderOverallDefensivePreference` | 1 | AI 模型代码里没有这个名字 |
| 推断 | `人格/DefaultTacticHomeBaseCriteria.PreferredNotBaseTypes` | 1 | AI 模型代码里读了这个名字 |
| 推断 | `人格/DefaultTacticHomeBaseCriteria.SortOrder` | 1 | AI 模型代码里读了这个名字 |
| 未做 | `人格/Filter.Exclude` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/Filter.Include` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `人格/Filter.Rule` | 1 | AI 模型代码里没有这个名字 |
| 推断 | `人格/RetreatBaseCriteria.PreferredNotBaseTypes` | 1 | AI 模型代码里读了这个名字 |
| 推断 | `人格/RetreatBaseCriteria.SortOrder` | 1 | AI 模型代码里读了这个名字 |
| 未做 | `全局常量/AIData.AICrushesInfantry` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.AIDozerBoredRadiusModifier` | 1 | AI 模型代码里没有这个名字 |
| 不涉及 | `全局常量/AIData.AllowForestFires` | 1 | 纯表现（语音、视频、画面） |
| 不涉及 | `全局常量/AIData.AltCameraPitchOverride` | 1 | 纯表现（语音、视频、画面） |
| 不涉及 | `全局常量/AIData.AltCameraZoomOverride` | 1 | 纯表现（语音、视频、画面） |
| 未做 | `全局常量/AIData.AttackMoveUsesFormations` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.AttackUsesLineOfSight` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.CastleSiegeStandBackDistance` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.ChaseFromBehindLimit` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.DeepWaterDepth` | 1 | AI 模型代码里没有这个名字 |
| 不涉及 | `全局常量/AIData.DisableTrees` | 1 | 纯表现（语音、视频、画面） |
| 未做 | `全局常量/AIData.EnableRepulsors` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.ForceSkirmishAI` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.FormationColumnWidth` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.FormationEnemyDistance` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.FormationRowDepth` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.FormationSquadSpacing` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.GuardChaseUnitFrames` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.GuardEnemyReturnScanRate` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.GuardEnemyScanRate` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.HordesWaitForHordes` | 1 | AI 模型代码里没有这个名字 |
| 不涉及 | `全局常量/AIData.LowLodTree` | 1 | 纯表现（语音、视频、画面） |
| 不涉及 | `全局常量/AIData.LowLodTreeNoGrab` | 1 | 纯表现（语音、视频、画面） |
| 不涉及 | `全局常量/AIData.LowLodTreeNoHarvest` | 1 | 纯表现（语音、视频、画面） |
| 不涉及 | `全局常量/AIData.LowLodTreeScale` | 1 | 纯表现（语音、视频、画面） |
| 未做 | `全局常量/AIData.MaxRecruitDistance` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.MaxRetaliateDistance` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.MaxSquadWidth` | 1 | AI 模型代码里没有这个名字 |
| 不涉及 | `全局常量/AIData.MaximumCraterDepth` | 1 | 纯表现（语音、视频、画面） |
| 未做 | `全局常量/AIData.MeleeApproachDist` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.MeleeApproachTolerance` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.MinDistanceForGroup` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.NarrowPassageScale` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.Optimization_NumEfficiencyUpdates` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.Optimization_NumTeamsToRecruit` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.Optimization_TacticsEmergencyKickPeriod` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.Optimization_TimeToCacheCanEnterTransport` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.Optimization_TimeToCacheCanReachImmobileTarget` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.Optimization_TimeToCacheCanReachMobileTarget` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.RebuildDelaySeconds` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.RepulsedDistance` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.ResourcesPoor` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.ResourcesWealthy` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.RetaliateFriendsRadius` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.RotateSkirmishBases` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.SkirmishGroupFudgeValue` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.StructureSeconds` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.StructuresPoorMod` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.StructuresWealthyMod` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.SupplyCenterSafeRadius` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.TeamPoorMod` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.TeamResourcesToBuild` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.TeamSeconds` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.TeamWealthyMod` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.UseFormations` | 1 | AI 模型代码里没有这个名字 |
| 不涉及 | `全局常量/AIData.UseLowLODTrees` | 1 | 纯表现（语音、视频、画面） |
| 未做 | `全局常量/AIData.WadeWaterDepth` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.WaitForOthers` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.WallHeight` | 1 | AI 模型代码里没有这个名字 |
| 已对拍 | `启发条件/ScriptedFlagHeuristic` | 1 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | `启发条件/ScriptedFlagHeuristic.FlagName` | 1 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 未做 | `微操/AIMicroManagerData.CanCollectCratesWhenIdle` | 1 | AI 模型代码里没有这个名字 |
| 未做 | `微操/AIMicroManagerData.FractionBlockedToDestroyWalls` | 1 | AI 模型代码里没有这个名字 |
| 推断 | `微操/AIMicroManagerData.IsHarvesterManager` | 1 | AI 模型代码里读了这个名字 |
| 未做 | `微操/AIMicroManagerData.MaxSecondaryDamageFraction` | 1 | AI 模型代码里没有这个名字 |
| 推断 | `微操/AIMicroManagerData.MaxTeamIdleDistanceChange` | 1 | AI 模型代码里读了这个名字 |
| 已对拍 | `微操/AIMicroManagerData.MaxTeamIdleTime` | 1 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 已对拍 | `微操/AIMicroManagerData.MaxUnitIdleTime` | 1 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 推断 | `微操/AIMicroManagerData.MinTimeToKeepTempVisionRangeBonus` | 1 | AI 模型代码里读了这个名字 |
| 未做 | `微操/IgnoreTargets.StatusBitFlags` | 1 | AI 模型代码里没有这个名字 |
| 推断 | `微操/SpecificSpecialPowerDelay.TogglePowerSubType=TOGGLE_DEFENSE_SELF_ONLY` | 1 | AI 模型代码里读了这个名字 |
| 已对拍 | `战术/Tactic.EndBehavior=RETURN_HOME_AND_DISBAND` | 1 | docs/engine/aitactics.md#目标没了以后（EndBehavior，2026-11-09 各一次）（aiendh：同 DISBAND，没回家，和模型对上） |
| 推断 | `战术/Tactic.Tactic=ReactiveDefense` | 1 | AI 模型代码里读了这个名字；台上量过（docs/engine/aitactics.md），没有测试跑这个台子 |
| 推断 | `战略状态/AIStrategicStateDefinition.MaxInactiveCopies` | 1 | AI 模型代码里读了这个名字 |
| 未做 | `战略状态/AIStrategicStateDefinition.PathfindingCheckType=QuickDoesAttackPathExist` | 1 | AI 模型代码里没有这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=Bridge` | 1 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=Crate` | 1 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=EnemyGarrison` | 1 | AI 模型代码里读了这个名字 |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=Help` | 1 | AI 模型代码里没有这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=NeutralGarrison` | 1 | AI 模型代码里读了这个名字 |
| 未做 | `组队招人/TeamTemplate.BaseDefenseMaxDistance` | 1 | AI 模型代码里没有这个名字 |
| 推断 | `组队招人/TeamTemplate.IsBaseDefenseTeam` | 1 | AI 模型代码里读了这个名字 |
| 推断 | `组队招人/TeamTemplate.Priority=HOTSPOT` | 1 | AI 模型代码里读了这个名字 |
| 推断 | `组队招人/TeamTemplate.Priority=SCRIPTED` | 1 | AI 模型代码里读了这个名字 |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.MinPowerAdvantageEnemiesInMyBaseVsAllMyUnits` | 1 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.NumberOfObjectsRecentlyLost` | 1 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.ObjectLostFilter` | 1 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.OnlyIfLocalPlayerIs` | 1 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.TimeBetweenScans` | 1 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.TimeForNumberOfObjectLost` | 1 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.TimeThatConditionsMustBeMet` | 1 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.TimeoutAfterPlaying` | 1 | 纯表现（语音、视频、画面） |
| 未做 | `造兵/BuildEntry.Score` | 1 | AI 模型代码里没有这个名字 |
