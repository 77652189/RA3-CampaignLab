# 起义时刻有、RA3 1.13 没有的东西（做新单位前先查这里）

2026-11-09 第一版，引擎线 A。用户的担心："超级要塞的武器系统是重写的，许多 mod 在原版都实现不了，这样的地方可能还有几处。"

**一句话结论**：起义时刻真正新增的引擎功能不多，一共 **13 种新模块、0 种新武器效果、0 种新运动器**，外加十来张枚举表里多出的取值。超级要塞的**武器部分**（武器组、激光、扫射激光）用的模块 RA3 1.13 全都有；它**新的地方在变形**（两种"展开"模块）和**一种扫射方式的取值**（新枚举，RA3 没有）。所以我们做新单位时，"借起义时刻单位的现成做法"要先查下面的表；不在表里的模块和效果，RA3 mod 能照用。

**怎么查的**（复现脚本 `work/re/scripts/upgap.py`，在仓库根目录跑）：
- 两个 exe（RA3 1.13 的 `RA3_1.13.game`、起义时刻 1.1 的 `ra3ep1_1.1.game`）里都留着模块类名和枚举名的字符串表，直接做差集。
- 两边编好的游戏数据（`StaticStream.big` 里的 static 流；起义时刻的 manifest 是第 7 版，头部多一个字）里，每个 GameObject 的数据里存着它每个模块的类型名哈希。拿两个 exe 里所有模块名算哈希去扫，就知道哪个单位用了哪个模块（RA3 自己的数据扫出来全都在 RA3 exe 里，说明方法可靠）。
- 每张枚举表在两个 exe 里各找一份、整表比较，再用 SDK 的 xsd 认出它是哪个字段的取值。

**"RA3 mod 能不能用"的依据**：下表"不能用"的东西，RA3 1.13 的 exe 里没有对应的类或取值，SDK 的 schema 里也没有。预计 BinaryAssetBuilder 编译时就会报错（**还没上台实测**，台子空了就测一个，见文末）。

## 第一层：脚本动作和条件（29 个）

起义时刻地图用到、动作号超出 RA3 1.13 分派范围的：**26 个动作、3 个条件**，RA3 战役地图用不了。清单在 `experimental/cnv/inventory.py` 的 `UPRISING_ONLY`（依据：从起义时刻地图读出动作号，对 RA3 exe 的分派表）。用得多的：`TELEPORT_STRUCTURE`（128 次）、`CREATE_UNNAMED_ON_TEAM_AT_NAMED_OBJECT_LOCATION`（67）、`SET_REFERENCE_TO_RANDOM_TEAM_MEMBER`（59），还有"引用"一族（`SET_LAST_CREATED_UNIT_TO_REFERENCE`、`SET_REFERENCE_TO_FIRST_TEAM_MEMBER_IN_AREA`）和"循环执行"一族（`FOR_EACH_TEAM_MEMBER_EXECUTE_SCRIPT`、`FOR_EACH_PLAYER_OBJECT_EXECUTE_SCRIPT`、`EVALUATE_SCRIPT`）。条件：`IS_OBJECT_OF_TYPE`、`OBJECT_IS_DISGUISED_AS_TYPE`、`PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA_WITH_MODELCONDITION`。

另外注意：起义时刻地图里有些动作 RA3 也有，只是我们的 `script_catalog.json` 没收（如 `SET_UNIT_REFERENCE`、`GATE_OPEN`）——那些**能用**，先补目录条目。

## 第二层：物体模块（13 种新的）

| 模块 | 起义时刻谁在用 | 大概做什么（按名字和使用者推断） | RA3 mod |
|---|---|---|---|
| UnitUnpackUpdate | 超级要塞（JapanFortressShip） | 单位"展开"成另一种形态 | 不能用 |
| GenericUnpackUpdate | 53 个：盟军全部建筑、超级要塞等 | 通用的展开动画/过程（RA3 建筑用的是 StructureUnpackUpdate） | 不能用；建筑展开用 RA3 自己的 StructureUnpackUpdate |
| YurikoShieldSphereUpdate | 尤里子（JapanIzumi、JapanYurikoTech1–3）、YurikoShieldProp | 尤里子的护盾球 | 不能用 |
| SphereModuleUpdate | 尤里子、未来坦克的中子节点、AlliedAntiStructureVehicle、YurikoShieldProp | 球形区域（护盾 / 中子场的底座） | 不能用；RA3 有 ShieldSphereUpdate 可替代一部分 |
| AddObjectsToLiftUpdateSpecialPower | 尤里子 | 念力举起一群物体 | 不能用 |
| AddObjectsToLureUpdateSpecialPower | 尤里子 | 念力吸过来 | 不能用 |
| LureObjectsUpdate | 尤里子 | 同上（被吸的过程） | 不能用 |
| FlingStoredObjectsSpecialPower | 尤里子 | 把举起的东西扔出去 | 不能用 |
| ReactionFXOnDamage | 尤里子（Tech1–3） | 挨打时按条件放特效 | 不能用；纯表现，可用 RA3 的受伤特效模块凑 |
| DamageSphereUpdate | 未来坦克的中子节点 | 球形持续伤害区 | 不能用；RA3 可用持续伤害武器 / 光环凑 |
| SpawnedSlaveUpdate | 辐射兵的喷射伤害轨迹（DesolatorSprayDamageTrail） | 生成的子物体跟随 | 不能用 |
| ProjectileReplaceSelfSpecialAbility | SovietHeavyWalkerVehicle（推测是乳齿象） | 发射后把自己换成别的物体 | 不能用；RA3 有普通的 ReplaceSelfSpecialAbility |
| 三种 DynamicsCollide（Audio / Damage / 基类） | exe 里有，static 数据里没扫到使用者 | 物理碰撞时发声 / 造成伤害 | 不能用 |

