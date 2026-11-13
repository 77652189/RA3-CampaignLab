"""Partial MetaImpact collision/trajectory replay; no whole-nugget coverage."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('impact_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_meta_impact_arc_probe_has_one_retail_payload_and_one_unfiltered_control():
    """Keep the negative lane interpretable: both shots must actually arrive.

    The first diagnostic accidentally retained restrictions in both lanes
    because retail XML uses newlines before attributes. This protects the
    experiment's independent variable, not evidence of arc implementation.
    """
    import re
    import xml.etree.ElementTree as ET
    import build
    import sim
    from checks.engine_knock_arc import retail_shock
    from checks.engine_knock_probe import ORDER, name

    m, t, _ = build.resolve('engine_knock_arc', 'a')
    e = sim.Sim(m, t)
    original = ET.fromstring(retail_shock()).attrib
    for lane, uid in (('yuri', 'CNV_KnockYuri'), ('rocket', 'CNV_KnockRocket')):
        gun = next(u for u in m.units if u.id == uid)
        nugget, = re.findall(r'<MetaImpactNugget\b[^>]*/>', gun.xml)
        expected = dict(original)
        if lane == 'rocket':
            expected.pop('ShockWaveArc')
            expected.pop('ForbiddenTargetModelCondition')
        assert ET.fromstring(nugget).attrib == expected
        weapon, = e.bodies[name(lane, 'gun')].weapons
        assert weapon['projectile']
        assert gun.names['rocket'] + '.xml' in gun.files
        if lane == 'rocket':
            assert weapon['meta_impacts'] == [dict(amount=50, radius=40, zmult=1, taper=1)]
        else:
            # Fail closed: retaining the gap is not successful filter coverage.
            assert weapon['meta_impacts'] == []
            assert 'MetaImpactNugget' in weapon['unmodeled_effects']
    stop_timers = [a[2] for script in t.scripts for a in script.do
                   if a[0] == 'SET_MILLISECOND_TIMER' and a[1].startswith('Knock Stop')]
    assert stop_timers == [ORDER + 2, ORDER + 2]


def test_meta_impact_arc_probe_replays_plain_neighbour_and_retains_filter_gap():
    """CampKArcA_mcp_1111_192408: health99/100/99/100, both arrivals seen.

    Raw plain neighbour samples175..177 below, restricted pair stationary
    through255. Arrival174/centre are replay inputs (phase INFERRED), not a
    full curved-projectile prediction. A rejected parser producing no motion
    is NOT evidence of implemented retail filtering: retain that explicit gap.
    """
    import build
    import sim
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_arc', 'a')
    e = sim.Sim(m, t)
    e.firing, e.volleys = [], []
    e.eng.frame = 174
    for lane in ('yuri', 'rocket'):
        by, victim, near = (e.bodies[name(lane, part)] for part in ('gun', 'man', 'near'))
        weapon, = by.weapons
        e.queue_projectile_hit(174, victim, weapon['dmg'], by, weapon, (victim.x,3750,219))
    e.deal(1/15)
    for lane in ('yuri', 'rocket'):
        assert e.bodies[name(lane, 'man')].hp == pytest.approx(148.5)
        assert e.bodies[name(lane, 'near')].hp == 150
    near = e.bodies[name('rocket', 'near')]
    for frame, xyz in enumerate([(2320,3746.7,213.40), (2320,3743.4,213.40),
                                 (2320,3740,212.50)], 175):
        e.eng.frame = frame
        e.move(1/15)
        e.deal(1/15)
        z = e.impact_ground_z(near.x, near.y) if near.z is None else near.z
        assert (near.x, near.y, z) == pytest.approx(xyz, abs=.051)
    assert id(near) not in e.impact_flights
    restricted, = e.bodies[name('yuri', 'gun')].weapons
    assert 'MetaImpactNugget' in restricted['unmodeled_effects']
    assert restricted['meta_impacts'] == []
    # These match the recorded negative, but are fail-closed parser behaviour.
    for part, x in (('man',800), ('near',820)):
        b = e.bodies[name('yuri', part)]
        assert id(b) not in e.impact_flights
        assert (b.x,b.y,e.impact_ground_z(b.x,b.y) if b.z is None else b.z) == (x,3750,212.5)


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


def _knock_water(check, centre=None):
    import build
    import sim
    from checks.engine_knock_water import CHECK_LANES, LANES, name

    lane = CHECK_LANES[check][0]
    m, t, _ = build.resolve('engine_knock_water', check)
    e = sim.Sim(m, t)
    gun, wet, dry = (e.bodies[name(lane, p)] for p in ('gun', 'wet', 'dry'))
    weapon, = gun.weapons
    # the rocket bursts a hair north of the lane (the engine's landings are at y 3280, its y floored to 20)
    e.meta_impact_detonate(weapon, centre or (1700 + LANES[lane][2], 3300.01, 219))
    return e, wet, dry


# engine_knock_water (Physics P3), the wet man's frames from his launch (173) to his landing, run ra3ext.log probe
# lines: man CampKWMan_mcp_1111_151010 (174-177), far CampKWFar_mcp_1111_151821 (174-176, apex 187, 201)
KNOCK_WATER = {'man': (5, {1: (2065.0, 3295.0, 220.36), 2: (2069.9, 3290.1, 222.98), 3: (2074.9, 3285.1, 220.36),
                           4: (2080.0, 3280.0, 212.50)}),
               'far': (29, {1: (2075.6, 3299.3, 215.52), 2: (2091.1, 3298.6, 218.33), 3: (2106.7, 3297.9, 220.90),
                            14: (2278.4, 3290.1, 234.46), 28: (2500.0, 3280.0, 212.50)})}


@pytest.mark.parametrize('check', ['man', 'far'])
def test_physics_p3_a_man_knocked_toward_water_lands_on_the_nearest_cell_he_can_stand_on(check):
    """engine_knock_water man / far (bench 11-11): his own landing in the trench (man 2220, far 2420) is moved to the
    nearest standable cell -- man back to his bank's 2080, far on to the far bank's top 2500, not back along the line --
    and the curve is rebuilt to it with the launch's height (Sim.knock_landing, Ground.stand); he lives."""
    import sim
    e, wet, dry = _knock_water(check)
    count, frames = KNOCK_WATER[check]
    _, _, points = e.impact_flights[id(wet)]
    assert len(points) == count
    for k, want in frames.items():
        assert points[k] == pytest.approx(want, abs=0.12), k
    assert id(dry) in e.impact_flights
    assert (sim.GAP_WEAPON, 'MetaImpactNugget') not in e.unmodeled


