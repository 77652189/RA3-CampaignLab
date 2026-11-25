"""StoreObjectsSpecialPower + TeleportStoredObjectsUpdate (E227, checks/engine_teleport.readings.toml): retail's
Chronosphere (no delays, INSTANT_DEATH_TELEPORTER_ONLY, insta-kill INFANTRY) -- the stored infantry dies, the stored
tank moves, the formation kept, and dies landing on a parked tank (the frames: the readings)."""
import pytest

import engine.script.act_ability as act
import engine.testing.small as simsmall

SELECT, SPAWN = 'SpecialPowerChronosphereObjectSelect', 'SpecialPowerChronosphereObjectSpawn'


@pytest.mark.parametrize('parked', [False, True])
def test_the_chronosphere_carries_the_stored_tank_and_kills_the_infantry(parked):
    things = [('chrono', 'AlliedSuperWeapon', 'Player_1', 2400.0, 2400.0),
              ('tank', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 1420.0, 1400.0),
              ('inf', 'AlliedAntiInfantryInfantry', 'Player_1', 1360.0, 1400.0),
              ('far', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 1400.0, 1550.0)]
    s = simsmall.small_world(things + [('parked', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 1820.0, 1400.0)] * parked,
                             model=False)
    b = s.bodies
    assert act._teleport(s, b['chrono'], SELECT, (1400.0, 1400.0))
    assert act._teleport(s, b['chrono'], SPAWN, (1800.0, 1400.0))
    s.advance(3)
    assert not b['inf'].alive
    assert (b['tank'].x, b['tank'].y) == (1820.0, 1400.0) and b['tank'].alive != parked
    assert (b['far'].x, b['far'].y) == (1400.0, 1550.0) and b['far'].alive     # outside Radius 100: not stored
    assert not parked or b['parked'].alive
