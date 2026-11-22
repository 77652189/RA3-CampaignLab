"""L6 script actions on unit orders (ADR 0029, docs/engine/sim-layers.md; L5): moves, follows, attacks, guards, stops,
hunts, stances, idles, teleports and the AI hand-over.

Each action is `fn(sim, name, a, script)`, moved verbatim out of Sim.act's chain; simact.act looks them up in ACTIONS.
A guarded one returns False where its guard fails (Sim.act's chain goes on, as before the move). team_commands is the
old chain's own run of branches for the team commands, in its order: the "no live team" branch first (E3).
`isinstance(b.goal, type(b))` was `isinstance(b.goal, Body)` (Body has no subclasses: the same test).

The orders go through the run's command port (R3 13d-1): `_order` for the units a script names (the names as the
script gave them: a reference reads as what it points at), `_order_bodies` for the ones an action picked itself (a
team's members, a player's units, the movers) -- by serial, so a reference of the same name cannot stand in for the
picked one (review 11-19 f #1). An action keeps what decides who is ordered and when. Not orders, so not through it: a
teleport and the AI hand-over (they drop the unit's order with `stand`, a god's hand)."""
import math

import engine.orders.order as simorder
import engine.orders.seq as simseq
from engine.ports.command import Command
from engine.script.common import TEAM_COMMANDS, TEAM_FOLLOWS, team_crew
from engine.world.handle import CIV, GAP_ACTION


def _order(sim, kind, units, *args, **fields):
    """A map script's order through the run's command port: `units` the objects' names as the action found them (one
    not there is given its order all the same, as the order calls always took it); `args` more (name, value) pairs."""
    sim.commands.do(Command(kind, 'script', units=tuple(units), args=(('objects', True),) + args, **fields))


def _order_bodies(sim, kind, bodies, *args, **fields):
    """The order to the objects an action picked itself, by serial (the port finds each as picked, not by a name a
    reference may take over)."""
    sim.commands.do(Command(kind, 'script', units=tuple(b.serial for b in bodies), args=(('objects', 'serial'),) + args,
                            **fields))


def team_commands(sim, name, a, script):
    if name not in TEAM_COMMANDS:
        return False
    crew = team_crew(sim, a[0])
    if crew is None:
        # the game looks the team up without making it: no team by the name, so the order does nothing (E3)
        sim.lost_orders.append((sim.t, script.name, name, a[0]))
        sim.note('无效命令', f'{name} {a[0]}：找不到这个队（没人加入 / AI 还没组），命令落空')
    elif name in ('MOVE_TEAM_TO', 'ATTACK_MOVE_TEAM_TO'):
        _order_bodies(sim, 'attack_move' if name == 'ATTACK_MOVE_TEAM_TO' else 'move', crew,
               ('group', True), ('on_grid', True), place=a[1])
    elif name in TEAM_FOLLOWS:
        # (team, path, asTeam[, ?][, start waypoint]); the fourth flag (work/re/handoff-archive.md) not read: ignored.
        # The attack version is each member's own walk whatever asTeam says (bench 11-10 engine_wayatk3 cut:
        # both tanks within 60 of P though they stood 300 apart, tank 3 on to Q while tank 2 fought; INFERRED
        # why); the team only picks the join (the waypoint nearest its middle: the first try, P and Q 427 off
        # the middle each, both went to Q)
        attack = name == 'TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS'
        _order_bodies(sim, 'follow_path', crew, ('exact', name.endswith('_EXACT')),
               ('as_team', bool(int(a[2])) and not attack),
               ('start', a[-1] if name.endswith('_AT_WAYPOINT') else None), place=a[1], attacking=attack)
    elif name == 'TEAM_ATTACK_NAMED':
        _order_bodies(sim, 'attack', crew, target=a[1])
    elif name == 'TEAM_GUARD_AREA':
        _order_bodies(sim, 'guard', crew, place=a[1])
    else:
        _order_bodies(sim, 'stop', crew)


def move_named_unit_to(sim, name, a, script):
    _order(sim, 'attack_move' if name == 'ATTACK_MOVE_NAMED_UNIT_TO' else 'move', [a[0]], ('on_grid', True),
           place=a[1])                                                                  # snapped (engine_drop)


def named_follow_waypoints(sim, name, a, script):
    # (unit, path[, start waypoint])
    _order(sim, 'follow_path', [a[0]], ('exact', name.endswith('_EXACT')),
           ('start', a[2] if name.endswith('_AT_WAYPOINT') else None), place=a[1],
           attacking=name == 'NAMED_ATTACK_FOLLOW_WAYPOINTS')


