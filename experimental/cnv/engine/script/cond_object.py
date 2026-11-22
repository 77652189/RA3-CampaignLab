"""L6 script conditions on objects (ADR 0029, docs/engine/sim-layers.md; L2): alive, dying, destroyed, where they
stand, who owns and hit them, health, status bits and model conditions, garrisons, selection, kills, and the counts of
a player's objects (by type, kind, area, status, upgrade-free).

Each condition is `fn(sim, name, a)`, moved verbatim out of Sim.cond's chain; simcond.cond looks them up in
CONDITIONS. None back: not taken (a gap)."""
import math

from engine.script.common import CMP
from engine.objects.status import ACTED_STATUS
from engine.world.handle import GAP_CONDITION, held, inside
from engine.kernel import interfaces, module


def attacker(sim, b):
    """The object that hit b last, itself (its Body module's last_attacker: not whatever has been made under its
    name since -- 11-19 same-name sweep), while the world holds it (simworld.held), else None."""
    m = b.find(interfaces.Body) if b.modules else None
    return held(sim, m.last_attacker() if m is not None else None)


def named_destroyed(sim, name, a):
    b = sim.body(a[0])
    if b is None:
        sim.used.add('destroyed unborn')
        return False
    # killed: destroyed at once; deleted: only from the next frame (the game's destroy list at the frame's end)
    dead = not b.alive and not (b.deleted and sim.t <= b.died_at)
    return dead if name == 'NAMED_DESTROYED' else not dead


def named_dying(sim, name, a):
    return sim.dying(sim.body(a[0]))


def named_inside_area(sim, name, a):
    # the game asks no question of life: a dying unit is where it fell; a removed one is outside every area
    b = sim.body(a[0])
    within = bool(sim.present(b) and inside(sim.areas[a[1]], b.x, b.y))
    return within if name == 'NAMED_INSIDE_AREA' else not within


def player_has_object_comparison(sim, name, a):
    # the dying counted too (Team::countObjectsByThingTemplate, ignoreDead false); a type or an object list
    want = sim.of_types(a[3])
    n = sum(1 for b in sim.bodies.values() if b.owner == a[0] and b.template.lower() in want
            and sim.present(b))
    return CMP[a[1]](n, a[2])


def player_has_comparison_unit_type_in_trigger_area(sim, name, a):
    # one without SELECTABLE is not counted (engine_acts_drop age 类 1101: of four GI copies each with one of the drop
    # bomber's bits, only the -SELECTABLE one left out; +SUMMONED counted -- review 1121mm #3)
    n = sum(1 for b in sim.living() if b.owner == a[0] and b.template.lower() == a[3].lower()
            and 'SELECTABLE' in b.kinds and inside(sim.areas[a[4]], b.x, b.y))
    return CMP[a[1]](n, a[2])


def player_has_comparison_unit_kind_in_trigger_area(sim, name, a):
    sim.used.add('kind all players')
    kind = a[3][2] if isinstance(a[3], tuple) else a[3]
    n = sum(1 for b in sim.living() if kind in b.kinds and inside(sim.areas[a[4]], b.x, b.y))
    return CMP[a[1]](n, a[2])


def skirmish_player_has_units_in_area(sim, name, a):
    sim.used.add('units in area')
    return any(b.owner == a[0] and not b.scenery and inside(sim.areas[a[1]], b.x, b.y) for b in sim.living())


def named_owned_by_player(sim, name, a):
    b = sim.body(a[1])
    return bool(sim.present(b) and b.owner == a[0])


def named_attacked_by_player(sim, name, a):
    # the last damage only (ActiveBody's m_lastDamageInfo): a script's kill or another's hit clears it; the game
    # reads its source's id and looks that object up, so a source that is gone (dead and removed, deleted, self-
    # destructed) makes it false, and one that changed hands counts for its new owner (E2, reference 2026-11-04)
    b = sim.body(a[0])
    if not sim.present(b):
        return False
    if b.last_by is None:               # a hit a run script made up (打 / 摧毁): taken as the player's, standing
        return b.last_hit == a[1]
    by = attacker(sim, b)
    return bool(sim.present(by) and by.owner == a[1])


def unit_has_modelcondition(sim, name, a):
    b = sim.body(a[0])
    condition = a[1][2] if isinstance(a[1], tuple) else a[1]
    return sim.has_model_condition(b, condition)


def unit_health(sim, name, a):
    # whole percent, rounded down (int(health * 100 / max): 99.9 % reads 99, so "< 50" holds at 49.9 %); a dying
    # unit reads 0 (E4)
    b = sim.body(a[0])
    pct = math.floor(b.health + 1e-6) if b is not None and b.alive else 0
    return bool(sim.present(b) and CMP[a[1]](pct, a[2]))


