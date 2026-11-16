"""E179 original Riptide evacuation button, named bench replay."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ifvevac_simbench', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_ifvevac_named_measured_snapshots():
    import build
    import sim
    from parts import contract, merged
    m, t, _ = build.resolve('ifvevac_e', 'a')
    assert not contract(merged(m, t))
    assert not any(a[0] in ('UNIT_CHANGE_OBJECT_STATUS', 'UNIT_SET_HEALTH')
                   for script in t.scripts for a in script.do)
    s = sim.Sim(m, t).run(12)
    assert [s.eng.value(c) for c in ('E179Frame', 'E179Before', 'E179After', 'E179Alive')] == [120, 11, 10, 1111]
