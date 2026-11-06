"""Engine unit test: stance (ADR 0019 layer 2; StancesBehavior) -- does HOLD_FIRE stop a shooting unit, does it stop a
standing order, does an idle unit fire by itself, does a held unit hit back.

On the festival map's west field a player's guardian tank A (AlliedAntiVehicleVehicleTech1) and an enemy (s1) guardian
T 150 away (in range, as in engine_attack); 2000 money; map revealed. T carries NO_ATTACK from the start (not in e). In
the 'Test Go' frame (one second in) each variant does (stance integers: GUARD 0, AGGRESSIVE 1, HOLD_POSITION 2,
HOLD_FIRE 3, all set with UNIT_SET_STANCE; "frame n" = the n-th frame of the 帧数 counter):

  a  mid     Go: A ordered to attack T (NAMED_ATTACK_NAMED); frame 45: A set to HOLD_FIRE
  b  held    A set to HOLD_FIRE before Go; Go: A ordered to attack T
  c  idle    nothing at all (A default stance, T cannot shoot)
  d  idleHF  as c, A set to HOLD_FIRE before Go
  e  hitback A set to HOLD_FIRE before Go; T not NO_ATTACK; Go: T ordered to attack A
  f  resume  as a; frame 90: A set back to GUARD

Counters (four lines), every one counted from 'Test Go' on:
  帧数   frames since Go
  T状态  1 x frames T is at full health + 1000 x frames it is below (first drop = frame count of the 1 part + 1)
  T血量  T's health in percent, set every frame
  A血量  A's health in percent, set every frame (e)

Bench 11-06 (first row already ~28 frames in; T hits are 12.5 percent each, ~7 frames after a row seen at 87/75/...):
  a CampStanceA_mcp_1106_025915: T 100 -> 87 (first drop frame 16) -> 75 (between frames 44 and 51, i.e. a shot
    already flying or fired at the stance frame); then 75 to frame 179: no more hits. HOLD_FIRE stops a standing order.
  b CampStanceB_mcp_1106_030114: HOLD_FIRE before the order does NOT stop it: 87 (frame 16), 75, 62 (<=81), 50 (<=128),
    37 (<=142), 25 (<=173), 12 (<=200); a hit about every 45-50 frames. The order beats the stance.
  c CampStanceC_mcp_1106_030325: A fires by itself, default stance: first drop frame 13 (12015 at frame 27), then
    75, 62, 50, 37, 25 at the same rhythm as b.
  d CampStanceD_mcp_1106_030532: A set HOLD_FIRE, no order: T 100 throughout (T状态 = 帧数 to frame 180), no fire.
  e CampStanceE_mcp_1106_030744: A held, T ordered to attack A: A 87 -> 75 -> 62 -> 50 -> 37 -> 25 (first seen
    87 at frame 29); T stays 100 all the way: a held unit does not hit back.
  f CampStanceF_mcp_1106_030945: as a, GUARD at frame 90: 87, 75 (<=52), none to frame ~90, then 62 (<=98), 50
    (<=129), 37 (<=158): the original order is still there and runs again.
Against the model (RA3-EngineModel stance.py + weapons.py, tests/test_objects_bench.py "stance", run with real
weapons): a, b, d, e, f the same (the hits' frames inside the bench's row bounds); c differs (strict xfail): idle
auto-acquire is the AI layer, not modelled, the model's A never fires without an order.
"""
from maps import festival
from parts import Mission, Script, Test, counted

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
RUN = 10.0
HOLD_FIRE, GUARD = 3, 0
SPOT = ('west field', 0, -150)


def _n(part):
    return f'UNIT - CNV Stance {part}'


def mission():
    m = Mission(name='CampStance', map=festival, facts={})
    m.put(GUARDIAN, SPOT[0], SPOT[1], SPOT[2], name=_n('A'), role='guard A')
    m.put(GUARDIAN, SPOT[0], SPOT[1], SPOT[2] + 150, side='s1', name=_n('T'), role='guard T')
    return m


def stance_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    A, T = m.role('guard A').name, m.role('guard T').name
    start = [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 2000), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    if which != 'e':
        start.append(('UNIT_CHANGE_OBJECT_STATUS', T, 'NO_ATTACK', 1))
    if which in 'bde':
        start.append(('UNIT_SET_STANCE', A, HOLD_FIRE))
    t.scripts.append(Script('Test - start', [], start))
    go = []
    if which in 'abf':
        go.append(('NAMED_ATTACK_NAMED', A, T))
    if which == 'e':
        go.append(('NAMED_ATTACK_NAMED', T, A))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)

    t.counters.append(('CNV_Stance_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Stance_Frames')], once=False))
    if which in 'af':
        t.scripts.append(Script('Test - hold fire', [going, ('COUNTER', 'CNV_Stance_Frames', 2, 45)],
                                [('UNIT_SET_STANCE', A, HOLD_FIRE)]))
    if which == 'f':
        t.scripts.append(Script('Test - guard', [going, ('COUNTER', 'CNV_Stance_Frames', 2, 90)],
                                [('UNIT_SET_STANCE', A, GUARD)]))

    t.counters.append(('CNV_Stance_TState', 'T状态'))
    for j, (cond, step) in enumerate(((('UNIT_HEALTH', T, 3, 100), 1), (('UNIT_HEALTH', T, 0, 100), 1000))):
        t.scripts.append(Script(f'Test - tstate {j}', [going, cond], [('INCREMENT_COUNTER', step, 'CNV_Stance_TState')],
                                once=False))
    counted('CNV_Stance_THp', 'T血量', t, health=T)
    counted('CNV_Stance_AHp', 'A血量', t, health=A)
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


MISSION = {'engine_stance': mission}
CHECKS = {'engine_stance': {w: (lambda m, w=w: stance_test(m, w)) for w in 'abcdef'}}
