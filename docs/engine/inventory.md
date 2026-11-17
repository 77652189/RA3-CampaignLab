# 原版功能总清单（引擎 A：脚本层、物体模块、武器效果；引擎 B：AI）

由 `experimental/cnv/inventory.py` 从原版数据生成，**别手改**；`tests/test_inventory.py` 在它过期时变红。状态与判定规则见脚本 docstring（ADR 0026）。用量：脚本 = 原版战役脚本里出现的次数；模块 = 原版战役地图里摆了的、用到它的物体种数（括号里是全部物体种数）；武器效果 = 用到它的原版武器数；AI = 原版 AI 数据（SDK SkirmishAI，含战役关的 AI 状态）里写它的次数，判定规则见 `inventory_ai.py`。**主数字是"按用量已对拍"**：已对拍项的用量占全部用量的比例，推断不算，不涉及不进分母；目标每部分 90%。"9 关用到"：我们 9 关（`missions/a1.py`～`a9.py`）里用到这项的关（脚本、物体模块、武器效果按 `inventory_levels.py`，AI 按 `inventory_ai.py levels`；"全部" = 9 关都用）；"9 关用到的按用量已对拍"只算这些项（用户 11-11 定：先做完 9 关用到的）。

| 部分 | 按用量已对拍 | 9 关用到的按用量已对拍 | 9 关用到（已对拍 / 项） | 项数 | 已对拍 | 推断 | 未做 | 不涉及 | 按用量已有（已对拍+推断） |
|---|---|---|---|---|---|---|---|---|---|
| 脚本动作 | **98%** | **100%** | 50 / 50 | 451 | 206 | 11 | 119 | 115 | 99% |
| 脚本条件 | **100%** | **100%** | 12 / 12 | 89 | 74 | 0 | 12 | 3 | 100% |
| 物体模块 | **98%** | **98%** | 59 / 119 | 197 | 61 | 27 | 83 | 26 | 99% |
| 武器效果 | **94%** | **95%** | 18 / 24 | 33 | 20 | 5 | 5 | 3 | 96% |
| AI | **98%** | **98%** | 201 / 357 | 428 | 220 | 83 | 91 | 34 | 100% |

## 脚本动作

