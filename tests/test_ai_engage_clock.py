"""E107 named EngageHostileTargets pair on the repaired observer clock.

Exact observations and unresolved acquisition boundary: work/re/e114_engage_aim.md.
No scripted special-power press is present in either named check.
"""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)
import teamlog

OBSERVED = ROOT / 'tests/fixtures/e_engage'


def test_engage_state33_replays_observed_goal_writes():
    """Replay D106's selected-target writes, not its unknown event/selection.

    The event time, candidate and passing gates are observed inputs. Neither
    first acquisition nor the whole named mission is claimed by this test.
    """
    if not simai.available():
        pytest.skip('no ra3model.ai')
    mc, sp = simai.model()['micro'], simai.model()['specials']
    evidence = json.loads((OBSERVED / 'aiegoff_reactions.json').read_text())
    assert (evidence['build'], evidence['check']) == ('aiegoff', 'a')
    targets = {i: sp.Thing((0, 0), name=str(i)) for i in (3167, 3168)}
    units = {i: mc.Unit(str(i)) for i in (3170, 3171)}
    writes = []
    for event in evidence['events']:
        unit = units[event['member']]
        assert (int(unit.target.name) if unit.target else 0) == event['old_goal']
        assert mc.react_to_threat(
            unit, targets[event['new_goal']], unit_state=event['unit_state'],
            ai_available=True, response_disabled=False, can_retaliate=True)
        writes.append((event['frame'], int(unit.target.name)))
        assert units[3170].target is None
    assert writes == [(431, 3168), (469, 3167)]


@pytest.mark.parametrize('gate', ['ai_unavailable', 'dead', 'disabled', 'cannot_retaliate',
                                'no_candidate', 'unsupported_state'])
def test_engage_state33_preserves_goal_when_reaction_cannot_apply(gate):
    """Keep caller-supplied gates and unsupported states outside a successful write."""
    if not simai.available():
        pytest.skip('no ra3model.ai')
    mc, sp = simai.model()['micro'], simai.model()['specials']
    old, new = sp.Thing((0, 0), name='old'), sp.Thing((1, 0), name='new')
    unit = mc.Unit('member', target=old, health=0 if gate == 'dead' else 100)
    args = dict(unit_state=8 if gate == 'unsupported_state' else 33,
                ai_available=gate != 'ai_unavailable', response_disabled=gate == 'disabled',
                can_retaliate=gate != 'cannot_retaliate')
    candidate = None if gate == 'no_candidate' else new
    if gate == 'unsupported_state':
        with pytest.raises(NotImplementedError):
            mc.react_to_threat(unit, candidate, **args)
    else:
        assert not mc.react_to_threat(unit, candidate, **args)
    assert unit.target is old


@pytest.mark.parametrize('build', ['aiegon', 'aiegoff'])
def test_engage_member_goal_observations(build):
    """Retain member identity, valid object goals and actual per-member destinations."""
    source = OBSERVED / (build + '.txt')
    rows = {r['frame']: r for r in teamlog.states(source)['T']}
    for frame, row in rows.items():
        assert {m[0] for m in row['mem']} == {3170, 3171}
        team, = teamlog.at(source, frame)
        assert team['frame'] == frame
        assert {m[0] for m in team['ids']} == {3170, 3171}
        assert set(row['hd']) == {3170, 3171}
    assert rows[345]['aim'] == {3170: (3171, (3890., 2930.)), 3171: (0, None)}
    assert rows[353]['aim'] == {3170: (0, None), 3171: (0, None)}
    assert rows[353]['dest'] == {i: (3906.3, 2626.5) for i in (3170, 3171)}
    if build == 'aiegon':
        assert rows[376]['aim'] == {i: (3168, (3911., 2706.3)) for i in (3170, 3171)}
        assert rows[376]['mstate'] == 2
    else:
        for frame in (431, 443):
            assert rows[frame]['aim'] == {3170: (0, None), 3171: (3168, (3911., 2706.3))}
            assert rows[frame]['dest'] == {3170: (3906.3, 2626.5), 3171: (3911., 2706.3)}
            assert rows[frame]['mstate'] == 8