# engine_knock_water tank / ramp / edge (Physics P3, vehicles), the runs' ra3ext.log: the burst centre (`shockinfo`),
# each Hammer's landing (`build ... land=`), its points (`built N=`), one probe line mid-curve, gone or not
# (tank CampKWTank_mcp_1111_151445, ramp CampKWRamp_mcp_1111_172522, edge CampKWEdge_mcp_1111_174551)
KNOCK_WATER_TANK = {
    'tank': ((2608.471, 3281.000, 218.037),
             {'man': ((2490, 3530, 203.125), 20, (180, (2559.8, 3384.0, 223.66)), True),
              'wet': ((2490, 3330, 203.125), 6, (176, (2502.1, 3317.9, 213.26)), True),
              'dry': ((2830, 3330, 212.5), 16, None, False)}),
    'ramp': ((2589.330, 781.000, 274.466),
             {'man': ((2650, 890, 268.75), 13, None, False),
              'wet': ((2470, 810, 240.625), 11, (178, (2495.2, 805.0, 267.11)), False),
              'dry': ((2730, 810, 268.75), 10, None, False)}),
    'edge': ((2629.330, 3281.000, 218.216),
             {'man': ((2690, 3390, 212.5), 13, None, False),
              'wet': ((2510, 3310, 212.5), 9, None, False),
              'dry': ((2770, 3310, 212.5), 10, None, False)}),
    # climb CampKWClimb_mcp_1111_214128: the wet one up the table's east ramp onto its top (56.25 higher), apex 275.00
    'climb': ((3149.330, 781.000, 218.216),
              {'man': ((3290, 1030, 212.5), 21, None, False),
               'wet': ((2930, 850, 268.75), 18, (185, (2974.6, 835.1, 275.00)), False),
               'dry': ((3350, 830, 212.5), 14, None, False)})}


