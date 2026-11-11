"""InformTarget controls and partial notification-to-armor execution; full replay stays a gap."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('inform_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.mark.parametrize('check_name', ['a', 'off'])
def test_inform_ai_has_one_slow_projectile_and_instant_player_low_controls(check_name):
    import build
    from contract import RETAIL_COMMANDS
    from checks import engine_inform_ai as probe

    m, t, _ = build.resolve('engine_inform_ai', check_name)
    ns = {'a': 'uri:ea.com:eala:asset'}
    assert len(m.name + check_name.title()) <= 15 and '_' not in m.name
    assert probe.COMMAND in RETAIL_COMMANDS
    assert [x[1] for x in t.counters] == [lane + ' info' for lane in probe.LANES]
    for lane, unit in zip(probe.LANES, m.units):
        root = ET.fromstring(unit.xml)
        weapons = root.findall('a:WeaponTemplate', ns)
        launch = next(w for w in weapons if w.get('id') == unit.names['weapon'])
        assert len(launch.findall('a:Nuggets/a:InformTargetNugget', ns)) == (0 if check_name == 'off' and lane == 'base' else 1)
        damage = root.find('.//a:DamageNugget', ns)
        assert damage.get('DamageType') == 'UNRESISTABLE'
        assert float(damage.get('Damage')) == (50 if lane == 'removed' else 150)
        projectiles = launch.findall('a:Nuggets/a:ProjectileNugget', ns)
        assert len(projectiles) == (0 if lane == 'order' else 1)
        assert float(launch.get('WeaponSpeed')) == (999999 if lane == 'order' else 75)
        for xml in unit.files.values():
            movement = ET.fromstring(xml).find('.//a:MoveInStraightLine', ns)
            assert float(movement.get('MuzzleVelocity')) == 5
        for weapon in weapons:
            if weapon is not launch:
                assert not weapon.findall('a:Nuggets/a:InformTargetNugget', ns)
    make = next(s for s in t.scripts if s.name == 'Test - make')
    creates = [a for a in make.do if a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT']
    assert [a[3] for a in creates] == [m.team('s1'), m.team('p1'), m.team('s1'), m.team('s1')]
    assert all(a[2] == 'SovietMiner' for a in creates)
    assert not any(a[0] == 'UNIT_CHANGE_OBJECT_STATUS' and a[2] == 'NO_ATTACK' for a in make.do)
    for lane in probe.LANES:
        hit = next(s for s in t.scripts if s.name == 'Test - hit ' + lane)
        assert ('UNIT_HEALTH', 'Info miner ' + lane, 0, 100) in hit.when


def test_inform_ai_off_changes_only_the_base_launch_nugget_and_expectation():
    import build

    original, before, _ = build.resolve('engine_inform_ai', 'a')
    ablated, after, _ = build.resolve('engine_inform_ai', 'off')
    for i, (left, right) in enumerate(zip(original.units, ablated.units)):
        assert right.xml == (left.xml.replace('<InformTargetNugget/>', '', 1) if i == 0 else left.xml)
        assert right.files == left.files
    assert original.objects == ablated.objects
    assert original.marks == ablated.marks
    assert before.scripts == after.scripts
    assert before.counters == after.counters and before.bench == after.bench
    assert after.expect[2:] == before.expect[1:]
    assert after.expect[:2] == [('base info', 31.0, '>=', 100000000, 34.0),
                              ('base info', 31.0, '<', 200000000, 34.0)]


def test_inform_ai_response_is_reported_as_a_gap_including_retail_cache():
    import build
    import sim
    import simunits

    retail = simunits._fight_data()['weapons']['SovietAntiVehicleVehicleTech1CannonWeapon']
    assert 'InformTargetNugget' in retail['unmodeled_effects']
    weapons = simunits._weapons(['''<WeaponTemplate id="head"><Nuggets>
        <AttributeModifierNugget AttributeModifierName="unused" RequiredTargetObjectStatus="IMMOBILE"/>
        </Nuggets></WeaponTemplate><WeaponTemplate id="launch"><Nuggets>
        <ProjectileNugget ProjectileTemplate="shell" WarheadTemplate="head"/>
        <InformTargetNugget/></Nuggets></WeaponTemplate>'''])
    resolved = simunits._resolve(weapons['launch'], weapons)
    assert set(resolved['unmodeled_effects']) == {'InformTargetNugget', 'AttributeModifierNugget'}
    # The existing direct-damage fixture isolates gap propagation from this
    # new probe's script-created AI units and unsupported armor status read.
    m, t, _ = build.resolve('engine_inform', 'damage')
    engine = sim.Sim(m, t)
    engine.shot_clock = True
    rows = engine.run(16).series
    assert tuple(rows[-1][1]) == (79, 1, 79, 1)
    assert (sim.GAP_WEAPON, 'InformTargetNugget') in engine.unmodeled
    import inventory
    # Retail target notifications are now registered by field form; the
    # runtime gap and whole tracking module must still remain explicit.
    assert inventory.NOTES[(inventory.MODULE, 'Behaviors/TrackIncomingWeaponFireBehavior')][0] == inventory.TODO


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason='Full script placement, custom projectile flight, miner AI enrollment/history and micro phase remain gaps')
@pytest.mark.parametrize('check_name, expected', [
    ('a', (1187051068, 87135068, 101003068, 87135089)),
    ('off', (87135068, 87135068, 101003068, 87135089)),
])
def test_inform_ai_advance_response_matches_engine_inform_ai_observation(check_name, expected):
    """Second: hit87/87/1/87, shield51/none/3/none; third: base shield absent.

    Frozen automatic readings, before manual controls; no scalar fitting of
    the unexplained ~2.4s advance window or projectile muzzle collision.
    """
    import build
    import sim

    m, t, _ = build.resolve('engine_inform_ai', check_name)
    engine = sim.Sim(m, t)
    engine.shot_clock = True
    rows = engine.run(36).series
    assert tuple(rows[-1][1]) == expected
    assert all(tuple(row) == expected for sec, row in rows if sec >= 31)


@pytest.mark.parametrize('check_name, run_name', [
    ('a', 'CampIPA_mcp_1110_231923'), ('off', 'CampIPOff_mcp_1110_231533'),
])
def test_inform_incoming_table_drives_miner_armor_from_engine_inform_probe(check_name, run_name, monkeypatch):
    """Replay observed notifications, not collision/micro phase or full Sim.run.

    Slow lanes: launch302, damage150/150/50, hit377, expiry404, removal389.
    The 2s window first sees the damage at347. Player and low controls stay off.
    Instant history is outside this slice; full packed replay stays strict xfail.
    """
    import re
    from types import SimpleNamespace
    import build
    import sim
    import simai
    import labpaths

    log = Path(labpaths.WORK) / 'testbench/runs' / run_name / 'ra3ext.log'
    if not simai.available():
        pytest.skip('ra3model.ai unavailable')
    m, t, _ = build.resolve('engine_inform_ai', check_name)
    e = sim.Sim(m, t)
    ai = m.player('s1')
    bodies = {}
    for lane in ('base', 'high', 'removed'):
        e.add('Replay ' + lane, 'SovietMiner', m.player('p1') if lane == 'high' else ai, 0, 0)
        bodies[lane] = e.body('Replay ' + lane)
    clock = [302]
    monkeypatch.setattr(e, 'frame_now', lambda: clock[0])
    # Runtime identifiers remain in the private log. Map source numbers, not addresses.
    # Sanitized event fixture keeps the replay runnable without private artifacts.
    observed = {13: ('high', 150.0, 377, 404), 14: ('instant', 150.0, 302, 302),
                15: ('low', 50.0, 377, 404)}
    if check_name == 'a':
        observed[12] = ('base', 150.0, 377, 404)
    lines = log.read_text(encoding='utf-8').splitlines() if log.exists() else []
    actual = {}
    for line in lines:
        if 'frame=302 n=1' not in line:
            continue
        row = re.search(r'src=(\d+) w=(\w+) dmg=([\d.]+) hit=(\d+) exp=(\d+)', line)
        assert row
        source, key, damage, hit, expiry = row.groups()
        actual[int(source)] = (key, float(damage), int(hit), int(expiry))
    if lines:
        assert {src: row[1:] for src, row in actual.items()} == {src: row[1:] for src, row in observed.items()}
        observed = actual
    for source, lane in ((12, 'base'), (13, 'high'), (15, 'removed')):
        if source in observed:
            key, damage, hit, expiry = observed[source]
            assert (damage, hit, expiry) == (50 if lane == 'removed' else 150, 377, 404)
            e.incoming_add(bodies[lane], source, key, damage, hit, expiry)
    assert (12 in observed) == (check_name == 'a')
    host = simai.SimAI(e)
    brain = object.__new__(simai.Brain)
    brain.host, brain.sim, brain.player = host, e, ai
    brain.view = SimpleNamespace(things=[], enemies=frozenset())
    brain.aim_of = lambda b, reach: None
    brain.fired = []
    team = SimpleNamespace(members=[simai.Unit(b) for b in bodies.values()])
    mc = host.mod['micro']
    manager = mc.MicroManager(mc.MicroInfo('replay'),
                             fire=lambda u, info: brain.fire_unit(None, 'replay', u, info))
    clock[0] = brain.frame = 346
    before = brain.micro_team(None, 346, team)
    assert all(u.damage(0, 2) == 0 for u in before.units)
    manager.round(346, before)
    assert not brain.fired
    clock[0] = brain.frame = 347
    visible = brain.micro_team(None, 347, team)
    assert [u.damage(0, 2) for u in visible.units] == ([150, 150, 50] if check_name == 'a' else [0, 150, 50])
    manager.round(347, visible)
    assert bodies['base'].armor_up == (check_name == 'a')
    assert not bodies['high'].armor_up and not bodies['removed'].armor_up
    if check_name == 'a':
        base = bodies['base']
        assert {'SPECIAL_ARMOR_ACTIVE', 'GENERIC_TOGGLE_STATE'} <= base.status
        assert base.taken < 1 and base.hp == 500
        e.modify(base)
        assert 'SPECIAL_ARMOR_ACTIVE' in base.status
        # New wrappers must preserve the already active state.
        again = brain.micro_team(None, 347, team)
        assert again.units[0].toggle_index == 1
        manager.round(347, again)
        assert base.armor_up
        # Wrong source/key cannot delete it; the original removal does.
        e.incoming_hit(base, 99, observed[12][0])
        assert e.expected_damage(base, 0, 2) == 150
        clock[0] = 389
        if lines:
            assert sum('frame=389 n=0' in line for line in lines) == 3
        e.incoming_hit(base, 12, observed[12][0])
        assert e.expected_damage(base, 0, 2) == 0
        clock[0] = brain.frame = 390
        manager.round(390, brain.micro_team(None, 390, team))
        assert not base.armor_up and 'SPECIAL_ARMOR_ACTIVE' not in base.status
    clock[0] = 405
    assert e.expected_damage(bodies['removed'], 0, 2) == 0


def test_inform_max_changes_only_base_factor_for_engine_inform_max():
    import build

    original, before, _ = build.resolve('engine_inform_probe', 'a')
    changed, after, _ = build.resolve('engine_inform_max', 'a')
    assert len(changed.name + 'A') <= 15 and changed.ext
    assert original.objects == changed.objects and original.marks == changed.marks
    assert before.scripts == after.scripts and before.bench == after.bench
    assert before.counters == after.counters
    assert before.expect[:-2] == after.expect[:-2]
    assert after.expect[-2:] == [(label, 45, op, value) for label, _, op, value in before.expect[-2:]]
    assert len(original.units) == len(changed.units) == 5
    for i, (left, right) in enumerate(zip(original.units, changed.units)):
        assert right.xml == (left.xml.replace('<InformTargetNugget/>',
                            '<InformTargetNugget MaxTimeToImpactFudgeFactor="1.6"/>', 1)
                            if i == 0 else left.xml)
        assert right.files == left.files


@pytest.mark.parametrize('run_name', ['CampIMaxA_mcp_1111_001917', 'CampIMaxA_mcp_1111_002132'])
def test_inform_max_launch_matches_engine_inform_max_observed_deadline(run_name, monkeypatch):
    """Recorded target notification, not full flight/AI or expiry-cleanup phase.

    engine_inform_max:a retains the engine_inform_probe:a controls; only
    base Max=1.6 changes expiry404 to444, not launch302/hit377/removal389.
    The normalized fixture keeps runtime addresses/keys in private logs.
    """
    import build
    import labpaths
    import re
    import sim

    log = Path(labpaths.WORK) / 'testbench/runs' / run_name / 'ra3ext.log'
    if log.exists():
        lines = log.read_text(encoding='utf-8').splitlines()
        entries = {}
        for line in lines:
            if not line.startswith('incoming ') or 'frame=302 n=1' not in line:
                continue
            row = re.search(r'object=(\w+).*src=(\d+) .*dmg=([\d.]+) hit=(\d+) exp=(\d+)', line)
            assert row
            obj, source, damage, hit, expiry = row.groups()
            entries[int(source)] = (float(damage), int(hit), int(expiry))
            removed = 304 if int(source) == 14 else 389
            assert any(f'object={obj} frame={removed} n=0' in later for later in lines)
        assert entries == {12: (150, 377, 444), 13: (150, 377, 404),
                           14: (150, 302, 302), 15: (50, 377, 404)}
    m, t, _ = build.resolve('engine_inform_max', 'a')
    e = sim.Sim(m, t)
    clock = [302]
    monkeypatch.setattr(e, 'frame_now', lambda: clock[0])
    for lane, damage, hit, expiry in (('base', 150, 377, 444),
                                      ('high', 150, 377, 404),
                                      ('removed', 50, 377, 404),
                                      ('order', 150, 302, 302)):
        gun = e.body('Info gun ' + lane)
        # Representative distance within the default timing's constrained interval;
        # actual muzzle/target offsets are still INFERRED, not replayed geometry.
        e.add('Max replay ' + lane, 'SovietMiner', m.player('s1'), gun.x, gun.y + 442)
        target = e.body('Max replay ' + lane)
        weapon, = gun.weapons
        assert weapon['inform'] == [dict(min=.85, max=1.6 if lane == 'base' else 1.15)]
        e.inform_launch(target, gun, weapon)
        assert e.incoming[id(target)] == [(id(gun), weapon['weapon_key'], damage, hit, expiry)]
        assert target.hp == 500
        if lane == 'order':
            clock[0] = 304
        else:
            clock[0] = 346
            assert e.expected_damage(target, 0, 2) == 0
            clock[0] = 347
            assert e.expected_damage(target, 0, 2) == damage
            clock[0] = 389
        e.incoming_hit(target, id(gun), weapon['weapon_key'])
        assert not e.incoming[id(target)]
        clock[0] = 302


def test_inform_launch_formula_and_matching_hit_lifecycle(monkeypatch):
    import build
    import sim
    import simunits

    m, t, _ = build.resolve('engine_inform_ai', 'a')
    e = sim.Sim(m, t)
    gun = e.body('Info gun base')
    e.add('Replay target', 'SovietMiner', m.player('s1'), gun.x, gun.y + 442)
    target = e.body('Replay target')
    clock = [302]
    monkeypatch.setattr(e, 'frame_now', lambda: clock[0])
    weapon, = gun.weapons
    assert weapon['inform'] == [dict(min=0.85, max=1.15)]
    assert weapon['weapon_speed'] == 75
    e.inform_launch(target, gun, weapon)
    assert e.incoming[id(target)] == [(id(gun), weapon['weapon_key'], 150, 377, 404)]
    # No tracking module, no table entry; no damage or HP mutation on notification.
    e.inform_launch(gun, gun, weapon)
    assert id(gun) not in e.incoming and target.hp == 500
    e.incoming_add(target, 999, 'other', 10, 377, 450)
    clock[0] = 347
    assert e.expected_damage(target, 0, 2) == 160
    assert e.expected_damage(target, 0, 0) == 0
    e.queue_projectile_hit(389, target, 150, gun, weapon)
    gun.alive = False
    e.firing, e.volleys = [], []
    clock[0] = 389
    e.deal(1/15)
    assert target.hp == 350
    assert e.expected_damage(target, 0, 2) == 10
    clock[0] = 451
    assert e.expected_damage(target, 0, 2) == 0
    # Retail cache was rebuilt with the new launch fields, preserving whole gap.
    retail = simunits._fight_data()['weapons']['SovietAntiVehicleVehicleTech1CannonWeapon']
    assert retail['inform'] and 'InformTargetNugget' in retail['unmodeled_effects']
    # Override factors and fractional duration distinguish truncation from rounding.
    clock[0] = 302
    target.y = gun.y + 103.75
    custom = dict(weapon, inform=[dict(min=0.5, max=1.6)], weapon_key='custom', dmg=100)
    e.inform_launch(target, gun, custom)
    assert e.incoming[id(target)] == [(id(gun), 'custom', 100, 312, 336)]
    assert e.expected_damage(target, 0, 10/15) / target.max_hp == 0.2
    e.incoming_hit(target, id(gun), 'custom')
    instant = dict(custom, weapon_speed=0)
    e.inform_launch(target, gun, instant)
    assert e.incoming[id(target)] == [(id(gun), 'custom', 100, 302, 302)]


@pytest.mark.parametrize('check_name', ['a', 'off'])
def test_inform_normal_fire_records_launch_and_deletes_on_arrival(check_name, monkeypatch):
    """Synthetic shot_clock dispatch, not script placement/collision phase replay."""
    import build
    import sim

    m, t, _ = build.resolve('engine_inform_ai', check_name)
    # As in the MetaImpact wiring test, use the modeled retail straight shell.
    # Sim.own currently omits Unit.files; this is not the original slow flight.
    import re
    from checks.engine_shot import SHELL
    for unit in m.units:
        unit.xml = re.sub(r'ProjectileTemplate="[^"]+"', f'ProjectileTemplate="{SHELL}"', unit.xml)
    e = sim.Sim(m, t)
    e.shot_clock = True
    clock = [302]
    monkeypatch.setattr(e, 'frame_now', lambda: clock[0])
    e.firing, e.volleys = [], []
    for lane in ('base', 'high', 'removed'):
        gun = e.body('Info gun ' + lane)
        e.add('Dispatch ' + lane, 'SovietMiner', m.player('s1'), gun.x, gun.y + 442)
        e.volleys.append((e.body('Dispatch ' + lane), gun.weapons[0], gun))
    e.t = 20
    e.deal(1/15)
    clock[0] += 1
    e.t += 1/15
    e.deal(1/15)
    notified = {b.name for b in e.bodies.values() if e.__dict__.get('incoming', {}).get(id(b))}
    assert notified == {'Dispatch high', 'Dispatch removed'} | ({'Dispatch base'} if check_name == 'a' else set())
    for target, weapon, gun in e.volleys:
        rows = e.incoming.get(id(target), [])
        if rows:
            assert rows == [(id(gun), weapon['weapon_key'], weapon['dmg'], clock[0] + 75, clock[0] + 102)]
    assert len(e.projectile_hits) == 3
    arrival = max(hit[0] for hit in e.projectile_hits)
    e.volleys = []
    clock[0] = arrival
    e.deal(1/15)
    assert all(not rows for rows in e.incoming.values())
    assert [e.body('Dispatch ' + lane).hp for lane in ('base', 'high', 'removed')] == [350, 350, 450]
