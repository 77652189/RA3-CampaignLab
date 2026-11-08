# 原版功能总清单（引擎 A：脚本层、物体模块、武器效果）

由 `experimental/cnv/inventory.py` 从原版数据生成，**别手改**；`tests/test_inventory.py` 在它过期时变红。状态与判定规则见脚本 docstring（ADR 0026）。用量：脚本 = 原版战役脚本里出现的次数；模块 = 原版战役地图里摆了的、用到它的物体种数（括号里是全部物体种数）；武器效果 = 用到它的原版武器数。

| 部分 | 项数 | 已对拍 | 推断 | 未做 | 不涉及 | 按用量已有（已对拍+推断） |
|---|---|---|---|---|---|---|
| 脚本动作 | 427 | 0 | 87 | 295 | 45 | 69% |
| 脚本条件 | 89 | 0 | 20 | 69 | 0 | 85% |
| 物体模块 | 184 | 0 | 18 | 152 | 14 | 21% |
| 武器效果 | 25 | 0 | 4 | 21 | 0 | 52% |

## 脚本动作

| 状态 | 名字 | 用量 | 说明 |
|---|---|---|---|
| 推断 | `ENABLE_SCRIPT` | 5727 | 引擎模型核心 |
| 推断 | `SET_MILLISECOND_TIMER` | 4153 | 引擎模型核心 |
| 推断 | `SET_FLAG` | 4105 | Sim.act / Sim.cond 有分支 |
| 推断 | `ALLOW_DISALLOW_ONE_BUILDING` | 3466 | Sim.act / Sim.cond 有分支 |
| 未做 | `PLAYER_LOCK_PLAYER_TECH` | 1887 | Sim.act / Sim.cond 不认识 |
| 推断 | `DISABLE_SCRIPT` | 1099 | 引擎模型核心 |
| 推断 | `MOVE_NAMED_UNIT_TO` | 1000 | Sim.act / Sim.cond 有分支 |
| 推断 | `LINK_MISSION_OBJECTIVE_TO_OBJECT` | 950 | Sim.act / Sim.cond 有分支 |
| 推断 | `NAMED_DELETE` | 908 | Sim.act / Sim.cond 有分支 |
| 未做 | `CREATE_REINFORCEMENT_TEAM` | 753 | Sim.act / Sim.cond 不认识 |
| 推断 | `SET_MISSION_OBJECTIVE_STATUS` | 732 | Sim.act / Sim.cond 有分支 |
| 推断 | `PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT` | 640 | 只记进时间线（sim.SHOWN） |
| 推断 | `CALL_SUBROUTINE` | 533 | 引擎模型核心 |
| 未做 | `UNIT_IDLE_FOR_FRAMECOUNT` | 504 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT_WITH_SUBTITLE` | 445 | 纯表现（名字规则） |
| 推断 | `MOVIE_PLAY_RADAR` | 433 | 只记进时间线（sim.SHOWN） |
| 推断 | `CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION` | 399 | Sim.act / Sim.cond 有分支 |
| 未做 | `OBJECTLIST_ADDOBJECTTYPE` | 383 | Sim.act / Sim.cond 不认识 |
| 推断 | `PLAYER_SET_MONEY` | 345 | Sim.act / Sim.cond 有分支 |
| 未做 | `SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY` | 343 | Sim.act / Sim.cond 不认识 |
| 推断 | `PLAYER_RELATES_PLAYER` | 319 | Sim.act / Sim.cond 有分支 |
| 未做 | `UNIT_AFFECT_OBJECT_PANEL_FLAGS` | 317 | Sim.act / Sim.cond 不认识 |
| 未做 | `SET_MISSION_HOT_SPOT_VISIBILITY` | 300 | Sim.act / Sim.cond 不认识 |
| 推断 | `MOVE_TEAM_TO` | 298 | Sim.act / Sim.cond 有分支 |
| 推断 | `CREATE_NAMED_ON_TEAM_AT_WAYPOINT` | 291 | Sim.act / Sim.cond 有分支 |
| 推断 | `NAMED_ATTACK_NAMED` | 271 | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT` | 264 | Sim.act / Sim.cond 不认识 |
| 未做 | `CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION` | 259 | Sim.act / Sim.cond 不认识 |
| 推断 | `MOVE_CAMERA_TO` | 255 | Sim.act / Sim.cond 有分支 |
| 推断 | `OBJECT_CREATE_RADAR_EVENT` | 254 | 只记进时间线（sim.SHOWN） |
| 未做 | `UNIT_IDLE_FOR_SECONDS` | 237 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_TRANSFER_TO_PLAYER` | 235 | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_TRANSFER_OWNERSHIP_PLAYER` | 231 | Sim.act / Sim.cond 有分支 |
| 推断 | `INCREMENT_COUNTER` | 229 | 引擎模型核心 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:SHROUD_REVEAL_TO_ALL` | 218 | 状态位 SHROUD_REVEAL_TO_ALL 只记下来 |
| 未做 | `PLAYER_SET_MAX_PLAYER_POWER_POINTS` | 206 | sim.IGNORED 明确丢掉 |
| 推断 | `NAMED_KILL` | 204 | Sim.act / Sim.cond 有分支 |
| 未做 | `TEAM_HUNT` | 203 | Sim.act / Sim.cond 不认识 |
| 未做 | `CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT` | 196 | sim.IGNORED 明确丢掉 |
| 推断 | `LINK_MISSION_OBJECTIVE_TO_WAYPOINT` | 194 | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_FOLLOW_WAYPOINTS` | 192 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY` | 186 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS` | 184 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `FADE_OUT_TO_BLACK` | 177 | 纯表现（名字规则） |
| 不涉及 | `FADE_IN_FROM_BLACK` | 176 | 纯表现（名字规则） |
| 推断 | `NAMED_FLASH` | 173 | 只记进时间线（sim.SHOWN） |
| 推断 | `SET_COUNTER` | 171 | 引擎模型核心 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:SKIRMISH_AI_DO_NOT_ATTACK` | 171 | 状态位 SKIRMISH_AI_DO_NOT_ATTACK 只记下来 |
| 推断 | `NAMED_SHOW_INFOBOX` | 166 | 只记进时间线（sim.SHOWN） |
| 未做 | `TEAM_USE_COMMANDBUTTON_ABILITY` | 162 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_SPECIAL_POWER_AVAILABILITY` | 158 | Sim.act / Sim.cond 不认识 |
| 推断 | `PATH_MUSIC_PLAY_EVENT` | 155 | 只记进时间线（sim.SHOWN） |
| 不涉及 | `CAMERA_LETTERBOX_END` | 154 | 纯表现（名字规则） |
| 推断 | `DISABLE_INPUT` | 152 | Sim.act / Sim.cond 有分支 |
| 未做 | `TEAM_AI_TRANSFER` | 152 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `EVA_SET_ENABLED_DISABLED` | 148 | 纯表现（名字规则） |
| 不涉及 | `PLAY_SOUND_EFFECT_AT` | 147 | 纯表现（名字规则） |
| 推断 | `ATTACK_MOVE_NAMED_UNIT_TO` | 146 | Sim.act / Sim.cond 有分支 |
| 不涉及 | `SOUND_PLAY_NAMED` | 137 | 纯表现（名字规则） |
| 推断 | `UNIT_AI_TRANSFER_ALL` | 137 | Sim.act / Sim.cond 有分支 |
| 推断 | `ENABLE_INPUT` | 132 | Sim.act / Sim.cond 有分支 |
| 推断 | `NO_OP` | 130 | 引擎模型核心 |
| 未做 | `TEAM_AFFECT_OBJECT_PANEL_FLAGS` | 130 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_AI_TRANSFER` | 129 | Sim.act / Sim.cond 不认识 |
| 未做 | `TELEPORT_STRUCTURE` | 128 | Sim.act / Sim.cond 不认识 |
| 推断 | `CAMPAIGN_CREATE_AUTO_SAVE` | 127 | 只记进时间线（sim.SHOWN） |
| 未做 | `UNIT_SET_STANCE` | 124 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_DELETE` | 122 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_KILL` | 121 | Sim.act / Sim.cond 不认识 |
| 推断 | `SET_TIMER` | 119 | 引擎模型核心 |
| 推断 | `NAMED_STOP` | 118 | Sim.act / Sim.cond 有分支 |
| 推断 | `UNIT_TELEPORT_TO_WAYPOINT` | 118 | Sim.act / Sim.cond 有分支 |
| 未做 | `PLAYER_CAMERA_MOVE_TO` | 117 | Sim.act / Sim.cond 不认识 |
| 推断 | `ATTACK_MOVE_TEAM_TO` | 116 | Sim.act / Sim.cond 有分支 |
| 未做 | `PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT` | 116 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_IDLE_FOR_SECONDS` | 114 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_SET_BASE_POWER` | 112 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_TOGGLE_RESOURCE_SHARING` | 111 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_SET_MODELCONDITION_GENERIC` | 111 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PLAY_SOUND_AS_AI_COCOMMANDER_DIALOG` | 109 | 纯表现（名字规则） |
| 未做 | `TEAM_CREATE_RADAR_EVENT` | 107 | Sim.act / Sim.cond 不认识 |
| 推断 | `MAP_REVEAL_PERMANENTLY_AT_WAYPOINT` | 105 | Sim.act / Sim.cond 有分支 |
| 不涉及 | `CAMERA_LETTERBOX_BEGIN` | 104 | 纯表现（名字规则） |
| 未做 | `NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY` | 103 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ALLOW_AI_AUTOACQUIRE` | 103 | Sim.act / Sim.cond 不认识 |
| 推断 | `SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER` | 101 | Sim.act / Sim.cond 有分支 |
| 不涉及 | `RESET_CAMERA` | 100 | 纯表现（名字规则） |
| 不涉及 | `CAMERA_LETTERBOX_BEGIN_WITH_RADAR` | 98 | 纯表现（名字规则） |
| 推断 | `SET_RANDOM_COUNTER` | 97 | 引擎模型核心 |
| 未做 | `PLAYER_SET_PLAYER_POWER_POINTS` | 95 | sim.IGNORED 明确丢掉 |
| 未做 | `SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER` | 94 | Sim.act / Sim.cond 不认识 |
| 推断 | `MAP_REVEAL_ALL_PERM` | 89 | Sim.act / Sim.cond 有分支 |
| 推断 | `MAP_SWITCH_BORDER` | 87 | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_SET_DISABLED` | 86 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_REMOVE_INFOBOX` | 83 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_FOLLOW_WAYPOINTS` | 83 | Sim.act / Sim.cond 不认识 |
| 推断 | `SKIRMISH_AI_MAKE_BASE` | 82 | Sim.act / Sim.cond 有分支 |
| 推断 | `SET_RANDOM_MSEC_TIMER` | 77 | 引擎模型核心 |
| 推断 | `TEAM_ATTACK_NAMED` | 76 | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateEjectPassengersSpecialPowerUntargeted` | 75 | 只记进时间线，没有效果 |
| 未做 | `SKIRMISH_AI_USE_REPAIRS` | 75 | sim.IGNORED 明确丢掉 |
| 未做 | `NAMED_OUTLINE` | 74 | Sim.act / Sim.cond 不认识 |
| 未做 | `FLASH_UI_UNIT_ABILITY_BUTTON` | 72 | Sim.act / Sim.cond 不认识 |
| 推断 | `MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT` | 72 | Sim.act / Sim.cond 有分支 |
| 推断 | `PLAYER_GIVE_MONEY` | 72 | Sim.act / Sim.cond 有分支 |
| 推断 | `UNIT_SET_TEAM` | 72 | Sim.act / Sim.cond 有分支 |
| 未做 | `TEAM_CHANGE_OBJECT_STATUS` | 71 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_GARRISON_TEAM_INSTANTLY` | 68 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_CLEAR_MODELCONDITION` | 68 | Sim.act / Sim.cond 不认识 |
| 未做 | `CREATE_UNNAMED_ON_TEAM_AT_NAMED_OBJECT_LOCATION` | 67 | Sim.act / Sim.cond 不认识 |
| 未做 | `LINK_MISSION_HOT_SPOT_TO_OBJECT` | 67 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_AI_USE_REBUILD_SYSTEM` | 67 | sim.IGNORED 明确丢掉 |
| 未做 | `TEAM_MERGE_INTO_TEAM` | 67 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_HUNT` | 66 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_FLASH` | 66 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_OVERRIDE_RELATION_TO_PLAYER` | 64 | Sim.act / Sim.cond 不认识 |
| 未做 | `SET_MISSION_HOT_SPOT_ACTIVENESS` | 61 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION` | 60 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_FORCE_ATTACK_NAMED` | 59 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_FORCE_ATTACK_WAYPOINT` | 59 | Sim.act / Sim.cond 不认识 |
| 推断 | `PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM` | 59 | 只记进时间线（sim.SHOWN） |
| 未做 | `SET_REFERENCE_TO_RANDOM_TEAM_MEMBER` | 59 | Sim.act / Sim.cond 不认识 |
| 推断 | `MAP_REVEAL_ALL_UNDO_PERM` | 58 | Sim.act / Sim.cond 有分支 |
| 推断 | `SHOW_MILITARY_CAPTION` | 58 | 只记进时间线（sim.SHOWN） |
| 未做 | `NAMED_FOLLOW_WAYPOINTS_EXACT` | 56 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_EXECUTE_SEQUENTIAL_SCRIPT` | 56 | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_SET_MAX_HEALTH` | 53 | Sim.act / Sim.cond 有分支 |
| 未做 | `TOGGLE_RADAR_UI` | 53 | Sim.act / Sim.cond 不认识 |
| 未做 | `DISPLAY_TUTORIAL_TEXT` | 52 | Sim.act / Sim.cond 不认识 |
| 推断 | `PLAY_SOUND_EFFECT` | 51 | 只记进时间线（sim.SHOWN） |
| 未做 | `TEAM_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT` | 51 | Sim.act / Sim.cond 不认识 |
| 推断 | `DECREMENT_COUNTER` | 50 | 引擎模型核心 |
| 推断 | `DISPLAY_COUNTDOWN_TIMER` | 50 | Sim.act / Sim.cond 有分支 |
| 未做 | `SELL_OBJECT` | 50 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ATTACK_TEAM` | 50 | Sim.act / Sim.cond 不认识 |
| 未做 | `FLASH_UI_BUILD_BUTTON` | 48 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JAAVT1_Transform` | 48 | 只记进时间线，没有效果 |
| 未做 | `SET_UNIT_REFERENCE` | 48 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_ATTACK_FOLLOW_WAYPOINTS` | 47 | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_RECEIVE_UPGRADE` | 47 | Sim.act / Sim.cond 有分支 |
| 未做 | `TEAM_SET_STANCE` | 45 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_CUSTOM_COLOR` | 44 | Sim.act / Sim.cond 不认识 |
| 推断 | `HIDE_COUNTDOWN_TIMER` | 43 | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_SovietAntiGroundAircraftEvacuate` | 43 | 只记进时间线，没有效果 |
| 未做 | `PLAYER_SET_OVERRIDE_RELATION_TO_TEAM` | 43 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleSpiderHole` | 41 | 只记进时间线，没有效果 |
| 未做 | `PLAYER_SET_SPECIAL_POWER_COUNTDOWN` | 41 | Sim.act / Sim.cond 不认识 |
| 未做 | `FOR_EACH_PLAYER_OBJECT_EXECUTE_SCRIPT` | 39 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JAIV_Transform` | 38 | 只记进时间线，没有效果 |
| 未做 | `TECHTREE_MODIFY_BUILDABILITY_OBJECT` | 38 | Sim.act / Sim.cond 不认识 |
| 未做 | `EVALUATE_SCRIPT` | 35 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_AI_TRANSFER_ALL` | 35 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_CONTEXT_SENSITIVE_ATTACK` | 35 | Sim.act / Sim.cond 不认识 |
| 未做 | `FOR_EACH_TEAM_MEMBER_EXECUTE_SCRIPT` | 34 | Sim.act / Sim.cond 不认识 |
| 未做 | `LINK_MISSION_HOT_SPOT_TO_WAYPOINT` | 34 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_DAMAGE` | 34 | Sim.act / Sim.cond 不认识 |
| 未做 | `FLASH_MOUSE_HUD_FIXED_ELEMENT` | 33 | Sim.act / Sim.cond 不认识 |
| 未做 | `GATE_OPEN` | 33 | Sim.act / Sim.cond 不认识 |
| 未做 | `MAP_REVEAL_PERMANENTLY_IN_TRIGGER` | 33 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_DisguisedEvacuate` | 33 | 只记进时间线，没有效果 |
| 推断 | `STOP_TIMER` | 33 | 引擎模型核心 |
| 未做 | `TEAM_SET_OVERRIDE_RELATION_TO_TEAM` | 33 | Sim.act / Sim.cond 不认识 |
| 推断 | `UNIT_CHANGE_OBJECT_STATUS:NO_ATTACK` | 33 | Sim.act / Sim.cond 有分支 |
| 推断 | `ALLOW_DISALLOW_ONE_UPGRADE` | 32 | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_ATTACK_TEAM` | 32 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_KILL_ALL_IN_AREA` | 32 | Sim.act / Sim.cond 不认识 |
| 未做 | `ATTACK_MOVE_TEAM_TO_NAMED_OBJECT` | 31 | Sim.act / Sim.cond 不认识 |
| 未做 | `CREATE_REINFORCEMENT_TEAM_AT_UNIT_POSITION` | 31 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_AI_SET_FAVORED_ENEMY` | 31 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT` | 30 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:SKIRMISH_AI_DO_NOT_TAKE` | 30 | 状态位 SKIRMISH_AI_DO_NOT_TAKE 只记下来 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleAlliedArtilleryVehicle` | 29 | 只记进时间线，没有效果 |
| 未做 | `PLAYER_ALLOWED_TOBE_COOPAI` | 29 | Sim.act / Sim.cond 不认识 |
| 推断 | `SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER` | 29 | Sim.act / Sim.cond 有分支 |
| 未做 | `DESELECT` | 28 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SOUND_DISABLE_TYPE` | 28 | 纯表现（名字规则） |
| 未做 | `PLAYER_CAMERA_MOVE_TO_NAMED` | 27 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_GARRISON_SPECIFIC_BUILDING` | 27 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_PLAYERS_NEAREST_UNIT_OF_TYPE_TO_REFERENCE` | 27 | Sim.act / Sim.cond 不认识 |
| 推断 | `TEAM_STOP` | 27 | Sim.act / Sim.cond 有分支 |
| 未做 | `TEAM_TELEPORT_TO_WAYPOINT` | 27 | Sim.act / Sim.cond 不认识 |
| 未做 | `MAP_UNDO_REVEAL_PERMANENTLY_IN_TRIGGER` | 26 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `NAMED_FLASH_WHITE` | 26 | 纯表现（名字规则） |
| 不涉及 | `RADAR_CREATE_EVENT` | 26 | 纯表现（名字规则） |
| 未做 | `TEAM_GUARD_AREA_FROM_POSITION` | 26 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_DISABLED` | 26 | Sim.act / Sim.cond 不认识 |
| 未做 | `LINK_MISSION_OBJECTIVE_TO_OBJECT_WITH_CATEGORY` | 25 | Sim.act / Sim.cond 不认识 |
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
| 未做 | `SET_COOP_AI_COMMAND_UI_ENABLED` | 24 | sim.IGNORED 明确丢掉 |
| 未做 | `LINK_MISSION_OBJECTIVE_TO_WAYPOINT_WITH_CATEGORY` | 23 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_GRANT_SPECIAL_POWER` | 23 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_TRANSFER_OWNERSHIP_PLAYER` | 23 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE` | 23 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `HIDE_TUTORIAL_TEXT` | 22 | 纯表现（名字规则） |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NO_ATTACK_FROM_AI` | 22 | 状态位 NO_ATTACK_FROM_AI 只记下来 |
| 未做 | `MOVE_NAMED_UNIT_TO_UNIT` | 21 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_LOGIC_COMMAND_ABILITY_ON_NAMED_POSITION` | 21 | Sim.act / Sim.cond 不认识 |
| 未做 | `SELECT_OBJECT` | 21 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_FOLLOW_WAYPOINTS_EXACT` | 21 | Sim.act / Sim.cond 不认识 |
| 推断 | `MOVE_CAMERA_TO_NAMED` | 20 | Sim.act / Sim.cond 有分支 |
| 未做 | `REDALERT_DISABLE_THREAT_LEVEL_BONUS` | 20 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_EXECUTE_SEQUENTIAL_SCRIPT_COPY` | 20 | Sim.act / Sim.cond 不认识 |
| 推断 | `CAMERA_FOLLOW_NAMED` | 19 | Sim.act / Sim.cond 有分支 |
| 推断 | `COUNTER_MATH_COUNTER` | 19 | 引擎模型核心 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_SmokeBombSpecialPower` | 19 | 只记进时间线，没有效果 |
| 未做 | `PLAYER_DISABLE_BASE_CONSTRUCTION` | 16 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_ENABLE_UNIT_CONSTRUCTION` | 16 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PLAY_SOUND_EFFECT_AT_TEAM` | 16 | 纯表现（名字规则） |
| 未做 | `TOGGLE_LOCK_CURRENT_SELECTION` | 16 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_SET_MODELCONDITION_FOR_DURATION` | 16 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_STOP_SEQUENTIAL_SCRIPT` | 16 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_EXIT_BUILDING` | 15 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_UPGRADE` | 15 | Sim.act / Sim.cond 不认识 |
| 推断 | `UNIT_SET_HEALTH` | 15 | Sim.act / Sim.cond 有分支 |
| 推断 | `GIVE_PLAYER_UPGRADE` | 14 | Sim.act / Sim.cond 有分支 |
| 推断 | `MARK_MISSION_OBJECTIVE_COMPLETED` | 14 | 引擎模型核心 |
| 不涉及 | `MOVIE_PLAY_FULLSCREEN` | 14 | 纯表现（名字规则） |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleEnergizedArmorSpecialPower` | 14 | 只记进时间线，没有效果 |
| 未做 | `PLAYER_KILL` | 14 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_SET_ALL_UNITS_TO_FLEE` | 14 | Sim.act / Sim.cond 不认识 |
| 未做 | `SET_REFERENCE_TO_FIRST_TEAM_MEMBER_IN_AREA` | 14 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES` | 14 | sim.IGNORED 明确丢掉 |
| 未做 | `UNIT_EXECUTE_SEQUENTIAL_SCRIPT_LOOPING` | 14 | Sim.act / Sim.cond 不认识 |
| 未做 | `DISABLE_MOUSE_HUD_FIXED_ELEMENT` | 13 | Sim.act / Sim.cond 不认识 |
| 未做 | `SET_LAST_CREATED_UNIT_TO_REFERENCE` | 13 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_EXIT_ALL_BUILDINGS` | 13 | Sim.act / Sim.cond 不认识 |
| 未做 | `GATE_CLOSE` | 12 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_GARRISON_NEAREST_BUILDING` | 12 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_SET_SPECIAL_POWER_COUNTDOWN` | 12 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleAfterburners` | 12 | 只记进时间线，没有效果 |
| 未做 | `OPTIONS_SET_OCCLUSION_MODE` | 12 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_SELL_EVERYTHING` | 12 | Sim.act / Sim.cond 不认识 |
| 推断 | `SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER` | 12 | Sim.act / Sim.cond 有分支 |
| 未做 | `TEAM_GARRISON_NEAREST_BUILDING` | 12 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_MOVE_TO_NEAREST_OBJECT_OF_KINDOF_OWNED_BY_PLAYER` | 12 | Sim.act / Sim.cond 不认识 |
| 未做 | `DISABLE_JOYPAD_COMMANDBAR_BUTTON` | 11 | Sim.act / Sim.cond 不认识 |
| 未做 | `FLASH_JOYPAD_COMMANDBAR_BUTTON` | 11 | Sim.act / Sim.cond 不认识 |
| 未做 | `FLASH_JOYPAD_HUD_FIXED_ELEMENT` | 11 | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_REMOVE_UPGRADE` | 11 | Sim.act / Sim.cond 有分支 |
| 未做 | `ORE_NODE_SET_MAX_GATHER_VALUE` | 11 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_ENABLE_BASE_CONSTRUCTION` | 10 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `ROTATE_CAMERA` | 10 | 纯表现（名字规则） |
| 未做 | `SKIRMISH_AI_CONSIDER_ALL_ENEMIES_WHEN_BUILDING` | 10 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `ZOOM_CAMERA` | 10 | 纯表现（名字规则） |
| 未做 | `MAP_SHROUD_SET_RESHROUD_TIME` | 9 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleHarpoonSpecialPower` | 9 | 只记进时间线，没有效果 |
| 未做 | `PLAYER_DISABLE_UNIT_CONSTRUCTION` | 9 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_TOGGLE_SKIRMISH_AI` | 9 | Sim.act / Sim.cond 不认识 |
| 未做 | `SET_COUNTER_TO_NUMBER_OBJECTS_PLAYER_OWNS_WITH_KINDOF` | 9 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_AI_START` | 9 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SOUND_ENABLE_TYPE` | 9 | 纯表现（名字规则） |
| 推断 | `SUB_FROM_MSEC_TIMER` | 9 | 引擎模型核心 |
| 推断 | `TEAM_GUARD_AREA` | 9 | Sim.act / Sim.cond 有分支 |
| 未做 | `TEAM_IDLE_FOR_FRAMECOUNT` | 9 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE_OWNED_BY_PLAYER` | 9 | Sim.act / Sim.cond 不认识 |
| 推断 | `COUNTER_MATH_VALUE` | 8 | 引擎模型核心 |
| 未做 | `EXIT_SPECIFIC_BUILDING` | 8 | Sim.act / Sim.cond 不认识 |
| 未做 | `FLASH_UI_PLAYER_POWER_BUTTON` | 8 | Sim.act / Sim.cond 不认识 |
| 推断 | `MAP_REVEAL_AT_WAYPOINT` | 8 | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_CivilianStructureEvacuate` | 8 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleAlliedEngineerHeal` | 8 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_UnPackJapanBaseDefenseEgg` | 8 | 只记进时间线，没有效果 |
| 推断 | `RESTART_TIMER` | 8 | 引擎模型核心 |
| 推断 | `SET_COUNTER_TO_COUNTER` | 8 | 引擎模型核心 |
| 未做 | `SET_PLAYER_KILLS_OF_TYPE_TO_COUNTER` | 8 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `CAMERA_STOP_FOLLOW` | 7 | 纯表现（名字规则） |
| 未做 | `FIRE_SPECIAL_POWER_ON_UNIT` | 7 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_FACE_NAMED` | 7 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateRoarSpecialPower` | 7 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JAAS_Transform` | 7 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleMirageField` | 7 | 只记进时间线，没有效果 |
| 不涉及 | `PATH_MUSIC_ENABLE_DYNAMIC_SYSTEM` | 7 | 纯表现（名字规则） |
| 未做 | `TEAM_DELETE_LIVING` | 7 | Sim.act / Sim.cond 不认识 |
| 推断 | `UNIT_CHANGE_OBJECT_STATUS:NON_AUTOACQUIRABLE` | 7 | Sim.act / Sim.cond 有分支 |
| 推断 | `UNIT_CHANGE_OBJECT_STATUS:UNATTACKABLE` | 7 | Sim.act / Sim.cond 有分支 |
| 未做 | `ATTACK_MOVE_TEAM_TO_NEAREST_OBJECT_OF_TYPE_OF_PLAYER` | 6 | Sim.act / Sim.cond 不认识 |
| 未做 | `DISABLE_COUNTDOWN_TIMER_DISPLAY` | 6 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_FACE_WAYPOINT` | 6 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleBinaryWeapon` | 6 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_ActivateRoarSpecialPower` | 6 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_TriggerRushAttackSpecialPower` | 6 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_FIRE_MULTI_TARGET_SPECIAL_POWER_AT_WAYPOINTS` | 6 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_LOAD_TRANSPORTS` | 6 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_ENABLE_HOUSE_COLOR` | 6 | Sim.act / Sim.cond 不认识 |
| 未做 | `BORDER_SHROUD_SET_OPACITY` | 5 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `CAMERA_STOP_TETHER_NAMED` | 5 | 纯表现（名字规则） |
| 未做 | `FIRE_SPECIAL_POWER_ON_NEAREST_OBJECTTYPE_BY_PLAYER` | 5 | Sim.act / Sim.cond 不认识 |
| 未做 | `FIRE_SPECIAL_POWER_ON_TEAM` | 5 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `HIDE_UI` | 5 | 纯表现（名字规则） |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleDeployWeapon` | 5 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleRiotShieldSpecialPower` | 5 | 只记进时间线，没有效果 |
| 未做 | `TEAM_SET_HEALTH` | 5 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_MODELCONDITION_FOR_DURATION` | 5 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_SLEEP_STATUS` | 5 | Sim.act / Sim.cond 不认识 |
| 未做 | `ENABLE_COUNTDOWN_TIMER_DISPLAY` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_ATTACK_AREA` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructJapanMinerFromRefinery` | 4 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ConstructSovietAntiVehicleVehicleTech2` | 4 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleJapanFortressShipTransformMode` | 4 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleMagneticArmor` | 4 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleShortCircuit` | 4 | 只记进时间线，没有效果 |
| 未做 | `PLAYER_AI_CHANGEUNITBUILDER` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_SET_DISABLED` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `SET_BLOOM_INTENSITY` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER_INCLUDE_DEAD` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `SET_TEXTURE_LOOKUP_TABLE` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_AI_CLEAR_ALL_ENEMY_PLAYERS_PRIORITIES` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_FIRE_SPECIAL_POWER_AT_MOST_COST` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_CONTEXT_SENSITIVE_ATTACK` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ENABLE_HOUSE_COLOR` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_EXECUTE_SEQUENTIAL_SCRIPT` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_ATTACK_MOVE_TOWARDS_NEAREST_OBJECT_TYPE` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NO_COLLISIONS` | 4 | 状态位 NO_COLLISIONS 只记下来 |
| 推断 | `UNIT_GUARD_AREA` | 4 | Sim.act / Sim.cond 有分支 |
| 未做 | `UNIT_GUARD_OBJECT` | 4 | Sim.act / Sim.cond 不认识 |
| 推断 | `MAP_REVEAL_ALL` | 3 | Sim.act / Sim.cond 有分支 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JapanAntiInfantryInfantryBonzai` | 3 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleShieldSphere` | 3 | 只记进时间线，没有效果 |
| 不涉及 | `PATH_MUSIC_FADE_IN_MUSIC` | 3 | 纯表现（名字规则） |
| 不涉及 | `RESET_CAMERA_AT_OBJECT` | 3 | 纯表现（名字规则） |
| 未做 | `SKIRMISH_AI_CLEAR_ENEMY_PLAYER_PRIORITY` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ATTACK_MOVE_TOWARDS_NEAREST_OBJECT_TYPE` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ENTER_NAMED` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_FLASH_WHITE` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_GUARD_OBJECT` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_MODELCONDITION` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_STOP_SEQUENTIAL_SCRIPT` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NEXT_MOVE_IS_REVERSE` | 3 | 状态位 NEXT_MOVE_IS_REVERSE 只记下来 |
| 推断 | `ADD_TO_MSEC_TIMER` | 2 | 引擎模型核心 |
| 未做 | `AUDIO_FADE_VOLUME` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `AUDIO_POP_MUSIC` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `AUDIO_SET_SOUNDEFFECTS_SLIDER_FADEABLE` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `DISABLE_BORDER_SHROUD` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `DISABLE_UI_UNIT_ABILITY_BUTTON` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT:specialpowercampalliedbomberdrop2` | 2 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateDisguiseSpecialPower` | 2 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_AlliedAntiInfantryVehicleEvacuate` | 2 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JASV_FireKiCannon` | 2 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY:Command_JapanEngineerSprint` | 2 | 只记进时间线，没有效果 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_ActivateDisguiseSpecialPower` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_AlliedSupportAircraftShrinkRay` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_CaptureBuilding` | 2 | 只记进时间线，没有效果 |
| 未做 | `OVERRIDE_GLOBAL_TERRAIN_HEIGHT` | 2 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PATH_MUSIC_FADE_OUT_MUSIC` | 2 | 纯表现（名字规则） |
| 不涉及 | `PATH_MUSIC_STOP_MUSIC` | 2 | 纯表现（名字规则） |
| 未做 | `PLAYER_CAMERA_TETHER_NAMED` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_DISABLE_FACTORIES` | 2 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SCREEN_SHAKE` | 2 | 纯表现（名字规则） |
| 推断 | `SET_PLAYER_MONEY_TO_COUNTER` | 2 | Sim.act / Sim.cond 有分支 |
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
| 未做 | `MOVE_TEAM_TO_UNIT` | 1 | Sim.act / Sim.cond 不认识 |
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
| 未做 | `NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_ActivateLaserGlaiveBlastSpecialPower` | 1 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `PATH_MUSIC_ENABLE_RESUME_SYSTEM` | 1 | 纯表现（名字规则） |
| 不涉及 | `PITCH_CAMERA` | 1 | 纯表现（名字规则） |
| 未做 | `PLAYER_AI_CHANGEBASEBUILDER` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_AI_CHANGESCIENCEUPGRADER` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_AI_CHANGETEAMBUILDER` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_AI_CHANGE_ECONOMY_MANAGER` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_EXIT_ALL_BUILDINGS` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_UNIT_TYPE_SPECIAL_POWER_IGNORE_REQUIREMENTS` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `RESUME_BACKGROUND_SOUNDS` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_AI_DONT_CONSIDER_ENEMY_WHEN_BUILDING` | 1 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `SOUND_AMBIENT_PAUSE` | 1 | 纯表现（名字规则） |
| 不涉及 | `SOUND_AMBIENT_RESUME` | 1 | 纯表现（名字规则） |
| 不涉及 | `SOUND_ENABLE_ALL` | 1 | 纯表现（名字规则） |
| 未做 | `SUSPEND_BACKGROUND_SOUNDS` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_CLEAR_MODELCONDITION` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_FACE_NAMED` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_REMOVE_ALL_OVERRIDE_RELATIONS` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_SET_EXPERIENCE_POINTS` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `TOGGLE_SHADER_OVERRIDE` | 1 | Sim.act / Sim.cond 不认识 |
| 不涉及 | `UNFREEZE_TIME` | 1 | 纯表现（名字规则） |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:CAN_ATTACK` | 1 | 状态位 CAN_ATTACK 只记下来 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:NO_BRIBE` | 1 | 状态位 NO_BRIBE 只记下来 |
| 未做 | `UNIT_CHANGE_OBJECT_STATUS:UNDER_FROZEN` | 1 | 状态位 UNDER_FROZEN 只记下来 |
| 未做 | `UNIT_GIVE_EXPERIENCE_POINTS` | 1 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_GUARD_AREA_FROM_POSITION` | 1 | Sim.act / Sim.cond 不认识 |

