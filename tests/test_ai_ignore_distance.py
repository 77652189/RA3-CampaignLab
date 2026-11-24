"""Base-distance gate probe: identical geometry and a single XML gate contrast."""
import xml.etree.ElementTree as ET
import importlib.util
from pathlib import Path
import pytest


ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)


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
@pytest.mark.parametrize('passive, distance, expected_state, has_foe', [
    (False, 0, 8, False), (False, 2000, 2, False),
    (True, 0, 8, False), (True, 2000, 6, True),
])
def test_ignore_distance_consumer_preserves_lists_and_gates_attacks(
        passive, distance, expected_state, has_foe):
    """Regression for consumer dispatch, not an exact measured distance boundary.

    INFERRED home geometry remains open. Keep hostile lists intact: filtering
    attack eligibility must not erase enemies used by other state decisions.
    """
    from types import SimpleNamespace as NS

    tc = simai.model()['tactics']
    md = tc.MicroData(root='nonexistent')
    md.add_text(f'''<AssetDeclaration><AIMicroManagerData id="base"
        MinDistanceFromBaseToIgnoreTargets="{distance}">
        <IgnoreTargets Rule="ANY"><IncludeThing>AlliedEngineer</IncludeThing></IgnoreTargets>
        </AIMicroManagerData><AIMicroManagerData id="derived" inheritFrom="base"/>
        </AssetDeclaration>''')
    member = tc.Fighter('mine', (500, 0), 100, 100, speed=100,
                        reach=100, vision=1000, rate=lambda _: 10)
    target = tc.Fighter('enemy', (500, 0), 100, 100, speed=100,
                        structure=passive, template='AlliedEngineer')
    team = NS(members=[member], template=NS(micro='derived'))
    run = tc.Run(team, None)
    block = tc.TacticsBlock(None, None, None, lambda _: (0, 0), micro=md,
                           fight=lambda *_: ([member], [target]))
    state = block._team_state(None, run, 400, (500, 0), 'derived')
    assert (state, run.foe is not None) == (expected_state, has_foe)
    assert run.hostiles == (0 if passive else 1)
    assert run.hostile == ([] if passive else [target])


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
def test_ignore_distance_tactical_target_bypasses_passive_filter():
    """A tactical object is selected through its own eligibility path."""
    from types import SimpleNamespace as NS

    tc = simai.model()['tactics']
    md = tc.MicroData(root='nonexistent')
    md.add_text('''<AssetDeclaration><AIMicroManagerData id="ignore">
        <IgnoreTargets Rule="ANY"><IncludeThing>AlliedEngineer</IncludeThing></IgnoreTargets>
        </AIMicroManagerData></AssetDeclaration>''')
    member = tc.Fighter('mine', (500, 0), 100, 100, reach=100,
                        vision=1000, rate=lambda _: 10)
    target = tc.Fighter('enemy', (500, 0), 100, 100, structure=True,
                        template='AlliedEngineer')
    run = tc.Run(NS(members=[member], template=NS(micro='ignore')), None, target='enemy')
    block = tc.TacticsBlock(None, None, None, lambda _: (0, 0), micro=md,
                           fight=lambda *_: ([member], [target]))
    assert block._team_state(None, run, 400, (500, 0), 'ignore') == 6
    assert run.foe is target


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
def test_ignore_distance_assignment_skips_filtered_enemy():
    """A later state-2 assignment cannot reintroduce the ignored candidate."""
    from types import SimpleNamespace as NS

    tc = simai.model()['tactics']
    md = tc.MicroData(root='nonexistent')
    md.add_text('''<AssetDeclaration><AIMicroManagerData id="ignore">
        <IgnoreTargets Rule="ANY" Include="INFANTRY"><ExcludeThing>Allowed</ExcludeThing>
        </IgnoreTargets></AIMicroManagerData></AssetDeclaration>''')
    # the model keys its keep tables by the member itself (by identity, as the simulator's bodies)
    unit = type('Member', (NS,), {'__hash__': object.__hash__, '__eq__': object.__eq__})(pos=(500, 0))
    member = tc.Fighter('mine', (500, 0), 100, rate=lambda _: 10, unit=unit)
    ignored = tc.Fighter('ignored', (500, 0), 1, template='Ignored', kinds=frozenset({'INFANTRY'}))
    allowed = tc.Fighter('allowed', (600, 0), 100, template='Allowed', kinds=frozenset({'INFANTRY'}))
    run = tc.Run(NS(members=[unit], template=NS(micro='ignore'), tactic='test'), None)
    run.mem, run.hostile = [member], [ignored, allowed]
    block = tc.TacticsBlock(None, None, None, lambda _: (0, 0), micro=md)
    attacks = []
    block._attack_one = lambda ai, run, unit, fighter, target, frame: attacks.append(target.id)
    block._assign(None, run, 400)
    assert attacks == ['allowed']
