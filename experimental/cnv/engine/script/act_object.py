"""L6 script actions on objects (ADR 0029, docs/engine/sim-layers.md; L2): delete, kill, damage and health, status
bits and model conditions, panel flags, buildability, selling, garrisons and the construction switches.

Each action is `fn(sim, name, a, script)`, moved verbatim out of Sim.act's chain; simact.act looks them up in ACTIONS."""
import math

import engine.data.units as simunits
import engine.objects.locomotion as simlocomotion
import engine.objects.modifier as simmodifier
import engine.orders.order as simorder
from engine.kernel import interfaces, module
from engine.script.common import refined
from engine.objects.status import ACTED_STATUS, AI_ONLY_STATUS
from engine.world.handle import GAP_ACTION, inside


def team_delete(sim, name, a, script):
    # (team) INFERRED (Generals doTeamDelete / doTeamKill): every living member removed / killed, as
    # NAMED_DELETE / NAMED_KILL one by one; TEAM_DELETE_LIVING as TEAM_DELETE. engine_scripts8 team asks
    for b in sim.members(a[0]):
        if name == 'TEAM_KILL':
            b.set_last_damage(None)
        (sim.world.kill if name == 'TEAM_KILL' else sim.world.remove)(b, '脚本' if name == 'TEAM_KILL' else '脚本删掉')


def team_change_object_status(sim, name, a, script):
    # (team, status, on) INFERRED: the unit version on every member
    for b in sim.members(a[0]):
        sim.ra3_only.add('UNIT_CHANGE_OBJECT_STATUS')       # as Sim.act noted the unit action it runs
        unit_change_object_status(sim, 'UNIT_CHANGE_OBJECT_STATUS', [b.name, *a[1:]], script, unit=b)


def techtree_modify_buildability_object(sim, name, a, script):
    # (template, BuildableStatus 0 YES 1 IGNORE_PREREQUISITES 2 NO 3 ONLY_BY_AI): one table for every player
    # (d115 25); read by can_build
    sim.buildable[str(a[0]).lower()] = int(a[1])
    sim.change()


def named_set_disabled(sim, name, a, script):
    # (object, type, on) d115 20: on = disabled for ever by that type, off = that type cleared. Every type
    # holds a unit as EMP does (emp_disabled; benched for EMP only, the others INFERRED)
    b = sim.body(a[0])
    if b:
        kinds = sim.script_disabled.setdefault(b.serial, set())
        (kinds.add if int(a[2]) else kinds.discard)(str(a[1]))
        if not kinds:
            sim.script_disabled.pop(b.serial)


def unit_kill_all_in_area(sim, name, a, script):
    # (player, area) d115 27: every object of the player's inside the area killed (death type 6, INFERRED a
    # plain death); a drone is passed by (engine_spawn), modelled as no other kind is
    if a[1] in sim.areas:
        for b in [b for b in sim.living() if b.owner == a[0] and inside(sim.areas[a[1]], b.x, b.y)
                  and 'DRONE' not in b.kinds and a[0] != '']:
            b.set_last_damage(None)
            sim.world.kill(b, '脚本')


def team_garrison_team_instantly(sim, name, a, script):
    # (passengers, containers[, c]) d115 12: each passenger not inside yet into the next container of B that
    # may hold it, one cursor going round B (shared between passengers: they are dealt out, not one filled
    # first). The room is not asked: bench 11-13 engine_acts_more 驻 767 (six into the five-place Bullfrog, as
    # TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY; d115's c true for retail's two-argument form) -> 363 (seven
    # dealt 4 + 3, the first Bullfrog 4: its kill took 4)
    boxes = [g for g in sim.members(a[1]) if sim.garrison.box(g) is not None]
    free = not (len(a) > 2 and not int(a[2]))
    k = 0
    for m in sim.members(a[0]):
        if m.serial in sim.garrison.where or not boxes:
            continue
        for _ in range(len(boxes)):
            g = boxes[k % len(boxes)]
            k += 1
            if g is m:
                continue
            sp = sim.garrison.box(g)
            if (free or len(sim.garrison.held(g)) < sp['max']) and \
                    sim.garrison.put(m, g, script=True):
                simorder.stand(m)
                break


