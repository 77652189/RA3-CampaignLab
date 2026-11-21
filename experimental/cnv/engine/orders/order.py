"""L5 unit orders: what a unit is told to do and how its standing orders run on (ADR 0029, docs/engine/sim-layers.md).

The order entries set a body's mode and goal and hand the walk to L2 (`peers.send`): a plain or attack move
(`order_move`, a group's `order_group`), an attack (`order_attack`), an engineer's capture (`order_capture`), a guard,
stop / stand, a waypoint path (`order_follow`, `path_start`, `path_next`, `follow_leg`); a stance and auto-acquire are
the unit's AIUpdate's (engine/modules/aiupdate.py). The dues are their frame parts:
a capture at the building's side, the next leg of a path, a sequential script's next step, a hunt's next pick
(`capture_due`, `follow_due`, `seq_due`, `hunt_due`). A run off the map is engine.orders.ability's.
The fight (`fight`, once a tick) is the attack state machine: a team attack goes on to the next member, each armed
body aims (L3 `aim`) and fires, rounds a blocked line, and chases by itself (`chase_step`: an attack-mover's
`attack_chase`, anyone else's `idle_chase`).
All over the world it is given (simworld.WORLD_API only). Its host's other parts come in as `peers` (`Peers`, the
names in PEERS only, read when used): L2 locomotion (send, claims, free_spot, goal_off_nodes, column_ends), L2
bodies (delete, modify, engineer_entry, the garrison), L3 targeting and fire (reach, fight_field, aim, can_hit,
in_range, shot_blocked, fire_spot, side_sees, the unshot templates and AI sides: engine.orders.target's), L4 money (wallet), the team
registry (members, team_targets) and the order queues the scripts fill (seq, hunts). The fight's per-tick state on the host
(WRITES: seen, firing, volleys, chilling, mid_aims, the fire obstacles, the field) is reset through `peers` too --
the only names it may set. This module never imports them. The loan serves engine.orders.ability too (its PEERS).
"""
import math

import numpy as np

import engine.data.units as simunits
from engine.kernel import interfaces
from engine.orders import ability as simability
from engine.orders import target as simtarget
from engine.world.handle import CIV, GRID, inside

CAPTURE_REACH = 20.0           # R4: an engineer this far outside a building's round is at its side (a guess)
ARRIVE = 1.5 * GRID             # a plain move that ends farther than this from where it was sent stopped short (held_up)
HUNT_REPICK = 45                    # frames from a hunted target's death to the crew's next pick (fit, hunt_due)
# an idle unit takes nothing by itself in the mission's first logic frame (bench 11-15 engine_dam BR: a bear 60 from an
# enemy conscript, NO_ATTACK from 0.1 s = frame 2, never left its 8-half start square; the simulator had it chase from
# frame 1 and stand at the conscript's feet by frame 15). INFERRED: the program's first idle scan not read -- 2 is the
# least the bench allows; with one acquisition pass a tick, any value up to the second tick's frame (8) acts the same
IDLE_SCAN_FROM = 2

WRITES = frozenset({'_field', '_fire_obstacles', 'chilling', 'firing', 'mid_aims', 'seen', 'volleys'})
PEERS = frozenset({'act', 'claims', 'column_ends', 'delete', 'engineer_entry', 'free_spot', 'garrison',
                   'goal_off_nodes', 'hunts', 'modify', 'powers_off', 'reach', 'send', 'seq', 'toggle_press',
                   'toggles_of', 'wallet', 'production',
                   'aim', 'can_hit', 'fight_field', 'fire_spot', 'in_range', 'members', 'shot_blocked',
                   'side_sees', 'ai', 'team_targets', 'unshot',
                   '_field', '_fire_obstacles', 'chilling', 'firing', 'mid_aims', 'seen', 'volleys'})


class Peers:
    """What the orders may reach on their host (the Sim) beyond the world: the names in PEERS, read when used; and
    the fight's per-tick state it may set there (WRITES)."""
    __slots__ = ('host',)

    def __init__(self, host):
        object.__setattr__(self, 'host', host)

    def __getattr__(self, name):
        if name not in PEERS:
            raise AttributeError(f'simorder.Peers: {name} is not lent (PEERS)')
        return getattr(self.host, name)

    def __setattr__(self, name, value):
        if name not in WRITES:
            raise AttributeError(f'simorder.Peers: {name} may not be set (WRITES)')
        setattr(self.host, name, value)


