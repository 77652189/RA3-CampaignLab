"""SpecialPowerNugget (step N3b): a direct hit fires a power of the caster on itself -- the bench-read cases: a
self ARMOR modifier for its Duration, or the disguise's DISGUISED bit; every other power a gap."""
import math

from engine.combat.registry import nugget


@nugget('SpecialPower', 'effect')
class SpecialPower:
    """Each power effect ({power, required_upgrade, forbidden_upgrade, include, exclude}) whose upgrade gate the
    caster passes (Context.host.upgrade_gate, engine_spng / engine_spngp: an OBJECT gate reads its own upgrades, a PLAYER gate its owner's; any
    other type a gap) and whose kinds filter the target passes: the caster's module of that power
    (host.self_power, the host's cache: None -- no module, the engine does nothing). Only a zero-recharge power from a
    direct single shot within its reach; a noop power does nothing; a disguise sets DISGUISED on the caster (the
    target's kinds and template its filter); else the power's modifier, when it has a Duration, no status and only
    ARMOR, goes on the caster until then (else a gap)."""

    def payload(self, weapon):
        return weapon.get('special_powers') or None

    def apply(self, context, effects):
        t, by, host = context.target, context.by, context.host
        for effect in effects:
            gate, passed = host.upgrade_gate(by, effect.get('required_upgrade', ''),
                                             effect.get('forbidden_upgrade', ''))
            if gate not in (None, 'OBJECT', 'PLAYER'):
                context.gap('SpecialPowerNugget', '升级门槛未知类型待核')
                continue
            if not passed or ((effect['include'] and not set(effect['include']) & t.kinds)
                              or set(effect['exclude']) & t.kinds):
                continue
            power = host.self_power(by.template, effect['power'])
            if power is None:      # no matching module on caster: engine_spn order
                continue
            if not power or context.weapon.get('projectile') or context.n != 1 or (
                    power['reach'] and math.hypot(t.x - by.x, t.y - by.y) > power['reach']):
                context.gap('SpecialPowerNugget', '仅直接单发、零冷却自身修正已对拍；其他技能处理器/弹体/范围待核')
                continue
            if power.get('noop'):
                continue
            if power.get('disguise'):
                if not set(power['include']) & t.kinds or t.template.lower() in power['exclude_templates']:
                    continue
                host.disguise(by, t.owner)
                context.gap('SpecialDisguiseUpdate', '命中、展开、被动索敌、出舱取消已对拍；外观/点名攻击/探测未测')
                continue
            modifier, xml = host.modifier(by.template, power['modifier'])
            if (modifier and modifier['frames'] is not None and not modifier['status']
                    and set(modifier['types']) <= {'ARMOR'}):
                host.wear(by, power['modifier'], modifier['frames'], xml)
            else:
                context.gap('SpecialPowerNugget', '仅有Duration的自身ARMOR修正已对拍')
