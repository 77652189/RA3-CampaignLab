# 我们 9 关用到的脚本、物体模块、武器效果（引擎 A 部分）

由 `experimental/cnv/inventory_levels.py --write` 生成，**别手改**。范围：9 关（`missions/a1.py`～`a9.py`）编出的全部脚本（`parts.merged`，含目标显示脚本）里的动作和条件；地图和任务摆的物体、我们自己的单位、脚本点名的模板，连同模块点名的武器、武器点名的物体（抛射体）和武器，取生效的模块（继承、include、同 id 覆盖）和武器效果。没跟：模块点名的别的物体（多是能变成 / 能装的东西：多功能步兵车的乘客、锤子坦克吸来的车）、物体生成表（死亡碎片、OCL 技能）和命令表（工厂能造什么）。AI 部分（引擎 B）在 [inventory-levels.md](inventory-levels.md)。状态和原版用量取自 [inventory.md](inventory.md)。停止条件①：下表全部已对拍。

**已对拍 89 / 200**（不涉及的不算）。

| 部分 | 已对拍 | 推断 | 未做 | 不涉及 |
|---|---|---|---|---|
| 脚本动作 | 52 | 0 | 0 | 12 |
| 脚本条件 | 12 | 0 | 0 | 0 |
| 物体模块 | 23 | 7 | 85 | 15 |
| 武器效果 | 2 | 3 | 16 | 0 |

按原版用量加权：已对拍 89%，已有（已对拍+推断）89%。

摆了、但原版数据和我们的单位里都找不到的模板（模块没算）：a9 `AlliedFutureTank`。

编出的脚本里有、清单里没有的名字（不算）：`Behaviors/TeleportSpecialAbilityUpdate`、`Behaviors/TeleportToCasterSpecialPower`、`NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT:SpecialPower_CNV_ChronoDeck`、`NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT:SpecialPower_CNV_IceEngineer_Freeze`、`UNIT_CHANGE_OBJECT_STATUS:IMMOBILE`。

