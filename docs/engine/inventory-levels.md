# 我们 9 关的敌方 AI 用到的清单项

由 `experimental/cnv/inventory_ai.py levels` 生成，**别手改**。范围：9 关（`missions/a1.py`～`a9.py`）里由遭遇战 AI 带的敌人：它的人格（`enemy_ai.py` 生成）沿继承、战略状态、战术、组队、目标启发、微操、造兵 / 预算状态、开局一路引用到的原版 AI 数据项，加上全局常量 AIData 和本阵营的 ArmyDefinition；再加关卡脚本里点了 AI 玩家名字的脚本动作 / 条件。状态取自 [inventory.md](inventory.md)。"AI 做完"的第一条：下表全部已对拍。

**已对拍 113 / 369**（不涉及的不算）。用到敌方 AI 的关：a4、a5、a7。

| 部分 | 已对拍 | 推断 | 未做 |
|---|---|---|---|
| AI | 101 | 122 | 134 |
| 脚本动作 | 11 | 0 | 0 |
| 脚本条件 | 1 | 0 | 0 |

按原版用量加权：已对拍 86%，已有（已对拍+推断）97%。

| 状态 | 部分 | 项 | 原版用量 | 关 | 说明 |
|---|---|---|---|---|---|
| 未做 | AI | `造兵/BlockIfThingNearFactory.IncludeThing` | 40 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.PersonalityType` | 35 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `造兵/BuildEntry.MinTime` | 34 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `造兵/BlockIfThingNearFactory.Relationship` | 28 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `造兵/BlockIfThingNearFactory.Rule` | 28 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.SkirmishPersonality` | 20 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `战略状态/AIStrategicStateDefinition.CannotAttackTargetReaction` | 16 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `造兵/BuildEntry.Upgrade` | 16 | a4 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `微操/AIMicroManagerData.DodgeThreats` | 15 | a4 a5 a7 | engine_aidodge aidodgeon/aidodgeoff 原版精确打击信标开关对照；tests/test_ai_dodge.py 按名回放，开启组 strict xfail：模型无躲避消费者，simai.micro_team 缺威胁视图与移动回调（归B）；见 work/re/c_dodge_report.md；固定0.5秒反应，截图秒窗与游戏帧漂移亦留gap；未量精确时间、圆边界、过滤和多威胁，不晋升已对拍 |
| 未做 | AI | `目标/AITargetingHeuristic.HeuristicType=Expansion` | 12 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `造兵/CountAsStructureForBuildPurposesFilter.ExcludeThing` | 12 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `组队招人/ObjectFilter.Include` | 11 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `其他/BuildingPlacementDistance.Distance` | 10 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.RepairBuildingsAtDifficulty` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `微操/AIMicroManagerData.DodgeThreatsReactionTimeMax` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `微操/AIMicroManagerData.DodgeThreatsReactionTimeMin` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `战略状态/AIStrategicStateDefinition.PathfindingCheckType` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `组队招人/TeamTemplate.RequireCanAttackTarget` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `经济/AccountShare.Account=SLUSH_FUND` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/EnemyFilter.Include` | 5 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/EnemyFilter.Relationship` | 5 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/EnemyFilter.Rule` | 5 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `微操/AIMicroManagerData.MinDistanceFromBaseToIgnoreTargets` | 5 | a4 a5 a7 | engine_aiignore aiignzero/aiignnear：仅基地距离阈值0/2000不同，无武装工程师延迟至26秒且两武士造出后；零阈值仍受伤，tests/test_ai_ignore_distance.py 按名回放伤害观测；Hunt/普通自动攻击与微操过滤入口尚未分离，基地取点和精确边界未量，不实现消费者、不晋升已对拍；见 work/re/c_ignore_distance_report.md |
| 未做 | AI | `微操/AIMicroManagerData.PassiveTargetSearchDistance` | 5 | a4 a5 a7 | C接口闸门阻塞：被动目标分类/选择在B的tactics._team_state；micro.Team.enemies无被动分类，MicroBlock仅有技能回调，缺候选与距离基准及选敌回写；SDK显式600/650/0、默认400，距离基准和零值语义未证实；本轮未上台、不实现消费者、不晋升已对拍；见 work/re/c_passive_distance_report.md |
| 未做 | AI | `微操/IgnoreTargets.Include` | 5 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `微操/SpecificSpecialPowerDelay.TogglePowerSubType=TOGGLE_LOCKDOWN` | 5 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `战略状态/AIStrategicStateDefinition.PathfindingCheckType=None` | 5 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `微操/IgnoreTargets.Exclude` | 4 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `造兵/CountAsStructureForBuildPurposesFilter.Include` | 4 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `造兵/CountAsStructureForBuildPurposesFilter.Rule` | 4 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.EmergencyManagerHandleConyardInDangerAtDifficulty` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `战术/Tactic.AestheticsManagerMinDistanceFromHarvester` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `战术/Tactic.AestheticsManagerPatrolIdleTime` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `目标/AITargetingHeuristic.HeuristicType=Point` | 3 | a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `目标/AITargetingHeuristic.HeuristicType=UnpackBuildingPlacement` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `阵营/ArmyDefinition.AircraftRepairFacility` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `阵营/ArmyDefinition.EnergyProducer` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `阵营/ArmyDefinition.ExpanderTemplate` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `阵营/ArmyDefinition.GathererTemplate` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `阵营/ArmyDefinition.MCVTemplate` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `阵营/ArmyDefinition.NavalRepairFacility` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `阵营/ArmyDefinition.PrimaryResourceNodeCollector` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `阵营/ArmyDefinition.PrimaryResourceThingToBuild` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `阵营/ArmyDefinition.VehicleRepairFacility` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `阵营/ArmyDefinition.WallPiece` | 3 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.BuildTechEfficiencyThreshold` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.BuildTechMinPowerAdvantage` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.DesiredExcessPowerBuffer` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.EmergencyManagerHandleNoConyardAtDifficulty` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.EmergencyManagerHandleNoIncomeAtDifficulty` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.EmergencyManagerHandleUnderAttackAtDifficulty` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `目标/AITargetingHeuristic.IgnoreMinDistanceFromConyardEntranceForTime` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `目标/AITargetingHeuristic.MinDistanceFromConyardEntrance` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `组队招人/ObjectFilter.Exclude` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `经济/ResourceMultiplierCheat.Difficulty` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `经济/ResourceMultiplierCheat.Percentage` | 2 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.AssaultBeaconRadius` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.CleanupRefineries` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.ConyardInDangerEmergencyEngineerDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.ConyardInDangerEmergencyHealthPercent` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.ConyardInDangerEmergencyUnderAttackTime` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.CoopPersonality` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.DefaultThreatFindRadius` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.EnemyResortingTime` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.EnemySortingBrutalDifficulty` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.EnemySortingEasyDifficulty` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.EnemySortingHardDifficulty` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.EnemySortingMediumDifficulty` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.HoldObjectBeaconRadius` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.HoldPositionBeaconRadius` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.MaxWallDestroyTimeToCountAsGoThroughWalls` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.RefineryPlacementIncreaseTickAmount` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.RefineryPlacementNumberOfIncreaseTicksBeforeGivingUp` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.RefineryPlacementStartDistanceDelta` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.ResourceNodeSearchRadius` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.ResourceNodeValueRemainingForExpansion` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/Filter.Exclude` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/Filter.Include` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/Filter.Rule` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.AICrushesInfantry` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.AIDozerBoredRadiusModifier` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.AttackMoveUsesFormations` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.AttackUsesLineOfSight` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.CastleSiegeStandBackDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.ChaseFromBehindLimit` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.DeepWaterDepth` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.EnableRepulsors` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.ForceSkirmishAI` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.FormationColumnWidth` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.FormationEnemyDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.FormationRowDepth` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.FormationSquadSpacing` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.GuardChaseUnitFrames` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.GuardEnemyReturnScanRate` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.GuardEnemyScanRate` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.HordesWaitForHordes` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.MaxRecruitDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.MaxRetaliateDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.MaxSquadWidth` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.MeleeApproachDist` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.MeleeApproachTolerance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.MinDistanceForGroup` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.NarrowPassageScale` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.Optimization_NumEfficiencyUpdates` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.Optimization_NumTeamsToRecruit` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.Optimization_TacticsEmergencyKickPeriod` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.Optimization_TimeToCacheCanEnterTransport` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.Optimization_TimeToCacheCanReachImmobileTarget` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.Optimization_TimeToCacheCanReachMobileTarget` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.RebuildDelaySeconds` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.RepulsedDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.ResourcesPoor` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.ResourcesWealthy` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.RetaliateFriendsRadius` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.RotateSkirmishBases` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.SkirmishGroupFudgeValue` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.StructureSeconds` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.StructuresPoorMod` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.StructuresWealthyMod` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.SupplyCenterSafeRadius` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.TeamPoorMod` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.TeamResourcesToBuild` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.TeamSeconds` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.TeamWealthyMod` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.UseFormations` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.WadeWaterDepth` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.WaitForOthers` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `全局常量/AIData.WallHeight` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `微操/AIMicroManagerData.CanCollectCratesWhenIdle` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `微操/AIMicroManagerData.FractionBlockedToDestroyWalls` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `微操/AIMicroManagerData.MaxSecondaryDamageFraction` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `微操/IgnoreTargets.StatusBitFlags` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `战略状态/AIStrategicStateDefinition.PathfindingCheckType=QuickDoesAttackPathExist` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `组队招人/TeamTemplate.BaseDefenseMaxDistance` | 1 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 推断 | AI | `造兵/BuildState.Difficulty` | 84 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.EngageHostileTargets` | 82 | a4 a5 a7 | 台上 aimicspon（开）/ aimicengoff（关）两个武士都在家跟征召兵打、都冲锋活到最后——关掉不让队伍躲开战斗；差别只在首次冲锋：关 ~258 帧、开 ~362 帧（各两次一致）。模拟器开关都冲，但先后相反（关 ~457、开 ~275），tests/test_simai.py strict xfail；私有模型里的打分式没读（按"杀死所需秒数"推断） |
| 推断 | AI | `微操/AIMicroManagerData.Crush` | 77 | a4 a5 a7 | 台上量过（engine_aicrush：开了 s28 前碾光守军）；模拟器已验证派发，碾压 move 终点不再被避让挪开（A 161 Sim.claims）；原场景仍 strict xfail：到厂晚约 6 s、目标死后等 UpdateTime 才重选（handoff A 161） |
| 推断 | AI | `组队招人/TeamTemplate.SortByDistance` | 75 | a4 a5 a7 | AI 模型代码里读了这个名字（台上没单独量：engine_aiskirm 里是推测） |
| 推断 | AI | `微操/AIMicroManagerData.ReverseMove` | 74 | a4 a5 a7 | 推断（台上未复现）：锤子 airev / airevp / airevt 都不倒车；剩门队员有没有当前攻击目标，量法见 handoff-b 第 73 节 |
| 推断 | AI | `目标/AITargetingHeuristic.Location` | 74 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `组队招人/TeamTemplate.ReleaseType` | 71 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `开局/SkirmishOpeningMove.Side` | 64 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/SpecificUnitCap.Cap` | 60 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/SpecificUnitCap.Difficulty` | 60 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/SpecificUnitCap.Unit` | 60 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `组队招人/CreateUnits.MinUnits` | 60 | a4 a5 a7 | AI 模型代码里读了这个名字（台上量的是 TeamTemplate.MinUnits，不是现造兵） |
| 推断 | AI | `组队招人/CreateUnits.UnitName` | 60 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `造兵/BuildEntry.PercentHigh` | 54 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `造兵/BuildEntry.PercentLow` | 54 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/PathToTargetHeuristic.LocomotorConditionToUseForTest` | 45 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `战术/Tactic.Distance` | 41 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `战术/Tactic.UseAestheticsManager` | 40 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/IsBuildingHeuristic` | 30 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/IsBuildingHeuristic.KindOf` | 30 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/IsBuildingHeuristic.PassIfBuilding` | 30 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.AlphaStrikeTargetHealthPct` | 28 | a4 a5 a7 | engine_aialphahp 固定远厂70%血量，仅阈值0.01/0.9不同；有限诊断不等于字段闭环；tests/test_simai_alphahp.py 保留完整回放，AlphaStrike目标可用条件待证实，见 handoff-c |
| 推断 | AI | `目标/AITargetingHeuristic.HeuristicType=FriendlyUnit` | 27 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.UpdateTime` | 26 | a4 a5 a7 | 台上量过（engine_aidefense aidefctl4：每圈晚 1～2 s）；模拟器 4 s 与 1 s 逐秒相同（tests/test_simai_bench_b.py strict xfail） |
| 推断 | AI | `组队招人/TeamTemplate.ReleaseType=NEVER_RELEASE` | 25 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `战术/Tactic.Tactic=Engineer` | 24 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.EnterBaseDefensesWhenIdle` | 23 | a4 a5 a7 | engine_aibasedef aibd1 是战斗中总开关开、idle关的正例（s21起1人进炮塔）；aibd0/aibdidle 总开关均关且无人进驻，不是idle分支正例；tests/test_simai_basedef_idle.py 直接计数回放，aibd1仍strict xfail；消费者已调用，到达/炮塔存活差异待A/B接口；见 handoff-c |
| 推断 | AI | `经济/AccountShare.Account` | 18 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/BaseSelection.PreferredNotBaseTypes` | 17 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/BaseSelection.SortOrder` | 17 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/BaseSelection.PreferredBaseTypes` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/BaseSelection.SortOrder=PREFER_OLDEST` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/ConstantHeuristic.Weight` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/IntervalHeuristic.CountFrom` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/TechBuildingShareHeuristic` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/TechBuildingShareHeuristic.Above` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/TechBuildingShareHeuristic.PercentOfFairShare` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.AlphaStrikeTargetTimeToKill` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.MinDistanceFromEnemy` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.SortType=ThreatToWater` | 14 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/AIPersonalityDefinition.Side` | 13 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/IgnoreTargets.Rule` | 13 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/AllNearbyNodesFullHeuristic` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.CrushPreference` | 12 | a4 a5 a7 | 同 Crush：派发已验证，碾压 move 终点已不挪；engine_aicrush 原场景 strict xfail 保留（handoff A 161） |
| 推断 | AI | `微操/AIMicroManagerData.RandomTargetScoreModifier` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.TimeToKeepTargetMax` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.TimeToKeepTargetMin` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `战术/Tactic.Tactic=SimpleExpansion` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `组队招人/TeamTemplate.Priority=COOP` | 11 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/PowerAdvantageHeuristic.Above` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/PowerAdvantageHeuristic.IncludeEnemyDefenses` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/PowerAdvantageHeuristic.IncludeOwnDefenses` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/PowerAdvantageHeuristic.Value` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/TimeSinceLastExpansionHeuristic` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/TimeSinceLastExpansionHeuristic.Time` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `组队招人/TeamTemplate.AllowRecruitUnitsInCombat` | 9 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/EnemyNearbyHeuristic.MinEnemyValue` | 8 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/ObjectOfTypeExistsHeuristic.Location` | 8 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.ForbiddenObjectStatus` | 8 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.SortType=ThreatToAir` | 8 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.Beacon` | 7 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.HeuristicType=Beacon` | 7 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `组队招人/TeamTemplate.MaxTypesOfUnits` | 7 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/AIPersonalityDefinition.BaseCompactness` | 6 | a4 a5 a7 | 台上量过（engine_aitower：0.5 / 0.75 / 1.0 塔落在不同圈）；模拟器只对上 0.5，0.75 / 1.0 和 0.5 一样（strict xfail） |
| 推断 | AI | `启发条件/BeaconExistsHeuristic` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/BeaconExistsHeuristic.Exists` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/BeaconExistsHeuristic.Type` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/PathToTargetHeuristic.Surface` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/ResourceNodeShareHeuristic` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/ResourceNodeShareHeuristic.Above` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/ResourceNodeShareHeuristic.PercentOfFairShare` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/SpecificSpecialPowerDelay.MaximumDelay` | 6 | a4 a5 a7 | 模型按成功施放后同类冷却消费上限；tests/test_simai_delay.py 验证上端点和真实冲锋执行接线；engine_aidelay 0/999实机PASS，脚本冲峰值2/1且曾冲>0已有回放；台上帧数减曾冲恒362、模型270，精确观测时钟strict xfail；随机分布及原版TOGGLE两种子类仍gap，不晋升原版用量；见work/re/c_delay_clock_report.md |
| 推断 | AI | `微操/SpecificSpecialPowerDelay.MinimumDelay` | 6 | a4 a5 a7 | 模型已读取；engine_aidelay 0/999实机配对仅改变MaximumDelay，本字段没有独立变量对照，不因探针出现字段名登记已对拍 |
| 推断 | AI | `微操/SpecificSpecialPowerDelay.PowerType` | 6 | a4 a5 a7 | 模型已读取；engine_aidelay 0/999实机配对仅改变MaximumDelay，本字段没有独立变量对照，不因探针出现字段名登记已对拍 |
| 推断 | AI | `微操/SpecificSpecialPowerDelay.TogglePowerSubType` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `战术/Tactic.Tactic=ExactExpansion` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `战术/Tactic.Tactic=GarrisonBuilding` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `组队招人/TeamTemplate.Priority=DEFENSE_HIGH` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.SiegeWeaponBuffer` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.SpecialPowerDelayMaximum` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.SpecialPowerDelayMinimum` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.HeuristicType=EnemyStructureCloseToShore` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.HeuristicType=TechBuilding` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.MaxDistanceToShore` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.SortType=ClosestToEnemy` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `经济/BudgetState.Difficulty` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `经济/BudgetState.State` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/IncomeAdvantageHeuristic` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/IncomeAdvantageHeuristic.Above` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/IncomeAdvantageHeuristic.Value` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/OpenNodeHeuristic` | 4 | a4 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/OpenNodeHeuristic.Exists` | 4 | a4 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/OpenNodeHeuristic.MinDistanceFromEnemy` | 4 | a4 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.CanUseSiegeState` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.GatherTempVisionRangeBonus` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.RetreatTempVisionRangeBonus` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.VitalObjectStatus` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `战术/Tactic.Tactic=NullTactic` | 3 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `阵营/ArmyDefinition.Side` | 3 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/BaseSelection.SortOrder=PREFER_NEWEST` | 2 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/CanBuildBuildingsOnSurfaceHeuristic` | 2 | a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/CanBuildBuildingsOnSurfaceHeuristic.MaxPlacementGridCells` | 2 | a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/CanBuildBuildingsOnSurfaceHeuristic.MinPlacementGridCells` | 2 | a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/CanBuildBuildingsOnSurfaceHeuristic.Surfaces` | 2 | a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.MaxUnitIdleDistanceChange` | 2 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.HeuristicType=Husk` | 2 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.HeuristicType=UnderAttackBy` | 2 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过（docs/engine/aitactics.md），没有测试跑这个台子 |
| 推断 | AI | `人格/AIPersonalityDefinition.ReactiveDefenseRadius` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过（docs/engine/aitactics.md），没有测试跑这个台子 |
| 推断 | AI | `人格/AIPersonalityDefinition.UnitBuilderEnemyNearbyDistance` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/AIPersonalityDefinition.UnitBuilderEnemyNearbyMultiplier` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/AIPersonalityDefinition.UnitBuilderOverallDefensivePreference` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/DefaultTacticHomeBaseCriteria.PreferredNotBaseTypes` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/DefaultTacticHomeBaseCriteria.SortOrder` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/RetreatBaseCriteria.PreferredNotBaseTypes` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/RetreatBaseCriteria.SortOrder` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.IsHarvesterManager` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.MaxTeamIdleDistanceChange` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.MinTimeToKeepTempVisionRangeBonus` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `战略状态/AIStrategicStateDefinition.MaxInactiveCopies` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.HeuristicType=Crate` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.HeuristicType=NeutralGarrison` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `组队招人/TeamTemplate.IsBaseDefenseTeam` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 已对拍 | AI | `开局/Order.Build` | 635 | a4 a5 a7 | docs/engine/aiopen.md#读数（aiopen f1～f3：造的顺序和 AlliedStandard 单子一样） |
| 已对拍 | AI | `目标/AITargetingHeuristic.HeuristicType` | 392 | a4 a5 a7 | docs/engine/aitactics.md#读数（ClosestStructure / SafestToGroundStructure 是 EnemyStructure，FriendlyLandStructure 是 FriendlyStructure，都上台） |
| 已对拍 | AI | `造兵/BuildEntry.Heuristic` | 380 | a4 a5 a7 | 台上量过（engine_aiskirm y aisknew / aisknew2：没列进任何建造状态的我们的兵不造、列成 FEWEST_UNIT 占兵营约一半；z aiskvinf / aiskvveh：BEST_UNIT_EXPECTED 兵营只造克制兵），测试对拍 tests/test_simai_bench_b.py（B 第 126–131 轮）；RANDOM_UNIT（PercentLow/High）、MinTime 没单独量 |
| 已对拍 | AI | `造兵/BuildEntry.Build` | 364 | a4 a5 a7 | 台上量过（engine_aiskirm y aisknew / aisknew2：没列进任何建造状态的我们的兵不造、列成 FEWEST_UNIT 占兵营约一半；z aiskvinf / aiskvveh：BEST_UNIT_EXPECTED 兵营只造克制兵），测试对拍 tests/test_simai_bench_b.py（B 第 126–131 轮）；RANDOM_UNIT（PercentLow/High）、MinTime 没单独量 |
| 已对拍 | AI | `组队招人/ObjectFilter.ExcludeThing` | 288 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 已对拍 | AI | `战略状态/TargetHeuristic.TargetHeuristic` | 287 | a4 a5 a7 | docs/engine/aitactics.md#读数（aitargetnear / aitargetsafe：按状态写的目标启发挑楼） |
| 已对拍 | AI | `战略状态/StrategicState.Difficulty` | 268 | a4 a5 a7 | docs/engine/aistate.md#按难度挂的状态（aidiff / aidiffx：普通 = MEDIUM，没挂 MEDIUM 的状态不跑） |
| 已对拍 | AI | `战略状态/StrategicState.State` | 268 | a4 a5 a7 | docs/engine/aistate.md#读数（人格只留台上写的状态，AI 只跑这些：aistateconst / aistateslash 等） |
| 已对拍 | AI | `开局/Order.Time` | 237 | a4 a5 a7 | docs/engine/aiopen.md#开局里的 Time 从什么时候算（aiotime：从唤醒起的绝对时刻） |
| 已对拍 | AI | `战术/Tactic.Tactic` | 184 | a4 a5 a7 | docs/engine/aitactics.md#读数（SimpleAttack / DefenseAvoidanceAttack / FlankAttack / StaticDefense 上台） |
| 已对拍 | AI | `组队招人/TeamTemplate.AlwaysRecruit` | 182 | a4 a5 a7 | 台上量过（engine_aiteamfilter aiar0～3，第 90 轮）、测试对拍 tests/test_simai_bench_b.py：关着新造的车留家、开着出门的队把它招走、满员不招、不预放时第一辆自己组队（模拟器每次晚 3～4 s）；模拟器多造第 3、4 辆是造兵的缺口（strict xfail），不是这个开关 |
| 已对拍 | AI | `组队招人/TeamTemplate.MicroManager` | 182 | a4 a5 a7 | 台上量过（engine_airetreat：airet / airet0 只差 MicroManager 指名的那份数据里的 RetreatPowerAdvantage，一个撤一个不撤；aipas1 / aipas0 只差 EngagePassiveTargets）、测试对拍 tests/test_simai.py——队伍跑的是 MicroManager 指名的那份微操数据；指名不存在的 id 会怎样没量 |
| 已对拍 | AI | `组队招人/TeamTemplate.MinUnits` | 182 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | AI | `组队招人/TeamTemplate.Priority` | 182 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | AI | `战略状态/TargetHeuristic.Priority` | 170 | a4 a5 a7 | docs/engine/aitactics.md#目标挑哪个（aitpphi / aitpplo：同一状态两条目标启发，Priority 高的先试，两向都上台） |
| 已对拍 | AI | `组队招人/TeamTemplate.ExcludeKindOf` | 170 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 已对拍 | AI | `组队招人/TeamTemplate.IncludeKindOf` | 170 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 已对拍 | AI | `组队招人/TeamTemplate.MaxUnits` | 170 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | AI | `战略状态/AIStrategicStateDefinition.MaxTargets` | 156 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | AI | `组队招人/ObjectFilter.Rule` | 155 | a4 a5 a7 | docs/engine/aistate.md#队伍招谁（aitfany / aitfnone / aitfall：ANY、NONE + 名单只要名单，ALL + 排除名单） |
| 已对拍 | AI | `目标/AITargetingHeuristic.RequireUniqueTarget` | 154 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | AI | `战术/Tactic.EndBehavior` | 152 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | AI | `组队招人/ObjectFilter.IncludeThing` | 152 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 已对拍 | AI | `组队招人/TeamTemplate.RegisteredObjectSet` | 148 | a4 a5 a7 | docs/engine/aistate.md#移动方式和对象集（第 81 轮） |
| 已对拍 | AI | `组队招人/TeamTemplate.AllowedLocomotorTypes` | 145 | a4 a5 a7 | docs/engine/aistate.md#移动方式和对象集（第 81 轮） |
| 已对拍 | AI | `目标/AITargetingHeuristic.VitalKindOf` | 129 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 已对拍 | AI | `组队招人/TeamTemplate.Priority=STANDARD` | 126 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | AI | `启发条件/ConstantHeuristic` | 119 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipoweradv.py |
| 已对拍 | AI | `人格/PowerChoice.PlayerPower` | 117 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipower.py |
| 已对拍 | AI | `人格/PowerChoice.Weight` | 117 | a4 a5 a7 | docs/engine/aiopen.md#买协议（aipwrb 权重 0 的不买） |
| 已对拍 | AI | `战术/Tactic.EndBehavior=DISBAND` | 105 | a4 a5 a7 | docs/engine/aitactics.md#目标没了以后（EndBehavior，2026-11-09 各一次）（aiendd：目标没了队伍解散、状态重派去兵营，和模型对上） |
| 已对拍 | AI | `目标/AITargetingHeuristic.ForbiddenKindOf` | 102 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 已对拍 | AI | `微操/AIMicroManagerData.RetreatPowerAdvantage` | 94 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_airetreat.py |
| 已对拍 | AI | `人格/UnitModifier.DefensiveModifier` | 92 | a4 a5 a7 | 台上量过（engine_aiskirm u：aiskmod 把维和、标枪的 UnitModifier 两个系数都设 0，造兵逐秒和原版 aiskirm c 一样）、测试对拍 tests/test_simai.py——没有选兵策略表时 UnitModifier 不影响造什么；有策略表时的打分没量（原版人格都没有） |
| 已对拍 | AI | `人格/UnitModifier.OffensiveModifier` | 92 | a4 a5 a7 | 台上量过（engine_aiskirm u：aiskmod 把维和、标枪的 UnitModifier 两个系数都设 0，造兵逐秒和原版 aiskirm c 一样）、测试对拍 tests/test_simai.py——没有选兵策略表时 UnitModifier 不影响造什么；有策略表时的打分没量（原版人格都没有） |
| 已对拍 | AI | `人格/UnitModifier.Unit` | 92 | a4 a5 a7 | 台上量过（engine_aiskirm u：aiskmod 把维和、标枪的 UnitModifier 两个系数都设 0，造兵逐秒和原版 aiskirm c 一样）、测试对拍 tests/test_simai.py——没有选兵策略表时 UnitModifier 不影响造什么；有策略表时的打分没量（原版人格都没有） |
| 已对拍 | AI | `战术/Tactic.DisbandAfterRetreatTeamSize` | 86 | a4 a5 a7 | 台上量过（engine_airetreat：airetf 0 撤回家后再出门，airetfd 999 撤回家后一直在家——撤退结束那轮人数 ≤ 它就结束战术、放人）、测试对拍 tests/test_simai.py；1 / 4 / 5 这种"剩几人才散"的中间值没量 |
| 已对拍 | AI | `微操/AIMicroManagerData.EnterGarrisons` | 84 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aigarrison.py |
| 已对拍 | AI | `造兵/BuildState.State` | 84 | a4 a5 a7 | 台上量过（engine_aiskirm y aisknew / aisknew2：没列进任何建造状态的我们的兵不造、列成 FEWEST_UNIT 占兵营约一半；z aiskvinf / aiskvveh：BEST_UNIT_EXPECTED 兵营只造克制兵），测试对拍 tests/test_simai_bench_b.py（B 第 126–131 轮）；RANDOM_UNIT（PercentLow/High）、MinTime 没单独量 |
| 已对拍 | AI | `微操/AIMicroManagerData.UseSpecialPowers` | 83 | a4 a5 a7 | 台上量过（engine_aimicro：aimicspon 开 两个武士 s41 冲锋，aimicspoff 关 一直没冲、s51 前被打死，脚本按的对照照样冲）、测试对拍 tests/test_simai.py（模拟器读进探针自写的微操数据：开的想冲、关的从不冲；技能本身模拟器没接，只记"想用"） |
| 已对拍 | AI | `微操/AIMicroManagerData.EngagePassiveTargets` | 82 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_airetreat.py |
| 已对拍 | AI | `开局/Order.Account` | 81 | a4 a5 a7 | docs/engine/aiopen.md#开局存款进哪个账户（Order Account，第 116 轮）（aiskacp / aiskacd：PRODUCTION 兵营出兵、DEFENSE 兵营不出） |
| 已对拍 | AI | `开局/Order.Deposit` | 81 | a4 a5 a7 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（aiom15：带 Deposit 2000 照造、晚 4 秒） |
| 已对拍 | AI | `微操/AIMicroManagerData.EngageTacticalTarget` | 79 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitactical.py |
| 已对拍 | AI | `微操/AIMicroManagerData.PullbackInjured` | 78 | a4 a5 a7 | engine_aipullback aipullsov 残血坦克离队回吊车；tests/test_simai_bench_b.py::test_a_hurt_soviet_tank_team_is_pulled_back_to_the_crane 回放；普通盟军/日本工厂不可进入；仅地面车辆回撤，吊车回收仍 strict xfail，未验证空海军/精确时间 |
| 已对拍 | AI | `目标/AITargetingHeuristic.SortType` | 76 | a4 a5 a7 | docs/engine/aitactics.md#目标挑哪个（Distance：aitpnear / aitpmt2 最近、次近；ThreatToGround：aitargetsafe） |
| 已对拍 | AI | `微操/AIMicroManagerData.EnemySearchDistanceVisionMultiplier` | 70 | a4 a5 a7 | engine_aisearch aisrchhi/aisrchlo 仅倍率1.5/0.25不同：高先打旁厂、到远厂0；低旁厂100且到远厂4；tests/test_simai_search.py 回放；仅被动建筑搜索，精确边界、敌军目标取得和揭雾未量 |
| 已对拍 | AI | `启发条件/EnemyNearbyHeuristic` | 68 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/EnemyNearbyHeuristic.Distance` | 68 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/EnemyNearbyHeuristic.EnemyNearby` | 68 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/ObjectOfTypeExistsHeuristic` | 67 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/ObjectOfTypeExistsHeuristic.PassIfExists` | 67 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `组队招人/ObjectFilter.Relationship` | 67 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `组队招人/TeamTemplate.MinPowerAdvantage` | 64 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | AI | `组队招人/CreateUnits.MaxUnits` | 60 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | AI | `战术/Tactic.Tactic=SimpleAttack` | 59 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 已对拍 | AI | `微操/AIMicroManagerData.UseGatherState` | 51 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipullback.py |
| 已对拍 | AI | `启发条件/OpeningMoveHeuristic` | 47 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiomove.py |
| 已对拍 | AI | `启发条件/OpeningMoveHeuristic.Complete` | 47 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiomove.py |
| 已对拍 | AI | `开局/OpeningMove.Difficulty` | 46 | a4 a5 a7 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（aiodf / aiodf2：只留 MEDIUM 的） |
| 已对拍 | AI | `开局/OpeningMove.Name` | 46 | a4 a5 a7 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（每个探针按名字挂自写开局，都照它造） |
| 已对拍 | AI | `开局/OpeningMove.Weight` | 46 | a4 a5 a7 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（aiowt / aiowt2：0% 永远抽不到） |
| 已对拍 | AI | `战术/Tactic.EndBehavior=RAMPAGE` | 46 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_ainamed.py |
| 已对拍 | AI | `组队招人/TeamTemplate.ReleaseType=RELEASE_TO_PRIORITY` | 46 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | AI | `启发条件/PathToTargetHeuristic` | 45 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiopath.py |
| 已对拍 | AI | `启发条件/PathToTargetHeuristic.ObjectTypeToUseForTest` | 45 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiopath.py |
| 已对拍 | AI | `启发条件/PathToTargetHeuristic.PathExists` | 45 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiopath.py |
| 已对拍 | AI | `目标/AITargetingHeuristic.HeuristicType=EnemyUnit` | 44 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 已对拍 | AI | `战术/Tactic.Tactic=DefenseAvoidanceAttack` | 43 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | AI | `微操/AIMicroManagerData.RetreatMinDistanceFromBase` | 40 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_airetreat.py |
| 已对拍 | AI | `目标/AITargetingHeuristic.Relationship` | 40 | a4 a5 a7 | docs/engine/ainamed.md#给关卡线的结论（ainmrel：写了 Relationship 就按关系过滤，玩家的楼当 NEUTRAL 不算，不出门） |
| 已对拍 | AI | `微操/AIMicroManagerData.RetreatMinDistanceToFallback` | 38 | a4 a5 a7 | engine_aifallback aifbshort100/aifblong500：四人存活回齐、在家约18秒、长组先于短组再出发；tests/test_simai_fallback.py::test_fallback_distance_first_return_and_departure；仅此固定FromBase=300场景的行为回放，未量内部退出位置、精确距离边界或其他基地选择 |
| 已对拍 | AI | `目标/AITargetingHeuristic.SortType=Distance` | 37 | a4 a5 a7 | docs/engine/aitactics.md#目标挑哪个（aitpnear 挑最近、aitpmt2 第二槽挑次近、aitpvk 显式写 Distance） |
| 已对拍 | AI | `微操/AIMicroManagerData.PullbackInjuredHealthPct` | 30 | a4 a5 a7 | engine_aipullpct 固定30%血量、苏联吊车，仅阈值0.2/0.5不同；tests/test_simai_pullpct.py::test_pullback_threshold_high_returns_before_recycling 完整回放四车回家且不到远厂；同文件 low 对照先到远厂；仅初次回撤阈值，精确边界/晚段/吊车回收未闭环（回收 strict xfail） |
| 已对拍 | AI | `战术/Tactic.Tactic=StaticDefense` | 28 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aidefense.py |
| 已对拍 | AI | `启发条件/TimerHeuristic` | 25 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/TimerHeuristic.EndTime` | 25 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/TimerHeuristic.StartTime` | 25 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `目标/AITargetingHeuristic.HeuristicType=EnemyStructure` | 25 | a4 a5 a7 | docs/engine/aitactics.md#读数（ClosestStructureHeuristic、SafestToGroundStructureHeuristic：aitargetnear / aitargetsafe） |
| 已对拍 | AI | `启发条件/IntervalHeuristic` | 22 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/IntervalHeuristic.ActiveTime` | 22 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/IntervalHeuristic.IntervalTime` | 22 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `微操/AIMicroManagerData.EnterGarrisonableStructureDistance` | 21 | a4 a5 a7 | engine_aigarrison aigar1/aigar0/aigarfar：默认150、旧楼EAST=40，近楼归AI、关闭或远楼不进；tests/test_simai_garrison_distance.py::test_garrison_distance_replays_recorded_near_far_and_disabled；仅现成近远行为回放，精确边界、其他配置值和进门死亡时序未量；距离0仅模型敏感性守卫 |
| 已对拍 | AI | `战术/Tactic.EndIfStateTurnsOff` | 19 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | AI | `经济/AccountShare.Percent` | 18 | a4 a5 a7 | 台上量过（engine_aiskirm d / f：开局后 CoopBudget 防御 5%，存款约 36000 两座塔、约 17000 一座、15000 没有）、测试对拍 tests/test_simai.py——塔数对上；第一座的时刻模拟器早 ~36 s（strict xfail），别的份额 / 状态没单独量 |
| 已对拍 | AI | `启发条件/TimerHeuristic.CountFrom` | 16 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `战略状态/AIStrategicStateDefinition.MaxRunningCopies` | 16 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | AI | `微操/IgnoreTargets.IncludeThing` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiteamfilter.py |
| 已对拍 | AI | `组队招人/TeamTemplate.Priority=LOW` | 15 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | AI | `组队招人/TeamTemplate.Priority=DEFENSE` | 13 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | AI | `目标/AITargetingHeuristic.SortType=ThreatToGround` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 已对拍 | AI | `目标/AITargetingHeuristic.HeuristicType=FriendlyStructure` | 11 | a4 a5 a7 | docs/engine/aitactics.md#读数（FriendlyLandStructureHeuristic：engine_aidefense 守自家建造厂） |
| 已对拍 | AI | `启发条件/PowerAdvantageHeuristic` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aipoweradv.py |
| 已对拍 | AI | `目标/AITargetingHeuristic.SearchRange` | 10 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | AI | `组队招人/TeamTemplate.Priority=HIGH` | 9 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | AI | `战术/Tactic.Targetless` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | AI | `经济/AccountShare.Account=DEFENSE` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | AI | `经济/AccountShare.Account=PRODUCTION` | 6 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiomove.py |
| 已对拍 | AI | `人格/AIPersonalityDefinition.SecondsTillTargetsExpire` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | AI | `微操/AIMicroManagerData.MaxTeamIdleTime` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 已对拍 | AI | `微操/AIMicroManagerData.MaxUnitIdleTime` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 已对拍 | 脚本动作 | `ALLOW_DISALLOW_ONE_BUILDING` | 3466 | a4 a5 a7 | tests/test_simbench.py::test_a_ban_holds_the_queue_and_does_not_cancel |
| 已对拍 | 脚本动作 | `PLAYER_SET_MONEY` | 345 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aitower.py |
| 已对拍 | 脚本动作 | `PLAYER_RELATES_PLAYER` | 319 | a4 a5 a7 | tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back |
| 已对拍 | 脚本动作 | `NAMED_TRANSFER_OWNERSHIP_PLAYER` | 231 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_invuln.py |
| 已对拍 | 脚本动作 | `PLAYER_SET_MAX_PLAYER_POWER_POINTS` | 206 | a4 a5 a7 | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 已对拍 | 脚本动作 | `UNIT_AI_TRANSFER_ALL` | 137 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aidefense.py |
| 已对拍 | 脚本动作 | `PLAYER_SET_PLAYER_POWER_POINTS` | 95 | a4 a5 a7 | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 已对拍 | 脚本动作 | `SKIRMISH_AI_MAKE_BASE` | 82 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiomove.py |
| 已对拍 | 脚本动作 | `SKIRMISH_AI_USE_REPAIRS` | 75 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aipullback.py |
| 已对拍 | 脚本动作 | `SKIRMISH_AI_USE_REBUILD_SYSTEM` | 67 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiswitch.py |
| 已对拍 | 脚本动作 | `SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES` | 14 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiswitch.py |
| 已对拍 | 脚本条件 | `PLAYER_HAS_OBJECT_COMPARISON` | 628 | a4 a5 a7 | tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back |
| 不涉及 | AI | `战略状态/AIStrategicStateDefinition.ExecutionBeginFeedbackKey` | 11 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `战略状态/AIStrategicStateDefinition.ExecutionCanceledFeedbackKey` | 11 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `战略状态/AIStrategicStateDefinition.ExecutionCompleteFeedbackKey` | 11 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `表现/StrategicDirectiveFeedback.Event` | 9 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `表现/StrategicDirectiveFeedback.FeedbackKey` | 9 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `表现/StrategicDirectiveFeedback.StrategicDirective` | 9 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `表现/SkirmishGameEventFeedback.Event` | 6 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `表现/SkirmishGameEventFeedback.FeedbackKey` | 6 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `人格/AIPersonalityDefinition.SkirmishTimeTillGreeting` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `全局常量/AIData.AllowForestFires` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `全局常量/AIData.AltCameraPitchOverride` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `全局常量/AIData.AltCameraZoomOverride` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `全局常量/AIData.DisableTrees` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `全局常量/AIData.LowLodTree` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `全局常量/AIData.LowLodTreeNoGrab` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `全局常量/AIData.LowLodTreeNoHarvest` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `全局常量/AIData.LowLodTreeScale` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `全局常量/AIData.MaximumCraterDepth` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `全局常量/AIData.UseLowLODTrees` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `表现/InTroubleSkirmishFeedbackControl.MinPowerAdvantageEnemiesInMyBaseVsAllMyUnits` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `表现/InTroubleSkirmishFeedbackControl.NumberOfObjectsRecentlyLost` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `表现/InTroubleSkirmishFeedbackControl.ObjectLostFilter` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `表现/InTroubleSkirmishFeedbackControl.OnlyIfLocalPlayerIs` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `表现/InTroubleSkirmishFeedbackControl.TimeBetweenScans` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `表现/InTroubleSkirmishFeedbackControl.TimeForNumberOfObjectLost` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `表现/InTroubleSkirmishFeedbackControl.TimeThatConditionsMustBeMet` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
| 不涉及 | AI | `表现/InTroubleSkirmishFeedbackControl.TimeoutAfterPlaying` | 1 | a4 a5 a7 | 纯表现（语音、视频、画面） |
