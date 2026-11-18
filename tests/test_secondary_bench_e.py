"""E174: named secondary-listener measurements and the module-only control."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('secondary_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_secondary_only_listener_removed():
    import build
    from model import merged
    from contract import contract
    from package import spec_of
    on, a, _ = build.resolve('engine_secondon_e', 'a')
    off, b, _ = build.resolve('engine_secondoff_e', 'a')
    assert re.sub(r'<xi:include\s+href="DATA:Includes/InfantryFighting/IF_SecondaryObjectListener.xml"\s*/>', '',
                  on.units[0].xml) == off.units[0].xml
    for m, t in [(on, a), (off, b)]:
        assert spec_of(m, t).replaces == ('GameObject:AlliedBaseDefense',)
        assert not contract(merged(m, t))
        assert len([o for o in m.objects if o.template == 'AlliedEngineer']) == 1