def named_attack_named(sim, name, a, script):
    _order(sim, 'attack', [a[0]], target=a[1])


def unit_guard_area(sim, name, a, script):
    _order(sim, 'guard', [a[0]], place=a[1])


def named_stop(sim, name, a, script):
    _order(sim, 'stop', [a[0]])


def unit_context_sensitive_attack(sim, name, a, script):
    # (unit, target). Bench 11-13 engine_acts_u: an engineer on an enemy plant takes it (SKIRMISH_AI_DO_NOT_TAKE
    # on it or not, the uncommanded one beside another plant does not); a tank on an enemy plant 210 off never
    # fired in 30 s, on its own plant neither -- so not "attack". What else it does (repair, enter) INFERRED: nothing.
    # The team action: the same on every member (its handler loops the members through the unit one's call)
    g = sim.body(a[1])
    for b in [sim.body(a[0])] if name.startswith('UNIT') else sim.members(a[0]):
        if b and g and b.alive and g.alive and sim.engineer_entry(b, g):
            _order_bodies(sim, 'capture', [b], target=a[1])
        elif b and g:
            sim.note('无效命令', f'{name} {b.name} -> {a[1]}：只认工兵占楼（台上坦克对敌楼不开火）')


def team_move_to_nearest_object_of_type(sim, name, a, script):
    # (team, type): a move to the living object of that type nearest the team's middle. Bench 11-13
    # engine_acts_v near: the crew walked to the nearer of two of the player's barracks, and after it was
    # deleted (and the order given again) to the other. Its owner not asked (the bench's were the player's own;
    # any owner INFERRED); no such object: nothing done (INFERRED)
    crew = sim.members(a[0])
    if crew:
        want = str(a[1]).split(':')[-1].lower()
        mid = (sum(b.x for b in crew) / len(crew), sum(b.y for b in crew) / len(crew))
        _to_nearest(sim, 'move', crew, mid, lambda o: o.template.lower() == want)


def _to_nearest(sim, kind, crew, at, which):
    """The crew's group order to the living object `which` takes nearest the point `at`; none: nothing done."""
    goal = min((o for o in sim.living() if which(o)), key=lambda o: math.hypot(o.x - at[0], o.y - at[1]), default=None)
    if goal is not None:
        _order_bodies(sim, kind, crew, ('group', True), pos=(goal.x, goal.y))


def team_guard_area_from_position(sim, name, a, script):
    # (team, area, waypoint): bench 11-13 engine_acts_v guard: the tanks went to the waypoint (inside the area,
    # 100 in from its edge) and stayed there, the area's middle never reached; an enemy put in the area 600
    # from them: see the module docstring for what they did. Taken as a group move to the waypoint
    _order_bodies(sim, 'move', sim.members(a[0]), ('group', True), ('on_grid', True), place=a[2])


def named_face_waypoint(sim, name, a, script):
    # Native hull headings: engine_facewpai:b, west 180 / north-west 117,
    # untouched 0. Reuse the measured locomotor turn rate. Exact order
    # phase, moving hosts and missing/dead names remain gaps (INFERRED).
    b, p = sim.body(a[0]), sim.point(a[1])
    if b and b.alive and p is not None:
        _order(sim, 'face', [a[0]], place=a[1])
        sim.change()


def _crew(sim, name, who):
    """A TEAM_ action's members, else the living unit of that name (none: [])."""
    return sim.members(who) if name.startswith('TEAM_') else [b for b in [sim.body(who)] if b and b.alive]


def team_face_waypoint(sim, name, a, script):
    # (team, waypoint) A298 read: NAMED_FACE_WAYPOINT on each member with an AI
    crew = [b for b in _crew(sim, name, a[0]) if b.speed]
    if crew and sim.point(a[1]) is not None:
        _order_bodies(sim, 'face', crew, place=a[1])
        sim.change()


def unit_teleport_to_waypoint(sim, name, a, script, unit=None):
    # `unit`: the member a team action picked (the object itself, not a reference of its name: 11-19 sweep)
    b, p = unit if unit is not None else sim.body(a[0]), sim.point(a[1])
    if b and p:
        # the unit's orders go too: bench aiaeson (work/re d150) member 3166 attacking (AI state 10, not
        # ready) is idle and ready (16:1) the frame after the teleport, its team still in state 6
        b.x, b.y = p[0], p[1]
        simorder.stand(b)
        b.aiupdate.forget()
        sim.change()


def team_teleport_to_waypoint(sim, name, a, script):
    # (team, waypoint) INFERRED: the unit version on every member
    for b in sim.members(a[0]):
        sim.ra3_only.add('UNIT_TELEPORT_TO_WAYPOINT')       # as Sim.act noted the unit action it runs
        unit_teleport_to_waypoint(sim, 'UNIT_TELEPORT_TO_WAYPOINT', [b.name, a[1]], script, unit=b)


