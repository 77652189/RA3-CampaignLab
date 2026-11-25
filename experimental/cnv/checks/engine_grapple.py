"""GrapplingHookUpdate -- the Apocalypse's harpoon (SovietAntiVehicleVehicleTech3, 24 of the 27 levels).

Retail: Command_ToggleHarpoonSpecialPower steps its ToggleStatusSpecialAbilityUpdate to GENERIC_TOGGLE_STATE; the weapon
set then forbids the cannon and arms SovietAntiVehicleVehicleTech3Harpoon (300 range, FiringDuration 1 s, clip 1 /
reload 2 s; GrapplingHookNugget Damage 1 CANNON on VEHICLE / STRUCTURE / TIME_BOMB not AIRCRAFT / bridge). The
GrapplingHookUpdate (RequiredStatus GENERIC_TOGGLE_STATE) pulls the hooked thing at PullRate 40; at the hooker it
fires SingleFireWeapon SovietHarpoonCrushWeapon (999999 CRUSH on VEHICLE / TIME_BOMB, 1 s delay) and then
ContinuousFireWeapon SovietHarpoonGrindWeapon (25 EXPLOSIVE every 0.24 s, 0.25 s after) -- BouncePercentage 5 %.

Two lanes, each a p1 Apocalypse facing north and an s1 Hammer (NO_ATTACK) DIST north of it (260 / 160: two distances
part the pull's speed from its fixed delays). Both Apocalypses pressed at PRESS, held NO_ATTACK until SHOOT, then
ordered at their Hammer. Counters: each Hammer's health and its ring -- how many of the squares of half-side 25 .. 225
(step 25) round its Apocalypse it stands in (9 far .. 0 beyond 225; it walks the line, so a ring is a 25 band).
Prediction: the ring climbs about 40 a second (1.6 a second), the Hammer dies a second after it is at the tank.
b (A365): pressed the same, never ordered: Far's Apocalypse keeps NO_ATTACK all along, Near's loses it at the press -- does
the harpoon fire at the press on its own (a's hook came at the press, a second before the order)?
The older synthetic probe here (a gun with a GrapplingHookNugget, no toggle) never pulled anything (1099 x 4).
"""
from maps import probe_range
from parts import Mission, Script, Test, counted, square

APOC, HAMMER = 'SovietAntiVehicleVehicleTech3', 'SovietAntiVehicleVehicleTech1'
TOGGLE = 'Command_ToggleHarpoonSpecialPower'
LANES = {'Far': ('base', 260.0), 'Near': ('high', 160.0)}
RINGS = range(25, 250, 25)
PRESS, SHOOT, END = 15 * 16, 15 * 17, 15 * 32      # the counters are read from s15


def mission():
    m = Mission(name='CampGrapple', map=probe_range, units=[])
    for arm, (lane, dist) in LANES.items():
        m.put(APOC, f'{lane} gun', side='p1', role=f'apoc {arm}', name=f'E226 Apoc {arm}', angle=1.5708)
        m.put(HAMMER, f'{lane} gun', 0, dist, side='s1', role=f'victim {arm}', name=f'E226 Hammer {arm}', angle=4.7124)
    return m


def check(m, b=False):
    t = Test()
    for arm, (lane, _) in LANES.items():
        counted(f'E226Hp{arm}', '血' + arm, t, health=m.role(f'victim {arm}').name)
    for arm, (lane, _) in LANES.items():
        c, v, (x, y) = f'E226Ring{arm}', m.role(f'victim {arm}').name, m.site(f'{lane} gun', 0, 0)
        t.counters.append((c, '圈' + arm))
        t.scripts.append(Script(f'Test - ring {arm} zero', [], [('SET_COUNTER', c, 0)], once=False))
        for r in RINGS:
            t.areas[f'E226 {arm} {r}'] = square(x, y, r)
            t.scripts.append(Script(f'Test - ring {arm} {r}', [('NAMED_INSIDE_AREA', v, f'E226 {arm} {r}')],
                                    [('INCREMENT_COUNTER', 1, c)], once=False))
    apocs = [m.role(f'apoc {arm}').name for arm in LANES]
    t.scripts += [Script('Test - clock', [('COUNTER', 'E226Frame', 0, END)],
                         [('INCREMENT_COUNTER', 1, 'E226Frame')], once=False),
                  Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))] +
                         [('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in apocs] +
                         [('UNIT_CHANGE_OBJECT_STATUS', m.role(f'victim {arm}').name, 'NO_ATTACK', 1) for arm in LANES]),
                  Script('Test - press', [('COUNTER', 'E226Frame', 2, PRESS)],
                         [('NAMED_USE_COMMANDBUTTON_ABILITY', n, TOGGLE) for n in apocs] +
                         ([('UNIT_CHANGE_OBJECT_STATUS', apocs[1], 'NO_ATTACK', 0)] if b else []))]
    t.scripts += [] if b else [Script('Test - shoot', [('COUNTER', 'E226Frame', 2, SHOOT)],
                         [a for arm in LANES for a in (('UNIT_CHANGE_OBJECT_STATUS', m.role(f'apoc {arm}').name,
                                                        'NO_ATTACK', 0),
                                                       ('NAMED_ATTACK_NAMED', m.role(f'apoc {arm}').name,
                                                        m.role(f'victim {arm}').name))])]
    t.expect = [('血Far', 0, '==', 100)]
    t.bench = [('bench_camera', dict(x=m.site('base gun', 0, 0)[0], y=m.site('base gun', 0, 0)[1], look=False)),
               ('bench_watch', dict(seconds=END // 15 + 3, every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_grapple': mission}
CHECKS = {'engine_grapple': {'a': check, 'b': lambda m: check(m, True)}}
