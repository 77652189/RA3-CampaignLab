"""L5 the button orders (ADR 0029): a ground power, the Tengu's transform, an unpack -- apart from engine.orders.order's
targeting, chase and moves. Over the world (WORLD_API only); the host through simorder.Peers, reading only PEERS."""
import math

import engine.data.units as simunits
from engine.objects.power import UNPACK_POWER, start_reload

PEERS = frozenset({'act', 'powers_off', 'production', 'send', 'toggle_press', 'toggles_of'})


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
    why = power_refusal(world, peers, b, power, b.x, b.y)
    if why:
        return False, why
    if not peers.toggle_press(b, 'Command_JAIV_Transform'):
        return False, 'not a toggle of his'
    start_reload(world, b, power, world.frame_now() + simunits.power_rules(b.template, power, world.own)['reload'])
    return True, None


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
    if not b.alive:
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
        peers.send(b, p)
    return True