| 状态 | 部分 | 项 | 原版用量 | 关 | 说明 |
|---|---|---|---|---|---|
| 未做 | 物体模块 | `Body/PropBody` | 1443 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 弹体和特效道具的身体（9 关 22 个模板里 16 个是弹体）：模拟器没有弹体（同 BezierProjectile），道具能不能挨打没读；例：AlliedAntiGroundAircraftMissileProjectile_Veteran, AlliedAntiInfantryVehicleTorpedoProjectile |
| 未做 | 物体模块 | `Behaviors/Physics` | 597 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 移动物理（坠落、弹跳、被击飞、倾倒）：模拟器走路按速度直走，没有物理；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 未做 | 物体模块 | `Behaviors/ToppleUpdate` | 347 | a4 | 倒伏：车压过的灯笼、栏杆、路灯倒下即死（OK_Lantern01 KillWhenStartToppled）。碾压本身已做（Sim.crush_along，台上对过），倒伏还没有：OK_LANTERN01 在模拟器里不是物体（不挡路），platprops.STRUCTURE 里的栏杆路灯是永久障碍（游戏里车能压倒）；台上没量过灯笼，要先写探针；例：OK_Lantern01 |
| 未做 | 物体模块 | `Behaviors/ModelConditionUpgrade` | 341 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedAntiInfantryInfantry, AlliedAntiVehicleInfantry |
| 未做 | 物体模块 | `Behaviors/ContestableGarrisonContain` | 305 | a4 | 已核（11-08）：模拟器没有这个效果（没有驻军）；例：HA_Building16_02, HA_Building16_03 |
| 未做 | 物体模块 | `Behaviors/InvisibilityBehavior` | 305 | a4 a5 a9 | 已核（11-08）：模拟器没有这个效果（没有隐身）；例：CNV_A4IceDisplay, CNV_A4IceSeed |
| 未做 | 物体模块 | `Behaviors/EnableDynamicsCollide` | 137 | a4 | 模拟器代码里没有这个名字；例：OK_Lantern01 |
| 未做 | 物体模块 | `Behaviors/DynamicsUpdate` | 113 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryVehicle |
| 未做 | 物体模块 | `Behaviors/StancesBehavior` | 108 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 已核（11-08）：模拟器没有这个效果（没有姿态）；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 未做 | 物体模块 | `Behaviors/LevelUpUpgrade` | 88 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryInfantry |
| 未做 | 物体模块 | `Behaviors/RunOffMapBehavior` | 88 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 已核（11-08）：模拟器没有这个效果（没有逃离地图）；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryInfantry |
| 未做 | 物体模块 | `Behaviors/EngineerContain` | 70 | a1 a2 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 未做 | 物体模块 | `Behaviors/RepairUpdate` | 66 | a1 a2 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 未做 | 物体模块 | `Behaviors/InfiltratorContain` | 34 | a1 a2 a4 a5 a6 a7 a8 | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedBarracks |
| 未做 | 物体模块 | `Behaviors/LUAEventList` | 32 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 未做 | 物体模块 | `Behaviors/ToggleStatusSpecialAbilityUpdate` | 27 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 已核（11-08）：模拟器没有这个效果（没有按钮切换状态）；例：AlliedAntiInfantryInfantry, AlliedAntiNavyShipTech1 |
| 未做 | 物体模块 | `Behaviors/FreefallUpdate` | 24 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 未做 | 物体模块 | `Behaviors/SuppressionUpdate` | 22 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 未做 | 物体模块 | `Behaviors/LaserState` | 19 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedAntiAirVehicleTech1, AlliedAntiVehicleInfantry |
| 未做 | 物体模块 | `Behaviors/QueueProductionExitUpdate` | 19 | a1 a2 a4 a5 a6 a7 a8 | 模拟器代码里没有这个名字；例：AlliedBarracks, AlliedConstructionYard |
| 未做 | 物体模块 | `Behaviors/ReplaceSelfSpecialAbility` | 18 | a1 a2 a4 a5 a6 a7 a9 | 已核（11-08）：模拟器没有这个效果（没有换形态）；例：AlliedConstructionYard, AlliedMCV |
| 未做 | 物体模块 | `Behaviors/WeaponFireSpecialAbilityUpdate` | 16 | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiNavalScout, AlliedAntiStructureShip |
| 未做 | 物体模块 | `Behaviors/BridgeBuilder` | 14 | a1 a4 a7 | 模拟器代码里没有这个名字；例：HB_Bridge_02 |
| 未做 | 物体模块 | `Body/ManagerBody` | 14 | a1 a4 a7 | 模拟器代码里没有这个名字；例：HB_Bridge_02 |
| 未做 | 物体模块 | `AI/JetAIUpdate` | 13 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedBomberAircraft, AlliedFighterAircraft |
| 未做 | 物体模块 | `Behaviors/TransportContain` | 13 | a1 a2 a4 a5 a7 a9 | 模拟器代码里没有这个名字；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryVehicle |
| 未做 | 物体模块 | `Behaviors/SpawnBehavior` | 10 | a1 a2 a4 a5 a6 a7 a8 | 已核（11-08）：模拟器没有这个效果（没有母体造随从）；例：AlliedAirfield, AlliedRefinery |
| 未做 | 物体模块 | `Behaviors/ProductionUpdateInfo` | 9 | a1 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedConstructionYard, AlliedMCV |
| 未做 | 物体模块 | `Behaviors/EjectPassengersSpecialAbilityUpdate` | 7 | a2 a5 a9 | 模拟器代码里没有这个名字；例：AlliedBomberAircraft, CNV_Burrower |
| 未做 | 物体模块 | `Behaviors/AssignSlavesTargetObjectSpecialPower` | 6 | a2 a4 a5 a7 a8 | 模拟器代码里没有这个名字；例：AlliedWarFactory, JapanNavalYard |
| 未做 | 物体模块 | `Behaviors/BezierProjectile` | 6 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 已核（11-08）：模拟器没有这个效果（开火按每秒伤害直接扣血，没有弹体）；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 未做 | 物体模块 | `Behaviors/OCLSpecialPower` | 6 | a1 a2 a4 a6 a7 | 模拟器代码里没有这个名字；例：SovietCommandoTech1 |
| 未做 | 物体模块 | `Behaviors/SubStructureStorageBehavior` | 6 | a1 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedMCV, JapanMCV |
| 未做 | 物体模块 | `Behaviors/TrackDamage` | 6 | a1 a2 a3 a4 a5 a6 a7 a8 | 模拟器代码里没有这个名字；例：AlliedAntiNavalScout, AlliedFighterAircraft |
| 未做 | 物体模块 | `Behaviors/TrackIncomingWeaponFireBehavior` | 6 | a1 a2 a3 a4 a5 a6 a7 a8 | 模拟器代码里没有这个名字；例：AlliedAntiNavalScout, AlliedFighterAircraft |
| 未做 | 物体模块 | `Behaviors/WallBuilderBehavior` | 6 | a1 a2 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedWallPiece, JapanWallPiece |
| 未做 | 物体模块 | `Behaviors/AttackAssistResponseBehavior` | 5 | a1 a2 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedBaseDefenseAdvanced, SovietBaseDefenseAdvanced |
| 未做 | 物体模块 | `Behaviors/CaptureSpecialAbilityUpdate` | 5 | a1 a2 a3 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedCommandoTech1, AlliedEngineer |
| 未做 | 物体模块 | `Behaviors/EmotionTrackerUpdate` | 5 | a1 a2 a3 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedCommandoTech1, AlliedEngineer |
| 未做 | 物体模块 | `Behaviors/PassiveAreaEffectBehavior` | 5 | a3 a4 a7 | 模拟器代码里没有这个名字；例：AlliedEngineer, CNV_IceEngineer |
| 未做 | 物体模块 | `Behaviors/ActivateModuleSpecialPower` | 4 | a1 a2 a4 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiStructureVehicle, JapanAntiVehicleVehicleTech1 |
| 未做 | 物体模块 | `Behaviors/ParkingPlaceBehavior` | 4 | a4 a5 a7 a8 | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedAntiStructureShip |
| 未做 | 物体模块 | `Behaviors/QueueDockBehavior` | 4 | a1 a2 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedRefinery, JapanRefinery |
| 未做 | 物体模块 | `Behaviors/RadarBehavior` | 4 | a4 | 模拟器代码里没有这个名字；例：JapanConstructionYard |
| 未做 | 物体模块 | `Behaviors/SpecialDisguiseUpdate` | 4 | a1 a4 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiVehicleVehicleTech3, JapanLightTransportVehicle |
| 未做 | 物体模块 | `Behaviors/AssistedPlacementBehavior` | 3 | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedRefinery, JapanRefinery |
| 未做 | 物体模块 | `Behaviors/AttachUpdate` | 3 | a1 a2 a4 a5 a6 a7 a9 | 已核（11-08）：模拟器没有这个效果（没有附着）；例：AlliedCommandoTech1, SovietScoutVehicle |
| 未做 | 物体模块 | `Behaviors/HitReactionBehavior` | 3 | a1 a2 a3 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedAntiInfantryInfantry, CNV_Beacon |
| 未做 | 物体模块 | `Behaviors/LiftObjectUpdate` | 3 | a1 a2 a4 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiAirVehicleTech1, AlliedBaseDefense |
| 未做 | 物体模块 | `Behaviors/LoseHealthUpdate` | 3 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：CNV_Liberty, SovietBomberAircraft |
| 未做 | 物体模块 | `Behaviors/MovementSpecialPower` | 3 | a1 a4 a6 a7 | 模拟器代码里没有这个名字；例：JapanAntiVehicleVehicleTech3 |
| 未做 | 物体模块 | `Behaviors/ReturnToProducerSpecialPower` | 3 | a1 a2 a3 a4 a5 a6 a7 a8 | 模拟器代码里没有这个名字；例：AlliedFighterAircraft, SovietFighterAircraft |
| 未做 | 物体模块 | `Behaviors/SecondaryObjectListenerModule` | 3 | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiAirVehicleTech1, AlliedBaseDefense |
| 未做 | 物体模块 | `Behaviors/SlaughterHordeContain` | 3 | a5 a7 a8 | 模拟器代码里没有这个名字；**待核**：台上量过（checks/engine_aipullback.py），可能用别的名字实现了；例：AlliedAntiStructureShip, CNV_Liberty |
| 未做 | 物体模块 | `Behaviors/StealthDetectorUpdate` | 3 | a2 a6 | 已核（11-08）：模拟器没有这个效果（没有反隐）；例：AlliedScoutInfantry |
| 未做 | 物体模块 | `Behaviors/StructurePlacementBehavior` | 3 | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedRefinery, JapanRefinery |
| 未做 | 物体模块 | `Behaviors/AimWeapon` | 2 | a1 a4 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedAntiVehicleInfantry, SovietAntiVehicleInfantry |
| 未做 | 物体模块 | `Behaviors/ConvergingLaserState` | 2 | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiStructureVehicle, SovietAntiVehicleVehicleTech1 |
| 未做 | 物体模块 | `Behaviors/InvisibilityBroadcastUpdate` | 2 | a1 a4 a6 a7 | 已核（11-08）：模拟器没有这个效果（没有隐身）；例：AlliedAntiVehicleVehicleTech3 |
| 未做 | 物体模块 | `Behaviors/NotifyWhenAttackingBehavior` | 2 | a1 a2 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedBaseDefenseAdvanced, SovietBaseDefenseAdvanced |
| 未做 | 物体模块 | `Behaviors/PowerUpgrade` | 2 | a5 | 模拟器代码里没有这个名字；例：SovietPowerPlant |
| 未做 | 物体模块 | `Behaviors/PrematureDischargeSpecialPower` | 2 | a4 | 模拟器代码里没有这个名字；例：JapanBaseDefenseAdvanced |
| 未做 | 物体模块 | `Behaviors/RecallUnitsSpecialPower` | 2 | a4 a7 | 模拟器代码里没有这个名字；例：AlliedAirfield |
| 未做 | 物体模块 | `Behaviors/SpiderHoleUpdate` | 2 | a4 | 模拟器代码里没有这个名字；例：JapanAntiVehicleInfantry |
| 未做 | 物体模块 | `Behaviors/AssistedPlacementInfoBehavior` | 1 | a1 a2 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：OreNode |
| 未做 | 物体模块 | `Behaviors/ChargeWeaponUpdate` | 1 | a4 | 模拟器代码里没有这个名字；例：JapanBaseDefenseAdvanced |
| 未做 | 物体模块 | `Behaviors/FireWeaponCollide` | 1 | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：JapanBalloonBomb, SovietAntiVehicleInfantry |
| 未做 | 物体模块 | `Behaviors/GarrisonContain` | 1 | a6 a7 | 已核（11-08）：模拟器没有这个效果（没有驻军；NAMED_GARRISON_SPECIFIC_BUILDING 另算）；例：AlliedBaseDefense |
| 未做 | 物体模块 | `Behaviors/GrapplingHookUpdate` | 1 | a1 a3 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech3 |
| 未做 | 物体模块 | `Behaviors/LinearDamageUpdate` | 1 | a1 a2 a4 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiNavalScout |
| 未做 | 物体模块 | `Behaviors/MagneticEffectUpdate` | 1 | a1 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiNavyShipTech1 |
| 未做 | 物体模块 | `Behaviors/MonitorConditionUpdate` | 1 | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：JapanMiner |
| 未做 | 物体模块 | `Behaviors/OCLMonitorUpdate` | 1 | a1 a2 a4 a6 a7 | 模拟器代码里没有这个名字；例：SovietCommandoTech1 |
| 未做 | 物体模块 | `Behaviors/ObjectCreationUpgrade` | 1 | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech1 |
| 未做 | 物体模块 | `Behaviors/ReconstituteStateSpecialAbility` | 1 | a1 a2 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedCommandoTech1 |
| 未做 | 物体模块 | `Behaviors/ShieldSphereUpdate` | 1 | a2 a6 | 模拟器代码里没有这个名字；例：AlliedAntiStructureVehicle |
| 未做 | 物体模块 | `Behaviors/SlaveWatcherBehavior` | 1 | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech1 |
| 未做 | 物体模块 | `Behaviors/StoreCurrentStateUpdate` | 1 | a1 a2 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedCommandoTech1 |
| 未做 | 物体模块 | `Behaviors/StoreObjectsSpecialPower` | 1 | a7 a8 | 已核（11-08）：模拟器没有这个效果（没有存放单位）；例：CNV_Liberty |
| 未做 | 物体模块 | `Behaviors/SweepingLaserState` | 1 | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：SovietScoutVehicle |
| 未做 | 物体模块 | `Behaviors/SwitchLocomotorUpdate` | 1 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：CNV_Liberty, SovietBomberAircraft |
| 未做 | 物体模块 | `Behaviors/TeleportStoredObjectsSpecialPower` | 1 | a7 a8 | 已核（11-08）：模拟器没有这个效果（没有传送存放的单位）；例：CNV_Liberty |
| 未做 | 物体模块 | `Behaviors/TeleportStoredObjectsUpdate` | 1 | a7 a8 | 已核（11-08）：模拟器没有这个效果（UNIT_TELEPORT_TO_WAYPOINT 另算）；例：CNV_Liberty |
| 未做 | 物体模块 | `Behaviors/HeightDieUpdate` | 0 | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：JapanBalloonBomb |
| 未做 | 物体模块 | `Behaviors/ProjectileUpdate` | 0 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 已核（11-08）：模拟器没有这个效果（开火按每秒伤害直接扣血，没有弹体飞行时间）；例：AlliedAntiVehicleVehicleTech1Projectile, AlliedBomberAircraftBombProjectile |
| 未做 | 武器效果 | `InformTargetNugget` | 69 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AAAVT1_AlliedAntiVehicleInfantryMissileLauncher, ABD_AlliedAntiVehicleInfantryMissileLauncher |
| 未做 | 武器效果 | `SuppressionNugget` | 64 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AAAVT1_AlliedAntiVehicleInfantryMissileLauncher, AAAVT1_CommandoPistolWeapon |
| 未做 | 武器效果 | `MetaImpactNugget` | 36 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AAAVT1_ShotgunWeapon, ABD_ShotgunWeapon |
| 未做 | 武器效果 | `ActivateLaserNugget` | 27 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 已核（11-08）：模拟器没有这个效果（没有激光束）；例：AAAVT1_JapanAntiVehicleInfantryPlasmaBazooka, ABD_JapanAntiVehicleInfantryPlasmaBazooka |
| 未做 | 武器效果 | `AttributeModifierNugget` | 20 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AAAVT1_RepairWeapon, AAGA_RepairWeapon |
| 未做 | 武器效果 | `ParalyzeNugget` | 11 | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AAAVT1_RoarWeapon, ABD_RoarWeapon |
| 未做 | 武器效果 | `TintObjectsNugget` | 9 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedCommandoAttachWeapon, AlliedSupportAircraftShrinkRay |
| 未做 | 武器效果 | `ActivateLiftObjectNugget` | 6 | a1 a2 a4 a6 a7 | 模拟器代码里没有这个名字；例：AAAVT1_JapanCommandoTech1PsyonicAntiAirCrush, AAAVT1_JapanCommandoTech1PsyonicCrush |
| 未做 | 武器效果 | `SpecialPowerNugget` | 6 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedAntiVehicleVehicleTech1TargetPainter, CNV_DeckSendTrigger |
| 未做 | 武器效果 | `AttachNugget` | 4 | a1 a2 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedCommandoAttachWeapon, SovietScoutVehicleMeleeAttachWeapon |
| 未做 | 武器效果 | `StripMaxHealthPercentNugget` | 3 | a1 a2 a4 a6 a7 | 模拟器代码里没有这个名字；例：AAAVT1_JapanCommandoTech1PsyonicCrush, ABD_JapanCommandoTech1PsyonicCrush |
| 未做 | 武器效果 | `ActivateLinearDamageNugget` | 2 | a1 a2 a4 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiNavalScoutSonar, AlliedAntiNavalScoutSonarForBridges |
| 未做 | 武器效果 | `DamageContainedNugget` | 2 | a1 a2 a3 a5 | 模拟器代码里没有这个名字；例：SovietAntiInfantryInfantryMolotovCocktailWarhead |
| 未做 | 武器效果 | `LeechPercentMaxHealthDamageNugget` | 2 | a1 a3 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：SovietHarpoonCrushWeapon |
| 未做 | 武器效果 | `GrapplingHookNugget` | 1 | a1 a3 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech3Harpoon |
| 未做 | 武器效果 | `LeechHealthDamageNugget` | 1 | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：SovietAntiVehicleVehicleTech1LeechBeamWeapon |
| 推断 | 物体模块 | `Behaviors/WeaponSetUpdate` | 82 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里有这个名字；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryInfantry |
| 推断 | 物体模块 | `Behaviors/StatusBitsUpgrade` | 66 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里有这个名字；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryVehicle |
| 推断 | 物体模块 | `Behaviors/CommandSetUpgrade` | 5 | a1 a4 a5 a7 | 模拟器代码里有这个名字；例：AlliedConstructionYard, CNVA4AlliedConstructionYard |
| 推断 | 物体模块 | `Behaviors/AutoDepositUpdate` | 4 | a1 a4 a5 a7 | 模拟器代码里有这个名字；例：OilDerrick |
| 推断 | 物体模块 | `Behaviors/SpecialAbilityUpdate` | 4 | a1 a4 a6 a7 | 模拟器代码里有这个名字；例：JapanAntiInfantryInfantry, JapanAntiVehicleVehicleTech1 |
| 推断 | 物体模块 | `Behaviors/TechUpgradeReceiver` | 4 | a2 a4 a5 a7 a8 | 模拟器代码里有这个名字；例：AlliedAirfield, AlliedBarracks |
| 推断 | 物体模块 | `Behaviors/FireWeaponUpdate` | 1 | a1 a2 a4 a5 a6 a7 | 部分：simunits.ocl_round 把召出物的 FireWeaponNugget + LifetimeUpdate 折成伤害，不模拟召出物本身；例：SovietHeavyAntiVehicleInfantry |
| 推断 | 武器效果 | `WeaponOCLNugget` | 26 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里有这个名字；例：AlliedAntiStructureAttackDrones, AlliedAntiStructureSolarTargeter |
| 推断 | 武器效果 | `LineDamageNugget` | 6 | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里有这个名字；例：AAAVT1_SovietCommandoSniperRifle, ABD_SovietCommandoSniperRifle |
| 推断 | 武器效果 | `SecondaryDamageNugget` | 5 | a7 | simunits._weapons 读 Amount（不要升级的那条）→ sdps，Sim.chill；例：AlliedSupportAircraftCryobeam |
| 已对拍 | 脚本动作 | `SET_MILLISECOND_TIMER` | 4153 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过：checks/engine_acquire.py |
| 已对拍 | 脚本动作 | `SET_FLAG` | 4105 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_aimicro.py |
| 已对拍 | 脚本动作 | `ALLOW_DISALLOW_ONE_BUILDING` | 3466 | a4 a5 a7 | tests/test_simbench.py::test_a_ban_holds_the_queue_and_does_not_cancel |
| 已对拍 | 脚本动作 | `LINK_MISSION_OBJECTIVE_TO_OBJECT` | 950 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_scripts5.py |
| 已对拍 | 脚本动作 | `NAMED_DELETE` | 908 | a2 a4 a5 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_attack.py |
| 已对拍 | 脚本动作 | `SET_MISSION_OBJECTIVE_STATUS` | 732 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_scripts5.py |
| 已对拍 | 脚本动作 | `PLAYER_SET_MONEY` | 345 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_aitower.py |
| 已对拍 | 脚本动作 | `PLAYER_RELATES_PLAYER` | 319 | a2 a4 a5 a7 a9 | tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back |
| 已对拍 | 脚本动作 | `MOVE_TEAM_TO` | 298 | a4 a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_scripts1.py |
| 已对拍 | 脚本动作 | `CREATE_NAMED_ON_TEAM_AT_WAYPOINT` | 291 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_acquire.py |
| 已对拍 | 脚本动作 | `MOVE_CAMERA_TO` | 255 | a1 a2 a4 a6 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_camera.py |
| 已对拍 | 脚本动作 | `NAMED_TRANSFER_OWNERSHIP_PLAYER` | 231 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_invuln.py |
| 已对拍 | 脚本动作 | `INCREMENT_COUNTER` | 229 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过：checks/engine_aimicro.py |
| 已对拍 | 脚本动作 | `PLAYER_SET_MAX_PLAYER_POWER_POINTS` | 206 | a4 a5 a7 | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 已对拍 | 脚本动作 | `NAMED_KILL` | 204 | a4 a5 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_aitargetpick.py |
| 已对拍 | 脚本动作 | `CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT` | 196 | a4 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_ref.py |
| 已对拍 | 脚本动作 | `LINK_MISSION_OBJECTIVE_TO_WAYPOINT` | 194 | a1 a3 a4 a5 a6 a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_scripts5.py |
| 已对拍 | 脚本动作 | `SET_COUNTER` | 171 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过：checks/engine_aidiff.py |
| 已对拍 | 脚本动作 | `PATH_MUSIC_PLAY_EVENT` | 155 | a4 | 只记进时间线（sim.SHOWN）；台上量过：docs/engine/script-semantics.md |
| 已对拍 | 脚本动作 | `DISABLE_INPUT` | 152 | a4 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_scripts3.py |
| 已对拍 | 脚本动作 | `UNIT_AI_TRANSFER_ALL` | 137 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_aidefense.py |
| 已对拍 | 脚本动作 | `ENABLE_INPUT` | 132 | a4 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_scripts3.py |
| 已对拍 | 脚本动作 | `UNIT_TELEPORT_TO_WAYPOINT` | 118 | a4 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_aidefense.py |
| 已对拍 | 脚本动作 | `ATTACK_MOVE_TEAM_TO` | 116 | a1 a3 a5 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过：docs/engine/pathing.md |
| 已对拍 | 脚本动作 | `MAP_REVEAL_PERMANENTLY_AT_WAYPOINT` | 105 | a4 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_vision.py |
| 已对拍 | 脚本动作 | `SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER` | 101 | a4 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_kingref.py |
| 已对拍 | 脚本动作 | `PLAYER_SET_PLAYER_POWER_POINTS` | 95 | a4 a5 a7 | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 已对拍 | 脚本动作 | `MAP_SWITCH_BORDER` | 87 | a1 a2 a3 a4 a5 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_scripts4.py |
| 已对拍 | 脚本动作 | `SKIRMISH_AI_MAKE_BASE` | 82 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_aistate.py |
| 已对拍 | 脚本动作 | `TEAM_ATTACK_NAMED` | 76 | a2 a4 a7 a8 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_reorder.py |
| 已对拍 | 脚本动作 | `SKIRMISH_AI_USE_REPAIRS` | 75 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_aipullback.py |
| 已对拍 | 脚本动作 | `MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT` | 72 | a4 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_vision.py |
| 已对拍 | 脚本动作 | `PLAYER_GIVE_MONEY` | 72 | a4 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_aiskirm.py |
| 已对拍 | 脚本动作 | `UNIT_SET_TEAM` | 72 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_acquire.py |
| 已对拍 | 脚本动作 | `SKIRMISH_AI_USE_REBUILD_SYSTEM` | 67 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_aiswitch.py |
| 已对拍 | 脚本动作 | `PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM` | 59 | a4 | 只记进时间线（sim.SHOWN）；台上量过：docs/engine/script-semantics.md |
| 已对拍 | 脚本动作 | `NAMED_SET_MAX_HEALTH` | 53 | a4 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_missile.py |
| 已对拍 | 脚本动作 | `PLAY_SOUND_EFFECT` | 51 | a4 | 只记进时间线（sim.SHOWN）；台上量过：checks/engine_dialog.py |
| 已对拍 | 脚本动作 | `DECREMENT_COUNTER` | 50 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过：checks/engine_scripts3.py |
| 已对拍 | 脚本动作 | `DISPLAY_COUNTDOWN_TIMER` | 50 | a4 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_scripts4.py |
| 已对拍 | 脚本动作 | `NAMED_RECEIVE_UPGRADE` | 47 | a8 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_invuln.py |
| 已对拍 | 脚本动作 | `HIDE_COUNTDOWN_TIMER` | 43 | a4 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_scripts4.py |
| 已对拍 | 脚本动作 | `SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER` | 29 | a1 a2 a3 a4 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_aiopen.py |
| 已对拍 | 脚本动作 | `TEAM_STOP` | 27 | a4 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_scripts4.py |
| 已对拍 | 脚本动作 | `COUNTER_MATH_COUNTER` | 19 | a1 a2 a3 a6 a7 a9 | 引擎模型核心；台上量过：checks/engine_scripts3.py |
| 已对拍 | 脚本动作 | `UNIT_SET_HEALTH` | 15 | a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_aimicro.py |
| 已对拍 | 脚本动作 | `SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES` | 14 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_aiswitch.py |
| 已对拍 | 脚本动作 | `NAMED_REMOVE_UPGRADE` | 11 | a8 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_invuln.py |
| 已对拍 | 脚本动作 | `TEAM_GUARD_AREA` | 9 | a1 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_scripts4.py |
| 已对拍 | 脚本动作 | `MAP_REVEAL_AT_WAYPOINT` | 8 | a1 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_vision.py |
| 已对拍 | 脚本动作 | `SET_COUNTER_TO_COUNTER` | 8 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过：checks/engine_protocol.py |
| 已对拍 | 脚本动作 | `UNIT_CHANGE_OBJECT_STATUS:UNATTACKABLE` | 7 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_crush.py |
| 已对拍 | 脚本条件 | `FLAG` | 5099 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过：checks/engine_aimicro.py |
| 已对拍 | 脚本条件 | `TIMER_EXPIRED` | 3917 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过：checks/engine_acquire.py |
| 已对拍 | 脚本条件 | `NAMED_DESTROYED` | 922 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_aispecial.py |
| 已对拍 | 脚本条件 | `PLAYER_HAS_OBJECT_COMPARISON` | 628 | a1 a4 a5 a7 | tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back |
| 已对拍 | 脚本条件 | `COUNTER` | 577 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过：checks/engine_aimicro.py |
| 已对拍 | 脚本条件 | `NAMED_INSIDE_AREA` | 413 | a3 a4 a5 a6 a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_bits.py |
| 已对拍 | 脚本条件 | `SKIRMISH_PLAYER_HAS_UNITS_IN_AREA` | 410 | a1 a3 a4 a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_area.py |
| 已对拍 | 脚本条件 | `NAMED_OWNED_BY_PLAYER` | 397 | a4 a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_garrison.py |
| 已对拍 | 脚本条件 | `NAMED_NOT_DESTROYED` | 374 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_crush.py |
| 已对拍 | 脚本条件 | `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA` | 278 | a4 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_aistate.py |
| 已对拍 | 脚本条件 | `NAMED_ATTACKED_BY_PLAYER` | 150 | a4 a5 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_attack.py |
| 已对拍 | 脚本条件 | `UNIT_HEALTH` | 134 | a2 a4 a7 | Sim.act / Sim.cond 有分支；台上量过：checks/engine_air.py |
| 已对拍 | 物体模块 | `Body/ActiveBody` | 790 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_super_the_proton_collider_ends_as_the_bench；例：AlliedAirfield, AlliedAntiAirMissileProjectile |
| 已对拍 | 物体模块 | `Behaviors/AttributeModifierPoolUpdate` | 622 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_super_the_iron_curtain_holds_off_fire_some_23_seconds；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 已对拍 | 物体模块 | `Behaviors/SecondaryDamageTracker` | 617 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_cryo_a_frozen_tank_melts_334_frames_after_the_beam_whatever_the_beam；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 已对拍 | 物体模块 | `Behaviors/CreateObjectDie` | 591 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里有这个名字；台上量过：checks/engine_crush.py；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 已对拍 | 物体模块 | `Behaviors/DestroyDie` | 578 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_destroy_die_a_building_killed_is_dying_one_frame_and_gone；例：AlliedAirfield, AlliedAntiAirMissileProjectile |
| 已对拍 | 物体模块 | `Behaviors/SquishCollide` | 569 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_crush_a_tank_drives_over_a_lower_level_and_leaves_an_equal_one；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryInfantry |
| 已对拍 | 物体模块 | `Behaviors/SlowDeath` | 565 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_slow_death_a_crushed_conscript_lies_127_frames_dying_and_in_its_spot；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 已对拍 | 物体模块 | `Behaviors/ProductionUpdate` | 351 | a1 a2 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_production_pays_as_it_builds_and_comes_out_after_the_door；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | 物体模块 | `Behaviors/BuildingBehavior` | 334 | a1 a2 a4 a5 a6 a7 a8 | tests/test_simbench.py::test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | 物体模块 | `Behaviors/AttributeModifierAuraUpdate` | 311 | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里有这个名字；台上量过：checks/engine_invuln.py；例：CNV_A3StasisZone, HA_Building16_02 |
| 已对拍 | 物体模块 | `Behaviors/FireWeaponWhenDead` | 146 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里有这个名字；台上量过：checks/engine_spawn.py；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 已对拍 | 物体模块 | `AI/AIUpdate` | 136 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_r8_idle_within_sight_walks_up_fires_and_comes_back；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 已对拍 | 物体模块 | `Behaviors/AutoHealBehavior` | 88 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_autoheal_an_apocalypse_mends_two_points_every_7_frames_after_a_15_frame_wait；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryInfantry |
| 已对拍 | 物体模块 | `Behaviors/SpecialPower` | 74 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_super_a_scripts_cast_starts_the_retail_reload；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 已对拍 | 物体模块 | `Behaviors/StructureUnpackUpdate` | 59 | a1 a2 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_power_back_after_the_plant_unpacks；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | 物体模块 | `Behaviors/StructureSellUpdate` | 52 | a1 a2 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | 物体模块 | `Behaviors/AttributeModifierUpgrade` | 22 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里有这个名字；台上量过：checks/engine_invuln.py；例：AlliedAntiStructureShip, AlliedAntiVehicleVehicleTech1 |
| 已对拍 | 物体模块 | `Behaviors/CrushDie` | 22 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_crush_a_tank_drives_over_a_lower_level_and_leaves_an_equal_one；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 已对拍 | 物体模块 | `Behaviors/TechUpgrade` | 2 | a1 a4 a5 a7 | 模拟器代码里有这个名字；台上量过：checks/engine_tech.py；例：AlliedConstructionYard, CNVA4AlliedConstructionYard |
| 已对拍 | 物体模块 | `Behaviors/AssembleStructureSpecialAbilityUpdate` | 1 | a4 | 模拟器代码里有这个名字；台上量过：checks/engine_skill.py；例：CNV_IceEngineer |
| 已对拍 | 物体模块 | `Behaviors/LifetimeUpdate` | 1 | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里有这个名字；台上量过：checks/engine_crush.py；例：CNV_A4IceSeed, CNV_A4IceWall |
| 已对拍 | 物体模块 | `Behaviors/OreMinerBehavior` | 1 | a1 a2 a4 a5 a6 a7 | tests/test_simbench.py::test_mining_pays_8_a_frame_and_a_trip_takes_269；例：AlliedMiner, JapanMiner |
| 已对拍 | 物体模块 | `Behaviors/OreNodeBehavior` | 1 | a1 a2 a4 a5 a6 a7 a9 | tests/test_simbench.py::test_mining_a_second_miner_on_one_node_adds_nothing；例：OreNode |
| 已对拍 | 武器效果 | `DamageNugget` | 183 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里有这个名字；台上量过：checks/engine_clip.py；例：AAAVT1_CommandoPistolWeapon, AAAVT1_JapanAntiVehicleInfantryPlasmaBazooka |
| 已对拍 | 武器效果 | `ProjectileNugget` | 88 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里有这个名字；台上量过：checks/engine_shot.py；例：AAAVT1_AlliedAntiVehicleInfantryMissileLauncher, AAAVT1_JapanInfiltrationShiruken |
| 不涉及 | 脚本动作 | `PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT` | 640 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 不涉及 | 脚本动作 | `MOVIE_PLAY_RADAR` | 433 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 不涉及 | 脚本动作 | `OBJECT_CREATE_RADAR_EVENT` | 254 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 不涉及 | 脚本动作 | `NAMED_FLASH` | 173 | a9 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 不涉及 | 脚本动作 | `NAMED_SHOW_INFOBOX` | 166 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 不涉及 | 脚本动作 | `CAMERA_LETTERBOX_END` | 154 | a4 | 纯表现（名字规则） |
| 不涉及 | 脚本动作 | `CAMPAIGN_CREATE_AUTO_SAVE` | 127 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 不涉及 | 脚本动作 | `UNIT_SET_MODELCONDITION_GENERIC` | 111 | a7 | 纯表现：设模型状态只换画法。原版脚本设的是 SUPPRESSED（a01 摆拍枪战的趴下动作），SDK 数据里读 SUPPRESSED 的只有绘制模块的 ConditionsYes；我们 a7 设的 USER_1 只有自由号的充能画法读 |
| 不涉及 | 脚本动作 | `CAMERA_LETTERBOX_BEGIN` | 104 | a4 | 纯表现（名字规则） |
| 不涉及 | 脚本动作 | `SHOW_MILITARY_CAPTION` | 58 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 不涉及 | 脚本动作 | `SET_COOP_AI_COMMAND_UI_ENABLED` | 24 | a4 | 纯界面：开关玩家给盟友 AI 下令的按钮；模拟器的玩家没有给盟友下令的命令，开关无从起作用（以后加了这个命令再算） |
| 不涉及 | 脚本动作 | `MOVE_CAMERA_TO_NAMED` | 20 | a5 a7 | 纯表现（名字规则）；Sim.act / Sim.cond 有分支 |
| 不涉及 | 物体模块 | `Draws/ScriptedModelDraw` | 1895 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（Draws）；例：AlliedAirfield, AlliedAntiAirMissileProjectile |
| 不涉及 | 物体模块 | `Behaviors/FXListBehavior` | 796 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（名字规则）；例：AlliedAirfield, AlliedAntiAirMissileProjectile |
| 不涉及 | 物体模块 | `Behaviors/ObjectDefectionHelper` | 640 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 没人触发：原版只在 BaseObject 挂一个空的（所以每个物体都有），SageXML 里没有一处 DefectorSpecialPower，脚本动作表里也没有叛变；《将军》里它管"叛变后一段时间不被发现"；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 不涉及 | 物体模块 | `Behaviors/ObjectSMCHelper` | 640 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现：《将军》ObjectSMCHelper 到时清掉"定时模型状态"（UNIT_SET_MODELCONDITION_GENERIC 的秒数），只换画法；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 不涉及 | 物体模块 | `Behaviors/BuildingDestructionBehavior` | 493 | a1 a2 a4 a5 a6 a7 a8 a9 | 纯表现：建筑死后按骨骼放特效、甩碎块（CreationObject 如 AlliedBarracks_Debris：只有画法、寿命和碎片体积，没有身体和武器）、烟尘；例：AlliedAirfield, AlliedBarracks |
| 不涉及 | 物体模块 | `ClientBehaviors/ModelConditionAudioLoopClientBehavior` | 466 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（ClientBehaviors）；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 不涉及 | 物体模块 | `ClientBehaviors/ModelConditionSoundSelectorClientBehavior` | 140 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（ClientBehaviors）；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 不涉及 | 物体模块 | `Draws/DynamicsDraw` | 138 | a4 | 纯表现（Draws）；例：OK_Lantern01 |
| 不涉及 | 物体模块 | `ClientBehaviors/AnimationSoundClientBehavior` | 48 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（ClientBehaviors）；例：AlliedAntiInfantryInfantry, AlliedAntiStructureShip |
| 不涉及 | 物体模块 | `Draws/TruckDraw` | 35 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（Draws）；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryVehicle |
| 不涉及 | 物体模块 | `Behaviors/SubObjectsUpgrade` | 26 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（名字规则）；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 不涉及 | 物体模块 | `Draws/LaserDraw` | 21 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（Draws）；例：AlliedAntiAirVehicleTech1, AlliedAntiStructureVehicle |
| 不涉及 | 物体模块 | `Draws/TracerModelDraw` | 18 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（Draws）；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryVehicle |
| 不涉及 | 物体模块 | `Behaviors/AudioLoopUpgrade` | 1 | a1 a2 a3 a4 a5 a6 a7 | 纯表现（名字规则）；例：SovietAntiVehicleVehicleTech1 |
| 不涉及 | 物体模块 | `ClientBehaviors/UpgradeSoundSelectorClientBehavior` | 1 | a1 a4 a7 | 纯表现（ClientBehaviors）；例：AlliedAntiAirVehicleTech1 |
