"""L6 script actions on the world's bookkeeping (ADR 0029, docs/engine/sim-layers.md; L0): flags, counters (on the
script executor's table: simexec.Counters; the timer actions are the executor's own), making objects and reinforcement teams, references and object lists, team membership and override relations,
sequential scripts, the *_TO_COUNTER reads, mission objectives, player relations and the map border (the script
switches are the executor's: engine/script/executor.py).

Each action is `fn(sim, name, a, script)`, moved verbatim out of Sim.act's chain; simact.act looks them up in ACTIONS."""
import math

import engine.data.units as simunits
import engine.world.handle as simworld
from engine.script.common import LOST, SCENE_FLAG, SHOW_FLAG, WON


def set_flag(sim, name, a, script):
    if SCENE_FLAG.fullmatch(str(a[0])):         # the player's input is off: nothing is late for a scene's length
        if a[1]:
            sim.scenes.append([sim.t, None])
        elif sim.scenes and sim.scenes[-1][1] is None:
            sim.scenes[-1][1] = sim.t
    if SHOW_FLAG.fullmatch(str(a[0])):          # a 功能 line's caption: asked for, then up (ctx.Talk `Now k`)
        if a[1]:
            sim.asked.setdefault(a[0], sim.t)
        elif a[0] in sim.asked:
            sim.up.append((a[0], sim.asked.pop(a[0]), sim.t))
    old = int(sim.flags.get(a[0], 0))
    sim.flags[a[0]] = int(a[1])                 # in the table once set, at 0 too (the script engine's flag array)
    if old != int(a[1]):
        sim.change()
        if a[0] == WON and a[1]:
            sim.end('赢', script)
        elif a[0] == LOST and a[1]:
            sim.end('输', script)


def set_counter(sim, name, a, script):
    sim.counters[a[0]] = a[1]


def set_counter_to_counter(sim, name, a, script):
    sim.counters[a[0]] = sim.counters.get(a[1], 0)


def counter_math_counter(sim, name, a, script):
    # retail uses 0 adds (a total of per-player kills) and 1 takes away (what is left of the transports spawned);
    # bench engine_scripts3 math / input (11-09): 2 multiplies, 3 divides toward zero (13 / 4 -> 3, -13 / 4 -> -3),
    # no floor; another code leaves the counter as it is (as the model). COUNTER_MATH_VALUE: the same with a number
    # for the second counter (bench engine_leechhealth: code 2 x 1000 packs the target's health, 11-18)
    dst, op, src = a
    c = sim.counters.get(dst, 0)
    other = int(src) if name == 'COUNTER_MATH_VALUE' else sim.counters.get(src, 0)
    if op not in (0, 1, 2, 3):
        sim.used.add(f'{name} code {op}')
    sim.counters[dst] = {0: c + other, 1: c - other, 2: c * other, 3: int(c / other) if other else c}.get(op, c)


def increment_counter(sim, name, a, script):
    sim.counters[a[1]] = sim.counters.get(a[1], 0) + (a[0] if name == 'INCREMENT_COUNTER' else -a[0])
    sim.change()


def create_named_on_team_at_waypoint(sim, name, a, script):
    p = sim.point(a[3])
    if p is None:
        return
    old = sim.bodies.get(a[0])
    if old and old.alive:
        return                                  # one object to a name (the game makes no second)
    b = sim.add(a[0], a[1], a[2].split('/')[0], *p, by=script.name, at=sim.t)
    b.team = a[2]
    sim.active.add(a[2])
    b.angle = float(a[4]) if len(a) > 4 else 0.0
    if sim.blocks(b):
        sim.reblock()
    sim.note('出现', f'{sim.label(b)}（{a[1]}，{sim.who(b.owner)}）在 {a[3]}'
              + ('' if b.owner == sim.human or sim.sees(b.x, b.y, b.surface == 'air') else '，玩家看不见'))
    sim.change()


