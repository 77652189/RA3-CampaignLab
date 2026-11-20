"""LineDamageNugget (step N1): a dynamic line picks the victims the volley's direct damage goes to."""
import math

from engine.combat.registry import nugget


@nugget('LineDamage', 'aim')
class LineDamage:
    """UseDynamicLineLength: the line runs from the shooter through the aimed target, as long as their flat distance,
    from `lead` behind the shooter to `out` past it; a living enemy the weapon can hit, its centre within
    width / 2 + its radius across, is a victim, in the world's order (GUESSED edge geometry: circle extent; the bench
    round 1 centres avoid edges). Not dynamic, or the shooter on the target: the aimed target alone."""

    def payload(self, weapon):
        return weapon.get('line') or None

    def apply(self, context, line):
        if not line['dynamic']:
            return
        t, by, w = context.target, context.by, context.weapon
        dx, dy = t.x - by.x, t.y - by.y
        length = math.hypot(dx, dy)
        if not length:
            return
        ux, uy = dx / length, dy / length
        victims = []
        for candidate in context.world.living():
            if candidate is by or not context.world.hostile(by, candidate) or not context.can_hit(w, candidate):
                continue
            cx, cy = candidate.x - by.x, candidate.y - by.y
            along, across = cx * ux + cy * uy, abs(cx * uy - cy * ux)
            if -line['lead'] <= along <= length + line['out'] and across <= line['width'] / 2 + candidate.radius:
                victims.append(candidate)
        context.victims = victims
