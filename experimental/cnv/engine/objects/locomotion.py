"""L2 locomotion (ADR 0029, docs/engine/sim-layers.md): putting a body on its way -- the way's end and the route.

`go_to` holds no command state (no mode, no target: the command layer's order_move sets those and comes here). It
reaches the world only through simworld.WORLD_API; the frame-mover registry and the toppled bodies are handed in by
the caller (Sim.send). The per-frame driving along the way (Sim.move) comes here at step 8.
"""
import engine.objects.jet as simjet
import engine.objects.topple as simtopple


def go_to(world, b, target, reach, face, frame_movers, topples):
    """Put b on a way to target (a point, or a waypoint / area name); face: the facing (radians) to turn to at the
    way's end (move), None for none -- a new way drops an old one's. From standing it first turns in place toward
    its way (move, Sim.turn), whoever gave the order."""
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
        b.set_off = world.frame_now()
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
        b.stood_for = b.dest
    b.jet_motion = simjet.start(world, b, path)
    points = [(b.x, b.y)] + path
    b.frame_move = (b.jet_motion is not None or any(o.alive and simtopple.crosses(b, o, a, z, world.own)
                                              for o in topples if o is not b
                                              for a, z in zip(points, points[1:])))
    if b.frame_move:
        if not b.path:
            b.drive_speed = 0.0
        frame_movers[b.name] = b
    else:
        frame_movers.pop(b.name, None)
    b.path = path
    world.change()
