"""StoreObjectsSpecialPower + TeleportStoredObjectsUpdate (E227, checks/engine_teleport.readings.toml): retail's
Chronosphere (no delays, INSTANT_DEATH_TELEPORTER_ONLY, insta-kill INFANTRY) -- the stored infantry dies, the stored
tank moves, the formation kept, and dies landing on a parked tank (the frames: the readings)."""
import pytest

import engine.script.act_ability as act
import engine.testing.small as simsmall
from engine.kernel import interfaces
from engine.modules import teleport

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


@pytest.mark.parametrize('early', [False, True])
def test_a_second_cast_starts_the_delays_over(early):
    """review 1125 T: given delays (initial 25 frames, then 30), a spawn at B and 20 frames on at C lands at C as late
    as a cast at C alone (INFERRED: the game's recast untested); it used to keep the first cast's wake, 15 frames early."""
    s = simsmall.small_world([('chrono', 'AlliedSuperWeapon', 'Player_1', 2400.0, 2400.0),
                              ('tank', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 1420.0, 1400.0)], model=False)
    chrono, tank = s.bodies['chrono'], s.bodies['tank']
    m = chrono.find(interfaces.Teleport)[0]
    d = m.data
    m.data = teleport.TeleportData(d.power, 25, 30, d.telefrag, d.at_store, d.kill, d.collide, d.fade)
    for power, x, after in [(SELECT, 1400.0, 0)] + [(SPAWN, 1900.0, 0)] * early + [(SPAWN, 2200.0, 20)]:
        s.advance(after)
        assert act._teleport(s, chrono, power, (x, 1400.0))
    cast = s.frame_now()
    while tank.x == 1420.0 and s.frame_now() - cast < 80:
        s.advance(1)
    assert (s.frame_now() - cast, tank.x) == (60, 2220.0)
