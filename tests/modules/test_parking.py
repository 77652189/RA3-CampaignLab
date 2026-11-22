"""ParkingPlaceBehavior (engine/modules/parking.py): what the bench's counters cannot see. Read on the bench:
checks/engine_parking.readings.toml (4 of 5 Apollos at the retail airfield, none without the module)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.testing.small as simsmall  # noqa: E402

APOLLO = 'AlliedFighterAircraft'


def test_queued_planes_hold_their_spots_and_a_dead_one_gives_its_back():
    s = simsmall.small_world([('field', 'AlliedAirfield', 'Player_1', 0.0, 0.0),
                              ('other', 'AlliedAirfield', 'Player_1', 600.0, 0.0)])
    f = s.bodies['field']
    assert all(s.order_build('Player_1', APOLLO, factory=f) for _ in range(4))
    assert not s.order_build('Player_1', APOLLO, factory=f)            # 4 queued: no fifth
    s.production.put(f.serial, [])
    for k in range(3):
        s.add(f'made {k}', APOLLO, 'Player_1', 0.0, 300.0, by=f.name)
    s.add('elsewhere', APOLLO, 'Player_1', 600.0, 300.0, by='other')   # another field's: not this one's spot
    assert s.order_build('Player_1', APOLLO, factory=f)
    assert not s.order_build('Player_1', APOLLO, factory=f)
    s.bodies['made 0'].alive = False
    assert s.order_build('Player_1', APOLLO, factory=f)
