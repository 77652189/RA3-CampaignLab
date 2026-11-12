# 我们 9 关用到的脚本、物体模块、武器效果（引擎 A 部分）

由 `experimental/cnv/inventory_levels.py --write` 生成，**别手改**。范围：9 关（`missions/a1.py`～`a9.py`）编出的全部脚本（`parts.merged`，含目标显示脚本）里的动作和条件；地图和任务摆的物体、我们自己的单位、脚本点名的模板，连同模块点名的武器、武器点名的物体（抛射体）和武器，取生效的模块（继承、include、同 id 覆盖）和武器效果。没跟：模块点名的别的物体（多是能变成 / 能装的东西：多功能步兵车的乘客、锤子坦克吸来的车）、物体生成表（死亡碎片、OCL 技能）和命令表（工厂能造什么）。AI 部分（引擎 B）在 [inventory-levels.md](inventory-levels.md)。状态和原版用量取自 [inventory.md](inventory.md)。停止条件①：下表全部已对拍。

**已对拍 132 / 198**（不涉及的不算）。

| 部分 | 已对拍 | 推断 | 未做 | 不涉及 |
|---|---|---|---|---|
| 脚本动作 | 50 | 0 | 0 | 14 |
| 脚本条件 | 12 | 0 | 0 | 0 |
| 物体模块 | 53 | 13 | 47 | 20 |
| 武器效果 | 17 | 3 | 3 | 2 |

按原版用量加权：已对拍 99%，已有（已对拍+推断）99%。

摆了、但原版数据和我们的单位里都找不到的模板（模块没算）：a9 `AlliedFutureTank`。

编出的脚本里有、清单里没有的名字（不算）：`Behaviors/TeleportSpecialAbilityUpdate`、`Behaviors/TeleportToCasterSpecialPower`、`NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT:SpecialPower_CNV_ChronoDeck`、`NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT:SpecialPower_CNV_IceEngineer_Freeze`、`UNIT_CHANGE_OBJECT_STATUS:IMMOBILE`。

