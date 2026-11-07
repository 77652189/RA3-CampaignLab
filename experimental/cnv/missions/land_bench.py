"""Engine probe mission: which way an amphibious transport takes to a shore point behind a quay (checks/engine_land.py;
the simulator's rule R7, docs/story/sim-vs-bench-a4.md: the A4 bench landed the Ghost King ~12 s after the horn,
the simulator ~29 s -- its transport found the quay too high and went round by the southern slip, 2420 long, where
the straight way is 630).

A4's map (sapporo) as A4's horn uses it: the transport (JapanLightTransportVehicle) made at the sea point (4750,
2900) and sent to the beach site (4120, 2900), on the quay 120 above the water.
"""
from maps import sapporo
from parts import Mission, Script

BOAT = 'JapanLightTransportVehicle'
SEA, SHORE = (4750.0, 2900.0), (4120.0, 2900.0)


def mission():
    m = Mission(name='CampLand', map=sapporo, facts={})
    m.waypoints['CNV Land Sea'], m.marks['sea'] = SEA, 'CNV Land Sea'
    m.waypoints['CNV Land Shore'], m.marks['shore'] = SHORE, 'CNV Land Shore'
    # the game's start camera is off the map's view (K5): cut it to the quay, held inside the 'whole' border's view
    m.waypoints['CNV Land View'], m.views['CNV Land View'] = (3940.0, 2970.0), (950.0, 540.0, 4050.0, 4460.0)
    m.scripts.append(Script('CNV Land - camera', [], [('MOVE_CAMERA_TO', 'CNV Land View', 0.1, 0.0, 0.0, 0.0)]))
    return m


MISSION = {'engine_land': mission}
