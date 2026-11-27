"""A1 toll plaza (E255 item 3, work/logs/a1_toll_cars/answer.md): do retail abandoned cars hold a convoy up, who drives
over them, how long they take to shoot away. On the range probe map, five lanes along +x, 500 apart (y 1000..3000 at
x 3800): the mover 250 west of the lane's middle, sent at 2 s to 250 east of it, HOLD_FIRE.

  a cars: a wall of neutral SM_Auto04 / SM_Auto03 / CC_Auto01 across the lane's middle (300 long, 2 apart, long side
    across). Movers: 1 the Ore Collector with CrusherLevel 0 (the convoy truck), 2 a conscript, 3 an IFV (1),
    4 a Guardian (20), 5 an Apocalypse (30).
  b open: a without the cars (the free drive).
  c booths: a's wall made of HV_TollBooth01. Movers 1 the zero truck, 2 a Guardian, 3 an Apocalypse.
  d fire: 1 the zero truck behind a's wall whose middle three cars are killed (NAMED_KILL) at 3.5 s (does it turn
    back to the straight way?); 2..5 a Guardian, a conscript, an IFV, a Hammer each 150 west of one lone car,
    NAMED_ATTACK_NAMED on it at 2 s (fire allowed); their 到时 is the frames until the car is destroyed.

Counters: 到时甲 lanes 1..3 (x1, x1000, x1e6) and 到时乙 lanes 4..5 the frames from the go until the mover first stood
within 40 of its goal (999 = never); 穿心 a digit a lane (10**(k-1)), latched: 1 once the mover stood within 50 of the
lane's middle; 车存 a digit a lane: how many of the middle three cars (d 2..5: the lone car) still stand.
Prediction from the data (BaseParkedCar: STRUCTURE CRUSHABLE_OBSTACLE, CrushableLevel 0, ActiveBody 300; crushed when
the crusher is strictly above): a -- 1 and 2 go round (穿心 0, later than b), 3..5 straight over (穿心 1, cars crushed);
c -- the booths (no STRUCTURE, UNATTACKABLE) hold nobody up.
"""
import math
import re

from maps import probe_range
from parts import Mission, Script, Test, square
from checks import engine_scripts8 as s8
from checks.engine_objectbatch import clone

ZERO = 'CNVA1TollTruck'
CONSCRIPT, IFV, GUARDIAN = 'SovietAntiInfantryInfantry', 'AlliedAntiInfantryVehicle', 'AlliedAntiVehicleVehicleTech1'
HAMMER, APOC = 'SovietAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech3'
# car: (half across the lane = along y, angle): the SM boxes are long in y at angle 0, CC's in x
CARS = {'SM_Auto04': (15.13, 0.0), 'SM_Auto03': (15.13, 0.0), 'CC_Auto01': (18.7, math.pi / 2)}
BOOTH = {'HV_TollBooth01': (9.6, 0.0)}
WALL, GAP, START, MIDDLE, RUN = 150.0, 2.0, 250.0, 3, 45.0
RUNS = {'a': ((ZERO, CONSCRIPT, IFV, GUARDIAN, APOC), CARS), 'b': ((ZERO, CONSCRIPT, IFV, GUARDIAN, APOC), None),
        'c': ((ZERO, GUARDIAN, APOC), BOOTH), 'd': ((ZERO, GUARDIAN, CONSCRIPT, IFV, HAMMER), CARS)}
# E256 blockers a player might shoot, one a lane: SM_Auto04 without CRUSHABLE_OBSTACLE, s1's SM_Auto04, three walls
NOCRUSH = 'CNVA1TollCar'
CAND = ({NOCRUSH: (15.13, 0.0)}, {'SM_Auto04': (15.13, 0.0)}, {'MJ_PalaceWall01': (30.0, 0.0)},
        {'KR_Wall01': (23.3, math.pi / 2)}, {'OD_Wall01': (63.9, math.pi / 2)})
