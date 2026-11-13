# 原版功能总清单（引擎 A：脚本层、物体模块、武器效果；引擎 B：AI）

由 `experimental/cnv/inventory.py` 从原版数据生成，**别手改**；`tests/test_inventory.py` 在它过期时变红。状态与判定规则见脚本 docstring（ADR 0026）。用量：脚本 = 原版战役脚本里出现的次数；模块 = 原版战役地图里摆了的、用到它的物体种数（括号里是全部物体种数）；武器效果 = 用到它的原版武器数；AI = 原版 AI 数据（SDK SkirmishAI，含战役关的 AI 状态）里写它的次数，判定规则见 `inventory_ai.py`。**主数字是"按用量已对拍"**：已对拍项的用量占全部用量的比例，推断不算，不涉及不进分母；目标每部分 90%。"9 关用到"：我们 9 关（`missions/a1.py`～`a9.py`）里用到这项的关（脚本、物体模块、武器效果按 `inventory_levels.py`，AI 按 `inventory_ai.py levels`；"全部" = 9 关都用）；"9 关用到的按用量已对拍"只算这些项（用户 11-11 定：先做完 9 关用到的）。

| 部分 | 按用量已对拍 | 9 关用到的按用量已对拍 | 9 关用到（已对拍 / 项） | 项数 | 已对拍 | 推断 | 未做 | 不涉及 | 按用量已有（已对拍+推断） |
|---|---|---|---|---|---|---|---|---|---|
| 脚本动作 | **92%** | **100%** | 50 / 50 | 451 | 123 | 20 | 191 | 117 | 93% |
| 脚本条件 | **94%** | **100%** | 12 / 12 | 89 | 33 | 6 | 47 | 3 | 95% |
| 物体模块 | **98%** | **98%** | 54 / 113 | 189 | 55 | 13 | 95 | 26 | 99% |
| 武器效果 | **93%** | **95%** | 17 / 22 | 28 | 18 | 3 | 5 | 2 | 96% |
| AI | **88%** | **88%** | 131 / 357 | 415 | 137 | 126 | 118 | 34 | 98% |

## 脚本动作

