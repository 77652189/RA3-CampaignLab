"""LeechPercentMaxHealthDamageNugget and LeechHealthDamageNugget (step N2): a victim's hit claims health back for the
shooter; the claim pays out once the frame's damage is dealt (refund), by what the hit did.

The claims are the frame's ledger (Context.claims: victim serial -> [(healer, basis, fraction, raw)], in hit order):
the maximum-health kind pays only when the victim dies, the damage kind only while it lives, at most what it lost
(the bench: engine_leechpct / engine_leechhealth). Two claims on one victim in a frame are a gap (who pays is not
modelled), as before."""
from engine.combat.registry import nugget


@nugget('LeechPercentMaxHealth', 'victim')
class LeechPercentMaxHealth:
    """A claim of `fraction` of the victim's maximum health, paid if this frame kills it."""

    def payload(self, weapon):
        return weapon.get('leech_percent') or None

    def apply(self, context, fraction):
        context.claims.setdefault(context.victim.serial, []).append((context.by, 'maximum', fraction, 0.0))


@nugget('LeechHealth', 'victim')
class LeechHealth:
    """A claim of `fraction` of the damage this volley's direct hit does to the victim (its own dmg and type through
    armor, taken and flank: the host's scalar), paid by at most what the victim lost while it lives."""

    def payload(self, weapon):
        fraction = weapon.get('leech_health')
        return (fraction, weapon['dmg'], weapon['type']) if fraction else None

    def apply(self, context, payload):
        fraction, dmg, damage_type = payload
        victim = context.victim
        raw = context.n * dmg * context.by.dealt * context.hit(victim, damage_type)
        context.claims.setdefault(victim.serial, []).append((context.by, 'damage', fraction, raw))


def refund(claims, victim, before_hp, gap):
    """Pay the victim's claims of this frame (`claims`: its list, or none) once its damage is dealt: it had
    `before_hp`; a healer still alive mends by what its one claim earns (none: nothing). `gap(tag, why)`: the host's."""
    if not claims:
        return
    if len(claims) != 1:
        gap('leech', '并发吸取的伤害归属与回补尚未建模')
        return
    healer, basis, fraction, raw = claims[0]
    amount = 0.0
    if basis == 'maximum' and victim.hp <= 0:
        amount = victim.max_hp * fraction
    elif basis == 'damage' and victim.hp > 0:
        amount = min(raw, max(0.0, before_hp - victim.hp)) * fraction
    else:
        tag = 'LeechPercentMaxHealthDamageNugget' if basis == 'maximum' else 'LeechHealthDamageNugget'
        gap(tag, '最大血量吸取仅致死、实伤吸取仅非致死场景已验证')
    if healer.alive:
        healer.mend(amount)
