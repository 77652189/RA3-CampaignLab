r"""The retail feature inventory (ADR 0026): everything the retail game uses that the simulator should be able to do,
each item with a state, ordered by how much retail uses it. Generated from retail data -- never written by hand --
into docs/engine/inventory.md; tests/test_inventory.py fails when the file is stale (a new item, a changed state).

Parts (the engine A line's share of ADR 0026; AI is the B line's):
  脚本动作 / 脚本条件  every action and condition name the retail campaign scripts use (script_catalog.json), with the
                    uses counted in the retail scripts (work/retailref, retailref.py's cache); an action told apart by
                    what it is told to do (a status bit, a special power, a command button: simcoverage.refined) is
                    one item per refinement
  物体模块          every module type the retail GameObjects use (retailmodules.module_census: includes and
                    inheritance resolved), counted by templates placed in the retail campaign maps, then by all
  武器效果          every Nugget type of the retail weapons (retailmodules.weapon_census)

States (STATES): 已对拍 -- implemented and a bench comparison test cites it (BENCHED: the register, each entry naming
the test); 推断 -- the simulator has code for it, no bench comparison yet; 未做 -- nothing; 不涉及 -- presentation only
(a rule below, by name or module group: never a list; a presentation action measured on the bench stays 已对拍).
How "has code" is told:
  script names    simcoverage.name_state: the engine model's core, a Sim.act / Sim.cond branch (probed with a retail
                  use's own arguments), sim.SHOWN; sim.IGNORED is 未做 (dropped on purpose, may hide play)
  modules, nuggets  the type's name is a string constant in sim.py / simunits.py / simproxy.py (simcoverage.sim_code)
                  -- a first cut: a module read under another name shows as 未做 until NOTES says otherwise

  python -I -X utf8 experimental/cnv/inventory.py            regenerate docs/engine/inventory.md, print the summary
  python -I -X utf8 experimental/cnv/inventory.py --check    exit 1 when the file is stale
"""
import ast
import collections
import json
import os
import re
import sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'campaign')))
import labpaths  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

CATALOG = os.path.join(ROOT, 'experimental', 'campaign', 'script_catalog.json')
RETAIL_SCRIPTS = os.path.join(labpaths.WORK, 'retailref')
OUT = os.path.join(ROOT, 'docs', 'engine', 'inventory.md')

BENCHED, GUESSED, TODO, NA = '已对拍', '推断', '未做', '不涉及'
STATES = (BENCHED, GUESSED, TODO, NA)
ACTION, CONDITION, MODULE, NUGGET, AI = '脚本动作', '脚本条件', '物体模块', '武器效果', 'AI'
PARTS = (ACTION, CONDITION, MODULE, NUGGET, AI)     # AI: engine B's part, its own rules in inventory_ai.py