def order_move(world, peers, b, where, attacking, given=(), skip=(), face=None, on_grid=False):
    """A plain move (attacking: an attack-move). The spot is adjusted first (free_spot: the goal kept off the spots
    other units hold; on_grid, for a unit sent to a point -- MOVE_NAMED_UNIT_TO, a team's or a selection's move --
    also snapped to the grid, bench engine_drop; other moves keep their exact point, INFERRED); `given` are spots
    already handed out to a group being ordered, `skip` that group (its members' old goals are dropped first).
    face: the facing (radians) it turns to once there (the AI's form-up slots; send)."""
    if b:
        simability.stop_flee(b)             # INFERRED: any move order takes the run over, as STOP does
        b.follow = None                     # ... and a waypoint path (order_follow sets it again after its legs)
        b.ground_fire = None                # ... and a fire at the ground
        b.mode = 'attack' if attacking else 'move'
        p = world.point(where) if isinstance(where, str) else where
        if p is not None and b.alive and b.speed > 0:
            spot = peers.free_spot(b, peers.goal_off_nodes(b, p), peers.claims(b, skip) + list(given), on_grid)
            where = where if spot == p else spot
        peers.send(b, where, face=face)
        b.move_to = b.dest if not attacking else None


def order_group(world, peers, bodies, where, attacking, on_grid=False):
    """A move order to several units at once (a team's MOVE_TEAM_TO, a selection's click): Generals'
    AIGroup::groupMoveToPosition without a formation (GL/AI/AIGroup.cpp; work/re/generals-source-map.md). The unit
    nearest the goal is the centre and walks to the point; the others, nearest first, each to the point plus where
    it stands from that centre, the offset cut to 6 times its radius (computeIndividualDestination), then moved
    off spots already held (free_spot). Bench 2026-11-08 acceptance question 1 (a01's squad, 4 Peacekeepers + 2
    dogs): the squad's middle ~18-23 short of the point, the units apart -- the simulator had all six on the point.
    INFERRED for RA3 (its group move not read, docs/engine/pathing.md 5: the script's MOVE_TEAM_TO hands the team
    to one group command): the line check from the group's goal to the spot is left out. Two or more infantry stand
    in their block instead (column_ends -> simpath.block, bench 2026-11-17 engine_column)."""
    movers = [b for b in bodies if b and b.alive and b.speed > 0 and 'IMMOBILE' not in b.status]
    p = world.point(where) if isinstance(where, str) else where
    if len(movers) < 2 or p is None:
        for b in bodies:
            order_move(world, peers, b, where, attacking, on_grid=on_grid)
        return
    world.used.add('group move')
    movers.sort(key=lambda b: (b.x - p[0]) ** 2 + (b.y - p[1]) ** 2)
    given = []                                  # (x, y, radius) spots handed out to the group so far
    foot = [b for b in movers if 'INFANTRY' in b.kinds]
    if len(foot) >= 2:      # bench engine_colgate: 2 men, and 6 sent 20 short, stand in the block too
        world.used.add('column march')
        peers.column_ends(foot, p, attacking, given, movers, on_grid)
        movers = [b for b in movers if b not in foot]
    if not movers:
        return
    cx, cy = movers[0].x, movers[0].y
    for b in movers:
        vx, vy = b.x - cx, b.y - cy
        n = math.hypot(vx, vy)
        cap = 6 * b.radius
        if n > cap:
            vx, vy = vx * cap / n, vy * cap / n
        order_move(world, peers, b, (p[0] + vx, p[1] + vy), attacking, given, movers, on_grid=on_grid)
        given.append(tuple(b.dest or (b.x, b.y)) + (b.radius,))


def held_up(b):
    """A plain move whose way ended short of where it was sent (blocked: a wall across the street) is still on
    that move: it neither fires nor goes after anyone until its next order. Bench 2026-11-07 `a4 demoeng`: the
    opening demo's pair, sent to the engineer's clear mark and stopped by the ice ~157 from him (centre to centre,
    in the simulator), never shot him in the 2 s before their turn order; the simulator, counting them idle once
    stopped, had him dead at 61.7 s. INFERRED (RA3's AI move state not read); not told apart on the bench: that
    they stop farther off than the simulator's wall lets them (out of reach)."""
    return b.mode == 'move' and not b.path and b.goal is None and b.move_to is not None and \
        b.dest == b.move_to and math.hypot(b.dest[0] - b.x, b.dest[1] - b.y) > ARRIVE


