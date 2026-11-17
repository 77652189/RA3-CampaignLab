"""Engine unit test: where a ground point is drawn once the mission's MOVE_CAMERA_TO stands the camera on a point, when
the ground around is not flat (engine line round 8: at A4's back lane V1 the engineer was drawn 26 px below the
screen point (640, 350) the bench assumed, a terrace edge 40-60 units south of him; V2 and V3, on flat ground, were not).

On A4's map (maps/sapporo.py) one guardian is parked far west; for each probe the camera moves to a point C (0.1 s),
the guardian is parked again, and 2 s later he is teleported to a point U. Two archived frames, before and after
the teleport, differ only by him: their difference (calib.blobs) gives where he is drawn. Probes with U = C ask what
height the camera looks at (only the ground under C, or the ground around it, and how far around); probes with one
C and several U at different heights ask how many pixels a unit of height moves a point on screen. '第几步' counts
the probes so the frames line up (the archive's mission seconds run ~2 s behind these timers: step k+1 shows at
about FIRST + k * PERIOD).

Measured (run CampCameraWhere_mcp_1104_150834): the camera looks up to 43 of our units above the ground beside a
terrace (V1), not lower where the ground around is lower; a unit of height moves a point 0.48 world units north on
screen (~52 deg down). Fitted into calib.Ground (HEIGHT_Y, PIVOT_R), which the bench's world clicks now use.
"""
from maps import sapporo
from parts import Mission, Script, Test
from checks.probe_view import open_in_view

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
PARK = (250.0, 2500.0)                     # 'convoy start': ~950 west of the nearest probe, off every probe's screen
FIRST, PERIOD, SHOW = 3.0, 5.0, 2.0        # probe k: camera at FIRST + k * PERIOD, the guardian SHOW seconds later
# (camera point C, unit point U); heights in our units (ours = stored / 16): the lane at 340, the terraces at 455
PROBES = [
    ((2830.0, 2225.0), (2830.0, 2225.0)),  # V3: flat for 300 around (the control: drawn at (640, 350) by the engineer)
    ((2830.0, 2225.0), (2830.0, 2325.0)),  # same camera, flat: the bench's ground mapping alone
    ((1200.0, 2400.0), (1200.0, 2400.0)),  # V1 (the engineer: (640, 376))
    ((1200.0, 2400.0), (1200.0, 2480.0)),  # same camera, the lane (340)
    ((1200.0, 2400.0), (1200.0, 2250.0)),  # same camera, the south terrace (455): height against pixels
    ((1200.0, 2400.0), (1080.0, 2200.0)),  # same camera, the south terrace further off
    ((1200.0, 2450.0), (1200.0, 2450.0)),  # U = C along x 1200, the cliff edge 2340-2380 south, a ramp 2550-2880 north
    ((1200.0, 2500.0), (1200.0, 2500.0)),
    ((1200.0, 2540.0), (1200.0, 2540.0)),
    ((1200.0, 2700.0), (1200.0, 2700.0)),  # the middle of a straight ramp: the mean around = the ground, the max is not
    ((1200.0, 2250.0), (1200.0, 2250.0)),  # the terrace 90 above the edge: the ground around is lower
    ((1200.0, 2150.0), (1200.0, 2150.0)),
    ((2015.0, 2635.0), (2015.0, 2635.0)),  # V2: flat for 100 around (the engineer: (640, 350))
]
RUN = FIRST + len(PROBES) * PERIOD + 2.0


def mission():
    m = Mission(name='CampCamera', map=sapporo, facts={})
    m.put(GUARDIAN, 'convoy start', 0, 0, name='UNIT - CNV Camera Guardian', role='guardian')
    return open_in_view(m, 'Camera')    # K5: the map's start (450, 2500) is too near the west edge


def where(m):
    t = Test()
    name = m.role('guardian').name
    t.waypoints['Test Camera Park'] = PARK
    t.counters.append(('Test Step', '第几步'))
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_COUNTER', 'Test Step', 0)] +
                            [('SET_MILLISECOND_TIMER', f'Test - camera {k}', FIRST + k * PERIOD) for k in range(len(PROBES))]))
    for k, (c, u) in enumerate(PROBES):
        t.waypoints[f'Test Camera C{k}'] = c
        t.waypoints[f'Test Camera U{k}'] = u
        t.scripts += [Script(f'Test - camera {k}', [('TIMER_EXPIRED', f'Test - camera {k}')],
                             [('UNIT_TELEPORT_TO_WAYPOINT', name, 'Test Camera Park'),
                              ('MOVE_CAMERA_TO', f'Test Camera C{k}', 0.1, 0.0, 0.0, 0.0),
                              ('SET_MILLISECOND_TIMER', f'Test - show {k}', SHOW)]),
                      Script(f'Test - show {k}', [('TIMER_EXPIRED', f'Test - show {k}')],
                             [('UNIT_TELEPORT_TO_WAYPOINT', name, f'Test Camera U{k}'), ('SET_COUNTER', 'Test Step', k + 1)])]
    t.expect.append(('第几步', RUN - 1, 'ever==', len(PROBES)))
    t.bench = [('bench_watch', dict(seconds=RUN, every=0.5, sheet=False, lines=1))]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_camera': mission}
CHECKS = {'engine_camera': {'where': where}}