def select_object(sim, name, a, script):
    # (player, object): bench 11-14 engine_share all -- replaces the
    sim.selected = a[1]                # selection, an enemy's object too; DESELECT changed nothing there


def sell_object(sim, name, a, script):
    # (object) engine_sell: simbody.Life.sell, refused while unpacking
    b = sim.body(a[0])
    sim._life().sell(sim, b, sim.garrison, sim.world.modify, sim.wallet.credit)


def player_sell_everything(sim, name, a, script):
    # engine_sellall: owned plant sells/refunds once; Guardians and other owners stay.
    # Other sellable structures use existing sell() rules (INFERRED); see work/re/c_sellall_report.md.
    for b in list(sim.living()):
        if b.owner == a[0]:
            sim._life().sell(sim, b, sim.garrison, sim.world.modify, sim.wallet.credit)


def named_damage(sim, name, a, script):
    # (object, amount) health points off, no armour; engine_sell b / e
    b = sim.body(a[0])                  # the Indestructible panel flag does not stop it (engine_scripts7 panel)
    if b and b.alive:
        b.set_last_damage(None)
        b.damage(float(a[1]))
        if b.hp <= 0.0:
            sim.world.kill(b, '脚本伤害')
            b.find(interfaces.Body).set_bits_read_until(sim.frame_now())    # step B4a: the Body module's
        else:                           # under REALLYDAMAGED: out in this frame (engine_garrison 伤争敌 1230)
            sim.garrison.hurt(b)


def named_kill(sim, name, a, script):
    b = sim.body(a[0])
    if b:
        if name == 'NAMED_KILL':
            b.set_last_damage(None)   # the game's kill damage comes from nobody (INVALID_ID)
        (sim.world.remove if name == 'NAMED_DELETE' else sim.world.kill)(b, '脚本' if name == 'NAMED_KILL' else '脚本删掉')


def player_kill(sim, name, a, script):
    # engine_playerkill:a: owned Guardian + plant die; other owners survive, empty/repeated calls harmless.
    # Only the object cleanup slice measured; player defeat state and protected bodies remain gaps.
    # Ordinary lethal dispatch for other templates is INFERRED (work/re/c_playerkill_report.md). engine_pkallied:a
    # (review xx #2): an Allied plant so cleared leaves no Peacekeeper (its list REQUIRES_LIVE_PLAYER); NAMED_KILL's does
    for b in list(sim.living()):
        if b.owner == a[0]:
            b.set_last_damage(None)
            sim.world.kill(b, '玩家脚本清理', cause=module.PLAYER_GONE)


def unit_set_health(sim, name, a, script):
    b = sim.body(a[0])
    if b and b.alive:
        b.health = float(a[1])


def team_set_health(sim, name, a, script):
    # Current living explicit-team members; engine_teamhp a/b.
    # Other templates/AI instances and boundary values remain INFERRED;
    # see work/re/c_teamhp_report.md for measured scope.
    for b in sim.members(a[0]):
        b.health = float(a[1])


def named_set_max_health(sim, name, a, script):
    # (name, INT max, full too): retail Iga's trucks by difficulty. RA3 (work/re/ra3-script-reference.md): setMaxHealth(max,
    # SAME_CURRENTHEALTH) -- the hit points stay (clamped to a lower max), then 100 % if `full`. Bench 11-10
    # engine_maxhealth mh: 480 -> 240 hp, max 960 full 0: 25 %; full 1: 100 %; max 240 full 0, 120 off: 50 %
    b = sim.body(a[0])
    if b and b.alive:
        top = float(a[1])
        b.set_hp(top if a[2] else min(b.hp, top), top)     # told: a module waiting on the health (a raised maximum too)


