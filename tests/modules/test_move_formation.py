"""A group command gives each mover its own destination and route (the files: tests/test_sim_column.py)."""
import engine.testing.small as simsmall


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
