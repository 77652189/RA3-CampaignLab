"""Unresolved grappling dispatch must remain visible, not count as bench replay."""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location('simbench_grapple', Path(__file__).resolve().parents[1] /
                                             'experimental/cnv/simbench.py')
_harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_harness)


def test_grapple_unresolved_consumer_reports_gap_at_fire():
    import build
    import sim
    import simunits

    m, t, _ = build.resolve('engine_grapple', 'a')
    e = sim.Sim(m, t)
    e.shot_clock = True
    e.run(8)
    assert (sim.GAP_WEAPON, 'GrapplingHookNugget') in e.unmodeled
    for lane in ('base', 'high', 'order', 'removed'):
        victim = e.body('Grapple '+lane+' victim')
        assert victim.alive and round(victim.hp/victim.max_hp*100) == 99
    # Check the real cached retail table too, not only probe-owned XML.
    w = simunits._fight_data()['weapons']['SovietAntiVehicleVehicleTech3Harpoon']
    assert 'GrapplingHookNugget' in w['unmodeled_effects']


@pytest.mark.parametrize('nugget', [
    '<GrapplingHookNugget Damage="1" DamageType="CANNON"/>',
    '<GrapplingHookNugget Damage="0" DamageType="UNRESISTABLE">'
    '<SpecialObjectFilter Rule="ANY" Include="VEHICLE"/></GrapplingHookNugget>',
])
def test_grapple_unresolved_consumer_survives_inheritance_and_warhead(nugget):
    import simunits

    xml = ('<WeaponTemplate id="HookBase"><Nuggets>'+nugget+'</Nuggets></WeaponTemplate>'
           '<WeaponTemplate id="HookChild" inheritFrom="HookBase"/>'
           '<WeaponTemplate id="HookShot"><Nuggets><ProjectileNugget '
           'WarheadTemplate="HookChild"/></Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    for name in ('HookBase', 'HookChild', 'HookShot'):
        assert simunits._resolve(weapons[name], weapons)['unmodeled_effects'] == ['GrapplingHookNugget']
