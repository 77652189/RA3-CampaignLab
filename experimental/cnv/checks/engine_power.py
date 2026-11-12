"""Engine unit test: a superweapon's cooldown and a unit's toggle ability (ADR 0019 layer 2) -- what scripts can do to the
Soviet superweapon building's special power (set the countdown, fire it, read ready / triggered) and the Mirage tank's
field button.

On the Niagara map the player's construction yard (+50 power), a power plant (+100), three barracks (-25 each), a
Soviet superweapon building (SovietSuperWeapon, -75 power, SpecialPowerIronCurtain, ReloadTime 180 s, not available at
start) in the west field, a Mirage tank next to it and a cast point away from both. One second in ('Test Go') each
variant does one thing; at the start it deletes what it does not need:

  a  countdown  Go: SET_COUNTDOWN 5 s; frame 120: fire the power at the cast point; frame 150: SET_COUNTDOWN 2 s. 14 s
  b  fire       no countdown; fire at frames 10, 11 and 12 (the map's building: ready at the start? fired in the
                reload?). 6 s
  c  built      the map's building deleted; Go: made by script (unpack 30 s ~ 450 frames); fire at frame 60. 36 s
  d  dark       plant and barracks deleted (power 50 - 75 = -25); Go: SET_COUNTDOWN 5 s. 10 s
  e  mirage     Go: NAMED_USE_COMMANDBUTTON_ABILITY Command_ToggleMirageField; again at frames 10, 40 and 80. 8 s

Counters (four lines), every one counted from 'Test Go' on, frames added per frame while the thing holds:
  帧数    frames since Go
  就绪帧  (a-d) SKIRMISH_SPECIAL_POWER_READY: 1 x frames before frame 120 + 1000 x frames from 120 on
          (e) the Mirage tank's GENERIC_TOGGLE_STATE: 1 x before frame 40, 1000 x from 40, 1000000 x from 80 on
  施放数  frames PLAYER_TRIGGERED_SPECIAL_POWER (read once, then cleared) holds
  效果帧  frames the player owns an IronCurtainEffect (the power's OCL object) + (c) 1000 x frames the building is
          UNPACKING

Bench 11-05 (round 47), final readings (帧数 / 就绪帧 / 施放数 / 效果帧; watch rows are every ~7 frames):
  a CampPowerA_mcp_1105_230155: 239 / 0 / 1 / 0. 就绪帧 0 throughout: SET_COUNTDOWN 5 s at Go did NOT make the power
    ready within 232 frames. 施放数 first 1 in the row at frame 125 (fire at 120; read once), never again. 效果帧 0.
    Side tries (spec value restored): countdown 0 at Go (CampPowerA_mcp_1105_231211): ready every frame from Go (就绪帧
    = 帧数 up to 119), after the fire at 120 it goes 0 for good (119 at the end; the 2 s set at 150 did not bring it
    back in 88 frames); countdown 1 at Go (CampPowerA_mcp_1105_231414): 就绪帧 0 for 238 frames. So any countdown > 0
    kept it not ready for 15 s; the unit of the argument is not yet known (minutes? retail passes 480 for a 480 s timer).
  b CampPowerB_mcp_1105_230356: 118 / 0 / 3 / 0. The map-placed building is NOT ready at the start (就绪帧 0 from Go);
    the three scripted fires (frames 10-12) were all counted: 施放数 3 already in the first row (frame 28), although the
    power was not ready. 效果帧 0 (no IronCurtainEffect owned by Player_1 seen; the frame shows no effect either).
  c CampPowerC_mcp_1105_230549: 571 / 0 / 1 / 451000. Made by script: UNPACKING 451 frames (30 s x 15 + 1), then stops;
    就绪帧 0 (not ready); 施放数 1 in the row at frame 64 (fire at 60, while it was unpacking); 效果帧 0.
  d CampPowerD_mcp_1105_230804: 178 / 0 / 0 / 0. Dark (power -25) and countdown 5: not ready; nothing else to see
    (the same as a with the 5 s: the countdown 5 never makes it ready here, power or no power).
  e CampPowerE_mcp_1105_230956: 148 / 40009 / 0 / 0. GENERIC_TOGGLE_STATE: on 9 frames after Go (the button at Go works,
    turned off by the press at 10), off 10-39, on 40-79 (40 frames: 40009 at frame 80), off from 80 (no 1000000 step,
    the counter stays 40009). All four presses work, one toggle each.
Open: why a countdown > 0 never gave ready (try minutes, or 480 as retail), and whether the power's effect object is
owned by Player_1 / what it is called in the game (效果帧 0 in every variant, also after the ready fire in a-with-0).
"""
import resources
from maps import niagara
from parts import Mission, Script, Test, square, status

SUPER, POWER, EFFECT, MIRAGE = 'SovietSuperWeapon', 'SpecialPowerIronCurtain', 'IronCurtainEffect', \
                               'AlliedAntiVehicleVehicleTech3'
