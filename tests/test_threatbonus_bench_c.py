"""C-line named replays for the retail threat-bonus action; evidence in work/re/c_threatbonus_report.md."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('threatbonus_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_threatbonus_scripted_losses_replay_measured_waves():
    """A actual samples: 0/0/100/1, then 0/0/80/2, then 0/0/60/3.

    Capture seconds did not identify logic frames; compare the observed wave states only.
    This does not establish the effect of DISABLE and must not promote its inventory state.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_threatbonus', 'a')
    e = sim.Sim(m, t, script='不打')
    result = e.run(150.)
    rows = {tuple(row) for _, row in result.series}
    assert {(0, 0, 100, 1), (0, 0, 80, 2), (0, 0, 60, 3)} <= rows


@pytest.mark.xfail(strict=True, reason=(
    'engine_threatbonus:b: both actual rank-2 frames are 2893, including disabled s5; '
    'Sim has no death-threat protocol multiplier (both 5400). The action reward scope and same-frame '
    'player threat/multiplier are unobserved; see work/re/c_threatbonus_report.md.'))
def test_threatbonus_both_actual_rank_frames_as_the_bench():
    """B archived 0063: 2893/2893/40/3374; final 0129: 2893/2893/0/5708.

    Rank-frame counters are latched by once scripts; compare them after reaching that measured stage,
    without converting capture seconds to mission time or replacing the observed 2893 with 5400.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_threatbonus', 'b')
    e = sim.Sim(m, t, script='不打')
    result = e.run(380.)
    row = result.series[-1][1]
    assert row[2] == 0 and row[3] >= 5700, row
    assert row[:2] == [2893, 2893], row
