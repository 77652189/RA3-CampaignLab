"""Two probes of the counters themselves (build.py digits --calibrate; build.py kinds), not levels."""
import parts


def digits():
    """A map that shows counters.CALIBRATION (every digit once), whose frame gives the counter reader's templates."""
    from maps import island
    values = [1234, 5678, 90]                   # experimental/testbench/counters.py CALIBRATION
    m = parts.Mission(name='CampDigits', map=island)
    t = parts.Test(counters=[(f'Digit {k}', '校准') for k in range(len(values))])
    t.scripts.append(parts.Script('Digits', [], [('SET_COUNTER', f'Digit {k}', v) for k, v in enumerate(values)]))
    t.bench = [('bench_watch', dict(seconds=3, every=3, sheet=False))]
    return m, t


def kinds():
    """A probe of the counting itself: 3 Guardians and 2 buildings of ours, counted four ways at once -- by KindOf
    in an area (VEHICLE, STRUCTURE), by template in an area, by template owned. Should read 3 2 3 3 (the a8 assault's
    KindOf counts read 20 for 12 vehicles, 2026-10-21)."""
    from maps import island
    guardian = 'AlliedAntiVehicleVehicleTech1'
    m = parts.Mission(name='CampKinds', map=island)
    for dx in (-60, 0, 60):
        m.put(guardian, 'west field', dx, -60, role='guardian')
    m.put('AlliedWarFactory', 'base factory', angle=3.1416, role='factory')
    m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power')
    t = parts.Test()
    whole = m.where('island')
    t.areas['Test Whole Island'] = parts.square(whole.x, whole.y, whole.r + 300)
    parts.counted('Test Kind V', '类别车辆', t, kind=parts.kindof('VEHICLE'), area='Test Whole Island')
    parts.counted('Test Kind S', '类别建筑', t, kind=parts.kindof('STRUCTURE'), area='Test Whole Island')
    parts.counted('Test Type A', '型号区域', t, template=guardian, area='Test Whole Island')
    parts.counted('Test Type O', '型号拥有', t, template=guardian)
    t.expect += [('类别车辆', 3, '==', 3), ('类别建筑', 3, '==', 2), ('型号区域', 3, '==', 3), ('型号拥有', 3, '==', 3)]
    t.bench = [('bench_watch', dict(seconds=6, every=3, sheet=False))]
    return m, t


PAIR_BUILDS = {'digits': digits, 'kinds': kinds}
