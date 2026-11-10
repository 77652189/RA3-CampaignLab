# 武器组与状态位（WeaponSetUpdate / StatusBitsUpgrade）

台上读数 2026-11-09（引擎线 C 第 11 轮；探针 `experimental/cnv/checks/engine_weaponset.py`、`engine_statusbits.py`）。模拟器：`simunits.weapon_sets` / `pick_weapons`、`Sim.modify`。测试：`tests/test_simbench_c.py` 最后两条。

## 1. 按状态选武器（engine_weaponset a，台上）

零件 XML 里每把 `<Weapon>` 可以写 `ObjectStatus`（单位身上要有这些位）和 `ForbiddenObjectStatus`（有一个就不能用）。征召兵：AK47 在 GENERIC_TOGGLE_STATE 下被禁，火焰瓶需要它。对一辆不还手的海啸坦克读每秒血：

| 车道 | 第 41 秒血 | 说明 |
| --- | --- | --- |
| 基准（AK47） | 42 | 每秒约 1.4 % |
| 毒瓶（从头带 TOGGLE） | 9 | 每秒约 2.2 %（火焰瓶更狠） |
| 中途（12 秒时脚本才给 TOGGLE） | 21 | 前 12 秒和基准重合，之后换成火焰瓶的斜率 |

结论：武器组在**状态变化的那一刻**重新选；已经在打的目标不丢，只是换枪。
模拟器：同槽位里 PRIMARY_WEAPON 的那一行先试，第一把"需要的位都在、禁用的位都没有"的就是它；伤害为 0 或射程为 0 的（涂靶器）不算枪。读数 `[43, 10, 20]` vs 台上 `[42, 9, 21]`。

## 2. 涂靶器不伤人（engine_weaponset b，台上）

守护者带 TOGGLE：主炮被禁，只剩涂靶器，海啸坦克血一直 100。模拟器同。

## 3. 状态位升级（engine_statusbits b，台上）

`NAMED_RECEIVE_UPGRADE Upgrade_Veterancy_HEROIC`（脚本给的）会让带 StatusBitsUpgrade 的单位得到 WEAPON_UPGRADED_0x：幻影坦克 / 征召兵 _01，守护者 _02（不会得到 _01）。`NAMED_REMOVE_UPGRADE` 把位撤回。读数（`UNIT_HAS_OBJECT_STATUS`）：英雄位 1；晚位 0→1（8 秒给）；去位 1→0（8 秒撤）；兵守位 11（征召兵 _01、守护者 _02、守护者 _01 为 0）。模拟器一模一样。

## 4. 没解释的：幻影坦克只开一炮（engine_weaponset b 的 棱镜 / 老兵 车道，engine_statusbits a）

台上幻影坦克对不还手的海啸（380 血）只开**一炮就停**：普通炮 200 → 血 47，老兵炮（WEAPON_UPGRADED_01，250）→ 血 34，之后 40 秒不变。武器数据是单发、FiringDuration 1.5 s、ClipReloadTime 0.1 s、自动装填，理应每 1.6 s 一炮；模拟器照数据打，3~5 秒打死。**原因没查出来**（候选：武器 `WeaponOCLNugget` 在目标处生出棱镜节点物体，挡住了后续直线视线；`ReAcquireDetailType=PER_CLIP`；与 NAMED_ATTACK_NAMED 的交互）。选武器本身（普通 → 老兵）已由单炮伤害 200 / 250 证明。

**第二个探针 `engine_prism` a（台上，同日）**：四条车道，第 1 秒起海啸血 基准（幻影坦克，一道攻击令）47 / 自动（不下令，自动索敌）47 / 对照守护者炮 84→68→52→36→21→5（连发，每 3 秒约 16 %，打到 5 不动是坦克血量只剩一炮前的数）/ 重令（每 3 秒重下一次攻击令）47。结论：**① 不是攻击令的事**（自动索敌也只一炮；重下令也不重新开火）；**② 不是目标的事**（守护者对同一辆坦克连发）；**是幻影坦克这把炮自己的毛病**：开一炮后在这个场景里再不开火。排除了"棱镜节点挡视线"的简单版本：节点物体（AlliedAntiVehicleVehicleTech3CannonNodeRegular）是 INERT / NO_COLLIDE、半径 0.8，自带 WeaponScatterEffectUpdate（对附近敌人再放 CannonNode 武器，散射 5）。**下一步**（要自己的单位 XML 改一下炮）：克隆幻影坦克的炮，分别 ① 去掉 WeaponOCLNugget ② 去掉 ATTACK_NEEDS_LINE_OF_SIGHT ③ 去掉 SuppressionNugget / ActivateLaserNugget，看哪一个让它连发；做法参照 `units/crane.py` 这类改 XML 的单位。模拟器暂时不动（战役里幻影坦克要不要连发，得先知道真相）。