def unit_allow_ai_autoacquire(sim, name, a, script):
    # (unit, on): TEAM_ALLOW_AI_AUTOACQUIRE's for one unit
    b = sim.body(a[0])
    if b and b.alive:
        _order(sim, 'auto_acquire', [a[0]], ('on', bool(int(a[1]))))


def player_allow_ai_autoacquire(sim, name, a, script):
    # (player, on): the team version on every unit the player owns now. Bench 11-13 engine_acts_v aaq: the
    # player's tank fired on the enemy plant 210 off after it. A unit the player gets later not benched (the
    # bench's hand-over never happened), INFERRED: not reached
    crew = [b for b in sim.living() if b.owner == a[0]]
    if crew:                    # the flag read only with a unit to set, as each unit's was (review 11-19 f #3)
        _order_bodies(sim, 'auto_acquire', crew, ('on', bool(int(a[1]))))


def _wait(name, n):
    """An IDLE_FOR_* / GUARD_FOR_SECONDS count as its sequential-script wait in frames (l2_scripts1 3): the argument's
    integer slot -- a float written (mapscript.encode_arg's float slot: engine_acts2's 5.0) reads 0; _SECONDS x 15."""
    n = n if isinstance(n, int) else 0
    return n * 15 if name.endswith('_SECONDS') else n


def _hold(sim, name, n, b=None, team=None):
    """The wait on the unit's / team's sequential script (simseq.wait)."""
    simseq.wait(sim.seq, _wait(name, n), b, team)


def team_idle_for_seconds(sim, name, a, script):
    # (team, n) the members' orders dropped (engine_scripts7 idle) and the team's sequential script waits (A298:
    # TEAM_GUARD_FOR_SECONDS is this handler, engine_seqguard:g)
    _order_bodies(sim, 'idle', [b for b in sim.members(a[0]) if b.speed])
    _hold(sim, name, a[1], team=a[0])


def team_attack_team(sim, name, a, script):
    # (team / unit, team) INFERRED (Generals groupAttackTeam): each attacker on the target team's nearest
    # living member; when that one dies the fight picks the next (auto target). pending_scripts9 atk
    crew = _crew(sim, name, a[0])
    them = sim.members(a[1])
    for b in crew:
        if them:                # the nearest member by serial (its name for the record): no reference stands in
            t = min(them, key=lambda t: math.hypot(t.x - b.x, t.y - b.y))
            _order_bodies(sim, 'attack', [b], ('team', a[1]),     # the fight takes the next member when this dies
                   ('target_serial', t.serial), target=t.name)


def unit_idle_for_framecount(sim, name, a, script):
    # (unit, n) l2_scripts1 3: a unit with an AI drops its order (command 5) and its idle count is set. Bench
    # 11-08 idle: UNIT_IDLE_FOR_SECONDS 3 on a moving tank -- it never went on (45 s), not a 3 s pause
    b = sim.body(a[0])
    if b and b.alive and b.speed:
        _order(sim, 'idle', [a[0]])
        _hold(sim, name, a[1], b)


def team_hunt(sim, name, a, script):
    # l2_scripts1 4: a flag bit on each unit and its AI woken; only an AI player's HuntTactic (TEAM_HUNT) and
    # its AI (NAMED_HUNT) read it. Bench 11-08 hunt: a computer player's team / unit (AI not woken) and the
    # player's own team stayed where they were for 60 s (that team was emptied by the container, see below).
    # Bench 11-14 engine_acts_w hunt (round 216; retail a01's wave 2: Soviet_1 has a personality, never handed
    # to the AI, aiTeamBuilder / aiTactical 255): Soviet_4's crew (DefaultPersonality, both switches 255, not
    # woken) left home ~4 s after TEAM_ALLOW_AI_AUTOACQUIRE + TEAM_HUNT and went for the player's tank ~870
    # away, not the barracks ~1650 (the nearest structure, never reached); Soviet_5's (both 240) stayed, and
    # NAMED_HUNT moved neither side's lone conscript in 60 s. Bench 11-14 engine_acts_y hunt (round 218,
    # unarmed engineers as targets): aiTactical is the gate (Soviet_5 240 / 255 hunted, Soviet_6 255 / 240
    # stayed); the crew went for the engineer 700 east, not the barracks 1000 west -- the nearest hostile
    # object, a unit too; when it died the crew went on to the next nearest (another engineer, then the
    # barracks), and NAMED_HUNT moved a woken AI's (Soviet_3's) conscript neither. So: an attack-move of the
    # crew to the nearest hostile object, again after each target dies (Sim.hunt_due; the AI's own HuntTactic
    # in the model is engine line B's: work/re/a216_hunt_interface.md)
    crew = _crew(sim, name, a[0])
    movers = [b for b in crew if b.speed > 0]
    if name == 'TEAM_HUNT' and movers and sim.tactical(movers[0].owner):
        _order_bodies(sim, 'hunt', movers)
    elif any(b.owner in sim.ai for b in crew):
        sim.gap(GAP_ACTION, name, 'AI 玩家的猎杀战术（HuntTactic）不模拟（引擎 B 的 AI）')