| 状态 | 名字 | 用量 | 9 关用到 | 说明 |
|---|---|---|---|---|
| 已对拍 | `ENABLE_SCRIPT` | 5727 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_cast.py |
| 已对拍 | `SET_MILLISECOND_TIMER` | 4153 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `SET_FLAG` | 4105 | 全部 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_activate.py |
| 已对拍 | `ALLOW_DISALLOW_ONE_BUILDING` | 3466 | a4 a5 a7 | tests/test_simbench.py::test_a_ban_holds_the_queue_and_does_not_cancel |
| 已对拍 | `PLAYER_LOCK_PLAYER_TECH` | 1887 |  | tests/test_simbench.py::test_protocol_a_computer_player_spends_unless_locked |
| 已对拍 | `DISABLE_SCRIPT` | 1099 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `MOVE_NAMED_UNIT_TO` | 1000 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acts.py |
| 已对拍 | `LINK_MISSION_OBJECTIVE_TO_OBJECT` | 950 | 全部 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts5.py |
| 已对拍 | `NAMED_DELETE` | 908 | a2 a4 a5 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aipullback.py |
| 已对拍 | `CREATE_REINFORCEMENT_TEAM` | 753 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_conds.py:team |
| 已对拍 | `SET_MISSION_OBJECTIVE_STATUS` | 732 | 全部 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_markobj.py |
| 不涉及 | `PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT` | 640 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `CALL_SUBROUTINE` | 533 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `UNIT_IDLE_FOR_FRAMECOUNT` | 504 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 不涉及 | `PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT_WITH_SUBTITLE` | 445 |  | 纯表现（名字规则） |
| 不涉及 | `MOVIE_PLAY_RADAR` | 433 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION` | 399 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 已对拍 | `OBJECTLIST_ADDOBJECTTYPE` | 383 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_kind.py:all |
| 已对拍 | `PLAYER_SET_MONEY` | 345 | 全部 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acts.py |
| 已对拍 | `SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY` | 343 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiprio.py |
| 已对拍 | `PLAYER_RELATES_PLAYER` | 319 | a2 a4 a5 a7 a9 | tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back |
| 已对拍 | `UNIT_AFFECT_OBJECT_PANEL_FLAGS` | 317 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 已对拍 | `SET_MISSION_HOT_SPOT_VISIBILITY` | 300 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_conds.py:sight |
| 已对拍 | `MOVE_TEAM_TO` | 298 | a4 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aixfer.py |
| 已对拍 | `CREATE_NAMED_ON_TEAM_AT_WAYPOINT` | 291 | 全部 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `NAMED_ATTACK_NAMED` | 271 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acts.py |
| 已对拍 | `CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION` | 259 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py:face |
| 已对拍 | `MOVE_CAMERA_TO` | 255 | a1 a2 a4 a6 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_camera.py |
| 不涉及 | `OBJECT_CREATE_RADAR_EVENT` | 254 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `UNIT_IDLE_FOR_SECONDS` | 237 |  | tests/test_simbench.py::test_scripts1_idle_for_seconds_drops_the_move |
| 已对拍 | `TEAM_TRANSFER_TO_PLAYER` | 235 |  | tests/test_simbench.py::test_scripts1_a_team_handed_over_drops_its_move |
| 已对拍 | `NAMED_TRANSFER_OWNERSHIP_PLAYER` | 231 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_invuln.py |
| 已对拍 | `INCREMENT_COUNTER` | 229 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_activate.py |
| 已对拍 | `UNIT_CHANGE_OBJECT_STATUS:SHROUD_REVEAL_TO_ALL` | 218 |  | tests/test_simbench.py::test_acts_flow_as_the_bench |
| 已对拍 | `PLAYER_SET_MAX_PLAYER_POWER_POINTS` | 206 | a4 a5 a7 | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 已对拍 | `NAMED_KILL` | 204 | a4 a5 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aihome.py |
| 已对拍 | `TEAM_HUNT` | 203 |  | tests/test_simbench.py::test_acts_y_hunt_as_the_bench |
| 已对拍 | `CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT` | 196 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_ref.py |
| 已对拍 | `LINK_MISSION_OBJECTIVE_TO_WAYPOINT` | 194 | a1 a3 a4 a5 a6 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts5.py |
| 已对拍 | `NAMED_FOLLOW_WAYPOINTS` | 192 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_wayatk.py |
| 已对拍 | `TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY` | 186 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_spncancel.py |
| 已对拍 | `TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS` | 184 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_wayatk.py |
| 不涉及 | `FADE_OUT_TO_BLACK` | 177 |  | 纯表现（名字规则） |
| 不涉及 | `FADE_IN_FROM_BLACK` | 176 |  | 纯表现（名字规则） |
| 不涉及 | `NAMED_FLASH` | 173 | a9 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `SET_COUNTER` | 171 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_activate.py |
| 已对拍 | `UNIT_CHANGE_OBJECT_STATUS:SKIRMISH_AI_DO_NOT_ATTACK` | 171 |  | tests/test_simbench.py::test_acts_flow_as_the_bench |
| 不涉及 | `NAMED_SHOW_INFOBOX` | 166 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `TEAM_USE_COMMANDBUTTON_ABILITY` | 162 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_parking.py |
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
| 已对拍 | `TEAM_KILL` | 121 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_conds.py |
| 已对拍 | `SET_TIMER` | 119 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `NAMED_STOP` | 118 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_emp.py |
| 已对拍 | `UNIT_TELEPORT_TO_WAYPOINT` | 118 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aidefense.py |
| 不涉及 | `PLAYER_CAMERA_MOVE_TO` | 117 |  | 纯表现（名字规则） |
| 已对拍 | `ATTACK_MOVE_TEAM_TO` | 116 | a1 a3 a5 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_wayatk.py |
| 已对拍 | `PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT` | 116 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8b.py |
| 已对拍 | `TEAM_IDLE_FOR_SECONDS` | 114 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 已对拍 | `PLAYER_SET_BASE_POWER` | 112 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attackassist.py |
| 已对拍 | `PLAYER_TOGGLE_RESOURCE_SHARING` | 111 |  | tests/test_simbench.py::test_share_all_as_the_bench |
| 不涉及 | `UNIT_SET_MODELCONDITION_GENERIC` | 111 | a7 | 纯表现：设模型状态只换画法。原版脚本设的是 SUPPRESSED（a01 摆拍枪战的趴下动作），SDK 数据里读 SUPPRESSED 的只有绘制模块的 ConditionsYes；我们 a7 设的 USER_1 只有自由号的充能画法读 |
| 不涉及 | `PLAY_SOUND_AS_AI_COCOMMANDER_DIALOG` | 109 |  | 纯表现（名字规则） |
| 不涉及 | `TEAM_CREATE_RADAR_EVENT` | 107 |  | 纯表现（名字规则） |
| 已对拍 | `MAP_REVEAL_PERMANENTLY_AT_WAYPOINT` | 105 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 不涉及 | `CAMERA_LETTERBOX_BEGIN` | 104 | a4 | 纯表现（名字规则） |
| 已对拍 | `NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY` | 103 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aibasedef.py |
| 已对拍 | `TEAM_ALLOW_AI_AUTOACQUIRE` | 103 |  | tests/test_simbench.py::test_acts_flow_as_the_bench |
| 已对拍 | `SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER` | 101 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_ref.py |
| 不涉及 | `RESET_CAMERA` | 100 |  | 纯表现（名字规则） |
| 不涉及 | `CAMERA_LETTERBOX_BEGIN_WITH_RADAR` | 98 |  | 纯表现（名字规则） |
| 已对拍 | `SET_RANDOM_COUNTER` | 97 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `PLAYER_SET_PLAYER_POWER_POINTS` | 95 | a4 a5 a7 | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 已对拍 | `SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER` | 94 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts7.py |
| 已对拍 | `MAP_REVEAL_ALL_PERM` | 89 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `MAP_SWITCH_BORDER` | 87 | a1 a2 a3 a4 a5 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 已对拍 | `NAMED_SET_DISABLED` | 86 |  | tests/test_simbench.py::test_acts_flow_as_the_bench |
| 不涉及 | `NAMED_REMOVE_INFOBOX` | 83 |  | 纯表现（名字规则） |
| 已对拍 | `TEAM_FOLLOW_WAYPOINTS` | 83 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_waypath.py |
| 已对拍 | `SKIRMISH_AI_MAKE_BASE` | 82 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiomove.py |
| 已对拍 | `SET_RANDOM_MSEC_TIMER` | 77 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `TEAM_ATTACK_NAMED` | 76 | a2 a4 a7 a8 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_reorder.py |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateEjectPassengersSpecialPowerUntargeted` | 75 |  | tests/test_simbench.py::test_acts_btn_all_as_the_bench |
| 已对拍 | `SKIRMISH_AI_USE_REPAIRS` | 75 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aipullback.py |
| 不涉及 | `NAMED_OUTLINE` | 74 |  | 纯表现（名字规则） |
| 不涉及 | `FLASH_UI_UNIT_ABILITY_BUTTON` | 72 |  | 纯表现（名字规则） |
| 已对拍 | `MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT` | 72 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 已对拍 | `PLAYER_GIVE_MONEY` | 72 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acts.py |
| 已对拍 | `UNIT_SET_TEAM` | 72 | 全部 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `TEAM_CHANGE_OBJECT_STATUS` | 71 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8b.py |
| 已对拍 | `TEAM_GARRISON_TEAM_INSTANTLY` | 68 |  | tests/test_simbench.py::test_acts_more_as_the_bench |
| 不涉及 | `UNIT_CLEAR_MODELCONDITION` | 68 |  | 纯表现：同 UNIT_SET_MODELCONDITION_GENERIC，清掉画法状态 |
| 不涉及 | `CREATE_UNNAMED_ON_TEAM_AT_NAMED_OBJECT_LOCATION` | 67 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `LINK_MISSION_HOT_SPOT_TO_OBJECT` | 67 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_conds.py:sight |
| 已对拍 | `SKIRMISH_AI_USE_REBUILD_SYSTEM` | 67 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiswitch.py |
| 已对拍 | `TEAM_MERGE_INTO_TEAM` | 67 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 已对拍 | `NAMED_HUNT` | 66 |  | tests/test_simbench.py::test_acts_w_hunt_as_the_bench |
| 不涉及 | `TEAM_FLASH` | 66 |  | 纯表现（名字规则） |
| 已对拍 | `TEAM_SET_OVERRIDE_RELATION_TO_PLAYER` | 64 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 已对拍 | `SET_MISSION_HOT_SPOT_ACTIVENESS` | 61 |  | tests/test_simbench.py::test_conds_sight_as_the_bench |
| 已对拍 | `UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION` | 60 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aipullback.py |
| 已对拍 | `NAMED_FORCE_ATTACK_NAMED` | 59 |  | tests/test_simbench.py::test_acts_flow_as_the_bench |
| 已对拍 | `NAMED_FORCE_ATTACK_WAYPOINT` | 59 |  | tests/test_simbench.py::test_acts_more_as_the_bench |
| 不涉及 | `PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM` | 59 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN）；台上量过（docs/engine/inventory-levels-a.md），没有测试跑这个台子 |
| 不涉及 | `SET_REFERENCE_TO_RANDOM_TEAM_MEMBER` | 59 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `MAP_REVEAL_ALL_UNDO_PERM` | 58 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 不涉及 | `SHOW_MILITARY_CAPTION` | 58 | 全部 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 已对拍 | `NAMED_FOLLOW_WAYPOINTS_EXACT` | 56 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_waypath.py |
| 已对拍 | `UNIT_EXECUTE_SEQUENTIAL_SCRIPT` | 56 |  | tests/test_simbench.py::test_acts_seq_as_the_bench |
| 已对拍 | `NAMED_SET_MAX_HEALTH` | 53 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_maxhealth.py |
| 不涉及 | `TOGGLE_RADAR_UI` | 53 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `DISPLAY_TUTORIAL_TEXT` | 52 |  | 纯表现（名字规则） |
| 已对拍 | `PLAY_SOUND_EFFECT` | 51 | a4 | 只记进时间线（sim.SHOWN）；台上量过、测试对拍：checks/engine_dialog.py |
| 已对拍 | `TEAM_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT` | 51 |  | tests/test_simbench.py::test_acts_btn_all_as_the_bench |
| 已对拍 | `DECREMENT_COUNTER` | 50 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts3.py |
| 已对拍 | `DISPLAY_COUNTDOWN_TIMER` | 50 | a4 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 已对拍 | `SELL_OBJECT` | 50 |  | tests/test_simbench.py::test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames |
| 已对拍 | `TEAM_ATTACK_TEAM` | 50 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateEjectPassengersSpecialPower` | 49 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_transport.py |
| 不涉及 | `FLASH_UI_BUILD_BUTTON` | 48 |  | 纯表现（名字规则） |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JAAVT1_Transform` | 48 |  | tests/test_simbench.py::test_acts_btn_all_as_the_bench |
| 未做 | `SET_UNIT_REFERENCE` | 48 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_ATTACK_FOLLOW_WAYPOINTS` | 47 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_wayatk.py |
| 已对拍 | `NAMED_RECEIVE_UPGRADE` | 47 | a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_invuln.py |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanBaseDefenseEgg` | 46 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_eggcmd.py |
| 已对拍 | `TEAM_SET_STANCE` | 45 |  | tests/test_simbench.py::test_acts_flow_as_the_bench |
| 不涉及 | `NAMED_CUSTOM_COLOR` | 44 |  | 纯表现（名字规则） |
| 已对拍 | `HIDE_COUNTDOWN_TIMER` | 43 | a4 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_SovietAntiGroundAircraftEvacuate` | 43 |  | tests/test_simbench.py::test_acts_btn_all_as_the_bench |
| 已对拍 | `PLAYER_SET_OVERRIDE_RELATION_TO_TEAM` | 43 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleSpiderHole` | 41 |  | tests/test_simbench.py::test_acts_btn_all_as_the_bench |
| 已对拍 | `PLAYER_SET_SPECIAL_POWER_COUNTDOWN` | 41 |  | tests/test_simbench.py::test_acts_u_as_the_bench |
| 不涉及 | `FOR_EACH_PLAYER_OBJECT_EXECUTE_SCRIPT` | 39 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JAIV_Transform` | 38 |  | tests/test_simbench.py::test_acts_btn_all_as_the_bench |
| 已对拍 | `TECHTREE_MODIFY_BUILDABILITY_OBJECT` | 38 |  | tests/test_simbench.py::test_acts_u_as_the_bench |
| 不涉及 | `EVALUATE_SCRIPT` | 35 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `SKIRMISH_AI_TRANSFER_ALL` | 35 |  | tests/test_simbench.py::test_acts_z_all_as_the_bench |
| 已对拍 | `UNIT_CONTEXT_SENSITIVE_ATTACK` | 35 |  | tests/test_simbench.py::test_acts_u_as_the_bench |
| 不涉及 | `FOR_EACH_TEAM_MEMBER_EXECUTE_SCRIPT` | 34 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `LINK_MISSION_HOT_SPOT_TO_WAYPOINT` | 34 |  | 纯表现（名字规则）；Sim.act / Sim.cond 有分支 |
| 已对拍 | `NAMED_DAMAGE` | 34 |  | tests/test_simbench.py::test_sell_a_killed_building_stays_paid_and_a_building_unpacking_is_not_sold |
| 不涉及 | `FLASH_MOUSE_HUD_FIXED_ELEMENT` | 33 |  | 纯表现（名字规则） |
| 未做 | `GATE_OPEN` | 33 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `MAP_REVEAL_PERMANENTLY_IN_TRIGGER` | 33 |  | tests/test_simbench.py::test_acts_more_as_the_bench |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_DisguisedEvacuate` | 33 |  | tests/test_simbench.py::test_acts_tgl_all_as_the_bench |
| 已对拍 | `STOP_TIMER` | 33 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_timer.py |
| 已对拍 | `TEAM_SET_OVERRIDE_RELATION_TO_TEAM` | 33 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 已对拍 | `UNIT_CHANGE_OBJECT_STATUS:NO_ATTACK` | 33 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `ALLOW_DISALLOW_ONE_UPGRADE` | 32 |  | tests/test_simai_upgrade_c.py::test_upgrade_ban_holds_until_the_allow_as_the_bench |
| 已对拍 | `NAMED_ATTACK_TEAM` | 32 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts9.py |
| 已对拍 | `UNIT_KILL_ALL_IN_AREA` | 32 |  | tests/test_simbench.py::test_acts_more_as_the_bench |
| 已对拍 | `ATTACK_MOVE_TEAM_TO_NAMED_OBJECT` | 31 |  | tests/test_simbench.py::test_acts_more_as_the_bench |
| 已对拍 | `CREATE_REINFORCEMENT_TEAM_AT_UNIT_POSITION` | 31 |  | tests/test_simbench.py::test_reinforcement_at_a_unit_as_the_bench |
| 已对拍 | `SKIRMISH_AI_SET_FAVORED_ENEMY` | 31 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aifav.py |
| 已对拍 | `NAMED_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT` | 30 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_waypath.py |
| 已对拍 | `UNIT_CHANGE_OBJECT_STATUS:SKIRMISH_AI_DO_NOT_TAKE` | 30 |  | tests/test_simbench.py::test_acts_u_as_the_bench |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleAlliedArtilleryVehicle` | 29 |  | 只记进时间线，没有效果 |
| 不涉及 | `PLAYER_ALLOWED_TOBE_COOPAI` | 29 |  | A219 读程序：只写 AI 脑的"可当合作 AI"位；读它的只有合作 AI 的界面 / 语音、玩家挑合作伙伴、关掉时取消合作 AI 正执行的玩家指令；模拟器的玩家没有给盟友下令的命令，脚本读不到它（同下一条） |
| 已对拍 | `SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER` | 29 | a1 a2 a3 a4 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiopen.py |
| 不涉及 | `DESELECT` | 28 |  | 纯表现（名字规则） |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_CAMPAlliedBomberDrop2` | 28 |  | A224-A226 engine_acts_mix:all、engine_acts_drop / _ally:own、engine_acts_wet:all、A266 engine_acts_edge:edge（store 放地图边上 / 界外，假设 D）：七局都没出轰炸机；A226 PLAYER_TRIGGERED_SPECIAL_POWER 看到按钮和按名字放都算放了（人类、电脑的 store 都是），所以卡在 OCL 生成那步（CREATE_AT_EDGE_NEAR_SOURCE），原因未明；模拟器只记施放、不出东西 |
| 不涉及 | `SOUND_DISABLE_TYPE` | 28 |  | 纯表现（名字规则） |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackAlliedMCV` | 27 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_substorage.py |
| 不涉及 | `PLAYER_CAMERA_MOVE_TO_NAMED` | 27 |  | 纯表现（名字规则） |
| 已对拍 | `TEAM_GARRISON_SPECIFIC_BUILDING` | 27 |  | tests/test_simbench.py::test_acts_tel_as_the_bench |
| 已对拍 | `TEAM_SET_PLAYERS_NEAREST_UNIT_OF_TYPE_TO_REFERENCE` | 27 |  | tests/test_simbench.py::test_acts_tel_as_the_bench |
| 已对拍 | `TEAM_STOP` | 27 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 已对拍 | `TEAM_TELEPORT_TO_WAYPOINT` | 27 |  | tests/test_simbench.py::test_acts_tel_as_the_bench |
| 已对拍 | `MAP_UNDO_REVEAL_PERMANENTLY_IN_TRIGGER` | 26 |  | tests/test_simbench.py::test_acts_more_as_the_bench |
| 不涉及 | `NAMED_FLASH_WHITE` | 26 |  | 纯表现（名字规则） |
| 不涉及 | `RADAR_CREATE_EVENT` | 26 |  | 纯表现（名字规则） |
| 已对拍 | `TEAM_GUARD_AREA_FROM_POSITION` | 26 |  | tests/test_simbench.py::test_acts_v_as_the_bench |
| 不涉及 | `TEAM_SET_DISABLED` | 26 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `LINK_MISSION_OBJECTIVE_TO_OBJECT_WITH_CATEGORY` | 25 |  | 纯表现（名字规则） |
| 已对拍 | `NAMED_GARRISON_SPECIFIC_BUILDING` | 25 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_bankcapture.py |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JapanBaseDefenseToggleBinaryWeapon` | 25 |  | tests/test_simbench.py::test_acts_twr_t_as_the_bench |
| 已对拍 | `PLAYER_SET_MONEY_CAP` | 25 |  | tests/test_simbench.py::test_money_cap_holds_harvest_income_as_the_bench |
| 已对拍 | `UNIT_ALLOW_AI_AUTOACQUIRE` | 25 |  | tests/test_simbench.py::test_acts_tel_as_the_bench |
| 已对拍 | `UNIT_SET_MODELCONDITION` | 25 |  | tests/test_simbench.py::test_acts_v_as_the_bench |
| 已对拍 | `DISPLAY_COUNTER` | 24 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_modulebatch.py |
| 不涉及 | `HIDE_COUNTER` | 24 |  | 纯表现（名字规则） |
| 已对拍 | `PLAYER_ALLOW_AI_AUTOACQUIRE` | 24 |  | tests/test_simbench.py::test_acts_v_as_the_bench |
| 不涉及 | `PLAY_SOUND_AS_AI_COCOMMANDER_DIALOG_WITH_SUBTITLE` | 24 |  | 纯表现（名字规则） |
| 不涉及 | `SETUP_CAMERA` | 24 |  | 纯表现（名字规则） |
| 不涉及 | `SET_COOP_AI_COMMAND_UI_ENABLED` | 24 | a4 | 纯界面：开关玩家给盟友 AI 下令的按钮；模拟器的玩家没有给盟友下令的命令，开关无从起作用（以后加了这个命令再算） |
| 不涉及 | `LINK_MISSION_OBJECTIVE_TO_WAYPOINT_WITH_CATEGORY` | 23 |  | 纯表现（名字规则） |
| 已对拍 | `PLAYER_GRANT_SPECIAL_POWER` | 23 |  | tests/test_simbench.py::test_acts_u_as_the_bench |
| 已对拍 | `PLAYER_TRANSFER_OWNERSHIP_PLAYER` | 23 |  | tests/test_simbench.py::test_acts_x_own_as_the_bench |
| 已对拍 | `TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE` | 23 |  | tests/test_simbench.py::test_acts_v_as_the_bench |
| 不涉及 | `HIDE_TUTORIAL_TEXT` | 22 |  | 纯表现（名字规则） |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NO_ATTACK_FROM_AI` | 22 |  | 状态位 NO_ATTACK_FROM_AI 只记下来 |
| 不涉及 | `MOVE_NAMED_UNIT_TO_UNIT` | 21 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `NAMED_USE_LOGIC_COMMAND_ABILITY_ON_NAMED_POSITION` | 21 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `SELECT_OBJECT` | 21 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_eyes.py |
| 已对拍 | `TEAM_FOLLOW_WAYPOINTS_EXACT` | 21 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_waypath.py |
| 不涉及 | `MOVE_CAMERA_TO_NAMED` | 20 | a5 a7 | 纯表现（名字规则）；Sim.act / Sim.cond 有分支 |
| 未做 | `REDALERT_DISABLE_THREAT_LEVEL_BONUS` | 20 |  | C两局engine_threatbonus:a/b：A仅到第三批损失，不能用捕获秒作任务秒；B改逻辑帧闸门并交换禁用方，实测双方均第2893帧升二级（含禁用方），模型均5400。tests/test_threatbonus_bench_c.py具名阶段读数回放通过，协议升级读数strict xfail保留。未证明动作关闭协议经验倍率，不写无操作实现；缺同帧玩家threat/等级/倍率及单位经验奖励消费，整项未晋升。见work/re/c_threatbonus_report.md |
| 不涉及 | `UNIT_EXECUTE_SEQUENTIAL_SCRIPT_COPY` | 20 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `CAMERA_FOLLOW_NAMED` | 19 |  | 纯表现（名字规则）；Sim.act / Sim.cond 有分支 |
| 已对拍 | `COUNTER_MATH_COUNTER` | 19 | a1 a2 a3 a6 a7 a9 | 引擎模型核心；台上量过、测试对拍：checks/engine_attach.py |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_SmokeBombSpecialPower` | 19 |  | tests/test_simbench.py::test_acts_mix_all_as_the_bench |
| 已对拍 | `PLAYER_DISABLE_BASE_CONSTRUCTION` | 16 |  | tests/test_basegate_bench_a.py::test_aibgate_disabled_ai_spends_nothing_and_builds_nothing_until_enabled；A269 aibgate:a（B的aiskirm图，s1盟军AI 10秒醒、50000）：开局禁用，醒后到第1054帧钱50000、建筑数1，不下任何建筑单；70秒恢复后f1054起付款、f1208第二栋（对照aiskirm d醒后11秒第二栋）。模拟simai.build拒结构单：f1065/f1215。tests/test_basegate_bench_a.py按名回放。C的engine_baseban：日本核心（UNIT_BUILD）不受此门；A的engine_basegate:a：脚本按盟军建造厂电厂按钮两边都不扣钱，玩家建造厂队列量不到（未模拟）。This Player/All Players范围仍gap |
| 已对拍 | `PLAYER_ENABLE_UNIT_CONSTRUCTION` | 16 |  | tests/test_unitban_bench_c.py::test_unitban_enable_resumes_partly_paid_engineer；C两局engine_unitban:a/b具名玩家盟军工程师原生按钮：禁用期可排队但不扣款；恢复后付款/进度续跑，不退款不重置。a第150帧甲2000/乙1603，恢复后第198帧1843/1500/10，末1000/1000/33；b第101至180帧甲保持1800，第195帧1753/1500/10、第285帧1500/1500/11。tests/test_unitban_bench_c.py按名回放实读；第二笔队列付款提前10帧留strict xfail。仅此玩家/工程师切片已量，其他模板门禁INFERRED，UI拒绝、升级、建筑、AI及This Player/All Players范围仍gap；见work/re/c_unitban_report.md |
| 不涉及 | `PLAY_SOUND_EFFECT_AT_TEAM` | 16 |  | 纯表现（名字规则） |
| 不涉及 | `TOGGLE_LOCK_CURRENT_SELECTION` | 16 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `UNIT_SET_MODELCONDITION_FOR_DURATION` | 16 |  | tests/test_modeldur_bench_c.py::test_modeldur_real_bits_expire_after_measured_frames；C engine_modeldur:a真实UNIT_HAS_MODELCONDITION查询：3/7秒USER_1分别为真46/106逻辑帧，b的1/2秒为真16/31帧，均含到期边界；空白阴性始终无位，永久阳性保持，状态码11→10→8。tests/test_modeldur_bench_c.py按名回放同帧四计数器。仅正持续时间、第四参数1.0、独立USER_1写入/到期切片；其他位推广INFERRED，重复/覆盖、零时长、第四参数其他值及原生生产者均gap；见work/re/c_modeldur_report.md |
| 已对拍 | `UNIT_STOP_SEQUENTIAL_SCRIPT` | 16 |  | tests/test_seqstop_bench_c.py::test_seqstop_clears_pending_scripts_keeps_move_and_accepts_fresh_script；C engine_seqstop:a真实继续/停止对照：f282步骤111/1、到达码3，f308新排脚本后111/1001/3，f360保持。停止清当前及后排脚本，不取消已发移动，新脚本可再执行；tests/test_seqstop_bench_c.py按名回放四计数器。仅存活具名单车移动切片；精确移动/idle时序、自停、循环、死亡/缺失单位及其他订单仍gap；其他宿主推广INFERRED；见work/re/c_seqstop_report.md |
| 已对拍 | `NAMED_EXIT_BUILDING` | 15 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_enter.py |
| 已对拍 | `TEAM_UPGRADE` | 15 |  | tests/test_teamup_bench_c.py::test_teamup_real_query_and_consumer_apply_only_to_current_team；C engine_teamup:a真实玩家升级查询+守护者状态位：f150本队/异队/查询0/0/0，f157授予后3/0/3，f248移除一人后2/0/1，f332再授予3/0/3；同玩家异队和敌方异队均无位。tests/test_teamup_bench_c.py按名逐实读帧回放；仅当前存活显式队伍OBJECT升级派发/消费者切片，j05地图私有升级效果、未来成员、死/缺队伍和AI队伍实例仍gap；其他宿主推广INFERRED；见work/re/c_teamup_report.md |
| 已对拍 | `UNIT_SET_HEALTH` | 15 | a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aibuilding.py |
| 已对拍 | `GIVE_PLAYER_UPGRADE` | 14 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_spngp.py |
| 已对拍 | `MARK_MISSION_OBJECTIVE_COMPLETED` | 14 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_markobj.py |
| 不涉及 | `MOVIE_PLAY_FULLSCREEN` | 14 |  | 纯表现（名字规则） |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleEnergizedArmorSpecialPower` | 14 |  | tests/test_simbench.py::test_acts_mix_all_as_the_bench |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanEgg` | 14 |  | tests/test_eggcmd_bench_c.py::test_eggcmd_naval_legacy_and_concrete_buttons_match_display_counters；C engine_eggcmd:a与engine_eggnav:a两局：零售使用的防御/电厂/船厂三种核心，旧通用按钮均留原处；专用防御/船厂按钮到点展开，未下令对照留家。地面f249/393/560建筑位/存活位/原处位4/15/11，水域f247/390/496为2/7/5；tests/test_eggcmd_bench_c.py按名逐实读帧回放。Sim.act仅三种实测宿主且无地图本地定义时显式无操作，不映射专用展开；地图局部按钮、缺失/死亡宿主及其他宿主仍gap，跨宿主推广INFERRED；见work/re/c_eggcmd_report.md、work/re/c_eggnav_report.md |
| 已对拍 | `PLAYER_KILL` | 14 |  | tests/test_playerkill_bench_c.py::test_playerkill_owned_units_and_buildings_match_bench；C engine_playerkill:a一局：目标Soviet_4守护者/电厂死亡，Player_1与Soviet_5同类对照保留；空Soviet_6调用和重复调用未误伤。f45/61/75单位位/建筑位/死亡位7/7/0，f83/152/287为5/5/0；tests/test_playerkill_bench_c.py按名逐实读逻辑帧回放四计数器。仅所属普通对象清理切片已对拍；玩家失败/淘汰、保护对象、容器/子体、死亡瞬间和其他模板推广仍gap或INFERRED；见work/re/c_playerkill_report.md |
| 已对拍 | `PLAYER_SET_ALL_UNITS_TO_FLEE` | 14 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_runoffmap.py |
| 不涉及 | `SET_REFERENCE_TO_FIRST_TEAM_MEMBER_IN_AREA` | 14 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES` | 14 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiswitch.py |
| 未做 | `UNIT_EXECUTE_SEQUENTIAL_SCRIPT_LOOPING` | 14 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `DISABLE_MOUSE_HUD_FIXED_ELEMENT` | 13 |  | C engine_mousehud:a/b两局SellButton禁用/开场禁用后恢复对照：末f356/f414均存活位5、资金2400；脚本出售位2消失、原生点击位1和未操作位4保留。B原生出售阳性预测4/2800未成立，tests/test_mousehud_bench_c.py保留一strict xfail；具名全三计数器负基线回放不能证明UI门。存档画面A按钮灰/B按钮亮且目标被选中；每次bench_click间Esc可能取消卖出模式（INFERRED）。cnv_result只有点击坐标及三计数器，没有SellButton enabled、卖出模式接受或拒绝字段；其他固定元素未量，不据余额或负基线登记纯表现。两局耗完，保持未做；见work/re/c_mousehud_report.md |
| 不涉及 | `SET_LAST_CREATED_UNIT_TO_REFERENCE` | 13 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `TEAM_EXIT_ALL_BUILDINGS` | 13 |  | tests/test_teamexit_bench_c.py::test_teamexit_mixed_building_and_transport_match_bench；C engine_teamexit:a混装建筑/运输车一局：本队征召兵退出公寓和牛蛙，同容器异队保留；队外成员/两宿主均存活，空队伍与重复调用无误伤。f44..74本队驻/异队驻/存活位3/3/127，f82..287为0/3/127；tests/test_teamexit_bench_c.py按名逐33个实读逻辑帧回放四计数器。仅显式存活队伍普通退出切片；精确出门位置/时序、运输抛射、取消进驻中订单、死/缺队伍及AI实例仍gap，其他模板推广INFERRED；见work/re/c_teamexit_report.md |
| 未做 | `GATE_CLOSE` | 12 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_GARRISON_NEAREST_BUILDING` | 12 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_SET_SPECIAL_POWER_COUNTDOWN` | 12 |  | C两局engine_namedcount:a/engine_namedvac:a：三独立玩家宿主，1秒0/2、7秒2/0交换，第三方不操作；铁幕f43..143就绪0、f153..315为7，真空弹f41..148为0、f155..300为3，宿主位均7、零余电位均0。旧零/非零预测被否定；缺真实剩余冷却/READY刷新与宿主初始化同帧字段，秒数与作用域未闭环。两个按名逐31实读帧回放strict xfail，未改模型、未晋升；假设表及字段缺口见work/re/c_namedcount_report.md |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleAfterburners` | 12 |  | tests/test_simbench.py::test_acts_tgl_all_as_the_bench |
| 不涉及 | `OPTIONS_SET_OCCLUSION_MODE` | 12 |  | 纯表现（名字规则） |
| 已对拍 | `PLAYER_SELL_EVERYTHING` | 12 |  | tests/test_sellall_bench_c.py::test_sellall_owner_refund_and_repeat_match_bench；C engine_sellall:a/b显式玩家交换对照：所属普通盟军电厂退款400一次、SOLD后消失，三方守护者及异玩家电厂保留；空玩家与重复调用无额外退款。tests/test_sellall_bench_c.py按名逐实读逻辑帧回放资金码/存活位/出售位/逻辑帧。仅显式玩家单电厂切片已量，多建筑枚举和其他模板推广INFERRED；不可售/受损/展开中/队列/驻军及This Player、All Players仍gap；见work/re/c_sellall_report.md |
| 已对拍 | `SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER` | 12 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acts.py |
| 已对拍 | `TEAM_GARRISON_NEAREST_BUILDING` | 12 |  | tests/test_teamgarr_bench_c.py::test_teamgarr_nearest_and_team_scope_match_bench；C engine_teamgarr:a/b两栋空公寓最近选择：建筑摆放顺序不变，仅步兵东移；本队两名征召兵进最近楼，同玩家异队留外，空队伍/重复调用无误伤。最终进驻位/楼归属/存活位分别3/1/31与3/2/31；tests/test_teamgarr_bench_c.py按名回放实读逻辑帧的动作前及稳定窗口。仅显式普通步兵与空楼选择切片；逐成员距离及其他模板推广INFERRED，队伍中心/等距/搜索范围、容量/敌属/损坏楼/AI实例和入门时序仍gap；见work/re/c_teamgarr_report.md |
| 未做 | `TEAM_MOVE_TO_NEAREST_OBJECT_OF_KINDOF_OWNED_BY_PLAYER` | 12 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `DISABLE_JOYPAD_COMMANDBAR_BUTTON` | 11 |  | C engine_joypad:a一局17组读数f40..182，原版buttonopenplayertechstore/buttonaiassaultdirective未操作、禁用、分步恢复的脚本阶段0/1/2/3均出现，未操作电厂始终1，末3/1/182。tests/test_joypad_bench_c.py仅锚定具名原始读数，不冒充完整模型回放或原生输入接受。cnv_result仅脚本阶段/存活/逻辑帧，index仅id/second/note/view，无Joypad元素enabled、输入accepted/rejected字段；台子仅键鼠注入，XInput四槽未连接。PC路径无消费者仅INFERRED，不用鼠标或余额替代阳性，不登记纯表现。一局后缺真实入口/观测而暂停，不耗相同第二局；见work/re/c_joypad_report.md |
| 不涉及 | `FLASH_JOYPAD_COMMANDBAR_BUTTON` | 11 |  | 纯表现（名字规则） |
| 不涉及 | `FLASH_JOYPAD_HUD_FIXED_ELEMENT` | 11 |  | 纯表现（名字规则） |
| 已对拍 | `NAMED_REMOVE_UPGRADE` | 11 | a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_invuln.py |
| 不涉及 | `ORE_NODE_SET_MAX_GATHER_VALUE` | 11 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ArcherArrowBarrageSpecialPower` | 10 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanMCV` | 10 |  | tests/test_jpndeploy_bench_c.py::test_jpndeploy_waypoint_and_untouched_control_match_bench；C engine_jpndeploy:a一局：两辆普通日本MCV到东400路径点展开，未下令第三车留家；f256..501目标区建造场/名称存活/原处MCV位码3/7/4。tests/test_jpndeploy_bench_c.py按名回放动作前及事前预测f300之后稳定窗口实读逻辑帧四计数器；现有order_unpack匹配，无模型或阈值修改。仅普通活宿主空地切片；精确到达/展开时序、地形阻挡、伤害继承、重复/死亡/缺失宿主仍gap，其他宿主推广INFERRED；见work/re/c_jpndeploy_report.md |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackSovietMCV` | 10 |  | tests/test_sovdeploy_bench_c.py::test_sovdeploy_waypoint_and_untouched_control_match_bench；C engine_sovdeploy:a一局：两辆普通苏联MCV到东400路径点展开，未下令第三车留家；f220..468目标区建造场/名称存活/原处MCV位码3/7/4。tests/test_sovdeploy_bench_c.py按名回放34个动作前及稳定窗口实读逻辑帧四计数器；现有order_unpack即可匹配，未调模型或阈值。仅普通活宿主空地切片；精确到达/展开时序、地形阻挡、伤害继承、重复/死亡/缺失宿主仍gap，其他宿主推广INFERRED；见work/re/c_sovdeploy_report.md |
| 已对拍 | `PLAYER_ENABLE_BASE_CONSTRUCTION` | 10 |  | tests/test_basegate_bench_a.py::test_aibgate_enable_starts_the_ai_base；A269 aibgate:a：禁用的AI在70秒恢复后立即开始下建筑单，f1054付款、f1208第二栋，节奏同刚醒（模拟f1065/f1215）。tests/test_basegate_bench_a.py按名回放；范围同DISABLE（具名AI玩家；玩家建造厂队列、This Player/All Players未量） |
| 不涉及 | `ROTATE_CAMERA` | 10 |  | 纯表现（名字规则） |
| 未做 | `SKIRMISH_AI_CONSIDER_ALL_ENEMIES_WHEN_BUILDING` | 10 |  | C aiallbuildon/off:a两局原生候选/订单对照：共同窗口前6次成功订单同帧同种（两警犬后四标枪），非空候选31/16条、订单307/156条。捕获末逻辑帧598/459，均未到70秒转友闸门；不能比较捕获秒数的存量差。tests/test_allbuild_bench_c.py只锚定具名原生读数，不声称模型等价。bpick/border缺同帧敌方玩家集合、动作开关及参与评分的兵力/资格输入，无法区分默认全敌或消费者未触发；倾向先补观测（INFERRED）。两局耗完，保持未做；见work/re/c_allbuild_report.md |
| 不涉及 | `ZOOM_CAMERA` | 10 |  | 纯表现（名字规则） |
| 已对拍 | `MAP_SHROUD_SET_RESHROUD_TIME` | 9 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleHarpoonSpecialPower` | 9 |  | tests/test_simbench.py::test_acts_tgl_all_as_the_bench |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateLaserGlaiveBlastSpecialPower` | 9 |  | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackAlliedMiner` | 9 |  | Sim.act / Sim.cond 有分支 |
| 已对拍 | `PLAYER_DISABLE_UNIT_CONSTRUCTION` | 9 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_unitban.py |
| 未做 | `PLAYER_TOGGLE_SKIRMISH_AI` | 9 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `SET_COUNTER_TO_NUMBER_OBJECTS_PLAYER_OWNS_WITH_KINDOF` | 9 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_AI_START` | 9 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SOUND_ENABLE_TYPE` | 9 |  | 纯表现（名字规则） |
| 已对拍 | `SUB_FROM_MSEC_TIMER` | 9 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_timer.py |
| 已对拍 | `TEAM_GUARD_AREA` | 9 | a1 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 已对拍 | `TEAM_IDLE_FOR_FRAMECOUNT` | 9 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts8.py |
| 未做 | `TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE_OWNED_BY_PLAYER` | 9 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `COUNTER_MATH_VALUE` | 8 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_attachc4.py:a |
| 已对拍 | `EXIT_SPECIFIC_BUILDING` | 8 |  | tests/test_exitbld_bench_c.py::test_exitbld_named_host_and_mixed_crews_match_bench；C engine_exitbld:a/b两座公寓各装同玩家两队征召兵，交换具名目标西/东；指定楼两队均退出、另一楼仍驻，重复调用无误伤。进驻位15→12/3、区域码始终22、五兵两楼存活位127；tests/test_exitbld_bench_c.py逐实读逻辑帧按名回放四计数器。区域人数包含楼内人员，原仅室外预测2/20保留strict xfail，不改原门槛；仅存活公寓具名退出切片，出门位置沿现有INFERRED近似，精确时序、其他容器/模板、缺名/死亡目标、取消进门仍gap；见work/re/c_exitbld_report.md |
| 不涉及 | `FLASH_UI_PLAYER_POWER_BUTTON` | 8 |  | 纯表现（名字规则） |
| 已对拍 | `MAP_REVEAL_AT_WAYPOINT` | 8 | a1 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_CivilianStructureEvacuate` | 8 |  | tests/test_simbench.py::test_acts_tgl_all_as_the_bench |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleAlliedEngineerHeal` | 8 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_UnPackJapanBaseDefenseEgg` | 8 |  | 只记进时间线，没有效果 |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateJumpSpecialPower` | 8 |  | tests/test_simbench.py::test_dam_all_as_the_bench |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateLeapSpecialPower` | 8 |  | tests/test_simbench.py::test_acts_mix_all_as_the_bench |
| 已对拍 | `RESTART_TIMER` | 8 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_timer.py |
| 已对拍 | `SET_COUNTER_TO_COUNTER` | 8 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_aicombat.py |
| 已对拍 | `SET_PLAYER_KILLS_OF_TYPE_TO_COUNTER` | 8 |  | tests/test_killcount_bench_c.py::test_killcount_native_type_and_player_match_bench；C engine_killcount:a/b原生守护者击杀两征召兵/一守护者，交换Player_1与Soviet_5为击杀者；DISPLAY_COUNTER主步兵/主坦克/另步兵开局0/0/0、末2/1/0，独立脚本杀死未受伤征召兵后不增计数，存活码末240。每帧先写77再查询，证明覆盖；tests/test_killcount_bench_c.py按名回放四读数。原s22存活码窗口差异保留strict xfail，不改门槛。仅具名玩家/单模板/原生直接武器致死和无归属脚本死阴性；列表并集INFERRED，This Player/All Players、换主、友军/间接伤害、争夺最后击和精确帧仍gap，见work/re/c_killcount_report.md |
| 不涉及 | `CAMERA_STOP_FOLLOW` | 7 |  | 纯表现（名字规则） |
| 不涉及 | `FIRE_SPECIAL_POWER_ON_UNIT` | 7 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 未做 | `NAMED_FACE_NAMED` | 7 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateRoarSpecialPower` | 7 |  | tests/test_simbench.py::test_acts_mix_all_as_the_bench |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JAAS_Transform` | 7 |  | 只记进时间线，没有效果 |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleMirageField` | 7 |  | tests/test_simbench.py::test_acts_tgl_all_as_the_bench |
| 不涉及 | `PATH_MUSIC_ENABLE_DYNAMIC_SYSTEM` | 7 |  | 纯表现（名字规则） |
| 推断 | `TEAM_DELETE_LIVING` | 7 |  | Sim.act / Sim.cond 有分支 |
| 已对拍 | `UNIT_CHANGE_OBJECT_STATUS:NON_AUTOACQUIRABLE` | 7 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attach.py |
| 已对拍 | `UNIT_CHANGE_OBJECT_STATUS:UNATTACKABLE` | 7 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attach.py |
| 未做 | `ATTACK_MOVE_TEAM_TO_NEAREST_OBJECT_OF_TYPE_OF_PLAYER` | 6 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `DISABLE_COUNTDOWN_TIMER_DISPLAY` | 6 |  | 纯表现（名字规则） |
| 已对拍 | `NAMED_FACE_WAYPOINT` | 6 |  | tests/test_facewp_bench_c.py::test_facewp_named_heading_and_untouched_control_match_bench；C engine_facewp:a及engine_facewpai:b两局；a仅人类玩家存活位7，无team/tstate朝向，b换AI观察宿主，原生hd甲0→180、乙0→117、未操作0，分别朝西/西北路点。tests/test_facewp_bench_c.py按名回放24组原始稳定朝向（全圈1度容差对应hd整数舍入），并断言存活位7；没有用位置不变替代朝向。转身复用既有移动器速率，精确命令/起转相位、移动中打断、缺名/死亡目标和其他模板仍gap或INFERRED；仅存活静止守护者的具名路点朝向切片，见work/re/c_facewp_report.md |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleBinaryWeapon` | 6 |  | tests/test_simbench.py::test_acts_twr_t_as_the_bench |
| 推断 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanPowerPlantEgg` | 6 |  | Sim.act / Sim.cond 有分支 |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_ActivateRoarSpecialPower` | 6 |  | tests/test_simbench.py::test_acts_wet_all_as_the_bench |
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
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleRiotShieldSpecialPower` | 5 |  | tests/test_simbench_c.py::test_toggle_status_a_press_moves_to_the_next_state_unpack_delays_it_and_a_held_state_takes_no_press |
| 已对拍 | `TEAM_SET_HEALTH` | 5 |  | tests/test_teamhp_bench_c.py::test_teamhp_current_mixed_members_and_controls_match_bench；C engine_teamhp:a/b显式目标队守护者/征召兵血量100→25→75及100→75→25，同玩家异队/另一玩家守护者均保持100；四计数器为两成员实际血量百分比、异队血量组合码100100和逻辑帧。tests/test_teamhp_bench_c.py按名字逐实读帧回放；仅当前存活显式队伍成员的百分比设置切片，未来/死亡/缺名成员、AI实例、边界数值和精确派发相位仍gap，其他模板推广INFERRED；见work/re/c_teamhp_report.md |
| 未做 | `TEAM_SET_MODELCONDITION_FOR_DURATION` | 5 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_SLEEP_STATUS` | 5 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `ENABLE_COUNTDOWN_TIMER_DISPLAY` | 4 |  | 纯表现（名字规则） |
| 未做 | `NAMED_ATTACK_AREA` | 4 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanMinerFromRefinery` | 4 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructSovietAntiVehicleVehicleTech2` | 4 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleJapanFortressShipTransformMode` | 4 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleMagneticArmor` | 4 |  | 只记进时间线，没有效果 |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleShortCircuit` | 4 |  | tests/test_simbench_c.py::test_toggle_status_a_press_moves_to_the_next_state_unpack_delays_it_and_a_held_state_takes_no_press |
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
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_AlliedAntiInfantryVehicleEvacuate` | 2 |  | tests/test_ifvevac_bench_e.py::test_ifvevac_named_measured_snapshots |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JASV_FireKiCannon` | 2 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JapanEngineerSprint` | 2 |  | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateCryoLeapSpecialPower` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_DisguisedEvacuate` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_SovietAntiGroundAircraftEvacuate` | 2 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanNavalYardEgg` | 2 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_eggcmd.py |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_ActivateDisguiseSpecialPower` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_AlliedSupportAircraftShrinkRay` | 2 |  | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_CaptureBuilding` | 2 |  | 只记进时间线，没有效果 |
| 不涉及 | `OVERRIDE_GLOBAL_TERRAIN_HEIGHT` | 2 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 不涉及 | `PATH_MUSIC_FADE_OUT_MUSIC` | 2 |  | 纯表现（名字规则） |
| 不涉及 | `PATH_MUSIC_STOP_MUSIC` | 2 |  | 纯表现（名字规则） |
| 不涉及 | `PLAYER_CAMERA_TETHER_NAMED` | 2 |  | 纯表现（名字规则） |
| 未做 | `PLAYER_DISABLE_FACTORIES` | 2 |  | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SCREEN_SHAKE` | 2 |  | 纯表现（名字规则） |
| 已对拍 | `SET_PLAYER_MONEY_TO_COUNTER` | 2 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acts.py |
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
| 已对拍 | `MARK_MISSION_OBJECTIVE_NOT_COMPLETED` | 1 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_markobj.py |
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
| 已对拍 | `FLAG` | 5099 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_activate.py |
| 已对拍 | `TIMER_EXPIRED` | 3917 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | `CONDITION_TRUE` | 2947 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `NAMED_DESTROYED` | 922 | 全部 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_areaoverlap.py |
| 已对拍 | `PLAYER_HAS_OBJECT_COMPARISON` | 628 | a1 a4 a5 a7 | tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back |
| 已对拍 | `COUNTER` | 577 | 全部 | 引擎模型核心；台上量过、测试对拍：checks/engine_activate.py |
| 已对拍 | `HAS_FINISHED_AUDIO` | 495 |  | tests/test_simbench.py::test_audio_a_dubbed_line_is_done_its_length_after_it_is_heard |
| 已对拍 | `PLAYER_IS_HUMAN_OR_AI_PERSONALITY` | 470 |  | tests/test_simbench.py::test_scripts1_conditions_as_the_bench |
| 已对拍 | `HAS_FINISHED_VIDEO` | 422 |  | tests/test_simbench.py::test_video_a_radar_clip_is_done_after_its_length_full_screen_never |
| 已对拍 | `NAMED_INSIDE_AREA` | 413 | a3 a4 a5 a6 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acts8.py |
| 已对拍 | `SKIRMISH_PLAYER_HAS_UNITS_IN_AREA` | 410 | a1 a3 a4 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_area.py |
| 已对拍 | `NAMED_OWNED_BY_PLAYER` | 397 | a4 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_bankcapture.py |
| 已对拍 | `NAMED_NOT_DESTROYED` | 374 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_activate.py |
| 已对拍 | `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA` | 278 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aidelay.py |
| 已对拍 | `NAMED_ATTACKED_BY_PLAYER` | 150 | a4 a5 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attack.py |
| 已对拍 | `UNIT_HAS_OBJECT_STATUS` | 142 |  | tests/test_simbench.py::test_scripts1_conditions_as_the_bench |
| 已对拍 | `COUNTER_SECONDS` | 141 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `UNIT_HEALTH` | 134 | a2 a4 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_air.py |
| 已对拍 | `MISSION_HOT_SPOT_ACTIVE` | 110 |  | tests/test_simbench.py::test_conds_sight_as_the_bench |
| 已对拍 | `NAMED_DISCOVERED` | 104 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_eyes.py |
| 已对拍 | `TEAM_ATTACKED_BY_PLAYER` | 93 |  | tests/test_simbench.py::test_conds_fight_as_the_bench |
| 已对拍 | `UNIT_HAS_MODELCONDITION` | 88 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_hitreaction_e.py |
| 已对拍 | `TEAM_INSIDE_AREA_PARTIALLY` | 80 |  | tests/test_simbench.py::test_conds_team_as_the_bench |
| 已对拍 | `ENEMY_SIGHTED_BY_TEAM` | 69 |  | tests/test_simbench.py::test_conds_sight_as_the_bench |
| 不涉及 | `IS_OBJECT_OF_TYPE` | 69 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `CAMERA_ENTERED_AREA` | 60 |  | tests/test_simbench.py::test_eyes_all_as_the_bench |
| 已对拍 | `ENEMY_SIGHTED` | 59 |  | tests/test_simbench.py::test_eyes_all_as_the_bench |
| 已对拍 | `COUNTER_COUNTER` | 55 |  | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts6.py |
| 已对拍 | `NAMED_SELECTED` | 50 |  | tests/test_simbench.py::test_share_all_as_the_bench |
| 已对拍 | `TEAM_DISCOVERED` | 47 |  | tests/test_simbench.py::test_conds_sight_as_the_bench |
| 已对拍 | `SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER` | 44 |  | tests/test_simbench.py::test_conds_fight_as_the_bench |
| 已对拍 | `TEAM_HAS_UNITS` | 39 |  | tests/test_simbench.py::test_conds_team_as_the_bench |
| 已对拍 | `NAMED_OUTSIDE_AREA` | 38 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiaesthetics.py |
| 已对拍 | `TYPE_SELECTED` | 38 |  | tests/test_simbench.py::test_eyes_all_as_the_bench |
| 已对拍 | `TEAM_DESTROYED` | 35 |  | tests/test_simbench.py::test_conds_team_as_the_bench |
| 已对拍 | `TEAM_INSIDE_AREA_ENTIRELY` | 33 |  | tests/test_simbench.py::test_conds_team_as_the_bench |
| 未做 | `DISTANCE_BETWEEN_TEAM` | 32 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `PLAYER_HAS_KILLED_TYPE_UNITS` | 29 |  | tests/test_simbench.py::test_conds_fight_as_the_bench |
| 已对拍 | `PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA` | 28 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_slaughter_e.py |
| 已对拍 | `PLAYER_HAS_PLAYER_TECH` | 26 |  | tests/test_simbench.py::test_protocol_rank_two_at_frame_5400 |
| 未做 | `DISTANCE_BETWEEN_OBJ` | 25 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `CURRENT_PLATFORM` | 24 |  | tests/test_simbench.py::test_conds_team_as_the_bench |
| 已对拍 | `PLAYER_HAS_KILLED_NAMED_UNIT` | 24 |  | tests/test_simbench.py::test_conds_fight_as_the_bench |
| 已对拍 | `NAMED_HAS_KILLED_COMPARISON_UNIT_TYPE` | 21 |  | tests/test_simbench.py::test_conds_fight_as_the_bench |
| 已对拍 | `TEAM_CREATED` | 20 |  | tests/test_simbench.py::test_conds_team_as_the_bench |
| 已对拍 | `TEAM_ALL_HAS_OBJECT_STATUS` | 18 |  | tests/test_simbench.py::test_conds_team_as_the_bench |
| 已对拍 | `TYPE_SIGHTED` | 17 |  | tests/test_simbench.py::test_sighted_all_as_the_bench |
| 已对拍 | `SKIRMISH_SPECIAL_POWER_READY` | 16 |  | tests/test_simbench.py::test_acts_u_as_the_bench |
| 已对拍 | `TEAM_SOME_HAVE_OBJECT_STATUS` | 15 |  | tests/test_simbench.py::test_conds_team_as_the_bench |
| 已对拍 | `NAMED_BUILDING_IS_EMPTY` | 13 |  | tests/test_simbench.py::test_sighted_all_as_the_bench |
| 已对拍 | `TEAM_HAS_FEWER_THAN_X_UNITS_WITH_KINDOF` | 12 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `NAMED_ATTACKED_BY_OBJECTTYPE` | 10 |  | tests/test_simbench.py::test_conds_fight_as_the_bench |
| 不涉及 | `OBJECT_IS_DISGUISED_AS_TYPE` | 10 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `PLAYER_HAS_COMPARISON_POWER_POINTS` | 10 |  | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 已对拍 | `TEAM_ATTACKED_BY_OBJECTTYPE` | 10 |  | tests/test_simbench.py::test_conds_fight_as_the_bench |
| 已对拍 | `TEAM_COMPARE_NUM_MEMBERS` | 10 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiskirm.py |
| 不涉及 | `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA_WITH_MODELCONDITION` | 9 |  | 起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了 |
| 已对拍 | `PLAYER_HAS_POWER` | 9 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_infiltrator.py:a |
| 已对拍 | `PLAYER_TRIGGERED_SPECIAL_POWER` | 9 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_cast.py |
| 已对拍 | `BUILT_BY_PLAYER` | 8 |  | tests/test_simbench.py::test_sighted_all_as_the_bench |
| 未做 | `GATE_IS_OPEN` | 8 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `PLAYER_DESTROYED_N_BUILDINGS_PLAYER` | 8 |  | tests/test_simbench.py::test_razed_all_as_the_bench |
| 已对拍 | `PLAYER_HAS_CREDITS` | 8 |  | tests/test_simbench.py::test_conds_team_as_the_bench |
| 已对拍 | `SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED` | 8 |  | tests/test_simbench.py::test_razed_all_as_the_bench |
| 已对拍 | `NAMED_EXITED_AREA` | 7 |  | tests/test_simbench.py::test_conds_team_as_the_bench |
| 未做 | `UNIT_SPECIAL_POWER_READY` | 7 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `PLAYER_HAS_NO_POWER` | 6 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_infiltrator.py:a |
| 已对拍 | `PLAYER_EXCESS_POWER_COMPARE_VALUE` | 5 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_infiltrator.py:a |
| 已对拍 | `PLAYER_TRIGGERED_SPECIAL_POWER_FROM_NAMED` | 5 |  | tests/test_simbench.py::test_cast_all_as_the_bench |
| 已对拍 | `PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS` | 4 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | `PLAYER_TRIGGERED_SPECIAL_POWER_IN_AREA` | 4 |  | tests/test_simbench.py::test_cast_all_as_the_bench |
| 已对拍 | `TEAM_CAN_PATH_TO_WAYPOINT` | 4 |  | tests/test_simbench.py::test_cast_all_as_the_bench |
| 已对拍 | `PLAYER_HAS_COMPARISON_UNIT_KIND` | 3 |  | tests/test_simbench.py::test_kind_all_as_the_bench |
| 未做 | `SKIRMISH_COMMAND_BUTTON_READY_PARTIAL` | 3 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `NAMED_DESTROYED_BY_OBJECTTYPE` | 2 |  | tests/test_simbench.py::test_kind_by_as_the_bench |
| 已对拍 | `NAMED_DYING` | 2 |  | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_crush.py:all |
| 未做 | `PLAYER_HAS_NUMBER_OBJECTS_WITH_MODELCONDITION` | 2 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `PLAYER_LOST_OBJECT_TYPE` | 2 |  | tests/test_simbench.py::test_kind_all_as_the_bench |
| 已对拍 | `TEAM_ENTERED_AREA_PARTIALLY` | 2 |  | tests/test_simbench.py::test_area_all_as_the_bench |
| 未做 | `TEAM_IS_ATTACKED_AND_CANNOT_RETALIATE_ANY` | 2 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `TEAM_OUTSIDE_AREA_ENTIRELY` | 2 |  | tests/test_simbench.py::test_area_all_as_the_bench |
| 未做 | `UNIT_HAS_UPGRADE` | 2 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `BUILDING_GARRISONNED_BY_OBJECT_TYPE` | 1 |  | tests/test_simbench.py::test_area_all_as_the_bench |
| 未做 | `EVAL_TEAM_HEALTH` | 1 |  | Sim.act / Sim.cond 不认识 |
| 已对拍 | `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA_COMPLETELY_BUILT` | 1 |  | tests/test_simbench.py::test_area_all_as_the_bench |
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
| 推断 | `Behaviors/BezierProjectile` | 6 (78) | 全部 | E168 engine_bezier_e:a单发原版V4火箭/仅删Bezier模块对照，f60满血编码3、f240冻结目标HP95/100；tests/test_bezier_bench_e.py按名字以私有物体模型回放，修复无飞行模块仍直接伤害目标的退化分支。公开Sim曲线弹接线、精确飞行/命中帧、追踪/移动目标、碰撞/地形、其他配置仍gap；无模块立即清理为INFERRED，不登记整个模块已对拍。两局原录像秒窗口FAIL保留，冻结帧判定见work/re/e168_bezier.md；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 推断 | `Behaviors/AssignSlavesTargetObjectSpecialPower` | 6 (10) | a2 a4 a5 a7 a8 | E181 engine_assignrace:b一局PASS：f150两组前三受伤目标UNDERGOING_REPAIR编码33，f180只给原版模块组指定第四辆，f360冻结第四辆HP70/20；tests/test_simassignslaves.py::test_repair_assignment_frame_snapshot_matches_named_bench按名回放同帧血量通过，占用模型0对台33保留strict xfail。原版480HP/20HP每秒预测成立，未改治疗率/时间窗；off同时删模块且不发令，不能单独归因模块删除。E66/E67旧捕获时序xfail保留；自动获取、单架子体派发/抢占、状态清理、其他宿主/筛选及精确启动帧仍gap，INFERRED启动相位未扩展，不登记整模块已对拍；见work/re/e181_assignframes.md；例：AlliedConstructionYardRepairBay, AlliedNavalYard |
| 未做 | `Behaviors/TrackDamage` | 6 (9) | a1 a2 a3 a4 a5 a6 a7 a8 | E69静态核实：6个SDK配置均InstantWeaponsOnly=true，TimeToTrack为0/1/2s；现有expected_damage只接来弹，历史伤害仍gap。与C线瞬发历史接口工单重叠，E暂停独立探针；尚无本模块具名实测回放，不登记已对拍、不改分母；见work/re/e_trackdamage_e69.md；例：AlliedAntiNavalScout, AlliedFighterAircraft |
| 未做 | `Behaviors/TrackIncomingWeaponFireBehavior` | 6 (9) | a1 a2 a3 a4 a5 a6 a7 a8 | 部分：engine_inform_probe a/off通知记录回放验证录入、30帧窗口、来源与武器匹配删除和过期清理；精确过期边界INFERRED，原版完整调度/历史伤害仍gap，不靠名字命中晋升整项；例：AlliedAntiNavalScout, AlliedFighterAircraft |
| 已对拍 | `Behaviors/EngineerContain:三国ALLIES` | 6 (7) | a1 a2 a4 a5 a6 a7 a9 | tests/test_simengineer.py::test_engineer_allied_defence_refusal_soviet_japan_as_on_the_bench；已测范围：engine_engineer a/e/f普通进入，三国工程师友军半血防御修满并消耗、满血及敌方拒入且存活，目标归属不变；按完整配置匹配登记6用量/7模板；gap：精确进入帧仍INFERRED；日本单人ALLIES和桥配置保留在未对拍残余行，不借本组登记；例：SovietBaseDefenseGround |
| 已对拍 | `Behaviors/OCLSpecialPower` | 6 (7) | a1 a2 a4 a6 a7 | tests/test_simocl.py::test_iron_curtain_zero_count_ocl_reference；总控第四切片按已测边界收尾：tests/test_simocl.py具名回放engine_oclcurtain/engine_oclnone/engine_oclwrong a，铁幕宿主匹配模块才保护并记事件，删除/改绑模块无保护/事件；engine_oclempty a空声明无保护且事件1；engine_oclcopy a完整原版载荷改名仍保护100/100且事件1；engine_oclzero a仅外层Count=0无保护且事件1。只闭合铁幕派发和零数量不保护边界，未测生成数量/通用生成；其他非零数量/载荷/超武、位置/过滤、按钮/冷却仍gap，继承、等价空声明及格式等价INFERRED，不表示全模块全字段验证；见 work/re/e_ocl_e65.md；例：AlliedSuperWeaponAdvanced, CAMP_PowerStore_AlliedBomberDrop |
| 未做 | `Behaviors/SubStructureStorageBehavior` | 6 (6) | a1 a4 a5 a6 a7 a9 | 6用量/6模板为三国MCV及海军继承型，模块无专用字段；有效配置没有SubStructureBuild；engine_substorage_on/off:a仅测原版空载荷收起/展开对照，不登记已对拍，不据此排除运行时用途；gap：非空载荷、存储数量/父体绑定/保存恢复接受字段未测；普通展开及COPY_UPGRADES不能归因；见 work/re/e182_substorage.md（静态证据work/re/e_substorage_e57.md）；例：AlliedMCV, AlliedMCV_Naval |
| 推断 | `Behaviors/WallBuilderBehavior` | 6 (6) | a1 a2 a4 a6 a7 a9 | 部分：engine_wallinit:a有/无模块对照10/11/10，仅StartInSecondaryModel默认WALL_SEGMENT初始化；6/6权重保留，建墙/连接/段数上限/生死联动及自定义配置仍gap，未登记完整已对拍；见 work/re/e_wallbuilder_e58.md；例：AlliedWallPiece, AlliedWallSegmentPiece |
| 推断 | `Behaviors/PassiveAreaEffectBehavior` | 5 (14) | a3 a4 a7 | E70范围/兵种/状态开关和E74分批治疗具名回放保留。E145单图engine_modulebatch:a：MaxBeneficiaries=1/0两组，早期受益人数1/3、后期3/3，敌方均50%不回血；已补0/1上限，tests/test_simmodulebatch.py按名断言台上读数。E163 engine_areaally:a跨玩家双向友军伤员与己方同步50→100、inactive保持50；b脚本f240友军快照15（己方/友军满血、inactive半血、源满血），tests/test_simareaally_e.py按名回放该快照。已补显式双向Friend治疗资格；两局原捕获秒断言FAIL保留，b末帧448未到f450，敌对/位置快照未测，不据零值推规则。见work/re/e163_areaally.md。具体受益身份次序、共用任务帧相位和SDK换算跳幅INFERRED；E165 engine_areaself:a原自疗预测失败，f61半血快照7/f210满血快照6/存活7；engine_areaselfpeer:a完整PASS，f210源/远端对照/旁步兵/旁工程师HP=50/50/100/100、存活15。已明确排除治疗源自身，允许另一工程师受益；tests/test_simareaself_e.py按名断言两局台上快照，原a预测保留，见work/re/e165_areaself.md。E166 engine_areaoverlap:a叠加满血预测失败，f61/f100/f210=31/29/31；b完整PASS，三快照31/31/31，f100单源与双源均75..80%、关闭50%，四源满血且七物体存活。已支持双满血同规则无限人数源重叠按一次贡献回放，tests/test_simareaoverlap_e.py按名断言两局读数，原a预测保留，见work/re/e166_areaoverlap.md；同规则源身份选择INFERRED。时钟来源/动态创建与重开/调查周期/其他重叠或受伤源/隐式联盟或中立单向关系/自身与人数上限交互/附着无人机/更大上限仍gap，不登记整项已对拍；见work/re/e145_modulebatch.md、e_passive_e74.md；例：AlliedAirfieldRepairDrone, AlliedEngineer |
| 未做 | `Behaviors/EmotionTrackerUpdate` | 5 (7) | a1 a2 a3 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedCommandoTech1, AlliedEngineer |
| 推断 | `Behaviors/InfiltratorContain:RESET` | 5 (6) |  | E195完整RESET配置5用量/6模板；engine_infreset a/b原台末段s21–35/s41–55敌间谍消耗、友军拒入、建筑满血原主且正供电，test_spy_superweapon_reset_entry_as_on_the_bench按名断言。仅苏联铁幕/盟军间谍首次入楼已接；原s11/s31进入窗口和全部就绪读数仍strict xfail，真实冷却未观测，不拟合十秒恢复；进入距离/时钟INFERRED，其他宿主/间谍/重复仍gap。不登记已对拍、不扩大整模块覆盖；见work/re/e195_reset.md；例：SovietSuperWeapon |
| 未做 | `Behaviors/MonitorSpecialPowerTimerUpdate` | 5 (6) |  | E145单图engine_modulebatch:a：原版质子炮宿主有/无模块，设技能就绪后SPECIALPOWER1_READY为1/0，设冷却后0/0。模型倒计时脚本入口和模块就绪输出仍gap；具名回放strict xfail，需A倒计时接口，不按纯表现排除；见work/re/e145_modulebatch.md；例：AlliedSuperWeapon, AlliedSuperWeaponAdvanced |
| 未做 | `Behaviors/AttackAssistResponseBehavior` | 5 (5) | a1 a2 a4 a5 a6 a7 a9 | E144派发诊断：engine_attackassist a两次准备运行均进关前崩溃，无台上读数；最终原版光谱塔宿主配方已修本地模块引用及结构武器掩码，尚未上台，暂停追加运行直至启动原因解释。tests/test_simattackassist.py严格xfail仅保留待验预测，不作已对拍证据；响应武器派发/原版增伤/时序均gap，模型未改；见work/re/e144_attackassist.md；例：AlliedBaseDefenseAdvanced, SovietBaseDefenseAdvanced |
| 未做 | `Behaviors/CaptureSpecialAbilityUpdate` | 5 (5) | a1 a2 a3 a4 a6 a7 a9 | E151 engine_capture:a原版工程师对CaptureFlag中立/敌方/己方和删模块中立四路：归属100、存活1111、前置1，f45..575未换主。原预测111保留；具名测试仅回放负基线，不登记模块效果已对拍。缺命令被模块接受及同帧阶段证据（INFERRED），暂停同输入重跑；见work/re/e151_capture.md；例：AlliedCommandoTech1, AlliedEngineer |
| 推断 | `Behaviors/CommandSetUpgrade` | 5 (5) | a1 a4 a5 a7 | E145单图engine_modulebatch:a：空初始菜单的兵营，授Tech2前产物0/0、授后有/无模块产物1/0。菜单切换解析已有；整链路具名回放strict xfail：生产层factories按未持升级的初始菜单识别工厂，故模型仍0/0，需B接口修复。未晋升整项；见work/re/e145_modulebatch.md；例：AlliedConstructionYard, AlliedOutpost |
| 推断 | `Behaviors/InfiltratorContain:VISION` | 5 (5) | a1 a4 a7 | E196普通VISION完整配置5用量/5模板（同宿主RADAR_FREEZE未测）；engine_infvis a/b/c按名回放敌消耗、友拒入、满血原主与局部揭示稳定窗。日本s18实测0而模型提前揭示，单独保留strict xfail；不拟合延迟、不登记已对拍。进入距离、约5秒激活、半径映射和死亡清理仍INFERRED；精确时钟/其他模板/重复与持久性仍gap；见work/re/e196_vision.md；例：JapanConstructionYard |
| 推断 | `Behaviors/QueueDockBehavior` | 4 (12) | a1 a2 a4 a5 a6 a7 a9 | E164消费D165 dockphase:a/off阶段证据：on装货f156..186、卸货f289..319各30帧，货量250→0；off首次交矿f200同帧异常，不是无效果对照。公开Sim已按继承读取码头模块，矿车选中缺码头矿场时明确报错、禁止模拟成功交矿；卸货结束清空货量。具名tests/test_simqueuedock.py回放拒绝边界、30帧卸250及清货；E180补装货结束才显货250，装货期保持0；装货计时现为29帧对台30帧，独立strict xfail，不改路径时钟迎合读数。整模块不晋升，骨骼/队列/绝对路径时钟仍gap，E152 f786快照保留strict xfail；见work/re/e164_queuedock.md、work/re/e180_queuedock_load.md；例：AlliedRefinery, AlliedRefinery_NoHarvester |
| 推断 | `Behaviors/AutoDepositUpdate` | 4 (8) | a1 a4 a5 a7 | E147 engine_bankcapture:a：中立SwissBank有/无模块两路普通工程师占领，换主并消耗工程师；on奖金750、随后每15游戏帧+5至770，off全0，帧锁定证据1023；具名测试test_simbankcapture按实际读数回放。E146已有归属产钱60/0仍有效；再占领/驻军/上限/修理仍gap，不晋升整项；见work/re/e147_bankcapture.md；例：GE_SwissBank, NY_NYStockExchange |
| 已对拍 | `Behaviors/InfiltratorContain:ENERGY` | 4 (6) | a2 a4 a5 a6 a7 a8 | tests/test_siminfiltrator.py::test_spy_power_plant_as_on_the_bench；总控11-11授权按配置组收尾：engine_infiltrator a/b/c/d按名字重放，盟军间谍对盟/苏/帝普通电厂及帝国忍者对盟军电厂，敌方进入者消耗、建筑满血不换主、100电量停电约20秒并恢复，友军拒入且存活；gap：其他电量/苏联超级电厂、重复进入续期、精确时序和默认状态分支仍未对拍，不表示全字段全模板已验证；例：JapanPowerPlant |
| 推断 | `Behaviors/ActivateModuleSpecialPower` | 4 (5) | a1 a2 a4 a6 a7 | E153 engine_activate:a 原版雅典娜宿主/仅删本模块对照，合法按钮激活链接ShieldSphereUpdate；f76..371状态111/100，f379消退100/100，证据7。tests/test_simactivate.py按名回放并断言实测f152/f379；仅实现SELF_POSITION、InitiallyActive=false链接的ObjectStatus/Duration。吸收伤害、上限、提前终止、重复激活及其他链接仍gap；不晋升整项，不表示C的SpecialPowerNugget派发覆盖；见work/re/e153_activate.md；例：AlliedAntiStructureVehicle, JapanAntiVehicleVehicleTech1 |
| 推断 | `Behaviors/RadarBehavior` | 4 (5) | a4 | E158原版雷达宿主/仅删模块对照，两构建均隔离原生PlayerSpellBook，不强开地图或UI。engine_radar:a宿主删除前后小地图显示/阵营徽标。E159 engine_radarlow:a只删电厂，供需150/75→50/75，f147/f302宿主及消费者均存活、供电1/0，小地图均显示；tests/test_radar_bench_e.py按名回放供需、存活及HUD。E160 engine_radartwo:a两同类宿主，f114/f197/f386存活11→01→00、独立HUD地形→地形→徽标，供电及前置均1；按实测帧回放，慢速运行现实秒断言FAIL原样保留见work/re/e160_radar_multi.md。E161 engine_radardeath:a原版500HP宿主受250/1000伤害，f87=100%、f95/f173=50%且地形，f182死亡1/HP0且HUD关闭过渡、f192/f374徽标，供电前置始终1；按名回放HP/死亡/供需/HUD，见work/re/e161_radar_death.md。E162 engine_radarout/in:a脚本双向换主，两局本地HUD分别作原主/新主：out f91归属1地形→f312归属2徽标，in f87归属2徽标→f282归属1地形，宿主存活及双方供电前置均1；按名回放归属/存活/双侧供需/HUD，见work/re/e162_radar_owner.md。不表示工程师占领或直接观测Soviet_4 HUD。只覆盖已建成盟军雷达宿主正常/不足供电、同类多来源脚本删除、受伤致死及脚本换主采样边界；注册内部实现INFERRED，精确死亡注销/换主帧、其他致死来源、建造、工程师占领、混合模板和其他宿主仍gap，不晋升整项。PLAYER_HAS_POWER物体模型条件缺口strict xfail；见work/re/e158_radar.md、work/re/e159_radar_power.md；例：AlliedRadarDish, PlayerSpellBook |
| 推断 | `Behaviors/SpecialAbilityUpdate` | 4 (5) | a1 a4 a6 a7 | E176 engine_specialability_e:a原版忍者/仅删模块对照一局PASS，f240冻结240/13/4/4：两侧曾有NON_AUTOACQUIRABLE，只有原版曾有UNATTACKABLE，最终均清状态且存活。tests/test_specialability_bench_e.py按名字回放四行实测，现有公开Sim无需改规则。仅此烟雾弹Pack状态设置/清除边界；精确开始/到期帧及Pack起算INFERRED，旧命令恢复、其他选项/宿主、重复施放、受击/死亡打断仍gap，不晋升整模块，不新增拆分用量；见work/re/e176_specialability.md；例：JapanAntiInfantryInfantry, JapanAntiVehicleVehicleTech1 |
| 推断 | `Behaviors/TechUpgradeReceiver` | 4 (5) | a2 a4 a5 a7 a8 | E167 engine_techrecvon/engine_techrecvoff:a原版工厂/仅删二级接收模块两局PASS，均完整f330；f60/f180/f300冻结15/15/15，f180近侧300距离持有数2/1、远侧750距离1/1（含各自建造场来源），f210删除来源后f300双方均0、两工厂存活。tests/test_simtechreceiver_e.py按名字回放台上读数；公开Sim补读链接覆盖GameObject XML，未改传播规则。仅此Tech2/建造场/工厂配置，精确传播时钟及矩形角点距离INFERRED；三级、其他宿主/来源、关系/换主/半径边界/生产仍gap，不晋升整模块、不拆分用量；见work/re/e167_techreceiver.md；例：AlliedAirfield, AlliedBarracks |
| 未做 | `Behaviors/HealCrateCollide` | 4 (4) |  | E146 engine_objectbatch:a/b有/无模块均未治疗，步兵始终50/50；b中立箱且到位成立，仍无效，两轮后暂停；不把负结果登记成效果已对拍。SecretFile原XML含当前schema不接受的属性，未冒充普通HealCrate等价；碰撞派发前置待查；见work/re/e146_objectbatch.md；例：SS_SecretFile1, SS_SecretFile2 |
| 推断 | `Behaviors/InfiltratorContain` | 4 (4) | a4 a5 | E198按总控配置收尾；ENERGY独立已对拍4用量/6模板，STEAL_MONEY独立登记3用量/4模板，车辆VISION_UNITS另行登记4用量/4模板仍推断；RESET另行登记5用量/6模板仍推断；普通VISION另行登记5用量/5模板仍推断；飞机VISION_UNITS另行登记2用量/2模板仍推断；步兵VISION_UNITS另行登记3用量/3模板仍推断；舰船VISION_UNITS单列3用量/3模板仍推断；本行2配置4用量/4模板仍待闭合，不登记整组或整模块已对拍。逐配置边界：KILL 1用量/1模板部分已测（engine_infkill a，敌消耗/友拒入、满血不换主；tests/test_siminfiltrator_kill.py）；PARALYZE 3用量/3模板部分已测（三国engine_infpara a/b、engine_infpsov a、engine_infpjap a移动及engine_infpatk/engine_infasov/engine_infajap a攻击，tests/test_siminfiltrator_paralyze.py）；普通VISION 5用量/5模板部分已测且暂停扩宿主（engine_infvis a/b稳定窗通过，c已接敌消耗/友拒入、满血原主与s19起局部揭示，s18=0时序保留strict xfail，见work/re/e196_vision.md）；港口阻断VISION单列1用量/1模板，实测边界见该行；飞机VISION_UNITS单列已接E199前300帧周期；步兵VISION_UNITS单列已接E199前300帧周期；车辆VISION_UNITS已接同一周期（engine_inffoot c、engine_infclock a，tests/test_siminfiltrator_clock.py）；完整筛选/移动/生产/到期仍gap；舰船VISION_UNITS已独立分区，实测边界见该行；RESET单列仅入楼已接（engine_infreset a/b就绪与真实冷却未闭环、strict xfail）。VISION/STEAL_MONEY/VISION_UNITS/RESET具名回放见tests/test_siminfiltrator.py。INFERRED：进入距离/生效和精确到期、VISION约5秒延迟/半径映射/宿主死亡清理、KILL致死清理；gap：其他间谍/模板、PARALYZE生产/重复进入/旧攻击订单、KILL抛飞/死亡效果、VISION持久性/重复进入及未测配置。已测PARALYZE不代表其余配置已测；完整逐配置证据与原始读数指针见work/re/e142_infiltrator_closure.md；例：AlliedAirfield, AlliedBarracks |
| 推断 | `Behaviors/InfiltratorContain:VISION_UNITS_VEHICLE` | 4 (4) | a2 a4 a5 a7 a8 | E194完整车辆配置4用量/4模板；engine_infveh a敌间谍消耗、友军拒入，两厂满血原主，test_spy_vehicle_factory_entry_as_on_the_bench按名断言原台s19–25与s34–35。E199接既存AlliedAntiVehicleVehicleTech1前300帧0/1/1/1/1周期（engine_infclock a，tests/test_siminfiltrator_clock.py）；b直接SET与旧计数同步间歇，c三类标记位置掩码恒111仍间歇；a/b/c可见位及s10入楼时钟保留strict xfail，不拟合连续30秒；观察者内部/寿命、完整筛选/移动/生产和其他宿主/间谍/重复仍gap；进入距离与时钟INFERRED。不登记已对拍、不扩大整模块覆盖；见work/re/e194_vehicle.md；例：AlliedWarFactory |
| 已对拍 | `Behaviors/ParkingPlaceBehavior` | 4 (4) | a4 a5 a7 a8 | tests/test_parking_bench_e.py::test_parking_named_object_model_observations；E188复用E157两局旧台，tests/test_parking_bench_e.py按名字回放原机场/仅删模块f194=1/0、f982=4/0及交换玩家f196=1/0全部通过；消费LIMITED_PRODUCTION_AIRCRAFT及配置配额4，修空闲队列后续唤醒。只覆盖本机场Apollo生产差异；准入发生在下单阶段、排队/出场预留为INFERRED，精确生产帧、筛选、物理机位、返航预约/占用/释放、航母及其他机型仍gap；旧队伍飞离预测失败仍保留，不追加实机；见work/re/e188_parking.md；例：AlliedAirfield, AlliedAntiStructureShip |
| 已对拍 | `Behaviors/SpecialDisguiseUpdate` | 4 (4) | a1 a4 a6 a7 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_spndisguise.py；例：AlliedAntiVehicleVehicleTech3, AlliedInfiltrationInfantry |
| 推断 | `Behaviors/AttachUpdate` | 3 (24) | a1 a2 a4 a5 a6 a7 a9 | 部分：engine_attach a验证瞬移/跟随/父子状态；engine_attach_parent a验证简单模块脚本杀父后子活/清理链接，NO_COLLISIONS读数差异为严格xfail；原版模块死亡前无稳定链接，不推广死亡规则；子死/直接删除/维修/吸血/解除/自主扫描仍gap；例：ChronoTargetMarker, AlliedAirfieldRepairDrone |
| 已对拍 | `Behaviors/StealthDetectorUpdate` | 3 (8) | a2 a6 | tests/test_detector_bench_e.py::test_detector_named_object_model_observations；已测范围：engine_detector:a原版军犬/仅删模块/超半径三路，距离150/150/450；目标INVISIBLE_DETECTED在f151为1/0/0，删除军犬后f310均0，目标始终存活；tests/test_detector_bench_e.py按名用私有物体模型回放同帧读数，原有实现无需修改；gap：公开Sim未接反隐（strict xfail），精确首扫/清除帧、半径边界、移动/驻军/多探测器/其他宿主及过滤配置未对拍；见work/re/e156_detector.md；例：AlliedScoutInfantry, A08_Dog1 |
| 未做 | `Behaviors/SlaughterHordeContain` | 3 (6) | a5 a7 a8 | E170 engine_slaughter_e:a/b航母原版/仅删模块两局完成f600、宿主存活11，f180攻击期/f600返航后数量编码均0；a误用DRONE分类，b改AIRCRAFT后仍0。tests/test_slaughter_bench_e.py按名字回放负基线；快照未定位出机/吞入，不能以0判模块无效或借起重机AI撤退晋升。缺同帧命令接受、子机父体/存活轨迹及enterAccepted/停车阶段；同输入暂停，原数量预测FAIL保留，不推猜测模型，不登记已对拍；见work/re/e170_slaughter.md；例：AlliedAntiStructureShip, S08_AlliedAntiStructureShip |
| 未做 | `AI/AnimalAIUpdate` | 3 (4) |  | E192 engine_animal_e:a原版女性平民近敌100/仅删模块/远敌700三路，f240四行240/0/7/7，六物体存活但均未离开起点。engine_animalfire_e:a增加敌兵攻击旁电厂，仍240/0/7/7，三路受击前置未成立；两局原逃跑预测FAIL保留。tests/test_animal_bench_e.py按名字回放实读负基线，开火接受Sim63对台7保留strict xfail。ra3ext tgt0/inc3/ua0无fleeTrigger/attackAccepted/rejectReason，触发资格未闭合（INFERRED），不实现猜测规则、不登记效果覆盖；同输入暂停，需合法触发或接受证据与新预算，见work/re/e192_animal.md；例：BaseCivilian, CivilianFemale1 |
| 未做 | `Behaviors/AssistedPlacementBehavior` | 3 (4) | a1 a2 a4 a5 a6 a7 | E169 assistpon:a / assistpoff:a原版与删模块两局均资金8000、矿场总数0、提示位数量0、采样完成0；红色预览未落地，原吸附预测保留。当前计数器无放置接受/拒因字段，不能归因于模块；同输入暂停。tests/test_assistplace_bench_e.py具名回放资金负基线strict xfail：Sim未消费侧栏排队/放置点击；吸附、朝向、迷雾资格和精确距离均gap，不登记已对拍；见work/re/e169_assistplace.md；例：AlliedRefinery, AlliedRefinery_NoHarvester |
| 已对拍 | `Behaviors/InfiltratorContain:STEAL_MONEY` | 3 (4) | a1 a2 a4 a5 a6 a7 | tests/test_siminfiltrator.py::test_spy_refinery_transfer_amount_as_on_the_bench；总控11-16按完整配置收尾：3用量/4模板；engine_infmon a的s13实测p1/s1资金3000/3000（初始1000/5000），转账2000，敌方间谍消耗、友军拒入，两矿厂满血且归属不变。仅盟军间谍/盟军矿厂单次足额转账效果已实现；gap：其他宿主/间谍、余额不足、重复进入、BlockedDuration收入阻断；通用进入距离/时钟INFERRED，s11稳定窗及匿名矿车清除/后续收入回放保留strict xfail，未放宽原断言；按总控与ENERGY同样的配置登记口径，不表示全字段全模板均已验证；见work/re/e193_money.md；例：AlliedRefinery |
| 未做 | `Behaviors/LoseHealthUpdate` | 3 (4) | 全部 | E146 engine_objectbatch:a/b：原船完整模块移植480HP坦克，HealthTrigger=101%/0%均无耗血，两路100/100；b已确认toggle/铁幕状态成立。两轮后暂停，移植激活资格待查，未推猜测实现、不晋升整项；见work/re/e146_objectbatch.md；例：SovietAntiStructureShip, SovietBomberAircraft |
| 推断 | `Behaviors/MovementSpecialPower` | 3 (4) | a1 a4 a6 a7 | E171 engine_movement_e:a原版鬼王/仅删模块对照，f210冻结完成210、曾激活位1、离开起点位1、最终清状态且存活11；tests/test_movement_bench_e.py按名字回放台上读数。公开Sim消费TARGETED静态地点、ObjectStatus、Duration、LocomotorSet及自身AttributeModifier；仅覆盖合法范围内单次施放。INFERRED：从按键起算Duration及到期停走；gap：精确起止帧、对象目标/跟踪、超距接近、冷却/重复命令、碰撞伤害/反弹、舰船及其他配置。不登记整模块已对拍，见work/re/e171_movement.md；例：JapanAntiStructureShip, JapanAntiVehicleVehicleTech3 |
| 推断 | `Behaviors/SecondaryObjectListenerModule` | 3 (4) | a1 a2 a3 a4 a5 a6 a7 | E174 engine_secondon_e:a / engine_secondoff_e:a原版多功能炮塔/仅删监听器对照；f60/f180/f360冻结主次体存活、乘员ENCLOSED和Repair升级位，原版3/15/3、删模块3/7/3。tests/test_secondary_bench_e.py具名回放；公开Sim补单乘员显式IncludeThing的UpgradeSelf进入授予/退出撤销，不改容器阈值。INFERRED：通知立即生效及未单测的显式模板匹配；gap：武器/外观通知、SelfValidation、复杂过滤、多乘员、其他宿主/乘员、死亡及精确帧，不登记整个模块已对拍；私有物体模型未接，见work/re/e174_secondary.md；例：AlliedBaseDefense, AlliedAntiAirVehicleTech1 |
| 未做 | `Behaviors/StructurePlacementBehavior` | 3 (4) | a1 a2 a4 a5 a6 a7 | E183 structpon:a/structpoff:a原版矿场/仅删模块两局，前方120放电厂；总数及前方区域始终0，资金从10000采矿增长到11750/12000，未到9200付费哨兵。原禁建/允许预测FAIL保留，未建立合法排队/放置接受事实；tests/test_structureplace_bench_e.py仅按名字回放零电厂负基线，不登记模块效果已对拍。queueAccepted/queueReady/placementAccepted/rejectReason缺失，同输入暂停；几何消费/旋转/边缘仍gap，见work/re/e183_structureplace.md；例：AlliedRefinery, AlliedRefinery_NoHarvester |
| 推断 | `Behaviors/HitReactionBehavior` | 3 (3) | a1 a2 a3 a4 a5 a6 a7 a9 | E172 engine_hitreaction_e:b原版维和步兵/仅删模块对照，f180冻结完成180、血量99/99、位895：两侧举盾/合法受击/留在原位，只有原版曾出现HIT_REACTION，最终均清除；tests/test_hitreaction_bench_e.py按名字回放台上读数。公开Sim补零阈值heavy分支、配置状态门及条件时长；INFERRED：正实伤起算/刷新和精确到期。gap：受击转向、动画、非零阈值/light/medium、GoIdle/死亡类型门、其他伤害入口/宿主、精确时钟及状态门切换；不登记整模块已对拍。a诊断帧比较/持续采样错误保留，未拿其血量差推模块规则；见work/re/e172_hitreaction.md；例：AlliedAntiInfantryInfantry, JapanEmperor |
| 推断 | `Behaviors/InfiltratorContain:VISION_UNITS_INFANTRY` | 3 (3) | a2 a4 a5 a7 | E198步兵完整配置3用量/3模板；engine_inffoot a独立步兵对照按名回放敌间谍消耗、友军拒入、两兵营满血原主，身份位置511。E199接既存AlliedEngineer前300帧0/1/1/1/1周期（engine_inffoot c，tests/test_siminfiltrator_clock.py）；观察者内部/完整筛选/到期仍gap，旧墙钟保留strict xfail，不从30秒XML推连续揭示；进入距离/时钟INFERRED，其他宿主/间谍/玩家/重复未测，不登记已对拍；见work/re/e198_infantry.md；例：AlliedBarracks |
| 推断 | `Behaviors/InfiltratorContain:VISION_UNITS_SHIP` | 3 (3) | a4 a5 | E200舰船完整配置3用量/3模板；engine_infship a独立水陆对照：敌消耗友拒入、满血原主、身份位置511、异类/第三方隐藏；c逐帧300位、20页均31710（0/1/1/1/1）已接具名回放，a墙钟间歇strict xfail；观察者内部/完整筛选/移动/生产/到期仍gap，不登记已对拍；进入距离/时钟INFERRED；见work/re/e200_ship.md；例：AlliedNavalYard |
| 推断 | `Behaviors/LiftObjectUpdate` | 3 (3) | a1 a2 a4 a6 a7 | 部分：显式TimeIncrement/MaxTimeLifted的开火者举升表计时接口；tests/test_lift_nugget.py回放engine_lift a状态计数，逐帧计时来自模块证据、未上台逐帧量表；垂直运动/死亡/飞机/落地武器/清位仍gap，落地清位INFERRED，不登记整模块已对拍；例：AlliedBaseDefense, AlliedAntiAirVehicleTech1 |
| 未做 | `Behaviors/ReturnToProducerSpecialPower` | 3 (3) | a1 a2 a3 a4 a5 a6 a7 a8 | E173 engine_returnon_e:a / engine_returnoff_e:a两局均f660冻结660/7/11/1：原生生产后具名引用，f405到离场区，返航后曾USER_1，最终存活回机场区且施放1。a遗漏显式原版资产替换，两局实际都保留原版飞机，删模块预测FAIL；不据相同读数判模块无效。b补显式replaces，仅静态/构建验证、未上台；原失败预测保留。tests/test_returnproducer_bench_e.py具名物体模型回放出发位0对实测7，2 strict xfail：生产按钮/引用前置未闭合，不手放飞机绕过。producerId、命令接受/拒因、机位/停靠阶段未量到，DOCKING未置位；暂停同输入，修正台须新预算，未实现返航、不登记已对拍；见work/re/e173_returnproducer.md；例：AlliedAntiGroundAircraft, AlliedFighterAircraft |
| 未做 | `Behaviors/SubStructureBehavior` | 2 (11) |  | E189 engine_substructure_e:a一局PASS，独立摆放的原版维修台/仅删模块对照，f59血量100/100、f120脚本伤害后80/80、f240删除无绑定建造场后80/80且场存活位0；tests/test_substructure_bench_e.py按名字回放最终四行240/80/80/0通过，无模型改动。只测独立摆放基线，不推断父子联动或模块无效；SDK有效XML无SubStructureBuild，现四行缺parentId/bindAccepted/forwardedDamage。父体绑定、伤害传递、清理及其他模板仍gap，同输入暂停，需合法绑定入口及新预算；见work/re/e189_substructure.md；例：AlliedConstructionYardRepairBay, AlliedCrane |
| 未做 | `Behaviors/AttributeCrateCollide` | 2 (3) |  | 模拟器代码里没有这个名字；例：SS_SecretFile1, SS_SecretFile2 |
| 未做 | `Behaviors/ConvergingLaserState` | 2 (3) | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiStructureVehicle, SovietAntiVehicleVehicleTech1 |
| 未做 | `Behaviors/AimWeapon` | 2 (2) | a1 a4 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedAntiVehicleInfantry, SovietAntiVehicleInfantry |
| 未做 | `Behaviors/GateOpenAndCloseBehavior` | 2 (2) |  | E190原版门/删模块初始化台被SDK Behaviors拒绝该模块且缺模型资源；原生地图摆放同样强制编译失败。改用engine_gate_e:a运行时同动作创建两门与电厂哨兵，一局PASS，f180=180/0/0/1（完成/Romania门/Sanitarium门/哨兵存活）。tests/test_gate_bench_e.py按名回放帧数与哨兵通过，SDK模型两门均1对台0，2 strict xfail；未改模型，不登记模块效果覆盖。缺templateResolved/createAccepted/rejectReason，倾向模板在当前运行环境不可用（INFERRED）；开闭/通行/复位均gap，同输入暂停，重开需可创建宿主及合法开关入口，见work/re/e190_gate.md；例：RM_AlliedBlastDoor, SS_Door |
| 推断 | `Behaviors/InfiltratorContain:VISION_UNITS_AIRCRAFT` | 2 (2) | a4 a7 | E197飞机完整配置2用量/2模板；engine_infair a独立飞机对照按名回放敌间谍消耗、友军拒入、两机场满血原主。E199接既存AlliedSupportAircraft前300帧0/1/1/1/1周期（engine_infclock a，tests/test_siminfiltrator_clock.py）；观察者内部/完整筛选/到期仍gap，旧墙钟可见位保留strict xfail，不从30秒XML推连续揭示；通用进入距离/时钟INFERRED，其他宿主/间谍/玩家/重复未测，不登记已对拍；见work/re/e197_aircraft.md；例：AlliedAirfield |
| 已对拍 | `Behaviors/InvisibilityBroadcastUpdate` | 2 (2) | a1 a4 a6 a7 | tests/test_simbench_c.py::test_invisibility_broadcast_the_aura_holds_its_guardian_at_full_health_and_the_control_dies；例：AlliedAntiVehicleVehicleTech3, A08_SpecialMirageTank |
| 未做 | `Behaviors/NotifyWhenAttackingBehavior` | 2 (2) | a1 a2 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；**待核**：台上量过（checks/engine_attackassist.py），可能用别的名字实现了；例：AlliedBaseDefenseAdvanced, SovietBaseDefenseAdvanced |
| 未做 | `Behaviors/PowerUpgrade` | 2 (2) | a5 | E175 engine_powerupgrade_e:a/b两局：a冻结330/11/10/11，b精确供电始终100/100/500/350，授予期升级持有位均0。高级原版500来自战役覆盖，删模块克隆为SDK350，不能拿基线差归因于模块。TriggeredBy的Upgrade_PowerPlantTurbine在SDK Upgrade.xml无定义；合法授予/接受拒因未闭合，倾向未解析引用（INFERRED），两局后暂停同输入。tests/test_powerupgrade_bench_e.py具名实际读数回放2 strict xfail，模型未改、不登记已对拍；原预测保留，购买升级、加电/撤销和其他升级门均gap；见work/re/e175_powerupgrade.md；例：SovietPowerPlantAdvanced, SovietPowerPlant |
| 未做 | `Behaviors/PrematureDischargeSpecialPower` | 2 (2) | a4 | E177 dischargeon_e:a/dischargeoff_e:a两局原版波能坦克/仅删模块对照，f45攻击、f75按键；f210冻结原版210/76/0/1、删模块210/0/109/0，首伤提前33脚本帧、施放事件1/0。删模块原施放1预测FAIL保留。tests/test_discharge_bench_e.py具名回放2 strict xfail：Sim两侧首伤47，且原版漏施放；武器PER_SHOT前摇及提前放电派发未闭合，不硬调模型、不登记已对拍。内部充能、伤害缩放、重复/取消、其他宿主与绝对帧均gap；见work/re/e177_discharge.md；例：JapanBaseDefenseAdvanced, JapanAntiStructureVehicle |
| 已对拍 | `Behaviors/RecallUnitsSpecialPower` | 2 (2) | a4 a7 | tests/test_recall_bench_e.py::test_recall_named_object_model_bench；E187按名回放E184原版机场/仅删模块旧台，两路完整读数660/7/3/1与660/7/5/0通过；单架原生生产Apollo由机场按钮召回回近场并记录施放，使用模板速度移动，未改原预测。已测限本机场/机型单架；生产者筛选、选择顺序、回机场中心的路径为INFERRED，数量上限、精确帧、其他机型/机场、换主、降落及Parking仍gap；见work/re/e187_recall.md；例：AlliedAirfield, SovietAirfield |
| 未做 | `Behaviors/SpiderHoleUpdate` | 2 (2) | a4 | E178 spideron_e:a/spideroff_e:a原版反坦克步兵/仅删模块两局PASS，f45合法入洞、f120隔离者出洞；f90/f180具名状态及存活编码两侧均1515/1508，施放事件均3。tests/test_spider_bench_e.py具名回放状态通过，施放事件2 strict xfail（Sim为0）。手动切换由ToggleStatus提供，不据相同状态晋升扫描模块；同点载具实际距离/扫描接受与内部阶段未测，自动出洞假设未成立，_Ambush/精确扫描时钟/移动载具/攻击碾压仍gap，不拟合规则、不改分母；见work/re/e178_spider.md；例：JapanAntiVehicleInfantry, JapanAntiVehicleInfantry_Ambush |
| 已对拍 | `Behaviors/TechUpgrade` | 2 (2) | a1 a4 a5 a7 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_tech.py；例：AlliedConstructionYard, AlliedOutpost |
| 已对拍 | `Behaviors/LifetimeUpdate` | 1 (855) | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_attachmine.py；例：AlliedAirField_Collapse, AlliedAntiAirShip_Collapse |
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
| 未做 | `Behaviors/SwitchLocomotorUpdate` | 1 (2) | 全部 | 模拟器代码里没有这个名字；**待核**：台上量过（checks/engine_acts11.py），可能用别的名字实现了；例：SovietBomberAircraft, SovietBomberAircraft_Special |
| 未做 | `Behaviors/TeleportStoredObjectsSpecialPower` | 1 (2) | a7 a8 | 已核（11-08）：模拟器没有这个效果（没有传送存放的单位）；例：AlliedSuperWeapon, PlayerSpellBook |
| 未做 | `Behaviors/TeleportStoredObjectsUpdate` | 1 (2) | a7 a8 | 已核（11-08）：模拟器没有这个效果（UNIT_TELEPORT_TO_WAYPOINT 另算）；例：AlliedSuperWeapon, PlayerSpellBook |
| 未做 | `Behaviors/VeterancyCrateCollide` | 1 (2) |  | 模拟器代码里没有这个名字；例：VeterancyCrate, VeterancyCrateMP |
| 未做 | `Behaviors/ActivateSpecialPowerOnCreate` | 1 (1) |  | 模拟器代码里没有这个名字；例：JapanAntiVehicleInfantry_Ambush |
| 已对拍 | `Behaviors/AssembleStructureSpecialAbilityUpdate` | 1 (1) | a4 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_skill.py；例：SovietEngineer |
| 未做 | `Behaviors/ChargeWeaponUpdate` | 1 (1) | a4 | 模拟器代码里没有这个名字；例：JapanBaseDefenseAdvanced |
| 未做 | `Behaviors/CircularDamageUpdate` | 1 (1) |  | E143最小消费诊断：engine_circular a/b/c/d具名回放仅保留负结果，不登记效果已对拍。陆地无ONLY_ON_WATER、MaxRadius175/ArcDistance50、径向50/100/150靶；正常/删激活/删模块/持续开火对照，消费前置仍未解释，未实现接口。Lifetime推进、SweepWeapon实际派发、水面过滤、重复激活和死亡清理均gap；tests/test_simcircular.py；假设表见work/re/e143_circular_gate.md；例：SovietAntiNavyShipTech1 |
| 未做 | `Behaviors/DieOnProducerDeathUpdate` | 1 (1) |  | 模拟器代码里没有这个名字；例：AlliedAttackDrone |
| 未做 | `Behaviors/DominateEnemySpecialPower` | 1 (1) |  | 模拟器代码里没有这个名字；例：AlliedInfiltrationInfantry |
| 未做 | `Behaviors/GrapplingHookUpdate` | 1 (1) | a1 a3 a4 a6 a7 a9 | 仅engine_grapple a最小消费者诊断；模块派发/拉拽/释放未解释，未实现，不作为已对拍证据；例：SovietAntiVehicleVehicleTech3 |
| 已对拍 | `Behaviors/InfiltratorContain:VISION_PORT` | 1 (1) |  | tests/test_siminfiltrator_port.py::test_port_entry_and_blocked_repeat_as_on_the_bench；E201按总控完整配置口径独立登记1用量/1模板；engine_infport a/b按名回放敌消耗/友拒入、满血原主、近同属与近第三方可见、远端隐藏、身份位置511；a第二间谍存活，b取消首次敌入港后同一第二间谍被消耗，闭合重复阻断对照。gap：其他间谍/玩家、长时持久性/到期、死亡清理及观察者内部；精确进入/揭示相位、半径映射与XML阻断到期INFERRED，b的s25瞬态保留strict xfail，不调时钟；见work/re/e201_port.md；例：CA_PortStructure |
| 已对拍 | `Behaviors/LinearDamageUpdate` | 1 (1) | a1 a2 a4 a6 a7 | tests/test_simsweep.py::test_sweep_the_line_walks_out_and_a_stop_does_not_cut_it_at_the_bench_frames；例：AlliedAntiNavalScout |
| 未做 | `Behaviors/MagneticEffectUpdate` | 1 (1) | a1 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiNavyShipTech1 |
| 已对拍 | `Behaviors/ReconstituteStateSpecialAbility` | 1 (1) | a1 a2 a4 a6 a7 a9 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_cast.py；例：AlliedCommandoTech1 |
| 推断 | `Behaviors/ShieldSphereUpdate` | 1 (1) | a2 a6 | 模拟器代码里有这个名字；台上量过（docs/engine/inventory-levels-a.md），没有测试跑这个台子；例：AlliedAntiStructureVehicle |
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
| 已对拍 | `DamageNugget` | 183 | 全部 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_attackassist.py；例：BaseExplodingPropVehicleWeapon, MountRushmoreHeadEyeWeapon |
| 已对拍 | `ProjectileNugget` | 88 | 全部 | tests/test_simbench_c.py::test_projectile_nugget_flight_uses_retail_shell_speed_and_resolved_warhead；例：BB_EuropeCoastalGunWeapon, KremlinArtilleryDomeMissle |
| 已对拍 | `SuppressionNugget` | 64 | 全部 | tests/test_simbench_c.py::test_suppression_samples_entry_refresh_and_expiry_at_the_four_probe_readings；例：BB_EuropeCoastalGunWeapon, KremlinArtilleryDomeMissle |
| 已对拍 | `InformTargetNugget:默认系数目标通知` | 47 | 全部 | tests/test_inform_ai.py::test_inform_incoming_table_drives_miner_armor_from_engine_inform_probe；仅默认Min=.85/Max=1.15的目标通知→来弹表/矿车预计伤害开甲；engine_inform_probe a/off录入302、hit377、exp404、删除389，347帧入窗。半径/历史/海啸/忍者及完整AI调度不在本登记范围，完整脚本仍xfail；例：BB_EuropeCoastalGunWeapon, AlliedPrecisionBomb |
| 不涉及 | `ActivateLaserNugget` | 27 | 全部 | 纯表现：Lifetime/LaserId/HitGroundFX/OverShootDistance驱动LaserState/LaserDraw；engine_laser pair实测2/90/2/90，无附加伤害或首发延迟，test_simbench_c重放；例：MountRushmoreHeadEyeWeapon, JapanAntiVehicleInfantryTech3LockDownGun |
| 已对拍 | `WeaponOCLNugget` | 26 | 全部 | tests/test_simbench_c.py::test_weapon_ocl_lifetime_damage_reads_the_fire_delay_before_counting_updates；例：MountRushmoreHeadEyeWeapon, AlliedPrecisionBombWarhead |
| 已对拍 | `InformTargetNugget:Max1.6目标通知` | 22 | 全部 | tests/test_inform_ai.py::test_inform_max_launch_matches_engine_inform_max_observed_deadline；仅Min=.85/Max=1.6目标通知→来弹表；engine_inform_max a单变量对照录入302、hit377不变、exp444（默认404）、受伤389删除，矿车提前开甲。自然过期清理边界/半径/历史/海啸/忍者/完整AI调度未对拍，完整脚本仍xfail；例：AlliedBaseDefenseRockets, AlliedBaseDefenseRockets_Aircraft |
| 已对拍 | `AttributeModifierNugget` | 20 | 全部 | tests/test_simbench_c.py::test_weaponfx_predictions_and_finite_bursts；例：NanoHiveSwarmEffectTrigger, JapanCommandoSoftLanding |
| 已对拍 | `MetaImpactNugget:普通无延迟显式Z` | 13 | a1 a2 a4 a5 a6 a7 | tests/test_meta_impact.py::test_meta_impact_collision_event_replays_engine_knock_probe_neighbour_five_frames；仅普通弹头碰撞事件→默认Physics轨迹；engine_knock_probe land/late邻人5帧落(2380,3740)、目标99%/邻人100%。到达帧为台上输入，非完整V4曲线弹回放；直击方向/落点网格/选人仍INFERRED；例：KremlinArtilleryDomeMissleWarhead, AlliedTimeBomb_Level1 |
| 未做 | `MetaImpactNugget` | 11 | a1 a2 a3 a4 a5 a6 a7 a9 | 剩余复杂写法：延迟、Arc、飞机资格等；engine_knock_filter a/b两局99/99/3/3，原版每路4次冲击、删除筛选7次。tests/test_meta_filter.py具名回放地面派发/速度/铁锤落点：恐怖机器人和磁暴步兵显式包含越过INFANTRY，铁幕状态仍拒绝；飞机两局无冲击且缺逐帧高度/拒绝原因，完整消费者不晋升，见work/re/c_filter_report.md。engine_knock_invert水平反向回放已绿；engine_knock_objectgate a/b均99/99/1/0，保留ForbiddenTargetObjectStatus拒绝脚本LEECHED_TARGET_ACTIVE邻人、仅删字段后放行，tests/test_meta_objectgate.py具名回放派发/七帧路径；该隔离台移除Arc/模型条件/步兵过滤；engine_knock_kindgate a/b均99/99/11/0，保留INFANTRY子筛选及状态门时仅无位步兵邻人冲击，删子筛选后无位合成非步兵亦冲击，带位两邻人仍拒绝。tests/test_meta_kindgate.py具名回放派发/初速度和步兵七帧路径；合成非步兵落点网格轨迹strict xfail，原生吸血生命周期及Arc/模型条件组合仍gap，见work/re/c_kindgate_report.md；普通延迟只解析及隔离队列，Physics相位未解。ShockWaveSpeed/Cyclonic、非默认Physics、坡地及V4到达仍gap；例：JapanCommandoTech1PsyonicBlast, JapanMechaKingKatana |
| 已对拍 | `MetaImpactNugget:省略Z默认值` | 11 | 全部 | tests/test_meta_impact.py::test_meta_impact_omitted_z_replays_engine_knock_z_tall_neighbour；仅普通无延迟弹头省略ShockWaveZMult→SDK默认1及默认Physics轨迹；engine_knock_z a高度93邻人14帧落(2420,3740)、目标99%/邻人100%。碰撞时刻/爆心为台上输入；直击噪声方向/网格/选人仍INFERRED，完整曲线弹/坡地/筛选未对拍；例：JapanCommandoTech1AirplaneCrashWeapon, AlliedBomberAircraftBombWarhead |
| 已对拍 | `ParalyzeNugget` | 11 | a1 a2 a4 a5 a6 a7 | tests/test_simbench_c.py::test_weapon_first_hit_is_observed_one_frame_after_the_order_script；例：JapanAntiVehicleInfantryTech3LockDownGun, AlliedAntiStructureShipEMPCruiseMissleWarhead |
| 不涉及 | `TintObjectsNugget` | 9 | 全部 | 纯表现：Color及Pre/Sustained/PostColorTime、Frequency/Amplitude仅控制染色动画；engine_tint pair实测2/90/2/90，独立DamageNugget解释全部伤害，test_simbench_c重放；不声称像素已验证；例：SovietCommandoCallBombingRun, AlliedCommandoAttachWeapon |
| 推断 | `ActivateLiftObjectNugget` | 6 | a1 a2 a4 a6 a7 | 部分：按模块证据实现开火者举升表，trunc(TimeIncrement×15)逐发累加、续期封顶MaxTimeLifted、逐帧递减释放；Lifetime不参与，释放不清LIFTED；tests/test_lift_nugget.py按名回放engine_lift a旧读数一致，landing因落地清位未实现strict xfail；engine_liftground a原百合子/入驻IFV/入驻炮塔与删Nugget为11/111/111/10；engine_liftair a为0/100/100/10（三原版飞机死亡、未锁存LIFTED，阴性存活），原对空预测FAIL保留；tests/test_lift_nugget.py具名回放实际读数，两strict xfail（原版复杂筛选/飞机消费未接通），见work/re/c_liftretail_report.md；地面3/对空3均有局部读数但完整消费者仍未对拍，旧合成VEHICLE组不占原版用量；A169已量接地帧但28清位/40与60不清的门槛未解；落地清位规则INFERRED，垂直运动/死亡/飞机/弹体/复杂筛选仍gap，不登记整项已对拍；整项边界见work/re/c_liftclosure_report.md；例：JapanCommandoTech1PsyonicCrush, JapanCommandoTech1AirborneKiller |
| 已对拍 | `LineDamageNugget` | 6 | a1 a2 a3 a4 a5 a6 a7 | tests/test_simbench_c.py::test_weaponfx_predictions_and_finite_bursts；例：SovietCommandoSniperRifle, AAAVT1_SovietCommandoSniperRifle |
| 未做 | `FireOnObjectsNugget` | 5 |  | 未实现：子武器派发条件与空间锚点尚未解释；失败诊断不作为已对拍依据；例：PlayerPowerJapanEmperorsResolveWeapon_L1, PlayerPowerJapanEmperorsResolveWeapon_L2 |
| 已对拍 | `SecondaryDamageNugget` | 5 | a7 | tests/test_simbench_c.py::test_secondary_damage_delivers_one_amount_at_hit_without_damaging_health；例：MountRushmoreHeadEyeWeapon, AlliedCryoSatelliteLvl1 |
| 推断 | `AttachNugget` | 4 | a1 a2 a4 a5 a6 a7 a9 | 部分：engine_attach a实测直接单发、父子状态、随父移动及目标状态/类型拒绝；仅零半径简单模块，原版复杂筛选/维修/吸血/解除/弹体未接通；engine_attachc4 a原版谭雅/删Nugget及父EXPLOSIVES_ATTACHED对照为11/10024/10030/10028，正常原版附着后父死子活，禁用父仍有MARCH_OF_DEATH但无ATTACHED；tests/test_attach_c4.py具名回放，原生模块状态/链接/爆破消费strict xfail，见work/re/c_attachc4_report.md；engine_attachmine a原生磁力地雷本体原位创建/删Nugget×普通/SPECIAL_ARMOR_ACTIVE为111/110/111/110，保留者均附着、删除者均不附着；tests/test_attach_mine.py具名回放阴性，b三个禁用位均读到仍附着为111/110/7111/7110，两原生回放strict xfail；上游弹体/OCL、复杂筛选及生命周期仍gap，见work/re/c_attachmine_report.md；不登记整项已对拍；例：AlliedCommandoAttachWeapon, SovietAntiVehicleInfantryMagneticBombAttachWeapon |
| 已对拍 | `StripMaxHealthPercentNugget` | 3 | a1 a2 a4 a6 a7 | tests/test_simbench_c.py::test_strip_max_health_percent_uses_maximum_at_full_and_half_health；例：JapanCommandoTech1PsyonicCrush, AAAVT1_JapanCommandoTech1PsyonicCrush |
| 已对拍 | `ActivateLinearDamageNugget` | 2 | a1 a2 a4 a6 a7 | tests/test_simsweep.py::test_sweep_a_killed_shooters_line_stops_with_it_and_the_second_ones_rows_are_hit；例：AlliedAntiNavalScoutSonar, AlliedAntiNavalScoutSonarForBridges |
| 已对拍 | `DamageContainedNugget` | 2 | a1 a2 a3 a5 | tests/test_simbench_c.py::test_damage_contained_limits_eligible_passengers_without_damaging_the_others；例：SovietAntiInfantryInfantryMolotovCocktailWarhead, Weapon_DesolatorBombFieldUpdate |
| 已对拍 | `LeechPercentMaxHealthDamageNugget` | 2 | a1 a3 a4 a6 a7 a9 | tests/test_simbench_c.py::test_leech_percent_uses_victim_maximum_not_current_health_or_caster_maximum；例：SovietCrushWeapon, SovietHarpoonCrushWeapon |
| 不涉及 | `ReportWeaponFiredStatNugget` | 2 |  | 纯统计（C线工单允许排除）：只记录玩家武器开火次数；原版两份空配置附于SovietVacuumBomb / ParticleCannonWeapon，伤害与创建物体由独立WeaponOCLNugget负责。保留用量2，不登记已对拍；未上台，不模拟战后统计；证据见work/re/c_reportstat_report.md；例：SovietVacuumBomb, ParticleCannonWeapon |
| 推断 | `SpecialPowerNugget:变装消费者` | 2 | a4 | 2用量：间谍/迅雷直接命中DISGUISED位及INFANTRY/VEHICLE/恐怖机器人排除已测；engine_spndisguise/spnspyx/spnspyex/spntrans/spntrfilter a均1111/1110/1110/1111，tests/test_special_power_nugget.py按名回放；gap：身份/外观/索敌/换目标/取消，迅雷展开时序strict xfail，即时位应用INFERRED；engine_spnrelations a间谍/迅雷各Friend与Neutral四路s6-15全1111，独立命中且无脚本变装位；engine_spncancel a四路真变装保留/空载撤离/删SPN/仅脚本位稳定1101/1101/1110/1111：普通征召兵自动攻击仅伤后两路，空载撤离不取消；engine_spncargo a有载撤离high从111101到101100再101110，实测出舱/清位后才受伤，原截图时间窗预测FAIL不改阈值；两原生消费者回放strict xfail，脚本位不等于真实身份。身份/时序缺口见work/re/c_spnclosure_report.md、c_spncancel_report.md，不登记完整消费者；例：AlliedInfiltrationInfantryDisguiser, JapanLightTransportVehicleDisguiser |
| 未做 | `ActivateCircularDamageNugget` | 1 |  | C线前置门禁：原版TeslaNova的Lifetime决定扩散速度，伤害来自宿主CircularDamageUpdate的SweepWeapon；E线模块消费接口尚缺，不能用直伤或DOT代替。0局、无台上读数，不登记已对拍；接口需求与假设表见work/re/c_circular_gate_report.md；例：SovietAntiNavyShipTech1TeslaNova |
| 已对拍 | `DOTNugget` | 1 |  | tests/test_simbench_c.py::test_dot_counts_interval_ticks_for_two_durations_and_observes_first_damage_frame；例：PlayerPowerIrradiateTargetWeapon |
| 未做 | `GrapplingHookNugget` | 1 | a1 a3 a4 a6 a7 a9 | engine_grapple a最小消费者诊断；GrapplingHookUpdate派发/拉拽/释放未解释，显式报告gap；tests/test_grapple_nugget.py守卫直接命中/继承/弹头及原版缓存，不登记已对拍；例：SovietAntiVehicleVehicleTech3Harpoon |
| 已对拍 | `LeechHealthDamageNugget` | 1 | a1 a2 a3 a4 a5 a6 a7 | tests/test_simbench_c.py::test_leech_health_heals_from_damage_and_respects_the_heal_fraction；例：SovietAntiVehicleVehicleTech1LeechBeamWeapon |
| 已对拍 | `MetaImpactNugget:镰刀敌我筛选` | 1 |  | tests/test_meta_impact.py::test_meta_impact_relation_collision_replays_observed_selection；仅镰刀无延迟筛选写法的发射者敌我关系→默认Physics；engine_knock_relation a健康99/100/99/100，ENEMIES仅敌/ALLIES仅友，逐帧位置回放。碰撞帧/爆心由台上输入；tests/test_meta_nocoll.py具名回放engine_knock_nocoll a/b：99/99/1/0与99/99/0/1，仅无NO_COLLISIONS位邻人收到冲击并三帧落到y3740。仅脚本置位；engine_knock_statusgate a/b均99/99/1/0，b仅删XML状态排除后有位邻人也收shock并三帧落y3740，tests/test_meta_statusgate.py四路具名回放；此切片无独立状态拒绝门，解析/消费按XML声明排除，原生位生命周期仍gap。engine_knock_kind a/b均99/100/99/100：原版步兵邻人收shock、铁锤无，删除Include后空Rule=ANY全无shock；tests/test_meta_kind.py具名回放派发/位置及空ANY拒绝。铁锤阳性未建立，原生位生命周期/倒地状态/非步兵拒绝归因仍gap，Physics状态映射INFERRED。engine_knock_sickle a/b真实跳跃两道均f114接地；a在f115仅敌兵收shock并三帧落y3540，b仅删MetaImpact后无shock、原地不动；tests/test_meta_sickle.py具名落地区域计数/落地事件消费回放已接通。精确到达帧和落点仍strict xfail，落地伤害筛选及衰减gap；仅派发冲击，不覆盖完整跳跃、延迟、Arc；例：SovietAntiInfantryVehicleLandWeapon |
| 推断 | `SpecialPowerNugget:干扰消费者` | 1 |  | 1用量，暂停额外SPN消费：engine_spnscr c原版四路删减、受害者真实开火、靶子封闭暴露窗，早HP100/100/90/90、晚HP90/90/80/80，打包301000090/301000090/300999080/300999080实机PASS；tests/test_special_power_nugget.py具名回放。停火差异由AttributeModifier决定，保留/删SPN相等不能证明额外消费者no-op；b仅NAMED_STOP仍续射，原预测strict xfail保留。两局耗完，缺SpecialPower开始/结束及命令消费观测，不晋升完整消费者，见work/re/c_spnscr_active_report.md；例：AlliedAntiAirShipWeaponScrambler |
| 已对拍 | `SpecialPowerNugget:涂靶升级门槛` | 1 | 全部 | tests/test_special_power_nugget.py::test_special_power_nugget_retail_painter_consumer；仅原版守护者普通/高科技两种升级门槛与空PaintTarget消费者边界；engine_spnret a保留/删除SPN晚段74/69/74/69%血，增伤来自伴随AttributeModifierNugget。非通用技能执行；原版涂靶开关/持续光束/重复开火未测，其他消费者另列gap；例：AlliedAntiVehicleVehicleTech1TargetPainter |
| 推断 | `SpecialPowerNugget:轰炸消费者` | 1 | a1 a2 a4 a6 a7 | 1用量，暂停：engine_spnbombnative a原版/删SPN/合成/合成删SPN为1010/1110/1110/1110；OCL活动消费者未实现，具名回放strict xfail；需要原版与合成宿主派发观测，work/re/c_spnbomb_report.md；例：SovietCommandoCallBombingRun |
| 未做 | `SpecialPowerNugget:附着dummy消费者` | 1 |  | 1用量，暂停：JapanScoutInfantryAttachWeaponWarhead引用OBJECT dummy模板及原版宿主；缺独立派发/附着读数，不能按Dummy名字推定无操作；需Attach模块观测，work/re/c_spnclosure_report.md；例：JapanScoutInfantryAttachWeaponWarhead |

## AI

| 状态 | 名字 | 用量 | 9 关用到 | 说明 |
|---|---|---|---|---|
| 已对拍 | `战略状态/StrategicState.State` | 4422 | a4 a5 a7 | docs/engine/aistate.md#读数（人格只留台上写的状态，AI 只跑这些：aistateconst / aistateslash 等） |
| 已对拍 | `人格/PowerChoice.PlayerPower` | 2326 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipower.py |
| 已对拍 | `人格/PowerChoice.Weight` | 2326 | a4 a5 a7 | docs/engine/aiopen.md#买协议（aipwrb 权重 0 的不买） |
| 已对拍 | `战略状态/TargetHeuristic.TargetHeuristic` | 1237 | a4 a5 a7 | docs/engine/aitactics.md#读数（aitargetnear / aitargetsafe：按状态写的目标启发挑楼） |
| 已对拍 | `造兵/BuildState.State` | 1180 | a4 a5 a7 | 台上量过（engine_aiskirm y aisknew / aisknew2：没列进任何建造状态的我们的兵不造、列成 FEWEST_UNIT 占兵营约一半；z aiskvinf / aiskvveh：BEST_UNIT_EXPECTED 兵营只造克制兵），测试对拍 tests/test_simai_bench_b.py（B 第 126–131 轮）；RANDOM_UNIT（PercentLow/High）没单独量 |
| 已对拍 | `人格/UnitModifier.Unit` | 1168 | a4 a5 a7 | 台上量过（engine_aiskirm u：aiskmod 把维和、标枪的 UnitModifier 两个系数都设 0，造兵逐秒和原版 aiskirm c 一样）、测试对拍 tests/test_simai.py——没有选兵策略表时 UnitModifier 不影响造什么；有策略表时的打分没量（原版人格都没有） |
| 已对拍 | `战略状态/StrategicState.Difficulty` | 1105 | a4 a5 a7 | docs/engine/aistate.md#按难度挂的状态（aidiff / aidiffx：普通 = MEDIUM，没挂 MEDIUM 的状态不跑） |
| 已对拍 | `人格/SpecificUnitCap.Unit` | 1005 | a4 a5 a7 | engine_aiskirm aiskcap:y（2026-11-12）：子人格给父人格没写的CNVNewPK四档Cap=2，新维和s33到2、停到s149（无上限aisknew2 s44已4），兵营改造标枪/维和；tests/test_simai_bench_b.py::test_a_specific_unit_cap_holds_our_unit_at_two按名回放、断言台上读数。E80父人格已有维和Cap=20时子人格Cap=2不生效=第一条命中（test_simai_bench_e.py）。gap：s150后又造到4、没死人，引擎拿什么数对上限未知（strict xfail test_after_s150_the_capped_unit_is_built_again）；见 work/re/handoff-b.md 第145节 |
| 已对拍 | `人格/SpecificUnitCap.Cap` | 852 | a4 a5 a7 | engine_aiskirm aiskcap:y（2026-11-12）：子人格给父人格没写的CNVNewPK四档Cap=2，新维和s33到2、停到s149（无上限aisknew2 s44已4），兵营改造标枪/维和；tests/test_simai_bench_b.py::test_a_specific_unit_cap_holds_our_unit_at_two按名回放、断言台上读数。E80父人格已有维和Cap=20时子人格Cap=2不生效=第一条命中（test_simai_bench_e.py）。gap：s150后又造到4、没死人，引擎拿什么数对上限未知（strict xfail test_after_s150_the_capped_unit_is_built_again）；见 work/re/handoff-b.md 第145节 |
| 已对拍 | `人格/UnitModifier.OffensiveModifier` | 821 | a4 a5 a7 | 台上量过（engine_aiskirm u：aiskmod 把维和、标枪的 UnitModifier 两个系数都设 0，造兵逐秒和原版 aiskirm c 一样）、测试对拍 tests/test_simai.py——没有选兵策略表时 UnitModifier 不影响造什么；有策略表时的打分没量（原版人格都没有） |
| 不涉及 | `表现/FeedbackEntry.FeedbackKey` | 812 |  | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/FeedbackEntry.FeedbackTo` | 812 |  | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/StrategicDirectiveFeedback.Event` | 747 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/StrategicDirectiveFeedback.FeedbackKey` | 747 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/StrategicDirectiveFeedback.StrategicDirective` | 747 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 已对拍 | `战术/Tactic.Tactic` | 713 | a4 a5 a7 | docs/engine/aitactics.md#读数（SimpleAttack / DefenseAvoidanceAttack / FlankAttack / StaticDefense 上台） |
| 已对拍 | `人格/UnitModifier.DefensiveModifier` | 712 | a4 a5 a7 | 台上量过（engine_aiskirm u：aiskmod 把维和、标枪的 UnitModifier 两个系数都设 0，造兵逐秒和原版 aiskirm c 一样）、测试对拍 tests/test_simai.py——没有选兵策略表时 UnitModifier 不影响造什么；有策略表时的打分没量（原版人格都没有） |
| 已对拍 | `组队招人/TeamTemplate.MicroManager` | 711 | a4 a5 a7 | 台上量过（engine_airetreat：airet / airet0 只差 MicroManager 指名的那份数据里的 RetreatPowerAdvantage，一个撤一个不撤；aipas1 / aipas0 只差 EngagePassiveTargets）、测试对拍 tests/test_simai.py——队伍跑的是 MicroManager 指名的那份微操数据；指名不存在的 id 会怎样没量 |
| 已对拍 | `战略状态/TargetHeuristic.Priority` | 686 | a4 a5 a7 | docs/engine/aitactics.md#目标挑哪个（aitpphi / aitpplo：同一状态两条目标启发，Priority 高的先试，两向都上台） |
| 已对拍 | `组队招人/TeamTemplate.IncludeKindOf` | 686 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 已对拍 | `组队招人/TeamTemplate.MaxUnits` | 675 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 不涉及 | `表现/FeedbackEntry.EvaEvent` | 644 |  | 纯表现（语音、视频、画面） |
| 已对拍 | `开局/Order.Build` | 635 | a4 a5 a7 | docs/engine/aiopen.md#读数（aiopen f1～f3：造的顺序和 AlliedStandard 单子一样） |
| 已对拍 | `组队招人/TeamTemplate.AllowedLocomotorTypes` | 585 | a4 a5 a7 | docs/engine/aistate.md#移动方式和对象集（第 81 轮） |
| 已对拍 | `造兵/BuildEntry.Heuristic` | 535 | a4 a5 a7 | E78 engine_aiskirm z：BEST_UNIT_EXPECTED 两组台上 PASS；[s150,s160) 征召兵组维和5→6、标枪0，锤子组标枪7→8→9、维和0；tests/test_simai_bench_e.py::test_best_unit_expected_infantry_choice 两组按来源断言通过（建造状态造的另一种=0；锤子组多的那个维和是单位生成器均匀抽签，台上 t 也抽2次：狗 s23、工程师 s144）；B 第 149 轮模拟器侧排除"一帧多单""队列非空仍下单"；FEWEST_UNIT 见 aisknew2 y、RANDOM_UNIT 见 aiskrand s；抽签结果属运气不对拍，"每次评估无条件掷一次随机数"没建模；见 work/re/e_aiheur_e78.md、work/re/handoff-b.md 第 149 节 |
| 不涉及 | `表现/SkirmishGameEventFeedback.Event` | 498 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/SkirmishGameEventFeedback.FeedbackKey` | 498 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 已对拍 | `组队招人/TeamTemplate.MinUnits` | 482 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `造兵/BuildEntry.Build` | 481 | a4 a5 a7 | 台上量过（engine_aiskirm y aisknew / aisknew2：没列进任何建造状态的我们的兵不造、列成 FEWEST_UNIT 占兵营约一半；z aiskvinf / aiskvveh：BEST_UNIT_EXPECTED 兵营只造克制兵），测试对拍 tests/test_simai_bench_b.py（B 第 126–131 轮）；RANDOM_UNIT（PercentLow/High）没单独量 |
| 已对拍 | `造兵/CountAsStructureForBuildPurposesFilter.ExcludeThing` | 459 | a4 a5 a7 | C engine_aibuildexclude：旧aibex/aibin直接过滤New/Dear=0/1，IncludeThing优先；新aibxo/aibxi:x类别Include INFANTRY、无Dear的IncludeThing，仅切Dear的ExcludeThing，直接过滤分别1/0和1/1；New首成功f343均走SD，Dear首成功f409分别走U/SD，两局PASS。tests/test_build_exclude.py按名加载台子并对拍过滤、同帧工厂候选篮子及请求；现有模型吻合，无模型修改。整体产兵资格/时钟仍gap，两旧整局回放保留strict xfail；见work/re/c_buildexclude_follow_report.md |
| 已对拍 | `战术/Tactic.EndBehavior` | 454 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aihome.py |
| 已对拍 | `战略状态/AIStrategicStateDefinition.MaxTargets` | 430 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `组队招人/ObjectFilter.ExcludeThing` | 425 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aibuildexclude.py |
| 已对拍 | `经济/BudgetState.State` | 410 | a4 a5 a7 | engine_aitower aibsprod h（2026-11-13）：人格自己声明 DEFENSE 50% 的预算，唯一一行 BudgetState 的 State 指原版 ProductionOnlyBudget（DEFENSE 0%）：开局 2 万、到 s160 一座塔也不造，钱只随矿车涨——State 指哪个预算定义就用哪个的份额。tests/test_simai_bench_b.py::test_a_budget_state_line_uses_the_budget_its_state_names按名回放；自建预算那几局（aitowerinc10 / inc5）同一规则。见 work/re/handoff-b.md 第177节。多行时选哪一个（work/re/d122_ai_rules.md 第1节）：engine_aitower aibsmax / aibstie / aibszero i（2026-11-13 三局 PASS）——权重最大的一个单独生效、不混合份额，并列取靠前，全 0 取第一条；tests/test_simai_bench_b.py 的 test_the_heavier_budget_state_runs_alone_though_listed_second 等三条。敌人进出时切回（d122 R4）：engine_aitower aibsback r4（2026-11-14 PASS，原版四个预算、开局立刻完、5000）：Coop 5% 到 s48 无塔；4 辆守护者在 700 内 s29–s57 → s49 一座塔；撤走后 s73 再给 5000 不造第二座（又回 Coop）。test_the_retail_budgets_switch_to_defense_while_the_raid_is_near_and_back_after |
| 已对拍 | `经济/ResourceMultiplierCheat.Difficulty` | 398 | a4 a5 a7 | engine_aitower aicheat2 / aicheat1 g（2026-11-13，台上 MEDIUM，矿车每趟 250）：MEDIUM 200% → 每趟 500；EASY HARD BRUTAL 300% + MEDIUM 100% → 每趟 250（与没写的 aitowerinc5 同）——Percentage 就是倍率本身，难度不含当前难度的行跳过；原版 EASY 100% / BRUTAL 200% 两种取值都在内。tests/test_simai_bench_b.py::test_a_medium_cheat_line_of_200_percent_doubles_each_trip、test_a_100_percent_line_and_lines_for_other_difficulties_change_nothing按名回放。gap：多行同难度取哪条（取第一条，INFERRED）、卖楼等其他入账也乘（l2_mining 读到，没上台）；见 work/re/handoff-b.md 第176节 |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType` | 392 | a4 a5 a7 | docs/engine/aitactics.md#读数（ClosestStructure / SafestToGroundStructure 是 EnemyStructure，FriendlyLandStructure 是 FriendlyStructure，都上台） |
| 已对拍 | `组队招人/TeamTemplate.Priority` | 374 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | `组队招人/TeamTemplate.ExcludeKindOf` | 369 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 已对拍 | `组队招人/TeamTemplate.AlwaysRecruit` | 365 | a4 a5 a7 | 台上量过（engine_aiteamfilter aiar0～3，第 90 轮）、测试对拍 tests/test_simai_bench_b.py：关着新造的车留家、开着出门的队把它招走、满员不招、不预放时第一辆自己组队（模拟器每次晚 3～4 s）；模拟器多造第 3、4 辆是造兵的缺口（strict xfail），不是这个开关 |
| 已对拍 | `战术/Tactic.EndBehavior=DISBAND` | 348 | a4 a5 a7 | docs/engine/aitactics.md#目标没了以后（EndBehavior，2026-11-09 各一次）（aiendd：目标没了队伍解散、状态重派去兵营，和模型对上） |
| 已对拍 | `人格/SpecificUnitCap.Difficulty` | 317 | a4 a5 a7 | engine_aiskirm aiskcap:y（2026-11-12）：子人格给父人格没写的CNVNewPK四档Cap=2，新维和s33到2、停到s149（无上限aisknew2 s44已4），兵营改造标枪/维和；tests/test_simai_bench_b.py::test_a_specific_unit_cap_holds_our_unit_at_two按名回放、断言台上读数。E80父人格已有维和Cap=20时子人格Cap=2不生效=第一条命中（test_simai_bench_e.py）。gap：s150后又造到4、没死人，引擎拿什么数对上限未知（strict xfail test_after_s150_the_capped_unit_is_built_again）；见 work/re/handoff-b.md 第145节 |
| 已对拍 | `战术/Tactic.Tactic=SimpleAttack` | 315 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 已对拍 | `启发条件/ConstantHeuristic` | 298 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipoweradv.py |
| 已对拍 | `人格/UnitCap.Cap` | 295 |  | engine_aiskirm aiskuc uc（2026-11-13，台上 MEDIUM）：子人格写 Cap 3 MEDIUM + Cap 1 EASY HARD BRUTAL，兵数（矿车以外）s37 到 4、停到 s110（原版 aiskirm c 约 s60 已 8 个步兵）——严格大于最小匹配上限才停，别的难度那行跳过；建筑照造。tests/test_simai_bench_b.py::test_a_medium_unit_cap_of_3_holds_the_army_at_4按名回放。原版只有 Cap 100 一种取值（够不着，规则同一条）。s111 后涨到 10 = 开局表末尾 3 辆激流（开局下单不过 UnitCap 门；计数同时列了激流两个模板名，_Ground 等同于前者，每辆算两次），第183轮转正 test_after_s110_the_opening_riptides_pass_the_unit_cap。第179轮：aiskuc7 uc（Cap 7）兵数 s55–s111 停在 7、第一辆矿车 s53 → 矿车算进单位数（test_the_unit_cap_counts_the_miners）；aiskucn ucn（建造状态列新维和 + Cap 3）兵数 5、新维和 2 停到 s111 → 建造状态的单位单也过这道门（test_the_unit_cap_holds_the_build_states_unit_too） |
| 已对拍 | `启发条件/ScriptedFlagHeuristic` | 289 |  | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py:y |
| 已对拍 | `启发条件/ScriptedFlagHeuristic.FlagName` | 289 |  | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | `人格/UnitCap.Difficulty` | 283 |  | engine_aiskirm aiskuc uc（2026-11-13，台上 MEDIUM）：子人格写 Cap 3 MEDIUM + Cap 1 EASY HARD BRUTAL，兵数（矿车以外）s37 到 4、停到 s110（原版 aiskirm c 约 s60 已 8 个步兵）——严格大于最小匹配上限才停，别的难度那行跳过；建筑照造。tests/test_simai_bench_b.py::test_a_medium_unit_cap_of_3_holds_the_army_at_4按名回放。原版只有 Cap 100 一种取值（够不着，规则同一条）。s111 后涨到 10 = 开局表末尾 3 辆激流（开局下单不过 UnitCap 门；计数同时列了激流两个模板名，_Ground 等同于前者，每辆算两次），第183轮转正 test_after_s110_the_opening_riptides_pass_the_unit_cap。第179轮：aiskuc7 uc（Cap 7）兵数 s55–s111 停在 7、第一辆矿车 s53 → 矿车算进单位数（test_the_unit_cap_counts_the_miners）；aiskucn ucn（建造状态列新维和 + Cap 3）兵数 5、新维和 2 停到 s111 → 建造状态的单位单也过这道门（test_the_unit_cap_holds_the_build_states_unit_too） |
| 已对拍 | `经济/ResourceMultiplierCheat.Percentage` | 280 | a4 a5 a7 | engine_aitower aicheat2 / aicheat1 g（2026-11-13，台上 MEDIUM，矿车每趟 250）：MEDIUM 200% → 每趟 500；EASY HARD BRUTAL 300% + MEDIUM 100% → 每趟 250（与没写的 aitowerinc5 同）——Percentage 就是倍率本身，难度不含当前难度的行跳过；原版 EASY 100% / BRUTAL 200% 两种取值都在内。tests/test_simai_bench_b.py::test_a_medium_cheat_line_of_200_percent_doubles_each_trip、test_a_100_percent_line_and_lines_for_other_difficulties_change_nothing按名回放。gap：多行同难度取哪条（取第一条，INFERRED）、卖楼等其他入账也乘（l2_mining 读到，没上台）；见 work/re/handoff-b.md 第176节 |
| 已对拍 | `组队招人/ObjectFilter.Rule` | 263 | a4 a5 a7 | docs/engine/aistate.md#队伍招谁（aitfany / aitfnone / aitfall：ANY、NONE + 名单只要名单，ALL + 排除名单） |
| 已对拍 | `目标/AITargetingHeuristic.Name` | 241 |  | docs/engine/ainamed.md#给关卡线的结论（ainmfar 点名物件不管远近、ainmwp 走到路点守着、ainmnone 名字查不到不派队，全 PASS） |
| 已对拍 | `组队招人/ObjectFilter.IncludeThing` | 239 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aibuildexclude.py |
| 已对拍 | `开局/Order.Time` | 237 | a4 a5 a7 | docs/engine/aiopen.md#开局里的 Time 从什么时候算（aiotime：从唤醒起的绝对时刻） |
| 已对拍 | `战术/Tactic.DisbandAfterRetreatTeamSize` | 205 | a4 a5 a7 | 台上量过（engine_airetreat：airetf 0 撤回家后再出门，airetfd 999 撤回家后一直在家——撤退结束那轮人数 ≤ 它就结束战术、放人）、测试对拍 tests/test_simai.py；1 / 4 / 5 这种"剩几人才散"的中间值没量 |
| 已对拍 | `人格/AIPersonalityDefinition.PersonalityType` | 184 | a4 a5 a7 | tests/test_simai_bench_b.py::test_the_personality_condition_matches_the_id_not_the_personality_type（engine_aiskirm pt aiskpt / aiskpti：脚本条件 PLAYER_IS_HUMAN_OR_AI_PERSONALITY 只认人格 id，PersonalityType 写成别的名字或不写都不影响；AI 行为不读它；B 第 150 轮） |
| 已对拍 | `组队招人/TeamTemplate.RegisteredObjectSet` | 179 | a4 a5 a7 | docs/engine/aistate.md#移动方式和对象集（第 81 轮） |
| 已对拍 | `组队招人/CreateUnits.UnitName` | 174 | a4 a5 a7 | engine_aicreate aicr1c/aicr3c：最低1是一名新成员加两名已知预摆维和，最低3等三名新成员；tests/test_simai_bench_c.py按名回放首次组成；新成员兵种由固定生产归属仍INFERRED；仅指定最低数优先再普通补位，不是排他过滤；其他兵种/多槽位/替补仍gap；见 work/re/e_create_e88.md |
| 不涉及 | `表现/FeedbackEntry.Video` | 168 |  | 纯表现（语音、视频、画面） |
| 已对拍 | `人格/AIPersonalityDefinition.Side` | 166 | a4 a5 a7 | B184 engine_aiskirm sd（work/re/d123_side.md 第3节；s1 阵营 Japan，人格 CNVSideX 只写 Side Soviet）：aisksd1 SkirmishPersonality=false（27 关全是这样）人格位 9 = 照用 CNVSideX，Side 不符不管；aisksd2 =true → 136 = 换成随机的日本人格（2JapanMechaWarfare）。27 关 Side 不起作用；test_a_personality_whose_skirmish_gate_is_closed_is_used_whatever_its_side 按名回放；门开着换人格 B207 进模拟器（模型 AIData.assigned_personality，随机抽签对不齐，只断言"不是 CNVSideX、是日本人格"）：test_a_skirmish_personality_of_another_side_is_replaced |
| 已对拍 | `人格/AIPersonalityDefinition.UsePlayerPowersAtDifficulty` | 154 |  | B181 engine_aispecial aispecoff / aispechb:t（1AlliedBalanced 子人格只改这个字段，台上 MEDIUM）："" 和 "HARD BRUTAL" 两局技能第 2 帧就绪、到第 950 帧放帧 0；对照 aispecial t（XSD 缺省四档全开）第 61 帧放。模型 RA3-EngineModel tests/test_ai_bench.py::test_special_use_at_difficulty 按名回放（None / "" / HB / MEDIUM）。gap：simai 不放超武，只在模型层对拍 |
| 已对拍 | `目标/AITargetingHeuristic.RequireUniqueTarget` | 154 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | `人格/AIPersonalityDefinition.RepairBuildingsAtDifficulty` | 153 | a4 a5 a7 | B181 engine_repair_ai repairoff / repairmed:a（repair_bench 只改这个字段，USE_REPAIRS 开、钱 10000）："" 整局 50 / 50 / 10000 不修；"MEDIUM" 每秒 +1%，s49 起 100 / 50 / 9900（同 repairai 四档全开）。tests/test_simrepair_ai.py 按名回放两局 |
| 已对拍 | `造兵/CountAsStructureForBuildPurposesFilter.Include` | 153 | a4 a5 a7 | B第198轮 engine_aibuildexclude x：原版过滤（Rule ANY、Include STRUCTURE UNPACKS_INTO_BUILDING）去掉 IncludeThing，只改 Rule：aibxall（ALL）五种兵的候选 flt 全 1、下单走 SD 篮；aibxany（ANY）全 0、走 U 篮；aibxi（Include 加 INFANTRY）两种维和都过——Include 按 KindOf 认、ALL 不看 Include。tests/test_build_exclude.py 按名加载三台子、断言模型过滤和篮子；模型没改。Rule NONE、Exclude 类别没上台 |
| 已对拍 | `造兵/CountAsStructureForBuildPurposesFilter.Rule` | 153 | a4 a5 a7 | B第198轮 engine_aibuildexclude x：原版过滤（Rule ANY、Include STRUCTURE UNPACKS_INTO_BUILDING）去掉 IncludeThing，只改 Rule：aibxall（ALL）五种兵的候选 flt 全 1、下单走 SD 篮；aibxany（ANY）全 0、走 U 篮；aibxi（Include 加 INFANTRY）两种维和都过——Include 按 KindOf 认、ALL 不看 Include。tests/test_build_exclude.py 按名加载三台子、断言模型过滤和篮子；模型没改。Rule NONE、Exclude 类别没上台 |
| 已对拍 | `人格/AIPersonalityDefinition.DesiredExcessPowerBuffer` | 150 | a4 a5 a7 | B122 engine_aiskirm x 三局（aiskpw0 / aiskirm / aiskpw3 = 缓冲 0 / 100 / 300）：开局后多造电厂 0 / 2 / 4 座，一座接一座（唤醒后 ~130 / 140 / 150 / 160 s）。B182 模型 POWER 启发照读到的规则（产电 + 在队列里的电量 对 耗电 + 缓冲；建造场算、刚放下还在展开的电厂两边都不算）三局数量和时刻都对上，tests/test_simai.py::test_desired_excess_power_buffer_* 按名回放。gap：敌人压境（500 内价值 ≥1000）那道门没上台；缓冲 300 时空军台上晚 17 s 没解释（strict xfail） |
| 已对拍 | `人格/AIPersonalityDefinition.BuildTechMinPowerAdvantage` | 149 | a4 a5 a7 | B181 engine_aiskirm aiskmtp:mt（aiskmt40 加 BuildTechMinPowerAdvantage=1000）：到 s810（科技帧 12159）没造科技楼；aiskmt40（继承 1.25）f5857 造。模型 tech_score 在 MinTime..ForceTime 窗口里加兵力比门（RA3-EngineModel tests/test_ai_tech.py），tests/test_simai_mintime.py::test_a_power_advantage_of_1000_keeps_the_tech_building_away 按名回放两局。gap：兵力比怎么算没读（台上只知道在 [1.25, 1000) 之间），simai 不给比值 |
| 已对拍 | `战术/Tactic.Tactic=StaticDefense` | 149 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aibasedef.py |
| 已对拍 | `人格/AIPersonalityDefinition.ConyardInDangerEmergencyEngineerDistance` | 148 | a4 a5 a7 | B181 一局证一批 engine_aiskirm aiskinb:ib vs aiskirm:ib（同一次排队，都 PASS）：七个字段一次改成极端值（ConyardInDanger 三项 1000s / 100% / 5000、HoldObjectBeaconRadius 5000、ResourceNodeValueRemainingForExpansion 1000000、DefaultThreatFindRadius 5000、MaxWallDestroyTimeToCountAsGoThroughWalls 1000s），AI钱 / 建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s 开局相位）；tests/test_simai_bench_b.py::test_seven_inert_personality_fields_change_nothing。为什么不起作用：D126 难度门 EmergencyManagerHandleConyardInDangerAtDifficulty 94 个人格全空。gap：台上没有围攻建造厂、没有墙、没有协同信标，只证"27 关的门关着时不起作用" |
| 已对拍 | `人格/AIPersonalityDefinition.ConyardInDangerEmergencyHealthPercent` | 148 | a4 a5 a7 | B181 一局证一批 engine_aiskirm aiskinb:ib vs aiskirm:ib（同一次排队，都 PASS）：七个字段一次改成极端值（ConyardInDanger 三项 1000s / 100% / 5000、HoldObjectBeaconRadius 5000、ResourceNodeValueRemainingForExpansion 1000000、DefaultThreatFindRadius 5000、MaxWallDestroyTimeToCountAsGoThroughWalls 1000s），AI钱 / 建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s 开局相位）；tests/test_simai_bench_b.py::test_seven_inert_personality_fields_change_nothing。为什么不起作用：D126 难度门 EmergencyManagerHandleConyardInDangerAtDifficulty 94 个人格全空。gap：台上没有围攻建造厂、没有墙、没有协同信标，只证"27 关的门关着时不起作用" |
| 已对拍 | `人格/AIPersonalityDefinition.ConyardInDangerEmergencyUnderAttackTime` | 148 | a4 a5 a7 | B181 一局证一批 engine_aiskirm aiskinb:ib vs aiskirm:ib（同一次排队，都 PASS）：七个字段一次改成极端值（ConyardInDanger 三项 1000s / 100% / 5000、HoldObjectBeaconRadius 5000、ResourceNodeValueRemainingForExpansion 1000000、DefaultThreatFindRadius 5000、MaxWallDestroyTimeToCountAsGoThroughWalls 1000s），AI钱 / 建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s 开局相位）；tests/test_simai_bench_b.py::test_seven_inert_personality_fields_change_nothing。为什么不起作用：D126 难度门 EmergencyManagerHandleConyardInDangerAtDifficulty 94 个人格全空。gap：台上没有围攻建造厂、没有墙、没有协同信标，只证"27 关的门关着时不起作用" |
| 已对拍 | `人格/AIPersonalityDefinition.DefaultThreatFindRadius` | 148 | a4 a5 a7 | B181 一局证一批 engine_aiskirm aiskinb:ib vs aiskirm:ib（同一次排队，都 PASS）：七个字段一次改成极端值（ConyardInDanger 三项 1000s / 100% / 5000、HoldObjectBeaconRadius 5000、ResourceNodeValueRemainingForExpansion 1000000、DefaultThreatFindRadius 5000、MaxWallDestroyTimeToCountAsGoThroughWalls 1000s），AI钱 / 建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s 开局相位）；tests/test_simai_bench_b.py::test_seven_inert_personality_fields_change_nothing。为什么不起作用：D127 只写进目标槽、零读者。gap：台上没有围攻建造厂、没有墙、没有协同信标，只证"27 关的门关着时不起作用" |
| 已对拍 | `人格/AIPersonalityDefinition.MaxWallDestroyTimeToCountAsGoThroughWalls` | 148 | a4 a5 a7 | B181 一局证一批 engine_aiskirm aiskinb:ib vs aiskirm:ib（同一次排队，都 PASS）：七个字段一次改成极端值（ConyardInDanger 三项 1000s / 100% / 5000、HoldObjectBeaconRadius 5000、ResourceNodeValueRemainingForExpansion 1000000、DefaultThreatFindRadius 5000、MaxWallDestroyTimeToCountAsGoThroughWalls 1000s），AI钱 / 建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s 开局相位）；tests/test_simai_bench_b.py::test_seven_inert_personality_fields_change_nothing。为什么不起作用：D127 读它的循环遍历的列表从不被填。gap：台上没有围攻建造厂、没有墙、没有协同信标，只证"27 关的门关着时不起作用" |
| 已对拍 | `人格/AIPersonalityDefinition.ReactiveDefenseRadius` | 148 | a4 a5 a7 | B199 engine_aireactive aireact750/aireact1200：ReactiveDefense 单状态、敌人在基地正南 1000，仅半径不同；750 全程不动（家300 4、敌存活 1 到 s80），1200 s8 全员出门、s20 敌人死；tests/test_simai_bench_b.py::test_reactive_defense_radius_gates_the_chase 按名回放（模拟器 s10 出门、s23 打死）。原版 27 关没有状态用 ReactiveDefense（只有 PCG 演示状态），只证半径门；精确边界、R×1.25 到位、美学站位没量 |
| 已对拍 | `人格/AIPersonalityDefinition.RefineryPlacementIncreaseTickAmount` | 148 | a4 a5 a7 | B185 / B186 engine_aiskirm aiskinp:ib、aiskin1:rp、aiskin0:rp vs aiskirm（都 PASS）：aiskinp 和另两项一起改成 1000（单改没上台）；1AlliedBalanced 的 -30 / 30 / 15 只两座矿场，改了之后 s148 在东矿出第三座、s188 / s223 再各一座。模拟器（B189 simai Brain.refinery_spot + 模型 REFINERY 150 分）照 d125 第 1 节排矿点、D136 第 5 节固定圈 + 矿点朝向 ±k·π/16 七个方向、Ticks ≤ 0 不转圈（读到）；B188 rpx 坐标：aiskirm 两座落各东矿点第 5 圈 −3 档（条带 x26 y9 / x28 y11，模拟器逐条对上）、不造第三座；tests/test_simai_bench_b.py::test_stock_refineries_stand_on_ring_5_of_each_east_node_at_minus_three_sixteenths 等。B191 照 D138 换成读到的：预检（各矿点默认位 S 的外形相交 + 通道点 150）、方向顺序 0/−1/+1/−2/+2/−3/+3、"还要不要矿场" = 矿点前方点在建造半径 600 + 75 内。gap：第 4 圈 −3 档模拟器放得下、台上放不下（aiskirm 差一条带，strict xfail，外形没读）；找位失败退到建造厂旁的摆放（F1）位置不对；"已服务"300、只试要矿场的矿点仍 INFERRED |
| 已对拍 | `人格/AIPersonalityDefinition.RefineryPlacementNumberOfIncreaseTicksBeforeGivingUp` | 148 | a4 a5 a7 | B185 / B186 engine_aiskirm aiskinp:ib、aiskin1:rp、aiskin0:rp vs aiskirm（都 PASS）：aiskin0 只改成 0；1AlliedBalanced 的 -30 / 30 / 15 只两座矿场，改了之后 s148 在东矿出第三座、s188 / s223 再各一座。模拟器（B189 simai Brain.refinery_spot + 模型 REFINERY 150 分）照 d125 第 1 节排矿点、D136 第 5 节固定圈 + 矿点朝向 ±k·π/16 七个方向、Ticks ≤ 0 不转圈（读到）；B188 rpx 坐标：aiskirm 两座落各东矿点第 5 圈 −3 档（条带 x26 y9 / x28 y11，模拟器逐条对上）、不造第三座；tests/test_simai_bench_b.py::test_stock_refineries_stand_on_ring_5_of_each_east_node_at_minus_three_sixteenths 等。B191 照 D138 换成读到的：预检（各矿点默认位 S 的外形相交 + 通道点 150）、方向顺序 0/−1/+1/−2/+2/−3/+3、"还要不要矿场" = 矿点前方点在建造半径 600 + 75 内。gap：第 4 圈 −3 档模拟器放得下、台上放不下（aiskirm 差一条带，strict xfail，外形没读）；找位失败退到建造厂旁的摆放（F1）位置不对；"已服务"300、只试要矿场的矿点仍 INFERRED |
| 已对拍 | `人格/AIPersonalityDefinition.RefineryPlacementStartDistanceDelta` | 148 | a4 a5 a7 | B185 / B186 engine_aiskirm aiskinp:ib、aiskin1:rp、aiskin0:rp vs aiskirm（都 PASS）：aiskin1 只改成 1000；1AlliedBalanced 的 -30 / 30 / 15 只两座矿场，改了之后 s148 在东矿出第三座、s188 / s223 再各一座。模拟器（B189 simai Brain.refinery_spot + 模型 REFINERY 150 分）照 d125 第 1 节排矿点、D136 第 5 节固定圈 + 矿点朝向 ±k·π/16 七个方向、Ticks ≤ 0 不转圈（读到）；B188 rpx 坐标：aiskirm 两座落各东矿点第 5 圈 −3 档（条带 x26 y9 / x28 y11，模拟器逐条对上）、不造第三座；tests/test_simai_bench_b.py::test_stock_refineries_stand_on_ring_5_of_each_east_node_at_minus_three_sixteenths 等。B191 照 D138 换成读到的：预检（各矿点默认位 S 的外形相交 + 通道点 150）、方向顺序 0/−1/+1/−2/+2/−3/+3、"还要不要矿场" = 矿点前方点在建造半径 600 + 75 内。gap：第 4 圈 −3 档模拟器放得下、台上放不下（aiskirm 差一条带，strict xfail，外形没读）；找位失败退到建造厂旁的摆放（F1）位置不对；"已服务"300、只试要矿场的矿点仍 INFERRED |
| 已对拍 | `人格/AIPersonalityDefinition.ResourceNodeSearchRadius` | 148 | a4 a5 a7 | B185 engine_aiskirm aiskind:ib vs aiskirm:ib（都 PASS）：1AlliedBalanced 子人格只把它从 700 改成 5000，建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s）；tests/test_simai_bench_b.py::test_a_resource_node_search_radius_of_5000_changes_nothing_on_a_plain_skirmish。D125 第 1 节：只给矿点排先后（半径内先试），不排除远处矿点。gap：台上只有基地旁的矿，两个矿点的排序台子（d125 第 1 节）没上 |
| 已对拍 | `人格/AIPersonalityDefinition.ResourceNodeValueRemainingForExpansion` | 148 | a4 a5 a7 | B181 一局证一批 engine_aiskirm aiskinb:ib vs aiskirm:ib（同一次排队，都 PASS）：七个字段一次改成极端值（ConyardInDanger 三项 1000s / 100% / 5000、HoldObjectBeaconRadius 5000、ResourceNodeValueRemainingForExpansion 1000000、DefaultThreatFindRadius 5000、MaxWallDestroyTimeToCountAsGoThroughWalls 1000s），AI钱 / 建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s 开局相位）；tests/test_simai_bench_b.py::test_seven_inert_personality_fields_change_nothing。为什么不起作用：D125 第 2 节只拷贝不读。gap：台上没有围攻建造厂、没有墙、没有协同信标，只证"27 关的门关着时不起作用" |
| 已对拍 | `人格/AIPersonalityDefinition.SecondsTillTargetsExpire` | 148 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `人格/AIPersonalityDefinition.UnitBuilderOverallDefensivePreference` | 148 | a4 a5 a7 | B199 engine_aiskirm z aiskvd9（aiskvveh 布局，仅此项 1000%）：维和 s30 起到 s196 共 14、标枪 s151 才有、s222 共 7；原版 25% 的 aiskvveh 和 aiskvd0（0%）都只造标枪（0%：s29 起到 s169 共 11、维和 0）。B228：只乘候选血量（读到）；再按读到的两条——K 的建造时间是帧（×15）、模板对打每槽只算一把不要升级 / 状态的武器（锤子只算吸血光束）——模拟器首发 d9 维和、d0 / vveh 标枪，tests/test_simai_bench_b.py::test_the_defensive_preference_turns_the_first_pick_against_tanks 按名回放。没对上：d9 模拟器标枪 s60 左右就出（台上 s151） |
| 已对拍 | `人格/DefaultTacticHomeBaseCriteria.PreferredNotBaseTypes` | 148 | a4 a5 a7 | B201 engine_aihome aihmgno：同上，PREFER_CLOSEST + PreferredNotBaseTypes OLDEST_OF_TYPE → 不回近的 A、回 B（s30 起家B 4），反偏好压过排序；同一测试按名回放。原版写的 CAPTURED 要占领来的基地才分得出，没量 |
| 已对拍 | `人格/DefaultTacticHomeBaseCriteria.SortOrder` | 148 | a4 a5 a7 | B201 engine_aihome aihmgcl/aihmgnw：两座初始建造厂（A 先放、B 在北 1350），SimpleAttack 打 A 西 ~700 的具名电厂、RETURN_HOME_AND_DISBAND，仅人格这条不同；PREFER_NEWEST 电厂没后全员回 B（s36 起家B 4），PREFER_CLOSEST 选 A、队伍中心已在 600 内 → 原地解散不走（到电厂 4 到 s88）；tests/test_simai_bench_b.py::test_return_home_picks_the_base_by_the_personality_criteria 按名回放。CLOSEST 的量点（队伍中心）是推断，OLDEST/SMALLEST 等其余排序没量 |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=NamedObject` | 145 |  | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_ainamed.py |
| 已对拍 | `战术/Tactic.Distance` | 144 | a4 a5 a7 | D169晋升：bench engine_aisimpleexp aiexpb400/aiexpb200/aiexpb50只差SimpleExpansion的Distance，台上400/200在离矿点397/194处原地展开前哨、50走到离矿点98停下不展开；tests/test_expansion_target.py三局按名回放、正常断言（矿点按自身外接圆53挡路后50那局也对上）。旧记录：专用engine_aidistance aidist250/aidist2000保留AI队、同次传送1200，仅Distance不同；s65小组圈300/900=1/1，大组0/0，存活均1；两组各5条PASS、模型末态匹配；大组实机传送前离300、传送后回900再离，模型美学轨迹strict xfail；精确边界/动态队成员仍gap，不晋升；tests/test_simai_bench_c.py；见 work/re/c_distance_report.md |
| 已对拍 | `启发条件/TimerHeuristic` | 138 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/TimerHeuristic.StartTime` | 137 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/IntervalHeuristic` | 132 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `目标/AITargetingHeuristic.VitalKindOf` | 129 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 已对拍 | `启发条件/TimerHeuristic.CountFrom` | 126 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `组队招人/TeamTemplate.Priority=HIGH` | 126 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | `组队招人/TeamTemplate.Priority=STANDARD` | 126 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | `启发条件/IntervalHeuristic.IntervalTime` | 125 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `人格/AIPersonalityDefinition.BaseCompactness` | 122 | a4 a5 a7 | 台上量过（engine_aitower b / c：0.5 / 0.75 / 1.0 的基地防御塔离建造场 ~296 / 420–442 / 590–620）、测试对拍 tests/test_simai_bench_b.py（B 第 198 轮：模拟器的基地防御塔改用模型的 tower_spots，半径 = (BaseCompactness ± 0.05) × ~600）；只量了防御塔，其他建筑的摆放（模拟器的建造场圈）不读它 |
| 已对拍 | `启发条件/IntervalHeuristic.ActiveTime` | 118 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `组队招人/TeamTemplate.ReleaseType` | 117 | a4 a5 a7 | engine_aiskirm aiskirm:m 实机（11-11 CampAISkirmM_mcp_1111_221811）s125-128防御8/清扫99，s129防御0/清扫8，池兵0、转队时逐帧兵池峰1：DEFENSE队RELEASE_TO_PRIORITY放人给STANDARD清扫队，一个采样内直接转、不经兵池。模拟器按引擎队名读AI队（A第202轮：状态_战术类型_a_b、defaultSkirmishTeam<玩家>、不存在的队条件为假）；tests/test_simai_bench_c.py::test_release_to_priority_named_transfer_skips_the_pool按名回放、断言台上读数（防御稳定、减少数=清扫人数、池兵0、峰1、s129±3）。NEVER_RELEASE见上一行。gap：人数——模型（fca219e）s131防御9→0/清扫99→9，实机8（模型多造1个，造兵归B）；s134池峰2模型没有（strict xfail test_release_to_priority_transfers_defense_without_a_pool_round_trip）；ALWAYS_RELEASE、精确时钟仍gap；见 work/re/handoff.md 第202轮、c_release_report.md |
| 已对拍 | `战术/Tactic.Tactic=DefenseAvoidanceAttack` | 115 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `人格/AIPersonalityDefinition.CleanupRefineries` | 112 | a4 a5 a7 | B185 一局证一批 engine_aiskirm aiskins:ib vs aiskirm:ib（都 PASS）：七个字段一次改成 27 关敌方人格的值 / 极端值（CleanupRefineries false、CoopPersonality false、Assault / HoldPosition BeaconRadius 5000、EmergencyManagerHandle NoIncome / NoConyard / UnderAttack ""；1AlliedBalanced 继承的是 Coop 那套），建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s）；tests/test_simai_bench_b.py::test_seven_conditional_personality_fields_change_nothing_on_a_plain_skirmish。D126：矿采空后每 45 帧卖矿场。gap：D126 读成"条件满足才起作用"，台上条件都不满足（矿没采空、没有人类盟友和信标、建造厂在、有收入），起作用的那半没上台（d126 第 3 节的对照台子） |
| 已对拍 | `战术/Tactic.EndIfStateTurnsOff` | 108 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | `开局/OpeningMove.Name` | 107 | a4 a5 a7 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（每个探针按名字挂自写开局，都照它造） |
| 已对拍 | `目标/AITargetingHeuristic.ForbiddenKindOf` | 102 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 已对拍 | `组队招人/TeamTemplate.SortByDistance` | 96 | a4 a5 a7 | 专用engine_aisort aisort0/aisort1：容量1，关闭远候选f177先离、开启近候选f178先离，另一名留原位；固定到目标距离约985/700、到基地顺序相反；tests/test_simai_bench_c.py::test_sort_by_distance_replays_named_departure按名断言两组台内计数并回放匹配；已对拍限具名候选离开顺序；招走解释仍INFERRED，同帧动态队成员ID/实际距离和等距规则仍gap；见 work/re/c_sort_report.md |
| 已对拍 | `微操/AIMicroManagerData.RetreatPowerAdvantage` | 94 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_airetreat.py |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=Waypoint` | 94 |  | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_ainamed.py |
| 已对拍 | `组队招人/CreateUnits.MinUnits` | 93 | a4 a5 a7 | engine_aicreate aicr1c/aicr3c：最低1在(301,316]帧激活，最低3在(631,646]帧激活；后者f316一人/f481两人均未激活；tests/test_simai_bench_c.py按名回放激活区间和成员；仅孤立单槽位最低数1/3，多槽位/替补/MaxUnits仍gap；s70额外造兵另有strict xfail；见 work/re/e_create_e88.md |
| 不涉及 | `人格/AIPersonalityDefinition.CommanderPortrait` | 92 |  | 纯表现（语音、视频、画面） |
| 已对拍 | `组队招人/CreateUnits.MaxUnits` | 90 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `组队招人/TeamTemplate.MinPowerAdvantage` | 86 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | `微操/AIMicroManagerData.EnterGarrisons` | 84 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aigarrison.py |
| 已对拍 | `造兵/BuildState.Difficulty` | 84 | a4 a5 a7 | 台上量过（engine_aiskirm s aiskdiff：只挂 HARD 的建造状态在普通难度一个不造，挂 MEDIUM 的照造），测试对拍 tests/test_simai_bench_b.py |
| 已对拍 | `人格/AIPersonalityDefinition.AssaultBeaconRadius` | 83 | a4 a5 a7 | B185 一局证一批 engine_aiskirm aiskins:ib vs aiskirm:ib（都 PASS）：七个字段一次改成 27 关敌方人格的值 / 极端值（CleanupRefineries false、CoopPersonality false、Assault / HoldPosition BeaconRadius 5000、EmergencyManagerHandle NoIncome / NoConyard / UnderAttack ""；1AlliedBalanced 继承的是 Coop 那套），建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s）；tests/test_simai_bench_b.py::test_seven_conditional_personality_fields_change_nothing_on_a_plain_skirmish。D126：协同 AI 扫人类伙伴的进攻信标。gap：D126 读成"条件满足才起作用"，台上条件都不满足（矿没采空、没有人类盟友和信标、建造厂在、有收入），起作用的那半没上台（d126 第 3 节的对照台子） |
| 已对拍 | `人格/AIPersonalityDefinition.CoopPersonality` | 83 | a4 a5 a7 | B185 一局证一批 engine_aiskirm aiskins:ib vs aiskirm:ib（都 PASS）：七个字段一次改成 27 关敌方人格的值 / 极端值（CleanupRefineries false、CoopPersonality false、Assault / HoldPosition BeaconRadius 5000、EmergencyManagerHandle NoIncome / NoConyard / UnderAttack ""；1AlliedBalanced 继承的是 Coop 那套），建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s）；tests/test_simai_bench_b.py::test_seven_conditional_personality_fields_change_nothing_on_a_plain_skirmish。D126：给人类玩家挑协同 AI，只对友方 AI 有意义。gap：D126 读成"条件满足才起作用"，台上条件都不满足（矿没采空、没有人类盟友和信标、建造厂在、有收入），起作用的那半没上台（d126 第 3 节的对照台子） |
| 已对拍 | `人格/AIPersonalityDefinition.HoldObjectBeaconRadius` | 83 | a4 a5 a7 | B181 一局证一批 engine_aiskirm aiskinb:ib vs aiskirm:ib（同一次排队，都 PASS）：七个字段一次改成极端值（ConyardInDanger 三项 1000s / 100% / 5000、HoldObjectBeaconRadius 5000、ResourceNodeValueRemainingForExpansion 1000000、DefaultThreatFindRadius 5000、MaxWallDestroyTimeToCountAsGoThroughWalls 1000s），AI钱 / 建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s 开局相位）；tests/test_simai_bench_b.py::test_seven_inert_personality_fields_change_nothing。为什么不起作用：D126 找不到读者，信标半径只认进攻 / 驻守两类。gap：台上没有围攻建造厂、没有墙、没有协同信标，只证"27 关的门关着时不起作用" |
| 已对拍 | `人格/AIPersonalityDefinition.HoldPositionBeaconRadius` | 83 | a4 a5 a7 | B185 一局证一批 engine_aiskirm aiskins:ib vs aiskirm:ib（都 PASS）：七个字段一次改成 27 关敌方人格的值 / 极端值（CleanupRefineries false、CoopPersonality false、Assault / HoldPosition BeaconRadius 5000、EmergencyManagerHandle NoIncome / NoConyard / UnderAttack ""；1AlliedBalanced 继承的是 Coop 那套），建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s）；tests/test_simai_bench_b.py::test_seven_conditional_personality_fields_change_nothing_on_a_plain_skirmish。D126：协同 AI 扫人类伙伴的驻守信标。gap：D126 读成"条件满足才起作用"，台上条件都不满足（矿没采空、没有人类盟友和信标、建造厂在、有收入），起作用的那半没上台（d126 第 3 节的对照台子） |
| 不涉及 | `人格/AIPersonalityDefinition.PersonalityUIName` | 83 |  | 纯表现（语音、视频、画面） |
| 已对拍 | `微操/AIMicroManagerData.UseSpecialPowers` | 83 | a4 a5 a7 | 台上量过（engine_aimicro：aimicspon 开 两个武士 s41 冲锋，aimicspoff 关 一直没冲、s51 前被打死，脚本按的对照照样冲）、测试对拍 tests/test_simai.py（模拟器读进探针自写的微操数据：开的想冲、关的从不冲；技能本身模拟器没接，只记"想用"） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.MinPowerAdvantageEnemiesInMyBaseVsAllMyUnits` | 83 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.NumberOfObjectsRecentlyLost` | 83 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.ObjectLostFilter` | 83 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.OnlyIfLocalPlayerIs` | 83 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.TimeBetweenScans` | 83 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.TimeForNumberOfObjectLost` | 83 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.TimeThatConditionsMustBeMet` | 83 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `表现/InTroubleSkirmishFeedbackControl.TimeoutAfterPlaying` | 83 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 已对拍 | `人格/AIPersonalityDefinition.EmergencyManagerHandleNoConyardAtDifficulty` | 82 | a4 a5 a7 | B185 一局证一批 engine_aiskirm aiskins:ib vs aiskirm:ib（都 PASS）：七个字段一次改成 27 关敌方人格的值 / 极端值（CleanupRefineries false、CoopPersonality false、Assault / HoldPosition BeaconRadius 5000、EmergencyManagerHandle NoIncome / NoConyard / UnderAttack ""；1AlliedBalanced 继承的是 Coop 那套），建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s）；tests/test_simai_bench_b.py::test_seven_conditional_personality_fields_change_nothing_on_a_plain_skirmish。D126：没建造厂也没 MCV 才补 MCV。gap：D126 读成"条件满足才起作用"，台上条件都不满足（矿没采空、没有人类盟友和信标、建造厂在、有收入），起作用的那半没上台（d126 第 3 节的对照台子） |
| 已对拍 | `人格/AIPersonalityDefinition.EmergencyManagerHandleNoIncomeAtDifficulty` | 82 | a4 a5 a7 | B185 一局证一批 engine_aiskirm aiskins:ib vs aiskirm:ib（都 PASS）：七个字段一次改成 27 关敌方人格的值 / 极端值（CleanupRefineries false、CoopPersonality false、Assault / HoldPosition BeaconRadius 5000、EmergencyManagerHandle NoIncome / NoConyard / UnderAttack ""；1AlliedBalanced 继承的是 Coop 那套），建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s）；tests/test_simai_bench_b.py::test_seven_conditional_personality_fields_change_nothing_on_a_plain_skirmish。D126：无矿经济且钱 < 5000 才置位。gap：D126 读成"条件满足才起作用"，台上条件都不满足（矿没采空、没有人类盟友和信标、建造厂在、有收入），起作用的那半没上台（d126 第 3 节的对照台子） |
| 已对拍 | `人格/AIPersonalityDefinition.EmergencyManagerHandleUnderAttackAtDifficulty` | 82 | a4 a5 a7 | B185 一局证一批 engine_aiskirm aiskins:ib vs aiskirm:ib（都 PASS）：七个字段一次改成 27 关敌方人格的值 / 极端值（CleanupRefineries false、CoopPersonality false、Assault / HoldPosition BeaconRadius 5000、EmergencyManagerHandle NoIncome / NoConyard / UnderAttack ""；1AlliedBalanced 继承的是 Coop 那套），建筑码 / 兵数 / 我方建筑逐秒和基准一样（±1 s）；tests/test_simai_bench_b.py::test_seven_conditional_personality_fields_change_nothing_on_a_plain_skirmish。D126 没读（总表无此行），台上 AI 基地没挨打。gap：D126 读成"条件满足才起作用"，台上条件都不满足（矿没采空、没有人类盟友和信标、建造厂在、有收入），起作用的那半没上台（d126 第 3 节的对照台子） |
| 已对拍 | `启发条件/ObjectOfTypeExistsHeuristic` | 82 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `微操/AIMicroManagerData.EngageHostileTargets` | 82 | a4 a5 a7 | D145晋升：tests/test_ai_engage_clock.py::test_engage_switch_gates_the_state2_pick_on_bench_and_in_model 按名跑 aiegon/aiegoff：台上开的f376进状态2、f375两人按打分派目标，关的一直状态8、没有派目标；模型开的进状态2、f394起逐人派目标，关的从不进2/3/5、0次派目标，正常断言；首派帧（375对394）和关的一侧自主目标仍strict xfail。旧记录：E114新DLL aiegon:a / aiegoff:a各3/3 PASS：首冲371/259，首活均2；首批3170/3171均f345入队，f353均有单兵dest且aim为0。关无玩家级移动命令，但f431成员3171已有有效目标，不能解释成没有自主行军/目标；开f353模型过早推得目标，关f443模型首批仍无目标；同宿主帧按名回放 tests/test_ai_engage_clock.py strict xfail。单兵目标来源/保持契约仍gap，见 work/re/e114_engage_aim.md；保持推断，不晋升 |
| 已对拍 | `微操/AIMicroManagerData.EngagePassiveTargets` | 82 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_airetreat.py |
| 已对拍 | `组队招人/ObjectFilter.Relationship` | 82 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `开局/Order.Account` | 81 | a4 a5 a7 | docs/engine/aiopen.md#开局存款进哪个账户（Order Account，第 116 轮）（aiskacp / aiskacd：PRODUCTION 兵营出兵、DEFENSE 兵营不出） |
| 已对拍 | `开局/Order.Deposit` | 81 | a4 a5 a7 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（aiom15：带 Deposit 2000 照造、晚 4 秒） |
| 已对拍 | `启发条件/EnemyNearbyHeuristic` | 80 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/EnemyNearbyHeuristic.Distance` | 80 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `启发条件/EnemyNearbyHeuristic.EnemyNearby` | 79 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `微操/AIMicroManagerData.EngageTacticalTarget` | 79 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitactical.py |
| 已对拍 | `微操/AIMicroManagerData.PullbackInjured` | 78 | a4 a5 a7 | engine_aipullback aipullsov 残血坦克离队回吊车；tests/test_simai_bench_b.py::test_a_hurt_soviet_tank_team_is_pulled_back_to_the_crane 回放；普通盟军/日本工厂不可进入；仅地面车辆回撤，吊车回收仍 strict xfail，未验证空海军/精确时间 |
| 已对拍 | `微操/AIMicroManagerData.Crush` | 77 | a4 a5 a7 | D145晋升：tests/test_crush_observation.py::test_crush_switch_runs_the_guards_over_only_when_on 按名跑 aicrush1/aicrush0（只差Crush）：台上开的s27守军1、坦克4，关的守军12、坦克被打掉；模型开的s27守军5、坦克4、18次碾压派令，关的守军10、0次碾压，正常断言；碾得多快（台上s28清零）仍strict xfail。旧记录：engine_aicrush:aicrush1 台上s28–33守军0、坦克4；按名回放存活正常断言，清零strict xfail；模型守军11/9/9/9/8/8，首目标活着即被重选、未接触；首move终点不挪不代表后续均不挪；D86 aicrush1t碾压段aim全0，dest在f350/410/440变化；模型f230后首世界样本尚无远厂goal，前置已失配；tests/test_crush_observation.py按名回放，前置与首目的地strict xfail；追踪/选敌及移动仍gap，见work/re/e113_crush.md、e109_crush.md；不晋升 |
| 已对拍 | `目标/AITargetingHeuristic.SortType` | 76 | a4 a5 a7 | docs/engine/aitactics.md#目标挑哪个（Distance：aitpnear / aitpmt2 最近、次近；ThreatToGround：aitargetsafe） |
| 已对拍 | `微操/AIMicroManagerData.ReverseMove` | 74 | a4 a5 a7 | engine_aipullback airev1/0台上s1–10坦克4、s19–22近厂2；tests/test_simai_bench_b.py按名回放，存活前置正常断言、近厂计数strict xfail；airevp近厂4不能证明没有倒车；E115 airev1t/0t各PASS：同帧目标/位置/车身朝向已取得，两侧各23个有效目标相邻帧移动样本无负点积；tests/test_ai_reverse_clock.py按名f263目标取得strict xfail；模型朝向/分支前置仍gap，暂停新台、不晋升；宿主台近厂读数不同于旧台，不假设等价；见work/re/e115_reverse_aim.md；D132 airevk1/0（玩家坦克目标）逐帧相同、无退后目的点，但前置未达：近的玩家坦克s13组队前被打死，入队2辆到目标中心距166–233 > R−10=135，与模型一致不算反例；airevkg1守护者未入队，无效；见work/re/d132_whenidle.md；D133 airevk2/airevk2o（s16.7删掉远处玩家坦克、在每辆锤子身上生成玩家守护者）：开的那局f302起成员停下、下移动令到离目标135（R−10）、车头对着目标倒着开（位移与车头点积<0），全局23条；关的那局0条；tests/test_ai_reverse_k2.py按名读台上样本正常断言；D134 模拟器接上成员自己的攻击目标（simai ordered_aim）和射程AttackRange−5：test_model_backs_up_after_the_swap_only_with_the_switch_on 开的那局换敌后下倒车令、关的那局0条，正常断言，晋升；近敌计数回放仍strict xfail（台上只2辆入队、近敌s13先死，模拟器4辆全入队，是招兵不是倒车）；见work/re/d133_airevk2.md |
| 已对拍 | `目标/AITargetingHeuristic.Location` | 74 | a4 a5 a7 | E81/E87 engine_ailocation a：同型电厂一陆一水、四架双刃，仅切Land/Water/Water Land；s40到陆厂/到水厂分别4/0、0/4、4/0；tests/test_simai_bench_e.py::test_target_location按名回放三组通过。Location按位置地形过滤；只验证EnemyStructure/Distance，浅滩、桥面及空中目标仍INFERRED；见 work/re/e_location_e87.md |
| 已对拍 | `战术/Tactic.UseAestheticsManager` | 73 | a4 a5 a7 | D145晋升：tests/test_simai_bench_c.py::test_tactic_aesthetics_switch_after_displacement 按名跑 aiaeson/aiaesoff，传送出圈后开的一侧回900再离开（s65 圈300/900=0/0）、关的一侧回双圈（1/1），模型两边都对上，正常断言；传送前模型开的一侧也离900（台上不离）仍strict xfail。旧记录：专用engine_aiaesthetics aiaeson/aiaesoff固定Distance=2000，仅切美学开关；两组各5条PASS：on先离300、传送后回900再离，off回双圈，存活/锁存均1；tests/test_simai_bench_c.py关闭组完整轨迹已回放；探针战术附加属性现传入消费者；E108按D83实际调用回放：首次遇敌gate=0仍发，后续102次gate=0不发、两次gate=1发；完整模拟首发154对台191且漏461，选敌/成员目的地/ready仍gap、strict xfail，不晋升；tests/test_ai_aesthetics_clock.py；见 work/re/e108_aesthetics_gate.md |
| 已对拍 | `组队招人/TeamTemplate.ReleaseType=NEVER_RELEASE` | 71 | a4 a5 a7 | engine_airelease airelnever/airelprio仅ReleaseType不同；CNVTeams两组f166防御激活持3166/3167，priority在(526,541]同两ID转进攻，never保留至末样本；tests/test_simai_bench_c.py::test_never_release_engine_members_and_model_replay按名跑两台、断言实机ID/n/active及模型f301/601/976成员归属；仅固定两辆车的保留/转队，精确激活/转队时钟、priority后段短暂第三ID及其他释放模式仍gap；见 work/re/c_release_teams_report.md |
| 已对拍 | `微操/AIMicroManagerData.EnemySearchDistanceVisionMultiplier` | 70 | a4 a5 a7 | engine_aisearch aisrchhi/aisrchlo 仅倍率1.5/0.25不同：高先打旁厂、到远厂0；低旁厂100且到远厂4；tests/test_simai_search.py 回放；仅被动建筑搜索，精确边界、敌军目标取得和揭雾未量 |
| 已对拍 | `启发条件/OpeningMoveHeuristic` | 69 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiomove.py |
| 已对拍 | `启发条件/ObjectOfTypeExistsHeuristic.PassIfExists` | 67 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `开局/SkirmishOpeningMove.Side` | 64 | a4 a5 a7 | E82 engine_aiopenside a：固定盟军玩家显式挂载三电厂开局，仅切Side。Allies在[s55,s60)电厂3/兵营0，Soviet电厂2/兵营1。D66：Side和玩家阵营全等才进候选，候选全空=开局直接完成、不下单、不回退；模型照此（B第147节）。tests/test_simai_bench_e.py::test_opening_side[aiosallies]、test_an_opening_of_another_side_is_not_run按名回放、断言台上读数（Soviet s19-s28 无电厂）。gap：Soviet之后的2电厂1兵营是没开局时的结构建造，模型没建（strict xfail，同第123节）；见 work/re/e_openside_e82.md |
| 推断 | `战术/Tactic.Tactic=Engineer` | 63 | a4 a5 a7 | A第203轮 engine_aiskirm aiskirm:et原版（11-13）：AlliedCaptureTech_MEDIUM_EngineerTactic_0_0 s128空队、s144工程师入队、s216到油井、s222油井归AI同秒队消失，矿点旁始终0。tests/test_simai_engineer_tactic.py按名回放队伍出现/入队通过；模型（fca219e）目标选了AI基地旁矿点、Engineer到达动作空实现不占领（strict xfail）。A第205轮：模型分支a204-tech-filter + Brain.act占领 + 陆路回退看地形，模拟器s230到、s236占（晚14 s，台上像游水走近直线，both网格下不了这岸）；另aieng/aiengctl（E111）单独台未招到工程师，见work/re/handoff.md第203轮、e111_engineer.md |
| 已对拍 | `启发条件/IntervalHeuristic.CountFrom` | 61 | a4 a5 a7 | C engine_aiintervalfrom aiintmap/aiintai:a：同人格同图s10唤醒，仅MAP_START/AI_START；IntervalTime=25s、ActiveTime=30s，s24在家/总数均4/4，s32为0/4与4/4，s42均0/4。tests/test_simai_intervalfrom_c.py按名回放两组实测；只验证首次开启起点，后续循环、精确求值帧、未唤醒边界仍gap；见work/re/c_intervalfrom_report.md |
| 已对拍 | `造兵/BuildEntry.MinTime` | 61 | a4 a5 a7 | 台上量过（engine_aiskirm mt aiskmt0/03/20 → 唤醒后第 2256 帧有科技楼，aiskmt14/15/16/40/99 → 第 5857 帧：分数缓存按模板、排前的原版 AlliedTechBuildState MinTime 360 盖住子人格的条目，D 第 100 轮），测试对拍 tests/test_simai_mintime.py（模型 first_tech_order 按名拿人格，容差一次评估）；模拟器的建造厂只走开局，没接进回放；电力门、效率那半没建模 |
| 已对拍 | `战术/Tactic.EndBehavior=RETURN_HOME_AND_DISBAND` | 59 |  | docs/engine/aitactics.md#目标没了以后（EndBehavior，2026-11-09 各一次）（aiendh：同 DISBAND，没回家，和模型对上） |
| 已对拍 | `组队招人/TeamTemplate.MaxTypesOfUnits` | 58 | a4 a5 a7 | D150：tests/test_ai_team_fields.py 按名跑 aimaxty1/aimaxty3（只差 MaxTypesOfUnits 1/3，家里坦克/步兵/标枪各 2）：台上 1 只收维和（s16 起 2/0/2），3 三种都收（s20-s22 全走）；模型同形；收兵顺序与时刻 INFERRED |
| 不涉及 | `表现/FeedbackEntry.Timeout` | 56 |  | 纯表现（语音、视频、画面） |
| 已对拍 | `造兵/BuildEntry.PercentHigh` | 56 | a4 a5 a7 | 台上量过（engine_aiskirm s aiskrand：RANDOM_UNIT "0%–30%" 和不带百分号的 "30–100" 两条都造出来——不带 % 的数也按百分比读，原版 _RANDOM 状态就这么写），测试对拍 tests/test_simai_bench_b.py；两条的比例（预测 3:7，台上 4:4）样本太少没定 |
| 已对拍 | `造兵/BuildEntry.PercentLow` | 55 | a4 a5 a7 | 台上量过（engine_aiskirm s aiskrand：RANDOM_UNIT "0%–30%" 和不带百分号的 "30–100" 两条都造出来——不带 % 的数也按百分比读，原版 _RANDOM 状态就这么写），测试对拍 tests/test_simai_bench_b.py；两条的比例（预测 3:7，台上 4:4）样本太少没定 |
| 已对拍 | `开局/OpeningMove.Difficulty` | 54 | a4 a5 a7 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（aiodf / aiodf2：只留 MEDIUM 的） |
| 已对拍 | `造兵/BuildEntry.Upgrade` | 54 | a4 a7 | C engine_aiupgrade a：aicupgon常量状态含UPGRADE_TECH/Tech2，s39起持有2（建造厂+它够得着的兵营）；aicupgoff移除专用状态后恒0；见work/re/c_upgrade_report.md。B第153轮接模型：升级条目按状态权重×分（UPGRADE 140；UPGRADE_TECH MinTime前0、ForceTime后200推断、中间140推断）挑最高下单，扣PRODUCTION，下了升级这一轮不下兵；模拟器s20下单、s40起持有2。tests/test_simai_upgrade_c.py按名回放两组通过。电力门、效率/兵力比两道、开局里的升级单没建模 |
| 已对拍 | `微操/AIMicroManagerData.UseGatherState` | 51 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipullback.py |
| 已对拍 | `造兵/BuildEntry.ForceTime` | 48 |  | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py:mt |
| 已对拍 | `启发条件/OpeningMoveHeuristic.Complete` | 47 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiomove.py |
| 已对拍 | `组队招人/TeamTemplate.Priority=HOTSPOT` | 47 |  | D150：tests/test_ai_team_fields.py 按名跑 aihotstd/aihotscr/aihotdef（防守队 STANDARD/SCRIPTED 对 进攻队 HOTSPOT/DEFAULT，只差一处）：台上 HOTSPOT 两局 s40 放人、s43 到目标，DEFAULT 到 s70 不放；模型同形（s47/s50，晚约 7 s，时刻 INFERRED） |
| 已对拍 | `开局/OpeningMove.Weight` | 46 | a4 a5 a7 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（aiowt / aiowt2：0% 永远抽不到） |
| 已对拍 | `战术/Tactic.EndBehavior=RAMPAGE` | 46 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_ainamed.py |
| 已对拍 | `组队招人/TeamTemplate.ReleaseType=RELEASE_TO_PRIORITY` | 46 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `启发条件/PathToTargetHeuristic` | 45 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiopath.py |
| 推断 | `启发条件/PathToTargetHeuristic.LocomotorConditionToUseForTest` | 45 | a4 a5 a7 | E84 engine_aiopathcond a：同JapanAntiAirShip仅切NORMAL深水/SUPERSONIC空中；两组s22-s24均兵营1/电厂0，水组原始Island预测FAIL、空中PASS。tests/test_simai_bench_e.py按名回放实际计数通过，但不能区分条件生效与路径判定边界；C复核：旧配方Surface未显式指定，SDK移动器差异不能独立证明实际路径可达性；C断桥两组aipcland/aipcamph同模板切NORMAL地面/SUPERSONIC地面+水面：s22-24仍均兵营1/电厂0，s40-44控制车均存活未到岸，两栖阳性未建立。tests/test_simai_pathbanks_c.py独立断言控制读数；D108/D175：开局f4抽签时未登记基地，启发early:nobase直接"判不了"、不看测试模板，B217模拟器开局同样判不了，建筑选择各局按名回放通过——但这些局都没走到条件/移动器，保持gap不晋升；见 work/re/c_pathbanks_report.md、c_pathcond_gate_report.md、d175_gap_b216.md |
| 已对拍 | `启发条件/PathToTargetHeuristic.ObjectTypeToUseForTest` | 45 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiopath.py |
| 已对拍 | `启发条件/PathToTargetHeuristic.PathExists` | 45 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiopath.py |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=EnemyUnit` | 44 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 已对拍 | `启发条件/TimerHeuristic.EndTime` | 41 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | `造兵/BuildEntry.CountModifier` | 41 |  | C engine_countmodifier a：同经济/工厂/候选和初始新维和4/新标枪2，仅切0.5/4；台上低组s27先补标枪、s38–66人数4/5，高组s27先补维和、s39–66人数7/2。tests/test_count_modifier.py按名回放s40原人数。B206 b：两组都在开局存款2000花到剩100时停（原版兵营2狗+2/3标枪），模型加开局只有存款时按价格挡；gap：原版兵营兵种搭配（模型3狗+1标枪+1维和）使高组模型停在8/2（strict xfail）；见work/re/c_countmodifier_report.md |
| 已对拍 | `微操/AIMicroManagerData.RetreatMinDistanceFromBase` | 40 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_airetreat.py |
| 已对拍 | `目标/AITargetingHeuristic.Relationship` | 40 | a4 a5 a7 | docs/engine/ainamed.md#给关卡线的结论（ainmrel：写了 Relationship 就按关系过滤，玩家的楼当 NEUTRAL 不算，不出门） |
| 已对拍 | `造兵/BlockIfThingNearFactory.IncludeThing` | 40 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aibuildexclude.py |
| 已对拍 | `微操/AIMicroManagerData.RetreatMinDistanceToFallback` | 38 | a4 a5 a7 | engine_aifallback aifbshort100/aifblong500：四人存活回齐、在家约18秒、长组先于短组再出发；tests/test_simai_fallback.py::test_fallback_distance_first_return_and_departure；仅此固定FromBase=300场景的行为回放，未量内部退出位置、精确距离边界或其他基地选择 |
| 已对拍 | `目标/AITargetingHeuristic.SortType=Distance` | 37 | a4 a5 a7 | docs/engine/aitactics.md#目标挑哪个（aitpnear 挑最近、aitpmt2 第二槽挑次近、aitpvk 显式写 Distance） |
| 已对拍 | `经济/AccountShare.Account` | 37 | a4 a5 a7 | tests/test_slush_account.py::test_slush_defense_named_bench_replay（C 的 engine_aislush aislddef / aislsdef：同一预算只把 100% 从 DEFENSE 挪到 SLUSH_FUND，台上炮塔 s28/48/68 1/2/3 座 vs 全程 0 座，模拟器按名回放 s60 2 / 0——Account 决定份额进哪个池、造防御只花 DEFENSE 池；PRODUCTION / DEFENSE 两值另有台子；SLUSH_FUND 自己花在哪单列未做；D 第 151 轮） |
| 已对拍 | `战术/Tactic.Tactic=SimpleExpansion` | 36 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aisimpleexp.py |
| 已对拍 | `启发条件/IsBuildingHeuristic` | 30 | a4 a5 a7 | E83 engine_aibuilding a：STRUCTURE空队列、现成基地1；PassIfBuilding=false时s40到陆厂4/在家0，true时0/4，两组PASS；tests/test_simai_bench_e.py::test_is_building_idle按名回放通过。C补充活跃连续电厂队列false反向对照：匹配组s40到陆厂/在家0/4，不匹配4/0，两组电厂4/基地1、各一次PASS；模型匹配组4/0，test_simai_buildkind_c为strict xfail，队列/求值时序未解；取消/挂起/等待仍gap；见 work/re/c_buildkind_false_report.md、e_building_e83.md |
| 已对拍 | `启发条件/IsBuildingHeuristic.KindOf` | 30 | a4 a5 a7 | C engine_aibuildkind a：同一连续电厂开局，FS_POWER匹配时s40到陆厂4/在家0，FS_BARRACKS不匹配时0/4；两组电厂4/基地1，两局PASS；多token aibkindoryes/aibkindorno各一次PASS：FS_BARRACKS FS_POWER仅第二token匹配时4/0，FS_BARRACKS FS_TECHNOLOGY均不匹配时0/4，两组电厂4/基地1；tests/test_simai_buildkind_c.py按名回放单token和多token四组，验证活跃队列KindOf按OR匹配。false反向两组各一次PASS：匹配0/4、不匹配4/0，均电厂4/基地1；模型匹配false组4/0，strict xfail，见 work/re/c_buildkind_false_report.md。仅连续电厂开局，队列挂起/取消/等待阶段仍gap；见 work/re/c_buildkind_or_report.md、c_buildkind_report.md；空队列边界见 work/re/e_building_e83.md |
| 已对拍 | `启发条件/IsBuildingHeuristic.PassIfBuilding` | 30 | a4 a5 a7 | E83 engine_aibuilding a：STRUCTURE空队列、现成基地1；PassIfBuilding=false时s40到陆厂4/在家0，true时0/4，两组PASS；tests/test_simai_bench_e.py::test_is_building_idle按名回放通过。C补充活跃连续电厂队列false反向对照：匹配组s40到陆厂/在家0/4，不匹配4/0，两组电厂4/基地1、各一次PASS；模型匹配组4/0，test_simai_buildkind_c为strict xfail，队列/求值时序未解；取消/挂起/等待仍gap；见 work/re/c_buildkind_false_report.md、e_building_e83.md |
| 已对拍 | `微操/AIMicroManagerData.PullbackInjuredHealthPct` | 30 | a4 a5 a7 | engine_aipullpct 固定30%血量、苏联吊车，仅阈值0.2/0.5不同；tests/test_simai_pullpct.py::test_pullback_threshold_high_returns_before_recycling 完整回放四车回家且不到远厂；同文件 low 对照先到远厂；仅初次回撤阈值，精确边界/晚段/吊车回收未闭环（回收 strict xfail） |
| 已对拍 | `组队招人/TeamTemplate.Priority=DEFENSE` | 29 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `微操/AIMicroManagerData.AlphaStrikeTargetHealthPct` | 28 | a4 a5 a7 | D146晋升：tests/test_ai_alpha_switch.py 按名跑 aialobshi/aialobslo（只差阈值0.9/0.01，CNVTeams宿主，E99两局都PASS）：台上高的8→6 f230→0（集火）f290，低的8→6 f230→1（撤退）f470、从不进0；模型高的6 f240→0 f270、低的6 f240→1 f480、从不进0，正常断言；精确帧和低的一侧后段8/6/1循环、血量/存活结局仍strict xfail。旧记录：engine_aialphahp 旧固定70%对照；engine_aialphaclose 独立延迟守军、仅阈值0.01/0.9不同；tests/test_simai_bench_c.py 保留读数回放，有限诊断不等于字段闭环；目标适用条件与回放差异仍gap，见 work/re/c_alpha_close_report.md |
| 已对拍 | `造兵/BlockIfThingNearFactory.Relationship` | 28 | a4 a5 a7 | tests/test_simai_bench_b.py::test_a_thing_near_the_factory_blocks_the_entry（engine_aiskirm y aiskblkn / aiskblkr：Rule ANY + Relationship NEUTRAL 挡住，aiskblkf 400 外不挡；ENEMIES 走同一段代码没单独上台；B 第 149 轮） |
| 已对拍 | `造兵/BlockIfThingNearFactory.Rule` | 28 | a4 a5 a7 | tests/test_simai_bench_b.py::test_a_thing_near_the_factory_blocks_the_entry（engine_aiskirm y aiskblkn / aiskblkr：Rule ANY + Relationship NEUTRAL 挡住，aiskblkf 400 外不挡；ENEMIES 走同一段代码没单独上台；B 第 149 轮） |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=FriendlyUnit` | 27 | a4 a5 a7 | C engine_aifrdistance a：aifrnear/aifrswap三友军MCV，仅交换近远角色；s30逻辑帧478/486，tact对应原友车/second，同帧坐标均为距基地650的最近候选；友/敌MCV存活3/1。tests/test_simai_friendly_c.py::test_friendly_distance_target按名回放通过。仅验SAME_PLAYER、MCV、Distance、单槽StaticDefense；其他排序、默认关系、unique多槽仍INFERRED。旧E85远处双车的站位strict xfail保留，不由新配方解释；见work/re/c_friendly_distance_report.md |
| 已对拍 | `微操/AIMicroManagerData.UpdateTime` | 26 | a4 a5 a7 | D147晋升：tests/test_ai_micro_clock.py 按名跑 aimicupft/aimicupst（只差微操UpdateTime 0.5/4s，E102两局）：台上微操逐个选中成员的帧快的376/384/392/400…（间隔8的倍数、最小8），慢的405/466/527（间隔61=float32累加1/15到4.0，不是60）；模型同周期（快8、慢61），正常断言；相位（台上首拍376/405、模型394/391）和首冲帧仍strict xfail。旧记录：engine_aimicro aimicupft/aimicupst:a 仅切微操0.5/4s，15帧宿主、D81时钟重量；台内首冲帧371/317、首活均2，末图逻辑帧872/876；tests/test_simai_bench_e.py 按名回放首活通过，精确首冲及人口峰值strict xfail；资格/更新前置状态、观测宿主人口等价仍gap；旧时钟读数不用于晋升，非固定延迟；见work/re/e102_update_clock.md |
| 已对拍 | `经济/AccountShare.Percent` | 26 | a4 a5 a7 | 台上量过（engine_aiskirm d / f：开局后 CoopBudget 防御 5%，存款约 36000 两座塔、约 17000 一座、15000 没有）、测试对拍 tests/test_simai.py——塔数对上；第一座的时刻模拟器早 ~36 s（strict xfail），别的份额 / 状态没单独量 |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=EnemyStructure` | 25 | a4 a5 a7 | docs/engine/aitactics.md#读数（ClosestStructureHeuristic、SafestToGroundStructureHeuristic：aitargetnear / aitargetsafe） |
| 已对拍 | `战术/Tactic.GatherWaypoint` | 24 |  | D148：tests/test_ai_team_fields.py 按名跑 aigathwp/aigathno/aigathbad（只差 GatherWaypoint：路点名 / 不写 / 写错名，SimpleAttack 打远厂）：台上写路点的先到路点（s9-s21 四人）再去远厂（s44），不写和写错名直接去（s15/s17）；模型（simai 本轮接上 gather_point）同形，路点 s11、远厂 s38；精确等待时长（台上全队停稳判据，见 work/re d130）INFERRED |
| 已对拍 | `战略状态/AIStrategicStateDefinition.PathfindingCheckType` | 24 | a4 a5 a7 | D152 engine_aipathcheck aipfdef/aipfatk/aipfpath/aipfnone:a（去桥尼亚加拉，SimpleAttack 打对岸玩家基地，四局只差这个字段）：不写 / QuickDoesAttackPathExist / QuickDoesPathExist 三局 4 个维和从不出门，CNVTeams 每 90 帧建一支空队、约 75 帧后过期；None 一局 f21 招满 4 人、s6 出门。走不到的单位招人时就不招（模型 TeamMaker.reach，缺省按战术类 data.PATH_CHECK）；tests/test_ai_pathcheck.py 按名断言台上读数并回放。gap：AttackPath 与 Path 在"岸边射程内"时的区别没测；出门后路断的周期踢人读到没上台；见 work/re/d152_pathcheck.md |
| 已对拍 | `微操/AIMicroManagerData.EnterBaseDefensesWhenIdle` | 23 | a4 a5 a7 | D132 engine_aibasedef aibdi1/0/2（守点队状态8、无敌人、己方4座炮塔）：两开关都开时进基地防御那段程序发进驻令（f50四条、f98三条），s2起进炮塔、s6起2人；只开一个时该程序不发令；tests/test_simai_basedef_whenidle.py 按名回放：都开进炮塔、关一个时该程序不送人，正常断言；台上f50开局即发令、2人，模型s12.5、1人，strict xfail；两对照各有1人经另一段不受开关管的程序进炮塔（f80），模型没有这条路，strict xfail；见work/re/d132_whenidle.md。旧读数：engine_aibasedef aibd1 是战斗中总开关开、idle关的正例（s21起1人进炮塔）；aibd0/aibdidle 总开关均关且无人进驻，不是idle分支正例；tests/test_simai_basedef_idle.py 直接计数回放，aibd1仍strict xfail；独立回放其余三计数：s21台上炮塔3/远厂步兵4，模型1/0，三组strict xfail；模型有idle状态但三组均无双开关开启更新；实机idle/成员观测与到达/存活仍gap；见work/re/e112_basedef_idle.md |
| 已对拍 | `战略状态/AIStrategicStateDefinition.PathfindingCheckType=None` | 23 | a4 a5 a7 | D152 engine_aipathcheck aipfdef/aipfatk/aipfpath/aipfnone:a（去桥尼亚加拉，SimpleAttack 打对岸玩家基地，四局只差这个字段）：不写 / QuickDoesAttackPathExist / QuickDoesPathExist 三局 4 个维和从不出门，CNVTeams 每 90 帧建一支空队、约 75 帧后过期；None 一局 f21 招满 4 人、s6 出门。走不到的单位招人时就不招（模型 TeamMaker.reach，缺省按战术类 data.PATH_CHECK）；tests/test_ai_pathcheck.py 按名断言台上读数并回放。gap：AttackPath 与 Path 在"岸边射程内"时的区别没测；出门后路断的周期踢人读到没上台；见 work/re/d152_pathcheck.md |
| 已对拍 | `微操/AIMicroManagerData.EnterGarrisonableStructureDistance` | 21 | a4 a5 a7 | engine_aigarrison aigar1/aigar0/aigarfar：默认150、旧楼EAST=40，近楼归AI、关闭或远楼不进；tests/test_simai_garrison_distance.py::test_garrison_distance_replays_recorded_near_far_and_disabled；仅现成近远行为回放，精确边界、其他配置值和进门死亡时序未量；距离0仅模型敏感性守卫 |
| 已对拍 | `人格/AIPersonalityDefinition.SkirmishPersonality` | 20 | a4 a5 a7 | B207：aisksd1 / aisksd2 只差这一项（engine_aiskirm sd，2026-11-14 两局 PASS，work/re/d123_side.md 1.2）：false（27 关全是默认 false）人格位 9 = 照用地图写的 CNVSideX；true 且 Side 不含玩家阵营 → 136 = 换成随机的本阵营遭遇战人格。模拟器 simai SimAI.assigned → 模型 AIData.assigned_personality（库 = SkirmishPersonality 的人格、Side 随继承，INFERRED）；按名回放 test_a_personality_whose_skirmish_gate_is_closed_is_used_whatever_its_side、test_a_skirmish_personality_of_another_side_is_replaced |
| 已对拍 | `人格/AIPersonalityDefinition.CanBuildInAlliedBuildRadii` | 18 |  | B212-B213 engine_aiskirm acbr0 / acbr1:rpb（都 PASS）：玩家盟军建造厂放在 AI 建造厂西南 700、两向 Friend，只差这一项 false / true：兵营 s49 都在 x10 y17（在盟友 600 半径内）、电厂都在其后 +21 +17，两局相同；tests/test_simai_bench_b.py::test_allied_build_radius_over_the_ais_own_does_not_move_its_structures。程序（l4_allied_radii，读到）：false 时放置搜索多带一位，格子可建区检查拒绝盟友的那条记录；台上否掉"重叠处也挡"，模拟器 simai.allied_ok 只挡"只有盟友半径盖住"的落点（任一记录过就过，INFERRED）。gap：只在盟友半径里的落点（AI 建造厂挪到盟友半径边上）没上台；盟友是 AI 时挡不挡没测 |
| 已对拍 | `战略状态/AIStrategicStateDefinition.MaxRunningCopies` | 18 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | `组队招人/TeamTemplate.Priority=LOW` | 18 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | `人格/BaseSelection.PreferredNotBaseTypes` | 17 | a4 a5 a7 | C aibn2old/aibn2new:b初始双基地固定OLD，仅切反偏好OLDEST/MOST_RECENT；f274两基地均合格，分数0/1选1与1/0选0，f284点命令崖矿/东矿。s55–65东/崖队员/双厂分别0/0/1/1与4/0/1/1；tests/test_expansion_target.py按名断言类型、分数、选择点和原计数。仅年龄类型反偏好命中子集；自动注册、死亡清理和矿点资格仍gap，旧CAPTURED单基地只回放计数，不证明类型；见work/re/c_bn2_report.md |
| 已对拍 | `人格/BaseSelection.SortOrder` | 17 | a4 a5 a7 | C aibs3old/aibs3new:b初始双厂：f274两个合格基地0/1均分1，OLD pick/model=0/0、NEW=1/1；点命令分别东矿/崖矿。s55–65东/崖队员与双厂OLD=4/0/1/1、NEW=0/0/1/1；tests/test_expansion_target.py按名回放断言选择点和计数。仅OLD/NEW按基地编号排序；其他排序、注册顺序和矿点资格仍gap，见work/re/c_bs3_report.md |
| 已对拍 | `启发条件/AllNearbyNodesFullHeuristic` | 17 | a4 a5 a7 | B208-B210：simai facts 给 nodes full（Brain.open_nodes，与"还要不要矿场"同一扫描，已读）；台子 engine_ainodesfull ainf0-ainf5（0/1/2 座矿场，每座矿场连自带共 1/2/3 辆矿车）：只有两座矿场各 3 辆矿车（ainf3）该状态出兵，其余都在家；模拟器每个矿点 3 辆矿车算满（NODE_MINERS，阈值由台上夹出、引擎的矿点占用表没读，INFERRED），矿车跨矿点合算也是 INFERRED；tests/test_nodes_full.py 六局按名回放 |
| 已对拍 | `启发条件/ConstantHeuristic.Weight` | 17 | a4 a5 a7 | C engine_aiconstweight aicwzero/aicwone:a：同人格单战略状态，仅Weight=0/1；s40步兵在家/总数/未登记坦克在家为4/4/4与0/4/4，tests/test_simai_constweight_c.py按名回放两组实测。仅验证零排除及正值可进入；多个正权重的抽样比例、随机分布和预算/造兵消费者仍gap；见work/re/c_constweight_report.md |
| 已对拍 | `战略状态/AIStrategicStateDefinition.CannotAttackTargetReaction` | 17 | a4 a5 a7 | engine_aicannot aicantig/di/su:r：Ignore保留两人和空靶；Disband f95清空/f97重招；TreatLikeSuccess f92换地面厂/f500进入攻击态。tests/test_ai_cannot_reaction.py按名回放生命周期；仅显式三值、SimpleAttack/RAMPAGE；精确周期、模板资格、缺省、回家和多队仍gap；见work/re/c_cannot_report.md、e122_cannot.md |
| 已对拍 | `人格/BaseSelection.PreferredBaseTypes` | 15 | a4 a5 a7 | C aibp1old/aibp1new:b初始双基地固定OLD、反偏好为空，仅切偏好OLDEST/MOST_RECENT；f274两基地均合格，分数1/0选0与0/1选1；f284点命令东矿/崖矿。s55–65东/崖队员/双厂分别4/0/1/1与0/0/1/1；tests/test_expansion_target.py按名断言类型、分数、选择点与原计数。仅年龄类型偏好命中子集；自动注册、死亡清理和矿点资格仍gap；见work/re/c_bp1_report.md |
| 已对拍 | `人格/BaseSelection.SortOrder=PREFER_OLDEST` | 15 | a4 a5 a7 | 初始双厂同分候选，OLD选基地0、NEW选基地1；按名选择点/计数回放，仅该排序子集，见work/re/c_bs3_report.md |
| 推断 | `启发条件/TechBuildingShareHeuristic` | 15 | a4 a5 a7 | C engine_aitechshare a：四座开局油井、活跃拥有者两方，aitechlow/high自有1/2；s40低于75/高于75/低于125三组在家人数均4/0/4，原预测0/4/0与4/0/0。地图另有Soviet_2..6空玩家，倾向引擎玩家数包含空槽；tests/test_simai_techshare_c.py按名回放两组实测，门控两strict xfail、所有权控制独立断言；尚缺同帧own/total/player-count和状态权重，保留gap，不按结果倒推公式；见work/re/c_techshare_report.md、handoff-c.md |
| 推断 | `启发条件/TechBuildingShareHeuristic.Above` | 15 | a4 a5 a7 | C engine_aitechshare a：四座开局油井、活跃拥有者两方，aitechlow/high自有1/2；s40低于75/高于75/低于125三组在家人数均4/0/4，原预测0/4/0与4/0/0。地图另有Soviet_2..6空玩家，倾向引擎玩家数包含空槽；tests/test_simai_techshare_c.py按名回放两组实测，门控两strict xfail、所有权控制独立断言；尚缺同帧own/total/player-count和状态权重，保留gap，不按结果倒推公式；见work/re/c_techshare_report.md、handoff-c.md |
| 推断 | `启发条件/TechBuildingShareHeuristic.PercentOfFairShare` | 15 | a4 a5 a7 | C engine_aitechshare a：四座开局油井、活跃拥有者两方，aitechlow/high自有1/2；s40低于75/高于75/低于125三组在家人数均4/0/4，原预测0/4/0与4/0/0。地图另有Soviet_2..6空玩家，倾向引擎玩家数包含空槽；tests/test_simai_techshare_c.py按名回放两组实测，门控两strict xfail、所有权控制独立断言；尚缺同帧own/total/player-count和状态权重，保留gap，不按结果倒推公式；见work/re/c_techshare_report.md、handoff-c.md |
| 已对拍 | `微操/AIMicroManagerData.AlphaStrikeTargetTimeToKill` | 15 | a4 a5 a7 | B219：tests/test_ai_alpha_switch.py 按名跑 aialobttk（= aialobshi 只把 TimeToKill 1000 改 0.01，CNVTeams宿主，台上 PASS）：上台前模型预测"血量比×击杀时间 < 0.01 不成立→不集火"，台上 8→6 f230→1 f470、从不进0，与低阈值 aialobslo 逐帧相同；模型 6 f240→1 f480、从不进0，正常断言；击杀时间本身的算法（中间值）没上台 |
| 已对拍 | `微操/AIMicroManagerData.DodgeThreats` | 15 | a4 a5 a7 | engine_aidodge aidodgeon/aidodgeoff 原版精确打击信标开关对照；tests/test_ai_dodge.py 按名断言两人存活、信标存在时on离开/off保持2，以及到期清理；simai micro_team威胁视图/移动回调接私有micro消费者，仅单信标地面成员；固定0.5秒反应、径向逃离/目的地保持/首次可见寿命起点为INFERRED；精确时钟、安全圆、通用过滤/所属、多威胁仍gap，见 work/re/e116_dodge.md |
| 已对拍 | `微操/IgnoreTargets.IncludeThing` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aibuildexclude.py |
| 推断 | `目标/AITargetingHeuristic.HighestPriorityEnemyPlayersOnly` | 15 |  | C按名台子engine_aitoponly：显式s4=30/p1=10，高档仅建造场、低档有兵营；true组s40在家4/兵营0，false组在家0/兵营4；把兵营给高档的true阳性对照同false。tests/test_top_enemy_only.py断言原计数并按名回放；无同帧实际优先级表/候选资格，同档多玩家及动态优先级仍gap，保持推断；见work/re/c_toponly_report.md |
| 推断 | `目标/AITargetingHeuristic.MinDistanceFromEnemy` | 15 | a4 a5 a7 | C按名台子engine_aimindist：同一中立油井，TechBuilding阈值0组采样s6起目标区4，2000组采样s1-55在家4/目标区0；NamedObject阳性对照同0组。tests/test_min_enemy_distance.py断言原计数并按名回放；无同帧实际距离/候选资格，追加双油井aimindpair0/350:a仅切0/350，近油井距固定敌电厂200、远约1230；s40近/远/家/总数实机4/0/0/4与0/0/4/4，模型350选远，strict xfail；原预测FAIL独立strict xfail。采样时钟未对齐游戏帧，缺远油井同帧资格/最近候选拒绝后的回退次序，保持推断、不晋升；见work/re/c_mindist_report.md、work/re/c_mindist_pair_report.md |
| 已对拍 | `组队招人/TeamTemplate.AllowRecruitUnitsInCombat` | 15 | a4 a5 a7 | 专用engine_aicombat aicombat0/aicombat1：容量1、先放守护者与玩家坦克对射、后放一辆闲着；关闭时闲车f184先离、战者留原位到s55，开启时战者被招走（打到敌人s30消失才f462离开）、闲车留原位；tests/test_ai_recruit_combat.py 回放招谁；"入队后先打完再走"模拟器不符（strict xfail）；模拟器以"上一拍在开火"代替"目标在射程内"（INFERRED），CreateUnits具名槽不查此门（INFERRED）；见 work/re/b220_recruit_combat.md |
| 未做 | `战术/Tactic.UseTransports` | 14 |  | AI 模型代码里没有这个名字 |
| 推断 | `目标/AITargetingHeuristic.SortType=ThreatToWater` | 14 | a4 a5 a7 | C按名台子engine_aiwater：两电厂/近处守护者/AI两栖矿车，仅切Distance与ThreatToWater，实机两组采样s14后均近4/远0/家0；模型ThreatToWater选远，按名回放strict xfail。tests/test_water_threat.py独立断言原计数并保留原预测FAIL；近处Named对照因s40-41无采样亦strict xfail。无同帧候选资格/实际water威胁值/水域样本资格，不改模型、不晋升；见work/re/c_water_report.md |
| 推断 | `微操/IgnoreTargets.Rule` | 13 | a4 a5 a7 | E118 engine_aiignore_rule aiignrany/aiignrall：原版EASY包含标记不变，仅切ANY/ALL；同帧两成员，首伤396/397，前置失配0；f406/421分别状态0有目标与8无目标。ALL保留墙钟s22造出1导致的诊断FAIL，游戏帧前置成立；tests/test_ai_ignore_rule.py按名回放伤害/前置及ALL状态，ANY候选资格strict xfail；目标身份、工程师分类/Alpha资格仍gap，不晋升；见 work/re/e118_ignore_rule.md |
| 推断 | `战术/Tactic.Tactic=GarrisonBuilding` | 13 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/TimeSinceLastExpansionHeuristic` | 12 | a4 a5 a7 | C engine_ailastexp的60s/240s首次计时已对拍，Time字段单独登记；真实扩张后时间戳来源/重置消费者未测，初始时间戳0保持INFERRED，整条件保持推断；见work/re/c_lastexp_report.md |
| 已对拍 | `启发条件/TimeSinceLastExpansionHeuristic.Time` | 12 | a4 a5 a7 | C engine_ailastexp ailastexp:a：原版27关有效依赖仅60s/240s，另设常量阳性组；同图一局12条预写断言PASS，在家人数s19-62为4/4/0、s64-242为0/4/0、s244-345为0/0/0。tests/test_last_expansion_c.py按名回放四个窗口一致，无模型修改。仅首次扩张前计时；SDK其他Time取值、初始时刻精确值、真实扩张后重置/Past=false/逐帧边界仍gap；见work/re/c_lastexp_report.md |
| 推断 | `微操/AIMicroManagerData.CrushPreference` | 12 | a4 a5 a7 | 同Crush，开关/低偏好对照守军至少8的按名回放保留；完整清零strict xfail；不把活目标重选解释为死亡后等待，见work/re/e109_crush.md；不晋升 |
| 推断 | `微操/AIMicroManagerData.RandomTargetScoreModifier` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.TimeToKeepTargetMax` | 12 | a4 a5 a7 | E123仅作为固定Min=Max=2秒的控制量；未验证非退化随机区间/Max独立消费，不晋升；见work/re/e123_keep_target.md |
| 已对拍 | `微操/AIMicroManagerData.TimeToKeepTargetMin` | 12 | a4 a5 a7 | E123 aikeeptwo:a：Min=Max=2秒，score分配f495写until525，f503/519 hold，f527 go重写until557；aiegon:a零保持f375/383均go。tests/test_ai_keep_target.py按名回放原台候选资格、分配来源和保持/到期消费者；只验固定区间、已发布成员资格；随机区间、打分、死亡清理、其他来源与整局时钟仍gap；见work/re/e123_keep_target.md |
| 不涉及 | `战略状态/AIStrategicStateDefinition.ExecutionBeginFeedbackKey` | 12 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `战略状态/AIStrategicStateDefinition.ExecutionCanceledFeedbackKey` | 12 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | `战略状态/AIStrategicStateDefinition.ExecutionCompleteFeedbackKey` | 12 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=Expansion` | 12 | a4 a5 a7 | C aiexpc:a东矿区4、崖矿区0、普通实体0；D104同帧基地中心3850/3400，三矿点state2，选44号4173/2987（最近524）；模型先选基地再取最近合格矿点。tests/test_expansion_target.py按名回放原计数与候选选择；无距离上限、不读SortType。仅state2普通陆矿子集对拍；其他状态/占用/标记/敌距/水域拒绝仍INFERRED，动态矿表/基地注册和死亡清理仍gap；见work/re/c_expansion_d104_report.md |
| 已对拍 | `目标/AITargetingHeuristic.SortType=ThreatToGround` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 推断 | `组队招人/ObjectFilter.Include` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `组队招人/TeamTemplate.Priority=COOP` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 已对拍 | `战术/Tactic.Targetless` | 11 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | `战术/Tactic.UpdateTime` | 11 |  | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aidefense.py |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=FriendlyStructure` | 11 | a4 a5 a7 | docs/engine/aitactics.md#读数（FriendlyLandStructureHeuristic：engine_aidefense 守自家建造厂） |
| 已对拍 | `经济/AccountShare.Account=DEFENSE` | 11 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | `经济/AccountShare.Account=PRODUCTION` | 11 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiomove.py |
| 未做 | `经济/AccountShare.Account=SLUSH_FUND` | 11 | a4 a5 a7 | C按名台子engine_aislush：aislush100/aislush0仅交换SLUSH_FUND与PRODUCTION份额，两组电厂均s19一座、s29两座，零份额原预测FAIL保留；开局未区分此账户。第二轮有收入无开局：aislsdef全程零炮塔，aislddef在s28/48/68造出1/2/3座，s60为2。tests/test_slush_account.py原读数及模型回放；账户余额/实际支出消费者仍gap，不以开局计数吻合晋升；见work/re/c_slush_report.md |
| 未做 | `其他/BuildingPlacementDistance.Distance` | 10 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 已对拍 | `启发条件/PowerAdvantageHeuristic` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipoweradv.py |
| 已对拍 | `启发条件/PowerAdvantageHeuristic.Above` | 10 | a4 a5 a7 | C engine_aipowerabove aipabtrue/aipabfalse:a：同图4对8同型守护者、Value=1.0，仅Above=true/false；s40在家/AI总数/玩家坦克分别4/4/8与0/4/8，两局各3条PASS，tests/test_simai_powerabove_c.py按名回放两组实测。仅验证该固定军队与阈值下Above翻转；精确求值帧、其他比值/动态伤亡/防御计入仍gap；未改模型与阈值，见work/re/c_powerabove_report.md |
| 已对拍 | `启发条件/PowerAdvantageHeuristic.IncludeEnemyDefenses` | 10 | a4 a5 a7 | C engine_aipowerenemy aipenoff/aipenon:a：同图8对4守护者、一座玩家光谱塔及电厂，固定Value=2.0/Above=true/IncludeOwnDefenses=false，仅IncludeEnemyDefenses=false/true；s40在家/AI总数/玩家坦克/玩家塔为0/8/4/1与8/8/4/1，两局各4条PASS。tests/test_simai_powerenemy_c.py按名回放原读数；仅验证此塔与军队组合，精确比值公式、求值帧、其他防御类别仍gap；未改模型或阈值，见work/re/c_powerenemy_report.md |
| 已对拍 | `启发条件/PowerAdvantageHeuristic.IncludeOwnDefenses` | 10 | a4 a5 a7 | C engine_aipowerown aipownoff/aipownon:a：同图4对8守护者、一座己方光谱塔及电厂，固定Value=0.5/Above=true，仅IncludeOwnDefenses=false/true；s40在家/AI总数/玩家坦克/己方塔为4/4/8/1与0/4/8/1，两局各4条PASS。tests/test_simai_powerown_c.py按名回放原读数；仅验证此塔与军队组合，精确比值公式、求值帧、其他防御类别及敌方防御计入仍gap；未改模型或阈值，见work/re/c_powerown_report.md |
| 已对拍 | `启发条件/PowerAdvantageHeuristic.Value` | 10 | a4 a5 a7 | C engine_aipowervalue aipval1/aipval01:a：同图4对8同型守护者、Above=true，仅Value=1.0/0.1；s40在家/AI总数/玩家坦克分别4/4/8与0/4/8，两局各3条PASS。tests/test_simai_powervalue_c.py按名回放两组实测；仅验证该固定军队下两阈值的行为差异，完整比值公式、精确边界/求值帧、动态伤亡与防御计入仍gap；未改模型或阈值，见work/re/c_powervalue_report.md |
| 已对拍 | `目标/AITargetingHeuristic.SearchRange` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 推断 | `组队招人/TeamTemplate.Priority=DEFENSE_HIGH` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `战术/Tactic.Tactic=ExactExpansion` | 9 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 已对拍 | `启发条件/EnemyNearbyHeuristic.MinEnemyValue` | 8 | a4 a5 a7 | C engine_aiminvalue aiminvalue/aiminvaluehi:a：27关依赖显式取值1000/2500；单盟军矿车1000、合计2400/3800对照；tests/test_min_enemy_value_c.py按名回放台上前三路。低值反向组台上留家1、模型0，strict xfail；招募/个人移动原因及其他对象价值算法保持gap；见work/re/c_minvalue_report.md |
| 推断 | `启发条件/ObjectOfTypeExistsHeuristic.Location` | 8 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.ForbiddenObjectStatus` | 8 | a4 a5 a7 | C engine_aiforbid a：同近电厂仅切UNDER_IRON_CURTAIN禁用字段；无过滤有位/有过滤有位/有过滤清位三组原状态与近远家计数分别1/4/0/0、1/0/4/0、0/4/0/0，均PASS。tests/test_forbidden_status.py按名回放并断言原图计数；单位置位过滤吻合，未改模型。追加原UNATTACKABLE UNDER_IRON_CURTAIN组合，仅IRON置位，原状态计数1；空/单IRON/双位过滤s40.1计数为1/4/0/0、1/0/4/0、1/0/4/0，三局PASS支持该子集ANY，模型吻合。再测仅UNATTACKABLE置位，空/单UNATTACKABLE/双位过滤s40.1原读数分别2/4/0/0、2/0/4/0、2/0/4/0；s5..41原状态均2，三局PASS及按名回放支持另一单位置位子集ANY，未改模型。双位同时置位追加空过滤/原双位过滤两局均PASS，s40.1原计数3/4/0/0与3/0/4/0，s5..41状态均3；tests/test_forbidden_status.py按名回放及原图复读均吻合，未改模型。复核旧双位及单UNATTACKABLE共五局：run均无ra3ext.log，图像index无逻辑帧；新双位/单UNATTACKABLE两局启用观察宿主，CNVStateTP/index0均f151近电厂ok=false/stat、远兵营ok=true并选中；公开原记录与按名资格/选择回放吻合。s40状态/近/远/家3/0/0/0与2/0/3/0，对应逻辑帧327/363，原到达预期未改、两strict xfail；截图秒不能直接当模型秒，时钟/到达仍gap，不重跑。target_picks仍无两位原状态与运行时掩码，why.stat仅拒绝分类，不据此证明一般掩码公式；原版技能及AIRBORNE_TARGET/SUBMERGED仍gap，整字段不晋升；见work/re/c_forbidnew_report.md（旧证据见c_forbidframe_report.md及该报告指针） |
| 推断 | `目标/AITargetingHeuristic.SortType=ThreatToAir` | 8 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/BeaconExistsHeuristic` | 7 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/BeaconExistsHeuristic.Exists` | 7 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.Beacon` | 7 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=Beacon` | 7 | a4 a5 a7 | AI 模型代码里读了这个名字 |
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
| 已对拍 | `战术/Tactic.Tactic=ReactiveDefense` | 6 |  | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aihome.py |
| 已对拍 | `组队招人/TeamTemplate.Priority=SCRIPTED` | 6 |  | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 未做 | `组队招人/TeamTemplate.RequireCanAttackTarget` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 已对拍 | `人格/EnemyFilter.Include` | 5 | a4 a5 a7 | tests/test_enemyfilter.py::test_enemyfilter_named_bench_replay（C 的 engine_aienemyfilter aiefharv / aiefeng / aiefself：Include HARVESTER 近处敌矿车触发、ENGINEER 不触发，SAME_PLAYER 无自家矿车不触发；模型 B 第 155 轮接进 EnemyNearby） |
| 已对拍 | `人格/EnemyFilter.Relationship` | 5 | a4 a5 a7 | tests/test_enemyfilter.py::test_enemyfilter_named_bench_replay（C 的 engine_aienemyfilter aiefharv / aiefeng / aiefself：Include HARVESTER 近处敌矿车触发、ENGINEER 不触发，SAME_PLAYER 无自家矿车不触发；模型 B 第 155 轮接进 EnemyNearby） |
| 推断 | `人格/EnemyFilter.Rule` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/OpenNodeHeuristic` | 5 | a4 | AI 模型代码里读了这个名字 |
| 未做 | `微操/AIMicroManagerData.MinDistanceFromBaseToIgnoreTargets` | 5 | a4 a5 a7 | E120 engine_aiignore aiignzt/aiignnt：同run基地选择与目标位置配对，0/2000首伤397/396；f406/421零组状态8无目标、高组状态0有目标。消费者已接被动选敌、敌对可攻击及逐人分配过滤；唯一基地(3850,3400)与home一致，两目标距基地502.49；tests/test_ai_ignore_distance.py按名断言基地/目标位置与距离门，零组状态通过，高组资格仍strict xfail；多基地选择/精确边界/无基地/候选资格仍gap，不晋升已对拍；见 work/re/e120_ignore_base.md |
| 未做 | `微操/AIMicroManagerData.PassiveTargetSearchDistance` | 5 | a4 a5 a7 | E104 engine_aipassive_distance aipsdz/aipsdt/aipsds/aipsdl：0/1/200/600均f140状态6选四人旁厂，f320状态0；中心距350.3、逐兵至少324.3，微操目标不同于战术目标。两轮未出现距离分离；tests/test_ai_passive_distance.py按台名回放选择/移动/存活，精确首选时钟strict xfail；本入口未显现消费者，零值全局语义/距离基准/其他入口仍gap，暂停、不加猜测消费者、不晋升；见 work/re/e104_passive_distance.md、work/re/handoff-e.md |
| 推断 | `微操/AIMicroManagerData.SiegeWeaponBuffer` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.SpecialPowerDelayMaximum` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.SpecialPowerDelayMinimum` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/IgnoreTargets.Include` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `微操/SpecificSpecialPowerDelay.TogglePowerSubType=TOGGLE_LOCKDOWN` | 5 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=EnemyStructureCloseToShore` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=TechBuilding` | 5 | a4 a5 a7 | C aitechkind/aitechnon:a 原名ClosestTechBuildingHeuristic、敌距0、空VitalKindOf，同位中立油井/普通电厂；f16油井ok并选中，普通电厂不在科技候选集合，阴性组反选地图原有远油井(700,3200)。s40四区域计数4/0/0/0与0/0/0/0；tests/test_tech_building_c.py按名回放选择/计数，阴性模型留家、两strict xfail，原预测FAIL另strict xfail。资格对照已测，实时基地/搜索范围参考仍gap，不晋升；见work/re/c_techkind_report.md、handoff-c.md |
| 推断 | `目标/AITargetingHeuristic.MaxDistanceToShore` | 5 | a4 a5 a7 | C按名台子engine_aishore：同一岸边电厂仅上限2000改1，2000组s14目标区4/s25全离家，1组s1-65在家4/目标区0；普通EnemyStructure阳性对照同2000组。tests/test_shore_distance.py断言原读数并按名回放；1组strict xfail，世界桥接尚未提供实际岸距。复杂海岸/取点算法仍gap，未晋升；见work/re/c_shore_report.md |
| 已对拍 | `目标/AITargetingHeuristic.SortType=ClosestToEnemy` | 5 | a4 a5 a7 | C aiclosest:a：D158 target_picks同帧f16四槽按过滤分组选择塔/塔/电厂/电厂，tests/test_closest_enemy_c.py按名回放目标选择并断言实机候选/forbid/最近敌距；仅陆地选择切片已对拍，水域/矿厂过滤仍gap。选后战术/微操转攻导致区域人数4/4/0/0，后两路整局strict xfail保留交E；见work/re/c_closest_recheck_report.md |
| 推断 | `目标/AITargetingHeuristic.UnderAttack` | 5 |  | C重开复用D164：满血电厂f5记录、f16门true并选中；last33/clear109来源活，另一对象last146/clear222来源已删，clr不等于同帧门。新aiuagate两局，修正旗标空作用域后普通对照f49/f139选建筑，UnderAttack两路无目标；受伤电厂已不在候选，仅另三座last=-1的f49门false，缺该对象后命中/清除门。tests/test_underattack_gate_c.py断言原始读数、实际消费者和具名aiunderatk回放；三strict xfail：后命中门证据、FriendlyStructure绕过布尔、具名选择差异。世界层缺真实受伤时钟，HP差两秒不能替代；两局耗完、暂停不晋升；见work/re/c_underattack_reopen_report.md；27关范围仍见c_underattack_scope.json |
| 推断 | `经济/BudgetState.Difficulty` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/IncomeAdvantageHeuristic` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/IncomeAdvantageHeuristic.Above` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/IncomeAdvantageHeuristic.Value` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/OpenNodeHeuristic.Exists` | 4 | a4 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/OpenNodeHeuristic.MinDistanceFromEnemy` | 4 | a4 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.CanUseSiegeState` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.GatherTempVisionRangeBonus` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.RetreatTempVisionRangeBonus` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/IgnoreTargets.Exclude` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `目标/AITargetingHeuristic.VitalObjectStatus` | 4 | a4 a5 a7 | C engine_aivital aivitalon/off:a：四原名宿主、脚本状态置/清对照；s55-60原打包状态*100+目标区*10+家中计数分别24/4/4/140与24/4/4/4。ATTACHED置位到目标4、清位留家4，按名回放吻合；仅脚本位子集。三地面样本的AIRBORNE_TARGET始终读0，模型却保留；路0区域重叠且位置差异未解。tests/test_vital_status_c.py断言原图读数，四strict xfail保留状态/位置差异；缺真实飞行/落地状态入口、同帧候选资格及原附着生命周期，整字段不晋升。见work/re/c_vital_report.md |
| 未做 | `人格/AIPersonalityDefinition.EmergencyManagerHandleConyardInDangerAtDifficulty` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | `人格/PersonalityMap.Personality` | 3 |  | AI 模型代码里读了这个名字 |
| 推断 | `人格/PersonalityMap.Side` | 3 |  | AI 模型代码里读了这个名字 |
| 未做 | `战术/Tactic.AestheticsManagerMinDistanceFromHarvester` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `战术/Tactic.AestheticsManagerPatrolIdleTime` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 已对拍 | `战术/Tactic.CombatLeashSlack` | 3 |  | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aidefense.py |
| 推断 | `战术/Tactic.Tactic=NullTactic` | 3 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=Point` | 3 | a5 a7 | C engine_aipoint新ID CNVPointWater/CNVPointTiny，真实范围1500/1：f16同原点3850,3400；1500有38候选/8合格，选2890,3011；1有40候选/0合格，不选。tests/test_point_target_c.py按任务名用原生候选回放TargetsBlock，选择与槽坐标吻合；模型新增Point搜索提供者入口及无威胁样本退回最近点；未提供输入时不代用普通对象。整项保持TODO：随机生成/基地世界输入/非空威胁及高度未闭环，整局阳性strict xfail；旧同名范围1实际加载1500；新1500局计数窄窗缺帧FAIL，1局PASS。见work/re/c_point_resume_report.md；27关静态14关45条宿主引用见c_point_scope.json |
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
| 已对拍 | `人格/BaseSelection.SortOrder=PREFER_NEWEST` | 2 | a4 a5 a7 | 初始双厂同分候选，OLD选基地0、NEW选基地1；按名选择点/计数回放，仅该排序子集，见work/re/c_bs3_report.md |
| 推断 | `启发条件/CanBuildBuildingsOnSurfaceHeuristic` | 2 | a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/CanBuildBuildingsOnSurfaceHeuristic.MaxPlacementGridCells` | 2 | a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/CanBuildBuildingsOnSurfaceHeuristic.MinPlacementGridCells` | 2 | a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/CanBuildBuildingsOnSurfaceHeuristic.Surfaces` | 2 | a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `微操/AIMicroManagerData.MaxUnitIdleDistanceChange` | 2 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `战术/Tactic.Tactic=Hunt` | 2 |  | AI 模型代码里读了这个名字 |
| 推断 | `战术/Tactic.Tactic=SimpleDefense` | 2 |  | AI 模型代码里读了这个名字；台上量过（docs/engine/aitactics.md），没有测试跑这个台子 |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=Husk` | 2 | a4 a5 a7 | C aihusknone/aihusknamed:a同位普通中立油井，LandHusk阴性与NamedObject阳性；两局f16分别found=0/1，阳性选(2900,3300)，s20两组总数4，均PASS。tests/test_husk_target_c.py按名回放并断言原选择记录及存活计数。模型移除Husk通用中立物回退；缺真实残骸候选提供者时不选目标，不以KindOf或模板名字猜登记。原版残骸创建/候选资格/水域阳性仍gap，不晋升整项；见work/re/c_husk_report.md |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=Team` | 2 |  | C核对SDK两原名宿主AITarget_S01_Warriors/Attackers，编译状态AIState_S01_KillWarriors01引用两者；按真实队伍全名选择，不能以单对象或NamedObject替代。当前目标View没有队伍候选提供者，target_picks公开接口未提供队伍目标身份/同帧成员资格；缺B/D事实入口，0局，暂停且不晋升；见work/re/c_team_gate_report.md |
| 推断 | `目标/AITargetingHeuristic.HeuristicType=UnderAttackBy` | 2 | a4 a5 a7 | SDK陆/水两原名与编译EmergencyDefense六引用已核验；C两具名交战局：f18真实来源3185，Land f19选中同源。Water仅f16命中前空目标，日志至f137无命中后直接选择行；来源候选列表未发布，不能据此证明Location拒绝。simai未供attacking_us，Land具名回放与Water直接拒绝证据各一strict xfail；来源资格/置清保持gap，不晋升；见work/re/c_underattackby_resume_report.md |
| 未做 | `目标/AITargetingHeuristic.IgnoreMinDistanceFromConyardEntranceForTime` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `目标/AITargetingHeuristic.MinDistanceFromConyardEntrance` | 2 | a4 a5 a7 | C engine_aiconyard aicyard0/300:a仅切出口距离0/300、保留原15s豁免，两局核心/电厂/近处电厂/宿主均1/0/0/1。CNVStateTP队伍均无成员、目标-1，tgt未发布该状态记录；不能以无行推断未调用或以基地锚点代出口。tests/test_conyard_target.py仅断言诊断读数和具名回放，缺同帧真实出口/候选资格/选址点/起算帧；两局预算耗完，暂停且整字段未做，不晋升；见work/re/c_conyard_report.md |
| 推断 | `组队招人/ObjectFilter.Exclude` | 2 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 未做 | `经济/AccountShare.Account=SPECIAL_OPERATIONS` | 2 |  | AI 模型代码里没有这个名字 |
| 未做 | `经济/AccountShare.Account=TECHNOLOGY` | 2 |  | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemyResortingTime` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemySortingBrutalDifficulty` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemySortingEasyDifficulty` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemySortingHardDifficulty` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.EnemySortingMediumDifficulty` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | `人格/AIPersonalityDefinition.MaxStrategicTargets` | 1 |  | AI 模型代码里没有这个名字 |
| 不涉及 | `人格/AIPersonalityDefinition.SkirmishTimeTillGreeting` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 推断 | `人格/AIPersonalityDefinition.UnitBuilderEnemyNearbyDistance` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/AIPersonalityDefinition.UnitBuilderEnemyNearbyMultiplier` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/Filter.Exclude` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/Filter.Include` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `人格/Filter.Rule` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 已对拍 | `人格/RetreatBaseCriteria.PreferredNotBaseTypes` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aihome.py |
| 已对拍 | `人格/RetreatBaseCriteria.SortOrder` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aihome.py |
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
| 推断 | `启发条件/StructureOrHarvesterUnderAttackHeuristic` | 1 |  | AI 模型代码里读了这个名字 |
| 推断 | `启发条件/StructureOrHarvesterUnderAttackHeuristic.TimeSinceAttacked` | 1 |  | AI 模型代码里读了这个名字 |
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
| 已对拍 | `战术/Tactic.EndBehavior=PICK_NEW_TARGET` | 1 |  | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 推断 | `战略状态/AIStrategicStateDefinition.MaxInactiveCopies` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 已对拍 | `战略状态/AIStrategicStateDefinition.PathfindingCheckType=QuickDoesAttackPathExist` | 1 | a4 a5 a7 | D152 engine_aipathcheck aipfdef/aipfatk/aipfpath/aipfnone:a（去桥尼亚加拉，SimpleAttack 打对岸玩家基地，四局只差这个字段）：不写 / QuickDoesAttackPathExist / QuickDoesPathExist 三局 4 个维和从不出门，CNVTeams 每 90 帧建一支空队、约 75 帧后过期；None 一局 f21 招满 4 人、s6 出门。走不到的单位招人时就不招（模型 TeamMaker.reach，缺省按战术类 data.PATH_CHECK）；tests/test_ai_pathcheck.py 按名断言台上读数并回放。gap：AttackPath 与 Path 在"岸边射程内"时的区别没测；出门后路断的周期踢人读到没上台；见 work/re/d152_pathcheck.md |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=Bridge` | 1 |  | C engine_aibridge aibridgeon/off:a原生700长桥/普通中立电厂两局PASS；桥部件编码322/33与111/11，起终点存活1/0与1/1。两局f16 Bridge槽均found=0/n=0；真桥起点NamedObject选对象1(2250,4200)，终点不选。tests/test_bridge_target_c.py按名回放并断言原生读数与具名消费；模型仍选真桥终点且保留已消失终点，两strict xfail。缺桥登记/资格/状态及登记后求值与端点生命周期事实，不据空列表改模型；两局耗完，不晋升，见work/re/c_bridge_report.md |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=Crate` | 1 | a4 a5 a7 | C engine_aicrate aicrateon/off:a同位原版HealCrate与普通中立油井对照；tests/test_crate_target_c.py按名回放并断言原生Crate槽与独立NamedObject槽的选择/对象/坐标。真实箱子阳性、普通中立物阴性；只验恒定状态下选择，原版CratePickup的29秒间隔、捡取/治疗/撤销、多箱排序、所有权与范围仍gap；原始证据见work/re/c_crate_report.md |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=EnemyGarrison` | 1 |  | C engine_aienemygarr aiegarron/off:a真进驻敌方排屋/同位敌电厂，tests/test_enemy_garrison_target_c.py具名回放；归属和ENCLOSED已独立观测，但原生EnemyGarrison两组候选为空，NamedObject能选控制物。未取得有效阳性，不据空候选修改模型；两组模型选普通电厂而原生无目标，strict xfail；缺登记后有效重求值/敌方搜索资格及驻军候选登记事实，不晋升，见work/re/c_enemygarr_report.md |
| 未做 | `目标/AITargetingHeuristic.HeuristicType=Help` | 1 |  | AI 模型代码里没有这个名字 |
| 已对拍 | `目标/AITargetingHeuristic.HeuristicType=NeutralGarrison` | 1 | a4 a5 a7 | C engine_aineutralgarr aigarron/off:a原版排屋/油井同位对照；tests/test_garrison_target_c.py按名回放并断言原生选择、对象与坐标：两组均选原图HV_Shop01(3180,2760)，排屋候选ok=true，油井不入候选。补目标视图漏掉的可驻军地图建筑；GARRISON资格代理仍INFERRED，完整容器/容量/占领/进入/撤销/排序/范围及BaseSelection仍gap；阴性局原存活判定因s2–s3无采样FAIL，原始值及原因保留，未重跑；见work/re/c_garrison_report.md |
| 未做 | `组队招人/TeamTemplate.BaseDefenseMaxDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | `组队招人/TeamTemplate.IsBaseDefenseTeam` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | `造兵/BuildEntry.Score` | 1 |  | AI 模型代码里读了这个名字 |
