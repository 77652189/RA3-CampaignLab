"""The two script gates on unit production."""
import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
from engine.ports.command import Command  # noqa: E402
from engine.testing.small import small_world  # noqa: E402

PLAYER = 'Player_1'
ENGINEER = 'AlliedEngineer'


@pytest.mark.parametrize('gate', ['template', 'player'])
def test_a_script_gate_keeps_the_paid_head_and_waiting_jobs_until_reenabled(gate):
    s = small_world([('factory', 'AlliedBarracks', PLAYER, 600, 600),
                     ('plant', 'AlliedPowerPlant', PLAYER, 900, 600)], model=False)
    f = s.bodies['factory']
    s.money[PLAYER] = 1000
    sidebar = Command('build', player=PLAYER, template=ENGINEER)
    assert s.commands.do(sidebar) == (True, '')
    s.production.due(1)
    head, = s.production.queues[f.serial]
    progress = head['progress']
    assert progress == pytest.approx(100 / 150)
    assert head['paid'] == 4 and s.money[PLAYER] == 996  # ceil(500/150)

    if gate == 'template':
        s.act('ALLOW_DISALLOW_ONE_BUILDING', [PLAYER, ENGINEER.lower(), 0], None)
        assert not s.commands.do(sidebar)[0]
    else:
        s.act('PLAYER_DISABLE_UNIT_CONSTRUCTION', [PLAYER], None)
    s.act('NAMED_USE_COMMANDBUTTON_ABILITY', [f.name, 'Command_ConstructAlliedEngineer'], None)
    waiting = s.production.queues[f.serial][1]
    s.production.due(20)
    assert s.production.queues[f.serial] == [head, waiting]
    assert head['progress'] == progress and head['paid'] == 4 and s.money[PLAYER] == 996
    assert waiting['progress'] == waiting['paid'] == 0

    if gate == 'template':
        s.act('ALLOW_DISALLOW_ONE_BUILDING', [PLAYER, ENGINEER.lower(), 1], None)
    else:
        s.act('PLAYER_ENABLE_UNIT_CONSTRUCTION', [PLAYER], None)
    s.production.due(21)
    assert head['progress'] == pytest.approx(200 / 150)
    assert head['paid'] == 7 and s.money[PLAYER] == 993  # ceil(2*500/150), with the original $4 still paid
    assert waiting['progress'] == waiting['paid'] == 0
