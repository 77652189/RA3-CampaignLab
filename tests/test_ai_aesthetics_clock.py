"""E106 aesthetics replay on the repaired observer clock.

Named probe aiaeson:a, CampAIAesOnA_mcp_1112_155111 (5/5 PASS).
The bench clock anchors s16.1/f270 and s31.1/f495. Command frames
come directly from this run, with no wall-time scaling or frame shift.
Evidence and unresolved readiness: work/re/e106_aesthetics_clock.md.
"""
import importlib.util
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
    'E106 repaired-clock aiaeson:a issues stand orders at frames 191 and 461; '
    'baseline starts at 154 and repeats; E96 candidate starts at 214 and repeats. '
    'Readiness/formation command gating unresolved; see work/re/e106_aesthetics_clock.md.'))
def test_aiaeson_clock_replays_stand_emission_frames(aesthetics_record):
    """Both measured orders, and absence of intervening repeats, are required."""
    orders = [o for o in aesthetics_record['orders'] if 150 <= o['frame'] <= 500
              and o['kind'] == 'move']
    assert [o['frame'] for o in orders] == [191, 461], orders


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E106 repaired-clock aiaeson:a retains the west stand command; baseline stands east. '
    'Selection and ready consumers remain gaps; see work/re/e106_aesthetics_clock.md.'))
def test_aiaeson_clock_replays_last_command_points(aesthetics_record):
    """Logged command-point precision, independent of formation member positions."""
    expected = {166: (3850.0, 3400.0), 196: (1859.9, 3201.0),
                256: (1859.9, 3201.0), 496: (1859.9, 3201.0)}
    for frame, point in expected.items():
        orders = [o for o in aesthetics_record['orders'] if o['frame'] <= frame]
        assert orders, frame
        assert orders[-1]['point'] == pytest.approx(point, abs=0.05), (frame, orders[-1])