| 状态 | 名字 | 用量 | 9 关用到 | 说明 |
|---|---|---|---|---|
| 已对拍 | `ENABLE_SCRIPT` | 5727 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_script.py |
| 已对拍 | `SET_MILLISECOND_TIMER` | 4153 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `SET_FLAG` | 4105 | 全部 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | `ALLOW_DISALLOW_ONE_BUILDING` | 3466 | a4 a5 a7 | tests/test_simbench.py::test_a_ban_holds_the_queue_and_does_not_cancel |
| 已对拍 | `PLAYER_LOCK_PLAYER_TECH` | 1887 |  | tests/test_simbench.py::test_protocol_a_computer_player_spends_unless_locked |
| 已对拍 | `DISABLE_SCRIPT` | 1099 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `MOVE_NAMED_UNIT_TO` | 1000 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aidefense.py |
| 已对拍 | `LINK_MISSION_OBJECTIVE_TO_OBJECT` | 950 | 全部 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts5.py |
| 已对拍 | `NAMED_DELETE` | 908 | a2 a4 a5 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attach.py |
| 已对拍 | `CREATE_REINFORCEMENT_TEAM` | 753 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_reinf.py |
| 已对拍 | `SET_MISSION_OBJECTIVE_STATUS` | 732 | 全部 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts5.py |
| 不涉及 | `PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT` | 640 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `CALL_SUBROUTINE` | 533 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `UNIT_IDLE_FOR_FRAMECOUNT` | 504 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 不涉及 | `PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT_WITH_SUBTITLE` | 445 |  | 纯表现（名字规则） |
| 不涉及 | `MOVIE_PLAY_RADAR` | 433 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION` | 399 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 已对拍 | `OBJECTLIST_ADDOBJECTTYPE` | 383 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 已对拍 | `PLAYER_SET_MONEY` | 345 | 全部 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aitower.py |
| 已对拍 | `SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY` | 343 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiprio.py |
| 已对拍 | `PLAYER_RELATES_PLAYER` | 319 | a2 a4 a5 a7 a9 | tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back |
| 已对拍 | `UNIT_AFFECT_OBJECT_PANEL_FLAGS` | 317 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 不涉及 | `SET_MISSION_HOT_SPOT_VISIBILITY` | 300 |  | 纯表现（名字规则） |
| 已对拍 | `MOVE_TEAM_TO` | 298 | a4 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aixfer.py |
| 已对拍 | `CREATE_NAMED_ON_TEAM_AT_WAYPOINT` | 291 | 全部 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `NAMED_ATTACK_NAMED` | 271 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attach.py |
| 已对拍 | `CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION` | 259 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py:face |
| 已对拍 | `MOVE_CAMERA_TO` | 255 | a1 a2 a4 a6 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_camera.py |
| 不涉及 | `OBJECT_CREATE_RADAR_EVENT` | 254 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `UNIT_IDLE_FOR_SECONDS` | 237 |  | tests/test_simbench.py::test_scripts1_idle_for_seconds_drops_the_move |
| 已对拍 | `TEAM_TRANSFER_TO_PLAYER` | 235 |  | tests/test_simbench.py::test_scripts1_a_team_handed_over_drops_its_move |
| 已对拍 | `NAMED_TRANSFER_OWNERSHIP_PLAYER` | 231 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_invuln.py |
| 已对拍 | `INCREMENT_COUNTER` | 229 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_aimicro.py |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:SHROUD_REVEAL_TO_ALL` | 218 |  | 状态位 SHROUD_REVEAL_TO_ALL 只记下来 |
| 已对拍 | `PLAYER_SET_MAX_PLAYER_POWER_POINTS` | 206 | a4 a5 a7 | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 已对拍 | `NAMED_KILL` | 204 | a4 a5 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 推断 | `TEAM_HUNT` | 203 |  | 没交给 AI 的玩家（含玩家自己）：不动，台上量过（engine_scripts1 hunt 60 s）；AI 玩家的 HuntTactic 不模拟（引擎 B），碰到记 Sim.unmodeled |
| 已对拍 | `CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT` | 196 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_ref.py |
| 已对拍 | `LINK_MISSION_OBJECTIVE_TO_WAYPOINT` | 194 | a1 a3 a4 a5 a6 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts5.py |
| 已对拍 | `NAMED_FOLLOW_WAYPOINTS` | 192 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_wayatk.py |
| 已对拍 | `TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY` | 186 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_transport.py |
| 已对拍 | `TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS` | 184 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_wayatk.py |
| 不涉及 | `FADE_OUT_TO_BLACK` | 177 |  | 纯表现（名字规则） |
| 不涉及 | `FADE_IN_FROM_BLACK` | 176 |  | 纯表现（名字规则） |
| 不涉及 | `NAMED_FLASH` | 173 | a9 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `SET_COUNTER` | 171 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_aidiff.py |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:SKIRMISH_AI_DO_NOT_ATTACK` | 171 |  | 状态位 SKIRMISH_AI_DO_NOT_ATTACK 只记下来 |
| 不涉及 | `NAMED_SHOW_INFOBOX` | 166 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `TEAM_USE_COMMANDBUTTON_ABILITY` | 162 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts1.py |
| 已对拍 | `PLAYER_SPECIAL_POWER_AVAILABILITY` | 158 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8b.py |
| 不涉及 | `PATH_MUSIC_PLAY_EVENT` | 155 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN）；台上量过（docs/engine/inventory-levels-a.md），没有测试跑这个台子 |
| 不涉及 | `CAMERA_LETTERBOX_END` | 154 | a4 | 纯表现（名字规则） |
| 已对拍 | `DISABLE_INPUT` | 152 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts3.py |
| 已对拍 | `TEAM_AI_TRANSFER` | 152 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aixfer.py |
| 不涉及 | `EVA_SET_ENABLED_DISABLED` | 148 |  | 纯表现（名字规则） |
| 不涉及 | `PLAY_SOUND_EFFECT_AT` | 147 |  | 纯表现（名字规则） |
| 已对拍 | `ATTACK_MOVE_NAMED_UNIT_TO` | 146 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aixfer.py |
| 不涉及 | `SOUND_PLAY_NAMED` | 137 |  | 纯表现（名字规则） |
| 已对拍 | `UNIT_AI_TRANSFER_ALL` | 137 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aidefense.py |
| 已对拍 | `ENABLE_INPUT` | 132 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts3.py |
| 已对拍 | `NO_OP` | 130 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `TEAM_AFFECT_OBJECT_PANEL_FLAGS` | 130 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 已对拍 | `UNIT_AI_TRANSFER` | 129 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aixfer.py |
| 不涉及 | `TELEPORT_STRUCTURE` | 128 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `CAMPAIGN_CREATE_AUTO_SAVE` | 127 | 全部 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `UNIT_SET_STANCE` | 124 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `TEAM_DELETE` | 122 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 已对拍 | `TEAM_KILL` | 121 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 已对拍 | `SET_TIMER` | 119 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `NAMED_STOP` | 118 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_emp.py |
| 已对拍 | `UNIT_TELEPORT_TO_WAYPOINT` | 118 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aidefense.py |
| 不涉及 | `PLAYER_CAMERA_MOVE_TO` | 117 |  | 纯表现（名字规则） |
| 已对拍 | `ATTACK_MOVE_TEAM_TO` | 116 | a1 a3 a5 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_wayatk.py |
| 已对拍 | `PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT` | 116 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8b.py |
| 已对拍 | `TEAM_IDLE_FOR_SECONDS` | 114 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 已对拍 | `PLAYER_SET_BASE_POWER` | 112 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8b.py |
| 未做 | `PLAYER_TOGGLE_RESOURCE_SHARING` | 111 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `UNIT_SET_MODELCONDITION_GENERIC` | 111 | a7 | 纯表现：设模型状态只换画法。原版脚本设的是 SUPPRESSED（a01 摆拍枪战的趴下动作），SDK 数据里读 SUPPRESSED 的只有绘制模块的 ConditionsYes；我们 a7 设的 USER_1 只有自由号的充能画法读 |
| 不涉及 | `PLAY_SOUND_AS_AI_COCOMMANDER_DIALOG` | 109 |  | 纯表现（名字规则） |
| 不涉及 | `TEAM_CREATE_RADAR_EVENT` | 107 |  | 纯表现（名字规则） |
| 已对拍 | `MAP_REVEAL_PERMANENTLY_AT_WAYPOINT` | 105 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 不涉及 | `CAMERA_LETTERBOX_BEGIN` | 104 | a4 | 纯表现（名字规则） |
| 已对拍 | `NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY` | 103 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aibasedef.py |
| 未做 | `TEAM_ALLOW_AI_AUTOACQUIRE` | 103 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER` | 101 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_ref.py |
| 不涉及 | `RESET_CAMERA` | 100 |  | 纯表现（名字规则） |
| 不涉及 | `CAMERA_LETTERBOX_BEGIN_WITH_RADAR` | 98 |  | 纯表现（名字规则） |
| 已对拍 | `SET_RANDOM_COUNTER` | 97 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `PLAYER_SET_PLAYER_POWER_POINTS` | 95 | a4 a5 a7 | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 已对拍 | `SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER` | 94 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 已对拍 | `MAP_REVEAL_ALL_PERM` | 89 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `MAP_SWITCH_BORDER` | 87 | a1 a2 a3 a4 a5 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 未做 | `NAMED_SET_DISABLED` | 86 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `NAMED_REMOVE_INFOBOX` | 83 |  | 纯表现（名字规则） |
| 已对拍 | `TEAM_FOLLOW_WAYPOINTS` | 83 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_waypath.py |
| 已对拍 | `SKIRMISH_AI_MAKE_BASE` | 82 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiomove.py |
| 已对拍 | `SET_RANDOM_MSEC_TIMER` | 77 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `TEAM_ATTACK_NAMED` | 76 | a2 a4 a7 a8 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_reorder.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateEjectPassengersSpecialPowerUntargeted` | 75 |  | 只记进时间线，没有效果 |
| 已对拍 | `SKIRMISH_AI_USE_REPAIRS` | 75 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aipullback.py |
| 不涉及 | `NAMED_OUTLINE` | 74 |  | 纯表现（名字规则） |
| 不涉及 | `FLASH_UI_UNIT_ABILITY_BUTTON` | 72 |  | 纯表现（名字规则） |
| 已对拍 | `MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT` | 72 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 已对拍 | `PLAYER_GIVE_MONEY` | 72 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `UNIT_SET_TEAM` | 72 | 全部 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `TEAM_CHANGE_OBJECT_STATUS` | 71 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8b.py |
| 未做 | `TEAM_GARRISON_TEAM_INSTANTLY` | 68 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `UNIT_CLEAR_MODELCONDITION` | 68 |  | 纯表现：同 UNIT_SET_MODELCONDITION_GENERIC，清掉画法状态 |
| 不涉及 | `CREATE_UNNAMED_ON_TEAM_AT_NAMED_OBJECT_LOCATION` | 67 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `LINK_MISSION_HOT_SPOT_TO_OBJECT` | 67 |  | 纯表现（名字规则） |
| 已对拍 | `SKIRMISH_AI_USE_REBUILD_SYSTEM` | 67 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiswitch.py |
| 已对拍 | `TEAM_MERGE_INTO_TEAM` | 67 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 推断 | `NAMED_HUNT` | 66 |  | 同 TEAM_HUNT：没交给 AI 不动（台上量过）；AI 玩家的猎杀不模拟（引擎 B） |
| 不涉及 | `TEAM_FLASH` | 66 |  | 纯表现（名字规则） |
| 已对拍 | `TEAM_SET_OVERRIDE_RELATION_TO_PLAYER` | 64 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 未做 | `SET_MISSION_HOT_SPOT_ACTIVENESS` | 61 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION` | 60 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 未做 | `NAMED_FORCE_ATTACK_NAMED` | 59 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_FORCE_ATTACK_WAYPOINT` | 59 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM` | 59 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN）；台上量过（docs/engine/inventory-levels-a.md），没有测试跑这个台子 |
| 不涉及 | `SET_REFERENCE_TO_RANDOM_TEAM_MEMBER` | 59 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `MAP_REVEAL_ALL_UNDO_PERM` | 58 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 不涉及 | `SHOW_MILITARY_CAPTION` | 58 | 全部 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `NAMED_FOLLOW_WAYPOINTS_EXACT` | 56 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_waypath.py |
| 未做 | `UNIT_EXECUTE_SEQUENTIAL_SCRIPT` | 56 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_SET_MAX_HEALTH` | 53 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_maxhealth.py |
| 不涉及 | `TOGGLE_RADAR_UI` | 53 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `DISPLAY_TUTORIAL_TEXT` | 52 |  | 纯表现（名字规则） |
| 已对拍 | `PLAY_SOUND_EFFECT` | 51 | a4 | 只记进时间线（sim.SHOWN）；台上量过、测试对拍：checks/engine_dialog.py |
| 未做 | `TEAM_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT` | 51 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `DECREMENT_COUNTER` | 50 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts3.py |
| 已对拍 | `DISPLAY_COUNTDOWN_TIMER` | 50 | a4 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 已对拍 | `SELL_OBJECT` | 50 |  | tests/test_simbench.py::test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames |
| 已对拍 | `TEAM_ATTACK_TEAM` | 50 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateEjectPassengersSpecialPower` | 49 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_transport.py |
| 不涉及 | `FLASH_UI_BUILD_BUTTON` | 48 |  | 纯表现（名字规则） |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JAAVT1_Transform` | 48 |  | 只记进时间线，没有效果 |
| 未做 | `SET_UNIT_REFERENCE` | 48 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_ATTACK_FOLLOW_WAYPOINTS` | 47 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_wayatk.py |
| 已对拍 | `NAMED_RECEIVE_UPGRADE` | 47 | a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_invuln.py |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanBaseDefenseEgg` | 46 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_unpack.py |
| 未做 | `TEAM_SET_STANCE` | 45 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `NAMED_CUSTOM_COLOR` | 44 |  | 纯表现（名字规则） |
| 已对拍 | `HIDE_COUNTDOWN_TIMER` | 43 | a4 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_SovietAntiGroundAircraftEvacuate` | 43 |  | 只记进时间线，没有效果 |
| 已对拍 | `PLAYER_SET_OVERRIDE_RELATION_TO_TEAM` | 43 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleSpiderHole` | 41 |  | 只记进时间线，没有效果 |
| 未做 | `PLAYER_SET_SPECIAL_POWER_COUNTDOWN` | 41 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `FOR_EACH_PLAYER_OBJECT_EXECUTE_SCRIPT` | 39 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JAIV_Transform` | 38 |  | 只记进时间线，没有效果 |
| 未做 | `TECHTREE_MODIFY_BUILDABILITY_OBJECT` | 38 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `EVALUATE_SCRIPT` | 35 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `SKIRMISH_AI_TRANSFER_ALL` | 35 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_CONTEXT_SENSITIVE_ATTACK` | 35 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `FOR_EACH_TEAM_MEMBER_EXECUTE_SCRIPT` | 34 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `LINK_MISSION_HOT_SPOT_TO_WAYPOINT` | 34 |  | 纯表现（名字规则） |
| 已对拍 | `NAMED_DAMAGE` | 34 |  | tests/test_simbench.py::test_sell_a_killed_building_stays_paid_and_a_building_unpacking_is_not_sold |
| 不涉及 | `FLASH_MOUSE_HUD_FIXED_ELEMENT` | 33 |  | 纯表现（名字规则） |
| 未做 | `GATE_OPEN` | 33 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `MAP_REVEAL_PERMANENTLY_IN_TRIGGER` | 33 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_DisguisedEvacuate` | 33 |  | 只记进时间线，没有效果 |
| 已对拍 | `STOP_TIMER` | 33 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_timer.py |
| 已对拍 | `TEAM_SET_OVERRIDE_RELATION_TO_TEAM` | 33 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 已对拍 | `UNIT_CHANGE_OBJECT_STATUS:NO_ATTACK` | 33 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 推断 | `ALLOW_DISALLOW_ONE_UPGRADE` | 32 |  | Sim.act / Sim.cond 有分支 |
| 已对拍 | `NAMED_ATTACK_TEAM` | 32 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 未做 | `UNIT_KILL_ALL_IN_AREA` | 32 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `ATTACK_MOVE_TEAM_TO_NAMED_OBJECT` | 31 |  | Sim.act / Sim.cond 不认识 |
| 推断 | `CREATE_REINFORCEMENT_TEAM_AT_UNIT_POSITION` | 31 |  | Sim.act / Sim.cond 有分支 |
| 未做 | `SKIRMISH_AI_SET_FAVORED_ENEMY` | 31 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT` | 30 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_waypath.py |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:SKIRMISH_AI_DO_NOT_TAKE` | 30 |  | 状态位 SKIRMISH_AI_DO_NOT_TAKE 只记下来 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleAlliedArtilleryVehicle` | 29 |  | 只记进时间线，没有效果 |
| 未做 | `PLAYER_ALLOWED_TOBE_COOPAI` | 29 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER` | 29 | a1 a2 a3 a4 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiopen.py |
| 不涉及 | `DESELECT` | 28 |  | 纯表现（名字规则） |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_CAMPAlliedBomberDrop2` | 28 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SOUND_DISABLE_TYPE` | 28 |  | 纯表现（名字规则） |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackAlliedMCV` | 27 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_unpack.py |
| 不涉及 | `PLAYER_CAMERA_MOVE_TO_NAMED` | 27 |  | 纯表现（名字规则） |
| 未做 | `TEAM_GARRISON_SPECIFIC_BUILDING` | 27 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_PLAYERS_NEAREST_UNIT_OF_TYPE_TO_REFERENCE` | 27 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `TEAM_STOP` | 27 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 未做 | `TEAM_TELEPORT_TO_WAYPOINT` | 27 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `MAP_UNDO_REVEAL_PERMANENTLY_IN_TRIGGER` | 26 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `NAMED_FLASH_WHITE` | 26 |  | 纯表现（名字规则） |
| 不涉及 | `RADAR_CREATE_EVENT` | 26 |  | 纯表现（名字规则） |
| 未做 | `TEAM_GUARD_AREA_FROM_POSITION` | 26 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `TEAM_SET_DISABLED` | 26 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `LINK_MISSION_OBJECTIVE_TO_OBJECT_WITH_CATEGORY` | 25 |  | 纯表现（名字规则） |
| 已对拍 | `NAMED_GARRISON_SPECIFIC_BUILDING` | 25 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_engineer.py:a |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JapanBaseDefenseToggleBinaryWeapon` | 25 |  | 只记进时间线，没有效果 |
| 未做 | `PLAYER_SET_MONEY_CAP` | 25 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_ALLOW_AI_AUTOACQUIRE` | 25 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_SET_MODELCONDITION` | 25 |  | Sim.act / Sim.cond 不认识 |
| 推断 | `DISPLAY_COUNTER` | 24 |  | 引擎模型核心 |
| 不涉及 | `HIDE_COUNTER` | 24 |  | 纯表现（名字规则） |
| 未做 | `PLAYER_ALLOW_AI_AUTOACQUIRE` | 24 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PLAY_SOUND_AS_AI_COCOMMANDER_DIALOG_WITH_SUBTITLE` | 24 |  | 纯表现（名字规则） |
| 不涉及 | `SETUP_CAMERA` | 24 |  | 纯表现（名字规则） |
| 不涉及 | `SET_COOP_AI_COMMAND_UI_ENABLED` | 24 | a4 | 纯界面：开关玩家给盟友 AI 下令的按钮；模拟器的玩家没有给盟友下令的命令，开关无从起作用（以后加了这个命令再算） |
| 不涉及 | `LINK_MISSION_OBJECTIVE_TO_WAYPOINT_WITH_CATEGORY` | 23 |  | 纯表现（名字规则） |
| 未做 | `PLAYER_GRANT_SPECIAL_POWER` | 23 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_TRANSFER_OWNERSHIP_PLAYER` | 23 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE` | 23 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `HIDE_TUTORIAL_TEXT` | 22 |  | 纯表现（名字规则） |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NO_ATTACK_FROM_AI` | 22 |  | 状态位 NO_ATTACK_FROM_AI 只记下来 |
| 不涉及 | `MOVE_NAMED_UNIT_TO_UNIT` | 21 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `NAMED_USE_LOGIC_COMMAND_ABILITY_ON_NAMED_POSITION` | 21 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `SELECT_OBJECT` | 21 |  | 纯表现（名字规则） |
| 已对拍 | `TEAM_FOLLOW_WAYPOINTS_EXACT` | 21 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_waypath.py |
| 不涉及 | `MOVE_CAMERA_TO_NAMED` | 20 | a5 a7 | 纯表现（名字规则）；Sim.act / Sim.cond 有分支 |
| 未做 | `REDALERT_DISABLE_THREAT_LEVEL_BONUS` | 20 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `UNIT_EXECUTE_SEQUENTIAL_SCRIPT_COPY` | 20 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `CAMERA_FOLLOW_NAMED` | 19 |  | 纯表现（名字规则）；Sim.act / Sim.cond 有分支 |
| 已对拍 | `COUNTER_MATH_COUNTER` | 19 | a1 a2 a3 a6 a7 a9 | 引擎模型核心；台上量过、测试对拍：checks/engine_attach.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_SmokeBombSpecialPower` | 19 |  | 只记进时间线，没有效果 |
| 未做 | `PLAYER_DISABLE_BASE_CONSTRUCTION` | 16 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_ENABLE_UNIT_CONSTRUCTION` | 16 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PLAY_SOUND_EFFECT_AT_TEAM` | 16 |  | 纯表现（名字规则） |
| 不涉及 | `TOGGLE_LOCK_CURRENT_SELECTION` | 16 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `UNIT_SET_MODELCONDITION_FOR_DURATION` | 16 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_STOP_SEQUENTIAL_SCRIPT` | 16 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_EXIT_BUILDING` | 15 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_garrison.py |
| 未做 | `TEAM_UPGRADE` | 15 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `UNIT_SET_HEALTH` | 15 | a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aibuilding.py |
| 已对拍 | `GIVE_PLAYER_UPGRADE` | 14 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_spngp.py |
| 推断 | `MARK_MISSION_OBJECTIVE_COMPLETED` | 14 |  | 引擎模型核心 |
| 不涉及 | `MOVIE_PLAY_FULLSCREEN` | 14 |  | 纯表现（名字规则） |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleEnergizedArmorSpecialPower` | 14 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanEgg` | 14 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_KILL` | 14 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `PLAYER_SET_ALL_UNITS_TO_FLEE` | 14 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_runoffmap.py |
| 不涉及 | `SET_REFERENCE_TO_FIRST_TEAM_MEMBER_IN_AREA` | 14 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES` | 14 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiswitch.py |
| 未做 | `UNIT_EXECUTE_SEQUENTIAL_SCRIPT_LOOPING` | 14 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `DISABLE_MOUSE_HUD_FIXED_ELEMENT` | 13 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SET_LAST_CREATED_UNIT_TO_REFERENCE` | 13 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `TEAM_EXIT_ALL_BUILDINGS` | 13 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `GATE_CLOSE` | 12 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_GARRISON_NEAREST_BUILDING` | 12 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_SET_SPECIAL_POWER_COUNTDOWN` | 12 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleAfterburners` | 12 |  | 只记进时间线，没有效果 |
| 不涉及 | `OPTIONS_SET_OCCLUSION_MODE` | 12 |  | 纯表现（名字规则） |
| 未做 | `PLAYER_SELL_EVERYTHING` | 12 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER` | 12 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aipullback.py |
| 未做 | `TEAM_GARRISON_NEAREST_BUILDING` | 12 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_MOVE_TO_NEAREST_OBJECT_OF_KINDOF_OWNED_BY_PLAYER` | 12 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `DISABLE_JOYPAD_COMMANDBAR_BUTTON` | 11 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `FLASH_JOYPAD_COMMANDBAR_BUTTON` | 11 |  | 纯表现（名字规则） |
| 不涉及 | `FLASH_JOYPAD_HUD_FIXED_ELEMENT` | 11 |  | 纯表现（名字规则） |
| 已对拍 | `NAMED_REMOVE_UPGRADE` | 11 | a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_invuln.py |
| 不涉及 | `ORE_NODE_SET_MAX_GATHER_VALUE` | 11 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ArcherArrowBarrageSpecialPower` | 10 |  | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanMCV` | 10 |  | Sim.act / Sim.cond 有分支 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackSovietMCV` | 10 |  | Sim.act / Sim.cond 有分支 |
| 未做 | `PLAYER_ENABLE_BASE_CONSTRUCTION` | 10 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `ROTATE_CAMERA` | 10 |  | 纯表现（名字规则） |
| 未做 | `SKIRMISH_AI_CONSIDER_ALL_ENEMIES_WHEN_BUILDING` | 10 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `ZOOM_CAMERA` | 10 |  | 纯表现（名字规则） |
| 已对拍 | `MAP_SHROUD_SET_RESHROUD_TIME` | 9 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleHarpoonSpecialPower` | 9 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateLaserGlaiveBlastSpecialPower` | 9 |  | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackAlliedMiner` | 9 |  | Sim.act / Sim.cond 有分支 |
| 未做 | `PLAYER_DISABLE_UNIT_CONSTRUCTION` | 9 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_TOGGLE_SKIRMISH_AI` | 9 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `SET_COUNTER_TO_NUMBER_OBJECTS_PLAYER_OWNS_WITH_KINDOF` | 9 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_AI_START` | 9 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SOUND_ENABLE_TYPE` | 9 |  | 纯表现（名字规则） |
| 已对拍 | `SUB_FROM_MSEC_TIMER` | 9 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_timer.py |
| 已对拍 | `TEAM_GUARD_AREA` | 9 | a1 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 已对拍 | `TEAM_IDLE_FOR_FRAMECOUNT` | 9 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 未做 | `TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE_OWNED_BY_PLAYER` | 9 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `COUNTER_MATH_VALUE` | 8 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_contained.py |
| 未做 | `EXIT_SPECIFIC_BUILDING` | 8 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `FLASH_UI_PLAYER_POWER_BUTTON` | 8 |  | 纯表现（名字规则） |
| 已对拍 | `MAP_REVEAL_AT_WAYPOINT` | 8 | a1 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_CivilianStructureEvacuate` | 8 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleAlliedEngineerHeal` | 8 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_UnPackJapanBaseDefenseEgg` | 8 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateJumpSpecialPower` | 8 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateLeapSpecialPower` | 8 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `RESTART_TIMER` | 8 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_timer.py |
| 已对拍 | `SET_COUNTER_TO_COUNTER` | 8 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_aimicro.py |
| 未做 | `SET_PLAYER_KILLS_OF_TYPE_TO_COUNTER` | 8 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `CAMERA_STOP_FOLLOW` | 7 |  | 纯表现（名字规则） |
| 不涉及 | `FIRE_SPECIAL_POWER_ON_UNIT` | 7 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `NAMED_FACE_NAMED` | 7 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateRoarSpecialPower` | 7 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JAAS_Transform` | 7 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleMirageField` | 7 |  | 只记进时间线，没有效果 |
| 不涉及 | `PATH_MUSIC_ENABLE_DYNAMIC_SYSTEM` | 7 |  | 纯表现（名字规则） |
| 推断 | `TEAM_DELETE_LIVING` | 7 |  | Sim.act / Sim.cond 有分支 |
| 已对拍 | `UNIT_CHANGE_OBJECT_STATUS:NON_AUTOACQUIRABLE` | 7 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attach.py |
| 已对拍 | `UNIT_CHANGE_OBJECT_STATUS:UNATTACKABLE` | 7 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attach.py |
| 未做 | `ATTACK_MOVE_TEAM_TO_NEAREST_OBJECT_OF_TYPE_OF_PLAYER` | 6 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `DISABLE_COUNTDOWN_TIMER_DISPLAY` | 6 |  | 纯表现（名字规则） |
| 未做 | `NAMED_FACE_WAYPOINT` | 6 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleBinaryWeapon` | 6 |  | 只记进时间线，没有效果 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanPowerPlantEgg` | 6 |  | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_ActivateRoarSpecialPower` | 6 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_TriggerRushAttackSpecialPower` | 6 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PLAYER_FIRE_MULTI_TARGET_SPECIAL_POWER_AT_WAYPOINTS` | 6 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `TEAM_LOAD_TRANSPORTS` | 6 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `UNIT_ENABLE_HOUSE_COLOR` | 6 |  | 纯表现（名字规则） |
| 不涉及 | `BORDER_SHROUD_SET_OPACITY` | 5 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `CAMERA_STOP_TETHER_NAMED` | 5 |  | 纯表现（名字规则） |
| 未做 | `FIRE_SPECIAL_POWER_ON_NEAREST_OBJECTTYPE_BY_PLAYER` | 5 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `FIRE_SPECIAL_POWER_ON_TEAM` | 5 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `HIDE_UI` | 5 |  | 纯表现（名字规则） |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleDeployWeapon` | 5 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleRiotShieldSpecialPower` | 5 |  | 只记进时间线，没有效果 |
| 未做 | `TEAM_SET_HEALTH` | 5 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_MODELCONDITION_FOR_DURATION` | 5 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_SLEEP_STATUS` | 5 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `ENABLE_COUNTDOWN_TIMER_DISPLAY` | 4 |  | 纯表现（名字规则） |
| 未做 | `NAMED_ATTACK_AREA` | 4 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanMinerFromRefinery` | 4 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructSovietAntiVehicleVehicleTech2` | 4 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleJapanFortressShipTransformMode` | 4 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleMagneticArmor` | 4 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleShortCircuit` | 4 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_TriggerRushAttackSpecialPower` | 4 |  | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanBarracksEgg` | 4 |  | Sim.act / Sim.cond 有分支 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanRefineryEgg` | 4 |  | Sim.act / Sim.cond 有分支 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanWarFactoryEgg` | 4 |  | Sim.act / Sim.cond 有分支 |
| 未做 | `PLAYER_AI_CHANGEUNITBUILDER` | 4 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PLAYER_SET_DISABLED` | 4 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `SET_BLOOM_INTENSITY` | 4 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER_INCLUDE_DEAD` | 4 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SET_TEXTURE_LOOKUP_TABLE` | 4 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `SKIRMISH_AI_CLEAR_ALL_ENEMY_PLAYERS_PRIORITIES` | 4 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_FIRE_SPECIAL_POWER_AT_MOST_COST` | 4 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_CONTEXT_SENSITIVE_ATTACK` | 4 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `TEAM_ENABLE_HOUSE_COLOR` | 4 |  | 纯表现（名字规则） |
| 未做 | `TEAM_EXECUTE_SEQUENTIAL_SCRIPT` | 4 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_ATTACK_MOVE_TOWARDS_NEAREST_OBJECT_TYPE` | 4 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NO_COLLISIONS` | 4 |  | 状态位 NO_COLLISIONS 只记下来 |
| 已对拍 | `UNIT_GUARD_AREA` | 4 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 未做 | `UNIT_GUARD_OBJECT` | 4 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `MAP_REVEAL_ALL` | 3 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JapanAntiInfantryInfantryBonzai` | 3 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleShieldSphere` | 3 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_CAMPAlliedBomberDrop1` | 3 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PATH_MUSIC_FADE_IN_MUSIC` | 3 |  | 纯表现（名字规则） |
| 不涉及 | `RESET_CAMERA_AT_OBJECT` | 3 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `SKIRMISH_AI_CLEAR_ENEMY_PLAYER_PRIORITY` | 3 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ATTACK_MOVE_TOWARDS_NEAREST_OBJECT_TYPE` | 3 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ENTER_NAMED` | 3 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `TEAM_FLASH_WHITE` | 3 |  | 纯表现（名字规则） |
| 推断 | `TEAM_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT` | 3 |  | Sim.act / Sim.cond 有分支 |
| 未做 | `TEAM_GUARD_OBJECT` | 3 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_MODELCONDITION` | 3 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_STOP_SEQUENTIAL_SCRIPT` | 3 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NEXT_MOVE_IS_REVERSE` | 3 |  | 状态位 NEXT_MOVE_IS_REVERSE 只记下来 |
| 推断 | `ADD_TO_MSEC_TIMER` | 2 |  | 引擎模型核心 |
| 不涉及 | `AUDIO_FADE_VOLUME` | 2 |  | 纯表现（名字规则） |
| 不涉及 | `AUDIO_POP_MUSIC` | 2 |  | 纯表现（名字规则） |
| 不涉及 | `AUDIO_SET_SOUNDEFFECTS_SLIDER_FADEABLE` | 2 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `DISABLE_BORDER_SHROUD` | 2 |  | 纯表现（名字规则） |
| 未做 | `DISABLE_UI_UNIT_ABILITY_BUTTON` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT:specialpowercampalliedbomberdrop2` | 2 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateDisguiseSpecialPower` | 2 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_AlliedAntiInfantryVehicleEvacuate` | 2 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JASV_FireKiCannon` | 2 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JapanEngineerSprint` | 2 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateCryoLeapSpecialPower` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_DisguisedEvacuate` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_SovietAntiGroundAircraftEvacuate` | 2 |  | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanNavalYardEgg` | 2 |  | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_ActivateDisguiseSpecialPower` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_AlliedSupportAircraftShrinkRay` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_CaptureBuilding` | 2 |  | 只记进时间线，没有效果 |
| 不涉及 | `OVERRIDE_GLOBAL_TERRAIN_HEIGHT` | 2 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `PATH_MUSIC_FADE_OUT_MUSIC` | 2 |  | 纯表现（名字规则） |
| 不涉及 | `PATH_MUSIC_STOP_MUSIC` | 2 |  | 纯表现（名字规则） |
| 不涉及 | `PLAYER_CAMERA_TETHER_NAMED` | 2 |  | 纯表现（名字规则） |
| 未做 | `PLAYER_DISABLE_FACTORIES` | 2 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SCREEN_SHAKE` | 2 |  | 纯表现（名字规则） |
| 已对拍 | `SET_PLAYER_MONEY_TO_COUNTER` | 2 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiskirm.py |
| 推断 | `SET_RANDOM_TIMER` | 2 |  | 引擎模型核心 |
| 不涉及 | `SHOW_MISSION_OBJECTIVE` | 2 |  | 纯表现（名字规则） |
| 未做 | `SKIRMISH_AI_CONSIDER_ENEMY_WHEN_BUILDING` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_AI_USE_AUTOMATIC_ENEMY_PLAYER_PRIORITY_SCHEME` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ALL_USE_COMMANDBUTTON_ON_NEAREST_ENEMY_UNIT` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_FACE_WAYPOINT` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_GUARD_FOR_SECONDS` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_PARTIAL_USE_COMMANDBUTTON` | 2 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `TERRAIN_RENDER_DISABLE` | 2 |  | 纯表现（名字规则） |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:DYNAMICS_DISABLED` | 2 |  | 状态位 DYNAMICS_DISABLED 只记下来 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NO_AUTO_ACQUIRE` | 2 |  | 状态位 NO_AUTO_ACQUIRE 只记下来 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:WEAPON_UPGRADED_01` | 2 |  | 状态位 WEAPON_UPGRADED_01 只记下来 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:WEAPON_UPGRADED_02` | 2 |  | 状态位 WEAPON_UPGRADED_02 只记下来 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:WEAPON_UPGRADED_03` | 2 |  | 状态位 WEAPON_UPGRADED_03 只记下来 |
| 不涉及 | `CAMERA_BLOOM_EFFECT_BEGIN` | 1 |  | 纯表现（名字规则） |
| 不涉及 | `CAMERA_TETHER_NAMED` | 1 |  | 纯表现（名字规则） |
| 未做 | `DAMAGE_MEMBERS_OF_TEAM` | 1 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `FREEZE_TIME` | 1 |  | 纯表现（名字规则） |
| 推断 | `MARK_MISSION_OBJECTIVE_NOT_COMPLETED` | 1 |  | 引擎模型核心 |
| 不涉及 | `MOVE_TEAM_TO_UNIT` | 1 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `MUSIC_SET_TRACK` | 1 |  | 纯表现（名字规则） |
| 不涉及 | `MUSIC_SET_VOLUME` | 1 |  | 纯表现（名字规则） |
| 未做 | `NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT:specialpowernanoswarmhive` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_SET_SLEEP_STATUS` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateBribeSpecialPower` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateYurikoShieldRank3` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanAntiInfantryVehicle` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanAntiStructureVehicle` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanAntiVehicleShip` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanAntiVehicleVehicleTech1` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanAntiVehicleVehicleTech3` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanSentinelVehicle` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_Evacuate` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_PackAlliedMCV` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_PackJapanMCV` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_PackSovietMCV` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_PsyonicBlastSpecialPower` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_TimeBeltSpecialPower` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleAlliedGunshipAircraft` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleTargetPainter` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_UnPackAlliedMCV` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_UnPackJapanMCV` | 1 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_PackJapanMCV` | 1 |  | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackSovietSurveyor` | 1 |  | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_VacuumBomb` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_ActivateLaserGlaiveBlastSpecialPower` | 1 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PATH_MUSIC_ENABLE_RESUME_SYSTEM` | 1 |  | 纯表现（名字规则） |
| 不涉及 | `PITCH_CAMERA` | 1 |  | 纯表现（名字规则） |
| 未做 | `PLAYER_AI_CHANGEBASEBUILDER` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_AI_CHANGESCIENCEUPGRADER` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_AI_CHANGETEAMBUILDER` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_AI_CHANGE_ECONOMY_MANAGER` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_EXIT_ALL_BUILDINGS` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_UNIT_TYPE_SPECIAL_POWER_IGNORE_REQUIREMENTS` | 1 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `RESUME_BACKGROUND_SOUNDS` | 1 |  | 纯表现（名字规则） |
| 未做 | `SKIRMISH_AI_DONT_CONSIDER_ENEMY_WHEN_BUILDING` | 1 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SOUND_AMBIENT_PAUSE` | 1 |  | 纯表现（名字规则） |
| 不涉及 | `SOUND_AMBIENT_RESUME` | 1 |  | 纯表现（名字规则） |
| 不涉及 | `SOUND_ENABLE_ALL` | 1 |  | 纯表现（名字规则） |
| 不涉及 | `SUSPEND_BACKGROUND_SOUNDS` | 1 |  | 纯表现（名字规则） |
| 未做 | `TEAM_CLEAR_MODELCONDITION` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_FACE_NAMED` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_REMOVE_ALL_OVERRIDE_RELATIONS` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_EXPERIENCE_POINTS` | 1 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `TOGGLE_SHADER_OVERRIDE` | 1 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `UNFREEZE_TIME` | 1 |  | 纯表现（名字规则） |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:CAN_ATTACK` | 1 |  | 状态位 CAN_ATTACK 只记下来 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NO_BRIBE` | 1 |  | 状态位 NO_BRIBE 只记下来 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:UNDER_FROZEN` | 1 |  | 状态位 UNDER_FROZEN 只记下来 |
| 未做 | `UNIT_GIVE_EXPERIENCE_POINTS` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_GUARD_AREA_FROM_POSITION` | 1 |  | Sim.act / Sim.cond 不认识 |

## 脚本条件

| 状态 | 名字 | 用量 | 9 关用到 | 说明 |
|---|---|---|---|---|
| 已对拍 | `FLAG` | 5099 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | `TIMER_EXPIRED` | 3917 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `CONDITION_TRUE` | 2947 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `NAMED_DESTROYED` | 922 | 全部 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_crash_fall.py |
| 已对拍 | `PLAYER_HAS_OBJECT_COMPARISON` | 628 | a1 a4 a5 a7 | tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back |
| 已对拍 | `COUNTER` | 577 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | `HAS_FINISHED_AUDIO` | 495 |  | tests/test_simbench.py::test_audio_a_dubbed_line_is_done_its_length_after_it_is_heard |
| 已对拍 | `PLAYER_IS_HUMAN_OR_AI_PERSONALITY` | 470 |  | tests/test_simbench.py::test_scripts1_conditions_as_the_bench |
| 已对拍 | `HAS_FINISHED_VIDEO` | 422 |  | tests/test_simbench.py::test_video_a_radar_clip_is_done_after_its_length_full_screen_never |
| 已对拍 | `NAMED_INSIDE_AREA` | 413 | a3 a4 a5 a6 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aixfer.py |
| 已对拍 | `SKIRMISH_PLAYER_HAS_UNITS_IN_AREA` | 410 | a1 a3 a4 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_area.py |
| 已对拍 | `NAMED_OWNED_BY_PLAYER` | 397 | a4 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_engineer.py:a |
| 已对拍 | `NAMED_NOT_DESTROYED` | 374 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attach.py |
| 已对拍 | `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA` | 278 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aistate.py:a |
| 已对拍 | `NAMED_ATTACKED_BY_PLAYER` | 150 | a4 a5 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attack.py |
| 已对拍 | `UNIT_HAS_OBJECT_STATUS` | 142 |  | tests/test_simbench.py::test_scripts1_conditions_as_the_bench |
| 已对拍 | `COUNTER_SECONDS` | 141 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `UNIT_HEALTH` | 134 | a2 a4 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_air.py |
| 未做 | `MISSION_HOT_SPOT_ACTIVE` | 110 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_DISCOVERED` | 104 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_infveh.py |
| 未做 | `TEAM_ATTACKED_BY_PLAYER` | 93 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `UNIT_HAS_MODELCONDITION` | 88 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_spndisguise.py |
| 未做 | `TEAM_INSIDE_AREA_PARTIALLY` | 80 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `ENEMY_SIGHTED_BY_TEAM` | 69 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `IS_OBJECT_OF_TYPE` | 69 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 推断 | `CAMERA_ENTERED_AREA` | 60 |  | Sim.act / Sim.cond 有分支 |
| 推断 | `ENEMY_SIGHTED` | 59 |  | 部分：engine_levelvision a普通/英雄幻影在近点移除后对工程师240/310距离四路0/101/0/100，test_simbench_c重放；仅敌对关系范围查询已量，其他关系、隐形与精确边界未对拍，不登记整项 |
| 已对拍 | `COUNTER_COUNTER` | 55 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 未做 | `NAMED_SELECTED` | 50 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_DISCOVERED` | 47 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER` | 44 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_HAS_UNITS` | 39 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_OUTSIDE_AREA` | 38 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_air.py |
| 未做 | `TYPE_SELECTED` | 38 |  | Sim.act / Sim.cond 不认识 |
| 推断 | `TEAM_DESTROYED` | 35 |  | Sim.act / Sim.cond 有分支；台上量过（checks/engine_team.py），没有测试跑这个台子 |
| 未做 | `TEAM_INSIDE_AREA_ENTIRELY` | 33 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `DISTANCE_BETWEEN_TEAM` | 32 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_KILLED_TYPE_UNITS` | 29 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA` | 28 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_spawn.py:spawn |
| 已对拍 | `PLAYER_HAS_PLAYER_TECH` | 26 |  | tests/test_simbench.py::test_protocol_rank_two_at_frame_5400 |
| 未做 | `DISTANCE_BETWEEN_OBJ` | 25 |  | Sim.act / Sim.cond 不认识 |
| 推断 | `CURRENT_PLATFORM` | 24 |  | Sim.act / Sim.cond 有分支 |
| 未做 | `PLAYER_HAS_KILLED_NAMED_UNIT` | 24 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_HAS_KILLED_COMPARISON_UNIT_TYPE` | 21 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_CREATED` | 20 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ALL_HAS_OBJECT_STATUS` | 18 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TYPE_SIGHTED` | 17 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_SPECIAL_POWER_READY` | 16 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SOME_HAVE_OBJECT_STATUS` | 15 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_BUILDING_IS_EMPTY` | 13 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_HAS_FEWER_THAN_X_UNITS_WITH_KINDOF` | 12 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_ATTACKED_BY_OBJECTTYPE` | 10 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `OBJECT_IS_DISGUISED_AS_TYPE` | 10 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `PLAYER_HAS_COMPARISON_POWER_POINTS` | 10 |  | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 未做 | `TEAM_ATTACKED_BY_OBJECTTYPE` | 10 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `TEAM_COMPARE_NUM_MEMBERS` | 10 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiskirm.py |
| 不涉及 | `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA_WITH_MODELCONDITION` | 9 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `PLAYER_HAS_POWER` | 9 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_infiltrator.py:a |
| 已对拍 | `PLAYER_TRIGGERED_SPECIAL_POWER` | 9 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8b.py |
| 未做 | `BUILT_BY_PLAYER` | 8 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `GATE_IS_OPEN` | 8 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_DESTROYED_N_BUILDINGS_PLAYER` | 8 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_CREDITS` | 8 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED` | 8 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_EXITED_AREA` | 7 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_SPECIAL_POWER_READY` | 7 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `PLAYER_HAS_NO_POWER` | 6 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_infiltrator.py:a |
| 已对拍 | `PLAYER_EXCESS_POWER_COMPARE_VALUE` | 5 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_infiltrator.py:a |
| 推断 | `PLAYER_TRIGGERED_SPECIAL_POWER_FROM_NAMED` | 5 |  | Sim.act / Sim.cond 有分支 |
| 已对拍 | `PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS` | 4 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aimicro.py |
| 推断 | `PLAYER_TRIGGERED_SPECIAL_POWER_IN_AREA` | 4 |  | Sim.act / Sim.cond 有分支 |
| 未做 | `TEAM_CAN_PATH_TO_WAYPOINT` | 4 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_COMPARISON_UNIT_KIND` | 3 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_COMMAND_BUTTON_READY_PARTIAL` | 3 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_DESTROYED_BY_OBJECTTYPE` | 2 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_DYING` | 2 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_crush.py:all |
| 未做 | `PLAYER_HAS_NUMBER_OBJECTS_WITH_MODELCONDITION` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_LOST_OBJECT_TYPE` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ENTERED_AREA_PARTIALLY` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_IS_ATTACKED_AND_CANNOT_RETALIATE_ANY` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_OUTSIDE_AREA_ENTIRELY` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_HAS_UPGRADE` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `BUILDING_GARRISONNED_BY_OBJECT_TYPE` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `EVAL_TEAM_HEALTH` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA_COMPLETELY_BUILT` | 1 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `PLAYER_HAS_NUM_UNITS_WITH_UPGRADE` | 1 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiupgrade.py |
| 未做 | `PLAYER_TRIGGERED_SCRIPT_EVENT` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_EXITED_AREA_PARTIALLY` | 1 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_OWNED_BY_PLAYER` | 1 |  | Sim.act / Sim.cond 不认识 |