def create_unnamed_on_team_at_waypoint(sim, name, a, script):
    # (type, team, waypoint[, angle]): the named one's maker without a name (RA3 1.13: both run the same three
    # calls, work/re actions_map.json), a new object every time it runs, on the team; no name, so '#' (an
    # unnamed one for SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER) -- bench 2026-11-09 ref_d
    sim.used.add('create unnamed')
    p = sim.point(a[2])
    if p is None:
        return
    b = sim.add(simworld.free_name(sim, '#created', a[0]), a[0], a[1].split('/')[0], *p, by=script.name, at=sim.t)
    b.team = a[1]
    sim.active.add(a[1])
    b.angle = float(a[3]) if len(a) > 3 else 0.0
    if sim.blocks(b):
        sim.reblock()
    sim.note('出现', f'{a[0]}（{sim.who(b.owner)}）在 {a[2]}'
              + ('' if b.owner == sim.human or sim.sees(b.x, b.y, b.surface == 'air') else '，玩家看不见'))
    sim.change()


def create_reinforcement_team(sim, name, a, script):
    sim.reinforce(a[0], a[1], script)


def create_reinforcement_team_at_unit_position(sim, name, a, script):
    # (team, named unit): at where the unit stands now, on a building too (not pushed off it); nothing at a
    # dead one (bench 11-15 engine_reinfat go: 3 inside 60 of a house, 3 at a tank's goal after it drove
    # there, none at a tank killed 2 s before)
    b = sim.body(a[1])
    if b is None or not b.alive:
        sim.used.add('reinforcement unit dead')
    else:       # where the unit checked stands, not the name read again (11-19 same-name sweep)
        sim.reinforce(a[0], a[1], script, at=(b.x, b.y))


def set_ref_to_nerest_team_of_unnamed_type_owned_by_player(sim, name, a, script):
    sim.nearest_ref(*a[:4])


def set_ref_to_nerest_team_of_type_owned_by_player(sim, name, a, script):
    # INFERRED: the same, named ones too
    sim.used.add('nearest ref any')
    sim.nearest_ref(*a[:4], unnamed=False)


def objectlist_addobjecttype(sim, name, a, script):
    # (type, list): the list grows by that type (types read lower case)
    sim.object_lists.setdefault(str(a[1]).lower(), set()).add(str(a[0]).lower())


def unit_set_team(sim, name, a, script):
    # the unit joins the team (K6: ctx.order does it before every whole-team order)
    b = sim.body(a[0])
    sim.active.add(a[1])                   # ... and the team has an instance from then on, the unit there or not (E3)
    if b and b.alive:
        b.team = a[1]


def team_set_players_nearest_unit_of_type_to_reference(sim, name, a, script):
    # (type, team, ref) INFERRED: SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER with the team's player
    crew = sim.members(a[1])
    if crew:
        sim.nearest_ref(a[0], crew[0].owner, a[1], a[2], unnamed=False)


def team_merge_into_team(sim, name, a, script):
    # (source, target) INFERRED (Generals doMergeTeamIntoTeam): the
    for b in sim.members(a[0]):              # source's members join the target, their orders kept
        b.team = a[1]
    sim.active.add(a[1])
    sim.change()


def team_set_override_relation_to_team(sim, name, a, script):
    # (team / player, team / player, Enemy / Neutral / Friend) INFERRED (Generals doTeam / doPlayer override
    # relation): how the first takes the second from then on, over the players' relation (hostile)
    table = {'TEAM_SET_OVERRIDE_RELATION_TO_TEAM': sim.team_team_rel,
             'TEAM_SET_OVERRIDE_RELATION_TO_PLAYER': sim.team_player_rel}.get(name, sim.player_team_rel)
    table[(a[0], a[1])] = a[2] if isinstance(a[2], str) else {0: 'Enemy', 1: 'Neutral', 2: 'Friend'}[a[2][0]]
    sim.change()


def unit_spawn_named_object_on_team_at_named_object_location(sim, name, a, script):
    # (name, type, team, object) INFERRED: CREATE_NAMED_ON_TEAM_AT_WAYPOINT at the object's place, its facing
    at = sim.body(a[3])
    if at and sim.present(at):
        spot = f'SIM spawn spot {len(sim.waypoints)}'
        sim.waypoints[spot] = (at.x, at.y)
        sim.act('CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION', [a[0], a[1], a[2], spot, at.angle], script)


