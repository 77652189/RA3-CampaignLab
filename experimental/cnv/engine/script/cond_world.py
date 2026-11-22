"""L6 script conditions on the world (ADR 0029, docs/engine/sim-layers.md; L0): flags, counters, the platform, hot
spots, and teams (made, emptied, where their members are, what hit them, whether they can get somewhere). TIMER_EXPIRED
is the script executor's own (engine/script/executor.py: the timers are its table).

Each condition is `fn(sim, name, a)`, moved verbatim out of Sim.cond's chain; simcond.cond looks them up in
CONDITIONS. None back: not taken (a gap)."""
from engine.script.cond_object import attacker
from engine.script.common import CMP, SURFACES, team_crew
from engine.world.handle import inside, same_team


def flag(sim, name, a):
    return int(sim.flags.get(a[0], 0)) == int(a[1])


def counter(sim, name, a):
    return CMP[a[1]](sim.counters.get(a[0], 0), a[2])


def team_destroyed(sim, name, a):
    # INFERRED (Generals evaluateIsDestroyed: the team has no object left; not read in RA3): the dying count
    # as there, as PLAYER_HAS_OBJECT_COMPARISON's; a team nobody was ever in is not destroyed; an AI's (its
    # members carry no map team name) when it holds none
    sim.used.add('team destroyed')
    crew = team_crew(sim, a[0])
    if crew is None:
        return False
    ever = [b for b in sim.bodies.values() if same_team(b.team, a[0])]
    if not ever:
        return not crew
    if all(b.instance >= 1 for b in ever):
        # bench 11-13 engine_conds team: a reinforcement team emptied by TEAM_KILL never reads destroyed
        # (队形&64), a map team TEAM_KILLed does (&128). INFERRED: an emptied instance made by a script is
        # gone, and the name finds no team (while one lives it is not destroyed either)
        return False
    return not any(same_team(b.team, a[0]) and sim.present(b) for b in sim.bodies.values())


def team_compare_num_members(sim, name, a):
    # (team, op, n) the living members (bench 11-08 engine_scripts1 xfer
    crew = team_crew(sim, a[0])       # 队里几个 2 -> 0 at the hand-over; engine_aixfer 队)
    return crew is not None and CMP[a[1]](len(crew) + sim.hidden_members(a[0]), a[2])


def team_has_fewer_than_x_units_with_kindof(sim, name, a):
    # (team, n, kind): fewer than n living members with the KindOf (bench 11-11 aiskirm:m 池兵: the AI pool's
    # CAN_ATTACK members 0 while the defense team holds the eight, 2 at s134). INFERRED: the dying are not
    # counted (as TEAM_COMPARE_NUM_MEMBERS here)
    sim.used.add('team kindof')
    crew, kind = team_crew(sim, a[0]), a[2][2] if isinstance(a[2], tuple) else a[2]
    return crew is not None and sum(1 for b in crew if kind in b.kinds) < int(a[1])


def current_platform(sim, name, a):
    # the game we run is the PC one
    return str(a[0]).upper() == 'PC'


def team_has_units(sim, name, a):
    # retail batch 1 (round 207, checks/engine_conds.py; d115_script_semantics.md where it says 码)
    # 码: any instance of the team's prototype with a living member that is no STRUCTURE / PROJECTILE /
    # IGNORE_FOR_VICTORY (a dying one is DESTROYED: not counted); no such team: false
    return any(not ({'STRUCTURE', 'PROJECTILE', 'IGNORE_FOR_VICTORY'} & set(b.kinds))
               for b in team_crew(sim, a[0], every=True) or ())


def team_inside_area_partially(sim, name, a):
    # retail batch 1 (round 207, checks/engine_conds.py; d115_script_semantics.md where it says 码)
    # 码: no such team (common.team_crew): false. The members considered (living, not INERT / MOVE_ONLY; k a
    # bit of the AI module's set);
    # PARTIALLY = one of them inside, ENTIRELY = all and one at least. Bench 11-13 engine_conds team: a
    # Guardian passes k 0 only (状态&16 / &32 / &128, k 3 / 7 / 1, never on). D 119 (码 + the retail uses): k is
    # a Locomotor Surface's index (GROUND 0, WATER 1, CLIFF 2, AIR 3 ... DEEP_WATER 7), a member counted when
    # its locomotor goes on that surface -- a ship without GROUND never for k 0 (INFERRED until engine_conds
    # sight). The game reads each object's area record, updated when its whole-number position changes
    # (Generals): INFERRED the same as where it stands
    k = int(a[2])
    crew = [b for b in team_crew(sim, a[0]) or () if not ({'INERT', 'MOVE_ONLY'} & set(b.kinds))]
    if k != 0:
        sim.used.add('team area k')
    face = SURFACES[k] if 0 <= k < len(SURFACES) else None
    crew = [b for b in crew if face in sim.surfaces(b)]
    ins = [inside(sim.areas[a[1]], b.x, b.y) for b in crew]
    return any(ins) if name.endswith('PARTIALLY') else bool(ins) and all(ins)


