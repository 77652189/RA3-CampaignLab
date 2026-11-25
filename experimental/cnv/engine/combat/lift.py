"""ActivateLiftObjectNugget (step N3a): a direct hit lifts a ground target into the air for the caster's
LiftObjectUpdate time; the countdown is the host's (by caster and target name, dropped the check after it runs out),
the LIFTED_INTO_AIR bit stays on the target unless a soft landing clears it (simunits.LiftTimers; the rest a gap,
the host's text); an aircraft crashes instead."""
from engine.combat.registry import nugget
from engine.kernel.module import status_now


@nugget('Lift', 'effect')
class Lift:
    """Each lift effect ({include, exclude kinds, things, status}) whose filter the target passes: the caster's LiftObjectUpdate rule
    (Context.host.lift_rule(template), the host's cache: None -- no module, the engine does nothing; False -- a
    timing it does not read) adds its increment to the (caster, target) countdown up to its maximum, sets the bit
    and re-reads the target's modifiers; an aircraft fires the rule's crash weapon on itself. Only a direct single
    shot at a ground or air target; anything else is a gap."""

    def payload(self, weapon):
        return weapon.get('lift') or None

    def apply(self, context, effects):
        t, by, host = context.target, context.by, context.host
        for effect in effects:
            if ((effect['include'] and not set(effect['include']) & t.kinds) or set(effect['exclude']) & t.kinds
                    or t.template.lower() in effect['things'] or set(effect['status']) & (status_now(t) | t.script_status)):
                continue
            rule = host.lift_rule(by.template)
            if rule is None:
                continue
            if rule is False or context.weapon.get('projectile') or context.n != 1 or t.surface not in ('ground', 'air'):
                context.gap('ActivateLiftObjectNugget', '仅直接单发、显式计时字段和地面、空中目标已接通')
                continue
            rule = dict(rule)
            crash = rule.pop('crash', None)
            if t.surface == 'air':
                # an aircraft takes the plane branch: the caster's AirplaneCrashWeapon fired by the plane at itself, no
                # LIFTED (bench engine_liftair: the three retail hosts' Twinblades died, never latched; D50). INFERRED:
                # it goes off at the hit (the death frame is not measured), its kill the weapon's own-owner nugget
                if crash:
                    host.kill(t, f'被 {by.name} 举升坠机')
                    host.fire_weapon(t, crash)
                continue
            host.lift_hit(by.name, t.name, serial=t.serial, **rule)
            t.engine_status.add('LIFTED_INTO_AIR')
            host.refresh_modifiers(t)
            context.gap('ActivateLiftObjectNugget', host.LIFT_LANDING)
