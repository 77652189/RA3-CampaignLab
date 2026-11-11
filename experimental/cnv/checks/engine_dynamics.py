"""Engine unit test: does a vehicle's DynamicsUpdate change what it does on the ground (engine line E). Retail data
(SDK SageXML): BaseVehicle carries `DynamicsUpdate Motion="TRACKED" Collision="OMNICOLLIDING" ContactTag="VEHICLE"`
(no Volume); every tank, ship and aircraft inherits it (62 of the 113 retail campaign templates with the module; the
other 51 -- the SS_Fling* props and doors -- are Uprising-only, absent from RA3's data). Question: does a Hammer
without the module crush, go round and arrive as the retail one does.

A child cannot take an inherited module out, so the copies inherit a copy of BaseVehicle written into their own file
(CNVBaseVehicleNoDyn: BaseVehicle without its DynamicsUpdate; CNVBaseVehicleDyn: the same copy with it, the control),
the Hammer's own XML on top under a new id, its NORMAL speed 60 as the campaign override gives the retail one.

On the festival map, west field, three lanes along +x, 300 apart (engine_crush's layout); every unit on HOLD_FIRE (a
death is a crush). Per lane a tank 200 west of an enemy target, ordered at 'Test Go' (1 s in) to a point 200 east of it:
  lane 1 retail Hammer   lane 2 CNVHammerNoDyn   lane 3 CNVHammerDyn
  a  each -> an enemy conscript (crushable 10: crushed)      b  each -> an enemy Guardian tank (20: the Hammer goes round)
Counters (four lines), counted from 'Test Go' on:
  帧数  frames since Go
  行k   1 x frames the target is not destroyed + 1000 x frames it is dying + 1000000 x frames the tank is at its goal
        (a square of half-side 40)

PREDICTED (engine_crush, bench 11-06: conscript crushed at frame 43, dying 127 frames; the Guardian untouched, the Hammer
round it and at its goal from 96): the three lanes alike in each variant.
Bench 2026-11-10 (both PASS; the three rows identical every second): a (CampDynAA_mcp_1110_173046) 607127043 at frame
698 -- each conscript crushed at frame 43, dying 127 frames, each tank at its goal from frame 92; b
(CampDynBB_mcp_1110_173513) 613000709 at frame 709 -- each Guardian alive all along, never dying, each Hammer round it
and at its goal from 97. Without DynamicsUpdate a vehicle crushes, goes round and arrives as with it.
Simulated: tests/test_simbench_c.py::test_dynamics_update_a_hammer_without_it_crushes_and_goes_round_as_the_retail_one.
"""
import os
import re

import labpaths
from maps import festival
from parts import Mission, Script, Test, Unit, square

SAGE = os.path.join(labpaths.SDK3, 'SageXML')
HAMMER, CONSCRIPT, GUARDIAN = 'SovietAntiVehicleVehicleTech1', 'SovietAntiInfantryInfantry', 'AlliedAntiVehicleVehicleTech1'
NODYN, DYN = 'CNVHammerNoDyn', 'CNVHammerDyn'
TANKS = {1: (HAMMER, -300.0), 2: (NODYN, 0.0), 3: (DYN, 300.0)}
TARGETS = {'a': CONSCRIPT, 'b': GUARDIAN}
RUN, HOLD_FIRE = 45.0, 3


def _sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def hammer_copy(dyn):
    """Retail's Hammer under a new id, inheriting a copy of BaseVehicle (written into the same file) with or without
    its DynamicsUpdate; NORMAL speed 60 (CampaignOverrides gives the retail Hammer 60, a new id gets none)."""
    name, base = (DYN, 'CNVBaseVehicleDyn') if dyn else (NODYN, 'CNVBaseVehicleNoDyn')
    v = open(os.path.join(SAGE, 'BaseObjects', 'BaseVehicle.xml'), encoding='utf-8').read()
    b = re.search(r'\t<GameObject\s+id="BaseVehicle".*?</GameObject>\n', v, re.S).group(0)
    b = _sub1(b, 'id="BaseVehicle"', f'id="{base}"')
    if not dyn:
        b, k = re.subn(r'\s*<DynamicsUpdate\s+id="ModuleTag_DefaultDynamicsUpdate".*?</DynamicsUpdate>', '', b, flags=re.S)
        assert k == 1, k
    x = open(os.path.join(SAGE, 'Soviet', 'Units', HAMMER + '.xml'), encoding='utf-8').read()
    x = _sub1(x, f'id="{HAMMER}"', f'id="{name}"')
    x = _sub1(x, f'EditorName="{HAMMER}"', f'EditorName="{name}"')
    x = _sub1(x, 'inheritFrom="BaseVehicle"', f'inheritFrom="{base}"')
    x = _sub1(x, 'Condition="NORMAL"\n\t\t\tSpeed="75.0"', 'Condition="NORMAL"\n\t\t\tSpeed="60.0"')
    x = _sub1(x, '\t<GameObject', b + '\t<GameObject')
    # the base copy inherits BaseObject: its file must be in our includes (BaseVehicle.xml's own include is not ours)
    x = _sub1(x, '<Includes>', '<Includes>\n\t\t<Include type="instance" source="DATA:BaseObjects/BaseObject.xml" />')
    return Unit(name, x, names=dict(unit=name, base=base),
                what='锤子坦克的复制（继承的 BaseVehicle 复制' + ('保留' if dyn else '去掉') + ' DynamicsUpdate；速度 60 同战役）')


def _n(part):
    return f'UNIT - CNV Dyn {part}'


def mission(which='a'):
    m = Mission(name=f'CampDyn{which.upper()}', map=festival, units=[hammer_copy(False), hammer_copy(True)], facts={})
    for k, (tank, dy) in TANKS.items():
        m.put(tank, 'west field', -200.0, dy, angle=0.0, role=f'tank {k}', name=_n(f'Tank {k}'))
        m.put(TARGETS[which], 'west field', 0.0, dy, angle=180.0, side='s1', role=f'target {k}', name=_n(f'Target {k}'))
    return m


def dyn_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    x, y = m.site('west field')[:2]
    for k, (_, dy) in TANKS.items():
        t.waypoints[f'Test Goal {k}'] = (x + 200.0, y + dy)
        t.areas[f'Test Goal {k}'] = square(x + 200.0, y + dy, 40.0)
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    start += [('UNIT_SET_STANCE', _n(f'{w} {k}'), HOLD_FIRE) for k in TANKS for w in ('Tank', 'Target')]
    t.scripts.append(Script('Test - start', [], start))
    go = [('MOVE_NAMED_UNIT_TO', _n(f'Tank {k}'), f'Test Goal {k}') for k in TANKS]
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)
    t.counters.append(('CNV_Dyn_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Dyn_Frames')], once=False))
    for k in TANKS:
        target, tank = _n(f'Target {k}'), _n(f'Tank {k}')
        t.counters.append((f'CNV_Dyn_Row{k}', f'行{k}'))
        for j, (cond, step) in enumerate([(('NAMED_NOT_DESTROYED', target), 1), (('NAMED_DYING', target), 1000),
                                          (('NAMED_INSIDE_AREA', tank, f'Test Goal {k}'), 1000000)]):
            t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                    [('INCREMENT_COUNTER', step, f'CNV_Dyn_Row{k}')], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


MISSION = {'engine_dynamics': mission, 'engine_dynamics_b': lambda: mission('b')}
CHECKS = {'engine_dynamics': {'a': dyn_test}, 'engine_dynamics_b': {'b': lambda m: dyn_test(m, 'b')}}
