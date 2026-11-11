"""Keep unresolved lift timing visible; these guards do not claim bench replay."""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location('simbench_lift', Path(__file__).resolve().parents[1] /
                                             'experimental/cnv/simbench.py')
_harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_harness)


@pytest.mark.parametrize('check', ['a', 'landing'])
def test_lift_unresolved_timing_is_reported_at_fire(check):
    """Two historical runs disagree with lease expiry; never accept HP alone.

    a: 1099/11001099/11001099/1099;
    landing: 1099/10001099/10001099/1099.
    Both short and long Lifetime still have the early bit. No expiry rule is
    implemented until module renewal/release is explained.
    """
    import build
    import sim
    import simunits

    m, t, _ = build.resolve('engine_lift', check)
    e = sim.Sim(m, t)
    e.shot_clock = True
    e.run(8)
    assert (sim.GAP_WEAPON, 'ActivateLiftObjectNugget') in e.unmodeled
    weapons = simunits._weapons([u.xml for u in m.units])
    lifted = [w for w in weapons.values()
              if 'ActivateLiftObjectNugget' in w.get('unmodeled_effects', [])]
    assert len(lifted) == 3  # even the missing-module lane must not be silently accepted
    for lane in ('base', 'high', 'order', 'removed'):
        victim = e.body('Lift ' + lane + ' victim')
        assert victim.alive and round(victim.hp / victim.max_hp * 100) == 99
        assert 'LIFTED_INTO_AIR' not in victim.status


@pytest.mark.parametrize('nugget', [
    '<ActivateLiftObjectNugget/>',
    '<ActivateLiftObjectNugget Lifetime="0.2s"><SpecialObjectFilter Rule="ANY" '
    'Include="VEHICLE"/></ActivateLiftObjectNugget>',
])
def test_lift_unresolved_timing_survives_inheritance_and_warhead(nugget):
    import simunits

    xml = ('<WeaponTemplate id="LiftBase"><Nuggets>' + nugget + '</Nuggets></WeaponTemplate>'
           '<WeaponTemplate id="LiftChild" inheritFrom="LiftBase"/>'
           '<WeaponTemplate id="LiftShot"><Nuggets><ProjectileNugget '
           'WarheadTemplate="LiftChild"/></Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    for name in ('LiftBase', 'LiftChild', 'LiftShot'):
        assert simunits._resolve(weapons[name], weapons)['unmodeled_effects'] == ['ActivateLiftObjectNugget']
