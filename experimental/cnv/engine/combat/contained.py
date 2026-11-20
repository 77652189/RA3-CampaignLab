"""DamageContainedNugget (step N2): a hit on a house damages the eligible passengers inside it, not the house."""
from engine.combat.registry import nugget


@nugget('DamageContained', 'hit')
class DamageContained:
    """Each contained effect ({damage, type, maximum, include, exclude}) hits the first `maximum` living passengers of
    the target (the host's garrison, in its own order: GUESSED entry order, the bench asserts only the total health)
    whose kinds pass the filter, each through its own armor and taken (the host's plain scalar: no flank)."""

    def payload(self, weapon):
        return weapon.get('contained') or None

    def apply(self, context, effects):
        t, by, n = context.target, context.by, context.n
        for effect in effects:
            eligible = [p for p in context.held(t) if p.alive
                        and (not effect['include'] or set(effect['include']) & p.kinds)
                        and not set(effect['exclude']) & p.kinds]
            for passenger in eligible[:max(0, effect['maximum'])]:
                context.add(passenger, n * effect['damage'] * by.dealt * context.armor(passenger, effect['type']))
