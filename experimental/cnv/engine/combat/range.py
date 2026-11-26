"""L3 weapon reach (ADR 0029, docs/engine/sim-layers.md: targeting and aiming are combat's): how far a weapon reaches
and whether it reaches a target, as pure rules of the weapon and the two bodies -- no world, no state. Generals keeps
them on the Weapon (Weapon::isWithinAttackRange); here they are module functions, read by the host (Sim.reach_of /
Sim.in_range are these) and by the skirmish AI directly (R3 13f-2b: not through the host's loan)."""
import math

from engine.objects.modifier import UNDERSIZE


def reach_of(w):
    """R8: how far weapon w reaches edge to edge: (AttackRange - UNDERSIZE) x the range multiplier (D162 read);
    the minimum range, the height bonus and UseCenterForRangeCheck are not modelled."""
    return max(w['range'] - w.get('undersize', UNDERSIZE), 0.0)


def in_range(a, t, w, d=None):
    """R8: a weapon reaches when the 2D gap between the two bounding circles is within its range (Generals
    Weapon::isWithinAttackRange, FROM_BOUNDINGSPHERE_2D: the centre distance less both radii); `d` the centre
    distance when known. Bench 2026-11-07 engine_acquire: a Guardian (150, radius 23.3) fires at one 180 off.
    An immobile shooter reaches a structure at its centre (A382 checks/engine_a1coil a / d: the tesla coil, 350,
    circle 14.1, fires at a power plant 355 off, not 370 -- the plant's circle 42.4 counts for 11 at most; INFERRED
    for other immobile shooters and structures, mobile ones keep both circles)."""
    if d is None:
        d = math.hypot(t.x - a.x, t.y - a.y)
    near = 0.0 if 'STRUCTURE' in t.kinds and 'IMMOBILE' in a.kinds else t.radius
    return d - a.radius - near <= reach_of(w)


def takes(w, t):
    """Sim.can_hit's anti mask test (its armour test aside): aircraft need ANTI_AIRBORNE, buildings ANTI_STRUCTURE
    or ground, the rest ground or water -- or RA3's ANTI_VEHICLE / ANTI_INFANTRY for a vehicle / infantry off the
    air (bench B 11-24 ailock2: the Rocket Angel's lockdown gun, ANTI_VEHICLE ANTI_INFANTRY alone, locks a Bullfrog;
    the infantry bit INFERRED). No RequiredAntiMask: the SDK's default, not the air."""
    anti = w['anti'] or ('ANTI_GROUND', 'ANTI_WATER', 'ANTI_STRUCTURE')
    if t.surface == 'air':
        return any(a.startswith('ANTI_AIRBORNE') for a in anti)
    if 'STRUCTURE' in t.kinds:
        return 'ANTI_STRUCTURE' in anti or 'ANTI_GROUND' in anti
    return bool({'ANTI_GROUND', 'ANTI_WATER'} & set(anti)) or any(
        f'ANTI_{k}' in anti and k in t.kinds for k in ('VEHICLE', 'INFANTRY'))


def hits(weapons):
    """The domains a body's weapons hit (ai.targets.Thing.hits) from the simulator's anti masks (R3 13f-2d:
    moved from simproxy; read by the proxy player and the skirmish AI). A weapon that writes no RequiredAntiMask has
    the SDK's default, ANTI_GROUND ANTI_WATER ANTI_STRUCTURE (AssetTypeWeaponTemplate.xsd)."""
    out = set()
    for w in weapons:
        anti = w.get('anti') or ('ANTI_GROUND', 'ANTI_WATER')
        for a in anti:
            if a.startswith('ANTI_AIRBORNE'):
                out.add('air')
            elif a == 'ANTI_WATER':
                out.add('water')
            elif a in ('ANTI_GROUND', 'ANTI_STRUCTURE'):
                out.add('ground')
    return frozenset(out)
