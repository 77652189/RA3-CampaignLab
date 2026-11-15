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


@pytest.mark.xfail(strict=True, reason='E148标记模板不存在，台上前置不等价；'
                   '见work/re/handoff-e.md、work/re/e148_infiltrator.md；修复后须重新上台')
def test_infiltrator_batch_requires_real_retail_markers():
    import build
    import simunits
    m, _, _ = build.resolve('engine_infbatch', 'a')
    missing = [obj.template for obj in m.objects if not simunits.retail_xml(obj.template)]
    assert not missing, missing


@pytest.mark.xfail(strict=True, reason='E148诊断台前置不等价且VISION_UNITS/港口未实现，'
                   '不登记效果已对拍；见work/re/handoff-e.md和work/re/e148_infiltrator.md')
def test_infiltrator_batch_diagnostic_as_on_the_bench():
    """Raw first-run counters only, not evidence of valid unit-filter behavior.

    Port second spy stays alive; no claim about correct blocking mechanism.
    Missing marker templates and the port radius error invalidate promotion.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_infbatch', 'a')
    s = sim.Sim(m, t).run(45)
    for start, end, wanted in (
            (1, 10, [111, 111, 111, 1000111]),
            (11, 11, [110, 111, 110, 1000110]),
            (12, 24, [110, 110, 110, 1000110]),
            (25, 42, [10110, 110, 110, 1000110]),
            (43, 45, [110, 110, 110, 1000110])):
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(row == wanted for row in rows), (start, end, rows)