def _target(world, target):
    """An order's target: an object the giver picked, given as it is (the 11-19 same-name sweep: read again by its
    name, a script reference of that name took its place), or a name, read as the world reads it (Sim.body)."""
    return world.body(target) if isinstance(target, str) else target


def order_attack(world, peers, b, target_name, force=False):
    """True where `b` goes for the target (already on it too), False where the order is turned down: a unit or target
    missing or dead, or one of its own side without force (review 11-19 m: the port read a success there)."""
    world.used.add('attack')
    target = _target(world, target_name)
    if b and target and not force and world.relation(b.owner, target.owner) == 'ALLIES':
        return False    # bench 11-13 engine_acts flow 友血: NAMED_ATTACK_NAMED on one of its own side, no shot (d115
        #                 13: FORCE_ATTACK_NAMED is the order that takes any relation); a neutral one not benched, kept
    if not (b and target and target.alive and b.alive):
        return False
    if b.hold_paused:                       # an order given under HOLD_FIRE fires (stance.md b)
        b.aiupdate.hold_paused = False
    if b.goal is not target:
        b.goal, b.mode, b.follow, b.ground_fire = target, 'attack', None, None
        peers.send(b, (target.x, target.y), reach=peers.reach(b, target))
    return True


def order_capture(world, peers, b, target_name):
    """R4: NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED with Command_CaptureBuilding: the engineer goes to the
    building; at its side it takes it (capture_due)."""
    world.used.add('capture')
    target = _target(world, target_name)
    if b and b.alive and target and target.alive and peers.engineer_entry(b, target):
        b.goal, b.mode = target, 'capture'
        peers.send(b, (target.x, target.y))
        return True
    return False


def capture_due(world, peers):
    """R4 / E15: an engineer at the building's side (reach and travel timing INFERRED).
    EngineerContain admits capture or allied repair; the entering engineer is consumed
    (engine_engineer:a/c, all three nations). Capture preserves HP, allied repair fills HP without changing owner.
    A deposit building pays its bonus now and its next
    deposit an interval on (Generals' AutoDepositUpdate.awardInitialCaptureBonus). Bench 2026-11-07 a4 derrick:
    the derrick the player's at the first reading after the order (s4), 500, then 15 every 2 s (s7 515 -> s46 800)."""
    for b in world.living():
        g = b.goal
        if b.mode != 'capture' or not isinstance(g, type(b)):
            continue
        if not g.alive:
            b.goal, b.mode, b.path = None, 'move', []
            continue
        rule = peers.engineer_entry(b, g)
        if not rule:
            b.goal, b.mode, b.path = None, 'move', []
            continue
        shape = world.blocks(g)
        r = (shape[2] if shape and len(shape) == 3 else 40.0) + CAPTURE_REACH
        d = math.hypot(g.x - b.x, g.y - b.y)
        if d > r and (b.path or d > 2 * r):
            continue
        if world.relation(g.owner, b.owner) == 'ALLIES':
            if g.hp >= g.max_hp:
                # engine_engineer:b: full-health allies keep their owner/HP
                # and all three nations' engineers survive. Travel INFERRED.
                b.goal, b.mode, b.path = None, 'move', []
                continue
            g.mend(math.inf)
            world.note('修理', f'{world.label(b)} 修复 {world.label(g)}')
            peers.delete(b, '进楼修理')
            world.change()
            continue
        g.owner = b.owner
        world.note('占领', f'{world.label(b)} 占下 {world.label(g)}，归 {world.who(b.owner)}')
        m = g.find(interfaces.Deposit) if g.modules else None
        if m is not None:                               # engine/modules/deposit.py (step M4)
            peers.wallet.credit(b.owner, m.capture(world.frame_now()))
        peers.delete(b, '进楼占领')
        world.change()


def order_guard(world, peers, b, area):
    world.used.add('guard')
    if b:
        b.follow = None
    if b and not inside(world.areas[area], b.x, b.y):
        peers.send(b, area)


