"""L2 locomotion (ADR 0029, docs/engine/sim-layers.md): putting a body on its way -- the way's end and the route.

`go_to` holds no command state (no mode, no target: the command layer's order_move sets those and comes here). It
reaches the world only through simworld.WORLD_API (the frame-mover registry and the toppled bodies too); whoever
sends a body calls it. The driving along the way (`drive`, `turn`) is Sim.move's past its gates, `crush` its tail.
"""
import math

import numpy as np

import engine.data.units as simunits
import engine.modules.locomotor as locomotor
import engine.objects.jet as simjet
import engine.objects.topple as simtopple
import engine.world.handle as simworld
from engine.kernel import interfaces


def go_to(world, b, target, reach=0.0, face=None):
    """Put b on a way to target (a point, or a waypoint / area name); face: the facing (radians) to turn to at the
    way's end (move), None for none -- a new way drops an old one's. From standing it first turns in place toward
    its way (move, turn), whoever gave the order."""
    if b.guessed:                               # its speed matters now: say when it is only a guess
        world.guessed.add(f'{b.template}: {", ".join(b.guessed)}')
    if not b.alive or b.speed <= 0:
        return
    b.face = face
    p = world.point(target) if isinstance(target, str) else target
    if p is None:
        world.note('卡住', f'{world.label(b)} 找不到要去的地方 {target}')
        return
    path = world.ground.within(b.surface, (b.x, b.y), p, reach) if reach else None
    stands = False
    if path is None:
        path = world.ground.route(b.surface, (b.x, b.y), p, closest=True)
        stands = path == []
    if not b.path:
        locomotor.write(world, b, set_off=world.frame_now())
    b.dest = p
    if path is None:
        world.note('卡住', f'{world.label(b)} 到不了 {target if isinstance(target, str) else "目标"}'
                          f'（{b.surface} 没有路）')
        b.path = []
        return
    if stands and b.dest != b.stood_for:
        # walled in, where it stands is the nearest it gets: it stays (bench engine_seal move); not stuck
        world.note('够不着', f'{world.label(b)} 走不到 {target if isinstance(target, str) else "目标"}，'
                            f'原地就是能到的最近处，站着')
        locomotor.write(world, b, stood_for=b.dest)
    jet = simjet.start(world, b, path)
    points = [(b.x, b.y)] + path
    locomotor.write(world, b, jet_motion=jet, frame_move=jet is not None or any(
        o.alive and simtopple.crosses(b, o, a, z, world.own) for o in world.topples if o is not b
        for a, z in zip(points, points[1:])))
    if b.frame_move:
        if not b.path:
            locomotor.write(world, b, drive_speed=0.0)
        world.frame_movers[b.name] = b
    else:
        world.frame_movers.pop(b.name, None)
    b.path = path
    world.change()


def turn(world, b, want, dt, within=0.0):
    """Turn b in place toward the facing `want` (radians) for up to dt seconds, at its turn_rate a frame (bench
    airev1t / airevgt / airevat, A round 227, tests/test_turn_rate.py: 360 / the Locomotor's TurnTimeSeconds a
    second from the order frame; TurnThresholdHS is not seen -- a 51 deg turn is made in place too). Stops
    `within` degrees short (DRIVE_WITHIN: the rest is made as it drives). Returns the seconds it took (dt: not
    there yet). Turning to its face (within 0) drops the face once it is reached: Unit.moving is false from then.
    turn_rate None (aircraft, no locomotor): at once."""
    off = math.degrees(math.atan2(math.sin(want - b.angle), math.cos(want - b.angle)))
    need = abs(off) - within
    if need <= 1e-9 or b.turn_rate is None:
        if within <= 0:
            b.angle, b.face = want, None
        return 0.0
    per_frame = b.turn_rate / simunits.LIFE_FPS
    frames = math.ceil(need / per_frame - 1e-9)
    took = frames / simunits.LIFE_FPS
    if dt <= 0:
        return dt
    if took <= dt + 1e-9:
        if within <= 0:
            b.angle, b.face = want, None
        else:
            a = b.angle + math.radians(math.copysign(min(abs(off), frames * per_frame), off))
            b.angle = math.atan2(math.sin(a), math.cos(a))
        world.change()
        return took
    a = b.angle + math.radians(math.copysign(b.turn_rate * dt, off))
    b.angle = math.atan2(math.sin(a), math.cos(a))
    world.change()
    return dt


