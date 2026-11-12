"""Engine unit test: selling (ADR 0019 layer 2) -- what SELL_OBJECT does to a structure: the money back, how long it
takes, whether it is counted as power meanwhile, what happens to a garrison, to a half-built one, to a hurt one.

On the Niagara map the player's construction yard (+50 power), a power plant (+100, cost 800, 1000 health) and
the three barracks of engine_build (deleted: not needed); 2000 money set at the start. In the 'Test Go' frame (one
second in) each variant sells its target:

  a  full    the map's power plant
  b  half    as a, health set to 500 before Go
  c  unpack  the map's plant deleted; one made by script at Go (unpacks 46 frames); sold at frame 10 of the count
  d  bunker  a SovietBunker for the player (cost 500) with two Allied peacekeepers garrisoned instantly at the
             start (NO_ATTACK); the bunker is sold at Go
  e  killed  as a; 5000 damage at frame 5 (killed half way through the sale)
  f  twice   as a; SELL_OBJECT written twice in the Go actions

Counters (four lines), every one counted from 'Test Go' on:
  帧数   frames since Go
  资金   the player's money
  卖帧   1 x frames the target is not destroyed + 1000 x frames it carries SOLD
  第四行  a-c, e, f: 1 x frames excess power >= 150 (the plant still counts) + 1000 x frames excess power <= 50
          d: 1 x frames the first peacekeeper is alive + 1000 x frames it is ENCLOSED (still in the bunker)

Bench 11-06 (round 49; the counters read from s1 on, the first row already 26-29 frames in; one run each):
  a CampSellA_mcp_1106_021303: 资金 2000 -> 2400 (half of the 800) by frame 28; 卖帧 31031; 第四行 31 then 1000 a
    frame: SOLD from frame 1, the plant gone at frame 31 and counted as power until then.
  b CampSellB_mcp_1106_021504: 2000 -> 2200 by frame 27 (800 x 0.5 x health 0.5); 卖帧 31031; 第四行 as a.
  c CampSellC_mcp_1106_021657: sold at frame 10 of the unpack: NOTHING -- 资金 2000, 卖帧 = 帧数 (never SOLD,
    never gone), 第四行 46 frames of no power (46000) then the plant counts (46004 ... 46071): refused while it
    unpacks.
  d CampSellD_mcp_1106_022301 (2nd try; the 1st, garrison in the start script, read the same): 资金 2000 -> 2250
    (half of 500); 卖帧 31031; 第四行 = frames only: the first peacekeeper alive throughout, ENCLOSED never seen
    (the garrison did not take, or the bunker does not give that status: open, not looked into).
  e CampSellE_mcp_1106_022507: killed at frame 5: 资金 2400 (the refund comes at the start of the sale); 卖帧 5004
    (gone after 4 frames, SOLD 5); 第四行 4 then 1000 a frame: the power goes with it.
  f CampSellF_mcp_1106_022713: SELL_OBJECT twice: 2400 (paid once); 卖帧 31031; 第四行 as a.
Against the model (RA3-EngineModel sell.py, tests/test_objects_bench.py "selling"): every final reading and the
frames after the first row the same, d included (the model empties the bunker in the sell's frame).
"""
import resources
from maps import niagara
from parts import Mission, Script, Test, status

PLANT, BUNKER, MAN = 'AlliedPowerPlant', 'SovietBunker', 'AlliedAntiInfantryInfantry'
RUN = 6.0
BUILD = ('west field', -120.0, 260.0)


def _n(part):
    return f'UNIT - CNV Sell {part}'


def mission():
    m = Mission(name='CampSell', map=resources.measured(niagara), units=[], facts={})
    m.spawns |= {PLANT}
    m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
    m.put(PLANT, 'base power', angle=0.0, role='power', name=_n('Power'))
    m.put(BUNKER, *BUILD[:1], BUILD[1], BUILD[2], angle=0.0, role='bunker', name=_n('Bunker'))
    for k in range(2):
        m.put(MAN, BUILD[0], BUILD[1] + 150.0, BUILD[2] + 60.0 * k, angle=0.0, role=f'man {k}', name=_n(f'Man {k}'))
    m.waypoint('build spot', 'Test Build Spot', *BUILD)
    return m


def sell_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    d = which == 'd'
    target = _n('Bunker') if d else (_n('Made') if which == 'c' else _n('Power'))
    gone = [_n('Bunker'), _n('Man 0'), _n('Man 1')] if not d else [_n('Power')]
    if which == 'c':
        gone.append(_n('Power'))
    start = [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 2000), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    start += [('NAMED_DELETE', n) for n in gone]
    if which == 'b':
        start.append(('NAMED_DAMAGE', target, 500))
    if d:
        for k in range(2):
            start.append(('UNIT_CHANGE_OBJECT_STATUS', _n(f'Man {k}'), 'NO_ATTACK', 1))
        start.append(('SET_MILLISECOND_TIMER', 'Test In', 0.4))
        t.scripts.append(Script('Test - in', [('TIMER_EXPIRED', 'Test In')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', _n(f'Man {k}'), target) for k in range(2)]))
    t.scripts.append(Script('Test - start', [], start))
    go = []
    if which == 'c':
        go.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', target, PLANT, m.team('p1'), 'Test Build Spot'))
    else:
        go += [('SELL_OBJECT', target)] * (2 if which == 'f' else 1)
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)

    t.counters.append(('CNV_Sell_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Sell_Frames')], once=False))
    if which == 'c':
        t.scripts.append(Script('Test - sell', [going, ('COUNTER', 'CNV_Sell_Frames', 2, 10)],
                                [('SELL_OBJECT', target)]))
    if which == 'e':
        t.scripts.append(Script('Test - kill', [going, ('COUNTER', 'CNV_Sell_Frames', 2, 5)],
                                [('NAMED_DAMAGE', target, 5000)]))

    t.counters.append(('CNV_Sell_Money', '资金'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Sell_Money')], once=False))

    t.counters.append(('CNV_Sell_Sold', '卖帧'))
    for cond, step, nm in ((('NAMED_NOT_DESTROYED', target), 1, 'alive'),
                           (('UNIT_HAS_OBJECT_STATUS', target, status('SOLD')), 1000, 'sold')):
        t.scripts.append(Script(f'Test - {nm}', [going, cond], [('INCREMENT_COUNTER', step, 'CNV_Sell_Sold')],
                                once=False))

    t.counters.append(('CNV_Sell_Four', '第四行'))
    if d:
        rows = [(('NAMED_NOT_DESTROYED', _n('Man 0')), 1), (('UNIT_HAS_OBJECT_STATUS', _n('Man 0'),
                                                              status('ENCLOSED')), 1000)]
    else:
        rows = [(('PLAYER_EXCESS_POWER_COMPARE_VALUE', p1, 3, 150), 1),
                (('PLAYER_EXCESS_POWER_COMPARE_VALUE', p1, 0, 51), 1000)]
    for k, (cond, step) in enumerate(rows):
        t.scripts.append(Script(f'Test - four {k}', [going, cond], [('INCREMENT_COUNTER', step, 'CNV_Sell_Four')],
                                once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, RUN)]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN))]
    return t


MISSION = {'engine_sell': mission}
CHECKS = {'engine_sell': {w: (lambda m, w=w: sell_test(m, w)) for w in 'abcdef'}}
