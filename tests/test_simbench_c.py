"""Engine line C's simulator-vs-bench tests (object modules, weapon effects): each takes a reading the bench made and holds
the simulator to it, so a module can be registered in inventory.BENCHED_TESTS against it. A separate file from
test_simbench.py so line C's hunks never share a file with another line's uncommitted ones."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
# loaded by file: simbench.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
_spec = importlib.util.spec_from_file_location('simbench_c', ROOT / 'experimental' / 'cnv' / 'simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)
import engine.objects.modifier as simmodifier  # noqa: E402


def _clocks(b):
    """b's clip clocks by weapon key (step W3: its WeaponSet's, the host's Sim.clocks before)."""
    from engine.kernel import interfaces
    m = b.find(interfaces.WeaponSet) if b.modules else None
    return (m.clocks if m is not None else None) or {}


def test_levelup_heroic_vision_sights_inner_engineer_after_near_controls_are_deleted():
    """engine_levelvision a:11/11/11/11 ->0/0/0/0 ->0/101/0/100 at240/310."""
    import build
    import sim
    from checks.engine_levelup import SHROUD_LANES
    m, t, _ = build.resolve('engine_levelvision', 'a')
    e = sim.Sim(m, t)
    e.shot_clock = True
    rows = e.run(25).series
    # Freeze actual bench readings independently of the check's predictions.
    for first, last, values in ((2, 4, (11, 11, 11, 11)), (8, 10, (0, 0, 0, 0)),
                                (20, 24, (0, 101, 0, 100))):
        readings = [tuple(row) for at, row in rows if first <= at < last]
        assert readings and all(row == values for row in readings), (readings, values)
    guns = [e.body(m.role(lane).name) for lane in SHROUD_LANES]
    assert [b.level_rank for b in guns] == [1, 4, 1, 4]
    assert [b.level_vision for b in guns] == [1, 1.25, 1, 1.25]
    assert [b.sight for b in guns] == [200] * 4  # automatic acquisition remains unmeasured
    assert [b.vision for b in guns] == [500, 625, 500, 625]  # independent shroud modifier
    for _ in range(3):
        e.world.modify(guns[1])
        assert guns[1].sight * guns[1].level_vision == 250
        assert guns[1].vision == 625
    for lane in SHROUD_LANES:
        gun = e.body(m.role(lane).name)
        target = e.body(m.role(lane + ' target').name)
        assert gun.radius + target.radius < 40
    assert 'ENEMY_SIGHTED' not in e.unknown
    gap = e.unmodeled[sim.GAP_UPGRADE, 'LevelUpUpgrade/Unit_Heroic']['what']
    assert 'VISION/自动索敌及精确边界' in gap
    for obj in m.objects:
        b = e.body(obj.name)
        assert b.alive == (not obj.name.endswith(' near'))
        if b.alive:
            assert b.hp == b.max_hp and (b.x, b.y) == (obj.x, obj.y)
    assert not e.reveal_all and not e.reveals and not any(_clocks(b) for b in e.bodies.values())


def test_levelup_heroic_shroud_discovers_inner_target_only_without_changing_sight():
    """engine_levelshroud a:1/1/1/1 ->1/111/1/101; near controls stay visible."""
    import build
    import sim
    from checks.engine_levelup import SHROUD_LANES
    m, t, _ = build.resolve('engine_levelshroud', 'a')
    e = sim.Sim(m, t)
    e.shot_clock = True
    rows = e.run(23).series
    for label, first, op, value, last in t.expect:
        idx = [label for _, label in t.counters].index(label)
        readings = [row[idx] for at, row in rows if first <= at < last]
        assert readings and all(v == value for v in readings), (label, readings, value)
    guns = [e.body(m.role(lane).name) for lane in SHROUD_LANES]
    assert [b.level_rank for b in guns] == [1, 4, 1, 4]
    assert [b.vision for b in guns] == [500, 625, 500, 625]
    assert [b.sight for b in guns] == [200] * 4
    for obj in m.objects:
        b = e.body(obj.name)
        assert b.alive and b.hp == b.max_hp
        assert (b.x, b.y) == (obj.x, obj.y)
    assert not e.reveal_all and not e.reveals and not any(_clocks(b) for b in e.bodies.values())
    for _ in range(3):
        e.world.modify(guns[1])
        assert (guns[1].vision, guns[1].sight) == (625, 200)
    gap = e.unmodeled[sim.GAP_UPGRADE, 'LevelUpUpgrade/Unit_Heroic']['what']
    assert 'SHROUD_CLEARING' not in gap and 'VISION' in gap


def test_levelup_heroic_rate_changes_three_intershot_spans_without_scaling_each_hit():
    """engine_levelrate a: spans25/25/20/25, then HP84/80/68/80 (4/4/5/4 hits)."""
    import build
    import sim
    m, t, _ = build.resolve('engine_levelrate', 'a')
    e = sim.Sim(m, t)
    e.shot_clock = True
    rows = e.run(18).series
    for label, first, op, value, last in t.expect:
        idx = [label for _, label in t.counters].index(label)
        readings = [row[idx] for at, row in rows if first <= at <= last]
        assert readings and all(v == value for v in readings), (label, readings, value)
    guns = [e.body(m.role(lane).name) for lane in ('base', 'high', 'order', 'removed')]
    targets = [e.body(m.role(lane + ' target').name) for lane in ('base', 'high', 'order', 'removed')]
    assert [b.level_rank for b in guns] == [1, 1, 4, 3]
    assert [b.level_rate for b in guns] == [1, 1, 1.2, 1]
    assert [b.hp for b in targets] == [4200, 4000, 3437.5, 4000]
    assert [b.dealt for b in guns] == [1, 1, 1.25, 1.25]
    for obj in m.objects:
        b = e.body(obj.name)
        assert b.alive
        assert (b.x, b.y) == (obj.x, obj.y)
    gun = guns[2]
    for _ in range(3):
        e.world.modify(gun)
        assert gun.dealt == 1.25
        assert gun.level_rate == 1.2
    # Range refreshes copy the heroic weapon; copies must share its one clock.
    assert all(len(_clocks(b)) == 1 for b in guns)
    gap = e.unmodeled[sim.GAP_UPGRADE, 'LevelUpUpgrade/Unit_Heroic']['what']
    assert 'RATE_OF_FIRE' not in gap and 'VISION' in gap