# (part, name) -> 'tests/<file>.py::<test>': the bench comparison that backs the item (the guard checks the test exists)
BENCHED_TESTS = {
    (MODULE, 'Behaviors/EngineerContain:通用三国'):
        'tests/test_simengineer.py::test_engineer_soviet_japan_captures_as_on_the_bench',
    # Field-form coverage only: recorded collision / incoming-event replay, not full retail flight or every consumer.
    (NUGGET, 'MetaImpactNugget:普通无延迟显式Z'):
        'tests/test_meta_impact.py::test_meta_impact_collision_event_replays_engine_knock_probe_neighbour_five_frames',
    (NUGGET, 'MetaImpactNugget:省略Z默认值'):
        'tests/test_meta_impact.py::test_meta_impact_omitted_z_replays_engine_knock_z_tall_neighbour',
    (NUGGET, 'InformTargetNugget:默认系数目标通知'):
        'tests/test_inform_ai.py::test_inform_incoming_table_drives_miner_armor_from_engine_inform_probe',
    (NUGGET, 'InformTargetNugget:Max1.6目标通知'):
        'tests/test_inform_ai.py::test_inform_max_launch_matches_engine_inform_max_observed_deadline',
    # engine_suppression under D's read-only engine_suppress_probe, four measured state/end traces.
    # Walking counters still expose the straight-path approximation; fractional lifetime rounding INFERRED.
    (MODULE, 'Behaviors/SuppressionUpdate'): 'tests/test_simbench_c.py::test_suppression_samples_entry_refresh_and_expiry_at_the_four_probe_readings',
    (NUGGET, 'SuppressionNugget'): 'tests/test_simbench_c.py::test_suppression_samples_entry_refresh_and_expiry_at_the_four_probe_readings',
    # engine_dot: direct single hit, immediate first tick and inclusive expiry; stacking/healing/projectiles unbenched.
    (NUGGET, 'DOTNugget'): 'tests/test_simbench_c.py::test_dot_counts_interval_ticks_for_two_durations_and_observes_first_damage_frame',
    # engine_contained: NONE KindOf filter, cap1/2; selection order GUESSED, radius/projectiles/death unbenched.
    (NUGGET, 'DamageContainedNugget'): 'tests/test_simbench_c.py::test_damage_contained_limits_eligible_passengers_without_damaging_the_others',
    (NUGGET, 'LeechHealthDamageNugget'): 'tests/test_simbench_c.py::test_leech_health_heals_from_damage_and_respects_the_heal_fraction',
    (NUGGET, 'LeechPercentMaxHealthDamageNugget'): 'tests/test_simbench_c.py::test_leech_percent_uses_victim_maximum_not_current_health_or_caster_maximum',
    (NUGGET, 'SecondaryDamageNugget'): 'tests/test_simbench_c.py::test_secondary_damage_delivers_one_amount_at_hit_without_damaging_health',
    (NUGGET, 'WeaponOCLNugget'): 'tests/test_simbench_c.py::test_weapon_ocl_lifetime_damage_reads_the_fire_delay_before_counting_updates',
    (NUGGET, 'ProjectileNugget'): 'tests/test_simbench_c.py::test_projectile_nugget_flight_uses_retail_shell_speed_and_resolved_warhead',
    # Weapon C: replayed bench variants; tests name the actual engine_X build (A line rule).
    (NUGGET, 'AttributeModifierNugget'): 'tests/test_simbench_c.py::test_weaponfx_predictions_and_finite_bursts',
    (NUGGET, 'LineDamageNugget'): 'tests/test_simbench_c.py::test_weaponfx_predictions_and_finite_bursts',
    (NUGGET, 'ParalyzeNugget'): 'tests/test_simbench_c.py::test_weapon_first_hit_is_observed_one_frame_after_the_order_script',
    (NUGGET, 'StripMaxHealthPercentNugget'): 'tests/test_simbench_c.py::test_strip_max_health_percent_uses_maximum_at_full_and_half_health',
    (MODULE, 'Behaviors/OreMinerBehavior'): 'tests/test_simbench.py::test_mining_pays_8_a_frame_and_a_trip_takes_269',
    (MODULE, 'Behaviors/OreNodeBehavior'): 'tests/test_simbench.py::test_mining_a_second_miner_on_one_node_adds_nothing',
    # batch 1 (work/re/l2_scripts1.md, checks/engine_scripts1.py, bench 11-08)
    (CONDITION, 'PLAYER_IS_HUMAN_OR_AI_PERSONALITY'): 'tests/test_simbench.py::test_scripts1_conditions_as_the_bench',
    (CONDITION, 'UNIT_HAS_OBJECT_STATUS'): 'tests/test_simbench.py::test_scripts1_conditions_as_the_bench',
    (CONDITION, 'HAS_FINISHED_AUDIO'):
        'tests/test_simbench.py::test_audio_a_dubbed_line_is_done_its_length_after_it_is_heard',
    (CONDITION, 'HAS_FINISHED_VIDEO'):
        'tests/test_simbench.py::test_video_a_radar_clip_is_done_after_its_length_full_screen_never',
    (ACTION, 'TEAM_TRANSFER_TO_PLAYER'): 'tests/test_simbench.py::test_scripts1_a_team_handed_over_drops_its_move',
    (ACTION, 'PLAYER_RELATES_PLAYER'): 'tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back',
    (CONDITION, 'PLAYER_HAS_OBJECT_COMPARISON'): 'tests/test_simbench.py::test_scripts2_a_relation_is_one_way_and_turns_back',
    (ACTION, 'ALLOW_DISALLOW_ONE_BUILDING'): 'tests/test_simbench.py::test_a_ban_holds_the_queue_and_does_not_cancel',
    (ACTION, 'UNIT_IDLE_FOR_SECONDS'): 'tests/test_simbench.py::test_scripts1_idle_for_seconds_drops_the_move',
    # protocol points (simtech.py, checks/engine_protocol.py, bench 11-08)
    (ACTION, 'PLAYER_SET_MAX_PLAYER_POWER_POINTS'):
        'tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule',
    (ACTION, 'PLAYER_SET_PLAYER_POWER_POINTS'):
        'tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule',
    (ACTION, 'PLAYER_LOCK_PLAYER_TECH'): 'tests/test_simbench.py::test_protocol_a_computer_player_spends_unless_locked',
    (CONDITION, 'PLAYER_HAS_COMPARISON_POWER_POINTS'):
        'tests/test_simbench.py::test_protocol_set_points_follows_the_programs_rule',
    (CONDITION, 'PLAYER_HAS_PLAYER_TECH'): 'tests/test_simbench.py::test_protocol_rank_two_at_frame_5400',
    # engine line C round 1: modules whose retail data the simulator already follows and a bench-reading test cites
    (MODULE, 'Behaviors/ProductionUpdate'):
        'tests/test_simbench.py::test_production_pays_as_it_builds_and_comes_out_after_the_door',   # engine_production a-g
    (MODULE, 'Behaviors/StructureUnpackUpdate'): 'tests/test_simbench.py::test_power_back_after_the_plant_unpacks',
    (MODULE, 'Behaviors/SpecialPower'): 'tests/test_simbench.py::test_super_a_scripts_cast_starts_the_retail_reload',
    (MODULE, 'AI/AIUpdate'): 'tests/test_simbench.py::test_r8_idle_within_sight_walks_up_fires_and_comes_back',
    # engine line C round 3: the crush / slow-death family (checks/engine_crush.py, docs/engine/crush.md, bench 11-06)
    # engine line C round 7: the superweapon benches (engine_super) read health % of 1000-health defenses and the
    # Iron Curtain's expiry frame -- MaxHealth through the damage, the modifier pool through the 23 s it holds
    (MODULE, 'Body/ActiveBody'): 'tests/test_simbench.py::test_super_the_proton_collider_ends_as_the_bench',
    (MODULE, 'Behaviors/AttributeModifierPoolUpdate'):
        'tests/test_simbench.py::test_super_the_iron_curtain_holds_off_fire_some_23_seconds',
    (MODULE, 'Behaviors/SecondaryDamageTracker'):
        'tests/test_simbench.py::test_cryo_a_frozen_tank_melts_334_frames_after_the_beam_whatever_the_beam',
    (MODULE, 'Behaviors/AutoHealBehavior'):
        'tests/test_simbench.py::test_autoheal_an_apocalypse_mends_two_points_every_7_frames_after_a_15_frame_wait',
    (MODULE, 'Behaviors/SquishCollide'):
        'tests/test_simbench.py::test_crush_a_tank_drives_over_a_lower_level_and_leaves_an_equal_one',
    (MODULE, 'Behaviors/CrushDie'):
        'tests/test_simbench.py::test_crush_a_tank_drives_over_a_lower_level_and_leaves_an_equal_one',
    (MODULE, 'Behaviors/SlowDeath'):
        'tests/test_simbench.py::test_slow_death_a_crushed_conscript_lies_127_frames_dying_and_in_its_spot',
    (MODULE, 'Behaviors/DestroyDie'): 'tests/test_simbench.py::test_destroy_die_a_building_killed_is_dying_one_frame_and_gone',
    # engine line C round 8: running off the map (Sim.flee_start / flee_due, checks/engine_runoffmap.py, bench 11-06)
    (MODULE, 'Behaviors/RunOffMapBehavior'):
        'tests/test_simbench_c.py::test_run_off_map_the_peacekeeper_is_gone_64_and_304_frames_after_the_order_never_dying',
    # engine line C round 9: the mirage aura (Sim.cloaked, simunits.invis_broadcast, checks/engine_stealth.py, bench 11-05)
    (MODULE, 'Behaviors/InvisibilityBroadcastUpdate'):
        'tests/test_simbench_c.py::test_invisibility_broadcast_the_aura_holds_its_guardian_at_full_health_and_the_control_dies',
    (MODULE, 'Behaviors/InvisibilityBehavior'):
        'tests/test_simbench_c.py::test_invisibility_behavior_a_house_given_garrison_can_stealth_by_script_is_shot_like_a_plain_one',
    # engine line C round 11: weapon choice by ObjectStatus (simunits.weapon_sets, checks/engine_weaponset.py,
    # engine_statusbits.py, bench 11-09)
    (MODULE, 'Behaviors/WeaponSetUpdate'):
        'tests/test_simbench_c.py::test_weapon_set_the_status_picks_the_gun_molotov_under_the_toggle_and_the_painter_does_no_harm',
    # engine line D: the damage line (simsweep, checks/engine_sweep.py engine_sweepoff a / b / c, bench 11-10)
    (MODULE, 'Behaviors/LinearDamageUpdate'):
        'tests/test_simsweep.py::test_sweep_the_line_walks_out_and_a_stop_does_not_cut_it_at_the_bench_frames',
    (NUGGET, 'ActivateLinearDamageNugget'):
        'tests/test_simsweep.py::test_sweep_a_killed_shooters_line_stops_with_it_and_the_second_ones_rows_are_hit',
    (MODULE, 'Behaviors/StatusBitsUpgrade'):
        'tests/test_simbench_c.py::test_status_bits_upgrade_the_heroic_grant_sets_weapon_upgraded_and_a_removal_clears_it',
    # immortal a / b / c, bench 11-09 (checks/engine_immortal.py): damage floor 1 %, script kill clamped, delete removes
    (MODULE, 'Body/ImmortalBody'):
        'tests/test_simbench_c.py::test_immortal_damage_stops_at_one_hp_kill_is_damage_and_delete_removes',
    # engine_propbody a / b / c, bench 11-10: no health, a kill leaves the street segment, topples the tree / lantern
    (MODULE, 'Body/PropBody'):
        'tests/test_simbench_c.py::test_prop_body_no_health_a_kill_leaves_the_street_and_topples_the_tree_and_lantern_at_the_bench_frames',
    # engine_spawn_refill, bench 11-05: a scripted kill sets off the exploding mig's death weapon, the Guardian beside it dies
    (MODULE, 'Behaviors/FireWeaponWhenDead'):
        'tests/test_simbench_c.py::test_fire_weapon_when_dead_a_scripted_kill_blows_the_mig_and_the_guardian_beside_it',
    # topple a / b, bench 11-09: neutral props, delayed removal without DYING; all five readings within one frame
    (MODULE, 'Behaviors/ToppleUpdate'):
        'tests/test_simbench_c.py::test_topple_the_five_props_disappear_at_the_bench_frames_without_ever_dying',
    # topple c, bench 11-10: lantern copies with / without EnableDynamicsCollide crushed and gone at the same frames
    (MODULE, 'Behaviors/EnableDynamicsCollide'):
        'tests/test_simbench_c.py::test_enable_dynamics_collide_a_lantern_without_it_is_crushed_and_gone_at_the_same_frames',
    # engine_dynamics a / b, bench 11-10: Hammers with / without BaseVehicle's DynamicsUpdate crush, go round and
    # arrive at the same frames (the Uprising fling props' share is split off: SPLIT_ORPHAN)
    (MODULE, 'Behaviors/DynamicsUpdate'):
        'tests/test_simbench_c.py::test_dynamics_update_a_hammer_without_it_crushes_and_goes_round_as_the_retail_one',
    # all four stances the retail scripts set: engine_stance a-f (HOLD_FIRE, bench 11-06) and engine_acquire hold / agg
    # (HOLD_POSITION goes after nothing, AGGRESSIVE never walks back; bench 11-10) -- tests/test_simbench_c.py test_stance_*
    (MODULE, 'Behaviors/StancesBehavior'):
        'tests/test_simbench_c.py::test_stance_hold_fire_stops_a_standing_attack_order',
    # engine_garrison in / hp, bench 11-05 (simgarrison): script entry skips room and relation, owner follows the
    # first passenger, out at 13 % in the damage's frame, the contester bounces one, kill / hit eject them alive
    (MODULE, 'Behaviors/ContestableGarrisonContain'):
        'tests/test_simbench_c.py::test_garrison_script_entry_skips_room_and_relation_owner_follows_and_damage_or_kill_ejects_alive_at_the_bench',
    # engine_transport load, bench 11-10 round 152 (simgarrison's transports): the script's entry skips room and
    # relation, the men ride along, a killed transport kills them; the man cannon throws one every TimePerPassenger
    (MODULE, 'Behaviors/TransportContain'):
        'tests/test_simbench.py::test_transport_a_team_put_in_instantly_skips_the_room_and_the_relation_and_rides_along',
    (MODULE, 'Behaviors/EjectPassengersSpecialAbilityUpdate'):
        'tests/test_simbench.py::test_transport_the_man_cannon_throws_one_every_half_second_and_a_killed_transport_kills_its_men',
    # engine line C round 5: selling (checks/engine_sell.py, docs/engine/sell.md, bench 11-06)
    (MODULE, 'Behaviors/BuildingBehavior'):
        'tests/test_simbench.py::test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames',
    (MODULE, 'Behaviors/StructureSellUpdate'):
        'tests/test_simbench.py::test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames',
    (ACTION, 'SELL_OBJECT'):
        'tests/test_simbench.py::test_sell_pays_half_the_cost_scaled_by_health_once_and_deletes_after_30_frames',
    (ACTION, 'NAMED_DAMAGE'):
        'tests/test_simbench.py::test_sell_a_killed_building_stays_paid_and_a_building_unpacking_is_not_sold',
}

