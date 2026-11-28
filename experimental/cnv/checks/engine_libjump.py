"""Engine unit test: 自由号跳跃 (TeleportSpecialAbilityUpdate, A427) -- the Liberty's deck jump read off a script cast
(NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT, no cooldown). The program (work/re l2_teleport_ability.md): the unpack starts
the order's frame and fires SourceWeapon at its own place (the deck store), UnpackTime later it sets itself at the
point (ground + its flying height) and fires DestinationWeapon there (the deck send: TeleportStoredObjectsUpdate,
GetObjectsCurrentlyAtStorePosition, Initial / Delay 0, Telefrag INSTANT_DEATH_TELEPORTER_ONLY, FadeIn 1 s).

Island west field: the Liberty (units/liberty.py, no look, deck radius 150) 60 south of the site; under its deck
Guardians G1 60 east and G2 60 south; a runner Guardian 135 west, ordered west the Go frame (out of the 150 by the send:
carried or not tells the store's second take). T = the site + (300, -225), 342 off.
A parked Guardian stands where G1 lands (T + (60, 0)); deleted at the start except in b. All ours, NO_ATTACK.
  a  jump to T
  b  as a, the parked one left: G1 lands on it
  c  jump to east 2, ~2390 off (MaxDistance 2000): does it land there, at the 2000 cap, or nowhere?

Counters, every one counted from 'Test Go' (frame 0 = the cast):
  帧数   frames since Go
  第二行  1 x frames the Liberty is inside S (square 100 round its start) + 1000 x inside T's square 100 (c: east 2's)
  第三行  1 x frames G1 is inside S + 1000 x inside T (b: 1000 x frames G1 is destroyed)
  第四行  1 x frames G2 is inside T + 1000 x the runner (c: 1 x the Liberty inside the cap square 150 + 1000 x G2 in T)
"""
import math

from maps import island
from parts import Mission, Script, Test, square
from units import liberty as lib

RUN = 6.0
TANK = 'AlliedAntiVehicleVehicleTech1'
SITE, AT = 'west field', (0.0, -60.0)            # the Liberty
T_BY, FAR = (300.0, -225.0), 'east 2'            # T from the site; c's point
CREW = {'g1': (60.0, 0.0), 'g2': (0.0, -60.0), 'run': (-135.0, 0.0)}   # from the Liberty
CAP = 2000.0


def _n(part):
    return f'UNIT - CNV LibJump {part}'


def mission():
    unit = lib.liberty('CNV_LibJump', tag='J', drones_home=False, model=None)
    m = Mission(name='CampLibJump', map=island, units=[unit])
    m.put(unit.id, SITE, *AT, angle=0.0, role='carrier', name=_n('Liberty'))
    for k, (dx, dy) in CREW.items():
        m.put(TANK, SITE, AT[0] + dx, AT[1] + dy, angle=0.0, role=k, name=_n(k))
    m.put(TANK, SITE, T_BY[0] + CREW['g1'][0], T_BY[1] + CREW['g1'][1], angle=0.0, role='parked', name=_n('parked'))
    return m


def jump_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    s, here = m.site(SITE)[:2], m.site(SITE, *AT)[:2]
    to = m.site(FAR)[:2] if which == 'c' else m.site(SITE, *T_BY)[:2]
    d = math.hypot(to[0] - here[0], to[1] - here[1])
    cap = (here[0] + (to[0] - here[0]) * CAP / d, here[1] + (to[1] - here[1]) * CAP / d)
    t.waypoints['Test Jump To'] = to
    t.waypoints['Test Run'] = (here[0] - 600.0, here[1])
    t.areas['Test S'], t.areas['Test T'], t.areas['Test Cap'] = square(*here, 100.0), square(*to, 100.0), \
        square(*cap, 150.0)
    names = {k: _n(k) for k in list(CREW) + ['parked']}
    lib_n = _n('Liberty')
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    if which != 'b':
        start.append(('NAMED_DELETE', names['parked']))
    start += [('UNIT_CHANGE_OBJECT_STATUS', u, 'NO_ATTACK', 1) for u in names.values()]
    t.scripts.append(Script('Test - start', [], start))
    go = [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', lib_n, m.ability('carrier', 'jump'), 'Test Jump To'),
          ('MOVE_NAMED_UNIT_TO', names['run'], 'Test Run'), ('SET_FLAG', 'Test Going', 1)]
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go))
    going = ('FLAG', 'Test Going', 1)
    t.counters.append(('CNV_LibJump_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_LibJump_Frames')], once=False))

    def inside(u, a):
        return ('NAMED_INSIDE_AREA', u, a)
    rows = {2: [(inside(lib_n, 'Test S'), 1), (inside(lib_n, 'Test T'), 1000)],
            3: [(inside(names['g1'], 'Test S'), 1),
                (('NAMED_DESTROYED', names['g1']), 1000) if which == 'b' else (inside(names['g1'], 'Test T'), 1000)],
            4: ([(inside(lib_n, 'Test Cap'), 1), (inside(names['g2'], 'Test T'), 1000)] if which == 'c' else
                [(inside(names['g2'], 'Test T'), 1), (inside(names['run'], 'Test T'), 1000)])}
    for k, label in ((2, '第二行'), (3, '第三行'), (4, '第四行')):
        t.counters.append((f'CNV_LibJump_Row{k}', label))
        for j, (cond, step) in enumerate(rows[k]):
            t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                    [('INCREMENT_COUNTER', step, f'CNV_LibJump_Row{k}')], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


MISSION = {'engine_libjump': mission}
CHECKS = {'engine_libjump': {w: (lambda m, w=w: jump_test(m, w)) for w in 'abc'}}
