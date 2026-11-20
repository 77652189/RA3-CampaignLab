"""ParalyzeNugget (step N2): a hit stands the target still (EMP) till a frame; the host's EMP book is shared with
the special powers' (simspecial: the leap, the wfire), each picking its own objects."""
from engine.combat.registry import nugget


@nugget('Paralyze', 'hit')
class Paralyze:
    """Each duration (seconds) of the weapon moves the target's deadline (Context.emp_until(): serial -> frame, the
    host's book, made on first use) to now + its frames if that is later (max); the readers judge now < deadline, so
    what it has already fired still lands."""

    def payload(self, weapon):
        return weapon.get('emp_seconds') or None

    def apply(self, context, durations):
        t, now = context.target, context.world.frame_now()
        for seconds in durations:
            deadlines = context.emp_until()
            deadlines[t.serial] = max(deadlines.get(t.serial, 0), now + context.frames(seconds))