SIDE = {2: 's1'}
RUNS |= {'e': ((ZERO,) * 5, CAND), 'f': ((GUARDIAN,) * 5, CAND), 'g': ((GUARDIAN,) * 5, CAND)}
# E256 h, g's positive control: a Guardian 150 west of one s1 thing a lane -- 1 a Hammer, the Guardian on HOLD_FIRE but
# ordered; 2 a Hammer, ordered; 3 a Hammer, no order (auto-acquire); 4 s1's SM_Auto04, 5 a neutral one, ordered.
# The Hammers hold fire. 伤 a digit a lane: how many of 100/75/50/25 % the target's health is under.
TANK = {HAMMER: (0.0, 0.0)}
RUNS['h'] = ((GUARDIAN,) * 5, (TANK, TANK, TANK, CAND[1], CAND[1]))
SIDES = {'e': SIDE, 'f': SIDE, 'g': SIDE, 'h': {1: 's1', 2: 's1', 3: 's1', 4: 's1'}}
LONE = {'d': (2, 3, 4, 5), 'g': (1, 2, 3, 4, 5), 'h': (1, 2, 3, 4, 5)}
# E256 i, OD_Wall01 again (e/f drove straight through it): 1 the zero truck at e's wall (angle pi/2), the camera on it;
# 2 the truck at the wall turned to 0 (the box's long side along the lane, so a thick block); 3 a Guardian at e's wall
OD = 'OD_Wall01'
RUNS['i'] = ((ZERO, ZERO, GUARDIAN), ({OD: (63.9, math.pi / 2)}, {OD: (9.47, 0.0)}, {OD: (63.9, math.pi / 2)}))
# E258 (mod A1): NOCRUSH given an ArmorSet -- BaseParkedCar has none and h's cars took no damage. The retail civilian
# structures' BaseCivilianStructureArmor: 100 % but SNIPER / MELEE 0 and EXPLOSIVE 125, so its 300 health reads as
# shots. j: a wall of them; 1 the truck, 2 a Guardian (held up still?); 3 the truck, 4 a Guardian, the middle three
# killed (NAMED_KILL) at 3 s; 5 the truck, killed at 5 s (on its way round by then): back to the straight way, when?
# k: one a lane, 1 a Guardian, 2 a conscript, 3 a Hammer ordered on it; 4 a Guardian not ordered (NOT_AUTOACQUIRABLE);
# 5 a Guardian ordered on NOCRUSH (no ArmorSet, h's control).
ARMORED = 'CNVA1TollArmCar'
ARM = {ARMORED: (15.13, 0.0)}
RUNS |= {'j': ((ZERO, GUARDIAN, ZERO, GUARDIAN, ZERO), ARM),
         'k': ((GUARDIAN, CONSCRIPT, HAMMER, GUARDIAN, GUARDIAN), (ARM,) * 4 + (CAND[0],))}
LONE['k'] = (1, 2, 3, 4, 5)
# l (j, k both read nothing): 1 a Guardian ordered on BARE (ARMORED without SIMPLE_OBJECT_PROP), 2 on an s1 ARMORED;
# 3..5 j's 3..5 with the middle three NAMED_DELETEd (no 3 s SlowDeath sinking): is it the wreck or no new path?
BARE = 'CNVA1TollBareCar'
RUNS['l'] = ((GUARDIAN, GUARDIAN, ZERO, GUARDIAN, ZERO), ({BARE: (15.13, 0.0)}, ARM, ARM, ARM, ARM))
LONE['l'], SIDES['l'] = (1, 2), {2: 's1'}
# m (E258's next step): the car on a retail base that takes damage -- SM_Auto04's model and box on
# BaseCivilianStructureNoGarrisonDestructible (MJ_PalaceWall01's base), 300 health, the ArmorSet replaced by
# BaseCivilianStructureArmor. 1 the truck, 2 a Guardian at a wall of them (held up still?); 3 a Guardian, 4 a Hammer,
# 5 a conscript ordered on one (how long to shoot away?).
CIV = 'CNVA1TollCivCar'
RUNS['m'] = ((ZERO, GUARDIAN, GUARDIAN, HAMMER, CONSCRIPT), {CIV: (15.13, 0.0)})
LONE['m'] = (3, 4, 5)
# o (m's lone cars took no damage, like every SM_Auto04 box so far): 1 a Guardian on the retail MJ_PalaceWall01 (its base,
# 3000 health: is any civilian structure hurt here?); 2 a Guardian, 4 a Hammer, 5 a conscript on CIVC (CIV with the
# box's ContactPointGeneration="STRUCTURE", MJ_PalaceWall01's); 3 a Guardian on CIV, the camera on it (does it fire?).
CIVC = 'CNVA1TollCivCarC'
RUNS['o'] = ((GUARDIAN, GUARDIAN, GUARDIAN, HAMMER, CONSCRIPT),
             ({'MJ_PalaceWall01': (30.0, 0.0)}, {CIVC: (15.13, 0.0)}, {CIV: (15.13, 0.0)}, {CIVC: (15.13, 0.0)},
              {CIVC: (15.13, 0.0)}))
