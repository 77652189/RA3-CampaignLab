"""E148 named multi-lane replay; unimplemented effects retain explicit gaps."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench_infbatch', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_infiltrator_batch_retail_configuration():
    import build
    import siminfiltrator
    m, t, mod = build.resolve('engine_infbatch', 'a')
    assert len(mod) <= 15 and '_' not in mod
    assert len(t.counters) == 4
    for lane, kind in (('air', 'Aircraft'), ('infantry', 'Infantry'), ('ship', 'Ship')):
        rule = siminfiltrator.spec(m.role(lane).template)
        assert (rule['Effect'], rule['Duration'], rule['UnitDuration'], rule['ObjectRef']) == (
            'VISION_UNITS', '30s', '30s', 'UnitVisionObserver')
        assert rule['UnitFilter'] == 'Infiltration' + kind + 'ObjectFilter'
        assert rule['StructureFilter'] == 'Infiltration' + kind + 'StructuresFilter'
    port = siminfiltrator.spec(m.role('port').template)
    assert (port['Effect'], port['Duration'], port['BlockedDuration'], port['ObjectRef']) == (
        'VISION', '-1s', '9999999s', 'VisionObserver')


def test_infiltrator_batch_requires_real_retail_markers():
    import build
    import simunits
    m, _, _ = build.resolve('engine_infbatch', 'a')
    missing = [obj.template for obj in m.objects if not simunits.retail_xml(obj.template)]
    assert not missing, missing
    import re
    for lane, kind in (('air', 'AIRCRAFT'), ('infantry', 'INFANTRY'), ('ship', 'SHIP')):
        xml = simunits.retail_xml(m.role(lane + ' match').template)
        kinds = re.search(r'KindOf="([^"]+)"', xml).group(1).split()
        assert kind in kinds
    port, near, far = (m.point(role) for role in ('port', 'port match', 'port wrong'))
    assert (near[0] - port[0])**2 + (near[1] - port[1])**2 < 600**2
    assert (far[0] - port[0])**2 + (far[1] - port[1])**2 > 600**2
    _, t, _ = build.resolve('engine_infbatch', 'a')
    assert [item[3] for item in t.expect] == [200111, 200111, 200111, 1200111]


@pytest.mark.xfail(strict=True, reason='E149步兵/舰船身份位置门未过、港口首入前已发现标记；'
                   '前置不等价且效果未闭合，不登记覆盖；见work/re/handoff-e.md和work/re/e149_infiltrator.md')
def test_infiltrator_batch_diagnostic_as_on_the_bench():
    """Replay actual E149 diagnostic readings; failed gates forbid effect claims."""
    import build
    import sim
    m, t, _ = build.resolve('engine_infbatch', 'a')
    s = sim.Sim(m, t).run(45)
    # Keep the failed real prerequisites, rather than changing their expectations.
    rows = [values for second, values in s.series if 1 <= second <= 7]
    assert rows and all(row == [200111, 111, 111, 1001111] for row in rows), rows
    rows = [values for second, values in s.series if 39 <= second <= 45]
    assert rows and all(row == [111110, 110, 1110, 1101110] for row in rows), rows