# (part, name) -> (state, why): where the name rule above is wrong (a module read under another name ...)
_NOT_IN_SIM = '已核（11-08）：模拟器没有这个效果'
NOTES = {
    (MODULE, 'Behaviors/InfiltratorContain'): (GUESSED, '部分：engine_infiltrator a盟军间谍普通进入敌方原版盟军电厂，间谍消耗、建筑不换主、单座100电量停电约20秒后恢复；友军拒入且间谍存活，tests/test_siminfiltrator.py重放。E20完整配置盘点：11种配置/34用量，ENERGY 4、KILL 1、STEAL_MONEY 3、VISION 5+港口阻断型1、PARALYZE 3、VISION_UNITS飞机2/步兵3/舰船3/车辆4、RESET 5；ENERGY仍缺忍者/电量缩放/重复进入，其余配置无效果对拍，完整配置已对拍0/34，不登记整项已对拍（tests/test_inventory_contain.py）'),
    (MODULE, 'Behaviors/TrackIncomingWeaponFireBehavior'): (TODO, '部分：engine_inform_probe a/off通知记录回放验证录入、30帧窗口、来源与武器匹配删除和过期清理；精确过期边界INFERRED，原版完整调度/历史伤害仍gap，不靠名字命中晋升整项'),
    (MODULE, 'Behaviors/RepairUpdate'): (TODO, '仅字段读取：engine_repair a两次未触发玩家维修，双方电厂血量50、资金5000；维修入口原因未明，不以schema默认10HP/s或预测费用登记已对拍'),
    (MODULE, 'Behaviors/EngineerContain'): (GUESSED, '通用三国完整配置已拆分63用量并由engine_engineer a/b/c/d重放登记；本行保留三国ALLIES防御型6、日本单工程师ALLIES型TH_TombBuilding02为1及间接可达桥头堡0，共7用量/18模板；e重放三国友军半血防御修满及盟军满血拒入，仍缺苏联/帝国满血与敌方拒入、日本单人筛选维修、桥修复。ReplaceWith和ObjectStatusToSet无原版显式声明；精确进入帧仍INFERRED，不登记整模块已对拍（tests/test_simengineer.py、tests/test_inventory_contain.py、tests/test_inventory_engineer.py）'),
    (MODULE, 'Behaviors/LevelUpUpgrade'): (GUESSED, '部分：engine_levelup a创建升级触发升阶、重复持有不升级；b移除创建升级保留等级，老兵创建升级移除重给可再次升阶，英雄位0/0/0/1→0/0/1/1→0/1/1/1；engine_leveldamage a等级DAMAGE_MULT125保持到精英/英雄，单发血量47/34/34/17；engine_levelhealth a满血升级HEALTH_MULT125保持到英雄，100脚本伤害同帧冻结80/80/84/84；b残血升精英保留血量比例50/80/50/20，再扣100血为30/64/34/4，当前和最大血量均乘1.25，simlevel及test_simbench_c重放；其余等级属性、经验成长、上限、精英/英雄创建升级重给及Permanent=true未对拍，不登记整项已对拍'),
    (NUGGET, 'FireOnObjectsNugget'): (TODO, '未实现：子武器派发条件与空间锚点尚未解释；失败诊断不作为已对拍依据'),
    (NUGGET, 'ActivateLiftObjectNugget'): (TODO, 'engine_lift两轮确认需LiftObjectUpdate且SoftLanding影响清位，但Lifetime/续期释放规则未解释；保留诊断、不登记已对拍'),
    (NUGGET, 'AttachNugget'): (GUESSED, '部分：engine_attach a实测直接单发、父子状态、随父移动及目标状态/类型拒绝；仅零半径简单模块，原版复杂筛选/维修/吸血/解除/弹体未接通，不登记整项已对拍'),
    (NUGGET, 'SpecialPowerNugget'): (GUESSED, '部分：engine_spn a实测自身ARMOR派发、缺模块/类型过滤对照；仅直接单发零冷却自制技能，原版六处的OCL/模块/变装及升级门槛未接通，不登记整项已对拍'),
    (MODULE, 'Behaviors/OCLSpecialPower'): (TODO, '仅在SpecialPowerNugget处理器中识别并拒绝，未实现OCL技能执行'),
    (MODULE, 'Behaviors/ActivateModuleSpecialPower'): (TODO, '仅在SpecialPowerNugget处理器中识别并拒绝，未实现模块技能执行'),
    (NUGGET, 'TintObjectsNugget'): (NA, '纯表现：Color及Pre/Sustained/PostColorTime、Frequency/Amplitude仅控制染色动画；engine_tint pair实测2/90/2/90，独立DamageNugget解释全部伤害，test_simbench_c重放；不声称像素已验证'),
    (NUGGET, 'MetaImpactNugget'): (TODO, '剩余复杂写法：延迟、筛选、Arc、Invert等；ShockWaveSpeed/Cyclonic本轮原版用量为0也未建模。非默认Physics、坡地及V4曲线弹到达仍gap'),
    (NUGGET, 'ParalyzeNugget'): (GUESSED, '部分：engine_emp phase实测PASS16051/31066/61096、hit1；engine_empfire a实测PASS901090/901100/901080/901090，失能窗口按令不开火、到期后新令恢复；仅无筛选EMP，其他类型/筛选/装填相位未验证'),
    (NUGGET, 'StripMaxHealthPercentNugget'): (GUESSED, '部分：engine_strip exact实测PASS95/45/74，4%满血/半血与25%满血按最大血量扣减；筛选、护甲倍率、无标记伤害形式未验证，最大血量不变仍推断'),
    # Weapon round 1: scope limitations retained; explicit replay register above sets the bench state.
    (NUGGET, 'AttributeModifierNugget'): (GUESSED, '部分：engine_weaponfx attribute实测PASS，涂靶ARMOR150%、9s前到期（数据1.1s，到期帧未测）；owner/筛选/范围形式未验证，其余形式仍未验证'),
    (NUGGET, 'LineDamageNugget'): (GUESSED, '部分：engine_weaponfx line探针；实测PASS90/90/90/100验证动态线长及穿透，圆形边界GUESSED，筛选与静态线未模拟'),
    (MODULE, 'Body/ActiveBody'): (GUESSED, 'simunits.stats 读 MaxHealth（只有生命值；受伤状态、回血等另算）'),
    (MODULE, 'AI/AIUpdate'): (GUESSED, 'Sim.fight / 移动（单位 AI 的状态机细项按引擎 B 的 AI 清单推进）'),
    # the 26 the bench measured but the name rule called 未做 (checked 11-08 against sim.py / simunits.py)
    (MODULE, 'Behaviors/FireWeaponUpdate'): (GUESSED, '部分：simunits.ocl_round 把召出物的 FireWeaponNugget + '
                                                      'LifetimeUpdate 折成伤害，不模拟召出物本身'),
    (MODULE, 'Behaviors/StealthDetectorUpdate'): (TODO, f'{_NOT_IN_SIM}（没有反隐）'),
    (MODULE, 'Behaviors/GarrisonContain'): (GUESSED, 'simgarrison 同一套规则（不可争夺）；没单独上台对拍'),
    (MODULE, 'Behaviors/ToggleStatusSpecialAbilityUpdate'): (TODO, f'{_NOT_IN_SIM}（没有按钮切换状态）'),
    (MODULE, 'Behaviors/ReplaceSelfSpecialAbility'): (TODO, f'{_NOT_IN_SIM}（没有换形态）'),
    (MODULE, 'Behaviors/SpawnBehavior'): (TODO, f'{_NOT_IN_SIM}（没有母体造随从）'),
    (MODULE, 'Behaviors/SlavedUpdate'): (TODO, f'{_NOT_IN_SIM}（没有随从跟随）'),
    (MODULE, 'Behaviors/BezierProjectile'): (TODO, f'{_NOT_IN_SIM}（开火按每秒伤害直接扣血，没有弹体）'),
    (MODULE, 'Behaviors/ProjectileUpdate'): (TODO, f'{_NOT_IN_SIM}（开火按每秒伤害直接扣血，没有弹体飞行时间）'),
    (MODULE, 'Behaviors/AttachUpdate'): (GUESSED, '部分：engine_attach a验证瞬移/跟随/父子状态；只支持简单直接附着模块，死亡/维修/吸血/解除/自主扫描未建模'),
    (MODULE, 'Behaviors/StoreObjectsSpecialPower'): (TODO, f'{_NOT_IN_SIM}（没有存放单位）'),
    (MODULE, 'Behaviors/TeleportStoredObjectsSpecialPower'): (TODO, f'{_NOT_IN_SIM}（没有传送存放的单位）'),
    (MODULE, 'Behaviors/TeleportStoredObjectsUpdate'): (TODO, f'{_NOT_IN_SIM}（UNIT_TELEPORT_TO_WAYPOINT 另算）'),
    (NUGGET, 'ActivateLaserNugget'): (NA, '纯表现：Lifetime/LaserId/HitGroundFX/OverShootDistance驱动LaserState/LaserDraw；engine_laser pair实测2/90/2/90，无附加伤害或首发延迟，test_simbench_c重放'),
    (MODULE, 'Behaviors/LaserState'): (NA, '纯表现：LaserId关联光束，起止粒子/骨骼/EndOffset与ObjectStatusValidation只控制光束表现；LaserStateModule.xsd无伤害字段；engine_laser pair匹配LaserDraw/State 201，伤害由独立DamageNugget给出，test_simbench_c重放2/90/2/90'),
    (MODULE, 'Behaviors/LUAEventList'): (NA, '纯表现：EventListName连接原版ScriptEvents.xml与Scripts.lua；RA3声明可达的事件处理函数只调用模型部件显隐（及tostring），含继承；未定义的AlliedInfantryFightingFunctions无可达处理函数；C&C3升级/状态函数不可达。tests/test_inventory_lua.py静态核对游戏包与SDK声明，非上台对拍'),
    # batch 1 (work/re/l2_scripts1.md, checks/engine_scripts1.py, bench 11-08)
    (ACTION, 'TEAM_HUNT'): (GUESSED, '没交给 AI 的玩家（含玩家自己）：不动，台上量过（engine_scripts1 hunt 60 s）；'
                                     'AI 玩家的 HuntTactic 不模拟（引擎 B），碰到记 Sim.unmodeled'),
    (MODULE, 'Behaviors/ModelConditionUpgrade'): (NA, '纯表现：只加模型状态（民房/步兵按阵营换画法、支援技能画法），'
                                                     '同模板的非画法模块和原版脚本 UNIT_HAS_MODELCONDITION 都不读'
                                                     '（E 线 work/re/e_na_physics_mcu.md）'),
    (ACTION, 'NAMED_HUNT'): (GUESSED,'同 TEAM_HUNT：没交给 AI 不动（台上量过）；AI 玩家的猎杀不模拟（引擎 B）'),
    # engine A round 106: judged by what reads them
    (ACTION, 'UNIT_SET_MODELCONDITION_GENERIC'): (NA, '纯表现：设模型状态只换画法。原版脚本设的是 SUPPRESSED（a01 '
                                                      '摆拍枪战的趴下动作），SDK 数据里读 SUPPRESSED 的只有绘制模块的 '
                                                      'ConditionsYes；我们 a7 设的 USER_1 只有自由号的充能画法读'),
    (ACTION, 'UNIT_CLEAR_MODELCONDITION'): (NA, '纯表现：同 UNIT_SET_MODELCONDITION_GENERIC，清掉画法状态'),
    (MODULE, 'Behaviors/ObjectSMCHelper'): (NA, '纯表现：《将军》ObjectSMCHelper 到时清掉"定时模型状态"'
                                                '（UNIT_SET_MODELCONDITION_GENERIC 的秒数），只换画法'),
    (MODULE, 'Behaviors/AttributeModifierPoolUpdate'): (GUESSED, 'Sim.modify：属性修正挂在这个池里，到期规则'
                                                                 '（到期帧 >= 即失效、再挂覆盖不叠加）读自程序，'
                                                                 'work/re/l2_ability.md 第 51 轮'),
    (ACTION, 'SET_COOP_AI_COMMAND_UI_ENABLED'): (NA,'纯界面：开关玩家给盟友 AI 下令的按钮；模拟器的玩家没有给盟友'
                                                     '下令的命令，开关无从起作用（以后加了这个命令再算）'),
    # engine A round 107: the freeze; what the front modules are, read in the SDK data
    (MODULE, 'Behaviors/SecondaryDamageTracker'): (GUESSED, 'Sim.chill（ALIGN freeze）：冷冻光束的冷冻值累计、每秒'
                                                            '消散、按生命值分档减速、满档冻住（CryoBeamFrozenArmor '
                                                            '90000%，一碰就碎）；规则读自 SDK 数据，程序和台上都没对'),
    (NUGGET, 'SecondaryDamageNugget'): (GUESSED, 'simunits._weapons 读 Amount（不要升级的那条）→ sdps，Sim.chill'),
    (MODULE, 'Behaviors/Physics'): (TODO, '移动物理（坠落、弹跳、被击飞、倾倒）：模拟器走路按速度直走，没有物理'),
    # engine A round 108: read in the SDK data
    (MODULE, 'Behaviors/ObjectDefectionHelper'): (NA, '没人触发：原版只在 BaseObject 挂一个空的（所以每个物体都有），'
                                                      'SageXML 里没有一处 DefectorSpecialPower，脚本动作表里也没有'
                                                      '叛变；《将军》里它管"叛变后一段时间不被发现"'),
    (MODULE, 'Behaviors/BuildingDestructionBehavior'): (NA, '纯表现：建筑死后按骨骼放特效、甩碎块（CreationObject '
                                                            '如 AlliedBarracks_Debris：只有画法、寿命和碎片体积，'
                                                            '没有身体和武器）、烟尘'),
}

