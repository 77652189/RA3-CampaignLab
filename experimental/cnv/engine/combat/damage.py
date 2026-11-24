"""DamageNugget (step N1): a direct hit's damage through the victim's armor and the flank scalar."""
import math

from engine.combat.registry import nugget


def tapered(dmg, taper, by, victim):
    """A DamageDealtAtSelfPosition weapon's damage to `victim` (weapon['taper'] = Radius, MinRadius, DamageTaperOff):
    Damage at MinRadius down to DamageTaperOff at Radius by the ground distance from the shooter less the victim's
    bounding circle, clamped (docs/engine/weapons.md, the splash taper). INFERRED: dealt at the shooter's position
    there is no aimed victim to take it whole (bench aigarrbld: a Peacekeeper's 40 took 25 off the plant a shot)."""
    hi, lo, off = taper
    if hi - lo < 1e-3:
        return dmg
    d = min(hi, max(lo, math.hypot(victim.x - by.x, victim.y - by.y) - victim.radius))
    return dmg - (dmg - off) * (d - lo) / (hi - lo)


@nugget('Damage', 'victim')
class Damage:
    """Every volley deals its resolved damage (`dmg`, `type`: the weapon's own, else one warhead's, else its OCL's;
    simunits._resolve) to each victim through its armor, taken and the flank (the host's `scalar`), a zero too: the
    entry still names the shooter."""

    def payload(self, weapon):
        return (weapon['dmg'], weapon['type'], weapon.get('taper'))

    def apply(self, context, payload):
        dmg, damage_type, taper = payload
        victim = context.victim
        if taper:
            dmg = tapered(dmg, taper, context.by, victim)
        context.add(victim, context.n * dmg * context.by.dealt * context.boost * context.hit(victim, damage_type))