def team_transfer_to_player(sim, name, a, script):
    # (team, player) l2_scripts1 6: each member goes to the player's own team, its order cleared. Bench 11-08
    # engine_scripts1 xfer: owned by the new player at once, the move it was on dropped, the team left empty
    for b in sim.members(a[0]):
        b.owner, b.team = a[1], f'{a[1]}/team{a[1]}'
        sim.stand(b)
        sim.note('易主', f'{sim.label(b)} 归 {sim.who(a[1])}（命令清掉）')
    sim.change()


def unit_stop_sequential_script(sim, name, a, script):
    # engine_seqstop:a: clear both active and queued scripts; leave the
    # already issued move running, and allow a fresh script afterwards.
    b = sim.body(a[0])
    if b is not None:
        sim.seq[:] = [r for r in sim.seq if r['b'] is not b]


def unit_execute_sequential_script(sim, name, a, script):
    # (unit, script) d115 14: queued on the unit (behind its others), one action a frame once it is idle
    # (seq_due); the script becomes a subroutine. The record's loop count is 0 here (one run; the catalog's
    # action has no third argument)
    b = sim.body(a[0])
    sc = sim.executor.script_named(a[1])
    if b and b.alive and sc is not None:
        sc.subroutine = True
        sim.seq.append({'b': b, 'script': sc, 'step': -1, 'loops': int(a[2]) if len(a) > 2 else 0})


def set_unit_health_percentage_to_counter(sim, name, a, script):
    b = sim.body(a[0])
    if b:
        sim.used.add('health of the dead')
        if b.alive:                     # whole percent, rounded down (engine_garrison hp: 200 of 3000 reads 6)
            sim.counters[a[1]] = math.floor(b.health + 1e-6)
        elif b.died_at == sim.t and not b.deleted:
            # killed by a script earlier this frame: it is still there, at 0 (a NAMED_DELETE leaves the last
            # value: engine_immortal b, bench 11-09, health 1 beside gone 1)
            sim.counters[a[1]] = 0
        # dead before this frame (a weapon's kill lands after the frame's scripts): the counter keeps the last
        # value read (bench 11-09 pend_scripts9 rel: 12 to the end, the tank gone on the minimap; engine_float,
        # engine_spawn, engine_super saw the same freeze)


def set_player_ownership_of_type_counter(sim, name, a, script):
    # a template's EquivalentTo counts under that name too (simunits.equivalent_to; bench engine_aiopen b)
    name = a[0].lower()
    sim.counters[a[2]] = sum(1 for b in sim.living() if b.owner == a[1] and
                              (b.template.lower() == name or simunits.equivalent_to(b.template, sim.own) == name))


def set_player_money_to_counter(sim, name, a, script):
    sim.counters[a[1]] = int(sim.money.get(a[0], 0))


def set_player_kills_of_type_to_counter(sim, name, a, script):
    # Native weapon-credit/type/player contrast: engine_killcount a/b.
    # Lists use the existing type resolver; list unions remain INFERRED.
    want = sim.of_types(a[1])
    sim.counters[a[2]] = sum(1 for owner, _, template, _ in sim.kills
                               if owner == a[0] and template.lower() in want)


def mark_mission_objective_completed(sim, name, a, script):
    # bench 11-16 checks/engine_markobj.py goals: status 2 / 1 from any status -- a hidden one listed done, a
    # failed one done, a done one unticked; NOT_COMPLETED never draws the failed mark (j07 'failed bonus 2')
    sim.act('SET_MISSION_OBJECTIVE_STATUS', [a[0], 1 if 'NOT' in name else 2], script)


def set_mission_objective_status(sim, name, a, script):
    if a[1] not in (0, 1, 2, 3):                # script-semantics.md 8: only 0..3, any other does nothing
        return                                  # (inferred; checks/engine_scripts5.py goals O5 asks the bench)
    old = sim.objectives.get(a[0], 0)
    sim.objectives[a[0]] = a[1]
    if a[1] != old and a[1]:
        g = next((g for g in sim.m.objectives if g.name == a[0]), None)
        title = sim.text(g.title) if g else a[0]
        sim.note('目标', f'{"奖励" if g and g.bonus else ""}目标{["", "亮出", "完成", "失败"][a[1]]}：{title}')
        sim.change()


