"""DOTNugget (step N2): a direct single hit puts a damage-over-time entry on the host's book (Context.dots); once the
frame's volleys are done the host ticks the book (tick, step N2c) into the frame's damage and keeps what is still due."""
from engine.combat.registry import accumulate, nugget


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


def tick(dots, now, hurt, armor, gap):
    """The frame-end DOT ledger, once the frame's volleys are done: each entry of the book `dots` (booking order) on a
    living target adds its ticks due by frame `now` into the frame's damage `hurt` (registry.accumulate): the first on
    its booking frame, the last on its end frame too (inclusive expiry: floor(duration / interval) + 1 ticks). A target
    whose health rose since the last look was healed (GUESSED outside the no-healing probe): a gap, and an entry that
    is `remove_healed` is dropped. Each tick reads `armor(victim, type)` (the host's armor x taken, no flank) and the
    caster's `dealt` again (GUESSED for changing modifiers / dead casters). Immunity, shields and indestructibility are
    the host's, at the final damage. `gap(tag, why)`: the host's. Returns the entries still due (the book is the
    host's: it keeps them itself)."""
    keep = []
    for entry in dots:
        t, by, effect = entry['target'], entry['by'], entry['effect']
        if not t.alive:
            continue
        if t.hp > entry['hp'] + 1e-6:
            gap('DOTNugget', '治疗取消与再次施加未对拍')
            if effect['remove_healed']:
                continue
        while entry['next'] <= now and entry['next'] <= entry['end']:
            accumulate(hurt, t, effect['damage'] * by.dealt * armor(t, effect['type']), by)
            entry['next'] += effect['interval']
        entry['hp'] = t.hp
        if entry['next'] <= entry['end']:
            keep.append(entry)
    return keep
