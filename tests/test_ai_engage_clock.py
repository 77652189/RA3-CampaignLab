"""E107 named EngageHostileTargets pair on the repaired observer clock.

Exact observations and unresolved acquisition boundary: work/re/e114_engage_aim.md.
No scripted special-power press is present in either named check.
"""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)
import teamlog

OBSERVED = ROOT / 'tests/fixtures/e_engage'


def test_engage_command_goal_chain_observations():
    """Assert D107's ordered observations, including a write and clear in one frame.

    This is evidence validation, not natural mission replay. Command names are
    descriptive; special-power identity and upstream eligibility remain gaps.
    See work/re/e131_engage_inputs.md for the raw-source mapping.
    """
    evidence = json.loads((OBSERVED / 'aiegoff_commands.json').read_text())
    assert (evidence['build'], evidence['check'], evidence['run']) == (
        'aiegoff', 'a', 'CampAIEgOffA_mcp_1113_065607')
    goals = {3170: 0, 3171: 0}
    trace = []
    for event in evidence['goals']:
        assert goals[event['member']] == event['old']
        goals[event['member']] = event['new']
        trace.append((event['frame'], event['member'], event['new']))
    assert trace == [(320, 3170, 3171), (353, 3170, 0),
                     (408, 3171, 3168), (408, 3171, 0),
                     (431, 3171, 3168), (469, 3171, 3167),
                     (496, 3170, 0), (512, 3171, 0)]
    clears = [e for e in evidence['goals'] if e['source'] == 'clear_command']
    assert [(e['command_frame'], e['frame']) for e in clears] == [
        (352, 353), (408, 408), (511, 512)]
    reactions = [e for e in evidence['goals'] if e['source'] == 'threat_reaction']
    assert [(e['frame'], e['member'], e['unit_state'], e['old'], e['new'])
            for e in reactions] == [(431, 3171, 33, 0, 3168), (469, 3171, 33, 3168, 3167)]
    assert goals == {3170: 0, 3171: 0}


def test_engage_hunt_command_state_contract():
    """D112 command/state observations; D113 requires arrival before idle.

    Named natural replay below remains the acceptance gate for promotion.
    """
    if not simai.available():
        pytest.skip('no ra3model.ai')
    mc = simai.model()['micro']
    evidence = json.loads((OBSERVED / 'aiegoff_commands.json').read_text())
    states = {i: mc.HuntGoal() for i in (3170, 3171)}
    for event in evidence['goals']:
        state = states[event['member']]
        if event['source'] == 'clear_command':
            state.command('pursuit')
            assert (state.state, state.target) == (33, None)
        elif event['source'] == 'threat_reaction':
            assert state.state == event['unit_state']
            state.target = event['new']
    state = states[3171]
    state.command('live')
    state.target = 'skill-target'
    state.charge_finished()
    assert (state.state, state.pursuit, state.target) == (33, 'live', None)
    state.expire(lambda t: t == 'live')
    assert state.state == 33
    state.expire(lambda t: False)
    assert state.state == 33
    state.target = 'retained-goal'
    state.expire(lambda t: False, arrived=True)
    assert state.state == 16
    assert state.target == 'retained-goal'
    # Regression: a Hunt member must read its persistent goal even when the
    # movement simulator still has an ordered/chased enemy beside it.
    brain = simai.Brain.__new__(simai.Brain)
    old = SimpleNamespace(alive=True)
    body = SimpleNamespace(name='member', goal=old, chase=old)
    brain._hunt_goals = {'member': mc.HuntGoal()}
    held = brain._hunt_goals['member']
    held.command(old)
    assert brain.aim_of(body, 100) is None
    held.target = old
    assert brain.aim_of(body, 100) is old
    old.alive = False
    assert brain.aim_of(body, 100) is None