def link_mission_objective_to_object(sim, name, a, script):
    s = sim.markers.setdefault(a[0], set())
    (s.add if a[2] else s.discard)(a[1])


def player_relates_player(sim, name, a, script):
    # (index, 0, name): the game reads the index (plan.relates)
    r = a[2]
    sim.relations[(a[0], a[1])] = r if isinstance(r, str) else \
        {0: 'Enemy', 1: 'Neutral', 2: 'Friend'}[r[0]]


def map_switch_border(sim, name, a, script):
    if sim.all_revealed() or sim.reveals:
        sim.used.add('border reveal')
    sim.border = int(a[0])
    names = list(getattr(sim.m.map, 'BORDERS', {}))
    sim.note('边界', f'可玩区换成 {names[sim.border] if sim.border < len(names) else sim.border}')
    sim.change()


ACTIONS = {
    'SET_FLAG': set_flag,
    'SET_COUNTER': set_counter,
    'SET_COUNTER_TO_COUNTER': set_counter_to_counter,
    'COUNTER_MATH_COUNTER': counter_math_counter,
    'COUNTER_MATH_VALUE': counter_math_counter,
    'INCREMENT_COUNTER': increment_counter,
    'DECREMENT_COUNTER': increment_counter,
    'CREATE_NAMED_ON_TEAM_AT_WAYPOINT': create_named_on_team_at_waypoint,
    'CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION': create_named_on_team_at_waypoint,
    'CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT': create_unnamed_on_team_at_waypoint,
    'CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION': create_unnamed_on_team_at_waypoint,
    'CREATE_REINFORCEMENT_TEAM': create_reinforcement_team,
    'CREATE_REINFORCEMENT_TEAM_AT_UNIT_POSITION': create_reinforcement_team_at_unit_position,
    'SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER': set_ref_to_nerest_team_of_unnamed_type_owned_by_player,
    'SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER': set_ref_to_nerest_team_of_type_owned_by_player,
    'OBJECTLIST_ADDOBJECTTYPE': objectlist_addobjecttype,
    'UNIT_SET_TEAM': unit_set_team,
    'TEAM_SET_PLAYERS_NEAREST_UNIT_OF_TYPE_TO_REFERENCE': team_set_players_nearest_unit_of_type_to_reference,
    'TEAM_MERGE_INTO_TEAM': team_merge_into_team,
    'TEAM_SET_OVERRIDE_RELATION_TO_TEAM': team_set_override_relation_to_team,
    'TEAM_SET_OVERRIDE_RELATION_TO_PLAYER': team_set_override_relation_to_team,
    'PLAYER_SET_OVERRIDE_RELATION_TO_TEAM': team_set_override_relation_to_team,
    'UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION': unit_spawn_named_object_on_team_at_named_object_location,
    'TEAM_TRANSFER_TO_PLAYER': team_transfer_to_player,
    'UNIT_STOP_SEQUENTIAL_SCRIPT': unit_stop_sequential_script,
    'UNIT_EXECUTE_SEQUENTIAL_SCRIPT': unit_execute_sequential_script,
    'SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER': set_unit_health_percentage_to_counter,
    'SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER': set_player_ownership_of_type_counter,
    'SET_PLAYER_MONEY_TO_COUNTER': set_player_money_to_counter,
    'SET_PLAYER_KILLS_OF_TYPE_TO_COUNTER': set_player_kills_of_type_to_counter,
    'MARK_MISSION_OBJECTIVE_COMPLETED': mark_mission_objective_completed,
    'MARK_MISSION_OBJECTIVE_NOT_COMPLETED': mark_mission_objective_completed,
    'SET_MISSION_OBJECTIVE_STATUS': set_mission_objective_status,
    'LINK_MISSION_OBJECTIVE_TO_OBJECT': link_mission_objective_to_object,
    'LINK_MISSION_OBJECTIVE_TO_WAYPOINT': link_mission_objective_to_object,
    'PLAYER_RELATES_PLAYER': player_relates_player,
    'MAP_SWITCH_BORDER': map_switch_border,
}
