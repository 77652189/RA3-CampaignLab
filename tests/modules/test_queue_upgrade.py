"""A factory's own tier upgrade, with a snapshot during its last pending frame."""
import json

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.state.snapshot as simsnap  # noqa: E402
from engine.ports.command import Command  # noqa: E402
from engine.testing.small import small_world  # noqa: E402

PLAYER = 'Player_1'
TECH = 'Upgrade_JapanBarracksTech2'


def test_object_upgrade_survives_snapshot_and_applies_before_the_unit_door_delay():
    s = small_world([('seller', 'JapanBarracks', PLAYER, 600, 600),
                     ('refinery', 'JapanRefinery', PLAYER, 900, 600),
                     ('plant', 'JapanPowerPlant', PLAYER, 1200, 600)], model=False)
    seller = s.bodies['seller']
    s.money[PLAYER] = 1000
    order = Command('build', player=PLAYER, template=TECH)
    assert s.commands.do(order) == (True, '')
    assert not s.commands.do(order)[0]  # owner's duplicate is suppressed even before the upgrade arrives
    assert s.money[PLAYER] == 1000

    s.act('PLAYER_DISABLE_UNIT_CONSTRUCTION', [PLAYER], None)   # a unit gate holds no upgrade (INFERRED, simproduce)
    s.production.due(1)
    # $500 over 30 s at full power (100 supply, 75 demand): ceil(500/450) = 2.
    job, = s.queues[seller.serial]
    assert job['progress'] == pytest.approx(100 / 450)
    assert job['paid'] == 2 and s.money[PLAYER] == 998
    s.production.due(450)
    assert job['full'] is None and job['paid'] == 500  # the single-precision sum needs one more step
    s.production.due(451)
    assert job['full'] == 451 and TECH not in seller.upgrades
    s.clock.frame = 451

    restored = small_world(model=False)
    simsnap.restore(restored, json.loads(json.dumps(simsnap.snapshot(s))))
    b = restored.bodies['seller']
    assert b.serial == seller.serial
    assert restored.queues[b.serial] == [job] and restored.production.produced_to == 451
    assert restored.money[PLAYER] == 500 and TECH not in b.upgrades
    restored.production.due(451)
    assert TECH not in b.upgrades
    restored.clock.frame = 452
    restored.production.due(452)
    assert b.upgrades == {TECH} and b.up_since[TECH] == 452
    assert TECH not in restored.player_ups.get(PLAYER, ())
    assert restored.money[PLAYER] == 500 and not restored.queues[b.serial]
    assert not restored.commands.do(order)[0]  # held by the only seller now
