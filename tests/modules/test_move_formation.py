"""A group command gives each mover its own destination and route."""
import simsmall


def test_three_infantry_fill_two_files_and_center_the_back_row():
    s = simsmall.small_world(model=False)
    template = 'AlliedAntiInfantryInfantry'
    left = s.add('left', template, 'Player_1', 1220, 2480)
    right = s.add('right', template, 'Player_1', 1220, 2520)
    rear = s.add('rear', template, 'Player_1', 1200, 2500)
    s.order_group([rear, right, left], (1400, 2500), False)

    # Eastbound, ceil(sqrt(3)) = 2 files: the front pair has 40 between
    # its slots and the remaining man is centered 40 behind the point.
    for b, goal in [(left, (1400, 2480)), (right, (1400, 2520)), (rear, (1360, 2500))]:
        assert b.dest == goal and b.path == [goal]


def test_vehicle_group_uses_the_nearest_as_anchor_and_caps_the_offset():
    s = simsmall.small_world(model=False)
    template = 'AlliedAntiVehicleVehicleTech1'
    near = s.add('near', template, 'Player_1', 1400, 2500)
    far = s.add('far', template, 'Player_1', 1200, 2500)
    s.order_group([far, near], (1600, 2500), False)

    # The anchor keeps the click. The follower's 200-unit offset is capped
    # at six of its own radii, which still leaves its goal free.
    assert near.dest == (1600, 2500) and near.path == [near.dest]
    assert 6 * far.radius < 200
    assert far.dest == (1600 - 6 * far.radius, 2500) and far.path == [far.dest]
