# 我们 9 关的敌方 AI 用到的清单项

由 `experimental/cnv/inventory_ai.py levels` 生成，**别手改**。范围：9 关（`missions/a1.py`～`a9.py`）里由遭遇战 AI 带的敌人：它的人格（`enemy_ai.py` 生成）沿继承、战略状态、战术、组队、目标启发、微操、造兵 / 预算状态、开局一路引用到的原版 AI 数据项，加上全局常量 AIData 和本阵营的 ArmyDefinition；再加关卡脚本里点了 AI 玩家名字的脚本动作 / 条件。状态取自 [inventory.md](inventory.md)。"AI 做完"的第一条：下表全部已对拍。

**已对拍 133 / 369**（不涉及的不算）。用到敌方 AI 的关：a4、a5、a7。

| 部分 | 已对拍 | 推断 | 未做 |
|---|---|---|---|
| AI | 121 | 115 | 121 |
| 脚本动作 | 11 | 0 | 0 |
| 脚本条件 | 1 | 0 | 0 |

按原版用量加权：已对拍 91%，已有（已对拍+推断）98%。

| 状态 | 部分 | 项 | 原版用量 | 关 | 说明 |
|---|---|---|---|---|---|
| 未做 | AI | `人格/AIPersonalityDefinition.SkirmishPersonality` | 20 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `战略状态/AIStrategicStateDefinition.CannotAttackTargetReaction` | 16 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `微操/AIMicroManagerData.DodgeThreats` | 15 | a4 a5 a7 | engine_aidodge aidodgeon/aidodgeoff 原版精确打击信标开关对照；tests/test_ai_dodge.py 按名回放，开启组 strict xfail：模型无躲避消费者，simai.micro_team 缺威胁视图与移动回调（归B）；见 work/re/c_dodge_report.md；固定0.5秒反应，截图秒窗与游戏帧漂移亦留gap；未量精确时间、圆边界、过滤和多威胁，不晋升已对拍 |
| 未做 | AI | `目标/AITargetingHeuristic.HeuristicType=Expansion` | 12 | a4 a5 a7 | C已上台：aiexpc:a东矿区4、崖矿区0、普通实体0，命令指向东矿点；模型已保留BaseSelection，增加显式候选回调和槽位点，Expansion不再回退普通实体。自动候选资格/基地发现与排序尚未证实，模型按名回放strict xfail；仅接口实现，不晋升；见 work/re/c_expansion_probe_report.md |
| 未做 | AI | `造兵/CountAsStructureForBuildPurposesFilter.ExcludeThing` | 12 | a4 a5 a7 | C静态核查：原版过滤器用于建造优先级，排除矿车/勘探车/日本矿厂核心；不是现有建筑计数。模型未消费该过滤器，候选分类需接B共享build_units，普通建筑BuildState优先级亦缺消费者；按工单接口门禁停止，未上台、未晋升。待B给候选分类/优先级接口；见work/re/c_buildfilter_report.md |
| 未做 | AI | `其他/BuildingPlacementDistance.Distance` | 10 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/AIPersonalityDefinition.RepairBuildingsAtDifficulty` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `微操/AIMicroManagerData.DodgeThreatsReactionTimeMax` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `微操/AIMicroManagerData.DodgeThreatsReactionTimeMin` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `战略状态/AIStrategicStateDefinition.PathfindingCheckType` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `组队招人/TeamTemplate.RequireCanAttackTarget` | 6 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `经济/AccountShare.Account=SLUSH_FUND` | 6 | a4 a5 a7 | C按名台子engine_aislush：aislush100/aislush0仅交换SLUSH_FUND与PRODUCTION份额，两组电厂均s19一座、s29两座，零份额原预测FAIL保留；开局未区分此账户。第二轮有收入无开局：aislsdef全程零炮塔，aislddef在s28/48/68造出1/2/3座，s60为2。tests/test_slush_account.py原读数及模型回放；账户余额/实际支出消费者仍gap，不以开局计数吻合晋升；见work/re/c_slush_report.md |
| 未做 | AI | `人格/EnemyFilter.Include` | 5 | a4 a5 a7 | C按名台子engine_aienemyfilter：近处敌矿车、仅Include由HARVESTER改ENGINEER，前者s15全离家、s18目标区4辆，后者s1-65在家4/目标区0；tests/test_enemyfilter.py保留原读数及按名回放，ENGINEER回放strict xfail。实际消费者为B的状态启发式/数据解析及near接口，非C的targets.py；未实现、不晋升；见work/re/c_enemyfilter_report.md |
| 未做 | AI | `人格/EnemyFilter.Relationship` | 5 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `人格/EnemyFilter.Rule` | 5 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `微操/AIMicroManagerData.MinDistanceFromBaseToIgnoreTargets` | 5 | a4 a5 a7 | E103 engine_aiignore aiignzt/aiignnt：同run逻辑时钟配对，0/2000首伤397/396；f406/421零组状态8无目标、高组状态0有目标。消费者已接被动选敌、敌对可攻击及逐人分配过滤；tests/test_ai_ignore_distance.py 零组精确回放通过，高组资格/分类仍strict xfail；基地取点/精确边界/宿主等价仍gap，不晋升已对拍；见 work/re/e103_ignore_distance.md |
| 未做 | AI | `微操/AIMicroManagerData.PassiveTargetSearchDistance` | 5 | a4 a5 a7 | E104 engine_aipassive_distance aipsdz/aipsdt/aipsds/aipsdl：0/1/200/600均f140状态6选四人旁厂，f320状态0；中心距350.3、逐兵至少324.3，微操目标不同于战术目标。两轮未出现距离分离；tests/test_ai_passive_distance.py按台名回放选择/移动/存活，精确首选时钟strict xfail；本入口未显现消费者，零值全局语义/距离基准/其他入口仍gap，暂停、不加猜测消费者、不晋升；见 work/re/e104_passive_distance.md、work/re/handoff-e.md |
| 未做 | AI | `微操/SpecificSpecialPowerDelay.TogglePowerSubType=TOGGLE_LOCKDOWN` | 5 | a4 a5 a7 | AI 模型代码里没有这个名字 |
| 未做 | AI | `战略状态/AIStrategicStateDefinition.PathfindingCheckType=None` | 5 | a4 a5 a7 | AI 模型代码里没有这个名字 |
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
| 推断 | AI | `微操/AIMicroManagerData.EngageHostileTargets` | 82 | a4 a5 a7 | E107新时钟 aiegon:a / aiegoff:a：关首冲259帧，开两轮371帧；两边首批都入队，关无行军单，开先编队站位。模型两边333帧向西，关首批无目标且不冲；补兵冲锋不能顶替首批。命名回放 tests/test_ai_engage_clock.py strict xfail；见 work/re/e107_engage_clock.md。目标取得/队伍发令仍gap，未晋升 |
| 推断 | AI | `微操/AIMicroManagerData.Crush` | 77 | a4 a5 a7 | engine_aicrush:aicrush1 台上s28–33守军0、坦克4；按名回放存活正常断言，清零strict xfail；模型守军11/9/9/9/8/8，首目标活着即被重选、未接触；首move终点不挪不代表后续均不挪；追踪/选敌及移动消费者仍gap，见work/re/e109_crush.md；不晋升 |
| 推断 | AI | `微操/AIMicroManagerData.ReverseMove` | 74 | a4 a5 a7 | engine_aipullback airev1/0台上s1–10坦克4、s19–22近厂2；tests/test_simai_bench_b.py按名回放，存活前置正常断言、近厂计数strict xfail；airevp近厂4不能证明没有倒车；缺同帧成员当前目标/位置/车身朝向，暂停新台；不把区域计数当倒车观测，不晋升；接口及假设表见work/re/e110_reverse.md |
| 推断 | AI | `组队招人/TeamTemplate.ReleaseType` | 71 | a4 a5 a7 | engine_aiskirm aiskirm:m 实机s128防御8/清扫99，s129防御0/清扫8，转队时逐帧兵池峰1；后续s134峰2，不能宣称全程峰1；tests/test_simai_bench_c.py 按名回放至170秒无非空清扫计数，strict xfail；新airelnever/airelprio的CNVTeams已证原两ID保留/转队且模型阶段归属匹配，原八人补测的独立建造厂日志宿主实测防御9→2、清扫0→7，同名空实例并存；tests/test_simai_bench_c.py::test_release_eight_named_model_replays_carrier_partial_transfer为strict xfail，宿主等价性/精确时钟/后段第三ID和其他模式仍gap，整个字段未晋升；见 work/re/c_release_eight_report.md、c_release_teams_report.md、c_release_report.md |
| 推断 | AI | `启发条件/PathToTargetHeuristic.LocomotorConditionToUseForTest` | 45 | a4 a5 a7 | E84 engine_aiopathcond a：同JapanAntiAirShip仅切NORMAL深水/SUPERSONIC空中；两组s22-s24均兵营1/电厂0，水组原始Island预测FAIL、空中PASS。tests/test_simai_bench_e.py按名回放实际计数通过，但不能区分条件生效与路径判定边界；C复核：旧配方Surface未显式指定，SDK移动器差异不能独立证明实际路径可达性；共享teamlog未提供路径求值或所选移动器读数，暂停重复上台，待可验证无路对照或D接口。保持gap不晋升，未改模型；见 work/re/c_pathcond_gate_report.md、e_pathcond_e84.md |
| 推断 | AI | `战术/Tactic.Distance` | 41 | a4 a5 a7 | 专用engine_aidistance aidist250/aidist2000保留AI队、同次传送1200，仅Distance不同；s65小组圈300/900=1/1，大组0/0，存活均1；两组各5条PASS、模型末态匹配；大组实机传送前离300、传送后回900再离，模型美学轨迹strict xfail；精确边界/动态队成员仍gap，不晋升；tests/test_simai_bench_c.py；见 work/re/c_distance_report.md |
| 推断 | AI | `战术/Tactic.UseAestheticsManager` | 40 | a4 a5 a7 | 专用engine_aiaesthetics aiaeson/aiaesoff固定Distance=2000，仅切美学开关；两组各5条PASS：on先离300、传送后回900再离，off回双圈，存活/锁存均1；tests/test_simai_bench_c.py关闭组完整轨迹已回放；探针战术附加属性现传入消费者；E108按D83实际调用回放：首次遇敌gate=0仍发，后续102次gate=0不发、两次gate=1发；完整模拟首发154对台191且漏461，选敌/成员目的地/ready仍gap、strict xfail，不晋升；tests/test_ai_aesthetics_clock.py；见 work/re/e108_aesthetics_gate.md |
| 推断 | AI | `造兵/BuildEntry.MinTime` | 34 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过（checks/engine_aiskirm.py:mt），没有测试跑这个台子 |
| 推断 | AI | `启发条件/IsBuildingHeuristic.KindOf` | 30 | a4 a5 a7 | E83 engine_aibuilding只测STRUCTURE空队列，无法区分KindOf匹配与忽略此字段；有效建造队列、匹配/不匹配、多个token仍gap，不晋升；见 work/re/e_building_e83.md |
| 推断 | AI | `微操/AIMicroManagerData.AlphaStrikeTargetHealthPct` | 28 | a4 a5 a7 | engine_aialphahp 旧固定70%对照；engine_aialphaclose 独立延迟守军、仅阈值0.01/0.9不同；tests/test_simai_bench_c.py 保留读数回放，有限诊断不等于字段闭环；目标适用条件与回放差异仍gap，见 work/re/c_alpha_close_report.md |
| 推断 | AI | `微操/AIMicroManagerData.UpdateTime` | 26 | a4 a5 a7 | engine_aimicro aimicupft/aimicupst:a 仅切微操0.5/4s，15帧宿主、D81时钟重量；台内首冲帧371/317、首活均2，末图逻辑帧872/876；tests/test_simai_bench_e.py 按名回放首活通过，精确首冲及人口峰值strict xfail；资格/更新前置状态、观测宿主人口等价仍gap；旧时钟读数不用于晋升，非固定延迟；见work/re/e102_update_clock.md，不晋升 |
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
| 推断 | AI | `目标/AITargetingHeuristic.MinDistanceFromEnemy` | 15 | a4 a5 a7 | C按名台子engine_aimindist：同一中立油井，TechBuilding阈值0组采样s6起目标区4，2000组采样s1-55在家4/目标区0；NamedObject阳性对照同0组。tests/test_min_enemy_distance.py断言原计数并按名回放；无同帧实际距离/候选资格，采样时钟未对齐游戏帧，边界与敌人物体资格仍gap，保持推断；见work/re/c_mindist_report.md |
| 推断 | AI | `目标/AITargetingHeuristic.SortType=ThreatToWater` | 14 | a4 a5 a7 | C按名台子engine_aiwater：两电厂/近处守护者/AI两栖矿车，仅切Distance与ThreatToWater，实机两组采样s14后均近4/远0/家0；模型ThreatToWater选远，按名回放strict xfail。tests/test_water_threat.py独立断言原计数并保留原预测FAIL；近处Named对照因s40-41无采样亦strict xfail。无同帧候选资格/实际water威胁值/水域样本资格，不改模型、不晋升；见work/re/c_water_report.md |
| 推断 | AI | `人格/AIPersonalityDefinition.Side` | 13 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/IgnoreTargets.Rule` | 13 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `启发条件/AllNearbyNodesFullHeuristic` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.CrushPreference` | 12 | a4 a5 a7 | 同Crush，开关/低偏好对照守军至少8的按名回放保留；完整清零strict xfail；不把活目标重选解释为死亡后等待，见work/re/e109_crush.md；不晋升 |
| 推断 | AI | `微操/AIMicroManagerData.RandomTargetScoreModifier` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.TimeToKeepTargetMax` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `微操/AIMicroManagerData.TimeToKeepTargetMin` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `战术/Tactic.Tactic=SimpleExpansion` | 12 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `组队招人/ObjectFilter.Include` | 11 | a4 a5 a7 | AI 模型代码里读了这个名字 |
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
| 推断 | AI | `目标/AITargetingHeuristic.ForbiddenObjectStatus` | 8 | a4 a5 a7 | C engine_aiforbid a：同近电厂仅切UNDER_IRON_CURTAIN禁用字段；无过滤有位/有过滤有位/有过滤清位三组原状态与近远家计数分别1/4/0/0、1/0/4/0、0/4/0/0，均PASS。tests/test_forbidden_status.py按名回放并断言原图计数；单位置位过滤吻合，未改模型。同帧候选资格、原版铁幕技能、多位组合及UNATTACKABLE/AIRBORNE_TARGET/SUBMERGED仍gap，整字段不晋升；见work/re/c_forbid_report.md |
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
| 推断 | AI | `微操/IgnoreTargets.Include` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.HeuristicType=EnemyStructureCloseToShore` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.HeuristicType=TechBuilding` | 5 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `目标/AITargetingHeuristic.MaxDistanceToShore` | 5 | a4 a5 a7 | C按名台子engine_aishore：同一岸边电厂仅上限2000改1，2000组s14目标区4/s25全离家，1组s1-65在家4/目标区0；普通EnemyStructure阳性对照同2000组。tests/test_shore_distance.py断言原读数并按名回放；1组strict xfail，世界桥接尚未提供实际岸距。复杂海岸/取点算法仍gap，未晋升；见work/re/c_shore_report.md |
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
| 推断 | AI | `微操/IgnoreTargets.Exclude` | 4 | a4 a5 a7 | AI 模型代码里读了这个名字 |
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
| 推断 | AI | `组队招人/ObjectFilter.Exclude` | 2 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/AIPersonalityDefinition.ReactiveDefenseRadius` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过（docs/engine/aitactics.md），没有测试跑这个台子 |
| 推断 | AI | `人格/AIPersonalityDefinition.UnitBuilderEnemyNearbyDistance` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/AIPersonalityDefinition.UnitBuilderEnemyNearbyMultiplier` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/AIPersonalityDefinition.UnitBuilderOverallDefensivePreference` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/DefaultTacticHomeBaseCriteria.PreferredNotBaseTypes` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/DefaultTacticHomeBaseCriteria.SortOrder` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/Filter.Exclude` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/Filter.Include` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
| 推断 | AI | `人格/Filter.Rule` | 1 | a4 a5 a7 | AI 模型代码里读了这个名字 |
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
| 已对拍 | AI | `造兵/BuildEntry.Heuristic` | 380 | a4 a5 a7 | E78 engine_aiskirm z：BEST_UNIT_EXPECTED 两组台上 PASS；[s150,s160) 征召兵组维和5→6、标枪0，锤子组标枪7→8→9、维和0；tests/test_simai_bench_e.py::test_best_unit_expected_infantry_choice 两组按来源断言通过（建造状态造的另一种=0；锤子组多的那个维和是单位生成器均匀抽签，台上 t 也抽2次：狗 s23、工程师 s144）；B 第 149 轮模拟器侧排除"一帧多单""队列非空仍下单"；FEWEST_UNIT 见 aisknew2 y、RANDOM_UNIT 见 aiskrand s；抽签结果属运气不对拍，"每次评估无条件掷一次随机数"没建模；见 work/re/e_aiheur_e78.md、work/re/handoff-b.md 第 149 节 |
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
| 已对拍 | AI | `组队招人/ObjectFilter.IncludeThing` | 152 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py:y |
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
| 已对拍 | AI | `造兵/BuildState.Difficulty` | 84 | a4 a5 a7 | 台上量过（engine_aiskirm s aiskdiff：只挂 HARD 的建造状态在普通难度一个不造，挂 MEDIUM 的照造），测试对拍 tests/test_simai_bench_b.py |
| 已对拍 | AI | `造兵/BuildState.State` | 84 | a4 a5 a7 | 台上量过（engine_aiskirm y aisknew / aisknew2：没列进任何建造状态的我们的兵不造、列成 FEWEST_UNIT 占兵营约一半；z aiskvinf / aiskvveh：BEST_UNIT_EXPECTED 兵营只造克制兵），测试对拍 tests/test_simai_bench_b.py（B 第 126–131 轮）；RANDOM_UNIT（PercentLow/High）、MinTime 没单独量 |
| 已对拍 | AI | `微操/AIMicroManagerData.UseSpecialPowers` | 83 | a4 a5 a7 | 台上量过（engine_aimicro：aimicspon 开 两个武士 s41 冲锋，aimicspoff 关 一直没冲、s51 前被打死，脚本按的对照照样冲）、测试对拍 tests/test_simai.py（模拟器读进探针自写的微操数据：开的想冲、关的从不冲；技能本身模拟器没接，只记"想用"） |
| 已对拍 | AI | `微操/AIMicroManagerData.EngagePassiveTargets` | 82 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_airetreat.py |
| 已对拍 | AI | `开局/Order.Account` | 81 | a4 a5 a7 | docs/engine/aiopen.md#开局存款进哪个账户（Order Account，第 116 轮）（aiskacp / aiskacd：PRODUCTION 兵营出兵、DEFENSE 兵营不出） |
| 已对拍 | AI | `开局/Order.Deposit` | 81 | a4 a5 a7 | docs/engine/aiopen.md#开局怎么抽、哪些单子会作废（OpeningMove Weight / Difficulty，第 89～90 轮）（aiom15：带 Deposit 2000 照造、晚 4 秒） |
| 已对拍 | AI | `微操/AIMicroManagerData.EngageTacticalTarget` | 79 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitactical.py |
| 已对拍 | AI | `微操/AIMicroManagerData.PullbackInjured` | 78 | a4 a5 a7 | engine_aipullback aipullsov 残血坦克离队回吊车；tests/test_simai_bench_b.py::test_a_hurt_soviet_tank_team_is_pulled_back_to_the_crane 回放；普通盟军/日本工厂不可进入；仅地面车辆回撤，吊车回收仍 strict xfail，未验证空海军/精确时间 |
| 已对拍 | AI | `目标/AITargetingHeuristic.SortType` | 76 | a4 a5 a7 | docs/engine/aitactics.md#目标挑哪个（Distance：aitpnear / aitpmt2 最近、次近；ThreatToGround：aitargetsafe） |
| 已对拍 | AI | `组队招人/TeamTemplate.SortByDistance` | 75 | a4 a5 a7 | 专用engine_aisort aisort0/aisort1：容量1，关闭远候选f177先离、开启近候选f178先离，另一名留原位；固定到目标距离约985/700、到基地顺序相反；tests/test_simai_bench_c.py::test_sort_by_distance_replays_named_departure按名断言两组台内计数并回放匹配；已对拍限具名候选离开顺序；招走解释仍INFERRED，同帧动态队成员ID/实际距离和等距规则仍gap；见 work/re/c_sort_report.md |
| 已对拍 | AI | `目标/AITargetingHeuristic.Location` | 74 | a4 a5 a7 | E81/E87 engine_ailocation a：同型电厂一陆一水、四架双刃，仅切Land/Water/Water Land；s40到陆厂/到水厂分别4/0、0/4、4/0；tests/test_simai_bench_e.py::test_target_location按名回放三组通过。Location按位置地形过滤；只验证EnemyStructure/Distance，浅滩、桥面及空中目标仍INFERRED；见 work/re/e_location_e87.md |
| 已对拍 | AI | `微操/AIMicroManagerData.EnemySearchDistanceVisionMultiplier` | 70 | a4 a5 a7 | engine_aisearch aisrchhi/aisrchlo 仅倍率1.5/0.25不同：高先打旁厂、到远厂0；低旁厂100且到远厂4；tests/test_simai_search.py 回放；仅被动建筑搜索，精确边界、敌军目标取得和揭雾未量 |
| 已对拍 | AI | `启发条件/EnemyNearbyHeuristic` | 68 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/EnemyNearbyHeuristic.Distance` | 68 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/EnemyNearbyHeuristic.EnemyNearby` | 68 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/ObjectOfTypeExistsHeuristic` | 67 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/ObjectOfTypeExistsHeuristic.PassIfExists` | 67 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `组队招人/ObjectFilter.Relationship` | 67 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `开局/SkirmishOpeningMove.Side` | 64 | a4 a5 a7 | E82 engine_aiopenside a：固定盟军玩家显式挂载三电厂开局，仅切Side。Allies在[s55,s60)电厂3/兵营0，Soviet电厂2/兵营1。D66：Side和玩家阵营全等才进候选，候选全空=开局直接完成、不下单、不回退；模型照此（B第147节）。tests/test_simai_bench_e.py::test_opening_side[aiosallies]、test_an_opening_of_another_side_is_not_run按名回放、断言台上读数（Soviet s19-s28 无电厂）。gap：Soviet之后的2电厂1兵营是没开局时的结构建造，模型没建（strict xfail，同第123节）；见 work/re/e_openside_e82.md |
| 已对拍 | AI | `组队招人/TeamTemplate.MinPowerAdvantage` | 64 | a4 a5 a7 | docs/engine/aistate.md#两队抢兵和 MinPowerAdvantage（第 82 轮） |
| 已对拍 | AI | `人格/SpecificUnitCap.Cap` | 60 | a4 a5 a7 | engine_aiskirm aiskcap:y（2026-11-12）：子人格给父人格没写的CNVNewPK四档Cap=2，新维和s33到2、停到s149（无上限aisknew2 s44已4），兵营改造标枪/维和；tests/test_simai_bench_b.py::test_a_specific_unit_cap_holds_our_unit_at_two按名回放、断言台上读数。E80父人格已有维和Cap=20时子人格Cap=2不生效=第一条命中（test_simai_bench_e.py）。gap：s150后又造到4、没死人，引擎拿什么数对上限未知（strict xfail test_after_s150_the_capped_unit_is_built_again）；见 work/re/handoff-b.md 第145节 |
| 已对拍 | AI | `人格/SpecificUnitCap.Difficulty` | 60 | a4 a5 a7 | engine_aiskirm aiskcap:y（2026-11-12）：子人格给父人格没写的CNVNewPK四档Cap=2，新维和s33到2、停到s149（无上限aisknew2 s44已4），兵营改造标枪/维和；tests/test_simai_bench_b.py::test_a_specific_unit_cap_holds_our_unit_at_two按名回放、断言台上读数。E80父人格已有维和Cap=20时子人格Cap=2不生效=第一条命中（test_simai_bench_e.py）。gap：s150后又造到4、没死人，引擎拿什么数对上限未知（strict xfail test_after_s150_the_capped_unit_is_built_again）；见 work/re/handoff-b.md 第145节 |
| 已对拍 | AI | `人格/SpecificUnitCap.Unit` | 60 | a4 a5 a7 | engine_aiskirm aiskcap:y（2026-11-12）：子人格给父人格没写的CNVNewPK四档Cap=2，新维和s33到2、停到s149（无上限aisknew2 s44已4），兵营改造标枪/维和；tests/test_simai_bench_b.py::test_a_specific_unit_cap_holds_our_unit_at_two按名回放、断言台上读数。E80父人格已有维和Cap=20时子人格Cap=2不生效=第一条命中（test_simai_bench_e.py）。gap：s150后又造到4、没死人，引擎拿什么数对上限未知（strict xfail test_after_s150_the_capped_unit_is_built_again）；见 work/re/handoff-b.md 第145节 |
| 已对拍 | AI | `组队招人/CreateUnits.MaxUnits` | 60 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | AI | `组队招人/CreateUnits.MinUnits` | 60 | a4 a5 a7 | engine_aicreate aicr1c/aicr3c：最低1在(301,316]帧激活，最低3在(631,646]帧激活；后者f316一人/f481两人均未激活；tests/test_simai_bench_c.py按名回放激活区间和成员；仅孤立单槽位最低数1/3，多槽位/替补/MaxUnits仍gap；s70额外造兵另有strict xfail；见 work/re/e_create_e88.md |
| 已对拍 | AI | `组队招人/CreateUnits.UnitName` | 60 | a4 a5 a7 | engine_aicreate aicr1c/aicr3c：最低1是一名新成员加两名已知预摆维和，最低3等三名新成员；tests/test_simai_bench_c.py按名回放首次组成；新成员兵种由固定生产归属仍INFERRED；仅指定最低数优先再普通补位，不是排他过滤；其他兵种/多槽位/替补仍gap；见 work/re/e_create_e88.md |
| 已对拍 | AI | `战术/Tactic.Tactic=SimpleAttack` | 59 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aitarget.py |
| 已对拍 | AI | `造兵/BuildEntry.PercentHigh` | 54 | a4 a5 a7 | 台上量过（engine_aiskirm s aiskrand：RANDOM_UNIT "0%–30%" 和不带百分号的 "30–100" 两条都造出来——不带 % 的数也按百分比读，原版 _RANDOM 状态就这么写），测试对拍 tests/test_simai_bench_b.py；两条的比例（预测 3:7，台上 4:4）样本太少没定 |
| 已对拍 | AI | `造兵/BuildEntry.PercentLow` | 54 | a4 a5 a7 | 台上量过（engine_aiskirm s aiskrand：RANDOM_UNIT "0%–30%" 和不带百分号的 "30–100" 两条都造出来——不带 % 的数也按百分比读，原版 _RANDOM 状态就这么写），测试对拍 tests/test_simai_bench_b.py；两条的比例（预测 3:7，台上 4:4）样本太少没定 |
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
| 已对拍 | AI | `造兵/BlockIfThingNearFactory.IncludeThing` | 40 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py:y |
| 已对拍 | AI | `微操/AIMicroManagerData.RetreatMinDistanceToFallback` | 38 | a4 a5 a7 | engine_aifallback aifbshort100/aifblong500：四人存活回齐、在家约18秒、长组先于短组再出发；tests/test_simai_fallback.py::test_fallback_distance_first_return_and_departure；仅此固定FromBase=300场景的行为回放，未量内部退出位置、精确距离边界或其他基地选择 |
| 已对拍 | AI | `目标/AITargetingHeuristic.SortType=Distance` | 37 | a4 a5 a7 | docs/engine/aitactics.md#目标挑哪个（aitpnear 挑最近、aitpmt2 第二槽挑次近、aitpvk 显式写 Distance） |
| 已对拍 | AI | `人格/AIPersonalityDefinition.PersonalityType` | 35 | a4 a5 a7 | tests/test_simai_bench_b.py::test_the_personality_condition_matches_the_id_not_the_personality_type（engine_aiskirm pt aiskpt / aiskpti：脚本条件 PLAYER_IS_HUMAN_OR_AI_PERSONALITY 只认人格 id，PersonalityType 写成别的名字或不写都不影响；AI 行为不读它；B 第 150 轮） |
| 已对拍 | AI | `启发条件/IsBuildingHeuristic` | 30 | a4 a5 a7 | E83 engine_aibuilding a：STRUCTURE空队列、现成基地1；PassIfBuilding=false时s40到陆厂4/在家0，true时0/4，两组PASS；tests/test_simai_bench_e.py::test_is_building_idle按名回放通过。只验空队列边界，建造中的行为未量；见 work/re/e_building_e83.md |
| 已对拍 | AI | `启发条件/IsBuildingHeuristic.PassIfBuilding` | 30 | a4 a5 a7 | E83 engine_aibuilding a：STRUCTURE空队列、现成基地1；PassIfBuilding=false时s40到陆厂4/在家0，true时0/4，两组PASS；tests/test_simai_bench_e.py::test_is_building_idle按名回放通过。只验空队列边界，建造中的行为未量；见 work/re/e_building_e83.md |
| 已对拍 | AI | `微操/AIMicroManagerData.PullbackInjuredHealthPct` | 30 | a4 a5 a7 | engine_aipullpct 固定30%血量、苏联吊车，仅阈值0.2/0.5不同；tests/test_simai_pullpct.py::test_pullback_threshold_high_returns_before_recycling 完整回放四车回家且不到远厂；同文件 low 对照先到远厂；仅初次回撤阈值，精确边界/晚段/吊车回收未闭环（回收 strict xfail） |
| 已对拍 | AI | `战术/Tactic.Tactic=StaticDefense` | 28 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aidefense.py |
| 已对拍 | AI | `造兵/BlockIfThingNearFactory.Relationship` | 28 | a4 a5 a7 | tests/test_simai_bench_b.py::test_a_thing_near_the_factory_blocks_the_entry（engine_aiskirm y aiskblkn / aiskblkr：Rule ANY + Relationship NEUTRAL 挡住，aiskblkf 400 外不挡；ENEMIES 走同一段代码没单独上台；B 第 149 轮） |
| 已对拍 | AI | `造兵/BlockIfThingNearFactory.Rule` | 28 | a4 a5 a7 | tests/test_simai_bench_b.py::test_a_thing_near_the_factory_blocks_the_entry（engine_aiskirm y aiskblkn / aiskblkr：Rule ANY + Relationship NEUTRAL 挡住，aiskblkf 400 外不挡；ENEMIES 走同一段代码没单独上台；B 第 149 轮） |
| 已对拍 | AI | `目标/AITargetingHeuristic.HeuristicType=FriendlyUnit` | 27 | a4 a5 a7 | C engine_aifrdistance a：aifrnear/aifrswap三友军MCV，仅交换近远角色；s30逻辑帧478/486，tact对应原友车/second，同帧坐标均为距基地650的最近候选；友/敌MCV存活3/1。tests/test_simai_friendly_c.py::test_friendly_distance_target按名回放通过。仅验SAME_PLAYER、MCV、Distance、单槽StaticDefense；其他排序、默认关系、unique多槽仍INFERRED。旧E85远处双车的站位strict xfail保留，不由新配方解释；见work/re/c_friendly_distance_report.md |
| 已对拍 | AI | `启发条件/TimerHeuristic` | 25 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/TimerHeuristic.EndTime` | 25 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/TimerHeuristic.StartTime` | 25 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `目标/AITargetingHeuristic.HeuristicType=EnemyStructure` | 25 | a4 a5 a7 | docs/engine/aitactics.md#读数（ClosestStructureHeuristic、SafestToGroundStructureHeuristic：aitargetnear / aitargetsafe） |
| 已对拍 | AI | `组队招人/TeamTemplate.ReleaseType=NEVER_RELEASE` | 25 | a4 a5 a7 | engine_airelease airelnever/airelprio仅ReleaseType不同；CNVTeams两组f166防御激活持3166/3167，priority在(526,541]同两ID转进攻，never保留至末样本；tests/test_simai_bench_c.py::test_never_release_engine_members_and_model_replay按名跑两台、断言实机ID/n/active及模型f301/601/976成员归属；仅固定两辆车的保留/转队，精确激活/转队时钟、priority后段短暂第三ID及其他释放模式仍gap；见 work/re/c_release_teams_report.md |
| 已对拍 | AI | `启发条件/IntervalHeuristic` | 22 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/IntervalHeuristic.ActiveTime` | 22 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `启发条件/IntervalHeuristic.IntervalTime` | 22 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `微操/AIMicroManagerData.EnterGarrisonableStructureDistance` | 21 | a4 a5 a7 | engine_aigarrison aigar1/aigar0/aigarfar：默认150、旧楼EAST=40，近楼归AI、关闭或远楼不进；tests/test_simai_garrison_distance.py::test_garrison_distance_replays_recorded_near_far_and_disabled；仅现成近远行为回放，精确边界、其他配置值和进门死亡时序未量；距离0仅模型敏感性守卫 |
| 已对拍 | AI | `战术/Tactic.EndIfStateTurnsOff` | 19 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | AI | `经济/AccountShare.Percent` | 18 | a4 a5 a7 | 台上量过（engine_aiskirm d / f：开局后 CoopBudget 防御 5%，存款约 36000 两座塔、约 17000 一座、15000 没有）、测试对拍 tests/test_simai.py——塔数对上；第一座的时刻模拟器早 ~36 s（strict xfail），别的份额 / 状态没单独量 |
| 已对拍 | AI | `启发条件/TimerHeuristic.CountFrom` | 16 | a4 a5 a7 | docs/engine/aistate.md#启发条件：定时、间隔、敌人在旁、某物存在（第 83 轮） |
| 已对拍 | AI | `战略状态/AIStrategicStateDefinition.MaxRunningCopies` | 16 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | AI | `造兵/BuildEntry.Upgrade` | 16 | a4 a7 | C engine_aiupgrade a：aicupgon常量状态含UPGRADE_TECH/Tech2，s39起持有2（建造厂+它够得着的兵营）；aicupgoff移除专用状态后恒0；见work/re/c_upgrade_report.md。B第153轮接模型：升级条目按状态权重×分（UPGRADE 140；UPGRADE_TECH MinTime前0、ForceTime后200推断、中间140推断）挑最高下单，扣PRODUCTION，下了升级这一轮不下兵；模拟器s20下单、s40起持有2。tests/test_simai_upgrade_c.py按名回放两组通过。电力门、效率/兵力比两道、开局里的升级单没建模 |
| 已对拍 | AI | `微操/IgnoreTargets.IncludeThing` | 15 | a4 a5 a7 | AI 模型代码里读了这个名字；台上量过、测试对拍：checks/engine_aiskirm.py:y |
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
