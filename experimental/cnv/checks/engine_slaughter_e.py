"""E170: carrier SlaughterHordeContain removal, natural drone sortie/return.

Prediction (INFERRED): both carriers launch three drones; after their named
victims are deleted the retail carrier consumes returning drones, while the
removal control retains them. Counts are living drones per owner, not parking
slots or parent identity. Freeze at script frames 180 and 600. No AI tactical
result is used as container evidence. Unmeasured lifecycle details stay gaps.

Build p (E170 reopened): both carriers p1, both targets s1, so each arm is
counted by its own area (half 850 round host and target, 1800 apart). Lines:
frame; OnLate / OffLate, the frames f300-f600 with a p1 AIRCRAFT in that
arm's area (the targets go at f240, so a drone then is one not taken back);
gate bits: target attacked by an AlliedAttackDrone On 1 / Off 2, an AIRCRAFT
in the area f60-f240 On 4 / Off 8, host alive at f600 On 16 / Off 32.
Prediction from the data (OCL RETURN_TO_SOURCE; only SlaughterHordeContain
takes a drone in -- the ParkingPlace stays in both): gate 63, OnLate small
(the last sortie's way home), OffLate 300 (its drones stay out or parked on
deck, still AIRCRAFT). A gate without 1 / 2 says the sortie never happened.
"""
import re
from pathlib import Path
import labpaths


from checks.engine_modulebatch import native
from checks import engine_scripts8 as s8
from maps import infiltrator_batch
from parts import Mission, Script, Test, Unit, counted, kindof, square


def carrier(ident, strip=False, hardpoint=False):
    """The retail carrier cloned as `ident`; strip: without its SlaughterHordeContain; hardpoint: its drone weapon on
    a WeaponSlotHardpoint in place of the turret slot (no TurretSettings)."""
    xml = native('AlliedAntiStructureShip', 'Units', ident).xml
    # The included render states consume local defines too; expand them
    # before cloning so the two files do not share compiler globals.
    sage = Path(labpaths.SDK3) / 'SageXML'
    states = (sage / 'Includes/SpecialModelStates.xml').read_text(encoding='utf-8-sig')
    states = states[states.index('>') + 1:states.rindex('</SpecialModelStates>')]
    original = (sage / 'Allied/Units/AlliedAntiStructureShip.xml').read_text(encoding='utf-8-sig')
    for key, value in re.findall(r'<Define\s+name="([^"]+)"\s+value="([^"]+)"\s*/>', original):
        states = states.replace('=$' + key, value).replace('$' + key, value)
    xml, count = re.subn(r'<xi:include\s+href="DATA:Includes/SpecialModelStates.xml".*?/>', states, xml, flags=re.S)
    assert count == 1
    if strip:
        xml, count = re.subn(r'<SlaughterHordeContain\b.*?</SlaughterHordeContain>', '', xml, flags=re.S)
        assert count == 1
    if hardpoint:
        xml, count = re.subn(r'<WeaponSlotTurret ID="1">(.*?)<TurretSettings.*?</TurretSettings>\s*</WeaponSlotTurret>',
                             r'<WeaponSlotHardpoint ID="1">\1</WeaponSlotHardpoint>', xml, flags=re.S)
        assert count == 1
    return Unit(ident, xml)


def mission(name='CampSlaughterE', sides=('p1', 's1')):
    m = Mission(name=name, map=infiltrator_batch, units=[])
    for tag, side, dx in [('On', sides[0], -1800), ('Off', sides[1], 0)]:
        ident = 'CNVE170' + tag
        m.units.append(carrier(ident, tag == 'Off'))
        m.put(ident, 'ship', dx, 0, side=side, role=tag + ' host', name='E170 ' + tag + ' host')
        m.put('SovietAntiAirShip', 'ship', dx, 500, side='s1' if side == 'p1' else 'p1',
              role=tag + ' target', name='E170 ' + tag + ' target')
        m.waypoint(tag + ' mid', 'E170 ' + tag + ' mid', 'ship', dx, 250)
    m.spawns.add('AlliedAttackDrone')
    return m


