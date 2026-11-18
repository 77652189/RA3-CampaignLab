"""E178: retail toggle / SpiderHoleUpdate removal control and measured replay."""
import importlib.util
import re
from pathlib import Path

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
