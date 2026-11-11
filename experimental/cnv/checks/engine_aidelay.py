"""MaximumDelay-only pair on the successful aimicspon Hunt team.

Prediction before bench: zero permits both warriors to charge together; long
still permits the first charge, then samples a RUSH_ATTACK cooldown in 0..999s.
Thus long is expected to have no simultaneous pair in the automatic window,
but that is a sampled prediction, NOT a deterministic lower-bound guarantee.
Both builds keep MinimumDelay=0, no team delay, the same update/health/targets.
The old aimicmed all-zero run is not a successful delay control.
Only the automatic window is measured; remove the inherited manual warrior.

Bench 2026-11-11, aidelay0:a PASS: two warriors from s20, charging one at
s33 and two at s34-s42; Ever grows from 11 at s33 to 146 at s42.
aidelay999:a PASS: two warriors from s20, one charging at s33-s42,
none from s43; Ever 11 at s33 and 142 at s42. Both first-seen clocks
are frame 362 after wake. This single pair does not measure the RNG distribution.
The simulator's body-state trace is separate from these script counters:
PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS is still unmodeled.
"""
from checks import engine_aimicro as ac


def check(m):
    t = ac.probe_built(m, 'aimicspon')
    t.scripts = [s for s in t.scripts if s.name not in ('Test - control make', 'Test - control press')]
    t.expect = [('造出', 14, 'ever>=', 2, 50), ('曾冲', 14, 'ever>=', 1, 50)]
    t.expect += [('冲', 14, '<=', 1, 50)] if m.facts['specific maximum'] else [('冲', 14, 'ever>=', 2, 50)]
    t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=4))]
    return t


CHECKS = {key: {'a': check} for key in ('aidelay0', 'aidelay999')}
