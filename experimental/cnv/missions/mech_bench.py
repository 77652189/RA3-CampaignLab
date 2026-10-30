"""Engine-mechanic bench scenes for the level line's four questions (handoff 0b, docs/design/flow/mechanics.md).

thin_ice: three runners on the west field head north through a square of "thin ice" (a trigger area, 300 wide, the
middle of the lane): two heavy vehicles (a Guardian and a Hammer) and one light one (a Sickle).
There is no ice in the engine to sink them, so the script does it: a heavy one standing in the area is killed, a
light one is left alone (S1's fallback for "冰面承重").

shown: two things shown on the same unit at once, to be looked at: an info box (NAMED_SHOW_INFOBOX) and a radar event
(OBJECT_CREATE_RADAR_EVENT, the minimap blip), the second one on a unit that stands far from the camera.

Published (the cast): heavy A, heavy B, light; marks ice (its middle), goal.
"""
from maps import island
from parts import Mission

X = 100.0
HEAVY_A = 'AlliedAntiVehicleVehicleTech1'       # the Guardian
HEAVY_B = 'SovietAntiVehicleVehicleTech1'       # the Hammer (all three ours: an enemy one would shoot the others)
LIGHT = 'SovietAntiInfantryVehicle'             # the Sickle


def thin_ice(name='CampThin'):
    m = Mission(name=name, map=island)
    m.put(HEAVY_A, 'west field', X - 100, -350, name='UNIT - CNV Heavy A', role='heavy A', angle=1.5708)
    m.put(HEAVY_B, 'west field', X, -350, name='UNIT - CNV Heavy B', role='heavy B', angle=1.5708)
    m.put(LIGHT, 'west field', X + 100, -350, name='UNIT - CNV Light', role='light', angle=1.5708)
    m.waypoint('ice', 'CNV Ice Middle', 'west field', X, 0)
    m.waypoint('goal', 'CNV Ice Goal', 'west field', X, 400)
    return m


def shown(name='CampShown'):
    m = Mission(name=name, map=island)
    m.put(LIGHT, 'west field', X, 0, name='UNIT - CNV Near', role='near')
    m.put(LIGHT, 'east field', 0, 0, name='UNIT - CNV Far', role='far')
    return m
