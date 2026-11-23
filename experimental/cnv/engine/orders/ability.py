"""L5 the button orders (ADR 0029): a ground power, the Tengu's transform, an unpack, a run off the map (flee_*) -- apart
from engine.orders.order's targeting, chase and moves. Over the world (WORLD_API only); the host by simorder.Peers (PEERS)."""
import math

import engine.data.units as simunits
import engine.objects.locomotion as simlocomotion
import engine.objects.modifier as simmodifier
import engine.objects.toggle as simtoggle
from engine.objects.power import AI_POWERS, UNPACK_POWER, start_reload

PEERS = frozenset({'act', 'garrison', 'powers_off', 'production', 'short_of_power', 'toggles_of'})
FLEE_GONE = 3


def power_refusal(world, peers, b, power, x, y):
    """Why the player's click of `power` on (x, y) for unit b would be refused, None if it goes (order_power). A
    script's cast (engine_skill a-c, w) skips all of this. The click, bench 2026-11-07 engine_skill d (clicked by
    hand, the ice engineer): its reload not over (ready_at: refused 8 s after his cast, went 21 s after); PATHABLE_ONLY
    and the spot not ground he can walk (a point in the sea and one on the cliff refused); within ForbiddenObjectRange
    (32) of the edge of an object that does not move (an ore node, box 33 x 41, refused 75 from its centre and not
    123: its bounding circle 53 + 32 lies between) -- a unit does not count (our own tank 20 / 40 / 60 from the spot,
    inside its 23 radius, the core came all the same; a click right on the tank's centre took nothing, left out);
    MaxCastRange with LIMIT_DISTANCE and the spot farther from him (not measured)."""
    rules = simunits.power_rules(b.template, power, world.own)
    if rules is None:
        return 'not a power of his'
    if b.ready_at.get(power, 0) > world.frame_now():
        return 'reloading'
    if any(peers.powers_off.get((p, power.lower()), 'Available') != 'Available' for p in (b.owner, '<All Players>')):
        return 'disabled'                   # PLAYER_SPECIAL_POWER_AVAILABILITY (INFERRED)
    if 'PATHABLE_ONLY' in rules['flags']:
        g, c = world.ground.grids.get(b.surface, world.ground.grids['ground']), world.ground.cell(x, y)
        if not (0 <= c[0] < g.shape[0] and 0 <= c[1] < g.shape[1] and g[c]):
            return 'not pathable'
    if rules['forbidden'] and any(o is not b and not o.speed
                                  and math.hypot(o.x - x, o.y - y) - o.radius < rules['forbidden']
                                  for o in world.living()):
        return 'too near an object'
    if 'LIMIT_DISTANCE' in rules['flags'] and rules['reach'] and math.hypot(b.x - x, b.y - y) > rules['reach']:
        return 'out of reach'
    return None


def order_power(world, peers, b, power, pos):
    """The player's ground power (simproxy's): (True, None) and cast as the scripts' way does (at a waypoint of its
    own), or (False, why) -- power_refusal."""
    x, y = float(pos[0]), float(pos[1])
    why = power_refusal(world, peers, b, power, x, y) if b and b.alive else 'gone'
    if why:
        world.note('技能', f'{world.label(b) if b else "?"} 用 {power} 不行：{why}')
        return False, why
    spot = f'SIM power spot {len(world.waypoints)}'
    world.waypoints[spot] = (x, y)
    peers.act('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', [b.name, power, spot], None, unit=b)    # b itself casts: by
    # its name, a script reference of that name cast in its place (11-19 same-name sweep S4)
    return True, None


def order_transform(world, peers, b, power):
    """E206: the player's untargeted Tengu transform, the measured button effect. Reload / availability: the player
    power gate (power_refusal); the 15 s reload is XML-derived (INFERRED for this input) -- the bench measured the state
    and locomotor, not a player's cooldown or animation-frame boundaries."""
    if power != 'SpecialPower_JAIV_Transform':
        return False, 'unmeasured self power'
    if not b or not b.alive:
        return False, 'gone'
    if not any(tm['power'] == power for tm in peers.toggles_of(b)):
        return False, 'not a toggle of his'
    if why := power_refusal(world, peers, b, power, b.x, b.y):
        return False, why
    if not simtoggle.press(world, b, 'Command_JAIV_Transform', peers.short_of_power):
        return False, 'not a toggle of his'
    start_reload(world, b, power, world.frame_now() + simunits.power_rules(b.template, power, world.own)['reload'])
    return True, None


def ai_player_power(world, units, command, pos, death_blasts):
    """The skirmish AI's player power `command` cast at `pos` from its living `units` (the structure it needs): the
    bomb queued on `death_blasts` (the world's: L3 fires it, through armor) to land AI_POWERS' `after` frames on.
    Refused with no such structure."""
    p = AI_POWERS.get(command)
    b = next((b for b in units if b.alive and p and b.template == p['needs']), None)
    if b is None or pos is None:
        return False, f'{command}: no {p and p["needs"]}'
    world.used.add('superweapon')
    world.note('技能', f'{world.label(b)} 的 AI 放 {p["power"]} 打 ({pos[0]:.0f}, {pos[1]:.0f})')
    death_blasts.append((world.frame_now() + p['after'], float(pos[0]), float(pos[1]), p['damage'], p['type'],
                         p['radius'], p['affects'].split(), b.owner, b, 1.0, False, None, p['structure']))
    return True, ''