@pytest.mark.parametrize('check', ['tank', 'ramp', 'edge', 'climb'])
def test_physics_p3_a_hammer_lands_on_the_plus_10_grid_and_drowns_within_10_of_the_water(check):
    """engine_knock_water tank / ramp / edge / climb (bench 11-11): a knocked Hammer lands on the 20 grid + 10;
    climb's wet one is pushed up the table's ramp and lands on its top, 56.25 higher, where its own landing says
    (2930, 850), the curve's controls 1.3 a over the landing;
    tank's wet one, its landing 2410 in the trench, goes to the nearest cell over the water, (2490, 3330) on the
    far bank's slope (Sim.knock_landing_vehicle, Ground.stand_vehicle); a landing cell within 10 of the water kills
    the frame it lands -- tank's wet one 178, its direct hit 192 (Ground.drowns) -- while ramp's dry slope (65 over)
    and edge's bank top (20 over) do not; the curves down to lower ground match the engine's frames
    (simunits.meta_impact_trajectory)."""
    import sim
    from checks.engine_knock_water import CHECK_LANES, DEAD, name

    centre, bodies = KNOCK_WATER_TANK[check]
    lane = CHECK_LANES[check][0]
    e, _, _ = _knock_water(check, centre)
    assert (sim.GAP_WEAPON, 'MetaImpactNugget') not in e.unmodeled
    assert int(bodies['wet'][3]) == DEAD[check]
    want = {}
    for p, (land, count, mid, dies) in bodies.items():
        b = e.bodies[name(lane, p)]
        _, start, points = e.impact_flights[id(b)]
        assert len(points) == count, p
        assert points[-1] == pytest.approx(land, abs=1e-3), p
        if mid:
            assert points[mid[0] - 173] == pytest.approx(mid[1], abs=.06), p
        want[p] = (b, start + count - 1, dies)
    e.firing, e.volleys = [], []
    for _ in range(25):
        e.eng.frame += 1
        e.deal(1/15)
        for p, (b, last, dies) in want.items():
            assert b.alive == (not dies or e.frame_now() < last), (p, e.frame_now())


# engine_knock_water gate<A> (Physics P3 gate, bench 11-11): edge's layout, the burst centre of edge's run (the same
# shockinfo centre in gate91's ra3ext.log); each Hammer's (landing, points) from its `build` / `built` lines, None =
# no `shock` line at all (CampKWGate91_mcp_1111_205100, CampKWGate90_mcp_1111_205701, CampKWGate89_mcp_1111_205321)
_GATE_FLY = {'man': ((2670, 3350, 212.5), 11), 'wet': ((2530, 3310, 212.5), 8), 'dry': ((2750, 3310, 212.5), 9)}
KNOCK_GATE = {'gate91': _GATE_FLY, 'gate90': _GATE_FLY, 'gate89': {'man': None, 'wet': None, 'dry': None}}


