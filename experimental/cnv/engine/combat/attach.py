"""AttachNugget (step N3): a direct hit attaches the shooter to a ground vehicle (its AttachUpdate rule by module
id); the chain is the host's (child serial -> (child, parent, rule)), which places the child at once."""
import math

from engine.combat.registry import nugget, standing


@nugget('Attach', 'effect')
class Attach:
    """Each attach effect ({module, forbidden, include, exclude}) whose filter the target passes (none of the
    forbidden status, the kinds): the shooter's AttachUpdate rule of that module ({range, flags}) chains it to the
    target (Context.host.attach: the host's chain, updated at once so the effects after see the new place). Only
    the bench-read case: a direct single shot, a published module, a ground vehicle or structure (A387 h) in range,
    neither end already chained, the shooter not the target; else a gap. ONE_ATTACH_PER_PARENT: a parent already holding a child takes
    no other (no gap: the engine's own rule)."""

    def payload(self, weapon):
        return weapon.get('attach') or None

    def apply(self, context, effects):
        t, by, host = context.target, context.by, context.host
        for effect in effects:
            relation = {r.rstrip('S') for r in effect.get('relation', ())}
            if (set(effect['forbidden']) & t.status
                    or (effect['include'] and not set(effect['include']) & t.kinds)
                    or set(effect['exclude']) & t.kinds
                    or effect.get('things') and t.template.lower() in effect['things']
                    or relation and standing(context.world, by.owner, t).rstrip('S') not in relation):
                continue
            rule = by.attachment_rules.get(effect['module'])
            if not rule or context.weapon.get('projectile') or context.n != 1:
                context.gap('AttachNugget', '仅匹配已发布模块的直接单发附着已对拍；复杂模块/弹体未建模')
                continue
            if not {'VEHICLE', 'STRUCTURE'} & t.kinds or t.surface != 'ground':
                context.gap('AttachNugget', '目前仅地面车辆、建筑父对象已对拍')
                continue
            chains = host.attachments
            if by is t or t.serial in chains or by.serial in chains:
                context.gap('AttachNugget', '重复、换父与嵌套附着未对拍')
                continue
            if rule['range'] is not None and math.hypot(t.x - by.x, t.y - by.y) > rule['range']:
                context.gap('AttachNugget', 'AttachUpdate距离边界未对拍')
                continue
            if 'ONE_ATTACH_PER_PARENT' in rule['flags'] and any(p is t for _, p, _ in chains.values()):
                continue
            if t.status & rule.get('forbidden_parent', set()):  # engine_attachc4 a: its ParentStatus, then no link
                t.engine_status.update(rule['parent'])
                host.refresh_modifiers(t)
                continue
            host.attach(by, t, rule)
