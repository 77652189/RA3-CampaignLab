"""ActivateLiftObjectNugget (step N3a): a direct hit lifts a ground target into the air for the caster's
LiftObjectUpdate time; the countdown is the host's (by caster and target name, dropped the check after it runs out),
the LIFTED_INTO_AIR bit stays on the target (the landing is not modelled: a gap, the host's text)."""
from engine.combat.registry import nugget


@nugget('Lift', 'effect')
class Lift:
    """Each lift effect ({include, exclude}) whose filter the target's kinds pass: the caster's LiftObjectUpdate rule
    (Context.host.lift_rule(template), the host's cache: None -- no module, the engine does nothing; False -- a
    timing it does not read) adds its increment to the (caster, target) countdown up to its maximum, sets the bit
    and re-reads the target's modifiers. Only a direct single shot at a ground target; anything else is a gap."""

    def payload(self, weapon):
        return weapon.get('lift') or None

    def apply(self, context, effects):
        t, by, host = context.target, context.by, context.host
        for effect in effects:
            if ((effect['include'] and not set(effect['include']) & t.kinds)
                    or set(effect['exclude']) & t.kinds):
                continue
            rule = host.lift_rule(by.template)
            if rule is None:
                continue
            if rule is False or context.weapon.get('projectile') or context.n != 1 or t.surface != 'ground':
                context.gap('ActivateLiftObjectNugget', '仅直接单发、显式计时字段和地面目标已接通')
                continue
            host.lift_hit(by.name, t.name, rule['increment'], rule['maximum'])
            t.engine_status.add('LIFTED_INTO_AIR')
            host.refresh_modifiers(t)
            context.gap('ActivateLiftObjectNugget', host.LIFT_LANDING)