@pytest.mark.parametrize('check', sorted(KNOCK_GATE))
def test_physics_p3_a_shock_under_the_hammers_resistance_90_launches_nothing(check):
    """engine_knock_water gate91 / gate90 / gate89 (bench 11-11): the Hammer's ShockwaveResistance 90 (BaseVehicle)
    gates the nugget's raw amount -- at 91 and 90 all three fly, the dry one too though its falloff leaves it
    0.63 x 90 = 57; at 89 none (no ra3ext `shock` line) -- and the ones that fly land as the engine's `build` lines say
    (simunits.meta_impact_resistance, Sim.meta_impact_detonate)."""
    import simunits
    from checks.engine_knock_probe import PROBE_TANK
    from checks.engine_knock_water import name

    e, _, _ = _knock_water(check, KNOCK_WATER_TANK['edge'][0])
    assert simunits.meta_impact_resistance(PROBE_TANK, e.own) == 90
    for p, want in KNOCK_GATE[check].items():
        flight = e.impact_flights.get(id(e.bodies[name('tank', p)]))
        if want is None:
            assert flight is None, p
        else:
            land, count = want
            assert len(flight[2]) == count, p
            assert flight[2][-1] == pytest.approx(land, abs=1e-3), p


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


@pytest.mark.parametrize('lane,collision,shock,y', [
    ('rocket', 174, 204, 3750), ('strong', 173, 192, 850),
])
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'Delayed collision dispatch does not consume the expiry queue or advance Physics; '
    'see work/re/handoff-c.md and work/re/c_meta_dispatch_gap_report.md'))
def test_meta_impact_delayed_collision_replays_observed_shock_frame(lane, collision, shock, y):
    """Recorded arrival -> actual dispatch -> observed first delayed sample.

    CampKDA_mcp_1111_005836: counters1174/100/1173/100. Neighbour probes
    at shock204/192 read (2364.2, y-.7, 215.24), already past the start.
    D39 establishes phase-1 expiry before Physics modules. Collision inputs
    from health counters remain INFERRED; curved projectile arrival is supplied.
    This asserts only that recorded sample, never a physical landing frame or
    an unobserved Physics pause. Later probe/module ordering remains a gap.
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
    assert collision + simunits.meta_impact_delay_frames(effect['delay_seconds']) + 1 == shock
    e.firing, e.volleys = [], []
    e.eng.frame = collision
    e.queue_projectile_hit(collision, victim, weapon['dmg'], by, weapon, (2300, y, 219))
    for frame in range(collision, shock + 1):
        e.eng.frame = frame
        e.deal(1/15)
        assert victim.hp == pytest.approx(148.5)
        assert near.hp == 150
        got = (near.x, near.y, e.impact_ground_z(near.x, near.y) if near.z is None else near.z)
        expected = (2360, y, 212.5) if frame < shock else (2364.2, y-.7, 215.24)
        assert got == pytest.approx(expected, abs=.051), (lane, frame, got)


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


def test_physics_p4_a_knocked_man_fires_his_order_while_lying_before_he_stands():
    """engine_knock_probe fire (bench 11-11 CampKPFire_mcp_1111_163338 PASS): the flung man (lift 174, on the ground at
    (2300, 3180) from 300, still there to the end) is ordered at frame 240, in the air, to attack a Hammer 100 east of
    the landing spot ((2400, 3060)); the unshot control, ordered on the same frame at a Hammer 100 east of him, first
    hits it within ~1 s. Timed against the rocket man's own hit (frame 173, his counter drops at bench s10.1), the
    flung man's Hammer first drops ~9.0 s of bench samples later: frame ~300-316 -- from the landing, well before the
    landing hold ends at 338: the hold stops his feet, not his gun, and the attack order given in the air is kept.
    The simulator's 2-D reach has the target from frame 292, ~840 up: no fire in the air (INFERRED, not told apart)."""
    import build
    import sim
    import simunits
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_probe', 'fire')
    e = sim.Sim(m, t)
    man, target = e.bodies[name('rocket', 'man')], e.bodies[name('fire', 'target')]
    man.status.discard('NO_ATTACK')
    man.script_status.discard('NO_ATTACK')
    points = simunits.meta_impact_trajectory((2300, 3750, 212.5), (0, -1.7730, 45.6088), (2300, 3180, 212.5))
    assert points[-1] == (2300, 3180, 212.5)
    e.impact_flights = {id(man): (man, 173, points)}
    man.x, man.y = points[0][:2]
    e.eng.frame = 173
    full, first = target.health, None
    while e.eng.frame < 345:
        e.eng.frame += 1
        if e.eng.frame == 240:
            e.order_attack(man, target.name)
        e.move(1 / 15)
        e.fight()
        e.deal(1 / 15)
        if first is None and target.health < full:
            first = e.eng.frame
    assert (man.x, man.y) == (2300, 3180)
    assert first is not None and 300 <= first <= 316 < 338, first


