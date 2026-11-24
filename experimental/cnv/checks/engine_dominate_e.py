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
"""
from maps import probe_range
from parts import Mission, Script, Test, status

SPY, BUTTON = 'AlliedInfiltrationInfantry', 'Command_ActivateBribeSpecialPower'
GO, LONG = 30, 120
VICTIMS = [('Inf', 'SovietAntiVehicleInfantry', 40.0, 0.0, 1), ('Veh', 'SovietAntiInfantryVehicle', -50.0, 0.0, 10),
           ('Far', 'SovietAntiVehicleInfantry', 0.0, 90.0, 100), ('Str', 'SovietBaseDefenseGround', 0.0, -50.0, 1000)]


def mission():
    m = Mission(name='CampDominE', map=probe_range, units=[])
    m.put(SPY, 'base gun', 0.0, 0.0, role='spy', name='E216 spy')
    for role, template, dx, dy, _ in VICTIMS:
        m.put(template, 'base gun', dx, dy, side='s1', role=role, name='E216 ' + role, angle=0.0)
    return m


def check(m):
    end = GO + LONG
    spy, them = m.role('spy').name, m.player('s1')
    t = Test()
    t.counters = [('E216Frame', '完成帧'), ('E216Inf', '近步兵'), ('E216Veh', '近车'), ('E216Taken', '换手')]
    t.scripts = [Script('Test - clock', [('COUNTER', 'E216Frame', 0, end)],
                        [('INCREMENT_COUNTER', 1, 'E216Frame')], once=False),
                 Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                 Script('Test - quiet', [], [('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, status('NO_ATTACK'), 1)
                                             for r, *_ in VICTIMS]),
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


MISSION = {'engine_dominate_e': mission}
CHECKS = {'engine_dominate_e': {'a': check}}
