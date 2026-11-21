"""An approach stays pending until movement reaches entry range."""
import engine.testing.small as simsmall
from engine.modules import locomotor  # noqa: E402


def test_garrison_approach_enters_with_a_route_still_pending_at_the_building_edge():
    s = simsmall.small_world(model=False)
    house = s.add('house', 'AM_Apartments_01', 'PlyrCivilian', 1400, 2500)
    b = s.add('walker', 'AlliedAntiInfantryInfantry', 'Player_1', 1240, 2500)
    locomotor.write(s.world, b, speed=120)
    b.goal = house                      # sending it (and putting it in, below) drops a goal it had
    assert s.garrison.send(b, house)
    assert s.garrison.going[b.serial] == (b, house) and s.garrison.held(house) == [] and b.goal is None

    route = b.path.copy()
    assert route
    b.path, b.goal = [], None  # the approach was interrupted 160 units from the building
    s.garrison.due()
    assert s.garrison.going[b.serial] == (b, house) and s.garrison.held(house) == []
    assert b.path == route

    # Each half-second tick covers 60. After one move x=1300,
    # still 100 away; after two x=1360, now within the footprint plus 20.
    s.move()
    s.garrison.due()
    assert (b.x, b.y) == (1300, 2500) and s.garrison.held(house) == []
    s.t = 0.5
    s.move()
    assert (b.x, b.y) == (1360, 2500) and b.path
    b.goal = house
    s.garrison.due()
    assert b.serial not in s.garrison.going and s.garrison.held(house) == [b]
    assert 'ENCLOSED' in b.script_status and b.path == [] and b.goal is None