def check(m, corrected=False):
    t = Test()
    t.areas['E170All'] = square(2500, 2500, 2700)
    t.counters = [('E170Frame', '完成帧'), ('E170Hosts', '宿主存活'),
                  ('E170Attack', '攻击期数量'), ('E170Return', '返航后数量')]
    t.scripts = [Script('Test - frame', [('COUNTER', 'E170Frame', 0, 600)],
                        [('INCREMENT_COUNTER', 1, 'E170Frame')], once=False),
                 Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    for tag, side, weight in [('On', 'p1', 1), ('Off', 's1', 10)]:
        host, victim = m.role(tag + ' host').name, m.role(tag + ' target').name
        t.scripts += [Script('Test - quiet ' + tag, [], [
            ('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 1),
            ('UNIT_CHANGE_OBJECT_STATUS', victim, 'NO_ATTACK', 1),
            ('UNIT_SET_HEALTH', victim, 100)]),
            Script('Test - heal ' + tag, [('NAMED_NOT_DESTROYED', victim)], [('UNIT_SET_HEALTH', victim, 100)], once=False),
            Script('Test - attack ' + tag, [('COUNTER', 'E170Frame', 2, 60)], [
                ('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 0),
                ('NAMED_ATTACK_NAMED', host, victim)]),
            Script('Test - remove victim ' + tag, [('COUNTER', 'E170Frame', 2, 240)], [('NAMED_DELETE', victim)]),
            Script('Test - alive ' + tag, [('COUNTER', 'E170Frame', 2, 600), ('NAMED_NOT_DESTROYED', host)],
                   [('INCREMENT_COUNTER', weight, 'E170Hosts')])]
        for frame, counter in [(180, 'E170Attack'), (600, 'E170Return')]:
            for n in range(1, 10):
                t.scripts.append(Script(f'Test - count {tag} {frame} {n}', [
                    ('COUNTER', 'E170Frame', 2, frame),
                    ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', m.player(side), 2, n, kindof('AIRCRAFT' if corrected else 'DRONE'), 'E170All')],
                    [('INCREMENT_COUNTER', weight * n, counter)]))
    t.expect = [('完成帧', 0, 'ever==', 600), ('宿主存活', 0, 'ever==', 11),
                ('攻击期数量', 0, 'ever==', 55 if corrected else 33),
                ('返航后数量', 0, 'ever==', 50 if corrected else 30)]
    # Run a's DRONE meter cannot see AlliedAttackDrone (retail KindOf is AIRCRAFT).
    # Run b changes only the meter. ClipSize=5/OCL Count=1 predicts five sorties;
    # this remains a prediction, not a fitted observation.
    t.bench = ([('bench_camera', dict(x=2000, y=3400, look=False))] if corrected else []) + [('bench_watch', dict(seconds=100, every=1, sheet=False, lines=4))]
    return t


def check_p(m):
    """Build p: both arms p1, each counted in its own area (module docstring)."""
    t = Test()
    t.counters = [('E170Frame', '完成帧'), ('E170OnLate', '原版晚段帧'),
                  ('E170OffLate', '删模块晚段帧'), ('E170Gate', '前置位')]
    t.scripts = [Script('Test - frame', [('COUNTER', 'E170Frame', 0, 600)],
                        [('INCREMENT_COUNTER', 1, 'E170Frame')], once=False),
                 Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    p1 = m.player('p1')
    for tag, weight in [('On', 1), ('Off', 2)]:
        host, victim, area = m.role(tag + ' host').name, m.role(tag + ' target').name, 'E170 ' + tag
        t.areas[area] = square(*m.point(tag + ' mid'), 850)
        air = ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', p1, 3, 1, kindof('AIRCRAFT'), area)
        t.scripts += [
            Script('Test - quiet ' + tag, [], [
                ('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 1),
                ('UNIT_CHANGE_OBJECT_STATUS', victim, 'NO_ATTACK', 1),
                ('UNIT_SET_HEALTH', victim, 100)]),
            Script('Test - heal ' + tag, [('NAMED_NOT_DESTROYED', victim)], [('UNIT_SET_HEALTH', victim, 100)], once=False),
            Script('Test - attack ' + tag, [('COUNTER', 'E170Frame', 2, 60)], [
                ('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 0),
                ('NAMED_ATTACK_NAMED', host, victim)]),
            Script('Test - remove victim ' + tag, [('COUNTER', 'E170Frame', 2, 240)], [('NAMED_DELETE', victim)]),
            Script('Test - hit ' + tag, [('COUNTER', 'E170Frame', 1, 240), ('NAMED_NOT_DESTROYED', victim),
                   ('NAMED_ATTACKED_BY_OBJECTTYPE', victim, 'AlliedAttackDrone')],
                   [('INCREMENT_COUNTER', weight, 'E170Gate')]),
            Script('Test - out ' + tag, [('COUNTER', 'E170Frame', 3, 60), ('COUNTER', 'E170Frame', 1, 240), air],
                   [('INCREMENT_COUNTER', 4 * weight, 'E170Gate')]),
            Script('Test - late ' + tag, [('COUNTER', 'E170Frame', 3, 300), ('COUNTER', 'E170Frame', 0, 600), air],
                   [('INCREMENT_COUNTER', 1, 'E170' + tag + 'Late')], once=False),
            Script('Test - alive ' + tag, [('COUNTER', 'E170Frame', 2, 600), ('NAMED_NOT_DESTROYED', host)],
                   [('INCREMENT_COUNTER', 16 * weight, 'E170Gate')])]
    t.expect = [('完成帧', 0, 'ever==', 600), ('前置位', 0, 'ever==', 63)]
    t.bench = [('bench_camera', dict(x=2900, y=3600, look=False)),
               ('bench_watch', dict(seconds=100, every=1, sheet=False, lines=4))]
    return t


# Build q (after p's three no-sortie runs): does any carrier send a drone when told to? Three p1 arms, 1200 apart,
# each with its s1 target 500 off: Rs the retail carrier at a SovietAntiAirShip (as p), Rb the retail one at a
# SovietPowerPlant ashore, Cb p's clone (module kept) at the same plant. The weapon writes no RequiredAntiMask and the
# schema's default is ANTI_GROUND ANTI_WATER ANTI_STRUCTURE (AssetTypeWeaponTemplate.xsd), so the data predicts all
# three launch. Rs alone dark: ships are not its targets after all; Cb alone: the clone; all dark: the order. The
# order comes at f300 (p's at f60 was over before the bench's frames start, about f250), the targets go at f480.
ARMS_Q = [('Rs', 'AlliedAntiStructureShip', 'SovietAntiAirShip', -2400, 500),
          ('Rb', 'AlliedAntiStructureShip', 'SovietPowerPlant', -1200, -500),
          ('Cb', 'CNVE170Cb', 'SovietPowerPlant', 0, -500)]


def mission_q():
    m = Mission(name='CampSlaughterQ', map=infiltrator_batch, units=[carrier('CNVE170Cb')])
    for tag, host, target, dx, dy in ARMS_Q:
        m.put(host, 'ship', dx, 0, side='p1', role=tag + ' host', name='E170 ' + tag + ' host')
        m.put(target, 'ship', dx, dy, side='s1', role=tag + ' target', name='E170 ' + tag + ' target')
        m.waypoint(tag + ' mid', 'E170 ' + tag + ' mid', 'ship', dx, dy / 2)
    m.spawns.add('AlliedAttackDrone')
    return m


def check_q(m):
    """Lines: frame; Out (bits Rs 1 / Rb 2 / Cb 4: a p1 AIRCRAFT in that arm's area f300-f480); Hit (the same bits:
    the target attacked by an AlliedAttackDrone before f480). Prediction: 600 / 7 / 7."""
    t = Test()
    t.counters = [('E170Frame', '完成帧'), ('E170Out', '出机位'), ('E170Hit', '命中位')]
    t.scripts = [Script('Test - frame', [('COUNTER', 'E170Frame', 0, 600)],
                        [('INCREMENT_COUNTER', 1, 'E170Frame')], once=False),
                 Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    for (tag, *_), bit in zip(ARMS_Q, (1, 2, 4)):
        host, victim, area = m.role(tag + ' host').name, m.role(tag + ' target').name, 'E170 ' + tag
        t.areas[area] = square(*m.point(tag + ' mid'), 550)
        air = ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', m.player('p1'), 3, 1, kindof('AIRCRAFT'), area)
        t.scripts += [
            Script('Test - quiet ' + tag, [], [
                ('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 1),
                ('UNIT_CHANGE_OBJECT_STATUS', victim, 'NO_ATTACK', 1),
                ('UNIT_SET_HEALTH', victim, 100)]),
            Script('Test - heal ' + tag, [('NAMED_NOT_DESTROYED', victim)], [('UNIT_SET_HEALTH', victim, 100)], once=False),
            Script('Test - attack ' + tag, [('COUNTER', 'E170Frame', 2, 300)], [
                ('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 0),
                ('NAMED_ATTACK_NAMED', host, victim)]),
            Script('Test - remove victim ' + tag, [('COUNTER', 'E170Frame', 2, 480)], [('NAMED_DELETE', victim)]),
            Script('Test - hit ' + tag, [('COUNTER', 'E170Frame', 1, 480), ('NAMED_NOT_DESTROYED', victim),
                   ('NAMED_ATTACKED_BY_OBJECTTYPE', victim, 'AlliedAttackDrone')],
                   [('INCREMENT_COUNTER', bit, 'E170Hit')]),
            Script('Test - out ' + tag, [('COUNTER', 'E170Frame', 3, 300), ('COUNTER', 'E170Frame', 1, 480), air],
                   [('INCREMENT_COUNTER', bit, 'E170Out')])]
    t.expect = [('完成帧', 0, 'ever==', 600), ('出机位', 0, 'ever==', 7), ('命中位', 0, 'ever==', 7)]
    t.bench = [('bench_camera', dict(x=2600, y=3000, look=False)),
               ('bench_watch', dict(seconds=70, every=1, sheet=False, lines=3))]
    return t


# Build r (coordinator 11-23, after q): the order by hand, as HealCrate c. One p1 retail carrier 100 south of the ship
# pad, an s1 SovietPowerPlant ashore 350 south of it (inside the weapon's 200-1000); the camera goes to their midpoint at
# s1, the bench boxes the carrier and right-clicks the plant. Lines: frame; gate (a p1 AIRCRAFT near the pair 1, the
# plant attacked by an AlliedAttackDrone 2, the plant deleted 4 -- 150 frames after that first hit, so the bench's slow
# steps do not matter); frames since the hit; Late, the frames 60-240 after the deletion with a p1 AIRCRAFT near the
# pair. Prediction: 1500 / 7 / 400 / small (the last sortie's way home, then taken in). Gate 0: not even by hand.
def mission_r():
    m = Mission(name='CampSlaughterR', map=infiltrator_batch, units=[])
    m.put('AlliedAntiStructureShip', 'ship', 0, -100, side='p1', role='R host', name='E170 R host')
    m.put('SovietPowerPlant', 'ship', 0, -450, side='s1', role='R target', name='E170 R target')
    m.spawns.add('AlliedAttackDrone')
    return m


def check_r(m):
    t = Test()
    t.counters = [('E170Frame', '完成帧'), ('E170Gate', '前置位'), ('E170Since', '命中后帧'), ('E170Late', '删后有机帧')]
    victim = m.role('R target').name
    (x, y), (px, py), (vx, vy) = (m.site('ship', 0, dy) for dy in (-100, -450, -275))
    t.waypoints['E170 R view'] = (vx, vy)
    t.areas['E170 R'] = square(vx, vy, 450)
    air = ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', m.player('p1'), 3, 1, kindof('AIRCRAFT'), 'E170 R')
    since = lambda op, n: ('COUNTER', 'E170Since', op, n)
    t.scripts = [Script('Test - frame', [('COUNTER', 'E170Frame', 0, 1500)], [('INCREMENT_COUNTER', 1, 'E170Frame')],
                        once=False),
                 Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                 Script('Test - heal', [('NAMED_NOT_DESTROYED', victim)], [('UNIT_SET_HEALTH', victim, 100)], once=False),
                 Script('Test - out', [air], [('INCREMENT_COUNTER', 1, 'E170Gate')]),
                 Script('Test - hit', [('NAMED_NOT_DESTROYED', victim),
                                       ('NAMED_ATTACKED_BY_OBJECTTYPE', victim, 'AlliedAttackDrone')],
                        [('INCREMENT_COUNTER', 2, 'E170Gate'), ('SET_COUNTER', 'E170Since', 1)]),
                 Script('Test - since', [since(3, 1), since(0, 400)], [('INCREMENT_COUNTER', 1, 'E170Since')], once=False),
                 Script('Test - remove victim', [since(2, 150)],
                        [('NAMED_DELETE', victim), ('INCREMENT_COUNTER', 4, 'E170Gate')]),
                 Script('Test - late', [since(3, 210), since(1, 390), air], [('INCREMENT_COUNTER', 1, 'E170Late')],
                        once=False)]
    s8.at(t, 'view', 1., [('MOVE_CAMERA_TO', 'E170 R view', 0.5, 0.0, 1.0, 1.0)])
    t.expect = [('完成帧', 0, 'ever==', 1500), ('前置位', 0, 'ever==', 7)]
    watch = dict(every=1, sheet=False, lines=4)
    t.bench = [('bench_watch', dict(watch, seconds=2.0)), ('bench_view', dict(x=vx, y=vy, look=True)),
               ('bench_box', dict(x0=x - 100, y0=y - 50, x1=x + 100, y1=y + 50, look=True)),
               ('bench_click', dict(x=px, y=py, right=True, look=True)), ('bench_watch', dict(watch, seconds=75.0))]
    return t


# Build s (E251, coordinator 11-26: D191's controls, two rounds at most). Four p1 lanes 1200 apart, each with its s1
# SovietPowerPlant ashore 500 off (the Athena 350): Ra the retail carrier (the baseline, dark in q / r); Hp the clone
# with the drone weapon on a WeaponSlotHardpoint (D's H2: the turret never gets on target); Dr the retail carrier with
# a p1 AlliedAttackDrone put into it at f30 by NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY (H1: a drone aboard first);
# At an Athena at the same kind of plant, the positive control for an OCL-only weapon on a turret told
# NAMED_ATTACK_NAMED. Order f300, targets go f480. Lines: frame; Out (a p1 AIRCRAFT in the lane's area f300-f480, Ra 1
# / Hp 2 / Dr 4 -- Dr counts two, its own drone may be one); Hit (the plant attacked by an AlliedAttackDrone, At's by
# p1 at all: Ra 1 / Hp 2 / Dr 4 / At 8); Aboard (Dr's area has no p1 AIRCRAFT at f290: 1). The data predicts
# 600 / 7 / 15 / 1; q / r predict 600 / 0 / 8. Hp alone lights: H2; Dr alone: H1; At dark: the order on this bench,
# not the carrier; carriers dark with At lit: back to the program (H4, the factory's build-complete init, round 2).
ARMS_S = [('Ra', 'AlliedAntiStructureShip', -3000, 0), ('Hp', 'CNVE170Hp', -1800, 0),
          ('Dr', 'AlliedAntiStructureShip', -600, 0), ('At', 'AlliedAntiStructureVehicle', 600, -850)]


def mission_s():
    m = Mission(name='CampSlaughterS', map=infiltrator_batch, units=[carrier('CNVE170Hp', hardpoint=True)])
    for tag, host, dx, hy in ARMS_S:
        m.put(host, 'ship', dx, hy, side='p1', role=tag + ' host', name='E170 ' + tag + ' host')
        m.put('SovietPowerPlant', 'ship', dx, -500, side='s1', role=tag + ' target', name='E170 ' + tag + ' target')
        m.waypoint(tag + ' mid', 'E170 ' + tag + ' mid', 'ship', dx, (hy - 500) / 2)
    m.put('AlliedAttackDrone', 'ship', -450, 0, side='p1', role='Dr drone', name='E170 Dr drone')
    m.spawns.add('AlliedAttackDrone')
    return m


def check_s(m, probe=False):
    """probe (check t, round 2 after s read 600 / 0 / 0 / 1 -- the Athena dark too): At's plant is not healed, the
    fourth line is At's two signs (attacked by p1 1, health under 100 % 2) in place of Aboard, and the camera follows
    At (s15-s25), Dr, Hp, then At again. Prediction: 600 / 0 / 0 / 3 (Athena fires, carriers dark as in s)."""
    t = Test()
    t.counters = [('E170Frame', '完成帧'), ('E170Out', '出机位'), ('E170Hit', '命中位'),
                  ('E170Aboard', '雅典娜' if probe else '预装')]
    p1 = m.player('p1')
    t.scripts = [Script('Test - frame', [('COUNTER', 'E170Frame', 0, 600)],
                        [('INCREMENT_COUNTER', 1, 'E170Frame')], once=False),
                 Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1)]),
                 Script('Test - board', [('COUNTER', 'E170Frame', 2, 30)], [
                     ('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', m.role('Dr drone').name, m.role('Dr host').name)]),
                 Script('Test - aboard', [('COUNTER', 'E170Frame', 2, 290), (
                     'PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', p1, 2, 0, kindof('AIRCRAFT'), 'E170 Dr')],
                     [('INCREMENT_COUNTER', 1, 'E170Aboard')])][:-1 if probe else None]
    if probe:
        plant = m.role('At target').name
        t.scripts += [Script(f'Test - athena {n}', [('COUNTER', 'E170Frame', 1, 480), ('NAMED_NOT_DESTROYED', plant), c],
                             [('INCREMENT_COUNTER', n, 'E170Aboard')])
                      for n, c in ((1, ('NAMED_ATTACKED_BY_PLAYER', plant, p1)), (2, ('UNIT_HEALTH', plant, 0, 100)))]
    for (tag, *_), bit in zip(ARMS_S, (1, 2, 4, 8)):
        host, victim, area = m.role(tag + ' host').name, m.role(tag + ' target').name, 'E170 ' + tag
        t.areas[area] = square(*m.point(tag + ' mid'), 550)
        hit = ('NAMED_ATTACKED_BY_PLAYER', victim, p1) if tag == 'At' else (
            'NAMED_ATTACKED_BY_OBJECTTYPE', victim, 'AlliedAttackDrone')
        t.scripts += [
            Script('Test - quiet ' + tag, [], [
                ('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 1),
                ('UNIT_CHANGE_OBJECT_STATUS', victim, 'NO_ATTACK', 1),
                ('UNIT_SET_HEALTH', victim, 100)])] + ([] if probe and tag == 'At' else [
            Script('Test - heal ' + tag, [('NAMED_NOT_DESTROYED', victim)], [('UNIT_SET_HEALTH', victim, 100)], once=False),
            Script('Test - hit ' + tag, [('COUNTER', 'E170Frame', 1, 480), ('NAMED_NOT_DESTROYED', victim), hit],
                   [('INCREMENT_COUNTER', bit, 'E170Hit')])]) + [
            Script('Test - attack ' + tag, [('COUNTER', 'E170Frame', 2, 300)], [
                ('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 0),
                ('NAMED_ATTACK_NAMED', host, victim)]),
            Script('Test - remove victim ' + tag, [('COUNTER', 'E170Frame', 2, 480)], [('NAMED_DELETE', victim)])]
        if tag != 'At':
            air = ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', p1, 3, 2 if tag == 'Dr' else 1,
                   kindof('AIRCRAFT'), area)
            t.scripts.append(Script('Test - out ' + tag, [('COUNTER', 'E170Frame', 3, 300),
                                                          ('COUNTER', 'E170Frame', 1, 480), air],
                                    [('INCREMENT_COUNTER', bit, 'E170Out')]))
    t.expect = [('完成帧', 0, 'ever==', 600), ('出机位', 0, 'ever==', 7), ('命中位', 0, 'ever==', 7 if probe else 15),
                ('雅典娜', 0, 'ever==', 3) if probe else ('预装', 0, 'ever==', 1)]
    watch = dict(every=1, sheet=False, lines=4)
    if not probe:
        t.bench = [('bench_camera', dict(x=2600, y=3000, look=False)), ('bench_watch', dict(watch, seconds=70))]
        return t
    t.bench = []
    for tag, seconds in (('At', 10), ('Dr', 5), ('Hp', 5), ('At', 45)):
        x, y = m.point(tag + ' mid')
        t.bench += [('bench_camera', dict(x=x, y=y, look=False)), ('bench_watch', dict(watch, seconds=seconds))]
    return t


# Build u (A400, after t's dark Athena: the program's attack gate takes an OCL-only weapon, engine_see's Athena hit its
# tower on order). t's geometry, five Athenas 1000 apart, each 350 from its s1 target: a quieted at f0 and cleared at
# f300, no order (H10: does it pick the plant by itself); b the clone with a Damage=1 DamageNugget beside the OCLs,
# cleared and ordered (H9: a damage warhead passes where the OCL ones do not); c retail cleared and ordered (t again);
# d retail never quieted, ordered at f300 (engine_see's way: is NO_ATTACK's history the gate); e as c at an
# AlliedBaseDefense (H7: the plant). Lines: frame; Hit (target attacked by p1, a 1 b 2 c 4 d 8 e 16); Hurt (target under
# 100 %); Early (attacked by p1 before f300). The data predicts 900 / 31 / 31 / 8; all dark leaves the map (H8).
ARMS_U = [('a', 'AlliedAntiStructureVehicle', 'SovietPowerPlant'), ('b', 'CNVA400Dmg', 'SovietPowerPlant'),
          ('c', 'AlliedAntiStructureVehicle', 'SovietPowerPlant'), ('d', 'AlliedAntiStructureVehicle', 'SovietPowerPlant'),
          ('e', 'AlliedAntiStructureVehicle', 'AlliedBaseDefense')]


def athena_dmg():
    uid, wid = 'CNVA400Dmg', 'CNVA400DmgWeapon'
    sage = Path(labpaths.SDK3) / 'SageXML'
    w = re.search(r'<WeaponTemplate\s+id="AlliedAntiStructureSolarTargeter".*?</WeaponTemplate>',
                  (sage / 'GlobalData/Weapon.xml').read_text(encoding='utf-8-sig'), re.S).group(0)
    w = w.replace('id="AlliedAntiStructureSolarTargeter"', f'id="{wid}"').replace('<Nuggets>', '<Nuggets>\n<DamageNugget '
        'Damage="1.0" Radius="10.0" DamageType="EXPLOSIVE" DeathType="NORMAL" PartitionFilterTestType="CIRCLE"/>', 1)
    xml = (sage / 'Allied/Units/AlliedAntiStructureVehicle.xml').read_text(encoding='utf-8-sig')
    assert xml.count('id="AlliedAntiStructureVehicle"') == xml.count('Template="AlliedAntiStructureSolarTargeter"') == 1
    xml = xml.replace('id="AlliedAntiStructureVehicle"', f'id="{uid}"').replace(
        'Template="AlliedAntiStructureSolarTargeter"', f'Template="{wid}"').replace(
        '</AssetDeclaration>', f'{w}\n</AssetDeclaration>', 1)
    return Unit(uid, xml, link=[f'WeaponTemplate:{wid}'])


def mission_u():
    m = Mission(name='CampSlaughterU', map=infiltrator_batch, units=[athena_dmg()])
    for k, (tag, host, target) in enumerate(ARMS_U):
        dx = 1000 * k - 3000
        m.put(host, 'ship', dx, -850, side='p1', role=tag + ' host', name='A400 ' + tag + ' host')
        m.put(target, 'ship', dx, -500, side='s1', role=tag + ' target', name='A400 ' + tag + ' target')
    return m


def check_u(m):
    t = Test()
    t.counters = [('A400Frame', '完成帧'), ('A400Hit', '打到'), ('A400Hurt', '掉血'), ('A400Early', '早打')]
    p1 = m.player('p1')
    t.scripts = [Script('Test - frame', [('COUNTER', 'A400Frame', 0, 900)],
                        [('INCREMENT_COUNTER', 1, 'A400Frame')], once=False),
                 Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1)])]
    for k, (tag, *_) in enumerate(ARMS_U):
        host, victim, bit = m.role(tag + ' host').name, m.role(tag + ' target').name, 1 << k
        hit = ('NAMED_ATTACKED_BY_PLAYER', victim, p1)
        t.scripts += [Script('Test - quiet ' + tag, [], [('UNIT_CHANGE_OBJECT_STATUS', victim, 'NO_ATTACK', 1)] + (
                          [] if tag == 'd' else [('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 1)])),
                      Script('Test - hit ' + tag, [hit], [('INCREMENT_COUNTER', bit, 'A400Hit')]),
                      Script('Test - hurt ' + tag, [('UNIT_HEALTH', victim, 0, 100)],
                             [('INCREMENT_COUNTER', bit, 'A400Hurt')]),
                      Script('Test - early ' + tag, [('COUNTER', 'A400Frame', 0, 300), hit],
                             [('INCREMENT_COUNTER', bit, 'A400Early')]),
                      Script('Test - attack ' + tag, [('COUNTER', 'A400Frame', 2, 300)],
                             ([] if tag == 'd' else [('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 0)]) +
                             ([] if tag == 'a' else [('NAMED_ATTACK_NAMED', host, victim)]))]
    t.expect = [('完成帧', 0, 'ever==', 900), ('打到', 0, 'ever==', 31), ('掉血', 0, 'ever==', 31), ('早打', 0, 'ever==', 8)]
    t.bench = [('bench_camera', dict(x=3800, y=2700, look=False)),
               ('bench_watch', dict(every=1, sheet=False, lines=4, seconds=80))]
    return t


def mission_v():
    """E251 H4: a naval-yard product versus a map-placed carrier."""
    m = Mission(name='CampSlaughterV', map=infiltrator_batch, units=[], ext=True)
    m.put('AlliedNavalYard', 'ship', -1200, 400, role='yard', name='E251 Yard')
    m.put('AlliedPowerPlant', 'ship', -1200, -650)
    m.put('AlliedAntiStructureShip', 'ship', -2510, 400, role='placed', name='E251 Placed')
    for lane, x in [('placed', -2510), ('built', -1110)]:
        m.put('SovietAntiAirShip', 'ship', x, 900, side='s1', role=lane + ' target', name='E251 ' + lane + ' target')
        m.waypoint(lane, 'E251 ' + lane, 'ship', x, 650)
    m.spawns.add('AlliedAttackDrone')
    return m


def check_v(m, controlled=False):
    """At f30 press the yard's build button (SDK 30s, 2000 ore); expect a second ship around f480.

    Gate bits: 1 second carrier in the built lane, 2 live reference bound to the unnamed product, 4 both
    orders dispatched at or after f600. Each arm displays 1000 * peak count in its area + current target HP%.
    Build w enables the real build button without the tech prerequisite and holds both hosts quiet
    until the paired order. It counts AIRCRAFT because v's type meter missed the sortie. This includes
    the yard's repair aircraft, so read the built arm against its pre-order peak.
    H4 predicts a dark placed arm (100) and a built arm with 1-5 live drones and damage; without an
    initialization difference the XML predicts both arms launch and deal damage. Both predictions INFERRED.
    """
    t, p1 = Test(), m.player('p1')
    frame, gate, ref = 'E251Frame', 'E251Gate', 'UNITRef - CNV E251 Built'
    yard, placed = m.role('yard').name, m.role('placed').name
    host_type = m.role('placed').template
    t.counters = [(frame, '完成帧'), (gate, '出厂位')]
    t.scripts = [
        Script('Test - frame', [('COUNTER', frame, 0, 1050)], [('INCREMENT_COUNTER', 1, frame)], once=False),
        Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 10000),
                                    ('TECHTREE_MODIFY_BUILDABILITY_OBJECT', host_type, 1) if controlled else
                                    ('NAMED_RECEIVE_UPGRADE', 'Upgrade_AlliedTech3', yard)] + [
            ('UNIT_CHANGE_OBJECT_STATUS', m.role(lane + ' target').name, 'NO_ATTACK', 1)
            for lane in ('placed', 'built')] + (
                [('UNIT_CHANGE_OBJECT_STATUS', placed, 'NO_ATTACK', 1)] if controlled else [])),
        Script('Test - queue carrier', [('COUNTER', frame, 2, 30)], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', yard, 'Command_ConstructAlliedAntiStructureShip')]),
        Script('Test - second carrier', [
            ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1, host_type, 'E251 built')], [
            ('INCREMENT_COUNTER', 1, gate),
            ('SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER', host_type, p1, m.team('s1'), ref)]),
        Script('Test - live reference', [('NAMED_NOT_DESTROYED', ref)], [('INCREMENT_COUNTER', 2, gate)] + (
            [('UNIT_CHANGE_OBJECT_STATUS', ref, 'NO_ATTACK', 1)] if controlled else [])),
        Script('Test - attack both', [('COUNTER', frame, 3, 600), ('NAMED_NOT_DESTROYED', ref),
                                      ('NAMED_NOT_DESTROYED', placed)], ([
            ('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 0) for host in (placed, ref)
        ] if controlled else []) + [
            ('NAMED_ATTACK_NAMED', host, m.role(lane + ' target').name)
            for lane, host in [('placed', placed), ('built', ref)]] + [('INCREMENT_COUNTER', 4, gate)]),
    ]
    for lane, label in [('placed', '预摆'), ('built', '现造')]:
        area, peak, meter = f'E251 {lane}', f'E251Peak{lane}', f'E251Meter{lane}'
        victim = m.role(lane + ' target').name
        t.areas[area] = square(*m.point(lane), 600)
        t.counters.append((meter, label))
        count = ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', kindof('AIRCRAFT')) if controlled else (
            'PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'AlliedAttackDrone')
        for n in range(1, 10):
            t.scripts.append(Script(f'Test - {lane} peak {n}', [
                (count[0], p1, 3, n, count[1], area)],
                [('INCREMENT_COUNTER', 1000, peak)]))
        t.scripts += [
            Script(f'Test - {lane} HP', [('NAMED_NOT_DESTROYED', victim)],
                   [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', victim, meter)], once=False),
            Script(f'Test - {lane} dead', [('NAMED_DESTROYED', victim)], [('SET_COUNTER', meter, 0)], once=False),
            Script(f'Test - {lane} show', [], [('COUNTER_MATH_COUNTER', meter, 0, peak)], once=False),
        ]
    s8.watch(t, 81., .5)
    return t


def mission_y():
    m = Mission(name='CampSlaughterY', map=infiltrator_batch, units=[carrier('CNVE170Off', strip=True)], ext=True)
    for tag, template, x in [('On', 'AlliedAntiStructureShip', -2510), ('Off', 'CNVE170Off', -1110)]:
        m.put(template, 'ship', x, 400, role=tag + ' host', name='E291 ' + tag + ' host')
        m.put('SovietAntiAirShip', 'ship', x, 900, side='s1', role=tag + ' target', name='E291 ' + tag + ' target')
        m.waypoint(tag, 'E291 ' + tag, 'ship', x, 650)
    m.spawns.add('AlliedAttackDrone')
    return m


def check_y(m):
    """W's water lanes without the yard. Predict both launch after f600 (INFERRED).

    Gate records each first aircraft (1/2) and paired deletion of live targets (4).
    RETURN_TO_SOURCE predicts the retail arm clears and the stripped arm retains
    aircraft (INFERRED); regional AIRCRAFT counts do not identify individual drones.
    """
    t, p1 = Test(), m.player('p1')
    frame, gate = 'E291Frame', 'E291Gate'
    t.counters = [(frame, '完成帧'), (gate, '出机位')]
    quiet, orders, delete, both_out = [], [], [], []
    for tag, label, bit in [('On', '原版机', 1), ('Off', '删模块机', 2)]:
        host, target = m.role(tag + ' host').name, m.role(tag + ' target').name
        area, meter = 'E291 ' + tag, 'E291Air' + tag
        t.areas[area] = square(*m.point(tag), 690)
        t.counters.append((meter, label))
        quiet.extend(('UNIT_CHANGE_OBJECT_STATUS', unit, 'NO_ATTACK', 1) for unit in (host, target))
        orders.extend([('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', host, target)])
        delete.append(('NAMED_DELETE', target))
        air = ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', p1, 3, 1, kindof('AIRCRAFT'), area)
        both_out.extend([air, ('NAMED_NOT_DESTROYED', target)])
        t.scripts += [Script('Test - sortie ' + tag, [('COUNTER', frame, 3, 600), air],
                             [('INCREMENT_COUNTER', bit, gate)]),
                      Script('Test - reset meter ' + tag, [], [('SET_COUNTER', meter, 0)], once=False)]
        for n in range(1, 11):
            t.scripts.append(Script(f'Test - {tag} live {n}', [(*air[:3], n, *air[4:])],
                                    [('SET_COUNTER', meter, n)], once=False))
    t.scripts[:0] = [
        Script('Test - frame', [('COUNTER', frame, 0, 1050)], [('INCREMENT_COUNTER', 1, frame)], once=False),
        Script('Test - quiet', [], [('MAP_REVEAL_ALL_PERM', p1), *quiet]),
        Script('Test - attack', [('COUNTER', frame, 2, 600)], orders),
        Script('Test - remove both targets', [('COUNTER', frame, 3, 600), *both_out],
               [*delete, ('INCREMENT_COUNTER', 4, gate)]),
    ]
    t.expect = [('完成帧', 0, 'ever==', 1050), ('出机位', 0, 'ever==', 7)]
    s8.watch(t, 77., .5)
    return t


def mission_producer(strip=False):
    """Keep E291's water positions and use retail carriers on both lanes."""
    m = Mission(name='CampDrone' + ('Off' if strip else 'On'), map=infiltrator_batch, ext=True)
    for lane, x in [('kill', -2510), ('keep', -1110)]:
        m.put('AlliedAntiStructureShip', 'ship', x, 400, role=lane + ' host', name=lane + ' carrier')
        m.put('SovietAntiAirShip', 'ship', x, 900, side='s1', role=lane + ' target', name=lane + ' target')
        m.waypoint(lane, lane + ' sortie', 'ship', x, 650)
    drone = 'AlliedAttackDrone'
    m.spawns.add(drone)
    if strip:
        source = Path(labpaths.SDK3) / 'SageXML/Allied/Units' / (drone + '.xml')
        xml, count = re.subn(r'<DieOnProducerDeathUpdate\b[^>]*/>', '', source.read_text(encoding='utf-8-sig'))
        assert count == 1
        m.assets.append(('DroneProducerControl.xml', xml, 'GameObject:' + drone))
        m.replaces.append('GameObject:' + drone)
    return m


def check_producer(m):
    """INFERRED from the XML: both lanes launch; only the stock drone dies when its producer dies.

    Keep both targets alive, and require aircraft in both regions before killing
    either host. Regional counts cannot identify the producer of an individual drone.
    """
    t, p1 = Test(), m.player('p1')
    frame, gate = 'E306Frame', 'E306Gate'
    t.counters = [(frame, '帧'), (gate, '门')]
    quiet, orders, both_out = [], [], []
    for lane, label in [('kill', '击毁侧'), ('keep', '存活侧')]:
        host, target = m.role(lane + ' host').name, m.role(lane + ' target').name
        t.areas[lane] = square(*m.point(lane), 690)
        quiet.extend(('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1) for name in (host, target))
        orders.extend([('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', host, target)])
        t.scripts.append(Script('Test - heal ' + lane, [('NAMED_NOT_DESTROYED', target)],
                                [('UNIT_SET_HEALTH', target, 100)], once=False))
        both_out.extend([('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', p1, 3, 1, kindof('AIRCRAFT'), lane),
                         ('NAMED_NOT_DESTROYED', target), ('NAMED_NOT_DESTROYED', host)])
        counted('E306Air' + lane, label, t, kind=kindof('AIRCRAFT'), area=lane, player=p1, most=10)
    t.scripts[:0] = [
        Script('Test - frame', [], [('INCREMENT_COUNTER', 1, frame)], once=False),
        Script('Test - quiet', [], [('MAP_REVEAL_ALL_PERM', p1), *quiet]),
        Script('Test - attack', [('COUNTER', frame, 2, 600)], orders),
        Script('Test - kill producer', [('COUNTER', frame, 3, 600), *both_out],
               [('NAMED_KILL', m.role('kill host').name), ('SET_COUNTER', gate, 1)]),
        Script('Test - producer dead', [('COUNTER', gate, 2, 1), ('NAMED_DESTROYED', m.role('kill host').name),
                                        ('NAMED_NOT_DESTROYED', m.role('keep host').name)],
               [('SET_COUNTER', gate, 2)]),
    ]
    t.expect = [('门', 0, 'ever==', 2)]
    s8.watch(t, 55., .5)
    return t


MISSION = {'engine_slaughter_e': mission, 'engine_slaughter_p': lambda: mission('CampSlaughterP', ('p1', 'p1')),
           'engine_slaughter_q': mission_q, 'engine_slaughter_r': mission_r, 'engine_slaughter_s': mission_s,
           'engine_slaughter_u': mission_u, 'engine_slaughter_v': mission_v, 'engine_slaughter_y': mission_y,
           'engine_droneproducer_on': mission_producer, 'engine_droneproducer_off': lambda: mission_producer(True)}
CHECKS = {'engine_slaughter_e': {'a': check, 'b': lambda m: check(m, corrected=True)},
          'engine_slaughter_p': {'p': check_p}, 'engine_slaughter_q': {'q': check_q},
          'engine_slaughter_r': {'r': check_r}, 'engine_slaughter_s': {'s': check_s, 't': lambda m: check_s(m, True)},
          'engine_slaughter_u': {'u': check_u},
          'engine_slaughter_v': {'v': check_v, 'w': lambda m: check_v(m, controlled=True)},
          'engine_slaughter_y': {'y': check_y},
          'engine_droneproducer_on': {'a': check_producer}, 'engine_droneproducer_off': {'a': check_producer}}
# Each arm's drones are counted by its own player, so the hosts (and targets) swap sides: a confound, held here
# as the one freedom; both arms read 0 (a negative baseline). Put both on p1 and count by area when E170 reopens.
CONTROL_ARMS = {'engine_slaughter_e': ('On', 'Off', 'side'), 'engine_slaughter_p': ('On', 'Off')}
