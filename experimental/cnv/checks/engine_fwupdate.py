"""Engine unit test: FireWeaponUpdate (E218) -- the Tesla trooper's (SovietHeavyAntiVehicleInfantry) short circuit.

Of retail's 23 templates with the module the 27 missions reach two: this trooper (all 27) and A09_IronCurtainEffect
(a09, the Iron Curtain's look-alike). Retail data: ModuleTag_FireWeaponUpdate, FireInterval 0.13 s, AliveOnly,
ActiveWhenDisabled HELD, FireWeaponNugget SovietHeavyAntiVehicleInfantryShortCircuit (OneShot false),
ObjectStatusValidation RequiredStatus GENERIC_TOGGLE_STATE (Command_ToggleShortCircuit; on from the press for good,
engine_toggle f). The weapon: two ParalyzeNuggets EMP, radius 50, 1.1 s, ENEMIES NEUTRAL -- the first Rule NONE with
no Include (ExcludeThing the trooper), the second Rule ANY Include VEHICLE (+ SovietScoutVehicle), Exclude INFANTRY
AIRCRAFT STRUCTURE, StatusBitFlagsExclude UNATTACKABLE UNDER_IRON_CURTAIN.

On the probe range, everyone NO_ATTACK. Lane 1 (base gun): the player's trooper, an enemy Hammer 30 north and one 80
north, an enemy conscript 30 south, the player's own Hammer 30 east. Lane 2 (switch gun, the control): the same
trooper and an enemy Hammer 30 north, no press. At PRESS lane 1's trooper presses the toggle; MOVE_AT after it every
other unit is sent 300 further out (its own direction); KILL after the press lane 1's trooper is killed (AliveOnly).

Counters (four lines), frames added from the press on:
  近车  +1 a frame lane 1's Hammer 30 stands in its 30 home square, +1000 the Hammer 80 does
  旁人  +1 the conscript, +1000 the own Hammer
  对照  +1 lane 2's Hammer 30, +1000 a frame lane 1's Hammer 30 is below 100 % (NO_ATTACK holds)

Predicted from the data (15 frames a second): a pulse every 2 frames from the press (0.13 s), each holding a taken
unit 17 frames (1.1 s) past it; the trooper's last pulse at the kill (frame 75), so the Hammer 30 stays till ~92 and
then walks its 30 like the control -- 近车 % 1000 = 对照 % 1000 + ~87; the Hammer 80 (outside 50) = the control;
the own Hammer = the control (ENEMIES NEUTRAL); the conscript: the first nugget's Rule NONE with an empty Include
read as taking nothing (INFERRED; it would hold him as the Hammer 30 if NONE takes all) -- = the control. 对照 // 1000
= 0.
"""
from maps import probe_range
from parts import Mission, Script, Test, square

PRESS, MOVE_AT, KILL, RUN = 2.0, 0.3, 5.0, 14.0
TESLA, HAMMER, CONSCRIPT = 'SovietHeavyAntiVehicleInfantry', 'SovietAntiVehicleVehicleTech1', 'SovietAntiInfantryInfantry'
TOGGLE = 'Command_ToggleShortCircuit'
N = 'UNIT - CNV FWU '
# name: (template, side, lane site, dx, dy) -- each sent 300 further out along (dx, dy)
VICTIMS = {'H30': (HAMMER, 's1', 'base gun', 0, 30), 'H80': (HAMMER, 's1', 'base gun', 0, 80),
           'C30': (CONSCRIPT, 's1', 'base gun', 0, -30), 'Own': (HAMMER, 'p1', 'base gun', 30, 0),
           'Ctl': (HAMMER, 's1', 'switch gun', 0, 30)}


def mission():
    m = Mission(name='CampFWUpd', map=probe_range, units=[], facts={})
    m.put(TESLA, 'base gun', side='p1', name=N + 'Tesla')
    m.put(TESLA, 'switch gun', side='p1', name=N + 'Tesla Ctl')
    for k, (tpl, side, site, dx, dy) in VICTIMS.items():
        m.put(tpl, site, dx, dy, side=side, name=N + k)
        f = 300.0 / (dx * dx + dy * dy) ** 0.5
        m.waypoint(f'{k} away', f'Test FWU {k} Away', site, dx * (1 + f), dy * (1 + f))
    return m


def surge(m):
    t = Test()
    p1 = m.player('p1')
    names = [N + 'Tesla', N + 'Tesla Ctl'] + [N + k for k in VICTIMS]
    for k, (_, _, site, dx, dy) in VICTIMS.items():
        t.areas[f'Test FWU {k} Home'] = square(*m.site(site, dx, dy), 30.0)
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1)] +
                            [('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in names] +
                            [('SET_MILLISECOND_TIMER', 'Test Press', PRESS),
                             ('SET_MILLISECOND_TIMER', 'Test Move', PRESS + MOVE_AT),
                             ('SET_MILLISECOND_TIMER', 'Test Kill', PRESS + KILL)]))
    t.scripts.append(Script('Test - press', [('TIMER_EXPIRED', 'Test Press')], [
        ('NAMED_USE_COMMANDBUTTON_ABILITY', N + 'Tesla', TOGGLE), ('SET_FLAG', 'Test Going', 1)]))
    t.scripts.append(Script('Test - move', [('TIMER_EXPIRED', 'Test Move')],
                            [('MOVE_NAMED_UNIT_TO', N + k, m.mark(f'{k} away')) for k in VICTIMS]))
    t.scripts.append(Script('Test - kill', [('TIMER_EXPIRED', 'Test Kill')], [('NAMED_KILL', N + 'Tesla')]))
    going = ('FLAG', 'Test Going', 1)
    home = lambda k: ('NAMED_INSIDE_AREA', N + k, f'Test FWU {k} Home')  # noqa: E731
    rows = {'近车': [(home('H30'), 1), (home('H80'), 1000)],
            '旁人': [(home('C30'), 1), (home('Own'), 1000)],
            '对照': [(home('Ctl'), 1), (('UNIT_HEALTH', N + 'H30', 0, 100), 1000)]}
    t.counters.append(('CNV_FWU_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_FWU_Frames')], once=False))
    for j, (label, conds) in enumerate(rows.items()):
        counter = f'CNV_FWU_Row{j}'
        t.counters.append((counter, label))
        t.scripts.extend(Script(f'Test - {counter} {i}', [going, cond], [('INCREMENT_COUNTER', step, counter)],
                                once=False) for i, (cond, step) in enumerate(conds))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


MISSION = {'engine_fwupdate': mission}
CHECKS = {'engine_fwupdate': {'a': surge}}      # mod CampFWUpdA: 10 characters
