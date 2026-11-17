"""E178: retail toggle / SpiderHoleUpdate removal control and measured replay."""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('spider_simbench', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_spider_only_module_removed():
    import build
    from parts import contract, merged
    arms = [build.resolve(name, 'a')[:2] for name in ('spideron_e', 'spideroff_e')]
    for m, t in arms:
        assert not contract(merged(m, t))
        assert len(m.objects) == 3
        assert not any(a[0] in ('UNIT_CHANGE_OBJECT_STATUS', 'UNIT_SET_HEALTH')
                       for script in t.scripts for a in script.do)
    on, off = [m.units[0].xml for m, _ in arms]
    assert re.sub(r'<SpiderHoleUpdate\b.*?</SpiderHoleUpdate>', '', on, flags=re.S).replace('CNVE178On', 'CNVE178Off') == off


@pytest.mark.parametrize('name', ['spideron_e', 'spideroff_e'])
def test_spider_named_measured_toggle_snapshot(name):
    """Retail f90: both in hole/alive; f180: quiet out, contact still in."""
    import build
    import sim
    m, t, _ = build.resolve(name, 'a')
    s = sim.Sim(m, t).run(16)
    assert [s.eng.value(c) for c in ('E178Frame', 'E178Entry', 'E178Exit')] == [180, 1515, 1508]


@pytest.mark.parametrize('name', ['spideron_e', 'spideroff_e'])
@pytest.mark.xfail(strict=True, reason='E178: retail toggle emits three player cast observations, '
                   'Sim emits zero; dispatch event gap, see work/re/e178_spider.md')
def test_spider_named_measured_cast_events(name):
    import build
    import sim
    m, t, _ = build.resolve(name, 'a')
    s = sim.Sim(m, t).run(16)
    assert s.eng.value('E178Cast') == 3