## 物体模块

| 状态 | 名字 | 用量 | 9 关用到 | 说明 |
|---|---|---|---|---|
| 不涉及 | `Draws/ScriptedModelDraw` | 1895 (2888) | 全部 | 纯表现（Draws）；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 已对拍 | `Body/PropBody` | 1443 (2758) | 全部 | tests/test_simbench_c.py::test_prop_body_no_health_a_kill_leaves_the_street_and_topples_the_tree_and_lantern_at_the_bench_frames；例：AlliedAirField_Collapse, AlliedAntiAirShip_Collapse |
| 不涉及 | `Behaviors/FXListBehavior` | 796 (1241) | 全部 | 纯表现（名字规则）；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 已对拍 | `Body/ActiveBody` | 790 (1398) | 全部 | tests/test_simbench.py::test_super_the_proton_collider_ends_as_the_bench；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 不涉及 | `Behaviors/ObjectDefectionHelper` | 640 (1059) | 全部 | 没人触发：原版只在 BaseObject 挂一个空的（所以每个物体都有），SageXML 里没有一处 DefectorSpecialPower，脚本动作表里也没有叛变；《将军》里它管"叛变后一段时间不被发现"；例：AlliedSatelliteSweepShroudRevealer, AlliedTimeBombLvl1 |
| 不涉及 | `Behaviors/ObjectSMCHelper` | 640 (1059) | 全部 | 纯表现：《将军》ObjectSMCHelper 到时清掉"定时模型状态"（UNIT_SET_MODELCONDITION_GENERIC 的秒数），只换画法；例：AlliedSatelliteSweepShroudRevealer, AlliedTimeBombLvl1 |
| 已对拍 | `Behaviors/AttributeModifierPoolUpdate` | 622 (910) | 全部 | tests/test_simbench.py::test_super_the_iron_curtain_holds_off_fire_some_23_seconds；例：AlliedAntiVehicleVehicleTech3CannonNodeBase, AlliedAntiVehicleVehicleTech3CannonNodeEnd |
| 已对拍 | `Behaviors/SecondaryDamageTracker` | 617 (852) | 全部 | tests/test_simbench.py::test_cryo_a_frozen_tank_melts_334_frames_after_the_beam_whatever_the_beam；例：AlliedSatelliteSweepShroudRevealer, AlliedTimeBombLvl1 |
| 已对拍 | `Behaviors/CreateObjectDie` | 591 (838) | 全部 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_crash_fall.py；例：AlliedAntiGroundAircraft_Dying, AlliedBomberAircraft_Dying |
| 已对拍 | `Behaviors/DestroyDie` | 578 (1006) | 全部 | tests/test_simbench.py::test_destroy_die_a_building_killed_is_dying_one_frame_and_gone；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 已对拍 | `Behaviors/SquishCollide` | 569 (749) | 全部 | tests/test_simbench.py::test_crush_a_tank_drives_over_a_lower_level_and_leaves_an_equal_one；例：AlliedSatelliteSweepShroudRevealer, AlliedWallPiece |
| 已对拍 | `Behaviors/SlowDeath` | 565 (1480) | 全部 | tests/test_simbench.py::test_slow_death_a_crushed_conscript_lies_127_frames_dying_and_in_its_spot；例：AlliedAirField_Collapse, AlliedAntiAirShip_Collapse |
| 不涉及 | `Behaviors/BuildingDestructionBehavior` | 493 (650) | a1 a2 a4 a5 a6 a7 a8 a9 | 纯表现：建筑死后按骨骼放特效、甩碎块（CreationObject 如 AlliedBarracks_Debris：只有画法、寿命和碎片体积，没有身体和武器）、烟尘；例：AlliedAirfield, AlliedBarracks |
| 不涉及 | `ClientBehaviors/ModelConditionAudioLoopClientBehavior` | 466 (649) | 全部 | 纯表现（ClientBehaviors）；例：AlliedSatelliteSweepShroudRevealer, AlliedAirfield |
| 不涉及 | `Behaviors/Physics:不动` | 454 (630) |  | 模板上没有 AIUpdate 类模块（不能下命令、没有移动器）：默认物理不让它自己动，被甩飞、击飞另算（DynamicsUpdate、MetaImpactNugget）；原版字段全是默认（E 线 work/re/e_na_physics_mcu.md） |
| 已对拍 | `Behaviors/ProductionUpdate` | 351 (465) | a1 a2 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_production_pays_as_it_builds_and_comes_out_after_the_door；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | `Behaviors/ToppleUpdate` | 347 (410) | a4 | tests/test_simbench_c.py::test_topple_the_five_props_disappear_at_the_bench_frames_without_ever_dying；例：BaseTopple, BaseTree |
| 不涉及 | `Behaviors/ModelConditionUpgrade` | 341 (465) | 全部 | 纯表现：只加模型状态（民房/步兵按阵营换画法、支援技能画法），同模板的非画法模块和原版脚本 UNIT_HAS_MODELCONDITION 都不读（E 线 work/re/e_na_physics_mcu.md）；例：AlliedAntiInfantryInfantry, AlliedAntiVehicleInfantry |
| 已对拍 | `Behaviors/BuildingBehavior` | 334 (440) | a1 a2 a4 a5 a6 a7 a8 | tests/test_simbench.py::test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | `Behaviors/AttributeModifierAuraUpdate` | 311 (420) | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_invuln.py；例：A09_IronCurtainEffect, BaseCivilianStructure |
| 已对拍 | `Behaviors/InvisibilityBehavior` | 305 (412) | a4 a5 a9 | tests/test_simbench_c.py::test_invisibility_behavior_a_house_given_garrison_can_stealth_by_script_is_shot_like_a_plain_one；例：BaseCivilianStructure, BaseCivilianStructureLarge |
| 已对拍 | `Behaviors/ContestableGarrisonContain` | 305 (411) | a4 | tests/test_simbench_c.py::test_garrison_script_entry_skips_room_and_relation_owner_follows_and_damage_or_kill_ejects_alive_at_the_bench；例：BaseCivilianStructure, BaseCivilianStructureLarge |
| 不涉及 | `Draws/PropDraw` | 221 (301) |  | 纯表现（Draws）；例：AM_Trash01, AM_Debris01 |
| 已对拍 | `Behaviors/FireWeaponWhenDead` | 146 (230) | 全部 | tests/test_simbench_c.py::test_fire_weapon_when_dead_a_scripted_kill_blows_the_mig_and_the_guardian_beside_it；例：AlliedAntiGroundAircraft_Dying, AlliedAntiStructureVehicleCannonEffect |
| 已对拍 | `Behaviors/Physics` | 143 (206) | 全部 | tests/test_meta_impact.py::test_physics_p5_a_shot_down_wreck_falls_the_knock_curve_under_its_own_gravity；例：AlliedAntiGroundAircraft_Dying, AlliedBomberAircraft_Dying |
| 不涉及 | `ClientBehaviors/ModelConditionSoundSelectorClientBehavior` | 140 (195) | 全部 | 纯表现（ClientBehaviors）；例：AlliedSatelliteSweepShroudRevealer, AlliedAirfield |
| 不涉及 | `Draws/DynamicsDraw` | 138 (857) | a4 | 纯表现（Draws）；例：AlliedAirField_Collapse, AlliedAntiAirShip_Collapse |
| 已对拍 | `Behaviors/EnableDynamicsCollide` | 137 (154) | a4 | tests/test_simbench_c.py::test_enable_dynamics_collide_a_lantern_without_it_is_crushed_and_gone_at_the_same_frames；例：BaseSimulatedProp, AM_Boat01 |
| 已对拍 | `AI/AIUpdate` | 136 (237) | 全部 | tests/test_simbench.py::test_r8_idle_within_sight_walks_up_fires_and_comes_back；例：AlliedSatelliteSweepShroudRevealer, AlliedSuperWeaponEffect |
| 已对拍 | `Behaviors/StancesBehavior` | 108 (148) | 全部 | tests/test_simbench_c.py::test_stance_hold_fire_stops_a_standing_attack_order；例：AlliedSatelliteSweepShroudRevealer, AlliedAirfield |
| 已对拍 | `Body/ImmortalBody` | 91 (111) |  | tests/test_simbench_c.py::test_immortal_damage_stops_at_one_hp_kill_is_damage_and_delete_removes；例：BaseRock, CPDummyTarget |
| 已对拍 | `Behaviors/LevelUpUpgrade` | 88 (124) | 全部 | tests/test_simbench_c.py::test_levelup_creation_grants_reach_heroic_only_after_three_distinct_triggers；已测范围：engine_levelup a创建升级触发升阶、重复持有不升级；b移除创建升级保留等级，老兵创建升级移除重给可再次升阶，英雄位0/0/0/1→0/0/1/1→0/1/1/1；c独立精英/英雄创建升级各自移除重给两次，首次仍0/0/0/1、第二次0/1/1/1；engine_leveldamage a等级DAMAGE_MULT125保持到精英/英雄，单发血量47/34/34/17；engine_levelhealth a满血升级HEALTH_MULT125保持到英雄，100脚本伤害同帧冻结80/80/84/84；b残血升精英保留血量比例50/80/50/20，再扣100血为30/64/34/4，当前和最大血量均乘1.25，simlevel及test_simbench_c重放；engine_levelrange a原版幻影普通炮125、英雄炮150叠加RANGE125%为187.5，220距离仅英雄命中、260距离均未命中，四路100/10100/100/10100→100/10017/100/10100，离位异常均0；engine_levelrate a幻影普通/直接英雄武器/创建英雄/创建精英三段周期25/25/20/25帧，最终血量84/80/68/80，ROF不增加单发伤害；仅此离散单发炮配置已量，射速分段取整/其他武器仍未对拍；engine_levelshroud a原版幻影基础揭雾500、创建英雄SHROUD_CLEARING125%预测625，580/750距离普通/英雄四路1/1/1/1→1/111/1/101，近点始终可见且无离位；仅此模板配置已量，精确边界未对拍；engine_levelvision a原版幻影普通/创建英雄对小包围体工程师240/310距离ENEMY_SIGHTED四路11/11/11/11→0/0/0/0→0/101/0/100，近点在正式窗口前删除且无离位，支持VISION125按1.25倍率为250的预测；仅脚本范围查询已量，精确边界/自动索敌未对拍；gap：英雄自动索敌、精确射程/揭雾/视野边界、射速分段取整/其他武器、其余模板/等级属性、经验成长、额外上限及Permanent=true未对拍；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证；这些分支与已测效果共用模板，不能按SPLIT_STILL互斥拆分用量；例：AlliedSatelliteSweepShroudRevealer, AlliedAntiAirShip |
| 已对拍 | `Behaviors/AutoHealBehavior` | 88 (123) | 全部 | tests/test_simbench.py::test_autoheal_an_apocalypse_mends_two_points_every_7_frames_after_a_15_frame_wait；例：AlliedSatelliteSweepShroudRevealer, AlliedAntiAirShip |
| 已对拍 | `Behaviors/RunOffMapBehavior` | 88 (123) | 全部 | tests/test_simbench_c.py::test_run_off_map_the_peacekeeper_is_gone_64_and_304_frames_after_the_order_never_dying；例：AlliedSatelliteSweepShroudRevealer, AlliedAntiAirShip |
| 已对拍 | `Behaviors/WeaponSetUpdate` | 82 (110) | 全部 | tests/test_simbench_c.py::test_weapon_set_the_status_picks_the_gun_molotov_under_the_toggle_and_the_painter_does_no_harm；例：AlliedBaseDefense, AlliedBaseDefenseAdvanced |
| 已对拍 | `Behaviors/SpecialPower` | 74 (95) | 全部 | tests/test_simbench.py::test_super_a_scripts_cast_starts_the_retail_reload；例：AlliedConstructionYard, AlliedAntiAirShip |
| 已对拍 | `Behaviors/DynamicsUpdate` | 69 (101) | 全部 | tests/test_simbench_c.py::test_dynamics_update_a_hammer_without_it_crushes_and_goes_round_as_the_retail_one；例：AlliedDynamicsImpact, AlliedSatelliteSweepShroudRevealer |
| 已对拍 | `Behaviors/RepairUpdate` | 66 (91) | a1 a2 a4 a5 a6 a7 a8 a9 | tests/test_simrepair_ai.py::test_ai_repair_funded_and_zero_credit_final_readings；repairai a/repairq a/repairt a/repairzero a按名重放：开局足额资金、默认1000HP/800造价电厂初始50%/25%/75%血约10HP/s修满、实扣100/225/25，费用按缺血比例平方；零资金无经济不修；tests/test_simrepair_ai.py。只支持已测配置，完整配置门禁保留；gap：玩家入口、废墟维修、受伤停修、其他初始血量/造价/速率及资金耗尽未测；AI启动相位INFERRED；按总控11-11三切片收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | `Behaviors/StatusBitsUpgrade` | 66 (85) | 全部 | tests/test_simbench_c.py::test_status_bits_upgrade_the_heroic_grant_sets_weapon_upgraded_and_a_removal_clears_it；例：AlliedBaseDefense, AlliedAntiAirShip |
| 已对拍 | `Behaviors/EngineerContain:通用三国` | 63 (87) | a1 a2 a4 a5 a6 a7 a8 | tests/test_simengineer.py::test_engineer_soviet_japan_captures_as_on_the_bench；已测范围：engine_engineer a/b/c/d普通进入，三国工程师中立/敌方半血电厂占领并消耗、友军半血修满并消耗、满血拒入且存活；按完整配置匹配登记63用量/87模板；gap：精确进入帧仍INFERRED；日本单人ALLIES和桥配置保留在未对拍残余行，不借本组登记；例：AlliedPowerPlant |
| 已对拍 | `Behaviors/StructureUnpackUpdate` | 59 (96) | a1 a2 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_power_back_after_the_plant_unpacks；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | `Behaviors/StructureSellUpdate` | 52 (72) | a1 a2 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames；例：AlliedAirfield, AlliedBarracks |
| 不涉及 | `ClientBehaviors/AnimationSoundClientBehavior` | 48 (67) | 全部 | 纯表现（ClientBehaviors）；例：AlliedTimeBombLvl3, AlliedRefinery |
| 不涉及 | `Behaviors/DynamicsUpdate:起义专有` | 44 (53) |  | 起义时刻专有模板：继承链上的父模板 RA3 数据里没有（SS_Fling* 的 BaseClientFlingableProp），RA3 的 mod 编不过（engine_dynamics c，11-10 地图编译报 Critical），玩家在 RA3 里见不到 |
| 不涉及 | `Draws/TruckDraw` | 35 (51) | 全部 | 纯表现（Draws）；例：AlliedTimeBombLvl1, AlliedTimeBombLvl2 |
| 不涉及 | `Behaviors/LUAEventList` | 32 (44) | 全部 | 纯表现：EventListName连接原版ScriptEvents.xml与Scripts.lua；RA3声明可达的事件处理函数只调用模型部件显隐（及tostring），含继承；未定义的AlliedInfantryFightingFunctions无可达处理函数；C&C3升级/状态函数不可达。tests/test_inventory_lua.py静态核对游戏包与SDK声明，非上台对拍；例：AlliedAirfield, AlliedBarracks |
| 推断 | `Behaviors/InfiltratorContain` | 30 (32) | a1 a2 a4 a5 a6 a7 a8 | ENERGY已按总控11-11决定拆分登记4用量/6模板；本行剩余10种配置30用量/32模板：KILL 1、STEAL_MONEY 3、VISION 5+港口阻断型1、PARALYZE 3、VISION_UNITS飞机2/步兵3/舰船3/车辆4、RESET 5；普通VISION仅engine_infvis a/b盟军间谍对盟/苏建造场最小对照：敌方消耗不换主、友军拒入、近处可见而远处及第三方不可见，tests/test_siminfiltrator.py::test_spy_ordinary_vision_as_on_the_bench；a首次发现s16、b首次发现s18，仅稳定窗口回放；E76日本宿主engine_infvis c首次发现s19，原s18窗口FAIL，严格xfail且未扩展宿主模型，见work/re/e_infvis_e76.md；约5秒生效延迟/视野半径映射/宿主死亡清理INFERRED，跨宿主精确时序仍gap；STEAL_MONEY的engine_infmon a两次量到2000转账和后续矿车收入，匿名矿车清除无效、未闭环且暂停；tests/test_siminfiltrator.py::test_spy_refinery_money_as_on_the_bench为严格xfail，未实现该效果；E77车辆VISION_UNITS仅engine_infveh a原版盟军战车厂对已有车辆/同属步兵/第三方车辆对照：敌消耗、友拒入，可见编码只出现车辆位1但间歇回0，连续可见原窗口FAIL，tests/test_siminfiltrator.py具名实测回放严格xfail；观察者调度/时效/新产单位仍gap，未实现该效果，见work/re/e_infveh_e77.md；其他模板/间谍、精确时序、持久性/重复进入及其余效果仍gap，不登记整组或整模块已对拍；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | `Behaviors/ToggleStatusSpecialAbilityUpdate` | 27 (34) | 全部 | tests/test_simbench_c.py::test_toggle_status_a_press_moves_to_the_next_state_unpack_delays_it_and_a_held_state_takes_no_press；例：AlliedAntiAirShip, AlliedAntiInfantryInfantry |
| 不涉及 | `Behaviors/SubObjectsUpgrade` | 26 (30) | 全部 | 纯表现（名字规则）；例：AlliedAirfield, AlliedBarracks |
| 不涉及 | `Behaviors/FreefallUpdate` | 24 (31) | 全部 | 纯表现（总控 11-11 定）：配置只有 InitialVelocity / Acceleration / TerminalVelocity / ModelConditionsToSet=STUNNED_FLAILING，管空中死亡后尸体下落的画面；engine_freefall fall 已核人炮扔出的兵原版 / 改慢 / 改快三份读数一样（AIRBORNE_TARGET 1-125 帧、22 帧到点、降落伞约 96 帧），不归本模块。gap：被举起后落下（ActivateLiftObjectNugget / LiftObjectUpdate，C 已接通计时、落地仍 gap）可能用到下落速度，落地时刻会影响逻辑，未上台；同 id 覆盖是否生效未排除；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 已对拍 | `Behaviors/AttributeModifierUpgrade` | 22 (30) | 全部 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_invuln.py；例：AlliedOutpost, AlliedAntiGroundAircraft |
| 已对拍 | `Behaviors/CrushDie` | 22 (28) | 全部 | tests/test_simbench.py::test_crush_a_tank_drives_over_a_lower_level_and_leaves_an_equal_one；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 已对拍 | `Behaviors/SuppressionUpdate` | 22 (28) | 全部 | tests/test_simbench_c.py::test_suppression_samples_entry_refresh_and_expiry_at_the_four_probe_readings；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 不涉及 | `Draws/LaserDraw` | 21 (37) | 全部 | 纯表现（Draws）；例：AlliedAntiVehicleVehicleTech3CannonNodeBase, AlliedAntiVehicleVehicleTech3CannonNodeEnd |
| 不涉及 | `Behaviors/LaserState` | 19 (25) | 全部 | 纯表现：LaserId关联光束，起止粒子/骨骼/EndOffset与ObjectStatusValidation只控制光束表现；LaserStateModule.xsd无伤害字段；engine_laser pair匹配LaserDraw/State 201，伤害由独立DamageNugget给出，test_simbench_c重放2/90/2/90；例：AlliedBaseDefense, AlliedBaseDefenseAdvanced |
| 已对拍 | `Behaviors/QueueProductionExitUpdate` | 19 (20) | a1 a2 a4 a5 a6 a7 a8 | tests/test_simbench.py::test_a_new_unit_stops_beyond_the_natural_rally_point_as_the_bench；例：AlliedBarracks, AlliedConstructionYard |
| 已对拍 | `Behaviors/ReplaceSelfSpecialAbility` | 18 (24) | a1 a2 a4 a5 a6 a7 a9 | tests/test_simbench.py::test_a_yard_packs_into_its_mcv_at_once_and_the_mcv_stands_before_it_drives；三类用法都上台：基地车 / 帝国蛋到点展开（engine_unpack mcv / egg，名字和血量比例跟过去）、三国建造场收起（engine_pack a/s/j，按下当帧就是基地车，先站 2 秒 + 约 14 帧再开，14 帧是拟合 INFERRED）；gap：盟军矿车、苏联勘探车的展开没上台，其余 8 种蛋按同一机制推；例：AlliedConstructionYard, AlliedMCV |
| 不涉及 | `Draws/TracerModelDraw` | 18 (22) | 全部 | 纯表现（Draws）；例：AlliedAntiAirShip, AlliedAntiAirVehicleTech1 |
| 已对拍 | `Behaviors/WeaponFireSpecialAbilityUpdate` | 16 (23) | a1 a2 a4 a5 a6 a7 | tests/test_simbench.py::test_a_weapon_fire_ability_goes_off_after_its_unpack_and_holds_the_caster_through_its_pack；例：AlliedSuperWeaponAdvanced, AlliedAntiNavalScout |
| 已对拍 | `Body/ManagerBody` | 14 (32) | a1 a4 a7 | tests/test_simmanagerbody.py::test_manager_body_script_damage_preserves_retail_bridge_proxy；已测范围：engine_managerbody a/b原版HB_Bridge_02，270/700长度整体代理脚本伤害200后均80%、致命量后1%且存活，tests/test_simmanagerbody.py按名重放；gap：有效HP取CenterPiece及内部1%下限映射仍INFERRED，内部最大血量/伤害转发/显示下限待核；HV_Bridge_01等其他模板/配置、桥段共享血量/损毁/维修未对拍；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母；例：BaseBridge, BaseCivilianBridge |
| 已对拍 | `Behaviors/BridgeBuilder` | 14 (30) | a1 a4 a7 | tests/test_simbridgebuilder.py::test_bridgebuilder_counts_short_and_long_retail_bridges；已测范围：engine_bridgebuilder:a已量HB_Bridge_02长度270/700，EndCap/EndCap2/CenterPiece/CenterPieceB/GateHouse数量1/1/1/0/2及1/1/2/2/2；engine_bridgebuilder_b:b已量原版HB桥首16+Bridge1a桥尾32混合构型，两长度HB数量不变、五类Bridge1物件均0；tests/test_simbridgebuilder.py按名核计数模型与读数编码，simunits仅有限数量模型；gap：HV_Bridge_01等其他桥型/配置/长度、世界物体生成/位置、通行、损毁、共享血量与维修未建模；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母；例：AM_Bridge_01, AM_Bridge_01a |
| 已对拍 | `AI/JetAIUpdate` | 13 (17) | 全部 | tests/test_simjet.py::test_jet_vindicator_first_entry_frame_matches_bench；已测范围：engine_jet:a/b原版维和轰炸机静止正东起步，距离1200/600，首次入框97/47，框内1且血100%；simjet按逐帧位置实现首步2.7（机制INFERRED）、每帧+0.8至12；tests/test_simjet.py按名回放两种时钟均97/47，并核启动位置和入框112/62帧；未新增上台；gap：其他配置/机型、重复命令/转弯、MinSpeed、起飞高度/盘旋/降落、机场/跑道/停车位、返场补弹/耗尽伤害及攻击状态，配置与动作门禁保留；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母；例：AlliedAntiGroundAircraft, AlliedAttackDrone |
| 已对拍 | `Behaviors/TransportContain` | 13 (16) | a1 a2 a4 a5 a7 a9 | tests/test_simbench.py::test_transport_a_team_put_in_instantly_skips_the_room_and_the_relation_and_rides_along；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryVehicle |
| 已对拍 | `Behaviors/SpawnBehavior` | 10 (16) | a1 a2 a4 a5 a6 a7 a8 | tests/test_simspawn.py::test_spawn_initial_burst_and_parent_kill_delete_match_named_bench；已测范围：engine_spawn:spawn开局3架及母体死亡/删除清随从；engine_spawn_refill:refill两架分别死亡10秒后补回（tests/test_simspawn.py显式预置贴车位置）；engine_spawn_power:power缺电及复电期间总数/厂旁均3；gap：自主维修飞行、子体直接删除、真正禁用/占领、缺电时死亡补充、展开时机及其他完整配置，生成位置和秒内相位INFERRED；按总控11-11三切片收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母；例：AlliedAirfield, AlliedConstructionYardRepairBay |
| 不涉及 | `Behaviors/ProductionUpdateInfo` | 9 (9) | a1 a4 a5 a6 a7 a9 | 纯界面状态：保存七个生产类别的侧栏子页签编号；读写限于侧栏编号维护、变形时保留编号和存档传递，没有游戏逻辑读者，模拟器不建模；9用量/9模板保留；读者闭包证据见 work/re/e_production_e56.md，非上台对拍；例：AlliedConstructionYard, AlliedMCV |
| 已对拍 | `Behaviors/EjectPassengersSpecialAbilityUpdate` | 7 (8) | a2 a5 a9 | tests/test_simbench.py::test_transport_the_man_cannon_throws_one_every_half_second_and_a_killed_transport_kills_its_men；例：AlliedBomberAircraft, A08_CenturyTransportAircraft |
| 未做 | `Behaviors/BezierProjectile` | 6 (78) | 全部 | 已核（11-08）：模拟器没有这个效果（开火按每秒伤害直接扣血，没有弹体）；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 推断 | `Behaviors/AssignSlavesTargetObjectSpecialPower` | 6 (10) | a2 a4 a5 a7 a8 | 模拟器代码里有这个名字；台上量过（checks/engine_assignslaves.py），没有测试跑这个台子；例：AlliedConstructionYardRepairBay, AlliedNavalYard |
| 未做 | `Behaviors/TrackDamage` | 6 (9) | a1 a2 a3 a4 a5 a6 a7 a8 | E69静态核实：6个SDK配置均InstantWeaponsOnly=true，TimeToTrack为0/1/2s；现有expected_damage只接来弹，历史伤害仍gap。与C线瞬发历史接口工单重叠，E暂停独立探针；尚无本模块具名实测回放，不登记已对拍、不改分母；见work/re/e_trackdamage_e69.md；例：AlliedAntiNavalScout, AlliedFighterAircraft |
| 未做 | `Behaviors/TrackIncomingWeaponFireBehavior` | 6 (9) | a1 a2 a3 a4 a5 a6 a7 a8 | 部分：engine_inform_probe a/off通知记录回放验证录入、30帧窗口、来源与武器匹配删除和过期清理；精确过期边界INFERRED，原版完整调度/历史伤害仍gap，不靠名字命中晋升整项；例：AlliedAntiNavalScout, AlliedFighterAircraft |
| 已对拍 | `Behaviors/EngineerContain:三国ALLIES` | 6 (7) | a1 a2 a4 a5 a6 a7 a9 | tests/test_simengineer.py::test_engineer_allied_defence_refusal_soviet_japan_as_on_the_bench；已测范围：engine_engineer a/e/f普通进入，三国工程师友军半血防御修满并消耗、满血及敌方拒入且存活，目标归属不变；按完整配置匹配登记6用量/7模板；gap：精确进入帧仍INFERRED；日本单人ALLIES和桥配置保留在未对拍残余行，不借本组登记；例：SovietBaseDefenseGround |
| 已对拍 | `Behaviors/OCLSpecialPower` | 6 (7) | a1 a2 a4 a6 a7 | tests/test_simocl.py::test_iron_curtain_zero_count_ocl_reference；总控第四切片按已测边界收尾：tests/test_simocl.py具名回放engine_oclcurtain/engine_oclnone/engine_oclwrong a，铁幕宿主匹配模块才保护并记事件，删除/改绑模块无保护/事件；engine_oclempty a空声明无保护且事件1；engine_oclcopy a完整原版载荷改名仍保护100/100且事件1；engine_oclzero a仅外层Count=0无保护且事件1。只闭合铁幕派发和零数量不保护边界，未测生成数量/通用生成；其他非零数量/载荷/超武、位置/过滤、按钮/冷却仍gap，继承、等价空声明及格式等价INFERRED，不表示全模块全字段验证；见 work/re/e_ocl_e65.md；例：AlliedSuperWeaponAdvanced, CAMP_PowerStore_AlliedBomberDrop |
| 未做 | `Behaviors/SubStructureStorageBehavior` | 6 (6) | a1 a4 a5 a6 a7 a9 | 6用量/6模板为三国MCV及海军继承型，模块无专用字段；有效配置没有SubStructureBuild，未找到可生成待存子结构的原版入口；gap：保存/恢复专属读数及合法触发待接口核实，未上台、不登记已对拍，也不据此排除运行时用途；普通展开及COPY_UPGRADES不能归因；见 work/re/e_substorage_e57.md；例：AlliedMCV, AlliedMCV_Naval |
| 推断 | `Behaviors/WallBuilderBehavior` | 6 (6) | a1 a2 a4 a6 a7 a9 | 部分：engine_wallinit:a有/无模块对照10/11/10，仅StartInSecondaryModel默认WALL_SEGMENT初始化；6/6权重保留，建墙/连接/段数上限/生死联动及自定义配置仍gap，未登记完整已对拍；见 work/re/e_wallbuilder_e58.md；例：AlliedWallPiece, AlliedWallSegmentPiece |
| 推断 | `Behaviors/PassiveAreaEffectBehavior` | 5 (14) | a3 a4 a7 | E70部分：engine_passivearea a按名回放工程师独立范围治疗；状态开启、40距离同属步兵100%，400距离步兵/60距离车辆/未开启源旁步兵50%，关闭再扣血后四路50%。E74按名回放f/g阈值帧11/31/51/71与16/36/56/76，每20帧分批治疗；共用任务帧相位及SDK每秒10%换算跳幅INFERRED，时钟来源/动态创建与重开/调查周期/叠加/跨玩家关系/自身受益/附着无人机仍gap，不登记整项已对拍；tests/test_simpassivearea.py；见work/re/e_passive_e74.md；例：AlliedAirfieldRepairDrone, AlliedEngineer |
| 未做 | `Behaviors/EmotionTrackerUpdate` | 5 (7) | a1 a2 a3 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedCommandoTech1, AlliedEngineer |
| 未做 | `Behaviors/MonitorSpecialPowerTimerUpdate` | 5 (6) |  | 模拟器代码里没有这个名字；例：AlliedSuperWeapon, AlliedSuperWeaponAdvanced |
| 未做 | `Behaviors/AttackAssistResponseBehavior` | 5 (5) | a1 a2 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedBaseDefenseAdvanced, SovietBaseDefenseAdvanced |
| 未做 | `Behaviors/CaptureSpecialAbilityUpdate` | 5 (5) | a1 a2 a3 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedCommandoTech1, AlliedEngineer |
| 推断 | `Behaviors/CommandSetUpgrade` | 5 (5) | a1 a4 a5 a7 | 模拟器代码里有这个名字；例：AlliedConstructionYard, AlliedOutpost |
| 未做 | `Behaviors/QueueDockBehavior` | 4 (12) | a1 a2 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedRefinery, AlliedRefinery_NoHarvester |
| 推断 | `Behaviors/AutoDepositUpdate` | 4 (8) | a1 a4 a5 a7 | 模拟器代码里有这个名字；例：GE_SwissBank, NY_NYStockExchange |
| 已对拍 | `Behaviors/InfiltratorContain:ENERGY` | 4 (6) | a2 a4 a5 a6 a7 a8 | tests/test_siminfiltrator.py::test_spy_power_plant_as_on_the_bench；总控11-11授权按配置组收尾：engine_infiltrator a/b/c/d按名字重放，盟军间谍对盟/苏/帝普通电厂及帝国忍者对盟军电厂，敌方进入者消耗、建筑满血不换主、100电量停电约20秒并恢复，友军拒入且存活；gap：其他电量/苏联超级电厂、重复进入续期、精确时序和默认状态分支仍未对拍，不表示全字段全模板已验证；例：JapanPowerPlant |
| 未做 | `Behaviors/ActivateModuleSpecialPower` | 4 (5) | a1 a2 a4 a6 a7 | 仅在SpecialPowerNugget处理器中识别并拒绝，未实现模块技能执行；例：AlliedAntiStructureVehicle, JapanAntiVehicleVehicleTech1 |
| 未做 | `Behaviors/RadarBehavior` | 4 (5) | a4 | 模拟器代码里没有这个名字；例：AlliedRadarDish, PlayerSpellBook |
| 推断 | `Behaviors/SpecialAbilityUpdate` | 4 (5) | a1 a4 a6 a7 | 模拟器代码里有这个名字；例：JapanAntiInfantryInfantry, JapanAntiVehicleVehicleTech1 |
| 推断 | `Behaviors/TechUpgradeReceiver` | 4 (5) | a2 a4 a5 a7 a8 | 模拟器代码里有这个名字；例：AlliedAirfield, AlliedBarracks |
| 未做 | `Behaviors/HealCrateCollide` | 4 (4) |  | 模拟器代码里没有这个名字；例：SS_SecretFile1, SS_SecretFile2 |
| 未做 | `Behaviors/ParkingPlaceBehavior` | 4 (4) | a4 a5 a7 a8 | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedAntiStructureShip |
| 已对拍 | `Behaviors/SpecialDisguiseUpdate` | 4 (4) | a1 a4 a6 a7 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_spndisguise.py；例：AlliedAntiVehicleVehicleTech3, AlliedInfiltrationInfantry |
| 推断 | `Behaviors/AttachUpdate` | 3 (24) | a1 a2 a4 a5 a6 a7 a9 | 部分：engine_attach a验证瞬移/跟随/父子状态；engine_attach_parent a验证简单模块脚本杀父后子活/清理链接，NO_COLLISIONS读数差异为严格xfail；原版模块死亡前无稳定链接，不推广死亡规则；子死/直接删除/维修/吸血/解除/自主扫描仍gap；例：ChronoTargetMarker, AlliedAirfieldRepairDrone |
| 未做 | `Behaviors/StealthDetectorUpdate` | 3 (8) | a2 a6 | 已核（11-08）：模拟器没有这个效果（没有反隐）；例：AlliedScoutInfantry, A08_Dog1 |
| 未做 | `Behaviors/SlaughterHordeContain` | 3 (6) | a5 a7 a8 | 模拟器代码里没有这个名字；**待核**：台上量过（checks/engine_aipullback.py），可能用别的名字实现了；例：AlliedAntiStructureShip, S08_AlliedAntiStructureShip |
| 未做 | `AI/AnimalAIUpdate` | 3 (4) |  | 模拟器代码里没有这个名字；例：BaseCivilian, CivilianFemale1 |
| 未做 | `Behaviors/AssistedPlacementBehavior` | 3 (4) | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedRefinery, AlliedRefinery_NoHarvester |
| 未做 | `Behaviors/LoseHealthUpdate` | 3 (4) | 全部 | 模拟器代码里没有这个名字；例：SovietAntiStructureShip, SovietBomberAircraft |
| 未做 | `Behaviors/MovementSpecialPower` | 3 (4) | a1 a4 a6 a7 | 模拟器代码里没有这个名字；例：JapanAntiStructureShip, JapanAntiVehicleVehicleTech3 |
| 未做 | `Behaviors/SecondaryObjectListenerModule` | 3 (4) | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedBaseDefense, AlliedAntiAirVehicleTech1 |
| 未做 | `Behaviors/StructurePlacementBehavior` | 3 (4) | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedRefinery, AlliedRefinery_NoHarvester |
| 未做 | `Behaviors/HitReactionBehavior` | 3 (3) | a1 a2 a3 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedAntiInfantryInfantry, JapanEmperor |
| 推断 | `Behaviors/LiftObjectUpdate` | 3 (3) | a1 a2 a4 a6 a7 | 部分：显式TimeIncrement/MaxTimeLifted的开火者举升表计时接口；tests/test_lift_nugget.py回放engine_lift a状态计数，逐帧计时来自模块证据、未上台逐帧量表；垂直运动/死亡/飞机/落地武器/清位仍gap，落地清位INFERRED，不登记整模块已对拍；例：AlliedBaseDefense, AlliedAntiAirVehicleTech1 |
| 未做 | `Behaviors/ReturnToProducerSpecialPower` | 3 (3) | a1 a2 a3 a4 a5 a6 a7 a8 | 模拟器代码里没有这个名字；例：AlliedAntiGroundAircraft, AlliedFighterAircraft |
| 未做 | `Behaviors/SubStructureBehavior` | 2 (11) |  | 模拟器代码里没有这个名字；例：AlliedConstructionYardRepairBay, AlliedCrane |
| 未做 | `Behaviors/AttributeCrateCollide` | 2 (3) |  | 模拟器代码里没有这个名字；例：SS_SecretFile1, SS_SecretFile2 |
| 未做 | `Behaviors/ConvergingLaserState` | 2 (3) | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiStructureVehicle, SovietAntiVehicleVehicleTech1 |
| 未做 | `Behaviors/AimWeapon` | 2 (2) | a1 a4 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedAntiVehicleInfantry, SovietAntiVehicleInfantry |
| 未做 | `Behaviors/GateOpenAndCloseBehavior` | 2 (2) |  | 模拟器代码里没有这个名字；例：RM_AlliedBlastDoor, SS_Door |
| 已对拍 | `Behaviors/InvisibilityBroadcastUpdate` | 2 (2) | a1 a4 a6 a7 | tests/test_simbench_c.py::test_invisibility_broadcast_the_aura_holds_its_guardian_at_full_health_and_the_control_dies；例：AlliedAntiVehicleVehicleTech3, A08_SpecialMirageTank |
| 未做 | `Behaviors/NotifyWhenAttackingBehavior` | 2 (2) | a1 a2 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedBaseDefenseAdvanced, SovietBaseDefenseAdvanced |
| 未做 | `Behaviors/PowerUpgrade` | 2 (2) | a5 | 模拟器代码里没有这个名字；例：SovietPowerPlantAdvanced, SovietPowerPlant |
| 未做 | `Behaviors/PrematureDischargeSpecialPower` | 2 (2) | a4 | 模拟器代码里没有这个名字；例：JapanBaseDefenseAdvanced, JapanAntiStructureVehicle |
| 未做 | `Behaviors/RecallUnitsSpecialPower` | 2 (2) | a4 a7 | 模拟器代码里没有这个名字；例：AlliedAirfield, SovietAirfield |
| 未做 | `Behaviors/SpiderHoleUpdate` | 2 (2) | a4 | 模拟器代码里没有这个名字；例：JapanAntiVehicleInfantry, JapanAntiVehicleInfantry_Ambush |
| 已对拍 | `Behaviors/TechUpgrade` | 2 (2) | a1 a4 a5 a7 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_tech.py；例：AlliedConstructionYard, AlliedOutpost |
| 已对拍 | `Behaviors/LifetimeUpdate` | 1 (855) | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_crush.py；例：AlliedAirField_Collapse, AlliedAntiAirShip_Collapse |
| 推断 | `Behaviors/FireWeaponUpdate` | 1 (21) | a1 a2 a4 a5 a6 a7 | 部分：simunits.ocl_round 把召出物的 FireWeaponNugget + LifetimeUpdate 折成伤害，不模拟召出物本身；例：AlliedAntiStructureVehicleCannonEffect, AlliedAntiStructureVehicleCannonEffect_Vet |
| 推断 | `Behaviors/EngineerContain` | 1 (11) | a4 a5 a8 | 总控11-11授权工程师组收尾、不再上台；已测通用三国63用量及三国ALLIES6用量分别登记；gap：日本单人ALLIES型TH_TombBuilding02为1用量/1模板，筛选与维修未对拍；间接可达桥头堡为0用量/10模板，桥修复未对拍；本行共1用量/11模板。ReplaceWith和ObjectStatusToSet无原版显式声明；精确进入帧仍INFERRED，不登记整模块已对拍（tests/test_simengineer.py、tests/test_inventory_contain.py、tests/test_inventory_engineer.py）；例：TH_TombBuilding02 |
| 已对拍 | `Behaviors/OreNodeBehavior` | 1 (8) | a1 a2 a4 a5 a6 a7 a9 | tests/test_simbench.py::test_mining_a_second_miner_on_one_node_adds_nothing；例：BaseOreNode, OreNode |
| 未做 | `Behaviors/AssistedPlacementInfoBehavior` | 1 (7) | a1 a2 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：OreNode, OreNode2a |
| 已对拍 | `Behaviors/OreMinerBehavior` | 1 (7) | a1 a2 a4 a5 a6 a7 | tests/test_simbench.py::test_mining_pays_8_a_frame_and_a_trip_takes_269；例：AlliedMiner, AlliedMiner_Naval |
| 未做 | `Behaviors/FireWeaponCollide` | 1 (4) | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：SovietAntiVehicleInfantry, JapanAntiVehicleShipTorpedoSpreadProjectile |
| 未做 | `Behaviors/StrafeAreaUpdate` | 1 (3) |  | 模拟器代码里没有这个名字；例：AlliedSatelliteSweepShroudRevealer, JapanFinalSquadronAircraft |
| 不涉及 | `Behaviors/AudioLoopUpgrade` | 1 (2) | a1 a2 a3 a4 a5 a6 a7 | 纯表现（名字规则）；例：SovietAntiVehicleVehicleTech1, Tutorial_SovietTech1Tank |
| 推断 | `Behaviors/GarrisonContain` | 1 (2) | a6 a7 | simgarrison 同一套规则（不可争夺）；没单独上台对拍；例：AlliedBaseDefense, SovietBunker |
| 未做 | `Behaviors/MoneyCrateCollide` | 1 (2) |  | 模拟器代码里没有这个名字；例：MoneyCrate, MoneyCrateMP |
| 未做 | `Behaviors/MonitorConditionUpdate` | 1 (2) | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：JapanMiner, JapanMiner_Naval |
| 未做 | `Behaviors/OCLMonitorUpdate` | 1 (2) | a1 a2 a4 a6 a7 | 模拟器代码里没有这个名字；**待核**：台上量过（checks/engine_spnbomb.py），可能用别的名字实现了；例：SovietCommandoTech1, Soviet_BombingRun |
| 未做 | `Behaviors/ObjectCreationUpgrade` | 1 (2) | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech1, Tutorial_SovietTech1Tank |
| 未做 | `Behaviors/SlaveWatcherBehavior` | 1 (2) | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech1, Tutorial_SovietTech1Tank |
| 未做 | `Behaviors/StoreObjectsSpecialPower` | 1 (2) | a7 a8 | 已核（11-08）：模拟器没有这个效果（没有存放单位）；例：AlliedSuperWeapon, PlayerSpellBook |
| 未做 | `Behaviors/SwitchLocomotorUpdate` | 1 (2) | 全部 | 模拟器代码里没有这个名字；例：SovietBomberAircraft, SovietBomberAircraft_Special |
| 未做 | `Behaviors/TeleportStoredObjectsSpecialPower` | 1 (2) | a7 a8 | 已核（11-08）：模拟器没有这个效果（没有传送存放的单位）；例：AlliedSuperWeapon, PlayerSpellBook |
| 未做 | `Behaviors/TeleportStoredObjectsUpdate` | 1 (2) | a7 a8 | 已核（11-08）：模拟器没有这个效果（UNIT_TELEPORT_TO_WAYPOINT 另算）；例：AlliedSuperWeapon, PlayerSpellBook |
| 未做 | `Behaviors/VeterancyCrateCollide` | 1 (2) |  | 模拟器代码里没有这个名字；例：VeterancyCrate, VeterancyCrateMP |
| 未做 | `Behaviors/ActivateSpecialPowerOnCreate` | 1 (1) |  | 模拟器代码里没有这个名字；例：JapanAntiVehicleInfantry_Ambush |
| 已对拍 | `Behaviors/AssembleStructureSpecialAbilityUpdate` | 1 (1) | a4 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_skill.py；例：SovietEngineer |
| 未做 | `Behaviors/ChargeWeaponUpdate` | 1 (1) | a4 | 模拟器代码里没有这个名字；例：JapanBaseDefenseAdvanced |
| 未做 | `Behaviors/CircularDamageUpdate` | 1 (1) |  | 模拟器代码里没有这个名字；例：SovietAntiNavyShipTech1 |
| 未做 | `Behaviors/DieOnProducerDeathUpdate` | 1 (1) |  | 模拟器代码里没有这个名字；例：AlliedAttackDrone |
| 未做 | `Behaviors/DominateEnemySpecialPower` | 1 (1) |  | 模拟器代码里没有这个名字；例：AlliedInfiltrationInfantry |
| 未做 | `Behaviors/GrapplingHookUpdate` | 1 (1) | a1 a3 a4 a6 a7 a9 | 仅engine_grapple a最小消费者诊断；模块派发/拉拽/释放未解释，未实现，不作为已对拍证据；例：SovietAntiVehicleVehicleTech3 |
| 已对拍 | `Behaviors/LinearDamageUpdate` | 1 (1) | a1 a2 a4 a6 a7 | tests/test_simsweep.py::test_sweep_the_line_walks_out_and_a_stop_does_not_cut_it_at_the_bench_frames；例：AlliedAntiNavalScout |
| 未做 | `Behaviors/MagneticEffectUpdate` | 1 (1) | a1 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiNavyShipTech1 |
| 未做 | `Behaviors/ReconstituteStateSpecialAbility` | 1 (1) | a1 a2 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedCommandoTech1 |
| 未做 | `Behaviors/ShieldSphereUpdate` | 1 (1) | a2 a6 | 模拟器代码里没有这个名字；例：AlliedAntiStructureVehicle |
| 未做 | `Behaviors/StoreCurrentStateUpdate` | 1 (1) | a1 a2 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedCommandoTech1 |
| 未做 | `Behaviors/SweepingLaserState` | 1 (1) | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：SovietScoutVehicle |
| 不涉及 | `Behaviors/TimedOpacityUpdate` | 1 (1) |  | 纯表现（名字规则）；例：JapanInfiltrationInfantry |
| 不涉及 | `ClientBehaviors/ModelConditionEvaEventSelectorClientBehavior` | 1 (1) |  | 纯表现（ClientBehaviors）；例：AlliedInfiltrationInfantry |
| 不涉及 | `ClientBehaviors/UpgradeSoundSelectorClientBehavior` | 1 (1) | a1 a4 a7 | 纯表现（ClientBehaviors）；例：AlliedAntiAirVehicleTech1 |
| 不涉及 | `Draws/TankDraw` | 1 (1) |  | 纯表现（Draws）；例：SovietAntiVehicleVehicleTech2 |
| 未做 | `Body/ManagedImmortalBody` | 0 (44) |  | 模拟器代码里没有这个名字；例：BaseIndestructableBridgeSegment, BaseBridgeEnd |
| 未做 | `Body/ManagedActiveBody` | 0 (31) |  | 模拟器代码里没有这个名字；例：BaseBridgeSegment, AM_Bridge_01_Center |
| 未做 | `Behaviors/ProjectileUpdate` | 0 (18) | 全部 | 已核（11-08）：模拟器没有这个效果（开火按每秒伤害直接扣血，没有弹体飞行时间）；例：AlliedAntiVehicleVehicleTech1Projectile, AlliedBomberAircraftBombProjectile |
| 未做 | `Behaviors/LaserScatterUpdate` | 0 (10) |  | 模拟器代码里没有这个名字；例：AlliedAntiVehicleVehicleTech3CannonNodeBase, AlliedAntiVehicleVehicleTech3CannonNodeEnd |
| 未做 | `Behaviors/SlavedUpdate` | 0 (9) |  | 已核（11-08）：模拟器没有这个效果（没有随从跟随）；例：AlliedAirfieldRepairDrone, AlliedAttackDrone_Leeched |
| 未做 | `Behaviors/BombardAreaUpdate` | 0 (8) |  | 模拟器代码里没有这个名字；例：BaseBalloonBombEffect, BalloonBombEffectLvl1 |
| 未做 | `Behaviors/WeaponScatterEffectUpdate` | 0 (8) |  | 模拟器代码里没有这个名字；例：AlliedAntiVehicleVehicleTech3CannonNodeEnd, AlliedAntiVehicleVehicleTech3CannonNodeRegular |
| 未做 | `Behaviors/DestroyObjectsUpdate` | 0 (7) |  | 模拟器代码里没有这个名字；例：AlliedAntiStructureVehicleCannonEffect, AlliedAntiStructureVehicleCannonEffect_Vet |
| 未做 | `Body/HighlanderBody` | 0 (5) |  | 模拟器代码里没有这个名字；例：BaseMountRushmoreHead, MR_LaserMtRushmore_Jefferson_Ready |
| 未做 | `Behaviors/StrafeAreaTargetChooser` | 0 (4) |  | 模拟器代码里没有这个名字；例：JapanFinalSquadronAircraft, JapanFinalSquadronSeed_L1 |
| 未做 | `Behaviors/InvalidTargetsDeathUpdate` | 0 (3) |  | 模拟器代码里没有这个名字；例：AlliedProtonColliderBeacon, SovietBombingRunBeacon |
| 未做 | `Behaviors/ParabolicCurveUpdate` | 0 (3) |  | 模拟器代码里没有这个名字；例：AlliedSupersonicBomber, SovietSupportBomber |
| 未做 | `Behaviors/SelectiveVisibilityBehavior` | 0 (3) |  | 模拟器代码里没有这个名字；例：ChronoTargetMarker, MultiplayerBeacon |
| 未做 | `Behaviors/SuckUpObjectsUpdate` | 0 (3) |  | 模拟器代码里没有这个名字；例：MagneticSatelliteEffectLvl1, MagneticSatelliteEffectLvl2 |
| 未做 | `Behaviors/CrateCollide` | 0 (2) |  | 模拟器代码里没有这个名字；例：BombCrate, ShroudCrate |
| 未做 | `Behaviors/SetLocomotorSpeedUpdate` | 0 (2) |  | 模拟器代码里没有这个名字；例：BaseCivilianAuto, CUAuto01 |
| 未做 | `Behaviors/ShipSlowDeath` | 0 (2) |  | 模拟器代码里没有这个名字；例：SovietBomberAircraft_Dying, SovietBomberAircraft_Special_Dying |
| 未做 | `AI/HordeAIUpdate` | 0 (1) |  | 模拟器代码里没有这个名字；例：YOURSQUAD |
| 未做 | `Behaviors/CaptureAndGiveUpgradeBehavior` | 0 (1) |  | 模拟器代码里没有这个名字；例：VeterancyTechStructure |
| 未做 | `Behaviors/DistributeEnergyToAlliesBehavior` | 0 (1) |  | 模拟器代码里没有这个名字；例：NeutralPowerPlant |
| 未做 | `Behaviors/EncloseBehavior` | 0 (1) |  | 模拟器代码里没有这个名字；例：NanoSwarmHiveEffect |
| 未做 | `Behaviors/EnergyDisablingBehavior` | 0 (1) |  | 模拟器代码里没有这个名字；例：EnergyDisabler |
| 未做 | `Behaviors/GatherEjectUpdate` | 0 (1) |  | 模拟器代码里没有这个名字；例：VacuumBombEffect |
| 未做 | `Behaviors/GiveProductionBonusSpecialPower` | 0 (1) |  | 模拟器代码里没有这个名字；例：PlayerSpellBook |
| 未做 | `Behaviors/HeightDieUpdate` | 0 (1) | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：JapanBalloonBomb |
| 未做 | `Behaviors/HordeContain` | 0 (1) |  | 模拟器代码里没有这个名字；例：YOURSQUAD |
| 未做 | `Behaviors/LineSegmentDamageUpdate` | 0 (1) |  | 模拟器代码里没有这个名字；例：IrradiatedTargetDamageDealer |
| 未做 | `Behaviors/MoneyGainAttachUpdate` | 0 (1) |  | 模拟器代码里没有这个名字；例：SovietProductionKickbackHelper |
| 未做 | `Behaviors/PlayerPowerManager` | 0 (1) |  | 模拟器代码里没有这个名字；例：PlayerSpellBook |
| 未做 | `Behaviors/PlayerUpgradeSpecialPower` | 0 (1) |  | 模拟器代码里没有这个名字；例：PlayerSpellBook |
| 未做 | `Behaviors/RandomCrateCollide` | 0 (1) |  | 模拟器代码里没有这个名字；例：RandomCrate |
| 未做 | `Behaviors/RenderStoredThingTemplate` | 0 (1) |  | 模拟器代码里没有这个名字；例：OrbitalRefuseRandomDebris |
| 未做 | `Behaviors/SalvageCrateCollide` | 0 (1) |  | 模拟器代码里没有这个名字；例：SalvageCrate |
| 未做 | `Behaviors/SpawnCrateUpdate` | 0 (1) |  | 模拟器代码里没有这个名字；例：GenericCrateSpawner |
| 未做 | `Behaviors/SqueezeFlingUpdate` | 0 (1) |  | 模拟器代码里没有这个名字；例：MagneticSingularityEffect |
| 未做 | `Behaviors/StoreTemplateIDBehavior` | 0 (1) |  | 模拟器代码里没有这个名字；例：PlayerSpellBook |
| 未做 | `Behaviors/UnitCrateCollide` | 0 (1) |  | 模拟器代码里没有这个名字；例：UnitCrate |
| 未做 | `Behaviors/UnitVisionBehavior` | 0 (1) |  | 模拟器代码里没有这个名字；例：UnitVisionObserver |