def test_physics_p4b_a_knocked_man_does_not_fire_in_the_air_with_the_target_in_reach():
    """engine_knock_water farfire (bench 11-11 CampKWFarfire_mcp_1111_212052): far's push flings the dry man low and
    flat, 1940 -> 1560 (shock 175, N 25, ~20 up), past a Hammer 60 off his line; ordered on it at frame 176, he has it
    within his 150 (2-D gap) over frames ~182..196 -- and the Hammer stays 100 until s15, its first damage at s16,
    after he landed (199), lay out of reach and walked in: no fire in the air (Sim.fight skips impact_flights). The
    curve is the engine's own (probe lines 176, 177, 187, 199)."""
    import math
    import sim
    from checks.engine_knock_water import name

    m, t, _ = build_farfire()
    e = sim.Sim(m, t)
    gun = e.bodies[name('man', 'gun')]
    weapon, = gun.weapons
    e.meta_impact_detonate(weapon, (2000, 3300.01, 219))
    man, target = e.bodies[name('man', 'dry')], e.bodies[name('man', 'target')]
    _, _, points = e.impact_flights[id(man)]
    assert len(points) == 25
    for k, want in {1: (1924.3, 3299.2, 216.01), 2: (1908.6, 3298.3, 219.21), 12: (1751.4, 3290.1, 234.46),
                    24: (1560.0, 3280.0, 212.5)}.items():
        assert points[k] == pytest.approx(want, abs=0.06), k
    e.impact_flights[id(man)] = (man, 175, points)
    for b in e.bodies.values():
        if b is not man:
            b.status.add('NO_ATTACK')
    man.status.discard('NO_ATTACK')
    man.script_status.discard('NO_ATTACK')
    weapon, = man.weapons
    e.eng.frame, full, reach = 175, target.health, []
    while e.eng.frame < 199:
        e.eng.frame += 1
        if e.eng.frame == 176:
            e.order_attack(man, target.name)
        e.meta_impact_tick()
        e.move(1 / 15)
        e.fight()
        e.deal(1 / 15)
        if sim.Sim.in_range(man, target, weapon):
            reach.append(e.eng.frame)
        assert target.health == full, e.eng.frame
    assert reach and reach[0] <= 183 and reach[-1] >= 195, reach
    assert (man.x, man.y) == (1560, 3280)
    assert math.hypot(target.x - man.x, target.y - man.y) - man.radius - target.radius > weapon['range']


def build_farfire(check='farfire'):
    import build
    return build.resolve('engine_knock_water', check)