@pytest.fixture(scope='module', params=['aiegon', 'aiegoff'])
def engage_record(request):
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
        world = simai.run(request.param, 'a', until=45,
                          lib=simai.model()['xmldata'].Library(), record=True)
    brain, = world.brains.values()
    first = next(row for row in brain.rec['frames'] if row['members'])
    cohort = {member['name'] for member in first['members']}
    return request.param, brain, cohort


def test_engage_clock_recruits_initial_pair(engage_record):
    """Keep the recruited, live first-cohort prerequisite outside xfail."""
    build, brain, cohort = engage_record
    assert len(cohort) == 2, (build, cohort)
    first = next(row for row in brain.rec['frames'] if row['members'])
    assert all(member['alive'] for member in first['members']), (build, first)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E107 first-cohort movement diverges before power selection; original '
    'recruitment/formation and targetless marching remain unresolved. '
    'See work/re/e107_engage_clock.md and work/re/handoff-e.md.'))
def test_engage_clock_replays_first_cohort_movement(engage_record):
    """Compare actual bench movement emission; formation offsets stay a gap."""
    build, brain, cohort = engage_record
    expected = {'aiegon': 352}
    orders = [order for order in brain.rec['orders']
              if order['member'] in cohort and order['kind'] in ('move', 'attack-move')]
    if build == 'aiegoff':
        # No player-issued move/formation orders after recruitment in the bench log.
        assert orders == [], orders
        return
    frame = expected[build]
    first = orders[0]
    assert first['frame'] == frame, (build, first)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E114 exact host-frame member goal validity diverges: on f353 engine has no '
    'goal while model infers enemies; off f443 engine second initial member has '
    'a valid goal while model initial pair has none. Autonomous goal acquisition '
    'and holding contract missing; see work/re/e114_engage_aim.md and work/re/handoff-e.md.'))
def test_engage_clock_replays_member_goal_validity(engage_record):
    """Compare the initial pair at the same host frame, without replacement units.

    Model aim is still an INFERRED proxy, not a persistent object-goal field.
    Pair by production order; do not equate runtime object IDs across runs.
    """
    build, brain, cohort = engage_record
    frame = {'aiegon': 353, 'aiegoff': 443}[build]
    row = next(r for r in brain.rec['frames'] if r['frame'] == r['host_frame'] == frame)
    members = sorted((m for m in row['members'] if m['name'] in cohort), key=lambda m: m['name'])
    assert len(members) == 2 and all(m['alive'] for m in members)
    observed = next(r for r in teamlog.states(OBSERVED / (build + '.txt'))['T'] if r['frame'] == frame)
    expected = [bool(observed['aim'][i][0]) and observed['aim'][i][1] is not None for i in (3170, 3171)]
    assert [m['aim'] is not None for m in members] == expected, (frame, members, observed['aim'])


@pytest.mark.parametrize('build', ['aiegon', 'aiegoff'])
def test_engage_target_source_observations(build):
    """Keep the observed assignment boundary distinct from autonomous aim.

    State-2 assignment is visible on the enabled side. The disabled side's
    state-8 goal has no team assignment record: its source remains a gap.
    Raw evidence and the observation request: work/re/e126_engage_sources.md.
    """
    source = str(OBSERVED / (build + '_sources.txt'))
    rows = {r['frame']: r for r in teamlog.states(source)['T']}
    orders = teamlog.target_orders(source, 'T')
    passes = teamlog.keep_passes(source, 'T')
    assert rows[353]['aim'] == {3170: (0, None), 3171: (0, None)}
    if build == 'aiegon':
        first = [o for o in orders if o['frame'] == 375]
        assert len(first) == 2
        assert {o['mem'] for o in first} == {3170, 3171}
        assert all((o['mstate'], o['src'], o['tgt'], o['wrote']) ==
                   (2, 'score', 3168, True) for o in first)
        assignment_pass = next(p for p in passes if p['frame'] == 375)
        assert assignment_pass['cand'] == [(3168, True), (3167, True)]
        assert assignment_pass['keep'] == [(3170, 0, 'go'), (3171, 0, 'go')]
        assert rows[376]['mstate'] == 2
        assert rows[376]['aim'] == {i: (3168, (3911., 2706.3)) for i in (3170, 3171)}
    else:
        assert orders == [] and passes == []
        for frame in (431, 443):
            assert rows[frame]['mstate'] == 8
            assert rows[frame]['aim'] == {3170: (0, None), 3171: (3168, (3911., 2706.3))}
