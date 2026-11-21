"""A group command gives each mover its own destination and route (the files: tests/test_sim_column.py)."""
import pytest

import engine.testing.small as simsmall


@pytest.mark.parametrize('spots, goals', [
    # Each man keeps the slot on his own side, each route is the slot alone (no start point).
    ([(1220, 2480), (1220, 2520)], [(1400, 2480), (1400, 2520)]),
    ([(1220, 2480), (1220, 2520), (1200, 2500)], [(1400, 2480), (1400, 2520), (1360, 2500)]),
])
def test_infantry_group_slots_and_routes(spots, goals):
    s = simsmall.small_world(model=False)
    men = [s.add(f'm{i}', 'AlliedAntiInfantryInfantry', 'Player_1', *xy) for i, xy in enumerate(spots)]
    s.order_group(men[::-1], (1400, 2500), False)
    assert [(b.dest, b.path) for b in men] == [(g, [g]) for g in goals]


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


def test_vehicle_keeps_off_a_man_held_up_short_of_his_slot():
    # review 1121ll #1: on probe_block foot3 has no way to his slot and stays put; the tank's goal keeps off him.
    from maps import probe_block
    s = simsmall.small_world(model=False, map=probe_block)
    men = [s.add(f'foot{i}', 'AlliedAntiInfantryInfantry', 'Player_1', *xy) for i, xy in enumerate(
        [(3990, 3495), (4050, 3468), (4050, 3486), (4000, 3511), (3950, 3491), (3995, 3502), (3990, 3489)])]
    tank = s.add('tank', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 3900, 3500)
    s.order_group(men + [tank], (4000, 3500), False)
    assert men[3].path == [] and (men[3].x, men[3].y) == (4000, 3511)
    assert tank.dest == (3960, 3540)