def order_stop(b):
    if b:
        b.path, b.goal, b.follow, b.ground_fire = [], None, None, None
        simability.stop_flee(b)             # a later order takes the run over (engine_runoffmap d; the status stays)


def stand(b):
    """Its order dropped, nothing new: idle where it is (the AI's command 5: l2_scripts1 3, 6)."""
    b.path, b.goal, b.mode, b.move_to, b.follow = [], None, 'idle', None, None
    b.ground_fire = None


def idle(peers, b):
    """The unit's AI has nothing to do (a sequential script's next step waits for it, d115 14): no way to walk,
    no living target, no path, not firing at the ground, not running off."""
    return not b.path and not (isinstance(b.goal, type(b)) and b.goal.alive) and not b.follow \
        and not getattr(b, 'ground_fire', None) and not getattr(b, 'flee', None) \
        and b.serial not in peers.garrison.going


def seq_due(world, peers):
    """UNIT_EXECUTE_SEQUENTIAL_SCRIPT's frame (d115 14, the engine's "Advancing SeqScript"): of each unit's queue
    only the head moves -- the unit idle, its next action run (with <This Object> = the unit); past the last one
    it is done (loops 0), or goes to the back of the unit's queue to run again (loops - 1; -1 for ever). A dead
    unit's records go. Bench 11-13 engine_acts_seq: 跑 1 -> 11 at P -> 111 back and no more (one run, each step
    after the move before it), 排 0 -> 11 (the second script after the first's move). d115 14's wait frames
    (IDLE_FOR_* writing them) are not kept: 等 11 from the first second -- UNIT_IDLE_FOR_SECONDS 5 on the standing
    unit held the next step back not at all (what writes the wait: not known)."""
    heads = set()
    for r in list(peers.seq):
        b = r['b']
        if b.serial in heads:
            continue
        heads.add(b.serial)
        if not b.alive:
            peers.seq.remove(r)
            continue
        if not idle(peers, b):
            continue
        r['step'] += 1
        acts = [x for x in r['script'].actions if x.enabled]
        if r['step'] >= len(acts):
            peers.seq.remove(r)
            if r['loops']:
                r['loops'] -= r['loops'] != -1
                r['step'] = -1
                peers.seq.append(r)
            continue
        act = acts[r['step']]
        args = [b.name if x == '<This Object>' else (b.team if x == '<This Team>' else x) for x in act.args]
        if '<This Object>' in act.args:
            written = {}                    # the unit's name written as well: that one reads as written -- the
            if b.name in act.args and world.body(b.name) is not None:   # reference or the object of that name, not
                tok = b.name + AS_WRITTEN                               # the unit (same-name audit 11-19b O19)
                written[tok] = world.body(b.name)
                args = [tok if x == b.name else y for x, y in zip(act.args, args)]
            _as_itself(world, b, lambda: world.executor.action(act.name, args, r['script']), written)
        else:
            world.executor.action(act.name, args, r['script'])
        if not b.alive and r in peers.seq:
            peers.seq.remove(r)


_NONE = object()
# the suffix of a sequential step's token for the unit's name written as well as <This Object> (O19): the token reads
# as the object the name read before the step; a place by the name (Sim.point: waypoint, area, mark, site) is read by
# the name itself, before any object, as without the token (review 11-19 w P2 #2)
AS_WRITTEN = ' <as written>'


def _as_itself(world, b, step, written=()):
    """Run `step` (a sequential script's action, <This Object> written as `b`'s name) with that name reading as `b`
    itself: a reference of the same name, or another object made under it since, cannot take the unit's place
    (same-name audit 11-19, S5). For the step's length the name is in world.acting, which world.body and world.point
    read before the references (every action finds its object by name through them, either executor); the
    references are not written, so one the step points at the name itself stays (review 11-19 n P3 #3; #4: a point
    by the name is the unit's). Only a step written with <This Object> runs here (the caller; #2). Arguments and the
    log's text unchanged. A step writing both <This Object> and the unit's name gives the written one as a token of
    its own in `written` (token -> what the name read before the step: O19), in world.acting for the step too."""
    had = {k: world.acting.get(k, _NONE) for k in (b.name, *written)}
    world.acting[b.name] = b
    world.acting.update(written)
    try:
        step()
    finally:
        for k, v in had.items():
            if v is _NONE:
                world.acting.pop(k, None)
            else:
                world.acting[k] = v


