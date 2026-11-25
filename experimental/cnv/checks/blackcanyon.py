"""A2's map (maps/blackcanyon.py) on the bench: the four questions its draft left (work/mappage/a2/notes.md, r6).
The mission is the bare map; each check puts down what it asks about. Predictions (from SageXML and the map's
heights and walk grid, before the bench) are the expectations.

foot:  Stingrays in the river below the dam: three ordered at the powerhouse on the level-1 ledge (river bed 220,
       ledge 340, crest 455), two at a player plant beside it, two only moved to the tailrace pool. Predicted: they
       reach the pool (amphibious) and hurt both from it or up the boat slip (tesla 125).
v4:    two V4s on the Arizona overlook (570 high), one ordered at a plant on the crest's east section, one at the
       west's. Predicted: rocket range 500 (minimum 200); east is 516 from the overlook's middle, ~380 from its west
       rim, so the first fires from up there; west is ~590 even from the rim, so the second drives off.
camp:  three Hammers from the Soviet camp at a plant on crest west, three Tesla tanks at one on crest east.
       attack_routes (11-24): to west 3999 by the bridge, ~4000 round the east side (a tie, the bridge by a hair);
       to east 3766 round the east side, ~4230 by the bridge. Predicted: Hammers over the bridge, Teslas round east.
crest: eight Hammers moved across the crest east to west (760), eight on open ground the same length (the
       control). The crest is 80 walkable across its whole run, both ends too (the rect is 130, the cliff takes 25 a
       side). Predicted: all eight get over, two abreast, the tail later than the control's.
Bench 2026-11-24: v4 PASS (east 37 by s13 from up there; the west one off the overlook at s9). crest PASS (all eight
over by s21, the control by s19). foot r7 (the powerhouse still neutral): the movers in the pool, the plant 100 -> 4
shot from the water, the powerhouse's three never set out (100) -- a neutral prop is no one's target, so the map
gives it to the player. camp r7: the Teslas round east, Hammer 0 in the camp all run -- they stood in a warehouse
(4200, 780), moved west of it. (The counter reader misreads a long line's last digit, 1 as 7: read the frames.)
r8, the dam the player's Allied plants (readings: blackcanyon.readings.toml): ath, the Athena on an enemy plant 50
beside the player's own: both 100 -> 25 -> 2 (its beam hurts SELF ALLIES too). sell: CANNOT_BE_SOLD set, SELL_OBJECT
still sells it. roads (plan-wave team orders): conscripts over the bridge at crest west, Hammers down the bend at crest
east, both shot down. last: lake Stingrays land at the beach and drive to crest west; V4s hit east from the road.
"""
from parts import Obj, Script, Test
from model import counted, square, status

RAY, V4 = 'SovietAntiNavyShipTech1', 'SovietAntiStructureVehicle'
HAMMER, TESLA, PLANT = 'SovietAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech2', 'SovietPowerPlant'
DAM, ATHENA, CONSCRIPT = 'AlliedPowerPlant', 'AlliedAntiStructureVehicle', 'SovietAntiInfantryInfantry'
NOSELL = 'CNV_NoSell_AlliedPowerPlant'                 # units/unsellable.py, the bench mission carries it


def _start(t, m, orders, at=4.0):
    t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                              ('SET_MILLISECOND_TIMER', 'Test Go', at)]),
                  Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], orders)]


def _plant(t, m, site, tag, tpl=PLANT):
    name = f'UNIT - Test Plant {tag}'
    t.objects.append(Obj(tpl, *m.site(site), side='p1', name=name, site=site))
    return name