DRIVE_WITHIN = 9.0      # ordered from standing, a unit drives on the frame that starts this near its way (deg;
                        # bench airev1t / airevgt / airevat, A round 227: 8 drove, 10 / 15 did not; INFERRED 9)
BUILD_STEP = 5.0        # a builder on his way (R5) moves in steps this long, to see where he gets within range


def drive(world, b, dt, precise, targets, entry, at_site):
    """Sim.move past its gates: b's tick (precise: a frame mover's frame) along its way. A builder stops where
    at_site(b, walked) says, an attack-mover (targets: Sim.range_targets) where entry (Sim.range_entry) finds a foe.
    None: it did not drive; else (x0, y0, at, stopped): where it set out, the seconds into the tick it stopped
    (None: it goes on), whether entry stopped it."""
    if not b.path:
        locomotor.write(world, b, rolling=False, carry=0.0)
        if b.face is not None:                  # arrived: turns in place to the facing it was given
            turn(world, b, b.face, dt)
        return None
    spent, extra = 0.0, (b.carry if not precise else 0.0)
    locomotor.write(world, b, carry=0.0)
    if not b.rolling and b.jet_motion is None and b.turn_first:     # from standing: turns in place until near its
        # way. Infantry (TestReactiveLocomotorHUMAN, no TurnThresholdHS) walk off at once, turning as they go: bench
        # airevit (A round 231) -- Conscripts' form-up order f26, each moved ~3.2 a frame from f26 on (full speed)
        # while the heading went -180 -135 -90 -72 (45 a frame)
        way = next(((tx, ty) for tx, ty in b.path if (tx, ty) != (b.x, b.y)), None)
        if way is not None:
            spent = turn(world, b, math.atan2(way[1] - b.y, way[0] - b.x), dt, DRIVE_WITHIN)
        if spent >= dt:
            return None
    left = b.speed * (dt - spent + extra)
    if precise and b.jet_motion is not None:
        left = simjet.distance(world, b)
    elif precise:
        speed, acceleration = simtopple.motion(b.template, world.own)
        base = simunits.stats(b.template, world.own)['speed']
        speed = speed * b.speed / base if speed is not None and base else b.speed
        locomotor.write(world, b, drive_speed=min(speed, b.drive_speed + speed * dt / acceleration)
                        if acceleration else speed)
        left = b.drive_speed * (dt - spent)
    walked, x0, y0, stopped = left, b.x, b.y, False
    reach = None if precise else targets(b)
    while left > 0 and b.path:
        tx, ty = b.path[0]
        d = math.hypot(tx - b.x, ty - b.y)
        step = min(BUILD_STEP, left)
        if b.building and d > step:                 # a builder: in short steps, to see where he reaches it
            b.x += (tx - b.x) * step / d
            b.y += (ty - b.y) * step / d
            left -= step
            if at_site(b, walked - left):
                break
            continue
        if reach and d > 0:                         # an attack-mover stops where it gets a foe in range
            s = entry(b, reach, tx, ty, min(d, left))
            if s is not None:
                b.x += (tx - b.x) * s / d
                b.y += (ty - b.y) * s / d
                left -= s
                stopped = True
                break
        if d <= left:
            b.x, b.y, left = tx, ty, left - d
            b.path.pop(0)
        else:
            b.x += (tx - b.x) * left / d
            b.y += (ty - b.y) * left / d
            left = 0
    at = max(spent + (walked - left) / b.speed - extra, 0.0) if (stopped or not b.path) and b.speed > 0 else None
    if not b.path and not precise and at is not None:   # where in the tick its way ended (Sim.on_the_move)
        locomotor.write(world, b, stops_at=math.floor(world.t / simworld.DT + 1e-6) * simworld.DT + at)
    locomotor.write(world, b, rolling=True)    # it drove this tick: a next leg given at once (follow_due) is driven on, no stop
                            # (bench engine_waypath line / exact: no time lost at the 90 deg corners)
    if (b.x, b.y) != (x0, y0):
        # once it drives, the hull faces its way: the last DRIVE_WITHIN of a turn from standing, a turn on a new way
        # while it drives (bench airevgt f170: no stop, 24 deg a frame on moving frames) and the bends taken at once
        # (INFERRED; bench engine_hull, round 187: no reversing)
        b.angle = math.atan2(b.y - y0, b.x - x0)
    if not b.path and b.follow is not None and not precise and b.speed > 0:
        locomotor.write(world, b, carry=min(left / b.speed, dt))
    if not b.path and b.face is not None:      # arrived this tick: from the next frame on it turns
        rate = b.drive_speed if precise and b.jet_motion is None else b.speed
        turn(world, b, b.face, (left / rate if rate > 0 else 0.0) - 1.0 / simunits.LIFE_FPS)
    if b.building:
        at_site(b, walked - left)
    return x0, y0, at, stopped