def unit_has_object_status(sim, name, a):
    # (unit, status) l2_scripts1 2.2: the object's status bit; no object, false. Bench 11-08 cond: a bit a
    # script set reads at once, cleared at once, and a killed unit reads false from the kill
    b = sim.body(a[0])
    st = a[1][2] if isinstance(a[1], tuple) else a[1]
    bits = module.status_now(b) if b else set()     # AIRBORNE_TARGET in the air (engine_acts_wing: the Sea-Wing)
    if st not in ACTED_STATUS and st not in sim.attachment_known_status and st not in bits:
        sim.gap(GAP_CONDITION, name, f'状态位 {st}：模拟器只知道脚本设的和 {"、".join(sorted(ACTED_STATUS))}')
    if b and not b.alive and b.read_until == sim.frame_now():     # engine_sell e: a damage kill still reads
        return st in bits                                          # its bits in that frame
    return bool(b and b.alive and st in bits)


def player_has_number_objects_with_object_status(sim, name, a):
    # (player, cmp, n, status): the player's living objects with that bit, compared with n (know-how 97; the
    # count probes model.counted(status=), engine_aimicro 冲 / 曾冲). INFERRED: the dying not counted, as
    # UNIT_HAS_OBJECT_STATUS reads false from the kill -- no bench separates it; but a dead one that stays (no die
    # module, body.kill: NO_COLLISIONS) is counted (engine_block gk)
    st = a[3][2] if isinstance(a[3], tuple) else a[3]
    stay = [b for b in sim.bodies.values() if not b.alive and 'NO_COLLISIONS' in b.engine_status]
    mine = [b for b in sim.living() + stay if b.owner == a[0]]
    n = sum(1 for b in mine if st in b.status)
    if not n and st not in ACTED_STATUS and st not in sim.attachment_known_status:
        sim.gap(GAP_CONDITION, name, f'状态位 {st}：模拟器只知道脚本设的和 {"、".join(sorted(ACTED_STATUS))}')
    return CMP[a[1]](n, a[2])


def named_exited_area(sim, name, a):
    # retail batch 1 (round 207, checks/engine_conds.py; d115_script_semantics.md where it says 码)
    # INFERRED: inside the frame before, outside now (one frame)
    b = sim.body(a[0])
    now = bool(sim.present(b) and inside(sim.areas[a[1]], b.x, b.y))
    key = ('exited', a[0], a[1])
    was, sim.cond_memory[key] = sim.cond_memory.get(key, now), now
    return was and not now


def named_attacked_by_objecttype(sim, name, a):
    # retail batch 1 (round 207, checks/engine_conds.py; d115_script_semantics.md where it says 码)
    b = sim.body(a[0])
    by = attacker(sim, b) if sim.present(b) and b.last_by is not None else None
    return bool(by is not None and by.template.lower() in sim.of_types(a[1]))


def skirmish_player_has_been_attacked_by_player(sim, name, a):
    # retail batch 1 (round 207, checks/engine_conds.py; d115_script_semantics.md where it says 码)
    # INFERRED (Generals Player::getAttackedBy): set by any hit of the second's on the first's, kept for good
    for b in sim.bodies.values():
        if b.last_by is not None and b.last_hit is not None:
            sim.attacked_by.add((b.owner, b.last_hit))
    return (a[0], a[1]) in sim.attacked_by


def player_has_killed_named_unit(sim, name, a):
    # retail batch 1 (round 207, checks/engine_conds.py; d115_script_semantics.md where it says 码)
    # INFERRED: kills by weapon (self.kills, World.kill); n of a type at least n
    if name == 'PLAYER_HAS_KILLED_NAMED_UNIT':
        return any(k[0] == a[0] and k[3] == a[1] for k in sim.kills)
    if name == 'PLAYER_HAS_KILLED_TYPE_UNITS':
        want = sim.of_types(a[2])
        return sum(1 for k in sim.kills if k[0] == a[0] and k[2].lower() in want) >= int(a[1])
    want = sim.of_types(a[3])
    n = sum(1 for k in sim.kills if k[1] == a[0] and k[2].lower() in want)
    return CMP[int(a[1])](n, int(a[2]))


def named_selected(sim, name, a):
    # retail batch 2 (round 210, checks/engine_conds.py sight; d115_script_semantics.md 4-6)
    # bench 11-14 engine_share all: the object SELECT_OBJECT picked, while
    b = sim.body(a[0])                 # it lives (the bench: ~3 s more after NAMED_KILL, not modelled)
    return bool(b and b.alive and sim.selected == a[0])