@pytest.mark.parametrize('check', ['farfire', 'farwalk'])
def test_physics_p4b_an_attack_order_kept_through_the_knock_walks_at_landing_plus_50(check):
    """engine_knock_water farfire / farwalk (bench 11-11 CampKWFarfire_mcp_1111_212052, CampKWFarwalk_mcp_1111_212626):
    landed at 199 out of reach of the Hammer he was ordered on in the air (farfire ~158 degrees round from his flight,
    farwalk straight ahead), he lies to 248 and takes his first step at 249 both times -- landing + 50, a move order's
    + 38 plus simunits.KNOCK_ATTACK_WAIT 12, not a turn. (Where he stops to fire, centre 171.6 / 164.2 off, gap 140 /
    133, deeper in than the simulator's range edge, is not modelled.)"""
    import sim
    from checks.engine_knock_water import name

    m, t, _ = build_farfire(check)
    e = sim.Sim(m, t)
    weapon, = e.bodies[name('man', 'gun')].weapons
    e.meta_impact_detonate(weapon, (2000, 3300.01, 219))
    man, target = e.bodies[name('man', 'dry')], e.bodies[name('man', 'target')]
    _, _, points = e.impact_flights[id(man)]
    e.impact_flights[id(man)] = (man, 175, points)
    for b in e.bodies.values():
        if b is not man:
            b.status.add('NO_ATTACK')
    man.status.discard('NO_ATTACK')
    man.script_status.discard('NO_ATTACK')
    e.eng.frame, first = 175, None
    while e.eng.frame < 260 and first is None:
        e.eng.frame += 1
        if e.eng.frame == 176:
            e.order_attack(man, target.name)
        e.meta_impact_tick()
        e.move(1 / 15)
        e.fight()
        e.deal(1 / 15)
        if e.eng.frame > 199 and (man.x, man.y) != (1560, 3280):
            first = e.eng.frame
    assert first == 249


@pytest.mark.parametrize('lane', ['plain', 'gm30'])
def test_physics_p5_a_shot_down_wreck_falls_the_knock_curve_under_its_own_gravity(lane):
    """Bench 11-11 engine_crash_fall (CampCFFall_mcp_1111_221320): an Apollo copy killed 175 up drops its wreck
    copy; the wreck's own GravityMultiplier (1 / 30) sets the fall, the logged landing, N 30 / 8 and every probe z."""
    import build
    import simunits
    from checks.engine_crash_fall import BENCH, LANES
    m, t, name = build.resolve('engine_crash_fall', 'fall')
    assert name == 'CampCFFall'
    wreck = next(u for u in m.units if u.id == LANES[lane][0] + 'Dying')
    gm = wreck.params['gm']
    assert (gm == 30) == ('GravityMultiplier="30"' in wreck.xml)
    start, v, landing, n, zs = BENCH[lane]
    points, end = simunits.meta_impact_fall(start, v, 212.5, gravity=gm)
    assert end == landing and len(points) == n
    assert [round(p[2], 2) for p in points[2:]] == pytest.approx(zs, abs=0.06)


def test_physics_p5_the_apollo_s_air_death_reads_its_crash_from_the_data():
    """Sim.air_crash's data (simunits.air_wrecks / fly_height / crash_frames): an Apollo killed in the air leaves one
    of Collapse (no weapon) and Dying (x 0.5, falls, 150 EXPLOSIVE radius 20, allies 50 %), 175 up; the wreck's fall
    from the bench's kill (engine_crash_fall plain) hits 29 frames on, at (3160, 1500)."""
    import simunits
    choose, wrecks = simunits.air_wrecks('AlliedFighterAircraft')
    assert choose and [w['template'] for w in wrecks] == ['AlliedFighterAircraft_Collapse', 'AlliedFighterAircraft_Dying']
    dying = wrecks[1]
    assert (dying['scale'], dying['gravity'], dying['falls']) == (0.5, 1.0, True) and not wrecks[0]['weapons']
    assert [(d[0], d[1], d[2], d[5]) for d in dying['weapons']] == [(150.0, 'EXPLOSIVE', 20.0, 0.5)]
    assert simunits.fly_height('AlliedFighterAircraft') == simunits.fly_height('SovietFighterAircraft') == 175.0
    assert simunits.crash_frames((2885.0, 1500.47, 387.44), (7.5, 0.003, 0.0011), 212.5) == (29, (3160, 1500, 212.5))


