r"""The retail feature inventory (ADR 0026): everything the retail game uses that the simulator should be able to do,
each item with a state, ordered by how much retail uses it. Generated from retail data -- never written by hand --
on demand into docs/engine/inventory.md, which is not committed (ADR 0030: PAGES are gitignored); tests/test_inventory.py
checks that the page renders and is self-consistent, not what a file on disk says.

Parts (the engine A line's share of ADR 0026; AI is the B line's):
  脚本动作 / 脚本条件  every action and condition name the retail campaign scripts use (script_catalog.json), with the
                    uses counted in the retail scripts (work/retailref, retailref.py's cache); an action told apart by
                    what it is told to do (a status bit, a special power, a command button: simcoverage.refined) is
                    one item per refinement
  物体模块          every module type the retail GameObjects use (retailmodules.module_census: includes and
                    inheritance resolved), counted by templates placed in the retail campaign maps, then by all
  武器效果          every Nugget type of the retail weapons (retailmodules.weapon_census)

States (STATES): 已对拍 -- implemented and matched against the bench: a reading in the readings data beside the probe
(checks/engine_X.readings.toml) the conformance runner holds without a mismatch mark (ADR 0035 5, conformance_probes:
the only way an item becomes 已对拍 from now on), or, frozen, a legacy test that names the probe (tested_probes; the
guard tests/guards/test_bench_tests.py lets no new test function name a probe) or a register entry (BENCHED_TESTS,
and the BENCHED entries of NOTES: the same guard lets them only shrink); 推断 -- the simulator has code for it, no
bench comparison yet; 未做 -- nothing; 不涉及 -- presentation / statistics only
(a rule below, by name or module group: never a list; a presentation action measured on the bench stays 已对拍).
How "has code" is told:
  script names    simcoverage.name_state: the engine model's core, a Sim.act / Sim.cond branch (probed with a retail
                  use's own arguments), sim.SHOWN; sim.IGNORED is 未做 (dropped on purpose, may hide play)
  modules, nuggets  the type's name is a string constant in the simulator's files (simcoverage.sim_code / sim_files)
                  -- a first cut: a module read under another name shows as 未做 until NOTES says otherwise

  python -I -X utf8 experimental/cnv/inventory.py            generate docs/engine/inventory.md, print the summary

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
# the generated pages (this one, inventory_levels.OUT, inventory_ai.LEVELS_OUT): gitignored, generated on demand
# (ADR 0030), and never a bench source -- read back, their item notes made the next run depend on whether and in
# which order the pages had been generated in that checkout
PAGES = ('inventory.md', 'inventory-levels.md', 'inventory-levels-a.md')

BENCHED, GUESSED, TODO, NA = '已对拍', '推断', '未做', '不涉及'
STATES = (BENCHED, GUESSED, TODO, NA)
ACTION, CONDITION, MODULE, NUGGET, AI = '脚本动作', '脚本条件', '物体模块', '武器效果', 'AI'
PARTS = (ACTION, CONDITION, MODULE, NUGGET, AI)     # AI: engine B's part, its own rules in inventory_ai.py

# (part, name) -> 'tests/<file>.py::<test>': the bench comparison that backs the item (the guard checks the test exists).
# Legacy (ADR 0035 5): only shrinks (tests/guards/test_bench_tests.py); a new one is a reading in the readings data.
BENCHED_TESTS = {
    (ACTION, 'TEAM_SET_HEALTH'):
        'tests/test_teamhp_bench_c.py::test_teamhp_current_mixed_members_and_controls_match_bench',
    (ACTION, 'NAMED_FACE_WAYPOINT'):
        'tests/test_facewp_bench_c.py::test_facewp_named_heading_and_untouched_control_match_bench',
    (ACTION, 'EXIT_SPECIFIC_BUILDING'):
        'tests/test_exitbld_bench_c.py::test_exitbld_named_host_and_mixed_crews_match_bench',
    (ACTION, 'PLAYER_DISABLE_BASE_CONSTRUCTION'):
        'tests/test_basegate_bench_a.py::test_aibgate_disabled_ai_spends_nothing_and_builds_nothing_until_enabled',
    (ACTION, 'PLAYER_ENABLE_BASE_CONSTRUCTION'):
        'tests/test_basegate_bench_a.py::test_aibgate_enable_starts_the_ai_base',
    (ACTION, 'SKIRMISH_AI_START'):
        'tests/test_aistart_bench_a.py::test_skirmish_ai_start_opens_an_ai_whose_yard_was_handed',
    (ACTION, 'PLAYER_TOGGLE_SKIRMISH_AI'):
        'tests/test_aistart_bench_a.py::test_toggle_skirmish_ai_off_freezes_the_ai_and_on_resumes_it',
    (ACTION, 'SET_PLAYER_KILLS_OF_TYPE_TO_COUNTER'):
        'tests/test_killcount_bench_c.py::test_killcount_native_type_and_player_match_bench',
    (ACTION, 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanMCV'):
        'tests/test_jpndeploy_bench_c.py::test_jpndeploy_waypoint_and_untouched_control_match_bench',
    (ACTION, 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackSovietMCV'):
        'tests/test_sovdeploy_bench_c.py::test_sovdeploy_waypoint_and_untouched_control_match_bench',
    (ACTION, 'TEAM_GARRISON_NEAREST_BUILDING'):
        'tests/test_teamgarr_bench_c.py::test_teamgarr_nearest_and_team_scope_match_bench',
    (ACTION, 'PLAYER_SELL_EVERYTHING'):
        'tests/test_sellall_bench_c.py::test_sellall_owner_refund_and_repeat_match_bench',
    (ACTION, 'TEAM_EXIT_ALL_BUILDINGS'):
        'tests/test_teamexit_bench_c.py::test_teamexit_mixed_building_and_transport_match_bench',
    (ACTION, 'PLAYER_KILL'):
        'tests/test_playerkill_bench_c.py::test_playerkill_owned_units_and_buildings_match_bench',
    (MODULE, 'Behaviors/ParkingPlaceBehavior'):
        'tests/test_parking_bench_e.py::test_parking_named_object_model_observations',
    (ACTION, 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanEgg'):
        'tests/test_eggcmd_bench_c.py::test_eggcmd_naval_legacy_and_concrete_buttons_match_display_counters',
    (ACTION, 'TEAM_UPGRADE'):
        'tests/test_teamup_bench_c.py::test_teamup_real_query_and_consumer_apply_only_to_current_team',
    (MODULE, 'Behaviors/RecallUnitsSpecialPower'):
        'tests/test_recall_bench_e.py::test_recall_named_object_model_bench',
    (ACTION, 'UNIT_STOP_SEQUENTIAL_SCRIPT'):
        'tests/test_seqstop_bench_c.py::test_seqstop_clears_pending_scripts_keeps_move_and_accepts_fresh_script',
    (ACTION, 'UNIT_SET_MODELCONDITION_FOR_DURATION'):
        'tests/test_modeldur_bench_c.py::test_modeldur_real_bits_expire_after_measured_frames',
    (ACTION, 'PLAYER_ENABLE_UNIT_CONSTRUCTION'):
        'tests/test_unitban_bench_c.py::test_unitban_enable_resumes_partly_paid_engineer',
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
    (MODULE, 'Behaviors/InfiltratorContain:STEAL_MONEY'):
        'tests/test_siminfiltrator.py::test_spy_refinery_transfer_amount_as_on_the_bench',
    (MODULE, 'Behaviors/InfiltratorContain:PARALYZE'):
        'tests/test_siminfiltrator_paralyze.py::test_paralyze_complete_configuration_as_on_the_bench',
    (MODULE, 'Behaviors/InfiltratorContain:VISION_PORT'):
        'tests/test_siminfiltrator_port.py::test_port_entry_and_blocked_repeat_as_on_the_bench',
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
    (CONDITION, 'HAS_FINISHED_AUDIO'):
        'tests/test_simbench.py::test_audio_a_dubbed_line_is_done_its_length_after_it_is_heard',
    (ACTION, 'ALLOW_DISALLOW_ONE_BUILDING'): 'tests/test_simbench.py::test_a_ban_holds_the_queue_and_does_not_cancel',
    # protocol points (simtech.py, checks/engine_protocol.py, bench 11-08)
    # engine line A round 208: retail-campaign conditions batch 1 (checks/engine_conds.py team / fight); the
    # TEAM_INSIDE_AREA k other than 0 is benched only as "no Guardian passes 1 / 3 / 7" (air / ships INFERRED)
    # engine line A round 210: batch 2 (checks/engine_conds.py sight): sight / discovery, the hot spot switch
    # engine line A round 211: retail-campaign actions batch 1 (checks/engine_acts.py flow; NAMED_SET_DISABLED benched
    # for EMP only, the other types INFERRED the same hold)
    **{(ACTION, n): 'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator' for n in (
        'UNIT_CHANGE_OBJECT_STATUS:SHROUD_REVEAL_TO_ALL', 'UNIT_CHANGE_OBJECT_STATUS:SKIRMISH_AI_DO_NOT_ATTACK',
        'TEAM_ALLOW_AI_AUTOACQUIRE', 'NAMED_SET_DISABLED', 'NAMED_FORCE_ATTACK_NAMED', 'TEAM_SET_STANCE')},
    # round 212: batch 2 (checks/engine_acts2.py seq / more; the ground fire's own damage not benched, none simulated)
    # round 254: checks/engine_reinfat.py go (on a house, at a moved tank's place now, none at a dead one)
    # round 254: checks/engine_mining.py mineturn0 cap / capz (harvest income held; scripts' money not: acts_tel)
    # round 264: checks/engine_aiupgrade.py aicupgon:ban (0 holders until the allow; bench rebuys 7 s after the model)
    # round 213: batch 3 (checks/engine_acts3.py tel)
    # round 214: batch 4 (checks/engine_acts4.py acts: spellbook powers, the context attack, buildability)
    **{(ACTION, n): 'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator' for n in (
        'PLAYER_GRANT_SPECIAL_POWER', 'PLAYER_SET_SPECIAL_POWER_COUNTDOWN', 'UNIT_CONTEXT_SENSITIVE_ATTACK',
        'UNIT_CHANGE_OBJECT_STATUS:SKIRMISH_AI_DO_NOT_TAKE', 'TECHTREE_MODIFY_BUILDABILITY_OBJECT')},
    (CONDITION, 'SKIRMISH_SPECIAL_POWER_READY'): 'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    # round 215: batch 5 (checks/engine_acts5.py acts; PLAYER_TRANSFER_OWNERSHIP_PLAYER changed nothing on the bench:
    # not simulated, stays 未做)
    **{(ACTION, n): 'tests/test_simbench.py::test_acts_v_as_the_bench' for n in (
        'UNIT_SET_MODELCONDITION', 'PLAYER_ALLOW_AI_AUTOACQUIRE', 'TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE',
        'TEAM_GUARD_AREA_FROM_POSITION')},
    # round 216: TEAM_HUNT / NAMED_HUNT (checks/engine_acts6.py hunt: an aiTactical-255 owner's crew attack-moves to
    # the nearest enemy; the 240 one's, and NAMED_HUNT on an AI not woken: nothing)
    # round 218 (checks/engine_acts8.py hunt): the gate is aiTactical, the target the nearest hostile object (units
    # too), re-picked after each one dies; NAMED_HUNT moves a woken AI's unit neither
    (ACTION, 'TEAM_HUNT'): 'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    (ACTION, 'NAMED_HUNT'): 'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    # round 219 (checks/engine_acts9.py all): on -- off every team; off -- back onto the map default team, with a
    # hidden member (the AI wake UNIT_AI_TRANSFER_ALL adds is not in it: program, not benched)
    # round 221 (checks/engine_acts10.py all): ability buttons in one run -- the bomber's untargeted eject, the
    # Twinblade's evacuate, the spider hole, the two transforms (with their locomotors), the team's button at a spot
    **{(ACTION, n): 'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator' for n in (
        'NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateEjectPassengersSpecialPowerUntargeted',
        'NAMED_USE_COMMANDBUTTON_ABILITY:Command_JAAVT1_Transform',
        'NAMED_USE_COMMANDBUTTON_ABILITY:Command_SovietAntiGroundAircraftEvacuate',
        'NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleSpiderHole',
        'NAMED_USE_COMMANDBUTTON_ABILITY:Command_JAIV_Transform',
        'TEAM_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT')},
    (ACTION, 'NAMED_USE_COMMANDBUTTON_ABILITY:Command_AlliedAntiInfantryVehicleEvacuate'):
        'tests/test_ifvevac_bench_e.py::test_ifvevac_named_measured_snapshots',
    # round 223 (checks/engine_acts11.py all): EVACUATE on a ground transport / a civilian block (out at once), the
    # Apocalypse's harpoon, both mirage fields, the Kirov's afterburners (its LoseHealthUpdate while on)
    **{(ACTION, f'NAMED_USE_COMMANDBUTTON_ABILITY:{n}'): 'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator'
       for n in ('Command_DisguisedEvacuate', 'Command_CivilianStructureEvacuate', 'Command_ToggleHarpoonSpecialPower',
                 'Command_ToggleMirageField', 'Command_ToggleAfterburners')},
    # (engine_acts11.py t): the Japanese tower's toggle takes a press only with power; the Sickle's button on it: none
    **{(ACTION, f'NAMED_USE_COMMANDBUTTON_ABILITY:{n}'): 'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator'
       for n in ('Command_JapanBaseDefenseToggleBinaryWeapon', 'Command_ToggleBinaryWeapon')},
    # round 224 (checks/engine_acts12.py all): the shinobi's smoke bomb and the Tsunami's energized armor (a self
    # AttributeModifier for its Duration), the bear's roar (the bark's EMP), the Sickle's leap to a spot
    **{(ACTION, n): 'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator' for n in (
        'NAMED_USE_COMMANDBUTTON_ABILITY:Command_SmokeBombSpecialPower',
        'NAMED_USE_COMMANDBUTTON_ABILITY:Command_ToggleEnergizedArmorSpecialPower',
        'NAMED_USE_COMMANDBUTTON_ABILITY:Command_ActivateRoarSpecialPower',
        'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateLeapSpecialPower')},
    # round 226 (checks/engine_acts13.py all): the roar _ON_NAMED (the bear walks up to the target, then roars)
    **{(ACTION, n): 'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator' for n in (
        'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED:Command_ActivateRoarSpecialPower',)},
    # round 252 (checks/engine_dam.py all): the dolphin's jump over a dry dam its swimming twin cannot pass (round
    # 249 had it in NOTES: engine_acts_wet's readout did not tell the jump from swimming)
    (ACTION, 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_ActivateJumpSpecialPower'):
        'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    # round 222 (checks/engine_share.py all): mining income split among sharing Friends (the earner keeps the rest);
    # NAMED_SELECTED after SELECT_OBJECT (TYPE_SELECTED in NOTES: never true there)
    # round 237 (checks/engine_eyes.py all): ENEMY_SIGHTED's player = the sighted object's owner, Friend takes the
    # viewer itself; CAMERA_ENTERED_AREA latches (the way there counts); TYPE_SELECTED never, the player's own click
    # and box selection too
    # round 238 (checks/engine_sighted.py all): TYPE_SIGHTED = ENEMY_SIGHTED's query with a type (the viewer itself
    # counts, a script's object list never); NAMED_BUILDING_IS_EMPTY a living garrison with nobody in; BUILT_BY_PLAYER
    # the player owns one, placed ones too (a killed one ~7 s while it lies: not modelled)
    # round 240 (checks/engine_razed.py all): PLAYER_DESTROYED_N_BUILDINGS_PLAYER false always (Generals' stub, n 0
    # too); SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED counts the player's men inside garrisons, not the buildings
    # round 242 (checks/engine_cast.py all): a cast waits until the first matching reader takes it; IN_AREA by the
    # cast's point; TEAM_CAN_PATH_TO_WAYPOINT every member to the waypoint itself (no snap)
    # round 245 (checks/engine_enter.py all): TEAM_OUTSIDE_AREA_ENTIRELY = not inside (an absent team outside);
    # TEAM_ENTERED_AREA_PARTIALLY one frame a member comes in (a start inside also on leaving); GARRISONNED by type
    # and owner; COMPLETELY_BUILT the player's own, a script's unpacking one at once
    # round 244 (checks/engine_kind.py all / by): PLAYER_HAS_COMPARISON_UNIT_KIND counts every player's objects;
    # PLAYER_LOST_OBJECT_TYPE one stored count per (player, type string), the first reader takes a drop;
    # NAMED_DESTROYED_BY_OBJECTTYPE false always (four kills, either case)
    # round 217: PLAYER_TRANSFER_OWNERSHIP_PLAYER (checks/engine_acts7.py own: the giver's units on no team and its
    # money go to the receiver; ones on a team stay)
    # engine line C round 1: modules whose retail data the simulator already follows and a bench-reading test cites
    (MODULE, 'Behaviors/ProductionUpdate'):
        'tests/test_simbench.py::test_production_pays_as_it_builds_and_comes_out_after_the_door',   # engine_production a-g
    (MODULE, 'Behaviors/StructureUnpackUpdate'): 'tests/test_simbench.py::test_power_back_after_the_plant_unpacks',
    (MODULE, 'Behaviors/SpecialPower'): 'tests/test_simbench.py::test_super_a_scripts_cast_starts_the_retail_reload',
    (MODULE, 'AI/AIUpdate'): 'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    # engine line C round 3: the crush / slow-death family (checks/engine_crush.py, docs/engine/crush.md, bench 11-06)
    # engine line C round 7: the superweapon benches (engine_super) read health % of 1000-health defenses and the
    # Iron Curtain's expiry frame -- MaxHealth through the damage, the modifier pool through the 23 s it holds
    (MODULE, 'Body/ActiveBody'): 'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    (MODULE, 'Behaviors/AttributeModifierPoolUpdate'):
        'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    (MODULE, 'Behaviors/SecondaryDamageTracker'):
        'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    (MODULE, 'Behaviors/SquishCollide'):
        'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    (MODULE, 'Behaviors/CrushDie'):
        'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    # engine A rounds 162-173: knock-back curve, landing, hold, gates, fire, the crash's fall (checks/engine_knock_probe,
    # engine_knock_water, engine_crash_fall; the whole list in NOTES' Physics line)
    (MODULE, 'Behaviors/Physics'):
        'tests/test_meta_impact.py::test_physics_p5_a_shot_down_wreck_falls_the_knock_curve_under_its_own_gravity',
    # engine line C round 8: running off the map (Sim.flee_start / flee_due, checks/engine_runoffmap.py, bench 11-06)
    # engine line C round 9: the mirage aura (Sim.cloaked, simunits.invis_broadcast, checks/engine_stealth.py, bench 11-05)
    (MODULE, 'Behaviors/InvisibilityBehavior'):
        'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    (MODULE, 'Behaviors/StealthDetectorUpdate'):
        'tests/test_detector_bench_e.py::test_detector_named_object_model_observations',
    # engine line C round 11: weapon choice by ObjectStatus (simunits.weapon_sets, checks/engine_weaponset.py,
    # engine_statusbits.py, bench 11-09)
    # engine line D: the damage line (simsweep, checks/engine_sweep.py engine_sweepoff a / b / c, bench 11-10)
    (MODULE, 'Behaviors/LinearDamageUpdate'):
        'tests/test_simsweep.py::test_sweep_the_line_walks_out_and_a_stop_does_not_cut_it_at_the_bench_frames',
    (NUGGET, 'ActivateLinearDamageNugget'):
        'tests/test_simsweep.py::test_sweep_a_killed_shooters_line_stops_with_it_and_the_second_ones_rows_are_hit',
    # immortal a / b / c, bench 11-09 (checks/engine_immortal.py): damage floor 1 %, script kill clamped, delete removes
    (MODULE, 'Body/ImmortalBody'):
        'tests/test_simbench_c.py::test_immortal_damage_stops_at_one_hp_kill_is_damage_and_delete_removes',
    # engine_propbody a / b / c, bench 11-10: no health, a kill leaves the street segment, topples the tree / lantern
    # engine_spawn_refill, bench 11-05: a scripted kill sets off the exploding mig's death weapon, the Guardian beside it dies
    (MODULE, 'Behaviors/FireWeaponWhenDead'):
        'tests/test_simbench_c.py::test_fire_weapon_when_dead_a_scripted_kill_blows_the_mig_and_the_guardian_beside_it',
    # topple a / b, bench 11-09: neutral props, delayed removal without DYING; all five readings within one frame
    # topple c, bench 11-10: lantern copies with / without EnableDynamicsCollide crushed and gone at the same frames
    (MODULE, 'Behaviors/EnableDynamicsCollide'):
        'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    # engine_dynamics a / b, bench 11-10: Hammers with / without BaseVehicle's DynamicsUpdate crush, go round and
    # arrive at the same frames (the Uprising fling props' share is split off: SPLIT_ORPHAN)
    (MODULE, 'Behaviors/DynamicsUpdate'):
        'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    # all four stances the retail scripts set: engine_stance a-f (HOLD_FIRE, bench 11-06) and engine_acquire hold / agg
    # (HOLD_POSITION goes after nothing, AGGRESSIVE never walks back; bench 11-10) -- tests/test_simbench_c.py test_stance_*
    (MODULE, 'Behaviors/StancesBehavior'):
        'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    # engine_garrison in / hp, bench 11-05 (simgarrison): script entry skips room and relation, owner follows the
    # first passenger, out at 13 % in the damage's frame, the contester bounces one, kill / hit eject them alive
    # engine_transport load, bench 11-10 round 152 (simgarrison's transports): the script's entry skips room and
    # relation, the men ride along, a killed transport kills them; the man cannon throws one every TimePerPassenger
    # engine_unpack mcv / egg (bench 11-10, round 138) and engine_pack a / s / j (bench 11-11, round 159): an MCV or
    # an egg drives to its point and turns into the replacement, a yard packs into its MCV at once and the MCV stands
    # ~44 frames -- tests/test_simbench.py test_*deploys_at_a_far_waypoint*, test_a_yard_packs_*
    # engine_production a / e (out at UnitCreatePoint, the door 10 frames), h / i and engine_rally tank (bench 11-11,
    # round 159): the unit stops 40 beyond NaturalRallyPoint on the centre -> rally line (sim.RALLY_PUSH, fitted);
    # gap: ExitDelaySeconds (0.07 s between two units), h's barracks stop 1-2 units off (strict xfail)
    (MODULE, 'Behaviors/QueueProductionExitUpdate'):
        'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    # engine line A round 160: engine_wfire all (bench 11-11): Yuriko's blast (radius damage after the nugget's
    # delay), Natasha's pilot snipe (walks till the target's edge is in StartAbilityRange, UnpackTime, the vehicle
    # neutral), the dog's bark (EMP on enemy infantry in the radius); the caster stands Pack / Freeze. Gaps: the
    # blast's MetaImpactNugget push, the ships' / Cryocopter's / superweapons' (WeaponSlot, FaceTarget), the sickle's
    # leap (BezierProjectile), the player's click reload
    # engine line A round 156: engine_toggle a-f, bench 11-11 (Sim.toggle_press): six of our 9 levels' toggles -- a
    # press moves to the next ToggleState (its ObjectStatus / AttributeModifier), the first state's bits from the
    # start, UnpackTime delays, PackTime does not, a DisabledType state takes no press (INFERRED cause). Not modelled:
    # ModelConditions, ArmorSet / LocomotorSet (the VX's / Tengu's jet form), TriggerAttributeModifier
    (MODULE, 'Behaviors/ToggleStatusSpecialAbilityUpdate'):
        'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    # round 223: the same bench's a / f are the retail presses' own units (s09's Peacekeepers, a08's Tesla troopers)
    **{(ACTION, f'NAMED_USE_COMMANDBUTTON_ABILITY:{n}'):
       'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator'
       for n in ('Command_ToggleRiotShieldSpecialPower', 'Command_ToggleShortCircuit')},
    # engine line C round 5: selling (checks/engine_sell.py, docs/engine/sell.md, bench 11-06)
    (MODULE, 'Behaviors/BuildingBehavior'):
        'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    (MODULE, 'Behaviors/StructureSellUpdate'):
        'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
    (ACTION, 'SELL_OBJECT'):
        'tests/conformance/test_readings.py::test_the_bench_readings_hold_on_the_simulator',
}

# (part, name) -> (state, why): where the name rule above is wrong (a module read under another name ...)
_NOT_IN_SIM = '已核（11-08）：模拟器没有这个效果'
NOTES = {
    (ACTION, 'NAMED_ATTACK_AREA'): (TODO, 'C engine_attackarea:a/b原版无畏舰对北/南电厂区域两局：禁自动索敌，b揭图并交换区域；区域段实际HP均100/100、对照血量与原位码3100，18秒点名阳性靶HP100→75→50→25。tests/test_attackarea_bench_c.py按名回放阴性窗口，两完整回放strict xfail；无命中不能证明区域命令无操作，尚缺区域候选/接受拒绝/实际弹着点，禁自动索敌与建筑目标类别仍未区分，单纯揭图不足以解释。原版a02四舰同区域；两局预算耗完，不实现猜测规则、不晋升；见work/re/c_attackarea_report.md'),
    (ACTION, 'TEAM_SET_HEALTH'): (BENCHED, 'C engine_teamhp:a/b显式目标队守护者/征召兵血量100→25→75及100→75→25，同玩家异队/另一玩家守护者均保持100；四计数器为两成员实际血量百分比、异队血量组合码100100和逻辑帧。tests/test_teamhp_bench_c.py按名字逐实读帧回放；仅当前存活显式队伍成员的百分比设置切片，未来/死亡/缺名成员、AI实例、边界数值和精确派发相位仍gap，其他模板推广INFERRED；见work/re/c_teamhp_report.md'),
    (ACTION, 'NAMED_FACE_WAYPOINT'): (BENCHED, 'C engine_facewp:a及engine_facewpai:b两局；a仅人类玩家存活位7，无team/tstate朝向，b换AI观察宿主，原生hd甲0→180、乙0→117、未操作0，分别朝西/西北路点。tests/test_facewp_bench_c.py按名回放24组原始稳定朝向（全圈1度容差对应hd整数舍入），并断言存活位7；没有用位置不变替代朝向。转身复用既有移动器速率，精确命令/起转相位、移动中打断、缺名/死亡目标和其他模板仍gap或INFERRED；仅存活静止守护者的具名路点朝向切片，见work/re/c_facewp_report.md'),
    (ACTION, 'EXIT_SPECIFIC_BUILDING'): (BENCHED, 'C engine_exitbld:a/b两座公寓各装同玩家两队征召兵，交换具名目标西/东；指定楼两队均退出、另一楼仍驻，重复调用无误伤。进驻位15→12/3、区域码始终22、五兵两楼存活位127；tests/test_exitbld_bench_c.py逐实读逻辑帧按名回放四计数器。区域人数包含楼内人员，原仅室外预测2/20保留strict xfail，不改原门槛；仅存活公寓具名退出切片，出门位置沿现有INFERRED近似，精确时序、其他容器/模板、缺名/死亡目标、取消进门仍gap；见work/re/c_exitbld_report.md'),
    (ACTION, 'SET_PLAYER_KILLS_OF_TYPE_TO_COUNTER'): (BENCHED, 'C engine_killcount:a/b原生守护者击杀两征召兵/一守护者，交换Player_1与Soviet_5为击杀者；DISPLAY_COUNTER主步兵/主坦克/另步兵开局0/0/0、末2/1/0，独立脚本杀死未受伤征召兵后不增计数，存活码末240。每帧先写77再查询，证明覆盖；tests/test_killcount_bench_c.py按名回放四读数。原s22存活码窗口差异保留strict xfail，不改门槛。仅具名玩家/单模板/原生直接武器致死和无归属脚本死阴性；列表并集INFERRED，This Player/All Players、换主、友军/间接伤害、争夺最后击和精确帧仍gap，见work/re/c_killcount_report.md'),
    (ACTION, 'DISABLE_JOYPAD_COMMANDBAR_BUTTON'): (TODO, 'C engine_joypad:a一局17组读数f40..182，原版buttonopenplayertechstore/buttonaiassaultdirective未操作、禁用、分步恢复的脚本阶段0/1/2/3均出现，未操作电厂始终1，末3/1/182。tests/test_joypad_bench_c.py仅锚定具名原始读数，不冒充完整模型回放或原生输入接受。cnv_result仅脚本阶段/存活/逻辑帧，index仅id/second/note/view，无Joypad元素enabled、输入accepted/rejected字段；台子仅键鼠注入，XInput四槽未连接。PC路径无消费者仅INFERRED，不用鼠标或余额替代阳性，不登记纯表现。一局后缺真实入口/观测而暂停，不耗相同第二局；见work/re/c_joypad_report.md'),
    (ACTION, 'DISABLE_MOUSE_HUD_FIXED_ELEMENT'): (TODO, 'C engine_mousehud:a/b两局SellButton禁用/开场禁用后恢复对照：末f356/f414均存活位5、资金2400；脚本出售位2消失、原生点击位1和未操作位4保留。B原生出售阳性预测4/2800未成立，tests/test_mousehud_bench_c.py保留一strict xfail；具名全三计数器负基线回放不能证明UI门。存档画面A按钮灰/B按钮亮且目标被选中；每次bench_click间Esc可能取消卖出模式（INFERRED）。cnv_result只有点击坐标及三计数器，没有SellButton enabled、卖出模式接受或拒绝字段；其他固定元素未量，不据余额或负基线登记纯表现。两局耗完，保持未做；见work/re/c_mousehud_report.md'),
    (ACTION, 'SKIRMISH_AI_CONSIDER_ALL_ENEMIES_WHEN_BUILDING'): (TODO, 'C aiallbuildon/off:a两局原生候选/订单对照：共同窗口前6次成功订单同帧同种（两警犬后四标枪），非空候选31/16条、订单307/156条。捕获末逻辑帧598/459，均未到70秒转友闸门；不能比较捕获秒数的存量差。tests/test_allbuild_bench_c.py只锚定具名原生读数，不声称模型等价。bpick/border缺同帧敌方玩家集合、动作开关及参与评分的兵力/资格输入，无法区分默认全敌或消费者未触发；倾向先补观测（INFERRED）。两局耗完，保持未做；见work/re/c_allbuild_report.md'),
    (ACTION, 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanMCV'): (BENCHED, 'C engine_jpndeploy:a一局：两辆普通日本MCV到东400路径点展开，未下令第三车留家；f256..501目标区建造场/名称存活/原处MCV位码3/7/4。tests/test_jpndeploy_bench_c.py按名回放动作前及事前预测f300之后稳定窗口实读逻辑帧四计数器；现有order_unpack匹配，无模型或阈值修改。仅普通活宿主空地切片；精确到达/展开时序、地形阻挡、伤害继承、重复/死亡/缺失宿主仍gap，其他宿主推广INFERRED；见work/re/c_jpndeploy_report.md'),
    (ACTION, 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackSovietMCV'): (BENCHED, 'C engine_sovdeploy:a一局：两辆普通苏联MCV到东400路径点展开，未下令第三车留家；f220..468目标区建造场/名称存活/原处MCV位码3/7/4。tests/test_sovdeploy_bench_c.py按名回放34个动作前及稳定窗口实读逻辑帧四计数器；现有order_unpack即可匹配，未调模型或阈值。仅普通活宿主空地切片；精确到达/展开时序、地形阻挡、伤害继承、重复/死亡/缺失宿主仍gap，其他宿主推广INFERRED；见work/re/c_sovdeploy_report.md'),
    (ACTION, 'TEAM_GARRISON_NEAREST_BUILDING'): (BENCHED, 'C engine_teamgarr:a/b两栋空公寓最近选择：建筑摆放顺序不变，仅步兵东移；本队两名征召兵进最近楼，同玩家异队留外，空队伍/重复调用无误伤。最终进驻位/楼归属/存活位分别3/1/31与3/2/31；tests/test_teamgarr_bench_c.py按名回放实读逻辑帧的动作前及稳定窗口。仅显式普通步兵与空楼选择切片；逐成员距离及其他模板推广INFERRED，队伍中心/等距/搜索范围、容量/敌属/损坏楼/AI实例和入门时序仍gap；见work/re/c_teamgarr_report.md'),
    (ACTION, 'PLAYER_SELL_EVERYTHING'): (BENCHED, 'C engine_sellall:a/b显式玩家交换对照：所属普通盟军电厂退款400一次、SOLD后消失，三方守护者及异玩家电厂保留；空玩家与重复调用无额外退款。tests/test_sellall_bench_c.py按名逐实读逻辑帧回放资金码/存活位/出售位/逻辑帧。仅显式玩家单电厂切片已量，多建筑枚举和其他模板推广INFERRED；不可售/受损/展开中/队列/驻军及This Player、All Players仍gap；见work/re/c_sellall_report.md'),
    (MODULE, 'AI/AnimalAIUpdate'): (TODO, 'E192 engine_animal_e:a原版女性平民近敌100/仅删模块/远敌700三路，f240四行240/0/7/7，六物体存活但均未离开起点。engine_animalfire_e:a增加敌兵攻击旁电厂，仍240/0/7/7，三路受击前置未成立；两局原逃跑预测FAIL保留。tests/test_animal_bench_e.py按名字回放实读负基线，开火接受Sim63对台7保留strict xfail。ra3ext tgt0/inc3/ua0无fleeTrigger/attackAccepted/rejectReason，触发资格未闭合（INFERRED），不实现猜测规则、不登记效果覆盖；同输入暂停，需合法触发或接受证据与新预算，见work/re/e192_animal.md'),
    (ACTION, 'NAMED_SET_SPECIAL_POWER_COUNTDOWN'): (TODO, 'C两局engine_namedcount:a/engine_namedvac:a：三独立玩家宿主，1秒0/2、7秒2/0交换，第三方不操作；铁幕f43..143就绪0、f153..315为7，真空弹f41..148为0、f155..300为3，宿主位均7、零余电位均0。旧零/非零预测被否定；缺真实剩余冷却/READY刷新与宿主初始化同帧字段，秒数与作用域未闭环。两个按名逐31实读帧回放strict xfail，未改模型、未晋升；假设表及字段缺口见work/re/c_namedcount_report.md'),
    (ACTION, 'TEAM_EXIT_ALL_BUILDINGS'): (BENCHED, 'C engine_teamexit:a混装建筑/运输车一局：本队征召兵退出公寓和牛蛙，同容器异队保留；队外成员/两宿主均存活，空队伍与重复调用无误伤。f44..74本队驻/异队驻/存活位3/3/127，f82..287为0/3/127；tests/test_teamexit_bench_c.py按名逐33个实读逻辑帧回放四计数器。仅显式存活队伍普通退出切片；精确出门位置/时序、运输抛射、取消进驻中订单、死/缺队伍及AI实例仍gap，其他模板推广INFERRED；见work/re/c_teamexit_report.md'),
    (ACTION, 'PLAYER_KILL'): (BENCHED, 'C engine_playerkill:a一局：目标Soviet_4守护者/电厂死亡，Player_1与Soviet_5同类对照保留；空Soviet_6调用和重复调用未误伤。f45/61/75单位位/建筑位/死亡位7/7/0，f83/152/287为5/5/0；tests/test_playerkill_bench_c.py按名逐实读逻辑帧回放四计数器。仅所属普通对象清理切片已对拍；玩家失败/淘汰、保护对象、容器/子体、死亡瞬间和其他模板推广仍gap或INFERRED；见work/re/c_playerkill_report.md'),
    (ACTION, 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanEgg'): (BENCHED, 'C engine_eggcmd:a与engine_eggnav:a两局：零售使用的防御/电厂/船厂三种核心，旧通用按钮均留原处；专用防御/船厂按钮到点展开，未下令对照留家。地面f249/393/560建筑位/存活位/原处位4/15/11，水域f247/390/496为2/7/5；tests/test_eggcmd_bench_c.py按名逐实读帧回放。Sim.act仅三种实测宿主且无地图本地定义时显式无操作，不映射专用展开；地图局部按钮、缺失/死亡宿主及其他宿主仍gap，跨宿主推广INFERRED；见work/re/c_eggcmd_report.md、work/re/c_eggnav_report.md'),
    (ACTION, 'TEAM_UPGRADE'): (BENCHED, 'C engine_teamup:a真实玩家升级查询+守护者状态位：f150本队/异队/查询0/0/0，f157授予后3/0/3，f248移除一人后2/0/1，f332再授予3/0/3；同玩家异队和敌方异队均无位。tests/test_teamup_bench_c.py按名逐实读帧回放；仅当前存活显式队伍OBJECT升级派发/消费者切片，j05地图私有升级效果、未来成员、死/缺队伍和AI队伍实例仍gap；其他宿主推广INFERRED；见work/re/c_teamup_report.md'),
    (ACTION, 'UNIT_STOP_SEQUENTIAL_SCRIPT'): (BENCHED, 'C engine_seqstop:a真实继续/停止对照：f282步骤111/1、到达码3，f308新排脚本后111/1001/3，f360保持。停止清当前及后排脚本，不取消已发移动，新脚本可再执行；tests/test_seqstop_bench_c.py按名回放四计数器。仅存活具名单车移动切片；精确移动/idle时序、自停、循环、死亡/缺失单位及其他订单仍gap；其他宿主推广INFERRED；见work/re/c_seqstop_report.md'),
    (ACTION, 'UNIT_SET_MODELCONDITION_FOR_DURATION'): (BENCHED, 'C engine_modeldur:a真实UNIT_HAS_MODELCONDITION查询：3/7秒USER_1分别为真46/106逻辑帧，b的1/2秒为真16/31帧，均含到期边界；空白阴性始终无位，永久阳性保持，状态码11→10→8。tests/test_modeldur_bench_c.py按名回放同帧四计数器。仅正持续时间、第四参数1.0、独立USER_1写入/到期切片；其他位推广INFERRED，重复/覆盖、零时长、第四参数其他值及原生生产者均gap；见work/re/c_modeldur_report.md'),
    (ACTION, 'PLAYER_ENABLE_UNIT_CONSTRUCTION'): (BENCHED, 'C两局engine_unitban:a/b具名玩家盟军工程师原生按钮：禁用期可排队但不扣款；恢复后付款/进度续跑，不退款不重置。a第150帧甲2000/乙1603，恢复后第198帧1843/1500/10，末1000/1000/33；b第101至180帧甲保持1800，第195帧1753/1500/10、第285帧1500/1500/11。tests/test_unitban_bench_c.py按名回放实读；第二笔队列付款提前10帧留strict xfail。仅此玩家/工程师切片已量，其他模板门禁INFERRED，UI拒绝、升级、建筑、AI及This Player/All Players范围仍gap；见work/re/c_unitban_report.md'),
    (MODULE, 'Behaviors/RecallUnitsSpecialPower'): (BENCHED, 'E187按名回放E184原版机场/仅删模块旧台，两路完整读数660/7/3/1与660/7/5/0通过；单架原生生产Apollo由机场按钮召回回近场并记录施放，使用模板速度移动，未改原预测。已测限本机场/机型单架；生产者筛选、选择顺序、回机场中心的路径为INFERRED，数量上限、精确帧、其他机型/机场、换主、降落及Parking仍gap；见work/re/e187_recall.md'),
    (ACTION, 'PLAYER_DISABLE_BASE_CONSTRUCTION'): (BENCHED, 'A269 aibgate:a（B的aiskirm图，s1盟军AI 10秒醒、50000）：开局禁用，醒后到第1054帧钱50000、建筑数1，不下任何建筑单；70秒恢复后f1054起付款、f1208第二栋（对照aiskirm d醒后11秒第二栋）。模拟simai.build拒结构单：f1065/f1215。tests/test_basegate_bench_a.py按名回放。C的engine_baseban：日本核心（UNIT_BUILD）不受此门；A的engine_basegate:a：脚本按盟军建造厂电厂按钮两边都不扣钱，玩家建造厂队列量不到（未模拟）。This Player/All Players范围仍gap'),
    (ACTION, 'PLAYER_ENABLE_BASE_CONSTRUCTION'): (BENCHED, 'A269 aibgate:a：禁用的AI在70秒恢复后立即开始下建筑单，f1054付款、f1208第二栋，节奏同刚醒（模拟f1065/f1215）。tests/test_basegate_bench_a.py按名回放；范围同DISABLE（具名AI玩家；玩家建造厂队列、This Player/All Players未量）'),
    (ACTION, 'SKIRMISH_AI_START'): (BENCHED, 'A270 B的aiskirm图去脚本库四局（s1盟军AI，10秒给50000）：只START（建造厂留在teamSoviet_1）、只MAKE_BASE、只SKIRMISH_AI_TRANSFER_ALL（交队不唤醒）都整局50000/建筑1；UNIT_AI_TRANSFER(建造厂)+START（原版a07写法）f169前付款、f290-f312第二栋（模拟f158/f308）。程序：START=TRANSFER_ALL的唤醒半步。模拟器：MAKE_BASE只对脚本库玩家代唤醒，simai只用交给AI的建造厂。tests/test_aistart_bench_a.py按名回放'),
    (ACTION, 'PLAYER_TOGGLE_SKIRMISH_AI'): (BENCHED, 'A270 aipause:a（aiskirm带库，25秒关、85秒开）：关后在造的付清到48300（f457）就冻结到f1262，暂停中造好的第3栋恢复后f1280才放下，f1300起又花钱。程序：写AI脑暂停字节，每帧更新整帧跳过。模拟器Sim.ai_paused：Brain.tick跳过思考、yard_due暂停时不放建筑。tests/test_aistart_bench_a.py按名回放；具名玩家，玩家掩码范围gap'),
    (MODULE, 'Behaviors/StructurePlacementBehavior'): (TODO, 'E183 structpon:a/structpoff:a原版矿场/仅删模块两局，前方120放电厂；总数及前方区域始终0，资金从10000采矿增长到11750/12000，未到9200付费哨兵。原禁建/允许预测FAIL保留，未建立合法排队/放置接受事实；tests/test_structureplace_bench_e.py仅按名字回放零电厂负基线，不登记模块效果已对拍。queueAccepted/queueReady/placementAccepted/rejectReason缺失，同输入暂停；几何消费/旋转/边缘仍gap，见work/re/e183_structureplace.md'),
    (MODULE, 'Behaviors/AssignSlavesTargetObjectSpecialPower'): (GUESSED, 'E181 engine_assignrace:b一局PASS：f150两组前三受伤目标UNDERGOING_REPAIR编码33，f180只给原版模块组指定第四辆，f360冻结第四辆HP70/20；tests/test_simassignslaves.py::test_repair_assignment_frame_snapshot_matches_named_bench按名回放同帧血量通过，占用模型0对台33保留strict xfail。原版480HP/20HP每秒预测成立，未改治疗率/时间窗；off同时删模块且不发令，不能单独归因模块删除。E66/E67旧捕获时序xfail保留；自动获取、单架子体派发/抢占、状态清理、其他宿主/筛选及精确启动帧仍gap，INFERRED启动相位未扩展，不登记整模块已对拍；见work/re/e181_assignframes.md'),
    (ACTION, 'REDALERT_DISABLE_THREAT_LEVEL_BONUS'): (TODO, 'C两局engine_threatbonus:a/b：A仅到第三批损失，不能用捕获秒作任务秒；B改逻辑帧闸门并交换禁用方，实测双方均第2893帧升二级（含禁用方），模型均5400。experimental/cnv/checks/engine_threatbonus.readings.toml具名阶段读数回放通过，协议升级读数strict xfail保留。未证明动作关闭协议经验倍率，不写无操作实现；缺同帧玩家threat/等级/倍率及单位经验奖励消费，整项未晋升。见work/re/c_threatbonus_report.md'),
    (MODULE, 'Behaviors/SpiderHoleUpdate'): (TODO, 'E178 spideron_e:a/spideroff_e:a原版反坦克步兵/仅删模块两局PASS，f45合法入洞、f120隔离者出洞；f90/f180具名状态及存活编码两侧均1515/1508，施放事件均3。tests/test_spider_bench_e.py具名回放状态通过，施放事件2 strict xfail（Sim为0）。手动切换由ToggleStatus提供，不据相同状态晋升扫描模块；同点载具实际距离/扫描接受与内部阶段未测，自动出洞假设未成立，_Ambush/精确扫描时钟/移动载具/攻击碾压仍gap，不拟合规则、不改分母；见work/re/e178_spider.md'),
    (MODULE, 'Behaviors/PrematureDischargeSpecialPower'): (TODO, 'E177 dischargeon_e:a/dischargeoff_e:a两局原版波能坦克/仅删模块对照，f45攻击、f75按键；f210冻结原版210/76/0/1、删模块210/0/109/0，首伤提前33脚本帧、施放事件1/0。删模块原施放1预测FAIL保留。tests/test_discharge_bench_e.py具名回放2 strict xfail：Sim两侧首伤47，且原版漏施放；武器PER_SHOT前摇及提前放电派发未闭合，不硬调模型、不登记已对拍。内部充能、伤害缩放、重复/取消、其他宿主与绝对帧均gap；见work/re/e177_discharge.md'),
    (MODULE, 'Behaviors/SpecialAbilityUpdate'): (GUESSED, 'E176 engine_specialability_e:a原版忍者/仅删模块对照一局PASS，f240冻结240/13/4/4：两侧曾有NON_AUTOACQUIRABLE，只有原版曾有UNATTACKABLE，最终均清状态且存活。experimental/cnv/checks/engine_specialability_e.readings.toml按名字回放四行实测，现有公开Sim无需改规则。仅此烟雾弹Pack状态设置/清除边界；精确开始/到期帧及Pack起算INFERRED，旧命令恢复、其他选项/宿主、重复施放、受击/死亡打断仍gap，不晋升整模块，不新增拆分用量；见work/re/e176_specialability.md'),
    (MODULE, 'Behaviors/PowerUpgrade'): (TODO, 'E175 engine_powerupgrade_e:a/b两局：a冻结330/11/10/11，b精确供电始终100/100/500/350，授予期升级持有位均0。高级原版500来自战役覆盖，删模块克隆为SDK350，不能拿基线差归因于模块。TriggeredBy的Upgrade_PowerPlantTurbine在SDK Upgrade.xml无定义；合法授予/接受拒因未闭合，倾向未解析引用（INFERRED），两局后暂停同输入。tests/test_powerupgrade_bench_e.py具名实际读数回放2 strict xfail，模型未改、不登记已对拍；原预测保留，购买升级、加电/撤销和其他升级门均gap；见work/re/e175_powerupgrade.md'),
    (MODULE, 'Behaviors/SecondaryObjectListenerModule'): (GUESSED, 'E174 engine_secondon_e:a / engine_secondoff_e:a原版多功能炮塔/仅删监听器对照；f60/f180/f360冻结主次体存活、乘员ENCLOSED和Repair升级位，原版3/15/3、删模块3/7/3。tests/test_secondary_bench_e.py具名回放；公开Sim补单乘员显式IncludeThing的UpgradeSelf进入授予/退出撤销，不改容器阈值。INFERRED：通知立即生效及未单测的显式模板匹配；gap：武器/外观通知、SelfValidation、复杂过滤、多乘员、其他宿主/乘员、死亡及精确帧，不登记整个模块已对拍；私有物体模型未接，见work/re/e174_secondary.md'),
    (MODULE, 'Behaviors/ReturnToProducerSpecialPower'): (TODO, 'E173 engine_returnon_e:a / engine_returnoff_e:a两局均f660冻结660/7/11/1：原生生产后具名引用，f405到离场区，返航后曾USER_1，最终存活回机场区且施放1。a遗漏显式原版资产替换，两局实际都保留原版飞机，删模块预测FAIL；不据相同读数判模块无效。b补显式replaces，仅静态/构建验证、未上台；原失败预测保留。tests/test_returnproducer_bench_e.py具名物体模型回放出发位0对实测7，2 strict xfail：生产按钮/引用前置未闭合，不手放飞机绕过。producerId、命令接受/拒因、机位/停靠阶段未量到，DOCKING未置位；暂停同输入，修正台须新预算，未实现返航、不登记已对拍；见work/re/e173_returnproducer.md'),
    (MODULE, 'Behaviors/HitReactionBehavior'): (GUESSED, 'E172 engine_hitreaction_e:b原版维和步兵/仅删模块对照，f180冻结完成180、血量99/99、位895：两侧举盾/合法受击/留在原位，只有原版曾出现HIT_REACTION，最终均清除；tests/test_hitreaction_bench_e.py按名字回放台上读数。公开Sim补零阈值heavy分支、配置状态门及条件时长；INFERRED：正实伤起算/刷新和精确到期。gap：受击转向、动画、非零阈值/light/medium、GoIdle/死亡类型门、其他伤害入口/宿主、精确时钟及状态门切换；不登记整模块已对拍。a诊断帧比较/持续采样错误保留，未拿其血量差推模块规则；见work/re/e172_hitreaction.md'),
    (MODULE, 'Behaviors/MovementSpecialPower'): (GUESSED, 'E171 engine_movement_e:a原版鬼王/仅删模块对照，f210冻结完成210、曾激活位1、离开起点位1、最终清状态且存活11；tests/test_movement_bench_e.py按名字回放台上读数。公开Sim消费TARGETED静态地点、ObjectStatus、Duration、LocomotorSet及自身AttributeModifier；仅覆盖合法范围内单次施放。INFERRED：从按键起算Duration及到期停走；gap：精确起止帧、对象目标/跟踪、超距接近、冷却/重复命令、碰撞伤害/反弹、舰船及其他配置。不登记整模块已对拍，见work/re/e171_movement.md'),
    (MODULE, 'Behaviors/SlaughterHordeContain'): (TODO, 'E170 engine_slaughter_e:a/b航母原版/仅删模块两局完成f600、宿主存活11，f180攻击期/f600返航后数量编码均0；a误用DRONE分类，b改AIRCRAFT后仍0。tests/test_slaughter_bench_e.py按名字回放负基线；快照未定位出机/吞入，不能以0判模块无效或借起重机AI撤退晋升。缺同帧命令接受、子机父体/存活轨迹及enterAccepted/停车阶段；同输入暂停，原数量预测FAIL保留，不推猜测模型，不登记已对拍；见work/re/e170_slaughter.md'),
    (MODULE, 'Behaviors/AssistedPlacementBehavior'): (TODO, 'E169 assistpon:a / assistpoff:a原版与删模块两局均资金8000、矿场总数0、提示位数量0、采样完成0；红色预览未落地，原吸附预测保留。当前计数器无放置接受/拒因字段，不能归因于模块；同输入暂停。tests/test_assistplace_bench_e.py具名回放资金负基线strict xfail：Sim未消费侧栏排队/放置点击；吸附、朝向、迷雾资格和精确距离均gap，不登记已对拍；见work/re/e169_assistplace.md'),
    (MODULE, 'Behaviors/QueueDockBehavior'): (GUESSED, 'E164消费D165 dockphase:a/off阶段证据：on装货f156..186、卸货f289..319各30帧，货量250→0；off首次交矿f200同帧异常，不是无效果对照。公开Sim已按继承读取码头模块，矿车选中缺码头矿场时明确报错、禁止模拟成功交矿；卸货结束清空货量。具名tests/test_simqueuedock.py回放拒绝边界、30帧卸250及清货；E180补装货结束才显货250，装货期保持0；装货计时现为29帧对台30帧，独立strict xfail，不改路径时钟迎合读数。整模块不晋升，骨骼/队列/绝对路径时钟仍gap，E152 f786快照保留strict xfail；见work/re/e164_queuedock.md、work/re/e180_queuedock_load.md'),
    (MODULE, 'Behaviors/CaptureSpecialAbilityUpdate'): (TODO, 'E151 engine_capture:a原版工程师对CaptureFlag中立/敌方/己方和删模块中立四路：归属100、存活1111、前置1，f45..575未换主。原预测111保留；具名测试仅回放负基线，不登记模块效果已对拍。缺命令被模块接受及同帧阶段证据（INFERRED），暂停同输入重跑；见work/re/e151_capture.md'),
    (ACTION, 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_CAMPAlliedBomberDrop2'): (GUESSED, 'A224-A226 engine_acts_mix:all、engine_acts_drop / _ally:own、engine_acts_wet:all、A266 engine_acts_edge:edge（store 放地图边上 / 界外，假设 D）：七局都没出轰炸机；A226 PLAYER_TRIGGERED_SPECIAL_POWER 看到按钮和按名字放都算放了（人类、电脑的 store 都是），所以卡在 OCL 生成那步（CREATE_AT_EDGE_NEAR_SOURCE），原因未明；模拟器只记施放、不出东西'),
    (MODULE, 'Behaviors/AutoDepositUpdate'): (GUESSED, 'E147 engine_bankcapture:a：中立SwissBank有/无模块两路普通工程师占领，换主并消耗工程师；on奖金750、随后每15游戏帧+5至770，off全0，帧锁定证据1023；具名测试test_simbankcapture按实际读数回放。E146已有归属产钱60/0仍有效；再占领/驻军/上限/修理仍gap，不晋升整项；见work/re/e147_bankcapture.md'),
    (MODULE, 'Behaviors/HealCrateCollide'): (TODO, 'E146 engine_objectbatch:a/b有/无模块均未治疗，步兵始终50/50；b中立箱且到位成立，仍无效，两轮后暂停；不把负结果登记成效果已对拍。SecretFile原XML含当前schema不接受的属性，未冒充普通HealCrate等价；碰撞派发前置待查；见work/re/e146_objectbatch.md'),
    (MODULE, 'Behaviors/LoseHealthUpdate'): (TODO, 'E146 engine_objectbatch:a/b：原船完整模块移植480HP坦克，HealthTrigger=101%/0%均无耗血，两路100/100；b已确认toggle/铁幕状态成立。两轮后暂停，移植激活资格待查，未推猜测实现、不晋升整项；见work/re/e146_objectbatch.md'),
    (MODULE, 'Behaviors/CommandSetUpgrade'): (GUESSED, 'E145单图engine_modulebatch:a：空初始菜单的兵营，授Tech2前产物0/0、授后有/无模块产物1/0。菜单切换解析已有；整链路具名回放strict xfail：生产层factories按未持升级的初始菜单识别工厂，故模型仍0/0，需B接口修复。未晋升整项；见work/re/e145_modulebatch.md'),
    (MODULE, 'Behaviors/MonitorSpecialPowerTimerUpdate'): (TODO, 'E145单图engine_modulebatch:a：原版质子炮宿主有/无模块，设技能就绪后SPECIALPOWER1_READY为1/0，设冷却后0/0。模型倒计时脚本入口和模块就绪输出仍gap；具名回放strict xfail，需A倒计时接口，不按纯表现排除；见work/re/e145_modulebatch.md'),
    (MODULE, 'Behaviors/AttackAssistResponseBehavior'): (TODO, 'E144派发诊断：engine_attackassist a两次准备运行均进关前崩溃，无台上读数；最终原版光谱塔宿主配方已修本地模块引用及结构武器掩码，尚未上台，暂停追加运行直至启动原因解释。tests/test_simattackassist.py严格xfail仅保留待验预测，不作已对拍证据；响应武器派发/原版增伤/时序均gap，模型未改；见work/re/e144_attackassist.md'),
    (MODULE, 'Behaviors/CircularDamageUpdate'): (TODO, 'E143最小消费诊断：engine_circular a/b/c/d具名回放仅保留负结果，不登记效果已对拍。陆地无ONLY_ON_WATER、MaxRadius175/ArcDistance50、径向50/100/150靶；正常/删激活/删模块/持续开火对照，消费前置仍未解释，未实现接口。Lifetime推进、SweepWeapon实际派发、水面过滤、重复激活和死亡清理均gap；tests/test_simcircular.py；假设表见work/re/e143_circular_gate.md'),
    (NUGGET, 'ActivateCircularDamageNugget'): (TODO, 'C线前置门禁：原版TeslaNova的Lifetime决定扩散速度，伤害来自宿主CircularDamageUpdate的SweepWeapon；E线模块消费接口尚缺，不能用直伤或DOT代替。0局、无台上读数，不登记已对拍；接口需求与假设表见work/re/c_circular_gate_report.md'),
    (NUGGET, 'ReportWeaponFiredStatNugget'): (NA, '纯统计（C线工单允许排除）：只记录玩家武器开火次数；原版两份空配置附于SovietVacuumBomb / ParticleCannonWeapon，伤害与创建物体由独立WeaponOCLNugget负责。保留用量2，不登记已对拍；未上台，不模拟战后统计；证据见work/re/c_reportstat_report.md'),
    (MODULE, 'Behaviors/PassiveAreaEffectBehavior'): (GUESSED, 'E70范围/兵种/状态开关和E74分批治疗具名回放保留。E145单图engine_modulebatch:a：MaxBeneficiaries=1/0两组，早期受益人数1/3、后期3/3，敌方均50%不回血；已补0/1上限，tests/test_simmodulebatch.py按名断言台上读数。E163 engine_areaally:a跨玩家双向友军伤员与己方同步50→100、inactive保持50；b脚本f240友军快照15（己方/友军满血、inactive半血、源满血），experimental/cnv/checks/engine_areaally.readings.toml 读数核对该快照。已补显式双向Friend治疗资格；两局原捕获秒断言FAIL保留，b末帧448未到f450，敌对/位置快照未测，不据零值推规则。见work/re/e163_areaally.md。具体受益身份次序、共用任务帧相位和SDK换算跳幅INFERRED；E165 engine_areaself:a原自疗预测失败，f61半血快照7/f210满血快照6/存活7；engine_areaselfpeer:a完整PASS，f210源/远端对照/旁步兵/旁工程师HP=50/50/100/100、存活15。已明确排除治疗源自身，允许另一工程师受益；tests/test_simareaself_e.py按名断言两局台上快照，原a预测保留，见work/re/e165_areaself.md。E166 engine_areaoverlap:a叠加满血预测失败，f61/f100/f210=31/29/31；b完整PASS，三快照31/31/31，f100单源与双源均75..80%、关闭50%，四源满血且七物体存活。已支持双满血同规则无限人数源重叠按一次贡献回放，tests/test_simareaoverlap_e.py按名断言两局读数，原a预测保留，见work/re/e166_areaoverlap.md；同规则源身份选择INFERRED。时钟来源/动态创建与重开/调查周期/其他重叠或受伤源/隐式联盟或中立单向关系/自身与人数上限交互/附着无人机/更大上限仍gap，不登记整项已对拍；见work/re/e145_modulebatch.md、e_passive_e74.md'),
    (MODULE, 'Behaviors/TechUpgradeReceiver'): (GUESSED, 'E167 engine_techrecvon/engine_techrecvoff:a原版工厂/仅删二级接收模块两局PASS，均完整f330；f60/f180/f300冻结15/15/15，f180近侧300距离持有数2/1、远侧750距离1/1（含各自建造场来源），f210删除来源后f300双方均0、两工厂存活。tests/test_simtechreceiver_e.py按名字回放台上读数；公开Sim补读链接覆盖GameObject XML，未改传播规则。仅此Tech2/建造场/工厂配置，精确传播时钟及矩形角点距离INFERRED；三级、其他宿主/来源、关系/换主/半径边界/生产仍gap，不晋升整模块、不拆分用量；见work/re/e167_techreceiver.md'),
    (MODULE, 'Behaviors/TrackDamage'): (TODO, 'E69静态核实：6个SDK配置均InstantWeaponsOnly=true，TimeToTrack为0/1/2s；现有expected_damage只接来弹，历史伤害仍gap。与C线瞬发历史接口工单重叠，E暂停独立探针；尚无本模块具名实测回放，不登记已对拍、不改分母；见work/re/e_trackdamage_e69.md'),
    (MODULE, 'Behaviors/InfiltratorContain'): (GUESSED, 'E198按总控配置收尾；ENERGY独立已对拍4用量/6模板，STEAL_MONEY独立登记3用量/4模板，车辆VISION_UNITS另行登记4用量/4模板仍推断；RESET另行登记5用量/6模板仍推断；普通VISION另行登记5用量/5模板仍推断；飞机VISION_UNITS另行登记2用量/2模板仍推断；步兵VISION_UNITS另行登记3用量/3模板仍推断；舰船VISION_UNITS单列3用量/3模板仍推断；PARALYZE单列3用量/3模板已对拍；KILL另行登记1用量/1模板仍推断；本行无剩余配置，不登记整组或整模块已对拍。逐配置边界：KILL单列1用量/1模板仅存活已测（engine_infkill a/c，另c已量到玩家击杀归属；敌消耗/友拒入、满血不换主；tests/test_siminfiltrator_kill.py）；PARALYZE单列3用量/3模板已对拍（三国engine_infpara a/b、engine_infpsov a、engine_infpjap a移动及engine_infpatk/engine_infasov/engine_infajap a攻击，tests/test_siminfiltrator_paralyze.py）；普通VISION 5用量/5模板部分已测且暂停扩宿主（engine_infvis a/b稳定窗通过，c已接敌消耗/友拒入、满血原主与s19起局部揭示，s18=0时序保留strict xfail，见work/re/e196_vision.md）；港口阻断VISION单列1用量/1模板，实测边界见该行；飞机VISION_UNITS单列已接E199前300帧周期；步兵VISION_UNITS单列已接E199前300帧周期；车辆VISION_UNITS已接同一周期（engine_inffoot c、engine_infclock a，tests/test_siminfiltrator_clock.py）；完整筛选/移动/生产/到期仍gap；舰船VISION_UNITS已独立分区，实测边界见该行；RESET单列仅入楼已接（engine_infreset a/b就绪与真实冷却未闭环、strict xfail）。VISION/STEAL_MONEY/VISION_UNITS/RESET具名回放见tests/test_siminfiltrator.py。INFERRED：进入距离/生效和精确到期、VISION约5秒延迟/半径映射/宿主死亡清理、KILL致死清理；gap：其他间谍/模板、PARALYZE生产/重复进入/旧攻击订单、KILL抛飞/死亡效果、VISION持久性/重复进入及未测配置。已测PARALYZE不代表其余配置已测；完整逐配置证据与原始读数指针见work/re/e142_infiltrator_closure.md'),
    (MODULE, 'Behaviors/InfiltratorContain:ENERGY'): (BENCHED, '总控11-11授权按配置组收尾：engine_infiltrator a/b/c/d按名字重放，盟军间谍对盟/苏/帝普通电厂及帝国忍者对盟军电厂，敌方进入者消耗、建筑满血不换主、100电量停电约20秒并恢复，友军拒入且存活；gap：其他电量/苏联超级电厂、重复进入续期、精确时序和默认状态分支仍未对拍，不表示全字段全模板已验证'),
    (MODULE, 'Behaviors/InfiltratorContain:STEAL_MONEY'): (BENCHED, '总控11-16按完整配置收尾：3用量/4模板；engine_infmon a的s13实测p1/s1资金3000/3000（初始1000/5000），转账2000，敌方间谍消耗、友军拒入，两矿厂满血且归属不变。仅盟军间谍/盟军矿厂单次足额转账效果已实现；gap：其他宿主/间谍、余额不足、重复进入、BlockedDuration收入阻断；通用进入距离/时钟INFERRED，s11稳定窗及匿名矿车清除/后续收入回放保留strict xfail，未放宽原断言；按总控与ENERGY同样的配置登记口径，不表示全字段全模板均已验证；见work/re/e193_money.md'),
    (MODULE, 'Behaviors/InfiltratorContain:KILL'): (GUESSED, 'E205完整KILL签名单列1用量/1模板；engine_infkill a按名回放s1..7敌友11100/11100、s18..30为1100/11100，敌间谍不再存活、友间谍存活、两起重机满血原主。c独立实测s46..52=1100/11100/1/111（敌/友/玩家击杀归属/派发抵近阶段），已接起重机所属玩家记账，不推具体击杀对象身份。原18..30预测窗口仍FAIL，b/c实际早窗回放保留strict xfail；Amount=1.5与空Eva事件及无额外属性/子项由分区测试守住；同宿主SlaughterHordeContain的友军载具过滤不含本台间谍，不据入楼声称抛飞或死亡派发已验证。致死清理与进入距离/时钟INFERRED；抛飞轨迹/死亡模块派发、其他间谍/玩家与重复进入仍gap，不进BENCHED_TESTS、不晋升已对拍；见work/re/e205_kill.md'),
    (MODULE, 'Behaviors/InfiltratorContain:PARALYZE'): (BENCHED, 'E202按总控与ENERGY相同的完整配置口径单列3用量/3模板；engine_infpara b、engine_infpsov a、engine_infpjap a及engine_infpatk/engine_infasov/engine_infajap a按名回放敌消耗/友拒入、满血原主、同属既存幻影移动与新订单攻击暂停/恢复，异类及第三方对照不暂停。台上移动对照21/21/22秒到、同属45/46/45秒到；攻击HP原值76/95/76→100/92/68→68/92/68。精确到达/血量回放保留strict xfail（模型到达23/47秒、基线80/95/80），未调伤害或阈值；精确进入/到期INFERRED，生产/重复/旧订单/其他匹配模板仍gap，不表示全字段全模板已测、不晋升整模块；见work/re/e202_paralyze.md'),
    (MODULE, 'Behaviors/InfiltratorContain:VISION_PORT'): (BENCHED, 'E201按总控完整配置口径独立登记1用量/1模板；engine_infport a/b按名回放敌消耗/友拒入、满血原主、近同属与近第三方可见、远端隐藏、身份位置511；a第二间谍存活，b取消首次敌入港后同一第二间谍被消耗，闭合重复阻断对照。gap：其他间谍/玩家、长时持久性/到期、死亡清理及观察者内部；精确进入/揭示相位、半径映射与XML阻断到期INFERRED，b的s25瞬态保留strict xfail，不调时钟；见work/re/e201_port.md'),
    (MODULE, 'Behaviors/InfiltratorContain:VISION'): (GUESSED, 'E196普通VISION完整配置5用量/5模板（同宿主RADAR_FREEZE未测）；engine_infvis a/b/c按名回放敌消耗、友拒入、满血原主与局部揭示稳定窗。日本s18实测0而模型提前揭示，单独保留strict xfail；不拟合延迟、不登记已对拍。进入距离、约5秒激活、半径映射和死亡清理仍INFERRED；精确时钟/其他模板/重复与持久性仍gap；见work/re/e196_vision.md'),
    (MODULE, 'Behaviors/InfiltratorContain:RESET'): (GUESSED, 'E195完整RESET配置5用量/6模板；engine_infreset a/b原台末段s21–35/s41–55敌间谍消耗、友军拒入、建筑满血原主且正供电，test_spy_superweapon_reset_entry_as_on_the_bench按名断言。仅苏联铁幕/盟军间谍首次入楼已接；原s11/s31进入窗口和全部就绪读数仍strict xfail，真实冷却未观测，不拟合十秒恢复；进入距离/时钟INFERRED，其他宿主/间谍/重复仍gap。不登记已对拍、不扩大整模块覆盖；见work/re/e195_reset.md'),
    (MODULE, 'Behaviors/InfiltratorContain:VISION_UNITS_AIRCRAFT'): (GUESSED, 'E197飞机完整配置2用量/2模板；engine_infair a独立飞机对照按名回放敌间谍消耗、友军拒入、两机场满血原主。E199接既存AlliedSupportAircraft前300帧0/1/1/1/1周期（engine_infclock a，tests/test_siminfiltrator_clock.py）；观察者内部/完整筛选/到期仍gap，旧墙钟可见位保留strict xfail，不从30秒XML推连续揭示；通用进入距离/时钟INFERRED，其他宿主/间谍/玩家/重复未测，不登记已对拍；见work/re/e197_aircraft.md'),
    (MODULE, 'Behaviors/InfiltratorContain:VISION_UNITS_SHIP'): (GUESSED, 'E200舰船完整配置3用量/3模板；engine_infship a独立水陆对照：敌消耗友拒入、满血原主、身份位置511、异类/第三方隐藏；c逐帧300位、20页均31710（0/1/1/1/1）已接具名回放，a墙钟间歇strict xfail；观察者内部/完整筛选/移动/生产/到期仍gap，不登记已对拍；进入距离/时钟INFERRED；见work/re/e200_ship.md'),
    (MODULE, 'Behaviors/InfiltratorContain:VISION_UNITS_INFANTRY'): (GUESSED, 'E198步兵完整配置3用量/3模板；engine_inffoot a独立步兵对照按名回放敌间谍消耗、友军拒入、两兵营满血原主，身份位置511。E199接既存AlliedEngineer前300帧0/1/1/1/1周期（engine_inffoot c，tests/test_siminfiltrator_clock.py）；观察者内部/完整筛选/到期仍gap，旧墙钟保留strict xfail，不从30秒XML推连续揭示；进入距离/时钟INFERRED，其他宿主/间谍/玩家/重复未测，不登记已对拍；见work/re/e198_infantry.md'),
    (MODULE, 'Behaviors/InfiltratorContain:VISION_UNITS_VEHICLE'): (GUESSED, 'E194完整车辆配置4用量/4模板；engine_infveh a敌间谍消耗、友军拒入，两厂满血原主，test_spy_vehicle_factory_entry_as_on_the_bench按名断言原台s19–25与s34–35。E199接既存AlliedAntiVehicleVehicleTech1前300帧0/1/1/1/1周期（engine_infclock a，tests/test_siminfiltrator_clock.py）；b直接SET与旧计数同步间歇，c三类标记位置掩码恒111仍间歇；a/b/c可见位及s10入楼时钟保留strict xfail，不拟合连续30秒；观察者内部/寿命、完整筛选/移动/生产和其他宿主/间谍/重复仍gap；进入距离与时钟INFERRED。不登记已对拍、不扩大整模块覆盖；见work/re/e194_vehicle.md'),
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
    (NUGGET, 'ActivateLiftObjectNugget'): (GUESSED, '部分：按模块证据实现开火者举升表，trunc(TimeIncrement×15)逐发累加、续期封顶MaxTimeLifted、逐帧递减释放；Lifetime不参与，释放不清LIFTED；tests/test_lift_nugget.py按名回放engine_lift a旧读数一致，landing因落地清位未实现strict xfail；engine_liftground a原百合子/入驻IFV/入驻炮塔与删Nugget为11/111/111/10；engine_liftair a为0/100/100/10（三原版飞机死亡、未锁存LIFTED，阴性存活），原对空预测FAIL保留；tests/test_lift_nugget.py具名回放实际读数，两strict xfail（原版复杂筛选/飞机消费未接通），见work/re/c_liftretail_report.md；地面3/对空3均有局部读数但完整消费者仍未对拍，旧合成VEHICLE组不占原版用量；A169已量接地帧但28清位/40与60不清的门槛未解；落地清位规则INFERRED，垂直运动/死亡/飞机/弹体/复杂筛选仍gap，不登记整项已对拍；整项边界见work/re/c_liftclosure_report.md'),
    (NUGGET, 'AttachNugget'): (GUESSED, '部分：engine_attach a实测直接单发、父子状态、随父移动及目标状态/类型拒绝；仅零半径简单模块，原版复杂筛选/维修/吸血/解除/弹体未接通；engine_attachc4 a原版谭雅/删Nugget及父EXPLOSIVES_ATTACHED对照为11/10024/10030/10028，正常原版附着后父死子活，禁用父仍有MARCH_OF_DEATH但无ATTACHED；tests/test_attach_c4.py具名回放，原生模块状态/链接/爆破消费strict xfail，见work/re/c_attachc4_report.md；engine_attachmine a原生磁力地雷本体原位创建/删Nugget×普通/SPECIAL_ARMOR_ACTIVE为111/110/111/110，保留者均附着、删除者均不附着；tests/test_attach_mine.py具名回放阴性，b三个禁用位均读到仍附着为111/110/7111/7110，两原生回放strict xfail；上游弹体/OCL、复杂筛选及生命周期仍gap，见work/re/c_attachmine_report.md；不登记整项已对拍'),
    (NUGGET, 'SpecialPowerNugget:变装消费者'): (GUESSED, '2用量：间谍/迅雷直接命中DISGUISED位及INFANTRY/VEHICLE/恐怖机器人排除已测；engine_spndisguise/spnspyx/spnspyex/spntrans/spntrfilter a均1111/1110/1110/1111，tests/test_special_power_nugget.py按名回放；gap：身份/外观/索敌/换目标/取消，迅雷展开时序strict xfail，即时位应用INFERRED；engine_spnrelations a间谍/迅雷各Friend与Neutral四路s6-15全1111，独立命中且无脚本变装位；engine_spncancel a四路真变装保留/空载撤离/删SPN/仅脚本位稳定1101/1101/1110/1111：普通征召兵自动攻击仅伤后两路，空载撤离不取消；engine_spncargo a有载撤离high从111101到101100再101110，实测出舱/清位后才受伤，原截图时间窗预测FAIL不改阈值；两原生消费者回放strict xfail，脚本位不等于真实身份。身份/时序缺口见work/re/c_spnclosure_report.md、c_spncancel_report.md，不登记完整消费者'),
    (NUGGET, 'SpecialPowerNugget:轰炸消费者'): (GUESSED, '1用量，暂停：engine_spnbombnative a原版/删SPN/合成/合成删SPN为1010/1110/1110/1110；OCL活动消费者未实现，具名回放strict xfail；需要原版与合成宿主派发观测，work/re/c_spnbomb_report.md'),
    (NUGGET, 'SpecialPowerNugget:干扰消费者'): (GUESSED, '1用量，暂停额外SPN消费：engine_spnscr c原版四路删减、受害者真实开火、靶子封闭暴露窗，早HP100/100/90/90、晚HP90/90/80/80，打包301000090/301000090/300999080/300999080实机PASS；tests/test_special_power_nugget.py具名回放。停火差异由AttributeModifier决定，保留/删SPN相等不能证明额外消费者no-op；b仅NAMED_STOP仍续射，原预测strict xfail保留。两局耗完，缺SpecialPower开始/结束及命令消费观测，不晋升完整消费者，见work/re/c_spnscr_active_report.md'),
    (NUGGET, 'SpecialPowerNugget:附着dummy消费者'): (TODO, '1用量，暂停：JapanScoutInfantryAttachWeaponWarhead引用OBJECT dummy模板及原版宿主；缺独立派发/附着读数，不能按Dummy名字推定无操作；需Attach模块观测，work/re/c_spnclosure_report.md'),
    (MODULE, 'Behaviors/OCLSpecialPower'): (BENCHED, '总控第四切片按已测边界收尾：tests/test_simocl.py具名回放engine_oclcurtain/engine_oclnone/engine_oclwrong a，铁幕宿主匹配模块才保护并记事件，删除/改绑模块无保护/事件；engine_oclempty a空声明无保护且事件1；engine_oclcopy a完整原版载荷改名仍保护100/100且事件1；engine_oclzero a仅外层Count=0无保护且事件1。只闭合铁幕派发和零数量不保护边界，未测生成数量/通用生成；其他非零数量/载荷/超武、位置/过滤、按钮/冷却仍gap，继承、等价空声明及格式等价INFERRED，不表示全模块全字段验证；见 work/re/e_ocl_e65.md'),
    (MODULE, 'Behaviors/ActivateModuleSpecialPower'): (GUESSED, 'E153 engine_activate:a 原版雅典娜宿主/仅删本模块对照，合法按钮激活链接ShieldSphereUpdate；f76..371状态111/100，f379消退100/100，证据7。tests/test_simactivate.py按名回放并断言实测f152/f379；仅实现SELF_POSITION、InitiallyActive=false链接的ObjectStatus/Duration。吸收伤害、上限、提前终止、重复激活及其他链接仍gap；不晋升整项，不表示C的SpecialPowerNugget派发覆盖；见work/re/e153_activate.md'),
    (MODULE, 'Behaviors/RadarBehavior'): (GUESSED, 'E158原版雷达宿主/仅删模块对照，两构建均隔离原生PlayerSpellBook，不强开地图或UI。engine_radar:a宿主删除前后小地图显示/阵营徽标。E159 engine_radarlow:a只删电厂，供需150/75→50/75，f147/f302宿主及消费者均存活、供电1/0，小地图均显示；tests/test_radar_bench_e.py按名回放供需、存活及HUD。E160 engine_radartwo:a两同类宿主，f114/f197/f386存活11→01→00、独立HUD地形→地形→徽标，供电及前置均1；按实测帧回放，慢速运行现实秒断言FAIL原样保留见work/re/e160_radar_multi.md。E161 engine_radardeath:a原版500HP宿主受250/1000伤害，f87=100%、f95/f173=50%且地形，f182死亡1/HP0且HUD关闭过渡、f192/f374徽标，供电前置始终1；按名回放HP/死亡/供需/HUD，见work/re/e161_radar_death.md。E162 engine_radarout/in:a脚本双向换主，两局本地HUD分别作原主/新主：out f91归属1地形→f312归属2徽标，in f87归属2徽标→f282归属1地形，宿主存活及双方供电前置均1；按名回放归属/存活/双侧供需/HUD，见work/re/e162_radar_owner.md。不表示工程师占领或直接观测Soviet_4 HUD。只覆盖已建成盟军雷达宿主正常/不足供电、同类多来源脚本删除、受伤致死及脚本换主采样边界；注册内部实现INFERRED，精确死亡注销/换主帧、其他致死来源、建造、工程师占领、混合模板和其他宿主仍gap，不晋升整项。PLAYER_HAS_POWER物体模型条件缺口strict xfail；见work/re/e158_radar.md、work/re/e159_radar_power.md'),
    (MODULE, 'Behaviors/ParkingPlaceBehavior'): (BENCHED, 'E188复用E157两局旧台，tests/test_parking_bench_e.py按名字回放原机场/仅删模块f194=1/0、f982=4/0及交换玩家f196=1/0全部通过；消费LIMITED_PRODUCTION_AIRCRAFT及配置配额4，修空闲队列后续唤醒。只覆盖本机场Apollo生产差异；准入发生在下单阶段、排队/出场预留为INFERRED，精确生产帧、筛选、物理机位、返航预约/占用/释放、航母及其他机型仍gap；旧队伍飞离预测失败仍保留，不追加实机；见work/re/e188_parking.md'),
    (NUGGET, 'TintObjectsNugget'): (NA, '纯表现：Color及Pre/Sustained/PostColorTime、Frequency/Amplitude仅控制染色动画；engine_tint pair实测2/90/2/90，独立DamageNugget解释全部伤害，test_simbench_c重放；不声称像素已验证'),
    (NUGGET, 'MetaImpactNugget'): (TODO, '剩余复杂写法：延迟、Arc、飞机资格等；engine_knock_filter a/b两局99/99/3/3，原版每路4次冲击、删除筛选7次。tests/test_meta_filter.py具名回放地面派发/速度/铁锤落点：恐怖机器人和磁暴步兵显式包含越过INFANTRY，铁幕状态仍拒绝；飞机两局无冲击且缺逐帧高度/拒绝原因，完整消费者不晋升，见work/re/c_filter_report.md。engine_knock_invert水平反向回放已绿；engine_knock_objectgate a/b均99/99/1/0，保留ForbiddenTargetObjectStatus拒绝脚本LEECHED_TARGET_ACTIVE邻人、仅删字段后放行，tests/test_meta_objectgate.py具名回放派发/七帧路径；该隔离台移除Arc/模型条件/步兵过滤；engine_knock_kindgate a/b均99/99/11/0，保留INFANTRY子筛选及状态门时仅无位步兵邻人冲击，删子筛选后无位合成非步兵亦冲击，带位两邻人仍拒绝。tests/test_meta_kindgate.py具名回放派发/初速度和步兵七帧路径；合成非步兵落点网格轨迹strict xfail，原生吸血生命周期及Arc/模型条件组合仍gap，见work/re/c_kindgate_report.md；普通延迟只解析及隔离队列，Physics相位未解。ShockWaveSpeed/Cyclonic、非默认Physics、坡地及V4到达仍gap'),
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
    (MODULE, 'Behaviors/StealthDetectorUpdate'): (BENCHED, '已测范围：engine_detector:a原版军犬/仅删模块/超半径三路，距离150/150/450；目标INVISIBLE_DETECTED在f151为1/0/0，删除军犬后f310均0，目标始终存活；tests/test_detector_bench_e.py按名用私有物体模型回放同帧读数，原有实现无需修改；gap：公开Sim未接反隐（strict xfail），精确首扫/清除帧、半径边界、移动/驻军/多探测器/其他宿主及过滤配置未对拍；见work/re/e156_detector.md'),
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
    (MODULE, 'Behaviors/SubStructureStorageBehavior'): (TODO, '6用量/6模板为三国MCV及海军继承型，模块无专用字段；有效配置没有SubStructureBuild；engine_substorage_on/off:a仅测原版空载荷收起/展开对照，不登记已对拍，不据此排除运行时用途；gap：非空载荷、存储数量/父体绑定/保存恢复接受字段未测；普通展开及COPY_UPGRADES不能归因；见 work/re/e182_substorage.md（静态证据work/re/e_substorage_e57.md）'),
    (MODULE, 'Behaviors/SubStructureBehavior'): (TODO, 'E189 engine_substructure_e:a一局PASS，独立摆放的原版维修台/仅删模块对照，f59血量100/100、f120脚本伤害后80/80、f240删除无绑定建造场后80/80且场存活位0；experimental/cnv/checks/engine_substructure_e.readings.toml按名字回放最终四行240/80/80/0通过，无模型改动。只测独立摆放基线，不推断父子联动或模块无效；SDK有效XML无SubStructureBuild，现四行缺parentId/bindAccepted/forwardedDamage。父体绑定、伤害传递、清理及其他模板仍gap，同输入暂停，需合法绑定入口及新预算；见work/re/e189_substructure.md'),
    (MODULE, 'Behaviors/WallBuilderBehavior'): (GUESSED, '部分：engine_wallinit:a有/无模块对照10/11/10，仅StartInSecondaryModel默认WALL_SEGMENT初始化；6/6权重保留，建墙/连接/段数上限/生死联动及自定义配置仍gap，未登记完整已对拍；见 work/re/e_wallbuilder_e58.md'),
    (MODULE, 'Behaviors/GateOpenAndCloseBehavior'): (TODO, 'E190原版门/删模块初始化台被SDK Behaviors拒绝该模块且缺模型资源；原生地图摆放同样强制编译失败。改用engine_gate_e:a运行时同动作创建两门与电厂哨兵，一局PASS，f180=180/0/0/1（完成/Romania门/Sanitarium门/哨兵存活）。tests/test_gate_bench_e.py按名回放帧数与哨兵通过，SDK模型两门均1对台0，2 strict xfail；未改模型，不登记模块效果覆盖。缺templateResolved/createAccepted/rejectReason，倾向模板在当前运行环境不可用（INFERRED）；开闭/通行/复位均gap，同输入暂停，重开需可创建宿主及合法开关入口，见work/re/e190_gate.md'),
    (MODULE, 'Behaviors/SlavedUpdate'): (TODO, f'{_NOT_IN_SIM}（没有随从跟随）'),
    (MODULE, 'Behaviors/BezierProjectile'): (GUESSED, 'E168 engine_bezier_e:a单发原版V4火箭/仅删Bezier模块对照，f60满血编码3、f240冻结目标HP95/100；tests/test_bezier_bench_e.py按名字以私有物体模型回放，修复无飞行模块仍直接伤害目标的退化分支。公开Sim曲线弹接线、精确飞行/命中帧、追踪/移动目标、碰撞/地形、其他配置仍gap；无模块立即清理为INFERRED，不登记整个模块已对拍。两局原录像秒窗口FAIL保留，冻结帧判定见work/re/e168_bezier.md'),
    (MODULE, 'Behaviors/ProjectileUpdate'): (TODO, f'{_NOT_IN_SIM}（开火按每秒伤害直接扣血，没有弹体飞行时间）'),
    (MODULE, 'Behaviors/AttachUpdate'): (GUESSED, '部分：engine_attach a验证瞬移/跟随/父子状态；engine_attach_parent a验证简单模块脚本杀父后子活/清理链接，NO_COLLISIONS读数差异为严格xfail；原版模块死亡前无稳定链接，不推广死亡规则；子死/直接删除/维修/吸血/解除/自主扫描仍gap'),
    (MODULE, 'Behaviors/StoreObjectsSpecialPower'): (TODO, f'{_NOT_IN_SIM}（没有存放单位）'),
    (MODULE, 'Behaviors/TeleportStoredObjectsSpecialPower'): (TODO, f'{_NOT_IN_SIM}（没有传送存放的单位）'),
    (MODULE, 'Behaviors/TeleportStoredObjectsUpdate'): (TODO, f'{_NOT_IN_SIM}（UNIT_TELEPORT_TO_WAYPOINT 另算）'),
    (NUGGET, 'ActivateLaserNugget'): (NA, '纯表现：Lifetime/LaserId/HitGroundFX/OverShootDistance驱动LaserState/LaserDraw；engine_laser pair实测2/90/2/90，无附加伤害或首发延迟，test_simbench_c重放'),
    (MODULE, 'Behaviors/LaserState'): (NA, '纯表现：LaserId关联光束，起止粒子/骨骼/EndOffset与ObjectStatusValidation只控制光束表现；LaserStateModule.xsd无伤害字段；engine_laser pair匹配LaserDraw/State 201，伤害由独立DamageNugget给出，test_simbench_c重放2/90/2/90'),
    (MODULE, 'Behaviors/LUAEventList'): (NA, '纯表现：EventListName连接原版ScriptEvents.xml与Scripts.lua；RA3声明可达的事件处理函数只调用模型部件显隐（及tostring），含继承；未定义的AlliedInfantryFightingFunctions无可达处理函数；C&C3升级/状态函数不可达。tests/test_inventory_lua.py静态核对游戏包与SDK声明，非上台对拍'),
    # batch 1 (work/re/l2_scripts1.md, checks/engine_scripts1.py, bench 11-08)
    (ACTION, 'TEAM_HUNT'): (GUESSED, '主人 aiTactical 255（人类除外）：攻击移动到最近敌对物体（单位也算），目标死后'
                                     '3 s 重选（engine_acts_y 台上量过）；240 不动。重选间隔是拟合值（INFERRED）'),
    (MODULE, 'Behaviors/ModelConditionUpgrade'): (NA, '纯表现：只加模型状态（民房/步兵按阵营换画法、支援技能画法），'
                                                     '同模板的非画法模块和原版脚本 UNIT_HAS_MODELCONDITION 都不读'
                                                     '（E 线 work/re/e_na_physics_mcu.md）'),
    (ACTION, 'NAMED_HUNT'): (GUESSED, '60 s 不动：没交 AI 的（engine_acts_w）和容器已交 AI 的 Soviet_3（engine_acts_y）'
                                      '都量过；醒着的 AI 后来会不会用这一位（引擎 B）没量'),
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
    (ACTION, 'PLAYER_ALLOWED_TOBE_COOPAI'): (NA, 'A219 读程序：只写 AI 脑的"可当合作 AI"位；读它的只有合作 AI 的'
                                              '界面 / 语音、玩家挑合作伙伴、关掉时取消合作 AI 正执行的玩家指令；'
                                              '模拟器的玩家没有给盟友下令的命令，脚本读不到它（同下一条）'),
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
            share = contain_audit.infiltrator_money_share(with_templates=True)
            v = dict(v, campaign=v['campaign'] - share['campaign'],
                     templates=v['templates'] - share['templates'])
            items.append(dict(part=MODULE, name='Behaviors/InfiltratorContain:STEAL_MONEY',
                              uses=share['campaign'], all=share['templates'], state=GUESSED,
                              template_ids=share['template_ids'],
                              why='完整经济配置，单次2000转账：engine_infmon a', eg='AlliedRefinery'))
            share = contain_audit.infiltrator_vehicle_share(with_templates=True)
            v = dict(v, campaign=v['campaign'] - share['campaign'],
                     templates=v['templates'] - share['templates'])
            items.append(dict(part=MODULE, name='Behaviors/InfiltratorContain:VISION_UNITS_VEHICLE',
                              uses=share['campaign'], all=share['templates'], state=GUESSED,
                              template_ids=share['template_ids'],
                              why='车辆完整配置：engine_infveh a/b/c；入楼已接，可见调度仍gap', eg='AlliedWarFactory'))
            share = contain_audit.infiltrator_aircraft_share(with_templates=True)
            v = dict(v, campaign=v['campaign'] - share['campaign'],
                     templates=v['templates'] - share['templates'])
            items.append(dict(part=MODULE, name='Behaviors/InfiltratorContain:VISION_UNITS_AIRCRAFT',
                              uses=share['campaign'], all=share['templates'], state=GUESSED,
                              template_ids=share['template_ids'],
                              why='飞机完整配置：engine_infair a；入楼已接，观察者/筛选仍gap', eg='AlliedAirfield'))
            share = contain_audit.infiltrator_infantry_share(with_templates=True)
            v = dict(v, campaign=v['campaign'] - share['campaign'],
                     templates=v['templates'] - share['templates'])
            items.append(dict(part=MODULE, name='Behaviors/InfiltratorContain:VISION_UNITS_INFANTRY',
                              uses=share['campaign'], all=share['templates'], state=GUESSED,
                              template_ids=share['template_ids'],
                              why='步兵完整配置：engine_inffoot a；入楼已接，观察者/筛选仍gap', eg='AlliedBarracks'))
            share = contain_audit.infiltrator_ship_share(with_templates=True)
            v = dict(v, campaign=v['campaign'] - share['campaign'],
                     templates=v['templates'] - share['templates'])
            items.append(dict(part=MODULE, name='Behaviors/InfiltratorContain:VISION_UNITS_SHIP',
                              uses=share['campaign'], all=share['templates'], state=GUESSED,
                              template_ids=share['template_ids'],
                              why='舰船完整配置：engine_infship a；入楼已接，观察者/筛选仍gap', eg='AlliedNavalYard'))
            share = contain_audit.infiltrator_paralyze_share(with_templates=True)
            v = dict(v, campaign=v['campaign'] - share['campaign'],
                     templates=v['templates'] - share['templates'])
            items.append(dict(part=MODULE, name='Behaviors/InfiltratorContain:PARALYZE',
                              uses=share['campaign'], all=share['templates'], state=GUESSED,
                              template_ids=share['template_ids'],
                              why='三国完整PARALYZE配置移动/新订单攻击回放；见 work/re/e202_paralyze.md', eg='AlliedTechStructure'))
            share = contain_audit.infiltrator_port_share(with_templates=True)
            v = dict(v, campaign=v['campaign'] - share['campaign'],
                     templates=v['templates'] - share['templates'])
            items.append(dict(part=MODULE, name='Behaviors/InfiltratorContain:VISION_PORT',
                              uses=share['campaign'], all=share['templates'], state=GUESSED,
                              template_ids=share['template_ids'],
                              why='港口完整阻断配置：engine_infport a；见 work/re/e201_port.md', eg='CA_PortStructure'))
            share = contain_audit.infiltrator_vision_share(with_templates=True)
            v = dict(v, campaign=v['campaign'] - share['campaign'],
                     templates=v['templates'] - share['templates'])
            items.append(dict(part=MODULE, name='Behaviors/InfiltratorContain:VISION',
                              uses=share['campaign'], all=share['templates'], state=GUESSED,
                              template_ids=share['template_ids'],
                              why='普通VISION完整配置：engine_infvis a/b/c；稳定窗已接，日本s18仍gap', eg='JapanConstructionYard'))
            share = contain_audit.infiltrator_kill_share(with_templates=True)
            v = dict(v, campaign=v['campaign'] - share['campaign'],
                     templates=v['templates'] - share['templates'])
            items.append(dict(part=MODULE, name='Behaviors/InfiltratorContain:KILL',
                              uses=share['campaign'], all=share['templates'], state=GUESSED,
                              template_ids=share['template_ids'],
                              why='完整KILL配置：engine_infkill a；存活/玩家击杀归属已接，抛飞与死亡派发仍gap', eg='SovietCrane'))
            share = contain_audit.infiltrator_reset_share(with_templates=True)
            v = dict(v, campaign=v['campaign'] - share['campaign'],
                     templates=v['templates'] - share['templates'])
            items.append(dict(part=MODULE, name='Behaviors/InfiltratorContain:RESET',
                              uses=share['campaign'], all=share['templates'], state=GUESSED,
                              template_ids=share['template_ids'],
                              why='完整RESET配置：engine_infreset a/b；仅入楼已接，真实冷却仍gap', eg='SovietSuperWeapon'))
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
    'MetaImpactNugget:镰刀敌我筛选': '仅镰刀无延迟筛选写法的发射者敌我关系→默认Physics；engine_knock_relation a健康99/100/99/100，ENEMIES仅敌/ALLIES仅友，逐帧位置回放。碰撞帧/爆心由台上输入；tests/test_meta_nocoll.py具名回放engine_knock_nocoll a/b：99/99/1/0与99/99/0/1，仅无NO_COLLISIONS位邻人收到冲击并三帧落到y3740。仅脚本置位；engine_knock_statusgate a/b均99/99/1/0，b仅删XML状态排除后有位邻人也收shock并三帧落y3740，tests/test_meta_statusgate.py四路具名回放；此切片无独立状态拒绝门，解析/消费按XML声明排除，原生位生命周期仍gap。engine_knock_kind a/b均99/100/99/100：原版步兵邻人收shock、铁锤无，删除Include后空Rule=ANY全无shock；tests/test_meta_kind.py具名回放派发/位置及空ANY拒绝。铁锤阳性未建立，原生位生命周期/倒地状态/非步兵拒绝归因仍gap，Physics状态映射INFERRED。engine_knock_sickle a/b真实跳跃两道均f114接地；a在f115仅敌兵收shock并三帧落y3540，b仅删MetaImpact后无shock、原地不动；tests/test_meta_sickle.py具名落地区域计数/落地事件消费回放已接通。精确到达帧和落点仍strict xfail，落地伤害筛选及衰减gap；仅派发冲击，不覆盖完整跳跃、延迟、Arc',
    'MetaImpactNugget:省略Z默认值': '仅普通无延迟弹头省略ShockWaveZMult→SDK默认1及默认Physics轨迹；engine_knock_z a高度93邻人14帧落(2420,3740)、目标99%/邻人100%。碰撞时刻/爆心为台上输入；直击噪声方向/网格/选人仍INFERRED，完整曲线弹/坡地/筛选未对拍',
    'InformTargetNugget:默认系数目标通知': '仅默认Min=.85/Max=1.15的目标通知→来弹表/矿车预计伤害开甲；engine_inform_probe a/off录入302、hit377、exp404、删除389，347帧入窗。engine_inform_expiry a/b只改预报速度及截止系数：两路截止313/304与303/317，物理清除336/312与336/320；tests/test_inform_ai.py具名入表回放绿，自主清理四strict xfail，不能以到期即时删除或共享周期拟合，见work/re/c_inform_expiry_report.md。另有合成engine_inform_radius a/b具名回放（tests/test_inform_radius.py）：Radius200通知80近邻、不通知320远邻，默认0仅主目标，删除通知全无；近邻复制主目标来弹信息。此合成切片不增加原版用量，边界/高度/异型护甲/复杂筛选仍INFERRED或gap，见work/re/c_inform_radius_report.md。历史/海啸/忍者及完整AI调度不在本登记范围，完整脚本仍xfail',
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


class _Unknown(Exception):
    """A part of a probe's CHECKS / MISSION the static reader cannot work out (it is skipped, not guessed)."""