## 脚本条件

| 状态 | 名字 | 用量 | 说明 |
|---|---|---|---|
| 推断 | `FLAG` | 5099 | 引擎模型核心 |
| 推断 | `TIMER_EXPIRED` | 3917 | 引擎模型核心 |
| 推断 | `CONDITION_TRUE` | 2947 | 引擎模型核心 |
| 推断 | `NAMED_DESTROYED` | 922 | Sim.act / Sim.cond 有分支 |
| 推断 | `PLAYER_HAS_OBJECT_COMPARISON` | 628 | Sim.act / Sim.cond 有分支 |
| 推断 | `COUNTER` | 577 | 引擎模型核心 |
| 未做 | `HAS_FINISHED_AUDIO` | 495 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_IS_HUMAN_OR_AI_PERSONALITY` | 470 | Sim.act / Sim.cond 不认识 |
| 未做 | `HAS_FINISHED_VIDEO` | 422 | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_INSIDE_AREA` | 413 | Sim.act / Sim.cond 有分支 |
| 推断 | `SKIRMISH_PLAYER_HAS_UNITS_IN_AREA` | 410 | Sim.act / Sim.cond 有分支 |
| 推断 | `NAMED_OWNED_BY_PLAYER` | 397 | Sim.act / Sim.cond 有分支 |
| 推断 | `NAMED_NOT_DESTROYED` | 374 | Sim.act / Sim.cond 有分支 |
| 推断 | `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA` | 278 | Sim.act / Sim.cond 有分支 |
| 推断 | `NAMED_ATTACKED_BY_PLAYER` | 150 | Sim.act / Sim.cond 有分支 |
| 未做 | `UNIT_HAS_OBJECT_STATUS` | 142 | Sim.act / Sim.cond 不认识 |
| 推断 | `COUNTER_SECONDS` | 141 | 引擎模型核心 |
| 推断 | `UNIT_HEALTH` | 134 | Sim.act / Sim.cond 有分支 |
| 未做 | `MISSION_HOT_SPOT_ACTIVE` | 110 | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_DISCOVERED` | 104 | Sim.act / Sim.cond 有分支 |
| 未做 | `TEAM_ATTACKED_BY_PLAYER` | 93 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_HAS_MODELCONDITION` | 88 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_INSIDE_AREA_PARTIALLY` | 80 | Sim.act / Sim.cond 不认识 |
| 未做 | `ENEMY_SIGHTED_BY_TEAM` | 69 | Sim.act / Sim.cond 不认识 |
| 未做 | `IS_OBJECT_OF_TYPE` | 69 | Sim.act / Sim.cond 不认识 |
| 推断 | `CAMERA_ENTERED_AREA` | 60 | Sim.act / Sim.cond 有分支 |
| 未做 | `ENEMY_SIGHTED` | 59 | Sim.act / Sim.cond 不认识 |
| 推断 | `COUNTER_COUNTER` | 55 | 引擎模型核心 |
| 未做 | `NAMED_SELECTED` | 50 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_DISCOVERED` | 47 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER` | 44 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_HAS_UNITS` | 39 | Sim.act / Sim.cond 不认识 |
| 推断 | `NAMED_OUTSIDE_AREA` | 38 | Sim.act / Sim.cond 有分支 |
| 未做 | `TYPE_SELECTED` | 38 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_DESTROYED` | 35 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_INSIDE_AREA_ENTIRELY` | 33 | Sim.act / Sim.cond 不认识 |
| 未做 | `DISTANCE_BETWEEN_TEAM` | 32 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_KILLED_TYPE_UNITS` | 29 | Sim.act / Sim.cond 不认识 |
| 推断 | `PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA` | 28 | Sim.act / Sim.cond 有分支 |
| 未做 | `PLAYER_HAS_PLAYER_TECH` | 26 | Sim.act / Sim.cond 不认识 |
| 未做 | `DISTANCE_BETWEEN_OBJ` | 25 | Sim.act / Sim.cond 不认识 |
| 未做 | `CURRENT_PLATFORM` | 24 | Sim.act / Sim.cond 不认识 |
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
| 未做 | `OBJECT_IS_DISGUISED_AS_TYPE` | 10 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_COMPARISON_POWER_POINTS` | 10 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_ATTACKED_BY_OBJECTTYPE` | 10 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_COMPARE_NUM_MEMBERS` | 10 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA_WITH_MODELCONDITION` | 9 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_POWER` | 9 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_TRIGGERED_SPECIAL_POWER` | 9 | Sim.act / Sim.cond 不认识 |
| 未做 | `BUILT_BY_PLAYER` | 8 | Sim.act / Sim.cond 不认识 |
| 未做 | `GATE_IS_OPEN` | 8 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_DESTROYED_N_BUILDINGS_PLAYER` | 8 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_CREDITS` | 8 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED` | 8 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_EXITED_AREA` | 7 | Sim.act / Sim.cond 不认识 |
| 未做 | `UNIT_SPECIAL_POWER_READY` | 7 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_NO_POWER` | 6 | Sim.act / Sim.cond 不认识 |
| 推断 | `PLAYER_EXCESS_POWER_COMPARE_VALUE` | 5 | Sim.act / Sim.cond 有分支 |
| 未做 | `PLAYER_TRIGGERED_SPECIAL_POWER_FROM_NAMED` | 5 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_TRIGGERED_SPECIAL_POWER_IN_AREA` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `TEAM_CAN_PATH_TO_WAYPOINT` | 4 | Sim.act / Sim.cond 不认识 |
| 未做 | `PLAYER_HAS_COMPARISON_UNIT_KIND` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `SKIRMISH_COMMAND_BUTTON_READY_PARTIAL` | 3 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_DESTROYED_BY_OBJECTTYPE` | 2 | Sim.act / Sim.cond 不认识 |
| 未做 | `NAMED_DYING` | 2 | Sim.act / Sim.cond 不认识 |
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
| 未做 | `Body/PropBody` | 1443 (2758) | 模拟器代码里没有这个名字；例：AlliedAirField_Collapse, AlliedAntiAirShip_Collapse |
| 不涉及 | `Behaviors/FXListBehavior` | 796 (1241) | 纯表现（名字规则）；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 推断 | `Body/ActiveBody` | 790 (1398) | simunits.stats 读 MaxHealth（只有生命值；受伤状态、回血等另算）；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 未做 | `Behaviors/ObjectDefectionHelper` | 640 (1059) | 模拟器代码里没有这个名字；例：AlliedSatelliteSweepShroudRevealer, AlliedTimeBombLvl1 |
| 未做 | `Behaviors/ObjectSMCHelper` | 640 (1059) | 模拟器代码里没有这个名字；例：AlliedSatelliteSweepShroudRevealer, AlliedTimeBombLvl1 |
| 未做 | `Behaviors/AttributeModifierPoolUpdate` | 622 (910) | 模拟器代码里没有这个名字；例：AlliedAntiVehicleVehicleTech3CannonNodeBase, AlliedAntiVehicleVehicleTech3CannonNodeEnd |
| 未做 | `Behaviors/SecondaryDamageTracker` | 617 (852) | 模拟器代码里没有这个名字；例：AlliedSatelliteSweepShroudRevealer, AlliedTimeBombLvl1 |
| 未做 | `Behaviors/Physics` | 597 (836) | 模拟器代码里没有这个名字；例：AlliedAntiGroundAircraft_Dying, AlliedBomberAircraft_Dying |
| 推断 | `Behaviors/CreateObjectDie` | 591 (838) | 模拟器代码里有这个名字；例：AlliedAntiGroundAircraft_Dying, AlliedBomberAircraft_Dying |
| 未做 | `Behaviors/DestroyDie` | 578 (1006) | 模拟器代码里没有这个名字；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 未做 | `Behaviors/SquishCollide` | 569 (749) | 模拟器代码里没有这个名字；例：AlliedSatelliteSweepShroudRevealer, AlliedWallPiece |
| 未做 | `Behaviors/SlowDeath` | 565 (1480) | 模拟器代码里没有这个名字；例：AlliedAirField_Collapse, AlliedAntiAirShip_Collapse |
| 未做 | `Behaviors/BuildingDestructionBehavior` | 493 (650) | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 不涉及 | `ClientBehaviors/ModelConditionAudioLoopClientBehavior` | 466 (649) | 纯表现（ClientBehaviors）；例：AlliedSatelliteSweepShroudRevealer, AlliedAirfield |
| 推断 | `Behaviors/ProductionUpdate` | 351 (465) | 模拟器代码里有这个名字；例：AlliedAirfield, AlliedBarracks |
| 未做 | `Behaviors/ToppleUpdate` | 347 (410) | 模拟器代码里没有这个名字；例：BaseTopple, BaseTree |
| 未做 | `Behaviors/ModelConditionUpgrade` | 341 (465) | 模拟器代码里没有这个名字；例：AlliedAntiInfantryInfantry, AlliedAntiVehicleInfantry |
| 未做 | `Behaviors/BuildingBehavior` | 334 (440) | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 推断 | `Behaviors/AttributeModifierAuraUpdate` | 311 (420) | 模拟器代码里有这个名字；例：A09_IronCurtainEffect, BaseCivilianStructure |
| 未做 | `Behaviors/InvisibilityBehavior` | 305 (412) | 模拟器代码里没有这个名字；例：BaseCivilianStructure, BaseCivilianStructureLarge |
| 未做 | `Behaviors/ContestableGarrisonContain` | 305 (411) | 模拟器代码里没有这个名字；例：BaseCivilianStructure, BaseCivilianStructureLarge |
| 不涉及 | `Draws/PropDraw` | 221 (301) | 纯表现（Draws）；例：AM_Trash01, AM_Debris01 |
| 推断 | `Behaviors/FireWeaponWhenDead` | 146 (230) | 模拟器代码里有这个名字；例：AlliedAntiGroundAircraft_Dying, AlliedAntiStructureVehicleCannonEffect |
| 不涉及 | `ClientBehaviors/ModelConditionSoundSelectorClientBehavior` | 140 (195) | 纯表现（ClientBehaviors）；例：AlliedSatelliteSweepShroudRevealer, AlliedAirfield |
| 不涉及 | `Draws/DynamicsDraw` | 138 (857) | 纯表现（Draws）；例：AlliedAirField_Collapse, AlliedAntiAirShip_Collapse |
| 未做 | `Behaviors/EnableDynamicsCollide` | 137 (154) | 模拟器代码里没有这个名字；例：BaseSimulatedProp, AM_Boat01 |
| 推断 | `AI/AIUpdate` | 136 (237) | Sim.fight / 移动（单位 AI 的状态机细项按引擎 B 的 AI 清单推进）；例：AlliedSatelliteSweepShroudRevealer, AlliedSuperWeaponEffect |
| 未做 | `Behaviors/DynamicsUpdate` | 113 (154) | 模拟器代码里没有这个名字；例：AlliedDynamicsImpact, AlliedSatelliteSweepShroudRevealer |
| 未做 | `Behaviors/StancesBehavior` | 108 (148) | 模拟器代码里没有这个名字；例：AlliedSatelliteSweepShroudRevealer, AlliedAirfield |
| 未做 | `Body/ImmortalBody` | 91 (111) | 模拟器代码里没有这个名字；例：BaseRock, CPDummyTarget |
| 未做 | `Behaviors/LevelUpUpgrade` | 88 (124) | 模拟器代码里没有这个名字；例：AlliedSatelliteSweepShroudRevealer, AlliedAntiAirShip |
| 未做 | `Behaviors/AutoHealBehavior` | 88 (123) | 模拟器代码里没有这个名字；例：AlliedSatelliteSweepShroudRevealer, AlliedAntiAirShip |
| 未做 | `Behaviors/RunOffMapBehavior` | 88 (123) | 模拟器代码里没有这个名字；例：AlliedSatelliteSweepShroudRevealer, AlliedAntiAirShip |
| 推断 | `Behaviors/WeaponSetUpdate` | 82 (110) | 模拟器代码里有这个名字；例：AlliedBaseDefense, AlliedBaseDefenseAdvanced |
| 推断 | `Behaviors/SpecialPower` | 74 (95) | 模拟器代码里有这个名字；例：AlliedConstructionYard, AlliedAntiAirShip |
| 未做 | `Behaviors/EngineerContain` | 70 (105) | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 未做 | `Behaviors/RepairUpdate` | 66 (91) | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 推断 | `Behaviors/StatusBitsUpgrade` | 66 (85) | 模拟器代码里有这个名字；例：AlliedBaseDefense, AlliedAntiAirShip |
| 推断 | `Behaviors/StructureUnpackUpdate` | 59 (96) | 模拟器代码里有这个名字；例：AlliedAirfield, AlliedBarracks |
| 未做 | `Behaviors/StructureSellUpdate` | 52 (72) | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 不涉及 | `ClientBehaviors/AnimationSoundClientBehavior` | 48 (67) | 纯表现（ClientBehaviors）；例：AlliedTimeBombLvl3, AlliedRefinery |
| 不涉及 | `Draws/TruckDraw` | 35 (51) | 纯表现（Draws）；例：AlliedTimeBombLvl1, AlliedTimeBombLvl2 |
| 未做 | `Behaviors/InfiltratorContain` | 34 (38) | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 未做 | `Behaviors/LUAEventList` | 32 (44) | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 未做 | `Behaviors/ToggleStatusSpecialAbilityUpdate` | 27 (34) | 模拟器代码里没有这个名字；例：AlliedAntiAirShip, AlliedAntiInfantryInfantry |
| 未做 | `Behaviors/SubObjectsUpgrade` | 26 (30) | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 未做 | `Behaviors/FreefallUpdate` | 24 (31) | 模拟器代码里没有这个名字；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 推断 | `Behaviors/AttributeModifierUpgrade` | 22 (30) | 模拟器代码里有这个名字；例：AlliedOutpost, AlliedAntiGroundAircraft |
| 未做 | `Behaviors/CrushDie` | 22 (28) | 模拟器代码里没有这个名字；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 未做 | `Behaviors/SuppressionUpdate` | 22 (28) | 模拟器代码里没有这个名字；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 不涉及 | `Draws/LaserDraw` | 21 (37) | 纯表现（Draws）；例：AlliedAntiVehicleVehicleTech3CannonNodeBase, AlliedAntiVehicleVehicleTech3CannonNodeEnd |
| 未做 | `Behaviors/LaserState` | 19 (25) | 模拟器代码里没有这个名字；例：AlliedBaseDefense, AlliedBaseDefenseAdvanced |
| 未做 | `Behaviors/QueueProductionExitUpdate` | 19 (20) | 模拟器代码里没有这个名字；例：AlliedBarracks, AlliedConstructionYard |
| 未做 | `Behaviors/ReplaceSelfSpecialAbility` | 18 (24) | 模拟器代码里没有这个名字；例：AlliedConstructionYard, AlliedMCV |
| 不涉及 | `Draws/TracerModelDraw` | 18 (22) | 纯表现（Draws）；例：AlliedAntiAirShip, AlliedAntiAirVehicleTech1 |
| 未做 | `Behaviors/WeaponFireSpecialAbilityUpdate` | 16 (23) | 模拟器代码里没有这个名字；例：AlliedSuperWeaponAdvanced, AlliedAntiNavalScout |
| 未做 | `Body/ManagerBody` | 14 (32) | 模拟器代码里没有这个名字；例：BaseBridge, BaseCivilianBridge |
| 未做 | `Behaviors/BridgeBuilder` | 14 (30) | 模拟器代码里没有这个名字；例：AM_Bridge_01, AM_Bridge_01a |
| 未做 | `AI/JetAIUpdate` | 13 (17) | 模拟器代码里没有这个名字；例：AlliedAntiGroundAircraft, AlliedAttackDrone |
| 未做 | `Behaviors/TransportContain` | 13 (16) | 模拟器代码里没有这个名字；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryVehicle |
| 未做 | `Behaviors/SpawnBehavior` | 10 (16) | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedConstructionYardRepairBay |
| 未做 | `Behaviors/ProductionUpdateInfo` | 9 (9) | 模拟器代码里没有这个名字；例：AlliedConstructionYard, AlliedMCV |
| 未做 | `Behaviors/EjectPassengersSpecialAbilityUpdate` | 7 (8) | 模拟器代码里没有这个名字；例：AlliedBomberAircraft, A08_CenturyTransportAircraft |
| 未做 | `Behaviors/BezierProjectile` | 6 (78) | 模拟器代码里没有这个名字；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
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
| 未做 | `Behaviors/AttachUpdate` | 3 (24) | 模拟器代码里没有这个名字；例：ChronoTargetMarker, AlliedAirfieldRepairDrone |
| 未做 | `Behaviors/StealthDetectorUpdate` | 3 (8) | 模拟器代码里没有这个名字；例：AlliedScoutInfantry, A08_Dog1 |
| 未做 | `Behaviors/SlaughterHordeContain` | 3 (6) | 模拟器代码里没有这个名字；例：AlliedAntiStructureShip, S08_AlliedAntiStructureShip |
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
| 未做 | `Behaviors/InvisibilityBroadcastUpdate` | 2 (2) | 模拟器代码里没有这个名字；例：AlliedAntiVehicleVehicleTech3, A08_SpecialMirageTank |
| 未做 | `Behaviors/NotifyWhenAttackingBehavior` | 2 (2) | 模拟器代码里没有这个名字；例：AlliedBaseDefenseAdvanced, SovietBaseDefenseAdvanced |
| 未做 | `Behaviors/PowerUpgrade` | 2 (2) | 模拟器代码里没有这个名字；例：SovietPowerPlantAdvanced, SovietPowerPlant |
| 未做 | `Behaviors/PrematureDischargeSpecialPower` | 2 (2) | 模拟器代码里没有这个名字；例：JapanBaseDefenseAdvanced, JapanAntiStructureVehicle |
| 未做 | `Behaviors/RecallUnitsSpecialPower` | 2 (2) | 模拟器代码里没有这个名字；例：AlliedAirfield, SovietAirfield |
| 未做 | `Behaviors/SpiderHoleUpdate` | 2 (2) | 模拟器代码里没有这个名字；例：JapanAntiVehicleInfantry, JapanAntiVehicleInfantry_Ambush |
| 推断 | `Behaviors/TechUpgrade` | 2 (2) | 模拟器代码里有这个名字；例：AlliedConstructionYard, AlliedOutpost |
| 推断 | `Behaviors/LifetimeUpdate` | 1 (855) | 模拟器代码里有这个名字；例：AlliedAirField_Collapse, AlliedAntiAirShip_Collapse |
| 未做 | `Behaviors/FireWeaponUpdate` | 1 (21) | 模拟器代码里没有这个名字；例：AlliedAntiStructureVehicleCannonEffect, AlliedAntiStructureVehicleCannonEffect_Vet |
| 未做 | `Behaviors/OreNodeBehavior` | 1 (8) | 模拟器代码里没有这个名字；例：BaseOreNode, OreNode |
| 未做 | `Behaviors/AssistedPlacementInfoBehavior` | 1 (7) | 模拟器代码里没有这个名字；例：OreNode, OreNode2a |
| 未做 | `Behaviors/OreMinerBehavior` | 1 (7) | 模拟器代码里没有这个名字；例：AlliedMiner, AlliedMiner_Naval |
| 未做 | `Behaviors/FireWeaponCollide` | 1 (4) | 模拟器代码里没有这个名字；例：SovietAntiVehicleInfantry, JapanAntiVehicleShipTorpedoSpreadProjectile |
| 未做 | `Behaviors/StrafeAreaUpdate` | 1 (3) | 模拟器代码里没有这个名字；例：AlliedSatelliteSweepShroudRevealer, JapanFinalSquadronAircraft |
| 不涉及 | `Behaviors/AudioLoopUpgrade` | 1 (2) | 纯表现（名字规则）；例：SovietAntiVehicleVehicleTech1, Tutorial_SovietTech1Tank |
| 未做 | `Behaviors/GarrisonContain` | 1 (2) | 模拟器代码里没有这个名字；例：AlliedBaseDefense, SovietBunker |
| 未做 | `Behaviors/MoneyCrateCollide` | 1 (2) | 模拟器代码里没有这个名字；例：MoneyCrate, MoneyCrateMP |
| 未做 | `Behaviors/MonitorConditionUpdate` | 1 (2) | 模拟器代码里没有这个名字；例：JapanMiner, JapanMiner_Naval |
| 未做 | `Behaviors/OCLMonitorUpdate` | 1 (2) | 模拟器代码里没有这个名字；例：SovietCommandoTech1, Soviet_BombingRun |
| 未做 | `Behaviors/ObjectCreationUpgrade` | 1 (2) | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech1, Tutorial_SovietTech1Tank |
| 未做 | `Behaviors/SlaveWatcherBehavior` | 1 (2) | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech1, Tutorial_SovietTech1Tank |
| 未做 | `Behaviors/StoreObjectsSpecialPower` | 1 (2) | 模拟器代码里没有这个名字；例：AlliedSuperWeapon, PlayerSpellBook |
| 未做 | `Behaviors/SwitchLocomotorUpdate` | 1 (2) | 模拟器代码里没有这个名字；例：SovietBomberAircraft, SovietBomberAircraft_Special |
| 未做 | `Behaviors/TeleportStoredObjectsSpecialPower` | 1 (2) | 模拟器代码里没有这个名字；例：AlliedSuperWeapon, PlayerSpellBook |
| 未做 | `Behaviors/TeleportStoredObjectsUpdate` | 1 (2) | 模拟器代码里没有这个名字；例：AlliedSuperWeapon, PlayerSpellBook |
| 未做 | `Behaviors/VeterancyCrateCollide` | 1 (2) | 模拟器代码里没有这个名字；例：VeterancyCrate, VeterancyCrateMP |
| 未做 | `Behaviors/ActivateSpecialPowerOnCreate` | 1 (1) | 模拟器代码里没有这个名字；例：JapanAntiVehicleInfantry_Ambush |
| 推断 | `Behaviors/AssembleStructureSpecialAbilityUpdate` | 1 (1) | 模拟器代码里有这个名字；例：SovietEngineer |
| 未做 | `Behaviors/ChargeWeaponUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：JapanBaseDefenseAdvanced |
| 未做 | `Behaviors/CircularDamageUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：SovietAntiNavyShipTech1 |
| 未做 | `Behaviors/DieOnProducerDeathUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：AlliedAttackDrone |
| 未做 | `Behaviors/DominateEnemySpecialPower` | 1 (1) | 模拟器代码里没有这个名字；例：AlliedInfiltrationInfantry |
| 未做 | `Behaviors/GrapplingHookUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech3 |
| 未做 | `Behaviors/LinearDamageUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：AlliedAntiNavalScout |
| 未做 | `Behaviors/MagneticEffectUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：AlliedAntiNavyShipTech1 |
| 未做 | `Behaviors/ReconstituteStateSpecialAbility` | 1 (1) | 模拟器代码里没有这个名字；例：AlliedCommandoTech1 |
| 未做 | `Behaviors/ShieldSphereUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：AlliedAntiStructureVehicle |
| 未做 | `Behaviors/StoreCurrentStateUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：AlliedCommandoTech1 |
| 未做 | `Behaviors/SweepingLaserState` | 1 (1) | 模拟器代码里没有这个名字；例：SovietScoutVehicle |
| 未做 | `Behaviors/TimedOpacityUpdate` | 1 (1) | 模拟器代码里没有这个名字；例：JapanInfiltrationInfantry |
| 不涉及 | `ClientBehaviors/ModelConditionEvaEventSelectorClientBehavior` | 1 (1) | 纯表现（ClientBehaviors）；例：AlliedInfiltrationInfantry |
| 不涉及 | `ClientBehaviors/UpgradeSoundSelectorClientBehavior` | 1 (1) | 纯表现（ClientBehaviors）；例：AlliedAntiAirVehicleTech1 |
| 不涉及 | `Draws/TankDraw` | 1 (1) | 纯表现（Draws）；例：SovietAntiVehicleVehicleTech2 |
| 未做 | `Body/ManagedImmortalBody` | 0 (44) | 模拟器代码里没有这个名字；例：BaseIndestructableBridgeSegment, BaseBridgeEnd |
| 未做 | `Body/ManagedActiveBody` | 0 (31) | 模拟器代码里没有这个名字；例：BaseBridgeSegment, AM_Bridge_01_Center |
| 未做 | `Behaviors/ProjectileUpdate` | 0 (18) | 模拟器代码里没有这个名字；例：AlliedAntiVehicleVehicleTech1Projectile, AlliedBomberAircraftBombProjectile |
| 未做 | `Behaviors/LaserScatterUpdate` | 0 (10) | 模拟器代码里没有这个名字；例：AlliedAntiVehicleVehicleTech3CannonNodeBase, AlliedAntiVehicleVehicleTech3CannonNodeEnd |
| 未做 | `Behaviors/SlavedUpdate` | 0 (9) | 模拟器代码里没有这个名字；例：AlliedAirfieldRepairDrone, AlliedAttackDrone_Leeched |
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
| 推断 | `DamageNugget` | 183 | 模拟器代码里有这个名字；例：BaseExplodingPropVehicleWeapon, MountRushmoreHeadEyeWeapon |
| 推断 | `ProjectileNugget` | 88 | 模拟器代码里有这个名字；例：BB_EuropeCoastalGunWeapon, KremlinArtilleryDomeMissle |
| 未做 | `InformTargetNugget` | 69 | 模拟器代码里没有这个名字；例：BB_EuropeCoastalGunWeapon, AlliedPrecisionBomb |
| 未做 | `SuppressionNugget` | 64 | 模拟器代码里没有这个名字；例：BB_EuropeCoastalGunWeapon, KremlinArtilleryDomeMissle |
| 未做 | `MetaImpactNugget` | 36 | 模拟器代码里没有这个名字；例：KremlinArtilleryDomeMissleWarhead, AlliedTimeBomb_Level1 |
| 未做 | `ActivateLaserNugget` | 27 | 模拟器代码里没有这个名字；例：MountRushmoreHeadEyeWeapon, JapanAntiVehicleInfantryTech3LockDownGun |
| 推断 | `WeaponOCLNugget` | 26 | 模拟器代码里有这个名字；例：MountRushmoreHeadEyeWeapon, AlliedPrecisionBombWarhead |
| 未做 | `AttributeModifierNugget` | 20 | 模拟器代码里没有这个名字；例：NanoHiveSwarmEffectTrigger, JapanCommandoSoftLanding |
| 未做 | `ParalyzeNugget` | 11 | 模拟器代码里没有这个名字；例：JapanAntiVehicleInfantryTech3LockDownGun, AlliedAntiStructureShipEMPCruiseMissleWarhead |
| 未做 | `TintObjectsNugget` | 9 | 模拟器代码里没有这个名字；例：SovietCommandoCallBombingRun, AlliedCommandoAttachWeapon |
| 未做 | `ActivateLiftObjectNugget` | 6 | 模拟器代码里没有这个名字；例：JapanCommandoTech1PsyonicCrush, JapanCommandoTech1AirborneKiller |
| 推断 | `LineDamageNugget` | 6 | 模拟器代码里有这个名字；例：SovietCommandoSniperRifle, AAAVT1_SovietCommandoSniperRifle |
| 未做 | `SpecialPowerNugget` | 6 | 模拟器代码里没有这个名字；例：SovietCommandoCallBombingRun, AlliedAntiVehicleVehicleTech1TargetPainter |
| 未做 | `FireOnObjectsNugget` | 5 | 模拟器代码里没有这个名字；例：PlayerPowerJapanEmperorsResolveWeapon_L1, PlayerPowerJapanEmperorsResolveWeapon_L2 |
| 未做 | `SecondaryDamageNugget` | 5 | 模拟器代码里没有这个名字；例：MountRushmoreHeadEyeWeapon, AlliedCryoSatelliteLvl1 |
| 未做 | `AttachNugget` | 4 | 模拟器代码里没有这个名字；例：AlliedCommandoAttachWeapon, SovietAntiVehicleInfantryMagneticBombAttachWeapon |
| 未做 | `StripMaxHealthPercentNugget` | 3 | 模拟器代码里没有这个名字；例：JapanCommandoTech1PsyonicCrush, AAAVT1_JapanCommandoTech1PsyonicCrush |
| 未做 | `ActivateLinearDamageNugget` | 2 | 模拟器代码里没有这个名字；例：AlliedAntiNavalScoutSonar, AlliedAntiNavalScoutSonarForBridges |
| 未做 | `DamageContainedNugget` | 2 | 模拟器代码里没有这个名字；例：SovietAntiInfantryInfantryMolotovCocktailWarhead, Weapon_DesolatorBombFieldUpdate |
| 未做 | `LeechPercentMaxHealthDamageNugget` | 2 | 模拟器代码里没有这个名字；例：SovietCrushWeapon, SovietHarpoonCrushWeapon |
| 未做 | `ReportWeaponFiredStatNugget` | 2 | 模拟器代码里没有这个名字；例：SovietVacuumBomb, ParticleCannonWeapon |
| 未做 | `ActivateCircularDamageNugget` | 1 | 模拟器代码里没有这个名字；例：SovietAntiNavyShipTech1TeslaNova |
| 未做 | `DOTNugget` | 1 | 模拟器代码里没有这个名字；例：PlayerPowerIrradiateTargetWeapon |
| 未做 | `GrapplingHookNugget` | 1 | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech3Harpoon |
| 未做 | `LeechHealthDamageNugget` | 1 | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech1LeechBeamWeapon |
