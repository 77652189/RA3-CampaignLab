"""Bridge target native evidence and named mission replays; work/re/c_bridge_report.md."""
import importlib.util
import json
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bridge_simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
BUILDS = ('aibridgeon', 'aibridgeoff')
MEASURED = json.loads((ROOT / 'tests/fixtures/bridge_target_measurements.json').read_text(encoding='utf-8'))


def native(build, state):
    import teamlog
    rows = teamlog.target_picks(str(ROOT / f'tests/fixtures/{build}_target_picks.txt'))
    return [r for r in rows if r['state_id'] == teamlog.state_hash(state)]


@lru_cache(maxsize=2)
def replay(build):
    if not simai.available():
        pytest.skip('no private AI model')
    return simai.run(build, 'a', until=MEASURED[build]['last_log_frame'] / simai.FPS)


def model_picks(w, state):
    return [text for _, kind, text in w.brains['Soviet_1'].ai.log
            if kind == 'target' and text.startswith(state + ': ')]


@pytest.mark.parametrize('build', BUILDS)
def test_bridge_target_contract(build):
    import build as builder
    from parts import contract, merged
    m, t, name = builder.resolve(build, 'a')
    assert len(name) <= 15 and name.isalnum()
    assert not contract(merged(m, t))
    assert len(t.counters) == 4
    assert [next(o.flags for o in m.objects if o.name == m.role(f'bridge {i}').name)
            for i in range(2)] == (
        [16, 32] if build == 'aibridgeon' else [0, 0])
    assert not any(o.template.startswith('HB_Bridge') for o in m.map.OBJECTS)


@pytest.mark.parametrize('build,readings,ids', [
    ('aibridgeon', '322 33 1 0', (1, None)),
    ('aibridgeoff', '111 11 1 1', (3140, 3141)),
])
def test_bridge_target_native_readings(build, readings, ids):
    measured = MEASURED[build]
    assert measured['verdict'] == 'PASS'
    assert len(measured['expectations']) == 2
    assert all(line.startswith('PASS ') for line in measured['expectations'])
    assert measured['readings'].endswith(': ' + readings)
    rows = native(build, 'CNVStateTP')
    assert rows and all(r['frame'] == 16 and r['index'] == 0 and not r['found']
                        and r['target'] is None and r['count'] == 0 and not r['candidates'] for r in rows)
    for i, tid in enumerate(ids):
        named = native(build, f'CNVBridgeNamedState{i}')
        assert named and all(r['frame'] == 16 and r['found'] == (tid is not None)
                             and r['target'] == tid for r in named)
        if tid is not None:
            assert all(r['point'] == ((2250.0 if i == 0 else 2950.0), 4200.0) for r in named)


@pytest.mark.parametrize('build,i', [('aibridgeon', 0), ('aibridgeoff', 0), ('aibridgeoff', 1)])
def test_bridge_target_named_survivor_replay(build, i):
    w = replay(build)
    brain = w.brains['Soviet_1']
    state = f'CNVBridgeNamedState{i}'
    rows = native(build, state)
    assert rows and all(r['found'] for r in rows)
    body = w.sim.bodies[w.sim.m.role(f'bridge {i}').name]
    picks = model_picks(w, state)
    assert picks and all(text.endswith(f'-> [{brain.tid(body)}]') for text in picks)
    assert all((body.x, body.y) == r['point'] for r in rows)


@pytest.mark.parametrize('build', [
    pytest.param('aibridgeon', marks=pytest.mark.xfail(strict=True, reason=
        'Native real bridge has no Bridge target; model selects its endpoint. '
        'Bridge registration/eligibility and post-registration evaluation missing: work/re/c_bridge_report.md')),
    'aibridgeoff',
])
def test_bridge_target_absence_replay(build):
    rows = native(build, 'CNVStateTP')
    assert rows and all(not r['found'] for r in rows)
    assert bool(model_picks(replay(build), 'CNVStateTP')) == any(r['found'] for r in rows)


@pytest.mark.xfail(strict=True, reason=
    'Native bridge end builder is gone (alive=0, NamedObject not found); model retains it. '
    'Object lifecycle input gap: work/re/c_bridge_report.md')
def test_bridge_target_removed_endpoint_replay():
    rows = native('aibridgeon', 'CNVBridgeNamedState1')
    assert rows and all(not r['found'] for r in rows)
    assert bool(model_picks(replay('aibridgeon'), 'CNVBridgeNamedState1')) == any(r['found'] for r in rows)


@pytest.mark.parametrize('build', BUILDS)
def test_bridge_target_public_evidence_matches_original(build):
    import teamlog
    path = Path(simai.labpaths.WORK) / 're/c_bridge_measured.json'
    if not path.exists():
        pytest.skip('private original evidence unavailable')
    original = json.loads(path.read_text(encoding='utf-8'))[build]
    assert {k: original[k] for k in MEASURED[build]} == MEASURED[build]
    for row in original['picks']:
        for key in ('brain', 'state', 'heuristic'):
            row[key] = 'redacted'
    public = teamlog.target_picks(str(ROOT / f'tests/fixtures/{build}_target_picks.txt'))
    assert json.loads(json.dumps(public)) == original['picks']