def test_levelup_elite_health_persists_at_heroic_and_freezes_before_healing():
    """engine_levelhealth a: structure only (the 80/80/84/84 readings are in checks/engine_levelup.readings.toml)."""
    import build
    import sim
    m, t, _ = build.resolve('engine_levelhealth', 'a')
    e = sim.Sim(m, t)
    e.run(12)
    assert [e.body(m.role(lane).name).max_hp for lane in ('base', 'high', 'order', 'removed')] == [500, 500, 625, 625]
    heroic = e.body(m.role('removed').name)
    for upgrade in ('VETERAN', 'ELITE', 'HEROIC'):
        simmodifier.upgrade(e, heroic, 'Upgrade_CreationVeterancy_' + upgrade, True)
        e.world.modify(heroic)
    assert heroic.max_hp == 625  # held grants and modifier refresh must not stack health


def test_levelup_injured_elite_promotion_preserves_fraction_and_scales_current_health():
    """engine_levelhealth b, structure only (the 50/80/50/20 -> 30/64/34/4 readings are in
    checks/engine_levelup.readings.toml).

    Check absolute HP too: skipping the modifier also preserves percentages.
    No heroic autoheal is present in this probe.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_levelhealth', 'b')
    e = sim.Sim(m, t)
    e.run(16)
    bodies = [e.body(m.role(lane).name) for lane in ('base', 'high', 'order', 'removed')]
    assert [b.max_hp for b in bodies] == [500, 625, 625, 625]
    assert [b.hp for b in bodies] == [150, 400, 212.5, 25]
    assert (sim.GAP_UPGRADE, 'LevelUpUpgrade/injured-health') not in e.unmodeled
    for b in bodies[1:]:
        for upgrade in ('VETERAN', 'ELITE'):
            simmodifier.upgrade(e, b, 'Upgrade_CreationVeterancy_' + upgrade, True)
            e.world.modify(b)
    assert [b.max_hp for b in bodies] == [500, 625, 625, 625]
    assert [b.hp for b in bodies] == [150, 400, 212.5, 25]


def test_levelup_creation_grants_reach_heroic_only_after_three_distinct_triggers():
    """Bench 11-10 engine_levelup a: 0/0/1/0 early, 0/1/1/0 after late grants.

    A single CreationVeterancy_HEROIC adds one rank; repeated held grants add
    none. Heroic modifiers remain partial; check b covers creation remove/regrant.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_levelup', 'a')
    e = sim.Sim(m, t)
    e.run(12)                      # the 0/0/1/0 -> 0/1/1/0 readings: checks/engine_levelup.readings.toml
    assert (sim.GAP_UPGRADE, 'LevelUpUpgrade/Unit_Elite') not in e.unmodeled
    assert '创建升级触发' in '\n'.join(e.report())


def test_levelup_creation_remove_keeps_rank_and_regrant_can_trigger_twice():
    """engine_levelup b: removal keeps heroic; two veteran regrants reach heroic.

    Hold the simulator to every stable window, not just the final heroic bit.
    The one-grant control never upgrades, while the two-grant lane turns heroic
    on the first regrant and the one-grant lane only on the second regrant.
    """
    import build
    import sim
    from checks.engine_levelup import CREATION
    m, t, _ = build.resolve('engine_levelup', 'b')
    e = sim.Sim(m, t)
    e.run(28)                      # the stable-window readings: checks/engine_levelup.readings.toml
    bodies = [e.body(m.role(lane).name) for lane in ('base', 'high', 'order', 'removed')]
    assert [b.level_rank for b in bodies] == [2, 4, 4, 4]
    assert not (set(CREATION) & bodies[-1].upgrades)
    assert [b.max_hp for b in bodies] == [500, 625, 625, 625]
    assert (sim.GAP_UPGRADE, 'LevelUpUpgrade/regrant') not in e.unmodeled
    # Grants that are still held must remain idempotent after reactivation too.
    simmodifier.upgrade(e, bodies[0], CREATION[0], True)
    assert bodies[0].level_rank == 2
    for b in bodies[1:3]:
        simmodifier.upgrade(e, b, CREATION[0], True)
        assert b.level_rank == 4 and b.max_hp == 625


def test_levelup_elite_and_heroic_creation_regrants_each_need_two_reactivations():
    """engine_levelup c: 0/0/0/1 through first regrant, then 0/1/1/1.

    The two triggers are isolated; neither borrows the veteran trigger's evidence.
    Check nonempty windows before/after both removals and both regrants.
    """
    import build
    import sim
    from checks.engine_levelup import CREATION
    m, t, _ = build.resolve('engine_levelup', 'c')
    e = sim.Sim(m, t)
    e.run(28)                      # the stable-window readings: checks/engine_levelup.readings.toml
    bodies = [e.body(m.role(lane).name) for lane in ('base', 'high', 'order', 'removed')]
    assert [b.level_rank for b in bodies] == [2, 4, 4, 4]
    assert [b.max_hp for b in bodies] == [500, 625, 625, 625]
    assert [set(CREATION) & b.upgrades for b in bodies] == [
        {CREATION[0]}, {CREATION[1]}, {CREATION[2]}, set()]
    for b, up in zip(bodies[:3], CREATION):
        simmodifier.upgrade(e, b, up, True)
        e.world.modify(b)
    assert [b.level_rank for b in bodies] == [2, 4, 4, 4]
    assert [b.max_hp for b in bodies] == [500, 625, 625, 625]


