"""The beacon trooper's bench scene: four Guardians at the south of the west field, the trooper 500 north of them.

Published (the cast): beacon, squad (the Guardians); marks: squad, beacon (where each stands).
"""
from maps import island
from parts import Mission
from units import beacon as be

X = 100.0                                       # east of the field's middle: its west edge is shallows
SQUAD_Y, BEACON_Y = -150.0, 350.0


def mission(name='CampBeacon', **unit):
    u = be.beacon(**unit)
    m = Mission(name=name, map=island, units=[u])
    m.put(u.id, 'west field', X, BEACON_Y, name='UNIT - CNV Beacon', role='beacon')
    for dx, dy in ((-40, -40), (40, -40), (-40, 40), (40, 40)):
        m.put('AlliedAntiVehicleVehicleTech1', 'west field', X + dx, SQUAD_Y + dy, role='squad')
    m.waypoint('squad', 'CNV Beacon Squad', 'west field', X, SQUAD_Y)
    m.waypoint('beacon', 'CNV Beacon Stand', 'west field', X, BEACON_Y)
    return m
