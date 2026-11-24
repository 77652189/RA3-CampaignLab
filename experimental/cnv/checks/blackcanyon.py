"""A2's map (maps/blackcanyon.py) on the bench: the four questions its draft left (work/mappage/a2/notes.md, r6).
The mission is the bare map; each check puts down what it asks about. Predictions (from SageXML and the map's
heights and walk grid, before the bench) are the expectations.

foot:  three Stingrays and three Bullfrogs in the river below the dam, ordered at the powerhouse on the level-1 ledge
       (river bed 220, ledge 340, crest 455). Predicted: the Stingrays (amphibious, tesla 125) come up the boat slip
       and hurt it; the Bullfrogs cannot (flak only, anti-air).
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
over by s21, the control by s19). foot FAIL, open: the powerhouse 100 all run, no ship in the pool or on the ledge --
cannot reach, or will not attack a neutral prop? camp FAIL, open: the Teslas seen on the east way at s29, the
Hammers in neither area -- the counters sample every 4 s and a fast tank crosses an area between two samples.
"""
from maps import blackcanyon
from parts import Mission, Obj, Script, Test
from model import counted, square

RAY, FROG, V4 = 'SovietAntiNavyShipTech1', 'SovietAntiAirShip', 'SovietAntiStructureVehicle'
HAMMER, TESLA, PLANT = 'SovietAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech2', 'SovietPowerPlant'
POWERHOUSE = blackcanyon.POWERHOUSE


def mission(name='CampCanyon'):
    return Mission(name=name, map=blackcanyon, spawns={RAY, FROG, HAMMER, TESLA})     # what the checks count


def _start(t, m, orders, at=4.0):
    t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                              ('SET_MILLISECOND_TIMER', 'Test Go', at)]),
                  Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], orders)]


def _plant(t, m, site, tag):
    name = f'UNIT - Test Plant {tag}'
    t.objects.append(Obj(PLANT, *m.site(site), side='p1', name=name, site=site))
    return name


def foot(m):
    t = Test()
    rays = [f'UNIT - Test Ray {k}' for k in range(3)]
    frogs = [f'UNIT - Test Frog {k}' for k in range(3)]
    for k, n in enumerate(rays):                        # the river at y 2400 runs x ~2600 .. 2860
        t.objects.append(Obj(RAY, 2690.0 + 50.0 * k, 2400.0, side='s1', name=n, site='st_foot', angle=1.5708))
    for k, n in enumerate(frogs):
        t.objects.append(Obj(FROG, 2700.0 + 60.0 * k, 2500.0, side='s1', name=n, site='st_foot', angle=1.5708))
    t.areas['Test Ledge'] = square(2650.0, 2910.0, 125.0)
    t.areas['Test Pool'] = square(2890.0, 2935.0, 100.0)
    counted('Test Foot hp', '厂房血', t, health=POWERHOUSE)
    counted('Test Ray ledge', '魟鱼上台', t, template=RAY, area='Test Ledge', player=m.player('s1'))
    counted('Test Ray pool', '魟鱼到池', t, template=RAY, area='Test Pool', player=m.player('s1'))
    counted('Test Frog pool', '牛蛙到池', t, template=FROG, area='Test Pool', player=m.player('s1'))
    _start(t, m, [('NAMED_ATTACK_NAMED', n, POWERHOUSE) for n in rays + frogs])
    t.expect += [('厂房血', 0, 'ever<=', 90)]
    t.bench = [('bench_watch', dict(seconds=70.0, every=5, sheet=False, lines=len(t.counters)))]
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
    s1 = m.player('s1')
    west, east = _plant(t, m, 'st_dam_w', 'West'), _plant(t, m, 'st_dam_e', 'East')
    orders = []
    for tpl, tag, target, dy in ((HAMMER, 'Hammer', west, -150.0), (TESLA, 'Tesla', east, 150.0)):
        for k in range(3):
            n = f'UNIT - Test {tag} {k}'
            t.objects.append(Obj(tpl, *m.site('sov_camp', -250.0 + 70.0 * k, dy), side='s1', name=n, site='sov_camp'))
            orders.append(('NAMED_ATTACK_NAMED', n, target))
    t.areas['Test Bridge'] = square(2885.0, 1700.0, 200.0)
    t.areas['Test East'] = square(3700.0, 2550.0, 250.0)
    for tpl, tag, word in ((HAMMER, '锤', 'Hammer'), (TESLA, '磁', 'Tesla')):
        counted(f'Test {word} bridge', f'{tag}过桥', t, template=tpl, area='Test Bridge', player=s1)
        counted(f'Test {word} east', f'{tag}走东', t, template=tpl, area='Test East', player=s1)
    _start(t, m, orders)
    t.expect += [('锤过桥', 0, 'ever>=', 1), ('磁走东', 0, 'ever>=', 1), ('磁过桥', 0, '==', 0)]
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


MISSION = {'canyon': mission}
CHECKS = {'canyon': {'foot': foot, 'v4': v4, 'camp': camp, 'crest': crest}}
