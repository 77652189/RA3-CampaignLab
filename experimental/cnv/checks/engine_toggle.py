"""Engine unit test: ToggleStatusSpecialAbilityUpdate on the units our 9 levels place -- what a script's button press
does to the ObjectStatus of each ToggleState, when, and with PackTime / UnpackTime / a first state that has bits.

On the Niagara map, the player's construction yard; each variant keeps one unit (the others deleted at the start),
held (NO_ATTACK), on open ground of the west field. Presses are NAMED_USE_COMMANDBUTTON_ABILITY at the given frames
after 'Test Go' (one second in). Two ObjectStatus bits are read per variant (A, B):

  a  Peacekeeper (AlliedAntiInfantryInfantry, riot shield; PackTime 0s). A GENERIC_TOGGLE_STATE, B CAN_CONTEST_GARRISON.
     Presses at 0 and 60.
  b  Conscript (SovietAntiInfantryInfantry, Molotov; PackTime 1s). A GENERIC_TOGGLE_STATE, B ANTI_GARRISON. 0 and 60.
  c  Hammer (SovietAntiVehicleVehicleTech1, leech beam; the FIRST state has GENERIC_TOGGLE_STATE, the second
     SWITCHED_WEAPONS). A GENERIC_TOGGLE_STATE, B SWITCHED_WEAPONS. Presses at 30 and 90.
  d  Engineer (AlliedEngineer, heal tent; UnpackTime 1s PackTime 1s; three ToggleStates, the first two empty).
     A GENERIC_TOGGLE_STATE, B UNPACKING. Presses at 0, 60, 120.
  e  Sickle (SovietScoutVehicle, binary weapons; WEAPON_UPGRADED_01 in the first state, _02 in the second).
     A WEAPON_UPGRADED_01, B WEAPON_UPGRADED_02. Presses at 30 and 90.
  f  Tesla trooper (SovietHeavyAntiVehicleInfantry, short circuit; GENERIC_TOGGLE_STATE IMMOBILE IGNORING_STEALTH).
     A GENERIC_TOGGLE_STATE, B IMMOBILE. Presses at 0 and 60.

Counters (four lines), every one counted from 'Test Go' on (the counting scripts run before the marker scripts, so a
frame a bit is first seen on / off is not counted):
  帧数   frames since Go
  第二行  frames A holds + 1000 x frames B holds
  第三行  frames until A is first seen on + 1000 x the same for B (a bit never on counts every frame)
  第四行  frames until A is first seen off after having been on + 1000 x the same for B

Predictions from the data and work/re/l2_ability.md (the press: index + 1 modulo the states, the old state's bits off,
the new one's on in one call; the transform bench: seen 1 frame after the press): a 第三行 1001, 第四行 61061;
c / e: A on from the start (第三行 x000), off 1 frame after the press at 30, B on 31; d: the first press enters the
empty second state (nothing seen), the second the tent's (A at 61, or later by UnpackTime 15 frames: INFERRED);
b / f: PackTime 1 s may hold the leave 15 frames (INFERRED).

Bench 11-11 (round 156, run_queue one at a time, all PASS; rows at frame n, the same from s4 on):
  a CampToggle 02:36  59059 / 1001 / 1001: A and B on 1-59 (seen the press's frame), off by the press at 60.
  b 02:39             59059 / 1001 / 1001: the same -- PackTime 1 s delays neither the on nor the off.
  c 02:41  at n=163: 60103 / 30001 / 30031: GENERIC_TOGGLE_STATE from the start (the first ToggleState), off by the
                      press at 30, SWITCHED_WEAPONS 30-89, GENERIC back from 90 (A = n - 60).
  d 02:43  at n=163:   147 / 163017 / 163163: the tent's GENERIC_TOGGLE_STATE first seen 16 frames after the press
                      (UnpackTime 1 s), then held: the presses at 60 and 120 change nothing; UNPACKING never seen.
  e 02:45  at n=164: 60104 / 30001 / 30031: as c, WEAPON_UPGRADED_01 -> _02 -> _01.
  f 02:48  at n=163: 163163 / 1001 / 1001: on from the press for good, the press at 60 (reload 1 s) does nothing.
  第四行 1001 where A / B come on with the press: the NOT flag is set at the frame's top, before the press (model.unnot),
  so that frame reads 'lost' -- 第四行 says nothing there; 第二行 gives the off frame.
  The two that take no second press are the two whose on state has DisabledType="HELD" (INFERRED the cause; a run
  pressing a HELD-free 3-state toggle, or the engineer after a NAMED_STOP, would tell).
"""
from maps import niagara
from parts import NOT, Mission, Script, Test, status

