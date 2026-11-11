"""Partial MetaImpact collision/trajectory replay; no whole-nugget coverage."""
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


@pytest.mark.parametrize('check', ['land', 'late'])
def test_meta_impact_collision_event_replays_engine_knock_probe_neighbour_five_frames(check):
    """Recorded collision -> real damage dispatch -> five Physics frame updates.

    Frozen neighbour positions from CampKPLand_mcp_1110_223946 (174..178)
    and CampKPLate_mcp_1110_224110 (176..180), ra3ext.log. Both runs:
    damage target 99%, neighbour 100%; neighbour lands at (2380,3740).
    The arrival frame/centre is supplied from the bench: V4 curved projectile
    arrival and the direct victim's noise-dependent direction remain gaps.
    """
    import build
    import sim
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_probe', check)
    e = sim.Sim(m, t)
    by, victim, near = (e.bodies[name('rocket', part)] for part in ('gun', 'man', 'near'))
    weapon, = by.weapons
    assert weapon['meta_impacts']
    assert e.impact_ground_z(near.x, near.y) == 212.5
    expected = [(2364.0, 3748.0, 213.73), (2367.9, 3746.0, 214.34),
                (2371.9, 3744.0, 214.34), (2375.9, 3742.0, 213.73), (2380, 3740, 212.50)]
    e.firing, e.volleys = [], []
    e.eng.frame = 173 if check == 'land' else 175
    # Snapshot the same 1.5 UNRESISTABLE hit as the real warhead.
    e.queue_projectile_hit(e.frame_now(), victim, weapon['dmg'], by, weapon, (2300, 3750, 219))
    e.deal(1/15)
    assert victim.hp == pytest.approx(148.5)
    assert near.hp == near.max_hp == 150
    assert (near.x, near.y, near.z) == (2360, 3750, 212.5)
    for k, xyz in enumerate(expected, 1):
        e.eng.frame += 1
        # A queued walk must not override the Physics path while airborne.
        near.path = [(2500, 3750)]
        e.move(1/15)
        e.deal(1/15)
        got = (near.x, near.y, e.impact_ground_z(near.x, near.y) if near.z is None else near.z)
        assert got == pytest.approx(xyz, abs=.051), (check, k, got)
        assert (id(near) in e.impact_flights) == (k < 5)
    assert near.hp == 150
    assert 'meta impact' in e.used


def test_meta_impact_default_curve_uses_ceil_and_caps_long_observed_launches():
    import simunits

    for velocity, frames, landing in [((4.5010, 0, .0004), 5, (2380, 3740, 212.5)),
                                     ((0, -2.1463, 45.6088), 127, (2300, 3060, 212.5)),
                                     ((0, -5.7344, 6.0928), 33, (2300, 3500, 212.5))]:
        start = (2360, 3750, 212.5) if frames == 5 else (2300, 3750, 212.5)
        points = simunits.meta_impact_trajectory(start, velocity)
        assert len(points)-1 == frames
        assert points[-1] == landing


def test_meta_impact_straight_projectile_dispatches_on_arrival_not_launch(monkeypatch):
    """Synthetic wiring regression; the actual V4 curved arrival is still a gap.

    Keep engine_knock_probe land's warhead/targets and switch only to the
    already modeled retail straight shell. Scripts launch the shot; its queue
    dispatches the shock even if the shooter dies while the shell is in flight.
    """
    import re
    import build
    import sim
    from checks.engine_knock_probe import name
    from checks.engine_shot import SHELL

    m, t, _ = build.resolve('engine_knock_probe', 'land')
    gun = next(u for u in m.units if u.id == 'CNV_KnockRocket')
    def straight(match):
        return re.sub(r'ProjectileTemplate="[^"]+"', f'ProjectileTemplate="{SHELL}"', match[0])
    gun.xml, count = re.subn(r'<ProjectileNugget\b[^>]*WarheadTemplate="CNV_KnockRocketWarhead"[^>]*>',
                            straight, gun.xml)
    assert count == 1
    e = sim.Sim(m, t)
    e.shot_clock = True
    near = e.bodies[name('rocket', 'near')]
    queued, arrived = [], []
    queue, detonate = e.queue_projectile_hit, e.projectile_detonate

    def record_queue(when, target, damage, attacker, weapon, centre=None):
        queued.append((e.frame_now(), when))
        assert near.x == 2360 and near.z is None
        queue(when, target, damage, attacker, weapon, centre)
        attacker.hp, attacker.alive = 0, False

    def record_arrival(weapon, target, centre=None):
        arrived.append(e.frame_now())
        detonate(weapon, target, centre)

    monkeypatch.setattr(e, 'queue_projectile_hit', record_queue)
    monkeypatch.setattr(e, 'projectile_detonate', record_arrival)
    e.run(26)
    assert len(queued) == len(arrived) == 1
    launch, arrival = queued[0]
    assert arrival-launch == 9
    assert arrived == [arrival]
    assert (near.x, near.y, near.z) == (2380, 3740, None)
    assert near.hp == 150


def test_meta_impact_dispatch_retains_nondefault_physics_and_outside_radius_gaps():
    import build
    import sim
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_probe', 'land')
    e = sim.Sim(m, t)
    by, near = (e.bodies[name('rocket', part)] for part in ('gun', 'near'))
    weapon, = by.weapons
    e.meta_impact_detonate(weapon, (2300, 3750, 219))
    assert id(near) in e.impact_flights
    # The instant control lane, 1500 away, must not be selected.
    assert id(e.bodies[name('strong', 'near')]) not in e.impact_flights

    m, t, _ = build.resolve('engine_knock_probe', 'land')
    probe = next(u for u in m.units if u.id == near.template)
    probe.xml = probe.xml.replace('id="ModuleTag_Physics"', 'id="ModuleTag_Physics" GravityMultiplier="2"')
    e = sim.Sim(m, t)
    e.meta_impact_detonate(weapon, (2300, 3750, 219))
    assert not e.impact_flights
    assert (sim.GAP_WEAPON, 'MetaImpactNugget') in e.unmodeled
