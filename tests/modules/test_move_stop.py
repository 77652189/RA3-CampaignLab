"""Stopping early and exhausting a fallback route retain the command's intent."""
import simsmall
from engine.ports.command import Command


def test_stop_cancels_the_remaining_way_without_resetting_the_plain_move():
    s = simsmall.small_world(model=False)
    b = s.add('walker', 'AlliedAntiInfantryInfantry', 'Player_1', 1200, 2500)
    b.speed = 60
    s.order_move(b, (1320, 2500), False)
    s.move()
    assert (b.x, b.y) == (1230, 2500) and b.path
    s.order_stop(b)
    s.move()
    # STOP clears the path, while mode and the original move_to stay put.
    assert (b.x, b.y) == (1230, 2500) and b.path == []
    assert b.mode == 'move' and b.move_to == (1320, 2500)
    assert s.held_up(b) and not b.rolling


def test_stop_cancels_a_pending_run_off_map():
    s = simsmall.small_world(model=False)
    runner = s.add('runner', 'AlliedAntiInfantryInfantry', 'Player_1', 1200, 2500)
    assert s.commands.do(Command('flee', 'script', units=('runner',),
                                 args=(('objects', True),))) == (True, '')
    assert runner.flee is not None
    start = (runner.x, runner.y)
    s.order_stop(runner)
    assert runner.flee is None
    s.flee_due(s.frame_now() + 1)
    assert (runner.x, runner.y) == start


def test_give_up_at_nearest_reachable_cell_keeps_the_requested_destination():
    s = simsmall.small_world(model=False)
    b = s.add('walker', 'AlliedAntiInfantryInfantry', 'Player_1', 1200, 2500)
    b.speed = 60
    s.ground.set_blocks([(1260, 2500, 0, 20, 10000)])
    goal = (1320, 2500)
    assert s.ground.route('ground', (1200, 2500), goal) is None
    s.order_move(b, goal, False)
    # The bar shuts the x=1260 column; x=1240 is the nearest open column
    # on the starting side, and y=2500 minimizes distance within it.
    assert b.path == [(1240, 2500)] and b.dest == goal
    s.move()
    s.t = 0.5
    s.move()
    assert (b.x, b.y) == (1240, 2500) and b.path == [] and s.held_up(b)
