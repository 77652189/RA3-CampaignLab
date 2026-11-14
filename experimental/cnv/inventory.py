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
the test); 推断 -- the simulator has code for it, no bench comparison yet; 未做 -- nothing; 不涉及 -- presentation / statistics only
(a rule below, by name or module group: never a list; a presentation action measured on the bench stays 已对拍).
How "has code" is told:
  script names    simcoverage.name_state: the engine model's core, a Sim.act / Sim.cond branch (probed with a retail
                  use's own arguments), sim.SHOWN; sim.IGNORED is 未做 (dropped on purpose, may hide play)
  modules, nuggets  the type's name is a string constant in sim.py / simunits.py / simproxy.py (simcoverage.sim_code)
                  -- a first cut: a module read under another name shows as 未做 until NOTES says otherwise

  python -I -X utf8 experimental/cnv/inventory.py            regenerate docs/engine/inventory.md, print the summary
  python -I -X utf8 experimental/cnv/inventory.py --check    exit 1 when the file is stale

Our 9 levels (LEVEL_COLUMN): each item is marked with the levels that use it -- engine A's parts as inventory_levels.py
counts them (the scripts as built, the templates and weapons reached), the AI part as inventory_ai.py levels (what the
enemy AI's personality reaches) -- and the summary's LEVEL_MAIN is 按用量已对拍 over those items only (the user, 11-11:
finish what our 9 levels use first).
"""
import ast
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]
import labpaths  # noqa: E402

CATALOG = os.path.join(ROOT, 'experimental', 'campaign', 'script_catalog.json')
RETAIL_SCRIPTS = os.path.join(labpaths.WORK, 'retailref')
OUT = os.path.join(ROOT, 'docs', 'engine', 'inventory.md')

BENCHED, GUESSED, TODO, NA = '已对拍', '推断', '未做', '不涉及'
STATES = (BENCHED, GUESSED, TODO, NA)
ACTION, CONDITION, MODULE, NUGGET, AI = '脚本动作', '脚本条件', '物体模块', '武器效果', 'AI'
PARTS = (ACTION, CONDITION, MODULE, NUGGET, AI)     # AI: engine B's part, its own rules in inventory_ai.py

# (part, name) -> 'tests/<file>.py::<test>': the bench comparison that backs the item (the guard checks the test exists)
BENCHED_TESTS = {
    (NUGGET, 'SpecialPowerNugget:涂靶升级门槛'):
        'tests/test_special_power_nugget.py::test_special_power_nugget_retail_painter_consumer',
    # E65 coordinator closure after four slices; only measured Iron Curtain dispatch.
    (MODULE, 'Behaviors/OCLSpecialPower'):
        'tests/test_simocl.py::test_iron_curtain_zero_count_ocl_reference',
    # E54 coordinator closure: measured straight startup; NOTES retains unmeasured Jet states.
    (MODULE, 'AI/JetAIUpdate'):
        'tests/test_simjet.py::test_jet_vindicator_first_entry_frame_matches_bench',
    # E52 coordinator closure: three measured initial health slices, shared gaps retained in NOTES.
    (MODULE, 'Behaviors/RepairUpdate'):
        'tests/test_simrepair_ai.py::test_ai_repair_funded_and_zero_credit_final_readings',
    # E47 coordinator closure after three slices; NOTES preserves the shared-template gaps.
    (MODULE, 'Behaviors/SpawnBehavior'):
        'tests/test_simspawn.py::test_spawn_initial_burst_and_parent_kill_delete_match_named_bench',
    (MODULE, 'Behaviors/InfiltratorContain:ENERGY'):
        'tests/test_siminfiltrator.py::test_spy_power_plant_as_on_the_bench',
    # E30 closure: measured creation grants and rank modifiers; NOTES keeps the remaining gaps visible.
    (MODULE, 'Behaviors/LevelUpUpgrade'):
        'tests/test_simbench_c.py::test_levelup_creation_grants_reach_heroic_only_after_three_distinct_triggers',
    # E37 coordinator closure: measured proxy/count interfaces; NOTES retains unmeasured bridge gaps.
    (MODULE, 'Body/ManagerBody'):
        'tests/test_simmanagerbody.py::test_manager_body_script_damage_preserves_retail_bridge_proxy',
    (MODULE, 'Behaviors/BridgeBuilder'):
        'tests/test_simbridgebuilder.py::test_bridgebuilder_counts_short_and_long_retail_bridges',
    (MODULE, 'Behaviors/EngineerContain:通用三国'):
        'tests/test_simengineer.py::test_engineer_soviet_japan_captures_as_on_the_bench',
    (MODULE, 'Behaviors/EngineerContain:三国ALLIES'):
        'tests/test_simengineer.py::test_engineer_allied_defence_refusal_soviet_japan_as_on_the_bench',
    # Field-form coverage only: recorded collision / incoming-event replay, not full retail flight or every consumer.
    (NUGGET, 'MetaImpactNugget:普通无延迟显式Z'):
        'tests/test_meta_impact.py::test_meta_impact_collision_event_replays_engine_knock_probe_neighbour_five_frames',
    (NUGGET, 'MetaImpactNugget:镰刀敌我筛选'):
        'tests/test_meta_impact.py::test_meta_impact_relation_collision_replays_observed_selection',
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
    # engine line A round 208: retail-campaign conditions batch 1 (checks/engine_conds.py team / fight); the
    # TEAM_INSIDE_AREA k other than 0 is benched only as "no Guardian passes 1 / 3 / 7" (air / ships INFERRED)
    **{(CONDITION, n): 'tests/test_simbench.py::test_conds_team_as_the_bench' for n in (
        'TEAM_HAS_UNITS', 'TEAM_INSIDE_AREA_PARTIALLY', 'TEAM_INSIDE_AREA_ENTIRELY', 'TEAM_CREATED', 'TEAM_DESTROYED',
        'TEAM_SOME_HAVE_OBJECT_STATUS', 'TEAM_ALL_HAS_OBJECT_STATUS', 'PLAYER_HAS_CREDITS', 'CURRENT_PLATFORM',
        'NAMED_EXITED_AREA')},
    **{(CONDITION, n): 'tests/test_simbench.py::test_conds_fight_as_the_bench' for n in (
        'TEAM_ATTACKED_BY_PLAYER', 'SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER', 'TEAM_ATTACKED_BY_OBJECTTYPE',
        'NAMED_ATTACKED_BY_OBJECTTYPE', 'PLAYER_HAS_KILLED_NAMED_UNIT', 'PLAYER_HAS_KILLED_TYPE_UNITS',
        'NAMED_HAS_KILLED_COMPARISON_UNIT_TYPE')},
    # engine line A round 210: batch 2 (checks/engine_conds.py sight): sight / discovery, the hot spot switch
    **{(CONDITION, n): 'tests/test_simbench.py::test_conds_sight_as_the_bench' for n in (
        'ENEMY_SIGHTED_BY_TEAM', 'TEAM_DISCOVERED', 'MISSION_HOT_SPOT_ACTIVE')},
    (ACTION, 'SET_MISSION_HOT_SPOT_ACTIVENESS'): 'tests/test_simbench.py::test_conds_sight_as_the_bench',
    # engine line A round 211: retail-campaign actions batch 1 (checks/engine_acts.py flow; NAMED_SET_DISABLED benched
    # for EMP only, the other types INFERRED the same hold)
    **{(ACTION, n): 'tests/test_simbench.py::test_acts_flow_as_the_bench' for n in (
        'UNIT_CHANGE_OBJECT_STATUS:SHROUD_REVEAL_TO_ALL', 'UNIT_CHANGE_OBJECT_STATUS:SKIRMISH_AI_DO_NOT_ATTACK',
        'TEAM_ALLOW_AI_AUTOACQUIRE', 'NAMED_SET_DISABLED', 'NAMED_FORCE_ATTACK_NAMED', 'TEAM_SET_STANCE')},
    # round 212: batch 2 (checks/engine_acts2.py seq / more; the ground fire's own damage not benched, none simulated)
    (ACTION, 'UNIT_EXECUTE_SEQUENTIAL_SCRIPT'): 'tests/test_simbench.py::test_acts_seq_as_the_bench',
    **{(ACTION, n): 'tests/test_simbench.py::test_acts_more_as_the_bench' for n in (
        'TEAM_GARRISON_TEAM_INSTANTLY', 'NAMED_FORCE_ATTACK_WAYPOINT', 'UNIT_KILL_ALL_IN_AREA',
        'ATTACK_MOVE_TEAM_TO_NAMED_OBJECT', 'MAP_REVEAL_PERMANENTLY_IN_TRIGGER', 'MAP_UNDO_REVEAL_PERMANENTLY_IN_TRIGGER')},
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
    # engine A rounds 162-173: knock-back curve, landing, hold, gates, fire, the crash's fall (checks/engine_knock_probe,
    # engine_knock_water, engine_crash_fall; the whole list in NOTES' Physics line)
    (MODULE, 'Behaviors/Physics'):
        'tests/test_meta_impact.py::test_physics_p5_a_shot_down_wreck_falls_the_knock_curve_under_its_own_gravity',
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
    # engine_unpack mcv / egg (bench 11-10, round 138) and engine_pack a / s / j (bench 11-11, round 159): an MCV or
    # an egg drives to its point and turns into the replacement, a yard packs into its MCV at once and the MCV stands
    # ~44 frames -- tests/test_simbench.py test_*deploys_at_a_far_waypoint*, test_a_yard_packs_*
    (MODULE, 'Behaviors/ReplaceSelfSpecialAbility'):
        'tests/test_simbench.py::test_a_yard_packs_into_its_mcv_at_once_and_the_mcv_stands_before_it_drives',
    # engine_production a / e (out at UnitCreatePoint, the door 10 frames), h / i and engine_rally tank (bench 11-11,
    # round 159): the unit stops 40 beyond NaturalRallyPoint on the centre -> rally line (sim.RALLY_PUSH, fitted);
    # gap: ExitDelaySeconds (0.07 s between two units), h's barracks stop 1-2 units off (strict xfail)
    (MODULE, 'Behaviors/QueueProductionExitUpdate'):
        'tests/test_simbench.py::test_a_new_unit_stops_beyond_the_natural_rally_point_as_the_bench',
    # engine line A round 160: engine_wfire all (bench 11-11): Yuriko's blast (radius damage after the nugget's
    # delay), Natasha's pilot snipe (walks till the target's edge is in StartAbilityRange, UnpackTime, the vehicle
    # neutral), the dog's bark (EMP on enemy infantry in the radius); the caster stands Pack / Freeze. Gaps: the
    # blast's MetaImpactNugget push, the ships' / Cryocopter's / superweapons' (WeaponSlot, FaceTarget), the sickle's
    # leap (BezierProjectile), the player's click reload
    (MODULE, 'Behaviors/WeaponFireSpecialAbilityUpdate'):
        'tests/test_simbench.py::test_a_weapon_fire_ability_goes_off_after_its_unpack_and_holds_the_caster_through_its_pack',
    (MODULE, 'Behaviors/EjectPassengersSpecialAbilityUpdate'):
        'tests/test_simbench.py::test_transport_the_man_cannon_throws_one_every_half_second_and_a_killed_transport_kills_its_men',
    # engine line A round 156: engine_toggle a-f, bench 11-11 (Sim.toggle_press): six of our 9 levels' toggles -- a
    # press moves to the next ToggleState (its ObjectStatus / AttributeModifier), the first state's bits from the
    # start, UnpackTime delays, PackTime does not, a DisabledType state takes no press (INFERRED cause). Not modelled:
    # ModelConditions, ArmorSet / LocomotorSet (the VX's / Tengu's jet form), TriggerAttributeModifier
    (MODULE, 'Behaviors/ToggleStatusSpecialAbilityUpdate'):
        'tests/test_simbench_c.py::test_toggle_status_a_press_moves_to_the_next_state_unpack_delays_it_and_a_held_state_takes_no_press',
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
    (ACTION, 'PLAYER_TOGGLE_RESOURCE_SHARING'): (GUESSED, 'A211 engine_acts:flow：两边都开共享的盟友之间，脚本给钱（PLAYER_GIVE_MONEY）不分（1001 / 1000 / 2001 原样）；D 119 读的码是采矿等收入平分给共享盟友，模拟器没做、没上台（要采矿台子）'),
    (MODULE, 'Behaviors/AutoDepositUpdate'): (GUESSED, 'E146 engine_objectbatch:a/b：原版SwissBank克隆有/无模块的钱包，on逐次+5至60、12秒删除后稳定，off全0；具名测试按实际60/0回放。只量已有归属产钱，不晋升整项；占领奖金/驻军/上限/修理仍gap；见work/re/e146_objectbatch.md'),
    (MODULE, 'Behaviors/HealCrateCollide'): (TODO, 'E146 engine_objectbatch:a/b有/无模块均未治疗，步兵始终50/50；b中立箱且到位成立，仍无效，两轮后暂停；不把负结果登记成效果已对拍。SecretFile原XML含当前schema不接受的属性，未冒充普通HealCrate等价；碰撞派发前置待查；见work/re/e146_objectbatch.md'),
    (MODULE, 'Behaviors/LoseHealthUpdate'): (TODO, 'E146 engine_objectbatch:a/b：原船完整模块移植480HP坦克，HealthTrigger=101%/0%均无耗血，两路100/100；b已确认toggle/铁幕状态成立。两轮后暂停，移植激活资格待查，未推猜测实现、不晋升整项；见work/re/e146_objectbatch.md'),
    (MODULE, 'Behaviors/CommandSetUpgrade'): (GUESSED, 'E145单图engine_modulebatch:a：空初始菜单的兵营，授Tech2前产物0/0、授后有/无模块产物1/0。菜单切换解析已有；整链路具名回放strict xfail：生产层factories按未持升级的初始菜单识别工厂，故模型仍0/0，需B接口修复。未晋升整项；见work/re/e145_modulebatch.md'),
    (MODULE, 'Behaviors/MonitorSpecialPowerTimerUpdate'): (TODO, 'E145单图engine_modulebatch:a：原版质子炮宿主有/无模块，设技能就绪后SPECIALPOWER1_READY为1/0，设冷却后0/0。模型倒计时脚本入口和模块就绪输出仍gap；具名回放strict xfail，需A倒计时接口，不按纯表现排除；见work/re/e145_modulebatch.md'),
    (MODULE, 'Behaviors/AttackAssistResponseBehavior'): (TODO, 'E144派发诊断：engine_attackassist a两次准备运行均进关前崩溃，无台上读数；最终原版光谱塔宿主配方已修本地模块引用及结构武器掩码，尚未上台，暂停追加运行直至启动原因解释。tests/test_simattackassist.py严格xfail仅保留待验预测，不作已对拍证据；响应武器派发/原版增伤/时序均gap，模型未改；见work/re/e144_attackassist.md'),
    (MODULE, 'Behaviors/CircularDamageUpdate'): (TODO, 'E143最小消费诊断：engine_circular a/b/c/d具名回放仅保留负结果，不登记效果已对拍。陆地无ONLY_ON_WATER、MaxRadius175/ArcDistance50、径向50/100/150靶；正常/删激活/删模块/持续开火对照，消费前置仍未解释，未实现接口。Lifetime推进、SweepWeapon实际派发、水面过滤、重复激活和死亡清理均gap；tests/test_simcircular.py；假设表见work/re/e143_circular_gate.md'),
    (NUGGET, 'ActivateCircularDamageNugget'): (TODO, 'C线前置门禁：原版TeslaNova的Lifetime决定扩散速度，伤害来自宿主CircularDamageUpdate的SweepWeapon；E线模块消费接口尚缺，不能用直伤或DOT代替。0局、无台上读数，不登记已对拍；接口需求与假设表见work/re/c_circular_gate_report.md'),
    (NUGGET, 'ReportWeaponFiredStatNugget'): (NA, '纯统计（C线工单允许排除）：只记录玩家武器开火次数；原版两份空配置附于SovietVacuumBomb / ParticleCannonWeapon，伤害与创建物体由独立WeaponOCLNugget负责。保留用量2，不登记已对拍；未上台，不模拟战后统计；证据见work/re/c_reportstat_report.md'),
    (MODULE, 'Behaviors/PassiveAreaEffectBehavior'): (GUESSED, 'E70范围/兵种/状态开关和E74分批治疗具名回放保留。E145单图engine_modulebatch:a：MaxBeneficiaries=1/0两组，早期受益人数1/3、后期3/3，敌方均50%不回血；已补0/1上限，tests/test_simmodulebatch.py按名断言台上读数。具体受益身份次序、共用任务帧相位和SDK换算跳幅INFERRED；时钟来源/动态创建与重开/调查周期/叠加/友方跨玩家/自身受益/附着无人机/更大上限仍gap，不登记整项已对拍；见work/re/e145_modulebatch.md、e_passive_e74.md'),
    (MODULE, 'Behaviors/TrackDamage'): (TODO, 'E69静态核实：6个SDK配置均InstantWeaponsOnly=true，TimeToTrack为0/1/2s；现有expected_damage只接来弹，历史伤害仍gap。与C线瞬发历史接口工单重叠，E暂停独立探针；尚无本模块具名实测回放，不登记已对拍、不改分母；见work/re/e_trackdamage_e69.md'),
    (CONDITION, 'ENEMY_SIGHTED'): (GUESSED, '部分：engine_levelvision a普通/英雄幻影在近点移除后对工程师240/310距离四路0/101/0/100，test_simbench_c重放；仅敌对关系范围查询已量，其他关系、隐形与精确边界未对拍，不登记整项'),
    (MODULE, 'Behaviors/InfiltratorContain'): (GUESSED, 'E142整项收束，不再细切宿主；ENERGY独立已对拍4用量/6模板，本行10配置30用量/32模板仍待闭合，不登记整组或整模块已对拍。逐配置边界：KILL 1用量/1模板部分已测（engine_infkill a，敌消耗/友拒入、满血不换主；tests/test_siminfiltrator_kill.py）；PARALYZE 3用量/3模板部分已测（三国engine_infpara a/b、engine_infpsov a、engine_infpjap a移动及engine_infpatk/engine_infasov/engine_infajap a攻击，tests/test_siminfiltrator_paralyze.py）；普通VISION 5用量/5模板部分已测且暂停扩宿主（engine_infvis a/b稳定窗通过，c实测s18=0/s19起1但模型未支持，严格xfail）；港口阻断VISION 1用量/1模板未测；STEAL_MONEY 3用量/4模板暂停（engine_infmon a量到2000转账后有矿车收入，未实现、严格xfail）；车辆VISION_UNITS 4用量/4模板暂停（engine_infveh a量到可见位间歇1/0，未实现、严格xfail）；飞机VISION_UNITS 2用量/2模板未测；步兵VISION_UNITS 3用量/3模板未测；舰船VISION_UNITS 3用量/3模板未测；RESET 5用量/6模板暂停（engine_infreset a/b就绪与真实冷却未闭环、严格xfail）。VISION/STEAL_MONEY/VISION_UNITS/RESET具名回放见tests/test_siminfiltrator.py。INFERRED：进入距离/生效和精确到期、VISION约5秒延迟/半径映射/宿主死亡清理、KILL致死清理；gap：其他间谍/模板、PARALYZE生产/重复进入/旧攻击订单、KILL抛飞/死亡效果、VISION持久性/重复进入及未测配置。已测PARALYZE不代表其余配置已测；完整逐配置证据与原始读数指针见work/re/e142_infiltrator_closure.md'),
    (MODULE, 'Behaviors/InfiltratorContain:ENERGY'): (BENCHED, '总控11-11授权按配置组收尾：engine_infiltrator a/b/c/d按名字重放，盟军间谍对盟/苏/帝普通电厂及帝国忍者对盟军电厂，敌方进入者消耗、建筑满血不换主、100电量停电约20秒并恢复，友军拒入且存活；gap：其他电量/苏联超级电厂、重复进入续期、精确时序和默认状态分支仍未对拍，不表示全字段全模板已验证'),
    (MODULE, 'Behaviors/TrackIncomingWeaponFireBehavior'): (TODO, '部分：engine_inform_probe a/off通知记录回放验证录入、30帧窗口、来源与武器匹配删除和过期清理；精确过期边界INFERRED，原版完整调度/历史伤害仍gap，不靠名字命中晋升整项'),
    (MODULE, 'Behaviors/RepairUpdate'): (BENCHED, 'repairai a/repairq a/repairt a/repairzero a按名重放：开局足额资金、默认1000HP/800造价电厂初始50%/25%/75%血约10HP/s修满、实扣100/225/25，费用按缺血比例平方；零资金无经济不修；tests/test_simrepair_ai.py。只支持已测配置，完整配置门禁保留；gap：玩家入口、废墟维修、受伤停修、其他初始血量/造价/速率及资金耗尽未测；AI启动相位INFERRED；按总控11-11三切片收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母'),
    (MODULE, 'Behaviors/EngineerContain:通用三国'): (BENCHED, '已测范围：engine_engineer a/b/c/d普通进入，三国工程师中立/敌方半血电厂占领并消耗、友军半血修满并消耗、满血拒入且存活；按完整配置匹配登记63用量/87模板；gap：精确进入帧仍INFERRED；日本单人ALLIES和桥配置保留在未对拍残余行，不借本组登记'),
    (MODULE, 'Behaviors/EngineerContain:三国ALLIES'): (BENCHED, '已测范围：engine_engineer a/e/f普通进入，三国工程师友军半血防御修满并消耗、满血及敌方拒入且存活，目标归属不变；按完整配置匹配登记6用量/7模板；gap：精确进入帧仍INFERRED；日本单人ALLIES和桥配置保留在未对拍残余行，不借本组登记'),
    (MODULE, 'Behaviors/EngineerContain'): (GUESSED, '总控11-11授权工程师组收尾、不再上台；已测通用三国63用量及三国ALLIES6用量分别登记；gap：日本单人ALLIES型TH_TombBuilding02为1用量/1模板，筛选与维修未对拍；间接可达桥头堡为0用量/10模板，桥修复未对拍；本行共1用量/11模板。ReplaceWith和ObjectStatusToSet无原版显式声明；精确进入帧仍INFERRED，不登记整模块已对拍（tests/test_simengineer.py、tests/test_inventory_contain.py、tests/test_inventory_engineer.py）'),
    (MODULE, 'Behaviors/LevelUpUpgrade'): (BENCHED, '已测范围：engine_levelup a创建升级触发升阶、重复持有不升级；b移除创建升级保留等级，老兵创建升级移除重给可再次升阶，英雄位0/0/0/1→0/0/1/1→0/1/1/1；c独立精英/英雄创建升级各自移除重给两次，首次仍0/0/0/1、第二次0/1/1/1；engine_leveldamage a等级DAMAGE_MULT125保持到精英/英雄，单发血量47/34/34/17；engine_levelhealth a满血升级HEALTH_MULT125保持到英雄，100脚本伤害同帧冻结80/80/84/84；b残血升精英保留血量比例50/80/50/20，再扣100血为30/64/34/4，当前和最大血量均乘1.25，simlevel及test_simbench_c重放；engine_levelrange a原版幻影普通炮125、英雄炮150叠加RANGE125%为187.5，220距离仅英雄命中、260距离均未命中，四路100/10100/100/10100→100/10017/100/10100，离位异常均0；engine_levelrate a幻影普通/直接英雄武器/创建英雄/创建精英三段周期25/25/20/25帧，最终血量84/80/68/80，ROF不增加单发伤害；仅此离散单发炮配置已量，射速分段取整/其他武器仍未对拍；engine_levelshroud a原版幻影基础揭雾500、创建英雄SHROUD_CLEARING125%预测625，580/750距离普通/英雄四路1/1/1/1→1/111/1/101，近点始终可见且无离位；仅此模板配置已量，精确边界未对拍；engine_levelvision a原版幻影普通/创建英雄对小包围体工程师240/310距离ENEMY_SIGHTED四路11/11/11/11→0/0/0/0→0/101/0/100，近点在正式窗口前删除且无离位，支持VISION125按1.25倍率为250的预测；仅脚本范围查询已量，精确边界/自动索敌未对拍；gap：英雄自动索敌、精确射程/揭雾/视野边界、射速分段取整/其他武器、其余模板/等级属性、经验成长、额外上限及Permanent=true未对拍；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证；这些分支与已测效果共用模板，不能按SPLIT_STILL互斥拆分用量'),
    (NUGGET, 'FireOnObjectsNugget'): (TODO, '未实现：子武器派发条件与空间锚点尚未解释；失败诊断不作为已对拍依据'),
    (MODULE, 'Behaviors/GrapplingHookUpdate'): (TODO, '仅engine_grapple a最小消费者诊断；模块派发/拉拽/释放未解释，未实现，不作为已对拍证据'),
    (NUGGET, 'GrapplingHookNugget'): (TODO, 'engine_grapple a最小消费者诊断；GrapplingHookUpdate派发/拉拽/释放未解释，显式报告gap；tests/test_grapple_nugget.py守卫直接命中/继承/弹头及原版缓存，不登记已对拍'),
    (MODULE, 'Behaviors/LiftObjectUpdate'): (GUESSED, '部分：显式TimeIncrement/MaxTimeLifted的开火者举升表计时接口；tests/test_lift_nugget.py回放engine_lift a状态计数，逐帧计时来自模块证据、未上台逐帧量表；垂直运动/死亡/飞机/落地武器/清位仍gap，落地清位INFERRED，不登记整模块已对拍'),
    (NUGGET, 'ActivateLiftObjectNugget'): (GUESSED, '部分：按模块证据实现开火者举升表，trunc(TimeIncrement×15)逐发累加、续期封顶MaxTimeLifted、逐帧递减释放；Lifetime不参与，释放不清LIFTED；tests/test_lift_nugget.py按名回放engine_lift a旧读数一致，landing因落地清位未实现strict xfail；原版地面3/对空3共6消费者均未完整对拍，旧合成VEHICLE组不占原版用量；A169已量接地帧但28清位/40与60不清的门槛未解；落地清位规则INFERRED，垂直运动/死亡/飞机/弹体/复杂筛选仍gap，不登记整项已对拍；整项边界见work/re/c_liftclosure_report.md'),
    (NUGGET, 'AttachNugget'): (GUESSED, '部分：engine_attach a实测直接单发、父子状态、随父移动及目标状态/类型拒绝；仅零半径简单模块，原版复杂筛选/维修/吸血/解除/弹体未接通，不登记整项已对拍'),
    (NUGGET, 'SpecialPowerNugget:变装消费者'): (GUESSED, '2用量：间谍/迅雷直接命中DISGUISED位及INFANTRY/VEHICLE/恐怖机器人排除已测；engine_spndisguise/spnspyx/spnspyex/spntrans/spntrfilter a均1111/1110/1110/1111，tests/test_special_power_nugget.py按名回放；gap：身份/外观/索敌/换目标/取消，迅雷展开时序strict xfail，即时位应用INFERRED；engine_spnrelations a间谍/迅雷各Friend与Neutral四路s6-15全1111，独立命中且无脚本变装位；身份/时序缺口见work/re/c_spnclosure_report.md，不登记完整消费者'),
    (NUGGET, 'SpecialPowerNugget:轰炸消费者'): (GUESSED, '1用量，暂停：engine_spnbombnative a原版/删SPN/合成/合成删SPN为1010/1110/1110/1110；OCL活动消费者未实现，具名回放strict xfail；需要原版与合成宿主派发观测，work/re/c_spnbomb_report.md'),
    (NUGGET, 'SpecialPowerNugget:干扰消费者'): (GUESSED, '1用量，暂停：engine_spnscr a保留/删除SPN最终同80%，活动消费者未闭合；状态到期与攻击订单恢复已另有具名回放，筛选仅隔离接口；需要活动派发和状态观测，不登记完整消费者，work/re/c_spnclosure_report.md'),
    (NUGGET, 'SpecialPowerNugget:附着dummy消费者'): (TODO, '1用量，暂停：JapanScoutInfantryAttachWeaponWarhead引用OBJECT dummy模板及原版宿主；缺独立派发/附着读数，不能按Dummy名字推定无操作；需Attach模块观测，work/re/c_spnclosure_report.md'),
    (MODULE, 'Behaviors/OCLSpecialPower'): (BENCHED, '总控第四切片按已测边界收尾：tests/test_simocl.py具名回放engine_oclcurtain/engine_oclnone/engine_oclwrong a，铁幕宿主匹配模块才保护并记事件，删除/改绑模块无保护/事件；engine_oclempty a空声明无保护且事件1；engine_oclcopy a完整原版载荷改名仍保护100/100且事件1；engine_oclzero a仅外层Count=0无保护且事件1。只闭合铁幕派发和零数量不保护边界，未测生成数量/通用生成；其他非零数量/载荷/超武、位置/过滤、按钮/冷却仍gap，继承、等价空声明及格式等价INFERRED，不表示全模块全字段验证；见 work/re/e_ocl_e65.md'),
    (MODULE, 'Behaviors/ActivateModuleSpecialPower'): (TODO, '仅在SpecialPowerNugget处理器中识别并拒绝，未实现模块技能执行'),
    (NUGGET, 'TintObjectsNugget'): (NA, '纯表现：Color及Pre/Sustained/PostColorTime、Frequency/Amplitude仅控制染色动画；engine_tint pair实测2/90/2/90，独立DamageNugget解释全部伤害，test_simbench_c重放；不声称像素已验证'),
    (NUGGET, 'MetaImpactNugget'): (TODO, '剩余复杂写法：延迟、筛选、Arc、Invert等；普通延迟仅解析payload及隔离到期队列，engine_knock_delay碰撞输入174/173→到期204/192；Physics观察/落地相位未解，不晋升整项。ShockWaveSpeed/Cyclonic本轮原版用量为0也未建模。非默认Physics、坡地及V4曲线弹到达仍gap'),
    (NUGGET, 'ParalyzeNugget'): (GUESSED, '部分：engine_emp phase实测PASS16051/31066/61096、hit1；engine_empfire a实测PASS901090/901100/901080/901090，失能窗口按令不开火、到期后新令恢复；仅无筛选EMP，其他类型/筛选/装填相位未验证'),
    (NUGGET, 'StripMaxHealthPercentNugget'): (GUESSED, '部分：engine_strip exact实测PASS95/45/74，4%满血/半血与25%满血按最大血量扣减；筛选、护甲倍率、无标记伤害形式未验证，最大血量不变仍推断'),
    # Weapon round 1: scope limitations retained; explicit replay register above sets the bench state.
    (NUGGET, 'AttributeModifierNugget'): (GUESSED, '部分：engine_weaponfx attribute实测涂靶ARMOR150%；engine_spnret a实测单个PLAYER升级Required/Forbidden读取施法者玩家，普通/高科技ARMOR150/200%、晚段74/69%血，tests/test_special_power_nugget.py回放；数据1.1s且9s前到期，到期帧未测；OBJECT升级/owner/筛选/范围形式仍未验证'),
    (NUGGET, 'LineDamageNugget'): (GUESSED, '部分：engine_weaponfx line探针；实测PASS90/90/90/100验证动态线长及穿透，圆形边界GUESSED，筛选与静态线未模拟'),
    (MODULE, 'Body/ActiveBody'): (GUESSED, 'simunits.stats 读 MaxHealth（只有生命值；受伤状态、回血等另算）'),
    (MODULE, 'Body/ManagerBody'): (BENCHED, '已测范围：engine_managerbody a/b原版HB_Bridge_02，270/700长度整体代理脚本伤害200后均80%、致命量后1%且存活，tests/test_simmanagerbody.py按名重放；gap：有效HP取CenterPiece及内部1%下限映射仍INFERRED，内部最大血量/伤害转发/显示下限待核；HV_Bridge_01等其他模板/配置、桥段共享血量/损毁/维修未对拍；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母'),
    (MODULE, 'Behaviors/BridgeBuilder'): (BENCHED, '已测范围：engine_bridgebuilder:a已量HB_Bridge_02长度270/700，EndCap/EndCap2/CenterPiece/CenterPieceB/GateHouse数量1/1/1/0/2及1/1/2/2/2；engine_bridgebuilder_b:b已量原版HB桥首16+Bridge1a桥尾32混合构型，两长度HB数量不变、五类Bridge1物件均0；tests/test_simbridgebuilder.py按名核计数模型与读数编码，simunits仅有限数量模型；gap：HV_Bridge_01等其他桥型/配置/长度、世界物体生成/位置、通行、损毁、共享血量与维修未建模；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母'),
    (MODULE, 'AI/AIUpdate'): (GUESSED, 'Sim.fight / 移动（单位 AI 的状态机细项按引擎 B 的 AI 清单推进）'),
    (MODULE, 'AI/JetAIUpdate'): (BENCHED, '已测范围：engine_jet:a/b原版维和轰炸机静止正东起步，距离1200/600，首次入框97/47，框内1且血100%；simjet按逐帧位置实现首步2.7（机制INFERRED）、每帧+0.8至12；tests/test_simjet.py按名回放两种时钟均97/47，并核启动位置和入框112/62帧；未新增上台；gap：其他配置/机型、重复命令/转弯、MinSpeed、起飞高度/盘旋/降落、机场/跑道/停车位、返场补弹/耗尽伤害及攻击状态，配置与动作门禁保留；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母'),
    # the 26 the bench measured but the name rule called 未做 (checked 11-08 against sim.py / simunits.py)
    (MODULE, 'Behaviors/FireWeaponUpdate'): (GUESSED, '部分：simunits.ocl_round 把召出物的 FireWeaponNugget + '
                                                      'LifetimeUpdate 折成伤害，不模拟召出物本身'),
    (MODULE, 'Behaviors/StealthDetectorUpdate'): (TODO, f'{_NOT_IN_SIM}（没有反隐）'),
    (MODULE, 'Behaviors/GarrisonContain'): (GUESSED, 'simgarrison 同一套规则（不可争夺）；没单独上台对拍'),
    (MODULE, 'Behaviors/ReplaceSelfSpecialAbility'): (BENCHED, '三类用法都上台：基地车 / 帝国蛋到点展开（engine_unpack mcv / egg，'
                                                     '名字和血量比例跟过去）、三国建造场收起（engine_pack a/s/j，按下当帧就是基地车，'
                                                     '先站 2 秒 + 约 14 帧再开，14 帧是拟合 INFERRED）；gap：盟军矿车、苏联勘探车的展开没上台，'
                                                     '其余 8 种蛋按同一机制推'),
    (MODULE, 'Behaviors/FreefallUpdate'): (NA, '纯表现（总控 11-11 定）：配置只有 InitialVelocity / Acceleration / TerminalVelocity / '
                                         'ModelConditionsToSet=STUNNED_FLAILING，管空中死亡后尸体下落的画面；engine_freefall fall 已核'
                                         '人炮扔出的兵原版 / 改慢 / 改快三份读数一样（AIRBORNE_TARGET 1-125 帧、22 帧到点、降落伞约 96 帧），'
                                         '不归本模块。gap：被举起后落下（ActivateLiftObjectNugget / LiftObjectUpdate，C 已接通计时、落地仍 gap）'
                                         '可能用到下落速度，落地时刻会影响逻辑，未上台；同 id 覆盖是否生效未排除'),
    (MODULE, 'Behaviors/SpawnBehavior'): (BENCHED, '已测范围：engine_spawn:spawn开局3架及母体死亡/删除清随从；engine_spawn_refill:refill两架分别死亡10秒后补回（tests/test_simspawn.py显式预置贴车位置）；engine_spawn_power:power缺电及复电期间总数/厂旁均3；gap：自主维修飞行、子体直接删除、真正禁用/占领、缺电时死亡补充、展开时机及其他完整配置，生成位置和秒内相位INFERRED；按总控11-11三切片收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母'),
    (MODULE, 'Behaviors/ProductionUpdateInfo'): (NA, '纯界面状态：保存七个生产类别的侧栏子页签编号；读写限于侧栏编号维护、变形时保留编号和存档传递，没有游戏逻辑读者，模拟器不建模；9用量/9模板保留；读者闭包证据见 work/re/e_production_e56.md，非上台对拍'),
    (MODULE, 'Behaviors/SubStructureStorageBehavior'): (TODO, '6用量/6模板为三国MCV及海军继承型，模块无专用字段；有效配置没有SubStructureBuild，未找到可生成待存子结构的原版入口；gap：保存/恢复专属读数及合法触发待接口核实，未上台、不登记已对拍，也不据此排除运行时用途；普通展开及COPY_UPGRADES不能归因；见 work/re/e_substorage_e57.md'),
    (MODULE, 'Behaviors/WallBuilderBehavior'): (GUESSED, '部分：engine_wallinit:a有/无模块对照10/11/10，仅StartInSecondaryModel默认WALL_SEGMENT初始化；6/6权重保留，建墙/连接/段数上限/生死联动及自定义配置仍gap，未登记完整已对拍；见 work/re/e_wallbuilder_e58.md'),
    (MODULE, 'Behaviors/SlavedUpdate'): (TODO, f'{_NOT_IN_SIM}（没有随从跟随）'),
    (MODULE, 'Behaviors/BezierProjectile'): (TODO, f'{_NOT_IN_SIM}（开火按每秒伤害直接扣血，没有弹体）'),
    (MODULE, 'Behaviors/ProjectileUpdate'): (TODO, f'{_NOT_IN_SIM}（开火按每秒伤害直接扣血，没有弹体飞行时间）'),
    (MODULE, 'Behaviors/AttachUpdate'): (GUESSED, '部分：engine_attach a验证瞬移/跟随/父子状态；engine_attach_parent a验证简单模块脚本杀父后子活/清理链接，NO_COLLISIONS读数差异为严格xfail；原版模块死亡前无稳定链接，不推广死亡规则；子死/直接删除/维修/吸血/解除/自主扫描仍gap'),
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
    (MODULE, 'Behaviors/Physics'): (TODO, 'RA3 的 Physics 只有击飞曲线、反弹、落地后倒地/起身、重力倍数（没有 Generals 的 '
                                          'Mass/摩擦/推挤），会动的战役模板全是默认字段（仅 6 个改 GravityMultiplier）。'
                                          '已测：落地后锁 38 帧再走移动令（engine_knock_probe stand / standlate，'
                                          'tests/test_meta_impact.py::test_physics_a_knocked_man_keeps_still_38_frames_after_landing_then_walks_his_order）；'
                                          '人的落点站不住（落水）挪到最近能站的格、按新落点重画曲线（engine_knock_water man / far，'
                                          'tests/test_meta_impact.py::test_physics_p3_a_man_knocked_toward_water_lands_on_the_nearest_cell_he_can_stand_on）；'
                                          '车的落点按 20 取整再加 10、不能落（水）挪到最近的水上格、落点格离水 10 以内落地即死（斜坡本身不致死），'
                                          '落到低处的曲线（engine_knock_water tank / ramp / edge，'
                                          'tests/test_meta_impact.py::test_physics_p3_a_hammer_lands_on_the_plus_10_grid_and_drowns_within_10_of_the_water；'
                                          '门槛 10、搜索格网 INFERRED）；'
                                          '冲击量（弹头原值，不算距离衰减）小于物体的 ShockwaveResistance（车 90、步兵 0）就完全不击飞，等于照飞'
                                          '（engine_knock_water gate89 / gate90 / gate91，'
                                          'tests/test_meta_impact.py::test_physics_p3_a_shock_under_the_hammers_resistance_90_launches_nothing）；'
                                          '倒地时照样开火、空中下的攻击令保留（engine_knock_probe fire，'
                                          'tests/test_meta_impact.py::test_physics_p4_a_knocked_man_fires_his_order_while_lying_before_he_stands）；'
                                          '空中不开火：低飞 20 高、靶子在 2D 射程内十几帧也不打（engine_knock_water farfire，'
                                          'tests/test_meta_impact.py::test_physics_p4b_a_knocked_man_does_not_fire_in_the_air_with_the_target_in_reach）；'
                                          '空中下的攻击令、落地够不着时落地 + 50 帧才起步（移动令 + 38，不是转身；farfire / farwalk，'
                                          'tests/test_meta_impact.py::test_physics_p4b_an_attack_order_kept_through_the_knock_walks_at_landing_plus_50；'
                                          '多等的 12 帧是哪个等待 INFERRED，走进射程多深未建模）；'
                                          '落到高处（车被推上坡、落在高 56 的台面）的曲线：两个控制点都在落点高 + 1.3a'
                                          '（engine_knock_water climb，同上 test_physics_p3_a_hammer_lands_on_the_plus_10_grid…[climb]）；'
                                          '出图不死、默认不反弹（台上读过）；'
                                          '坠机：空中打死的飞机本体立刻没了，下落的是 OCL 生成的残骸，残骸走同一条击飞曲线、'
                                          '重力看残骸自己的 GravityMultiplier（活飞机的 30 不进坠机；默认 1 从 175 高 30 点、'
                                          '改 30 只 8 点；n = ⌈自由落体时间⌉ + 1，落点 = 起点 + 速度 × n 取最近的 20 格，'
                                          'engine_crash_fall fall，tests/test_meta_impact.py::'
                                          'test_physics_p5_a_shot_down_wreck_falls_the_knock_curve_under_its_own_gravity，'
                                          'simunits.meta_impact_fall）。坠机砸伤已接进 Sim（Sim.air_crash：残骸最后一点时'
                                          '死亡武器在落点炸，友军 50 %，只伤地面；悬停的飞机带 0.2/帧 朝向漂移；CHOOSE_ONE '
                                          '取会砸的那个，INFERRED），engine_crash_hit hit 台上悬停两架 38 帧、敌 72 % 友 86 %，'
                                          'test_physics_p5_a_hovering_apollo_s_crash_hurts_what_is_under_it_as_on_the_bench；'
                                          '飞行中那架多掉约 15 血原因没查（strict xfail），落点高度不同、冲击波没派发'),
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
            for allies, label, checks, example in (
                    (False, '通用三国', 'a/b/c/d', 'AlliedPowerPlant'),
                    (True, '三国ALLIES', 'a/e/f', 'SovietBaseDefenseGround')):
                share = contain_audit.engineer_capture_share(allies=allies, with_templates=True)
                v = dict(v, campaign=v['campaign'] - share['campaign'],
                         templates=v['templates'] - share['templates'])
                items.append(dict(part=MODULE, name='Behaviors/EngineerContain:' + label,
                                  uses=share['campaign'], all=share['templates'], state=GUESSED,
                                  template_ids=share['template_ids'],
                                  why=f'完整配置：engine_engineer {checks}；精确进入帧仍INFERRED', eg=example))
            v = dict(v, examples=['TH_TombBuilding02'])
        if (group, mtype) == ('Behaviors', 'InfiltratorContain'):
            import contain_audit
            share = contain_audit.infiltrator_energy_share(with_templates=True)
            v = dict(v, campaign=v['campaign'] - share['campaign'],
                     templates=v['templates'] - share['templates'])
            items.append(dict(part=MODULE, name='Behaviors/InfiltratorContain:ENERGY',
                              uses=share['campaign'], all=share['templates'], state=GUESSED,
                              template_ids=share['template_ids'],
                              why='三国普通电厂敌友对照：engine_infiltrator a/b/c/d', eg='JapanPowerPlant'))
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
    if ntype == 'SpecialPowerNugget':
        # Only the two exact retail upgrade forms have a closed consumer
        # boundary. Other native consumers keep their own unresolved weight.
        paint = {
            'SpecialPower_PaintTargetTrigger': 'ForbiddenUpgrade',
            'SpecialPower_PaintTargetTrigger_HighTechnology': 'RequiredUpgrade',
        }
        def paint_form(n):
            power = n.get('SpecialPowerTemplate')
            return (power in paint and set(n.attrib) <= {'id', 'SpecialPowerTemplate'}
                    and len(n) == 1 and not list(n[0]) and not n[0].attrib
                    and n[0].tag.rsplit('}', 1)[-1] == paint[power]
                    and (n[0].text or '').strip() == 'Upgrade_AlliedHighTechnology')
        if (len(forms) == 2 and all(paint_form(n) for n in forms)
                and {n.get('SpecialPowerTemplate') for n in forms} == set(paint)):
            return ':涂靶升级门槛'
        powers = {n.get('SpecialPowerTemplate') for n in forms}
        for allowed, suffix in [
            ({'SpecialPower_InfantryDisguise', 'SpecialPower_JapanLightTransportVehicleDisguise'}, ':变装消费者'),
            ({'SpecialPowerBombingRun'}, ':轰炸消费者'),
            ({'SpecialPower_WeaponScrambler'}, ':干扰消费者'),
            ({'SpecialPower_JapanScoutInfantryAttachWeaponDummy'}, ':附着dummy消费者'),
        ]:
            if powers <= allowed:
                return suffix
        return ''
    if ntype == 'MetaImpactNugget':
        allowed = {'id', 'ShockWaveAmount', 'ShockWaveRadius', 'ShockWaveZMult', 'ShockWaveTaperOff'}
        def measured_filter(n):
            children = list(n)
            return (set(n.attrib) <= allowed | {'ForbiddenTargetModelCondition'}
                    and {'ShockWaveAmount', 'ShockWaveRadius'} <= set(n.attrib)
                    and set(n.get('ForbiddenTargetModelCondition', '').split()) == {
                        'STUNNED', 'STUNNED_STANDING_UP', 'STUNNED_FLAILING'}
                    and len(children) == 1 and children[0].tag.rsplit('}', 1)[-1] == 'SpecialObjectFilter'
                    and not list(children[0])
                    and not (children[0].text or '').strip()
                    and children[0].attrib == dict(Rule='ANY', Relationship='ENEMIES',
                        Include='INFANTRY', StatusBitFlagsExclude='NO_COLLISIONS'))
        if all(measured_filter(n) for n in forms):
            return ':镰刀敌我筛选'
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
    'SpecialPowerNugget:涂靶升级门槛': '仅原版守护者普通/高科技两种升级门槛与空PaintTarget消费者边界；engine_spnret a保留/删除SPN晚段74/69/74/69%血，增伤来自伴随AttributeModifierNugget。非通用技能执行；原版涂靶开关/持续光束/重复开火未测，其他消费者另列gap',
    'MetaImpactNugget:普通无延迟显式Z': '仅普通弹头碰撞事件→默认Physics轨迹；engine_knock_probe land/late邻人5帧落(2380,3740)、目标99%/邻人100%。到达帧为台上输入，非完整V4曲线弹回放；直击方向/落点网格/选人仍INFERRED',
    'MetaImpactNugget:镰刀敌我筛选': '仅镰刀无延迟筛选写法的发射者敌我关系→默认Physics；engine_knock_relation a健康99/100/99/100，ENEMIES仅敌/ALLIES仅友，逐帧位置回放。碰撞帧/爆心由台上输入；倒地状态及NO_COLLISIONS/非步兵拒绝未单独上台，Physics状态映射INFERRED；不覆盖原版落地入口、延迟、Arc',
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
        if ntype in ('MetaImpactNugget', 'InformTargetNugget', 'SpecialPowerNugget'):
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


def probe_checks(text):
    """(missions, {check key: [function name]}) of a probe's source: its CHECKS = {mission: {key: function}} read from
    the syntax tree (a probe is not imported: it builds missions)."""
    missions, keys = set(), collections.defaultdict(list)
    for node in ast.parse(text).body:
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict)
                and any(getattr(g, 'id', None) in ('CHECKS', 'MISSION') for g in node.targets)):
            continue
        for mk, mv in zip(node.value.keys, node.value.values):
            if isinstance(mk, ast.Constant) and isinstance(mk.value, str):
                missions.add(mk.value)
            if any(getattr(g, 'id', None) == 'CHECKS' for g in node.targets) and isinstance(mv, ast.Dict):
                for k, v in zip(mv.keys, mv.values):
                    if isinstance(k, ast.Constant) and isinstance(k.value, str) and isinstance(v, ast.Name):
                        if v.id not in keys[k.value]:
                            keys[k.value].append(v.id)
    return missions, dict(keys)


def probe_parts(name, text):
    """[(source, text)] of one probe. A probe with one check is one source, 'checks/engine_X.py'. A probe with several
    (engine_aiskirm's thirty) is split: each check's own function (its docstring holds that check's readings) is
    'checks/engine_X.py:<key>', the rest (module docstring, shared helpers, constants) 'checks/engine_X.py'. A word only
    a check's own function names was read by that check: only a test that runs that check makes it 已对拍
    (tested_probes), not one that runs another check of the same probe."""
    src = f'checks/{name}.py'
    _, keys = probe_checks(text)
    if len(keys) < 2:
        return [(src, text)]
    fns = {node.name: node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)}
    lines, cut, out = text.splitlines(keepends=True), set(), []
    for key, names in keys.items():
        body = []
        for n in names:
            node = fns.get(n)
            if node is not None:
                first = min([node.lineno] + [d.lineno for d in node.decorator_list]) - 1
                body.append(''.join(lines[first:node.end_lineno]))
                cut.update(range(first, node.end_lineno))
        out.append((f'{src}:{key}', ''.join(body)))
    return [(src, ''.join(x for i, x in enumerate(lines) if i not in cut))] + out


# a line saying what it names was not measured (a prediction, a gap, a run not made) is no reading of it
NOT_MEASURED = re.compile(r'未实测|没(?:单独)?量|未量|not (?:yet )?(?:measured|run)|unmeasured|outside the observation'
                          r'|remain gaps?', re.I)


def measured(text):
    """`text` without the lines NOT_MEASURED marks."""
    return ''.join(x for x in text.splitlines(keepends=True) if not NOT_MEASURED.search(x))


def bench_sources():
    """[(source, text)] where bench measurements live: the engine probes (checks/engine_*.py, run with cnv_check on the
    bench, their readings in the docstrings; a probe of several checks split by check, probe_parts) and the lines of
    docs/engine/*.md marked measured (**测**). In both a line NOT_MEASURED marks is left out (engine_aiupgrade's
    'Retail tech entries have MinTime >=180s, outside the observation' made MinTime 已对拍)."""
    need(CHECKS, 'the bench checks')
    need(ENGINE_DOCS, 'the engine docs')
    out = []
    for f in sorted(os.listdir(CHECKS)):
        if f.startswith('engine_') and f.endswith('.py'):
            text = open(os.path.join(CHECKS, f), encoding='utf-8').read()
            out += [(s, measured(t)) for s, t in probe_parts(f[:-3], text)]
    for f in sorted(os.listdir(ENGINE_DOCS)):
        if f.endswith('.md') and f != os.path.basename(OUT):
            lines = [x for x in open(os.path.join(ENGINE_DOCS, f), encoding='utf-8')
                     if '测' in x.replace('未实测', '').replace('推断', '')]
            out.append((f'docs/engine/{f}', measured(''.join(lines))))
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
    (engine_mining's), and each cites the probe whose readings it asserts. A probe no test names is a reading only.
    For a probe of several checks (probe_parts) also 'checks/engine_X.py:<key>' for each check the naming test file
    runs (tested_checks); naming the probe alone runs none of its checks' own readings."""
    stems = {f[:-3] for f in os.listdir(checks) if f.startswith('engine_') and f.endswith('.py')}
    info = {}
    out = set()
    for f in sorted(os.listdir(tests)):
        if not f.endswith('.py'):
            continue
        text = open(os.path.join(tests, f), encoding='utf-8').read()
        named = {}
        for name in PROBE_NAME.findall(text):
            full = name
            while name not in stems and '_' in name[len('engine_'):]:
                name = name.rsplit('_', 1)[0]
            if name in stems:
                out.add(f'checks/{name}.py')
                named.setdefault(name, set()).add(full)
        for name, variants in named.items():
            if name not in info:
                info[name] = probe_checks(open(os.path.join(checks, f'{name}.py'), encoding='utf-8').read())
            missions, keys = info[name]
            if len(keys) >= 2:
                out |= {f'checks/{name}.py:{k}' for k in tested_checks(text, name, variants, missions, set(keys))}
    return out


_WORD_LIST = r'(?:\.py)?(?:\s*[:.]\s*|\s+)(\w+(?:\s*[/,]\s*\w+)*)'
_PARAMETRIZE = re.compile(r'parametrize\((.*?)\)\s*\n\s*(?:@|def )', re.S)


def tested_checks(text, probe, variants, missions, keys):
    """The checks of `probe` (keys) that the test file `text` runs: a key written after the probe's or one of its
    missions' name ('bench engine_aiskirm d / f', 'engine_engineer:c', 'checks/engine_aiskirm.py y'), quoted as the
    argument after it (_sim_run('engine_scripts7', 'idle'), simai.run('aiskirmlow', 'd')), a build variant
    'engine_seal_move', or -- when the check is a variable (_sim_resolve('engine_seal', check)) -- quoted in the
    file's pytest parametrize lists."""
    names = sorted({probe, *missions, *variants}, key=len, reverse=True)
    alt = '|'.join(re.escape(n) for n in names)
    found = set()
    for v in variants:
        if v != probe and v[len(probe) + 1:] in keys:
            found.add(v[len(probe) + 1:])
    for m in re.finditer(r'(?<![\w/])(?:checks/)?(?:' + alt + r')(?![\w])' + _WORD_LIST, text):
        found |= set(re.split(r'\s*[/,]\s*', m.group(1))) & keys
    quoted = r'[\'"](?:' + alt + r')[\'"]\s*,\s*'
    found |= set(re.findall(quoted + r'[\'"](\w+)[\'"]', text)) & keys
    if re.search(quoted + r'[A-Za-z_]\w*\s*[,)]', text):
        for block in _PARAMETRIZE.findall(text):
            found |= set(re.findall(r'[\'"](\w+)[\'"]', block)) & keys
    return found


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
            if k in NOTES and NOTES[k][0] == BENCHED:
                scope = NOTES[k][1]
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
    return mark_levels(items)


def level_marks(items):
    """{(part, name): {level}}: what our 9 levels use -- engine A's parts by inventory_levels.level_scope (a nugget
    split by field form attributed to its forms, as inventory-levels-a.md), the AI part by inventory_ai.level_scope
    (its '?' keys, script names aimed at the AI player, are in engine A's scope already)."""
    import inventory_ai
    import inventory_levels
    marks = collections.defaultdict(set)
    scope, _ = inventory_levels.expand_forms(items, inventory_levels.level_scope()[0])
    for key, lvs in scope.items():
        marks[key] |= set(lvs)
    for (part, name), lvs in inventory_ai.level_scope().items():
        if part == AI:
            marks[(part, name)] |= set(lvs)
    return marks


def mark_levels(items, marks=None):
    """Each item gets 'levels': the levels (a1 ... a9, in order) that use it, [] when none does."""
    import inventory_levels
    marks = level_marks(items) if marks is None else marks
    for it in items:
        it['levels'] = sorted(marks.get((it['part'], it['name']), ()), key=inventory_levels.LEVELS.index)
    return items


def levels_cell(levels):
    import inventory_levels
    return '全部' if list(levels) == inventory_levels.LEVELS else ' '.join(levels)


def order(items):
    return sorted(items, key=lambda i: (PARTS.index(i['part']), -i['uses'], -i.get('all', 0), i['name']))


MAIN = '按用量已对拍'
LEVEL_COLUMN = '9 关用到'
LEVEL_MAIN = '9 关用到的按用量已对拍'
LEVEL_COUNT = '9 关用到（已对拍 / 项）'
SUMMARY_COLUMNS = (MAIN, LEVEL_MAIN, LEVEL_COUNT, '项数', BENCHED, GUESSED, TODO, NA, '按用量已有（已对拍+推断）')


def summary(items):
    """[(part, {column: value})], the summary table's rows. The main number is MAIN: the share of the retail uses that
    are 已对拍 (推断 does not count; 不涉及 is left out of the total); LEVEL_MAIN the same over the items our 9 levels
    use (None when they use none of the part), LEVEL_COUNT how many of those are 已对拍 (不涉及 left out)."""
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
        ours = [i for i in rel if i.get('levels')]
        ow = sum(i['uses'] for i in ours)
        mine = 100 * sum(i['uses'] for i in ours if i['state'] == BENCHED) / ow if ow else None
        count = f"{sum(i['state'] == BENCHED for i in ours)} / {len(ours)}"
        rows.append((part, {MAIN: pct({BENCHED}), LEVEL_MAIN: mine, LEVEL_COUNT: count, '项数': len(xs),
                            BENCHED: c[BENCHED], GUESSED: c[GUESSED], TODO: c[TODO], NA: c[NA],
                            '按用量已有（已对拍+推断）': pct({BENCHED, GUESSED})}))
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
           '**主数字是"按用量已对拍"**：已对拍项的用量占全部用量的比例，推断不算，不涉及不进分母；目标每部分 90%。'
           '"9 关用到"：我们 9 关（`missions/a1.py`～`a9.py`）里用到这项的关（脚本、物体模块、武器效果按 '
           '`inventory_levels.py`，AI 按 `inventory_ai.py levels`；"全部" = 9 关都用）；"9 关用到的按用量已对拍"只算这些项'
           '（用户 11-11 定：先做完 9 关用到的）。', '',
           '| 部分 | ' + ' | '.join(SUMMARY_COLUMNS) + ' |', '|---' * (len(SUMMARY_COLUMNS) + 1) + '|']
    for part, row in summary(items):
        cells = ['—' if row[c] is None else f'**{row[c]:.0f}%**' if c in (MAIN, LEVEL_MAIN) else
                 f'{row[c]:.0f}%' if c.startswith('按用量') else str(row[c]) for c in SUMMARY_COLUMNS]
        out.append(f'| {part} | ' + ' | '.join(cells) + ' |')
    for part in PARTS:
        xs = by.get(part, [])
        if not xs:
            continue
        out += ['', f'## {part}', '', f'| 状态 | 名字 | 用量 | {LEVEL_COLUMN} | 说明 |', '|---|---|---|---|---|']
        for i in xs:
            n = f"{i['uses']}" + (f" ({i['all']})" if 'all' in i else '')
            why = i['why'] + (f"；例：{i['eg']}" if i.get('eg') else '')
            out.append(f"| {i['state']} | `{i['name']}` | {n} | {levels_cell(i.get('levels', []))} | {why} |")
    return '\n'.join(out) + '\n'


def gaps(items, k=20, ours=False):
    """The k most used items not 已对拍 (未做 and 推断: both are short of the main number), across the parts; with
    ours, only those our 9 levels use. (11-13 it listed 未做 only and hid the 推断 items that weigh the most.)"""
    return sorted((i for i in items if i['state'] in (TODO, GUESSED) and (i.get('levels') or not ours)),
                  key=lambda i: (-i['uses'], i['name']))[:k]


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
    for part, row in summary(items):
        if row[LEVEL_MAIN] is not None and row[LEVEL_MAIN] < 90:
            ours = [i for i in items if i['part'] == part and i['state'] != NA and i.get('levels')]
            short = 0.9 * sum(i['uses'] for i in ours) - sum(i['uses'] for i in ours if i['state'] == BENCHED)
            print(f'{part}: {row[LEVEL_MAIN]:.2f}%, {short:.0f} uses short of 90%')
    print('top gaps our 9 levels use (未做 and 推断):')
    for i in gaps(items, ours=True):
        print(f"  {i['part']} {i['name']} {i['uses']} {i['state']} ({levels_cell(i['levels'])})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
