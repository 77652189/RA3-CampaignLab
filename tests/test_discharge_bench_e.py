"""E177: single-module controls and named measured discharge replay."""
import importlib.util
import re
from pathlib import Path

import pytest

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


@pytest.mark.xfail(strict=True, reason='E177: Sim hits at 47 before the discharge button at 75, '
                   'and lacks the discharge cast event; retail first hit is 76. '
                   'Weapon preattack/dispatch gap, see work/re/e177_discharge.md')
def test_discharge_on_named_measured_snapshot():
    """E177 original: first target damage at script frame 76, cast seen once."""
    import build
    import sim
    m, t, _ = build.resolve('dischargeon_e', 'a')
    s = sim.Sim(m, t).run(16)
    assert [s.eng.value(c) for c in ('E177Frame', 'E177On', 'E177Off', 'E177Cast')] == [210, 76, 0, 1]


@pytest.mark.xfail(strict=True, reason='E177: ordinary Waveforce first hit is 47 in Sim versus '
                   '109 on the removal bench; PER_SHOT preattack remains a gap. '
                   'See work/re/e177_discharge.md')
def test_discharge_off_named_measured_snapshot():
    """E177 removal: first damage at 109; no special-power event observed."""
    import build
    import sim
    m, t, _ = build.resolve('dischargeoff_e', 'a')
    s = sim.Sim(m, t).run(16)
    assert [s.eng.value(c) for c in ('E177Frame', 'E177On', 'E177Off', 'E177Cast')] == [210, 0, 109, 0]
