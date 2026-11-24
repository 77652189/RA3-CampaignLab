"""E108: the stand's enemy gate replayed on the bench's own D83 calls (aiaeson:a).

The integrated replay's order frames and points are readings now:
checks/engine_aiaesthetics.readings.toml::aiaeson_stand_moves_at_f191_and_f461 (mismatch).
Evidence: work/re/e106_aesthetics_clock.md, work/re/e108_aesthetics_gate.md.
"""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')


def test_aiaeson_d83_enemy_gate_replays_actual_calls():
    """Replay observed gate inputs, independently of unresolved world/formation inputs.

    aiaeson:a / CampAIAesOnA_mcp_1112_161459. These are conditional
    enemy-mode calls, not a claim that the model finds the same enemy at that frame.
    See work/re/e108_aesthetics_gate.md for raw extraction and remaining gaps.
    """
    rows = json.loads((ROOT / 'tests/fixtures/ai_aesthetics_d83.json').read_text(encoding='utf8'))
    assert len(rows) == 107
    # D83's capture skips two calls near its reported s65-66 gap.
    assert [r['frame'] for r in rows] == [f for f in range(160, 1781, 15) if f not in (1075, 1090)]
    # Alive retained member and command precision are measured prerequisites.
    assert all(3166 in {m[0] for m in r['member']} for r in rows)
    assert all(r['member'][0][0] == 3166 and len(r['member']) == 1
               for r in rows if r['frame'] <= 1510)
    assert [r['frame'] for r in rows if len(r['member']) > 1] == [1735, 1765]
    assert rows[2]['member'] == [[3166, 1, 0]]
    assert rows[2]['dest']['3166'] == [3850.0, 3400.0]
    tc = simai.model()['tactics']
    if not hasattr(tc.TacticsBlock, '_stand_enemy_ready'):
        pytest.skip('EngineModel predates the D83 aesthetics consumer')
    block = tc.TacticsBlock.__new__(tc.TacticsBlock)
    run = SimpleNamespace(extra={})
    emitted, observed, ready_calls = [], [], []
    for row in rows:
        frame = row['frame']
        def measured_ready(run, frame):
            ready_calls.append(frame)
            return bool(row['gate'])
        block._ready = measured_ready
        assert bool(run.extra.get('stand_enemy')) == bool(row['mode'])
        # The first two observations have no enemy. Do not infer enemy lookup
        # from the team's centre or replace it with the tactical target.
        if row['mode_after']:
            if block._stand_enemy_ready(run, frame):
                emitted.append(frame)
        else:
            assert not row['orders']
        assert bool(run.extra.get('stand_enemy')) == bool(row['mode_after'])
        if row['orders']:
            order, = row['orders']
            observed.append((frame, order['frame']))
            assert order['point'][:2] == pytest.approx((1859.9, 3201.0), abs=0.05)
    assert emitted == [190, 460, 1510]
    assert observed == [(190, 191), (460, 461), (1510, 1511)]
    assert ready_calls == [r['frame'] for r in rows if r['mode']]
    assert sum(r['mode'] == 1 and r['gate'] == 0 for r in rows) == 102
