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
the player status count (A round 164); engine_aidelay.readings.toml replays these
script counters.
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
W_EDGES = [2000, *range(2700, 3061, 30), 3600]   # run 2: 14 non-overlapping warrior bands [lo, hi), read as lo


def where(m):
    """p (A round 248, H1: where do the two sides stop): four counters show world y in 10-unit steps, every frame:
      动1y / 动2y  conscript k's y: the largest Y with it in {y > Y}  -> its y in (Y, Y + 10]
      武前y / 武后y  the southmost / northmost s1 warrior: the band [lo, hi) of W_EDGES it is in, read as lo
                   (run 2; 2000 = below 2700, 3060 = 3060 or above)
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
    is not affected. Where the warriors stood is not read.
    Run 2 (A round 249): the warrior readouts moved to 14 non-overlapping bands written first in the areas (83 areas,
    the Test S half dropped). Sim: 武前y 2910 s19-s23, 2820 s28-s34, 2850 to s42; 武后y 2850-2970; conscripts as above.
    Bench 2026-11-15 aidelay0:p PASS (CampADZeroP_mcp_1115_153330): the warrior readouts are positions now (front <=
    back every second), so the run-1 failure was the area count / order (H5 supported; cap or order not split).
    Conscripts 2510 to s19, 2730 / 2700 s24, 2750 / 2700 s25 (conscript 2 pauses at the sim's stop 2700), 2780 / 2740
    s26, then on to 3030 / 2950 from s32. Warriors: 2940 s15, 2910 s16-s22, 2850 s23-s26 (the sim's 2820-2850), then
    NORTH: 2910 s27, 2970 s28, 3000 s29, >= 3060 s30-s33, back south from s34 (3030 ... 2910 s39-s46). So the two
    sides first meet at the sim's gap (H1, a deeper stop, not supported; H4, warriors staying home, not either); the
    bench differs after: the warriors withdraw north s27-s30 and the conscripts follow to the attack-move's end
    (INFERRED; only y is read, x unknown)."""
    t = check(m)
    s1 = m.player('s1')
    warrior = m.cnv_units[0]
    ys = list(range(Y_LO, Y_HI + 1, Y_STEP))
    areas = {f'Test W {lo}': [(X_LO, lo), (X_HI, lo), (X_HI, hi), (X_LO, hi)] for lo, hi in zip(W_EDGES, W_EDGES[1:])}
    areas.update({f'Test N {y}': [(X_LO, y), (X_HI, y), (X_HI, 3600.0), (X_LO, 3600.0)] for y in ys})   # y > Y
    t.areas = {**areas, **t.areas}   # the warrior bands first (run 1: the type count saw only the first ~14 areas)
    t.counters = []
    readouts = [(f'CNV_AD_C{k}', f'动{k}y', lambda y, n=r.name: ('NAMED_INSIDE_AREA', n, f'Test N {y}'), ys)
                for k, r in enumerate(m.roles('conscript'), 1)]
    bands = W_EDGES[:-1]
    readouts += [('CNV_AD_WF', '武前y', lambda y: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1,
                                                    warrior, f'Test W {y}'), bands[::-1]),
                 ('CNV_AD_WB', '武后y', lambda y: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 3, 1,
                                                    warrior, f'Test W {y}'), bands)]
    for counter, label, cond, order in readouts:
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        t.scripts += [Script(f'Test - {counter} {y}', [cond(y)], [('SET_COUNTER', counter, y)], once=False)
                      for y in order]
    t.expect = [('动1y', 1, 'ever>=', Y_LO, 50), ('武前y', 1, 'ever>=', W_EDGES[0], 50)]
    t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=4))]
    return t


CHECKS = {key: {'a': check} for key in ('aidelay0', 'aidelay999')}
CHECKS['aidelay0']['p'] = where
