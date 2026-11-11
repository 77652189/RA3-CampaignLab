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
    assert launch['delayed_meta_impacts'][0]['delay_seconds'] == 1
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


def test_meta_impact_omitted_z_replays_engine_knock_z_tall_neighbour():
    """engine_knock_z a: omitted Z=1, height93 makes vertical scaling observable.

    Collision event supplied separately from V4 arrival/noisy direct-hit vector.
    Expected health99/100, fourteen neighbour flight frames, landing2420/3740.
    Observed CampKZA_mcp_1111_004210: shock173, positions174..187,
    apex222.85. The fourteen positions below match that run's ra3ext.log.
    Delays/filters/nondefault Physics still retain the whole-nugget gap.
    """
    import build
    import sim
    import simunits
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_z', 'a')
    gun = next(u for u in m.units if u.id == 'CNV_KnockRocket')
    assert 'ShockWaveZMult' not in gun.xml
    e = sim.Sim(m, t)
    by, victim, near = (e.bodies[name('rocket', part)] for part in ('gun', 'man', 'near'))
    weapon, = by.weapons
    effect, = weapon['meta_impacts']
    assert effect['zmult'] == 1
    assert simunits.meta_impact_body(near.template, e.own) == 93
    v = simunits.meta_impact_velocity(effect, (2360, 3750, 212.5),
                                     (2300, 3750, 219), 93, detonation=True)
    assert v == pytest.approx((3.7451, 0, 2.4967), abs=.0001)
    expected = [(2364.2, 3749.3, 215.24), (2368.5, 3748.6, 217.57),
                (2372.7, 3747.9, 219.47), (2377.0, 3747.2, 220.95),
                (2381.2, 3746.5, 222.00), (2385.5, 3745.7, 222.63),
                (2389.8, 3745.0, 222.85), (2394.1, 3744.3, 222.63),
                (2398.3, 3743.6, 222.00), (2402.6, 3742.9, 220.95),
                (2407.0, 3742.2, 219.47), (2411.3, 3741.5, 217.57),
                (2415.6, 3740.7, 215.24), (2420, 3740, 212.50)]
    e.firing, e.volleys = [], []
    e.eng.frame = 173
    e.queue_projectile_hit(e.frame_now(), victim, weapon['dmg'], by, weapon, (2300, 3750, 219))
    e.deal(1/15)
    assert victim.hp == pytest.approx(148.5)
    assert near.hp == 150
    for k, xyz in enumerate(expected, 1):
        e.eng.frame += 1
        e.move(1/15)
        e.deal(1/15)
        got = (near.x, near.y, e.impact_ground_z(near.x, near.y) if near.z is None else near.z)
        assert got == pytest.approx(xyz, abs=.051), (k, got)
        assert (id(near) in e.impact_flights) == (k < 14)
    assert near.hp == 150
    # Rebuilding the retail cache must also populate an omitted-Z warhead.
    retail = simunits.weapon_table()['AlliedBomberAircraftBombWarhead']
    assert retail['meta_impacts'][0]['zmult'] == 1
    assert 'MetaImpactNugget' in retail['unmodeled_effects']


@pytest.mark.parametrize('lane,seconds', [('rocket', 1.9), ('strong', 1.2)])
def test_meta_impact_delay_probe_keeps_phase_gap_and_publishes_projectiles(lane, seconds):
    """engine_knock_delay a diagnostic: corrected bench1174/100/1173/100.

    Shock frames204/192; full-health counts174/173 are collision inputs for
    the isolated queue interface (their script phase remains INFERRED). Delayed
    Physics also exposes sample1 in the shock frame, holds it next frame,
    then advances: do not register an immediate-shock replay as delayed cover.
    Both projectile assets must exist; the initial short copy omitted its file.
    """
    import build
    import sim
    import simunits
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_delay', 'a')
    e = sim.Sim(m, t)
    gun_id = 'CNV_KnockRocket' if lane == 'rocket' else 'CNV_DelayShort'
    gun = next(u for u in m.units if u.id == gun_id)
    assert f'ShockwaveDelaySeconds="{seconds}s"' in gun.xml
    assert gun.names['rocket']+'.xml' in gun.files
    assert f'id="{gun.names["rocket"]}"' in gun.files[gun.names['rocket']+'.xml']
    if lane == 'strong':
        assert all('CNV_KnockRocket' not in v for v in gun.files.values())
    weapon, = e.bodies[name(lane, 'gun')].weapons
    assert weapon['meta_impacts'] == []
    assert 'MetaImpactNugget' in weapon['unmodeled_effects']
    # Existing spatial solver agrees with both observed neighbour paths; this
    # does not assert the missing Physics observation/update phase.
    effect = dict(amount=89, radius=250, zmult=1, taper=0)
    y = 3750 if lane == 'rocket' else 850
    velocity = simunits.meta_impact_velocity(effect, (2360,y,212.5),
                                             (2300,y,219), 93, detonation=True)
    points = simunits.meta_impact_trajectory((2360,y,212.5), velocity)
    assert len(points) == 15
    assert points[1] == pytest.approx((2364.2,y-.7,215.24), abs=.051)
    assert points[-1] == (2420,y-10,212.5)


