"""ReverseMove observer pair: exact engine samples, with unresolved consumer gaps.

Evidence and bounded inference: work/re/e115_reverse_aim.md.
"""
import importlib.util
import math
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)
import teamlog

OBSERVED = ROOT / 'tests/fixtures/e_reverse'


@pytest.mark.parametrize('build', ['airev1t', 'airev0t'])
def test_reverse_member_same_frame_observations(build):
    source = OBSERVED / (build + '.txt')
    rows = {r['frame']: r for r in teamlog.states(source)['T']}
    cohort = {3170, 3171, 3172, 3173}
    assert {m[0] for m in rows[21]['mem']} == cohort
    assert rows[21]['aim'] == {i: (0, None) for i in cohort}
    assert rows[21]['hd'] == {i: -180. for i in cohort}
    assert rows[230]['aim'] == {i: (3169, (3700., 2400.)) for i in cohort}
    assert rows[260]['mstate'] == rows[261]['mstate'] == 2
    for frame, row in rows.items():
        team, = teamlog.at(source, frame)
        assert team['frame'] == frame
        ids = {i for i, _, _ in team['ids']}
        assert cohort <= ids
        assert cohort <= row['hd'].keys()
        assert cohort <= row['aim'].keys()
    before, = teamlog.at(source, 260)
    after, = teamlog.at(source, 261)
    assert before['ids'] == [(3170, 3721, 2621), (3171, 3681, 2621),
                             (3172, 3665, 2682), (3173, 3750, 2661)]
    assert after['ids'] == [(3170, 3721, 2621), (3171, 3681, 2621),
                            (3172, 3663, 2678), (3173, 3754, 2661)]
    assert rows[261]['hd'] == {3170: -100., 3171: -92., 3172: -106., 3173: 0.}
    # INFERRED diagnostic only: displacement dotted with hull forward is
    # positive in these two moving members, not evidence of reverse travel.
    for member, dx, dy in ((3172, -2, -4), (3173, 4, 0)):
        angle = math.radians(rows[261]['hd'][member])
        assert dx * math.cos(angle) + dy * math.sin(angle) > 0


@pytest.fixture(scope='module', params=['airev1t', 'airev0t'])
def reverse_record(request):
    if not simai.available():
        pytest.skip('no ra3model.ai')
    snap = simai.Brain.snap

    def snapshot(brain, frame):
        start = len(brain.rec['frames'])
        result = snap(brain, frame)
        for row in brain.rec['frames'][start:]:
            row['host_frame'] = brain.host.frame
        return result

    with patch.object(simai.Brain, 'snap', snapshot):
        world = simai.run(request.param, 'a', until=19,
                          lib=simai.model()['xmldata'].Library(), record=True)
    brain, = world.brains.values()
    return request.param, brain


def test_reverse_named_replay_has_four_initial_members(reverse_record):
    build, brain = reverse_record
    first = next(r for r in brain.rec['frames'] if r['members'])
    assert len(first['members']) == 4, build
    assert all(m['alive'] for m in first['members'])


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E115 observer pair: engine initial four have valid far-plant object goals at '
    'host f263, model has none. Persistent member goal acquisition and body heading '
    'remain gaps; see work/re/e115_reverse_aim.md and work/re/handoff-e.md.'))
def test_reverse_named_replay_member_goal_at_engine_frame(reverse_record):
    """INFERRED model aim proxy cannot replace the engine persistent goal contract."""
    build, brain = reverse_record
    row = next(r for r in brain.rec['frames'] if r['frame'] == r['host_frame'] == 263)
    observed = next(r for r in teamlog.states(OBSERVED / (build + '.txt'))['T'] if r['frame'] == 263)
    assert len(row['members']) == 4
    expected = [bool(observed['aim'][i][0]) and observed['aim'][i][1] is not None
                for i in (3170, 3171, 3172, 3173)]
    assert [m['aim'] is not None for m in row['members']] == expected
