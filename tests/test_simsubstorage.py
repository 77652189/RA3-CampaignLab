"""Named retail empty-payload control; not storage coverage. See work/re/e182_substorage.md."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench', ROOT / 'experimental/cnv/simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)


@pytest.mark.parametrize('variant', ['on', 'off'])
def test_substorage_empty_payload_measured_prefix(variant):
    """Bench reaches stage 7 after f300; final f435 stage remains unmeasured."""
    import build
    import sim

    mission, check, _ = build.resolve(f'engine_substorage_{variant}', 'a')
    result = sim.Sim(mission, check).run(20.)
    _, stages, alive, children = result.series[-1][1]
    assert (stages, alive, children) == (7, 1, 0)
