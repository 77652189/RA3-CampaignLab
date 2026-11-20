"""DamageNugget (step N1): a direct hit's damage through the victim's armor and the flank scalar."""
from engine.combat.registry import nugget


@nugget('Damage', 'victim')
class Damage:
    """Every volley deals its resolved damage (`dmg`, `type`: the weapon's own, else one warhead's, else its OCL's;
    simunits._resolve) to each victim through its armor, taken and the flank (the host's `scalar`), a zero too: the
    entry still names the shooter."""

    def payload(self, weapon):
        return (weapon['dmg'], weapon['type'])

    def apply(self, context, payload):
        dmg, damage_type = payload
        victim = context.victim
        context.add(victim, context.n * dmg * context.by.dealt * context.hit(victim, damage_type))