def path_start(world, label, at):
    """The waypoint a path is joined at: of the waypoints carrying `label`, the nearest to `at` (2D; strictly
    nearer replaces, so the first in map order wins a tie) -- Generals' TerrainLogic::getClosestWaypointOnPath.
    None if no waypoint carries it."""
    best, bd = None, None
    for n, labels in world.mm.labels.items():
        if label in labels and n in world.waypoints:
            x, y = world.waypoints[n]
            d = (x - at[0]) ** 2 + (y - at[1]) ** 2
            if bd is None or d < bd:
                best, bd = n, d
    return best


def path_next(world, at):
    """The waypoint after `at` on its path (the map's WaypointsList, one way, whatever the next one's label),
    None at the path's end. Of several links the game takes either (Generals' getNextWaypoint: at random; bench
    11-10 engine_waypath: two runs of one map forked two ways); this takes the first (the runs stay repeatable)
    and marks the run. A loop goes round and round (bench 11-10 engine_waypath loop)."""
    nxt = [z for a, z in world.mm.links if a == at]
    if len(nxt) > 1:
        world.used.add('path fork')
    return nxt[0] if nxt else None


def order_follow(world, peers, bodies, label, attacking, exact=False, start=None, as_team=False):
    """NAMED_ / TEAM_ (ATTACK_) FOLLOW_WAYPOINTS (_EXACT, _STARTING_AT_WAYPOINT): each unit goes waypoint by
    waypoint along the path `label`, from `start`, or else the path's waypoint nearest to it (a team: to its
    middle, Generals' doTeamFollowWaypoints joins at getClosestWaypointOnPath of the team's estimated position);
    at a waypoint it takes the next (path_next) and stops at the path's end. Each leg is a move (order_move;
    attacking: an attack-move, it stops to fight and goes on). as_team (Generals AIFollowWaypointPathState with
    m_moveAsGroup): each member keeps where it stood from the team's middle (the mean, AIGroup::getCenter) when
    ordered -- every leg's goal is the waypoint plus that, uncut -- and the team shares one waypoint: the first
    member to get there sends them all on to the next (the team's current waypoint). Bench 11-10 engine_waypath
    (checks/engine_waypath.py 读数): line = exact (both reach B within 10: no corner cut), a loop goes round and
    round, a fork takes either link (random, the two runs took different ones), links lead on through waypoints
    without the label, joined at the nearest; team: both trucks 75 off every waypoint, the one ahead on the last
    leg there 3 s first. INFERRED: the team version's fourth flag, BiDirectional, the group's speed (the slowest
    member's, AIGroup::getSpeed: the bench's trucks are one kind)."""
    movers = [b for b in bodies if b and b.alive and b.speed > 0 and 'IMMOBILE' not in b.status]
    if not movers:
        return
    world.used.add('follow path')
    if start is None:
        n = len(movers)
        start = path_start(world, label, (sum(b.x for b in movers) / n, sum(b.y for b in movers) / n))
    if start is None or start not in world.waypoints:
        for b in movers:
            world.note('卡住', f'{world.label(b)} 找不到路 {label}')
        return
    how = {'label': label, 'at': start, 'attacking': attacking, 'exact': exact, 'team': as_team}
    if as_team and len(movers) > 1:
        n = len(movers)
        cx, cy = sum(b.x for b in movers) / n, sum(b.y for b in movers) / n
        how['offset'] = {b.serial: (b.x - cx, b.y - cy) for b in movers}
        world.used.add('team path')
    follow_leg(world, peers, movers, how)


def follow_leg(world, peers, movers, how):
    """Sends `movers` to how['at'] and marks them as on the path (a team as one: one shared dict; each member
    to the waypoint plus its own offset from the team's middle when ordered)."""
    if how['team'] and len(movers) > 1:
        wx, wy = world.waypoints[how['at']]
        given = []
        for b in movers:
            ox, oy = how['offset'].get(b.serial, (0.0, 0.0))
            order_move(world, peers, b, (wx + ox, wy + oy), how['attacking'], given=given, skip=movers)
            given.append((wx + ox, wy + oy, b.radius))
            b.follow = how
    else:
        for b in movers:
            order_move(world, peers, b, how['at'], how['attacking'])
            b.follow = dict(how, team=False)


