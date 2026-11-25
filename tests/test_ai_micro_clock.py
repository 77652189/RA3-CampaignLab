"""AIMicroManagerData.UpdateTime: the switch's on / off effect is the micro update period (D rounds 146 / 147).

Bench aimicupft / aimicupst (benches/ai/tactics/scenes.py#aimicro_bench, engine_aimicro:a; E102 runs CampMicObsFastA_mcp_1112_144315
/ CampMicObsSlowA_mcp_1112_144547) differ only in the micro manager's UpdateTime (0.5 s / 4 s). Fixtures
tests/fixtures/d_microclock/*_cmds.txt keep the AI's order lines (cmd:) minus the host's own. The micro update
re-selects each member (0x1f5 by id) before it orders it, so the frames of those selects are the update beats:
fast 376, 384, 392, 400, ... (all 8 apart or a multiple of 8), slow 405, 466, 527 (61 apart: a float32 sum of 1/15 a
frame reaches 4.0 on the 61st frame, not round(4 x 15) = 60). The model (tactics.MicroData.update_frames) gives the
same periods; the phase (bench first beat 376 / 405, model 394 / 391) and the first-charge frame stay INFERRED
(mismatch readings in experimental/cnv/benches/ai/tactics/readings.toml#engine_aimicro).
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)
import teamlog

OBSERVED = ROOT / 'tests/fixtures/d_microclock'
HOST = 36
PERIOD = {'aimicupft': 8, 'aimicupst': 61}
SELECT_BY_ID = 0x1f5


def _beats(frames):
    return sorted(set(frames))


def _gaps(beats):
    return [b - a for a, b in zip(beats, beats[1:])]


@pytest.mark.parametrize('build', ['aimicupft', 'aimicupst'])
def test_bench_member_orders_beat_at_the_update_time(build):
    cmds = teamlog.commands(str(OBSERVED / (build + '_cmds.txt')), types=(SELECT_BY_ID,))
    beats = _beats(f for f, _, args in cmds if args[-1] != HOST)
    gaps = _gaps(beats)
    if build == 'aimicupft':
        assert beats[:4] == [376, 384, 392, 400], beats
        assert min(gaps) == 8 and all(g % 8 == 0 for g in gaps), gaps
    else:
        assert beats == [405, 466, 527], beats


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
@pytest.mark.parametrize('build', ['aimicupft', 'aimicupst'])
def test_model_member_orders_beat_at_the_update_time(build):
    w = simai_run.run(build, 'a', until=40, lib=simai.model()['xmldata'].Library(), record=True)
    brain, = w.brains.values()
    orders = brain.rec['orders']
    first = [o['member'] for o in orders if o['kind'] == 'hunt'][:2]   # the first team the tactic made
    start = min(o['frame'] for o in orders if o['member'] in first and o['kind'] != 'hunt')
    beats = _beats(o['frame'] for o in orders if o['member'] in first and o['frame'] >= start)
    gaps = _gaps(beats)
    p = PERIOD[build]
    assert len(beats) >= 3 and min(gaps) == p and all(g % p == 0 for g in gaps), (build, beats)
