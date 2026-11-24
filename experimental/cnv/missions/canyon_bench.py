"""A2's map (maps/blackcanyon.py) bare, for the bench questions its draft left (checks/blackcanyon.py)."""
from maps import blackcanyon
from parts import Mission

SPAWNS = {'SovietAntiNavyShipTech1', 'SovietAntiAirShip', 'SovietAntiVehicleVehicleTech1',
          'SovietAntiVehicleVehicleTech2'}                    # what the checks count


def mission(name='CampCanyon'):
    return Mission(name=name, map=blackcanyon, spawns=SPAWNS)


MISSION = {'canyon': mission}
