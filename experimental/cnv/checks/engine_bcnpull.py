"""Engine unit test: 信标拉回 (TeleportToCasterSpecialPower, A428) -- the beacon trooper's pull read off a script cast
(NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT, no cooldown). The program (work/re l2_teleport_to_caster.md): the base unpack
(UnpackTime 0.5 s), then the things of the power's ObjectFilter (INFANTRY VEHICLE, SAME_PLAYER ALLIES) within Radius
150 of the point are put round the caster at once: the i-th of n from angle 2 pi i / n, the first free spot from
MinDestinationRadius 40 out to MaxDestinationRadius 140, facing out; none free: on the caster's own point.

Island west field: the trooper (units/beacon.py) at the site; P 450 east of him. Round P: own Guardians G1 at P and
G2 100 north, an own Peacekeeper 100 west, a Soviet_1 Guardian 100 east (in the radius, not ours), an own Guardian
200 south (outside it). All NO_ATTACK.
  a  pull at P
  b  as a with G1 alone (the rest deleted): where round him the one lands

Counters, every one counted from 'Test Go' (frame 0 = the cast); Near = the square 150 round the trooper:
  帧数   frames since Go
  a: 第二行 G1 in Near + 1000 x G2 in Near; 第三行 the Peacekeeper in Near + 1000 x the foe in Near;
     第四行 the far one in Near + 1000 x the trooper in the square 30 round his start
  b: G1 in the BOXES round him (half sides; quadrants NE NW SW SE, E40 = 40 east, R45 R60 R100 = squares round him),
     each row three of them at steps 1, 100, 10000 (B_ROWS)
"""
from maps import island
from parts import Mission, Script, Test, square
from units import beacon

RUN = 4.0
TANK, INF = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
SITE, P = 'west field', (450.0, 0.0)
CREW = {'g1': (TANK, 0.0, 0.0, 'p1'), 'g2': (TANK, 0.0, 100.0, 'p1'), 'inf': (INF, -100.0, 0.0, 'p1'),
        'foe': (TANK, 100.0, 0.0, 's1'), 'far': (TANK, 0.0, -200.0, 'p1')}     # from P
BOXES = {'NE': (75, 75, 75), 'NW': (-75, 75, 75), 'SW': (-75, -75, 75), 'SE': (75, -75, 75),    # (dx, dy, half side)
         'E40': (40, 0, 12), 'R45': (0, 0, 45), 'R60': (0, 0, 60), 'R100': (0, 0, 100)}
B_ROWS = {2: ('NE', 'NW', 'SW'), 3: ('SE', 'E40', 'R45'), 4: ('R60', 'R100', 'Near')}   # steps 1, 100, 10000


def _n(part):
    return f'UNIT - CNV BcnPull {part}'


def mission():
    unit = beacon.beacon('CNV_BcnPull', look_as=None)
    m = Mission(name='CampBcnPull', map=island, units=[unit])
    m.put(unit.id, SITE, 0.0, 0.0, angle=0.0, role='beacon', name=_n('beacon'))
    for k, (tpl, dx, dy, side) in CREW.items():
        m.put(tpl, SITE, P[0] + dx, P[1] + dy, angle=0.0, role=k, side=side, name=_n(k))
    return m


def pull_test(m, which='a'):
    t = Test()
    here = m.site(SITE)[:2]
    t.waypoints['Test Pull At'] = m.site(SITE, *P)[:2]
    t.areas['Test Near'], t.areas['Test Start'] = square(*here, 150.0), square(*here, 30.0)
    for k, (dx, dy, r) in BOXES.items():
        t.areas[f'Test {k}'] = square(here[0] + dx, here[1] + dy, r)
    names = {k: _n(k) for k in CREW}
    me = _n('beacon')
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    if which == 'b':
        start += [('NAMED_DELETE', names[k]) for k in CREW if k != 'g1']
    start += [('UNIT_CHANGE_OBJECT_STATUS', u, 'NO_ATTACK', 1) for u in list(names.values()) + [me]]
    t.scripts.append(Script('Test - start', [], start))
    go = [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', me, m.ability('beacon', 'pull'), 'Test Pull At'),
          ('SET_FLAG', 'Test Going', 1)]
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go))
    going = ('FLAG', 'Test Going', 1)
    t.counters.append(('CNV_BcnPull_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_BcnPull_Frames')], once=False))

    def inside(k, a):
        return ('NAMED_INSIDE_AREA', me if k == 'beacon' else names[k], f'Test {a}')
    rows = ({2: [(inside('g1', 'Near'), 1), (inside('g2', 'Near'), 1000)],
             3: [(inside('inf', 'Near'), 1), (inside('foe', 'Near'), 1000)],
             4: [(inside('far', 'Near'), 1), (inside('beacon', 'Start'), 1000)]} if which == 'a' else
            {k: [(inside('g1', a), 100 ** j) for j, a in enumerate(row)] for k, row in B_ROWS.items()})
    for k, label in ((2, '第二行'), (3, '第三行'), (4, '第四行')):
        t.counters.append((f'CNV_BcnPull_Row{k}', label))
        for j, (cond, step) in enumerate(rows[k]):
            t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                    [('INCREMENT_COUNTER', step, f'CNV_BcnPull_Row{k}')], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


MISSION = {'engine_bcnpull': mission}
CHECKS = {'engine_bcnpull': {w: (lambda m, w=w: pull_test(m, w)) for w in 'ab'}}
