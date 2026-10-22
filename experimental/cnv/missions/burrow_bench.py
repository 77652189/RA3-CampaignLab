"""The burrowing APC's bench scene: two of them side by side on the west field (A west, B east), three conscripts
aboard each, three Hammers between their lanes 175 north, a goal for each 425 north beyond the Hammers. The lanes sit
east of the field's middle: A's goal at its west edge was in the shallows (bench 2026-10-22).

Published (the cast): burrower A, burrower B, hammer, passenger (aboard, not placed); marks: goal A, goal B.
"""
from maps import island
from parts import Mission, Role
from units import burrower as bu

LANE = 150.0                                    # each lane this far from the scene's middle
MIDDLE = 150.0                                  # the scene's middle, east of the field's
PASSENGER = 'SovietAntiInfantryInfantry'        # the conscript


def mission(name='CampBurrow', **unit):
    u = bu.burrower(payload=(PASSENGER, 3), **unit)
    m = Mission(name=name, map=island, units=[u])
    m.cast['passenger'] = Role(PASSENGER)
    for tag, dx in (('A', MIDDLE - LANE), ('B', MIDDLE + LANE)):
        m.put(u.id, 'west field', dx, -150, name=f'UNIT - CNV Burrower {tag}', role=f'burrower {tag}')
        m.waypoint(f'goal {tag}', f'CNV Burrow Goal {tag}', 'west field', dx, 425)
    for dx in (-60, 0, 60):
        m.put('SovietAntiVehicleVehicleTech1', 'west field', MIDDLE + dx, 175, side='s1', role='hammer')
    return m
