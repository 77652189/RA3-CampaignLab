"""Ground (and one air) locomotion from route request to consumption of its last point."""
import pytest

import engine.objects.locomotion as simlocomotion  # noqa: E402
import engine.testing.small as simsmall
from engine.modules import locomotor  # noqa: E402
import engine.orders.order as simorder  # noqa: E402


def test_open_ground_keeps_exact_goal_and_records_arrival_inside_a_coarse_tick():
    s = simsmall.small_world(model=False)
    b = s.add('walker', 'AlliedAntiInfantryInfantry', 'Player_1', 1200, 2500)
    locomotor.write(s.world, b, speed=60)
    goal = (1240, 2500)
    simlocomotion.go_to(s, b, goal)
    assert b.path == [goal] and b.dest == goal

    # At 60 units/s, the first half-second tick covers 30 units.
    s.move()
    assert (b.x, b.y) == (1230, 2500) and b.path == [goal]
    s.t = 0.5
    s.move()
    assert (b.x, b.y) == goal and b.path == []
    # The last ten units take 1/6 s, so the recorded arrival is at frame 10 (15 Hz).
    assert b.stops_at * 15 == pytest.approx(10)


def test_ground_route_pulls_a_single_bend_around_a_blocked_strip():
    s = simsmall.small_world(model=False)
    # A bar blocks x=1240..1260 through y=2500. The coarse chain clears
    # the near corner at (1240, 2520). From there the line to the goal
    # passes x=1260 above y=2510, so fine sight removes the far bend.
    s.ground.set_blocks([(1250, 2200, 0, 20, 600)])
    assert s.ground.route('ground', (1200, 2500), (1300, 2500)) == [
        (1240, 2520), (1300, 2500),
    ]


def test_script_path_test_reads_the_ground_its_unit_walks():
    # E256: a CRUSHABLE_OBSTACLE shuts the 'foot' cells only; TEAM_CAN_PATH_TO_WAYPOINT asks the same ground the
    # unit's move takes (review 141 P2: it asked 'ground', so infantry read yes to a car it walks round and never on)
    from engine.script.cond_world import team_can_path_to_waypoint
    s = simsmall.small_world(model=False)
    s.add('walker', 'AlliedAntiInfantryInfantry', 'Player_1', 1200, 2500, team='F')
    s.add('tank', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 1200, 2600, team='V')
    s.ground.set_blocks([], foot=[(1300, 2500, 30)])
    assert not team_can_path_to_waypoint(s, '', ['F', '@1300,2500'])
    assert team_can_path_to_waypoint(s, '', ['V', '@1300,2500'])


def test_ground_attack_route_stops_at_the_first_cell_in_range():
    s = simsmall.small_world(model=False)
    b = s.add('walker', 'AlliedAntiInfantryInfantry', 'Player_1', 1200, 2500)
    target = (1320, 2500)
    simlocomotion.go_to(s, b, target, reach=40)

    # The near edge of the range circle is two 20-unit cells west of the
    # target. The physical endpoint differs from the requested destination.
    assert b.path == [(1280, 2500)] and b.dest == target


def test_air_route_ignores_ground_blocks_and_lands_exactly_on_its_last_point():
    s = simsmall.small_world(model=False)
    jet = s.add('jet', 'AlliedAntiGroundAircraft', 'Player_1', 1200, 2500)
    s.ground.set_blocks([(1220, 2500, 10)])
    simorder.order_move(s, simorder.Peers(s), jet, (1220, 2500), False)
    assert jet.path == [(1220, 2500)]  # a blocked ground goal does not refuse an air route
    for _ in range(5):
        s.move(1 / 15, precise=True)
    assert (jet.x, jet.y) == (1220, 2500) and jet.path == []
