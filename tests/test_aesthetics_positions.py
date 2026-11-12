"""Same-frame UseAestheticsManager observations; evidence: work/re/e_aesthetics_e93.md."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)


def _observations():
    return json.loads((ROOT / 'tests/fixtures/aiaeson_positions.json').read_text(encoding='utf8'))


def _rings(pos, center):
    return tuple(int(abs(pos[0] - center[0]) <= r and abs(pos[1] - center[1]) <= r)
                 for r in (300, 900))


def _initial_guardian(data):
    first, = data['samples'][0]['members']
    ident = first[0]
    held = []
    for row in data['samples']:
        member, = [m for m in row['members'] if m[0] == ident]
        held.append((row['frame'], member[1:]))
    return held


def test_aesthetics_retail_initial_guardian_survives_full_excursion():
    """Track the first recruit, even if an extra member temporarily joins."""
    data = _observations()
    held = _initial_guardian(data)
    assert len(held) == 68 and (held[0][0], held[-1][0]) == (166, 1171)
    assert all(b[0] - a[0] == 15 for a, b in zip(held, held[1:]))
    transitions = []
    for frame, pos in held:
        rings = _rings(pos, data['center'])
        if not transitions or transitions[-1][1] != rings:
            transitions.append((frame, rings))
    assert transitions == [(166, (1, 1)), (256, (0, 1)), (451, (0, 0)),
                           (541, (0, 1)), (871, (0, 0))]


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'Enabled aesthetics same-frame Guardian trajectory differs from retail. '
    'Stand-point, order source, readiness and random stream remain gaps; '
    'see work/re/handoff-e.md and work/re/e_aesthetics_e93.md.'))
def test_aesthetics_model_replays_same_frame_initial_guardian_positions():
    """Compare actual game frames, with no fitted clock or altered circle thresholds."""
    data = _observations()
    w = simai.run('aiaeson', 'a', until=80, record=True, lib=simai.model()['xmldata'].Library())
    brain, = w.brains.values()
    frames = {r['frame']: r for r in brain.rec['frames'] if r['state_key'] == 'CNVStateTF'}
    pairs = []
    for frame, pos in _initial_guardian(data):
        assert frame in frames, ('missing model frame', frame)
        member, = [m for m in frames[frame]['members'] if m['name'] == 'UNIT - CNV AI Tank 1']
        assert member['alive'], frame
        pairs.append((frame, pos, member['pos']))
    # Occupancy must agree at every measured frame before checking integer log precision.
    mismatch = [(f, p, m) for f, p, m in pairs if _rings(p, data['center']) != _rings(m, data['center'])]
    assert not mismatch, mismatch
    assert all(abs(p[i] - m[i]) <= 1 for _, p, m in pairs for i in (0, 1)), pairs