def team_created(sim, name, a):
    # retail batch 1 (round 207, checks/engine_conds.py; d115_script_semantics.md where it says 码)
    # bench 11-13 engine_conds team: one frame after a script made it (建队帧 1: Sim.reinforce, which makes the
    # team there too), a map team never (队形&32 off all along); which frame of the two INFERRED -- the one after
    f = next((v for k, v in sim.made_frame.items() if same_team(k, a[0])), None)
    return f is not None and sim.frame_now() == f + 1


def team_some_have_object_status(sim, name, a):
    # retail batch 1 (round 207, checks/engine_conds.py; d115_script_semantics.md where it says 码)
    # INFERRED (Generals evaluateTeamHasObjectStatus): the living members' bit; ALL holds on an empty team, not
    # on none (common.team_crew)
    crew, st = team_crew(sim, a[0]), a[1][2] if isinstance(a[1], tuple) else a[1]
    has = [st in b.status for b in crew or ()]
    return crew is not None and (any(has) if name.startswith('TEAM_SOME') else all(has))


def team_attacked_by_player(sim, name, a):
    # retail batch 1 (round 207, checks/engine_conds.py; d115_script_semantics.md where it says 码)
    # 码 (the player one): a living member's last damage recorded that player (its owner then, the attacker
    # gone or not); no such team (common.team_crew): false. The object type one INFERRED: the attacker's template
    crew = team_crew(sim, a[0]) or ()
    if name == 'TEAM_ATTACKED_BY_PLAYER':
        return any(b.last_by is not None and b.last_hit == a[1] for b in crew)
    want = sim.of_types(a[1])
    return any(b.last_by is not None and attacker(sim, b) is not None
               and attacker(sim, b).template.lower() in want for b in crew)


def mission_hot_spot_active(sim, name, a):
    # retail batch 2 (round 210, checks/engine_conds.py sight; d115_script_semantics.md 4-6)
    # 码: the hot spot's on byte; a name the map lacks: false
    return sim.hotspots.get(str(a[0]), False)


def team_can_path_to_waypoint(sim, name, a):
    # retail batch 4 (round 238, checks/engine_sighted.py all)
    # (team, waypoint): every living member has a way to the waypoint itself -- engine_cast all (round 242,
    # bench 11-15 CampCastAll_mcp_1115_040813) 路 21 -> 5: two Guardians to land yes, to the trench's water
    # no (no snap to the bank), a lone Bullfrog to the water yes, a Guardian + a Bullfrog to the water no, an
    # emptied team no. INFERRED: all members (a leader-only check -- the Guardian -- reads the same here)
    crew, q = sim.members(a[0]), sim.point(a[1])
    g = sim.ground
    return bool(crew) and q is not None and all(
        b.surface == 'air' or (g.open(b.surface, *q) and g.route(b.surface, (b.x, b.y), q) is not None)
        for b in crew)


def team_outside_area_entirely(sim, name, a):
    # retail batch 6 (round 245, checks/engine_enter.py all)
    # (team, area, k): not (INSIDE_ENTIRELY or INSIDE_PARTIALLY), Generals evaluateTeamOutsideAreaEntirely --
    # 区外 11 / 30 / 15: a team never made (absent) reads outside, k 1 (a Guardian has no WATER) outside all
    # along, the emptied team outside everything
    return not (team_inside_area_partially(sim, 'TEAM_INSIDE_AREA_ENTIRELY', a)
                or team_inside_area_partially(sim, 'TEAM_INSIDE_AREA_PARTIALLY', a))


def team_entered_area_partially(sim, name, a):
    # retail batch 6 (round 245, checks/engine_enter.py all)
    return sim.team_entered(a)


CONDITIONS = {
    'FLAG': flag,
    'COUNTER': counter,
    'TEAM_DESTROYED': team_destroyed,
    'TEAM_COMPARE_NUM_MEMBERS': team_compare_num_members,
    'TEAM_HAS_FEWER_THAN_X_UNITS_WITH_KINDOF': team_has_fewer_than_x_units_with_kindof,
    'CURRENT_PLATFORM': current_platform,
    'TEAM_HAS_UNITS': team_has_units,
    'TEAM_INSIDE_AREA_PARTIALLY': team_inside_area_partially,
    'TEAM_INSIDE_AREA_ENTIRELY': team_inside_area_partially,
    'TEAM_CREATED': team_created,
    'TEAM_SOME_HAVE_OBJECT_STATUS': team_some_have_object_status,
    'TEAM_ALL_HAS_OBJECT_STATUS': team_some_have_object_status,
    'TEAM_ATTACKED_BY_PLAYER': team_attacked_by_player,
    'TEAM_ATTACKED_BY_OBJECTTYPE': team_attacked_by_player,
    'MISSION_HOT_SPOT_ACTIVE': mission_hot_spot_active,
    'TEAM_CAN_PATH_TO_WAYPOINT': team_can_path_to_waypoint,
    'TEAM_OUTSIDE_AREA_ENTIRELY': team_outside_area_entirely,
    'TEAM_ENTERED_AREA_PARTIALLY': team_entered_area_partially,
}