def type_selected(sim, name, a):
    # retail batch 2 (round 210, checks/engine_conds.py sight; d115_script_semantics.md 4-6)
    # the same bench: never true after SELECT_OBJECT of a Guardian, a
    return False                        # refinery, an enemy Hammer; engine_eyes all: nor the player's own click / box


def named_building_is_empty(sim, name, a):
    # retail batch 4 (round 238, checks/engine_sighted.py all)
    # (object): a living garrison holding nobody -- 驻军 1 -> 3: H2 empty again once its man was ordered out;
    # H3 killed reads false (gone), as do a barracks and a tank (no garrison). A transport INFERRED as these
    b = sim.body(a[0])
    return bool(b and b.alive and sim.garrison.spec(b) is not None
                and not [u for u in sim.garrison.held(b) if u.alive])


def built_by_player(sim, name, a):
    # retail batch 4 (round 238, checks/engine_sighted.py all)
    # (type, player): the player owns one, however it came (建造 6 from the start: a placed Guardian and
    # barracks count; 23 once the engineer is out, a state -- 帧 +15 a second); a killed one still counts
    # while it lies (the engineer ~7 s after UNIT_KILL_ALL_IN_AREA; its linger INFERRED from the template)
    want = sim.of_types(a[0])
    return any(b.owner == a[1] and b.template.lower() in want and (sim.present(b) or sim.dying(b))
               for b in sim.bodies.values())


def player_destroyed_n_buildings_player(sim, name, a):
    # retail batch 4 (round 238, checks/engine_sighted.py all)
    # (player, n, opponent): false, always -- 摧毁 0 all run (round 240, checks/engine_razed.py all, bench 11-15
    # CampRazedAll_mcp_1115_030516), n 0 too, while the player's tanks razed two of the opponent's plants and
    # the opponent one of the player's. Generals' evaluatePlayerDestroyedNOrMoreBuildings is the same stub
    return False


def skirmish_player_has_comparison_garrisoned(sim, name, a):
    # retail batch 4 (round 238, checks/engine_sighted.py all)
    # (player, comparison, n): n against the player's men inside garrisons -- the men, not the buildings
    # (驻军, same run: two men in one building read == 2, a third in another >= 3, then 2 / 1 / 0 as they
    # leave; another player's man counts for his own). Men in a transport INFERRED not counted
    held = sum(1 for g in sim.living() if sim.garrison.spec(g) is not None
               for u in sim.garrison.held(g) if u.alive and u.owner == a[0])
    return CMP[int(a[1])](held, int(a[2]))


def player_has_comparison_unit_kind(sim, name, a):
    # retail batch 4 (round 238, checks/engine_sighted.py all)
    # (player, comparison, n, KindOf): n against EVERY player's living objects of the KindOf, as the
    # _IN_TRIGGER_AREA one reads -- engine_kind all (round 244, bench 11-15 CampKindAll_mcp_1115_045506) 种
    # 11 -> 15 -> 6 -> 22: four FS_FACTORY (two each) fail Player_1 == 2 and Soviet_4 <= 3, Soviet_4 >= 1
    # ENGINEER holds on Player_1's engineer once its own died, off with the last one
    sim.used.add('kind all players')
    kind = a[3][2] if isinstance(a[3], tuple) else a[3]
    return CMP[a[1]](sum(1 for b in sim.living() if kind in b.kinds), a[2])


def player_lost_object_type(sim, name, a):
    # retail batch 4 (round 238, checks/engine_sighted.py all)
    # (player, type or object list): Generals' evaluatePlayerLostObjectType -- ONE stored count per (player,
    # type string), the player's living objects of the type(s); every reader stores the count it finds and is
    # true when it is below the one stored, so a drop is one frame's truth for the first reader only (engine_kind
    # all 失 1 / 25 / 29 / 30 / 62: the second reader of the same string never; the object list its own string)
    store = sim.__dict__.setdefault('lost_counts', {})
    key = (a[0], str(a[1]).lower())
    want = sim.of_types(a[1])
    n = sum(1 for b in sim.living() if b.owner == a[0] and b.template.lower() in want)
    before = store.get(key, 0)
    store[key] = n
    return n < before