def follow_due(world, peers):
    """The path followers that got where their leg went (no way left, not fighting): on to the next waypoint,
    or off the path at its end. One waypoint per tick at most."""
    done = set()
    for b in world.living():
        how = b.follow
        if how is None or id(how) in done:
            continue
        if how['team']:                     # the first member there moves the team's waypoint on
            group = [o for o in world.living() if o.follow is how]
            if all(o.path or o.engaged or o.resume is not None or isinstance(o.goal, type(o)) for o in group):
                continue
            done.add(id(how))
        else:
            if b.path or b.engaged or b.resume is not None or isinstance(b.goal, type(b)):
                continue                    # resume: turned aside to fight (attack_chase), the leg not done
            group = [b]
        nxt = path_next(world, how['at'])
        if nxt is None or nxt not in world.waypoints:
            for o in group:
                o.follow = None
            continue
        leg = dict(how, at=nxt)
        done.add(id(leg))
        follow_leg(world, peers, group, leg)


def hunt_due(world, peers, frame):
    """TEAM_HUNT's crews (Sim.act): one with no living target, its re-pick frame come, attack-moves to the
    hostile object (unit or structure, not civilian) nearest its middle. Bench 11-14 engine_acts_y hunt: an
    engineer died at s15, the crew by the next one (566 on) at s21; that one died at s29, the crew out of its
    spot at s39 and back past home (s49) for the barracks; another crew's bait died at s13, the next attacked at
    s29 -- HUNT_REPICK 45 frames (3 s) has each a second later, the bench's usual lag (0: the same but the
    second bait 2 s early; 75: 2-3 s late). INFERRED: a fit, the program's re-pick rule not read. A crew's members dying, joining other teams: not followed (the crew as ordered)."""
    for h in list(peers.hunts):
        movers = [b for b in h[0] if b.alive]
        if not movers:
            peers.hunts.remove(h)
            continue
        if h[1] is not None and h[1].alive:
            continue
        if h[1] is not None:                # its target just died: the re-pick waits
            h[1], h[2] = None, frame + HUNT_REPICK
        if frame < h[2]:
            continue
        mx, my = sum(b.x for b in movers) / len(movers), sum(b.y for b in movers) / len(movers)
        goal = min((o for o in world.living() if o.owner != CIV and world.hostile(movers[0], o)),
                   key=lambda o: (math.hypot(o.x - mx, o.y - my), o.name), default=None)
        if goal is None:
            peers.hunts.remove(h)
            continue
        h[1] = goal
        order_group(world, peers, movers, (goal.x, goal.y), True)


def fight(world, peers):
    """One tick of the fight model (未对齐, docs: the 'combat' align entry): every armed body fires each of its
    weapons at the nearest enemy in that weapon's range it can hit (its NAMED_ATTACK target first, when in
    range); the damage rate = the weapon's damage per second x the target's armour percent for its damage type;
    an attack-mover with an enemy in range holds while it fights; a plain move goes on firing; an idle unit goes
    after an enemy within its sight and comes back (`idle_chase`, R8). The reach is measured between the bounding
    circles (`in_range`, R8). The aim is taken once a tick; the damage is dealt frame by frame (`deal`, R6)."""
    peers.seen = {}
    peers.firing = []
    peers.volleys = []
    peers.chilling = []
    peers.mid_aims = {}
    peers._fire_obstacles = None             # `shot_blocked`'s footprints, taken once a tick when first asked
    live, armed, targets = peers.fight_field()
    peers._field = (live, armed, targets)
    if not armed or not targets:
        return
    aimable = {t.serial for t in targets}
    tx = np.array([b.x for b in targets])
    ty = np.array([b.y for b in targets])
    for a in armed:                         # an attack on a team goes on to its next member (TEAM_ATTACK_TEAM)
        if a.serial in peers.team_targets and not (isinstance(a.goal, type(a)) and a.goal.alive):
            them = peers.members(peers.team_targets[a.serial])
            if them:
                order_attack(world, peers, a, min(them, key=lambda t: math.hypot(t.x - a.x, t.y - a.y)))   # itself
            else:
                del peers.team_targets[a.serial]
    for a in armed:
        a.engaged = False
        if held_up(a):                 # stopped short on a plain move: still moving (DEMO_KILL)
            continue
        got = peers.aim(a, targets, aimable, tx, ty)
        if got is None:
            chase_step(world, peers, a, False, [])
            continue
        fired, d, idx = got
        g = a.goal
        if not fired and isinstance(g, type(a)) and g.alive and not a.path and g.serial in aimable and \
                (a.spot is None or a.spot[0] != g.serial or math.hypot(g.x - a.spot[1], g.y - a.spot[2]) > 150) and \
                any(peers.can_hit(w, g) and peers.shot_blocked(a, g, w) for w in a.weapons) and \
                not any(peers.can_hit(w, g) and peers.in_range(a, g, w) and not peers.shot_blocked(a, g, w)
                        for w in a.weapons):
            a.spot = (g.serial, g.x, g.y)          # told to attack, the line blocked: round to a clear spot
            p = peers.fire_spot(a, g)
            if p is not None:
                world.note('绕位', f'{world.label(a)} 打不着 {world.label(g)}（中间有建筑），绕到 ({p[0]:.0f},{p[1]:.0f})')
                peers.send(a, p)
        chase_step(world, peers, a, fired, [(d[j], targets[idx[j]]) for j in np.argsort(d, kind='stable')])
    if peers.firing or peers.volleys:
        world.used.add('combat')
    if peers.chilling:
        world.used.add('freeze')