## 武器效果

| 状态 | 名字 | 用量 | 9 关用到 | 说明 |
|---|---|---|---|---|
| 已对拍 | `DamageNugget` | 183 | 全部 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_clip.py；例：BaseExplodingPropVehicleWeapon, MountRushmoreHeadEyeWeapon |
| 已对拍 | `ProjectileNugget` | 88 | 全部 | tests/test_simbench_c.py::test_projectile_nugget_flight_uses_retail_shell_speed_and_resolved_warhead；例：BB_EuropeCoastalGunWeapon, KremlinArtilleryDomeMissle |
| 已对拍 | `SuppressionNugget` | 64 | 全部 | tests/test_simbench_c.py::test_suppression_samples_entry_refresh_and_expiry_at_the_four_probe_readings；例：BB_EuropeCoastalGunWeapon, KremlinArtilleryDomeMissle |
| 已对拍 | `InformTargetNugget:默认系数目标通知` | 47 | 全部 | tests/test_inform_ai.py::test_inform_incoming_table_drives_miner_armor_from_engine_inform_probe；仅默认Min=.85/Max=1.15的目标通知→来弹表/矿车预计伤害开甲；engine_inform_probe a/off录入302、hit377、exp404、删除389，347帧入窗。半径/历史/海啸/忍者及完整AI调度不在本登记范围，完整脚本仍xfail；例：BB_EuropeCoastalGunWeapon, AlliedPrecisionBomb |
| 不涉及 | `ActivateLaserNugget` | 27 | 全部 | 纯表现：Lifetime/LaserId/HitGroundFX/OverShootDistance驱动LaserState/LaserDraw；engine_laser pair实测2/90/2/90，无附加伤害或首发延迟，test_simbench_c重放；例：MountRushmoreHeadEyeWeapon, JapanAntiVehicleInfantryTech3LockDownGun |
| 已对拍 | `WeaponOCLNugget` | 26 | 全部 | tests/test_simbench_c.py::test_weapon_ocl_lifetime_damage_reads_the_fire_delay_before_counting_updates；例：MountRushmoreHeadEyeWeapon, AlliedPrecisionBombWarhead |
| 已对拍 | `InformTargetNugget:Max1.6目标通知` | 22 | 全部 | tests/test_inform_ai.py::test_inform_max_launch_matches_engine_inform_max_observed_deadline；仅Min=.85/Max=1.6目标通知→来弹表；engine_inform_max a单变量对照录入302、hit377不变、exp444（默认404）、受伤389删除，矿车提前开甲。自然过期清理边界/半径/历史/海啸/忍者/完整AI调度未对拍，完整脚本仍xfail；例：AlliedBaseDefenseRockets, AlliedBaseDefenseRockets_Aircraft |
| 已对拍 | `AttributeModifierNugget` | 20 | 全部 | tests/test_simbench_c.py::test_weaponfx_predictions_and_finite_bursts；例：NanoHiveSwarmEffectTrigger, JapanCommandoSoftLanding |
| 已对拍 | `MetaImpactNugget:普通无延迟显式Z` | 13 | a1 a2 a4 a5 a6 a7 | tests/test_meta_impact.py::test_meta_impact_collision_event_replays_engine_knock_probe_neighbour_five_frames；仅普通弹头碰撞事件→默认Physics轨迹；engine_knock_probe land/late邻人5帧落(2380,3740)、目标99%/邻人100%。到达帧为台上输入，非完整V4曲线弹回放；直击方向/落点网格/选人仍INFERRED；例：KremlinArtilleryDomeMissleWarhead, AlliedTimeBomb_Level1 |
| 未做 | `MetaImpactNugget` | 12 | a1 a2 a3 a4 a5 a6 a7 a9 | 剩余复杂写法：延迟、筛选、Arc、Invert等；普通延迟仅解析payload及隔离到期队列，engine_knock_delay碰撞输入174/173→到期204/192；Physics观察/落地相位未解，不晋升整项。ShockWaveSpeed/Cyclonic本轮原版用量为0也未建模。非默认Physics、坡地及V4曲线弹到达仍gap；例：JapanCommandoTech1PsyonicBlast, JapanMechaKingKatana |
| 已对拍 | `MetaImpactNugget:省略Z默认值` | 11 | 全部 | tests/test_meta_impact.py::test_meta_impact_omitted_z_replays_engine_knock_z_tall_neighbour；仅普通无延迟弹头省略ShockWaveZMult→SDK默认1及默认Physics轨迹；engine_knock_z a高度93邻人14帧落(2420,3740)、目标99%/邻人100%。碰撞时刻/爆心为台上输入；直击噪声方向/网格/选人仍INFERRED，完整曲线弹/坡地/筛选未对拍；例：JapanCommandoTech1AirplaneCrashWeapon, AlliedBomberAircraftBombWarhead |
| 已对拍 | `ParalyzeNugget` | 11 | a1 a2 a4 a5 a6 a7 | tests/test_simbench_c.py::test_weapon_first_hit_is_observed_one_frame_after_the_order_script；例：JapanAntiVehicleInfantryTech3LockDownGun, AlliedAntiStructureShipEMPCruiseMissleWarhead |
| 不涉及 | `TintObjectsNugget` | 9 | 全部 | 纯表现：Color及Pre/Sustained/PostColorTime、Frequency/Amplitude仅控制染色动画；engine_tint pair实测2/90/2/90，独立DamageNugget解释全部伤害，test_simbench_c重放；不声称像素已验证；例：SovietCommandoCallBombingRun, AlliedCommandoAttachWeapon |
| 推断 | `ActivateLiftObjectNugget` | 6 | a1 a2 a4 a6 a7 | 部分：按模块证据实现开火者举升表，trunc(TimeIncrement×15)逐发累加、续期封顶MaxTimeLifted、逐帧递减释放；Lifetime不参与，释放不清LIFTED；tests/test_lift_nugget.py按名回放engine_lift a旧读数一致，landing因落地清位未实现strict xfail；落地清位INFERRED，垂直运动/死亡/飞机/弹体/复杂筛选仍gap，不登记整项已对拍；例：JapanCommandoTech1PsyonicCrush, JapanCommandoTech1AirborneKiller |
| 已对拍 | `LineDamageNugget` | 6 | a1 a2 a3 a4 a5 a6 a7 | tests/test_simbench_c.py::test_weaponfx_predictions_and_finite_bursts；例：SovietCommandoSniperRifle, AAAVT1_SovietCommandoSniperRifle |
| 推断 | `SpecialPowerNugget` | 6 | 全部 | 部分：engine_spn a实测自身ARMOR派发、缺模块/类型过滤；engine_spng a / engine_spngp a实测单个OBJECT/PLAYER升级门槛读取施法者/其玩家；engine_spnret a原版守护者普通/高科技保留与去除此Nugget均74/69%血，增伤由AttributeModifierNugget提供，无活动消费者的PaintTarget模块无附加效果；tests/test_special_power_nugget.py回放；engine_spnscr a原版干扰保留/去除SPN首伤均延后但最终同80%，到期无条件清除脚本同名状态位接口已覆盖；原版筛选最小派发接口已覆盖（类别/气球模板/铁幕排除），攻击订单恢复未解释，未登记完整消费者；engine_spndisguise a原版/删SPN/删变装模块/脚本正对照1111/1110/1110/1111已按名回放，接通直接命中DISGUISED位，身份/外观/索敌/换目标/取消仍gap；仅直接单发，OCL/其他模块、未知类型/多重升级未接通，不登记整项已对拍；例：SovietCommandoCallBombingRun, AlliedAntiVehicleVehicleTech1TargetPainter |
| 未做 | `FireOnObjectsNugget` | 5 |  | 未实现：子武器派发条件与空间锚点尚未解释；失败诊断不作为已对拍依据；例：PlayerPowerJapanEmperorsResolveWeapon_L1, PlayerPowerJapanEmperorsResolveWeapon_L2 |
| 已对拍 | `SecondaryDamageNugget` | 5 | a7 | tests/test_simbench_c.py::test_secondary_damage_delivers_one_amount_at_hit_without_damaging_health；例：MountRushmoreHeadEyeWeapon, AlliedCryoSatelliteLvl1 |
| 推断 | `AttachNugget` | 4 | a1 a2 a4 a5 a6 a7 a9 | 部分：engine_attach a实测直接单发、父子状态、随父移动及目标状态/类型拒绝；仅零半径简单模块，原版复杂筛选/维修/吸血/解除/弹体未接通，不登记整项已对拍；例：AlliedCommandoAttachWeapon, SovietAntiVehicleInfantryMagneticBombAttachWeapon |
| 已对拍 | `StripMaxHealthPercentNugget` | 3 | a1 a2 a4 a6 a7 | tests/test_simbench_c.py::test_strip_max_health_percent_uses_maximum_at_full_and_half_health；例：JapanCommandoTech1PsyonicCrush, AAAVT1_JapanCommandoTech1PsyonicCrush |
| 已对拍 | `ActivateLinearDamageNugget` | 2 | a1 a2 a4 a6 a7 | tests/test_simsweep.py::test_sweep_a_killed_shooters_line_stops_with_it_and_the_second_ones_rows_are_hit；例：AlliedAntiNavalScoutSonar, AlliedAntiNavalScoutSonarForBridges |
| 已对拍 | `DamageContainedNugget` | 2 | a1 a2 a3 a5 | tests/test_simbench_c.py::test_damage_contained_limits_eligible_passengers_without_damaging_the_others；例：SovietAntiInfantryInfantryMolotovCocktailWarhead, Weapon_DesolatorBombFieldUpdate |
| 已对拍 | `LeechPercentMaxHealthDamageNugget` | 2 | a1 a3 a4 a6 a7 a9 | tests/test_simbench_c.py::test_leech_percent_uses_victim_maximum_not_current_health_or_caster_maximum；例：SovietCrushWeapon, SovietHarpoonCrushWeapon |
| 未做 | `ReportWeaponFiredStatNugget` | 2 |  | 模拟器代码里没有这个名字；例：SovietVacuumBomb, ParticleCannonWeapon |
| 未做 | `ActivateCircularDamageNugget` | 1 |  | 模拟器代码里没有这个名字；例：SovietAntiNavyShipTech1TeslaNova |
| 已对拍 | `DOTNugget` | 1 |  | tests/test_simbench_c.py::test_dot_counts_interval_ticks_for_two_durations_and_observes_first_damage_frame；例：PlayerPowerIrradiateTargetWeapon |
| 未做 | `GrapplingHookNugget` | 1 | a1 a3 a4 a6 a7 a9 | engine_grapple a最小消费者诊断；GrapplingHookUpdate派发/拉拽/释放未解释，显式报告gap；tests/test_grapple_nugget.py守卫直接命中/继承/弹头及原版缓存，不登记已对拍；例：SovietAntiVehicleVehicleTech3Harpoon |
| 已对拍 | `LeechHealthDamageNugget` | 1 | a1 a2 a3 a4 a5 a6 a7 | tests/test_simbench_c.py::test_leech_health_heals_from_damage_and_respects_the_heal_fraction；例：SovietAntiVehicleVehicleTech1LeechBeamWeapon |

