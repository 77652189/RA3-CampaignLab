"""Engine unit test: FireWeaponCollide (E217) -- the Flak trooper's (SovietAntiVehicleInfantry) crush revenge.

Retail data: ModuleTag_CrushRevengeWeapon, CollideWeapon SovietAntiVehicleInfantryMagneticBombExplosion, Flags
WHEN_BEING_CRUSHED, RequiredStatus GENERIC_TOGGLE_STATE (its magnetic bomb's ToggleState,
Command_ToggleMagneticBombSpecialPower), FireOnce. The weapon: one DamageNugget 200 CANNON, radius 10 (taper 10),
VEHICLE / STRUCTURE only, RadiusDamageAffects ALLIES ENEMIES NEUTRALS. The Hammer (SovietAntiVehicleVehicleTech1,
crusher 20 against infantry's 10) has MaxHealth 550, BaseTankArmor CANNON 100 %.

On the festival map, west field, two lanes along +x 300 apart (engine_crush's lanes): in each the player's Hammer
200 west of an enemy Flak trooper, everyone HOLD_FIRE, the Hammers ordered at 'Test Go' (2 s) to a point 200 east of
the trooper (straight through). Lane 1's trooper presses the toggle at once (its GENERIC_TOGGLE_STATE comes on with
the press: engine_toggle b, PackTime 1 s delays nothing); lane 2's does not (the control).

Counters (four lines), counted from 'Test Go' on:
  帧数  frames since Go
  一道  lane 1's Hammer: 1 x frames its health is below 100 % + 1000 x frames below 70 %
  二道  lane 2's Hammer: the same
  步兵  1 x frames lane 1's trooper is not destroyed + 1000 x frames lane 2's is not

Predicted from the data: both troopers crushed (engine_crush: the conscript at frame 43); lane 1's Hammer from that
frame 350 / 550 = 63 % (one hit at the centre, the taper INFERRED to leave it whole) -- 一道 n001 n001 alike
(the same count in both parts); lane 2's Hammer whole (二道 0).
"""
from maps import festival
from parts import Mission, Script, Test

HAMMER, FLAK = 'SovietAntiVehicleVehicleTech1', 'SovietAntiVehicleInfantry'
TOGGLE = 'Command_ToggleMagneticBombSpecialPower'
LANES = {1: -150.0, 2: 150.0}
RUN, HOLD_FIRE = 30.0, 3


def _n(part):
    return f'UNIT - CNV FWColl {part}'


def mission():
    m = Mission(name='CampFWColl', map=festival, units=[], facts={})
    for k, dy in LANES.items():
        m.put(HAMMER, 'west field', -200.0, dy, angle=0.0, role=f'tank {k}', name=_n(f'Tank {k}'))
        m.put(FLAK, 'west field', 0.0, dy, angle=180.0, side='s1', role=f'flak {k}', name=_n(f'Flak {k}'))
    return m


def collide_test(m):
    t = Test()
    p1 = m.player('p1')
    x, y = m.site('west field')[:2]
    for k, dy in LANES.items():
        t.waypoints[f'Test Goal {k}'] = (x + 200.0, y + dy)
    names = [_n(f'{p} {k}') for k in LANES for p in ('Tank', 'Flak')]
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 2.0)]
    start += [('UNIT_SET_STANCE', n, HOLD_FIRE) for n in names]
    start += [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('Flak 1'), TOGGLE)]
    t.scripts.append(Script('Test - start', [], start))
    go = [('MOVE_NAMED_UNIT_TO', _n(f'Tank {k}'), f'Test Goal {k}') for k in LANES]
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)
    t.counters.append(('CNV_FWColl_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_FWColl_Frames')], once=False))
    hurt = lambda k, pct: ('UNIT_HEALTH', _n(f'Tank {k}'), 0, pct)  # noqa: E731
    rows = {
        2: ('一道', [(hurt(1, 100), 1), (hurt(1, 70), 1000)]),
        3: ('二道', [(hurt(2, 100), 1), (hurt(2, 70), 1000)]),
        4: ('步兵', [(('NAMED_NOT_DESTROYED', _n('Flak 1')), 1), (('NAMED_NOT_DESTROYED', _n('Flak 2')), 1000)]),
    }
    for k, (label, conds) in rows.items():
        t.counters.append((f'CNV_FWColl_Row{k}', label))
        for j, (cond, step) in enumerate(conds):
            t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                    [('INCREMENT_COUNTER', step, f'CNV_FWColl_Row{k}')], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


MISSION = {'engine_fwcollide': mission}
CHECKS = {'engine_fwcollide': {'a': collide_test}}
