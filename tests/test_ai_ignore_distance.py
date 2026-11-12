"""Base-distance gate probe: identical geometry and a single XML gate contrast."""
import xml.etree.ElementTree as ET
import importlib.util
from pathlib import Path
import pytest


ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)


def test_ignore_distance_fixture_changes_only_distance():
    import build
    from contract import contract
    from model import merged

    views = []
    for name, distance in [('aiignzero', '0'), ('aiignnear', '2000')]:
        m, t, _ = build.resolve(name, 'r')
        assert contract(merged(m, t)) == []
        xml = ET.fromstring(m.assets[0][1])
        micro = next(e for e in xml.iter() if e.tag.endswith('}AIMicroManagerData'))
        assert micro.attrib.pop('MinDistanceFromBaseToIgnoreTargets') == distance
        assert micro.get('UseSpecialPowers') == 'false'
        assert micro.get('DodgeThreats') == 'false'
        assert micro.get('PullbackInjured') == 'false'
        assert len(m.cnv_named) == 2
        assert m.facts['target earliest at'] == 26
        views.append((ET.tostring(xml), m.objects, m.scripts, m.waypoints, m.cnv_named))
    assert views[0] == views[1]


def test_ignore_distance_observer_preserves_inputs_and_game_clock_gate():
    import build
    from contract import contract
    from model import merged

    observed = []
    for original, diagnostic in [('aiignzero', 'aiignzt'), ('aiignnear', 'aiignnt')]:
        base, old, _ = build.resolve(original, 'r')
        m, t, name = build.resolve(diagnostic, 'r')
        assert len(name) <= 15 and '_' not in name
        assert contract(merged(m, t)) == []
        assert m.assets == base.assets
        assert m.scripts == base.scripts and m.waypoints == base.waypoints
        assert m.cnv_named == base.cnv_named and m.facts == base.facts
        assert m.objects[:-1] == base.objects
        assert m.objects[-1].template == 'CNVTeamsHost' and m.ext
        assert 'MinFrames="15"' in m.units[-1].xml
        assert t.scripts == old.scripts and t.counters == old.counters
        assert ('帧数', 1, 'ever>=', 600, 240) in t.expect
        assert old.bench[0][1]['seconds'] == 52
        observed.append(m)
    assert observed[0].objects == observed[1].objects
    assert observed[0].assets[0][1] == observed[1].assets[0][1].replace(
        'MinDistanceFromBaseToIgnoreTargets="2000"', 'MinDistanceFromBaseToIgnoreTargets="0"')


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
@pytest.mark.parametrize('name', ['aiignzero', 'aiignnear'])
def test_ignore_distance_replays_named_damage_observation(name):
    w = simai.run(name, 'r', until=50)
    rows = [values for _, values in w.sim.series]
    # The targets cannot be attacked before both warriors exist. Keep the
    # rejected first probe's contamination out of the replay acceptance.
    before = [v for v in rows if 23 * simai.FPS <= v[0] < 26 * simai.FPS]
    assert before and all(v[1] == 2 and v[2:] == [0, 0] for v in before), before
    after = [v for v in rows if 28 * simai.FPS <= v[0] <= 49 * simai.FPS]
    assert after and any(v[2] == 1 for v in after), after
    first = {v[3] for v in after if v[2]}
    assert len(first) == 1 and next(iter(first)) >= 26 * simai.FPS, first


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
@pytest.mark.parametrize('name, expected', [
    ('aiignzero', [(391, 8, False), (406, 8, False), (421, 8, False)]),
    ('aiignnear', [(391, 8, False), (406, 0, True), (421, 0, True)]),
])
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'CNVTeams diagnostics: distance 0 stays state 8/no target; 2000 selects '
    'nonempty targets in state 0 at frames 406/421. Model gives state 2/no target '
    'in both. Target selection belongs to tactics.py; carrier equivalence '
    'and base-distance input remain gaps. See work/re/handoff-c.md and '
    'work/re/c_ignore_state_report.md.'))
def test_ignore_distance_micro_target_state_replays_observed_pair(name, expected):
    """Damage can coincide while the measured team targets differ.

    Diagnostic carrier equivalence remains a gap. These exact state readings
    are observations, not a fitted distance rule; work/re/c_ignore_state_report.md.
    """
    w = simai.run(name, 'r', until=29, record=True)
    rows = [row for brain in w.brains.values() for row in brain.rec['frames']
            if row['state_key'] == 'CNVStateMicro' and len(row['members']) == 2]
    actual = [(frame, row['state'], row['foe_id'] is not None) for frame, _, _ in expected
              for row in rows if row['frame'] == frame]
    assert actual == expected, actual
