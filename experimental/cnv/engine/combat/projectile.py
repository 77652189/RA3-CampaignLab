"""ProjectileNugget (step N1): a straight-line shell flies, its damage fixed at launch, and lands frames later."""
import math

from engine.combat.registry import accumulate, nugget
from engine.kernel import interfaces

# a weapon with any of these flies no shell yet: its effects are dealt as a direct hit (the old fallback)
COMPOUND = ('suppression', 'hit_modifiers', 'line', 'emp_seconds', 'strip_max_health', 'sd', 'dot', 'contained',
            'special_powers', 'attach', 'lift')
# Context.speed's two non-speed answers (host.straight_speed). A Bezier rocket lands a fixed time after launch whatever
# the distance (docs/engine/missile.md 1: retail V4 at 250 and 450 alike, launch 35-40 frames after the order and
# first hit at 108; INFERRED: the flight's 70 of them); a shell with no flight module never lands (bench E168).
BEZIER, NO_FLIGHT = -1.0, -2.0
BEZIER_FRAMES = 70


def queue(pending, when, target, damage, attacker, weapon, centre=None):
    """A projectile's arrival event on the host's queue, also usable to replay an observed collision.

    Damage is the launch-time snapshot. An explicit collision centre overrides the static target half-height fallback
    (INFERRED). Curved flight cannot make this event yet; an observed arrival does not model flight."""
    pending.append((when, target, damage, attacker, weapon, centre))


def due(pending, now):
    """The arrivals due by frame `now`, in queue order; they leave the queue."""
    out = [hit for hit in pending if now >= hit[0]]
    pending[:] = [hit for hit in pending if now < hit[0]]
    return out


def arrive(hit, hurt, detonate, clear):
    """An arrival: its MetaImpact payload goes off first (detonate, the host's, swappable), then a living target's
    notification clears (clear) and it takes the launch-time damage (a new entry's attacker is the shooter). A shield up
    on the target (engine/modules/shield.py) takes the shell instead: nothing goes off, the notification clears."""
    when, target, damage, attacker, weapon, centre = hit
    away = math.hypot(target.x - attacker.x, target.y - attacker.y)
    if any([m.absorb(when, damage, weapon.get('type'), away) for m in target.find(interfaces.Shield)]):
        clear(target, attacker.serial, weapon.get('weapon_key'))
        return
    detonate(weapon, target, centre, attacker)
    if target.alive:
        clear(target, attacker.serial, weapon.get('weapon_key'))
        accumulate(hurt, target, damage, attacker)


@nugget('Projectile', 'launch')
class Projectile:
    """A straight shell (the host's `speed` > 0) and no compound effect takes the volley over: damage through armor
    and flank at launch, landing int(flat distance / speed) frames later (GUESSED collision boundary, rechecked for
    the two probe distances: full distance steps before impact; no fitted per-distance delays), or this frame on zero
    steps. Any other shell is a gap and the volley lands as a direct hit."""

    def payload(self, weapon):
        return weapon.get('projectile') or None

    def apply(self, context, projectile):
        speed = context.speed(projectile)
        w = context.weapon
        if speed == NO_FLIGHT:
            return True
        if (speed == BEZIER or speed > 0) and not any(w.get(k) for k in COMPOUND):
            t, by = context.target, context.by
            frames = BEZIER_FRAMES if speed == BEZIER else int(math.hypot(t.x - by.x, t.y - by.y) / speed)
            # GUESSED until dynamic-armor bench: snapshot scalars at launch (the flank too: bench engine_inform_ai,
            # the side-facing miners' 68 %, from the launch)
            damage = context.n * w['dmg'] * by.dealt * context.hit(t, w['type'])
            if frames:
                context.queue_hit(context.world.frame_now() + frames, t, damage, by, w)
            else:
                context.detonate(w, t, attacker=by)
                context.clear_notice(t, by.serial, w.get('weapon_key'))
                context.add(t, damage)
            return True
        context.gap('ProjectileNugget', '仅无复合效果的直线弹飞行已建模；曲线弹/复合弹/自制弹体待核')
        return False