# Uprising only: actions / conditions only Uprising's campaign maps use, whose content type there is past the last
# case of RA3 1.13's dispatch (actions >= 573, RA3's last 572; conditions >= 156, RA3's last 155; read 11-09 from the
# Uprising maps' chunks against work/re/actions_map.json / conds_map.json). An RA3 mod cannot run them: 不涉及.
_UPRISING = '起义时刻专有：动作 / 条件号在 RA3 1.13 的脚本分派里没有，RA3 的 mod 用不了'
UPRISING_ONLY = {(ACTION, n) for n in (
    'NAMED_USE_LOGIC_COMMAND_ABILITY_ON_NAMED_POSITION', 'TELEPORT_STRUCTURE', 'TOGGLE_RADAR_UI',
    'TOGGLE_LOCK_CURRENT_SELECTION', 'SET_LAST_CREATED_UNIT_TO_REFERENCE', 'MOVE_NAMED_UNIT_TO_UNIT',
    'SET_REFERENCE_TO_RANDOM_TEAM_MEMBER', 'SET_REFERENCE_TO_FIRST_TEAM_MEMBER_IN_AREA',
    'CREATE_UNNAMED_ON_TEAM_AT_NAMED_OBJECT_LOCATION', 'TEAM_SET_DISABLED', 'EVALUATE_SCRIPT', 'PLAYER_SET_DISABLED',
    'UNIT_EXECUTE_SEQUENTIAL_SCRIPT_COPY', 'FOR_EACH_TEAM_MEMBER_EXECUTE_SCRIPT', 'MOVE_TEAM_TO_UNIT',
    'FOR_EACH_PLAYER_OBJECT_EXECUTE_SCRIPT', 'FIRE_SPECIAL_POWER_ON_UNIT', 'BORDER_SHROUD_SET_OPACITY',
    'PLAYER_FIRE_MULTI_TARGET_SPECIAL_POWER_AT_WAYPOINTS', 'SET_TEXTURE_LOOKUP_TABLE', 'SET_BLOOM_INTENSITY',
    'OVERRIDE_GLOBAL_TERRAIN_HEIGHT', 'TOGGLE_SHADER_OVERRIDE', 'AUDIO_SET_SOUNDEFFECTS_SLIDER_FADEABLE',
    'ORE_NODE_SET_MAX_GATHER_VALUE', 'RESET_CAMERA_AT_OBJECT')} | {(CONDITION, n) for n in (
    'PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA_WITH_MODELCONDITION', 'IS_OBJECT_OF_TYPE',
    'OBJECT_IS_DISGUISED_AS_TYPE')}