## AI

| 状态 | 名字 | 用量 | 9 关用到 | 说明 |
|---|---|---|---|---|
| 已对拍 | `开局/Order.Build` | 635 | a4 a5 a7 | docs/engine/aiopen.md#读数（aiopen f1～f3：造的顺序和 AlliedStandard 单子一样） |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType` | 392 | a4 a5 a7 | docs/engine/aitactics.md#读数（ClosestStructure / SafestToGroundStructure 是 EnemyStructure，FriendlyLandStructure 是 FriendlyStructure，都上台） |
| 已对拍 | `造兵/BuildEntry.Heuristic` | 380 | a4 a5 a7 | E78 engine_aiskirm z：BEST_UNIT_EXPECTED 两组台上 PASS；[s150,s160) 征召兵组维和5→6、标枪0，锤子组标枪7→8→9、维和0；tests/test_simai_bench_e.py::test_best_unit_expected_infantry_choice 两组按来源断言通过（建造状态造的另一种=0；锤子组多的那个维和是单位生成器均匀抽签，台上 t 也抽2次：狗 s23、工程师 s144）；B 第 149 轮模拟器侧排除"一帧多单""队列非空仍下单"；FEWEST_UNIT 见 aisknew2 y、RANDOM_UNIT 见 aiskrand s；抽签结果属运气不对拍，"每次评估无条件掷一次随机数"没建模；见 work/re/e_aiheur_e78.md、work/re/handoff-b.md 第 149 节 |
| 已对拍 | `造兵/BuildEntry.Build` | 364 | a4 a5 a7 | 台上量过（engine_aiskirm y aisknew / aisknew2：没列进任何建造状态的我们的兵不造、列成 FEWEST_UNIT 占兵营约一半；z aiskvinf / aiskvveh：BEST_UNIT_EXPECTED 兵营只造克制兵），测试对拍 tests/test_simai_bench_b.py（B 第 126–131 轮）；RANDOM_UNIT（PercentLow/High）、MinTime 没单独量 |
| 已对拍 | `组队招人/ObjectFilter.ExcludeThing` | 288 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 已对拍 | `战略状态/TargetHeuristic.TargetHeuristic` | 287 | a4 a5 a7 | docs/engine/aitactics.md#读数（aitargetnear / aitargetsafe：按状态写的目标启发挑楼） |
| 已对拍 | `战略状态/StrategicState.Difficulty` | 268 | a4 a5 a7 | docs/engine/aistate.md#按难度挂的状态（aidiff / aidiffx：普通 = MEDIUM，没挂 MEDIUM 的状态不跑） |
| 已对拍 | `战略状态/StrategicState.State` | 268 | a4 a5 a7 | docs/engine/aistate.md#读数（人格只留台上写的状态，AI 只跑这些：aistateconst / aistateslash 等） |
| 已对拍 | `目标/AITargetingHeuristic.Name` | 241 |  | docs/engine/ainamed.md#给关卡线的结论（ainmfar 点名物件不管远近、ainmwp 走到路点守着、ainmnone 名字查不到不派队，全 PASS） |
| 不涉及 | `表现/FeedbackEntry.FeedbackKey` | 238 |  | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/FeedbackEntry.FeedbackTo` | 238 |  | 纯表现（语音、视频、画面） |
| 已对拍 | `开局/Order.Time` | 237 | a4 a5 a7 | docs/engine/aiopen.md#开局里的 Time 从什么时候算（aiotime：从唤醒起的绝对时刻） |
| 已对拍 | `战术/Tactic.Tactic` | 184 | a4 a5 a7 | docs/engine/aitactics.md#读数（SimpleAttack / DefenseAvoidanceAttack / FlankAttack / StaticDefense 上台） |
| 已对拍 | `组队招人/TeamTemplate.AlwaysRecruit` | 182 | a4 a5 a7 | 台上量过（engine_aiteamfilter aiar0～3，第 90 轮）、测试对拍 tests/test_simai_bench_b.py：关着新造的车留家、开着出门的队把它招走、满员不招、不预放时第一辆自己组队（模拟器每次晚 3～4 s）；模拟器多造第 3、4 辆是造兵的缺口（strict xfail），不是这个开关 |
| 已对拍 | `组队招人/TeamTemplate.MicroManager` | 182 | a4 a5 a7 | 台上量过（engine_airetreat：airet / airet0 只差 MicroManager 指名的那份数据里的 RetreatPowerAdvantage，一个撤一个不撤；aipas1 / aipas0 只差 EngagePassiveTargets）、测试对拍 tests/test_simai.py——队伍跑的是 MicroManager 指名的那份微操数据；指名不存在的 id 会怎样没量 |
| 已对拍 | `组队招人/TeamTemplate.MinUnits` | 182 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `组队招人/TeamTemplate.Priority` | 182 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | `战略状态/TargetHeuristic.Priority` | 170 | a4 a5 a7 | docs/engine/aitactics.md#目标挑哪个（aitpphi / aitpplo：同一状态两条目标启发，Priority 高的先试，两向都上台） |
| 已对拍 | `组队招人/TeamTemplate.ExcludeKindOf` | 170 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 已对拍 | `组队招人/TeamTemplate.IncludeKindOf` | 170 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 已对拍 | `组队招人/TeamTemplate.MaxUnits` | 170 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 不涉及 | `表现/FeedbackEntry.Video` | 168 |  | 纯表现（语音、视频、画面） |
| 已对拍 | `战略状态/AIStrategicStateDefinition.MaxTargets` | 156 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `组队招人/ObjectFilter.Rule` | 155 | a4 a5 a7 | docs/engine/aistate.md#队伍招谁（aitfany / aitfnone / aitfall：ANY、NONE + 名单只要名单，ALL + 排除名单） |
| 已对拍 | `目标/AITargetingHeuristic.RequireUniqueTarget` | 154 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | `战术/Tactic.EndBehavior` | 152 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | `组队招人/ObjectFilter.IncludeThing` | 152 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py:y |
| 已对拍 | `组队招人/TeamTemplate.RegisteredObjectSet` | 148 | a4 a5 a7 | docs/engine/aistate.md#移动方式和对象集（第 81 轮） |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=NamedObject` | 145 |  | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_ainamed.py |
| 已对拍 | `组队招人/TeamTemplate.AllowedLocomotorTypes` | 145 | a4 a5 a7 | docs/engine/aistate.md#移动方式和对象集（第 81 轮） |
| 已对拍 | `目标/AITargetingHeuristic.VitalKindOf` | 129 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 已对拍 | `组队招人/TeamTemplate.Priority=STANDARD` | 126 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | `启发条件/ConstantHeuristic` | 119 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipoweradv.py |
| 已对拍 | `人格/PowerChoice.PlayerPower` | 117 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipower.py |
| 已对拍 | `人格/PowerChoice.Weight` | 117 | a4 a5 a7 | docs/engine/aiopen.md#买协议（aipwrb 权重 0 的不买） |
| 已对拍 | `战术/Tactic.EndBehavior=DISBAND` | 105 | a4 a5 a7 | docs/engine/aitactics.md#目标没了以后（EndBehavior，2026-11-09 各一次）（aiendd：目标没了队伍解散、状态重派去兵营，和模型对上） |
| 已对拍 | `目标/AITargetingHeuristic.ForbiddenKindOf` | 102 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 已对拍 | `微操/AIMicroManagerData.RetreatPowerAdvantage` | 94 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_airetreat.py |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=Waypoint` | 94 |  | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_ainamed.py |
| 已对拍 | `人格/UnitModifier.DefensiveModifier` | 92 | a4 a5 a7 | 台上量过（engine_aiskirm u：aiskmod 把维和、标枪的 UnitModifier 两个系数都设 0，造兵逐秒和原版 aiskirm c 一样）、测试对拍 tests/test_simai.py——没有选兵策略表时 UnitModifier 不影响造什么；有策略表时的打分没量（原版人格都没有） |
| 已对拍 | `人格/UnitModifier.OffensiveModifier` | 92 | a4 a5 a7 | 台上量过（engine_aiskirm u：aiskmod 把维和、标枪的 UnitModifier 两个系数都设 0，造兵逐秒和原版 aiskirm c 一样）、测试对拍 tests/test_simai.py——没有选兵策略表时 UnitModifier 不影响造什么；有策略表时的打分没量（原版人格都没有） |
| 已对拍 | `人格/UnitModifier.Unit` | 92 | a4 a5 a7 | 台上量过（engine_aiskirm u：aiskmod 把维和、标枪的 UnitModifier 两个系数都设 0，造兵逐秒和原版 aiskirm c 一样）、测试对拍 tests/test_simai.py——没有选兵策略表时 UnitModifier 不影响造什么；有策略表时的打分没量（原版人格都没有） |
| 已对拍 | `战术/Tactic.DisbandAfterRetreatTeamSize` | 86 | a4 a5 a7 | 台上量过（engine_airetreat：airetf 0 撤回家后再出门，airetfd 999 撤回家后一直在家——撤退结束那轮人数 ≤ 它就结束战术、放人）、测试对拍 tests/test_simai.py；1 / 4 / 5 这种"剩几人才散"的中间值没量 |
| 已对拍 | `微操/AIMicroManagerData.EnterGarrisons` | 84 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aigarrison.py |
| 已对拍 | `造兵/BuildState.Difficulty` | 84 | a4 a5 a7 | 台上量过（engine_aiskirm s aiskdiff：只挂 HARD 的建造状态在普通难度一个不造，挂 MEDIUM 的照造），测试对拍 tests/test_simai_bench_b.py |
| 已对拍 | `造兵/BuildState.State` | 84 | a4 a5 a7 | 台上量过（engine_aiskirm y aisknew / aisknew2：没列进任何建造状态的我们的兵不造、列成 FEWEST_UNIT 占兵营约一半；z aiskvinf / aiskvveh：BEST_UNIT_EXPECTED 兵营只造克制兵），测试对拍 tests/test_simai_bench_b.py（B 第 126–131 轮）；RANDOM_UNIT（PercentLow/High）、MinTime 没单独量 |
| 已对拍 | `微操/AIMicroManagerData.UseSpecialPowers` | 83 | a4 a5 a7 | 台上量过（engine_aimicro：aimicspon 开 两个武士 s41 冲锋，aimicspoff 关 一直没冲、s51 前被打死，脚本按的对照照样冲）、测试对拍 tests/test_simai.py（模拟器读进探针自写的微操数据：开的想冲、关的从不冲；技能本身模拟器没接，只记"想用"） |
| 推断 | `微操/AIMicroManagerData.EngageHostileTargets` | 82 | a4 a5 a7 | E114新DLL aiegon:a / aiegoff:a各3/3 PASS：首冲371/259，首活均2；首批3170/3171均f345入队，f353均有单兵dest且aim为0。关无玩家级移动命令，但f431成员3171已有有效目标，不能解释成没有自主行军/目标；开f353模型过早推得目标，关f443模型首批仍无目标；同宿主帧按名回放 tests/test_ai_engage_clock.py strict xfail。单兵目标来源/保持契约仍gap，见 work/re/e114_engage_aim.md；保持推断，不晋升 |
| 已对拍 | `微操/AIMicroManagerData.EngagePassiveTargets` | 82 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_airetreat.py |
| 已对拍 | `开局/Order.Account` | 81 | a4 a5 a7 | docs/engine/aiopen.md#开局存款进哪个账户（Order Account，第 116 轮）（aiskacp / aiskacd：PRODUCTION 兵营出兵、DEFENSE 兵营不出） |
| 已对拍 | `开局/Order.Deposit` | 81 | a4 a5 a7 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（aiom15：带 Deposit 2000 照造、晚 4 秒） |
| 已对拍 | `微操/AIMicroManagerData.EngageTacticalTarget` | 79 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitactical.py |
| 已对拍 | `微操/AIMicroManagerData.PullbackInjured` | 78 | a4 a5 a7 | engine_aipullback aipullsov 残血坦克离队回吊车；tests/test_simai_bench_b.py::test_a_hurt_soviet_tank_team_is_pulled_back_to_the_crane 回放；普通盟军/日本工厂不可进入；仅地面车辆回撤，吊车回收仍 strict xfail，未验证空海军/精确时间 |
| 推断 | `微操/AIMicroManagerData.Crush` | 77 | a4 a5 a7 | engine_aicrush:aicrush1 台上s28–33守军0、坦克4；按名回放存活正常断言，清零strict xfail；模型守军11/9/9/9/8/8，首目标活着即被重选、未接触；首move终点不挪不代表后续均不挪；D86 aicrush1t碾压段aim全0，dest在f350/410/440变化；模型f230后首世界样本尚无远厂goal，前置已失配；tests/test_crush_observation.py按名回放，前置与首目的地strict xfail；追踪/选敌及移动仍gap，见work/re/e113_crush.md、e109_crush.md；不晋升 |
| 已对拍 | `目标/AITargetingHeuristic.SortType` | 76 | a4 a5 a7 | docs/engine/aitactics.md#目标挑哪个（Distance：aitpnear / aitpmt2 最近、次近；ThreatToGround：aitargetsafe） |
| 已对拍 | `组队招人/TeamTemplate.SortByDistance` | 75 | a4 a5 a7 | 专用engine_aisort aisort0/aisort1：容量1，关闭远候选f177先离、开启近候选f178先离，另一名留原位；固定到目标距离约985/700、到基地顺序相反；tests/test_simai_bench_c.py::test_sort_by_distance_replays_named_departure按名断言两组台内计数并回放匹配；已对拍限具名候选离开顺序；招走解释仍INFERRED，同帧动态队成员ID/实际距离和等距规则仍gap；见 work/re/c_sort_report.md |
| 推断 | `微操/AIMicroManagerData.ReverseMove` | 74 | a4 a5 a7 | engine_aipullback airev1/0台上s1–10坦克4、s19–22近厂2；tests/test_simai_bench_b.py按名回放，存活前置正常断言、近厂计数strict xfail；airevp近厂4不能证明没有倒车；E115 airev1t/0t各PASS：同帧目标/位置/车身朝向已取得，两侧各23个有效目标相邻帧移动样本无负点积；tests/test_ai_reverse_clock.py按名f263目标取得strict xfail；模型朝向/分支前置仍gap，暂停新台、不晋升；宿主台近厂读数不同于旧台，不假设等价；见work/re/e115_reverse_aim.md |
| 已对拍 | `目标/AITargetingHeuristic.Location` | 74 | a4 a5 a7 | E81/E87 engine_ailocation a：同型电厂一陆一水、四架双刃，仅切Land/Water/Water Land；s40到陆厂/到水厂分别4/0、0/4、4/0；tests/test_simai_bench_e.py::test_target_location按名回放三组通过。Location按位置地形过滤；只验证EnemyStructure/Distance，浅滩、桥面及空中目标仍INFERRED；见 work/re/e_location_e87.md |
| 推断 | `组队招人/TeamTemplate.ReleaseType` | 71 | a4 a5 a7 | engine_aiskirm aiskirm:m 实机s128防御8/清扫99，s129防御0/清扫8，转队时逐帧兵池峰1；后续s134峰2，不能宣称全程峰1；tests/test_simai_bench_c.py 按名回放至170秒无非空清扫计数，strict xfail；新airelnever/airelprio的CNVTeams已证原两ID保留/转队且模型阶段归属匹配，原八人补测的独立建造厂日志宿主实测防御9→2、清扫0→7，同名空实例并存；tests/test_simai_bench_c.py::test_release_eight_named_model_replays_carrier_partial_transfer为strict xfail，宿主等价性/精确时钟/后段第三ID和其他模式仍gap，整个字段未晋升；见 work/re/c_release_eight_report.md、c_release_teams_report.md、c_release_report.md |
| 已对拍 | `微操/AIMicroManagerData.EnemySearchDistanceVisionMultiplier` | 70 | a4 a5 a7 | engine_aisearch aisrchhi/aisrchlo 仅倍率1.5/0.25不同：高先打旁厂、到远厂0；低旁厂100且到远厂4；tests/test_simai_search.py 回放；仅被动建筑搜索，精确边界、敌军目标取得和揭雾未量 |
| 不涉及 | `表现/FeedbackEntry.EvaEvent` | 70 |  | 纯表现（语音、视频、画面） |
| 已对拍 | `启发条件/EnemyNearbyHeuristic` | 68 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/EnemyNearbyHeuristic.Distance` | 68 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/EnemyNearbyHeuristic.EnemyNearby` | 68 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/ObjectOfTypeExistsHeuristic` | 67 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/ObjectOfTypeExistsHeuristic.PassIfExists` | 67 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `组队招人/ObjectFilter.Relationship` | 67 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `开局/SkirmishOpeningMove.Side` | 64 | a4 a5 a7 | E82 engine_aiopenside a：固定盟军玩家显式挂载三电厂开局，仅切Side。Allies在[s55,s60)电厂3/兵营0，Soviet电厂2/兵营1。D66：Side和玩家阵营全等才进候选，候选全空=开局直接完成、不下单、不回退；模型照此（B第147节）。tests/test_simai_bench_e.py::test_opening_side[aiosallies]、test_an_opening_of_another_side_is_not_run按名回放、断言台上读数（Soviet s19-s28 无电厂）。gap：Soviet之后的2电厂1兵营是没开局时的结构建造，模型没建（strict xfail，同第123节）；见 work/re/e_openside_e82.md |
| 已对拍 | `组队招人/TeamTemplate.MinPowerAdvantage` | 64 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | `人格/SpecificUnitCap.Cap` | 60 | a4 a5 a7 | engine_aiskirm aiskcap:y（2026-11-12）：子人格给父人格没写的CNVNewPK四档Cap=2，新维和s33到2、停到s149（无上限aisknew2 s44已4），兵营改造标枪/维和；tests/test_simai_bench_b.py::test_a_specific_unit_cap_holds_our_unit_at_two按名回放、断言台上读数。E80父人格已有维和Cap=20时子人格Cap=2不生效=第一条命中（test_simai_bench_e.py）。gap：s150后又造到4、没死人，引擎拿什么数对上限未知（strict xfail test_after_s150_the_capped_unit_is_built_again）；见 work/re/handoff-b.md 第145节 |
| 已对拍 | `人格/SpecificUnitCap.Difficulty` | 60 | a4 a5 a7 | engine_aiskirm aiskcap:y（2026-11-12）：子人格给父人格没写的CNVNewPK四档Cap=2，新维和s33到2、停到s149（无上限aisknew2 s44已4），兵营改造标枪/维和；tests/test_simai_bench_b.py::test_a_specific_unit_cap_holds_our_unit_at_two按名回放、断言台上读数。E80父人格已有维和Cap=20时子人格Cap=2不生效=第一条命中（test_simai_bench_e.py）。gap：s150后又造到4、没死人，引擎拿什么数对上限未知（strict xfail test_after_s150_the_capped_unit_is_built_again）；见 work/re/handoff-b.md 第145节 |
| 已对拍 | `人格/SpecificUnitCap.Unit` | 60 | a4 a5 a7 | engine_aiskirm aiskcap:y（2026-11-12）：子人格给父人格没写的CNVNewPK四档Cap=2，新维和s33到2、停到s149（无上限aisknew2 s44已4），兵营改造标枪/维和；tests/test_simai_bench_b.py::test_a_specific_unit_cap_holds_our_unit_at_two按名回放、断言台上读数。E80父人格已有维和Cap=20时子人格Cap=2不生效=第一条命中（test_simai_bench_e.py）。gap：s150后又造到4、没死人，引擎拿什么数对上限未知（strict xfail test_after_s150_the_capped_unit_is_built_again）；见 work/re/handoff-b.md 第145节 |
| 已对拍 | `组队招人/CreateUnits.MaxUnits` | 60 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `组队招人/CreateUnits.MinUnits` | 60 | a4 a5 a7 | engine_aicreate aicr1c/aicr3c：最低1在(301,316]帧激活，最低3在(631,646]帧激活；后者f316一人/f481两人均未激活；tests/test_simai_bench_c.py按名回放激活区间和成员；仅孤立单槽位最低数1/3，多槽位/替补/MaxUnits仍gap；s70额外造兵另有strict xfail；见 work/re/e_create_e88.md |
| 已对拍 | `组队招人/CreateUnits.UnitName` | 60 | a4 a5 a7 | engine_aicreate aicr1c/aicr3c：最低1是一名新成员加两名已知预摆维和，最低3等三名新成员；tests/test_simai_bench_c.py按名回放首次组成；新成员兵种由固定生产归属仍INFERRED；仅指定最低数优先再普通补位，不是排他过滤；其他兵种/多槽位/替补仍gap；见 work/re/e_create_e88.md |
| 已对拍 | `战术/Tactic.Tactic=SimpleAttack` | 59 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 不涉及 | `表现/FeedbackEntry.Timeout` | 56 |  | 纯表现（语音、视频、画面） |
| 已对拍 | `造兵/BuildEntry.PercentHigh` | 54 | a4 a5 a7 | 台上量过（engine_aiskirm s aiskrand：RANDOM_UNIT "0%–30%" 和不带百分号的 "30–100" 两条都造出来——不带 % 的数也按百分比读，原版 _RANDOM 状态就这么写），测试对拍 tests/test_simai_bench_b.py；两条的比例（预测 3:7，台上 4:4）样本太少没定 |
| 已对拍 | `造兵/BuildEntry.PercentLow` | 54 | a4 a5 a7 | 台上量过（engine_aiskirm s aiskrand：RANDOM_UNIT "0%–30%" 和不带百分号的 "30–100" 两条都造出来——不带 % 的数也按百分比读，原版 _RANDOM 状态就这么写），测试对拍 tests/test_simai_bench_b.py；两条的比例（预测 3:7，台上 4:4）样本太少没定 |
| 已对拍 | `微操/AIMicroManagerData.UseGatherState` | 51 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipullback.py |
| 已对拍 | `启发条件/OpeningMoveHeuristic` | 47 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiomove.py |
| 已对拍 | `启发条件/OpeningMoveHeuristic.Complete` | 47 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiomove.py |
| 已对拍 | `开局/OpeningMove.Difficulty` | 46 | a4 a5 a7 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（aiodf / aiodf2：只留 MEDIUM 的） |
| 已对拍 | `开局/OpeningMove.Name` | 46 | a4 a5 a7 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（每个探针按名字挂自写开局，都照它造） |
| 已对拍 | `开局/OpeningMove.Weight` | 46 | a4 a5 a7 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（aiowt / aiowt2：0% 永远抽不到） |
| 已对拍 | `战术/Tactic.EndBehavior=RAMPAGE` | 46 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_ainamed.py |
| 已对拍 | `组队招人/TeamTemplate.ReleaseType=RELEASE_TO_PRIORITY` | 46 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `启发条件/PathToTargetHeuristic` | 45 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiopath.py |
| 推断 | `启发条件/PathToTargetHeuristic.LocomotorConditionToUseForTest` | 45 | a4 a5 a7 | E84 engine_aiopathcond a：同JapanAntiAirShip仅切NORMAL深水/SUPERSONIC空中；两组s22-s24均兵营1/电厂0，水组原始Island预测FAIL、空中PASS。tests/test_simai_bench_e.py按名回放实际计数通过，但不能区分条件生效与路径判定边界；C复核：旧配方Surface未显式指定，SDK移动器差异不能独立证明实际路径可达性；共享teamlog未提供路径求值或所选移动器读数，暂停重复上台，待可验证无路对照或D接口。保持gap不晋升，未改模型；见 work/re/c_pathcond_gate_report.md、e_pathcond_e84.md |
| 已对拍 | `启发条件/PathToTargetHeuristic.ObjectTypeToUseForTest` | 45 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiopath.py |
| 已对拍 | `启发条件/PathToTargetHeuristic.PathExists` | 45 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiopath.py |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=EnemyUnit` | 44 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 已对拍 | `战术/Tactic.Tactic=DefenseAvoidanceAttack` | 43 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 推断 | `战术/Tactic.Distance` | 41 | a4 a5 a7 | 专用engine_aidistance aidist250/aidist2000保留AI队、同次传送1200，仅Distance不同；s65小组圈300/900=1/1，大组0/0，存活均1；两组各5条PASS、模型末态匹配；大组实机传送前离300、传送后回900再离，模型美学轨迹strict xfail；精确边界/动态队成员仍gap，不晋升；tests/test_simai_bench_c.py；见 work/re/c_distance_report.md |
| 已对拍 | `微操/AIMicroManagerData.RetreatMinDistanceFromBase` | 40 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_airetreat.py |
| 推断 | `战术/Tactic.UseAestheticsManager` | 40 | a4 a5 a7 | 专用engine_aiaesthetics aiaeson/aiaesoff固定Distance=2000，仅切美学开关；两组各5条PASS：on先离300、传送后回900再离，off回双圈，存活/锁存均1；tests/test_simai_bench_c.py关闭组完整轨迹已回放；探针战术附加属性现传入消费者；E108按D83实际调用回放：首次遇敌gate=0仍发，后续102次gate=0不发、两次gate=1发；完整模拟首发154对台191且漏461，选敌/成员目的地/ready仍gap、strict xfail，不晋升；tests/test_ai_aesthetics_clock.py；见 work/re/e108_aesthetics_gate.md |
| 已对拍 | `目标/AITargetingHeuristic.Relationship` | 40 | a4 a5 a7 | docs/engine/ainamed.md#给关卡线的结论（ainmrel：写了 Relationship 就按关系过滤，玩家的楼当 NEUTRAL 不算，不出门） |
| 已对拍 | `造兵/BlockIfThingNearFactory.IncludeThing` | 40 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py:y |
| 已对拍 | `微操/AIMicroManagerData.RetreatMinDistanceToFallback` | 38 | a4 a5 a7 | engine_aifallback aifbshort100/aifblong500：四人存活回齐、在家约18秒、长组先于短组再出发；tests/test_simai_fallback.py::test_fallback_distance_first_return_and_departure；仅此固定FromBase=300场景的行为回放，未量内部退出位置、精确距离边界或其他基地选择 |
| 已对拍 | `目标/AITargetingHeuristic.SortType=Distance` | 37 | a4 a5 a7 | docs/engine/aitactics.md#目标挑哪个（aitpnear 挑最近、aitpmt2 第二槽挑次近、aitpvk 显式写 Distance） |
| 已对拍 | `人格/AIPersonalityDefinition.PersonalityType` | 35 | a4 a5 a7 | tests/test_simai_bench_b.py::test_the_personality_condition_matches_the_id_not_the_personality_type（engine_aiskirm pt aiskpt / aiskpti：脚本条件 PLAYER_IS_HUMAN_OR_AI_PERSONALITY 只认人格 id，PersonalityType 写成别的名字或不写都不影响；AI 行为不读它；B 第 150 轮） |
| 推断 | `造兵/BuildEntry.MinTime` | 34 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过（checks/engine_aiskirm.py:mt），没有测试跑这个台子 |
| 已对拍 | `启发条件/IsBuildingHeuristic` | 30 | a4 a5 a7 | E83 engine_aibuilding a：STRUCTURE空队列、现成基地1；PassIfBuilding=false时s40到陆厂4/在家0，true时0/4，两组PASS；tests/test_simai_bench_e.py::test_is_building_idle按名回放通过。只验空队列边界，建造中的行为未量；见 work/re/e_building_e83.md |
| 推断 | `启发条件/IsBuildingHeuristic.KindOf` | 30 | a4 a5 a7 | E83 engine_aibuilding只测STRUCTURE空队列，无法区分KindOf匹配与忽略此字段；有效建造队列、匹配/不匹配、多个token仍gap，不晋升；见 work/re/e_building_e83.md |
| 已对拍 | `启发条件/IsBuildingHeuristic.PassIfBuilding` | 30 | a4 a5 a7 | E83 engine_aibuilding a：STRUCTURE空队列、现成基地1；PassIfBuilding=false时s40到陆厂4/在家0，true时0/4，两组PASS；tests/test_simai_bench_e.py::test_is_building_idle按名回放通过。只验空队列边界，建造中的行为未量；见 work/re/e_building_e83.md |
| 已对拍 | `微操/AIMicroManagerData.PullbackInjuredHealthPct` | 30 | a4 a5 a7 | engine_aipullpct 固定30%血量、苏联吊车，仅阈值0.2/0.5不同；tests/test_simai_pullpct.py::test_pullback_threshold_high_returns_before_recycling 完整回放四车回家且不到远厂；同文件 low 对照先到远厂；仅初次回撤阈值，精确边界/晚段/吊车回收未闭环（回收 strict xfail） |
| 推断 | `微操/AIMicroManagerData.AlphaStrikeTargetHealthPct` | 28 | a4 a5 a7 | engine_aialphahp 旧固定70%对照；engine_aialphaclose 独立延迟守军、仅阈值0.01/0.9不同；tests/test_simai_bench_c.py 保留读数回放，有限诊断不等于字段闭环；目标适用条件与回放差异仍gap，见 work/re/c_alpha_close_report.md |
| 已对拍 | `战术/Tactic.Tactic=StaticDefense` | 28 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aidefense.py |
| 已对拍 | `造兵/BlockIfThingNearFactory.Relationship` | 28 | a4 a5 a7 | tests/test_simai_bench_b.py::test_a_thing_near_the_factory_blocks_the_entry（engine_aiskirm y aiskblkn / aiskblkr：Rule ANY + Relationship NEUTRAL 挡住，aiskblkf 400 外不挡；ENEMIES 走同一段代码没单独上台；B 第 149 轮） |
| 已对拍 | `造兵/BlockIfThingNearFactory.Rule` | 28 | a4 a5 a7 | tests/test_simai_bench_b.py::test_a_thing_near_the_factory_blocks_the_entry（engine_aiskirm y aiskblkn / aiskblkr：Rule ANY + Relationship NEUTRAL 挡住，aiskblkf 400 外不挡；ENEMIES 走同一段代码没单独上台；B 第 149 轮） |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=FriendlyUnit` | 27 | a4 a5 a7 | C engine_aifrdistance a：aifrnear/aifrswap三友军MCV，仅交换近远角色；s30逻辑帧478/486，tact对应原友车/second，同帧坐标均为距基地650的最近候选；友/敌MCV存活3/1。tests/test_simai_friendly_c.py::test_friendly_distance_target按名回放通过。仅验SAME_PLAYER、MCV、Distance、单槽StaticDefense；其他排序、默认关系、unique多槽仍INFERRED。旧E85远处双车的站位strict xfail保留，不由新配方解释；见work/re/c_friendly_distance_report.md |
| 推断 | `微操/AIMicroManagerData.UpdateTime` | 26 | a4 a5 a7 | engine_aimicro aimicupft/aimicupst:a 仅切微操0.5/4s，15帧宿主、D81时钟重量；台内首冲帧371/317、首活均2，末图逻辑帧872/876；tests/test_simai_bench_e.py 按名回放首活通过，精确首冲及人口峰值strict xfail；资格/更新前置状态、观测宿主人口等价仍gap；旧时钟读数不用于晋升，非固定延迟；见work/re/e102_update_clock.md，不晋升 |
| 已对拍 | `启发条件/TimerHeuristic` | 25 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/TimerHeuristic.EndTime` | 25 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/TimerHeuristic.StartTime` | 25 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=EnemyStructure` | 25 | a4 a5 a7 | docs/engine/aitactics.md#读数（ClosestStructureHeuristic、SafestToGroundStructureHeuristic：aitargetnear / aitargetsafe） |
| 已对拍 | `组队招人/TeamTemplate.ReleaseType=NEVER_RELEASE` | 25 | a4 a5 a7 | engine_airelease airelnever/airelprio仅ReleaseType不同；CNVTeams两组f166防御激活持3166/3167，priority在(526,541]同两ID转进攻，never保留至末样本；tests/test_simai_bench_c.py::test_never_release_engine_members_and_model_replay按名跑两台、断言实机ID/n/active及模型f301/601/976成员归属；仅固定两辆车的保留/转队，精确激活/转队时钟、priority后段短暂第三ID及其他释放模式仍gap；见 work/re/c_release_teams_report.md |
| 推断 | `战术/Tactic.Tactic=Engineer` | 24 | a4 a5 a7 | aieng/aiengctl原台四读数归属0/近目标0/工程师1/HP100，未证明招募或占领。E111 tests/test_simai_engineer_gate.py按名回放；模型状态/目标槽成立，工程师IGNORES_SELECT_ALL被候选池排除，空队超时且无战术运行/订单。这是模型前置诊断，不推定实机拒绝原因；需B候选资格/D同帧成员契约，不改过滤、不晋升，见work/re/e111_engineer.md |
| 推断 | `微操/AIMicroManagerData.EnterBaseDefensesWhenIdle` | 23 | a4 a5 a7 | engine_aibasedef aibd1 是战斗中总开关开、idle关的正例（s21起1人进炮塔）；aibd0/aibdidle 总开关均关且无人进驻，不是idle分支正例；tests/test_simai_basedef_idle.py 直接计数回放，aibd1仍strict xfail；独立回放其余三计数：s21台上炮塔3/远厂步兵4，模型1/0，三组strict xfail；模型有idle状态但三组均无双开关开启更新；实机idle/成员观测与到达/存活仍gap；见work/re/e112_basedef_idle.md |
| 已对拍 | `启发条件/IntervalHeuristic` | 22 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/IntervalHeuristic.ActiveTime` | 22 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/IntervalHeuristic.IntervalTime` | 22 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `微操/AIMicroManagerData.EnterGarrisonableStructureDistance` | 21 | a4 a5 a7 | engine_aigarrison aigar1/aigar0/aigarfar：默认150、旧楼EAST=40，近楼归AI、关闭或远楼不进；tests/test_simai_garrison_distance.py::test_garrison_distance_replays_recorded_near_far_and_disabled；仅现成近远行为回放，精确边界、其他配置值和进门死亡时序未量；距离0仅模型敏感性守卫 |
| 未做 | `人格/AIPersonalityDefinition.SkirmishPersonality` | 20 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 已对拍 | `战术/Tactic.EndIfStateTurnsOff` | 19 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 推断 | `经济/AccountShare.Account` | 18 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 已对拍 | `经济/AccountShare.Percent` | 18 | a4 a5 a7 | 台上量过（engine_aiskirm d / f：开局后 CoopBudget 防御 5%，存款约 36000 两座塔、约 17000 一座、15000 没有）、测试对拍 tests/test_simai.py——塔数对上；第一座的时刻模拟器早 ~36 s（strict xfail），别的份额 / 状态没单独量 |
| 已对拍 | `人格/BaseSelection.PreferredNotBaseTypes` | 17 | a4 a5 a7 | C aibn2old/aibn2new:b初始双基地固定OLD，仅切反偏好OLDEST/MOST_RECENT；f274两基地均合格，分数0/1选1与1/0选0，f284点命令崖矿/东矿。s55–65东/崖队员/双厂分别0/0/1/1与4/0/1/1；tests/test_expansion_target.py按名断言类型、分数、选择点和原计数。仅年龄类型反偏好命中子集；自动注册、死亡清理和矿点资格仍gap，旧CAPTURED单基地两strict xfail保留；见work/re/c_bn2_report.md |
| 已对拍 | `人格/BaseSelection.SortOrder` | 17 | a4 a5 a7 | C aibs3old/aibs3new:b初始双厂：f274两个合格基地0/1均分1，OLD pick/model=0/0、NEW=1/1；点命令分别东矿/崖矿。s55–65东/崖队员与双厂OLD=4/0/1/1、NEW=0/0/1/1；tests/test_expansion_target.py按名回放断言选择点和计数。仅OLD/NEW按基地编号排序；其他排序、注册顺序和矿点资格仍gap，见work/re/c_bs3_report.md |
| 已对拍 | `启发条件/TimerHeuristic.CountFrom` | 16 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 未做 | `战略状态/AIStrategicStateDefinition.CannotAttackTargetReaction` | 16 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 已对拍 | `战略状态/AIStrategicStateDefinition.MaxRunningCopies` | 16 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | `造兵/BuildEntry.Upgrade` | 16 | a4 a7 | C engine_aiupgrade a：aicupgon常量状态含UPGRADE_TECH/Tech2，s39起持有2（建造厂+它够得着的兵营）；aicupgoff移除专用状态后恒0；见work/re/c_upgrade_report.md。B第153轮接模型：升级条目按状态权重×分（UPGRADE 140；UPGRADE_TECH MinTime前0、ForceTime后200推断、中间140推断）挑最高下单，扣PRODUCTION，下了升级这一轮不下兵；模拟器s20下单、s40起持有2。tests/test_simai_upgrade_c.py按名回放两组通过。电力门、效率/兵力比两道、开局里的升级单没建模 |
| 已对拍 | `人格/BaseSelection.PreferredBaseTypes` | 15 | a4 a5 a7 | C aibp1old/aibp1new:b初始双基地固定OLD、反偏好为空，仅切偏好OLDEST/MOST_RECENT；f274两基地均合格，分数1/0选0与0/1选1；f284点命令东矿/崖矿。s55–65东/崖队员/双厂分别4/0/1/1与0/0/1/1；tests/test_expansion_target.py按名断言类型、分数、选择点与原计数。仅年龄类型偏好命中子集；自动注册、死亡清理和矿点资格仍gap；见work/re/c_bp1_report.md |
| 已对拍 | `人格/BaseSelection.SortOrder=PREFER_OLDEST` | 15 | a4 a5 a7 | 初始双厂同分候选，OLD选基地0、NEW选基地1；按名选择点/计数回放，仅该排序子集，见work/re/c_bs3_report.md |
| 推断 | `启发条件/ConstantHeuristic.Weight` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/IntervalHeuristic.CountFrom` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/TechBuildingShareHeuristic` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/TechBuildingShareHeuristic.Above` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/TechBuildingShareHeuristic.PercentOfFairShare` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.AlphaStrikeTargetTimeToKill` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 已对拍 | `微操/AIMicroManagerData.DodgeThreats` | 15 | a4 a5 a7 | engine_aidodge aidodgeon/aidodgeoff 原版精确打击信标开关对照；tests/test_ai_dodge.py 按名断言两人存活、信标存在时on离开/off保持2，以及到期清理；simai micro_team威胁视图/移动回调接私有micro消费者，仅单信标地面成员；固定0.5秒反应、径向逃离/目的地保持/首次可见寿命起点为INFERRED；精确时钟、安全圆、通用过滤/所属、多威胁仍gap，见 work/re/e116_dodge.md |
| 已对拍 | `微操/IgnoreTargets.IncludeThing` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py:y |
| 推断 | `目标/AITargetingHeuristic.HighestPriorityEnemyPlayersOnly` | 15 |  | C按名台子engine_aitoponly：显式s4=30/p1=10，高档仅建造场、低档有兵营；true组s40在家4/兵营0，false组在家0/兵营4；把兵营给高档的true阳性对照同false。tests/test_top_enemy_only.py断言原计数并按名回放；无同帧实际优先级表/候选资格，同档多玩家及动态优先级仍gap，保持推断；见work/re/c_toponly_report.md |
| 推断 | `目标/AITargetingHeuristic.MinDistanceFromEnemy` | 15 | a4 a5 a7 | C按名台子engine_aimindist：同一中立油井，TechBuilding阈值0组采样s6起目标区4，2000组采样s1-55在家4/目标区0；NamedObject阳性对照同0组。tests/test_min_enemy_distance.py断言原计数并按名回放；无同帧实际距离/候选资格，采样时钟未对齐游戏帧，边界与敌人物体资格仍gap，保持推断；见work/re/c_mindist_report.md |
| 已对拍 | `组队招人/TeamTemplate.Priority=LOW` | 15 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 推断 | `造兵/BuildEntry.CountModifier` | 15 |  | C engine_countmodifier a：同经济/工厂/候选和初始新维和4/新标枪2，仅切0.5/4；台上低组s27先补标枪、s38–66人数4/5，高组s27先补维和、s39–66人数7/2。tests/test_count_modifier.py按名回放s40原人数；精确分值/资格/队列消费未观测，保留推断，不改B模型；见work/re/c_countmodifier_report.md |
| 不涉及 | `人格/AIPersonalityDefinition.PersonalityUIName` | 14 |  | 纯表现（语音、视频、画面） |
| 推断 | `目标/AITargetingHeuristic.SortType=ThreatToWater` | 14 | a4 a5 a7 | C按名台子engine_aiwater：两电厂/近处守护者/AI两栖矿车，仅切Distance与ThreatToWater，实机两组采样s14后均近4/远0/家0；模型ThreatToWater选远，按名回放strict xfail。tests/test_water_threat.py独立断言原计数并保留原预测FAIL；近处Named对照因s40-41无采样亦strict xfail。无同帧候选资格/实际water威胁值/水域样本资格，不改模型、不晋升；见work/re/c_water_report.md |
| 推断 | `人格/AIPersonalityDefinition.Side` | 13 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/IgnoreTargets.Rule` | 13 | a4 a5 a7 | E118 engine_aiignore_rule aiignrany/aiignrall：原版EASY包含标记不变，仅切ANY/ALL；同帧两成员，首伤396/397，前置失配0；f406/421分别状态0有目标与8无目标。ALL保留墙钟s22造出1导致的诊断FAIL，游戏帧前置成立；tests/test_ai_ignore_rule.py按名回放伤害/前置及ALL状态，ANY候选资格strict xfail；目标身份、工程师分类/Alpha资格仍gap，不晋升；见 work/re/e118_ignore_rule.md |
| 已对拍 | `组队招人/TeamTemplate.Priority=DEFENSE` | 13 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 推断 | `启发条件/AllNearbyNodesFullHeuristic` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.CrushPreference` | 12 | a4 a5 a7 | 同Crush，开关/低偏好对照守军至少8的按名回放保留；完整清零strict xfail；不把活目标重选解释为死亡后等待，见work/re/e109_crush.md；不晋升 |
| 推断 | `微操/AIMicroManagerData.RandomTargetScoreModifier` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.TimeToKeepTargetMax` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.TimeToKeepTargetMin` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `战术/Tactic.Tactic=SimpleExpansion` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=Expansion` | 12 | a4 a5 a7 | C已上台：aiexpc:a东矿区4、崖矿区0、普通实体0，命令指向东矿点；模型已保留BaseSelection，增加显式候选回调和槽位点，Expansion不再回退普通实体。D98新观测确认所选基地id0、合格且偏好分1；双厂实验已移除脚本厂伪基地。bsel是基地候选而非矿点候选；矿点资格/排序/占用仍未证，aiexpc模型按名回放仍strict xfail，不晋升；见 work/re/c_expansion_d98_report.md |
| 已对拍 | `目标/AITargetingHeuristic.SortType=ThreatToGround` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 未做 | `造兵/CountAsStructureForBuildPurposesFilter.ExcludeThing` | 12 | a4 a5 a7 | C静态核查：原版过滤器用于建造优先级，排除矿车/勘探车/日本矿厂核心；不是现有建筑计数。模型未消费该过滤器，候选分类需接B共享build_units，普通建筑BuildState优先级亦缺消费者；按工单接口门禁停止，未上台、未晋升。待B给候选分类/优先级接口；见work/re/c_buildfilter_report.md |
| 不涉及 | `战略状态/AIStrategicStateDefinition.ExecutionBeginFeedbackKey` | 11 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `战略状态/AIStrategicStateDefinition.ExecutionCanceledFeedbackKey` | 11 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `战略状态/AIStrategicStateDefinition.ExecutionCompleteFeedbackKey` | 11 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=FriendlyStructure` | 11 | a4 a5 a7 | docs/engine/aitactics.md#读数（FriendlyLandStructureHeuristic：engine_aidefense 守自家建造厂） |
| 推断 | `组队招人/ObjectFilter.Include` | 11 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `组队招人/TeamTemplate.Priority=COOP` | 11 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 不涉及 | `人格/AIPersonalityDefinition.CommanderPortrait` | 10 |  | 纯表现（语音、视频、画面） |
| 未做 | `其他/BuildingPlacementDistance.Distance` | 10 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 已对拍 | `启发条件/PowerAdvantageHeuristic` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipoweradv.py |
| 推断 | `启发条件/PowerAdvantageHeuristic.Above` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/PowerAdvantageHeuristic.IncludeEnemyDefenses` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/PowerAdvantageHeuristic.IncludeOwnDefenses` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/PowerAdvantageHeuristic.Value` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/TimeSinceLastExpansionHeuristic` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/TimeSinceLastExpansionHeuristic.Time` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 已对拍 | `目标/AITargetingHeuristic.SearchRange` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 推断 | `组队招人/TeamTemplate.AllowRecruitUnitsInCombat` | 9 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 已对拍 | `组队招人/TeamTemplate.Priority=HIGH` | 9 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 不涉及 | `表现/StrategicDirectiveFeedback.Event` | 9 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/StrategicDirectiveFeedback.FeedbackKey` | 9 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/StrategicDirectiveFeedback.StrategicDirective` | 9 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 推断 | `启发条件/EnemyNearbyHeuristic.MinEnemyValue` | 8 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/ObjectOfTypeExistsHeuristic.Location` | 8 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.ForbiddenObjectStatus` | 8 | a4 a5 a7 | C engine_aiforbid a：同近电厂仅切UNDER_IRON_CURTAIN禁用字段；无过滤有位/有过滤有位/有过滤清位三组原状态与近远家计数分别1/4/0/0、1/0/4/0、0/4/0/0，均PASS。tests/test_forbidden_status.py按名回放并断言原图计数；单位置位过滤吻合，未改模型。追加原UNATTACKABLE UNDER_IRON_CURTAIN组合，仅IRON置位，原状态掩码1；空/单IRON/双位过滤s40.1计数为1/4/0/0、1/0/4/0、1/0/4/0，三局PASS支持该子集ANY，模型吻合。再测仅UNATTACKABLE置位，空/单UNATTACKABLE/双位过滤s40.1原读数分别2/4/0/0、2/0/4/0、2/0/4/0；s5..41原状态均2，三局PASS及按名回放支持另一单位置位子集ANY，未改模型。同帧候选资格、原版技能、双位同时置位及AIRBORNE_TARGET/SUBMERGED仍gap，整字段不晋升；见work/re/c_forbid_report.md、work/re/c_forbidmask_report.md、work/re/c_forbiduna_report.md |
| 推断 | `目标/AITargetingHeuristic.SortType=ThreatToAir` | 8 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.Beacon` | 7 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=Beacon` | 7 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `组队招人/TeamTemplate.MaxTypesOfUnits` | 7 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/AIPersonalityDefinition.BaseCompactness` | 6 | a4 a5 a7 | 台上量过（engine_aitower：0.5 / 0.75 / 1.0 塔落在不同圈）；模拟器只对上 0.5，0.75 / 1.0 和 0.5 一样（strict xfail） |
| 未做 | `人格/AIPersonalityDefinition.RepairBuildingsAtDifficulty` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.UsePlayerPowersAtDifficulty` | 6 |  | AI 模型代码里没有这个名字 |
| 推断 | `启发条件/BeaconExistsHeuristic` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/BeaconExistsHeuristic.Exists` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/BeaconExistsHeuristic.Type` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/PathToTargetHeuristic.Surface` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/ResourceNodeShareHeuristic` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/ResourceNodeShareHeuristic.Above` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/ResourceNodeShareHeuristic.PercentOfFairShare` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 已对拍 | `微操/AIMicroManagerData.DodgeThreatsReactionTimeMax` | 6 | a4 a5 a7 | engine_aidodge aidodgezero/aidodgetwo固定相等端点联合快慢对照；tests/test_ai_dodge.py按名回放出生/首次离开锁存和前置；只验0秒先于2秒，未区分单独Min/Max、随机分布或精确反应帧；见 work/re/e117_dodge_clock.md |
| 已对拍 | `微操/AIMicroManagerData.DodgeThreatsReactionTimeMin` | 6 | a4 a5 a7 | engine_aidodge aidodgezero/aidodgetwo固定0/0与2/2秒联合端点对照；台内出生f451，首次离开f454/f486，前置失配0；tests/test_ai_dodge.py按名断言快慢顺序；绝对离开帧模型475/505未对齐，单独端点作用/随机范围/精确反应帧仍gap；见 work/re/e117_dodge_clock.md |
| 推断 | `微操/SpecificSpecialPowerDelay.MaximumDelay` | 6 | a4 a5 a7 | 模型按成功施放后同类冷却消费上限；tests/test_simai_delay.py 验证上端点和真实冲锋执行接线；engine_aidelay 0/999实机PASS，脚本冲峰值2/1且曾冲>0已有回放；台上帧数减曾冲恒362、模型270，精确观测时钟strict xfail；随机分布及原版TOGGLE两种子类仍gap，不晋升原版用量；见work/re/c_delay_clock_report.md |
| 推断 | `微操/SpecificSpecialPowerDelay.MinimumDelay` | 6 | a4 a5 a7 | 模型已读取；engine_aidelay 0/999实机配对仅改变MaximumDelay，本字段没有独立变量对照，不因探针出现字段名登记已对拍 |
| 推断 | `微操/SpecificSpecialPowerDelay.PowerType` | 6 | a4 a5 a7 | 模型已读取；engine_aidelay 0/999实机配对仅改变MaximumDelay，本字段没有独立变量对照，不因探针出现字段名登记已对拍 |
| 推断 | `微操/SpecificSpecialPowerDelay.TogglePowerSubType` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `战术/Tactic.Tactic=ExactExpansion` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `战术/Tactic.Tactic=GarrisonBuilding` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 已对拍 | `战术/Tactic.Targetless` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aimicro.py |
| 未做 | `战略状态/AIStrategicStateDefinition.PathfindingCheckType` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | `组队招人/TeamTemplate.Priority=DEFENSE_HIGH` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `组队招人/TeamTemplate.RequireCanAttackTarget` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 已对拍 | `经济/AccountShare.Account=DEFENSE` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `经济/AccountShare.Account=PRODUCTION` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiomove.py |
| 未做 | `经济/AccountShare.Account=SLUSH_FUND` | 6 | a4 a5 a7 | C按名台子engine_aislush：aislush100/aislush0仅交换SLUSH_FUND与PRODUCTION份额，两组电厂均s19一座、s29两座，零份额原预测FAIL保留；开局未区分此账户。第二轮有收入无开局：aislsdef全程零炮塔，aislddef在s28/48/68造出1/2/3座，s60为2。tests/test_slush_account.py原读数及模型回放；账户余额/实际支出消费者仍gap，不以开局计数吻合晋升；见work/re/c_slush_report.md |
| 不涉及 | `表现/SkirmishGameEventFeedback.Event` | 6 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/SkirmishGameEventFeedback.FeedbackKey` | 6 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 已对拍 | `人格/EnemyFilter.Include` | 5 | a4 a5 a7 | tests/test_enemyfilter.py::test_enemyfilter_named_bench_replay（C 的 engine_aienemyfilter aiefharv / aiefeng / aiefself：Include HARVESTER 近处敌矿车触发、ENGINEER 不触发，SAME_PLAYER 无自家矿车不触发；模型 B 第 155 轮接进 EnemyNearby） |
| 已对拍 | `人格/EnemyFilter.Relationship` | 5 | a4 a5 a7 | tests/test_enemyfilter.py::test_enemyfilter_named_bench_replay（C 的 engine_aienemyfilter aiefharv / aiefeng / aiefself：Include HARVESTER 近处敌矿车触发、ENGINEER 不触发，SAME_PLAYER 无自家矿车不触发；模型 B 第 155 轮接进 EnemyNearby） |
| 推断 | `人格/EnemyFilter.Rule` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `微操/AIMicroManagerData.MinDistanceFromBaseToIgnoreTargets` | 5 | a4 a5 a7 | E120 engine_aiignore aiignzt/aiignnt：同run基地选择与目标位置配对，0/2000首伤397/396；f406/421零组状态8无目标、高组状态0有目标。消费者已接被动选敌、敌对可攻击及逐人分配过滤；唯一基地(3850,3400)与home一致，两目标距基地502.49；tests/test_ai_ignore_distance.py按名断言基地/目标位置与距离门，零组状态通过，高组资格仍strict xfail；多基地选择/精确边界/无基地/候选资格仍gap，不晋升已对拍；见 work/re/e120_ignore_base.md |
| 未做 | `微操/AIMicroManagerData.PassiveTargetSearchDistance` | 5 | a4 a5 a7 | E104 engine_aipassive_distance aipsdz/aipsdt/aipsds/aipsdl：0/1/200/600均f140状态6选四人旁厂，f320状态0；中心距350.3、逐兵至少324.3，微操目标不同于战术目标。两轮未出现距离分离；tests/test_ai_passive_distance.py按台名回放选择/移动/存活，精确首选时钟strict xfail；本入口未显现消费者，零值全局语义/距离基准/其他入口仍gap，暂停、不加猜测消费者、不晋升；见 work/re/e104_passive_distance.md、work/re/handoff-e.md |
| 推断 | `微操/AIMicroManagerData.SiegeWeaponBuffer` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.SpecialPowerDelayMaximum` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.SpecialPowerDelayMinimum` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/IgnoreTargets.Include` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `微操/SpecificSpecialPowerDelay.TogglePowerSubType=TOGGLE_LOCKDOWN` | 5 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `战略状态/AIStrategicStateDefinition.PathfindingCheckType=None` | 5 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=EnemyStructureCloseToShore` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=TechBuilding` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.MaxDistanceToShore` | 5 | a4 a5 a7 | C按名台子engine_aishore：同一岸边电厂仅上限2000改1，2000组s14目标区4/s25全离家，1组s1-65在家4/目标区0；普通EnemyStructure阳性对照同2000组。tests/test_shore_distance.py断言原读数并按名回放；1组strict xfail，世界桥接尚未提供实际岸距。复杂海岸/取点算法仍gap，未晋升；见work/re/c_shore_report.md |
| 推断 | `目标/AITargetingHeuristic.SortType=ClosestToEnemy` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.UnderAttack` | 5 |  | AI 模型代码里读了这个名字 |
| 推断 | `经济/BudgetState.Difficulty` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `经济/BudgetState.State` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/UnitCap.Cap` | 4 |  | AI 模型代码里读了这个名字 |
| 推断 | `人格/UnitCap.Difficulty` | 4 |  | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/IncomeAdvantageHeuristic` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/IncomeAdvantageHeuristic.Above` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/IncomeAdvantageHeuristic.Value` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/OpenNodeHeuristic` | 4 | a4 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/OpenNodeHeuristic.Exists` | 4 | a4 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/OpenNodeHeuristic.MinDistanceFromEnemy` | 4 | a4 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.CanUseSiegeState` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.GatherTempVisionRangeBonus` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.RetreatTempVisionRangeBonus` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/IgnoreTargets.Exclude` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.VitalObjectStatus` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `造兵/CountAsStructureForBuildPurposesFilter.Include` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `造兵/CountAsStructureForBuildPurposesFilter.Rule` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EmergencyManagerHandleConyardInDangerAtDifficulty` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/PersonalityMap.Personality` | 3 |  | AI 模型代码里没有这个名字 |
| 未做 | `人格/PersonalityMap.Side` | 3 |  | AI 模型代码里没有这个名字 |
| 未做 | `战术/Tactic.AestheticsManagerMinDistanceFromHarvester` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `战术/Tactic.AestheticsManagerPatrolIdleTime` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | `战术/Tactic.Tactic=NullTactic` | 3 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=Point` | 3 | a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=UnpackBuildingPlacement` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.AircraftRepairFacility` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.EnergyProducer` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.ExpanderTemplate` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.GathererTemplate` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.MCVTemplate` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.NavalRepairFacility` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.PrimaryResourceNodeCollector` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.PrimaryResourceThingToBuild` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | `阵营/ArmyDefinition.Side` | 3 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `阵营/ArmyDefinition.VehicleRepairFacility` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `阵营/ArmyDefinition.WallPiece` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.BuildTechEfficiencyThreshold` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.BuildTechMinPowerAdvantage` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.DesiredExcessPowerBuffer` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EmergencyManagerHandleNoConyardAtDifficulty` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EmergencyManagerHandleNoIncomeAtDifficulty` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EmergencyManagerHandleUnderAttackAtDifficulty` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 已对拍 | `人格/BaseSelection.SortOrder=PREFER_NEWEST` | 2 | a4 a5 a7 | 初始双厂同分候选，OLD选基地0、NEW选基地1；按名选择点/计数回放，仅该排序子集，见work/re/c_bs3_report.md |
| 推断 | `启发条件/CanBuildBuildingsOnSurfaceHeuristic` | 2 | a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/CanBuildBuildingsOnSurfaceHeuristic.MaxPlacementGridCells` | 2 | a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/CanBuildBuildingsOnSurfaceHeuristic.MinPlacementGridCells` | 2 | a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/CanBuildBuildingsOnSurfaceHeuristic.Surfaces` | 2 | a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.MaxUnitIdleDistanceChange` | 2 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `战术/Tactic.Tactic=Hunt` | 2 |  | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=Husk` | 2 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=Team` | 2 |  | AI 模型代码里没有这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=UnderAttackBy` | 2 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过（docs/engine/aitactics.md），没有测试跑这个台子 |
| 未做 | `目标/AITargetingHeuristic.IgnoreMinDistanceFromConyardEntranceForTime` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `目标/AITargetingHeuristic.MinDistanceFromConyardEntrance` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | `组队招人/ObjectFilter.Exclude` | 2 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `经济/ResourceMultiplierCheat.Difficulty` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `经济/ResourceMultiplierCheat.Percentage` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.AssaultBeaconRadius` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.CleanupRefineries` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.ConyardInDangerEmergencyEngineerDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.ConyardInDangerEmergencyHealthPercent` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.ConyardInDangerEmergencyUnderAttackTime` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.CoopPersonality` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.DefaultThreatFindRadius` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemyResortingTime` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemySortingBrutalDifficulty` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemySortingEasyDifficulty` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemySortingHardDifficulty` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemySortingMediumDifficulty` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.HoldObjectBeaconRadius` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.HoldPositionBeaconRadius` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.MaxWallDestroyTimeToCountAsGoThroughWalls` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | `人格/AIPersonalityDefinition.ReactiveDefenseRadius` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过（docs/engine/aitactics.md），没有测试跑这个台子 |
| 未做 | `人格/AIPersonalityDefinition.RefineryPlacementIncreaseTickAmount` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.RefineryPlacementNumberOfIncreaseTicksBeforeGivingUp` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.RefineryPlacementStartDistanceDelta` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.ResourceNodeSearchRadius` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.ResourceNodeValueRemainingForExpansion` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 已对拍 | `人格/AIPersonalityDefinition.SecondsTillTargetsExpire` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 不涉及 | `人格/AIPersonalityDefinition.SkirmishTimeTillGreeting` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 推断 | `人格/AIPersonalityDefinition.UnitBuilderEnemyNearbyDistance` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/AIPersonalityDefinition.UnitBuilderEnemyNearbyMultiplier` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/AIPersonalityDefinition.UnitBuilderOverallDefensivePreference` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/DefaultTacticHomeBaseCriteria.PreferredNotBaseTypes` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/DefaultTacticHomeBaseCriteria.SortOrder` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过（checks/engine_aiexpansion.py），没有测试跑这个台子 |
| 推断 | `人格/Filter.Exclude` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/Filter.Include` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/Filter.Rule` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/RetreatBaseCriteria.PreferredNotBaseTypes` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/RetreatBaseCriteria.SortOrder` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过（checks/engine_aiexpansion.py），没有测试跑这个台子 |
| 未做 | `全局常量/AIData.AICrushesInfantry` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.AIDozerBoredRadiusModifier` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 不涉及 | `全局常量/AIData.AllowForestFires` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `全局常量/AIData.AltCameraPitchOverride` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `全局常量/AIData.AltCameraZoomOverride` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 未做 | `全局常量/AIData.AttackMoveUsesFormations` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.AttackUsesLineOfSight` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.CastleSiegeStandBackDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.ChaseFromBehindLimit` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.DeepWaterDepth` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 不涉及 | `全局常量/AIData.DisableTrees` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 未做 | `全局常量/AIData.EnableRepulsors` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.ForceSkirmishAI` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.FormationColumnWidth` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.FormationEnemyDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.FormationRowDepth` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.FormationSquadSpacing` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.GuardChaseUnitFrames` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.GuardEnemyReturnScanRate` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.GuardEnemyScanRate` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.HordesWaitForHordes` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 不涉及 | `全局常量/AIData.LowLodTree` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `全局常量/AIData.LowLodTreeNoGrab` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `全局常量/AIData.LowLodTreeNoHarvest` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `全局常量/AIData.LowLodTreeScale` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 未做 | `全局常量/AIData.MaxRecruitDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.MaxRetaliateDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.MaxSquadWidth` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 不涉及 | `全局常量/AIData.MaximumCraterDepth` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 未做 | `全局常量/AIData.MeleeApproachDist` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.MeleeApproachTolerance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.MinDistanceForGroup` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.NarrowPassageScale` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.Optimization_NumEfficiencyUpdates` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.Optimization_NumTeamsToRecruit` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.Optimization_TacticsEmergencyKickPeriod` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.Optimization_TimeToCacheCanEnterTransport` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.Optimization_TimeToCacheCanReachImmobileTarget` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.Optimization_TimeToCacheCanReachMobileTarget` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.RebuildDelaySeconds` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.RepulsedDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.ResourcesPoor` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.ResourcesWealthy` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.RetaliateFriendsRadius` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.RotateSkirmishBases` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.SkirmishGroupFudgeValue` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.StructureSeconds` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.StructuresPoorMod` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.StructuresWealthyMod` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.SupplyCenterSafeRadius` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.TeamPoorMod` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.TeamResourcesToBuild` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.TeamSeconds` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.TeamWealthyMod` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.UseFormations` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 不涉及 | `全局常量/AIData.UseLowLODTrees` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 未做 | `全局常量/AIData.WadeWaterDepth` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.WaitForOthers` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `全局常量/AIData.WallHeight` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 已对拍 | `启发条件/ScriptedFlagHeuristic` | 1 |  | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py:y |
| 已对拍 | `启发条件/ScriptedFlagHeuristic.FlagName` | 1 |  | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 未做 | `微操/AIMicroManagerData.CanCollectCratesWhenIdle` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `微操/AIMicroManagerData.FractionBlockedToDestroyWalls` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | `微操/AIMicroManagerData.IsHarvesterManager` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `微操/AIMicroManagerData.MaxSecondaryDamageFraction` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | `微操/AIMicroManagerData.MaxTeamIdleDistanceChange` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 已对拍 | `微操/AIMicroManagerData.MaxTeamIdleTime` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 已对拍 | `微操/AIMicroManagerData.MaxUnitIdleTime` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 推断 | `微操/AIMicroManagerData.MinTimeToKeepTempVisionRangeBonus` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `微操/IgnoreTargets.StatusBitFlags` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | `微操/SpecificSpecialPowerDelay.TogglePowerSubType=TOGGLE_DEFENSE_SELF_ONLY` | 1 |  | AI 模型代码里读了这个名字 |
| 已对拍 | `战术/Tactic.EndBehavior=RETURN_HOME_AND_DISBAND` | 1 |  | docs/engine/aitactics.md#目标没了以后（EndBehavior，2026-11-09 各一次）（aiendh：同 DISBAND，没回家，和模型对上） |
| 推断 | `战术/Tactic.Tactic=ReactiveDefense` | 1 |  | AI 模型代码里读了这个名字；台上量过（docs/engine/aitactics.md），没有测试跑这个台子 |
| 推断 | `战略状态/AIStrategicStateDefinition.MaxInactiveCopies` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `战略状态/AIStrategicStateDefinition.PathfindingCheckType=QuickDoesAttackPathExist` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=Bridge` | 1 |  | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=Crate` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=EnemyGarrison` | 1 |  | AI 模型代码里读了这个名字 |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=Help` | 1 |  | AI 模型代码里没有这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=NeutralGarrison` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `组队招人/TeamTemplate.BaseDefenseMaxDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | `组队招人/TeamTemplate.IsBaseDefenseTeam` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `组队招人/TeamTemplate.Priority=HOTSPOT` | 1 |  | AI 模型代码里读了这个名字 |
| 推断 | `组队招人/TeamTemplate.Priority=SCRIPTED` | 1 |  | AI 模型代码里读了这个名字 |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.MinPowerAdvantageEnemiesInMyBaseVsAllMyUnits` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.NumberOfObjectsRecentlyLost` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.ObjectLostFilter` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.OnlyIfLocalPlayerIs` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.TimeBetweenScans` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.TimeForNumberOfObjectLost` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.TimeThatConditionsMustBeMet` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.TimeoutAfterPlaying` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 推断 | `造兵/BuildEntry.Score` | 1 |  | AI 模型代码里读了这个名字 |
