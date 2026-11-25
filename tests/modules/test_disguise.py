"""SpecialDisguiseUpdate (engine/modules/disguise.py). Read on the bench: checks/engine_spntrans.readings.toml (the
transport's DISGUISED one UnpackTime after the hit), checks/engine_spncancel.readings.toml (a foe of the hit's owner
leaves the disguised one alone)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.testing.small as simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.orders import target  # noqa: E402


def test_the_disguise_shows_after_its_unpack_and_passes_for_the_hits_owner():
    s = simsmall.small_world([('car', 'JapanLightTransportVehicle', 'Player_1', 0.0, 0.0),
                              ('foe', 'SovietAntiInfantryInfantry', 'Soviet_1', 100.0, 0.0)])
    car, foe = s.bodies['car'], s.bodies['foe']
    (d,) = car.find(interfaces.Disguise)
    assert target.takes_by_itself(foe, car, s)
    now = s.world.frame
    d.wear('Soviet_1')
    assert not d.shows('DISGUISED', now + 14) and d.shows('DISGUISED', now + 15)      # UnpackTime 1 s
    s.world.frame = now + 15
    assert not target.takes_by_itself(foe, car, s)          # it passes for one of the foe's own
    d.wear('Player_1')
    s.world.frame = now + 30
    assert target.takes_by_itself(foe, car, s)              # disguised as one of its own owner's: still a foe
