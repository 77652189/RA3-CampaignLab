"""SecondaryDamageNugget (step N2): a hit's cold goes into the target's freeze tracker (Freeze, the object module);
the frame's chill (simdamage.Damage.chill) turns it into frozen or melted."""
from engine.combat.registry import nugget
from engine.kernel import interfaces


@nugget('SecondaryDamage', 'hit')
class SecondaryDamage:
    """Amount per hit (not a partial clip's mean DPS) x the shots x the shooter's dealt, added to an unshielded target
    that can be cold (the host's cold_of: a threshold); its shooter is the one of record for the frame's chill
    (Context.mark_cold, the host's book). A shell's cold is a gap: its arrival event is not modelled."""

    def payload(self, weapon):
        return weapon.get('sd') or None

    def apply(self, context, amount):
        t, by = context.target, context.by
        if context.weapon.get('projectile'):
            context.gap('SecondaryDamageNugget', '弹体冷冻值的到达事件尚未建模')
        elif not t.shielded and context.cold_of(t)[0] is not None:
            t.find(interfaces.Freeze).add(context.n * amount * by.dealt)   # SecondaryDamageTracker
            context.mark_cold(t, by)
            context.world.used.add('freeze')