TOGGLE = 'Command_ToggleMirageField'
RUN = {'a': 14.0, 'b': 6.0, 'c': 36.0, 'd': 10.0, 'e': 8.0}
IC_AT = ('west field', 100.0, -175.0)       # the building's pad (1280, 2200)
MIRAGE_AT = ('west field', -100.0, 300.0)   # (1080, 2675)
CAST_AT = ('west field', -400.0, 100.0)     # the cast point (780, 2475), away from the building
DELETE = {'a': ('Mirage',), 'b': ('Mirage',), 'c': ('Mirage', 'IC'),
          'd': ('Mirage', 'Power', 'Barracks 1', 'Barracks 2', 'Barracks 3'), 'e': ('IC',)}
FIRE = {'a': (120,), 'b': (10, 11, 12), 'c': (60,)}     # the frames a script fires the power at
COUNTDOWN = {'a': ((None, 5), (150, 2)), 'd': ((None, 5),)}   # (frame or None = at Go, seconds)
PRESS = (10, 40, 80)                                     # e: the frames the field button is pressed again


def _n(part):
    return f'UNIT - CNV Power {part}'


def mission():
    m = Mission(name='CampPower', map=resources.measured(niagara), units=[], facts={})
    m.spawns |= {SUPER, EFFECT}
    m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
    m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power', name=_n('Power'))
    for k, dy in enumerate((0.0, 140.0, 280.0)):
        m.put('AlliedBarracks', 'base factory', 0.0, dy, angle=3.1416, role=f'barracks {k + 1}',
              name=_n(f'Barracks {k + 1}'))
    m.put(SUPER, IC_AT[0], *IC_AT[1:], angle=0.0, role='ic', name=_n('IC'))
    m.put(MIRAGE, MIRAGE_AT[0], *MIRAGE_AT[1:], angle=0.0, role='mirage', name=_n('Mirage'))
    m.waypoint('ic spot', 'Test IC Spot', *IC_AT)
    m.waypoint('cast spot', 'Test Cast Spot', *CAST_AT)
    return m


def power_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    cx, cy = m.waypoints['Test Cast Spot']
    t.areas['Test Target'] = square(cx, cy, 2500.0)
    ic, mirage = _n('IC'), _n('Mirage')
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    start += [('NAMED_DELETE', _n(p)) for p in DELETE[which]]
    t.scripts.append(Script('Test - start', [], start))
    go = []
    if which == 'c':
        go.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', ic, SUPER, m.team('p1'), 'Test IC Spot'))
    if which == 'e':
        go.append(('NAMED_USE_COMMANDBUTTON_ABILITY', mirage, TOGGLE))
    for at, secs in COUNTDOWN.get(which, ()):
        if at is None:
            go.append(('NAMED_SET_SPECIAL_POWER_COUNTDOWN', ic, POWER, secs))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)

    t.counters.append(('CNV_Power_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Power_Frames')], once=False))

    def frame(op, v):
        return ('COUNTER', 'CNV_Power_Frames', op, v)
    for f in FIRE.get(which, ()):
        t.scripts.append(Script(f'Test - fire {f}', [going, frame(2, f)],
                                [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', ic, POWER, 'Test Cast Spot')]))
    for f, secs in COUNTDOWN.get(which, ()):
        if f is not None:
            t.scripts.append(Script(f'Test - countdown {f}', [going, frame(2, f)],
                                    [('NAMED_SET_SPECIAL_POWER_COUNTDOWN', ic, POWER, secs)]))
    if which == 'e':
        for f in PRESS:
            t.scripts.append(Script(f'Test - press {f}', [going, frame(2, f)],
                                    [('NAMED_USE_COMMANDBUTTON_ABILITY', mirage, TOGGLE)]))

    t.counters.append(('CNV_Power_Ready', '就绪帧'))
    if which == 'e':
        on = ('UNIT_HAS_OBJECT_STATUS', mirage, status('GENERIC_TOGGLE_STATE'))
        steps = [([frame(0, 40)], 1), ([frame(3, 40), frame(0, 80)], 1000), ([frame(3, 80)], 1000000)]
    else:
        on = ('SKIRMISH_SPECIAL_POWER_READY', p1, POWER)
        steps = [([frame(0, 120)], 1), ([frame(3, 120)], 1000)]
    for k, (cond, step) in enumerate(steps):
        t.scripts.append(Script(f'Test - ready {k}', [going, on] + cond, [('INCREMENT_COUNTER', step,
                                                                           'CNV_Power_Ready')], once=False))

    t.counters.append(('CNV_Power_Cast', '施放数'))
    t.scripts.append(Script('Test - cast', [going, ('PLAYER_TRIGGERED_SPECIAL_POWER', p1, POWER)],
                            [('INCREMENT_COUNTER', 1, 'CNV_Power_Cast')], once=False))

    t.counters.append(('CNV_Power_Effect', '效果帧'))
    t.scripts.append(Script('Test - effect', [going, ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, 1,
                                                       EFFECT, 'Test Target')],
                            [('INCREMENT_COUNTER', 1, 'CNV_Power_Effect')], once=False))
    if which == 'c':
        t.scripts.append(Script('Test - unpacking', [going, ('UNIT_HAS_OBJECT_STATUS', ic, status('UNPACKING'))],
                                [('INCREMENT_COUNTER', 1000, 'CNV_Power_Effect')], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN[which])]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN[which]))]
    return t


MISSION = {'engine_power': mission}
CHECKS = {'engine_power': {w: (lambda m, w=w: power_test(m, w)) for w in 'abcde'}}
