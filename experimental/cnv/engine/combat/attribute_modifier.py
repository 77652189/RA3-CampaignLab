"""AttributeModifierNugget (step N3c): a direct hit puts the weapon's modifier on the target for its Duration (the
modifier read in the shooter's XML); a gated or filtered one only where the bench read it."""
from engine.combat.registry import nugget


@nugget('AttributeModifier', 'effect')
class AttributeModifier:
    """Each hit modifier -- a modifier name, or {modifier, required_upgrade, forbidden_upgrade, target_filter} -- whose
    gate the shooter's owner passes (Context.host.upgrade_gate: only a PLAYER gate, any other a gap) and whose target
    filter the target fits (host.fits: the garrison's PassengerFilter, kinds / unkinds as sets; none of its
    status_exclude, the object's or the script's): the modifier (host.modifier, the shooter's XML) goes on the target for its Duration
    (host.wear); one not found or without a Duration is a gap."""

    def payload(self, weapon):
        return weapon.get('hit_modifiers') or None

    def apply(self, context, effects):
        t, by, host = context.target, context.by, context.host
        for effect in effects:
            mid = effect
            if isinstance(effect, dict):
                gate, passed = host.upgrade_gate(by, effect['required_upgrade'], effect['forbidden_upgrade'])
                if gate not in (None, 'PLAYER'):
                    context.gap('AttributeModifierNugget', '仅PLAYER升级门槛已对拍')
                    continue
                flt = effect.get('target_filter')
                if not passed or flt and (not (t.template.lower() in flt['include'] if 'include' in flt else
                                               host.fits(t, dict(flt, kinds=set(flt['kinds']), unkinds=set(flt['unkinds']))))
                                          or set(flt['status_exclude']) & (t.status | t.script_status)):
                    continue
                mid = effect['modifier']
            modifier, xml = host.modifier(by.template, mid)
            if modifier and modifier['frames'] is not None:
                host.wear(t, mid, modifier['frames'], xml)
            else:
                context.gap(mid, '命中修正未找到或缺少已解释的Duration')