LONE['o'] = (1, 2, 3, 4, 5)
# p (o's Guardian turned to the car and away, never fired; every target that took nothing is NOT_AUTOACQUIRABLE):
# CIVA = CIV with its base's KindOf less NOT_AUTOACQUIRABLE. 1 a Guardian, 2 a Hammer, 3 a conscript on CIVA, 4 a
# Guardian on an s1 CIVA, 5 a Guardian on CIV (o's 3 again).
CIVA = 'CNVA1TollCivCarA'
RUNS['p'] = ((GUARDIAN, GUARDIAN, CONSCRIPT, GUARDIAN, GUARDIAN), ({CIVA: (15.13, 0.0)},) * 4 + ({CIV: (15.13, 0.0)},))
LONE['p'], SIDES['p'] = (1, 2, 3, 4, 5), {4: 's1'}
# n: the middle three gone at 1 s, before the go (j / l took them away under movers already on their way): 1 the truck,
# 2 a Guardian, NAMED_DELETE; 3 the truck, NAMED_KILL (the wreck sinks for 3 s); 4 the truck, the whole wall deleted;
# 5 the truck, nothing taken away (the way round).
RUNS['n'] = ((ZERO, GUARDIAN, ZERO, ZERO, ZERO), ARM)
DEL, KIL = 'NAMED_DELETE', 'NAMED_KILL'
# lane: (seconds, action, every car of the wall or the middle three)
KILL = {'d': {1: (3.5, KIL, False)}, 'j': {3: (3.0, KIL, False), 4: (3.0, KIL, False), 5: (5.0, KIL, False)},
        'l': {3: (3.0, DEL, False), 4: (3.0, DEL, False), 5: (5.0, DEL, False)},
        'n': {1: (1.0, DEL, False), 2: (1.0, DEL, False), 3: (1.0, KIL, False), 4: (1.0, DEL, True)}}
IDLE = {('h', 3), ('k', 4)}
# q (E259's open end): the player's own order, given by the bench's clicks (no script order), 80 apart on one screen:
# a Guardian on 1 CIV with Ctrl + right click (force attack), 2 MJ_PalaceWall01 with Ctrl + right, 3 CIV with a plain
# right click, 4 a neutral CIVA with Ctrl + right; 5, 240 out (beyond the others' sight), on HOLD_FIRE, a plain right
# click on an s1 CIVA (the click's positive control). lane: (dy, ctrl, the target's pixel), in click order. The pixels
# are where q's first run drew them (calib's world point missed the cars by 15-25 px: those clicks hit the ground).
RUNS['q'] = ((GUARDIAN,) * 5, ({CIV: (15.13, 0.0)}, {'MJ_PalaceWall01': (30.0, 0.0)}, {CIV: (15.13, 0.0)},
                               {CIVA: (15.13, 0.0)}, {CIVA: (15.13, 0.0)}))
LONE['q'], SIDES['q'] = (1, 2, 3, 4, 5), {5: 's1'}
IDLE |= {('q', k) for k in LONE['q']}
# r (review 141: the simulator shoots s1's parked cars away, g / h / l's bench never did): five Guardians on HOLD_FIRE,
# each ordered on one s1 thing -- 1 CIV (NOT_AUTOACQUIRABLE alone), 2 CIVI (CIV with AUTO_ACQUIRABLE_BY_AI too, as every
# retail base structure), 3 BARE (BaseParkedCar less SIMPLE_OBJECT_PROP), 4 ARMI (ARMORED with AUTO_ACQUIRABLE_BY_AI),
# 5 CIVA (no NOT_AUTOACQUIRABLE, p 4's control). Is a script's order turned down by NOT_ without AUTO_ACQUIRABLE_BY_AI
# (1, 3 stand; 2, 4, 5 go) or by SIMPLE_OBJECT_PROP (4 stands)?
# s (E260's open end): a wall of neutral CIV, the middle three NAMED_KILLed at 1 s (KEEP_CLASSIFIED_WHEN_DEAD, the model
# stays): 1 the truck, 2 a Guardian; 3 the truck, NAMED_DELETEd; 4 the truck, 5 a Guardian, nothing taken away.
CIVI, ARMI = 'CNVA1TollCivCarI', 'CNVA1TollArmCarI'
RUNS['r'] = ((GUARDIAN,) * 5, ({CIV: (15.13, 0.0)}, {CIVI: (15.13, 0.0)}, {BARE: (15.13, 0.0)}, {ARMI: (15.13, 0.0)},
                               {CIVA: (15.13, 0.0)}))