起义时刻还用了 5 种 **RA3 exe 有、但 RA3 自己数据没用过**的模块：BeamSpecialAbilityUpdate（未来坦克）、ArmorUpgrade、ImmortalBody、StreamState + W3DStreamDraw（辐射兵等的喷射流）。这些**理论上能用**，但 RA3 自己没用过，没有现成例子，用前先上台试。

## 第三层：武器效果和运动器（没有新类型）

- 武器效果（Nugget）的类名两个 exe 完全一样，只多了两个**音乐**用的条件（`MusicScriptConditionNugget_LocalPlayerHitRedAlertButton`、`…_ObjectTypesInProximity`）。也就是说起义时刻没有新的武器效果种类。
- 运动器：类名一样，没有新种类。
- 但**武器、运动器、特殊能力、护甲、物体**这几种资产的编译结构都和 RA3 不同（manifest 里的类型哈希不同；贴图、模型、粒子、UI 大多相同）。至少一部分原因是下面这些共用枚举加了取值，**是否还加了字段，这一版没量**。

## 第四层：同名但多了取值（枚举）

RA3 的 SDK 和 exe 都不认识下面这些取值，起义时刻单位用到它们的做法在 RA3 里做不出来：

| 字段（SDK 里的类型） | 起义时刻新加的取值 |
|---|---|
| 伤害类型（DamageType） | `NEUTRON`（中子，未来坦克） |
| 单位种类标记（KindOf） | `ATTACKS_BRIDGE_GATEHOUSE`、`CAN_BE_FORCED_TO_ATTACK`、`DETECTOR`、`FLINGABLE_PROP`、`INVALID_TARGET_FOR_C4`、`PATH_THROUGH_ENEMY_VEHICLES`、`PRODUCED_FROM_ABOVE`、`TREAT_AS_TERRAIN_FOR_LINE_OF_SIGHT`、`TURRET_CREATED_FROM_UNIT`、`UNIT_BUILT_LIKE_STRUCTURE`（另一张表还有 `FROZEN`） |
| 物体状态（ObjectStatus）和模型状态 | `AIRBORNE_PULLED_FROM_SKY`、`BLATTED`、`BLAT_TRIGGER`、`BRIDGE_DEAD`、`DESOLATION_ACTIVE`、`DYNAMICS_DISABLED`、`DYNAMICS_SIMULATION_ACTIVE`、`OPEN`、`REFLECTING`、`SKIP_PATH_CLAMPING`、`SPECIAL_POWER_SELECTED`；模型状态另有 `SPECIAL_POWER_SELECTED_PENDING`、`WEAPONBARREL_01`–`05`（多炮管轮换开火的画面） |
| 碰撞开火（FireWeaponCollide 的条件） | `CHECK_WEAPON_AIM_DELTA`、`DISABLE_WHILE_FIRING`、`NOT_WHILE_ATTACKING`、`ONLY_FRONT_COLLIDES`、`ONLY_WHILE_MOVING`、`STANCE_ONLY_FORBIDDEN_WHILE_STATIONARY`（RA3 只有 5 个取值，起义时刻 11 个） |
| 附着（AttachUpdate 的标记） | `DETACH_WHEN_MULTIPLE_ARE_ATTACHED`、`USE_BONE_POSITION` |
| 换自身（ReplaceSelf 的选项） | `REPLACE_OVER_ENEMIES`、`TRANSFER_EXPERIENCE` |
| 曲线弹道（BezierProjectile 的标记） | `DONT_GO_UNDERWATER` |
| 属性修正的类别、武器加成条件 | `SHRINK`（缩小；谁在用还没对，推测是中子武器一类） |
| **一张 RA3 完全没有的新表** | `SWEEP_HORIZONTAL`、`SWEEP_VERTICAL`、`SWEEP_FROM_SOURCE_ON_ANGLE`、`MOVE_BACK_AND_FORTH`——扫射方式。推断属于超级要塞一类的扫射激光（RA3 的 SweepingLaserState 只有半径、特效、武器这几个字段，没有扫射方式） |

RA3 有、起义时刻删掉的几个是 C&C3 的遗留（`HIJACKED`、`TIBERIUM_*`、`CASTLE_KEEP` 等），对我们没影响。

## 超级要塞到底怎么回事

- 它的模块里，武器相关的 **WeaponSetUpdate、LaserState、SweepingLaserState、W3DLaserDraw 在 RA3 1.13 里都有**。所以"武器系统整个重写"在模块这一层**不成立**。
- 真正 RA3 没有的：**UnitUnpackUpdate + GenericUnpackUpdate**（海上 / 空中两种形态的展开）和**扫射方式那张新表**。
- 对我们的意思：做"多武器、会扫射的大家伙"RA3 mod 能做，扫射路线只能用 RA3 默认的那一种；做"会展开变形的单位"，要走 RA3 自己的变形办法（换运动器、换状态、换自身，见 [transform.md](transform.md)），不能照抄超级要塞。
- 还没查清的：WeaponSetUpdate / 武器模板在起义时刻里有没有**新增字段**（类型哈希不同，但可能只是枚举扩充带来的）。要查得比较两边编好的同一个模块的结构大小，或上台试。

## 还没做的

- **上台实测**：把一个起义时刻专有模块（打算用 UnitUnpackUpdate）写进一个 mod 单位，看 BinaryAssetBuilder 报错 / 游戏忽略 / 崩溃。台子被用户的红警2 占着，空了再做。
- 字段级差别（见上一节最后一条）。
- 只扫了 static 流里的 597 个起义时刻物体；地图自带流里的物体没扫。新 KindOf / 状态具体是哪些单位在用，也还没对（要把枚举位号对回数据）。
