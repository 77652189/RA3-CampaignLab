"""Retail-campaign conditions, batch 3 (round 237): CAMERA_ENTERED_AREA (60 uses, j02's statues with NAMED_DISCOVERED),
ENEMY_SIGHTED (59: a02 / j06 / s08 / ep01, 'Enemy' 58 times, 'Friend' once) and TYPE_SELECTED (38: a06 / j01 hint
scripts, the player's own click, the template written in lower case). Mission on maps/probe_border.py (level
ground), every place absolute; every unit NO_ATTACK. Clear of probe_range's lanes (y 400, 1200-1900, 3300-3750) and
the start (1250, 2500). Trigger areas do not overlap (round 236: a unit in too many at once freezes them).

  all  sight: the player's 'watch' (Guardian, sight 200) at (1000, 4500), its 'mate' 150 north, 'lone' alone at
       (2200, 4100); Soviet_4's 'near' 150 east of watch; Soviet_5's 'far' 600 east, sent at 5 s to 150 west of watch.
       看见 (every frame) = 1 ENEMY_SIGHTED(watch, Enemy, Soviet_4) 2 (watch, Enemy, Soviet_5) 4 (watch, Friend,
         Player_1) 8 (lone, Friend, Player_1) 16 (watch, Enemy, Player_1) 32 (near, Enemy, Player_1)
         64 (watch, Neutral, Soviet_4)
       camera: P1 (3500, 2500), P2 (2000, 2500). MOVE_CAMERA_TO P1 at 1 s (0.1 s), P2 at 6 s, P1 again at 9 s over
       4 s (passing M), P2 at 16 s. Areas: A (P1, half-side 100); strips round it, x 3300-3700: N1 y 2610-2900,
       N2 2900-3250, S1 2100-2390, S2 1500-2100, S3 600-1500; E x 3610-4100, y 2400-2600; M (2750, 2500) half-side 100.
       镜头 (every frame) = 1 CAMERA_ENTERED_AREA(A) 2 (N1) 4 (N2) 8 (S1) 16 (S2) 32 (S3) 64 (E) 128 (M)
       帧 (only added) = 1 a frame CAMERA_ENTERED_AREA(A) holds, 10000 a frame TYPE_SELECTED(Guardian, either case)
         holds (an edge or a state)
       selection: the player's 'pick' (Guardian, (3000, 4300)) and 'other' (Peacekeeper, (3300, 4300));
       SELECT_OBJECT(Player_1, pick) at 3 s. After 20 s by hand (bench_camera, bench_click): the player's own
       camera to P1, clicks on pick, other, the bare ground.
       选中 (every frame) = 1 NAMED_SELECTED(pick) 2 TYPE_SELECTED(Guardian) 4 TYPE_SELECTED(guardian, lower case)
         8 NAMED_SELECTED(other) 16 TYPE_SELECTED(Peacekeeper)
  [prediction from the data (the simulator before this round: the camera a point, set at once by MOVE_CAMERA_TO;
   ENEMY_SIGHTED any enemy of the viewer, the player argument unread, other relations a gap; TYPE_SELECTED never):
   看见 1 + 4 + 8 + 32 = 45 to ~s7 (the third argument the sighted object's owner: 2 only once far is within 200 of
   watch; a viewer counts itself as BY_TEAM's member does: 8, INFERRED), 47 after. 镜头 1 s2-s6, 0, 128 about
   s10-s11 (the camera moves, it is not set at once), 1 s13-s16, 0; the strips never (the camera's point is where it
   looks, not the eye or the view). 帧 grows while 1 holds (a state). 选中 1 from s3 (A222), TYPE_SELECTED only
   after a player's click: 1 + 2 + 4 while pick is clicked, 8 + 16 for other, 0 on the bare ground]
  BENCH 11-14 (round 237; build.py's own run CampSeeAll_mcp_1114_234139 PASS, then by hand _234250): 看见 / 镜头 /
    帧 / 选中 s1 45 129 27 0 | s2-s8 45 129 41..131 1 | s9-s21 47 129 146..328 1. By hand: the player's camera
    (minimap) to N2 133, to (4300, 4300) 133 still; left clicks on pick 1, on other 8, on pick 1, a box on pick 1; 帧
    never +10000. So: ENEMY_SIGHTED as predicted (the owner, Friend with the viewer itself); CAMERA_ENTERED_AREA
    latches for good once the camera's point has been in the area, the way there too (M from the 0.1 s move at 1 s),
    the player's camera as well, never the strips round the point; TYPE_SELECTED never (exact or lower case; a
    double click not tried); NAMED_SELECTED follows the player's clicks. Simulator: sim.Sim.cond ENEMY_SIGHTED /
    CAMERA_ENTERED_AREA, MOVE_CAMERA_TO (tests/test_simbench.py test_eyes_all_as_the_bench).
"""
from maps import probe_border
from parts import Mission, Script, Test, square, status
import checks.engine_scripts8 as s8

TANK, PK = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
WATCH, MATE, LONE = (1000.0, 4500.0), (1000.0, 4650.0), (2200.0, 4100.0)
NEAR, FAR, FAR_TO = (1150.0, 4500.0), (1600.0, 4500.0), (850.0, 4500.0)
PICK, OTHER = (3000.0, 4300.0), (3300.0, 4300.0)
P1, P2, M = (3500.0, 2500.0), (2000.0, 2500.0), (2750.0, 2500.0)
STRIPS = {'N1': (3300.0, 2610.0, 3700.0, 2900.0), 'N2': (3300.0, 2900.0, 3700.0, 3250.0),
          'S1': (3300.0, 2100.0, 3700.0, 2390.0), 'S2': (3300.0, 1500.0, 3700.0, 2100.0),
          'S3': (3300.0, 600.0, 3700.0, 1500.0), 'E': (3610.0, 2400.0, 4100.0, 2600.0)}
