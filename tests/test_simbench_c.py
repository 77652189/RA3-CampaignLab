"""Engine line C's simulator-vs-bench tests (object modules, weapon effects): each takes a reading the bench made and holds
the simulator to it, so a module can be registered in inventory.BENCHED_TESTS against it. A separate file from
test_simbench.py so line C's hunks never share a file with another line's uncommitted ones."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# loaded by file: simbench.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
_spec = importlib.util.spec_from_file_location('simbench_c', ROOT / 'experimental' / 'cnv' / 'simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)


def _sim_run(build_name, check, until):
    import build
    import sim
    m, t, _ = build.resolve(build_name, check)
    return sim.Sim(m, t).run(until)


# ---- RunOffMapBehavior (sim.Sim.flee_start / flee_due; simunits.run_off_map): bench 2026-11-06 engine_runoffmap
# (checks/engine_runoffmap.py, docs/engine/runoffmap.md): the peacekeeper runs to the waypoint `RunOffMap` (a, 200 off)
# or 1000 along its facing (b), is gone 3 frames after it arrives and was never dying; a structure does not run (c);
# NAMED_STOP at frame 15 leaves him standing with the status on (d). 逃帧 = frames not removed + 1000 x frames fleeing.
def test_run_off_map_the_peacekeeper_is_gone_64_and_304_frames_after_the_order_never_dying():
    a = _sim_run('engine_runoffmap', 'a', 20.0).series[-1][1]
    b = _sim_run('engine_runoffmap', 'b', 50.0).series[-1][1]
    assert (a[1], a[3]) == (64064, 15) and (b[1], b[3]) == (304304, 15), (a, b)
    assert a[2] == a[0] - 64 and b[2] == b[0] - 304, (a, b)         # 死法 = removed frames (+ 1000 x dying: none)


def test_run_off_map_a_structure_stays_and_a_stop_takes_the_run_over_with_the_status_left_on():
    c = _sim_run('engine_runoffmap', 'c', 20.0).series[-1][1]
    d = _sim_run('engine_runoffmap', 'd', 20.0).series[-1][1]
    assert c[1] == c[0] and c[2] == 0 and c[3] == 64064, c           # the plant: there all along, never fleeing
    assert d[1] == 1000 * d[0] + d[0] and d[2] == 0 and d[3] == 0, d     # stopped at 15: still there, still fleeing


# ---- InvisibilityBroadcastUpdate (sim.Sim.cloaked; simunits.invis_broadcast): bench 2026-11-05 engine_stealth a / b
# (checks/engine_stealth.py, docs/engine/stealth.md 1-2, 4). A mirage tank carrying GENERIC_TOGGLE_STATE (a script gives
# it) hides the friendly infantry / vehicles within 175; its enemy cannot pick them, the attack order stays and fires
# the moment the aura goes off. The series is read in percent at each second (the bench's seconds run ahead of the
# simulator's, so the times are not compared, the values are).
def _stealth_series(check):
    import build
    import sim
    m, t, _ = build.resolve('engine_stealth', check)
    return {c: [row[1][i] for row in sim.Sim(m, t).run(24.0).series] for i, (c, _) in enumerate(t.counters)}


def test_invisibility_broadcast_the_aura_holds_its_guardian_at_full_health_and_the_control_dies():
    a = _stealth_series('a')
    assert a['CNV_Stealth_BaseHp'] == [100] * 25, a['CNV_Stealth_BaseHp']    # bench 光环血 100 throughout
    assert a['CNV_Stealth_HighHp'][-1] <= 10, a['CNV_Stealth_HighHp']        # bench 对照血 4 at the end
    assert a['CNV_Stealth_Bits'] == [0] * 25                                # STEALTHED never reads (stealth.md 5)


def test_invisibility_broadcast_fire_stops_the_moment_it_hides_and_the_order_waits_for_the_aura_to_drop():
    a, b = _stealth_series('a'), _stealth_series('b')
    order, late = a['CNV_Stealth_OrderHp'], b['CNV_Stealth_SwitchHp']
    assert order[:5] == [100] * 5 and 50 <= order[-1] <= 56, order        # aura off 6 s, on again: bench 54 from s15
    assert order[-1] == order[-3] and order[11] > order[-1], order        # stopped dead once the aura came back
    assert late[0] == 100 and 47 <= late[-1] <= 56 and late[-1] == late[-4], late   # bench 后隐血 50 from s10


def test_invisibility_behavior_a_house_given_garrison_can_stealth_by_script_is_shot_like_a_plain_one():
    b = _stealth_series('b')                                              # bench 隐楼血 = 明楼血 (98 at s4 .. 45)
    assert b['CNV_Stealth_HiddenHp'] == b['CNV_Stealth_PlainHp'] and b['CNV_Stealth_HiddenHp'][-1] < 80, b


# ---- WeaponSetUpdate / StatusBitsUpgrade (simunits.weapon_sets / pick_weapons, Sim.modify; bench 2026-11-09 engine_weaponset
# a / b, engine_statusbits b; docs/engine/weaponset.md). A weapon line's ObjectStatus / ForbiddenObjectStatus choose the gun:
# a conscript with GENERIC_TOGGLE_STATE throws Molotovs instead of firing the AK47 (changing in mid-fight when the script
# gives it); a Guardian under the toggle holds only the target painter (no damage); the upgrade module's HEROIC grant
# sets WEAPON_UPGRADED_01 / _02 and a removal takes it back. Bench 基准血 / 毒瓶血 / 中途血 at s41: 42 / 9 / 21.
def _series(build_name, check, until):
    import build
    import sim
    m, t, _ = build.resolve(build_name, check)
    return {c: [row[1][i] for row in sim.Sim(m, t).run(until).series] for i, (c, _) in enumerate(t.counters)}


def test_weapon_set_the_status_picks_the_gun_molotov_under_the_toggle_and_the_painter_does_no_harm():
    a = _series('engine_weaponset', 'a', 41.0)
    base, high, order = a['CNV_Wset_BaseHp'], a['CNV_Wset_HighHp'], a['CNV_Wset_OrderHp']
    assert abs(base[-1] - 42) <= 3 and abs(high[-1] - 9) <= 3 and abs(order[-1] - 21) <= 3, (base[-1], high[-1], order[-1])
    assert order[8] == base[8] and order[20] < base[20], (order, base)       # the same until the toggle, faster after it
    b = _series('engine_weaponset', 'b', 20.0)
    assert b['CNV_Wset_LowHp'] == [100] * len(b['CNV_Wset_LowHp']), b['CNV_Wset_LowHp']      # bench 涂靶血 100 throughout


def test_status_bits_upgrade_the_heroic_grant_sets_weapon_upgraded_and_a_removal_clears_it():
    b = _series('engine_statusbits', 'b', 20.0)
    assert [b[k][-1] for k in ('CNV_Sbits_HighBit', 'CNV_Sbits_OrderBit', 'CNV_Sbits_RemovedBit', 'CNV_Sbits_Other')] == \
        [1, 1, 0, 11], b                                                      # bench s7-s41: 1 1 0 11 (s1-s6: 1 0 1 11)
    assert (b['CNV_Sbits_OrderBit'][3], b['CNV_Sbits_RemovedBit'][3]) == (0, 1)


# ---- ToppleUpdate: engine_topple a / b, bench 2026-11-09 (docs/engine/crush.md).
# Each row is undestroyed frames + 1000 * dying frames + 1000000 * frames at the goal.
def test_topple_the_five_props_disappear_at_the_bench_frames_without_ever_dying():
    for build_name, check, destroyed, arrivals in (
            ('engine_topple', 'a', (162, 118, 163), (91, 91, 91)),
            ('engine_topple_b', 'b', (119, None, 170), (91, 111, 110))):
        s = _sim_run(build_name, check, 50.0)
        frames, *rows = s.series[-1][1]
        assert 710 <= frames < 1000, frames                  # the conscript's control outlasts the bench's 710
        for row, gone, arrived in zip(rows, destroyed, arrivals):
            undestroyed, dying, at_goal = row % 1000, row // 1000 % 1000, row // 1000000
            assert dying == 0, (check, row)
            assert undestroyed == frames if gone is None else abs(undestroyed - gone) <= 2, (check, row, gone)
            assert abs((frames - at_goal + 1) - arrived) <= 2, (check, row, arrived)


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
    import simunits
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
        assert simunits.suppression('AlliedCommandoTech1') is None
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
    # Directly isolate the settled threshold and modifier from open timing.
    m, t, _ = build.resolve('engine_suppression', 'threshold')
    s = sim.Sim(m, t)
    b = s.body('UNIT - CNV Supp high man')
    for points, suppressed in ((48, False), (50, True)):
        b.suppression_hits = [(1000, points)]
        b.suppression_next = 0
        b.suppressed_until = -1
        s.suppression_tick()
        assert (b.suppressed_until > s.frame_now()) is suppressed
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


def test_inform_target_does_not_add_damage_to_the_separate_damage_nugget():
    import build
    import sim
    m,t,_=build.resolve('engine_inform','damage')
    engine=sim.Sim(m,t);engine.shot_clock=True
    assert tuple(engine.run(16).series[-1][1])==(79,1,79,1)


# ---- FireWeaponWhenDead (simunits.death_weapons; Sim.destroy / death_blast_due): bench 2026-11-05 engine_spawn_refill
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


# ---- PropBody (simunits.prop_body; Body.damage / health, Sim.destroy): bench 2026-11-10 engine_propbody a / b / c
# (checks/engine_propbody.py). A street segment AM_StreetSegment01, a tree CS_Tree01 and a lantern OK_Lantern01, neutral.
# a: NAMED_DAMAGE 10 -- the health percent reads 0 throughout, all three stay. b: NAMED_KILL -- the segment stays for
# good, the tree / lantern are gone 61 / 121 frames after (their ToppleUpdate delay), never dying. c: a Hammer told to
# attack each never fires. Rows: frames not destroyed + 1000 x frames dying (a: 存 1000^(k-1) a frame for each left).
def test_prop_body_no_health_a_kill_leaves_the_street_and_topples_the_tree_and_lantern_at_the_bench_frames():
    a = _sim_run('engine_propbody', 'a', 21.0).series
    assert all(row[1][:3] == [0, 0, 0] for row in a), a                     # bench 血1..3: 0 0 0 throughout
    left = a[-1][1][3]
    assert left == (left % 1000) * 1001001, left                            # bench 存 333333333: all three there
    frames, street, tree, lantern = _sim_run('engine_propbody_b', 'b', 21.0).series[-1][1]
    assert street == frames and (tree, lantern) == (61, 121), (frames, street, tree, lantern)   # bench 332 332 61 121
    c = _sim_run('engine_propbody_c', 'c', 21.0).series[-1][1]
    assert c[1:] == [c[0]] * 3, c                                           # bench 332 x 4: none shot, none dying


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
    assert inventory.NOTES[inventory.NUGGET,'InformTargetNugget'][0]==inventory.TODO


def test_projectile_nugget_flight_uses_retail_shell_speed_and_resolved_warhead():
    import build
    import sim
    import simunits
    assert any(w.get('projectile')=='SovietAntiVehicleVehicleTech1TankProjectile'
               for w in simunits.weapon_table().values())
    m,t,_=build.resolve('engine_projectile','flight')
    e=sim.Sim(m,t);e.shot_clock=True
    assert tuple(e.run(16).series[-1][1])==(7,95,11,95)


def test_activate_laser_uses_separate_damage_nugget_without_delaying_the_hit():
    import inventory
    assert inventory.NOTES[inventory.NUGGET,'ActivateLaserNugget'][0]==inventory.NA
    import build
    import sim
    m,t,_=build.resolve('engine_laser','pair')
    e=sim.Sim(m,t);e.shot_clock=True
    assert tuple(e.run(16).series[-1][1])==(2,90,2,90)
    assert all('LaserStateID="201"' in u.xml and 'LaserId="201"' in u.xml
               for u in m.units if u.id.startswith('CNV_Laser'))


def test_weapon_ocl_lifetime_damage_reads_the_fire_delay_before_counting_updates():
    import build
    import sim
    m,t,_=build.resolve('engine_oclone','a')
    e=sim.Sim(m,t);e.shot_clock=True
    assert tuple(e.run(16).series[-1][1])==(99,1,40,1)


def test_tint_changes_no_health_or_hit_timing_beyond_the_separate_damage_nugget():
    import inventory
    assert inventory.NOTES[inventory.NUGGET,'TintObjectsNugget'][0]==inventory.NA
    import build
    import sim
    m,t,_=build.resolve('engine_tint','pair')
    e=sim.Sim(m,t);e.shot_clock=True
    assert tuple(e.run(16).series[-1][1])==(2,90,2,90)
    assert 'TintObjectsNugget' in next(u.xml for u in m.units if u.id=='CNV_LaserHigh')


def test_secondary_damage_delivers_one_amount_at_hit_without_damaging_health():
    import build
    import sim
    m,t,_=build.resolve('engine_secondary','single')
    e=sim.Sim(m,t);e.shot_clock=True
    assert tuple(e.run(16).series[-1][1])==(1099,0,1099,1)


# ---- ContestableGarrisonContain (simgarrison.Garrisons, sim.Sim.garrison): bench 2026-11-05 engine_garrison in / hp
# (checks/engine_garrison.py, docs/engine/garrison.md 1-5). The script's _INSTANTLY entry skips the room and the
# relation (six in, 16), the owner is the first passenger's and back to the civilians when empty (15, 0); 3000 health
# (BaseCivilianStructureMedium's), out at 13 % in the damage's frame (伤争敌 1230), the contesting conscript bounces one
# and stays out (1220); a killing hit and a script kill both eject them alive (炸杀 33 -> 0, 存活 33 throughout).
def _garrison_series(check):
    import build
    import sim
    m, t, _ = build.resolve('engine_garrison', check)
    return {s: row for s, row in sim.Sim(m, t).run(24.0).series}


def test_garrison_script_entry_skips_room_and_relation_owner_follows_and_damage_or_kill_ejects_alive_at_the_bench():
    a = _garrison_series('in')
    got = [tuple(a[s]) for s in (4, 10, 16)]
    assert got == [(16, 1123, 33, 33), (15, 1230, 0, 33), (0, 1220, 0, 33)], got   # bench s4-7 / s10-13 / s16-
    hp = _garrison_series('hp')
    assert [hp[s][:2] for s in (4, 10, 16)] == [[100, 100], [0, 13], [0, 6]], hp   # bench 炸楼血 / 伤楼血


def test_leech_percent_uses_victim_maximum_not_current_health_or_caster_maximum():
    import build
    import sim
    m,t,_=build.resolve('engine_leechpct','a')
    e=sim.Sim(m,t);e.shot_clock=True
    assert tuple(e.run(16).series[-1][1])==(1000025,1000025,1000030,1000020)
