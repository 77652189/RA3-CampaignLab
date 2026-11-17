"""Engine unit test: 开出地图外 (ADR 0019 layer 2; RunOffMapBehavior) -- what PLAYER_SET_ALL_UNITS_TO_FLEE does:
where a unit runs, whether it is gone on arrival and how (removed or killed), what an object without the module
does, whether a later order stops the run.

On the Niagara map the player's construction yard and one Allied peacekeeper (BaseInfantry: RunOffMapBehavior,
RequiresSpecificTrigger, RunOffMapWaypointName "RunOffMap") on the west field, facing +x. In the 'Test Go' frame
(one second in) each variant fires PLAYER_SET_ALL_UNITS_TO_FLEE on the player:

  a  near    a waypoint "RunOffMap" 200 east of the man (and a trigger area of half-side 40 around it)
  b  none    no such waypoint (read: the module falls back to 1000 straight ahead along the facing); the area
             1000 east
  c  plant   as a, plus a power plant of the player (a structure: no RunOffMapBehavior); the plant is the target
             of rows 2-3, the man moves to row 4
  d  stop    as a; NAMED_STOP on the man at frame 15

Counters (four lines), every one counted from 'Test Go' on:
  帧数   frames since Go
  逃帧   1 x frames the target is not destroyed + 1000 x frames it carries FLEE_OFF_MAP (status 54 = the read 0x36)
  死法   1 x frames it is destroyed (NAMED_DESTROYED) + 1000 x frames it is dying (NAMED_DYING: killed, not removed)
  第四行  a, b, d: 1 x frames the man is inside the waypoint's area
         c: 1 x frames the man is not destroyed + 1000 x frames he carries FLEE_OFF_MAP

Bench 11-06 (B round 4; one run each, rows every second, the first ~25 frames in):
  a CampRunoffmapA_mcp_1106_035353: 逃帧 64064 (FLEE_OFF_MAP from Go, gone after 64 frames); 死法 +1 a frame from
    65, never dying (removed, not killed); 第四行 15 (in the area from frame 50 to 64).
  b CampRunoffmapB_mcp_1106_035552: no waypoint -> 1000 east (the facing): 逃帧 304304, 第四行 15 (290-304).
    50/s from the order's frame, removed 3 frames after the point: 200 -> 64, 1000 -> 304.
  c CampRunoffmapC_mcp_1106_040133: the plant = frames only (never fleeing, never killed); the man 64064 as a.
  d CampRunoffmapD_mcp_1106_040353: after NAMED_STOP at 15 the man stays to the end, FLEE_OFF_MAP on throughout.
Against the model (RA3-EngineModel runoffmap.py, tests/test_objects_bench.py "runoffmap"): every row the same.
"""
import resources
from maps import niagara
from parts import Mission, Script, Test, square, status

MAN, PLANT = 'AlliedAntiInfantryInfantry', 'AlliedPowerPlant'
SPOT = ('west field', 0.0, 0.0)
RUNS = {'a': 20.0, 'b': 50.0, 'c': 20.0, 'd': 20.0}
FLEE = status('FLEE_OFF_MAP')


def _n(part):
    return f'UNIT - CNV Runoffmap {part}'


def mission():
    m = Mission(name='CampRunoffmap', map=resources.measured(niagara), units=[], facts={})
    m.spawns |= {PLANT}
    m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
    m.put(MAN, *SPOT, angle=0.0, role='man', name=_n('Man'))
    return m


def runoffmap_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    man, run = _n('Man'), RUNS[which]
    x, y = m.site(SPOT[0])[:2]
    far = 1000.0 if which == 'b' else 200.0
    if which != 'b':
        t.waypoints['RunOffMap'] = (x + far, y)
    t.areas['Test RunOff Spot'] = square(x + far, y, 40.0)
    start = [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', 1.0)]
    target = man
    if which == 'c':
        target = _n('Plant')
        start.insert(0, ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', target, PLANT, m.team('p1'), 'Test Plant Spot'))
        t.waypoints['Test Plant Spot'] = (x - 250.0, y + 250.0)
    t.scripts.append(Script('Test - start', [], start))
    go = [('PLAYER_SET_ALL_UNITS_TO_FLEE', p1)]
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test Go')], go + [('SET_FLAG', 'Test Going', 1)]))
    going = ('FLAG', 'Test Going', 1)

    t.counters.append(('CNV_Runoffmap_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [going], [('INCREMENT_COUNTER', 1, 'CNV_Runoffmap_Frames')], once=False))
    if which == 'd':
        t.scripts.append(Script('Test - stop', [going, ('COUNTER', 'CNV_Runoffmap_Frames', 2, 15)],
                                [('NAMED_STOP', man)]))
    rows = {
        2: ('逃帧', [(('NAMED_NOT_DESTROYED', target), 1), (('UNIT_HAS_OBJECT_STATUS', target, FLEE), 1000)]),
        3: ('死法', [(('NAMED_DESTROYED', target), 1), (('NAMED_DYING', target), 1000)]),
        4: ('第四行', [(('NAMED_NOT_DESTROYED', man), 1), (('UNIT_HAS_OBJECT_STATUS', man, FLEE), 1000)]
            if which == 'c' else [(('NAMED_INSIDE_AREA', man, 'Test RunOff Spot'), 1)]),
    }
    for k, (label, conds) in rows.items():
        t.counters.append((f'CNV_Runoffmap_Row{k}', label))
        for j, (cond, step) in enumerate(conds):
            t.scripts.append(Script(f'Test - row {k} {j}', [going, cond],
                                    [('INCREMENT_COUNTER', step, f'CNV_Runoffmap_Row{k}')], once=False))
    t.expect = [('帧数', 0, 'ever>=', 1, run)]
    t.bench = [('bench_watch', dict(every=1.0, sheet=False, lines=len(t.counters), seconds=run))]
    return t


MISSION = {'engine_runoffmap': mission}
CHECKS = {'engine_runoffmap': {w: (lambda m, w=w: runoffmap_test(m, w)) for w in 'abcd'}}