LONE['r'], SIDES['r'] = (1, 2, 3, 4, 5), {k: 's1' for k in range(1, 6)}
RUNS['s'] = ((ZERO, GUARDIAN, ZERO, ZERO, GUARDIAN), {CIV: (15.13, 0.0)})
KILL['s'] = {1: (1.0, KIL, False), 2: (1.0, KIL, False), 3: (1.0, DEL, False)}
# E266 (who a retail prop holds up, work/logs/e266_prop_blocking.md): a's wall of one prop a lane, the half its box's
# minor side (no Shape: 5) so the row is closed either way the box lies. t / w a conscript, u / x the zero truck.
# 1 tree (topple), 2 bush (NO_COLLIDE, no Shape), 3 Japanese fence (simulated prop, no STRUCTURE), 4 cargo container
# and 5 big rock (BaseRockBig: STRUCTURE with NO_COLLIDE); w / x: 1 rock (CRUSHABLE_OBSTACLE), 2 bench (topple
# STRUCTURE), 3 bench (simulated prop), 4 lamp post (CRUSHABLE_OBSTACLE topple, no Shape), 5 fence (CRUSHABLE_OBSTACLE).
PROPS = (({'HB_Tree07': (3.4, 0.0)}, {'CC_BUSH02': (5.0, 0.0)}, {'TH_JAPANFENCE01': (5.3, math.pi / 2)},
          {'TH_CARGOCONTAINER05': (22.4, math.pi / 2)}, {'YU_LARGEROCKS02': (21.6, 0.0)}),
         ({'MY_ROCKS03': (30.0, math.pi / 2)}, {'GE_BENCH': (3.4, math.pi / 2)}, {'HB_BENCH01': (4.5, math.pi / 2)},
          {'TH_LAMPPOST04': (5.0, 0.0)}, {'ST_SOVIETFENCE01': (2.8, math.pi / 2)}))
RUNS |= {r: ((who,) * 5, PROPS[p]) for r, who, p in (('t', CONSCRIPT, 0), ('u', ZERO, 0), ('w', CONSCRIPT, 1),
                                                     ('x', ZERO, 1))}
HOLD = {'h': (1,), 'q': (5,), 'r': (1, 2, 3, 4, 5)}
CLICK = {5: (240.0, False, (726, 103)), 1: (-160.0, True, (759, 505)), 2: (-80.0, True, (756, 365)),
         3: (0.0, False, (743, 311)), 4: (80.0, True, (736, 233))}


def _kinds(kinds, k):
    return kinds[k - 1] if isinstance(kinds, tuple) else kinds


def _dy(k, run=''):
    return 1600.0 + CLICK[k][0] if run == 'q' else 600.0 + 500.0 * (k - 1)


def _wall(kinds):
    """[(template, y, angle)] across -WALL..WALL, the kinds in turn, GAP between the boxes."""
    out, y, names = [], -WALL, list(kinds)
    while True:
        t = names[len(out) % len(names)]
        half, ang = kinds[t]
        if y + 2 * half > WALL:
            return out
        out.append((t, y + half, ang))
        y += 2 * half + GAP


def _middle(wall):
    return sorted(range(len(wall)), key=lambda i: abs(wall[i][1]))[:MIDDLE]


