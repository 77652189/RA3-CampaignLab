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


def test_vehicle_group_keeps_its_spread_round_the_point():
    # bench engine_seqteam:t: the group's middle goes to the point, each its whole offset (not the nearest on it).
    s = simsmall.small_world(model=False)
    template = 'AlliedAntiVehicleVehicleTech1'
    near = s.add('near', template, 'Player_1', 1400, 2500)
    far = s.add('far', template, 'Player_1', 1200, 2400)
    s.order_group([far, near], (1600, 2500), False)
    assert (near.dest, far.dest) == ((1700, 2550), (1500, 2450)) and near.path == [near.dest]
    # bench engine_acts_near: 1600 apart, the offsets are cut (SPREAD radii) and both end near the point.
    a, b = s.add('a', template, 'Player_1', 1000, 3500), s.add('b', template, 'Player_1', 2600, 3500)
    s.order_group([a, b], (1800, 4500), False)
    cut = 15 * a.radius
    assert (a.dest, b.dest) == ((1800 - cut, 4500), (1800 + cut, 4500))


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