def _seen(t, counter, label, marks):
    """marks: (names, area) a digit, the first one the ones: that digit turns 1 the first frame any of the names
    stands in the area and never goes back (a 4 s sample misses a fast tank; only four counter lines fit)."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - seen {counter} zero', [], [('SET_COUNTER', counter, 0)]))
    for d, (names, area) in enumerate(marks):
        flag = f'Test Seen {counter} {d}'
        t.scripts += [Script(f'{flag} {k}', [('NAMED_INSIDE_AREA', n, area)], [('SET_FLAG', flag, 1)])
                      for k, n in enumerate(names)]
        t.scripts.append(Script(f'{flag} add', [('FLAG', flag, 1)], [('INCREMENT_COUNTER', 10 ** d, counter)]))


def foot(m):
    t = Test()
    hit, shoot, go = ([f'UNIT - Test Ray {tag} {k}' for k in range(n)]
                      for tag, n in (('Hit', 3), ('Plant', 2), ('Go', 2)))
    for k, n in enumerate(hit + shoot + go):            # the river at y 2400 .. 2500 runs x ~2600 .. 2860
        t.objects.append(Obj(RAY, 2660.0 + 55.0 * (k % 4), 2400.0 + 80.0 * (k // 4), side='s1', name=n,
                             site='st_foot', angle=1.5708))
    plant = 'UNIT - Test Plant Ledge'                   # an enemy on the ledge by the slip's top, by the powerhouse
    t.objects.append(Obj(PLANT, 2715.0, 2850.0, side='p1', name=plant, site='st_foot'))
    t.waypoints['Test Pool'] = (2890.0, 2935.0)
    t.areas['Test Ledge'] = square(2650.0, 2910.0, 125.0)
    t.areas['Test Pool'] = square(2890.0, 2935.0, 100.0)
    counted('Test Foot hp', '厂房血', t, health=m.map.POWERHOUSE)
    counted('Test Plant hp', '电厂血', t, health=plant)
    _seen(t, 'Test Move', '移组 池/台', [(go, 'Test Pool'), (go, 'Test Ledge')])     # not 'Test Go': the timer's
    _seen(t, 'Test Hit', '打组 厂池/厂台/电池/电台', [(hit, 'Test Pool'), (hit, 'Test Ledge'),
                                                    (shoot, 'Test Pool'), (shoot, 'Test Ledge')])
    _start(t, m, [('NAMED_ATTACK_NAMED', n, m.map.POWERHOUSE) for n in hit] +
           [('NAMED_ATTACK_NAMED', n, plant) for n in shoot] + [('MOVE_NAMED_UNIT_TO', n, 'Test Pool') for n in go])
    # the powerhouse is a neutral prop again (r9; the low section is the plant): no one's target, as r7 read it
    t.expect += [('移组 池/台', 0, 'ever>=', 1), ('电厂血', 0, 'ever<=', 90), ('厂房血', 0, '==', 100)]
    t.bench = [('bench_watch', dict(seconds=90.0, every=5, sheet=False, lines=len(t.counters)))]
    return t


def v4(m):
    t = Test()
    east, west = _plant(t, m, 'st_dam_e', 'East'), _plant(t, m, 'st_dam_w', 'West')
    ve, vw = 'UNIT - Test V4 East', 'UNIT - Test V4 West'
    t.objects += [Obj(V4, *m.site('overlook', 0.0, 50.0), side='s1', name=ve, site='overlook', angle=3.1416),
                  Obj(V4, *m.site('overlook', 0.0, -50.0), side='s1', name=vw, site='overlook', angle=3.1416)]
    t.areas['Test Overlook'] = square(*m.site('overlook'), 150.0)
    counted('Test East hp', '东段血', t, health=east)
    counted('Test West hp', '西段血', t, health=west)
    counted('Test V4e up', 'V4东在台上', t, named=ve, area='Test Overlook')
    counted('Test V4w up', 'V4西在台上', t, named=vw, area='Test Overlook')
    _start(t, m, [('NAMED_ATTACK_NAMED', ve, east), ('NAMED_ATTACK_NAMED', vw, west)])
    t.expect += [('东段血', 0, 'ever<=', 90), ('V4东在台上', 0, '==', 1), ('V4西在台上', 8, 'ever==', 0)]
    t.bench = [('bench_watch', dict(seconds=60.0, every=4, sheet=False, lines=len(t.counters)))]
    return t


def camp(m):
    t = Test()
    west, east = _plant(t, m, 'st_dam_w', 'West'), _plant(t, m, 'st_dam_e', 'East')
    orders = []
    for tpl, tag, target, dy in ((HAMMER, 'Hammer', west, -150.0), (TESLA, 'Tesla', east, 150.0)):
        for k in range(3):
            n = f'UNIT - Test {tag} {k}'
            t.objects.append(Obj(tpl, *m.site('sov_camp', -450.0 + 70.0 * k, dy), side='s1', name=n, site='sov_camp'))
            orders.append(('NAMED_ATTACK_NAMED', n, target))
    t.areas['Test Bridge W'] = square(2480.0, 1700.0, 150.0)
    t.areas['Test Bridge'] = square(2885.0, 1700.0, 200.0)
    t.areas['Test East'] = square(3700.0, 2550.0, 250.0)
    for tag, word in (('锤', 'Hammer'), ('磁', 'Tesla')):
        names = [f'UNIT - Test {word} {k}' for k in range(3)]
        _seen(t, f'Test {word}', f'{tag} 桥西/桥/东', [(names, a) for a in ('Test Bridge W', 'Test Bridge', 'Test East')])
    t.areas['Test Camp'] = square(*m.site('sov_camp'), 400.0)
    counted('Test Hammer home', '锤0在营', t, named='UNIT - Test Hammer 0', area='Test Camp')
    counted('Test West hp', '西段血', t, health=west)
    _start(t, m, orders)                               # monotone: <= 11 all run = never east, <= 100 = never on the bridge
    t.expect += [('锤 桥西/桥/东', 0, 'ever==', 11), ('锤 桥西/桥/东', 0, '<=', 11),
                 ('磁 桥西/桥/东', 0, 'ever==', 100), ('磁 桥西/桥/东', 0, '<=', 100)]
    t.bench = [('bench_watch', dict(seconds=110.0, every=4, sheet=False, lines=len(t.counters)))]
    return t


def crest(m):
    t = Test()
    t.waypoints['Test Crest End'] = (2420.0, 3085.0)
    t.waypoints['Test Flat End'] = (3180.0, 2450.0)
    orders = []
    for k in range(8):                                  # a 4 x 2 block behind the start of each lane
        dx, dy = 60.0 * (k // 2), 50.0 * (k % 2) - 25.0
        for lane, (x, y), goal, site in (('Crest', (3180.0, 3085.0), 'Test Crest End', 'st_dam_e'),
                                         ('Flat', (3940.0, 2450.0), 'Test Flat End', 'st_bend')):
            n = f'UNIT - Test {lane} {k}'
            t.objects.append(Obj(HAMMER, x + dx, y + dy, side='p1', name=n, site=site, angle=3.1416))
            orders.append(('MOVE_NAMED_UNIT_TO', n, goal))
    t.areas['Test Crest End'] = square(2420.0, 3085.0, 110.0)
    t.areas['Test Flat End'] = square(3180.0, 2450.0, 110.0)
    counted('Test Crest over', '坝上组到', t, template=HAMMER, area='Test Crest End')
    counted('Test Flat over', '平地组到', t, template=HAMMER, area='Test Flat End')
    _start(t, m, orders)
    t.expect += [('坝上组到', 0, 'ever>=', 8), ('平地组到', 0, 'ever>=', 8)]
    t.bench = [('bench_watch', dict(seconds=60.0, every=2, sheet=False, lines=len(t.counters)))]
    return t


def athena(m):
    t = Test()
    dam = _plant(t, m, 'st_dam_w', 'Dam', DAM)
    x, y = m.site('st_dam_w')
    foe, gun = 'UNIT - Test Foe Plant', 'UNIT - Test Athena'
    t.objects += [Obj(PLANT, x, y + 50.0, side='s1', name=foe, site='st_dam_w'),
                  Obj(ATHENA, x - 350.0, y, side='p1', name=gun, site='st_dam_w')]
    counted('Test Dam hp', '坝血', t, health=dam)
    counted('Test Foe hp', '靶血', t, health=foe)
    _start(t, m, [('NAMED_ATTACK_NAMED', gun, foe)], at=6.0)
    t.expect += [('靶血', 0, 'ever<=', 50), ('坝血', 0, 'ever<=', 90)]
    t.bench = [('bench_watch', dict(seconds=50.0, every=5, sheet=False, lines=len(t.counters)))]
    return t


def sell(m):
    t = Test()
    p1 = m.player('p1')
    kept, sold = _plant(t, m, 'st_dam_w', 'Kept', DAM), _plant(t, m, 'st_dam_e', 'Sold', DAM)
    t.counters.append(('Test Alive', '存活 留/卖'))      # a digit each, the kept one the ones
    t.scripts.append(Script('Test - alive zero', [], [('SET_COUNTER', 'Test Alive', 0)], once=False))
    t.scripts += [Script(f'Test - alive {k}', [('NAMED_NOT_DESTROYED', n)], [('INCREMENT_COUNTER', 10 ** k, 'Test Alive')],
                         once=False) for k, n in enumerate((kept, sold))]
    counted('Test Locked', '不能卖数', t, status=status('CANNOT_BE_SOLD'))
    t.counters.append(('Test Money', '资金'))
    t.scripts += [Script('Test - lock', [], [('UNIT_CHANGE_OBJECT_STATUS', kept, 'CANNOT_BE_SOLD', 1),
                                             ('PLAYER_SET_MONEY', p1, 2000)]),
                  Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'Test Money')], once=False)]
    _start(t, m, [('SELL_OBJECT', kept), ('SELL_OBJECT', sold)])
    t.expect += [('存活 留/卖', 1, '==', 11, 3), ('不能卖数', 0, 'ever==', 1), ('存活 留/卖', 8, '==', 1),
                 ('资金', 8, '==', 2400)]
    t.bench = [('bench_watch', dict(seconds=16.0, every=2, sheet=False, lines=len(t.counters)))]
    return t


def lock(m):
    """sell again, the kept one the plant's copy with KindOf +NOT_SELLABLE (units/unsellable.py), no status set."""
    t = Test()
    p1 = m.player('p1')
    kept, sold = _plant(t, m, 'st_dam_w', 'Kept', NOSELL), _plant(t, m, 'st_dam_e', 'Sold', DAM)
    t.counters += [('Test Alive', '存活 留/卖'), ('Test Money', '资金')]      # a digit each, the kept one the ones
    t.scripts += [Script('Test - alive zero', [], [('SET_COUNTER', 'Test Alive', 0)], once=False),
                  Script('Test - money set', [], [('PLAYER_SET_MONEY', p1, 2000)]),
                  Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'Test Money')], once=False)]
    t.scripts += [Script(f'Test - alive {k}', [('NAMED_NOT_DESTROYED', n)], [('INCREMENT_COUNTER', 10 ** k, 'Test Alive')],
                         once=False) for k, n in enumerate((kept, sold))]
    _start(t, m, [('SELL_OBJECT', kept), ('SELL_OBJECT', sold)])
    t.expect += [('存活 留/卖', 1, '==', 11, 3), ('存活 留/卖', 8, '==', 1), ('资金', 8, '==', 2400)]
    t.bench = [('bench_watch', dict(seconds=16.0, every=2, sheet=False, lines=len(t.counters)))]
    return t