def unit_ai_transfer(sim, name, a, script):
    # (unit / team, on) l2_scripts1 7: a computer player's units into / out of its AI's hands; a human
    # player's: nothing. Bench 11-10 engine_aixfer xfer / late (Soviet_4, AI not woken): handed over (on)
    # each leaves its crew (onto no team a script names: teamSoviet_4 stays 0) and drops its order -- the
    # notes read no order cleared, yet a move given in the same script or 3 s before never arrived; the
    # player's crew kept both. Handed back (off): not benched, nothing done. What a woken AI then does with
    # them is engine B's (AI not simulated)
    crew = _crew(sim, name, a[0])
    theirs = [b for b in crew if b.owner not in (sim.human, CIV)]
    if theirs and int(a[1]):
        for b in theirs:
            b.team = ''
            simorder.stand(b)
    elif theirs:
        sim.gap(GAP_ACTION, name, '收回（开关 0）没上台量过，不模拟')
    if any(b.owner in sim.ai for b in theirs):
        sim.gap(GAP_ACTION, name, '交给 AI 后的行为不模拟（引擎 B 的 AI）')


def team_set_stance(sim, name, a, script):
    # (team, stance) d115 23: each member now (a member's, not the team's: one joining later keeps its own),
    # as UNIT_SET_STANCE; bench 11-13 engine_acts flow (stance)
    for b in sim.members(a[0]):
        unit_set_stance(sim, 'UNIT_SET_STANCE', [b.name, a[1]], script, unit=b)


def team_allow_ai_autoacquire(sim, name, a, script):
    # (team, on) d115 11: each member now takes what only a computer's units take by themselves (the
    # NOT_AUTOACQUIRABLE + AUTO_ACQUIRABLE_BY_AI ones: structures); takes_by_itself reads it
    crew = sim.members(a[0])
    if crew:                    # the flag read only with a unit to set (review 11-19 f #3)
        _order_bodies(sim, 'auto_acquire', crew, ('on', bool(int(a[1]))))


def named_force_attack_named(sim, name, a, script):
    # (attacker, target) d115 13: the attack order that takes any relation (command 0xc); bench 11-13
    # engine_acts flow (force): on one of its own side
    _order(sim, 'attack', [a[0]], target=a[1], force=True)


def named_force_attack_waypoint(sim, name, a, script):
    # (attacker, waypoint) d115 13: command 0xe, fire at that spot of ground with no limit till another order
    # replaces it (retail a01: NAMED_STOP 6 s later). It takes nothing by itself meanwhile (fight: ground_fire);
    # the shots' own damage there is not simulated (INFERRED: none without a blast radius)
    b, p = sim.body(a[0]), sim.point(a[1])
    if b and b.alive and p and b.weapons:
        _order(sim, 'attack_ground', [a[0]], place=a[1])


def attack_move_team_to_named_object(sim, name, a, script):
    # (team, object) INFERRED: ATTACK_MOVE_TEAM_TO the object's place at the order (it is not followed)
    o = sim.body(a[1])
    if o and sim.present(o):
        _order_bodies(sim, 'attack_move', sim.members(a[0]), ('group', True), pos=(o.x, o.y))


def attack_move_team_to_nearest_object_of_type_of_player(sim, name, a, script):
    # (team, type, player): the same order as ATTACK_MOVE_TEAM_TO_NAMED_OBJECT, to the player's living object of that
    # type nearest the team's first member (INFERRED: not its middle); none of them: nothing done
    crew, want = sim.members(a[0]), sim.of_types(a[1])
    if crew:
        _to_nearest(sim, 'attack_move', crew, (crew[0].x, crew[0].y),
                    lambda o: o.owner == a[2] and o.template.lower() in want)


def player_set_all_units_to_flee(sim, name, a, script):
    # (player) engine_runoffmap: every one with RunOffMapBehavior runs
    _order_bodies(sim, 'flee', [b for b in sim.living() if b.owner == a[0]])


