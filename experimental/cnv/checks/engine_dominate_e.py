"""E216: DominateEnemySpecialPower -- retail's one use, the Allied spy's bribe (AlliedInfiltrationInfantry:
SpecialPower_Bribe, UnpackTime 0 s, PackTime 3.66 s, BUSY_DURING_PACK, DominateRadius 65, PermanentlyConvert true,
ENEMIES VEHICLE INFANTRY).

A p1 spy with four s1 things around it, all holding fire (NO_ATTACK): an infantry 40 east, a vehicle 50 west, an
infantry 90 north (outside the radius), a sentry gun 50 south (a structure: not in Include). At GO the map presses the
bribe button (Command_ActivateBribeSpecialPower).
Prediction: the near infantry and the vehicle change hands, the far one and the structure do not; when: at the press
(UnpackTime 0) or once the pack is over (3.66 s = 55 frames).
Counters: frame (stops at END = GO + 120), Inf / Veh = frames from GO the near infantry / the vehicle is still s1's
(stops when it is not), Taken at END = near infantry 1 + vehicle 10 + far infantry 100 + structure 1000, the ones p1
owns.

b (review 1124 P2, a press while the first one's pack is on): four more spies on other lanes, each an s1 infantry 40
east (One) and one 300 north (Two, out of the radius). At GO each spy's press takes One; then Two is teleported 40
west of it and the spy pressed again: D the same frame (same script, after the first press), P 1 s on (inside the
3.66 s pack), R 5 s on (the pack over, the 10 s reload not); C the control, Two teleported before its one press (is
a teleport seen by a press the same frame?). Four counter lines: One / Two at END = the spots' One / Two p1 owns, D 1
+ P 10 + R 100 + C 1000; W = frames from the second press that Two is still s1's, D's x 1 + P's x 1000.
Prediction: a script's cast heeds no reload (read, l2_ability.md): R takes Two; BUSY_DURING_PACK: D and P not.
"""
from maps import probe_range
from parts import Mission, Script, Test, status

SPY, BUTTON = 'AlliedInfiltrationInfantry', 'Command_ActivateBribeSpecialPower'
GO, LONG = 30, 120
VICTIMS = [('Inf', 'SovietAntiVehicleInfantry', 40.0, 0.0, 1), ('Veh', 'SovietAntiInfantryVehicle', -50.0, 0.0, 10),
           ('Far', 'SovietAntiVehicleInfantry', 0.0, 90.0, 100), ('Str', 'SovietBaseDefenseGround', 0.0, -50.0, 1000)]


# b: spot -> (lane, the second press's frames after GO; None: the control's one press, after the teleport)
AGAIN = {'D': ('high gun', 0), 'P': ('order gun', 15), 'R': ('removed gun', 75), 'C': ('switch gun', None)}


def mission():
    m = Mission(name='CampDominE', map=probe_range, units=[])
    m.put(SPY, 'base gun', 0.0, 0.0, role='spy', name='E216 spy')
    for role, template, dx, dy, _ in VICTIMS:
        m.put(template, 'base gun', dx, dy, side='s1', role=role, name='E216 ' + role, angle=0.0)
    for k, (lane, _) in AGAIN.items():
        m.put(SPY, lane, 0.0, 0.0, role='spy ' + k, name='E216 spy ' + k)
        for who, dx, dy in (('One', 40.0, 0.0), ('Two', 0.0, 300.0)):
            m.put(VICTIMS[0][1], lane, dx, dy, side='s1', role=who + k, name=f'E216 {who} {k}', angle=0.0)
        m.waypoint('beside ' + k, 'Test E216 ' + k, lane, -40.0, 0.0)
    return m