def test_engage_dead_pursuit_arrival_observations():
    """D113 late state changes retain goals; arrival geometry stays INFERRED.

    Arrival is supplied here, not derived from observed frame numbers in the
    model. Natural on/off replay remains the promotion gate below. The engine's
    transient state 0 is not separately simulated by the atomic expire call.
    """
    if not simai.available():
        pytest.skip('no ra3model.ai')
    mc = simai.model()['micro']
    evidence = json.loads((OBSERVED / 'aiegoff_arrival.json').read_text())
    events = evidence['events']
    assert [(e['frame'], e['member'], e['old'], e['new'], e['goal']) for e in events] == [
        (510, 3171, 33, 0, 3167), (510, 3171, 0, 16, 3167),
        (515, 3170, 33, 0, 0), (515, 3170, 0, 16, 0)]
    for event in events[1::2]:
        state = mc.HuntGoal()
        pursuit = SimpleNamespace(alive=True)
        state.command(pursuit)
        state.target = event['goal'] or None
        state.expire(lambda t: t.alive, arrived=True)
        assert state.state == 33  # arrival alone cannot finish a live pursuit
        pursuit.alive = False
        state.expire(lambda t: t.alive)
        assert state.state == 33  # death alone cannot finish it either
        state.expire(lambda t: t.alive, arrived=True)
        assert (state.state, state.target or 0) == (event['new'], event['goal'])


def test_engage_dead_pursuit_continues_cancelled_path():
    """Host regression: retain the last-position movement after combat cancels it.

    Positions are synthetic; the body's arrival radius remains INFERRED.
    """
    if not simai.available():
        pytest.skip('no ra3model.ai')
    state = simai.model()['micro'].HuntGoal()
    pursuit = SimpleNamespace(alive=False, x=100., y=0.)
    state.command(pursuit)
    retained = SimpleNamespace(alive=False)
    state.target = retained
    body = SimpleNamespace(name='member', alive=True, x=0., y=0., radius=10.,
                           path=[], goal=retained)
    brain = simai.Brain.__new__(simai.Brain)
    moves = []
    brain.sim = SimpleNamespace(body=lambda name: body,
                                order_move=lambda *args: moves.append(args))
    brain._hunt_goals = {'member': state}
    brain.hunt_threats(1)  # no partition scan before the first eligible frame
    assert state.state == 33 and state.target is retained
    assert moves == [(body, (100., 0.), True)]
    assert body.goal is None
    body.x = 100.
    brain.hunt_threats(2)
    assert state.state == 16 and state.target is retained
    assert len(moves) == 1


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


def test_engage_clock_replays_first_cohort_movement(engage_record, request):
    """Compare actual bench movement emission; formation offsets stay a gap."""
    build, brain, cohort = engage_record
    if build == 'aiegon':
        request.node.add_marker(pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
            'E137 D113 arrival fix leaves enabled-side movement emission divergent '
            'before power selection; see work/re/e137_engage_arrival.md '
            'and work/re/handoff-e.md.')))
    expected = {'aiegon': 352}
    orders = [order for order in brain.rec['orders']
              if order['member'] in cohort and order['kind'] in ('move', 'attack-move')]
    if build == 'aiegoff':
        # No player-issued move/formation orders after recruitment in the bench log.
        assert orders == [], orders
        return
    frame = expected[build]
    assert orders, (build, 'no movement emission')
    first = orders[0]
    assert first['frame'] == frame, (build, first)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E137 D113 death-to-arrival rule is connected, but natural '
    'movement still diverges before acquisition: on f353 two goals '
    'instead of none; off f443 no goals instead of the second member goal. '
    'Model off members are already west of the observed scan cells. Grid '
    'failure boundaries and command-source timing remain INFERRED. '
    'See work/re/e137_engage_arrival.md '
    'and work/re/handoff-e.md.'))