def unit_set_modelcondition(sim, name, a, script):
    # (unit, n, on): ModelState USER_<n> set / cleared, held till cleared. Bench 11-13 engine_acts_v mc: 1 -> USER_1,
    # 2 -> USER_2, 3 -> USER_3 (a08's saluting conscripts: USER_2 is the conscript's STATE_Saluting), 0 clears;
    # the team action every member alike (engine_modeldur:u)
    for b in [sim.body(a[0])] if name.startswith('UNIT') else sim.members(a[0]):
        if not sim.present(b):
            continue
        if int(a[2]):
            sim.set_model_condition(b, f'USER_{int(a[1])}')
        else:
            b.model_conditions.pop(f'USER_{int(a[1])}', None)


def unit_set_modelcondition_for_duration(sim, name, a, script):
    condition = a[1][2] if isinstance(a[1], tuple) else a[1]
    if float(a[2]) <= 0 or float(a[3]) != 1.:
        sim.gap(GAP_ACTION, name, '仅已量正持续时间和第四参数1.0；见work/re/c_modeldur_report.md')
        return
    # engine_modeldur:a: 3/7 seconds query true for 46/106 frames (the boundary included); :t the team action
    # on every member alike. Other producers untouched.
    for b in [sim.body(a[0])] if name.startswith('UNIT') else sim.members(a[0]):
        if sim.present(b):
            b.model_conditions[condition] = sim.frame_now() + math.ceil(float(a[2]) * simunits.LIFE_FPS) + 1


def unit_set_modelcondition_generic(sim, name, a, script):
    b = sim.body(a[0])
    condition = a[1][2] if isinstance(a[1], tuple) else a[1]
    if sim.present(b):
        if name == 'UNIT_CLEAR_MODELCONDITION':
            b.model_conditions.pop(condition, None)
        else:
            sim.set_model_condition(b, condition, float(a[2]))


def unit_change_object_status(sim, name, a, script, unit=None):
    # `unit`: the member a team action picked (the object itself, not a reference of its name: 11-19 sweep)
    b = unit if unit is not None else sim.body(a[0])
    st = a[1][2] if isinstance(a[1], tuple) else a[1]
    if b and st != 'NEXT_MOVE_IS_REVERSE':  # A310 engine_hull pace: set at s0, a script never reads it (INFERRED: not kept)
        (b.script_status.add if a[2] else b.script_status.discard)(st)
        simmodifier.modify(sim, b)
    if st not in ACTED_STATUS | AI_ONLY_STATUS:
        sim.gap(GAP_ACTION, refined(name, a), f'状态位 {st} 只记下来；模拟器只认 {"、".join(sorted(ACTED_STATUS))}')


def unit_affect_object_panel_flags(sim, name, a, script):
    # (unit or team, flag, on). Indestructible: the body takes no damage at all (Generals ScriptActions
    # changeObjectPanelFlagForSingleObject -> ActiveBody::setIndestructible; attemptDamage returns at once;
    # not read in RA3). Bench 2026-11-09 engine_scripts7 panel: NAMED_DAMAGE and NAMED_KILL go through it (UNIT
    # and TEAM alike); a weapon's damage not measured -- still refused here (INFERRED).
    # Retail s01 keeps Natasha alive so ('Emergency - Natasha Indestructible'); the other
    # flags (Selectable, Enabled, AI Recruitable ...) are only noted
    flag = str(a[1][2] if isinstance(a[1], tuple) else a[1])
    if flag.lower() == 'indestructible':
        bodies = [sim.body(a[0])] if name.startswith('UNIT') else sim.members(a[0])
        for b in bodies:
            if b:
                b.find(interfaces.Body).set_indestructible(a[2])
    else:
        sim.gap(GAP_ACTION, f'{name}:{flag}', f'面板标志 {flag} 没模拟（只认 Indestructible）')


