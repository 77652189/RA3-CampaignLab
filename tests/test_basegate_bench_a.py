"""A269: PLAYER_DISABLE / ENABLE_BASE_CONSTRUCTION, benched by name (checks/engine_basegate.py).

aibgate:a (bench 11-16, NOEXPECT): s1 AlliedBalanced woken at 10 s with 50000, base-disabled from frame 0, enabled at
70 s. Measured: money 50000 and 建筑数 1 from the wake to frame 1054, paying from f1054 (49993), 建筑数 2 at f1208.
engine_basegate:a: a script's press of the Allied yard's power-plant button pays nothing on either side (2000/2000
to f377), so a player's yard queue is no consumer the bench can read this way.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('basegate_simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)

pytestmark = pytest.mark.skipif(not simai.available(), reason='ra3model.ai not on this computer')

KEYS = ('CNV_AIBGate_Money', 'CNV_AIBGate_Built')


@pytest.fixture(scope='module')
def run():
    """aibgate:a to 85 s, the counters read at every frame the bench sampled."""
    w = simai_run.run('aibgate', 'a', until=1.0)
    got = {}
    for f in (163, 1000, 1050, 1208, 1250):
        w.advance(f - w.sim.frame_now())
        got[f] = [w.sim.counters.get(k, 0) for k in KEYS]
    return got


def test_aibgate_disabled_ai_spends_nothing_and_builds_nothing_until_enabled(run):
    """bench aibgate:a s14-s95 (f163-f1050): 50000 / 1 -- the base-disabled AI orders no structure."""
    for f in (163, 1000, 1050):
        assert run[f] == [50000, 1], (f, run[f])


def test_aibgate_enable_starts_the_ai_base(run):
    """bench aibgate:a: paying from f1054, the second structure at f1208 (10.3 s after the 70 s enable; aiskirm d's
    control, never disabled: 11 s after the wake). Read at f1250: paying and two structures."""
    money, built = run[1250]
    assert money < 50000 and built == 2, run[1250]
