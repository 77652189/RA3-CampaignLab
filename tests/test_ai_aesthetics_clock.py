"""E106 aesthetics replay on the repaired observer clock.

Named probe aiaeson:a, CampAIAesOnA_mcp_1112_155111 (5/5 PASS).
The bench clock anchors s16.1/f270 and s31.1/f495. Command frames
come directly from this run, with no wall-time scaling or frame shift.
Evidence and unresolved readiness: work/re/e106_aesthetics_clock.md.
"""
import importlib.util
import json
from types import SimpleNamespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')


@pytest.fixture(scope='module')
def aesthetics_record():
    world = simai.run('aiaeson', 'a', until=34,
                      lib=simai.model()['xmldata'].Library(), record=True)
    brain, = world.brains.values()
    return brain.rec


def test_aiaeson_clock_replay_has_live_retained_member(aesthetics_record):
    """Keep survival/membership prerequisites outside the expected failures."""
    names = set()
    for frame in (166, 196, 256, 461, 496):
        rows = [row for row in aesthetics_record['frames'] if row['frame'] == frame]
        assert len(rows) == 1, (frame, rows)
        member, = rows[0]['members']
        assert member['alive'], (frame, member)
        names.add(member['name'])
    assert len(names) == 1, names


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'D83 aiaeson:a emits at 191/461; E108 conditional gate replay passes, '
    'but integrated replay starts at 154 and misses 461. Enemy lookup timing and '
    'member destination/ready remain gaps; see work/re/e108_aesthetics_gate.md.'))
def test_aiaeson_clock_replays_stand_emission_frames(aesthetics_record):
    """Both measured orders, and absence of intervening repeats, are required."""
    orders = [o for o in aesthetics_record['orders'] if 150 <= o['frame'] <= 500
              and o['kind'] == 'move']
    assert [o['frame'] for o in orders] == [191, 461], orders


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E108 reaches the west command point but emits it at 154, before the measured 191. '
    'Enemy selection timing/member ready remain gaps; see work/re/e108_aesthetics_gate.md.'))
def test_aiaeson_clock_replays_last_command_points(aesthetics_record):
    """Logged command-point precision, independent of formation member positions."""
    expected = {166: (3850.0, 3400.0), 196: (1859.9, 3201.0),
                256: (1859.9, 3201.0), 496: (1859.9, 3201.0)}
    for frame, point in expected.items():
        orders = [o for o in aesthetics_record['orders'] if o['frame'] <= frame]
        assert orders, frame
        assert orders[-1]['point'] == pytest.approx(point, abs=0.05), (frame, orders[-1])


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