| 状态 | 部分 | 项 | 原版用量 | 关 | 说明 |
|---|---|---|---|---|---|
| 未做 | 物体模块 | `Behaviors/Physics` | 143 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | RA3 的 Physics 只有击飞曲线、反弹、落地后倒地/起身、重力倍数（没有 Generals 的 Mass/摩擦/推挤），会动的战役模板全是默认字段（仅 6 个改 GravityMultiplier）。已测：落地后锁 38 帧再走移动令（engine_knock_probe stand / standlate，tests/test_meta_impact.py::test_physics_a_knocked_man_keeps_still_38_frames_after_landing_then_walks_his_order）；人的落点站不住（落水）挪到最近能站的格、按新落点重画曲线（engine_knock_water man / far，tests/test_meta_impact.py::test_physics_p3_a_man_knocked_toward_water_lands_on_the_nearest_cell_he_can_stand_on）；车的落点按 20 取整再加 10、不能落（水）挪到最近的水上格、落点格离水 10 以内落地即死（斜坡本身不致死），落到低处的曲线（engine_knock_water tank / ramp / edge，tests/test_meta_impact.py::test_physics_p3_a_hammer_lands_on_the_plus_10_grid_and_drowns_within_10_of_the_water；门槛 10、搜索格网 INFERRED）；倒地时照样开火、空中下的攻击令保留（engine_knock_probe fire，tests/test_meta_impact.py::test_physics_p4_a_knocked_man_fires_his_order_while_lying_before_he_stands；空中不开火 INFERRED）；出图不死、默认不反弹（台上读过）；未测：落到高处的曲线、冲击太小不击飞的门槛（60 不飞、130 飞）、空中能否开火、坠机重力；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 未做 | 物体模块 | `Behaviors/BezierProjectile` | 6 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 已核（11-08）：模拟器没有这个效果（开火按每秒伤害直接扣血，没有弹体）；例：AlliedAntiAirMissileProjectile, AlliedAntiAirMissileProjectile_Veteran |
| 未做 | 物体模块 | `Behaviors/SubStructureStorageBehavior` | 6 | a1 a4 a5 a6 a7 a9 | 6用量/6模板为三国MCV及海军继承型，模块无专用字段；有效配置没有SubStructureBuild，未找到可生成待存子结构的原版入口；gap：保存/恢复专属读数及合法触发待接口核实，未上台、不登记已对拍，也不据此排除运行时用途；普通展开及COPY_UPGRADES不能归因；见 work/re/e_substorage_e57.md；例：AlliedMCV, JapanMCV |
| 未做 | 物体模块 | `Behaviors/TrackDamage` | 6 | a1 a2 a3 a4 a5 a6 a7 a8 | E69静态核实：6个SDK配置均InstantWeaponsOnly=true，TimeToTrack为0/1/2s；现有expected_damage只接来弹，历史伤害仍gap。与C线瞬发历史接口工单重叠，E暂停独立探针；尚无本模块具名实测回放，不登记已对拍、不改分母；见work/re/e_trackdamage_e69.md；例：AlliedAntiNavalScout, AlliedFighterAircraft |
| 未做 | 物体模块 | `Behaviors/TrackIncomingWeaponFireBehavior` | 6 | a1 a2 a3 a4 a5 a6 a7 a8 | 部分：engine_inform_probe a/off通知记录回放验证录入、30帧窗口、来源与武器匹配删除和过期清理；精确过期边界INFERRED，原版完整调度/历史伤害仍gap，不靠名字命中晋升整项；例：AlliedAntiNavalScout, AlliedFighterAircraft |
| 未做 | 物体模块 | `Behaviors/AttackAssistResponseBehavior` | 5 | a1 a2 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedBaseDefenseAdvanced, SovietBaseDefenseAdvanced |
| 未做 | 物体模块 | `Behaviors/CaptureSpecialAbilityUpdate` | 5 | a1 a2 a3 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedCommandoTech1, AlliedEngineer |
| 未做 | 物体模块 | `Behaviors/EmotionTrackerUpdate` | 5 | a1 a2 a3 a4 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedCommandoTech1, AlliedEngineer |
| 未做 | 物体模块 | `Behaviors/ActivateModuleSpecialPower` | 4 | a1 a2 a4 a6 a7 | 仅在SpecialPowerNugget处理器中识别并拒绝，未实现模块技能执行；例：AlliedAntiStructureVehicle, JapanAntiVehicleVehicleTech1 |
| 未做 | 物体模块 | `Behaviors/ParkingPlaceBehavior` | 4 | a4 a5 a7 a8 | 模拟器代码里没有这个名字；例：AlliedAirfield, AlliedAntiStructureShip |
| 未做 | 物体模块 | `Behaviors/QueueDockBehavior` | 4 | a1 a2 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedRefinery, JapanRefinery |
| 未做 | 物体模块 | `Behaviors/RadarBehavior` | 4 | a4 | 模拟器代码里没有这个名字；例：JapanConstructionYard |
| 未做 | 物体模块 | `Behaviors/AssistedPlacementBehavior` | 3 | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedRefinery, JapanRefinery |
| 未做 | 物体模块 | `Behaviors/HitReactionBehavior` | 3 | a1 a2 a3 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedAntiInfantryInfantry, CNV_Beacon |
| 未做 | 物体模块 | `Behaviors/LoseHealthUpdate` | 3 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里没有这个名字；例：CNV_Liberty, SovietBomberAircraft |
| 未做 | 物体模块 | `Behaviors/MovementSpecialPower` | 3 | a1 a4 a6 a7 | 模拟器代码里没有这个名字；例：JapanAntiVehicleVehicleTech3 |
| 未做 | 物体模块 | `Behaviors/ReturnToProducerSpecialPower` | 3 | a1 a2 a3 a4 a5 a6 a7 a8 | 模拟器代码里没有这个名字；例：AlliedFighterAircraft, SovietFighterAircraft |
| 未做 | 物体模块 | `Behaviors/SecondaryObjectListenerModule` | 3 | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiAirVehicleTech1, AlliedBaseDefense |
| 未做 | 物体模块 | `Behaviors/SlaughterHordeContain` | 3 | a5 a7 a8 | 模拟器代码里没有这个名字；**待核**：台上量过（checks/engine_aipullback.py），可能用别的名字实现了；例：AlliedAntiStructureShip, CNV_Liberty |
| 未做 | 物体模块 | `Behaviors/StealthDetectorUpdate` | 3 | a2 a6 | 已核（11-08）：模拟器没有这个效果（没有反隐）；例：AlliedScoutInfantry |
| 未做 | 物体模块 | `Behaviors/StructurePlacementBehavior` | 3 | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedRefinery, JapanRefinery |
| 未做 | 物体模块 | `Behaviors/AimWeapon` | 2 | a1 a4 a7 a8 a9 | 模拟器代码里没有这个名字；例：AlliedAntiVehicleInfantry, SovietAntiVehicleInfantry |
| 未做 | 物体模块 | `Behaviors/ConvergingLaserState` | 2 | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiStructureVehicle, SovietAntiVehicleVehicleTech1 |
| 未做 | 物体模块 | `Behaviors/NotifyWhenAttackingBehavior` | 2 | a1 a2 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：AlliedBaseDefenseAdvanced, SovietBaseDefenseAdvanced |
| 未做 | 物体模块 | `Behaviors/PowerUpgrade` | 2 | a5 | 模拟器代码里没有这个名字；例：SovietPowerPlant |
| 未做 | 物体模块 | `Behaviors/PrematureDischargeSpecialPower` | 2 | a4 | 模拟器代码里没有这个名字；例：JapanBaseDefenseAdvanced |
| 未做 | 物体模块 | `Behaviors/RecallUnitsSpecialPower` | 2 | a4 a7 | 模拟器代码里没有这个名字；例：AlliedAirfield |
| 未做 | 物体模块 | `Behaviors/SpiderHoleUpdate` | 2 | a4 | 模拟器代码里没有这个名字；例：JapanAntiVehicleInfantry |
| 未做 | 物体模块 | `Behaviors/AssistedPlacementInfoBehavior` | 1 | a1 a2 a4 a5 a6 a7 a9 | 模拟器代码里没有这个名字；例：OreNode |
| 未做 | 物体模块 | `Behaviors/ChargeWeaponUpdate` | 1 | a4 | 模拟器代码里没有这个名字；例：JapanBaseDefenseAdvanced |
| 未做 | 物体模块 | `Behaviors/FireWeaponCollide` | 1 | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：JapanBalloonBomb, SovietAntiVehicleInfantry |
| 未做 | 物体模块 | `Behaviors/GrapplingHookUpdate` | 1 | a1 a3 a4 a6 a7 a9 | 仅engine_grapple a最小消费者诊断；模块派发/拉拽/释放未解释，未实现，不作为已对拍证据；例：SovietAntiVehicleVehicleTech3 |
| 未做 | 物体模块 | `Behaviors/MagneticEffectUpdate` | 1 | a1 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：AlliedAntiNavyShipTech1 |
| 未做 | 物体模块 | `Behaviors/MonitorConditionUpdate` | 1 | a1 a2 a4 a5 a6 a7 | 模拟器代码里没有这个名字；例：JapanMiner |
| 未做 | 物体模块 | `Behaviors/OCLMonitorUpdate` | 1 | a1 a2 a4 a6 a7 | 模拟器代码里没有这个名字；**待核**：台上量过（checks/engine_spnbomb.py），可能用别的名字实现了；例：SovietCommandoTech1 |
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
| 未做 | 武器效果 | `MetaImpactNugget` | 12 | a1 a2 a3 a4 a5 a6 a7 a9 | 剩余复杂写法：延迟、筛选、Arc、Invert等；普通延迟仅解析payload及隔离到期队列，engine_knock_delay碰撞输入174/173→到期204/192；Physics观察/落地相位未解，不晋升整项。ShockWaveSpeed/Cyclonic本轮原版用量为0也未建模。非默认Physics、坡地及V4曲线弹到达仍gap；例：AAAVT1_ShotgunWeapon, ABD_ShotgunWeapon |
| 未做 | 武器效果 | `GrapplingHookNugget` | 1 | a1 a3 a4 a6 a7 a9 | engine_grapple a最小消费者诊断；GrapplingHookUpdate派发/拉拽/释放未解释，显式报告gap；tests/test_grapple_nugget.py守卫直接命中/继承/弹头及原版缓存，不登记已对拍；例：SovietAntiVehicleVehicleTech3Harpoon |
| 未做 | 武器效果 | `InformTargetNugget` | 0 | a3 a7 a8 a9 | 未覆盖的自制或未知武器写法；原版字段分片另行登记；例：CNV_ChronoLag_Shell, CNV_LibertyDrones |
| 推断 | 物体模块 | `Behaviors/InfiltratorContain` | 30 | a1 a2 a4 a5 a6 a7 a8 | ENERGY已按总控11-11决定拆分登记4用量/6模板；本行剩余10种配置30用量/32模板：KILL 1、STEAL_MONEY 3、VISION 5+港口阻断型1、PARALYZE 3、VISION_UNITS飞机2/步兵3/舰船3/车辆4、RESET 5；普通VISION仅engine_infvis a盟军间谍/建造场最小对照：敌方消耗不换主、友军拒入、近处可见而远处及第三方不可见，tests/test_siminfiltrator.py::test_spy_ordinary_vision_as_on_the_bench；约5秒生效延迟/视野半径映射/宿主死亡清理INFERRED；STEAL_MONEY的engine_infmon a两次量到2000转账和后续矿车收入，匿名矿车清除无效、未闭环且暂停；tests/test_siminfiltrator.py::test_spy_refinery_money_as_on_the_bench为严格xfail，未实现该效果；其他模板/间谍、精确时序、持久性/重复进入及其余效果仍gap，不登记整组或整模块已对拍；例：AlliedAirfield, AlliedBarracks |
| 推断 | 物体模块 | `Behaviors/AssignSlavesTargetObjectSpecialPower` | 6 | a2 a4 a5 a7 a8 | 模拟器代码里有这个名字；台上量过（checks/engine_assignslaves.py），没有测试跑这个台子；例：AlliedWarFactory, JapanNavalYard |
| 推断 | 物体模块 | `Behaviors/WallBuilderBehavior` | 6 | a1 a2 a4 a6 a7 a9 | 部分：engine_wallinit:a有/无模块对照10/11/10，仅StartInSecondaryModel默认WALL_SEGMENT初始化；6/6权重保留，建墙/连接/段数上限/生死联动及自定义配置仍gap，未登记完整已对拍；见 work/re/e_wallbuilder_e58.md；例：AlliedWallPiece, JapanWallPiece |
| 推断 | 物体模块 | `Behaviors/CommandSetUpgrade` | 5 | a1 a4 a5 a7 | 模拟器代码里有这个名字；例：AlliedConstructionYard, CNVA4AlliedConstructionYard |
| 推断 | 物体模块 | `Behaviors/PassiveAreaEffectBehavior` | 5 | a3 a4 a7 | E70部分：engine_passivearea a按名回放工程师独立范围治疗；状态开启、40距离同属步兵100%，400距离步兵/60距离车辆/未开启源旁步兵50%，关闭再扣血后四路50%。仅单源同属步兵稳定平台，SDK每秒10%逐帧积分和调查时序INFERRED；精确帧/叠加/跨玩家关系/自身受益/附着无人机仍gap，不登记整项已对拍；tests/test_simpassivearea.py；见work/re/e_passive_e70.md；例：AlliedEngineer, CNV_IceEngineer |
| 推断 | 物体模块 | `Behaviors/AutoDepositUpdate` | 4 | a1 a4 a5 a7 | 模拟器代码里有这个名字；例：OilDerrick |
| 推断 | 物体模块 | `Behaviors/SpecialAbilityUpdate` | 4 | a1 a4 a6 a7 | 模拟器代码里有这个名字；例：JapanAntiInfantryInfantry, JapanAntiVehicleVehicleTech1 |
| 推断 | 物体模块 | `Behaviors/TechUpgradeReceiver` | 4 | a2 a4 a5 a7 a8 | 模拟器代码里有这个名字；例：AlliedAirfield, AlliedBarracks |
| 推断 | 物体模块 | `Behaviors/AttachUpdate` | 3 | a1 a2 a4 a5 a6 a7 a9 | 部分：engine_attach a验证瞬移/跟随/父子状态；engine_attach_parent a验证简单模块脚本杀父后子活/清理链接，NO_COLLISIONS读数差异为严格xfail；原版模块死亡前无稳定链接，不推广死亡规则；子死/直接删除/维修/吸血/解除/自主扫描仍gap；例：AlliedCommandoTech1, SovietScoutVehicle |
| 推断 | 物体模块 | `Behaviors/LiftObjectUpdate` | 3 | a1 a2 a4 a6 a7 | 部分：显式TimeIncrement/MaxTimeLifted的开火者举升表计时接口；tests/test_lift_nugget.py回放engine_lift a状态计数，逐帧计时来自模块证据、未上台逐帧量表；垂直运动/死亡/飞机/落地武器/清位仍gap，落地清位INFERRED，不登记整模块已对拍；例：AlliedAntiAirVehicleTech1, AlliedBaseDefense |
| 推断 | 物体模块 | `Behaviors/EngineerContain` | 1 | a4 a5 a8 | 总控11-11授权工程师组收尾、不再上台；已测通用三国63用量及三国ALLIES6用量分别登记；gap：日本单人ALLIES型TH_TombBuilding02为1用量/1模板，筛选与维修未对拍；间接可达桥头堡为0用量/10模板，桥修复未对拍；本行共1用量/11模板。ReplaceWith和ObjectStatusToSet无原版显式声明；精确进入帧仍INFERRED，不登记整模块已对拍（tests/test_simengineer.py、tests/test_inventory_contain.py、tests/test_inventory_engineer.py）；例：CNVA4AlliedBarracks, CNVA4AlliedConstructionYard |
| 推断 | 物体模块 | `Behaviors/FireWeaponUpdate` | 1 | a1 a2 a4 a5 a6 a7 | 部分：simunits.ocl_round 把召出物的 FireWeaponNugget + LifetimeUpdate 折成伤害，不模拟召出物本身；例：SovietHeavyAntiVehicleInfantry |
| 推断 | 物体模块 | `Behaviors/GarrisonContain` | 1 | a6 a7 | simgarrison 同一套规则（不可争夺）；没单独上台对拍；例：AlliedBaseDefense |
| 推断 | 武器效果 | `ActivateLiftObjectNugget` | 6 | a1 a2 a4 a6 a7 | 部分：按模块证据实现开火者举升表，trunc(TimeIncrement×15)逐发累加、续期封顶MaxTimeLifted、逐帧递减释放；Lifetime不参与，释放不清LIFTED；tests/test_lift_nugget.py按名回放engine_lift a旧读数一致，landing因落地清位未实现strict xfail；落地清位INFERRED，垂直运动/死亡/飞机/弹体/复杂筛选仍gap，不登记整项已对拍；例：AAAVT1_JapanCommandoTech1PsyonicAntiAirCrush, AAAVT1_JapanCommandoTech1PsyonicCrush |
| 推断 | 武器效果 | `SpecialPowerNugget` | 6 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 部分：engine_spn a实测自身ARMOR派发、缺模块/类型过滤；engine_spng a / engine_spngp a实测单个OBJECT/PLAYER升级门槛读取施法者/其玩家；engine_spnret a原版守护者普通/高科技保留与去除此Nugget均74/69%血，增伤由AttributeModifierNugget提供，无活动消费者的PaintTarget模块无附加效果；tests/test_special_power_nugget.py回放；engine_spnscr a原版干扰保留/去除SPN首伤均延后但最终同80%，到期无条件清除脚本同名状态位接口已覆盖；原版筛选最小派发接口已覆盖（类别/气球模板/铁幕排除），攻击订单恢复未解释，未登记完整消费者；engine_spndisguise a原版/删SPN/删变装模块/脚本正对照1111/1110/1110/1111已按名回放，接通直接命中DISGUISED位，身份/外观/索敌/换目标/取消仍gap；仅直接单发，OCL/其他模块、未知类型/多重升级未接通，不登记整项已对拍；例：AlliedAntiVehicleVehicleTech1TargetPainter, CNV_DeckSendTrigger |
| 推断 | 武器效果 | `AttachNugget` | 4 | a1 a2 a4 a5 a6 a7 a9 | 部分：engine_attach a实测直接单发、父子状态、随父移动及目标状态/类型拒绝；仅零半径简单模块，原版复杂筛选/维修/吸血/解除/弹体未接通，不登记整项已对拍；例：AlliedCommandoAttachWeapon, SovietScoutVehicleMeleeAttachWeapon |
| 已对拍 | 脚本动作 | `SET_MILLISECOND_TIMER` | 4153 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | 脚本动作 | `SET_FLAG` | 4105 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | 脚本动作 | `ALLOW_DISALLOW_ONE_BUILDING` | 3466 | a4 a5 a7 | tests/test_simbench.py::test_a_ban_holds_the_queue_and_does_not_cancel |
| 已对拍 | 脚本动作 | `LINK_MISSION_OBJECTIVE_TO_OBJECT` | 950 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts5.py |
| 已对拍 | 脚本动作 | `NAMED_DELETE` | 908 | a2 a4 a5 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attach.py |
| 已对拍 | 脚本动作 | `SET_MISSION_OBJECTIVE_STATUS` | 732 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts5.py |
| 已对拍 | 脚本动作 | `PLAYER_SET_MONEY` | 345 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aitower.py |
| 已对拍 | 脚本动作 | `PLAYER_RELATES_PLAYER` | 319 | a2 a4 a5 a7 a9 | tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back |
| 已对拍 | 脚本动作 | `MOVE_TEAM_TO` | 298 | a4 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aixfer.py |
| 已对拍 | 脚本动作 | `CREATE_NAMED_ON_TEAM_AT_WAYPOINT` | 291 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | 脚本动作 | `MOVE_CAMERA_TO` | 255 | a1 a2 a4 a6 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_camera.py |
| 已对拍 | 脚本动作 | `NAMED_TRANSFER_OWNERSHIP_PLAYER` | 231 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_invuln.py |
| 已对拍 | 脚本动作 | `INCREMENT_COUNTER` | 229 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | 脚本动作 | `PLAYER_SET_MAX_PLAYER_POWER_POINTS` | 206 | a4 a5 a7 | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 已对拍 | 脚本动作 | `NAMED_KILL` | 204 | a4 a5 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aitargetpick.py |
| 已对拍 | 脚本动作 | `CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT` | 196 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_ref.py |
| 已对拍 | 脚本动作 | `LINK_MISSION_OBJECTIVE_TO_WAYPOINT` | 194 | a1 a3 a4 a5 a6 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts5.py |
| 已对拍 | 脚本动作 | `SET_COUNTER` | 171 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过、测试对拍：checks/engine_aidiff.py |
| 已对拍 | 脚本动作 | `DISABLE_INPUT` | 152 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts3.py |
| 已对拍 | 脚本动作 | `UNIT_AI_TRANSFER_ALL` | 137 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aidefense.py |
| 已对拍 | 脚本动作 | `ENABLE_INPUT` | 132 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts3.py |
| 已对拍 | 脚本动作 | `UNIT_TELEPORT_TO_WAYPOINT` | 118 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aidefense.py |
| 已对拍 | 脚本动作 | `ATTACK_MOVE_TEAM_TO` | 116 | a1 a3 a5 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_wayatk.py |
| 已对拍 | 脚本动作 | `MAP_REVEAL_PERMANENTLY_AT_WAYPOINT` | 105 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 已对拍 | 脚本动作 | `SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER` | 101 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_ref.py |
| 已对拍 | 脚本动作 | `PLAYER_SET_PLAYER_POWER_POINTS` | 95 | a4 a5 a7 | tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule |
| 已对拍 | 脚本动作 | `MAP_SWITCH_BORDER` | 87 | a1 a2 a3 a4 a5 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 已对拍 | 脚本动作 | `SKIRMISH_AI_MAKE_BASE` | 82 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiomove.py |
| 已对拍 | 脚本动作 | `TEAM_ATTACK_NAMED` | 76 | a2 a4 a7 a8 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_reorder.py |
| 已对拍 | 脚本动作 | `SKIRMISH_AI_USE_REPAIRS` | 75 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aipullback.py |
| 已对拍 | 脚本动作 | `MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT` | 72 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 已对拍 | 脚本动作 | `PLAYER_GIVE_MONEY` | 72 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiskirm.py |
| 已对拍 | 脚本动作 | `UNIT_SET_TEAM` | 72 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | 脚本动作 | `SKIRMISH_AI_USE_REBUILD_SYSTEM` | 67 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiswitch.py |
| 已对拍 | 脚本动作 | `NAMED_SET_MAX_HEALTH` | 53 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_maxhealth.py |
| 已对拍 | 脚本动作 | `PLAY_SOUND_EFFECT` | 51 | a4 | 只记进时间线（sim.SHOWN）；台上量过、测试对拍：checks/engine_dialog.py |
| 已对拍 | 脚本动作 | `DECREMENT_COUNTER` | 50 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过、测试对拍：checks/engine_scripts3.py |
| 已对拍 | 脚本动作 | `DISPLAY_COUNTDOWN_TIMER` | 50 | a4 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 已对拍 | 脚本动作 | `NAMED_RECEIVE_UPGRADE` | 47 | a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_invuln.py |
| 已对拍 | 脚本动作 | `HIDE_COUNTDOWN_TIMER` | 43 | a4 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 已对拍 | 脚本动作 | `SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER` | 29 | a1 a2 a3 a4 a6 a7 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiopen.py |
| 已对拍 | 脚本动作 | `TEAM_STOP` | 27 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 已对拍 | 脚本动作 | `COUNTER_MATH_COUNTER` | 19 | a1 a2 a3 a6 a7 a9 | 引擎模型核心；台上量过、测试对拍：checks/engine_attach.py |
| 已对拍 | 脚本动作 | `UNIT_SET_HEALTH` | 15 | a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | 脚本动作 | `SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES` | 14 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aiswitch.py |
| 已对拍 | 脚本动作 | `NAMED_REMOVE_UPGRADE` | 11 | a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_invuln.py |
| 已对拍 | 脚本动作 | `TEAM_GUARD_AREA` | 9 | a1 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_scripts4.py |
| 已对拍 | 脚本动作 | `MAP_REVEAL_AT_WAYPOINT` | 8 | a1 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_vision.py |
| 已对拍 | 脚本动作 | `SET_COUNTER_TO_COUNTER` | 8 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过、测试对拍：checks/engine_contained.py |
| 已对拍 | 脚本动作 | `UNIT_CHANGE_OBJECT_STATUS:UNATTACKABLE` | 7 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attach.py |
| 已对拍 | 脚本条件 | `FLAG` | 5099 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | 脚本条件 | `TIMER_EXPIRED` | 3917 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过、测试对拍：checks/engine_acquire.py |
| 已对拍 | 脚本条件 | `NAMED_DESTROYED` | 922 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_immortal.py |
| 已对拍 | 脚本条件 | `PLAYER_HAS_OBJECT_COMPARISON` | 628 | a1 a4 a5 a7 | tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back |
| 已对拍 | 脚本条件 | `COUNTER` | 577 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 引擎模型核心；台上量过、测试对拍：checks/engine_aimicro.py |
| 已对拍 | 脚本条件 | `NAMED_INSIDE_AREA` | 413 | a3 a4 a5 a6 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aixfer.py |
| 已对拍 | 脚本条件 | `SKIRMISH_PLAYER_HAS_UNITS_IN_AREA` | 410 | a1 a3 a4 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_area.py |
| 已对拍 | 脚本条件 | `NAMED_OWNED_BY_PLAYER` | 397 | a4 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_engineer.py |
| 已对拍 | 脚本条件 | `NAMED_NOT_DESTROYED` | 374 | a4 a5 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attach.py |
| 已对拍 | 脚本条件 | `PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA` | 278 | a4 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_aistate.py |
| 已对拍 | 脚本条件 | `NAMED_ATTACKED_BY_PLAYER` | 150 | a4 a5 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_attack.py |
| 已对拍 | 脚本条件 | `UNIT_HEALTH` | 134 | a2 a4 a7 | Sim.act / Sim.cond 有分支；台上量过、测试对拍：checks/engine_air.py |
| 已对拍 | 物体模块 | `Body/PropBody` | 1443 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench_c.py::test_prop_body_no_health_a_kill_leaves_the_street_and_topples_the_tree_and_lantern_at_the_bench_frames；例：AlliedAntiGroundAircraftMissileProjectile_Veteran, AlliedAntiInfantryVehicleTorpedoProjectile |
| 已对拍 | 物体模块 | `Body/ActiveBody` | 790 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_super_the_proton_collider_ends_as_the_bench；例：AlliedAirfield, AlliedAntiAirMissileProjectile |
| 已对拍 | 物体模块 | `Behaviors/AttributeModifierPoolUpdate` | 622 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_super_the_iron_curtain_holds_off_fire_some_23_seconds；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 已对拍 | 物体模块 | `Behaviors/SecondaryDamageTracker` | 617 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_cryo_a_frozen_tank_melts_334_frames_after_the_beam_whatever_the_beam；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 已对拍 | 物体模块 | `Behaviors/CreateObjectDie` | 591 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_crush.py；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 已对拍 | 物体模块 | `Behaviors/DestroyDie` | 578 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_destroy_die_a_building_killed_is_dying_one_frame_and_gone；例：AlliedAirfield, AlliedAntiAirMissileProjectile |
| 已对拍 | 物体模块 | `Behaviors/SquishCollide` | 569 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_crush_a_tank_drives_over_a_lower_level_and_leaves_an_equal_one；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryInfantry |
| 已对拍 | 物体模块 | `Behaviors/SlowDeath` | 565 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_slow_death_a_crushed_conscript_lies_127_frames_dying_and_in_its_spot；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 已对拍 | 物体模块 | `Behaviors/ProductionUpdate` | 351 | a1 a2 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_production_pays_as_it_builds_and_comes_out_after_the_door；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | 物体模块 | `Behaviors/ToppleUpdate` | 347 | a4 | tests/test_simbench_c.py::test_topple_the_five_props_disappear_at_the_bench_frames_without_ever_dying；例：OK_Lantern01 |
| 已对拍 | 物体模块 | `Behaviors/BuildingBehavior` | 334 | a1 a2 a4 a5 a6 a7 a8 | tests/test_simbench.py::test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | 物体模块 | `Behaviors/AttributeModifierAuraUpdate` | 311 | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_invuln.py；例：CNV_A3StasisZone, HA_Building16_02 |
| 已对拍 | 物体模块 | `Behaviors/ContestableGarrisonContain` | 305 | a4 | tests/test_simbench_c.py::test_garrison_script_entry_skips_room_and_relation_owner_follows_and_damage_or_kill_ejects_alive_at_the_bench；例：HA_Building16_02, HA_Building16_03 |
| 已对拍 | 物体模块 | `Behaviors/InvisibilityBehavior` | 305 | a4 a5 a9 | tests/test_simbench_c.py::test_invisibility_behavior_a_house_given_garrison_can_stealth_by_script_is_shot_like_a_plain_one；例：CNV_A4IceDisplay, CNV_A4IceSeed |
| 已对拍 | 物体模块 | `Behaviors/FireWeaponWhenDead` | 146 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench_c.py::test_fire_weapon_when_dead_a_scripted_kill_blows_the_mig_and_the_guardian_beside_it；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 已对拍 | 物体模块 | `Behaviors/EnableDynamicsCollide` | 137 | a4 | tests/test_simbench_c.py::test_enable_dynamics_collide_a_lantern_without_it_is_crushed_and_gone_at_the_same_frames；例：OK_Lantern01 |
| 已对拍 | 物体模块 | `AI/AIUpdate` | 136 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_r8_idle_within_sight_walks_up_fires_and_comes_back；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 已对拍 | 物体模块 | `Behaviors/StancesBehavior` | 108 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench_c.py::test_stance_hold_fire_stops_a_standing_attack_order；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 已对拍 | 物体模块 | `Behaviors/AutoHealBehavior` | 88 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_autoheal_an_apocalypse_mends_two_points_every_7_frames_after_a_15_frame_wait；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryInfantry |
| 已对拍 | 物体模块 | `Behaviors/LevelUpUpgrade` | 88 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench_c.py::test_levelup_creation_grants_reach_heroic_only_after_three_distinct_triggers；已测范围：engine_levelup a创建升级触发升阶、重复持有不升级；b移除创建升级保留等级，老兵创建升级移除重给可再次升阶，英雄位0/0/0/1→0/0/1/1→0/1/1/1；c独立精英/英雄创建升级各自移除重给两次，首次仍0/0/0/1、第二次0/1/1/1；engine_leveldamage a等级DAMAGE_MULT125保持到精英/英雄，单发血量47/34/34/17；engine_levelhealth a满血升级HEALTH_MULT125保持到英雄，100脚本伤害同帧冻结80/80/84/84；b残血升精英保留血量比例50/80/50/20，再扣100血为30/64/34/4，当前和最大血量均乘1.25，simlevel及test_simbench_c重放；engine_levelrange a原版幻影普通炮125、英雄炮150叠加RANGE125%为187.5，220距离仅英雄命中、260距离均未命中，四路100/10100/100/10100→100/10017/100/10100，离位异常均0；engine_levelrate a幻影普通/直接英雄武器/创建英雄/创建精英三段周期25/25/20/25帧，最终血量84/80/68/80，ROF不增加单发伤害；仅此离散单发炮配置已量，射速分段取整/其他武器仍未对拍；engine_levelshroud a原版幻影基础揭雾500、创建英雄SHROUD_CLEARING125%预测625，580/750距离普通/英雄四路1/1/1/1→1/111/1/101，近点始终可见且无离位；仅此模板配置已量，精确边界未对拍；engine_levelvision a原版幻影普通/创建英雄对小包围体工程师240/310距离ENEMY_SIGHTED四路11/11/11/11→0/0/0/0→0/101/0/100，近点在正式窗口前删除且无离位，支持VISION125按1.25倍率为250的预测；仅脚本范围查询已量，精确边界/自动索敌未对拍；gap：英雄自动索敌、精确射程/揭雾/视野边界、射速分段取整/其他武器、其余模板/等级属性、经验成长、额外上限及Permanent=true未对拍；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证；这些分支与已测效果共用模板，不能按SPLIT_STILL互斥拆分用量；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryInfantry |
| 已对拍 | 物体模块 | `Behaviors/RunOffMapBehavior` | 88 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench_c.py::test_run_off_map_the_peacekeeper_is_gone_64_and_304_frames_after_the_order_never_dying；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryInfantry |
| 已对拍 | 物体模块 | `Behaviors/WeaponSetUpdate` | 82 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench_c.py::test_weapon_set_the_status_picks_the_gun_molotov_under_the_toggle_and_the_painter_does_no_harm；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryInfantry |
| 已对拍 | 物体模块 | `Behaviors/SpecialPower` | 74 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_super_a_scripts_cast_starts_the_retail_reload；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 已对拍 | 物体模块 | `Behaviors/DynamicsUpdate` | 69 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench_c.py::test_dynamics_update_a_hammer_without_it_crushes_and_goes_round_as_the_retail_one；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryVehicle |
| 已对拍 | 物体模块 | `Behaviors/RepairUpdate` | 66 | a1 a2 a4 a5 a6 a7 a8 a9 | tests/test_simrepair_ai.py::test_ai_repair_funded_and_zero_credit_final_readings；repairai a/repairq a/repairt a/repairzero a按名重放：开局足额资金、默认1000HP/800造价电厂初始50%/25%/75%血约10HP/s修满、实扣100/225/25，费用按缺血比例平方；零资金无经济不修；tests/test_simrepair_ai.py。只支持已测配置，完整配置门禁保留；gap：玩家入口、废墟维修、受伤停修、其他初始血量/造价/速率及资金耗尽未测；AI启动相位INFERRED；按总控11-11三切片收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | 物体模块 | `Behaviors/StatusBitsUpgrade` | 66 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench_c.py::test_status_bits_upgrade_the_heroic_grant_sets_weapon_upgraded_and_a_removal_clears_it；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryVehicle |
| 已对拍 | 物体模块 | `Behaviors/EngineerContain:通用三国` | 63 | a1 a2 a4 a5 a6 a7 a8 | tests/test_simengineer.py::test_engineer_soviet_japan_captures_as_on_the_bench；已测范围：engine_engineer a/b/c/d普通进入，三国工程师中立/敌方半血电厂占领并消耗、友军半血修满并消耗、满血拒入且存活；按完整配置匹配登记63用量/87模板；gap：精确进入帧仍INFERRED；日本单人ALLIES和桥配置保留在未对拍残余行，不借本组登记；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | 物体模块 | `Behaviors/StructureUnpackUpdate` | 59 | a1 a2 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_power_back_after_the_plant_unpacks；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | 物体模块 | `Behaviors/StructureSellUpdate` | 52 | a1 a2 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames；例：AlliedAirfield, AlliedBarracks |
| 已对拍 | 物体模块 | `Behaviors/ToggleStatusSpecialAbilityUpdate` | 27 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench_c.py::test_toggle_status_a_press_moves_to_the_next_state_unpack_delays_it_and_a_held_state_takes_no_press；例：AlliedAntiInfantryInfantry, AlliedAntiNavyShipTech1 |
| 已对拍 | 物体模块 | `Behaviors/AttributeModifierUpgrade` | 22 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_invuln.py；例：AlliedAntiStructureShip, AlliedAntiVehicleVehicleTech1 |
| 已对拍 | 物体模块 | `Behaviors/CrushDie` | 22 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench.py::test_crush_a_tank_drives_over_a_lower_level_and_leaves_an_equal_one；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 已对拍 | 物体模块 | `Behaviors/SuppressionUpdate` | 22 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench_c.py::test_suppression_samples_entry_refresh_and_expiry_at_the_four_probe_readings；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 已对拍 | 物体模块 | `Behaviors/QueueProductionExitUpdate` | 19 | a1 a2 a4 a5 a6 a7 a8 | tests/test_simbench.py::test_a_new_unit_stops_beyond_the_natural_rally_point_as_the_bench；例：AlliedBarracks, AlliedConstructionYard |
| 已对拍 | 物体模块 | `Behaviors/ReplaceSelfSpecialAbility` | 18 | a1 a2 a4 a5 a6 a7 a9 | tests/test_simbench.py::test_a_yard_packs_into_its_mcv_at_once_and_the_mcv_stands_before_it_drives；三类用法都上台：基地车 / 帝国蛋到点展开（engine_unpack mcv / egg，名字和血量比例跟过去）、三国建造场收起（engine_pack a/s/j，按下当帧就是基地车，先站 2 秒 + 约 14 帧再开，14 帧是拟合 INFERRED）；gap：盟军矿车、苏联勘探车的展开没上台，其余 8 种蛋按同一机制推；例：AlliedConstructionYard, AlliedMCV |
| 已对拍 | 物体模块 | `Behaviors/WeaponFireSpecialAbilityUpdate` | 16 | a1 a2 a4 a5 a6 a7 | tests/test_simbench.py::test_a_weapon_fire_ability_goes_off_after_its_unpack_and_holds_the_caster_through_its_pack；例：AlliedAntiNavalScout, AlliedAntiStructureShip |
| 已对拍 | 物体模块 | `Behaviors/BridgeBuilder` | 14 | a1 a4 a7 | tests/test_simbridgebuilder.py::test_bridgebuilder_counts_short_and_long_retail_bridges；已测范围：engine_bridgebuilder:a已量HB_Bridge_02长度270/700，EndCap/EndCap2/CenterPiece/CenterPieceB/GateHouse数量1/1/1/0/2及1/1/2/2/2；engine_bridgebuilder_b:b已量原版HB桥首16+Bridge1a桥尾32混合构型，两长度HB数量不变、五类Bridge1物件均0；tests/test_simbridgebuilder.py按名核计数模型与读数编码，simunits仅有限数量模型；gap：HV_Bridge_01等其他桥型/配置/长度、世界物体生成/位置、通行、损毁、共享血量与维修未建模；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母；例：HB_Bridge_02 |
| 已对拍 | 物体模块 | `Body/ManagerBody` | 14 | a1 a4 a7 | tests/test_simmanagerbody.py::test_manager_body_script_damage_preserves_retail_bridge_proxy；已测范围：engine_managerbody a/b原版HB_Bridge_02，270/700长度整体代理脚本伤害200后均80%、致命量后1%且存活，tests/test_simmanagerbody.py按名重放；gap：有效HP取CenterPiece及内部1%下限映射仍INFERRED，内部最大血量/伤害转发/显示下限待核；HV_Bridge_01等其他模板/配置、桥段共享血量/损毁/维修未对拍；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母；例：HB_Bridge_02 |
| 已对拍 | 物体模块 | `AI/JetAIUpdate` | 13 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simjet.py::test_jet_vindicator_first_entry_frame_matches_bench；已测范围：engine_jet:a/b原版维和轰炸机静止正东起步，距离1200/600，首次入框97/47，框内1且血100%；simjet按逐帧位置实现首步2.7（机制INFERRED）、每帧+0.8至12；tests/test_simjet.py按名回放两种时钟均97/47，并核启动位置和入框112/62帧；未新增上台；gap：其他配置/机型、重复命令/转弯、MinSpeed、起飞高度/盘旋/降落、机场/跑道/停车位、返场补弹/耗尽伤害及攻击状态，配置与动作门禁保留；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母；例：AlliedBomberAircraft, AlliedFighterAircraft |
| 已对拍 | 物体模块 | `Behaviors/TransportContain` | 13 | a1 a2 a4 a5 a7 a9 | tests/test_simbench.py::test_transport_a_team_put_in_instantly_skips_the_room_and_the_relation_and_rides_along；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryVehicle |
| 已对拍 | 物体模块 | `Behaviors/SpawnBehavior` | 10 | a1 a2 a4 a5 a6 a7 a8 | tests/test_simspawn.py::test_spawn_initial_burst_and_parent_kill_delete_match_named_bench；已测范围：engine_spawn:spawn开局3架及母体死亡/删除清随从；engine_spawn_refill:refill两架分别死亡10秒后补回（tests/test_simspawn.py显式预置贴车位置）；engine_spawn_power:power缺电及复电期间总数/厂旁均3；gap：自主维修飞行、子体直接删除、真正禁用/占领、缺电时死亡补充、展开时机及其他完整配置，生成位置和秒内相位INFERRED；按总控11-11三切片收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母；例：AlliedAirfield, AlliedRefinery |
| 已对拍 | 物体模块 | `Behaviors/EjectPassengersSpecialAbilityUpdate` | 7 | a2 a5 a9 | tests/test_simbench.py::test_transport_the_man_cannon_throws_one_every_half_second_and_a_killed_transport_kills_its_men；例：AlliedBomberAircraft, CNV_Burrower |
| 已对拍 | 物体模块 | `Behaviors/EngineerContain:三国ALLIES` | 6 | a1 a2 a4 a5 a6 a7 a9 | tests/test_simengineer.py::test_engineer_allied_defence_refusal_soviet_japan_as_on_the_bench；已测范围：engine_engineer a/e/f普通进入，三国工程师友军半血防御修满并消耗、满血及敌方拒入且存活，目标归属不变；按完整配置匹配登记6用量/7模板；gap：精确进入帧仍INFERRED；日本单人ALLIES和桥配置保留在未对拍残余行，不借本组登记；例：AlliedBaseDefenseAdvanced, JapanBaseDefenseAdvanced |
| 已对拍 | 物体模块 | `Behaviors/OCLSpecialPower` | 6 | a1 a2 a4 a6 a7 | tests/test_simocl.py::test_iron_curtain_zero_count_ocl_reference；总控第四切片按已测边界收尾：tests/test_simocl.py具名回放engine_oclcurtain/engine_oclnone/engine_oclwrong a，铁幕宿主匹配模块才保护并记事件，删除/改绑模块无保护/事件；engine_oclempty a空声明无保护且事件1；engine_oclcopy a完整原版载荷改名仍保护100/100且事件1；engine_oclzero a仅外层Count=0无保护且事件1。只闭合铁幕派发和零数量不保护边界，未测生成数量/通用生成；其他非零数量/载荷/超武、位置/过滤、按钮/冷却仍gap，继承、等价空声明及格式等价INFERRED，不表示全模块全字段验证；见 work/re/e_ocl_e65.md；例：SovietCommandoTech1 |
| 已对拍 | 物体模块 | `Behaviors/InfiltratorContain:ENERGY` | 4 | a2 a4 a5 a6 a7 a8 | tests/test_siminfiltrator.py::test_spy_power_plant_as_on_the_bench；总控11-11授权按配置组收尾：engine_infiltrator a/b/c/d按名字重放，盟军间谍对盟/苏/帝普通电厂及帝国忍者对盟军电厂，敌方进入者消耗、建筑满血不换主、100电量停电约20秒并恢复，友军拒入且存活；gap：其他电量/苏联超级电厂、重复进入续期、精确时序和默认状态分支仍未对拍，不表示全字段全模板已验证；例：AlliedPowerPlant, JapanPowerPlant |
| 已对拍 | 物体模块 | `Behaviors/SpecialDisguiseUpdate` | 4 | a1 a4 a6 a7 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_spndisguise.py；例：AlliedAntiVehicleVehicleTech3, JapanLightTransportVehicle |
| 已对拍 | 物体模块 | `Behaviors/InvisibilityBroadcastUpdate` | 2 | a1 a4 a6 a7 | tests/test_simbench_c.py::test_invisibility_broadcast_the_aura_holds_its_guardian_at_full_health_and_the_control_dies；例：AlliedAntiVehicleVehicleTech3 |
| 已对拍 | 物体模块 | `Behaviors/TechUpgrade` | 2 | a1 a4 a5 a7 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_tech.py；例：AlliedConstructionYard, CNVA4AlliedConstructionYard |
| 已对拍 | 物体模块 | `Behaviors/AssembleStructureSpecialAbilityUpdate` | 1 | a4 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_skill.py；例：CNV_IceEngineer |
| 已对拍 | 物体模块 | `Behaviors/LifetimeUpdate` | 1 | a1 a2 a3 a4 a5 a6 a7 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_crush.py；例：CNV_A4IceSeed, CNV_A4IceWall |
| 已对拍 | 物体模块 | `Behaviors/LinearDamageUpdate` | 1 | a1 a2 a4 a6 a7 | tests/test_simsweep.py::test_sweep_the_line_walks_out_and_a_stop_does_not_cut_it_at_the_bench_frames；例：AlliedAntiNavalScout |
| 已对拍 | 物体模块 | `Behaviors/OreMinerBehavior` | 1 | a1 a2 a4 a5 a6 a7 | tests/test_simbench.py::test_mining_pays_8_a_frame_and_a_trip_takes_269；例：AlliedMiner, JapanMiner |
| 已对拍 | 物体模块 | `Behaviors/OreNodeBehavior` | 1 | a1 a2 a4 a5 a6 a7 a9 | tests/test_simbench.py::test_mining_a_second_miner_on_one_node_adds_nothing；例：OreNode |
| 已对拍 | 武器效果 | `DamageNugget` | 183 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 模拟器代码里有这个名字；台上量过、测试对拍：checks/engine_clip.py；例：AAAVT1_CommandoPistolWeapon, AAAVT1_JapanAntiVehicleInfantryPlasmaBazooka |
| 已对拍 | 武器效果 | `ProjectileNugget` | 88 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench_c.py::test_projectile_nugget_flight_uses_retail_shell_speed_and_resolved_warhead；例：AAAVT1_AlliedAntiVehicleInfantryMissileLauncher, AAAVT1_JapanInfiltrationShiruken |
| 已对拍 | 武器效果 | `SuppressionNugget` | 64 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench_c.py::test_suppression_samples_entry_refresh_and_expiry_at_the_four_probe_readings；例：AAAVT1_AlliedAntiVehicleInfantryMissileLauncher, AAAVT1_CommandoPistolWeapon |
| 已对拍 | 武器效果 | `InformTargetNugget:默认系数目标通知` | 47 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_inform_ai.py::test_inform_incoming_table_drives_miner_armor_from_engine_inform_probe；仅默认Min=.85/Max=1.15的目标通知→来弹表/矿车预计伤害开甲；engine_inform_probe a/off录入302、hit377、exp404、删除389，347帧入窗。半径/历史/海啸/忍者及完整AI调度不在本登记范围，完整脚本仍xfail；例：AlliedAntiInfantryVehicleTorpedoLauncher, AlliedAntiInfantryVehicleTorpedoLauncherForBridges |
| 已对拍 | 武器效果 | `WeaponOCLNugget` | 26 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench_c.py::test_weapon_ocl_lifetime_damage_reads_the_fire_delay_before_counting_updates；例：AlliedAntiStructureAttackDrones, AlliedAntiStructureSolarTargeter |
| 已对拍 | 武器效果 | `InformTargetNugget:Max1.6目标通知` | 22 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_inform_ai.py::test_inform_max_launch_matches_engine_inform_max_observed_deadline；仅Min=.85/Max=1.6目标通知→来弹表；engine_inform_max a单变量对照录入302、hit377不变、exp444（默认404）、受伤389删除，矿车提前开甲。自然过期清理边界/半径/历史/海啸/忍者/完整AI调度未对拍，完整脚本仍xfail；例：AAAVT1_AlliedAntiVehicleInfantryMissileLauncher, ABD_AlliedAntiVehicleInfantryMissileLauncher |
| 已对拍 | 武器效果 | `AttributeModifierNugget` | 20 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_simbench_c.py::test_weaponfx_predictions_and_finite_bursts；例：AAAVT1_RepairWeapon, AAGA_RepairWeapon |
| 已对拍 | 武器效果 | `MetaImpactNugget:普通无延迟显式Z` | 13 | a1 a2 a4 a5 a6 a7 | tests/test_meta_impact.py::test_meta_impact_collision_event_replays_engine_knock_probe_neighbour_five_frames；仅普通弹头碰撞事件→默认Physics轨迹；engine_knock_probe land/late邻人5帧落(2380,3740)、目标99%/邻人100%。到达帧为台上输入，非完整V4曲线弹回放；直击方向/落点网格/选人仍INFERRED；例：OilDerrickExplosion, SovietBombingRunWeaponWarhead |
| 已对拍 | 武器效果 | `MetaImpactNugget:省略Z默认值` | 11 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | tests/test_meta_impact.py::test_meta_impact_omitted_z_replays_engine_knock_z_tall_neighbour；仅普通无延迟弹头省略ShockWaveZMult→SDK默认1及默认Physics轨迹；engine_knock_z a高度93邻人14帧落(2420,3740)、目标99%/邻人100%。碰撞时刻/爆心为台上输入；直击噪声方向/网格/选人仍INFERRED，完整曲线弹/坡地/筛选未对拍；例：AlliedBomberAircraftBombWarhead, JapanCommandoTech1AirplaneCrashWeapon |
| 已对拍 | 武器效果 | `ParalyzeNugget` | 11 | a1 a2 a4 a5 a6 a7 | tests/test_simbench_c.py::test_weapon_first_hit_is_observed_one_frame_after_the_order_script；例：AAAVT1_RoarWeapon, ABD_RoarWeapon |
| 已对拍 | 武器效果 | `LineDamageNugget` | 6 | a1 a2 a3 a4 a5 a6 a7 | tests/test_simbench_c.py::test_weaponfx_predictions_and_finite_bursts；例：AAAVT1_SovietCommandoSniperRifle, ABD_SovietCommandoSniperRifle |
| 已对拍 | 武器效果 | `SecondaryDamageNugget` | 5 | a7 | tests/test_simbench_c.py::test_secondary_damage_delivers_one_amount_at_hit_without_damaging_health；例：AlliedSupportAircraftCryobeam |
| 已对拍 | 武器效果 | `StripMaxHealthPercentNugget` | 3 | a1 a2 a4 a6 a7 | tests/test_simbench_c.py::test_strip_max_health_percent_uses_maximum_at_full_and_half_health；例：AAAVT1_JapanCommandoTech1PsyonicCrush, ABD_JapanCommandoTech1PsyonicCrush |
| 已对拍 | 武器效果 | `ActivateLinearDamageNugget` | 2 | a1 a2 a4 a6 a7 | tests/test_simsweep.py::test_sweep_a_killed_shooters_line_stops_with_it_and_the_second_ones_rows_are_hit；例：AlliedAntiNavalScoutSonar, AlliedAntiNavalScoutSonarForBridges |
| 已对拍 | 武器效果 | `DamageContainedNugget` | 2 | a1 a2 a3 a5 | tests/test_simbench_c.py::test_damage_contained_limits_eligible_passengers_without_damaging_the_others；例：SovietAntiInfantryInfantryMolotovCocktailWarhead |
| 已对拍 | 武器效果 | `LeechPercentMaxHealthDamageNugget` | 2 | a1 a3 a4 a6 a7 a9 | tests/test_simbench_c.py::test_leech_percent_uses_victim_maximum_not_current_health_or_caster_maximum；例：SovietHarpoonCrushWeapon |
| 已对拍 | 武器效果 | `LeechHealthDamageNugget` | 1 | a1 a2 a3 a4 a5 a6 a7 | tests/test_simbench_c.py::test_leech_health_heals_from_damage_and_respects_the_heal_fraction；例：SovietAntiVehicleVehicleTech1LeechBeamWeapon |
| 不涉及 | 脚本动作 | `PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT` | 640 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 不涉及 | 脚本动作 | `MOVIE_PLAY_RADAR` | 433 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 不涉及 | 脚本动作 | `OBJECT_CREATE_RADAR_EVENT` | 254 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 不涉及 | 脚本动作 | `NAMED_FLASH` | 173 | a9 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 不涉及 | 脚本动作 | `NAMED_SHOW_INFOBOX` | 166 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 不涉及 | 脚本动作 | `PATH_MUSIC_PLAY_EVENT` | 155 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN）；台上量过（docs/engine/inventory-levels-a.md），没有测试跑这个台子 |
| 不涉及 | 脚本动作 | `CAMERA_LETTERBOX_END` | 154 | a4 | 纯表现（名字规则） |
| 不涉及 | 脚本动作 | `CAMPAIGN_CREATE_AUTO_SAVE` | 127 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 不涉及 | 脚本动作 | `UNIT_SET_MODELCONDITION_GENERIC` | 111 | a7 | 纯表现：设模型状态只换画法。原版脚本设的是 SUPPRESSED（a01 摆拍枪战的趴下动作），SDK 数据里读 SUPPRESSED 的只有绘制模块的 ConditionsYes；我们 a7 设的 USER_1 只有自由号的充能画法读 |
| 不涉及 | 脚本动作 | `CAMERA_LETTERBOX_BEGIN` | 104 | a4 | 纯表现（名字规则） |
| 不涉及 | 脚本动作 | `PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM` | 59 | a4 | 纯表现（名字规则）；只记进时间线（sim.SHOWN）；台上量过（docs/engine/inventory-levels-a.md），没有测试跑这个台子 |
| 不涉及 | 脚本动作 | `SHOW_MILITARY_CAPTION` | 58 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（名字规则）；只记进时间线（sim.SHOWN） |
| 不涉及 | 脚本动作 | `SET_COOP_AI_COMMAND_UI_ENABLED` | 24 | a4 | 纯界面：开关玩家给盟友 AI 下令的按钮；模拟器的玩家没有给盟友下令的命令，开关无从起作用（以后加了这个命令再算） |
| 不涉及 | 脚本动作 | `MOVE_CAMERA_TO_NAMED` | 20 | a5 a7 | 纯表现（名字规则）；Sim.act / Sim.cond 有分支 |
| 不涉及 | 物体模块 | `Draws/ScriptedModelDraw` | 1895 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（Draws）；例：AlliedAirfield, AlliedAntiAirMissileProjectile |
| 不涉及 | 物体模块 | `Behaviors/FXListBehavior` | 796 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（名字规则）；例：AlliedAirfield, AlliedAntiAirMissileProjectile |
| 不涉及 | 物体模块 | `Behaviors/ObjectDefectionHelper` | 640 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 没人触发：原版只在 BaseObject 挂一个空的（所以每个物体都有），SageXML 里没有一处 DefectorSpecialPower，脚本动作表里也没有叛变；《将军》里它管"叛变后一段时间不被发现"；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 不涉及 | 物体模块 | `Behaviors/ObjectSMCHelper` | 640 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现：《将军》ObjectSMCHelper 到时清掉"定时模型状态"（UNIT_SET_MODELCONDITION_GENERIC 的秒数），只换画法；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 不涉及 | 物体模块 | `Behaviors/BuildingDestructionBehavior` | 493 | a1 a2 a4 a5 a6 a7 a8 a9 | 纯表现：建筑死后按骨骼放特效、甩碎块（CreationObject 如 AlliedBarracks_Debris：只有画法、寿命和碎片体积，没有身体和武器）、烟尘；例：AlliedAirfield, AlliedBarracks |
| 不涉及 | 物体模块 | `ClientBehaviors/ModelConditionAudioLoopClientBehavior` | 466 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（ClientBehaviors）；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 不涉及 | 物体模块 | `Behaviors/ModelConditionUpgrade` | 341 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现：只加模型状态（民房/步兵按阵营换画法、支援技能画法），同模板的非画法模块和原版脚本 UNIT_HAS_MODELCONDITION 都不读（E 线 work/re/e_na_physics_mcu.md）；例：AlliedAntiInfantryInfantry, AlliedAntiVehicleInfantry |
| 不涉及 | 物体模块 | `ClientBehaviors/ModelConditionSoundSelectorClientBehavior` | 140 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（ClientBehaviors）；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 不涉及 | 物体模块 | `Draws/DynamicsDraw` | 138 | a4 | 纯表现（Draws）；例：OK_Lantern01 |
| 不涉及 | 物体模块 | `ClientBehaviors/AnimationSoundClientBehavior` | 48 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（ClientBehaviors）；例：AlliedAntiInfantryInfantry, AlliedAntiStructureShip |
| 不涉及 | 物体模块 | `Draws/TruckDraw` | 35 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（Draws）；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryVehicle |
| 不涉及 | 物体模块 | `Behaviors/LUAEventList` | 32 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现：EventListName连接原版ScriptEvents.xml与Scripts.lua；RA3声明可达的事件处理函数只调用模型部件显隐（及tostring），含继承；未定义的AlliedInfantryFightingFunctions无可达处理函数；C&C3升级/状态函数不可达。tests/test_inventory_lua.py静态核对游戏包与SDK声明，非上台对拍；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 不涉及 | 物体模块 | `Behaviors/SubObjectsUpgrade` | 26 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（名字规则）；例：AlliedAirfield, AlliedAntiAirVehicleTech1 |
| 不涉及 | 物体模块 | `Behaviors/FreefallUpdate` | 24 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（总控 11-11 定）：配置只有 InitialVelocity / Acceleration / TerminalVelocity / ModelConditionsToSet=STUNNED_FLAILING，管空中死亡后尸体下落的画面；engine_freefall fall 已核人炮扔出的兵原版 / 改慢 / 改快三份读数一样（AIRBORNE_TARGET 1-125 帧、22 帧到点、降落伞约 96 帧），不归本模块。gap：被举起后落下（ActivateLiftObjectNugget / LiftObjectUpdate，C 已接通计时、落地仍 gap）可能用到下落速度，落地时刻会影响逻辑，未上台；同 id 覆盖是否生效未排除；例：AlliedAntiInfantryInfantry, AlliedAntiNavalScout |
| 不涉及 | 物体模块 | `Draws/LaserDraw` | 21 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（Draws）；例：AlliedAntiAirVehicleTech1, AlliedAntiStructureVehicle |
| 不涉及 | 物体模块 | `Behaviors/LaserState` | 19 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现：LaserId关联光束，起止粒子/骨骼/EndOffset与ObjectStatusValidation只控制光束表现；LaserStateModule.xsd无伤害字段；engine_laser pair匹配LaserDraw/State 201，伤害由独立DamageNugget给出，test_simbench_c重放2/90/2/90；例：AlliedAntiAirVehicleTech1, AlliedAntiVehicleInfantry |
| 不涉及 | 物体模块 | `Draws/TracerModelDraw` | 18 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现（Draws）；例：AlliedAntiAirVehicleTech1, AlliedAntiInfantryVehicle |
| 不涉及 | 物体模块 | `Behaviors/ProductionUpdateInfo` | 9 | a1 a4 a5 a6 a7 a9 | 纯界面状态：保存七个生产类别的侧栏子页签编号；读写限于侧栏编号维护、变形时保留编号和存档传递，没有游戏逻辑读者，模拟器不建模；9用量/9模板保留；读者闭包证据见 work/re/e_production_e56.md，非上台对拍；例：AlliedConstructionYard, AlliedMCV |
| 不涉及 | 物体模块 | `Behaviors/AudioLoopUpgrade` | 1 | a1 a2 a3 a4 a5 a6 a7 | 纯表现（名字规则）；例：SovietAntiVehicleVehicleTech1 |
| 不涉及 | 物体模块 | `ClientBehaviors/UpgradeSoundSelectorClientBehavior` | 1 | a1 a4 a7 | 纯表现（ClientBehaviors）；例：AlliedAntiAirVehicleTech1 |
| 不涉及 | 武器效果 | `ActivateLaserNugget` | 27 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现：Lifetime/LaserId/HitGroundFX/OverShootDistance驱动LaserState/LaserDraw；engine_laser pair实测2/90/2/90，无附加伤害或首发延迟，test_simbench_c重放；例：AAAVT1_JapanAntiVehicleInfantryPlasmaBazooka, ABD_JapanAntiVehicleInfantryPlasmaBazooka |
| 不涉及 | 武器效果 | `TintObjectsNugget` | 9 | a1 a2 a3 a4 a5 a6 a7 a8 a9 | 纯表现：Color及Pre/Sustained/PostColorTime、Frequency/Amplitude仅控制染色动画；engine_tint pair实测2/90/2/90，独立DamageNugget解释全部伤害，test_simbench_c重放；不声称像素已验证；例：AlliedCommandoAttachWeapon, AlliedSupportAircraftShrinkRay |
