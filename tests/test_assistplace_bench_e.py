"""E169: isolate the native placement-hint control before interpreting readings."""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('assistplace_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_assistplace_only_hint_is_removed():
    import build
    on, ton, _ = build.resolve('assistpon', 'a')
    off, toff, _ = build.resolve('assistpoff', 'a')
    hint = r'<xi:include\s+href="DATA:Includes/GenericRefineryPlacementHint.xml"\s*/>'
    assert re.subn(hint, '', on.units[0].xml) == (off.units[0].xml, 1)
    assert on.units[1] == off.units[1]
    assert on.objects == off.objects
    assert on.map.OBJECTS == off.map.OBJECTS
    assert ton.bench == toff.bench
    assert build.steps('CampAsstOnA', ton)[0][1]['hold'] is False
    assert sum(name == 'bench_start' for name, _ in build.steps('CampAsstOnA', ton)) == 1


@pytest.mark.xfail(strict=True, reason='E169: Sim does not replay sidebar queue/placement clicks; '
                   'bench money is 8000 after queue completion, model stays 10000; '
                   'see work/re/e169_assistplace.md')
@pytest.mark.parametrize('name', ['assistpon', 'assistpoff'])
def test_assistplace_named_sidebar_baseline(name):
    import build
    import sim
    m, t, _ = build.resolve(name, 'a')
    # Actual on/off plateaus: no building was accepted, but the full queue was paid.
    # This is a UI-input gap, not evidence for an AssistedPlacement rule.
    t.expect = [('资金', 0, 'ever==', 8000), ('采样完成', 0, '==', 0),
                ('矿场总数', 0, '==', 0), ('提示位数量', 0, '==', 0)]
    engine = sim.Sim(m, t).run(90)
    verdicts = build.judge(t, engine.series)
    assert verdicts and all(ok for ok, _ in verdicts), verdicts