def _crash_digits(v):
    from checks.engine_crash_fall import HIT_STEP
    return {k: v // step % 100 if k != 'out' else v // step for k, step in HIT_STEP.items()}


def test_physics_p5_a_hovering_apollo_s_crash_hurts_what_is_under_it_as_on_the_bench():
    """Bench 11-12 engine_crash_hit (CampCHHit_mcp_1112_111034): two Apollo copies hovering 175 over a Hammer each are
    killed; each wreck (v 0.1 drift, 38 points) hits 38 counted frames after the kill, the enemy Hammer to 72 %, the
    player's own to 86 % (allies 50 %); the Hammer 40 off the flying plane's landing is never hit. The flying lane's
    plane is where the sim's coarse flight puts it (no acceleration), so only its untouched neighbour is held here."""
    import build
    import sim
    from checks.engine_crash_fall import HIT_BENCH
    m, t, name = build.resolve('engine_crash_hit', 'hit')
    assert name == 'CampCHHit'
    s = sim.Sim(m, t).run(13.0)                     # the check's RUN: the flying lane's miss counts < 100
    frames, health_in, health_h, health_g = s.series[-1][1]
    got = _crash_digits(frames)
    assert (got['H'], got['G']) == (HIT_BENCH['frames']['H'], HIT_BENCH['frames']['G']), got
    assert got['out'] >= 85, got                                    # bench: untouched every frame (150 at s15)
    assert (health_h, health_g) == (HIT_BENCH['health']['H'], HIT_BENCH['health']['G'])
    assert 'air crash' in s.used


def test_physics_p5_the_flying_apollo_s_wreck_hits_its_last_point_as_on_the_bench():
    """The flying lane from the bench's kill (fall's plain start, logged again in CampCHHit): 30 points, the hit on
    the last -- counted 30 frames (crash_frames + 1, as the hovering ones' 37 + 1 = 38)."""
    import simunits
    from checks.engine_crash_fall import BENCH, HIT_BENCH
    start, v, landing, n, _ = BENCH['plain']
    frames, end = simunits.crash_frames(start, v, 212.5)
    assert end == landing and frames + 1 == HIT_BENCH['frames']['in'] == n
    assert simunits.crash_frames((3000.0, 2000.0, 387.5), (0.1, 0.0, 0.0), 212.5) == (37, (3000, 2000, 212.5))


def _face_health():
    """Sim.air_crash from the bench's kill (x 2885, 15 a frame east) of engine_crash_face's four planes,
    death_blast_due past the landing: each Hammer's health percent as the counter reads it."""
    import math
    import build
    import sim
    from checks.engine_crash_fall import FACE_LANES, face_name
    m, t, name = build.resolve('engine_crash_face', 'face')
    assert name == 'CampCKFace'
    s = sim.Sim(m, t)
    s.eng.frame = 105
    for k, (y, _) in FACE_LANES.items():
        b = s.bodies[face_name(k)]
        b.x, b.y, b.z, b.path, b.speed, b.engaged = 2885.0, y, None, [(4200.0, y)], 15.0 * 15, None
        s.air_crash(b)
    s.death_blast_due(105 + 40)
    tanks = {k: s.bodies[face_name('Tank ' + k)] for k in FACE_LANES}
    return {k: math.floor(b.hp / b.max_hp * 100 + 1e-9) for k, b in tanks.items()}


def test_physics_p5_the_flying_wreck_hits_its_hammer_by_the_side_it_comes_in_from():
    """Bench 11-12 engine_crash_face (CampCKFace_mcp_1112_120614): hit's 70 against the hover's 72 was the armour's
    flank scalar (BaseTankArmor Rear 110 / Side 105; simunits.flank), not a collision or the shock -- the Hammers
    facing east / north under the y < 2048 wrecks take rear / side as from the wreck's way in (west)."""
    from checks.engine_crash_fall import FACE_BENCH
    got = _face_health()
    assert (got['E'], got['N']) == (FACE_BENCH['E'], FACE_BENCH['N']) == (70, 71), got


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'bench 11-12 engine_crash_face: the Hammers facing west / south (y 2100 / 2400) take side 71 / rear 70 -- the '
    "wreck's resting hair off the centre north, not west (INFERRED float32 residue over y 2048); the sim takes the "
    'way in (west): front 72 / side 71'))
