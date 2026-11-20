"""SuppressionNugget (step N2): each hit leaves a still 2D field where the target stands, sampled by the suppression
module (engine/modules/suppression.py) while now < its end (simdamage.suppression_at)."""
from engine.combat.registry import nugget


@nugget('Suppression', 'hit')
class Suppression:
    """Each (radius, value, seconds) of the weapon adds one field a shot to the host's list (Context.
    suppression_fields): (end frame, value, x, y, radius) at the target's place now (bench engine_suppress_probe: one
    field a hit, each its own lifetime)."""

    def payload(self, weapon):
        return weapon.get('suppression') or None

    def apply(self, context, fields):
        t, now = context.target, context.world.frame_now()
        for radius, value, seconds in fields:
            context.suppression_fields.extend((now + context.frames(seconds), value, t.x, t.y, radius)
                                              for _ in range(context.n))
