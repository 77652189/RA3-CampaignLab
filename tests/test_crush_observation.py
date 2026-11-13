"""Crush member observations from engine_aicrush:aicrush1t (D86).

Selected same-frame team/tstate pairs, with pointer tokens replaced only, are in
fixtures/e_crush/aicrush1t.txt. Source and comparison: work/re/e113_crush.md.
The preceding plant attack must agree before interpreting later crush pursuit.
"""
import importlib.util
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)
import teamlog

SOURCE = ROOT / 'tests/fixtures/e_crush/aicrush1t.txt'
TANKS = {3170, 3171, 3172, 3173}


def test_aicrush1t_tactical_target_precedes_member_attack():
    """E136: a tactical target exists before current enemy/member goals.

    Original D113 transition readings; see work/re/e136_crush_approach.md.
    No hostile-list contents can be inferred from these state samples alone.
    """
    rows = {r['frame']: r for r in teamlog.states(
        SOURCE.with_name('aicrush1t_approach.txt'))['T']}
    assert set(rows) == {211, 226, 230}
    for frame in (211, 226):
        row = rows[frame]
        assert (row['mstate'], row['prev'], row['tgt'], row['tact']) == (8, 8, -1, 3169)
        assert {i: row['aim'][i] for i in TANKS} == {i: (0, None) for i in TANKS}
        assert row['mem'] == [(i, 1, 0) for i in sorted(TANKS)]
    row = rows[230]
    assert (row['mstate'], row['prev'], row['tgt'], row['tact']) == (6, 8, 3169, 3169)
    assert row['mem'] == [(i, 10, 0) for i in sorted(TANKS)]
    assert {i: row['aim'][i] for i in TANKS} == {
        i: (3169, (3700., 2400.)) for i in TANKS}


def test_aicrush1t_crush_assignment_sources():
    """E127: assignment IDs are observable even though crush clears aim.

    Candidate eligibility is the shared hostile filter, not each member's
    complete crush eligibility or score. See work/re/e127_crush_sources.md.
    """
    source = str(SOURCE.with_name('aicrush1t_sources.txt'))
    orders = teamlog.target_orders(source, 'T')
    passes = {p['frame']: p for p in teamlog.keep_passes(source, 'T')}
    rows = {r['frame']: r for r in teamlog.states(source)['T']}
    approach = [o for o in orders if o['frame'] == 229]
    assert len(approach) == 4
    assert {o['mem'] for o in approach} == TANKS
    assert all((o['mstate'], o['src'], o['tgt'], o['ret'], o['wrote']) ==
               (6, 'all', 3169, 1, True) for o in approach)
    assert {i: rows[230]['aim'][i] for i in TANKS} == {
        i: (3169, (3700., 2400.)) for i in TANKS}
    assert {i: (until, decision) for i, until, decision in passes[259]['keep']} == {
        3170: (299, 'hold'), 3171: (295, 'hold'),
        3172: (298, 'hold'), 3173: (284, 'hold')}
    expected = {
        349: {3170: 3183, 3171: 3220, 3172: 3181, 3173: 3176},
        409: {3170: 3184, 3171: 3178, 3173: 3178},
        439: {3170: 3182, 3171: 3174, 3172: 3174, 3173: 3183},
    }
    for frame, targets in expected.items():
        assigned = [o for o in orders if o['frame'] == frame]
        assert len(assigned) == len(targets)
        assert {o['mem']: o['tgt'] for o in assigned} == targets
        assert all((o['mstate'], o['src'], o['ret'], o['wrote'], o['until']) ==
                   (2, 'score', 2, True, 0) for o in assigned)
        eligible = {i for i, ok in passes[frame]['cand'] if ok}
        assert set(targets.values()) <= eligible
        assert passes[frame]['keep'] == [(i, 0, 'go') for i in targets]
        assert {i: rows[frame + 1]['aim'][i] for i in TANKS} == {
            i: (0, None) for i in TANKS}
    # An empty per-member pass does not mean no hostile candidates existed.
    assert passes[379]['cand'] and passes[379]['keep'] == []