@pytest.mark.parametrize('lane,collision,shock,delay_frames', [
    ('rocket', 174, 204, 29), ('strong', 173, 192, 18),
])
def test_meta_impact_delay_queue_replays_engine_knock_delay_due_frames(lane, collision, shock, delay_frames):
    """Replay dispatch only, with collision frames supplied from the bench.

    CampKDA_mcp_1111_005836 engine_knock_delay a: counters1174/100/1173/100,
    raw neighbour shock frames204/192. D39 establishes float32 ceil and
    decrement-before-strict-negative expiry; count=collision is INFERRED.
    The returned event is not fed to Physics: shock+1 sampling/landing is a gap.
    """
    import build
    import sim
    import simunits
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_delay', 'a')
    e = sim.Sim(m, t)
    by, victim, near = (e.bodies[name(lane, part)] for part in ('gun', 'man', 'near'))
    weapon, = by.weapons
    effect, = weapon['delayed_meta_impacts']
    assert simunits.meta_impact_delay_frames(effect['delay_seconds']) == delay_frames
    assert weapon['meta_impacts'] == []
    queue = simunits.MetaImpactDelayQueue()
    centre = (2300, 3750 if lane == 'rocket' else 850, 219)
    queue.enqueue(collision, effect, centre)
    # Ordinary collision damage still lands immediately; no delayed Physics.
    e.firing, e.volleys = [], []
    e.eng.frame = collision
    e.queue_projectile_hit(collision, victim, weapon['dmg'], by, weapon, centre)
    e.deal(1/15)
    assert victim.hp == pytest.approx(148.5)
    assert near.hp == 150
    for frame in range(collision, shock):
        assert queue.due(frame) == []
    assert queue.due(shock) == [(shock, effect, centre)]
    assert queue.due(shock) == queue.due(shock+1) == []
    assert not e.impact_flights
    assert 'MetaImpactNugget' in weapon['unmodeled_effects']
    # Retail cache must retain both original delays too, never as instant shocks.
    retail = simunits.weapon_table()
    key = 'JapanMechaKingKatana' if lane == 'rocket' else 'JapanMechaKingOmegaShockwave'
    assert retail[key]['delayed_meta_impacts'][0]['delay_seconds'] == effect['delay_seconds']
    assert not retail[key].get('meta_impacts')


def test_meta_impact_delay_queue_keeps_other_events_and_rejects_unmodeled_variants():
    import simunits

    queue = simunits.MetaImpactDelayQueue()
    effect = dict(amount=89, radius=250, zmult=1, taper=0, delay_seconds=1.9)
    queue.enqueue(174, effect, 'long')
    effect['delay_seconds'] = 1.2
    queue.enqueue(173, effect, 'short')
    queue.enqueue(173, effect, 'same-frame')
    assert queue.due(191) == []
    assert [(f, e['delay_seconds'], p) for f, e, p in queue.due(193)] == [
        (192, 1.2, 'short'), (192, 1.2, 'same-frame')]
    assert [(f, e['delay_seconds'], p) for f, e, p in queue.due(204)] == [(204, 1.9, 'long')]
    assert queue.due(300) == []
    for seconds in (0, -1, float('inf'), float('nan')):
        with pytest.raises(ValueError):
            simunits.meta_impact_delay_frames(seconds)
    for extra in ('ShockWaveSpeed="10"', 'ShockWaveArc="90"', 'ShockwaveDelaySeconds="-1s"'):
        delay = '' if extra.startswith('ShockwaveDelaySeconds') else 'ShockwaveDelaySeconds="1.2s"'
        w = simunits._weapons([f'''<WeaponTemplate id="unsupported"><Nuggets>
            <MetaImpactNugget ShockWaveAmount="89" ShockWaveRadius="250" {delay} {extra}/>
            </Nuggets></WeaponTemplate>'''])['unsupported']
        assert not w.get('meta_impacts') and not w.get('delayed_meta_impacts')
        assert 'MetaImpactNugget' in w['unmodeled_effects']


@pytest.mark.parametrize('check', ['stand', 'standlate'])
def test_physics_a_knocked_man_keeps_still_38_frames_after_landing_then_walks_his_order(check):
    """engine_knock_probe stand / standlate (CampKPStand_mcp_1111_082909, ra3ext.log): the man flung by the V4's shock
    lifts at 174, is on the ground at (2300, 3060) from 300 and takes his first step east at 338 = landing + 38
    (Physics defaults ShockStunnedTime 1 s + ShockStandingTime 1.5 s), whether the move order came in the air
    (stand: frame 248, the unshot control steps at 249) or on the ground (standlate: frame 310). The flight is the
    bench's own launch vector (the direct hit's direction is collision noise, not simulated)."""
    import build
    import sim
    import simunits
    from checks.engine_knock_probe import MOVE, ORDER, name

    m, t, _ = build.resolve('engine_knock_probe', check)
    e = sim.Sim(m, t)
    man = e.bodies[name('rocket', 'man')]
    e.firing, e.volleys = [], []
    points = simunits.meta_impact_trajectory((2300, 3750, 212.5), (0, -2.1463, 45.6088))
    assert len(points) == 128 and points[-1] == (2300, 3060, 212.5)
    e.impact_flights = {id(man): (man, 173, points)}
    order = round((ORDER + MOVE[check]) * 15)
    assert order == {'stand': 248, 'standlate': 310}[check]
    e.eng.frame = 173
    first = None
    while e.eng.frame < 345:
        e.eng.frame += 1
        if e.eng.frame == order:
            man.path = [(2700, 3060)]
        before = (man.x, man.y)
        e.move(1/15)
        e.deal(1/15)
        if e.eng.frame == 300:
            assert id(man) not in e.impact_flights and (man.x, man.y) == (2300, 3060)
        if first is None and e.eng.frame > 300 and (man.x, man.y) != before:
            first = e.eng.frame
    assert simunits.meta_impact_landing_hold() == 38
    assert first == 338
    assert man.x > 2300 and man.y == pytest.approx(3060)