def mission(run):
    movers, kinds = RUNS[run]
    m = Mission(name='CampA1Toll' + run.upper(), map=probe_range, units=[])
    truck = clone('Soviet/Units/SovietMiner.xml', 'SovietMiner', ZERO)
    for old, new in (('CrusherLevel="20"', 'CrusherLevel="0"'), ('ExtraCrushLevels CrusherLevel="1"',
                                                                  'ExtraCrushLevels CrusherLevel="0"')):
        assert truck.xml.count(old) == 1, old
        truck.xml = truck.xml.replace(old, new)
    truck.xml, n = re.subn(r'\s*<GameObject\s+id="SovietMiner_Naval".*?</GameObject>', '', truck.xml, flags=re.S)
    assert n == 1
    m.units.append(truck)
    used = {t for lane in (kinds if isinstance(kinds, tuple) else (kinds,)) for t in lane or {}}
    for ident in sorted({CIV, CIVC, CIVA, CIVI} & used):
        car = clone('Civilian/Santa_Monica_SA/Props/SM_Auto04.xml', 'SM_Auto04', ident)
        if ident == CIVC:
            car.xml = car.xml.replace('<Shape ', '<Shape ContactPointGeneration="STRUCTURE" ', 1)
        base = 'BaseCivilianStructureNoGarrisonDestructible'
        kindof = (' KindOf="SELECTABLE STRUCTURE IMMOBILE CAN_CAST_REFLECTIONS AUTO_RALLYPOINT COVER KEEP_CLASSIFIED_WHEN_DEAD'
                  ' CIVILIAN_BUILDING RESIST_EMP ALWAYS_VISIBLE_IN_RADAR'
                  + ' NOT_AUTOACQUIRABLE AUTO_ACQUIRABLE_BY_AI' * (ident == CIVI) + '"') if ident in (CIVA, CIVI) else ''
        car.xml = car.xml.replace('BaseObjects/BaseParkedCar.xml', f'BaseObjects/{base}.xml', 1)
        car.xml = car.xml.replace('inheritFrom="BaseParkedCar"', f'inheritFrom="{base}"{kindof}', 1)
        car.xml = car.xml.replace('<Geometry', '<ArmorSet id="DefaultArmor" xai:joinAction="Replace" xmlns:xai='
                                  '"uri:ea.com:eala:asset:instance" Armor="BaseCivilianStructureArmor" DamageFX='
                                  '"GenericStructureDamageFX" />\n    <Body><ActiveBody id="DefaultBody" MaxHealth="300" />'
                                  '</Body>\n    <Geometry', 1)
        assert car.xml.count(base) == 2 and 'MaxHealth="300"' in car.xml
        m.units.append(car)
    for ident in sorted({NOCRUSH, ARMORED, BARE, ARMI} & used):
        car = clone('Civilian/Santa_Monica_SA/Props/SM_Auto04.xml', 'SM_Auto04', ident)
        prop = '' if ident == BARE else ' SIMPLE_OBJECT_PROP' + ' AUTO_ACQUIRABLE_BY_AI' * (ident == ARMI)
        car.xml = car.xml.replace('inheritFrom="BaseParkedCar"', 'inheritFrom="BaseParkedCar" KindOf="IMMOBILE '
                                  f'NOT_AUTOACQUIRABLE STRUCTURE CAN_SEE_THROUGH_STRUCTURE RESIST_EMP{prop} '
                                  'CLEARED_BY_BUILD"', 1)
        if ident != NOCRUSH:
            car.xml = car.xml.replace('<Geometry', '<ArmorSet Armor="BaseCivilianStructureArmor" />\n    <Geometry', 1)
        assert 'KindOf="IMMOBILE' in car.xml and (ident == NOCRUSH or '<ArmorSet' in car.xml)
        m.units.append(car)
    for k, mover in enumerate(movers, 1):
        lone, lane, dy = k in LONE.get(run, ()), _kinds(kinds, k), _dy(k, run)
        m.put(mover, 'order gun', -150.0 if lone else -START, dy, angle=0.0, role=f'mover {k}', name=f'A1T Mover {k}')
        first = next(iter(lane or {}), None)
        wall = [(first, 0.0, lane[first][1])] if lone else _wall(lane) if kinds else []
        side = SIDES.get(run, {}).get(k, 'neutral')
        for i, (t, y, ang) in enumerate(wall):
            m.put(t, 'order gun', 0.0, dy + (0.0 if lone else y), angle=ang, side=side, role=f'car {k} {i}',
                  name=f'A1T Car {k} {i}')
    return m


