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
# A straight shell hits when it is this far outside the target's bounding circle: every retail straight shell's
# MinTargetDistance (INFERRED as that; bench E250 engine_projupd with engine_shot's shells -- 2 + 5 / 7 / 9 / 11 frames
# at 250-550 for MuzzleVelocity 50, 2 + 17 at 450 for 25, on a Hammer of radius 24.4 -- puts it between 0.6 and 25.6)
REACH = 5.0


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
    on the target (engine/modules/shield.py) takes the shell instead: nothing goes off, the notification clears.
    The shooter counts as the shield's ally when it has the same owner (review yy #5; another allied player's shell
    is still taken: a gap, the host's relation is not reached from here)."""
    when, target, damage, attacker, weapon, centre = hit
    away = math.hypot(target.x - attacker.x, target.y - attacker.y)
    ally = attacker.owner == target.owner
    if any([m.absorb(when, damage, weapon.get('type'), away, ally) for m in target.find(interfaces.Shield)]):
        clear(target, attacker.serial, weapon.get('weapon_key'))
        return
    detonate(weapon, target, centre, attacker)
    if target.alive:
        clear(target, attacker.serial, weapon.get('weapon_key'))
        accumulate(hurt, target, damage, attacker)


@nugget('Projectile', 'launch')
class Projectile:
    """A straight shell (the host's `speed` > 0) and no compound effect takes the volley over: damage through armor
    and flank at launch, landing after the steps of `speed` it takes to come within the target's radius + REACH (the
    flat distance; INFERRED collision boundary), or this frame on zero steps. Any other shell is a gap and the volley
    lands as a direct hit."""

    def payload(self, weapon):
        return weapon.get('projectile') or weapon.get('pounce') or None

    def apply(self, context, projectile):
        now = context.world.frame_now()
        if isinstance(projectile, dict):
            return pounce(context, projectile, now)
        speed = context.speed(projectile)
        w = context.weapon
        if speed == NO_FLIGHT:
            return True
        if (speed == BEZIER or speed > 0) and not any(w.get(k) for k in COMPOUND):
            t, by = context.target, context.by
            gap = math.hypot(t.x - by.x, t.y - by.y) - (t.radius or 0.0) - REACH
            frames = BEZIER_FRAMES if speed == BEZIER else max(0, math.ceil(gap / speed))
            # GUESSED until dynamic-armor bench: snapshot scalars at launch (the flank too: bench engine_inform_ai,
            # the side-facing miners' 68 %, from the launch)
            damage = context.n * w['dmg'] * by.dealt * context.hit(t, w['type'])
            if frames:
                context.queue_hit(now + frames, t, damage, by, w)
            else:
                context.detonate(w, t, attacker=by)
                context.clear_notice(t, by.serial, w.get('weapon_key'))
                context.add(t, damage)
            return True
        context.gap('ProjectileNugget', '仅无复合效果的直线弹飞行已建模；曲线弹/复合弹/自制弹体待核')
        return False


def pounce(context, leap, now):
    """A melee ProjectileSelf weapon (the dog's Maul): the shooter itself is the shell. At the shot its own nuggets go
    on (False: the 1 UNRESISTABLE, the hold on the prey); it flies at the WeaponSpeed and its warhead (leap: speed,
    dmg, type, weapon_key) lands after the frames it takes to come within the prey's radius + REACH, the shooter
    held still and silent meanwhile (the EMP deadlines, as the Sickle's leap). Bench engine_dogbite a: the leap at 31,
    the 200 at 34 (3 frames: 30 at 125 a second, not the 0.5 s FiringDuration). INFERRED: the shooter put beside its
    prey at the leap (where it lands is not read); the warhead's modifiers (MaulLanded: NO_ATTACK 2 s) put on at the
    leap to run till their Duration after the landing (the leap's own hold covers the flight)."""
    t, by = context.target, context.by
    away = math.hypot(t.x - by.x, t.y - by.y)
    frames = context.frames(max(0.0, away - (t.radius or 0.0) - REACH) / leap['speed'])
    land = now + frames
    for mid in leap['landed']:
        modifier, xml = context.host.modifier(by.template, mid)
        if modifier and modifier['frames'] is not None:
            context.host.wear(t, mid, frames + modifier['frames'], xml)
    damage = context.n * leap['dmg'] * by.dealt * context.hit(t, leap['type'])
    context.queue_hit(land, t, damage, by, dict(type=leap['type'], weapon_key=leap['weapon_key']))
    deadlines = context.emp_until()
    deadlines[by.serial] = max(deadlines.get(by.serial, 0), land)
    if away > 0:
        side = ((t.radius or 0.0) + (by.radius or 0.0)) / away
        by.x, by.y, by.path, by.dest = t.x + (by.x - t.x) * side, t.y + (by.y - t.y) * side, [], None
    return False
