"""Native UnderAttack gates, distinct from episode-derived expiry.

Evidence and unresolved world inputs: work/re/c_underattack_reopen_report.md.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)


def measured(key):
    import teamlog
    path = ROOT / f'tests/fixtures/underattack_{key}_c.txt'
    return path, teamlog.under_attack(str(path))


def test_underattack_native_full_health_gate_and_source_lifetimes():
    import teamlog
    path, data = measured('d164')
    assert 'hp=1000.0/1000.0' in path.read_text(encoding='utf-8').splitlines()[0]
    gates = data['gates']
    assert {(g['frame'], g['obj'], g['last'], g['result']) for g in gates} == {
        (16, 3163, -1, False), (16, 3181, 5, True),
        (16, 3182, -1, False), (16, 3184, -1, False)}
    selected = next(r for r in teamlog.target_picks(str(path))
                    if r['state_id'] == teamlog.state_hash('CNVClosest0'))
    assert selected['frame'] == 16 and selected['target'] == 3181
    assert [(c['id'], c['ok']) for c in selected['candidates']] == [
        (3163, False), (3181, True), (3182, False), (3184, False)]
    plant = next(e for e in data['episodes'] if e['obj'] == 3181)
    infantry = next(e for e in data['episodes'] if e['obj'] == 3187)
    assert (plant['last'], plant['clear'], plant['src_alive'], plant['inferred']) == (33, 109, True, False)
    assert (infantry['last'], infantry['clear'], infantry['src_alive'], infantry['inferred']) == (146, 222, False, False)
    # A clr observation does not supply another direct gate answer.
    assert all(g['frame'] == 16 for g in gates)


@pytest.mark.parametrize('key', ['d164', 'aiuagate'])
def test_underattack_public_observations_match_frozen_original(key):
    archive = Path(simai.labpaths.WORK) / 're/c_underattack_reopen_measured.json'
    if not archive.exists():
        pytest.skip('private original evidence unavailable')
    original = json.loads(archive.read_text(encoding='utf-8'))[key]
    _, data = measured(key)
    assert data == original['under_attack']
    assert original['last_frame'] > 120


def test_underattack_delayed_gates_have_live_ordinary_controls():
    import teamlog
    path, data = measured('aiuagate')
    rows = {r['state_id']: r for r in teamlog.target_picks(str(path))}
    actual = [rows[teamlog.state_hash(f'CNVClosest{i}')] for i in range(4)]
    assert [(r['frame'], r['found'], r['target']) for r in actual] == [
        (49, False, None), (139, False, None), (49, True, 3182), (139, True, 3184)]
    assert all({c['id'] for c in r['candidates']} == {3163, 3182, 3184} for r in actual)
    assert {(g['frame'], g['obj'], g['last'], g['result']) for g in data['gates']} == {
        (49, 3163, -1, False), (49, 3182, -1, False), (49, 3184, -1, False)}
    plant = next(e for e in data['episodes'] if e['obj'] == 3181)
    assert (plant['last'], plant['clear'], plant['src_alive'], plant['inferred']) == (32, 108, False, False)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason='Delayed slots omit injured plant 3181 '
    'from candidates; no direct post-hit gate for that object. Two games exhausted; '
    'see work/re/handoff-c.md and work/re/c_underattack_reopen_report.md.')
def test_underattack_delayed_probe_has_direct_injured_candidate_gate():
    _, data = measured('aiuagate')
    assert any(g['obj'] == 3181 and 18 <= g['frame'] < 108 and g['result'] for g in data['gates'])


@pytest.mark.xfail(strict=True, raises=AssertionError, reason='FriendlyStructure find bypasses UnderAttack even with native gate facts; '
    'world hit clock is also absent. See work/re/handoff-c.md and work/re/c_underattack_reopen_report.md.')
def test_underattack_actual_consumer_uses_native_gate_facts():
    if not simai.available():
        pytest.skip('no private AI model')
    tg = simai.model()['targets']
    _, data = measured('d164')
    # Isolated consumer replay: input is the game's direct boolean, not HP loss
    # or a value reconstructed from ua episode expiry.
    things = [tg.Thing(g['obj'], 'Soviet_1', kindof=frozenset({'STRUCTURE'}),
                       under_attack=g['result']) for g in data['gates']]
    view = tg.View('Soviet_1', things=things)
    chosen = tg.find(tg.TargetHeuristic('CNVUnderAttack', 'FriendlyStructure', under_attack=True),
                     view, (0, 0))
    assert chosen is not None and chosen.id == 3181


@pytest.mark.xfail(strict=True, raises=AssertionError, reason='Named aiunderatk replay lacks native full-health hit clock and '
    'FriendlyStructure gate consumption. See work/re/handoff-c.md and work/re/c_underattack_reopen_report.md.')
def test_underattack_named_selection_matches_native():
    import teamlog
    if not simai.available():
        pytest.skip('no private AI model')
    path, _ = measured('d164')
    selected = next(r for r in teamlog.target_picks(str(path))
                    if r['state_id'] == teamlog.state_hash('CNVClosest0'))
    assert selected['target'] == 3181 and selected['point'] == (4000.0, 3000.0)
    world = simai.run('aiunderatk', 'a', until=6)
    brain = world.brains['Soviet_1']
    picks = [text for _, kind, text in brain.ai.log
             if kind == 'target' and text.startswith('CNVClosest0: ')]
    plant = world.sim.m.role('closest plant').name
    expected = brain.ids[plant]
    assert picks and all(text.endswith(f'-> [{expected}]') for text in picks)