def _raid(t, m, groups, areas, seen):
    """groups: (template, tag, count, site, dx, dy, target) each one team ordered like a plan wave (TEAM_ATTACK_NAMED);
    seen: (label, tag, [area, ...]) a _seen line. via (an eighth item, a site): first moved there, the attack once
    one of them is inside it (as the plan's 先到)."""
    orders, names = [], {}
    for tpl, tag, n, site, dx, dy, target, *via in groups:
        names[tag] = [f'UNIT - Test {tag} {k}' for k in range(n)]
        t.objects += [Obj(tpl, *m.site(site, dx + 40.0 * (k % 4), dy + 40.0 * (k // 4)), side='s1', name=u, site=site)
                      for k, u in enumerate(names[tag])]
        if not via:
            orders += m.order('attack', names[tag], target, 's1')
            continue
        t.waypoints[f'Test Via {tag}'] = m.site(via[0])
        t.areas[f'Test Via {tag}'] = square(*m.site(via[0]), 150.0)
        orders += m.order('move', names[tag], f'Test Via {tag}', 's1')
        t.scripts += [Script(f'Test - via {tag} {k}', [('NAMED_INSIDE_AREA', u, f'Test Via {tag}')],
                             m.order('attack', names[tag], target, 's1')) for k, u in enumerate(names[tag])]
    t.areas.update(areas)
    for label, tag, where in seen:
        _seen(t, f'Test {tag}', label, [(names[tag], a) for a in where])
    _start(t, m, orders)


def roads(m):
    t = Test()
    w, e = _plant(t, m, 'st_dam_w', 'West', DAM), _plant(t, m, 'st_dam_e', 'East', DAM)
    counted('Test West hp', '西段血', t, health=w)
    counted('Test East hp', '东段血', t, health=e)
    _raid(t, m, [(CONSCRIPT, 'Conscript', 5, 'sov_camp', -450.0, -150.0, w), (HAMMER, 'Hammer', 3, 'sov_east', -120.0, 0.0, e)],
          {'Test Bridge': square(2885.0, 1700.0, 200.0), 'Test East': square(3700.0, 2550.0, 250.0),
           'Test Bend': square(*m.site('st_bend'), 250.0)},
          [('动 桥/东', 'Conscript', ['Test Bridge', 'Test East']), ('锤 长坡', 'Hammer', ['Test Bend'])])
    t.expect += [('西段血', 0, 'ever<=', 90), ('东段血', 0, 'ever<=', 90), ('动 桥/东', 0, 'ever==', 1),
                 ('动 桥/东', 0, '<=', 1), ('锤 长坡', 0, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=200.0, every=5, sheet=False, lines=len(t.counters)))]
    return t


def last(m):
    t = Test()
    w, e = _plant(t, m, 'st_dam_w', 'West', DAM), _plant(t, m, 'st_dam_e', 'East', DAM)
    counted('Test West hp', '西段血', t, health=w)
    counted('Test East hp', '东段血', t, health=e)
    _raid(t, m, [(V4, 'V4', 2, 'sov_east', -120.0, 0.0, e), (RAY, 'Ray', 3, 'sov_lake', -60.0, 0.0, w)],
          {'Test Overlook': square(*m.site('overlook'), 150.0), 'Test Face': square(2660.0, 3260.0, 150.0),
           'Test Beach': square(*m.site('st_beach'), 250.0)},
          [('V4 台上', 'V4', ['Test Overlook']), ('魟 坝面/湖滩', 'Ray', ['Test Face', 'Test Beach'])])
    t.expect += [('东段血', 0, 'ever<=', 90), ('西段血', 0, 'ever<=', 90), ('魟 坝面/湖滩', 0, 'ever==', 1),
                 ('魟 坝面/湖滩', 0, '<=', 1)]
    t.bench = [('bench_watch', dict(seconds=150.0, every=5, sheet=False, lines=len(t.counters)))]
    return t


def perch(m):
    """last's V4s as the plan's 先到 sends them: moved to the overlook first, the attack on crest east from there."""
    t = Test()
    e = _plant(t, m, 'st_dam_e', 'East', DAM)
    counted('Test East hp', '东段血', t, health=e)
    counted('Test East up', '东段在', t, owner=e)   # bench r9: the plant went s51-s56 with 东段血 still 100 (frozen)
    _raid(t, m, [(V4, 'V4', 2, 'sov_east', -120.0, 0.0, e, 'overlook')], {'Test Overlook': square(*m.site('overlook'), 150.0)},
          [('V4 台上', 'V4', ['Test Overlook'])])
    t.expect += [('V4 台上', 0, 'ever==', 1), ('东段在', 0, 'ever==', 0)]
    t.bench = [('bench_watch', dict(seconds=120.0, every=5, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {'canyon': {'foot': foot, 'v4': v4, 'camp': camp, 'crest': crest, 'ath': athena, 'sell': sell,
                     'roads': roads, 'last': last, 'lock': lock, 'perch': perch}}