# presentation only: script actions that move the camera, play sound / film, draw on screen (conditions are never NA:
# a script may wait on a camera); module groups that only draw
PRESENTATION_ACTION = re.compile(
    r'^(CAMERA_|MOVE_CAMERA|ZOOM_CAMERA|PITCH_CAMERA|ROTATE_CAMERA|RESET_CAMERA|SETUP_CAMERA|FREEZE_TIME|UNFREEZE_TIME|'
    r'CAMERA|SOUND_|PLAY_SOUND|MUSIC_|PATH_MUSIC|SPEECH_|MOVIE_|CINEMATIC|DISPLAY_CINEMATIC|FADE|SCREEN_SHAKE|'
    r'DRAW_|NAMED_FLASH|SHOW_|HIDE_|LETTERBOX|OBJECT_CREATE_RADAR_EVENT|RADAR_CREATE_EVENT|EVA_|NAMED_SET_EVAC|'
    r'SET_VISUAL_SPEED|WEATHER|TERRAIN_RENDER|WATER_|SKYBOX|OVERSIZE_TERRAIN|'
    # engine A round 122 (shared/night_plan.md 11-09): UI hints, sound, render settings, selection, the save
    r'FLASH_|AUDIO_|(RESUME|SUSPEND)_BACKGROUND_SOUNDS|DISPLAY_TUTORIAL_TEXT|TOGGLE_RADAR_UI|'
    r'SET_MISSION_HOT_SPOT_VISIBILITY|LINK_MISSION_HOT_SPOT_TO_|LINK_MISSION_OBJECTIVE_TO_|'
    r'OPTIONS_|SET_TEXTURE_LOOKUP_TABLE|SET_BLOOM_INTENSITY|TOGGLE_SHADER_OVERRIDE|(DISABLE_)?BORDER_SHROUD|'
    r'SELECT_OBJECT|DESELECT|CAMPAIGN_CREATE_AUTO_SAVE)'
    # ... and anywhere in the name: a camera, a flash, an infobox, a radar blip, an outline, a colour, a sound, a clip
    r'|(_CAMERA_|_FLASH|_INFOBOX|RADAR_EVENT|_OUTLINE$|_CUSTOM_COLOR$|_HOUSE_COLOR$|PLAY_SOUND|MOVIE_PLAY|'
    r'_TIMER_DISPLAY$)')