def named_destroyed_by_objecttype(sim, name, a):
    # retail batch 4 (round 238, checks/engine_sighted.py all)
    # (object, killer's type): false, always -- engine_kind all / by (round 244, bench 11-15
    # CampKindAll_mcp_1115_045506, CampKindBy_mcp_1115_045838): 毁 / 坦 / 王 0 all run on counters that add
    # every evaluation (one frame would show) while NAMED_DESTROYED saw all four die -- Tanya's pistols on an engineer, a
    # Guardian's gun on a truck, Tanya's charge on King Oni, a script's kill; the type in either case.
    # INFERRED why: the dead object's name no longer finds it, so retail a04's bonus crate never comes
    return False


def building_garrisonned_by_object_type(sim, name, a):
    # retail batch 6 (round 245, checks/engine_enter.py all)
    # (building, type, player): the building holds a living one of that type (case ignored) owned by that
    # player -- 驻类 13 -> 4: the conscript's own player only, dropped the moment NAMED_EXIT_BUILDING runs
    g = sim.body(a[0])
    if not sim.present(g):
        return False
    want = sim.of_types(a[1])
    return any(u.alive and u.owner == a[2] and u.template.lower() in want
               for u in sim.garrison.held(g))


def player_has_comparison_unit_type_in_trigger_area_completely_built(sim, name, a):
    # retail batch 6 (round 245, checks/engine_enter.py all)
    # (player, comparison, n, type, area): the _IN_TRIGGER_AREA count of the player's own (建成 21 -> 31:
    # Soviet_4's plant counts for Soviet_4 only; lower case too); a plant made by script counts at once,
    # while it unpacks. One under construction (a player's placed one) would be left out: INFERRED, not
    # benched, and the simulator builds nothing that way. The drop bomber is not counted either (engine_acts_drop age 见:
    # INFERRED the plain count's SELECTABLE)
    n = sum(1 for b in sim.living() if b.owner == a[0] and b.template.lower() == str(a[3]).lower()
            and 'SELECTABLE' in b.kinds and inside(sim.areas[a[4]], b.x, b.y))
    return CMP[int(a[1])](n, int(a[2]))


CONDITIONS = {
    'NAMED_DESTROYED': named_destroyed,
    'NAMED_NOT_DESTROYED': named_destroyed,
    'NAMED_DYING': named_dying,
    'NAMED_INSIDE_AREA': named_inside_area,
    'NAMED_OUTSIDE_AREA': named_inside_area,
    'PLAYER_HAS_OBJECT_COMPARISON': player_has_object_comparison,
    'PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA': player_has_comparison_unit_type_in_trigger_area,
    'PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA': player_has_comparison_unit_kind_in_trigger_area,
    'SKIRMISH_PLAYER_HAS_UNITS_IN_AREA': skirmish_player_has_units_in_area,
    'NAMED_OWNED_BY_PLAYER': named_owned_by_player,
    'NAMED_ATTACKED_BY_PLAYER': named_attacked_by_player,
    'UNIT_HAS_MODELCONDITION': unit_has_modelcondition,
    'UNIT_HEALTH': unit_health,
    'UNIT_HAS_OBJECT_STATUS': unit_has_object_status,
    'PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS': player_has_number_objects_with_object_status,
    'NAMED_EXITED_AREA': named_exited_area,
    'NAMED_ATTACKED_BY_OBJECTTYPE': named_attacked_by_objecttype,
    'SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER': skirmish_player_has_been_attacked_by_player,
    'PLAYER_HAS_KILLED_NAMED_UNIT': player_has_killed_named_unit,
    'PLAYER_HAS_KILLED_TYPE_UNITS': player_has_killed_named_unit,
    'NAMED_HAS_KILLED_COMPARISON_UNIT_TYPE': player_has_killed_named_unit,
    'NAMED_SELECTED': named_selected,
    'TYPE_SELECTED': type_selected,
    'NAMED_BUILDING_IS_EMPTY': named_building_is_empty,
    'BUILT_BY_PLAYER': built_by_player,
    'PLAYER_DESTROYED_N_BUILDINGS_PLAYER': player_destroyed_n_buildings_player,
    'SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED': skirmish_player_has_comparison_garrisoned,
    'PLAYER_HAS_COMPARISON_UNIT_KIND': player_has_comparison_unit_kind,
    'PLAYER_LOST_OBJECT_TYPE': player_lost_object_type,
    'NAMED_DESTROYED_BY_OBJECTTYPE': named_destroyed_by_objecttype,
    'BUILDING_GARRISONNED_BY_OBJECT_TYPE': building_garrisonned_by_object_type,
    'PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA_COMPLETELY_BUILT': player_has_comparison_unit_type_in_trigger_area_completely_built,
}
