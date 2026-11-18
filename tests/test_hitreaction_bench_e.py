"""E172 controlled legal-hit diagnostic; module effects remain a gap."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hitreact_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_hitreaction_only_module_removal_contract():
    import build
    from parts import contract, merged
    m, t, _ = build.resolve('engine_hitreaction_e', 'a')
    on, off = [u.xml for u in m.units]
    assert re.sub(r'<HitReactionBehavior\b.*?</HitReactionBehavior>', '',
                  on.replace('CNVE172On', 'CNVE172Off'), flags=re.S) == off
    assert 'RequiredStatus="GENERIC_TOGGLE_STATE"' in on
    assert 'ConditionsYes="HIT_REACTION USER_6"' in on
    assert not contract(merged(m, t))
    m, t, _ = build.resolve('engine_hitreaction_e', 'b')
    assert not contract(merged(m, t))