def named_garrison_specific_building(sim, name, a, script):
    b, g = sim.body(a[0]), sim.body(a[1])
    if b and g and 'INFILTRATOR' in b.kinds and sim.infiltrators.spec(g) is not None:
        sim.infiltrators.send(b, g)
    elif b and g and simunits.engineer_contain(g.template, sim.own) is not None:
        simorder.order_capture(sim, simorder.Peers(sim), b, g)         # the building looked at above, not its name read again (same-name sweep)
    elif b and g and sim.garrison.spec(g) is not None:      # walks to it, in if it may (simgarrison; INFERRED)
        sim.garrison.send(b, g)
    elif b and g:
        # a transport: walked to only. The team's version goes in (bench engine_acts_tel); this one too in the
        # game, but s01's intro then needs CONTAINER_OCCUPIED, the eject and the flyby's relation, not modelled
        # (Natasha would ride a Bullfrog the simulator lets die) -- round 213 handoff. To where that one stands
        # (11-19 same-name sweep: not the name read again as a point -- a waypoint or the body table's thing)
        simlocomotion.go_to(sim, b, (g.x, g.y))


def team_garrison_nearest_building(sim, name, a, script):
    # engine_teamgarr:a/b: only this crew, nearest of two empty apartments.
    # Per-member distance, candidate eligibility beyond this contrast,
    # capacity and exact walk/entry timing are INFERRED, not benched.
    # See work/re/c_teamgarr_report.md; use the existing walk-in consumer.
    for b in sim.members(a[0]):
        places = sim.garrison.places(b, False)
        if places:
            g = min(places, key=lambda g: math.hypot(g.x-b.x, g.y-b.y))
            sim.garrison.send(b, g)


def team_garrison_specific_building(sim, name, a, script):
    # (team, building or transport) each member walks there and goes in, the room asked (bench 11-13
    # engine_acts_tel: five of six into the five-place Bullfrog, one a second; unlike _INSTANTLY)
    g = sim.body(a[1])
    for b in sim.members(a[0]):
        if g and sim.garrison.box(g) is not None:
            sim.garrison.send(b, g)


def named_garrison_specific_building_instantly(sim, name, a, script):
    # (unit, building) engine_garrison: no
    sim.garrison.put(sim.body(a[0]), sim.body(a[1]), script=True)    # relation, no room (garrison.md 1)


def team_garrison_specific_building_instantly(sim, name, a, script):
    # (team, building or transport) each member as
    g = sim.body(a[1])                                         # the named one (bench 11-10 engine_transport
    for b in sim.members(a[0]):                                # load: six into the five-place Bullfrog)
        sim.garrison.put(b, g, script=True)


def named_exit_building(sim, name, a, script):
    # (unit) engine_garrison base: out where the building stands
    sim.garrison.out(sim.body(a[0]))


def exit_specific_building(sim, name, a, script):
    # engine_exitbld:a/b: all occupants of the named apartment, across
    # crews; the other apartment stays occupied. Repeating is harmless.
    # Other container types and exact exit positions/timing remain gaps;
    # the existing garrison exit position is INFERRED.
    g = sim.body(a[0])
    if g and g.alive:
        sim.garrison.empty(g)


def team_exit_all_buildings(sim, name, a, script):
    # engine_teamexit:a: only this crew exits, including Bullfrog passengers;
    # other crew sharing the same hosts stays in. Empty/repeated calls harmless.
    # Other templates/AI instances are INFERRED; exit positions remain the
    # existing garrison approximation (work/re/c_teamexit_report.md).
    for b in sim.members(a[0]):
        sim.garrison.out(b)


def player_disable_unit_construction(sim, name, a, script):
    # engine_unitban: the native scripted button still queues; payment/progress wait until enabled.
    # Only named players and engineer unit queues measured. UI rejection, upgrades, other production
    # categories and player masks remain gaps; do not infer a ban on all construction.
    if a[0] in sim.players.values():
        (sim.unit_construction_disabled.add if name == 'PLAYER_DISABLE_UNIT_CONSTRUCTION'
         else sim.unit_construction_disabled.discard)(a[0])
    else:
        sim.gap('ScriptAction', name, '单位生产开关仅具名玩家原生工程师队列已量；玩家范围未量')


