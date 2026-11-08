"""Render line probe (docs/research/rendering.md "第 0 步结果"): a big battle in the start camera's view that keeps going,
to measure drawn frames (capture shim log) against logic frames (a script counter) under each renderer setup.

The west field (island map), offsets from 'west field' (x east): the player's Allied army west of the centre, s1's Soviet
army east of it, ROWS x COLS each, GAP apart, the fronts 2 x FRONT apart; each side's reinforcements come in at its
rear waypoint (checks/render_war.py keeps them topped up and attacking the other side's rear).
Published waypoints: west rear, east rear.
"""
from maps import island
from parts import Mission

ALLIED = ('AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryVehicle', 'AlliedAntiStructureVehicle',
          'AlliedAntiInfantryInfantry')
SOVIET = ('SovietAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech3', 'SovietAntiStructureVehicle',
          'SovietAntiInfantryInfantry')
ROWS, COLS, GAP, FRONT = 6, 8, 35.0, 150.0


def mission(name):
    m = Mission(name=name, map=island, facts={})
    m.spawns |= set(ALLIED + SOVIET)
    for side, kinds, sign in (('p1', ALLIED, -1), ('s1', SOVIET, 1)):
        for r in range(ROWS):
            for c in range(COLS):
                m.put(kinds[(r + c) % len(kinds)], 'west field', sign * (FRONT + r * GAP),
                      (c - (COLS - 1) / 2) * GAP, side=side)
    m.waypoint('west rear', 'CNV Rw West', 'west field', -(FRONT + ROWS * GAP + 60), 0.0)
    m.waypoint('east rear', 'CNV Rw East', 'west field', FRONT + ROWS * GAP + 60, 0.0)
    return m


MISSION = {'render_war': lambda: mission('CampRndr')}