RUN = 20.0                                      # the scripted part; the bench run goes on by hand


def _n(part):
    return f'UNIT - CNV Eyes {part.title()}'


def _put(m, template, x, y, **kw):
    m.put(template, 'stop row', x - O[0], y - O[1], **kw)


def _mark(m, part, x, y):
    m.waypoint(part, f'Test Eyes {part.title()}', 'stop row', x - O[0], y - O[1])


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def mission():
    m = Mission(name='CampEyes', map=probe_border, units=[], facts={})
    m.spawns |= {TANK, PK}
    for role, side, template, (x, y) in (('watch', 'p1', TANK, WATCH), ('mate', 'p1', TANK, MATE),
                                         ('lone', 'p1', TANK, LONE), ('near', 's4', TANK, NEAR),
                                         ('far', 's5', TANK, FAR), ('pick', 'p1', TANK, PICK),
                                         ('other', 'p1', PK, OTHER)):
        _put(m, template, x, y, side=side, angle=0.0 if side == 'p1' else 3.1416, name=_n(role), role=role)
    for part, (x, y) in (('far to', FAR_TO), ('p1', P1), ('p2', P2)):
        _mark(m, part, x, y)
    return m


def all_(m):
    t = Test()
    p1, s4, s5 = m.player(), m.player('s4'), m.player('s5')
    n = {r: m.role(r).name for r in ('watch', 'mate', 'lone', 'near', 'far', 'pick', 'other')}
    t.areas['Test Eyes A'] = square(*P1, 100.0)
    t.areas['Test Eyes M'] = square(*M, 100.0)
    for k, r in STRIPS.items():
        t.areas[f'Test Eyes {k}'] = _rect(*r)
    t.scripts.append(Script('Test - Eyes hold', [], [
        ('UNIT_CHANGE_OBJECT_STATUS', name, status('NO_ATTACK'), 1) for name in n.values()]))
    p1w, p2w = m.mark('p1'), m.mark('p2')
    s8.at(t, 'cam1', 1.0, [('MOVE_CAMERA_TO', p1w, 0.1, 0.0, 0.0, 0.0)])
    s8.at(t, 'sel', 3.0, [('SELECT_OBJECT', p1, n['pick'])])
    s8.at(t, 'far', 5.0, [('MOVE_NAMED_UNIT_TO', n['far'], m.mark('far to'))])
    s8.at(t, 'cam2', 6.0, [('MOVE_CAMERA_TO', p2w, 0.1, 0.0, 0.0, 0.0)])
    s8.at(t, 'cam3', 9.0, [('MOVE_CAMERA_TO', p1w, 4.0, 0.0, 0.0, 0.0)])
    s8.at(t, 'cam4', 16.0, [('MOVE_CAMERA_TO', p2w, 0.1, 0.0, 0.0, 0.0)])
    s8.total(t, 'CNV_Eyes_Sight', '看见', [
        (1, ('ENEMY_SIGHTED', n['watch'], 'Enemy', s4)), (2, ('ENEMY_SIGHTED', n['watch'], 'Enemy', s5)),
        (4, ('ENEMY_SIGHTED', n['watch'], 'Friend', p1)), (8, ('ENEMY_SIGHTED', n['lone'], 'Friend', p1)),
        (16, ('ENEMY_SIGHTED', n['watch'], 'Enemy', p1)), (32, ('ENEMY_SIGHTED', n['near'], 'Enemy', p1)),
        (64, ('ENEMY_SIGHTED', n['watch'], 'Neutral', s4))])
    s8.total(t, 'CNV_Eyes_Cam', '镜头', [(w, ('CAMERA_ENTERED_AREA', f'Test Eyes {k}')) for w, k in (
        (1, 'A'), (2, 'N1'), (4, 'N2'), (8, 'S1'), (16, 'S2'), (32, 'S3'), (64, 'E'), (128, 'M'))])
    t.counters.append(('CNV_Eyes_Frames', '帧'))
    t.scripts += [Script('Test - CNV_Eyes_Frames A', [('CAMERA_ENTERED_AREA', 'Test Eyes A')],
                         [('INCREMENT_COUNTER', 1, 'CNV_Eyes_Frames')], once=False),
                  Script('Test - CNV_Eyes_Frames T', [('TYPE_SELECTED', TANK)],
                         [('INCREMENT_COUNTER', 10000, 'CNV_Eyes_Frames')], once=False),
                  Script('Test - CNV_Eyes_Frames t', [('TYPE_SELECTED', TANK.lower())],
                         [('INCREMENT_COUNTER', 10000, 'CNV_Eyes_Frames')], once=False)]
    s8.total(t, 'CNV_Eyes_Sel', '选中', [
        (1, ('NAMED_SELECTED', n['pick'])), (2, ('TYPE_SELECTED', TANK)), (4, ('TYPE_SELECTED', TANK.lower())),
        (8, ('NAMED_SELECTED', n['other'])), (16, ('TYPE_SELECTED', PK))])
    t.expect = [('看见', 0, 'ever>=', 1, RUN)]
    s8.watch(t, RUN)
    return t


MISSION = {'engine_eyes': mission}
CHECKS = {'engine_eyes': {'all': all_}}
