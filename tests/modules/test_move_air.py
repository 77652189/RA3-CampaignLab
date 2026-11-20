"""Air routing and the frame-by-frame startup of the measured jet."""
import pytest

import simsmall


def test_first_eastbound_vindicator_move_uses_the_air_route_and_frame_budget():
    s = simsmall.small_world(model=False)
    jet = s.add('jet', 'AlliedAntiGroundAircraft', 'Player_1', 1200, 2500)
    jet.angle = 0
    s.ground.set_blocks([(1220, 2500, 10)])
    assert not s.ground.open('ground', 1220, 2500)
    s.order_move(jet, (1220, 2500), False)
    assert jet.path == [(1220, 2500)]
    assert jet.frame_move and s.frame_movers['jet'] is jet
    s.move()  # A coarse tick must leave precise movers alone.
    assert jet.x == 1200

    # Measured first step 2.7, then (180/15)/15 = 0.8 more per frame.
    for distance in (2.7, 6.2, 10.5, 15.6):
        s.move(1 / 15, precise=True)
        assert (jet.x, jet.y) == pytest.approx((1200 + distance, 2500))
        assert jet.path
    s.move(1 / 15, precise=True)
    assert (jet.x, jet.y) == (1220, 2500) and jet.path == []

    s.order_move(jet, (1240, 2500), False)
    assert jet.path == [(1240, 2500)]
    assert not jet.frame_move and 'jet' not in s.frame_movers  # precise startup is first-order only
