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
give Frames - Ever = 362 after wake (24 positive samples per build).
This is the latched script observation clock, not an internal dispatch frame.
This single pair does not measure the RNG distribution. Sim.cond now supports
the player status count (A round 164); tests/test_simai_delay.py replays these
script counters separately from the simulator's body-state trace.
"""
from checks import engine_aimicro as ac
from parts import Script


def check(m):
    t = ac.probe_built(m, 'aimicspon')
    t.scripts = [s for s in t.scripts if s.name not in ('Test - control make', 'Test - control press')]
    t.expect = [('造出', 14, 'ever>=', 2, 50), ('曾冲', 14, 'ever>=', 1, 50)]
    t.expect += [('冲', 14, '<=', 1, 50)] if m.facts['specific maximum'] else [('冲', 14, 'ever>=', 2, 50)]
    t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=4))]
    return t


Y_LO, Y_HI, Y_STEP = 2480, 3160, 10     # the bands: the conscripts walk north from y 2520, the warriors south
X_LO, X_HI = 3300.0, 4400.0              # wide in x: only the y of each side is read


def where(m):
    """p (A round 248, H1: where do the two sides stop): four counters show world y in 10-unit steps, every frame:
      动1y / 动2y  conscript k's y: the largest Y with it in {y > Y}  -> its y in (Y, Y + 10]
      武前y        the southmost s1 warrior: the smallest Y with one in {y < Y} -> its y in (Y - 10, Y]
      武后y        the northmost s1 warrior: the largest Y with one in {y > Y} -> its y in (Y, Y + 10]
    0 = nobody in any band. Each counter is zeroed, then the band scripts run in order and the last true one wins
    (scripts run in order: model.counted's owner readout). The approach is along y (sim: dx ~26 at the stop), so the
    y gap is the stop distance less a few units. The conscripts stand at y 2520 till the go: their first rows calibrate
    how a band counts a unit (centre or footprint).
    Sim (model 9880258): 动1y / 动2y 2520 to s23, stop at 2700 from s28; 武前y 2850, 武后y 2860.
    Bench 2026-11-15 aidelay0:p FAIL (CampADZeroP_mcp_1115_151702, one run): 动1y / 动2y 2510 (placed at 2520: the
    centre, strict) to s19, walk from s20, 2740 / 2700 at s24, 3030 / 2950 from s31 to s42 (the barracks centre is
    y 3000, the attack-move's end), conscript 1 out of every band from s43, 2 from s45 -- they walk ~300 past the
    simulator's stop. 武前y 0 throughout and 武后y 2540 from s15 to s46: not a position (a warrior below no
    {y < Y} yet above only {y > 2540}). INFERRED: the type-in-area count sees only the first few areas (the bands
    2480..2540, 14 areas) -- an area cap or a per-object cap on the areas it is counted in; NAMED_INSIDE_AREA
    is not affected. Where the warriors stood is not read."""
    t = check(m)
    s1 = m.player('s1')
    warrior = m.cnv_units[0]
    ys = list(range(Y_LO, Y_HI + 1, Y_STEP))
    for y in ys:
        t.areas[f'Test N {y}'] = [(X_LO, y), (X_HI, y), (X_HI, 3600.0), (X_LO, 3600.0)]   # y > Y
        t.areas[f'Test S {y}'] = [(X_LO, 2000.0), (X_HI, 2000.0), (X_HI, y), (X_LO, y)]   # y < Y
    t.counters = []
    readouts = [(f'CNV_AD_C{k}', f'动{k}y', lambda y, n=r.name: ('NAMED_INSIDE_AREA', n, f'Test N {y}'), ys)
                for k, r in enumerate(m.roles('conscript'), 1)]
    readouts += [('CNV_AD_WF', '武前y', lambda y: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1,
                                                    warrior, f'Test S {y}'), ys[::-1]),
                 ('CNV_AD_WB', '武后y', lambda y: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1,
                                                    warrior, f'Test N {y}'), ys)]
    for counter, label, cond, order in readouts:
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        t.scripts += [Script(f'Test - {counter} {y}', [cond(y)], [('SET_COUNTER', counter, y)], once=False)
                      for y in order]
    t.expect = [('动1y', 1, 'ever>=', Y_LO, 50), ('武前y', 1, 'ever>=', Y_LO, 50)]
    t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=4))]
    return t


CHECKS = {key: {'a': check} for key in ('aidelay0', 'aidelay999')}
CHECKS['aidelay0']['p'] = where