def chase_step(world, peers, a, fired, near):
    """An attack-mover on its way (or turned aside) chases as `attack_chase`; anyone else as `idle_chase`."""
    if a.mode == 'attack' and not isinstance(a.goal, type(a)) and (a.path or a.resume is not None):
        attack_chase(world, peers, a, fired, near)
    else:
        idle_chase(world, peers, a, fired, near)


def attack_chase(world, peers, a, fired, near):
    """An attack-mover's own chase (bench 2026-11-10 engine_wayatk atk2, checks/engine_wayatk.py: a Guardian on an
    attack path, an enemy 220 beside the leg -- beyond the weapon's 196.6 from the path, within VisionRange 200 +
    its radius 23.3 -- steps up to it, fires from s6 (atk's, 150 off: s4), and goes on to B once it is dead (s22,
    atk s21); engine_acquire am260 / am400: 260 / 400 beside the path, no turn). Generals AIAttackMoveToState /
    AIAttackFollowWaypointPathState::update take getNextMoodTarget every frame their attack machine is idle: the
    mood scan within the vision range (calledDuringIdle false: AutoAcquireEnemiesWhenIdle not asked), an attack on
    what it finds, and the move again once that is done. The same reach as idle_chase's (the centre distance less
    the target's radius within its VisionRange); Generals limits a human player's units to attack range
    (WITHIN_ATTACK_RANGE) -- RA3 does not (the bench's tank is the human player's). It walks to `reach`, the fight
    holds it there (engaged), and with nothing left it is sent on to where the move was going (`resume`).
    A team on an attack path shares no target: each member takes only what its own scan finds (bench 11-10
    engine_wayatk3 cut: tank 2 fights an enemy 150 off its leg alone, ~13.5 % a shot; tank 3, never within 351 of
    it, goes on to P and Q meanwhile -- round 146's reading of engine_wayatk team, the team's target taken at any
    distance (Team::getTeamTargetObject), was wrong: there tank 3 walked to A itself, 212 from the enemy, within
    its own scan 223.3; order_follow keeps no places for the attack version).
    INFERRED: the scan's rate (MoodAttackCheckRate) and the way back (straight to the leg's end, not to the path)."""
    if a.chase is not None and a.path and a.dest != a.auto_to:      # an order since: its own way, not ours
        a.chase = a.resume = a.auto_to = None
    if a.building or a.speed <= 0 or 'IMMOBILE' in a.status or fired:
        return
    c = a.chase
    if c is not None and c.alive and peers.side_sees(a.owner, c) and \
            math.hypot(c.x - a.x, c.y - a.y) - c.radius <= a.sight:
        if not a.path:                      # got there and it is still out of reach: after it again
            peers.send(a, (c.x, c.y), reach=peers.reach(a, c))
            a.auto_to = a.dest
        return
    a.chase = None
    for dist, t in near:
        if dist - t.radius > a.sight:
            break                           # sorted by centre
        if not simtarget.takes_by_itself(a, t, peers) or not peers.side_sees(a.owner, t) or 'NON_AUTOACQUIRABLE' in t.status:
            continue
        if not any(peers.can_hit(w, t) and not peers.shot_blocked(a, t, w) for w in a.weapons):
            continue
        if a.resume is None:
            a.resume = a.dest
        a.chase = t
        world.used.add('acquire')
        peers.send(a, (t.x, t.y), reach=peers.reach(a, t))
        a.auto_to = a.dest
        return
    if a.resume is not None:                # nothing left: on to where the move was going
        r, a.resume, a.auto_to = a.resume, None, None
        peers.send(a, r)