def player_power(world, peers, units, power, pos, via):
    """The player's own press for each of `units` (the command port's power, simproxy's, R3 13e): `via` 'click' casts
    at `pos` (order_power), 'transform' untargeted (order_transform); refused only when every unit's is (why: their
    refusals, sorted, once each)."""
    refused = [why for ok, why in ((order_power(world, peers, b, power, pos) if via == 'click' else
                                    order_transform(world, peers, b, power)) for b in units) if not ok]
    if units and len(refused) == len(units):
        return False, ', '.join(sorted(set(refused)))
    return True, ''


def order_unpack(world, peers, b, p, button=None, where=None, stand=None, here=False, send=True):
    """b drives to point p and turns into its ReplaceSelfSpecialAbility's replacement there (the script's
    NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT with an unpack button).
    button None = the first unpack button of b's CommandSet (AlliedMiner: Command_UnPackAlliedMiner). False when
    b is dead or has no such button. The AI's SimpleExpansion (simai approach) arms it instead: stand = the
    Tactic's Distance (in place of the replacement's stand), here = the structure goes where b stands when it
    first comes within stand of p (at_site), send=False = b is not driven to p (its team's orders walk it)."""
    def real(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    # a bad point or stand is refused before b is touched (review vv P3: the unpack was written, then the note raised)
    if not b.alive or not (isinstance(p, (tuple, list)) and len(p) >= 2 and all(map(real, p[:2]))) or \
            not (stand is None or real(stand)):
        return False
    if button is None:
        sets, _ = simunits._commands(world.own)
        button = next((c for c in sets.get(simunits.command_set(b.template, (), world.own), [])
                       if simunits.command_power(c, world.own) == UNPACK_POWER
                       and simunits.replace_self(b.template, c, world.own)), None)
    got = button is not None and simunits.command_power(button, world.own) == UNPACK_POWER and \
        simunits.replace_self(b.template, button, world.own)
    if not got:
        return False
    own_stand, into = got
    world.used.add('unpack')
    b.building, b.replace = (into, p, own_stand if stand is None else stand), True
    b.unpack_here = here
    if send:
        b.goal, b.mode = None, 'move'
    world.note('技能', f'{world.label(b)} 去 {where or "(%.0f, %.0f)" % tuple(p)} 展开成 {into}'
              + (f'（{stand:g} 内原地）' if here else ''))
    if not peers.production.at_site(b, 0.0) and send:
        simlocomotion.go_to(world, b, p)
    return True


def flee_start(world, peers, b):
    """RunOffMapBehavior (simunits.run_off_map; engine line C round 8, engine_runoffmap a-d, bench 11-06): from the
    order's frame the body walks straight to the waypoint named `RunOffMap` (none: 1000 along its facing), at its
    speed, carrying FLEE_OFF_MAP, and FLEE_GONE frames after it arrives it is removed without a death (not dying).
    The counting scripts' frames give 64064 / 304304 and the 15 frames in the end's area at lag 0, gone 3 (a grid
    of lag 0-4 x gone 0-5 had that one fit). Not modelled: the path (a straight line), a way that cannot be walked,
    flying off. A later move or stop takes the run over (stop_flee, engine.orders.order's)."""
    name = simunits.run_off_map(b.template, world.own)
    if name is None or not b.alive or b.speed <= 0:
        return
    goal = world.waypoints.get(name or 'RunOffMap') or (b.x + 1000.0 * math.cos(b.angle), b.y + 1000.0 * math.sin(b.angle))
    d = math.hypot(goal[0] - b.x, goal[1] - b.y)
    b.flee = (world.frame_now(), b.x, b.y, goal[0], goal[1], d, b.speed / simunits.LIFE_FPS)
    b.path, b.goal, b.mode, b.aiupdate.move_to = [], None, 'idle', None
    b.script_status.add('FLEE_OFF_MAP')
    simmodifier.modify(world, b)
    world.used.add('flee off map')
    world.change()


def flee_due(world, peers, frame):
    """One frame of every runner: its place on the straight line, the removal when its time comes."""
    for b in peers.garrison.run_off():          # emptied transports' RunOffMapWhenDone (garrison._throw)
        flee_start(world, peers, b)
    for b in [b for b in world.living() if getattr(b, 'flee', None)]:
        f0, x0, y0, x1, y1, d, step = b.flee
        k = frame - f0
        walked = min(d, max(0, k) * step) / d if d else 1.0
        b.x, b.y = x0 + (x1 - x0) * walked, y0 + (y1 - y0) * walked
        world.change()                          # (the deletion's own too)
        if walked >= 1.0 and k - math.ceil(d / step - 1e-9) >= FLEE_GONE:
            b.flee = None
            world.world.remove(b, '逃出地图')


def stop_flee(b):
    b.flee = None