def _quiet(m, roles):
    return Script('Test - quiet', [], [('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, status('NO_ATTACK'), 1)
                                       for r in roles])


def check(m):
    end = GO + LONG
    spy, them = m.role('spy').name, m.player('s1')
    t = Test()
    t.counters = [('E216Frame', '完成帧'), ('E216Inf', '近步兵'), ('E216Veh', '近车'), ('E216Taken', '换手')]
    t.scripts = [Script('Test - clock', [('COUNTER', 'E216Frame', 0, end)],
                        [('INCREMENT_COUNTER', 1, 'E216Frame')], once=False),
                 Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                 _quiet(m, [r for r, *_ in VICTIMS] + [w + k for k in AGAIN for w in ('One', 'Two')]),
                 Script('Test - go', [('COUNTER', 'E216Frame', 2, GO)],
                        [('NAMED_USE_COMMANDBUTTON_ABILITY', spy, BUTTON)])]
    for role, _, _, _, weight in VICTIMS:
        who = m.role(role).name
        if role in ('Inf', 'Veh'):
            t.scripts.append(Script('Test - wait ' + role, [('COUNTER', 'E216Frame', 3, GO),
                                                            ('COUNTER', 'E216Frame', 0, end),
                                                            ('NAMED_OWNED_BY_PLAYER', them, who)],
                                    [('INCREMENT_COUNTER', 1, 'E216' + role)], once=False))
        t.scripts.append(Script('Test - taken ' + role, [('COUNTER', 'E216Frame', 2, end),
                                                         ('NAMED_OWNED_BY_PLAYER', m.player('p1'), who)],
                                [('INCREMENT_COUNTER', weight, 'E216Taken')]))
    t.expect = [('完成帧', 0, 'ever==', end)]
    t.bench = [('bench_camera', dict(x=1150, y=550, look=False)),
               ('bench_watch', dict(seconds=end // 15 + 25, every=1, sheet=False, lines=4))]
    return t


def again(m):
    """b: a second press while the first one's pack is on (module docstring)."""
    end = GO + LONG
    p1, them = m.player('p1'), m.player('s1')
    t = Test()
    t.counters = [('E216Frame', '完成帧'), ('E216One', 'One'), ('E216Two', 'Two'), ('E216W', 'W')]
    t.scripts = [Script('Test - clock', [('COUNTER', 'E216Frame', 0, end)],
                        [('INCREMENT_COUNTER', 1, 'E216Frame')], once=False),
                 Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]),
                 _quiet(m, [r for r, *_ in VICTIMS] + [w + k for k in AGAIN for w in ('One', 'Two')])]
    for i, (k, (_, later)) in enumerate(AGAIN.items()):
        spy, two = m.role('spy ' + k).name, m.role('Two' + k).name
        press, move = ('NAMED_USE_COMMANDBUTTON_ABILITY', spy, BUTTON), ('UNIT_TELEPORT_TO_WAYPOINT', two,
                                                                            m.mark('beside ' + k))
        second = GO + (later or 0)
        if later is None:
            t.scripts.append(Script(f'Test - go {k}', [('COUNTER', 'E216Frame', 2, GO)], [move, press]))
        elif later == 0:
            t.scripts.append(Script(f'Test - go {k}', [('COUNTER', 'E216Frame', 2, GO)], [press, move, press]))
        else:
            t.scripts += [Script(f'Test - go {k}', [('COUNTER', 'E216Frame', 2, GO)], [press]),
                          Script(f'Test - again {k}', [('COUNTER', 'E216Frame', 2, second)], [move, press])]
        if k in 'DP':
            t.scripts.append(Script(f'Test - wait {k}', [('COUNTER', 'E216Frame', 3, second),
                                                         ('COUNTER', 'E216Frame', 0, end),
                                                         ('NAMED_OWNED_BY_PLAYER', them, two)],
                                    [('INCREMENT_COUNTER', 1000 ** i, 'E216W')], once=False))
        for who in ('One', 'Two'):
            t.scripts.append(Script(f'Test - taken {who} {k}', [('COUNTER', 'E216Frame', 2, end),
                                                               ('NAMED_OWNED_BY_PLAYER', p1, m.role(who + k).name)],
                                    [('INCREMENT_COUNTER', 10 ** i, 'E216' + who)]))
    t.expect = [('完成帧', 0, 'ever==', end)]
    t.bench = [('bench_watch', dict(seconds=end // 15 + 25, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_dominate_e': mission}
CHECKS = {'engine_dominate_e': {'a': check, 'b': again}}
