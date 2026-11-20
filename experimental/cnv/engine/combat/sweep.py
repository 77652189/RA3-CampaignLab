"""ActivateLinearDamageNugget (step N3d): a direct hit starts the shooter's sweeping line."""
from engine.combat.registry import nugget


@nugget('Sweep', 'hit')
class Sweep:
    """The weapon's Lifetime (s): the shooter's line starts towards the aimed target, once a volley, after the other
    hit effects and before an aim picks the victims (Context.host.sweep: the host's Sweeps.fire reads the shooter's
    LinearDamageUpdate; the line's nodes are dealt in their own frame phase)."""

    def payload(self, weapon):
        return weapon.get('sweep') or None

    def apply(self, context, life):
        context.host.sweep(context.by, context.target, life)
