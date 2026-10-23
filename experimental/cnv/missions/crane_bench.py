"""The paper crane's bench scene: the flier on the west field, an enemy Guardian on the east field (1800 away, in the
shroud), a point 700 short of it to stop at -- inside the crane's 900, outside a retail flier's 500.

retail=True: retail's Twinblade flies instead (the control). Published (the cast): scout, target; marks stop.
"""
from maps import island
from parts import Mission
from units import crane as cr

SHORT = 700.0


def mission(name='CampCrane', retail=False, **unit):
    u = cr.crane(**unit)
    m = Mission(name=name, map=island, units=[] if retail else [u])
    m.put('SovietAntiGroundAircraft' if retail else u.id, 'west field', 100, 0, name='UNIT - CNV Scout', role='scout')
    m.put('AlliedAntiVehicleVehicleTech1', 'east field', 0, 0, side='s1', name='UNIT - CNV Target', role='target')
    m.waypoint('stop', 'CNV Crane Stop', 'east field', -SHORT, 0)
    return m
