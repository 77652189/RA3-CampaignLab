"""Partial numerical MetaImpact replay; never registers whole-nugget coverage."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('impact_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.mark.parametrize('check', ['land', 'late'])
def test_meta_impact_neighbour_velocity_and_ground_launch_match_engine_knock_probe(check):
    """Both bench runs: neighbour v.x=4.5010, a=1.9692, landing=(2380,3740).

    Replays numerical shock inputs, not full Sim.run or the flight's five frames.
    Exact direct-hit direction is collision noise and is not a stable target.
    """
    import build
    import simunits

    m, _, _ = build.resolve('engine_knock_probe', check)
    weapons = simunits.weapon_table({u.id: u.xml for u in m.units})
    gun = next(u for u in m.units if u.id == 'CNV_KnockRocket')
    launch = simunits._resolve(weapons[gun.names['weapon']], weapons)
    assert 'MetaImpactNugget' in launch['unmodeled_effects']
    effect, = launch['meta_impacts']
    velocity = simunits.meta_impact_velocity(effect, (2360, 3750, 212.5),
                                             (2300, 3750, 219), 13, detonation=True)
    assert velocity == pytest.approx((4.5010, 0, 0), abs=0.0005)
    plan = simunits.meta_impact_ground_launch((2360, 3750, 212.5), velocity)
    assert plan['steps'] == 7
    assert plan['height'] == pytest.approx(1.9692, abs=0.0001)
    assert plan['landing'] == (2380, 3740, 212.5)
    # No instant-hit push, the negative control in engine_knock_probe retail.
    assert simunits.meta_impact_velocity(effect, (2360, 3750, 212.5),
                                         (2300, 3750, 219), 13, detonation=False) == (0, 0, 0)


@pytest.mark.parametrize('velocity,steps,height,landing', [
    ((0, -2.1463, 45.6088), 320, 3648.7048, (2300, 3060, 212.5)),
    ((0, -5.7344, 6.0928), 42, 63.9749, (2300, 3500, 212.5)),
])
def test_meta_impact_ground_launch_replays_observed_direct_hit_vectors(velocity, steps, height, landing):
    import simunits

    plan = simunits.meta_impact_ground_launch((2300, 3750, 212.5), velocity)
    assert plan['steps'] == steps
    assert plan['height'] == pytest.approx(height, abs=0.002)
    assert plan['landing'] == landing


def test_meta_impact_partial_interface_retains_unsupported_variants_and_retail_gap():
    import build
    import sim
    import simunits

    weapons = simunits._weapons(['''<WeaponTemplate id="head"><Nuggets>
        <MetaImpactNugget ShockWaveAmount="89" ShockWaveRadius="250" ShockWaveZMult="8.5"
         ShockwaveDelaySeconds="1s"/></Nuggets></WeaponTemplate>
        <WeaponTemplate id="launch"><Nuggets>
        <ProjectileNugget ProjectileTemplate="shell" WarheadTemplate="head"/>
        <InformTargetNugget/>
        </Nuggets></WeaponTemplate>'''])
    launch = simunits._resolve(weapons['launch'], weapons)
    assert launch['meta_impacts'] == []
    assert set(launch['unmodeled_effects']) == {'MetaImpactNugget', 'InformTargetNugget'}
    assert any('MetaImpactNugget' in w.get('unmodeled_effects', [])
               for w in simunits._fight_data()['weapons'].values())
    effect = dict(amount=89, radius=250, zmult=8.5, taper=0)
    centered = simunits.meta_impact_velocity(effect, (0, 0, 0), (0, 0, 6.5), 13, detonation=True)
    assert centered == pytest.approx((0, 0, (89 / 15) * (1 - 6.5 / 250) * 8.5))
    assert simunits.meta_impact_velocity(effect, (0, 0, 0), (0, 0, 6.5), 13,
                                         detonation=True, resistance=1) == (0, 0, 0)
    assert simunits.meta_impact_ground_launch((3, 7, 0), (0, 0, 0))['landing'] == (3, 7, 0)
    m, t, _ = build.resolve('engine_knock_probe', 'shot')
    engine = sim.Sim(m, t)
    engine.shot_clock = True
    engine.run(16)
    assert (sim.GAP_WEAPON, 'MetaImpactNugget') in engine.unmodeled
