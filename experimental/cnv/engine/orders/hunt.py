"""L5 TEAM_HUNT (ADR 0029): a crew attack-moves to the nearest hostile object, again after each target dies -- apart
from engine.orders.order, whose group move it calls. Over the world (WORLD_API only); the host by simorder.Peers
(PEERS): the crews live on it (Sim.hunts, [movers, target, frame to re-pick at])."""
import math

from engine.orders.order import order_group
from engine.world.handle import CIV

PEERS = frozenset({'hunts'})
HUNT_REPICK = 45                    # frames from a hunted target's death to the crew's next pick (fit, hunt_due)


def hunt_due(world, peers, frame, crew=None):
    """TEAM_HUNT's crews (Sim.act): one with no living target, its re-pick frame come, attack-moves to the
    hostile object (unit or structure, not civilian) nearest its middle. `crew`: a new one (the command port's hunt),
    which takes its members out of any crew they hunted in and picks this frame. Bench 11-14 engine_acts_y hunt: an
    engineer died at s15, the crew by the next one (566 on) at s21; that one died at s29, the crew out of its
    spot at s39 and back past home (s49) for the barracks; another crew's bait died at s13, the next attacked at
    s29 -- HUNT_REPICK 45 frames (3 s) has each a second later, the bench's usual lag (0: the same but the
    second bait 2 s early; 75: 2-3 s late). INFERRED: a fit, the program's re-pick rule not read. A crew's members dying, joining other teams: not followed (the crew as ordered)."""
    if crew is not None:                    # the rest of an old crew hunts on, its target and re-pick kept (review jj #2)
        new = {b.serial for b in crew}
        for h in peers.hunts:
            h[0] = [b for b in h[0] if b.serial not in new]
        peers.hunts.append([crew, None, frame])
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