def player_disable_base_construction(sim, name, a, script):
    # aibgate:a (A269): a base-disabled skirmish AI orders no structure and spends nothing until enabled,
    # then starts as at its wake (simai build_offers). engine_baseban: a Japanese core (UNIT_BUILD) is not
    # held. A player's yard queue is not simulated (engine_basegate:a: a script's press queues nothing);
    # This Player / All Players remain gaps.
    if a[0] in sim.players.values():
        (sim.base_construction_disabled.add if name == 'PLAYER_DISABLE_BASE_CONSTRUCTION'
         else sim.base_construction_disabled.discard)(a[0])
    else:
        sim.gap('ScriptAction', name, '基地建造开关仅具名 AI 玩家的建筑订单已量；玩家范围未量')


ACTIONS = {
    'TEAM_DELETE': team_delete,
    'TEAM_KILL': team_delete,
    'TEAM_DELETE_LIVING': team_delete,
    'TEAM_CHANGE_OBJECT_STATUS': team_change_object_status,
    'TECHTREE_MODIFY_BUILDABILITY_OBJECT': techtree_modify_buildability_object,
    'NAMED_SET_DISABLED': named_set_disabled,
    'UNIT_KILL_ALL_IN_AREA': unit_kill_all_in_area,
    'TEAM_GARRISON_TEAM_INSTANTLY': team_garrison_team_instantly,
    'SELECT_OBJECT': select_object,
    'SELL_OBJECT': sell_object,
    'PLAYER_SELL_EVERYTHING': player_sell_everything,
    'NAMED_DAMAGE': named_damage,
    'NAMED_KILL': named_kill,
    'NAMED_DELETE': named_kill,
    'PLAYER_KILL': player_kill,
    'UNIT_SET_HEALTH': unit_set_health,
    'TEAM_SET_HEALTH': team_set_health,
    'NAMED_SET_MAX_HEALTH': named_set_max_health,
    'UNIT_SET_MODELCONDITION': unit_set_modelcondition,
    'TEAM_SET_MODELCONDITION': unit_set_modelcondition,
    'UNIT_SET_MODELCONDITION_FOR_DURATION': unit_set_modelcondition_for_duration,
    'TEAM_SET_MODELCONDITION_FOR_DURATION': unit_set_modelcondition_for_duration,
    'UNIT_SET_MODELCONDITION_GENERIC': unit_set_modelcondition_generic,
    'UNIT_CLEAR_MODELCONDITION': unit_set_modelcondition_generic,
    'UNIT_CHANGE_OBJECT_STATUS': unit_change_object_status,
    'UNIT_AFFECT_OBJECT_PANEL_FLAGS': unit_affect_object_panel_flags,
    'TEAM_AFFECT_OBJECT_PANEL_FLAGS': unit_affect_object_panel_flags,
    'NAMED_GARRISON_SPECIFIC_BUILDING': named_garrison_specific_building,
    'TEAM_GARRISON_NEAREST_BUILDING': team_garrison_nearest_building,
    'TEAM_GARRISON_SPECIFIC_BUILDING': team_garrison_specific_building,
    'NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY': named_garrison_specific_building_instantly,
    'TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY': team_garrison_specific_building_instantly,
    'NAMED_EXIT_BUILDING': named_exit_building,
    'EXIT_SPECIFIC_BUILDING': exit_specific_building,
    'TEAM_EXIT_ALL_BUILDINGS': team_exit_all_buildings,
    'PLAYER_DISABLE_UNIT_CONSTRUCTION': player_disable_unit_construction,
    'PLAYER_ENABLE_UNIT_CONSTRUCTION': player_disable_unit_construction,
    'PLAYER_DISABLE_BASE_CONSTRUCTION': player_disable_base_construction,
    'PLAYER_ENABLE_BASE_CONSTRUCTION': player_disable_base_construction,
}