def test_physics_p5_the_wreck_s_float_residue_over_y_2048_sets_its_side():
    from checks.engine_crash_fall import FACE_BENCH
    got = _face_health()
    assert (got['W'], got['S']) == (FACE_BENCH['W'], FACE_BENCH['S']), got


def test_meta_impact_relation_probe_changes_only_relationship():
    """Two identical payloads and mixed allegiance make the filter observable."""
    import re
    import xml.etree.ElementTree as ET
    import build
    from checks.engine_knock_relation import retail_shock
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_relation', 'a')
    original = ET.fromstring(retail_shock())
    for lane, uid in (('yuri', 'CNV_KnockYuri'), ('rocket', 'CNV_KnockRocket')):
        gun = next(u for u in m.units if u.id == uid)
        payload, = re.findall(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', gun.xml, re.S)
        actual = ET.fromstring(payload)
        assert actual.attrib == original.attrib
        expected = dict(original.find('SpecialObjectFilter').attrib)
        if lane == 'rocket':
            expected['Relationship'] = 'ALLIES'
        assert actual.find('SpecialObjectFilter').attrib == expected
        victim = next(o for o in m.objects if o.name == name(lane, 'man'))
        near = next(o for o in m.objects if o.name == name(lane, 'near'))
        assert (victim.side, near.side) == ('s1', 'p1')
        assert (near.x - victim.x, near.y - victim.y) == (20, 0)
        assert gun.names['rocket'] + '.xml' in gun.files
    assert len(t.counters) == 4


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason='MetaImpact relation/condition dispatch is missing; see work/re/c_meta_relation_report.md')
@pytest.mark.parametrize('lane,collision,moving,still,samples', [
    ('yuri', 173, 'man', 'near', [(798,3749,212.87), (796,3748,213.15), (794.1,3747,213.35)]),
    ('rocket', 174, 'near', 'man', [(2320,3746.7,213.40), (2320,3743.4,213.40), (2320,3740,212.50)]),
])
def test_meta_impact_relation_collision_replays_observed_selection(lane, collision, moving, still, samples):
    """CampKRelA_mcp_1113_140752: swap relationship, swap the moving body.

    Shock frames173/174 are raw; treating them as collision frames is INFERRED.
    The engine collision centre is supplied, so this does not claim curved
    arrival prediction. Negative positions alone cannot establish filtering.
    """
    import build
    import sim
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_relation', 'a')
    e = sim.Sim(m, t)
    e.firing, e.volleys = [], []
    e.eng.frame = collision
    by, victim, near = (e.bodies[name(lane, part)] for part in ('gun', 'man', 'near'))
    weapon, = by.weapons
    e.queue_projectile_hit(collision, victim, weapon['dmg'], by, weapon,
                           (victim.x,3750,219 if lane == 'yuri' else 219.001))
    e.deal(1/15)
    assert victim.hp == pytest.approx(148.5)
    assert near.hp == 150
    fixed = e.bodies[name(lane, still)]
    fixed_start = (fixed.x, fixed.y, 212.5)
    moving_body = e.bodies[name(lane, moving)]
    for frame, xyz in enumerate(samples, collision + 1):
        e.eng.frame = frame
        e.move(1/15)
        e.deal(1/15)
        def position(body):
            return body.x, body.y, e.impact_ground_z(body.x, body.y) if body.z is None else body.z
        assert position(fixed) == pytest.approx(fixed_start, abs=.051)
        assert position(moving_body) == pytest.approx(xyz, abs=.051)