PRESENTATION_GROUPS = {'Draws', 'ClientBehaviors'}
PRESENTATION_MODULE = re.compile(r'(Draw|Sound|Audio|Particle|FXList|Decal|Shadow|Flash|Camera|Animation|'
                                 r'^TimedOpacityUpdate$|^SubObjectsUpgrade$)', re.I)


def need(path, what):
    if not os.path.exists(path):
        raise SystemExit(f'inventory: {what} not found: {path}')


# ---- script names
def retail_uses():
    """{('act' | 'cond', key): [uses, first args]} counted in the retail campaign scripts; key refined for actions."""
    import simcoverage
    need(RETAIL_SCRIPTS, 'the retail scripts cache (python -I -X utf8 experimental/campaign/retailref.py cache)')
    rx = re.compile(r'^\s*(IF(?: NOT)?|DO|ELSE)\s+([A-Z0-9_]+)\((.*)\)\s*(?:\+[0-9a-f]+)?\s*$')
    out = {}
    names = sorted(f for f in os.listdir(RETAIL_SCRIPTS) if f.endswith('.txt'))
    if not names:
        raise SystemExit(f'inventory: no retail scripts in {RETAIL_SCRIPTS}')
    for f in names:
        for line in open(os.path.join(RETAIL_SCRIPTS, f), encoding='utf-8'):
            m = rx.match(line)
            if not m:
                continue
            kind = 'cond' if m.group(1).startswith('IF') else 'act'
            try:
                args = list(ast.literal_eval('(' + m.group(3) + ',)')) if m.group(3).strip() else []
            except (ValueError, SyntaxError):
                args = []
            key = simcoverage.refined(m.group(2), args) if kind == 'act' else m.group(2)
            got = out.setdefault((kind, key), [0, args])
            got[0] += 1
    return out


class _Inf:
    own = {}


