"""L5 unit orders: what a unit is told to do and how its standing orders run on (ADR 0029, docs/engine/sim-layers.md).

The order entries set a body's mode and goal and hand the walk to L2 (`peers.send`): a plain or attack move
(`order_move`, a group's `order_group`), an attack (`order_attack`), an engineer's capture (`order_capture`), a guard,
stop / stand, a waypoint path (`order_follow`, `path_start`, `path_next`, `follow_leg`); a stance and auto-acquire are
the unit's AIUpdate's (engine/modules/aiupdate.py). The dues are their frame parts:
a capture at the building's side, the next leg of a path (`capture_due`, `follow_due`). A run off the map is
engine.orders.ability's, a hunt engine.orders.hunt's, a sequential script engine.orders.seq's.
The fight (`fight`, once a tick) is the attack state machine: a team attack goes on to the next member, each armed
body aims (L3 `aim`) and fires, rounds a blocked line, and chases by itself (`chase_step`: an attack-mover's
`attack_chase`, anyone else's `idle_chase`).
All over the world it is given (simworld.WORLD_API only). Its host's other parts come in as `peers` (`Peers`, the
names in PEERS only, read when used): L2 bodies (modify, engineer_entry, the garrison; a walk is
simlocomotion.go_to's, a goal's spot engine.objects.path's, a deletion the kernel World's), L3 targeting and fire (reach, fight_field, aim, can_hit,
in_range, shot_blocked, fire_spot, side_sees, the unshot templates and AI sides: engine.orders.target's), L4 money (wallet), the team
registry (members, team_targets) and the order queues the scripts fill (seq, hunts). The fight's per-tick state on the host
(WRITES: seen, firing, volleys, chilling, mid_aims, the fire obstacles, the field) is reset through `peers` too --
the only names it may set. This module never imports them. The loan serves engine.orders.ability,
engine.orders.hunt and engine.orders.seq too (their PEERS).
"""
import math

import numpy as np

import engine.data.units as simunits
import engine.objects.locomotion as simlocomotion
import engine.objects.path as simpath
from engine.kernel import interfaces
from engine.modules import locomotor, weaponset
from engine.orders import ability as simability
from engine.orders import target as simtarget
from engine.world.handle import GRID, inside

CAPTURE_REACH = 20.0           # R4: an engineer this far outside a building's round is at its side (a guess)
ARRIVE = 1.5 * GRID             # a plain move that ends farther than this from where it was sent stopped short (held_up)
# an idle unit takes nothing by itself in the mission's first logic frame (bench 11-15 engine_dam BR: a bear 60 from an
# enemy conscript, NO_ATTACK from 0.1 s = frame 2, never left its 8-half start square; the simulator had it chase from
# frame 1 and stand at the conscript's feet by frame 15). INFERRED: the program's first idle scan not read -- 2 is the
# least the bench allows; with one acquisition pass a tick, any value up to the second tick's frame (8) acts the same
IDLE_SCAN_FROM = 2