def crush(world, b, x0, y0, precise, pool, attached, topples, destroy):
    """R9 (docs/engine/crush.md, bench 11-06 engine_crush), the tail of b's drive from (x0, y0) (precise: a frame
    mover's frame): a crusher (interfaces.Crush) kills what its footprint passes over that is a lower level -- strictly
    greater kills, 20 against 20 and 30 against 30 live; the crushed does not step aside and lies its SlowDeath out
    (`destroy`'s death CRUSHED, B5a). The segment passing within the CRUSHED's own radius of its centre (FITTED to two
    readings: Hammer / conscript at frame 43, Apocalypse / guardian at 69 -- touching at the radii's sum would be ~12
    and ~30 frames earlier still; the simulator has no acceleration). Whose units: the crusher's enemies' only
    (INFERRED: one's own / neutral units not measured). `pool`: Sim.move's, new each move, filled at its first crusher
    that drives (the crushable ones, not `attached`, as arrays: a big map's tanks all drive). A prop (`topples`) is
    toppled only frame by frame: a way across one is a frame mover's (go_to), with or without the model."""
    if b.crusher <= 0 or b.surface != 'ground' or (b.x, b.y) == (x0, y0):
        return
    dx, dy = b.x - x0, b.y - y0
    seg = dx * dx + dy * dy
    if not pool:
        low = [o for o in world.bodies.values() if o.alive and o.crushable is not None and not o.scenery  # living()
               and not o.topple and o.surface == 'ground' and o.serial not in attached]
        pool += [low, np.array([o.x for o in low]), np.array([o.y for o in low]),
                 np.array([o.radius for o in low]), np.array([o.crushable for o in low])]
    low, ox, oy, orad, olevel = pool
    if low:
        k = np.clip(((ox - x0) * dx + (oy - y0) * dy) / seg, 0.0, 1.0) if seg else np.zeros(len(low))
        near = np.hypot(ox - (x0 + k * dx), oy - (y0 + k * dy)) <= orad
        for j in np.nonzero(near & (olevel < b.crusher))[0]:
            o = low[j]
            if o is b or not o.alive or not world.enemy(b.owner, o.owner):
                continue
            world.used.add('crush')
            o.set_last_damage(b.owner, b)
            destroy(o, f'被 {world.label(b)} 压死', death='CRUSHED')
    for o in topples if precise else ():
        if o.alive and not o.toppled and o.crushable is not None and b.crusher > o.crushable and \
                simtopple.crosses(b, o, (x0, y0), (b.x, b.y), world.own):
            o.find(interfaces.Topple).knock(world.frame_now(), b.drive_speed / simunits.LIFE_FPS)