def unit_set_stance(sim, name, a, script, unit=None):
    # (name, stance): GUARD 0, AGGRESSIVE 1, HOLD_POSITION 2, HOLD_FIRE 3
    # Bench 11-06 engine_stance (docs/engine/stance.md): going HOLD_FIRE stops a standing attack order without
    # dropping it (a: no hit after the stance frame; f: back to GUARD, the same order fires again); an order
    # given while held fires (b); held, nothing by itself (d) and no hitting back (e)
    # `unit`: the member a team action picked, ordered by serial (11-19 sweep)
    b = unit if unit is not None else sim.body(a[0])
    if b and b.alive and unit is not None:
        _order_bodies(sim, 'stance', [b], ('stance', int(a[1])))
    elif b and b.alive:
        _order(sim, 'stance', [a[0]], ('stance', int(a[1])))


ACTIONS = {
    'ATTACK_MOVE_TEAM_TO': team_commands,
    'MOVE_TEAM_TO': team_commands,
    'TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS': team_commands,
    'TEAM_ATTACK_NAMED': team_commands,
    'TEAM_FOLLOW_WAYPOINTS': team_commands,
    'TEAM_FOLLOW_WAYPOINTS_EXACT': team_commands,
    'TEAM_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT': team_commands,
    'TEAM_GUARD_AREA': team_commands,
    'TEAM_STOP': team_commands,
    'MOVE_NAMED_UNIT_TO': move_named_unit_to,
    'ATTACK_MOVE_NAMED_UNIT_TO': move_named_unit_to,
    'NAMED_FOLLOW_WAYPOINTS': named_follow_waypoints,
    'NAMED_FOLLOW_WAYPOINTS_EXACT': named_follow_waypoints,
    'NAMED_ATTACK_FOLLOW_WAYPOINTS': named_follow_waypoints,
    'NAMED_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT': named_follow_waypoints,
    'NAMED_ATTACK_NAMED': named_attack_named,
    'UNIT_GUARD_AREA': unit_guard_area,
    'NAMED_STOP': named_stop,
    'UNIT_CONTEXT_SENSITIVE_ATTACK': unit_context_sensitive_attack,
    'TEAM_CONTEXT_SENSITIVE_ATTACK': unit_context_sensitive_attack,
    'TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE': team_move_to_nearest_object_of_type,
    'TEAM_GUARD_AREA_FROM_POSITION': team_guard_area_from_position,
    'NAMED_FACE_WAYPOINT': named_face_waypoint,
    'TEAM_FACE_WAYPOINT': team_face_waypoint,
    'UNIT_TELEPORT_TO_WAYPOINT': unit_teleport_to_waypoint,
    'TEAM_TELEPORT_TO_WAYPOINT': team_teleport_to_waypoint,
    'UNIT_ALLOW_AI_AUTOACQUIRE': unit_allow_ai_autoacquire,
    'PLAYER_ALLOW_AI_AUTOACQUIRE': player_allow_ai_autoacquire,
    'TEAM_IDLE_FOR_SECONDS': team_idle_for_seconds,
    'TEAM_IDLE_FOR_FRAMECOUNT': team_idle_for_seconds,
    'TEAM_GUARD_FOR_SECONDS': team_idle_for_seconds,
    'TEAM_ATTACK_TEAM': team_attack_team,
    'NAMED_ATTACK_TEAM': team_attack_team,
    'UNIT_IDLE_FOR_FRAMECOUNT': unit_idle_for_framecount,
    'UNIT_IDLE_FOR_SECONDS': unit_idle_for_framecount,
    'TEAM_HUNT': team_hunt,
    'NAMED_HUNT': team_hunt,
    'UNIT_AI_TRANSFER': unit_ai_transfer,
    'TEAM_AI_TRANSFER': unit_ai_transfer,
    'TEAM_SET_STANCE': team_set_stance,
    'TEAM_ALLOW_AI_AUTOACQUIRE': team_allow_ai_autoacquire,
    'NAMED_FORCE_ATTACK_NAMED': named_force_attack_named,
    'NAMED_FORCE_ATTACK_WAYPOINT': named_force_attack_waypoint,
    'ATTACK_MOVE_TEAM_TO_NAMED_OBJECT': attack_move_team_to_named_object,
    'ATTACK_MOVE_TEAM_TO_NEAREST_OBJECT_OF_TYPE_OF_PLAYER': attack_move_team_to_nearest_object_of_type_of_player,
    'PLAYER_SET_ALL_UNITS_TO_FLEE': player_set_all_units_to_flee,
    'UNIT_SET_STANCE': unit_set_stance,
}
