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


def test_the_liberty_jumps_after_its_unpack_and_its_deck_follows_a_frame_later():
    """TeleportSpecialAbilityUpdate (A427, checks/engine_libjump.readings.toml): UnpackTime 0.5 s rounds to 8 frames;
    the deck store (its own filter, Radius 150) takes the Guardian under it, not the one 200 off."""
    import parts
    import sim
    from maps import island
    from units import liberty
    s = sim.Sim(parts.Mission(name='T', map=island, scripts=[], units=[liberty.liberty('CNV_LibT', tag='T', model=None)]),
                model=False)
    for name in list(s.bodies):
        s.world.drop(s.bodies.pop(name))
    for name, template, x in (('lib', 'CNV_LibT', 1400.0), ('g', 'AlliedAntiVehicleVehicleTech1', 1460.0),
                              ('far', 'AlliedAntiVehicleVehicleTech1', 1200.0)):
        s.add(name, template, 'Player_1', x, 1400.0)
    b = s.bodies
    jump = next(m for m in b['lib'].find(interfaces.Teleport) if isinstance(m, teleport.TeleportAbility))
    cast = s.world.frame
    assert act._teleport(s, b['lib'], 'SpecialPower_CNV_ChronoDeck_T', (1400.0, 1800.0))
    assert jump.due - cast == 8 + teleport.LAG and b['lib'].y == 1400.0
    s.advance(20)
    assert (b['lib'].y, b['g'].x, b['g'].y, b['far'].y) == (1800.0, 1460.0, 1800.0, 1400.0)
