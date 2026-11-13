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
                   'model first world sample after f230 is state 8 with no member goal. Approach/engagement gap; '
                   'see work/re/e113_crush.md and work/re/handoff-e.md.')
def test_aicrush1t_model_plant_attack_precedes_crush(replay):
    brain, = replay.brains.values()
    # The world advances in coarse ticks. Keep both clocks; do not relabel a tactical frame as a world sample.
    row = next(r for r in brain.rec['frames'] if r['host_frame'] >= 230)
    assert 230 <= row['host_frame'] <= 240
    assert len(row['members']) == 4
    assert [m['goal'] for m in row['members']] == ['UNIT - CNV AI Far Plant'] * 4, (row['frame'], row['host_frame'])


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
