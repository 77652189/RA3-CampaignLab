"""Engine unit test: 变形 (ADR 0019 layer 2; ToggleStatusSpecialAbilityUpdate) -- how long the USER_3 TAKING_OFF
modifier a transform press gives lasts (1.5 s / 1.6 s in the XML: 30 frames for both if ROUND(s) x 15, else 22-23 / 24).

On the Niagara map the player's construction yard; 2000 money set at the start. Each variant keeps one unit (the others
are deleted at the start), held (NO_ATTACK), on open ground of the west field. In the 'Test Go' frame (one second in):

  a  Tengu (JapanAntiInfantryVehicle, Command_JAIV_Transform; modifier 1.5 s): press once. 6 s
  b  Tengu: press at Go, and again at frame 60 (back). 8 s
  c  VX (JapanAntiAirVehicleTech1, Command_JAAVT1_Transform; modifier 1.6 s): press once. 6 s
  d  Tengu: press at Go, and again at frame 10 (while USER_3 is still on). 6 s

Counters (four lines), every one counted from 'Test Go' on:
  帧数   frames since Go
  第二行  1 x frames TRANSFORMATION_TOGGLE_STATE holds + 1000 x frames ModelCondition USER_1 holds
  第三行  1 x frames USER_3 holds + 1000 x frames TAKING_OFF holds
  第四行  1 x frames from Go until TRANSFORMATION_TOGGLE_STATE is first seen + 1000 x frames from Go until USER_3 is
          first seen (a flag is set when seen; the counting script runs before it, so the frame of the first sight
          is not counted)

Bench 11-06 (round 51):
  (the first watch row is already ~27 frames in, so every first change below is before it; contract: the two buttons
  added to contract.RETAIL_COMMANDS). Final readings (帧数 / 第二行 / 第三行 / 第四行):
  a CampTransformA_mcp_1106_032729: 118 / 118118 / 16016 / 1001. Toggle state and USER_1 held every frame from Go to the
    end (118 + 118); USER_3 and TAKING_OFF each held 16 frames (not 30, not 22-23), then off for good. Both seen 1 frame
    after the press (第四行 1 + 1000: one counted frame before each first sight).
  b CampTransformB_mcp_1106_032922: 148 / 59059 / 32032 / 1001. State and USER_1 on 59 frames, off from the press at
    frame 60 (59059 from the row at frame 65 on); USER_3 / TAKING_OFF 16 frames for the first press (16016 until frame
    57), the second press ran another 16 (22022 at 65, 30030 at 73, 32032 at 82): 32 in all, no overlap.
  c CampTransformC_mcp_1106_033115: 118 / 118118 / 16016 / 1001. Same as a: the VX (XML 1.6 s) also 16 frames, as the
    Tengu (1.5 s).
  d CampTransformD_mcp_1106_033307: 118 / 9009 / 25025 / 1001. State and USER_1 on 9 frames (off by the press at 10);
    USER_3 / TAKING_OFF 25 frames in one run from Go: the press at 10 did not add a second 16 (would be 32 or 26 only if
    refreshed at 10: 10 + 15 ~ 25), it extended the window to ~16 frames after the second press.
Against the model (RA3-EngineModel transform.py, tests/test_objects_bench.py "transform"): the on spans (b 59,
d 9), status with USER_1, USER_3 with TAKING_OFF, the trigger starting with the status and a press refreshing it
all match. Two strict xfails: the trigger lasts 16 frames here, the model's ROUND(s) x 15 gives 30; the model
toggles one frame late (2002 against 1001, the Mirage field's open question).
"""
from maps import niagara
from parts import Mission, Script, Test, status

UNITS = {'a': ('JapanAntiInfantryVehicle', 'Command_JAIV_Transform'),
         'b': ('JapanAntiInfantryVehicle', 'Command_JAIV_Transform'),
         'c': ('JapanAntiAirVehicleTech1', 'Command_JAAVT1_Transform'),
         'd': ('JapanAntiInfantryVehicle', 'Command_JAIV_Transform')}
PRESS = {'b': (60,), 'd': (10,)}            # the frames after Go the button is pressed again
RUN = {'a': 6.0, 'b': 8.0, 'c': 6.0, 'd': 6.0}
AT = ('west field', 0.0, 0.0)               # open land away from the yard


def _n(part):
    return f'UNIT - CNV Transform {part}'


def mission():
    m = Mission(name='CampTransform', map=niagara, units=[], facts={})
    m.spawns |= {u for u, _ in UNITS.values()}
    m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
    for w, (u, _) in UNITS.items():
        m.put(u, AT[0], *AT[1:], angle=0.0, role=f'unit {w}', name=_n(f'Unit {w}'))
    return m


def transform_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    unit, button = UNITS[which]
    me = _n(f'Unit {which}')
    start = [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 2000), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0),
             ('UNIT_CHANGE_OBJECT_STATUS', me, 'NO_ATTACK', 1)]
    start += [('NAMED_DELETE', _n(f'Unit {w}')) for w in UNITS if w != which]
    t.scripts.append(Script('Test - start', [], start))
    go = [('NAMED_USE_COMMANDBUTTON_ABILITY', me, button)]
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)

    t.counters.append(('CNV_Transform_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Transform_Frames')], once=False))
    for f in PRESS.get(which, ()):
        t.scripts.append(Script(f'Test - press {f}', [going, ('COUNTER', 'CNV_Transform_Frames', 2, f)],
                                [('NAMED_USE_COMMANDBUTTON_ABILITY', me, button)]))
    tog = ('UNIT_HAS_OBJECT_STATUS', me, status('TRANSFORMATION_TOGGLE_STATE'))
    u1 = ('UNIT_HAS_MODELCONDITION', me, 'USER_1')
    u3 = ('UNIT_HAS_MODELCONDITION', me, 'USER_3')
    taking_off = ('UNIT_HAS_MODELCONDITION', me, 'TAKING_OFF')
    unseen_s, unseen_u = ('FLAG', 'Test Seen State', 0), ('FLAG', 'Test Seen User3', 0)
    rows_by = {2: [(tog, 1), (u1, 1000)], 3: [(u3, 1), (taking_off, 1000)], 4: [(unseen_s, 1), (unseen_u, 1000)]}
    for k, label in ((2, '第二行'), (3, '第三行'), (4, '第四行')):
        t.counters.append((f'CNV_Transform_Row{k}', label))
        for j, (cond, step) in enumerate(rows_by[k]):
            t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                    [('INCREMENT_COUNTER', step, f'CNV_Transform_Row{k}')], once=False))
    # the markers are set after the counting scripts ran, so the frame a thing is first seen is not counted
    t.scripts.append(Script('Test - seen state', [going, tog], [('SET_FLAG', 'Test Seen State', 1)], once=False))
    t.scripts.append(Script('Test - seen user3', [going, u3], [('SET_FLAG', 'Test Seen User3', 1)], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN[which])]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN[which]))]
    return t


MISSION = {'engine_transform': mission}
CHECKS = {'engine_transform': {w: (lambda m, w=w: transform_test(m, w)) for w in 'abcd'}}
