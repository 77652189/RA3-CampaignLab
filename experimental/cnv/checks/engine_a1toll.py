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


def _dy(k):
    return 600.0 + 500.0 * (k - 1)


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
    for k, mover in enumerate(movers, 1):
        lone = run == 'd' and k > 1
        m.put(mover, 'order gun', -150.0 if lone else -START, _dy(k), angle=0.0, role=f'mover {k}', name=f'A1T Mover {k}')
        wall = [('SM_Auto04', 0.0, 0.0)] if lone else _wall(kinds) if kinds else []
        for i, (t, y, ang) in enumerate(wall):
            m.put(t, 'order gun', 0.0, _dy(k) + y, angle=ang, side='neutral', role=f'car {k} {i}', name=f'A1T Car {k} {i}')
    return m


def check(m, run, view=False):
    movers, kinds = RUNS[run]
    t = Test()
    x, y = m.site('order gun')
    lanes = range(1, len(movers) + 1)
    hold = [('UNIT_SET_STANCE', m.role(f'mover {k}').name, 3) for k in lanes if not (run == 'd' and k > 1)]
    t.scripts.append(Script('Test - A1T start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))] + hold))
    go, going = [('SET_FLAG', 'A1T Going', 1)], ('FLAG', 'A1T Going', 1)
    for k in lanes:
        name = m.role(f'mover {k}').name
        t.areas[f'A1T Mid {k}'] = square(x, y + _dy(k), 50.0)
        if run == 'd' and k > 1:
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
    if view:                                    # a's v: the camera on lane 1's middle, to see the truck at the cars
        t.waypoints['A1T View'] = (x, y + _dy(1))
        s8.at(t, 'view', 1., [('MOVE_CAMERA_TO', 'A1T View', 0.5, 0.0, 1.0, 1.0)])
    if run == 'd':
        kill = [('NAMED_KILL', m.role(f'car 1 {i}').name) for i in _middle(_wall(kinds))]
        s8.at(t, 'kill', 3.5, kill)
    for label, ks in (('到时甲', (1, 2, 3)), ('到时乙', (4, 5))):
        counter = 'A1TTime' + ('A' if 1 in ks else 'B')
        t.counters.append((counter, label))
        for j, k in enumerate(ks):
            if k in lanes:
                t.scripts.append(Script(f'Test - {counter} {k}', [going, ('FLAG', f'A1T At {k}', 0)],
                                        [('INCREMENT_COUNTER', 1000 ** j, counter)], once=False))
    t.counters.append(('A1TMid', '穿心'))
    t.scripts += [Script(f'Test - A1T mid {k}', [going, ('NAMED_INSIDE_AREA', m.role(f'mover {k}').name, f'A1T Mid {k}')],
                         [('INCREMENT_COUNTER', 10 ** (k - 1), 'A1TMid')]) for k in lanes]
    if kinds:
        parts = []
        for k in lanes:
            idx = [0] if run == 'd' and k > 1 else _middle(_wall(kinds))
            parts += [(10 ** (k - 1), ('NAMED_NOT_DESTROYED', m.role(f'car {k} {i}').name)) for i in idx]
        s8.total(t, 'A1TCars', '车存', parts)
    s8.watch(t, RUN, .5)
    return t


MISSION = {f'engine_a1toll{r}': (lambda r=r: mission(r)) for r in RUNS}
CHECKS = {f"engine_a1toll{r}": {r: (lambda m, r=r: check(m, r))} for r in RUNS}
CHECKS["engine_a1tolla"]["v"] = lambda m: check(m, "a", True)
