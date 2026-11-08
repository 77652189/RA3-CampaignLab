"""Engine measurement: what ground a scene's picture shows (letterbox on) -- the width of the band at its top, middle and
bottom row, and where the band's middle sits against the camera centre (K8; model.LETTERBOX_BAND).

On A4's map (maps/sapporo.py) a grid of guardians stands parked far west. The scene opens (CAMERA_LETTERBOX_BEGIN), the
camera moves to a flat point C (0.1 s); a few seconds later every guardian is teleported to its grid point at once. Two
archived frames, before and after, differ only by the guardians: their difference (calib.blobs) gives where each is
drawn; matched to the grid (rows top to bottom = north to south) they fit a homography of ground -> screen (calib.fit's
way) for this camera. tools: python -I experimental/testbench/letterbox_fit.py <run dir> <frame before> <frame after>.
"""
from maps import sapporo
from parts import Mission, Script, Test
from checks.probe_view import open_in_view

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
PARK = (250.0, 2500.0)                      # 'convoy start'
C = (2830.0, 2225.0)                        # camera centre: A4's V3, the ground flat for 300 around, the avenue
COLS = [-450.0, -300.0, -150.0, 0.0, 150.0, 300.0, 450.0]       # grid offsets from C (x)
ROWS = [-250.0, -125.0, 0.0, 125.0, 250.0]                       # (y)
GRID = [(C[0] + dx, C[1] + dy) for dy in ROWS for dx in COLS
        if (dx, dy) != (450.0, 125.0)]      # (that spot stands on a tree: test_maps, nothing a build places on scenery)
SCENE_AT, SHOW_AT, RUN = 2.0, 6.0, 9.0


def mission():
    m = Mission(name='CampLbx', map=sapporo, facts={})
    for k in range(len(GRID)):
        m.put(GUARDIAN, 'convoy start', 0, 0, name=f'UNIT - CNV Letterbox G{k}', role=f'g{k}')
    return open_in_view(m, 'Letterbox')


def grid(m):
    t = Test()
    t.waypoints['Test Letterbox C'] = C
    t.counters.append(('Test Step', '第几步'))
    for k, p in enumerate(GRID):
        t.waypoints[f'Test Letterbox P{k}'] = p
    t.scripts += [
        Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_COUNTER', 'Test Step', 0),
                                    ('SET_MILLISECOND_TIMER', 'Test - scene', SCENE_AT),
                                    ('SET_MILLISECOND_TIMER', 'Test - show', SHOW_AT)]),
        Script('Test - scene', [('TIMER_EXPIRED', 'Test - scene')],
               [('CAMERA_LETTERBOX_BEGIN',), ('MOVE_CAMERA_TO', 'Test Letterbox C', 0.1, 0.0, 0.0, 0.0)]),
        Script('Test - show', [('TIMER_EXPIRED', 'Test - show')],
               [('UNIT_TELEPORT_TO_WAYPOINT', f'UNIT - CNV Letterbox G{k}', f'Test Letterbox P{k}') for k in range(len(GRID))] +
               [('SET_COUNTER', 'Test Step', 1)])]
    t.expect.append(('第几步', RUN - 1, 'ever==', 1))
    t.bench = [('bench_watch', dict(seconds=RUN, every=0.5, sheet=False, lines=1))]
    return t


MISSION = {'engine_letterbox': mission}
CHECKS = {'engine_letterbox': {'g': grid}}