def idle_chase(world, peers, a, fired, near):
    """R8, bench 2026-11-07 engine_acquire (a Guardian, weapon 150, VisionRange 200, both tanks radius 23.3): an
    idle unit fires where it stands at 180 (centre to centre); at 200 and 220 it walks up, fires, and once its
    target is done walks back to where it stood (within 15); at 240 and beyond, nothing -- likewise when guarding
    (260) or attack-moving past (260 / 400). Read as: an idle unit takes the nearest enemy it can hit and its side
    sees, when the centre distance less the target's radius is within its own VisionRange (220 < limit < 240:
    200 + 23.3; INFERRED, the scan itself not read), walks to `reach` of it, and goes home when it has none left.
    Idle = not building, no goal, no way of its own (a way this rule gave it does not count); any order since
    (another way) drops the chase and the home. `near`: [(centre distance, enemy)] nearest first.
    Stances (bench 2026-11-10 engine_acquire hold180 / hold220 / agg220 / agg240 / agg260): HOLD_POSITION fires
    in place at 180 as GUARD does but at 220 never moves nor fires -- it walks after nothing; AGGRESSIVE takes the
    same reach (220 yes, 240 / 260 nothing) but stays where the chase ended, never walking back (near 1 to s26
    against GUARD's home at s16). A stance set in the middle of a chase: INFERRED from these."""
    mine = a.path and a.dest is not None and a.dest == a.auto_to
    if a.path and not mine:                 # an order of its own since: not idle, nothing of ours to keep
        a.chase = a.home = a.auto_to = None
        return
    if a.goal is not None or a.building or a.speed <= 0 or 'IMMOBILE' in a.status:
        return
    if a.home is not None and a.chase is None and not a.path:
        a.home = a.auto_to = None           # back home
    if fired:
        return
    if a.stance == 2:                       # HOLD_POSITION: goes after nothing (hold220)
        return
    sight = a.sight
    c = a.chase
    if c is not None and c.alive and peers.side_sees(a.owner, c) and \
            math.hypot(c.x - a.x, c.y - a.y) - c.radius <= sight:
        if not a.path:                      # got there and it is still out of reach: after it again
            peers.send(a, (c.x, c.y), reach=peers.reach(a, c))
            a.auto_to = a.dest
        return
    a.chase = None
    if 'YES' not in a.acquire or world.frame_now() < IDLE_SCAN_FROM:
        near = []                           # AutoAcquireEnemiesWhenIdle NO / none, or the opening frame: nothing
    for dist, t in near:
        if dist - t.radius > sight:
            break                           # sorted by centre; a radius over 0 only cuts more
        if not simtarget.takes_by_itself(a, t, peers) or not peers.side_sees(a.owner, t) or 'NON_AUTOACQUIRABLE' in t.status:
            continue
        if not any(peers.can_hit(w, t) and not peers.shot_blocked(a, t, w) for w in a.weapons):
            continue                        # bench engine_seal row: a target behind a structure is not gone after
        if a.home is None:
            a.home = (a.x, a.y)
        a.chase = t
        world.used.add('acquire')
        peers.send(a, (t.x, t.y), reach=peers.reach(a, t))
        a.auto_to = a.dest
        return
    if a.stance == 1:                       # AGGRESSIVE: stays where the chase ended (agg220)
        a.home = None
    if a.home is not None and (a.path or math.hypot(a.home[0] - a.x, a.home[1] - a.y) > 1.0):
        if a.dest != a.home:
            peers.send(a, a.home)
            a.auto_to = a.dest
