"""SpecialPowerNugget gate replay; import the same simulator harness as line C."""
import importlib.util
from pathlib import Path
import pytest

_spec = importlib.util.spec_from_file_location('simbench_spng', Path(__file__).resolve().parents[1] /
                                             'experimental/cnv/simbench.py')
_harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_harness)


@pytest.mark.parametrize('mission,expected', [
    ('engine_spng', (1011099075, 1011099080, 1011099080, 1011099075)),
    ('engine_spn', (1001099080, 1001099075, 1001099080, 1001099080)),
])
def test_special_power_nugget_upgrade_gates_use_caster_not_victim(mission, expected):
    """engine_spng a: required/forbidden x caster/victim, plus grant proof."""
    import build
    import sim
    m, t, _ = build.resolve(mission, 'a')
    e = sim.Sim(m, t)
    e.shot_clock = True
    result = e.run(16)
    assert tuple(result.series[-1][1]) == expected
    assert all(tuple(row) == expected for sec, row in result.series if sec >= 14)
    assert (sim.GAP_WEAPON, 'SpecialPowerNugget') not in e.unmodeled


@pytest.mark.parametrize('inner', [
    '<RequiredUpgrade>A</RequiredUpgrade><RequiredUpgrade>B</RequiredUpgrade>',
    '<RequiredUpgrade>A</RequiredUpgrade><ForbiddenUpgrade>B</ForbiddenUpgrade>',
    '<RequiredUpgrade id="unexpected">A</RequiredUpgrade>',
])
def test_special_power_nugget_upgrade_gates_reject_unmeasured_forms(inner):
    import simunits
    xml = ('<WeaponTemplate id="GateTest"><Nuggets><SpecialPowerNugget '
           'SpecialPowerTemplate="Power">' + inner + '</SpecialPowerNugget></Nuggets></WeaponTemplate>')
    w = simunits._weapons([xml])['GateTest']
    assert not w.get('special_powers')
    assert 'SpecialPowerNugget' in w['unmodeled_effects']


def test_special_power_nugget_upgrade_gates_leave_player_upgrades_unmodeled():
    import build
    import sim
    import simunits
    from checks.engine_spng import UPGRADE
    m, t, _ = build.resolve('engine_spng', 'a')
    for u in m.units:
        u.xml = u.xml.replace(f'id="{UPGRADE}" Type="OBJECT"', f'id="{UPGRADE}" Type="PLAYER"')
    e = sim.Sim(m, t)
    e.shot_clock = True
    assert simunits.upgrade_type(UPGRADE, e.own) == 'PLAYER'
    result = e.run(16)
    assert tuple(result.series[-1][1]) == (1011099080,)*4
    assert (sim.GAP_WEAPON, 'SpecialPowerNugget') in e.unmodeled


def test_special_power_nugget_upgrade_gates_survive_retail_cache():
    import simunits
    weapon = simunits._fight_data()['weapons']['AlliedAntiVehicleVehicleTech1TargetPainter']
    assert [(p['required_upgrade'], p['forbidden_upgrade']) for p in weapon['special_powers']] == [
        ('', 'Upgrade_AlliedHighTechnology'), ('Upgrade_AlliedHighTechnology', '')]
