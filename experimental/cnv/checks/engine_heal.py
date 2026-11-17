"""Engine unit test: self-healing (AutoHealBehavior) -- how fast a hurt unit mends, whether it waits after a hit,
which unit needs a state or a rank to mend at all.

On the Niagara map one unit of the player's alone in the west field (NO_ATTACK from the start). One second in
('Test Go') each variant hurts it by script:

  a  apoc     Apocalypse (3000 health; 2 points every 7 frames, waits 15 frames after a hurt): 600 damage at Go
  b  apoc2    as a, plus 30 more damage at frame 40
  c  tsunami  Tsunami tank (380; mends only in GENERIC_TOGGLE_STATE, 3 points every 3 frames, no wait): state on
              before Go, 76 damage at Go
  d  late     as c with the state off at the start: 76 damage at Go, the state on at frame 20, 1 more damage at 60
  e  hero     Allied GI (150; mends from the hero rank only, 1 point every 7 frames): 30 damage (20 %) at Go,
              1800 experience points (the XP of rank 4) at frame 30

Counters (three lines), counted from 'Test Go' on:
  帧数    frames since Go
  低血    1 x frames the health percent is below T1 + 1000 x frames it is below T2
          (T1 / T2: a, b, e 81 / 82; c 81 / 85; d 80 / 81)
  血量    the unit's health in percent (rounded down)

Bench 11-06 (end readings 帧数 / 低血 / 血量; the OCR'd counters run ~7 frames per half second):
  a CampHealA_mcp_1106_021956: 301 / 219114 / 82. 80 held to s6, 81 from s7 (frame ~115: 81 reached 114 frames
    after Go, 82 at 219).
  b CampHealB_mcp_1106_022404: 300 / 300230 / 81. 79 after the 30 hit at frame 40, back to 80 at s8, 81 at s14.
  c CampHealC_mcp_1106_022200: 149 / 20005 / 100. 80 at Go, 87 at s1, 100 by s4 (frame ~81).
  d CampHealD_mcp_1106_022611: 181 / 64002 / 100. 80 flat until the state is on (frame 20) -- it does not mend
    before the hit at frame 60 (79), then 81 at frame 67, 100 at s8.
  e CampHealE_mcp_1106_022823: 300 / 52038 / 100. 80 at Go; mends from the start (81 at s2, before the XP at
    frame 30), 100 at s18; 低血 stops at 38 (T1 81) and 52 (T2 82).
Against the model (RA3-EngineModel, tools/objsidebyside.py engine_heal): a, b, c, d the same counters to the digit
(a 219114, b 230 below T2, c 20005, d 64002); e differs: the model's T2 count stops at 45 (the bench 52).

"""
import resources
from maps import niagara
from parts import Mission, Script, Test

APOC, TSUNAMI, GI = 'SovietAntiVehicleVehicleTech3', 'JapanAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
UNIT = {'a': 0, 'b': 0, 'c': 1, 'd': 1, 'e': 2}      # which of the three stands in this variant
HURT = {'a': 600, 'b': 600, 'c': 76, 'd': 76, 'e': 30}   # MaxHealth 3000 / 380 / 150: 20 %, 20 %, 20 %
LOW = {'a': (81, 82), 'b': (81, 82), 'c': (81, 85), 'd': (80, 81), 'e': (81, 82)}
RUN = {'a': 18.0, 'b': 18.0, 'c': 8.0, 'd': 10.0, 'e': 18.0}
XP = 1800                                   # RequiredExperience of AlliedAntiInfantryInfantryExperienceLevel_4
SITE = ('west field', -120.0, 260.0)


def _n(part):
    return f'UNIT - CNV Heal {part}'


def mission():
    m = Mission(name='CampHeal', map=resources.measured(niagara), units=[], facts={})
    for k, template in enumerate((APOC, TSUNAMI, GI)):         # all three stand; a variant deletes the other two
        m.put(template, SITE[0], SITE[1], SITE[2] + 120.0 * k, angle=0.0, role=f'unit {k}', name=_n(f'Unit {k}'))
    return m


def build_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    unit = _n(f'Unit {UNIT[which]}')
    start = [('MAP_REVEAL_ALL_PERM', p1), ('UNIT_CHANGE_OBJECT_STATUS', unit, 'NO_ATTACK', 1),
             ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    start += [('NAMED_DELETE', _n(f'Unit {k}')) for k in range(3) if k != UNIT[which]]
    if which == 'c':
        start.append(('UNIT_CHANGE_OBJECT_STATUS', unit, 'GENERIC_TOGGLE_STATE', 1))
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')],
                            [('NAMED_DAMAGE', unit, HURT[which]), ('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)

    t.counters.append(('CNV_Heal_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Heal_Frames')], once=False))
    at = lambda f: [going, ('COUNTER', 'CNV_Heal_Frames', 2, f)]
    if which == 'b':
        t.scripts.append(Script('Test - hurt again', at(40), [('NAMED_DAMAGE', unit, 30)]))
    if which == 'd':
        t.scripts.append(Script('Test - state on', at(20), [('UNIT_CHANGE_OBJECT_STATUS', unit, 'GENERIC_TOGGLE_STATE', 1)]))
        t.scripts.append(Script('Test - hurt late', at(60), [('NAMED_DAMAGE', unit, 1)]))
    if which == 'e':
        t.scripts.append(Script('Test - rank', at(30), [('UNIT_GIVE_EXPERIENCE_POINTS', unit, XP)]))

    t.counters.append(('CNV_Heal_Low', '低血'))
    t1, t2 = LOW[which]
    t.scripts += [Script(f'Test - low {k}', [going, ('UNIT_HEALTH', unit, 0, v)],
                         [('INCREMENT_COUNTER', step, 'CNV_Heal_Low')], once=False)
                  for k, (v, step) in enumerate(((t1, 1), (t2, 1000)))]

    t.counters.append(('CNV_Heal_Health', '血量'))
    t.scripts.append(Script('Test - health', [going], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', unit,
                                                        'CNV_Heal_Health')], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN[which])]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN[which]))]
    return t


MISSION = {'engine_heal': mission}
CHECKS = {'engine_heal': {w: (lambda m, w=w: build_test(m, w)) for w in 'abcde'}}
