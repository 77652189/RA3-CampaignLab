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
the only way an item becomes 已对拍 from now on), the probe's source naming the item or the reading declaring it
(its `item` key, declared_items: for a name the source never says), or, frozen, a legacy test that names the probe (tested_probes; the
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
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]
import labpaths  # noqa: E402
import registry  # noqa: E402

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
    (ACTION, 'NAMED_FACE_WAYPOINT'):
        'tests/test_facewp_bench_c.py::test_facewp_named_heading_and_untouched_control_match_bench',
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
    (NUGGET, 'DOTNugget'): 'experimental/cnv/benches/weapon/firing/readings.toml#engine_dot::dot_counts_interval_ticks_for_two_durations_and_observes_first_damage_frame',
    # engine_contained: NONE KindOf filter, cap1/2; selection order GUESSED, radius/projectiles/death unbenched.
    (NUGGET, 'DamageContainedNugget'): 'tests/test_simbench_c.py::test_damage_contained_limits_eligible_passengers_without_damaging_the_others',
    (NUGGET, 'LeechHealthDamageNugget'): 'experimental/cnv/benches/weapon/firing/readings.toml#engine_leechhealth::leech_health_heals_from_damage_and_respects_the_heal_fraction',
    (NUGGET, 'LeechPercentMaxHealthDamageNugget'): 'experimental/cnv/benches/weapon/firing/readings.toml#engine_leechpct::leech_percent_uses_victim_maximum_not_current_health_or_caster_maximum',
    (NUGGET, 'SecondaryDamageNugget'): 'experimental/cnv/benches/weapon/target_effects/readings.toml#engine_secondary::secondary_damage_delivers_one_amount_at_hit_without_damaging_health',
    (NUGGET, 'WeaponOCLNugget'): 'experimental/cnv/benches/weapon/firing/readings.toml#engine_oclone::weapon_ocl_lifetime_damage_reads_the_fire_delay_before_counting_updates',
    (NUGGET, 'ProjectileNugget'): 'tests/test_simbench_c.py::test_projectile_nugget_flight_uses_retail_shell_speed_and_resolved_warhead',
    # Weapon C: replayed bench variants; tests name the actual engine_X build (A line rule).
    (NUGGET, 'AttributeModifierNugget'): 'tests/test_simbench_c.py::test_weaponfx_predictions_and_finite_bursts',
    (NUGGET, 'LineDamageNugget'): 'tests/test_simbench_c.py::test_weaponfx_predictions_and_finite_bursts',
    (NUGGET, 'ParalyzeNugget'): 'tests/test_simbench_c.py::test_weapon_first_hit_is_observed_one_frame_after_the_order_script',
    (NUGGET, 'StripMaxHealthPercentNugget'): 'tests/test_simbench_c.py::test_strip_max_health_percent_uses_maximum_at_full_and_half_health',
    (MODULE, 'Behaviors/OreMinerBehavior'): 'tests/test_simbench.py::test_mining_pays_8_a_frame_and_a_trip_takes_269',
    (MODULE, 'Behaviors/OreNodeBehavior'): 'tests/test_simbench.py::test_mining_a_second_miner_on_one_node_adds_nothing',
    # batch 1 (work/re/l2_scripts1.md, benches/script/control/checks.py#engine_scripts1, bench 11-08)
    (CONDITION, 'HAS_FINISHED_AUDIO'):
        'tests/test_simbench.py::test_audio_a_dubbed_line_is_done_its_length_after_it_is_heard',
    (ACTION, 'ALLOW_DISALLOW_ONE_BUILDING'): 'tests/test_simbench.py::test_a_ban_holds_the_queue_and_does_not_cancel',
    # protocol points (simtech.py, checks/engine_protocol.py, bench 11-08)
    # engine line A round 208: retail-campaign conditions batch 1 (benches/script/control/checks.py#engine_conds team / fight); the
    # TEAM_INSIDE_AREA k other than 0 is benched only as "no Guardian passes 1 / 3 / 7" (air / ships INFERRED)
    # engine line A round 210: batch 2 (benches/script/control/checks.py#engine_conds sight): sight / discovery, the hot spot switch
    # engine line A round 211: retail-campaign actions batch 1 (checks/engine_acts.py flow; NAMED_SET_DISABLED benched
    # for EMP only, the other types INFERRED the same hold)
    # round 212: batch 2 (benches/script/control/checks.py#engine_acts2 seq / more; the ground fire's own damage not benched, none simulated)
    # round 254: checks/engine_reinfat.py go (on a house, at a moved tank's place now, none at a dead one)
    # round 254: benches/economy/construction/checks.py#engine_mining mineturn0 cap / capz (harvest income held; scripts' money not: acts_tel)
    # round 264: benches/ai/production/checks.py#engine_aiupgrade aicupgon:ban (0 holders until the allow; bench rebuys 7 s after the model)
    # round 213: batch 3 (checks/engine_acts3.py tel)
    # round 214: batch 4 (checks/engine_acts4.py acts: spellbook powers, the context attack, buildability)
    # round 215: batch 5 (benches/script/control/checks.py#engine_acts5 acts; PLAYER_TRANSFER_OWNERSHIP_PLAYER changed nothing on the bench:
    # not simulated, stays 未做)
    **{(ACTION, n): 'experimental/cnv/benches/script/control/readings.toml#engine_acts5::acts_v_as_the_bench' for n in (
        'UNIT_SET_MODELCONDITION', 'PLAYER_ALLOW_AI_AUTOACQUIRE', 'TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE',
        'TEAM_GUARD_AREA_FROM_POSITION')},
    # round 216: TEAM_HUNT / NAMED_HUNT (benches/script/control/checks.py#engine_acts6 hunt: an aiTactical-255 owner's crew attack-moves to
    # the nearest enemy; the 240 one's, and NAMED_HUNT on an AI not woken: nothing)
    # round 218 (benches/script/control/checks.py#engine_acts8 hunt): the gate is aiTactical, the target the nearest hostile object (units
    # too), re-picked after each one dies; NAMED_HUNT moves a woken AI's unit neither
    # round 219 (benches/script/control/checks.py#engine_acts9 all): on -- off every team; off -- back onto the map default team, with a
    # hidden member (the AI wake UNIT_AI_TRANSFER_ALL adds is not in it: program, not benched)
    # round 223 (checks/engine_acts11.py all): EVACUATE on a ground transport / a civilian block (out at once), the
    # Apocalypse's harpoon, both mirage fields, the Kirov's afterburners (its LoseHealthUpdate while on)
    # (engine_acts11.py t): the Japanese tower's toggle takes a press only with power; the Sickle's button on it: none
    # round 224 (checks/engine_acts12.py all): the shinobi's smoke bomb and the Tsunami's energized armor (a self
    # AttributeModifier for its Duration), the bear's roar (the bark's EMP), the Sickle's leap to a spot
    # round 226 (checks/engine_acts13.py all): the roar _ON_NAMED (the bear walks up to the target, then roars)
    # round 252 (benches/movement/pathing/checks.py#engine_dam all): the dolphin's jump over a dry dam its swimming twin cannot pass (round
    # 249 had it in NOTES: engine_acts_wet's readout did not tell the jump from swimming)
    # round 222 (benches/economy/construction/checks.py#engine_share all): mining income split among sharing Friends (the earner keeps the rest);
    # NAMED_SELECTED after SELECT_OBJECT (TYPE_SELECTED in NOTES: never true there)
    # round 237 (benches/ui/presentation/checks.py#engine_eyes all): ENEMY_SIGHTED's player = the sighted object's owner, Friend takes the
    # viewer itself; CAMERA_ENTERED_AREA latches (the way there counts); TYPE_SELECTED never, the player's own click
    # and box selection too
    # round 238 (checks/engine_sighted.py all): TYPE_SIGHTED = ENEMY_SIGHTED's query with a type (the viewer itself
    # counts, a script's object list never); NAMED_BUILDING_IS_EMPTY a living garrison with nobody in; BUILT_BY_PLAYER
    # the player owns one, placed ones too (a killed one ~7 s while it lies: not modelled)
    # round 240 (benches/script/control/checks.py#engine_razed all): PLAYER_DESTROYED_N_BUILDINGS_PLAYER false always (Generals' stub, n 0
    # too); SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED counts the player's men inside garrisons, not the buildings
    # round 242 (checks/engine_cast.py all): a cast waits until the first matching reader takes it; IN_AREA by the
    # cast's point; TEAM_CAN_PATH_TO_WAYPOINT every member to the waypoint itself (no snap)
    # round 245 (checks/engine_enter.py all): TEAM_OUTSIDE_AREA_ENTIRELY = not inside (an absent team outside);
    # TEAM_ENTERED_AREA_PARTIALLY one frame a member comes in (a start inside also on leaving); GARRISONNED by type
    # and owner; COMPLETELY_BUILT the player's own, a script's unpacking one at once
    # round 244 (benches/script/control/checks.py#engine_kind all / by): PLAYER_HAS_COMPARISON_UNIT_KIND counts every player's objects;
    # PLAYER_LOST_OBJECT_TYPE one stored count per (player, type string), the first reader takes a drop;
    # NAMED_DESTROYED_BY_OBJECTTYPE false always (four kills, either case)
    # round 217: PLAYER_TRANSFER_OWNERSHIP_PLAYER (benches/script/control/checks.py#engine_acts7 own: the giver's units on no team and its
    # money go to the receiver; ones on a team stay)
    # engine line C round 1: modules whose retail data the simulator already follows and a bench-reading test cites
    (MODULE, 'Behaviors/ProductionUpdate'):
        'tests/test_simbench.py::test_production_pays_as_it_builds_and_comes_out_after_the_door',   # engine_production a-g
    (MODULE, 'Behaviors/StructureUnpackUpdate'): 'tests/test_simbench.py::test_power_back_after_the_plant_unpacks',
    (MODULE, 'Behaviors/SpecialPower'): 'tests/test_simbench.py::test_super_a_scripts_cast_starts_the_retail_reload',
    # engine line C round 3: the crush / slow-death family (benches/body_death/state/checks.py#engine_crush, docs/engine/crush.md, bench 11-06)
    # engine line C round 7: the superweapon benches (engine_super) read health % of 1000-health defenses and the
    # Iron Curtain's expiry frame -- MaxHealth through the damage, the modifier pool through the 23 s it holds
    # engine A rounds 162-173: knock-back curve, landing, hold, gates, fire, the crash's fall (checks/engine_knock_probe,
    # engine_knock_water, engine_crash_fall; the whole list in NOTES' Physics line)
    (MODULE, 'Behaviors/Physics'):
        'tests/test_meta_impact.py::test_physics_p5_a_shot_down_wreck_falls_the_knock_curve_under_its_own_gravity',
    # engine line C round 8: running off the map (Sim.flee_start / flee_due, benches/movement/pathing/checks.py#engine_runoffmap, bench 11-06)
    # engine line C round 9: the mirage aura (Sim.cloaked, simunits.invis_broadcast, checks/engine_stealth.py, bench 11-05)
    # engine line C round 11: weapon choice by ObjectStatus (simunits.weapon_sets, benches/weapon/target_effects/checks.py#engine_weaponset,
    # benches/script/control/checks.py#engine_statusbits, bench 11-09)
    # engine line D: the damage line (simsweep, benches/weapon/target_effects/checks.py#engine_sweep engine_sweepoff a / b / c, bench 11-10)
    (MODULE, 'Behaviors/LinearDamageUpdate'):
        'tests/test_simsweep.py::test_sweep_the_line_walks_out_and_a_stop_does_not_cut_it_at_the_bench_frames',
    (NUGGET, 'ActivateLinearDamageNugget'):
        'tests/test_simsweep.py::test_sweep_a_killed_shooters_line_stops_with_it_and_the_second_ones_rows_are_hit',
    # immortal a / b / c, bench 11-09 (benches/body_death/state/checks.py#engine_immortal): damage floor 1 %, script kill clamped, delete removes
    (MODULE, 'Body/ImmortalBody'):
        'tests/test_simbench_c.py::test_immortal_damage_stops_at_one_hp_kill_is_damage_and_delete_removes',
    # engine_propbody a / b / c, bench 11-10: no health, a kill leaves the street segment, topples the tree / lantern
    # engine_spawn_refill, bench 11-05: a scripted kill sets off the exploding mig's death weapon, the Guardian beside it dies
    (MODULE, 'Behaviors/FireWeaponWhenDead'):
        'tests/test_simbench_c.py::test_fire_weapon_when_dead_a_scripted_kill_blows_the_mig_and_the_guardian_beside_it',
    # topple a / b, bench 11-09: neutral props, delayed removal without DYING; all five readings within one frame
    # topple c, bench 11-10: lantern copies with / without EnableDynamicsCollide crushed and gone at the same frames
    # engine_dynamics a / b, bench 11-10: Hammers with / without BaseVehicle's DynamicsUpdate crush, go round and
    # arrive at the same frames (the Uprising fling props' share is split off: SPLIT_ORPHAN)
    # all four stances the retail scripts set: engine_stance a-f (HOLD_FIRE, bench 11-06) and engine_acquire hold / agg
    # (HOLD_POSITION goes after nothing, AGGRESSIVE never walks back; bench 11-10) -- tests/test_simbench_c.py test_stance_*
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
    # engine line A round 160: engine_wfire all (bench 11-11): Yuriko's blast (radius damage after the nugget's
    # delay), Natasha's pilot snipe (walks till the target's edge is in StartAbilityRange, UnpackTime, the vehicle
    # neutral), the dog's bark (EMP on enemy infantry in the radius); the caster stands Pack / Freeze. Gaps: the
    # blast's MetaImpactNugget push, the ships' / Cryocopter's / superweapons' (WeaponSlot, FaceTarget), the sickle's
    # leap (BezierProjectile), the player's click reload
    # engine line A round 156: engine_toggle a-f, bench 11-11 (Sim.toggle_press): six of our 9 levels' toggles -- a
    # press moves to the next ToggleState (its ObjectStatus / AttributeModifier), the first state's bits from the
    # start, UnpackTime delays, PackTime does not, a DisabledType state takes no press (INFERRED cause). Not modelled:
    # ModelConditions, ArmorSet / LocomotorSet (the VX's / Tengu's jet form), TriggerAttributeModifier
    # round 223: the same bench's a / f are the retail presses' own units (s09's Peacekeepers, a08's Tesla troopers)
    # engine line C round 5: selling (benches/economy/construction/checks.py#engine_sell, docs/engine/sell.md, bench 11-06)
}

