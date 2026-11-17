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
    assert e.series[0][1] == [0, 0, 0, 255]
    assert e.series[-1][1] == [2, 1, 0, 240]
    assert (sim.GAP_ACTION, 'SET_PLAYER_KILLS_OF_TYPE_TO_COUNTER') not in e.unmodeled


@pytest.mark.xfail(strict=True, reason=(
    'engine_killcount:a at screenshot s22-s23 the alive mask is 248, not 240; '
    'script death is first captured at s25. Screenshot time is not aligned to '
    'script logic frames; keep original s22 window, see work/re/c_killcount_report.md.'))
def test_killcount_original_script_death_window_matches_bench():
    import build
    import sim
    m, t, _ = build.resolve('engine_killcount', 'a')
    e = sim.Sim(m, t).run(22.)
    assert e.series[-1][1] == [2, 1, 0, 248]
