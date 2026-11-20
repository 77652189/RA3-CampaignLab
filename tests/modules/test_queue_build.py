"""Unit production through the command port in a small world."""
import math

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
from engine.ports.command import Command  # noqa: E402
from engine.testing.small import small_world  # noqa: E402

PLAYER = 'Player_1'
ENGINEER = 'AlliedEngineer'


def test_unit_queue_pays_in_frames_and_starts_its_next_job_before_the_door_opens():
    s = small_world([('first', 'AlliedBarracks', PLAYER, 600, 600),
                     ('second', 'AlliedBarracks', PLAYER, 900, 600),
                     ('plant', 'AlliedPowerPlant', PLAYER, 1200, 600)], model=False)
    first, second = s.bodies['first'], s.bodies['second']
    first.angle, first.team = math.pi / 2, 'Player_1/FactoryTeam'
    s.money[PLAYER] = 2000
    sidebar = Command('build', player=PLAYER, template=ENGINEER)
    at_first = Command('build', player=PLAYER, template=ENGINEER, target=first.name,
                       args=(('target_serial', first.serial),))
    assert s.commands.do(sidebar) == (True, '')  # equally short: first in factory order
    assert s.commands.do(sidebar) == (True, '')  # now second has the shorter queue
    assert s.commands.do(at_first) == (True, '')
    assert s.money[PLAYER] == 2000
    head, following = s.queues[first.serial]
    other, = s.queues[second.serial]

    # Engineer: $500 over 10 s at 15 fps; ceil($500 * 16/150) = $54 per factory.
    s.produce_due(1)
    s.produce_due(16)
    assert head['paid'] == other['paid'] == 54
    assert s.money[PLAYER] == 1892
    s.produce_due(16)
    assert s.money[PLAYER] == 1892  # the same frame is not charged twice

    s.produce_due(150)
    assert head['paid'] == 500 and head['full'] is None  # single-precision sum is still below 100
    s.produce_due(151)
    assert head['full'] == 151 and following['paid'] == 0
    s.produce_due(152)
    assert following['paid'] == 4  # ceil($500/150), before the preceding engineer exits
    s.produce_due(160)
    assert not [b for b in s.living() if b.template == ENGINEER]
    s.produce_due(161)  # Barracks DoorOpeningTime rounds to 10 frames.
    made = {b.made_by: b for b in s.living() if b.template == ENGINEER}
    assert set(made) == {first.name, second.name}
    b = made[first.name]
    # Local UnitCreatePoint (0,18) and NaturalRallyPoint (40,18), rotated by 90 degrees.
    # Production extends the rally vector by 40 world units.
    assert (b.x, b.y, b.angle) == pytest.approx((582, 600, math.pi / 2))
    assert b.team == first.team and b.owner == PLAYER and b.mode == 'move'
    scale = 1 + 40 / math.hypot(40, 18)
    assert b.dest == pytest.approx((600 - 18 * scale, 600 + 40 * scale))


def test_unit_queue_stalls_for_cash_and_uses_current_power_when_it_resumes():
    s = small_world([('factory', 'AlliedBarracks', PLAYER, 600, 600)], model=False)
    f = s.bodies['factory']
    s.money[PLAYER] = 2
    assert s.commands.do(Command('build', player=PLAYER, template=ENGINEER)) == (True, '')
    job, = s.queues[f.serial]
    assert s.power(PLAYER) == (0, 25)
    s.produce_due(1)
    # With zero supply, trunc(10/0.3)*15 = 495 frames. First charge is ceil(500/495) = 2.
    assert job['progress'] == pytest.approx(100 / 495)
    assert job['paid'] == 2 and s.money[PLAYER] == 0
    s.produce_due(5)
    assert job['progress'] == pytest.approx(100 / 495)
    assert job['paid'] == 2 and s.money[PLAYER] == 0

    s.add('plant', 'AlliedPowerPlant', PLAYER, 900, 600)
    s.act('PLAYER_GIVE_MONEY', [PLAYER, 100], None)
    s.produce_due(6)
    assert s.power(PLAYER) == (100, 25)
    assert job['progress'] == pytest.approx(100 / 495 + 100 / 150)
    assert job['paid'] == 5 and s.money[PLAYER] == 97  # ceil(500*(1/495+1/150)) = 5


def test_the_proxy_can_spend_the_bank_less_what_its_own_queued_jobs_still_take():
    """simproxy money(): the bank less Production.owed -- the player's jobs only, paid so far counted (S7b 1)."""
    import simproxy
    s = small_world([('factory', 'AlliedBarracks', PLAYER, 600, 600),
                     ('foe', 'AlliedBarracks', 'Player_2', 900, 600)], model=False)
    s.money.update({PLAYER: 2000, 'Player_2': 2000})
    assert s.order_build(PLAYER, ENGINEER) and s.order_build('Player_2', ENGINEER)
    s.produce_due(10)
    w = object.__new__(simproxy.SimWorld)
    w.peers, w.me = simproxy.Peers(s), PLAYER
    job, = s.queues[s.bodies['factory'].serial]
    assert 0 < job['paid'] < job['cost'] and w.money() == s.money[PLAYER] - (job['cost'] - job['paid'])
