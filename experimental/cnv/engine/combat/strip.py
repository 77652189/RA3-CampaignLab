"""StripMaxHealthPercentDamageNugget (step N2): a hit takes a fraction of the victim's maximum health."""
from engine.combat.registry import nugget


@nugget('StripMaxHealthPercent', 'victim')
class StripMaxHealthPercent:
    """Each (fraction, damage type) of the weapon deals fraction x the victim's maximum health, through the armor of
    its own type, taken and the flank (the host's scalar; the flank: INFERRED); the maximum stays as it was."""

    def payload(self, weapon):
        return weapon.get('strip_max_health') or None

    def apply(self, context, strips):
        victim, by, n = context.victim, context.by, context.n
        for fraction, damage_type in strips:
            context.add(victim, n * victim.max_hp * fraction * by.dealt * context.hit(victim, damage_type))