UNITS = {'a': ('AlliedAntiInfantryInfantry', 'Command_ToggleRiotShieldSpecialPower', 'GENERIC_TOGGLE_STATE',
               'CAN_CONTEST_GARRISON', (0, 60)),
         'b': ('SovietAntiInfantryInfantry', 'Command_ToggleMolotovCocktailSpecialPower', 'GENERIC_TOGGLE_STATE',
               'ANTI_GARRISON', (0, 60)),
         'c': ('SovietAntiVehicleVehicleTech1', 'Command_ToggleLeechBeam', 'GENERIC_TOGGLE_STATE', 'SWITCHED_WEAPONS',
               (30, 90)),
         'd': ('AlliedEngineer', 'Command_ToggleAlliedEngineerHeal', 'GENERIC_TOGGLE_STATE', 'UNPACKING', (0, 60, 120)),
         'e': ('SovietScoutVehicle', 'Command_ToggleBinaryWeapon', 'WEAPON_UPGRADED_01', 'WEAPON_UPGRADED_02', (30, 90)),
         'f': ('SovietHeavyAntiVehicleInfantry', 'Command_ToggleShortCircuit', 'GENERIC_TOGGLE_STATE', 'IMMOBILE',
               (0, 60))}
RUN = 12.0
AT = ('west field', 0.0, 0.0)               # open land away from the yard


def _n(part):
    return f'UNIT - CNV Toggle {part}'


def mission():
    m = Mission(name='CampToggle', map=niagara, units=[], facts={})
    m.spawns |= {u[0] for u in UNITS.values()}
    m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
    for w, u in UNITS.items():
        m.put(u[0], AT[0], *AT[1:], angle=0.0, role=f'unit {w}', name=_n(f'Unit {w}'))
    return m


def toggle_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    unit, button, a_bit, b_bit, presses = UNITS[which]
    me = _n(f'Unit {which}')
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0),
             ('UNIT_CHANGE_OBJECT_STATUS', me, 'NO_ATTACK', 1)]
    start += [('NAMED_DELETE', _n(f'Unit {w}')) for w in UNITS if w != which]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)
    t.counters.append(('CNV_Toggle_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Toggle_Frames')], once=False))
    for f in presses:
        when = [('TIMER_EXPIRED', 'Test Go')] if f == 0 else [going, ('COUNTER', 'CNV_Toggle_Frames', 2, f)]
        t.scripts.append(Script(f'Test - press {f}', when, [('NAMED_USE_COMMANDBUTTON_ABILITY', me, button)]))
    bits = {'A': ('UNIT_HAS_OBJECT_STATUS', me, status(a_bit)), 'B': ('UNIT_HAS_OBJECT_STATUS', me, status(b_bit))}
    step = {'A': 1, 'B': 1000}
    rows = {2: [([going, c], step[k]) for k, c in bits.items()],
            3: [([going, ('FLAG', f'Test Seen {k}', 0)], step[k]) for k in bits],
            4: [([going, ('FLAG', f'Test Lost {k}', 0)], step[k]) for k in bits]}
    for k, label in ((2, '第二行'), (3, '第三行'), (4, '第四行')):
        t.counters.append((f'CNV_Toggle_Row{k}', label))
        for j, (conds, n) in enumerate(rows[k]):
            t.scripts.append(Script(f'Test - row {k} {j}', conds, [('INCREMENT_COUNTER', n, f'CNV_Toggle_Row{k}')],
                                    once=False))
    for k, c in bits.items():                   # markers after the counting scripts
        t.scripts.append(Script(f'Test - seen {k}', [going, c], [('SET_FLAG', f'Test Seen {k}', 1)], once=False))
        t.scripts.append(Script(f'Test - lost {k}', [going, ('FLAG', f'Test Seen {k}', 1), c + (NOT,)],
                                [('SET_FLAG', f'Test Lost {k}', 1)], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


MISSION = {'engine_toggle': mission}
CHECKS = {'engine_toggle': {w: (lambda m, w=w: toggle_test(m, w)) for w in UNITS}}
