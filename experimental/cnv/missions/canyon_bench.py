"""A2's map (maps/blackcanyon.py) bare, for the bench questions its draft left (checks/blackcanyon.py)."""
from maps import blackcanyon
from parts import Mission
from units import unsellable

SPAWNS = {'SovietAntiNavyShipTech1', 'SovietAntiAirShip', 'SovietAntiVehicleVehicleTech1',
          'SovietAntiVehicleVehicleTech2'}                    # what the checks count


def mission(name='CampCanyon'):
    # the dam sections' plant the player cannot sell (checks/blackcanyon.py lock)
    return Mission(name=name, map=blackcanyon, spawns=SPAWNS, units=[unsellable.copy('AlliedPowerPlant')])


MISSION = {'canyon': mission}
