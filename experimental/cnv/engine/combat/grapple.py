"""GrapplingHookNugget (E226): a hit whose filter takes the target (its kinds, none of the ForbiddenTargetObjectStatus)
hooks it for the shooter's GrapplingHookUpdate (engine/modules/grapple.py), which pulls it in; the nugget's own damage
is the weapon's like any other."""
from engine.combat.registry import nugget
from engine.kernel import interfaces


@nugget('Grapple', 'effect')
class Grapple:
    def payload(self, weapon):
        return weapon.get('grapple') or None

    def apply(self, context, effects):
        t, by = context.target, context.by
        for e in effects:
            if not (set(e['forbidden']) & t.status or (e['include'] and not set(e['include']) & t.kinds)
                    or set(e['exclude']) & t.kinds):
                for m in by.find(interfaces.Grapple):
                    m.hook(t)
