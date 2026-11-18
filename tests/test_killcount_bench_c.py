"""C named kill-credit counter replays; evidence: work/re/c_killcount_report.md."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('killcount_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.mark.parametrize('variant', ['a', 'b'])
def test_killcount_native_type_and_player_match_bench(variant):
    import build
    import sim
    m, t, _ = build.resolve('engine_killcount', variant)
    e = sim.Sim(m, t).run(25.)
    assert (sim.GAP_ACTION, 'SET_PLAYER_KILLS_OF_TYPE_TO_COUNTER') not in e.unmodeled