def script_items():
    import simcoverage
    need(CATALOG, 'the retail script catalog')
    catalog = json.load(open(CATALOG, encoding='utf-8'))
    uses = retail_uses()
    for name, v in catalog.items():                     # every catalog name is an item, even if no line was parsed
        kind = 'cond' if v['kind'] == 'Condition' else 'act'
        if not any(k == kind and (key == name or key.startswith(name + ':')) for k, key in uses):
            uses[(kind, name)] = [v['uses'], []]
    modelled = simcoverage.status_modelled()
    items = []
    for (kind, key), (n, args) in uses.items():
        name, _, detail = key.partition(':')
        st = simcoverage.name_state(kind, name, args, _Inf)
        part = ACTION if kind == 'act' else CONDITION
        if st in ('core', 'shown', 'handled'):
            state, why = GUESSED, {'core': '引擎模型核心', 'shown': '只记进时间线（sim.SHOWN）', 'handled': 'Sim.act / Sim.cond 有分支'}[st]
            if detail and name == 'UNIT_CHANGE_OBJECT_STATUS' and detail not in modelled:
                state, why = TODO, f'状态位 {detail} 只记下来'
            elif detail and name in ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'NAMED_USE_COMMANDBUTTON_ABILITY',
                                     'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED') and \
                    not (name == 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT' and simcoverage.power_modelled(detail, _Inf)):
                state, why = TODO, '只记进时间线，没有效果'
        elif st == 'ignored':
            state, why = TODO, 'sim.IGNORED 明确丢掉'
        else:
            state, why = TODO, 'Sim.act / Sim.cond 不认识'
        present = part == ACTION and bool(PRESENTATION_ACTION.search(name)) and not detail
        if present and state == TODO:
            state, why = NA, '纯表现（名字规则）'
        items.append(dict(part=part, name=key, uses=n, state=state, why=why, present=present))
    return items


# ---- modules and weapon effects
def module_items():
    import retailmodules
    import simcoverage
    code = simcoverage.sim_code()
    items = []
    for (group, mtype), v in retailmodules.module_census().items():
        if group in PRESENTATION_GROUPS or PRESENTATION_MODULE.search(mtype):
            state, why = NA, f'纯表现（{group}）' if group in PRESENTATION_GROUPS else '纯表现（名字规则）'
        elif any(mtype in s for s in code):
            state, why = GUESSED, '模拟器代码里有这个名字'
        else:
            state, why = TODO, '模拟器代码里没有这个名字'
        orphan = retailmodules.orphaned(mtype)
        if orphan['campaign'] and state != NA:  # the share on templates RA3 cannot build: its own item, 不涉及
            v = dict(v, campaign=v['campaign'] - orphan['campaign'], templates=v['templates'] - orphan['templates'])
            items.append(dict(part=MODULE, name=f'{group}/{mtype}:起义专有', uses=orphan['campaign'],
                              all=orphan['templates'], state=NA, why=SPLIT_ORPHAN, eg=''))
        if mtype in SPLIT_STILL:                # the share on templates no AI moves: its own item, 不涉及
            still = retailmodules.without_ai(mtype)
            v = dict(v, campaign=v['campaign'] - still['campaign'], templates=v['templates'] - still['templates'])
            items.append(dict(part=MODULE, name=f'{group}/{mtype}:不动', uses=still['campaign'], all=still['templates'],
                              state=NA, why=SPLIT_STILL[mtype], eg=''))
        if (group, mtype) == ('Behaviors', 'EngineerContain'):
            import contain_audit
            share = contain_audit.engineer_capture_share()
            v = dict(v, campaign=v['campaign'] - share['campaign'],
                     templates=v['templates'] - share['templates'])
            items.append(dict(part=MODULE, name='Behaviors/EngineerContain:通用三国',
                              uses=share['campaign'], all=share['templates'], state=GUESSED,
                              why='完整通用配置：engine_engineer a/b/c/d；精确进入帧仍INFERRED', eg='AlliedPowerPlant'))
        items.append(dict(part=MODULE, name=f'{group}/{mtype}', uses=v['campaign'], all=v['templates'], state=state,
                          why=why, eg=', '.join(v.get('examples', [])[:2])))
    return items


# why a module's share on templates whose inheritance reaches a parent RA3's data lacks (retailmodules.orphaned) is 不涉及
SPLIT_ORPHAN = ('起义时刻专有模板：继承链上的父模板 RA3 数据里没有（SS_Fling* 的 BaseClientFlingableProp），RA3 的 mod '
                '编不过（engine_dynamics c，11-10 地图编译报 Critical），玩家在 RA3 里见不到')


# module type -> why its share on templates without an AI update module (retailmodules.without_ai) is 不涉及
SPLIT_STILL = {'Physics': '模板上没有 AIUpdate 类模块（不能下命令、没有移动器）：默认物理不让它自己动，被甩飞、击飞'
                          '另算（DynamicsUpdate、MetaImpactNugget）；原版字段全是默认（E 线 work/re/e_na_physics_mcu.md）'}


def nugget_form_slice(ntype, forms):
    """Partition weapons, never occurrences. Every effective form must fit the measured slice.

    This classifies the nugget's field spelling, not every projectile, terrain or AI consumer.
    Unrecognized fields/children stay in the unsuffixed TODO remainder (fail closed).
    """
    if not forms:
        return ''
    if ntype == 'MetaImpactNugget':
        allowed = {'id', 'ShockWaveAmount', 'ShockWaveRadius', 'ShockWaveZMult', 'ShockWaveTaperOff'}
        if all(not list(n) and set(n.attrib) <= allowed
               and {'ShockWaveAmount', 'ShockWaveRadius'} <= set(n.attrib) for n in forms):
            return ':普通无延迟显式Z' if all('ShockWaveZMult' in n.attrib for n in forms) else ':省略Z默认值'
    elif ntype == 'InformTargetNugget':
        allowed = {'id', 'MinTimeToImpactFudgeFactor', 'MaxTimeToImpactFudgeFactor'}
        if all(not list(n) and set(n.attrib) <= allowed
               and float(n.get('MinTimeToImpactFudgeFactor', '.85')) == .85
               for n in forms):
            maxima = {float(n.get('MaxTimeToImpactFudgeFactor', '1.15')) for n in forms}
            if maxima == {1.15}:
                return ':默认系数目标通知'
            if maxima == {1.6}:
                return ':Max1.6目标通知'
    return ''


NUGGET_SCOPES = {
    'MetaImpactNugget:普通无延迟显式Z': '仅普通弹头碰撞事件→默认Physics轨迹；engine_knock_probe land/late邻人5帧落(2380,3740)、目标99%/邻人100%。到达帧为台上输入，非完整V4曲线弹回放；直击方向/落点网格/选人仍INFERRED',
    'MetaImpactNugget:省略Z默认值': '仅普通无延迟弹头省略ShockWaveZMult→SDK默认1及默认Physics轨迹；engine_knock_z a高度93邻人14帧落(2420,3740)、目标99%/邻人100%。碰撞时刻/爆心为台上输入；直击噪声方向/网格/选人仍INFERRED，完整曲线弹/坡地/筛选未对拍',
    'InformTargetNugget:默认系数目标通知': '仅默认Min=.85/Max=1.15的目标通知→来弹表/矿车预计伤害开甲；engine_inform_probe a/off录入302、hit377、exp404、删除389，347帧入窗。半径/历史/海啸/忍者及完整AI调度不在本登记范围，完整脚本仍xfail',
    'InformTargetNugget:Max1.6目标通知': '仅Min=.85/Max=1.6目标通知→来弹表；engine_inform_max a单变量对照录入302、hit377不变、exp444（默认404）、受伤389删除，矿车提前开甲。自然过期清理边界/半径/历史/海啸/忍者/完整AI调度未对拍，完整脚本仍xfail',
}


def nugget_items():
    import retailmodules
    import simcoverage
    code = simcoverage.sim_code()
    items = []
    for ntype, v in retailmodules.weapon_census().items():
        if ntype in ('MetaImpactNugget', 'InformTargetNugget'):
            groups = collections.defaultdict(list)
            st = retailmodules._load()
            for k, (name, _, _) in st['weapons'].items():
                forms = [n for n in retailmodules.effective_weapon_forms(k, st) if retailmodules._tag(n) == ntype]
                if forms:
                    groups[nugget_form_slice(ntype, forms)].append(name)
            assert sum(map(len, groups.values())) == v['weapons'], (ntype, groups)
            for suffix, names in groups.items():
                name = ntype + suffix
                items.append(dict(part=NUGGET, name=name, uses=len(names), state=TODO,
                                  why=NUGGET_SCOPES.get(name, '未覆盖的原版字段写法'),
                                  eg=', '.join(names[:2]), weapon_ids=names))
            continue
        hit = any(ntype in s for s in code)
        items.append(dict(part=NUGGET, name=ntype, uses=v['weapons'], state=GUESSED if hit else TODO,
                          why='模拟器代码里有这个名字' if hit else '模拟器代码里没有这个名字',
                          eg=', '.join(v.get('examples', [])[:2])))
    return items


CHECKS = os.path.join(HERE, 'checks')
ENGINE_DOCS = os.path.join(ROOT, 'docs', 'engine')


def bench_sources():
    """[(source, text)] where bench measurements live: the engine probes (checks/engine_*.py, run with cnv_check on the
    bench, their readings in the docstrings) and the lines of docs/engine/*.md marked measured (**测**, not 未实测)."""
    need(CHECKS, 'the bench checks')
    need(ENGINE_DOCS, 'the engine docs')
    out = []
    for f in sorted(os.listdir(CHECKS)):
        if f.startswith('engine_') and f.endswith('.py'):
            out.append((f'checks/{f}', open(os.path.join(CHECKS, f), encoding='utf-8').read()))
    for f in sorted(os.listdir(ENGINE_DOCS)):
        if f.endswith('.md') and f != os.path.basename(OUT):
            lines = [x for x in open(os.path.join(ENGINE_DOCS, f), encoding='utf-8')
                     if '测' in x.replace('未实测', '').replace('推断', '') and '未实测' not in x]
            out.append((f'docs/engine/{f}', ''.join(lines)))
    if not out:
        raise SystemExit('inventory: no bench sources found')
    return out


TESTS = os.path.join(ROOT, 'tests')
PROBE_NAME = re.compile(r'(?<![A-Za-z0-9_])(engine_[A-Za-z0-9_]+)')


def tested_probes(tests=TESTS, checks=CHECKS):
    """The bench probes a test holds the simulator to: {'checks/engine_X.py'} for each probe a test file names --
    'engine_X', or a variant 'engine_X_<v>' that is not a probe of its own (the longest probe name it starts with).
    Named, not only quoted as a build: tests replay a probe by its build name (_sim_resolve('engine_seal', ..)), by
    its bench mission (simai.run('aiskirm') -- 'bench engine_aiskirm c' in the test) or by its layout rebuilt
    (engine_mining's), and each cites the probe whose readings it asserts. A probe no test names is a reading only."""
    stems = {f[:-3] for f in os.listdir(checks) if f.startswith('engine_') and f.endswith('.py')}
    out = set()
    for f in sorted(os.listdir(tests)):
        if not f.endswith('.py'):
            continue
        for name in PROBE_NAME.findall(open(os.path.join(tests, f), encoding='utf-8').read()):
            while name not in stems and '_' in name[len('engine_'):]:
                name = name.rsplit('_', 1)[0]
            if name in stems:
                out.add(f'checks/{name}.py')
    return out


def bench_verdict(rx, src, tested):
    """(tested, measured): the first bench source naming `rx` that a test runs (tested_probes), and the first naming it
    at all. Only the first makes an item 已对拍 (ADR 0026: matched against the bench by a test); a reading on the bench
    no test replays (a probe's docstring, a docs/engine line) leaves it 推断, noted 台上量过."""
    hits = [s for s, text in src if rx.search(text)]
    return next((s for s in hits if s in tested), None), (hits[0] if hits else None)


def benched(items, src=None, tested=None):
    """An implemented item (推断) whose name a bench probe a test runs names becomes 已对拍, citing that probe; one only
    measured on the bench (no test runs that probe, or only a docs/engine line) stays 推断 with 台上量过 noted."""
    src = bench_sources() if src is None else src
    tested = tested_probes() if tested is None else tested
    for it in items:
        if it['state'] not in (GUESSED, TODO):
            continue
        name = it['name'].split('/')[-1].split(':')[-1] if it['part'] == MODULE else it['name'].split(':')[-1]
        rx = re.compile(r'(?<![A-Za-z0-9_])' + re.escape(name) + r'(?![A-Za-z0-9_])')
        run, hit = bench_verdict(rx, src, tested)
        if run and it['state'] == GUESSED:
            it['state'], it['why'] = BENCHED, f'{it["why"]}；台上量过、测试对拍：{run}'
        elif hit and it['state'] == GUESSED:
            it['why'] = f'{it["why"]}；台上量过（{hit}），没有测试跑这个台子'
        elif hit and it['part'] in (MODULE, NUGGET):       # measured, but the name rule finds no code: look (NOTES)
            it['why'] = f'{it["why"]}；**待核**：台上量过（{hit}），可能用别的名字实现了'
    return items


def apply_registers(items):
    benched(items)
    for it in items:
        if it.pop('present', False) and it['state'] == GUESSED:     # presentation, has code (often sim.SHOWN), not
            it['state'], it['why'] = NA, f'纯表现（名字规则）；{it["why"]}'     # measured: a measured one stays 已对拍
        k = (it['part'], it['name'])
        if k in NOTES:
            it['state'], it['why'] = NOTES[k]
        if k in BENCHED_TESTS:
            scope = NUGGET_SCOPES.get(it['name']) if it['part'] == NUGGET else None
            it['state'], it['why'] = BENCHED, BENCHED_TESTS[k] + ('；' + scope if scope else '')
        if (it['part'], it['name'].split(':')[0]) in UPRISING_ONLY:
            it['state'], it['why'] = NA, _UPRISING
    return items


def collect(parts=PARTS):
    items = []
    if ACTION in parts or CONDITION in parts:
        items += [i for i in script_items() if i['part'] in parts]
    if MODULE in parts:
        items += module_items()
    if NUGGET in parts:
        items += nugget_items()
    items = apply_registers(items)
    if AI in parts:                                 # engine B: its own state rules and registers (inventory_ai.py)
        import inventory_ai
        items += inventory_ai.ai_items(bench_sources(), tested_probes())
    return items


def order(items):
    return sorted(items, key=lambda i: (PARTS.index(i['part']), -i['uses'], -i.get('all', 0), i['name']))


MAIN = '按用量已对拍'
SUMMARY_COLUMNS = (MAIN, '项数', BENCHED, GUESSED, TODO, NA, '按用量已有（已对拍+推断）')


def summary(items):
    """[(part, {column: value})], the summary table's rows. The main number is MAIN: the share of the retail uses that
    are 已对拍 (推断 does not count; 不涉及 is left out of the total)."""
    by = collections.defaultdict(list)
    for it in items:
        by[it['part']].append(it)
    rows = []
    for part in PARTS:
        xs = by.get(part, [])
        if not xs:
            continue
        c = collections.Counter(i['state'] for i in xs)
        rel = [i for i in xs if i['state'] != NA]
        w = sum(i['uses'] for i in rel) or 1
        pct = lambda states: 100 * sum(i['uses'] for i in rel if i['state'] in states) / w  # noqa: E731
        rows.append((part, {MAIN: pct({BENCHED}), '项数': len(xs), BENCHED: c[BENCHED], GUESSED: c[GUESSED],
                            TODO: c[TODO], NA: c[NA], '按用量已有（已对拍+推断）': pct({BENCHED, GUESSED})}))
    return rows


def render(items):
    by = collections.defaultdict(list)
    for it in order(items):
        by[it['part']].append(it)
    out = ['# 原版功能总清单（引擎 A：脚本层、物体模块、武器效果；引擎 B：AI）', '',
           '由 `experimental/cnv/inventory.py` 从原版数据生成，**别手改**；`tests/test_inventory.py` 在它过期时变红。'
           '状态与判定规则见脚本 docstring（ADR 0026）。用量：脚本 = 原版战役脚本里出现的次数；模块 = 原版战役地图里摆了的、'
           '用到它的物体种数（括号里是全部物体种数）；武器效果 = 用到它的原版武器数；'
           'AI = 原版 AI 数据（SDK SkirmishAI，含战役关的 AI 状态）里写它的次数，判定规则见 `inventory_ai.py`。'
           '**主数字是"按用量已对拍"**：已对拍项的用量占全部用量的比例，推断不算，不涉及不进分母；目标每部分 90%。', '',
           '| 部分 | ' + ' | '.join(SUMMARY_COLUMNS) + ' |', '|---' * (len(SUMMARY_COLUMNS) + 1) + '|']
    for part, row in summary(items):
        cells = [f'**{row[c]:.0f}%**' if c == MAIN else f'{row[c]:.0f}%' if c.startswith('按用量') else str(row[c])
                 for c in SUMMARY_COLUMNS]
        out.append(f'| {part} | ' + ' | '.join(cells) + ' |')
    for part in PARTS:
        xs = by.get(part, [])
        if not xs:
            continue
        out += ['', f'## {part}', '', '| 状态 | 名字 | 用量 | 说明 |', '|---|---|---|---|']
        for i in xs:
            n = f"{i['uses']}" + (f" ({i['all']})" if 'all' in i else '')
            why = i['why'] + (f"；例：{i['eg']}" if i.get('eg') else '')
            out.append(f"| {i['state']} | `{i['name']}` | {n} | {why} |")
    return '\n'.join(out) + '\n'


def gaps(items, k=20):
    """The k most used items not done, across the parts."""
    return sorted((i for i in items if i['state'] == TODO), key=lambda i: (-i['uses'], i['name']))[:k]


def main():
    check = '--check' in sys.argv
    items = collect()
    text = render(items)
    old = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
    if check:
        print('inventory: up to date' if old == text else 'inventory: STALE (run experimental/cnv/inventory.py)')
        return 0 if old == text else 1
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print('\n'.join(text.splitlines()[4:4 + 2 + len(PARTS)]))
    print('top gaps:')
    for i in gaps(items):
        print(f"  {i['part']} {i['name']} {i['uses']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
