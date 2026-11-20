"""L3 weapon reach (ADR 0029, docs/engine/sim-layers.md: targeting and aiming are combat's): how far a weapon reaches
and whether it reaches a target, as pure rules of the weapon and the two bodies -- no world, no state. Generals keeps
them on the Weapon (Weapon::isWithinAttackRange); here they are module functions, read by the host (Sim.reach_of /
Sim.in_range are these) and by the skirmish AI directly (R3 13f-2b: not through the host's loan)."""
import math

from simmodifier import UNDERSIZE


def reach_of(w):
    """R8: how far weapon w reaches edge to edge: (AttackRange - UNDERSIZE) x the range multiplier (D162 read);
    the minimum range, the height bonus and UseCenterForRangeCheck are not modelled."""
    return max(w['range'] - w.get('undersize', UNDERSIZE), 0.0)


def in_range(a, t, w, d=None):
    """R8: a weapon reaches when the 2D gap between the two bounding circles is within its range (Generals
    Weapon::isWithinAttackRange, FROM_BOUNDINGSPHERE_2D: the centre distance less both radii); `d` the centre
    distance when known. Bench 2026-11-07 engine_acquire: a Guardian (150, radius 23.3) fires at one 180 off."""
    if d is None:
        d = math.hypot(t.x - a.x, t.y - a.y)
    return d - a.radius - t.radius <= reach_of(w)