# (part, name) -> (state, why): where the name rule above is wrong (a module read under another name ...)
_NOT_IN_SIM = '已核（11-08）：模拟器没有这个效果'
NOTES = {
    (ACTION, 'NAMED_ATTACK_AREA'): (TODO, 'C engine_attackarea:a/b原版无畏舰对北/南电厂区域两局：禁自动索敌，b揭图并交换区域；区域段实际HP均100/100、对照血量与原位码3100，18秒点名阳性靶HP100→75→50→25。读数 checks/engine_attackarea.readings.toml：两局区域窗口阴性相符，18秒后点名命中两条 mismatch（模拟器不打时不开火、本动作未识别；A338 由回放测试迁入）；无命中不能证明区域命令无操作，尚缺区域候选/接受拒绝/实际弹着点，禁自动索敌与建筑目标类别仍未区分，单纯揭图不足以解释。原版a02四舰同区域；两局预算耗完，不实现猜测规则、不晋升；见work/re/c_attackarea_report.md'),
    (ACTION, 'TEAM_SET_HEALTH'): (BENCHED, 'C engine_teamhp:a/b显式目标队守护者/征召兵血量100→25→75及100→75→25，同玩家异队/另一玩家守护者均保持100；四计数器为两成员实际血量百分比、异队血量组合码100100和逻辑帧。读数 checks/engine_teamhp.readings.toml（A331 由逐帧回放测试迁入，每秒一行）；仅当前存活显式队伍成员的百分比设置切片，未来/死亡/缺名成员、AI实例、边界数值和精确派发相位仍gap，其他模板推广INFERRED；见work/re/c_teamhp_report.md'),
    (ACTION, 'NAMED_FACE_WAYPOINT'): (BENCHED, 'C engine_facewp:a及engine_facewpai:b两局；a仅人类玩家存活位7，无team/tstate朝向，b换AI观察宿主，原生hd甲0→180、乙0→117、未操作0，分别朝西/西北路点。tests/test_facewp_bench_c.py按名回放24组原始稳定朝向（全圈1度容差对应hd整数舍入），并断言存活位7；没有用位置不变替代朝向。转身复用既有移动器速率，精确命令/起转相位、移动中打断、缺名/死亡目标和其他模板仍gap或INFERRED；仅存活静止守护者的具名路点朝向切片，见work/re/c_facewp_report.md'),
    (ACTION, 'EXIT_SPECIFIC_BUILDING'): (BENCHED, 'C engine_exitbld:a/b两座公寓各装同玩家两队征召兵，交换具名目标西/东；指定楼两队均退出、另一楼仍驻，重复调用无误伤。进驻位15→12/3、区域码始终22、五兵两楼存活位127；读数 checks/engine_exitbld.readings.toml（A333 由逐帧回放测试迁入）。区域人数包含楼内人员，探针保留原仅室外预测2/20；仅存活公寓具名退出切片，出门位置沿现有INFERRED近似，精确时序、其他容器/模板、缺名/死亡目标、取消进门仍gap；见work/re/c_exitbld_report.md'),
    (ACTION, 'DISABLE_JOYPAD_COMMANDBAR_BUTTON'): (TODO, 'C engine_joypad:a一局17组读数f40..182，原版buttonopenplayertechstore/buttonaiassaultdirective未操作、禁用、分步恢复的脚本阶段0/1/2/3均出现，未操作电厂始终1，末3/1/182。读数 benches/ui/presentation/readings.toml#engine_joypad 只核脚本阶段与对照存活（A338 由存档测试迁入），不冒充完整模型回放或原生输入接受。cnv_result仅脚本阶段/存活/逻辑帧，index仅id/second/note/view，无Joypad元素enabled、输入accepted/rejected字段；台子仅键鼠注入，XInput四槽未连接。PC路径无消费者仅INFERRED，不用鼠标或余额替代阳性，不登记纯表现。一局后缺真实入口/观测而暂停，不耗相同第二局；见work/re/c_joypad_report.md'),
    (ACTION, 'DISABLE_MOUSE_HUD_FIXED_ELEMENT'): (TODO, 'C engine_mousehud:a/b两局SellButton禁用/开场禁用后恢复对照：末f356/f414均存活位5、资金2400；脚本出售位2消失、原生点击位1和未操作位4保留。B原生出售阳性预测4/2800未成立；读数 benches/ui/presentation/readings.toml#engine_mousehud 两局负基线（A338 由回放测试迁入）不能证明UI门。存档画面A按钮灰/B按钮亮且目标被选中；每次bench_click间Esc可能取消卖出模式（INFERRED）。cnv_result只有点击坐标及三计数器，没有SellButton enabled、卖出模式接受或拒绝字段；其他固定元素未量，不据余额或负基线登记纯表现。两局耗完，保持未做；见work/re/c_mousehud_report.md'),
    (ACTION, 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanMCV'): (BENCHED, 'C engine_jpndeploy:a一局：两辆普通日本MCV到东400路径点展开，未下令第三车留家；f256..501目标区建造场/名称存活/原处MCV位码3/7/4。读数 checks/engine_jpndeploy.readings.toml（A334 由逐帧回放测试迁入：动作前及f300之后稳定窗口）；现有order_unpack匹配，无模型或阈值修改。仅普通活宿主空地切片；精确到达/展开时序、地形阻挡、伤害继承、重复/死亡/缺失宿主仍gap，其他宿主推广INFERRED；见work/re/c_jpndeploy_report.md'),
    (ACTION, 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackSovietMCV'): (BENCHED, 'C engine_sovdeploy:a一局：两辆普通苏联MCV到东400路径点展开，未下令第三车留家；f220..468目标区建造场/名称存活/原处MCV位码3/7/4。读数 checks/engine_sovdeploy.readings.toml（A334 由逐帧回放测试迁入：动作前及稳定窗口）；现有order_unpack即可匹配，未调模型或阈值。仅普通活宿主空地切片；精确到达/展开时序、地形阻挡、伤害继承、重复/死亡/缺失宿主仍gap，其他宿主推广INFERRED；见work/re/c_sovdeploy_report.md'),
    (ACTION, 'TEAM_GARRISON_NEAREST_BUILDING'): (BENCHED, 'C engine_teamgarr:a/b两栋空公寓最近选择：建筑摆放顺序不变，仅步兵东移；本队两名征召兵进最近楼，同玩家异队留外，空队伍/重复调用无误伤。最终进驻位/楼归属/存活位分别3/1/31与3/2/31；读数 checks/engine_teamgarr.readings.toml（A333 由逐帧回放测试迁入：动作前及稳定窗口）。仅显式普通步兵与空楼选择切片；逐成员距离及其他模板推广INFERRED，队伍中心/等距/搜索范围、容量/敌属/损坏楼/AI实例和入门时序仍gap；见work/re/c_teamgarr_report.md'),
    (ACTION, 'PLAYER_SELL_EVERYTHING'): (BENCHED, 'C engine_sellall:a/b显式玩家交换对照：所属普通盟军电厂退款400一次、SOLD后消失，三方守护者及异玩家电厂保留；空玩家与重复调用无额外退款。读数 benches/economy/construction/readings.toml#engine_sellall（A334 由逐帧回放测试迁入）。仅显式玩家单电厂切片已量，多建筑枚举和其他模板推广INFERRED；不可售/受损/展开中/队列/驻军及This Player、All Players仍gap；见work/re/c_sellall_report.md'),
    (MODULE, 'AI/AnimalAIUpdate'): (TODO, 'E192 engine_animal_e:a原版女性平民近敌100/仅删模块/远敌700三路，f240四行240/0/7/7，六物体存活但均未离开起点。engine_animalfire_e:a增加敌兵攻击旁电厂，仍240/0/7/7，三路受击前置未成立；两局原逃跑预测FAIL保留。checks/engine_animal_e.readings.toml记实读负基线，开火接受Sim63对台7标mismatch。ra3ext tgt0/inc3/ua0无fleeTrigger/attackAccepted/rejectReason，触发资格未闭合（INFERRED），不实现猜测规则、不登记效果覆盖；同输入暂停，需合法触发或接受证据与新预算，见work/re/e192_animal.md'),
    (ACTION, 'NAMED_SET_SPECIAL_POWER_COUNTDOWN'): (TODO, 'C两局engine_namedcount:a/engine_namedvac:a：三独立玩家宿主，1秒0/2、7秒2/0交换，第三方不操作；铁幕f43..143就绪0、f153..315为7，真空弹f41..148为0、f155..300为3，宿主位均7、零余电位均0。旧零/非零预测被否定；缺真实剩余冷却/READY刷新与宿主初始化同帧字段，秒数与作用域未闭环。读数 checks/engine_namedcount.readings.toml 两条 mismatch（A337 由 strict xfail 回放迁入），未改模型、未晋升；假设表及字段缺口见work/re/c_namedcount_report.md'),
    (ACTION, 'TEAM_EXIT_ALL_BUILDINGS'): (BENCHED, 'C engine_teamexit:a混装建筑/运输车一局：本队征召兵退出公寓和牛蛙，同容器异队保留；队外成员/两宿主均存活，空队伍与重复调用无误伤。f44..74本队驻/异队驻/存活位3/3/127，f82..287为0/3/127；读数 checks/engine_teamexit.readings.toml（A332 由逐帧回放测试迁入，每秒一行）。仅显式存活队伍普通退出切片；精确出门位置/时序、运输抛射、取消进驻中订单、死/缺队伍及AI实例仍gap，其他模板推广INFERRED；见work/re/c_teamexit_report.md'),
    (ACTION, 'PLAYER_KILL'): (BENCHED, 'C engine_playerkill:a一局：目标Soviet_4守护者/电厂死亡，Player_1与Soviet_5同类对照保留；空Soviet_6调用和重复调用未误伤。f45/61/75单位位/建筑位/死亡位7/7/0，f83/152/287为5/5/0；读数 benches/body_death/state/readings.toml#engine_playerkill（A331 由逐帧回放测试迁入，每秒一行）。仅所属普通对象清理切片已对拍；玩家失败/淘汰、保护对象、容器/子体、死亡瞬间和其他模板推广仍gap或INFERRED；见work/re/c_playerkill_report.md'),
    (ACTION, 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT:Command_UnPackJapanEgg'): (BENCHED, 'C engine_eggcmd:a与engine_eggnav:a两局：零售使用的防御/电厂/船厂三种核心，旧通用按钮均留原处；专用防御/船厂按钮到点展开，未下令对照留家。地面f249/393/560建筑位/存活位/原处位4/15/11，水域f247/390/496为2/7/5；读数checks/engine_eggcmd.readings.toml。A290起按类：单位CommandSet里没有的展开/收起按钮都不动（engine_unpack crs：防御蛋按电厂蛋按钮不动），旧通用按钮同此；收起一侧INFERRED；见work/re/c_eggcmd_report.md、work/re/c_eggnav_report.md'),
    (ACTION, 'TEAM_UPGRADE'): (BENCHED, 'C engine_teamup:a真实玩家升级查询+守护者状态位：f150本队/异队/查询0/0/0，f157授予后3/0/3，f248移除一人后2/0/1，f332再授予3/0/3；同玩家异队和敌方异队均无位。读数 checks/engine_teamup.readings.toml（A313 由逐帧回放测试迁入，每秒一行）；仅当前存活显式队伍OBJECT升级派发/消费者切片，j05地图私有升级效果、未来成员、死/缺队伍和AI队伍实例仍gap；其他宿主推广INFERRED；见work/re/c_teamup_report.md'),
    (ACTION, 'UNIT_SET_MODELCONDITION_FOR_DURATION'): (BENCHED, 'C engine_modeldur:a真实UNIT_HAS_MODELCONDITION查询：3/7秒USER_1分别为真46/106逻辑帧，b的1/2秒为真16/31帧，均含到期边界；空白阴性始终无位，永久阳性保持，状态码11→10→8。读数 checks/engine_modeldur.readings.toml（A332 由逐帧回放测试迁入）。仅正持续时间、第四参数1.0、独立USER_1写入/到期切片；其他位推广INFERRED，重复/覆盖、零时长、第四参数其他值及原生生产者均gap；见work/re/c_modeldur_report.md'),
    (ACTION, 'PLAYER_ENABLE_UNIT_CONSTRUCTION'): (BENCHED, 'C两局engine_unitban:a/b具名玩家盟军工程师原生按钮：禁用期可排队但不扣款；恢复后付款/进度续跑，不退款不重置。a第150帧甲2000/乙1603，恢复后第198帧1843/1500/10，末1000/1000/33；b第101至180帧甲保持1800，第195帧1753/1500/10、第285帧1500/1500/11。读数 checks/engine_unitban.readings.toml（A336 由回放测试迁入，资金按帧插值比）；第二笔队列付款提前10帧记为mismatch。仅此玩家/工程师切片已量，其他模板门禁INFERRED，UI拒绝、升级、建筑、AI及This Player/All Players范围仍gap；见work/re/c_unitban_report.md'),
    (ACTION, 'PLAYER_DISABLE_BASE_CONSTRUCTION'): (BENCHED, 'A269 aibgate:a（B的aiskirm图，s1盟军AI 10秒醒、50000）：开局禁用，醒后到第1054帧钱50000、建筑数1，不下任何建筑单；70秒恢复后f1054起付款、f1208第二栋（对照aiskirm d醒后11秒第二栋）。模拟simai.build拒结构单：f1065/f1215。读数 benches/script/control/readings.toml#engine_basegate（A335 由回放测试迁入）。C的engine_baseban：日本核心（UNIT_BUILD）不受此门；A的engine_basegate:a：脚本按盟军建造厂电厂按钮两边都不扣钱，玩家建造厂队列量不到（未模拟）。This Player/All Players范围仍gap'),
    (ACTION, 'PLAYER_ENABLE_BASE_CONSTRUCTION'): (BENCHED, 'A269 aibgate:a：禁用的AI在70秒恢复后立即开始下建筑单，f1054付款、f1208第二栋，节奏同刚醒（模拟f1065/f1215）。读数 benches/script/control/readings.toml#engine_basegate（A335 由回放测试迁入）；范围同DISABLE（具名AI玩家；玩家建造厂队列、This Player/All Players未量）'),
    (ACTION, 'SKIRMISH_AI_START'): (BENCHED, 'A270 B的aiskirm图去脚本库四局（s1盟军AI，10秒给50000）：只START（建造厂留在teamSoviet_1）、只MAKE_BASE、只SKIRMISH_AI_TRANSFER_ALL（交队不唤醒）都整局50000/建筑1；UNIT_AI_TRANSFER(建造厂)+START（原版a07写法）f169前付款、f290-f312第二栋（模拟f158/f308）。程序：START=TRANSFER_ALL的唤醒半步。模拟器：MAKE_BASE只对脚本库玩家代唤醒，simai只用交给AI的建造厂。读数 benches/script/control/readings.toml#engine_aistart（A335 由回放测试迁入）'),
    (ACTION, 'PLAYER_TOGGLE_SKIRMISH_AI'): (BENCHED, 'A270 aipause:a（aiskirm带库，25秒关、85秒开）：关后在造的付清到48300（f457）就冻结到f1262，暂停中造好的第3栋恢复后f1280才放下，f1300起又花钱。程序：写AI脑暂停字节，每帧更新整帧跳过。模拟器Sim.ai_paused：Brain.tick跳过思考、yard_due暂停时不放建筑。读数 benches/script/control/readings.toml#engine_aistart（A335 由回放测试迁入）；具名玩家，玩家掩码范围gap'),
    (MODULE, 'Behaviors/StructurePlacementBehavior'): (TODO, 'E183 structpon:a/structpoff:a原版矿场/仅删模块两局，前方120放电厂；总数及前方区域始终0，资金从10000采矿增长到11750/12000，未到9200付费哨兵。原禁建/允许预测FAIL保留，未建立合法排队/放置接受事实；benches/economy/construction/readings.toml#engine_structureplace_e只记零电厂负基线，不登记模块效果已对拍。queueAccepted/queueReady/placementAccepted/rejectReason缺失，同输入暂停；几何消费/旋转/边缘仍gap，见work/re/e183_structureplace.md'),
    (ACTION, 'REDALERT_DISABLE_THREAT_LEVEL_BONUS'): (TODO, 'C两局engine_threatbonus:a/b：A仅到第三批损失，不能用捕获秒作任务秒；B改逻辑帧闸门并交换禁用方，实测双方均第2893帧升二级（含禁用方），模型均5400。experimental/cnv/benches/economy/construction/readings.toml#engine_threatbonus具名阶段读数回放通过，协议升级读数strict xfail保留。未证明动作关闭协议经验倍率，不写无操作实现；缺同帧玩家threat/等级/倍率及单位经验奖励消费，整项未晋升。见work/re/c_threatbonus_report.md'),
    (MODULE, 'Behaviors/SpiderHoleUpdate'): (TODO, 'E178 spideron_e:a/spideroff_e:a原版反坦克步兵/仅删模块两局PASS，f45合法入洞、f120隔离者出洞；f90/f180具名状态及存活编码两侧均1515/1508，施放事件均3。checks/engine_spider_e.readings.toml状态相符，施放事件标mismatch（Sim为0）。手动切换由ToggleStatus提供，不据相同状态晋升扫描模块；同点载具实际距离/扫描接受与内部阶段未测，自动出洞假设未成立，_Ambush/精确扫描时钟/移动载具/攻击碾压仍gap，不拟合规则、不改分母；见work/re/e178_spider.md'),
    (MODULE, 'Behaviors/PrematureDischargeSpecialPower'): (TODO, 'E177 dischargeon_e:a/dischargeoff_e:a两局原版波能坦克/仅删模块对照，f45攻击、f75按键；f210冻结原版210/76/0/1、删模块210/0/109/0，首伤提前33脚本帧、施放事件1/0。删模块原施放1预测FAIL保留。benches/weapon/firing/readings.toml#engine_discharge_e两条mismatch：Sim两侧首伤47，且原版漏施放；武器PER_SHOT前摇及提前放电派发未闭合，不硬调模型、不登记已对拍。内部充能、伤害缩放、重复/取消、其他宿主与绝对帧均gap；见work/re/e177_discharge.md'),
    (MODULE, 'Behaviors/PowerUpgrade'): (TODO, 'E175 engine_powerupgrade_e:a/b两局：a冻结330/11/10/11，b精确供电始终100/100/500/350，授予期升级持有位均0。高级原版500来自战役覆盖，删模块克隆为SDK350，不能拿基线差归因于模块。TriggeredBy的Upgrade_PowerPlantTurbine在SDK Upgrade.xml无定义；合法授予/接受拒因未闭合，倾向未解析引用（INFERRED），两局后暂停同输入。benches/economy/construction/readings.toml#engine_powerupgrade_e：b普通两座和删模块高级350相符，原版高级500与持有位0标mismatch（Sim 350、授予期持有），不登记已对拍；原预测保留，购买升级、加电/撤销和其他升级门均gap；见work/re/e175_powerupgrade.md'),
    (MODULE, 'Behaviors/SlaughterHordeContain'): (TODO, 'E291 engine_slaughter_y:y 用 W 局摆位、去掉船厂；f621 双侧各 1 架且成对删目标门为 7，f643 起原版/删模块区域余量为 0/1。模拟器未出机，读数保留 mismatch。实际入舱、子机归属及停车阶段仍缺观测；见 work/re/e291_slaughter_return.md。旧无出机基线见 work/re/e170_slaughter.md'),
    (MODULE, 'Behaviors/AssistedPlacementBehavior'): (TODO, 'E169 assistpon:a / assistpoff:a原版与删模块两局均资金8000、矿场总数0、提示位数量0、采样完成0；红色预览未落地，原吸附预测保留。当前计数器无放置接受/拒因字段，不能归因于模块；同输入暂停。benches/economy/construction/readings.toml#engine_assistplace_e记零矿场负基线，资金8000一条标mismatch（Sim未消费侧栏排队/放置点击，10000）；吸附、朝向、迷雾资格和精确距离均gap，不登记已对拍；见work/re/e169_assistplace.md；11-23 b 任务脚本定镜头后点击被接受（E169 失败是 bench_camera 偏约100）：同一点击，on 矿场落在提示位20内、转向矿点，off 落在点击处、默认朝向——台上见到吸附；模拟器不回放台子点击，读数都是 mismatch，不登记已对拍'),
    (MODULE, 'Behaviors/CaptureSpecialAbilityUpdate'): (NA, '没人触发（A403）：它的特殊能力只收 KindOf CAPTURABLE，'
        '原版只有 CaptureFlag / ControlPoint，原版 27 关和我们 9 关都没摆；谭雅没有占领键。台上原版 / 只删本模块的工程师'
        '按占领键或进驻占建筑一样（checks/engine_capture.readings.toml）。E151 对旗子下令没换主，没追'),
    (MODULE, 'Behaviors/EmotionTrackerUpdate'): (NA, '没人触发（A404，读程序）：每帧只挑被强制过的情绪，不自发；'
        '宿主只挂 CHEER 两个模板，强制来源只有 PLAYER/TEAM/UNIT_FORCE_EMOTION、IDLE_ALL_UNITS、TEAM_PANIC 和'
        ' BezierProjectile 的落地情绪，原版 27 关和我们 9 关都没用、原版数据都没填。脚本直接设 EMOTION_CELEBRATING 是模型状态，不经本模块'),
    (MODULE, 'Behaviors/AttributeCrateCollide'): (BENCHED, '例子密件箱1/2是起义时刻数据（RA3流和27关都没有），按RA3写法克隆（无ApplyToSelf/KillOnPickup）。engine_secretfile_e:a 脚本移动不捡；b 右键点箱：箱消失、捡箱人戴上修正器USER_1到底，同箱的HealCrateCollide不回血（一次拾取一个效果）。engine_secretfile_s:b 两模块换序后回血、不戴修正器：一次拾取跑XML里写在前的那个。只核对无Duration的ModelConditionsSet，其他修正项gap。'),
    (MODULE, 'Behaviors/HealCrateCollide'): (BENCHED, 'E283 原版医疗箱右键拾取与脚本移动对照，回放末读数14/1/100/50与15/0/50/50。只核对玩家拾取、箱消失和回血筛选。碰撞形状、精确帧和距离口径 INFERRED；其他拾取资格、AI、音效和自定义筛选仍 gap。'),
    (NUGGET, 'ReportWeaponFiredStatNugget'): (NA, '纯统计（C线工单允许排除）：只记录玩家武器开火次数；原版两份空配置附于SovietVacuumBomb / ParticleCannonWeapon，伤害与创建物体由独立WeaponOCLNugget负责。保留用量2，不登记已对拍；未上台，不模拟战后统计；证据见work/re/c_reportstat_report.md'),
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
    (MODULE, 'Behaviors/RepairUpdate'): (BENCHED, 'repairai a/repairq a/repairt a/repairzero a按名重放：开局足额资金、默认1000HP/800造价电厂初始50%/25%/75%血约10HP/s修满、实扣100/225/25，费用按缺血比例平方；零资金无经济不修；tests/test_simrepair_ai.py。只支持已测配置，完整配置门禁保留；gap：玩家入口、废墟维修、受伤停修、其他初始血量/造价/速率及资金耗尽未测；AI启动相位INFERRED；按总控11-11三切片收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母'),
    (MODULE, 'Behaviors/EngineerContain:通用三国'): (BENCHED, '已测范围：engine_engineer a/b/c/d普通进入，三国工程师中立/敌方半血电厂占领并消耗、友军半血修满并消耗、满血拒入且存活；按完整配置匹配登记63用量/87模板；gap：精确进入帧仍INFERRED；日本单人ALLIES和桥配置保留在未对拍残余行，不借本组登记'),
    (MODULE, 'Behaviors/EngineerContain:三国ALLIES'): (BENCHED, '已测范围：engine_engineer a/e/f普通进入，三国工程师友军半血防御修满并消耗、满血及敌方拒入且存活，目标归属不变；按完整配置匹配登记6用量/7模板；gap：精确进入帧仍INFERRED；日本单人ALLIES和桥配置保留在未对拍残余行，不借本组登记'),
    (MODULE, 'Behaviors/EngineerContain'): (GUESSED, '总控11-11授权工程师组收尾、不再上台；已测通用三国63用量及三国ALLIES6用量分别登记；gap：日本单人ALLIES型TH_TombBuilding02为1用量/1模板，筛选与维修未对拍；间接可达桥头堡为0用量/10模板，桥修复未对拍；本行共1用量/11模板。ReplaceWith和ObjectStatusToSet无原版显式声明；精确进入帧仍INFERRED，不登记整模块已对拍（tests/test_simengineer.py、tests/test_inventory_contain.py、tests/test_inventory_engineer.py）'),
    (MODULE, 'Behaviors/LevelUpUpgrade'): (BENCHED, '已测范围：engine_levelup a创建升级触发升阶、重复持有不升级；b移除创建升级保留等级，老兵创建升级移除重给可再次升阶，英雄位0/0/0/1→0/0/1/1→0/1/1/1；c独立精英/英雄创建升级各自移除重给两次，首次仍0/0/0/1、第二次0/1/1/1；engine_leveldamage a等级DAMAGE_MULT125保持到精英/英雄，单发血量47/34/34/17；engine_levelhealth a满血升级HEALTH_MULT125保持到英雄，100脚本伤害同帧冻结80/80/84/84；b残血升精英保留血量比例50/80/50/20，再扣100血为30/64/34/4，当前和最大血量均乘1.25，simlevel及test_simbench_c重放；engine_levelrange a原版幻影普通炮125、英雄炮150叠加RANGE125%为187.5，220距离仅英雄命中、260距离均未命中，四路100/10100/100/10100→100/10017/100/10100，离位异常均0；engine_levelrate a幻影普通/直接英雄武器/创建英雄/创建精英三段周期25/25/20/25帧，最终血量84/80/68/80，ROF不增加单发伤害；仅此离散单发炮配置已量，射速分段取整/其他武器仍未对拍；engine_levelshroud a原版幻影基础揭雾500、创建英雄SHROUD_CLEARING125%预测625，580/750距离普通/英雄四路1/1/1/1→1/111/1/101，近点始终可见且无离位；仅此模板配置已量，精确边界未对拍；engine_levelvision a原版幻影普通/创建英雄对小包围体工程师240/310距离ENEMY_SIGHTED四路11/11/11/11→0/0/0/0→0/101/0/100，近点在正式窗口前删除且无离位，支持VISION125按1.25倍率为250的预测；仅脚本范围查询已量，精确边界/自动索敌未对拍；gap：英雄自动索敌、精确射程/揭雾/视野边界、射速分段取整/其他武器、其余模板/等级属性、经验成长、额外上限及Permanent=true未对拍；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证；这些分支与已测效果共用模板，不能按SPLIT_STILL互斥拆分用量'),
    (NUGGET, 'FireOnObjectsNugget'): (TODO, '未实现：子武器派发条件与空间锚点尚未解释；失败诊断不作为已对拍依据'),
    (NUGGET, 'GrapplingHookNugget'): (BENCHED, '仅原版天启鱼叉钩车辆：开关后 NO_ATTACK 挡着不钩、放开即自己索敌钩住拉死（engine_grapple a / b）；钩建筑 / TIME_BOMB、弹跳、放钩再钩未测，命中那 1 点伤害模拟器不显示（INFERRED）'),
    (MODULE, 'Behaviors/LiftObjectUpdate'): (GUESSED, '部分：显式TimeIncrement/MaxTimeLifted的开火者举升表；台上只有7s/18s状态快照（benches/weapon/impact/readings.toml#engine_lift），逐帧计时来自模块证据、未上台量；垂直运动/死亡/飞机/落地清位仍gap'),
    (NUGGET, 'ActivateLiftObjectNugget'): (BENCHED, '直接单发：开火者举升表 trunc(TimeIncrement×15) 逐发累加、续期封顶 MaxTimeLifted，释放不清 LIFTED，SoftLanding 举高 ≤ 28 落地清位（engine_lift a / landing / probe）；原版地面 3 个宿主的筛选（engine_liftground）；打飞机走坠机分支：开火者的 AirplaneCrashWeapon 由飞机打自己、不置 LIFTED（engine_liftair，死亡帧 INFERRED 取命中帧）。gap：弹体 / 多发、28–40 的清位边界、落地武器伤害；乘员炮塔一个槽里 SECONDARY 对空线不选（选武器归 weaponset，mismatch 读数）'),
    (NUGGET, 'AttachNugget'): (GUESSED, '部分：engine_attach a实测直接单发、父子状态、随父移动及目标状态/类型拒绝；仅零半径简单模块，原版复杂筛选/维修/吸血/解除/弹体未接通；engine_attachc4 a原版谭雅/删Nugget及父EXPLOSIVES_ATTACHED对照为11/10024/10030/10028，正常原版附着后父死子活，禁用父仍有MARCH_OF_DEATH但无ATTACHED；原版写法已切片:谭雅C4（A372），见work/re/c_attachc4_report.md；engine_attachmine a原生磁力地雷本体原位创建/删Nugget×普通/SPECIAL_ARMOR_ACTIVE为111/110/111/110，保留者均附着、删除者均不附着；tests/test_attach_mine.py具名回放阴性，b三个禁用位均读到仍附着为111/110/7111/7110，两原生回放strict xfail；上游弹体/OCL、复杂筛选及生命周期仍gap，见work/re/c_attachmine_report.md；不登记整项已对拍'),
    (NUGGET, 'SpecialPowerNugget:干扰消费者'): (GUESSED, '1用量，暂停额外SPN消费：engine_spnscr c原版四路删减、受害者真实开火、靶子封闭暴露窗，早HP100/100/90/90、晚HP90/90/80/80，打包301000090/301000090/300999080/300999080实机PASS；tests/test_special_power_nugget.py具名回放。停火差异由AttributeModifier决定，保留/删SPN相等不能证明额外消费者no-op；b仅NAMED_STOP仍续射，原预测strict xfail保留。两局耗完，缺SpecialPower开始/结束及命令消费观测，不晋升完整消费者，见work/re/c_spnscr_active_report.md'),
    (NUGGET, 'SpecialPowerNugget:附着dummy消费者'): (TODO, '1用量，暂停：JapanScoutInfantryAttachWeaponWarhead引用OBJECT dummy模板及原版宿主；缺独立派发/附着读数，不能按Dummy名字推定无操作；需Attach模块观测，work/re/c_spnclosure_report.md'),
    (MODULE, 'Behaviors/OCLSpecialPower'): (BENCHED, '总控第四切片按已测边界收尾：tests/test_simocl.py具名回放engine_oclcurtain/engine_oclnone/engine_oclwrong a，铁幕宿主匹配模块才保护并记事件，删除/改绑模块无保护/事件；engine_oclempty a空声明无保护且事件1；engine_oclcopy a完整原版载荷改名仍保护100/100且事件1；engine_oclzero a仅外层Count=0无保护且事件1。只闭合铁幕派发和零数量不保护边界，未测生成数量/通用生成；其他非零数量/载荷/超武、位置/过滤、按钮/冷却仍gap，继承、等价空声明及格式等价INFERRED，不表示全模块全字段验证；见 work/re/e_ocl_e65.md'),
    (MODULE, 'Behaviors/RadarBehavior'): (GUESSED, 'E158-E162原版盟军雷达宿主（原生PlayerSpellBook雷达已去掉）：删宿主、只删电厂、两同类宿主先后删、受伤致死、脚本双向换主。台上小地图有无只从HUD截图读，模拟器不模拟雷达也没有计数器能读，所以读数（benches/ui/presentation/readings.toml#engine_radar）只核对前提（存活、PLAYER_HAS_POWER、归属）、不挂本项；HUD结果写在读数bench里。精确注销/换主帧、建造中、工程师占领、其他宿主仍gap；见work/re/e158_radar.md等'),
    # review 1121nn: the readings stay (checks/engine_activate / _hitreaction_e), the main behavior not modelled
    (MODULE, 'Behaviors/HitReactionBehavior'): (GUESSED, '维和举盾已对拍：E172受击HIT_REACTION位、engine_hitreaction_r受击转向（原版94/删模块83，checks/engine_hitreaction_e.readings.toml）；征召兵BITTEN后反应30帧并取消走路已对拍（A396/E280，checks/engine_dogbite.readings.toml），早期快照仍有时差；征召兵无视idle的转向、JapanEmperor待量，idle判定和刷新时序INFERRED'),
    (NUGGET, 'TintObjectsNugget'): (NA, '纯表现：Color及Pre/Sustained/PostColorTime、Frequency/Amplitude仅控制染色动画；engine_tint pair实测2/90/2/90，独立DamageNugget解释全部伤害，test_simbench_c重放；不声称像素已验证'),
    (NUGGET, 'ParalyzeNugget'): (GUESSED, '部分：engine_emp phase实测PASS16051/31066/61096、hit1；engine_empfire a实测PASS901090/901100/901080/901090，失能窗口按令不开火、到期后新令恢复；仅无筛选EMP，其他类型/筛选/装填相位未验证'),
    (NUGGET, 'StripMaxHealthPercentNugget'): (GUESSED, '部分：engine_strip exact实测PASS95/45/74，4%满血/半血与25%满血按最大血量扣减；筛选、护甲倍率、无标记伤害形式未验证，最大血量不变仍推断'),
    # Weapon round 1: scope limitations retained; explicit replay register above sets the bench state.
    (NUGGET, 'AttributeModifierNugget'): (GUESSED, '部分：engine_weaponfx attribute实测涂靶ARMOR150%；engine_spnret a实测单个PLAYER升级Required/Forbidden读取施法者玩家，普通/高科技ARMOR150/200%、晚段74/69%血，tests/test_special_power_nugget.py回放；数据1.1s且9s前到期，到期帧未测；OBJECT升级/owner/筛选/范围形式仍未验证'),
    (NUGGET, 'LineDamageNugget'): (GUESSED, '部分：engine_weaponfx line探针；实测PASS90/90/90/100验证动态线长及穿透，圆形边界GUESSED，筛选与静态线未模拟'),
    (MODULE, 'Body/ActiveBody'): (GUESSED, 'simunits.stats 读 MaxHealth（只有生命值；受伤状态、回血等另算）'),
    (MODULE, 'Body/ManagedImmortalBody'): (BENCHED, '仅 HB_Bridge_02 的 GateHouse1：代理受伤后两座桥头堡均从 100% 到 1%，修好的回到 100%，未修对照留在 1%。直接伤害、致死保护、其他桥型和桥段未对拍'),
    (MODULE, 'Body/ManagerBody'): (BENCHED, '已测范围：engine_managerbody a/b原版HB_Bridge_02，270/700长度整体代理脚本伤害200后均80%、致命量后1%且存活，tests/test_simmanagerbody.py按名重放；gap：有效HP取CenterPiece及内部1%下限映射仍INFERRED，内部最大血量/伤害转发/显示下限待核；HV_Bridge_01等其他模板/配置、桥段共享血量/损毁/维修未对拍；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母'),
    (MODULE, 'Behaviors/BridgeBuilder'): (BENCHED, '已测范围：engine_bridgebuilder:a已量HB_Bridge_02长度270/700，EndCap/EndCap2/CenterPiece/CenterPieceB/GateHouse数量1/1/1/0/2及1/1/2/2/2；engine_bridgebuilder_b:b已量原版HB桥首16+Bridge1a桥尾32混合构型，两长度HB数量不变、五类Bridge1物件均0；tests/test_simbridgebuilder.py按名核计数模型与读数编码，simunits仅有限数量模型；gap：HV_Bridge_01等其他桥型/配置/长度、桥段物体生成/位置、断桥通行未建模（桥头堡生成、血量随代理、工程师修桥见engine_bridgefix）；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母'),
    (MODULE, 'AI/AIUpdate'): (GUESSED, 'Sim.fight / 移动（单位 AI 的状态机细项按引擎 B 的 AI 清单推进）'),
    (MODULE, 'AI/JetAIUpdate'): (BENCHED, '已测范围：engine_jet:a/b原版维和轰炸机静止正东起步，距离1200/600，首次入框97/47，框内1且血100%；simjet按逐帧位置实现首步2.7（机制INFERRED）、每帧+0.8至12；tests/test_simjet.py按名回放两种时钟均97/47，并核启动位置和入框112/62帧；未新增上台；gap：其他配置/机型、重复命令/转弯、MinSpeed、起飞高度/盘旋/降落、机场/跑道/停车位、返场补弹/耗尽伤害及攻击状态，配置与动作门禁保留；按总控11-11收尾决定登记模块已对拍，不表示这些gap已验证，不拆分分母'),
    # the 26 the bench measured but the name rule called 未做 (checked 11-08 against sim.py / simunits.py)
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
    (MODULE, 'Behaviors/SubStructureStorageBehavior'): (NA, '没人触发：原版只在三国 MCV（及海军继承型）挂一个空的，'
        'SDK 注释说它存收起的建造厂的子结构升级；能造子结构的 SubStructureBuild 在原版建造厂里整块注释掉'
        '（有效配置 0 个，test_retailmodules 守着），没东西可存。台上原版 / 只删本模块两臂两次收起展开一样'
        '（checks/engine_substorage.readings.toml）'),
    (MODULE, 'Behaviors/SubStructureBehavior'): (TODO, 'E189 engine_substructure_e:a一局PASS，独立摆放的原版维修台/仅删模块对照，f59血量100/100、f120脚本伤害后80/80、f240删除无绑定建造场后80/80且场存活位0；experimental/cnv/checks/engine_substructure_e.readings.toml按名字回放最终四行240/80/80/0通过，无模型改动。只测独立摆放基线，不推断父子联动或模块无效；SDK有效XML无SubStructureBuild，现四行缺parentId/bindAccepted/forwardedDamage。父体绑定、伤害传递、清理及其他模板仍gap，同输入暂停，需合法绑定入口及新预算；见work/re/e189_substructure.md'),
    (MODULE, 'Behaviors/WallBuilderBehavior'): (GUESSED, '部分：engine_wallinit:a/b预摆与脚本具名生成均为10/11/10，仅StartInSecondaryModel初始化默认WALL_SEGMENT；其他生成入口INFERRED，建墙/连接/段数上限/生死联动及自定义配置仍gap；见 benches/map/fixtures/readings.toml#engine_wallinit、work/re/e_wallbuilder_e58.md'),
    (MODULE, 'Behaviors/GateOpenAndCloseBehavior'): (TODO, 'E190原版门/删模块初始化台被SDK Behaviors拒绝该模块且缺模型资源；原生地图摆放同样强制编译失败。改用engine_gate_e:a运行时同动作创建两门与电厂哨兵，一局PASS，f180=180/0/0/1（完成/Romania门/Sanitarium门/哨兵存活）。读数在benches/map/fixtures/readings.toml#engine_gate_e：帧数与哨兵相符，模拟器两门均1对台0记mismatch（两门模板不在SageXML物体索引里）；不登记模块效果覆盖。缺templateResolved/createAccepted/rejectReason，倾向模板在当前运行环境不可用（INFERRED）；开闭/通行/复位均gap，同输入暂停，重开需可创建宿主及合法开关入口，见work/re/e190_gate.md'),
    (MODULE, 'Behaviors/SlavedUpdate'): (GUESSED, '模拟器记录生成归属并通知生成模块子体死亡；E294 原版吸取无人机在 LeashRange 300/3000 两组都到达终点，回放均留在起点（checks/engine_leechdrone.readings.toml），跟随派发及牵引边界仍 gap，见 work/re/e294_slaved_follow.md'),
    (MODULE, 'Behaviors/AttachUpdate'): (GUESSED, '部分：engine_attach a验证瞬移/跟随/父子状态；engine_attach_parent a验证简单模块脚本杀父后子活/清理链接，engine_attach_nocoll n验证AttachedObjectStatus不给NO_COLLISIONS；子死、单端删除已量（engine_attach_child/_delete、parent_delete）；原版模块死亡前无稳定链接，不推广死亡规则；维修/吸血/解除/自主扫描仍gap'),
    (NUGGET, 'ActivateLaserNugget'): (NA, '纯表现：Lifetime/LaserId/HitGroundFX/OverShootDistance驱动LaserState/LaserDraw；engine_laser pair实测2/90/2/90，无附加伤害或首发延迟，test_simbench_c重放'),
    (MODULE, 'Behaviors/LaserState'): (NA, '纯表现：LaserId关联光束，起止粒子/骨骼/EndOffset与ObjectStatusValidation只控制光束表现；LaserStateModule.xsd无伤害字段；engine_laser pair匹配LaserDraw/State 201，伤害由独立DamageNugget给出，test_simbench_c重放2/90/2/90'),
    (MODULE, 'Behaviors/ConvergingLaserState'): (NA, '纯表现：LaserState 加四束汇聚，原版两处（雅典娜、锤子坦克吸来的雅典娜炮）'
                                                     '都没填 SweepWeapon / SweepFXList；E211 engine_convlaser_e/s/o '
                                                     '三种摆法原版/删模块首伤同为 41 帧，1% 血差跟着先放的那臂走'
                                                     '（benches/weapon/firing/readings.toml#engine_cosmetic_e）'),
    (MODULE, 'Behaviors/SweepingLaserState'): (NA, '纯表现：LaserState 加光束末端扫动（Radius / SweepFXList / '
                                                   'SweepFXTimeout），能伤人的只有 SweepWeapon，原版唯一一处（恐怖机器人，'
                                                   'LaserId 0）没填；FX_SOV_ElectroRay 只有声音和粒子。麻痹由同一武器的 '
                                                   'ParalyzeNugget + AttributeModifierNugget 给出。同族 LaserState、'
                                                   'ConvergingLaserState 上台都无附加伤害或延迟（engine_laser、E211），未单独上台'),
    (MODULE, 'Behaviors/LUAEventList'): (NA, '纯表现：EventListName连接原版ScriptEvents.xml与Scripts.lua；RA3声明可达的事件处理函数只调用模型部件显隐（及tostring），含继承；未定义的AlliedInfantryFightingFunctions无可达处理函数；C&C3升级/状态函数不可达。tests/test_inventory_lua.py静态核对游戏包与SDK声明，非上台对拍'),
    # batch 1 (work/re/l2_scripts1.md, benches/script/control/checks.py#engine_scripts1, bench 11-08)
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
    (MODULE, 'Behaviors/AttributeModifierPoolUpdate'): (GUESSED, 'simmodifier.modify：属性修正挂在这个池里，到期规则'
                                                                 '（到期帧 >= 即失效、再挂覆盖不叠加）读自程序，'
                                                                 'work/re/l2_ability.md 第 51 轮'),
    (ACTION, 'PLAYER_ALLOWED_TOBE_COOPAI'): (NA, 'A219 读程序：只写 AI 脑的"可当合作 AI"位；读它的只有合作 AI 的'
                                              '界面 / 语音、玩家挑合作伙伴、关掉时取消合作 AI 正执行的玩家指令；'
                                              '模拟器的玩家没有给盟友下令的命令，脚本读不到它（同下一条）'),
    (ACTION, 'SET_COOP_AI_COMMAND_UI_ENABLED'): (NA,'纯界面：开关玩家给盟友 AI 下令的按钮；模拟器的玩家没有给盟友'
                                                     '下令的命令，开关无从起作用（以后加了这个命令再算）'),
    # engine A round 107: the freeze; what the front modules are, read in the SDK data
    (MODULE, 'Behaviors/SecondaryDamageTracker'): (GUESSED, 'Damage.chill（ALIGN freeze）：冷冻光束的冷冻值累计、每秒'
                                                            '消散、按生命值分档减速、满档冻住（CryoBeamFrozenArmor '
                                                            '90000%，一碰就碎）；规则读自 SDK 数据，程序和台上都没对'),
    (NUGGET, 'SecondaryDamageNugget'): (GUESSED, 'simunits._weapons 读 Amount（不要升级的那条）→ sdps，Damage.chill'),
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


def nugget_form_slice(ntype, forms, at_self=False):
    """Partition weapons, never occurrences. Every effective form must fit the measured slice. at_self: the weapon's
    DamageDealtAtSelfPosition (retailmodules.weapon_at_self).

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
        if all(set(n.attrib) <= allowed | {'ShockWaveArc', 'ForbiddenTargetObjectStatus', 'ForbiddenTargetModelCondition'}
               and 'ShockWaveArc' in n.attrib and n.get('ForbiddenTargetObjectStatus') == 'LEECHED_TARGET_ACTIVE'
               and set(n.get('ForbiddenTargetModelCondition', '').split()) == {
                   'STUNNED', 'STUNNED_STANDING_UP', 'STUNNED_FLAILING'}
               and len(n) == 1 and not list(n[0]) and not (n[0].text or '').strip()
               and n[0].tag.rsplit('}', 1)[-1] == 'SpecialObjectFilter'
               and dict(n[0].attrib, Relationship='ENEMIES') == dict(Rule='ANY', Relationship='ENEMIES', Include='INFANTRY')
               for n in forms):
            return ':鬼王瞬发弧'
        if not at_self and all(
                not list(n) and set(n.attrib) <= allowed | {
                    'ShockWaveArc', 'ForbiddenTargetObjectStatus', 'ForbiddenTargetModelCondition'}
                and 'ShockWaveArc' in n.attrib and n.get('ForbiddenTargetObjectStatus') == 'LEECHED_TARGET_ACTIVE'
                and set(n.get('ForbiddenTargetModelCondition', '').split()) == {
                    'STUNNED', 'STUNNED_STANDING_UP', 'STUNNED_FLAILING'} for n in forms):
            return ':弹体爆心弧'
        if all(set(n.attrib) <= allowed | {'InvertShockWave'} and n.get('InvertShockWave') == 'true' and len(n) == 1
               and n[0].tag.rsplit('}', 1)[-1] == 'SpecialObjectFilter' and n[0].attrib == dict(
                   Rule='ALL', Exclude='AIRCRAFT INFANTRY', StatusBitFlagsExclude='UNDER_IRON_CURTAIN')
               and [(c.tag.rsplit('}', 1)[-1], (c.text or '').strip()) for c in n[0]] == [
                   ('IncludeThing', 'SovietScoutVehicle'), ('IncludeThing', 'SovietHeavyAntiVehicleInfantry')]
               for n in forms):
            return ':磁暴反向筛选'
        if all(not list(n) and set(n.attrib) <= allowed | {'ShockWaveArc', 'ForbiddenTargetModelCondition'}
               and n.get('ForbiddenTargetModelCondition') == 'STUNNED_FLAILING' and n.get('ShockWaveArc') == '5d'
               for n in forms):
            return ':散弹自身弧'
        if all(not list(n) and set(n.attrib) <= allowed
               and {'ShockWaveAmount', 'ShockWaveRadius'} <= set(n.attrib) for n in forms):
            return ':普通无延迟显式Z' if all('ShockWaveZMult' in n.attrib for n in forms) else ':省略Z默认值'
        if all(set(n.attrib) <= allowed | {'ShockwaveDelaySeconds', 'ShockWaveClearRadius'}
               and n.get('ShockWaveClearRadius', 'false') == 'false' and len(n) == 1 and not list(n[0])
               and n[0].tag.rsplit('}', 1)[-1] == 'SpecialObjectFilter' and not (n[0].text or '').strip()
               and n[0].attrib == dict(Rule='NONE', Include='INFANTRY', StatusBitFlagsExclude='NO_COLLISIONS')
               for n in forms):
            return ':步兵筛选延迟'
        if all(not list(n) and set(n.attrib) <= allowed | {'ShockwaveDelaySeconds'}
               and {'ShockWaveAmount', 'ShockWaveRadius', 'ShockwaveDelaySeconds'} <= set(n.attrib) for n in forms):
            return ':自身延迟' if at_self else ':普通延迟'
    elif ntype == 'AttachNugget':
        for name, head, filt, things in (
                (':恐怖机器人近战', dict(AttachModuleId='ModuleTag_AttachUpdate', ForbiddenTargetObjectStatus=(
                    'AIRBORNE_TARGET VEHICLE_ATTACHED UNDERGOING_REPAIR SPECIAL_ARMOR_ACTIVE UNDER_IRON_CURTAIN NOT_IN_WORLD')),
                 dict(Rule='ANY', Include='VEHICLE', Exclude='INFANTRY', Relationship='ENEMIES NEUTRAL'),
                 ['SovietScoutVehicle']),
                (':谭雅C4', dict(id='ModuleTag_AttachNugget', AttachModuleId='ModuleTag_AttachUpdate', Radius='1'),
                 dict(Rule='ANY', Include='STRUCTURE VEHICLE VALID_TARGET_FOR_C4', Exclude='WALL_PIECE',
                      StatusBitFlagsExclude='AIRBORNE_TARGET NOT_IN_WORLD UNDER_IRON_CURTAIN'),
                 ['AlliedWallPiece', 'SovietWallPiece', 'JapanWallPiece'])):
            if all(n.attrib == head and len(n) == 1 and n[0].tag.rsplit('}', 1)[-1] == 'SpecialObjectFilter'
                   and n[0].attrib == filt and [(c.tag.rsplit('}', 1)[-1], (c.text or '').strip(), c.attrib, len(c))
                                                for c in n[0]] == [('ExcludeThing', t, {}, 0) for t in things]
                   for n in forms):
                return name
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
    'MetaImpactNugget:散弹自身弧': '仅瞬发DamageDealtAtSelfPosition散弹（维和/AAAVT1/ABD）：圆心=射手脚下，Arc沿射手→目标；engine_knock_self a 原样(0,25)(0,38)冲、39°侧邻与60外不冲，只删Arc侧邻也冲，三人初速度与模拟器公式同（tests/modules/test_nugget_meta_impact_self.py）；engine_knock_self b 原位计数读数（原样man离位/侧邻不动，只删Arc两人都离位）。半角arc/2、射手自身不受（自身或敌我未分）、禁FLAILING=飞行中跳过均INFERRED；AAAVT1继承后另加半径100一条（游戏是否两条都冲未量，模拟器只取自己那条）；弹体爆心的Arc轴未量（gap）',
    'MetaImpactNugget:普通延迟': '仅非DamageDealtAtSelfPosition的普通延迟写法（机甲王Katana）：碰撞帧c入队，D=ceil(float32秒×15)（1.9s→29、1.2s→18），c+D+1帧在碰撞爆心派发默认Physics冲击；首格出现在到期帧、下一帧停一格、到期+14落地（engine_knock_delay a原始轨迹）。engine_knock_delay b原位帧数读数：冲击帧−碰撞帧=30/19。台上用弹体碰撞；Katana是瞬发近战，瞬发的爆心按目标半身高取（INFERRED，未上台）；停一格的原因、目标中途死亡/移动、延迟期间新碰撞叠加未量（gap）',
    'MetaImpactNugget:自身延迟': '仅DamageDealtAtSelfPosition的普通延迟写法（机甲王Omega）：开火帧入队，c+D+1帧在开火那刻射手脚下派发（射手自己不受）；engine_knock_selfd a 散弹去Arc加1.2s两路，命中帧92、ra3ext冲击全在111帧，射手命中后被传送150外的一路爆心仍是原位、计数与不动的一路相同。Omega原本由特殊能力（WeaponFireSpecialAbilityUpdate）开火，那条链、它的DamageSpeed 800伤害和射手死于延迟期间未量（gap）；逐帧离位晚2帧归A363散弹轨迹（mismatch读数）',
    'MetaImpactNugget:步兵筛选延迟': '仅百合子PsyonicBlast写法（延迟1s、Z8.5、ClearRadius false=默认、Rule NONE Include INFANTRY+排除NO_COLLISIONS）：engine_knock_psy a 弹体爆心，步兵邻人冲、零抗性锤子复制不冲，去筛选两者都冲（NONE+列表=只要列表）。原版是瞬发能力开火（engine_knock_probe retail 瞬发不冲），那条开火链、敌我关系、ClearRadius true 未量（gap）',
    'MetaImpactNugget:鬼王瞬发弧': '仅鬼王近战（DamageDealtAtSelfPosition、Arc135）/冲撞（JapanAntiVehicleVehicleTech3、EmperorMecha：无 at-self、Arc180、TaperOff1）的瞬发写法（LEECHED、三种眩晕、Rule ANY Include INFANTRY±ENEMIES）：engine_knock_oni a 两道冲击都在射手脚下（无at-self的瞬发也是），135d 时偏 82° 的人也冲（半角=Arc，不是Arc/2）；去冲撞的Damage500用近战武器做底。冲撞由特殊能力冲锋触发那条链、三种眩晕=飞行或倒地起身（INFERRED，如镰刀）、吸血状态原生生命周期、EmperorMecha的ENEMIES（按镰刀的关系筛选）未单独上台（gap）',
    'MetaImpactNugget:磁暴反向筛选': '仅磁暴奇点写法（InvertShockWave、Z0、Rule ALL Exclude AIRCRAFT INFANTRY、IncludeThing 恐怖机器人/磁暴步兵、排除UNDER_IRON_CURTAIN）在弹体爆心：engine_knock_filter c 原位计数，原文一路普通锤子和磁暴兵被吸走、步兵和铁幕锤子不动，去筛选一路四个都被吸走（a/b 的逐速度与落点回放 tests/test_meta_filter.py、反向 tests/test_meta_invert.py）。原版由磁暴卫星特殊能力（MagneticSatelliteEffect）开火那条链、飞机（两局都无冲击，拒绝原因未知）、铁幕原生生命周期未量（gap）',
    'MetaImpactNugget:弹体爆心弧':'仅神风弹头写法（Arc5、半径20、LEECHED、三种眩晕、无筛选）在弹体爆心：engine_knock_kami a V4 带原文，爆心的人和东12的邻人都不冲，只删Arc两人都冲（engine_knock_arc b 同：爆心、东20、后20都不冲）。弧轴未知，"冲不到地面上的人"是INFERRED；神风机本身俯冲撞击那条链、俯冲方向上的人未量（gap）',
    'MetaImpactNugget:省略Z默认值':'仅普通无延迟弹头省略ShockWaveZMult→SDK默认1及默认Physics轨迹；engine_knock_z a高度93邻人14帧落(2420,3740)、目标99%/邻人100%。碰撞时刻/爆心为台上输入；直击噪声方向/网格/选人仍INFERRED，完整曲线弹/坡地/筛选未对拍',
    'AttachNugget:恐怖机器人近战': '仅原版恐怖机器人近战附着武器（AttachNugget筛选含Relationship/ExcludeThing）+原版完整AttachUpdate块（engine/modules/attach.py TERROR整块比对）；engine_attachterror a 14s 127/127/3/3、20s 127007/127000/3006/3002：附着后子ATTACHED/ENCLOSED/UNATTACKABLE、父VEHICLE_ATTACHED/BOOBY_TRAPPED，脚本杀父子随死，删Nugget不附着。派发时Range10不当门槛（台上在武器射程25外沿派发也附着；更近处是否卡未量，INFERRED）；子随父死按"父最后伤害者不是子"判（自己杀死父时不死INFERRED）；弹跳、无人驾驶脱离、父禁用状态致死、修理中拒绝未量（gap）',
    'AttachNugget:谭雅C4': '仅原版谭雅C4附着武器（Radius 1、StatusBitFlagsExclude并入禁用状态）+原版完整AttachUpdate块（engine/modules/attach.py C4整块比对）；engine_attachc4 a 11/10024/10030/10028、b（删ForbiddenParentStatus）11/10024/15/10028：附着后父MARCH_OF_DEATH、引爆炸死父、子活着脱离；父有EXPLOSIVES_ATTACHED时照样置MARCH_OF_DEATH但不链接；删Nugget不附着。地面车辆父 + 建筑父（engine_a1gate h：s1 的宫墙、电厂各被炸、谭雅留在旁边，乙末两位 66）；引爆武器的AttributeModifierNugget（父EXPLOSIVES_ATTACHED、谭雅EXPLOSIVES_DETONATING 20s）不建（台上父命中帧即死，从未读到该位）；Range 5、DETACH_WHEN_IDLE、铁幕/空中拒绝未量（gap）',
    'SpecialPowerNugget:变装消费者': '仅原版间谍/迅雷运输车的变装消费者（engine/modules/disguise.py）：命中按目标筛选（间谍INFANTRY、排除恐怖机器人；运输车VEHICLE），删SPN或删SpecialDisguiseUpdate不变装（engine_spndisguise/spnspyx/spnspyex/spntrans/spntrfilter 1111/1110/1110/1111）；Friend/Neutral同样变装（engine_spnrelations）；UnpackTime后才显示DISGUISED（engine_spntrans）；被动索敌按变装身份（engine_spncancel）；有载撤离乘员出舱即清变装、之后才挨打，空载撤离不清（engine_spncargo/spncancel；按出舱而非按键清，INFERRED）。gap：外观（OpacityTarget、显示成命中物模板）、点名攻击、探测器、间谍身份的其他用处、攻击或装载是否清变装',
    'InformTargetNugget:默认系数目标通知':'仅默认Min=.85/Max=1.15的目标通知→来弹表/矿车预计伤害开甲；engine_inform_probe a/off录入302、hit377、exp404、删除389，347帧入窗。engine_inform_expiry a/b只改预报速度及截止系数：两路截止313/304与303/317，物理清除336/312与336/320；tests/test_inform_ai.py具名入表回放绿，自主清理四strict xfail，不能以到期即时删除或共享周期拟合，见work/re/c_inform_expiry_report.md。另有合成engine_inform_radius a/b具名回放（tests/test_inform_radius.py）：Radius200通知80近邻、不通知320远邻，默认0仅主目标，删除通知全无；近邻复制主目标来弹信息。此合成切片不增加原版用量，边界/高度/异型护甲/复杂筛选仍INFERRED或gap，见work/re/c_inform_radius_report.md。历史/海啸/忍者及完整AI调度不在本登记范围，完整脚本仍xfail',
    'InformTargetNugget:Max1.6目标通知': '仅Min=.85/Max=1.6目标通知→来弹表；engine_inform_max a单变量对照录入302、hit377不变、exp444（默认404）、受伤389删除，矿车提前开甲。自然过期清理边界/半径/历史/海啸/忍者/完整AI调度未对拍，完整脚本仍xfail',
}


def nugget_items():
    import retailmodules
    import simcoverage
    code = simcoverage.sim_code()
    items = []
    for ntype, v in retailmodules.weapon_census().items():
        if ntype in ('MetaImpactNugget', 'InformTargetNugget', 'SpecialPowerNugget', 'AttachNugget'):
            groups = collections.defaultdict(list)
            st = retailmodules._load()
            for k, (name, _, _) in st['weapons'].items():
                forms = [n for n in retailmodules.effective_weapon_forms(k, st) if retailmodules._tag(n) == ntype]
                if forms:
                    groups[nugget_form_slice(ntype, forms, retailmodules.weapon_at_self(k, st))].append(name)
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


def probe_parts(name, text, source=None):
    """[(source, text)] of one probe. A probe with one check is one source, 'checks/engine_X.py'. A probe with several
    (engine_aiskirm's thirty) is split: each check's own function (its docstring holds that check's readings) is
    'checks/engine_X.py:<key>', the rest (module docstring, shared helpers, constants) 'checks/engine_X.py'. A word only
    a check's own function names was read by that check: only a test that runs that check makes it 已对拍
    (tested_probes), not one that runs another check of the same probe."""
    src = source or f'checks/{name}.py'
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


def probe_sources(checks=None):
    """Logical bench -> (citation path, check source), without importing any bench."""
    sources = {p.stem: (f'checks/{p.name}', p.read_text(encoding='utf-8'))
               for p in Path(checks or CHECKS).glob('*.py')}
    if checks is None:
        for path in sorted(registry.BENCH_ROOT.glob('*/*/checks.py')):
            rel = path.relative_to(HERE).as_posix()
            for name, body in registry.bench_sources(path).items():
                if name in sources:
                    previous = sources[name][0]
                    # A former check module may still house shared scene and script helpers.
                    if not previous.startswith('checks/') or registry.declared(Path(HERE) / previous) & set(registry.NAMES):
                        raise registry.RegistryError(f'{rel}: duplicate check source for {name}')
                sources[name] = (f'{rel}#{name}', body)
    return dict(sorted(sources.items()))


def bench_sources():
    """[(source, text)] where bench measurements live: the engine probes (checks/engine_*.py, run with cnv_check on the
    bench, their readings in the docstrings; a probe of several checks split by check, probe_parts) and the lines of
    docs/engine/*.md marked measured (**测**), the generated PAGES left out. In both a line NOT_MEASURED marks is left out (engine_aiupgrade's
    'Retail tech entries have MinTime >=180s, outside the observation' made MinTime 已对拍)."""
    need(CHECKS, 'the bench checks')
    need(ENGINE_DOCS, 'the engine docs')
    out = []
    for name, (source, body) in probe_sources().items():
        if name.startswith('engine_'):
            out += [(s, measured(t)) for s, t in probe_parts(name, body, source)]
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


def tested_probes(tests=TESTS, checks=None):
    """The bench probes a test holds the simulator to: {'checks/engine_X.py'} for each probe a test file names --
    'engine_X', or a variant 'engine_X_<v>' that is not a probe of its own (the longest probe name it starts with).
    Named, not only quoted as a build: tests replay a probe by its build name (_sim_resolve('engine_seal', ..)), by
    its bench mission (simai_run.run('aiskirm') -- 'bench engine_aiskirm c' in the test) or by its layout rebuilt
    (engine_mining's), and each cites the probe whose readings it asserts. A probe no test names is a reading only.
    For a probe of several checks (probe_parts) also 'checks/engine_X.py:<key>' for each check the naming test file
    runs (tested_checks); naming the probe alone runs none of its checks' own readings. A test of the inventory tools
    themselves names probes as its data and counts for none (without_tool_tests)."""
    sources = {n: src for n, src in probe_sources(checks).items() if n.startswith('engine_')}
    info = {}
    out = set()
    for f in sorted(Path(tests).rglob('test_*.py')):
        text = without_tool_tests(f.read_text(encoding='utf-8'))
        named = {}
        for name in PROBE_NAME.findall(text):
            full = name
            while name not in sources and '_' in name[len('engine_'):]:
                name = name.rsplit('_', 1)[0]
            if name in sources:
                out.add(sources[name][0])
                named.setdefault(name, set()).add(full)
        for name, variants in named.items():
            source, body = sources[name]
            if name not in info:
                info[name] = probe_checks(body)
            missions, keys = info[name]
            if len(keys) >= 2:
                out |= {f'{source}:{k}' for k in tested_checks(text, name, variants, missions, set(keys))}
    return out


_WORD_LIST = r'(?:\.py)?(?:\s*[:.]\s*|\s+)(\w+(?:\s*[/,]\s*\w+)*)'
_PARAMETRIZE = re.compile(r'parametrize\((.*?)\)\s*\n\s*(?:@|def )', re.S)


def tested_checks(text, probe, variants, missions, keys):
    """The checks of `probe` (keys) that the test file `text` runs: a key written after the probe's or one of its
    missions' name ('bench engine_aiskirm d / f', 'engine_engineer:c', 'checks/engine_aiskirm.py y'), quoted as the
    argument after it (_sim_run('engine_scripts7', 'idle'), simai_run.run('aiskirmlow', 'd')), a build variant
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


def conformance_probes(folder=None, checks=None):
    """The bench sources the readings data backs (ADR 0035 5, the definition of 已对拍 from now on): for every reading
    of checks/engine_X.readings.toml with no mismatch mark (the conformance runner, tests/conformance/test_readings.py,
    holds it to the simulator), 'checks/engine_X.py', and for a probe of several checks (probe_parts) also
    'checks/engine_X.py:<key>' of each of its scenes' check. A reading marked mismatch backs nothing."""
    import readings
    sources = probe_sources(checks)
    keys_of, out = {}, set()
    for r in readings.load_all(folder):
        if r['mismatch']:
            continue
        probe = r['bench_file']
        if probe not in sources:
            raise SystemExit(f'inventory: readings of {probe} sit beside no probe')
        source, body = sources[probe]
        if probe not in keys_of:
            keys_of[probe] = set(probe_checks(body)[1])
        out.add(source)
        if len(keys_of[probe]) >= 2:
            out |= {f'{source}:{c}' for _, c, *_ in r['scenes'].values() if c in keys_of[probe]}
    return out


def declared_items(folder=None, held_only=True):
    """{(part, name): 'checks/engine_X.readings.toml::<id>'}: the items readings declare they prove (their `item` key,
    readings.py), the first such reading by file and order; held_only: only readings with no mismatch mark (the
    conformance runner holds them to the simulator) -- what makes an item 已对拍 when the bench's source never names
    it. held_only=False: every declaration (the guard checks each names an item that exists)."""
    import readings
    out = {}
    for path, r in readings.located(folder):
        if held_only and r['mismatch']:
            continue
        p = Path(path)
        source = (f'{p.relative_to(HERE).as_posix()}#{r["bench_file"]}' if p.name == 'readings.toml'
                  else f'checks/{p.name}')
        for k in r['items']:
            out.setdefault(k, f'{source}::{r["id"].split("[")[0]}')
    return out


def _register_scope(it, notes=None):
    """What a register entry's why keeps after its citation: a nugget's scope, or a BENCHED NOTES entry's text."""
    notes = NOTES if notes is None else notes
    k = (it['part'], it['name'])
    if k in notes and notes[k][0] == BENCHED:
        return notes[k][1]
    return NUGGET_SCOPES.get(it['name']) if it['part'] == NUGGET else None


def apply_declared(items, declared=None, notes=None):
    """Items a held reading declares (declared_items) become 已对拍, citing it -- as a BENCHED_TESTS entry would.
    notes: the part's NOTES dict keyed as (part, name) (inventory_ai's are keyed by name: none is used for AI)."""
    declared = declared_items() if declared is None else declared
    for it in items:
        k = (it['part'], it['name'])
        if k in declared:
            scope = _register_scope(it, notes)
            it['state'], it['why'] = BENCHED, declared[k] + ('；' + scope if scope else '')
    return items


def backing(tests=TESTS, checks=None, folder=None):
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


def apply_registers(items, declared=None):
    benched(items)
    declared = declared_items() if declared is None else declared
    for it in items:
        if it.pop('present', False) and it['state'] == GUESSED:     # presentation, has code (often sim.SHOWN), not
            it['state'], it['why'] = NA, f'纯表现（名字规则）；{it["why"]}'     # measured: a measured one stays 已对拍
        k = (it['part'], it['name'])
        if k in NOTES:
            it['state'], it['why'] = NOTES[k]
        cite = BENCHED_TESTS.get(k) or declared.get(k)      # a legacy register entry, or a reading's own `item`
        if cite:
            scope = _register_scope(it)
            it['state'], it['why'] = BENCHED, cite + ('；' + scope if scope else '')
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
        items += apply_declared(inventory_ai.ai_items(bench_sources(), backing()), notes={})
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