def test_levelup_heroic_range_reaches_only_the_inner_target_without_moving():
    """engine_levelrange a: 100/10100/100/10100 -> 100/10017/100/10100.

    The heroic weapon alone is 150, insufficient at 220 centre distance;
    RANGE125% makes it 187.5. No kill, movement, XP or repeated range stacking.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_levelrange', 'a')
    e = sim.Sim(m, t)
    e.shot_clock = True
    rows = e.run(14).series
    for first, last, expected in ((2, 4, (100, 10100, 100, 10100)),
                                  (10, 14, (100, 10017, 100, 10100))):
        window = [tuple(row) for sec, row in rows if first <= sec <= last]
        assert window and all(row == expected for row in window), window
    guns = [e.body(m.role(lane).name) for lane in ('base', 'high', 'order', 'removed')]
    assert [b.level_rank for b in guns] == [1, 4, 1, 4]
    assert [b.weapons[0]['range'] for b in guns] == [125, 187.5, 125, 187.5]
    for obj in m.objects:
        b = e.body(obj.name)
        assert b.alive and (b.x, b.y) == (obj.x, obj.y)
    gun, target = guns[1], e.body(m.role('high target').name)
    assert not e.in_range(gun, target, dict(gun.weapons[0], range=150))
    assert e.in_range(gun, target, gun.weapons[0])
    assert target.hp == 67.5  # one 250 * DAMAGE_MULT125 hit, no XP from a kill
    for _ in range(3):
        e.world.modify(gun)
        assert gun.weapons[0]['range'] == 187.5
    gap = e.unmodeled[sim.GAP_UPGRADE, 'LevelUpUpgrade/Unit_Heroic']['what']
    assert 'RANGE' not in gap and 'RATE_OF_FIRE' not in gap and 'VISION' in gap


def test_levelup_veteran_damage_persists_at_elite_and_heroic_without_gated_target_healing():
    """Bench 11-10 engine_leveldamage a: 47/34/34/17 through s15.

    Level DAMAGE_MULT125 persists at elite and heroic. Heroic uses its 250 gun;
    Its measured RATE_OF_FIRE modifier must not enlarge this single hit.
    The Tsunami's state-gated heal stays off with no GENERIC_TOGGLE_STATE.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_leveldamage', 'a')
    e = sim.Sim(m, t)
    e.shot_clock = True
    rows = e.run(14).series
    assert tuple(rows[-1][1]) == (47, 34, 34, 17)
    assert all(tuple(row) == (47, 34, 34, 17) for sec, row in rows if sec >= 10)
    assert 'RATE_OF_FIRE' not in e.unmodeled[sim.GAP_UPGRADE, 'LevelUpUpgrade/Unit_Heroic']['what']


def test_a_mission_file_holding_two_game_objects_gives_each_its_own_crush_levels():
    import build
    import engine.data.units as simunits
    from engine.modules import crush
    m, _, _ = build.resolve('engine_dynamics', 'a')
    own = {u.id: u.xml for u in m.units}

    def levels(template):           # as the CrusherInfo module reads them (step M3)
        d = crush.CrushData.parse(*simunits.module_blocks(template, 'CrusherInfo', own)[0])
        return d.crusher, d.crushable
    assert levels('CNVHammerNoDyn') == (20, 20)        # its own CrusherInfo, not its base copy's 10
    assert levels('CNVBaseVehicleNoDyn') == (10, 20)   # the base copy, found inside the unit's file