class _Static:
    """Works out, from a probe's syntax tree alone, the entries of its CHECKS / MISSION / PAIR_BUILDS however they
    are written: a dict literal, a comprehension over a literal or a module-level constant ({k: .. for k in ('a',
    ..)}, `for b, v in VARIANTS.items()`, `for w in 'abc'`), f-string or helper-built keys (f'engine_unpack_{v}',
    _build(w) whose body is one return), `{**{..}, **{..}}` and `{..} | {..}` merges, and a name bound to any of
    these."""

    def __init__(self, tree):
        self.consts = {n.targets[0].id: n.value for n in tree.body
                       if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
        self.funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

    def entries(self, node, env, depth=0):
        """[(key, value node, env)] of the mapping `node`; a part it cannot work out is left out."""
        if depth > 8:
            return []
        if isinstance(node, ast.Dict):
            out = []
            for k, v in zip(node.keys, node.values):
                if k is None:
                    out += self.entries(v, env, depth + 1)
                    continue
                try:
                    out.append((self.value(k, env), v, env))
                except _Unknown:
                    pass
            return out
        if isinstance(node, ast.DictComp):
            out = []
            try:
                envs = self.bindings(node.generators, env)
            except _Unknown:
                return []
            for e in envs:
                try:
                    out.append((self.value(node.key, e), node.value, e))
                except _Unknown:
                    pass
            return out
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return self.entries(node.left, env, depth + 1) + self.entries(node.right, env, depth + 1)
        if isinstance(node, ast.Name) and node.id not in env and node.id in self.consts:
            return self.entries(self.consts[node.id], {}, depth + 1)
        return []

    def bindings(self, generators, env):
        envs = [env]
        for g in generators:
            if g.is_async:
                raise _Unknown
            more = []
            for e in envs:
                for item in self.iterate(self.value(g.iter, e)):
                    e2 = dict(e)
                    self.bind(g.target, item, e2)
                    if all(self.value(c, e2) for c in g.ifs):
                        more.append(e2)
            envs = more
        return envs

    @staticmethod
    def iterate(v):
        if isinstance(v, (str, list, tuple, set, frozenset, dict)):
            return list(v)
        raise _Unknown

    def bind(self, target, item, env):
        if isinstance(target, ast.Name):
            env[target.id] = item
        elif isinstance(target, (ast.Tuple, ast.List)):
            items = self.iterate(item)
            if len(items) != len(target.elts):
                raise _Unknown
            for t, x in zip(target.elts, items):
                self.bind(t, x, env)
        else:
            raise _Unknown

    def value(self, node, env, depth=0):
        """The Python value of the expression `node` (constants, containers, names, f-strings, simple calls)."""
        if depth > 20:
            raise _Unknown
        v = lambda n: self.value(n, env, depth + 1)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            if node.id in self.consts:
                return self.value(self.consts[node.id], {}, depth + 1)
            raise _Unknown
        if isinstance(node, (ast.Tuple, ast.List)):
            return tuple(v(e) for e in node.elts)
        if isinstance(node, ast.Set):
            return frozenset(v(e) for e in node.elts)
        if isinstance(node, ast.Dict):
            return {k: None for k, _, _ in self.entries(node, env)}
        if isinstance(node, ast.DictComp):
            return {k: None for k, _, _ in self.entries(node, env)}
        if isinstance(node, ast.JoinedStr):
            out = ''
            for part in node.values:
                if isinstance(part, ast.Constant):
                    out += str(part.value)
                elif isinstance(part, ast.FormattedValue) and part.conversion == -1 and part.format_spec is None:
                    out += str(v(part.value))
                else:
                    raise _Unknown
            return out
        if isinstance(node, ast.IfExp):
            return v(node.body) if v(node.test) else v(node.orelse)
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            a, b, op = v(node.left), v(node.comparators[0]), node.ops[0]
            ops = {ast.Eq: lambda: a == b, ast.NotEq: lambda: a != b, ast.In: lambda: a in b,
                   ast.NotIn: lambda: a not in b}
            if type(op) in ops:
                return ops[type(op)]()
            raise _Unknown
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            a, b = v(node.left), v(node.right)
            if type(a) is type(b) and isinstance(a, (str, tuple)):
                return a + b
            raise _Unknown
        if isinstance(node, ast.Call) and not node.keywords:
            f = node.func
            if isinstance(f, ast.Attribute) and not node.args and f.attr in ('items', 'keys', 'values'):
                d = self.value(f.value, env, depth + 1)
                if isinstance(d, dict):
                    if f.attr == 'keys':
                        return tuple(d)
                    full = self.full_dict(f.value, env)
                    return tuple(full.items()) if f.attr == 'items' else tuple(full.values())
                raise _Unknown
            if isinstance(f, ast.Name) and f.id in ('tuple', 'list', 'sorted') and len(node.args) == 1:
                items = self.iterate(v(node.args[0]))
                return tuple(sorted(items) if f.id == 'sorted' else items)
            if isinstance(f, ast.Name) and f.id in self.funcs:
                fn = self.funcs[f.id]
                body = [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
                a = fn.args
                if (len(body) == 1 and isinstance(body[0], ast.Return) and body[0].value is not None
                        and not (a.vararg or a.kwarg or a.kwonlyargs or a.defaults or a.posonlyargs)
                        and len(a.args) == len(node.args)):
                    inner = {p.arg: v(x) for p, x in zip(a.args, node.args)}
                    return self.value(body[0].value, inner, depth + 1)
        raise _Unknown

    def full_dict(self, node, env):
        """{key: value} of a mapping whose values are themselves worked out (for .items() / .values())."""
        if isinstance(node, ast.Name) and node.id not in env and node.id in self.consts:
            node, env = self.consts[node.id], {}
        if isinstance(node, ast.Dict) and None not in node.keys:
            return {self.value(k, env): self.value(x, env) for k, x in zip(node.keys, node.values)}
        raise _Unknown

    def functions(self, node, env):
        """The module-level function names a check value runs: a bare name (`a`), else every module-level function a
        lambda / call names in its body (lambda m, k=k: a(m, k) -> a), looked through a name bound to a constant."""
        if isinstance(node, ast.Name) and node.id not in self.funcs and node.id in self.consts and node.id not in env:
            return self.functions(self.consts[node.id], {})
        if isinstance(node, ast.Name):
            return [node.id]
        out = []
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and n.id in self.funcs and n.id not in out:
                out.append(n.id)
        return out


def probe_checks(text):
    """(missions, {check key: [function name]}) of a probe's source: its CHECKS = {mission: {key: function}} (and the
    builds of MISSION / PAIR_BUILDS) read from the syntax tree (a probe is not imported: it builds missions) by
    _Static, which works out comprehensions, f-strings and merges, and for a check written as a lambda or call names
    the module-level functions it runs. The one reader of a probe's builds and checks: the inventory's split by check
    (probe_parts, tested_checks) and the guard against new bench tests (tests/guards/test_bench_tests.py) both use it."""
    tree = ast.parse(text)
    st = _Static(tree)
    missions, keys = set(), collections.defaultdict(list)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = {getattr(g, 'id', None) for g in node.targets}
        if not names & {'CHECKS', 'MISSION', 'PAIR_BUILDS'}:
            continue
        for mk, mv, env in st.entries(node.value, {}):
            if isinstance(mk, str):
                missions.add(mk)
            if 'CHECKS' not in names:
                continue
            for k, v, env2 in st.entries(mv, env):
                if isinstance(k, str):
                    for fn in st.functions(v, env2):
                        if fn not in keys[k]:
                            keys[k].append(fn)
                    keys.setdefault(k, [])
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
    docs/engine/*.md marked measured (**测**), the generated PAGES left out. In both a line NOT_MEASURED marks is left out (engine_aiupgrade's
    'Retail tech entries have MinTime >=180s, outside the observation' made MinTime 已对拍)."""
    need(CHECKS, 'the bench checks')
    need(ENGINE_DOCS, 'the engine docs')
    out = []
    for f in sorted(os.listdir(CHECKS)):
        if f.startswith('engine_') and f.endswith('.py'):
            text = open(os.path.join(CHECKS, f), encoding='utf-8').read()
            out += [(s, measured(t)) for s, t in probe_parts(f[:-3], text)]
    for f in sorted(os.listdir(ENGINE_DOCS)):
        if f.endswith('.md') and f not in PAGES:
            lines = [x for x in open(os.path.join(ENGINE_DOCS, f), encoding='utf-8')
                     if '测' in x.replace('未实测', '').replace('推断', '')]
            out.append((f'docs/engine/{f}', measured(''.join(lines))))
    if not out:
        raise SystemExit('inventory: no bench sources found')
    return out


TESTS = os.path.join(ROOT, 'tests')
PROBE_NAME = re.compile(r'(?<![A-Za-z0-9_])(engine_[A-Za-z0-9_]+)')
_TOOL = re.compile(r'inventory(?:_\w+)?$')


def without_tool_tests(text):
    """`text` with the functions that test the inventory tools themselves blanked out: a function that calls one
    (inventory.tested_probes(..), I.collect(), levels.level_items(..)) feeds it probe names as data -- a fake tests
    folder, a fixture string, an expected 'why' -- and replays no bench. test_inventory's fixture
    "_sim_resolve('engine_seal_move', c)  # bench engine_scripts5 e" made engine_scripts5's readings
    (SET_MISSION_OBJECTIVE_STATUS and two more) 已对拍 with no test replaying it (A round 267). A tool is a name bound
    to an inventory* module (import inventory_levels as levels; inventory = module_from_spec(..)); reading a register
    (inventory.BENCHED_TESTS[..]) is no call. A file that does not parse is kept whole."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text
    tools = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            tools |= {a.asname or a.name for a in node.names if _TOOL.match(a.name)}
        elif isinstance(node, ast.Name) and _TOOL.match(node.id):
            tools.add(node.id)

    def calls_tool(fn):
        return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and isinstance(n.func.value, ast.Name) and n.func.value.id in tools for n in ast.walk(fn))

    fns = (ast.FunctionDef, ast.AsyncFunctionDef)
    defs = [n for n in tree.body if isinstance(n, fns)]
    defs += [m for c in tree.body if isinstance(c, ast.ClassDef) for m in c.body if isinstance(m, fns)]
    cut = set()
    for fn in defs:
        if calls_tool(fn):
            cut.update(range(min([fn.lineno] + [d.lineno for d in fn.decorator_list]) - 1, fn.end_lineno))
    if not cut:
        return text
    return ''.join('\n' if i in cut else x for i, x in enumerate(text.splitlines(keepends=True)))


def tested_probes(tests=TESTS, checks=CHECKS):
    """The bench probes a test holds the simulator to: {'checks/engine_X.py'} for each probe a test file names --
    'engine_X', or a variant 'engine_X_<v>' that is not a probe of its own (the longest probe name it starts with).
    Named, not only quoted as a build: tests replay a probe by its build name (_sim_resolve('engine_seal', ..)), by
    its bench mission (simai.run('aiskirm') -- 'bench engine_aiskirm c' in the test) or by its layout rebuilt
    (engine_mining's), and each cites the probe whose readings it asserts. A probe no test names is a reading only.
    For a probe of several checks (probe_parts) also 'checks/engine_X.py:<key>' for each check the naming test file
    runs (tested_checks); naming the probe alone runs none of its checks' own readings. A test of the inventory tools
    themselves names probes as its data and counts for none (without_tool_tests)."""
    stems = {f[:-3] for f in os.listdir(checks) if f.startswith('engine_') and f.endswith('.py')}
    info = {}
    out = set()
    for f in sorted(os.listdir(tests)):
        if not f.endswith('.py'):
            continue
        text = without_tool_tests(open(os.path.join(tests, f), encoding='utf-8').read())
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


READINGS = CHECKS
LEGACY, CONFORMS = '测试对拍', '读数数据核对相符'


def conformance_probes(folder=None, checks=CHECKS):
    """The bench sources the readings data backs (ADR 0035 5, the definition of 已对拍 from now on): for every reading
    of checks/engine_X.readings.toml with no mismatch mark (the conformance runner, tests/conformance/test_readings.py,
    holds it to the simulator), 'checks/engine_X.py', and for a probe of several checks (probe_parts) also
    'checks/engine_X.py:<key>' of each of its scenes' check. A reading marked mismatch backs nothing."""
    import readings
    folder = READINGS if folder is None else folder
    keys_of, out = {}, set()
    for r in readings.load_all(folder):
        if r['mismatch']:
            continue
        probe = r['bench_file']
        if probe not in keys_of:
            path = os.path.join(checks, f'{probe}.py')
            if not os.path.exists(path):
                raise SystemExit(f'inventory: {probe}.readings.toml sits beside no probe {path}')
            keys_of[probe] = set(probe_checks(open(path, encoding='utf-8').read())[1])
        out.add(f'checks/{probe}.py')
        if len(keys_of[probe]) >= 2:
            out |= {f'checks/{probe}.py:{c}' for _, c, *_ in r['scenes'].values() if c in keys_of[probe]}
    return out


def backing(tests=TESTS, checks=CHECKS, folder=None):
    """{bench source: how it is matched}: the readings data's (CONFORMS) over the frozen legacy route's (LEGACY, a
    test file naming the probe: tested_probes)."""
    out = dict.fromkeys(tested_probes(tests, checks), LEGACY)
    out.update(dict.fromkeys(conformance_probes(folder, checks), CONFORMS))
    return out


def how_matched(tested, run):
    """What backs `run` in `tested` (a set of sources: the legacy route; or backing()'s dict)."""
    return tested.get(run, LEGACY) if isinstance(tested, dict) else LEGACY


def bench_verdict(rx, src, tested):
    """(tested, measured): the first bench source naming `rx` that is matched (backing: the readings data, or the
    frozen legacy tests), and the first naming it at all. Only the first makes an item 已对拍; a reading on the bench
    nothing matches (a probe's docstring, a docs/engine line) leaves it 推断, noted 台上量过."""
    hits = [s for s, text in src if rx.search(text)]
    return next((s for s in hits if s in tested), None), (hits[0] if hits else None)


def benched(items, src=None, tested=None):
    """An implemented item (推断) whose name a bench probe a test runs names becomes 已对拍, citing that probe; one only
    measured on the bench (no test runs that probe, or only a docs/engine line) stays 推断 with 台上量过 noted."""
    src = bench_sources() if src is None else src
    tested = backing() if tested is None else tested
    for it in items:
        if it['state'] not in (GUESSED, TODO):
            continue
        name = it['name'].split('/')[-1].split(':')[-1] if it['part'] == MODULE else it['name'].split(':')[-1]
        rx = re.compile(r'(?<![A-Za-z0-9_])' + re.escape(name) + r'(?![A-Za-z0-9_])')
        run, hit = bench_verdict(rx, src, tested)
        if run and it['state'] == GUESSED:
            it['state'], it['why'] = BENCHED, f'{it["why"]}；台上量过、{how_matched(tested, run)}：{run}'
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
        items += inventory_ai.ai_items(bench_sources(), backing())
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
    items = collect()
    text = render(items)
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