WRITES = frozenset({'_field', '_fire_obstacles', 'chilling', 'firing', 'mid_aims', 'seen', 'volleys'})
PEERS = frozenset({'act', 'engineer_entry', 'garrison', 'hunts', 'powers_off', 'reach', 'send', 'seq', 'short_of_power',
                   'toggles_of', 'wallet', 'production',
                   'aim', 'can_hit', 'fight_field', 'fire_spot', 'in_range', 'members', 'shot_blocked',
                   'side_sees', 'ai', 'team_targets', 'unshot', 'relation',
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


def order_move(world, peers, b, where, attacking, given=(), skip=(), face=None, on_grid=False, exact=False):
    """A plain move (attacking: an attack-move). The spot is adjusted first (free_spot: the goal kept off the spots
    other units hold; on_grid, for a unit sent to a point -- MOVE_NAMED_UNIT_TO, a team's or a selection's move --
    also snapped to the grid, bench engine_drop; other moves keep their exact point, INFERRED); `given` are spots
    already handed out to a group being ordered, `skip` that group (its members' old goals are dropped first).
    face: the facing (radians) it turns to once there (the AI's form-up slots; send). exact: not adjusted at all
    (the AI's crush move onto its target: bench aicrush1, a mate's spot beside the guard moved it 20-40 aside and
    the tank stopped short of him)."""
    if b:
        simability.stop_flee(b)             # INFERRED: any move order takes the run over, as STOP does
        m = b.aiupdate                      # ... and a waypoint path (order_follow sets it again after its legs)
        m.follow = m.ground_fire = None     # ... and a fire at the ground
        m.mode, m.ordered = 'attack' if attacking else 'move', False
        p = world.point(where) if isinstance(where, str) else where
        if p is not None and b.alive and b.speed > 0 and not exact:
            spot = simpath.free_spot(world, b, simpath.goal_off_nodes(world, b, p),
                                     simpath.claims(world, b, skip) + list(given), on_grid)
            where = where if spot == p else spot
        simlocomotion.go_to(world, b, where, face=face)
        m.move_to = b.dest if not attacking else None


def order_group(world, peers, bodies, where, attacking, on_grid=False):
    """A move order to several units at once (a team's MOVE_TEAM_TO, a selection's click): each mover sent, in turn,
    to its spot of the group (simpath.formation_spots), off the spots already held and handed out to the group."""
    movers = [b for b in bodies if b and b.alive and b.speed > 0 and 'IMMOBILE' not in b.status]
    p = world.point(where) if isinstance(where, str) else where
    if len(movers) < 2 or p is None:
        for b in bodies:
            order_move(world, peers, b, where, attacking, on_grid=on_grid)
        return
    world.used.add('group move')
    given = []                                  # (x, y, radius) spots handed out to the group so far
    foot = [b for b in movers if 'INFANTRY' in b.kinds]     # the block's men skip the whole group, the rest only
    rest = [b for b in movers if b not in foot] if len(foot) >= 2 else movers   # each other: a man held up short
    for b, q in simpath.formation_spots(world, movers, p):  # of his spot still holds where he stands (review 1121ll #1)
        order_move(world, peers, b, q, attacking, given, rest if b in rest else movers, on_grid=on_grid)
        given.append(tuple(b.dest or (b.x, b.y)) + (b.radius,))


def held_up(b):
    """A plain move whose way ended short of where it was sent (blocked: a wall across the street) is still on
    that move: it neither fires nor goes after anyone until its next order. Bench 2026-11-07 `a4 demoeng`: the
    opening demo's pair, sent to the engineer's clear mark and stopped by the ice ~157 from him (centre to centre,
    in the simulator), never shot him in the 2 s before their turn order; the simulator, counting them idle once
    stopped, had him dead at 61.7 s. INFERRED (RA3's AI move state not read); not told apart on the bench: that
    they stop farther off than the simulator's wall lets them (out of reach)."""
    left, off = locomotor.progress(b)           # off > ARRIVE: dest is not None, nor move_to
    return b.mode == 'move' and not left and b.goal is None and b.dest == b.move_to and off > ARRIVE


def _relation(world, a, b):
    """How a's owner stands to b's (the host's relation, reached here only)."""
    return world.relation(a.owner, b.owner)


def _target(world, target):
    """An order's target: an object the giver picked, given as it is (the 11-19 same-name sweep: read again by its
    name, a script reference of that name took its place), or a name, read as the world reads it (Sim.body)."""
    return world.body(target) if isinstance(target, str) else target


def order_attack(world, peers, b, target_name, force=False):
    """True where `b` goes for the target (already on it too), False where the order is turned down: a unit or target
    missing or dead, or one of its own side or a neutral one without force (review 11-19 m: the port read a success
    there)."""
    world.used.add('attack')
    target = _target(world, target_name)
    if b and target and not force and (_relation(world, b, target) in ('ALLIES', 'NEUTRAL')
                                       or 'SIMPLE_OBJECT_PROP' in target.kinds):
        return False    # bench 11-13 engine_acts flow 友血: NAMED_ATTACK_NAMED on one of its own side, no shot (d115
        #                 13: FORCE_ATTACK_NAMED is the order that takes any relation); a neutral wall, gate or rock
        #                 likewise (11-25 engine_a1gate h, review 135 ③; INFERRED for other shooters than Tanya); an
        #                 enemy's SIMPLE_OBJECT_PROP (a parked car) too, NOT_AUTOACQUIRABLE or not (engine_a1toll r)
    if not (b and target and target.alive and b.alive):
        return False
    walk = b.goal is not target or b.mode != 'attack' or not b.aiupdate.ordered   # a goal the AI's pursuit set
    #                                                       alone, after a ground fire or attack-move: not on it (jj #1, kk #2)
    b.aiupdate.command('attack', target)
    if walk:
        b.aiupdate.follow = None
        simlocomotion.go_to(world, b, (target.x, target.y), reach=peers.reach(b, target))
    return True


def order_capture(world, peers, b, target_name):
    """R4: NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED with Command_CaptureBuilding: the engineer goes to the
    building; at its side it takes it (capture_due)."""
    world.used.add('capture')
    target = _target(world, target_name)
    if b and b.alive and target and target.alive and peers.engineer_entry(b, target):
        b.goal, b.mode = target, 'capture'
        simlocomotion.go_to(world, b, (target.x, target.y))
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
        if rule.get('bridge') or _relation(world, g, b) == 'ALLIES':
            # a bridge's gatehouse, whoever owns it, mends its bridge (engine_bridgefix a run 2: the owner, neutral, kept; an enemy's INFERRED)
            fix = getattr(g.find(interfaces.Body), 'manager', None) or g.find(interfaces.Body)
            if fix.health() >= fix.max_health():
                # engine_engineer:b: full-health allies keep their owner/HP
                # and all three nations' engineers survive (a whole bridge's too: engine_bridgefix b). Travel INFERRED.
                b.goal, b.mode, b.path = None, 'move', []
                continue
            fix.attempt_healing(math.inf)
            world.note('修理', f'{world.label(b)} 修复 {world.label(g)}')
            world.world.remove(b, '进楼修理')
            world.change()
            continue
        g.owner = b.owner
        world.note('占领', f'{world.label(b)} 占下 {world.label(g)}，归 {world.who(b.owner)}')
        m = g.find(interfaces.Deposit) if g.modules else None
        if m is not None:                               # engine/modules/deposit.py (step M4)
            peers.wallet.credit(b.owner, m.capture(world.frame_now()))
        world.world.remove(b, '进楼占领')
        world.change()


def order_guard(world, peers, b, area):
    world.used.add('guard')
    if b:
        b.aiupdate.follow = None
        if not inside(world.areas[area], b.x, b.y):
            simlocomotion.go_to(world, b, area)


def order_stop(b):
    if b:
        locomotor.write(None, b, path=[], rolling=False, carry=0.0)  # a move this frame sets off from standing,
        b.aiupdate.follow = None            # not on the old leg's carry (review 1121kk #3; INFERRED, not benched)
        b.aiupdate.command('stop')
        simability.stop_flee(b)             # a later order takes the run over (engine_runoffmap d; the status stays)


def stand(b):
    """Its order dropped, nothing new: idle where it is (the AI's command 5: l2_scripts1 3, 6)."""
    locomotor.write(None, b, path=[], rolling=False, carry=0.0)     # as order_stop
    b.aiupdate.move_to, b.aiupdate.follow = None, None
    b.aiupdate.command('idle')


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
    n = len(movers)
    cx, cy = sum(b.x for b in movers) / n, sum(b.y for b in movers) / n
    start = path_start(world, label, (cx, cy)) if start is None else start
    if start is None or start not in world.waypoints:
        for b in movers:
            world.note('卡住', f'{world.label(b)} 找不到路 {label}')
        return
    how = {'label': label, 'at': start, 'attacking': attacking, 'exact': exact, 'team': as_team}
    if as_team and n > 1:
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
            b.aiupdate.follow = how
    else:
        for b in movers:
            order_move(world, peers, b, how['at'], how['attacking'])
            b.aiupdate.follow = dict(how, team=False)


def follow_due(world, peers):
    """The path followers that got where their leg went (no way left, not fighting): on to the next waypoint,
    or off the path at its end. One waypoint per tick at most."""
    done = set()
    for b in world.living():
        how = b.follow
        if how is None or id(how) in done:
            continue
        group = [o for o in world.living() if o.follow is how] if how['team'] else [b]   # a team: its first member
        if all(locomotor.progress(o)[0] or o.engaged or o.resume is not None or isinstance(o.goal, type(o)) for o in group):  # there
            continue                        # moves it on; resume: turned aside to fight (attack_chase), the leg not done
        nxt = path_next(world, how['at'])
        if nxt is None or nxt not in world.waypoints:
            for o in group:
                o.aiupdate.follow = None
            continue
        leg = dict(how, at=nxt)
        done.add(id(leg))
        follow_leg(world, peers, group, leg)


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
    magnets = [(b, g) for b in live if b.modules for g in b.find(interfaces.Magnet)]
    for a in armed:     # a black hole on draws a shooter near it (engine/modules/magnet.py); its attack order is kept
        m = a.aiupdate  # aside (`drawn`) and taken up again once nothing draws it (review 109 #1, readings: s42-48)
        pull = next((b for b, g in magnets if g.draws(a, _relation(world, b, a) == 'ENEMIES')), None)
        if pull is not None and a.goal is not pull:
            m.drawn = a.goal if m.ordered and isinstance(a.goal, type(a)) else None
            order_attack(world, peers, a, pull, force=True)
        elif pull is None and m.drawn is not None:
            back, m.drawn = m.drawn, None   # not over an order given since (a move, another attack; review 1125 M)
            if m.ordered and isinstance(a.goal, type(a)) and a.goal.find(interfaces.Magnet):
                order_attack(world, peers, a, back, force=True)
    for a in armed:
        m = a.aiupdate
        m.engaged = False
        if held_up(a):                 # stopped short on a plain move: still moving (DEMO_KILL)
            continue
        got = peers.aim(a, targets, aimable, tx, ty)
        if got is None:
            chase_step(world, peers, a, False, [])
            continue
        fired, d, idx = got
        g = a.goal
        if not fired and isinstance(g, type(a)) and g.alive and not a.path and g.serial in aimable and \
                (m.spot is None or m.spot[0] != g.serial or math.hypot(g.x - m.spot[1], g.y - m.spot[2]) > 150) and \
                any(peers.can_hit(w, g) and peers.shot_blocked(a, g, w) for w in a.weapons) and \
                not any(peers.can_hit(w, g) and peers.in_range(a, g, w) and not peers.shot_blocked(a, g, w)
                        for w in a.weapons):
            m.spot = (g.serial, g.x, g.y)          # told to attack, the line blocked: round to a clear spot
            p = peers.fire_spot(a, g)
            if p is not None:
                world.note('绕位', f'{world.label(a)} 打不着 {world.label(g)}（中间有建筑），绕到 ({p[0]:.0f},{p[1]:.0f})')
                simlocomotion.go_to(world, a, p)
        chase_step(world, peers, a, fired, [(d[j], targets[idx[j]]) for j in np.argsort(d, kind='stable')])
    if peers.firing or peers.volleys:
        world.used.add('combat')
        assist(world, peers, live)
    if peers.chilling:
        world.used.add('freeze')


def assist(world, peers, live):
    """The tick's firing notifiers call their friends (engine/modules/assist.py): up to `most` callable ones, nearest
    first, not firing themselves, each answering with its response module's weapon line -- its hit modifiers (the link
    guns' boost, simunits: an ally of the one template) go on the caller for their Duration (world.modify). One holding
    NO_ATTACK answers nothing (bench 11-22 engine_attackassist:c: on / off targets both 70 at s30; review xx #5)."""
    shooters = list({a.serial: a for _, _, a in peers.firing + peers.volleys}.values())
    busy = {a.serial for a in shooters}
    for a in shooters:
        for n in a.find(interfaces.AssistNotify):
            near = sorted(((math.hypot(f.x - a.x, f.y - a.y), f) for f in live if f is not a and f.alive and
                           f.serial not in busy and 'NO_ATTACK' not in f.status and
                           f.find(interfaces.AssistResponse)), key=lambda p: p[0])
            called = [f for d, f in near if n.callable(f, _relation(world, a, f), d)][:n.data.most]
            for f in called:
                for r in f.find(interfaces.AssistResponse):
                    if r.data.tag == n.data.response:
                        respond(world, peers, f, r.data.ordering, a)


def respond(world, peers, f, ordering, a):
    """f's weapon line of `ordering` hits `a` with its hit modifiers (their target filter read)."""
    own = world.own
    sets = weaponset.read(simunits.module_blocks(f.template, 'WeaponSetUpdate', own))
    names = [x.template for d in sets for s in d.slots for x in s.lines if x.ordering == ordering]
    w = simunits.weapon_table(own).get(names[0], {}) if names else {}
    xml = world.xml_of(f.template)
    for e in w.get('hit_modifiers', []):
        mid, flt = (e['modifier'], e.get('target_filter')) if isinstance(e, dict) else (e, None)
        mod = simunits.modifier(xml, mid)
        if mod and mod['frames'] and (not flt or a.template.lower() in flt.get('include', ())):
            a.auras_on[mid] = (world.frame_now() + mod['frames'], xml)
            world.world.modify(a)


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
    m = a.aiupdate
    if m.chase is not None and a.path and a.dest != m.auto_to:      # an order since: its own way, not ours
        m.forget()
    if a.building or a.speed <= 0 or 'IMMOBILE' in a.status or fired:
        return
    c = m.chase
    if c is not None and c.alive and peers.side_sees(a.owner, c) and \
            math.hypot(c.x - a.x, c.y - a.y) - c.radius <= a.sight:
        if not a.path:                      # got there and it is still out of reach: after it again
            simlocomotion.go_to(world, a, (c.x, c.y), reach=peers.reach(a, c))
            m.auto_to = a.dest
        return
    m.chase = None
    for dist, t in near:
        if dist - t.radius > a.sight:
            break                           # sorted by centre
        if not simtarget.takes_by_itself(a, t, peers) or not peers.side_sees(a.owner, t) or 'NON_AUTOACQUIRABLE' in t.status:
            continue
        if not any(peers.can_hit(w, t) and not peers.shot_blocked(a, t, w) for w in a.weapons):
            continue
        if m.resume is None:
            m.resume = a.dest
        m.chase = t
        world.used.add('acquire')
        simlocomotion.go_to(world, a, (t.x, t.y), reach=peers.reach(a, t))
        m.auto_to = a.dest
        return
    if m.resume is not None:                # nothing left: on to where the move was going
        r, m.resume, m.auto_to = m.resume, None, None
        simlocomotion.go_to(world, a, r)


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
    m = a.aiupdate
    mine = a.path and a.dest is not None and a.dest == m.auto_to
    if a.path and not mine:                 # an order of its own since: not idle, nothing of ours to keep
        m.chase = m.home = m.auto_to = None
        return
    if a.goal is not None or a.building or a.speed <= 0 or 'IMMOBILE' in a.status:
        return
    if m.home is not None and m.chase is None and not a.path:
        m.home = m.auto_to = None           # back home
    if fired:
        return
    if a.stance == 2:                       # HOLD_POSITION: goes after nothing (hold220)
        return
    sight = a.sight
    c = m.chase
    if c is not None and c.alive and peers.side_sees(a.owner, c) and \
            math.hypot(c.x - a.x, c.y - a.y) - c.radius <= sight:
        if not a.path:                      # got there and it is still out of reach: after it again
            simlocomotion.go_to(world, a, (c.x, c.y), reach=peers.reach(a, c))
            m.auto_to = a.dest
        return
    m.chase = None
    if 'YES' not in a.acquire or 'NO_AUTO_ACQUIRE' in a.status or world.frame_now() < IDLE_SCAN_FROM:
        near = []                           # AutoAcquireEnemiesWhenIdle NO / none (or a script's NO_AUTO_ACQUIRE:
                                            # A310 statusbits n), or the opening frame: nothing
    for dist, t in near:
        if dist - t.radius > sight:
            break                           # sorted by centre; a radius over 0 only cuts more
        if not simtarget.takes_by_itself(a, t, peers) or not peers.side_sees(a.owner, t) or 'NON_AUTOACQUIRABLE' in t.status:
            continue
        if not any(peers.can_hit(w, t) and not peers.shot_blocked(a, t, w) for w in a.weapons):
            continue                        # bench engine_seal row: a target behind a structure is not gone after
        if m.home is None:
            m.home = (a.x, a.y)
        m.chase = t
        world.used.add('acquire')
        simlocomotion.go_to(world, a, (t.x, t.y), reach=peers.reach(a, t))
        m.auto_to = a.dest
        return
    if a.stance == 1:                       # AGGRESSIVE: stays where the chase ended (agg220)
        m.home = None
    if m.home is not None and (a.path or math.hypot(m.home[0] - a.x, m.home[1] - a.y) > 1.0):
        if a.dest != m.home:
            simlocomotion.go_to(world, a, m.home)
            m.auto_to = a.dest