def test_aicrush1t_engine_goal_and_destination_readings():
    rows = {s['frame']: s for s in teamlog.states(SOURCE)['T']}
    assert set(rows) == {230, 345, 347, 350, 410, 440}
    for frame in rows:
        members = teamlog.at(SOURCE, frame)
        assert len(members) == 1
        assert TANKS <= {m[0] for m in members[0]['ids']}
    assert {i: rows[230]['aim'][i] for i in TANKS} == {
        i: (3169, (3700., 2400.)) for i in TANKS}
    assert {i: rows[345]['aim'][i] for i in TANKS} == {i: (3169, None) for i in TANKS}
    for frame in (347, 350, 410, 440):
        assert {i: rows[frame]['aim'][i] for i in TANKS} == {i: (0, None) for i in TANKS}
    expected = {
        350: [(3700., 2340.), (3700., 2400.), (3648., 2370.), (3730., 2462.)],
        410: [(3730., 2354.7), (3670., 2468.6), (3648., 2370.), (3670., 2468.6)],
        440: [(3670., 2354.7), (3768.5, 2442.5), (3768.5, 2442.5), (3703.2, 2349.5)],
    }
    for frame, points in expected.items():
        assert [rows[frame]['dest'][i] for i in sorted(TANKS)] == points
        assert rows[frame]['mstate'] == 2


@pytest.fixture(scope='module')
def replay():
    if not simai.available():
        pytest.skip('requires private engine model')
    snap, order = simai.Brain.snap, simai.Brain.order

    def snapshot(brain, frame):
        start = len(brain.rec['frames'])
        result = snap(brain, frame)
        for row in brain.rec['frames'][start:]:
            row['host_frame'] = brain.host.frame
        return result

    def command(brain, unit, kind, arg):
        start = len(brain.rec['orders'])
        result = order(brain, unit, kind, arg)
        for row in brain.rec['orders'][start:]:
            row['host_frame'] = brain.host.frame
        return result

    with patch.object(simai.Brain, 'snap', snapshot), patch.object(simai.Brain, 'order', command):
        return simai.run('aicrush1t', 'a', until=30, record=True)


@pytest.mark.xfail(strict=True, reason='aicrush1t f230: engine four members target the far plant; '
                   'E136 model recognizes the plant but already sees hostile infantry and has no member plant goals. '
                   'Movement/candidate-input gap; see work/re/e136_crush_approach.md and work/re/handoff-e.md.')
def test_aicrush1t_model_plant_attack_precedes_crush(replay):
    brain, = replay.brains.values()
    # The world advances in coarse ticks. Keep both clocks; do not relabel a tactical frame as a world sample.
    row = next(r for r in brain.rec['frames'] if r['host_frame'] >= 230)
    assert 230 <= row['host_frame'] <= 240
    assert len(row['members']) == 4
    assert (row['state'], row['foe']) == (6, 'UNIT - CNV AI Far Plant'), row
    assert [m['goal'] for m in row['members']] == ['UNIT - CNV AI Far Plant'] * 4, row


@pytest.mark.xfail(strict=True, reason='aicrush1t f350: engine four new crush destinations with no goal object; '
                   'model last orders are tactical f301 / world f308, with different points. Earlier approach already diverges; '
                   'see work/re/e113_crush.md and work/re/handoff-e.md.')
def test_aicrush1t_model_first_crush_destinations(replay):
    brain, = replay.brains.values()
    latest = {}
    for order in brain.rec['orders']:
        if order['host_frame'] <= 350 and 'CNV AI Inf ' in order['member']:
            latest[order['member']] = order
    assert len(latest) == 4
    assert {o['kind'] for o in latest.values()} == {'move'}
    # Compare the published precision; do not map unrelated runtime IDs by order.
    actual = Counter(tuple(round(c, 1) for c in o['point']) for o in latest.values())
    observed = next(s for s in teamlog.states(SOURCE)['T'] if s['frame'] == 350)
    assert actual == Counter(observed['dest'][i] for i in TANKS)
