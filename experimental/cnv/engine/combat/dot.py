"""DOTNugget (step N2): a direct single hit puts a damage-over-time entry on the host's book (Context.dots); the
frame's end ticks it (the host's DOT ledger, simdamage.Damage.deal; step N2c moves it here)."""
from engine.combat.registry import nugget


@nugget('DOT', 'hit')
class DOT:
    """Each DOT effect of the weapon ({damage, type, interval, duration, remove_healed}, simunits._resolve) books one
    entry on the target: its first tick this frame, its last at now + duration (frames), the target's health now (a
    later rise is healing). Only a direct single first hit is on the bench: a shell, a volley of more than one, or a
    target already on the book is a gap and books nothing."""

    def payload(self, weapon):
        return weapon.get('dot') or None

    def apply(self, context, effects):
        t, by, now = context.target, context.by, context.world.frame_now()
        for effect in effects:
            dots = context.dots
            if context.weapon.get('projectile') or context.n != 1 or any(d['target'] is t for d in dots):
                context.gap('DOTNugget', '仅直接单发首次DOT已对拍；弹体/叠加/刷新未建模')
            else:
                dots.append(dict(target=t, by=by, effect=effect, next=now, end=now + effect['duration'], hp=t.hp))
