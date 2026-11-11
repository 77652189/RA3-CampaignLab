"""NAMED_SET_MAX_HEALTH(object, max, full) on the bench (engine line A round 147): what happens to the current health.

RA3 1.13 (work/re ra3-script-reference, action 551 at 0x5b0280): the body's setMaxHealth (slot 0x84) is called with
(max, 0) and, when `full` is set, setHealth 1.0 (slot 0x80). In Generals the 0 is MaxHealthChangeType
SAME_CURRENTHEALTH: the hit points stay, only the ceiling moves (clamped down to a lower ceiling). The argument types
are retail's (script_catalog: object, INT, BOOLEAN) -- the 11-05 engine_missile try passed 10000.0, a REAL, in the
INT slot, so its "keeps the current health" reading is not this action's (the try was never committed).

Four of the player's Guardians (480 health) on maps/probe_border.py, rows 500 apart, nobody near: NAMED_DAMAGE
(an INT, no armour: engine_scripts7 panel) at 1 s / 3 s, the set at 2 s; each one's health percent read every frame.
  甲 A  240 off at 1 s, max 960 full 0 at 2 s     SAME_CURRENTHEALTH 25 (the ratio kept would be 50)
  乙 B  240 off at 1 s, max 960 full 1            100
  丙 D  max 9600 full 1, 480 off at 3 s           95 (the max not taken: dead, 0)
  丁 E  max 240 full 0, 120 off at 3 s            50 (clamped to 240, then half; not clamped 100 -> 75)
"""
from maps import probe_border
from parts import Mission, Script, Test
import checks.engine_scripts8 as s8

TANK = 'AlliedAntiVehicleVehicleTech1'          # MaxHealth 480
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
LANES = {'A': (240, (960, 0), 0), 'B': (240, (960, 1), 0), 'D': (0, (9600, 1), 480),
         'E': (0, (240, 0), 120)}               # lane: (damage at 1 s, (max, full) at 2 s, damage at 3 s)
LABELS = dict(zip(LANES, '甲乙丙丁'))
BENCH = {'A': 25, 'B': 100, 'D': 95, 'E': 50}     # predicted from the decompile; the bench decides
RUN = 10.0


def _n(k):
    return f'UNIT - CNV MH {k}'


def mission():
    m = Mission(name='CampMaxHp', map=probe_border, units=[], facts={})
    m.spawns |= {TANK}
    for i, k in enumerate(LANES):
        m.put(TANK, 'stop row', 1000.0 - O[0], 1000.0 + 500.0 * i - O[1], angle=0.0, name=_n(k), role=f'{k} tank')
    return m


def mh(m, expect=BENCH):
    t = Test()
    first = [('NAMED_DAMAGE', m.role(f'{k} tank').name, d) for k, (d, _, _) in LANES.items() if d]
    sets = [('NAMED_SET_MAX_HEALTH', m.role(f'{k} tank').name, mx, full) for k, (_, (mx, full), _) in LANES.items()]
    then = [('NAMED_DAMAGE', m.role(f'{k} tank').name, d) for k, (_, _, d) in LANES.items() if d]
    s8.at(t, 'hurt', 1.0, first)
    s8.at(t, 'max', 2.0, sets)
    s8.at(t, 'then', 3.0, then)
    for k in LANES:
        counter = f'CNV_MH_{k}'
        t.counters.append((counter, LABELS[k]))
        t.scripts.append(Script(f'Test - {counter}', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',
                                                           m.role(f'{k} tank').name, counter)], once=False))
    t.expect += [(LABELS[k], 6, '==', v) for k, v in expect.items()]
    s8.watch(t, RUN)
    return t


MISSION = {'engine_maxhealth': mission}
CHECKS = {'engine_maxhealth': {'mh': mh}}
