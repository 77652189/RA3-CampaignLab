"""C-line AI bench missions: each pair differs only where it says (the replays are readings now)."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)

pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')


def test_engineer_pair_isolates_tactic_with_named_capture_candidate():
    """The experiment fixes candidates, geometry, micro and the wake clock."""
    from benches.ai.tactics.scenes import aiengineer_bench
    mission = aiengineer_bench()["shared"].mission
    engineer, control = mission(True), mission(False)
    assert engineer.assets[0][1].replace('Tactic="Engineer"', 'Tactic="SimpleAttack"') == control.assets[0][1]
    assert engineer.objects == control.objects
    assert engineer.scripts == control.scripts
    assert engineer.waypoints == control.waypoints
    candidates = [o for o in engineer.objects if o.template == 'AlliedEngineer']
    assert len(candidates) == 1
    assert candidates[0].name == engineer.cnv_named['engineer']


def test_never_release_pair_changes_only_release_type():
    """Fixed candidates, states, target and clock; only release policy changes."""
    from benches.ai.tactics.scenes import airelease_bench
    mission = airelease_bench()["shared"].mission
    never, priority = mission(True), mission(False)
    assert never.assets[0][1].replace('NEVER_RELEASE', 'RELEASE_TO_PRIORITY') == priority.assets[0][1]
    assert never.objects == priority.objects
    assert never.scripts == priority.scripts


def test_alpha_close_pair_has_only_one_changed_field():
    """Independent pair: the guard schedule, health hold and units are identical."""
    from benches.ai.tactics.scenes import aialphaclose_bench
    mission = aialphaclose_bench()["shared"].mission
    low, high = mission(False), mission(True)
    assert low.assets[0][1] == high.assets[0][1].replace(
        'AlphaStrikeTargetHealthPct="0.9"', 'AlphaStrikeTargetHealthPct="0.01"')
    assert low.objects == high.objects
    assert low.scripts == high.scripts


@pytest.mark.parametrize('high', [False, True])
def test_alpha_observer_preserves_the_measured_scenario(high):
    """Observe on the existing yard without changing any tactical or combat input."""
    from dataclasses import replace
    import labpaths
    from benches.ai.tactics.scenes import aialphaclose_bench
    mission = aialphaclose_bench()["shared"].mission
    stock, observed = mission(high), mission(high, observe=True)
    assert observed.ext and not stock.ext
    assert len(observed.objects) == len(stock.objects)
    assert observed.assets == stock.assets
    assert observed.scripts == stock.scripts
    assert observed.waypoints == stock.waypoints
    assert observed.facts == stock.facts
    yard = stock.role('ai yard')
    assert [replace(o, template=yard.template) if o.name == yard.name else o
            for o in observed.objects] == stock.objects
    host, = observed.units
    original = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures' / (yard.template + '.xml')).read_text(encoding='utf-8')
    behavior = '\n  <DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="4000"/>'
    assert host.xml.count(behavior) == 1
    assert host.xml.replace(behavior, '').replace(f'id="{host.id}"', f'id="{yard.template}"') == original
    assert observed.role('ai yard').template == observed.find(yard.name).template == host.id


def test_micro_update_time_pair_changes_only_micro_period():
    """Keep the measured pair independent of tactical clocks and scripted powers."""
    from benches.ai.tactics.scenes import aimicro_bench
    update_time = aimicro_bench()["shared"].update_time
    fast, slow = update_time('CampMicUpFast', 0.5), update_time('CampMicUpSlow', 4)
    assert len(fast.assets) == len(slow.assets)
    changed = 0
    for (path, text, key), (other_path, other_text, other_key) in zip(fast.assets, slow.assets):
        assert (path, key) == (other_path, other_key)
        if text != other_text:
            changed += 1
            assert text.count('UpdateTime="0.5s"') == 1
            assert other_text.count('UpdateTime="4s"') == 1
            assert text == other_text.replace('UpdateTime="4s"', 'UpdateTime="0.5s"')
    assert changed == 1
    assert fast.objects == slow.objects
    assert fast.scripts == slow.scripts
    assert fast.waypoints == slow.waypoints
    observed_fast = update_time('CampMicObsFast', 0.5, observe=True)
    observed_slow = update_time('CampMicObsSlow', 4, observe=True)
    assert not fast.ext and not slow.ext
    assert observed_fast.ext and observed_slow.ext
    assert observed_fast.units == observed_slow.units
    assert observed_fast.objects == observed_slow.objects
    assert observed_fast.scripts == fast.scripts == observed_slow.scripts
    assert observed_fast.assets == fast.assets
    assert observed_slow.assets == slow.assets
    hosts = [u for u in observed_fast.units if 'ModuleTag_CNVTeams' in u.xml]
    assert len(hosts) == 1
    assert 'MinFrames="15"' in hosts[0].xml


def test_release_eight_carrier_only_adds_passive_logging_to_existing_yard():
    import labpaths
    from missions.aiskirm_bench import mission
    m = mission(observe=True)
    # D round 105: the yard keeps its retail id (a renamed copy changed the AI: aiskxn vs aiskxo on check l)
    assert m.units == []
    (fname, xml, link), = m.assets
    assert link == 'GameObject:AlliedConstructionYard' and m.replaces == [link]
    original = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedConstructionYard.xml').read_text(encoding='utf-8')
    behavior = '\n  <DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="4000"/>'
    assert xml.count(behavior) == 1 and xml.replace(behavior, '') == original
    assert m.ext
    assert len(m.objects) == 4
    assert {o.template for o in m.objects if 'Yard' in o.template} == {'AlliedConstructionYard'}
    stock = mission()
    assert stock.units == [] and not stock.ext
