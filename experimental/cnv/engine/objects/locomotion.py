"""L2 locomotion (ADR 0029, docs/engine/sim-layers.md): putting a body on its way -- the way's end and the route.

`go_to` holds no command state (no mode, no target: the command layer's order_move sets those and comes here). It
reaches the world only through simworld.WORLD_API; the frame-mover registry and the toppled bodies are handed in by
the caller (Sim.send). The per-frame driving along the way (Sim.move) comes here at step 8; turning in place (`turn`) has.
"""
import math

import engine.data.units as simunits
import engine.modules.locomotor as locomotor
import engine.objects.jet as simjet
import engine.objects.topple as simtopple


def go_to(world, b, target, reach, face, frame_movers, topples):
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
        o.alive and simtopple.crosses(b, o, a, z, world.own) for o in topples if o is not b
        for a, z in zip(points, points[1:])))
    if b.frame_move:
        if not b.path:
            b.drive_speed = 0.0
        frame_movers[b.name] = b
    else:
        frame_movers.pop(b.name, None)
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