def check(m, run, view=False):
    movers, kinds = RUNS[run]
    t = Test()
    x, y = m.site('order gun')
    lanes = range(1, len(movers) + 1)
    hold = [('UNIT_SET_STANCE', m.role(f'mover {k}').name, 3) for k in lanes if k not in LONE.get(run, ())]
    if run == 'h':
        hold += [('UNIT_SET_STANCE', m.role(f'car {k} 0').name, 3) for k in (1, 2, 3)]
    hold += [('UNIT_SET_STANCE', m.role(f'mover {k}').name, 3) for k in HOLD.get(run, ())]
    t.scripts.append(Script('Test - A1T start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))] + hold))
    go, going = [('SET_FLAG', 'A1T Going', 1)], ('FLAG', 'A1T Going', 1)
    for k in lanes:
        name = m.role(f'mover {k}').name
        t.areas[f'A1T Mid {k}'] = square(x, y + _dy(k, run), 50.0)
        if k in LONE.get(run, ()):
            if (run, k) not in IDLE:
                go.append(('NAMED_ATTACK_NAMED', name, m.role(f'car {k} 0').name))
            t.scripts.append(Script(f'Test - A1T at {k}', [('NAMED_DESTROYED', m.role(f'car {k} 0').name)],
                                    [('SET_FLAG', f'A1T At {k}', 1)]))
            continue
        t.waypoints[f'A1T Goal {k}'] = (x + START, y + _dy(k))
        t.areas[f'A1T Goal {k}'] = square(x + START, y + _dy(k), 40.0)
        go.append(('MOVE_NAMED_UNIT_TO', name, f'A1T Goal {k}'))
        t.scripts.append(Script(f'Test - A1T at {k}', [('NAMED_INSIDE_AREA', name, f'A1T Goal {k}')],
                                [('SET_FLAG', f'A1T At {k}', 1)]))
    s8.at(t, 'go', 2., go)
    if view or run in ('i', 'o', 'p', 'q'):     # a's v: the camera on lane 1's middle (o: 3's), to see the movers
        t.waypoints['A1T View'] = (x - 75.0 * (run in 'opq'),     # q: 40 south, its lanes 85..520 px down the screen
                                   y + _dy(3 if run in 'opq' else 1, run) - 40.0 * (run == 'q'))
        s8.at(t, 'view', 1., [('MOVE_CAMERA_TO', 'A1T View', 0.5, 0.0, 1.0, 1.0)])
    for k, (secs, act, every) in KILL.get(run, {}).items():
        wall = _wall(_kinds(kinds, k))
        s8.at(t, f'kill {k}', secs, [(act, m.role(f'car {k} {i}').name)
                                     for i in (range(len(wall)) if every else _middle(wall))])
    for label, ks in (('到时甲', (1, 2, 3)), ('到时乙', (4, 5))):
        counter = 'A1TTime' + ('A' if 1 in ks else 'B')
        t.counters.append((counter, label))
        for j, k in enumerate(ks):
            if k in lanes:
                t.scripts.append(Script(f'Test - {counter} {k}', [going, ('FLAG', f'A1T At {k}', 0)],
                                        [('INCREMENT_COUNTER', 1000 ** j, counter)], once=False))
    if run in ('h', 'k', 'm', 'o', 'p', 'q', 'r'):   # lone movers' 穿心 says nothing: 伤 takes its line (m keeps both)
        s8.total(t, 'A1THurt', '伤', [(10 ** (k - 1), ('UNIT_HEALTH', m.role(f'car {k} 0').name, 0, pct))
                                     for k in lanes if k in LONE[run] for pct in (100, 75, 50, 25)])
    if run not in ('h', 'k', 'o', 'p', 'q', 'r'):
        t.counters.append(('A1TMid', '穿心'))
    t.scripts += [Script(f'Test - A1T mid {k}', [going, ('NAMED_INSIDE_AREA', m.role(f'mover {k}').name, f'A1T Mid {k}')],
                         [('INCREMENT_COUNTER', 10 ** (k - 1), 'A1TMid')]) for k in lanes]
    if kinds and run not in 'mopq':             # four lines fit: m's 到时 says when its lone cars go
        parts = []
        for k in lanes:
            idx = [0] if k in LONE.get(run, ()) else _middle(_wall(_kinds(kinds, k)))
            parts += [(10 ** (k - 1), ('NAMED_NOT_DESTROYED', m.role(f'car {k} {i}').name)) for i in idx]
        s8.total(t, 'A1TCars', '车存', parts)
    s8.watch(t, RUN, .5)
    if run == 'q':                              # engine_healcrate c's way: the clicks after the camera is there
        watch, (vx, vy) = t.bench[0][1], t.waypoints['A1T View']
        t.bench = [('bench_watch', dict(watch, seconds=2.0)), ('bench_view', dict(x=vx, y=vy, look=True))]
        for k, (dy, ctrl, (u, v)) in CLICK.items():
            my = y + _dy(k, run)
            t.bench += [('bench_box', dict(x0=x - 180, y0=my - 30, x1=x - 120, y1=my + 30, look=True)),
                        ('bench_click', dict(x=u, y=v, world=False, right=True, ctrl=ctrl, look=True))]
        t.bench.append(('bench_watch', dict(watch, seconds=RUN - 2.0)))
    return t


MISSION = {f'engine_a1toll{r}': (lambda r=r: mission(r)) for r in RUNS}
CHECKS = {f"engine_a1toll{r}": {r: (lambda m, r=r: check(m, r))} for r in RUNS}
CHECKS["engine_a1tolla"]["v"] = lambda m: check(m, "a", True)
