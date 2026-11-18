"""E177: single-module controls and named measured discharge replay."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('discharge_simbench', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_discharge_is_only_gameplay_module_difference():
    import build
    from parts import contract, merged
    arms = [build.resolve(name, 'a')[:2] for name in ('dischargeon_e', 'dischargeoff_e')]
    for m, t in arms:
        assert not contract(merged(m, t))
        assert len(m.objects) == 2
        assert not any(a[0] == 'UNIT_SET_HEALTH' for s in t.scripts for a in s.do)
    on, off = [m.units[0].xml for m, _ in arms]
    assert re.sub(r'<PrematureDischargeSpecialPower\b[^>]*/>', '', on).replace('CNVE177On', 'CNVE177Off') == off