def test_topple_the_legacy_loop_still_drives_through_and_removes_the_props():
    import build
    import sim
    m, t, _ = build.resolve('engine_topple', 'a')
    s = sim.Sim(m, t, model=False).run(50.0)
    _, *rows = s.series[-1][1]
    assert all(row // 1000000 > 0 and row // 1000 % 1000 == 0 for row in rows), rows
    assert all(not s.body(f'UNIT - CNV Topple Prop {k}').alive for k in range(1, 4))


# PREDICTED only: the retail dummy's 100 HP, 200 script damage, 1 HP floor.
# KILL is MaxHealth damage in the reference; DELETE bypasses the body.
def test_immortal_damage_stops_at_one_hp_kill_is_damage_and_delete_removes():
    import build
    import sim
    for lane in 'ab':
        m, t, _ = build.resolve('engine_immortal', lane)
        s = sim.Sim(m, t)
        readings = []
        for half in range(29):
            s.run(half * 0.5)
            readings.append([s.counters.get(c, 0) for c, _ in t.counters])
            dummy = s.body('UNIT - CNV Immortal Dummy')
            if 2 <= half < 24 or lane == 'a':
                assert dummy.max_hp == 100 and dummy.alive
                assert dummy.hp == (100 if half < 2 else 1)
        assert readings[:2] == [[100, 0]] * 2, readings
        # 1..11.5 s: ten seconds after damage, then KILL at 11 s still leaves 1 HP.
        assert readings[2:24] == [[1, 0]] * 22, readings
        if lane == 'a':
            assert readings[24:] == [[1, 0]] * 5, readings
        else:
            assert not dummy.alive and dummy.deleted
            assert readings[24:] == [[1, 1]] * 5, readings      # bench 11-09: DELETE leaves the counter at 1


def test_suppression_predictions():
    """Guard finite probe inputs and compare the model against the suppression bench."""
    import build
    from checks import engine_clip, engine_suppression
    import sim
    import engine.data.units as simunits
    from parts import contract, merged
    import struct
    import package
    import make_campnew18 as c18
    import mapxml
    import xml.etree.ElementTree as ET
    from mapscript import MapFile
    # Exercise the real pre-BinaryAssetBuilder map writer, not Sim's permissive
    # conversion of Python ints to seconds/percentages.
    _, source = next((p, d) for p, d in c18.c6._map_files() if p.lower().endswith('.map'))
    expected = {'threshold': [44, 59, 59, 59], 'expiry': [44, 44, 59, 59], 'speed': [44, 59],
                'armor': [73, 1, 73, 1], 'armored': [73, 1, 80, 1],
                'phasea': [44, 44], 'phaseb': [44, 44], 'lifetime': [44, 59], 'edge': [59, 59],
                'fraction': [59, 59], 'fast': [37, 37], 'tail': [56, 56],
                'duration': [44, 45, 44, 45], 'immune': [44, 40]}
    for lane, readings in expected.items():
        m, t, mod = build.resolve('engine_suppression', lane)
        assert len(mod) <= 15 and mod.isalnum()
        assert not contract(merged(m, t))
        built = MapFile(source)
        package.write_map(built, merged(m, t))
        objects = mapxml.objects(built)
        placed = {o['props'].get('objectName') for o in objects}
        named = {o['props'].get('objectName'): o for o in objects}
        waypoints = {o['props'].get('waypointName'): (o['x'], o['y']) for o in objects
                     if o['template'] == '*Waypoints/Waypoint'}
        # Exercise what the engine receives: ownership, legal V4 distance,
        # emitted trigger polygons and the exact waypoint/area references.
        assert built.trigger_areas() == t.areas
        for k in ('base', 'high', 'order', 'removed', 'low'):
            man = named[f'UNIT - CNV Supp {k} man']
            assert man['props']['originalOwner'] == m.team('s1')
            for part in ('gun', 'armor') + (('second',) if k in ('base', 'high') else ()):
                shooter = named[f'UNIT - CNV Supp {k} {part}']
                assert shooter['props']['originalOwner'] == m.team('p1')
                assert shooter['props']['originalOwner'] != man['props']['originalOwner']
                assert abs(shooter['angle'] - 1.5708) < .00001
                unit = next(u for u in m.units if u.id == shooter['template'])
                weapon = next(e for e in ET.fromstring(unit.xml).iter()
                              if e.tag.rsplit('}', 1)[-1] == 'WeaponTemplate')
                distance = ((shooter['x'] - man['x']) ** 2 + (shooter['y'] - man['y']) ** 2) ** .5
                assert man['y'] - shooter['y'] == 450
                assert float(weapon.attrib['MinimumAttackRange']) <= distance <= float(weapon.attrib['AttackRange'])
        for script in t.scripts:
            for action, *args in script.do:
                if action == 'MOVE_NAMED_UNIT_TO':
                    assert args[1] in waypoints
                    k = args[0].split()[-2]
                    leg = 'late' if 'late' in script.name else 'goal'
                    assert waypoints[args[1]] == m.point(k + ' ' + leg + ' runout')
            for action, *args in script.when:
                if action == 'NAMED_INSIDE_AREA':
                    points = built.trigger_areas()[args[1]]
                    k = args[0].split()[-2]
                    leg = 'late' if 'late' in script.name else 'goal'
                    x, y = m.point(k + ' ' + leg)
                    delta = -1 if lane == 'edge' else 0
                    assert points == [(x - 40, y - 5 + delta), (x + 40, y - 5 + delta),
                                      (x + 40, y + 75 + delta), (x - 40, y + 75 + delta)]
        revealed = []
        for _, node in built.walk():
            if node.name not in ('Condition', 'ScriptAction'):
                continue
            action, args, _ = built.content(node)
            if action == 'MAP_REVEAL_ALL_PERM':
                revealed.append(args[0][1])
            for kind, value in args:
                if kind == 14:               # named-object parameter, as written to the map
                    assert value in placed, (lane, action, value)
            if action in ('SET_MILLISECOND_TIMER', 'UNIT_SET_HEALTH'):
                assert type(args[1][1]) is float, (lane, action, args)
                # Decode raw argument slots too: the game consumes the real slot.
                first_string = len(args[0][1].encode('latin-1'))
                arg2 = 12 + 14 + first_string
                _, integer, real = struct.unpack_from('<Iif', node.head, arg2)
                assert integer == 0 and real == args[1][1] > 0
        assert revealed == [m.player('p1')]
        # The actual pre-BAB object-data list, not only permissive Sim bodies.
        spec = package.spec_of(m, t, name=mod)
        files = dict(spec.unit_files)
        xml, unknown = mapxml.map_xml(built, c18.c7.GAME_MAP_ID, spec.templates, also=spec.extra_all)
        root = ET.fromstring(xml)
        ns = {'a': 'uri:ea.com:eala:asset'}
        includes = {e.attrib['source'] for e in root.findall('a:Includes/a:Include', ns)}
        emitted = {e.attrib['ThingTemplate'] for e in root.findall('.//a:Unit', ns)}
        assert unknown == ['*Waypoints/Waypoint']
        for u in m.units:
            assert 'DATA:CNVUnits/Data/' + u.id + '.xml' in includes
            assert u.id in emitted and ('GameObject:' + u.id).encode() in spec.extra_own
            unit = ET.fromstring(files[u.id + '.xml'])
            obj = unit.find('a:GameObject', ns)
            if u.id == 'CNV_SuppFastMan':
                assert lane == 'fast' and simunits.stats(u.id, {u.id: u.xml})['speed'] == 80
                continue
            weapon = unit.find('a:WeaponTemplate', ns)
            assert obj.attrib['id'] == u.id
            assert obj.find('.//a:Weapon', ns).attrib['Template'] == weapon.attrib['id']
            assert ('WeaponTemplate:' + weapon.attrib['id']).encode() in spec.extra_own
            nuggets = weapon.findall('a:Nuggets', ns)
            assert len(nuggets) == 1 and len(nuggets[0].findall('a:DamageNugget', ns)) == 1
            damage = nuggets[0].find('a:DamageNugget', ns)
            assert damage.attrib['DamageType'] == ('EXPLOSIVE' if lane == 'armored' and u.id.endswith('Armor')
                                                    else 'UNRESISTABLE')
            pressure = nuggets[0].findall('a:SuppressionNugget', ns)
            assert len(pressure) == (0 if u.id.endswith('Armor') else 1)
            k = next(k for k in ('base', 'high', 'order', 'removed', 'low') if u.id.startswith('CNV_Supp' + k.title()))
            if pressure:
                _, value, duration = engine_suppression.cases_for(lane)[k]
                assert pressure[0].attrib == dict(Radius='20', Suppression=str(value), DurationSeconds=f'{duration}s')
        # Main guns belong on the actual named pads, not 350 south of them.
        for k in ('base', 'high', 'order', 'removed', 'low'):
            o = named[f'UNIT - CNV Supp {k} gun']
            assert (o['x'], o['y']) == m.site(k + ' gun')
        assert len(t.counters) == len(readings) <= 4
        assert [e[3] for e in t.expect] == readings
        assert all(e[1:3] == (21, '==') and e[4] == 23 for e in t.expect)
        assert all(ok for ok, _ in build.judge(t, [(21, readings), (22, readings)]))
        actions = [a for script in t.scripts for a in script.do]
        assert not any(a[0] in ('HIDE_COUNTER', 'DISPLAY_COUNTER') or
                       any(isinstance(v, str) and '_GUNS' in v for v in a) for a in actions)
        assert t.bench[0][1] == dict(seconds=23, every=.5, sheet=False, lines=len(readings))
        # Match clip's hold/release/order/flag sequence and its absolute order time.
        start = next(script for script in t.scripts if script.name == 'Test - start')
        timers = {a[1]: a[2] for a in start.do if a[0] == 'SET_MILLISECOND_TIMER'}
        fire_at = engine_clip.ORDER + {'phasea': 1 / 3, 'phaseb': 2 / 3}.get(lane, 0)
        assert {k: v for k, v in timers.items() if not k.startswith('Supp Stop ')} == {'Supp Fire': fire_at, 'Supp Move': 12.0 if lane == 'tail' else 10.0 if lane == 'duration' else 9.0,
                          'Supp Late': 17.0, 'Supp Armor': 11.0}
        fire = next(script for script in t.scripts if script.name == 'Test - fire')
        assert fire.when == [('TIMER_EXPIRED', 'Supp Fire')]
        assert fire.do[-1] == ('SET_FLAG', 'Supp Ordered', 1)
        for release, attack in zip(fire.do[:-1:2], fire.do[1:-1:2]):
            assert release == ('UNIT_CHANGE_OBJECT_STATUS', attack[1], 'NO_ATTACK', 0)
            assert attack[0] == 'NAMED_ATTACK_NAMED'
            assert ('UNIT_CHANGE_OBJECT_STATUS', attack[1], 'NO_ATTACK', 1) in start.do
            assert ('UNIT_CHANGE_OBJECT_STATUS', attack[2], 'NO_ATTACK', 1) in start.do
            gun_lane, part = attack[1].split()[-2:]
            uid = 'CNV_Supp' + gun_lane.title() + ('Second' if part == 'second' else '')
            unit = next(u for u in m.units if u.id == uid)
            hits = unit.params['clip']
            assert unit.params['reload'] == 1.0 < engine_clip.ORDER
            stop_at = timers['Supp Stop ' + gun_lane + part]
            assert stop_at == fire_at + (2 * hits + 2) / 15
            assert fire_at + 2 * hits / 15 < stop_at < fire_at + (2 * hits + 15) / 15
            assert any(script.do == [('UNIT_CHANGE_OBJECT_STATUS', attack[1], 'NO_ATTACK', 1)]
                       and script.when == [('TIMER_EXPIRED', 'Supp Stop ' + gun_lane + part)]
                       for script in t.scripts)
        if lane in ('armor', 'armored'):
            assert timers['Supp Stop armor order'] == timers['Supp Stop armor high'] == 11.0 + 4 / 15
        else:
            # Health evidence shares the goal line only before movement starts.
            for script in t.scripts:
                if script.name.startswith('Test - burst health '):
                    assert not script.once and script.when[0][0] == 'FLAG'
                    counter = script.do[0][2]
                    assert any(('SET_COUNTER', counter, 0) in move.do and
                               ('SET_FLAG', script.when[0][1], 1) in move.do for move in t.scripts)
        # The previous never-ending frame counters / zero armor readings must fail.
        bad = [0] * len(readings) if lane in ('armor', 'armored') else [287] * len(readings)
        assert not any(ok for ok, _ in build.judge(t, [(22, bad)]))
        s = sim.Sim(m, t)
        s.shot_clock = True                  # finite probe bursts, never change the shared default
        ordinary = s.body('UNIT - CNV Supp removed man')
        assert ordinary.max_hp == 150 and ordinary.speed == 50
        assert ordinary.suppression_rule == dict(threshold=50, every=15, duration=75,
                                                modifier='Modifier_Test_Suppression')
        assert simunits.module_blocks('AlliedCommandoTech1', 'SuppressionUpdate') == []   # its Remove block
        s.run(9)
        assert s.enemy(m.player('p1'), m.player('s1')) and s.enemy(m.player('s1'), m.player('p1'))
        assert 'SUPPRESSED' not in ordinary.status   # model condition is not an object status
        s.run(engine_suppression.RUN)
        # Exact model/bench matches only where expiry and fractional entry do
        # not intervene. The other expectations record the ENGINE, not Sim.
        if lane in ('armor', 'armored', 'immune', 'fast'):
            assert s.series[-1][1] == readings, (lane, s.series[-1][1], readings)
        assert ordinary.alive and ordinary.speed == 50 and ordinary.taken == 1
        assert not ordinary.suppression_hits
        if lane == 'immune':
            immune = s.body('UNIT - CNV Supp low man')
            assert immune.suppressed_until == -1 and immune.speed == 55
        assert s.eng is not None
    # Isolate the threshold and modifier; entering does not set the end frame.
    m, t, _ = build.resolve('engine_suppression', 'threshold')
    s = sim.Sim(m, t)
    b = s.body('UNIT - CNV Supp high man')
    from engine.kernel import interfaces
    mod = b.find(interfaces.Suppression)        # step M6: engine/modules/suppression.py
    for points, suppressed in ((48, False), (50, True)):
        s.suppression_fields = [(1000, points, b.x, b.y, 20)]
        mod.suppression_next = 0
        mod.suppressed = False
        mod.suppressed_until = 0
        mod.update(s.frame_now())
        assert b.suppressed is suppressed
        assert b.suppressed_until == 0
        assert b.speed == (37.5 if suppressed else 50)
        assert b.taken == (.75 if suppressed else 1)


def test_suppression_contributions_require_discrete_hit_events():
    """Continuous DPS must not invent suppression hits on a second weapon clock."""
    import build
    import sim
    for clock in (False, True):
        m, t, _ = build.resolve('engine_suppression', 'threshold')
        s = sim.Sim(m, t)
        s.shot_clock = clock
        s.run(9)
        high = s.body('UNIT - CNV Supp high man')
        assert bool(high.suppression_hits) is clock
        assert high.speed == (37.5 if clock else 50)
        assert high.taken == (.75 if clock else 1)
        assert ((sim.GAP_WEAPON, 'SuppressionNugget') in s.unmodeled) is not clock


def test_suppression_samples_entry_refresh_and_expiry_at_the_four_probe_readings():
    """D's read-only engine_suppress_probe wraps engine_suppression unchanged.

    Replay the named probe without its injected read-only logging carrier. Bench
    2026-11-10: tail, lifetime, duration, expiry all PASS (D rounds 21/22).
    """
    import build
    import sim
    import re
    # Exact module state/end readings from the four runs. Final walking
    # counters remain in engine_suppression: retail's lateral path drift is
    # absent from the simulator, giving one frame less on suppressed legs.
    expected={
        'tail': {'base':{121:(True,0),136:(True,211),211:(True,211),226:(False,211)}},
        'lifetime': {'order':{106:(True,0),121:(False,0)},
                     'removed':{106:(True,0),121:(True,196),196:(True,196),211:(False,196)}},
        'duration': {'order':{106:(True,0),121:(False,0)},
                     'removed':{106:(True,0),121:(False,0)}},
        'expiry': {'base':{106:(False,0),136:(False,0),226:(False,0)},
                   'high':{106:(False,0),136:(False,0),226:(False,0)},
                   'order':{106:(True,0),121:(True,196),136:(True,211),211:(True,211),226:(False,211)},
                   'removed':{106:(True,0),121:(True,196),136:(True,211),211:(True,211),226:(False,211)}}}
    for check, lanes in expected.items():
        m,t,_=build.resolve('engine_suppress_probe',check)
        # In the game ra3ext replaces this DeletionUpdate carrier with its
        # read-only logger. The replay needs neither deletion nor injected I/O;
        # keep all other target XML, placements and scripts from the real probe.
        probe=next(u for u in m.units if u.id=='CNV_SuppProbeMan')
        probe.xml,n=re.subn(r'<DeletionUpdate\b(?=[^>]*id="ModuleTag_CNVProbe")[^>]*/>', '', probe.xml)
        assert n==1
        e=sim.Sim(m,t);e.shot_clock=True
        got={lane:{} for lane in lanes}
        tick=e.suppression_tick
        def observe():
            tick()
            for lane, frames in lanes.items():
                if e.frame_now() in frames:
                    b=e.body('UNIT - CNV Supp '+lane+' man')
                    got[lane][e.frame_now()]=(b.suppressed,b.suppressed_until)
        e.suppression_tick=observe
        e.run(23)
        assert got==lanes, (check,got,lanes)
        if check=='duration':
            assert tuple(e.series[-1][1])==(44,45,44,45)


def test_weaponfx_predictions_and_finite_bursts():
    """Round1: attribute/line bench PASS."""
    import build
    import sim
    for variant, expected in [('attribute', (79,1,74,1)),
                              ('line', (90,90,90,100))]:
        m,t,_=build.resolve('engine_weaponfx',variant)
        assert len(t.counters)==4
        timers={a[1]:a[2] for s in t.scripts for a in s.do if a[0]=='SET_MILLISECOND_TIMER'}
        assert all(isinstance(v,float) for v in timers.values())
        for key,at in timers.items():
            if key.startswith('Wfx Fire '):
                assert at>=6.0
                assert abs(timers[key.replace('Fire','Stop')]-at-4/15)<1e-9
        for u in m.units:
            if 'CNV_Wfx' in u.id:
                assert 'MinSeconds="1s"' in u.xml and 'ClipSize="1"' in u.xml
        engine=sim.Sim(m,t); engine.shot_clock=True
        result=engine.run(16.0)
        readings=result.series[-1][1]
        assert tuple(readings)==expected,(variant,readings)
        if variant=='attribute':
            assert (89,1,84,1) in [tuple(row) for _,row in result.series]


def test_strip_max_health_percent_uses_maximum_at_full_and_half_health():
    import build
    import sim
    m,t,_=build.resolve('engine_strip','exact')
    engine=sim.Sim(m,t);engine.shot_clock=True
    assert tuple(engine.run(16).series[-1][1])==(100095,100045,100074,3)


def test_weapon_first_hit_is_observed_one_frame_after_the_order_script():
    import build
    import sim
    m,t,_=build.resolve('engine_emp','phase')
    engine=sim.Sim(m,t);engine.shot_clock=True
    assert tuple(engine.run(16).series[-1][1])==(16051,31066,61096,1)


# ---- FireWeaponWhenDead (engine/modules/fireweaponwhendead.py; Sim.destroy / death_blast_due): bench 2026-11-05 engine_spawn_refill
# (checks/engine_spawn.py, docs/engine/spawn.md 5). Two S02_ExplodingMig (1000 GRENADE, radius 100, .3 s) killed by
# script, at 8 s and 11 s, each beside a Guardian at 20 % health 57 off its centre: each Guardian dies with its mig and
# its health counter freezes there; the keep factory (its edge > 100 from either) stands.
def test_fire_weapon_when_dead_a_scripted_kill_blows_the_mig_and_the_guardian_beside_it():
    import build
    import sim
    m, t, _ = build.resolve('engine_spawn_refill', 'refill')
    s = sim.Sim(m, t).run(32.0)
    north, west = s.body('UNIT - CNV Refill North'), s.body('UNIT - CNV Refill West')
    assert not north.alive and not west.alive, (north.hp, west.hp)
    assert 8.0 <= north.died_at <= 9.0 and 11.0 - 1.0 <= west.died_at <= 11.5, (north.died_at, west.died_at)
    assert s.body('UNIT - CNV Refill Keep').alive
    by = [row[1][1] for row in s.series]                       # 车旁: hundreds / thousands = the north / west mig
    assert by[3] == 1100 and by[-1] == 3300, by                # bench: both gone by s11, as here


def test_weapon_bench_register_points_to_replayed_engine_probes():
    import inspect
    import inventory
    pairs={'ProjectileNugget':('test_projectile_nugget_flight_uses_retail_shell_speed_and_resolved_warhead','engine_projectile'),
           'AttributeModifierNugget':('test_weaponfx_predictions_and_finite_bursts','engine_weaponfx'),
           'LineDamageNugget':('test_weaponfx_predictions_and_finite_bursts','engine_weaponfx'),
           'ParalyzeNugget':('test_weapon_first_hit_is_observed_one_frame_after_the_order_script','engine_emp'),
           'StripMaxHealthPercentNugget':('test_strip_max_health_percent_uses_maximum_at_full_and_half_health','engine_strip')}
    for name,(test,probe) in pairs.items():
        assert inventory.BENCHED_TESTS[inventory.NUGGET,name].endswith('::'+test)
        assert probe in inspect.getsource(globals()[test])
        assert 'checks/'+probe+'.py' in inventory.tested_probes()
    for form, test, probe in (
            ('默认系数目标通知', 'test_inform_incoming_table_drives_miner_armor_from_engine_inform_probe',
             'engine_inform_probe'),
            ('Max1.6目标通知', 'test_inform_max_launch_matches_engine_inform_max_observed_deadline',
             'engine_inform_max')):
        assert inventory.BENCHED_TESTS[inventory.NUGGET, 'InformTargetNugget:' + form] == (
            'tests/test_inform_ai.py::' + test)
        assert 'checks/' + probe + '.py' in inventory.tested_probes()


def test_projectile_nugget_flight_uses_retail_shell_speed_and_resolved_warhead():
    import build
    import sim
    import engine.data.units as simunits
    assert any(w.get('projectile')=='SovietAntiVehicleVehicleTech1TankProjectile'
               for w in simunits.weapon_table().values())
    m,t,_=build.resolve('engine_projectile','flight')
    e=sim.Sim(m,t);e.shot_clock=True
    assert tuple(e.run(16).series[-1][1])==(7,95,11,95)


def test_activate_laser_uses_separate_damage_nugget_without_delaying_the_hit():
    import inventory
    assert inventory.NOTES[inventory.NUGGET,'ActivateLaserNugget'][0]==inventory.NA
    assert inventory.NOTES[inventory.MODULE,'Behaviors/LaserState'][0]==inventory.NA
    import build
    import sim
    m,t,_=build.resolve('engine_laser','pair')
    e=sim.Sim(m,t);e.shot_clock=True
    assert tuple(e.run(16).series[-1][1])==(2,90,2,90)
    assert all('LaserStateID="201"' in u.xml and 'LaserId="201"' in u.xml
               for u in m.units if u.id.startswith('CNV_Laser'))


def test_tint_changes_no_health_or_hit_timing_beyond_the_separate_damage_nugget():
    import inventory
    assert inventory.NOTES[inventory.NUGGET,'TintObjectsNugget'][0]==inventory.NA
    import build
    import sim
    m,t,_=build.resolve('engine_tint','pair')
    e=sim.Sim(m,t);e.shot_clock=True
    assert tuple(e.run(16).series[-1][1])==(2,90,2,90)
    assert 'TintObjectsNugget' in next(u.xml for u in m.units if u.id=='CNV_LaserHigh')


def test_damage_contained_limits_eligible_passengers_without_damaging_the_others():
    import build
    import sim
    m,t,_=build.resolve('engine_contained','a')
    e=sim.Sim(m,t);e.shot_clock=True
    for lane in ('base','high','order','removed'):
        assert e.body('Contained '+lane+' gun').y>=0
    assert tuple(e.run(16).series[-1][1])==(992002200,992002180,992002160,992002200)


def test_emp_blocks_an_ordered_shot_and_allows_a_new_shot_after_expiry():
    import build
    import sim
    m,t,_=build.resolve('engine_empfire','a')
    e=sim.Sim(m,t);e.shot_clock=True
    assert all('Armor="NoArmor"' in u.xml for u in m.units if
               u.id.startswith(('CNV_EmpFireGun','CNV_EmpFireTarget')))
    assert tuple(e.run(16).series[-1][1])==(901090,901100,901080,901090)


def test_special_power_nugget_dispatches_the_casters_self_modifier_only_with_module_and_eligible_target():
    import build
    import sim
    import engine.data.units as simunits
    retail=simunits._fight_data()['weapons']['JapanLightTransportVehicleDisguiser']
    assert retail['special_powers'][0]['power']=='SpecialPower_JapanLightTransportVehicleDisguise'
    m,t,_=build.resolve('engine_spn','a')
    e=sim.Sim(m,t);e.shot_clock=True
    assert tuple(e.run(16).series[-1][1])==(1001099080,1001099075,1001099080,1001099080)


def test_attach_nugget_sets_parent_child_status_and_follows_the_moving_parent():
    import build
    import sim
    import engine.data.units as simunits
    retail=simunits._fight_data()['weapons']['JapanScoutInfantryAttachWeaponWarhead']
    assert retail['attach'][0]['module']=='ModuleTag_Attach'
    m,t,_=build.resolve('engine_attach','a')
    e=sim.Sim(m,t);e.shot_clock=True
    assert tuple(e.run(20).series[-1][1])==(1000001099,1001111099,1000001099,1000001099)


def test_attach_parent_death_clears_simple_link_and_preserves_the_child():
    """engine_attach_parent a: simple live/kill controls; see work/re/c_attach_parent_report.md."""
    import build
    import sim
    m,t,_=build.resolve('engine_attach_parent','a')
    e=sim.Sim(m,t);e.shot_clock=True
    rows=e.run(18).series
    # NO_COLLISIONS (before64/late1) differs; the complete reading is held
    # separately below. Every other independently read bit matches the bench.
    assert tuple(v & ~65 for v in rows[-1][1][:2])==(958,928)
    assert all(tuple(v & ~65 for v in row[:2])==(958,928) for sec,row in rows if sec>=16)
    child,parent=e.body('Attach high child'),e.body('Attach high parent')
    assert child.alive and not parent.alive
    assert not child.status & {'ATTACHED','NON_AUTOACQUIRABLE','NO_COLLISIONS'}
    assert e.bodies['Attach high child'].serial not in e.attachments


def test_attach_child_death_clears_the_surviving_parents_status():
    """engine_attach_child a: live127/killed124; see work/re/c_attach_child_report.md."""
    import build
    import sim
    m,t,_=build.resolve('engine_attach_child','a')
    e=sim.Sim(m,t);e.shot_clock=True
    rows=e.run(18).series
    assert tuple(rows[-1][1])==(127,124)
    assert all(tuple(row)==(127,124) for sec,row in rows if sec>=16)
    assert all(tuple(row)==(120,120) for sec,row in rows if 9<=sec<10)
    child,parent=e.body('Attach high child'),e.body('Attach high parent')
    assert not child.alive and parent.alive
    assert 'VEHICLE_ATTACHED' not in parent.status
    assert 'VEHICLE_ATTACHED' in e.body('Attach base parent').status
    assert set(e.attachments)=={e.bodies['Attach base child'].serial}
    assert (sim.GAP_WEAPON,'AttachNugget') not in e.unmodeled


def test_attach_child_delete_clears_the_surviving_parents_status():
    """engine_attach_child_delete a: live127/deleted124; work/re/c_attach_delete_report.md."""
    import build
    import sim
    m,t,_=build.resolve('engine_attach_child_delete','a')
    e=sim.Sim(m,t);e.shot_clock=True
    rows=e.run(18).series
    assert tuple(rows[-1][1])==(127,124)
    assert all(tuple(row)==(127,124) for sec,row in rows if sec>=16)
    assert all(tuple(row)==(120,120) for sec,row in rows if 9<=sec<10)
    child,parent=e.body('Attach high child'),e.body('Attach high parent')
    assert child.deleted and not child.alive and parent.alive
    assert 'VEHICLE_ATTACHED' not in parent.status
    assert 'VEHICLE_ATTACHED' in e.body('Attach base parent').status
    assert set(e.attachments)=={e.bodies['Attach base child'].serial}
    assert (sim.GAP_WEAPON,'AttachNugget') not in e.unmodeled


def test_attach_parent_delete_clears_the_surviving_childs_status():
    """engine_attach_parent_delete a: live3871/deleted3856; work/re/c_attach_parent_delete_report.md."""
    import build
    import sim
    m,t,_=build.resolve('engine_attach_parent_delete','a')
    e=sim.Sim(m,t);e.shot_clock=True
    rows=e.run(18).series
    assert tuple(rows[-1][1])==(3871,3856)
    assert all(tuple(row)==(3871,3856) for sec,row in rows if sec>=16)
    assert all(tuple(row)==(3840,3840) for sec,row in rows if 9<=sec<10)
    child,parent=e.body('Attach high child'),e.body('Attach high parent')
    assert child.alive and parent.deleted and not parent.alive
    assert not child.status & {'ATTACHED','ENCLOSED','UNATTACKABLE'}
    assert e.body('Attach base child').status >= {'ATTACHED','ENCLOSED','UNATTACKABLE'}
    assert set(e.attachments)=={e.bodies['Attach base child'].serial}
    assert (sim.GAP_WEAPON,'AttachNugget') not in e.unmodeled


def test_attach_probe_rejects_an_unpublished_module_before_building():
    from types import SimpleNamespace
    import pytest
    from checks.engine_attach import _module_contract
    bad=SimpleNamespace(id='bad',xml='<AssetDeclaration><AttachNugget AttachModuleId="Missing"/></AssetDeclaration>')
    with pytest.raises(ValueError,match='unpublished AttachModuleId'):
        _module_contract(bad)


def test_attach_child_is_not_crushed_by_the_parent_it_travels_with():
    """A linked child has no independent collision along its carrier's path."""
    import build
    import sim
    m,t,_=build.resolve('engine_attach','a')
    e=sim.Sim(m,t);e.shot_clock=True
    from engine.kernel import interfaces
    from engine.modules import crush
    child=e.body('Attach high child');parent=e.body('Attach high parent')

    def levels(b, crusher, crushable):      # its CrusherInfo module swapped for one with these levels (step M3)
        b.modules=tuple(m for m in b.modules if not isinstance(m,interfaces.Crush))+(
            crush.Crush(b,crush.CrushData(crusher,crushable).seal(),e.world),)
    levels(child,child.crusher,0);levels(parent,100,parent.crushable)
    assert child.crushable==0 and parent.crusher==100
    e.run(20)
    assert child.alive and child.status >= {'ATTACHED','ENCLOSED','UNATTACKABLE'}


@pytest.mark.xfail(strict=True,raises=AssertionError,
                   reason='Flagged direct dispatch attaches transiently before8s; two-run gate, cause unresolved')
def test_attach_move_flag_transient_link_matches_engine_attach_detach_observation():
    """Observed engine_attach_detach a; never treat the rejected16s-detach prediction as truth."""
    import build
    import sim
    m,t,_=build.resolve('engine_attach_detach','a')
    e=sim.Sim(m,t);e.shot_clock=True
    rows=e.run(28).series
    expected=(1133111099,1122000199,1122000099,1100000200)
    assert all(tuple(row)==expected for sec,row in rows if sec>=26)
    assert tuple(rows[-1][1])==expected
    assert set(e.attachments)=={e.bodies['Attach base child'].serial}
    child,parent=e.body('Attach high child'),e.body('Attach high parent')
    assert child.alive and parent.alive
    assert not child.status & {'ATTACHED','NON_AUTOACQUIRABLE','NO_COLLISIONS'}
    assert 'VEHICLE_ATTACHED' not in parent.status
