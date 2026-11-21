"""Named building exit replay; evidence: work/re/c_exitbld_report.md."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('exitbld_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.mark.parametrize('variant,mask,before,after', [
    ('a', 12, (45, 52, 59, 68, 75),
     (82, 91, 98, 105, 113, 121, 128, 135, 143, 150, 159, 166, 173,
      182, 189, 196, 204, 211, 218, 227, 234, 241, 250, 257)),
    ('b', 3, (49, 59, 69),
     (80, 89, 102, 111, 121, 131, 142, 151, 159, 170, 179, 189, 201,
      210, 220, 229, 239, 249, 259, 267, 275, 284, 293, 302, 312, 321)),
])
def test_exitbld_named_host_and_mixed_crews_match_bench(variant, mask, before, after):
    import build
    import sim
    m, t, _ = build.resolve('engine_exitbld', variant)
    e = sim.Sim(m, t, script='不打')
    # All displayed samples, keyed by the displayed logical frame. Area counts
    # include enclosed men: measured 22 before AND after exit, not just outdoors.
    expected = {f: [15, 22, 127, f] for f in before}
    expected.update({f: [mask, 22, 127, f] for f in after})
    got = {}
    tick = e.production.due

    def observe(frame):
        tick(frame)
        if frame in expected:
            got[frame] = [e.counters.get(k, 0) for k, _ in t.counters]

    e.production.due = observe
    e.advance(max(expected)+8)
    assert not e.unknown.get('EXIT_SPECIFIC_BUILDING', 0)
    assert got == expected