def test_engage_clock_replays_member_goal_validity(engage_record):
    """Compare the initial pair at the same host frame, without replacement units.

    Hunt members use persistent unit goals; other units retain the old proxy.
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


def test_engage_partition_scans_replay_observed_candidates():
    """D109 candidate replay, with observed cell-change events as inputs.

    Cell geometry and candidate eligibility are NOT reconstructed by this test.
    No claim of natural named-mission replay or Engage promotion is made.
    See work/re/e132_partition_threats.md for the remaining world-input gap.
    """
    if not simai.available():
        pytest.skip('no ra3model.ai')
    mc, sp = simai.model()['micro'], simai.model()['specials']
    evidence = json.loads((OBSERVED / 'aiegoff_scans.json').read_text())
    assert (evidence['build'], evidence['check'], evidence['run']) == (
        'aiegoff', 'a', 'CampAIEgOffA_mcp_1113_080446')
    things = {}
    def thing(i):
        return things.setdefault(i, sp.Thing((0, 0), name=str(i))) if i else None
    units = {i: mc.Unit(str(i)) for i in (3170, 3171)}
    queue = mc.PartitionThreats()
    writes = []
    scans = evidence['scans']
    for event in scans:
        # The fixture records AFTER each scan. Earlier state-7/26 reactions
        # and skill/clear commands are outside this bounded state-33 replay.
        if event['state'] != 33 or event['frame'] < 353:
            continue
        if event['frame'] == 512:
            units[3171].target = None  # D107's independently observed clear.
        unit = units[event['member']]
        def candidates(rows, second):
            return [mc.ThreatCandidate(thing(row[0]), enemy=row[2] == 0,
                    excluded=row[1] == -1, requires_current_target=row[1] == 8,
                    in_range=(row[3] == 1 if second else True)) for row in rows]
        first = candidates(event['first'], False)
        second = candidates(event['second'], True)
        current = thing(event['current'])
        selected = mc.select_threat(first, second, current)
        assert (int(selected.name) if selected else 0) == event['selected']
        # Distinct opaque cells stand for the observed queue events, not a
        # guessed world grid. Duplicate moves in one frame drain only once.
        queue.moved(unit, ('observed', event['frame']), event['frame'])
        queue.moved(unit, ('observed-again', event['frame']), event['frame'])
        gates = dict(unit_state=33, ai_available=True,
                     response_disabled=False, can_retaliate=True)
        calls = []
        def query(member):
            calls.append(member.name)
            return first, second, current, gates
        written = queue.drain(query)
        assert calls == [unit.name]
        assert bool(written) == event['written']
        assert (int(unit.target.name) if unit.target else 0) == event['goal']
        if written:
            writes.append((event['frame'], event['member'], int(unit.target.name)))
    assert writes == [(431, 3171, 3168), (469, 3171, 3167)]


def test_engage_partition_selection_contract():
    """Boundary checks, not additional engine observations."""
    if not simai.available():
        pytest.skip('no ra3model.ai')
    mc = simai.model()['micro']
    a, b, c = object(), object(), object()
    candidate = mc.ThreatCandidate
    assert mc.select_threat([], [candidate(a, True), candidate(b, True)]) is b
    assert mc.select_threat([], [candidate(a, True), candidate(b, True)], a) is a
    assert mc.select_threat([], [candidate(a, False), candidate(b, True, excluded=True)]) is None
    assert mc.select_threat([], [candidate(a, True, requires_current_target=True)], b) is None
    assert mc.select_threat([candidate(a, True, in_range=False)], []) is None
    assert mc.select_threat([], [candidate(a, True, in_range=False)]) is None
    unit = mc.Unit('member', target=c)
    queue = mc.PartitionThreats()
    queue.moved(unit, (0, 0), 3)
    assert queue.drain(lambda _: pytest.fail('startup frame scanned')) == []
    queue.moved(unit, (0, 0), 4)
    assert queue.drain(lambda _: pytest.fail('unchanged cell scanned')) == []
    queue.moved(unit, (1, 0), 5)
    with pytest.raises(ValueError, match='drain'):
        queue.moved(unit, (2, 0), 6)
    gates = dict(unit_state=33, ai_available=True, response_disabled=False, can_retaliate=True)
    assert queue.drain(lambda _: ([], [], None, gates)) == []
    assert unit.target is c
